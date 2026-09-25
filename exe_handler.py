import hashlib
import struct

MATCH_FLAG_TYPES = {
    "3v": {
        "3v1": "B8EE0050B86A0050B90100",
        "3v2": "B8EE0050B8D40050B9010051B96B00",
        "3v3": "B8EE0050B83E0150B8010050B8D500",
    },
    "3h": {
        "3h1": "B84F0050B83E0150B90100",
        "3h2": "B8A00050B83E0150B9500051B90100",
        "3h3": "B8EE0050B83E0150B8A10050B80100",
    },
    }

_1st_LEAGUE_TEAMS = {
    "20": "01010100141414002626260004040400",
    "18": "01010100121414002226260003040400",
    }

GAME_PROFILES = {
    "THE MANAGER (ITALIAN)": {
        "ds_start": 0x53CE0,
        "base_const": bytes.fromhex("F64C"),
        "ptr_ranges": [
            (0x543DC, 0x54474), (0x5511C, 0x55148), (0x5514A, 0x5518A),
            (0x55190, 0x5536C), (0x55370, 0x55438), (0x58526, 0x58686),
            (0x5868E, 0x589A0), (0x58932, 0x58F7E), (0x5D1AC, 0x5D364),
        ],
        "valid_ranges": [(0x5456E, 0x55088), (0x55444, 0x58525), (0x5890A, 0x58932), (0x59632, 0x5D191)],
        "code_ptrs":   [(0x2E3BB, 0x5890A), (0x2E402, 0x5891E)],
        "fixed_strings": [(0x55438, 11)],
        "code_year": 0x12AF2,
        "region_offset": 0x5508A,
        "points_offset": 0x550AD,
        "subst_gk_offset": 0x23ee0,
        "subst_offset": 0x23ee6,
        "teams": {
            "offset": 0x55096,
            "number": _1st_LEAGUE_TEAMS,
        },
        "wdl_map": 0x550b6,
        "match_flag": {
            "detect_offset": 0x9fe0,
            "color_offsets": (0x9fe1, 0xa007, 0xa030),
            "band_offsets": (0x9fe3, 0xa009, 0xa032),
            "font_color_offset": 0xa084,
            "types": MATCH_FLAG_TYPES,
        },
        "range_font_defaults": {0: "FLOW.FON", 1: "FLOW.FON", 2: "MICRO4.FON", 3: "MICRO4.FON"},
        "immutable_signature": {
            "header_size": 0x6D80,
            "relocation_table_offset": 0x1C,
            "relocation_count": 7000,
            "relocation_topology_sha256": [
                "95235ED9EEB658148E86843DC0381D846BB8FFD91C0515850EE23D590588ED15",  # original MZ
                "BD94929F6723F899244CB19BDF077AB36E8693126F311F64091468D6DECD5DC3",  # decompressed by EXEPACK
            ],
            "entry_cs": 0x3A45,
            "entry_ip": 0x0018,
            "diagnostic_stack_ss": 0x578D,
            "diagnostic_stack_sp": 0x1000,
            "code_anchors": (
                (0x0F753, "55 8B EC B8 0A 00 9A C8 02 ?? ?? 2A C0 50 B9 EF 00 51 B9 3F 01 51 B9 2B 00 51 2B C9 51 8E 06 AA"),
                (0x1F7B7, "55 8B EC B8 68 00 9A C8 02 ?? ?? 57 56 8E 06 2A"),
                (0x228E0, "55 8B EC B8 0E 00 9A C8 02 ?? ?? 56 C6 46 FA 00"),
            ),
        },
    },
    "BUNDESLIGA MANAGER PROFESSIONAL": {
        "ds_start": 0x537E0,
        "base_const": bytes.fromhex("B34C"),
        "ptr_ranges": [
            (0x53EDC, 0x53F74), (0x55AC0, 0x56174), (0x5617C, 0x56184),
            (0x581F4, 0x58226), (0x58248, 0x58884), (0x5C8B2, 0x5CA6A),
        ],
        "valid_ranges": [(0x5406E, 0x55A2C), (0x5618A, 0x581F3), (0x58226, 0x58247), (0x58D38, 0x5C897)],
        "code_ptrs":   [(0x2DEB3, 0x58226), (0x2DEFA, 0x58236)],
        "fixed_strings": [(0x56174, 8)],
        "code_year": 0x12A18,
        "region_offset": 0x55A2E,
        "points_offset": 0x55A51,
        "subst_gk_offset": 0x23a06,
        "subst_offset": 0x23a0c,
        "teams": {
            "offset": 0x55A3A,
            "number": _1st_LEAGUE_TEAMS,
        },
        "wdl_map": 0x55a5a,
        "match_flag": {
            "detect_offset": 0x9f10,
            "color_offsets": (0x9f11, 0x9f37, 0x9f60),
            "band_offsets": (0x9f13, 0x9f39, 0x9f62),
            "font_color_offset": 0x9fb4,
            "types": MATCH_FLAG_TYPES,
        },
        "range_font_defaults": {0: "FLOW.FON", 1: "FLOW.FON", 2: "MICRO4.FON", 3: "MICRO4.FON"},
        "immutable_signature": {
            "header_size": 0x6CB0,
            "relocation_table_offset": 0x1C,
            "relocation_count": 6946,
            "relocation_topology_sha256": "8D0F8560784383D50D92DB5902B9ABF4ADA29D34035CD6FE18F14E2EEE29611E",
            "entry_cs": 0x3A01,
            "entry_ip": 0x0016,
            "diagnostic_stack_ss": 0x5709,
            "diagnostic_stack_sp": 0x1000,
            "code_anchors": (
                (0x0F749, "55 8B EC B8 0A 00 9A C6 02 ?? ?? 2A C0 50 B9 EF 00 51 B9 3F 01 51 B9 2B 00 51 2B C9 51 8E 06 B0"),
                (0x1FFFA, "55 8B EC B8 02 00 9A C6 02 ?? ?? 8E 06 20 9E B0"),
                (0x242CF, "55 8B EC B8 4A 00 9A C6 02 ?? ?? 8E 06 AA 9E 26"),
            ),
        },
    },
    "THE MANAGER (ENGLISH)": {
        "ds_start": 0x52320,
        "base_const": bytes.fromhex("694B"),
        "ptr_ranges": [
            (0x535E0, 0x535FC), (0x535FE, 0x53646), (0x5364C, 0x538F4),
            (0x56182, 0x562BA), (0x562EA, 0x56566), (0x56582, 0x56AB6),
            (0x56CB8, 0x56DCC), (0x5ADE8, 0x5AFA0),
        ],
        "valid_ranges": [(0x52B9A, 0x5354C), (0x538FC, 0x56182), (0x56566, 0x56582), (0x5726E, 0x5ADCD)],
        "code_ptrs": [(0x2E16B, 0x56566), (0x2E1B2, 0x56574)],
        "fixed_strings": [(0x538F4, 8)],
        "code_year": 0x128A2,
        "region_offset": 0x5354E,
        "points_offset": 0x53571,
        "subst_gk_offset": 0x23c90,
        "subst_offset": 0x23c96,
        "teams": {
            "offset": 0x5355A,
            "number": _1st_LEAGUE_TEAMS,
        },
        "wdl_map": 0x5357a,
        "match_flag": {
            "detect_offset": 0x9ef0,
            "color_offsets": (0x9ef1, 0x9f17, 0x9f40),
            "band_offsets": (0x9ef3, 0x9f19, 0x9f42),
            "font_color_offset": 0x9f94,
            "types": MATCH_FLAG_TYPES,
        },
        "range_font_defaults": {0: "FLOW.FON", 1: "FLOW.FON", 2: "MICRO4.FON", 3: "MICRO4.FON"},
        "immutable_signature": {
            "header_size": 0x6C90,
            "relocation_table_offset": 0x1C,
            "relocation_count": 6941,
            "relocation_topology_sha256": "802345DB9DD9B8E6C161D36B570BBBE33F4BC14A8753F89F368571DFD6B538BE",
            "entry_cs": 0x3A23,
            "entry_ip": 0x0016,
            "diagnostic_stack_ss": 0x555F,
            "diagnostic_stack_sp": 0x1000,
            "code_anchors": (
                (0x0F5F3, "55 8B EC B8 0A 00 9A C6 02 ?? ?? 2A C0 50 B9 EF 00 51 B9 3F 01 51 B9 2B 00 51 2B C9 51 8E 06 A4"),
                (0x1F657, "55 8B EC B8 68 00 9A C6 02 ?? ?? 57 56 8E 06 24"),
                (0x245A7, "55 8B EC B8 4A 00 9A C6 02 ?? ?? 8E 06 AE 98 26"),
            ),
        },
    },
    "THE MANAGER (FRENCH)": {
        "ds_start": 0x53CB0,
        "base_const": bytes.fromhex("F64C"),
        "ptr_ranges": [
            (0x543AC, 0x54444), (0x55148, 0x55172), (0x55174, 0x55390),
            (0x55394, 0x55460), (0x58348, 0x5847c), (0x584ac, 0x58720),
            (0x58740, 0x58d8c), (0x5cfcc, 0x5d184),
        ],
        "valid_ranges": [(0x5453E, 0x550b4), (0x55468, 0x58347), (0x58720, 0x58740), (0x59452, 0x5cfb1)],
        "code_ptrs":   [(0x2E38B, 0x58720), (0x2E3d2, 0x58730)],
        "fixed_strings": [(0x55460, 8)],
        "code_year": 0x12AC2,
        "region_offset": 0x550B6,
        "points_offset": 0x550d9,
        "subst_gk_offset": 0x23eb0,
        "subst_offset": 0x23eb6,
        "teams": {
            "offset": 0x550c2,
            "number": _1st_LEAGUE_TEAMS,
        },
        "wdl_map": 0x550e2,
        "match_flag": {
            "detect_offset": 0x9fb0,
            "color_offsets": (0x9fb1, 0x9fd7, 0xa000),
            "band_offsets": (0x9fb3, 0x9fd9, 0xa002),
            "font_color_offset": 0xa054,
            "types": MATCH_FLAG_TYPES,
        },
        "range_font_defaults": {0: "FLOW.FON", 1: "FLOW.FON", 2: "MICRO4.FON", 3: "MICRO4.FON"},
        "immutable_signature": {
            "header_size": 0x6D50,
            "relocation_table_offset": 0x1C,
            "relocation_count": 6986,
            "relocation_topology_sha256": [
                "03D7AC04A1F4AA837A0776B701AEA019D955577B937178882D9DF52307D87A75",  # original MZ
                "FB17C5F60EE0F8901A5273E077B53564AD5372D7ACC79E30EE2D5E8A82BA76B3",  # decompressed by EXEPACK
            ],
            "entry_cs": 0x3A45,
            "entry_ip": 0x0018,
            "diagnostic_stack_ss": 0x5772,
            "diagnostic_stack_sp": 0x1000,
            "code_anchors": (
                (0x0F753, "55 8B EC B8 0A 00 9A C8 02 ?? ?? 2A C0 50 B9 EF 00 51 B9 3F 01 51 B9 2B 00 51 2B C9 51 8E 06 FA"),
                (0x1F7B7, "55 8B EC B8 68 00 9A C8 02 ?? ?? 57 56 8E 06 7A"),
                (0x228E0, "55 8B EC B8 0E 00 9A C8 02 ?? ?? 56 C6 46 FA 00"),
            ),
        },
    },
}

