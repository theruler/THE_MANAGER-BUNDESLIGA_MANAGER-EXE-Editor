"""INTRO dispatcher: main menu, OPTIONS, joypad mapping and persistent options.

Pages (self.menu_page):  "main"   three buttons on PIC\\47.CP
                         "quick"  single match: team / roster selection   -> single_match_system.py
                         "champ"  championship                            -> championship_system.py
OPTIONS is an overlay flag (self.options_open) opened from the main menu, drawn on PIC\\22.CP; the joypad mapping opens from it.

Everything is drawn on the virtual surface self.su_surf (SU_W x SU_H) and scaled to the window with su_scale();
self.su_hits holds (rect, tag) pairs in virtual coordinates, consumed by su_click().
"""

import json
import os

import pygame

from fonts import FONTS
from i18n import Note, T, tr
from joystick import JOY_ACTIONS, JOY_HOTSPOTS, JOY_IMG
from graphics_system import (ART_RECTS, ART_SHEET, ART_SHEET_OF, FRAME_H, FRAME_W, NO_TRIM, SU_H, SU_W,
                             art_size)
from match_config import SPEED_MAX_CHOICES

OPTIONS_FILE = "options.json"

def options_path(dirs): # options.json in the first folder that already has it, else in the first folder (created on save).
    for d in dirs:
        p = os.path.join(d, OPTIONS_FILE)
        if os.path.isfile(p):
            return p
    return os.path.join(dirs[0], OPTIONS_FILE)

def _num(v, lo, hi): # A number inside lo..hi, or None.
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi else None

def load_options(path): # Saved options as a validated dict (unknown or invalid entries are dropped, a missing file gives {}).
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    if isinstance(raw.get("lang"), str) and raw["lang"].strip():
        out["lang"] = raw["lang"].strip().lower()
    v = _num(raw.get("half_min"), 0.5, 45)
    if v is not None:
        out["half_min"] = v
    v = _num(raw.get("replay_secs"), 1, 60)
    if v is not None:
        out["replay_secs"] = int(v)
    v = _num(raw.get("speed_max"), 1, 100)
    if v is not None:
        out["speed_max"] = int(v)
    for k in ("slowmo", "replay_auto", "font_modern", "hints", "orig_audio"):
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    if "user_team" in raw and (raw["user_team"] is None or raw["user_team"] in (0, 1) and not isinstance(raw["user_team"], bool)):
        out["user_team"] = raw["user_team"]
    return out

