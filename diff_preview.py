"""Read-only logical diff and capacity preview for the EXE editor."""

from __future__ import annotations

import copy
import re
import struct
from dataclasses import dataclass
from typing import Callable

from font_safety import (
    FontSafetyError,
    load_font_model,
    stage_font_apply,
    unique_glyphs,
    validate_all_fonts,
)
from repack_validator import repack_transaction, validate_image
from string_exchange import StringExchangeError, build_export_document


class DiffPreviewError(ValueError):
    """Raised when a trustworthy read-only preview cannot be produced."""


_CAPACITY_ERROR = re.compile(r"Range (\d+) overflow: (\d+) > (\d+)\Z")


@dataclass
class PreviewCache:
    """Small explicitly invalidated cache for one immutable preview snapshot."""

    generation: int = 0
    snapshot: dict | None = None
    invalidation_reason: str = "initial"

    def invalidate(self, reason: str) -> None:
        self.generation += 1
        self.snapshot = None
        self.invalidation_reason = str(reason)

    def store(self, snapshot: dict) -> dict:
        self.snapshot = snapshot
        return snapshot

    def get(self) -> dict | None:
        return self.snapshot

    @property
    def valid(self) -> bool:
        return self.snapshot is not None


def _raw(entry: dict) -> bytes:
    try:
        return entry["text"].encode("latin-1")
    except (KeyError, AttributeError, UnicodeEncodeError) as exc:
        raise DiffPreviewError(
            f"Entry {entry.get('string_id', '?')} does not contain strict raw bytes"
        ) from exc


def _range_index(profile: dict, address: int) -> int | None:
    for index, (start, end) in enumerate(profile["valid_ranges"]):
        if start <= address < end:
            return index
    return None


def _kind(entry: dict) -> str:
    if entry.get("fixed"):
        return "fixed"
    if entry.get("ptr_addrs"):
        return "normal"
    if entry.get("code_ptr_addrs"):
        return "code-only"
    raise DiffPreviewError(f"Entry {entry.get('string_id', '?')} has no reference type")


def _read_c_string(data: bytes | bytearray, start: int, limit: int, label: str) -> bytes:
    if not (0 <= start < limit <= len(data)):
        raise DiffPreviewError(f"Baseline range for {label} is outside the EXE")
    end = bytes(data).find(b"\x00", start, limit)
    if end < 0:
        raise DiffPreviewError(f"Baseline string {label} is not NUL-terminated")
    return bytes(data[start:end])


def _pointer_target(
    data: bytes | bytearray,
    source: int,
    profile: dict,
    pointer_kind: str,
) -> int:
    if pointer_kind == "normal":
        if source < 0 or source + 4 > len(data):
            raise DiffPreviewError(f"Normal pointer source outside EXE: {source:#x}")
        high = bytes(data[source + 2:source + 4])
    elif pointer_kind == "code":
        if source < 1 or source + 5 > len(data):
            raise DiffPreviewError(f"Code pointer source outside EXE: {source:#x}")
        high = bytes(data[source + 3:source + 5])
    else:
        raise DiffPreviewError(f"Unknown pointer kind: {pointer_kind}")
    if high != bytes(profile["base_const"]):
        raise DiffPreviewError(
            f"Pointer {source:#x} has base {high.hex().upper()}, "
            f"expected {bytes(profile['base_const']).hex().upper()}"
        )
    low = struct.unpack_from("<H", data, source)[0]
    target = int(profile["ds_start"]) + low
    if _range_index(profile, target) is None:
        raise DiffPreviewError(f"Pointer {source:#x} targets outside Repack ranges: {target:#x}")
    return target


