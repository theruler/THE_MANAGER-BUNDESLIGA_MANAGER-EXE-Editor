"""Simulation entities: referee flag, players, ball and referee."""

import math
import random

from ball_model import G
from game_utils import clamp, unit
from geometry import ground_to_img, L, V_BOT, V_SPOT, V_TOP
from lang import tr
from match_config import FLAG_FLY_SPEED, FLAG_H
from physics_system import PLAYER_SPEED


class Flag: # Animated referee flag state and screen position.

    def __init__(self, x, v, sg): # Initialize the referee flag position and animation state.
        self.hx, self.hv, self.sg = x, v, sg
        self.x, self.v, self.z = x, v, 0.0
        self.state, self.t = "planted", random.random() * 6.0
        self.tilt = self.w = 0.0
        self.dx, self.dv = 1.0, 0.0
        self.vx = self.vv = self.vz = 0.0
        self.ang = -math.pi / 2
        self.spin = 0.0
        self.timer = 0.0
        self.src = (x, v, 0.0)

    def hit(self, ix, iv, power): # Check whether the supplied point intersects the flag hit area.
        if self.state != "planted":
            return False
        self.dx, self.dv = unit(ix, iv, (1.0, 0.0))
        if power > FLAG_FLY_SPEED:
            self.state = "flying"
            self.vx, self.vv, self.vz = ix * 0.5, iv * 0.5, 36.0 + power * 0.12
            self.z = 2.0
            self.spin = random.choice((-1.0, 1.0)) * random.uniform(8.0, 16.0)
            self.ang = -math.pi / 2
        else:
            self.state = "falling"
            self.tilt, self.w = 0.05, 1.4 + power * 0.025
        return True

    def update(self, dt): # Advance the flag flight or waving animation.
        self.t += dt
        ev = None
        if self.state == "falling":
            self.w += 24.0 * math.sin(max(self.tilt, 0.15)) * dt
            self.tilt += self.w * dt
            if self.tilt >= math.pi / 2:
                self.tilt = math.pi / 2
                ev = "thud"
                if self.w > 2.8:
                    self.w = -self.w * 0.28
                else:
                    self.state, self.timer, self.w = "lying", random.uniform(3.0, 5.0), 0.0
        elif self.state == "flying":
            self.x = clamp(self.x + self.vx * dt, -14.0, L + 14.0)
            self.v = clamp(self.v + self.vv * dt, V_TOP - 10.0, V_BOT + 8.0)
            self.z += self.vz * dt
            self.vz -= G * 0.9 * dt
            self.ang += self.spin * dt
            if self.z <= 0.0:
                self.z = 0.0
                ev = "thud"
                if abs(self.vz) > 22.0:
                    self.vz = -self.vz * 0.38
                    self.vx *= 0.6
                    self.vv *= 0.6
                    self.spin *= 0.6
                else:
                    self.dx, self.dv = unit(math.cos(self.ang), math.sin(self.ang) * 0.6, (1.0, 0.0))
                    self.state, self.tilt, self.timer = "lying", math.pi / 2, random.uniform(3.0, 5.0)
        elif self.state == "lying":
            self.timer -= dt
            if self.timer <= 0.0:
                self.state, self.t2, self.src = "replant", 0.0, (self.x, self.v, self.tilt)
        elif self.state == "replant":
            self.t2 += dt
            u = min(1.0, self.t2 / 0.8)
            e = u * u * (3.0 - 2.0 * u)
            self.x = self.src[0] + (self.hx - self.src[0]) * e
            self.v = self.src[1] + (self.hv - self.src[1]) * e
            self.tilt = self.src[2] * (1.0 - e)
            self.z = 5.0 * math.sin(math.pi * u)
            if u >= 1.0:
                self.state, self.tilt, self.z = "planted", 0.0, 0.0
                self.x, self.v = self.hx, self.hv
                ev = "plant"
        return ev

    def screen(self): # Return the flag position in screen coordinates.
        if self.state == "flying":
            cx, cy = ground_to_img(self.x, self.v)
            cy -= self.z + FLAG_H / 2
            ux, uy = math.cos(self.ang) * FLAG_H / 2, math.sin(self.ang) * FLAG_H / 2
            return (cx - ux, cy - uy, cx + ux, cy + uy, self.sg)
        bx, by0 = ground_to_img(self.x, self.v)
        by = by0 - self.z
        ex, ey = ground_to_img(self.x + self.dx, self.v + self.dv)
        eux, euy = unit(ex - bx, ey - by0, (1.0, 0.0))
        sway = math.sin(self.t * 2.4) * 0.35 / FLAG_H if self.state == "planted" else 0.0
        st, ct = math.sin(self.tilt), math.cos(self.tilt)
        ux, uy = unit(st * eux + sway, st * euy - ct, (0.0, -1.0))
        return (bx, by, bx + ux * FLAG_H, by + uy * FLAG_H, self.sg)


