from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from typing import Callable

from charmap import CharmapEncodeError, charmap_encode
from font_safety import FontSafetyError, validate_all_fonts
from repack_validator import repack_transaction
from translator import CONTROL_TOKEN_PATTERN
from i18n import tr


FORMAT_NAME    = "stefanos-string-exchange"
FORMAT_VERSION = 1
HASH_PATTERN        = re.compile(r"[0-9A-F]{64}\Z")
HEX_PAIR_PATTERN    = re.compile(r"[0-9A-Fa-f]{2}\Z")
PROTECTED_TOKEN_PATTERN = re.compile(rf"(?:{CONTROL_TOKEN_PATTERN.pattern})|€|£|°")

TOP_LEVEL_FIELDS = {
    "format", "version", "profile_id", "profile_structure_sha256",
    "charmap_sha256", "source_manifest_sha256", "entry_count", "entries",
}
ENTRY_FIELDS = {
    "string_id", "kind", "editable", "suffix_links", "font",
    "repack_block", "pointer_count", "code_pointer_count",
    "fixed_capacity_bytes", "source_raw_sha256", "source_text", "translated_text",
}
SUFFIX_LINK_FIELDS      = {"role", "other_id", "byte_offset"}
READ_ONLY_ENTRY_FIELDS  = ENTRY_FIELDS - {"source_raw_sha256", "source_text", "translated_text"}


class StringExchangeError(ValueError):
    pass


def _canonical_bytes(value) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise StringExchangeError(tr("xchg.err.not_serialisable", error=exc)) from exc
    return text.encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _sha256_value(value) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _entry_raw_bytes(entry: dict) -> bytes:
    try:
        return entry["text"].encode("latin-1")
    except (KeyError, AttributeError, UnicodeEncodeError) as exc:
        raise StringExchangeError(
            tr("xchg.err.not_raw_text", sid=entry.get("string_id", "?"))
        ) from exc


def _range_index(profile: dict, address: int):
    for index, (start, end) in enumerate(profile["valid_ranges"]):
        if start <= address < end:
            return index
    return None


def _entry_kind(entry: dict) -> str:
    if entry.get("fixed"):          return "fixed"
    if entry.get("ptr_addrs"):      return "normal"
    if entry.get("code_ptr_addrs"): return "code-only"
    raise StringExchangeError(tr("xchg.err.no_ref_type", sid=entry.get("string_id", "?")))


def _validated_charmap(charmap: dict) -> dict[str, str]:
    if not isinstance(charmap, dict):
        raise StringExchangeError(tr("xchg.err.charmap_not_obj"))
    result = {}
    for raw_key, display_char in charmap.items():
        try:
            raw = bytes.fromhex(raw_key)
        except (TypeError, ValueError) as exc:
            raise StringExchangeError(tr("xchg.err.invalid_key", key=raw_key)) from exc
        if len(raw) != 1:
            raise StringExchangeError(tr("xchg.err.key_not_one_byte", key=raw_key))
        if not isinstance(display_char, str) or len(display_char) != 1:
            raise StringExchangeError(tr("xchg.err.invalid_char", char=display_char))
        key = f"{raw[0]:02x}"
        if key in result and result[key] != display_char:
            raise StringExchangeError(tr("xchg.err.conflict_key", key=raw_key))
        result[key] = display_char
    try:
        charmap_encode("", result)
    except CharmapEncodeError as exc:
        raise StringExchangeError(str(exc)) from exc
    return dict(sorted(result.items()))


def _inverse_charmap(charmap: dict[str, str]) -> dict[str, int]:
    inverse = {}
    for raw_key, display_char in charmap.items():
        raw = int(raw_key, 16)
        if display_char in inverse and inverse[display_char] != raw:
            raise StringExchangeError(tr("xchg.err.ambiguous_char", char=display_char))
        inverse[display_char] = raw
    return inverse


def _escape_visible_char(display_char: str) -> str:
    if display_char == "\\":
        return "\\\\"
    if display_char in "\x00\r\n":
        raise StringExchangeError(tr("xchg.err.nul_cr_lf"))
    return display_char