EXE_FONT_PROFILES = {
    "BUNDESLIGA MANAGER PROFESSIONAL": {
        "base_addr": 0x3C770,
        "fonts": {
            "NORMAL.FON": {"type": "dynamic", "rows": 16, "ptr_start": 0x3CF64, "ptr_end": 0x3D022, "glyph_start": 0x3D022, "glyph_end": 0x3D5CE, "num_ptrs": 95, "ascii_start": 0x20},
            "FLOW.FON":   {"type": "fixed",   "rows": 8,  "bytes_per_char": 9, "ptr_start": 0x3D930, "ptr_end": 0x3D9EE, "glyph_start": 0x3D9EE, "glyph_end": 0x3DD18, "num_ptrs": 95, "ascii_start": 0x20},
            "MICRO4.FON": {"type": "fixed",   "rows": 6,  "bytes_per_char": 7, "ptr_start": 0x3D5DA, "ptr_end": 0x3D698, "glyph_start": 0x3D698, "glyph_end": 0x3D92A, "num_ptrs": 95, "ascii_start": 0x20},
        },
    },
    "THE MANAGER (ITALIAN)": {
        "base_addr": 0x3CC80,
        "fonts": {
            "NORMAL.FON": {"type": "dynamic", "rows": 16, "ptr_start": 0x3D46E, "ptr_end": 0x3D52C, "glyph_start": 0x3D52C, "glyph_end": 0x3DAD8, "num_ptrs": 95, "ascii_start": 0x20},
            "FLOW.FON":   {"type": "fixed",   "rows": 8,  "bytes_per_char": 9, "ptr_start": 0x3DE43, "ptr_end": 0x3DF01, "glyph_start": 0x3DF01, "glyph_end": 0x3E22B, "num_ptrs": 95, "ascii_start": 0x20},
            "MICRO4.FON": {"type": "fixed",   "rows": 6,  "bytes_per_char": 7, "ptr_start": 0x3DAE4, "ptr_end": 0x3DBA4, "glyph_start": 0x3DBA4, "glyph_end": 0x3DE3D, "num_ptrs": 96, "ascii_start": 0x20},
        },
    },
    "THE MANAGER (ENGLISH)": {
        "base_addr": 0x3CA30,
        "fonts": {
            "NORMAL.FON": {"type": "dynamic", "rows": 16, "ptr_start": 0x3D102, "ptr_end": 0x3D1C0, "glyph_start": 0x3D1C0, "glyph_end": 0x3D77D, "num_ptrs": 95, "ascii_start": 0x20},
            "FLOW.FON":   {"type": "fixed",   "rows": 8,  "bytes_per_char": 9, "ptr_start": 0x3DB2B, "ptr_end": 0x3DBE9, "glyph_start": 0x3DBEB, "glyph_end": 0x3DF15, "num_ptrs": 95, "ascii_start": 0x20},
            "MICRO4.FON": {"type": "fixed",   "rows": 6,  "bytes_per_char": 7, "ptr_start": 0x3D789, "ptr_end": 0x3D849, "glyph_start": 0x3D85B, "glyph_end": 0x3DAF4, "num_ptrs": 96, "ascii_start": 0x20},
        },
    },
    "THE MANAGER (FRENCH)": {
        "base_addr": 0x3Cc50,
        "fonts": {
            "NORMAL.FON": {"type": "dynamic", "rows": 16, "ptr_start": 0x3D43e, "ptr_end": 0x3D4fc, "glyph_start": 0x3D4fc, "glyph_end": 0x3Daa8, "num_ptrs": 95, "ascii_start": 0x20},
            "FLOW.FON":   {"type": "fixed",   "rows": 8,  "bytes_per_char": 9, "ptr_start": 0x3De13, "ptr_end": 0x3Ded1, "glyph_start": 0x3Ded1, "glyph_end": 0x3e1fb, "num_ptrs": 95, "ascii_start": 0x20},
            "MICRO4.FON": {"type": "fixed",   "rows": 6,  "bytes_per_char": 7, "ptr_start": 0x3Dab4, "ptr_end": 0x3Db74, "glyph_start": 0x3Db74, "glyph_end": 0x3De0d, "num_ptrs": 96, "ascii_start": 0x20},
        },
    },
}



