from __future__ import annotations
import json
import os
import re
import sys
import unicodedata
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from PIL import Image, ImageTk, ImageDraw

def _hex_palette(s: str, scale: int = 1) -> list[tuple[int, int, int]]:
    return [
        (min(255, int(s[i:i+2], 16) * scale),
         min(255, int(s[i+2:i+4], 16) * scale),
         min(255, int(s[i+4:i+6], 16) * scale))
        for i in range(0, len(s) - 5, 6)
    ]

_PAL_GREYSCALE      = _hex_palette("000000808080404040C0C0C0202020A0A0A0606060E0E0E0101010909090505050D0D0D0303030B0B0B0707070F0F0F0", scale=1)
_PAL_TITLE          = _hex_palette("000000F0F0F0D0E0F0B0D0F090C0F080A0E04070C03060B0105090103070001060001040001030608030407010406010305010304010809090606060304050203040706010F0C0B0F0B090F09070E08060C06040B04030903020701000501000", scale=1)
_PAL_ADVERTISEMENTS = _hex_palette("000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A06020704010000050C0C0E0806040402020705030604030503020F0F0F0A08060202040", scale=1)
_PAL_NORMAL         = _hex_palette("000000A0A0C08080A0707090606080505070404060303050000070907050B0A080D0C0B0506010607020608030709040600010900010B00020C07020A060207040103040C0F0F000B0A070908050806040604030503020F0F0F0C030C0000000", scale=1)
_PAL_LOADER         = _hex_palette("10000090A0C01020102030302060201060301060801080A01060D00090C000A0C020A0C000A0C010A0C020A0C020C0F040200040502080100070401040606040709090603080706070A0A0004000E0D070C0C0B060A0D0B0C0C0D0C0C0F0F0F0", scale=1)

_PAL_NORMAL20       = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040C10303C3C002C281C24201420181018100C140C083C3C3C300C300000003F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4)

_PAL_ADVERTISEMENTS20 = _hex_palette("0000002828302020281C1C2418182014141C1010180C0C1400001C241C142C282034302C141804181C0818200C1C24101800042400042C0008301C082818081C10040000143030382018101008081C140C18100C140C083C3C3C2820180808103F00003B00003800003500003200002F00002C00002900002600002200001F00001C00001900001600001300001000003F36363F2E2E3F27273F1F1F3F17173F10103F08083F00003F2A173F26103F22083F1E00391B003318002D15002713003F3F363F3F2E3F3F273F3F1F3F3E173F3D103F3D083F3D003936003331002D2B002727002121001C1B00161500101000343F17313F102D3F08283F002439002033001D2D00182700363F362F3F2E273F27203F1F183F17103F10083F08003F00003F00003B00003800003500013200012F00012C00012900012600012200011F00011C00011900011600011300011000363F3F2E3F3F273F3F1F3F3E173F3F103F3F083F3F003F3F003939003333002D2D002727002121001C1C001616001010172F3F102C3F082A3F00273F002339001F33001B2D00172736363F2E2F3F27273F1F203F17183F10103F08093F00013F00003F00003B00003800003500003200002F00002C00002900002600002200001F00001C0000190000160000130000103C363F392E3F36273F341F3F32173F2F103F2D083F2A003F2600392000331D002D18002714002111001C0D00160A00103F363F3F2E3F3F273F3F1F3F3F173F3F103F3F083F3F003F3800393200332D002D2700272100211B001C1600161000103F3A373F38343F36313F352F3F332C3F31293F2F273F2E243F2C203F291C3F27183C25173A2316372215342014321F132F1E122D1C112A1A1028190F27180E24170D22160C20140B1D130A1B1209171008150F07120E06100C060E0B050A0803000000000000000000000000000000000000000000000000310A0A31130A311D0A31270A31310A27310A1D310A13310A0A310C0A31170A31220A312D0A2A310A1F310A14310B0A31160A31210A312C0A31310A2B310A20310A15310A0A00000000", scale=4) 

# Bundesliga Manager Hattrick palette (from bmh_palette.h, 256 entries).
# The header stores the values as positional RGBQUAD initialisers; they are
# read here as R, G, B. If the colours ever look red/blue swapped, set this
# flag to True.
_BMH_PALETTE_IS_BGR = True
_PAL_BMH = _hex_palette("0000006894D43068A000346C686864404040B0C4E44C649C1818744C48BC00680000BC0400FC00D4B428A888009458000000006894D43068A000346C686864404040B0C4E44C649C000C1028283000680000BC0400FC0000DCF800A8FC0074E40054800060900070A00080B40098C800ACD800C0EC00DCFC58E0FC90F0FC8000C0F00070606060E000C0744800905800643C00FCF0D8F4E4C0ECD4ACE8C898E0C088D8B478D0A864C89C54C49448BC8838B4802CAC7820A46C149C6808985C001414002424003030003C3C004C4C045858006464107070187878207C8028848430888C3C00002060B00000F0806000EC0000FC004C2C3C3C3C4444445858586868687C7C7C8C8C8CA0A0A0ACACACB8B8B8C8C4C4D4D4D4E0E0E0F0F0F0FFFFFF2020200C0C101C1C20282C30383C444448545458646068747078847C84988894A898A4B8A4B4C8B4C0DCC0D0ECD0E0FCC0C0C0A8A8A80C640C1070141C7C1C24882830943440A0404CAC505CB8606CC47080CC8094D894A8E4ACBCF0C0D8FCD8D8DCFC043060084854005C4414486808685C0C3C8014785C4C606008607C245880087470104098446078000044000030D8FCFCC0ECF0A8DCE494CCD880B8CC6CA4C05C90B44C7CA8406CA03058942444881C347C10247008186404085800004C0C640C145C081C5404244C042840002838002C3000282400707070D0D0002050E0F00000F0A0000C6C14086810086410006010005C100058100C20A41830A82844AC3454B04464B85474BC6884C07894C88CA8CC045C0400500040787408807C9CE0F800342880D4FC64D0FC84CCE84CCCF86CC0F04CC0F480C4D86CC4DC50BCE02CC0E834ACE820A4E854A4DC68B0C450B8C830ACD018B0D05090D43090D81C90D850A8B834A8BC14ACBC54A8A42878D42CC0F8308CC45084BC1494BC207CC454909C3894A41C6CC40898A0587CA01C909C1080AC38949040789C1458BC3864A40884906070780C8884205CA00C5CA04460FC4460DC00005C00007000008400009C0000B00000C40000DC1C28E03848E85464EC7480F0909CF4B4BCF8000000", scale=1)
if _BMH_PALETTE_IS_BGR:
    _PAL_BMH = [(b, g, r) for r, g, b in _PAL_BMH]

BUILTIN_PALETTES: dict[str, list[tuple[int, int, int]]] = {
    "Default":          _PAL_NORMAL,
    "Default 2.0":      _PAL_NORMAL20,
    "Newspaper":        _PAL_GREYSCALE,
    "Sponsors":         _PAL_ADVERTISEMENTS,
    "Sponsors 2.0":     _PAL_ADVERTISEMENTS20,
    "Title":            _PAL_TITLE,
    "Loader":           _PAL_LOADER,
    "BMH":              _PAL_BMH,
}

def _palette_to_flat_rgb(pal: list[tuple[int, int, int]], size: int = 256) -> list[int]:
    flat: list[int] = []
    for r, g, b in pal:
        flat.extend((r, g, b))
    while len(flat) < size * 3:
        flat.extend((0, 0, 0))
    return flat[:size * 3]

# File formats
#
#   BMP (Bundesliga Manager Professional / Eishockey Manager):
#       [W:2][H:2][payload length:2][RLE payload ... offset byte]
#   BMH (Bundesliga Manager Hattrick):
#       [W:2][H:2][payload length:4][RLE payload ... offset byte]
#
# The RLE payload is identical in both. The payload length includes the final
# offset byte. Anything after the payload is an embedded palette (3 bytes/entry).
FMT_BMP = "BMP"
FMT_BMH = "BMH"

_VGA_FORMATS: dict[str, dict[str, int]] = {
    FMT_BMP: {"header_len": 6, "len_bytes": 2},
    FMT_BMH: {"header_len": 8, "len_bytes": 4},
}

DEFAULT_PALETTE_FOR_FORMAT = {
    FMT_BMP: "Default 2.0",
    FMT_BMH: "BMH",
}

EMBEDDED_PALETTE_NAME = "Embedded (file)"

# BMH sprites without a palette of their own use the palette embedded in another
# file of the same folder: (first number, last number, source file number).
SHARED_PALETTE_RULES_BMH = [
    (40, 46, 128),
    (47, 47, 131),
    (48, 48, 128),
]

_MAX_IMG_W = 1280
_MAX_IMG_H = 960


class VgaFile:
    """Result of loading a .VGA/.CP file."""

    def __init__(self, image: Image.Image, fmt: str, trailer: bytes,
                 embedded_palette: list[tuple[int, int, int]] | None):
        self.image = image
        self.fmt = fmt
        self.trailer = trailer                    # raw bytes after the payload
        self.embedded_palette = embedded_palette  # parsed trailer, if a palette


def _decode_vga(data: bytes, fmt: str):
    """Strictly decode `data` as `fmt`.

    Returns (width, height, pixels, trailer) or None when the data is not a
    valid file of that format.
    """
    spec = _VGA_FORMATS[fmt]
    header_len = spec["header_len"]
    if len(data) < header_len + 1:
        return None

    width = data[0] | (data[1] << 8)
    height = data[2] | (data[3] << 8)
    payload_len = int.from_bytes(data[4:header_len], "little")

    if width <= 0 or height <= 0 or width > _MAX_IMG_W or height > _MAX_IMG_H:
        return None
    if payload_len < 1:
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
            value = data[i + 1]
            pixels.extend((value,) * count)
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


def _trailer_to_palette(trailer: bytes) -> list[tuple[int, int, int]] | None:
    """Interpret trailing bytes as an embedded palette (None if they are not one)."""
    n = len(trailer)
    if n == 0 or n % 3 != 0 or n > 256 * 3:
        return None
    entries = n // 3
    if entries < 2:
        return None
    # VGA DAC palettes are 6-bit (0..63) and need scaling up to 8-bit.
    scale = 4 if max(trailer) <= 63 else 1
    return [
        (min(255, trailer[i] * scale),
         min(255, trailer[i + 1] * scale),
         min(255, trailer[i + 2] * scale))
        for i in range(0, n, 3)
    ]


def _decode_vga_auto(data: bytes, prefer: str | None = None):
    """Try BMH and BMP decoding and pick the one that is valid.

    Returns (fmt, (width, height, pixels, trailer)) or None.
    """
    found: dict[str, tuple] = {}
    for fmt in (FMT_BMH, FMT_BMP):
        res = _decode_vga(data, fmt)
        if res is not None:
            found[fmt] = res

    if not found:
        return None
    if len(found) == 1:
        fmt = next(iter(found))
        return fmt, found[fmt]

    # Both decode (practically never happens): prefer the one that leaves no
    # stray bytes / a well-formed palette, then the folder hint, then BMP.
    def score(fmt: str) -> int:
        trailer = found[fmt][3]
        if not trailer:
            return 2
        return 1 if _trailer_to_palette(trailer) is not None else 0

    best = max(found, key=lambda f: (score(f), f == prefer, f == FMT_BMP))
    return best, found[best]


def detect_vga_format(data: bytes, prefer: str | None = None) -> str | None:
    """Return FMT_BMP / FMT_BMH for the given file contents, or None."""
    res = _decode_vga_auto(data, prefer)
    return res[0] if res else None


def load_vga_file(vga_path: str, palette: list[tuple[int, int, int]] | None = None,
                  prefer_fmt: str | None = None) -> VgaFile | None:
    """Load a .VGA/.CP file, auto-detecting BMP vs BMH."""
    if not os.path.isfile(vga_path):
        return None

    try:
        with open(vga_path, "rb") as f:
            data = f.read()

        res = _decode_vga_auto(data, prefer_fmt)
        if res is None:
            return None
        fmt, (width, height, pixels, trailer) = res

        img = Image.frombytes("P", (width, height), pixels)
        embedded = _trailer_to_palette(trailer)
        pal = palette if palette is not None else (embedded or _PAL_NORMAL20)
        img.putpalette(_palette_to_flat_rgb(pal))
        return VgaFile(img, fmt, trailer, embedded)

    except (OSError, ValueError, IndexError):
        return None


def load_vga_image(vga_path: str, palette: list[tuple[int, int, int]]) -> Image.Image | None:
    """Backward-compatible wrapper: returns only the image."""
    vf = load_vga_file(vga_path, palette)
    return vf.image if vf is not None else None

_RLE_OFFSET = 127
_RLE_SENTINEL = _RLE_OFFSET + 1
_RLE_MAX_COUNT = 127

class VgaEncodeError(Exception):
    pass

def _rle_encode_indices(indices: list[int]) -> bytearray:
    if not indices:
        raise VgaEncodeError("No pixels to save.")

    out = bytearray()
    n = len(indices)
    i = 0

    while i < n:
        run_value = indices[i]
        run_length = 1

        while (
            i + run_length < n
            and indices[i + run_length] == run_value
            and run_length < _RLE_MAX_COUNT
        ):
            run_length += 1

        if run_length >= 2:
            out.append(run_length + _RLE_OFFSET)
            out.append(run_value)
            i += run_length
            continue

        start = i
        i += 1

        while i < n and (i - start) < _RLE_MAX_COUNT:
            if i + 1 < n and indices[i] == indices[i + 1]:
                break
            i += 1

        count = i - start
        out.append(count - 1)
        out.extend(indices[start:i])

    out.append(_RLE_SENTINEL)
    return out