def raw_to_exchange_text(raw_bytes: bytes, charmap: dict) -> str:
    cmap     = _validated_charmap(charmap)
    raw_text = raw_bytes.decode("latin-1")
    parts, cursor = [], 0

    def append_segment(segment: bytes):
        for byte_value in segment:
            key = f"{byte_value:02x}"
            if key in cmap:
                parts.append(_escape_visible_char(cmap[key]))
            elif 0x20 <= byte_value <= 0x7E:
                parts.append(_escape_visible_char(chr(byte_value)))
            else:
                parts.append(f"\\x{byte_value:02X}")

    for match in CONTROL_TOKEN_PATTERN.finditer(raw_text):
        append_segment(raw_bytes[cursor:match.start()])
        parts.append(match.group(0))
        cursor = match.end()
    append_segment(raw_bytes[cursor:])
    return "".join(parts)


def _unescape_exchange_text(
    exchange_text: str, charmap: dict[str, str], *, escape_limits: Counter | None = None,
) -> tuple[str, Counter]:
    if not isinstance(exchange_text, str):
        raise StringExchangeError(tr("xchg.err.nul_cr_lf_import"))
    inverse       = _inverse_charmap(charmap)
    result        = []
    escape_counts = Counter()
    index         = 0
    while index < len(exchange_text):
        char = exchange_text[index]
        if char in "\x00\r\n":
            raise StringExchangeError(tr("xchg.err.nul_cr_lf_import"))
        if char != "\\":
            codepoint = ord(char)
            if codepoint <= 0xFF and not 0x20 <= codepoint <= 0x7E and char not in inverse:
                raise StringExchangeError(tr("xchg.err.unconfirmed_byte", cp=codepoint))
            result.append(char); index += 1; continue
        if index + 1 >= len(exchange_text):
            raise StringExchangeError(tr("xchg.err.trailing_backslash"))
        if exchange_text[index + 1] == "\\":
            result.append("\\"); index += 2; continue
        if (index + 3 < len(exchange_text)
                and exchange_text[index + 1] == "x"
                and HEX_PAIR_PATTERN.fullmatch(exchange_text[index + 2:index + 4])):
            byte_value = int(exchange_text[index + 2:index + 4], 16)
            if byte_value in {0x00, 0x0A, 0x0D}:
                raise StringExchangeError(tr("xchg.err.nul_byte_escape"))
            key = f"{byte_value:02x}"
            if 0x20 <= byte_value <= 0x7E or key in charmap:
                raise StringExchangeError(tr("xchg.err.use_visible", byte=byte_value))
            escape_counts[byte_value] += 1
            if escape_limits is not None and escape_counts[byte_value] > escape_limits[byte_value]:
                raise StringExchangeError(tr("xchg.err.new_dup_escape", byte=byte_value))
            result.append(chr(byte_value)); index += 4; continue
        raise StringExchangeError(tr("xchg.err.bad_escape"))
    return "".join(result), escape_counts


def exchange_text_to_raw(
    exchange_text: str, charmap: dict, allowed_bytes, *,
    source_mode: bool = False, escape_limits: Counter | None = None, preserve_bytes: bytes = b"",
) -> tuple[bytes, str, Counter]:
    cmap = _validated_charmap(charmap)
    display_text, escape_counts = _unescape_exchange_text(exchange_text, cmap, escape_limits=escape_limits)
    inverse  = _inverse_charmap(cmap)
    allowed  = set(allowed_bytes)
    encoded  = bytearray()
    confirmed_outside = Counter()
    cursor = 0

    def encode_segment(segment: str):
        if not segment: return
        try:
            segment_raw = charmap_encode(segment, cmap)
        except CharmapEncodeError as exc:
            raise StringExchangeError(str(exc)) from exc
        encoded.extend(segment_raw)
        for char in segment:
            if char in inverse:
                confirmed_outside[inverse[char]] += 1

    for match in CONTROL_TOKEN_PATTERN.finditer(display_text):
        encode_segment(display_text[cursor:match.start()])
        try:
            token_raw = match.group(0).encode("ascii")
        except UnicodeEncodeError as exc:
            raise StringExchangeError(tr("xchg.err.control_token", token=match.group(0))) from exc
        if any(b not in allowed for b in token_raw):
            raise StringExchangeError(tr("xchg.err.token_outside_font", token=match.group(0)))
        encoded.extend(token_raw); cursor = match.end()
    encode_segment(display_text[cursor:])

    outside_counts = Counter(b for b in encoded if b not in allowed)
    permitted = escape_counts + confirmed_outside if source_mode else Counter(preserve_bytes)
    for byte_value, count in outside_counts.items():
        if count > permitted[byte_value]:
            raise StringExchangeError(tr("xchg.err.unconfirmed_intro", byte=byte_value))
    return bytes(encoded), display_text, escape_counts


