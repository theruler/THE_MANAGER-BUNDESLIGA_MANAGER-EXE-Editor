import array
import math
import os
import random
import struct
import threading
import time
import wave

import pygame

from game_utils import clamp

SR = 22050 # Sample rate used to generate procedural sound effects, in samples per second.
TAU = 2.0 * math.pi
AUDIO_VERSION = "v6" # Sound-cache version; change it when generated sound definitions become incompatible.
HORNS = ("horn_vuvu1", "horn_vuvu2", "horn_vuvu3", "horn_air1", "horn_air2", "horn_bugle", "horn_vuvu4", "horn_vuvu5", "horn_air3", "horn_air4", "horn_fanfare") # Names of procedural horn sounds.
CHANTS = ("chant1", "chant2", "chant3", "chant4", "chant5", "chant6", "chant7", "chant8", "chant9", "chant10") # Names of crowd-chant sounds.
SHOUTS = ("shout1", "shout2", "shout3") # Names of short crowd or player shouts included in the sound library.
SOUND_NAMES = (  # Complete set of named sounds that the audio system can generate or play.
    "kick", "kick_hard", "head", "bounce", "tackle", "whistle", "whistle_long", "whistle_end", "post", "bar", "net", "stands",
    "amb", "amb2", *CHANTS[:5], "drums1", "drums2", "swell1", "swell2",
    "cheer1", "cheer2", "cheer3", "oh1", "oh2", "oh3", "oh4", "oh5", "boo1", "boo2", "jeer", *SHOUTS,
    "applause1", "applause2", *HORNS[:6], *CHANTS[5:], *HORNS[6:],
)


def _norm(x, peak=0.9): # Normalize a sample buffer against the requested peak level.
    m = max(1e-9, max(abs(v) for v in x))
    k = peak / m
    return [v * k for v in x]


def _formant_table(f1, f2, f3, base=110.0, n=512): # Build a lookup table for the requested vocal formant frequencies.
    tbl = [0.0] * n
    for k in range(1, 34):
        f = k * base
        a = 1.0 / k ** 0.8
        a *= 1 + 2.4 * math.exp(-((f - f1) / (0.35 * f1 + 60)) ** 2) + 1.7 * math.exp(-((f - f2) / (0.3 * f2 + 80)) ** 2)\
            + 0.5 * math.exp(-((f - f3) / 500.0) ** 2)
        for i in range(n):
            tbl[i] += a * math.sin(TAU * k * i / n)
    return _norm(tbl, 1.0)


def _harm_table(weights, n=512): # Build a harmonic lookup table from the supplied partial weights.
    tbl = [0.0] * n
    for k, a in weights:
        for i in range(n):
            tbl[i] += a * math.sin(TAU * k * i / n)
    return _norm(tbl, 1.0)


VOC_START, VOC_END = 0x5A3A, 0xCBD5 # Crowd chorus inside the plain DIGI.VOC archive (END is inclusive).
ORIG_MIN, ORIG_MAX = 0.1, 1.0 # Crowd-loop level range, relative to the main volume.
ORIG_UP, ORIG_DOWN = 1.8, 0.45 # Maximum level change per second when the crowd gets louder / quieter.
ORIG_AMB_DUCK = 0.4 # The procedural crowd bed is lowered to this factor while the original crowd loop is playing.
ORIG_MODE_LEVEL = {"goal": 1.0, "full": 0.7, "walkon": 0.6, "foul": 0.5, "restart": 0.35, "outball": 0.35, "subs": 0.2, "injury": 0.15, "half": 0.12} # Crowd level per match mode ("play" follows the action intensity).
ORIG_BOOST = {"goal": (1.0, 6.0), "near": (0.85, 2.5), "save": (0.7, 2.0), "corner": (0.75, 3.0), "tension": (0.8, 3.0),
              "foul": (0.6, 1.5), "card": (0.7, 2.0), "start": (0.9, 3.0), "whistle_end": (0.9, 4.0)} # Match events -> (minimum crowd level, seconds it is held).
FADE_SECS = 0.6 # Fade-out time of the original sounds (option turned OFF, match start).
MUSIC_VOL = 0.8 # Intro-music level, relative to the main volume.
MUSIC_CHUNK = 1.0 # Seconds of PCM per chunk handed to the mixer.
MUSIC_AHEAD = 4 # Chunks the synthesizer thread may render ahead of the playback position.
MUSIC_MAX_SECS = 360 # Safety limit for the rendered song length.
CMF_BEND_RANGE = 2.0 # Pitch-bend range in semitones.


def _voc_conv(data, codec, bits): # Convert VOC sample bytes into floats in -1..1.
    if bits == 16:
        n = len(data) // 2
        return [v / 32768.0 for v in struct.unpack("<%dh" % n, bytes(data[:2 * n]))]
    if codec == 0:
        return [(b - 128) / 128.0 for b in data]
    raise ValueError("VOC codec %d not supported" % codec)


