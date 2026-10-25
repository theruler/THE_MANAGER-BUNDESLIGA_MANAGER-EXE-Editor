"""INTRO screen (team / formation / numbered roster) and the OPTIONS page.

INTRO, per team:   [5-row alphabetical team list]   |  full roster, 20 rows: [shirt #] NAME  FIT SKL FRM
                   [logo + name + average values]   |  left click = give the next shirt number, right click = remove it
                   [formation buttons]              |
Shirt numbers 1..11 are the starting slots in formation order (1 = goalkeeper, then defenders, midfielders, forwards).
A match cannot start with fewer than 11 numbered players: the screen warns and START stays disabled.

Everything is drawn on the virtual surface self.su_surf (SU_W x SU_H) and scaled to the window with su_scale();
self.su_hits holds (rect, tag) pairs in virtual coordinates, consumed by su_click().
"""

import math

import pygame

from game_utils import clamp
from formation_system import formation_slots, FORMATIONS, ROLE_ORDER, ROLE_POOLS
from fonts import FONTS
from lang import Note, ROLE_TAG, T, tr
from layout import SU_H, SU_W
from match_config import TEAM_COL, TEAM_NAMES
from options_store import save_options

ROSTER = 20 # Players per team.
ROW_H = 23 # Height of a roster row.
TOP = 102 # Top of the team columns.
ROSTER_BOTTOM = TOP + 16 + ROSTER * ROW_H - 2 # Bottom edge of the roster; the team list ends on the same line.
LIST_Y = TOP + 178 + 2 * 33 + 6 # Top of the team list (below logo, name, averages and formations).
LIST_ROWS = (ROSTER_BOTTOM - LIST_Y - 4) // 20 # Visible rows of the team list.
ROLE_COL = {"GK": (90, 150, 255), "DEF": (90, 210, 120), "MID": (240, 200, 80), "FWD": (240, 90, 90)} # Role colours: POR blue, DIF green, CEN yellow, ATT red.

def stat_color(v): # Red (10) -> yellow -> green (99).
    t = clamp((v - 10) / 89.0, 0.0, 1.0)
    return (255, int(90 + 165 * min(1.0, t * 2)), 90) if t < 0.5 else (int(255 - 185 * (t - 0.5) * 2), 230, 110)


