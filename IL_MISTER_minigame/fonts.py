"""Bitmap/FON font loading and the shared font bank."""

import json
import os
import re
import unicodedata

import pygame


FONT_ROWS = {"MICRO4.FON": 6, "FLOW.FON": 8} # Glyph row counts used to decode the supported bitmap fonts.
FONT_CODES = {  # Character codes supported by the built-in bitmap fonts.
    "MICRO4.FON": list(range(0x20, 0x60)) + list(range(0x61, 0x7F)),
    "FLOW.FON": [0x20, 0x21, 0x22, 0x24, 0x25, 0x27, 0x28, 0x29] + list(range(0x2A, 0x40)) + list(range(0x41, 0x5F)) + list(range(0x61, 0x7F)),
}
_ACC = {"7e": "\u00b0", "24": "\u20ac", "5b": "\u00ec", "5d": "\u00e9", "7b": "\u00e8", "7c": "\u00f9", "7d": "\u00f2", "2a": "\u00e0"} # Built-in substitutions for glyphs unsupported by the bitmap font.
DEFAULT_CHARMAPS = {"MICRO4.FON": dict(_ACC), "FLOW.FON": dict(_ACC)} # Default character remappings applied to bitmap-font data.
CHARMAP_GAME = "BUNDESLIGA MANAGER PROFESSIONAL" # Game edition whose character map is used for localized text.
CHAR_FALLBACK = {"|": "/", "{": "(", "}": ")", "~": "-", "[": "(", "]": ")", "*": "+", "$": "S", "#": "+", "&": "+", "@": "a", # Fallback substitutions for characters missing from the bitmap font.
                 "_": "-", "`": "'", "\\": "/", "^": "'", "\u00df": "s", "\u00e6": "a", "\u00f8": "o", "\u0153": "o",
                 "\u2019": "'", "\u2018": "'", "\u201c": "\"", "\u201d": "\"", "\u2013": "-", "\u2014": "-", "\u2026": ".",
                 "\u00a0": " ", "\t": " "}


def _read_charmaps(dirs): # Load character-map overrides from the available resource directories.
    for d in dirs:
        p = os.path.join(d, "char-mapping.json") if d else None
        if p and os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    raw = re.sub(r",\s*([}\]])", r"\1", f.read())
                maps = json.loads(raw)[CHARMAP_GAME]["charmaps"]
                return {k: {str(b).lower(): ch for b, ch in v.items()} for k, v in maps.items()}
            except (OSError, ValueError, KeyError):
                continue
    return DEFAULT_CHARMAPS


