import copy
import io
import json
import math
import os
import re
import shutil
import struct
import sys
import time

import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from PIL import Image, ImageDraw, ImageTk

import i18n

FRAME_SIZE = 164
N_RECORDS = 27
CELL_W, CELL_H = 12, 11
SHEET_COLS = 24
Y_OFFSET = 35
ALLOW_NEGATIVE_BALL_Y = False
BALL_Y_MIN = -Y_OFFSET if ALLOW_NEGATIVE_BALL_Y else 0
WIN_W, WIN_H = 182, 96
SCROLL_MAX_X, SCROLL_MAX_Y = 137, 15
SIGNATURES = (b"BM-Ed1.0-WK\x00", b"BM-Ed1.3-WK\x00")
GOAL_L = ((0, 0, 24, 20), (0, 54)) 
GOAL_R = ((24, 0, 46, 20), (296, 54))

def _hex_palette(s, scale=1):
    return [
        (min(255, int(s[i:i + 2], 16) * scale),
         min(255, int(s[i + 2:i + 4], 16) * scale),
         min(255, int(s[i + 4:i + 6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

PAL_DEFAULT = _hex_palette(
    "000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A060207040103040C0F0F000B0A070908050806040604030503020F0F0F0C030C0000000",
    scale=1)
_ALPHA_LUT = bytes([0] + [255] * 255)


def _palette_to_flat_rgb(pal, size=256):
    flat = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]


def load_vga_image(vga_path, palette):
    if not os.path.isfile(vga_path):
        return None
    try:
        with open(vga_path, "rb") as f:
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
        img = Image.frombytes("P", (width, height), bytes(pixels))
        img.putpalette(_palette_to_flat_rgb(palette))
        return img
    except (OSError, ValueError, IndexError):
        return None


def find_subdir(parent, name):
    try:
        for fn in os.listdir(parent):
            p = os.path.join(parent, fn)
            if fn.lower() == name.lower() and os.path.isdir(p):
                return p
    except OSError:
        pass
    return None


def find_pic_dir(te_path):
    return find_subdir(os.path.dirname(os.path.dirname(os.path.abspath(te_path))), "pic")


def find_file(folder, stem):
    if folder and os.path.isdir(folder):
        for fn in os.listdir(folder):
            if fn.lower() == stem.lower() + ".vga":
                return os.path.join(folder, fn)
    return None


def _to_rgba(img_p):
    rgba = img_p.convert("RGBA")
    mask = Image.frombytes("L", img_p.size, img_p.tobytes().translate(_ALPHA_LUT)) 
    rgba.putalpha(mask)
    return rgba


class Graphics:
    def __init__(self, pic_dir):
        self.pic_dir = pic_dir
        self.missing = []
        loaded = {}
        for stem, what in (("26", "field"), ("27", "sprite"), ("29", "goals")):
            p = find_file(pic_dir, stem)
            img = load_vga_image(p, PAL_DEFAULT) if p else None
            if img is None:
                self.missing.append("%s.VGA (%s)" % (stem, what))
            loaded[stem] = img
        self.field = loaded["26"].convert("RGBA") if loaded["26"] else Image.new("RGBA", (320, 112), (40, 120, 40, 255))
        self.sheet = _to_rgba(loaded["27"]) if loaded["27"] else None
        self.goals = _to_rgba(loaded["29"]) if loaded["29"] else None
        self._cache = {}

    def _placeholder(self, sid):
        if sid not in self._cache:
            w = 4 if sid >= 142 else CELL_W
            t = team_of(sid)
            if sid == 145:
                im = Image.new("RGBA", (w, CELL_H), (0, 0, 0, 0))
                ImageDraw.Draw(im).ellipse((0, 4, w - 1, 8), fill=(0, 0, 0, 140))
            elif sid >= 142:
                im = Image.new("RGBA", (w, CELL_H), (0, 0, 0, 0))
                ImageDraw.Draw(im).ellipse((0, 3, w - 1, 7), fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
            else:
                col = {"R": (225, 70, 70, 255), "B": (80, 120, 235, 255), "A": (40, 40, 40, 255)}.get(t, (255, 255, 255, 255))
                im = Image.new("RGBA", (w, CELL_H), col)
                d = ImageDraw.Draw(im)
                d.rectangle((0, 0, w - 1, CELL_H - 1), outline=(0, 0, 0, 255))
                nose = (w - 4, 2, w - 2, 4) if facing_of(sid) == "E" else (1, 2, 3, 4)
                d.rectangle(nose, fill=(255, 255, 255, 255))
            self._cache[sid] = im
        return self._cache[sid]

    def sprite(self, sid):
        if not self.sheet:
            return self._placeholder(sid)
        if sid not in self._cache:
            col, row = sid % SHEET_COLS, sid // SHEET_COLS
            x0, w = col * CELL_W, CELL_W
            if sid >= 142:
                x0, w = x0 + 4, 4
            box = (x0, row * CELL_H, x0 + w, row * CELL_H + CELL_H)
            self._cache[sid] = self.sheet.crop(box) if box[3] <= self.sheet.height else None
        return self._cache[sid]


MAX_FRAMES = 256
FW, FH = 320, 112
MAX_Y = FH - Y_OFFSET - CELL_H
SOUNDS = [("snd.goal", "#2e9e3e"), ("snd.whistle", "#d4b000"), ("snd.disapproval", "#e07020"), ("snd.missed", "#3a5bd0")]
KINDS = {"T": "kind.T", "V": "kind.V"}
VARIANTS = {"": "var.none", "E": "var.E", "J": "var.J"}
PATH_COLORS = {"ball": "#ffd54a", "ref": "#d0d0d0", "red": "#ff6e6e", "blue": "#6ea8ff"}
PATH_COLOR_LABELS = (("ball", "col.ball"), ("ref", "col.ref"), ("red", "col.red"), ("blue", "col.blue"))
VIEW_ZOOM_MAX = 12.0
GHOST_KEYS = ("ghost.none", "ghost.prev", "ghost.allsel", "ghost.allspr")

DIRS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
DIR_LABEL = {d: "dir." + d for d in DIRS}

def _app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

APP_DIR = _app_dir()
DATA_DIR = os.path.join(APP_DIR, "data")
ACTIONS_FILE = os.path.join(DATA_DIR, "tore_actions.json")
POSES_FILE = os.path.join(DATA_DIR, "tore_pose_sets.json")
KICKOFF_FILE = os.path.join(DATA_DIR, "tore_kickoff.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "tore_settings.json")
I18N_PREFIX = "tore_lang_"


def _load_settings():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_language(code):
    d = _load_settings()
    d["lang"] = code
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2)
    except OSError:
        pass


LANG = i18n.Translator(prefix=I18N_PREFIX)
tr = LANG.tr

def _init_language():
    code = str(_load_settings().get("lang", i18n.FALLBACK_LANGUAGE))
    if not LANG.set_language(code):
        LANG.set_language(i18n.FALLBACK_LANGUAGE)


_init_language()

ACTIONS, ACTION_ORDER, MOVE_E, STAND_K = {}, [], {}, {}
REF_MOVE, REF_STAND, BALL_ROT = {}, {}, []
PLAYER_CATS, REF_CATS, BALL_CATS, BALL_ALL = [], [], [], []
DATA_WARNINGS = []


class DataError(Exception):
    pass


def _why(ex):
    return "missing key %s" % ex if isinstance(ex, KeyError) else str(ex)


def action_sides(key, acts=None):
    return ["E"] if (acts if acts is not None else ACTIONS)[key].get("single") else ["E", "W"]


def action_label(key, side, acts=None):
    a = (acts if acts is not None else ACTIONS)[key]
    return a["label"] if a.get("single") else "%s -> %s" % (a["label"], side)


def parse_ids(text, lo, hi):
    out = []
    for tok in re.split(r"[,\s;]+", re.sub(r"\s*-\s*", "-", text.strip())):
        if not tok:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", tok)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out += list(range(a, b + 1)) if a <= b else list(range(a, b - 1, -1))
        elif tok.isdigit():
            out.append(int(tok))
        else:
            raise ValueError("Bad value: %r" % tok)
    if not out:
        raise ValueError("Enter at least one id")
    bad = [v for v in out if not lo <= v <= hi]
    if bad:
        raise ValueError("Ids out of range %d-%d: %s" % (lo, hi, bad))
    return out


def ids_text(ids):
    return ",".join(str(i) for i in ids)


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _load_json(path):
    if not os.path.isfile(path):
        raise DataError("file not found in %s" % os.path.dirname(path))
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise DataError("unreadable or not a JSON object")
    return raw


def _dump(path, obj):
    txt = json.dumps(obj, indent=1, ensure_ascii=False)
    txt = re.sub(r"\[\s*([\d,\s-]*?)\s*\]", lambda m: "[" + re.sub(r"\s+", " ", m.group(1)) + "]", txt)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(txt + "\n")


def _dump_merge(path, updates):
    cur = _read_json(path)
    cur = cur if isinstance(cur, dict) else {}
    cur.update(updates)
    _dump(path, cur)


def _ks(v, lo, hi):
    out = [int(x) for x in v]
    if not out or any(not lo <= k <= hi for k in out):
        raise ValueError("ids must be %d-%d and not empty" % (lo, hi))
    return out


def _cats(d, lo, hi):
    if not isinstance(d, dict):
        raise ValueError("expected an object of name -> [ids]")
    return [(str(n), _ks(v, lo, hi)) for n, v in d.items()]


def _poses_file(red, referee, ball):
    return {"red": red, "blue": {n: [k + 59 for k in v] for n, v in red.items()}, "referee": referee, "ball": ball}


def _clean_actions(raw):
    acts = {}
    for key, a in raw["actions"].items():
        e = _ks(a["E"], 0, 58)
        d = {"label": str(a.get("label", key)), "E": e, "W": _ks(a["W"], 0, 58) if a.get("W") else [58 - k for k in e]}
        if a.get("single"):
            d["single"] = True
        if a.get("travel"):
            d["travel"] = True
        acts[str(key)] = d
    order = [k for k in raw.get("order", []) if k in acts]
    order += [k for k in acts if k not in order]
    moves = {d: _ks(raw["moves"][d], 0, 58) for d in DIRS}
    rst = raw.get("stand") or {}
    stand = {d: int(rst[d]) if d in rst else moves[d][0] for d in DIRS}
    rf = raw["referee"]
    rm, rs = rf["move"], rf["stand"]
    rmove = {d: _ks(rm[d] if d in rm else rm["W" if "W" in d else "E"], 118, 141) for d in DIRS}
    if isinstance(rs, dict):
        rstand = {d: int(rs[d]) if d in rs else rmove[d][0] for d in DIRS}
    else:
        rstand = {d: int(rs) if d in "EW" else rmove[d][0] for d in DIRS}
    return acts, order, moves, stand, {"move": rmove, "stand": rstand}


def load_data():
    global ACTIONS, ACTION_ORDER, MOVE_E, STAND_K, REF_MOVE, REF_STAND, BALL_ROT
    global PLAYER_CATS, REF_CATS, BALL_CATS, BALL_ALL
    warn = []
    try:
        acts, order, moves, stand, ref = _clean_actions(_load_json(ACTIONS_FILE))
    except (DataError, TypeError, ValueError, KeyError, AttributeError) as ex:
        warn.append("%s: %s - actions and movement unavailable" % (os.path.basename(ACTIONS_FILE), _why(ex)))
        acts, order, moves, stand, ref = {}, [], {}, {}, {"move": {}, "stand": {}}
    ACTIONS, ACTION_ORDER, MOVE_E, STAND_K = acts, order, moves, stand
    REF_MOVE, REF_STAND = ref["move"], ref["stand"]
    try:
        raw = _load_json(POSES_FILE)
        red = _cats(raw["red"], 0, 58)
        refc = _cats(raw["referee"], 118, 141)
        ball = _cats(raw["ball"], 142, 145)
    except (DataError, TypeError, ValueError, KeyError, AttributeError) as ex:
        warn.append("%s: %s - pose sets unavailable" % (os.path.basename(POSES_FILE), _why(ex)))
        red, refc, ball = [], [], []
    PLAYER_CATS, REF_CATS, BALL_ALL = red, refc, ball
    BALL_CATS = [(n, v) for n, v in ball if n != "shadow"]
    BALL_ROT = list(dict(ball).get("rotation") or [])
    DATA_WARNINGS[:] = warn
    return warn


def save_data_files(pg, ad):
    _dump(ACTIONS_FILE, {"order": ad["order"], "actions": ad["actions"], "moves": ad["moves"], "stand": ad["stand"], "referee": ad["referee"]})
    _dump_merge(POSES_FILE, _poses_file(pg["red"], pg["referee"], pg["ball"]))


load_data()


def cls(sid):
    if sid == 1000:
        return "L"
    if sid > 1000:
        return "R"
    if sid == 145:
        return "S"
    if sid >= 142:
        return "B"
    return "P"


def team_of(sid):
    return "R" if sid <= 58 else "B" if sid <= 117 else "A" if sid <= 141 else None


def xform_id(sid, flip, swap):
    t = team_of(sid)
    if t in ("R", "B"):
        k = sid if t == "R" else sid - 59
        if flip:
            k = 58 - k
        return (k + 59 if t == "R" else k) if swap else (k if t == "R" else k + 59)
    if t == "A" and flip and sid <= 139:
        return 257 - sid
    return sid


def mirror_pose(sid):
    return xform_id(sid, True, False)


def cats_for(sid):
    t = team_of(sid)
    if t in ("R", "B"):
        off = 0 if t == "R" else 59
        return [(n, [k + off for k in ks]) for n, ks in PLAYER_CATS]
    if t == "A":
        return REF_CATS
    return BALL_CATS if cls(sid) == "B" else []


def facing_of(sid):
    t = team_of(sid)
    if t in ("R", "B"):
        k = sid if t == "R" else sid - 59
        return "W" if 34 <= k <= 58 else "E"
    if t == "A":
        return "W" if sid >= 129 else "E"
    return "E"


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


def loco_cycle(sid, d):
    t = team_of(sid)
    if t in ("R", "B"):
        off = 0 if t == "R" else 59
        return [off + k for k in MOVE_E[d]] if d in MOVE_E else None
    if t == "A":
        return list(REF_MOVE.get(d) or []) or None
    return (list(BALL_ROT) or None) if cls(sid) == "B" else None


def stand_id(sid, face):
    t = team_of(sid)
    if t in ("R", "B"):
        k = STAND_K.get(face, STAND_K.get(face[-1:]))
        return sid if k is None else (0 if t == "R" else 59) + k
    if t == "A":
        return REF_STAND.get(face, REF_STAND.get(face[-1:], sid))
    return sid


def dir_of_sprite(sid):
    cycs = [(d, loco_cycle(sid, d)) for d in DIRS]
    for d, c in cycs:
        if c and sid == c[0]:
            return d
    for d, c in cycs:
        if c and sid in c:
            return d
    return facing_of(sid)


def loco_ids(sid):
    t = team_of(sid)
    if t in ("R", "B"):
        off = 0 if t == "R" else 59
        ks = {0, 58} | set(range(1, 10)) | set(range(49, 58))
        for v in MOVE_E.values():
            ks |= set(v)
        return {off + k for k in ks}
    if t == "A":
        return set(range(118, 142))
    return set(BALL_ROT)


def action_ids(sid, key, side=None):
    t = team_of(sid)
    if t not in ("R", "B") or key not in ACTIONS:
        return []
    off = 0 if t == "R" else 59
    return [off + k for k in ACTIONS[key][side or facing_of(sid)]]


TL_KIND_COLORS = {"stand": "#9e9e9e", "loco": "#66bb6a", "action": "#ff9800"}


def sprite_kind(sid):
    if sid in {stand_id(sid, d) for d in DIRS}:
        return "stand"
    return "loco" if sid in loco_ids(sid) else "action"


def find_actions(sids):
    cands, out, i = {}, [], 0
    while i < len(sids):
        team = team_of(sids[i])
        if team in ("R", "B"):
            if team not in cands:
                cands[team] = [(k, s, q) for k in ACTION_ORDER for s in action_sides(k)
                               for q in (action_ids(sids[i], k, s),)
                               if q and any(sprite_kind(v) == "action" for v in q)]
            best = None
            for k, s, q in cands[team]:
                if sids[i:i + len(q)] == q and (best is None or len(q) > len(best[2])):
                    best = (k, s, q)
            if best:
                out.append((i, i + len(best[2]), best[0], best[1]))
                i += len(best[2])
                continue
        i += 1
    return out


def poly_len(p):
    return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, len(p)))


PERSP_LINES = [(10, 60, 258), (20, 40, 277), (28, 24, 294), (39, 3, 314)]
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
    import bisect
    i = min(max(bisect.bisect_right(_PV, v) - 1, 0), _PV_N - 2)
    return _PV_Y0 + (i + (v - _PV[i]) / (_PV[i + 1] - _PV[i])) * _PV_STEP


def persp_to_world(x, y):
    y += PERSP_Y_SHIFT
    left, right = persp_edges(y)
    return (x - left) / max(20.0, right - left) * _PERSP_WREF, _persp_v(y)


def persp_from_world(wx, wv):
    y = _persp_y(wv) - PERSP_Y_SHIFT
    left, right = persp_edges(y + PERSP_Y_SHIFT)
    return left + wx / _PERSP_WREF * max(20.0, right - left), y


def xlim(sid):
    return 0, FW - sprite_w(sid)


def clamp_field(seq, xlo=0, xhi=FW - 1, tol=0.5, ylo=0.0):
    out, hit = [], False
    for x, y in seq:
        cx, cy = min(max(x, float(xlo)), float(xhi)), min(max(y, float(ylo)), float(MAX_Y))
        if abs(cx - x) > tol or abs(cy - y) > tol:
            hit = True
        out.append((cx, cy))
    return out, hit


def _densify(p, step=2.0):
    out = [p[0]]
    for i in range(1, len(p)):
        (x0, y0), (x1, y1) = p[i - 1], p[i]
        k = max(1, int(math.ceil(math.hypot(x1 - x0, y1 - y0) / step)))
        out += [(x0 + (x1 - x0) * j / k, y0 + (y1 - y0) * j / k) for j in range(1, k + 1)]
    return out


def rdp(pts, eps):
    if len(pts) < 3:
        return list(pts)
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dl = math.hypot(x2 - x1, y2 - y1)
    best, bi = -1.0, 0
    for i in range(1, len(pts) - 1):
        x0, y0 = pts[i]
        d = math.hypot(x0 - x1, y0 - y1) if dl == 0 else abs((y2 - y1) * x0 - (x2 - x1) * y0 + x2 * y1 - y2 * x1) / dl
        if d > best:
            best, bi = d, i
    if best <= eps:
        return [pts[0], pts[-1]]
    return rdp(pts[:bi + 1], eps)[:-1] + rdp(pts[bi:], eps)


def chaikin(pts, it=2):
    for _ in range(it):
        if len(pts) < 3:
            break
        q = [pts[0]]
        for i in range(len(pts) - 1):
            (ax, ay), (bx, by) = pts[i], pts[i + 1]
            q += [(0.75 * ax + 0.25 * bx, 0.75 * ay + 0.25 * by), (0.25 * ax + 0.75 * bx, 0.25 * ay + 0.75 * by)]
        q.append(pts[-1])
        pts = q
    return pts


def catmull(pts, seg=10):
    if len(pts) < 3:
        return list(pts)
    p = [pts[0]] + list(pts) + [pts[-1]]
    out = [pts[0]]
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(1, seg + 1):
            t = s / seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out


def resample_steps(path, n):
    cum = [0.0]
    for i in range(1, len(path)):
        cum.append(cum[-1] + math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]))
    total = cum[-1]
    out, j = [], 1
    for k in range(1, n + 1):
        target = total * k / n
        while j < len(path) - 1 and cum[j] < target:
            j += 1
        seg = cum[j] - cum[j - 1]
        u = 0.0 if seg == 0 else (target - cum[j - 1]) / seg
        out.append((path[j - 1][0] + (path[j][0] - path[j - 1][0]) * u, path[j - 1][1] + (path[j][1] - path[j - 1][1]) * u))
    return out


def resample_time(samples, fps):
    T = samples[-1][0] - samples[0][0]
    n = max(1, int(round(T * fps)))
    out, j = [], 1
    for k in range(1, n + 1):
        t = samples[0][0] + T * k / n
        while j < len(samples) - 1 and samples[j][0] < t:
            j += 1
        (t0, x0, y0), (t1, x1, y1) = samples[j - 1], samples[j]
        u = 0.0 if t1 == t0 else max(0.0, min(1.0, (t - t0) / (t1 - t0)))
        out.append((x0 + (x1 - x0) * u, y0 + (y1 - y0) * u))
    return out


def gauss_w(n, k0, sigma):
    return [math.exp(-0.5 * ((i - k0) / max(0.3, sigma)) ** 2) for i in range(n)]


def _stabilize(dirs, minrun=3):
    out = list(dirs)
    n = len(out)
    runs, i = [], 0
    while i < n:
        j = i
        while j + 1 < n and out[j + 1] == out[i]:
            j += 1
        runs.append((i, j, out[i]))
        i = j + 1
    for ri, (s, e, d) in enumerate(runs):
        if d is None or e - s + 1 >= minrun:
            continue
        repl = None
        if s > 0 and out[s - 1] is not None:
            repl = out[s - 1]
        elif ri + 1 < len(runs) and runs[ri + 1][2] is not None:
            repl = runs[ri + 1][2]
        if repl:
            for k in range(s, e + 1):
                out[k] = repl
    return out


RANK = {"S": 0, "B": 1, "P": 2, "L": 3, "R": 3}

class Frame:
    def __init__(self, scroll, figs, order=None):
        self.scroll = list(scroll)
        self.figs = [list(f) for f in figs]   
        self.order = order
        if not order:
            self.order = None
            self.order = self.sorted_order()
        self.dirty = False

    def sorted_order(self):
        sh = next((f for f in self.figs if f[2] == 145), None)

        def key(i):
            x, y, sid = self.figs[i]
            c = cls(sid)
            k = y
            if c == "S":
                k = y - 4
            elif c == "B":
                k = (sh[1] - 4) if sh else y
            return (k, RANK[c], i)
        pos = {sl: n for n, sl in enumerate(self.order)} if self.order else {}
        return sorted(range(len(self.figs)), key=lambda i: (key(i)[0], pos.get(i, key(i)[1] * 100 + i)))

    def touch(self):
        self.dirty = True
        self.order = self.sorted_order()

    def index_of(self, c):
        return next((i for i, f in enumerate(self.figs) if cls(f[2]) == c), None)


def _match(prev, recs, prev2=None):
    pairs = []
    for s, p in enumerate(prev):
        vx = vy = 0
        if prev2 is not None:
            vx = max(-6, min(6, p[0] - prev2[s][0]))
            vy = max(-6, min(6, p[1] - prev2[s][1]))
        for j, r in enumerate(recs):
            if cls(p[2]) == cls(r[2]):
                cost = (p[0] + vx - r[0]) ** 2 + (p[1] + vy - r[1]) ** 2
                cost += 0 if p[2] == r[2] else 60
                cost += 0 if team_of(p[2]) == team_of(r[2]) else 6000
                pairs.append((cost, s, j))
    pairs.sort()
    m, used = {}, set()
    for _, s, j in pairs:
        if s not in m and j not in used:
            m[s] = j
            used.add(j)
    free = [j for j in range(len(recs)) if j not in used]
    for s in range(len(prev)):
        if s not in m:
            m[s] = free.pop(0)
    return m


KICKOFF_COUNTS = [11, 11, 1, 1, 1, 1, 1]


def _grp(sid):
    if sid == 1000:
        return 5
    if sid > 1000:
        return 6
    if sid == 145:
        return 3
    if sid >= 142:
        return 4
    return 0 if sid <= 58 else 1 if sid <= 117 else 2


def _kick_check(figs):
    cnt = [0] * 7
    for g in figs:
        if len(g) != 3 or not 0 <= g[2] <= 1024:
            return "invalid record %s" % (g,)
        cnt[_grp(g[2])] += 1
    if len(figs) != N_RECORDS or cnt != KICKOFF_COUNTS:
        return "needs 11 red + 11 blue players, referee, shadow, ball and 2 goals (found %s)" % cnt
    return None


def save_kickoff(figs, scroll):
    figs = [[int(v) for v in g] for g in figs]
    err = _kick_check(figs)
    if err:
        return err
    ordered = [g for _, g in sorted(enumerate(figs), key=lambda t: (_grp(t[1][2]), t[0]))]
    try:
        _dump_merge(KICKOFF_FILE, {"scroll": [int(scroll[0]), int(scroll[1])], "figs": ordered})
    except OSError as ex:
        return str(ex)
    return None


def load_kickoff():
    try:
        raw = _load_json(KICKOFF_FILE)
        figs = [[int(v) for v in g] for g in raw["figs"]]
        err = _kick_check(figs)
        if err:
            raise ValueError(err)
        sc = [max(0, min(SCROLL_MAX_X, int(raw["scroll"][0]))), max(0, min(SCROLL_MAX_Y, int(raw["scroll"][1])))]
        return sc, figs
    except (DataError, TypeError, ValueError, KeyError, IndexError) as ex:
        raise DataError("%s: %s" % (os.path.basename(KICKOFF_FILE), _why(ex)))


class Scene:
    def __init__(self):
        self.sig = SIGNATURES[1]
        self.events = [None] * 4
        self.author = ""
        self.frames = []
        self.path = None
        self.kind = "T"
        self.variant = ""

    def ext(self):
        return self.kind + self.variant

    @staticmethod
    def new():
        s = Scene()
        try:
            sc, figs = load_kickoff()
        except DataError as ex:
            msg = "%s - empty scene created" % ex
            if msg not in DATA_WARNINGS:
                DATA_WARNINGS.append(msg)
            sc, figs = [0, 0], []
        s.frames = [Frame(sc, figs)]
        return s

    @staticmethod
    def load(path):
        d = open(path, "rb").read()
        if len(d) < 17 or d[:12] not in SIGNATURES:
            raise ValueError("Not a valid scene file (BM-Ed1.x-WK)")
        n = d[16] + 1
        end = 17 + n * FRAME_SIZE
        if len(d) < end:
            raise ValueError("Truncated file")
        s = Scene()
        s.path, s.sig = path, d[:12]
        e = os.path.splitext(path)[1][1:].upper()
        s.kind = e[0] if e[:1] in ("T", "V") else "T"
        s.variant = e[1] if len(e) > 1 and e[1] in ("E", "J") else ""
        s.events = [None if b == 255 else b for b in d[12:16]]
        prev = prev2 = None
        for i in range(n):
            w = struct.unpack("<82H", d[17 + i * FRAME_SIZE:17 + (i + 1) * FRAME_SIZE])
            scroll = (min(w[0] & 255, SCROLL_MAX_X), min(w[0] >> 8, SCROLL_MAX_Y))
            recs = [[x - 65536 if x > 32767 else x, y - 65536 if y > 32767 else y, sp]
                    for x, y, sp in (w[1 + 3 * k:4 + 3 * k] for k in range(N_RECORDS))]
            if prev is None:
                f = Frame(scroll, recs, list(range(N_RECORDS)))
            else:
                m = _match(prev, recs, prev2)
                figs = [recs[m[sl]] for sl in range(N_RECORDS)]
                order = [0] * N_RECORDS
                for sl in range(N_RECORDS):
                    order[m[sl]] = sl
                f = Frame(scroll, figs, order)
            s.frames.append(f)
            prev2, prev = prev, f.figs
        tail = d[end:]
        if tail:
            s.author = tail[1:1 + tail[0]].split(b"\0")[0].decode("cp437", "replace")
        return s

    def to_bytes(self):
        hdr = bytes(255 if e is None else max(0, min(254, e)) for e in self.events)
        out = bytearray(self.sig + hdr + bytes([len(self.frames) - 1]))
        for f in self.frames:
            if f.dirty:
                b = f.index_of("B")
                for c in ("L", "R"):
                    g = f.index_of(c)
                    if g is not None and b is not None:
                        f.figs[g][0] = f.figs[b][0]
                f.order = f.sorted_order()
            records = [list(g) for g in f.figs[:N_RECORDS]]
            while len(records) < N_RECORDS:
                records.append([0, 0, 0])
            order = list(f.order[:len(f.figs)])
            order += list(range(len(f.figs), N_RECORDS))
            w = [f.scroll[0] | (f.scroll[1] << 8)]
            for sl in order:
                w += records[sl]
            for j in range(1, len(w), 3):
                w[j] = max(0, min(65535, int(w[j])))
                w[j + 1] = max(BALL_Y_MIN if 142 <= w[j + 2] <= 144 else 0, min(65535, int(w[j + 1])))
                w[j + 1] &= 0xFFFF
            out += struct.pack("<82H", *w)
        a = self.author.encode("cp437", "replace")
        out += bytes([len(a) + 1]) + a + b"\0"
        return bytes(out)

    def save(self, path=None):
        path = path or self.path
        with open(path, "wb") as fh:
            fh.write(self.to_bytes())
        self.path = path
        for f in self.frames:
            f.dirty = False


def transform_frame(f, flip, swap):
    for g in f.figs:
        x, y, sid = g
        c = cls(sid)
        if c == "P":
            g[2] = xform_id(sid, flip, swap)
            if flip:
                g[0] = max(xlim(sid)[0], min(xlim(sid)[1], FW - CELL_W - x))
        elif c in "SB":
            if flip:
                g[0] = max(xlim(sid)[0], min(xlim(sid)[1], FW - 4 - x))
        elif flip:
            g[2] = 1024 if sid == 1000 else 1000
    if flip:
        b = f.index_of("B")
        for g in f.figs:
            if cls(g[2]) in "LR" and b is not None:
                g[0] = f.figs[b][0]
        f.scroll[0] = max(0, min(SCROLL_MAX_X, FW - WIN_W - f.scroll[0]))


def find_anzahl(path):
    here = os.path.dirname(os.path.abspath(path))
    for d in (here, os.path.dirname(here)):
        try:
            for n in os.listdir(d):
                if n.lower() == "anzahl" and os.path.isfile(os.path.join(d, n)):
                    return os.path.join(d, n)
        except OSError:
            pass
    return None


def read_anzahl(p):
    m = re.match(r"MAXSZENE:(\d+)\|(\d+)\|(\d+)", open(p, "rb").read().split(b"\0")[0].decode("latin1"))
    return [int(v) for v in m.groups()] if m else None


def write_anzahl(p, vals):
    if not os.path.exists(p + ".bak"):
        shutil.copy(p, p + ".bak")
    with open(p, "wb") as fh:
        fh.write(("MAXSZENE:%d|%d|%d" % tuple(vals)).encode() + b"\0")


def locate_pic(p=None):
    if p:
        d = find_pic_dir(p)
        if d:
            return d
        here = os.path.dirname(os.path.abspath(p))
        cand = [here, os.path.dirname(here)]
    else:
        cand = []
    cand.append(find_subdir(APP_DIR, "pic"))
    cand.append(APP_DIR)
    for d in filter(None, cand):
        if find_file(d, "27"):
            return d
    return None


def sprite_of(gfx, sid):
    return gfx.sprite(sid)


def ghost_sprite(gfx, sid, a):
    q = max(1, round(a * 8)) / 8
    cache = gfx.__dict__.setdefault("_g", {})
    if (sid, q) not in cache:
        sprite = sprite_of(gfx, sid)
        if sprite is None:
            return None
        s = sprite.copy()
        s.putalpha(s.getchannel("A").point(lambda v: int(v * q)))
        cache[(sid, q)] = s
    return cache[(sid, q)]


def compose(gfx, fr, ghosts=()):
    img = gfx.field.copy()
    for x, y, sid, a in ghosts:
        s = ghost_sprite(gfx, sid, a)
        if s is not None:
            img.paste(s, (x, y + Y_OFFSET), s)
    for sl in fr.order:
        x, y, sid = fr.figs[sl]
        if sid >= 1000:
            left = sid == 1000
            box, dst = GOAL_L if left else GOAL_R
            if gfx.goals:
                part = gfx.goals.crop(box)
                img.paste(part, dst, part)
            else:
                ph = Image.new("RGBA", (24, 20), (255, 255, 255, 90))
                img.paste(ph, dst, ph)
            continue
        spr = sprite_of(gfx, sid)
        if spr is not None:
            img.paste(spr, (x, y + Y_OFFSET), spr)
    return img


def path_h(sid):
    return CELL_H / 2 if cls(sid) in "SB" else CELL_H


def sprite_w(sid):
    return 4 if sid >= 142 else CELL_W


def _pil_enum(group, name):
    return getattr(getattr(Image, group, Image), name)

_DITHER_NONE = _pil_enum("Dither", "NONE")
_DITHER_FS = _pil_enum("Dither", "FLOYDSTEINBERG")
_Q_MEDIANCUT = _pil_enum("Quantize", "MEDIANCUT")
GIF_PRESETS = {
    "Smallest file":   dict(colors=32, shared=True, dither=False, step=2, optimize=True),
    "Small":           dict(colors=64, shared=True, dither=False, step=1, optimize=True),
    "Balanced":        dict(colors=128, shared=True, dither=False, step=1, optimize=True),
    "High quality":    dict(colors=256, shared=True, dither=False, step=1, optimize=True),
    "Maximum quality": dict(colors=256, shared=False, dither=True, step=1, optimize=True),
}
GIF_PRESET_KEYS = {"Smallest file": "gif.p.smallest", "Small": "gif.p.small", "Balanced": "gif.p.balanced", "High quality": "gif.p.high", "Maximum quality": "gif.p.max", "Custom": "gif.p.custom"}


class GifCancelled(Exception):
    pass


def _gif_shared_palette(frames, colors):
    union = set()
    for im in frames:
        found = im.getcolors(1 << 20)
        if found is None:
            union = None
            break
        union.update(c for _n, c in found)
        if len(union) > colors:
            union = None
            break
    pal = Image.new("P", (1, 1))
    if union is not None:
        flat = []
        for c in sorted(union):
            flat.extend(c[:3])
        pal.putpalette(flat)
        return pal
    n = len(frames)
    pick = frames if n <= 48 else [frames[round(i * (n - 1) / 47)] for i in range(48)]
    sheet = Image.new("RGB", (pick[0].width, pick[0].height * len(pick)))
    for i, im in enumerate(pick):
        sheet.paste(im, (0, i * pick[0].height))
    return sheet.quantize(colors=colors, method=_Q_MEDIANCUT, dither=_DITHER_NONE)


def build_gif(frames, durations, colors=256, dither=False, shared=True, optimize=True, loop=True, scale=1, smooth=False, progress=None):
    n = len(frames)
    colors = max(2, min(256, int(colors)))
    dth = _DITHER_FS if dither else _DITHER_NONE
    resample = Image.BICUBIC if smooth else Image.NEAREST
    pal = _gif_shared_palette(frames, colors) if shared else None

    def prep(i):
        im = frames[i]
        if scale > 1:
            im = im.resize((im.width * scale, im.height * scale), resample)
        if pal is not None:
            return im.quantize(palette=pal, dither=dth)
        q = im.quantize(colors=colors, method=_Q_MEDIANCUT, dither=_DITHER_NONE)
        return im.quantize(palette=q, dither=dth) if dither else q

    def rest():
        for i in range(1, n):
            if progress and progress(i, n) is False:
                raise GifCancelled()
            yield prep(i)

    if progress and progress(0, n) is False:
        raise GifCancelled()
    first = prep(0)
    kw = dict(format="GIF", save_all=True, append_images=rest(), duration=list(durations), optimize=bool(optimize))
    if loop:
        kw["loop"] = 0
    buf = io.BytesIO()
    first.save(buf, **kw)
    if progress:
        progress(n, n)
    return buf.getvalue()


def gif_durations(indices, last_index, fps, hold_ms=0):
    base = 1000.0 / max(1, fps)
    edges = [round((i - indices[0]) * base / 10) * 10 for i in indices]
    edges.append(round((last_index + 1 - indices[0]) * base / 10) * 10)
    out = [max(20, edges[k + 1] - edges[k]) for k in range(len(indices))]
    out[-1] += max(0, int(hold_ms) // 10 * 10)
    return out


def pick_sprite(parent, gfx, lo, hi, current=None):
    w = tk.Toplevel(parent)
    w.title(tr("pick.title"))
    w.transient(parent)
    w.resizable(False, False)
    cols, rows = SHEET_COLS, 7
    im = Image.new("RGBA", (cols * CELL_W, rows * CELL_H), (60, 60, 60, 255))
    if gfx.sheet:
        crop = gfx.sheet.crop((0, 0, min(gfx.sheet.width, im.width), min(gfx.sheet.height, im.height)))
        im.paste(crop, (0, 0), crop)
    z = max(1, min(6, (w.winfo_screenwidth() - 120) // im.width, (w.winfo_screenheight() - 220) // im.height))
    photo = ImageTk.PhotoImage(im.resize((im.width * z, im.height * z), Image.NEAREST))
    cv = tk.Canvas(w, width=im.width * z, height=im.height * z, highlightthickness=0, bg="#3c3c3c")
    cv.pack()
    cv.create_image(0, 0, anchor="nw", image=photo)
    cv._ph = photo
    info = tk.StringVar(master=w, value=tr("pick.info", lo=lo, hi=hi))
    ttk.Label(w, textvariable=info).pack(anchor="w", padx=6, pady=3)
    for sid in range(cols * rows):
        x0, y0 = (sid % cols) * CELL_W * z, (sid // cols) * CELL_H * z
        x1, y1 = x0 + CELL_W * z, y0 + CELL_H * z
        if lo <= sid <= hi:
            cv.create_rectangle(x0, y0, x1, y1, outline="#ff00ff")
            cv.create_text(x0 + z, y0 + z, anchor="nw", text=str(sid), fill="white", font=("TkDefaultFont", max(6, int(z * 1.2)), "bold"))
        else:
            cv.create_rectangle(x0, y0, x1, y1, fill="black", stipple="gray75", outline="")
    if current is not None and lo <= current <= hi and current < cols * rows:
        x0, y0 = (current % cols) * CELL_W * z, (current // cols) * CELL_H * z
        cv.create_rectangle(x0 + 1, y0 + 1, x0 + CELL_W * z - 1, y0 + CELL_H * z - 1, outline="#ffd54a", width=3)
    result = []

    def cell(e):
        col, row = int(e.x // (CELL_W * z)), int(e.y // (CELL_H * z))
        sid = row * cols + col
        return sid if 0 <= col < cols and 0 <= row < rows and lo <= sid <= hi else None

    def on_click(e):
        sid = cell(e)
        if sid is not None:
            result.append(sid)
            w.destroy()

    def on_move(e):
        sid = cell(e)
        info.set(tr("pick.hover", sid=sid) if sid is not None else tr("pick.info", lo=lo, hi=hi))

    cv.bind("<Button-1>", on_click)
    cv.bind("<Motion>", on_move)
    w.bind("<Escape>", lambda e: w.destroy())
    w.update_idletasks()
    w.geometry("+%d+%d" % (parent.winfo_rootx() + 30, parent.winfo_rooty() + 30))
    try:
        w.wait_visibility()
        w.grab_set()
    except tk.TclError:
        pass
    parent.wait_window(w)
    return result[0] if result else None


class SpriteStrip(tk.Canvas):
    PAD = 3

    def __init__(self, master, gfx_fn, var, rng, max_n=None, auto=None, locked=None, per_row=10, zoom=3):
        self.gfx_fn, self.var, self.rng = gfx_fn, var, rng
        self.max_n, self.auto, self.locked, self.per_row, self.zoom = max_n, auto, locked, per_row, zoom
        self.cw, self.ch = max(26, CELL_W * zoom + 6), CELL_H * zoom + 16
        super().__init__(master, width=per_row * self.cw + 2 * self.PAD, height=self.ch + 2 * self.PAD, bg="#fafafa", highlightthickness=1, highlightbackground="#c8c8c8", cursor="hand2")
        self._last, self._view, self._ph = [], ([], False, True, False), []
        self._tid = var.trace_add("write", lambda *_: self.refresh())
        self.bind("<Button-1>", lambda e: self._edit(e, "pick"))
        self.bind("<Button-2>" if sys.platform == "darwin" else "<Button-3>", lambda e: self._edit(e, "del"))
        self.bind("<Destroy>", self._on_destroy)
        self.refresh()

    def _on_destroy(self, e):
        if e.widget is self:
            try:
                self.var.trace_remove("write", self._tid)
            except tk.TclError:
                pass

    def _state(self):
        if self.locked and self.locked():
            return list(self.auto()) if self.auto else [], True, True, True
        txt = self.var.get()
        if not txt.strip():
            return (list(self.auto()), True, True, False) if self.auto else ([], False, True, False)
        try:
            return parse_ids(txt, *self.rng()), False, True, False
        except ValueError:
            return list(self._last), False, False, False

    def refresh(self):
        ids, dim, ok, locked = self._view = self._state()
        if ok and not dim:
            self._last = list(ids)
        gfx, z, cw, ch, P = self.gfx_fn(), self.zoom, self.cw, self.ch, self.PAD
        can_add = not locked and (self.max_n is None or len(ids) < self.max_n)
        cells = len(ids) + (1 if can_add else 0)
        self.config(height=max(1, -(-cells // self.per_row)) * ch + 2 * P, highlightbackground="#c8c8c8" if ok else "#d32f2f")
        self.delete("all")
        self._ph = []
        for i, pid in enumerate(ids):
            x0, y0 = P + (i % self.per_row) * cw, P + (i // self.per_row) * ch
            spr = ghost_sprite(gfx, pid, 0.45) if dim else sprite_of(gfx, pid)
            if spr is not None:
                ph = ImageTk.PhotoImage(spr.resize((spr.width * z, spr.height * z), Image.NEAREST))
                self._ph.append(ph)
                self.create_image(x0 + cw // 2, y0 + 3 + CELL_H * z // 2, image=ph)
            self.create_text(x0 + cw // 2, y0 + CELL_H * z + 10, text=str(pid), fill="#aaa" if dim else "#444", font=("TkDefaultFont", 7))
        if can_add:
            i = len(ids)
            x0, y0 = P + (i % self.per_row) * cw, P + (i // self.per_row) * ch
            self.create_rectangle(x0 + 4, y0 + 3, x0 + cw - 4, y0 + 3 + CELL_H * z, outline="#888", dash=(3, 2))
            self.create_text(x0 + cw // 2, y0 + 3 + CELL_H * z // 2, text="+", fill="#666", font=("TkDefaultFont", 12, "bold"))

    def _edit(self, e, op):
        ids, _dim, ok, locked = self._view
        if locked:
            return
        if not ok:
            return self.bell()
        c, r = int((e.x - self.PAD) // self.cw), int((e.y - self.PAD) // self.ch)
        if not 0 <= c < self.per_row or r < 0:
            return
        i, ids = r * self.per_row + c, list(ids)
        can_add = self.max_n is None or len(ids) < self.max_n
        if op == "pick":
            if i > len(ids) or (i == len(ids) and not can_add):
                return
            cur = ids[i] if i < len(ids) else None
            lo, hi = self.rng()
            pid = pick_sprite(self.winfo_toplevel(), self.gfx_fn(), lo, hi, cur)
            if pid is None:
                return
            if cur is None:
                ids.append(pid)
            else:
                ids[i] = pid
        else:
            if i >= len(ids) or len(ids) <= 1:
                return self.bell()
            del ids[i]
        self.var.set(ids_text(ids))


class ToreEditorPanel(ttk.Frame):

    def __init__(self, master=None, standalone=False, path=None, pic_dir=None):
        super().__init__(master)
        self.standalone = bool(standalone)
        self.top = self.winfo_toplevel()
        self._i18n_widgets, self._i18n_tabs = [], []
        self._i18n_menus, self._i18n_titles = [], []
        self._menubtns = []
        self.lang_var = tk.StringVar(value=LANG.current_language())
        self.on_state_change = None
        self.info_lbl = None
        self.menubar_frame = None
        self.scene = Scene.new()
        self.gfx = Graphics(None)
        self.pic_dir = None
        self.idx, self.sel = 0, None
        self.multi = set()
        self.playing = False
        self._play_mode = "here"
        self.loop_a, self.loop_b = 0, None
        self._tl_drag = None
        self.undo_s, self.redo_s = [], []
        self.modified = False
        self.drag = None
        self.stroke = None
        self.way = []
        self.cursor_pos = None
        self._photo = None
        self._thumbs = []
        self.pal = None
        self._pal_job = None
        self.scope = tk.StringVar(value="frame")
        self.ball_h = tk.IntVar(value=0)
        self.move_path = tk.BooleanVar(value=False)
        self.all_paths = tk.BooleanVar(value=False)
        self.path_colors = dict(PATH_COLORS)
        self._path_cache = []
        self._path_label_ids = []
        self._path_sig_built = None
        self._thumb_cache = {}
        self._thumb_gfx = None
        self._poses_key = None
        self._tl_acts = []
        self._act_backup = {}
        self._path_photo = None
        self._path_static_id = None
        self._path_current_ids = []
        self._canvas_image_id = None
        self.vz, self.vx, self.vy = 1.0, 0.0, 0.0
        self.view_zoom = tk.DoubleVar(value=1.0)
        self._vp = None
        self.show_win = tk.BooleanVar(value=True)
        self.show_path = tk.BooleanVar(value=True)
        self.show_ids = tk.BooleanVar(value=False)
        self.follow = tk.BooleanVar(value=True)
        self.ghost = tk.StringVar()
        self.loop = tk.BooleanVar(value=True)
        self.fps = tk.IntVar(value=12)
        self.zoom = tk.IntVar(value=3 if self.winfo_screenwidth() >= 1600 else 2)
        self.speed = tk.DoubleVar(value=3.0)
        self.sx, self.sy = tk.IntVar(), tk.IntVar()
        self.cat_var = tk.StringVar()
        self.snd_var = tk.IntVar(value=-1)
        self.tool = tk.StringVar(value="select")
        self.tool_main = tk.StringVar(value="select")
        self.path_kind = tk.StringVar(value="draw")
        self.cam_whole = tk.BooleanVar(value=True)
        self.cam_follow = tk.BooleanVar(value=False)
        self.cam_target = None
        self.cam_i0, self.cam_snap, self.cam_explicit = 0, False, False
        self.pmode = tk.StringVar(value="speed")
        self.pframes = tk.IntVar(value=20)
        self.smooth = tk.BooleanVar(value=True)
        self.persp = tk.BooleanVar(value=False)
        self.auto_spr = tk.BooleanVar(value=True)
        self.diag = tk.BooleanVar(value=True)
        self.rope = tk.DoubleVar(value=5.0)
        self.pin = tk.BooleanVar(value=True)
        self.resume = tk.BooleanVar(value=True)
        self._t_pan = 0.0
        if self.standalone:
            self.top.title("TORE Editor")
            self.top.protocol("WM_DELETE_WINDOW", self.quit_app)
        else:
            self.menubar_frame = ttk.Frame(self)
            self.menubar_frame.pack(fill="x", side="top")
            ttk.Style(self).configure("Tore.Treeview", rowheight=20, font=("TkDefaultFont", 9))
        self._menus()
        self._layout()
        self._keys()
        self.load_gfx(path)
        if pic_dir:
            self.set_pic_dir(pic_dir, refresh=False)
        if path:
            self.open_path(path)
        else:
            self.cam_default()
            self.refresh()
        if self.standalone:
            self._startup_job = self.after(100, self.startup)
        else:
            self.bind("<Map>", self._on_map)
            self.bind("<Unmap>", self._on_unmap)
            self.after(300, self._show_data_warnings)

    def startup(self):
        if not self.pic_dir:
            self.choose_pic()
        self._show_data_warnings()

    def _show_data_warnings(self):
        if DATA_WARNINGS and self.winfo_exists():
            messagebox.showwarning(tr("mb.datafiles"), "\n".join(DATA_WARNINGS), parent=self.top)

    def _active(self):
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except tk.TclError:
            return False

    def _on_map(self, _e=None):
        self.after_idle(self._take_focus)

    def _take_focus(self):
        try:
            if self.winfo_exists() and self.winfo_ismapped():
                self.canvas.focus_set()
        except tk.TclError:
            pass

    def _on_unmap(self, _e=None):
        if self.playing:
            self.toggle(self._play_mode)

    def set_pic_dir(self, d, refresh=True):
        if not (d and os.path.isdir(d)):
            return False
        self.pic_dir = d
        self.gfx = Graphics(d)
        self._close_palette()
        if self.gfx.missing:
            self.note(tr("st.pic_missing", files=", ".join(self.gfx.missing)))
        else:
            self.note(tr("st.pic_dir", dir=d))
        if refresh:
            self.refresh()
        return True

    def clear_pic_dir(self, refresh=True):
        self._close_palette()
        self.load_gfx(None)
        if refresh:
            self.refresh()

    def is_dirty(self):
        return bool(self.modified)

    def _set_title(self, fn, n):
        mod = " *" if self.modified else ""
        if self.standalone:
            self.top.title("TORE Editor - By Theruler76 - %s%s   %s" % (fn, mod, tr("title.frame", i=self.idx + 1, n=n)))
        elif self.info_lbl is not None:
            self.info_lbl.config(text="%s%s   %s" % (fn, mod, tr("title.frame", i=self.idx + 1, n=n)))
        cb = self.on_state_change
        if cb:
            try:
                cb(self.modified)
            except Exception:
                pass

    def _exit_items(self):
        return ((None, None, None), ("f.exit", self.quit_app, "")) if self.standalone else ()

    def tr(self, key, **fmt):
        return tr(key, **fmt)

    def _reg(self, widget, key):
        widget.config(text=self.tr(key))
        self._i18n_widgets.append((widget, key))
        return widget

    def _reg_tab(self, tab, key):
        self._i18n_tabs.append((tab, key))
        return tab

    def _mi(self, parent, kind, key, fmt=None, **kw):
        fmt = fmt or {}
        getattr(parent, "add_" + kind)(label=self.tr(key, **fmt), **kw)
        self._i18n_menus.append((parent, parent.index("end"), key, fmt))

    def _add(self, menu, key, cmd, acc):
        if key is None:
            menu.add_separator()
        else:
            self._mi(menu, "command", key, command=cmd, accelerator=acc)

    def set_language(self, code):
        if not LANG.set_language(code):
            self.lang_var.set(LANG.current_language())
            return False
        _save_language(code)
        self.lang_var.set(code)
        self.retranslate()
        return True

    @staticmethod
    def _alive(w):
        try:
            return bool(w.winfo_exists())
        except tk.TclError:
            return False

    def retranslate(self):
        keep = []
        for w, k in self._i18n_widgets:
            if self._alive(w):
                try:
                    w.config(text=self.tr(k))
                    keep.append((w, k))
                except tk.TclError:
                    pass
        self._i18n_widgets = keep
        keep = []
        for t, k in self._i18n_tabs:
            if self._alive(t):
                try:
                    t.master.tab(t, text=self.tr(k))
                    keep.append((t, k))
                except tk.TclError:
                    pass
        self._i18n_tabs = keep
        keep = []
        for mn, idx, k, fmt in self._i18n_menus:
            if self._alive(mn):
                try:
                    mn.entryconfigure(idx, label=self.tr(k, **fmt))
                    keep.append((mn, idx, k, fmt))
                except tk.TclError:
                    pass
        self._i18n_menus = keep
        keep = []
        for win, k in self._i18n_titles:
            if self._alive(win):
                win.title(self.tr(k))
                keep.append((win, k))
        self._i18n_titles = keep
        self.tree.heading("#0", text=self.tr("tree.sprite"))
        sel = self.cb_ghost.current()
        self.cb_ghost.config(values=[self.tr(k) for k in GHOST_KEYS])
        self.cb_ghost.current(max(0, sel))
        self._play_buttons()
        self.hint = self.tr("hint." + self.tool.get())
        self.show_tool_options()
        self.build_action_grid()
        self.refresh()
        self.note(self.hint)

    def _lang_menu(self, lm):
        self.lang_var.set(LANG.current_language())
        for code, name in LANG.discover_languages():
            lm.add_radiobutton(label=name, value=code, variable=self.lang_var, command=lambda c=code: self.set_language(c))
        for msg in LANG.take_problems():
            self.after(200, lambda m=msg: messagebox.showwarning(self.tr("mb.datafiles"), m, parent=self.top))

    def _menus(self):
        self._i18n_menus = []
        if self.standalone:
            m = tk.Menu(self.top)

            def newmenu(key):
                sm = tk.Menu(m, tearoff=0)
                m.add_cascade(label=self.tr(key), menu=sm)
                self._i18n_menus.append((m, m.index("end"), key, {}))
                return sm
        else:
            m = None
            for mb in self._menubtns:
                mb.destroy()
            self._menubtns = []

            def newmenu(key):
                mb = self._reg(ttk.Menubutton(self.menubar_frame), key)
                self._menubtns.append(mb)
                sm = tk.Menu(mb, tearoff=0)
                mb.config(menu=sm)
                mb.pack(side="left", padx=(0, 2))
                return sm
        f = newmenu("m.file")
        for key, cmd, acc in (("f.new", self.new_scene, "Ctrl+N"), ("f.open", self.open_dialog, "Ctrl+O"),
                              ("f.save", self.save, "Ctrl+S"), ("f.saveas", self.save_as, "Ctrl+Shift+S"),
                              ("f.numbered", self.save_numbered, ""),  (None, None, None), ("f.gif", self.export_gif, ""), (None, None, None),
                              ("f.pic", self.choose_pic, ""), ("f.delete", self.delete_file, ""), *self._exit_items()):
            self._add(f, key, cmd, acc)

        e = newmenu("m.edit")
        for key, cmd, acc in (("undo", self.undo, "Ctrl+Z"), ("redo", self.redo, "Ctrl+Y"), (None, None, None),
                              ("e.selall", self.select_all, "Ctrl+A"), (None, None, None),
                              ("e.insframe", self.ins_frame, "Ins"), ("e.delframe", self.del_frame, "Del"),
                              ("e.clearfilm", self.clear_film, ""), (None, None, None), ("e.mirror", lambda: self.mirror(True, True), ""),
                              ("e.swap", lambda: self.mirror(False, True), ""), (None, None, None), ("e.props", self.props, "")):
            self._add(e, key, cmd, acc)

        fg = newmenu("m.sprite")
        self._mi(fg, "cascade", "s.action", menu=self._action_menu(fg))
        self._mi(fg, "cascade", "s.run", menu=self._run_menu(fg))
        for key, cmd in (("s.auto_here", self.auto_here), ("s.auto_all", lambda: self.auto_here(True)), (None, None), ("s.mirrorpose", self.mirror_sel), ("s.lock", self.clear_anim), ("s.program", self.program_anim)):
            self._add(fg, key, cmd, "")

        p = newmenu("m.path")
        for key, cmd, acc in (("p.draw", lambda: self.tool.set("draw") or self.set_tool(), "D"),
                              ("p.way", lambda: self.tool.set("way") or self.set_tool(), "P"),
                              (None, None, None),
                              ("p.smooth", self.smooth_path, ""),
                              ("p.even", self.even_speed, ""),
                              ("p.freeze", self.freeze_here, ""),
                              ("p.tween", self.tween, ""),
                              (None, None, None),
                              ("p.cam_from", self.auto_camera, ""),
                              ("p.cam_all", lambda: self.auto_camera(True), ""),
                              ("p.tween_scroll", self.tween_scroll, ""),
                              ("p.scroll_end", self.scroll_to_end, "")):
            self._add(p, key, cmd, acc)
        p.add_separator()
        pcm = tk.Menu(p, tearoff=0)
        for key, label in PATH_COLOR_LABELS:
            self._mi(pcm, "command", label, command=lambda k=key: self.pick_path_color(k))
        pcm.add_separator()
        self._mi(pcm, "command", "p.colors_reset", command=self.reset_path_colors)
        self._mi(p, "cascade", "p.colors", menu=pcm)

        v = newmenu("m.view")
        self._mi(v, "checkbutton", "v.path", variable=self.show_path, command=self.refresh)
        self._mi(v, "checkbutton", "v.allpaths", variable=self.all_paths, command=self.refresh)
        self._mi(v, "checkbutton", "v.cam", variable=self.show_win, command=self.refresh)
        self._mi(v, "checkbutton", "v.ids", variable=self.show_ids, command=self.refresh)
        v.add_separator()
        self._mi(v, "command", "v.zoom_in", command=lambda: self.set_zoom(1), accelerator="Ctrl++")
        self._mi(v, "command", "v.zoom_out", command=lambda: self.set_zoom(-1), accelerator="Ctrl+-")
        v.add_separator()
        self._mi(v, "command", "v.area_in", command=lambda: self.set_view_zoom(self.vz * 1.5))
        self._mi(v, "command", "v.area_out", command=lambda: self.set_view_zoom(self.vz / 1.5))
        self._mi(v, "command", "v.area_reset", command=self.view_reset)
        v.add_separator()
        lm = tk.Menu(v, tearoff=0)
        self._mi(v, "cascade", "h.language", menu=lm)
        self._lang_menu(lm)

        dm = newmenu("m.data")
        for key, cmd in (("d.edit", self.edit_data), ("d.reload", self.reload_data), (None, None), ("d.kickoff", self.save_kickoff_here)):
            self._add(dm, key, cmd, "")

        h = newmenu("m.help")
        self._mi(h, "command", "h.quick", command=self.help)
        if self.standalone:
            self.top.config(menu=m)

    def _layout(self):
        z = self.z()
        tb = ttk.Frame(self)
        tb.pack(fill="x", padx=8, pady=(6, 0))
        self.tool_btns = {}
        for key, lkey in (("select", "tb.select"), ("path", "tb.path"), ("pan", "tb.pan")):
            b = self._reg(ttk.Button(tb, width=14, takefocus=False, command=lambda k=key: self.pick_main(k)), lkey)
            b.pack(side="left", padx=(0, 4))
            self.tool_btns[key] = b
        self._reg(ttk.Button(tb, width=14, takefocus=False, command=self.open_palette), "tb.sheet").pack(side="left", padx=(0, 0))
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=(6, 4))
        self._reg(ttk.Button(tb, width=8, takefocus=False, command=self.undo), "undo").pack(side="left", padx=(0, 4))
        self._reg(ttk.Button(tb, width=8, takefocus=False, command=self.redo), "redo").pack(side="left")
        if not self.standalone:
            self.info_lbl = ttk.Label(tb, foreground="#555")
            self.info_lbl.pack(side="right", padx=(8, 0))

        self.opt = ttk.LabelFrame(self)
        self.opt.pack(fill="x", padx=8, pady=(6, 0))
        self.opt_frames = {}

        o = ttk.Frame(self.opt)
        self.opt_frames["select"] = o
        self._reg(ttk.Label(o), "o.rope").pack(side="left", padx=(6, 0))
        ttk.Spinbox(o, from_=0.5, to=40, increment=0.5, width=4, textvariable=self.rope).pack(side="left", padx=2)
        self._reg(ttk.Checkbutton(o, variable=self.pin), "o.pin").pack(side="left", padx=8)
        self._reg(ttk.Checkbutton(o, variable=self.move_path), "o.movepath").pack(side="left", padx=8)

        o = ttk.Frame(self.opt)
        self.opt_frames["path"] = o
        self._reg(ttk.Radiobutton(o, value="draw", variable=self.path_kind, command=self.on_path_kind), "o.draw").pack(side="left", padx=(6, 0))
        self._reg(ttk.Radiobutton(o, value="way", variable=self.path_kind, command=self.on_path_kind), "o.click").pack(side="left", padx=(6, 0))
        self.mode_slot = ttk.Frame(o)
        self.mode_slot.pack(side="left", padx=(10, 0))
        self.cb_persp = self._reg(ttk.Checkbutton(self.mode_slot, variable=self.persp), "o.persp")
        self.rb_timing = self._reg(ttk.Radiobutton(self.mode_slot, value="timing", variable=self.pmode), "o.realtime")
        ttk.Separator(o, orient="vertical").pack(side="left", fill="y", padx=8)
        self._reg(ttk.Radiobutton(o, value="speed", variable=self.pmode), "o.speed").pack(side="left")
        ttk.Spinbox(o, from_=0.5, to=40, increment=0.5, width=5, textvariable=self.speed).pack(side="left", padx=2)
        self._reg(ttk.Label(o), "o.pxframe").pack(side="left")
        self._reg(ttk.Radiobutton(o, value="frames", variable=self.pmode), "o.duration").pack(side="left", padx=(10, 0))
        ttk.Spinbox(o, from_=1, to=MAX_FRAMES, width=4, textvariable=self.pframes).pack(side="left", padx=2)
        self._reg(ttk.Label(o), "o.frames").pack(side="left")
        ttk.Separator(o, orient="vertical").pack(side="left", fill="y", padx=8)
        self._reg(ttk.Checkbutton(o, variable=self.smooth), "o.smooth").pack(side="left")
        self._reg(ttk.Checkbutton(o, variable=self.auto_spr), "o.autorun").pack(side="left", padx=4)
        self._reg(ttk.Checkbutton(o, variable=self.diag), "o.diag").pack(side="left")
        self._reg(ttk.Checkbutton(o, variable=self.follow), "o.follow").pack(side="left", padx=4)

        o = ttk.Frame(self.opt)
        self.opt_frames["pan"] = o
        self._reg(ttk.Label(o), "o.scrollx").pack(side="left", padx=(6, 0))
        ttk.Spinbox(o, from_=0, to=SCROLL_MAX_X, width=4, textvariable=self.sx, command=self.set_scroll).pack(side="left")
        self._reg(ttk.Label(o), "o.scrolly").pack(side="left", padx=(6, 0))
        ttk.Spinbox(o, from_=0, to=SCROLL_MAX_Y, width=3, textvariable=self.sy, command=self.set_scroll).pack(side="left")
        ttk.Separator(o, orient="vertical").pack(side="left", fill="y", padx=8)
        self.cb_camfol = self._reg(ttk.Checkbutton(o, variable=self.cam_follow, command=self.on_cam_follow), "o.camfollow")
        self.cb_camfol.pack(side="left")
        self._reg(ttk.Checkbutton(o, variable=self.cam_whole, command=self.on_cam_whole), "o.wholefilm").pack(side="left", padx=6)
        self.cam_lbl = ttk.Label(o, foreground="#777")
        self.cam_lbl.pack(side="left", padx=4)

        t1 = ttk.Frame(self)
        t1.pack(fill="x", padx=8, pady=(6, 0))
        self._reg(ttk.Label(t1), "sc.label").pack(side="left")
        self._reg(ttk.Radiobutton(t1, value="frame", variable=self.scope), "sc.frame").pack(side="left", padx=4)
        self._reg(ttk.Radiobutton(t1, value="end", variable=self.scope), "sc.end").pack(side="left")
        ttk.Separator(t1, orient="vertical").pack(side="left", fill="y", padx=8)
        self._reg(ttk.Label(t1), "ball.h").pack(side="left")
        self.sp_h = ttk.Spinbox(t1, from_=-MAX_Y, to=MAX_Y - BALL_Y_MIN, width=4, textvariable=self.ball_h, command=self.set_ball_h)
        self.sp_h.pack(side="left", padx=2)
        self.sp_h.bind("<Return>", self.set_ball_h)
        self.sp_h.bind("<FocusOut>", self.set_ball_h)
        ttk.Separator(t1, orient="vertical").pack(side="left", fill="y", padx=8)
        self._reg(ttk.Label(t1), "ghost.label").pack(side="left")
        cb = self.cb_ghost = ttk.Combobox(t1, textvariable=self.ghost, values=[tr(k) for k in GHOST_KEYS], state="readonly", width=30)
        cb.current(0)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        self._reg(ttk.Checkbutton(t1, variable=self.show_path, command=self.refresh), "chk.path").pack(side="left", padx=4)
        self._reg(ttk.Checkbutton(t1, variable=self.all_paths, command=self.refresh), "chk.allpaths").pack(side="left")
        self._reg(ttk.Checkbutton(t1, variable=self.show_win, command=self.refresh), "chk.cam").pack(side="left")
        self._reg(ttk.Checkbutton(t1, variable=self.show_ids, command=self.refresh), "chk.ids").pack(side="left", padx=4)

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=8, pady=6)
        left = ttk.Frame(body)
        left.pack(side="left", fill="both", expand=True)
        cf = ttk.Frame(left)
        cf.pack()
        self.canvas = tk.Canvas(cf, bg="black", highlightthickness=0, width=FW * z, height=FH * z, cursor="arrow")
        self.canvas.grid(row=0, column=0)
        self.vbar = ttk.Scrollbar(cf, orient="vertical", command=lambda *a: self.view_scroll("y", *a))
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar = ttk.Scrollbar(cf, orient="horizontal", command=lambda *a: self.view_scroll("x", *a))
        self.hbar.grid(row=1, column=0, sticky="ew")
        bar = ttk.Frame(left)
        bar.pack(fill="x", pady=(6, 0))
        for t, c, w in (("|<", lambda: self.goto(0), 3), ("<", lambda: self.step(-1), 3)):
            ttk.Button(bar, text=t, width=w, takefocus=False, command=c).pack(side="left", padx=(0,4))
        self.btn = ttk.Button(bar, text=tr("play.all"), width=9, takefocus=False, command=lambda: self.toggle("all"))
        self.btn.pack(side="left", padx=(0,4))
        self.btn2 = ttk.Button(bar, text=tr("play.here"), width=13, takefocus=False, command=lambda: self.toggle("here"))
        self.btn2.pack(side="left", padx=(0,4))
        for t, c, w in ((">", lambda: self.step(1), 3), (">|", lambda: self.goto(len(self.scene.frames) - 1), 3)):
            ttk.Button(bar, text=t, width=w, takefocus=False, command=c).pack(side="left", padx=(0,4))
        self._reg(ttk.Button(bar, command=self.ins_frame), "fr.add").pack(side="left", padx=(12, 2))
        self._reg(ttk.Button(bar, command=self.del_frame), "fr.del").pack(side="left", padx=(2,4))
        self._reg(ttk.Checkbutton(bar, variable=self.loop), "loop").pack(side="left", padx=8)
        self._reg(ttk.Label(bar), "fps").pack(side="left")
        ttk.Spinbox(bar, from_=1, to=60, width=4, textvariable=self.fps).pack(side="left", padx=(2, 8))
        self._reg(ttk.Label(bar), "fieldsize").pack(side="left")
        ttk.Spinbox(bar, from_=1, to=6, width=3, textvariable=self.zoom, command=self.rezoom).pack(side="left", padx=2)
        self._reg(ttk.Label(bar), "zoomarea").pack(side="left", padx=(8, 0))
        sv = ttk.Spinbox(bar, from_=1, to=VIEW_ZOOM_MAX, increment=0.5, width=4, textvariable=self.view_zoom, command=self.on_view_zoom)
        sv.pack(side="left", padx=2)
        sv.bind("<Return>", self.on_view_zoom)
        ttk.Button(bar, text="1:1", width=4, takefocus=False, command=self.view_reset).pack(side="left", padx=2)
        self.tl = tk.Canvas(left, height=90, bg="#f2f2f2", highlightthickness=1, highlightbackground="#bbb")
        self.tl.pack(fill="x", pady=(6, 0))
        self.tl.bind("<Button-1>", self.on_tl_press)
        self.tl.bind("<B1-Motion>", self.on_tl_drag)
        self.tl.bind("<ButtonRelease-1>", self.on_tl_release)
        for b in ("<Button-3>", "<Button-2>"):
            self.tl.bind(b, self.on_tl_right)
        self.tl.bind("<Configure>", lambda e: self.draw_timeline())
        
        self._reg(ttk.Label(left,foreground="#777"), "tl.legend").pack(anchor="w")
        self.status = ttk.Label(left, anchor="w")
        self.status.pack(fill="x", pady=(2, 0))

        right = ttk.Frame(body)
        right.pack(side="right", fill="y", padx=(8, 0))
        hdr = ttk.Frame(right)
        hdr.pack(fill="x")
        self._reg(ttk.Label(hdr), "sel.multi").pack(side="left")
        tf = ttk.Frame(right)
        tf.pack(fill="x")
        self.tree = ttk.Treeview(tf, columns=("x", "y", "pose"), height=6, selectmode="extended", style="Treeview" if self.standalone else "Tore.Treeview")
        self.tree.heading("#0", text=tr("tree.sprite"))
        for c, w in (("x", 38), ("y", 38), ("pose", 42)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="e")
        self.tree.column("#0", width=110)
        sb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left")
        sb.pack(side="left", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self.on_tree)

        nb = ttk.Notebook(right)
        nb.pack(fill="x", pady=(8, 0))
        pf = ttk.Frame(nb)
        nb.add(self._reg_tab(pf, "tab.poses"), text=tr("tab.poses"))
        self.cat_cb = ttk.Combobox(pf, textvariable=self.cat_var, state="readonly", width=34)
        self.cat_cb.pack(padx=4, pady=4)
        self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self.draw_poses())
        self.pose_cv = tk.Canvas(pf, width=5 * 44, height=150, highlightthickness=0)
        self.pose_cv.pack(padx=4)
        self.pose_cv.bind("<Button-1>", self.on_pose_click)
        self.pose_info = ttk.Label(pf, text="", foreground="#555")
        self.pose_info.pack(anchor="w", padx=4, pady=(2, 4))

        af = ttk.Frame(nb)
        nb.add(self._reg_tab(af, "tab.actions"), text=tr("tab.actions"))
        self._reg(ttk.Label(af, foreground="#555"), "act.intro").pack(anchor="w", padx=6, pady=(2, 2))
        self.act_grid = ttk.Frame(af)
        self.act_grid.pack(fill="x")
        self.build_action_grid()
        self._reg(ttk.Checkbutton(af, variable=self.resume), "act.resume").pack(anchor="w", padx=6, pady=(2, 2))
        self._reg(ttk.Label(af, foreground="#555"), "act.rundir").pack(anchor="w", padx=6)
        cp = ttk.Frame(af)
        cp.pack(pady=2)
        for r, row in enumerate((("NW", "N", "NE"), ("W", None, "E"), ("SW", "S", "SE"))):
            for c, d in enumerate(row):
                if d is None:
                    self._reg(ttk.Button(cp, width=8, command=self.do_stand), "act.stand").grid(row=r, column=c, padx=1, pady=1)
                else:
                    self._reg(ttk.Button(cp, width=8, command=lambda d=d: self.do_cycle(d)), "dir.abbr." + d).grid(row=r, column=c, padx=1, pady=1)

        sf = ttk.Frame(nb)
        nb.add(self._reg_tab(sf, "tab.sound"), text=tr("tab.sound"))
        self._reg(ttk.Radiobutton(sf, value=-1, variable=self.snd_var, command=self.set_sound), "snd.none").pack(anchor="w", padx=4)
        for k, (nm, col) in enumerate(SOUNDS):
            r = tk.Frame(sf)
            r.pack(fill="x", padx=4)
            tk.Label(r, bg=col, width=1).pack(side="left", padx=(0, 4))
            self._reg(ttk.Radiobutton(r, value=k, variable=self.snd_var, command=self.set_sound), nm).pack(side="left")

        self.set_tool()


    def _keys(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<ButtonPress-1>", lambda e: c.focus_set(), add="+")
        c.bind("<B1-Motion>", self.on_motion)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Double-Button-1>", self.on_dbl)
        c.bind("<Motion>", self.on_hover)
        c.bind("<Leave>", lambda e: c.delete("hover"))
        for b in ("<Button-3>", "<Button-2>") if sys.platform == "darwin" else ("<Button-3>",):
            c.bind(b, self.on_right)
        if sys.platform != "darwin":
            c.bind("<ButtonPress-2>", self.view_pan_start)
            c.bind("<B2-Motion>", self.view_pan_move)
            c.bind("<ButtonRelease-2>", self.view_pan_end)
        c.bind("<MouseWheel>", lambda e: self.wheel(e, -1 if e.delta > 0 else 1))
        c.bind("<Button-4>", lambda e: self.wheel(e, -1))
        c.bind("<Button-5>", lambda e: self.wheel(e, 1))

        def tool_key(t):
            def f(e):
                if isinstance(e.widget, (tk.Entry, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
                    return
                self.tool.set(t)
                self.set_tool()
            return f
        def space_key(e):
            if isinstance(e.widget, (tk.Entry, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
                return None
            self.toggle("here")
            return "break"

        space_tag = "TORE_EDITOR_SPACE"
        self.top.bind_class(space_tag, "<space>", space_key)

        def install_space_tag(w):
            if isinstance(w, (tk.Entry, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
                return
            tags = list(w.bindtags())
            if space_tag in tags:
                tags.remove(space_tag)
            w.bindtags((space_tag, *tags))
            for child in w.winfo_children():
                install_space_tag(child)

        install_space_tag(self)
        for k, fn in ((("<space>"), space_key), ("<Left>", lambda e: self.nudge(-1, 0, e)),
                      ("<Right>", lambda e: self.nudge(1, 0, e)), ("<Up>", lambda e: self.nudge(0, -1, e)),
                      ("<Down>", lambda e: self.nudge(0, 1, e)), ("<Prior>", lambda e: self.step(-1)),
                      ("<Next>", lambda e: self.step(1)), ("<comma>", lambda e: self.step(-1)),
                      ("<period>", lambda e: self.step(1)), ("<Home>", lambda e: self.goto(0)),
                      ("<End>", lambda e: self.goto(len(self.scene.frames) - 1)),
                      ("<bracketleft>", lambda e: self.cycle_pose(-1)), ("<bracketright>", lambda e: self.cycle_pose(1)),
                      ("<Escape>", lambda e: self.escape()), ("<Return>", lambda e: self.finish_way()),
                      ("<BackSpace>", lambda e: self.way_back()),
                      ("<Insert>", lambda e: self.ins_frame()), ("<Delete>", lambda e: self.del_frame()),
                      ("<Control-z>", lambda e: self.undo()), ("<Control-y>", lambda e: self.redo()),
                      ("<Control-a>", lambda e: self.select_all()),
                      ("<Control-s>", lambda e: self.save()), ("<Control-o>", lambda e: self.open_dialog()),
                      ("<Control-n>", lambda e: self.new_scene()), ("<Control-S>", lambda e: self.save_as()),
                      ("<Control-plus>", lambda e: self.set_zoom(1)), ("<Control-equal>", lambda e: self.set_zoom(1)),
                      ("<Control-minus>", lambda e: self.set_zoom(-1)),
                      ("<KeyPress-v>", tool_key("select")), ("<KeyPress-d>", tool_key("draw")),
                      ("<KeyPress-p>", tool_key("way")), ("<KeyPress-h>", tool_key("pan"))):
            self.top.bind(k, self._guarded(fn), add="+")

    def _guarded(self, fn):
        def handler(e):
            if self._active():
                return fn(e)
            return None
        return handler


    @property
    def fr(self):
        return self.scene.frames[self.idx]

    def z(self):
        try:
            return max(1, int(self.zoom.get()))
        except (tk.TclError, ValueError):
            return 3

    def note(self, txt):
        self.status.config(text=txt)

    def _state(self):
        return (copy.deepcopy(self.scene.frames), list(self.scene.events), self.scene.author, self.idx)

    def snap(self):
        self.undo_s.append(self._state())
        del self.undo_s[:-100]
        self.redo_s.clear()
        self.modified = True

    def _restore(self, st):
        self.scene.frames, self.scene.events, self.scene.author, self.idx = st
        self.cam_release()
        self.idx = min(self.idx, len(self.scene.frames) - 1)
        self.refresh()

    def undo(self):
        if self.undo_s:
            self.redo_s.append(self._state())
            self._restore(self.undo_s.pop())

    def redo(self):
        if self.redo_s:
            self.undo_s.append(self._state())
            self._restore(self.redo_s.pop())

    def frames_in_scope(self):
        return range(self.idx, len(self.scene.frames)) if self.scope.get() == "end" else [self.idx]

    def partner(self, sl):
        c = cls(self.fr.figs[sl][2])
        if c in "SB":
            return self.fr.index_of("B" if c == "S" else "S")
        return None

    def move_fig(self, sl, dx, dy):
        if cls(self.fr.figs[sl][2]) in "LR":
            return
        ids = {sl} | (self.multi if sl in self.multi else set())
        if cls(self.fr.figs[sl][2]) == "B" and ids == {sl}:
            dx = 0
        else:
            ids |= {p for p in map(self.partner, ids) if p is not None}
        ids = {s for s in ids if cls(self.fr.figs[s][2]) not in "LR"}
        rng = range(len(self.scene.frames)) if self.move_path.get() else self.frames_in_scope()
        lox, hix, loy, hiy = -10 ** 6, 10 ** 6, -10 ** 6, 10 ** 6
        for i in rng:
            for s in ids:
                g = self.scene.frames[i].figs[s]
                xl, xh = xlim(g[2])
                lox, hix = max(lox, xl - g[0]), min(hix, xh - g[0])
                loy, hiy = max(loy, self._ylo(g[2]) - g[1]), min(hiy, MAX_Y - g[1])
        dx = max(lox, min(hix, dx))
        dy = max(loy, min(hiy, dy))
        for i in rng:
            f = self.scene.frames[i]
            for s in ids:
                f.figs[s][0] += dx
                f.figs[s][1] += dy
            f.touch()

    def set_ball_h(self, _e=None):
        try:
            h = int(self.ball_h.get())
        except (tk.TclError, ValueError):
            return
        h = max(-MAX_Y, min(MAX_Y - BALL_Y_MIN, h))
        s, b = self.fr.index_of("S"), self.fr.index_of("B")
        if s is None or b is None:
            return
        if h == self.fr.figs[s][1] - self.fr.figs[b][1]:
            return
        self.snap()
        for i in self.frames_in_scope():
            f = self.scene.frames[i]
            f.figs[b][1] = max(BALL_Y_MIN, min(MAX_Y, f.figs[s][1] - h))
            f.touch()
        self.refresh()

    def ref_slot(self, sl=None):
        sl = self.sel if sl is None else sl
        if sl is None or sl >= len(self.fr.figs):
            return sl
        if cls(self.fr.figs[sl][2]) == "B":
            s = self.fr.index_of("S")
            return s if s is not None else sl
        return sl

    def path_color(self, sid):
        c = cls(sid)
        if c in "SB":
            return self.path_colors["ball"]
        t = team_of(sid)
        return self.path_colors["red" if t == "R" else "blue" if t == "B" else "ref"]

    def pick_path_color(self, key):
        label = tr(dict(PATH_COLOR_LABELS)[key])
        res = colorchooser.askcolor(color=self.path_colors[key], title=tr("p.color_title", name=label), parent=self.top)
        if res and res[1]:
            self.path_colors[key] = res[1]
            self.refresh()

    def reset_path_colors(self):
        self.path_colors = dict(PATH_COLORS)
        self.refresh()

    def sc(self):
        return self.z() * self.vz

    def cx(self, x):
        return (x - self.vx) * self.sc()

    def cy(self, y):
        return (y - self.vy) * self.sc()

    def fx(self, ex):
        return ex / self.sc() + self.vx

    def fy(self, ey):
        return ey / self.sc() + self.vy

    def box(self, x, y, sid):
        return (self.cx(x), self.cy(y + Y_OFFSET), self.cx(x + sprite_w(sid)), self.cy(y + Y_OFFSET + CELL_H))

    def clamp_view(self):
        self.vz = max(1.0, min(VIEW_ZOOM_MAX, float(self.vz)))
        self.vx = max(0.0, min(FW - FW / self.vz, self.vx))
        self.vy = max(0.0, min(FH - FH / self.vz, self.vy))

    def update_view_bars(self):
        vw, vh = FW / self.vz, FH / self.vz
        self.hbar.set(self.vx / FW, (self.vx + vw) / FW)
        self.vbar.set(self.vy / FH, (self.vy + vh) / FH)

    def set_view_zoom(self, nz, ax=None, ay=None):
        z = self.z()
        if ax is None:
            ax, ay = FW * z / 2, FH * z / 2
        fxa, fya = self.fx(ax), self.fy(ay)
        self.vz = max(1.0, min(VIEW_ZOOM_MAX, float(nz)))
        self.view_zoom.set(round(self.vz, 2))
        s = self.sc()
        self.vx, self.vy = fxa - ax / s, fya - ay / s
        self.clamp_view()
        self.refresh()

    def on_view_zoom(self, _e=None):
        try:
            v = float(self.view_zoom.get())
        except (tk.TclError, ValueError):
            return
        self.set_view_zoom(v)

    def view_reset(self):
        self.vx = self.vy = 0.0
        self.set_view_zoom(1.0)

    def view_scroll(self, axis, *args):
        vw, vh = FW / self.vz, FH / self.vz
        span = vw if axis == "x" else vh
        cur = self.vx if axis == "x" else self.vy
        full = FW if axis == "x" else FH
        if args[0] == "moveto":
            cur = float(args[1]) * full
        else:
            n = int(args[1])
            cur += n * (span * (0.9 if args[2] == "pages" else 0.1))
        if axis == "x":
            self.vx = cur
        else:
            self.vy = cur
        self.clamp_view()
        self.refresh(light=True)

    def wheel(self, e, d):
        if e.state & 4:
            self.set_view_zoom(self.vz * (1.25 if d < 0 else 0.8), e.x, e.y)
        else:
            self.step(d)

    def view_pan_start(self, e):
        self._vp = (e.x, e.y, self.vx, self.vy)
        self.canvas.config(cursor="fleur")

    def view_pan_move(self, e):
        if not self._vp:
            return
        x0, y0, vx0, vy0 = self._vp
        s = self.sc()
        self.vx, self.vy = vx0 - (e.x - x0) / s, vy0 - (e.y - y0) / s
        self.clamp_view()
        self.refresh(light=True)

    def view_pan_end(self, _e=None):
        self._vp = None
        self.set_tool_cursor()

    def set_tool_cursor(self):
        self.canvas.config(cursor={"select": "arrow", "draw": "pencil", "way": "crosshair", "pan": "fleur"}[self.tool.get()])


    def targets(self):
        ids = set(self.multi)
        if self.sel is not None:
            ids.add(self.sel)
        ids = [s for s in sorted(ids) if s < len(self.fr.figs) and cls(self.fr.figs[s][2]) not in "LR"]
        if self.sel in ids:
            ids.remove(self.sel)
            ids.insert(0, self.sel)
        return ids

    @staticmethod
    def conv_pose(pid, tgt_sid):
        tp, tt = team_of(pid), team_of(tgt_sid)
        if tp in ("R", "B") and tt in ("R", "B"):
            return pid - (0 if tp == "R" else 59) + (0 if tt == "R" else 59)
        if tp == "A" and tt == "A":
            return pid
        if tp is None and tt is None and cls(pid) == cls(tgt_sid):
            return pid
        return None

    def set_pose_all(self, pid):
        for sl in self.targets():
            p = pid if sl == self.sel else self.conv_pose(pid, self.fr.figs[sl][2])
            if p is not None:
                self.set_pose_to(sl, p)

    def set_pose_to(self, sl, pid):
        pid = max(0, min(145, pid))
        for i in self.frames_in_scope():
            self.scene.frames[i].figs[sl][2] = pid
            self.scene.frames[i].touch()

    def nudge(self, dx, dy, e):
        if self.focus_get() not in (self, self.top, self.canvas) or self.sel is None:
            return
        k = 5 if (e.state & 1) else 1
        self.snap()
        self.move_fig(self.sel, dx * k, dy * k)
        self.refresh()

    def cycle_pose(self, d):
        if self.sel is None:
            return
        cur = self.fr.figs[self.sel][2]
        for _, ids in cats_for(cur):
            if cur in ids:
                self.snap()
                self.set_pose_all(ids[(ids.index(cur) + d) % len(ids)])
                return self.refresh()

    def hit_all(self, px, py):
        out = []
        for sl in reversed(self.fr.order):
            x, y, sid = self.fr.figs[sl]
            if sid >= 1000:
                continue
            w = sprite_w(sid)
            pad = 3 if w == 4 else 0
            if x - pad <= px < x + w + pad and y + Y_OFFSET - pad <= py < y + Y_OFFSET + CELL_H + pad:
                out.append(sl)
        return out

    def hit(self, px, py):
        h = self.hit_all(px, py)
        return h[0] if h else None

    def pick_cand(self, cands):
        if not cands:
            return None
        return self.sel if self.sel in cands else cands[0]

    def pan_click(self, cands, ctrl):
        if ctrl:
            return self.select(cands[0], add=True)
        if self.sel in cands and len(cands) > 1 and len(self.multi) <= 1:
            sl = cands[(cands.index(self.sel) + 1) % len(cands)]
        else:
            sl = self.sel if self.sel in cands else cands[0]
        self.select(sl)
        if len(cands) > 1:
            self.note(tr("st.overlap", name=self.names().get(sl, tr("name.sprite")), i=cands.index(sl) + 1, n=len(cands)))

    def on_hover(self, e):
        fxp, fyp = self.fx(e.x), self.fy(e.y)
        px, py = int(math.floor(fxp)), int(math.floor(fyp))
        c = self.canvas
        c.delete("hover")
        t = self.tool.get()
        self.cursor_pos = (fxp, fyp)
        if t == "way" and self.way:
            self.draw_overlay()
        cands = self.hit_all(px, py)
        sl = self.pick_cand(cands)
        k = self.path_hit(e.x, e.y) if (t == "select" and sl is None) else None
        if sl is not None:
            x, y, sid = self.fr.figs[sl]
            c.create_rectangle(*self.box(x, y, sid), outline="white", dash=(2, 2), tags="hover")
            extra = tr("st.hover_extra", n=len(cands)) if len(cands) > 1 else ""
            self.note(tr("st.hover_sprite", x=px, y=py - Y_OFFSET, sid=sid, f=self.idx + 1, n=len(self.scene.frames), extra=extra))
        elif k is not None:
            cx, cy = self.ctr(self.scene.frames[k].figs[self.ref_slot()])
            c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#ff9800", width=2, tags="hover")
            self.note(tr("st.hover_path", n=k + 1))
        else:
            self.note(tr("st.hover_idle", x=px, y=py - Y_OFFSET, f=self.idx + 1, n=len(self.scene.frames), hint=self.hint))


    def on_press(self, e):
        self.canvas.focus_set()
        px, py = self.fx(e.x), self.fy(e.y)
        t = self.tool.get()
        ctrl = bool(e.state & 4)
        cands = self.hit_all(int(math.floor(px)), int(math.floor(py)))
        sl = self.pick_cand(cands)
        if t == "pan":
            if cands:
                return self.pan_click(cands, ctrl)
            self.drag = dict(kind="win", x0=e.x, y0=e.y, a=tuple(self.fr.scroll), snapped=False, moved=False, live=False, pos=None)
            return
        if t == "draw":
            if sl is not None and sl != self.sel:
                self.select(sl)
            rs = self.ref_slot()
            if rs is None or cls(self.fr.figs[rs][2]) in "LR":
                return self.note(tr("st.draw_first"))
            g = self.fr.figs[rs]
            now = time.time()
            self.stroke = dict(pts=[(float(g[0]), float(g[1]))], t0=now, samples=[(0.0, float(g[0]), float(g[1]))], sid=g[2])
            self.drag = dict(kind="stroke")
            return
        if t == "way":
            if sl is not None and self.sel is None:
                return self.select(sl)
            if self.sel is None:
                return self.note(tr("st.way_first"))
            sid = self.fr.figs[self.ref_slot()][2]
            x, y = self.ptr_pos(e.x, e.y, sid)
            xl, xh = xlim(sid)
            x = max(float(xl), min(float(xh), x))
            y = max(0.0, min(float(MAX_Y), y))
            self.way.append((x, y))
            self.draw_overlay()
            return
        kk = self.path_hit(e.x, e.y, 5.0)
        if kk is not None and kk != self.idx and sl not in self.multi and not ctrl:
            return self.start_rope(kk, e)
        if sl is not None:
            if ctrl:
                if sl in self.multi:
                    self.remove_from_group(sl)
                else:
                    self.select(sl, add=True)
                return
            cyc = (cands, self.sel == sl and len(self.multi) <= 1 and len(cands) > 1)
            if sl not in self.multi:
                self.select(sl)
            self.drag = dict(kind="fig", sl=sl, x0=e.x, y0=e.y, done=(0, 0), snapped=False, cyc=cyc)
            return
        k = self.path_hit(e.x, e.y)
        if k is not None:
            return self.start_rope(k, e)

        if self.near_window_edge(px, py):
            self.drag = dict(kind="win", x0=e.x, y0=e.y, a=tuple(self.fr.scroll), snapped=False, moved=False, live=False, pos=None)
        else:
            self.drag = dict(kind="band", x0=e.x, y0=e.y, x1=e.x, y1=e.y, ctrl=ctrl, moved=False)


    def on_motion(self, e):
        d = self.drag
        if not d:
            return
        z = self.sc()
        k = d["kind"]
        if k == "stroke":
            sid = self.stroke["sid"]
            x, y = self.ptr_pos(e.x, e.y, sid)
            xl, xh = xlim(sid)
            x = max(float(xl), min(float(xh), x))
            y = max(0.0, min(float(MAX_Y), y))
            t = time.time() - self.stroke["t0"]
            if e.state & 1:
                self.stroke["pts"] = [self.stroke["pts"][0], (x, y)]
                self.stroke["samples"] = [self.stroke["samples"][0], (t, x, y)]
            else:
                lx, ly = self.stroke["pts"][-1]
                if math.hypot(x - lx, y - ly) >= 1.0:
                    self.stroke["pts"].append((x, y))
                    self.stroke["samples"].append((t, x, y))
            self.draw_overlay()
            return
        if k == "rope":
            return self.move_rope(e)
        if k == "band":
            d["x1"], d["y1"] = e.x, e.y
            d["moved"] = abs(e.x - d["x0"]) > 3 or abs(e.y - d["y0"]) > 3
            self.draw_overlay()
            return
        dxp, dyp = round((e.x - d["x0"]) / z), round((e.y - d["y0"]) / z)
        if k == "fig":
            dx, dy = dxp - d["done"][0], dyp - d["done"][1]
            if not (dx or dy):
                return
            if not d["snapped"]:
                self.snap()
                d["snapped"] = True
            self.move_fig(d["sl"], dx, dy)
            d["done"] = (dxp, dyp)
            self._drag_note(d["sl"])
        else:  
            if self.playing and not d["live"]:
                d.update(live=True, x0=e.x, y0=e.y, a=tuple(self.fr.scroll))
                return
            if not (dxp or dyp):
                return
            if not d["snapped"]:
                self.snap()
                d["snapped"] = True
            d["moved"] = True
            self.cam_release()
            nx = max(0, min(SCROLL_MAX_X, d["a"][0] + dxp))
            ny = max(0, min(SCROLL_MAX_Y, d["a"][1] + dyp))
            d["pos"] = (nx, ny)
            for i in self.frames_in_scope():
                self.scene.frames[i].scroll = [nx, ny]
                self.scene.frames[i].dirty = True
            if self.playing:
                now = time.monotonic()
                if now - self._t_pan < 0.03:
                    return
                self._t_pan = now
        self.refresh(light=True)
        if k == "fig":
            self._drag_note(d["sl"])


    def _drag_note(self, sl):
        x, y, sid = self.fr.figs[sl]
        self.note(tr("st.drag", x=x, y=y, cx=x + sprite_w(sid) // 2, sid=sid, f=self.idx + 1, n=len(self.scene.frames)))


    def on_release(self, e):
        d, self.drag = self.drag, None
        if not d:
            return
        k = d["kind"]
        if k == "stroke":
            return self.finish_stroke()
        if k == "rope":
            return self.end_rope(d)
        if k == "band":
            if d["moved"]:
                z = self.sc()
                x0, x1 = sorted((d["x0"], d["x1"]))
                y0, y1 = sorted((d["y0"], d["y1"]))
                hit = set()
                for i, g in enumerate(self.fr.figs):
                    if cls(g[2]) in "LR":
                        continue
                    gx, gy, gw = self.cx(g[0]), self.cy(g[1] + Y_OFFSET), sprite_w(g[2]) * z
                    if gx + gw >= x0 and gx <= x1 and gy + CELL_H * z >= y0 and gy <= y1:
                        hit.add(i)
                if d["ctrl"]:
                    hit |= self.multi
                self.multi = hit
                self.sel = self.pick_leader(hit) if hit else None
                self.refresh()
            else:
                self.select(None)
            return
        if k == "fig" and d["snapped"]:
            self.cam_refollow()
        if k == "fig" and not d["snapped"] and len(self.multi) > 1 and d["sl"] in self.multi and d["sl"] != self.sel:
            self.sel = d["sl"]
            self.note(tr("st.leader", name=self.names().get(d["sl"], tr("name.sprite"))))
        if k == "fig" and not d["snapped"] and d.get("cyc") and d["cyc"][1] and len(self.multi) <= 1:
            cands = d["cyc"][0]
            if d["sl"] in cands:
                nxt = cands[(cands.index(d["sl"]) + 1) % len(cands)]
                self.select(nxt)
                return self.note(tr("st.overlap", name=self.names().get(nxt, tr("name.sprite")), i=cands.index(nxt) + 1, n=len(cands)))
        if k == "win" and not d["moved"] and self.tool.get() == "select":
            self.select(None)
            return
        self.refresh()


    def remove_from_group(self, sl):
        if sl in self.multi:
            self.multi.remove(sl)
            if sl == self.sel:
                if self.multi:
                    self.sel = self.pick_leader(self.multi)
                else:
                    self.sel = None
            elif not self.multi:
                self.sel = None
            self.refresh()


    def on_right(self, e):
        self.canvas.focus_set()
        px, py = int(math.floor(self.fx(e.x))), int(math.floor(self.fy(e.y)))
        if self.tool.get() == "way" and self.way:
            return self.finish_way()
        cands = self.hit_all(px, py)
        sl = self.pick_cand(cands)
        k = self.path_hit(e.x, e.y) if sl is None else None
        m = tk.Menu(self, tearoff=0)
        if sl is not None:
            if sl not in self.multi:
                self.select(sl)
            sid = self.fr.figs[sl][2]
            nm = self.names().get(sl, tr("name.sprite"))
            m.add_command(label="-- %s --" % nm, state="disabled")
            if len(cands) > 1:
                sm = tk.Menu(m, tearoff=0)
                allnames = self.names()
                for s2 in cands:
                    sm.add_command(label=tr("cx.sprite_item", name=allnames.get(s2, tr("name.sprite")), sid=self.fr.figs[s2][2]), command=lambda s2=s2: self.select(s2))
                m.add_cascade(label=tr("cx.select_under", n=len(cands)), menu=sm)
            if len(self.multi) > 1 and sl in self.multi:
                if sl != self.sel:
                    m.add_command(label=tr("cx.leader"), command=lambda s=sl: self.set_leader(s))
                m.add_command(label=tr("cx.remove"), command=lambda s=sl: self.remove_from_group(s))
            if team_of(sid) in ("R", "B"):
                m.add_cascade(label=tr("s.action"), menu=self._action_menu(m))
            if loco_cycle(sid, "E"):
                m.add_cascade(label=tr("cx.run"), menu=self._run_menu(m))
            m.add_command(label=tr("s.mirrorpose"), command=self.mirror_sel)
            m.add_command(label=tr("s.lock"), command=self.clear_anim)
            m.add_separator()
            m.add_command(label=tr("cx.auto"), command=self.auto_here)
            m.add_command(label=tr("cx.smooth_here"), command=self.smooth_path)
            m.add_command(label=tr("cx.even_here"), command=self.even_speed)
            m.add_command(label=tr("p.freeze"), command=self.freeze_here)
            if cls(sid) in "SB":
                m.add_command(label=tr("cx.cam_ball"), command=self.auto_camera)
            else:
                m.add_command(label=tr("cx.cam_sprite"), command=self.auto_camera)
            m.add_separator()
            m.add_command(label=tr("cx.tip"), state="disabled")
        elif k is not None:
            m.add_command(label=tr("cx.pt_title", n=k + 1), state="disabled")
            m.add_command(label=tr("cx.goto", n=k + 1), command=lambda: self.goto(k))
            m.add_command(label=tr("p.smooth"), command=self.smooth_path)
            m.add_command(label=tr("p.even"), command=self.even_speed)
            m.add_command(label=tr("cx.straighten", n=k + 1), command=lambda: self.tween_to(k))
        elif self.sel is not None and cls(self.fr.figs[self.sel][2]) not in "LR":
            sid = self.fr.figs[self.sel][2]
            tx, ty = self.ptr_pos(e.x, e.y, sid)
            tx, ty = max(xlim(sid)[0], min(xlim(sid)[1], round(tx))), max(0, min(MAX_Y, round(ty)))
            nm = self.names().get(self.sel, tr("name.sprite"))
            m.add_command(label=tr("cx.path_to", name=nm), command=lambda: self.make_path(self.sel, tx, ty))
            m.add_command(label=tr("cx.path_n"), command=lambda: self.path_n(tx, ty))
            m.add_command(label=tr("cx.path_arrive"), command=lambda: self.path_to_frame(tx, ty))
            m.add_separator()
            m.add_command(label=tr("cx.move_here"), command=lambda: self.teleport(tx, ty))
            m.add_separator()
            m.add_command(label=tr("cx.draw"), command=lambda: (self.tool.set("draw"), self.set_tool()))
            m.add_command(label=tr("cx.way"), command=lambda: (self.tool.set("way"), self.set_tool()))
        else:
            m.add_command(label=tr("cx.select_first"), state="disabled")
        m.tk_popup(e.x_root, e.y_root)


    def ensure_frames(self, total):
        if total > MAX_FRAMES:
            return False
        while len(self.scene.frames) < total:
            nf = copy.deepcopy(self.scene.frames[-1])
            nf.dirty = True
            self.scene.frames.append(nf)
        return True

    def teleport(self, tx, ty):
        sl = self.ref_slot()
        g = self.fr.figs[sl]
        self.snap()
        self.move_fig(sl, tx - g[0], ty - g[1])
        self.cam_refollow()
        self.refresh()

    def path_n(self, tx, ty):
        n = simpledialog.askinteger(tr("path.title"), tr("path.n_prompt"), minvalue=1, maxvalue=MAX_FRAMES, parent=self.top)
        if n:
            self.make_path(self.sel, tx, ty, n)

    def path_to_frame(self, tx, ty):
        e = simpledialog.askinteger(tr("path.title"), tr("path.arrive_prompt", n=self.idx + 1), minvalue=self.idx + 2, maxvalue=MAX_FRAMES, parent=self.top)
        if e:
            self.make_path(self.sel, tx, ty, e - 1 - self.idx)

    def make_path(self, sl, tx, ty, n=None):
        if cls(self.fr.figs[sl][2]) in "LR":
            return
        g = self.fr.figs[self.ref_slot(sl)]
        self.bake_path([(g[0], g[1]), (tx, ty)], n=n)


    def need_sel(self):
        if self.sel is None or cls(self.fr.figs[self.sel][2]) in "LR":
            messagebox.showinfo(tr("mb.sprite"), tr("sel.first"))
            return False
        return True

    def program_anim(self):
        if not self.need_sel():
            return
        s = simpledialog.askstring(tr("pose.seq_title"), tr("pose.seq_prompt"), parent=self.top)
        try:
            seq = [int(v) for v in (s or "").replace(";", ",").split(",") if v.strip()]
        except ValueError:
            return messagebox.showerror(tr("mb.error"), tr("mb.invalid"))
        if seq:
            self.snap()
            for sl in self.targets():
                cur = self.fr.figs[sl][2]
                sq = [q if sl == self.sel else self.conv_pose(q, cur) for q in seq]
                if None in sq:
                    continue
                for n, i in enumerate(range(self.idx, len(self.scene.frames))):
                    self.scene.frames[i].figs[sl][2] = max(0, min(145, sq[n % len(sq)]))
                    self.scene.frames[i].touch()
            self.refresh()

    def clear_anim(self):
        if not self.need_sel():
            return
        self.snap()
        for sl in self.targets():
            pid = self.fr.figs[sl][2]
            for f in self.scene.frames[self.idx:]:
                f.figs[sl][2] = pid
                f.touch()
        self.refresh()

    def tween(self):
        if not self.need_sel():
            return
        end = simpledialog.askinteger(tr("tween.title"), tr("tween.prompt", n=len(self.scene.frames)), minvalue=1, maxvalue=len(self.scene.frames), parent=self.top)
        if end:
            self.tween_to(end - 1)


    def tween_scroll(self):
        end = simpledialog.askinteger(tr("tween.scroll_title"), tr("tween.prompt", n=len(self.scene.frames)), minvalue=1, maxvalue=len(self.scene.frames), parent=self.top)
        if not end or end - 1 <= self.idx:
            return
        self.snap()
        fs, n = self.scene.frames, end - 1 - self.idx
        a, b = fs[self.idx].scroll, fs[end - 1].scroll
        for k in range(1, n):
            fs[self.idx + k].scroll = [round(a[0] + (b[0] - a[0]) * k / n), round(a[1] + (b[1] - a[1]) * k / n)]
            fs[self.idx + k].dirty = True
        self.refresh()

    def set_scroll(self):
        try:
            sx, sy = int(self.sx.get()), int(self.sy.get())
        except (tk.TclError, ValueError):
            return
        self.snap()
        self.cam_release()
        for i in self.frames_in_scope():
            self.scene.frames[i].scroll = [max(0, min(SCROLL_MAX_X, sx)), max(0, min(SCROLL_MAX_Y, sy))]
            self.scene.frames[i].dirty = True
        self.refresh()

    def scroll_to_end(self):
        self.snap()
        for f in self.scene.frames[self.idx:]:
            f.scroll = list(self.fr.scroll)
            f.dirty = True
        self.refresh()

    def mirror(self, flip, swap):
        self.snap()
        for f in self.scene.frames:
            transform_frame(f, flip, swap)
        self.refresh()
        self.note(tr("st.mirrored") if flip else tr("st.swapped"))

    def set_sound(self):
        v = self.snd_var.get()
        self.snap()
        ev = self.scene.events
        for k in range(4):
            if ev[k] == self.idx:
                ev[k] = None
        if v >= 0:
            ev[v] = self.idx
        self.refresh(light=True)

    def apply_live_pan(self):
        d = self.drag
        if not d or d.get("kind") != "win" or not d.get("live") or d.get("pos") is None:
            return
        nx, ny = d["pos"]
        for i in self.frames_in_scope():
            f = self.scene.frames[i]
            if f.scroll != [nx, ny]:
                f.scroll = [nx, ny]
                f.dirty = True

    def goto(self, i):
        self.idx = max(0, min(len(self.scene.frames) - 1, i))
        self.apply_live_pan()
        self.refresh_step()

    def step(self, d):
        self.goto((self.idx + d) % len(self.scene.frames))

    def _tl_cw(self):
        return max(4.0, (max(self.tl.winfo_width(), 300) - 8) / len(self.scene.frames))

    def on_tl_press(self, e):
        self._tl_drag = None
        if e.y >= 64:
            a, b = self.loop_range()
            cw = self._tl_cw()
            xa, xb = 4 + a * cw, 4 + (b + 1) * cw
            self._tl_drag = "a" if abs(e.x - xa) <= abs(e.x - xb) else "b"
        self.on_tl_drag(e)

    def on_tl_drag(self, e):
        n = len(self.scene.frames)
        cw = self._tl_cw()
        if self._tl_drag:
            pos = int(round((e.x - 4) / cw))
            a, b = self.loop_range()
            if self._tl_drag == "a":
                self.loop_a = max(0, min(pos, b))
            else:
                j = max(a, min(n - 1, pos - 1))
                self.loop_b = None if j >= n - 1 else j
            self.draw_timeline()
            return
        self.goto(int((e.x - 4) / cw))

    def on_tl_release(self, e):
        self._tl_drag = None

    def loop_range(self):
        n = len(self.scene.frames)
        b = n - 1 if self.loop_b is None else max(0, min(self.loop_b, n - 1))
        a = max(0, min(self.loop_a, b))
        return a, b

    def _play_buttons(self):
        self.btn.config(text=tr("play.stop") if self.playing and self._play_mode == "all" else tr("play.all"))
        self.btn2.config(text=tr("play.stop") if self.playing and self._play_mode == "here" else tr("play.here"))

    def toggle(self, mode="here"):
        self.playing = not self.playing
        if self.playing:
            self._play_mode = mode
        self._play_buttons()
        if self.playing:
            a, b = self.loop_range()
            self.goto(a if (mode == "all" or self.idx > b) else self.idx)
            self.after(10, self.tick)

    def tick(self):
        if not self.playing:
            return
        a, b = self.loop_range()
        if self.idx >= b:
            if not self.loop.get():
                self.playing = False
                self._play_buttons()
                return
            self.idx = a
        else:
            self.idx += 1
        self.refresh_play()
        try:
            fps = max(1, int(self.fps.get()))
        except (tk.TclError, ValueError):
            fps = 12
        self.after(int(1000 / fps), self.tick)

    def ins_frame(self):
        if len(self.scene.frames) >= MAX_FRAMES:
            return messagebox.showwarning(tr("mb.limit"), tr("mb.max_frames", n=MAX_FRAMES))
        self.snap()
        nf = copy.deepcopy(self.fr)
        nf.dirty = True
        self.scene.frames.insert(self.idx + 1, nf)
        ev = self.scene.events
        self.scene.events = [e + 1 if (e is not None and e >= self.idx + 1) else e for e in ev]
        self.idx += 1
        self.refresh()

    def del_frame(self):
        if len(self.scene.frames) <= 1:
            return messagebox.showinfo(tr("mb.delete"), tr("mb.min_frame"))
        self.snap()
        del self.scene.frames[self.idx]
        self.scene.events = [None if e == self.idx else (e - 1 if (e is not None and e > self.idx) else e) for e in self.scene.events]
        self.idx = min(self.idx, len(self.scene.frames) - 1)
        self.refresh()


    def clear_film(self):
        if not messagebox.askyesno(tr("mb.delete_film"), tr("mb.delete_all")):
            return
        self.snap()
        self.scene.frames = [self.fr]
        self.scene.events = [0 if e is not None else None for e in self.scene.events]
        self.idx = 0
        self.refresh()

    def props(self):
        w = tk.Toplevel(self.top)
        w.title(tr("pr.title"))
        self._i18n_titles.append((w, "pr.title"))
        w.transient(self.top)
        ver = tk.StringVar(value=self.scene.sig[:11].decode())
        au = tk.StringVar(value=self.scene.author)
        self._reg(ttk.Label(w), "pr.author").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Entry(w, textvariable=au, width=24).grid(row=0, column=1, padx=8)
        self._reg(ttk.Label(w), "pr.version").grid(row=1, column=0, sticky="w", padx=8)
        ttk.Combobox(w, textvariable=ver, values=["BM-Ed1.3-WK", "BM-Ed1.0-WK"], state="readonly", width=14).grid(row=1, column=1, sticky="w", padx=8)
        kv, vv = tk.StringVar(value=self.scene.kind), tk.StringVar(value=self.scene.variant)
        ex = tk.StringVar()
        fk = self._reg(ttk.LabelFrame(w), "pr.result")
        fk.grid(row=2, column=0, columnspan=2, sticky="we", padx=8, pady=4)
        self._reg(ttk.Radiobutton(fk, value="T", variable=kv), "pr.scored").pack(side="left", padx=8, pady=2)
        self._reg(ttk.Radiobutton(fk, value="V", variable=kv), "pr.failure").pack(side="left", padx=8)
        fv = self._reg(ttk.LabelFrame(w), "pr.type")
        fv.grid(row=3, column=0, columnspan=2, sticky="we", padx=8, pady=4)
        self._reg(ttk.Radiobutton(fv, value="E", variable=vv), "pr.penalty").pack(side="left", padx=8, pady=2)
        self._reg(ttk.Radiobutton(fv, value="J", variable=vv), "pr.joke").pack(side="left", padx=8)
        self._reg(ttk.Radiobutton(fv, value="", variable=vv), "pr.none").pack(side="left", padx=8)
        ttk.Label(w, textvariable=ex, foreground="#555").grid(row=4, column=0, columnspan=2, sticky="w", padx=8)

        def upd(*_):
            ex.set(tr("pr.ext", ext=kv.get() + vv.get()))
        kv.trace_add("write", upd)
        vv.trace_add("write", upd)
        upd()

        def ok():
            self.snap()
            self.scene.kind, self.scene.variant = kv.get(), vv.get()
            self.scene.author = au.get()
            self.scene.sig = (ver.get() + "\0").encode()
            w.destroy()
        self._reg(ttk.Button(w, command=ok), "ok").grid(row=5, column=1, pady=8, sticky="e", padx=8)

    def help(self):
        messagebox.showinfo(tr("h.quick"), tr("help.text"))

    def sel_sid(self):
        return None if self.sel is None else self.fr.figs[self.sel][2]

    def draw_poses(self):
        cv = self.pose_cv
        sid = self.sel_sid()
        cats = cats_for(sid) if sid is not None else []
        self.cat_cb.config(values=[n for n, _ in cats])
        if self._thumb_gfx is not self.gfx:
            self._thumb_cache, self._thumb_gfx, self._poses_key = {}, self.gfx, None
        if not cats:
            cv.delete("all")
            self._thumbs = []
            self._poses_key = None
            self.cat_var.set("")
            self.pose_info.config(text=tr("pose.select"))
            return
        names = [n for n, _ in cats]
        if self.cat_var.get() not in names or sid != getattr(self, "_cat_sid", None):
            self.cat_var.set(next((n for n, ids in cats if sid in ids), self.cat_var.get() if self.cat_var.get() in names else names[0]))
        self._cat_sid = sid
        ids = dict(cats)[self.cat_var.get()]
        curcat = next((n for n, i in cats if sid in i), "-")
        self.pose_info.config(text=tr("pose.current", sid=sid, cat=curcat))
        key = (sid, self.cat_var.get(), tuple(ids))
        if key == self._poses_key:
            return
        self._poses_key = key
        cv.delete("all")
        self._thumbs = []
        cw, ch = 44, 50
        rows = (len(ids) + 4) // 5
        cv.config(height=max(60, rows * ch))
        for n, pid in enumerate(ids):
            x, y = (n % 5) * cw, (n // 5) * ch
            spr = sprite_of(self.gfx, pid)
            cv.create_rectangle(x + 2, y + 2, x + cw - 2, y + ch - 2, outline="#ffb000" if pid == sid else "#ccc",width=3 if pid == sid else 1, fill="#303030")
            if spr is not None:
                ph = self._thumb_cache.get(pid)
                if ph is None:
                    im = spr.resize((spr.width * 3, spr.height * 3), Image.NEAREST)
                    ph = self._thumb_cache[pid] = ImageTk.PhotoImage(im)
                self._thumbs.append(ph)
                cv.create_image(x + cw // 2, y + 18 + 2, image=ph)
            cv.create_text(x + cw // 2, y + ch - 8, text=str(pid), fill="#ddd")

    def on_pose_click(self, e):
        sid = self.sel_sid()
        if sid is None:
            return
        cats = dict(cats_for(sid))
        ids = cats.get(self.cat_var.get(), [])
        n = (e.y // 50) * 5 + e.x // 44
        if 0 <= n < len(ids):
            self.snap()
            self.set_pose_all(ids[n])
            self.refresh()

    def open_palette(self):
        if self.pal and self.pal.winfo_exists():
            return self.pal.lift()

        self.pal = w = tk.Toplevel(self.top)
        w.title(tr("pal.title"))
        self._i18n_titles.append((w, "pal.title"))
        w.transient(self.top)
        w.protocol("WM_DELETE_WINDOW", lambda: self._close_palette())

        cols, rows = SHEET_COLS, 7
        sheet = self.gfx.sheet
        im = Image.new("RGBA", (cols * CELL_W, rows * CELL_H), (60, 60, 60, 255))
        if sheet:
            crop = sheet.crop((0, 0, min(sheet.width, im.width), min(sheet.height, im.height)))
            im.paste(crop, (0, 0), crop)
        w._im = im
        z0 = max(1, min(6, (self.winfo_screenwidth() - 120) // im.width))
        self._pal_zx = self._pal_zy = float(z0)
        self._pal_job = None
        w.geometry("%dx%d" % (im.width * z0, im.height * z0))
        w.minsize(im.width, im.height)
        w.resizable(True, True)

        cv = tk.Canvas(w, highlightthickness=0, bg="#3c3c3c")
        cv.pack(fill="both", expand=True)
        cv.bind("<Configure>", lambda e: self._pal_schedule())
        cv.bind("<Button-1>", self.on_palette_click)
        cv.bind("<Motion>", self.on_palette_hover)
        self._palette_canvas = cv

    def _pal_schedule(self):
        if self._pal_job:
            self.after_cancel(self._pal_job)
        self._pal_job = self.after(40, self._pal_draw)

    def _pal_draw(self):
        self._pal_job = None
        w, cv = self.pal, self._palette_canvas
        if not (w and cv and w.winfo_exists()):
            return
        im = w._im
        cw, ch = max(1, cv.winfo_width()), max(1, cv.winfo_height())
        sc = max(1.0, min(cw / im.width, ch / im.height))
        bw, bh = max(1, int(im.width * sc)), max(1, int(im.height * sc))
        w._ph = ImageTk.PhotoImage(im.resize((bw, bh), Image.NEAREST))
        self._pal_zx, self._pal_zy = bw / im.width, bh / im.height
        zx, zy = self._pal_zx, self._pal_zy
        cv.delete("all")
        cv.create_image(0, 0, anchor="nw", image=w._ph)
        fs = max(6, int(min(zx, zy) * 1.2))
        for sid in range(SHEET_COLS * 7):
            x0, y0 = (sid % SHEET_COLS) * CELL_W * zx, (sid // SHEET_COLS) * CELL_H * zy
            cv.create_rectangle(x0, y0, x0 + CELL_W * zx, y0 + CELL_H * zy, outline="#ff00ff")
            cv.create_text(x0 + zx, y0 + zy, anchor="nw", text=str(sid), fill="white", font=("TkDefaultFont", fs, "bold"))

    def _pal_cell(self, e):
        col, row = int(e.x // (CELL_W * self._pal_zx)), int(e.y // (CELL_H * self._pal_zy))
        if 0 <= col < SHEET_COLS and 0 <= row < 7:
            return row * SHEET_COLS + col, col, row
        return None

    def _close_palette(self):
        if self._pal_job:
            self.after_cancel(self._pal_job)
            self._pal_job = None
        if self.pal and self.pal.winfo_exists():
            self.pal.destroy()
        self.pal = None
        self._palette_canvas = None

    def on_palette_hover(self, e):
        c = self._pal_cell(e)
        if c:
            self.note(tr("pal.hover", sid=c[0], x=c[1], y=c[2]))

    def on_palette_click(self, e):
        c = self._pal_cell(e)
        if not c:
            return
        if self.sel is not None:
            self.snap()
            self.set_pose_all(c[0])
            self.refresh()
            return
        return self.note(tr("st.assign_first"))

    def load_gfx(self, p=None):
        pic = locate_pic(p)
        self.pic_dir = pic
        self.gfx = Graphics(pic)
        if pic is None:
            self.note(tr("st.no_gfx"))
        elif self.gfx.missing:
            self.note(tr("st.pic_missing", files=", ".join(self.gfx.missing)))

    def choose_pic(self):
        d = filedialog.askdirectory(parent=self.top, title=tr("pic.select"), initialdir=self.pic_dir or APP_DIR)
        if d:
            self.set_pic_dir(d)

    def confirm_discard(self):
        return not self.modified or messagebox.askyesno(tr("mb.unsaved"), tr("mb.discard"))

    def _reset_session(self):
        self.cam_release()
        self.idx, self.sel, self.modified = 0, None, False
        self.multi = set()
        self.undo_s.clear()
        self.redo_s.clear()
        self._act_backup.clear()

    def new_scene(self):
        try:
            load_kickoff()
        except DataError as ex:
            return messagebox.showwarning(tr("mb.kickoff"), tr("mb.new_fail", err=ex), parent=self.top)
        if self.confirm_discard():
            self.scene = Scene.new()
            self._reset_session()
            self.cam_default()
            self.refresh()

    def open_dialog(self):
        if not self.confirm_discard():
            return
        p = filedialog.askopenfilename(title=tr("open.title"), filetypes=[(tr("ft.scene"), self.SCENE_PATTERNS), (tr("ft.all"), "*.*")])
        if p:
            self.open_path(p)

    def open_path(self, p):
        try:
            self.scene = Scene.load(p)
        except Exception as ex:
            return messagebox.showerror(tr("mb.error"), str(ex))
        if not self.pic_dir or find_pic_dir(p):
            self.load_gfx(p)
        self._reset_session()
        self.refresh()

    def _write(self, p):
        try:
            self.scene.save(p)
            self.modified = False
            self.refresh()
            return True
        except OSError as ex:
            messagebox.showerror(tr("mb.error"), tr("mb.save_fail", err=ex))
            return False

    SCENE_PATTERNS = "*.t *.T *.v *.V *.te *.TE *.tj *.TJ *.ve *.VE *.vj *.VJ"

    def _with_ext(self, p):
        return os.path.splitext(p)[0] + "." + self.scene.ext()

    def save(self):
        if not self.scene.path:
            return self.save_as()
        p = self._with_ext(self.scene.path)
        if p != self.scene.path and os.path.exists(p) and not messagebox.askyesno(
                tr("mb.existing"), tr("mb.overwrite", name=os.path.basename(p)), parent=self.top):
            return
        self._write(p)

    def save_as(self):
        base = os.path.splitext(os.path.basename(self.scene.path or "1"))[0]
        p = filedialog.asksaveasfilename(title=tr("save.title"), defaultextension="." + self.scene.ext(), initialfile=base + "." + self.scene.ext(), filetypes=[(tr("ft.scene"), self.SCENE_PATTERNS), (tr("ft.all"), "*.*")])
        if p:
            self._write(self._with_ext(p))

    def _gif_indices(self, s):
        n = len(self.scene.frames)
        if s["range"] == "loop":
            a, b = self.loop_range()
        elif s["range"] == "here":
            a, b = self.idx, n - 1
        else:
            a, b = 0, n - 1
        return a, b, list(range(a, b + 1, max(1, s["step"])))

    def _gif_render(self, s, idx, progress):
        out = []
        for k, i in enumerate(idx):
            if progress and progress(k, len(idx)) is False:
                raise GifCancelled()
            fr = self.scene.frames[i]
            im = compose(self.gfx, fr).convert("RGB")
            if s["area"] == "cam":
                sx = max(0, min(SCROLL_MAX_X, fr.scroll[0]))
                sy = max(0, min(SCROLL_MAX_Y, fr.scroll[1]))
                im = im.crop((sx, sy, sx + WIN_W, sy + WIN_H))
            out.append(im)
        return out

    def _gif_encode(self, s, progress):
        a, b, idx = self._gif_indices(s)
        frames = self._gif_render(s, idx, lambda i, n: progress(0.25 * i / n, tr("gif.rendering", i=i + 1, n=n)))
        durs = gif_durations(idx, b, s["fps"], s["hold"])
        data = build_gif(frames, durs, colors=s["colors"], dither=s["dither"], shared=s["shared"], optimize=s["optimize"], loop=s["loop"], scale=s["scale"], smooth=s["smooth"], progress=lambda i, n: progress(0.25 + 0.75 * i / n, tr("gif.encoding", i=min(i + 1, n), n=n)))
        return data, len(frames), (frames[0].width * s["scale"], frames[0].height * s["scale"])

    def export_gif(self):
        dflt = dict(range="all", area="cam", scale=2, smooth=False, fps=self._fps(), step=1, hold=500, loop=True, preset="High quality", colors=256, shared=True, dither=False, optimize=True)
        cfg = dict(dflt, **(getattr(self, "_gif_cfg", None) or {}))
        w = tk.Toplevel(self.top)
        w.title(tr("gif.title"))
        w.transient(self.top)
        w.resizable(False, False)
        w.grab_set()
        V = {k: (tk.BooleanVar if isinstance(v, bool) else tk.IntVar if isinstance(v, int) else tk.StringVar)(value=v)
             for k, v in cfg.items()}
        busy, running, cancel, closing = [False], [False], [False], [False]
        info, status = tk.StringVar(), tk.StringVar()

        def num(k, lo, hi):
            try:
                return max(lo, min(hi, int(V[k].get())))
            except (tk.TclError, ValueError):
                return dflt[k] if lo <= dflt[k] <= hi else lo

        def settings():
            return dict(range=V["range"].get(), area=V["area"].get(), scale=num("scale", 1, 8),
                        smooth=bool(V["smooth"].get()), fps=num("fps", 1, 50), step=num("step", 1, 8),
                        hold=num("hold", 0, 10000), loop=bool(V["loop"].get()), preset=V["preset"].get(),
                        colors=num("colors", 2, 256), shared=bool(V["shared"].get()),
                        dither=bool(V["dither"].get()), optimize=bool(V["optimize"].get()))

        def update_info(*_):
            try:
                s = settings()
                a, b, idx = self._gif_indices(s)
                ww, hh = (WIN_W, WIN_H) if s["area"] == "cam" else (FW, FH)
                secs = (b - a + 1) / s["fps"] + s["hold"] / 1000.0
                info.set(tr("gif.info", n=len(idx), total=b - a + 1, w=ww * s["scale"], h=hh * s["scale"], s="%.1f" % secs))
            except Exception:
                info.set("")

        def custom(*_):
            if not busy[0] and V["preset"].get() != "Custom":
                V["preset"].set("Custom")
            update_info()

        def apply_preset(_e=None):
            if 0 <= cb_.current() < len(pnames):
                V["preset"].set(pnames[cb_.current()])
            p = GIF_PRESETS.get(V["preset"].get())
            if p:
                busy[0] = True
                for k, v in p.items():
                    V[k].set(v)
                busy[0] = False
            update_info()

        for k in ("range", "area", "scale", "fps", "step", "hold"):
            V[k].trace_add("write", update_info)
        for k in ("colors", "shared", "dither", "optimize", "step"):
            V[k].trace_add("write", custom)

        P = dict(padx=8, pady=3)
        g1 = self._reg(ttk.LabelFrame(w), "gif.content")
        g1.grid(row=0, column=0, sticky="nsew", padx=8, pady=(8, 4))
        self._reg(ttk.Label(g1), "gif.frames").grid(row=0, column=0, sticky="w", **P)
        for i, (val, txt) in enumerate((("all", "gif.all"), ("loop", "gif.loop"), ("here", "gif.here"))):
            self._reg(ttk.Radiobutton(g1, value=val, variable=V["range"]), txt).grid(row=0, column=1 + i, sticky="w", padx=4)
        self._reg(ttk.Label(g1), "gif.area").grid(row=1, column=0, sticky="w", **P)
        self._reg(ttk.Radiobutton(g1, value="cam", variable=V["area"]), "gif.cam").grid(row=1, column=1, columnspan=2, sticky="w", padx=4)
        self._reg(ttk.Radiobutton(g1, value="full", variable=V["area"]), "gif.full").grid(row=1, column=3, sticky="w", padx=4)

        g2 = self._reg(ttk.LabelFrame(w), "gif.size")
        g2.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        self._reg(ttk.Label(g2), "gif.scale").grid(row=0, column=0, sticky="w", **P)
        ttk.Spinbox(g2, from_=1, to=8, width=4, textvariable=V["scale"]).grid(row=0, column=1, sticky="w")
        self._reg(ttk.Checkbutton(g2, variable=V["smooth"]), "gif.smooth").grid(row=0, column=2, columnspan=2, sticky="w", padx=8)
        self._reg(ttk.Label(g2), "gif.fps").grid(row=1, column=0, sticky="w", **P)
        ttk.Spinbox(g2, from_=1, to=50, width=4, textvariable=V["fps"]).grid(row=1, column=1, sticky="w")
        self._reg(ttk.Label(g2), "gif.hold").grid(row=1, column=2, sticky="e", padx=(8, 2))
        ttk.Spinbox(g2, from_=0, to=10000, increment=100, width=6, textvariable=V["hold"]).grid(row=1, column=3, sticky="w")
        self._reg(ttk.Checkbutton(g2, variable=V["loop"]), "gif.loopforever").grid(row=2, column=0, columnspan=4, sticky="w", **P)

        g3 = self._reg(ttk.LabelFrame(w), "gif.quality")
        g3.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self._reg(ttk.Label(g3), "gif.preset").grid(row=0, column=0, sticky="w", **P)
        pnames = list(GIF_PRESETS) + ["Custom"]
        pdisp = tk.StringVar(value=tr(GIF_PRESET_KEYS[V["preset"].get()]))
        V["preset"].trace_add("write", lambda *_: pdisp.set(tr(GIF_PRESET_KEYS.get(V["preset"].get(), "gif.p.custom"))))
        cb_ = ttk.Combobox(g3, textvariable=pdisp, values=[tr(GIF_PRESET_KEYS[k]) for k in pnames], state="readonly", width=18)
        cb_.grid(row=0, column=1, columnspan=2, sticky="w")
        cb_.bind("<<ComboboxSelected>>", apply_preset)
        self._reg(ttk.Label(g3), "gif.colors").grid(row=1, column=0, sticky="w", **P)
        ttk.Spinbox(g3, from_=2, to=256, width=5, textvariable=V["colors"]).grid(row=1, column=1, sticky="w")
        self._reg(ttk.Label(g3), "gif.step").grid(row=1, column=2, sticky="e", padx=(8, 2))
        ttk.Spinbox(g3, from_=1, to=8, width=4, textvariable=V["step"]).grid(row=1, column=3, sticky="w")
        self._reg(ttk.Checkbutton(g3, variable=V["shared"]), "gif.shared").grid(row=2, column=0, columnspan=4, sticky="w", **P)
        self._reg(ttk.Checkbutton(g3, variable=V["dither"]), "gif.dither").grid(row=3, column=0, columnspan=4, sticky="w", **P)
        self._reg(ttk.Checkbutton(g3, variable=V["optimize"]), "gif.optimize").grid(row=4, column=0, columnspan=4, sticky="w", **P)
        self._reg(ttk.Label(g3, foreground="#555"), "gif.tip").grid(row=5, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 6))

        ttk.Label(w, textvariable=info).grid(row=3, column=0, sticky="w", padx=12, pady=(4, 0))
        pb = ttk.Progressbar(w, maximum=100)
        pb.grid(row=4, column=0, sticky="ew", padx=10, pady=(4, 0))
        ttk.Label(w, textvariable=status, foreground="#1a5e1a").grid(row=5, column=0, sticky="w", padx=12)
        bar = ttk.Frame(w)
        bar.grid(row=6, column=0, sticky="e", padx=8, pady=8)
        b_size = self._reg(ttk.Button(bar), "gif.calc")
        b_exp = self._reg(ttk.Button(bar), "gif.export")
        b_close = self._reg(ttk.Button(bar), "close")
        for b_ in (b_size, b_exp, b_close):
            b_.pack(side="left", padx=3)

        def cbk(frac, text):
            if cancel[0]:
                return False
            pb["value"] = frac * 100
            status.set(text)
            w.update()
            return not cancel[0]

        def busy_ui(on):
            for b_ in (b_size, b_exp):
                b_.config(state="disabled" if on else "normal")
            b_close.config(text=tr("gif.cancel") if on else tr("close"))

        def run(save):
            if running[0]:
                return
            s = settings()
            path = None
            if save:
                base = os.path.splitext(os.path.basename(self.scene.path or "scene"))[0]
                path = filedialog.asksaveasfilename(parent=w, title=tr("gif.title"), defaultextension=".gif", initialfile=base + ".gif", initialdir=os.path.dirname(os.path.abspath(self.scene.path)) if self.scene.path else None, filetypes=[(tr("gif.type"), "*.gif"), (tr("ft.all"), "*.*")])
                if not path:
                    return
            running[0], cancel[0] = True, False
            busy_ui(True)
            try:
                data, nfr, (ww, hh) = self._gif_encode(s, cbk)
                size = "%.1f KB" % (len(data) / 1024.0) if len(data) < 1048576 else "%.2f MB" % (len(data) / 1048576.0)
                if path:
                    with open(path, "wb") as fh:
                        fh.write(data)
                    status.set(tr("gif.saved", name=os.path.basename(path), n=nfr, w=ww, h=hh, size=size))
                else:
                    status.set(tr("gif.estimate", size=size, n=nfr, w=ww, h=hh))
                pb["value"] = 100
            except GifCancelled:
                status.set(tr("gif.cancelled"))
                pb["value"] = 0
            except (OSError, ValueError, MemoryError) as ex:
                status.set("")
                messagebox.showerror(tr("mb.gifexport"), tr("gif.fail", err=ex), parent=w)
            finally:
                running[0] = False
                if closing[0]:
                    w.destroy()
                else:
                    busy_ui(False)

        def close():
            if running[0]:
                cancel[0] = closing[0] = True
                return
            self._gif_cfg = settings()
            w.destroy()

        b_size.config(command=lambda: run(False))
        b_exp.config(command=lambda: run(True))
        b_close.config(command=close)
        w.protocol("WM_DELETE_WINDOW", close)
        w.bind("<Escape>", lambda e: close())
        update_info()

    def save_numbered(self):
        base = os.path.dirname(os.path.abspath(self.scene.path)) if self.scene.path else os.getcwd()
        an = find_anzahl(self.scene.path or os.path.join(base, "x"))
        vals = read_anzahl(an) if an else None
        w = tk.Toplevel(self.top)
        w.title(tr("num.title"))
        w.transient(self.top)
        w.grab_set()
        kind, var_ = tk.StringVar(value=self.scene.kind), tk.StringVar(value=tr(VARIANTS[self.scene.variant]))
        num = tk.IntVar(value=(vals[0] + 1) if vals else 1)
        self._reg(ttk.Label(w), "num.type").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        for i, (k, nm) in enumerate(KINDS.items()):
            self._reg(ttk.Radiobutton(w, value=k, variable=kind), nm).grid(row=0, column=1 + i, padx=4)
        self._reg(ttk.Label(w), "num.variant").grid(row=1, column=0, sticky="w", padx=8)
        vb = ttk.Combobox(w, textvariable=var_, values=[tr(v) for v in VARIANTS.values()], state="readonly", width=18)
        vb.grid(row=1, column=1, columnspan=2, sticky="w", padx=4)
        self._reg(ttk.Label(w), "num.number").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Spinbox(w, from_=1, to=999, width=6, textvariable=num).grid(row=2, column=1, sticky="w", padx=4)
        ttk.Label(w, text=tr("num.anzahl", an=an, vals=vals) if vals else tr("num.anzahl_none"), foreground="#555").grid(row=3, column=0, columnspan=3, padx=8, sticky="w")

        def ok():
            vi = vb.current()
            ext = kind.get() + list(VARIANTS)[vi]
            p = os.path.join(base, "%d.%s" % (num.get(), ext))
            self.scene.kind, self.scene.variant = kind.get(), ext[1:]
            if os.path.exists(p) and not messagebox.askyesno(tr("mb.existing"), tr("mb.overwrite", name=os.path.basename(p)), parent=w):
                return
            if self._write(p) and an and vals and num.get() > vals[vi]:
                vals[vi] = num.get()
                write_anzahl(an, vals)
            w.destroy()
        self._reg(ttk.Button(w, command=ok), "save").grid(row=4, column=2, pady=8, padx=8, sticky="e")

    def delete_file(self):
        p = self.scene.path
        if p and os.path.isfile(p) and messagebox.askyesno(tr("mb.delete_file"), tr("mb.perm_delete", path=p)):
            os.remove(p)
            self.scene.path = None
            self.refresh()

    def quit_app(self):
        if self.confirm_discard():
            if self.standalone:
                job = getattr(self, "_startup_job", None)
                if job:
                    self.after_cancel(job)
                self.top.destroy()

    def rezoom(self):
        z = self.z()
        self.canvas.config(width=FW * z, height=FH * z)
        self.refresh()

    def ghosts(self):
        mode, i, fs = self.cb_ghost.current(), self.idx, self.scene.frames
        out = []
        if mode <= 0 or i == 0:
            return out
        if mode == 1 and self.sel is not None:
            x, y, sid = fs[i - 1].figs[self.sel]
            out.append((x, y, sid, 0.45))
        elif mode == 2 and self.sel is not None:
            for j in range(i):
                x, y, sid = fs[j].figs[self.sel]
                out.append((x, y, sid, 0.15 + 0.3 * (j + 1) / i))
        elif mode == 3:
            for j in range(i):
                a = 0.12 + 0.3 * (j + 1) / i
                for g in fs[j].figs:
                    if cls(g[2]) not in "LR":
                        out.append((g[0], g[1], g[2], a))
        return out

    def names(self):
        cnt, out = {"R": 0, "B": 0, "A": 0}, {}
        for i, g in enumerate(self.fr.figs):
            c = cls(g[2])
            if c in "LRSB":
                out[i] = tr({"S": "name.ball_shadow", "B": "name.ball", "L": "name.goal_l", "R": "name.goal_r"}[c])
            else:
                t = team_of(g[2])
                cnt[t] += 1
                out[i] = tr({"R": "name.red", "B": "name.blue", "A": "name.ref"}[t]) + ("" if t == "A" else " %d" % cnt[t])
        return out

    def select(self, sl, add=False):
        if sl is not None and cls(self.fr.figs[sl][2]) in "LR":
            sl = None
        if add and sl is not None:
            if sl in self.multi and len(self.multi) > 1:
                self.multi.discard(sl)
                self.sel = self.pick_leader(self.multi)
            else:
                self.multi.add(sl)
                self.sel = sl
            self.refresh()
            return
        changed = sl != self.sel
        self.sel = sl
        self.multi = {sl} if sl is not None else set()
        if changed and sl is not None:
            self.cat_var.set("")
            self.speed.set(8.0 if cls(self.fr.figs[sl][2]) in "SB" else 3.0)
        self.refresh()

    def on_tree(self, _e):
        ids = {int(i) for i in self.tree.selection() if cls(self.fr.figs[int(i)][2]) not in "LR"}
        if ids == self.multi:
            return
        if not ids:
            return self.select(None)
        if len(ids) == 1:
            return self.select(next(iter(ids)))
        added = ids - self.multi
        self.multi = ids
        if len(added) == 1:
            self.sel = next(iter(added))
        elif self.sel not in ids:
            self.sel = self.pick_leader(ids)
        self.refresh()

    def _path_slots(self, f):
        sel_ref = self.ref_slot() if self.sel is not None else None
        slots = []
        if self.all_paths.get():
            slots = [i for i, g in enumerate(f.figs) if cls(g[2]) not in "LRB"]
        if self.show_path.get() and sel_ref is not None and sel_ref not in slots:
            slots.append(sel_ref)
        if self.show_path.get() and len(self.multi) > 1:
            for m in sorted(self.multi):
                r = self.ref_slot(m)
                if r is not None and r < len(f.figs) and cls(f.figs[r][2]) not in "LR" and r not in slots:
                    slots.append(r)
        slots.sort(key=lambda i: i == sel_ref)
        return slots, sel_ref

    @staticmethod
    def _ball_runs(frames, s, b):
        up = [fr.figs[s][:2] != fr.figs[b][:2] for fr in frames]
        runs, i, n = [], 0, len(up)
        while i < n:
            if up[i]:
                j = i
                while j + 1 < n and up[j + 1]:
                    j += 1
                runs.append((max(0, i - 1), min(n - 1, j + 1)))
                i = j + 1
            else:
                i += 1
        return up, runs

    @staticmethod
    def _lighten(value, k=0.45):
        return "#%02x%02x%02x" % tuple(round(v + (255 - v) * k) for v in ToreEditorPanel._hex_rgb(value))

    def _build_path_cache(self, sc):
        self._path_cache = []
        if len(sc.frames) < 2:
            return
        f = self.fr
        slots, sel_ref = self._path_slots(f)
        cut_slots = set(self.group_slots())
        for i in slots:
            sid = f.figs[i][2]
            col = self.path_color(sid)
            end = self.moving_span(i) if i in cut_slots else len(sc.frames) - 1
            self._path_cache.append({
                "slot": i,
                "color": col,
                "pts": [self.ctr(fr.figs[i]) for fr in sc.frames[:end + 1]],
                "main": i == sel_ref and self.show_path.get(),
            })
            b = f.index_of("B") if cls(sid) == "S" else None
            if b is not None:
                up, runs = self._ball_runs(sc.frames, i, b)
                if runs:
                    bend = self.moving_span(b) if b in cut_slots else len(sc.frames) - 1
                    self._path_cache.append({
                        "slot": b,
                        "color": self._lighten(col),
                        "pts": [self.ctr(fr.figs[b]) for fr in sc.frames[:bend + 1]],
                        "main": False,
                        "runs": runs,
                        "show": up[:bend + 1],
                    })

    @staticmethod
    def _hex_rgb(value):
        value = value.lstrip("#")
        try:
            return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))
        except (TypeError, ValueError):
            return (255, 255, 255)

    @staticmethod
    def _draw_dashed_line(draw, pts, fill, width=1, dash=4, gap=3):
        if len(pts) < 2:
            return
        phase = 0.0
        drawing = True
        for a, b in zip(pts, pts[1:]):
            x0, y0 = a
            x1, y1 = b
            dx, dy = x1 - x0, y1 - y0
            seg_len = math.hypot(dx, dy)
            if seg_len <= 0.0:
                continue
            pos = 0.0
            while pos < seg_len:
                run = (dash if drawing else gap) - phase
                take = min(run, seg_len - pos)
                u0, u1 = pos / seg_len, (pos + take) / seg_len
                if drawing:
                    draw.line((x0 + dx * u0, y0 + dy * u0, x0 + dx * u1, y0 + dy * u1), fill=fill, width=width)
                pos += take
                phase += take
                limit = dash if drawing else gap
                if phase >= limit - 1e-9:
                    phase = 0.0
                    drawing = not drawing

    @staticmethod
    def _path_shown(d, k):
        return d.get("show") is None or d["show"][k]

    def _render_path_layer(self, c, sc):
        self._path_photo = None
        self._path_static_id = None
        self._path_current_ids = []
        self._path_label_ids = []
        if not self._path_cache:
            return

        cw, ch = FW * self.z(), FH * self.z()
        overlay = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        current = self.idx

        for d in self._path_cache:
            pts = d["pts"]
            col = self._hex_rgb(d["color"]) + (255,)
            ipts = [(round(x), round(y)) for x, y in pts]
            for a, b in d.get("runs") or [(0, len(ipts) - 1)]:
                seg = ipts[a:b + 1]
                if len(seg) < 2:
                    continue
                if d["main"]:
                    self._draw_dashed_line(draw, seg, col, width=1, dash=4, gap=3)
                else:
                    draw.line(seg, fill=col, width=1)

            ir = max(1, round(2.5 if d["main"] else 1.5))
            for k, (px, py) in enumerate(pts):
                if not self._path_shown(d, k):
                    continue
                x, y = round(px), round(py)
                draw.ellipse((x - ir, y - ir, x + ir, y + ir), fill=col)

        self._path_photo = ImageTk.PhotoImage(overlay)
        self._path_static_id = c.create_image(0, 0, anchor="nw", image=self._path_photo, tags="path_static")

        for d in self._path_cache:
            pts = d["pts"]
            if not pts or not (0 <= current < len(pts)):
                self._path_current_ids.append(None)
                continue
            px, py = pts[current]
            r = 4 if d["main"] else 2
            oid = c.create_oval(px - r, py - r, px + r, py + r, fill=d["color"], outline="white", tags="path_current", state="normal" if self._path_shown(d, current) else "hidden")
            self._path_current_ids.append(oid)

        if self.sc() >= 3:
            for d in self._path_cache:
                if not d["main"]:
                    continue
                for k, (px, py) in enumerate(d["pts"]):
                    if k % 5 != 4:
                        continue
                    oid = c.create_text(px, py - 7, text=str(k + 1), fill=d["color"], font=("TkDefaultFont", 7), tags="path_static_label", state="hidden" if k == current else "normal")
                    self._path_label_ids.append((k, oid))

    def _draw_path_current(self, c, k=None):
        if not self._path_cache or not self._path_current_ids:
            return
        k = self.idx if k is None else k
        for kk, oid in self._path_label_ids:
            c.itemconfigure(oid, state="hidden" if kk == k else "normal")
        for oid, d in zip(self._path_current_ids, self._path_cache):
            if oid is None:
                continue
            pts = d["pts"]
            if not (0 <= k < len(pts)) or not self._path_shown(d, k):
                c.itemconfigure(oid, state="hidden")
                continue
            px, py = pts[k]
            r = 4 if d["main"] else 2
            c.coords(oid, px - r, py - r, px + r, py + r)
            c.itemconfigure(oid, state="normal")

    def _field_photo(self, f):
        z = self.z()
        img = compose(self.gfx, f, self.ghosts())
        img = img.resize((FW * z, FH * z), Image.NEAREST, box=(self.vx, self.vy, self.vx + FW / self.vz, self.vy + FH / self.vz))
        self._photo = ImageTk.PhotoImage(img)

    def _draw_window_mask(self, c, f):
        if not self.show_win.get():
            return
        cw, ch = FW * self.z(), FH * self.z()
        x0, y0 = self.cx(f.scroll[0]), self.cy(f.scroll[1])
        x1, y1 = self.cx(f.scroll[0] + WIN_W), self.cy(f.scroll[1] + WIN_H)
        ax0, ay0 = max(0, min(cw, x0)), max(0, min(ch, y0))
        ax1, ay1 = max(0, min(cw, x1)), max(0, min(ch, y1))
        for r in ((0, 0, cw, ay0), (0, ay1, cw, ch), (0, ay0, ax0, ay1), (ax1, ay0, cw, ay1)):
            if r[2] > r[0] and r[3] > r[1]:
                c.create_rectangle(*r, fill="black", stipple="gray50", outline="", tags="play_win")
        c.create_rectangle(x0, y0, x1, y1, outline="#00e5ff", tags="play_win")

    def _draw_sprite_marks(self, c, f):
        if self.show_ids.get():
            for g in f.figs:
                if cls(g[2]) not in "LR":
                    c.create_text(self.cx(g[0]) + 1, self.cy(g[1] + Y_OFFSET) - 1, anchor="sw", text=str(g[2]), fill="#fff59d", font=("TkDefaultFont", 7), tags="play_dyn")
        for sm in self.multi:
            if sm != self.sel and sm < len(f.figs):
                x, y, sid = f.figs[sm]
                c.create_rectangle(*self.box(x, y, sid), outline="#00e5ff", width=2, dash=(3, 2), tags="play_dyn")
        if self.sel is not None:
            x, y, sid = f.figs[self.sel]
            c.create_rectangle(*self.box(x, y, sid), outline="#ffff00", width=2, tags="play_dyn")
            if len(self.multi) > 1:
                c.create_text(self.cx(x) + 1, self.cy(y + Y_OFFSET) - 1, anchor="sw", text="leader", fill="#ffff00", font=("TkDefaultFont", 7, "bold"), tags="play_dyn")

    def _sync_ball_h(self, f):
        sb, bb = f.index_of("S"), f.index_of("B")
        self.ball_h.set(f.figs[sb][1] - f.figs[bb][1] if sb is not None and bb is not None else 0)

    def refresh_play(self):
        if self._canvas_image_id is None:
            self.refresh()
            return
        f = self.fr
        self.sx.set(f.scroll[0])
        self.sy.set(f.scroll[1])
        self.clamp_view()
        self._field_photo(f)
        c = self.canvas
        c.itemconfigure(self._canvas_image_id, image=self._photo)
        c.delete("play_win", "play_dyn")
        self._draw_window_mask(c, f)
        if self._path_static_id is not None:
            c.tag_lower("play_win", "path_static")
        self._draw_sprite_marks(c, f)
        self._draw_path_current(c)
        self._sync_ball_h(f)
        self.draw_timeline()
        self._set_title(os.path.basename(self.scene.path) if self.scene.path else tr("title.new"), len(self.scene.frames))
        self.sync_cam_follow()

    def _path_sig(self):
        f = self.fr
        cut = [s for s in self.group_slots() if s < len(f.figs)]
        return (tuple(cls(g[2]) for g in f.figs), tuple(self.moving_span(s) for s in cut))

    def refresh_step(self):
        if self._canvas_image_id is None or self._path_sig_built is None or self._path_sig() != self._path_sig_built:
            return self.refresh()
        self.refresh_play()
        self.snd_var.set(next((k for k, e in enumerate(self.scene.events) if e == self.idx), -1))
        self.draw_overlay()
        self.fill_tree()
        self.draw_poses()

    def refresh(self, light=False):
        sc, z = self.scene, self.z()
        n = len(sc.frames)
        self.idx = min(self.idx, n - 1)
        f = self.fr
        self.sx.set(f.scroll[0])
        self.sy.set(f.scroll[1])
        self.clamp_view()
        self._field_photo(f)
        c = self.canvas
        c.config(width=FW * z, height=FH * z)
        c.delete("all")
        self._canvas_image_id = c.create_image(0, 0, anchor="nw", image=self._photo)
        self._draw_window_mask(c, f)
        self._build_path_cache(sc)
        self._path_sig_built = self._path_sig()
        self._render_path_layer(c, sc)
        self._draw_sprite_marks(c, f)
        self._sync_ball_h(f)
        self.update_view_bars()
        self.draw_overlay()
        self.draw_timeline()
        self.snd_var.set(next((k for k, e in enumerate(sc.events) if e == self.idx), -1))
        if not light:
            self.fill_tree()
            self.draw_poses()
        self._set_title(os.path.basename(sc.path) if sc.path else tr("title.new"), n)
        self.sync_cam_follow()

    def fill_tree(self):
        nm = self.names()
        self.tree.unbind("<<TreeviewSelect>>")
        figs = self.fr.figs
        kids = self.tree.get_children()
        if len(kids) == len(figs) and all(k == str(i) for i, k in enumerate(kids)):
            for sl, g in enumerate(figs):
                self.tree.item(str(sl), text=nm[sl], values=tuple(g))
            if not self.multi and self.tree.selection():
                self.tree.selection_remove(*self.tree.selection())
        else:
            if kids:
                self.tree.delete(*kids)
            for sl, g in enumerate(figs):
                self.tree.insert("", "end", iid=str(sl), text=nm[sl], values=tuple(g))
        if self.multi:
            self.tree.selection_set([str(i) for i in sorted(self.multi)])
        if self.sel is not None:
            self.tree.focus(str(self.sel))
            self.tree.see(str(self.sel))
        self.tree.bind("<<TreeviewSelect>>", self.on_tree)

    def draw_timeline(self):
        c = self.tl
        c.delete("all")
        fs = self.scene.frames
        n = len(fs)
        cw = self._tl_cw()
        sel = self.sel if self.sel is not None and self.sel < min(len(f.figs) for f in fs) else None
        sids = [f.figs[sel][2] for f in fs] if sel is not None else []
        for i in range(n):
            x0 = 4 + i * cw
            c.create_rectangle(x0, 4, x0 + cw - 1, 18, outline="", fill="#1e88e5" if i == self.idx else ("#d8d8d8" if i % 2 else "#c4c4c4"))
            if sids:
                c.create_rectangle(x0, 20, x0 + cw - 1, 27, outline="", fill=TL_KIND_COLORS[sprite_kind(sids[i])])
            if cw >= 16 or i % 5 == 4 or i == self.idx:
                c.create_text(x0 + cw / 2, 45, text=str(i + 1), font=("TkDefaultFont", 7), fill="#444")
        self._draw_action_labels(c, sel, sids, cw)
        for k, e in enumerate(self.scene.events):
            if e is not None and e < n:
                x = 4 + e * cw + cw / 2
                c.create_polygon(x - 5, 64, x + 5, 64, x, 54, fill=SOUNDS[k][1], outline="black")
        a, b = self.loop_range()
        xa, xb = 4 + a * cw, 4 + (b + 1) * cw
        if a > 0:
            c.create_rectangle(4, 4, xa, 27, fill="#000", stipple="gray50", outline="")
        if b < n - 1:
            c.create_rectangle(xb, 4, 4 + n * cw, 27, fill="#000", stipple="gray50", outline="")
        c.create_line(xa, 2, xa, 82, fill="#d32f2f", width=2)
        c.create_line(xb, 2, xb, 82, fill="#6a1b9a", width=2)
        c.create_polygon(xa, 66, xa + 13, 74, xa, 83, fill="#d32f2f", outline="black")
        c.create_polygon(xb, 66, xb - 13, 74, xb, 83, fill="#6a1b9a", outline="black")

    def _draw_action_labels(self, c, sel, sids, cw):
        self._tl_acts = []
        acts = find_actions(sids) if sids else []
        for k, (a, b, key, side) in enumerate(acts):
            x0 = 4 + a * cw
            limit = 4 + (acts[k + 1][0] if k + 1 < len(acts) else len(sids)) * cw
            c.create_line(x0, 29, 4 + b * cw - 1, 29, fill=TL_KIND_COLORS["action"])
            text = action_label(key, side)
            room = int((limit - x0) / 5)
            if room < 2:
                continue
            if len(text) > room:
                text = text[:room - 1] + "\u2026"
            item = c.create_text(x0, 36, anchor="w", text=text, font=("TkDefaultFont", 7, "bold"), fill="#e65100")
            self._tl_acts.append((c.bbox(item), sel, a, b))

    def remove_action(self, sl, a, b):
        fs = self.scene.frames
        seq = tuple(fs[i].figs[sl][2] for i in range(a, b))
        self.snap()
        prev = self._act_backup.pop((sl, a, seq), None)
        if prev:
            for i, sid in zip(range(a, b), prev):
                fs[i].figs[sl][2] = sid
                fs[i].touch()
        else:
            if a == 0:
                sid = fs[0].figs[sl][2]
                fs[0].figs[sl][2] = stand_id(sid, dir_of_sprite(sid))
                fs[0].touch()
            self.auto_sprites([sl], a, b - 1, force=True)
        self.refresh()

    def _tl_action_at(self, x, y):
        for bb, sl, a, b in self._tl_acts:
            if bb and bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]:
                return sl, a, b
        return None


    def _action_menu(self, parent):
        am = tk.Menu(parent, tearoff=0)
        for key in ACTION_ORDER:
            for side in action_sides(key):
                am.add_command(label=action_label(key, side), command=lambda k=key, s=side: self.do_action(k, s))
            am.add_separator()
        return am


    def _run_menu(self, parent):
        rm = tk.Menu(parent, tearoff=0)
        for d in DIRS:
            self._mi(rm, "command", "run.dir", fmt=dict(d=d, name=tr(DIR_LABEL[d])), command=lambda d=d: self.do_cycle(d))
        return rm


    def pick_main(self, k):
        self.tool_main.set(k)
        self.on_main_tool()

    def sync_tool_buttons(self):
        m = self.tool_main.get()
        for k, b in self.tool_btns.items():
            b.state(["pressed"] if k == m else ["!pressed"])

    def on_main_tool(self):
        m = self.tool_main.get()
        self.tool.set(self.path_kind.get() if m == "path" else m)
        self.set_tool()

    def on_path_kind(self):
        self.tool.set(self.path_kind.get())
        self.set_tool()

    def show_tool_options(self):
        m = self.tool_main.get()
        for k, fr in self.opt_frames.items():
            if k == m:
                fr.pack(fill="x", pady=2)
            else:
                fr.pack_forget()
        self.opt.config(text=tr({"select": "ot.select", "path": "ot.path", "pan": "ot.pan"}[m]))
        if self.tool.get() == "draw":
            self.cb_persp.pack_forget()
            self.rb_timing.pack(side="left")
        else:
            self.rb_timing.pack_forget()
            self.cb_persp.pack(side="left")
            if self.pmode.get() == "timing":
                self.pmode.set("speed")

    def set_tool(self):
        t = self.tool.get()
        self.stroke, self.way = None, []
        if t in ("draw", "way"):
            self.path_kind.set(t)
        self.tool_main.set("path" if t in ("draw", "way") else t)
        self.sync_tool_buttons()
        self.show_tool_options()
        self.hint = tr("hint." + t)
        self.set_tool_cursor()
        ct = self.cam_target
        if (t == "pan" and self.cam_follow.get() and self.cam_explicit and ct is not None and ct != self.sel
                and ct < len(self.fr.figs) and cls(self.fr.figs[ct][2]) in "PB"):
            self.select(ct)
        self.note(self.hint)
        self.draw_overlay()


    def set_zoom(self, d):
        self.zoom.set(max(1, min(6, self.z() + d)))
        self.rezoom()


    def escape(self):
        if self.stroke or self.way or (self.drag and self.drag.get("kind") == "band"):
            self.stroke, self.way, self.drag = None, [], None
            self.draw_overlay()
        else:
            self.select(None)


    def select_all(self):
        ids = {i for i, g in enumerate(self.fr.figs) if cls(g[2]) == "P"}
        if ids:
            self.multi = ids
            self.sel = self.pick_leader(ids)
            self.refresh()

    def ctr(self, g):
        w = sprite_w(g[2])
        return self.cx(g[0] + w / 2), self.cy(g[1] + Y_OFFSET + path_h(g[2]))


    def pos_ctr(self, x, y, sid):
        w = sprite_w(sid)
        return self.cx(x + w / 2), self.cy(y + Y_OFFSET + path_h(sid))


    def ptr_pos(self, ex, ey, sid):
        w = sprite_w(sid)
        return self.fx(ex) - w / 2, self.fy(ey) - Y_OFFSET - path_h(sid)


    def pick_leader(self, ids):
        fs = self.fr.figs
        return min(ids, key=lambda s: (fs[s][1], s))

    def set_leader(self, sl):
        if sl in self.multi and sl != self.sel:
            self.sel = sl
            self.refresh()
            self.note(tr("st.leader", name=self.names().get(sl, tr("name.sprite"))))

    def group_slots(self):
        base = set(self.multi) if self.multi else ({self.sel} if self.sel is not None else set())
        out = set(base)
        for s in base:
            p = self.partner(s)
            if p is not None:
                out.add(p)
        return sorted(out)


    def path_hit(self, ex, ey, tol=7.0):
        if self.sel is None or not self.show_path.get() or len(self.scene.frames) < 2:
            return None
        rs = self.ref_slot()
        end = self.moving_span(rs)
        best, bd = None, tol
        for k, f in enumerate(self.scene.frames[:end + 1]):
            cx, cy = self.ctr(f.figs[rs])
            d = math.hypot(cx - ex, cy - ey)
            if d < bd:
                best, bd = k, d
        return best


    def near_window_edge(self, px, py):
        sx, sy = self.fr.scroll
        tol = 3
        inx = sx - tol <= px <= sx + WIN_W + tol
        iny = sy - tol <= py <= sy + WIN_H + tol
        on_v = inx and iny and (abs(px - sx) <= tol or abs(px - (sx + WIN_W)) <= tol)
        on_h = inx and iny and (abs(py - sy) <= tol or abs(py - (sy + WIN_H)) <= tol)
        return on_v or on_h


    def on_dbl(self, e):
        if self.tool.get() == "way" and self.way:
            self.way = self.way[:-1] if len(self.way) > 1 else self.way 
            self.finish_way()


    def set_loop(self, a=None, b=None):
        n = len(self.scene.frames)
        ca, cb = self.loop_range()
        na, nb = (ca if a is None else a), (cb if b is None else b)
        if na > nb:
            if a is None:
                na = nb
            else:
                nb = n - 1
        self.loop_a = max(0, na)
        self.loop_b = None if nb >= n - 1 else nb
        self.draw_timeline()

    def on_tl_right(self, e):
        hit = self._tl_action_at(e.x, e.y)
        if hit:
            return self.remove_action(*hit)
        n = len(self.scene.frames)
        i = max(0, min(n - 1, int((e.x - 4) / self._tl_cw())))
        self.goto(i)
        m = tk.Menu(self, tearoff=0)
        m.add_command(label=tr("tl.frame", n=i + 1), state="disabled")
        m.add_command(label=tr("play.here"), command=lambda: self.toggle("here"))
        m.add_command(label=tr("tl.loop_start"), command=lambda: self.set_loop(a=i))
        m.add_command(label=tr("tl.loop_end"), command=lambda: self.set_loop(b=i))
        m.add_command(label=tr("tl.loop_reset"), command=lambda: self.set_loop(a=0, b=n - 1))
        m.add_separator()
        m.add_command(label=tr("e.insframe"), command=self.ins_frame)
        m.add_command(label=tr("tl.delete"), command=self.del_frame)
        m.add_separator()
        snd = tk.Menu(m, tearoff=0)
        snd.add_command(label=tr("snd.none"), command=lambda: (self.snd_var.set(-1), self.set_sound()))
        for k, (nm, _c) in enumerate(SOUNDS):
            snd.add_command(label=tr(nm), command=lambda k=k: (self.snd_var.set(k), self.set_sound()))
        m.add_cascade(label=tr("tl.sound"), menu=snd)
        m.tk_popup(e.x_root, e.y_root)

    def _fps(self):
        try:
            return max(1, int(self.fps.get()))
        except (tk.TclError, ValueError):
            return 12


    def _speed(self):
        try:
            return max(0.5, float(self.speed.get()))
        except (tk.TclError, ValueError):
            return 3.0


    def _clampx(self, v, sid):
        lo, hi = xlim(sid)
        return max(lo, min(hi, int(round(v))))


    @staticmethod
    def _ylo(sid):
        return BALL_Y_MIN if cls(sid) == "B" else 0

    def _clampy(self, v, sid=None):
        return max(self._ylo(sid) if sid is not None else 0, min(MAX_Y, int(round(v))))


    def mirror_sel(self):
        if self.need_sel():
            self.snap()
            for sl in self.targets():
                self.set_pose_to(sl, mirror_pose(self.fr.figs[sl][2]))
            self.refresh()

    def bake_path(self, pts, samples=None, n=None, persp=False):
        sl = self.ref_slot()
        if sl is None:
            return
        fs = self.scene.frames
        start = (float(self.fr.figs[sl][0]), float(self.fr.figs[sl][1]))
        path = [start] + [(float(x), float(y)) for x, y in pts[1:]]
        if poly_len(path) < 1:
            return self.note(tr("st.dest_close"))
        mode = self.pmode.get()
        hw = sprite_w(fs[self.idx].figs[sl][2]) / 2.0
        wpath = [persp_to_world(x + hw, y) for x, y in _densify(path)] if persp else None

        def pfw(w):
            px_, py_ = persp_from_world(*w)
            return px_ - hw, py_

        def rs(nn):
            if persp:
                return [pfw(w) for w in resample_steps(wpath, nn)]
            return resample_steps(path, nn)

        if n is not None:
            pos = resample_steps(path, max(1, n))
        elif mode == "timing" and samples and len(samples) > 1 and samples[-1][0] > 0.05:
            pos = resample_time(samples, self._fps())
            if self.smooth.get() and len(pos) > 2:
                for _ in range(2):
                    pos = [pos[0]] + [((pos[i - 1][0] + 2 * pos[i][0] + pos[i + 1][0]) / 4, (pos[i - 1][1] + 2 * pos[i][1] + pos[i + 1][1]) / 4) for i in range(1, len(pos) - 1)] + [pos[-1]]
        elif mode == "frames":
            pos = rs(max(1, int(self.pframes.get())))
        else:
            pos = rs(max(1, math.ceil(poly_len(wpath if persp else path) / self._speed())))
        n = len(pos)
        self.snap()
        if self.idx + n + 1 > MAX_FRAMES:
            n = MAX_FRAMES - 1 - self.idx
            pos = pos[:n]
        if n < 1:
            return self.note(tr("st.no_next"))
        self.ensure_frames(self.idx + n + 1)
        slots = self.group_slots()
        base = {s: (fs[self.idx].figs[s][0], fs[self.idx].figs[s][1]) for s in slots}
        endold = {s: (fs[self.idx + n].figs[s][0], fs[self.idx + n].figs[s][1]) for s in slots}
        slotpos = None
        if persp:
            w0 = persp_to_world(start[0] + hw, start[1])
            wpos = [persp_to_world(px + hw, py) for px, py in pos]
            slotpos, blocked = {}, 0
            for s in slots:
                hs = sprite_w(fs[self.idx].figs[s][2]) / 2.0
                bw = persp_to_world(base[s][0] + hs, base[s][1])
                seq = []
                for wx, wv in wpos:
                    qx, qy = persp_from_world(bw[0] + wx - w0[0], bw[1] + wv - w0[1])
                    seq.append((qx - hs, qy))
                slotpos[s], hit = clamp_field(seq, *xlim(fs[self.idx].figs[s][2]), ylo=float(self._ylo(fs[self.idx].figs[s][2])))
                blocked += hit
            shadow = next((t for t in slots if cls(fs[self.idx].figs[t][2]) == "S"), None)
            if shadow is not None:
                for s in slots:
                    if cls(fs[self.idx].figs[s][2]) == "B":
                        slotpos[s] = [(base[s][0] + sx - base[shadow][0], base[s][1] + sy - base[shadow][1])
                                      for sx, sy in slotpos[shadow]]
        for k, (px, py) in enumerate(pos, start=1):
            f = fs[self.idx + k]
            for s in slots:
                if slotpos:
                    tx, ty = slotpos[s][k - 1]
                else:
                    tx, ty = base[s][0] + px - start[0], base[s][1] + py - start[1]
                f.figs[s][0] = self._clampx(tx, f.figs[s][2])
                f.figs[s][1] = self._clampy(ty, f.figs[s][2])
            f.touch()
        if self.follow.get():
            fe = fs[self.idx + n]
            for j in range(self.idx + n + 1, len(fs)):
                for s in slots:
                    fs[j].figs[s][0] = self._clampx(fs[j].figs[s][0] + fe.figs[s][0] - endold[s][0], fs[j].figs[s][2])
                    fs[j].figs[s][1] = self._clampy(fs[j].figs[s][1] + fe.figs[s][1] - endold[s][1], fs[j].figs[s][2])
                fs[j].touch()
        if self.auto_spr.get():
            self.auto_sprites(slots, self.idx + 1, self.idx + n, force=True)
        self.cam_refollow()
        self.refresh()
        self.note(tr("st.baked", persp=tr("st.persp") if persp else "", n=n, a=self.idx + 1, b=self.idx + n + 1, length="%.0f" % poly_len(path), blocked=tr("st.blocked", n=blocked) if persp and blocked else ""))


    def auto_sprites(self, slots, i0, i1, force=True):
        fs = self.scene.frames
        diag = self.diag.get()
        i0 = max(1, i0)
        i1 = min(len(fs) - 1, i1)
        for sl in slots:
            c = cls(fs[i0].figs[sl][2]) if i0 <= i1 else None
            if c in (None, "S", "L", "R"):
                continue
            if c == "B":
                if not BALL_ROT:
                    continue
                for i in range(i0, i1 + 1):
                    fs[i].figs[sl][2] = BALL_ROT[i % 3]
                    fs[i].touch()
                continue
            dirs = []
            for i in range(i0, i1 + 1):
                a, b = fs[i - 1].figs[sl], fs[i].figs[sl]
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 0.5:
                    dirs.append(None)
                    continue
                p0, p1 = fs[max(0, i - 2)].figs[sl], fs[min(len(fs) - 1, i + 1)].figs[sl]
                dirs.append(dir8(p1[0] - p0[0], p1[1] - p0[1], diag) or dir8(b[0] - a[0], b[1] - a[1], diag))
            dirs = _stabilize(dirs)
            prev_sid = fs[i0 - 1].figs[sl][2]
            face = dir_of_sprite(prev_sid)
            ph = 0
            for n, i in enumerate(range(i0, i1 + 1)):
                f = fs[i]
                g = f.figs[sl]
                if not force and g[2] not in loco_ids(g[2]):
                    prev_sid, face, ph = g[2], dir_of_sprite(g[2]), 0
                    continue
                d = dirs[n]
                if d is None:
                    new = stand_id(g[2], face)
                    ph = 0
                else:
                    face = d
                    cyc = loco_cycle(g[2], d)
                    if not cyc:
                        prev_sid = g[2]
                        continue
                    if prev_sid in cyc and ph == 0:
                        ph = (cyc.index(prev_sid) + 1) % len(cyc)
                    new = cyc[ph % len(cyc)]
                    ph += 1
                g[2] = new
                prev_sid = new
                f.touch()


    def auto_here(self, whole=False):
        if not self.need_sel():
            return
        self.snap()
        i0 = 1 if whole else self.idx
        self.auto_sprites(self.group_slots(), i0, len(self.scene.frames) - 1, force=False)
        self.refresh()
        self.note(tr("st.autospr"))


    def do_stand(self):
        if not self.need_sel():
            return
        tg = [s for s in self.targets() if team_of(self.fr.figs[s][2]) is not None]
        if not tg:
            return
        self.snap()
        for sl in tg:
            sid = self.fr.figs[sl][2]
            new = stand_id(sid, self.run_dir(sl, self.idx) or dir_of_sprite(sid))
            for f in self.scene.frames[self.idx:]:
                f.figs[sl][2] = new
                f.touch()
        self.refresh()


    def run_dir(self, sl, i):
        fs = self.scene.frames
        for j in range(min(i, len(fs) - 1), 0, -1):
            a, b = fs[j - 1].figs[sl], fs[j].figs[sl]
            if math.hypot(b[0] - a[0], b[1] - a[1]) >= 0.5:
                return dir8(b[0] - a[0], b[1] - a[1], self.diag.get())
        return None


    def do_cycle(self, d):
        if not self.need_sel():
            return
        tg = [(s, loco_cycle(self.fr.figs[s][2], d)) for s in self.targets()]
        tg = [(s, c) for s, c in tg if c]
        if not tg:
            return
        self.snap()
        fs = self.scene.frames
        for sl, cyc in tg:
            sid = self.fr.figs[sl][2]
            ph = cyc.index(sid) + 1 if sid in cyc else 0
            start = self.idx + (1 if sid in cyc else 0)
            for k, i in enumerate(range(start, len(fs))):
                fs[i].figs[sl][2] = cyc[(ph + k) % len(cyc)]
                fs[i].touch()
        self.refresh()


    def do_action(self, key, side):
        if not self.need_sel():
            return
        seqs = [(s, action_ids(self.fr.figs[s][2], key, side)[:MAX_FRAMES - self.idx]) for s in self.targets()]
        seqs = [(s, q) for s, q in seqs if q]
        if not seqs:
            return self.note(tr("st.players_only"))
        nmax = max(len(q) for _, q in seqs)
        self.snap()
        self.ensure_frames(self.idx + nmax)
        fs = self.scene.frames
        for sl, seq in seqs:
            self._act_backup[(sl, self.idx, tuple(seq))] = [fs[self.idx + j].figs[sl][2] for j in range(len(seq))]
            for j, s in enumerate(seq):
                fs[self.idx + j].figs[sl][2] = s
                fs[self.idx + j].touch()
        if self.resume.get():
            for sl, seq in seqs:
                if self.idx + len(seq) < len(fs):
                    self.auto_sprites([sl], self.idx + len(seq), len(fs) - 1, force=False)
        self.refresh()
        self.note(tr("st.action_done", label=action_label(key, side), frames=nmax, f=self.idx + 1, n=len(seqs)))


    def tween_to(self, end):
        if end <= self.idx:
            return
        self.snap()
        fs, n = self.scene.frames, end - self.idx
        for s in self.group_slots():
            a, b = fs[self.idx].figs[s], fs[end].figs[s]
            for k in range(1, n):
                fs[self.idx + k].figs[s][0] = round(a[0] + (b[0] - a[0]) * k / n)
                fs[self.idx + k].figs[s][1] = round(a[1] + (b[1] - a[1]) * k / n)
                fs[self.idx + k].touch()
        if self.auto_spr.get():
            self.auto_sprites(self.group_slots(), self.idx + 1, end, force=False)
        self.cam_refollow()
        self.refresh()


    def moving_span(self, sl):
        fs = self.scene.frames
        last = self.idx
        for i in range(self.idx + 1, len(fs)):
            a, b = fs[i - 1].figs[sl], fs[i].figs[sl]
            if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.25:
                last = i
        return last


    def smooth_path(self):
        if not self.need_sel():
            return
        self.snap()
        fs = self.scene.frames
        for s in self.group_slots():
            j = self.moving_span(s)
            if j - self.idx < 2:
                continue
            for _ in range(3):
                old = [(fs[i].figs[s][0], fs[i].figs[s][1]) for i in range(self.idx, j + 1)]
                for i in range(self.idx + 1, j):
                    w = old[max(0, i - self.idx - 2):i - self.idx + 3]
                    fs[i].figs[s][0] = self._clampx(sum(p[0] for p in w) / len(w), fs[i].figs[s][2])
                    fs[i].figs[s][1] = self._clampy(sum(p[1] for p in w) / len(w), fs[i].figs[s][2])
        for i in range(self.idx, len(fs)):
            fs[i].touch()
        if self.auto_spr.get():
            self.auto_sprites(self.group_slots(), self.idx + 1, len(fs) - 1, force=False)
        self.cam_refollow()
        self.refresh()


    def even_speed(self):
        if not self.need_sel():
            return
        self.snap()
        fs = self.scene.frames
        for s in self.group_slots():
            j = self.moving_span(s)
            if j - self.idx < 2:
                continue
            path = [(float(fs[i].figs[s][0]), float(fs[i].figs[s][1])) for i in range(self.idx, j + 1)]
            if poly_len(path) < 1:
                continue
            pos = resample_steps(path, j - self.idx)
            for k, (px, py) in enumerate(pos, start=1):
                fs[self.idx + k].figs[s][0] = self._clampx(px, fs[self.idx + k].figs[s][2])
                fs[self.idx + k].figs[s][1] = self._clampy(py, fs[self.idx + k].figs[s][2])
        for i in range(self.idx, len(fs)):
            fs[i].touch()
        self.cam_refollow()
        self.refresh()
        self.note(tr("st.even"))


    def freeze_here(self):
        if not self.need_sel():
            return
        self.snap()
        fs = self.scene.frames
        for s in self.group_slots():
            x, y = fs[self.idx].figs[s][0], fs[self.idx].figs[s][1]
            for f in fs[self.idx + 1:]:
                f.figs[s][0], f.figs[s][1] = x, self._clampy(y, f.figs[s][2])
        for f in fs[self.idx + 1:]:
            f.touch()
        if self.auto_spr.get():
            self.auto_sprites(self.group_slots(), self.idx + 1, len(fs) - 1, force=False)
        self.refresh()


    def cam_sel_ok(self):
        return (self.sel is not None and self.sel < len(self.fr.figs)
                and cls(self.fr.figs[self.sel][2]) in "PB")

    def sync_cam_follow(self):
        ok = self.cam_sel_ok() or self.fr.index_of("B") is not None or self.cam_follow.get()
        self.cb_camfol.state(["!disabled"] if ok else ["disabled"])
        txt = ""
        ct = self.cam_target
        if self.cam_follow.get() and ct is not None and ct < len(self.fr.figs):
            txt = tr("st.cam_focus", name=self.names().get(ct, tr("name.sprite")))
        self.cam_lbl.config(text=txt)

    def on_cam_follow(self):
        if not self.cam_follow.get():
            self.cam_target = None
            self.sync_cam_follow()
            return
        if not self.cam_sel_ok() and self.fr.index_of("B") is None:
            self.cam_follow.set(False)
            return
        self.auto_camera(self.cam_whole.get())

    def on_cam_whole(self):
        if self.cam_follow.get() and (self.cam_sel_ok() or self.cam_target is not None):
            self.auto_camera(self.cam_whole.get(), keep_target=not self.cam_sel_ok())

    def cam_release(self):
        if self.cam_follow.get():
            self.cam_follow.set(False)
        self.cam_target = None
        self.cam_explicit = False

    def cam_default(self):
        b = self.fr.index_of("B")
        if b is None:
            return
        self.cam_target, self.cam_i0, self.cam_snap, self.cam_explicit = b, 0, False, False
        self.cam_follow.set(True)

    def _cam_build(self, tgt, i0, snap):
        fs = self.scene.frames
        i0 = max(0, min(i0, len(fs) - 1))
        sx, sy = float(fs[i0].scroll[0]), float(fs[i0].scroll[1])
        for i in range(i0, len(fs)):
            f = fs[i]
            b = tgt if tgt is not None else f.index_of("B")
            if b is None or b >= len(f.figs):
                continue
            g = f.figs[b]
            wx = max(0.0, min(float(SCROLL_MAX_X), g[0] + sprite_w(g[2]) / 2 - WIN_W / 2))
            wy = max(0.0, min(float(SCROLL_MAX_Y), g[1] + Y_OFFSET - WIN_H / 2))
            if i == i0 and snap:
                sx, sy = wx, wy
            sx += max(-6.0, min(6.0, (wx - sx) * 0.35))
            sy += max(-2.0, min(2.0, (wy - sy) * 0.35))
            f.scroll = [int(round(sx)), int(round(sy))]
            f.dirty = True
        self.cam_target = tgt if tgt is not None else fs[i0].index_of("B")
        self.cam_i0, self.cam_snap = i0, snap
        self.cam_follow.set(True)

    def cam_refollow(self):
        ct = self.cam_target
        if not self.cam_follow.get() or ct is None or ct >= len(self.fr.figs):
            return
        self._cam_build(ct, self.cam_i0, self.cam_snap)

    def auto_camera(self, whole=False, keep_target=False):
        fs = self.scene.frames
        i0 = 0 if whole else self.idx
        if keep_target and self.cam_target is not None:
            tgt = self.cam_target
        else:
            tgt = self.sel if self.cam_sel_ok() else None
        if tgt is None and fs[i0].index_of("B") is None:
            return self.note(tr("sel.first"))
        self.snap()
        self._cam_build(tgt, i0, bool(whole))
        self.cam_explicit = True
        self.refresh()
        self.note(tr("st.cam_all") if whole else tr("st.cam_from"))


    def finish_stroke(self):
        st, self.stroke = self.stroke, None
        self.draw_overlay()
        if not st or len(st["pts"]) < 2 or poly_len(st["pts"]) < 2:
            return
        raw = st["pts"]
        pts = rdp(raw, 1.0)
        if self.smooth.get():
            pts = chaikin(pts, 2)
        pts[0], pts[-1] = raw[0], raw[-1]
        self.bake_path(pts, st["samples"])


    def finish_way(self):
        if self.tool.get() != "way" or not self.way or self.sel is None:
            return
        g = self.fr.figs[self.ref_slot()]
        pts = [(float(g[0]), float(g[1]))] + list(self.way)
        self.way = []
        if self.smooth.get() and len(pts) > 2:
            pts = catmull(pts)
        self.bake_path(pts, persp=self.persp.get())
        self.draw_overlay()


    def way_back(self):
        if self.tool.get() == "way" and self.way:
            self.way.pop()
            self.draw_overlay()


    def start_rope(self, k0, e):
        slots = self.group_slots()
        fs = self.scene.frames
        base = {s: [(f.figs[s][0], f.figs[s][1]) for f in fs] for s in slots}
        self.snap()
        self.drag = dict(kind="rope", k0=k0, x0=e.x, y0=e.y, slots=slots, base=base, changed=set())


    def move_rope(self, e):
        d = self.drag
        z = self.sc()
        dx, dy = (e.x - d["x0"]) / z, (e.y - d["y0"]) / z
        fs = self.scene.frames
        sigma = 0.45 if (e.state & 1) else max(0.5, float(self.rope.get()))
        w = gauss_w(len(fs), d["k0"], sigma)
        for i, f in enumerate(fs):
            wi = w[i]
            if self.pin.get():
                if d["k0"] > self.idx and i <= self.idx:
                    wi = 0
                elif d["k0"] < self.idx and i >= self.idx:
                    wi = 0
            if wi < 0.03:
                if i in d["changed"]:
                    for s in d["slots"]:
                        f.figs[s][0], f.figs[s][1] = d["base"][s][i]
                    f.touch()
                    d["changed"].discard(i)
                continue
            for s in d["slots"]:
                bx, by = d["base"][s][i]
                f.figs[s][0] = self._clampx(bx + dx * wi, f.figs[s][2])
                f.figs[s][1] = self._clampy(by + dy * wi, f.figs[s][2])
            f.touch()
            d["changed"].add(i)
        self.refresh(light=True)


    def end_rope(self, d):
        ch = d["changed"]
        if ch and self.auto_spr.get():
            self.auto_sprites(d["slots"], min(ch), max(ch) + 1, force=False)
        if ch:
            self.cam_refollow()
        self.refresh()


    def draw_overlay(self):
        c = self.canvas
        c.delete("ov")
        if self.sel is None:
            sid = None
        else:
            sid = self.fr.figs[self.ref_slot()][2]
        st = self.stroke
        if st and len(st["pts"]) > 1:
            pts = [v for p in st["pts"] for v in self.pos_ctr(p[0], p[1], st["sid"])]
            c.create_line(*pts, fill="#ff9800", width=2, tags="ov")
        if self.way and sid is not None:
            g = self.fr.figs[self.ref_slot()]
            pts = [(float(g[0]), float(g[1]))] + list(self.way)
            curve = catmull(pts) if (self.smooth.get() and len(pts) > 2) else pts
            c.create_line(*[v for p in curve for v in self.pos_ctr(p[0], p[1], sid)], fill="#ff9800", width=2, tags="ov")
            for k, p in enumerate(pts):
                cx, cy = self.pos_ctr(p[0], p[1], sid)
                c.create_rectangle(cx - 3, cy - 3, cx + 3, cy + 3, fill="#ff9800" if k else "#ffff00", outline="black", tags="ov")
            if self.cursor_pos:
                lx, ly = self.pos_ctr(pts[-1][0], pts[-1][1], sid)
                c.create_line(lx, ly, self.cx(self.cursor_pos[0]), self.cy(self.cursor_pos[1]), fill="#ffcc80", dash=(3, 3), tags="ov")
        d = self.drag
        if d and d.get("kind") == "band" and d.get("moved"):
            c.create_rectangle(d["x0"], d["y0"], d["x1"], d["y1"], outline="#00e5ff", dash=(3, 3), tags="ov")


    def build_action_grid(self):
        grid = self.act_grid
        for wd in grid.winfo_children():
            wd.destroy()
        for r, key in enumerate(ACTION_ORDER):
            ttk.Label(grid, text=ACTIONS[key]["label"], width=20).grid(row=r, column=0, sticky="w", pady=1)
            if ACTIONS[key].get("single"):
                self._reg(ttk.Button(grid, width=10, command=lambda k=key: self.do_action(k, "E")), "act.go").grid(row=r, column=1, columnspan=2, padx=1)
                continue
            ttk.Button(grid, text="< W", width=4, command=lambda k=key: self.do_action(k, "W")).grid(row=r, column=1, padx=1, pady=1)
            ttk.Button(grid, text="E >", width=4, command=lambda k=key: self.do_action(k, "E")).grid(row=r, column=2, padx=1, pady=1)

    def after_data_change(self):
        self._menus()
        self.build_action_grid()
        self.cat_var.set("")
        self.refresh()

    def reload_data(self):
        warn = load_data()
        try:
            load_kickoff()
        except DataError as ex:
            warn.append(str(ex))
        self.after_data_change()
        if warn:
            messagebox.showwarning(tr("mb.datafiles"), "\n".join(warn), parent=self.top)
        self.note(tr("st.data_reloaded_warn") if warn else tr("st.data_reloaded"))

    def save_kickoff_here(self):
        if not messagebox.askyesno(tr("mb.kickoff"), tr("mb.kick_confirm", file=KICKOFF_FILE)):
            return
        err = save_kickoff(self.fr.figs, self.fr.scroll)
        if err:
            return messagebox.showerror(tr("mb.kickoff"), tr("mb.kick_fail", err=err))
        self.note(tr("st.kick_saved", file=KICKOFF_FILE))

    def edit_data(self):
        if getattr(self, "_dw", None) is not None and self._dw.winfo_exists():
            return self._dw.lift()
        w = self._dw = tk.Toplevel(self.top)
        w.title(tr("de.title"))
        w.transient(self.top)
        pg = {"red": {n: list(v) for n, v in PLAYER_CATS}, "referee": {n: list(v) for n, v in REF_CATS}, "ball": {n: list(v) for n, v in BALL_ALL}}
        ad = {"order": list(ACTION_ORDER), "actions": copy.deepcopy(ACTIONS),
              "moves": {d: list(v) for d, v in MOVE_E.items()}, "stand": dict(STAND_K),
              "referee": {"move": {d: list(v) for d, v in REF_MOVE.items()}, "stand": dict(REF_STAND)}}
        nb = ttk.Notebook(w)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        GROUP_RNG = {"red": (0, 58), "referee": (118, 141), "ball": (142, 145)}

        def gfx():
            return self.gfx

        def err(title, ex):
            messagebox.showerror(title, str(ex), parent=w)

        def safe_ids(text, lo, hi):
            try:
                return parse_ids(text, lo, hi)
            except ValueError:
                return []

        t1 = ttk.Frame(nb)
        nb.add(self._reg_tab(t1, "tab.poses_sets"), text=tr("tab.poses_sets"))
        grp = tk.StringVar(value="red")
        top = ttk.Frame(t1)
        top.pack(fill="x", pady=4)
        self._reg(ttk.Label(top), "de.group").pack(side="left")
        gcb = ttk.Combobox(top, textvariable=grp, values=list(GROUP_RNG), state="readonly", width=10)
        gcb.pack(side="left", padx=4)
        self._reg(ttk.Label(top, foreground="#666"), "de.group_hint").pack(side="left", padx=8)
        body = ttk.Frame(t1)
        body.pack(fill="both", expand=True)
        lb = tk.Listbox(body, width=36, height=16, exportselection=False)
        lb.pack(side="left", fill="y")
        form = ttk.Frame(body)
        form.pack(side="left", fill="both", expand=True, padx=8)
        name_v, ids_v = tk.StringVar(), tk.StringVar()

        def rng():
            return GROUP_RNG[grp.get()]

        self._reg(ttk.Label(form), "de.name").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=name_v, width=44).grid(row=0, column=1, sticky="we", pady=2)
        self._reg(ttk.Label(form), "de.ids").grid(row=1, column=0, sticky="w")
        ttk.Entry(form, textvariable=ids_v, width=44).grid(row=1, column=1, sticky="we", pady=2)
        self._reg(ttk.Label(form, foreground="#666"), "de.ids_hint").grid(row=2, column=1, sticky="w")
        self._reg(ttk.Label(form), "de.sprites").grid(row=3, column=0, sticky="nw", pady=8)
        pv = SpriteStrip(form, gfx, ids_v, rng)
        pv.grid(row=3, column=1, sticky="w", pady=8)
        self._reg(ttk.Label(form, foreground="#666", justify="left"), "de.sprites_hint").grid(row=4, column=1, sticky="w")
        bt = ttk.Frame(form)
        bt.grid(row=5, column=0, columnspan=2, sticky="w", pady=6)

        loading = [False]

        def fill_list(sel=None):
            lb.delete(0, "end")
            for n in pg[grp.get()]:
                lb.insert("end", n)
            if sel is not None and 0 <= sel < lb.size():
                lb.selection_set(sel)
                lb.see(sel)

        def on_sel(_e=None):
            s_ = lb.curselection()
            if s_:
                n = lb.get(s_[0])
                loading[0] = True
                name_v.set(n)
                ids_v.set(ids_text(pg[grp.get()][n]))
                loading[0] = False

        def p_read(exclude=None):
            nm = name_v.get().strip()
            if not nm:
                raise ValueError(tr("de.err_name"))
            if nm != exclude and nm in pg[grp.get()]:
                raise ValueError(tr("de.err_exists", name=nm))
            return nm, parse_ids(ids_v.get(), *rng())

        def p_live(*_):
            s_ = lb.curselection()
            if loading[0] or not s_:
                return
            old = lb.get(s_[0])
            try:
                nm, ids = p_read(exclude=old)
            except ValueError:
                return
            d = pg[grp.get()]
            if nm == old and ids == d[old]:
                return
            items = list(d.items())
            items[s_[0]] = (nm, ids)
            d.clear()
            d.update(items)
            if nm != old:
                lb.delete(s_[0])
                lb.insert(s_[0], nm)
                lb.selection_set(s_[0])

        def p_add():
            d = pg[grp.get()]
            nm, k = tr("de.new_set"), 2
            while nm in d:
                nm, k = tr("de.new_set_n", n=k), k + 1
            d[nm] = [rng()[0]]
            fill_list(len(d) - 1)
            on_sel()

        def p_del():
            s_ = lb.curselection()
            if s_ and messagebox.askyesno(tr("mb.delete"), tr("de.del_confirm", name=lb.get(s_[0])), parent=w):
                del pg[grp.get()][lb.get(s_[0])]
                fill_list(min(s_[0], lb.size() - 2))
                on_sel()
                if not lb.curselection():
                    loading[0] = True
                    name_v.set("")
                    ids_v.set("")
                    loading[0] = False

        def p_move(delta):
            s_ = lb.curselection()
            if not s_:
                return
            d = pg[grp.get()]
            items = list(d.items())
            i, j = s_[0], s_[0] + delta
            if 0 <= j < len(items):
                items[i], items[j] = items[j], items[i]
                d.clear()
                d.update(items)
                fill_list(j)

        for txt, cmd in (("de.add", p_add), ("de.del", p_del), ("de.up", lambda: p_move(-1)), ("de.down", lambda: p_move(1))):
            self._reg(ttk.Button(bt, command=cmd), txt).pack(side="left", padx=2)
        name_v.trace_add("write", p_live)
        ids_v.trace_add("write", p_live)
        lb.bind("<<ListboxSelect>>", on_sel)

        def on_group(_e=None):
            fill_list()
            loading[0] = True
            name_v.set("")
            ids_v.set("")
            loading[0] = False
            pv.refresh()

        gcb.bind("<<ComboboxSelected>>", on_group)
        fill_list()

        t2 = ttk.Frame(nb)
        nb.add(self._reg_tab(t2, "tab.actions"), text=tr("tab.actions"))
        body2 = ttk.Frame(t2)
        body2.pack(fill="both", expand=True, pady=4)
        lb2 = tk.Listbox(body2, width=36, height=16, exportselection=False)
        lb2.pack(side="left", fill="y")
        f2 = ttk.Frame(body2)
        f2.pack(side="left", fill="both", expand=True, padx=8)
        key_v, lab_v, e_v, w_v = tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()
        single_v, travel_v = tk.BooleanVar(), tk.BooleanVar()
        for r, (txt, var) in ((0, ("de.key", key_v)), (1, ("de.label", lab_v)), (2, ("de.seq_e", e_v)), (4, ("de.seq_w", w_v))):
            self._reg(ttk.Label(f2), txt).grid(row=r, column=0, sticky="w")
            ttk.Entry(f2, textvariable=var, width=44).grid(row=r, column=1, sticky="we", pady=2)
        se = SpriteStrip(f2, gfx, e_v, lambda: (0, 58))
        se.grid(row=3, column=1, sticky="w", pady=(0, 6))
        sw = SpriteStrip(f2, gfx, w_v, lambda: (0, 58), locked=single_v.get, auto=lambda: safe_ids(e_v.get(), 0, 58) if single_v.get() else [58 - k for k in safe_ids(e_v.get(), 0, 58)])
        sw.grid(row=5, column=1, sticky="w", pady=(0, 6))
        for v in (e_v, single_v):
            v.trace_add("write", lambda *_: sw.refresh())
        self._reg(ttk.Label(f2, foreground="#666", wraplength=460, justify="left"), "de.act_hint").grid(row=6, column=0, columnspan=2, sticky="w")
        self._reg(ttk.Checkbutton(f2, variable=single_v), "de.single").grid(row=7, column=0, columnspan=2, sticky="w")
        self._reg(ttk.Checkbutton(f2, variable=travel_v), "de.travel").grid(row=8, column=0, columnspan=2, sticky="w")
        bt2 = ttk.Frame(f2)
        bt2.grid(row=9, column=0, columnspan=2, sticky="w", pady=6)

        loading2 = [False]

        def fill2(sel=None):
            lb2.delete(0, "end")
            for k in ad["order"]:
                lb2.insert("end", "%s  (%s)" % (k, ad["actions"][k]["label"]))
            if sel is not None and 0 <= sel < lb2.size():
                lb2.selection_set(sel)
                lb2.see(sel)

        def on_sel2(_e=None):
            s_ = lb2.curselection()
            if s_:
                k = ad["order"][s_[0]]
                a_ = ad["actions"][k]
                loading2[0] = True
                key_v.set(k)
                lab_v.set(a_["label"])
                e_v.set(ids_text(a_["E"]))
                w_v.set(ids_text(a_["W"]))
                single_v.set(bool(a_.get("single")))
                travel_v.set(bool(a_.get("travel")))
                loading2[0] = False
                sw.refresh()

        def a_read(exclude=None):
            key = key_v.get().strip()
            if not re.fullmatch(r"[a-z0-9_]+", key):
                raise ValueError(tr("de.err_key"))
            if key != exclude and key in ad["actions"]:
                raise ValueError(tr("de.err_key_exists", key=key))
            e = parse_ids(e_v.get(), 0, 58)
            if single_v.get():
                wv = list(e)
            elif w_v.get().strip():
                wv = parse_ids(w_v.get(), 0, 58)
            else:
                wv = [58 - k for k in e]
            d = {"label": lab_v.get().strip() or key, "E": e, "W": wv}
            if single_v.get():
                d["single"] = True
            if travel_v.get():
                d["travel"] = True
            return key, d

        def a_live(*_):
            s_ = lb2.curselection()
            if loading2[0] or not s_:
                return
            old = ad["order"][s_[0]]
            try:
                key, d = a_read(exclude=old)
            except ValueError:
                return
            if key == old and d == ad["actions"][old]:
                return
            del ad["actions"][old]
            ad["actions"][key] = d
            ad["order"][s_[0]] = key
            lb2.delete(s_[0])
            lb2.insert(s_[0], "%s  (%s)" % (key, d["label"]))
            lb2.selection_set(s_[0])

        def a_add():
            key, k = "new_action", 2
            while key in ad["actions"]:
                key, k = "new_action_%d" % k, k + 1
            ad["actions"][key] = {"label": tr("de.new_action"), "E": [0], "W": [58]}
            ad["order"].append(key)
            fill2(len(ad["order"]) - 1)
            on_sel2()

        def a_del():
            s_ = lb2.curselection()
            if s_ and messagebox.askyesno(tr("mb.delete"), tr("de.del_action", key=ad["order"][s_[0]]), parent=w):
                del ad["actions"][ad["order"].pop(s_[0])]
                fill2(min(s_[0], lb2.size() - 2))
                on_sel2()

        def a_move(delta):
            s_ = lb2.curselection()
            if s_ and 0 <= s_[0] + delta < len(ad["order"]):
                o, i, j = ad["order"], s_[0], s_[0] + delta
                o[i], o[j] = o[j], o[i]
                fill2(j)

        for txt, cmd in (("de.add", a_add), ("de.del", a_del), ("de.up", lambda: a_move(-1)), ("de.down", lambda: a_move(1))):
            self._reg(ttk.Button(bt2, command=cmd), txt).pack(side="left", padx=2)
        for v in (key_v, lab_v, e_v, w_v, single_v, travel_v):
            v.trace_add("write", a_live)
        lb2.bind("<<ListboxSelect>>", on_sel2)
        fill2()

        t3 = ttk.Frame(nb)
        nb.add(self._reg_tab(t3, "tab.anim"), text=tr("tab.anim"))
        mtop = ttk.Frame(t3)
        mtop.pack(fill="x", pady=4)
        self._reg(ttk.Label(mtop), "de.group").pack(side="left")
        mgrp = tk.StringVar(value="red")
        mcb = ttk.Combobox(mtop, textvariable=mgrp, values=list(GROUP_RNG), state="readonly", width=10)
        mcb.pack(side="left", padx=4)
        mhint = ttk.Label(mtop, foreground="#666")
        mhint.pack(side="left", padx=8)
        self._reg(ttk.Label(t3, foreground="#666", wraplength=620, justify="left"), "de.anim_info").pack(anchor="w", pady=(0, 4))
        mrows = ttk.Frame(t3)
        mrows.pack(fill="both", expand=True)
        mv = []

        GRID = {"NW": (0, 0), "N": (0, 1), "NE": (0, 2), "W": (1, 0), "E": (1, 2), "SW": (2, 0), "S": (2, 1), "SE": (2, 2)}

        def parse_opt(text, lo, hi):
            return parse_ids(text, lo, hi) if text.strip() else []

        built = [None]

        def live(fn):
            def cb(*_a):
                try:
                    fn()
                except ValueError:
                    pass
            return cb

        def build_move_rows(*_):
            g = mgrp.get()
            built[0] = g
            mrows.pack_forget()
            for wd in mrows.winfo_children():
                wd.destroy()
            mv.clear()
            lo, hi = GROUP_RNG[g]
            mhint.config(text=tr({"red": "de.hint_red", "referee": "de.hint_ref", "ball": "de.hint_ball"}[g]))
            big = ("TkDefaultFont", 14, "bold")
            if g == "ball":
                var = tk.StringVar(value=ids_text(pg["ball"].get("rotation", [])))
                self._reg(ttk.Label(mrows, font=big, foreground="#b4b4b4", anchor="center"), "de.rotation").grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
                SpriteStrip(mrows, gfx, var, lambda: (lo, hi), per_row=6, zoom=3).grid(row=1, column=0, padx=6, pady=(0, 6))

                def ap(var=var):
                    pg["ball"]["rotation"] = parse_ids(var.get(), lo, hi)
                var.trace_add("write", live(ap))
                mv.append((tr("de.rot_cycle"), ap))
            else:
                moves = ad["moves"] if g == "red" else ad["referee"]["move"]
                stand = ad["stand"] if g == "red" else ad["referee"]["stand"]
                for d in DIRS:
                    r, c = GRID[d]
                    cyc = list(moves.get(d, []))
                    idle0 = stand[d] if d in stand else (cyc[0] if cyc else lo)
                    bx = ttk.Frame(mrows, borderwidth=1, relief="groove", padding=3)
                    bx.grid(row=r, column=c, padx=4, pady=4, sticky="n")
                    ttk.Label(bx, text=tr(DIR_LABEL[d]), font=big, foreground="#b4b4b4", anchor="center").grid(row=0, column=0, columnspan=2, sticky="ew")
                    iv, rv = tk.StringVar(value=str(idle0)), tk.StringVar(value=ids_text(cyc[1:]))
                    SpriteStrip(bx, gfx, iv, lambda: (lo, hi), max_n=1, per_row=1, zoom=3).grid(row=1, column=0, sticky="n", padx=(0, 6))
                    SpriteStrip(bx, gfx, rv, lambda: (lo, hi), per_row=4, zoom=3).grid(row=1, column=1, sticky="n")

                    def ap(d=d, iv=iv, rv=rv):
                        idle = parse_ids(iv.get(), lo, hi)
                        if len(idle) != 1:
                            raise ValueError(tr("de.err_idle"))
                        moves[d] = idle + parse_opt(rv.get(), lo, hi)
                        stand[d] = idle[0]
                    iv.trace_add("write", live(ap))
                    rv.trace_add("write", live(ap))
                    mv.append(("%s (%s)" % (d, tr(DIR_LABEL[d])), ap))
                self._reg(ttk.Label(mrows, foreground="#aaa", justify="center"), "de.idle_hint").grid(row=1, column=1)
            mrows.pack(fill="both", expand=True)

        def on_tab(_e=None):
            cur = nb.select()
            if cur == str(t3):
                if built[0] != mgrp.get():
                    build_move_rows()
            elif cur == str(t1):
                on_sel()
            elif cur == str(t2):
                on_sel2()

        mcb.bind("<<ComboboxSelected>>", build_move_rows)
        nb.bind("<<NotebookTabChanged>>", on_tab)

        def check_selected():
            s_ = lb.curselection()
            if s_:
                try:
                    p_read(exclude=lb.get(s_[0]))
                except ValueError as ex:
                    return tr("de.pose_err", name=lb.get(s_[0]), err=ex)
            s_ = lb2.curselection()
            if s_:
                try:
                    a_read(exclude=ad["order"][s_[0]])
                except ValueError as ex:
                    return tr("de.action_err", key=ad["order"][s_[0]], err=ex)
            return None

        def apply_all():
            msg = check_selected()
            if msg:
                return err(tr("de.invalid"), msg + tr("de.fix"))
            for name, fn in mv:
                try:
                    fn()
                except ValueError as ex:
                    return err(tr("tab.anim"), "%s: %s" % (name, ex))
            ad2 = dict(ad, actions={k: ad["actions"][k] for k in ad["order"]})
            try:
                save_data_files(pg, ad2)
            except OSError as ex:
                return err(tr("save"), ex)
            load_data()
            w.destroy()
            self.after_data_change()
            self.note(tr("de.saved", a=os.path.basename(POSES_FILE), b=os.path.basename(ACTIONS_FILE)))

        def snapshot():
            return json.dumps([pg, ad], sort_keys=True)

        base_state = snapshot()

        def on_close():
            if snapshot() != base_state:
                ans = messagebox.askyesnocancel(tr("mb.unsaved"), tr("de.unsaved"), parent=w)
                if ans is None:
                    return
                if ans:
                    return apply_all()
            w.destroy()

        w.protocol("WM_DELETE_WINDOW", on_close)
        bar = ttk.Frame(w)
        bar.pack(fill="x", padx=6, pady=(0, 6))
        self._reg(ttk.Label(bar, foreground="#666"), "de.footer").pack(side="left")
        self._reg(ttk.Button(bar, command=on_close), "close").pack(side="right")
        self._reg(ttk.Button(bar, command=apply_all), "de.save").pack(side="right", padx=4)


def run_gui(path=None):
    root = tk.Tk()
    root.title("TORE Editor")
    panel = ToreEditorPanel(root, standalone=True, path=path)
    panel.pack(fill=tk.BOTH, expand=True)
    root.mainloop()


if __name__ == "__main__":
    run_gui(sys.argv[1] if len(sys.argv) > 1 else None)