def _suffix_links(entries: list[dict], profile: dict) -> dict[str, list[dict]]:
    links = {entry["string_id"]: [] for entry in entries}
    for range_index, _range in enumerate(profile["valid_ranges"]):
        group = sorted(
            (e for e in entries if not e.get("fixed")
             and _range_index(profile, e["str_addr"]) == range_index),
            key=lambda e: e["str_addr"],
        )
        for child in group:
            child_raw  = _entry_raw_bytes(child)
            candidates = []
            for parent in group:
                offset     = child["str_addr"] - parent["str_addr"]
                parent_raw = _entry_raw_bytes(parent)
                if 0 < offset < len(parent_raw) and child_raw == parent_raw[offset:]:
                    candidates.append((parent["str_addr"], parent, offset))
            if not candidates: continue
            _, parent, offset = max(candidates, key=lambda x: x[0])
            links[parent["string_id"]].append({"role": "parent", "other_id": child["string_id"], "byte_offset": offset})
            links[child["string_id"]].append( {"role": "child",  "other_id": parent["string_id"], "byte_offset": offset})
    for v in links.values():
        v.sort(key=lambda link: (link["role"], link["other_id"], link["byte_offset"]))
    return links


def _build_context(profile_id, profile, entries, charmaps, effective_font, font_codes):
    ids = [entry.get("string_id") for entry in entries]
    if any(not isinstance(sid, str) or not sid for sid in ids):
        raise StringExchangeError(tr("xchg.err.no_sid"))
    if len(set(ids)) != len(ids):
        raise StringExchangeError(tr("xchg.err.dup_sid"))

    normalised_charmaps = {fn: _validated_charmap(cm) for fn, cm in sorted(charmaps.items())}
    links_by_id  = _suffix_links(entries, profile)
    fixed_slots  = {addr: size for addr, size in profile.get("fixed_strings", [])}
    contexts, structure_entries = [], []

    for entry in sorted(entries, key=lambda x: x["string_id"]):
        string_id = entry["string_id"]
        kind      = _entry_kind(entry)
        font      = effective_font(entry)
        if font not in normalised_charmaps or font not in font_codes:
            raise StringExchangeError(tr("xchg.err.no_charmap", font=font))
        raw   = _entry_raw_bytes(entry)
        block = None if kind == "fixed" else _range_index(profile, entry["str_addr"])
        if kind != "fixed" and block is None:
            raise StringExchangeError(tr("xchg.err.outside_repack", sid=string_id))
        if kind == "fixed":
            slot_size = fixed_slots.get(entry["str_addr"])
            if slot_size is None or slot_size < 1:
                raise StringExchangeError(tr("xchg.err.unknown_fixed_slot", sid=string_id))
            fixed_capacity = slot_size - 1
        else:
            fixed_capacity = None
        suffix_links = copy.deepcopy(links_by_id[string_id])
        metadata = {
            "string_id": string_id, "kind": kind, "editable": not suffix_links,
            "suffix_links": suffix_links, "font": font, "repack_block": block,
            "pointer_count": len(set(entry.get("ptr_addrs", []))),
            "code_pointer_count": len(set(entry.get("code_ptr_addrs", []))),
            "fixed_capacity_bytes": fixed_capacity,
        }
        row = dict(metadata)
        row.update({
            "source_raw_sha256": _sha256_bytes(raw),
            "source_text": raw_to_exchange_text(raw, normalised_charmaps[font]),
            "translated_text": None,
        })
        contexts.append({"entry": entry, "metadata": metadata, "row": row,
                         "raw": raw, "charmap": normalised_charmaps[font],
                         "allowed": set(font_codes[font])})
        structure_entries.append({
            **metadata,
            "pointer_sources":      sorted(set(entry.get("ptr_addrs", []))),
            "code_pointer_sources": sorted(set(entry.get("code_ptr_addrs", []))),
        })

    structure_manifest = {
        "profile_id": profile_id, "ds_start": int(profile["ds_start"]),
        "base_const": bytes(profile["base_const"]).hex().upper(),
        "repack_ranges": [list(x) for x in profile["valid_ranges"]],
        "entries": structure_entries,
    }
    charmap_manifest = {
        "charmaps": normalised_charmaps,
        "effective_fonts": [[c["row"]["string_id"], c["row"]["font"]] for c in contexts],
    }
    source_manifest = [[c["row"]["string_id"], c["row"]["source_raw_sha256"]] for c in contexts]
    return contexts, {
        "profile_structure_sha256": _sha256_value(structure_manifest),
        "charmap_sha256":           _sha256_value(charmap_manifest),
        "source_manifest_sha256":   _sha256_value(source_manifest),
    }