def save_vga_image(img: Image.Image, dest_path: str,
                   fmt: str = FMT_BMP, trailer: bytes = b"") -> None:
    if img is None:
        raise VgaEncodeError("No image to save.")

    if fmt not in _VGA_FORMATS:
        raise VgaEncodeError(f"Unknown file format: {fmt}")

    if img.mode != "P":
        raise VgaEncodeError("Internal image is not in indexed format.")

    w, h = img.size
    if w <= 0 or h <= 0:
        raise VgaEncodeError(f"Invalid image dimensions: {w}x{h}")
    if w > 0xFFFF or h > 0xFFFF:
        raise VgaEncodeError(f"Image dimensions too large: {w}x{h}")

    spec = _VGA_FORMATS[fmt]
    len_bytes = spec["len_bytes"]
    max_payload = (1 << (8 * len_bytes)) - 1

    indices = list(img.tobytes())
    payload = _rle_encode_indices(indices)

    if len(payload) > max_payload:
        raise VgaEncodeError(
            f"Payload too large ({len(payload)} bytes > {max_payload}). "
            "Reduce image dimensions or complexity."
        )

    header = bytearray()
    header += w.to_bytes(2, "little")
    header += h.to_bytes(2, "little")
    header += len(payload).to_bytes(len_bytes, "little")

    tmp_path = dest_path + ".tmp"

    try:
        with open(tmp_path, "wb") as f:
            f.write(header)
            f.write(payload)
            if trailer:
                f.write(trailer)   # keep an embedded palette, if the file had one

        os.replace(tmp_path, dest_path)

    except OSError as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        raise VgaEncodeError(f"File write error: {exc}") from exc

BG        = "#F4F6F9"
FG        = "#2C3E50"
ACCENT    = "#3498DB"
MUTED     = "#7F8C8D"
RED       = "#C0392B"
SEL_COLOR = "#00BFFF"
ALPHA_DISPLAY_COLOR = "#FF00FF"  # classic editor magenta for transparency
ALPHA_INDEX = 0

TOOL_DRAW       = "draw"
TOOL_SELECT     = "select"
TOOL_PICK       = "pick"
TOOL_FILL       = "fill"
TOOL_MOVE_PASTE = "move_paste"
TOOL_HAND       = "hand"
TOOL_SOFTEN     = "soften"
TOOL_TEXT       = "text"
TOOL_SHAPE      = "shape"

_TEXT_FONTS = ("MICRO4.FON", "FLOW.FON", "NORMAL.FON")   # original game fonts, loaded through fonts.py
_NONZERO_TABLE = bytes([0]) + bytes([255]) * 255


def _nonzero_mask(img: Image.Image) -> Image.Image:
    """'L' mask that is 255 wherever the indexed image is not the alpha index 0."""
    return Image.frombytes("L", img.size, img.tobytes().translate(_NONZERO_TABLE))

ZOOM_LEVELS = [1, 2, 4, 8, 16]

def _natural_key(s: str):
    return [int(c) if c.isdigit() else c.lower()
            for c in re.split(r"(\d+)", s)]

def _rgb_to_palette_index(
    r: int, g: int, b: int, palette: list[tuple[int, int, int]],
    start_index: int = 0,
) -> int:
    if not palette:
        return 0
    start_index = max(0, min(start_index, len(palette) - 1))
    best_idx = start_index
    best_dist = float("inf")
    for i in range(start_index, len(palette)):
        pr, pg, pb = palette[i]
        if (pr, pg, pb) == (r, g, b):
            return i
        dist = (pr - r) ** 2 + (pg - g) ** 2 + (pb - b) ** 2
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def _quantize_rgba_to_palette(
    src: Image.Image, palette: list[tuple[int, int, int]]
) -> Image.Image:
    """Quantize RGB data to the VGA palette while reserving index 0 for alpha.

    Palette index 0 is the only transparent color. All other palette entries,
    even when their RGB value is black or contains zero bytes, remain opaque.
    """
    if src is None:
        raise ValueError("No source image.")
    if len(palette) < 2:
        raise ValueError("The palette must contain at least one opaque color.")

    rgba = src.convert("RGBA")
    flat = _palette_to_flat_rgb(palette[1:])
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(flat)

    # Quantize only against palette entries 1..255. This prevents an opaque
    # black pixel from ever being mistaken for the alpha entry at index 0.
    q = rgba.convert("RGB").quantize(palette=pal_img, dither=0)
    indices = bytearray(q.tobytes())

    alpha = rgba.getchannel("A")
    alpha_bytes = alpha.tobytes()
    for i, a in enumerate(alpha_bytes):
        if a == 0:
            indices[i] = ALPHA_INDEX
        else:
            indices[i] += 1

    result = Image.frombytes("P", rgba.size, bytes(indices))
    result.putpalette(_palette_to_flat_rgb(palette))
    return result


#  Bitmap fonts (.FON) — pure PIL/tkinter port of the game's font loader.
#  Fonts are looked up in the ".\\data" folder (next to the editor, then the working dir).
FONT_ROWS = {"MICRO4.FON": 6, "FLOW.FON": 8, "NORMAL.FON": 16}   # glyph row counts of the bitmap fonts
FONT_CODES = {   # character codes stored in each font, in file order
    "MICRO4.FON": list(range(0x20, 0x60)) + list(range(0x61, 0x7F)),
    "FLOW.FON": [0x20, 0x21, 0x22, 0x24, 0x25, 0x27, 0x28, 0x29] + list(range(0x2A, 0x40)) + list(range(0x41, 0x5F)) + list(range(0x61, 0x7F)),
    # NORMAL.FON: 44 glyphs, 16 rows, uppercase only: space, '-', '.', 0-9, ':', A-Z, then I-grave, A-grave, O-grave, degree.
    "NORMAL.FON": [0x20, 0x2D, 0x2E] + list(range(0x30, 0x3B)) + list(range(0x41, 0x5B)) + [0x5B, 0x2A, 0x7D, 0x7E],
}
UPPERCASE_ONLY = {"NORMAL.FON"}   # fonts without lowercase glyphs: text is upper-cased before lookup
_ACC = {"7e": "\u00b0", "24": "\u20ac", "5b": "\u00ec", "5d": "\u00e9", "7b": "\u00e8", "7c": "\u00f9", "7d": "\u00f2", "2a": "\u00e0"}
DEFAULT_CHARMAPS = {"MICRO4.FON": dict(_ACC), "FLOW.FON": dict(_ACC), "NORMAL.FON": dict(_ACC)}
CHARMAP_GAME = "BUNDESLIGA MANAGER PROFESSIONAL"   # game edition whose character map is used
CHAR_FALLBACK = {"|": "/", "{": "(", "}": ")", "~": "-", "[": "(", "]": ")", "*": "+", "$": "S", "#": "+", "&": "+", "@": "a",
                 "_": "-", "`": "'", "\\": "/", "^": "'", "\u00df": "s", "\u00e6": "a", "\u00f8": "o", "\u0153": "o",
                 "\u2019": "'", "\u2018": "'", "\u201c": "\"", "\u201d": "\"", "\u2013": "-", "\u2014": "-", "\u2026": ".",
                 "\u00a0": " ", "\t": " "}


def _font_data_dirs() -> list[str]:
    """Folders searched for .FON / char-mapping.json: <editor folder>\\data, then <working dir>\\data."""
    out: list[str] = []
    for base in (os.path.dirname(os.path.abspath(__file__)), os.getcwd()):
        d = os.path.join(base, "data")
        if d not in out:
            out.append(d)
    return out


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
    """Parse a .FON file into {code: (width, [row bits], bytes_per_row)}."""
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
    """Legacy bitmap font: glyphs are PIL 'L' masks (255 = lit pixel)."""

    def __init__(self, path, name, charmap):
        self.name, self.rows = name, FONT_ROWS[name]
        raw = parse_fon(path, self.rows, FONT_CODES[name])
        self.rev = {ch: int(b, 16) for b, ch in charmap.items()}
        self.remap = {int(b, 16) for b in charmap}
        self.upper_only = name in UPPERCASE_ONLY
        if self.upper_only:   # accented lowercase mappings also serve their uppercase form
            for ch, c in list(self.rev.items()):
                u = ch.upper()
                if len(u) == 1:
                    self.rev.setdefault(u, c)
        self.glyphs: dict[int, Image.Image] = {}
        for code, (w, bits, bpr) in raw.items():
            g = Image.new("L", (max(1, w), self.rows), 0)
            px = g.load()
            for y, v in enumerate(bits):
                for x in range(w):
                    if (v >> (bpr * 8 - 1 - x)) & 1:
                        px[x, y] = 255
            self.glyphs[code] = g
        slash, backslash = self.glyphs.get(0x2F), self.glyphs.get(0x5C)
        if slash is not None and backslash is not None and backslash.getbbox() is None:   # empty backslash slot
            self.glyphs[0x5C] = slash.transpose(Image.FLIP_LEFT_RIGHT)
        self.width = {c: g.width for c, g in self.glyphs.items()}
        self._lut: dict[str, int] = {}
        self._text: dict[tuple, Image.Image] = {}

    def code(self, ch):
        """Resolve a character to the glyph code supported by this font."""
        c = self._lut.get(ch)
        if c is not None:
            return c
        orig = ch
        if self.upper_only and len(ch.upper()) == 1:
            ch = ch.upper()
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
                if alt is not None and self.upper_only and len(alt.upper()) == 1:
                    alt = alt.upper()
                c = None
                if alt is not None:
                    ao = ord(alt)
                    c = ao if (ao in self.glyphs and ao not in self.remap) else self.rev.get(alt)
                if c is None or c not in self.glyphs:
                    c = 0x3F if 0x3F in self.glyphs else 0x20
        self._lut[orig] = c
        return c

    def text_width(self, text, scale=1):
        return sum(self.width[self.code(ch)] for ch in text) * scale

    def render_mask(self, text, scale=1) -> Image.Image:
        """Render a string as an 'L' mask (255 = lit pixel)."""
        key = (text, scale)
        im = self._text.get(key)
        if im is None:
            if len(self._text) > 4000:
                self._text.clear()
            im = Image.new("L", (max(1, self.text_width(text, 1)), self.rows), 0)
            x = 0
            for ch in text:
                c = self.code(ch)
                im.paste(self.glyphs[c], (x, 0))
                x += self.width[c]
            if scale != 1:
                im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
            self._text[key] = im
        return im

    def render(self, text, color, scale=1) -> Image.Image:
        """Render a string as an RGBA image in `color`."""
        mask = self.render_mask(text, scale)
        im = Image.new("RGBA", mask.size, tuple(color[:3]) + (255,))
        im.putalpha(mask)
        return im


class ScaledFont:
    """Scaled wrapper around a bitmap font."""

    def __init__(self, font, scale):
        self.font, self.scale = font, scale

    def render(self, text, antialias=True, color=(255, 255, 255)):
        return self.font.render(text, color, self.scale)

    def size(self, text):
        return self.font.text_width(text, self.scale), self.font.rows * self.scale

    def get_height(self):
        return self.font.rows * self.scale


class FontBank:
    """Loading and caching of the bitmap fonts (plus an optional tkinter 'modern' font)."""
    SMALL_MAX_PX = 23

    def __init__(self):
        self.micro = self.flow = self.normal = None
        self.modern = False
        self._px: dict = {}

    def load(self, dirs):
        maps = _read_charmaps(dirs)
        for attr, name in (("micro", "MICRO4.FON"), ("flow", "FLOW.FON"), ("normal", "NORMAL.FON")):
            for d in dirs:
                p = os.path.join(d, name) if d else None
                if p and os.path.isfile(p):
                    try:
                        setattr(self, attr, BitmapFont(p, name, maps.get(name, DEFAULT_CHARMAPS[name])))
                        break
                    except (OSError, ValueError):
                        continue
        self._px.clear()
        return self.micro is not None and self.flow is not None

    def bitmap(self, name):
        return {"MICRO4.FON": self.micro, "FLOW.FON": self.flow, "NORMAL.FON": self.normal}.get(name)

    def small(self, scale=1):
        key = ("m", scale)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = ScaledFont(self.micro, scale)
        return f

    def normal_font(self, scale=1):
        key = ("n", scale)
        f = self._px.get(key)
        if f is None:
            f = self._px[key] = ScaledFont(self.normal, scale)
        return f

    def modern_font(self, px):
        key = ("mod", px)
        f = self._px.get(key)
        if f is None:
            fams = {n.lower(): n for n in tkfont.families()}
            fam = next((fams[n] for n in ("dejavu sans", "segoe ui", "arial", "helvetica", "liberation sans") if n in fams), "TkDefaultFont")
            f = self._px[key] = tkfont.Font(family=fam, size=-int(px))
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


FONTS = FontBank()   # shared font bank used by the TEXT tool