def read_u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]

def write_u16(buf, offset, value):
    struct.pack_into("<H", buf, offset, value)

def find_exepack_vars(data):
    header_para = read_u16(data, 0x08)
    init_CS     = read_u16(data, 0x16)
    stub_file   = header_para * 16 + init_CS * 16

    for sig_off in (0x10, 0x0e):
        vs = stub_file
        if vs + sig_off + 2 <= len(data) and data[vs + sig_off:vs + sig_off + 2] == b'RB':
            return vs, sig_off

    pos = data.find(b'RB')
    while pos != -1:
        for sig_off in (0x10, 0x0e):
            vs = pos - sig_off
            if vs < header_para * 16 or vs + sig_off + 2 > len(data):
                continue
            exepack_size = read_u16(data, vs + 0x06)
            dest_len     = read_u16(data, vs + 0x0c)
            stub_fixed   = sig_off + 2 + 0x105 + 0x16
            if exepack_size > stub_fixed and 0 < dest_len < 0xFFFF:
                return vs, sig_off
        pos = data.find(b'RB', pos + 1)

    raise ValueError("EXEPACK signature 'RB' not found")


def decompress_exepack(packed, unpacked_size):
    out = bytearray(unpacked_size)
    src = len(packed) - 1
    dst = unpacked_size - 1

    while src >= 0 and packed[src] == 0xFF:
        src -= 1

    while src >= 0:
        cmd = packed[src]; src -= 1
        op      = cmd & 0xFE
        is_last = cmd & 0x01

        if op == 0xB0:
            if src < 2:
                raise ValueError(f"FILL block truncated at src={src+1:#x}")
            length = packed[src] * 0x100 + packed[src - 1]; src -= 2
            fill   = packed[src]; src -= 1
            if dst - length + 1 < 0:
                raise ValueError(f"FILL block overflows output buffer (dst={dst}, length={length})")
            for _ in range(length):
                out[dst] = fill; dst -= 1
        elif op == 0xB2:
            if src < 2:
                raise ValueError(f"COPY block truncated at src={src+1:#x}")
            length = packed[src] * 0x100 + packed[src - 1]; src -= 2
            if dst - length + 1 < 0:
                raise ValueError(f"COPY block overflows output buffer (dst={dst}, length={length})")
            if src - length + 1 < 0:
                raise ValueError(f"COPY block reads past start of packed data (src={src}, length={length})")
            for _ in range(length):
                out[dst] = packed[src]; dst -= 1; src -= 1
        else:
            raise ValueError(f"Unknown EXEPACK command {cmd:#04x} at packed[{src+1:#x}]")

        if is_last:
            break

    return out, dst