def build_export_document(profile_id, profile, entries, charmaps, effective_font, font_codes) -> dict:
    contexts, fingerprints = _build_context(profile_id, profile, entries, charmaps, effective_font, font_codes)
    return {"format": FORMAT_NAME, "version": FORMAT_VERSION, "profile_id": profile_id,
            **fingerprints, "entry_count": len(contexts),
            "entries": [copy.deepcopy(c["row"]) for c in contexts]}


def export_json_bytes(profile_id, profile, entries, charmaps, effective_font, font_codes) -> bytes:
    document = build_export_document(profile_id, profile, entries, charmaps, effective_font, font_codes)
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    return text.encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StringExchangeError(tr("xchg.err.dup_json_key", key=key))
        result[key] = value
    return result


def _reject_constant(value):
    raise StringExchangeError(tr("xchg.err.invalid_constant", value=value))


def parse_json_document(raw_document: bytes) -> dict:
    try:
        text = bytes(raw_document).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StringExchangeError(tr("xchg.err.not_utf8")) from exc
    try:
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys,
                              parse_constant=_reject_constant)
    except StringExchangeError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise StringExchangeError(tr("xchg.err.invalid_json", error=exc)) from exc
    if not isinstance(document, dict):
        raise StringExchangeError(tr("xchg.err.root_not_obj"))
    return document


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_hash(value, field_name):
    if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
        raise StringExchangeError(tr("xchg.err.bad_hash", field=field_name))


def _validate_schema(document: dict):
    if set(document) != TOP_LEVEL_FIELDS:
        raise StringExchangeError(tr("xchg.err.schema_mismatch"))
    if document["format"] != FORMAT_NAME:
        raise StringExchangeError(tr("xchg.err.bad_format"))
    if not _is_int(document["version"]) or document["version"] != FORMAT_VERSION:
        raise StringExchangeError(tr("xchg.err.bad_version"))
    if not isinstance(document["profile_id"], str) or not document["profile_id"]:
        raise StringExchangeError(tr("xchg.err.no_profile_id"))
    for field in ("profile_structure_sha256", "charmap_sha256", "source_manifest_sha256"):
        _validate_hash(document[field], field)
    if not _is_int(document["entry_count"]) or document["entry_count"] < 0:
        raise StringExchangeError(tr("xchg.err.bad_entry_count"))
    if not isinstance(document["entries"], list):
        raise StringExchangeError(tr("xchg.err.entries_not_array"))
    if document["entry_count"] != len(document["entries"]):
        raise StringExchangeError(tr("xchg.err.count_mismatch"))

    seen_ids = set()
    for row in document["entries"]:
        if not isinstance(row, dict) or set(row) != ENTRY_FIELDS:
            raise StringExchangeError(tr("xchg.err.entry_schema"))
        string_id = row["string_id"]
        if not isinstance(string_id, str) or not string_id:
            raise StringExchangeError(tr("xchg.err.no_string_id"))
        if string_id in seen_ids:
            raise StringExchangeError(tr("xchg.err.dup_entry_id", sid=string_id))
        seen_ids.add(string_id)
        if row["kind"] not in {"normal", "code-only", "fixed"}:
            raise StringExchangeError(tr("xchg.err.invalid_kind", sid=string_id))
        if not isinstance(row["editable"], bool):
            raise StringExchangeError(tr("xchg.err.editable_not_bool", sid=string_id))
        if not isinstance(row["suffix_links"], list):
            raise StringExchangeError(tr("xchg.err.suffix_not_array", sid=string_id))
        for link in row["suffix_links"]:
            if not isinstance(link, dict) or set(link) != SUFFIX_LINK_FIELDS:
                raise StringExchangeError(tr("xchg.err.suffix_link_schema", sid=string_id))
            if link["role"] not in {"parent", "child"}:
                raise StringExchangeError(tr("xchg.err.suffix_role", sid=string_id))
            if not isinstance(link["other_id"], str) or not link["other_id"]:
                raise StringExchangeError(tr("xchg.err.suffix_peer", sid=string_id))
            if not _is_int(link["byte_offset"]) or link["byte_offset"] <= 0:
                raise StringExchangeError(tr("xchg.err.suffix_offset", sid=string_id))
        if not isinstance(row["font"], str) or not row["font"]:
            raise StringExchangeError(tr("xchg.err.no_font", sid=string_id))
        if row["repack_block"] is not None and (not _is_int(row["repack_block"]) or row["repack_block"] < 0):
            raise StringExchangeError(tr("xchg.err.invalid_block", sid=string_id))
        for field in ("pointer_count", "code_pointer_count"):
            if not _is_int(row[field]) or row[field] < 0:
                raise StringExchangeError(tr("xchg.err.invalid_ptr_count", field=field, sid=string_id))
        capacity = row["fixed_capacity_bytes"]
        if capacity is not None and (not _is_int(capacity) or capacity < 0):
            raise StringExchangeError(tr("xchg.err.invalid_capacity", sid=string_id))
        _validate_hash(row["source_raw_sha256"], f"source_raw_sha256 for {string_id}")
        if not isinstance(row["source_text"], str):
            raise StringExchangeError(tr("xchg.err.source_text_str", sid=string_id))
        if row["translated_text"] is not None and not isinstance(row["translated_text"], str):
            raise StringExchangeError(tr("xchg.err.translated_type", sid=string_id))

    calculated_manifest = _sha256_value([
        [row["string_id"], row["source_raw_sha256"]]
        for row in sorted(document["entries"], key=lambda x: x["string_id"])
    ])
    if calculated_manifest != document["source_manifest_sha256"]:
        raise StringExchangeError(tr("xchg.err.manifest_mismatch"))


