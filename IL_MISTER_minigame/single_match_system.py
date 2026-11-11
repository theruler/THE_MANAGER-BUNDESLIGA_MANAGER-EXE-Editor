"""SINGLE MATCH ("Partita veloce") screen: team / formation / numbered roster selection.

Per team:          [5-row alphabetical team list]   |  full roster, 20 rows: [shirt #] NAME  FIT SKL FRM
                   [logo + name + average values]   |  left click = give the next shirt number, right click = remove it
                   [formation buttons]              |
Shirt numbers 1..11 are the starting slots in formation order (1 = goalkeeper, then defenders, midfielders, forwards).
A match cannot start with fewer than 11 numbered players: the screen warns and START stays disabled.

Everything is drawn on the virtual surface self.su_surf (SU_W x SU_H); self.su_hits holds (rect, tag) pairs in virtual
coordinates. The dispatcher in intro_system.py calls single_click() / single_key() / draw_single_match().
"""

import math

import pygame

from game_utils import clamp
from formation_system import formation_slots, FORMATIONS
from i18n import ROLE_TAG, tr
from graphics_system import SU_H, SU_W
from match_config import ROLE_ORDER, ROLE_POOLS, TEAM_COL, TEAM_NAMES
from stats_system import ROLE_COL, stat_color

