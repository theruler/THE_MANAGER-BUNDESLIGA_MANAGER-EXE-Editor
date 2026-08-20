from __future__ import annotations

import copy
import os
import struct
import tempfile
from pathlib import Path

from i18n import tr


class FontSafetyError(ValueError):
    pass


def bytes_per_row_for_width(width: int) -> int:
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise FontSafetyError(tr("fsafe.err.invalid_width", width=width))
    return (width + 7) // 8


def _font_description(game_profile: dict, font_key: str) -> dict:
    try:
        return game_profile["fonts"][font_key]
    except (KeyError, TypeError) as exc:
        raise FontSafetyError(tr("fsafe.err.unknown_font", font=font_key)) from exc


def unique_glyphs(font_data: list[dict]) -> list[dict]:
    result, seen = [], set()
    for char in font_data:
        glyph = char["glyph"]
        off   = glyph["glyph_off"]
        if off not in seen:
            seen.add(off)
            result.append(glyph)
    return result


def _validate_description(data: bytes | bytearray, game_profile: dict, font_key: str):
    desc = _font_description(game_profile, font_key)
    try:
        ptr_start   = int(desc["ptr_start"])
        ptr_end     = int(desc["ptr_end"])
        glyph_start = int(desc["glyph_start"])
        glyph_end   = int(desc["glyph_end"])
        num_ptrs    = int(desc["num_ptrs"])
        rows        = int(desc["rows"])
        base        = int(game_profile["base_addr"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FontSafetyError(tr("fsafe.err.incomplete_desc", font=font_key)) from exc

    if desc.get("type") not in {"dynamic", "fixed"}:
        raise FontSafetyError(tr("fsafe.err.unsupported_type", font=font_key))
    if rows <= 0 or num_ptrs <= 0:
        raise FontSafetyError(tr("fsafe.err.invalid_row_count", font=font_key))
    if not (0 <= ptr_start <= ptr_end <= len(data)):
        raise FontSafetyError(tr("fsafe.err.ptr_table_outside", font=font_key))
    if ptr_end - ptr_start != num_ptrs * 2:
        raise FontSafetyError(tr("fsafe.err.ptr_table_size",
                                 font=font_key, got=ptr_end - ptr_start, ptrs=num_ptrs))
    if not (ptr_end <= glyph_start < glyph_end <= len(data)):
        raise FontSafetyError(tr("fsafe.err.glyph_range", font=font_key))
    return desc, base, ptr_start, glyph_start, glyph_end, num_ptrs, rows


def load_font_model(data: bytes | bytearray, game_profile: dict, font_key: str) -> list[dict]:
    desc, base, ptr_start, glyph_start, glyph_end, num_ptrs, rows = _validate_description(
        data, game_profile, font_key)
    glyph_offsets = []
    for index in range(num_ptrs):
        source   = ptr_start + index * 2
        relative = struct.unpack_from("<H", data, source)[0]
        off      = base + relative
        if not glyph_start <= off < glyph_end:
            raise FontSafetyError(tr("fsafe.err.ptr_target",
                                     idx=index, font=font_key, addr=off,
                                     start=glyph_start, end=glyph_end))
        glyph_offsets.append(off)

    sorted_unique = sorted(set(glyph_offsets))
    if not sorted_unique or sorted_unique[0] != glyph_start:
        raise FontSafetyError(tr("fsafe.err.first_glyph", font=font_key))

    glyph_by_offset = {}
    for index, off in enumerate(sorted_unique):
        slot_end  = sorted_unique[index + 1] if index + 1 < len(sorted_unique) else glyph_end
        slot_size = slot_end - off
        if slot_size <= 1:
            raise FontSafetyError(tr("fsafe.err.slot_invalid", addr=off, font=font_key))

        width = int(data[off])
        if desc["type"] == "dynamic":
            if (slot_size - 1) % rows:
                raise FontSafetyError(tr("fsafe.err.dynamic_uneven", addr=off))
            capacity_bpr = (slot_size - 1) // rows
            if capacity_bpr not in (1, 2, 3):
                raise FontSafetyError(tr("fsafe.err.dynamic_capacity", addr=off, cap=capacity_bpr))
            max_width = capacity_bpr * 8
            if not 1 <= width <= max_width:
                raise FontSafetyError(tr("fsafe.err.width_exceeds_slot",
                                         width=width, addr=off, max=max_width))
            bpr = bytes_per_row_for_width(width)
        else:
            expected_size = int(desc.get("bytes_per_char", rows + 1))
            if expected_size != rows + 1 or slot_size != expected_size:
                raise FontSafetyError(tr("fsafe.err.fixed_size",
                                         addr=off, got=slot_size, expected=expected_size))
            capacity_bpr, max_width = 1, 8
            if not 1 <= width <= 8:
                raise FontSafetyError(tr("fsafe.err.fixed_width", width=width, addr=off))
            bpr = 1

        required = 1 + rows * bpr
        if off + required > slot_end or off + required > len(data):
            raise FontSafetyError(tr("fsafe.err.glyph_exceeds_slot", addr=off))
        bitmap = [
            int.from_bytes(data[off + 1 + row * bpr:off + 1 + (row + 1) * bpr], "big")
            for row in range(rows)
        ]
        glyph_by_offset[off] = {
            "glyph_off": off, "slot_end": slot_end, "slot_size": slot_size,
            "capacity_bpr": capacity_bpr, "max_width": max_width,
            "width": width, "bytes_per_row": bpr, "bitmap": bitmap,
        }

    first_occurrence, font_data = {}, []
    ascii_start = int(desc["ascii_start"])
    for index, off in enumerate(glyph_offsets):
        first = first_occurrence.setdefault(off, index)
        font_data.append({"ascii": ascii_start + index,
                           "alias_of": None if first == index else first,
                           "glyph": glyph_by_offset[off]})
    validate_font_model(font_data, desc, len(data))
    return font_data


def validate_font_model(font_data: list[dict], desc: dict, data_length: int | None = None) -> dict:
    if len(font_data) != int(desc["num_ptrs"]):
        raise FontSafetyError(tr("fsafe.err.model_char_count",
                                 got=len(font_data), expected=desc["num_ptrs"]))
    rows = int(desc["rows"])
    first_by_offset, object_by_offset, offsets = {}, {}, []
    ascii_start = int(desc["ascii_start"])

    for index, char in enumerate(font_data):
        if char.get("ascii") != ascii_start + index:
            raise FontSafetyError(tr("fsafe.err.invalid_char_idx", idx=index))
        glyph = char.get("glyph")
        if not isinstance(glyph, dict):
            raise FontSafetyError(tr("fsafe.err.no_glyph_obj", idx=index))
        off = glyph.get("glyph_off")
        if not isinstance(off, int):
            raise FontSafetyError(tr("fsafe.err.invalid_glyph_off", idx=index))
        if off in object_by_offset and object_by_offset[off] is not glyph:
            raise FontSafetyError(tr("fsafe.err.alias_not_shared", addr=off))
        object_by_offset.setdefault(off, glyph)
        first = first_by_offset.setdefault(off, index)
        if char.get("alias_of") != (None if first == index else first):
            raise FontSafetyError(tr("fsafe.err.alias_meta", idx=index))
        offsets.append(off)

    unique_offsets = sorted(set(offsets))
    if not unique_offsets or unique_offsets[0] != int(desc["glyph_start"]):
        raise FontSafetyError(tr("fsafe.err.glyph_start"))
    for index, off in enumerate(unique_offsets):
        glyph        = object_by_offset[off]
        expected_end = (unique_offsets[index + 1] if index + 1 < len(unique_offsets)
                        else int(desc["glyph_end"]))
        if glyph.get("slot_end") != expected_end or glyph.get("slot_size") != expected_end - off:
            raise FontSafetyError(tr("fsafe.err.slot_boundary", addr=off))
        if data_length is not None and not (0 <= off < expected_end <= data_length):
            raise FontSafetyError(tr("fsafe.err.slot_outside_exe", addr=off))
        width  = glyph.get("width")
        bpr    = glyph.get("bytes_per_row")
        bitmap = glyph.get("bitmap")
        if not isinstance(width, int) or isinstance(width, bool):
            raise FontSafetyError(tr("fsafe.err.dynamic_cap_meta", addr=off))
        if not isinstance(bitmap, list) or len(bitmap) != rows:
            raise FontSafetyError(tr("fsafe.err.dynamic_cap_meta", addr=off))

        if desc["type"] == "dynamic":
            capacity_bpr = (expected_end - off - 1) // rows
            if 1 + rows * capacity_bpr != expected_end - off or capacity_bpr not in (1, 2, 3):
                raise FontSafetyError(tr("fsafe.err.dynamic_cap_meta", addr=off))
            if glyph.get("capacity_bpr") != capacity_bpr or glyph.get("max_width") != capacity_bpr * 8:
                raise FontSafetyError(tr("fsafe.err.dynamic_cap_stored", addr=off))
            expected_bpr = bytes_per_row_for_width(width)
            if not 1 <= width <= capacity_bpr * 8 or bpr != expected_bpr:
                raise FontSafetyError(tr("fsafe.err.dynamic_width_bpr", addr=off))
        else:
            expected_size = int(desc.get("bytes_per_char", rows + 1))
            if expected_end - off != expected_size or expected_size != rows + 1:
                raise FontSafetyError(tr("fsafe.err.fixed_slot", addr=off))
            if glyph.get("capacity_bpr") != 1 or glyph.get("max_width") != 8:
                raise FontSafetyError(tr("fsafe.err.fixed_cap_stored", addr=off))
            if not 1 <= width <= 8 or bpr != 1:
                raise FontSafetyError(tr("fsafe.err.fixed_width_bpr", addr=off))

        limit = 1 << (8 * bpr)
        if any(not isinstance(v, int) or isinstance(v, bool) or not 0 <= v < limit for v in bitmap):
            raise FontSafetyError(tr("fsafe.err.bitmap_value", addr=off))
        if 1 + rows * bpr > expected_end - off:
            raise FontSafetyError(tr("fsafe.err.serial_exceeds", addr=off))

    return {
        "pointer_count": len(font_data),
        "unique_count":  len(unique_offsets),
        "alias_count":   len(font_data) - len(unique_offsets),
        "slot_sizes":    [object_by_offset[off]["slot_size"] for off in unique_offsets],
    }


def validate_all_fonts(data: bytes | bytearray, game_profile: dict) -> dict[str, dict]:
    result = {}
    for font_key in game_profile.get("fonts", {}):
        model = load_font_model(data, game_profile, font_key)
        result[font_key] = validate_font_model(model, game_profile["fonts"][font_key], len(data))
    return result


def clone_font_model(font_data: list[dict]) -> list[dict]:
    return copy.deepcopy(font_data)


def _convert_rows_left_aligned(bitmap: list[int], old_bpr: int, new_bpr: int) -> list[int]:
    if old_bpr not in (1, 2, 3) or new_bpr not in (1, 2, 3):
        raise FontSafetyError(tr("fsafe.err.bpr_conversion"))
    shift = 8 * abs(new_bpr - old_bpr)
    converted = ([v << shift for v in bitmap] if new_bpr > old_bpr
                 else [v >> shift for v in bitmap] if new_bpr < old_bpr
                 else list(bitmap))
    mask = (1 << (8 * new_bpr)) - 1
    return [v & mask for v in converted]


def change_glyph_width(glyph: dict, desc: dict, new_width: int) -> None:
    if not isinstance(new_width, int) or isinstance(new_width, bool):
        raise FontSafetyError(tr("fsafe.err.width_not_int"))
    old_bpr = int(glyph["bytes_per_row"])
    if desc["type"] == "dynamic":
        max_width = int(glyph["max_width"])
        if not 1 <= new_width <= max_width:
            raise FontSafetyError(tr("fsafe.err.width_exceeds_max", width=new_width, max=max_width))
        new_bpr = bytes_per_row_for_width(new_width)
    else:
        if not 1 <= new_width <= 8:
            raise FontSafetyError(tr("fsafe.err.fixed_width_range"))
        new_bpr = 1
    glyph["width"]         = new_width
    glyph["bytes_per_row"] = new_bpr
    glyph["bitmap"]        = _convert_rows_left_aligned(glyph["bitmap"], old_bpr, new_bpr)


def copy_glyph_payload(glyph: dict, desc: dict) -> dict:
    return {"font_type": desc["type"], "rows": int(desc["rows"]),
            "width": int(glyph["width"]), "bytes_per_row": int(glyph["bytes_per_row"]),
            "bitmap": list(glyph["bitmap"])}


def paste_glyph_payload(glyph: dict, target_desc: dict, payload: dict) -> None:
    try:
        source_type   = payload["font_type"]
        source_rows   = int(payload["rows"])
        source_bpr    = int(payload["bytes_per_row"])
        source_width  = int(payload["width"])
        source_bitmap = list(payload["bitmap"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FontSafetyError(tr("fsafe.err.clipboard_invalid")) from exc

    target_rows = int(target_desc["rows"])
    if source_rows != target_rows or len(source_bitmap) != target_rows:
        raise FontSafetyError(tr("fsafe.err.height_mismatch", src=source_rows, tgt=target_rows))
    if source_type not in {"dynamic", "fixed"}:
        raise FontSafetyError(tr("fsafe.err.clip_type_invalid"))
    expected_source_bpr = bytes_per_row_for_width(source_width) if source_type == "dynamic" else 1
    if source_bpr not in (1, 2, 3) or source_bpr != expected_source_bpr:
        raise FontSafetyError(tr("fsafe.err.clip_bpr_invalid"))
    if source_type == "fixed" and not 1 <= source_width <= 8:
        raise FontSafetyError(tr("fsafe.err.clip_fixed_width"))
    if any(not isinstance(v, int) or v < 0 or v >= 1 << (8 * source_bpr) for v in source_bitmap):
        raise FontSafetyError(tr("fsafe.err.clip_bitmap"))

    if target_desc["type"] == "fixed":
        if not 1 <= source_width <= 8:
            raise FontSafetyError(tr("fsafe.err.target_too_wide"))
        target_bpr = 1
    else:
        max_width = int(glyph["max_width"])
        if not 1 <= source_width <= max_width:
            raise FontSafetyError(tr("fsafe.err.paste_exceeds_slot",
                                     width=source_width, max=max_width))
        target_bpr = bytes_per_row_for_width(source_width)

    glyph["width"]         = source_width
    glyph["bytes_per_row"] = target_bpr
    glyph["bitmap"]        = _convert_rows_left_aligned(source_bitmap, source_bpr, target_bpr)


def _write_glyph(buf: bytearray, glyph: dict, desc: dict) -> None:
    off          = int(glyph["glyph_off"])
    rows         = int(desc["rows"])
    bpr          = int(glyph["bytes_per_row"])
    required_end = off + 1 + rows * bpr
    if required_end > int(glyph["slot_end"]) or required_end > len(buf):
        raise FontSafetyError(tr("fsafe.err.write_exceeds", addr=off))
    buf[off] = int(glyph["width"])
    for row, value in enumerate(glyph["bitmap"]):
        row_start = off + 1 + row * bpr
        buf[row_start:row_start + bpr] = int(value).to_bytes(bpr, "big")


def stage_font_apply(
    data: bytes | bytearray,
    font_data: list[dict],
    game_profile: dict,
    font_key: str,
) -> tuple[bytearray, dict]:
    desc       = _font_description(game_profile, font_key)
    base_model = load_font_model(data, game_profile, font_key)
    validate_font_model(font_data, desc, len(data))
    for current, base in zip(font_data, base_model):
        cg, bg = current["glyph"], base["glyph"]
        if (cg["glyph_off"] != bg["glyph_off"] or cg["slot_end"] != bg["slot_end"]
                or current["alias_of"] != base["alias_of"]):
            raise FontSafetyError(tr("fsafe.err.ptr_alias_struct"))

    work = bytearray(data)
    for glyph in unique_glyphs(font_data):
        _write_glyph(work, glyph, desc)

    changed_offsets = [i for i, (a, b) in enumerate(zip(data, work)) if a != b]
    allowed = set()
    for glyph in unique_glyphs(font_data):
        allowed.update(range(glyph["glyph_off"], glyph["slot_end"]))
    if any(i not in allowed for i in changed_offsets):
        raise FontSafetyError(tr("fsafe.err.changed_outside"))

    readback        = load_font_model(work, game_profile, font_key)
    expected_by_off = {g["glyph_off"]: g for g in unique_glyphs(font_data)}
    for glyph in unique_glyphs(readback):
        expected = expected_by_off[glyph["glyph_off"]]
        if (glyph["width"] != expected["width"]
                or glyph["bytes_per_row"] != expected["bytes_per_row"]
                or glyph["bitmap"] != expected["bitmap"]):
            raise FontSafetyError(tr("fsafe.err.readback_mismatch", addr=glyph["glyph_off"]))
    return work, {"unique_count": len(expected_by_off), "changed_offsets": changed_offsets}


def export_font_bytes(font_data: list[dict], desc: dict) -> bytes:
    validate_font_model(font_data, desc)
    out = bytearray()
    for glyph in unique_glyphs(font_data):
        out.append(glyph["width"])
        bpr = glyph["bytes_per_row"]
        for value in glyph["bitmap"]:
            out.extend(int(value).to_bytes(bpr, "big"))
    return bytes(out)


def import_font_bytes(raw: bytes | bytearray, font_data: list[dict], desc: dict) -> list[dict]:
    staged = clone_font_model(font_data)
    glyphs = unique_glyphs(staged)
    rows   = int(desc["rows"])
    pos    = 0
    for index, glyph in enumerate(glyphs):
        if pos >= len(raw):
            raise FontSafetyError(tr("fsafe.err.import_truncated", idx=index))
        width = int(raw[pos]); pos += 1
        if desc["type"] == "dynamic":
            if not 1 <= width <= int(glyph["max_width"]):
                raise FontSafetyError(tr("fsafe.err.import_width",
                                         width=width, idx=index, cap=glyph["max_width"]))
            bpr = bytes_per_row_for_width(width)
        else:
            if not 1 <= width <= 8:
                raise FontSafetyError(tr("fsafe.err.import_fixed_width", width=width, idx=index))
            bpr = 1
        needed = rows * bpr
        if pos + needed > len(raw):
            raise FontSafetyError(tr("fsafe.err.import_trunc_body", idx=index))
        bitmap = [int.from_bytes(raw[pos + r * bpr:pos + (r + 1) * bpr], "big") for r in range(rows)]
        pos += needed
        glyph["width"] = width; glyph["bytes_per_row"] = bpr; glyph["bitmap"] = bitmap
    if pos != len(raw):
        raise FontSafetyError(tr("fsafe.err.import_trailing", n=len(raw) - pos))
    validate_font_model(staged, desc)
    return staged


def _normalised_path(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


def paths_equal(left, right) -> bool:
    return bool(left and right and _normalised_path(left) == _normalised_path(right))


def _atomic_replace_bytes(target: Path, payload: bytes) -> None:
    directory = target.parent
    if not directory.is_dir():
        raise OSError(tr("fsafe.err.no_dir", dir=directory))
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "wb") as handle:
            written = handle.write(payload)
            if written != len(payload):
                raise OSError(tr("fsafe.err.short_write", written=written, total=len(payload)))
            handle.flush()
            os.fsync(handle.fileno())
        if Path(temp_name).read_bytes() != payload:
            raise OSError(tr("fsafe.err.readback_tmp"))
        os.replace(temp_name, target)
    finally:
        try:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
        except OSError:
            pass


def _next_backup_path(target: Path) -> Path:
    candidate = target.with_name(target.name + ".bak")
    suffix = 1
    while candidate.exists():
        candidate = target.with_name(f"{target.name}.bak.{suffix}")
        suffix += 1
    return candidate


def atomic_save_bytes(
    target_path: str | os.PathLike[str],
    payload: bytes | bytearray,
    *,
    backup_original: bool = False,
) -> str | None:
    target, payload_bytes, backup_path = Path(target_path), bytes(payload), None
    if backup_original:
        if not target.is_file():
            raise OSError(tr("fsafe.err.no_backup_src"))
        backup_path = _next_backup_path(target)
        _atomic_replace_bytes(backup_path, target.read_bytes())
    _atomic_replace_bytes(target, payload_bytes)
    return str(backup_path) if backup_path is not None else None


__all__ = [
    "FontSafetyError", "atomic_save_bytes", "bytes_per_row_for_width",
    "change_glyph_width", "clone_font_model", "copy_glyph_payload",
    "export_font_bytes", "import_font_bytes", "load_font_model",
    "paste_glyph_payload", "paths_equal", "stage_font_apply",
    "unique_glyphs", "validate_all_fonts", "validate_font_model",
]
