import math
import random

from animation_config import ACT_SPEC, CELE_SLIDE, SLOWMO_KEYS, STOP_FLIP
from ball_model import G, STANDING_BALL_OFFSET, step_ball_physics
from game_utils import clamp, dir8, unit
from geometry import (
    BAR_HI, BOX_D, depth_k, depth_slow, depth_v_k, FW, GOAL_D, GOAL_H, GOAL_NET_H, HALF_MOUTH, in_box_fn, L,
    POST_T, s2w, screen_x_of, V_BOT, V_GC, V_MAX_P, V_MID, V_MIN_P, V_TOP, w2s,
)
from lang import tr
from match_config import CARRY_TOL_T, CARRY_TOL_V, INJURED_SPEED_K, REF_NEAR, TEAM_NAMES
from sprite_data import action_sids, run_cycle, stand_sid, team_sprite_offset


PLAYER_SPEED = 52.0 # Base maximum movement speed for outfield players.
TAKER_STALL_SECS = 1.0 # A restart taker that makes no progress towards his target for this long is moved onto it.
DRIBBLE_OFF = 6.0 # Offset between a player position and the ball while dribbling.
REACH_FIRST = 9.0 # Initial reach distance used when evaluating ball control.
PLAYER_CATCH_RADIUS = 4.5 # Normal ground-ball control radius for outfield players.
PLAYER_INTERCEPT_RADIUS = 3.8 # Reduced control radius used by defenders intercepting a pass in flight.
PLAYER_CATCH_HEIGHT = 5.0 # Maximum ball height for normal outfield-player control.
AIR_MIN_Z = 3.0 # Minimum ball height treated as an aerial contest.
THROW_HOLD_Z = 10.0 # Ball height used while a player is holding a throw-in.
THROW_RELEASE_Z = 11.0 # Ball height at which a throw-in releases the ball.
STRIKE_REACH = {  # Maximum contact distance by action type; tune individual entries to change reach.
    "kick": (11.0, -1.0, 9.5),
    "header": (11.0, 4.0, 24.0),
    "bicycle": (13.0, 7.0, 28.0),
    "header_dive": (13.0, 4.0, 18.0),
}
KEEPER_CATCH_RADIUS = 5.5 # Ground-space catch radius for goalkeeper saves.
KEEPER_CATCH_HEIGHT = 10.5 # Maximum ball height for goalkeeper catching attempts.


# ---- Goalkeeper save model (see PhysicsMixin.keeper_save_chance) ----
KEEPER_SAVE_BASE = 0.86 # Save chance for a slow, central ball hit straight at a keeper of average skill.
KEEPER_SPEED_K = 0.0017 # Chance lost per unit of ball speed above 140.
KEEPER_SKILL_K = 0.30 # Chance gained per point of keeper skill above 0.75.
KEEPER_REACH_K = 0.030 # Chance lost per world unit the keeper has to stretch.
KEEPER_CORNER_K = 0.22 # Extra chance lost for a shot that crosses the goal line at the post (scaled by distance from centre).
KEEPER_FAR_START, KEEPER_FAR_FULL = 45.0, 95.0 # Shot distance (world units) where foresight starts / is complete.
KEEPER_READ_BONUS = 0.30 # Save chance gained at full foresight.
KEEPER_FREEKICK_READ = 0.65 # Minimum foresight for free-kick shots (the keeper sees them coming).
KEEPER_SAVE_MIN, KEEPER_SAVE_MAX = 0.15, 0.90 # Clamp for the final save chance.
FAST_BALL_SPEED = 215.0 # Above this speed outfield players cannot simply take control of the ball.
BLOCK_CHANCE = 0.25 # Probability that a defender touching a hard shot deflects it.

