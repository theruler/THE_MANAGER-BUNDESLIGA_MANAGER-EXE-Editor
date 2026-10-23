import math
import os
import struct

from game_utils import clamp
from geometry import (
    BALL_Y_MIN, FIELD_X0, MAX_Y, ORIG_FW, ORIG_SCROLL_MAX_X, ORIG_SCROLL_MAX_Y, ORIG_WIN_H, ORIG_WIN_W, w2s,
    Y_OFFSET,
)
from lang import tr
from sprite_data import BALL_ROT


REPLAY_MAX_SECS = 20 # Maximum number of recent match seconds retained in the replay buffer.


TORE_SIG = b"BM-Ed1.3-WK\0" # TORE file signature; keep unchanged unless intentionally changing format compatibility.


TORE_N_REC = 27 # TORE record layout constant; change only with matching encoder and decoder updates.


TORE_FPS = 20 # Frame rate used for TORE replay serialization.


TORE_CAM_DEAD = (4, 3) # TORE camera dead-zone values stored for replay compatibility.


TORE_CAM_STEP = (22, 3) # TORE camera movement increments stored for replay compatibility.


TORE_LEAD_SECS = 1.0 # Seconds of context retained before a replay event.


TORE_MAX_FRAMES = 256 # Maximum number of frames accepted in one TORE record.


TORE_RANK = {"S": 0, "B": 1, "P": 2, "L": 3, "R": 3} # Sprite-class ordering used to serialize overlapping replay records.


TORE_GOAL_Y = 28 # Goal-line coordinate encoded into normalized TORE frames.


DE_MAP = {"[": "\u00c4", "\\": "\u00d6", "]": "\u00dc", "{": "\u00e4", "|": "\u00f6", "}": "\u00fc"} # Character substitutions for German text in TORE files.


DE_TABLE = {ord(k): v for k, v in DE_MAP.items()} # Precomputed Unicode translation table for the German TORE mapping.


DE_INV = {v: k for k, v in DE_MAP.items()} # Reverse translation table used when writing German TORE text.


def tore_cls(sid): # Map a sprite ID to its TORE replay record class.
    if 145 <= sid <= 147:
        return "S"
    if 142 <= sid <= 144:
        return "B"
    if sid == 1000:
        return "L"
    if sid == 1024:
        return "R"
    return "P"


def tore_normalize(snap): # Normalize a game snapshot into the coordinate and record format used by TORE.
    pl, rf, bl = snap[:3]

    def px(x): # Clamp and convert a screen x-coordinate into a TORE replay coordinate.
        return int(round(clamp(x - FIELD_X0, 6, ORIG_FW - 6)))

    def py(y): # Clamp and convert a screen y-coordinate into a TORE replay coordinate.
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


def tore_order(recs): # Sort replay records in the order required by the TORE renderer.
    sh = next((r for r in recs if tore_cls(r[2]) == "S"), None)

    def key(i): # Build the sort key for one normalized TORE record.
        x, y, sid = recs[i]
        c = tore_cls(sid)
        k = y
        if c == "S":
            k = y - 4
        elif c == "B":
            k = (sh[1] - 4) if sh else y
        return (k, TORE_RANK[c], i)
    return sorted(range(len(recs)), key=key)


def tore_pack(frames, events=None, author=""): # Encode replay frames and event metadata into TORE bytes.
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


def tore_build(snaps, author="", fps_src=60, fps=None): # Build TORE replay frames from captured snapshots.
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


def tore_next_path(folder, ext="V"): # Choose the next available filename for a replay file.
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


class ReplayMixin: # TORE replay capture, serialization, playback, and saving.

    def start_replay(self, end_tick=None, secs=None): # Start replay capture for the specified number of seconds.
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

    def save_tore(self, snaps): # Save captured snapshots as a TORE replay file.
        try:
            path = tore_next_path(self.tore_dir)
            with open(path, "wb") as fh:
                fh.write(tore_build(snaps, self.last_scorer, fps=getattr(self.args, "tore_fps", None)))
            self.say(tr("msg.replay_saved", path=path), (150, 230, 160), 4)
            return path
        except (OSError, ValueError) as ex:
            self.say(tr("msg.save_failed", reason=ex), (255, 150, 120), 4)
            return None

    def replay_step(self): # Advance replay capture or playback by one simulation step.
        r = self.replay
        r["i"] += 1
        if r["i"] >= len(r["frames"]):
            self.stop_replay()
        else:
            self.cam[0], self.cam[1] = r["frames"][r["i"]][2]

    def stop_replay(self): # Stop replay activity and finalize any pending recording.
        self.replay = None
        self.update_cam(0.0, True)

    def snapshot(self): # Capture a replay snapshot of players, referee, ball, and camera.
        b = self.ball
        bpx, bgy = w2s(b.wx, b.wv)
        if b.owner is not None and b.owner.role != "GK":
            bgy += 1.0
        r = self.ref
        return (tuple((p.sx, p.sy - p.lift, p.sid, p.state != "out") for p in self.players),
                (r.sx, r.sy, r.sid, r.card),
                (bpx, bgy, b.z, BALL_ROT[int(b.spin / 3.0) % len(BALL_ROT)]),
                tuple(f.screen() for f in self.flags))
