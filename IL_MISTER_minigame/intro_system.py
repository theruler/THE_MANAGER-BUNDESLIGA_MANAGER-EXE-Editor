"""INTRO dispatcher: MAIN MENU (CAMPIONATO / PARTITA VELOCE / OPZIONI), the OPTIONS page and the persistent options.

Pages (self.menu_page):  "main"   three buttons on PIC\\47.CP
                         "quick"  single match: team / roster selection   -> single_match_system.py
                         "champ"  championship (placeholder)              -> IntroMixin
OPTIONS is an overlay flag (self.options_open) opened from the main menu, drawn on PIC\\22.CP; the joypad mapping opens from it.

Everything is drawn on the virtual surface self.su_surf (SU_W x SU_H) and scaled to the window with su_scale();
self.su_hits holds (rect, tag) pairs in virtual coordinates, consumed by su_click().
"""

import json
import os
import time

import pygame

from fonts import FONTS
from i18n import Note, T, tr
from layout import SU_H, SU_W
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

NOTICE_SECS = 3.0 # Duration of the temporary championship notice on the main menu.
MENU_BTN_W, MENU_BTN_H, MENU_BTN_GAP = 420, 64, 26 # Main-menu buttons.
OPT_WHITE = (255, 255, 255) # Every font of the OPTIONS page is white (22.CP is a dark-ish marble); only warnings keep their orange.
OPT_WARN = (255, 170, 110)
OPT_RULE = (70, 76, 110)