class _ImageCanvas(tk.Frame):

    def __init__(self, parent, on_modified=None, on_color_picked=None, on_text_request=None, **kw):
        super().__init__(parent, bg="#1a1a2e", **kw)
        self._on_text_request = on_text_request
        self._paste_transparent: bool = False   # True for TEXT pastes: index 0 is see-through
        self._shape_mode: str = "line"          # "line" | "rect" | "rect_fill"
        self._shape_start: tuple[int, int] | None = None
        self._shape_end: tuple[int, int] | None = None
        self._on_modified = on_modified
        self._on_color_picked = on_color_picked
        self._img: Image.Image | None = None
        self._palette: list[tuple[int, int, int]] = list(_PAL_NORMAL20)
        self._zoom = 2
        self._tool = TOOL_DRAW
        self._draw_color = (255, 255, 255, 255)
        self._draw_index: int | None = None
        self._show_alpha = True
        self._show_grid = True
        self._clipboard: Image.Image | None = None
        self._sel: tuple[int, int, int, int] | None = None
        self._sel_start: tuple[int, int] | None = None
        self._dragging = False
        self._paste_buf: Image.Image | None = None
        self._paste_pos: tuple[int, int] = (0, 0)
        self._paste_drag_start: tuple[int, int] | None = None
        self._paste_drag_origin: tuple[int, int] = (0, 0)
        self._paste_src: Image.Image | None = None
        self._paste_resize_corner: str | None = None
        self._paste_resize_anchor: tuple[int, int] = (0, 0)
        self._paste_resize_filter: int = Image.NEAREST
        self._paste_aspect_lock: bool = False
        self._pan_start: tuple[int, int] | None = None
        self._drawing_stroke: bool = False
        self._last_draw_pt: tuple[int, int] | None = None

        view = tk.Frame(self, bg="#1a1a2e")
        view.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(view, bg="#1a1a2e", cursor="crosshair", highlightthickness=0, xscrollincrement=1, yscrollincrement=1)
        self._vbar = ttk.Scrollbar(view, orient=tk.VERTICAL, command=self._yview_and_redraw)
        self._hbar = ttk.Scrollbar(view, orient=tk.HORIZONTAL, command=self._xview_and_redraw)
        self._canvas.configure(xscrollcommand=self._hbar.set, yscrollcommand=self._vbar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._vbar.grid(row=0, column=1, sticky="ns")
        self._hbar.grid(row=1, column=0, sticky="ew")
        self._corner = tk.Frame(view, bg="#1a1a2e", width=0, height=0)
        self._corner.grid(row=1, column=1, sticky="nsew")
        self._vbar.grid_remove()
        self._hbar.grid_remove()
        self._corner.grid_remove()
        view.grid_rowconfigure(0, weight=1)
        view.grid_columnconfigure(0, weight=1)
        self._view = view
        self._tk_img = None
        self._canvas.bind("<Button-1>", self._on_b1_press)
        self._canvas.bind("<B1-Motion>", self._on_b1_motion)
        self._canvas.bind("<ButtonRelease-1>", self._on_b1_release)
        self._canvas.bind("<Button-2>", self._on_b2_press)
        self._canvas.bind("<B2-Motion>", self._on_b2_motion)
        self._canvas.bind("<ButtonRelease-2>", self._on_b2_release)
        self._canvas.bind("<Button-3>", self._on_b3_press)
        self._canvas.bind("<B3-Motion>", self._on_b3_motion)
        self._canvas.bind("<ButtonRelease-3>", self._on_b3_release)
        self._canvas.bind("<Motion>", self._on_motion)
        self._canvas.bind("<Configure>", lambda _e: self._redraw())
        self._canvas.bind("<Escape>", self.deselect)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel_zoom)
        self._canvas.bind("<Button-4>", self._on_mousewheel_zoom)
        self._canvas.bind("<Button-5>", self._on_mousewheel_zoom)
        self._zoom_changed_callback = None

    def _yview_and_redraw(self, *args):
        self._canvas.yview(*args)
        self._redraw()

    def _xview_and_redraw(self, *args):
        self._canvas.xview(*args)
        self._redraw()

    def _rescroll_for_zoom(self, anchor_ix: float, anchor_iy: float,screen_x: float, screen_y: float, new_zoom: int):
        if self._img is None:
            return
        iw, ih = self._img.size
        new_dw, new_dh = iw * new_zoom, ih * new_zoom
        self._canvas.configure(scrollregion=(0, 0, new_dw + 2, new_dh + 2))
        left = anchor_ix * new_zoom - screen_x
        top = anchor_iy * new_zoom - screen_y
        if new_dw > 0:
            self._canvas.xview_moveto(max(0.0, left) / (new_dw + 2))
        if new_dh > 0:
            self._canvas.yview_moveto(max(0.0, top) / (new_dh + 2))

    def _on_mousewheel_zoom(self, event):
        old_zoom = self._zoom
        if getattr(event, 'num', None) == 4 or (hasattr(event, 'delta') and event.delta > 0):
            new_zoom = min(16, old_zoom + 1)
        elif getattr(event, 'num', None) == 5 or (hasattr(event, 'delta') and event.delta < 0):
            new_zoom = max(1, old_zoom - 1)
        else:
            return "break"

        if new_zoom == old_zoom:
            return "break"

        img_x = self._canvas.canvasx(event.x) / old_zoom
        img_y = self._canvas.canvasy(event.y) / old_zoom
        self._zoom = new_zoom
        self._rescroll_for_zoom(img_x, img_y, event.x, event.y, new_zoom)
        self._redraw()
        if self._zoom_changed_callback:
            self._zoom_changed_callback(new_zoom)
        return "break"

    def set_palette(self, palette: list[tuple[int, int, int]]):
        self._palette = list(palette)
        if self._draw_index is not None:
            if not (0 <= self._draw_index < len(self._palette)):
                self._draw_index = None
            elif self._draw_index != ALPHA_INDEX:
                r, g, b, a = self._draw_color
                if a == 0 or self._palette[self._draw_index] != (r, g, b):
                    self._draw_index = None
        self._flat_palette_cache = None
        self._redraw()

    def _flat_palette(self) -> list[int]:
        cache = getattr(self, "_flat_palette_cache", None)
        if cache is None:
            cache = _palette_to_flat_rgb(self._palette)
            self._flat_palette_cache = cache
        return cache

    def set_image(self, img: Image.Image):
        self._commit_paste()
        if img.mode != "P":
            raise ValueError("The editor requires indexed images.")
        self._img = img.copy()
        self._sel = None
        self._paste_buf = None
        self._paste_drag_start = None
        self._canvas.xview_moveto(0)
        self._canvas.yview_moveto(0)
        self._redraw()

    def set_image_preserve_view(self, img: Image.Image):
        if img.mode != "P":
            raise ValueError("The editor requires indexed images.")
        xpos = self._canvas.xview()[0]
        ypos = self._canvas.yview()[0]
        self._img = img.copy()
        self._sel = None
        self._paste_buf = None
        self._paste_drag_start = None
        self._redraw()
        self._canvas.xview_moveto(xpos)
        self._canvas.yview_moveto(ypos)

    def get_image(self) -> Image.Image | None:
        self._commit_paste()
        return self._img

    def set_tool(self, tool: str):
        if tool != TOOL_MOVE_PASTE and self._tool == TOOL_MOVE_PASTE:
            self._commit_paste()
        self._tool = tool
        self._shape_start = self._shape_end = None
        self._update_cursor()

    def _update_cursor(self, event=None):
        if self._tool == TOOL_HAND:
            cursor = "hand2"
        elif self._tool == TOOL_SOFTEN:
            cursor = "circle"
        elif self._tool == TOOL_DRAW:
            cursor = "pencil"
        elif self._tool == TOOL_PICK:
            cursor = "target"
        elif self._tool == TOOL_FILL:
            cursor = "spraycan"
        elif self._tool == TOOL_TEXT:
            cursor = "xterm"
        elif self._tool == TOOL_MOVE_PASTE:
            if event is not None:
                corner = self._paste_corner_at(event.x, event.y)
                if corner in ("nw", "se"):
                    self._canvas.config(cursor="size_nw_se")
                    return
                if corner in ("ne", "sw"):
                    self._canvas.config(cursor="size_ne_sw")
                    return
            cursor = "fleur" if (event is not None and self._paste_hit(event.x, event.y)) else "crosshair"
        else:
            cursor = "crosshair"
        self._canvas.config(cursor=cursor)

    def set_draw_color(self, rgba: tuple, pal_idx: int | None = None):
        self._draw_color = rgba
        if pal_idx is not None and 0 <= pal_idx < len(self._palette):
            self._draw_index = pal_idx
        elif len(rgba) >= 4 and rgba[3] == 0:
            self._draw_index = ALPHA_INDEX
        else:
            self._draw_index = None

    def set_zoom(self, z: int):
        old_zoom = self._zoom
        if z == old_zoom:
            return
        anchor_ix, anchor_iy = 0, 0
        if self._img is not None and old_zoom > 0:
            anchor_ix = max(0, int(self._canvas.canvasx(0))) / old_zoom
            anchor_iy = max(0, int(self._canvas.canvasy(0))) / old_zoom
        self._zoom = z
        self._rescroll_for_zoom(anchor_ix, anchor_iy, 0, 0, z)
        self._redraw()

    def set_show_alpha(self, v: bool):
        self._show_alpha = bool(v)
        self._redraw()

    def set_show_grid(self, v: bool):
        self._show_grid = v
        self._redraw()

    def copy_selection(self):
        if self._img is None or self._sel is None or self._paste_buf is not None:
            return
        x0, y0, x1, y1 = self._normalised_sel()
        self._clipboard = self._img.crop((x0, y0, x1, y1))

    def paste_selection(self):
        if self._img is None or self._clipboard is None:
            return False
        self._commit_paste()
        self._paste_buf = self._clipboard.copy()
        self._paste_transparent = False
        self._paste_src = self._paste_buf.copy()
        self._paste_resize_corner = None
        pw, ph = self._paste_buf.size
        if self._sel is not None:
            x0, y0, _, _ = self._normalised_sel()
        else:
            x0, y0 = 0, 0
        self._paste_pos = (x0, y0)
        self._sel = (
            self._paste_pos[0], self._paste_pos[1],
            self._paste_pos[0] + pw - 1, self._paste_pos[1] + ph - 1,
        )
        self._tool = TOOL_MOVE_PASTE
        self._update_cursor()
        self._redraw()
        return True

    def commit_paste_now(self):
        if self._paste_buf is None:
            return
        back = TOOL_TEXT if self._paste_transparent else TOOL_SELECT
        self._commit_paste()
        self._tool = back
        self._update_cursor()
        self._redraw()

    def delete_selection(self):
        if self._paste_buf is not None:
            back = TOOL_TEXT if self._paste_transparent else TOOL_SELECT
            self._paste_buf = None
            self._paste_src = None
            self._paste_transparent = False
            self._paste_resize_corner = None
            self._sel = None
            self._paste_drag_start = None
            self._tool = back
            self._update_cursor()
            self._redraw()
        elif self._sel is not None and self._img is not None:
            self._notify_stroke_start()
            x0, y0, x1, y1 = self._normalised_sel()
            blank = Image.new("P", (x1 - x0, y1 - y0), 0)
            self._img.paste(blank, (x0, y0))
            self._sel = None
            self._notify_modified()
            self._redraw()

    def rotate_selection(self):
        if self._paste_buf is None:
            return
        self._paste_buf = self._paste_buf.transpose(Image.ROTATE_270)
        pw, ph = self._paste_buf.size
        px, py = self._paste_pos
        self._sel = (px, py, px + pw - 1, py + ph - 1)
        self._tool = TOOL_MOVE_PASTE
        self._paste_drag_start = None
        self._update_cursor()
        self._redraw()

    def mirror_selection(self):
        if self._paste_buf is None:
            return
        self._paste_buf = self._paste_buf.transpose(Image.FLIP_LEFT_RIGHT)
        self._tool = TOOL_MOVE_PASTE
        self._paste_drag_start = None
        self._update_cursor()
        self._redraw()

    def deselect(self, _event=None):
        back = TOOL_TEXT if self._paste_transparent else TOOL_SELECT
        self._shape_start = self._shape_end = None
        self._commit_paste()
        self._sel = None
        self._sel_start = None
        self._dragging = False
        self._paste_drag_start = None
        if self._tool == TOOL_MOVE_PASTE:
            self._tool = back
            self._update_cursor()
        self._redraw()
        parent = self.master
        if hasattr(parent, "_update_selection_buttons"):
            parent._update_selection_buttons(False)
        return "break"

    def _commit_paste(self):
        if self._paste_buf is None or self._img is None:
            return
        self._notify_stroke_start()
        iw, ih = self._img.size
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        src_x0 = max(0, -px)
        src_y0 = max(0, -py)
        src_x1 = min(pw, iw - px)
        src_y1 = min(ph, ih - py)
        dst_x = max(0, px)
        dst_y = max(0, py)
        if src_x1 > src_x0 and src_y1 > src_y0:
            region = self._paste_buf.crop((src_x0, src_y0, src_x1, src_y1))
            if self._paste_transparent:
                self._img.paste(region, (dst_x, dst_y), _nonzero_mask(region))
            else:
                self._img.paste(region, (dst_x, dst_y))
        self._paste_buf = None
        self._paste_src = None
        self._paste_transparent = False
        self._paste_resize_corner = None
        self._notify_modified()

    def _display_image(self) -> Image.Image:
        flat_pal = self._flat_palette()
        img = self._img.copy()
        # Index 0 is display-only: optionally show it as editor magenta.
        # The indexed image and the original palette remain unchanged.
        if len(flat_pal) >= 3:
            flat_pal[0:3] = (255, 0, 255) if self._show_alpha else (0, 0, 0)
        img.putpalette(flat_pal)
        layer = self._shape_layer()
        if layer is not None:
            smask, (sx, sy) = layer
            img.paste(self._current_draw_index(), (sx, sy, sx + smask.width, sy + smask.height), smask)
        if self._paste_buf is not None:
            iw, ih = img.size
            px, py = self._paste_pos
            pw, ph = self._paste_buf.size
            src_x0 = max(0, -px)
            src_y0 = max(0, -py)
            src_x1 = min(pw, iw - px)
            src_y1 = min(ph, ih - py)
            dst_x = max(0, px)
            dst_y = max(0, py)
            if src_x1 > src_x0 and src_y1 > src_y0:
                paste = self._paste_buf.crop((src_x0, src_y0, src_x1, src_y1))
                tmask = _nonzero_mask(paste) if self._paste_transparent else None
                paste.putpalette(flat_pal)
                img.paste(paste, (dst_x, dst_y), tmask)
        return img

    def _with_grid_overlay(self, scaled: Image.Image, iw: int, ih: int, z: int,offset: tuple[int, int] = (0, 0)) -> Image.Image:
        dw, dh = iw * z, ih * z
        ox, oy = offset
        grid_rgb = (51, 51, 51)
        x_start = (-ox) % z
        y_start = (-oy) % z
        scaled = scaled.convert("RGB")
        draw = ImageDraw.Draw(scaled)
        for x in range(x_start, dw, z):
            draw.line((x, 0, x, dh - 1), fill=grid_rgb, width=1)
        for y in range(y_start, dh, z):
            draw.line((0, y, dw - 1, y), fill=grid_rgb, width=1)
        return scaled

    def _redraw(self):
        c = self._canvas
        if self._img is None:
            c.delete("all")
            self._tk_img = None
            c.configure(scrollregion=(0, 0, c.winfo_width(), c.winfo_height()))
            c.create_text(
                c.winfo_width() // 2 or 200,
                c.winfo_height() // 2 or 150,
                text="No image loaded",
                fill="#555",
                font=("Segoe UI", 12, "italic"),
                tags="placeholder",
            )
            return
        c.delete("selection", "paste")
        if c.find_withtag("placeholder"):
            c.delete("placeholder")
        iw, ih = self._img.size
        z = self._zoom
        dw, dh = iw * z, ih * z
        c.configure(scrollregion=(0, 0, dw + 2, dh + 2))
        avail_w, avail_h = self._update_scrollbars(dw, dh)
        vx0 = max(0, int(c.canvasx(0)))
        vy0 = max(0, int(c.canvasy(0)))
        view_w = max(1, avail_w)
        view_h = max(1, avail_h)
        vx1 = min(dw, vx0 + view_w)
        vy1 = min(dh, vy0 + view_h)
        margin = z * 2
        vx0 = max(0, vx0 - margin)
        vy0 = max(0, vy0 - margin)
        vx1 = min(dw, vx1 + margin)
        vy1 = min(dh, vy1 + margin)

        if vx1 <= vx0 or vy1 <= vy0:
            c.delete("image")
            self._tk_img = None
        else:
            ix0, iy0 = vx0 // z, vy0 // z
            ix1 = min(iw, -(-vx1 // z))
            iy1 = min(ih, -(-vy1 // z))
            src = self._display_image().crop((ix0, iy0, ix1, iy1))
            crop_dw = (ix1 - ix0) * z
            crop_dh = (iy1 - iy0) * z
            scaled = src.resize((crop_dw, crop_dh), Image.NEAREST)
            if self._show_grid and z >= 4:
                scaled = self._with_grid_overlay(scaled, ix1 - ix0, iy1 - iy0, z, offset=(ix0 * z, iy0 * z))
            self._tk_img = ImageTk.PhotoImage(scaled)
            existing = c.find_withtag("image")
            if existing:
                c.itemconfigure(existing[0], image=self._tk_img)
                c.coords(existing[0], ix0 * z, iy0 * z)
            else:
                c.create_image(ix0 * z, iy0 * z, anchor="nw", image=self._tk_img, tags="image")
            c.tag_lower("image")

        if self._sel is not None:
            x0, y0, x1, y1 = self._normalised_sel()
            c.create_rectangle(x0 * z, y0 * z, x1 * z, y1 * z,outline=SEL_COLOR, width=2, dash=(4, 2), tags="selection")

        if self._paste_buf is not None:
            px0, py0 = self._paste_pos
            pw, ph = self._paste_buf.size
            c.create_rectangle(px0 * z, py0 * z, (px0 + pw) * z, (py0 + ph) * z,outline="#FFD700", width=2, dash=(4, 2), tags="paste")
            r = self._HANDLE_R
            for hx, hy in (() if self._paste_src is None else (
                (px0 * z,        py0 * z),
                ((px0 + pw) * z, py0 * z),
                (px0 * z,        (py0 + ph) * z),
                ((px0 + pw) * z, (py0 + ph) * z),
            )):
                c.create_rectangle(hx - r, hy - r, hx + r, hy + r,fill="#FFD700", outline="#000", width=1, tags="paste")
        c.configure(scrollregion=(0, 0, dw + 2, dh + 2))

    def _update_scrollbars(self, dw: int, dh: int) -> tuple[int, int]:
        base_w = max(1, self._view.winfo_width())
        base_h = max(1, self._view.winfo_height())
        v_w = max(1, self._vbar.winfo_reqwidth())
        h_h = max(1, self._hbar.winfo_reqheight())
        show_h = False
        show_v = False
        for _ in range(4):
            avail_w = base_w - (v_w if show_v else 0)
            avail_h = base_h - (h_h if show_h else 0)
            new_h = dw > max(1, avail_w)
            new_v = dh > max(1, avail_h)
            if (new_h, new_v) == (show_h, show_v):
                break
            show_h, show_v = new_h, new_v
        if show_v:
            self._vbar.grid(row=0, column=1, sticky="ns")
        else:
            self._vbar.grid_remove()
        if show_h:
            self._hbar.grid(row=1, column=0, sticky="ew")
        else:
            self._hbar.grid_remove()
        if show_h and show_v:
            self._corner.grid(row=1, column=1, sticky="nsew")
        else:
            self._corner.grid_remove()
        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._canvas.configure(
            xscrollcommand=self._hbar.set if show_h else lambda *args: None,
            yscrollcommand=self._vbar.set if show_v else lambda *args: None,
        )
        final_avail_w = base_w - (v_w if show_v else 0)
        final_avail_h = base_h - (h_h if show_h else 0)
        return max(1, final_avail_w), max(1, final_avail_h)

    _HANDLE_R = 5

    def _paste_corner_at(self, cx: int, cy: int) -> "str | None":
        if self._paste_buf is None or self._paste_src is None:
            return None   # text pastes cannot be resized (they have no source image)
        z = self._zoom
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        r = self._HANDLE_R
        sx = self._canvas.canvasx(cx)
        sy = self._canvas.canvasy(cy)
        corners = {
            "nw": (px * z,        py * z),
            "ne": ((px + pw) * z, py * z),
            "sw": (px * z,        (py + ph) * z),
            "se": ((px + pw) * z, (py + ph) * z),
        }
        for name, (hx, hy) in corners.items():
            if abs(sx - hx) <= r and abs(sy - hy) <= r:
                return name
        return None

    def _paste_hit(self, cx: int, cy: int) -> bool:
        if self._paste_buf is None:
            return False
        x = self._canvas.canvasx(cx)
        y = self._canvas.canvasy(cy)
        px, py = self._paste_pos
        pw, ph = self._paste_buf.size
        z = self._zoom
        return px * z <= x < (px + pw) * z and py * z <= y < (py + ph) * z

    def _canvas_to_pixel(self, cx: int, cy: int) -> tuple[int, int] | None:
        if self._img is None:
            return None
        z = self._zoom
        x = int(self._canvas.canvasx(cx))
        y = int(self._canvas.canvasy(cy))
        px = x // z
        py = y // z
        iw, ih = self._img.size
        if 0 <= px < iw and 0 <= py < ih:
            return px, py
        return None

    def _normalised_sel(self) -> tuple[int, int, int, int]:
        x0, y0, x1, y1 = self._sel
        return min(x0, x1), min(y0, y1), max(x0, x1) + 1, max(y0, y1) + 1

    def _point_in_selection(self, pt: tuple[int, int]) -> bool:
        if self._sel is None:
            return False
        x0, y0, x1, y1 = self._normalised_sel()
        return x0 <= pt[0] < x1 and y0 <= pt[1] < y1

    def _on_motion(self, event):
        self._update_cursor(event)

    def _on_b1_press(self, event):
        if self._tool == TOOL_HAND:
            iw = ih = 0
            if self._img is not None:
                iw, ih = self._img.size
            dw, dh = iw * self._zoom, ih * self._zoom
            can_pan = (dw > self._canvas.winfo_width() or dh > self._canvas.winfo_height())
            if can_pan:
                self._pan_start = (event.x, event.y)
                self._canvas.scan_mark(event.x, event.y)
            return

        if self._tool == TOOL_MOVE_PASTE and self._paste_buf is not None:
            corner = self._paste_corner_at(event.x, event.y)
            if corner is not None and self._paste_src is not None:
                self._paste_resize_corner = corner
                px, py = self._paste_pos
                pw, ph = self._paste_buf.size
                if corner == "nw":
                    self._paste_resize_anchor = (px + pw, py + ph)
                elif corner == "ne":
                    self._paste_resize_anchor = (px, py + ph)
                elif corner == "sw":
                    self._paste_resize_anchor = (px + pw, py)
                else:
                    self._paste_resize_anchor = (px, py)
                self._paste_drag_start = None 
                return
            if self._paste_hit(event.x, event.y):
                pt = self._canvas_to_pixel(event.x, event.y)
                if pt is not None:
                    self._paste_resize_corner = None
                    self._paste_drag_start = pt
                    self._paste_drag_origin = self._paste_pos
            return

        pt = self._canvas_to_pixel(event.x, event.y)
        if pt is None:
            if self._tool == TOOL_SELECT and self._sel is not None:
                self.deselect()
            return

        if self._tool == TOOL_SELECT:
            if self._sel is not None and not self._point_in_selection(pt):
                self._sel = None
            self._sel_start = pt
            self._sel = (pt[0], pt[1], pt[0], pt[1])
            self._dragging = True

        elif self._tool == TOOL_DRAW:
            self._last_draw_pt = pt
            self._paint_pixel(*pt)

        elif self._tool == TOOL_SOFTEN:
            self._notify_stroke_start()
            self._apply_soften_sharpen(pt, sharpen=False)

        elif self._tool == TOOL_PICK:
            index = self._pixel_index(pt)
            rgba = self._pixel_color(pt)
            self._draw_color = rgba
            self._draw_index = index
            if self._on_color_picked:
                self._on_color_picked(*rgba, index)

        elif self._tool == TOOL_FILL:
            self._flood_fill(*pt)

        elif self._tool == TOOL_TEXT:
            if self._on_text_request:
                self._on_text_request(pt)

        elif self._tool == TOOL_SHAPE:
            self._shape_start = self._shape_end = pt
            self._redraw()

    def _on_b1_motion(self, event):
        if self._tool == TOOL_HAND:
            if self._pan_start is not None:
                self._canvas.scan_dragto(event.x, event.y, gain=1)
                self._redraw()
            return

        pt = self._canvas_to_pixel(event.x, event.y)
        if self._tool == TOOL_MOVE_PASTE:
            if self._paste_resize_corner is not None and self._paste_src is not None:
                z = self._zoom
                ax, ay = self._paste_resize_anchor
                cx_raw = int(self._canvas.canvasx(event.x))
                cy_raw = int(self._canvas.canvasy(event.y))
                drag_x = max(0, cx_raw) // z
                drag_y = max(0, cy_raw) // z
                new_x0 = min(ax, drag_x)
                new_y0 = min(ay, drag_y)
                new_x1 = max(ax, drag_x)
                new_y1 = max(ay, drag_y)
                new_w = max(1, new_x1 - new_x0)
                new_h = max(1, new_y1 - new_y0)
                if (event.state & 0x0001) or self._paste_aspect_lock:
                    src_w, src_h = self._paste_src.size
                    scale = min(new_w / src_w, new_h / src_h)
                    new_w = max(1, int(src_w * scale))
                    new_h = max(1, int(src_h * scale))
                resized = self._paste_src.convert("RGBA").resize((new_w, new_h), Image.NEAREST)
                self._paste_buf = _quantize_rgba_to_palette(resized, self._palette)
                self._paste_pos = (new_x0, new_y0)
                self._sel = (new_x0, new_y0, new_x0 + new_w - 1, new_y0 + new_h - 1)
                self._redraw()
                return
            if self._paste_drag_start is not None and self._paste_buf is not None and pt is not None:
                dx = pt[0] - self._paste_drag_start[0]
                dy = pt[1] - self._paste_drag_start[1]
                ox0, oy0 = self._paste_drag_origin
                pw, ph = self._paste_buf.size
                nx = ox0 + dx
                ny = oy0 + dy
                self._paste_pos = (nx, ny)
                self._sel = (nx, ny, nx + pw - 1, ny + ph - 1)
                self._redraw()
            self._update_cursor(event)
            return

        if self._tool == TOOL_SHAPE:
            if self._shape_start is not None and self._img is not None:
                self._shape_end = self._shape_target(event)
                self._redraw()
            return

        if pt is None:
            return

        if self._tool == TOOL_DRAW:
            if self._last_draw_pt is not None:
                self._draw_line(self._last_draw_pt, pt)
            else:
                self._paint_pixel(*pt)
            self._last_draw_pt = pt
        elif self._tool == TOOL_SOFTEN:
            self._apply_soften_sharpen(pt, sharpen=False)
        elif self._tool == TOOL_SELECT and self._dragging and self._sel_start:
            x0, y0 = self._sel_start
            self._sel = (x0, y0, pt[0], pt[1])
            self._redraw()

    def _on_b1_release(self, event):
        if self._tool == TOOL_SHAPE and self._shape_start is not None:
            if self._img is not None:
                self._shape_end = self._shape_target(event)
            self._commit_shape()
        self._dragging = False
        self._pan_start = None
        self._drawing_stroke = False
        self._last_draw_pt = None
        if self._paste_resize_corner is not None and self._paste_src is not None and self._paste_buf is not None:
            pw, ph = self._paste_buf.size
            flt = self._paste_resize_filter
            if flt != Image.NEAREST:
                resized = self._paste_src.convert("RGBA").resize((pw, ph), flt)
                self._paste_buf = _quantize_rgba_to_palette(resized, self._palette)
                self._redraw()
            self._paste_resize_corner = None
        self._paste_drag_start = None

    def _on_b2_press(self, event):
        iw = ih = 0
        if self._img is not None:
            iw, ih = self._img.size
        dw, dh = iw * self._zoom, ih * self._zoom
        can_pan = dw > self._canvas.winfo_width() or dh > self._canvas.winfo_height()
        if can_pan:
            self._pan_start = (event.x, event.y)
            self._canvas.scan_mark(event.x, event.y)
        self._canvas.config(cursor="hand2")

    def _on_b2_motion(self, event):
        if self._pan_start is not None:
            self._canvas.scan_dragto(event.x, event.y, gain=1)
            self._redraw()

    def _on_b2_release(self, event):
        self._pan_start = None
        self._update_cursor()

    def _on_b3_press(self, event):
        if self._shape_start is not None:
            self._shape_start = self._shape_end = None
            self._redraw()
            return
        pt = self._canvas_to_pixel(event.x, event.y)
        if self._sel is not None and (pt is None or not self._point_in_selection(pt)):
            self.deselect()
            return

        if self._tool == TOOL_SOFTEN:
            if pt and self._img:
                self._notify_stroke_start()
                self._apply_soften_sharpen(pt, sharpen=True)
            return

        if pt and self._img and self._tool in (TOOL_PICK, TOOL_DRAW):
            index = self._pixel_index(pt)
            rgba = self._pixel_color(pt)
            self._draw_color = rgba
            self._draw_index = index
            if self._on_color_picked:
                self._on_color_picked(*rgba, index)

    def _on_b3_motion(self, event):
        if self._tool == TOOL_SOFTEN:
            pt = self._canvas_to_pixel(event.x, event.y)
            if pt and self._img:
                self._apply_soften_sharpen(pt, sharpen=True)

    def _on_b3_release(self, event):
        pass

    def _apply_soften_sharpen(self, pt: tuple[int, int], sharpen: bool = False):
        if self._img is None:
            return
        iw, ih = self._img.size
        px, py = pt

        def get_idx(x, y):
            v = self._img.getpixel((x, y))
            return v[0] if isinstance(v, tuple) else v

        def pal_rgb(idx):
            if 0 <= idx < len(self._palette):
                return self._palette[idx]
            return (0, 0, 0)

        strength = 0.85
        changed = False
        for bx in range(px, px + 2):
            for by in range(py, py + 2):
                if not (0 <= bx < iw and 0 <= by < ih):
                    continue
                center = get_idx(bx, by)
                neighbours = []
                for dx, dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
                    nx, ny = bx + dx, by + dy
                    if 0 <= nx < iw and 0 <= ny < ih:
                        neighbours.append(get_idx(nx, ny))
                if not neighbours:
                    continue
                cr, cg, cb = pal_rgb(center)
                avg_r = sum(pal_rgb(n)[0] for n in neighbours) / len(neighbours)
                avg_g = sum(pal_rgb(n)[1] for n in neighbours) / len(neighbours)
                avg_b = sum(pal_rgb(n)[2] for n in neighbours) / len(neighbours)
                if sharpen:
                    nr = cr + strength * (cr - avg_r)
                    ng = cg + strength * (cg - avg_g)
                    nb = cb + strength * (cb - avg_b)
                else:
                    nr = cr + strength * (avg_r - cr)
                    ng = cg + strength * (avg_g - cg)
                    nb = cb + strength * (avg_b - cb)
                nr = max(0, min(255, int(nr)))
                ng = max(0, min(255, int(ng)))
                nb = max(0, min(255, int(nb)))
                new_idx = _rgb_to_palette_index(nr, ng, nb, self._palette, start_index=1)
                if new_idx != center:
                    self._img.putpixel((bx, by), new_idx)
                    changed = True

        if changed:
            self._notify_modified()
            self._redraw()

    def _pixel_index(self, pt: tuple[int, int]) -> int:
        index = self._img.getpixel(pt)
        if isinstance(index, tuple):
            index = index[0]
        return int(index)

    def _pixel_color(self, pt: tuple[int, int]) -> tuple[int, int, int, int]:
        index = self._img.getpixel(pt)
        if isinstance(index, tuple):
            index = index[0]
        if index == ALPHA_INDEX:
            return 255, 0, 255, 0
        if 0 <= index < len(self._palette):
            r, g, b = self._palette[index]
        else:
            r = g = b = 0
        return r, g, b, 255

    def _draw_line(self, pt0: tuple[int, int], pt1: tuple[int, int]):
        x0, y0 = pt0
        x1, y1 = pt1
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self._paint_pixel_raw(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

        self._notify_modified()
        self._redraw()

    def _flood_fill(self, px: int, py: int):
        if self._img is None:
            return
        iw, ih = self._img.size
        target_index = self._img.getpixel((px, py))
        if isinstance(target_index, tuple):
            target_index = target_index[0]
        r, g, b, a = self._draw_color
        if a == 0:
            fill_index = ALPHA_INDEX
        elif (
            self._draw_index is not None
            and self._draw_index != ALPHA_INDEX
            and 0 <= self._draw_index < len(self._palette)
            and self._palette[self._draw_index] == (r, g, b)
        ):
            fill_index = self._draw_index
        else:
            fill_index = _rgb_to_palette_index(r, g, b, self._palette, start_index=1)
        if fill_index == target_index:
            return
        self._notify_stroke_start()
        pixels = self._img.load()
        stack = [(px, py)]
        while stack:
            cx, cy = stack.pop()
            if not (0 <= cx < iw and 0 <= cy < ih):
                continue
            val = pixels[cx, cy]
            if isinstance(val, tuple):
                val = val[0]
            if val != target_index:
                continue
            pixels[cx, cy] = fill_index
            stack.append((cx + 1, cy))
            stack.append((cx - 1, cy))
            stack.append((cx, cy + 1))
            stack.append((cx, cy - 1))
        self._notify_modified()
        self._redraw()

    def _paint_pixel_raw(self, px: int, py: int):
        if self._img is None:
            return
        if not self._drawing_stroke:
            self._drawing_stroke = True
            self._notify_stroke_start()
        r, g, b, a = self._draw_color
        if a == 0:
            index = ALPHA_INDEX
        elif (
            self._draw_index is not None
            and self._draw_index != ALPHA_INDEX
            and 0 <= self._draw_index < len(self._palette)
            and self._palette[self._draw_index] == (r, g, b)
        ):
            index = self._draw_index
        else:
            index = _rgb_to_palette_index(r, g, b, self._palette, start_index=1)
        self._img.putpixel((px, py), index)

    def set_shape_mode(self, mode: str):
        self._shape_mode = mode
        self._shape_start = self._shape_end = None
        self._redraw()

    def _shape_target(self, event) -> tuple[int, int]:
        """Pixel under the mouse, clamped to the image; Shift snaps to 45° lines / squares."""
        iw, ih = self._img.size
        z = self._zoom
        x = min(max(int(self._canvas.canvasx(event.x)) // z, 0), iw - 1)
        y = min(max(int(self._canvas.canvasy(event.y)) // z, 0), ih - 1)
        if event.state & 0x0001 and self._shape_start is not None:
            x0, y0 = self._shape_start
            dx, dy = x - x0, y - y0
            adx, ady = abs(dx), abs(dy)
            if self._shape_mode == "line" and ady * 2 < adx:
                dy = 0
            elif self._shape_mode == "line" and adx * 2 < ady:
                dx = 0
            else:
                m = min(adx, ady)
                dx = m if dx >= 0 else -m
                dy = m if dy >= 0 else -m
            x, y = x0 + dx, y0 + dy
        return x, y

    def _shape_layer(self):
        """('L' mask, (left, top)) of the shape being dragged, or None."""
        if self._img is None or self._shape_start is None or self._shape_end is None:
            return None
        (x0, y0), (x1, y1) = self._shape_start, self._shape_end
        bx, by = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0) + 1, abs(y1 - y0) + 1
        mask = Image.new("L", (w, h), 0)
        d = ImageDraw.Draw(mask)
        if self._shape_mode == "line":
            d.line([(x0 - bx, y0 - by), (x1 - bx, y1 - by)], fill=255, width=1)
        else:
            d.rectangle([0, 0, w - 1, h - 1], outline=255, fill=255 if self._shape_mode == "rect_fill" else None)
        return mask, (bx, by)

    def _commit_shape(self):
        layer = self._shape_layer()
        idx = self._current_draw_index()
        self._shape_start = self._shape_end = None
        if layer is None:
            return
        mask, (bx, by) = layer
        self._notify_stroke_start()
        self._img.paste(idx, (bx, by, bx + mask.width, by + mask.height), mask)
        self._notify_modified()
        self._redraw()

    def _current_draw_index(self) -> int:
        r, g, b, a = self._draw_color
        if a == 0:
            return ALPHA_INDEX
        if (
            self._draw_index is not None
            and self._draw_index != ALPHA_INDEX
            and 0 <= self._draw_index < len(self._palette)
            and self._palette[self._draw_index] == (r, g, b)
        ):
            return self._draw_index
        return _rgb_to_palette_index(r, g, b, self._palette, start_index=1)

    def begin_text(self, mask: Image.Image, pos: tuple[int, int]) -> bool:
        """Start a movable text paste: `mask` ('L', 255 = glyph pixel) painted in the current color."""
        if self._img is None or mask is None:
            return False
        idx = self._current_draw_index()
        if idx == ALPHA_INDEX:
            return False
        self._commit_paste()
        w, h = mask.size
        buf = Image.new("P", (w, h), ALPHA_INDEX)
        buf.paste(idx, (0, 0, w, h), mask)
        self._paste_buf = buf
        self._paste_src = None            # no source -> no resize handles
        self._paste_transparent = True
        self._paste_resize_corner = None
        self._paste_drag_start = None
        self._paste_pos = pos
        self._sel = (pos[0], pos[1], pos[0] + w - 1, pos[1] + h - 1)
        self._tool = TOOL_MOVE_PASTE
        self._update_cursor()
        self._redraw()
        return True

    def _paint_pixel(self, px: int, py: int):
        self._paint_pixel_raw(px, py)
        self._notify_modified()
        self._redraw()

    def _notify_modified(self):
        if self._on_modified:
            self._on_modified(stroke_start=False)

    def _notify_stroke_start(self):
        if self._on_modified:
            self._on_modified(stroke_start=True)


class PicEditorPanel(ttk.Frame):

    def __init__(self, parent, standalone=True, **kw):
        super().__init__(parent, **kw)
        self._standalone = standalone
        self._text_last = "TEXT"
        self._text_font = "FLOW.FON"
        self._text_scale = 1
        self._shape_idx = 0
        self._last_tool_value = TOOL_DRAW
        self._pic_dir:      str         = ""
        self._pic_files:    list[str]   = []
        self._current_idx:  int         = -1
        self._current_path: str         = ""
        self._active_palette_name: str  = "Default 2.0"
        self._active_palette: list[tuple[int,int,int]] = list(_PAL_NORMAL20)
        self._base_palette_name: str    = "Default 2.0"   # last non-embedded palette
        self._palette_auto: bool        = True            # follow the detected format
        self._folder_format: str | None = None            # BMP / BMH (auto-detected)
        self._current_format: str       = FMT_BMP         # format of the open file
        self._embedded_palette: list[tuple[int,int,int]] | None = None
        self._embedded_trailer: bytes   = b""
        # Embedded palettes seen in this folder, reusable by files without one
        # (e.g. 41.VGA has no palette of its own and uses the one of 128.VGA).
        self._extra_palettes: dict[str, list[tuple[int,int,int]]] = {}
        self._modified  = False
        self._undo_stack: list[Image.Image] = []
        self._apply_style()
        self._build_ui()

    def _apply_style(self):
        s = ttk.Style(self)
        try:
            s.theme_use("clam")
        except Exception:
            pass
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 9))
        s.configure("TLabelframe", background=BG, foreground=FG, font=("Segoe UI", 9, "bold"))
        s.configure("TLabelframe.Label", background=BG, foreground=FG)
        s.configure("TButton", font=("Segoe UI", 9, "bold"), padding=5, background=ACCENT, foreground="white", borderwidth=0)
        s.map("TButton", background=[("active", "#2980B9"), ("disabled", "#BDC3C7")])
        s.configure("Toolbutton", font=("Segoe UI", 9))
        s.configure("Tool.Toolbutton", font=("Segoe UI", 8), padding=(1, 3))   # compact: 3 buttons per row

    def _build_ui(self):
        sb = ttk.Frame(self, padding=(8, 2))
        sb.pack(fill=tk.X, side=tk.BOTTOM)
        self._status_lbl = ttk.Label(sb, text="Ready.", foreground=MUTED)
        self._status_lbl.pack(side=tk.LEFT)
        self._pixel_lbl  = ttk.Label(sb, text="", foreground=MUTED)
        self._pixel_lbl.pack(side=tk.RIGHT)
        self._hint_lbl = ttk.Label(sb, text="", foreground="#5D8AA8", font=("Segoe UI", 9))
        self._hint_lbl.pack(side=tk.LEFT, padx=(16, 0))
        center = ttk.Frame(self)
        center.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        sidebar = ttk.Frame(center, padding=(6, 6), width=200)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0), pady=6)
        sidebar.pack_propagate(False)
        self._build_toolbox(sidebar)
        self._canvas_frame = _ImageCanvas(center,on_modified=self._on_canvas_modified,on_color_picked=self._on_color_picked_from_canvas,on_text_request=self._on_text_request,)
        self._canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        self._canvas_frame._canvas.bind("<Motion>", self._on_mouse_move, add="+")
        self._canvas_frame._zoom_changed_callback = (lambda z: self._zoom_var.set(z))
        self._draw_swatch()

    def _build_toolbox(self, parent):
        self._tool_var = tk.StringVar(value=TOOL_DRAW)
        f_file = ttk.LabelFrame(parent, text="File", padding=(4, 4))
        f_file.pack(fill=tk.X, pady=(0, 6))
        if self._standalone:
            ttk.Button(f_file, text="📁 VGA Folder…", command=self._browse_dir).pack(fill=tk.X, pady=(0, 4))
        self._btn_save = ttk.Button(f_file, text="Save As…", command=self._save_as, state="disabled")
        self._btn_save.pack(fill=tk.X, pady=2)
        io_row = ttk.Frame(f_file)
        io_row.pack(fill=tk.X, pady=2)
        io_row.columnconfigure(0, weight=1)
        io_row.columnconfigure(1, weight=1)
        self._btn_import = ttk.Button(io_row, text="⬆ Import…", command=self._import_image, state="disabled")
        self._btn_import.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self._btn_export = ttk.Button(io_row, text="⬇ Export…", command=self._export_image, state="disabled")
        self._btn_export.grid(row=0, column=1, sticky="ew", padx=(2, 0))
        self._file_var = tk.StringVar()
        self._file_combo = ttk.Combobox(f_file, textvariable=self._file_var, values=[], state="readonly", width=18)
        self._file_combo.pack(fill=tk.X, pady=(4, 4))
        self._file_combo.bind("<<ComboboxSelected>>", self._on_file_selected)
        self._file_combo.bind("<MouseWheel>",         self._on_file_scroll)
        self._file_combo.bind("<Up>", self._on_file_updown)
        self._file_combo.bind("<Down>", self._on_file_updown)
        info_row = ttk.Frame(f_file)
        info_row.pack(fill=tk.X)
        self._info_lbl = ttk.Label(info_row, text="", foreground=MUTED)
        self._info_lbl.pack(side=tk.LEFT, anchor="w")
        self._dirty_lbl = ttk.Label(info_row, text="", foreground=RED, font=("Segoe UI", 9, "bold"))
        self._dirty_lbl.pack(side=tk.RIGHT, anchor="e")
        self._fmt_lbl = ttk.Label(f_file, text="", foreground=MUTED)
        self._fmt_lbl.pack(fill=tk.X, anchor="w")
        f_tools = ttk.LabelFrame(parent, text="Tools", padding=(4, 2))
        f_tools.pack(fill=tk.X, pady=3)
        for _c in range(3):
            f_tools.columnconfigure(_c, weight=1, uniform="tools")
        _tools = (
            ("✏ Pencil", TOOL_DRAW,   0, 0), ("▢ Select", TOOL_SELECT, 0, 1), ("🪣 Fill", TOOL_FILL, 0, 2),
            ("〜 Soften", TOOL_SOFTEN, 1, 0), ("T Text",   TOOL_TEXT,   1, 1), (self._SHAPE_MODES[0][1], TOOL_SHAPE, 1, 2),
        )
        for _txt, _val, _r, _c in _tools:
            _rb = ttk.Radiobutton(f_tools, text=_txt, variable=self._tool_var, value=_val, command=self._on_tool_change, style="Tool.Toolbutton")
            _rb.grid(row=_r, column=_c, sticky="ew", padx=1, pady=1)
            if _val == TOOL_SHAPE:
                self._shape_btn = _rb
        f_sel = ttk.LabelFrame(parent, text="Pasted selection", padding=(4, 2))
        f_sel.pack(fill=tk.X, pady=3)
        sel_grid = ttk.Frame(f_sel)
        sel_grid.pack(fill=tk.X)
        sel_grid.columnconfigure(0, weight=1)
        sel_grid.columnconfigure(1, weight=1)
        sel_grid.columnconfigure(2, weight=0)
        self._btn_rotate = ttk.Button(sel_grid, text="⟳ Rotate", command=self._rotate_sel, state="disabled")
        self._btn_rotate.grid(row=0, column=0, sticky="ew", padx=1, pady=1)
        self._btn_mirror = ttk.Button(sel_grid, text="⇹ Mirror", command=self._mirror_sel, state="disabled")
        self._btn_mirror.grid(row=0, column=1, columnspan=2, sticky="ew", padx=1, pady=1)
        self._btn_delete = ttk.Button(sel_grid, text="🗑 Delete", command=self._delete_sel, state="disabled")
        self._btn_delete.grid(row=1, column=0, sticky="ew", padx=1, pady=1)
        self._aspect_lock = tk.BooleanVar(value=False)
        lock_cell = ttk.Frame(sel_grid)
        lock_cell.grid(row=1, column=1, columnspan=2, sticky="ew", padx=1, pady=1)
        lock_cell.columnconfigure(0, weight=0)
        lock_cell.columnconfigure(1, weight=1)
        self._lock_bg_off = "#c0392b"
        self._lock_bg_off_dim = "#7f2a1e"
        self._btn_lock = tk.Button(lock_cell,text="🔓",width=2,command=self._toggle_aspect_lock,state="disabled",relief="flat",bg=self._lock_bg_off_dim,fg="white",disabledforeground="white",activebackground="#e74c3c",activeforeground="white",font=("",9),cursor="hand2",bd=0,padx=4)
        self._btn_lock.grid(row=0, column=0, sticky="ns", ipady=1)
        self._lbl_lock = tk.Label(lock_cell, text="Aspect Ratio", font=("", 8),bg=self._lock_bg_off_dim, fg="#aaaaaa", cursor="arrow")
        self._lbl_lock.bind("<Button-1>", lambda _e: self._toggle_aspect_lock() if self._btn_lock["state"] == "normal" else None)
        self._lbl_lock.grid(row=0, column=1, sticky="nsew", ipady=1)
        flt_row = ttk.Frame(f_sel)
        flt_row.pack(fill=tk.X, pady=(3, 1))
        ttk.Label(flt_row, text="Filter:", foreground=MUTED).pack(side=tk.LEFT)
        self._resize_filter_var = tk.StringVar(value="Nearest (pixel-perfect)")
        self._resize_filter_combo = ttk.Combobox(flt_row,textvariable=self._resize_filter_var,values=[label for label, _ in self._RESIZE_FILTERS],state="readonly",width=14,)
        self._resize_filter_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        self._resize_filter_combo.bind("<<ComboboxSelected>>", self._on_resize_filter_changed)
        f_colors = ttk.LabelFrame(parent, text="Colors", padding=(4, 2))
        f_colors.pack(fill=tk.X, pady=3)
        crow = ttk.Frame(f_colors)
        crow.pack(fill=tk.X, pady=(0, 4))
        self._color_canvas = tk.Canvas(crow, width=22, height=22, highlightthickness=1, highlightbackground="#888", cursor="arrow")
        self._color_canvas.pack(side=tk.LEFT)
        self._color_hex = ttk.Label(crow, text="#FFFFFF", font=("Consolas", 9), foreground=MUTED)
        self._color_hex.pack(side=tk.LEFT, padx=6)
        self._update_color_display((255, 255, 255, 255))
        palette_row = ttk.Frame(f_colors)
        palette_row.pack(fill=tk.X, pady=(1, 0))

        ttk.Label(palette_row, text="Palette:", foreground=MUTED).pack(side=tk.LEFT)

        self._show_alpha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            palette_row,
            text="Show Alpha",
            variable=self._show_alpha_var,
            command=self._on_show_alpha_toggle,
        ).pack(side=tk.RIGHT)
        self._swatch_frame = tk.Frame(f_colors, bg=BG)
        self._swatch_frame.pack(fill=tk.X, pady=(1, 2))
        self._swatch_canvas = tk.Canvas(self._swatch_frame, highlightthickness=0, bd=0, bg=BG)
        self._swatch_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._swatch_canvas.bind("<Button-1>", self._on_swatch_click)
        self._swatch_canvas.bind("<Configure>", lambda _e: self._draw_swatch())
        prow = ttk.Frame(f_colors)
        prow.pack(fill=tk.X, pady=(2, 0))
        ttk.Label(prow, text="Change:", foreground=MUTED).pack(side=tk.LEFT)
        self._pal_var = tk.StringVar(value="Default 2.0")
        pal_names = list(BUILTIN_PALETTES.keys())
        self._pal_combo = ttk.Combobox(prow, textvariable=self._pal_var, values=pal_names, state="readonly", width=12)
        self._pal_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))
        self._pal_combo.bind("<<ComboboxSelected>>", self._on_palette_changed)
        f_view = ttk.LabelFrame(parent, text="View", padding=(4, 2))
        f_view.pack(fill=tk.X, pady=3)
        zrow = ttk.Frame(f_view)
        zrow.pack(fill=tk.X)
        ttk.Label(zrow, text="Zoom:", foreground=MUTED).pack(side=tk.LEFT)
        self._zoom_var = tk.IntVar(value=2)
        self._zoom_spin = ttk.Spinbox(zrow, from_=1, to=16, width=2, textvariable=self._zoom_var, command=self._on_zoom_change)
        self._zoom_spin.pack(side=tk.LEFT, padx=(4, 0))
        self._zoom_spin.bind("<Return>", lambda e: self._on_zoom_change())
        self._zoom_spin.bind("<FocusOut>", lambda e: self._on_zoom_change())
        self._grid_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(zrow, text="Show grid", variable=self._grid_var, command=self._on_grid_toggle).pack(side=tk.RIGHT, padx=(10, 0))
        self._btn_undo = ttk.Button(parent, text="↩ Undo (Ctrl+Z)", command=self._undo, state="disabled")
        self._btn_undo.pack(fill=tk.X, pady=(6, 2))
        cmd_key = "Command" if sys.platform == "darwin" else "Control"
        self.bind_all(f"<{cmd_key}-c>",  lambda _e: self._copy())
        self.bind_all(f"<{cmd_key}-C>",  lambda _e: self._copy())
        self.bind_all(f"<{cmd_key}-v>",  lambda _e: self._paste())
        self.bind_all(f"<{cmd_key}-V>",  lambda _e: self._paste())
        self.bind_all(f"<{cmd_key}-z>",  lambda _e: self._undo())
        self.bind_all(f"<{cmd_key}-Z>",  lambda _e: self._undo())
        self.bind_all("<Return>",        lambda _e: self._apply_paste())
        self.bind_all("<KP_Enter>",      lambda _e: self._apply_paste())
        self.bind_all("<Delete>",        lambda _e: self._delete_sel())
        self.bind_all("<Escape>",        lambda _e: self._escape_action())
        self.after_idle(lambda: self._hint_lbl.config(
            text=self._TOOL_HINTS.get(self._tool_var.get(), ""))
            if hasattr(self, "_hint_lbl") else None
        )

    def _on_resize_filter_changed(self, _event=None):
        label = self._resize_filter_var.get()
        for lbl, flt in self._RESIZE_FILTERS:
            if lbl == label:
                self._canvas_frame._paste_resize_filter = flt
                break

    def _set_lock_appearance(self, locked: bool | None = None, enabled: bool = True):
        if locked is None:
            locked = self._aspect_lock.get()
        if not enabled:
            btn_kw  = dict(text="🔓", bg=self._lock_bg_off_dim,activebackground="#e74c3c", state="disabled", fg="white")
            lbl_kw  = dict(bg=self._lock_bg_off_dim, fg="#888888", cursor="arrow")
        elif locked:
            btn_kw  = dict(text="🔒", bg="#27ae60",activebackground="#2ecc71", state="normal", fg="white")
            lbl_kw  = dict(bg="#27ae60", fg="white", cursor="hand2")
        else:
            btn_kw  = dict(text="🔓", bg=self._lock_bg_off,activebackground="#e74c3c", state="normal", fg="white")
            lbl_kw  = dict(bg=self._lock_bg_off, fg="white", cursor="hand2")
        self._btn_lock.config(**btn_kw)
        self._lbl_lock.config(**lbl_kw)

    def _toggle_aspect_lock(self):
        locked = not self._aspect_lock.get()
        self._aspect_lock.set(locked)
        self._canvas_frame._paste_aspect_lock = locked
        self._set_lock_appearance(locked)

    def _update_selection_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for btn in (self._btn_rotate, self._btn_mirror, self._btn_delete):
            btn.config(state=state)
        if not enabled:
            self._aspect_lock.set(False)
            self._canvas_frame._paste_aspect_lock = False
        self._set_lock_appearance(enabled=enabled)
    
    def _escape_action(self):
        if self._canvas_frame._paste_buf is not None:
            self._canvas_frame.delete_selection()
        else:
            self._canvas_frame.deselect()
        self._update_selection_buttons(False)

    def set_pic_dir(self, path: str):
        if not path or not os.path.isdir(path):
            self._set_status(f"Folder not found: {path}")
            return
        self._pic_dir = path
        self._palette_auto = True
        self._extra_palettes.clear()
        self._scan_files()
        if self._pic_files:
            self._apply_palette_name(
                DEFAULT_PALETTE_FOR_FORMAT.get(self._folder_format or FMT_BMP,
                                               "Default 2.0"))
            self._load_index(0)

    def _browse_dir(self):
        d = filedialog.askdirectory(title="Select VGA Folder")
        if d:
            self.set_pic_dir(d)

    def _scan_files(self):
        exts = {".vga", ".VGA", ".cp", ".CP"}
        files = [f for f in os.listdir(self._pic_dir)
                 if os.path.splitext(f)[1] in exts]
        self._pic_files = sorted(files, key=_natural_key)
        n = len(self._pic_files)
        self._file_combo.config(values=self._pic_files)
        self._folder_format, mixed = self._detect_folder_format()
        if self._folder_format is None:
            fmt_txt = "format not recognised"
        else:
            fmt_txt = f"format: {self._folder_format} (auto-detected"
            fmt_txt += ", mixed folder)" if mixed else ")"
        self._set_status(f"{n} .VGA/.CP files found in {self._pic_dir}  [{fmt_txt}]")

    def _detect_folder_format(self) -> tuple[str | None, bool]:
        """Sample the files of the folder and vote for BMP or BMH.

        Returns (majority format or None, folder_is_mixed).
        """
        files = self._pic_files
        if not files:
            return None, False
        step = max(1, len(files) // 24)
        votes = {FMT_BMP: 0, FMT_BMH: 0}
        for fname in files[::step][:24]:
            try:
                with open(os.path.join(self._pic_dir, fname), "rb") as f:
                    data = f.read()
            except OSError:
                continue
            fmt = detect_vga_format(data)
            if fmt:
                votes[fmt] += 1
        if not any(votes.values()):
            return None, False
        best = max(votes, key=lambda k: votes[k])
        mixed = votes[FMT_BMP] > 0 and votes[FMT_BMH] > 0
        return best, mixed

    def _load_index(self, idx: int):
        if not self._pic_files:
            return
        idx = max(0, min(idx, len(self._pic_files) - 1))
        self._current_idx = idx
        fname = self._pic_files[idx]
        fpath = os.path.join(self._pic_dir, fname)

        vf = load_vga_file(fpath, None, prefer_fmt=self._folder_format)
        if vf is None:
            self._set_status(f"Failed to load {fname} (neither valid BMP nor BMH format)")
            return
        img = vf.image
        self._current_path = fpath
        self._current_format = vf.fmt
        self._embedded_trailer = vf.trailer
        self._embedded_palette = vf.embedded_palette
        self._extra_palettes.clear()      # shared palette only lives for this file
        self._undo_stack.clear()
        pal_name = self._palette_for_loaded_file()
        self._refresh_palette_choices()
        self._apply_palette_name(pal_name)
        self._canvas_frame.set_palette(self._active_palette)
        self._canvas_frame.set_image(img)
        self._canvas_frame.set_zoom(self._zoom_var.get())
        w, h = img.size
        self._file_var.set(fname)
        self._info_lbl.config(
            text=f"{w}×{h}  ({os.path.getsize(fpath):,} B)")
        extra = ""
        if self._embedded_palette:
            extra = f"  +palette ({len(self._embedded_palette)})"
        self._fmt_lbl.config(text=f"Format: {vf.fmt} (auto){extra}")
        self._set_dirty(False)
        self._enable_file_buttons(True)
        self._set_status(f"Loaded: {fpath}  [{vf.fmt}, palette: {self._active_palette_name}]")

    def _shared_palette_name(self, fname: str) -> str | None:
        """Name of the shared palette for `fname` (loading its source file), if any."""
        stem = os.path.splitext(fname)[0]
        if not stem.isdigit() or self._current_format != FMT_BMH:
            return None
        num = int(stem)
        for lo, hi, src in SHARED_PALETTE_RULES_BMH:
            if not (lo <= num <= hi):
                continue
            src_name = next(
                (f for f in self._pic_files
                 if os.path.splitext(f)[0].isdigit()
                 and int(os.path.splitext(f)[0]) == src), None)
            if src_name is None:
                return None
            label = f"From {src_name}"
            if label not in self._extra_palettes:
                vf = load_vga_file(os.path.join(self._pic_dir, src_name),
                                   None, prefer_fmt=FMT_BMH)
                if vf is None or not vf.embedded_palette:
                    return None
                self._extra_palettes[label] = list(vf.embedded_palette)
            return label
        return None

    def _palette_for_loaded_file(self) -> str:
        """Pick the palette to show for the file that was just loaded."""
        if self._embedded_palette:
            return EMBEDDED_PALETTE_NAME
        shared = self._shared_palette_name(os.path.basename(self._current_path))
        if shared:
            return shared
        return DEFAULT_PALETTE_FOR_FORMAT.get(self._current_format, "Default 2.0")

    def _refresh_palette_choices(self):
        names = list(BUILTIN_PALETTES.keys()) + list(self._extra_palettes.keys())
        if self._embedded_palette:
            names.append(EMBEDDED_PALETTE_NAME)
        self._pal_combo.config(values=names)

    def _apply_palette_name(self, name: str):
        """Activate a palette by name (built-in or the file's embedded one)."""
        if name == EMBEDDED_PALETTE_NAME and self._embedded_palette:
            pal = self._embedded_palette
        elif name in BUILTIN_PALETTES:
            pal = BUILTIN_PALETTES[name]
            self._base_palette_name = name
        elif name in self._extra_palettes:
            pal = self._extra_palettes[name]
            self._base_palette_name = name
        else:
            return
        self._active_palette_name = name
        self._active_palette = list(pal)
        self._pal_var.set(name)
        self._canvas_frame.set_palette(self._active_palette)
        self._draw_swatch()

    def _confirm_discard(self) -> bool:
        if not self._modified:
            return True
        fname = os.path.basename(self._current_path) if self._current_path else "current file"
        return messagebox.askyesno(
            "Unsaved changes",
            f'"{fname}" has unsaved changes.\nDiscard them and switch file?',
            icon="warning",
            default="no",
        )

    def _on_file_selected(self, _event=None):
        fname = self._file_var.get()
        if fname in self._pic_files:
            new_idx = self._pic_files.index(fname)
            if new_idx == self._current_idx:
                return
            if not self._confirm_discard():
                self._file_var.set(self._pic_files[self._current_idx] if self._current_idx >= 0 else "")
                return
            self._load_index(new_idx)

    def _on_file_scroll(self, event):
        if not self._pic_files:
            return "break"
        if event.delta > 0:
            direction = -1
        elif event.delta < 0:
            direction = 1
        else:
            return "break"
        new_idx = max(0, min(len(self._pic_files) - 1, self._current_idx + direction))
        if new_idx != self._current_idx:
            if not self._confirm_discard():
                return "break"
            self._load_index(new_idx)
        return "break"

    def _on_file_updown(self, event):
        if not self._pic_files:
            return "break"
        direction = -1 if event.keysym == "Up" else 1
        new_idx = max(0, min(len(self._pic_files) - 1, self._current_idx + direction))
        if new_idx != self._current_idx:
            if not self._confirm_discard():
                return "break"
            self._load_index(new_idx)
        return "break"

    def _save_as(self):
        img = self._canvas_frame.get_image()
        if img is None:
            return
        current_fname = os.path.basename(self._current_path) if self._current_path else ""   
        dest = filedialog.asksaveasfilename(
            title="Save Image As…",
            defaultextension=".VGA",
            filetypes=[(f"VGA/CP Image ({self._current_format})", "*.VGA *.vga *.CP *.cp"), ("All files", "*.*")],
            initialdir=self._pic_dir or ".",
            initialfile=current_fname,
        )
        if not dest:
            return
        self._do_save(img, dest)

    def _do_save(self, img: Image.Image, dest: str):
        self._set_status("Saving…")
        self.update_idletasks()
        try:
            save_vga_image(img, dest, fmt=self._current_format,
                           trailer=self._embedded_trailer)
            self._set_dirty(False)
            sz = os.path.getsize(dest)
            self._info_lbl.config(text=f"{img.width}×{img.height}  ({sz:,} B)")
            self._set_status(f"Saved: {dest}  ({sz:,} B, {self._current_format})")
        except VgaEncodeError as exc:
            messagebox.showerror("VGA Save Error", str(exc))
            self._set_status("Save failed.")
        except Exception as exc:
            messagebox.showerror("Unexpected Error", str(exc))
            self._set_status("Save failed.")

    def _enable_file_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._btn_save.config(state=state)
        self._btn_import.config(state=state)
        self._btn_export.config(state=state)
        self._btn_undo.config(state=state)

    _RESIZE_FILTERS = [
        ("Nearest (pixel-perfect)",  Image.NEAREST),
        ("Box (average)",            Image.BOX),
        ("Bilinear",                 Image.BILINEAR),
        ("Hamming",                  Image.HAMMING),
        ("Bicubic",                  Image.BICUBIC),
        ("Lanczos (best quality)",   Image.LANCZOS),
    ]

    _PREVIEW_W = 200
    _PREVIEW_H = 160

    def _ask_resize_filter(
        self,
        src_rgb: "Image.Image",
        target_size: "tuple[int,int]",
    ) -> "Image.Resampling | None":
        result: list = [None]
        tw, th = target_size
        pw, ph = self._PREVIEW_W, self._PREVIEW_H
        scale = min(pw / tw, ph / th)
        prev_w = max(1, int(tw * scale))
        prev_h = max(1, int(th * scale))

        def make_preview(flt):
            resized = src_rgb.convert("RGBA").resize((tw, th), flt)
            q = _quantize_rgba_to_palette(resized, self._active_palette)
            preview_pal = _palette_to_flat_rgb(self._active_palette)
            preview_pal[0:3] = (255, 0, 255)
            q.putpalette(preview_pal)
            rgb = q.convert("RGB")
            thumb = rgb.resize((prev_w, prev_h), Image.NEAREST)
            canvas = Image.new("RGB", (pw, ph), (30, 30, 30))
            ox = (pw - prev_w) // 2
            oy = (ph - prev_h) // 2
            canvas.paste(thumb, (ox, oy))
            return ImageTk.PhotoImage(canvas)

        previews = {label: make_preview(flt) for label, flt in self._RESIZE_FILTERS}
        dlg = tk.Toplevel(self)
        dlg.title("Resize filter")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self)
        body = ttk.Frame(dlg, padding=10)
        body.pack(fill=tk.BOTH)
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, anchor="n", padx=(0, 12))
        ttk.Label(left, text="Algorithm:", font=("", 9, "bold")).pack(anchor="w", pady=(0, 6))
        current_label = self._resize_filter_var.get()
        filter_var = tk.StringVar(value=current_label if current_label else self._RESIZE_FILTERS[0][0])
        right = ttk.LabelFrame(body, text=f"Preview  ({tw}×{th} → quantised)", padding=4)
        right.pack(side=tk.LEFT, anchor="n")
        preview_label = ttk.Label(right)
        preview_label.pack()
        size_lbl = ttk.Label(right, text="", foreground="#888888")
        size_lbl.pack()

        def update_preview(*_):
            lbl = filter_var.get()
            preview_label.configure(image=previews[lbl])
            preview_label.image = previews[lbl]

        for label, _ in self._RESIZE_FILTERS:
            ttk.Radiobutton(
                left, text=label, variable=filter_var, value=label,
                command=update_preview,
            ).pack(anchor="w", pady=2)
        update_preview()
        btn_row = ttk.Frame(dlg, padding=(10, 4, 10, 10))
        btn_row.pack(fill=tk.X)

        def on_ok():
            chosen_label = filter_var.get()
            for label, flt in self._RESIZE_FILTERS:
                if label == chosen_label:
                    result[0] = flt
                    break
            self._resize_filter_var.set(chosen_label)
            self._on_resize_filter_changed()
            dlg.destroy()

        def on_cancel():
            dlg.destroy()
        ttk.Button(btn_row, text="OK",     command=on_ok).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_row, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)
        dlg.bind("<Return>", lambda _e: on_ok())
        dlg.bind("<Escape>", lambda _e: on_cancel())
        self.update_idletasks()
        dlg.update_idletasks()
        px = self.winfo_rootx() + self.winfo_width()  // 2
        py = self.winfo_rooty() + self.winfo_height() // 2
        dlg.geometry(f"+{px - dlg.winfo_width() // 2}+{py - dlg.winfo_height() // 2}")
        self.wait_window(dlg)
        return result[0]

    def _import_image(self):
        if self._canvas_frame._img is None:
            return
        path = filedialog.askopenfilename(
            title="Import Image…",
            filetypes=[
                ("Image files", "*.png *.PNG *.bmp *.BMP *.jpg *.JPG *.jpeg *.JPEG"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            src = Image.open(path).convert("RGBA")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Cannot open image:\n{exc}")
            return

        iw, ih = self._canvas_frame._img.size
        sw, sh = src.size

        if sw > iw or sh > ih:
            answer = messagebox.askyesnocancel(
                "Image too large",
                f"The imported image ({sw}×{sh}) is larger than the canvas ({iw}×{ih}).\n\n"
                "• Yes   – resize to fit (aspect ratio preserved)\n"
                "• No    – keep original size (drag to position, cropped on commit)\n"
                "• Cancel – abort",
            )
            if answer is None:
                return
            if answer:
                scale = min(iw / sw, ih / sh)
                new_w = max(1, int(sw * scale))
                new_h = max(1, int(sh * scale))
                flt = self._ask_resize_filter(src, (new_w, new_h))
                if flt is None:
                    return
                src = src.resize((new_w, new_h), flt)
        quantised = _quantize_rgba_to_palette(src, self._active_palette)
        self._canvas_frame._clipboard = quantised
        self._canvas_frame._commit_paste()
        self._canvas_frame._paste_buf = quantised.copy()
        self._canvas_frame._paste_src = src 
        self._canvas_frame._paste_resize_corner = None
        self._canvas_frame._paste_pos = (0, 0)
        pw, ph = quantised.size
        self._canvas_frame._sel = (0, 0, pw - 1, ph - 1)
        self._canvas_frame._tool = TOOL_MOVE_PASTE
        self._canvas_frame._update_cursor()
        self._canvas_frame._redraw()
        self._update_selection_buttons(True)
        self._set_status(
            f"Imported: {os.path.basename(path)} ({quantised.width}×{quantised.height})"
            " — Paste active — drag to move  │  drag corner handle to resize (Shift or 🔒 = lock A/R)  │  Enter = commit  │  ESC = cancel"
        )

    def _export_image(self):
        img = self._canvas_frame.get_image()
        if img is None:
            return
        path = filedialog.asksaveasfilename(
            title="Export Image As…",
            defaultextension=".png",
            filetypes=[
                ("PNG",  "*.png"),
                ("BMP",  "*.bmp"),
                ("JPEG", "*.jpg"),
                ("All files", "*.*"),
            ],
            initialdir=self._pic_dir or ".",
        )
        if not path:
            return
        try:
            export = img.copy()
            export.putpalette(_palette_to_flat_rgb(self._active_palette))
            ext = os.path.splitext(path)[1].lower()
            rgb = export.convert("RGB")
            if ext == ".png":
                # Transparency is defined by palette index 0, not by RGB value.
                rgba = rgb.convert("RGBA")
                alpha_bytes = bytes(
                    0 if i == ALPHA_INDEX else 255
                    for i in export.tobytes()
                )
                alpha = Image.frombytes("L", export.size, alpha_bytes)
                rgba.putalpha(alpha)
                rgba.save(path, "PNG")
            elif ext in (".jpg", ".jpeg"):
                rgb.save(path, "JPEG", quality=95)
            else:
                rgb.save(path)
            self._set_status(f"Exported: {path}")
        except Exception as exc:
            messagebox.showerror("Export Error", f"Cannot save image:\n{exc}")
            self._set_status("Export failed.")

    def _on_palette_changed(self, _event=None):
        name = self._pal_var.get()
        if name == EMBEDDED_PALETTE_NAME and self._embedded_palette:
            pass
        elif name in BUILTIN_PALETTES or name in self._extra_palettes:
            # A manual choice stops the palette from following the file format.
            self._palette_auto = False
        else:
            self._pal_var.set(self._active_palette_name)
            return
        self._apply_palette_name(name)
        self._set_status(f"Palette: {self._active_palette_name}")

    def _draw_swatch(self):
        c = self._swatch_canvas
        c.delete("all")
        pal = self._active_palette
        n = len(pal)
        if n == 0:
            return
        if hasattr(self, "_swatch_vbar") and self._swatch_vbar.winfo_exists():
            self._swatch_vbar.pack_forget()
        c.update_idletasks()
        available_w = c.winfo_width()
        if available_w < 10:
            available_w = 180
        if n > 32:
            cols = 16
        else:
            cols = 8
        sq = max(6, available_w // cols)
        rows = (n + cols - 1) // cols
        canvas_w = cols * sq
        canvas_h = rows * sq
        c.config(width=canvas_w, height=canvas_h, scrollregion=(0, 0, canvas_w, canvas_h))
        for i, (r, g, b) in enumerate(pal):
            col = i % cols
            row = i // cols
            x0, y0 = col * sq, row * sq
            if i == ALPHA_INDEX:
                fill = ALPHA_DISPLAY_COLOR if self._show_alpha_var.get() else "#000000"
            else:
                fill = f"#{r:02X}{g:02X}{b:02X}"
            selected = (getattr(self._canvas_frame, "_draw_index", None) == i)
            c.create_rectangle(
                x0, y0, x0 + sq, y0 + sq,
                fill=fill,
                outline="#FFD700" if selected else "",
                width=2 if selected else 1,
            )


    def _on_swatch_click(self, event):
        pal = self._active_palette
        n = len(pal)
        if n > 32:
            cols = 16
        else:
            cols = 8

        c = self._swatch_canvas
        available_w = c.winfo_width()
        if available_w < 10:
            available_w = 180
        sq = max(6, available_w // cols)

        cy = int(c.canvasy(event.y))
        cx = int(c.canvasx(event.x))
        if cx < 0 or cy < 0:
            return
        col = cx // sq
        row = cy // sq
        rows = (n + cols - 1) // cols
        if not (0 <= col < cols and 0 <= row < rows):
            return
        idx = row * cols + col
        if idx < len(pal):
            r, g, b = pal[idx]
            rgba = (255, 0, 255, 0) if idx == ALPHA_INDEX else (r, g, b, 255)
            self._apply_draw_color(rgba, pal_idx=idx)

    _TOOL_HINTS: dict[str, str] = {
        TOOL_DRAW:   "Pencil — Left-click/drag to draw  │  Right-click to pick color",
        TOOL_SELECT: "Select — Left-click/drag to select a region  │  Ctrl+C copy  │  Ctrl+V paste  │  ESC deselect",
        TOOL_FILL:   "Fill — Left-click to flood-fill a region with the current color",
        TOOL_HAND:   "Hand — Left-click/drag to pan the canvas  │  Scroll wheel to zoom",
        TOOL_PICK:   "Pick — Left-click to sample a color from the canvas",
        TOOL_TEXT:   "Text — Left-click where the text should start  │  type it, pick font (MICRO4 / FLOW / NORMAL) and scale  │  drag to move, Enter = commit",
        TOOL_SHAPE:  "Line/Rect — drag to draw  │  click the button again to switch Line → Rect → Filled rect  │  Shift = 45° line / square  │  Right-click or ESC cancels",
        TOOL_SOFTEN: "Soften/Sharpen — Left-click/drag to soften  │  Right-click/drag to sharpen  │  Middle-click/drag to pan",
    }

    def _ensure_fonts(self):
        """Return the shared FontBank with the original .FON fonts loaded from .\\data, or None."""
        if any(FONTS.bitmap(n) is None for n in _TEXT_FONTS):
            FONTS.load(_font_data_dirs())
        if all(FONTS.bitmap(n) is None for n in _TEXT_FONTS):
            messagebox.showerror("Text tool", "No .FON file found (MICRO4.FON, FLOW.FON, NORMAL.FON).\nSearched:\n" + "\n".join(_font_data_dirs()))
            return None
        return FONTS

    def _render_text_mask(self, text: str, font_name: str, scale: int) -> Image.Image | None:
        bank = self._ensure_fonts()
        bf = bank.bitmap(font_name) if bank else None
        return bf.render_mask(text, scale) if bf is not None else None

    def _on_text_request(self, pt: tuple[int, int]):
        cf = self._canvas_frame
        if cf._img is None:
            return
        if cf._current_draw_index() == ALPHA_INDEX:
            self._set_status("Text: pick an opaque color first (index 0 is transparent).")
            return
        bank = self._ensure_fonts()
        if bank is None:
            return
        avail = [n for n in _TEXT_FONTS if bank.bitmap(n) is not None]
        top = self.winfo_toplevel()
        dlg = tk.Toplevel(top)
        dlg.title("Text")
        dlg.transient(top)
        dlg.resizable(False, False)
        body = ttk.Frame(dlg, padding=10)
        body.pack(fill=tk.BOTH, expand=True)
        var_text = tk.StringVar(value=self._text_last)
        var_font = tk.StringVar(value=self._text_font if self._text_font in avail else avail[0])
        var_scale = tk.IntVar(value=self._text_scale)
        ttk.Label(body, text="Text:").grid(row=0, column=0, sticky="w", pady=2)
        ent = ttk.Entry(body, textvariable=var_text, width=36)
        ent.grid(row=0, column=1, columnspan=3, sticky="ew", pady=2)
        ttk.Label(body, text="Font:").grid(row=1, column=0, sticky="w", pady=2)
        cmb = ttk.Combobox(body, textvariable=var_font, values=avail, state="readonly", width=14)
        cmb.grid(row=1, column=1, sticky="w", pady=2)
        ttk.Label(body, text="Scale:").grid(row=1, column=2, sticky="e", padx=(10, 4), pady=2)
        spn = ttk.Spinbox(body, from_=1, to=8, textvariable=var_scale, width=4)
        spn.grid(row=1, column=3, sticky="w", pady=2)
        preview = tk.Canvas(body, width=330, height=84, bg="#1a1a2e", highlightthickness=1, highlightbackground="#555")
        preview.grid(row=2, column=0, columnspan=4, pady=(6, 8))
        btns = ttk.Frame(body)
        btns.grid(row=3, column=0, columnspan=4, sticky="e")

        def cur_scale() -> int:
            try:
                return max(1, min(8, int(var_scale.get())))
            except (tk.TclError, ValueError):
                return 1

        def refresh(*_a):
            preview.delete("all")
            txt = var_text.get()
            if not txt:
                return
            mask = self._render_text_mask(txt, var_font.get(), cur_scale())
            if mask is None:
                return
            idx = cf._current_draw_index()
            fg = cf._palette[idx] if 0 <= idx < len(cf._palette) else (255, 255, 255)
            im = Image.composite(Image.new("RGB", mask.size, fg), Image.new("RGB", mask.size, (26, 26, 46)), mask)
            if im.width > 320 or im.height > 74:
                im.thumbnail((320, 74), Image.NEAREST)
            preview.image = ImageTk.PhotoImage(im)
            preview.create_image(4, 4, anchor="nw", image=preview.image)

        def ok(_e=None):
            txt = var_text.get()
            if not txt:
                return "break"
            sc = cur_scale()
            mask = self._render_text_mask(txt, var_font.get(), sc)
            self._text_last, self._text_font, self._text_scale = txt, var_font.get(), sc
            dlg.destroy()
            if mask is not None and cf.begin_text(mask, pt):
                self._update_selection_buttons(True)
                self._set_status("Text placed — drag to move  │  Rotate/Mirror available  │  Enter = commit  │  ESC = cancel")
            return "break"

        def cancel(_e=None):
            dlg.destroy()
            return "break"

        ttk.Button(btns, text="OK", command=ok).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Cancel", command=cancel).pack(side=tk.RIGHT, padx=(0, 6))
        var_text.trace_add("write", refresh)
        var_scale.trace_add("write", refresh)
        cmb.bind("<<ComboboxSelected>>", refresh)
        dlg.bind("<Return>", ok)
        dlg.bind("<KP_Enter>", ok)
        dlg.bind("<Escape>", cancel)
        dlg.update_idletasks()
        dlg.geometry(f"+{top.winfo_rootx() + 140}+{top.winfo_rooty() + 120}")
        refresh()
        dlg.grab_set()
        ent.focus_set()
        ent.selection_range(0, tk.END)

    _SHAPE_MODES = (("line", "╱ Line", "Line"), ("rect", "▭ Rect", "Rectangle"), ("rect_fill", "■ Rect", "Filled rectangle"))

    def _cycle_shape_mode(self):
        self._shape_idx = (self._shape_idx + 1) % len(self._SHAPE_MODES)
        mode, label, name = self._SHAPE_MODES[self._shape_idx]
        self._shape_btn.config(text=label)
        self._canvas_frame.set_shape_mode(mode)
        self._set_status(f"Shape mode: {name}")

    def _on_tool_change(self):
        tool = self._tool_var.get()
        if tool == TOOL_SHAPE and self._last_tool_value == TOOL_SHAPE:
            self._cycle_shape_mode()   # clicking the active Line/Rect button cycles its mode
        self._last_tool_value = tool
        self._canvas_frame.set_tool(tool)
        hint = self._TOOL_HINTS.get(tool, "")
        self._hint_lbl.config(text=hint)

    def _on_zoom_change(self):
        try:
            z = int(self._zoom_var.get())
        except Exception:
            z = 1
        z = max(1, min(16, z))
        self._zoom_var.set(z)
        self._canvas_frame.set_zoom(z)

    def _on_show_alpha_toggle(self):
        self._canvas_frame.set_show_alpha(self._show_alpha_var.get())
        self._draw_swatch()

    def _on_grid_toggle(self):
        self._canvas_frame.set_show_grid(self._grid_var.get())

    def _on_color_picked_from_canvas(self, r, g, b, a, pal_idx=None):
        self._apply_draw_color((r, g, b, a), pal_idx=pal_idx)

    def _apply_draw_color(self, rgba: tuple, pal_idx: int | None = None):
        self._canvas_frame.set_draw_color(rgba, pal_idx=pal_idx)
        self._update_color_display(rgba, pal_idx=pal_idx)
        self._draw_swatch()

    def _update_color_display(self, rgba: tuple, pal_idx: int | None = None):
        r, g, b, a = rgba
        if pal_idx is None:
            pal_idx = ALPHA_INDEX if a == 0 else _rgb_to_palette_index(r, g, b, self._active_palette, start_index=1)
        hex_str = ALPHA_DISPLAY_COLOR if pal_idx == ALPHA_INDEX else f"#{r:02X}{g:02X}{b:02X}"
        self._color_canvas.config(bg=hex_str)
        self._color_canvas.delete("all")
        self._color_canvas.create_rectangle(0, 0, 32, 32, fill=hex_str, outline="")
        self._color_hex.config(text=f"{hex_str} (0x{pal_idx:02X})")

    def _copy(self):
        self._canvas_frame.copy_selection()
        self._set_status("Copied to clipboard.")

    def _paste(self):
        if self._canvas_frame.paste_selection():
            self._update_selection_buttons(True)
            self._set_status("Paste active — drag to move  │  drag corner handle to resize (Shift or 🔒 = lock A/R)  │  Enter = commit  │  ESC = cancel")

    def _apply_paste(self):
        if self._canvas_frame._tool == TOOL_MOVE_PASTE:
            self._canvas_frame.commit_paste_now()
            self._update_selection_buttons(False)
            self._set_status("Paste applied.")

    def _rotate_sel(self):
        self._canvas_frame.rotate_selection()
        self._set_status("Selection rotated.")

    def _mirror_sel(self):
        self._canvas_frame.mirror_selection()
        self._set_status("Selection mirrored.")

    def _delete_sel(self):
        self._canvas_frame.delete_selection()
        self._update_selection_buttons(False)
        self._set_status("Selection deleted.")

    def _push_undo(self, img: Image.Image | None):
        if img is None:
            return
        self._undo_stack.append(img.copy())
        if len(self._undo_stack) > 40:
            self._undo_stack.pop(0)

    def _undo(self):
        if not self._undo_stack:
            self._set_status("Nothing to undo.")
            return
        img = self._undo_stack.pop()
        self._canvas_frame.set_image_preserve_view(img)
        self._canvas_frame._canvas.focus_set()
        self._set_dirty(True)
        self._set_status("Undone.")

    def _on_canvas_modified(self, stroke_start: bool = False):
        if stroke_start and self._canvas_frame._img is not None:
            self._push_undo(self._canvas_frame._img)
        self._set_dirty(True)

    def _set_dirty(self, v: bool):
        self._modified = v
        self._dirty_lbl.config(text="⚠ Modified" if v else "")

    def _set_status(self, msg: str):
        self._status_lbl.config(text=msg)

    def _on_mouse_move(self, event):
        pt = self._canvas_frame._canvas_to_pixel(event.x, event.y)
        img = self._canvas_frame._img
        if pt and img is not None:
            px, py = pt
            try:
                idx = self._canvas_frame._pixel_index(pt)
                r, g, b, _ = self._canvas_frame._pixel_color(pt)
                if idx == ALPHA_INDEX:
                    self._pixel_lbl.config(text=f"({px}, {py})  ALPHA (0x{idx:02X})")
                else:
                    self._pixel_lbl.config(
                        text=f"({px}, {py})  #{r:02X}{g:02X}{b:02X} (0x{idx:02X})"
                    )
            except Exception:
                self._pixel_lbl.config(text=f"({px}, {py})")
        else:
            self._pixel_lbl.config(text="")


if __name__ == "__main__":
    _root = tk.Tk()
    _root.title("VGA Editor v1.5.0 - by TheRuler76")
    _root.geometry("1200x800")
    _panel = PicEditorPanel(_root)
    _panel.pack(fill=tk.BOTH, expand=True)
    if len(sys.argv) > 1:
        _panel.set_pic_dir(sys.argv[1])
    _root.mainloop()