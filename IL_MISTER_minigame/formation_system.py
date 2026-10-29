import math

from game_utils import clamp, unit
from geometry import L, PITCH_W, V_TOP
from lang import tr
from match_config import TEAM_NAMES
from stats_system import rating


ROLE_K = {"GK": 0.0, "DEF": 0.55, "MID": 0.70, "FWD": 0.80} # Longitudinal home-position factors for each tactical role.
AGON_LINE_PUSH = {"GK": 0.0, "DEF": 0.10, "MID": 0.22, "FWD": 0.16} # Longitudinal shift of the home position between agonism 0 % and 100 %.
KEEP_OFF = 22.0 # Minimum distance an outfield player's home position should keep from the ball.
LAT_K = 0.28 # Lateral correction factor used when positioning players relative to the ball.
FORMATIONS = {} # Registry of available formations; each formation lists outfield players per line.
DEFAULT_FORMATION = "4-4-2" # Formation assigned when a team has no explicit formation choice.
ROLE_POOLS = {"GK": (0, 2), "DEF": (2, 7), "MID": (7, 15), "FWD": (15, 20)} # Player-index ranges eligible for each tactical role.
ROLE_ORDER = ("GK", "DEF", "MID", "FWD") # Order used when sorting or assigning tactical roles.
DEF_LINE_U, FWD_LINE_U = 0.13, 0.45 # Normalized longitudinal position of the defensive/forward line in a formation.
ZONE_U = {"GK": (0.0, 0.12), "DEF": (0.10, 0.58), "MID": (0.10, 0.92), "FWD": (0.22, 1.0)} # Allowed normalized longitudinal zone for each role.
DEF_MIN_U = 0.10 # Minimum normalized forward coordinate allowed for defenders.
WIDE_BONUS = 0.10 # Extra longitudinal zone width given to wide players in broad lines.
LANE_MARGIN = {1: 0.5, 2: 0.30, 3: 0.20, 4: 0.12, 5: 0.09, 6: 0.07} # Normalized lateral margin used to space players within a line of each size.
_SLOT_CACHE = {}


def register_formation(name, *lines): # Register a formation using the number of outfield players in each line.
    if sum(lines) != 10 or len(lines) < 2 or min(lines) < 1:
        raise ValueError("una formazione deve avere 10 giocatori di movimento in almeno 2 linee")
    FORMATIONS[name] = tuple(lines)
    _SLOT_CACHE.pop(name, None)


def formation_slots(name): # Build or retrieve the cached player slots for a formation.
    if name in _SLOT_CACHE:
        return _SLOT_CACHE[name]
    lines = FORMATIONS[name]
    slots = [dict(role="GK", u=0.035, w=0.5, zu=ZONE_U["GK"], zw=(0.30, 0.70))]
    n_l = len(lines)
    for k, n in enumerate(lines):
        role = "DEF" if k == 0 else "FWD" if k == n_l - 1 else "MID"
        u = DEF_LINE_U + (FWD_LINE_U - DEF_LINE_U) * k / float(n_l - 1)
        m = LANE_MARGIN.get(n, 0.5 / n)
        for i in range(n):
            w = 0.5 if n == 1 else m + (1.0 - 2.0 * m) * i / (n - 1)
            hw = 0.5 / n + 0.24
            zlo, zhi = clamp(w - hw, 0.03, 0.97), clamp(w + hw, 0.03, 0.97)
            if i == 0:
                zlo = 0.03
            if i == n - 1:
                zhi = 0.97
            ulo, uhi = ZONE_U[role]
            if n >= 5 and i in (0, n - 1):
                uhi = min(1.0, uhi + WIDE_BONUS)
            slots.append(dict(role=role, u=u, w=w, zu=(ulo, uhi), zw=(zlo, zhi)))
    _SLOT_CACHE[name] = slots
    return slots


def role_counts(name): # Count the goalkeeper, defender, midfielder, and forward slots in a formation.
    cnt = {r: 0 for r in ROLE_ORDER}
    for sl in formation_slots(name):
        cnt[sl["role"]] += 1
    return cnt


register_formation("4-4-2", 4, 4, 2)
register_formation("5-3-2", 5, 3, 2)
register_formation("3-5-2", 3, 5, 2)
register_formation("4-3-3", 4, 3, 3)
register_formation("4-5-1", 4, 5, 1)
register_formation("3-4-3", 3, 4, 3)