def reconstruct_baseline_entries(
    baseline_data: bytes | bytearray,
    current_entries: list[dict],
    profile: dict,
    relocation_sites: list[int],
) -> list[dict]:
    """Rebuild baseline text and targets from stable pointer sources/string_ids."""
    fixed_slots = {int(address): int(size) for address, size in profile.get("fixed_strings", [])}
    rebuilt = []
    seen_ids = set()

    for current in current_entries:
        string_id = current.get("string_id")
        if not isinstance(string_id, str) or not string_id or string_id in seen_ids:
            raise DiffPreviewError("Current entries do not have unique string_ids")
        seen_ids.add(string_id)
        ptr_addrs = sorted(set(int(value) for value in current.get("ptr_addrs", [])))
        code_addrs = sorted(set(int(value) for value in current.get("code_ptr_addrs", [])))

        if current.get("fixed"):
            try:
                address = int(string_id.split(":", 1)[1], 16)
            except (IndexError, ValueError) as exc:
                raise DiffPreviewError(f"Invalid fixed string_id: {string_id}") from exc
            slot_size = fixed_slots.get(address)
            if slot_size is None or slot_size < 1:
                raise DiffPreviewError(f"Unknown fixed baseline slot: {string_id}")
            raw = _read_c_string(
                baseline_data, address, address + slot_size, string_id
            )
            rebuilt.append({
                "ptr_addrs": [],
                "code_ptr_addrs": [],
                "ptr_base_const": None,
                "str_addr": address,
                "original_str_addr": address,
                "text": raw.decode("latin-1"),
                "max_len": slot_size,
                "fixed": True,
                "string_id": string_id,
            })
            continue

        targets = {
            _pointer_target(baseline_data, source, profile, "normal")
            for source in ptr_addrs
        }
        targets.update(
            _pointer_target(baseline_data, source, profile, "code")
            for source in code_addrs
        )
        if len(targets) != 1:
            raise DiffPreviewError(
                f"Baseline pointer sources for {string_id} have {len(targets)} targets"
            )
        address = targets.pop()
        range_index = _range_index(profile, address)
        range_end = int(profile["valid_ranges"][range_index][1])
        raw = _read_c_string(baseline_data, address, range_end, string_id)
        rebuilt.append({
            "ptr_addrs": ptr_addrs,
            "code_ptr_addrs": code_addrs,
            "ptr_base_const": bytes(profile["base_const"]),
            "str_addr": address,
            "original_str_addr": address,
            "text": raw.decode("latin-1"),
            "max_len": len(raw) + 1,
            "string_id": string_id,
        })

    validation = validate_image(
        bytearray(baseline_data), profile, rebuilt, relocation_sites
    )
    if not validation.get("ok"):
        detail = validation.get("errors", ["Unknown baseline validation failure"])[0]
        raise DiffPreviewError(f"Baseline reconstruction failed: {detail}")
    return rebuilt


def _repack_read_only(
    data: bytes | bytearray,
    profile: dict,
    entries: list[dict],
    relocation_sites: list[int],
):
    before_data = bytes(data)
    before_entries = copy.deepcopy(entries)
    work_data, work_entries, validation = repack_transaction(
        bytearray(data), profile, copy.deepcopy(entries), list(relocation_sites)
    )
    if bytes(data) != before_data or entries != before_entries:
        raise DiffPreviewError("Authoritative Repack dry-run mutated its inputs")
    return work_data, work_entries, validation


def _merged_used(entries: list[dict], start: int, end: int) -> int:
    """Measure the validated Repacker result; this does not predict placement."""
    intervals = []
    for entry in entries:
        if entry.get("fixed") or not start <= int(entry["str_addr"]) < end:
            continue
        left = int(entry["str_addr"])
        right = left + len(_raw(entry)) + 1
        if right > end:
            raise DiffPreviewError(f"Repacked string crosses block end at {left:#x}")
        intervals.append((left, right))
    intervals.sort()
    merged = []
    for left, right in intervals:
        if not merged or left > merged[-1][1]:
            merged.append([left, right])
        else:
            merged[-1][1] = max(merged[-1][1], right)
    return sum(right - left for left, right in merged)


def _capacity_rows(profile: dict, repacked_entries: list[dict]) -> list[dict]:
    rows = []
    for index, (start, end) in enumerate(profile["valid_ranges"]):
        total = int(end) - int(start)
        used = _merged_used(repacked_entries, int(start), int(end))
        rows.append({
            "block": index,
            "start": int(start),
            "end": int(end),
            "total": total,
            "used": used,
            "free": total - used,
        })
    return rows