def _token_signature(exchange_text: str) -> Counter:
    return Counter(m.group(0) for m in PROTECTED_TOKEN_PATTERN.finditer(exchange_text))


def _layout_signature(display_text: str):
    leading  = re.match(r"[ \t]*",  display_text).group(0)
    trailing = re.search(r"[ \t]*\Z", display_text).group(0)
    runs     = Counter(re.findall(r"[ \t]{2,}", display_text))
    return leading, trailing, tuple(sorted(runs.items())), display_text.count("\t")


def preflight_import_json(
    raw_document, profile_id, profile, entries, charmaps, effective_font, font_codes,
) -> dict:
    document = parse_json_document(raw_document)
    _validate_schema(document)
    contexts, fingerprints = _build_context(profile_id, profile, entries, charmaps, effective_font, font_codes)
    if document["profile_id"] != profile_id:
        raise StringExchangeError(tr("xchg.err.wrong_profile",
                                     got=document["profile_id"], expected=profile_id))
    if document["profile_structure_sha256"] != fingerprints["profile_structure_sha256"]:
        raise StringExchangeError(tr("xchg.err.structure_mismatch"))
    if document["charmap_sha256"] != fingerprints["charmap_sha256"]:
        raise StringExchangeError(tr("xchg.err.charmap_mismatch"))
    if document["entry_count"] != len(contexts):
        raise StringExchangeError(tr("xchg.err.entry_count_mismatch"))

    current_by_id  = {c["row"]["string_id"]: c for c in contexts}
    imported_by_id = {row["string_id"]: row for row in document["entries"]}
    missing = sorted(set(current_by_id) - set(imported_by_id))
    unknown = sorted(set(imported_by_id) - set(current_by_id))
    if missing: raise StringExchangeError(tr("xchg.err.missing_sid", sid=missing[0]))
    if unknown: raise StringExchangeError(tr("xchg.err.unknown_sid", sid=unknown[0]))

    replacements, requested_count, idempotent_count = {}, 0, 0
    for string_id in sorted(current_by_id):
        context      = current_by_id[string_id]
        row          = imported_by_id[string_id]
        expected_row = context["row"]
        for field in READ_ONLY_ENTRY_FIELDS:
            if row[field] != expected_row[field]:
                raise StringExchangeError(tr("xchg.err.manipulated_field", field=field, sid=string_id))

        source_raw, source_display, source_escape_counts = exchange_text_to_raw(
            row["source_text"], context["charmap"], context["allowed"], source_mode=True)
        if _sha256_bytes(source_raw) != row["source_raw_sha256"]:
            raise StringExchangeError(tr("xchg.err.source_hash", sid=string_id))

        translated = row["translated_text"]
        if translated is None: continue
        requested_count += 1
        desired_raw, desired_display, desired_escape_counts = exchange_text_to_raw(
            translated, context["charmap"], context["allowed"],
            source_mode=False, escape_limits=source_escape_counts, preserve_bytes=context["raw"])
        if desired_escape_counts != source_escape_counts:
            raise StringExchangeError(tr("xchg.err.escape_changed", sid=string_id))
        if _token_signature(row["source_text"]) != _token_signature(translated):
            raise StringExchangeError(tr("xchg.err.token_mismatch", sid=string_id))
        if _layout_signature(source_display) != _layout_signature(desired_display):
            raise StringExchangeError(tr("xchg.err.layout_mismatch", sid=string_id))
        if not expected_row["editable"] and desired_raw != context["raw"]:
            raise StringExchangeError(tr("xchg.err.read_only", sid=string_id))
        fixed_capacity = expected_row["fixed_capacity_bytes"]
        if fixed_capacity is not None and len(desired_raw) > fixed_capacity:
            raise StringExchangeError(tr("xchg.err.fixed_exceeds", sid=string_id, cap=fixed_capacity))
        if desired_raw == context["raw"]:
            idempotent_count += 1; continue
        if _sha256_bytes(context["raw"]) != row["source_raw_sha256"]:
            raise StringExchangeError(tr("xchg.err.stale_conflict", sid=string_id))
        replacements[string_id] = desired_raw

    return {"profile_id": profile_id, "entry_count": len(contexts),
            "requested_count": requested_count, "changed_count": len(replacements),
            "idempotent_count": idempotent_count, "replacements": replacements,
            "fingerprints": fingerprints}


