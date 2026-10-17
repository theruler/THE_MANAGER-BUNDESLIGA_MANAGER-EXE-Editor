import argparse
import array
import bisect
import collections
import json
import math
import os
import random
import re
import struct
import sys
import threading
import time
import unicodedata
import wave
import pygame
import i18n

T = i18n.Translator(prefix="mister_lang_")
tr = T.tr


class Note:

    def __init__(self, key, warn=False, **kw):
        self.key, self.warn, self.kw = key, warn, kw

    def text(self):
        return tr(self.key, **self.kw)


def init_language(code):
    for c in (code, "it", "en"):
        if c and T.set_language(c):
            return c
    return T.current_language()


CELL_W, CELL_H = 12, 11
SHEET_COLS = 24
Y_OFFSET = 35
ORIG_FW, ORIG_FH = 320, 112
ORIG_WIN_W, ORIG_WIN_H = 182, 96
ORIG_SCROLL_MAX_X, ORIG_SCROLL_MAX_Y = 137, 15
GEOMETRY = "originale" if any(a in ("--geometria-originale", "--original-geometry") for a in sys.argv) else "estesa"
if GEOMETRY == "originale":
    FIELD_X0 = 0
    FW, FH = ORIG_FW, ORIG_FH
    RUNOFF_Y = 0
    WIN_W, WIN_H = ORIG_WIN_W, ORIG_WIN_H
else:
    FIELD_X0 = 79
    FW, FH = 480, 124
    RUNOFF_Y = 6
    WIN_W, WIN_H = 204, 80
SCROLL_MAX_X, SCROLL_MAX_Y = FW - WIN_W, FH - WIN_H
MAX_Y = 66
BALL_Y_MIN = -Y_OFFSET


