"""Agonism (aggressiveness) level of each team, 0..100 %, adjustable live with a vertical bar next to the scoreboard.

    0 %   -> conservative: deep lines, fast recoveries, fewer sliding tackles, only standard challenges, few fouls and injuries.
    50 %  -> the game's original behaviour (every multiplier below is exactly 1.0).
    100 % -> maximum aggression: high lines, more pressing, many tackles and slides, more fouls and injuries.

All multipliers are piece-wise linear through (0 %, lo), (50 %, 1.0), (100 %, hi), so the effect is proportional.
"""

import math

import pygame

from game_utils import clamp
from graphics_system import BOARD_H, BOARD_W


AGON_DEFAULT = 0.5 # Starting level of both teams (a new match resets it).
AGON_AI_SWING = 0.15 # AI team: level change per goal of difference (trailing = up, leading = down), scaled by urgency.
AGON_AI_RATE = 0.04 # AI team: how fast (level/s) it moves toward its target, so the change is gradual.
AGON_STEP = 0.05 # Keyboard / mouse-wheel step.
AGON_INJURY_RANGE = (0.35, 1.70) # Injury probability multiplier at 0 % / 100 % (average of both teams' levels: giving and taking).
AGON_RECOVERY_BONUS = 0.10 # Extra running speed of a team without the ball at 0 % (fast recoveries); fades out at 50 %.
AGON_CHASE_BONUS = 0.06 # Extra running speed of the player pressing the ball carrier at 100 % (and the same malus at 0 %).
AGON_LINE_PUSH = {"GK": 0.0, "DEF": 0.10, "MID": 0.22, "FWD": 0.16} # Normalized longitudinal shift of the home positions between 0 % and 100 %.

BAND_COLORS = ( # (highest percentage of the band, fill colour)
    (20, (52, 190, 84)), # 0-20 green
    (40, (238, 214, 52)), # 21-40 yellow
    (60, (246, 148, 34)), # 41-60 orange
    (80, (222, 42, 42)), # 61-80 red
    (100, (122, 18, 52)), # 81-100 bordeaux
)


def _mul(g, lo, hi): # 1.0 at g = 0.5, lo at 0, hi at 1.
    return lo + (1.0 - lo) * g / 0.5 if g < 0.5 else 1.0 + (hi - 1.0) * (g - 0.5) / 0.5


def agon_color(level): # Band colour for a 0..1 level.
    pct = int(round(clamp(level, 0.0, 1.0) * 100.0))
    for top, col in BAND_COLORS:
        if pct <= top:
            return col
    return BAND_COLORS[-1][1]


