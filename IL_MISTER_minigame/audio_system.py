import array
import math
import os
import random
import threading
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


class Audio: # Procedural match sounds, audio caching, mixing, and playback.
    def __init__(self, enabled=True, cache_dir=None): # Initialize audio generation, cache storage, playback channels, and mute state.
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
            else:
                self.amb_vol = self.amb2_vol = 0.0

    def update(self, dt, intensity): # Advance pending sound events and update the current crowd response.
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


