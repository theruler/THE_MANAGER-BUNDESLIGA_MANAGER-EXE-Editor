"""CHAMPIONSHIP data model: divisions, fixtures, results, standings, season rollover, save / load.

No pygame and no UI here: championship_system.py draws it and connects it to the match engine.

The roster (MANA.DAT) is read in rows of DIV_SIZE teams: teams 0-19 = first division, 20-39 = second, 40-59 = third; the
teams left over (the last 4) are the POOL used for the relegations from / promotions to the last division.
Every division plays its own double round robin at the same time: the user plays (or simulates) his match of each
round, every other match of that round, in every division, is simulated at the same moment.

Only the results are stored: fixtures and standings are always recomputed. The save files are plain, readable JSON.
"""

import datetime
import json
import math
import os
import random
import re
import time

SAVE_DIR = "campionati" # Folder of the save slots, next to options.json.
SLOTS = 5
FORMAT_NAME, SAVE_VERSION = "il-mister-championship", 2
DIV_SIZE = 20 # Teams per division in MANA.DAT.
MAX_DIVS = 3
PROMO = 4 # Teams that move between two adjacent divisions (and between the last division and the pool) every season.
DIV_NAMES = "ABCDEFGH"
WIN_PTS, DRAW_PTS = 3, 1
START_YEAR = 2026 # The first season is 2026/27.
WINTER_AFTER = 16 # The winter break comes before round index 16 (the 17th round), after the 16th.
ROUND_DATES = ((8, 23, 6), (8, 30, 6), (9, 6, 6), (9, 13, 6), (9, 20, 6), (10, 11, 6), (10, 18, 6), (10, 25, 6), (10, 28, 2), (11, 1, 6),
               (11, 8, 6), (11, 22, 6), (11, 29, 6), (12, 6, 6), (12, 13, 6), (12, 20, 6), (1, 3, 6), (1, 6, 2), (1, 10, 6), # (month, day, weekday: Monday = 0)
               (1, 17, 6), (1, 24, 6), (1, 31, 6), (2, 7, 6), (2, 14, 6), (2, 21, 6), (2, 28, 6), (3, 7, 6), (3, 14, 6), (3, 21, 6),
               (4, 4, 6), (4, 11, 6), (4, 18, 6), (4, 25, 6), (5, 2, 6), (5, 9, 6), (5, 16, 6), (5, 23, 6), (5, 30, 6)) # calendario.txt: 38 rounds, 19 + 19.
ROSTER = 20 # Players per team (as in the roster of the single match).
BENCH = 7 # Substitutes named for a match: the best available players after the starting eleven.
YELLOW_BAN = 5 # Yellow cards that cost one match.
FAT_MATCH, FAT_REST, FAT_PLAYED = 45, 25, 10 # Fatigue (0-100): gained by a full match, lost after a match missed / played.
FAT_FAST_GAIN, FAT_FAST_RAND = 36, (0.5, 1.5) # SIMULA VELOCE / SUBITO: fatigue gained by a full match (random share of it, fitter players gain less)...
FAT_FAST_PLAYED, FAT_FAST_REST = 0.25, 0.50 # ...and the share of the fatigue lost after a match played / missed (bench, injured, suspended): rest pays off.
FAT_COND = 0.30 # Fatigue 100 takes this share of the top value off the player's Condition.
FAT_FORM = 0.30 # ...and this share off the player's Form: a tired player is also out of form.
FAT_PAPER_K = 1.8 # SIMULA SUBITO (on paper): the tiredness penalty (Condition and Form) is multiplied by this, so that a tired eleven plays clearly worse.
INJ_BASE, INJ_FAT = 0.008, 0.04 # Chance of an injury per match played: base + fatigue term (engine injuries are added to it).
FORM_CAP, FORM_GOAL = 15, 2 # The Form of a player moves by at most FORM_CAP (in 1/100 of the top value); a goal is worth FORM_GOAL.
BASE_GOALS, HOME_BONUS = 1.30, 1.10 # Match simulation: average goals per team (equal strengths), home factor.
ATT_W, DEF_W = (0.25, 0.55, 0.20), (0.30, 0.20, 0.50) # Weights of (Condition, Skill, Form) in the attack and in the defence of a team.
NEUTRAL = (50.0, 50.0) # (attack, defence) of an unknown team.
GAP_K, DAY_SD = 1.25, 0.10 # Goals scale by exp(GAP_K * (attack - opposing defence) / 50); DAY_SD = random form of the day (in the same units).
LAM_MIN, LAM_MAX = 0.12, 5.0 # Limits of the expected goals of a team in a match.