class IntroMixin: # INTRO and OPTIONS screens plus their mouse / keyboard handling.

    # ---------- helpers ----------
    def team_order(self): # Team indices sorted alphabetically.
        return sorted(range(len(self.teams)), key=lambda i: self.teams[i]["name"].casefold())

    def su_show(self, c): # Scroll the team list so that the selected team is visible.
        order = self.team_order()
        pos = order.index(self.sel[c]) if self.sel[c] in order else 0
        self.su_scroll[c] = int(clamp(self.su_scroll[c], pos - LIST_ROWS + 1, pos))
        self.su_scroll[c] = int(clamp(self.su_scroll[c], 0, max(0, len(order) - LIST_ROWS)))

    def su_wheel(self, dy): # Mouse wheel over the INTRO: scrolls the team list of the panel under the cursor.
        if self.mode != "intro" or self.options_open or self.joymap_open:
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

    # ---------- persistent options (DATA/options.json) ----------
    def options_snapshot(self): # Current values of everything saved in options.json.
        return dict(lang=str(T.current_language()), half_min=round(self.half_secs / 60.0, 3), slowmo=bool(self.slowmo_on),
                    replay_auto=bool(self.replay_auto), replay_secs=int(self.replay_secs), font_modern=bool(FONTS.modern),
                    hints=bool(self.show_hints), user_team=self.user_team, orig_audio=bool(self.audio.orig_on))

    def save_options(self): # Write options.json; a failure is reported once as a note on the INTRO.
        path = getattr(self, "options_path", None)
        if not path:
            return
        err = save_options(path, self.options_snapshot())
        if err and not getattr(self, "_options_warned", False):
            self._options_warned = True
            self.notes.append(Note("note.options_save", True, reason=err))

    # ---------- input ----------
    def su_click(self, pos, button=1): # Mouse click on INTRO / OPTIONS (button 1 = left, 3 = right).
        vx, vy = self.su_to_virtual(pos)
        hit = next((tag for r, tag in self.su_hits if r.collidepoint(vx, vy)), None) # first match wins
        if self.options_open and self.lang_open and (hit is None or hit[0] not in ("lang", "lang_toggle")):
            self.lang_open = False
            return
        if hit is None:
            return
        k = hit[0]
        if button == 3:
            if k == "num":
                self.clear_number(hit[1], hit[2])
            return
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
        elif k == "ctrl":
            self.user_team = hit[1]
        elif k == "start":
            self.start_match()
        elif k == "options":
            self.options_open, self.lang_open = True, False
        elif k == "back":
            self.options_open, self.lang_open = False, False
        elif k == "lang_toggle":
            self.lang_open = not self.lang_open
            if self.lang_open:
                self.langs = T.discover_languages()
        elif k == "lang":
            self.lang_open = False
            self.set_language(hit[1])
        elif k == "joymap":
            self.joymap_open, self.jm_wait = True, None
        elif k == "font":
            self.set_font_mode(hit[1])
        elif k == "replay_set":
            self.replay_auto = hit[1]
        elif k == "slowmo_set":
            self.slowmo_on = hit[1]
        elif k == "hints_set":
            self.show_hints = hit[1]
        elif k == "orig_set":
            self.audio.set_original(hit[1])
        elif k == "replay_secs":
            self.replay_secs = hit[1]
        elif k == "half":
            self.half_secs = hit[1]
        if k in ("ctrl", "lang", "font", "replay_set", "slowmo_set", "hints_set", "orig_set", "replay_secs", "half"):
            self.save_options()

    def su_key(self, k): # Keyboard on INTRO / OPTIONS.
        if self.options_open:
            if k == pygame.K_ESCAPE:
                self.options_open, self.lang_open = False, False
            return
        c = self.su_active
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.start_match()
        elif k == pygame.K_o:
            self.options_open = True
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

    # ---------- drawing (same buttons, colours and fonts as the original INTRO) ----------
    def _put(self, txt, px, col, cy, left=None, cx=None, w=None): # Text with the scoreboard font, optionally cut to w pixels.
        bd = self.board
        if w is not None:
            txt = self.fit_text(txt, px, w)
        bd.put(self.su_surf, bd.font(px).render(txt, True, col), left=left, cx=cx, cy=cy)

    def draw_intro(self): # INTRO or OPTIONS page; the joypad-mapping screen keeps its own drawing.
        if self.joymap_open:
            return self.draw_joymap()
        s, bd = self.su_surf, self.board
        s.fill((10, 12, 28))
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        if self.options_open:
            self._draw_options(s, bd, hits, vx, vy)
        else:
            self._draw_intro_main(s, bd, hits, vx, vy)
        sc, ox, oy = self.su_scale()
        self.screen.blit(pygame.transform.smoothscale(s, (int(SU_W * sc), int(SU_H * sc))), (int(ox), int(oy)))

    def _draw_intro_main(self, s, bd, hits, vx, vy):
        W = SU_W
        self._put(tr("intro.title"), 56, (232, 236, 255), 26, cx=W // 2)
        note = " | ".join(n.text() for n in self.notes[:2]) if self.notes else ""
        warn = any(n.warn for n in self.notes)
        self._put(note or tr("intro.subtitle"), 15, (255, 170, 110) if warn else (130, 140, 190), 58, cx=W // 2, w=W - 300)
        names_ctl = (tr("intro.team_home"), tr("intro.team_away"))
        for c in (0, 1):
            self._draw_intro_team(s, bd, hits, vx, vy, c, names_ctl)
        # bottom bar: line-up warning, control selector, options, start
        ok = self.lineup_ready()
        bad = [c for c in (0, 1) if self.lineup_count(c) != 11]
        if bad:
            self._put("   ".join("%s: %s" % (TEAM_NAMES[c], tr("intro.warn_lineup", n=self.lineup_count(c))) for c in bad), 17, (255, 170, 110), 622, cx=W // 2, w=W - 60)
        else: # Line-up complete: the warning gives way to the hint about the shirt numbers.
            self._put(tr("intro.hint_numbers"), 17, (130, 140, 190), 622, cx=W // 2, w=W - 60)
        row = 672 # START row.
        ob = pygame.Rect(W - 30 - 140, row - 22, 140, 44)
        self.su_chip(s, ob, tr("intro.options"), False, ob.collidepoint(vx, vy), (120, 170, 230), 20)
        hits.append((ob, ("options",)))
        sb = pygame.Rect(W // 2 - 140, row - 22, 280, 44)
        hov = sb.collidepoint(vx, vy)
        pygame.draw.rect(s, ((60, 150, 90) if hov else (44, 112, 70)) if ok else (40, 44, 58), sb, border_radius=8)
        pygame.draw.rect(s, (200, 255, 210) if ok else (80, 86, 104), sb, 2, border_radius=8)
        self._put(tr("intro.start"), 26, (255, 255, 255) if ok else (120, 126, 146), sb.centery, cx=sb.centerx, w=sb.w - 14)
        if ok:
            hits.append((sb, ("start",)))
        self._put(tr("intro.footer"), 16, (150, 158, 205), ROSTER_BOTTOM + 17, cx=W // 2, w=W - 30) # Right under the team and player lists.

    def _draw_intro_team(self, s, bd, hits, vx, vy, c, names_ctl): # One team column: header, logo + pitch + formations + team list, full numbered roster.
        x0 = 30 + c * 495
        col = TEAM_COL[c]
        td = self.team_data[c]
        hb = pygame.Rect(x0, 70, 465, 26)
        pygame.draw.rect(s, tuple(int(v * 0.55) for v in col), hb, border_radius=5)
        if self.su_active == c:
            pygame.draw.rect(s, (255, 224, 90), hb, 2, border_radius=5)
        self._put(names_ctl[c], 21, (255, 255, 255), hb.centery, cx=hb.centerx)
        top = TOP
        # --- logo and stylised pitch with the formation ---
        lg = pygame.Rect(x0, top, 110, 110)
        pygame.draw.rect(s, (8, 10, 24), lg)
        img = self.gfx.logo(td["logo"])
        if img is not None:
            k = min(98.0 / img.get_width(), 98.0 / img.get_height())
            im = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            s.blit(im, im.get_rect(center=lg.center))
        pygame.draw.rect(s, bd.FRAME, lg, 3)
        mp = pygame.Rect(x0 + 118, top, 98, 110)
        pygame.draw.rect(s, (40, 104, 48), mp)
        pygame.draw.rect(s, (220, 226, 220), mp, 1)
        pygame.draw.line(s, (220, 226, 220), (mp.left, mp.top + 2), (mp.right, mp.top + 2), 1)
        pygame.draw.arc(s, (220, 226, 220), (mp.left + 28, mp.top - 20, 42, 40), math.pi, 2 * math.pi, 1)
        for sl in formation_slots(self.form_names[c]):
            pt = (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16)))
            pygame.draw.circle(s, col, pt, 5)
            pygame.draw.circle(s, (250, 250, 250), pt, 5, 1)
        # --- name, team averages, formations ---
        self._put(td["name"].upper(), 24, (232, 236, 255), top + 126, left=x0, w=228)
        for n, (key, v) in enumerate(zip(("intro.attr_fit", "intro.attr_skill", "intro.attr_form"), td["avg"])):
            cx = x0 + 40 + n * 80
            self._put(tr(key), 15, bd.LIT, top + 146, cx=cx, w=84)
            self._put(str(v), 20, stat_color(v), top + 165, cx=cx)
        fy = top + 178
        for i, fname in enumerate(FORMATIONS):
            r = pygame.Rect(x0 + (i % 3) * 72, fy + (i // 3) * 33, 66, 28)
            self.su_chip(s, r, fname, self.form_names[c] == fname, r.collidepoint(vx, vy), col)
            hits.append((r, ("form", c, fname)))
        # --- team list: alphabetical, fills the column down to the bottom bar ---
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

    @staticmethod
    def _tr_or(key, default): # Translated text, or the English default when a language file lacks the key.
        try:
            t = tr(key)
        except Exception:
            return default
        return default if (not t or t == key) else t

    def _yes_no(self, s, hits, vx, vy, x, y, value, tag, enabled=True): # Two separate YES / NO buttons: the selected one is only outlined (no fill); disabled = greyed out, no click.
        for i, (lab, val) in enumerate(((tr("intro.on"), True), (tr("intro.off"), False))):
            r = pygame.Rect(x + i * 88, y, 80, 30)
            on = bool(value) == val
            pygame.draw.rect(s, (30, 34, 66) if enabled else (24, 26, 40), r, border_radius=6)
            if enabled:
                edge = (255, 224, 90) if on else ((120, 130, 210) if r.collidepoint(vx, vy) else (70, 78, 130))
            else:
                edge = (74, 78, 96) if on else (44, 48, 62)
            pygame.draw.rect(s, edge, r, 3 if on else 1, border_radius=6)
            self._put(lab, 18, ((255, 255, 255) if on else (150, 156, 190)) if enabled else (84, 88, 104), r.centery, cx=r.centerx)
            if enabled:
                hits.append((r, (tag, val)))

    def _draw_options(self, s, bd, hits, vx, vy): # OPTIONS page: every setting that used to sit on the INTRO.
        W = SU_W
        self._put(tr("intro.options_title"), 46, (232, 236, 255), 40, cx=W // 2)
        back = pygame.Rect(30, 16, 190, 32)
        self.su_chip(s, back, tr("intro.back"), False, back.collidepoint(vx, vy), (120, 170, 230), 20)
        hits.append((back, ("back",)))
        pygame.draw.line(s, bd.FRAME, (30, 76), (W - 30, 76), 2)
        x_lab, x_chip, y = 60, 400, 120
        rows = 0

        def label(text, yy):
            self._put(text, 22, bd.LIT, yy + 14, left=x_lab)

        label(tr("intro.half_len"), y)
        for i, m in enumerate((1, 2, 3, 5)):
            r = pygame.Rect(x_chip + i * 64, y, 56, 30)
            self.su_chip(s, r, str(m), abs(self.half_secs - m * 60.0) < 1, r.collidepoint(vx, vy))
            hits.append((r, ("half", m * 60.0)))
        y += 56
        label(tr("intro.slowmo"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.slowmo_on, "slowmo_set")
        y += 56
        label(tr("intro.replay_auto"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.replay_auto, "replay_set")
        y += 56
        grey = (84, 88, 104) # The replay length only matters while the automatic replay is ON: greyed out and not clickable otherwise.
        self._put(tr("intro.replay_secs"), 22, bd.LIT if self.replay_auto else grey, y + 14, left=x_lab)
        for i, m in enumerate((3, 5, 8, 10, 15)):
            r = pygame.Rect(x_chip + i * 64, y, 56, 30)
            if self.replay_auto:
                self.su_chip(s, r, str(m), self.replay_secs == m, r.collidepoint(vx, vy))
                hits.append((r, ("replay_secs", m)))
            else:
                on = self.replay_secs == m
                pygame.draw.rect(s, (24, 26, 40), r, border_radius=6)
                pygame.draw.rect(s, (74, 78, 96) if on else (44, 48, 62), r, 3 if on else 1, border_radius=6)
                self._put(str(m), 18, grey, r.centery, cx=r.centerx)
        y += 56
        label(tr("intro.hints"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.show_hints, "hints_set")
        y += 56
        label(tr("intro.font"), y)
        for i, (lab, val) in enumerate(((tr("intro.font_modern"), True), (tr("intro.font_old"), False))):
            r = pygame.Rect(x_chip + i * 150, y, 142, 30)
            self.su_chip(s, r, lab, FONTS.modern == val, r.collidepoint(vx, vy))
            hits.append((r, ("font", val)))
        y += 56
        label(tr("intro.controls"), y)
        for i, (lab, val) in enumerate(((tr("intro.ctrl_home"), 0), (tr("intro.ctrl_away"), 1), (tr("intro.ctrl_spec"), None))):
            r = pygame.Rect(x_chip + i * 168, y, 160, 30)
            self.su_chip(s, r, lab, self.user_team == val, r.collidepoint(vx, vy), px=16)
            hits.append((r, ("ctrl", val)))
        y += 56
        ok_orig = bool(self.audio.orig_available) # Greyed out when neither DIGI.VOC nor BM2TITLE.CMF was found at start-up.
        self._put(self._tr_or("intro.orig_audio", "Original audio:"), 22, bd.LIT if ok_orig else (84, 88, 104), y + 14, left=x_lab)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.audio.orig_on and ok_orig, "orig_set", ok_orig)
        if not ok_orig:
            self._put(self._tr_or("intro.orig_missing", "DIGI.VOC / BM2TITLE.CMF not found"), 15, (84, 88, 104), y + 14, left=x_chip + 190)
        y += 56
        label(tr("intro.joymap"), y)
        jb = pygame.Rect(x_chip, y, 240, 32)
        self.su_chip(s, jb, tr("intro.joymap"), False, jb.collidepoint(vx, vy), (120, 170, 230), 20)
        hits.append((jb, ("joymap",)))
        self.draw_lang_dropdown(s, bd, hits, vx, vy) # Language selector (top right, as before); its pop-up goes in front of the hits.