SINGLE_BG = (0, 0, 70) # Background of the single-match screen.
ROSTER = 20 # Players per team.
ROW_H = 23 # Height of a roster row.
TOP = 102 # Top of the team columns.
ROSTER_BOTTOM = TOP + 16 + ROSTER * ROW_H - 2 # Bottom edge of the roster; the team list ends on the same line.
LIST_Y = TOP + 178 + 2 * 33 + 6 # Top of the team list (below logo, name, averages and formations).
LIST_ROWS = (ROSTER_BOTTOM - LIST_Y - 4) // 20 # Visible rows of the team list.
class SingleMatchMixin: # Team / formation / roster selection for the quick match.

    # ---------- helpers ----------
    def team_order(self): # Team indices sorted alphabetically.
        return sorted(range(len(self.teams)), key=lambda i: self.teams[i]["name"].casefold())

    def su_show(self, c): # Scroll the team list so that the selected team is visible.
        order = self.team_order()
        pos = order.index(self.sel[c]) if self.sel[c] in order else 0
        self.su_scroll[c] = int(clamp(self.su_scroll[c], pos - LIST_ROWS + 1, pos))
        self.su_scroll[c] = int(clamp(self.su_scroll[c], 0, max(0, len(order) - LIST_ROWS)))

    def su_wheel(self, dy): # Mouse wheel over the INTRO: scrolls the team list of the panel under the cursor.
        if self.mode != "intro" or self.menu_page != "quick" or self.options_open or self.joymap_open:
            return
        vx, _vy = self.su_to_virtual(pygame.mouse.get_pos())
        c = 0 if vx < SU_W / 2 else 1
        self.su_scroll[c] = int(clamp(self.su_scroll[c] - dy * 3, 0, max(0, len(self.teams) - LIST_ROWS)))

    def slot_positions(self, t): # [(role, position inside role)] in shirt order (index k <-> shirt number k + 1).
        out = []
        for role in ROLE_ORDER:
            out += [(role, j) for j in range(len(self.lineup[t][role]))]
        return out

    def shirt_of(self, t, idx): # Shirt number (1..11) of roster player idx, or None.
        for k, (_r, i) in enumerate(self.lineup_slots(t)):
            if i == idx:
                return k + 1
        return None

    def natural_pool(self, idx): # Role whose roster range contains idx.
        for role in ROLE_ORDER:
            lo, hi = ROLE_POOLS[role]
            if lo <= idx < hi:
                return role
        return "MID"

    def clear_number(self, t, idx): # Right click: the player goes back to the bench.
        for role, j in self.slot_positions(t):
            if self.lineup[t][role][j] == idx:
                self.lineup[t][role][j] = None

    def assign_number(self, t, idx): # Left click: give idx the next free shirt (prefer one in his natural role); a numbered player moves to the next free shirt.
        pos = self.slot_positions(t)
        cur = self.shirt_of(t, idx)
        start = cur if cur is not None else 0 # numbered player: look after his current slot
        order = list(range(start, len(pos))) + list(range(0, start))
        free = [k for k in order if self.lineup[t][pos[k][0]][pos[k][1]] is None]
        if not free:
            if cur is not None:
                return
            nat = self.natural_pool(idx) # Full line-up: take the shirt of the weakest starter of the same role (else of the whole team).
            cands = [k for k in range(len(pos)) if pos[k][0] == nat] or list(range(len(pos)))
            k = min(cands, key=lambda k: self.player_rating(t, self.lineup[t][pos[k][0]][pos[k][1]]))
            role, j = pos[k]
            self.lineup[t][role][j] = idx
            return
        nat = self.natural_pool(idx)
        k = next((k for k in free if pos[k][0] == nat), free[0]) if cur is None else free[0]
        self.clear_number(t, idx)
        role, j = pos[k]
        self.lineup[t][role][j] = idx

    # ---------- input ----------
    def single_click(self, hit, button=1): # Click on a tag of the single-match screen. Returns True when the tag was handled.
        k = hit[0]
        if button == 3:
            if k == "num":
                self.clear_number(hit[1], hit[2])
            return k == "num"
        if k == "num":
            self.assign_number(hit[1], hit[2])
        elif k == "team":
            _k, c, idx = hit
            self.sel[c], self.su_active = idx, c
            self.team_data[c] = self.teams[idx]
            self.fix_lineup(c, reset=True)
        elif k == "form":
            self.set_formation(hit[1], hit[2])
            self.su_active = hit[1]
        elif k == "start":
            self.start_match()
        else:
            return False
        return True

    def single_key(self, k): # Keyboard on the single-match screen.
        c = self.su_active
        if k == pygame.K_ESCAPE:
            self.menu_page = "main"
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.start_match()
        elif k == pygame.K_TAB:
            self.su_active = 1 - c
        elif k in (pygame.K_UP, pygame.K_DOWN):
            order = self.team_order()
            pos = order.index(self.sel[c]) if self.sel[c] in order else 0
            idx = order[int(clamp(pos + (1 if k == pygame.K_DOWN else -1), 0, len(order) - 1))]
            self.sel[c] = idx
            self.team_data[c] = self.teams[idx]
            self.fix_lineup(c, reset=True)
            self.su_show(c)
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            self.change_formation(c, 1 if k == pygame.K_RIGHT else -1)
        elif k == pygame.K_t:
            self.user_team = {0: 1, 1: None, None: 0}[self.user_team]
            self.save_options()

    # ---------- drawing ----------
    def draw_single_match(self, s, bd, hits, vx, vy): # Team / formation / roster screen of the single match.
        W = SU_W # The page background is the 22.CP picture (draw_intro); the surface is transparent.
        self._put(tr("menu.quick_match"), 56, (232, 236, 255), 26, cx=W // 2, shadow=True)
        self._put(tr("intro.subtitle"), 15, (205, 215, 235), 58, cx=W // 2, w=W - 300, shadow=True)
        self.back_button_br(s, hits, vx, vy) # Framed INDIETRO picture, always in the bottom right corner.
        names_ctl = (tr("intro.team_home"), tr("intro.team_away"))
        for c in (0, 1):
            self._draw_single_team(s, bd, hits, vx, vy, c, names_ctl)
        # bottom bar: line-up warning, start
        ok = self.lineup_ready()
        bad = [c for c in (0, 1) if self.lineup_count(c) != 11]
        if bad:
            self._put("   ".join("%s: %s" % (TEAM_NAMES[c], tr("intro.warn_lineup", n=self.lineup_count(c))) for c in bad), 17, (255, 170, 110), 622, cx=W // 2, w=W - 60, shadow=True)
        else: # Line-up complete: the warning gives way to the hint about the shirt numbers (right-aligned).
            self._put_right(tr("intro.hint_numbers"), 17, (205, 215, 235), 622, W - 30, W - 60, shadow=True)
        row = 672 # START row.
        sb = pygame.Rect(W // 2 - 140, row - 22, 280, 44)
        hov = sb.collidepoint(vx, vy)
        self.draw_generic_button(s, sb, tr("intro.start"), False, hov and ok, px=26)
        if not ok:
            shade = pygame.Surface(sb.size, pygame.SRCALPHA)
            shade.fill((8, 12, 24, 125))
            s.blit(shade, sb.topleft)
        if ok:
            hits.append((sb, ("start",)))
        self._put(tr("intro.footer"), 16, (205, 215, 235), ROSTER_BOTTOM + 17, cx=W // 2, w=W - 30, shadow=True) # Right under the team and player lists.

    def _draw_single_team(self, s, bd, hits, vx, vy, c, names_ctl, with_list=True, panel_bottom=None): # One team column: header, logo + pitch + formations + team list (with_list), full numbered roster, all on a blue panel.
        x0 = 30 + c * 495
        col = TEAM_COL[c]
        td = self.team_data[c]
        hb = pygame.Rect(x0, 70, 465, 26)
        pygame.draw.rect(s, tuple(int(v * 0.55) for v in col), hb, border_radius=5)
        if self.su_active == c:
            pygame.draw.rect(s, (255, 224, 90), hb, 2, border_radius=5)
        self._put(names_ctl[c], 21, (255, 255, 255), hb.centery, cx=hb.centerx)
        top = TOP
        self.blue_panel(s, pygame.Rect(x0 - 6, hb.bottom + 2, 477, (ROSTER_BOTTOM + 4 if panel_bottom is None else panel_bottom) - hb.bottom - 2)) # Same blue box as the OPTIONS page, under the header.
        # --- logo and stylised pitch with the formation ---
        lg = pygame.Rect(x0+5, top, 110, 110)
        pygame.draw.rect(s, (8, 10, 24), lg)
        img = self.gfx.logo(td["logo"])
        if img is not None:
            k = min(98.0 / img.get_width(), 98.0 / img.get_height())
            im = pygame.transform.scale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            s.blit(im, im.get_rect(center=lg.center))
        pygame.draw.rect(s, bd.FRAME, lg, 3)
        mp = pygame.Rect(x0 + 128, top, 98, 110)
        pygame.draw.rect(s, (40, 104, 48), mp)
        pygame.draw.rect(s, (220, 226, 220), mp, 1)
        pygame.draw.arc(s, (220, 226, 220), (mp.left + 28, mp.top - 20, 42, 40), math.pi, 2 * math.pi, 1)
        for sl in formation_slots(self.form_names[c]):
            pt = (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16)))
            pygame.draw.circle(s, col, pt, 5)
            pygame.draw.circle(s, (250, 250, 250), pt, 5, 1)
        # --- name, team averages, formations ---
        self._put(td["name"].upper(), 24, (232, 236, 255), top + 126, cx=x0 + 114, w=228)
        for n, (key, v) in enumerate(zip(("intro.attr_fit", "intro.attr_skill", "intro.attr_form"), td["avg"])):
            cx = x0 + 40 + n * 80
            self._put(tr(key), 15, bd.LIT, top + 146, cx=cx, w=84)
            self._put(str(v), 20, stat_color(v), top + 165, cx=cx)
        fy = top + 178
        for i, fname in enumerate(FORMATIONS):
            r = pygame.Rect(x0 +1 + (i % 3) * 78, fy + (i // 3) * 33, 74, 28)
            self.draw_chip(s, r, fname, self.form_names[c] == fname, r.collidepoint(vx, vy), col)
            hits.append((r, ("form", c, fname)))
        if with_list:
            self._draw_team_list(s, bd, hits, vx, vy, c, x0, col)
        # --- full roster: role, shirt number, name, Fitness / Skill / Form ---
        px0, rw = x0 + 238, 227
        vw = 24
        self._put("#", 16, bd.DIM, top + 6, cx=px0 + 37)
        for n, lab in enumerate((tr("intro.attr_fit_short"), tr("intro.attr_skill_short"), tr("intro.attr_form_short"))):
            self._put(lab, 12, bd.DIM, top + 6, cx=px0 + rw - vw * (3 - n) + vw // 2)
        pl = td["players"]
        for i in range(ROSTER):
            y = top + 16 + i * ROW_H
            rr = pygame.Rect(px0, y, rw, ROW_H - 2)
            num = self.shirt_of(c, i)
            if rr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), rr, border_radius=3)
            elif num:
                pygame.draw.rect(s, (22, 28, 62), rr, border_radius=3)
            role = self.natural_pool(i)
            rc = ROLE_COL[role]
            tag = pygame.Rect(px0, y, 24, rr.h)
            pygame.draw.rect(s, tuple(int(v * 0.35) for v in rc), tag, border_radius=3)
            self._put(ROLE_TAG[role], 12, rc, tag.centery, cx=tag.centerx)
            nb = pygame.Rect(px0 + 26, y, 22, rr.h)
            pygame.draw.rect(s, tuple(int(v * 0.8) for v in col) if num else (26, 30, 58), nb, border_radius=3)
            if num:
                self._put(str(num), 16, (255, 255, 255), nb.centery, cx=nb.centerx)
            self._put(pl[i] if i < len(pl) else "-", 15, bd.WHITE if num else bd.DIM, rr.centery, left=px0 + 52, w=rw - 52 - vw * 3 - 1 )
            for n in range(3):
                v = td["stats"][i][n]
                self._put(str(v), 14, stat_color(v), rr.centery, cx=px0 + rw - vw * (3 - n) + vw // 2)
            hits.append((rr, ("num", c, i)))

    def _draw_team_list(self, s, bd, hits, vx, vy, c, x0, col): # Alphabetical team list of column c: fills the column down to the bottom bar.
        order = self.team_order()
        if self._su_last_sel.get(c) != self.sel[c]:
            self._su_last_sel[c] = self.sel[c]
            self.su_show(c)
        self.su_scroll[c] = sc0 = int(clamp(self.su_scroll[c], 0, max(0, len(order) - LIST_ROWS)))
        ly = LIST_Y
        lr = pygame.Rect(x0, ly, 232, ROSTER_BOTTOM - ly)
        pygame.draw.rect(s, bd.BG, lr)
        for i, idx in enumerate(order[sc0:sc0 + LIST_ROWS]):
            rr = pygame.Rect(x0, ly + 2 + i * 20, 226, 20)
            if idx == self.sel[c]:
                pygame.draw.rect(s, tuple(int(v * 0.6) for v in col), rr)
            elif rr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), rr)
            self._put(self.teams[idx]["name"], 16, (255, 255, 255) if idx == self.sel[c] else bd.WHITE, rr.centery, left=x0 + 8, w=140)
            for n, v in enumerate(self.teams[idx]["avg"]): # Team averages: Fitness, Skill, Form.
                self._put(str(v), 14, stat_color(v), rr.centery, cx=x0 + 222 - 24 * (3 - n) + 12)
            hits.append((rr, ("team", c, idx)))
        if len(order) > LIST_ROWS:
            th = max(18, int(lr.h * LIST_ROWS / len(order)))
            ty = lr.y + int((lr.h - th) * sc0 / float(len(order) - LIST_ROWS))
            pygame.draw.rect(s, (80, 90, 150), (x0 + 226, ty, 5, th), border_radius=2)
        pygame.draw.rect(s, bd.FRAME, lr, 2)