class AgonismMixin: # Per-team agonism level: state, behaviour multipliers, slider bar (draw + input).

    # ---- state ----
    def agon(self, team): # Level of a team, 0..1.
        try:
            return self.agon_lv[team]
        except (AttributeError, IndexError, TypeError):
            return AGON_DEFAULT

    def set_agon(self, team, value):
        self.agon_lv[team] = clamp(float(value), 0.0, 1.0)

    def agon_mul(self, team, lo, hi): # Behaviour multiplier of a team's level (1.0 at 50 %).
        return _mul(self.agon(team), lo, hi)

    # ---- effects on the simulation ----
    def agon_injury_k(self, p): # Both the team that hurts and the team that is hurt raise the risk.
        g = 0.5 * (self.agon(p.team) + self.agon(1 - p.team))
        return _mul(g, AGON_INJURY_RANGE[0], AGON_INJURY_RANGE[1])

    def agon_speed_k(self, p): # Running speed of an AI player: fast recoveries when conservative, sprint of the presser when aggressive.
        if p.role == "GK":
            return 1.0
        own = self.ball.owner
        if own is not None and own.team == p.team:
            return 1.0
        g = self.agon(p.team)
        if p.tag == "chase":
            return 1.0 + AGON_CHASE_BONUS * (2.0 * g - 1.0)
        if g < 0.5:
            return 1.0 + AGON_RECOVERY_BONUS * (1.0 - 2.0 * g)
        return 1.0

    # ---- bars ----
    def agon_bars(self): # [(team, side)] of the visible bars: only the user's team, or both (independent) for a spectator. side 0 = left, 1 = right.
        if self.mode in ("intro", "full") or self.replay:
            return []
        teams = (0, 1) if self.user_team is None else (self.user_team,)
        return [(t, t) for t in teams] # Each team keeps the side it had in the first half (team 0 left, team 1 right), also after the change of ends.

    def agon_ai_target(self, team): # Level an AI-run team wants: None = leave as is (first half), else from the score and the time left.
        if self.half < 2:
            return None
        diff = self.score[1 - team] - self.score[team] # > 0: trailing.
        prog = clamp(self.real_t / max(1.0, self.half_secs), 0.0, 1.0)
        urgency = 0.7 + 0.6 * prog # The closer to the end, the stronger the reaction.
        if diff == 0:
            return clamp(0.5 + 0.10 * prog, 0.0, 1.0) # Level game: push a little more as time runs out.
        return clamp(0.5 + AGON_AI_SWING * clamp(diff, -3, 3) * urgency, 0.10, 0.90)

    def update_agonism(self, dt): # The team the user does not control decides its own level, gradually.
        if self.user_team is None or self.mode in ("intro", "half", "full"):
            return
        team = 1 - self.user_team
        tgt = self.agon_ai_target(team)
        if tgt is None:
            return
        cur = self.agon(team)
        step = AGON_AI_RATE * dt
        self.set_agon(team, cur + clamp(tgt - cur, -step, step))

    def agon_rect(self, side): # Bar rectangle in screen coordinates: as tall as the scoreboard, right outside its left / right edge.
        bw = int(clamp(self.W / 42.0, 10, 20))
        ps = max(1, min(int(self.W // BOARD_W), int(self.bh // BOARD_H))) # Same scale and centring as Scoreboard.draw.
        draw_w, draw_h = BOARD_W * ps, BOARD_H * ps
        off_x, off_y = int((self.W - draw_w) // 2), int((self.bh - draw_h) // 2)
        y0, y1 = off_y + 3, max(off_y + 30, off_y + draw_h - 3)
        if off_x >= bw + 6: # Room beside the scoreboard.
            x = off_x - bw - 3 if side == 0 else off_x + draw_w + 3
        else: # Board fills the width: use the window edge.
            x = 3 if side == 0 else int(self.W) - 3 - bw
        return pygame.Rect(x, y0, bw, y1 - y0)

    def _agon_from_y(self, y): # Mouse y -> level on the dragged bar.
        team, side = self.agon_drag
        r = self.agon_rect(side)
        inner_top, inner_h = r.top + 2, r.height - 4
        self.set_agon(team, 1.0 - (y - inner_top) / float(max(1, inner_h)))

    def agon_mouse_down(self, pos, button): # True when the click was on a bar.
        if button != 1:
            return False
        for team, side in self.agon_bars():
            if self.agon_rect(side).inflate(10, 0).collidepoint(pos):
                self.agon_drag = (team, side)
                self._agon_from_y(pos[1])
                return True
        return False

    def agon_mouse_move(self, pos):
        if self.agon_drag is None:
            return False
        self._agon_from_y(pos[1])
        return True

    def agon_mouse_up(self):
        if self.agon_drag is None:
            return False
        self.agon_drag = None
        return True

    def agon_wheel(self, dy): # Wheel over a bar nudges it.
        if self.mouse_xy is None or not dy:
            return False
        for team, side in self.agon_bars():
            if self.agon_rect(side).inflate(10, 0).collidepoint(self.mouse_xy):
                self.set_agon(team, round((self.agon(team) + AGON_STEP * (1 if dy > 0 else -1)) / AGON_STEP) * AGON_STEP)
                return True
        return False

    def agon_key(self, direction, second=False): # Keyboard / pad: the user's bar; when spectating the left bar, or the right one with second=True.
        bars = self.agon_bars()
        if not bars:
            return False
        team, _side = bars[1 if (second and len(bars) > 1) else 0]
        self.set_agon(team, round((self.agon(team) + AGON_STEP * direction) / AGON_STEP) * AGON_STEP)
        return True

    # ---- drawing ----
    def draw_agonism(self, surf):
        for team, side in self.agon_bars():
            self._draw_agon_bar(surf, self.agon_rect(side), self.agon(team))

    @staticmethod
    def _rrect(surf, col, rect, radius, width=0):
        try:
            pygame.draw.rect(surf, col, rect, width, border_radius=radius)
        except TypeError: # pygame 1.x
            pygame.draw.rect(surf, col, rect, width)

    def _draw_agon_bar(self, surf, r, level): # Rounded, shaded "tube" that grows and changes colour with the level.
        rad = r.w // 2
        track = pygame.Surface(r.size, pygame.SRCALPHA)
        self._rrect(track, (12, 14, 24, 215), track.get_rect(), rad)
        iw, ih = r.w - 4, r.h - 4
        for pct in (20, 40, 60, 80): # Band limits, faint.
            y = 2 + int(round(ih * (1.0 - pct / 100.0)))
            pygame.draw.line(track, (255, 255, 255, 38), (3, y), (r.w - 4, y))
        surf.blit(track, r.topleft)
        fh = int(round(ih * clamp(level, 0.0, 1.0)))
        if fh > 0:
            fh = max(fh, iw)
            base = agon_color(level)
            fill = pygame.Surface((iw, fh), pygame.SRCALPHA)
            for x in range(iw): # Cylinder shading, light from the upper left.
                t = (x + 0.5) / iw
                k = 0.42 + 0.80 * math.sin(math.pi * (0.08 + 0.80 * t))
                col = tuple(min(255, int(c * k)) for c in base)
                pygame.draw.line(fill, col + (255,), (x, 0), (x, fh))
            gloss = pygame.Surface((max(2, iw // 4), fh), pygame.SRCALPHA)
            gloss.fill((255, 255, 255, 70))
            fill.blit(gloss, (max(1, int(iw * 0.22)), 0))
            cap = pygame.Surface((iw, max(3, iw // 2)), pygame.SRCALPHA) # Lighter dome at the top of the fill.
            pygame.draw.ellipse(cap, (255, 255, 255, 60), cap.get_rect())
            fill.blit(cap, (0, 0))
            mask = pygame.Surface((iw, fh), pygame.SRCALPHA)
            self._rrect(mask, (255, 255, 255, 255), mask.get_rect(), iw // 2)
            fill.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(fill, (r.x + 2, r.y + 2 + ih - fh))
        self._rrect(surf, (176, 182, 206), r, rad, 1)
