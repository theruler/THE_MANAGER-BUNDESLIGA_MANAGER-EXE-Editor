"""Restart handling in one place: kickoff, throw-in, corner, goal kick, free kick and penalty.

Everything that decides who takes a restart, where the taker and the ball stand, and how the
restart is resumed lives here (previously spread over ai_system, physics_system and the main file).
"""

import math
import random

from ball_model import STANDING_BALL_OFFSET
from game_utils import clamp, unit
from geometry import (
    BOX_D, BOX_V0, BOX_V1, FW, HALF_MOUTH, in_box_fn, L, PITCH_W, s2w, seg_dist, V_GC, V_MAX_P, V_MID, V_MIN_P, V_SPOT,
    V_TOP, w2s,
)
from lang import tr
from match_config import TEAM_NAMES


# ---- Restart alignment: the only three knobs that place a taker next to the ball ----
BALL_AHEAD = STANDING_BALL_OFFSET # World units behind the ball along the facing axis (same offset dribble() uses, so taking the ball causes no jump).
FOOT_PX = {"E": (0.0, -2.0), "W": (0.0, -2.0)} # Screen-pixel offset (dx, dy) from the stand point to the ball's ground point, per kick-pose facing. Calibrate here with the F1 debug overlay.
GK_ADVANCE_U = {"MID": (0.45, 0.70), "FWD": (0.62, 0.90)} # Goal kick, kicking team: normalized depth (from own goal) midfielders / forwards run up to.
GK_DEF_LINE_U = 0.24 # Goal kick: depth of the line defenders hold when they have nobody to mark.
GK_THREAT_U = 0.50 # Goal kick: opponents closer than this (normalized, from the kicking team's goal) to the goal being kicked from are marked.
GK_MARK_GOALSIDE = 6.0 # Goal kick: distance a marker keeps from his man, on the side of his own goal.
GK_TARGET_DIST = 140.0 # Goal kick: preferred distance to the receiver of the AI's kick.
RESTART_SHIFT_X = 0.55 # Restart shape: fraction of the ball's longitudinal offset from the centre the team block follows.
RESTART_SHIFT_V = 0.25 # Same for the lateral offset (small: the team stays spread over the whole width).
RESTART_SPREAD_W = 1.06 # Lateral widening of the shape around the pitch axis.
RESTART_JIT_U = 0.035 # Per-player longitudinal jitter (normalized depth), fixed for the whole restart.
RESTART_JIT_W = 0.05 # Per-player lateral jitter (normalized width).
RESTART_MIN_GAP = 15.0 # Minimum distance between two teammates' restart positions (world units).
RESTART_RELAX_ITERS = 6 # Overlap-relaxation passes.
KICKOFF_WALK_MAX = 30.0 # Seconds after which a walking kickoff starts even if somebody has not reached his spot.
THROW_PX = {"N": 0.0, "S": 4.0} # Vertical pixel offset of a throw-in taker outside the north/south touchline.