def stage_import_transaction(
    exe_data, entries, replacements, profile, relocation_sites, font_profile, *,
    repack_func=repack_transaction, font_validator=validate_all_fonts,
):
    source_suffix_links = _suffix_links(entries, profile)
    staged_data         = bytearray(exe_data)
    staged_entries      = copy.deepcopy(entries)
    staged_by_id        = {entry["string_id"]: entry for entry in staged_entries}
    if set(replacements) - set(staged_by_id):
        raise StringExchangeError(tr("xchg.err.unknown_sid_replace"))

    for string_id, raw in replacements.items():
        if not isinstance(raw, bytes):
            raise StringExchangeError(tr("xchg.err.replace_not_bytes", sid=string_id))
        entry = staged_by_id[string_id]
        entry["text"] = raw.decode("latin-1")
        if entry.get("fixed"):
            max_len = int(entry["max_len"])
            if len(raw) > max_len - 1:
                raise StringExchangeError(tr("xchg.err.fixed_exceed_import",
                                             sid=string_id, max=max_len - 1))
            address = int(entry["str_addr"])
            staged_data[address:address + max_len] = raw + b"\x00" * (max_len - len(raw))

    work_data, work_entries, validation = repack_func(
        staged_data, profile, staged_entries, relocation_sites)
    if not validation.get("ok"):
        detail = validation.get("errors", [tr("xchg.err.unknown_repack")])[0]
        raise StringExchangeError(tr("xchg.err.repack_blocked", detail=detail))
    if _suffix_links(work_entries, profile) != source_suffix_links:
        raise StringExchangeError(tr("xchg.err.suffix_changed"))
    try:
        font_result = font_validator(work_data, font_profile)
    except (FontSafetyError, ValueError, KeyError) as exc:
        raise StringExchangeError(tr("xchg.err.font_validation", error=exc)) from exc
    return work_data, work_entries, validation, font_result


__all__ = [
    "FORMAT_NAME", "FORMAT_VERSION", "StringExchangeError",
    "build_export_document", "export_json_bytes", "parse_json_document",
    "preflight_import_json", "raw_to_exchange_text", "exchange_text_to_raw",
    "stage_import_transaction",
]
