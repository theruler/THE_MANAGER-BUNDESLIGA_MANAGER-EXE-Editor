import copy
import json
import math
import os
import re
import shutil
import struct
import sys
import time

from PIL import Image, ImageDraw

FRAME_SIZE = 164
N_RECORDS = 27
CELL_W, CELL_H = 12, 11
SHEET_COLS = 24
Y_OFFSET = 35
WIN_W, WIN_H = 182, 96
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


def find_pic_dir(te_path):
    game_dir = os.path.dirname(os.path.dirname(os.path.abspath(te_path)))
    if os.path.isdir(game_dir):
        for name in os.listdir(game_dir):
            p = os.path.join(game_dir, name)
            if name.lower() == "pic" and os.path.isdir(p):
                return p
    return None


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
SOUNDS = [("Goal celebration", "#2e9e3e"), ("Referee whistle", "#d4b000"), ("Disapproval whistles", "#e07020"), ("Missed-goal disappointment", "#3a5bd0")]
KINDS = {"T": "Goal (scored)", "V": "Missed chance"}
VARIANTS = {"": "Normal", "E": "Penalty", "J": "Jux"} 
GHOST_OPTS = ["None", "Selected: previous frame", "Selected: all previous frames", "All sprites: all previous frames"]

def _mir(seq):
    return [58 - k for k in seq]

DIRS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"]
DIR_LABEL = {"E": "East", "NE": "North-East", "N": "North", "NW": "North-West",
             "W": "West", "SW": "South-West", "S": "South", "SE": "South-East"}
MOVE_E = {
    "E": [3, 4, 5], "SE": [6, 7, 8], "NE": [0, 1, 2],
    "W": [53, 54, 55], "SW": [50, 51, 52], "NW": [56, 57, 58],
    "N": [28, 29, 30], "S": [31, 32, 33],
}
STAND_K = {"E": 0, "W": 58}
ACTION_ORDER = ["dive", "header", "bicycle", "fall", "getup"]
ACTIONS = {
    "dive":    {"label": "Dive (tuffo)",
                "E": [12, 13, 14, 14, 14, 14, 13], "W": [46, 45, 44, 44, 44, 44, 45]},
    "header":  {"label": "Header (colpo di testa)",
                "E": [11, 11], "W": [47, 47]},
    "bicycle": {"label": "Bicycle kick (rovesciata)",
                "E": [11, 10, 23, 24, 24, 24], "W": [47, 48, 35, 34, 34, 34]},
    "fall":    {"label": "Collision fall (scontro + caduta)",
                "E": [22, 23, 24, 24, 24], "W": [36, 35, 34, 34, 34]},
    "getup":   {"label": "Get up",
                "E": [14, 13], "W": [44, 45]},
}
REF_MOVE = {"E": [121, 122, 123], "W": [135, 136]}
REF_STAND = 126
UNKNOWN_K = [("Other / unknown (?) 21,37", [21, 37]),
             ("Facing camera (?) 25", [25]),
             ("Arms up / celebration (?) 26,27", [26, 27]),
             ("Unknown run type A (?) 15-20", list(range(15, 21))),
             ("Unknown run type B (?) 38-43", list(range(38, 44)))]
_ov_act = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tore_actions.json")
if os.path.isfile(_ov_act):
    try:
        _j = json.load(open(_ov_act, encoding="utf-8"))
        ACTIONS.update(_j.get("actions", {}))
        MOVE_E.update(_j.get("moves", {}))
    except (OSError, ValueError):
        pass


def _uniq(seq):
    out = []
    for v in seq:
        if v not in out:
            out.append(v)
    return out


def _build_player_cats():
    c = [("Stand - facing E", [STAND_K["E"]]), ("Stand - facing W", [STAND_K["W"]])]
    for d in DIRS:
        c.append(("Run %s (%s)" % (d, DIR_LABEL[d]), list(MOVE_E[d])))
    c.append(("Run E - long cycle", list(range(3, 10))))
    c.append(("Run W - long cycle", list(range(49, 56))))
    for key in ACTION_ORDER:
        a = ACTIONS[key]
        for side in "EW":
            c.append(("%s -> %s" % (a["label"], side), _uniq(a[side])))
    c += UNKNOWN_K
    return c


PLAYER_CATS = _build_player_cats()
REF_CATS = [("Referee walk E", REF_MOVE["E"]), ("Referee walk W (A)", REF_MOVE["W"]),
            ("Referee walk W (B) 132-134", [132, 133, 134]), ("Referee standing", [REF_STAND]),
            ("Referee - side A (all)", list(range(118, 129))), ("Referee - side B (all)", list(range(129, 142)))]
BALL_ROT = [142, 143, 144]
BALL_CATS = [("Ball (rotation)", BALL_ROT)]
_ov = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tore_poses.json")
if os.path.isfile(_ov):
    try:
        PLAYER_CATS = [(k, list(v)) for k, v in json.load(open(_ov, encoding="utf-8")).items()]
    except (OSError, ValueError):
        pass


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


def team_off(sid):
    t = team_of(sid)
    return 0 if t == "R" else 59 if t == "B" else None


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
        return [off + k for k in MOVE_E[d]]
    if t == "A":
        return list(REF_MOVE["W" if "W" in d else "E"])
    return list(BALL_ROT) if cls(sid) == "B" else None


def stand_id(sid, face):
    t = team_of(sid)
    if t in ("R", "B"):
        return (0 if t == "R" else 59) + STAND_K[face]
    if t == "A":
        return REF_STAND
    return sid


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


def full_pose_sets():
    out = {}
    for colour, off in (("red", 0), ("blue", 59)):
        out[colour] = {n: [k + off for k in ks] for n, ks in PLAYER_CATS}
    out["referee"] = {n: list(ks) for n, ks in REF_CATS}
    out["ball"] = {"rotation": list(BALL_ROT), "shadow": [145]}
    out["goals"] = {"left": [1000], "right": [1024]}
    return out


def poly_len(p):
    return sum(math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]) for i in range(1, len(p)))


def rdp(pts, eps): # Ramer-Douglas-Peucker simplification.
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


def catmull(pts, seg=10): # Catmull-Rom spline
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


class Scene:
    def __init__(self):
        self.sig = SIGNATURES[1]
        self.events = [None] * 4
        self.author = ""
        self.frames = []
        self.path = None

    @staticmethod
    def new():
        s = Scene()
        s.frames = [Frame((110, 0), [])]
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
        s.events = [None if b == 255 else b for b in d[12:16]]
        prev = prev2 = None
        for i in range(n):
            w = struct.unpack("<82H", d[17 + i * FRAME_SIZE:17 + (i + 1) * FRAME_SIZE])
            scroll = (w[0] & 255, w[0] >> 8)
            recs = [list(w[1 + 3 * k:4 + 3 * k]) for k in range(N_RECORDS)]
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
                g[0] = max(0, FW - CELL_W - x)
        elif c in "SB":
            if flip:
                g[0] = max(0, FW - 4 - x)
        elif flip:
            g[2] = 1024 if sid == 1000 else 1000
    if flip:
        b = f.index_of("B")
        for g in f.figs:
            if cls(g[2]) in "LR" and b is not None:
                g[0] = f.figs[b][0]
        f.scroll[0] = max(0, FW - WIN_W - f.scroll[0])


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
    cand.append(os.path.dirname(os.path.abspath(__file__)))
    for d in cand:
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


def sprite_w(sid):
    return 4 if sid >= 142 else CELL_W


LEADER_RULES = ("North", "South", "West", "East")