def decode_voc(blob): # Decode a Creative Voice File (with or without header) into (sample rate, mono floats).
    blob = bytes(blob)
    pos = 0
    if blob[:19] == b"Creative Voice File":
        pos = int.from_bytes(blob[20:22], "little") or 26
    rate, chans, bits, codec, pend, first = 0, 1, 8, 0, None, True
    out = []

    def mono(vals): # Mix an interleaved stereo block down to mono.
        return [(vals[i] + vals[i + 1]) * 0.5 for i in range(0, len(vals) - 1, 2)] if chans == 2 else vals

    while pos + 4 <= len(blob):
        t = blob[pos]
        if t == 0:
            break
        ln = int.from_bytes(blob[pos + 1:pos + 4], "little")
        if first and (not 1 <= t <= 9 or ln > len(blob) - pos):
            raise ValueError("not a VOC block stream")
        first = False
        body = blob[pos + 4:pos + 4 + ln]
        pos += 4 + ln
        if t == 1 and len(body) > 2:
            codec, bits = body[1], 8
            rate, chans = pend if pend else (1000000.0 / (256 - body[0]), 1)
            pend = None
            out += mono(_voc_conv(body[2:], codec, bits))
        elif t == 2:
            out += mono(_voc_conv(body, codec, bits))
        elif t == 3 and len(body) >= 2:
            out += [0.0] * (int.from_bytes(body[:2], "little") + 1)
        elif t == 8 and len(body) >= 4:
            ch = body[3] + 1
            pend = (256000000.0 / (ch * (65536 - int.from_bytes(body[:2], "little"))), ch)
        elif t == 9 and len(body) > 12:
            rate, bits, chans = float(int.from_bytes(body[:4], "little")), body[4], body[5]
            codec = int.from_bytes(body[6:8], "little")
            out += mono(_voc_conv(body[12:], codec, bits))
    if not out or not 4000 <= rate <= 96000:
        raise ValueError("VOC without usable audio")
    return rate, out


def resample(smp, r_in, r_out): # Linear-interpolation resampler.
    if abs(r_in - r_out) < 1.0:
        return list(smp)
    step, last = r_in / r_out, len(smp) - 1
    out = []
    for i in range(int(len(smp) * r_out / r_in)):
        x = i * step
        j = int(x)
        a = smp[j]
        out.append(a + ((smp[j + 1] if j < last else a) - a) * (x - j))
    return out


