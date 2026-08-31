"""Fail-closed font model and atomic-save helpers for the EXE editor."""

from __future__ import annotations

import copy
import os
import struct
import tempfile
from pathlib import Path


class FontSafetyError(ValueError):
    """Raised before live data is touched when a font operation is unsafe."""


def bytes_per_row_for_width(width: int) -> int:
    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        raise FontSafetyError(f"Invalid glyph width: {width!r}")
    return (width + 7) // 8


def _font_description(game_profile: dict, font_key: str) -> dict:
    try:
        return game_profile["fonts"][font_key]
    except (KeyError, TypeError) as exc:
        raise FontSafetyError(f"Unknown font: {font_key}") from exc


def unique_glyphs(font_data: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for char in font_data:
        glyph = char["glyph"]
        off = glyph["glyph_off"]
        if off not in seen:
            seen.add(off)
            result.append(glyph)
    return result


def _validate_description(data: bytes | bytearray, game_profile: dict, font_key: str):
    desc = _font_description(game_profile, font_key)
    try:
        ptr_start = int(desc["ptr_start"])
        ptr_end = int(desc["ptr_end"])
        glyph_start = int(desc["glyph_start"])
        glyph_end = int(desc["glyph_end"])
        num_ptrs = int(desc["num_ptrs"])
        rows = int(desc["rows"])
        base = int(game_profile["base_addr"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FontSafetyError(f"Incomplete font description for {font_key}") from exc

    if desc.get("type") not in {"dynamic", "fixed"}:
        raise FontSafetyError(f"Unsupported font type for {font_key}")
    if rows <= 0 or num_ptrs <= 0:
        raise FontSafetyError(f"Invalid row/pointer count for {font_key}")
    if not (0 <= ptr_start <= ptr_end <= len(data)):
        raise FontSafetyError(f"Pointer table outside EXE for {font_key}")
    if ptr_end - ptr_start != num_ptrs * 2:
        raise FontSafetyError(
            f"Pointer table size mismatch for {font_key}: "
            f"{ptr_end - ptr_start} bytes for {num_ptrs} pointers"
        )
    if not (ptr_end <= glyph_start < glyph_end <= len(data)):
        raise FontSafetyError(f"Glyph range outside EXE or overlaps pointer table for {font_key}")
    return desc, base, ptr_start, glyph_start, glyph_end, num_ptrs, rows


def load_font_model(data: bytes | bytearray, game_profile: dict, font_key: str) -> list[dict]:
    """Parse and strictly validate one font while canonicalising shared glyphs."""
    desc, base, ptr_start, glyph_start, glyph_end, num_ptrs, rows = _validate_description(
        data, game_profile, font_key
    )
    glyph_offsets = []
    for index in range(num_ptrs):
        source = ptr_start + index * 2
        relative = struct.unpack_from("<H", data, source)[0]
        off = base + relative
        if not glyph_start <= off < glyph_end:
            raise FontSafetyError(
                f"Glyph pointer {index} for {font_key} targets {off:#x} outside "
                f"{glyph_start:#x}-{glyph_end:#x}"
            )
        glyph_offsets.append(off)

    sorted_unique = sorted(set(glyph_offsets))
    if not sorted_unique or sorted_unique[0] != glyph_start:
        raise FontSafetyError(f"First glyph for {font_key} does not start at glyph_start")

    glyph_by_offset = {}
    for index, off in enumerate(sorted_unique):
        slot_end = sorted_unique[index + 1] if index + 1 < len(sorted_unique) else glyph_end
        slot_size = slot_end - off
        if slot_size <= 1:
            raise FontSafetyError(f"Invalid/overlapping glyph slot at {off:#x} in {font_key}")

        width = int(data[off])
        if desc["type"] == "dynamic":
            if (slot_size - 1) % rows:
                raise FontSafetyError(f"Dynamic glyph slot at {off:#x} has an uneven row layout")
            capacity_bpr = (slot_size - 1) // rows
            if capacity_bpr not in (1, 2, 3):
                raise FontSafetyError(
                    f"Dynamic glyph slot at {off:#x} has unsupported capacity {capacity_bpr}"
                )
            max_width = capacity_bpr * 8
            if not 1 <= width <= max_width:
                raise FontSafetyError(
                    f"Glyph width {width} at {off:#x} exceeds slot capacity {max_width}"
                )
            bpr = bytes_per_row_for_width(width)
        else:
            expected_size = int(desc.get("bytes_per_char", rows + 1))
            if expected_size != rows + 1 or slot_size != expected_size:
                raise FontSafetyError(
                    f"Fixed glyph slot at {off:#x} has size {slot_size}, expected {expected_size}"
                )
            capacity_bpr = 1
            max_width = 8
            if not 1 <= width <= 8:
                raise FontSafetyError(f"Fixed glyph width {width} at {off:#x} is invalid")
            bpr = 1

        required = 1 + rows * bpr
        if off + required > slot_end or off + required > len(data):
            raise FontSafetyError(f"Glyph data at {off:#x} exceeds its physical slot")
        bitmap = [
            int.from_bytes(data[off + 1 + row * bpr:off + 1 + (row + 1) * bpr], "big")
            for row in range(rows)
        ]
        glyph_by_offset[off] = {
            "glyph_off": off,
            "slot_end": slot_end,
            "slot_size": slot_size,
            "capacity_bpr": capacity_bpr,
            "max_width": max_width,
            "width": width,
            "bytes_per_row": bpr,
            "bitmap": bitmap,
        }

    first_occurrence = {}
    font_data = []
    ascii_start = int(desc["ascii_start"])
    for index, off in enumerate(glyph_offsets):
        first = first_occurrence.setdefault(off, index)
        font_data.append(
            {
                "ascii": ascii_start + index,
                "alias_of": None if first == index else first,
                "glyph": glyph_by_offset[off],
            }
        )
    validate_font_model(font_data, desc, len(data))
    return font_data


def validate_font_model(font_data: list[dict], desc: dict, data_length: int | None = None) -> dict:
    if len(font_data) != int(desc["num_ptrs"]):
        raise FontSafetyError(
            f"Font model has {len(font_data)} characters, expected {desc['num_ptrs']}"
        )
    rows = int(desc["rows"])
    first_by_offset = {}
    object_by_offset = {}
    offsets = []
    ascii_start = int(desc["ascii_start"])

    for index, char in enumerate(font_data):
        if char.get("ascii") != ascii_start + index:
            raise FontSafetyError(f"Invalid character index {index}")
        glyph = char.get("glyph")
        if not isinstance(glyph, dict):
            raise FontSafetyError(f"Character {index} has no glyph object")
        off = glyph.get("glyph_off")
        if not isinstance(off, int):
            raise FontSafetyError(f"Character {index} has an invalid glyph offset")
        if off in object_by_offset and object_by_offset[off] is not glyph:
            raise FontSafetyError(f"Aliases at {off:#x} do not share one canonical glyph object")
        object_by_offset.setdefault(off, glyph)
        first = first_by_offset.setdefault(off, index)
        expected_alias = None if first == index else first
        if char.get("alias_of") != expected_alias:
            raise FontSafetyError(f"Alias metadata mismatch for character {index}")
        offsets.append(off)

    unique_offsets = sorted(set(offsets))
    if not unique_offsets or unique_offsets[0] != int(desc["glyph_start"]):
        raise FontSafetyError("Font model does not begin at glyph_start")
    for index, off in enumerate(unique_offsets):
        glyph = object_by_offset[off]
        expected_end = unique_offsets[index + 1] if index + 1 < len(unique_offsets) else int(desc["glyph_end"])
        if glyph.get("slot_end") != expected_end or glyph.get("slot_size") != expected_end - off:
            raise FontSafetyError(f"Slot boundary mismatch at {off:#x}")
        if data_length is not None and not (0 <= off < expected_end <= data_length):
            raise FontSafetyError(f"Slot at {off:#x} is outside the EXE")
        width = glyph.get("width")
        bpr = glyph.get("bytes_per_row")
        bitmap = glyph.get("bitmap")
        if not isinstance(width, int) or isinstance(width, bool):
            raise FontSafetyError(f"Invalid width at {off:#x}")
        if not isinstance(bitmap, list) or len(bitmap) != rows:
            raise FontSafetyError(f"Invalid bitmap row count at {off:#x}")

        if desc["type"] == "dynamic":
            capacity_bpr = (expected_end - off - 1) // rows
            if 1 + rows * capacity_bpr != expected_end - off or capacity_bpr not in (1, 2, 3):
                raise FontSafetyError(f"Invalid dynamic slot capacity at {off:#x}")
            if glyph.get("capacity_bpr") != capacity_bpr or glyph.get("max_width") != capacity_bpr * 8:
                raise FontSafetyError(f"Stored capacity mismatch at {off:#x}")
            expected_bpr = bytes_per_row_for_width(width)
            if not 1 <= width <= capacity_bpr * 8 or bpr != expected_bpr:
                raise FontSafetyError(f"Width/row-class exceeds slot at {off:#x}")
        else:
            expected_size = int(desc.get("bytes_per_char", rows + 1))
            if expected_end - off != expected_size or expected_size != rows + 1:
                raise FontSafetyError(f"Invalid fixed slot at {off:#x}")
            if glyph.get("capacity_bpr") != 1 or glyph.get("max_width") != 8:
                raise FontSafetyError(f"Stored fixed capacity mismatch at {off:#x}")
            if not 1 <= width <= 8 or bpr != 1:
                raise FontSafetyError(f"Invalid fixed width at {off:#x}")

        limit = 1 << (8 * bpr)
        if any(not isinstance(value, int) or isinstance(value, bool) or not 0 <= value < limit for value in bitmap):
            raise FontSafetyError(f"Bitmap value outside row class at {off:#x}")
        if 1 + rows * bpr > expected_end - off:
            raise FontSafetyError(f"Glyph serialization exceeds slot at {off:#x}")

    return {
        "pointer_count": len(font_data),
        "unique_count": len(unique_offsets),
        "alias_count": len(font_data) - len(unique_offsets),
        "slot_sizes": [object_by_offset[off]["slot_size"] for off in unique_offsets],
    }


def validate_all_fonts(data: bytes | bytearray, game_profile: dict) -> dict[str, dict]:
    result = {}
    for font_key in game_profile.get("fonts", {}):
        model = load_font_model(data, game_profile, font_key)
        result[font_key] = validate_font_model(
            model, game_profile["fonts"][font_key], len(data)
        )
    return result


def clone_font_model(font_data: list[dict]) -> list[dict]:
    """deepcopy preserves the shared-glyph identity graph."""
    return copy.deepcopy(font_data)


def _convert_rows_left_aligned(bitmap: list[int], old_bpr: int, new_bpr: int) -> list[int]:
    if old_bpr not in (1, 2, 3) or new_bpr not in (1, 2, 3):
        raise FontSafetyError("Unsupported bytes-per-row conversion")
    shift = 8 * abs(new_bpr - old_bpr)
    if new_bpr > old_bpr:
        converted = [value << shift for value in bitmap]
    elif new_bpr < old_bpr:
        converted = [value >> shift for value in bitmap]
    else:
        converted = list(bitmap)
    mask = (1 << (8 * new_bpr)) - 1
    return [value & mask for value in converted]


def change_glyph_width(glyph: dict, desc: dict, new_width: int) -> None:
    if not isinstance(new_width, int) or isinstance(new_width, bool):
        raise FontSafetyError("Width must be an integer")
    old_bpr = int(glyph["bytes_per_row"])
    if desc["type"] == "dynamic":
        max_width = int(glyph["max_width"])
        if not 1 <= new_width <= max_width:
            raise FontSafetyError(f"Width {new_width} exceeds this glyph slot (max {max_width})")
        new_bpr = bytes_per_row_for_width(new_width)
    else:
        if not 1 <= new_width <= 8:
            raise FontSafetyError("FLOW/MICRO width must remain between 1 and 8")
        new_bpr = 1
    converted = _convert_rows_left_aligned(glyph["bitmap"], old_bpr, new_bpr)
    glyph["width"] = new_width
    glyph["bytes_per_row"] = new_bpr
    glyph["bitmap"] = converted


def copy_glyph_payload(glyph: dict, desc: dict) -> dict:
    return {
        "font_type": desc["type"],
        "rows": int(desc["rows"]),
        "width": int(glyph["width"]),
        "bytes_per_row": int(glyph["bytes_per_row"]),
        "bitmap": list(glyph["bitmap"]),
    }


def paste_glyph_payload(glyph: dict, target_desc: dict, payload: dict) -> None:
    try:
        source_type = payload["font_type"]
        source_rows = int(payload["rows"])
        source_bpr = int(payload["bytes_per_row"])
        source_width = int(payload["width"])
        source_bitmap = list(payload["bitmap"])
    except (KeyError, TypeError, ValueError) as exc:
        raise FontSafetyError("Clipboard does not contain a valid glyph") from exc
    target_rows = int(target_desc["rows"])
    if source_rows != target_rows or len(source_bitmap) != target_rows:
        raise FontSafetyError(
            f"Incompatible glyph height: source {source_rows}, target {target_rows}"
        )
    if source_type not in {"dynamic", "fixed"}:
        raise FontSafetyError("Clipboard font type is invalid")
    expected_source_bpr = bytes_per_row_for_width(source_width) if source_type == "dynamic" else 1
    if source_bpr not in (1, 2, 3) or source_bpr != expected_source_bpr:
        raise FontSafetyError("Clipboard row class is invalid")
    if source_type == "fixed" and not 1 <= source_width <= 8:
        raise FontSafetyError("Clipboard fixed width is invalid")
    if any(not isinstance(value, int) or value < 0 or value >= 1 << (8 * source_bpr) for value in source_bitmap):
        raise FontSafetyError("Clipboard bitmap is invalid")

    if target_desc["type"] == "fixed":
        if not 1 <= source_width <= 8:
            raise FontSafetyError("Glyph is wider than a FLOW/MICRO target")
        target_bpr = 1
    else:
        max_width = int(glyph["max_width"])
        if not 1 <= source_width <= max_width:
            raise FontSafetyError(
                f"Glyph width {source_width} exceeds target slot capacity {max_width}"
            )
        target_bpr = bytes_per_row_for_width(source_width)

    converted = _convert_rows_left_aligned(source_bitmap, source_bpr, target_bpr)
    glyph["width"] = source_width
    glyph["bytes_per_row"] = target_bpr
    glyph["bitmap"] = converted


def _write_glyph(buf: bytearray, glyph: dict, desc: dict) -> None:
    off = int(glyph["glyph_off"])
    rows = int(desc["rows"])
    bpr = int(glyph["bytes_per_row"])
    required_end = off + 1 + rows * bpr
    if required_end > int(glyph["slot_end"]) or required_end > len(buf):
        raise FontSafetyError(f"Glyph write at {off:#x} exceeds its slot")
    buf[off] = int(glyph["width"])
    for row, value in enumerate(glyph["bitmap"]):
        row_bytes = int(value).to_bytes(bpr, "big")
        row_start = off + 1 + row * bpr
        buf[row_start:row_start + bpr] = row_bytes


def stage_font_apply(
    data: bytes | bytearray,
    font_data: list[dict],
    game_profile: dict,
    font_key: str,
) -> tuple[bytearray, dict]:
    """Validate, serialize on a copy, and verify readback before returning it."""
    desc = _font_description(game_profile, font_key)
    base_model = load_font_model(data, game_profile, font_key)
    validate_font_model(font_data, desc, len(data))
    for current, base in zip(font_data, base_model):
        current_glyph = current["glyph"]
        base_glyph = base["glyph"]
        if (
            current_glyph["glyph_off"] != base_glyph["glyph_off"]
            or current_glyph["slot_end"] != base_glyph["slot_end"]
            or current["alias_of"] != base["alias_of"]
        ):
            raise FontSafetyError("Font model no longer matches the EXE pointer/alias structure")

    work = bytearray(data)
    for glyph in unique_glyphs(font_data):
        _write_glyph(work, glyph, desc)

    changed_offsets = [index for index, (before, after) in enumerate(zip(data, work)) if before != after]
    allowed = set()
    for glyph in unique_glyphs(font_data):
        allowed.update(range(glyph["glyph_off"], glyph["slot_end"]))
    if any(index not in allowed for index in changed_offsets):
        raise FontSafetyError("Font serialization changed bytes outside glyph slots")

    readback = load_font_model(work, game_profile, font_key)
    expected_by_off = {glyph["glyph_off"]: glyph for glyph in unique_glyphs(font_data)}
    for glyph in unique_glyphs(readback):
        expected = expected_by_off[glyph["glyph_off"]]
        if (
            glyph["width"] != expected["width"]
            or glyph["bytes_per_row"] != expected["bytes_per_row"]
            or glyph["bitmap"] != expected["bitmap"]
        ):
            raise FontSafetyError(f"Font readback mismatch at {glyph['glyph_off']:#x}")
    return work, {
        "unique_count": len(expected_by_off),
        "changed_offsets": changed_offsets,
    }


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
    """Parse a complete font into a cloned model; never returns a partial import."""
    staged = clone_font_model(font_data)
    glyphs = unique_glyphs(staged)
    rows = int(desc["rows"])
    pos = 0
    for index, glyph in enumerate(glyphs):
        if pos >= len(raw):
            raise FontSafetyError(f"Import is truncated before glyph {index}")
        width = int(raw[pos])
        pos += 1
        if desc["type"] == "dynamic":
            if not 1 <= width <= int(glyph["max_width"]):
                raise FontSafetyError(
                    f"Imported width {width} exceeds glyph {index} capacity {glyph['max_width']}"
                )
            bpr = bytes_per_row_for_width(width)
        else:
            if not 1 <= width <= 8:
                raise FontSafetyError(f"Imported fixed width {width} is invalid at glyph {index}")
            bpr = 1
        needed = rows * bpr
        if pos + needed > len(raw):
            raise FontSafetyError(f"Import is truncated inside glyph {index}")
        bitmap = [
            int.from_bytes(raw[pos + row * bpr:pos + (row + 1) * bpr], "big")
            for row in range(rows)
        ]
        pos += needed
        glyph["width"] = width
        glyph["bytes_per_row"] = bpr
        glyph["bitmap"] = bitmap
    if pos != len(raw):
        raise FontSafetyError(f"Import has {len(raw) - pos} unexpected trailing bytes")
    validate_font_model(staged, desc)
    return staged


def _normalised_path(path: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.realpath(os.path.abspath(os.fspath(path))))


def paths_equal(left: str | os.PathLike[str] | None, right: str | os.PathLike[str] | None) -> bool:
    return bool(left and right and _normalised_path(left) == _normalised_path(right))


def _atomic_replace_bytes(target: Path, payload: bytes) -> None:
    directory = target.parent
    if not directory.is_dir():
        raise OSError(f"Target directory does not exist: {directory}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(directory))
    try:
        with os.fdopen(fd, "wb") as handle:
            written = handle.write(payload)
            if written != len(payload):
                raise OSError(f"Short write: {written} of {len(payload)} bytes")
            handle.flush()
            os.fsync(handle.fileno())
        if Path(temp_name).read_bytes() != payload:
            raise OSError("Temporary-file readback mismatch")
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
    """Write and verify in the target directory, then replace atomically."""
    target = Path(target_path)
    payload_bytes = bytes(payload)
    backup_path = None
    if backup_original:
        if not target.is_file():
            raise OSError("Cannot back up a missing original file")
        backup_path = _next_backup_path(target)
        _atomic_replace_bytes(backup_path, target.read_bytes())
    _atomic_replace_bytes(target, payload_bytes)
    return str(backup_path) if backup_path is not None else None


__all__ = [
    "FontSafetyError",
    "atomic_save_bytes",
    "bytes_per_row_for_width",
    "change_glyph_width",
    "clone_font_model",
    "copy_glyph_payload",
    "export_font_bytes",
    "import_font_bytes",
    "load_font_model",
    "paste_glyph_payload",
    "paths_equal",
    "stage_font_apply",
    "unique_glyphs",
    "validate_all_fonts",
    "validate_font_model",
]