class Player: # Player identity, movement, tactical slot, and action state.
    def __init__(self, team, idx, name=""): # Initialize a player identity, role, position, and runtime state.
        self.team, self.idx, self.num = team, idx, idx + 1
        self.name = name or tr("player.default", n=idx + 1)
        self.role, self.base_u, self.base_w = "MID", 0.3, 0.5
        self.zu, self.zw = (0.0, 1.0), (0.0, 1.0)
        self.roam = False
        self.mark = None
        self.wx = self.wv = 0.0
        self.vx = self.vv = 0.0
        self.dx, self.dv = (1.0, 0.0) if team == 0 else (-1.0, 0.0)
        self.face = "E" if team == 0 else "W"
        self.face_t = 0.0
        self.state = "free"
        self.act = None
        self.tx = self.tv = None
        self.kvec = None
        self.speed = PLAYER_SPEED * random.uniform(0.94, 1.07)
        self.skill = random.uniform(0.66, 0.95)
        self.aggr = random.uniform(0.2, 0.95)
        self.stride = 0.0
        self.cool = 0.0
        self.dec = random.random() * 0.4
        self.hold_t = 0.0
        self.yellow = 0
        self.red = False
        self.ctrl = False
        self.tag = None
        self.timer = 0.0
        self.sid = 0
        self.sx = self.sy = 0.0
        self.cele_t = 0.0
        self.act_cd = 0.0
        self.drift = (0.0, 0.0)
        self.drift_t = random.uniform(3.0, 9.0)
        self.swap_cd = random.uniform(2.0, 6.0)
        self.lift = 0.0
        self.path = None
        self.sq = idx
        self.limp = False
        self.injured = False
        self.walk = None
        self.wk_to = None
        self.gate = 0.0
        self.still = 0.0
        self.settled = True
        self.lx = self.lv = None

    def new_drift(self, scale=1.0): # Choose a new idle or tactical drift target.
        if self.role == "GK":
            self.drift = (0.0, 0.0)
            return
        du, dw = {"DEF": (0.055, 0.10), "MID": (0.09, 0.14), "FWD": (0.09, 0.14)}[self.role]
        self.drift = (random.uniform(-du, du) * scale, random.uniform(-dw, dw) * scale)
        self.drift_t = random.uniform(5.0, 11.0)

    def apply_slot(self, slot): # Apply the supplied formation slot and role to this player.
        self.role, self.base_u, self.base_w = slot["role"], slot["u"], slot["w"]
        self.zu, self.zw = slot["zu"], slot["zw"]

    def label(self): # Build the player label used by the interface.
        return "%s (%d)" % (self.name, self.num)

    def busy(self): # Report whether the player is occupied by an action or transition.
        return self.state == "action"

    def fallen(self): # Report whether the player is currently in a fall state.
        return self.state == "action" and self.act is not None and self.act["key"] == "fall"


class Ball: # Ball position, velocity, ownership, and action state.
    def __init__(self): # Initialize ball position, velocity, possession, and trajectory metadata.
        self.wx, self.wv, self.z = L / 2.0, V_SPOT, 0.0
        self.vx = self.vv = self.vz = 0.0
        self.ds = 1.0
        self.owner = None
        self.last = None
        self.last_team = 0
        self.intended = None
        self.tactical_pass = False
        self.pass_active = False
        self.spin = 0.0
        self.age = 0.0
        self.shot_team = None
        self.gk_attempted = False
        self.pen = False
        self.pen_save = False
        self.pen_team = None
        self.shot_dist = 0.0 # Distance from the goal at the moment of the last shot.
        self.shot_set = None # Restart kind of the last shot ("free", "penalty"...), None for open play.
        self.gy = 0.0
        self.px = 0.0
        self.own_t = 0.0
        self.out_t = 0.0


class Ref: # Referee position and animation state.
    def __init__(self): # Initialize referee position, direction, and animation state.
        self.wx, self.wv = L / 2.0 - 30, V_SPOT + 20
        self.vx = self.vv = 0.0
        self.face = "E"
        self.face_t = 0.0
        self.stride = 0.0
        self.card = None
        self.card_t = 0.0
        self.sid = 121
        self.sx = self.sy = 0.0
