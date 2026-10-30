import math
import os
import pygame


def _hex_palette(s, scale=1): # Decode a hexadecimal RGB palette and optionally scale its channel values.
    return [
        (min(255, int(s[i:i + 2], 16) * scale),
         min(255, int(s[i + 2:i + 4], 16) * scale),
         min(255, int(s[i + 4:i + 6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]


PAL_DEFAULT = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4) # Fallback RGB palette used when an asset does not provide its own palette.
_ALPHA_LUT = bytes([0] + [255] * 255)

CELL_W, CELL_H = 12, 11 # Sprite-sheet cell width/height in source pixels.
SHEET_COLS = 24 # Number of sprite cells per row in the source sheet.
GOAL_Y0, GOAL_Y1 = 18, 28 # Upper/Lower source-image row of the goal opening.
GOAL_FRONT_X = (23, 296) # Left and right source-image x coordinates of the goal front.
BOARD_GOAL_L = (158, 82, 185, 101) # Source rectangle containing the left scoreboard goal display.
BOARD_GOAL_R = (188, 82, 215, 101) # Source rectangle containing the right scoreboard goal display.
BOARD_CLOCK = (141, 85, 153, 97) # Source rectangle containing the scoreboard clock.
BOARD_ROSTER_ICON = (223, 84, 238, 99) # Source rectangle containing the roster toggle icon.
GOAL_SCROLL_STEP = 2 # Pixel step used when scrolling the animated goal display.
GOAL_SCROLL_INTERVAL = 0.05 # Seconds between goal-display scroll steps.
CROWD_FRAMES = 8 # Number of animation frames available for the crowd.

def decode_vga(path): # Decode a VGA image file into its dimensions and indexed pixel data.
    try:
        with open(path, "rb") as f:
            data = f.read()
        header_len = 6
        if len(data) < header_len:
            return None
        width = data[0] | (data[1] << 8)
        height = data[2] | (data[3] << 8)
        payload_len = data[4] | (data[5] << 8)
        if width <= 0 or height <= 0 or width > 1280 or height > 960:
            return None
        payload_end = header_len + payload_len - 1
        if payload_end < header_len or payload_end >= len(data):
            return None
        offset = data[payload_end] - 1
        if offset < 1:
            return None
        pixels = bytearray()
        i = header_len
        target = width * height
        while i < payload_end and len(pixels) < target:
            b = data[i]
            if b > offset + 1:
                if i + 1 >= payload_end:
                    return None
                pixels.extend((data[i + 1],) * (b - offset))
                i += 2
            elif b == offset + 1:
                i += 1
            else:
                count = b + 1
                if i + count >= payload_end:
                    return None
                pixels.extend(data[i + 1:i + 1 + count])
                i += count + 1
        if len(pixels) != target:
            return None
        return width, height, bytes(pixels)
    except (OSError, ValueError, IndexError):
        return None

def vga_surface(img, palette, transparent0): # Convert indexed VGA pixels into a Pygame surface using the supplied palette.
    w, h, pix = img
    pal = list(palette) + [(0, 0, 0)] * (256 - len(palette))
    out = bytearray(w * h * 4)
    out[0::4] = pix.translate(bytes(c[0] for c in pal[:256]))
    out[1::4] = pix.translate(bytes(c[1] for c in pal[:256]))
    out[2::4] = pix.translate(bytes(c[2] for c in pal[:256]))
    out[3::4] = pix.translate(_ALPHA_LUT) if transparent0 else b"\xff" * (w * h)
    return pygame.image.frombuffer(bytes(out), (w, h), "RGBA").convert_alpha()

def find_file(folder, stem): # Find a VGA asset by case-insensitive filename stem inside a folder.
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            if fn.lower() == stem.lower() + ".vga":
                return os.path.join(folder, fn)
    return None

class LoMetrics: # Text measurement adapter for the legacy bitmap font.
    def __init__(self, font, ps): # Store the font and pixel scale used by the text metrics adapter.
        self.font, self.ps = font, ps

    def size(self, text): # Measure text and return its width and fixed line height in logical units.
        return self.font.size(text)[0] / float(self.ps), 6

class Graphics: # VGA assets, field graphics, sprites, and crowd animation resources.
    def __init__(self, pic_dir, field_path, board_path, sheet_path, field_size, field_x0, y_offset, translate): # Load field, sprite sheet, scoreboard, and crowd assets.
        self.pic_dir = pic_dir
        self.translate = translate
        self.field_x0 = field_x0
        self.y_offset = y_offset
        fw, fh = field_size
        self.board_path = board_path
        img = decode_vga(sheet_path)
        if img is None:
            raise OSError(self.translate("err.gfx_unreadable", path=sheet_path))
        self.sheet = vga_surface(img, PAL_DEFAULT, True)
        try:
            field = pygame.image.load(field_path).convert()
        except pygame.error as ex:
            raise OSError(self.translate("err.gfx_unreadable_ex", path=field_path, reason=ex))
        if field.get_size() != (fw, fh):
            field = pygame.transform.smoothscale(field, (fw, fh))
        self.field = field
        self._cache = {}
        self._logos = {}
        try:
            raw = pygame.image.load(board_path).convert_alpha()

            def crop(box): # Crop a rectangular region from the supplied image or pixel buffer.
                return raw.subsurface(pygame.Rect(box[0], box[1], box[2] - box[0] + 1, box[3] - box[1] + 1)).copy()
            gl, gr = crop(BOARD_GOAL_L), crop(BOARD_GOAL_R)
            self.clock_icon = crop(BOARD_CLOCK)
            ri = crop(BOARD_ROSTER_ICON)
            self.roster_icon = ri.subsurface(ri.get_bounding_rect()).copy()
        except (ValueError, pygame.error) as ex:
            raise OSError(self.translate("err.board_area", reason=ex))
        gy = GOAL_Y1 + self.y_offset + 10 + 1
        self.goals = ((gl, (GOAL_FRONT_X[0] + self.field_x0 - gl.get_width(), gy - gl.get_height())),
                      (gr, (GOAL_FRONT_X[1] + self.field_x0, gy - gr.get_height())))
        self.shadow_top = self.sprite(145).get_bounding_rect().top
        self.crowd = self._build_crowd()

    def _build_crowd(self): # Create the crowd animation frames from the loaded sprite sheet.
        rect = pygame.Rect(0, 0, min(480, self.field.get_width()), min(33, self.field.get_height()))
        tob = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
        fromb = getattr(pygame.image, "frombytes", None) or pygame.image.fromstring
        raw = tob(self.field.subsurface(rect).copy(), "RGB")
        px = [raw[i:i + 3] for i in range(0, len(raw), 3)]
        uniq = sorted(set(px), key=lambda c: 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2])
        n = len(uniq)
        reach = max(1, min(2, n // 100))
        frames = []
        for f in range(CROWD_FRAMES):
            mp = {}
            for r, c in enumerate(uniq):
                sh = int(round(reach * math.sin(2.0 * math.pi * (f / CROWD_FRAMES + (r * 0.61803) % 1.0))))
                mp[c] = uniq[max(0, min(n - 1, r + sh))]
            frames.append(fromb(b"".join(mp[c] for c in px), rect.size, "RGB").convert())
        return frames

    def crowd_frame(self): # Return the crowd frame selected by the current animation state.
        return self.crowd[(pygame.time.get_ticks() // 280) % len(self.crowd)]


    def sprite(self, sid): # Return a sprite surface for the requested sprite ID.
        s = self._cache.get(sid)
        if s is None:
            col, row = sid % SHEET_COLS, sid // SHEET_COLS
            x0, w = col * CELL_W, CELL_W
            if sid >= 142:
                x0, w = x0 + 4, 4
            s = self._cache[sid] = self.sheet.subsurface(pygame.Rect(x0, row * CELL_H, w, CELL_H)).copy()
        return s

    def logo(self, logo_id): # Return the logo image mapped to a team logo ID.
        if logo_id in self._logos:
            return self._logos[logo_id]
        surf = None
        if logo_id is not None and logo_id >= 0:
            for stem in (str(logo_id), "%02d" % logo_id, "%03d" % logo_id):
                p = find_file(self.pic_dir, stem)
                img = decode_vga(p) if p else None
                if img:
                    surf = vga_surface(img, PAL_DEFAULT, False)
                    break
        self._logos[logo_id] = surf
        return surf

BOARD_W, BOARD_H, BOARD_SRC = 320, 81, (320, 112) # BOARD_W: rendered width; BOARD_H: rendered height; BOARD_SRC: source dimensions.
DIGIT_W, DIGIT_H, DIGIT_Y, DIGIT_PITCH = 11, 15, 84, 14 # DIGIT_W: digit width; DIGIT_H: height; DIGIT_Y: source y; DIGIT_PITCH: spacing.
BOARD_LOGO, LOGO_SZ = ((104, 35), (183, 35)), 38 # BOARD_LOGO: logo positions; LOGO_SZ: crop size.
NAME_Y, NAME_MAXW, GOAL_Y = 8, 52, 16 # NAME_Y: team-name y; NAME_MAXW: max name width; GOAL_Y: score y.
INFO_X, INFO_Y0, INFO_DY = (149, 172), 35, 8 # INFO_X: column x positions; INFO_Y0: first row y; INFO_DY: row spacing.
ROSTER_X, ROSTER_W, ROSTER_HDR_Y, ROSTER_Y0, ROSTER_DY = (4, 229), 88, 3, 13, 6 # ROSTER_X: column x; ROSTER_W: column width; ROSTER_HDR_Y: header y; ROSTER_Y0: first row y; ROSTER_DY: row spacing.
ROSTER_BALL_PX = 8 # Horizontal offset of the ball marker in a roster row.
ROSTER_BALL_CY = 2 # Vertical offset of the ball marker relative to a roster row.
BAR_DH = 58 # Height of the bottom status bar in virtual pixels.
SB_DW = 1040 # Virtual width used by scoreboard scaling calculations.

class Scoreboard: # Scoreboard, team roster, and match-information rendering.
    BG, FRAME = (13, 17, 38), (72, 82, 138)
    LIT, WHITE, DIM = (154, 164, 228), (228, 232, 252), (104, 112, 160)

    def __init__(self, board_path, fonts, role_tag, team_col, team_names, translate): # Initialize scoreboard, fonts, role labels, colors, and team names.
        self.fonts = fonts
        self.role_tag = role_tag
        self.team_col = team_col
        self.team_names = team_names
        self.translate = translate
        self.hit_rows, self.hit_form = [], []
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.lo = pygame.Surface((BOARD_W, BOARD_H))
        self._logo = {}
        self._fit_cache = {}
        self._roster_icon_cache = {}
        self._clock_icon_cache = {}
        self._scaled_board_cache = {}
        self.base, self.digits, self.goal_letters = self._load_board(board_path, translate)
        self.gfx_icon = None


    def font(self, px): # Get a cached font for the requested pixel size.
        return self.fonts.get(px)

    def fit(self, text, font, maxw): # Fit scoreboard text within the supplied width.
        base_font = getattr(font, "font", font)
        font_scale = getattr(font, "ps", getattr(font, "scale", 1))
        key = (text, int(maxw), id(base_font), int(font_scale))
        cached = self._fit_cache.get(key)
        if cached is not None:
            return cached
        if font.size(text)[0] <= maxw:
            result = text
        else:
            while text and font.size(text + "...")[0] > maxw:
                text = text[:-1]
            result = text + "..."
        if len(self._fit_cache) > 2048:
            self._fit_cache.clear()
        self._fit_cache[key] = result
        return result

    @staticmethod
    def put(surf, img, cx=None, cy=None, left=None, top=None): # Place a scoreboard image using centre or top-left coordinates.
        r = img.get_rect()
        if cx is not None:
            r.centerx = int(cx)
        if cy is not None:
            r.centery = int(cy)
        if left is not None:
            r.left = int(left)
        if top is not None:
            r.top = int(top)
        surf.blit(img, r)


    @staticmethod
    def _load_board(path, translate): # Load the scoreboard source image and prepare its drawing surface.
        try:
            img = pygame.image.load(path).convert_alpha()
        except pygame.error as ex:
            raise OSError(translate("err.gfx_unreadable_ex", path=path, reason=ex))
        if img.get_size() != BOARD_SRC:
            img = pygame.transform.smoothscale(img, BOARD_SRC)
        base = img.subsurface(pygame.Rect(0, 0, BOARD_W, BOARD_H)).copy()
        digs = [img.subsurface(pygame.Rect(i * DIGIT_PITCH, DIGIT_Y, DIGIT_W, DIGIT_H)).copy() for i in range(10)]
        goal_letters = [img.subsurface(pygame.Rect(243 + i * DIGIT_PITCH, 84, DIGIT_W, DIGIT_H)).copy()
                        for i in range(4)]
        return base, digs, goal_letters

    def _logo_img(self, g, t): # Resolve the correct logo image for the supplied team.
        td = g.team_data[t]
        key = (t, td["logo"], td["name"])
        if key in self._logo:
            return self._logo[key]
        img = g.gfx.logo(td["logo"])
        im = None
        if img is not None:
            iw, ih = img.get_size()
            k = min(LOGO_SZ / float(iw), LOGO_SZ / float(ih))
            im = pygame.transform.smoothscale(img, (max(1, int(iw * k)), max(1, int(ih * k))))
        if len(self._logo) > 64:
            self._logo.clear()
        self._logo[key] = im
        return im


    def text_at(self, lo, f, text, color, x, y, cx=None): # Render aligned text on the scoreboard surface.
        if self.fonts.modern:
            self.defer.append((text, tuple(color[:3]), x, y, cx))
            return
        im = f.render(text, True, color)
        lo.blit(im, ((cx - im.get_width() // 2) if cx is not None else x, y))

    def draw(self, surf, g, W, H): # Draw the scoreboard with current score, time, team, and roster information.

        pixel_scale = max(
            1,
            min(int(W // BOARD_W), int(H // BOARD_H))
        )

        draw_w = BOARD_W * pixel_scale
        draw_h = BOARD_H * pixel_scale


        off_x = int((W - draw_w) // 2)
        off_y = int((H - draw_h) // 2)
        lo = self.lo
        self.ps = pixel_scale
        self.defer = []
        f = LoMetrics(self.fonts.modern_font(self.modern_px(pixel_scale)), pixel_scale) if self.fonts.modern else self.fonts.small(1)
        self._f = f
        lo.fill(self.BG)
        for t in (0, 1):
            x, y = BOARD_LOGO[t]
            lo.fill((8, 10, 24), (x, y, LOGO_SZ, LOGO_SZ))
            im = self._logo_img(g, t)
            if im is not None:
                lo.blit(im, im.get_rect(center=(x + LOGO_SZ // 2, y + LOGO_SZ // 2)))
        lo.blit(self.base, (0, 0))
        mp = pygame.mouse.get_pos()
        mx = (mp[0] - off_x) / pixel_scale
        my = (mp[1] - off_y) / pixel_scale
        for t in (0, 1):
            cx = BOARD_LOGO[t][0] + LOGO_SZ // 2
            name = self.fit(self.team_names[t].upper(), f, NAME_MAXW)
            self.text_at(lo, f, name, self.LIT, 0, NAME_Y, cx=cx)
            score_rect = pygame.Rect(98 if t == 0 else 178, GOAL_Y, 49, DIGIT_H)
            ticker = (g.mode == "goal" and g.goal and g.goal.get("team") == t
                      and g.goal.get("t", 999.0) < ((score_rect.w + 7 * (DIGIT_W + 3)) / GOAL_SCROLL_STEP) * GOAL_SCROLL_INTERVAL)
            if ticker:
                letters = self.goal_letters
                glyphs = [letters[0], letters[1], letters[1], letters[1], letters[1], letters[2], letters[3]]
                step_w = DIGIT_W + 3
                progress = int(g.goal["t"] / GOAL_SCROLL_INTERVAL) * GOAL_SCROLL_STEP
                x = ((score_rect.right + 1) & ~1) - progress
                old_clip = lo.get_clip()
                lo.set_clip(score_rect)
                for glyph in glyphs:
                    lo.blit(glyph, (x, GOAL_Y))
                    x += step_w
                lo.set_clip(old_clip)
            else:
                sc = min(g.score[t], 99)
                digs = [sc // 10, sc % 10] if sc >= 10 else [sc]
                x = cx - (len(digs) * DIGIT_W + len(digs) - 1) // 2
                if t == 1:
                    x -= 1
                for d in digs:
                    lo.blit(self.digits[d], (x, GOAL_Y))
                    x += DIGIT_W + 1
        st = g.stats
        on = [sum(1 for p in g.team_p[t] if p.state != "out") for t in (0, 1)]
        rows = (st["yellow"], st["red"], st.get("injured", [0, 0]), on, st["shots"])
        for i, vals in enumerate(rows):
            y = INFO_Y0 + i * INFO_DY
            for t in (0, 1):
                txt = str(vals[t])
                dx = -3 if len(txt) >= 2 else 0
                self.text_at(lo, f, txt, self.LIT, INFO_X[t] + dx, y)
        rows_hit, form_hit = [], []
        for t in (0, 1):
            self.draw_roster(lo, g, t, mx, my, rows_hit, form_hit)
        board_size = (draw_w, draw_h)
        scaled_board = self._scaled_board_cache.get(board_size)
        if scaled_board is None:
            scaled_board = pygame.Surface(board_size)
            self._scaled_board_cache[board_size] = scaled_board
        pygame.transform.scale(lo, board_size, scaled_board)
        surf.blit(scaled_board, (off_x, off_y))
        if self.defer:
            mf = self.fonts.modern_font(self.modern_px(pixel_scale))
            for text, col, x, y, cx in self.defer:
                im = mf.render(text, True, col)
                px_ = cx * pixel_scale - im.get_width() // 2 if cx is not None else x * pixel_scale
                surf.blit(im, (off_x + int(px_), off_y + int((y + 3) * pixel_scale) - im.get_height() // 2))
        self.rect = pygame.Rect(off_x, off_y, draw_w, draw_h)


        up = lambda r: pygame.Rect(
            off_x + r.x * pixel_scale,
            off_y + r.y * pixel_scale,
            r.w * pixel_scale,
            r.h * pixel_scale
        )
        self.hit_rows = [(up(r), p) for r, p in rows_hit]
        self.hit_form = [(up(r), t, d) for r, t, d in form_hit]

    @staticmethod
    def modern_px(ps): # Scale a logical font size for the modern font renderer.
        return max(8, int(round(6.5 * ps)))

    def draw_roster(self, lo, g, t, mx, my, rows_hit, form_hit): # Draw both roster columns and register their interactive hit regions.
        f = self._f
        x0, w, col = ROSTER_X[t], ROSTER_W, self.team_col[t]
        hy = ROSTER_HDR_Y
        self.text_at(lo, f, g.form_names[t], self.WHITE, 0, hy, cx=x0 + w // 2)
        for dx, delta, ch in ((0, -1, "<"), (w - 8, 1, ">")):
            r = pygame.Rect(x0 + dx - 1, hy - 2, 10, 9)
            self.text_at(lo, f, ch, (255, 224, 90) if r.collidepoint(mx, my) else self.LIT, r.x + 2, hy)
            form_hit.append((r, t, delta))
        form_hit.append((pygame.Rect(x0 + 10, hy - 2, w - 20, 9), t, 1))
        pygame.draw.line(lo, col, (x0, ROSTER_Y0 - 3), (x0 + w - 1, ROSTER_Y0 - 3))
        for i, p in enumerate(g.team_p[t]):
            y = ROSTER_Y0 + ROSTER_DY * i
            r = pygame.Rect(x0 - 1, y - 1, w + 2, ROSTER_DY)
            out = p.state == "out" or p.red
            sel = g.cp is p
            if sel:
                lo.fill((96, 82, 20), r)
                lo.fill((255, 215, 0), (r.x, r.y, 1, r.h))
            elif r.collidepoint(mx, my) and not out:
                lo.fill((36, 44, 92), r)
            text_y = y - 1
            self.text_at(lo, f, str(p.num), tuple(v // 2 for v in col) if out else col, x0 + (4 if 1 <= p.num <= 9 else 1), text_y)
            right = x0 + w - 1
            fs = None if out else g.fatigue_sign(t, p.sq) if hasattr(g, "fatigue_sign") else None
            if fs == "down" or (fs == "up" and int(getattr(g, "t_all", 0.0) * 2.5) % 2 == 0): # Fatigue arrow: red down = tired, green up = recovering (blinks).
                fc = (232, 62, 62) if fs == "down" else (70, 212, 96)
                head, stem = ((y, y + 1, y + 2), (y + 3, y + 4)) if fs == "up" else ((y + 2, y + 3, y + 4), (y, y + 1))
                for k, hy_ in enumerate(head if fs == "up" else head[::-1]): # Arrow head: 1, 3, 5 px wide towards its base.
                    n = 1 + 2 * k
                    lo.fill(fc, (right - 2 - k, hy_, n, 1))
                for sy in stem:
                    lo.fill(fc, (right - 2, sy, 1, 1))
            if fs:
                right -= 7
            if p.red or p.yellow:
                lo.fill((230, 30, 30) if p.red else (240, 240, 0), (right - 1, y, 2, 4))
                right -= 4
            if p.injured and not out:
                lo.fill((235, 25, 25), (right - 4, y + 2, 5, 1))
                lo.fill((235, 25, 25), (right - 2, y, 1, 5))
                right -= 7
            if any(e["out"] is p for e in g.sub_q[t]):
                for j in range(3):
                    lo.fill((255, 150, 40), (right - 4 + j, y + j, 5 - 2 * j, 1))
                right -= 6
            if g.ball.owner is p:
                icon = self.roster_ball()
                lo.blit(icon, (right - icon.get_width() + 1, y + ROSTER_BALL_CY - icon.get_height() // 2))
                right -= icon.get_width() + 2
            c = (110, 70, 80) if p.red else (96, 100, 130) if out else (255, 236, 150) if sel else self.LIT
            nx = x0 + 16
            role = self.role_tag.get(g.natural_role(p.sq), "")
            if role:
                self.text_at(lo, f, role, c, nx, text_y)
                nx += 18
            self.text_at(lo, f, self.fit(p.name, f, max(0, right - nx)), c, nx, text_y)
            if out:
                pygame.draw.line(lo, c, (nx, y + 2), (right - 1, y + 2))
            rows_hit.append((r, p))

    def roster_ball(self): # Return the ball marker used to identify the player in possession.
        icon = self._roster_icon_cache.get(ROSTER_BALL_PX)
        if icon is None:
            src = self.gfx_icon
            h = ROSTER_BALL_PX
            w = max(2, int(round(src.get_width() * h / float(max(1, src.get_height())))))
            icon = pygame.transform.smoothscale(src, (w, h))
            self._roster_icon_cache[ROSTER_BALL_PX] = icon
        return icon

    def click(self, pos, g): # Handle scoreboard and roster clicks and update the corresponding game state.
        for r, t, delta in self.hit_form:
            if r.collidepoint(pos):
                g.change_formation(t, delta)
                return True
        for r, p in self.hit_rows:
            if r.collidepoint(pos):
                g.pick_player(p)
                return True
        return self.rect.collidepoint(pos)

    def draw_bar(self, surf, g, y, W, H): # Render the lower bar with current status and informational text.
        s = g.bs
        S = lambda v: max(1, int(round(v * s)))
        pygame.draw.rect(surf, (6, 6, 12), (0, y, W, H))
        cy = y + H // 2
        label = g.minute_label()
        f = self.fonts.get(S(36))
        txt = f.render(label, True, (206, 212, 246))
        shadow = f.render(label, True, (40, 44, 86))
        gap = S(14)
        gi = S(8)
        ci = g.gfx.clock_icon
        icon_h = max(1, int(round(txt.get_height() * 1.08)))
        icon_w = max(1, int(round(ci.get_width() * icon_h / float(max(1, ci.get_height())))))
        clock_key = (icon_w, icon_h)
        icon = self._clock_icon_cache.get(clock_key)
        if icon is None:
            icon = pygame.transform.scale(ci, clock_key)
            self._clock_icon_cache[clock_key] = icon
        iw = icon.get_width()
        total = iw + gi + txt.get_width() + gi + iw
        x0 = (W - total) // 2
        left = x0 + iw + gi
        surf.blit(icon, icon.get_rect(midleft=(x0, cy)))
        surf.blit(icon, icon.get_rect(midright=(x0 + total, cy)))
        surf.blit(shadow, shadow.get_rect(midleft=(left + 2, cy + 2)))
        surf.blit(txt, txt.get_rect(midleft=(left, cy)))
        m = S(34)
        bh = S(15)
        lb = pygame.Rect(m, cy - bh // 2, x0 - gap - m, bh)
        rb = pygame.Rect(x0 + total + gap, cy - bh // 2, W - m - (x0 + total + gap), bh)
        h1 = min(1.0, g.real_t / g.half_secs) if g.half == 1 else 1.0
        h2 = (min(1.0, g.real_t / g.half_secs) if g.half == 2 else 0.0)
        for rect, frac, from_left in ((lb, h1, True), (rb, h2, False)):
            pygame.draw.rect(surf, (24, 28, 58), rect, border_radius=S(3))
            w = int((rect.w - 4) * frac)
            if w > 0:
                fr = pygame.Rect(rect.left + 2, rect.top + 2, w, rect.h - 4)
                if not from_left:
                    fr.right = rect.right - 2
                pygame.draw.rect(surf, (98, 110, 186), fr, border_radius=S(2))
                pygame.draw.rect(surf, (236, 224, 70), (fr.left, fr.top + max(1, fr.h // 5), fr.w, max(2, fr.h // 4)))
            pygame.draw.rect(surf, (96, 106, 170), rect, max(2, S(2)), border_radius=S(3))
        sf = self.fonts.get(S(20))
        for rect, tx_ in ((lb, self.translate("hud.half_1")), (rb, self.translate("hud.half_2"))):
            t = sf.render(tx_, True, (120, 130, 186))
            surf.blit(t, t.get_rect(midtop=(rect.centerx, rect.bottom + 2)))