class PhysicsMixin: # Ball motion, player movement, collisions, and action execution.

    def simulate_ball(self, key, kw): # Simulate the ball trajectory and report its predicted path or contacts.
        b = self.ball
        power, lift = kw.get("power", 150.0), kw.get("lift", 0.0)
        if key in ("header", "header_dive"):
            power, lift = power * 0.8, max(lift, 18.0)
        elif key == "bicycle":
            power, lift = max(power, 235.0), max(lift, 28.0)
        x, v, z = b.wx, b.wv, max(b.z, 0.5)
        if key == "throw" and self.restart:
            x, v = self.restart["pos"]
            z = THROW_RELEASE_Z
        ds = depth_slow(kw["dx"], kw["dv"])
        vx, vv, vz = kw["dx"] * power * ds, kw["dv"] * power * ds, lift
        pts, t, h, nxt = [(x, v, z, power)], 0.0, 1.0 / 240.0, 0.1
        while t < 3.6 and len(pts) < 40:
            x, v, z, vx, vv, vz = step_ball_physics(
                x, v, z, vx, vv, vz, h, ds
            )
            t += h
            if t >= nxt:
                pts.append((x, v, z, math.hypot(vx, vv)))
                nxt += 0.1
            if (z < 0.05 and math.hypot(vx, vv) < 6.0) or x < -4.0 or x > L + 4.0 or v < V_TOP - 12.0 or v > V_BOT + 12.0:
                break
        return pts

    def build_shot_preview(self, x0, y0, x1, y1, act=None): # Build a predicted ball path for the shot-preview display.
        plan = self.gesture_plan(x0, y0, x1, y1, act)
        if plan is None or not self.can_kick_now():
            return None
        kp = self.ground_plan(self.cp, plan[0], plan[1][0], plan[1][1], plan[2], True)
        pts = self.simulate_ball("kick", dict(dx=kp["dx"], dv=kp["dv"],
                                               power=kp["power"], lift=kp["lift"]))
        target = None
        if kp["target"] is not None:
            target = (kp["target"].wx, kp["target"].wv)
        return {"points": pts, "target": target}

    def throw_in_out(self): # Place the ball into the out-of-play state and set its outward velocity.
        b = self.ball
        b.owner = None
        b.out_t = 0.0
        out_dir = -1.0 if b.wv < V_TOP else 1.0
        if b.vv * out_dir < 24.0:
            b.vv = out_dir * 24.0
        team = 1 - b.last_team
        self.begin_ball_out("throw", team, (clamp(b.wx, 8.0, L - 8.0), V_TOP if b.wv < V_TOP else V_BOT))
        self.log_event(tr("ev.throw", team=TEAM_NAMES[team]), secs=2.5, team=team)
        self.audio.play("whistle", 0.6)

    def check_ball_events(self, prev, carried=False, h=0.0): # Resolve ball events such as goal-line crossings, out-of-play, and contacts.
        b = self.ball
        px, pv, pz = prev
        for gx in (0.0, L):
            crossed = (px >= gx > b.wx) if gx == 0.0 else (px <= gx < b.wx)
            if not crossed:
                continue
            t = (px - gx) / (px - b.wx) if px != b.wx else 0.0
            vc = pv + (b.wv - pv) * t
            zc = pz + (b.z - pz) * t
            off = abs(vc - V_GC)
            att_team, def_team = self.teams_at(gx)
            sgn = 1.0 if gx == 0.0 else -1.0
            if zc >= GOAL_H + BAR_HI and off <= HALF_MOUTH + POST_T:
                b.over_bar = True
            if zc < GOAL_H + BAR_HI:
                if off <= HALF_MOUTH:
                    if GOAL_H <= zc <= GOAL_H + BAR_HI:
                        self.ball_hits_frame(gx, "bar", vc)
                    elif zc < GOAL_H:
                        self.score_goal(att_team, gx)
                    return
                if off <= HALF_MOUTH + POST_T:
                    if zc <= GOAL_H + BAR_HI:
                        self.ball_hits_frame(gx, "post", vc)
                        return

            if carried:
                b.owner = None
                b.vx = b.vv = b.vz = 0.0
            if b.last_team == def_team:
                x = 1.5 if gx == 0.0 else L - 1.5
                v = V_TOP + 1.5 if b.wv < V_MID else V_BOT - 1.5
                self.begin_ball_out("corner", att_team, (x, v))
                self.log_event(tr("ev.corner", team=TEAM_NAMES[att_team]), secs=3, team=att_team)
            else:
                self.log_missed()
                self.begin_ball_out("goalkick", def_team, (gx + sgn * 0.05 * L, V_GC + random.uniform(-0.5, 0.5) * HALF_MOUTH))
                self.log_event(tr("ev.goalkick", team=TEAM_NAMES[def_team]), secs=3, team=def_team)
            self.audio.play("whistle")
            if b.shot_team is not None:
                self.audio.react("near")
            return
        over = max(V_TOP - b.wv, b.wv - V_BOT)
        if carried:
            if over <= 0.0:
                b.out_t = 0.0
                return
            b.out_t += h
            if math.hypot(self.ref.wx - b.wx, self.ref.wv - b.wv) > REF_NEAR:
                if b.out_t > CARRY_TOL_T or over > CARRY_TOL_V:
                    self.throw_in_out()
            elif over > 0.3:
                self.throw_in_out()
            return
        if over > 0.0:
            self.throw_in_out()

    def ball_hits_frame(self, gx, what, vc): # Check whether the ball contacts the goal frame or related structure.
        b = self.ball
        b.ds = 1.0
        sgn = 1.0 if gx == 0.0 else -1.0
        b.wx = gx + sgn * 0.8
        b.pass_active = False
        if what == "bar":
            b.vx = abs(b.vx) * 0.5 * sgn
            b.vz = -abs(b.vz) * 0.4 - 25.0
            b.z = max(0.0, GOAL_H - 2.2)
        else:
            b.vx = abs(b.vx) * 0.55 * sgn
            b.vv = (b.vv * -0.5) + random.uniform(-25, 25)
        self.audio.play("bar" if what == "bar" else "post", 1.0)
        evento = "bar" if what == "bar" else "post"
        if b.last is not None and b.shot_team is not None:
            self.log_event(tr("ev." + evento, p=b.last.label(), team=TEAM_NAMES[b.last.team]), secs=2.5, team=b.last.team)
        else:
            self.log_event(tr("ev." + evento + "_plain"), secs=2.5, team=b.last_team)
        self.audio.react("near")

    def ball_pred(self, t): # Predict the ball position at a future time.
        b = self.ball
        if b.owner is not None:
            return b.owner.wx, b.owner.wv
        k = (0.7 if b.z < 1.0 else 0.14) * b.ds
        f = (1 - math.exp(-k * t)) / k
        return b.wx + b.vx * f, b.wv + b.vv * f

    def land_time(self): # Estimate when the airborne ball will land.
        b = self.ball
        if b.z < 0.5 and abs(b.vz) < 5:
            return 0.0
        return max(0.0, (b.vz + math.sqrt(max(0.0, b.vz * b.vz + 2 * G * b.z))) / G)

    def update_ball(self, dt): # Advance the ball physics state and resolve ball movement.
        b = self.ball
        n = 2
        h = dt / n
        for _ in range(n):
            prev = (b.wx, b.wv, b.z)
            if b.owner is not None:
                self.dribble(h)
            elif self.mode in ("play", "goal") or (self.mode == "outball" and self.outball["phase"] == "roll"):
                self.free_ball(h)
            self.ball_goal_collide(prev)
            if self.mode == "play":
                if b.owner is None:
                    self.check_ball_events(prev)
                    if self.mode != "play":
                        break
                else:
                    self.check_ball_events(prev, carried=True, h=h)
                    if self.mode != "play":
                        break
                self.check_possession()
        b.age += dt
        if b.age > 2.5:
            b.intended = None
            b.pass_active = False
        b.spin += math.hypot(b.vx, b.vv) * dt
        px, gy = w2s(b.wx, b.wv)
        if px < 2.0 or px > FW - 2.0:
            px = clamp(px, 2.0, FW - 2.0)
            b.wx = s2w(px, gy)[0]
            b.vx *= -0.3
        b.px, b.gy = px, gy

    def ball_goal_collide(self, prev): # Resolve ball collisions with the goal frame and net.
        b = self.ball
        over = bool(getattr(b, "over_bar", False))
        if not over and b.z <= GOAL_H + BAR_HI:
            b.wx, b.wv, hit = self.goal_solid(b.wx, b.wv, prev[0], prev[1], True)
            if hit == 1:
                b.vx = -b.vx * 0.25
            elif hit == 2:
                b.vv = -b.vv * 0.3
            if hit and b.owner is None and abs(b.vx) + abs(b.vv) > 25.0:
                self.audio.play("net", 0.6)
        v0, v1 = V_GC - HALF_MOUTH - POST_T, V_GC + HALF_MOUTH + POST_T
        for gx, out in ((0.0, -1.0), (L, 1.0)):
            in_depth = 0.0 < out * (b.wx - gx) < GOAL_D and v0 < b.wv < v1
            if in_depth and over:
                if b.z < GOAL_NET_H:
                    b.z = GOAL_NET_H
                    if b.vz < 0.0:
                        b.vz = -b.vz * 0.35
                    b.vx *= 0.8
                    b.vv *= 0.8
            elif in_depth and GOAL_NET_H < b.z <= GOAL_H + BAR_HI:
                b.z = GOAL_NET_H
                b.vz = -abs(b.vz) * 0.3
            elif abs(b.wx - gx) > GOAL_D + 2.0:
                b.over_bar = False

    def dribble(self, h): # Update the ball position while it is controlled by a player.
        b = self.ball
        o = b.owner
        if o.state in ("out", "leaving") or o.fallen():
            b.owner = None
            return
        sp = math.hypot(o.vx, o.vv)
        b.own_t += h
        gk_dive = o.role == "GK" and o.state == "action" and o.act is not None and o.act.get("key") == "dive"
        if o.role == "GK":
            tx, tv = o.wx + self.att[o.team] * (1.6 if gk_dive else 1.2), o.wv
            k = 1.0
        else:
            off = (DRIBBLE_OFF + 1.7 * math.sin(o.stride * 0.62)) if sp > 8 else STANDING_BALL_OFFSET
            tx, tv = o.wx + o.dx * off, o.wv + o.dv * off * 0.8
            k = min(1.0, self.touch_rate(o) * h) # Skill: how tightly the ball follows the dribbler.
            if self.mode == "play" and self.lose_ball_on_turn(o, h): # Skill: a sharp turn can cost a loose touch.
                b.owner = None
                b.pass_active, b.intended, b.shot_team = False, None, None
                b.vx, b.vv, b.vz = o.vx * 1.25 + o.dx * 14.0, o.vv * 1.25 + o.dv * 14.0, 0.0
                o.cool = 0.35
                return
        b.wx += (tx - b.wx) * k
        b.wv += (tv - b.wv) * k
        b.vx, b.vv, b.vz = o.vx, o.vv, 0.0
        b.ds = 1.0
        if o.role == "GK":
            b.z = max(0.0, o.lift - 1.0) if gk_dive else 4.0
        elif b.own_t < 1.0:
            b.z = 2.2 * (1.0 - b.own_t) * abs(math.sin(b.own_t * 14.0))
        else:
            b.z = 0.0
        b.last, b.last_team = o, o.team

    def free_ball(self, h): # Release the ball from player control and apply the required free-ball state.
        b = self.ball
        kk = depth_k(b.wv)
        kv = depth_v_k(b.wv, b.wx)
        b.wx += b.vx * h * kk
        b.wv += b.vv * h * kv
        b.z += b.vz * h
        b.vz -= G * h
        if b.z <= 0.0:
            b.z = 0.0
            if b.vz < -35.0:
                if b.vz < -50:
                    self.audio.play("bounce", min(1.0, -b.vz / 110.0))
                b.vz = -b.vz * 0.55
                b.vx *= 0.88
                b.vv *= 0.88
            else:
                b.vz = 0.0
        k = 0.7 if b.z < 0.05 else 0.14
        if self.mode == "goal":
            k = 2.6
        elif self.mode == "outball" and b.z < 0.05:
            k = 0.42
        f = math.exp(-k * h * b.ds)
        b.vx *= f
        b.vv *= f
        if b.z < 0.05 and math.hypot(b.vx, b.vv) < 3.0:
            b.vx = b.vv = 0.0

    def give_ball(self, p): # Transfer ball possession to the specified player.
        b = self.ball
        if p.role == "GK":
            self.log_missed()
        if b.tactical_pass and b.intended is p and b.last is not None and b.last is not p:
            self.log_event(tr("ev.targeted_pass", a=b.last.label(), b=p.label()), secs=2.5, team=b.last.team)
        b.tactical_pass = False
        b.pass_active = False
        b.owner = p
        if self.user_team is not None and p.team == self.user_team and self.mode == "play" and p.state not in ("out", "leaving", "subin", "subout", "tunnel") and not p.red:
            self.sel_hold_until = 0.0
            self.select_player(p, quiet=True)
        b.last, b.last_team = p, p.team
        b.vx = b.vv = b.vz = 0.0
        b.z = 0.0
        b.own_t = 0.0
        b.intended = None
        b.shot_team = None
        p.hold_t = 0.0
        p.dec = random.uniform(0.15, 0.4)
        p.cool = 0.0

    def check_possession(self): # Determine whether a player can take or retain possession of the ball.
        b = self.ball
        if b.owner is not None or self.mode != "play":
            return
        best = None
        sp = math.hypot(b.vx, b.vv)
        for p in self.players:
            if p.state in ("out", "leaving") or p.cool > 0:
                continue
            if p.state == "action" and p.act["key"] != "dive":
                continue
            d = math.hypot(p.wx - b.wx, p.wv - b.wv)
            gk = p.role == "GK"
            if gk and b.pen and not b.pen_save and b.last_team != p.team:
                continue
            catch_radius = KEEPER_CATCH_RADIUS if gk else PLAYER_CATCH_RADIUS
            if not gk and b.pass_active and b.last_team is not None and p.team != b.last_team:
                catch_radius = min(catch_radius, PLAYER_INTERCEPT_RADIUS * self.intercept_k(p)) # Form: interception.
            if d > catch_radius:
                continue
            if b.z > (KEEPER_CATCH_HEIGHT if gk else PLAYER_CATCH_HEIGHT):
                continue
            if sp > FAST_BALL_SPEED and b.intended is not p and not gk and not p.ctrl:
                if b.shot_team is not None and p.team != b.shot_team and self.try_block(p, sp):
                    return
                continue
            if gk and b.last_team != p.team and b.shot_team is not None:
                # A shot gives the goalkeeper one attempt; if it misses, the ball continues.
                if b.gk_attempted:
                    continue
                b.gk_attempted = True
                save_chance = self.keeper_save_chance(p, sp, d)
                if random.random() > save_chance:
                    continue
                self.register_save(p)
                if sp > 150.0:
                    self.gk_parry(p, punch=(sp > 215.0 and random.random() < 0.20))
                else:
                    self.give_ball(p)
                return
            if gk and b.last_team != p.team and not p.busy() and p.act_cd <= 0 and (sp > 110 or b.z > 6.0):
                p.act_cd = 0.9
                if random.random() < 0.28 + 0.25 * (1.0 - p.skill) + (0.2 if b.z > 8.0 else 0.0):
                    self.begin_action(p, "punch", "E" if b.wx > p.wx else "W", assist=True)
                    p.cool = 0.5
                    return
            if gk and sp > 230 and b.last_team != p.team and random.random() > 0.25 + 0.6 * p.skill:
                self.gk_parry(p, punch=random.random() < 0.4)
                return
            if best is None or d < best[0]:
                best = (d, p)
        if best:
            p = best[1]
            hot = sp > 150
            self.give_ball(p)
            if hot:
                self.audio.play("head", 0.5)

    def keeper_punch(self, p): # Attempt a goalkeeper punch on an incoming ball.
        b = self.ball
        b.ds = 1.0
        if b.owner is not None or math.hypot(b.wx - p.wx, b.wv - p.wv) > 17.0 or b.z > 26.0 or self.mode != "play":
            return False
        d = self.att[p.team]
        side = 1.0 if b.wv >= V_GC else -1.0
        self.log_missed()
        b.pass_active = False
        b.vx = d * random.uniform(105.0, 175.0)
        b.vv = side * random.uniform(15.0, 85.0)
        b.vz = random.uniform(38.0, 72.0)
        b.z = max(b.z, 4.0)
        b.last, b.last_team, b.intended = p, p.team, None
        b.shot_team = None
        b.age = 0.0
        p.cool = 0.5
        self.audio.play("head", 0.9)
        self.audio.react("save")
        self.log_event(tr("ev.punch", p=p.label()), secs=2, team=p.team)
        return True

    def gk_parry(self, p, punch=False): # Deflect the ball away during a goalkeeper save attempt.
        b = self.ball
        b.ds = 1.0
        d = self.att[p.team]
        if punch:
            b.z = max(b.z, 3.0)
            return self.keeper_punch_free(p)
        self.log_missed()
        b.pass_active = False
        if random.random() < 0.35:
            b.vx = -d * max(60.0, abs(b.vx) * 0.3)
            b.vv = random.choice((-1.0, 1.0)) * random.uniform(80, 120)
            b.vz = random.uniform(10, 35)
        else:
            b.vx = d * abs(b.vx) * 0.35
            b.vv = b.vv * 0.5 + random.uniform(-45, 45)
            b.vz = random.uniform(15, 55)
        b.last, b.last_team, b.intended = p, p.team, None
        p.cool = 0.35
        self.audio.play("kick", 0.8)
        self.audio.react("save")
        self.log_event(tr("ev.save", p=p.label()), secs=2, team=p.team)

    def keeper_punch_free(self, p): # Attempt a goalkeeper punch when the ball is not carried by a player.
        b = self.ball
        b.ds = 1.0
        d = self.att[p.team]
        side = 1.0 if b.wv >= V_GC else -1.0
        self.log_missed()
        b.pass_active = False
        b.vx = d * random.uniform(95.0, 160.0)
        b.vv = side * random.uniform(20.0, 90.0)
        b.vz = random.uniform(30.0, 60.0)
        b.last, b.last_team, b.intended = p, p.team, None
        b.shot_team = None
        p.cool = 0.4
        self.audio.play("head", 0.9)
        self.audio.react("save")
        self.log_event(tr("ev.punch", p=p.label()), secs=2, team=p.team)

    @staticmethod
    def goal_solid(x, v, px, pv, ball=False): # Check collision against the solid parts of the goal structure.
        if math.hypot(x - px, v - pv) > 8.0:
            return x, v, 0
        hit = 0
        v0, v1 = V_GC - HALF_MOUTH, V_GC + HALF_MOUTH
        for gx, out in ((0.0, -1.0), (L, 1.0)):
            d, dp = out * (x - gx), out * (px - gx)
            inside_now = 0.0 < d < GOAL_D and v0 < v < v1
            inside_prev = 0.0 < dp < GOAL_D and v0 < pv < v1
            if inside_prev:
                if d >= GOAL_D - 0.4:
                    x, hit = gx + out * (GOAL_D - 0.4), 1
                if v <= v0 + 0.4:
                    v, hit = v0 + 0.4, 2
                elif v >= v1 - 0.4:
                    v, hit = v1 - 0.4, 2
                if d <= 0.0 and not v0 < v < v1:
                    x, hit = gx - out * 0.1, 1
            elif inside_now:
                if dp > 0.0:
                    if pv <= v0:
                        v, hit = v0 - 0.4, 2
                    elif pv >= v1:
                        v, hit = v1 + 0.4, 2
                    else:
                        x, hit = gx + out * (GOAL_D + 0.4), 1
        return x, v, hit

    def clamp_player(self, p): # Keep the player inside the legal movement bounds for the current state.
        vmax = V_MAX_P if (p.state == "leaving" or self.mode != "play") else V_BOT + 0.5
        vmin = V_MIN_P
        rs = self.restart if self.mode == "restart" else None
        if rs is not None and rs.get("kind") == "throw" and rs.get("taker") is p:
            _throw_x, throw_v = self.taker_stand(rs)
            vmin, vmax = min(vmin, throw_v), max(vmax, throw_v)
        taker_pts = self.taker_points(p, rs)
        for _qx, qv in taker_pts: # Corner / goal-kick takers may need to stand where the ball is, even on the pitch edge.
            vmin, vmax = min(vmin, qv - 0.5), max(vmax, qv + 0.5)
        p.wv = clamp(p.wv, vmin, vmax)
        if p.lx is not None:
            p.wx, p.wv, _hit = self.goal_solid(p.wx, p.wv, p.lx, p.lv)
        if (rs is not None and rs.get("kind") == "goalkick" and p.team != rs["team"]
                and p.role != "GK" and not p.ctrl and p.state not in ("out", "leaving")):
            ad = self.att[rs["team"]]
            own_gx = 0.0 if ad > 0 else L
            if in_box_fn(p.wx, p.wv, own_gx):
                p.wx = own_gx + ad * (BOX_D + 0.5)
                p.vx = 0.0
        px, gy = w2s(p.wx, p.wv)
        lo, hi = 6.5, FW - 6.5
        for qx, qv in taker_pts:
            qs = w2s(qx, qv)[0]
            lo, hi = min(lo, qs - 0.5), max(hi, qs + 0.5)
        if px < lo or px > hi:
            px = clamp(px, lo, hi)
            p.wx = s2w(px, gy)[0]
        p.lx, p.lv = p.wx, p.wv

    def taker_points(self, p, rs): # Ball and walking target of a restart taker (empty for everybody else).
        if rs is None or rs.get("taker") is not p or rs.get("kind") == "throw":
            return ()
        pts = [(self.ball.wx, self.ball.wv)]
        if p.tx is not None:
            pts.append((p.tx, p.tv))
        return pts

    def taker_watchdog(self, p, rs, dt, sp): # A taker that walks on the spot without getting closer to his target is placed on it.
        if rs is None or rs.get("taker") is not p or p.tx is None or p.state != "free":
            p.stall_t = 0.0
            return
        d = math.hypot(p.tx - p.wx, p.tv - p.wv)
        if d <= 2.0 or sp <= 5.0 or d < getattr(p, "stall_d", 1e9) - 0.6:
            p.stall_t, p.stall_d = 0.0, d
            return
        p.stall_t = getattr(p, "stall_t", 0.0) + dt
        if p.stall_t > TAKER_STALL_SECS:
            p.wx, p.wv, p.vx, p.vv = p.tx, p.tv, 0.0, 0.0
            p.stall_t, p.stall_d = 0.0, 0.0
            self.post_move(p)

    def post_move(self, p): # Resolve movement effects after the player has moved.
        p.sx, p.sy = w2s(p.wx, p.wv)
        sp = math.hypot(p.vx, p.vv)
        if sp > 9 and p.state != "action":
            x1, y1 = w2s(p.wx + p.vx * 0.06 * depth_k(p.wv),
                         p.wv + p.vv * 0.06 * depth_v_k(p.wv, p.wx))
            nd = dir8(x1 - p.sx, y1 - p.sy, True)
            if nd and nd != p.face and p.face_t <= 0:
                p.face, p.face_t = nd, 0.09
            ux, uv = unit(p.vx, p.vv)
            p.dx += (ux - p.dx) * 0.35
            p.dv += (uv - p.dv) * 0.35
            p.dx, p.dv = unit(p.dx, p.dv)

    def desired_velocity(self, p): # Calculate the player velocity required by the current movement target.
        spd = p.speed * self.speed_mod(p) # Fitness and second-half fatigue (stats_system).
        if p.state == "leaving":
            spd *= 0.5
        elif p.role == "GK":
            spd *= 0.95 if getattr(p, "alert", False) else 0.62
        if self.ball.owner is p:
            spd *= 0.84
        if p.injured:
            spd *= INJURED_SPEED_K
        if p.ctrl and p.kvec:
            return p.kvec[0] * spd * 1.05, p.kvec[1] * spd * 1.05
        if p.tx is None:
            return 0.0, 0.0
        tx, tv = p.tx, p.tv
        if p.state == "leaving":
            tx, tv = self.gate_point(p, V_MAX_P)
        dx, dv = tx - p.wx, tv - p.wv
        d = math.hypot(dx, dv)
        if d < 1.2:
            return 0.0, 0.0
        s = spd * min(1.0, d / 9.0 + 0.15)
        vx, vv = dx / d * s, dv / d * s
        if not p.ctrl:
            for q in self.team_p[p.team]:
                if q is p or q.state == "out":
                    continue
                ex, ev = p.wx - q.wx, p.wv - q.wv
                dd = math.hypot(ex, ev)
                if 0.01 < dd < 12.0:
                    vx += ex / dd * (12.0 - dd) * 2.2
                    vv += ev / dd * (12.0 - dd) * 2.2
        return vx, vv

    def step_player(self, p, dt): # Advance one player simulation step including movement and action contacts.
        if p.state == "out":
            return
        if p.cool > 0:
            p.cool -= dt
        if p.act_cd > 0:
            p.act_cd -= dt
        if p.face_t > 0:
            p.face_t -= dt
        if p.state == "action":
            rs = self.restart if self.mode == "restart" else None
            pin_taker = rs is not None and rs.get("pin_taker") and rs.get("taker") is p
            act = p.act
            if (pin_taker and act is not None and act["key"] in ("kick", "throw")
                    and not act["fired"]):
                pin_pos = rs.get("pin_pos", (p.wx, p.wv))
                p.vx = p.vv = 0.0
                self.step_action(p, dt)
                if p.state == "action" and p.act is not None and not p.act["fired"]:
                    p.wx, p.wv = pin_pos
                    p.vx = p.vv = 0.0
            else:
                self.step_action(p, dt)
            self.post_move(p)
            return
        if p.state == "down":
            p.vx = p.vv = 0.0
            p.sid = action_sids(p.team, "fall", "W" if "W" in p.face else "E")[-1]
            self.post_move(p)
            return
        if p.state == "tunnel":
            p.vx = p.vv = 0.0
            return
        if p.state in ("subout", "subin"):
            self.step_sub(p, dt)
            return
        rs = self.restart if self.mode == "restart" else None
        if rs is not None and rs.get("taker") is p and rs.get("kind") in ("free", "penalty"):
            p.face = "E" if self.att[p.team] > 0 else "W"
            p.dx, p.dv = float(self.att[p.team]), 0.0
        if rs is not None and rs.get("pin_taker") and rs.get("taker") is p:
            p.wx, p.wv = rs.get("pin_pos", (p.wx, p.wv))
            p.vx = p.vv = 0.0
            p.tx = p.tv = p.kvec = p.path = None
            p.sid = stand_sid(p.team, p.face)
            self.post_move(p)
            return
        dvx, dvv = self.desired_velocity(p)
        if p.ctrl and p.kvec is None:
            k = min(1.0, 22.0 * dt)
        else:
            k = min(1.0, 14.0 * dt)
        p.vx += (dvx - p.vx) * k
        p.vv += (dvv - p.vv) * k
        sp = math.hypot(p.vx, p.vv)
        kk = depth_k(p.wv)
        kv = depth_v_k(p.wv, p.wx)
        p.wx += p.vx * dt * kk
        p.wv += p.vv * dt * kv
        self.clamp_player(p)
        self.taker_watchdog(p, rs, dt, sp)
        p.stride += sp * dt
        self.post_move(p)
        if rs is not None and rs.get("taker") is p and rs.get("kind") in ("free", "penalty"):
            p.face = "E" if self.att[p.team] > 0 else "W"
            p.dx, p.dv = float(self.att[p.team]), 0.0
        if p.state == "leaving" and p.tv is not None and abs(p.wv - V_MAX_P) < 2.0:
            p.state = "out"
            return
        if p.state == "cele" and sp < 6:
            # Use the main module's current action configuration. ACTIONS is
            # reassigned by load_data(), so a copied global binding can be stale.
            seq = action_sids(p.team, "cele", "E")
            p.cele_t += dt
            p.sid = seq[int(p.cele_t / 0.11) % len(seq)]
        elif sp > 9:
            p.still = 0.0
            p.settled = False
            cyc = run_cycle(p.team, p.face)
            p.sid = cyc[int(p.stride / 4.6) % len(cyc)]
        else:
            p.still += dt
            if self.mode != "play" and p.still > 0.15:
                p.face = "E" if self.att[p.team] > 0 else "W"
                p.settled = True
            elif p.still > 0.3 and not p.settled:
                p.face = STOP_FLIP.get(p.face, p.face)
                p.settled = True
            p.sid = stand_sid(p.team, p.face)

    def begin_action(self, p, key, side, **kw): # Initialize an animation/action and its timing and parameters.
        if self._preview is not None:
            self._preview.append((p, key, dict(kw)))
            return
        spec = ACT_SPEC[key]
        if key == "punch":
            c = action_sids(p.team, "cele", "E")
            seq = [c[1], c[2], c[1], c[0]]
        elif key == "throw":
            seq = [team_sprite_offset(p.team) + 27, team_sprite_offset(p.team) + 2, team_sprite_offset(p.team) + 2]
        elif kw.get("cele"):
            seq = [team_sprite_offset(p.team) + k for k in CELE_SLIDE[side]]
        elif key == "header_dive":
            seq = action_sids(p.team, "fall", side)
        elif key == "kick" and kw.get("kind", "pass") == "pass" and not kw.get("tackle") and not kw.get("special") \
                and kw.get("power", 1.0) > 0.0:
            cyc = run_cycle(p.team, "E" if side == "E" else "W")
            seq = [cyc[0], cyc[1], cyc[0]]
        else:
            seq = action_sids(p.team, key, side)
        if kw.get("repeat"):
            seq = seq * int(kw["repeat"])
        if p.ctrl:
            p.tx = p.tv = None
        p.state = "action"
        p.vx *= 0.4
        p.vv *= 0.4
        p.face = "E" if side == "E" else "W"
        if "dx" in kw:
            p.dx, p.dv = kw["dx"], kw["dv"]
        hold = kw.get("hold", spec["hold"])
        p.act = dict(key=key, seq=seq, t=0.0, fdur=spec["fdur"], contact=spec["contact"], hold=hold,
                     active=spec.get("active"), fired=False, resolved=False, kw=kw, side=side,
                     dur=len(seq) * spec["fdur"] + hold)
        if key == "fall" and self.ball.owner is p:
            self.ball.owner = None
        if kw.get("special") and getattr(self, "slowmo_on", True) and not kw.get("show") and self.strike_will_hit(p, key, kw):
            c, fd = spec["contact"], spec["fdur"]
            p.act["slow"] = (max(0, c - 1) * fd, (c + 1) * fd)
            self.slowmo_p = p
        if key in ("header", "header_dive") and "dx" in kw and not kw.get("show"):
            imp = 95.0 if key == "header_dive" else 34.0
            p.vx, p.vv = kw["dx"] * imp, kw["dv"] * imp

    def step_action(self, p, dt): # Advance the active player action and resolve frame timing.
        a = p.act
        a["t"] += dt
        n = len(a["seq"])
        fi = int(a["t"] / a["fdur"])
        p.sid = a["seq"][min(fi, n - 1)]
        key, kw = a["key"], a["kw"]
        if not a["fired"] and kw.get("steer"):
            if p.ctrl:
                self.steer_action_aim(p, a, dt) # User may still redirect the ball until contact.
            else:
                self.ai_steer_aim(p, a, dt) # AI keeps tracking its target teammate until contact.
        if not a["fired"] and fi >= a["contact"]:
            a["fired"] = True
            self.action_contact(p, a)
        if a["active"] and not a["resolved"] and a["active"][0] <= fi <= a["active"][1]:
            if key == "slide":
                self.slide_check(p, a)
            elif key == "dive":
                self.dive_check(p, a)
        if key == "slide":
            f = max(0.0, 1.0 - a["t"] / (a["dur"] * 0.85))
            p.vx, p.vv = kw["dx"] * kw["speed"] * f, kw["dv"] * kw["speed"] * f
        elif key == "dive":
            if 1 <= fi <= 3:
                p.vx, p.vv = 0.0, kw["dv"] * kw["speed"]
            else:
                p.vx *= 0.9
                p.vv *= math.exp(-6 * dt)
        elif kw.get("vel") is not None:
            p.vx, p.vv = kw["vel"]
        else:
            f = math.exp(-6.0 * dt)
            p.vx *= f
            p.vv *= f
            if kw.get("assist") and not a["fired"] and key in ("header", "bicycle", "header_dive") and self.ball.owner is None:
                T = max(0.0, a["contact"] * a["fdur"] - a["t"])
                tx, tv = self.ball_pred(T)
                ux, uv = unit(tx - p.wx, tv - p.wv)
                sp = min(85.0 if key == "header_dive" else 65.0, math.hypot(tx - p.wx, tv - p.wv) / max(T, 0.05))
                p.vx += (ux * sp - p.vx) * 0.6
                p.vv += (uv * sp - p.vv) * 0.6
        kk = depth_k(p.wv)
        kv = depth_v_k(p.wv, p.wx)
        p.wx += p.vx * dt * kk
        p.wv += p.vv * dt * kv
        if key == "dive" and p.role == "GK":
            p.wv = clamp(p.wv, V_GC - HALF_MOUTH * 2.2, V_GC + HALF_MOUTH * 2.2)
        self.clamp_player(p)
        if key in ("header", "header_dive") and not kw.get("show"):
            ph = clamp(a["t"] / max(0.01, len(a["seq"]) * a["fdur"]), 0.0, 1.0)
            p.lift = (7.0 if key == "header" else 4.0) * math.sin(math.pi * ph)
        elif key == "dive" and p.role == "GK":
            ph = clamp(a["t"] / (len(a["seq"]) * a["fdur"] + 0.3), 0.0, 1.0)
            p.lift = 6.0 * math.sin(math.pi * ph) ** 0.7
        if a["t"] >= a["dur"]:
            p.state, p.act = "free", None
            p.lift = 0.0

    def action_contact(self, p, a): # Return whether the current action frame is a ball-contact frame.
        key = a["key"]
        if a["kw"].get("show"):
            return
        if key in ("kick", "header", "bicycle", "header_dive"):
            self.try_strike(p, a)
        elif key == "throw":
            self.do_throw(p, a)
        elif key == "punch":
            self.keeper_punch(p)

    def try_strike(self, p, a): # Attempt the ball contact associated with the active player action.
        kw, b, key = a["kw"], self.ball, a["key"]
        if kw.get("tackle"):
            return self.tackle_contact(p, kw)
        setp = self.mode == "restart" and self.restart is not None and self.restart["taker"] is p
        reach, zlo, zhi = STRIKE_REACH[key]
        if kw.get("assist"):
            reach, zlo, zhi = reach + 7.0, (-2.0 if key == "bicycle" else zlo - 3.0), zhi + 8.0
        owned = b.owner is p
        if not owned and not setp:
            d = math.hypot(b.wx - p.wx, b.wv - p.wv)
            if b.owner is not None or d > reach or not (zlo <= b.z <= zhi) or self.mode != "play":
                return False
        dx, dv = kw["dx"], kw["dv"]
        err = kw.get("err", 0.0)
        if kw.get("kind", "pass") == "shot":
            err = math.hypot(err, self.shot_err(p)) # Skill: shooting accuracy, for AI and user alike.
        elif key in ("header", "header_dive", "bicycle"):
            err = math.hypot(err, self.aerial_err(p)) # Skill: precision of headed passes / clearances.
        if err:
            ang = random.gauss(0.0, err)
            dx, dv = dx * math.cos(ang) - dv * math.sin(ang), dx * math.sin(ang) + dv * math.cos(ang)
        power, lift = kw["power"], kw["lift"]
        if kw.get("kind", "pass") in ("shot", "pass"):
            power = min(power, self.power_cap(p)) # Fitness: maximum ball range on long kicks.
        if key in ("header", "header_dive"):
            power, lift = power * 0.8, max(lift, 18.0)
        elif key == "bicycle":
            power, lift = max(power, 235.0), max(lift, 28.0)
        b.owner = None
        b.ds = depth_slow(dx, dv)
        b.vx, b.vv, b.vz = dx * power * b.ds, dv * power * b.ds, lift
        b.z = max(b.z, 0.5)
        b.last, b.last_team = p, p.team
        b.intended = kw.get("target")
        b.age = 0.0
        p.cool = 0.4
        kind = kw.get("kind", "pass")
        if p is self.cp and p.team == self.user_team and kind in ("pass", "shot"):
            self.manual = False
            self.sel_hold_until = 0.0
        b.tactical_pass = bool(kw.get("tactical_pass", False) and kind == "pass" and kw.get("target") is not None)
        b.pass_active = kind == "pass"
        b.shot_team = p.team if kind == "shot" else None
        b.gk_attempted = False
        b.pen = bool(setp and kind == "shot" and self.restart is not None and self.restart["kind"] == "penalty")
        b.pen_team = p.team if b.pen else None
        goal_x = L if self.att[p.team] > 0 else 0.0
        b.shot_dist = math.hypot(goal_x - b.wx, V_GC - b.wv) if kind == "shot" else 0.0
        b.shot_set = self.restart["kind"] if (setp and self.restart is not None) else None
        if b.pen:
            gks = [q for q in self.team_p[1 - p.team] if q.role == "GK"]
            gsk = gks[0].skill if gks else 0.5
            b.pen_save = random.random() < 0.10 + 0.16 * gsk
        if kind == "shot":
            self.stats["shots"][p.team] += 1
            if self.shot_is_on_target(p):
                self.stats["on_target"][p.team] += 1
            self.audio.react("shot")
        if self.mode == "restart":
            if setp and self.restart is not None:
                self.log_restart_taker(p, self.restart["kind"])
            self.mode, self.restart = "play", None
        self.audio.play("head" if key in ("header", "header_dive") else ("kick_hard" if power > 205 else "kick"), 0.5 + min(0.5, power / 400.0))
        return True

    def keeper_reading(self): # 0..1: how well the keeper reads the current shot. Long shots and free kicks are read early; penalties stay a guess.
        b = self.ball
        if b.shot_team is None or b.pen:
            return 0.0
        r = clamp((b.shot_dist - KEEPER_FAR_START) / (KEEPER_FAR_FULL - KEEPER_FAR_START), 0.0, 1.0)
        if b.shot_set == "free":
            r = max(r, KEEPER_FREEKICK_READ)
        return r

    def keeper_save_chance(self, gk, speed, reach_d): # Single source of truth for save odds (standing saves and dives).
        p = KEEPER_SAVE_BASE - max(0.0, speed - 140.0) * KEEPER_SPEED_K + (gk.skill - 0.75) * KEEPER_SKILL_K
        p -= reach_d * KEEPER_REACH_K # The farther the keeper must stretch, the harder the save.
        if self.ball.shot_team is not None: # Corners are harder to reach than shots down the middle.
            p -= KEEPER_CORNER_K * min(1.0, abs(self.ball.wv - V_GC) / HALF_MOUTH)
        p += KEEPER_READ_BONUS * self.keeper_reading() # Foresight: far shots and free kicks are easier to read.
        return clamp(p, KEEPER_SAVE_MIN, KEEPER_SAVE_MAX)

    def try_block(self, p, sp): # A defender standing in the line of a hard shot may deflect it instead of letting it pass untouched.
        if random.random() > BLOCK_CHANCE:
            return False
        b = self.ball
        ang = random.choice((-1.0, 1.0)) * random.uniform(0.5, 1.3)
        keep = random.uniform(0.35, 0.55)
        c, s = math.cos(ang), math.sin(ang)
        b.vx, b.vv = (b.vx * c - b.vv * s) * keep, (b.vx * s + b.vv * c) * keep
        b.vz, b.ds = max(b.vz, 0.0) + random.uniform(10.0, 40.0), 1.0
        b.last, b.last_team, b.intended, b.age = p, p.team, None, 0.0
        b.shot_team, b.pass_active = None, False
        p.cool = 0.35
        self.stats["blocks"][p.team] += 1
        self.audio.play("tackle", 0.6)
        return True

    def register_save(self, gk): # Count a goalkeeper save when the ball in play is a shot.
        if self.ball.shot_team is not None:
            self.stats["saves"][gk.team] += 1

    def shot_is_on_target(self, shooter): # Forecast whether the ball just struck will cross the goal line inside the posts and under the bar.
        goal_x = L if self.att[shooter.team] > 0 else 0.0
        fc = self.ball_forecast(goal_x)
        return fc is not None and abs(fc["v"] - V_GC) < HALF_MOUTH and fc["z"] < GOAL_H

    def do_throw(self, p, a): # Release the ball using the active throw action.
        kw, b = a["kw"], self.ball
        if not (self.mode == "restart" and self.restart and self.restart["taker"] is p):
            return
        b.wx, b.wv = self.restart["pos"]
        b.z = THROW_RELEASE_Z
        b.ds = depth_slow(kw["dx"], kw["dv"])
        b.vx, b.vv, b.vz = kw["dx"] * kw["power"] * b.ds, kw["dv"] * kw["power"] * b.ds, kw.get("lift", 40.0)
        b.last, b.last_team, b.intended, b.age, b.owner = p, p.team, kw.get("target"), 0.0, None
        b.tactical_pass = False
        b.pass_active = False
        p.cool = 0.5
        self.log_restart_taker(p, self.restart["kind"])
        self.mode, self.restart = "play", None
        self.audio.play("head", 0.5)

    def tackle_contact(self, p, kw): # Check and resolve a tackle contact between two players.
        b = self.ball
        o = b.owner
        if o is not None and o.team != p.team:
            if math.hypot(o.wx - p.wx, o.wv - p.wv) < 9.0 and (unit(o.wx - p.wx, o.wv - p.wv)[0] * p.dx + unit(o.wx - p.wx, o.wv - p.wv)[1] * p.dv) > -0.3:
                self.resolve_challenge(p, o, "stand")
        elif o is None and self.mode == "play":
            if math.hypot(b.wx - p.wx, b.wv - p.wv) < 8.5 and b.z < 6.0:
                self.poke_ball(p, 100.0)

    def deflect_dir(self, p, spread=0.0): # Direction a tackle knocks the ball: the user's aim if one was recorded, else the player's facing.
        a = p.act
        aim = a["kw"].get("aim") if a else None
        dx, dv = aim if aim else (p.dx, p.dv)
        if spread:
            ang = random.uniform(-spread, spread)
            dx, dv = dx * math.cos(ang) - dv * math.sin(ang), dx * math.sin(ang) + dv * math.cos(ang)
        return dx, dv

    def poke_ball(self, p, power): # Attempt a short poke to move the ball away from a nearby opponent.
        b = self.ball
        b.ds = 1.0
        dx, dv = self.deflect_dir(p, spread=0.2)
        b.vx, b.vv, b.vz = dx * power, dv * power, random.uniform(0, 20)
        b.last, b.last_team, b.intended, b.age = p, p.team, None, 0.0
        b.pass_active = False
        self.audio.play("tackle", 0.7)

    def slide_check(self, p, a): # Check whether a sliding action can reach and contact the ball or opponent.
        b = self.ball
        o = b.owner
        if o is not None and o.team != p.team:
            dist_o = math.hypot(o.wx - p.wx, o.wv - p.wv)
            if dist_o < 12.0 and not o.fallen():
                if o.role == "GK":
                    ux, uv = unit(o.wx - p.wx, o.wv - p.wv)
                    if dist_o < 9.5 and a["kw"]["dx"] * ux + a["kw"]["dv"] * uv > 0.6:
                        a["resolved"] = True
                        self.resolve_challenge(p, o, "slide")
                    return
                a["resolved"] = True
                self.resolve_challenge(p, o, "slide")
            return
        if o is None and self.mode == "play" and math.hypot(b.wx - p.wx, b.wv - p.wv) < 10.0 and b.z < 6.0:
            a["resolved"] = True
            self.poke_ball(p, 130.0)
            return
        if self.mode == "play" and a["t"] > a["fdur"] * 2:
            for q in self.players:
                if q.team != p.team and q.state in ("free",) and math.hypot(q.wx - p.wx, q.wv - p.wv) < 8.0 and q is not o:
                    a["resolved"] = True
                    if random.random() < 0.22 * (0.5 + p.aggr):
                        self.call_foul(p, q, 0.30, 0.02)
                    return

    def resolve_challenge(self, t, o, kind): # Resolve the outcome of a player-versus-player challenge.
        b = self.ball
        if o.role == "GK" and b.owner is o and t.team != o.team:
            if kind != "slide":
                return
            ref_near = math.hypot(self.ref.wx - t.wx, self.ref.wv - t.wv) < 24.0
            if ref_near:
                self.call_foul(t, o, 0.50, 0.50)
            else:
                self.call_foul(t, o, 0.60, 0.0)
            self.log_event(tr("ev.gk_danger"), secs=3, team=t.team)
            return
        ux, uv = unit(o.wx - t.wx, o.wv - t.wv)
        away = o.dx * ux + o.dv * uv
        moving = math.hypot(o.vx, o.vv) > 10
        behind = moving and away > 0.4 and (t.dx * ux + t.dv * uv) > 0.3
        win = (0.52 if kind == "stand" else 0.46) + 0.28 * (t.skill - o.skill) - (0.14 if behind else 0.0)
        foul = (0.07 if kind == "stand" else 0.18) + (0.14 if behind else 0.0) + 0.04 * t.aggr
        r = random.random()
        b = self.ball
        if r < win:
            b.owner = None
            sp = random.uniform(55, 110)
            dx, dv = self.deflect_dir(t, spread=0.3)
            b.vx, b.vv, b.vz = dx * sp, dv * sp, random.uniform(0, 25)
            b.last, b.last_team, b.intended, b.age = t, t.team, None, 0.0
            o.cool = 0.55
            if random.random() < 0.5:
                self.give_ball(t)
            self.audio.play("tackle", 0.8)
            self.audio.react("tackle")
            self.maybe_injury_from_tackle(o, kind)
        elif r < win + foul:
            yp = 0.07 + (0.22 if kind == "slide" else 0.0) + (0.14 if behind else 0.0)
            rp = 0.003 + (0.035 if (kind == "slide" and behind) else 0.0)
            self.call_foul(t, o, yp, rp)

    def dive_check(self, p, a): # Check whether a goalkeeper dive reaches the incoming ball.
        b = self.ball
        if b.pen and not b.pen_save:
            return
        if b.owner is None and b.last_team != p.team and self.mode == "play":
            d = math.hypot(b.wx - p.wx, b.wv - p.wv)
            if d < 10.5 and b.z < GOAL_H + 5:
                a["resolved"] = True
                sp = math.hypot(b.vx, b.vv)
                is_shot = b.shot_team is not None
                if is_shot:
                    if b.gk_attempted:
                        return
                    b.gk_attempted = True
                save_chance = self.keeper_save_chance(p, sp, d)
                if random.random() > save_chance:
                    return
                self.register_save(p)
                if sp < 180 and random.random() < 0.35 + 0.35 * p.skill:
                    self.give_ball(p)
                    self.log_event(tr("ev.save", p=p.label()), secs=2, team=p.team)
                    self.audio.play("head", 0.7)
                    self.audio.react("save")
                else:
                    self.gk_parry(p, punch=random.random() < 0.35)

    def side_of(self, p, dx, dv): # Determine which side of a player the target lies on.
        return "E" if screen_x_of(p.wx, p.wv, dx, dv) >= 0 else "W"

    def start_kick(self, p, dx, dv, power, lift, kind="pass", target=None, err=0.0, tactical_pass=False, special=False, steer=False): # Start a ground kick, pass, or shot.
        if p.busy():
            return False
        self.begin_action(p, "kick", self.side_of(p, dx, dv), dx=dx, dv=dv, power=power, lift=lift, kind=kind, target=target, err=err,
                          tactical_pass=bool(tactical_pass and kind == "pass" and target is not None), special=special, steer=steer)
        return True

    def start_aerial(self, p, key, dx, dv, power, lift, kind="pass", err=0.0, target=None, assist=False, steer=False): # Start a header, volley, or other aerial action.
        if p.busy():
            return False
        if key in ("bicycle", "header_dive"):
            self.log_move(key, p)
        self.begin_action(p, key, self.side_of(p, dx, dv), dx=dx, dv=dv, power=power, lift=lift, kind=kind, err=err, target=target,
                          assist=assist, special=(key in SLOWMO_KEYS), steer=steer)
        p.act_cd = 0.8
        return True

    def start_tackle(self, p, dx, dv, kind, aim=None): # Start a standing/sliding tackle; aim (if given) is where the ball should be knocked.
        if p.busy():
            return False
        if kind == "slide":
            self.begin_action(p, "slide", self.side_of(p, dx, dv), dx=dx, dv=dv, speed=88.0, aim=aim)
        else:
            self.begin_action(p, "kick", self.side_of(p, dx, dv), dx=dx, dv=dv, power=0.0, lift=0.0, tackle=True, aim=aim)
        p.act_cd = 0.9
        return True

    def start_dive(self, p, vtarget): # Start a goalkeeper dive toward the specified target.
        if p.busy():
            return False
        b = self.ball
        self.log_move("dive", p)


        dist = clamp(abs(vtarget - p.wv), 2.0, HALF_MOUTH * 2.2)

        self.begin_action(p, "dive", "E" if b.wx > p.wx else "W", dv=1.0 if vtarget > p.wv else -1.0, speed=dist / 0.50)
        return True

    def start_throw(self, p, dx, dv, power, lift, target=None): # Start a player throw action with its target and launch parameters.
        if p.busy():
            return False
        self.begin_action(p, "throw", self.side_of(p, dx, dv), dx=dx, dv=dv, power=power, lift=lift, target=target)
        return True

    def lob_lift(self, dist, power, z_t=0.0): # Calculate the vertical lift needed for a lob over the supplied distance.
        T = max(0.15, dist / max(40.0, power * 0.82))
        return clamp((z_t + 0.5 * G * T * T) / T, 0.0, 140.0)