def decode_reloc_table(reloc_data):
    entries, pos = [], 0
    for section in range(16):
        if pos + 2 > len(reloc_data):
            break
        count = struct.unpack_from("<H", reloc_data, pos)[0]; pos += 2
        count = min(count, (len(reloc_data) - pos) // 2)
        for _ in range(count):
            offset = struct.unpack_from("<H", reloc_data, pos)[0]; pos += 2
            entries.append((0x1000 * section, offset))
    return entries

def build_mz_exe(unpacked_image, reloc_entries, real_CS, real_IP, real_SS, real_SP, min_alloc, max_alloc):
    reloc_count = len(reloc_entries)
    header_para = ((0x1C + reloc_count * 4) + 15) // 16
    header_size = header_para * 16
    total_size  = header_size + len(unpacked_image)

    out = bytearray(total_size)
    out[0:2] = b'MZ'
    for off, val in [
        (0x02, total_size % 512), (0x04, (total_size + 511) // 512),
        (0x06, reloc_count),      (0x08, header_para),
        (0x0A, min_alloc),        (0x0C, max_alloc),
        (0x0E, real_SS),          (0x10, real_SP),
        (0x12, 0),                (0x14, real_IP),
        (0x16, real_CS),          (0x18, 0x1C),
        (0x1A, 0),
    ]:
        write_u16(out, off, val)

    rpos = 0x1C
    for seg, off in reloc_entries:
        write_u16(out, rpos, off); rpos += 2
        write_u16(out, rpos, seg); rpos += 2

    out[header_size:header_size + len(unpacked_image)] = unpacked_image
    return out

def unpack_in_memory(data: bytearray) -> bytearray:
    if data[0:2] != b'MZ':
        return data
    try:
        vars_start, sig_offset = find_exepack_vars(data)
    except ValueError:
        return data
    try:
        real_IP      = read_u16(data, vars_start + 0x00)
        real_CS      = read_u16(data, vars_start + 0x02)
        exepack_size = read_u16(data, vars_start + 0x06)
        real_SP      = read_u16(data, vars_start + 0x08)
        real_SS      = read_u16(data, vars_start + 0x0A)
        dest_len     = read_u16(data, vars_start + 0x0C)
        min_alloc    = read_u16(data, 0x0A)
        max_alloc    = read_u16(data, 0x0C)

        ERROR_STRING    = b'Packed file is corrupt'
        stub_code_start = vars_start + sig_offset + 2
        err_pos = data.find(ERROR_STRING, stub_code_start, min(stub_code_start + 0x200, len(data)))

        if err_pos == -1:
            reloc_start = vars_start + (sig_offset + 2) + 0x105 + 0x16
        else:
            reloc_start = err_pos + len(ERROR_STRING)

        reloc_end  = vars_start + exepack_size
        if reloc_end > len(data) or reloc_end <= reloc_start:
            reloc_end = len(data)
        reloc_data = data[reloc_start:reloc_end]

        packed        = data[read_u16(data, 0x08) * 16:vars_start]
        unpacked_size = dest_len * 16

        decompressed_top, dst_stop = decompress_exepack(packed, unpacked_size)

        unpacked_image = bytearray(unpacked_size)
        prefix_end = dst_stop + 1
        unpacked_image[:prefix_end] = packed[:prefix_end]
        unpacked_image[prefix_end:] = decompressed_top[prefix_end:]

        reloc_entries = [(s, o) for s, o in decode_reloc_table(reloc_data) if s or o]

        result = build_mz_exe(unpacked_image, reloc_entries, real_CS, real_IP, real_SS, real_SP, min_alloc, max_alloc)
        if len(result) <= len(data):
            return data
        get_mz_relocation_sites(result)
        return result
    except Exception:
        return data


def get_mz_relocation_sites(data) -> list[int]:
    if len(data) < 0x1C or data[0:2] != b'MZ':
        raise ValueError("MZ header not found")

    reloc_count = read_u16(data, 0x06)
    header_size = read_u16(data, 0x08) * 16
    reloc_start = read_u16(data, 0x18)
    reloc_end = reloc_start + reloc_count * 4

    if header_size < 0x1C or header_size > len(data):
        raise ValueError("Invalid MZ header size")
    if reloc_start < 0x1C or reloc_end > header_size or reloc_end > len(data):
        raise ValueError("Invalid MZ relocation table")

    sites = set()
    for pos in range(reloc_start, reloc_end, 4):
        offset, segment = struct.unpack_from("<HH", data, pos)
        site = header_size + segment * 16 + offset
        if site < header_size or site + 2 > len(data):
            raise ValueError(f"MZ relocation site outside image: {site:#x}")
        sites.add(site)
    return sorted(sites)


def _canonical_mz_relocation_topology(data):
    if len(data) < 0x1C or bytes(data[:2]) != b"MZ":
        raise ValueError("Not a complete MZ image")
    header_size = int.from_bytes(data[0x08:0x0A], "little") * 16
    relocation_count = int.from_bytes(data[0x06:0x08], "little")
    relocation_offset = int.from_bytes(data[0x18:0x1A], "little")
    relocation_end = relocation_offset + relocation_count * 4
    if (
        header_size < 0x1C
        or header_size > len(data)
        or relocation_offset < 0x1C
        or relocation_end > header_size
    ):
        raise ValueError("Invalid MZ relocation table layout")

    pairs = []
    for pos in range(relocation_offset, relocation_end, 4):
        offset = int.from_bytes(data[pos:pos + 2], "little")
        segment = int.from_bytes(data[pos + 2:pos + 4], "little")
        site = header_size + segment * 16 + offset
        if site < header_size or site + 2 > len(data):
            raise ValueError("MZ relocation source outside image")
        pairs.append((segment, offset))

    canonical = b"".join(
        segment.to_bytes(2, "little") + offset.to_bytes(2, "little")
        for segment, offset in sorted(pairs)
    )
    return {
        "header_size": header_size,
        "relocation_count": relocation_count,
        "relocation_offset": relocation_offset,
        "sha256": hashlib.sha256(canonical).hexdigest().upper(),
    }


def _match_immutable_code_anchor(data, header_size, anchor):
    image_offset, pattern_text = anchor
    tokens = pattern_text.split()
    wildcard_offsets = tuple(i for i, token in enumerate(tokens) if token == "??")
    if wildcard_offsets != (9, 10):
        return False
    try:
        expected = tuple(None if token == "??" else int(token, 16) for token in tokens)
    except ValueError:
        return False
    if any(value is not None and not 0 <= value <= 0xFF for value in expected):
        return False
    start = header_size + image_offset
    end = start + len(expected)
    if start < header_size or end > len(data):
        return False
    return all(value is None or data[start + index] == value for index, value in enumerate(expected))


def _matches_immutable_profile(data, profile_name, profile, verbose=False, collect=False):
    lines = []
    def emit(msg):
        if collect:
            lines.append(msg)
        elif verbose:
            print(msg)
    pname = profile_name
    signature = profile.get("immutable_signature")
    if not signature:
        emit(f"[detect:{pname}] FAIL: no immutable_signature")
        return (False, lines) if collect else False
    anchors = signature.get("code_anchors", ())
    if len(anchors) != 3:
        emit(f"[detect:{pname}] FAIL: expected 3 anchors, got {len(anchors)}")
        return (False, lines) if collect else False
    try:
        topology = _canonical_mz_relocation_topology(data)
    except (TypeError, ValueError) as exc:
        emit(f"[detect:{pname}] FAIL: _canonical_mz_relocation_topology raised {exc}")
        return (False, lines) if collect else False
    expected_sha = signature["relocation_topology_sha256"]
    sha_ok = (topology["sha256"] == expected_sha) if isinstance(expected_sha, str) \
             else (topology["sha256"] in expected_sha)
    checks = [
        ("header_size",       topology["header_size"],       signature["header_size"]),
        ("relocation_offset", topology["relocation_offset"], signature["relocation_table_offset"]),
        ("relocation_count",  topology["relocation_count"],  signature["relocation_count"]),
        ("reloc_sha256",      sha_ok,                        True),
        ("entry_cs (0x16)",   int.from_bytes(data[0x16:0x18], "little"), signature["entry_cs"]),
        ("entry_ip (0x14)",   int.from_bytes(data[0x14:0x16], "little"), signature["entry_ip"]),
    ]
    failed = False
    for name, got, expected in checks:
        ok = got == expected
        if name == "reloc_sha256":
            if ok:
                status = f"ok  ({topology['sha256']})"
            else:
                expected_list = [expected_sha] if isinstance(expected_sha, str) else list(expected_sha)
                status = f"FAIL  got={topology['sha256']}  expected={expected_list}"
        else:
            got_s      = got      if isinstance(got, str)  else hex(got)
            expected_s = expected if isinstance(expected, str) else hex(expected)
            status = "ok" if ok else f"FAIL  got={got_s}  expected={expected_s}"
        emit(f"[detect:{pname}]   {name}: {status}")
        if not ok:
            failed = True
    if failed:
        return (False, lines) if collect else False
    for i, anchor in enumerate(anchors):
        ok = _match_immutable_code_anchor(data, topology["header_size"], anchor)
        img_off  = anchor[0]
        file_off = topology["header_size"] + img_off
        status   = "ok" if ok else f"FAIL  file_offset={hex(file_off)}  img_offset={hex(img_off)}"
        emit(f"[detect:{pname}]   anchor[{i}] @ img {hex(img_off)}: {status}")
        if not ok:
            return (False, lines) if collect else False
    emit(f"[detect:{pname}] MATCH")
    return (True, lines) if collect else True


def detect_game_profile(data, profiles):
    header = f"[detect_profile] file size={hex(len(data))}, MZ={bytes(data[:2]) if len(data) >= 2 else '?'}"
    all_logs = [header]
    matches = []
    for name, profile in profiles.items():
        all_logs.append(f"[detect_profile] --- testing profile: {name} ---")
        matched, lines = _matches_immutable_profile(data, name, profile, collect=True)
        all_logs.extend(lines)
        if matched:
            matches.append(name)
    result = matches[0] if len(matches) == 1 else None
    if result is not None:
        print(f"[detect_profile] detected={result}")
    else:
        for line in all_logs:
            print(line)
        print(f"[detect_profile] result=None  (all matches={matches})")
    return result


__all__ = [
    'unpack_in_memory',
    'get_mz_relocation_sites',
    'detect_game_profile',
    'GAME_PROFILES',
    'EXE_FONT_PROFILES',
]
