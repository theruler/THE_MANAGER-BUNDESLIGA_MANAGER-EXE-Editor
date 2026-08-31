import struct

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
    """Return file offsets of all valid MZ relocation words."""
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

GAME_PROFILES = {
    "THE MANAGER": {
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
        "range_font_defaults": {0: "FLOW.FON", 1: "FLOW.FON", 2: "MICRO4.FON", 3: "MICRO4.FON"},
        "immutable_signature": {
            "header_size": 0x6D80,
            "relocation_table_offset": 0x1C,
            "relocation_count": 7000,
            "relocation_topology_sha256": "95235ED9EEB658148E86843DC0381D846BB8FFD91C0515850EE23D590588ED15",
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
    "THE MANAGER": {
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
}

__all__ = ['unpack_in_memory', 'get_mz_relocation_sites', 'GAME_PROFILES', 'EXE_FONT_PROFILES']