def save_options(path, opts): # Write the options; returns an error text or None.
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(opts, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError as ex:
        return str(ex)
    return None

MENU_BTN_W, MENU_BTN_H, MENU_BTN_GAP = 420, 64, 26 # Main-menu buttons.
OPT_WHITE = (255, 255, 255) # Every font of the OPTIONS page is white (22.CP is a dark-ish marble); only warnings keep their orange.
OPT_WARN = (255, 170, 110)
OPT_RULE = (70, 76, 110)


class IntroMixin: # Main menu, OPTIONS, joypad mapping and intro input dispatch.
    exit_ask = False # The main menu asks "Sei sicuro?" before closing the program.
    _press_rect = None # Rect (tuple) of the button the left mouse button went down on (None = none): drives the pressed frame and the click on release.
    _txt_shadow = False # True while a page wants a shadow under every text (championship).

    # ---------- persistent options (DATA/options.json) ----------
    def options_snapshot(self): # Current values of everything saved in options.json.
        return dict(lang=str(T.current_language()), half_min=round(self.half_secs / 60.0, 3), slowmo=bool(self.slowmo_on),
                    replay_auto=bool(self.replay_auto), replay_secs=int(self.replay_secs), font_modern=bool(FONTS.modern),
                    hints=bool(self.show_hints), user_team=self.user_team, orig_audio=bool(self.audio.orig_on), speed_max=int(self.speed_max))

    def save_options(self): # Write options.json; a failure is reported once as a note on the INTRO.
        path = getattr(self, "options_path", None)
        if not path:
            return
        err = save_options(path, self.options_snapshot())
        if err and not getattr(self, "_options_warned", False):
            self._options_warned = True
            self.notes.append(Note("note.options_save", True, reason=err))

    # ---------- input ----------
    def intro_mouse(self, ev): # Left button of the intro pages: down = remember the button (pressed frame), up over the same button = click.
        vx, vy = self.su_to_virtual(ev.pos)
        hit = next((r for r, _tag in self.su_hits if r.collidepoint(vx, vy)), None)
        if ev.type == pygame.MOUSEBUTTONDOWN:
            self._press_rect = tuple(hit) if hit is not None else None
            return None
        down, self._press_rect = self._press_rect, None
        if (down is None and hit is None) or (down is not None and hit is not None and tuple(hit) == down):
            self.su_click(ev.pos, 1) # (a click outside every button still closes the language list)
        return None

    def su_click(self, pos, button=1): # Mouse click on the intro pages (button 1 = left, 3 = right).
        vx, vy = self.su_to_virtual(pos)
        hit = next((tag for r, tag in self.su_hits if r.collidepoint(vx, vy)), None) # first match wins
        if self.options_open and self.lang_open and (hit is None or hit[0] not in ("lang", "lang_toggle")):
            self.lang_open = False
            return
        if hit is None:
            return
        k = hit[0]
        if not self.options_open and self.menu_page == "quick" and self.single_click(hit, button):
            return
        if not self.options_open and self.menu_page == "champ" and self.championship_click(hit, button):
            return
        if button == 3:
            return
        if k == "menu_champ":
            self.championship_open()
        elif k == "menu_quick":
            self.menu_page = "quick"
        elif k == "menu_options":
            self.options_open, self.lang_open = True, False
        elif k == "menu_exit":
            self.exit_ask = True
        elif k == "exit_no":
            self.exit_ask = False
        elif k == "exit_yes":
            pygame.event.post(pygame.event.Event(pygame.QUIT)) # The main loop closes the program.
        elif k == "back":
            if self.options_open:
                self.options_open, self.lang_open = False, False
            else:
                self.menu_page = "main"
        elif k == "ctrl":
            self.user_team = hit[1]
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
        elif k == "speed_step":
            ch = SPEED_MAX_CHOICES
            pos = ch.index(self.speed_max) if self.speed_max in ch else len(ch) - 1
            self.speed_max = ch[max(0, min(len(ch) - 1, pos + hit[1]))]
            self.speed_idx = min(self.speed_idx, self.speed_top())
        if k in ("ctrl", "lang", "font", "replay_set", "slowmo_set", "hints_set", "orig_set", "replay_secs", "half", "speed_step"):
            self.save_options()

    def su_key(self, k): # Keyboard on the intro pages.
        if self.options_open:
            if k == pygame.K_ESCAPE:
                self.options_open, self.lang_open = False, False
            return
        if self.menu_page == "quick":
            self.single_key(k)
        elif self.menu_page == "champ":
            self.championship_key(k)
        elif self.exit_ask:
            if k in (pygame.K_s, pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                pygame.event.post(pygame.event.Event(pygame.QUIT))
            elif k in (pygame.K_n, pygame.K_ESCAPE):
                self.exit_ask = False
        else:
            if k == pygame.K_o:
                self.options_open, self.lang_open = True, False
            elif k == pygame.K_c:
                self.championship_open()
            elif k in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.menu_page = "quick"

    def _put(self, txt, px, col, cy, left=None, cx=None, w=None, shadow=None): # Text with the scoreboard font, optionally cut to w pixels, optionally with a shadow.
        bd = self.board
        if w is not None:
            txt = self.fit_text(txt, px, w)
        if self._txt_shadow if shadow is None else shadow: # None: the page decides (_txt_shadow); True / False force it.
            o = 1 + px // 40 # The shadow grows with the text: 1 pixel for small texts, 2 for the big titles.
            bd.put(self.su_surf, bd.font(px).render(txt, True, (0, 0, 0)), left=None if left is None else left + o, cx=None if cx is None else cx + o, cy=cy + o)
        bd.put(self.su_surf, bd.font(px).render(txt, True, col), left=left, cx=cx, cy=cy)

    def _put_right(self, txt, px, col, cy, right, w, shadow=None): # Text ending at x = right.
        txt = self.fit_text(txt, px, w)
        self._put(txt, px, col, cy, left=right - self.board.font(px).size(txt)[0], shadow=shadow)

    def blue_panel(self, s, rect): # The blue box with a black shadow of the OPTIONS page.
        pygame.draw.rect(s, (0, 0, 0), rect.move(4, 4))
        pygame.draw.rect(s, (0, 0, 112), rect)

    # ---------- drawing ----------
    def draw_intro(self): # Current intro page; the joypad-mapping screen keeps its own drawing.
        if self.joymap_open:
            return self.draw_joymap()
        s, bd = self.su_surf, self.board
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        bg = None # Menu picture drawn under the (transparent) virtual surface by present_su().
        if self.options_open:
            bg = "options"
            s.fill((0, 0, 0, 0))
            self.draw_options(s, bd, hits, vx, vy)
        elif self.menu_page == "quick":
            bg = "options" # Same picture (22.CP) as the OPTIONS page.
            s.fill((0, 0, 0, 0))
            self.draw_single_match(s, bd, hits, vx, vy)
        elif self.menu_page == "champ":
            bg = "options" # Same picture (22.CP) as the OPTIONS page.
            s.fill((0, 0, 0, 0))
            self.draw_championship(s, bd, hits, vx, vy)
        else:
            bg = "title"
            s.fill((0, 0, 0, 0))
            self.draw_main_menu(s, bd, hits, vx, vy)
        self.present_su(bg)

    def draw_main_menu(self, s, bd, hits, vx, vy): # Four pictures in a row at the bottom (3.VGA), the text under them; USCITA asks "Sei sicuro?" first.
        W, H = SU_W, SU_H
        items = (("menu_champ", tr("menu.championship")), ("menu_quick", tr("menu.quick_match")), ("menu_options", tr("intro.options")),
                 ("menu_exit", tr("menu.exit")))
        sc = 3 if W < 1400 else 4
        w, h, gap = FRAME_W * sc, FRAME_H * sc, 20 * sc
        x = (W - (len(items) * w + (len(items) - 1) * gap)) // 2
        y = H - 70 - 28 - h
        msg = self.championship_main_notice() # "PARTITA INTERROTTA" while a championship match waits for RIPRENDI.
        if msg:
            self._put(msg, 30, (255, 224, 90), y - 30, cx=W // 2, w=W - 60, shadow=True)
        for tag, label in items:
            ask = self.exit_ask
            r = self.framed_button(s, hits, vx, vy, "menu_exit_sure" if tag == "menu_exit" and ask else tag, 0, sc, x, y, (tag,), False, label, not ask)
            self._put(label, 24, (255, 255, 255) if r.collidepoint(vx, vy) and not ask else (225, 235, 250), r.bottom + 18, cx=r.centerx, w=w + gap - 4, shadow=True)
            x += w + gap
        if self.exit_ask: # Question in the middle of the screen.
            box = pygame.Rect(W // 2 - 240, H // 2 - 100, 480, 200)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (8, 14, 40, 235), panel.get_rect(), border_radius=12)
            s.blit(panel, box)
            pygame.draw.rect(s, (255, 224, 90), box, 3, border_radius=12)
            self._put(tr("menu.sure"), 40, (255, 255, 255), box.y + 62, cx=box.centerx, w=box.w - 30, shadow=True)
            for j, (tag, lab) in enumerate((("exit_yes", tr("menu.yes")), ("exit_no", tr("menu.no")))):
                r = pygame.Rect(box.centerx + (-150 if j == 0 else 20), box.y + 118, 130, 46)
                hov = r.collidepoint(vx, vy)
                pygame.draw.rect(s, (60, 150, 90) if (hov and j == 0) else (44, 112, 70) if j == 0 else (150, 60, 60) if hov else (112, 44, 44), r, border_radius=8)
                pygame.draw.rect(s, (230, 235, 245), r, 2, border_radius=8)
                self._put(lab, 28, (255, 255, 255), r.centery, cx=r.centerx, w=r.w - 12, shadow=True)
                hits.append((r, (tag,)))

    # ---------- button pictures (3.VGA) ----------
    def art(self, name, idx=0, scale=1): # Picture `name` (see the UI button pictures in graphics_system.py) scaled by an integer factor, opaque (no alpha); None when its sheet is not available.
        cache = self.__dict__.setdefault("_art_cache", {})
        stem = ART_SHEET_OF.get(name, ART_SHEET)
        if ("sheet", stem) not in cache:
            cache[("sheet", stem)] = None
            try: # The VGA file of the PIC folder, decoded by Graphics.pic_surface().
                fn = getattr(self.gfx, "pic_surface", None)
                cache[("sheet", stem)] = fn(stem) if fn else None
            except Exception:
                cache[("sheet", stem)] = None
        sheet = cache[("sheet", stem)]
        if sheet is None or name not in ART_RECTS:
            return None
        key = (name, idx, scale)
        if key not in cache:
            x1, y1, x2, y2 = ART_RECTS[name][min(idx, len(ART_RECTS[name]) - 1)]
            try:
                img = sheet.subsurface(pygame.Rect(x1, y1, x2 - x1 + 1, y2 - y1 + 1)).copy().convert() # convert(): drops the alpha channel.
                w, h = img.get_size()
                if name not in NO_TRIM and w > 2 and h > 2: # Without the 1-pixel black border, stretched back over the same space.
                    img = img.subsurface(pygame.Rect(1, 1, w - 2, h - 2)).copy()
                cache[key] = pygame.transform.scale(img, (w * scale, h * scale)) if (w, h) != img.get_size() or scale != 1 else img
            except (ValueError, pygame.error):
                cache[key] = None
        return cache[key]

    def framed_button(self, s, hits, vx, vy, name, idx, sc, x, y, tag, selected=False, fb_label="", clickable=True): # Picture of 3.VGA centred in its frame (24.VGA; 25.VGA while the mouse button is held on it). Returns the outer (frame) rect.
        outer = pygame.Rect(x, y, FRAME_W * sc, FRAME_H * sc)
        bw, bh = art_size(name)
        inner = pygame.Rect(0, 0, bw * sc, bh * sc)
        inner.center = outer.center
        hov = outer.collidepoint(vx, vy) and clickable
        frame = self.art("frame_down" if hov and self._press_rect == tuple(outer) else "frame", 0, sc) # 25.VGA while the mouse button is held on this button
        if frame is not None:
            s.blit(frame, outer)
        img = self.art(name, idx, sc)
        if img is None:
            self.draw_generic_button(s, inner, self.fit_text(fb_label, 16, inner.w - 12), selected, hov, px=16)
        else:
            s.blit(img, inner)
            if selected: # yellow frame, 1 pixel inside the old one (overlapping the picture)
                pygame.draw.rect(s, (255, 224, 90), inner.inflate(4, 4), 3)
            elif hov:
                pygame.draw.rect(s, (255, 224, 90), inner.inflate(2, 2), 2)
        if clickable:
            hits.append((outer, tag))
        return outer

    def back_button(self, s, hits, vx, vy, x, y, scale=2, fb=None): # INDIETRO: the framed picture, or the old generic button when 3.VGA is missing.
        if self.art("back", 0, scale) is None:
            r = fb if fb is not None else pygame.Rect(x, y + 8, 190, 32)
            self.draw_generic_button(s, r, tr("intro.back"), False, r.collidepoint(vx, vy), px=20)
            hits.append((r, ("back",)))
            return r
        return self.framed_button(s, hits, vx, vy, "back", 0, scale, x, y, ("back",))

    def back_button_br(self, s, hits, vx, vy, scale=2): # INDIETRO in the bottom right corner (same place as in the championship hub).
        x, y = SU_W - 16 - FRAME_W * scale, SU_H - 30 - FRAME_H * scale
        return self.back_button(s, hits, vx, vy, x, y, scale, pygame.Rect(SU_W - 16 - 190, SU_H - 30 - 32, 190, 32))

    def _yes_no(self, s, hits, vx, vy, x, y, value, tag, enabled=True): # YES / NO picture pair (33.VGA): the lit one is the current value; disabled = darkened, no click.
        ui = self.gfx.ui
        h = ui["yes_on"][0].get_height()
        top = y + 15 - h // 2 # Vertically centred on the 30 px row used by the labels.
        for i, (key, val) in enumerate((("yes", True), ("no", False))):
            on = bool(value) == val
            img = ui[key + ("_on" if on else "_off")][0 if enabled else 1]
            r = img.get_rect(topleft=(x + i * (img.get_width() + 8), top))
            s.blit(img, r)
            if enabled:
                if r.collidepoint(vx, vy):
                    pygame.draw.rect(s, (255, 224, 90), r.inflate(4, 4), 2)
                hits.append((r, (tag, val)))

    def _speed_button(self, s, hits, vx, vy, x, y): # Long "- value +" button (33.VGA): left half = slower limit, right half = faster limit.
        img = self.gfx.ui["speeds"][0]
        r = img.get_rect(topleft=(x, y + 15 - img.get_height() // 2))
        s.blit(img, r)
        for half, d in ((pygame.Rect(r.x, r.y, r.w // 8, r.h), -1), (pygame.Rect(r.x+r.w-25, r.y, r.w // 8, r.h), 1)):
            if half.collidepoint(vx, vy):
                pygame.draw.rect(s, (255, 224, 90), half.inflate(4, 4), 2)
            hits.append((half, ("speed_step", d)))
        self._put("%dx" % self.speed_max, 22, OPT_WHITE, r.centery, cx=r.centerx)

    def _num_button(self, s, hits, vx, vy, x, y, text, selected, tag, enabled=True): # Number on the 31.VGA button.
        img = self.gfx.ui["button"][0 if enabled else 1]
        r = img.get_rect(topleft=(x, y + 15 - img.get_height() // 2))
        s.blit(img, r)
    
        if enabled:
            col = (192, 112, 32) if selected else OPT_WHITE
            if r.collidepoint(vx, vy):
                pygame.draw.rect(s, (255, 224, 90), r.inflate(4, 4), 2)
            hits.append((r, tag))
        else:
            col = (120, 106, 40) if selected else (120, 120, 120)
    
        if selected:
            bg = pygame.Rect(0, 0, 44, 30)
            bg.center = (r.centerx, r.centery)
            pygame.draw.rect(s, (64, 64, 96), bg)
            pygame.draw.line(s, (0, 0, 0), bg.topleft, bg.topright, 2)
            pygame.draw.line(s, (0, 0, 0), bg.topleft, bg.bottomleft, 2)
    
        self._put(text, 30, (0, 0, 0), r.centery + 3, cx=r.centerx + 3)
        self._put(text, 30, col, r.centery, cx=r.centerx)

    def draw_options(self, s, bd, hits, vx, vy): # OPTIONS page (background 22.cp, marble grey -> dark text).
        W = SU_W
        x_lab, x_chip, y = 60, 450, 120

        def label(text, yy, px=28, left=None, cx=None, y_offset=14):
            if cx is not None:
                shadow_pos = {"cx": cx + 3}
                text_pos = {"cx": cx}
            else:
                left = x_lab if left is None else left
                shadow_pos = {"left": left + 3}
                text_pos = {"left": left}

            self._put(text, px, (0, 0, 0), yy + y_offset + 3, **shadow_pos)
            self._put(text, px, OPT_WHITE, yy + y_offset, **text_pos)

        label(tr("intro.options_title"), 40, 46, cx=W // 2, y_offset=0)
        self.back_button(s, hits, vx, vy, 30, 8, 2)

        # Options panel: position and dimensions.
        panel_x, panel_y = 40, 100
        panel_w, panel_h = W - 80, 580
        panel = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
        self.blue_panel(s, panel)

        label(tr("intro.half_len"), y)
        for i, m in enumerate((1, 2, 3, 5)):
            self._num_button(s, hits, vx, vy, x_chip + i * 68, y, str(m), abs(self.half_secs - m * 60.0) < 1, ("half", m * 60.0))
        y += 56

        label(tr("intro.speed"), y)
        self._speed_button(s, hits, vx, vy, x_chip, y)
        y += 56

        ok_orig = bool(self.audio.orig_available)
        label(tr("intro.orig_audio"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.audio.orig_on and ok_orig, "orig_set", ok_orig)
        if not ok_orig:
            self._put(tr("intro.orig_missing"), 15, OPT_WHITE, y + 14, left=x_chip + 120)
        y += 56

        label(tr("intro.hints"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.show_hints, "hints_set")
        y += 56

        label(tr("intro.slowmo"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.slowmo_on, "slowmo_set")
        y += 56

        label(tr("intro.replay_auto"), y)
        self._yes_no(s, hits, vx, vy, x_chip, y, self.replay_auto, "replay_set")
        y += 56

        label(tr("intro.replay_secs"), y)
        for k_, m in enumerate((3, 5, 8, 10, 15)):
            self._num_button(s, hits, vx, vy, x_chip + k_ * 68, y, str(m), self.replay_secs == m, ("replay_secs", m), self.replay_auto)
        y += 50
        pygame.draw.line(s, OPT_WHITE, (50, y), (W - 50, y), 4)
        y += 14
        label(tr("intro.font"), y)
        for i, (lab, val) in enumerate(((tr("intro.font_modern"), True), (tr("intro.font_old"), False))):
            r = pygame.Rect(x_chip + i * 160, y, 150, 30)
            self.draw_generic_button(s, r, lab, FONTS.modern == val, r.collidepoint(vx, vy))
            hits.append((r, ("font", val)))
        y += 56

        label(tr("intro.controls"), y)
        for i, (lab, val) in enumerate(((tr("intro.ctrl_home"), 0), (tr("intro.ctrl_away"), 1), (tr("intro.ctrl_spec"), None))):
            r = pygame.Rect(x_chip + i * 160, y, 150, 30)
            self.draw_generic_button(s, r, lab, self.user_team == val, r.collidepoint(vx, vy), px=16)
            hits.append((r, ("ctrl", val)))
        y += 56

        label(tr("intro.joymap"), y)
        jb = pygame.Rect(x_chip, y, 150, 32)
        self.draw_generic_button(s, jb, tr("intro.joymap"), False, jb.collidepoint(vx, vy), px=20)
        hits.append((jb, ("joymap",)))

        note = " | ".join(n.text() for n in self.notes[:2]) if self.notes else ""
        if note:
            self._put(note, 15, OPT_WARN if any(n.warn for n in self.notes) else OPT_WHITE, SU_H - 18, cx=W // 2, w=W - 60)

        self.draw_lang_dropdown(s, bd, hits, vx, vy)

    def present_su(self, bg=None): # Show the virtual menu surface on the window; with bg ("title" / "options") the menu picture goes underneath, whole and pixel-exact, and su_surf must be transparent where it should show through.
        if bg:
            self.screen.fill((0, 0, 0))
            img = self.gfx.menu_background(bg, (self.W, self.H))
            if img is not None:
                self.screen.blit(img, ((self.W - img.get_width()) // 2, (self.H - img.get_height()) // 2))
        sc, ox, oy = self.su_scale()
        self.screen.blit(pygame.transform.smoothscale(self.su_surf, (int(SU_W * sc), int(SU_H * sc))), (int(ox), int(oy)))

    def draw_joymap(self): # Draw the joystick-mapping and control-assignment screen.
        s, bd, j = self.su_surf, self.board, self.joy
        s.fill((0, 0, 0, 0)) # Transparent: PIC\\22.CP is drawn under it by present_su().
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        W = SU_W
        bd.put(s, bd.font(46).render(tr("intro.joymap"), True, (255, 255, 255)), cx=W // 2, cy=26)
        pads = j.names()
        st = ", ".join(pads) if pads else tr("joy.none")
        bd.put(s, bd.font(26).render(self.fit_text(st, 16, W - 40), True, (255, 255, 255)), cx=W // 2, cy=58)
        dt = 1.0 / 60.0
        self.jm_flash = {k: v - dt for k, v in self.jm_flash.items() if v - dt > 0}
        flash_ctrl = {j.control_of(t) for t in self.jm_flash}
        focus = None
        y = 80
        for act, _k, _u, label in JOY_ACTIONS:
            r = pygame.Rect(20, y, 410, 24)
            toks = j.cfg["buttons"].get(act, [])
            hov = r.collidepoint(vx, vy)
            waiting = self.jm_wait == act
            if waiting or (hov and not self.jm_wait):
                focus = act
            col = (96, 82, 20) if waiting else ((36, 44, 92) if hov else (22, 26, 56))
            pygame.draw.rect(s, col, r, border_radius=4)
            if j.is_held(act):
                pygame.draw.rect(s, (90, 220, 120), r, 2, border_radius=4)
            bd.put(s, bd.font(16).render(tr("joy.act." + act), True, (255, 236, 150) if waiting else (255, 255, 255)), left=r.left + 8, cy=r.centery)
            txt = tr("joy.press") if waiting else (", ".join(j.token_label(t) for t in toks) or "-")
            bd.put(s, bd.font(16).render(self.fit_text(txt, 16, 150), True, (255, 224, 90) if waiting else (255, 255, 255)), cx=r.right - 80, cy=r.centery)
            hits.append((r, ("act", act)))
            y += 26
        bx, by0, bw, bh = 48, 0, 945, 800
        sc = min(560.0 / bw, 500.0 / bh)
        ox, oy = 450, 92
        if self.jm_img is None and self.joy_img_path:
            try:
                im = pygame.image.load(self.joy_img_path).convert_alpha()
                self.jm_img = pygame.transform.smoothscale(im.subsurface(pygame.Rect(bx, by0, bw, bh)).copy(), (int(bw * sc), int(bh * sc)))
            except (pygame.error, ValueError, OSError):
                self.jm_img = False
        if self.jm_img:
            pygame.draw.rect(s, (22, 26, 56), (ox - 6, oy - 6, self.jm_img.get_width() + 12, self.jm_img.get_height() + 12), border_radius=8)
            s.blit(self.jm_img, (ox, oy))
        else:
            bd.put(s, bd.font(18).render(tr("joy.img_missing", name=JOY_IMG), True, (255, 170, 110)), cx=ox + 280, cy=oy + 200)
        sel_ctrl = {j.control_of(t) for t in j.cfg["buttons"].get(focus, [])} if focus else set()
        bound = {j.control_of(t) for toks in j.cfg["buttons"].values() for t in toks}
        self.jm_spots = {}
        drag = self.jm_drag
        tgt = self.jm_near(drag["pos"][0], drag["pos"][1], skip=drag["ctrl"], rad=self.JM_SNAP) if drag else None
        chip = {"triangle": "Tri", "circle": "Cer", "cross": "Cro", "square": "Qua", "select": "Sel", "start": "Sta"}
        for name, (hx, hy) in JOY_HOTSPOTS.items():
            if name in ("lstick", "rstick"):
                continue
            cx, cy = int(ox + (hx - bx) * sc), int(oy + (hy - by0) * sc)
            self.jm_spots[name] = (cx, cy)
            if name in self.JM_DRAGGABLE:
                lab = chip.get(name, name.upper())
                moving = drag is not None and drag["ctrl"] == name
                if name in flash_ctrl:
                    pygame.draw.circle(s, (90, 255, 140), (cx, cy), 16, 0)
                elif name == tgt:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 19, 3)
                elif name in sel_ctrl:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 16, 3)
                if not moving:
                    pygame.draw.circle(s, (24, 34, 80), (cx, cy), 11, 0)
                    pygame.draw.circle(s, (120, 150, 230), (cx, cy), 11, 1)
                    bd.put(s, bd.font(11).render(lab, True, (230, 236, 255)), cx=cx, cy=cy)
            else:
                if name in flash_ctrl:
                    pygame.draw.circle(s, (90, 255, 140), (cx, cy), 15, 0)
                elif name in sel_ctrl:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 15, 3)
                elif name in bound:
                    pygame.draw.circle(s, (80, 140, 255), (cx, cy), 4, 0)
        if drag:
            dxp, dyp = int(drag["pos"][0]), int(drag["pos"][1])
            pygame.draw.circle(s, (255, 215, 0), (dxp, dyp), 14, 0)
            bd.put(s, bd.font(12).render(chip.get(drag["ctrl"], drag["ctrl"].upper()), True, (20, 20, 20)), cx=dxp, cy=dyp)
        for name, lab, dx_ in (("lstick", tr("joy.lstick"), 0), ("rstick", tr("joy.rstick"), 0)):
            hx, hy = JOY_HOTSPOTS[name]
            cx, cy = int(ox + (hx - bx) * sc), int(oy + (hy - by0) * sc)
            bd.put(s, bd.font(14).render(lab, True, (80, 84, 120)), cx=cx, cy=int(oy + (712 - by0) * sc))
        if self.jm_wait:
            msg = tr("joy.wait") + tr("joy.act." + self.jm_wait) + tr("joy.cancel_hint")
            colr = (255, 255, 255)
        else:
            msg = tr("joy.hint")
            colr = (255, 255, 255)
        for i, line in enumerate(self._wrap(msg, bd.font(16), 560)):
            bd.put(s, bd.font(16).render(line, True, colr), cx=ox + 280, cy=oy + int(bh * sc) + 28 + i * 20)
        for rect, lab, tag in ((pygame.Rect(690, 660, 140, 34), tr("joy.reset"), ("reset",)),
                               (pygame.Rect(850, 660, 140, 34), tr("joy.close"), ("close",))):
            self.draw_chip(s, rect, lab, False, rect.collidepoint(vx, vy), (120, 170, 230), 18, fg=(255, 255, 255))
            hits.append((rect, tag))
        info = "File: " + os.path.abspath(j.write_path)
        if j.error:
            info += "   !  " + j.error
        bd.put(s, bd.font(13).render(self.fit_text(info, 13, 640), True, (255, 170, 110) if j.error else (255, 255, 255)), left=450, cy=700)
        self.present_su("options")

    def draw_lang_dropdown(self, s, bd, hits, vx, vy): # Draw the language selection dropdown.
        if not self.langs:
            return
        cur = T.current_language()
        names = dict(self.langs)
        btn = pygame.Rect(SU_W - 30 - 160, 12, 160, 32)
        lab = bd.font(16).render(tr("intro.language"), True, (255, 255, 255))
        bd.put(s, lab, left=btn.left - lab.get_width() - 8, cy=btn.centery)
        s.blit(self.gfx.make_generic_button(btn.w), btn)
        if self.lang_open or btn.collidepoint(vx, vy):
            pygame.draw.rect(s, (255, 224, 90), btn.inflate(4, 4), 2)
        shown = self.fit_text(names.get(cur, cur.upper()), 18, btn.w - 36)
        bd.put(s, bd.font(18).render(shown, True, (255, 255, 255)), left=btn.left + 8, cy=btn.centery)
        ax, ay = btn.right - 15, btn.centery
        arrow = [(ax - 5, ay + 3), (ax + 5, ay + 3), (ax, ay - 3)] if self.lang_open else [(ax - 5, ay - 3), (ax + 5, ay - 3), (ax, ay + 3)]
        pygame.draw.polygon(s, (255, 255, 255), arrow)
        hits.insert(0, (btn, ("lang_toggle",)))
        if not self.lang_open:
            return
        pr = pygame.Rect(btn.left, btn.bottom + 2, btn.w, 6 + len(self.langs) * 24)
        pygame.draw.rect(s, (14, 18, 44), pr, border_radius=6)
        pygame.draw.rect(s, (255, 224, 90), pr, 2, border_radius=6)
        pops = []
        for i, (code, name) in enumerate(self.langs):
            cr = pygame.Rect(pr.left + 3, pr.top + 3 + i * 24, pr.w - 6, 22)
            if code == cur:
                pygame.draw.rect(s, (46, 56, 112), cr, border_radius=3)
            elif cr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), cr, border_radius=3)
            bd.put(s, bd.font(18).render(self.fit_text(name, 18, cr.w - 12), True, (255, 255, 255)), left=cr.left + 6, cy=cr.centery)
            pops.append((cr, ("lang", code)))
        hits[0:0] = pops