def _hex_palette(s, scale=1):
    return [
        (min(255, int(s[i:i + 2], 16) * scale),
         min(255, int(s[i + 2:i + 4], 16) * scale),
         min(255, int(s[i + 4:i + 6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]


PAL_DEFAULT = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4)
_ALPHA_LUT = bytes([0] + [255] * 255)


PAN_DEAD_PX = 10
PAN_HYSTERESIS_MS = 2000
CAM_GLIDE_SECS = 0.6
PERSP_LINES = [(10, 61.0, 258.0), (43, -5.0, 324.0), (76, -71.0, 390.0)]
PERSP_Y_REF = 39
PERSP_Y_LAST = 76
PERSP_Y_SHIFT = PERSP_Y_LAST - MAX_Y


def _edge_model(pts):
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)

    def f(y):
        if y <= pts[0][0]:
            return pts[0][1] + slope * (y - pts[0][0])
        if y >= pts[-1][0]:
            return pts[-1][1] + slope * (y - pts[-1][0])
        for i in range(1, n):
            if y <= pts[i][0]:
                (y0, x0), (y1, x1) = pts[i - 1], pts[i]
                return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return f


_edge_l = _edge_model([(y, x0) for y, x0, _x1 in PERSP_LINES])
_edge_r = _edge_model([(y, x1) for y, _x0, x1 in PERSP_LINES])


def persp_edges(y):
    return _edge_l(y), _edge_r(y)


def persp_width(y):
    left, right = persp_edges(y)
    return max(20.0, right - left)


_PERSP_WREF = persp_width(PERSP_Y_REF)
_PV_Y0, _PV_STEP, _PV_N = -20.0, 0.5, 321


def _build_pv():
    v = [0.0]
    for i in range(1, _PV_N):
        y0 = _PV_Y0 + (i - 1) * _PV_STEP
        v.append(v[-1] + _PERSP_WREF * _PV_STEP * 0.5 * (1.0 / persp_width(y0) + 1.0 / persp_width(y0 + _PV_STEP)))
    return v


_PV = _build_pv()


def _persp_v(y):
    t = (min(max(y, _PV_Y0), _PV_Y0 + _PV_STEP * (_PV_N - 1)) - _PV_Y0) / _PV_STEP
    i = min(int(t), _PV_N - 2)
    return _PV[i] + (_PV[i + 1] - _PV[i]) * (t - i)


def _persp_y(v):
    i = min(max(bisect.bisect_right(_PV, v) - 1, 0), _PV_N - 2)
    return _PV_Y0 + (i + (v - _PV[i]) / (_PV[i + 1] - _PV[i])) * _PV_STEP


def persp_to_world(x, y):
    y += PERSP_Y_SHIFT
    x -= FIELD_X0
    left, right = persp_edges(y)
    return (x - left) / max(20.0, right - left) * _PERSP_WREF, _persp_v(y)


def persp_from_world(wx, wv):
    y = _persp_y(wv) - PERSP_Y_SHIFT
    left, right = persp_edges(y + PERSP_Y_SHIFT)
    return FIELD_X0 + left + wx / _PERSP_WREF * max(20.0, right - left), y


w2s = persp_from_world
s2w = persp_to_world

PITCH_TOP_Y, PITCH_BOT_Y = 0, 66
GOAL_Y0, GOAL_Y1 = 18, 28
GOAL_D = 9.0
GOAL_FRONT_X = (23, 296)
BOARD_GOAL_L = (158, 82, 185, 101)
BOARD_GOAL_R = (188, 82, 215, 101)
BOARD_CLOCK = (141, 85, 153, 97)
BOARD_ROSTER_ICON = (223, 84, 238, 99)
GOAL_SCROLL_STEP = 2
GOAL_SCROLL_INTERVAL = 0.05
CROWD_FRAMES = 8
GOAL_NET_H = 9.0
GATE_PX = 40.0
DEPTH_EXP = 0.5
BALL_DEPTH_K = 0.4


def depth_slow(dx, dv):
    n = math.hypot(dx, dv)
    if n < 1e-9:
        return 1.0
    return n / math.hypot(dx, dv / BALL_DEPTH_K)
GOAL_H = 11.0
POST_T = 1.2
BAR_LO, BAR_HI = 1.0, 1.2

L = _PERSP_WREF


def _vg(gy):
    return persp_to_world(FW / 2.0, gy)[1]


V_TOP, V_BOT = _vg(PITCH_TOP_Y), _vg(PITCH_BOT_Y)
V_MID = (V_TOP + V_BOT) / 2.0
SPOT_Y = 27.5
V_GC = (_vg(GOAL_Y0) + _vg(GOAL_Y1)) / 2.0
V_SPOT = _vg(SPOT_Y)
HALF_MOUTH = (_vg(GOAL_Y1) - _vg(GOAL_Y0)) / 2.0
V_MIN_P, V_MAX_P = V_TOP, _vg(MAX_Y + RUNOFF_Y)
PITCH_W = V_BOT - V_TOP

BOX_Y0, BOX_Y1 = 10, 46
GA_Y0, GA_Y1 = 18, 29
PEN_Y = 25
BOX_V0, BOX_V1 = _vg(BOX_Y0), _vg(BOX_Y1)
GA_V0, GA_V1 = _vg(GA_Y0), _vg(GA_Y1)
V_PEN = _vg(PEN_Y)
BOX_D = 0.157 * L
GA_D = 0.052 * L
PEN_D = 0.108 * L


def in_box_fn(x, v, own_gx):
    return abs(x - own_gx) < BOX_D and BOX_V0 <= v <= BOX_V1


GATE_K = _PERSP_WREF / persp_width(PERSP_Y_LAST)
GATE_HALF = GATE_PX / 2.0 * GATE_K
GATE_SPREAD = GATE_HALF - 6.0 * GATE_K


_DK = {}


def depth_k(v):
    key = int(round(v * 2.0))
    k = _DK.get(key)
    if k is None:
        k = _DK[key] = (_PERSP_WREF / persp_width(_persp_y(key / 2.0))) ** DEPTH_EXP
    return k


G = 150.0
PLAYER_SPEED = 52.0
DRIBBLE_OFF = 6.0
REACH_FIRST = 15.0
HUD_H = 76
SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
SPEED_DEFAULT = 3
SPEED_UNIT = 0.5
IDLE_AI = 2.5

DEFAULT_ACTIONS = {
    "order": ["kick", "dive", "header", "bicycle", "fall", "slide", "moonwalk", "cele"],
    "actions": {
        "kick": {"label": "Power Kick", "E": [1, 10, 11], "W": [49, 48, 47]},
        "dive": {"label": "Dive", "E": [12, 13, 14, 14, 14, 14], "W": [46, 45, 44, 44, 44, 44]},
        "header": {"label": "Header", "E": [16, 17, 18, 19, 20], "W": [42, 41, 40, 39, 38]},
        "bicycle": {"label": "Bicycle kick", "E": [18, 26, 12, 22, 23, 23, 24, 24], "W": [26, 36, 46, 35, 35, 34, 34]},
        "fall": {"label": "Collision fall", "E": [12, 13, 14, 14, 14], "W": [46, 45, 44, 44, 44]},
        "slide": {"label": "Sliding kick", "E": [36, 11, 11, 45, 34, 34, 34], "W": [22, 47, 47, 13, 24, 24, 24]},
        "moonwalk": {"label": "Moonwalk", "E": [55, 54, 55, 53], "W": [3, 4, 3, 5], "travel": True},
        "cele": {"label": "Celebration", "E": [25, 26, 27, 26, 27, 26, 27], "W": [25, 26, 27, 26, 27, 26, 27], "single": True},
    },
    "moves": {"E": [3, 4, 3, 5], "NE": [0, 1, 0, 2], "N": [28, 29, 28, 30], "NW": [58, 57, 58, 56],
              "W": [55, 54, 55, 53], "SW": [52, 51, 52, 50], "S": [31, 32, 31, 33], "SE": [6, 7, 6, 8]},
    "stand": {"E": 3, "NE": 0, "N": 28, "NW": 58, "W": 55, "SW": 52, "S": 31, "SE": 6},
    "referee": {
        "move": {"E": [121, 122, 121, 123], "NE": [118, 119, 118, 120], "N": [126, 127, 126, 128],
                 "NW": [139, 138, 139, 137], "W": [136, 135, 136, 134], "SW": [133, 132, 133, 134],
                 "S": [129, 130, 129, 131], "SE": [124, 125, 124, 123]},
        "stand": {"E": 121, "NE": 118, "N": 126, "NW": 139, "W": 136, "SW": 133, "S": 129, "SE": 124}},
    "ball": {"rotation": [142, 143, 144]},
}
DIRS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
NORTH_TO_SOUTH = {"N": "S", "NE": "SE", "NW": "SW"}
STOP_FLIP = {"N": "S", "NE": "SE", "NW": "SW", "S": "N", "SE": "NE", "SW": "NW"}
CELE_SLIDE = {"E": [13, 14, 14, 14], "W": [45, 44, 44, 44]}

ACTIONS, MOVE_E, STAND_K = {}, {}, {}
REF_MOVE, REF_STAND, BALL_ROT = {}, {}, [142, 143, 144]


def _ks(v, lo, hi):
    out = [int(x) for x in v]
    if not out or any(not lo <= k <= hi for k in out):
        raise ValueError(tr("err.ids_range"))
    return out


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _parse_actions(raw):
    acts = {}
    for key, a in raw["actions"].items():
        e = _ks(a["E"], 0, 58)
        acts[str(key)] = {"E": e, "W": _ks(a["W"], 0, 58) if a.get("W") else [58 - k for k in e]}
    moves = {d: _ks(raw["moves"][d], 0, 58) for d in DIRS}
    stand = {d: int((raw.get("stand") or {}).get(d, moves[d][0])) for d in DIRS}
    rf = raw["referee"]
    rmove = {d: _ks(rf["move"][d], 118, 141) for d in DIRS}
    rstand = {d: int(rf["stand"][d]) if isinstance(rf["stand"], dict) and d in rf["stand"] else rmove[d][0] for d in DIRS}
    rot = _ks(raw.get("ball", {}).get("rotation", [142, 143, 144]), 142, 144)
    return acts, moves, stand, rmove, rstand, rot


def load_data(dirs):
    global ACTIONS, MOVE_E, STAND_K, REF_MOVE, REF_STAND, BALL_ROT
    notes = []

    def find(name):
        for d in dirs:
            r = _read_json(os.path.join(d, name))
            if r:
                return r, os.path.join(d, name)
        return None, None

    raw, path = find("tore_actions.json")
    try:
        if raw is None:
            raise KeyError(tr("err.file_not_found"))
        parsed = _parse_actions(raw)
        notes.append(Note("note.actions_file", path=path))
    except (KeyError, ValueError, TypeError) as ex:
        parsed = _parse_actions(DEFAULT_ACTIONS)
        notes.append(Note("note.actions_default", True, reason=ex))
    ACTIONS, MOVE_E, STAND_K, REF_MOVE, REF_STAND, BALL_ROT = parsed
    for need in ("kick", "header", "bicycle", "slide", "dive", "fall", "cele"):
        if need not in ACTIONS:
            ACTIONS[need] = _parse_actions(DEFAULT_ACTIONS)[0][need]
    return notes


def _off(team):
    return 0 if team == 0 else 59


def run_cycle(team, d):
    return [_off(team) + k for k in MOVE_E[d]]


def stand_sid(team, d):
    return _off(team) + STAND_K[d]


def action_sids(team, key, side):
    return [_off(team) + k for k in ACTIONS[key][side]]


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def unit(x, y, default=(1.0, 0.0)):
    d = math.hypot(x, y)
    return (x / d, y / d) if d > 1e-9 else default


def dir8(dx, dy, diag=True):
    ax, ay = abs(dx), abs(dy)
    if ax == 0 and ay == 0:
        return None
    if ay < 0.41 * ax:
        d = "E" if dx > 0 else "W"
    elif ax < 0.41 * ay:
        d = "S" if dy > 0 else "N"
    else:
        d = ("S" if dy > 0 else "N") + ("E" if dx > 0 else "W")
        if not diag:
            d = d[1]
    return d


FONT_ROWS = {"MICRO4.FON": 6, "FLOW.FON": 8}
FONT_CODES = {
    "MICRO4.FON": list(range(0x20, 0x60)) + list(range(0x61, 0x7F)),
    "FLOW.FON": [0x20, 0x21, 0x22, 0x24, 0x25, 0x27, 0x28, 0x29] + list(range(0x2A, 0x40)) + list(range(0x41, 0x5F)) + list(range(0x61, 0x7F)),
}
_ACC = {"7e": "\u00b0", "24": "\u20ac", "5b": "\u00ec", "5d": "\u00e9", "7b": "\u00e8", "7c": "\u00f9", "7d": "\u00f2", "2a": "\u00e0"}
DEFAULT_CHARMAPS = {"MICRO4.FON": dict(_ACC), "FLOW.FON": dict(_ACC)}
CHARMAP_GAME = "BUNDESLIGA MANAGER PROFESSIONAL"

CHAR_FALLBACK = {"|": "/", "{": "(", "}": ")", "~": "-", "[": "(", "]": ")", "*": "+", "$": "S", "#": "+", "&": "+", "@": "a",
                 "_": "-", "`": "'", "\\": "/", "^": "'", "\u00df": "s", "\u00e6": "a", "\u00f8": "o", "\u0153": "o",
                 "\u2019": "'", "\u2018": "'", "\u201c": "\"", "\u201d": "\"", "\u2013": "-", "\u2014": "-", "\u2026": ".",
                 "\u00a0": " ", "\t": " "}


def _read_charmaps(dirs):
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


def parse_fon(path, rows, codes):
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


class BitmapFont:
    def __init__(self, path, name, charmap):
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

    def code(self, ch):
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

    def _glyph(self, code, scale):
        sc = self._scaled.setdefault(scale, {})
        g = sc.get(code)
        if g is None:
            base = self.glyphs[code]
            g = sc[code] = base if scale == 1 else pygame.transform.scale(base, (base.get_width() * scale, base.get_height() * scale))
        return g

    def text_width(self, text, scale=1):
        return sum(self.width[self.code(ch)] for ch in text) * scale

    def render(self, text, color, scale=1):
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


class LoMetrics:
    def __init__(self, font, ps):
        self.font, self.ps = font, ps

    def size(self, text):
        return self.font.size(text)[0] / float(self.ps), 6


class ScaledFont:
    def __init__(self, font, scale):
        self.font, self.scale = font, scale

    def render(self, text, antialias=True, color=(255, 255, 255)):
        return self.font.render(text, color, self.scale)

    def size(self, text):
        return self.font.text_width(text, self.scale), self.font.rows * self.scale

    def get_height(self):
        return self.font.rows * self.scale


class FontBank:
    SMALL_MAX_PX = 23

    def __init__(self):
        self.micro = self.flow = None
        self.modern = False
        self._px = {}

    def load(self, dirs):
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

    def small(self, scale=1):
        key = ("m", scale)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = ScaledFont(self.micro, scale)
        return f

    def modern_font(self, px):
        key = ("mod", px)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = pygame.font.SysFont("dejavusans,segoeui,arial,helvetica,liberationsans", int(px))
        return f

    def get(self, px):
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


FONTS = FontBank()


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else clamp(((px - ax) * dx + (py - ay) * dy) / l2, 0.0, 1.0)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def ground_to_img(wx, wv):
    px, gy = persp_from_world(wx, wv)
    return px, gy + Y_OFFSET + 10


def decode_vga(path):
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


def vga_surface(img, palette, transparent0):
    w, h, pix = img
    pal = list(palette) + [(0, 0, 0)] * (256 - len(palette))
    out = bytearray(w * h * 4)
    out[0::4] = pix.translate(bytes(c[0] for c in pal[:256]))
    out[1::4] = pix.translate(bytes(c[1] for c in pal[:256]))
    out[2::4] = pix.translate(bytes(c[2] for c in pal[:256]))
    out[3::4] = pix.translate(_ALPHA_LUT) if transparent0 else b"\xff" * (w * h)
    return pygame.image.frombuffer(bytes(out), (w, h), "RGBA").convert_alpha()


def find_subdir(parent, name):
    try:
        for fn in os.listdir(parent):
            p = os.path.join(parent, fn)
            if fn.lower() == name.lower() and os.path.isdir(p):
                return p
    except OSError:
        pass
    return None


def find_file(folder, stem):
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            if fn.lower() == stem.lower() + ".vga":
                return os.path.join(folder, fn)
    return None


def locate_pic(app_dir, hint=None):
    cand = []
    if hint:
        cand += [hint, find_subdir(hint, "pic")]
    env = os.environ.get("TORE_PIC")
    if env:
        cand += [env, find_subdir(env, "pic")]
    cwd = os.getcwd()
    for base in (app_dir, cwd, os.path.dirname(app_dir), os.path.dirname(cwd)):
        cand += [find_subdir(base, "pic"), base]
    for d in cand:
        if d and find_file(d, "27"):
            return d
    return None


def find_asset(name, dirs):
    for d in dirs:
        if d and os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower() == name and os.path.isfile(os.path.join(d, fn)):
                    return os.path.join(d, fn)
    return None


def fatal(missing, searched):
    msg = tr("fatal.missing") + "\n  " + "\n  ".join(missing)
    if searched:
        msg += "\n\n" + tr("fatal.searched") + "\n  " + "\n  ".join(searched)
    print(msg, file=sys.stderr)
    try:
        import tkinter as tk
        from tkinter import messagebox
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror(tr("fatal.title"), msg)
        r.destroy()
    except Exception:
        pass
    sys.exit(1)


def ask_pic_dir():
    try:
        import tkinter as tk
        from tkinter import filedialog
        r = tk.Tk()
        r.withdraw()
        d = filedialog.askdirectory(title=tr("dlg.pick_pic"))
        r.destroy()
        return d or None
    except Exception:
        return None


TORE_SIG = b"BM-Ed1.3-WK\0"
TORE_N_REC = 27
TORE_FPS = 20
TORE_CAM_DEAD = (4, 3)
TORE_CAM_STEP = (22, 3)
TORE_LEAD_SECS = 1.0
TORE_MAX_FRAMES = 256
TORE_RANK = {"S": 0, "B": 1, "P": 2, "L": 3, "R": 3}
TORE_GOAL_Y = 28
DE_MAP = {"[": "\u00c4", "\\": "\u00d6", "]": "\u00dc", "{": "\u00e4", "|": "\u00f6", "}": "\u00fc"}
DE_TABLE = {ord(k): v for k, v in DE_MAP.items()}
DE_INV = {v: k for k, v in DE_MAP.items()}


def tore_cls(sid):
    if 145 <= sid <= 147:
        return "S"
    if 142 <= sid <= 144:
        return "B"
    if sid == 1000:
        return "L"
    if sid == 1024:
        return "R"
    return "P"


def tore_normalize(snap):
    pl, rf, bl = snap[:3]

    def px(x):
        return int(round(clamp(x - FIELD_X0, 6, ORIG_FW - 6)))

    def py(y):
        return int(round(clamp(y, 0, MAX_Y)))
    recs = [[px(sx), py(sy), sid] for sx, sy, sid, _vis in pl]
    recs.append([px(rf[0]), py(rf[1]), rf[2]])
    bpx, bgy, bz, bsid = bl
    bx = int(round(clamp(bpx - FIELD_X0, 2, ORIG_FW - 2)))
    by = py(bgy)
    z = max(0.0, bz)
    recs.append([bx, by + 4, 145])
    recs.append([bx, int(round(by + 3 - z)), bsid])
    recs.append([bx, TORE_GOAL_Y, 1000])
    recs.append([bx, TORE_GOAL_Y, 1024])
    return recs, (bx, by, z)


def tore_order(recs):
    sh = next((r for r in recs if tore_cls(r[2]) == "S"), None)

    def key(i):
        x, y, sid = recs[i]
        c = tore_cls(sid)
        k = y
        if c == "S":
            k = y - 4
        elif c == "B":
            k = (sh[1] - 4) if sh else y
        return (k, TORE_RANK[c], i)
    return sorted(range(len(recs)), key=key)


def tore_pack(frames, events=None, author=""):
    n = len(frames)
    if not 1 <= n <= TORE_MAX_FRAMES:
        raise ValueError(tr("err.frames_invalid", n=n))
    ev = list(events or [None] * 4)[:4] + [None] * 4
    out = bytearray(TORE_SIG + bytes(255 if e is None else max(0, min(254, int(e))) for e in ev[:4]) + bytes([n - 1]))
    for scx, scy, recs in frames:
        if len(recs) != TORE_N_REC:
            raise ValueError(tr("err.need_records", n=TORE_N_REC))
        w = [(int(scx) & 255) | ((int(scy) & 255) << 8)]
        for x, y, sid in recs:
            ymin = BALL_Y_MIN if 142 <= sid <= 144 else 0
            w += [max(0, min(65535, int(x))), max(ymin, min(65535, int(y))) & 0xFFFF, int(sid)]
        out += struct.pack("<82H", *w)
    a = "".join(DE_INV.get(ch, ch) for ch in author).encode("cp437", "replace")[:250]
    out += bytes([len(a) + 1]) + a + b"\0"
    return bytes(out)


def tore_build(snaps, author="", fps_src=60, fps=None):
    fps = max(5, int(fps or TORE_FPS))
    step = fps_src / float(fps)
    n = len(snaps)
    idx = sorted(set(int(round((n - 1) - k * step)) for k in range(int((n - 1) / step) + 1)))
    idx = [i for i in idx if 0 <= i < n]
    norm = [tore_normalize(snaps[i]) for i in idx]
    balls = [b for _recs, b in norm]
    first = 0
    for k in range(1, len(balls)):
        if math.hypot(balls[k][0] - balls[k - 1][0], balls[k][1] - balls[k - 1][1]) >= 1.5 or abs(balls[k][2] - balls[k - 1][2]) >= 1.0:
            first = k
            break
    start = max(0, first - int(round(TORE_LEAD_SECS * fps)))
    start = max(start, len(idx) - TORE_MAX_FRAMES)
    norm = norm[start:]
    frames, cam, spin = [], None, 0
    prev_ball = None
    for k, (recs, (bx, by, z)) in enumerate(norm):
        moving = prev_ball is not None and (math.hypot(bx - prev_ball[0], by - prev_ball[1]) >= 0.5 or z > 0.5)
        prev_ball = (bx, by)
        if moving:
            spin += 1
        recs[-3][2] = BALL_ROT[spin % len(BALL_ROT)] if moving or spin else recs[-3][2]
        ty = by + Y_OFFSET + 4 - z * 0.4
        tgt = (clamp(bx - ORIG_WIN_W / 2.0, 0, ORIG_SCROLL_MAX_X), clamp(ty - ORIG_WIN_H / 2.0, 0, ORIG_SCROLL_MAX_Y))
        if cam is None:
            cam = [int(round(tgt[0])), int(round(tgt[1]))]
        else:
            for a in (0, 1):
                d = tgt[a] - cam[a]
                if abs(d) > TORE_CAM_DEAD[a]:
                    mv = int(round(d * (0.55, 0.35)[a]))
                    if mv == 0:
                        mv = 1 if d > 0 else -1
                    cam[a] += max(-TORE_CAM_STEP[a], min(TORE_CAM_STEP[a], mv))
        frames.append((cam[0], cam[1], [recs[j] for j in tore_order(recs)]))
    return tore_pack(frames, None, author)


def tore_next_path(folder, ext="V"):
    os.makedirs(folder, exist_ok=True)
    used = set()
    for fn in os.listdir(folder):
        stem, e = os.path.splitext(fn)
        if e[1:].upper() == ext and stem.isdigit():
            used.add(int(stem))
    n = 1
    while n in used:
        n += 1
    return os.path.join(folder, "%d.%s" % (n, ext))


MANA_HDR = 0x03D8
MANA_N_TEAMS = 64
MANA_TEAM_LEN = 543
MANA_NAME_LEN = 23
MANA_PLAYER_LEN = 26
MANA_N_PLAYERS = 20


def _mana_str(raw):
    raw = bytes(raw).split(b"\0", 1)[0]
    txt = raw.decode("cp850", "replace")
    return "".join(ch for ch in txt if ch.isprintable()).strip().translate(DE_TABLE)


def load_mana(path):
    with open(path, "rb") as fh:
        data = fh.read()
    teams = []
    for i in range(MANA_N_TEAMS):
        a = MANA_HDR + i * MANA_TEAM_LEN
        if a + MANA_TEAM_LEN > len(data):
            break
        rec = data[a:a + MANA_TEAM_LEN]
        name = _mana_str(rec[:MANA_NAME_LEN])
        if not name:
            continue
        players = [_mana_str(rec[MANA_NAME_LEN + j * MANA_PLAYER_LEN: MANA_NAME_LEN + (j + 1) * MANA_PLAYER_LEN])
                   for j in range(MANA_N_PLAYERS)]
        teams.append(dict(index=i, name=name, logo=data[i], players=players))
    if not teams:
        raise ValueError(tr("err.no_teams"))
    return teams


def find_mana(dirs, explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for d in dirs:
        try:
            for fn in os.listdir(d):
                if fn.lower() == "mana.dat" and os.path.isfile(os.path.join(d, fn)):
                    return os.path.join(d, fn)
        except OSError:
            pass
    return None


def default_teams():
    mk = lambda n: [tr("player.default", n=i + 1) for i in range(MANA_N_PLAYERS)]
    return [dict(index=0, name=tr("team.default_home"), logo=-1, players=mk(0)), dict(index=1, name=tr("team.default_away"), logo=-1, players=mk(1))]


def load_teams(dirs, explicit=None):
    path = find_mana(dirs, explicit)
    if path is None:
        return default_teams(), Note("note.mana_missing", True)
    try:
        teams = load_mana(path)
        return teams, Note("note.mana_ok", path=path, n=len(teams))
    except (OSError, ValueError) as ex:
        return default_teams(), Note("note.mana_bad", True, reason=ex)


def _wline(a, b, n=24):
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


FIELD_ROW0 = PITCH_TOP_Y + Y_OFFSET + 10




class Graphics:
    def __init__(self, pic_dir, field_path, board_path, sheet_path):
        self.pic_dir = pic_dir
        self.board_path = board_path
        img = decode_vga(sheet_path)
        if img is None:
            raise OSError(tr("err.gfx_unreadable", path=sheet_path))
        self.sheet = vga_surface(img, PAL_DEFAULT, True)
        try:
            field = pygame.image.load(field_path).convert()
        except pygame.error as ex:
            raise OSError(tr("err.gfx_unreadable_ex", path=field_path, reason=ex))
        if field.get_size() != (FW, FH):
            field = pygame.transform.smoothscale(field, (FW, FH))
        self.field = field
        self._cache = {}
        self._logos = {}
        try:
            raw = pygame.image.load(board_path).convert_alpha()

            def crop(box):
                return raw.subsurface(pygame.Rect(box[0], box[1], box[2] - box[0] + 1, box[3] - box[1] + 1)).copy()
            gl, gr = crop(BOARD_GOAL_L), crop(BOARD_GOAL_R)
            self.clock_icon = crop(BOARD_CLOCK)
            ri = crop(BOARD_ROSTER_ICON)
            self.roster_icon = ri.subsurface(ri.get_bounding_rect()).copy()
        except (ValueError, pygame.error) as ex:
            raise OSError(tr("err.board_area", reason=ex))
        gy = GOAL_Y1 + Y_OFFSET + 10 + 1
        self.goals = ((gl, (GOAL_FRONT_X[0] + FIELD_X0 - gl.get_width(), gy - gl.get_height())),
                      (gr, (GOAL_FRONT_X[1] + FIELD_X0, gy - gr.get_height())))
        self.shadow_top = self.sprite(145).get_bounding_rect().top
        self.crowd = self._build_crowd()

    def _build_crowd(self):
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

    def crowd_frame(self):
        return self.crowd[(pygame.time.get_ticks() // 280) % len(self.crowd)]


    def sprite(self, sid):
        s = self._cache.get(sid)
        if s is None:
            col, row = sid % SHEET_COLS, sid // SHEET_COLS
            x0, w = col * CELL_W, CELL_W
            if sid >= 142:
                x0, w = x0 + 4, 4
            s = self._cache[sid] = self.sheet.subsurface(pygame.Rect(x0, row * CELL_H, w, CELL_H)).copy()
        return s

    def logo(self, logo_id):
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


BOARD_W, BOARD_H, BOARD_SRC = 320, 81, (320, 112)
DIGIT_W, DIGIT_H, DIGIT_Y, DIGIT_PITCH = 11, 15, 84, 14
BOARD_LOGO, LOGO_SZ = ((104, 35), (183, 35)), 38
NAME_Y, NAME_MAXW, GOAL_Y = 8, 52, 16
INFO_X, INFO_Y0, INFO_DY = (149, 172), 35, 8
ROSTER_X, ROSTER_W, ROSTER_HDR_Y, ROSTER_Y0, ROSTER_DY = (4, 229), 88, 3, 13, 6
ROSTER_BALL_PX = 8
ROSTER_BALL_CY = 2
BAR_DH = 58
SB_DW = 1040
class _RoleLabels:

    def __init__(self, prefix):
        self.prefix = prefix

    def get(self, role, default=""):
        return tr(self.prefix + role) if role in ("GK", "DEF", "MID", "FWD") else default

    def __getitem__(self, role):
        return tr(self.prefix + role)


ROLE_TAG = _RoleLabels("role.tag.")


def board_scale(view_w):
    return clamp(view_w / float(SB_DW), 0.4, 1.12)


def compute_layout(zoom, scroll):
    vw, vh = (WIN_W, WIN_H) if scroll else (FW, FH)
    view_w, view_h = vw * zoom, vh * zoom
    s = board_scale(view_w)
    kb = max(1, int(view_w // BOARD_W))
    bh = BOARD_H * kb
    bar_h = int(round(BAR_DH * s))
    return dict(vw=vw, vh=vh, view_w=view_w, view_h=view_h, bs=s, kb=kb, bh=bh, bar_h=bar_h, W=view_w, H=bh + view_h + bar_h + HUD_H)


SU_W, SU_H = 1020, 716


class Scoreboard:
    BG, FRAME = (13, 17, 38), (72, 82, 138)
    LIT, WHITE, DIM = (154, 164, 228), (228, 232, 252), (104, 112, 160)

    def __init__(self, board_path):
        self.hit_rows, self.hit_form = [], []
        self.rect = pygame.Rect(0, 0, 0, 0)
        self.lo = pygame.Surface((BOARD_W, BOARD_H))
        self._logo = {}
        self._fit_cache = {}
        self._roster_icon_cache = {}
        self._clock_icon_cache = {}
        self._scaled_board_cache = {}
        self.base, self.digits, self.goal_letters = self._load_board(board_path)
        self.gfx_icon = None


    def font(self, px):
        return FONTS.get(px)

    def fit(self, text, font, maxw):
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
    def put(surf, img, cx=None, cy=None, left=None, top=None):
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
    def _load_board(path):
        try:
            img = pygame.image.load(path).convert_alpha()
        except pygame.error as ex:
            raise OSError(tr("err.gfx_unreadable_ex", path=path, reason=ex))
        if img.get_size() != BOARD_SRC:
            img = pygame.transform.smoothscale(img, BOARD_SRC)
        base = img.subsurface(pygame.Rect(0, 0, BOARD_W, BOARD_H)).copy()
        digs = [img.subsurface(pygame.Rect(i * DIGIT_PITCH, DIGIT_Y, DIGIT_W, DIGIT_H)).copy() for i in range(10)]
        goal_letters = [img.subsurface(pygame.Rect(243 + i * DIGIT_PITCH, 84, DIGIT_W, DIGIT_H)).copy()
                        for i in range(4)]
        return base, digs, goal_letters

    def _logo_img(self, g, t):
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


    def text_at(self, lo, f, text, color, x, y, cx=None):
        if FONTS.modern:
            self.defer.append((text, tuple(color[:3]), x, y, cx))
            return
        im = f.render(text, True, color)
        lo.blit(im, ((cx - im.get_width() // 2) if cx is not None else x, y))

    def draw(self, surf, g, W, H):

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
        f = LoMetrics(FONTS.modern_font(self.modern_px(pixel_scale)), pixel_scale) if FONTS.modern else FONTS.small(1)
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
            name = self.fit(TEAM_NAMES[t].upper(), f, NAME_MAXW)
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
            mf = FONTS.modern_font(self.modern_px(pixel_scale))
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
    def modern_px(ps):
        return max(8, int(round(6.5 * ps)))

    def draw_roster(self, lo, g, t, mx, my, rows_hit, form_hit):
        f = self._f
        x0, w, col = ROSTER_X[t], ROSTER_W, TEAM_COL[t]
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
            if p.red or p.yellow:
                lo.fill((230, 30, 30) if p.red else (240, 240, 0), (right - 1, y, 2, 4))
                right -= 4
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
            role = ROLE_TAG.get(getattr(p, "role", ""), "")
            if role:
                self.text_at(lo, f, role, c, nx, text_y)
                nx += 18
            self.text_at(lo, f, self.fit(p.name, f, max(0, right - nx)), c, nx, text_y)
            if out:
                pygame.draw.line(lo, c, (nx, y + 2), (right - 1, y + 2))
            rows_hit.append((r, p))

    def roster_ball(self):
        icon = self._roster_icon_cache.get(ROSTER_BALL_PX)
        if icon is None:
            src = self.gfx_icon
            h = ROSTER_BALL_PX
            w = max(2, int(round(src.get_width() * h / float(max(1, src.get_height())))))
            icon = pygame.transform.smoothscale(src, (w, h))
            self._roster_icon_cache[ROSTER_BALL_PX] = icon
        return icon

    def click(self, pos, g):
        for r, t, delta in self.hit_form:
            if r.collidepoint(pos):
                g.change_formation(t, delta)
                return True
        for r, p in self.hit_rows:
            if r.collidepoint(pos):
                g.pick_player(p)
                return True
        return self.rect.collidepoint(pos)

    def draw_bar(self, surf, g, y, W, H):
        s = g.bs
        S = lambda v: max(1, int(round(v * s)))
        pygame.draw.rect(surf, (6, 6, 12), (0, y, W, H))
        cy = y + H // 2
        label = g.minute_label()
        f = FONTS.get(S(36))
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
        sf = FONTS.get(S(20))
        for rect, tx_ in ((lb, tr("hud.half_1")), (rb, tr("hud.half_2"))):
            t = sf.render(tx_, True, (120, 130, 186))
            surf.blit(t, t.get_rect(midtop=(rect.centerx, rect.bottom + 2)))


SR = 22050
TAU = 2.0 * math.pi
AUDIO_VERSION = "v6"
HORNS = ("horn_vuvu1", "horn_vuvu2", "horn_vuvu3", "horn_air1", "horn_air2", "horn_bugle", "horn_vuvu4", "horn_vuvu5", "horn_air3", "horn_air4", "horn_fanfare")
CHANTS = ("chant1", "chant2", "chant3", "chant4", "chant5", "chant6", "chant7", "chant8", "chant9", "chant10")
SHOUTS = ("shout1", "shout2", "shout3")
SOUND_NAMES = (
    "kick", "kick_hard", "head", "bounce", "tackle", "whistle", "whistle_long", "whistle_end", "post", "bar", "net", "stands",
    "amb", "amb2", "chant1", "chant2", "chant3", "chant4", "chant5", "drums1", "drums2", "swell1", "swell2",
    "cheer1", "cheer2", "cheer3", "oh1", "oh2", "oh3", "oh4", "oh5", "boo1", "boo2", "jeer", "shout1", "shout2", "shout3",
    "applause1", "applause2", "horn_vuvu1", "horn_vuvu2", "horn_vuvu3", "horn_air1", "horn_air2", "horn_bugle",
    "chant6", "chant7", "chant8", "chant9", "chant10", "horn_vuvu4", "horn_vuvu5", "horn_air3", "horn_air4", "horn_fanfare",
)


def _norm(x, peak=0.9):
    m = max(1e-9, max(abs(v) for v in x))
    k = peak / m
    return [v * k for v in x]


def _formant_table(f1, f2, f3, base=110.0, n=512):
    tbl = [0.0] * n
    for k in range(1, 34):
        f = k * base
        a = 1.0 / k ** 0.8
        a *= 1 + 2.4 * math.exp(-((f - f1) / (0.35 * f1 + 60)) ** 2) + 1.7 * math.exp(-((f - f2) / (0.3 * f2 + 80)) ** 2)\
            + 0.5 * math.exp(-((f - f3) / 500.0) ** 2)
        for i in range(n):
            tbl[i] += a * math.sin(TAU * k * i / n)
    return _norm(tbl, 1.0)


def _harm_table(weights, n=512):
    tbl = [0.0] * n
    for k, a in weights:
        for i in range(n):
            tbl[i] += a * math.sin(TAU * k * i / n)
    return _norm(tbl, 1.0)


class Audio:
    def __init__(self, enabled=True, cache_dir=None):
        global SR
        self.ok = False
        self.ready = False
        self.snd = {}
        self.muted = False
        self.chn = 1
        self.focus = 0.0
        self.cache_dir = cache_dir
        self.amb_vol = 0.0
        self.amb2_vol = 0.0
        self.mood = 0.0
        self.chant_t = 3.0
        self.acc_t = 6.0
        self.react_cd = 0.0
        self.pending = []
        self.last_chant = None
        if not enabled:
            return
        try:
            try:
                pygame.mixer.init(SR, -16, 2, 512, allowedchanges=0)
            except TypeError:
                pygame.mixer.init(SR, -16, 2, 512)
            f, _fmt, ch = pygame.mixer.get_init()
            SR, self.chn = f, ch
            pygame.mixer.set_num_channels(28)
            pygame.mixer.set_reserved(4)
            self.amb_ch = pygame.mixer.Channel(0)
            self.chant_ch = pygame.mixer.Channel(1)
            self.acc_ch = pygame.mixer.Channel(2)
            self.amb2_ch = pygame.mixer.Channel(3)
            self.ok = True
        except Exception:
            self.ok = False
            return
        threading.Thread(target=self._build, daemon=True).start()

    @staticmethod
    def _pcm(samples, gain=1.0):
        return array.array("h", (int(clamp(v * gain, -1.0, 1.0) * 30000) for v in samples))

    def _write_wav(self, name, pcm):
        if not self.cache_dir:
            return
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            with wave.open(os.path.join(self.cache_dir, name + ".wav"), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(SR)
                w.writeframes(pcm.tobytes())
        except (OSError, wave.Error):
            pass

    def _load_cache(self):
        if not self.cache_dir:
            return False
        try:
            with open(os.path.join(self.cache_dir, "ver.txt")) as f:
                if f.read().strip() != AUDIO_VERSION + str(SR):
                    return False
            for n in SOUND_NAMES:
                self.snd[n] = pygame.mixer.Sound(os.path.join(self.cache_dir, n + ".wav"))
            return True
        except (OSError, pygame.error):
            self.snd.clear()
            return False

    @staticmethod
    def _thump(f0, f1, dur, noise, decay, kdrop=25.0):
        n = int(dur * SR)
        out, ph = [0.0] * n, 0.0
        for i in range(n):
            t = i / SR
            ph += TAU * (f1 + (f0 - f1) * math.exp(-t * kdrop)) / SR
            out[i] = math.sin(ph) * math.exp(-t * decay) + random.uniform(-1, 1) * noise * math.exp(-t * 220)
        return _norm(out)

    @staticmethod
    def _clap():
        n = int(0.05 * SR)
        out, a = [], 0.0
        for i in range(n):
            x = random.uniform(-1, 1)
            a += 0.4 * (x - a)
            out.append((x - a) * math.exp(-i / SR * 70))
        return _norm(out, 0.8)

    @staticmethod
    def _clang():
        parts = [(540, 1.0, 3.0), (1210, .8, 4.5), (1890, .6, 5.5), (2750, .45, 7.0), (3980, .3, 9.0)]
        n = int(1.2 * SR)
        out = []
        for i in range(n):
            t = i / SR
            s = sum(a * math.sin(TAU * f * t) * math.exp(-t * d) for f, a, d in parts)
            out.append(s + random.uniform(-1, 1) * 1.5 * math.exp(-t * 300))
        return _norm(out)

    @staticmethod
    def _clang_bar():
        parts = [(215, 1.0, 1.7), (480, .85, 2.4), (845, .65, 3.4), (1320, .5, 4.8), (2010, .32, 7.0)]
        n = int(1.7 * SR)
        out = []
        for i in range(n):
            t = i / SR
            wob = 1.0 + 0.25 * math.sin(TAU * 7.0 * t) * math.exp(-t * 2.0)
            s = sum(a * math.sin(TAU * f * t + 0.6 * math.sin(TAU * 3.1 * t)) * math.exp(-t * d) for f, a, d in parts)
            out.append(s * wob + random.uniform(-1, 1) * 1.2 * math.exp(-t * 260))
        return _norm(out)

    @staticmethod
    def _plastic():
        n = int(0.5 * SR)
        out, ph, a = [], 0.0, 0.0
        for i in range(n):
            t = i / SR
            ph += TAU * (62.0 + 95.0 * math.exp(-t * 26.0)) / SR
            body = math.sin(ph) * math.exp(-t * 15.0)
            hollow = math.sin(TAU * 305.0 * t + 1.3 * math.sin(TAU * 17.0 * t)) * math.exp(-t * 20.0) * 0.45
            a += 0.45 * (random.uniform(-1, 1) - a)
            rattle = a * (0.5 + 0.5 * math.sin(TAU * 43.0 * t)) * math.exp(-t * 10.0) * 0.6
            click = random.uniform(-1, 1) * math.exp(-t * 380.0) * 0.5
            out.append(body + hollow + rattle + click)
        return _norm(out)

    @staticmethod
    def _net():
        n = int(0.7 * SR)
        out, a = [], 0.0
        for i in range(n):
            t = i / SR
            a += 0.35 * (random.uniform(-1, 1) - a)
            env = min(1.0, t / 0.012) * math.exp(-t * 6.0)
            out.append(a * env + math.sin(TAU * 70 * t) * math.exp(-t * 14) * 0.7)
        return _norm(out)

    @staticmethod
    def _whistle(dur, f=2900.0, trill=26.0):
        n = int(dur * SR)
        out, ph = [], 0.0
        for i in range(n):
            t = i / SR
            ph += TAU * f * (1 + 0.012 * math.sin(TAU * 6 * t)) / SR
            s = math.sin(ph) * 0.7 + math.sin(2 * ph) * 0.15 + random.uniform(-1, 1) * 0.10
            tr = 0.62 + 0.38 * math.sin(TAU * trill * t)
            env = min(1.0, t / 0.02) * min(1.0, max(0.0, (dur - t) / 0.05))
            out.append(s * tr * env)
        return _norm(out, 0.8)


    @staticmethod
    def _syllable_bank(n_syl=64):
        vowels = ((700, 1150, 2500), (500, 1800, 2500), (300, 2200, 3000), (430, 800, 2500), (320, 800, 2500), (600, 1000, 2600))
        tbls = [_formant_table(*v) for v in vowels]
        bank = []
        for _ in range(n_syl):
            tbl = random.choice(tbls)
            tl = len(tbl)
            dur = random.uniform(0.08, 0.27)
            n = int(dur * SR)
            f0 = random.choice((random.uniform(88, 130), random.uniform(95, 145), random.uniform(160, 240)))
            glide = random.uniform(-0.22, 0.22)
            ph = random.random() * tl
            breath = random.uniform(0.05, 0.16)
            a = 0.0
            out = []
            att = max(1, int(0.018 * SR))
            for i in range(n):
                u = i / n
                f = f0 * (1.0 + glide * (u - 0.5)) * (1.0 + 0.02 * math.sin(TAU * 5.5 * i / SR))
                ph = (ph + f * tl / SR) % tl
                env = min(1.0, i / att) * math.sin(math.pi * u) ** 0.7
                a += 0.4 * (random.uniform(-1, 1) - a)
                out.append((tbl[int(ph)] * (1 - breath) + a * breath * 2.5) * env)
            if random.random() < 0.45:
                b = 0.0
                for i in range(min(n, int(0.03 * SR))):
                    x = random.uniform(-1, 1)
                    out[i] += (x - b) * 0.5 * (1 - i / (0.03 * SR))
                    b += 0.6 * (x - b)
            bank.append(out)
        return bank

    @staticmethod
    def _walla(bank, dur, speakers, gap_rate, pitch_lo, pitch_hi, bed, swell):
        n = int(dur * SR)
        fade = int(0.6 * SR)
        raw = [0.0] * (n + fade)
        for _s in range(speakers):
            t = random.uniform(0.0, 0.4)
            sg = 0.12 + random.random() ** 2 * 0.9
            pm = random.uniform(pitch_lo, pitch_hi)
            while t < (n + fade) / SR:
                syl = random.choice(bank)
                r = pm * random.uniform(0.93, 1.08)
                m = int(len(syl) / r)
                o = int(t * SR)
                g = sg * random.uniform(0.5, 1.0)
                end = min(m, len(raw) - o)
                for k in range(end):
                    raw[o + k] += syl[int(k * r)] * g
                t += m / SR * random.uniform(0.9, 1.1) + (random.uniform(0.0, 0.03) if random.random() < 0.62 else random.expovariate(gap_rate))
        a = 0.0
        for i in range(n + fade):
            a += 0.018 * (random.uniform(-1, 1) - a)
            raw[i] = raw[i] + a * bed * 40.0
        mk = [0.78 + 0.22 * math.sin(TAU * swell[0] * i / n) * math.sin(TAU * swell[1] * i / n + 1.0) for i in range(n + fade)]
        raw = _norm([v * m for v, m in zip(raw, mk)], 0.75)
        out = raw[:n]
        for i in range(fade):
            k = i / fade
            out[i] = out[i] * k + raw[n + i] * (1 - k)
        return out

    def _choir(self, out, t0, dur, f0, amp, f1=None, voices=4, vib=5.2, noise=0.0, tbl=None):
        tbl = tbl or self._vt_oh
        tl = len(tbl)
        n = int(dur * SR)
        o = int(t0 * SR)
        if o >= len(out):
            return
        n = min(n, len(out) - o)
        att, rel = min(0.07, dur * 0.25), min(0.28, dur * 0.5)
        env = [max(0.0, min(1.0, (i / SR) / att, (dur - i / SR) / rel)) for i in range(n)]
        for _v in range(voices):
            det = 1 + random.uniform(-0.016, 0.016)
            ph = random.random() * tl
            vp = random.random() * TAU
            vr = vib * (1 + random.uniform(-0.2, 0.2))
            g = amp / voices
            for i in range(n):
                f = f0 if f1 is None else f0 + (f1 - f0) * i / n
                f *= det * (1 + 0.013 * math.sin(vp + TAU * vr * i / SR))
                ph = (ph + f * tl / SR) % tl
                out[o + i] += tbl[int(ph)] * g * env[i]
        if noise:
            a = 0.0
            for i in range(n):
                a += 0.12 * (random.uniform(-1, 1) - a)
                out[o + i] += a * noise * env[i]

    @staticmethod
    def _mix(out, snd, t0, gain):
        o = int(t0 * SR)
        for i, v in enumerate(snd):
            if o + i >= len(out):
                break
            out[o + i] += v * gain

    @staticmethod
    def _roar(out, t0, dur, gain, peak=0.4):
        o = int(t0 * SR)
        n = min(int(dur * SR), len(out) - o)
        a = b = 0.0
        for i in range(n):
            x = random.uniform(-1, 1)
            a += 0.03 * (x - a)
            b += 0.22 * (x - b)
            p = i / max(1, n)
            env = math.sin(math.pi * 0.5 * p / peak) if p < peak else math.cos(math.pi * 0.5 * (p - peak) / (1 - peak)) ** 1.5
            out[o + i] += (a * 3.0 + (b - a) * 1.4) * env * gain

    def _applause(self, dur, rate):
        n = int(dur * SR)
        out = [0.0] * n
        claps = [self._clap() for _ in range(6)]
        t = 0.0
        while True:
            env = math.sin(math.pi * min(1.0, t / dur)) ** 0.7
            t += random.expovariate(rate * env + 12)
            if t >= dur:
                break
            c, o, g = random.choice(claps), int(t * SR), random.uniform(0.3, 1.0)
            for i, v in enumerate(c):
                if o + i >= n:
                    break
                out[o + i] += v * g
        return _norm(out, 0.8)

    @staticmethod
    def _horn(tbl, f, dur, vib=0.0, buzz=0.12, att=0.08, rel=0.2, scoop=0.03, gate=None):
        tl, n = len(tbl), int(dur * SR)
        out, ph = [0.0] * n, random.random() * len(tbl)
        for i in range(n):
            t = i / SR
            ff = f * (1 + vib * math.sin(TAU * 5.5 * t)) * (1 - scoop * math.exp(-t * 14))
            ph = (ph + ff * tl / SR) % tl
            e = max(0.0, min(1.0, t / att, (dur - t) / rel))
            if gate:
                e *= 1.0 if (t % gate[0]) < gate[1] else 0.0
            out[i] = (tbl[int(ph)] + random.uniform(-1, 1) * buzz) * e
        return out

    def _build(self):
        try:
            if self._load_cache():
                self.ready = True
                return
            self._vt_oh = _formant_table(430, 800, 2500)
            self._vt_ah = _formant_table(700, 1150, 2500)
            brass = _harm_table([(k, (1.0 / k ** 0.55) * (1 + 1.6 * math.exp(-((k - 4) / 2.6) ** 2))) for k in range(1, 19)])
            air = _harm_table([(k, 1.0 / k ** 0.8) for k in range(1, 24, 2)] + [(2, 0.12), (4, 0.06)])
            bombo = self._thump(130, 42, 0.32, 0.3, 12, 18)
            clap = self._clap()
            stomp = self._thump(200, 80, 0.14, 0.6, 38)

            def put(name, samples, gain=1.0):
                pcm = self._pcm(samples, gain)
                self._write_wav(name, pcm)
                if self.chn == 2:
                    st = array.array("h", [0]) * (2 * len(pcm))
                    st[0::2] = pcm
                    st[1::2] = pcm
                    pcm = st
                self.snd[name] = pygame.mixer.Sound(buffer=pcm.tobytes())

            put("kick", self._thump(190, 55, 0.14, 0.7, 30), 0.8)
            put("kick_hard", self._thump(230, 48, 0.2, 1.0, 20), 1.0)
            put("head", self._thump(130, 70, 0.10, 0.35, 38), 0.8)
            put("bounce", self._thump(120, 80, 0.09, 0.1, 40), 0.55)
            put("tackle", self._thump(95, 45, 0.16, 0.8, 24), 0.9)
            put("whistle", self._whistle(0.32), 0.75)
            put("whistle_long", self._whistle(0.85), 0.75)
            tri = [0.0] * int(1.9 * SR)
            for t0, d in ((0.0, 0.3), (0.45, 0.3), (0.95, 0.85)):
                self._mix(tri, self._whistle(d), t0, 1.0)
            put("whistle_end", _norm(tri, 0.85), 0.75)
            put("post", self._clang(), 0.9)
            put("bar", self._clang_bar(), 0.9)
            put("net", self._net(), 0.9)
            put("stands", self._plastic(), 0.9)
            bank = self._syllable_bank()
            put("amb", self._walla(bank, 6.0, 15, 2.6, 0.85, 1.10, 0.20, (2, 3)), 1.0)
            put("amb2", self._walla(bank, 7.0, 26, 4.0, 0.95, 1.30, 0.14, (3, 2)), 1.0)
            self.ready = True

            def chant(notes, drums, bpm, beats, tbl, voices=3, noise=0.04):
                beat = 60.0 / bpm
                out = [0.0] * int(beats * beat * SR)
                for b0, d, hz, a in notes:
                    self._choir(out, b0 * beat, d * beat, hz, a, voices=voices, noise=noise, tbl=tbl)
                for b0, k in drums:
                    self._mix(out, {"b": bombo, "c": clap, "s": stomp}[k], b0 * beat, {"b": 1.1, "c": 0.5, "s": 0.7}[k])
                return _norm(out, 0.85)
            A2, C3, D3, E3, G3, A3 = 110.0, 130.8, 146.8, 164.8, 196.0, 220.0
            oh, ah = self._vt_oh, self._vt_ah
            put("chant1", chant([(0, .8, E3, 1), (1, .8, E3, 1), (2, .8, E3, 1), (3, 1.7, G3, 1.1), (5, .8, E3, 1), (6, .8, D3, 1), (7, 1.9, C3, 1.1)],
                                [(0, "b"), (1, "b"), (2, "b"), (3, "b"), (4.5, "c"), (5, "b"), (6, "b"), (7, "b"), (8.5, "c")], 112, 9.6, oh))
            put("chant2", chant([(0, 2.8, G3, 1), (3, 1.8, A3, 1.1), (5, 2.8, G3, 1), (8, 3.6, E3, 1.1)],
                                [(0, "b"), (2, "b"), (4, "b"), (6, "b"), (8, "b"), (10, "b"), (1, "s"), (3, "s"), (5, "s"), (7, "s")], 84, 12, ah, 4))
            put("chant3", chant([(0, .4, E3, 1), (.5, .4, E3, 1), (1, .4, E3, 1), (1.5, .4, E3, 1), (2, .4, E3, 1), (2.5, .4, E3, 1), (3, 1.3, G3, 1.2),
                                 (5, .4, E3, 1), (5.5, .4, E3, 1), (6, .4, E3, 1), (6.5, .4, E3, 1), (7, 1.3, D3, 1.1)],
                                [(i, "b") for i in range(9)] + [(0.5 + i, "c") for i in range(0, 9, 2)], 140, 9, oh))
            put("chant4", chant([(0, 1.6, C3, 1), (2, .7, E3, 1), (3, 1.8, G3, 1.1), (6, 1.6, C3, 1), (8, .7, E3, 1), (9, 2.2, D3, 1.1)],
                                [(0, "b"), (3, "b"), (6, "b"), (9, "b"), (4.5, "s"), (10.5, "s")], 100, 12, ah, 4))
            put("chant5", chant([(0, 3.6, A2, 1.1), (4, 3.6, C3, 1.1)],
                                [(i * 0.5, "c") for i in range(0, 16, 2)] + [(i, "b") for i in range(0, 8, 2)], 128, 8, oh, 4, 0.08))
            F3 = 174.6
            put("chant6", chant([(0, .5, E3, 1), (.5, .5, E3, 1), (1, .5, E3, 1), (1.5, 1.3, A3, 1.15), (3.5, .5, E3, 1), (4, .5, E3, 1),
                                 (4.5, .5, E3, 1), (5, 1.5, G3, 1.1)],
                                [(i, "b") for i in range(0, 7)] + [(0.5 + i, "c") for i in range(0, 7, 2)], 132, 7, oh))
            put("chant7", chant([(0, 1.8, A2, 1), (2, 1.8, C3, 1), (4, 1.8, E3, 1.1), (6, 3.6, A3, 1.2)],
                                [(0, "b"), (4, "b"), (6, "b"), (2, "s"), (3, "s"), (5, "s"), (7, "c")], 76, 10, ah, 5, 0.06))
            put("chant8", chant([(0, .3, D3, 1), (.5, .3, D3, 1), (1, .3, D3, 1), (1.5, .3, D3, 1), (2, .9, F3, 1.1),
                                 (3.5, .3, D3, 1), (4, .3, D3, 1), (4.5, .3, D3, 1), (5, .3, D3, 1), (5.5, .9, E3, 1.1)],
                                [(i, "b") for i in range(7)] + [(i + 0.5, "c") for i in range(0, 7)] + [(i * 0.5, "s") for i in range(1, 12, 2)],
                                156, 7, oh))
            put("chant9", chant([(0, 1.6, G3, 1.1), (2, .7, E3, 1), (3, .7, E3, 1), (4, 1.6, G3, 1.1), (6, .7, D3, 1), (7, 1.8, E3, 1.1)],
                                [(0, "b"), (2, "b"), (4, "b"), (6, "b"), (3, "c"), (7, "c"), (1, "s"), (5, "s")], 96, 9.6, ah, 4))
            put("chant10", chant([(0, .9, C3, 1), (1, .9, D3, 1), (2, .9, E3, 1.05), (3, .9, G3, 1.1), (4, 2.4, A3, 1.25),
                                  (7, .9, G3, 1), (8, 2.2, E3, 1.1)],
                                 [(i, "b") for i in range(0, 10, 2)] + [(i + 1, "c") for i in range(0, 10, 2)], 108, 10.5, oh, 4))
            for nm, pat in (("drums1", [(0, "b"), (1, "b"), (2, "b"), (3, "b"), (1.5, "c"), (3.5, "c")]),
                            ("drums2", [(0, "b"), (0.75, "b"), (1.5, "b"), (2, "b"), (3, "b"), (3.5, "b"), (1, "c"), (3, "c")])):
                beat = 60.0 / 108
                out = [0.0] * int(4 * beat * 2 * SR)
                for rep in range(2):
                    for b0, k in pat:
                        self._mix(out, {"b": bombo, "c": clap}[k], (b0 + rep * 4) * beat, 1.0 if k == "b" else 0.55)
                put(nm, _norm(out, 0.85), 0.9)
            for nm, f0, f1 in (("swell1", 100, 125), ("swell2", 90, 80)):
                out = [0.0] * int(4.2 * SR)
                self._choir(out, 0.2, 3.8, f0, 0.8, f1, voices=5, noise=0.5, tbl=oh)
                self._roar(out, 0.0, 4.0, 0.6)
                put(nm, _norm(out, 0.8), 0.8)
            ch = [0.0] * int(4.0 * SR)
            for t0, d, f0, f1, v in ((0.0, 2.0, 120, 190, 5), (0.3, 1.8, 150, 240, 5), (0.7, 2.6, 180, 290, 5), (1.2, 2.5, 130, 210, 5)):
                self._choir(ch, t0, d, f0, 1.0, f1, voices=v, noise=0.3, tbl=oh)
            self._roar(ch, 0.0, 3.8, 0.9)
            self._mix(ch, bombo, 0.0, 1.0)
            put("cheer1", _norm(ch, 0.9), 1.0)
            ch = [0.0] * int(4.4 * SR)
            for t0, d, f0, f1 in ((0.0, 1.2, 150, 200), (0.9, 1.4, 190, 260), (1.9, 2.3, 230, 330)):
                self._choir(ch, t0, d, f0, 1.0, f1, voices=5, noise=0.25, tbl=ah)
            self._roar(ch, 0.3, 4.0, 1.1, 0.35)
            for i in range(4):
                self._mix(ch, bombo, 0.6 + i * 0.5, 0.8)
            put("cheer2", _norm(ch, 0.9), 1.0)
            ch = [0.0] * int(3.4 * SR)
            self._roar(ch, 0.0, 3.4, 1.6, 0.25)
            self._choir(ch, 0.1, 2.8, 110, 0.9, 150, voices=6, noise=0.3, tbl=oh)
            self._mix(ch, bombo, 0.05, 1.2)
            self._mix(ch, self._applause(2.6, 90), 0.8, 0.6)
            put("cheer3", _norm(ch, 0.9), 1.0)
            oo = [0.0] * int(1.8 * SR)
            self._choir(oo, 0.0, 1.7, 130, 1.0, 230, voices=5, noise=0.25, tbl=oh)
            self._choir(oo, 0.7, 1.0, 230, 0.8, 120, voices=4, tbl=oh)
            put("oh1", _norm(oo, 0.85), 1.0)
            oo = [0.0] * int(1.6 * SR)
            self._choir(oo, 0.0, 1.5, 180, 1.0, 110, voices=5, vib=3.5, noise=0.3, tbl=ah)
            self._roar(oo, 0.0, 1.5, 0.6, 0.3)
            put("oh2", _norm(oo, 0.85), 1.0)
            bo = [0.0] * int(2.0 * SR)
            self._choir(bo, 0.0, 1.9, 100, 1.0, 78, voices=6, vib=3.0, noise=0.4, tbl=oh)
            self._roar(bo, 0.0, 1.9, 0.5, 0.3)
            put("boo1", _norm(bo, 0.85), 1.0)
            bo = [0.0] * int(2.4 * SR)
            self._choir(bo, 0.0, 2.2, 112, 1.0, 90, voices=5, vib=2.5, noise=0.5, tbl=oh)
            self._choir(bo, 0.4, 1.8, 135, 0.7, 100, voices=4, tbl=ah)
            put("boo2", _norm(bo, 0.85), 1.0)
            je = [0.0] * int(3.0 * SR)
            for _ in range(9):
                f0 = random.uniform(1700, 3200)
                o = int(random.uniform(0, 1.6) * SR)
                n, ph = int(random.uniform(0.6, 1.3) * SR), 0.0
                for i in range(min(n, len(je) - o)):
                    ph += TAU * f0 * (1 - 0.18 * (i / n)) * (1 + 0.01 * math.sin(TAU * 6 * i / SR)) / SR
                    je[o + i] += math.sin(ph) * math.sin(math.pi * i / n) * 0.35
            self._roar(je, 0.0, 3.0, 0.8, 0.4)
            put("jeer", _norm(je, 0.8), 0.9)
            sad = [0.0] * int(1.7 * SR)
            self._choir(sad, 0.0, 0.8, 230, 1.0, 150, voices=6, vib=2.5, noise=0.2, tbl=oh)
            self._choir(sad, 0.65, 0.95, 200, 0.9, 115, voices=6, vib=3.0, noise=0.25, tbl=oh)
            self._roar(sad, 0.0, 1.6, 0.35, 0.3)
            put("oh3", _norm(sad, 0.85), 1.0)
            sad = [0.0] * int(2.3 * SR)
            self._choir(sad, 0.0, 2.1, 250, 1.0, 105, voices=7, vib=3.2, noise=0.35, tbl=ah)
            self._roar(sad, 0.0, 2.2, 0.4, 0.2)
            put("oh4", _norm(sad, 0.85), 1.0)
            sad = [0.0] * int(2.0 * SR)
            self._choir(sad, 0.0, 1.8, 160, 1.0, 95, voices=6, vib=2.0, noise=0.4, tbl=oh)
            self._choir(sad, 0.35, 1.4, 190, 0.6, 120, voices=4, vib=2.8, tbl=ah)
            self._mix(sad, self._applause(0.8, 70), 1.1, 0.25)
            put("oh5", _norm(sad, 0.85), 1.0)
            for k, (f0, f1, d) in enumerate(((140, 105, 0.42), (120, 150, 0.35), (160, 120, 0.5))):
                sh = [0.0] * int((d + 0.3) * SR)
                self._choir(sh, 0.0, d, f0, 1.0, f1, voices=4, vib=4.0, noise=0.2, tbl=ah)
                put("shout%d" % (k + 1), _norm(sh, 0.85), 0.9)
            put("applause1", self._applause(3.2, 110), 0.8)
            put("applause2", self._applause(4.6, 150), 0.8)
            put("horn_vuvu1", _norm(self._horn(brass, 233.0, 2.6, vib=0.004, buzz=0.18, att=0.15), 0.8), 0.9)
            put("horn_vuvu2", _norm(self._horn(brass, 233.0, 2.4, buzz=0.18, att=0.05, rel=0.05, gate=(0.8, 0.5)), 0.8), 0.9)
            a = self._horn(brass, 233.0, 2.2, vib=0.005, buzz=0.15, att=0.2)
            b = self._horn(brass, 237.5, 2.2, vib=0.006, buzz=0.15, att=0.3)
            c = self._horn(brass, 117.0, 2.2, buzz=0.1, att=0.25)
            put("horn_vuvu3", _norm([x + y + 0.7 * z for x, y, z in zip(a, b, c)], 0.8), 0.9)
            ah1 = [self._horn(air, f, 1.1, scoop=0.0, att=0.015, rel=0.15, buzz=0.05) for f in (311.0, 392.0, 466.0)]
            put("horn_air1", _norm([x + y + z for x, y, z in zip(*ah1)], 0.8), 0.9)
            d2 = [0.0] * int(1.9 * SR)
            for t0, d, base in ((0.0, 0.45, 349.0), (0.6, 1.1, 311.0)):
                for mult in (1.0, 1.26, 1.5):
                    self._mix(d2, self._horn(air, base * mult, d, scoop=0.0, att=0.015, rel=0.12, buzz=0.05), t0, 0.5)
            put("horn_air2", _norm(d2, 0.8), 0.9)
            bu = [0.0] * int(2.4 * SR)
            for t0, d, hz in ((0.0, 0.17, 392.0), (0.22, 0.17, 523.0), (0.44, 0.17, 659.0), (0.66, 1.2, 784.0)):
                self._mix(bu, self._horn(brass, hz, d, vib=0.01 if d > 1 else 0.0, buzz=0.04, att=0.02, rel=0.08, scoop=0.01), t0, 1.0)
            put("horn_bugle", _norm(bu, 0.8), 0.85)
            put("horn_vuvu4", _norm(self._horn(brass, 175.0, 2.8, vib=0.006, buzz=0.2, att=0.2, rel=0.3), 0.8), 0.9)
            put("horn_vuvu5", _norm(self._horn(brass, 261.0, 2.6, buzz=0.2, att=0.04, rel=0.04, gate=(0.38, 0.2)), 0.8), 0.9)
            d3 = [0.0] * int(1.6 * SR)
            for t0, d, base in ((0.0, 0.3, 311.0), (0.4, 0.3, 311.0), (0.8, 0.7, 392.0)):
                for mult in (1.0, 1.25, 1.5):
                    self._mix(d3, self._horn(air, base * mult, d, scoop=0.0, att=0.01, rel=0.08, buzz=0.05), t0, 0.5)
            put("horn_air3", _norm(d3, 0.8), 0.9)
            a4 = self._horn(air, 392.0, 2.4, scoop=0.0, att=0.03, rel=0.35, buzz=0.05)
            b4 = self._horn(air, 398.5, 2.4, scoop=0.0, att=0.03, rel=0.35, buzz=0.05)
            put("horn_air4", _norm([x + y for x, y in zip(a4, b4)], 0.8), 0.9)
            fa = [0.0] * int(2.6 * SR)
            for t0, d, hz in ((0.0, 0.14, 349.0), (0.18, 0.14, 349.0), (0.36, 0.14, 349.0), (0.54, 0.5, 466.0), (1.1, 0.2, 440.0), (1.34, 1.2, 523.0)):
                self._mix(fa, self._horn(brass, hz, d, vib=0.008 if d > 1 else 0.0, buzz=0.04, att=0.015, rel=0.08, scoop=0.01), t0, 1.0)
            put("horn_fanfare", _norm(fa, 0.8), 0.85)
            if self.cache_dir:
                try:
                    with open(os.path.join(self.cache_dir, "ver.txt"), "w") as f:
                        f.write(AUDIO_VERSION + str(SR))
                except OSError:
                    pass
        except Exception as ex:
            print("audio: errore di sintesi:", ex)

    @staticmethod
    def _set(ch, vol, pan):
        v = clamp(vol, 0.0, 1.0)
        ch.set_volume(v * min(1.0, 1.0 - pan), v * min(1.0, 1.0 + pan))

    def _pan_for(self, name):
        if name.startswith(("cheer", "oh", "boo", "jeer", "stands")):
            return clamp(self.focus, -1.0, 1.0) * 0.9
        if name.startswith(("chant", "horn", "shout", "applause", "drums", "swell")):
            return random.choice((-1.0, 1.0)) * random.uniform(0.3, 1.0)
        return 0.0

    def silence(self):
        if self.ok:
            pygame.mixer.stop()
            self.amb_vol = self.amb2_vol = 0.0
            self.pending = []

    def play(self, name, vol=1.0, pan=None):
        if not self.ok or self.muted:
            return
        s = self.snd.get(name)
        if s:
            ch = s.play()
            if ch:
                self._set(ch, vol, self._pan_for(name) if pan is None else pan)

    def crowd(self, name, vol=0.9):
        var = {"cheer": ("cheer1", "cheer2", "cheer3"), "oh": ("oh1", "oh2"), "oh_sad": ("oh3", "oh4", "oh5"),
               "boo": ("boo1", "boo2")}.get(name, (name,))
        self.play(random.choice(var), vol)
        if name == "boo" and random.random() < 0.45:
            self.later(0.25, "jeer", vol * 0.8)

    def later(self, delay, name, vol=1.0):
        self.pending.append([delay, name, vol, self._pan_for(name)])

    def react(self, kind):
        if not (self.ok and self.ready) or self.muted:
            return
        if kind in ("tackle", "shot", "save") and self.react_cd > 0:
            return
        if kind == "goal":
            self.crowd("cheer", 1.0)
            self.later(random.uniform(0.15, 0.5), random.choice(HORNS), random.uniform(0.6, 0.9))
            self.later(random.uniform(1.0, 1.6), random.choice(("applause1", "applause2", "drums1", "drums2")), 0.8)
            self.react_cd = 1.5
        elif kind == "near":
            self.crowd("oh_sad" if random.random() < 0.5 else "oh", 0.85)
            if random.random() < 0.5:
                self.later(0.4, random.choice(SHOUTS), 0.6)
            self.react_cd = 1.0
        elif kind == "save":
            self.crowd("oh_sad", 0.75)
            self.later(0.8, random.choice(("applause1", "shout1", "shout2")), 0.55)
            self.react_cd = 1.0
        elif kind == "shot":
            if random.random() < 0.4:
                self.play(random.choice(SHOUTS), random.uniform(0.35, 0.6))
            self.react_cd = 0.7
        elif kind == "tackle":
            if random.random() < 0.45:
                self.play(random.choice(SHOUTS), random.uniform(0.3, 0.55))
            self.react_cd = 0.9
        elif kind == "foul":
            self.crowd("boo", 0.8)
        elif kind == "card":
            self.play("jeer", 0.9)
            self.later(0.3, random.choice(("boo1", "boo2")), 0.8)
        elif kind == "corner":
            self.play(random.choice(("swell1", "swell2")), 0.6)
            if random.random() < 0.5:
                self.later(0.6, random.choice(HORNS), 0.5)
        elif kind == "tension":
            self.play("swell2", 0.8)
        elif kind == "start":
            self.play(random.choice(HORNS), 0.6)
            self.later(0.5, "applause1", 0.6)
        elif kind == "whistle_end":
            self.later(0.3, "applause2", 0.8)
            self.later(0.2, random.choice(HORNS), 0.6)

    def toggle_mute(self):
        self.muted = not self.muted
        if self.ok:
            if self.muted:
                pygame.mixer.stop()
            else:
                self.amb_vol = self.amb2_vol = 0.0

    def update(self, dt, intensity):
        if not (self.ok and self.ready) or self.muted:
            return
        self.react_cd = max(0.0, self.react_cd - dt)
        for item in self.pending:
            item[0] -= dt
        due = [p for p in self.pending if p[0] <= 0]
        self.pending = [p for p in self.pending if p[0] > 0]
        for _d, name, vol, pan in due:
            if name.startswith(("horn", "applause", "drums")):
                s = self.snd.get(name)
                if s:
                    self.acc_ch.play(s)
                    self._set(self.acc_ch, vol, pan)
            else:
                self.play(name, vol, pan)
        self.mood = clamp(self.mood + random.uniform(-0.6, 0.6) * dt, -0.15, 0.15)
        a1, a2 = self.snd.get("amb"), self.snd.get("amb2")
        if a1 and not self.amb_ch.get_busy():
            self.amb_ch.play(a1, loops=-1)
        if a2 and not self.amb2_ch.get_busy():
            self.amb2_ch.play(a2, loops=-1)
        k = min(1.0, 2.5 * dt)
        self.amb_vol += (clamp(0.30 + 0.45 * intensity + self.mood, 0.1, 1.0) - self.amb_vol) * k
        self.amb2_vol += (clamp(0.55 * max(0.0, intensity - 0.2) + self.mood * 0.5, 0.0, 1.0) - self.amb2_vol) * k
        self._set(self.amb_ch, self.amb_vol, 0.0)
        self._set(self.amb2_ch, self.amb2_vol, 0.0)
        self.chant_t -= dt
        if self.chant_t <= 0 and not self.chant_ch.get_busy():
            choices = [c for c in CHANTS if c != self.last_chant and c in self.snd]
            if choices:
                self.last_chant = random.choice(choices)
                self.chant_ch.play(self.snd[self.last_chant])
                self._set(self.chant_ch, 0.35 + 0.35 * intensity + random.uniform(-0.1, 0.1), self._pan_for("chant"))
            self.chant_t = random.uniform(8.0 - 5.0 * intensity, 20.0 - 10.0 * intensity)
        self.acc_t -= dt
        if self.acc_t <= 0 and not self.acc_ch.get_busy():
            r = random.random()
            if r < 0.30:
                name = random.choice(HORNS)
            elif r < 0.52:
                name = random.choice(SHOUTS)
            elif r < 0.64:
                name = random.choice(("applause1", "applause2"))
            elif r < 0.82:
                name = random.choice(("drums1", "drums2"))
            else:
                name = random.choice(("swell1", "swell2"))
            s = self.snd.get(name)
            if s:
                self.acc_ch.play(s)
                self._set(self.acc_ch, random.uniform(0.35, 0.8) * (0.7 + 0.5 * intensity), self._pan_for(name))
            self.acc_t = random.uniform(5.0 - 2.5 * intensity, 14.0 - 7.0 * intensity)


TEAM_NAMES = ["ROSSI", "BLU"]
TEAM_COL = [(225, 70, 70), (80, 120, 235)]
ROLE_K = {"GK": 0.0, "DEF": 0.40, "MID": 0.55, "FWD": 0.62}
KEEP_OFF = 36.0
LAT_K = 0.28
REF_NEAR, CARRY_TOL_T, CARRY_TOL_V = 25.0, 0.35, 2.0
MARK_R, MARK_DIST, MAX_MARK = 60.0, 5.5, 3
FORMATIONS = {}
DEFAULT_FORMATION = "4-4-2"
ROLE_POOLS = {"GK": (0, 2), "DEF": (2, 7), "MID": (7, 15), "FWD": (15, 20)}
ROLE_ORDER = ("GK", "DEF", "MID", "FWD")
REPLAY_MAX_SECS = 20
CELE_KINDS = (("huddle", 2), ("slide", 2), ("lift", 2), ("brawl", 2), ("train", 2), ("dance", 2))
T_CELE, T_AFTER = 5.6, 2.6
ROLE_LETTER = _RoleLabels("role.letter.")
DEF_LINE_U, FWD_LINE_U = 0.13, 0.45
ZONE_U = {"GK": (0.0, 0.12), "DEF": (0.03, 0.58), "MID": (0.10, 0.92), "FWD": (0.22, 1.0)}
WIDE_BONUS = 0.10
LEASH_U, LEASH_W = 0.08, 0.11
LANE_MARGIN = {1: 0.5, 2: 0.30, 3: 0.20, 4: 0.12, 5: 0.09, 6: 0.07}
_SLOT_CACHE = {}


def register_formation(name, *lines):
    if sum(lines) != 10 or len(lines) < 2 or min(lines) < 1:
        raise ValueError("una formazione deve avere 10 giocatori di movimento in almeno 2 linee")
    FORMATIONS[name] = tuple(lines)
    _SLOT_CACHE.pop(name, None)


def formation_slots(name):
    if name in _SLOT_CACHE:
        return _SLOT_CACHE[name]
    lines = FORMATIONS[name]
    slots = [dict(role="GK", u=0.035, w=0.5, zu=ZONE_U["GK"], zw=(0.30, 0.70))]
    n_l = len(lines)
    for k, n in enumerate(lines):
        role = "DEF" if k == 0 else "FWD" if k == n_l - 1 else "MID"
        u = DEF_LINE_U + (FWD_LINE_U - DEF_LINE_U) * k / float(n_l - 1)
        m = LANE_MARGIN.get(n, 0.5 / n)
        for i in range(n):
            w = 0.5 if n == 1 else m + (1.0 - 2.0 * m) * i / (n - 1)
            hw = 0.5 / n + 0.24
            zlo, zhi = clamp(w - hw, 0.03, 0.97), clamp(w + hw, 0.03, 0.97)
            if i == 0:
                zlo = 0.03
            if i == n - 1:
                zhi = 0.97
            ulo, uhi = ZONE_U[role]
            if n >= 5 and i in (0, n - 1):
                uhi = min(1.0, uhi + WIDE_BONUS)
            slots.append(dict(role=role, u=u, w=w, zu=(ulo, uhi), zw=(zlo, zhi)))
    _SLOT_CACHE[name] = slots
    return slots


def role_counts(name):
    cnt = {r: 0 for r in ROLE_ORDER}
    for sl in formation_slots(name):
        cnt[sl["role"]] += 1
    return cnt


register_formation("4-4-2", 4, 4, 2)
register_formation("5-3-2", 5, 3, 2)
register_formation("3-5-2", 3, 5, 2)
register_formation("4-3-3", 4, 3, 3)
register_formation("4-5-1", 4, 5, 1)
register_formation("3-4-3", 3, 4, 3)
ACT_SPEC = {
    "kick": dict(fdur=0.075, contact=1, hold=0.10),
    "header": dict(fdur=0.085, contact=2, hold=0.08),
    "bicycle": dict(fdur=0.075, contact=4, hold=0.20),
    "slide": dict(fdur=0.080, contact=1, hold=0.30, active=(1, 4)),
    "dive": dict(fdur=0.090, contact=99, hold=0.50, active=(1, 4)),
    "fall": dict(fdur=0.090, contact=99, hold=1.10),
    "throw": dict(fdur=0.120, contact=1, hold=0.10),
    "moonwalk": dict(fdur=0.110, contact=99, hold=0.15),
    "cele": dict(fdur=0.110, contact=99, hold=0.30),
    "punch": dict(fdur=0.085, contact=1, hold=0.30),
}


FLAG_H = 9.0
FLAG_R = 3.0
FLAG_FLY_SPEED = 135.0
INJURY_RATE = 0.0042
LOG_DIR = None


class Flag:

    def __init__(self, x, v, sg):
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

    def hit(self, ix, iv, power):
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

    def update(self, dt):
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

    def screen(self):
        if self.state == "flying":
            cx, cy = ground_to_img(self.x, self.v)
            cy -= self.z + FLAG_H / 2
            ux, uy = math.cos(self.ang) * FLAG_H / 2, math.sin(self.ang) * FLAG_H / 2
            return (cx - ux, cy - uy, cx + ux, cy + uy, self.sg)
        bx, by = ground_to_img(self.x, self.v)
        by -= self.z
        s_ = math.sin(self.tilt) * FLAG_H
        tx, ty = ground_to_img(self.x + self.dx * s_, self.v + self.dv * s_)
        sway = math.sin(self.t * 2.4) * 0.35 if self.state == "planted" else 0.0
        return (bx, by, tx + sway, ty - self.z - math.cos(self.tilt) * FLAG_H, self.sg)


class Player:
    def __init__(self, team, idx, name=""):
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
        self.walk = None
        self.wk_to = None
        self.gate = 0.0
        self.still = 0.0
        self.settled = True
        self.lx = self.lv = None

    def new_drift(self, scale=1.0):
        if self.role == "GK":
            self.drift = (0.0, 0.0)
            return
        du, dw = {"DEF": (0.055, 0.10), "MID": (0.09, 0.14), "FWD": (0.09, 0.14)}[self.role]
        self.drift = (random.uniform(-du, du) * scale, random.uniform(-dw, dw) * scale)
        self.drift_t = random.uniform(5.0, 11.0)

    def apply_slot(self, slot):
        self.role, self.base_u, self.base_w = slot["role"], slot["u"], slot["w"]
        self.zu, self.zw = slot["zu"], slot["zw"]

    def label(self):
        return "%s (%d)" % (self.name, self.num)

    def busy(self):
        return self.state == "action"

    def fallen(self):
        return self.state == "action" and self.act is not None and self.act["key"] == "fall"


class Ball:
    def __init__(self):
        self.wx, self.wv, self.z = L / 2.0, V_SPOT, 0.0
        self.vx = self.vv = self.vz = 0.0
        self.ds = 1.0
        self.owner = None
        self.last = None
        self.last_team = 0
        self.intended = None
        self.tactical_pass = False
        self.spin = 0.0
        self.age = 0.0
        self.shot_team = None
        self.gy = 0.0
        self.px = 0.0
        self.own_t = 0.0
        self.out_t = 0.0


class Ref:
    def __init__(self):
        self.wx, self.wv = L / 2.0 - 30, V_SPOT + 20
        self.vx = self.vv = 0.0
        self.face = "E"
        self.face_t = 0.0
        self.stride = 0.0
        self.card = None
        self.card_t = 0.0
        self.sid = 121
        self.sx = self.sy = 0.0


class Game:
    def __init__(self, args, gfx, audio, screen, notes, teams):
        self.args, self.gfx, self.audio, self.screen, self.notes = args, gfx, audio, screen, notes
        self.target = screen
        self.teams = teams
        self.sel = [0, 1 if len(teams) > 1 else 0]
        self.form_names = [DEFAULT_FORMATION, DEFAULT_FORMATION]
        self.team_data = [teams[self.sel[0]], teams[self.sel[1]]]
        self.board = Scoreboard(gfx.board_path)
        self.board.gfx_icon = gfx.roster_icon
        self.lineup = [None, None]
        self.su_pick = None
        self.replay_auto = not getattr(args, "no_replay", False)
        self.replay_secs = int(getattr(args, "replay_secs", 5) or 5)
        self.tore_dir = getattr(args, "tore_dir", None) or "TORE_OUT"
        self.rec = collections.deque(maxlen=60 * (REPLAY_MAX_SECS + 14))
        self.tick = 0
        self.replay = None
        self.last_scorer = ""
        self._fr = {}
        self._help_cache = None
        self.lang_open = False
        self.langs = T.discover_languages()
        self.help_page = 0
        self._help_paged = False
        self.vsurf = None
        self.su_surf = pygame.Surface((SU_W, SU_H))
        self.su_scroll, self.su_active, self.su_hits = [0, 0], 0, []
        self.zoom = args.zoom
        self.scroll = not getattr(args, "noscroll", False)
        self.speed_idx = SPEED_DEFAULT
        self.user_team = 0
        self.ctrl_choice = 0
        self._gk_press_owner = None
        self._gk_press_idx = None
        self.manual = False
        self.idle_t = 0.0
        self._last_owner = None
        self._poss_prev = None
        self.show_help = False
        self.fullscreen = False
        self.set_view_dims()
        self.font_s = FONTS.get(22)
        self.font_m = FONTS.get(34)
        self.font_t = FONTS.get(18)
        self.font_l = FONTS.get(72)
        self.field_surf = pygame.Surface((FW, FH))
        self.half_secs = max(20.0, args.half * 60.0)
        self.mode = "intro"
        self.paused = False
        self.confirm_exit = False
        self.exit_btns = ()
        self.pathdrag = None
        self.sub_menu = None
        self.subs_list = []
        self.walk_t = 0.0
        self._preview = None
        self.inj_t = 1.0
        self.flags = []
        self.sub_q, self.subs_used, self.sub_out = [[], []], [0, 0], [set(), set()]
        self.mlog, self.log_saved, self.injury = [], True, None
        self.debug = False
        self.cp = None
        self.msgs = []
        self.big = None
        self.cam = [60.0, 8.0]
        self.cam_manual = False
        self.cam_glide = 0.0 
        self.pan_return_at = 0
        self.pan_drag = None
        self.drag = None
        self.paused_gesture = None
        self.paused_traj_surface = None
        self.click_mark = None
        self.t_all = 0.0
        self.role_timer = 0.0
        self.stats = self.new_stats()
        self.reset_match()
        self.mode = "intro"

    @staticmethod
    def new_stats():
        return dict(fouls=[0, 0], yellow=[0, 0], red=[0, 0], injured=[0, 0], shots=[0, 0], goals=[0, 0], corners=[0, 0],
                    poss=[0.0, 0.0])

    def reset_match(self):
        self.score = [0, 0]
        self.half, self.real_t, self.extra = 1, 0.0, 0.0
        self.stoppage_target = 1.0
        self.att = {0: 1, 1: -1}
        self.players, self.team_p = [], [[], []]
        self.sync_teams()
        for team in (0, 1):
            slots = formation_slots(self.form_names[team])
            self.fix_lineup(team)
            names = self.lineup_names(team)
            for i in range(11):
                p = Player(team, i, names[i] if i < len(names) else "")
                p.apply_slot(slots[i])
                self.players.append(p)
                self.team_p[team].append(p)
        self.ball, self.ref = Ball(), Ref()
        self.first_kick = random.randint(0, 1)
        self.cp = None
        self.foul = self.goal = self.restart = self.outball = None
        self.half_t = 0.0
        self.msgs, self.big = [], None
        self.stats = self.new_stats()
        self.flags = [Flag(0.0, V_TOP, 1.0), Flag(L, V_TOP, -1.0), Flag(0.0, V_BOT, 1.0), Flag(L, V_BOT, -1.0)]
        self.sub_q, self.subs_used, self.sub_out = [[], []], [0, 0], [set(), set()]
        self.injury, self.sub_menu, self.pathdrag = None, None, None
        self.paused = False
        self.paused_gesture = self.paused_traj_surface = None
        for t_ in (0, 1):
            for p_, (_r, sq) in zip(self.team_p[t_], self.lineup_slots(t_)):
                p_.sq = sq
        self.mlog, self.log_saved = [], False
        self.log_event(tr("ev.match_start", home=TEAM_NAMES[0], away=TEAM_NAMES[1], fh=self.form_names[0], fa=self.form_names[1]), show=False)
        self.manual, self._last_owner, self._poss_prev = False, None, None
        self.setup_kickoff(self.first_kick, sound=False)


    def update_flags(self, dt):
        live = self.mode in ("play", "goal", "outball")
        b = self.ball
        for f in self.flags:
            if live and f.state == "planted":
                if b.owner is None:
                    sp = math.hypot(b.vx, b.vv)
                    if abs(b.wx - f.x) < FLAG_R and abs(b.wv - f.v) < FLAG_R * 1.2 and b.z < FLAG_H + 1.5 and sp > 20.0:
                        if f.hit(b.vx, b.vv, sp):
                            self.audio.play("bar" if b.z > 4.5 else "post", clamp(0.4 + sp / 260.0, 0.4, 1.0))
                            b.vx *= -0.4
                            b.vv *= 0.6
                            continue
                for p in self.players:
                    if p.state in ("out", "leaving", "down", "subout", "subin"):
                        continue
                    ddx, ddv = f.x - p.wx, f.v - p.wv
                    dist = math.hypot(ddx, ddv)
                    if dist > FLAG_R * 1.1:
                        continue
                    sp = math.hypot(p.vx, p.vv)
                    if sp > 32.0 and (p.vx * ddx + p.vv * ddv) > 0.4 * sp * max(dist, 0.1):
                        if f.hit(p.vx, p.vv, sp * (1.3 if p.state == "action" else 1.0)):
                            self.audio.play("post", clamp(0.35 + sp / 300.0, 0.35, 0.8))
                            break
            ev = f.update(dt)
            if ev == "thud":
                self.audio.play("bounce", 0.4)
            elif ev == "plant":
                self.audio.play("bounce", 0.25)


    def follow_path(self, p):
        while p.path and math.hypot(p.wx - p.path[0][0], p.wv - p.path[0][1]) < 3.0:
            p.path.pop(0)
        if not p.path:
            p.path = None
            p.new_drift(0.5)
            return False
        p.tx, p.tv = p.path[0]
        p.tag = None
        return True

    def path_player_at(self, mx, my):
        fx, row, _w = self.screen_to_ground(mx, my)
        best = None
        for p in self.players:
            if p.state in ("out", "leaving", "subout", "subin"):
                continue
            if self.user_team is not None and p.team != self.user_team:
                continue
            dd = math.hypot(p.sx - fx, (p.sy + Y_OFFSET + 5) - row)
            if dd < 14 and (best is None or dd < best[0]):
                best = (dd, p)
        return best[1] if best else None

    GESTURE_FULL = 0.55

    def gesture_intensity(self, ln):
        return clamp(ln / max(160.0, self.view_w * self.GESTURE_FULL), 0.0, 1.0)

    def gesture_plan(self, x0, y0, x1, y1):
        p = self.cp
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if p is None or ln < 12:
            return None
        ux, uy = dx / ln, dy / ln
        w1x, w1v = s2w(p.sx + ux * 40.0, p.sy + uy * 40.0)
        w0x, w0v = s2w(p.sx, p.sy)
        f = self.gesture_intensity(ln)
        return ("short" if f < 0.35 else "long"), unit(w1x - w0x, w1v - w0v), f

    def kick_plan(self, p, dx, dv, f, lob, free):
        D = 14.0 + f * (L * 0.85 - 14.0)
        lx, lv = p.wx + dx * D, p.wv + dv * D
        rad = 9.0 if free else max(14.0, 0.18 * D)
        best = None
        for q in self.team_p[p.team]:
            if q is p or q.state in ("out", "leaving", "down", "subout", "subin", "tunnel"):
                continue
            dd = math.hypot(q.wx - lx, q.wv - lv)
            if dd < rad and (best is None or dd < best[0]):
                best = (dd, q)
        target = None
        if best:
            target = best[1]
            dx, dv = unit(target.wx - p.wx, target.wv - p.wv)
            D = math.hypot(target.wx - p.wx, target.wv - p.wv)
        kind = "pass" if target else "shot"
        if target:
            power = clamp(D * 1.55 + 55.0, 95.0, 300.0)
            lift = max(self.lob_lift(D, power), 18.0) if lob else 0.0
        elif lob:
            power = clamp(D * 1.55 + 55.0, 60.0, 300.0)
            lift = max(self.lob_lift(D, power), 18.0)
        else:
            lift = 28.0
            power = self.power_for_range(dx, dv, D, lift)
        return dict(dx=dx, dv=dv, power=power, lift=lift, kind=kind, target=target, D=D)

    def power_for_range(self, dx, dv, D, lift):
        b = self.ball
        lo, hi = 25.0, 320.0
        for _ in range(11):
            mid = (lo + hi) / 2.0
            e = self.simulate_ball("kick", dict(dx=dx, dv=dv, power=mid, lift=lift))[-1]
            if math.hypot(e[0] - b.wx, e[1] - b.wv) < D:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    def can_kick_now(self):
        p, b = self.cp, self.ball
        if p is None or p.state != "free":
            return False
        return b.owner is p or (b.owner is None and math.hypot(b.wx - p.wx, b.wv - p.wv) < REACH_FIRST and b.z < 7.5)

    def simulate_ball(self, key, kw):
        b = self.ball
        power, lift = kw.get("power", 150.0), kw.get("lift", 0.0)
        if key == "header":
            power, lift = power * 0.8, max(lift, 18.0)
        elif key == "bicycle":
            power, lift = max(power, 235.0), max(lift, 28.0)
        x, v, z = b.wx, b.wv, max(b.z, 0.5)
        if key == "throw" and self.restart:
            x, v = self.restart["pos"]
            z = 12.0
        ds = depth_slow(kw["dx"], kw["dv"])
        vx, vv, vz = kw["dx"] * power * ds, kw["dv"] * power * ds, lift
        pts, t, h, nxt = [(x, v, z, power)], 0.0, 1.0 / 240.0, 0.1
        while t < 3.6 and len(pts) < 40:
            kk = depth_k(v)
            x += vx * h * kk
            v += vv * h * kk
            z += vz * h
            vz -= G * h
            if z <= 0.0:
                z = 0.0
                if vz < -35.0:
                    vz, vx, vv = -vz * 0.55, vx * 0.88, vv * 0.88
                else:
                    vz = 0.0
            f = math.exp(-(0.7 if z < 0.05 else 0.14) * h * ds)
            vx *= f
            vv *= f
            t += h
            if t >= nxt:
                pts.append((x, v, z, math.hypot(vx, vv)))
                nxt += 0.1
            if (z < 0.05 and math.hypot(vx, vv) < 6.0) or x < -4.0 or x > L + 4.0 or v < V_TOP - 12.0 or v > V_BOT + 12.0:
                break
        return pts

    def draw_shot_preview(self, x0, y0, x1, y1, lob):
        plan = self.gesture_plan(x0, y0, x1, y1)
        if plan is None or not self.can_kick_now():
            return
        kp = self.kick_plan(self.cp, plan[1][0], plan[1][1], plan[2], lob, True)
        pts = self.simulate_ball("kick", dict(dx=kp["dx"], dv=kp["dv"], power=kp["power"], lift=kp["lift"]))
        cx, cy = self.cam_int()
        z = self.zoom
        ov = pygame.Surface((self.view_w, self.view_h), pygame.SRCALPHA)
        scr = []
        for (wx, wv, wz, sp) in pts:
            ix, iy = ground_to_img(wx, wv)
            scr.append(((ix - cx) * z, (iy - cy) * z, (iy - wz - cy) * z))
        for i in range(1, len(scr)):
            pygame.draw.line(ov, (255, 255, 255, 60), scr[i - 1][:2], scr[i][:2], 1)
        n = len(scr)
        balls = {}
        for i, (sx, sy, sy2) in enumerate(scr):
            a = int(235 - 150 * i / max(1, n))
            if abs(sy2 - sy) > 2:
                pygame.draw.line(ov, (255, 255, 255, 45), (sx, sy), (sx, sy2), 1)
            frame = BALL_ROT[i % len(BALL_ROT)]
            spr = balls.get((frame, a))
            if spr is None:
                spr = pygame.transform.scale(self.gfx.sprite(frame), (4 * z, CELL_H * z))
                spr.set_alpha(a)
                balls[(frame, a)] = spr
            ov.blit(spr, (int(sx) - 2 * z, int(sy2) - 7 * z))
        ex, ey, _e2 = scr[-1]
        pygame.draw.circle(ov, (255, 200, 40, 220), (int(ex), int(ey)), max(3, int(z * 1.6)), 2)
        if kp["target"] is not None:
            tx, ty = ground_to_img(kp["target"].wx, kp["target"].wv)
            pygame.draw.circle(ov, (90, 255, 130, 230), (int((tx - cx) * z), int((ty - cy) * z)), max(6, int(z * 3.2)), 3)
        self.target.blit(ov, (0, 0))


    def natural_role(self, sq):
        for r in ROLE_ORDER:
            lo, hi = ROLE_POOLS[r]
            if lo <= sq < hi:
                return r
        return "MID"

    def bench(self, t):
        pl = self.team_data[t]["players"]
        on = {q.sq for q in self.team_p[t]} | self.sub_out[t] | {e["inn"] for e in self.sub_q[t]}
        return [i for i in range(min(len(pl), 20)) if i not in on and pl[i]]

    def sub_candidates(self, p):
        bn = self.bench(p.team)
        if p.role == "GK":
            return [i for i in bn if self.natural_role(i) == "GK"]
        c = [i for i in bn if self.natural_role(i) != "GK"]
        return sorted(c, key=lambda i: 0 if self.natural_role(i) == p.role else 1)

    def request_sub(self, p, inn=None, why="tattica"):
        t = p.team
        for e in self.sub_q[t]:
            if e["out"] is p:
                if why == "tattica":
                    self.sub_q[t].remove(e)
                    self.stoppage_target = max(1.0, self.stoppage_target - 0.55)
                    self.say(tr("msg.sub_cancelled", name=p.name), (255, 220, 160), 2.5)
                return False
        if p.red or p.state == "out":
            return False
        if self.subs_used[t] + len(self.sub_q[t]) >= 5:
            self.say(tr("msg.sub_limit", team=TEAM_NAMES[t]), (255, 160, 140), 3)
            return False
        cand = self.sub_candidates(p)
        if not cand:
            self.say(tr("msg.sub_none", name=p.name), (255, 160, 140), 3)
            return False
        inn = cand[0] if inn is None else inn
        self.sub_q[t].append(dict(out=p, inn=inn, why=why))
        self.stoppage_target += 0.55
        return True

    def open_sub_menu(self, p, rect):
        if self.user_team is not None and p.team != self.user_team:
            return
        if any(e["out"] is p for e in self.sub_q[p.team]):
            self.request_sub(p)
            return
        cand = self.sub_candidates(p)
        if not cand or self.subs_used[p.team] + len(self.sub_q[p.team]) >= 5:
            self.request_sub(p)
            return
        self.sub_menu = dict(p=p, rect=rect, cand=cand[:10])

    def sub_menu_layout(self):
        m = self.sub_menu
        w, rh = 270, 22
        h = rh * (len(m["cand"]) + 1) + 8
        x = int(clamp(m["rect"].left, 0, self.W - w))
        y = int(clamp(m["rect"].bottom + 2, 0, self.H - h))
        items = [(pygame.Rect(x + 4, y + 4 + rh * (i + 1), w - 8, rh), idx) for i, idx in enumerate(m["cand"])]
        return pygame.Rect(x, y, w, h), items

    def draw_sub_menu(self):
        m = self.sub_menu
        panel, items = self.sub_menu_layout()
        pygame.draw.rect(self.screen, (10, 12, 26), panel)
        pygame.draw.rect(self.screen, (255, 215, 0), panel, 2)
        t = m["p"].team
        used = self.subs_used[t] + len(self.sub_q[t])
        self.text(tr("hud.sub_title", name=m["p"].name, used=used), self.font_s, (255, 215, 0), (panel.x + 8, panel.y + 6), shadow=False)
        pl = self.team_data[t]["players"]
        mp = pygame.mouse.get_pos()
        for r, idx in items:
            if r.collidepoint(mp):
                pygame.draw.rect(self.screen, (60, 70, 130), r)
            self.text("%2d  %s  [%s]" % (idx + 1, pl[idx], ROLE_TAG[self.natural_role(idx)]), self.font_s, (235, 235, 245), (r.x + 4, r.y + 3), shadow=False)

    def sub_menu_click(self, pos):
        panel, items = self.sub_menu_layout()
        m = self.sub_menu
        self.sub_menu = None
        if panel.collidepoint(pos):
            for r, idx in items:
                if r.collidepoint(pos):
                    self.request_sub(m["p"], idx)
                    return

    def maybe_ai_subs(self):
        rs = self.restart
        if rs is None or rs.get("ai_sub") or self.half != 2 or self.minute() < 60:
            return
        rs["ai_sub"] = True
        for t in (0, 1):
            if self.user_team == t or self.subs_used[t] + len(self.sub_q[t]) >= 5 or random.random() > 0.16:
                continue
            c = [q for q in self.team_p[t] if q.role != "GK" and not q.red and q.state != "out"
                 and not any(e["out"] is q for e in self.sub_q[t])]
            if c:
                c.sort(key=lambda q: -(q.yellow * 2 + random.random()))
                self.request_sub(c[0], why="tattica")


    def begin_subs(self):
        self.mode = "subs"
        self.subs_t = 0.0
        self.subs_list = []
        for t in (0, 1):
            for e in self.sub_q[t]:
                p = e["out"]
                if p.state in ("out", "leaving"):
                    continue
                p.state, p.act, p.path, p.tx, p.tv = "subout", None, None, None, None
                self.set_gate(p)
                p.limp = e["why"] == "infortunio"
                self.subs_list.append(e)
            self.sub_q[t] = []
        self.audio.play("whistle", 0.5)

    def swap_identity(self, p, e):
        t = p.team
        pl = self.team_data[t]["players"]
        old = p.name
        self.sub_out[t].add(p.sq)
        p.sq = e["inn"]
        p.name = pl[p.sq]
        self.subs_used[t] += 1
        p.num = 11 + self.subs_used[t]
        p.yellow, p.red, p.limp, p.path = 0, False, False, None
        p.speed = PLAYER_SPEED * random.uniform(0.94, 1.07)
        p.skill, p.aggr = random.uniform(0.66, 0.95), random.uniform(0.2, 0.95)
        p.stride, p.hold_t, p.lift = 0.0, 0.0, 0.0
        p.new_drift()
        sub_reason = tr("ev.sub_reason_injury") if e["why"] == "infortunio" else ""
        self.log_event(tr("ev.sub", team=TEAM_NAMES[t], out=old, inn=p.name, n=self.subs_used[t], reason=sub_reason), secs=4, team=t)

    def gate_point(self, p, tv_end, tx=None, tv=None):
        gx = L / 2.0 + p.gate
        if tx is None:
            if p.wv < V_BOT + 8.0 and abs(p.wx - gx) > 1.5:
                return gx, (V_BOT - 1.0 if p.wv < V_BOT + 0.5 else V_BOT + 0.5)
            return gx, tv_end
        if p.wv > V_BOT - 1.0:
            return gx, V_BOT - 2.0
        return tx, tv

    def set_gate(self, p, side=0):
        if side:
            p.gate = side * random.uniform(0.15, 1.0) * GATE_SPREAD
        else:
            p.gate = random.uniform(-1.0, 1.0) * GATE_SPREAD

    def step_sub(self, p, dt):
        vexit = _vg(MAX_Y + 30)
        e = next((x for x in self.subs_list if x["out"] is p), None)
        sp = 30.0 if p.limp else 46.0
        if p.state == "subout":
            tx, tv = self.gate_point(p, vexit)
        else:
            if p.tx is None:
                p.tx, p.tv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            tx, tv = self.gate_point(p, vexit, p.tx, p.tv)
        ux, uv = unit(tx - p.wx, tv - p.wv, (0.0, 1.0))
        kk = depth_k(p.wv)
        p.wx += ux * sp * dt * kk
        p.wv += uv * sp * dt * kk
        p.vx, p.vv = ux * sp, uv * sp
        p.stride += sp * dt
        if abs(ux) > 0.2:
            p.face = "E" if ux > 0 else "W"
        cyc = run_cycle(p.team, p.face)
        p.sid = cyc[int(p.stride / 4.6) % len(cyc)]
        self.post_move(p)
        if p.state == "subout" and p.wv >= vexit - 0.5 and p.walk == "off":
            p.state, p.vx, p.vv, p.wv = "tunnel", 0.0, 0.0, vexit
            return
        if p.state == "subout" and p.wv >= vexit - 0.5:
            if e is not None:
                self.swap_identity(p, e)
            p.state = "subin"
            p.wx = L / 2.0 + p.gate
            p.wv = vexit
            hx, hv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            p.tx, p.tv = hx, hv
            p.limp = False
        elif p.state == "subin" and math.hypot(p.wx - p.tx, p.wv - p.tv) < 2.5:
            p.state = "free"
            p.tx = p.tv = None
            p.vx = p.vv = 0.0

    def update_subs(self, dt):
        self.subs_t += dt
        busy = [p for p in self.players if p.state in ("subout", "subin")]
        if busy and self.subs_t < 30.0:
            return
        for p in busy:
            e = next((x for x in self.subs_list if x["out"] is p), None)
            if p.state == "subout" and e is not None:
                self.swap_identity(p, e)
            p.state = "free"
            p.tx = p.tv = None
            hx, hv = self.home_pos(p, self.ball.wx, self.ball.wv, False)
            p.wx, p.wv = hx, hv
        self.mode = "restart"
        rs = self.restart
        if rs is not None:
            rs["t"], rs["ready"], rs["said"] = 0.0, False, False
            if rs["kind"] == "kickoff":
                self.setup_kickoff(rs["team"], sound=False)
            else:
                rs["taker"] = self.pick_taker(rs["kind"], rs["team"], rs["pos"])
                self.auto_taker(rs["taker"])

    def instant_subs(self):
        for t in (0, 1):
            for e in self.sub_q[t]:
                if e["out"].state != "out":
                    self.swap_identity(e["out"], e)
            self.sub_q[t] = []

    def update_injuries(self, dt):
        return

    def maybe_injury_from_tackle(self, p, kind):
        if self.mode != "play" or p.role == "GK" or p.state in ("out", "leaving") or p.red:
            return False
        sx, sy = w2s(p.wx, p.wv)
        cx, cy = self.cam_int()
        vw, vh = (WIN_W, WIN_H) if self.scroll else (FW, FH)
        if not (cx - 2 <= sx <= cx + vw + 2 and cy - 2 <= sy + Y_OFFSET <= cy + vh + 2):
            return False
        chance = 0.035 if kind == "slide" else 0.012
        if random.random() < chance:
            self.begin_injury(p)
            return True
        return False

    def begin_injury(self, p):
        self.stoppage_target += 0.85
        b = self.ball
        b.owner, b.vx, b.vv, b.vz, b.z = None, 0.0, 0.0, 0.0, 0.0
        self.mode = "injury"
        self.injury = dict(p=p, t=0.0, team=b.last_team if b.last_team is not None else 1 - p.team)
        p.state, p.act, p.tx, p.tv, p.path = "down", None, None, None, None
        p.vx = p.vv = 0.0
        self.stats["injured"][p.team] += 1
        self.log_event(tr("ev.injury", p=p.label(), team=TEAM_NAMES[p.team]), secs=5, team=p.team)
        self.audio.play("whistle_long", 0.7)
        self.audio.react("save")
        for q in self.players:
            if q is not p and q.state not in ("out", "leaving", "action"):
                q.state, q.tx, q.tv, q.tag = "free", None, None, None

    def update_injury(self, dt):
        inj = self.injury
        inj["t"] += dt
        if inj["t"] < 4.5:
            return
        p = inj["p"]
        t = p.team
        ok = self.subs_used[t] + len(self.sub_q[t]) < 5 and self.sub_candidates(p)
        p.state = "free"
        if ok:
            self.request_sub(p, why="infortunio")
        else:
            p.speed *= 0.8
            self.log_event(tr("ev.injury_stays", name=p.name), secs=3, team=p.team)
        b = self.ball
        self.injury = None
        self.start_restart("free", inj["team"], (b.wx, b.wv))
        self.log_event(tr("ev.restart_free", team=TEAM_NAMES[inj["team"]]), secs=3, team=inj["team"])

    def team_uw(self, team, wx, wv):
        u = wx / L if self.att[team] > 0 else 1.0 - wx / L
        return u, (wv - V_TOP) / PITCH_W

    def in_zone(self, p, wx, wv, mu=0.0, mw=0.0):
        u, w = self.team_uw(p.team, wx, wv)
        return p.zu[0] - mu <= u <= p.zu[1] + mu and p.zw[0] - mw <= w <= p.zw[1] + mw

    def zone_clamp(self, p, wx, wv, mu=0.0, mw=0.0):
        u, w = self.team_uw(p.team, wx, wv)
        u = clamp(u, p.zu[0] - mu, p.zu[1] + mu)
        w = clamp(w, p.zw[0] - mw, p.zw[1] + mw)
        return (u * L if self.att[p.team] > 0 else (1.0 - u) * L), V_TOP + w * PITCH_W

    def home_pos(self, p, bx, bv, poss):
        d = self.att[p.team]
        bu = bx / L if d > 0 else 1 - bx / L
        bw = (bv - V_TOP) / PITCH_W
        u = p.base_u + p.drift[0] + (bu - 0.5) * ROLE_K[p.role]
        if p.role in ("MID", "FWD"):
            u += 0.06 if poss else -0.04
        u = clamp(u, p.zu[0], p.zu[1])
        w = clamp(p.base_w + p.drift[1] + (bw - 0.5) * (0.15 if p.role == "GK" else LAT_K), p.zw[0], p.zw[1])
        hx, hv = (u * L if d > 0 else (1 - u) * L), V_TOP + w * PITCH_W
        if p.role != "GK":
            if math.hypot(hx - bx, hv - bv) < KEEP_OFF:
                ux, uv = unit(hx - bx, hv - bv, (-d, 0.0))
                hx, hv = self.zone_clamp(p, bx + ux * KEEP_OFF, bv + uv * KEEP_OFF)
        return hx, hv

    def fix_lineup(self, t, reset=False):
        need = role_counts(self.form_names[t])
        cur = {} if (reset or self.lineup[t] is None) else self.lineup[t]
        out, used = {}, set()
        for role in ROLE_ORDER:
            lo, hi = ROLE_POOLS[role]
            keep = [i for i in cur.get(role, []) if lo <= i < hi and i not in used][:need[role]]
            used.update(keep)
            for i in range(lo, hi):
                if len(keep) >= need[role]:
                    break
                if i not in used:
                    keep.append(i)
                    used.add(i)
            out[role] = keep
        self.lineup[t] = out

    def lineup_slots(self, t):
        if self.lineup[t] is None:
            self.fix_lineup(t)
        return [(r, i) for r in ROLE_ORDER for i in self.lineup[t][r]]

    def lineup_names(self, t):
        pl = self.team_data[t]["players"]
        return [pl[i] if i < len(pl) else "" for _r, i in self.lineup_slots(t)]

    def sync_teams(self):
        self.team_data = [self.teams[self.sel[0]], self.teams[self.sel[1]]]
        TEAM_NAMES[:] = [self.team_data[0]["name"].upper(), self.team_data[1]["name"].upper()]

    def set_formation(self, team, name, quiet=False):
        if name not in FORMATIONS:
            return
        self.form_names[team] = name
        self.fix_lineup(team)
        self.su_pick = None
        _SLOT_CACHE.pop(name, None)
        if self.mode == "intro":
            return
        slots = formation_slots(name)
        for p in self.team_p[team]:
            p.apply_slot(slots[p.idx])
            p.roam = False
        if not quiet:
            self.say(tr("msg.formation", team=TEAM_NAMES[team], name=name), (255, 255, 255), 2.5)
        if self.mode == "restart" and self.restart and self.restart["kind"] == "kickoff":
            self.setup_kickoff(self.restart["team"], sound=False)

    def change_formation(self, team, delta):
        names = list(FORMATIONS)
        i = names.index(self.form_names[team]) if self.form_names[team] in names else 0
        self.set_formation(team, names[(i + delta) % len(names)])

    def pick_player(self, p):
        if self.mode == "intro" or p.state in ("out", "leaving", "subin", "subout", "tunnel") or p.red:
            return
        if self.ctrl_choice in (0, 1) and p.team != self.ctrl_choice:
            return
        self.user_team = p.team
        self.manual = True
        self.select_player(p)

    def minute_label(self):
        if self.time_over():
            extra = max(1, int(self.extra / max(1.0, self.half_secs) * 45.0) + 1)
            return tr("hud.minute_extra", base=45 * self.half, extra=extra)
        return tr("hud.minute", n=int(self.minute()) + 1)

    def start_match(self):
        self.ctrl_choice = self.user_team if self.user_team in (0, 1) else None
        self.reset_match()
        self.begin_walkon(self.first_kick)

    def setup_kickoff(self, team, sound=True):
        b = self.ball
        sx, sv = L / 2.0, V_SPOT
        for p in self.players:
            if p.state == "out":
                continue
            p.state, p.act, p.vx, p.vv, p.cool, p.tag = "free", None, 0.0, 0.0, 0.0, None
            p.tx = p.tv = None
            d = self.att[p.team]
            hx, hv = self.home_pos(p, sx, sv, False)
            if p.team != team and math.hypot(hx - sx, hv - sv) < 36:
                u = 0.5 - 40.0 / L
                hx = u * L if d > 0 else (1 - u) * L
            p.wx, p.wv = hx, hv
            p.dx, p.dv, p.face = float(d), 0.0, "E" if d > 0 else "W"
        fw = [p for p in self.team_p[team] if p.role == "FWD" and p.state != "out"] or\
             [p for p in self.team_p[team] if p.role != "GK" and p.state != "out"]
        d = self.att[team]
        fw[0].wx, fw[0].wv = sx - d * 4.5, sv
        if len(fw) > 1:
            fw[1].wx, fw[1].wv = sx - d * 6, sv + 15
        b.owner = None
        b.wx, b.wv, b.z, b.vx, b.vv, b.vz = sx, sv, 0.0, 0.0, 0.0, 0.0
        b.last_team = team
        b.last = None
        b.intended = None
        b.tactical_pass = False
        r = self.ref
        r.wx, r.wv, r.vx, r.vv, r.card = sx - 30, sv + 24, 0.0, 0.0, None
        self.restart = dict(kind="kickoff", team=team, pos=(sx, sv), taker=fw[0], t=0.0, ready=False, ready_t=0.0, said=False)
        self.mode = "restart"
        self.foul = self.goal = None
        self.auto_taker(fw[0])
        if sound and self.half_t == 0:
            self.audio.play("whistle")
        for p in self.players:
            self.post_move(p)

    def minute(self):
        return (self.half - 1) * 45 + clamp(self.real_t / self.half_secs, 0.0, 1.0) * 45

    def time_over(self):
        return self.real_t >= self.half_secs

    def update_clock(self, dt):
        if self.mode in ("restart", "outball", "play"):
            if self.mode == "restart" and self.restart and self.restart["kind"] == "kickoff":
                return
            self.real_t += dt
            if self.time_over():
                self.extra += dt
                own = self.ball.owner
                danger = own is not None and (own.wx / L if self.att[own.team] > 0 else 1 - own.wx / L) > 0.72
                extra_minutes = self.extra / max(1.0, self.half_secs) * 45.0
                if extra_minutes >= self.stoppage_target and not danger:
                    if self.mode == "outball":
                        self.outball = None
                    self.end_half()

    def end_half(self):
        self.log_event(tr("ev.end_first" if self.half == 1 else "ev.end_full", a=self.score[0], b=self.score[1]), show=False)
        if self.half == 2:
            self.save_log("finale")
        self.audio.play("whistle_end")
        self.mode = "half" if self.half == 1 else "full"
        self.half_t = 0.0
        self.restart = self.foul = None
        b = self.ball
        b.owner, b.vx, b.vv, b.vz = None, 0.0, 0.0, 0.0
        for p in self.players:
            p.tx = p.tv = None
        self.big = (tr("big.end_first" if self.half == 1 else "big.end_full"), 4.5)
        self.audio.react("whistle_end")
        if self.half == 1:
            self.begin_walkoff()


    def begin_walkoff(self):
        for p in self.players:
            if p.state == "out":
                continue
            p.state, p.act, p.path, p.tx, p.tv = "subout", None, None, None, None
            p.walk, p.limp = "off", False
            self.set_gate(p, -1 if p.team == 0 else 1)

    def begin_walkon(self, team):
        self.setup_kickoff(team, sound=False)
        vexit, cx = _vg(MAX_Y + 30), L / 2.0
        for t in (0, 1):
            for k, p in enumerate([q for q in self.team_p[t] if q.state != "out"]):
                p.wk_to = (p.wx, p.wv)
                p.tx, p.tv = p.wk_to
                self.set_gate(p, -1 if t == 0 else 1)
                p.wx = cx + p.gate
                p.wv = vexit + 7.0 * k + random.uniform(0.0, 2.0)
                p.state, p.walk, p.act, p.path = "subin", "on", None, None
                p.vx = p.vv = 0.0
                self.post_move(p)
        self.mode, self.walk_t = "walkon", 0.0

    def update_walkon(self, dt):
        self.walk_t += dt
        busy = [p for p in self.players if p.state == "subin"]
        if busy and self.walk_t < 25.0:
            return
        for p in busy:
            p.state = "free"
            p.wx, p.wv = p.wk_to
        for p in self.players:
            p.walk = None
            p.tx = p.tv = None
            if p.state != "out":
                p.vx = p.vv = 0.0
            self.post_move(p)
        self.mode = "restart"
        rs = self.restart
        if rs is not None:
            rs["t"], rs["ready"], rs["said"] = 0.0, False, False
            self.auto_taker(rs["taker"])
        self.audio.play("whistle")
        if self.half == 1:
            self.audio.react("start")

    def update_half(self, dt):
        self.half_t += dt
        walking = any(p.state == "subout" for p in self.players)
        if self.half_t > 5.0 and (not walking or self.half_t > 20.0):
            self.instant_subs()
            self.half, self.real_t, self.extra = 2, 0.0, 0.0
            self.stoppage_target = 1.0
            self._gk_press_owner = None
            self._gk_press_idx = None
            self.att = {0: -1, 1: 1}
            self.big = (tr("big.second_half"), 2.5)
            self.half_t = 0.0
            self.begin_walkon(1 - self.first_kick)

    def say(self, text, col=(255, 255, 255), secs=4.0):
        self.msgs.append([text, col, secs])
        del self.msgs[:-4]

    def log_event(self, text, col=None, secs=4.0, show=False, team=None):
        if col is None:
            col = TEAM_COL[team] if team in (0, 1) else (255, 255, 255)
        try:
            stamp = "%dT %02d'" % (self.half, int(self.minute()))
        except Exception:
            stamp = "--"
        self.mlog.append(("[%s] %s" % (stamp, text), col))
        if show:
            self.msgs.append([text, col, secs])
            del self.msgs[:-4]

    def save_log(self, reason="finale"):
        if self.log_saved or not self.mlog or LOG_DIR is None:
            return None
        self.log_saved = True
        bad = '<>:"/\\|?*'
        nm = "%s(%d)-%s(%d)-[%s].log" % (TEAM_NAMES[0], self.score[0], TEAM_NAMES[1], self.score[1], time.strftime("%Y-%m-%d_%H-%M-%S"))
        nm = "".join("_" if c in bad else c for c in nm)
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            path = os.path.join(LOG_DIR, nm)
            with open(path, "w", encoding="utf-8") as f:
                f.write(tr("log.header", reason=tr("log.reason." + reason)) + "\n")
                f.write("%s %d - %d %s\n" % (TEAM_NAMES[0], self.score[0], self.score[1], TEAM_NAMES[1]))
                f.write(tr("log.forms", fa=self.form_names[0], fb=self.form_names[1], sa=self.subs_used[0], sb=self.subs_used[1]) + "\n")
                f.write("-" * 60 + "\n")
                for k, v in self.stats.items():
                    f.write("%-8s %s / %s\n" % (k, ("%.0f" % v[0]) if k == "poss" else v[0], ("%.0f" % v[1]) if k == "poss" else v[1]))
                f.write("-" * 60 + "\n")
                f.write("\n".join(entry[0] if isinstance(entry, tuple) else entry for entry in self.mlog) + "\n")
            return path
        except OSError:
            return None

    def pick_taker(self, kind, team, pos):
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving")]
        out = [p for p in c if p.role != "GK"]
        if kind == "goalkick":
            return next((p for p in c if p.role == "GK"), c[0])
        if kind == "penalty":
            return max(out, key=lambda p: p.skill + (0.15 if p.role == "FWD" else 0))
        near = sorted(out, key=lambda p: math.hypot(p.wx - pos[0], p.wv - pos[1]))
        if self.cp and self.cp.team == team and self.cp in near and self.cp.role != "GK" and\
                math.hypot(self.cp.wx - pos[0], self.cp.wv - pos[1]) < 60:
            return self.cp
        if kind == "free":
            return max(near[:3], key=lambda p: p.skill)
        return near[0]

    @staticmethod
    def visible_pos(pos, margin=9.0):
        px, gy = w2s(pos[0], pos[1])
        if margin <= px <= FW - margin:
            return pos
        return s2w(clamp(px, margin, FW - margin), gy)[0], pos[1]

    def log_missed(self):
        b = self.ball
        if b.shot_team is not None and b.last is not None and b.last.team == b.shot_team:
            self.log_event(tr("ev.missed", p=b.last.label(), team=TEAM_NAMES[b.last.team]), secs=3, team=b.last.team)

    def log_restart_taker(self, p, kind):
        if kind in ("throw", "corner", "free", "penalty", "no_gol"):
            self.log_event(tr("ev.taker." + kind, p=p.label(), team=TEAM_NAMES[p.team]), team=p.team)

    def start_restart(self, kind, team, pos):
        pos = self.visible_pos(pos)
        b = self.ball
        b.owner, b.vx, b.vv, b.vz, b.z = None, 0.0, 0.0, 0.0, 0.0
        b.wx, b.wv = pos
        b.intended = None
        b.tactical_pass = False
        taker = self.pick_taker(kind, team, pos)
        for p in self.players:
            if p.state in ("out", "leaving"):
                continue
            if not p.busy():
                p.state = "free"
            p.tag = None
        self.restart = dict(kind=kind, team=team, pos=pos, taker=taker, t=0.0, ready=False, ready_t=0.0, said=False)
        self.mode = "restart"
        self.foul = None
        if kind == "corner":
            self.stats["corners"][team] += 1
            self.audio.react("corner")
        elif kind == "penalty":
            self.audio.react("tension")
        self.auto_taker(taker)

    def begin_ball_out(self, kind, team, pos):
        b = self.ball
        self.outball = dict(kind=kind, team=team, pos=pos, t=0.0, phase="roll", roll=random.uniform(1.0, 3.0), src=None, fly=0.0)
        b.owner, b.intended, b.shot_team = None, None, None
        b.tactical_pass = False
        b.vz = max(b.vz, 0.0)
        self.mode = "outball"
        self.foul = None
        for p in self.players:
            if p.state not in ("out", "leaving", "action"):
                p.tag, p.tx, p.tv = None, None, None
                if p.state == "cele":
                    p.state = "free"

    def update_outball(self, dt):
        o = self.outball
        b = self.ball
        o["t"] += dt
        if o["phase"] == "roll":
            b.wv = clamp(b.wv, V_TOP - 13.0, V_MAX_P + 8.0)
            if b.wv in (V_TOP - 13.0, V_MAX_P + 8.0) and abs(b.vv) > 8:
                hit_v = abs(b.vv)
                b.vv *= -0.4
                if b.wv == V_TOP - 13.0:
                    self.audio.play("stands", clamp(0.35 + hit_v / 130.0, 0.35, 1.0))
                else:
                    self.audio.play("bounce", 0.5)
            if o["t"] >= o["roll"]:
                o["phase"] = "fly"
                o["src"] = (b.wx, b.wv, b.z)
                o["fly"] = clamp(math.hypot(o["pos"][0] - b.wx, o["pos"][1] - b.wv) / 85.0, 0.7, 1.7)
                o["t"] = 0.0
                b.vx = b.vv = b.vz = 0.0
                tk = self.pick_taker(o["kind"], o["team"], self.visible_pos(o["pos"]))
                o["taker"] = tk
                self.audio.play("kick", 0.45)
        else:
            u = min(1.0, o["t"] / o["fly"])
            sx, sv, sz = o["src"]
            tx, tv = self.visible_pos(o["pos"])
            b.wx, b.wv = sx + (tx - sx) * u, sv + (tv - sv) * u
            b.z = sz * (1.0 - u) + 4.0 * 13.0 * u * (1.0 - u)
            tk = o.get("taker")
            if tk is not None and tk.state not in ("out", "leaving") and not tk.busy():
                self.goto(tk, *self.taker_stand(dict(kind=o["kind"], pos=self.visible_pos(o["pos"]), team=o["team"])))
            if u >= 1.0:
                self.start_restart(o["kind"], o["team"], o["pos"])
                self.outball = None

    def auto_taker(self, taker):
        if self.user_team is not None and taker.team == self.user_team and taker.state not in ("out", "leaving"):
            self.manual = False
            taker.tx = taker.tv = None
            self.idle_t = 0.0
            self.select_player(taker, quiet=True)

    def taker_stand(self, rs):
        kind, (x, v), team = rs["kind"], rs["pos"], rs["team"]
        d = self.att[team]
        if kind == "throw":
            return x, (v - 3.2 if v < V_MID else v + 3.2)
        if kind == "corner":
            return (x - 4.0 if x < L / 2 else x + 4.0), (v + 1.5 if v < V_MID else v - 1.5)
        if kind in ("free", "penalty"):
            gx = L if d > 0 else 0.0
            ux, uv = unit(gx - x, V_GC - v)
            return x - ux * 5.0, v - uv * 5.0
        return x - d * 5.0, v

    def update_restart(self, dt):
        rs = self.restart
        rs["t"] += dt
        tk = rs["taker"]
        if tk.state in ("out", "leaving"):
            rs["taker"] = tk = self.pick_taker(rs["kind"], rs["team"], rs["pos"])
        sx, sv = self.taker_stand(rs)
        if not tk.ctrl or tk.kvec is None:
            if not (tk.ctrl and tk.tx is not None):
                tk.tx, tk.tv = sx, sv
        at = math.hypot(tk.wx - sx, tk.wv - sv) < 3.5 or math.hypot(tk.wx - rs["pos"][0], tk.wv - rs["pos"][1]) < 5.0
        minw = dict(kickoff=1.3, throw=0.8, goalkick=1.3, corner=1.8, free=1.9, penalty=2.4)[rs["kind"]]
        if not rs["ready"] and at and rs["t"] > minw and not tk.busy():
            rs["ready"], rs["ready_t"] = True, rs["t"]
            if rs["kind"] in ("free", "penalty", "corner"):
                self.audio.play("whistle")
            if tk.ctrl:
                self.say(tr("msg.hint_shoot"), (255, 255, 120), 4)
        if rs["ready"] and not tk.busy():
            if rs["t"] - rs["ready_t"] > 0.55 and (not tk.ctrl or self.idle_t > 4.0):
                self.ai_take_restart(tk, rs)
        elif rs["t"] > 14.0 and not tk.busy():
            self.ai_take_restart(tk, rs)

    def call_foul(self, off, victim, yellow_p, red_p):
        b = self.ball
        self.stoppage_target += 0.28
        spot = (clamp(victim.wx, 3.0, L - 3.0), clamp(victim.wv, V_TOP + 1.0, V_BOT - 1.0))
        own_gx = 0.0 if self.att[off.team] > 0 else L
        in_box = in_box_fn(spot[0], spot[1], own_gx)
        card = None
        r = random.random()
        if r < red_p:
            card = "R"
        elif r < red_p + yellow_p:
            card = "Y"
        self.mode = "foul"
        self.foul = dict(off=off, victim=victim, card=card, kind="penalty" if in_box else "free", spot=spot, t=0.0, shown=False)
        b.owner, b.vx, b.vv, b.vz = None, 0.0, 0.0, 0.0
        self.stats["fouls"][off.team] += 1
        self.log_event(tr("ev.foul", off=off.label(), victim=victim.label(), team=TEAM_NAMES[off.team]), team=off.team)
        self.begin_action(victim, "fall", "E" if victim.dx >= 0 else "W")
        for p in self.players:
            if p is not victim and not p.busy():
                p.tx = p.tv = None
        self.audio.play("whistle_long")
        self.audio.play("tackle", 0.9)
        if card or random.random() < 0.5:
            self.audio.react("foul")

    def update_foul(self, dt):
        f = self.foul
        f["t"] += dt
        off = f["off"]
        if f["card"] and not f["shown"] and f["t"] > 1.3:
            f["shown"] = True
            card = f["card"]
            second = False
            if card == "Y":
                off.yellow += 1
                self.stats["yellow"][off.team] += 1
                if off.yellow >= 2:
                    card = "R"
                    f["card"] = "R"
                    second = True
            if card == "R":
                self.stats["red"][off.team] += 1
            self.ref.card, self.ref.card_t = card, 1.8
            if card == "Y":
                ckey, ccol, csecs = "ev.card_yellow", (255, 230, 70), 4
            else:
                ckey, ccol, csecs = ("ev.card_red_second" if second else "ev.card_red"), (255, 90, 90), 5
            self.log_event(tr(ckey, p=off.label(), team=TEAM_NAMES[off.team]), ccol, csecs)
            self.audio.react("card")
        end_t = 3.6 if f["card"] else 2.2
        if f["t"] > end_t and not self.ref.card:
            if f["card"] == "R" or off.yellow >= 2:
                off.red = True
                off.state, off.act = "leaving", None
                self.set_gate(off)
                off.tx, off.tv = L / 2.0 + off.gate, V_MAX_P
                if self.cp is off:
                    self.select_player(None)
            if self.time_over() and f["kind"] != "penalty":
                self.end_half()
                return
            self.start_restart(f["kind"], f["victim"].team, f["spot"])
            if f["kind"] == "penalty":
                own_gx = 0.0 if self.att[off.team] > 0 else L
                px = PEN_D if own_gx == 0.0 else L - PEN_D
                self.ball.wx, self.ball.wv = px, V_PEN
                self.restart["pos"] = (px, V_PEN)
                self.log_event(tr("ev.penalty"), secs=3, team=f["victim"].team)
                self.big = (tr("big.penalty"), 2.0)

    def score_goal(self, team, gx):
        b = self.ball
        self.stoppage_target += 0.45
        self.score[team] += 1
        self.stats["goals"][team] += 1
        own_goal = b.last is not None and b.last.team != team
        if own_goal:
            sc = b.last
        elif b.last is not None and b.last.team == team:
            sc = b.last
        else:
            candidates = [p for p in self.team_p[team] if p.state != "out" and p.role != "GK"]
            sc = min(candidates, key=lambda p: math.hypot(p.wx - b.wx, p.wv - b.wv)) if candidates else self.team_p[team][0]
        kinds = [k for k, w in CELE_KINDS for _ in range(w)]
        self.goal = dict(team=team, scorer=sc, t=0.0, kick=1 - team, own=own_goal, kind=random.choice(kinds), s={}, part=set(),
                         released=False, pairs=None)
        self.mode = "goal"
        if own_goal:
            self.log_event(tr("ev.own_goal", p=sc.label(), own_team=TEAM_NAMES[sc.team], team=TEAM_NAMES[team],
                              a=self.score[0], b=self.score[1]), secs=6, team=team)
        else:
            self.log_event(tr("ev.goal", p=sc.label(), team=TEAM_NAMES[team], a=self.score[0], b=self.score[1]), secs=6, team=team)
        self.last_scorer = sc.name
        b.owner = None
        b.vx *= 0.25
        b.vv *= 0.25
        b.vz = 0.0
        self.big = (tr("big.goal", team=TEAM_NAMES[team]), 4.0)
        self.audio.play("net")
        self.audio.play("whistle")
        self.audio.react("goal")


    def goto(self, p, x, v):
        p.tx, p.tv = clamp(x, 7.0, L - 7.0), clamp(v, V_MIN_P + 1.0, V_BOT - 1.0)

    def pose(self, p):
        p.tx = p.tv = None
        if p.state != "cele":
            p.state = "cele"
            p.cele_t = random.random()

    def cele_pose_if_near(self, p, x, v, r=3.0):
        self.goto(p, x, v)
        if math.hypot(p.wx - x, p.wv - v) < r:
            self.pose(p)

    def cele_huddle(self, g, t, sc, mates):
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.5 and sc.state != "cele":
            self.goto(sc, sc.wx + d * 40, sc.wv)
        else:
            self.pose(sc)
        for p in mates:
            if t > 0.5:
                ang = (p.idx * 2.399) % 6.283
                self.cele_pose_if_near(p, sc.wx + 9 * math.cos(ang), sc.wv + 6 * math.sin(ang), 4.0)

    def cele_slide(self, g, t, sc, mates):
        d = self.att[g["team"]]
        gx = L if d > 0 else 0.0
        top = sc.wv < V_MID
        fx, fv = gx - d * 4.0, (V_TOP + 3.0 if top else V_BOT - 3.0)
        order = sorted(mates, key=lambda q: math.hypot(q.wx - fx, q.wv - fv))
        crew = [sc] + order[:4]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        for i, p in enumerate(mates + [sc]):
            st = g["s"].setdefault(p.idx, {"ph": 0})
            if p.busy():
                continue
            dist = math.hypot(fx - p.wx, fv - p.wv)
            if p in crew:
                k = crew.index(p)
                if st["ph"] == 0:
                    self.goto(p, fx, fv)
                    if dist < 36 and t > 0.3 + 0.28 * k:
                        ux, uv = unit(fx - p.wx, fv - p.wv)
                        self.begin_action(p, "slide", "E" if ux >= 0 else "W", dx=ux, dv=uv, speed=clamp((dist - 4.0) / 0.366, 45.0, 115.0), cele=True, hold=0.54)
                        p.act_cd = 5.0
                        st["ph"] = 1
                elif st["ph"] == 1:
                    st["ph"] = 2
                else:
                    self.cele_pose_if_near(p, fx - d * (2.0 + 2.5 * k), fv + (4.0 * k if top else -4.0 * k) * 0.6, 3.0)
            else:
                ux, uv = unit(p.wx - fx, p.wv - fv)
                self.cele_pose_if_near(p, fx + ux * 55, fv + uv * 55, 4.0)

    def cele_lift(self, g, t, sc, mates):
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.1:
            self.goto(sc, sc.wx + d * 18, sc.wv)
        elif sc.state not in ("cele", "down"):
            self.pose(sc)
        crew = sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
        for k, p in enumerate(crew):
            if p.busy():
                continue
            if k < 4:
                ang = k * math.pi / 2 + 0.6
                self.cele_pose_if_near(p, sc.wx + 4.5 * math.cos(ang), sc.wv + 3.2 * math.sin(ang), 2.5)
            else:
                ang = (p.idx * 2.399) % 6.283
                self.cele_pose_if_near(p, sc.wx + 13 * math.cos(ang), sc.wv + 9 * math.sin(ang), 3.5)
        near = sum(1 for p in crew[:4] if p.state == "cele")
        t0 = 2.0
        if t > t0 and near >= 2 and t < T_CELE - 0.4:
            ph = (t - t0) / 0.95
            sc.state, sc.tx, sc.tv = "down", None, None
            sc.lift = 7.0 + 7.0 * abs(math.sin(math.pi * ph)) ** 0.8
            if ph % 1.0 < 0.05 and int(ph) != g["s"].get("toss"):
                g["s"]["toss"] = int(ph)
                self.audio.play("bounce", 0.4)
        else:
            sc.lift = max(0.0, sc.lift - 40 * 0.0167)

    def cele_train(self, g, t, sc, mates):
        d = self.att[g["team"]]
        gx = L if d > 0 else 0.0
        g["part"] = {p.idx for p in mates} | {sc.idx}
        wps = [(gx - d * 40, V_TOP + 10), (gx - d * 70, V_MID), (gx - d * 40, V_BOT - 10), (gx - d * 95, V_MID)]
        i = g["s"].setdefault("wp", 0)
        wx, wv = wps[i % len(wps)]
        self.goto(sc, wx, wv)
        if math.hypot(sc.wx - wx, sc.wv - wv) < 6:
            g["s"]["wp"] = i + 1
        chain = [sc] + sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
        for k in range(1, len(chain)):
            q, pr = chain[k], chain[k - 1]
            if q.busy():
                continue
            ux, uv = unit(pr.vx, pr.vv, (-d, 0.0))
            self.goto(q, pr.wx - ux * 6.0, pr.wv - uv * 6.0)
            q.speed = max(q.speed, PLAYER_SPEED * 1.0)
        if t > T_CELE - 1.0:
            for p in chain:
                self.pose(p)

    def cele_dance(self, g, t, sc, mates):
        d = self.att[g["team"]]
        g["part"] = {p.idx for p in mates} | {sc.idx}
        if t < 1.0:
            self.goto(sc, sc.wx + d * 14, sc.wv)
        elif not sc.busy() and t < T_CELE - 0.8:
            n = g["s"].get("moon", 0)
            g["s"]["moon"] = n + 1
            sgn = d if n % 2 == 0 else -d
            self.begin_action(sc, "moonwalk", "E" if sgn >= 0 else "W", dx=sgn, dv=0.0, vel=(sgn * 24.0, 0.0), repeat=6)
        elif t >= T_CELE - 0.8 and not sc.busy():
            self.pose(sc)
        for k, p in enumerate(sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))):
            if p.busy():
                continue
            ang = math.pi * (0.35 + 1.3 * k / max(1, len(mates) - 1))
            self.cele_pose_if_near(p, sc.wx + 17 * math.cos(ang), sc.wv + 11 * math.sin(ang) * 0.9, 3.0)

    def cele_brawl(self, g, t, sc, mates):
        if g["pairs"] is None:
            center_x = clamp(L * 0.5 - self.att[g["team"]] * 22.0, L * 0.25, L * 0.75)
            center_v = clamp(V_MID + random.uniform(-8.0, 8.0), V_TOP + 8.0, V_BOT - 8.0)
            g["s"]["brawl_center"] = (center_x, center_v)
            self.goto(sc, center_x, center_v)
            ma = sorted(mates, key=lambda q: math.hypot(q.wx - sc.wx, q.wv - sc.wv))
            grp = [sc] + ma[:5]
            g["pairs"] = [(grp[i], grp[i + 1]) for i in range(0, len(grp) - 1, 2)]
            self.log_event(tr("ev.cele_headbutt"), secs=3, team=g["team"])
            g["part"] = {q.idx for pr in g["pairs"] for q in pr} | {sc.idx}
            g["part"] |= {q.idx for q in mates}
        for k, (a, b2) in enumerate(g["pairs"]):
            st = g["s"].setdefault(("pair", k), {"n": 0, "next": 1.2 + 0.35 * k})
            ang = k * 2.0944 + 0.5
            center_x, center_v = g["s"].get("brawl_center", (sc.wx, sc.wv))
            mx, mv = center_x + 12 * math.cos(ang), center_v + 8 * math.sin(ang)
            ux, uv = unit(math.cos(ang + 1.57), math.sin(ang + 1.57))
            for q, sgn in ((a, -1), (b2, 1)):
                if q.busy() or q is sc and t < 0.0:
                    continue
                if q.state == "cele":
                    q.state = "free"
                if q.role != "GK":
                    self.goto(q, mx + sgn * ux * 2.6, mv + sgn * uv * 1.8)
            if a.busy() or b2.busy():
                continue
            if math.hypot(a.wx - b2.wx, a.wv - b2.wv) < 8.0 and t >= st["next"] and t < T_CELE - 0.3:
                att_, def_ = (a, b2) if st["n"] % 2 == 0 else (b2, a)
                hx, hv = unit(def_.wx - att_.wx, def_.wv - att_.wv)
                self.begin_action(att_, "header", "E" if hx >= 0 else "W", dx=hx, dv=hv, power=0.0, lift=0.0, kind="pass", show=True)
                att_.vx, att_.vv = hx * 36.0, hv * 36.0
                def_.vx, def_.vv = def_.vx + hx * 22.0, def_.vv + hv * 22.0
                self.audio.play("head", 0.55)
                st["n"] += 1
                st["next"] = t + 0.85
                if st["n"] >= 2 and random.random() < 0.30:
                    self.begin_action(def_, "fall", "E" if hx >= 0 else "W")
                    st["next"] = t + 1.6
                    offender = att_ if random.random() < 0.5 else def_
                    if offender.yellow == 0 and not offender.red and random.random() < 0.10:
                        offender.yellow += 1
                        self.stats["yellow"][offender.team] += 1
                        self.ref.card, self.ref.card_t = "Y", 1.4
                        self.log_event(tr("ev.card_brawl", p=offender.label(), team=TEAM_NAMES[offender.team]), (255, 230, 70), 3)
                        self.audio.react("card")

    def update_goal(self, dt):
        g = self.goal
        g["t"] += dt
        t = g["t"]
        sc = g["scorer"]
        team = g["team"]
        if t < 0.05 and not g["own"]:
            sc.state, sc.act = "free", None
        mates = [p for p in self.team_p[team] if p.role != "GK" and p is not sc and p.state not in ("out", "leaving") and not p.red]
        if t > 0.5 and not g["own"] and not g["released"] and sc.state not in ("out", "leaving"):
            if g.get("said") is None:
                g["said"] = True
                self.log_event(tr("ev.cele." + g["kind"]), secs=3, team=g["team"])
            getattr(self, "cele_" + g["kind"])(g, t, sc, mates)
        if t >= T_CELE and not g["released"]:
            g["released"] = True
            for p in self.players:
                p.lift = 0.0
                if p.state in ("cele", "down"):
                    p.state = "free"
        for p in self.players:
            if p.state in ("out", "leaving") or p.busy():
                continue
            if p.state == "cele" and not g["released"]:
                continue
            in_cele = (not g["own"]) and (not g["released"]) and p.idx in g["part"] and p.team == team
            if in_cele and p.role != "GK":
                continue
            hx, hv = self.home_pos(p, L / 2, V_SPOT, False)
            p.tx, p.tv = hx, hv
        done_t = T_CELE + T_AFTER
        if g["own"]:
            done_t = 4.0
        if t > done_t and not g.get("replayed"):
            g["replayed"] = True
            if self.replay_auto:
                if self.start_replay(end_tick=self.tick, secs=self.replay_secs + t + 0.5):
                    return
        if t > done_t + 0.2:
            if self.time_over():
                extra_minutes = self.extra / max(1.0, self.half_secs) * 45.0
                if extra_minutes >= self.stoppage_target:
                    self.end_half()
                    return
            self.log_event(tr("ev.kickoff", team=TEAM_NAMES[g["kick"]]), secs=3, team=g["kick"])
            self.setup_kickoff(g["kick"])

    def teams_at(self, gx):
        a = next(t for t in (0, 1) if self.att[t] == (-1 if gx == 0.0 else 1))
        return a, 1 - a

    def throw_in_out(self):
        b = self.ball
        b.owner = None
        b.out_t = 0.0
        out_dir = -1.0 if b.wv < V_TOP else 1.0
        if b.vv * out_dir < 24.0:
            b.vv = out_dir * 24.0
        team = 1 - b.last_team
        self.begin_ball_out("throw", team, (clamp(b.wx, 8.0, L - 8.0), V_TOP if b.wv < V_TOP else V_BOT))
        self.log_event(tr("ev.throw", team=TEAM_NAMES[team]), secs=2.5, team=team)
        self.audio.play("whistle", 0.6)

    def check_ball_events(self, prev, carried=False, h=0.0):
        b = self.ball
        px, pv, pz = prev
        for gx in (0.0, L):
            crossed = (px >= gx > b.wx) if gx == 0.0 else (px <= gx < b.wx)
            if not crossed:
                continue
            t = (px - gx) / (px - b.wx) if px != b.wx else 0.0
            vc = pv + (b.wv - pv) * t
            zc = pz + (b.z - pz) * t
            off = abs(vc - V_GC)
            att_team, def_team = self.teams_at(gx)
            sgn = 1.0 if gx == 0.0 else -1.0
            if carried:
                if off <= HALF_MOUTH and zc < GOAL_H:
                    self.score_goal(att_team, gx)
                    return
            if zc < GOAL_H + BAR_HI:
                if off <= HALF_MOUTH:
                    if GOAL_H <= zc <= GOAL_H + BAR_HI:
                        self.ball_hits_frame(gx, "bar", vc)
                    elif zc < GOAL_H:
                        self.score_goal(att_team, gx)
                    return
                if off <= HALF_MOUTH + POST_T:
                    if zc <= GOAL_H + BAR_HI:
                        self.ball_hits_frame(gx, "post", vc)
                        return

            if carried:
                b.owner = None
                b.vx = b.vv = b.vz = 0.0
            if b.last_team == def_team:
                x = 1.5 if gx == 0.0 else L - 1.5
                v = V_TOP + 1.5 if b.wv < V_MID else V_BOT - 1.5
                self.begin_ball_out("corner", att_team, (x, v))
                self.log_event(tr("ev.corner", team=TEAM_NAMES[att_team]), secs=3, team=att_team)
            else:
                self.log_missed()
                self.begin_ball_out("goalkick", def_team, (gx + sgn * 0.05 * L, V_GC + random.uniform(-0.5, 0.5) * HALF_MOUTH))
                self.log_event(tr("ev.goalkick", team=TEAM_NAMES[def_team]), secs=3, team=def_team)
            self.audio.play("whistle")
            if b.shot_team is not None:
                self.audio.react("near")
            return
        over = max(V_TOP - b.wv, b.wv - V_BOT)
        if carried:
            if over <= 0.0:
                b.out_t = 0.0
                return
            b.out_t += h
            if math.hypot(self.ref.wx - b.wx, self.ref.wv - b.wv) > REF_NEAR:
                if b.out_t > CARRY_TOL_T or over > CARRY_TOL_V:
                    self.throw_in_out()
            elif over > 0.3:
                self.throw_in_out()
            return
        if over > 0.0:
            self.throw_in_out()

    def ball_hits_frame(self, gx, what, vc):
        b = self.ball
        b.ds = 1.0
        sgn = 1.0 if gx == 0.0 else -1.0
        b.wx = gx + sgn * 0.8
        if what == "bar":
            b.vx = abs(b.vx) * 0.5 * sgn
            b.vz = -abs(b.vz) * 0.4 - 25.0
            b.z = max(0.0, GOAL_H - 2.2)
        else:
            b.vx = abs(b.vx) * 0.55 * sgn
            b.vv = (b.vv * -0.5) + random.uniform(-25, 25)
        self.audio.play("bar" if what == "bar" else "post", 1.0)
        evento = "bar" if what == "bar" else "post"
        if b.last is not None and b.shot_team is not None:
            self.log_event(tr("ev." + evento, p=b.last.label(), team=TEAM_NAMES[b.last.team]), secs=2.5, team=b.last.team)
        else:
            self.log_event(tr("ev." + evento + "_plain"), secs=2.5, team=b.last_team)
        self.audio.react("near")

    def ball_pred(self, t):
        b = self.ball
        if b.owner is not None:
            return b.owner.wx, b.owner.wv
        k = (0.7 if b.z < 1.0 else 0.14) * b.ds
        f = (1 - math.exp(-k * t)) / k
        return b.wx + b.vx * f, b.wv + b.vv * f

    def land_time(self):
        b = self.ball
        if b.z < 0.5 and abs(b.vz) < 5:
            return 0.0
        return max(0.0, (b.vz + math.sqrt(max(0.0, b.vz * b.vz + 2 * G * b.z))) / G)

    def update_ball(self, dt):
        b = self.ball
        n = 2
        h = dt / n
        for _ in range(n):
            prev = (b.wx, b.wv, b.z)
            if b.owner is not None:
                self.dribble(h)
            elif self.mode in ("play", "goal") or (self.mode == "outball" and self.outball["phase"] == "roll"):
                self.free_ball(h)
            self.ball_goal_collide(prev)
            if self.mode == "play":
                if b.owner is None:
                    self.check_ball_events(prev)
                    if self.mode != "play":
                        break
                else:
                    self.check_ball_events(prev, carried=True, h=h)
                    if self.mode != "play":
                        break
                self.check_possession()
        b.age += dt
        if b.age > 2.5:
            b.intended = None
        b.spin += math.hypot(b.vx, b.vv) * dt
        px, gy = w2s(b.wx, b.wv)
        if px < 2.0 or px > FW - 2.0:
            px = clamp(px, 2.0, FW - 2.0)
            b.wx = s2w(px, gy)[0]
            b.vx *= -0.3
        b.px, b.gy = px, gy

    def ball_goal_collide(self, prev):
        b = self.ball
        b.wx, b.wv, hit = self.goal_solid(b.wx, b.wv, prev[0], prev[1], True)
        if hit == 1:
            b.vx = -b.vx * 0.25
        elif hit == 2:
            b.vv = -b.vv * 0.3
        if hit and b.owner is None and abs(b.vx) + abs(b.vv) > 25.0:
            self.audio.play("net", 0.6)
        v0, v1 = V_GC - HALF_MOUTH, V_GC + HALF_MOUTH
        for gx, out in ((0.0, -1.0), (L, 1.0)):
            if 0.0 < out * (b.wx - gx) < GOAL_D and v0 < b.wv < v1 and b.z > GOAL_NET_H:
                b.z = GOAL_NET_H
                b.vz = -abs(b.vz) * 0.3

    def dribble(self, h):
        b = self.ball
        o = b.owner
        if o.state in ("out", "leaving") or o.fallen():
            b.owner = None
            return
        sp = math.hypot(o.vx, o.vv)
        b.own_t += h
        if o.role == "GK":
            off = 1.6
        else:
            off = (DRIBBLE_OFF + 1.7 * math.sin(o.stride * 0.62)) if sp > 8 else 4.5
        tx, tv = o.wx + o.dx * off, o.wv + o.dv * off * 0.8
        k = min(1.0, 16.0 * h)
        b.wx += (tx - b.wx) * k
        b.wv += (tv - b.wv) * k
        b.vx, b.vv, b.vz = o.vx, o.vv, 0.0
        b.ds = 1.0
        if o.role == "GK":
            b.z = 4.0
        elif b.own_t < 1.0:
            b.z = 2.2 * (1.0 - b.own_t) * abs(math.sin(b.own_t * 14.0))
        else:
            b.z = 0.0
        b.last, b.last_team = o, o.team

    def free_ball(self, h):
        b = self.ball
        kk = depth_k(b.wv)
        b.wx += b.vx * h * kk
        b.wv += b.vv * h * kk
        b.z += b.vz * h
        b.vz -= G * h
        if b.z <= 0.0:
            b.z = 0.0
            if b.vz < -35.0:
                if b.vz < -50:
                    self.audio.play("bounce", min(1.0, -b.vz / 110.0))
                b.vz = -b.vz * 0.55
                b.vx *= 0.88
                b.vv *= 0.88
            else:
                b.vz = 0.0
        k = 0.7 if b.z < 0.05 else 0.14
        if self.mode == "goal":
            k = 2.6
        elif self.mode == "outball" and b.z < 0.05:
            k = 0.42
        f = math.exp(-k * h * b.ds)
        b.vx *= f
        b.vv *= f
        if b.z < 0.05 and math.hypot(b.vx, b.vv) < 3.0:
            b.vx = b.vv = 0.0

    def give_ball(self, p):
        b = self.ball
        if p.role == "GK":
            self.log_missed()
        if b.tactical_pass and b.intended is p and b.last is not None and b.last is not p:
            self.log_event(tr("ev.targeted_pass", a=b.last.label(), b=p.label()), secs=2.5, team=b.last.team)
        b.tactical_pass = False
        b.owner = p
        b.last, b.last_team = p, p.team
        b.vx = b.vv = b.vz = 0.0
        b.z = 0.0
        b.own_t = 0.0
        b.intended = None
        b.shot_team = None
        p.hold_t = 0.0
        p.dec = random.uniform(0.15, 0.4)
        p.cool = 0.0

    def check_possession(self):
        b = self.ball
        if b.owner is not None or self.mode != "play":
            return
        best = None
        sp = math.hypot(b.vx, b.vv)
        for p in self.players:
            if p.state in ("out", "leaving") or p.cool > 0:
                continue
            if p.state == "action" and p.act["key"] != "dive":
                continue
            d = math.hypot(p.wx - b.wx, p.wv - b.wv)
            gk = p.role == "GK"
            if d > (10.5 if gk else 7.5) or b.z > (14.0 if gk else 7.5):
                continue
            if sp > 215 and b.intended is not p and not gk and not p.ctrl:
                continue
            if gk and b.last_team != p.team and not p.busy() and p.act_cd <= 0 and (sp > 110 or b.z > 6.0):
                p.act_cd = 0.9
                if random.random() < 0.28 + 0.25 * (1.0 - p.skill) + (0.2 if b.z > 8.0 else 0.0):
                    self.begin_action(p, "punch", "E" if b.wx > p.wx else "W", assist=True)
                    p.cool = 0.5
                    return
            if gk and sp > 230 and b.last_team != p.team and random.random() > 0.25 + 0.6 * p.skill:
                self.gk_parry(p, punch=random.random() < 0.4)
                return
            if best is None or d < best[0]:
                best = (d, p)
        if best:
            p = best[1]
            hot = sp > 150
            self.give_ball(p)
            if hot:
                self.audio.play("head", 0.5)

    def keeper_punch(self, p):
        b = self.ball
        b.ds = 1.0
        if b.owner is not None or math.hypot(b.wx - p.wx, b.wv - p.wv) > 17.0 or b.z > 26.0 or self.mode != "play":
            return False
        d = self.att[p.team]
        side = 1.0 if b.wv >= V_GC else -1.0
        self.log_missed()
        b.vx = d * random.uniform(105.0, 175.0)
        b.vv = side * random.uniform(15.0, 85.0)
        b.vz = random.uniform(38.0, 72.0)
        b.z = max(b.z, 4.0)
        b.last, b.last_team, b.intended = p, p.team, None
        b.shot_team = None
        b.age = 0.0
        p.cool = 0.5
        self.audio.play("head", 0.9)
        self.audio.react("save")
        self.log_event(tr("ev.punch", p=p.label()), secs=2, team=p.team)
        return True

    def gk_parry(self, p, punch=False):
        b = self.ball
        b.ds = 1.0
        d = self.att[p.team]
        if punch:
            b.z = max(b.z, 3.0)
            return self.keeper_punch_free(p)
        self.log_missed()
        if random.random() < 0.35:
            b.vx = -d * max(60.0, abs(b.vx) * 0.3)
            b.vv = random.choice((-1.0, 1.0)) * random.uniform(80, 120)
            b.vz = random.uniform(10, 35)
        else:
            b.vx = d * abs(b.vx) * 0.35
            b.vv = b.vv * 0.5 + random.uniform(-45, 45)
            b.vz = random.uniform(15, 55)
        b.last, b.last_team, b.intended = p, p.team, None
        p.cool = 0.35
        self.audio.play("kick", 0.8)
        self.audio.react("save")
        self.log_event(tr("ev.save", p=p.label()), secs=2, team=p.team)

    def keeper_punch_free(self, p):
        b = self.ball
        b.ds = 1.0
        d = self.att[p.team]
        side = 1.0 if b.wv >= V_GC else -1.0
        self.log_missed()
        b.vx = d * random.uniform(95.0, 160.0)
        b.vv = side * random.uniform(20.0, 90.0)
        b.vz = random.uniform(30.0, 60.0)
        b.last, b.last_team, b.intended = p, p.team, None
        b.shot_team = None
        p.cool = 0.4
        self.audio.play("head", 0.9)
        self.audio.react("save")
        self.log_event(tr("ev.punch", p=p.label()), secs=2, team=p.team)

    @staticmethod
    def goal_solid(x, v, px, pv, ball=False):
        if math.hypot(x - px, v - pv) > 8.0:
            return x, v, 0
        hit = 0
        v0, v1 = V_GC - HALF_MOUTH, V_GC + HALF_MOUTH
        for gx, out in ((0.0, -1.0), (L, 1.0)):
            d, dp = out * (x - gx), out * (px - gx)
            inside_now = 0.0 < d < GOAL_D and v0 < v < v1
            inside_prev = 0.0 < dp < GOAL_D and v0 < pv < v1
            if inside_prev:
                if d >= GOAL_D - 0.4:
                    x, hit = gx + out * (GOAL_D - 0.4), 1
                if v <= v0 + 0.4:
                    v, hit = v0 + 0.4, 2
                elif v >= v1 - 0.4:
                    v, hit = v1 - 0.4, 2
                if d <= 0.0 and not v0 < v < v1:
                    x, hit = gx - out * 0.1, 1
            elif inside_now:
                if dp > 0.0:
                    if pv <= v0:
                        v, hit = v0 - 0.4, 2
                    elif pv >= v1:
                        v, hit = v1 + 0.4, 2
                    else:
                        x, hit = gx + out * (GOAL_D + 0.4), 1
        return x, v, hit

    def clamp_player(self, p):
        vmax = V_MAX_P if (p.state == "leaving" or self.mode != "play") else V_BOT + 0.5
        p.wv = clamp(p.wv, V_MIN_P, vmax)
        if p.lx is not None:
            p.wx, p.wv, _hit = self.goal_solid(p.wx, p.wv, p.lx, p.lv)
        px, gy = w2s(p.wx, p.wv)
        if px < 6.5 or px > FW - 6.5:
            px = clamp(px, 6.5, FW - 6.5)
            p.wx = s2w(px, gy)[0]
        p.lx, p.lv = p.wx, p.wv

    def post_move(self, p):
        p.sx, p.sy = w2s(p.wx, p.wv)
        sp = math.hypot(p.vx, p.vv)
        if sp > 9 and p.state != "action":
            x1, y1 = w2s(p.wx + p.vx * 0.06, p.wv + p.vv * 0.06)
            nd = dir8(x1 - p.sx, y1 - p.sy, True)
            if nd and nd != p.face and p.face_t <= 0:
                p.face, p.face_t = nd, 0.09
            ux, uv = unit(p.vx, p.vv)
            p.dx += (ux - p.dx) * 0.35
            p.dv += (uv - p.dv) * 0.35
            p.dx, p.dv = unit(p.dx, p.dv)

    def desired_velocity(self, p):
        spd = p.speed
        if p.state == "leaving":
            spd *= 0.5
        elif p.role == "GK":
            spd *= 0.62
        if self.ball.owner is p:
            spd *= 0.9
        if p.ctrl and p.kvec:
            return p.kvec[0] * spd * 1.05, p.kvec[1] * spd * 1.05
        if p.tx is None:
            return 0.0, 0.0
        tx, tv = p.tx, p.tv
        if p.state == "leaving":
            tx, tv = self.gate_point(p, V_MAX_P)
        dx, dv = tx - p.wx, tv - p.wv
        d = math.hypot(dx, dv)
        if d < 1.2:
            return 0.0, 0.0
        s = spd * min(1.0, d / 9.0 + 0.15)
        vx, vv = dx / d * s, dv / d * s
        if not p.ctrl:
            for q in self.team_p[p.team]:
                if q is p or q.state == "out":
                    continue
                ex, ev = p.wx - q.wx, p.wv - q.wv
                dd = math.hypot(ex, ev)
                if 0.01 < dd < 12.0:
                    vx += ex / dd * (12.0 - dd) * 2.2
                    vv += ev / dd * (12.0 - dd) * 2.2
        return vx, vv

    def step_player(self, p, dt):
        if p.state == "out":
            return
        if p.cool > 0:
            p.cool -= dt
        if p.act_cd > 0:
            p.act_cd -= dt
        if p.face_t > 0:
            p.face_t -= dt
        if p.state == "action":
            self.step_action(p, dt)
            self.post_move(p)
            return
        if p.state == "down":
            p.vx = p.vv = 0.0
            p.sid = action_sids(p.team, "fall", "W" if "W" in p.face else "E")[-1]
            self.post_move(p)
            return
        if p.state == "tunnel":
            p.vx = p.vv = 0.0
            return
        if p.state in ("subout", "subin"):
            self.step_sub(p, dt)
            return
        dvx, dvv = self.desired_velocity(p)
        if p.ctrl and p.kvec is None:
            k = min(1.0, 22.0 * dt)
        else:
            k = min(1.0, 14.0 * dt)
        p.vx += (dvx - p.vx) * k
        p.vv += (dvv - p.vv) * k
        sp = math.hypot(p.vx, p.vv)
        kk = depth_k(p.wv)
        p.wx += p.vx * dt * kk
        p.wv += p.vv * dt * kk
        self.clamp_player(p)
        p.stride += sp * dt
        self.post_move(p)
        if p.state == "leaving" and p.tv is not None and abs(p.wv - V_MAX_P) < 2.0:
            p.state = "out"
            return
        if p.state == "cele" and sp < 6:
            seq = ACTIONS["cele"]["E"]
            p.cele_t += dt
            p.sid = _off(p.team) + seq[int(p.cele_t / 0.11) % len(seq)]
        elif sp > 9:
            p.still = 0.0
            p.settled = False
            cyc = run_cycle(p.team, p.face)
            p.sid = cyc[int(p.stride / 4.6) % len(cyc)]
        else:
            p.still += dt
            if self.mode != "play" and p.still > 0.15:
                p.face = "E" if self.att[p.team] > 0 else "W"
                p.settled = True
            elif p.still > 0.3 and not p.settled:
                p.face = STOP_FLIP.get(p.face, p.face)
                p.settled = True
            p.sid = stand_sid(p.team, p.face)

    def begin_action(self, p, key, side, **kw):
        if self._preview is not None:
            self._preview.append((p, key, dict(kw)))
            return
        spec = ACT_SPEC[key]
        if key == "punch":
            c = ACTIONS["cele"]["E"]
            seq = [_off(p.team) + c[1], _off(p.team) + c[2], _off(p.team) + c[1], _off(p.team) + c[0]]
        elif key == "throw":
            c = ACTIONS["cele"]["E"]
            seq = [_off(p.team) + c[0], _off(p.team) + c[0], _off(p.team) + c[1]]
        elif kw.get("cele"):
            seq = [_off(p.team) + k for k in CELE_SLIDE[side]]
        else:
            seq = action_sids(p.team, key, side)
        if kw.get("repeat"):
            seq = seq * int(kw["repeat"])
        if p.ctrl:
            p.tx = p.tv = None
        p.state = "action"
        p.vx *= 0.4
        p.vv *= 0.4
        p.face = "E" if side == "E" else "W"
        if "dx" in kw:
            p.dx, p.dv = kw["dx"], kw["dv"]
        hold = kw.get("hold", spec["hold"])
        p.act = dict(key=key, seq=seq, t=0.0, fdur=spec["fdur"], contact=spec["contact"], hold=hold,
                     active=spec.get("active"), fired=False, resolved=False, kw=kw, side=side,
                     dur=len(seq) * spec["fdur"] + hold)
        if key == "fall" and self.ball.owner is p:
            self.ball.owner = None

    def step_action(self, p, dt):
        a = p.act
        a["t"] += dt
        n = len(a["seq"])
        fi = int(a["t"] / a["fdur"])
        p.sid = a["seq"][min(fi, n - 1)]
        key, kw = a["key"], a["kw"]
        if not a["fired"] and fi >= a["contact"]:
            a["fired"] = True
            self.action_contact(p, a)
        if a["active"] and not a["resolved"] and a["active"][0] <= fi <= a["active"][1]:
            if key == "slide":
                self.slide_check(p, a)
            elif key == "dive":
                self.dive_check(p, a)
        if key == "slide":
            f = max(0.0, 1.0 - a["t"] / (a["dur"] * 0.85))
            p.vx, p.vv = kw["dx"] * kw["speed"] * f, kw["dv"] * kw["speed"] * f
        elif key == "dive":
            if 1 <= fi <= 3:
                p.vx, p.vv = 0.0, kw["dv"] * kw["speed"]
            else:
                p.vx *= 0.9
                p.vv *= math.exp(-6 * dt)
        elif kw.get("vel") is not None:
            p.vx, p.vv = kw["vel"]
        else:
            f = math.exp(-6.0 * dt)
            p.vx *= f
            p.vv *= f
            if kw.get("assist") and not a["fired"] and key in ("header", "bicycle") and self.ball.owner is None:
                T = max(0.0, a["contact"] * a["fdur"] - a["t"])
                tx, tv = self.ball_pred(T)
                ux, uv = unit(tx - p.wx, tv - p.wv)
                sp = min(65.0, math.hypot(tx - p.wx, tv - p.wv) / max(T, 0.05))
                p.vx += (ux * sp - p.vx) * 0.6
                p.vv += (uv * sp - p.vv) * 0.6
        kk = depth_k(p.wv)
        p.wx += p.vx * dt * kk
        p.wv += p.vv * dt * kk
        if key == "dive" and p.role == "GK":
            p.wv = clamp(p.wv, V_GC - HALF_MOUTH * 2.2, V_GC + HALF_MOUTH * 2.2)
        self.clamp_player(p)
        if a["t"] >= a["dur"]:
            p.state, p.act = "free", None

    def action_contact(self, p, a):
        key = a["key"]
        if a["kw"].get("show"):
            return
        if key in ("kick", "header", "bicycle"):
            self.try_strike(p, a)
        elif key == "throw":
            self.do_throw(p, a)
        elif key == "punch":
            self.keeper_punch(p)

    def try_strike(self, p, a):
        kw, b, key = a["kw"], self.ball, a["key"]
        if kw.get("tackle"):
            return self.tackle_contact(p, kw)
        setp = self.mode == "restart" and self.restart is not None and self.restart["taker"] is p
        reach, zlo, zhi = {"kick": (11.0, -1.0, 9.5), "header": (11.0, 6.0, 24.0), "bicycle": (13.0, 7.0, 28.0)}[key]
        if kw.get("assist"):
            reach, zlo, zhi = reach + 7.0, (-2.0 if key == "bicycle" else zlo - 3.0), zhi + 8.0
        owned = b.owner is p
        if not owned and not setp:
            d = math.hypot(b.wx - p.wx, b.wv - p.wv)
            if b.owner is not None or d > reach or not (zlo <= b.z <= zhi) or self.mode != "play":
                return False
        dx, dv = kw["dx"], kw["dv"]
        err = kw.get("err", 0.0)
        if err:
            ang = random.gauss(0.0, err)
            dx, dv = dx * math.cos(ang) - dv * math.sin(ang), dx * math.sin(ang) + dv * math.cos(ang)
        power, lift = kw["power"], kw["lift"]
        if key == "header":
            power, lift = power * 0.8, max(lift, 18.0)
        elif key == "bicycle":
            power, lift = max(power, 235.0), max(lift, 28.0)
        b.owner = None
        b.ds = depth_slow(dx, dv)
        b.vx, b.vv, b.vz = dx * power * b.ds, dv * power * b.ds, lift
        b.z = max(b.z, 0.5)
        b.last, b.last_team = p, p.team
        b.intended = kw.get("target")
        b.age = 0.0
        p.cool = 0.4
        kind = kw.get("kind", "pass")
        b.tactical_pass = bool(kw.get("tactical_pass", False) and kind == "pass" and kw.get("target") is not None)
        b.shot_team = p.team if kind == "shot" else None
        if kind == "shot":
            self.stats["shots"][p.team] += 1
            self.audio.react("shot")
        if self.mode == "restart":
            if setp and self.restart is not None:
                self.log_restart_taker(p, self.restart["kind"])
            self.mode, self.restart = "play", None
        self.audio.play("head" if key == "header" else ("kick_hard" if power > 205 else "kick"), 0.5 + min(0.5, power / 400.0))
        return True

    def do_throw(self, p, a):
        kw, b = a["kw"], self.ball
        if not (self.mode == "restart" and self.restart and self.restart["taker"] is p):
            return
        b.wx, b.wv = self.restart["pos"]
        b.z = 12.0
        b.ds = depth_slow(kw["dx"], kw["dv"])
        b.vx, b.vv, b.vz = kw["dx"] * kw["power"] * b.ds, kw["dv"] * kw["power"] * b.ds, kw.get("lift", 40.0)
        b.last, b.last_team, b.intended, b.age, b.owner = p, p.team, kw.get("target"), 0.0, None
        b.tactical_pass = False
        p.cool = 0.5
        self.log_restart_taker(p, self.restart["kind"])
        self.mode, self.restart = "play", None
        self.audio.play("head", 0.5)

    def tackle_contact(self, p, kw):
        b = self.ball
        o = b.owner
        if o is not None and o.team != p.team:
            if math.hypot(o.wx - p.wx, o.wv - p.wv) < 10.5 and (unit(o.wx - p.wx, o.wv - p.wv)[0] * p.dx + unit(o.wx - p.wx, o.wv - p.wv)[1] * p.dv) > -0.3:
                self.resolve_challenge(p, o, "stand")
        elif o is None and self.mode == "play":
            if math.hypot(b.wx - p.wx, b.wv - p.wv) < 10.0 and b.z < 6.0:
                self.poke_ball(p, 100.0)

    def poke_ball(self, p, power):
        b = self.ball
        b.ds = 1.0
        b.vx, b.vv, b.vz = p.dx * power + random.uniform(-20, 20), p.dv * power + random.uniform(-20, 20), random.uniform(0, 20)
        b.last, b.last_team, b.intended, b.age = p, p.team, None, 0.0
        self.audio.play("tackle", 0.7)

    def slide_check(self, p, a):
        b = self.ball
        o = b.owner
        if o is not None and o.team != p.team:
            if math.hypot(o.wx - p.wx, o.wv - p.wv) < 14.0 and not o.fallen():
                a["resolved"] = True
                self.resolve_challenge(p, o, "slide")
            return
        if o is None and self.mode == "play" and math.hypot(b.wx - p.wx, b.wv - p.wv) < 12.0 and b.z < 6.0:
            a["resolved"] = True
            self.poke_ball(p, 130.0)
            return
        if self.mode == "play" and a["t"] > a["fdur"] * 2:
            for q in self.players:
                if q.team != p.team and q.state in ("free",) and math.hypot(q.wx - p.wx, q.wv - p.wv) < 8.0 and q is not o:
                    a["resolved"] = True
                    if random.random() < 0.22 * (0.5 + p.aggr):
                        self.call_foul(p, q, 0.30, 0.02)
                    return

    def resolve_challenge(self, t, o, kind):
        b = self.ball
        if o.role == "GK" and b.owner is o and t.team != o.team and o.hold_t > 1.8:
            ref_near = math.hypot(self.ref.wx - t.wx, self.ref.wv - t.wv) < 24.0
            if ref_near:
                self.call_foul(t, o, 0.95, 0.0)
                self.log_event(tr("ev.gk_danger"), secs=3, team=t.team)
                return
            b.owner = None
            b.z = 0.0
            b.vx, b.vv, b.vz = t.dx * 65.0, t.dv * 45.0, 0.0
            b.last, b.last_team, b.intended = t, t.team, None
            self.log_event(tr("ev.gk_loose"), secs=2.5, team=o.team)
        ux, uv = unit(o.wx - t.wx, o.wv - t.wv)
        away = o.dx * ux + o.dv * uv
        moving = math.hypot(o.vx, o.vv) > 10
        behind = moving and away > 0.4 and (t.dx * ux + t.dv * uv) > 0.3
        win = (0.52 if kind == "stand" else 0.46) + 0.28 * (t.skill - o.skill) - (0.14 if behind else 0.0)
        foul = (0.07 if kind == "stand" else 0.18) + (0.14 if behind else 0.0) + 0.04 * t.aggr
        r = random.random()
        b = self.ball
        if r < win:
            b.owner = None
            sp = random.uniform(55, 110)
            b.vx, b.vv, b.vz = t.dx * sp + random.uniform(-30, 30), t.dv * sp + random.uniform(-30, 30), random.uniform(0, 25)
            b.last, b.last_team, b.intended, b.age = t, t.team, None, 0.0
            o.cool = 0.55
            if random.random() < 0.5:
                self.give_ball(t)
            self.audio.play("tackle", 0.8)
            self.audio.react("tackle")
            self.maybe_injury_from_tackle(o, kind)
        elif r < win + foul:
            yp = 0.07 + (0.22 if kind == "slide" else 0.0) + (0.14 if behind else 0.0)
            rp = 0.003 + (0.035 if (kind == "slide" and behind) else 0.0)
            self.call_foul(t, o, yp, rp)

    def dive_check(self, p, a):
        b = self.ball
        if b.owner is None and b.last_team != p.team and self.mode == "play":
            d = math.hypot(b.wx - p.wx, b.wv - p.wv)
            if d < 15.0 and b.z < GOAL_H + 5:
                a["resolved"] = True
                sp = math.hypot(b.vx, b.vv)
                if sp < 215 and random.random() < 0.35 + 0.55 * p.skill:
                    self.give_ball(p)
                    self.log_event(tr("ev.save", p=p.label()), secs=2, team=p.team)
                    self.audio.play("head", 0.7)
                    self.audio.react("save")
                else:
                    self.gk_parry(p, punch=random.random() < 0.5)

    def start_kick(self, p, dx, dv, power, lift, kind="pass", target=None, err=0.0, tactical_pass=False):
        if p.busy():
            return False
        self.begin_action(p, "kick", "E" if dx >= 0 else "W", dx=dx, dv=dv, power=power, lift=lift, kind=kind, target=target, err=err,
                          tactical_pass=bool(tactical_pass and kind == "pass" and target is not None))
        return True

    def start_aerial(self, p, key, dx, dv, power, lift, kind="pass", err=0.0, target=None, assist=False):
        if p.busy():
            return False
        self.begin_action(p, key, "E" if dx >= 0 else "W", dx=dx, dv=dv, power=power, lift=lift, kind=kind, err=err, target=target,
                          assist=assist)
        p.act_cd = 0.8
        return True

    def start_tackle(self, p, dx, dv, kind):
        if p.busy():
            return False
        if kind == "slide":
            self.begin_action(p, "slide", "E" if dx >= 0 else "W", dx=dx, dv=dv, speed=88.0)
        else:
            self.begin_action(p, "kick", "E" if dx >= 0 else "W", dx=dx, dv=dv, power=0.0, lift=0.0, tackle=True)
        p.act_cd = 0.9
        return True

    def start_dive(self, p, vtarget):
        if p.busy():
            return False
        b = self.ball


        dist = clamp(abs(vtarget - p.wv), 2.0, HALF_MOUTH * 2.2)

        self.begin_action(p, "dive", "E" if b.wx > p.wx else "W", dv=1.0 if vtarget > p.wv else -1.0, speed=dist / 0.437)
        return True

    def start_throw(self, p, dx, dv, power, lift, target=None):
        if p.busy():
            return False
        self.begin_action(p, "throw", "E" if dx >= 0 else "W", dx=dx, dv=dv, power=power, lift=lift, target=target)
        return True

    def lob_lift(self, dist, power, z_t=0.0):
        T = max(0.15, dist / max(40.0, power * 0.82))
        return clamp((z_t + 0.5 * G * T * T) / T, 0.0, 140.0)

    def opponents(self, team):
        return [q for q in self.team_p[1 - team] if q.state not in ("out", "leaving")]

    def waits_for_pass(self, p):
        if self.user_team is None or p.team != self.user_team:
            return False
        b = self.ball
        if b.owner is None and b.intended is p and b.last is not None and b.last.team == p.team:
            return math.hypot(b.wx - p.wx, b.wv - p.wv) > 10.0
        for q in self.team_p[p.team]:
            a = q.act
            if (q is not p and q.state == "action" and a is not None and a["key"] == "kick"
                    and not a["resolved"] and a["kw"].get("target") is p):
                return True
        return False

    def ai_update(self, dt):
        self.role_timer -= dt
        if self.role_timer <= 0:
            self.role_timer = 0.12
            if self.mode in ("play", "restart"):
                self.assign_roles()
        m = self.mode
        b = self.ball
        for p in self.players:
            if p.state in ("out", "action", "leaving", "cele", "down", "subout", "subin"):
                continue
            if m in ("play", "restart") and p.state == "free" and self.waits_for_pass(p):
                p.tx = p.tv = None
                continue
            receiving = b.owner is None and b.intended is p
            if p.ctrl and self.idle_t < IDLE_AI and not p.path:
                continue
            if p.path:
                if m in ("play", "restart") and p.state == "free" and not (m == "restart" and self.restart and self.restart["taker"] is p):
                    if not receiving and self.follow_path(p):
                        continue
                elif m in ("goal", "half", "full"):
                    p.path = None
            if m == "play":
                self.ai_play(p, dt)
            elif m == "restart":
                self.ai_restart(p, dt)
            elif m in ("foul", "half", "full", "subs", "injury"):
                p.tx = p.tv = None
            if p.dec > 0 and m != "play":
                p.dec -= dt

    def mark_pos(self, p, o):
        b = self.ball
        ogx = 0.0 if self.att[p.team] > 0 else L
        gx_, gv_ = unit(ogx - o.wx, V_GC - o.wv)
        bx_, bv_ = unit(b.wx - o.wx, b.wv - o.wv)
        ux, uv = unit(gx_ * 0.7 + bx_ * 0.3, gv_ * 0.7 + bv_ * 0.3)
        return o.wx + ux * MARK_DIST, o.wv + uv * MARK_DIST

    def assign_roles(self):
        old = {id(p): p.tag for p in self.players}
        self._assign_roles0()
        for p in self.players:
            if p.role == "GK":
                continue
            if old[id(p)] is not None and p.tag is None:
                p.new_drift()
            p.drift_t -= 0.12
            p.swap_cd -= 0.12
            if p.drift_t <= 0 and p.tag is None and self.mode != "restart":
                p.new_drift()
        if self.mode == "play":
            for team in (0, 1):
                self.fluid_swaps(team)

    def slot_xy(self, p, slot):
        d = self.att[p.team]
        return (slot["u"] * L if d > 0 else (1 - slot["u"]) * L), V_TOP + slot["w"] * PITCH_W

    def fluid_swaps(self, team):
        ps = [p for p in self.team_p[team] if p.role != "GK" and p.state == "free" and not p.ctrl and p.tag in (None, "support")
              and p.swap_cd <= 0 and not p.red]
        best = None
        for i, a in enumerate(ps):
            sa = dict(role=a.role, u=a.base_u, w=a.base_w, zu=a.zu, zw=a.zw)
            for b2 in ps[i + 1:]:
                if abs(ROLE_ORDER.index(a.role) - ROLE_ORDER.index(b2.role)) > 1:
                    continue
                sb = dict(role=b2.role, u=b2.base_u, w=b2.base_w, zu=b2.zu, zw=b2.zw)
                ax, av = self.slot_xy(a, sa)
                bx, bv = self.slot_xy(b2, sb)
                cur = math.hypot(a.wx - ax, a.wv - av) + math.hypot(b2.wx - bx, b2.wv - bv)
                swp = math.hypot(a.wx - bx, a.wv - bv) + math.hypot(b2.wx - ax, b2.wv - av)
                if cur - swp > 14.0 and swp < cur * 0.72 and (best is None or cur - swp > best[0]):
                    best = (cur - swp, a, b2)
        if best:
            _g, a, b2 = best
            for att in ("role", "base_u", "base_w", "zu", "zw"):
                va, vb = getattr(a, att), getattr(b2, att)
                setattr(a, att, vb)
                setattr(b2, att, va)
            a.swap_cd = b2.swap_cd = random.uniform(7.0, 14.0)
            a.new_drift(0.6)
            b2.new_drift(0.6)

    def _assign_roles0(self):
        b = self.ball
        own = b.owner
        rs = self.restart if self.mode == "restart" else None
        for p in self.players:
            p.tag, p.roam, p.mark = None, False, None
        if rs is not None and rs["kind"] == "kickoff":
            return
        has = rs["team"] if rs is not None else (own.team if own is not None else None)
        if own is not self._gk_press_owner:
            self._gk_press_owner = own
            self._gk_press_idx = None
            if own is not None and own.role == "GK":
                forwards = [q for q in self.team_p[1 - own.team] if q.role == "FWD" and q.state == "free" and not q.ctrl]
                if forwards and random.random() < 0.18:
                    self._gk_press_idx = min(forwards, key=lambda q: math.hypot(q.wx - own.wx, q.wv - own.wv)).idx
        for team in (0, 1):
            cands = [p for p in self.team_p[team] if p.role != "GK" and not p.ctrl and p.state == "free" and p is not own
                     and not (rs is not None and p is rs["taker"])]
            if has == team:
                if own is not None and rs is None:
                    near = [p for p in cands if self.in_zone(p, own.wx, own.wv, 0.14, 0.18)]
                    for p in sorted(near, key=lambda q: math.hypot(q.wx - own.wx, q.wv - own.wv))[:2]:
                        p.tag = "support"
                continue
            if rs is not None:
                px, pv = rs["pos"]
            else:
                px, pv = (own.wx, own.wv) if own is not None else self.ball_pred(0.25)
            pool = list(cands)
            if own is not None and own.role == "GK" and team != own.team:
                for defender in cands:
                    if defender.idx == self._gk_press_idx and defender.role == "FWD":
                        defender.tag = "chase"
                        defender.roam = True
                    else:
                        defender.tx, defender.tv = self.home_pos(defender, own.wx, own.wv, False)
                continue
            if rs is None:
                elig = [p for p in cands if self.in_zone(p, px, pv, 0.05, 0.08)]
                roam = not elig
                sc = sorted(elig or cands, key=lambda q: math.hypot(q.wx - px, q.wv - pv) / q.speed)
                if sc:
                    sc[0].tag, sc[0].roam = "chase", roam
                    pool.remove(sc[0])
                if len(sc) > 1:
                    d1 = math.hypot(sc[1].wx - px, sc[1].wv - pv)
                    if own is None and d1 < 22:
                        sc[1].tag, sc[1].roam = "chase", roam
                        pool.remove(sc[1])
                    elif own is not None and self.team_uw(team, px, pv)[0] < 0.35:
                        sc[1].tag, sc[1].roam = "cover", roam
                        pool.remove(sc[1])
            if rs is not None and rs["kind"] in ("free", "penalty"):
                continue
            targets = [o for o in self.opponents(team) if o.role != "GK" and o is not own and math.hypot(o.wx - px, o.wv - pv) <= MARK_R]
            targets.sort(key=lambda o: math.hypot(o.wx - px, o.wv - pv))
            for o in targets[:MAX_MARK]:
                best = None
                for p in pool:
                    c = math.hypot(p.wx - o.wx, p.wv - o.wv) + (0.0 if self.in_zone(p, o.wx, o.wv, 0.10, 0.12) else 70.0)
                    if best is None or c < best[0]:
                        best = (c, p)
                if best and best[0] < 110.0:
                    best[1].tag, best[1].mark = "mark", o
                    pool.remove(best[1])

    def ai_play(self, p, dt):
        self._ai_play(p, dt)
        b = self.ball
        if p.role == "GK" or b.owner is p or p.roam or p.tx is None or (b.owner is None and b.intended is p):
            return
        p.tx, p.tv = self.zone_clamp(p, p.tx, p.tv, LEASH_U, LEASH_W)

    def _ai_play(self, p, dt):
        b = self.ball
        if p.role == "GK":
            return self.ai_keeper(p, dt)
        if b.owner is p:
            return self.ai_owner(p, dt)
        own = b.owner
        d = self.att[p.team]
        poss = own is not None and own.team == p.team
        if own is None and b.intended is p:
            T = clamp(math.hypot(b.wx - p.wx, b.wv - p.wv) / p.speed, 0.1, 1.4)
            if b.z > 3:
                T = min(T, self.land_time() + 0.05)
            p.tx, p.tv = self.ball_pred(T)
            self.ai_aerial(p)
            return
        tag = p.tag
        if own is None:
            if tag == "chase":
                dist = math.hypot(b.wx - p.wx, b.wv - p.wv)
                T = clamp(dist / p.speed * 0.8, 0.05, 0.9)
                if b.z > 3:
                    T = min(max(T, 0.2), self.land_time() + 0.05)
                p.tx, p.tv = self.ball_pred(T)
                self.ai_aerial(p)
            elif tag == "mark" and p.mark is not None:
                p.tx, p.tv = self.mark_pos(p, p.mark)
            else:
                p.tx, p.tv = self.home_pos(p, b.wx, b.wv, b.last_team == p.team)
            return
        if poss:
            p.dec -= dt
            if tag == "support":
                if p.dec <= 0 or p.tx is None:
                    p.dec = random.uniform(0.6, 1.2)
                    side = 1.0 if p.idx % 2 else -1.0
                    sx = own.wx + d * random.uniform(32, 62)
                    sv = own.wv + side * random.uniform(18, 36)
                    p.tx, p.tv = clamp(sx, 6.0, L - 6.0), clamp(sv, V_TOP + 3, V_BOT - 3)
            else:
                p.tx, p.tv = self.home_pos(p, b.wx, b.wv, True)
            return

        ogx = 0.0 if d > 0 else L
        if tag == "chase":
            dd = math.hypot(own.wx - p.wx, own.wv - p.wv)
            p.tx, p.tv = own.wx + own.dx * 3.0, own.wv + own.dv * 3.0
            p.dec -= dt
            if dd < 13.0 and p.dec <= 0 and p.cool <= 0 and p.act_cd <= 0 and not own.fallen():
                p.dec = random.uniform(0.4, 0.9)
                ux, uv = unit(own.wx - p.wx, own.wv - p.wv)
                r = random.random()
                if r < 0.32:
                    self.start_tackle(p, ux, uv, "stand")
                elif dd > 8.5 and r < 0.32 + 0.03 + 0.06 * p.aggr:
                    self.start_tackle(p, ux, uv, "slide")
        elif tag == "cover":
            ux, uv = unit(ogx - own.wx, V_GC - own.wv)
            p.tx, p.tv = own.wx + ux * 17.0, own.wv + uv * 17.0
        elif tag == "mark" and p.mark is not None:
            p.tx, p.tv = self.mark_pos(p, p.mark)
        else:
            hx, hv = self.home_pos(p, b.wx, b.wv, False)
            if p.role in ("DEF", "MID"):
                thr = None
                for o in self.opponents(p.team):
                    if o.role == "GK" or o is own:
                        continue
                    if math.hypot(o.wx - hx, o.wv - hv) < 42 and (o.wx - p.wx) * d >= -12:
                        if thr is None or math.hypot(o.wx - hx, o.wv - hv) < math.hypot(thr.wx - hx, thr.wv - hv):
                            thr = o
                if thr is not None:
                    ux, uv = unit(ogx - thr.wx, V_GC - thr.wv)
                    hx = hx * 0.35 + (thr.wx + ux * 7.0) * 0.65
                    hv = hv * 0.35 + (thr.wv + uv * 7.0) * 0.65
            p.tx, p.tv = hx, hv

    def ai_aerial(self, p):
        b = self.ball
        if p.busy() or p.act_cd > 0 or b.owner is not None:
            return
        dist = math.hypot(b.wx - p.wx, b.wv - p.wv)
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        togoal = math.hypot(goalx - p.wx, V_GC - p.wv)
        sp = math.hypot(b.vx, b.vv)
        if dist < 9.5 and 8.0 <= b.z <= 20.0 and b.vz < 35:
            if togoal < 90:
                tv = V_GC + random.uniform(-0.7, 0.7) * HALF_MOUTH
                dx, dv = unit(goalx - p.wx, tv - p.wv)
                key = "bicycle" if (b.z > 12 and p.skill > 0.72 and random.random() < 0.35) else "header"
                self.start_aerial(p, key, dx, dv, 205.0, 22.0, "shot", err=(1.05 - p.skill) * 0.12)
            else:
                bp = self.best_pass(p)
                if bp:
                    dx, dv = unit(bp[2] - p.wx, bp[3] - p.wv)
                    self.start_aerial(p, "header", dx, dv, 150.0, 25.0, "pass", err=(1 - p.skill) * 0.1, target=bp[1])
                else:
                    self.start_aerial(p, "header", float(d), 0.0, 170.0, 28.0, "pass", err=0.1)
        elif dist < 9.0 and 1.0 < b.z < 7.0 and sp > 80 and togoal < 85 and b.intended is p and random.random() < 0.5:
            tv = V_GC + random.uniform(-0.7, 0.7) * HALF_MOUTH
            dx, dv = unit(goalx - p.wx, tv - p.wv)
            self.start_kick(p, dx, dv, 250.0, self.lob_lift(togoal, 250.0, 4.0), "shot", err=(1.05 - p.skill) * 0.12)

    def best_pass(self, p, aim=None, cone=0.55):
        d = self.att[p.team]
        opp = self.opponents(p.team)
        best = None
        for q in self.team_p[p.team]:
            if q is p or q.state in ("out", "leaving") or q.fallen():
                continue
            qx, qv = q.wx + q.vx * 0.4, q.wv + q.vv * 0.4
            dist = math.hypot(qx - p.wx, qv - p.wv)
            if dist < 16 or dist > 210:
                continue
            ux, uv = unit(qx - p.wx, qv - p.wv)
            cosv = 1.0
            if aim is not None:
                cosv = ux * aim[0] + uv * aim[1]
                if cosv < cone:
                    continue
            lane = min([seg_dist(o.wx, o.wv, p.wx, p.wv, qx, qv) for o in opp] or [99.0])
            nq = min([math.hypot(o.wx - qx, o.wv - qv) for o in opp] or [99.0])
            if lane < 6.0 and aim is None:
                continue
            score = (qx - p.wx) * d * 0.5 + min(nq, 40) * 0.7 + min(lane, 30) * 0.4 - dist * 0.1 + random.uniform(0, 8)
            if q.role == "GK":
                score -= 30
            if aim is not None:
                score += cosv * 60
            if best is None or score > best[0]:
                best = (score, q, qx, qv)
        return best

    def ai_pass(self, p, bp):
        _s, q, qx, qv = bp
        dist = math.hypot(qx - p.wx, qv - p.wv)
        dx, dv = unit(qx - p.wx, qv - p.wv)
        power = clamp(dist * 1.55 + 55, 95, 250)
        lift = self.lob_lift(dist, power) if (dist > 125 and random.random() < 0.45) else 0.0
        p.tx = p.tv = None
        return self.start_kick(p, dx, dv, power, lift, "pass", target=q, err=(1 - p.skill) * 0.07)

    def ai_shoot(self, p):
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        tv = V_GC + random.uniform(-0.85, 0.85) * HALF_MOUTH
        dx, dv = unit(goalx - p.wx, tv - p.wv)
        dist = math.hypot(goalx - p.wx, tv - p.wv)
        power = random.uniform(225, 285)
        lift = self.lob_lift(dist, power, random.uniform(2.0, 8.0))
        p.tx = p.tv = None
        return self.start_kick(p, dx, dv, power, lift, "shot", err=(1.05 - p.skill) * 0.10)

    def ai_clear(self, p):
        d = self.att[p.team]
        tx = clamp(p.wx + d * 130, 6, L - 6)
        tv = clamp(p.wv + random.uniform(-30, 30), V_TOP + 4, V_BOT - 4)
        dx, dv = unit(tx - p.wx, tv - p.wv)
        dist = math.hypot(tx - p.wx, tv - p.wv)
        p.tx = p.tv = None
        return self.start_kick(p, dx, dv, 245.0, self.lob_lift(dist, 245.0), "pass", err=0.08)

    def ai_owner(self, p, dt):
        d = self.att[p.team]
        goalx = L if d > 0 else 0.0
        p.hold_t += dt
        p.dec -= dt
        if p.dec > 0 and p.tx is not None:
            return
        p.dec = random.uniform(0.18, 0.34)
        opp = self.opponents(p.team)
        near = min(opp, key=lambda q: math.hypot(q.wx - p.wx, q.wv - p.wv))
        press = math.hypot(near.wx - p.wx, near.wv - p.wv)
        to_goal = math.hypot(goalx - p.wx, V_GC - p.wv)
        if to_goal < 105 and p.hold_t > 0.22:
            block = min(seg_dist(o.wx, o.wv, p.wx, p.wv, goalx, V_GC) for o in opp)
            prob = 0.9 if to_goal < 60 else 0.55 if to_goal < 82 else 0.28
            if block < 5:
                prob *= 0.35
            if random.random() < prob:
                return self.ai_shoot(p)
        if p.hold_t > 0.3 and (press < 17 or p.hold_t > 1.1 or random.random() < 0.10):
            bp = self.best_pass(p)
            if bp and (press < 17 or bp[0] > 8):
                return self.ai_pass(p, bp)
        own_u = p.wx / L if d > 0 else 1 - p.wx / L
        if p.role in ("DEF", "MID") and own_u >= p.zu[1] and p.hold_t > 0.3:
            bp = self.best_pass(p)
            if bp:
                return self.ai_pass(p, bp)
        if press < 9 and p.hold_t > 0.25 and own_u < 0.3:
            return self.ai_clear(p)
        if p.hold_t > 3.2:
            return self.ai_clear(p)
        ux, uv = unit(goalx - p.wx, V_GC - p.wv)
        tx, tv = p.wx + ux * 60.0, p.wv + uv * 40.0
        if press < 24 and (near.wx - p.wx) * d > -4:
            side = -1.0 if near.wv > p.wv else 1.0
            tx, tv = p.wx + d * 28.0, p.wv + side * 34.0
        if p.wv < V_TOP + 6:
            tv = max(tv, p.wv + 10)
        if p.wv > V_BOT - 6:
            tv = min(tv, p.wv - 10)
        tx, tv = clamp(tx, 6.0, L - 6.0), clamp(tv, V_TOP + 2, V_BOT - 2)
        ulim = min(1.0, p.zu[1] + LEASH_U)
        xlim = ulim * L if d > 0 else (1.0 - ulim) * L
        tx = min(tx, xlim) if d > 0 else max(tx, xlim)
        p.tx, p.tv = tx, tv

    def ai_keeper(self, p, dt):
        b = self.ball
        d = self.att[p.team]
        own_x = 0.0 if d > 0 else L
        if b.owner is p:
            p.hold_t += dt
            p.tx = p.tv = None
            if p.hold_t > 2.5:
                self.gk_distribute(p)
            return
        toward = -d * b.vx
        if b.owner is None and b.last_team != p.team and toward > 70:
            T = abs(own_x - b.wx) / max(1.0, toward)
            vc = b.wv + b.vv * T
            zc = b.z + b.vz * T - 0.5 * G * T * T
            if T < 1.3 and abs(vc - V_GC) < HALF_MOUTH + 5 and zc < GOAL_H + 3:
                p.tx, p.tv = own_x + d * 4.0, clamp(vc, V_GC - HALF_MOUTH - 3, V_GC + HALF_MOUTH + 3)
                if T < 0.45 and abs(vc - p.wv) > 5 and not p.busy() and p.act_cd <= 0:
                    p.act_cd = 0.9
                    self.start_dive(p, vc)
                return
        dist_b = math.hypot(b.wx - p.wx, b.wv - p.wv)
        in_box = abs(b.wx - own_x) < BOX_D * 0.85 and BOX_V0 <= b.wv <= BOX_V1
        if b.owner is None and in_box and math.hypot(b.vx, b.vv) < 60 and dist_b < 30:
            p.tx, p.tv = self.ball_pred(0.3)
            return
        gcx = own_x + d * 2.0
        ux, uv = unit(b.wx - gcx, b.wv - V_GC)
        r = clamp(0.2 * math.hypot(b.wx - gcx, b.wv - V_GC), 6.0, 28.0)
        tx, tv = gcx + ux * r, V_GC + uv * r * 0.8
        if (tx - own_x) * d < 3.0:
            tx = own_x + d * 3.0
        p.tx, p.tv = tx, clamp(tv, V_GC - HALF_MOUTH - 10, V_GC + HALF_MOUTH + 10)

    def gk_distribute(self, p):
        bp = self.best_pass(p)
        if bp and random.random() < 0.6:
            return self.ai_pass(p, bp)
        return self.ai_clear(p)

    def ai_restart(self, p, dt):
        rs = self.restart
        if rs is None or p is rs["taker"]:
            return
        kind, team = rs["kind"], rs["team"]
        if kind == "kickoff":
            return
        x, v = rs["pos"]
        ad = self.att[team]
        agx = L if ad > 0 else 0.0
        poss = p.team == team
        hx, hv = self.home_pos(p, x, v, poss)
        near_goal = math.hypot(agx - x, V_GC - v) < 130
        if p.role == "GK":
            p.tx, p.tv = hx, hv
            return
        if kind == "corner":
            if poss and p.role in ("MID", "FWD"):
                hx, hv = agx - ad * (8 + (p.idx % 4) * 7), V_GC + ((p.idx % 5) - 2) * HALF_MOUTH * 0.55
            elif not poss and p.role in ("DEF", "MID"):
                hx, hv = agx - ad * (5 + (p.idx % 4) * 6), V_GC + (((p.idx + 2) % 5) - 2) * HALF_MOUTH * 0.55
        elif kind == "penalty":
            hx, hv = agx - ad * (BOX_D + 16 + (p.idx % 3) * 6), V_GC + ((p.idx % 7) - 3) * 10
        elif kind == "free" and not poss and near_goal and p.role != "GK":
            ordered = sorted([q for q in self.team_p[p.team] if q.role != "GK" and q.state not in ("out", "leaving")],
                             key=lambda q: math.hypot(q.wx - x, q.wv - v))[:3]
            if p in ordered:
                ux, uv = unit(agx - x, V_GC - v)
                k = ordered.index(p) - 1
                hx, hv = x + ux * 21.0 - uv * k * 5.0, v + uv * 21.0 + ux * k * 5.0
        elif kind == "free" and poss and near_goal and p.role in ("MID", "FWD"):
            hx, hv = agx - ad * (14 + (p.idx % 4) * 8), V_GC + ((p.idx % 5) - 2) * HALF_MOUTH * 0.6
        if poss and kind == "throw":
            ub, _wb = self.team_uw(team, x, v)
            inward = 1.0 if v < V_MID else -1.0
            mates = sorted([q for q in self.team_p[team] if q is not rs["taker"] and q.role != "GK" and q.state not in ("out", "leaving")],
                           key=lambda q: math.hypot(q.wx - x, q.wv - v))
            if mates and p is mates[0]:
                hx, hv = x - ad * 4.0, v + inward * 17.0
            elif len(mates) > 1 and p is mates[1]:
                hx, hv = x + ad * 17.0, v + inward * 25.0
            elif p.role in ("MID", "FWD"):
                u, w = self.team_uw(team, hx, hv)
                u = clamp(max(u, ub + (0.10 if p.role == "FWD" else 0.04)), p.zu[0], p.zu[1])
                hx = u * L if ad > 0 else (1.0 - u) * L
        elif not poss and p.tag == "mark" and p.mark is not None:
            hx, hv = self.mark_pos(p, p.mark)
        if not poss:
            R = 15.0 if kind == "throw" else 24.0
            dd = math.hypot(hx - x, hv - v)
            if dd < R:
                ux, uv = unit(hx - x, hv - v, (-ad, 0.0))
                hx, hv = x + ux * R, v + uv * R
        p.tx, p.tv = clamp(hx, 6.0, L - 6.0), clamp(hv, V_MIN_P, V_MAX_P)

    def ai_take_restart(self, p, rs):
        if p.busy():
            return
        kind, team = rs["kind"], rs["team"]
        ad = self.att[team]
        agx = L if ad > 0 else 0.0
        x, v = rs["pos"]
        p.tx = p.tv = None
        if kind == "penalty" or (kind == "free" and math.hypot(agx - x, V_GC - v) < 118):
            tv = V_GC + random.choice((-1, 1)) * random.uniform(0.35, 0.85) * HALF_MOUTH
            dx, dv = unit(agx - p.wx, tv - p.wv)
            dist = math.hypot(agx - p.wx, tv - p.wv)
            power = random.uniform(235, 275)
            lift = self.lob_lift(dist, power, random.uniform(2, 6)) + (25 if kind == "free" else 0)
            self.start_kick(p, dx, dv, power, lift, "shot", err=(1.05 - p.skill) * (0.05 if kind == "penalty" else 0.09))
            return
        if kind == "corner":
            tx, tv = agx - ad * random.uniform(10, 26), V_GC + random.uniform(-0.9, 0.9) * HALF_MOUTH * 1.3
            dx, dv = unit(tx - p.wx, tv - p.wv)
            dist = math.hypot(tx - p.wx, tv - p.wv)
            self.start_kick(p, dx, dv, 165.0, self.lob_lift(dist, 165.0, 9.0), "pass", err=0.05)
            return
        if kind == "goalkick":
            return self.ai_clear(p)
        mates = [q for q in self.team_p[team] if q is not p and q.state not in ("out", "leaving") and q.role != "GK"]
        if kind == "throw":
            opp = self.opponents(team)

            def tscore(m):
                dist_ = math.hypot(m.wx - p.wx, m.wv - p.wv)
                free_ = min([math.hypot(o.wx - m.wx, o.wv - m.wv) for o in opp] or [60.0])
                lane_ = min([seg_dist(o.wx, o.wv, p.wx, p.wv, m.wx, m.wv) for o in opp] or [60.0])
                return min(free_, 30) + min(lane_, 20) * 0.6 + (m.wx - p.wx) * ad * 0.12 - abs(dist_ - 40) * 0.25 - (60 if dist_ > 105 else 0)
            q = max(mates, key=tscore)
            dist = math.hypot(q.wx - p.wx, q.wv - p.wv)
            dx, dv = unit(q.wx - p.wx, q.wv - p.wv)
            power = clamp(dist * 1.4 + 40, 80, 170)
            self.start_throw(p, dx, dv, power, self.lob_lift(dist, power, -10.0), q)
            return
        bp = self.best_pass(p)
        if bp:
            self.ai_pass(p, bp)
        else:
            q = min(mates, key=lambda m: math.hypot(m.wx - p.wx, m.wv - p.wv))
            self.ai_pass(p, (0, q, q.wx, q.wv))

    def update_ref(self, dt):
        r, b, m = self.ref, self.ball, self.mode
        if r.card_t > 0:
            r.card_t -= dt
            if r.card_t <= 0:
                r.card = None
        if m == "foul" and self.foul:
            sx, sv = self.foul["spot"]
            tx, tv = sx - 8, sv + (11 if sv < V_MID else -11)
        elif m == "goal":
            tx, tv = L / 2 - 30, V_SPOT + 24
        elif m == "restart" and self.restart:
            x, v = self.restart["pos"]
            tx, tv = x - 12, v + (14 if v < V_MID else -14)
        elif m == "injury" and self.injury:
            q = self.injury["p"]
            tx, tv = q.wx + 6, q.wv + (4 if q.wv < V_MID else -4)
        elif m in ("half", "full", "intro"):
            tx, tv = L / 2 - 30, V_SPOT + 24
        else:
            tx, tv = b.wx - 12, b.wv + (24 if b.wv < V_MID else -24)
        dx, dv = tx - r.wx, tv - r.wv
        dist = math.hypot(dx, dv)
        spd = 48.0 * min(1.0, dist / 20.0)
        if dist > 0.5:
            r.vx += (dx / dist * spd - r.vx) * min(1.0, 6 * dt)
            r.vv += (dv / dist * spd - r.vv) * min(1.0, 6 * dt)
        else:
            r.vx *= 0.8
            r.vv *= 0.8
        r.wx += r.vx * dt
        r.wv = clamp(r.wv + r.vv * dt, V_MIN_P, V_MAX_P)
        px, gy = w2s(r.wx, r.wv)
        if px < 6.5 or px > FW - 6.5:
            r.wx = s2w(clamp(px, 6.5, FW - 6.5), gy)[0]
            px, gy = w2s(r.wx, r.wv)
        r.sx, r.sy = px, gy
        sp = math.hypot(r.vx, r.vv)
        r.stride += sp * dt
        if r.face_t > 0:
            r.face_t -= dt
        if r.card and self.foul:
            fx, fv = self.foul["off"].sx, self.foul["off"].sy
            nd = dir8(fx - px, fv - gy, True)
            if nd and r.face_t <= 0:
                r.face, r.face_t = nd, 0.2
        elif sp > 6:
            x1, y1 = w2s(r.wx + r.vx * 0.06, r.wv + r.vv * 0.06)
            nd = dir8(x1 - px, y1 - gy, True)
            if nd and nd != r.face and r.face_t <= 0:
                r.face, r.face_t = nd, 0.12
        if sp > 6 and not r.card:
            cyc = REF_MOVE[r.face]
            r.sid = cyc[int(r.stride / 5.0) % len(cyc)]
        else:
            r.sid = REF_STAND[r.face]


    @property
    def speed(self):
        return SPEEDS[self.speed_idx] * SPEED_UNIT

    @property
    def speed_label(self):
        return SPEEDS[self.speed_idx]

    def set_view_dims(self):
        d = compute_layout(self.zoom, self.scroll)
        self.vw, self.vh = d["vw"], d["vh"]
        self.view_w, self.view_h, self.W, self.H = d["view_w"], d["view_h"], d["W"], d["H"]
        self.bs, self.bh, self.bar_h = d["bs"], d["bh"], d["bar_h"]
        self.field_y = self.bh
        self.bar_y = self.bh + self.view_h
        self.hud_y = self.bar_y + self.bar_h
        if self.vsurf is None or self.vsurf.get_size() != (self.view_w, self.view_h):
            self.vsurf = pygame.Surface((self.view_w, self.view_h))

    def fit_zoom(self, zoom):
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError, pygame.error):
            dw, dh = 0, 0
        if dw <= 0 or dh <= 0:
            dw, dh = 1920, 1080
        zoom = int(clamp(zoom, 2, 8))
        while zoom > 2:
            d = compute_layout(zoom, self.scroll)
            if d["W"] <= dw * 0.98 and d["H"] <= dh * 0.92:
                break
            zoom -= 1
        return zoom

    def apply_view(self):
        self.zoom = self.fit_zoom(self.zoom)
        self.vsurf = None
        self.paused_gesture = None
        self.paused_traj_surface = None
        self.set_view_dims()
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        try:
            screen = pygame.display.set_mode((int(self.W), int(self.H)), flags)
        except pygame.error:
            screen = pygame.display.set_mode((int(self.W), int(self.H)))
        self.screen = screen
        self.target = screen
        self.update_cam(0.0, True)

    def cam_int(self):
        if not self.scroll:
            return 0, 0
        return int(clamp(self.cam[0], 0, SCROLL_MAX_X)), int(clamp(self.cam[1], 0, SCROLL_MAX_Y))

    def update_cam(self, dt, snap=False):
        if not self.scroll:
            self.cam[0] = self.cam[1] = 0.0
            return
        if self.cam_manual:
            return
        b = self.ball
        px, gy = w2s(b.wx, b.wv)
        tx, ty = px + clamp(b.vx * 0.15, -28, 28), gy + Y_OFFSET + 4 - b.z * 0.4
        if self.mode == "goal" and self.goal and self.goal["t"] > 0.6:
            sc = self.goal["scorer"]
            tx, ty = sc.sx, sc.sy + Y_OFFSET + 6
        elif self.mode == "foul" and self.foul:
            v = self.foul["victim"]
            tx, ty = v.sx, v.sy + Y_OFFSET + 6
        wx = clamp(tx - WIN_W / 2.0, 0, SCROLL_MAX_X)
        wy = clamp(ty - WIN_H / 2.0, 0, SCROLL_MAX_Y)
        k = 1.0 if snap else min(1.0, (16.0 if self.cam_glide > 0.0 else 6.5) * dt)
        if self.cam_glide > 0.0:
            self.cam_glide = max(0.0, self.cam_glide - dt)
        self.cam[0] += (wx - self.cam[0]) * k
        self.cam[1] += (wy - self.cam[1]) * k

    def select_player(self, p, quiet=False):
        if self.cp is p:
            return
        self.paused_gesture = None
        self.paused_traj_surface = None
        if self.cp:
            self.cp.ctrl = False
            self.cp.kvec = None
        self.cp = p
        if p:
            p.ctrl = True
            if not quiet:
                if p.state not in ("subin", "subout"):
                    p.tx = p.tv = None
                self.say(tr("msg.control", name=p.label(), role=p.role), (255, 255, 255), 2.5)

    def select_nearest(self, team, exclude=None):
        b = self.ball
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving") and p is not exclude and p.role != "GK"]
        if c:
            self.select_player(min(c, key=lambda p: math.hypot(p.wx - b.wx, p.wv - b.wv)), quiet=True)

    def auto_select(self):
        ut = self.user_team
        if ut is None or self.mode in ("intro", "half", "full"):
            return
        b = self.ball
        o = b.owner
        if o is not self._last_owner:
            self._last_owner = o
            if o is not None and o.state not in ("out", "leaving"):
                if o.team == ut:
                    if self._poss_prev != ut:
                        self.manual = False
                    if not self.manual and self.cp is not o:
                        self.select_player(o, quiet=True)
                elif self.cp is None:
                    self.select_nearest(ut)
                self._poss_prev = o.team
        if self.cp is None and self.mode in ("play", "restart"):
            self.select_nearest(ut)

    def user_move_input(self):
        p = self.cp
        if p is None:
            return
        if p.state == "out" or p.red:
            self.select_player(None)
            return
        if p.state in ("subin", "subout", "tunnel"):
            return
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        v = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        if x or v:
            p.kvec = unit(float(x), float(v))
            p.tx = p.tv = None
            p.path = None
            self.idle_t = 0.0
        else:
            p.kvec = None

    def screen_to_ground(self, mx, my):
        cx, cy = self.cam_int()
        fx = cx + mx / self.zoom
        row = cy + my / self.zoom
        return fx, row, s2w(fx, row - Y_OFFSET - 10)

    def user_action(self, kind, vec=None, lob=False, inten=None):
        p = self.cp
        if p is None or p.state != "free":
            return
        self.idle_t = 0.0
        b = self.ball
        dx, dv = unit(*(vec or p.kvec or (p.dx, p.dv)))
        d = math.hypot(b.wx - p.wx, b.wv - p.wv)
        have = b.owner is p
        rs = self.restart if self.mode == "restart" else None
        setp = rs is not None and rs["taker"] is p
        if setp and not rs["ready"] and rs["t"] < 1.0:
            return
        if kind in ("moon", "dance", "fall") and not setp:
            return self.user_show(p, kind, dx, dv)
        acro = kind == "acro"
        if acro:
            kind = "long"
        if setp and rs["kind"] == "throw":
            bp = self.best_pass(p, aim=(dx, dv), cone=0.6)
            if bp:
                _s, q, qx, qv = bp
                dist = math.hypot(qx - p.wx, qv - p.wv)
                ddx, ddv = unit(qx - p.wx, qv - p.wv)
                power = clamp(dist * 1.4 + 40, 80, 170)
                self.start_throw(p, ddx, ddv, power, self.lob_lift(dist, power, -10.0), q)
            else:
                self.start_throw(p, dx, dv, 110.0, 45.0)
            return
        ground = have or setp or (self.mode == "play" and b.owner is None and d < REACH_FIRST and b.z < 7.5)
        if ground and inten is not None:
            kp = self.kick_plan(p, dx, dv, inten, lob,
                                self.paused or getattr(self, "_applying_paused_gesture", False))
            tactical_pass = bool(getattr(self, "_applying_paused_gesture", False) and
                                  kp["kind"] == "pass" and kp["target"] is not None)
            self.start_kick(p, kp["dx"], kp["dv"], kp["power"], kp["lift"], kp["kind"],
                            target=kp["target"], tactical_pass=tactical_pass)
            return
        if ground:
            if kind == "short":
                bp = self.best_pass(p, aim=(dx, dv), cone=0.82)
                if bp:
                    _s, q, qx, qv = bp
                    dist = math.hypot(qx - p.wx, qv - p.wv)
                    ddx, ddv = unit(qx - p.wx, qv - p.wv)
                    power = clamp(dist * 1.55 + 55, 95, 250)
                    self.start_kick(p, ddx, ddv, power, self.lob_lift(dist, power) if lob else 0.0, "pass", target=q)
                else:
                    self.start_kick(p, dx, dv, 150.0, 90.0 if lob else 0.0, "pass")
            else:
                goalx = L if self.att[p.team] > 0 else 0.0
                gx, gv = unit(goalx - p.wx, V_GC - p.wv)
                if dx * gx + dv * gv > 0.94:
                    dx, dv = unit(dx * 0.5 + gx * 0.5, dv * 0.5 + gv * 0.5)
                self.start_kick(p, dx, dv, 270.0, 95.0 if lob else 36.0, "shot")
            return
        if p.role == "GK" and self.mode == "play" and b.owner is None and b.z >= 5 and d < 20 and not acro:
            self.begin_action(p, "punch", "E" if b.wx > p.wx else "W", assist=True)
            return
        if self.mode == "play" and b.owner is None and b.z >= 5 and d < 24:
            if b.z < 7.5 and d < 18 and not acro:
                self.start_kick(p, dx, dv, 250.0 if kind == "long" else 160.0, 20.0, "shot" if kind == "long" else "pass")
            elif (acro and b.z >= 5.5) or (kind == "long" and b.z >= 8.0):
                self.start_aerial(p, "bicycle", dx, dv, 255.0, 30.0, "shot", assist=True)
            else:
                self.start_aerial(p, "header", dx, dv, 230.0 if kind == "long" else 150.0, 22.0, "shot" if kind == "long" else "pass", assist=True)
            return
        if acro:
            self.say(tr("msg.need_high_ball"), (255, 220, 140), 2.5)
            return
        if p.role == "GK" and self.mode == "play" and kind == "long":
            self.start_dive(p, p.wv + dv * 20)
            return
        if b.owner is not None and b.owner.team != p.team and vec is None:
            dx, dv = unit(b.owner.wx - p.wx, b.owner.wv - p.wv)
        self.start_tackle(p, dx, dv, "slide" if kind == "long" else "stand")

    def user_show(self, p, kind, dx, dv):
        if kind == "moon":
            self.begin_action(p, "moonwalk", "E" if dx >= 0 else "W", dx=dx, dv=dv, vel=(dx * 22.0, dv * 22.0), repeat=5)
        elif kind == "dance":
            self.begin_action(p, "cele", "E", repeat=5)
        else:
            near = [q for q in self.opponents(p.team) if math.hypot(q.wx - p.wx, q.wv - p.wv) < 10 and not q.busy()]
            if near and self.mode == "play" and random.random() < 0.5:
                self.call_foul(near[0], p, 0.35, 0.02)
            else:
                self.begin_action(p, "fall", "E" if p.dx >= 0 else "W")
                if self.mode == "play" and random.random() < 0.6:
                    self.log_event(tr("ev.dive_fake", p=p.label()), secs=2.5, team=p.team)
                    self.audio.react("foul")

    def set_font_mode(self, modern):
        FONTS.modern = modern
        self.font_s = FONTS.get(22)
        self.font_m = FONTS.get(34)
        self.font_t = FONTS.get(18)
        self.font_l = FONTS.get(72)
        self._fr = {}
        self._help_cache = None

    def abort_match(self):
        self.confirm_exit = False
        self.save_log("interrotta")
        self.replay = None
        self.paused = False
        self.paused_gesture = self.paused_traj_surface = None
        self.sub_menu = None
        self.drag = self.pathdrag = None
        self.show_help = False
        self.help_page = 0
        self.audio.silence()
        self.mode = "intro"

    def draw_exit_dialog(self):
        s = self.screen
        dim = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        s.blit(dim, (0, 0))
        w, h = min(self.W - 40, 560), 190
        box = pygame.Rect(0, 0, w, h)
        box.center = (self.W // 2, self.H // 2)
        pygame.draw.rect(s, (22, 26, 52), box, border_radius=10)
        pygame.draw.rect(s, (214, 218, 238), box, 2, border_radius=10)
        bd = self.board
        bd.put(s, bd.font(40).render(tr("dlg.exit_title"), True, (255, 255, 255)), cx=box.centerx, cy=box.top + 66)
        yes = pygame.Rect(0, 0, 140, 40)
        no = pygame.Rect(0, 0, 140, 40)
        yes.center = (box.centerx - 110, box.bottom - 42)
        no.center = (box.centerx + 110, box.bottom - 42)
        mp = pygame.mouse.get_pos()
        for r, label, col in ((yes, tr("dlg.exit_yes"), (200, 90, 90)), (no, tr("dlg.exit_no"), (90, 170, 110))):
            pygame.draw.rect(s, col if r.collidepoint(mp) else tuple(int(c * 0.6) for c in col), r, border_radius=8)
            pygame.draw.rect(s, (240, 240, 250), r, 2, border_radius=8)
            bd.put(s, bd.font(20).render(label, True, (255, 255, 255)), cx=r.centerx, cy=r.centery)
        self.exit_btns = ((yes, True), (no, False))

    def set_speed(self, idx):
        self.speed_idx = int(clamp(idx, 0, len(SPEEDS) - 1))
        self.say(tr("msg.speed", speed=self.speed_label), (150, 230, 160), 1.8)

    def change_speed(self, delta):
        self.speed_idx = int(clamp(self.speed_idx + delta, 0, len(SPEEDS) - 1))
        self.say(tr("msg.speed", speed=self.speed_label), (150, 230, 160), 1.8)

    def set_scroll(self, on):
        self.scroll = on
        self.cam_manual = False
        self.pan_drag = None
        self.zoom = 5 if on else 3
        self.apply_view()

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            return "quit"
        if ev.type == pygame.KEYDOWN:
            k, uni = ev.key, ev.unicode
            if self.confirm_exit:
                if k in (pygame.K_s, pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.abort_match()
                elif k in (pygame.K_n, pygame.K_ESCAPE):
                    self.confirm_exit = False
                return None
            if k == pygame.K_ESCAPE:
                if self.mode in ("intro", "full"):
                    return "quit"
                self.confirm_exit = True
                return None
            self.idle_t = 0.0
            if self.replay and k in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p):
                self.stop_replay()
                return None
            if k == pygame.K_SPACE and self.mode == "goal" and self.goal:
                self.goal["t"] = T_CELE + T_AFTER + 0.25
                self.goal["released"] = True
                self.goal["replayed"] = True
                for pl in self.players:
                    if pl.state in ("cele", "down"):
                        pl.state, pl.lift = "free", 0.0
                return None
            if self.replay and k not in (pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F11, pygame.K_m, pygame.K_h,
                                         pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_PLUS, pygame.K_MINUS, pygame.K_KP_PLUS,
                                         pygame.K_HOME, pygame.K_END,
                                         pygame.K_KP_MINUS, pygame.K_EQUALS) and uni not in ("+", "-"):
                return None
            if k == pygame.K_F11:
                self.fullscreen = not self.fullscreen
                self.apply_view()
            elif k == pygame.K_F1:
                self.debug = not self.debug
            elif k == pygame.K_F2:
                self.set_scroll(not self.scroll)
            elif k in (pygame.K_F3, pygame.K_F4):
                self.zoom += 1 if k == pygame.K_F4 else -1
                self.apply_view()
            elif k == pygame.K_m:
                self.audio.toggle_mute()
            elif k == pygame.K_h:
                self.help_toggle()
            elif self.mode != "intro" and (k in (pygame.K_F5, pygame.K_F6) or uni in ("[", "]")):
                team = self.user_team if self.user_team is not None else (self.cp.team if self.cp else 0)
                self.change_formation(team, -1 if (k == pygame.K_F5 or uni == "[") else 1)
            elif k in (pygame.K_PAGEUP, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) or uni == "+":
                self.change_speed(+1)
            elif k in (pygame.K_PAGEDOWN, pygame.K_MINUS, pygame.K_KP_MINUS) or uni == "-":
                self.change_speed(-1)
            elif k == pygame.K_HOME:
                self.set_speed(SPEED_DEFAULT)
            elif k == pygame.K_END:
                self.set_speed(len(SPEEDS) - 1)
            elif k == pygame.K_r and self.mode != "intro":
                self.start_replay()
            elif self.mode == "intro":
                self.su_key(k)
            elif self.mode == "full":
                if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.start_match()
                elif k == pygame.K_s:
                    self.mode = "intro"
            elif k in (pygame.K_p, pygame.K_SPACE):
                was_paused = self.paused
                self.paused = not self.paused
                if was_paused and not self.paused and self.paused_gesture is not None:
                    kind, vec, lob, inten = self.paused_gesture
                    self.paused_gesture = None
                    self.paused_traj_surface = None
                    self._applying_paused_gesture = True
                    try:
                        self.user_action(kind, vec, lob, inten)
                    finally:
                        self._applying_paused_gesture = False
            else:
                shift = bool(ev.mod & pygame.KMOD_SHIFT)
                if k == pygame.K_TAB:
                    self.switch_player()
                elif k == pygame.K_q:
                    self.user_team = None
                    self.ctrl_choice = None
                    self.select_player(None)
                    self.say(tr("msg.spectator"), (200, 200, 220), 3)
                elif k == pygame.K_z:
                    self.user_action("short", None, shift)
                elif k == pygame.K_x:
                    self.user_action("long", None, shift)
                elif k == pygame.K_b:
                    self.user_action("acro", None, shift)
                elif k == pygame.K_v:
                    self.user_action("moon", None, shift)
                elif k == pygame.K_c:
                    self.user_action("dance", None, shift)
                elif k == pygame.K_f:
                    self.user_action("fall", None, shift)
        elif ev.type == pygame.MOUSEWHEEL and self.mode == "intro":
            self.su_wheel(ev.y)
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_exit:
                if ev.button == 1:
                    for r, yes in self.exit_btns:
                        if r.collidepoint(ev.pos):
                            if yes:
                                self.abort_match()
                            else:
                                self.confirm_exit = False
                return None
            self.idle_t = 0.0
            if self.replay:
                return None
            if self.mode == "intro":
                if ev.button == 1:
                    self.su_click(ev.pos)
                return None
            x, y = ev.pos
            if self.sub_menu:
                self.sub_menu_click(ev.pos) if ev.button == 1 else setattr(self, "sub_menu", None)
                return None
            if ev.button == 2:
                if self.scroll and self.field_y <= y < self.field_y + self.view_h:
                    self.pan_return_at = 0
                    self.pan_drag = {
                        "start": ev.pos,
                        "cam": tuple(self.cam),
                        "moved": False,
                    }
                return None
            if y < self.field_y:
                if ev.button == 3 and self.mode not in ("half", "full"):
                    for r, pl_ in self.board.hit_rows:
                        if r.collidepoint(ev.pos):
                            self.open_sub_menu(pl_, r)
                            return None
                if ev.button in (1, 3):
                    self.board.click(ev.pos, self)
            elif y < self.field_y + self.view_h:
                my = y - self.field_y
                if ev.button == 3:
                    q = self.path_player_at(x, my) if self.paused else None
                    if q is not None and q.path:
                        q.path = None
                    else:
                        self.pick_at(x, my)
                elif ev.button == 1:
                    ballmod = bool(pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
                    if self.paused and not ballmod and self.paused_gesture is not None:
                        self.paused_gesture = None
                        self.paused_traj_surface = None
                    q = self.path_player_at(x, my) if (self.paused and not ballmod) else None
                    if q is not None:
                        self.pathdrag = dict(p=q, pts=[(q.wx, q.wv)], px=(x, my))
                    else:
                        self.drag = [x, my, x, my]
        elif ev.type == pygame.MOUSEMOTION and self.pan_drag:
            pd = self.pan_drag
            raw_dx = ev.pos[0] - pd["start"][0]
            raw_dy = ev.pos[1] - pd["start"][1]
            if not pd["moved"] and abs(raw_dx) + abs(raw_dy) >= PAN_DEAD_PX:
                pd["moved"] = True
                self.cam_manual = True
                self.cam_glide = 0.0
                self.pan_return_at = 0
            if pd["moved"]:
                dx = raw_dx / float(max(1, self.zoom))
                dy = raw_dy / float(max(1, self.zoom))
                self.cam[0] = clamp(pd["cam"][0] - dx, 0, SCROLL_MAX_X)
                self.cam[1] = clamp(pd["cam"][1] - dy, 0, SCROLL_MAX_Y)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 2:
            if self.pan_drag is not None:
                if not self.pan_drag["moved"] and self.cam_manual:
                    self.cam_manual = False
                    self.cam_glide = CAM_GLIDE_SECS
                    self.pan_return_at = 0
                    self.say(tr("msg.camera_ball"), (200, 220, 255), 1.5)
                    if self.paused:
                        self.update_cam(0.0, True)
                elif self.pan_drag["moved"] and self.cam_manual:
                    self.pan_return_at = (pygame.time.get_ticks() + PAN_HYSTERESIS_MS)
            self.pan_drag = None
        elif ev.type == pygame.MOUSEMOTION and self.pathdrag:
            pd = self.pathdrag
            _fx, _row, (wx, wv) = self.screen_to_ground(ev.pos[0], ev.pos[1] - self.field_y)
            wx, wv = clamp(wx, 4.0, L - 4.0), clamp(wv, V_MIN_P, V_MAX_P)
            if math.hypot(wx - pd["pts"][-1][0], wv - pd["pts"][-1][1]) >= 3.5:
                pd["pts"].append((wx, wv))
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.pathdrag:
            pd, self.pathdrag = self.pathdrag, None
            q = pd["p"]
            moved = math.hypot(ev.pos[0] - pd["px"][0], ev.pos[1] - self.field_y - pd["px"][1])
            if moved < 8 or len(pd["pts"]) < 2:
                self.pick_player(q)
            else:
                q.path = pd["pts"][1:]
                q.tag = None
                self.say(tr("msg.path_assigned", name=q.name, n=len(q.path)), (255, 255, 255), 2.0)
        elif ev.type == pygame.MOUSEMOTION and self.drag:
            self.drag[2], self.drag[3] = ev.pos[0], ev.pos[1] - self.field_y
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.drag:
            x0, y0 = self.drag[0], self.drag[1]
            self.drag = None
            self.idle_t = 0.0
            self.finish_gesture(x0, y0, ev.pos[0], ev.pos[1] - self.field_y, pygame.key.get_mods())
        return None

    def su_scale(self):
        sc = min(self.W / float(SU_W), self.H / float(SU_H))
        return sc, (self.W - SU_W * sc) / 2.0, (self.H - SU_H * sc) / 2.0

    def su_to_virtual(self, pos):
        sc, ox, oy = self.su_scale()
        return (pos[0] - ox) / sc, (pos[1] - oy) / sc

    def su_show(self, c):
        rows = 15
        self.su_scroll[c] = int(clamp(self.su_scroll[c], self.sel[c] - rows + 1, self.sel[c]))
        self.su_scroll[c] = int(clamp(self.su_scroll[c], 0, max(0, len(self.teams) - rows)))

    def su_wheel(self, dy):
        vx, _vy = self.su_to_virtual(pygame.mouse.get_pos())
        c = 0 if vx < SU_W / 2 else 1
        self.su_scroll[c] = int(clamp(self.su_scroll[c] - dy * 3, 0, max(0, len(self.teams) - 15)))

    def su_click(self, pos):
        vx, vy = self.su_to_virtual(pos)
        if self.lang_open and not any(r.collidepoint(vx, vy) and t[0] in ("lang", "lang_toggle") for r, t in self.su_hits):
            self.lang_open = False
            return
        for r, tag in self.su_hits:
            if r.collidepoint(vx, vy):
                if tag[0] == "lang_toggle":
                    self.lang_open = not self.lang_open
                    if self.lang_open:
                        self.langs = T.discover_languages()
                elif tag[0] == "lang":
                    self.lang_open = False
                    self.set_language(tag[1])
                elif tag[0] == "team":
                    self.sel[tag[1]] = tag[2]
                    self.su_active = tag[1]
                    self.team_data[tag[1]] = self.teams[tag[2]]
                    self.fix_lineup(tag[1], reset=True)
                    self.su_pick = None
                elif tag[0] == "slot":
                    self.su_pick = None if self.su_pick == (tag[1], tag[2]) else (tag[1], tag[2])
                elif tag[0] == "cand":
                    c, i = self.su_pick
                    role = self.lineup_slots(c)[i][0]
                    start = [k for k, (r, _n) in enumerate(self.lineup_slots(c)) if r == role][0]
                    self.lineup[c][role][i - start] = tag[1]
                    self.su_pick = None
                elif tag[0] == "replay_auto":
                    self.replay_auto = not self.replay_auto
                elif tag[0] == "replay_secs":
                    self.replay_secs = tag[1]
                elif tag[0] == "font":
                    self.set_font_mode(tag[1])
                elif tag[0] == "form":
                    self.set_formation(tag[1], tag[2])
                    self.su_active = tag[1]
                elif tag[0] == "half":
                    self.half_secs = tag[1]
                elif tag[0] == "ctrl":
                    self.user_team = tag[1]
                    self.ctrl_choice = tag[1]
                elif tag[0] == "start":
                    self.start_match()
                return
        self.su_pick = None

    def su_key(self, k):
        c = self.su_active
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.start_match()
        elif k == pygame.K_TAB:
            self.su_active = 1 - c
        elif k in (pygame.K_UP, pygame.K_DOWN):
            self.sel[c] = int(clamp(self.sel[c] + (1 if k == pygame.K_DOWN else -1), 0, len(self.teams) - 1))
            self.team_data[c] = self.teams[self.sel[c]]
            self.fix_lineup(c, reset=True)
            self.su_pick = None
            self.su_show(c)
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            self.change_formation(c, 1 if k == pygame.K_RIGHT else -1)
        elif k in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.half_secs = {pygame.K_1: 60.0, pygame.K_2: 120.0, pygame.K_3: 180.0, pygame.K_4: 300.0}[k]
        elif k == pygame.K_t:
            self.user_team = {0: 1, 1: None, None: 0}[self.user_team]

    def switch_player(self):
        team = self.cp.team if self.cp else (self.user_team if self.user_team is not None else
                                             (self.ball.last_team if self.ball.last_team in (0, 1) else 0))
        self.user_team = team
        self.manual = True
        b = self.ball
        c = [p for p in self.team_p[team] if p.state not in ("out", "leaving") and p is not self.cp and p.role != "GK"]
        if c:
            self.select_player(min(c, key=lambda p: math.hypot(p.wx - b.wx, p.wv - b.wv)))

    def pick_at(self, mx, my):
        if mx < 0 or my < 0 or mx >= self.view_w or my >= self.view_h:
            return
        fx, row, _w = self.screen_to_ground(mx, my)
        best = None
        for p in self.players:
            if p.state == "out":
                continue
            dd = math.hypot(p.sx - fx, (p.sy + Y_OFFSET + 5) - row)
            if dd < 20 and (best is None or dd < best[0]):
                best = (dd, p)
        if best:
            self.pick_player(best[1])

    def finish_gesture(self, x0, y0, x1, y1, mods):
        if x0 < 0 or y0 < 0 or x0 >= self.view_w or y0 >= self.view_h:
            return
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        p = self.cp
        if p is None:
            return
        if ln < 12:
            fx, row, (wx, wv) = self.screen_to_ground(x1, y1)
            p.tx, p.tv = wx, clamp(wv, V_MIN_P, V_MAX_P)
            p.path = None
            self.click_mark = [fx, row, 2.0]
            return
        plan = self.gesture_plan(x0, y0, x1, y1)
        if plan is None:
            return
        lob = bool(mods & pygame.KMOD_SHIFT) and not (mods & pygame.KMOD_CTRL)
        if self.paused and (mods & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL)):
            self.paused_gesture = (plan[0], plan[1], lob, plan[2])
            old_target = self.target
            preview = pygame.Surface((self.view_w, self.view_h), pygame.SRCALPHA)
            self.target = preview
            self.draw_shot_preview(x0, y0, x1, y1, lob)
            self.target = old_target
            self.paused_traj_surface = preview
            return
        self.user_action(plan[0], plan[1], lob, plan[2])

    def intensity(self):
        b = self.ball
        if self.mode == "goal":
            return 1.0
        near = max(0.0, 1.0 - min(b.wx, L - b.wx) / 110.0)
        return clamp(0.15 + 0.7 * near * (0.5 + 0.5 * min(1.0, math.hypot(b.vx, b.vv) / 200.0)), 0.0, 1.0)

    def update(self, dt):
        if self.mode == "intro":
            self.update_cam(dt, True)
            return
        self.t_all += dt
        self.idle_t += dt
        self.audio.focus = clamp((self.ball.wx - L / 2.0) / (L / 2.0), -1.0, 1.0)
        self.update_clock(dt)
        if self.mode == "play" and self.ball.owner is not None:
            self.stats["poss"][self.ball.owner.team] += dt
        if self.mode == "restart":
            self.update_restart(dt)
        elif self.mode == "foul":
            self.update_foul(dt)
        elif self.mode == "goal":
            self.update_goal(dt)
        elif self.mode == "outball":
            self.update_outball(dt)
        elif self.mode == "subs":
            self.update_subs(dt)
        elif self.mode == "injury":
            self.update_injury(dt)
        elif self.mode == "half":
            self.update_half(dt)
        elif self.mode == "walkon":
            self.update_walkon(dt)
        if self.mode == "restart" and self.restart is not None:
            self.maybe_ai_subs()
            rs = self.restart
            if any(self.sub_q) and not rs["ready"] and not rs["taker"].busy():
                self.begin_subs()
        if self.mode == "play":
            self.update_injuries(dt)
        self.update_flags(dt)
        self.auto_select()
        self.ai_update(dt)
        self.user_move_input()
        for p in self.players:
            self.step_player(p, dt)
        if self.mode in ("play", "goal", "restart", "foul", "half", "full", "outball"):
            self.update_ball(dt)
        self.update_ref(dt)
        self.update_cam(dt)
        self.rec.append((self.tick, self.snapshot(), (self.cam[0], self.cam[1])))
        self.tick += 1
        self.audio.update(dt, self.intensity())
        for m in self.msgs:
            m[2] -= dt
        self.msgs = [m for m in self.msgs if m[2] > 0]
        if self.big:
            self.big = (self.big[0], self.big[1] - dt)
            if self.big[1] <= 0:
                self.big = None
        if self.click_mark:
            self.click_mark[2] -= dt
            if self.click_mark[2] <= 0:
                self.click_mark = None

    def text(self, s, font, col, pos, center=False, shadow=True):
        img = font.render(s, True, col)
        r = img.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        if shadow:
            self.target.blit(font.render(s, True, (0, 0, 0)), r.move(2, 2))
        self.target.blit(img, r)

    def img_to_screen(self, ix, iy):
        cx, cy = self.cam_int()
        return (ix - cx) * self.zoom, (iy - cy) * self.zoom

    def start_replay(self, end_tick=None, secs=None):
        frames = list(self.rec)
        if end_tick is not None:
            frames = [f for f in frames if f[0] <= end_tick]
        n = int((secs or self.replay_secs) * 60)
        frames = frames[-n:]
        if len(frames) < 30:
            self.say(tr("msg.replay_short"), (255, 200, 120), 2.5)
            return False
        self.replay = dict(frames=frames, i=0)
        self.cam[0], self.cam[1] = frames[0][2]
        if self.replay_auto:
            self.save_tore([f[1] for f in frames])
        return True

    def save_tore(self, snaps):
        try:
            path = tore_next_path(self.tore_dir)
            with open(path, "wb") as fh:
                fh.write(tore_build(snaps, self.last_scorer, fps=getattr(self.args, "tore_fps", None)))
            self.say(tr("msg.replay_saved", path=path), (150, 230, 160), 4)
            return path
        except (OSError, ValueError) as ex:
            self.say(tr("msg.save_failed", reason=ex), (255, 150, 120), 4)
            return None

    def replay_step(self):
        r = self.replay
        r["i"] += 1
        if r["i"] >= len(r["frames"]):
            self.stop_replay()
        else:
            self.cam[0], self.cam[1] = r["frames"][r["i"]][2]

    def stop_replay(self):
        self.replay = None
        self.update_cam(0.0, True)

    def draw_replay_badge(self):
        r = self.replay
        s = self.target
        size = max(70, int(self.view_h * 0.30))
        f = self._fr.get(size)
        if f is None:
            f = self._fr[size] = FONTS.get(size)
        if int(pygame.time.get_ticks() / 400) % 2 == 0:
            img = f.render("R", True, (236, 30, 30))
            edge = f.render("R", True, (0, 0, 0))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                s.blit(edge, (16 + dx, 8 + dy))
            s.blit(img, (16, 8))
        self.text(tr("hud.replay"), self.font_m, (255, 255, 255), (16 + int(size * 0.55), 14))
        prog = (r["i"] + 1) / float(len(r["frames"]))
        pygame.draw.rect(s, (0, 0, 0), (0, self.view_h - 7, self.view_w, 7))
        pygame.draw.rect(s, (236, 30, 30), (0, self.view_h - 6, int(self.view_w * prog), 5))

    def snapshot(self):
        b = self.ball
        bpx, bgy = w2s(b.wx, b.wv)
        if b.owner is not None and b.owner.role != "GK":
            bgy += 1.0
        r = self.ref
        return (tuple((p.sx, p.sy - p.lift, p.sid, p.state != "out") for p in self.players),
                (r.sx, r.sy, r.sid, r.card),
                (bpx, bgy, b.z, BALL_ROT[int(b.spin / 3.0) % len(BALL_ROT)]),
                tuple(f.screen() for f in self.flags))

    def draw_field(self, snap=None):
        s = self.field_surf
        s.blit(self.gfx.field, (0, 0))
        s.blit(self.gfx.crowd_frame(), (0, 0))
        snap = snap or self.snapshot()
        pl, rf, bl = snap[:3]
        flags = snap[3] if len(snap) > 3 else ()
        bpx, bgy, bz, bsid = bl
        items = [(sy, 2, "p", (sx, sy, sid)) for sx, sy, sid, vis in pl if vis]
        items += [(bgy, 0, "s", None), (bgy, 1, "b", None), (rf[1], 2, "r", rf)]
        for goal_img in self.gfx.goals:
            items.append((GOAL_Y1, 3, "g", goal_img))
        items += [(fl[1] - FIELD_ROW0, 2, "f", fl) for fl in flags]
        items.sort(key=lambda t: (t[0], t[1]))
        for _k, _r, kind, p in items:
            if kind == "f":
                self.draw_flag(s, p)
            elif kind == "p":
                s.blit(self.gfx.sprite(p[2]), (int(round(p[0])) - 6, int(round(p[1])) + Y_OFFSET))
            elif kind == "r":
                s.blit(self.gfx.sprite(rf[2]), (int(round(rf[0])) - 6, int(round(rf[1])) + Y_OFFSET))
            elif kind == "s":
                sy_ = max(int(round(bgy)) + 3 + Y_OFFSET, FIELD_ROW0 - 2 - self.gfx.shadow_top)
                s.blit(self.gfx.sprite(145), (int(round(bpx)) - 2, sy_))
            elif kind == "b":
                s.blit(self.gfx.sprite(bsid), (int(round(bpx)) - 2, int(round(bgy + 3 - bz)) + Y_OFFSET))
            else:
                s.blit(p[0], p[1])
        if rf[3]:
            cx, cy = int(round(rf[0])) + 4, int(round(rf[1])) + Y_OFFSET - 8
            pygame.draw.rect(s, (0, 0, 0), (cx - 1, cy - 1, 6, 8))
            pygame.draw.rect(s, (255, 220, 0) if rf[3] == "Y" else (230, 30, 30), (cx, cy, 4, 6))
        if snap is None and self.click_mark:
            x, y = int(self.click_mark[0]), int(self.click_mark[1])
            pygame.draw.line(s, (255, 255, 255), (x - 2, y), (x + 2, y))
            pygame.draw.line(s, (255, 255, 255), (x, y - 2), (x, y + 2))
        if self.debug:
            self.draw_debug(s)

    def draw_flag(self, s, fl):
        bx, by, tx, ty, sg = fl
        pygame.draw.line(s, (240, 240, 240), (int(round(bx)), int(round(by))), (int(round(tx)), int(round(ty))))
        ux, uy = unit(tx - bx, ty - by, (0.0, -1.0))
        nx, ny = -uy * sg, ux * sg
        pts = [(tx, ty), (tx - ux * 3.2, ty - uy * 3.2), (tx - ux * 1.6 + nx * 4.2, ty - uy * 1.6 + ny * 4.2)]
        pygame.draw.polygon(s, (230, 40, 40), [(int(round(x)), int(round(y))) for x, y in pts])

    def draw_debug(self, s):
        def pl(pts, col):
            pygame.draw.lines(s, col, False, [ground_to_img(*p) for p in pts], 1)
        pl(_wline((0, V_TOP), (L, V_TOP)) + _wline((L, V_TOP), (L, V_BOT)) + _wline((L, V_BOT), (0, V_BOT)) + _wline((0, V_BOT), (0, V_TOP)), (255, 255, 0))
        pl(_wline((L / 2, V_TOP), (L / 2, V_BOT)), (255, 255, 0))
        for x0, sg in ((0, 1), (L, -1)):
            pl([(x0, V_GC - HALF_MOUTH), (x0, V_GC + HALF_MOUTH)], (0, 255, 255))
            pl([(x0, BOX_V0), (x0 + sg * BOX_D, BOX_V0), (x0 + sg * BOX_D, BOX_V1), (x0, BOX_V1)], (255, 120, 0))
            pl([(x0, GA_V0), (x0 + sg * GA_D, GA_V0), (x0 + sg * GA_D, GA_V1), (x0, GA_V1)], (255, 60, 200))
        cp = self.cp
        if cp and cp.state != "out":
            d = self.att[cp.team]
            xa, xb = [(u * L if d > 0 else (1 - u) * L) for u in cp.zu]
            va, vb = V_TOP + cp.zw[0] * PITCH_W, V_TOP + cp.zw[1] * PITCH_W
            pl(_wline((xa, va), (xb, va), 12) + _wline((xb, va), (xb, vb), 12) + _wline((xb, vb), (xa, vb), 12) + _wline((xa, vb), (xa, va), 12),
               (120, 255, 120))
        for p in self.players:
            if p.state != "out" and p.tx is not None:
                pygame.draw.line(s, TEAM_COL[p.team], ground_to_img(p.wx, p.wv), ground_to_img(p.tx, p.tv), 1)

    def draw(self):
        if self.mode == "intro":
            self.target = self.screen
            self.screen.fill((10, 12, 28))
            self.draw_intro()
            return
        for p in self.players:
            if p.sx == 0 and p.sy == 0:
                self.post_move(p)
        rp = self.replay
        self.draw_field(rp["frames"][min(rp["i"], len(rp["frames"]) - 1)][1] if rp else None)
        cx, cy = self.cam_int()
        view = self.field_surf.subsurface(pygame.Rect(cx, cy, self.vw, self.vh))
        self.screen.fill((6, 6, 12))
        vs = self.vsurf
        pygame.transform.scale(view, (self.view_w, self.view_h), vs)
        self.target = vs
        if not rp:
            self.draw_marker()
        if self.paused and not rp:
            self.draw_tactics()
        if self.drag and self.cp and not rp:
            x0, y0, x1, y1 = self.drag
            ln = math.hypot(x1 - x0, y1 - y0)
            if ln > 6:
                f_ = self.gesture_intensity(ln)
                col = (255, int(255 - 110 * f_), int(255 - 225 * f_))
                pygame.draw.line(vs, col, (x0, y0), (x1, y1), 3)
                pygame.draw.circle(vs, col, (x1, y1), 6, 2)
                if self.paused:
                    md = pygame.key.get_mods()
                    self.draw_shot_preview(x0, y0, x1, y1, bool(md & pygame.KMOD_SHIFT) and not (md & pygame.KMOD_CTRL))
        if self.paused and self.paused_traj_surface is not None and not self.drag and not rp:
            vs.blit(self.paused_traj_surface, (0, 0))
        if self.big and not rp:
            self.text(self.big[0], self.font_l, (255, 255, 255), (self.view_w // 2, self.view_h // 3), True)
        if self.mode in ("half", "full") and not rp:
            self.draw_summary()
        if rp:
            self.draw_replay_badge()
        if self.show_help:
            self.draw_help()
        self.target = self.screen
        self.screen.blit(vs, (0, self.field_y))
        pygame.draw.rect(self.screen, (214, 218, 238), (0, self.field_y, self.view_w, self.view_h), 2)
        self.board.draw(self.screen, self, self.W, self.bh)
        self.board.draw_bar(self.screen, self, self.bar_y, self.W, self.bar_h)
        self.draw_hud()
        if self.sub_menu:
            self.draw_sub_menu()
        if self.confirm_exit:
            self.draw_exit_dialog()

    def draw_marker(self):
        cp = self.cp
        if not cp or cp.state == "out":
            return
        z = self.zoom
        sx, sy = self.img_to_screen(cp.sx, cp.sy + Y_OFFSET)
        bob = math.sin(self.t_all * 7.0) * 0.5 * z
        tip = (sx, sy - 0.6 * z + bob)
        pts = [(tip[0] - 1.9 * z, tip[1] - 3.6 * z), (tip[0] + 1.9 * z, tip[1] - 3.6 * z), tip]
        pygame.draw.polygon(self.target, (255, 215, 0), pts)
        pygame.draw.polygon(self.target, (0, 0, 0), pts, max(2, z // 2))

    def draw_tactics(self):
        z = self.zoom
        size = (self.view_w, self.view_h)
        ov = getattr(self, "_tactics_overlay", None)
        if ov is None or ov.get_size() != size:
            ov = pygame.Surface(size, pygame.SRCALPHA)
            self._tactics_overlay = ov
        else:
            ov.fill((0, 0, 0, 0))

        camx, camy = self.cam_int()
        def P(wx, wv):
            ix, iy = ground_to_img(wx, wv)
            return (ix - camx) * z, (iy - camy) * z

        def arrow(a, b, col, w=3):
            pygame.draw.line(ov, col, a, b, w)
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            h = 4 * z / 2.0 + 5
            pygame.draw.polygon(ov, col, [b,
                (b[0] - h * math.cos(ang - 0.45), b[1] - h * math.sin(ang - 0.45)),
                (b[0] - h * math.cos(ang + 0.45), b[1] - h * math.sin(ang + 0.45))])

        for p in self.players:
            if p.state == "out":
                continue
            col = TEAM_COL[p.team]
            radius = p.speed * 0.6
            pts = [P(p.wx + radius * math.cos(a * math.pi / 12),
                     p.wv + radius * math.sin(a * math.pi / 12)) for a in range(24)]
            pygame.draw.polygon(ov, col + (16,), pts)
            pygame.draw.polygon(ov, col + (120,), pts, 1)
            speed = math.hypot(p.vx, p.vv)
            length = 12 + speed * 0.45
            arrow(P(p.wx, p.wv), P(p.wx + p.dx * length, p.wv + p.dv * length), col + (255,))
            if p.tx is not None and p.tv is not None:
                a, dest = P(p.wx, p.wv), P(p.tx, p.tv)
                pygame.draw.line(ov, col + (120,), a, dest, 1)
                pygame.draw.circle(ov, col + (230,), (int(dest[0]), int(dest[1])), max(3, z), 2)

        paths = [(p, [(p.wx, p.wv)] + list(p.path))
                 for p in self.players if p.path and p.state != "out"]
        pd = self.pathdrag
        if pd and len(pd["pts"]) >= 2:
            paths.append((pd["p"], list(pd["pts"])))
        for player, pts in paths:
            col = TEAM_COL[player.team]
            screen_pts = [P(*pt) for pt in pts]
            if len(screen_pts) >= 2:
                pygame.draw.lines(ov, col + (230,), False, screen_pts, 3)
                for pt in screen_pts[1:]:
                    pygame.draw.circle(ov, col + (255,), (int(pt[0]), int(pt[1])), max(2, z // 2))
                arrow(screen_pts[-2], screen_pts[-1], col + (255,), 3)

        b = self.ball
        prev = P(b.wx, b.wv)
        for i in range(1, 7):
            nxt = P(*self.ball_pred(i * 0.25))
            pygame.draw.circle(ov, (255, 255, 255, 220), (int(nxt[0]), int(nxt[1])), max(2, z // 2))
            pygame.draw.line(ov, (255, 255, 255, 110), prev, nxt, 1)
            prev = nxt

        self.target.blit(ov, (0, 0))
        for p in self.players:
            if p.state == "out":
                continue
            fx, fy = P(p.wx, p.wv)
            self.text(str(p.num), self.font_t, TEAM_COL[p.team], (fx, fy - 11.5 * z), True)

    def draw_tactics_panel(self):
        surf = self.screen
        x, y = 8, self.hud_y + 2
        bw = min(540, max(180, self.W // 2 - 14))
        bh = HUD_H - 4
        pygame.draw.rect(surf, (30, 34, 52), (x, y, bw, bh))
        pygame.draw.rect(surf, (112, 122, 172), (x, y, bw, bh), 1)
        title_font = ScaledFont(FONTS.flow, 2) if FONTS.flow is not None else self.font_s
        self.text(tr("hud.tactical"), title_font, (255, 215, 0), (x + 8, y + 3), False, False)
        rows = (tr("hud.tactical_1"), tr("hud.tactical_2"), tr("hud.tactical_3"))
        for i, line in enumerate(rows):
            self.text(line, self.font_t, (220, 220, 230), (x + 8, y + 21 + i * 13), False, False)

    def draw_action_log(self):
        if not self.mlog or FONTS.flow is None:
            return
        font = ScaledFont(FONTS.flow, 2)
        maxw = max(100, self.W - 100)
        y0 = self.hud_y + 8
        for i, (entry, col) in enumerate(self.mlog[-3:]):
            line = entry.split("] ", 1)[-1]
            original = line
            while line and font.size(line)[0] > maxw:
                line = line[:-1]
            if line != original and len(line) > 3:
                line = line[:-3] + "..."
            self.text(line, font, col, (10, y0 + i * 20), False, False)

    def draw_hud(self):
        y = self.hud_y
        pygame.draw.rect(self.screen, (22, 24, 34), (0, y, self.W, HUD_H))
        if not self.replay:
            if self.paused:
                self.draw_tactics_panel()
            else:
                self.draw_action_log()
        margin = 8
        available = self.W - margin * 2
        yy = y + 3
        for t, col, _s in self.msgs[-3:]:
            line = t
            while line and self.font_s.size(line)[0] > available:
                line = line[:-1]
            if line != t and len(line) > 3:
                line = line[:-3] + "..."
            text_w = self.font_s.size(line)[0]
            self.text(line, self.font_s, col, (self.W - margin - text_w, yy), shadow=False)
            yy += 18

    def overlay(self, alpha=190):
        o = pygame.Surface((self.view_w, self.view_h), pygame.SRCALPHA)
        o.fill((0, 0, 0, alpha))
        self.target.blit(o, (0, 0))
        return self.view_w, self.view_h

    def su_chip(self, s, r, label, active, hover, col=(120, 130, 210), px=18):
        bd = self.board
        pygame.draw.rect(s,tuple(int(v * 0.5) for v in col) if active else (30, 34, 66),r,border_radius=6,)
        pygame.draw.rect(s,(255, 224, 90) if active else (col if hover else (70, 78, 130)),r,2,border_radius=6,)
        t = bd.font(px).render(label, True, (255, 255, 255) if active else (190, 196, 230))
        bd.put(s, t, cx=r.centerx, cy=r.centery)

    def draw_intro(self):
        s = self.su_surf
        s.fill((10, 12, 28))
        bd = self.board
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        W = SU_W
        bd.put(s, bd.font(58).render(tr("intro.title"), True, (232, 236, 255)), cx=W // 2, cy=32)
        bd.put(s, bd.font(24).render(tr("intro.subtitle"), True, bd.LIT), cx=W // 2, cy=68)
        note = " | ".join(n.text() for n in self.notes[:2]) if self.notes else ""
        warn = any(n.warn for n in self.notes)
        bd.put(s, bd.font(14).render(self.fit_text(note, 16, W - 40), True, (255, 170, 110) if warn else (130, 140, 190)), cx=W // 2, cy=92)
        names_ctl = (tr("intro.team_home"), tr("intro.team_away"))
        for c in (0, 1):
            x0 = 30 + c * 495
            col = TEAM_COL[c]
            hb = pygame.Rect(x0, 108, 465, 28)
            pygame.draw.rect(s, tuple(int(v * 0.55) for v in col), hb, border_radius=5)
            if self.su_active == c:
                pygame.draw.rect(s, (255, 224, 90), hb, 2, border_radius=5)
            bd.put(s, bd.font(21).render(names_ctl[c], True, (255, 255, 255)), cx=hb.centerx, cy=hb.centery)

            lr = pygame.Rect(x0, 142, 232, 360)
            pygame.draw.rect(s, bd.BG, lr)
            sc0 = int(clamp(self.su_scroll[c], 0, max(0, len(self.teams) - 15)))
            self.su_scroll[c] = sc0
            s.set_clip(lr)
            for i in range(15):
                idx = sc0 + i
                if idx >= len(self.teams):
                    break
                rr = pygame.Rect(x0, 142 + i * 24, 226, 24)
                if idx == self.sel[c]:
                    pygame.draw.rect(s, tuple(int(v * 0.6) for v in col), rr)
                elif rr.collidepoint(vx, vy):
                    pygame.draw.rect(s, (36, 44, 92), rr)
                t = bd.font(20).render(self.fit_text(self.teams[idx]["name"], 20, 212), True, (255, 255, 255) if idx == self.sel[c] else bd.WHITE)
                bd.put(s, t, left=x0 + 8, cy=rr.centery)
                hits.append((rr, ("team", c, idx)))
            s.set_clip(None)
            if len(self.teams) > 15:
                th = max(18, int(360 * 15 / len(self.teams)))
                ty = 142 + int((360 - th) * sc0 / float(len(self.teams) - 15))
                pygame.draw.rect(s, (80, 90, 150), (x0 + 226, ty, 5, th), border_radius=2)
            pygame.draw.rect(s, bd.FRAME, lr, 2)

            td = self.teams[self.sel[c]]
            px0 = x0 + 248
            lg = pygame.Rect(px0, 142, 110, 110)
            pygame.draw.rect(s, (8, 10, 24), lg)
            img = self.gfx.logo(td["logo"])
            if img is not None:
                k = min(98.0 / img.get_width(), 98.0 / img.get_height())
                im = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
                s.blit(im, im.get_rect(center=lg.center))
            pygame.draw.rect(s, bd.FRAME, lg, 3)

            mp = pygame.Rect(px0 + 118, 142, 98, 110)
            pygame.draw.rect(s, (40, 104, 48), mp)
            pygame.draw.rect(s, (220, 226, 220), mp, 1)
            pygame.draw.line(s, (220, 226, 220), (mp.left, mp.top + 2), (mp.right, mp.top + 2), 1)
            pygame.draw.arc(s, (220, 226, 220), (mp.left + 28, mp.top - 20, 42, 40), math.pi, 2 * math.pi, 1)
            for sl in formation_slots(self.form_names[c]):
                pygame.draw.circle(s, col, (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16))), 5)
                pygame.draw.circle(s, (250, 250, 250), (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16))), 5, 1)
            bd.put(s, bd.font(26).render(self.fit_text(td["name"].upper(), 26, 215), True, (232, 236, 255)), left=px0, cy=270)
            for i, fname in enumerate(FORMATIONS):
                r = pygame.Rect(px0 + (i % 3) * 72, 290 + (i // 3) * 33, 66, 28)
                self.su_chip(s, r, fname, self.form_names[c] == fname, r.collidepoint(vx, vy), col)
                hits.append((r, ("form", c, fname)))
            rows = (len(FORMATIONS) + 2) // 3
            ry = 290 + rows * 33 + 8
            bd.put(s, bd.font(16).render(tr("intro.starters"), True, bd.DIM), left=px0, top=ry)
            slots = self.lineup_slots(c)
            for i, (role, ni) in enumerate(slots):
                rr = pygame.Rect(px0 + (i // 6) * 110, ry + 18 + (i % 6) * 17, 108, 16)
                sel = self.su_pick == (c, i)
                if sel:
                    pygame.draw.rect(s, tuple(int(v * 0.6) for v in col), rr, border_radius=3)
                elif rr.collidepoint(vx, vy):
                    pygame.draw.rect(s, (36, 44, 92), rr, border_radius=3)
                nm = td["players"][ni] if ni < len(td["players"]) else ""
                bd.put(s, bd.font(15).render(ROLE_LETTER[role], True, bd.DIM), left=rr.left + 2, cy=rr.centery)
                bd.put(s, bd.font(15).render(self.fit_text(nm or "-", 15, 90), True, bd.WHITE), left=rr.left + 14, cy=rr.centery)
                hits.append((rr, ("slot", c, i)))
            if self.su_pick and self.su_pick[0] == c:
                pi = self.su_pick[1]
                role = slots[pi][0]
                lo, hi = ROLE_POOLS[role]
                used = set(self.lineup[c][role])
                cands = [n for n in range(lo, hi) if n not in used]
                ph = 30 + max(1, len(cands)) * 22
                pr = pygame.Rect(px0 - 6, 286, 222, ph)
                pygame.draw.rect(s, (14, 18, 44), pr, border_radius=6)
                pygame.draw.rect(s, (255, 224, 90), pr, 2, border_radius=6)
                lab = tr("role.long." + role)
                bd.put(s, bd.font(16).render(tr("intro.pick_new", role=lab), True, bd.DIM), left=pr.left + 8, top=pr.top + 5)
                if not cands:
                    bd.put(s, bd.font(17).render(tr("intro.no_other"), True, bd.LIT), left=pr.left + 10, top=pr.top + 28)
                pops = []
                for k2, ni in enumerate(cands):
                    cr = pygame.Rect(pr.left + 4, pr.top + 26 + k2 * 22, pr.w - 8, 21)
                    if cr.collidepoint(vx, vy):
                        pygame.draw.rect(s, (46, 56, 112), cr, border_radius=3)
                    nm = td["players"][ni] if ni < len(td["players"]) else ""
                    bd.put(s, bd.font(18).render(self.fit_text("%s" % (nm or "-"), 18, pr.w - 24), True, bd.WHITE), left=cr.left + 6, cy=cr.centery)
                    pops.append((cr, ("cand", ni)))
                hits[0:0] = pops

        bd.put(s, bd.font(20).render(tr("intro.half_len"), True, bd.LIT), left=30, cy=526)
        for i, m in enumerate((1, 2, 3, 5)):
            r = pygame.Rect(330 + i * 54, 512, 46, 28)
            self.su_chip(s, r, str(m), abs(self.half_secs - m * 60.0) < 1, r.collidepoint(vx, vy))
            hits.append((r, ("half", m * 60.0)))
        bd.put(s, bd.font(20).render(tr("intro.controls"), True, bd.LIT), left=30, cy=564)
        for i, (lab, val) in enumerate(((tr("intro.ctrl_home"), 0), (tr("intro.ctrl_away"), 1), (tr("intro.ctrl_spec"), None))):
            r = pygame.Rect(330 + i * 150, 550, 142, 28)
            self.su_chip(s, r, lab, self.user_team == val, r.collidepoint(vx, vy))
            hits.append((r, ("ctrl", val)))
        bd.put(s, bd.font(20).render(tr("intro.replay_auto"), True, bd.LIT), left=30, cy=602)
        r = pygame.Rect(400, 588, 70, 28)
        self.su_chip(s, r, tr("intro.on") if self.replay_auto else tr("intro.off"), self.replay_auto, r.collidepoint(vx, vy), (90, 200, 120))
        hits.append((r, ("replay_auto",)))
        bd.put(s, bd.font(20).render(tr("intro.replay_secs"), True, bd.LIT), left=530, cy=602)
        for i, m in enumerate((3, 5, 8, 10, 15)):
            r = pygame.Rect(690 + i * 54, 588, 46, 28)
            self.su_chip(s, r, str(m), self.replay_secs == m, r.collidepoint(vx, vy))
            hits.append((r, ("replay_secs", m)))
        bd.put(s, bd.font(20).render(tr("intro.font"), True, bd.LIT), left=30, cy=660)
        for i, (lab, val) in enumerate(((tr("intro.font_modern"), True), (tr("intro.font_old"), False))):
            r = pygame.Rect(110 + i * 112, 646, 104, 28)
            self.su_chip(s, r, lab, FONTS.modern == val, r.collidepoint(vx, vy))
            hits.append((r, ("font", val)))
        sb = pygame.Rect(W // 2 - 140, 636, 280, 46)
        hov = sb.collidepoint(vx, vy)
        pygame.draw.rect(s, (60, 150, 90) if hov else (44, 112, 70), sb, border_radius=8)
        pygame.draw.rect(s, (200, 255, 210), sb, 2, border_radius=8)
        bd.put(s, bd.font(28).render(tr("intro.start"), True, (255, 255, 255)), cx=sb.centerx, cy=sb.centery)
        hits.append((sb, ("start",)))
        bd.put(s, bd.font(20).render(tr("intro.footer"), True, (110, 118, 160)), cx=W // 2, cy=708)
        self.draw_lang_dropdown(s, bd, hits, vx, vy)
        sc, ox, oy = self.su_scale()
        out = pygame.transform.smoothscale(s, (int(SU_W * sc), int(SU_H * sc)))
        self.screen.blit(out, (int(ox), int(oy)))

    def draw_lang_dropdown(self, s, bd, hits, vx, vy):
        if not self.langs:
            return
        cur = T.current_language()
        names = dict(self.langs)
        btn = pygame.Rect(SU_W - 30 - 160, 12, 160, 26)
        lab = bd.font(16).render(tr("intro.language"), True, bd.DIM)
        bd.put(s, lab, left=btn.left - lab.get_width() - 8, cy=btn.centery)
        pygame.draw.rect(s, (30, 34, 66), btn, border_radius=6)
        edge = (255, 224, 90) if self.lang_open else ((120, 130, 210) if btn.collidepoint(vx, vy) else (70, 78, 130))
        pygame.draw.rect(s, edge, btn, 2, border_radius=6)
        shown = self.fit_text(names.get(cur, cur.upper()), 18, btn.w - 36)
        bd.put(s, bd.font(18).render(shown, True, (255, 255, 255)), left=btn.left + 8, cy=btn.centery)
        ax, ay = btn.right - 15, btn.centery
        arrow = [(ax - 5, ay + 3), (ax + 5, ay + 3), (ax, ay - 3)] if self.lang_open else [(ax - 5, ay - 3), (ax + 5, ay - 3), (ax, ay + 3)]
        pygame.draw.polygon(s, (190, 196, 230), arrow)
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
            bd.put(s, bd.font(18).render(self.fit_text(name, 18, cr.w - 12), True, bd.WHITE), left=cr.left + 6, cy=cr.centery)
            pops.append((cr, ("lang", code)))
        hits[0:0] = pops

    def set_language(self, code):
        if T.set_language(code):
            self._help_cache = None
            pygame.display.set_caption(tr("app.caption"))
            for detail in T.take_problems():
                self.notes.append(Note("note.lang_problem", True, detail=detail))

    def fit_text(self, text, px, maxw):
        return self.board.fit(text, self.board.font(px), maxw)

    def draw_summary(self):
        W, _H = self.overlay(150)
        title = tr("sum.half") if self.mode == "half" else tr("sum.full")
        self.text(title, self.font_l, (255, 255, 255), (W // 2, 70), True)
        self.text("%s %d - %d %s" % (TEAM_NAMES[0], self.score[0], self.score[1], TEAM_NAMES[1]), self.font_m, (255, 255, 255), (W // 2, 120), True)
        st = self.stats
        tot = max(0.001, st["poss"][0] + st["poss"][1])
        rows = [(tr("sum.poss"), "%d%%" % round(100 * st["poss"][0] / tot), "%d%%" % round(100 * st["poss"][1] / tot)),
                (tr("sum.shots"), st["shots"][0], st["shots"][1]), (tr("sum.fouls"), st["fouls"][0], st["fouls"][1]),
                (tr("sum.yellow"), st["yellow"][0], st["yellow"][1]), (tr("sum.red"), st["red"][0], st["red"][1]),
                (tr("sum.corners"), st["corners"][0], st["corners"][1])]
        y = 170
        for name, a, b in rows:
            self.text(str(a), self.font_m, TEAM_COL[0], (W // 2 - 150, y), True)
            self.text(name, self.font_s, (230, 230, 240), (W // 2, y), True)
            self.text(str(b), self.font_m, TEAM_COL[1], (W // 2 + 150, y), True)
            y += 34
        if self.mode == "full":
            self.text(tr("sum.hint"), self.font_s, (255, 230, 120), (W // 2, y + 18), True)

    HELP_LAYOUT = (
        (("mf", 7), ("mb", 3)),
        (("kg", 11), ("pt", 4)),
        (("view", 6), ("other", 5)),
    )

    @classmethod
    def help_columns(cls):
        return tuple(
            tuple(
                (tr("help.%s.title" % sec),
                 tuple((tr("help.%s.%d.k" % (sec, i)), tr("help.%s.%d.d" % (sec, i))) for i in range(1, n + 1)))
                for sec, n in col)
            for col in cls.HELP_LAYOUT)

    @staticmethod
    def _wrap(text, font, maxw):
        lines, cur = [], ""
        for word in text.split(" "):
            trial = word if not cur else cur + " " + word
            if cur and font.size(trial)[0] > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines or [""]

    def _help_layout(self, px, W, H, cols=None):
        f = FONTS.get(px)
        tf = FONTS.get(int(px * 1.35))
        m = max(10, W // 50)
        gap = max(10, W // 60)
        cols = self.help_columns() if cols is None else cols
        cw = (W - 2 * m - (len(cols) - 1) * gap) // len(cols)
        lh = f.size("Ag")[1] + max(1, px // 8)
        sec_gap = lh // 2
        top = m + tf.size("Ag")[1] + max(6, px // 2)
        draws, worst = [], 0
        for ci, sections in enumerate(cols):
            x0 = m + ci * (cw + gap)
            y = top
            for title, entries in sections:
                draws.append(("title", title, x0, y, cw, tf))
                y += tf.size("Ag")[1] * 0 + f.size("Ag")[1] + max(4, px // 4)
                draws.append(("rule", None, x0, y - max(2, px // 8), cw, None))
                for key, desc in entries:
                    kl = self._wrap(key, f, int(cw * 0.46))
                    kw = int(cw * 0.46)
                    dl = self._wrap(desc, f, cw - kw - max(6, px // 2))
                    n = max(len(kl), len(dl))
                    for li in range(n):
                        if li < len(kl):
                            draws.append(("key", kl[li], x0, y + li * lh, kw, f))
                        if li < len(dl):
                            draws.append(("desc", dl[li], x0 + kw + max(6, px // 2), y + li * lh, cw - kw, f))
                    y += n * lh + max(2, px // 6)
                y += sec_gap
            worst = max(worst, y)
        return worst <= H - m, draws, m, tf

    HELP_MIN_PX = 11

    @classmethod
    def help_sections(cls):
        return [sec for col in cls.help_columns() for sec in col]

    def help_pages(self):
        return len(self.HELP_LAYOUT)

    def help_toggle(self):
        if self.show_help and self.help_page < self.help_pages() - 1:
            self.help_page += 1
        else:
            self.show_help = not self.show_help
            self.help_page = 0


    def draw_help(self):
        W, H = self.overlay(236)
        page = getattr(self, "help_page", 0)
        key = (W, H, page, T.current_language())
    
        cache = getattr(self, "_help_cache", None)
        if cache is None or cache[0] != key:
            help_cols = self.help_columns()
            chosen, paged = None, True
            page_cols = tuple((col,) for col in help_cols)
            page = min(page, len(page_cols) - 1)
            self.help_page = page
            for px in range(30, 7, -1):
                ok, draws, m, tf = self._help_layout(
                    px, W, H, page_cols[page]
                )
                chosen = (px, draws, m, tf)
                if ok:
                    break
            self._help_paged = True
            self._help_page_count = len(page_cols)
            cache = self._help_cache = (key, chosen)
        px, draws, m, tf = cache[1]
        f = FONTS.get(px)
        t = self.target
    
        t.blit(tf.render(tr("help.title"), True, (255, 215, 0)), (m, m // 2 + 2))
    
        label = tr("help.close_hint")
        if self._help_paged:
            last = page >= self._help_page_count - 1
            label = tr("help.page", page=page + 1, pages=self._help_page_count,
                       action=tr("help.close") if last else tr("help.next"))
    
        hint = f.render(label, True, (170, 176, 210))
        t.blit(hint, (W - m - hint.get_width(), m // 2 + 4))
    
        for kind, text, x, y, w, fnt in draws:
            if kind == "title":
                t.blit(fnt.render(text, True, (255, 215, 0)), (x, y))
            elif kind == "rule":
                pygame.draw.line(t, (110, 96, 30), (x, y), (x + w - 2, y))
            elif kind == "key":
                t.blit(fnt.render(text, True, (150, 220, 255)), (x, y))
            else:
                t.blit(fnt.render(text, True, (236, 236, 246)), (x, y))


def selftest(game, seconds, shots_dir=None):
    game.mode = "restart"
    dt = 1.0 / 60.0
    t = 0.0
    last_shot = -99.0
    n = 0
    while t < seconds and game.mode != "full":
        game.update(dt)
        t += dt
        if shots_dir and t - last_shot > 12:
            last_shot = t
            game.draw()
            pygame.image.save(game.screen, os.path.join(shots_dir, "shot_%03d.png" % n))
            n += 1
    st = game.stats
    print("tempo sim %.0fs  modo=%s tempo=%dT %.0f'" % (t, game.mode, game.half, game.minute()))
    print("punteggio", game.score, "tiri", st["shots"], "falli", st["fouls"], "gialli", st["yellow"], "rossi", st["red"],
          "angoli", st["corners"])


def main():
    ap = argparse.ArgumentParser(description="IL MISTER (pygame)")
    ap.add_argument("--pic", help="cartella PIC con 27.VGA (sprite) e i loghi delle squadre")
    ap.add_argument("--data", help="cartella con tore_actions.json")
    ap.add_argument("--mana", help="percorso di MANA.DAT (default: cartella del programma)")
    ap.add_argument("--geometria-originale", "--original-geometry", action="store_true", dest="orig_geom",
                    help="tela 320x112 come nell'editor TORE (default: tela estesa con gli angoli vicini)")
    ap.add_argument("--no-replay", action="store_true", help="replay automatico disattivato di default")
    ap.add_argument("--replay-secs", type=int, default=5, help="durata del replay in secondi (default 5)")
    ap.add_argument("--tore-fps", type=int, default=TORE_FPS, help="frame al secondo dei file TORE (default %d: nel viewer imposta lo stesso fps)" % TORE_FPS)
    ap.add_argument("--tore-dir", help="cartella dove salvare i file TORE dei replay (default: TORE_OUT accanto al programma)")
    ap.add_argument("--half", type=float, default=3.0, help="durata (minuti REALI) di ogni tempo, default 3")
    ap.add_argument("--zoom", type=int, help="ingrandimento (default 5 con scroll, 3 a campo intero)")
    ap.add_argument("--noscroll", action="store_true", help="vedi sempre tutto il campo (senza scroll)")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--lang", default="it", help="lingua dell'interfaccia (codice di data/lang/mister_lang_<codice>.py, default it)")
    ap.add_argument("--no-dialog", action="store_true", help="non chiedere la cartella PIC")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--selftest", type=float, help=argparse.SUPPRESS)
    ap.add_argument("--shots", help=argparse.SUPPRESS)
    args = ap.parse_args()
    init_language(args.lang)
    if args.seed is not None:
        random.seed(args.seed)
    app_dir = os.path.dirname(os.path.abspath(__file__))
    cwd = os.getcwd()
    dirs = ([args.data] if args.data else []) + [os.path.join(app_dir, "data"), app_dir, os.path.join(cwd, "data"), cwd]
    notes = load_data(dirs)
    teams, team_note = load_teams([app_dir, cwd], args.mana)
    pic = locate_pic(app_dir, args.pic)
    if pic is None and not (args.selftest or args.no_dialog):
        pic = ask_pic_dir()
    asset_dirs = [app_dir, os.path.join(app_dir, "data"), cwd, os.path.join(cwd, "data")] + ([pic] if pic else [])
    field_path = find_asset("campo.png", asset_dirs)
    board_path = find_asset("tabellone.png", asset_dirs)
    sheet_path = find_file(pic, "27") if pic else None
    missing = [n for n, p in (("campo.png", field_path), ("tabellone.png", board_path), ("27.vga", sheet_path)) if p is None]
    if missing:
        fatal(missing, [d for d in asset_dirs if d])
    pygame.display.init()
    pygame.font.init()
    FONTS.load([app_dir, os.path.join(app_dir, "data"), cwd, os.path.join(cwd, "data")])
    miss_fon = [n for n, f in (("MICRO4.FON", FONTS.micro), ("FLOW.FON", FONTS.flow)) if f is None]
    if miss_fon:
        fatal(miss_fon, [d for d in asset_dirs if d])
    pygame.display.set_caption(tr("app.caption"))
    args.zoom = args.zoom or (3 if args.noscroll else 5)
    d = compute_layout(args.zoom, not args.noscroll)
    try:
        screen = pygame.display.set_mode((int(d["W"]), int(d["H"])), pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode((d["W"], d["H"]))
    global LOG_DIR
    LOG_DIR = os.path.join(app_dir, "log")
    args.tore_dir = args.tore_dir or os.path.join(app_dir, "TORE_OUT")
    try:
        gfx = Graphics(pic, field_path, board_path, sheet_path)
    except OSError as ex:
        fatal([str(ex)], [])
    notes = [team_note] + notes
    print(team_note.text())
    audio = Audio(not args.no_sound and not args.selftest, os.path.join(app_dir, ".tore_audio"))
    game = Game(args, gfx, audio, screen, notes, teams)
    game.notes.extend(Note("note.lang_problem", True, detail=d) for d in T.take_problems())
    game.apply_view()
    if args.selftest:
        selftest(game, args.selftest, args.shots)
        return
    clock = pygame.time.Clock()
    DT = 1.0 / 60.0
    acc = 0.0
    running = True
    
    while running:
        acc = min(acc + clock.tick(60) / 1000.0 * game.speed, 0.5)
    
        for ev in pygame.event.get():
            if game.handle_event(ev) == "quit":
                running = False
        now = pygame.time.get_ticks()
        if (
            game.cam_manual
            and game.pan_return_at
            and now >= game.pan_return_at
        ):
            game.cam_manual = False
            game.cam_glide = CAM_GLIDE_SECS
            game.pan_return_at = 0
            game.say(tr("msg.camera_ball"), (200, 220, 255), 1.5)
            if game.paused:
                game.update_cam(0.0, True)
        while acc >= DT:
            if game.confirm_exit:
                pass
            elif game.replay:
                game.replay_step()
            elif not game.paused and not game.confirm_exit:
                game.update(DT)
            acc -= DT
        game.draw()
        pygame.display.flip()
    game.save_log("interrotta")
    pygame.quit()


if __name__ == "__main__":
    main()
