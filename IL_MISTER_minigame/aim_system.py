"""Aim resolution: where the user is pointing (mouse gesture, stick, keys or mouse cursor) for passes, shots and tackles."""

import math
import time

import pygame

from game_utils import unit
from geometry import screen_to_world_dir

CURSOR_AIM_SECS = 1.5 # The mouse cursor counts as an aim source only if it moved within this many seconds.
CURSOR_AIM_MIN_DIST = 3.0 # World units; a cursor closer than this to the player gives no usable direction.
AIM_STEER_RATE = 14.0 # Responsiveness (1/s) of live aim steering while a spectacular action is winding up.


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

    def steer_action_aim(self, p, a, dt): # Let the user keep steering a spectacular action until its contact frame.
        live = self.aim_input(p)
        if live is None:
            return
        kw = a["kw"]
        r = 1.0 - math.exp(-AIM_STEER_RATE * dt)
        cur = (kw["dx"], kw["dv"])
        kw["dx"], kw["dv"] = unit(cur[0] + (live[0] - cur[0]) * r, cur[1] + (live[1] - cur[1]) * r, cur)