def _stage_pending_text(
    current_data: bytes | bytearray,
    current_entries: list[dict],
    replacements: dict[str, bytes],
    profile: dict,
    relocation_sites: list[int],
):
    staged_data = bytearray(current_data)
    staged_entries = copy.deepcopy(current_entries)
    staged_by_id = {entry["string_id"]: entry for entry in staged_entries}
    errors = []
    dynamic_changed = False

    for string_id, raw in replacements.items():
        if string_id not in staged_by_id:
            errors.append(f"Unknown pending string_id: {string_id}")
            continue
        if not isinstance(raw, bytes):
            errors.append(f"Pending replacement for {string_id} is not raw bytes")
            continue
        entry = staged_by_id[string_id]
        entry["text"] = raw.decode("latin-1")
        if entry.get("fixed"):
            max_len = int(entry["max_len"])
            if len(raw) > max_len - 1:
                errors.append(
                    f"Fixed string {string_id} exceeds {max_len - 1} bytes "
                    f"({len(raw)} bytes)"
                )
                continue
            address = int(entry["str_addr"])
            staged_data[address:address + max_len] = (
                raw + b"\x00" * (max_len - len(raw))
            )
        else:
            dynamic_changed = True

    if errors:
        return None, staged_entries, {
            "ok": False,
            "errors": errors,
            "stage": "pending-preflight",
        }, dynamic_changed

    if dynamic_changed:
        work_data, work_entries, validation = _repack_read_only(
            staged_data, profile, staged_entries, relocation_sites
        )
        return work_data, (work_entries or staged_entries), validation, True

    validation = validate_image(
        staged_data, profile, staged_entries, relocation_sites
    )
    validation["stage"] = "fixed-preview"
    return (
        staged_data if validation.get("ok") else None,
        staged_entries,
        validation,
        False,
    )


def _pointer_value(
    data: bytes | bytearray,
    source: int,
    pointer_kind: str,
    profile: dict,
):
    target = _pointer_target(data, source, profile, pointer_kind)
    lowword = struct.unpack_from("<H", data, source)[0]
    return lowword, target


def _pointer_diffs(
    baseline_data: bytes | bytearray,
    preview_data: bytes | bytearray,
    entries: list[dict],
    profile: dict,
) -> list[dict]:
    owners = {}
    for entry in entries:
        string_id = entry["string_id"]
        for source in set(entry.get("ptr_addrs", [])):
            key = ("normal", int(source))
            if key in owners:
                raise DiffPreviewError(f"Duplicate normal pointer source: {source:#x}")
            owners[key] = string_id
        for source in set(entry.get("code_ptr_addrs", [])):
            key = ("code", int(source))
            if key in owners:
                raise DiffPreviewError(f"Duplicate code pointer source: {source:#x}")
            owners[key] = string_id

    result = []
    for (pointer_kind, source), string_id in sorted(
        owners.items(), key=lambda item: item[0][1]
    ):
        old_low, old_target = _pointer_value(
            baseline_data, source, pointer_kind, profile
        )
        new_low, new_target = _pointer_value(
            preview_data, source, pointer_kind, profile
        )
        if old_low == new_low:
            continue
        result.append({
            "source": source,
            "kind": pointer_kind,
            "string_id": string_id,
            "old_lowword": old_low,
            "new_lowword": new_low,
            "old_target": old_target,
            "new_target": new_target,
            "target_delta": new_target - old_target,
        })
    return result


def _glyph_groups(model: list[dict]) -> dict[int, dict]:
    groups = {}
    for char in model:
        glyph = char["glyph"]
        offset = int(glyph["glyph_off"])
        group = groups.setdefault(offset, {"glyph": glyph, "codes": []})
        if group["glyph"] is not glyph:
            raise DiffPreviewError(f"Aliases at {offset:#x} are not canonical")
        group["codes"].append(int(char["ascii"]))
    return groups


