import math
import random

import pygame

from formation_system import ROLE_ORDER, ROLE_POOLS
from game_utils import clamp, unit
from geometry import depth_k, depth_v_k, FH, FW, GATE_SPREAD, L, MAX_Y, pitch_v, V_BOT, w2s, WIN_H, WIN_W, Y_OFFSET
from lang import tr
from match_config import TEAM_NAMES
from physics_system import PLAYER_SPEED
from sprite_data import run_cycle


class SubstitutionMixin: # Substitutions, sideline transitions, and injury handling.
    def natural_role(self, sq): # Return the natural tactical role associated with a squad position.
        for r in ROLE_ORDER:
            lo, hi = ROLE_POOLS[r]
            if lo <= sq < hi:
                return r
        return "MID"

    def bench(self, t): # Return the eligible substitute players for a team.
        pl = self.team_data[t]["players"]
        on = {q.sq for q in self.team_p[t]} | self.sub_out[t] | {e["inn"] for e in self.sub_q[t]}
        return [i for i in range(min(len(pl), 20)) if i not in on and pl[i]]

    def sub_candidates(self, p): # Build the candidate list for replacing the selected player.
        bn = self.bench(p.team)
        if p.role == "GK":
            return [i for i in bn if self.natural_role(i) == "GK"]
        c = [i for i in bn if self.natural_role(i) != "GK"]
        return sorted(c, key=lambda i: 0 if self.natural_role(i) == self.natural_role(p.sq) else 1)

    def request_sub(self, p, inn=None, why="tattica"): # Validate and queue a requested substitution.
        t = p.team
        for e in self.sub_q[t]:
            if e["out"] is p:
                if why == "tattica":
                    self.sub_q[t].remove(e)
                    self.stoppage_target = max(1.0, self.stoppage_target - 0.55)
                    self.say(tr("msg.sub_cancelled", name=p.name), (255, 220, 160), 2.5)
                return False
        if p.red or p.state == "out":
            return False
        if self.subs_used[t] + len(self.sub_q[t]) >= 5:
            self.say(tr("msg.sub_limit", team=TEAM_NAMES[t]), (255, 160, 140), 3)
            return False
        cand = self.sub_candidates(p)
        if not cand:
            self.say(tr("msg.sub_none", name=p.name), (255, 160, 140), 3)
            return False
        inn = cand[0] if inn is None else inn
        self.sub_q[t].append(dict(out=p, inn=inn, why=why))
        self.stoppage_target += 0.55
        return True

    def open_sub_menu(self, p, rect): # Open the substitution menu for the selected player and panel position.
        if self.user_team is not None and p.team != self.user_team:
            return
        if any(e["out"] is p for e in self.sub_q[p.team]):
            self.request_sub(p)
            return
        cand = self.sub_candidates(p)
        if not cand or self.subs_used[p.team] + len(self.sub_q[p.team]) >= 5:
            self.request_sub(p)
            return
        self.sub_menu = dict(p=p, rect=rect, cand=cand[:10])

    def sub_menu_layout(self): # Calculate the substitution panel and item hitboxes.
        m = self.sub_menu
        w, rh = 270, 22
        h = rh * (len(m["cand"]) + 1) + 8
        x = int(clamp(m["rect"].left, 0, self.W - w))
        y = int(clamp(m["rect"].bottom + 2, 0, self.H - h))
        items = [(pygame.Rect(x + 4, y + 4 + rh * (i + 1), w - 8, rh), idx) for i, idx in enumerate(m["cand"])]
        return pygame.Rect(x, y, w, h), items

    def sub_menu_click(self, pos): # Handle a click on the substitution menu.
        panel, items = self.sub_menu_layout()
        m = self.sub_menu
        self.sub_menu = None
        if panel.collidepoint(pos):
            for r, idx in items:
                if r.collidepoint(pos):
                    self.request_sub(m["p"], idx)
                    return

    def maybe_ai_subs(self): # Check whether the AI should request tactical substitutions.
        rs = self.restart
        if rs is None or rs.get("ai_sub") or self.half != 2 or self.minute() < 60:
            return
        rs["ai_sub"] = True
        for t in (0, 1):
            if self.user_team == t or self.subs_used[t] + len(self.sub_q[t]) >= 5 or random.random() > 0.16:
                continue
            c = [q for q in self.team_p[t] if q.role != "GK" and not q.red and q.state != "out"
                 and not any(e["out"] is q for e in self.sub_q[t])]
            if c:
                c.sort(key=lambda q: -(q.yellow * 2 + random.random()))
                self.request_sub(c[0], why="tattica")

    def begin_subs(self): # Start the queued substitutions and their transition animations.
        self.mode = "subs"
        self.subs_t = 0.0
        self.subs_list = []
        for t in (0, 1):
            for e in self.sub_q[t]:
                p = e["out"]
                if p.state in ("out", "leaving"):
                    continue
                p.state, p.act, p.path, p.tx, p.tv = "subout", None, None, None, None
                self.set_gate(p)
                p.limp = e["why"] == "infortunio"
                self.subs_list.append(e)
            self.sub_q[t] = []
        self.audio.play("whistle", 0.5)

    def swap_identity(self, p, e): # Transfer player identity and match statistics during a substitution.
        t = p.team
        pl = self.team_data[t]["players"]
        old = p.name
        self.sub_out[t].add(p.sq)
        p.sq = e["inn"]
        p.name = pl[p.sq]
        self.subs_used[t] += 1
        p.num = 11 + self.subs_used[t]
        p.yellow, p.red, p.limp, p.path = 0, False, False, None
        p.injured = False
        p.speed = PLAYER_SPEED * random.uniform(0.94, 1.07)
        p.skill, p.aggr = random.uniform(0.66, 0.95), random.uniform(0.2, 0.95)
        p.skill0 = p.skill
        self.apply_skill(p, self.pstats(p)) # The substitute plays with his own Fitness / Skill / Form.
        p.stride, p.hold_t, p.lift = 0.0, 0.0, 0.0
        p.new_drift()
        sub_reason = tr("ev.sub_reason_injury") if e["why"] == "infortunio" else ""
        self.log_event(tr("ev.sub", team=TEAM_NAMES[t], out=old, inn=p.name, n=self.subs_used[t], reason=sub_reason), secs=4, team=t)

    def gate_point(self, p, tv_end, tx=None, tv=None): # Calculate the point where a player enters or exits at the sideline gate.
        gx = L / 2.0 + p.gate
        if tx is None:
            if p.wv < V_BOT + 8.0 and abs(p.wx - gx) > 1.5:
                return gx, (V_BOT - 1.0 if p.wv < V_BOT + 0.5 else V_BOT + 0.5)
            return gx, tv_end
        if p.wv > V_BOT - 1.0:
            return gx, V_BOT - 2.0
        return tx, tv

    def set_gate(self, p, side=0): # Set the sideline gate used by the player substitution animation.
        if side:
            p.gate = side * random.uniform(0.15, 1.0) * GATE_SPREAD
        else:
            p.gate = random.uniform(-1.0, 1.0) * GATE_SPREAD

    def step_sub(self, p, dt): # Advance a player through the substitution walk-on or walk-off path.
        vexit = pitch_v(MAX_Y + 30)
        e = next((x for x in self.subs_list if x["out"] is p), None)
        sp = 30.0 if p.limp else 46.0
        if p.state == "subout":
            tx, tv = self.gate_point(p, vexit)
        else:
            if p.tx is None:
                p.tx, p.tv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            tx, tv = self.gate_point(p, vexit, p.tx, p.tv)
        ux, uv = unit(tx - p.wx, tv - p.wv, (0.0, 1.0))
        kk = depth_k(p.wv)
        kv = depth_v_k(p.wv, p.wx)
        p.wx += ux * sp * dt * kk
        p.wv += uv * sp * dt * kv
        p.vx, p.vv = ux * sp, uv * sp
        p.stride += sp * dt
        if abs(ux) > 0.2:
            p.face = "E" if ux > 0 else "W"
        cyc = run_cycle(p.team, p.face)
        p.sid = cyc[int(p.stride / 4.6) % len(cyc)]
        self.post_move(p)
        if p.state == "subout" and p.wv >= vexit - 0.5 and p.walk == "off":
            p.state, p.vx, p.vv, p.wv = "tunnel", 0.0, 0.0, vexit
            return
        if p.state == "subout" and p.wv >= vexit - 0.5:
            if e is not None:
                self.swap_identity(p, e)
            p.state = "subin"
            p.wx = L / 2.0 + p.gate
            p.wv = vexit
            hx, hv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            p.tx, p.tv = hx, hv
            p.limp = False
        elif p.state == "subin" and math.hypot(p.wx - p.tx, p.wv - p.tv) < 2.5:
            p.state = "free"
            p.tx = p.tv = None
            p.vx = p.vv = 0.0

    def update_subs(self, dt): # Advance active substitution transitions and player movement.
        self.subs_t += dt
        busy = [p for p in self.players if p.state in ("subout", "subin")]
        if busy and self.subs_t < 30.0:
            return
        for p in busy:
            e = next((x for x in self.subs_list if x["out"] is p), None)
            if p.state == "subout" and e is not None:
                self.swap_identity(p, e)
            p.state = "free"
            p.tx = p.tv = None
            hx, hv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            p.wx, p.wv = hx, hv
        self.mode = "restart"
        rs = self.restart
        if rs is not None:
            rs["t"], rs["ready"], rs["said"] = 0.0, False, False
            if rs["kind"] == "kickoff":
                self.setup_kickoff(rs["team"], sound=False)
            else:
                rs["taker"] = self.pick_taker(rs["kind"], rs["team"], rs["pos"])
                self.auto_taker(rs["taker"])

    def instant_subs(self): # Apply queued substitutions immediately without walk-on animations.
        for t in (0, 1):
            for e in self.sub_q[t]:
                if e["out"].state != "out":
                    self.swap_identity(e["out"], e)
            self.sub_q[t] = []

    def update_injuries(self, dt): # Advance injury timers and recovery state for all players.
        return

    def maybe_injury_from_tackle(self, p, kind): # Apply the configured injury chance after a tackle.
        if self.mode != "play" or p.role == "GK" or p.state in ("out", "leaving") or p.red or p.injured:
            return False
        sx, sy = w2s(p.wx, p.wv)
        cx, cy = self.cam_int()
        vw, vh = (WIN_W, WIN_H) if self.scroll else (FW, FH)
        if not (cx - 2 <= sx <= cx + vw + 2 and cy - 2 <= sy + Y_OFFSET <= cy + vh + 2):
            return False
        chance = (0.035 if kind == "slide" else 0.012) * self.injury_k(p) # Fitness: injury proneness.
        if random.random() < chance:
            self.begin_injury(p)
            return True
        return False

    def begin_injury(self, p): # Start the injury state and its associated player animation.
        self.stoppage_target += 0.85
        b = self.ball
        b.owner, b.vx, b.vv, b.vz, b.z = None, 0.0, 0.0, 0.0, 0.0
        self.mode = "injury"
        p.injured = True
        self.injury = dict(p=p, t=0.0, team=b.last_team if b.last_team is not None else 1 - p.team)
        p.state, p.act, p.tx, p.tv, p.path = "down", None, None, None, None
        p.vx = p.vv = 0.0
        self.stats["injured"][p.team] += 1
        self.log_event(tr("ev.injury", p=p.label(), team=TEAM_NAMES[p.team]), secs=5, team=p.team)
        self.audio.play("whistle_long", 0.7)
        self.audio.react("save")
        for q in self.players:
            if q is not p and q.state not in ("out", "leaving", "action"):
                q.state, q.tx, q.tv, q.tag = "free", None, None, None

    def update_injury(self, dt): # Advance the current injury and recovery sequence.
        inj = self.injury
        inj["t"] += dt
        if inj["t"] < 4.5:
            return
        p = inj["p"]
        p.state = "free"
        p.injured = True
        self.log_event(tr("ev.injury_stays", name=p.name), secs=3, team=p.team)
        b = self.ball
        self.injury = None
        self.start_restart("free", inj["team"], (b.wx, b.wv))
        self.log_event(tr("ev.restart_free", team=TEAM_NAMES[inj["team"]]), secs=3, team=inj["team"])