class IntroMixin: # Main menu + OPTIONS and the click / key dispatch of every intro page.

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
        else:
            if k == pygame.K_o:
                self.options_open, self.lang_open = True, False
            elif k == pygame.K_c:
                self.championship_open()
            elif k in (pygame.K_p, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                self.menu_page = "quick"

    def _put(self, txt, px, col, cy, left=None, cx=None, w=None): # Text with the scoreboard font, optionally cut to w pixels.
        bd = self.board
        if w is not None:
            txt = self.fit_text(txt, px, w)
        bd.put(self.su_surf, bd.font(px).render(txt, True, col), left=left, cx=cx, cy=cy)

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
            self.draw_single_match(s, bd, hits, vx, vy)
        elif self.menu_page == "champ":
            s.fill((10, 12, 28))
            self.draw_championship(s, bd, hits, vx, vy)
        else:
            bg = "title"
            s.fill((0, 0, 0, 0))
            self.draw_main_menu(s, bd, hits, vx, vy)
        self.present_su(bg)

    def draw_main_menu(self, s, bd, hits, vx, vy): # Three buttons: CAMPIONATO / PARTITA VELOCE / OPZIONI.
        items = (("menu_champ", tr("menu.championship")),
                 ("menu_quick", tr("menu.quick_match")),
                 ("menu_options", tr("intro.options")))
        total = len(items) * MENU_BTN_H + (len(items) - 1) * MENU_BTN_GAP
        y = SU_H - total - 70
        for tag, label in items:
            r = pygame.Rect((SU_W - MENU_BTN_W) // 2, y, MENU_BTN_W, MENU_BTN_H)
            hov = r.collidepoint(vx, vy)
            panel = pygame.Surface(r.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (8, 14, 40, 205 if hov else 160), panel.get_rect(), border_radius=10)
            s.blit(panel, r)
            pygame.draw.rect(s, (255, 224, 90) if hov else (190, 215, 245), r, 3, border_radius=10)
            self._put(label, 32, (255, 255, 255) if hov else (225, 235, 250), r.centery, cx=r.centerx, w=r.w - 24)
            hits.append((r, (tag,)))
            y += MENU_BTN_H + MENU_BTN_GAP
        notice = getattr(self, "menu_notice", None)
        if notice and time.time() < notice[1]:
            self._put(notice[0], 20, (255, 224, 90), y - MENU_BTN_GAP + 24, cx=SU_W // 2, w=SU_W - 60)

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
    
        self._put(text, 30, (0, 0, 0), r.centery + 2, cx=r.centerx + 2)
        self._put(text, 30, col, r.centery, cx=r.centerx)

    def draw_options(self, s, bd, hits, vx, vy): # OPTIONS page (background 22.cp, marble grey -> dark text).
        W = SU_W
        self._put(tr("intro.options_title"), 46, OPT_WHITE, 40, cx=W // 2)
        back = pygame.Rect(30, 16, 190, 32)
        self.draw_generic_button(s, back, tr("intro.back"), False, back.collidepoint(vx, vy), px=20)
        hits.append((back, ("back",)))
        pygame.draw.line(s, OPT_RULE, (30, 76), (W - 30, 76), 2)
        x_lab, x_chip, y = 60, 450, 120
        rows = 0

        def label(text, yy):
            self._put(text, 22, OPT_WHITE, yy + 14, left=x_lab)

        label(tr("intro.half_len"), y)
        for i, m in enumerate((1, 2, 3, 5)):
            self._num_button(s, hits, vx, vy, x_chip + i * 68, y, str(m), abs(self.half_secs - m * 60.0) < 1, ("half", m * 60.0))
        y += 56
        label(tr("intro.speed"), y)
        self._speed_button(s, hits, vx, vy, x_chip, y)
        y += 56
        ok_orig = bool(self.audio.orig_available) # Greyed out when neither DIGI.VOC nor BM2TITLE.CMF was found at start-up.
        self._put(tr("intro.orig_audio"), 22, OPT_WHITE, y + 14, left=x_lab)
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
        label(tr("intro.replay_secs"), y) # The replay length only matters while the automatic replay is ON: darkened and not clickable otherwise.
        for k_, m in enumerate((3, 5, 8, 10, 15)):
            self._num_button(s, hits, vx, vy, x_chip + k_ * 68, y, str(m), self.replay_secs == m, ("replay_secs", m), self.replay_auto)
        y += 56
        label(tr("intro.font"), y)
        for i, (lab, val) in enumerate(((tr("intro.font_modern"), True), (tr("intro.font_old"), False))):
            r = pygame.Rect(x_chip + i * 150, y, 142, 30)
            self.draw_generic_button(s, r, lab, FONTS.modern == val, r.collidepoint(vx, vy))
            hits.append((r, ("font", val)))
        y += 56
        label(tr("intro.controls"), y)
        for i, (lab, val) in enumerate(((tr("intro.ctrl_home"), 0), (tr("intro.ctrl_away"), 1), (tr("intro.ctrl_spec"), None))):
            r = pygame.Rect(x_chip + i * 168, y, 160, 30)
            self.draw_generic_button(s, r, lab, self.user_team == val, r.collidepoint(vx, vy), px=16)
            hits.append((r, ("ctrl", val)))
        y += 56
        label(tr("intro.joymap"), y)
        jb = pygame.Rect(x_chip, y, 240, 32)
        self.draw_generic_button(s, jb, tr("intro.joymap"), False, jb.collidepoint(vx, vy), px=20)
        hits.append((jb, ("joymap",)))
        note = " | ".join(n.text() for n in self.notes[:2]) if self.notes else "" # Notes / warnings moved here from the old INTRO.
        if note:
            self._put(note, 15, OPT_WARN if any(n.warn for n in self.notes) else OPT_WHITE, SU_H - 18, cx=W // 2, w=W - 60)
        self.draw_lang_dropdown(s, bd, hits, vx, vy) # Language selector (top right, as before); its pop-up goes in front of the hits.

    # ---------- championship placeholder ----------
    def championship_open(self): # Called by the CAMPIONATO button.
        self.menu_notice = (tr("menu.championship_soon"), time.time() + NOTICE_SECS)
    def championship_click(self, hit, button=1): # Tags of future championship screens. Returns True when handled.
        return False
    def championship_key(self, k): # Keyboard of future championship screens.
        pass
    def draw_championship(self, s, bd, hits, vx, vy): # Future championship screen.
        pass