class FormationMixin: # Formation slots, tactical zones, roles, and player positioning.
    def team_uw(self, team, wx, wv): # Convert a team-relative position into world coordinates.
        u = wx / L if self.att[team] > 0 else 1.0 - wx / L
        return u, (wv - V_TOP) / PITCH_W

    def in_zone(self, p, wx, wv, mu=0.0, mw=0.0): # Check whether a player position is inside the assigned tactical zone.
        u, w = self.team_uw(p.team, wx, wv)
        return p.zu[0] - mu <= u <= p.zu[1] + mu and p.zw[0] - mw <= w <= p.zw[1] + mw

    def zone_clamp(self, p, wx, wv, mu=0.0, mw=0.0): # Clamp a target position to the player's assigned tactical zone.
        u, w = self.team_uw(p.team, wx, wv)
        u_min = p.zu[0] - mu
        if p.role == "DEF":
            u_min = max(u_min, DEF_MIN_U)
        u = clamp(u, u_min, p.zu[1] + mu)
        w = clamp(w, p.zw[0] - mw, p.zw[1] + mw)
        return (u * L if self.att[p.team] > 0 else (1.0 - u) * L), V_TOP + w * PITCH_W

    def home_pos(self, p, bx, bv, poss): # Calculate a player's home position from its role, slot, and possession state.
        d = self.att[p.team]
        bu = bx / L if d > 0 else 1 - bx / L
        bw = (bv - V_TOP) / PITCH_W
        u = p.base_u + p.drift[0] + (bu - 0.5) * ROLE_K[p.role]
        if p.role in ("MID", "FWD"):
            u += 0.06 if poss else -0.04
        u += (self.agon(p.team) - 0.5) * AGON_LINE_PUSH.get(p.role, 0.0) # Agonism: deep and compact at 0 %, high line at 100 %.
        u = clamp(u, p.zu[0], p.zu[1])
        w = clamp(p.base_w + p.drift[1] + (bw - 0.5) * (0.15 if p.role == "GK" else LAT_K), p.zw[0], p.zw[1])
        hx, hv = (u * L if d > 0 else (1 - u) * L), V_TOP + w * PITCH_W
        if p.role != "GK":
            if math.hypot(hx - bx, hv - bv) < KEEP_OFF:
                ux, uv = unit(hx - bx, hv - bv, (-d, 0.0))
                hx, hv = self.zone_clamp(p, bx + ux * KEEP_OFF, bv + uv * KEEP_OFF)
        return hx, hv

    def player_rating(self, t, i): # Mean of Fitness, Skill and Form of roster player i of team t.
        st = self.team_data[t].get("stats")
        return rating(st[i]) if st and i < len(st) else 0.0

    def auto_lineup(self, t): # Best players per role (highest Fitness/Skill/Form mean) for the current formation.
        need = role_counts(self.form_names[t])
        out, used = {}, set()
        for role in ROLE_ORDER:
            lo, hi = ROLE_POOLS[role]
            pool = sorted((i for i in range(lo, hi) if i not in used), key=lambda i: (-self.player_rating(t, i), i))
            out[role] = pool[:need[role]]
            used.update(out[role])
        return out

    def fix_lineup(self, t, reset=False): # Repair a lineup, or rebuild it with the best players when reset is true.
        if reset or self.lineup[t] is None:
            self.lineup[t] = self.auto_lineup(t)
            return
        need = role_counts(self.form_names[t])
        cur, out, used = self.lineup[t], {}, set()
        for role in ROLE_ORDER:
            keep = []
            for i in cur.get(role, []):
                if len(keep) < need[role] and (i is None or i not in used):
                    keep.append(i)
                    if i is not None:
                        used.add(i)
            out[role] = keep + [None] * (need[role] - len(keep))
        if self.mode != "intro": # In INTRO empty slots are left empty (the screen warns); during a match they are always filled.
            for role in ROLE_ORDER:
                lo, hi = ROLE_POOLS[role]
                pool = sorted((i for i in range(lo, hi) if i not in used), key=lambda i: (-self.player_rating(t, i), i))
                for k, i in enumerate(out[role]):
                    if i is None and pool:
                        out[role][k] = pool.pop(0)
                        used.add(out[role][k])
        self.lineup[t] = out

    def lineup_count(self, t): # Number of shirts (1-11) assigned to a player.
        return sum(1 for _r, i in self.lineup_slots(t) if i is not None)

    def lineup_ready(self): # Both teams have all 11 starters.
        return self.lineup_count(0) == 11 and self.lineup_count(1) == 11

    def lineup_slots(self, t): # Return the formation slots assigned to the current lineup.
        if self.lineup[t] is None:
            self.fix_lineup(t)
        return [(r, i) for r in ROLE_ORDER for i in self.lineup[t][r]]

    def lineup_names(self, t): # Return the display names of the current lineup roles.
        pl = self.team_data[t]["players"]
        return [pl[i] if i is not None and i < len(pl) else "" for _r, i in self.lineup_slots(t)]

    def sync_teams(self): # Synchronize each team's formation and role data with its players.
        self.team_data = [self.teams[self.sel[0]], self.teams[self.sel[1]]]
        TEAM_NAMES[:] = [self.team_data[0]["name"].upper(), self.team_data[1]["name"].upper()]

    def set_formation(self, team, name, quiet=False): # Apply the named formation to a team.
        if name not in FORMATIONS:
            return
        self.form_names[team] = name
        self.fix_lineup(team, reset=(self.mode == "intro")) # In INTRO the best players are picked again for the new shape.
        self.su_pick = None
        _SLOT_CACHE.pop(name, None)
        if self.mode == "intro":
            return
        slots = formation_slots(name)
        for p in self.team_p[team]:
            p.apply_slot(slots[p.idx])
            p.roam = False
        if not quiet:
            self.say(tr("msg.formation", team=TEAM_NAMES[team], name=name), (255, 255, 255), 2.5)
        if self.mode == "restart" and self.restart and self.restart["kind"] == "kickoff":
            self.setup_kickoff(self.restart["team"], sound=False, walk=True)

    def change_formation(self, team, delta): # Move to the next or previous available formation.
        names = list(FORMATIONS)
        i = names.index(self.form_names[team]) if self.form_names[team] in names else 0
        self.set_formation(team, names[(i + delta) % len(names)])