def loop_crossfade(smp, xf): # Make a buffer loop without a click: the tail is blended into the head.
    n = len(smp)
    xf = max(0, min(xf, n // 4))
    if xf == 0:
        return list(smp)
    out = smp[:n - xf]
    for i in range(xf):
        w = i / xf
        out[i] = out[i] * w + smp[n - xf + i] * (1.0 - w)
    return out


# ---------- OPL2 (YM3812) software synthesizer ----------
OPL_RATE = 49716.0 # Native sample rate of the chip; it defines the F-number -> Hz relation.
_N = 1024 # Waveform table length.
_SINE = [math.sin(TAU * i / _N) for i in range(_N)]
_WAVES = (_SINE, [max(0.0, v) for v in _SINE], [abs(v) for v in _SINE], [abs(_SINE[i]) if (i & 511) < 256 else 0.0 for i in range(_N)])
_MULT = (0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 12, 12, 15, 15)
_KSL_DB = tuple(v * 0.28125 for v in (0, 32, 40, 45, 48, 51, 53, 55, 56, 58, 59, 60, 61, 62, 63, 64))
_KSL_K = (0.0, 1.0, 0.5, 2.0) # Key-scale-level register value -> 3 dB/oct multiplier.
_FB_CYC = (0.0, 1 / 32., 1 / 16., 1 / 8., 1 / 4., 1 / 2., 1.0, 2.0) # Feedback depth, in cycles.
MOD_DEPTH = 2.0 # Modulator output -> carrier phase offset, in cycles (4*pi radians).
_ENV_FLOOR = 90.0 # Attenuation (dB) beyond which an operator counts as silent.


def _op_rate(r, rof): # Effective OPL rate (0..63) from the 4-bit register rate and the key-scale offset.
    return 0 if r == 0 else min(63, 4 * r + rof)


class _Op: # One FM operator: phase, parameters and ADSR envelope (attenuation in dB).
    __slots__ = ("ph", "inc", "mult", "wave", "tl", "ksl", "ksr", "am", "vib", "egt", "ar", "dr", "sl", "rr",
                 "stage", "att", "amp", "extra", "r_a", "r_d", "r_r", "ksl_db")

    def __init__(self):
        self.ph = self.inc = self.tl = self.sl = self.amp = self.extra = self.ksl_db = self.r_a = self.r_d = self.r_r = 0.0
        self.mult, self.wave, self.att = 1.0, _SINE, 96.0
        self.ksl = self.ksr = self.am = self.vib = self.ar = self.dr = self.rr = self.stage = 0
        self.egt = 1

    def load(self, r20, r40, r60, r80, re0): # Program the operator from the OPL registers 0x20/0x40/0x60/0x80/0xE0.
        self.am, self.vib, self.egt, self.ksr, self.mult = (r20 >> 7) & 1, (r20 >> 6) & 1, (r20 >> 5) & 1, (r20 >> 4) & 1, _MULT[r20 & 15]
        self.ksl, self.tl = (r40 >> 6) & 3, (r40 & 63) * 0.75
        self.ar, self.dr = r60 >> 4, r60 & 15
        sl = r80 >> 4
        self.sl, self.rr = 93.0 if sl == 15 else sl * 3.0, r80 & 15
        self.wave = _WAVES[re0 & 3]

    def retune(self, hz, fnum, block, fs): # Recompute increment, key scaling and the envelope rates for a new pitch.
        self.inc = hz * self.mult / fs
        a = _KSL_DB[fnum >> 6] - 3.0 * (7 - block)
        self.ksl_db = max(0.0, a) * _KSL_K[self.ksl]
        rof = ((block << 1) | (fnum >> 9)) >> (0 if self.ksr else 2)
        ea = _op_rate(self.ar, rof)
        self.r_a = 0.0 if ea == 0 else (-1.0 if ea >= 60 else math.log(96.0 / 0.3) / (2.82624 * 2.0 ** (-(ea - 4) / 4.0)))
        ed, er = _op_rate(self.dr, rof), _op_rate(max(1, self.rr), rof)
        self.r_d = 0.0 if ed == 0 else 96.0 / (39.28 * 2.0 ** (-(min(ed, 63) - 4) / 4.0))
        self.r_r = 96.0 / (39.28 * 2.0 ** (-(min(er, 63) - 4) / 4.0))

    def key_on(self): # Restart the operator: phase to zero, envelope into the attack stage.
        self.ph = 0.0
        self.stage = 1
        if self.r_a < 0:
            self.att, self.stage = 0.0, 2

    def key_off(self): # Enter the release stage.
        if self.stage:
            self.stage = 4

    def step(self, dt): # Advance the envelope by dt seconds and return the attenuation in dB.
        st = self.stage
        if st == 0:
            return 96.0
        if st == 1:
            if self.r_a > 0:
                self.att *= math.exp(-self.r_a * dt)
                if self.att < 0.3:
                    self.att, self.stage = 0.0, 2
        elif st == 2:
            self.att += self.r_d * dt
            if self.att >= self.sl:
                self.att, self.stage = self.sl, 3
        elif st == 3:
            if not self.egt:
                self.att += self.r_r * dt
        else:
            self.att += self.r_r * dt
        if self.att >= _ENV_FLOOR and self.stage >= 3:
            self.att, self.stage = 96.0, 0
        return self.att


class _Voice: # One OPL channel: modulator + carrier with connection and feedback.
    __slots__ = ("m", "c", "conn", "fbk", "y1", "y2", "hz", "fnum", "block", "midi", "note", "age", "gain")

    def __init__(self):
        self.m, self.c = _Op(), _Op()
        self.conn, self.fbk, self.y1, self.y2 = 0, 0.0, 0.0, 0.0
        self.hz, self.fnum, self.block, self.midi, self.note, self.age, self.gain = 0.0, 0, 0, -1, -1, 0, 1.0

    def load_patch(self, p): # Load a 16-byte CMF/SBI instrument.
        self.m.load(p[0], p[2], p[4], p[6], p[8])
        self.c.load(p[1], p[3], p[5], p[7], p[9])
        self.conn = p[10] & 1
        self.fbk = _FB_CYC[(p[10] >> 1) & 7] * 0.5

    def set_pitch(self, hz, fs): # Quantize hz to the chip's block / F-number pair and retune both operators.
        hz = max(8.0, min(hz, 6200.0))
        block = 0
        while block < 7 and hz * (1 << (20 - block)) / OPL_RATE >= 1024:
            block += 1
        fnum = min(1023, int(round(hz * (1 << (20 - block)) / OPL_RATE)))
        self.fnum, self.block = fnum, block
        self.hz = fnum * OPL_RATE / (1 << (20 - block))
        self.m.retune(self.hz, fnum, block, fs)
        self.c.retune(self.hz, fnum, block, fs)

    def key_on(self):
        self.m.key_on()
        self.c.key_on()
        self.y1 = self.y2 = 0.0

    def key_off(self):
        self.m.key_off()
        self.c.key_off()

    def active(self): # True while the voice can still produce sound.
        return self.c.stage != 0 or (self.conn and self.m.stage != 0)


def _amp(db): # Attenuation in dB -> linear amplitude.
    return 10.0 ** (-db * 0.05) if db < _ENV_FLOOR else 0.0


class Opl2: # Nine melodic channels or six melodic + five rhythm instruments, rendered in short blocks.
    def __init__(self, fs):
        self.fs, self.v, self.rhythm, self.t = float(fs), [_Voice() for _ in range(9)], False, 0.0
        self.tdepth, self.vcents = 1.0, 7.0 # Tremolo depth (dB) and vibrato depth (cents).

    def idle(self): # True when every voice has died away.
        for k, v in enumerate(self.v):
            if (v.m.stage or v.c.stage) if (self.rhythm and k in (7, 8)) else v.active():
                return False
        return True

    def render(self, n, blk): # Add n samples of the whole chip to blk (list of floats).
        dt = n / self.fs
        self.t += dt
        fr = (self.t * 3.7) % 1.0
        trem = self.tdepth * (2 * fr if fr < 0.5 else 2 * (1 - fr))
        vf = 2.0 ** (math.sin(TAU * self.t * 6.1) * self.vcents / 1200.0)
        top = 6 if self.rhythm else 9
        for k in range(top):
            v = self.v[k]
            if v.active():
                self._run_voice(v, n, blk, dt, trem, vf)
        if self.rhythm:
            v7, v8 = self.v[7], self.v[8]
            if v7.m.stage or v7.c.stage or v8.m.stage or v8.c.stage:
                self._run_rhythm(v7, v8, n, blk, dt, trem)
            v6 = self.v[6]
            if v6.active():
                self._run_voice(v6, n, blk, dt, trem, vf)

    def _run_voice(self, v, n, blk, dt, trem, vf): # Render one two-operator voice.
        m, c = v.m, v.c
        ma1 = _amp(m.step(dt) + m.tl + m.ksl_db + m.extra + (trem if m.am else 0.0)) * (v.gain if v.conn else 1.0)
        ca1 = _amp(c.step(dt) + c.tl + c.ksl_db + c.extra + (trem if c.am else 0.0)) * v.gain
        ma, ca = m.amp, c.amp
        dm, dc = (ma1 - ma) / n, (ca1 - ca) / n
        mp, cp = m.ph, c.ph
        mi = m.inc * (vf if m.vib else 1.0)
        ci = c.inc * (vf if c.vib else 1.0)
        mw, cw, fbk, y1, y2 = m.wave, c.wave, v.fbk, v.y1, v.y2
        if v.conn:
            for i in range(n):
                ma += dm
                ca += dc
                mp += mi
                cp += ci
                y = mw[int((mp + (y1 + y2) * fbk) * 1024) & 1023] * ma
                y2, y1 = y1, y
                blk[i] += y + cw[int(cp * 1024) & 1023] * ca
        else:
            for i in range(n):
                ma += dm
                ca += dc
                mp += mi
                cp += ci
                y = mw[int((mp + (y1 + y2) * fbk) * 1024) & 1023] * ma
                y2, y1 = y1, y
                blk[i] += cw[int((cp + y * MOD_DEPTH) * 1024) & 1023] * ca
        m.ph, c.ph, m.amp, c.amp, v.y1, v.y2 = mp % 1.0, cp % 1.0, ma1, ca1, y1, y2

    def _run_rhythm(self, v7, v8, n, blk, dt, trem): # Hi-hat, snare, tom and top cymbal (phase / noise formulas of the YM3812 rhythm section).
        hm, sc, tm, tc = v7.m, v7.c, v8.m, v8.c
        ops = (hm, sc, tm, tc)
        a1 = [_amp(o.step(dt) + o.tl + o.ksl_db + o.extra + (trem if o.am else 0.0)) for o in ops]
        a0 = [o.amp for o in ops]
        d = [(a1[k] - a0[k]) / n for k in range(4)]
        ha, sa, ta, ca = a0
        dh, ds, dt_, dca = d
        hp, tp, cp = hm.ph, tm.ph, tc.ph
        hi, ti, ci = hm.inc, tm.inc, tc.inc
        hw, sw, tw, cw = hm.wave, sc.wave, tm.wave, tc.wave
        rb = random.getrandbits
        for i in range(n):
            ha += dh
            sa += ds
            ta += dt_
            ca += dca
            hp += hi
            tp += ti
            cp += ci
            p7, p8 = int(hp * 1024) & 1023, int(cp * 1024) & 1023
            res1 = (((p7 >> 2) ^ (p7 >> 7)) | (p7 >> 3)) & 1
            res2 = ((p8 >> 3) ^ (p8 >> 5)) & 1
            noise = rb(1)
            ph = 0x234 if res1 else 0xD0
            if res2:
                ph = 0x240
            if ph & 0x200:
                if noise:
                    ph = 0x2D0
            elif noise:
                ph = 0x34
            out = hw[ph] * ha
            ph = 0x200 if (p7 >> 8) & 1 else 0x100
            if noise:
                ph ^= 0x100
            out += sw[ph] * sa
            out += tw[int(tp * 1024) & 1023] * ta
            out += cw[0x300 if (res1 or res2) else 0x100] * ca
            blk[i] += out * 1.5
        hm.ph, tm.ph, tc.ph = hp % 1.0, tp % 1.0, cp % 1.0
        for o, a in zip(ops, a1):
            o.amp = a


class CmfSynth: # Creative Music File player driving the OPL2 emulation (MIDI-like events, CMF controllers 0x67-0x69).
    GAIN = 0.22 # Mix level of the whole chip.

    def __init__(self, data, fs):
        if data[:4] != b"CTMF":
            raise ValueError("CTMF header missing")
        u16 = lambda o: data[o] | (data[o + 1] << 8)
        ver, ioff, moff, self.tps = u16(4), u16(6), u16(8), u16(12)
        if self.tps < 8:
            self.tps = 120
        count = data[0x24] if ver < 0x0101 else u16(0x24)
        if moff > ioff:
            count = min(count, (moff - ioff) // 16)
        self.patches = [bytes(data[ioff + 16 * i: ioff + 16 * i + 16]) for i in range(count)]
        self.patches = [p for p in self.patches if len(p) == 16] or [bytes(16)]
        self.data, self.pos, self.fs = bytes(data), moff, float(fs)
        self.opl = Opl2(fs)
        self.prog, self.vol, self.bend, self.fine = [0] * 16, [100] * 16, [8192] * 16, [0.0] * 16
        self.status, self.acc, self.age = 0, 0.0, 0
        self.finished = self.done = False
        self.tail = 0
        self.wait = self._vlq()

    def _vlq(self): # Read a MIDI variable-length quantity.
        v, d = 0, self.data
        for _ in range(4):
            if self.pos >= len(d):
                self.finished = True
                return 0
            b = d[self.pos]
            self.pos += 1
            v = (v << 7) | (b & 0x7F)
            if not b & 0x80:
                break
        return v

    def _freq(self, ch, note): # MIDI note (+ CMF transpose and pitch bend) -> Hz.
        semi = note - 69 + self.fine[ch] + (self.bend[ch] - 8192) / 8192.0 * CMF_BEND_RANGE
        return 440.0 * 2.0 ** (semi / 12.0)

    def _db(self, ch, vel): # Velocity and channel volume -> attenuation in dB.
        return -20.0 * math.log10(max(0.01, (vel / 127.0) * (self.vol[ch] / 127.0)))

    def _patch(self, ch):
        p = self.prog[ch]
        return self.patches[p if p < len(self.patches) else 0]

    def _alloc(self): # Choose a voice for a new note: idle first, then the quietest releasing one, then the oldest.
        top = 6 if self.opl.rhythm else 9
        vs = self.opl.v[:top]
        for v in vs:
            if not v.active():
                return v
        rel = [v for v in vs if v.c.stage == 4]
        return max(rel, key=lambda v: v.c.att) if rel else min(vs, key=lambda v: v.age)

    def _note_on(self, ch, note, vel):
        if vel == 0:
            return self._note_off(ch, note)
        fs, p = self.fs, self._patch(ch)
        db = self._db(ch, vel)
        if self.opl.rhythm and ch >= 11:
            v = self.opl.v
            if ch == 11: # bass drum: a normal two-operator voice on channel 6
                t = v[6]
                t.load_patch(p)
                t.gain = 2.0
                t.m.extra, t.c.extra = (db if t.conn else 0.0), db
                t.set_pitch(self._freq(ch, note), fs)
                t.key_on()
                return
            t, op = {12: (v[7], v[7].c), 13: (v[8], v[8].m), 14: (v[8], v[8].c), 15: (v[7], v[7].m)}[ch]
            if op is t.c:
                op.load(p[1], p[3], p[5], p[7], p[9])
            else:
                op.load(p[0], p[2], p[4], p[6], p[8])
            op.extra = db
            t.set_pitch(self._freq(ch, note), fs)
            op.key_on()
            return
        v = self._alloc()
        self.age += 1
        v.load_patch(p)
        v.gain, v.midi, v.note, v.age = 1.0, ch, note, self.age
        v.m.extra, v.c.extra = (db if v.conn else 0.0), db
        v.set_pitch(self._freq(ch, note), fs)
        v.key_on()

    def _note_off(self, ch, note):
        v = self.opl.v
        if self.opl.rhythm and ch >= 11:
            {11: v[6], 12: v[7].c, 13: v[8].m, 14: v[8].c, 15: v[7].m}[ch].key_off()
            return
        for x in v[:6 if self.opl.rhythm else 9]:
            if x.midi == ch and x.note == note and x.c.stage in (1, 2, 3):
                x.key_off()
                x.midi = -1
                return

    def _controller(self, ch, cc, val):
        if cc == 7:
            self.vol[ch] = val
        elif cc == 0x67:
            on = val != 0
            if on != self.opl.rhythm:
                for x in self.opl.v[6:9]:
                    x.m.stage = x.c.stage = 0
                    x.m.att = x.c.att = 96.0
                self.opl.rhythm = on
        elif cc in (0x68, 0x69):
            self.fine[ch] = (val if cc == 0x68 else -val) / 128.0

    def _repitch(self, ch): # Pitch bend / transpose changed: retune the sounding notes of the channel.
        for x in self.opl.v:
            if x.midi == ch and x.c.stage in (1, 2, 3):
                x.set_pitch(self._freq(ch, x.note), self.fs)

    def _event(self): # Parse and execute one event.
        d = self.data
        if self.pos >= len(d):
            self.finished = True
            return
        b = d[self.pos]
        if b & 0x80:
            self.status = b
            self.pos += 1
        st = self.status
        if st == 0xFF:
            if self.pos + 1 >= len(d):
                self.finished = True
                return
            typ = d[self.pos]
            self.pos += 1
            ln = self._vlq()
            self.pos += ln
            if typ == 0x2F:
                self.finished = True
            return
        if st in (0xF0, 0xF7):
            self.pos += self._vlq()
            return
        if st < 0x80 or st >= 0xF0:
            self.pos += 1
            return
        ch, kind = st & 15, st >> 4
        n = 1 if kind in (0xC, 0xD) else 2
        a = d[self.pos] if self.pos < len(d) else 0
        c = d[self.pos + 1] if n == 2 and self.pos + 1 < len(d) else 0
        self.pos += n
        if kind == 9:
            self._note_on(ch, a & 127, c & 127)
        elif kind == 8:
            self._note_off(ch, a & 127)
        elif kind == 0xB:
            self._controller(ch, a & 127, c & 127)
            if a in (0x68, 0x69):
                self._repitch(ch)
        elif kind == 0xC:
            self.prog[ch] = a & 127
        elif kind == 0xE:
            self.bend[ch] = (a & 127) | ((c & 127) << 7)
            self._repitch(ch)

    def render(self, n=32): # Render n samples; returns the block or None once the song and its tail have ended.
        if self.done:
            return None
        if not self.finished:
            self.acc += n * self.tps / self.fs
            while not self.finished and self.acc >= self.wait:
                self.acc -= self.wait
                self._event()
                if self.finished:
                    break
                self.wait = self._vlq()
            if self.finished:
                for x in self.opl.v:
                    x.key_off()
                    x.m.key_off()
                    x.c.key_off()
        blk = [0.0] * n
        self.opl.render(n, blk)
        if self.finished:
            self.tail += n
            if self.tail > 2.5 * self.fs or self.opl.idle():
                self.done = True
        return blk


class Audio: # Procedural match sounds, audio caching, mixing, and playback.
    def __init__(self, enabled=True, cache_dir=None, voc_path=None, cmf_path=None): # Initialize audio generation, cache storage, playback channels, and mute state.
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
        self.voc_path, self.cmf_path = voc_path, cmf_path # Original assets found at start-up (DIGI.VOC crowd, BM2TITLE.CMF intro music).
        self.orig_on = bool(voc_path or cmf_path) # "Original audio" option: ON by default when something was found.
        self.master_vol = 1.0 # Main volume the original-audio levels are relative to.
        self.voc_snd, self.voc_failed, self.cmf_failed = None, False, False
        self.orig_vol, self.boost_lvl, self.boost_t = 0.0, 0.0, 0.0
        self.intro_active, self.mus_fade = False, 0.0
        self._mus_chunks, self._mus_idx, self._mus_done, self._mus_playing = [], 0, False, False
        self._mus_thread, self._mus_run = None, threading.Event()
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
            pygame.mixer.set_reserved(6)
            self.amb_ch = pygame.mixer.Channel(0)
            self.chant_ch = pygame.mixer.Channel(1)
            self.acc_ch = pygame.mixer.Channel(2)
            self.amb2_ch = pygame.mixer.Channel(3)
            self.voc_ch = pygame.mixer.Channel(4)
            self.mus_ch = pygame.mixer.Channel(5)
            self.ok = True
        except Exception:
            self.ok = False
            return
        threading.Thread(target=self._build, daemon=True).start()
        if self.voc_path:
            threading.Thread(target=self._load_voc, daemon=True).start()

    @property
    def orig_available(self): # True when the mixer works and at least one original file was found at start-up.
        return bool(self.ok and ((self.voc_path and not self.voc_failed) or (self.cmf_path and not self.cmf_failed)))

    def set_original(self, on): # Switch the "Original audio" option; the original sounds fade out when it is turned off.
        self.orig_on = bool(on) and self.orig_available
        if self.ok and not self.orig_on:
            if self.voc_ch.get_busy():
                self.voc_ch.fadeout(int(FADE_SECS * 1000))
            self._music_stop(fade=True)

    def _stereo(self, pcm): # Duplicate a mono PCM buffer when the mixer is stereo.
        if self.chn == 2:
            st = array.array("h", [0]) * (2 * len(pcm))
            st[0::2] = pcm
            st[1::2] = pcm
            return st
        return pcm

    def _load_voc(self): # Decode the crowd chorus of DIGI.VOC straight into RAM, resampled to the mixer rate and loop-ready.
        try:
            with open(self.voc_path, "rb") as f:
                blob = f.read()[VOC_START:VOC_END + 1]
            if len(blob) < 64:
                raise ValueError("DIGI.VOC too short for the chorus range")
            try:
                rate, smp = decode_voc(blob)
            except ValueError: # No VOC blocks at that offset: treat the range as raw unsigned 8-bit audio.
                rate, smp = 11025.0, [(b - 128) / 128.0 for b in blob]
                print("audio: DIGI.VOC: range is not a block stream, using raw 8-bit 11025 Hz")
            smp = loop_crossfade(resample(smp, rate, SR), int(0.05 * SR))
            self.voc_snd = pygame.mixer.Sound(buffer=self._stereo(self._pcm(smp)).tobytes())
        except Exception as ex:
            self.voc_failed = True
            print("audio: DIGI.VOC:", ex)

    # ---------- intro music (BM2TITLE.CMF through the OPL2 emulation) ----------
    def _music_worker(self): # Thread: parse the CMF, render it with the OPL2 emulation and publish 1-second PCM chunks.
        try:
            with open(self.cmf_path, "rb") as f:
                data = f.read()
            i = data.find(b"CTMF")
            if i < 0:
                raise ValueError("no CTMF header in file")
            fs = SR
            synth = CmfSynth(data[i:], fs)
            per_chunk, buf, total = int(MUSIC_CHUNK * fs), [], 0
            while total < MUSIC_MAX_SECS * fs:
                while not self._mus_run.is_set() or len(self._mus_chunks) - self._mus_idx > MUSIC_AHEAD:
                    time.sleep(0.05)
                fin = False
                for _ in range(16):
                    blk = synth.render(32)
                    if blk is None:
                        fin = True
                        break
                    buf += blk
                    total += 32
                if len(buf) >= per_chunk or fin:
                    k = CmfSynth.GAIN * 32767
                    pcm = array.array("h", [-32767 if v * k < -32767 else 32767 if v * k > 32767 else int(v * k) for v in buf])
                    if pcm:
                        self._mus_chunks.append(self._stereo(pcm).tobytes())
                    buf = []
                if fin:
                    break
                time.sleep(0.003) # Leave the GIL to the game loop.
            self._mus_done = True
        except Exception as ex:
            self.cmf_failed = True
            print("audio: BM2TITLE.CMF:", ex)

    def _music_start(self): # Start (or resume) the synthesizer thread and the playback of the intro music.
        if not (self.cmf_path and not self.cmf_failed):
            return
        self._mus_run.set()
        if self._mus_thread is None:
            self._mus_thread = threading.Thread(target=self._music_worker, daemon=True)
            self._mus_thread.start()
        if self.mus_fade > 0 and self._mus_playing: # Turned back ON while fading out: resume at full level.
            self.mus_fade = 0.0
            self.mus_ch.set_volume(clamp(MUSIC_VOL * self.master_vol, 0.0, 1.0))
        if not self._mus_playing:
            if len(self._mus_chunks) < 2 and not self._mus_done:
                return # Wait for a small head start.
            self._mus_playing, self._mus_idx = True, 0
            self.mus_ch.set_volume(0.0)
            self.mus_fade = 0.0
        self._music_pump()

    def _music_pump(self): # Keep one chunk queued behind the playing one; loop the finished song from the start.
        if not self._mus_playing or self.mus_fade > 0 or self.mus_ch.get_queue() is not None:
            return
        n = len(self._mus_chunks)
        if self._mus_idx >= n:
            if not (self._mus_done and n):
                return
            self._mus_idx = 0
        snd = pygame.mixer.Sound(buffer=self._mus_chunks[self._mus_idx])
        self._mus_idx += 1
        if self.mus_ch.get_busy():
            self.mus_ch.queue(snd)
        else:
            self.mus_ch.play(snd)
        self.mus_ch.set_volume(clamp(MUSIC_VOL * self.master_vol, 0.0, 1.0))

    def _music_stop(self, fade=False): # Stop the intro music (optionally with a fade); the synthesizer thread pauses, the rendered part stays in RAM.
        self._mus_run.clear()
        if fade and self._mus_playing and self.ok and self.mus_ch.get_busy():
            if self.mus_fade <= 0:
                self.mus_fade = 1.0 # _music_fade_step() lowers the level and then stops the channel.
            return
        self._mus_playing, self.mus_fade = False, 0.0
        if self.ok:
            self.mus_ch.stop()
            self.mus_ch.stop() # Some pygame versions start the queued chunk after the first stop().

    def _music_fade_step(self, dt): # Advance a running music fade-out (called from the INTRO and the match update).
        if self.mus_fade <= 0:
            return
        self.mus_fade -= dt / FADE_SECS
        if self.mus_fade <= 0:
            self._music_stop()
        else:
            self.mus_ch.set_volume(clamp(MUSIC_VOL * self.master_vol * self.mus_fade, 0.0, 1.0))

    def intro_tick(self, dt): # Called every frame while the INTRO / OPTIONS pages are shown.
        if not self.ok or self.muted:
            return
        self.intro_active = True
        self._music_fade_step(dt)
        if self.orig_on and self.cmf_path:
            self._music_start()
        elif self._mus_playing:
            self._music_stop(fade=True)

    def _leave_intro(self): # The match starts: fade the music out.
        self.intro_active = False
        self._music_stop(fade=True)

    # ---------- original crowd loop (DIGI.VOC) ----------
    def _boost(self, lvl, secs): # Hold the crowd loop at (at least) lvl for secs seconds.
        self.boost_lvl = max(lvl, self.boost_lvl if self.boost_t > 0 else 0.0)
        self.boost_t = max(self.boost_t, secs)

    def _update_orig(self, dt, intensity, mode): # Raise / lower the looping crowd between ORIG_MIN and ORIG_MAX (x main volume).
        if self.intro_active:
            self._leave_intro()
        self._music_fade_step(dt)
        snd = self.voc_snd
        if not (self.orig_on and snd):
            return # A running fade-out (set_original) ends the channel by itself.
        self.boost_t = max(0.0, self.boost_t - dt)
        base = ORIG_MODE_LEVEL.get(mode)
        if base is None:
            base = 0.2 + 0.6 * intensity
        target = base + self.mood * 0.4
        if self.boost_t > 0:
            target = max(target, self.boost_lvl)
        target = clamp(target, ORIG_MIN, ORIG_MAX)
        step = (ORIG_UP if target > self.orig_vol else ORIG_DOWN) * dt
        self.orig_vol = clamp(max(self.orig_vol, ORIG_MIN) + clamp(target - max(self.orig_vol, ORIG_MIN), -step, step), ORIG_MIN, ORIG_MAX)
        if not self.voc_ch.get_busy():
            self.voc_ch.set_volume(self.orig_vol * self.master_vol)
            self.voc_ch.play(snd, loops=-1)
        self.voc_ch.set_volume(clamp(self.orig_vol * self.master_vol, 0.0, 1.0))

    @staticmethod
    def _pcm(samples, gain=1.0): # Convert floating-point samples into clipped 16-bit PCM audio.
        return array.array("h", (int(clamp(v * gain, -1.0, 1.0) * 30000) for v in samples))

    def _write_wav(self, name, pcm): # Write a PCM buffer to a WAV file in the sound cache.
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

    def _load_cache(self): # Load generated sound files that are already present in the cache.
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
    def _thump(f0, f1, dur, noise, decay, kdrop=25.0): # Synthesize a low-frequency impact sound.
        n = int(dur * SR)
        out, ph = [0.0] * n, 0.0
        for i in range(n):
            t = i / SR
            ph += TAU * (f1 + (f0 - f1) * math.exp(-t * kdrop)) / SR
            out[i] = math.sin(ph) * math.exp(-t * decay) + random.uniform(-1, 1) * noise * math.exp(-t * 220)
        return _norm(out)

    @staticmethod
    def _clap(): # Synthesize a short hand-clap sound.
        n = int(0.05 * SR)
        out, a = [], 0.0
        for i in range(n):
            x = random.uniform(-1, 1)
            a += 0.4 * (x - a)
            out.append((x - a) * math.exp(-i / SR * 70))
        return _norm(out, 0.8)

    @staticmethod
    def _clang(): # Synthesize a metallic impact sound.
        parts = [(540, 1.0, 3.0), (1210, .8, 4.5), (1890, .6, 5.5), (2750, .45, 7.0), (3980, .3, 9.0)]
        n = int(1.2 * SR)
        out = []
        for i in range(n):
            t = i / SR
            s = sum(a * math.sin(TAU * f * t) * math.exp(-t * d) for f, a, d in parts)
            out.append(s + random.uniform(-1, 1) * 1.5 * math.exp(-t * 300))
        return _norm(out)

    @staticmethod
    def _clang_bar(): # Synthesize the metallic-bar variant used by the sound set.
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
    def _plastic(): # Synthesize a short plastic impact sound.
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
    def _net(): # Synthesize the sound of a ball hitting the net.
        n = int(0.7 * SR)
        out, a = [], 0.0
        for i in range(n):
            t = i / SR
            a += 0.35 * (random.uniform(-1, 1) - a)
            env = min(1.0, t / 0.012) * math.exp(-t * 6.0)
            out.append(a * env + math.sin(TAU * 70 * t) * math.exp(-t * 14) * 0.7)
        return _norm(out)

    @staticmethod
    def _whistle(dur, f=2900.0, trill=26.0): # Synthesize a referee whistle with the requested duration and pitch.
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
    def _syllable_bank(n_syl=64): # Create reusable syllable samples for procedural crowd chants.
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
    def _walla(bank, dur, speakers, gap_rate, pitch_lo, pitch_hi, bed, swell): # Mix a bank of vocal syllables into a crowd ambience layer.
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

    def _choir(self, out, t0, dur, f0, amp, f1=None, voices=4, vib=5.2, noise=0.0, tbl=None): # Render a layered vocal tone into the output buffer.
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
    def _mix(out, snd, t0, gain): # Mix a sound buffer into the output at the requested start time and gain.
        o = int(t0 * SR)
        for i, v in enumerate(snd):
            if o + i >= len(out):
                break
            out[o + i] += v * gain

    @staticmethod
    def _roar(out, t0, dur, gain, peak=0.4): # Add a crowd roar envelope to the output audio buffer.
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

    def _applause(self, dur, rate): # Generate an applause layer with the requested duration and density.
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
    def _horn(tbl, f, dur, vib=0.0, buzz=0.12, att=0.08, rel=0.2, scoop=0.03, gate=None): # Synthesize a horn tone with pitch and envelope controls.
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

    def _build(self): # Generate the procedural sound library and populate the cache.
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

            def put(name, samples, gain=1.0): # Register a generated sound sample in the sound library.
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

            self._build_chants(put, bombo, clap, stomp)
            self._build_horns(put, brass, air)
            if self.cache_dir:
                try:
                    with open(os.path.join(self.cache_dir, "ver.txt"), "w") as f:
                        f.write(AUDIO_VERSION + str(SR))
                except OSError:
                    pass
        except Exception as ex:
            print("audio: errore di sintesi:", ex)

    def _build_chants(self, put, bombo, clap, stomp): # Build chant variations from voice, drum, clap, and stomp samples.
        def chant(notes, drums, bpm, beats, tbl, voices=3, noise=0.04): # Compose a chant from notes, drums, tempo, and voices.
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

    def _build_horns(self, put, brass, air): # Build the horn sound variations used by the match.
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

    @staticmethod
    def _set(ch, vol, pan): # Apply volume and stereo-pan settings to a sound channel.
        v = clamp(vol, 0.0, 1.0)
        ch.set_volume(v * min(1.0, 1.0 - pan), v * min(1.0, 1.0 + pan))

    def _pan_for(self, name): # Return the default stereo pan associated with a sound name.
        if name.startswith(("cheer", "oh", "boo", "jeer", "stands")):
            return clamp(self.focus, -1.0, 1.0) * 0.9
        if name.startswith(("chant", "horn", "shout", "applause", "drums", "swell")):
            return random.choice((-1.0, 1.0)) * random.uniform(0.3, 1.0)
        return 0.0

    def silence(self): # Stop active sounds and clear pending playback.
        if self.ok:
            pygame.mixer.stop()
            self.amb_vol = self.amb2_vol = 0.0
            self.pending = []
            self.orig_vol, self.boost_t, self.mus_fade = 0.0, 0.0, 0.0
            self._mus_playing, self.intro_active = False, False
            self._mus_run.clear()

    def play(self, name, vol=1.0, pan=None): # Play a named sound with the requested volume and stereo position.
        if not self.ok or self.muted:
            return
        s = self.snd.get(name)
        if s:
            ch = s.play()
            if ch:
                self._set(ch, vol, self._pan_for(name) if pan is None else pan)

    def crowd(self, name, vol=0.9): # Play or update a crowd response sound.
        var = {"cheer": ("cheer1", "cheer2", "cheer3"), "oh": ("oh1", "oh2"), "oh_sad": ("oh3", "oh4", "oh5"),
               "boo": ("boo1", "boo2")}.get(name, (name,))
        self.play(random.choice(var), vol)
        if name == "boo" and random.random() < 0.45:
            self.later(0.25, "jeer", vol * 0.8)

    def later(self, delay, name, vol=1.0): # Schedule a named sound to play after a delay.
        self.pending.append([delay, name, vol, self._pan_for(name)])

    def react(self, kind): # Choose a sound reaction for the supplied match event.
        if kind in ORIG_BOOST and self.ok and not self.muted:
            self._boost(*ORIG_BOOST[kind])
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

    def toggle_mute(self): # Toggle sound playback between muted and enabled states.
        self.muted = not self.muted
        if self.ok:
            if self.muted:
                pygame.mixer.stop()
                self._mus_playing = False
                self.orig_vol = 0.0
            else:
                self.amb_vol = self.amb2_vol = 0.0

    def update(self, dt, intensity, mode="play"): # Advance pending sound events and update the current crowd response.
        if self.ok and not self.muted:
            self._update_orig(dt, intensity, mode)
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
        duck = ORIG_AMB_DUCK if (self.orig_on and self.voc_snd and self.voc_ch.get_busy()) else 1.0 # The original crowd replaces most of the procedural bed.
        self._set(self.amb_ch, self.amb_vol * duck, 0.0)
        self._set(self.amb2_ch, self.amb2_vol * duck, 0.0)
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