def _font_diffs(
    baseline_data: bytes | bytearray,
    current_data: bytes | bytearray,
    preview_data: bytes | bytearray,
    font_profile: dict,
    *,
    pending_font_key: str | None,
) -> tuple[list[dict], list[str]]:
    result = []
    errors = []
    try:
        validate_all_fonts(baseline_data, font_profile)
        validate_all_fonts(preview_data, font_profile)
    except (FontSafetyError, KeyError, ValueError) as exc:
        return [], [str(exc)]

    for font_key, desc in font_profile.get("fonts", {}).items():
        ptr_start, ptr_end = int(desc["ptr_start"]), int(desc["ptr_end"])
        if bytes(baseline_data[ptr_start:ptr_end]) != bytes(preview_data[ptr_start:ptr_end]):
            errors.append(f"Font pointer table changed for {font_key}")
            continue
        try:
            old_model = load_font_model(baseline_data, font_profile, font_key)
            new_model = load_font_model(preview_data, font_profile, font_key)
        except FontSafetyError as exc:
            errors.append(f"{font_key}: {exc}")
            continue
        old_groups = _glyph_groups(old_model)
        new_groups = _glyph_groups(new_model)
        if set(old_groups) != set(new_groups):
            errors.append(f"Physical glyph set changed for {font_key}")
            continue

        for offset in sorted(old_groups):
            old = old_groups[offset]
            new = new_groups[offset]
            if old["codes"] != new["codes"]:
                errors.append(f"Alias set changed at {offset:#x} in {font_key}")
                continue
            old_glyph, new_glyph = old["glyph"], new["glyph"]
            slot_end = int(old_glyph["slot_end"])
            changed_bytes = sum(
                before != after
                for before, after in zip(
                    baseline_data[offset:slot_end], preview_data[offset:slot_end]
                )
            )
            if not changed_bytes:
                continue
            result.append({
                "font": font_key,
                "glyph_offset": offset,
                "canonical_code": old["codes"][0],
                "alias_codes": old["codes"][1:],
                "old_width": int(old_glyph["width"]),
                "new_width": int(new_glyph["width"]),
                "max_width": int(new_glyph["max_width"]),
                "bitmap_changed": (
                    int(old_glyph["bytes_per_row"]), old_glyph["bitmap"]
                ) != (
                    int(new_glyph["bytes_per_row"]), new_glyph["bitmap"]
                ),
                "changed_physical_bytes": changed_bytes,
                "status": "PENDING" if (
                    font_key == pending_font_key
                    and bytes(current_data[offset:slot_end])
                    != bytes(preview_data[offset:slot_end])
                ) else "PASS",
            })
    return result, errors


def _document_by_id(
    profile_id: str,
    profile: dict,
    entries: list[dict],
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
) -> dict[str, dict]:
    try:
        document = build_export_document(
            profile_id,
            profile,
            entries,
            copy.deepcopy(charmaps),
            effective_font,
            font_codes,
        )
    except (StringExchangeError, KeyError, ValueError) as exc:
        raise DiffPreviewError(f"String metadata could not be reconstructed: {exc}") from exc
    return {row["string_id"]: row for row in document["entries"]}


def _capacity_failure(validation: dict):
    if validation.get("stage") != "capacity":
        return None
    for error in validation.get("errors", []):
        match = _CAPACITY_ERROR.fullmatch(str(error))
        if match:
            block, required, total = (int(value) for value in match.groups())
            return {
                "block": block,
                "required": required,
                "total": total,
                "missing": required - total,
                "error": str(error),
            }
    return None


def _baseline_raw_for_entry(
    baseline_data: bytes | bytearray,
    entry: dict,
    profile: dict,
) -> bytes:
    string_id = entry["string_id"]
    if entry.get("fixed"):
        fixed_slots = {int(address): int(size) for address, size in profile.get("fixed_strings", [])}
        try:
            address = int(string_id.split(":", 1)[1], 16)
        except (IndexError, ValueError) as exc:
            raise DiffPreviewError(f"Invalid fixed string_id: {string_id}") from exc
        size = fixed_slots.get(address)
        if size is None:
            raise DiffPreviewError(f"Unknown fixed string: {string_id}")
        return _read_c_string(baseline_data, address, address + size, string_id)
    targets = {
        _pointer_target(baseline_data, int(source), profile, "normal")
        for source in set(entry.get("ptr_addrs", []))
    }
    targets.update(
        _pointer_target(baseline_data, int(source), profile, "code")
        for source in set(entry.get("code_ptr_addrs", []))
    )
    if len(targets) != 1:
        raise DiffPreviewError(f"Baseline target is ambiguous for {string_id}")
    address = targets.pop()
    range_index = _range_index(profile, address)
    limit = int(profile["valid_ranges"][range_index][1])
    return _read_c_string(baseline_data, address, limit, string_id)


