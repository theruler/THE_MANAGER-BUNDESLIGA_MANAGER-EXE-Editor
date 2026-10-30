import math
import random
import time

from ball_model import G, step_ball_physics
from formation_system import ROLE_ORDER
from game_utils import clamp, unit
from geometry import BOX_D, BOX_V0, BOX_V1, GOAL_H, HALF_MOUTH, L, PITCH_W, POST_T, seg_dist, V_BOT, V_GC, V_TOP
from lang import tr
from physics_system import KEEPER_CATCH_HEIGHT, PLAYER_CATCH_RADIUS
from stats_system import norm


SAVE_HORIZON = 1.5 # Seconds ahead scanned for a loose ball leaving over a touchline.
SAVE_REACTION = 0.12 # Seconds a player needs before starting to run for a ball.
SAVE_SLACK = 0.10 # A player counts as able to reach the ball if he is at most this late.
SAVE_MAX_RUN = 55.0 # Longest run (world units) a player will attempt for a ball.
SAVE_MAX_HEIGHT = 9.0 # Balls higher than this when they cross the line are out of reach.
SELECT_LOOKAHEAD = 0.35 # Seconds of ball travel considered when auto-selecting the player nearest to a loose ball.
IDLE_AI = 2.5 # Seconds without manual input before automatic player selection resumes.
MARK_R, MARK_DIST, MAX_MARK = 45.0, 9.0, 2 # MARK_R: marking search radius; MARK_DIST: marking offset; MAX_MARK: max defenders per target.
LEASH_U, LEASH_W = 0.08, 0.11 # Maximum extra longitudinal/lateral movement beyond a player's tactical zone.
MARK_MOVE_THRESHOLD = 1.5 # Target movement required before a man-marker updates its destination.
MARK_STICKY_MARGIN = 12.0 # Extra distance allowed to keep an existing marking assignment stable.
GK_DRIBBLE_CHALLENGE_DISTANCE = 28.0 # Maximum goal depth at which the goalkeeper challenges a dribbler.
GK_DRIBBLE_CHALLENGE_RADIUS = 23.0 # Maximum goalkeeper-to-carrier distance for a challenge.
GK_DRIBBLE_CHALLENGE_CHANCE = 0.84 # Base probability that a goalkeeper wins a dribble challenge.
LONG_SHOT_FROM, LONG_SHOT_TO = 105.0, 170.0 # Distance band (to the goal) of long shots: only taken from beyond the normal shooting range.
LONG_SHOT_PROB = 0.07 # Chance per AI decision of a long shot at Skill 10 (about 0.2 of that at Skill 99).
BICYCLE_MIN_Z = 9.0 # Ball height from which a bicycle kick is an option (otherwise a plain header).
DIVE_HEADER_MIN, DIVE_HEADER_MAX = 10.0, 22.0 # Distance band from which a player may throw himself at the ball for a diving header.
DIVE_HEADER_REACH = 17.0 # The ball (0.2 s ahead) must pass within this distance of the diver.
AERIAL_BACK_MAX = 0.35 # A headed pass may not point more than this (cosine) back toward where the ball came from.
AERIAL_CLEAR_DIST = 70.0 # Distance of the fallback clearance target when no teammate is usable.
AERIAL_EDGE = 25.0 # Distance from a touchline inside which a header is never aimed toward that touchline.
LONG_PASS_FROM, LONG_PASS_FULL = 110.0, 170.0 # Passes beyond LONG_PASS_FROM are 'long', fully weighted at LONG_PASS_FULL.
LONG_PASS_BIAS = 40.0 # Score bonus for a long pass at Skill 99; at Skill 10 the same pass is penalised by this much.
FWD_RUN_BASE, FWD_RUN_SKILL = 0.35, 0.60 # Chance per decision that a forward makes an advanced run while his team has the ball: 0.35 at Skill 10, 0.95 at Skill 99.
FWD_LEAD_MIN, FWD_LEAD_MAX = 40.0, 75.0 # How far ahead of the ball carrier (world units) a forward runs; scaled by 0.6 (Skill 10) .. 1.0 (Skill 99).
FWD_GOAL_MARGIN = 24.0 # Forwards never run closer than this to the goal line.
FWD_SIDE = 0.22 # Lateral offsets (fraction of the pitch width) tried to find free space.
GK_DRIBBLE_RETRY_SECS = 0.38 # Simulated seconds between failed goalkeeper challenge attempts.


