"""CAMPIONATO: the championship pages of the INTRO (menu_page == "champ") and their link with the match engine.

Pages (self.champ_view):  "slots"  the save slots: load a championship or start a new one in a slot
                          "setup"  pick any team of any division; the picked team is shown with the column of the single-match screen
                                   (logo, formation, averages, numbered roster) and its line-up is chosen there
                          "hub"    CLASSIFICA / CALENDARIO / SQUADRA of the user's division + GIOCA / SIMULA / SIMULA VELOCE / RIPRENDI / SALVA / SLOT
Three ways to play the user's match of a round (self.champ_kind):
  "play"  the real match, with the user's controls
  "sim"   SIMULA: the real match screen (scoreboard, LOG, speed PgUp/PgDn, line-up, intensity...) but the pitch is drawn
          empty and fixed (champ_hide_play / champ_hide_cam); the goals are shown by the automatic replay
  "fast"  SIMULA VELOCE: the real engine headless, FAST_SPEEDS[champ_fast_idx] updates per frame (100x - 1000x, PgUp / PgDn),
          progress bars on the hub (_champ_dry_step); in practice limited by the speed of the engine (see Game.champ_headless)
  (now)   SIMULA SUBITO: no engine at all, the result comes from the strengths like the other matches of the round, but with the
          user's real line-up, tiredness and form; goals / cards / injuries of his players are drawn from the same model (_champ_settle_paper)
Strengths: (attack, defence) from the absolute Condition / Skill / Form of the best eleven (championship_model.rows_rating): a weak team
loses against a strong one in every division. SIMULA / GIOCA: every foul, injury, goal and replay brings the speed back to 1x (and SPACE skips it).
SIMULA VELOCE / SUBITO use the fast fatigue model: tiredness piles up at a personal random rate and rest (bench) recovers much more.
ESC never closes the game: in the championship pages it steps back (the global handler of input_system would quit), in a match
(or during the fast simulation) championship_interrupt() freezes the engine state, goes to the main menu ("PARTITA INTERROTTA")
and the hub then offers RIPRENDI (championship_resume) in place of the simulations.
At full time only ENTER (continue) and S (save) work (championship_event).
The user's team keeps a record of every player (cm.Squad): matches, goals, cards, injuries, bans, fatigue, form; the line-up and the
formation are chosen in the setup page and in the SQUADRA tab. Injured / suspended players are removed from the line-up and cannot be
substituted in (they are put in Game.sub_out), tiredness lowers the Condition the engine sees (_champ_patch_stats).
Result flow: end_half() -> championship_match_done() stores the result, books the match in the squad and simulates the rest of the round.
The slots are plain JSON files in <folder of options.json>/campionati/ (see championship_model.py).
"""

import contextlib
import copy
import cProfile
import os
import pstats
import random
import time
import types

import pygame

import championship_model as cm
import geometry
import match_config
from formation_system import FORMATIONS
from graphics_system import BANNER_BOXES, FRAME_H, FRAME_W, MANAGER_BOXES, SU_H, SU_W, art_size
from i18n import ROLE_TAG, tr
from match_config import ROLE_ORDER, TEAM_COL
from single_match_system import LIST_Y, ROSTER_BOTTOM, ROW_H
from stats_system import ROLE_COL, norm, stat_color

NOTE_SECS = 6.0
FAT_TIRED = 60 # Above this tiredness (%) a player loses priority in the automatic line-up.
CONFIRM_SECS = 3.0
SETUP_COLS = 2
SLOTS_PER_PAGE = 10 # Slots shown at once; the two arrows at the bottom left turn the page.
SLOTS = SLOTS_PER_PAGE * 10 # Save slots of the slots page: 10 pages (championship_model.SLOTS is no longer used here).
SIM_SPEED = 10 # Speed (x) the normal simulation starts at; PgUp / PgDn change it as in a played match.
FAST_SPEEDS = (100, 200, 300, 400, 500, 600, 700, 800, 900, 1000) # Engine updates per frame (= x real time at 60 fps) of the fast simulation.
FAST_DEFAULT = 1 # Index in FAST_SPEEDS of the starting speed (200x). PgUp / PgDn / + / - change it, Home = default, End = maximum.
DRY_DT = 1.0 / 60.0 # Engine step of the fast simulation (as in the main loop). 1/30 would double the speed but changes the physics: untested.
DRY_BUDGET = 0.080 # Seconds of engine work per drawn frame (the window redraws ~10 times a second, ESC answers within that).
PROFILE_ENV = "MISTER_FASTPROF" # Set this environment variable to 1: the fast simulation writes fast_profile.txt (where time goes) next to options.json.
SIM_EVENT_MODES = ("foul", "goal", "injury") # Engine modes of the events SPACE can skip in the normal simulation.
EVENT_SECONDS = 2.0 # Real seconds the picture of a yellow / red card or an injury is watched at 1x (the goal replay is 1x for its whole length).
SKIP_MAX_STEPS = 60 * 45 # SPACE skips at most this many engine steps of one event.
MANAGER_MAX = 16 # Letters of the manager name.
BANNER_INK = (58, 64, 118) # Dark blue of the texts printed on the parchment of the banner.
BANNER_LIGHT = (232, 236, 255) # Texts printed on its dark plates.
DRY_MAX_STEPS = 400000 # Safety net: a match that never ends is settled on paper.
GOLD, WHITE, DIM, WARN = (255, 224, 90), (255, 255, 255), (205, 215, 235), (255, 170, 110)
RULE = (70, 76, 110)
WON, DRAWN, LOST = (140, 230, 150), (235, 235, 160), (255, 140, 120)
NAME_KEYS = ("name", "nome", "team", "squadra") # Where a roster entry keeps its name.
ROLE_GOAL_W = (0.0, 0.6, 1.5, 3.0) # Share of the goals of a match settled on paper, by role (goalkeeper, defender, midfielder, forward).


def ctr(key, **kw): # Text "champ.<key>" of the language files.
    return tr("champ." + key, **kw)

def div_name(d): # Letter of division d.
    return cm.DIV_NAMES[d]

def _get(o, k): # o[k] / o.k or None.
    try:
        return o[k]
    except (KeyError, IndexError, TypeError):
        return getattr(o, k, None)

def _shade(s, rect, rgba, radius=4): # Translucent rounded rectangle over the marble background.
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, rgba, panel.get_rect(), border_radius=radius)
    s.blit(panel, rect.topleft)

def _ghost(o): # Copy of a world object parked far outside the pitch (used to draw the pitch alone).
    g = copy.copy(o)
    for a in ("wx", "wv", "sx", "sy", "x", "y"): # World and screen position: the referee is drawn from his screen position.
        if hasattr(g, a):
            setattr(g, a, -5000.0)
    return g


class NullAudio: # Stands in for Game.audio while the fast simulation runs: every call does nothing.
    focus = 0.0
    def __getattr__(self, name):
        return lambda *a, **k: None