def selected_string_status(
    baseline_data: bytes | bytearray,
    entry: dict,
    profile: dict,
    font: str,
    *,
    pending_raw: bytes | None = None,
    cached_snapshot: dict | None = None,
) -> dict:
    old_raw = _baseline_raw_for_entry(baseline_data, entry, profile)
    new_raw = pending_raw if pending_raw is not None else _raw(entry)
    string_id = entry["string_id"]
    kind = _kind(entry)
    block = None if kind == "fixed" else _range_index(profile, int(entry["str_addr"]))
    status = "PENDING" if pending_raw is not None else (
        "PASS" if old_raw != new_raw else "UNCHANGED"
    )
    block_free = None
    shared_read_only = False
    if cached_snapshot:
        row = cached_snapshot.get("strings_by_id", {}).get(string_id)
        if row:
            status = row["status"] if pending_raw is None or row["status"] in {"PENDING", "FAIL"} else status
            shared_read_only = bool(row.get("read_only_shared"))
        if block is not None:
            block_row = next(
                (item for item in cached_snapshot.get("blocks", []) if item["block"] == block),
                None,
            )
            if block_row and block_row.get("preview_free") is not None:
                block_free = int(block_row["preview_free"])
    if shared_read_only and old_raw == new_raw and pending_raw is None:
        status = "READ-ONLY"
    fixed_capacity = int(entry["max_len"]) - 1 if kind == "fixed" else None
    fixed_free = None if fixed_capacity is None else fixed_capacity - len(new_raw)
    if fixed_free is not None and fixed_free < 0:
        status = "FAIL"
    return {
        "string_id": string_id,
        "kind": kind,
        "font": font,
        "old_length": len(old_raw),
        "new_length": len(new_raw),
        "delta": len(new_raw) - len(old_raw),
        "block": block,
        "fixed_capacity_bytes": fixed_capacity,
        "fixed_free": fixed_free,
        "shared_block_free": block_free,
        "status": status,
        "read_only_shared": shared_read_only,
    }