class AIMixin: # AI decisions for player selection, tactics, goalkeepers, restarts, and attacks.
    def waits_for_pass(self, p): # Return whether the controlled player should hold position for an incoming pass.
        if self.user_team is None or p.team != self.user_team:
            return False
        b = self.ball
        if b.owner is None and b.intended is p and b.last is not None and b.last.team == p.team:
            return math.hypot(b.wx - p.wx, b.wv - p.wv) > 10.0
        for q in self.team_p[p.team]:
            a = q.act
            if (q is not p and q.state == "action" and a is not None and a["key"] == "kick"
                    and not a["resolved"] and a["kw"].get("target") is p):
                return True
        return False

    def check_overlap_steal(self): # Check whether a nearby opponent can win possession through an automatic close-range steal.
        b = self.ball
        o = b.owner
        if self.mode != "play" or o is None or o.role == "GK" or o.state in ("out", "leaving") or o.fallen():
            self.ov_set.clear()
            self._gk_dribble_attempted = None
            return
        goal_dir = self.att[o.team]
        goal_x = L if goal_dir > 0 else 0.0
        goal_dist = (goal_x - o.wx) * goal_dir
        in_goal_lane = (-1.0 <= goal_dist <= GK_DRIBBLE_CHALLENGE_DISTANCE
                        and abs(o.wv - V_GC) <= HALF_MOUTH + 8.0)
        challenge_key = (id(o), 1 - o.team)
        attempt_state = self._gk_dribble_attempted
        retry_due = not (
            isinstance(attempt_state, tuple) and len(attempt_state) == 2
            and attempt_state[0] == challenge_key and self.t_all < attempt_state[1]
        )
        if not in_goal_lane:
            self._gk_dribble_attempted = None
        elif retry_due:
            keepers = [q for q in self.team_p[1 - o.team]
                       if q.role == "GK" and q.state == "free" and q.cool <= 0
                       and not q.red and not q.busy()]
            if keepers:
                keeper = min(keepers, key=lambda q: math.hypot(q.wx - o.wx, q.wv - o.wv))
                if math.hypot(keeper.wx - o.wx, keeper.wv - o.wv) <= GK_DRIBBLE_CHALLENGE_RADIUS:
                    self._gk_dribble_attempted = (challenge_key, self.t_all + GK_DRIBBLE_RETRY_SECS)
                    chance = clamp(GK_DRIBBLE_CHALLENGE_CHANCE + (keeper.skill - 0.7) * 0.25,
                                   0.78, 0.92)
                    if random.random() < chance:
                        o.cool = 0.55
                        self.give_ball(keeper)
                        self.audio.play("tackle", 0.9)
                        self.audio.react("save")
                        self.log_event(tr("ev.save", p=keeper.label()), secs=2.0, team=keeper.team)
                        return
        near = set()
        for q in self.team_p[1 - o.team]:
            if q.role == "GK" or q.state != "free" or q.cool > 0 or q.red:
                continue
            d = math.hypot(q.wx - o.wx, q.wv - o.wv)
            if d < 8.0:
                near.add(id(q))
            if d < 4.4 and id(q) not in self.ov_set:
                self.ov_set.add(id(q))
                if random.random() < 0.25:
                    o.cool = 0.55
                    self.give_ball(q)
                    self.audio.play("tackle", 0.7)
                    self.audio.react("tackle")
                    return
        self.ov_set &= near


    def select_nearest(self, team, exclude=None): # Select the eligible outfield player closest to the current ball position.
        b = self.ball
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving") and p is not exclude and p.role != "GK"]
        if c:
            self.select_player(min(c, key=lambda p: math.hypot(p.wx - b.wx, p.wv - b.wv)), quiet=True)

    def sel_candidates(self, team, at=None): # Return eligible player candidates ordered by distance to a point (default: the ball).
        b = self.ball
        ax, av = at if at is not None else (b.wx, b.wv)
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving", "subin", "subout", "tunnel")
             and not p.red and (p.role != "GK" or b.owner is p)]
        return sorted(c, key=lambda p: math.hypot(p.wx - ax, p.wv - av))

    def auto_select(self): # Update automatic player selection while respecting user control and pass reception.
        ut = self.user_team
        if ut is None or self.mode in ("intro", "half", "full"):
            return
        b = self.ball
        if self.mode == "play" and b.owner is None and b.intended is not None and b.intended.team == ut \
                and b.intended.state not in ("out", "leaving") and not b.intended.red:
            if self.cp is not b.intended:
                self.select_player(b.intended, quiet=True)
            self.sel_hold_until = 0.0
            return
        if self.cp is None and self.mode in ("play", "restart", "outball"):
            self.select_nearest(ut)
            return
        if self.mode != "play" or time.time() < self.sel_hold_until:
            return
        cp = self.cp
        if self.charge is not None or self.drag or (cp is not None and cp.state != "free"):
            return
        if cp is not None and b.owner is cp:
            return
        # A loose ball is judged by where it will be shortly, so the cursor jumps to the receiver before the ball arrives.
        ax, av = self.ball_pred(SELECT_LOOKAHEAD) if b.owner is None else (b.wx, b.wv)
        c = self.sel_candidates(ut, (ax, av))
        if not c:
            return
        near = c[0]
        if near is not cp:
            dn = math.hypot(near.wx - ax, near.wv - av)
            dc = math.hypot(cp.wx - ax, cp.wv - av) if cp is not None else 1e9
            if dc > dn + 6.0:
                self.select_player(near, quiet=True)


    def ai_update(self, dt): # Advance AI movement and decisions for eligible players.
        self.role_timer -= dt
        if self.role_timer <= 0:
            self.role_timer = 0.12
            if self.mode in ("play", "restart"):
                self.assign_roles()
        m = self.mode
        b = self.ball
        for p in self.players:
            if p.state in ("out", "action", "leaving", "cele", "down", "subout", "subin"):
                continue
            if m in ("play", "restart") and p.state == "free" and self.waits_for_pass(p):
                p.tx = p.tv = None
                continue
            receiving = b.owner is None and b.intended is p
            if p.ctrl and self.idle_t < IDLE_AI and not p.path:
                continue
            if p.path:
                if m in ("play", "restart") and p.state == "free" and not (m == "restart" and self.restart and self.restart["taker"] is p):
                    if not receiving and self.follow_path(p):
                        continue
                elif m in ("goal", "half", "full"):
                    p.path = None
            if m == "play":
                self.ai_play(p, dt)
            elif m == "restart":
                self.ai_restart(p, dt)
            elif m in ("foul", "half", "full", "subs", "injury"):
                p.tx = p.tv = None
            if p.dec > 0 and m != "play":
                p.dec -= dt

    def mark_pos(self, p, o): # Calculate a marking position around the assigned opponent.
        target_id = id(o)
        last_id = getattr(p, "_mark_target_id", None)
        anchor = getattr(p, "_mark_target_anchor", None)
        held_pos = getattr(p, "_mark_target_pos", None)
        if last_id == target_id and anchor is not None and held_pos is not None:
            if math.hypot(o.wx - anchor[0], o.wv - anchor[1]) < MARK_MOVE_THRESHOLD:
                return held_pos

        own_goal_x = 0.0 if self.att[p.team] > 0 else L
        ux, uv = unit(own_goal_x - o.wx, V_GC - o.wv)
        target_pos = (o.wx + ux * MARK_DIST, o.wv + uv * MARK_DIST)
        p._mark_target_id = target_id
        p._mark_target_anchor = (o.wx, o.wv)
        p._mark_target_pos = target_pos
        return target_pos

    def ball_exit_forecast(self): # Where/when a loose ball will cross a touchline within SAVE_HORIZON, else None (cached per frame).
        if getattr(self, "_exit_key", None) == self.t_all:
            return self._exit_val
        b, val = self.ball, None
        if b.owner is None and self.mode == "play":
            for i in range(1, int(SAVE_HORIZON / 0.1) + 1):
                t = i * 0.1
                x, v = self.ball_pred(t)
                if 0.0 < x < L and (v < V_TOP or v > V_BOT):
                    z = b.z + b.vz * t - 0.5 * G * t * t if (b.z > 0.5 or b.vz > 0.0) else 0.0
                    if z <= SAVE_MAX_HEIGHT:
                        val = dict(t=t, x=x, v=v)
                    break
        self._exit_key, self._exit_val = self.t_all, val
        return val

    def assign_savers(self): # Send one player per team to the spot where a ball leaving over a touchline can still be kept in play.
        fc = self.ball_exit_forecast()
        if fc is None:
            return
        b = self.ball
        for team in (0, 1):
            best = None
            for p in self.team_p[team]:
                if p.role == "GK" or p.state != "free" or p.ctrl or p.red or p is b.intended:
                    continue
                for i in range(1, int(fc["t"] / 0.1) + 1):
                    t = i * 0.1
                    x, v = self.ball_pred(t)
                    v = clamp(v, V_TOP + 1.0, V_BOT - 1.0)
                    run = math.hypot(x - p.wx, v - p.wv)
                    need = run / p.speed + SAVE_REACTION
                    if need <= t + SAVE_SLACK:
                        if run <= SAVE_MAX_RUN and (best is None or need < best[0]):
                            best = (need, p, (x, v, t))
                        break
            if best is not None:
                best[1].tag, best[1].roam, best[1].save_pt = "save", True, best[2]

    def ai_save_ball(self, p): # Run to the interception point; normal ball control takes over on arrival.
        p.tx, p.tv = p.save_pt[0], p.save_pt[1]

    def assign_roles(self): # Rebuild tactical roles and opponent-marking assignments for both teams.
        old = {id(p): p.tag for p in self.players}
        self._assign_roles0()
        if self.mode == "play":
            self.assign_savers()
        for p in self.players:
            if p.role == "GK":
                continue
            if old[id(p)] is not None and p.tag is None:
                p.new_drift()
            p.drift_t -= 0.12
            p.swap_cd -= 0.12
            if p.drift_t <= 0 and p.tag is None and self.mode != "restart":
                p.new_drift()
        if self.mode == "play":
            for team in (0, 1):
                self.fluid_swaps(team)

    def slot_xy(self, p, slot): # Convert a formation slot into its current world-space position.
        d = self.att[p.team]
        return (slot["u"] * L if d > 0 else (1 - slot["u"]) * L), V_TOP + slot["w"] * PITCH_W

    def fluid_swaps(self, team): # Smoothly exchange assignments when teammates need to swap tactical positions.
        ps = [p for p in self.team_p[team] if p.role != "GK" and p.state == "free" and not p.ctrl and p.tag in (None, "support")
              and p.swap_cd <= 0 and not p.red]
        best = None
        for i, a in enumerate(ps):
            sa = dict(role=a.role, u=a.base_u, w=a.base_w, zu=a.zu, zw=a.zw)
            for b2 in ps[i + 1:]:
                if abs(ROLE_ORDER.index(a.role) - ROLE_ORDER.index(b2.role)) > 1:
                    continue
                sb = dict(role=b2.role, u=b2.base_u, w=b2.base_w, zu=b2.zu, zw=b2.zw)
                ax, av = self.slot_xy(a, sa)
                bx, bv = self.slot_xy(b2, sb)
                cur = math.hypot(a.wx - ax, a.wv - av) + math.hypot(b2.wx - bx, b2.wv - bv)
                swp = math.hypot(a.wx - bx, a.wv - bv) + math.hypot(b2.wx - ax, b2.wv - av)
                if cur - swp > 14.0 and swp < cur * 0.72 and (best is None or cur - swp > best[0]):
                    best = (cur - swp, a, b2)
        if best:
            _g, a, b2 = best
            for att in ("role", "base_u", "base_w", "zu", "zw"):
                va, vb = getattr(a, att), getattr(b2, att)
                setattr(a, att, vb)
                setattr(b2, att, va)
            a.swap_cd = b2.swap_cd = random.uniform(7.0, 14.0)
            a.new_drift(0.6)
            b2.new_drift(0.6)

    def _assign_roles0(self): # Recalculate the base role and marking assignments.
        b = self.ball
        own = b.owner
        rs = self.restart if self.mode == "restart" else None
        previous_marks = [(p, p.mark) for p in self.players if p.tag == "mark" and p.mark is not None]
        for p in self.players:
            p.tag, p.roam, p.mark = None, False, None
        if rs is not None and rs["kind"] == "kickoff":
            return
        has = rs["team"] if rs is not None else (own.team if own is not None else None)
        if own is not self._gk_press_owner:
            self._gk_press_owner = own
            self._gk_press_idx = None
            if own is not None and own.role == "GK":
                forwards = [q for q in self.team_p[1 - own.team] if q.role == "FWD" and q.state == "free" and not q.ctrl]
                if forwards and random.random() < 0.18:
                    self._gk_press_idx = min(forwards, key=lambda q: math.hypot(q.wx - own.wx, q.wv - own.wv)).idx
        for team in (0, 1):
            cands = [p for p in self.team_p[team] if p.role != "GK" and not p.ctrl and p.state == "free" and p is not own
                     and not (rs is not None and p is rs["taker"])]
            if has == team:
                if own is not None and rs is None:
                    near = [p for p in cands if self.in_zone(p, own.wx, own.wv, 0.14, 0.18)]
                    for p in sorted(near, key=lambda q: math.hypot(q.wx - own.wx, q.wv - own.wv))[:2]:
                        p.tag = "support"
                continue
            if rs is not None:
                px, pv = rs["pos"]
            else:
                px, pv = (own.wx, own.wv) if own is not None else self.ball_pred(0.25)
            if own is not None and own.role == "GK" and team != own.team:
                for defender in cands:
                    if defender.idx == self._gk_press_idx and defender.role == "FWD":
                        defender.tag = "chase"
                        defender.roam = True
                    else:
                        defender.tx, defender.tv = self.home_pos(defender, own.wx, own.wv, False)
                continue
            preserved_targets = set()
            if rs is None:
                for marker, target in previous_marks:
                    if marker not in cands or target is own or target.team == team or target.role == "GK":
                        continue
                    if target.state in ("out", "leaving", "subin", "subout", "tunnel") or target.red:
                        continue
                    if id(target) in preserved_targets:
                        continue
                    if math.hypot(target.wx - px, target.wv - pv) > MARK_R + MARK_STICKY_MARGIN:
                        continue
                    marker.tag, marker.mark = "mark", target
                    cands.remove(marker)
                    preserved_targets.add(id(target))
            pool = list(cands)
            if rs is None:
                elig = [p for p in cands if self.in_zone(p, px, pv, 0.05, 0.08)]
                roam = not elig
                sc = sorted(elig or cands, key=lambda q: math.hypot(q.wx - px, q.wv - pv) / q.speed)
                if sc:
                    sc[0].tag, sc[0].roam = "chase", roam
                    pool.remove(sc[0])
                if len(sc) > 1:
                    d1 = math.hypot(sc[1].wx - px, sc[1].wv - pv)
                    if own is None and d1 < 14 * self.agon_mul(team, 0.5, 1.6):
                        sc[1].tag, sc[1].roam = "chase", roam
                        pool.remove(sc[1])
                    elif own is not None and self.team_uw(team, px, pv)[0] < 0.35 * self.agon_mul(team, 0.55, 1.5):
                        sc[1].tag, sc[1].roam = "cover", roam
                        pool.remove(sc[1])
            if rs is not None:
                continue
            targets = [o for o in self.opponents(team) if o.role != "GK" and o is not own
                       and id(o) not in preserved_targets
                       and math.hypot(o.wx - px, o.wv - pv) <= MARK_R]
            targets.sort(key=lambda o: math.hypot(o.wx - px, o.wv - pv))
            for o in targets[:MAX_MARK]:
                best = None
                for p in pool:
                    c = math.hypot(p.wx - o.wx, p.wv - o.wv) + (0.0 if self.in_zone(p, o.wx, o.wv, 0.10, 0.12) else 70.0)
                    if best is None or c < best[0]:
                        best = (c, p)
                if best and best[0] < 110.0:
                    best[1].tag, best[1].mark = "mark", o
                    pool.remove(best[1])

    def ai_play(self, p, dt): # Run the AI decision cycle for one player.
        self._ai_play(p, dt)
        b = self.ball
        if p.role == "GK" or b.owner is p or p.roam or p.tx is None or (b.owner is None and b.intended is p):
            return
        p.tx, p.tv = self.zone_clamp(p, p.tx, p.tv, LEASH_U, LEASH_W)

    def _ai_play(self, p, dt): # Resolve the player's current movement, support, and possession decisions.
        b = self.ball
        if p.role == "GK":
            return self.ai_keeper(p, dt)
        if b.owner is p:
            return self.ai_owner(p, dt)
        own = b.owner
        d = self.att[p.team]
        poss = own is not None and own.team == p.team
        if own is None and b.intended is p:
            T = clamp(math.hypot(b.wx - p.wx, b.wv - p.wv) / p.speed, 0.1, 1.4)
            if b.z > 3:
                T = min(T, self.land_time() + 0.05)
            p.tx, p.tv = self.ball_pred(T)
            self.ai_aerial(p)
            return
        tag = p.tag
        if own is None:
            if tag == "save" and getattr(p, "save_pt", None) is not None:
                self.ai_save_ball(p)
            elif tag == "chase":
                dist = math.hypot(b.wx - p.wx, b.wv - p.wv)
                T = clamp(dist / p.speed * 0.8, 0.05, 0.9)
                if b.z > 3:
                    T = min(max(T, 0.2), self.land_time() + 0.05)
                p.tx, p.tv = self.ball_pred(T)
                self.ai_aerial(p)
            elif tag == "mark" and p.mark is not None:
                p.tx, p.tv = self.mark_pos(p, p.mark)
            else:
                p.tx, p.tv = self.home_pos(p, b.wx, b.wv, b.last_team == p.team)
            return
        if poss:
            if p.role == "FWD":
                return self.fwd_run(p, own, d, dt)
            p.dec -= dt
            if tag == "support":
                if p.dec <= 0 or p.tx is None:
                    p.dec = random.uniform(0.6, 1.2)
                    side = 1.0 if p.idx % 2 else -1.0
                    sx = own.wx + d * random.uniform(40, 70)
                    sv = own.wv + side * random.uniform(0.18, 0.36) * PITCH_W # Lateral spacing scales with the (narrow) pitch width.
                    p.tx, p.tv = clamp(sx, 6.0, L - 6.0), clamp(sv, V_TOP + 3, V_BOT - 3)
            else:
                p.tx, p.tv = self.home_pos(p, b.wx, b.wv, True)
            return

        ogx = 0.0 if d > 0 else L
        if tag == "chase":
            dd = math.hypot(own.wx - p.wx, own.wv - p.wv)
            p.tx, p.tv = own.wx + own.dx * 3.0, own.wv + own.dv * 3.0
            p.dec -= dt
            gk_hold = own.role == "GK"
            if dd < 13.0 * self.agon_mul(p.team, 0.85, 1.25) and p.dec <= 0 and p.cool <= 0 and p.act_cd <= 0 and not own.fallen() and (not gk_hold or random.random() < 0.03 * p.aggr):
                p.dec = random.uniform(0.4, 0.9) * self.agon_mul(p.team, 1.4, 0.7) # Agonism: how often he tries.
                ux, uv = unit(own.wx - p.wx, own.wv - p.wv)
                r = random.random()
                stand_p = 0.32 * self.agon_mul(p.team, 0.75, 1.35)
                slide_p = (0.08 + 0.14 * p.aggr) * 2.0 * self.agon(p.team) # None at 0 %, the original odds at 50 %, double at 100 %.
                if r < stand_p:
                    self.start_tackle(p, ux, uv, "stand")
                elif dd > 7.5 and r < stand_p + slide_p:
                    self.start_tackle(p, ux, uv, "slide")
        elif tag == "cover":
            ux, uv = unit(ogx - own.wx, V_GC - own.wv)
            p.tx, p.tv = own.wx + ux * 26.0, own.wv + uv * 26.0
        elif tag == "mark" and p.mark is not None:
            p.tx, p.tv = self.mark_pos(p, p.mark)
        else:
            hx, hv = self.home_pos(p, b.wx, b.wv, False)
            if p.role in ("DEF", "MID"):
                thr = None
                for o in self.opponents(p.team):
                    if o.role == "GK" or o is own:
                        continue
                    if math.hypot(o.wx - hx, o.wv - hv) < 42 and (o.wx - p.wx) * d >= -12:
                        if thr is None or math.hypot(o.wx - hx, o.wv - hv) < math.hypot(thr.wx - hx, thr.wv - hv):
                            thr = o
                if thr is not None:
                    ux, uv = unit(ogx - thr.wx, V_GC - thr.wv)
                    hx = hx * 0.35 + (thr.wx + ux * 7.0) * 0.65
                    hv = hv * 0.35 + (thr.wv + uv * 7.0) * 0.65
            p.tx, p.tv = hx, hv


    def fwd_run(self, p, own, d, dt): # A forward of the team in possession gets ahead of the ball and into free space, to be a target for long balls.
        p.dec -= dt
        if p.dec > 0 and p.tx is not None:
            return
        p.dec = random.uniform(0.6, 1.2)
        skl = norm(self.pstats(p)[1])
        hx, hv = self.home_pos(p, self.ball.wx, self.ball.wv, True)
        if random.random() > (FWD_RUN_BASE + FWD_RUN_SKILL * skl) * self.agon_mul(p.team, 0.65, 1.35): # Agonism: propensity to run forward.
            p.tx, p.tv = hx, hv
            return
        goalx = L if d > 0 else 0.0
        ahead = own.wx + d * random.uniform(FWD_LEAD_MIN, FWD_LEAD_MAX) * (0.6 + 0.4 * skl)
        tx = max(hx, ahead) if d > 0 else min(hx, ahead)
        tx = min(tx, goalx - FWD_GOAL_MARGIN) if d > 0 else max(tx, goalx + FWD_GOAL_MARGIN)
        opp = self.opponents(p.team)
        cands = [clamp(hv + k * FWD_SIDE * PITCH_W, V_TOP + 3, V_BOT - 3) for k in (0.0, -1.0, 1.0)]
        free = lambda v: min([math.hypot(o.wx - tx, o.wv - v) for o in opp] or [99.0])
        tv = max(cands, key=free) if random.random() < skl else random.choice(cands) # Skilled forwards find the free spot.
        p.tx, p.tv = self.zone_clamp(p, tx, tv, 0.12, 0.2)

    def ai_keeper(self, p, dt): # Choose goalkeeper positioning, shot response, and distribution behaviour.
        b = self.ball
        d = self.att[p.team]
        own_x = 0.0 if d > 0 else L
        if b.owner is p:
            p.hold_t += dt
            p.tx = p.tv = None
            if p.hold_t > (0.7 if getattr(p, "feet", False) else 2.5): # Back-pass: no time to hold the ball with the feet.
                self.gk_distribute(p)
            return
        toward = -d * b.vx
        p.alert = False
        if b.owner is None and self.keeper_threat(p) and toward > 25 and (b.wx - own_x) * d > 0: # Also a team-mate's shot towards his own goal.
            fc = self.ball_forecast(own_x)
            if fc is not None and abs(fc["v"] - V_GC) < HALF_MOUTH + POST_T + 16.0 and fc["z"] < GOAL_H + 8.0:
                kt = self.t_all - b.age
                if abs(getattr(p, "gk_kt", -9.0) - kt) > 0.05:
                    p.gk_kt = kt
                    p.gk_err = random.gauss(0.0, 1.0) * (1.0 - p.skill) * 4.5 * (1.0 - 0.8 * self.keeper_reading())
                T = fc["t"]
                tv = clamp(fc["v"] + p.gk_err, V_GC - HALF_MOUTH - 3.0, V_GC + HALF_MOUTH + 3.0)
                if b.pen and not b.pen_save:
                    side = 1.0 if fc["v"] >= V_GC else -1.0
                    tv = V_GC - side * HALF_MOUTH * 0.55
                p.alert = True
                p.tx, p.tv = own_x + d * 3.0, tv
                need = abs(tv - p.wv)
                high = fc["z"] > KEEPER_CATCH_HEIGHT - 2.0
                if not p.busy() and p.act_cd <= 0:
                    lead = 0.12 * self.keeper_reading() # Well-read shots: the keeper commits earlier.
                    if (need > 3.5 and T < 0.30 + lead + min(0.14, need * 0.010)) or (high and T < 0.30 + lead) or T < 0.12:
                        p.act_cd = 0.9
                        self.start_dive(p, tv if need > 3.5 else p.wv + (1.0 if tv >= p.wv else -1.0) * 3.0)
                return
        dist_b = math.hypot(b.wx - p.wx, b.wv - p.wv)
        in_box = abs(b.wx - own_x) < BOX_D * 0.85 and BOX_V0 <= b.wv <= BOX_V1
        if b.owner is None and in_box and math.hypot(b.vx, b.vv) < 60 and dist_b < 30:
            p.tx, p.tv = self.ball_pred(0.3)
            return
        gcx = own_x + d * 2.0
        ux, uv = unit(b.wx - gcx, b.wv - V_GC)
        r = clamp(0.2 * math.hypot(b.wx - gcx, b.wv - V_GC), 6.0, 28.0)
        tx, tv = gcx + ux * r, V_GC + uv * r * 0.8
        if (tx - own_x) * d < 3.0:
            tx = own_x + d * 3.0
        p.tx, p.tv = tx, clamp(tv, V_GC - HALF_MOUTH - 10, V_GC + HALF_MOUTH + 10)

    def ball_forecast(self, x_line, tmax=3.2): # Predict the ball position when it reaches a specified field line.
        b = self.ball
        x, v, z, vx, vv, vz = b.wx, b.wv, b.z, b.vx, b.vv, b.vz
        h, t = 1.0 / 60.0, 0.0
        while t < tmax:
            px = x
            x, v, z, vx, vv, vz = step_ball_physics(
                x, v, z, vx, vv, vz, h, b.ds
            )
            t += h
            if (px - x_line) * (x - x_line) <= 0.0 and px != x:
                return dict(t=t, v=v, z=z)
            if z < 0.05 and math.hypot(vx, vv) < 3.0:
                return None
        return None

    def gk_distribute(self, p): # Choose and initiate a goalkeeper distribution action.
        bp = self.best_pass(p)
        if bp and random.random() < 0.6:
            return self.ai_pass(p, bp)
        return self.ai_clear(p)


    def aerial_aim(self, p): # Where a header/bicycle pass should go: a teammate or open space upfield, never back where the ball came from or out over the touchline.
        b, d = self.ball, self.att[p.team]
        sp = math.hypot(b.vx, b.vv)
        back = (-b.vx / sp, -b.vv / sp) if sp > 20.0 else (-float(d), 0.0) # Direction the ball came from.

        def ok(ux, uv): # Reject directions that send the ball back toward its origin.
            return ux * back[0] + uv * back[1] < AERIAL_BACK_MAX
        bp = self.best_pass(p)
        if bp and not ok(*unit(bp[2] - p.wx, bp[3] - p.wv)):
            bp = None
        if bp is None:
            bp = self.best_pass(p, aim=unit(float(d), (V_GC - p.wv) * 0.02), cone=0.3)
            if bp and not ok(*unit(bp[2] - p.wx, bp[3] - p.wv)):
                bp = None
        if bp:
            dx, dv = unit(bp[2] - p.wx, bp[3] - p.wv)
            tgt = bp[1]
        else: # Nobody usable: clear upfield toward the middle of the pitch.
            tx = clamp(p.wx + d * AERIAL_CLEAR_DIST, 6.0, L - 6.0)
            dx, dv = unit(tx - p.wx, (p.wv + (V_GC - p.wv) * 0.5) - p.wv)
            tgt = None
            if not ok(dx, dv):
                dx, dv = unit(float(d), (V_GC - p.wv) * 0.05)
        edge = V_TOP + AERIAL_EDGE, V_BOT - AERIAL_EDGE # Near a touchline never head the ball toward it.
        if (p.wv < edge[0] and dv < 0.0) or (p.wv > edge[1] and dv > 0.0):
            dx, dv = unit(dx, -dv * 0.5, (float(d), 0.0))
        return dx, dv, tgt

    def ai_aerial(self, p): # Choose an appropriate action for a player contesting an aerial ball.
        b = self.ball
        if p.busy() or p.act_cd > 0 or b.owner is not None:
            return
        dist = math.hypot(b.wx - p.wx, b.wv - p.wv)
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        togoal = math.hypot(goalx - p.wx, V_GC - p.wv)
        sp = math.hypot(b.vx, b.vv)
        flair = self.flair_k(p) # Skill: how readily spectacular moves are tried.
        if dist < 9.5 and 8.0 <= b.z <= 20.0 and b.vz < 35:
            key = "bicycle" if (b.z >= BICYCLE_MIN_Z and random.random() < flair) else "header"
            if togoal < 90:
                tv = V_GC + random.uniform(-0.7, 0.7) * HALF_MOUTH
                dx, dv = unit(goalx - p.wx, tv - p.wv)
                self.start_aerial(p, key, dx, dv, 205.0, 22.0, "shot", err=(1.05 - p.skill) * 0.12, steer=True)
            else:
                dx, dv, tgt = self.aerial_aim(p)
                self.start_aerial(p, key, dx, dv, 150.0, 25.0, "pass", target=tgt, steer=True)
        elif DIVE_HEADER_MIN <= dist < DIVE_HEADER_MAX and 4.0 <= b.z <= 14.0 and togoal < 130 and b.vz < 35 \
                and unit(b.wx - p.wx, b.wv - p.wv)[0] * d > 0.2 and random.random() < 0.01 + 0.07 * flair:
            bx, bv = self.ball_pred(0.2)
            if math.hypot(bx - p.wx, bv - p.wv) < DIVE_HEADER_REACH: # Only dive for a ball that will really pass within reach.
                tv = V_GC + random.uniform(-0.7, 0.7) * HALF_MOUTH
                dx, dv = unit(goalx - p.wx, tv - p.wv)
                self.start_aerial(p, "header_dive", dx, dv, 205.0, 22.0, "shot", err=(1.05 - p.skill) * 0.12, assist=True, steer=True)
        elif dist < 12.0 and 1.0 < b.z < 8.0 and sp > 45 and togoal < 100 and b.intended is p \
                and random.random() < 0.10 + 0.50 * flair:
            tv = V_GC + random.uniform(-0.7, 0.7) * HALF_MOUTH
            dx, dv = unit(goalx - p.wx, tv - p.wv)
            self.log_move("volley", p)
            self.start_kick(p, dx, dv, 250.0, self.lob_lift(togoal, 250.0, 4.0), "shot", err=(1.05 - p.skill) * 0.12, special=True, steer=True)

    def best_pass(self, p, aim=None, cone=0.55): # Rank available passing options using their targets and nearby opponents.
        d = self.att[p.team]
        opp = self.opponents(p.team)
        best = None
        for q in self.team_p[p.team]:
            if q is p or q.state in ("out", "leaving") or q.fallen():
                continue
            qx, qv = q.wx + q.vx * 0.4, q.wv + q.vv * 0.4
            dist = math.hypot(qx - p.wx, qv - p.wv)
            if dist < 16 or dist > 210:
                continue
            ux, uv = unit(qx - p.wx, qv - p.wv)
            cosv = 1.0
            if aim is not None:
                cosv = ux * aim[0] + uv * aim[1]
                if cosv < cone:
                    continue
            lane = min([seg_dist(o.wx, o.wv, p.wx, p.wv, qx, qv) for o in opp] or [99.0])
            nq = min([math.hypot(o.wx - qx, o.wv - qv) for o in opp] or [99.0])
            if lane < PLAYER_CATCH_RADIUS + 0.4 and aim is None:
                continue
            score = (qx - p.wx) * d * 0.5 + min(nq, 40) * 0.7 + min(lane, 30) * 0.4 - dist * 0.1 + random.uniform(0, 8)
            if dist > LONG_PASS_FROM: # Skill: a skilled player trusts the long ball, a low-skilled one prefers short passes.
                score += LONG_PASS_BIAS * (1.0 - 2.0 * self.long_k(p)) * min(1.0, (dist - LONG_PASS_FROM) / (LONG_PASS_FULL - LONG_PASS_FROM))
            if q.role == "GK":
                score -= 30
            if aim is not None:
                score += cosv * 60
            if best is None or score > best[0]:
                best = (score, q, qx, qv)
        return best

    def ai_pass(self, p, bp): # Execute the pass selected by the AI.
        _s, q, qx, qv = bp
        dist = math.hypot(qx - p.wx, qv - p.wv)
        dx, dv = unit(qx - p.wx, qv - p.wv)
        power = clamp(dist * 1.55 + 55, 95, 250)
        lift = self.lob_lift(dist, power) if (dist > 125 and random.random() < 0.45) else 0.0
        p.tx = p.tv = None
        return self.start_kick(p, dx, dv, power, lift, "pass", target=q, err=(1 - p.skill) * 0.07)

    def ai_shoot(self, p): # Choose and execute an AI-controlled shot.
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        tv = V_GC + random.uniform(-0.85, 0.85) * HALF_MOUTH
        dx, dv = unit(goalx - p.wx, tv - p.wv)
        dist = math.hypot(goalx - p.wx, tv - p.wv)
        power = random.uniform(225, 285) if dist < LONG_SHOT_FROM else random.uniform(260, 305)
        lift = self.lob_lift(dist, power, random.uniform(2.0, 8.0))
        p.tx = p.tv = None
        far = 1.0 + max(0.0, dist - 100.0) / 100.0 # Long shots are less accurate.
        return self.start_kick(p, dx, dv, power, lift, "shot", err=(1.05 - p.skill) * 0.10 * far)

    def ai_clear(self, p): # Clear the ball when keeping possession is not the preferred option.
        d = self.att[p.team]
        tx = clamp(p.wx + d * 130, 6, L - 6)
        tv = clamp(p.wv + random.uniform(-30, 30), V_TOP + 4, V_BOT - 4)
        dx, dv = unit(tx - p.wx, tv - p.wv)
        dist = math.hypot(tx - p.wx, tv - p.wv)
        p.tx = p.tv = None
        return self.start_kick(p, dx, dv, 245.0, self.lob_lift(dist, 245.0), "pass", err=0.08)

    def ai_owner(self, p, dt): # Choose the ball carrier's next action, such as moving, passing, shooting, or clearing.
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        p.hold_t += dt
        p.dec -= dt
        if p.dec > 0 and p.tx is not None:
            return
        p.dec = random.uniform(0.18, 0.34)
        opp = self.opponents(p.team)
        near = min(opp, key=lambda q: math.hypot(q.wx - p.wx, q.wv - p.wv))
        press = math.hypot(near.wx - p.wx, near.wv - p.wv)
        to_goal = math.hypot(goalx - p.wx, V_GC - p.wv)
        if to_goal < 105 and p.hold_t > 0.22:
            block = min(seg_dist(o.wx, o.wv, p.wx, p.wv, goalx, V_GC) for o in opp)
            prob = 0.9 if to_goal < 60 else 0.55 if to_goal < 82 else 0.28
            if block < 5:
                prob *= 0.35
            if random.random() < prob:
                return self.ai_shoot(p)
        elif LONG_SHOT_FROM <= to_goal < LONG_SHOT_TO and p.hold_t > 0.3: # Long shot: the lower the Skill, the more often.
            block = min(seg_dist(o.wx, o.wv, p.wx, p.wv, goalx, V_GC) for o in opp)
            prob = LONG_SHOT_PROB * (0.2 + 0.8 * self.long_k(p)) * (0.4 if block < 6 else 1.0)
            if random.random() < prob:
                return self.ai_shoot(p)
        press_r = 17.0 * self.agon_mul(p.team, 1.35, 0.8) # Agonism: a cautious team gets rid of the ball earlier under pressure.
        if p.hold_t > 0.3 and (press < press_r or p.hold_t > 1.1 or random.random() < 0.10):
            bp = self.best_pass(p)
            if bp and (press < press_r or bp[0] > 8):
                return self.ai_pass(p, bp)
        own_u = p.wx / L if d > 0 else 1 - p.wx / L
        if p.role in ("DEF", "MID") and own_u >= p.zu[1] and p.hold_t > 0.3:
            bp = self.best_pass(p)
            if bp:
                return self.ai_pass(p, bp)
        if press < 9 and p.hold_t > 0.25 and own_u < 0.3:
            return self.ai_clear(p)
        if p.hold_t > 3.2:
            return self.ai_clear(p)
        ux, uv = unit(goalx - p.wx, V_GC - p.wv)
        tx, tv = p.wx + ux * 60.0, p.wv + uv * 40.0
        if press < 24 and (near.wx - p.wx) * d > -4:
            side = -1.0 if near.wv > p.wv else 1.0
            tx, tv = p.wx + d * 28.0, p.wv + side * 34.0
        if p.wv < V_TOP + 6:
            tv = max(tv, p.wv + 10)
        if p.wv > V_BOT - 6:
            tv = min(tv, p.wv - 10)
        tx, tv = clamp(tx, 6.0, L - 6.0), clamp(tv, V_TOP + 2, V_BOT - 2)
        ulim = min(1.0, p.zu[1] + LEASH_U)
        xlim = ulim * L if d > 0 else (1.0 - ulim) * L
        tx = min(tx, xlim) if d > 0 else max(tx, xlim)
        p.tx, p.tv = tx, tv
