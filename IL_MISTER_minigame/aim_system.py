"""Aim resolution: where the user is pointing (mouse gesture, stick, keys or mouse cursor) for passes, shots and tackles."""

import math
import time

import pygame

from game_utils import unit
from geometry import screen_to_world_dir

CURSOR_AIM_SECS = 1.5 # The mouse cursor counts as an aim source only if it moved within this many seconds.
CURSOR_AIM_MIN_DIST = 3.0 # World units; a cursor closer than this to the player gives no usable direction.
AIM_STEER_RATE = 14.0 # Responsiveness (1/s) of live aim steering while a spectacular action is winding up.
AI_STEER_RATE = 8.0 # Same for AI players: they track the moving target (teammate) a bit more slowly than a user.
AI_STEER_LEAD = 0.35 # Seconds of target movement the AI leads a header/volley pass by.


class AimMixin: # Aim sources shared by user actions: drag gesture, stick, keys, mouse cursor.

    def aim_input(self, p): # Explicit aim from the user, or None when nothing is being pointed at (no facing fallback).
        if self.drag:
            x0, y0, x1, y1 = self.drag
            plan = self.gesture_plan(x0, y0, x1, y1)
            if plan is not None:
                return plan[1]

        def scr(u): # Convert a screen-space direction to a world direction at the player's position.
            return screen_to_world_dir(p.wx, p.wv, u[0], u[1])
        a = self.joy.aim_vec()
        if a:
            return scr(a)
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        v = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        if x or v:
            return scr(unit(float(x), float(v)))
        m = self.joy.move_vec()
        if m:
            return scr(m)
        return self.cursor_aim(p)

    def aim_dir(self, p): # Calculate the aiming direction for a player action (explicit aim, then movement, then facing).
        return self.aim_input(p) or p.kvec or (p.dx, p.dv)

    def cursor_aim(self, p): # Direction from the player toward the mouse cursor, if the mouse was used recently.
        if self.mouse_xy is None or self.paused or time.time() - self.mouse_moved_at > CURSOR_AIM_SECS:
            return None
        mx, my = self.mouse_xy[0], self.mouse_xy[1] - self.field_y
        if not (0 <= mx < self.view_w and 0 <= my < self.view_h):
            return None
        _fx, _row, (wx, wv) = self.screen_to_ground(mx, my)
        if math.hypot(wx - p.wx, wv - p.wv) < CURSOR_AIM_MIN_DIST:
            return None
        return unit(wx - p.wx, wv - p.wv)

    def blend_action_aim(self, a, live, rate, dt): # Ease the pending action direction toward `live`.
        kw = a["kw"]
        r = 1.0 - math.exp(-rate * dt)
        cur = (kw["dx"], kw["dv"])
        kw["dx"], kw["dv"] = unit(cur[0] + (live[0] - cur[0]) * r, cur[1] + (live[1] - cur[1]) * r, cur)

    def steer_action_aim(self, p, a, dt): # Let the user keep steering a spectacular action until its contact frame.
        live = self.aim_input(p)
        if live is not None:
            self.blend_action_aim(a, live, AIM_STEER_RATE, dt)

    def ai_steer_aim(self, p, a, dt): # AI counterpart: keep the ball pointed at the (moving) target teammate until contact.
        q = a["kw"].get("target")
        if q is None or q.state in ("out", "leaving"):
            return
        cur = (a["kw"]["dx"], a["kw"]["dv"])
        live = unit(q.wx + q.vx * AI_STEER_LEAD - p.wx, q.wv + q.vv * AI_STEER_LEAD - p.wv, cur)
        self.blend_action_aim(a, live, AI_STEER_RATE, dt)