def parse_fon(path, rows, codes): # Parse a bitmap font file into glyph widths and pixel rows.
    with open(path, "rb") as f:
        d = f.read()
    out, i = {}, 0
    for code in codes:
        if i >= len(d):
            break
        w = d[i]
        bpr = max(1, (w + 7) // 8)
        body = d[i + 1:i + 1 + rows * bpr]
        if len(body) < rows * bpr:
            break
        out[code] = (w, [int.from_bytes(body[r * bpr:(r + 1) * bpr], "big") for r in range(rows)], bpr)
        i += 1 + rows * bpr
    return out


class BitmapFont: # Legacy bitmap-font decoding and text rendering.
    def __init__(self, path, name, charmap): # Load glyph metrics and bitmap data from the parsed font records.
        self.name, self.rows = name, FONT_ROWS[name]
        raw = parse_fon(path, self.rows, FONT_CODES[name])
        self.rev = {ch: int(b, 16) for b, ch in charmap.items()}
        self.remap = {int(b, 16) for b in charmap}
        self.glyphs = {}
        for code, (w, bits, bpr) in raw.items():
            surf = pygame.Surface((max(1, w), self.rows), pygame.SRCALPHA)
            for y, v in enumerate(bits):
                for x in range(w):
                    if (v >> (bpr * 8 - 1 - x)) & 1:
                        surf.set_at((x, y), (255, 255, 255, 255))
            self.glyphs[code] = surf
        self.width = {c: s.get_width() for c, s in self.glyphs.items()}
        self._lut, self._scaled, self._text = {}, {}, {}

    def code(self, ch): # Resolve a character to the glyph code supported by this font.
        c = self._lut.get(ch)
        if c is not None:
            return c
        c = self.rev.get(ch)
        if c is None or c not in self.glyphs:
            o = ord(ch)
            if o < 0x80 and o in self.glyphs and o not in self.remap:
                c = o
            else:
                alt = CHAR_FALLBACK.get(ch)
                if alt is None:
                    base = unicodedata.normalize("NFD", ch)[0]
                    alt = base if base != ch else None
                c = None
                if alt is not None:
                    ao = ord(alt)
                    c = ao if (ao in self.glyphs and ao not in self.remap) else self.rev.get(alt)
                if c is None or c not in self.glyphs:
                    c = 0x3F if 0x3F in self.glyphs else 0x20
        self._lut[ch] = c
        return c

    def _glyph(self, code, scale): # Rasterize a single glyph at the requested scale.
        sc = self._scaled.setdefault(scale, {})
        g = sc.get(code)
        if g is None:
            base = self.glyphs[code]
            g = sc[code] = base if scale == 1 else pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
        return g

    def text_width(self, text, scale=1): # Calculate the text width from glyph metrics and scale.
        return sum(self.width[self.code(ch)] for ch in text) * scale

    def render(self, text, color, scale=1): # Render a string using the legacy bitmap glyph data.
        col = tuple(color[:3]) + (255,)
        key = (text, col, scale)
        im = self._text.get(key)
        if im is None:
            if len(self._text) > 4000:
                self._text.clear()
            im = pygame.Surface((max(1, self.text_width(text, scale)), self.rows * scale), pygame.SRCALPHA)
            x = 0
            for ch in text:
                c = self.code(ch)
                im.blit(self._glyph(c, scale), (x, 0))
                x += self.width[c] * scale
            im.fill(col, special_flags=pygame.BLEND_RGBA_MULT)
            self._text[key] = im
        return im


class ScaledFont: # Scaled wrapper around the legacy bitmap font.
    def __init__(self, font, scale): # Wrap a font with a fixed scale factor.
        self.font, self.scale = font, scale

    def render(self, text, antialias=True, color=(255, 255, 255)): # Render text using the wrapped font and scale factor.
        return self.font.render(text, color, self.scale)

    def size(self, text): # Return the scaled text dimensions.
        return self.font.text_width(text, self.scale), self.font.rows * self.scale

    def get_height(self): # Return the wrapped font height after scaling.
        return self.font.rows * self.scale


class FontBank: # Loading and caching of bitmap and modern fonts.
    SMALL_MAX_PX = 23

    def __init__(self): # Initialize the bitmap-font registry and modern-font cache.
        self.micro = self.flow = None
        self.modern = False
        self._px = {}

    def load(self, dirs): # Load supported bitmap fonts from the resource directories.
        maps = _read_charmaps(dirs)
        for attr, name in (("micro", "MICRO4.FON"), ("flow", "FLOW.FON")):
            for d in dirs:
                p = os.path.join(d, name) if d else None
                if p and os.path.isfile(p):
                    try:
                        setattr(self, attr, BitmapFont(p, name, maps.get(name, DEFAULT_CHARMAPS[name])))
                        break
                    except (OSError, pygame.error):
                        continue
        self._px.clear()
        return self.micro is not None and self.flow is not None

    def small(self, scale=1): # Return a cached compact bitmap font.
        key = ("m", scale)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = ScaledFont(self.micro, scale)
        return f

    def modern_font(self, px): # Create or retrieve a cached system font for the requested size.
        key = ("mod", px)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = pygame.font.SysFont("dejavusans,segoeui,arial,helvetica,liberationsans", int(px))
        return f

    def get(self, px): # Return the configured font for a logical size.
        px = max(8, int(px))
        if self.modern:
            return self.modern_font(max(8, int(px * 0.8)))
        f = self._px.get(px)
        if f is None:
            if px <= self.SMALL_MAX_PX:
                f = ScaledFont(self.micro, max(1, int(round(px * 0.55 / 5.0))))
            else:
                f = ScaledFont(self.flow, max(1, int(round(px * 0.55 / 7.0))))
            self._px[px] = f
        return f


FONTS = FontBank() # Shared font bank used by the HUD, menus, and match messages.
