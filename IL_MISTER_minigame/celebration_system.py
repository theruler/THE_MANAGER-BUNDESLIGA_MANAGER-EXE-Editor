import math
import random

from game_utils import clamp, unit
from geometry import L, V_BOT, V_MID, V_MIN_P, V_SPOT, V_TOP
from lang import tr
from match_config import TEAM_NAMES
from physics_system import PLAYER_SPEED


CELE_KINDS = (("huddle", 2), ("slide", 2), ("lift", 2), ("brawl", 2), ("train", 2), ("dance", 2)) # Celebration types and participant counts.
T_CELE, T_AFTER = 5.6, 2.6 # T_CELE: celebration duration; T_AFTER: post-celebration delay.
GOAL_RETURN_DELAY = 4.0 # Seconds after a goal before the team that does not celebrate starts walking back to its kickoff positions.

class CelebrationMixin: # Player and team goal-celebration sequences.
    def goto(self, p, x, v): # Set a player's target position and movement speed for an animation.
        p.tx, p.tv = clamp(x, 7.0, L - 7.0), clamp(v, V_MIN_P + 1.0, V_BOT - 1.0)

    def cele_walk_home(self, g, t): # During the goal sequence: whoever is not celebrating walks back to his kickoff position; the conceding team first waits GOAL_RETURN_DELAY seconds.
        team = g["team"]
        for p in self.players:
            if p.state in ("out", "leaving") or p.busy():
                continue
            if p.state == "cele" and not g["released"]:
                continue
            if not g["own"] and p.team != team and t < GOAL_RETURN_DELAY:
                p.tx = p.tv = None
                continue
            in_cele = (not g["own"]) and (not g["released"]) and p.idx in g["part"] and p.team == team
            if in_cele and p.role != "GK":
                continue
            p.tx, p.tv = self.home_pos(p, L / 2, V_SPOT, False)

    def pose(self, p): # Switch a player to the appropriate celebration pose.
        p.tx = p.tv = None
        if p.state != "cele":
            p.state = "cele"
            p.cele_t = random.random()

    def cele_pose_if_near(self, p, x, v, r=3.0): # Apply the celebration pose when the player reaches its target area.
        self.goto(p, x, v)
        if math.hypot(p.wx - x, p.wv - v) < r:
            self.pose(p)

    def cele_huddle(self, g, t, sc, mates): # Arrange teammates for the huddle celebration.
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.5 and sc.state != "cele":
            self.goto(sc, sc.wx + d * 40, sc.wv)
        else:
            self.pose(sc)
        for p in mates:
            if t > 0.5:
                ang = (p.idx * 2.399) % 6.283
                self.cele_pose_if_near(p, sc.wx + 9 * math.cos(ang), sc.wv + 6 * math.sin(ang), 4.0)

    def cele_slide(self, g, t, sc, mates): # Run the sliding celebration sequence.
        d = self.att[g["team"]]
        gx = L if d > 0 else 0.0
        top = sc.wv < V_MID
        fx, fv = gx - d * 4.0, (V_TOP + 3.0 if top else V_BOT - 3.0)
        order = sorted(mates, key=lambda q: math.hypot(q.wx - fx, q.wv - fv))
        crew = [sc] + order[:4]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        for i, p in enumerate(mates + [sc]):
            st = g["s"].setdefault(p.idx, {"ph": 0})
            if p.busy():
                continue
            dist = math.hypot(fx - p.wx, fv - p.wv)
            if p in crew:
                k = crew.index(p)
                if st["ph"] == 0:
                    self.goto(p, fx, fv)
                    if dist < 36 and t > 0.3 + 0.28 * k:
                        ux, uv = unit(fx - p.wx, fv - p.wv)
                        self.begin_action(p, "slide", "E" if ux >= 0 else "W", dx=ux, dv=uv, speed=clamp((dist - 4.0) / 0.366, 45.0, 115.0), cele=True, hold=0.54)
                        p.act_cd = 5.0
                        st["ph"] = 1
                elif st["ph"] == 1:
                    st["ph"] = 2
                else:
                    self.cele_pose_if_near(p, fx - d * (2.0 + 2.5 * k), fv + (4.0 * k if top else -4.0 * k) * 0.6, 3.0)
            else:
                ux, uv = unit(p.wx - fx, p.wv - fv)
                self.cele_pose_if_near(p, fx + ux * 55, fv + uv * 55, 4.0)

    def cele_lift(self, g, t, sc, mates): # Run the celebration in which teammates lift the scorer.
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.1:
            self.goto(sc, sc.wx + d * 18, sc.wv)
        elif sc.state not in ("cele", "down"):
            self.pose(sc)
        crew = sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
        for k, p in enumerate(crew):
            if p.busy():
                continue
            if k < 4:
                ang = k * math.pi / 2 + 0.6
                self.cele_pose_if_near(p, sc.wx + 4.5 * math.cos(ang), sc.wv + 3.2 * math.sin(ang), 2.5)
            else:
                ang = (p.idx * 2.399) % 6.283
                self.cele_pose_if_near(p, sc.wx + 13 * math.cos(ang), sc.wv + 9 * math.sin(ang), 3.5)
        near = sum(1 for p in crew[:4] if p.state == "cele")
        t0 = 2.0
        if t > t0 and near >= 2 and t < T_CELE - 0.4:
            ph = (t - t0) / 0.95
            sc.state, sc.tx, sc.tv = "down", None, None
            sc.lift = 7.0 + 7.0 * abs(math.sin(math.pi * ph)) ** 0.8
            if ph % 1.0 < 0.05 and int(ph) != g["s"].get("toss"):
                g["s"]["toss"] = int(ph)
                self.audio.play("bounce", 0.4)
        else:
            sc.lift = max(0.0, sc.lift - 40 * 0.0167)

    def cele_train(self, g, t, sc, mates): # Arrange the players for the train celebration.
        d = self.att[g["team"]]
        gx = L if d > 0 else 0.0
        g["part"] = {p.idx for p in mates} | {sc.idx}
        wps = [(gx - d * 40, V_TOP + 10), (gx - d * 70, V_MID), (gx - d * 40, V_BOT - 10), (gx - d * 95, V_MID)]
        i = g["s"].setdefault("wp", 0)
        wx, wv = wps[i % len(wps)]
        self.goto(sc, wx, wv)
        if math.hypot(sc.wx - wx, sc.wv - wv) < 6:
            g["s"]["wp"] = i + 1
        chain = [sc] + sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
        for k in range(1, len(chain)):
            q, pr = chain[k], chain[k - 1]
            if q.busy():
                continue
            ux, uv = unit(pr.vx, pr.vv, (-d, 0.0))
            self.goto(q, pr.wx - ux * 6.0, pr.wv - uv * 6.0)
            q.speed = max(q.speed, PLAYER_SPEED * 1.0)
        if t > T_CELE - 1.0:
            for p in chain:
                self.pose(p)

    def cele_dance(self, g, t, sc, mates): # Run the coordinated dance celebration.
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.0:
            self.goto(sc, sc.wx + d * 14, sc.wv)
        elif not sc.busy() and t < T_CELE - 0.8:
            n = g["s"].get("moon", 0)
            g["s"]["moon"] = n + 1
            sgn = d if n % 2 == 0 else -d
            self.begin_action(sc, "moonwalk", "E" if sgn >= 0 else "W", dx=sgn, dv=0.0, vel=(sgn * 24.0, 0.0), repeat=6)
        elif t >= T_CELE - 0.8 and not sc.busy():
            self.pose(sc)
        for k, p in enumerate(sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))):
            if p.busy():
                continue
            ang = math.pi * (0.35 + 1.3 * k / max(1, len(mates) - 1))
            self.cele_pose_if_near(p, sc.wx + 17 * math.cos(ang), sc.wv + 11 * math.sin(ang) * 0.9, 3.0)

    def cele_brawl(self, g, t, sc, mates): # Run the staged group-brawl celebration.
        if g["pairs"] is None:
            center_x = clamp(L * 0.5 - self.att[g["team"]] * 22.0, L * 0.25, L * 0.75)
            center_v = clamp(V_MID + random.uniform(-8.0, 8.0), V_TOP + 8.0, V_BOT - 8.0)
            g["s"]["brawl_center"] = (center_x, center_v)
            self.goto(sc, center_x, center_v)
            ma = sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
            grp = [sc] + ma[:5]
            g["pairs"] = [(grp[i], grp[i + 1]) for i in range(0, len(grp) - 1, 2)]
            self.log_event(tr("ev.cele_headbutt"), secs=3, team=g["team"])
            g["part"] = {q.idx for pr in g["pairs"] for q in pr} | {sc.idx}
            g["part"] |= {q.idx for q in mates}
        for k, (a, b2) in enumerate(g["pairs"]):
            st = g["s"].setdefault(("pair", k), {"n": 0, "next": 1.2 + 0.35 * k})
            ang = k * 2.0944 + 0.5
            center_x, center_v = g["s"].get("brawl_center", (sc.wx, sc.wv))
            mx, mv = center_x + 12 * math.cos(ang), center_v + 8 * math.sin(ang)
            ux, uv = unit(math.cos(ang + 1.57), math.sin(ang + 1.57))
            for q, sgn in ((a, -1), (b2, 1)):
                if q.busy() or q is sc and t < 0.0:
                    continue
                if q.state == "cele":
                    q.state = "free"
                if q.role != "GK":
                    self.goto(q, mx + sgn * ux * 2.6, mv + sgn * uv * 1.8)
            if a.busy() or b2.busy():
                continue
            if math.hypot(a.wx - b2.wx, a.wv - b2.wv) < 8.0 and t >= st["next"] and t < T_CELE - 0.3:
                att_, def_ = (a, b2) if st["n"] % 2 == 0 else (b2, a)
                hx, hv = unit(def_.wx - att_.wx, def_.wv - att_.wv)
                self.begin_action(att_, "header", "E" if hx >= 0 else "W", dx=hx, dv=hv, power=0.0, lift=0.0, kind="pass", show=True)
                att_.vx, att_.vv = hx * 36.0, hv * 36.0
                def_.vx, def_.vv = def_.vx + hx * 22.0, def_.vv + hv * 22.0
                self.audio.play("head", 0.55)
                st["n"] += 1
                st["next"] = t + 0.85
                if st["n"] >= 2 and random.random() < 0.30:
                    self.begin_action(def_, "fall", "E" if hx >= 0 else "W")
                    st["next"] = t + 1.6
                    offender = att_ if random.random() < 0.5 else def_
                    if offender.yellow == 0 and not offender.red and random.random() < 0.10:
                        offender.yellow += 1
                        self.stats["yellow"][offender.team] += 1
                        self.ref.card, self.ref.card_t = "Y", 1.4
                        self.log_event(tr("ev.card_brawl", p=offender.label(), team=TEAM_NAMES[offender.team]), (255, 230, 70), 3)
                        self.audio.react("card")