def run_gui(path=None):
    import tkinter as tk
    from tkinter import filedialog, messagebox, simpledialog, ttk
    from PIL import ImageTk

    class Editor(tk.Tk):
        def __init__(self):
            super().__init__()
            self.scene = Scene.new()
            self.gfx = Graphics(None)
            self.pic_dir = None
            self.idx, self.sel = 0, None
            self.multi = set()
            self.playing = False
            self.undo_s, self.redo_s = [], []
            self.modified = False
            self.drag = None
            self.stroke = None
            self.way = []
            self.cursor_pos = None
            self._photo = None
            self._thumbs = []
            self.pal = None
            self.scope = tk.StringVar(value="frame")
            self.lock_ball = tk.BooleanVar(value=True)
            self.show_win = tk.BooleanVar(value=True)
            self.show_path = tk.BooleanVar(value=True)
            self.show_ids = tk.BooleanVar(value=False)
            self.follow = tk.BooleanVar(value=True)
            self.ghost = tk.StringVar(value=GHOST_OPTS[0])
            self.loop = tk.BooleanVar(value=True)
            self.fps = tk.IntVar(value=12)
            self.zoom = tk.IntVar(value=3 if self.winfo_screenwidth() >= 1600 else 2)
            self.speed = tk.DoubleVar(value=3.0)
            self.sx, self.sy = tk.IntVar(), tk.IntVar()
            self.cat_var = tk.StringVar()
            self.snd_var = tk.IntVar(value=-1)
            self.tool = tk.StringVar(value="select")
            self.pmode = tk.StringVar(value="speed")
            self.pframes = tk.IntVar(value=20)
            self.smooth = tk.BooleanVar(value=True)
            self.auto_spr = tk.BooleanVar(value=True)
            self.diag = tk.BooleanVar(value=True)
            self.rope = tk.DoubleVar(value=5.0)
            self.pin = tk.BooleanVar(value=True)
            self.resume = tk.BooleanVar(value=True)
            self.cam_ball = tk.BooleanVar(value=False)
            self.ball_off = [0, 0]
            self.leader_rule = tk.StringVar(value=LEADER_RULES[0])
            self._t_pan = 0.0
            self.title("TORE Editor")
            self._menus()
            self._layout()
            self._keys()
            self.protocol("WM_DELETE_WINDOW", self.quit_app)
            self.load_gfx(path)
            if path:
                self.open_path(path)
            else:
                self.refresh()


        def _menus(self):
            m = tk.Menu(self)
            f = tk.Menu(m, tearoff=0)
            for lbl, cmd, acc in (("New scene", self.new_scene, "Ctrl+N"), ("Open...", self.open_dialog, "Ctrl+O"),
                                  ("Save", self.save, "Ctrl+S"), ("Save As...", self.save_as, "Ctrl+Shift+S"),
                                  ("Save as numbered scene (update ANZAHL)...", self.save_numbered, ""),
                                  (None, None, None), ("Export pose sets (JSON)...", self.export_sets, ""),
                                  ("PIC folder...", self.choose_pic, ""), ("Delete file...", self.delete_file, ""),
                                  (None, None, None), ("Exit", self.quit_app, "")):
                self._add(f, lbl, cmd, acc)
            m.add_cascade(label="File", menu=f)

            e = tk.Menu(m, tearoff=0)
            for lbl, cmd, acc in (("Undo", self.undo, "Ctrl+Z"), ("Redo", self.redo, "Ctrl+Y"), (None, None, None),
                                  ("Select all players", self.select_all, "Ctrl+A"), (None, None, None),
                                  ("Insert frame (copy)", self.ins_frame, "Ins"),
                                  ("Delete current frame", self.del_frame, "Del"),
                                  ("Delete entire film...", self.clear_film, ""), (None, None, None),
                                  ("Mirror scene (field side + team colors)", lambda: self.mirror(True, True), ""),
                                  ("Swap team colors only", lambda: self.mirror(False, True), ""),
                                  (None, None, None), ("Scene properties...", self.props, "")):
                self._add(e, lbl, cmd, acc)
            m.add_cascade(label="Edit", menu=e)

            fg = tk.Menu(m, tearoff=0)
            fg.add_cascade(label="Action here", menu=self._action_menu(fg))
            fg.add_cascade(label="Run (sprites only, to end of film)", menu=self._run_menu(fg))
            for lbl, cmd in (("Auto-sprites along trajectory (from this frame)", self.auto_here),
                             ("Auto-sprites along trajectory (whole film)", lambda: self.auto_here(True)),
                             (None, None), ("Mirror pose (E <-> W)", self.mirror_sel),
                             ("Lock pose (clear animation from here)", self.clear_anim),
                             ("Program pose sequence...", self.program_anim)):
                self._add(fg, lbl, cmd, "")
            m.add_cascade(label="Figure", menu=fg)

            p = tk.Menu(m, tearoff=0)
            for lbl, cmd, acc in (("Draw path (freehand)", lambda: self.tool.set("draw") or self.set_tool(), "D"),
                                  ("Click path (waypoints)", lambda: self.tool.set("way") or self.set_tool(), "P"),
                                  (None, None, None),
                                  ("Smooth trajectory (from this frame)", self.smooth_path, ""),
                                  ("Even speed (from this frame)", self.even_speed, ""),
                                  ("Freeze here (stop figure)", self.freeze_here, ""),
                                  ("Interpolate position to frame...", self.tween, ""),
                                  (None, None, None),
                                  ("Camera follows ball/figure (from this frame)", self.auto_camera, ""),
                                  ("Camera follows ball/figure (whole film)", lambda: self.auto_camera(True), ""),
                                  ("Interpolate scroll to frame...", self.tween_scroll, ""),
                                  ("Continue current scroll to end of film", self.scroll_to_end, "")):
                self._add(p, lbl, cmd, acc)
            p.add_separator()
            p.add_checkbutton(label="Window locked to ball", variable=self.cam_ball, command=self.toggle_cam_ball)
            m.add_cascade(label="Path / Camera", menu=p)

            v = tk.Menu(m, tearoff=0)
            v.add_checkbutton(label="Show trajectory", variable=self.show_path, command=self.refresh)
            v.add_checkbutton(label="Show visible window (182x96)", variable=self.show_win, command=self.refresh)
            v.add_checkbutton(label="Show sprite ids", variable=self.show_ids, command=self.refresh)
            v.add_separator()
            v.add_command(label="Zoom in", command=lambda: self.set_zoom(1), accelerator="Ctrl++")
            v.add_command(label="Zoom out", command=lambda: self.set_zoom(-1), accelerator="Ctrl+-")
            m.add_cascade(label="View", menu=v)

            h = tk.Menu(m, tearoff=0)
            h.add_command(label="Quick help", command=self.help)
            m.add_cascade(label="?", menu=h)
            self.config(menu=m)


        @staticmethod
        def _add(menu, lbl, cmd, acc):
            if lbl is None:
                menu.add_separator()
            else:
                menu.add_command(label=lbl, command=cmd, accelerator=acc)

        def _layout(self):
            z = self.z()
            t1 = ttk.Frame(self)
            t1.pack(fill="x", padx=8, pady=(6, 0))
            ttk.Label(t1, text="Changes apply to:").pack(side="left")
            ttk.Radiobutton(t1, text="this frame", value="frame", variable=self.scope).pack(side="left", padx=4)
            ttk.Radiobutton(t1, text="this + following frames", value="end", variable=self.scope).pack(side="left")
            ttk.Separator(t1, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Checkbutton(t1, text="ball + shadow together", variable=self.lock_ball).pack(side="left")
            ttk.Separator(t1, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Label(t1, text="Ghosts:").pack(side="left")
            cb = ttk.Combobox(t1, textvariable=self.ghost, values=GHOST_OPTS, state="readonly", width=30)
            cb.pack(side="left", padx=4)
            cb.bind("<<ComboboxSelected>>", lambda e: self.refresh())
            ttk.Checkbutton(t1, text="trajectory", variable=self.show_path, command=self.refresh).pack(side="left", padx=4)
            ttk.Checkbutton(t1, text="window", variable=self.show_win, command=self.refresh).pack(side="left")
            ttk.Checkbutton(t1, text="ids", variable=self.show_ids, command=self.refresh).pack(side="left", padx=4)
            ttk.Label(t1, text=" Scroll X").pack(side="left")
            ttk.Spinbox(t1, from_=0, to=FW - WIN_W, width=4, textvariable=self.sx, command=self.set_scroll).pack(side="left")
            ttk.Label(t1, text="Y").pack(side="left")
            ttk.Spinbox(t1, from_=0, to=FH - WIN_H, width=3, textvariable=self.sy, command=self.set_scroll).pack(side="left")

            t2 = ttk.LabelFrame(self, text="Path & animation")
            t2.pack(fill="x", padx=8, pady=(4, 0))
            ttk.Radiobutton(t2, text="speed", value="speed", variable=self.pmode).pack(side="left", padx=(6, 0))
            ttk.Spinbox(t2, from_=0.5, to=40, increment=0.5, width=5, textvariable=self.speed).pack(side="left", padx=2)
            ttk.Label(t2, text="px/frame").pack(side="left")
            ttk.Radiobutton(t2, text="duration", value="frames", variable=self.pmode).pack(side="left", padx=(10, 0))
            ttk.Spinbox(t2, from_=1, to=MAX_FRAMES, width=4, textvariable=self.pframes).pack(side="left", padx=2)
            ttk.Label(t2, text="frames").pack(side="left")
            ttk.Radiobutton(t2, text="as drawn (real timing)", value="timing", variable=self.pmode).pack(side="left", padx=10)
            ttk.Separator(t2, orient="vertical").pack(side="left", fill="y", padx=6)
            ttk.Checkbutton(t2, text="smooth curves", variable=self.smooth).pack(side="left")
            ttk.Checkbutton(t2, text="auto run sprites", variable=self.auto_spr).pack(side="left", padx=4)
            ttk.Checkbutton(t2, text="diagonal sprites", variable=self.diag).pack(side="left")
            ttk.Checkbutton(t2, text="later frames follow", variable=self.follow).pack(side="left", padx=4)
            ttk.Separator(t2, orient="vertical").pack(side="left", fill="y", padx=6)
            ttk.Label(t2, text="Rope softness").pack(side="left")
            ttk.Spinbox(t2, from_=0.5, to=40, increment=0.5, width=4, textvariable=self.rope).pack(side="left", padx=2)
            ttk.Checkbutton(t2, text="pin current frame", variable=self.pin).pack(side="left", padx=4)
            t3 = ttk.Frame(self)
            t3.pack(fill="x", padx=8, pady=(4, 0))
            ttk.Checkbutton(t3, text="window locked to ball", variable=self.cam_ball, command=self.toggle_cam_ball).pack(side="left")
            ttk.Separator(t3, orient="vertical").pack(side="left", fill="y", padx=8)
            ttk.Label(t3, text="Box-select leader:").pack(side="left")
            lc = ttk.Combobox(t3, textvariable=self.leader_rule, values=LEADER_RULES, state="readonly", width=7)
            lc.pack(side="left", padx=4)
            lc.bind("<<ComboboxSelected>>", lambda e: self.regroup_leader())
            ttk.Label(t3, text="(or click / right-click a selected figure to make it the leader)",foreground="#555").pack(side="left", padx=4)
            body = ttk.Frame(self)
            body.pack(fill="both", expand=True, padx=8, pady=6)
            tools = ttk.Frame(body)
            tools.pack(side="left", fill="y", padx=(0, 6))
            for key, txt in (("select", "Select move (V)"), ("draw", "Draw path (D)"), ("way", "Click path (P)"), ("pan", "Pan window (H)")):
                ttk.Radiobutton(tools, text=txt, value=key, variable=self.tool, style="Toolbutton", command=self.set_tool, width=14).pack(fill="x", pady=2)
            left = ttk.Frame(body)
            left.pack(side="left", fill="both", expand=True)
            self.canvas = tk.Canvas(left, bg="black", highlightthickness=0, width=FW * z, height=FH * z, cursor="arrow")
            self.canvas.pack()
            bar = ttk.Frame(left)
            bar.pack(fill="x", pady=(6, 0))
            for t, c, w in (("|<", lambda: self.goto(0), 3), ("<", lambda: self.step(-1), 3)):
                ttk.Button(bar, text=t, width=w, command=c).pack(side="left")
            self.btn = ttk.Button(bar, text="Play all", width=9, command=lambda: self.toggle(0))
            self.btn.pack(side="left")
            ttk.Button(bar, text="Play from here", width=13, command=lambda: self.toggle(self.idx)).pack(side="left")
            for t, c, w in ((">", lambda: self.step(1), 3), (">|", lambda: self.goto(len(self.scene.frames) - 1), 3)):
                ttk.Button(bar, text=t, width=w, command=c).pack(side="left")
            ttk.Button(bar, text="+ Frame", command=self.ins_frame).pack(side="left", padx=(12, 0))
            ttk.Button(bar, text="- Frame", command=self.del_frame).pack(side="left")
            ttk.Checkbutton(bar, text="Loop", variable=self.loop).pack(side="left", padx=8)
            ttk.Label(bar, text="fps").pack(side="left")
            ttk.Spinbox(bar, from_=1, to=60, width=4, textvariable=self.fps).pack(side="left", padx=(2, 8))
            ttk.Label(bar, text="zoom").pack(side="left")
            ttk.Spinbox(bar, from_=1, to=6, width=3, textvariable=self.zoom, command=self.rezoom).pack(side="left", padx=2)
            self.tl = tk.Canvas(left, height=58, bg="#f2f2f2", highlightthickness=1, highlightbackground="#bbb")
            self.tl.pack(fill="x", pady=(6, 0))
            self.tl.bind("<Button-1>", self.on_tl)
            self.tl.bind("<B1-Motion>", self.on_tl)
            for b in ("<Button-3>", "<Button-2>"):
                self.tl.bind(b, self.on_tl_right)
            self.tl.bind("<Configure>", lambda e: self.draw_timeline())
            ttk.Label(left, text="Timeline: green = running, grey = standing, orange = special action (selected figure)", foreground="#777").pack(anchor="w")
            right = ttk.Frame(body)
            right.pack(side="right", fill="y", padx=(8, 0))
            hdr = ttk.Frame(right)
            hdr.pack(fill="x")
            ttk.Label(hdr, text="Figures (Ctrl+click = multi-select)").pack(side="left")
            ttk.Button(hdr, text="Sprite sheet", command=self.open_palette).pack(side="right")
            tf = ttk.Frame(right)
            tf.pack(fill="x")
            self.tree = ttk.Treeview(tf, columns=("x", "y", "pose"), height=8, selectmode="browse")
            self.tree.heading("#0", text="Figure")
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
            nb.add(pf, text="Poses")
            self.cat_cb = ttk.Combobox(pf, textvariable=self.cat_var, state="readonly", width=34)
            self.cat_cb.pack(padx=4, pady=4)
            self.cat_cb.bind("<<ComboboxSelected>>", lambda e: self.draw_poses())
            self.pose_cv = tk.Canvas(pf, width=5 * 44, height=150, highlightthickness=0)
            self.pose_cv.pack(padx=4)
            self.pose_cv.bind("<Button-1>", self.on_pose_click)
            self.pose_info = ttk.Label(pf, text="", foreground="#555")
            self.pose_info.pack(anchor="w", padx=4, pady=(2, 4))

            af = ttk.Frame(nb)
            nb.add(af, text="Actions")
            ttk.Label(af, text="Applied at the current frame to the\nselected player (team colour is automatic).",
                      foreground="#555").pack(anchor="w", padx=6, pady=(4, 2))
            grid = ttk.Frame(af)
            grid.pack(fill="x", padx=6)
            for r, key in enumerate(ACTION_ORDER):
                ttk.Label(grid, text=ACTIONS[key]["label"], width=30).grid(row=r, column=0, sticky="w", pady=1)
                ttk.Button(grid, text="< W", width=4, command=lambda k=key: self.do_action(k, "W")).grid(row=r, column=1, padx=1)
                ttk.Button(grid, text="E >", width=4, command=lambda k=key: self.do_action(k, "E")).grid(row=r, column=2, padx=1)
            ttk.Checkbutton(af, text="then resume running automatically", variable=self.resume).pack(anchor="w", padx=6, pady=(4, 2))
            ttk.Label(af, text="Run direction (sprites, until end of film):", foreground="#555").pack(anchor="w", padx=6)
            cp = ttk.Frame(af)
            cp.pack(pady=4)
            for r, row in enumerate((("NW", "N", "NE"), ("W", None, "E"), ("SW", "S", "SE"))):
                for c, d in enumerate(row):
                    if d is None:
                        ttk.Button(cp, text="stand", width=6, command=self.do_stand).grid(row=r, column=c, padx=1, pady=1)
                    else:
                        ttk.Button(cp, text=d, width=6, command=lambda d=d: self.do_cycle(d)).grid(row=r, column=c, padx=1, pady=1)

            sf = ttk.Frame(nb)
            nb.add(sf, text="Sound")
            ttk.Radiobutton(sf, text="none", value=-1, variable=self.snd_var, command=self.set_sound).pack(anchor="w", padx=4)
            for k, (nm, col) in enumerate(SOUNDS):
                r = tk.Frame(sf)
                r.pack(fill="x", padx=4)
                tk.Label(r, bg=col, width=1).pack(side="left", padx=(0, 4))
                ttk.Radiobutton(r, text=nm, value=k, variable=self.snd_var, command=self.set_sound).pack(side="left")

            self.status = ttk.Label(self, anchor="w", relief="sunken")
            self.status.pack(fill="x", side="bottom")
            self.set_tool()


        def _keys(self):
            c = self.canvas
            c.bind("<ButtonPress-1>", self.on_press)
            c.bind("<B1-Motion>", self.on_motion)
            c.bind("<ButtonRelease-1>", self.on_release)
            c.bind("<Double-Button-1>", self.on_dbl)
            c.bind("<Motion>", self.on_hover)
            c.bind("<Leave>", lambda e: c.delete("hover"))
            for b in ("<Button-3>", "<Button-2>", "<Control-Button-1>"):
                c.bind(b, self.on_right)
            c.bind("<MouseWheel>", lambda e: self.step(-1 if e.delta > 0 else 1))
            c.bind("<Button-4>", lambda e: self.step(-1))
            c.bind("<Button-5>", lambda e: self.step(1))

            def tool_key(t):
                def f(e):
                    if isinstance(e.widget, (tk.Entry, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
                        return
                    self.tool.set(t)
                    self.set_tool()
                return f
            for k, fn in ((("<space>"), lambda e: self.toggle(0)), ("<Left>", lambda e: self.nudge(-1, 0, e)),
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
                self.bind(k, fn)


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
            if c in "SB" and self.lock_ball.get():
                return self.fr.index_of("B" if c == "S" else "S")
            return None

        def move_fig(self, sl, dx, dy, only_self=False):
            if cls(self.fr.figs[sl][2]) in "LR":
                return
            ids = {sl}
            if not only_self:
                if sl in self.multi:
                    ids |= self.multi
                for s in list(ids):
                    p = self.partner(s)
                    if p is not None:
                        ids.add(p)
            ids = {s for s in ids if cls(self.fr.figs[s][2]) not in "LR"}
            for i in self.frames_in_scope():
                f = self.scene.frames[i]
                for s in ids:
                    g = f.figs[s]
                    g[0] = max(0, min(FW - 1, g[0] + dx))
                    g[1] = max(0, min(MAX_Y, g[1] + dy))
                f.touch()


        def set_pose_to(self, sl, pid):
            pid = max(0, min(145, pid))
            for i in self.frames_in_scope():
                self.scene.frames[i].figs[sl][2] = pid
                self.scene.frames[i].touch()

        def nudge(self, dx, dy, e):
            if self.focus_get() not in (self, self.canvas) or self.sel is None:
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
                    self.set_pose_to(self.sel, ids[(ids.index(cur) + d) % len(ids)])
                    return self.refresh()

        def hit(self, px, py):
            for sl in reversed(self.fr.order):
                x, y, sid = self.fr.figs[sl]
                if sid >= 1000:
                    continue
                w = sprite_w(sid)
                pad = 3 if w == 4 else 0
                if x - pad <= px < x + w + pad and y + Y_OFFSET - pad <= py < y + Y_OFFSET + CELL_H + pad:
                    return sl
            return None

        def on_hover(self, e):
            z = self.z()
            px, py = e.x // z, e.y // z
            c = self.canvas
            c.delete("hover")
            t = self.tool.get()
            self.cursor_pos = (e.x / z, e.y / z)
            if t == "way" and self.way:
                self.draw_overlay()
            sl = self.hit(px, py)
            k = self.path_hit(e.x, e.y) if (t == "select" and sl is None) else None
            if sl is not None:
                x, y, sid = self.fr.figs[sl]
                c.create_rectangle(x * z, (y + Y_OFFSET) * z, (x + sprite_w(sid)) * z, (y + Y_OFFSET + CELL_H) * z,
                                   outline="white", dash=(2, 2), tags="hover")
                self.note("x=%d  y(sprite)=%d  sprite=%d  |  frame %d/%d" % (px, py - Y_OFFSET, sid, self.idx + 1, len(self.scene.frames)))
            elif k is not None:
                cx, cy = self.ctr(self.scene.frames[k].figs[self.sel])
                c.create_oval(cx - 6, cy - 6, cx + 6, cy + 6, outline="#ff9800", width=2, tags="hover")
                self.note("Trajectory frame %d - drag to pull the path like a rope (Shift = move only this point, "
                          "softness in the top bar)" % (k + 1))
            else:
                self.note("x=%d  y(sprite)=%d  |  frame %d/%d  |  %s" % (px, py - Y_OFFSET, self.idx + 1, len(self.scene.frames), self.hint))


        def on_press(self, e):
            self.canvas.focus_set()
            z = self.z()
            px, py = e.x / z, e.y / z
            t = self.tool.get()
            ctrl = bool(e.state & 4)
            if t == "pan":
                self.drag = dict(kind="win", x0=e.x, y0=e.y, a=tuple(self.fr.scroll), off=tuple(self.ball_off),
                                 snapped=False, moved=False, live=False, pos=None)
                return
            sl = self.hit(int(px), int(py))
            if t == "draw":
                if sl is not None and sl != self.sel:
                    self.select(sl)
                if self.sel is None or cls(self.fr.figs[self.sel][2]) in "LR":
                    return self.note("Press on a figure to draw its path (or select it first).")
                g = self.fr.figs[self.sel]
                now = time.time()
                self.stroke = dict(pts=[(float(g[0]), float(g[1]))], t0=now, samples=[(0.0, float(g[0]), float(g[1]))], sid=g[2])
                self.drag = dict(kind="stroke")
                return
            if t == "way":
                if sl is not None and self.sel is None:
                    return self.select(sl)
                if self.sel is None:
                    return self.note("Select a figure first, then click the path points.")
                sid = self.fr.figs[self.sel][2]
                x, y = self.ptr_pos(e.x, e.y, sid)
                x = max(0.0, min(FW - 1.0, x))
                y = max(0.0, min(float(MAX_Y), y))
                self.way.append((x, y))
                self.draw_overlay()
                return
            kk = self.path_hit(e.x, e.y, 5.0)
            if kk is not None and kk != self.idx and sl not in self.multi and not ctrl:
                return self.start_rope(kk, e) 
            if sl is not None:
                if ctrl:
                    self.select(sl, add=True)
                    return
                if sl not in self.multi:
                    self.select(sl)
                self.drag = dict(kind="fig", sl=sl, x0=e.x, y0=e.y, done=(0, 0), snapped=False)
                return
            k = self.path_hit(e.x, e.y)
            if k is not None:
                return self.start_rope(k, e)
            if self.near_window_edge(px, py):
                self.drag = dict(kind="win", x0=e.x, y0=e.y, a=tuple(self.fr.scroll), off=tuple(self.ball_off),
                                 snapped=False, moved=False, live=False, pos=None)
            else:
                self.drag = dict(kind="band", x0=e.x, y0=e.y, x1=e.x, y1=e.y, ctrl=ctrl, moved=False)


        def on_motion(self, e):
            d = self.drag
            if not d:
                return
            z = self.z()
            k = d["kind"]
            if k == "stroke":
                sid = self.stroke["sid"]
                x, y = self.ptr_pos(e.x, e.y, sid)
                x = max(0.0, min(FW - 1.0, x))
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
                ball_h = cls(self.fr.figs[d["sl"]][2]) == "B" and (e.state & 1)
                if ball_h:
                    self.move_fig(d["sl"], 0, dy, only_self=True)
                else:
                    self.move_fig(d["sl"], dx, dy)
                d["done"] = (dxp, dyp)
            else:  
                if self.playing and not d["live"]:
                    d.update(live=True, x0=e.x, y0=e.y, a=tuple(self.fr.scroll), off=tuple(self.ball_off))
                    return
                if not (dxp or dyp):
                    return
                if not d["snapped"]:
                    self.snap()
                    d["snapped"] = True
                d["moved"] = True
                if self.cam_ball.get():  
                    self.ball_off = [max(-FW, min(FW, d["off"][0] + dxp)), max(-FH, min(FH, d["off"][1] + dyp))]
                else:
                    nx = max(0, min(FW - WIN_W, d["a"][0] + dxp))
                    ny = max(0, min(FH - WIN_H, d["a"][1] + dyp))
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
                    z = self.z()
                    x0, x1 = sorted((d["x0"], d["x1"]))
                    y0, y1 = sorted((d["y0"], d["y1"]))
                    hit = set()
                    for i, g in enumerate(self.fr.figs):
                        if cls(g[2]) in "LR":
                            continue
                        gx, gy, gw = g[0] * z, (g[1] + Y_OFFSET) * z, sprite_w(g[2]) * z
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
            if k == "fig" and not d["snapped"] and len(self.multi) > 1 and d["sl"] in self.multi and d["sl"] != self.sel:
                self.sel = d["sl"]
                self.note("Leader of the selection: %s" % self.names().get(d["sl"], "figure"))
            if k == "win" and not d["moved"] and self.tool.get() == "select":
                self.select(None)
                return
            self.refresh()


        def on_right(self, e):
            self.canvas.focus_set()
            z = self.z()
            px, py = e.x // z, e.y // z
            if self.tool.get() == "way" and self.way:
                return self.finish_way()
            sl = self.hit(px, py)
            k = self.path_hit(e.x, e.y) if sl is None else None
            m = tk.Menu(self, tearoff=0)
            if sl is not None:
                if sl not in self.multi:
                    self.select(sl)
                sid = self.fr.figs[sl][2]
                nm = self.names().get(sl, "figure")
                m.add_command(label="-- %s --" % nm, state="disabled")
                if len(self.multi) > 1 and sl in self.multi and sl != self.sel:
                    m.add_command(label="Make leader of the selection", command=lambda s=sl: self.set_leader(s))
                if team_of(sid) in ("R", "B"):
                    m.add_cascade(label="Action here", menu=self._action_menu(m))
                if loco_cycle(sid, "E"):
                    m.add_cascade(label="Run (sprites, to end of film)", menu=self._run_menu(m))
                m.add_command(label="Mirror pose (E <-> W)", command=self.mirror_sel)
                m.add_command(label="Lock pose (clear animation from here)", command=self.clear_anim)
                m.add_separator()
                m.add_command(label="Auto-sprites along trajectory", command=self.auto_here)
                m.add_command(label="Smooth trajectory (from here)", command=self.smooth_path)
                m.add_command(label="Even speed (from here)", command=self.even_speed)
                m.add_command(label="Freeze here (stop figure)", command=self.freeze_here)
                if cls(sid) in "SB":
                    m.add_command(label="Camera follows this ball", command=self.auto_camera)
                else:
                    m.add_command(label="Camera follows this figure", command=self.auto_camera)
                m.add_separator()
                m.add_command(label="Tip: draw a path with tool D, or right-click the field", state="disabled")
            elif k is not None:
                m.add_command(label="Trajectory point - frame %d" % (k + 1), state="disabled")
                m.add_command(label="Go to frame %d" % (k + 1), command=lambda: self.goto(k))
                m.add_command(label="Smooth trajectory (from this frame)", command=self.smooth_path)
                m.add_command(label="Even speed (from this frame)", command=self.even_speed)
                m.add_command(label="Straighten: interpolate to frame %d..." % (k + 1), command=lambda: self.tween_to(k))
            elif self.sel is not None and cls(self.fr.figs[self.sel][2]) not in "LR":
                sid = self.fr.figs[self.sel][2]
                tx, ty = self.ptr_pos(e.x, e.y, sid)
                tx, ty = max(0, min(FW - sprite_w(sid), round(tx))), max(0, min(MAX_Y, round(ty)))
                nm = self.names().get(self.sel, "figure")
                m.add_command(label="Path for '%s' to here (straight)" % nm, command=lambda: self.make_path(self.sel, tx, ty))
                m.add_command(label="Path to here in N frames...", command=lambda: self.path_n(tx, ty))
                m.add_command(label="Path to here, arriving at frame...", command=lambda: self.path_to_frame(tx, ty))
                m.add_separator()
                m.add_command(label="Move here (within selected scope only)", command=lambda: self.teleport(tx, ty))
                m.add_separator()
                m.add_command(label="Draw path (D)", command=lambda: (self.tool.set("draw"), self.set_tool()))
                m.add_command(label="Click path (P)", command=lambda: (self.tool.set("way"), self.set_tool()))
            else:
                m.add_command(label="Select a figure first (left click)", state="disabled")
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
            sl = self.sel
            g = self.fr.figs[sl]
            self.snap()
            self.move_fig(sl, tx - g[0], ty - g[1])
            self.refresh()

        def path_n(self, tx, ty):
            n = simpledialog.askinteger("Path", "Number of frames to reach the target:", minvalue=1, maxvalue=MAX_FRAMES, parent=self)
            if n:
                self.make_path(self.sel, tx, ty, n)

        def path_to_frame(self, tx, ty):
            e = simpledialog.askinteger("Path", "Arrival frame number (current is %d):" % (self.idx + 1),
                                        minvalue=self.idx + 2, maxvalue=MAX_FRAMES, parent=self)
            if e:
                self.make_path(self.sel, tx, ty, e - 1 - self.idx)

        def make_path(self, sl, tx, ty, n=None):
            if cls(self.fr.figs[sl][2]) in "LR":
                return
            g = self.fr.figs[sl]
            self.bake_path([(g[0], g[1]), (tx, ty)], n=n)


        def do_mirror_pose(self, sl):
            self.snap()
            self.set_pose_to(sl, mirror_pose(self.fr.figs[sl][2]))
            self.refresh()

        def need_sel(self):
            if self.sel is None or cls(self.fr.figs[self.sel][2]) in "LR":
                messagebox.showinfo("Figure", "Select a figure first.")
                return False
            return True

        def program_anim(self):
            if not self.need_sel():
                return
            s = simpledialog.askstring("Pose sequence", "Pose IDs separated by commas.\nThey repeat cyclically from this frame to the end of the film:", parent=self)
            try:
                seq = [int(v) for v in (s or "").replace(";", ",").split(",") if v.strip()]
            except ValueError:
                return messagebox.showerror("Error", "Invalid values.")
            if seq:
                self.snap()
                for n, i in enumerate(range(self.idx, len(self.scene.frames))):
                    self.scene.frames[i].figs[self.sel][2] = max(0, min(145, seq[n % len(seq)]))
                    self.scene.frames[i].touch()
                self.refresh()

        def clear_anim(self):
            if not self.need_sel():
                return
            self.snap()
            pid = self.fr.figs[self.sel][2]
            for f in self.scene.frames[self.idx:]:
                f.figs[self.sel][2] = pid
                f.touch()
            self.refresh()

        def tween(self):
            if not self.need_sel():
                return
            end = simpledialog.askinteger("Interpolate", "Final frame (1-%d):" % len(self.scene.frames),
                                          minvalue=1, maxvalue=len(self.scene.frames), parent=self)
            if end:
                self.tween_to(end - 1)


        def tween_scroll(self):
            end = simpledialog.askinteger("Interpolatete scroll", "Final frame (1-%d):" % len(self.scene.frames), minvalue=1, maxvalue=len(self.scene.frames), parent=self)
            if not end or end - 1 <= self.idx:
                return
            self.snap()
            fs, n = self.scene.frames, end - 1 - self.idx
            a, b = fs[self.idx].scroll, fs[end - 1].scroll
            for k in range(1, n):
                fs[self.idx + k].scroll = [round(a[0] + (b[0] - a[0]) * k / n), round(a[1] + (b[1] - a[1]) * k / n)]
                fs[self.idx + k].dirty = True
            self.refresh()

        def ball_anchor(self, f):
            b = f.index_of("B")
            if b is None:
                return None
            g = f.figs[b]
            sh = f.index_of("S")
            gy = f.figs[sh][1] if sh is not None else g[1]
            return g[0] + sprite_w(g[2]) / 2 - WIN_W / 2, gy + Y_OFFSET - WIN_H / 2

        def apply_ball_lock(self):
            ox, oy = self.ball_off
            for f in self.scene.frames:
                a = self.ball_anchor(f)
                if a is None:
                    continue
                sc = [int(round(max(0, min(FW - WIN_W, a[0] + ox)))), int(round(max(0, min(FH - WIN_H, a[1] + oy))))]
                if f.scroll != sc:
                    f.scroll = sc
                    f.dirty = True

        def toggle_cam_ball(self):
            if self.cam_ball.get():
                self.snap()
                self.ball_off = [0, 0]
                self.refresh()
                self.note("Window locked to the ball (whole film). Pan (H) now shifts the window relative to the ball.")
            else:
                self.note("Window released: it keeps the positions computed while it was locked.")

        def set_scroll(self):
            try:
                sx, sy = int(self.sx.get()), int(self.sy.get())
            except (tk.TclError, ValueError):
                return
            if self.cam_ball.get():
                a = self.ball_anchor(self.fr)
                if a is not None:
                    self.snap()
                    self.ball_off = [sx - round(a[0]), sy - round(a[1])]
                    self.refresh()
                    return
            self.snap()
            for i in self.frames_in_scope():
                self.scene.frames[i].scroll = [max(0, min(FW - WIN_W, sx)), max(0, min(FH - WIN_H, sy))]
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
            self.note("Scene %s." % ("mirrored (field side + colors)" if flip else "with team colors swapped"))

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
            self.refresh()

        def step(self, d):
            self.goto((self.idx + d) % len(self.scene.frames))

        def on_tl(self, e):
            n = len(self.scene.frames)
            cw = max(4.0, (self.tl.winfo_width() - 8) / n)
            self.goto(int((e.x - 4) / cw))

        def toggle(self, start):
            self.playing = not self.playing
            self.btn.config(text="Stop" if self.playing else "Play tutto")
            if self.playing:
                self.goto(start)
                self.after(10, self.tick)

        def tick(self):
            if not self.playing:
                return
            if self.idx >= len(self.scene.frames) - 1:
                if not self.loop.get():
                    self.playing = False
                    self.btn.config(text="Play tutto")
                    return
                self.goto(0)
            else:
                self.goto(self.idx + 1)
            try:
                fps = max(1, int(self.fps.get()))
            except (tk.TclError, ValueError):
                fps = 12
            self.after(int(1000 / fps), self.tick)

        def ins_frame(self):
            if len(self.scene.frames) >= MAX_FRAMES:
                return messagebox.showwarning("Limit", "Maximum %d frames." % MAX_FRAMES)
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
                return messagebox.showinfo("Delete", "At least one frame is required.")
            self.snap()
            del self.scene.frames[self.idx]
            self.scene.events = [None if e == self.idx else (e - 1 if (e is not None and e > self.idx) else e) for e in self.scene.events]
            self.idx = min(self.idx, len(self.scene.frames) - 1)
            self.refresh()


        def clear_film(self):
            if not messagebox.askyesno("Delete film", "Delete ALL frames (keep only the current one)?"):
                return
            self.snap()
            self.scene.frames = [self.fr]
            self.scene.events = [0 if e is not None else None for e in self.scene.events]
            self.idx = 0
            self.refresh()

        def props(self):
            w = tk.Toplevel(self)
            w.title("Scene properties")
            w.transient(self)
            ver = tk.StringVar(value=self.scene.sig[:11].decode())
            au = tk.StringVar(value=self.scene.author)
            ttk.Label(w, text="Author (ERBAUER):").grid(row=0, column=0, sticky="w", padx=8, pady=6)
            ttk.Entry(w, textvariable=au, width=24).grid(row=0, column=1, padx=8)
            ttk.Label(w, text="File version:").grid(row=1, column=0, sticky="w", padx=8)
            ttk.Combobox(w, textvariable=ver, values=["BM-Ed1.3-WK", "BM-Ed1.0-WK"], state="readonly", width=14).grid(row=1, column=1, sticky="w", padx=8)

            def ok():
                self.snap()
                self.scene.author = au.get()
                self.scene.sig = (ver.get() + "\0").encode()
                w.destroy()
            ttk.Button(w, text="OK", command=ok).grid(row=2, column=1, pady=8, sticky="e", padx=8)

        def help(self):
            messagebox.showinfo("Quick help",
                "TOOLS (left column or keys)\n"
                " V select/move | D draw a path freehand | P click a path with waypoints | H pan the window\n\n"
                "DRAWING A PATH\n"
                " D: press on a figure and draw; on release the path is baked into the following frames.\n"
                "   Top bar: speed / fixed duration / 'as drawn' (your real drawing speed). Shift = straight line.\n"
                " P: click points (Enter, double-click or right-click to finish). 'smooth curves' rounds the corners.\n"
                " Run sprites are chosen automatically from the direction of travel (8 directions, both colours).\n\n"
                "EDITING A PATH LIKE A ROPE\n"
                " Select tool: drag any dot of the yellow trajectory; neighbouring frames follow smoothly\n"
                " (Rope softness = how many frames are pulled). Shift = move only that point.\n"
                " 'pin current frame' keeps the current frame in place. Path menu: smooth / even speed / freeze.\n\n"
                "ACTIONS (right-click a player, Figure menu or Actions tab)\n"
                " Dive, Header, Bicycle kick, Collision fall, Get up - each with E/W, colour automatic.\n\n"
                "CAMERA\n Path/Camera > Camera follows ball/figure generates the scroll keyframes for you.\n\n"
                "MOUSE\n Drag figure: move (Ctrl+click or box-select for groups; Shift on the ball = height only).\n"
                " Drag the cyan window edge: scroll (also live while playing). Box select: leader = rule in the bar; click a selected figure to change it.\n"
                " Path/Camera > Window locked to ball: window centred on the ball in every frame.\n"
                " Wheel / PgUp / PgDn: change frame. Timeline: click, right-click.\n\n"
                "KEYS\n Arrows: move 1 px (Shift = 5) | [ ]: previous/next pose | Space: play | Ins/Del: frame\n"
                " Ctrl+Z/Y undo/redo | Ctrl+S save | Ctrl+A select all players | Ctrl +/-: zoom | Esc: cancel/deselect\n\n"
                "Pose sets marked (?) are still unverified; override with tore_poses.json / tore_actions.json.")

        def sel_sid(self):
            return None if self.sel is None else self.fr.figs[self.sel][2]

        def draw_poses(self):
            cv = self.pose_cv
            cv.delete("all")
            self._thumbs = []
            sid = self.sel_sid()
            cats = cats_for(sid) if sid is not None else []
            self.cat_cb.config(values=[n for n, _ in cats])
            if not cats:
                self.cat_var.set("")
                self.pose_info.config(text="Select a player, the referee, or the ball")
                return
            names = [n for n, _ in cats]
            if self.cat_var.get() not in names or sid != getattr(self, "_cat_sid", None):
                self.cat_var.set(next((n for n, ids in cats if sid in ids), self.cat_var.get() if self.cat_var.get() in names else names[0]))
            self._cat_sid = sid
            ids = dict(cats)[self.cat_var.get()]
            curcat = next((n for n, i in cats if sid in i), "-")
            self.pose_info.config(text="Current pose: id %d  (%s)" % (sid, curcat))
            cw, ch = 44, 50
            rows = (len(ids) + 4) // 5
            cv.config(height=max(60, rows * ch))
            for n, pid in enumerate(ids):
                x, y = (n % 5) * cw, (n // 5) * ch
                spr = sprite_of(self.gfx, pid)
                cv.create_rectangle(x + 2, y + 2, x + cw - 2, y + ch - 2, outline="#ffb000" if pid == sid else "#ccc",
                                    width=3 if pid == sid else 1, fill="#303030")
                if spr is not None:
                    im = spr.resize((spr.width * 3, spr.height * 3), Image.NEAREST)
                    ph = ImageTk.PhotoImage(im)
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
                self.set_pose_to(self.sel, ids[n])
                self.refresh()

        def open_palette(self):
            if self.pal and self.pal.winfo_exists():
                return self.pal.lift()

            self.pal = w = tk.Toplevel(self)
            w.title("Sprite IDs (click to assign)")
            w.transient(self)
            w.protocol("WM_DELETE_WINDOW", lambda: self._close_palette())

            zz = 6
            cols = SHEET_COLS
            rows = 7
            sheet = self.gfx.sheet
            im = Image.new("RGBA", (cols * CELL_W, rows * CELL_H), (60, 60, 60, 255))
            if sheet:
                crop = sheet.crop((0, 0, min(sheet.width, im.width), min(sheet.height, im.height)))
                im.paste(crop, (0, 0), crop)

            big = im.resize((im.width * zz, im.height * zz), Image.NEAREST)
            w._ph = ImageTk.PhotoImage(big)
            cv = tk.Canvas(w, width=big.width, height=big.height, highlightthickness=0, bg="#3c3c3c")
            cv.pack()
            cv.create_image(0, 0, anchor="nw", image=w._ph)

            for sid in range(cols * rows):
                col = sid % cols
                row = sid // cols
                x0 = col * CELL_W * zz
                y0 = row * CELL_H * zz
                x1 = x0 + CELL_W * zz
                y1 = y0 + CELL_H * zz
                cv.create_rectangle(x0, y0, x1, y1, outline="#ff00ff")
                cv.create_text(x0 + 1 * zz, y0 + 1 * zz, anchor="nw", text=str(sid),
                               fill="white", font=("TkDefaultFont", 7, "bold"))

            cv.bind("<Button-1>", self.on_palette_click)
            cv.bind("<Motion>", self.on_palette_hover)
            self._palette_canvas = cv

        def _close_palette(self):
            if self.pal and self.pal.winfo_exists():
                self.pal.destroy()
            self.pal = None
            self._palette_canvas = None

        def on_palette_hover(self, e):
            sid = (e.y // (CELL_H * 6)) * SHEET_COLS + (e.x // (CELL_W * 6))
            if 0 <= sid < SHEET_COLS * 7:
                self.note("sprite=%d  |  palette cell x=%d y=%d" %
                          (sid, e.x // (CELL_W * 6), e.y // (CELL_H * 6)))

        def on_palette_click(self, e):
            sid = (e.y // (CELL_H * 6)) * SHEET_COLS + (e.x // (CELL_W * 6))
            if not (0 <= sid < SHEET_COLS * 7):
                return

            if self.sel is not None:
                self.snap()
                self.set_pose_to(self.sel, sid)
                self.refresh()
                return

            if len(self.fr.figs) >= N_RECORDS:
                return self.note("Select a figure to assign a sprite ID.")

            self.snap()
            x = max(0, min(FW - sprite_w(sid), self.fr.scroll[0] + WIN_W // 2 - sprite_w(sid) // 2))
            y = max(0, min(MAX_Y, self.fr.scroll[1] + WIN_H // 2 - Y_OFFSET - CELL_H // 2))
            for i in self.frames_in_scope():
                f = self.scene.frames[i]
                f.figs.append([x, y, sid])
                f.touch()
            self.sel = len(self.fr.figs) - 1
            self.refresh()

        def load_gfx(self, p=None):
            pic = locate_pic(p)
            self.pic_dir = pic
            self.gfx = Graphics(pic)
            if pic is None:
                self.note("Graphics not found (File > PIC folder...)")
            elif self.gfx.missing:
                self.note("Missing: " + ", ".join(self.gfx.missing))

        def choose_pic(self):
            d = filedialog.askdirectory(title="Folder containing 26.VGA, 27.VGA, 29.VGA")
            if d:
                self.pic_dir = d
                self.gfx = Graphics(d)
                self.refresh()

        def confirm_discard(self):
            return not self.modified or messagebox.askyesno("Unsaved changes", "Discard changes?")

        def new_scene(self):
            if self.confirm_discard():
                self.scene = Scene.new()
                self.idx, self.sel, self.modified = 0, None, False
                self.undo_s.clear()
                self.refresh()

        def open_dialog(self):
            if not self.confirm_discard():
                return
            p = filedialog.askopenfilename(title="Open scene", filetypes=[("Scene", "*.t *.v *.te *.tj *.ve *.vj"), ("Tutti", "*.*")])
            if p:
                self.open_path(p)

        def open_path(self, p):
            try:
                self.scene = Scene.load(p)
            except Exception as ex:
                return messagebox.showerror("Error", str(ex))
            if not self.pic_dir or find_pic_dir(p):
                self.load_gfx(p)
            self.idx, self.sel, self.modified = 0, None, False
            self.undo_s.clear()
            self.refresh()

        def _write(self, p):
            try:
                self.scene.save(p)
                self.modified = False
                self.refresh()
                return True
            except OSError as ex:
                messagebox.showerror("Error", "Could not save: %s" % ex)
                return False

        def save(self):
            if not self.scene.path:
                return self.save_as()
            self._write(self.scene.path)

        def save_as(self):
            p = filedialog.asksaveasfilename(title="Save scene", defaultextension=".T",
                                             initialfile=os.path.basename(self.scene.path or "1.T"),
                                             filetypes=[("Scene", "*.t *.v *.te *.tj *.ve *.vj"), ("Tutti", "*.*")])
            if p:
                self._write(p)

        def save_numbered(self):
            base = os.path.dirname(os.path.abspath(self.scene.path)) if self.scene.path else os.getcwd()
            an = find_anzahl(self.scene.path or os.path.join(base, "x"))
            vals = read_anzahl(an) if an else None
            w = tk.Toplevel(self)
            w.title("Save as numbered scene")
            w.transient(self)
            w.grab_set()
            kind, var_ = tk.StringVar(value="T"), tk.StringVar(value=VARIANTS[""])
            num = tk.IntVar(value=(vals[0] + 1) if vals else 1)
            ttk.Label(w, text="Type:").grid(row=0, column=0, sticky="w", padx=8, pady=6)
            for i, (k, nm) in enumerate(KINDS.items()):
                ttk.Radiobutton(w, text=nm, value=k, variable=kind).grid(row=0, column=1 + i, padx=4)
            ttk.Label(w, text="Variant:").grid(row=1, column=0, sticky="w", padx=8)
            vb = ttk.Combobox(w, textvariable=var_, values=list(VARIANTS.values()), state="readonly", width=18)
            vb.grid(row=1, column=1, columnspan=2, sticky="w", padx=4)
            ttk.Label(w, text="Scene number:").grid(row=2, column=0, sticky="w", padx=8, pady=6)
            ttk.Spinbox(w, from_=1, to=999, width=6, textvariable=num).grid(row=2, column=1, sticky="w", padx=4)
            ttk.Label(w, text=("ANZAHL: %s -> max %s" % (an, vals)) if vals else "ANZAHL not found (it will not be updated)",
                      foreground="#555").grid(row=3, column=0, columnspan=3, padx=8, sticky="w")

            def ok():
                vi = list(VARIANTS.values()).index(var_.get())
                ext = kind.get() + list(VARIANTS)[vi]
                p = os.path.join(base, "%d.%s" % (num.get(), ext))
                if os.path.exists(p) and not messagebox.askyesno("Existing file", "%s already exists. Overwrite?" % os.path.basename(p), parent=w):
                    return
                if self._write(p) and an and vals and num.get() > vals[vi]:
                    vals[vi] = num.get()
                    write_anzahl(an, vals)
                w.destroy()
            ttk.Button(w, text="Save", command=ok).grid(row=4, column=2, pady=8, padx=8, sticky="e")

        def delete_file(self):
            p = self.scene.path
            if p and os.path.isfile(p) and messagebox.askyesno("Delete file", "Permanently delete %s?" % p):
                os.remove(p)
                self.scene.path = None
                self.refresh()

        def quit_app(self):
            if self.confirm_discard():
                self.destroy()

        def rezoom(self):
            z = self.z()
            self.canvas.config(width=FW * z, height=FH * z)
            self.refresh()

        def ghosts(self):
            mode, i, fs = self.ghost.get(), self.idx, self.scene.frames
            out = []
            if mode == GHOST_OPTS[0] or i == 0:
                return out
            if mode == GHOST_OPTS[1] and self.sel is not None:
                x, y, sid = fs[i - 1].figs[self.sel]
                out.append((x, y, sid, 0.45))
            elif mode == GHOST_OPTS[2] and self.sel is not None:
                for j in range(i):
                    x, y, sid = fs[j].figs[self.sel]
                    out.append((x, y, sid, 0.15 + 0.3 * (j + 1) / i))
            elif mode == GHOST_OPTS[3]:
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
                    out[i] = {"S": "Ball shadow", "B": "Ball", "L": "Left goal", "R": "Right goal"}[c]
                else:
                    t = team_of(g[2])
                    cnt[t] += 1
                    out[i] = {"R": "Red", "B": "Blue", "A": "Referee"}[t] + ("" if t == "A" else " %d" % cnt[t])
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
            s = self.tree.selection()
            if s and int(s[0]) != self.sel:
                self.select(int(s[0]))

        def refresh(self, light=False):
            sc, z = self.scene, self.z()
            n = len(sc.frames)
            self.idx = min(self.idx, n - 1)
            if self.cam_ball.get():
                self.apply_ball_lock()
            f = self.fr
            self.sx.set(f.scroll[0])
            self.sy.set(f.scroll[1])
            img = compose(self.gfx, f, self.ghosts())
            img = img.resize((img.width * z, img.height * z), Image.NEAREST)
            self._photo = ImageTk.PhotoImage(img)
            c = self.canvas
            c.config(width=img.width, height=img.height)
            c.delete("all")
            c.create_image(0, 0, anchor="nw", image=self._photo)
            if self.show_win.get():
                x0, y0 = f.scroll[0] * z, f.scroll[1] * z
                x1, y1 = x0 + WIN_W * z, y0 + WIN_H * z
                for r in ((0, 0, img.width, y0), (0, y1, img.width, img.height), (0, y0, x0, y1), (x1, y0, img.width, y1)):
                    c.create_rectangle(*r, fill="black", stipple="gray50", outline="")
                c.create_rectangle(x0, y0, x1, y1, outline="#00e5ff")
            if self.show_ids.get():
                for g in f.figs:
                    if cls(g[2]) not in "LR":
                        c.create_text(g[0] * z + 1, (g[1] + Y_OFFSET) * z - 1, anchor="sw", text=str(g[2]),
                                      fill="#fff59d", font=("TkDefaultFont", 7))
            for s in self.multi:
                if s != self.sel and s < len(f.figs):
                    x, y, sid = f.figs[s]
                    c.create_rectangle(x * z, (y + Y_OFFSET) * z, (x + sprite_w(sid)) * z, (y + Y_OFFSET + CELL_H) * z,
                                       outline="#00e5ff", width=2, dash=(3, 2))
            if self.sel is not None:
                x, y, sid = f.figs[self.sel]
                if self.show_path.get() and n > 1:
                    pts = [self.ctr(g.figs[self.sel]) for g in sc.frames]
                    c.create_line(*[v for p in pts for v in p], fill="#ffd54a", dash=(4, 3))
                    for k, (px, py) in enumerate(pts):
                        r = 4 if k == self.idx else 2.5
                        c.create_oval(px - r, py - r, px + r, py + r, fill="#ff5252" if k == self.idx else "#ffd54a", outline="black" if k == self.idx else "")
                        if z >= 3 and k % 5 == 4 and k != self.idx:
                            c.create_text(px, py - 7, text=str(k + 1), fill="#ffe082", font=("TkDefaultFont", 7))
                c.create_rectangle(x * z, (y + Y_OFFSET) * z, (x + sprite_w(sid)) * z, (y + Y_OFFSET + CELL_H) * z, outline="#ffff00", width=2)
                if len(self.multi) > 1:
                    c.create_text(x * z + 1, (y + Y_OFFSET) * z - 1, anchor="sw", text="leader", fill="#ffff00",
                                  font=("TkDefaultFont", 7, "bold"))
            self.draw_overlay()
            self.draw_timeline()
            ev = next((k for k, e in enumerate(sc.events) if e == self.idx), -1)
            self.snd_var.set(ev)
            if not light:
                self.fill_tree()
                self.draw_poses()
            fn = os.path.basename(sc.path) if sc.path else "(new)"
            self.title("TORE Editor - %s%s   frame %d/%d" % (fn, " *" if self.modified else "", self.idx + 1, n))


        def fill_tree(self):
            nm = self.names()
            self.tree.unbind("<<TreeviewSelect>>")
            self.tree.delete(*self.tree.get_children())
            for sl, g in enumerate(self.fr.figs):
                self.tree.insert("", "end", iid=str(sl), text=nm[sl], values=tuple(g))
            if self.sel is not None:
                self.tree.selection_set(str(self.sel))
            self.tree.bind("<<TreeviewSelect>>", self.on_tree)

        def draw_timeline(self):
            c = self.tl
            c.delete("all")
            fs = self.scene.frames
            n = len(fs)
            W = max(c.winfo_width(), 300)
            cw = max(4.0, (W - 8) / n)
            for i in range(n):
                x0 = 4 + i * cw
                c.create_rectangle(x0, 4, x0 + cw - 1, 18, outline="", fill="#1e88e5" if i == self.idx else ("#d8d8d8" if i % 2 else "#c4c4c4"))
                if self.sel is not None and self.sel < len(fs[i].figs):
                    sid = fs[i].figs[self.sel][2]
                    stand = {stand_id(sid, "E"), stand_id(sid, "W")}
                    col = "#9e9e9e" if sid in stand else "#66bb6a" if sid in loco_ids(sid) else "#ff9800"
                    c.create_rectangle(x0, 20, x0 + cw - 1, 27, outline="", fill=col)
                if cw >= 16 or i % 5 == 4 or i == self.idx:
                    c.create_text(x0 + cw / 2, 37, text=str(i + 1), font=("TkDefaultFont", 7), fill="#444")
            for k, e in enumerate(self.scene.events):
                if e is not None and e < n:
                    x = 4 + e * cw + cw / 2
                    c.create_polygon(x - 5, 56, x + 5, 56, x, 46, fill=SOUNDS[k][1], outline="black")


        def _action_menu(self, parent):
            am = tk.Menu(parent, tearoff=0)
            for key in ACTION_ORDER:
                for side in "EW":
                    am.add_command(label="%s -> %s" % (ACTIONS[key]["label"], side),
                                   command=lambda k=key, s=side: self.do_action(k, s))
                am.add_separator()
            return am


        def _run_menu(self, parent):
            rm = tk.Menu(parent, tearoff=0)
            for d in DIRS:
                rm.add_command(label="Run %s (%s)" % (d, DIR_LABEL[d]), command=lambda d=d: self.do_cycle(d))
            return rm


        HINTS = {
            "select": f"\nClick: select | Ctrl+click: add | Drag figure: move | Drag a trajectory dot: pull the rope | "
                      f"Drag empty: box select (leader rule in the bar)\nClick a selected figure: make it leader | "
                      "Drag the cyan window edge: scroll | Right-click: menu",
            "draw": f"\nPress on a figure and draw its path; release to bake it into the frames | Shift: straight line | Esc: cancel",
            "way": f"\nClick points to lay out a path | Enter / double-click / right-click: finish | Backspace: undo point | Esc: cancel",
            "pan": f"\nDrag to move the visible window (works live during playback; with 'window locked to ball' it shifts the offset)",
        }


        def set_tool(self):
            t = self.tool.get()
            self.stroke, self.way = None, []
            self.hint = self.HINTS[t]
            self.canvas.config(cursor={"select": "arrow", "draw": "pencil", "way": "crosshair", "pan": "fleur"}[t])
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
            z, w = self.z(), sprite_w(g[2])
            return (g[0] + w / 2) * z, (g[1] + Y_OFFSET + CELL_H / 2) * z


        def pos_ctr(self, x, y, sid):
            z, w = self.z(), sprite_w(sid)
            return (x + w / 2) * z, (y + Y_OFFSET + CELL_H / 2) * z


        def ptr_pos(self, ex, ey, sid):
            z, w = self.z(), sprite_w(sid)
            return ex / z - w / 2, ey / z - Y_OFFSET - CELL_H / 2


        def pick_leader(self, ids):
            fs = self.fr.figs
            r = self.leader_rule.get()
            key = {"North": lambda s: (fs[s][1], s), "South": lambda s: (-fs[s][1], s),
                   "West": lambda s: (fs[s][0], s), "East": lambda s: (-fs[s][0], s)}.get(r, lambda s: s)
            return min(ids, key=key)

        def regroup_leader(self):
            if len(self.multi) > 1:
                self.sel = self.pick_leader(self.multi)
                self.refresh()

        def set_leader(self, sl):
            if sl in self.multi and sl != self.sel:
                self.sel = sl
                self.refresh()
                self.note("Leader of the selection: %s" % self.names().get(sl, "figure"))

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
            best, bd = None, tol
            for k, f in enumerate(self.scene.frames):
                cx, cy = self.ctr(f.figs[self.sel])
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


        def on_tl_right(self, e):
            n = len(self.scene.frames)
            cw = max(4.0, (self.tl.winfo_width() - 8) / n)
            i = max(0, min(n - 1, int((e.x - 4) / cw)))
            self.goto(i)
            m = tk.Menu(self, tearoff=0)
            m.add_command(label="Frame %d" % (i + 1), state="disabled")
            m.add_command(label="Play from here", command=lambda: self.toggle(i))
            m.add_separator()
            m.add_command(label="Insert frame (copy)", command=self.ins_frame)
            m.add_command(label="Delete frame", command=self.del_frame)
            m.add_separator()
            snd = tk.Menu(m, tearoff=0)
            snd.add_command(label="none", command=lambda: (self.snd_var.set(-1), self.set_sound()))
            for k, (nm, _c) in enumerate(SOUNDS):
                snd.add_command(label=nm, command=lambda k=k: (self.snd_var.set(k), self.set_sound()))
            m.add_cascade(label="Sound at this frame", menu=snd)
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


        def _clampx(self, v):
            return max(0, min(FW - 1, int(round(v))))


        def _clampy(self, v):
            return max(0, min(MAX_Y, int(round(v))))


        def mirror_sel(self):
            if self.need_sel():
                self.do_mirror_pose(self.sel)

        def bake_path(self, pts, samples=None, n=None):
            sl = self.sel
            if sl is None:
                return
            fs = self.scene.frames
            start = (float(self.fr.figs[sl][0]), float(self.fr.figs[sl][1]))
            path = [start] + [(float(x), float(y)) for x, y in pts[1:]]
            if poly_len(path) < 1:
                return self.note("Destination is too close.")
            mode = self.pmode.get()
            if n is not None:
                pos = resample_steps(path, max(1, n))
            elif mode == "timing" and samples and len(samples) > 1 and samples[-1][0] > 0.05:
                pos = resample_time(samples, self._fps())
                if self.smooth.get() and len(pos) > 2:
                    for _ in range(2):
                        pos = [pos[0]] + [((pos[i - 1][0] + 2 * pos[i][0] + pos[i + 1][0]) / 4,
                                           (pos[i - 1][1] + 2 * pos[i][1] + pos[i + 1][1]) / 4) for i in range(1, len(pos) - 1)] + [pos[-1]]
            elif mode == "frames":
                pos = resample_steps(path, max(1, int(self.pframes.get())))
            else:
                pos = resample_steps(path, max(1, math.ceil(poly_len(path) / self._speed())))
            n = len(pos)
            self.snap()
            if self.idx + n + 1 > MAX_FRAMES:
                n = MAX_FRAMES - 1 - self.idx
                pos = pos[:n]
            if n < 1:
                return self.note("No frame available after this one.")
            self.ensure_frames(self.idx + n + 1)
            slots = self.group_slots()
            base = {s: (fs[self.idx].figs[s][0], fs[self.idx].figs[s][1]) for s in slots}
            endold = {s: (fs[self.idx + n].figs[s][0], fs[self.idx + n].figs[s][1]) for s in slots}
            for k, (px, py) in enumerate(pos, start=1):
                f = fs[self.idx + k]
                for s in slots:
                    f.figs[s][0] = self._clampx(base[s][0] + px - start[0])
                    f.figs[s][1] = self._clampy(base[s][1] + py - start[1])
                f.touch()
            if self.follow.get():
                fe = fs[self.idx + n]
                for j in range(self.idx + n + 1, len(fs)):
                    for s in slots:
                        fs[j].figs[s][0] = self._clampx(fs[j].figs[s][0] + fe.figs[s][0] - endold[s][0])
                        fs[j].figs[s][1] = self._clampy(fs[j].figs[s][1] + fe.figs[s][1] - endold[s][1])
                    fs[j].touch()
            if self.auto_spr.get():
                self.auto_sprites(slots, self.idx + 1, self.idx + n, force=True)
            self.refresh()
            self.note("Path baked: %d frames (%d -> %d), length %.0f px" % (n, self.idx + 1, self.idx + n + 1, poly_len(path)))


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
                face = facing_of(prev_sid)
                ph = 0
                for n, i in enumerate(range(i0, i1 + 1)):
                    f = fs[i]
                    g = f.figs[sl]
                    if not force and g[2] not in loco_ids(g[2]):
                        prev_sid, face, ph = g[2], facing_of(g[2]), 0
                        continue
                    d = dirs[n]
                    if d is None:
                        new = stand_id(g[2], face)
                        ph = 0
                    else:
                        if "E" in d or "W" in d:
                            face = "W" if "W" in d else "E"
                        cyc = loco_cycle(g[2], d)
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
            self.note("Sprites re-derived from movement (special poses kept).")


        def do_stand(self):
            if not self.need_sel():
                return
            sid = self.fr.figs[self.sel][2]
            if team_of(sid) is None:
                return
            self.snap()
            new = stand_id(sid, facing_of(sid))
            for f in self.scene.frames[self.idx:]:
                f.figs[self.sel][2] = new
                f.touch()
            self.refresh()


        def do_cycle(self, d):
            if not self.need_sel():
                return
            sid = self.fr.figs[self.sel][2]
            cyc = loco_cycle(sid, d)
            if not cyc:
                return
            self.snap()
            fs = self.scene.frames
            ph = cyc.index(sid) + 1 if sid in cyc else 0
            start = self.idx + (1 if sid in cyc else 0)
            for k, i in enumerate(range(start, len(fs))):
                fs[i].figs[self.sel][2] = cyc[(ph + k) % len(cyc)]
                fs[i].touch()
            self.refresh()


        def do_action(self, key, side):
            if not self.need_sel():
                return
            sid = self.fr.figs[self.sel][2]
            seq = action_ids(sid, key, side)
            if not seq:
                return self.note("Actions are for players (red/blue) only.")
            n = len(seq)
            self.snap()
            if self.idx + n > MAX_FRAMES:
                seq = seq[:MAX_FRAMES - self.idx]
                n = len(seq)
            self.ensure_frames(self.idx + n)
            fs = self.scene.frames
            for j, s in enumerate(seq):
                fs[self.idx + j].figs[self.sel][2] = s
                fs[self.idx + j].touch()
            if self.resume.get() and self.idx + n < len(fs):
                self.auto_sprites([self.sel], self.idx + n, len(fs) - 1, force=False)
            self.refresh()
            self.note("%s (%s): %d frames from frame %d" % (ACTIONS[key]["label"], side, n, self.idx + 1))


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
                        fs[i].figs[s][0] = self._clampx(sum(p[0] for p in w) / len(w))
                        fs[i].figs[s][1] = self._clampy(sum(p[1] for p in w) / len(w))
            for i in range(self.idx, len(fs)):
                fs[i].touch()
            if self.auto_spr.get():
                self.auto_sprites(self.group_slots(), self.idx + 1, len(fs) - 1, force=False)
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
                    fs[self.idx + k].figs[s][0] = self._clampx(px)
                    fs[self.idx + k].figs[s][1] = self._clampy(py)
            for i in range(self.idx, len(fs)):
                fs[i].touch()
            self.refresh()
            self.note("Trajectory re-spaced at constant speed.")


        def freeze_here(self):
            if not self.need_sel():
                return
            self.snap()
            fs = self.scene.frames
            for s in self.group_slots():
                x, y = fs[self.idx].figs[s][0], fs[self.idx].figs[s][1]
                for f in fs[self.idx + 1:]:
                    f.figs[s][0], f.figs[s][1] = x, y
            for f in fs[self.idx + 1:]:
                f.touch()
            if self.auto_spr.get():
                self.auto_sprites(self.group_slots(), self.idx + 1, len(fs) - 1, force=False)
            self.refresh()


        def auto_camera(self, whole=False):
            fs = self.scene.frames
            i0 = 0 if whole else self.idx
            tgt = self.sel if (self.sel is not None and cls(self.fr.figs[self.sel][2]) in "PB") else None
            self.snap()
            sx, sy = float(fs[i0].scroll[0]), float(fs[i0].scroll[1])
            for i in range(i0, len(fs)):
                f = fs[i]
                b = tgt if tgt is not None else f.index_of("B")
                if b is None:
                    continue
                g = f.figs[b]
                wx = max(0.0, min(float(FW - WIN_W), g[0] + sprite_w(g[2]) / 2 - WIN_W / 2))
                wy = max(0.0, min(float(FH - WIN_H), g[1] + Y_OFFSET - WIN_H / 2))
                if i == i0 and whole:
                    sx, sy = wx, wy
                sx += max(-6.0, min(6.0, (wx - sx) * 0.35))
                sy += max(-2.0, min(2.0, (wy - sy) * 0.35))
                f.scroll = [int(round(sx)), int(round(sy))]
                f.dirty = True
            self.refresh()
            self.note("Camera keyframes generated (smoothed, max 6 px/frame).")


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
            g = self.fr.figs[self.sel]
            pts = [(float(g[0]), float(g[1]))] + list(self.way)
            self.way = []
            if self.smooth.get() and len(pts) > 2:
                pts = catmull(pts)
            self.bake_path(pts)
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
            z = self.z()
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
                    f.figs[s][0] = self._clampx(bx + dx * wi)
                    f.figs[s][1] = self._clampy(by + dy * wi)
                f.touch()
                d["changed"].add(i)
            self.refresh(light=True)


        def end_rope(self, d):
            ch = d["changed"]
            if ch and self.auto_spr.get():
                self.auto_sprites(d["slots"], min(ch), max(ch) + 1, force=False)
            self.refresh()


        def draw_overlay(self):
            c = self.canvas
            c.delete("ov")
            z = self.z()
            if self.sel is None:
                sid = None
            else:
                sid = self.fr.figs[self.sel][2]
            st = self.stroke
            if st and len(st["pts"]) > 1:
                pts = [v for p in st["pts"] for v in self.pos_ctr(p[0], p[1], st["sid"])]
                c.create_line(*pts, fill="#ff9800", width=2, tags="ov")
            if self.way and sid is not None:
                g = self.fr.figs[self.sel]
                pts = [(float(g[0]), float(g[1]))] + list(self.way)
                curve = catmull(pts) if (self.smooth.get() and len(pts) > 2) else pts
                c.create_line(*[v for p in curve for v in self.pos_ctr(p[0], p[1], sid)], fill="#ff9800", width=2, tags="ov")
                for k, p in enumerate(pts):
                    cx, cy = self.pos_ctr(p[0], p[1], sid)
                    c.create_rectangle(cx - 3, cy - 3, cx + 3, cy + 3, fill="#ff9800" if k else "#ffff00", outline="black", tags="ov")
                if self.cursor_pos:
                    lx, ly = self.pos_ctr(pts[-1][0], pts[-1][1], sid)
                    c.create_line(lx, ly, self.cursor_pos[0] * z, self.cursor_pos[1] * z, fill="#ffcc80", dash=(3, 3), tags="ov")
            d = self.drag
            if d and d.get("kind") == "band" and d.get("moved"):
                c.create_rectangle(d["x0"], d["y0"], d["x1"], d["y1"], outline="#00e5ff", dash=(3, 3), tags="ov")


        def export_sets(self):
            p = filedialog.asksaveasfilename(title="Export pose sets", defaultextension=".json", initialfile="tore_pose_sets.json",
                                             filetypes=[("JSON", "*.json")])
            if p:
                with open(p, "w", encoding="utf-8") as fh:
                    json.dump(full_pose_sets(), fh, indent=1)
                self.note("Pose sets written to %s" % p)


    Editor().mainloop()


if __name__ == "__main__":
    run_gui(sys.argv[1] if len(sys.argv) > 1 else None)