class RestartMixin: # Restart setup, taker placement, AI takers and resume logic.
    def restart_box_gx(self, rs): # Goal x of the penalty area the opponents must stay out of during this restart, or None.
        kind = rs.get("kind")
        ogx = 0.0 if self.att[rs["team"]] > 0 else L
        if kind == "goalkick":
            return ogx
        if kind == "free" and in_box_fn(rs["pos"][0], rs["pos"][1], ogx): # Free kick inside the taker's own area: no wall, opponents outside.
            return ogx
        return None

    def pick_taker(self, kind, team, pos): # Choose the player responsible for a specified restart.
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving")]
        out = [p for p in c if p.role != "GK"]
        if kind == "goalkick":
            return next((p for p in c if p.role == "GK"), c[0])
        if kind == "penalty":
            return max(out, key=lambda p: p.skill + (0.15 if p.role == "FWD" else 0))
        near = sorted(out, key=lambda p: math.hypot(p.wx - pos[0], p.wv - pos[1]))
        if self.cp and self.cp.team == team and self.cp in near and self.cp.role != "GK" and\
                math.hypot(self.cp.wx - pos[0], self.cp.wv - pos[1]) < 60:
            return self.cp
        if kind == "free":
            return max(near[:3], key=lambda p: p.skill)
        return near[0]

    def auto_taker(self, taker): # Hand user control to the selected player when that player is the restart taker.
        if self.user_team is not None and taker.team == self.user_team and taker.state not in ("out", "leaving"):
            self.manual = False
            taker.tx = taker.tv = None
            self.idle_t = 0.0
            self.select_player(taker, quiet=True)

    def stand_facing(self, rs): # Facing (E/W) a taker uses for the given restart.
        if rs["kind"] == "corner":
            return "E" if rs["pos"][0] < L / 2 else "W" # Corner takers face into the pitch.
        return "E" if self.att[rs["team"]] > 0 else "W"

    def stand_for(self, ball_xy, facing, behind=BALL_AHEAD): # World position that puts a kicker's feet on the ball's ground point.
        bx, bv = ball_xy
        sgn = 1.0 if facing == "E" else -1.0
        stand_sx, _ = w2s(bx - sgn * behind, bv) # Step back along the facing axis...
        _, ball_sy = w2s(bx, bv) # ...but keep the ball's screen row so feet and ball shadow line up.
        fx, fy = FOOT_PX[facing]
        return s2w(stand_sx + fx, ball_sy + fy)

    def taker_stand(self, rs): # Calculate the standing position for a restart taker.
        x, v = rs["pos"]
        if rs["kind"] == "throw":
            sx, sy = w2s(x, v)
            return s2w(sx, sy + THROW_PX["N" if v < V_MID else "S"])
        return self.stand_for((x, v), self.stand_facing(rs))

    def kickoff_forwards(self, team): # Players who start the kickoff: the first one takes it, the second stands beside him.
        return [p for p in self.team_p[team] if p.role == "FWD" and p.state != "out"] or\
               [p for p in self.team_p[team] if p.role != "GK" and p.state != "out"]

    def kickoff_taker(self, team): # The player who will kick off for the given team (None if nobody is available).
        fw = self.kickoff_forwards(team)
        return fw[0] if fw else None

    def kickoff_spot(self, p, team): # Kickoff position of any player (taker and partner included); used by setup_kickoff and during the goal sequence.
        sx, sv = L / 2.0, V_SPOT
        fw = self.kickoff_forwards(team)
        if fw and p is fw[0]:
            return self.taker_stand(dict(kind="kickoff", pos=(sx, sv), team=team))
        if len(fw) > 1 and p is fw[1]:
            return sx - self.att[team] * 6, sv + 15
        d = self.att[p.team]
        hx, hv = self.home_pos(p, sx, sv, False)
        if p.team != team and math.hypot(hx - sx, hv - sv) < 36:
            u = 0.5 - 40.0 / L
            hx = u * L if d > 0 else (1 - u) * L
        return hx, hv

    def setup_kickoff(self, team, sound=True, walk=False): # Arrange players and the ball for a kickoff; with walk=True everybody walks to his place (clock stopped, no teleport).
        b = self.ball
        sx, sv = L / 2.0, V_SPOT
        for p in self.players:
            if p.state == "out":
                continue
            p.state, p.act, p.cool, p.tag = "free", None, 0.0, None
            if not walk:
                p.vx, p.vv = 0.0, 0.0
            p.tx = p.tv = None
            if walk:
                p.path = None
            d = self.att[p.team]
            self._kick_place(p, *self.kickoff_spot(p, team), walk)
            p.dx, p.dv, p.face = float(d), 0.0, "E" if d > 0 else "W"
        fw = self.kickoff_forwards(team)
        b.owner = None
        b.wx, b.wv, b.z, b.vx, b.vv, b.vz = sx, sv, 0.0, 0.0, 0.0, 0.0
        b.last_team = team
        b.last = None
        b.intended = None
        b.tactical_pass = False
        b.pass_active = False
        r = self.ref
        if walk: # The referee walks to his spot too (update_ref).
            r.card = None
        else:
            r.wx, r.wv, r.vx, r.vv, r.card = sx - 30, sv + 24, 0.0, 0.0, None
        self.restart = dict(kind="kickoff", team=team, pos=(sx, sv), taker=fw[0], t=0.0, ready=False, ready_t=0.0, said=False, walk=walk)
        self.mode = "restart"
        self.foul = self.goal = None
        self.auto_taker(fw[0])
        if sound and self.half_t == 0:
            self.audio.play("whistle")
        for p in self.players:
            self.post_move(p)

    @staticmethod
    def _kick_place(p, x, v, walk): # Put a player at a kickoff spot at once, or give him the spot as a walking target.
        if walk:
            p.tx, p.tv = x, v
        else:
            p.wx, p.wv = x, v

    def kickoff_settled(self, rs): # Kickoff with walking players: True when everybody (user-steered players excepted) stands at his spot.
        if not rs.get("walk") or rs["t"] > KICKOFF_WALK_MAX:
            return True
        for q in self.players:
            if q.state != "free" or q.ctrl or q is rs["taker"] or q.tx is None:
                continue
            if math.hypot(q.tx - q.wx, q.tv - q.wv) > 3.0:
                return False
        return True

    def start_restart(self, kind, team, pos): # Initialize a restart such as a free kick, throw-in, or goal kick.
        pos = self.visible_pos(pos)
        self._gk_area_violator = None
        b = self.ball
        self._backpass_src = None
        b.owner, b.vx, b.vv, b.vz, b.z = None, 0.0, 0.0, 0.0, 0.0
        b.wx, b.wv = pos
        b.intended = None
        b.tactical_pass = False
        taker = self.pick_taker(kind, team, pos)
        if kind in ("free", "penalty"):
            taker.face = "E" if self.att[team] > 0 else "W"
            taker.dx, taker.dv, taker.face_t = float(self.att[team]), 0.0, 0.0
        for p in self.players:
            if p.state in ("out", "leaving"):
                continue
            if not p.busy():
                p.state = "free"
            p.tag = None
        self.restart = dict(kind=kind, team=team, pos=pos, taker=taker, t=0.0, ready=False, ready_t=0.0, said=False)
        self.mode = "restart"
        self.foul = None
        if kind == "corner":
            self.stats["corners"][team] += 1
            self.audio.react("corner")
        elif kind == "penalty":
            self.audio.react("tension")
        self.auto_taker(taker)

    def begin_ball_out(self, kind, team, pos): # Start the sequence for a ball that has gone out of play.
        b = self.ball
        self._backpass_src = None
        self.outball = dict(kind=kind, team=team, pos=pos, t=0.0, phase="roll", roll=random.uniform(0.25, 0.6), src=None, fly=0.0)
        b.owner, b.intended, b.shot_team = None, None, None
        b.tactical_pass = False
        b.pass_active = False
        b.vz = max(b.vz, 0.0)
        self.mode = "outball"
        self.foul = None
        for p in self.players:
            if p.state not in ("out", "leaving", "action"):
                p.tag, p.tx, p.tv = None, None, None
                if p.state == "cele":
                    p.state = "free"

    def update_outball(self, dt): # Advance the out-of-play sequence and prepare the restart.
        o = self.outball
        b = self.ball
        o["t"] += dt
        if o["phase"] == "roll":
            b.wv = clamp(b.wv, V_TOP - 13.0, V_MAX_P + 8.0)
            if b.wv in (V_TOP - 13.0, V_MAX_P + 8.0) and abs(b.vv) > 8:
                hit_v = abs(b.vv)
                b.vv *= -0.4
                if b.wv == V_TOP - 13.0:
                    self.audio.play("stands", clamp(0.35 + hit_v / 130.0, 0.35, 1.0))
                else:
                    self.audio.play("bounce", 0.5)
            if o["t"] >= o["roll"]:
                o["phase"] = "fly"
                o["src"] = (b.wx, b.wv, b.z)
                o["fly"] = clamp(math.hypot(o["pos"][0] - b.wx, o["pos"][1] - b.wv) / 230.0, 0.35, 0.8)
                o["dist"] = math.hypot(o["pos"][0] - b.wx, o["pos"][1] - b.wv)
                o["t"] = 0.0
                b.vx = b.vv = b.vz = 0.0
                tk = self.pick_taker(o["kind"], o["team"], self.visible_pos(o["pos"]))
                o["taker"] = tk
                self.audio.play("kick", 0.45)
        else:
            u = min(1.0, o["t"] / o["fly"])
            sx, sv, sz = o["src"]
            tx, tv = self.visible_pos(o["pos"])
            b.wx, b.wv = sx + (tx - sx) * u, sv + (tv - sv) * u
            b.z = sz * (1.0 - u) + 4.0 * 13.0 * u * (1.0 - u)
            b.spin += o.get("dist", 60.0) / o["fly"] * dt
            tk = o.get("taker")
            if tk is not None and tk.state not in ("out", "leaving") and not tk.busy():
                self.goto(tk, *self.taker_stand(dict(kind=o["kind"], pos=self.visible_pos(o["pos"]), team=o["team"])))
            if u >= 1.0:
                self.start_restart(o["kind"], o["team"], o["pos"])
                self.outball = None

    def dismiss_goal_kick_area_player(self, rs, offender, second_yellow=False): # Send off a player who ignores the goal-kick area warning.
        offender.red = True
        if getattr(self, "_gk_area_violator", None) is offender:
            self._gk_area_violator = None
        self.stats["red"][offender.team] += 1
        self.ref.card, self.ref.card_t = "R", 2.2
        key = "ev.card_red_second" if second_yellow else "ev.card_red"
        text = tr(key, p=offender.label(), team=TEAM_NAMES[offender.team])
        self.log_event(text, (255, 90, 90), secs=5.0, team=offender.team)
        self.say(text, (255, 90, 90), 5.0)
        self.audio.react("card")
        offender.state, offender.act = "leaving", None
        offender.path = None
        offender.kvec = None
        self.set_gate(offender)
        offender.tx, offender.tv = L / 2.0 + offender.gate, V_MAX_P
        rs.pop("area_violator", None)
        rs.pop("area_elapsed", None)
        rs["area_stage"] = 3
        if self.cp is offender:
            self.select_player(None)

    def update_goal_kick_area_rule(self, rs, dt, own_gx): # Enforce the manual-player penalty-area rule during a goal kick.
        offender = rs.get("area_violator")
        if offender is not None and (
            offender.state in ("out", "leaving") or offender.red
            or not in_box_fn(offender.wx, offender.wv, own_gx)
        ):
            if getattr(self, "_gk_area_violator", None) is offender:
                self._gk_area_violator = None
            rs.pop("area_violator", None)
            rs.pop("area_elapsed", None)
            rs.pop("area_stage", None)
            offender = None

        if offender is None:
            selected = self.cp
            if (selected is not None and selected.team != rs["team"]
                    and selected.state not in ("out", "leaving") and not selected.red
                    and in_box_fn(selected.wx, selected.wv, own_gx)):
                offender = selected
                rs["area_violator"] = offender
                self._gk_area_violator = offender
                rs["area_elapsed"] = 0.0
                rs["area_stage"] = 0

        if offender is None:
            return False

        rs["area_elapsed"] = rs.get("area_elapsed", 0.0) + dt
        elapsed = rs["area_elapsed"]
        stage = rs.get("area_stage", 0)

        while stage < 3 and elapsed >= (4.0 * (stage + 1)):
            stage += 1
            rs["area_stage"] = stage
            if stage == 1:
                self.audio.play("whistle_long")
                self.say("Esci dall'area di rigore!", (255, 230, 70), 4.0)
                self.log_event("Richiamo arbitrale per permanenza nell'area di rigore: " + offender.label(),
                               (255, 230, 70), secs=4.0, team=offender.team)
            elif stage == 2:
                offender.yellow += 1
                self.stats["yellow"][offender.team] += 1
                if offender.yellow >= 2:
                    self.dismiss_goal_kick_area_player(rs, offender, second_yellow=True)
                    return False
                self.ref.card, self.ref.card_t = "Y", 2.0
                text = tr("ev.card_yellow", p=offender.label(), team=TEAM_NAMES[offender.team])
                self.log_event(text, (255, 230, 70), secs=4.0, team=offender.team)
                self.say(text, (255, 230, 70), 4.0)
                self.audio.react("card")
            else:
                self.dismiss_goal_kick_area_player(rs, offender)
                return False

        return True

    def update_restart(self, dt): # Advance the restart setup until play can resume.
        rs = self.restart
        rs["t"] += dt
        tk = rs["taker"]
        if tk.state in ("out", "leaving"):
            rs["taker"] = tk = self.pick_taker(rs["kind"], rs["team"], rs["pos"])
            rs["pin_taker"] = False
            rs.pop("pin_pos", None)
            if rs["kind"] in ("free", "penalty"):
                tk.face = "E" if self.att[rs["team"]] > 0 else "W"
                tk.dx, tk.dv, tk.face_t = float(self.att[rs["team"]]), 0.0, 0.0
        sx, sv = self.taker_stand(rs)
        # Set-piece takers cannot walk away from the designated ball position.
        tk.kvec = None
        tk.path = None
        tk.tx, tk.tv = sx, sv
        if rs["kind"] in ("free", "penalty"):
            tk.face = "E" if self.att[rs["team"]] > 0 else "W"
            tk.dx, tk.dv, tk.face_t = float(self.att[rs["team"]]), 0.0, 0.0
        at = math.hypot(tk.wx - sx, tk.wv - sv) < 1.4
        if at and not rs.get("pin_taker", False):
            rs["pin_taker"] = True
            # Keep the reached longitudinal position and align only the feet to the target depth.
            rs["pin_pos"] = (tk.wx, tk.wv)
        minw = dict(kickoff=1.3, throw=0.8, goalkick=0.8, corner=1.8, free=1.9, penalty=2.4)[rs["kind"]]
        box_free = True
        manual_box_block = False
        if self.restart_box_gx(rs) is not None: # Goal kick, or free kick inside the taker's own area.
            ad_ = self.att[rs["team"]]
            ogx_ = 0.0 if ad_ > 0 else L
            if "push" not in rs:
                rs["push"] = {id(q) for q in self.team_p[1 - rs["team"]]
                              if q.role != "GK" and not q.ctrl and q.state not in ("out", "leaving") and in_box_fn(q.wx, q.wv, ogx_)}
            for q in self.team_p[1 - rs["team"]]:
                if q.role == "GK" or q.ctrl or q.state in ("out", "leaving"):
                    continue
                inside = in_box_fn(q.wx, q.wv, ogx_)
                if not inside:
                    rs["push"].discard(id(q))
                    continue
                box_free = False
                if id(q) in rs["push"] and (q.busy() or q.tx is None):
                    q.wx += ad_ * 70.0 * dt
            manual_box_block = self.update_goal_kick_area_rule(rs, dt, ogx_)
            if manual_box_block:
                box_free = False
                rs["ready"] = False
                rs["ready_t"] = rs["t"]
        settled = self.kickoff_settled(rs) if rs["kind"] == "kickoff" else True
        if not rs["ready"] and at and settled and rs["t"] > minw and not tk.busy() and (box_free or rs["t"] > 8.0) and not manual_box_block:
            rs["ready"], rs["ready_t"] = True, rs["t"]
            if rs["kind"] in ("free", "penalty", "corner"):
                self.audio.play("whistle")
            if tk.ctrl:
                self.say(tr("msg.hint_shoot"), (255, 255, 120), 4)
        if rs["ready"] and tk.ctrl and tk is self.cp and self.paused_gesture is not None and not tk.busy():
            gesture = self.paused_gesture
            self.paused_gesture = None
            self.paused_traj_data = None
            self._applying_paused_gesture = True
            try:
                self.user_action(*gesture)
            finally:
                self._applying_paused_gesture = False
            return
        if rs["ready"] and not tk.busy():
            idle_limit = 1.2 if rs["kind"] == "goalkick" else 4.0
            if rs["t"] - rs["ready_t"] > 0.55 and (not tk.ctrl or self.idle_t > idle_limit):
                self.ai_take_restart(tk, rs)
        elif rs["t"] > (KICKOFF_WALK_MAX + 10.0 if rs.get("walk") else 14.0) and not tk.busy() and not manual_box_block:
            self.ai_take_restart(tk, rs)

    @staticmethod
    def visible_pos(pos, margin=9.0): # Check whether a position lies within the visible field area.
        px, gy = w2s(pos[0], pos[1])
        if margin <= px <= FW - margin:
            return pos
        return s2w(clamp(px, margin, FW - margin), gy)[0], pos[1]

    def ai_restart(self, p, dt): # Position an AI player during a restart situation.
        rs = self.restart
        if rs is None or p is rs["taker"]:
            return
        kind, team = rs["kind"], rs["team"]
        if kind == "kickoff":
            return
        x, v = rs["pos"]
        ad = self.att[team]
        agx = L if ad > 0 else 0.0
        poss = p.team == team
        hx, hv = self.restart_shape(rs, p, poss)
        near_goal = math.hypot(agx - x, V_GC - v) < 130
        own_box_gx = self.restart_box_gx(rs) if kind == "free" else None # Set when the free kick is taken inside the kicker's own area.
        if p.role == "GK":
            p.tx, p.tv = hx, hv
            return
        if kind == "corner":
            if poss and p.role in ("MID", "FWD"):
                hx, hv = agx - ad * (8 + (p.idx % 4) * 7), V_GC + ((p.idx % 5) - 2) * HALF_MOUTH * 0.55
            elif not poss and p.role in ("DEF", "MID"):
                hx, hv = agx - ad * (5 + (p.idx % 4) * 6), V_GC + (((p.idx + 2) % 5) - 2) * HALF_MOUTH * 0.55
        elif kind == "penalty":
            hx, hv = agx - ad * (BOX_D + 16 + (p.idx % 3) * 6), V_GC + ((p.idx % 7) - 3) * 10
        elif kind == "free" and not poss and p.role != "GK" and own_box_gx is None:
            wall = rs.get("wall")
            if wall is None:
                nwall = 3 if near_goal else 2
                cand = sorted([q for q in self.team_p[p.team] if q.role != "GK" and not q.ctrl and q.state not in ("out", "leaving")],
                              key=lambda q: math.hypot(q.wx - x, q.wv - v))[:nwall]
                wall = rs["wall"] = [id(q) for q in cand]
            if id(p) in wall:
                gd = math.hypot(agx - x, V_GC - v)
                wd = clamp(gd * 0.5, 8.0, 22.0)
                ux, uv = unit(agx - x, V_GC - v)
                k = wall.index(id(p)) - (len(wall) - 1) / 2.0
                hx, hv = x + ux * wd - uv * k * 5.0, v + uv * wd + ux * k * 5.0
                p.tx, p.tv = clamp(hx, 6.0, L - 6.0), clamp(hv, V_MIN_P, V_MAX_P)
                return
        elif kind == "free" and poss and near_goal and p.role in ("MID", "FWD"):
            hx, hv = agx - ad * (14 + (p.idx % 4) * 8), V_GC + ((p.idx % 5) - 2) * HALF_MOUTH * 0.6
        if kind == "goalkick" and poss:
            hx, hv = self.goalkick_shape(p, rs, hx, hv)
        if poss and kind == "throw":
            ub, _wb = self.team_uw(team, x, v)
            inward = 1.0 if v < V_MID else -1.0
            mates = sorted([q for q in self.team_p[team] if q is not rs["taker"] and q.role != "GK" and q.state not in ("out", "leaving")],
                           key=lambda q: math.hypot(q.wx - x, q.wv - v))
            if mates and p is mates[0]:
                hx, hv = x - ad * 4.0, v + inward * 17.0
            elif len(mates) > 1 and p is mates[1]:
                hx, hv = x + ad * 17.0, v + inward * 25.0
            elif p.role in ("MID", "FWD"):
                u, w = self.team_uw(team, hx, hv)
                u = clamp(max(u, ub + (0.10 if p.role == "FWD" else 0.04)), p.zu[0], p.zu[1])
                hx = u * L if ad > 0 else (1.0 - u) * L
        elif not poss and p.tag == "mark" and p.mark is not None:
            hx, hv = self.mark_pos(p, p.mark)
        min_restart_distance = 18.0 if kind == "throw" else 28.0 if kind == "free" else 0.0
        if not poss and min_restart_distance:
            dd = math.hypot(hx - x, hv - v)
            if dd < min_restart_distance:
                ux, uv = unit(hx - x, hv - v, (-ad, 0.0))
                hx, hv = x + ux * min_restart_distance, v + uv * min_restart_distance
        if (kind == "goalkick" or own_box_gx is not None) and not poss:
            ogx = 0.0 if ad > 0 else L
            edge = BOX_D + 8.0
            if abs(hx - ogx) < edge and BOX_V0 - 6.0 <= hv <= BOX_V1 + 6.0:
                hx = ogx + ad * edge
        p.tx, p.tv = clamp(hx, 6.0, L - 6.0), clamp(hv, V_MIN_P, V_MAX_P)

    def restart_shape(self, rs, p, poss): # Organic, ball-aware position of an outfield player; the whole team shape is built once per restart and cached.
        cache = rs.setdefault("shape", {})
        if p.team not in cache:
            x, v = rs["pos"]
            bx = L / 2.0 + (x - L / 2.0) * RESTART_SHIFT_X # The block follows the ball only partly...
            bv = V_MID + (v - V_MID) * RESTART_SHIFT_V # ...and hardly sideways, so nobody is dragged to one touchline.
            rng = random.Random(hash((id(rs), p.team)) & 0xFFFFFFFF)
            team_poss = p.team == rs["team"]
            pts = {}
            for q in self.team_p[p.team]:
                if q.role == "GK" or q.state in ("out", "leaving"):
                    continue
                hx, hv = self.home_pos(q, bx, bv, team_poss)
                u, w = self.team_uw(p.team, hx, hv)
                u += rng.uniform(-RESTART_JIT_U, RESTART_JIT_U)
                w = 0.5 + (w - 0.5) * RESTART_SPREAD_W + rng.uniform(-RESTART_JIT_W, RESTART_JIT_W)
                u, w = clamp(u, q.zu[0], q.zu[1]), clamp(w, q.zw[0], q.zw[1])
                pts[id(q)] = [(u * L if self.att[p.team] > 0 else (1.0 - u) * L), V_TOP + w * PITCH_W, q]
            for _ in range(RESTART_RELAX_ITERS): # Relax overlaps: teammates closer than the minimum gap are pushed apart (inside their zones).
                for a in pts.values():
                    for b in pts.values():
                        if a is b or id(a[2]) > id(b[2]):
                            continue
                        dd = math.hypot(a[0] - b[0], a[1] - b[1])
                        if dd < RESTART_MIN_GAP:
                            ux, uv = unit(a[0] - b[0], a[1] - b[1], (0.0, 1.0 if a[2].idx % 2 else -1.0))
                            k = (RESTART_MIN_GAP - dd) * 0.5
                            a[0], a[1] = self.zone_clamp(a[2], a[0] + ux * k, a[1] + uv * k, 0.03, 0.03)
                            b[0], b[1] = self.zone_clamp(b[2], b[0] - ux * k, b[1] - uv * k, 0.03, 0.03)
            cache[p.team] = {k: (a[0], a[1]) for k, a in pts.items()}
        return cache[p.team].get(id(p)) or self.home_pos(p, L / 2.0, V_MID, poss)

    def goalkick_marks(self, rs): # Assign defenders (not the taker) to opponents who stayed in the kicking team's half; computed once per restart.
        if "gk_marks" in rs:
            return rs["gk_marks"]
        team = rs["team"]
        defs = [q for q in self.team_p[team] if q.role == "DEF" and q is not rs["taker"] and not q.ctrl and q.state not in ("out", "leaving")]
        threats = [o for o in self.opponents(team) if o.role != "GK" and o.state not in ("out", "leaving")
                   and self.team_uw(team, o.wx, o.wv)[0] < GK_THREAT_U]
        threats.sort(key=lambda o: self.team_uw(team, o.wx, o.wv)[0]) # Deepest intruder (closest to our goal) first.
        marks, free = {}, list(defs)
        for o in threats[:max(1, len(defs) - 1)]: # Always keep one defender on the line.
            if not free:
                break
            q = min(free, key=lambda d: math.hypot(d.wx - o.wx, d.wv - o.wv))
            free.remove(q)
            marks[id(q)] = o
        rs["gk_marks"] = marks
        return marks

    def goalkick_shape(self, p, rs, hx, hv): # Kicking team at a goal kick: no formation; MID/FWD run upfield to receive, DEF stay back and mark intruders.
        team = rs["team"]
        ad = self.att[team]
        ogx = 0.0 if ad > 0 else L
        if p.role == "DEF":
            o = self.goalkick_marks(rs).get(id(p))
            if o is not None and o.state not in ("out", "leaving"):
                ux, uv = unit(ogx - o.wx, V_GC - o.wv, (ad * -1.0, 0.0))
                return o.wx + ux * GK_MARK_GOALSIDE, o.wv + uv * GK_MARK_GOALSIDE
            u, w = GK_DEF_LINE_U, p.base_w
        elif p.role in GK_ADVANCE_U:
            lo, hi = GK_ADVANCE_U[p.role]
            u, w = lo + (hi - lo) * (((p.idx * 7) % 5) / 4.0), p.base_w # Spread the runners over the depth band.
            u = max(u, p.base_u)
        else:
            return hx, hv
        w = clamp(w, p.zw[0], p.zw[1])
        return (u * L if ad > 0 else (1.0 - u) * L), V_TOP + w * PITCH_W

    def goalkick_target(self, p, rs): # Best receiver among the midfielders/forwards that moved up, or None.
        team = rs["team"]
        ad = self.att[team]
        cands = [q for q in self.team_p[team] if q is not p and q.role in ("MID", "FWD") and q.state not in ("out", "leaving")]
        if not cands:
            return None
        opp = self.opponents(team)

        def spot(q): # Where the receiver is heading (he is still running upfield when the kick is taken).
            return (q.tx, q.tv) if q.tx is not None else (q.wx, q.wv)

        def score(q):
            qx, qv = spot(q)
            free = min([math.hypot(o.wx - qx, o.wv - qv) for o in opp] or [60.0])
            dist = math.hypot(qx - p.wx, qv - p.wv)
            return min(free, 35.0) + (qx - p.wx) * ad * 0.04 - abs(dist - GK_TARGET_DIST) * 0.12 + random.uniform(0.0, 6.0)
        q = max(cands, key=score)
        return q, spot(q)

    def ai_take_restart(self, p, rs): # Execute the selected AI-controlled restart.
        if p.busy():
            return
        kind, team = rs["kind"], rs["team"]
        ad = self.att[team]
        agx = L if ad > 0 else 0.0
        x, v = rs["pos"]
        p.tx = p.tv = None
        if kind == "penalty" or (kind == "free" and math.hypot(agx - x, V_GC - v) < 118):
            lo, hi = (0.55, 0.92) if kind == "penalty" else (0.35, 0.85)
            tv = V_GC + random.choice((-1, 1)) * random.uniform(lo, hi) * HALF_MOUTH
            dx, dv = unit(agx - p.wx, tv - p.wv)
            dist = math.hypot(agx - p.wx, tv - p.wv)
            power = random.uniform(235, 275)
            lift = self.lob_lift(dist, power, random.uniform(2, 6)) + (25 if kind == "free" else 0)
            self.start_kick(p, dx, dv, power, lift, "shot", err=(1.05 - p.skill) * (0.05 if kind == "penalty" else 0.09))
            return
        if kind == "corner":
            tx, tv = agx - ad * random.uniform(10, 26), V_GC + random.uniform(-0.9, 0.9) * HALF_MOUTH * 1.3
            dx, dv = unit(tx - p.wx, tv - p.wv)
            dist = math.hypot(tx - p.wx, tv - p.wv)
            self.start_kick(p, dx, dv, 165.0, self.lob_lift(dist, 165.0, 9.0), "pass", err=0.05)
            return
        if kind == "goalkick":
            tg = self.goalkick_target(p, rs)
            if tg is None:
                return self.ai_clear(p)
            q, (qx, qv) = tg
            dist = math.hypot(qx - p.wx, qv - p.wv)
            dx, dv = unit(qx - p.wx, qv - p.wv)
            power = clamp(dist * 1.55 + 55, 95, 250)
            return self.start_kick(p, dx, dv, power, self.lob_lift(dist, power), "pass", target=q, err=(1 - p.skill) * 0.07)
        mates = [q for q in self.team_p[team] if q is not p and q.state not in ("out", "leaving") and q.role != "GK"]
        if kind == "throw":
            opp = self.opponents(team)

            def tscore(m): # Rank throw-in receivers using distance, available space, and defensive pressure.
                dist_ = math.hypot(m.wx - p.wx, m.wv - p.wv)
                free_ = min([math.hypot(o.wx - m.wx, o.wv - m.wv) for o in opp] or [60.0])
                lane_ = min([seg_dist(o.wx, o.wv, p.wx, p.wv, m.wx, m.wv) for o in opp] or [60.0])
                return min(free_, 30) + min(lane_, 20) * 0.6 + (m.wx - p.wx) * ad * 0.12 - abs(dist_ - 40) * 0.25 - (60 if dist_ > 105 else 0)
            q = max(mates, key=tscore)
            dist = math.hypot(q.wx - p.wx, q.wv - p.wv)
            dx, dv = unit(q.wx - p.wx, q.wv - p.wv)
            power = clamp(dist * 1.4 + 40, 80, 170)
            self.start_throw(p, dx, dv, power, self.lob_lift(dist, power, -10.0), q)
            return
        bp = self.best_pass(p)
        if bp:
            self.ai_pass(p, bp)
        else:
            q = min(mates, key=lambda m: math.hypot(m.wx - p.wx, m.wv - p.wv))
            self.ai_pass(p, (0, q, q.wx, q.wv))