def build_diff_preview(
    *,
    baseline_data: bytes | bytearray,
    current_data: bytes | bytearray,
    current_entries: list[dict],
    profile_id: str,
    profile: dict,
    relocation_sites: list[int],
    font_profile: dict,
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
    integrity_valid: bool,
    repack_required_state: bool,
    validation_errors_state: list[str] | None,
    font_valid: bool,
    font_pending: bool,
    font_errors_state: list[str] | None,
    save_possible: bool,
    pending_replacements: dict[str, bytes] | None = None,
    pending_string_ids: set[str] | None = None,
    pending_font_key: str | None = None,
    pending_font_model: list[dict] | None = None,
    pending_error: str | None = None,
) -> dict:
    """Build a complete preview without mutating any supplied object."""
    baseline_before = bytes(baseline_data)
    current_before = bytes(current_data)
    entries_before = copy.deepcopy(current_entries)
    pending_font_before = copy.deepcopy(pending_font_model)
    replacements = dict(pending_replacements or {})
    pending_ids = set(pending_string_ids or set())
    errors = [str(pending_error)] if pending_error else []
    if not integrity_valid or repack_required_state:
        errors.extend(str(value) for value in (validation_errors_state or []))
    if not font_valid:
        errors.extend(str(value) for value in (font_errors_state or []))

    baseline_entries = reconstruct_baseline_entries(
        baseline_data, current_entries, profile, relocation_sites
    )
    baseline_work, baseline_capacity_entries, baseline_validation = _repack_read_only(
        baseline_data, profile, baseline_entries, relocation_sites
    )
    if not baseline_validation.get("ok"):
        detail = baseline_validation.get("errors", ["Unknown baseline Repack failure"])[0]
        raise DiffPreviewError(f"Baseline Repack failed: {detail}")
    del baseline_work
    baseline_capacity = _capacity_rows(profile, baseline_capacity_entries)

    current_work, current_capacity_entries, current_capacity_validation = _repack_read_only(
        current_data, profile, current_entries, relocation_sites
    )
    if current_capacity_validation.get("ok"):
        current_capacity = _capacity_rows(profile, current_capacity_entries)
    else:
        current_capacity = [
            {
                "block": index,
                "start": int(start),
                "end": int(end),
                "total": int(end) - int(start),
                "used": None,
                "free": None,
            }
            for index, (start, end) in enumerate(profile["valid_ranges"])
        ]
        errors.extend(current_capacity_validation.get("errors", []))
    del current_work

    preview_data = bytearray(current_data)
    preview_entries = copy.deepcopy(current_entries)
    preview_validation = current_capacity_validation
    dynamic_pending = False
    preview_complete = not bool(pending_error)
    preview_capacity = copy.deepcopy(current_capacity)
    font_preview_ok = not (font_pending and pending_font_model is None)

    if replacements:
        staged_data, staged_entries, staged_validation, dynamic_pending = _stage_pending_text(
            current_data,
            current_entries,
            replacements,
            profile,
            relocation_sites,
        )
        preview_entries = staged_entries
        preview_validation = staged_validation
        if staged_data is None or not staged_validation.get("ok"):
            preview_complete = False
            errors.extend(staged_validation.get("errors", []))
        else:
            preview_data = staged_data
            if dynamic_pending:
                # _stage_pending_text already returned the authoritative,
                # validated Repacker output. Measuring it again would only
                # repeat the same transaction.
                preview_capacity = _capacity_rows(profile, preview_entries)

    if pending_font_model is not None:
        if not pending_font_key:
            errors.append("Pending font model has no font key")
            preview_complete = False
            font_preview_ok = False
        elif preview_complete:
            try:
                preview_data, _font_stage = stage_font_apply(
                    preview_data,
                    copy.deepcopy(pending_font_model),
                    font_profile,
                    pending_font_key,
                )
            except (FontSafetyError, KeyError, ValueError) as exc:
                errors.append(f"Pending font preview failed: {exc}")
                preview_complete = False
                font_preview_ok = False

    failure = _capacity_failure(preview_validation)
    if failure:
        for row in preview_capacity:
            if row["block"] == failure["block"]:
                row["used"] = failure["required"]
                row["free"] = -failure["missing"]

    baseline_meta = _document_by_id(
        profile_id, profile, baseline_entries, charmaps, effective_font, font_codes
    )
    preview_meta = _document_by_id(
        profile_id, profile, preview_entries, charmaps, effective_font, font_codes
    )
    baseline_by_id = {entry["string_id"]: entry for entry in baseline_entries}
    preview_by_id = {entry["string_id"]: entry for entry in preview_entries}
    if set(baseline_by_id) != set(preview_by_id):
        raise DiffPreviewError("Baseline/current string_id sets differ")

    block_rows = []
    for base, preview in zip(baseline_capacity, preview_capacity):
        used = preview.get("used")
        delta = None if used is None else used - int(base["used"])
        block_error = None
        missing = 0
        if failure and failure["block"] == base["block"]:
            block_error = failure["error"]
            missing = failure["missing"]
        block_rows.append({
            "block": int(base["block"]),
            "start": int(base["start"]),
            "end": int(base["end"]),
            "total": int(base["total"]),
            "baseline_used": int(base["used"]),
            "preview_used": used,
            "delta": delta,
            "savings": None if delta is None else max(-delta, 0),
            "growth": None if delta is None else max(delta, 0),
            "preview_free": preview.get("free"),
            "missing_bytes": missing,
            "status": "FAIL" if block_error else (
                "PASS" if preview_complete else "UNCHANGED"
            ),
            "error": block_error,
        })

    string_rows = []
    logical_errors = []
    changed_counts = {"normal": 0, "fixed": 0, "code-only": 0}
    for string_id in sorted(baseline_by_id):
        old_entry = baseline_by_id[string_id]
        new_entry = preview_by_id[string_id]
        old_raw, new_raw = _raw(old_entry), _raw(new_entry)
        old_meta, new_meta = baseline_meta[string_id], preview_meta[string_id]
        kind = new_meta["kind"]
        changed = old_raw != new_raw
        shared = bool(old_meta["suffix_links"] or new_meta["suffix_links"])
        row_error = None
        if shared and changed:
            row_error = "READ-ONLY/shared suffix content changed"
            logical_errors.append(f"{string_id}: {row_error}")
        fixed_capacity = new_meta["fixed_capacity_bytes"]
        fixed_free = None if fixed_capacity is None else fixed_capacity - len(new_raw)
        if fixed_free is not None and fixed_free < 0:
            row_error = f"Fixed capacity exceeded by {-fixed_free} bytes"
            logical_errors.append(f"{string_id}: {row_error}")
        if changed:
            changed_counts[kind] += 1
        if row_error:
            status = "FAIL"
        elif string_id in pending_ids:
            status = "PENDING" if preview_complete else "FAIL"
        elif shared:
            status = "READ-ONLY"
        elif changed:
            status = "PASS"
        else:
            status = "UNCHANGED"
        string_rows.append({
            "string_id": string_id,
            "kind": kind,
            "font": new_meta["font"],
            "old_text": old_meta["source_text"],
            "new_text": new_meta["source_text"],
            "old_length": len(old_raw),
            "new_length": len(new_raw),
            "delta": len(new_raw) - len(old_raw),
            "repack_block": new_meta["repack_block"],
            "pointer_count": new_meta["pointer_count"],
            "code_pointer_count": new_meta["code_pointer_count"],
            "fixed_capacity_bytes": fixed_capacity,
            "fixed_free": fixed_free,
            "suffix_links": copy.deepcopy(old_meta["suffix_links"] or new_meta["suffix_links"]),
            "read_only_shared": shared,
            "status": status,
            "error": row_error,
        })
    errors.extend(logical_errors)

    pointer_rows = []
    pointer_complete = preview_complete
    if preview_complete:
        try:
            pointer_rows = _pointer_diffs(
                baseline_data, preview_data, preview_entries, profile
            )
        except DiffPreviewError as exc:
            errors.append(str(exc))
            pointer_complete = False

    font_rows, font_errors = _font_diffs(
        baseline_data,
        current_data,
        preview_data if preview_complete else current_data,
        font_profile,
        pending_font_key=pending_font_key if pending_font_model is not None else None,
    )
    errors.extend(font_errors)

    repack_pass = bool(preview_validation.get("ok")) and not any(
        row["status"] == "FAIL" for row in block_rows
    )
    validator_pass = bool(integrity_valid) and not bool(repack_required_state)
    if replacements:
        validator_pass = validator_pass and bool(preview_validation.get("ok"))
    font_pass = bool(font_valid) and not font_errors and font_preview_ok
    pending = bool(pending_ids or font_pending or pending_font_model is not None or pending_error)
    changed_strings = sum(changed_counts.values())
    fonts_affected = sorted({row["font"] for row in font_rows})
    repack_needed = bool(
        changed_counts["normal"]
        or changed_counts["code-only"]
        or pointer_rows
        or dynamic_pending
    )
    any_change = bool(changed_strings or pointer_rows or font_rows)

    if errors or not repack_pass or not validator_pass or not font_pass:
        overall_status = "FAIL"
    elif pending:
        overall_status = "PENDING"
    elif any_change:
        overall_status = "PASS"
    else:
        overall_status = "UNCHANGED"

    errors = list(dict.fromkeys(str(error) for error in errors))
    snapshot = {
        "status": overall_status,
        "profile_id": profile_id,
        "strings": string_rows,
        "strings_by_id": {row["string_id"]: row for row in string_rows},
        "blocks": block_rows,
        "pointers": pointer_rows,
        "fonts": font_rows,
        "errors": errors,
        "summary": {
            "normal_changed": changed_counts["normal"],
            "fixed_changed": changed_counts["fixed"],
            "code_only_changed": changed_counts["code-only"],
            "glyphs_changed": len(font_rows),
            "fonts_affected": fonts_affected,
            "pointer_sources_changed": len(pointer_rows),
            "pointer_preview_complete": pointer_complete,
            "repack_needed": repack_needed,
            "repack_status": "PASS" if repack_pass else "FAIL",
            "validator_status": "PASS" if validator_pass else "FAIL",
            "font_status": "PASS" if font_pass else "FAIL",
            "save_possible": bool(save_possible),
            "pending": pending,
        },
    }

    if bytes(baseline_data) != baseline_before:
        raise DiffPreviewError("Preview mutated baseline_data")
    if bytes(current_data) != current_before:
        raise DiffPreviewError("Preview mutated current_data")
    if current_entries != entries_before:
        raise DiffPreviewError("Preview mutated current entries")
    if pending_font_model != pending_font_before:
        raise DiffPreviewError("Preview mutated the pending font model")
    return snapshot


__all__ = [
    "DiffPreviewError",
    "PreviewCache",
    "build_diff_preview",
    "reconstruct_baseline_entries",
    "selected_string_status",
]
