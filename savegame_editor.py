from __future__ import annotations
import os
import re
import shutil
import struct
import sys
import traceback
import zlib
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont
from PIL import Image, ImageTk

import i18n

APP_TITLE = "BMP / THE MANAGER Savegame Editor v1.0.15"
ICON_FILE = "THE_MANAGER_String_Editor.ico"

def _hex_palette(s: str, scale: int = 1) -> list[tuple[int, int, int]]:
    return [
        (min(255, int(s[i:i+2], 16) * scale),
         min(255, int(s[i+2:i+4], 16) * scale),
         min(255, int(s[i+4:i+6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

_PAL_NORMAL20 = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4)

def _palette_to_flat_rgb(pal: list[tuple[int, int, int]], size: int = 256) -> list[int]:
    flat: list[int] = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]

def _decode_vga(data: bytes, fmt: str = "BMP"):
    header_len = 8 if fmt == "BMH" else 6
    if len(data) < header_len + 1:
        return None
    width = data[0] | (data[1] << 8)
    height = data[2] | (data[3] << 8)
    payload_len = int.from_bytes(data[4:header_len], "little")
    if width <= 0 or height <= 0 or width > 1280 or height > 960 or payload_len < 1:
        return None
    payload_end = header_len + payload_len - 1
    if payload_end >= len(data):
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
            count = b - offset
            pixels.extend((data[i + 1],) * count)
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
    return width, height, bytes(pixels), bytes(data[payload_end + 1:])

def load_vga_image_safe(path: str) -> Image.Image | None:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            data = f.read()
        res = _decode_vga(data, "BMH") or _decode_vga(data, "BMP")
        if not res:
            return None
        w, h, pix, trailer = res
        img = Image.frombytes("P", (w, h), pix)
        pal = _PAL_NORMAL20
        if len(trailer) >= 768:
            pal = [(trailer[i]*4, trailer[i+1]*4, trailer[i+2]*4) for i in range(0, 768, 3)]
        img.putpalette(_palette_to_flat_rgb(pal))
        return img
    except Exception:
        return None

FACE_W, FACE_STEP, FACE_ZOOM = 40, 41, 3


def find_pic_dir(*bases):
    seen = set()
    for base in bases:
        if not base:
            continue
        for d in (base, os.path.dirname(os.path.abspath(base))):
            d = os.path.abspath(d)
            if d in seen:
                continue
            seen.add(d)
            try:
                names = os.listdir(d)
            except OSError:
                continue
            for n in names:
                p = os.path.join(d, n)
                if n.lower() == "pic" and os.path.isdir(p):
                    return p
    return None


def load_faces(pic_dir):
    out = []
    if not pic_dir:
        return out
    try:
        names = {n.lower(): n for n in os.listdir(pic_dir)}
    except OSError:
        return out
    for stem in ["0"] + ["0" + ch for ch in "abcdefghijklmnopqrstuvwxyz"]:
        real = names.get(stem + ".vga")
        img = load_vga_image_safe(os.path.join(pic_dir, real)) if real else None
        if img is None:
            if stem == "0":
                continue
            break
        img = img.convert("RGB")
        for i in range((img.width + 1) // FACE_STEP):
            if i * FACE_STEP + FACE_W <= img.width and img.height >= FACE_W:
                out.append((stem, i, img.crop((i * FACE_STEP, 0, i * FACE_STEP + FACE_W, FACE_W))))
    return out


BG, FG, MUTED = "#F4F6F9", "#2C3E50", "#7F8C8D"
ACCENT, ERR, OK = "#2980B9", "#C0392B", "#27AE60"

_TR = i18n.Translator("savegame_")


def T(key, **fmt):
    return _TR.tr(key, **fmt)


# file header signature
SIG = b"WeRnEr_krahe~&~JeNs_onnen>V2\x00"
# base offsets: managers, clubs, players, squad slots
MB, CB, PB, LB = 2345, 5557, 15813, 21400
# first checksum offset and start of the message block
CHK1, FIX = 28006, 34368
# base of the records and series tables
H = 28435
N_MANAGERS_OFF = 2339
SEASONS_COUNT_OFF = 34224


# salt for the hidden edit marker
EDITOR_TAG = b"MANED"
# hidden marker copies, 8 bytes each, in always-zero padding
MARK_OFFS = (2300, 31000, 33700, 34268)
# values of the cheater player, impossible in normal play
CHEAT_AGE = 0
CHEAT_CARDS = 99
CHEAT_SUSPENSION = 255
CHEAT_CONTRACT = 99
CHEAT_STAT = 10
CHEAT_ROLE = 99


# checksum of one marker copy
def _mark_crc(nonce, off):
    return zlib.crc32(bytes(nonce) + EDITOR_TAG + struct.pack("<H", off)) & 0xFFFFFFFF


# crc32 of every 4th club name per known game version
VERSION_FPRINTS = (
    ('ENG 2.0',
        "aac5ef28,3e26cac8,0123c66e,6b5ad711,83a44028,2d4abc96,4b823d05,0aeaed6a,ff86ad81,70409ad1,b62b6f"
        "fd,bd6e56a2,de76e294,41c641ac,8c7830c2,4aa321e8,556cb9d1,9afe57fd,35a466b3,fa3450d5,02048724,38c"
        "94be6,8eb038ea,a44c856e,9c59d0a3,e8c6329f,656a4bf0,1cfd9a38,13e5ad75,5477c7fe,f10610b1,94166204,"
        "65b89e6d,bb4694a4,57e1e148,e0d37946,4ca3a5f4,ef03ffb7,26ac80f0,f388d152,b624c658,20ded93b,955223"
        "88,fbf0271c,90a342a4,ad7fcb73,290ee48c,6c847bde,56370287,11664eeb"),
    ('FRE 2.0',
        "20c559a6,b09aa235,8e11a92a,e3885186,08a0cbd9,54090715,042d717a,f826ef84,319b1851,b1ae7b31,1acedd"
        "c6,810171a1,567c0bf1,8f42ce6e,a0753527,74e58816,4f0bc143,83a44028,35a466b3,89884730,2ce27b4e,3fa"
        "48fff,8eb038ea,2c3fbabd,1b7782a8,e8c6329f,656a4bf0,737e428c,e626d2a8,a9c97d76,f10610b1,7845e069,"
        "65b89e6d,293bbb8b,57e1e148,e0d37946,adf9acfd,b8aa9bd6,c67969ee,020e22b8,017b590f,32827d11,955223"
        "88,bb88916c,1d42985d,ad7fcb73,111b84bf,6c847bde,89b473f1,11664eeb"),
    ('GER 2.0',
        "ecb16bfd,2c7b0952,606d40e4,2f169703,5ef6f2f8,23819f8a,b24f2729,1b491563,2acae49e,ea891eb5,4f24c7"
        "34,2b0ce0fa,5dbb4d0e,a88c56aa,ae0c3974,0c2c4acf,d681dc6e,ea3cf985,9721a9d6,65359047,4f0bc143,075"
        "deb07,02e3b6bb,7f2ff0f1,71d7a7ad,fb684ed3,974ee77f,4ebb2a39,7a2f67d3,f2085b15,5477c7fe,baf3f676,"
        "e0df70e4,b09aa235,e7bb274d,e548dd10,5d891979,314a8638,26ac80f0,12cd5c3f,7ff72f4c,5f9cfef9,c9533c"
        "fd,5c0d6060,02c5dc39,9f5c2c20,4b9afa12,f7aeaa81,c6368be4,8c7f7287"),
    ('ITA 1.1',
        "6aa86b36,ef3046f9,b711b081,c386fbb2,14a9d374,64f92c4c,58d5701a,ddbf5eb5,9ebd479c,5cc30e77,ff414e"
        "4c,95c8d0c6,1117f311,87f865d0,205ab462,bb4ea8fe,4f0bc143,83a44028,35a466b3,dc302ef7,8ae8cf2a,38c"
        "94be6,896cc1cd,2c3fbabd,1b7782a8,e8c6329f,f3eeed45,1cfd9a38,d651859a,5477c7fe,9a950b1c,94166204,"
        "65b89e6d,293bbb8b,57e1e148,79aec2df,6500e544,ef03ffb7,f385fd78,020e22b8,017b590f,20ded93b,955223"
        "88,a0845cda,e626d2a8,ad7fcb73,111b84bf,6c847bde,56370287,11664eeb"),
    ('BMP-ITA',
        "f6adbd1e,88bef827,6aa86b36,94e4f3a6,9ebd479c,f4cbfa0e,988a808c,f3f9888e,abde0962,66d46b80,d6b7ba"
        "99,ee4a9212,6b361d3e,e68c6ebf,5f78a05c,0f43b0e1,2999dfcf,8bd4efdf,ea215da0,0ca0eedd,0dd134f6,fe5"
        "4aa9a,7b5a18e1,656a4bf0,299c626b,2a3127b3,e0d8c0d5,4b9bcc66,f3334fd0,cf75b49e,5c934b23,b578548c,"
        "241bdaf0,bf0f5b5e,c6ad51e5,12f47bb6,2e7f91c4,ae0e536c,e759693c,1da7254c,07d36bee,0ed4ef4c,f14649"
        "e1,83c26bd7,86d5c5b9,724c9c8a,92e34e50,ace17560,92ec3b36,0446b1a3"),
    ('CHAMP99',
        "7f8a9286,6aa86b36,94e4f3a6,81db1a25,f476767c,054f1960,68d5f2b2,d5a1e445,9ebd479c,17937f35,98d41a"
        "80,248f5362,ad339ae6,66d46b80,60aff447,fe737125,a2007ee6,a8d4554e,0ca0eedd,90443f76,d1e1e83d,dc0"
        "b72e9,addea165,efcbe1b8,73b498d2,6b5ad711,71446488,d0fc27d0,9dcb714b,cbd7a699,a51ddede,9724be34,"
        "2b5df85f,d2b0b8f6,004def88,9db041ed,a4e447d4,3ca9b06d,2811b514,3db49a53,6dbdb232,a28180da,4048c2"
        "ad,3c8b9f4e,866e5058,10ba9e66,49c9c0e9,02c5dc39,5ed0baf3,22a9fdc8"),
)


# parse fingerprint strings into integer lists
def _fp_lists():
    out = []
    for name, s in VERSION_FPRINTS:
        out.append((name, [int(x, 16) for x in s.replace("\"", "").split(",")]))
    return out

# struct formats and value limits per field type
_FMT = {"u8": "<B", "i8": "<b", "i16": "<h", "u16": "<H", "i32": "<i", "u32": "<I"}
_LIMITS = {"u8": (0, 255), "i8": (-128, 127), "i16": (-32768, 32767), "u16": (0, 65535), "i32": (-2 ** 31, 2 ** 31 - 1), "u32": (0, 2 ** 32 - 1)}


class SaveError(Exception):

    def __str__(self):
        return T(self.args[0])


# save stream cipher, same routine for encode and decode
def _crypt(src, dst, a, b, st, enc):
    k, c = st
    if enc:
        for i in range(a, b):
            p = src[i]
            dst[i] = (k + (k ^ p)) & 255
            c = (c + p) & 255
            k = (k + 0xD7) & 255
    else:
        for i in range(a, b):
            p = ((src[i] - k) & 255) ^ k
            dst[i] = p
            c = (c + p) & 255
            k = (k + 0xD7) & 255
    st[0], st[1] = k, c


# role byte to position label
def pos4(v):
    return T("pos.gk" if v < 25 else "pos.df" if v < 50 else "pos.mf" if v < 75 else "pos.fw")


# decrypted save held in memory
class SaveFile:

    def __init__(self, path, data):
        self.path = path
        self.original = bytes(data)
        self.buf, self.mend = self._decode(self.original)
        self.league_team_count = self._detect_league_team_count(self.buf)
        self.roundtrip_ok = self.encode() == self.original
        self.dirty = False

    @staticmethod
    def _is_id_permutation(values, first, count):
        return len(values) == count and sorted(values) == list(range(first, first + count))

    @classmethod
    def _detect_league_team_count(cls, buf):
        if len(buf) < 27960:
            return 20

        first = list(buf[27900:27920])
        second = list(buf[27920:27940])
        third = list(buf[27940:27960])

        if (cls._is_id_permutation(first, 0, 20)
                and cls._is_id_permutation(second, 20, 20)
                and cls._is_id_permutation(third, 40, 20)):
            return 20

        if (cls._is_id_permutation(first[:18], 0, 18)
                and cls._is_id_permutation(second, 18, 20)
                and cls._is_id_permutation(third, 38, 20)):
            return 18

        if len(buf) >= 28304:
            permutations = [list(buf[28244 + 20 * i:28264 + 20 * i]) for i in range(3)]
            p0, p1, p2 = permutations
            if (cls._is_id_permutation(p0, 0, 20)
                    and cls._is_id_permutation(p1, 20, 20)
                    and cls._is_id_permutation(p2, 40, 20)):
                return 20
            if (cls._is_id_permutation(p0[:18], 0, 18)
                    and cls._is_id_permutation(p1, 18, 20)
                    and cls._is_id_permutation(p2, 38, 20)):
                return 18

        if cls._is_id_permutation(first, 0, 20):
            return 20
        if cls._is_id_permutation(first[:18], 0, 18):
            return 18

        return 20

    def league_club_range(self, league):
        first = self.league_team_count
        start = 0 if league == 0 else first + 20 * (league - 1)
        count = first if league == 0 else 20
        return start, start + count

    # decrypt and verify both checksums
    @staticmethod
    def _decode(data):
        if len(data) < FIX + 1:
            raise SaveError("err.too_short")
        if data[:len(SIG)] != SIG:
            raise SaveError("err.bad_sig")
        try:
            p = bytearray(data)
            st = [data[34], data[34]]
            _crypt(data, p, 35, CHK1, st, False)
            if st[1] != data[CHK1]:
                raise SaveError("err.chk1")
            _crypt(data, p, CHK1 + 1, FIX, st, False)
            pos = FIX
            for m in range(p[N_MANAGERS_OFF]):
                for _ in range(p[41 + m]):
                    _crypt(data, p, pos, pos + 5, st, False)
                    n = p[pos + 4]
                    _crypt(data, p, pos + 5, pos + 5 + n, st, False)
                    pos += 5 + n
            if st[1] != data[pos]:
                raise SaveError("err.chk2")
        except IndexError:
            raise SaveError("err.truncated")
        return p, pos

    # encrypt the buffer and refresh checksums
    def encode(self):
        o = bytearray(self.buf)
        st = [self.buf[34], self.buf[34]]
        _crypt(self.buf, o, 35, CHK1, st, True)
        o[CHK1] = st[1]
        _crypt(self.buf, o, CHK1 + 1, self.mend, st, True)
        o[self.mend] = st[1]
        return bytes(o)


    # compare club name hashes with known versions
    def detect_version(self):
        mine = [zlib.crc32(bytes(self.buf[CB + 34 * i:CB + 34 * i + 23]).split(b"\0")[0]) & 0xFFFFFFFF
                for i in range(0, 200, 4)]
        best, pct = None, 0
        for name, ref in _fp_lists():
            p = 100 * sum(a == b for a, b in zip(mine, ref)) // len(ref)
            if p > pct:
                best, pct = name, p
        return (best, pct) if pct >= 50 else (None, pct)

    @property
    def version_name(self):
        n, p = self.detect_version()
        if n is None:
            return None
        if n == "BMP-ITA":
            n = f"BMP-ITA ({T('info.bmp_ita_mod')})"
        return n if p == 100 else f"{n} ~{p}%"

    # count intact hidden marker copies
    def mark_copies(self):
        n = 0
        for off in MARK_OFFS:
            blk = bytes(self.buf[off:off + 8])
            if len(blk) == 8 and struct.unpack("<I", blk[4:])[0] == _mark_crc(blk[:4], off):
                n += 1
        return n

    # squad slot offsets of one manager
    def _slot_offs(self, m=0):
        return [LB + 52 * (m * 25 + i) for i in range(25)]

    # cheater signature: max suspension, 99 cards, age 0, loan flag
    def is_cheater_slot(self, off):
        pi = self.buf[off + 15]
        return (1 <= pi <= 150 and self.buf[off + 13] == CHEAT_SUSPENSION and self.buf[off] == CHEAT_CARDS
                and self.buf[off + 1] == CHEAT_CARDS and self.buf[off + 12] & 0x80
                and self.buf[PB + 37 * pi + 26] == CHEAT_AGE)

    def cheater_present(self):
        return any(self.is_cheater_slot(o) for m in range(self.n_managers) for o in self._slot_offs(m))

    @staticmethod
    def cheater_name():
        import unicodedata
        t = unicodedata.normalize("NFKD", T("mark.name")).encode("ascii", "ignore").decode().upper()
        return (t or "CHEATER")[:25]

    # add or refresh the loaned cheater in a manager squad
    def _write_cheater(self, m):
        slots = self._slot_offs(m)
        # club id of the manager
        own = self.buf[MB + 778 * m + 30]
        ex = [o for o in slots if self.is_cheater_slot(o)]
        if ex:
            o, pi = ex[0], self.buf[ex[0] + 15]
        else:
            used = [i for i, q in enumerate(slots) if self.buf[q + 15]]
            idx = (max(used) + 1) if used else 0
            # full squad: the cheater replaces the 24th player
            if idx > 23:
                idx = 23
            o = slots[idx]
            ref = {self.buf[LB + 52 * i + 15] for i in range(125) if LB + 52 * i != o}
            # free player record, attackers pool first
            pi = next((i for i in list(range(150, 106, -1)) + list(range(106, 0, -1)) if i not in ref), None)
            if pi is None:
                return False
        self.buf[o:o + 52] = bytes(52)
        # slot: cards, status, loan lender, suspension, stats
        self.buf[o + 0] = CHEAT_CARDS
        self.buf[o + 1] = CHEAT_CARDS
        self.buf[o + 6] = 1
        self.buf[o + 9] = 1
        self.buf[o + 11] = CHEAT_CONTRACT
        self.buf[o + 12] = 0x80 | self._lender(m, own)
        self.buf[o + 13] = CHEAT_SUSPENSION
        self.buf[o + 14] = 0x40
        self.buf[o + 15] = pi
        self.buf[o + 16:o + 19] = bytes((CHEAT_STAT,) * 3)
        self.buf[o + 19] = 99
        # player record: name, age, stats, role, club
        nm = self.cheater_name().encode("latin-1")
        rec = bytearray(37)
        rec[:len(nm)] = nm
        rec[26] = CHEAT_AGE
        rec[27] = 50
        rec[28:31] = bytes((CHEAT_STAT,) * 3)
        rec[31] = CHEAT_ROLE
        rec[33] = 4
        rec[35] = 1
        rec[36] = own
        self.buf[PB + 37 * pi:PB + 37 * pi + 37] = rec
        return True

    # first club that is not the manager club
    def _lender(self, m, own):
        return next(c for c in range(128) if c != own)

    def is_marked(self):
        return self.mark_copies() > 0 or self.cheater_present()

    # hidden copies plus the visible cheater
    def mark(self, managers=None):
        nonce = os.urandom(4)
        for off in MARK_OFFS:
            self.buf[off:off + 8] = nonce + struct.pack("<I", _mark_crc(nonce, off))
        for m in (managers if managers is not None else [0]):
            if 0 <= m < self.n_managers:
                self._write_cheater(m)

    # read a typed value
    def rd(self, off, t="u8"):
        return struct.unpack_from(_FMT[t], self.buf, off)[0]

    # write a typed value with range check
    def wr(self, off, t, value):
        lo, hi = _LIMITS[t]
        try:
            v = int(round(float(value)))
        except (TypeError, ValueError):
            v = 0
        struct.pack_into(_FMT[t], self.buf, off, max(lo, min(hi, v)))
        self.dirty = True

    def get_str(self, off, n):
        raw = bytes(self.buf[off:off + n])
        z = raw.find(0)
        return (raw if z < 0 else raw[:z]).decode("latin-1")

    def set_str(self, off, n, s):
        raw = s.encode("latin-1", "replace")[:n - 1]
        self.buf[off:off + n] = raw + bytes(n - len(raw))
        self.dirty = True

    @property
    def n_managers(self):
        return self.buf[N_MANAGERS_OFF]

    def manager_name(self, m):
        return self.get_str(MB + 778 * m, 29)

    def club_name(self, i):
        return self.get_str(CB + 34 * i, 23) if 0 <= i < 200 else ""

    def club_ids(self, limit=200):
        return [i for i in range(limit) if self.club_name(i)]

    def read_messages(self):
        out, p = [], FIX
        for m in range(self.n_managers):
            for _ in range(self.buf[41 + m]):
                n = self.buf[p + 4]
                out.append([m, bytes(self.buf[p:p + 4]), self.get_str(p + 5, n)])
                p += 5 + n
        return out

    def write_messages(self, msgs):
        tail = bytes(self.buf[self.mend:])
        head = bytes(self.buf[:FIX])
        body = b""
        for _m, ptr, text in msgs:
            if not text.endswith("^"):
                text += "^"
            raw = text.encode("latin-1", "replace")[:254]
            body += ptr + bytes([len(raw) + 1]) + raw + b"\x00"
        self.buf = bytearray(head + body + tail)
        self.mend = FIX + len(body)
        self.dirty = True


# sorted .MAN files of a folder
def list_man_files(directory):
    try:
        names = [n for n in os.listdir(directory)
                 if n.lower().endswith(".man") and os.path.isfile(os.path.join(directory, n))]
    except OSError:
        return []
    return sorted(names, key=str.lower)


def apply_editor_style(root):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, font=("Segoe UI", 10), foreground=FG)
    style.configure("TLabelframe", background=BG, font=("Segoe UI", 10, "bold"), foreground=FG)
    style.configure("TLabelframe.Label", background=BG, foreground=FG)
    style.configure("TButton", font=("Segoe UI", 9, "bold"), padding=6, background="#3498DB",
                    foreground="white", borderwidth=0)
    style.map("TButton", background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
    style.configure("Treeview", font=("Consolas", 9), rowheight=25, background="white",
                    fieldbackground="white", foreground=FG, borderwidth=0)
    style.configure("Treeview.Heading", font=("Segoe UI", 7, "bold"), background="#EAECEE",
                    foreground=FG, padding=(2, 7), anchor="center")
    style.map("Treeview", background=[("selected", "#2980B9")], foreground=[("selected", "white")])
    style.configure("TNotebook.Tab", font=("Segoe UI", 9), padding=(10, 3))
    style.map("TNotebook.Tab", font=[("selected", ("Segoe UI", 9, "bold"))],
              padding=[("selected", (10, 4))])


# vertical scrollable container
class ScrollFrame(ttk.Frame):
    _wheel_installed = False

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=BG, yscrollincrement=20)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self._vsb_shown = False
        self.canvas.configure(yscrollcommand=self._vsb_set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self._install_wheel(self)

    def _vsb_set(self, first, last):
        self.vsb.set(first, last)
        full = float(first) <= 0.0 and float(last) >= 1.0
        if full and self._vsb_shown:
            self.vsb.pack_forget()
            self._vsb_shown = False
        elif not full and not self._vsb_shown:
            self.vsb.pack(side="right", fill="y", before=self.canvas)
            self._vsb_shown = True

    @classmethod
    def _install_wheel(cls, widget):
        if cls._wheel_installed:
            return
        cls._wheel_installed = True
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            widget.bind_all(seq, cls._on_wheel, add="+")

    @staticmethod
    def _on_wheel(event):
        try:
            w = event.widget.winfo_containing(event.x_root, event.y_root)
        except (tk.TclError, KeyError, AttributeError):
            return
        if isinstance(w, tk.Text):
            return
        while w is not None:
            if isinstance(w, ScrollFrame):
                if not w._vsb_shown:
                    return
                step = -1 if (getattr(event, "num", 0) == 4 or getattr(event, "delta", 0) > 0) else 1
                w.canvas.yview_scroll(step * 3, "units")
                return
            w = getattr(w, "master", None)


# editable cell: getter and setter
class E:
    __slots__ = ("get", "set")

    def __init__(self, get, set_):
        self.get, self.set = get, set_

    def text(self):
        return self.get()

    def commit(self, text):
        return self.set(text)


# editable cell with a fixed list of choices
class Ch(E):
    __slots__ = ("options",)

    def __init__(self, get, set_, options):
        super().__init__(get, set_)
        self.options = options


# read-only cell
class D:
    __slots__ = ("fn",)

    def __init__(self, fn):
        self.fn = fn

    def text(self):
        return self.fn()


def _autohide(bar, show):
    state = {"on": False}

    def setter(first, last):
        bar.set(first, last)
        full = float(first) <= 0.0 and float(last) >= 1.0
        if full and state["on"]:
            bar.grid_remove()
            state["on"] = False
        elif not full and not state["on"]:
            show()
            state["on"] = True
    return setter


# table with in-place cell editing
class EditableGrid(ttk.Frame):

    def __init__(self, parent, columns, rows=(), height=12, tips=None):
        super().__init__(parent)
        self.columns = list(columns)
        self.headings = [str(spec[0]) for spec in self.columns]
        self.tips = list(tips or ())
        self.header_font = tkfont.Font(root=self, family="Segoe UI", size=7, weight="bold")
        try:
            style = ttk.Style(self)
            value_font = style.lookup("Treeview", "font") or "TkDefaultFont"
            self.value_font = tkfont.Font(root=self, font=value_font)
        except (tk.TclError, TypeError):
            self.value_font = tkfont.Font(root=self, family="TkDefaultFont", size=9)
        # Width measurements are reused when rows refresh or cells are edited.
        # The two fonts are fixed for the lifetime of this grid.
        self._measure_cache = {"header": {}, "value": {}}

        line_space = self.header_font.metrics("linespace")
        max_lines = max((len(label.splitlines()) or 1 for label in self.headings), default=1)
        self.header_height = max(28, line_space * max_lines + 10)
        self.header = tk.Canvas(self, height=self.header_height, width=300,
                                background="#EAECEE", highlightthickness=0, bd=0)
        self.header.grid(row=0, column=0, sticky="ew")
        self._tip_job = None
        self._tip_window = None
        self._header_tip_ranges = []
        self._hover_tip_index = None
        self.header.bind("<Motion>", self._on_header_motion)
        self.header.bind("<Leave>", self._hide_tip)

        ids = [f"c{i}" for i in range(len(self.columns))]
        self.tree = ttk.Treeview(self, columns=ids, show="", height=height, selectmode="browse")
        for cid, spec in zip(ids, self.columns):
            self.tree.column(cid, width=max(36, int(spec[1])), minwidth=36,
                             anchor=spec[2] if len(spec) > 2 else "center", stretch=False)
        self.tree.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        auto_yset = _autohide(vsb, lambda: vsb.grid(row=1, column=1, sticky="ns"))
        auto_xset = _autohide(hsb, lambda: hsb.grid(row=2, column=0, sticky="ew"))

        def sync_xview(first, last):
            auto_xset(first, last)
            self.header.xview_moveto(first)

        self.tree.configure(
            yscrollcommand=auto_yset,
            xscrollcommand=sync_xview)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self._edit = None
        self.rows = []
        self.tree.bind("<Double-1>", self._on_double)
        self.tree.bind("<Return>", self._on_return)
        self.tree.bind("<F2>", self._on_return)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self.set_rows(rows)

    def _fit_columns(self):
        """Fit each column to its widest heading line or displayed cell value."""
        widths = []
        header_cache = self._measure_cache["header"]
        value_cache = self._measure_cache["value"]

        def measure(font, cache, text):
            text = str(text)
            width = cache.get(text)
            if width is None:
                try:
                    width = font.measure(text)
                except (tk.TclError, TypeError):
                    width = len(text) * 8
                cache[text] = width
            return width

        for col, label in enumerate(self.headings):
            heading_width = max((measure(self.header_font, header_cache, line)
                                 for line in (label.splitlines() or [label])), default=0)
            value_width = 0
            for row in self.rows:
                if col < len(row):
                    value_width = max(value_width, measure(self.value_font, value_cache,
                                                           self._display(row[col])))
            # Widths are content-driven: the old design-time width is only a
            # fallback for the initial Treeview construction, not a minimum.
            widths.append(max(36, heading_width, value_width) + 18)

        self.column_widths = widths
        total_width = sum(widths)
        self.header.delete("all")
        self._header_tip_ranges = []
        x = 0
        for i, (label, width, spec) in enumerate(zip(self.headings, widths, self.columns)):
            tip_text = spec[3] if len(spec) > 3 else (self.tips[i] if i < len(self.tips) else "")
            if not tip_text:
                tip_text = T("tip.generic", label=label.replace("\n", " "))
            tag = f"header_{i}"
            self.header.create_rectangle(x, 0, x + width, self.header_height,
                                         fill="#EAECEE", outline="#B8BDC2", tags=(tag,))
            self.header.create_text(x + width / 2, self.header_height / 2,
                                    text=label, width=max(20, width - 8),
                                    justify="center", anchor="center",
                                    font=self.header_font, fill=FG, tags=(tag,))
            self._header_tip_ranges.append((x, x + width, tip_text))
            self.tree.column(f"c{i}", width=width, minwidth=width, stretch=False)
            x += width

        # Keep the Canvas viewport tied to the visible table width. Setting its
        # widget width to total_width makes Tk request the entire virtual width
        # from its parent and can make wide tables expand the whole window.
        self.header.configure(scrollregion=(0, 0, total_width, self.header_height))

    def _schedule_tip(self, event, text):
        self._cancel_tip_job()
        self._close_tip_window()
        x, y = event.x_root + 14, event.y_root + 18
        self._tip_job = self.after(450, self._show_tip, text, x, y)

    def _on_header_motion(self, event):
        x = self.header.canvasx(event.x)
        for i, (left, right, text) in enumerate(self._header_tip_ranges):
            if left <= x < right:
                if i != self._hover_tip_index:
                    self._hover_tip_index = i
                    self._schedule_tip(event, text)
                return
        self._hide_tip()

    def _show_tip(self, text, x, y):
        self._tip_job = None
        if not self.winfo_exists() or not text:
            return
        try:
            tip = tk.Toplevel(self)
            tip.wm_overrideredirect(True)
            tip.configure(background="#6B737B")
            label = tk.Label(
                tip, text=text, justify="left", anchor="w", wraplength=390,
                padx=9, pady=6, background="#FFFBEA", foreground="#20252A",
                font=("Segoe UI", 9), relief="solid", borderwidth=1)
            label.pack(padx=1, pady=1)
            tip.update_idletasks()
            sw, sh = tip.winfo_screenwidth(), tip.winfo_screenheight()
            x = min(x, max(4, sw - tip.winfo_width() - 8))
            y = min(y, max(4, sh - tip.winfo_height() - 8))
            tip.geometry(f"+{max(4, x)}+{max(4, y)}")
            self._tip_window = tip
        except tk.TclError:
            self._tip_window = None

    def _cancel_tip_job(self):
        if self._tip_job is not None:
            try:
                self.after_cancel(self._tip_job)
            except tk.TclError:
                pass
            self._tip_job = None

    def _hide_tip(self, _event=None):
        self._cancel_tip_job()
        self._close_tip_window()
        self._hover_tip_index = None

    def _close_tip_window(self):
        if self._tip_window is not None:
            try:
                self._tip_window.destroy()
            except tk.TclError:
                pass
            self._tip_window = None

    def _on_destroy(self, event):
        if event.widget is self:
            self._hide_tip()

    @staticmethod
    def _display(cell):
        if isinstance(cell, (E, D)):
            return cell.text()
        return "" if cell is None else str(cell)

    def set_rows(self, rows):
        self._finish(False)
        self.rows = [list(r) for r in rows]
        self.tree.delete(*self.tree.get_children())
        for i, row in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(i), values=[self._display(c) for c in row])
        self._fit_columns()
        self.tree.xview_moveto(0)
        self.header.xview_moveto(0)

    def refresh_all(self):
        for i in range(len(self.rows)):
            self._refresh_row(i)
        self._fit_columns()

    def _refresh_row(self, i):
        self.tree.item(str(i), values=[self._display(c) for c in self.rows[i]])

    def _on_double(self, ev):
        if self.tree.identify_region(ev.x, ev.y) != "cell":
            return
        iid = self.tree.identify_row(ev.y)
        col = int(self.tree.identify_column(ev.x)[1:]) - 1
        if iid:
            self.begin_edit(int(iid), col)

    def _on_return(self, _ev):
        sel = self.tree.selection()
        if sel:
            row = int(sel[0])
            for c, cell in enumerate(self.rows[row]):
                if isinstance(cell, E):
                    self.begin_edit(row, c)
                    break
        return "break"

    def begin_edit(self, row, col):
        self._finish(True)
        if row >= len(self.rows) or col >= len(self.rows[row]):
            return
        cell = self.rows[row][col]
        if not isinstance(cell, E):
            return
        iid = str(row)
        self.tree.selection_set(iid)
        self.tree.see(iid)
        self.tree.update_idletasks()
        bbox = self.tree.bbox(iid, f"#{col + 1}")
        if not bbox:
            return
        x, y, w, h = bbox
        var = tk.StringVar(value=cell.text())
        if isinstance(cell, Ch):
            ent = ttk.Combobox(self.tree, textvariable=var, values=cell.options, state="readonly")
            ent.place(x=x, y=y, width=max(w, 200), height=h)
            ent.focus_set()
            ent.bind("<<ComboboxSelected>>", lambda e: self._finish(True, refocus=True))
            ent.bind("<Escape>", lambda e: self._finish(False, refocus=True))
            ent.bind("<FocusOut>", lambda e, ent=ent: self.after(150, lambda: self._combo_lost(ent)))
            ent.after(30, lambda: self._post(ent))
        else:
            ent = ttk.Entry(self.tree, textvariable=var)
            ent.place(x=x, y=y, width=w, height=h)
            ent.focus_set()
            ent.select_range(0, "end")
            ent.bind("<Return>", lambda e: self._finish(True, refocus=True))
            ent.bind("<Escape>", lambda e: self._finish(False, refocus=True))
            ent.bind("<Tab>", lambda e: self._finish(True, move=1) or "break")
            ent.bind("<Shift-Tab>", lambda e: self._finish(True, move=-1) or "break")
            ent.bind("<ISO_Left_Tab>", lambda e: self._finish(True, move=-1) or "break")
            ent.bind("<FocusOut>",
                     lambda e, ent=ent: self._edit and self._edit[2] is ent and self._finish(True))
        self._edit = (row, col, ent, var, cell.text())

    @staticmethod
    def _post(combo):
        try:
            combo.tk.call("ttk::combobox::Post", str(combo))
        except tk.TclError:
            pass

    def _combo_lost(self, combo):
        if not (self._edit and self._edit[2] is combo):
            return
        try:
            focus = str(self.focus_get() or "")
        except KeyError:
            return
        if focus.startswith(str(combo)) or "popdown" in focus:
            return
        self._finish(False)

    def _finish(self, commit, move=0, refocus=False):
        ed = self._edit
        if not ed:
            return
        self._edit = None
        row, col, ent, var, before = ed
        text = var.get()
        ent.destroy()
        if commit and text != before:
            if not self.rows[row][col].commit(text):
                self.bell()
            self._refresh_row(row)
            self._fit_columns()
        if move:
            self._edit_next(row, col, move)
        elif refocus:
            self.tree.focus_set()

    def _edit_next(self, row, col, step):
        r, c = row, col
        while True:
            c += step
            if c >= len(self.rows[r]) or c < 0:
                r += step
                if r < 0 or r >= len(self.rows):
                    return
                c = -1 if step > 0 else len(self.rows[r])
                continue
            if isinstance(self.rows[r][c], E):
                self.begin_edit(r, c)
                return


# numeric or text entry bound to a save field
class ValueEntry(ttk.Entry):

    def __init__(self, parent, cell, width=9, maxlen=None, upper=False, on_write=None,
                 justify="right"):
        self.var = tk.StringVar()
        kw = {}
        if maxlen:
            kw = dict(validate="key",
                      validatecommand=(parent.register(lambda p, n=maxlen: len(p) <= n), "%P"))
        super().__init__(parent, textvariable=self.var, width=width, justify=justify, **kw)
        self.cell, self.upper, self.on_write = cell, upper, on_write
        self.refresh()
        self.bind("<KeyRelease>", self._typed)
        self.bind("<FocusOut>", lambda e: self.refresh())
        self.bind("<Return>", lambda e: self.refresh())

    def _typed(self, _e=None):
        text = self.var.get()
        if self.upper and text != text.upper():
            pos = self.index("insert")
            text = text.upper()
            self.var.set(text)
            self.icursor(pos)
        if text == self._last:
            return
        if self.cell.commit(text):
            self._last = text
            if self.on_write:
                self.on_write()

    def refresh(self):
        self._last = self.cell.text()
        self.var.set(self._last)


NOTE_FONT = ("Segoe UI", 9, "italic")
H1_FONT = ("Segoe UI", 9, "bold")


def _tl(key):
    return T(key).split("|")


def _tip(key, **args):
    return T("tip." + key, **args)


# main panel: toolbar, pages and save logic
class SavegamePanel(ttk.Frame):

    def __init__(self, parent, standalone=False, on_change=None):
        super().__init__(parent)
        self.standalone = standalone
        self.on_change = on_change
        self.sf = None
        self.dir = ""
        self._files = {}
        self._status = ("status.none", {}, MUTED)
        self.mi = self.lg = self.md = self.cup = 0
        self.rec_club = None
        self._pages, self._page_by_path, self._group_inner = [], {}, {}
        self._live = []
        self._photos = {}
        if not standalone:
            _TR.set_language(i18n.current_language())
        self._configure_styles()
        self._build_toolbar()
        self.body = ttk.Frame(self)
        self.body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 8))
        self.placeholder = ttk.Label(self.body, font=NOTE_FONT, foreground=MUTED,
                                     anchor="center", justify="center")
        self.placeholder.pack(expand=True)
        self._build_notebook()
        self.clear()

    def _configure_styles(self):
        st = ttk.Style(self)
        st.configure("Sub.TNotebook", background=BG)
        st.configure("Sub.TNotebook.Tab", font=("Segoe UI", 9), padding=(12, 3), background="#E3E8EE")
        st.map("Sub.TNotebook.Tab", background=[("selected", "#FFFFFF")],
               font=[("selected", ("Segoe UI", 9, "bold"))])

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 8, 10, 6))
        bar.pack(fill=tk.X)

        self.btn_dir = ttk.Button(bar, command=self._choose_dir)
        self.btn_dir.pack(side=tk.LEFT, padx=(0, 6))

        self.saveas_btn = ttk.Button(bar, command=lambda: self.save(True))
        self.saveas_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.file_combo = ttk.Combobox(bar, state="readonly", width=22)
        self.file_combo.pack(side=tk.LEFT, padx=(0, 8))
        self.file_combo.bind("<<ComboboxSelected>>", self._on_pick)

        self.mgr_combo = ttk.Combobox(bar, state="readonly", width=26)
        self.mgr_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.mgr_combo.bind("<<ComboboxSelected>>", self._on_manager)

        if self.standalone:
            self.lang_combo = ttk.Combobox(bar, state="readonly", width=11)
            langs = _TR.discover_languages()
            self._lang_codes = [c for c, _ in langs]
            self.lang_combo.config(values=[n for _, n in langs])
            if _TR.current_language() in self._lang_codes:
                self.lang_combo.current(self._lang_codes.index(_TR.current_language()))
            self.lang_combo.pack(side=tk.RIGHT, padx=(8, 0))
            self.lang_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self.set_language(self._lang_codes[self.lang_combo.current()]))

        self.info_label = ttk.Label(bar, font=("Segoe UI", 9, "italic"), foreground=MUTED)
        self.info_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._apply_toolbar_texts()

    def _apply_toolbar_texts(self):
        self.btn_dir.config(text=T("tb.folder"))
        self.saveas_btn.config(text=T("tb.save_as"))

    def _build_notebook(self):
        G = lambda k: T("grp." + k)
        P = lambda k: T("pg." + k)
        layout = [
            (G("manager"), [(P("profile"), self._pg_profile, "mgr"), (P("history"), self._pg_history, "mgr"),
                            (P("stats"), self._pg_stats, "mgr")]),
            (G("squad"), [(P("roster"), self._pg_squad, "mgr"), (P("players"), self._pg_players, None),
                           (P("market"), self._pg_market, None)]),
            (G("economy"), [(P("stadium"), self._pg_stadium, "mgr"), (P("loans"), self._pg_loans, "mgr"),
                            (P("sponsors"), self._pg_sponsors, "mgr")]),
            (G("league"), [(P("standings"), self._pg_standings, "league"),
                           (P("results"), self._pg_results, "league"),
                           (P("calendar"), self._pg_calendar, "league")]),
            (G("cups"), [(P("cup_state"), self._pg_cup_state, None), (P("cup_ties"), self._pg_cup_ties, None)]),
            (G("clubs"), [(P("clubs"), self._pg_clubs, None), (P("ext_standings"), self._pg_ext_standings, None),
                          (P("series"), self._pg_series, None),
                          (P("records"), self._pg_records, None), (P("versus"), self._pg_versus, "mgr")]),
            (G("messages"), [(P("messages"), self._pg_messages, None)]),
            (P("options"), [(P("options"), self._pg_options, None)]),
            (P("raw"), [(P("raw"), self._pg_raw, None)]),
        ]
        self.nb = ttk.Notebook(self.body)
        for gname, pages in layout:
            gframe = ttk.Frame(self.nb)
            self.nb.add(gframe, text=gname)
            if len(pages) == 1:
                self._add_page(gframe, pages[0][1], pages[0][2])
                continue
            inner = ttk.Notebook(gframe, style="Sub.TNotebook")
            inner.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            self._group_inner[str(gframe)] = inner
            for title, builder, dep in pages:
                holder = ttk.Frame(inner)
                inner.add(holder, text=title)
                self._add_page(holder, builder, dep)
            inner.bind("<<NotebookTabChanged>>", self._ensure_visible)
        self.nb.bind("<<NotebookTabChanged>>", self._ensure_visible)

    def _add_page(self, host, builder, dep):
        page = {"host": host, "build": builder, "dep": dep, "stale": True}
        self._pages.append(page)
        self._page_by_path[str(host)] = page

    def set_language(self, code):
        if code == _TR.current_language() or not _TR.set_language(code):
            return False
        self.retranslate()
        return True

    def retranslate(self):
        self._apply_toolbar_texts()
        shown = self.sf is not None
        self.nb.destroy()
        self._pages, self._page_by_path, self._group_inner = [], {}, {}
        self._build_notebook()
        if shown:
            self.nb.pack(fill=tk.BOTH, expand=True)
            self._fill_managers()
            self._invalidate()
        self.refresh_list()
        self._render_status()
        if self.standalone and _TR.current_language() in self._lang_codes:
            self.lang_combo.current(self._lang_codes.index(_TR.current_language()))

    def _current_page(self):
        try:
            top = self.nb.select()
        except tk.TclError:
            return None
        if not top:
            return None
        inner = self._group_inner.get(top)
        return self._page_by_path.get(inner.select() if inner else top)

    def _ensure_visible(self, _e=None):
        page = self._current_page()
        if self.sf and page and page["stale"]:
            self._build(page)

    def _build(self, page):
        host = page["host"]
        for child in host.winfo_children():
            child.destroy()
        page["stale"] = False
        try:
            page["build"](host)
        except Exception as exc:
            traceback.print_exc()
            ttk.Label(host, text=T("err.page", error=exc), foreground=ERR).pack(padx=10, pady=10)

    def _invalidate(self, dep=None):
        for p in self._pages:
            if dep is None or p["dep"] == dep:
                for child in p["host"].winfo_children():
                    child.destroy()
                p["stale"] = True
        self._ensure_visible()

    def _reload(self, host):
        page = self._page_by_path[str(host)]
        self.after_idle(lambda: self._build(page))

    def set_dir(self, directory):
        self.dir = os.path.abspath(directory) if directory else ""
        self.refresh_list()
        if self.dir and not self.sf:
            names = list_man_files(self.dir)
            if names:
                self.load_file(os.path.join(self.dir, names[0]))

    def refresh_list(self, select=None):
        names = list_man_files(self.dir) if self.dir else []
        self._files = {n: os.path.join(self.dir, n) for n in names}
        self.file_combo.config(values=names)
        cur = select or (os.path.basename(self.sf.path) if self.sf else None)
        self.file_combo.set(cur if cur in self._files else "")
        if not self.sf:
            if not self.dir:
                msg = T("ph.no_dir")
            elif not names:
                msg = T("ph.none", dir=self.dir)
            else:
                msg = T("ph.pick", n=len(names))
            self.placeholder.config(text=msg)
        self._render_status()

    def _on_pick(self, _e=None):
        path = self._files.get(self.file_combo.get())
        if path and not self.load_file(path):
            self.file_combo.set(os.path.basename(self.sf.path) if self.sf else "")

    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.dir or None, title=T("dlg.folder"))
        if d and self.confirm_discard():
            self._unload()
            self.set_dir(d)

    def _filetypes(self):
        return [(T("dlg.type_man"), "*.MAN *.man"), (T("dlg.type_all"), "*.*")]

    def is_dirty(self):
        return bool(self.sf and self.sf.dirty)

    def confirm_discard(self):
        if not self.is_dirty():
            return True
        return messagebox.askyesno(T("dlg.title"),
                                   T("dlg.discard", name=os.path.basename(self.sf.path)),
                                   parent=self.winfo_toplevel())

    def load_file(self, path):
        if not self.confirm_discard():
            return False
        try:
            with open(path, "rb") as fh:
                data = fh.read()
            sf = SaveFile(os.path.abspath(path), data)
        except (OSError, SaveError) as exc:
            messagebox.showerror(T("dlg.title"), f"{os.path.basename(path)}:\n{exc}",
                                 parent=self.winfo_toplevel())
            self._set_status_raw(str(exc), ERR)
            return False
        self.sf = sf
        self.mi = min(sf.buf[49], max(0, sf.n_managers - 1))
        self.lg = self.md = self.cup = 0
        self.rec_club = None
        folder = os.path.dirname(sf.path)
        if os.path.normcase(folder) != os.path.normcase(self.dir):
            self.dir = folder
        self.refresh_list(select=os.path.basename(sf.path))
        self._fill_managers()
        self.placeholder.pack_forget()
        self.nb.pack(fill=tk.BOTH, expand=True)
        self.nb.select(0)
        self._invalidate()
        self._set_status_key("status.loaded_ok" if sf.roundtrip_ok else "status.loaded_warn",
                             MUTED if sf.roundtrip_ok else ERR, name=os.path.basename(sf.path))
        self._update_ui(keep_status=True)

        return True

    def _unload(self):
        self.sf = None
        self.nb.pack_forget()
        self.placeholder.pack(expand=True)
        self._invalidate()
        self.mgr_combo.config(values=[], state="disabled")
        self.mgr_combo.set("")

    def clear(self):
        self._unload()
        self.dir = ""
        self.refresh_list()
        self._set_status_key("status.none", MUTED)
        self._update_ui(keep_status=True)

    # verify, back up and write the save
    def save(self, save_as=False):
        sf = self.sf
        if not sf:
            return False
        parent = self.winfo_toplevel()
        path = sf.path
        if save_as:
            path = filedialog.asksaveasfilename(
                initialdir=os.path.dirname(sf.path), initialfile=os.path.basename(sf.path),
                defaultextension=".MAN", title=T("dlg.save_as"), filetypes=self._filetypes())
            if not path:
                return False
        if not sf.roundtrip_ok and not messagebox.askyesno(T("dlg.title"), T("dlg.roundtrip"), parent=parent):
            return False
        made_backup = False
        try:
            # mark every manager edited in this session
            sf.mark(sorted(getattr(sf, "touched", set()) | {self.mi}))
            data = sf.encode()
            check, _ = SaveFile._decode(data)
            if (bytes(check[:CHK1]) != bytes(sf.buf[:CHK1])
                    or bytes(check[CHK1 + 1:sf.mend]) != bytes(sf.buf[CHK1 + 1:sf.mend])):
                raise SaveError("err.verify")
            backup = path + ".bak"
            if os.path.isfile(path) and not os.path.exists(backup):
                shutil.copy2(path, backup)
                made_backup = True
            tmp = path + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(data)
            os.replace(tmp, path)
        except (OSError, SaveError) as exc:
            messagebox.showerror(T("dlg.title"), T("dlg.save_failed", error=exc), parent=parent)
            return False
        sf.path, sf.original, sf.dirty = os.path.abspath(path), data, False
        if os.path.normcase(os.path.dirname(sf.path)) == os.path.normcase(self.dir):
            self.refresh_list(select=os.path.basename(sf.path))
        self._set_status_key("status.saved", OK, name=os.path.basename(path),
                             backup=T("status.backup") if made_backup else "")
        self._update_ui(keep_status=True)
        if self.on_change:
            self.on_change()
        return True

    def _set_status_key(self, key, color=MUTED, **args):
        self._status = (key, args, color)
        self._render_status()

    def _set_status_raw(self, text, color=MUTED):
        self._status = (None, text, color)
        self._render_status()

    def _render_status(self):
        key, args, color = self._status
        st_text = args if key is None else T(key, **args)
        parts = []
        if self.dir:
            parts.append(f"({self.dir})")
        if self.sf:
            def tx(k, d):
                t = T(k)
                return d if t == k else t
            ver = self.sf.version_name
            parts.append(f"{tx('info.version', 'Versione')}: {ver or tx('info.unknown', 'sconosciuta')}")
            if self.sf.is_marked():
                n = self.sf.mark_copies()
                g = self.sf.cheater_present()
                extra = f" [{n}/{len(MARK_OFFS)}" + (f" + {tx('info.ingame', 'in-game')}]" if g else "]")
                parts.append(tx("info.edited", "MODIFICATO CON L'EDITOR") + extra)
        if st_text:
            parts.append(st_text)
        self.info_label.config(text=" – ".join(parts), foreground=color)

    def _update_ui(self, keep_status=False):
        loaded = bool(self.sf)
        self.saveas_btn.config(state=tk.NORMAL if loaded else tk.DISABLED)
        if loaded and self.sf.dirty and not keep_status:
            self._set_status_key("status.dirty", ERR)

    # remember the edited manager and refresh live widgets
    def _changed(self):
        if self.sf is not None:
            self.sf.touched = getattr(self.sf, "touched", set()) | {self.mi}
        for fn in list(self._live):
            try:
                fn()
            except tk.TclError:
                self._live.remove(fn)
        self._update_ui()
        if self.on_change:
            self.on_change()

    def _fill_managers(self):
        sf = self.sf
        vals = [T("mgr.item", n=m + 1, name=sf.manager_name(m)) for m in range(sf.n_managers)]
        self.mgr_combo.config(values=vals, state="readonly")
        if vals:
            self.mgr_combo.current(self.mi)

    def _on_manager(self, _e=None):
        i = self.mgr_combo.current()
        if i >= 0 and i != self.mi:
            self.mi = i
            self._invalidate("mgr")

    def _mo(self):
        return MB + 778 * self.mi

    def _num(self, off, t="u8"):
        def get():
            return str(self.sf.rd(off, t))

        def set_(text):
            try:
                v = int(text.strip())
            except ValueError:
                return False
            self.sf.wr(off, t, v)
            self._changed()
            return True
        return E(get, set_)

    def _num_range(self, off, t="u8", minimum=None, maximum=None):
        """Numeric field constrained to the accepted interval."""
        def get():
            return str(self.sf.rd(off, t))

        def set_(text):
            try:
                value = int(text.strip())
            except ValueError:
                return False
            if minimum is not None and value < minimum:
                return False
            if maximum is not None and value > maximum:
                return False
            try:
                self.sf.wr(off, t, value)
            except (OverflowError, struct.error):
                return False
            self._changed()
            return True
        return E(get, set_)

    def _hex_bytes(self, off, count):
        return D(lambda off=off, count=count: " ".join(
            f"{v:02X}" for v in self.sf.buf[off:off + count]))

    def _dword_hex(self, off):
        # Display the complete 32-bit pointer without splitting it into WORDs.
        def get():
            value = int.from_bytes(self.sf.buf[off:off + 4], "little", signed=False)
            return f"0x{value:08X}"
        return D(get)

    def _player_owner_cell(self, off):
        def get():
            owner = self.sf.buf[off]
            if 0 <= owner < 4:
                name = self.sf.get_str(MB + 778 * owner, 29).strip()
                return f"{owner}: {name or f'Manager {owner + 1}'}"
            if owner == 4:
                return f"4: {T('pl.owner_market')}"
            if owner == 5:
                return f"5: {T('pl.owner_free')}"
            return str(owner)
        return D(get)

    def _txt(self, off, n):
        def set_(text):
            self.sf.set_str(off, n, text.upper())
            self._changed()
            return True
        return E(lambda: self.sf.get_str(off, n), set_)

    def _pair(self, off, empty_255):
        def get():
            v = self.sf.buf[off]
            return "" if (empty_255 and v == 255) else f"{v >> 4}:{v & 15}"

        def set_(text):
            t = text.strip()
            if not t:
                self.sf.wr(off, "u8", 255 if empty_255 else 0)
            else:
                parts = [p for p in re.split(r"[:\s/,;\-]+", t) if p]
                try:
                    a = int(parts[0])
                    b = int(parts[1]) if len(parts) > 1 else 0
                except (ValueError, IndexError):
                    return False
                self.sf.wr(off, "u8", (max(0, min(15, a)) << 4) | max(0, min(15, b)))
            self._changed()
            return True
        return E(get, set_)

    def _club_label(self, v):
        n = self.sf.club_name(v)
        return f"{v} – {n}" if n else f"{v} – ?"

    def _club_options(self):
        return [self._club_label(i) for i in self.sf.club_ids()]

    def _club_cell(self, off):
        def set_(text):
            m = re.match(r"\s*(\d+)", text)
            if not m:
                return False
            self.sf.wr(off, "u8", int(m.group(1)))
            self._changed()
            return True
        return Ch(lambda: self._club_label(self.sf.buf[off]), set_, self._club_options())

    def _club_combo(self, parent, off, width=30):
        cb = ttk.Combobox(parent, state="readonly", width=width, values=self._club_options())
        cb.set(self._club_label(self.sf.buf[off]))

        def picked(_e):
            self.sf.wr(off, "u8", self.sf.club_ids()[cb.current()])
            self._changed()
        cb.bind("<<ComboboxSelected>>", picked)
        return cb

    def _live_label(self, parent, fn, **kw):
        lab = ttk.Label(parent, **kw)
        lab.config(text=fn())
        self._live.append(lambda: lab.config(text=fn()))
        return lab

    def _hexrun(self, off, n):
        def get():
            return " ".join(f"{x:02X}" for x in self.sf.buf[off:off + n])

        def set_(text):
            try:
                vals = [int(t, 16) for t in re.split(r"[\s,;:]+", text.strip()) if t]
            except ValueError:
                return False
            if len(vals) != n or any(not 0 <= v <= 255 for v in vals):
                return False
            self.sf.buf[off:off + n] = bytes(vals)
            self.sf.dirty = True
            self._changed()
            return True
        return E(get, set_)

    def _note(self, parent, text, wrap=900):
        return ttk.Label(parent, text=text, foreground=MUTED, font=NOTE_FONT,
                         wraplength=wrap, justify="left")

    def _field(self, parent, row, label, widget, col=0):
        ttk.Label(parent, text=label).grid(row=row, column=col * 2, sticky="w", padx=(4, 8), pady=3)
        widget.grid(row=row, column=col * 2 + 1, sticky="w", padx=(0, 4), pady=3)

    def _num_field(self, parent, off, t="u8", width=8, **kw):
        return ValueEntry(parent, self._num(off, t), width=width, **kw)

    def _combo_field(self, parent, options, off, base, width=20):
        cb = ttk.Combobox(parent, values=options, state="readonly", width=width)
        idx = self.sf.buf[off] - base
        if 0 <= idx < len(options):
            cb.current(idx)
        else:
            cb.set(f"? ({self.sf.buf[off]})")

        def picked(_e):
            self.sf.wr(off, "u8", cb.current() + base)
            self._changed()
        cb.bind("<<ComboboxSelected>>", picked)
        return cb

    def _value_grid(self, parent, off, n, cols, w=44, first_w=44, description=""):
        columns = [("#", first_w)] + [(str(i + 1), w) for i in range(cols)]
        rows = [[i + 1] + [self._num(off + k) for k in range(i, min(n, i + cols))]
                for i in range(0, n, cols)]
        tips = [_tip("index")]
        tips.extend(T("tip.value_column", column=i + 1, description=description or T("tip.unknown_values"))
                    for i in range(cols))
        return EditableGrid(parent, columns, rows, height=len(rows), tips=tips)

    def _labeled(self, parent, text, **grid):
        lf = ttk.LabelFrame(parent, text=text, padding=8)
        lf.grid(**grid)
        return lf

    def _scroll_page(self, host):
        sc = ScrollFrame(host)
        sc.pack(fill=tk.BOTH, expand=True)
        return sc.inner

    def _league_bar(self, host):
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("lbl.league")).pack(side="left")
        cb = ttk.Combobox(bar, values=_tl("lists.leagues"), state="readonly", width=14)
        cb.current(self.lg)
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.lg, self.md = cb.current(), 0
            self.after_idle(lambda: self._invalidate("league"))
        cb.bind("<<ComboboxSelected>>", picked)
        return bar

    def _pg_profile(self, host):
        sf, o = self.sf, self._mo()
        body = self._scroll_page(host)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)

        ident = self._labeled(body, T("prof.identity"), row=0, column=0, sticky="nsew", padx=(10, 5), pady=(10, 5))
        self._field(ident, 0, T("prof.name"),
                    ValueEntry(ident, self._txt(o, 29), width=30, maxlen=28, upper=True,
                               justify="left", on_write=self._refresh_manager_combo))
        league_holder = []
        ids = sf.club_ids()
        cb = ttk.Combobox(ident, values=self._club_options(), state="readonly", width=30)
        cb.set(self._club_label(sf.buf[o + 30]))

        def club_picked(_e):
            v = ids[cb.current()]
            sf.wr(o + 30, "u8", v)
            first_end = sf.league_team_count
            sf.wr(o + 312, "u8", 0 if v < first_end else 1 if v < first_end + 20 else 2)
            self._changed()
            for w in league_holder:
                w.refresh()
        cb.bind("<<ComboboxSelected>>", club_picked)
        self._field(ident, 1, T("c.club"), cb)

        self._field(ident, 2, T("prof.cash"), self._num_field(ident, o + 496, "i32", width=14))

        def month_cell():
            def set_(t):
                try:
                    sf.wr(27964, "i32", int(t) - 1)
                except ValueError:
                    return False
                self._changed()
                return True
            return E(lambda: str(sf.rd(27964, "i32") + 1), set_)

        def year_cell():
            def set_(t):
                try:
                    v = int(t)
                except ValueError:
                    return False
                sf.wr(27968, "i32", v)
                sf.wr(27976, "u16", v)
                self._changed()
                return True
            return E(lambda: str(sf.rd(27968, "i32")), set_)
        date = ttk.Frame(ident)
        ValueEntry(date, self._num(27960, "i32"), width=4).pack(side="left")
        ttk.Label(date, text=" / ").pack(side="left")
        ValueEntry(date, month_cell(), width=4).pack(side="left")
        ttk.Label(date, text=" / ").pack(side="left")
        ValueEntry(date, year_cell(), width=6).pack(side="left")
        self._field(ident, 3, T("prof.date"), date)

        def level_cell():
            def set_(t):
                try:
                    v = int(t)
                except ValueError:
                    return False
                sf.wr(34062, "u8", max(0, min(4, 5 - v)))
                self._changed()
                return True
            return E(lambda: str(5 - sf.buf[34062]), set_)
        self._field(ident, 4, T("prof.level"), ValueEntry(ident, level_cell(), width=4))

        face_lab = ttk.Label(ident, anchor="center", relief="solid")
        face_lab.grid(row=0, column=2, rowspan=5, padx=(16, 4), pady=3, sticky="ne")

        def show_face(*_):
            faces = self._faces()
            idx = sf.buf[o + 29] - 1
            if 0 <= idx < len(faces):
                im = faces[idx][2].resize((FACE_W * FACE_ZOOM, FACE_W * FACE_ZOOM), Image.NEAREST)
                self._photos["face"] = ImageTk.PhotoImage(im)
                face_lab.config(image=self._photos["face"], text="")
            else:
                self._photos["face"] = None
                face_lab.config(image="", text="—", width=8)
        self._field(ident, 5, T("prof.portrait_id"),
                    ValueEntry(ident, self._num(o + 29), width=4, on_write=show_face))
        show_face()

        mgmt = self._labeled(body, T("prof.mgmt"), row=0, column=1, sticky="nsew", padx=(5, 10), pady=(10, 5))
        items = list(zip(_tl("prof.mgmt_items"), (305, 319, 321, 322, 323, 324, 317, 314,
                                                  325, 326, 327, 328, 329)))
        place = {3: (0, 0), 4: (1, 0), 5: (2, 0), 6: (3, 0), 9: (4, 0),
                 10: (0, 1), 11: (1, 1), 12: (2, 1), 13: (3, 1),
                 1: (6, 0), 2: (6, 1), 7: (7, 0), 8: (7, 1)}
        ttk.Frame(mgmt, height=14).grid(row=5, column=0)
        for pos, (r, col) in place.items():
            label, d = items[pos - 1]
            self._field(mgmt, r, label, self._num_field(mgmt, o + d, width=6), col=col)

        adv = self._labeled(body, T("prof.internal"), row=1, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=5)
        lg = self._num_field(adv, o + 312, width=6)
        league_holder.append(lg)
        a_lab = _tl("prof.internal_items")
        self._field(adv, 0, a_lab[0], lg, col=0)
        self._field(adv, 0, a_lab[1], self._num_field(adv, o + 265, width=6), col=1)
        self._field(adv, 0, a_lab[2], self._num_field(adv, o + 320, width=6), col=2)
        self._note(body, T("prof.note")).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(2, 5))

        ext = self._labeled(body, T("prof.extra"), row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
        extra = [(480, "u16"), (482, "u16"), (310, "u16"), (376, "u16"), (384, "u16"),
                 (392, "u16"), (400, "u16"), (502, "u16"), (506, "u16"), (313, "u8"), (315, "u8"), (318, "u8")]
        for k, (x, t) in enumerate(extra):
            self._field(ext, k // 6, T("prof.extra_item", off=x), self._num_field(ext, o + x, t, width=8), col=k % 6)
        self._note(body, T("prof.extra_note")).grid(row=4, column=0, columnspan=2, sticky="w", padx=10,
                                                    pady=(2, 10))

    def _pic_dir(self):
        here = os.path.dirname(os.path.abspath(__file__))
        return find_pic_dir(self.dir, os.getcwd(), here) or None

    def _faces(self):
        pic = self._pic_dir()
        if "faces" not in self._photos or self._photos.get("faces_dir") != pic:
            self._photos["faces_dir"], self._photos["faces"] = pic, load_faces(pic)
        return self._photos["faces"]

    def _refresh_manager_combo(self):
        if self.sf:
            self._fill_managers()

    def _pg_history(self, host):
        sf, o = self.sf, self._mo()
        count = min(50, sf.rd(SEASONS_COUNT_OFF, "u16"))
        left = ttk.Frame(host)
        left.pack(side="left", fill="y", padx=(10, 5), pady=10)
        pal = ttk.LabelFrame(left, text=T("hist.palmares"), padding=8)
        pal.pack(fill="x")
        self._field(pal, 0, T("hist.seasons_played"), self._num_field(pal, SEASONS_COUNT_OFF, "u16", width=6))
        titles = _tl("lists.titles")
        for i, t in enumerate(titles):
            self._field(pal, 1 + i, T("hist.titles", name=t), self._num_field(pal, o + 57 + i, width=6))
        for i, t in enumerate(titles[1:]):
            self._field(pal, 6 + i, T("hist.round", name=t), self._num_field(pal, o + 306 + i, width=6))

        bil = ttk.LabelFrame(left, text=T("hist.balance"), padding=8)
        bil.pack(fill="x", pady=(10, 0))
        labs = _tl("hist.balance_items")
        labs = labs + ["Games played", "Points conceded (2G-Pts)"][max(0, len(labs) - 6):]
        rows = [[lab, self._num(o + x, "u16"), self._num(o + x + 2, "u16")]
                for lab, x in zip(labs[:6], (420, 424, 428, 440, 444, 448))]
        rows.append([labs[6], self._num(o + 436, "u16"), self._num(o + 438, "u16")])
        rows.append([labs[7], self._num(o + 432, "i16"), self._num(o + 434, "i16")])
        EditableGrid(bil, [("", 110, "w"), (T("c.home"), 80), (T("c.away_full"), 80)], rows,
                     height=len(rows), tips=[_tip("balance_item"), _tip("home_total"),
                                             _tip("away_total")]).pack()

        sea = ttk.LabelFrame(host, text=T("hist.seasons"), padding=8)
        sea.pack(side="right", fill="both", expand=True, padx=(5, 10), pady=10)
        btns = ttk.Frame(sea)
        btns.pack(fill="x", pady=(0, 6))

        def add():
            c = sf.rd(SEASONS_COUNT_OFF, "u16")
            if c >= 50:
                return
            b = o + 62 + 4 * c
            for k in range(4):
                sf.buf[b + k] = sf.buf[b - 4 + k] if c else (1, 0, 0, 0)[k]
            sf.wr(SEASONS_COUNT_OFF, "u16", c + 1)
            self._changed()
            self._reload(host)

        def remove():
            c = sf.rd(SEASONS_COUNT_OFF, "u16")
            if not c:
                return
            for k in range(4):
                sf.buf[o + 62 + 4 * (c - 1) + k] = 0
            sf.wr(SEASONS_COUNT_OFF, "u16", c - 1)
            self._changed()
            self._reload(host)
        ttk.Button(btns, text=T("hist.add"), command=add).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text=T("hist.remove"), command=remove).pack(side="left")
        rows = [[i + 1] + [self._num(o + 62 + 4 * i + k) for k in range(4)] for i in range(count)]
        cols = _tl("hist.season_cols")
        EditableGrid(sea, [("#", 50), (cols[0], 90), (cols[1], 70), (cols[2], 95), (cols[3], 80)],
                     rows, height=12, tips=[_tip("index"), _tip("season_position"),
                                            _tip("season_league"), _tip("season_cup"),
                                            _tip("season_europe")]).pack(fill="both", expand=True)
        self._note(sea, T("hist.note"), wrap=520).pack(anchor="w", pady=(6, 0))

    def _pg_stats(self, host):
        o = self._mo()
        body = self._scroll_page(host)
        for title, off, n, cols, w, desc in ((T("stats.positions"), o + 267, 38, 10, 44,
                                              T("tip.positions_by_round")),
                                             (T("stats.attendance"), o + 330, 17, 10, 44,
                                              T("tip.attendance_by_match")),
                                             (T("stats.series"), H + 3904 + 21 * self.mi, 21, 21, 40,
                                              T("tip.series_unverified"))):
            lf = ttk.LabelFrame(body, text=title, padding=8)
            lf.pack(fill="x", padx=10, pady=(10, 5))
            self._value_grid(lf, off, n, cols, w=w, description=desc).pack(anchor="w")
        ch = ttk.LabelFrame(body, text=T("stats.chart"), padding=8)
        ch.pack(fill="x", padx=10, pady=5)
        self._field(ch, 0, T("std.home_games") + " (+476)", self._num_field(ch, o + 476, "u16", width=6))
        self._field(ch, 0, "+478", self._num_field(ch, o + 478, "u16", width=6), col=1)
        self._note(body, T("stats.note")).pack(anchor="w", padx=10, pady=(2, 10))

    # squad page, the cheater row is hidden
    def _pg_squad(self, host):
        sf = self.sf
        rows, slots = [], []
        for i in range(25):
            b = LB + 52 * (self.mi * 25 + i)
            pi = sf.buf[b + 15]
            if not pi or sf.is_cheater_slot(b):
                continue
            pb = PB + 37 * pi
            slots.append(b)
            # Identity first, then every displayed slot field in ascending byte order.
            rows.append([
                sf.get_str(pb, 26), D(lambda pb=pb: pos4(self.sf.buf[pb + 31])),
                self._num(b), self._num(b + 1), self._num(b + 2),
                self._num(b + 3), self._num(b + 4), self._num(b + 5),
                self._num(b + 6), self._num(b + 7), self._num(b + 8),
                self._num(b + 9), self._num(b + 10), self._num(b + 11),
                self._num(b + 12), self._num(b + 13),
                self._num(b + 14), D(lambda b=b: str(self.sf.buf[b + 15])),
                self._num(b + 16), self._num(b + 17), self._num(b + 18),
                self._num(b + 19), self._num(b + 20), self._num(b + 21, "i8"),
                self._num(b + 22), self._num(b + 23), self._num(b + 24),
                self._num(b + 25, "i8"), self._num(b + 26),
                D(lambda b=b: str(self.sf.buf[b + 27])),
                self._num(b + 28, "u16"), self._num(b + 30, "u16"),
                self._num(b + 32, "u16"), self._num(b + 34, "u16"),
                self._num(b + 36, "u16"), self._num(b + 38, "u16"),
                self._num(b + 40, "i32"), self._hex_bytes(b + 44, 4), self._dword_hex(b + 48),
            ])
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        c = _tl("squad.cols")
        widths = (180, 55, 66, 58, 76, 72, 78, 68, 80, 82, 72, 66, 55, 82, 62, 88)
        xc = _tl("squad.extra_cols")
        xwidths = (78, 65, 62, 62, 58, 64, 82, 78, 84, 72, 82, 66, 66, 80,
                   90, 90, 78, 90, 90, 78, 92, 86, 92)
        squad_tip_keys = [
            "player", "role_group", "direct_reds", "yellow_cards", "second_yellow",
            "league_goals", "goals_cup", "goals_europe", "league_appearances", "apps_cup",
            "apps_europe", "state_flags", "shirt_number", "contract_seasons", "loan",
            "suspension_injury", "training_factor", "player_index", "condition_current",
            "technique_current", "form_current", "freshness", "training_program", "match_rating",
            "offering_club", "injury_type", "contract_status", "pitch_column", "pitch_line",
            "unknown_byte27", "apps_league", "apps_cup", "apps_europe", "league_goals",
            "goals_cup", "goals_europe", "monthly_wage", "unknown_bytes44",
            "notification_pointer",
        ]
        grid = EditableGrid(host, [(c[0], widths[0], "w")] +
                            [(t, w) for t, w in zip(c[1:], widths[1:])] +
                            [(t, w) for t, w in zip(xc, xwidths)], rows, height=14,
                            tips=[_tip(k) for k in squad_tip_keys])

        def all99():
            for b in slots:
                for k in (16, 17, 18):
                    sf.wr(b + k, "u8", 99)
            self._changed()
            grid.refresh_all()
        ttk.Button(bar, text=T("squad.all99"), command=all99).pack(side="left")
        ttk.Label(bar, text=T("squad.count", n=len(rows)), foreground=MUTED).pack(side="right")

        def avg_text():
            if not slots:
                return ""
            n = len(slots)
            av = [sum(sf.buf[b + k] for b in slots) / n for k in (16, 17, 18)]
            return T("squad.avg", c=f"{av[0]:.1f}", t=f"{av[1]:.1f}", f=f"{av[2]:.1f}")
        self._live_label(bar, avg_text, foreground=MUTED).pack(side="left", padx=12)

        def formation_text():
            # Two bytes per manager: active selection and saved backup.
            off = 51 + 2 * self.mi
            names = {
                1: T("squad.system_manual"),
                2: "4-4-2",
                3: "3-5-2",
                4: "3-4-3",
            }
            active_v, backup_v = sf.buf[off], sf.buf[off + 1]
            active = names.get(active_v, T("squad.system_unknown", value=active_v))
            backup = names.get(backup_v, T("squad.system_unknown", value=backup_v))
            return T("squad.formation_info", active=active, backup=backup)
        self._live_label(bar, formation_text, foreground=FG).pack(side="left", padx=12)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._note(host, T("squad.hint")).pack(anchor="w", padx=10, pady=(0, 8))

    # all players of the save
    def _pg_players(self, host):
        sf = self.sf
        club_ids = sorted({sf.buf[PB + 37 * i + 36] for i in range(151) if sf.buf[PB + 37 * i]})
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("pl.search")).pack(side="left")
        q = tk.StringVar()
        ttk.Entry(bar, textvariable=q, width=22).pack(side="left", padx=(6, 14))
        ttk.Label(bar, text=T("pl.club")).pack(side="left")
        cb = ttk.Combobox(bar, state="readonly", width=28,
                          values=[T("pl.all")] + [self._club_label(c) for c in club_ids])
        cb.current(0)
        cb.pack(side="left", padx=6)
        count = ttk.Label(bar, foreground=MUTED)
        count.pack(side="right")
        c = _tl("pl.cols")
        xcols = _tl("pl.extra_cols")
        labels = [c[0], c[1], xcols[0], c[2], c[3], c[4], c[5], c[6], xcols[1],
                  xcols[2], c[7], c[8], c[9]]
        widths = (175, 48, 78, 78, 72, 62, 78, 85, 84, 112, 74, 78, 180)
        pl_tips = ["player", "age", "initial_average", "condition_base", "technique_base",
                   "form_base", "position_value", "role_group", "preferred_side", "owner",
                   "league_goals", "league_appearances", "current_club"]
        grid = EditableGrid(host, [("#", 42)] + [(t, w, "w" if i in (0, 12) else "center")
                                                  for i, (t, w) in enumerate(zip(labels, widths))],
                            height=16, tips=[_tip("index")] + [_tip(k) for k in pl_tips])
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 4))

        def draw(*_):
            f = q.get().upper()
            sel = cb.current()
            club = club_ids[sel - 1] if sel > 0 else None
            rows = []
            for i in range(151):
                o = PB + 37 * i
                if not sf.buf[o] or (club is not None and sf.buf[o + 36] != club):
                    continue
                if f and f not in sf.get_str(o, 26):
                    continue
                rows.append([
                    i, self._txt(o, 26), self._num(o + 26),
                    D(lambda o=o: str(self.sf.buf[o + 27])),
                    self._num(o + 28), self._num(o + 29), self._num(o + 30),
                    self._num(o + 31), D(lambda o=o: pos4(self.sf.buf[o + 31])),
                    self._num(o + 32), self._player_owner_cell(o + 33),
                    self._num(o + 34), self._num(o + 35), self._club_cell(o + 36),
                ])
            grid.set_rows(rows)
            count.config(text=T("pl.count", n=len(rows)))
        q.trace_add("write", draw)
        cb.bind("<<ComboboxSelected>>", draw)
        draw()
        self._note(host, T("pl.hint")).pack(anchor="w", padx=10, pady=(0, 8))

    # transfer list slots
    def _pg_market(self, host):
        sf = self.sf
        rows = []
        # The actual transfer market contains 12 slots: 100..111.
        for i in range(100, 112):
            b = LB + 52 * i
            pi = sf.buf[b + 15]
            if not pi or sf.is_cheater_slot(b):
                continue
            pb = PB + 37 * pi
            rows.append([
                i, sf.get_str(pb, 26), D(lambda pb=pb: pos4(self.sf.buf[pb + 31])),
                self._num(b + 3), self._num(b + 9), self._num(b + 12),
                self._num(b + 13), self._num(b + 14), D(lambda b=b: str(self.sf.buf[b + 15])),
                self._num(b + 16), self._num(b + 17), self._num(b + 18),
                self._num(b + 19), self._num(b + 20), self._num(b + 21, "i8"),
                self._num(b + 22), self._num(b + 23), self._num(b + 24),
                D(lambda b=b: str(self.sf.buf[b + 27])), self._num(b + 40, "i32"),
                self._hex_bytes(b + 44, 4), self._dword_hex(b + 48),
            ])
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("mk.count", n=len(rows)), foreground=MUTED).pack(side="right")
        c = _tl("mk.cols")
        widths = (175, 58, 72, 66, 72, 88, 78, 68, 70, 62, 62, 62, 66, 82, 76,
                  82, 72, 80, 90, 92, 86)
        market_tip_keys = ["index", "player", "role_group", "offer_refusals", "state_flags", "loan",
                           "suspension_injury", "training_factor", "player_index", "condition_current",
                           "technique_current", "form_current", "freshness", "training_program",
                           "match_rating", "offering_club", "injury_type", "contract_status",
                           "unknown_byte27", "market_value", "unknown_bytes44", "notification_pointer"]
        columns = [("#", 42)] + [(t, w, "w" if j == 0 else "center")
                                  for j, (t, w) in enumerate(zip(c, widths))]
        EditableGrid(host, columns, rows, height=12,
                     tips=[_tip(k) for k in market_tip_keys]).pack(
            fill="both", expand=True, padx=10, pady=(0, 4))
        self._note(host, T("mk.hint")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_stadium(self, host):
        o = self._mo()
        body = self._scroll_page(host)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        sizes = _tl("lists.sizes")
        grades = [T("lists.grade_1"), "2", "3", "4", "5", T("lists.grade_6")]
        amp = self._labeled(body, T("std.expansions"), row=0, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=(10, 5))
        top = ttk.Frame(amp)
        top.pack(anchor="w", pady=(0, 6))
        self._field(top, 0, T("std.ticket"), self._num_field(top, o + 266, width=6))
        self._field(top, 0, T("std.capacity"),
                    self._live_label(top, lambda: f"{self.sf.rd(o + 350, 'i32') + self.sf.rd(o + 358, 'i32'):,}"),
                    col=1)
        names = _tl("std.exp_items")
        choice = {4: (o + 374, sizes, 0), 5: (o + 382, sizes, 0), 6: (o + 390, grades, 1), 7: (o + 398, grades, 1)}
        rows = []
        for k in range(1, 8):
            cur = self._num(o + 350 + 8 * (k - 1), "i32") if k < 4 else self._choice_cell(*choice[k])
            rows.append([names[k - 1], cur, self._num(o + 354 + 8 * (k - 1), "i32"),
                         self._num(o + 404 + 2 * k, "u16")])
        c = _tl("std.exp_cols")
        EditableGrid(amp, [(c[0], 150, "w"), (c[1], 110), (c[2], 120), (c[3], 130)], rows,
                     height=7, tips=[_tip("stadium_item"), _tip("current_value"),
                                    _tip("work_in_progress"), _tip("days_remaining")]).pack(anchor="w")

        aff = self._labeled(body, T("std.attendance"), row=1, column=0, columnspan=2, sticky="ew",
                            padx=10, pady=5)
        self._field(aff, 0, T("std.season_att"), self._num_field(aff, o + 484, "i32", width=12))
        self._field(aff, 1, T("std.record_att"), self._num_field(aff, o + 488, "i32", width=12))
        self._field(aff, 2, T("std.record_opp"), self._club_combo(aff, o + 500))
        self._field(aff, 3, T("std.min_att"), self._num_field(aff, o + 492, "i32", width=12))
        self._field(aff, 4, T("std.min_opp"), self._club_combo(aff, o + 504))
        self._field(aff, 0, T("std.home_games"), self._num_field(aff, o + 476, "u16", width=12), col=1)

        def avg_att():
            n = self.sf.rd(o + 476, 'u16')
            return f"{self.sf.rd(o + 484, 'i32') / n:,.0f}" if n else "–"
        self._field(aff, 1, T("std.avg_att"), self._live_label(aff, avg_att), col=1)

    def _choice_cell(self, off, labels, base):
        buf = self.sf.buf

        def get():
            i = buf[off] - base
            return labels[i] if 0 <= i < len(labels) else f"? ({buf[off]})"

        def set_(text):
            t = text.strip().lower()
            for i, lab in enumerate(labels):
                if t == lab.lower() or t == str(i + base):
                    buf[off] = i + base
                    self.sf.dirty = True
                    self._changed()
                    return True
            return False
        return E(get, set_)

    def _loan_date(self, b_day, b_year):
        buf = self.sf.buf

        def get():
            d, mth, y = buf[b_day], buf[b_day + 2], buf[b_year] | (buf[b_year + 1] << 8)
            return "–" if not (d or y) else f"{d:02d}/{mth + 1:02d}/{y}"

        def set_(text):
            text = text.strip()
            if text in ("", "–", "-", "0"):
                d, mth, y = 0, 0, 0
            else:
                try:
                    d, mth, y = (int(t) for t in re.split(r"[/.\-\s]+", text))
                except ValueError:
                    return False
                if not (1 <= d <= 31 and 1 <= mth <= 12 and 0 <= y <= 65535):
                    return False
                mth -= 1
            buf[b_day], buf[b_day + 2] = d, mth
            buf[b_year], buf[b_year + 1] = y & 255, y >> 8
            self.sf.dirty = True
            self._changed()
            return True
        return E(get, set_)

    def _pg_loans(self, host):
        o = self._mo()
        rows = []
        mi = self.mi
        others = [k for k in range(self.sf.n_managers) if k != mi]

        def lender(g):
            if g == 0:
                return T("loan.bank")
            if g - 1 < len(others):
                k = others[g - 1]
                return T("mgr.item", n=k + 1, name=self.sf.manager_name(k))
            return T("loan.lender", n=g)
        for g in range(5):
            for i in range(3):
                b = o + 508 + (g * 3 + i) * 18
                rows.append([lender(g), i + 1, self._num(b, "i32"), self._num(b + 4, "i32"),
                             self._num(b + 12, "u16"), self._loan_date(b + 8, b + 14), self._loan_date(b + 9, b + 16)])
        c = _tl("loan.cols")
        sf = self.sf
        tot = ttk.Frame(host)
        tot.pack(fill="x", padx=10, pady=(10, 0))
        ttk.Label(tot, text=T("loan.total") + ":").pack(side="left")
        self._live_label(tot, lambda: f"{sum(sf.rd(o + 508 + 18 * k, 'i32') for k in range(15)):,}",
                         font=H1_FONT).pack(side="left", padx=(6, 24))
        ttk.Label(tot, text=T("loan.interest_total") + ":").pack(side="left")
        self._live_label(tot, lambda: f"{sum(sf.rd(o + 512 + 18 * k, 'i32') for k in range(15)):,}",
                         font=H1_FONT).pack(side="left", padx=6)
        EditableGrid(host, [(c[0], 190, "w"), ("#", 45), (c[1], 110), (c[2], 120), (c[3], 70),
                            (c[4], 110), (c[5], 110)], rows, height=15,
                     tips=[_tip("lender"), _tip("loan_number"), _tip("loan_amount"),
                           _tip("monthly_interest"), _tip("interest_rate"), _tip("start_date"),
                           _tip("end_date")]).pack(fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("loan.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_sponsors(self, host):
        mi = self.mi
        a = 33918 + 36 * mi
        body = self._scroll_page(host)
        top = ttk.Frame(body)
        top.pack(fill="x", padx=10, pady=(10, 5))
        shirt, board, tv, adcost = T("sp.shirt"), T("sp.board"), T("sp.tv"), T("sp.adcost")
        ent = ttk.LabelFrame(top, text=T("sp.income"), padding=8)
        ent.pack(side="left", fill="y", padx=(0, 10))
        rows = [[shirt, self._num(a, "i32")]]
        rows += [[f"{board} {k + 1}", self._num(a + 4 + 4 * k, "i32")] for k in range(6)]
        rows += [[tv, self._num(a + 28, "i32")], [adcost, self._num(a + 32, "i32")]]
        EditableGrid(ent, [(T("sp.item"), 150, "w"), (T("sp.amount"), 120)], rows,
                     height=len(rows), tips=[_tip("sponsor_item"), _tip("amount")]).pack()
        con = ttk.LabelFrame(top, text=T("sp.contracts"), padding=8)
        con.pack(side="left", fill="y")
        spaces = [(shirt, 33462 + 2 * mi)] + [(f"{board} {k + 1}", 33470 + (mi * 6 + k) * 2) for k in range(6)]
        rows = [[lab, self._num(x), self._num(x + 1)] for lab, x in spaces]
        c = _tl("sp.contract_cols")
        EditableGrid(con, [(c[0], 140, "w"), (c[1], 110), (c[2], 100)], rows,
                     height=len(rows), tips=[_tip("sponsor_slot"), _tip("months_remaining"),
                                             _tip("sponsor_count")]).pack()
        off = ttk.LabelFrame(body, text=T("sp.offers"), padding=8)
        off.pack(fill="x", padx=10, pady=5)
        rows = []
        for j in range(10):
            t, b = (mi * 2) * 10 + j, (mi * 2 + 1) * 10 + j
            rows.append([j + 1, self._num(33518 + t), self._num(33598 + 4 * t, "i32"),
                         self._num(33518 + b), self._num(33598 + 4 * b, "i32")])
        c = _tl("sp.offer_cols")
        EditableGrid(off, [(c[0], 80), (c[1], 110), (c[2], 140), (c[3], 130), (c[4], 150)], rows,
                     height=10, tips=[_tip("sponsor"), _tip("shirt_years"), _tip("shirt_amount"),
                                     _tip("boards_years"), _tip("boards_amount")]).pack(anchor="w")
        self._note(body, T("sp.note")).pack(anchor="w", padx=10, pady=(2, 10))

    def _pg_standings(self, host):
        sf = self.sf
        a, b = sf.league_club_range(self.lg)
        recs = []
        for i in range(a, b):
            o = 12357 + 54 * i
            pt = sf.buf[o] + sf.buf[o + 1]
            gd = sf.buf[o + 22] + sf.buf[o + 23] - sf.buf[o + 26] - sf.buf[o + 27]
            recs.append((i, o, pt, gd))
        recs.sort(key=lambda r: (-r[2], -r[3]))
        bar = self._league_bar(host)
        ttk.Button(bar, text=T("st.resort"), command=lambda: self._reload(host)).pack(side="left", padx=6)
        rows = []
        for k, (i, o, _pt, _gd) in enumerate(recs):
            rows.append([k + 1, sf.club_name(i),
                         D(lambda o=o: str(self.sf.buf[o] + self.sf.buf[o + 1])),
                         D(lambda o=o: f"{self.sf.buf[o + 22] + self.sf.buf[o + 23] - self.sf.buf[o + 26] - self.sf.buf[o + 27]:+d}")]
                        + [self._num(o + x) for x in (0, 1, 22, 23, 26, 27, 30, 31, 38, 39, 42, 43)]
                        + [self._num(o + 50, "i32")])
        c = _tl("st.cols")
        widths = (76, 88, 78, 82, 86, 82, 86, 92, 94, 80, 84, 80, 84, 92, 96)
        cols = [("#", 40), (c[0], 180, "w")] + [(t, w) for t, w in zip(c[1:], widths)]
        standing_tips = ["index", "club", "points", "goal_difference", "home_points", "away_points",
                         "home_goals_for", "away_goals_for", "home_goals_against", "away_goals_against",
                         "home_games", "away_games", "home_wins", "away_wins", "home_losses",
                         "away_losses", "historical_points"]
        EditableGrid(host, cols, rows, height=20,
                     tips=[_tip(k) for k in standing_tips]).pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._note(host, T("st.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_results(self, host):
        lg = self.lg
        n, per = ((34, 9) if self.sf.league_team_count == 18 else (38, 10)) if lg == 0 else (38, 10)
        self.md = min(self.md, n - 1)
        bar = self._league_bar(host)
        ms = ttk.Combobox(bar, values=[T("res.round", n=d + 1) for d in range(n)], state="readonly", width=14)
        ms.current(self.md)
        ms.pack(side="left", padx=(10, 6))

        def goto(d):
            self.md = max(0, min(n - 1, d))
            self._reload(host)
        ms.bind("<<ComboboxSelected>>", lambda e: goto(ms.current()))
        ttk.Button(bar, text="◀", width=3, command=lambda: goto(self.md - 1)).pack(side="left", padx=2)
        ttk.Button(bar, text="▶", width=3, command=lambda: goto(self.md + 1)).pack(side="left", padx=2)
        b = 59 + (lg * 38 + self.md) * 20
        rows = [[k + 1, self._num(b + 2 * k), "–", self._num(b + 2 * k + 1)] for k in range(per)]
        EditableGrid(host, [(T("res.match"), 80), (T("c.home"), 80), ("", 30), (T("c.away"), 80)], rows,
                     height=per, tips=[_tip("match_no"), _tip("home_goals"), _tip("score_separator"),
                                      _tip("away_goals")]).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(host, T("res.note")).pack(anchor="w", padx=10)

    def _pg_calendar(self, host):
        body = self._scroll_page(host)
        lf = ttk.LabelFrame(body, text=T("cal.season"), padding=8)
        lf.pack(fill="x", padx=10, pady=(10, 5))
        self._field(lf, 0, T("cal.day"), self._num_field(lf, 27972, "i32", width=8))
        for i in range(3):
            self._field(lf, 1 + i, T("cal.next", n=i + 1), self._num_field(lf, 28432 + i, width=6))
        bar = self._league_bar(body)
        ttk.Label(bar, text=T("cal.matches"), foreground=MUTED).pack(side="left", padx=6)
        f = 20 * self.lg
        n = self.sf.league_team_count // 2 if self.lg == 0 else 10
        rows = [[k + 1, self._club_cell(27900 + f + 2 * k), self._club_cell(27901 + f + 2 * k)]
                for k in range(n)]
        EditableGrid(body, [("#", 40), (T("c.home_team"), 250, "w"), (T("c.away_team"), 250, "w")],
                     rows, height=n, tips=[_tip("index"), _tip("home_team"),
                                           _tip("away_team")]).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(body, T("cal.note")).pack(anchor="w", padx=10, pady=(0, 6))
        pf = ttk.LabelFrame(body, text=T("cal.perm"), padding=8)
        pf.pack(fill="x", padx=10, pady=5)
        self._value_grid(pf, 28244 + 20 * self.lg, 20, 10,
                         description=T("tip.calendar_order")).pack(anchor="w")
        self._note(body, T("cal.perm_note")).pack(anchor="w", padx=10, pady=(2, 10))

    def _pg_cup_state(self, host):
        body = self._scroll_page(host)
        cups = _tl("lists.cups")
        top = ttk.Frame(body)
        top.pack(fill="x", padx=10, pady=(10, 5))
        rel = ttk.LabelFrame(top, text=T("cup.relegation"), padding=8)
        rel.pack(side="left", fill="y", padx=(0, 10))
        self._field(rel, 0, T("cup.first_leg"), self._num_field(rel, 28007, width=6))
        self._field(rel, 1, T("cup.outcome"), self._num_field(rel, 34367, width=6))
        rnd = ttk.LabelFrame(top, text=T("cup.round"), padding=8)
        rnd.pack(side="left", fill="y", padx=(0, 10))
        for c, name in enumerate(cups):
            self._field(rnd, c, name, self._num_field(rnd, 28233 + c, width=6))
        leg = ttk.LabelFrame(top, text=T("cup.legs_played"), padding=8)
        leg.pack(side="left", fill="y")
        for c in range(3):
            self._field(leg, c, cups[c + 1], self._num_field(leg, 28241 + c, width=6))
        lf = ttk.LabelFrame(body, text=T("cup.qualified"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 27978, 10, 10,
                         description=T("tip.european_qualifiers")).pack(anchor="w")
        lf = ttk.LabelFrame(body, text=T("cup.slots"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 27988, 18, 6,
                         description=T("tip.european_places")).pack(anchor="w")

    def _pg_cup_ties(self, host):
        body = self._scroll_page(host)
        bar = ttk.Frame(body)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("cup.label")).pack(side="left")
        cb = ttk.Combobox(bar, values=_tl("lists.cups"), state="readonly", width=22)
        cb.current(self.cup)
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.cup = cb.current()
            self._reload(host)
        cb.bind("<<ComboboxSelected>>", picked)
        c = self.cup
        rows = [[k + 1, self._club_cell(28009 + 32 * c + 2 * k), self._club_cell(28010 + 32 * c + 2 * k),
                 self._num(28304 + 32 * c + 2 * k), self._num(28305 + 32 * c + 2 * k)] for k in range(16)]
        EditableGrid(body, [("#", 40), (T("c.home_team"), 240, "w"), (T("c.away_team"), 240, "w"),
                            (T("cup.goals_h"), 60), (T("cup.goals_a"), 60)], rows,
                     height=16, tips=[_tip("index"), _tip("home_team"), _tip("away_team"),
                                     _tip("home_goals"), _tip("away_goals")]).pack(
                         anchor="w", padx=10, pady=(0, 6))
        lf = ttk.LabelFrame(body, text=T("cup.first_leg_goals"), padding=8)
        lf.pack(fill="x", padx=10, pady=5)
        self._value_grid(lf, 28137, 96, 16,
                         description=T("tip.european_first_leg_goals")).pack(anchor="w")
        self._note(body, T("cup.note")).pack(anchor="w", padx=10, pady=(2, 10))

    def _pg_clubs(self, host):
        sf = self.sf
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("cl.search")).pack(side="left")
        q = tk.StringVar()
        ttk.Entry(bar, textvariable=q, width=24).pack(side="left", padx=6)
        count = ttk.Label(bar, foreground=MUTED)
        count.pack(side="right")
        cols = [("#", 45), (T("c.name"), 200, "w")] + [(t, 52) for t in _tl("cl.cols")]
        club_tips = [_tip("index"), _tip("club_name"), _tip("club_base"),
                     _tip("club_condition_home"), _tip("club_condition_away"),
                     _tip("club_condition_third"), _tip("club_technique_home"),
                     _tip("club_technique_away"), _tip("club_technique_third"),
                     _tip("club_form_home"), _tip("club_form_away"), _tip("club_form_third"),
                     _tip("club_status")]
        grid = EditableGrid(host, cols, height=16, tips=club_tips)
        grid.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        def draw(*_):
            f = q.get().upper()
            rows = []
            for i in range(200):
                n = sf.club_name(i)
                if not n or (f and f not in n):
                    continue
                o = CB + 34 * i
                rows.append([i, self._txt(o, 23)] + [self._num(o + k) for k in range(23, 34)])
            grid.set_rows(rows)
            count.config(text=T("cl.count", n=len(rows)))
        q.trace_add("write", draw)
        draw()
        note = T("cl.note")
        if sf.league_team_count == 20:
            for old, new in (("0–17", "0–19"), ("18–37", "20–39"), ("38–57", "40–59"),
                             ("0-17", "0-19"), ("18-37", "20-39"), ("38-57", "40-59")):
                note = note.replace(old, new)
        self._note(host, note).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_ext_standings(self, host):
        sf = self.sf
        rows = []
        for i in sf.club_ids(64):
            o = 12357 + 54 * i
            rows.append([i, sf.club_name(i), self._hexrun(o + 4, 8), self._hexrun(o + 13, 8)]
                        + [self._num(o + x) for x in (2, 3, 24, 25, 28, 29, 40, 41, 44, 45, 46)]
                        + [self._hexrun(o + 32, 6)])
        c = _tl("xs.cols")
        cols = [("#", 40), (T("c.club"), 190, "w"), (c[0], 235), (c[1], 235)] + [(t, 48) for t in c[2:13]] \
            + [(c[13], 160)]
        ext_tips = [_tip("index"), _tip("club_name"), _tip("external_series_a"),
                    _tip("external_series_b")] + [
                        T("tip.club_record_unknown", offset=x) for x in (2, 3, 24, 25, 28, 29, 40, 41, 44, 45, 46)
                    ] + [_tip("club_record_tail")]
        EditableGrid(host, cols, rows, height=20, tips=ext_tips).pack(
            fill="both", expand=True, padx=10, pady=(10, 6))
        self._note(host, T("xs.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_options(self, host):
        """Display the game's original option checkboxes and speed control."""
        body = self._scroll_page(host)
        lf = ttk.LabelFrame(body, text=T("opt.panel"), padding=8)
        lf.pack(fill="x", padx=10, pady=(10, 5))

        series = _tl("opt.series")
        items = _tl("opt.items")
        self._opt_vars = []

        def check(parent, off, row, col):
            var = tk.BooleanVar(value=bool(self.sf.buf[off]))

            def toggled(off=off, var=var):
                self.sf.wr(off, "u8", 1 if var.get() else 0)
                self._changed()

            ttk.Checkbutton(parent, variable=var, command=toggled).grid(
                row=row, column=col, padx=14, pady=2)
            self._opt_vars.append(var)

        for col, name in enumerate(series, start=1):
            ttk.Label(lf, text=name, font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, padx=14, pady=(0, 4))

        for row, name in enumerate(items, start=1):
            ttk.Label(lf, text=name).grid(row=row, column=0, sticky="w", padx=(0, 10))
            for col in range(3):
                check(lf, 33447 + 3 * col + row - 1, row, col + 1)
        self._note(lf, T("opt.note")).grid(
            row=len(items) + 1, column=0, columnspan=4, sticky="w", padx=4, pady=(5, 0))

        other = ttk.LabelFrame(body, text=T("opt.other"), padding=8)
        other.pack(fill="x", padx=10, pady=5)
        for row, name in enumerate(_tl("opt.others")):
            ttk.Label(other, text=name).grid(row=row, column=0, sticky="w", padx=(0, 10))
            check(other, 33456 + row, row, 1)

        speed = ttk.LabelFrame(body, text=T("opt.speed"), padding=8)
        speed.pack(fill="x", padx=10, pady=(5, 10))
        self._field(speed, 0, T("opt.speed_value"),
                    ValueEntry(speed, self._num_range(34222, "u16", 0, 70), width=7))
        self._note(speed, T("opt.speed_note")).grid(
            row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))

    def _pg_raw(self, host):
        body = self._scroll_page(host)

        # Postponed fixtures: 20 records of five bytes each.
        lf = ttk.LabelFrame(body, text=T("raw.block5"), padding=8)
        lf.pack(fill="x", padx=10, pady=(10, 5))
        rows = [[k + 1] + [self._num(5457 + 5 * k + j) for j in range(5)] for k in range(20)]
        c = _tl("raw.cols5")
        recovery_tips = [
            _tip("index"), T("tip.recovery_marker"), T("tip.recovery_day_index"),
            T("tip.recovery_matchday"), T("tip.recovery_league"), T("tip.recovery_fixture"),
        ]
        EditableGrid(lf, [("#", 40)] + [(t, 70) for t in c], rows, height=10,
                     tips=recovery_tips).pack(anchor="w")
        self._note(lf, T("raw.recovery_note")).pack(anchor="w", pady=(6, 0))

        # Display identified fields separately from unassigned data ranges.
        unknown = ttk.LabelFrame(body, text=T("raw.unknown_area"), padding=8)
        unknown.pack(fill="x", padx=10, pady=5)

        game = ttk.LabelFrame(unknown, text=T("raw.game_type"), padding=6)
        game.pack(fill="x", pady=3)
        self._field(game, 0, T("raw.end_year_code"), self._num_field(game, 34063, "u16", width=9))
        def end_year_text():
            value = self.sf.rd(34063, "u16")
            known = {
                22222: T("raw.endyear_endless_historical"),
                22251: T("raw.endyear_endless"),
                1964: T("raw.endyear_one_historical"),
                1993: T("raw.endyear_one"),
                1966: T("raw.endyear_three_historical"),
                1995: T("raw.endyear_three"),
            }
            return known.get(value, T("raw.endyear_other", value=value))
        self._field(game, 0, T("raw.end_year_meaning"), self._live_label(game, end_year_text), col=1)
        self._note(game, T("tip.raw_34063")).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))

        part = ttk.LabelFrame(unknown, text=T("raw.unknown_34065"), padding=6)
        part.pack(fill="x", pady=3)
        self._value_grid(part, 34065, 30, 20, w=38,
                         description=T("tip.raw_34065")).pack(anchor="w")

        # Four bytes preceding the rules selector have no assigned function.
        part = ttk.LabelFrame(unknown, text=T("raw.unknown_34095"), padding=6)
        part.pack(fill="x", pady=3)
        self._value_grid(part, 34095, 4, 4, w=42,
                         description=T("tip.raw_34095")).pack(anchor="w")

        rule = ttk.LabelFrame(unknown, text=T("raw.rule_2026"), padding=6)
        rule.pack(fill="x", pady=3)
        rule_options = [T("raw.rules_original"), T("raw.rules_2026")]
        self._field(rule, 0, T("raw.rule_value"),
                    ValueEntry(rule, self._choice_cell(34099, rule_options, 0), width=24))
        self._note(rule, T("tip.rule_2026")).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))

        poach = ttk.LabelFrame(unknown, text=T("raw.poach_counts"), padding=6)
        poach.pack(fill="x", pady=3)
        poach_rows = [[T("raw.manager_number", n=i + 1)] +
                      [self._num(34100 + i * 4 + j) for j in range(4)] for i in range(4)]
        poach_cols = [(T("raw.poacher"), 145, "w")] + [
            (T("raw.owner_manager", n=j + 1), 90) for j in range(4)]
        EditableGrid(poach, poach_cols, poach_rows, height=4,
                     tips=[T("tip.poach_count_row")] + [T("tip.poach_count") for _ in range(4)]).pack(anchor="w")
        self._note(poach, T("raw.poach_note")).pack(anchor="w", pady=(4, 0))

        small = ttk.LabelFrame(unknown, text=T("raw.additional_fields"), padding=6)
        small.pack(fill="x", pady=3)
        self._field(small, 0, T("raw.unknown_34116_label"), self._num_field(small, 34116, width=6))
        self._field(small, 0, T("raw.debt_mask"), self._num_field(small, 34117, width=6), col=1)
        self._note(small, T("tip.debt_mask")).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))

        derby = ttk.LabelFrame(unknown, text=T("raw.derby_stakes"), padding=6)
        derby.pack(fill="x", pady=3)
        stake_labels = _tl("raw.derby_levels")
        def stake_cell(off):
            def get():
                value = self.sf.buf[off]
                return stake_labels[value] if 0 <= value < len(stake_labels) else T("raw.unknown_value", value=value)
            def set_(text):
                try:
                    value = stake_labels.index(text)
                except ValueError:
                    return False
                self.sf.buf[off] = value
                self.sf.dirty = True
                self._changed()
                return True
            return Ch(get, set_, stake_labels)
        derby_rows = [[T("raw.manager_number", n=i + 1), stake_cell(34118 + i)] for i in range(4)]
        EditableGrid(derby, [(T("raw.manager"), 145, "w"), (T("raw.stake"), 140)],
                     derby_rows, height=4,
                     tips=[T("tip.manager_index"), T("tip.derby_stake")]).pack(anchor="w")

        youth = ttk.LabelFrame(unknown, text=T("raw.youth_counts"), padding=6)
        youth.pack(fill="x", pady=3)
        youth_rows = [[T("raw.manager_number", n=i + 1), self._num(34122 + i),
                       self._num(34126 + i)] for i in range(4)]
        EditableGrid(youth, [(T("raw.manager"), 145, "w"), (T("raw.promotions"), 155),
                             (T("raw.youth_poached"), 170)], youth_rows, height=4,
                     tips=[T("tip.manager_index"), T("tip.youth_promotions"),
                           T("tip.youth_poach")]).pack(anchor="w")
        self._note(youth, T("raw.youth_note")).pack(anchor="w", pady=(4, 0))

        part = ttk.LabelFrame(unknown, text=T("raw.unknown_34130"), padding=6)
        part.pack(fill="x", pady=3)
        self._value_grid(part, 34130, 85, 20, w=38,
                         description=T("tip.raw_34130")).pack(anchor="w")

        part = ttk.LabelFrame(unknown, text=T("raw.stadium_lockout"), padding=6)
        part.pack(fill="x", pady=3)
        self._value_grid(part, 34215, 7, 7, w=48,
                         description=T("tip.stadium_lockout")).pack(anchor="w")

        # Calendar pointer and mask.
        cal = ttk.LabelFrame(body, text=T("raw.calendar_title"), padding=8)
        cal.pack(fill="x", padx=10, pady=5)
        index_row = ttk.Frame(cal)
        index_row.pack(fill="x")
        self._field(index_row, 0, T("raw.calendar_index"), self._num_field(index_row, 34226, width=6))
        self._note(cal, T("raw.calendar_index_note")).pack(anchor="w", pady=(2, 5))
        mask = ttk.LabelFrame(cal, text=T("raw.calendar_mask"), padding=6)
        mask.pack(fill="x", pady=3)
        self._value_grid(mask, 34227, 95, 19, w=38,
                         description=T("tip.calendar_mask")).pack(anchor="w")

        # Eight signed countdowns for the training camps (DGROUP:0620).
        # Training-ground availability counters, stored as signed 16-bit values.
        daily = ttk.LabelFrame(body, text=T("raw.training_camps"), padding=8)
        daily.pack(fill="x", padx=10, pady=5)

        def camp_status(off):
            value = self.sf.rd(off, "i16")
            if value < 0:
                return T("raw.camp_open_days", days=-value)
            if value > 0:
                return T("raw.camp_closed_days", days=value)
            return T("raw.camp_changeover")

        camp_rows = [[i + 1, 34322 + 2 * i,
                      D(lambda off=34322 + 2 * i: camp_status(off)),
                      self._num(34322 + 2 * i, "i16")]
                     for i in range(8)]
        EditableGrid(daily,
                     [(T("raw.camp_number"), 72), (T("raw.offset"), 72),
                      (T("raw.camp_status"), 150), (T("raw.camp_counter"), 150)],
                     camp_rows, height=8,
                     tips=[T("tip.camp_number"), T("tip.save_offset"),
                           T("tip.camp_status"), T("tip.camp_counter")]).pack(anchor="w")
        self._note(daily, T("raw.camp_note")).pack(anchor="w", pady=(6, 0))

        extra = ttk.LabelFrame(body, text=T("raw.trailing_values"), padding=8)
        extra.pack(fill="x", padx=10, pady=5)
        byte_row = ttk.Frame(extra)
        byte_row.pack(fill="x")
        self._field(byte_row, 0, T("raw.unknown_byte"), self._num_field(byte_row, 34338, width=6))
        dword_rows = [[i + 1, 34339 + 4 * i, self._num(34339 + 4 * i, "u32")]
                      for i in range(7)]
        EditableGrid(extra, [("#", 40), (T("raw.offset"), 80), (T("raw.dword_value"), 150)],
                     dword_rows, height=7,
                     tips=[_tip("index"), T("tip.save_offset"), T("tip.trailing_dword")]).pack(anchor="w", pady=(6, 0))
        self._note(body, T("raw.note")).pack(anchor="w", padx=10, pady=(2, 10))

    def _pg_series(self, host):
        sf = self.sf
        rows = [[i, sf.club_name(i)] + [self._num(H + 2560 + 21 * i + k) for k in range(21)]
                for i in sf.club_ids(64)]
        EditableGrid(host, [("#", 40), (T("c.club"), 190, "w")] + [(str(k + 1), 42) for k in range(21)],
                     rows, height=18, tips=[_tip("index"), _tip("club_name")] +
                     [T("tip.series_column", number=k + 1) for k in range(21)]).pack(
                         fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("ser.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_records(self, host):
        sf = self.sf
        ids = sf.club_ids(64)
        if not ids:
            ttk.Label(host, text=T("rec.none"), foreground=MUTED).pack(padx=10, pady=10)
            return
        if self.rec_club not in ids:
            self.rec_club = ids[0]
        bar = ttk.Frame(host)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ttk.Label(bar, text=T("pl.club")).pack(side="left")
        cb = ttk.Combobox(bar, values=[self._club_label(i) for i in ids], state="readonly", width=30)
        cb.current(ids.index(self.rec_club))
        cb.pack(side="left", padx=6)

        def picked(_e):
            self.rec_club = ids[cb.current()]
            self._reload(host)
        cb.bind("<<ComboboxSelected>>", picked)
        i = self.rec_club
        rows = [[lab, self._pair(H + 3988 + 8 * i + k, False), self._club_cell(H + 4500 + 8 * i + k)]
                for k, lab in enumerate(_tl("lists.records"))]
        c = _tl("rec.cols")
        EditableGrid(host, [(c[0], 160, "w"), (c[1], 110), (c[2], 250, "w")], rows,
                     height=8, tips=[_tip("record"), _tip("record_value"),
                                    _tip("record_opponent")]).pack(anchor="w", padx=10, pady=(0, 6))
        self._note(host, T("rec.note")).pack(anchor="w", padx=10)

    def _pg_versus(self, host):
        sf = self.sf
        rows = []
        for i in sf.club_ids(64):
            b = H + (self.mi * 64 + i) * 10
            rows.append([i, sf.club_name(i)] + [self._pair(b + j, True) for j in range(10)])
        home, away = T("c.home"), T("c.away")
        cols = [("#", 40), (T("c.club"), 190, "w")] + [(f"{k} {s}", 62) for k in range(1, 6) for s in (home, away)]
        versus_tips = [_tip("index"), _tip("club_name")] + [
            _tip("versus_home") if j % 2 == 0 else _tip("versus_away") for j in range(10)
        ]
        EditableGrid(host, cols, rows, height=18, tips=versus_tips).pack(
            fill="both", expand=True, padx=10, pady=10)
        self._note(host, T("vs.note")).pack(anchor="w", padx=10, pady=(0, 8))

    def _pg_messages(self, host):
        sf = self.sf
        msgs = sf.read_messages()
        body = self._scroll_page(host)
        for idx, (m, _ptr, text) in enumerate(msgs):
            ttk.Label(body, text=T("msg.manager", n=m + 1, name=sf.manager_name(m)),
                      font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
            box = tk.Text(body, height=4, width=80, wrap="word", font=("Segoe UI", 10),
                          relief="solid", bd=1, undo=True)
            box.insert("1.0", text)
            box.pack(anchor="w", padx=10)

            def typed(_e, idx=idx, box=box):
                t = box.get("1.0", "end-1c")
                if len(t) > 240:
                    box.delete("1.0+240c", "end-1c")
                    t = t[:240]
                t = t.replace("\n", "^")
                if t != msgs[idx][2]:
                    msgs[idx][2] = t
                    sf.write_messages(msgs)
                    self._changed()
            box.bind("<KeyRelease>", typed)
        if not msgs:
            self._note(body, T("msg.none")).pack(anchor="w", padx=10, pady=10)
        self._note(body, T("msg.note")).pack(anchor="w", padx=10, pady=(10, 10))


def _resource_path(rel):
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, rel)


# pick the UI language from the system locale
def _guess_language():
    import locale
    try:
        name = (locale.getlocale()[0] or "").lower()
    except Exception:
        name = ""
    name = name or os.environ.get("LANG", "").lower()
    if name.startswith(("it", "ital")):
        return "it"
    if name.startswith(("de", "germ", "deut")):
        return "de"
    return "en"


# program entry point
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    root = tk.Tk()
    _TR.set_language(_guess_language())
    root.title(APP_TITLE)
    root.geometry("1180x780")
    root.minsize(780, 560)
    root.configure(bg=BG)
    try:
        root.iconbitmap(default=_resource_path(os.path.join("assets", ICON_FILE)))
    except Exception:
        pass
    apply_editor_style(root)

    def retitle():
        sf = panel.sf
        name = f" – {os.path.basename(sf.path)}" if sf else ""
        root.title(f"{APP_TITLE}{name}{' *' if panel.is_dirty() else ''}")
    panel = SavegamePanel(root, standalone=True, on_change=retitle)
    panel.pack(fill=tk.BOTH, expand=True)

    def on_close():
        if panel.confirm_discard():
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)

    target = argv[0] if argv else os.getcwd()
    if os.path.isfile(target):
        panel.set_dir(os.path.dirname(os.path.abspath(target)))
        if panel.load_file(target):
            retitle()
    else:
        panel.set_dir(target)
    root.mainloop()


if __name__ == "__main__":
    main()