class ChampionshipMixin: # Class attributes give the defaults, so Game.__init__ needs no change.
    champ = None # cm.Championship in progress.
    champ_view = "slots"
    champ_tab = "table" # Hub tab: "table", "calendar" or "squad".
    champ_div = 0 # Division shown by the tabs (hub) / the team grid (setup).
    champ_slot = 0 # Slot of the championship in memory (where SALVA writes).
    champ_cur = 0 # Slot highlighted on the slots page.
    champ_page = 0 # Page of the slots page (SLOTS_PER_PAGE slots each).
    champ_slots = () # Per slot: None (no file), False (invalid file) or a cm.Championship.
    champ_pick = 0 # Team highlighted in the setup page.
    champ_prev = None # Setup preview of the picked team: SimpleNamespace(team, lineup, formation).
    champ_round = 0 # Round shown by the CALENDARIO tab.
    champ_scroll = 0 # First row of "LE TUE PARTITE" shown.
    champ_manager = "" # Name typed in the setup page (the championship keeps its own copy: Championship.manager).
    champ_face = 0 # Manager face picked in the setup page (index of the faces of 0.VGA, 0a.VGA ...).
    champ_team = None # Team whose players the CLASSIFICA tab shows on the right of the table (None = the user's own).
    _champ_ev_prev = None # Speed index to go back to when an event of the normal simulation is over.
    _champ_ev_t = None # time.time() when the running event started (None = no event).
    _champ_ev_id = None # Identity of the event whose picture is shown (card / injury).
    _champ_ghosts = frozenset() # Roster indexes put in the line-up only to satisfy the engine (nobody else is available): sent off before the kick-off.
    _champ_ghosts_all = frozenset() # The same, kept until full time (they are neither played minutes nor red cards).
    _champ_roles = None # {team: [role of each player]} of the teams shown read-only.
    champ_dirty = False # Results not written to the slot yet.
    champ_live = None # (round, home, away) of the match being played / simulated.
    champ_kind = None # "play" | "sim" | "fast" while a championship match exists.
    champ_session = False # True while a "play" / "sim" match is on the screen.
    champ_dry = None # State of the fast simulation.
    champ_fast_idx = FAST_DEFAULT # Speed of the fast simulation (index in FAST_SPEEDS).
    champ_headless = False # True while the fast simulation steps the engine: Game.update() skips what only the screen needs.
    champ_paused = None # Interrupted match: dict(kind, mode, user_team); the engine state stays in memory.
    champ_guard_t = 0.0 # Time until which a second click may replace an unsaved championship.
    champ_drop_t = 0.0 # Same for dropping an interrupted match.
    champ_over = None # (slot, expiry) waiting for the second click of NUOVO.
    champ_note = None # (text, expiry, warning) shown at the bottom of the page.
    champ_goals = None # {roster index: goals} of the user's team in the running match.
    champ_hurt = None # Roster indices of the user's players injured in the running match.
    _champ_xi = None # Roster indices of the starting eleven of the running match.
    _champ_side = 0 # Side (0 home / 1 away) of the user's team in the running match.
    _champ_orig = None # Roster stats saved while they are patched for a match.
    _champ_cam = None # Frozen camera of the simulated match: (key, cam_view()).
    _champ_prev_user = None
    _champ_prev_replay = True
    _champ_prev_slowmo = True
    _champ_starting = False
    _champ_str = None
    _champ_str_key = None
    _champ_top_v = None
    _champ_logos = None

    # ---------- files ----------
    def champ_slot_path(self, i):
        op = getattr(self, "options_path", None)
        return os.path.join(os.path.dirname(os.path.abspath(op)), cm.SAVE_DIR, cm.slot_file(i)) if op else None

    def champ_refresh_slots(self):
        out = []
        for i in range(SLOTS):
            p = self.champ_slot_path(i)
            out.append(None if not p or not os.path.isfile(p) else (cm.load_slot(p, len(self.teams)) or False))
        self.champ_slots = out

    def championship_save_slot(self): # SALVA: write the championship in its slot. Returns True on success.
        p = self.champ_slot_path(self.champ_slot)
        if not p or not self.champ:
            self.champ_say(ctr("save_err", reason="-"), True)
            return False
        err = cm.save_slot(p, self.champ, self.champ_name, self._champ_player_names(self.champ.user))
        if err:
            self.champ_say(ctr("save_err", reason=err), True)
            return False
        self.champ_dirty = False
        self.champ_say(ctr("saved", n=self.champ_slot + 1))
        return True

    # ---------- helpers ----------
    def champ_name(self, i): # Display name of roster team i.
        t = self.teams[i]
        for k in NAME_KEYS:
            v = _get(t, k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return "TEAM %d" % (i + 1)

    def _champ_player_names(self, team): # Names of the players of roster team `team`.
        pl = _get(self.teams[team], "players") or []
        return [str(pl[i]) if i < len(pl) else "" for i in range(cm.ROSTER)]

    def _champ_top(self): # Highest Condition / Skill / Form value of the roster (the scale the engine uses).
        if self._champ_top_v is None:
            vals = [v for t in self.teams for row in (_get(t, "stats") or []) for v in list(row)[:3] if isinstance(v, (int, float))]
            self._champ_top_v = max(vals) if vals else 99
        return self._champ_top_v

    def champ_strengths(self):
        key = tuple(tuple(d) for d in self.champ.divisions)
        if self._champ_str is None or self._champ_str_key != key:
            self._champ_str, self._champ_str_key = cm.division_strengths(self.teams, self.champ.divisions), key
        return self._champ_str

    def champ_say(self, text, warn=False, oneline=False): # oneline: shown on a single line, right-justified (lineup_short).
        self.champ_note = (text, time.time() + NOTE_SECS, warn, oneline)

    def _champ_line(self, r, i, d=None): # "Round 3: A 2-1 B" for fixture i of round r.
        d = self.champ.user_div if d is None else d
        h, a = self.champ.rounds[d][r][i]
        gh, ga = self.champ.results[d][r][i]
        return ctr("result", n=r + 1, h=self.champ_name(h), a=self.champ_name(a), gh=gh, ga=ga)

    def _champ_guard(self): # True when the championship in memory may be replaced (saved, or the click is repeated).
        if not (self.champ and self.champ_dirty) or time.time() < self.champ_guard_t:
            return True
        self.champ_guard_t = time.time() + CONFIRM_SECS
        self.champ_say(ctr("unsaved"), True)
        return False

    def _champ_drop_ok(self): # True when no interrupted match exists, or the click is repeated (the match is then dropped).
        if not self.champ_paused or time.time() < self.champ_drop_t:
            return True
        self.champ_drop_t = time.time() + CONFIRM_SECS
        self.champ_say(ctr("discard"), True)
        return False

    def _champ_view_round(self, r): # Select round r in the calendar and keep it inside the scroll window.
        n = self.champ.total_rounds()
        self.champ_round = max(0, min(n - 1, r))
        nvis = self._champ_rows_visible()
        self.champ_scroll = max(0, min(max(0, n - nvis), min(max(self.champ_scroll, self.champ_round - nvis + 1), self.champ_round)))

    def _champ_rows_visible(self):
        g = self._champ_geom()
        return max(5, (g["bot"] - g["y0"] - 30) // 22)

    def _champ_date(self, r, short=False): # "Domenica 23 agosto" / "23/08" for round r ("" without a calendar).
        dt = self.champ.round_date(r)
        if dt is None:
            return ""
        if short:
            return ctr("date_short", d=dt.day, m=dt.month)
        return ctr("date", wd=ctr("wd.%d" % dt.weekday()), d=dt.day, mo=ctr("mo.%d" % dt.month))

    def _champ_round_lines(self, r): # Up to two lines about round r: leg + date, and the winter-break note.
        ch, parts = self.champ, []
        if ch.double:
            parts.append(ctr("leg_first" if r < ch.total_rounds() // 2 else "leg_second"))
        if self._champ_date(r):
            parts.append(self._champ_date(r))
        return [" - ".join(parts)] + ([ctr("winter")] if r == cm.WINTER_AFTER and ch.round_date(r) else [])

    # ---------- a roster team shown on a side of the single-match machinery ----------
    @contextlib.contextmanager
    def _champ_ctx(self, c, team_id, lineup, form, only=False): # Side c shows roster team team_id with this line-up / formation; everything is restored afterwards.
        saved = (self.teams, self.sel[c], self.team_data[c], self.lineup[c], self.form_names[c], self.su_scroll[c], self._su_last_sel.get(c), self.su_active)
        try:
            td = self.teams[team_id]
            if only: # The team list of the column then holds just this team.
                self.teams, self.sel[c] = [td], 0
            self.team_data[c], self.lineup[c], self.form_names[c], self.su_active = td, lineup, form, c
            yield
        finally:
            self.teams, self.sel[c], self.team_data[c], self.lineup[c], self.form_names[c], self.su_scroll[c], last, self.su_active = saved
            if last is None:
                self._su_last_sel.pop(c, None)
            else:
                self._su_last_sel[c] = last

    def _champ_edit(self, c, team_id, store, fn, only=False): # Run fn() on side c, then keep the resulting line-up / formation in store.
        with self._champ_ctx(c, team_id, store.lineup, store.formation, only):
            r = fn()
            store.lineup, store.formation = self.lineup[c], self.form_names[c]
        return r

    def _champ_default_store(self, c, team_id, store): # Give store the default line-up of the team (the same as picking it in the single match).
        with self._champ_ctx(c, team_id, copy.deepcopy(self.lineup[c]), self.form_names[c]):
            self.fix_lineup(c, reset=True)
            store.lineup, store.formation = copy.deepcopy(self.lineup[c]), self.form_names[c]

    # ---------- entry points ----------
    def championship_open(self): # CAMPIONATO button / C key.
        self.menu_page = "champ"
        self.champ_page = self.champ_cur // SLOTS_PER_PAGE
        if self.champ is None:
            self.champ_view = "slots"
            self.champ_refresh_slots()
        else:
            self.champ_view = "hub"

    def championship_main_notice(self): # Text for the main menu while a match is interrupted.
        return ctr("interrupted") if self.champ_paused else None

    def championship_load(self, i): # Load slot i into memory.
        if not self._champ_guard():
            return
        ch = self.champ_slots[i] if i < len(self.champ_slots) else None
        if not ch:
            return
        self._champ_drop_match()
        self.champ, self.champ_slot, self.champ_dirty, self._champ_str = ch, i, False, None
        self.champ_view, self.champ_tab, self.champ_div, self.champ_team = "hub", "table", ch.user_div, None
        self._champ_repair()
        self._champ_view_round(ch.played_rounds() if not ch.finished else ch.total_rounds() - 1)

    def championship_new(self, i): # NUOVO: the setup page for a new championship in slot i.
        if not self._champ_guard():
            return
        self.champ_slot, self.champ_view, self.champ_div, self.champ_over = i, "setup", 0, None
        divs, _ = cm.layout_divisions(len(self.teams))
        self._champ_set_pick(divs[0][0] if divs else 0)

    def _champ_set_pick(self, team): # Pick a team in the setup page: its default line-up is shown.
        self.champ_pick = team
        self.champ_prev = types.SimpleNamespace(team=team, lineup=None, formation=None)
        self._champ_default_store(1, team, self.champ_prev)

    def championship_start(self): # INIZIA: create the championship with the picked team, formation and line-up, and write it in the slot.
        prev = self.champ_prev
        if not prev or prev.team != self.champ_pick:
            self._champ_set_pick(self.champ_pick)
            prev = self.champ_prev
        with self._champ_ctx(1, prev.team, prev.lineup, prev.formation):
            if self.lineup_count(1) != 11:
                return
        self._champ_drop_match()
        self.champ = cm.Championship.new(len(self.teams), prev.team, formation=prev.formation, lineup=copy.deepcopy(prev.lineup))
        self.champ.manager, self.champ.face = self.champ_manager.strip(), self.champ_face
        self._champ_str, self.champ_dirty = None, True
        self.champ_view, self.champ_tab, self.champ_div, self.champ_team = "hub", "table", self.champ.user_div, None
        self._champ_view_round(0)
        self.championship_save_slot()
        self.champ_refresh_slots()

    def championship_next_season(self): # NUOVA STAGIONE: promotions / relegations and fresh fixtures.
        ch = self.champ
        if not ch or not ch.finished or self.champ_dry:
            return
        old = ch.user_div
        info = ch.end_season(self.champ_strengths())
        new = ch.user_div
        self._champ_str, self.champ_dirty, self.champ_div = None, True, new
        key = "rescued" if info["rescued"] else "promoted" if new < old else "relegated" if new > old else "stayed"
        self.champ_say(ctr(key, l=div_name(new)))
        self._champ_view_round(0)

    # ---------- the user's squad ----------
    def _champ_repair(self, fill=True): # Line-up of the user's team: no injured / suspended starter; fill=True also fills the empty slots with the best available players.
        ch = self.champ
        sq = ch.squad
        if sq.lineup is None:
            self._champ_default_store(0, ch.user, sq)
        with self._champ_ctx(0, ch.user, sq.lineup, sq.formation):
            pos = self.slot_positions(0)
            lu = self.lineup[0]
            for role, j in pos:
                if lu[role][j] is not None and not sq.available(lu[role][j]):
                    lu[role][j] = None
            for role, j in pos if fill else ():
                if lu[role][j] is None:
                    taken = {lu[r][k] for r, k in pos}
                    cands = [i for i in range(cm.ROSTER) if sq.available(i) and i not in taken]
                    pick = self._champ_pick(role, cands)
                    if pick is not None:
                        lu[role][j] = pick
            sq.lineup, sq.formation = self.lineup[0], self.form_names[0]

    def _champ_pick(self, role, cands): # Best player for a slot: highest average first, but a player above FAT_TIRED tiredness only comes after the fresh ones (a goalkeeper slot only takes goalkeepers when any is left).
        sq = self.champ.squad
        fresh = lambda i: sq.p[i]["fat"] <= FAT_TIRED
        rate = lambda i: self.player_rating(0, i)
        nat = [i for i in cands if self.natural_pool(i) == role]
        others = [] if role == ROLE_ORDER[0] else [i for i in cands if i not in nat and self.natural_pool(i) != ROLE_ORDER[0]]
        for pool in ([i for i in nat if fresh(i)], [i for i in others if fresh(i)], nat, cands):
            if pool:
                return max(pool, key=rate)
        return None

    def _champ_tired_swap(self): # After an automatic change of formation: every starter above FAT_TIRED is replaced by the best fresh available player of the same role (only when there is one).
        ch = self.champ
        sq = ch.squad
        with self._champ_ctx(0, ch.user, sq.lineup, sq.formation):
            pos = self.slot_positions(0)
            lu = self.lineup[0]
            for role, j in pos:
                cur = lu[role][j]
                if cur is None or sq.p[cur]["fat"] <= FAT_TIRED:
                    continue
                taken = {lu[r][k] for r, k in pos}
                fresh = [i for i in range(cm.ROSTER) if sq.available(i) and i not in taken and sq.p[i]["fat"] <= FAT_TIRED and self.natural_pool(i) == role]
                if fresh:
                    lu[role][j] = max(fresh, key=lambda i: self.player_rating(0, i))
            sq.lineup, sq.formation = self.lineup[0], self.form_names[0]

    def _champ_check_lineup(self): # Before any match: 11 players named, or fewer only when nobody else is available. False = the match must not start (message shown).
        sq = self.champ.squad
        self._champ_repair(False)
        named = [i for v in (sq.lineup or {}).values() for i in v if i is not None]
        if not named:
            self.champ_say(ctr("lineup_err"), True)
            return False
        if len(named) < 11 and any(sq.available(i) and i not in named for i in range(cm.ROSTER)):
            self.champ_say(ctr("lineup_short", n=len(named)), True, True)
            return False
        return True

    def _champ_squad_info(self): # ({roster index: shirt}, bench) of the user's team: the best available players after the eleven (and a goalkeeper).
        ch = self.champ
        sq = ch.squad
        with self._champ_ctx(0, ch.user, sq.lineup, sq.formation):
            shirts = {i: self.shirt_of(0, i) for i in range(cm.ROSTER) if self.shirt_of(0, i)}
            cands = sorted((i for i in range(cm.ROSTER) if i not in shirts and sq.available(i)), key=lambda i: -self.player_rating(0, i))
            gk = next((i for i in cands if self.natural_pool(i) == ROLE_ORDER[0]), None)
            bench = ([gk] if gk is not None else []) + [i for i in cands if i != gk]
        return shirts, set(bench[:cm.BENCH])

    def _champ_state(self, i, shirts, bench): # (text key, matches left, colour) of the STATO column.
        r = self.champ.squad.p[i]
        if r["inj"] > 0:
            return "st_inj", r["inj"], (255, 110, 110)
        if r["susp"] > 0:
            return "st_susp", r["susp"], (255, 170, 90)
        if shirts.get(i):
            return "st_start", 0, (160, 240, 170)
        if i in bench:
            return "st_bench", 0, (170, 200, 255)
        return "st_res", 0, DIM

    def _champ_squad_edit(self, op, arg): # Line-up editing of the SQUADRA tab: op = "num" (left click), "clear" (right click), "form".
        ch = self.champ
        sq = ch.squad
        if op == "num" and not sq.available(arg):
            self.champ_say(ctr("unavailable"), True)
            return
        fn = {"num": lambda: self.assign_number(0, arg), "clear": lambda: self.clear_number(0, arg), "form": lambda: self.set_formation(0, arg)}[op]
        self._champ_edit(0, ch.user, sq, fn)
        if op == "form": # The engine re-places the players for the new formation: tired ones give way to fresh ones.
            self._champ_tired_swap()
        self._champ_repair(False) # A removed number stays removed: the line-up is free (checked before the match).
        self.champ_dirty = True

    def _champ_patch_stats(self, apply): # Tiredness and form change the Condition / Form the engine reads from the roster (restored after the match).
        if not apply:
            if self._champ_orig is not None:
                team, rows = self._champ_orig
                self._champ_orig = None
                try:
                    st = self.teams[team]["stats"]
                    for i, row in enumerate(rows):
                        st[i] = row
                except (TypeError, KeyError, IndexError):
                    pass
            return
        if self._champ_orig is not None or not self.champ:
            return
        team, sq, top = self.champ.user, self.champ.squad, self._champ_top()
        try:
            st = self.teams[team]["stats"]
            rows = [st[i] for i in range(cm.ROSTER)]
            for i, row in enumerate(rows):
                new = list(row)
                new[:3] = sq.effective(i, row, top)
                st[i] = type(row)(new) if isinstance(row, (list, tuple)) else new
            self._champ_orig = (team, rows)
        except (TypeError, KeyError, IndexError, ValueError): # The roster cannot be patched: matches use the plain values.
            self._champ_orig = None

    # ---------- launching a match ----------
    def _champ_prepare(self, r): # Put the fixture of round r into the engine, with the user's line-up. False when the line-ups are not ready.
        ch = self.champ
        h, a = ch.user_fixture(r)
        side = 0 if h == ch.user else 1
        self.sel = [h, a]
        self.sync_teams()
        if not self._champ_check_lineup():
            return False
        sq = ch.squad
        self.fix_lineup(1 - side, reset=True) # The opponent: his default line-up.
        self.set_formation(side, sq.formation)
        self.lineup[side] = copy.deepcopy(sq.lineup)
        ghosts = set()
        if self.lineup_count(side) != 11: # Nobody else is available: the engine still wants 11, the extra ones walk off before the kick-off (fewer men).
            named = {i for _role, i in self.lineup_slots(side)}
            for i in range(cm.ROSTER):
                if i not in named and self.lineup_count(side) < 11:
                    self.assign_number(side, i)
                    ghosts.add(i)
        if not self.lineup_ready():
            self.champ_say(ctr("lineup_err"), True)
            return False
        self.champ_live, self._champ_side = (r, h, a), side
        self._champ_ghosts = self._champ_ghosts_all = frozenset(ghosts)
        self._champ_xi = {i for _role, i in self.lineup_slots(side)} - ghosts
        self.champ_goals, self.champ_hurt = {}, set()
        return True

    def _champ_block_subs(self): # Injured, suspended and not-named players cannot come on: the engine treats them as already substituted.
        shirts, bench = self._champ_squad_info()
        sq = self.champ.squad
        blocked = {i for i in range(cm.ROSTER) if i not in self._champ_xi and (not sq.available(i) or i not in bench)}
        try:
            self.sub_out[self._champ_side] |= blocked
        except (AttributeError, TypeError, IndexError):
            pass

    def _champ_speed_idx(self, target): # Index of the fastest preset not above target (nor above the limit chosen in OPTIONS).
        top = min(target, self.speed_max)
        return max((i for i, v in enumerate(match_config.SPEEDS) if v <= top), default=0)

    def _champ_launch(self, kind): # GIOCA ("play"), SIMULA ("sim") and SIMULA VELOCE ("fast") of the current round.
        ch = self.champ
        r = ch.round_index() if ch else None
        if r is None or self.champ_dry or not self._champ_drop_ok():
            return
        self._champ_drop_match() # An interrupted match is dropped by the second click.
        if not self._champ_prepare(r):
            return
        h = self.champ_live[1]
        self.champ_kind = kind
        self._champ_prev_user, self._champ_prev_replay, self._champ_prev_slowmo = self.user_team, self.replay_auto, self.slowmo_on
        self._champ_patch_stats(True)
        if kind == "fast":
            self.champ_dry = dict(r=r, h=h, a=self.champ_live[2], steps=0, mode=None, eff=0.0, t_last=None, prof=cProfile.Profile() if os.environ.get(PROFILE_ENV) else None,
                                  saved=dict(user_team=self.user_team, replay_auto=self.replay_auto, slowmo_on=self.slowmo_on))
            self.replay_auto, self.slowmo_on, self.user_team = False, False, None # Nobody drives: both teams on the AI; no replays, no slow motion.
            real = self.audio
            self.audio, self._champ_starting = NullAudio(), True
            try:
                self.start_match()
            finally:
                self.audio, self._champ_starting = real, False
            if self.mode == "intro": # The engine refused to start.
                self._champ_dry_end(False)
                return
            self._champ_block_subs()
            self.champ_dry["mode"] = self.mode
            self.mode = "intro" # The main loop keeps drawing the menu; _champ_dry_step() advances the engine.
            return
        self.user_team = 0 if h == ch.user else 1 # The user's side: tactics (formation, intensity, substitutions) work for it.
        if kind == "sim":
            self.replay_auto, self.slowmo_on = True, False # The goals are shown by the default replay; no slow motion.
            self._champ_cam = None
            self._champ_ev_prev, self._champ_ev_t, self._champ_ev_id = None, None, None
        self.champ_session, self._champ_starting = True, True
        try:
            self.start_match()
        finally:
            self._champ_starting = False
        if self.mode == "intro": # The engine refused to start.
            self.champ_session, self.champ_live, self.champ_kind = False, None, None
            self.user_team, self.replay_auto, self.slowmo_on = self._champ_prev_user, self._champ_prev_replay, self._champ_prev_slowmo
            self._champ_patch_stats(False)
            return
        self._champ_block_subs()
        if kind == "sim":
            self.speed_idx = self.speed_top() # The normal simulation runs at the maximum speed.

    def championship_play(self):
        self._champ_launch("play")

    def championship_sim_now(self): # SIMULA SUBITO: the user's match settled on paper, instantly.
        ch = self.champ
        r = ch.round_index() if ch else None
        if r is None or self.champ_dry or not self._champ_drop_ok():
            return
        if not self._champ_check_lineup():
            return
        self._champ_drop_match()
        self._champ_settle_paper(r)
        self.champ_dirty = True
        self.champ_say(self._champ_line(r, ch.user_slot(r)))
        self._champ_view_round(r)

    def championship_sim(self, fast=False):
        self._champ_launch("fast" if fast else "sim")

    def champ_hide_play(self): # True while the simulated match must show the pitch alone (replays still show the players).
        return bool(self.champ_session and self.champ_kind == "sim" and not self.replay and self.mode != "intro")

    def champ_hide_begin(self): # Park the players, the ball and the referee outside the pitch; returns what champ_hide_end() restores.
        saved = (self.players, self.ball, self.ref, self.cp)
        self.players, self.ball, self.ref, self.cp = [], _ghost(self.ball), _ghost(self.ref), None
        return saved

    def champ_hide_end(self, saved):
        self.players, self.ball, self.ref, self.cp = saved

    def champ_hide_cam(self): # Fixed camera for the simulated match: the pitch does not scroll (the view of the kick-off, kept until the zoom changes).
        key = (self.zoom, self.view_w, self.view_h, bool(self.scroll))
        if self._champ_cam is None or self._champ_cam[0] != key:
            real = self.ball
            self.ball = copy.copy(real)
            self.ball.wx, self.ball.wv = geometry.L / 2.0, geometry.V_MID
            try:
                self._champ_cam = (key, self.cam_view())
            finally:
                self.ball = real
        return self._champ_cam[1]

    def championship_tick(self): # Called by Game.update() on every engine step.
        if self.champ_session and self.champ_kind == "sim": # A simulation is not driven by hand and has no slow motion.
            self.manual, self.slowmo_p = False, None
            if self.cp is not None:
                self.select_player(None, quiet=True)
            self._champ_event_speed()
        if self._champ_ghosts and self.champ_live and self.mode in ("restart", "play"): # Fewer men: the extra players leave as after a red card (no card, no ban).
            for p in self.team_p[self._champ_side]:
                if getattr(p, "sq", -1) in self._champ_ghosts and not p.red:
                    p.red = True
                    p.state, p.act = "leaving", None
                    self.set_gate(p)
                    p.tx, p.tv = geometry.L / 2.0 + p.gate, geometry.V_MAX_P
            self._champ_ghosts = frozenset()
        inj = self.injury
        if inj and self.champ_live and isinstance(inj, dict): # An engine injury of one of the user's players.
            p = inj.get("p")
            if p is not None and getattr(p, "team", None) == self._champ_side and hasattr(p, "sq"):
                self.champ_hurt.add(p.sq)

    def _champ_event_key(self): # Identity of the event whose scoreboard picture is up (yellow / red card, injury); None otherwise. Goals are not slowed here: their replay is 1x (IlMister.speed).
        f, inj = getattr(self, "foul", None), getattr(self, "injury", None)
        if self.mode == "foul" and f and f.get("card") and f.get("shown"):
            return ("f", id(f))
        if self.mode == "injury" and inj and inj.get("p") is not None:
            return ("i", id(inj))
        return None

    def _champ_event_speed(self): # Everything runs at the maximum speed; the picture of a card / injury is watched at 1x for EVENT_SECONDS real seconds.
        now, key, one = time.time(), self._champ_event_key(), self._champ_speed_idx(1)
        if key is not None and key != self._champ_ev_id: # A new picture.
            self._champ_ev_id, self._champ_ev_t = key, now
            if match_config.SPEEDS[self.speed_idx] > match_config.SPEEDS[one]: # Never faster than 1x; a slower speed chosen by the user stays.
                self._champ_ev_prev, self.speed_idx = self.speed_idx, one
        elif key is None:
            self._champ_ev_id = None
        if self._champ_ev_prev is not None and (key is None or now - self._champ_ev_t >= EVENT_SECONDS):
            if self.speed_idx == one: # Not changed by hand meanwhile.
                self.speed_idx = self._champ_ev_prev
            self._champ_ev_prev = None

    def _champ_skip_event(self): # SPACE during a foul / injury / goal of the normal simulation: run the event to its end (the replay of a skipped goal is skipped too).
        keep, self.replay_auto = self.replay_auto, False
        try:
            n = 0
            while self.mode in SIM_EVENT_MODES and not self.replay and self.champ_session and n < SKIP_MAX_STEPS:
                self.update(DRY_DT)
                n += 1
        finally:
            self.replay_auto = keep

    def championship_goal(self, sc, own): # Called by Game.score_goal(): goals of the user's players.
        if self.champ_live and not own and sc.team == self._champ_side and hasattr(sc, "sq"):
            self.champ_goals[sc.sq] = self.champ_goals.get(sc.sq, 0) + 1

    def championship_match_started(self): # Called by Game.start_match(): any match that is not ours drops an interrupted one.
        if not self._champ_starting:
            self._champ_drop_match()

    def _champ_drop_match(self): # Forget an interrupted match (its engine state is about to be overwritten).
        if self.champ_paused:
            self._champ_patch_stats(False)
            self.champ_paused, self.champ_dry, self.champ_live, self.champ_kind, self.champ_session = None, None, None, None, False

    def championship_match_done(self): # Called by end_half() at full time of every match.
        if not self.champ_live or not self.champ:
            return
        r, h, a = self.champ_live
        ch, side = self.champ, self._champ_side
        self.champ_live = None
        gf, ga = self.score[side], self.score[1 - side]
        team = self.team_p[side]
        final = {p.sq for p in team} - self._champ_ghosts_all
        played = {i: (1.0 if i in final else 0.6) if i in self._champ_xi else 0.4 for i in self._champ_xi | final}
        yellows, reds = {}, {}
        for p in team:
            if p.sq in self._champ_ghosts_all:
                continue
            if p.red:
                reds[p.sq] = 1 if p.yellow >= 2 else 2 # Second yellow: one match; straight red: two.
                yellows[p.sq] = min(1, p.yellow)
            elif p.yellow:
                yellows[p.sq] = p.yellow
        fit = self._champ_fit(self._champ_orig[1] if self._champ_orig else None) if self.champ_kind == "fast" else None # Fast model: rest / fitness decide the fatigue.
        ch.squad.after_match(played, self.champ_goals or {}, yellows, reds, (gf > ga) - (gf < ga), self.champ_hurt or (), random, fit)
        self._champ_patch_stats(False)
        ch.record_user(r, self.score[0], self.score[1], self.champ_strengths())
        self._champ_repair()
        self.champ_dirty = True
        self.champ_say(self._champ_line(r, ch.user_slot(r)))
        self._champ_view_round(r)

    def _champ_fit(self, rows=None): # {roster index: Fitness 0..1} of the user's players (rows = the unpatched roster rows when a match patched them).
        try:
            rows = rows if rows is not None else self.teams[self.champ.user]["stats"]
            return {i: norm(list(r)[0]) for i, r in enumerate(rows[:cm.ROSTER])}
        except (KeyError, IndexError, TypeError):
            return {}

    def _champ_settle_paper(self, r): # The user's match of round r on paper: result by strength (his real eleven, tiredness and form), players by role weight.
        ch = self.champ
        self._champ_repair(False)
        sq = ch.squad
        xi = [i for v in (sq.lineup or {}).values() for i in v if i is not None]
        top, st = self._champ_top(), self.teams[ch.user]["stats"]
        rows = [sq.effective(i, st[i], top, cm.FAT_PAPER_K) for i in xi] if xi else cm.best_rows(self.teams[ch.user]) # Instant simulation: tiredness weighs more.
        mine = cm.rows_rating(rows)
        if xi and len(xi) < 11: # Fewer men: weaker attack and defence.
            mine = (mine[0] * len(xi) / 11.0, mine[1] * len(xi) / 11.0)
        h, a = ch.user_fixture(r)
        opp = self.champ_strengths().get(a if h == ch.user else h, cm.NEUTRAL)
        gh, ga = cm.sim_score(*((mine, opp) if h == ch.user else (opp, mine)))
        ch.record_user(r, gh, ga, self.champ_strengths())
        gf, gc = (gh, ga) if h == ch.user else (ga, gh)
        with self._champ_ctx(0, ch.user, sq.lineup, sq.formation):
            w = {i: ROLE_GOAL_W[min(list(ROLE_ORDER).index(self.natural_pool(i)), len(ROLE_GOAL_W) - 1)] for i in xi}
        if xi:
            sq.paper_match(xi, w, gf, (gf > gc) - (gf < gc), random, self._champ_fit())
        self._champ_repair()

    def championship_match_closed(self): # Called by abort_match(): back to the hub (an unfinished match is not counted).
        if not self.champ_session:
            return
        self.champ_session, self.champ_live, self.champ_kind = False, None, None
        self.user_team, self.replay_auto, self.slowmo_on = self._champ_prev_user, self._champ_prev_replay, self._champ_prev_slowmo # What the player chose in OPTIONS.
        self._champ_patch_stats(False)
        self.menu_page, self.champ_view = "champ", "hub"
        r = self.champ.round_index()
        self.champ_div = self.champ.user_div
        self._champ_view_round(self.champ.total_rounds() - 1 if r is None else r)

    # ---------- interrupt / resume ----------
    def championship_interrupt(self): # ESC: freeze the match, go to the main menu showing "PARTITA INTERROTTA".
        if self.champ_dry:
            p = dict(kind="fast")
            sv = self.champ_dry["saved"]
            self.user_team, self.replay_auto, self.slowmo_on = sv["user_team"], sv["replay_auto"], sv["slowmo_on"]
        elif self.champ_session and self.mode != "intro":
            p = dict(kind=self.champ_kind, mode=self.mode, user_team=self.user_team)
            self.audio.silence()
            self.champ_session = False
            self.user_team, self.replay_auto, self.slowmo_on = self._champ_prev_user, self._champ_prev_replay, self._champ_prev_slowmo
            self.mode = "intro" # update() does nothing in the menus, so the engine state stays exactly as it is.
        else:
            return
        self._champ_patch_stats(False)
        self.champ_paused = p
        self.menu_page, self.champ_view = "main", "hub"

    def championship_resume(self): # RIPRENDI: continue exactly from where the match was interrupted.
        p, self.champ_paused = self.champ_paused, None
        if not p or not self.champ:
            return
        self._champ_patch_stats(True)
        if p["kind"] == "fast":
            self.replay_auto, self.slowmo_on, self.user_team = False, False, None
            self.champ_dry["t_last"] = None
        else:
            self.user_team = p["user_team"]
            if p["kind"] == "sim":
                self.replay_auto, self.slowmo_on = True, False
                self._champ_cam = None
            self.champ_session, self.mode = True, p["mode"]

    def championship_event(self, ev): # Called first by Game.handle_event. True = event consumed.
        if ev.type not in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            return False
        if self.mode == "intro" and self.menu_page == "champ" and not (self.options_open or self.joymap_open or self.confirm_exit):
            if ev.type == pygame.KEYDOWN and self.champ_view == "setup" and not self.champ_dry: # The manager name is typed in the setup page.
                u = getattr(ev, "unicode", "")
                if ev.key == pygame.K_BACKSPACE:
                    self.champ_manager = self.champ_manager[:-1]
                    return True
                if u and u.isprintable() and ev.key not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_TAB):
                    if len(self.champ_manager) < MANAGER_MAX and (u != " " or self.champ_manager):
                        self.champ_manager += u.upper()
                    return True
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: # The global handler of input_system would quit the game: here ESC steps back / suspends.
                    self.championship_key(pygame.K_ESCAPE)
                    return True
                if self.champ_dry and not self.champ_paused and self._champ_speed_key(ev):
                    return True
            return False
        if not (self.champ_session and self.champ and self.mode != "intro") or self.replay:
            return False
        if self.mode == "full": # Championship rules: at full time only ENTER (continue) and S (save).
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.abort_match(log=False)
                elif ev.key == pygame.K_s:
                    ok = self.championship_save_slot()
                    self.say(self.champ_note[0], (150, 230, 160) if ok else (255, 170, 110), 3.0)
                return True
            return True
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_SPACE and self.champ_kind == "sim" and self.mode in SIM_EVENT_MODES and not (self.sub_menu or self.show_help or self.paused):
                self._champ_skip_event() # While a replay runs SPACE reaches the normal handler, which skips it.
                return True
            if ev.key == pygame.K_ESCAPE and not (self.sub_menu or self.show_help or self.paused):
                self.championship_interrupt() # ESC never closes the game.
                return True
            if ev.key == pygame.K_l and self.champ_kind == "sim": # No slow motion in a simulation.
                return True
        return False

    def _champ_speed_key(self, ev): # PgUp / PgDn / + / - / Home / End: speed of the fast simulation (100x - 1000x).
        k, n = ev.key, len(FAST_SPEEDS)
        if k in (pygame.K_PAGEUP, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) or ev.unicode == "+":
            self.champ_fast_idx = min(n - 1, self.champ_fast_idx + 1)
        elif k in (pygame.K_PAGEDOWN, pygame.K_MINUS, pygame.K_KP_MINUS) or ev.unicode == "-":
            self.champ_fast_idx = max(0, self.champ_fast_idx - 1)
        elif k == pygame.K_HOME:
            self.champ_fast_idx = FAST_DEFAULT
        elif k == pygame.K_END:
            self.champ_fast_idx = n - 1
        else:
            return False
        return True

    def draw_championship_footer(self): # Replaces the hints of the end-of-match summary (ENTER / S only).
        w, h = self.view_w, self.view_h
        pygame.draw.rect(self.target, (8, 10, 24), (0, h - 36, w, 36))
        self.text(ctr("full_hint") + ("" if self.champ_dirty else ctr("full_saved")), self.font_s, GOLD, (w // 2, h - 18), True)

    # ---------- fast simulation ----------
    def _champ_dry_step(self): # One frame of the fast simulation: as many engine updates as the speed and the time budget allow.
        d = self.champ_dry
        real, t0, n = self.audio, time.perf_counter(), 0
        want = FAST_SPEEDS[self.champ_fast_idx]
        self.audio, self.mode, self.champ_headless = NullAudio(), d["mode"], True
        prof = d.get("prof")
        if prof:
            prof.enable()
        try:
            while n < want and time.perf_counter() - t0 < DRY_BUDGET and self.mode != "full":
                self.update(DRY_DT)
                self.replay = None
                n += 1
        except Exception: # A crash of the engine must not lose the championship: settle the match on paper.
            self.audio, self.champ_headless = real, False
            if prof:
                prof.disable()
            self._champ_dry_end(False, fallback=True)
            return
        if prof:
            prof.disable()
        self.audio, self.champ_headless = real, False
        d["steps"] += n
        if d["t_last"] is not None: # Speed really reached (simulated seconds per real second), smoothed.
            d["eff"] = 0.8 * d["eff"] + 0.2 * (n * DRY_DT / max(1e-3, t0 - d["t_last"]))
        d["t_last"] = t0
        if self.mode == "full":
            self._champ_dry_end(True)
        elif d["steps"] > DRY_MAX_STEPS:
            self._champ_dry_end(False, fallback=True)
        else:
            d["mode"], self.mode = self.mode, "intro"

    def _champ_write_profile(self, d): # fast_profile.txt: the functions that took the time, to see what is worth optimising.
        op = getattr(self, "options_path", None)
        if not (d.get("prof") and op):
            return
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(op)), "fast_profile.txt"), "w", encoding="utf-8") as fh:
                fh.write("%d engine steps\n\n" % d["steps"])
                for key in ("tottime", "cumulative"):
                    fh.write("--- sorted by %s ---\n" % key)
                    pstats.Stats(d["prof"], stream=fh).sort_stats(key).print_stats(35)
        except OSError:
            pass

    def _champ_dry_end(self, done, fallback=False): # Leave the fast simulation (done: the match reached full time and was recorded).
        d, self.champ_dry = self.champ_dry, None
        self._champ_write_profile(d)
        self.user_team, self.replay_auto, self.slowmo_on = d["saved"]["user_team"], d["saved"]["replay_auto"], d["saved"]["slowmo_on"]
        self.mode, self.replay, self.big, self.msgs, self.paused = "intro", None, None, [], False
        self.champ_kind = None
        self._champ_patch_stats(False)
        if not done:
            self.champ_live = None
            if fallback and self.champ and self.champ.round_index() == d["r"]:
                self._champ_settle_paper(d["r"])
                self.champ_dirty = True
                self.champ_say(ctr("sim_fallback"), True)

    # ---------- input ----------
    def championship_click(self, hit, button=1): # Tags of the championship pages. Returns True when handled.
        k = hit[0]
        if button == 3: # Right click: take a shirt number away.
            if k == "num" and self.champ_view == "setup":
                self._champ_edit(1, self.champ_prev.team, self.champ_prev, lambda: self.clear_number(1, hit[2]), only=True)
            elif k == "sq_num" and self.champ_view == "hub" and not self.champ_dry:
                self._champ_squad_edit("clear", hit[1])
            return k in ("num", "sq_num")
        if button != 1:
            return False
        if self.champ_dry and not self.champ_paused: # While the fast simulation runs nothing else can be clicked.
            return True
        if k == "back":
            if self.champ_view == "setup":
                self.champ_view = "slots"
            elif self.champ_view == "slots" and self.champ:
                self.champ_view = "hub"
            else:
                return False
        elif k == "ch_page":
            self._champ_turn_page(hit[1])
        elif k == "ch_slot":
            self.champ_cur = hit[1]
            self._champ_slot_enter(hit[1])
        elif k == "ch_new":
            if self.champ_over and self.champ_over[0] == hit[1] and time.time() < self.champ_over[1]:
                self.championship_new(hit[1])
            else:
                self.champ_over = (hit[1], time.time() + CONFIRM_SECS)
        elif k == "ch_div":
            self.champ_div = hit[1]
            if self.champ_view == "setup":
                self._champ_set_pick(cm.layout_divisions(len(self.teams))[0][hit[1]][0])
        elif k == "ch_pick":
            self._champ_set_pick(hit[1])
        elif k == "form" and self.champ_view == "setup": # Formation chips of the single-match column.
            self._champ_edit(1, self.champ_prev.team, self.champ_prev, lambda: self.set_formation(1, hit[2]), only=True)
        elif k == "num" and self.champ_view == "setup": # Shirt numbers of the roster.
            self._champ_edit(1, self.champ_prev.team, self.champ_prev, lambda: self.assign_number(1, hit[2]), only=True)
        elif k == "team":
            pass
        elif k == "ch_start":
            self.championship_start()
        elif k == "ch_face":
            self.champ_face = (self.champ_face + 1) % max(1, len(self._champ_faces()))
        elif k == "ch_tab": # CLASSIFICA / CALENDARIO always show the same series: a click on the shown one steps to the next series (both pictures follow).
            nd = min(3, len(self.champ.divisions))
            if hit[1] in ("table", "calendar") and self.champ_tab == hit[1] and nd > 1:
                self.champ_div = (self.champ_div + 1) % nd
            else:
                self.champ_tab = hit[1]
        elif k == "ch_team":
            self._champ_open_team(hit[1])
        elif k == "ch_goto": # A team of the calendar: CLASSIFICA of its series, with the team selected.
            self.champ_tab, self.champ_div = "table", hit[2]
            self._champ_open_team(hit[1])
        elif k == "sq_num":
            self._champ_squad_edit("num", hit[1])
        elif k == "sq_form":
            self._champ_squad_edit("form", hit[1])
        elif k == "ch_round":
            self._champ_view_round(hit[1])
        elif k == "ch_step":
            self._champ_view_round(self.champ_round + hit[1])
        elif k == "ch_play":
            self.championship_play()
        elif k == "ch_sim":
            self.championship_sim()
        elif k == "ch_fast":
            self.championship_sim(True)
        elif k == "ch_now":
            self.championship_sim_now()
        elif k == "ch_resume":
            self.championship_resume()
        elif k == "ch_save":
            self.championship_save_slot()
            self.champ_refresh_slots()
        elif k == "ch_slots":
            self.champ_refresh_slots()
            self.champ_page = self.champ_cur // SLOTS_PER_PAGE
            self.champ_view = "slots"
        elif k == "ch_season":
            self.championship_next_season()
        else:
            return False
        return True

    def _champ_pages(self): # Number of pages of the slots page.
        return (SLOTS + SLOTS_PER_PAGE - 1) // SLOTS_PER_PAGE

    def _champ_turn_page(self, d): # Arrow buttons / LEFT / RIGHT: another page of slots; the highlight keeps its row.
        page = max(0, min(self._champ_pages() - 1, self.champ_page + d))
        if page != self.champ_page:
            row = self.champ_cur % SLOTS_PER_PAGE
            self.champ_page = page
            self.champ_cur = min(SLOTS - 1, page * SLOTS_PER_PAGE + row)

    def _champ_open_team(self, t): # Click on a team name of the table: its players appear on the right of the table.
        self.champ_team = None if t == self.champ.user else t

    def _champ_slot_enter(self, i): # A slot was activated: load it, or start a new championship in an empty one.
        if self.champ_slots[i]:
            self.championship_load(i)
        elif self.champ_slots[i] is None:
            self.championship_new(i)

    def championship_key(self, k):
        if self.champ_dry and not self.champ_paused: # Fast simulation on screen.
            if k == pygame.K_ESCAPE:
                self.championship_interrupt()
            return
        enter = k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if k == pygame.K_ESCAPE:
            if self.champ_view == "setup":
                self.champ_view = "slots"
            elif self.champ_view == "slots" and self.champ:
                self.champ_view = "hub"
            else:
                self.menu_page = "main"
        elif self.champ_view == "slots":
            if k == pygame.K_UP:
                self.champ_cur = max(0, self.champ_cur - 1)
                self.champ_page = self.champ_cur // SLOTS_PER_PAGE
            elif k == pygame.K_DOWN:
                self.champ_cur = min(SLOTS - 1, self.champ_cur + 1)
                self.champ_page = self.champ_cur // SLOTS_PER_PAGE
            elif k in (pygame.K_LEFT, pygame.K_PAGEUP):
                self._champ_turn_page(-1)
            elif k in (pygame.K_RIGHT, pygame.K_PAGEDOWN):
                self._champ_turn_page(1)
            elif enter:
                self._champ_slot_enter(self.champ_cur)
        elif self.champ_view == "setup":
            divs = cm.layout_divisions(len(self.teams))[0]
            ids = divs[self.champ_div]
            pos = ids.index(self.champ_pick) if self.champ_pick in ids else 0
            step = {pygame.K_LEFT: -1, pygame.K_RIGHT: 1, pygame.K_UP: -SETUP_COLS, pygame.K_DOWN: SETUP_COLS}.get(k)
            if step:
                self._champ_set_pick(ids[max(0, min(len(ids) - 1, pos + step))])
            elif k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
                self.champ_div = max(0, min(len(divs) - 1, self.champ_div + (1 if k == pygame.K_PAGEDOWN else -1)))
                self._champ_set_pick(divs[self.champ_div][0])
            elif enter:
                self.championship_start()
        elif self.champ_view == "hub":
            tabs = ("table", "calendar", "squad")
            if k == pygame.K_s:
                self.championship_save_slot()
                self.champ_refresh_slots()
            elif k == pygame.K_TAB:
                self.champ_tab = tabs[(tabs.index(self.champ_tab) + 1) % len(tabs)]
            elif self.champ_tab == "calendar" and k in (pygame.K_UP, pygame.K_DOWN, pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_LEFT, pygame.K_RIGHT):
                n = {pygame.K_UP: -1, pygame.K_LEFT: -1, pygame.K_DOWN: 1, pygame.K_RIGHT: 1}.get(k, -10 if k == pygame.K_PAGEUP else 10)
                self._champ_view_round(self.champ_round + n)
            elif self.champ.finished:
                if enter:
                    self.championship_next_season()
            elif k == pygame.K_r or (enter and self.champ_paused):
                self.championship_resume()
            elif enter or k == pygame.K_p:
                self.championship_play()
            elif k == pygame.K_m:
                self.championship_sim()
            elif k == pygame.K_v:
                self.championship_sim(True)
            elif k == pygame.K_n:
                self.championship_sim_now()

    # ---------- drawing ----------
    def _champ_button(self, s, hits, vx, vy, r, label, tag, px=20, selected=False): # Generic button + hit.
        self.draw_generic_button(s, r, self.fit_text(label, px, r.w - 16), selected, r.collidepoint(vx, vy), px=px)
        hits.append((r, tag))

    def draw_championship(self, s, bd, hits, vx, vy): # The page background (the OPTIONS picture) is chosen by draw_intro().
        self._txt_shadow = True # Every text of the championship pages has a shadow.
        try:
            self._draw_championship(s, bd, hits, vx, vy)
        finally:
            self._txt_shadow = False

    def _draw_championship(self, s, bd, hits, vx, vy):
        W, H = SU_W, SU_H
        if self.champ_dry and not self.champ_paused:
            self._champ_dry_step()
        hub = self.champ_view != "setup" and not (self.champ_view == "slots" or self.champ is None)
        if not hub: # The hub has no title and no top rule: its space goes to the tables.
            if self.champ_view == "setup":
                self._put(ctr("title"), 46, WHITE, 40, cx=30 + 495 + 232, w=465) # The top left belongs to the SERIE A / B / C buttons.
            else: # The slots page has the label of the slots instead of the title.
                self._put(ctr("slots_title"), 46, WHITE, 40, cx=W // 2, w=W - 60, shadow=True)
                pygame.draw.line(s, RULE, (30, 94), (W - 30, 94), 2)
            self.back_button_br(s, hits, vx, vy)
        if self.champ_view == "setup":
            self._champ_setup(s, bd, hits, vx, vy)
        elif not hub:
            self._champ_slots(s, hits, vx, vy)
        else:
            self._champ_hub(s, hits, vx, vy)
            if self.champ_dry and not self.champ_paused:
                self._champ_dry_panel(s)
        note = self.champ_note
        if note and time.time() < note[1]:
            col = WARN if note[2] else GOLD
            if hub and len(note) > 3 and note[3]: # One line, right-justified, on the row of the SIMULA label.
                x1 = 16
                w = W - 32
                txt = self.fit_text(note[0], 16, w)
                self._put(txt, 16, col, self._champ_geom()["row_y"] - 16, left=W - 16 - self.board.font(16).size(txt)[0])
            elif hub: # Hub: the message sits in the last third of the page, on the row of the SIMULA label (up to two lines, the last one on that row).
                x1 = 16
                w = W - 32
                lines = self._wrap_text(note[0], 16, w, 2)
                for j, ln in enumerate(reversed(lines)):
                    self._put(ln, 16, col, self._champ_geom()["row_y"] - 16 - j * 18, cx=x1 + w // 2, w=w)
            else:
                self._put(note[0], 18, col, H - 14, cx=W // 2, w=W - 60)

    def _champ_place(self, n): # the text champ.place of the language files when it exists, otherwise this default.
        return ctr("final_pos", n=n)

    def _wrap_text(self, txt, px, w, max_lines=2): # Break txt into at most max_lines lines of w pixels (the last one is cut when the text is still too long).
        font, lines, cur = self.board.font(px), [], ""
        for word in txt.split():
            t = (cur + " " + word).strip()
            if cur and font.size(t)[0] > w and len(lines) < max_lines - 1:
                lines.append(cur)
                cur = word
            else:
                cur = t
        lines.append(cur)
        return [self.fit_text(ln, px, w) for ln in lines]

    def _champ_div_tabs(self, s, hits, vx, vy, n, x=None, y=84): # SERIE A / B / C.
        bw = 116
        x = SU_W - 30 - n * (bw + 6) + 6 if x is None else x
        for d in range(n):
            r = pygame.Rect(x + d * (bw + 6), y, bw, 30)
            self._champ_button(s, hits, vx, vy, r, ctr("div", l=div_name(d)), ("ch_div", d), 16, self.champ_div == d)

    def _champ_slots(self, s, hits, vx, vy): # The save slots of the current page, in a block centred on the page; the arrows at the bottom left turn the page.
        W, H = SU_W, SU_H
        if len(self.champ_slots) != SLOTS:
            self.champ_refresh_slots()
        pages = self._champ_pages()
        self.champ_page = page = max(0, min(pages - 1, self.champ_page))
        rh, gap = 44, 8
        bw = min(W - 60, 780)
        x0 = (W - bw) // 2
        ry = H - 30 - FRAME_H * 2 # Row of the bottom buttons (the same as the hub and the back button).
        total = SLOTS_PER_PAGE * rh + (SLOTS_PER_PAGE - 1) * gap # A full page: every page has the same block.
        y0 = 94 + (ry - 10 - 94 - total) // 2
        first = page * SLOTS_PER_PAGE
        for n, i in enumerate(range(first, min(SLOTS, first + SLOTS_PER_PAGE))):
            y = y0 + n * (rh + gap)
            ch = self.champ_slots[i]
            r = pygame.Rect(x0, y, bw - 176 if ch else bw, rh)
            if ch:
                nxt = ch.round_index()
                label = ctr("slot_done" if nxt is None else "slot_info", team=self.champ_name(ch.user), l=div_name(ch.user_div),
                            s=cm.season_label(ch.season), r=0 if nxt is None else nxt + 1, t=ch.total_rounds())
            else:
                label = ctr("slot_empty" if ch is None else "slot_bad")
            self._champ_button(s, hits, vx, vy, r, "%d   %s" % (i + 1, label), ("ch_slot", i), 20, self.champ_cur == i)
            if ch:
                wait = self.champ_over and self.champ_over[0] == i and time.time() < self.champ_over[1]
                self._champ_button(s, hits, vx, vy, pygame.Rect(x0 + bw - 164, y + 6, 164, rh - 12), ctr("confirm_over" if wait else "new"), ("ch_new", i), 16, bool(wait))
        if pages > 1: # LEFT / RIGHT arrows (3.VGA) in the frame of the back button; the one that has nowhere to go is darkened and cannot be clicked.
            fw, gap2 = FRAME_W * 2, 8
            for j, (name, d, lab) in enumerate((("arrow_left", -1, "<"), ("arrow_right", 1, ">"))):
                ok = 0 <= page + d < pages
                r = self.framed_button(s, hits, vx, vy, name, 0, 2, 16 + j * (fw + gap2), ry, ("ch_page", d), False, lab, ok)
                if not ok:
                    dim = pygame.Surface(r.size, pygame.SRCALPHA)
                    dim.fill((0, 0, 30, 150))
                    s.blit(dim, r)
            self._put("%d / %d" % (page + 1, pages), 22, WHITE, ry + FRAME_H, cx=16 + 2 * fw + gap2 + 50, w=90)

    def _champ_setup(self, s, bd, hits, vx, vy): # Left: series pictures (top) + the teams of the series with their strengths; right: the picked team, manager face and name.
        W, H = SU_W, SU_H
        divs, pool = cm.layout_divisions(len(self.teams))
        if self.champ_prev is None or self.champ_prev.team != self.champ_pick:
            self._champ_set_pick(self.champ_pick)
        prev = self.champ_prev
        nd, sc, gap = min(3, len(divs)), 2, 8 # the same CLASSIFICA SERIE A / B / C pictures as the next pages, in the top left corner
        x = 30 + (465 - (nd * FRAME_W * sc + (nd - 1) * gap)) // 2
        for d in range(nd):
            self._champ_art_button(s, hits, vx, vy, "tab_table", d, sc, x + d * (FRAME_W * sc + gap), 6, ("ch_div", d), self.champ_div == d, ctr("tab_table") + " " + div_name(d))
        hb = pygame.Rect(30, 6 + FRAME_H * sc + 4, 465, 26)
        pygame.draw.rect(s, (36, 60, 110), hb, border_radius=5)
        self._put(ctr("pick_team"), 21, WHITE, hb.centery, cx=hb.centerx)
        ids = divs[self.champ_div] if divs else []
        y0 = hb.bottom + 18 # selectable list: team name and its three strengths; it ends where the player list of the right column ends
        rh = max(16, min(ROW_H, (ROSTER_BOTTOM - y0) // max(1, len(ids))))
        px = max(12, min(16, rh - 5))
        cw = 44
        for n, key in enumerate(("c_cond", "c_skill", "c_form")):
            self._put(ctr(key), 12, DIM, hb.bottom + 9, cx=30 + 465 - cw * (3 - n) + cw // 2)
        for k, t in enumerate(ids):
            r = pygame.Rect(30, y0 + k * rh, 465, rh - 2)
            sel = self.champ_pick == t
            _shade(s, r, (70, 60, 10, 200) if sel else (60, 100, 170, 150) if r.collidepoint(vx, vy) else (8, 12, 34, 150 if k % 2 == 0 else 105))
            col = GOLD if sel else WHITE
            put = self._put_bold if sel else self._put
            put(self.champ_name(t), px, col, r.centery, left=r.x + 8, w=465 - 3 * cw - 16)
            for n, v in enumerate(self.teams[t]["avg"]):
                self._put(str(v), px, stat_color(v), r.centery, cx=r.right - cw * (3 - n) + cw // 2)
            hits.append((r, ("ch_pick", t)))
        # the picked team, drawn by the single-match screen itself (side 1) without its team list: the manager frame takes that place
        with self._champ_ctx(1, prev.team, prev.lineup, prev.formation, only=True):
            self._draw_single_team(s, bd, hits, vx, vy, 1, ("", ctr("selected")), with_list=False, panel_bottom=ROSTER_BOTTOM + 36) # The blue panel under "selected" also holds the manager hint.
            n = self.lineup_count(1)
        msc = 3 # Manager frame (35.VGA): face above (click = next face), typed name below.
        fw_, fh_ = art_size("manager_frame")
        fr = pygame.Rect(0, 0, fw_ * msc, fh_ * msc)
        fr.midtop = (525 + 116, LIST_Y - 8)
        frame = self.art("manager_frame", 0, msc)

        def box(name): # An empty area of the frame, in virtual pixels.
            x1, y1, x2, y2 = MANAGER_BOXES[name]
            return pygame.Rect(fr.x + x1 * msc, fr.y + y1 * msc, (x2 - x1 + 1) * msc, (y2 - y1 + 1) * msc)
        face, nb = box("face"), box("name")
        if frame is not None:
            s.blit(frame, fr)
        else: # 35.VGA missing: a plain frame with the two black areas.
            pygame.draw.rect(s, bd.BG, fr)
            pygame.draw.rect(s, bd.FRAME, fr, 2)
            pygame.draw.rect(s, (0, 0, 0), face)
            pygame.draw.rect(s, (0, 0, 0), nb)
        fimg = self._champ_face_img(self.champ_face)
        if fimg is not None: # The 40x40 face, centred in the black area.
            s.blit(pygame.transform.scale(fimg, (40 * msc, 40 * msc)), (face.x + (face.w // msc - 40) // 2 * msc, face.y + (face.h // msc - 40) // 2 * msc))
        if face.collidepoint(vx, vy):
            pygame.draw.rect(s, WHITE, face, 2)
        hits.append((face, ("ch_face",)))
        cur = "_" if int(time.time() * 2) % 2 == 0 and len(self.champ_manager) < MANAGER_MAX else ""
        if self.champ_manager or cur:
            self._put(self.champ_manager + cur, 14, WHITE, nb.centery, left=nb.x + 4, w=nb.w - 8)
        else:
            self._put(ctr("manager"), 14, DIM, nb.centery, left=nb.x + 4, w=nb.w - 8)
        self._put(ctr("manager_hint"), 16, DIM, fr.bottom + 16, cx=fr.centerx, w=300)
        if n != 11:
            self._put(tr("intro.warn_lineup", n=n), 17, WARN, 622, cx=W // 2, w=W - 60)
        else:
            self._put_right(tr("intro.hint_numbers"), 17, DIM, 622, W - 30, W - 60)
        sb = pygame.Rect(W // 2 - 140, 650, 280, 44)
        hov = sb.collidepoint(vx, vy)
        pygame.draw.rect(s, ((60, 150, 90) if hov else (44, 112, 70)) if n == 11 else (40, 44, 58), sb, border_radius=8)
        pygame.draw.rect(s, (200, 255, 210) if n == 11 else (80, 86, 104), sb, 2, border_radius=8)
        self._put(ctr("start"), 24, WHITE if n == 11 else (120, 126, 146), sb.centery, cx=sb.centerx, w=sb.w - 14)
        if n == 11:
            hits.append((sb, ("ch_start",)))

    def _champ_faces(self): # [(file stem, index)] of every manager face: 0.VGA (4 faces of 40x40, 41 px apart), then 0a.VGA, 0b.VGA ... when they exist.
        c = self.__dict__.setdefault("_face_cache", {})
        if "list" not in c:
            lst = []
            for stem in ["0"] + ["0" + ch for ch in "abcdefghijklmnopqrstuvwxyz"]:
                sheet = self.gfx.pic_surface(stem) if hasattr(self.gfx, "pic_surface") else None
                if sheet is None:
                    if stem == "0":
                        continue
                    break
                for i in range((sheet.get_width() + 1) // 41):
                    if i * 41 + 40 <= sheet.get_width() and sheet.get_height() >= 40:
                        c[(stem, i)] = sheet.subsurface(pygame.Rect(i * 41, 0, 40, 40)).copy().convert()
                        lst.append((stem, i))
            c["list"] = lst
        return c["list"]

    def _champ_face_img(self, n): # Surface (40x40) of face number n, or None.
        faces = self._champ_faces()
        return self._face_cache.get(faces[n % len(faces)]) if faces else None

    def _champ_banner_h(self): # Height of the header: the 69 px of 23.VGA at an integer vertical zoom (its width follows the screen).
        return 69 * 3

    def _champ_trend(self): # Cumulative trend of the user's season: +1 per win, 0 per draw, -1 per defeat (one value per round played, starting at 0).
        ch = self.champ
        out, v = [0], 0
        for r in range(ch.played_rounds()):
            h, a = ch.user_fixture(r)
            res = ch.results[ch.user_div][r][ch.user_slot(r)]
            if res is not None:
                gf, gc = (res[0], res[1]) if h == ch.user else (res[1], res[0])
                v += (gf > gc) - (gf < gc)
            out.append(v)
        return out

    def _champ_banner(self, s): # Header: 23.VGA stretched over the screen width with the manager, the round, the team logo, the date and the season trend.
        W, ch = SU_W, self.champ
        bh = self._champ_banner_h()
        kx, ky = W / 320.0, bh // 69
        img = self.art("banner", 0, 1)
        if img is not None:
            cache = self.__dict__.setdefault("_banner_cache", {})
            if cache.get("key") != (W, bh):
                cache["key"], cache["img"] = (W, bh), pygame.transform.scale(img, (W, bh))
            s.blit(cache["img"], (0, 0))

        def box(name):
            x1, y1, x2, y2 = BANNER_BOXES[name]
            return pygame.Rect(int(x1 * kx), y1 * ky, int((x2 - x1 + 1) * kx), (y2 - y1 + 1) * ky)

        if img is None: # No picture: plain plates so that the information stays readable.
            pygame.draw.rect(s, (40, 46, 96), (0, 0, W, bh))
            for nm in BANNER_BOXES:
                pygame.draw.rect(s, (70, 76, 130), box(nm))
        r = box("face") # manager face (40x40, integer zoom, centred)
        fimg = self._champ_face_img(ch.face)
        if fimg is not None:
            z = max(1, min(r.w // 40, r.h // 40))
            fi = pygame.transform.scale(fimg, (40 * z, 40 * z))
            s.blit(fi, fi.get_rect(center=r.center))
        td = self.teams[ch.user]
        lr = box("lower")
        who = "  -  ".join(t for t in (ch.manager.strip(), self.champ_name(ch.user)) if t)
        self._put(who, max(12, lr.h - 2), BANNER_LIGHT, lr.centery, cx=lr.centerx, w=lr.w - 12, shadow=True)
        tr_ = box("title")
        rnd = ch.round_index()
        n = ch.total_rounds() if rnd is None else rnd + 1
        txt = ctr("banner_round", n=n)
        self._put(txt, max(12, tr_.h - 2), BANNER_LIGHT, tr_.centery, cx=tr_.centerx, w=tr_.w - 10, shadow=True)
        lg = box("logo") # team logo
        logo = self.gfx.logo(td["logo"])
        if logo is not None:
            k = min((lg.w - 8) / float(logo.get_width()), (lg.h - 8) / float(logo.get_height()))
            im = pygame.transform.smoothscale(logo, (max(1, int(logo.get_width() * k)), max(1, int(logo.get_height() * k))))
            s.blit(im, im.get_rect(center=lg.center))
        sh = box("sheet") # date of the round (the next one to play; the last one when the season is over)
        d = ch.round_date(n - 1)
        cx = sh.centerx
        if d is not None:
            f = lambda p: max(16, int(sh.h * p))
            # Percentuali ridotte per spostare le label più in alto
            self._put(tr("champ.wd.%d" % d.weekday()), f(0.22), BANNER_INK, sh.y + sh.h * 15 // 100, cx=cx, w=sh.w - 12, shadow=True)
            self._put("%d." % d.day, f(0.50), BANNER_INK, sh.y + sh.h * 45 // 100, cx=cx, w=sh.w - 12, shadow=True)
            self._put(tr("champ.mo.%d" % d.month), f(0.22), BANNER_INK, sh.y + sh.h * 70 // 100, cx=cx, w=sh.w - 1, shadow=True)
            self._put(str(d.year), f(0.22), BANNER_INK, sh.y + sh.h * 90 // 100, cx=cx, w=sh.w - 12, shadow=True)
        else:
            # Spostato sopra il centro (es. al 35% invece di sh.centery che corrisponde al 50%)
            self._put(cm.season_label(ch.season), 24, BANNER_INK, sh.y + sh.h * 35 // 100, cx=cx, w=sh.w - 16, shadow=True)
        ct = box("chart") # trend of the season: up with a win, flat with a draw, down with a defeat
        trend = self._champ_trend()
        top = max(3, max(trend))
        bot = min(-3, min(trend))
        tot = max(1, ch.total_rounds())
        yy = lambda v: ct.bottom - 6 - int((v - bot) * (ct.h - 12) / float(top - bot))
        pygame.draw.line(s, (40, 44, 150), (ct.x + 4, yy(0)), (ct.right - 4, yy(0)), 1)
        pts = [(ct.x + 6 + int(i * (ct.w - 12) / float(tot)), yy(v)) for i, v in enumerate(trend)]
        if len(pts) > 1:
            pygame.draw.lines(s, (214, 214, 226), False, pts, 2)
        elif pts:
            pygame.draw.circle(s, (214, 214, 226), pts[0], 3)

    def _champ_geom(self): # Hub layout: picture scale, left column of framed buttons, content box under the banner, bottom row of framed buttons (labels under them).
        W, H = SU_W, SU_H
        sc = 2
        colw, rowh = FRAME_W * sc, FRAME_H * sc
        x0, row_y = 16 + colw + 16, H - 18 - 12 - rowh # The labels under the buttons end 10 pixels above the bottom edge.
        return dict(sc=sc, colw=colw, rowh=rowh, x0=x0, y0=self._champ_banner_h() + 10, w=W - 16 - x0, bot=row_y - 50, row_y=row_y)

    def _champ_art_button(self, s, hits, vx, vy, name, idx, sc, x, y, tag, selected=False, fb_label="", label=None): # Framed picture button (3.VGA + 24 / 25.VGA); returns the frame rect.
        return self.framed_button(s, hits, vx, vy, name, idx, sc, x, y, tag, selected, label or fb_label)

    def _put_bold(self, txt, px, col, cy, left=None, cx=None, w=None): # Bold text: the same text drawn twice, one pixel apart (works with the bitmap font too).
        bd = self.board
        if w is not None:
            txt = self.fit_text(txt, px, w)
        img = bd.font(px).render(txt, True, col)
        if self._txt_shadow:
            sh = bd.font(px).render(txt, True, (0, 0, 0))
            for dx in (1, 2):
                bd.put(self.su_surf, sh, left=None if left is None else left + dx, cx=None if cx is None else cx + dx, cy=cy + 1)
        for dx in (0, 1):
            bd.put(self.su_surf, img, left=None if left is None else left + dx, cx=None if cx is None else cx + dx, cy=cy)

    def _champ_team_avg(self, t): # (Condition, Skill, Form) mean of the roster of team t; for the user's team the values the engine sees (tiredness, form).
        rows = [list(r)[:3] for r in (_get(self.teams[t], "stats") or [])[:cm.ROSTER]]
        if t == self.champ.user:
            top, sq = self._champ_top(), self.champ.squad
            rows = [list(sq.effective(i, r, top)) for i, r in enumerate(rows)]
        rows = [r for r in rows if len(r) == 3]
        return tuple(int(round(sum(r[k] for r in rows) / len(rows))) for k in range(3)) if rows else (0, 0, 0)

    def _champ_hub(self, s, hits, vx, vy):
        W, H, ch = SU_W, SU_H, self.champ
        g = self._champ_geom()
        sc, x0, fw, fh, gap = g["sc"], g["x0"], g["colw"], g["rowh"], 8
        if self.champ_team is not None and not 0 <= self.champ_team < len(self.teams):
            self.champ_team = None
        self._champ_banner(s)
        skin = min(self.champ_div, 2) # Left column: CLASSIFICA and CALENDARIO (always the same series, see ch_tab), then LA MIA SQUADRA (fixed picture of the user's series).
        y = g["y0"]
        self._champ_art_button(s, hits, vx, vy, "tab_table", skin, sc, 16, y, ("ch_tab", "table"), self.champ_tab == "table", ctr("tab_table") + " " + div_name(self.champ_div))
        self._champ_art_button(s, hits, vx, vy, "tab_cal", skin, sc, 16, y + fh + 10, ("ch_tab", "calendar"), self.champ_tab == "calendar", ctr("tab_cal") + " " + div_name(self.champ_div))
        extra = ctr("interrupted") if self.champ_paused else ctr("dirty") if self.champ_dirty else ""
        if extra:
            self._put(extra, 14, WARN, y + 2 * fh + 34, cx=16 + fw // 2, w=fw + 8)
        ys = g["bot"] - fh - 44
        self._champ_art_button(s, hits, vx, vy, "tab_squad", min(ch.user_div, 2), sc, 16, ys, ("ch_tab", "squad"), self.champ_tab == "squad", ctr("tab_squad"))
        mine = ctr("my_squad")
        for j, t in enumerate(mine.rsplit(" ", 1) if " " in mine else [mine]):
            self._put(t, 16, WHITE, ys + fh + 14 + j * 18, cx=16 + fw // 2, w=fw + 12)
        if self.champ_tab == "table":
            self._champ_table(s, hits, vx, vy)
        elif self.champ_tab == "calendar":
            self._champ_calendar(s, hits, vx, vy)
        else:
            self._champ_squad(s, hits, vx, vy)
        ry = g["row_y"]
        lab_cy = ry + fh + 12

        def btn(x, tag, name, label, selected=False): # Framed picture button with its text UNDER it (inside only when the picture is missing).
            self._champ_art_button(s, hits, vx, vy, name, 0, sc, x, ry, (tag,), selected, label)
            if self.art(name, 0, sc) is not None:
                self._put(label, 16, WHITE, lab_cy, cx=x + fw // 2, w=fw + 2 * gap - 2)

        def g_play(x):
            btn(x, "ch_season" if ch.finished else "ch_play", "play", ctr("next_season" if ch.finished else "play"))

        def g_sims(x):
            if self.champ_paused:
                btn(x, "ch_resume", "sim", ctr("resume"), True)
                return
            w = 3 * fw + 2 * gap
            self._put(ctr("grp_sim"), 16, GOLD, ry - 16, cx=x + w // 2, w=w)
            pygame.draw.line(s, GOLD, (x, ry - 6), (x + w, ry - 6), 1)
            for j, (tag, name, key) in enumerate((("ch_sim", "sim", "sim_n"), ("ch_fast", "fast", "sim_f"), ("ch_now", "now", "sim_i"))):
                btn(x + j * (fw + gap), tag, name, ctr(key))

        def g_save(x):
            btn(x, "ch_save", "save", ctr("save") + (" *" if self.champ_dirty else ""))
            btn(x + fw + gap, "ch_slots", "slot", ctr("slot"))

        def g_back(x):
            self.back_button(s, hits, vx, vy, x, ry, sc)

        groups = [(fw, g_play)]
        if not ch.finished:
            groups.append((fw if self.champ_paused else 3 * fw + 2 * gap, g_sims))
        groups += [(2 * fw + gap, g_save), (fw, g_back)]
        space = (W - 32 - sum(w for w, _f in groups)) / float(len(groups) - 1) # The groups are equally spaced along the row.
        x = 16.0
        for w, fn in groups:
            fn(int(x))
            x += w + space

    def _champ_squad(self, s, hits, vx, vy): # SQUADRA: every player of the user's team with his season record; click = shirt number, right click = bench. Another team: its players, read only.
        H, ch, g = SU_H, self.champ, self._champ_geom()
        sq = ch.squad
        td = self.teams[ch.user]
        shirts, bench = self._champ_squad_info()
        top = self._champ_top()
        x0, y0, tw = g["x0"], g["y0"], g["w"]
        fl = list(FORMATIONS) # One formation chip, just above the LA MIA SQUADRA button: a click cycles through the formations.
        fw_, fh_ = g["colw"], g["rowh"]
        chip = pygame.Rect(16, g["bot"] - fh_ - 44 - 27 - 8 + 4, fw_, 27)
        cur = fl.index(sq.formation) if sq.formation in fl else -1
        self.draw_chip(s, chip, sq.formation or "-", True, chip.collidepoint(vx, vy), TEAM_COL[0])
        hits.append((chip, ("sq_form", fl[(cur + 1) % len(fl)])))
        note = self.champ_note
        if not (note and time.time() < note[1] and len(note) > 3 and note[3]): # The hint gives way to the one-line message (lineup_short).
            txt = self.fit_text(ctr("sq_hint"), 15, tw)
            self._put(txt, 15, DIM, g["row_y"] - 16, left=SU_W - 16 - self.board.font(15).size(txt)[0])
        roles = [self.natural_pool(i) for i in range(cm.ROSTER)]
        gaps = [0] * cm.ROSTER # Extra pixels above each row: 2 more between one role group and the next.
        for i in range(1, cm.ROSTER):
            gaps[i] = gaps[i - 1] + (10 if roles[i] != roles[i - 1] else 0)
        rh = max(18, min(26, (g["bot"] - y0 - 4 - gaps[-1]) // (cm.ROSTER + 1)))
        px = max(14, min(20, rh - 4))
        cols = (("sq_games", 44), ("sq_cond", 46), ("sq_skill", 46), ("sq_form", 46), ("sq_goals", 44), ("sq_yellow", 44), ("sq_red", 44), ("sq_state", 150), ("sq_fat", 130))
        cx_list, xr = [], x0 + tw
        for key, w in reversed(cols):
            xr -= w
            cx_list.append((key, xr, w))
        cx_list.reverse()
        name_w = cx_list[0][1] - (x0 + 56) - 6
        for key, xx, w in cx_list:
            self._put(ctr(key), px, DIM, y0 + rh // 2, cx=xx + w // 2)
        self._put(ctr("lineup_n", n=len(shirts)), px, DIM if len(shirts) == 11 else WARN, y0 + rh // 2, left=x0 + 4, w=name_w) # Players named for the match.
        names = self._champ_player_names(ch.user)
        for i in range(cm.ROSTER):
            y = y0 + (i + 1) * rh + gaps[i]
            rr = pygame.Rect(x0, y, tw, rh - 2)
            if i and gaps[i] > gaps[i - 1]:
                line_y = y - 6
                pygame.draw.line(s, WHITE, (x0 + 10, line_y), (x0 + tw - 10, line_y), 3)
            rec = sq.p[i]
            skey, sleft, scol = self._champ_state(i, shirts, bench)
            avail = sq.available(i)
            _shade(s, rr, (70, 30, 30, 170) if not avail else (20, 40, 80, 190) if shirts.get(i) else (8, 12, 34, 150 if i % 2 == 0 else 105))
            if rr.collidepoint(vx, vy):
                pygame.draw.rect(s, (255, 255, 255), rr, 1, border_radius=3)
            cy = y + rh // 2 - 1
            role = roles[i]
            self._put(ROLE_TAG[role], px - 2, ROLE_COL[role], cy, cx=x0 + 14)
            if shirts.get(i):
                self._put(str(shirts[i]), px, WHITE, cy, cx=x0 + 40)
            self._put(names[i] or "-", px, WHITE if avail else (255, 160, 150), cy, left=x0 + 58, w=name_w)
            base = list(td["stats"][i])[:3]
            eff = sq.effective(i, base, top)
            vals = {"sq_games": rec["games"], "sq_goals": rec["goals"], "sq_yellow": rec["yellow"], "sq_red": rec["red"]}
            for key, xx, w in cx_list:
                if key in vals:
                    self._put(str(vals[key]), px, WHITE if vals[key] else DIM, cy, cx=xx + w // 2)
                elif key in ("sq_cond", "sq_skill", "sq_form"):
                    v = eff[("sq_cond", "sq_skill", "sq_form").index(key)]
                    self._put(str(v), px, stat_color(v), cy, cx=xx + w // 2)
                elif key == "sq_state":
                    self._put(ctr(skey) + (" (%d)" % sleft if sleft else ""), px, scol, cy, cx=xx + w // 2, w=w - 4)
                else: # fatigue bar
                    f = rec["fat"]
                    bar = pygame.Rect(xx + 6, y + 3, w - 50, rh - 8)
                    pygame.draw.rect(s, (30, 36, 70), bar, border_radius=3)
                    if f > 0:
                        pygame.draw.rect(s, (60 + int(1.9 * f), 210 - int(1.4 * f), 70), (bar.x, bar.y, max(3, bar.w * f // 100), bar.h), border_radius=3)
                    pygame.draw.rect(s, WHITE, bar, 1, border_radius=3)
                    self._put("%d%%" % f, px - 1, WHITE, cy, left=bar.right + 6)
            hits.append((rr, ("sq_num", i)))

    def _champ_roster(self, s, t, x0, y0, tw, bot): # Players of team t (role, name, Condition / Skill / Form); the user's team shows the values the engine sees.
        if self._champ_roles is None:
            self._champ_roles = {}
        if t not in self._champ_roles:
            with self._champ_ctx(0, t, copy.deepcopy(self.lineup[0]), self.form_names[0]):
                self._champ_roles[t] = [self.natural_pool(i) for i in range(cm.ROSTER)]
        roles, names = self._champ_roles[t], self._champ_player_names(t)
        st = [list(r)[:3] for r in (_get(self.teams[t], "stats") or [])[:cm.ROSTER]]
        if t == self.champ.user:
            top, sq = self._champ_top(), self.champ.squad
            st = [list(sq.effective(i, r, top)) for i, r in enumerate(st)]
        rh = max(16, min(26, (bot - y0) // (cm.ROSTER + 1)))
        px = max(13, min(20, rh - 4))
        vw = 46
        for n, key in enumerate(("c_cond", "c_skill", "c_form")):
            self._put(ctr(key), px, DIM, y0 + rh // 2, cx=x0 + tw - vw * (3 - n) + vw // 2)
        self._put_bold(self.champ_name(t), px + 4, GOLD, y0 + rh // 2, left=x0, w=tw - 3 * vw - 6)
        for i in range(cm.ROSTER):
            y = y0 + (i + 1) * rh
            _shade(self.su_surf, pygame.Rect(x0, y, tw, rh - 2), (8, 12, 34, 150 if i % 2 == 0 else 105))
            cy = y + rh // 2 - 1
            self._put(ROLE_TAG[roles[i]], px - 2, ROLE_COL[roles[i]], cy, cx=x0 + 12)
            self._put(names[i] or "-", px, WHITE, cy, left=x0 + 30, w=tw - 30 - 3 * vw - 4)
            for n, v in enumerate(st[i] if i < len(st) else [0, 0, 0]):
                self._put(str(v), px, stat_color(v), cy, cx=x0 + tw - vw * (3 - n) + vw // 2)

    def _champ_table(self, s, hits, vx, vy): # Table of the shown division on the left; next match / champion and last round on the right.
        ch, g = self.champ, self._champ_geom()
        d = self.champ_div
        rows = ch.standings(d)
        sel_t = self.champ_team if self.champ_team is not None else ch.user
        x0, y0 = g["x0"], g["y0"]
        tw = int(g["w"] * 0.58)
        cols = (("c_played", 34), ("c_won", 34), ("c_drawn", 34), ("c_lost", 34), ("c_gd", 42), ("c_pts", 40), ("c_cond", 38), ("c_skill", 38), ("c_form", 38))
        rh = max(16, min(30, (g["bot"] - y0) // (len(rows) + 1)))
        px = max(13, min(22, rh - 4))
        xr, xs = x0 + tw, []
        for key, w in reversed(cols):
            xr -= w
            xs.append((key, xr + w // 2))
        name_w = xr - (x0 + 44) - 6
        self._put(ctr("c_team"), px, DIM, y0 + rh // 2, left=x0 + 44)
        for key, cx in xs:
            self._put(ctr(key), px, DIM, y0 + rh // 2, cx=cx)
        for pos, row in enumerate(rows):
            y = y0 + (pos + 1) * rh
            me = row["team"] == ch.user
            _shade(s, pygame.Rect(x0, y, tw, rh - 2), (70, 60, 10, 190) if me else (8, 12, 34, 150 if pos % 2 == 0 else 105))
            col, put = (GOLD, self._put_bold) if me else (WHITE, self._put) # Your team is in bold.
            put(str(pos + 1), px, col, y + rh // 2, cx=x0 + 20)
            nr = pygame.Rect(x0 + 40, y, name_w + 8, rh - 2) # Click on the name: the players of that team.
            if nr.collidepoint(vx, vy):
                pygame.draw.rect(s, WHITE, nr, 1, border_radius=3)
            elif row["team"] == sel_t and not me:
                pygame.draw.rect(s, GOLD, nr, 1, border_radius=3)
            put(self.champ_name(row["team"]), px, col, y + rh // 2, left=x0 + 44, w=name_w)
            hits.append((nr, ("ch_team", row["team"])))
            avg = self._champ_team_avg(row["team"])
            vals = dict(c_played=row["played"], c_won=row["won"], c_drawn=row["drawn"], c_lost=row["lost"], c_gd="%+d" % row["gd"], c_pts=row["pts"],
                        c_cond=avg[0], c_skill=avg[1], c_form=avg[2])
            for key, cx in xs:
                put(str(vals[key]), px, stat_color(vals[key]) if key in ("c_cond", "c_skill", "c_form") else col, y + rh // 2, cx=cx)
        sel = self.champ_team if self.champ_team is not None else ch.user # Right: the players of the clicked team (the round and match info are in the calendar).
        self._champ_roster(s, sel, x0 + tw + 24, y0, g["w"] - tw - 24, g["bot"])

    def _champ_calendar(self, s, hits, vx, vy): # Left: every match of the user's team with its date; right: the whole round of the shown division.
        ch, g = self.champ, self._champ_geom()
        ud, d = ch.user_div, self.champ_div
        x0, y0, cw = g["x0"], g["y0"], int(g["w"] * 0.48)
        rh, nvis, cur = 22, self._champ_rows_visible(), ch.round_index()
        self._put(ctr("your_matches"), 16, DIM, y0 + 8, left=x0 + 4)
        place = {row["team"]: n + 1 for n, row in enumerate(ch.standings(ud))} # Current place of every team of the user's series.
        self._put(ctr("cal_hint"), 14, DIM, y0 + 8, left=x0 + cw - 210, w=210)
        for k in range(nvis):
            r = self.champ_scroll + k
            if r >= ch.total_rounds():
                break
            i = ch.user_slot(r)
            h, a = ch.rounds[ud][r][i]
            sc = ch.results[ud][r][i]
            y = y0 + 24 + k * rh
            rect = pygame.Rect(x0, y, cw, rh - 2)
            _shade(s, rect, (70, 60, 10, 200) if r == self.champ_round else (20, 44, 80, 190) if r == cur else (8, 12, 34, 150 if k % 2 == 0 else 100))
            if r == cm.WINTER_AFTER and ch.round_date(r): # The winter break sits just above this row.
                pygame.draw.line(s, GOLD, (x0, y - 1), (x0 + cw, y - 1), 1)
            home = h == ch.user
            opp = a if home else h
            res, col = "-", DIM
            if sc is not None:
                gf, gc = (sc[0], sc[1]) if home else (sc[1], sc[0])
                col = WON if gf > gc else DRAWN if gf == gc else LOST
                res = "%d-%d" % (sc[0], sc[1])
            cy = y + rh // 2 - 1
            self._put("%d" % (r + 1), 15, DIM, cy, cx=x0 + 16)
            self._put(self._champ_date(r, True), 14, DIM, cy, left=x0 + 34, w=56)
            self._put(ctr("home" if home else "away"), 15, DIM, cy, left=x0 + 96)
            self._put(self.champ_name(opp), 15, col if sc is not None else WHITE, cy, left=x0 + 128, w=cw - 128 - 58 - 78)
            if opp in place: # Place of the opponent in the table (always up to date): "3° posto".
                self._put_right(self._champ_place(place[opp]), 15, DIM, cy, x0 + cw - 62, 76)
            self._put(res, 15, col, cy, cx=x0 + cw - 30)
            hits.append((rect, ("ch_round", r)))
    
            rx, rw = x0 + cw + 24, g["w"] - cw - 24
            cx = rx + rw // 2
            
            self.blue_panel(s, pygame.Rect(rx, y0+60, rw, g["bot"] - y0-60))
            
            if ch.total_rounds() > 1: # LEFT / RIGHT arrows.
                fw, fh = int(FRAME_W * 1.5), int(FRAME_H * 1.5)
                for name, delta, lab, bx in (
                    ("arrow_left", -1, "<", rx),
                    ("arrow_right", 1, ">", rx + rw - fw),
                ):
                    ok = 0 <= self.champ_round + delta < ch.total_rounds()
                    r = self.framed_button(s, hits, vx, vy, name, 0, 1.5, bx, y0 + (32 - fh) // 2, ("ch_step", delta), False, lab, ok)
                    if not ok:
                        dim = pygame.Surface(r.size, pygame.SRCALPHA)
                        dim.fill((0, 0, 30, 150))
                        s.blit(dim, r)
    
        self._put(ctr("round", n=self.champ_round + 1, tot=ch.total_rounds()), 24, GOLD if self.champ_round == cur else WHITE, y0 + 16, cx=cx, w=rw - (2 * fw + 16) if ch.total_rounds() > 1 else rw)
    
        lines = [ln for ln in self._champ_round_lines(self.champ_round) if ln]
        for j, ln in enumerate(lines):
            self._put(ln, 15, DIM, y0 + 44 + j * 16, cx=cx, w=rw)
    
        top = y0 + 48 + max(1, len(lines)) * 16 + 4
        if self.champ_round < len(ch.rounds[d]):
            fx = ch.rounds[d][self.champ_round]
            lh = max(20, min(34, (g["bot"] - top) // max(1, len(fx))))
            for i, (h, a) in enumerate(fx):
                y = top + i * lh + lh // 2
                sc = ch.results[d][self.champ_round][i]
                col = GOLD if ch.user in (h, a) else WHITE
                px = max(13, min(20, lh - 8))
                half = (rw - 90) // 2
                for t, tr_ in ((h, pygame.Rect(cx - 36 - half, y - lh // 2, half + 6, lh)), (a, pygame.Rect(cx + 30, y - lh // 2, half + 6, lh))): # Click on a team: the table of the series with that team selected.
                    if tr_.collidepoint(vx, vy):
                        pygame.draw.rect(s, WHITE, tr_.inflate(0, -2), 1, border_radius=3)
                    hits.append((tr_, ("ch_goto", t, d)))
                self._put_right(self.champ_name(h), px, col, y, cx - 36, half)
                self._put("%d-%d" % tuple(sc) if sc is not None else "-", px, col, y, cx=cx)
                self._put(self.champ_name(a), px, col, y, left=cx + 36, w=half)

    def _champ_dry_panel(self, s): # Time bars of the simulated match, on top of the bottom of the page.
        W, H, d = SU_W, SU_H, self.champ_dry
        _shade(s, pygame.Rect(30, H - 140, W - 60, 126), (8, 12, 34, 235), 10)
        pygame.draw.rect(s, GOLD, (30, H - 140, W - 60, 126), 2, border_radius=10)
        mode, half = d["mode"], self.half
        f1 = 1.0 if half >= 2 or mode in ("half", "full") else (0.0 if mode == "walkon" else min(1.0, self.real_t / self.half_secs))
        f2 = 0.0 if half < 2 else (1.0 if mode == "full" else (0.0 if mode == "walkon" else min(1.0, self.real_t / self.half_secs)))
        phase = ctr("ph_walkon") if mode == "walkon" else ctr("ph_half") if mode == "half" else "%d'" % min(45 * half, int(self.minute()) + 1)
        speed = FAST_SPEEDS[self.champ_fast_idx]
        self._put(ctr("sim_fast_title", speed=speed) + (("   " + ctr("sim_eff", eff=int(d["eff"]))) if d["eff"] >= 1 else ""), 16, DIM, H - 124, left=46, w=W // 2 - 140)
        self._put("%s  %d - %d  %s" % (self.champ_name(d["h"]), self.score[0], self.score[1], self.champ_name(d["a"])), 24, WHITE, H - 120, cx=W // 2 + 60, w=W - 520)
        self._put(phase, 18, GOLD, H - 124, left=W - 46 - 140, w=140)
        for j, (key, f) in enumerate((("half1", f1), ("half2", f2))):
            y = H - 92 + j * 26
            self._put(ctr(key), 16, WHITE, y + 8, left=46)
            bar = pygame.Rect(170, y, W - 60 - 170 - 46 + 30, 16)
            pygame.draw.rect(s, (30, 36, 70), bar, border_radius=4)
            if f > 0:
                pygame.draw.rect(s, GOLD, (bar.x, bar.y, max(6, int(bar.w * f)), bar.h), border_radius=4)
            pygame.draw.rect(s, WHITE, bar, 1, border_radius=4)
        self._put(ctr("sim_cancel"), 14, DIM, H - 34, cx=W // 2)