def season_label(season): # "2026/27" for season 1.
    y = START_YEAR + int(season) - 1
    return "%d/%02d" % (y, (y + 1) % 100)

def round_date(season, r): # Date of round r (0-based) of the season: the real calendar of 2026/27, moved to the nearest same weekday in later years.
    if not 0 <= r < len(ROUND_DATES):
        return None
    m, d, wd = ROUND_DATES[r]
    t = datetime.date(START_YEAR + int(season) - 1 + (1 if m < 8 else 0), m, d)
    delta = (wd - t.weekday()) % 7
    return t + datetime.timedelta(days=delta - 7 if delta > 3 else delta)

def slot_file(i): # File name of save slot i (0-based).
    return "slot%d.json" % (i + 1)

def layout_divisions(n_teams): # (divisions, pool) for a roster of n_teams: rows of DIV_SIZE teams, the rest is the pool.
    n = int(n_teams)
    if n >= DIV_SIZE:
        k = min(MAX_DIVS, n // DIV_SIZE)
        return [list(range(i * DIV_SIZE, (i + 1) * DIV_SIZE)) for i in range(k)], list(range(k * DIV_SIZE, n))
    m = n - n % 2 # Tiny roster: one even division (keeps the program usable with a short MANA.DAT).
    return ([list(range(m))] if m >= 2 else []), list(range(m, n))

def round_robin(ids, double=False): # Circle method: list of rounds, each a list of (home, away). double = home and away legs.
    ids = list(ids)
    n = len(ids)
    rounds, venue = [], {} # venue[team] = +1 if its last match was at home, -1 if away: each pairing is oriented to alternate them.
    for r in range(n - 1):
        rd = []
        for i in range(n // 2):
            a, b = ids[i], ids[n - 1 - i]
            keep = (venue.get(a, 0) > 0) + (venue.get(b, 0) < 0) # Penalty of a-home / b-away after streaks.
            swap = (venue.get(b, 0) > 0) + (venue.get(a, 0) < 0)
            h, w = (a, b) if keep < swap or (keep == swap and (r + i) % 2 == 0) else (b, a)
            rd.append((h, w))
            venue[h], venue[w] = 1, -1
        rounds.append(rd)
        ids = [ids[0]] + [ids[-1]] + ids[1:-1]
    if double:
        rounds += [[(a, h) for h, a in rd] for rd in rounds]
    return rounds

def rows_rating(rows): # (attack, defence) of a set of players given as (Condition, Skill, Form) rows (10-99 scale).
    rows = [r for r in rows if len(r) >= 3]
    if not rows:
        return NEUTRAL
    c, t, f = (sum(float(r[k]) for r in rows) / len(rows) for k in range(3))
    return (c * ATT_W[0] + t * ATT_W[1] + f * ATT_W[2], c * DEF_W[0] + t * DEF_W[1] + f * DEF_W[2])

def best_rows(team, n=11): # The (Condition, Skill, Form) rows of the best n players of a roster team (mean of the three, as the automatic line-up ranks them).
    try:
        rows = [list(r)[:3] for r in team["stats"][:ROSTER]]
    except (KeyError, IndexError, TypeError):
        return []
    rows = [r for r in rows if len(r) == 3 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in r)]
    rows.sort(key=sum, reverse=True)
    return rows[:n]

def team_strength(team): # (attack, defence) of a roster team from the ABSOLUTE ratings of its best eleven: a 40/40/40 team is weak in every division.
    return rows_rating(best_rows(team))

def division_strengths(teams, divisions): # {team id: (attack, defence)} for every team of every division.
    return {i: team_strength(teams[i]) for d in divisions for i in d}

def poisson(lam, rng): # Knuth's algorithm, capped at 8 goals.
    lim, k, p = math.exp(-lam), 0, 1.0
    while k < 8:
        p *= rng.random()
        if p <= lim:
            break
        k += 1
    return k

def sim_score(sh, sa, rng=random): # (goals home, goals away) for the (attack, defence) pairs sh, sa: expected goals follow the gap between one attack and the other defence.
    dh, da = rng.gauss(0.0, DAY_SD), rng.gauss(0.0, DAY_SD) # Form of the day: keeps an upset possible between near equals, not between a 40 and a 90.
    lh = BASE_GOALS * HOME_BONUS * math.exp(GAP_K * ((sh[0] - sa[1]) / 50.0 + dh))
    la = BASE_GOALS / HOME_BONUS * math.exp(GAP_K * ((sa[0] - sh[1]) / 50.0 + da))
    return poisson(min(LAM_MAX, max(LAM_MIN, lh)), rng), poisson(min(LAM_MAX, max(LAM_MIN, la)), rng)


def new_record(): # Season record of one player.
    return dict(games=0, goals=0, yellow=0, red=0, ybank=0, inj=0, susp=0, fat=0, formd=0) # inj / susp: matches still to miss.

class Squad:
    """The user's team through the championship: formation, line-up and the record of each of its ROSTER players."""
    def __init__(self, formation=None, lineup=None, players=None):
        self.formation, self.lineup = formation, lineup # lineup: {role: [roster index or None, ...]} as in Game.lineup[side].
        self.p = players if players is not None else [new_record() for _ in range(ROSTER)]

    def available(self, i): # Can player i be named for the next match?
        return self.p[i]["inj"] <= 0 and self.p[i]["susp"] <= 0

    def effective(self, i, base, top, k=1.0): # (Condition, Skill, Form) the engine uses: tiredness lowers Condition AND Form, results move Form. k scales the tiredness penalty (SIMULA SUBITO uses FAT_PAPER_K).
        c, t, f = base[0], base[1], base[2]
        r, lo = self.p[i], 1 if top > 1 else 0
        def clamp(v, b):
            return max(min(b, lo), min(top, v))
        tired = top * k * r["fat"] / 100.0
        return (clamp(c - round(FAT_COND * tired), c), t, clamp(f + round(top * r["formd"] / 100.0) - round(FAT_FORM * tired), f))

    def after_match(self, played, goals, yellows, reds, result, hurt=(), rng=random, fit=None):
        """Book one championship match of the user's team.
        played {idx: share of the match}, goals {idx: n}, yellows {idx: n}, reds {idx: matches of ban}, result +1 / 0 / -1, hurt: injured in the match.
        fit: {idx: Fitness 0..1} = the fast fatigue model (SIMULA VELOCE / SUBITO); None = the classic one (GIOCA / SIMULA)."""
        for r in self.p: # Players who could not play served one match of their sanction.
            r["inj"], r["susp"] = max(0, r["inj"] - 1), max(0, r["susp"] - 1)
        for i, r in enumerate(self.p):
            share = played.get(i, 0.0)
            if share:
                r["games"] += 1
                if fit is None:
                    r["fat"] = min(100, r["fat"] + round(FAT_MATCH * share))
                else: # A random share of a full match's load; a fit player gains less.
                    r["fat"] = min(100, r["fat"] + round(FAT_FAST_GAIN * share * rng.uniform(*FAT_FAST_RAND) * (1.3 - 0.6 * fit.get(i, 0.5))))
            if fit is None:
                r["fat"] = max(0, r["fat"] - (FAT_PLAYED if share else FAT_REST))
            else: # Proportional recovery: whoever rests (bench, not named) recovers much more than whoever plays every week.
                r["fat"] = max(0, round(r["fat"] * (1.0 - (FAT_FAST_PLAYED if share else FAT_FAST_REST))))
            g = goals.get(i, 0)
            r["goals"] += g
            d = r["formd"]
            d = d + FORM_GOAL * g + result if share else d - (d > 0) + (d < 0) # Players who did not play drift back to their usual form.
            r["formd"] = max(-FORM_CAP, min(FORM_CAP, d))
            y = yellows.get(i, 0)
            r["yellow"] += y
            r["ybank"] += y if i not in reds else 0
            while r["ybank"] >= YELLOW_BAN:
                r["ybank"] -= YELLOW_BAN
                r["susp"] += 1
            if i in reds:
                r["red"] += 1
                r["susp"] += reds[i]
            if share and (i in hurt or rng.random() < INJ_BASE + INJ_FAT * (r["fat"] / 100.0) ** 2):
                r["inj"] = max(r["inj"], rng.choice((1, 1, 2, 2, 3, 4, 6)))

    def paper_match(self, xi, weights, goals_for, result, rng=random, fit=None): # The user's match settled on paper: eleven players, goals shared by weight.
        goals = {}
        for _ in range(goals_for):
            i = rng.choices(xi, weights=[max(0.01, weights.get(i, 1.0)) for i in xi])[0]
            goals[i] = goals.get(i, 0) + 1
        yellows = {i: 1 for i in xi if rng.random() < 0.06}
        reds = {i: 1 for i in xi if rng.random() < 0.004}
        self.after_match({i: 1.0 for i in xi}, goals, yellows, reds, result, (), rng, fit)

    def season_reset(self): # New season: the counters restart, tiredness / injuries / bans carry over.
        for r in self.p:
            r.update(games=0, goals=0, yellow=0, red=0, ybank=0, formd=0)

    def to_dict(self, names=None):
        pl = []
        for i, r in enumerate(self.p):
            pl.append(dict(name=names[i], **r) if names and i < len(names) and names[i] else dict(r))
        return dict(formation=self.formation, lineup=self.lineup, players=pl)

    @classmethod
    def from_dict(cls, d): # Validated squad, or None.
        try:
            lineup = d["lineup"]
            if lineup is not None and not (isinstance(lineup, dict) and all(isinstance(v, list) and all(x is None or (isinstance(x, int) and 0 <= x < ROSTER) for x in v) for v in lineup.values())):
                return None
            pl = []
            for r in d["players"]:
                rec = new_record()
                for k in rec:
                    v = r[k]
                    if not isinstance(v, int) or isinstance(v, bool) or not -100 <= v <= 100000:
                        return None
                    rec[k] = v
                pl.append(rec)
            if len(pl) != ROSTER or not (d["formation"] is None or isinstance(d["formation"], str)):
                return None
            return cls(d["formation"], lineup, pl)
        except (KeyError, TypeError):
            return None


class Championship:
    def __init__(self, divisions, pool, user, season=1, double=True, results=None, squad=None):
        self.squad = squad or Squad() # The user's team: formation, line-up and player records.
        self.manager, self.face = "", 0 # Name and face (index in the faces of 0.VGA, 0a.VGA ...) of the user's manager.
        self.divisions = [list(d) for d in divisions]
        self.pool, self.user, self.season, self.double = list(pool), user, int(season), bool(double)
        if not any(user in d for d in self.divisions):
            raise ValueError("user team not in a division")
        self.rounds = [round_robin(d, self.double) for d in self.divisions] # rounds[division][round] = [(home, away), ...]
        self.results = results if results is not None else self._empty_results() # Same shape: [gh, ga] or None.

    def _empty_results(self):
        return [[[None] * len(rd) for rd in rds] for rds in self.rounds]

    @classmethod
    def new(cls, n_teams, user, double=True, formation=None, lineup=None): # A fresh championship on the divisions of a roster of n_teams.
        divs, pool = layout_divisions(n_teams)
        return cls(divs, pool, user, 1, double, squad=Squad(formation, lineup))

    # ---------- the user's division ----------
    @property
    def user_div(self): # Index of the division of the user's team.
        return next(i for i, d in enumerate(self.divisions) if self.user in d)

    def total_rounds(self):
        return len(self.rounds[self.user_div])

    def round_date(self, r): # Calendar date of round r, or None when the division does not have the 38 rounds of the real calendar.
        return round_date(self.season, r) if self.total_rounds() == len(ROUND_DATES) else None

    def user_slot(self, r): # Index of the user's match inside round r.
        return next(i for i, (h, a) in enumerate(self.rounds[self.user_div][r]) if self.user in (h, a))

    def user_fixture(self, r): # (home, away) of the user's match in round r.
        return self.rounds[self.user_div][r][self.user_slot(r)]

    def round_index(self): # First round whose user match is still to play; None when the season is over.
        d = self.user_div
        return next((r for r in range(len(self.rounds[d])) if self.results[d][r][self.user_slot(r)] is None), None)

    @property
    def finished(self):
        return self.round_index() is None

    def played_rounds(self): # Number of rounds already played by the user.
        r = self.round_index()
        return self.total_rounds() if r is None else r

    # ---------- results ----------
    def _sim_round(self, r, strengths, rng): # Simulate every unplayed match of round r, in every division.
        for d, rds in enumerate(self.rounds):
            if r < len(rds):
                for i, (h, a) in enumerate(rds[r]):
                    if self.results[d][r][i] is None:
                        self.results[d][r][i] = list(sim_score(strengths.get(h, NEUTRAL), strengths.get(a, NEUTRAL), rng))

    def record_user(self, r, gh, ga, strengths, rng=random): # Store the user's result of round r and simulate the rest of the round.
        self.results[self.user_div][r][self.user_slot(r)] = [int(gh), int(ga)]
        self._sim_round(r, strengths, rng)

    def simulate_user(self, r, strengths, rng=random): # Settle the user's match of round r on paper too.
        h, a = self.user_fixture(r)
        self.record_user(r, *sim_score(strengths.get(h, NEUTRAL), strengths.get(a, NEUTRAL), rng), strengths, rng)

    # ---------- table ----------
    def standings(self, d=None): # Rows of division d (default: the user's) by points, goal difference, goals scored, team id.
        d = self.user_div if d is None else d
        rows = {i: dict(team=i, played=0, won=0, drawn=0, lost=0, gf=0, ga=0, gd=0, pts=0) for i in self.divisions[d]}
        for rd, res in zip(self.rounds[d], self.results[d]):
            for (h, a), sc in zip(rd, res):
                if sc is None:
                    continue
                for t, f, g in ((h, sc[0], sc[1]), (a, sc[1], sc[0])):
                    row = rows[t]
                    row["played"] += 1
                    row["gf"] += f
                    row["ga"] += g
                    if f > g:
                        row["won"] += 1
                        row["pts"] += WIN_PTS
                    elif f == g:
                        row["drawn"] += 1
                        row["pts"] += DRAW_PTS
                    else:
                        row["lost"] += 1
        for row in rows.values():
            row["gd"] = row["gf"] - row["ga"]
        return sorted(rows.values(), key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["team"]))

    def champion(self, d=None): # Team id leading division d (the champion once the season is over).
        return self.standings(d)[0]["team"]

    def user_position(self): # 1-based place of the user in his division.
        return 1 + [x["team"] for x in self.standings()].index(self.user)

    # ---------- season rollover ----------
    def end_season(self, strengths, rng=random): # Finish every division, move teams between divisions / pool, start the next season.
        for r in range(max(len(x) for x in self.rounds)):
            self._sim_round(r, strengths, rng)
        tabs = [[x["team"] for x in self.standings(d)] for d in range(len(self.divisions))]
        nd = len(tabs)
        size = min(len(t) for t in tabs)
        kb = min(PROMO, size // 4) if nd > 1 else 0 # Moves between adjacent divisions.
        kp = min(PROMO, len(self.pool), size // 4) # Moves between the last division and the pool.
        up = [t[:kb] for t in tabs] # Promoted from division d to d-1 (d >= 1).
        down = [t[len(t) - kb:] if kb else [] for t in tabs] # Relegated from d to d+1 (d < nd-1).
        out_pool = [t for t in reversed(tabs[-1]) if t != self.user][:kp] # The user is never sent to the pool: the next worst goes instead.
        rescued = kp > 0 and self.user in tabs[-1][len(tabs[-1]) - kp:]
        in_pool = self.pool[:kp]
        new = []
        for d in range(nd):
            keep = [t for t in tabs[d] if not (d >= 1 and t in up[d]) and not (d < nd - 1 and t in down[d]) and not (d == nd - 1 and t in out_pool)]
            came = (down[d - 1] if d >= 1 else []) + (up[d + 1] if d + 1 < nd else []) + (in_pool if d == nd - 1 else [])
            new.append(sorted(keep + came))
        self.pool = self.pool[kp:] + out_pool
        self.squad.season_reset()
        self.divisions, self.season = new, self.season + 1
        self.rounds = [round_robin(d, self.double) for d in self.divisions]
        self.results = self._empty_results()
        return dict(rescued=rescued)

    # ---------- save / load ----------
    def to_dict(self, name=None, players=None): # Plain data for the JSON file; name(i) / players = the user's player names are written only to make it readable.
        def team(i):
            return dict(id=i, name=name(i)) if name else dict(id=i)
        r = self.round_index()
        meta = dict(team=name(self.user) if name else None, division=DIV_NAMES[self.user_div], season=self.season,
                    round=None if r is None else r + 1, rounds=self.total_rounds(), saved=time.strftime("%Y-%m-%d %H:%M:%S"))
        divs = []
        for d, ids in enumerate(self.divisions):
            fx = [[[h, a] + (sc if sc is not None else [None, None]) for (h, a), sc in zip(rd, res)] for rd, res in zip(self.rounds[d], self.results[d])]
            divs.append(dict(name=DIV_NAMES[d], teams=[team(i) for i in ids], fixtures=fx)) # fixture = [home id, away id, home goals, away goals]
        return dict(format=FORMAT_NAME, version=SAVE_VERSION, meta=meta, season=self.season, user=self.user, double_round=self.double,
                    divisions=divs, pool=[team(i) for i in self.pool], squad=self.squad.to_dict(players), manager=self.manager, face=self.face)

    @classmethod
    def from_dict(cls, d, n_teams): # Validated championship, or None when the data is unusable for a roster of n_teams.
        def ident(t):
            i = t["id"]
            if not isinstance(i, int) or isinstance(i, bool) or not 0 <= i < n_teams:
                raise ValueError("bad team id")
            return i
        try:
            if d["format"] != FORMAT_NAME or d["version"] != SAVE_VERSION:
                return None
            divs = [[ident(t) for t in dv["teams"]] for dv in d["divisions"]]
            pool = [ident(t) for t in d["pool"]]
            allids = [i for dv in divs for i in dv] + pool
            if not divs or len(set(allids)) != len(allids) or any(len(dv) < 2 or len(dv) % 2 for dv in divs):
                return None
            season = d["season"]
            if not isinstance(season, int) or isinstance(season, bool) or season < 1:
                return None
            squad = Squad.from_dict(d["squad"]) if d.get("squad") is not None else None
            if d.get("squad") is not None and squad is None:
                return None
            ch = cls(divs, pool, d["user"], season, bool(d["double_round"]), squad=squad)
            if isinstance(d.get("manager"), str):
                ch.manager = d["manager"][:24]
            if isinstance(d.get("face"), int) and not isinstance(d.get("face"), bool) and d["face"] >= 0:
                ch.face = d["face"]
            res = ch._empty_results()
            for di, dv in enumerate(d["divisions"]):
                fx = dv["fixtures"]
                if len(fx) != len(ch.rounds[di]):
                    return None
                for r, rd in enumerate(fx):
                    if len(rd) != len(ch.rounds[di][r]):
                        return None
                    for i, (h, a, gh, ga) in enumerate(rd):
                        if (h, a) != ch.rounds[di][r][i]:
                            return None
                        if gh is None and ga is None:
                            continue
                        if not all(isinstance(g, int) and not isinstance(g, bool) and 0 <= g <= 99 for g in (gh, ga)):
                            return None
                        res[di][r][i] = [gh, ga]
            ch.results = res
            return ch
        except (KeyError, TypeError, ValueError):
            return None


def render_json(data): # Readable JSON: indented, but every team and every round of fixtures on a single line.
    toks = []
    def tok(obj):
        toks.append(json.dumps(obj, ensure_ascii=False))
        return "@@%d@@" % (len(toks) - 1)
    d = dict(data)
    d["divisions"] = [dict(dv, teams=[tok(t) for t in dv["teams"]], fixtures=[tok(rd) for rd in dv["fixtures"]]) for dv in data["divisions"]]
    d["pool"] = [tok(t) for t in data["pool"]]
    if data.get("squad"):
        d["squad"] = dict(data["squad"], players=[tok(r) for r in data["squad"]["players"]], lineup={k: tok(v) for k, v in (data["squad"]["lineup"] or {}).items()} or None)
    text = json.dumps(d, indent=1, ensure_ascii=False)
    return re.sub(r'"@@(\d+)@@"', lambda m: toks[int(m.group(1))], text) + "\n"

def save_slot(path, ch, name=None, players=None): # Atomic write; returns an error text or None.
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(render_json(ch.to_dict(name, players)))
        os.replace(tmp, path)
    except OSError as ex:
        return str(ex)
    return None

def load_slot(path, n_teams): # Saved championship or None (missing, corrupted or for another roster).
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return Championship.from_dict(json.load(fh), n_teams)
    except (OSError, ValueError):
        return None
