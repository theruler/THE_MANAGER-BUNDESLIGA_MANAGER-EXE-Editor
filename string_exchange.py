"""Deterministic, fail-closed string exchange for supported EXE profiles."""

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


FORMAT_NAME = "stefanos-string-exchange"
FORMAT_VERSION = 2
HASH_PATTERN = re.compile(r"[0-9A-F]{64}\Z")
HEX_PAIR_PATTERN = re.compile(r"[0-9A-Fa-f]{2}\Z")
PROTECTED_TOKEN_PATTERN = re.compile(
    rf"(?:{CONTROL_TOKEN_PATTERN.pattern})|€|£|°"
)

TOP_LEVEL_FIELDS = {
    "format",
    "version",
    "profile_id",
    "profile_structure_sha256",
    "charmap_sha256",
    "source_manifest_sha256",
    "entry_count",
    "entries",
}
ENTRY_FIELDS = {
    "string_id",
    "kind",
    "editable",
    "suffix_links",
    "font",
    "repack_block",
    "pointer_count",
    "code_pointer_count",
    "fixed_capacity_bytes",
    "protected_trail_spaces",
    "source_raw_sha256",
    "source_text",
    "translated_text",
}
SUFFIX_LINK_FIELDS = {"role", "other_id", "byte_offset"}
READ_ONLY_ENTRY_FIELDS = ENTRY_FIELDS - {
    "source_raw_sha256",
    "source_text",
    "translated_text",
}


class StringExchangeError(ValueError):
    """Raised before live state can be touched when exchange data is unsafe."""


def _canonical_bytes(value) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StringExchangeError(f"Value cannot be canonicalised: {exc}") from exc
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
            f"Entry {entry.get('string_id', '?')} does not contain strict raw-byte text"
        ) from exc


def _range_index(profile: dict, address: int):
    for index, (start, end) in enumerate(profile["valid_ranges"]):
        if start <= address < end:
            return index
    return None


def _entry_kind(entry: dict) -> str:
    if entry.get("fixed"):
        return "fixed"
    if entry.get("ptr_addrs"):
        return "normal"
    if entry.get("code_ptr_addrs"):
        return "code-only"
    raise StringExchangeError(
        f"Entry {entry.get('string_id', '?')} has no supported reference type"
    )


def _validated_charmap(charmap: dict) -> dict[str, str]:
    if not isinstance(charmap, dict):
        raise StringExchangeError("CharMap must be an object")
    result = {}
    for raw_key, display_char in charmap.items():
        try:
            raw = bytes.fromhex(raw_key)
        except (TypeError, ValueError) as exc:
            raise StringExchangeError(f"Invalid CharMap byte key: {raw_key!r}") from exc
        if len(raw) != 1:
            raise StringExchangeError(f"CharMap key must identify one byte: {raw_key!r}")
        if not isinstance(display_char, str) or len(display_char) != 1:
            raise StringExchangeError(f"Invalid CharMap character: {display_char!r}")
        key = f"{raw[0]:02x}"
        if key in result and result[key] != display_char:
            raise StringExchangeError(f"Conflicting CharMap key: {raw_key!r}")
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
            raise StringExchangeError(f"Ambiguous CharMap character: {display_char!r}")
        inverse[display_char] = raw
    return inverse


def _escape_visible_char(display_char: str) -> str:
    if display_char == "\\":
        return "\\\\"
    if display_char in "\x00\r\n":
        raise StringExchangeError("NUL/CR/LF cannot be exported as visible text")
    return display_char


def raw_to_exchange_text(raw_bytes: bytes, charmap: dict) -> str:
    """Decode raw bytes while preserving control tokens and unknown bytes."""
    cmap = _validated_charmap(charmap)
    raw_text = raw_bytes.decode("latin-1")
    parts = []
    cursor = 0

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
    exchange_text: str,
    charmap: dict[str, str],
    *,
    escape_limits: Counter | None = None,
) -> tuple[str, Counter]:
    if not isinstance(exchange_text, str):
        raise StringExchangeError("Exchange text must be a string")
    inverse = _inverse_charmap(charmap)
    result = []
    escape_counts = Counter()
    index = 0
    while index < len(exchange_text):
        char = exchange_text[index]
        if char in "\x00\r\n":
            raise StringExchangeError("NUL, CR and LF are not allowed in imported strings")
        if char != "\\":
            codepoint = ord(char)
            if (
                codepoint <= 0xFF
                and not 0x20 <= codepoint <= 0x7E
                and char not in inverse
            ):
                raise StringExchangeError(
                    f"Unconfirmed byte-like character U+{codepoint:04X} must use \\xNN"
                )
            result.append(char)
            index += 1
            continue

        if index + 1 >= len(exchange_text):
            raise StringExchangeError("Trailing backslash in exchange text")
        if exchange_text[index + 1] == "\\":
            result.append("\\")
            index += 2
            continue
        if (
            index + 3 < len(exchange_text)
            and exchange_text[index + 1] == "x"
            and HEX_PAIR_PATTERN.fullmatch(exchange_text[index + 2:index + 4])
        ):
            byte_value = int(exchange_text[index + 2:index + 4], 16)
            if byte_value in {0x00, 0x0A, 0x0D}:
                raise StringExchangeError("NUL, CR and LF byte escapes are not allowed")
            key = f"{byte_value:02x}"
            if 0x20 <= byte_value <= 0x7E or key in charmap:
                raise StringExchangeError(
                    f"Byte 0x{byte_value:02X} must use its confirmed visible representation"
                )
            escape_counts[byte_value] += 1
            if escape_limits is not None and escape_counts[byte_value] > escape_limits[byte_value]:
                raise StringExchangeError(
                    f"New or duplicated byte escape \\x{byte_value:02X}"
                )
            result.append(chr(byte_value))
            index += 4
            continue
        raise StringExchangeError("Backslash must be escaped as \\\\ or form \\xNN")
    return "".join(result), escape_counts


def exchange_text_to_raw(
    exchange_text: str,
    charmap: dict,
    allowed_bytes,
    *,
    source_mode: bool = False,
    escape_limits: Counter | None = None,
    preserve_bytes: bytes = b"",
) -> tuple[bytes, str, Counter]:
    """Strictly encode exchange text without replacement or invented bytes."""
    cmap = _validated_charmap(charmap)
    display_text, escape_counts = _unescape_exchange_text(
        exchange_text, cmap, escape_limits=escape_limits
    )
    inverse = _inverse_charmap(cmap)
    allowed = set(allowed_bytes)
    encoded = bytearray()
    confirmed_outside = Counter()
    cursor = 0

    def encode_segment(segment: str):
        if not segment:
            return
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
            raise StringExchangeError(f"Invalid control token: {match.group(0)!r}") from exc
        if any(byte_value not in allowed for byte_value in token_raw):
            raise StringExchangeError(f"Control token outside active font: {match.group(0)!r}")
        encoded.extend(token_raw)
        cursor = match.end()
    encode_segment(display_text[cursor:])

    outside_counts = Counter(byte_value for byte_value in encoded if byte_value not in allowed)
    if source_mode:
        permitted = escape_counts + confirmed_outside
    else:
        permitted = Counter(preserve_bytes)
    for byte_value, count in outside_counts.items():
        if count > permitted[byte_value]:
            raise StringExchangeError(
                f"Unconfirmed byte 0x{byte_value:02X} was introduced or duplicated"
            )
    return bytes(encoded), display_text, escape_counts


def _suffix_links(entries: list[dict], profile: dict) -> dict[str, list[dict]]:
    links = {entry["string_id"]: [] for entry in entries}
    for range_index, _range in enumerate(profile["valid_ranges"]):
        group = sorted(
            (
                entry for entry in entries
                if not entry.get("fixed")
                and _range_index(profile, entry["str_addr"]) == range_index
            ),
            key=lambda entry: entry["str_addr"],
        )
        for child in group:
            child_raw = _entry_raw_bytes(child)
            candidates = []
            for parent in group:
                offset = child["str_addr"] - parent["str_addr"]
                parent_raw = _entry_raw_bytes(parent)
                if 0 < offset < len(parent_raw) and child_raw == parent_raw[offset:]:
                    candidates.append((parent["str_addr"], parent, offset))
            if not candidates:
                continue
            _address, parent, offset = max(candidates, key=lambda item: item[0])
            links[parent["string_id"]].append({
                "role": "parent",
                "other_id": child["string_id"],
                "byte_offset": offset,
            })
            links[child["string_id"]].append({
                "role": "child",
                "other_id": parent["string_id"],
                "byte_offset": offset,
            })
    for value in links.values():
        value.sort(key=lambda link: (link["role"], link["other_id"], link["byte_offset"]))
    return links


def _protected_trailing(string_id, raw, charmap, layout_reference) -> int:
    """Geschuetzter nachlaufender Leerraum eines Eintrags.

    min(englisches Original, heutiger Stand). Das Minimum verhindert, dass
    Eintraege, deren Leerlauf schon heute unter dem englischen liegt, den
    Ist-Zustand ungueltig machen und einen unveraenderten Rundlauf blockieren."""
    current = _trailing_spaces(raw_to_exchange_text(raw, charmap))
    if not layout_reference:
        return current
    reference = layout_reference.get(string_id, 0)
    if not isinstance(reference, int) or reference < 0:
        return current
    return min(reference, current)


def _build_context(
    profile_id: str,
    profile: dict,
    entries: list[dict],
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
    layout_reference: dict | None = None,
):
    ids = [entry.get("string_id") for entry in entries]
    if any(not isinstance(string_id, str) or not string_id for string_id in ids):
        raise StringExchangeError("Every entry must have a string_id")
    if len(set(ids)) != len(ids):
        raise StringExchangeError("Duplicate string_id in live entries")

    normalised_charmaps = {
        font_name: _validated_charmap(charmap)
        for font_name, charmap in sorted(charmaps.items())
    }
    links_by_id = _suffix_links(entries, profile)
    fixed_slots = {address: size for address, size in profile.get("fixed_strings", [])}
    contexts = []
    structure_entries = []

    for entry in sorted(entries, key=lambda item: item["string_id"]):
        string_id = entry["string_id"]
        kind = _entry_kind(entry)
        font = effective_font(entry)
        if font not in normalised_charmaps or font not in font_codes:
            raise StringExchangeError(f"No confirmed CharMap/font codes for {font}")
        raw = _entry_raw_bytes(entry)
        block = None if kind == "fixed" else _range_index(profile, entry["str_addr"])
        if kind != "fixed" and block is None:
            raise StringExchangeError(f"Entry {string_id} is outside all Repack blocks")
        if kind == "fixed":
            slot_size = fixed_slots.get(entry["str_addr"])
            if slot_size is None or slot_size < 1:
                raise StringExchangeError(f"Unknown fixed slot for {string_id}")
            fixed_capacity = slot_size - 1
        else:
            fixed_capacity = None
        suffix_links = copy.deepcopy(links_by_id[string_id])
        metadata = {
            "string_id": string_id,
            "kind": kind,
            "editable": not suffix_links,
            "suffix_links": suffix_links,
            "font": font,
            "repack_block": block,
            "pointer_count": len(set(entry.get("ptr_addrs", []))),
            "code_pointer_count": len(set(entry.get("code_ptr_addrs", []))),
            "fixed_capacity_bytes": fixed_capacity,
            "protected_trail_spaces": _protected_trailing(
                string_id, raw, normalised_charmaps[font], layout_reference
            ),
        }
        row = dict(metadata)
        row.update({
            "source_raw_sha256": _sha256_bytes(raw),
            "source_text": raw_to_exchange_text(raw, normalised_charmaps[font]),
            "translated_text": None,
        })
        contexts.append({
            "entry": entry,
            "metadata": metadata,
            "row": row,
            "raw": raw,
            "charmap": normalised_charmaps[font],
            "allowed": set(font_codes[font]),
        })
        structure_entries.append({
            **metadata,
            "pointer_sources": sorted(set(entry.get("ptr_addrs", []))),
            "code_pointer_sources": sorted(set(entry.get("code_ptr_addrs", []))),
        })

    structure_manifest = {
        "profile_id": profile_id,
        "ds_start": int(profile["ds_start"]),
        "base_const": bytes(profile["base_const"]).hex().upper(),
        "repack_ranges": [list(item) for item in profile["valid_ranges"]],
        "entries": structure_entries,
    }
    charmap_manifest = {
        "charmaps": normalised_charmaps,
        "effective_fonts": [
            [context["row"]["string_id"], context["row"]["font"]]
            for context in contexts
        ],
    }
    source_manifest = [
        [context["row"]["string_id"], context["row"]["source_raw_sha256"]]
        for context in contexts
    ]
    return contexts, {
        "profile_structure_sha256": _sha256_value(structure_manifest),
        "charmap_sha256": _sha256_value(charmap_manifest),
        "source_manifest_sha256": _sha256_value(source_manifest),
    }


def build_export_document(
    profile_id: str,
    profile: dict,
    entries: list[dict],
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
    layout_reference: dict | None = None,
) -> dict:
    contexts, fingerprints = _build_context(
        profile_id, profile, entries, charmaps, effective_font, font_codes,
        layout_reference
    )
    return {
        "format": FORMAT_NAME,
        "version": FORMAT_VERSION,
        "profile_id": profile_id,
        **fingerprints,
        "entry_count": len(contexts),
        "entries": [copy.deepcopy(context["row"]) for context in contexts],
    }


def export_json_bytes(
    profile_id: str,
    profile: dict,
    entries: list[dict],
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
    layout_reference: dict | None = None,
) -> bytes:
    document = build_export_document(
        profile_id, profile, entries, charmaps, effective_font, font_codes,
        layout_reference
    )
    text = json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        allow_nan=False,
    ) + "\n"
    return text.encode("utf-8")


def _reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StringExchangeError(f"Duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value):
    raise StringExchangeError(f"Invalid JSON numeric constant: {value}")


def parse_json_document(raw_document: bytes) -> dict:
    try:
        text = bytes(raw_document).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise StringExchangeError("Import is not valid UTF-8") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except StringExchangeError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        raise StringExchangeError(f"Invalid or truncated JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise StringExchangeError("Exchange document root must be an object")
    return document


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_hash(value, field_name):
    if not isinstance(value, str) or not HASH_PATTERN.fullmatch(value):
        raise StringExchangeError(f"{field_name} must be an uppercase SHA-256")


def _validate_schema(document: dict):
    if set(document) != TOP_LEVEL_FIELDS:
        raise StringExchangeError("Top-level schema fields do not match version 1")
    if document["format"] != FORMAT_NAME:
        raise StringExchangeError("Unsupported string exchange format")
    if not _is_int(document["version"]) or document["version"] != FORMAT_VERSION:
        raise StringExchangeError("Unsupported string exchange version")
    if not isinstance(document["profile_id"], str) or not document["profile_id"]:
        raise StringExchangeError("profile_id must be a non-empty string")
    for field in (
        "profile_structure_sha256", "charmap_sha256", "source_manifest_sha256"
    ):
        _validate_hash(document[field], field)
    if not _is_int(document["entry_count"]) or document["entry_count"] < 0:
        raise StringExchangeError("entry_count must be a non-negative integer")
    if not isinstance(document["entries"], list):
        raise StringExchangeError("entries must be an array")
    if document["entry_count"] != len(document["entries"]):
        raise StringExchangeError("entry_count does not match entries")

    seen_ids = set()
    for row in document["entries"]:
        if not isinstance(row, dict) or set(row) != ENTRY_FIELDS:
            raise StringExchangeError("Entry schema fields do not match version 1")
        string_id = row["string_id"]
        if not isinstance(string_id, str) or not string_id:
            raise StringExchangeError("string_id must be a non-empty string")
        if string_id in seen_ids:
            raise StringExchangeError(f"Duplicate string_id: {string_id}")
        seen_ids.add(string_id)
        protected = row["protected_trail_spaces"]
        if not _is_int(protected) or protected < 0:
            raise StringExchangeError(
                f"protected_trail_spaces must be a non-negative integer for {string_id}"
            )
        if row["kind"] not in {"normal", "code-only", "fixed"}:
            raise StringExchangeError(f"Invalid kind for {string_id}")
        if not isinstance(row["editable"], bool):
            raise StringExchangeError(f"editable must be boolean for {string_id}")
        if not isinstance(row["suffix_links"], list):
            raise StringExchangeError(f"suffix_links must be an array for {string_id}")
        for link in row["suffix_links"]:
            if not isinstance(link, dict) or set(link) != SUFFIX_LINK_FIELDS:
                raise StringExchangeError(f"Invalid suffix link schema for {string_id}")
            if link["role"] not in {"parent", "child"}:
                raise StringExchangeError(f"Invalid suffix role for {string_id}")
            if not isinstance(link["other_id"], str) or not link["other_id"]:
                raise StringExchangeError(f"Invalid suffix peer for {string_id}")
            if not _is_int(link["byte_offset"]) or link["byte_offset"] <= 0:
                raise StringExchangeError(f"Invalid suffix offset for {string_id}")
        if not isinstance(row["font"], str) or not row["font"]:
            raise StringExchangeError(f"Invalid font for {string_id}")
        if row["repack_block"] is not None and (
            not _is_int(row["repack_block"]) or row["repack_block"] < 0
        ):
            raise StringExchangeError(f"Invalid repack_block for {string_id}")
        for field in ("pointer_count", "code_pointer_count"):
            if not _is_int(row[field]) or row[field] < 0:
                raise StringExchangeError(f"Invalid {field} for {string_id}")
        capacity = row["fixed_capacity_bytes"]
        if capacity is not None and (not _is_int(capacity) or capacity < 0):
            raise StringExchangeError(f"Invalid fixed capacity for {string_id}")
        _validate_hash(row["source_raw_sha256"], f"source_raw_sha256 for {string_id}")
        if not isinstance(row["source_text"], str):
            raise StringExchangeError(f"source_text must be a string for {string_id}")
        if row["translated_text"] is not None and not isinstance(row["translated_text"], str):
            raise StringExchangeError(f"translated_text must be null or string for {string_id}")

    calculated_manifest = _sha256_value([
        [row["string_id"], row["source_raw_sha256"]]
        for row in sorted(document["entries"], key=lambda item: item["string_id"])
    ])
    if calculated_manifest != document["source_manifest_sha256"]:
        raise StringExchangeError("source_manifest_sha256 does not match entry hashes")


def _token_signature(exchange_text: str) -> Counter:
    return Counter(match.group(0) for match in PROTECTED_TOKEN_PATTERN.finditer(exchange_text))


def _trailing_spaces(display_text: str) -> int:
    """Nachlaufender Leerraum.

    Ein String, der nur aus Leerzeichen besteht, zaehlt vollstaendig als
    nachlaufend. Wuerde man ihn als fuehrenden Leerraum verbuchen, gaelte
    freier Platz faelschlich als geschuetzt."""
    if display_text and not display_text.strip(" \t"):
        return len(display_text)
    return len(re.search(r"[ \t]*\Z", display_text).group(0))


def _layout_signature(display_text: str):
    """Fuehrender Leerraum, innere Mehrfach-Leerraeume, Tabulatoren.

    Der nachlaufende Leerraum ist bewusst NICHT Teil der Signatur. Er ist die
    Platzreserve fuer den 1:1-Nachbau und wird getrennt gegen das englische
    Original geprueft, siehe docs/patchplan/LAYOUT_REFERENCE_PATCHPLAN.md."""
    if display_text and not display_text.strip(" \t"):
        return "", (), 0
    leading = re.match(r"[ \t]*", display_text).group(0)
    trailing = re.search(r"[ \t]*\Z", display_text).group(0)
    end = len(display_text) - len(trailing) if trailing else len(display_text)
    core = display_text[len(leading):end]
    runs = Counter(re.findall(r"[ \t]{2,}", core))
    return leading, tuple(sorted(runs.items())), display_text.count("\t")


def preflight_import_json(
    raw_document: bytes,
    profile_id: str,
    profile: dict,
    entries: list[dict],
    charmaps: dict,
    effective_font: Callable[[dict], str],
    font_codes: dict[str, set[int]],
    layout_reference: dict | None = None,
) -> dict:
    """Validate an import completely and return raw replacements only."""
    document = parse_json_document(raw_document)
    _validate_schema(document)
    contexts, fingerprints = _build_context(
        profile_id, profile, entries, charmaps, effective_font, font_codes,
        layout_reference
    )
    if document["profile_id"] != profile_id:
        raise StringExchangeError(
            f"Wrong profile: {document['profile_id']!r}, expected {profile_id!r}"
        )
    if document["profile_structure_sha256"] != fingerprints["profile_structure_sha256"]:
        raise StringExchangeError("Profile structure fingerprint mismatch")
    if document["charmap_sha256"] != fingerprints["charmap_sha256"]:
        raise StringExchangeError("CharMap fingerprint mismatch")
    if document["entry_count"] != len(contexts):
        raise StringExchangeError("Import entry count does not match the loaded EXE")

    current_by_id = {context["row"]["string_id"]: context for context in contexts}
    imported_by_id = {row["string_id"]: row for row in document["entries"]}
    missing = sorted(set(current_by_id) - set(imported_by_id))
    unknown = sorted(set(imported_by_id) - set(current_by_id))
    if missing:
        raise StringExchangeError(f"Missing string_id: {missing[0]}")
    if unknown:
        raise StringExchangeError(f"Unknown string_id: {unknown[0]}")

    replacements = {}
    requested_count = 0
    idempotent_count = 0
    for string_id in sorted(current_by_id):
        context = current_by_id[string_id]
        row = imported_by_id[string_id]
        expected_row = context["row"]
        for field in READ_ONLY_ENTRY_FIELDS:
            if row[field] != expected_row[field]:
                raise StringExchangeError(f"Manipulated {field} for {string_id}")

        source_raw, source_display, source_escape_counts = exchange_text_to_raw(
            row["source_text"],
            context["charmap"],
            context["allowed"],
            source_mode=True,
        )
        if _sha256_bytes(source_raw) != row["source_raw_sha256"]:
            raise StringExchangeError(f"source_text/hash mismatch for {string_id}")

        translated = row["translated_text"]
        if translated is None:
            continue
        requested_count += 1
        desired_raw, desired_display, desired_escape_counts = exchange_text_to_raw(
            translated,
            context["charmap"],
            context["allowed"],
            source_mode=False,
            escape_limits=source_escape_counts,
            preserve_bytes=context["raw"],
        )
        if desired_escape_counts != source_escape_counts:
            raise StringExchangeError(
                f"Unconfirmed byte escapes changed for {string_id}"
            )
        if _token_signature(row["source_text"]) != _token_signature(translated):
            raise StringExchangeError(f"Protected token mismatch for {string_id}")
        if _layout_signature(source_display) != _layout_signature(desired_display):
            raise StringExchangeError(f"Protected whitespace/layout mismatch for {string_id}")
        protected = expected_row["protected_trail_spaces"]
        if _trailing_spaces(desired_display) < protected:
            raise StringExchangeError(
                f"Protected trailing space shortfall for {string_id}: "
                f"{_trailing_spaces(desired_display)} < {protected}"
            )
        if not expected_row["editable"] and desired_raw != context["raw"]:
            raise StringExchangeError(f"Suffix entry is read-only: {string_id}")
        fixed_capacity = expected_row["fixed_capacity_bytes"]
        if fixed_capacity is not None and len(desired_raw) > fixed_capacity:
            raise StringExchangeError(
                f"Fixed string {string_id} exceeds {fixed_capacity} bytes"
            )

        if desired_raw == context["raw"]:
            idempotent_count += 1
            continue
        if _sha256_bytes(context["raw"]) != row["source_raw_sha256"]:
            raise StringExchangeError(f"Stale source conflict for {string_id}")
        replacements[string_id] = desired_raw

    return {
        "profile_id": profile_id,
        "entry_count": len(contexts),
        "requested_count": requested_count,
        "changed_count": len(replacements),
        "idempotent_count": idempotent_count,
        "replacements": replacements,
        "fingerprints": fingerprints,
    }


def stage_import_transaction(
    exe_data: bytes | bytearray,
    entries: list[dict],
    replacements: dict[str, bytes],
    profile: dict,
    relocation_sites: list[int],
    font_profile: dict,
    *,
    repack_func=repack_transaction,
    font_validator=validate_all_fonts,
):
    """Apply replacements only to copies, then Repack and validate them."""
    source_suffix_links = _suffix_links(entries, profile)
    staged_data = bytearray(exe_data)
    staged_entries = copy.deepcopy(entries)
    staged_by_id = {entry["string_id"]: entry for entry in staged_entries}
    if set(replacements) - set(staged_by_id):
        raise StringExchangeError("Replacement set contains an unknown string_id")

    for string_id, raw in replacements.items():
        if not isinstance(raw, bytes):
            raise StringExchangeError(f"Replacement for {string_id} is not raw bytes")
        entry = staged_by_id[string_id]
        entry["text"] = raw.decode("latin-1")
        if entry.get("fixed"):
            max_len = int(entry["max_len"])
            if len(raw) > max_len - 1:
                raise StringExchangeError(
                    f"Fixed string {string_id} exceeds {max_len - 1} bytes"
                )
            address = int(entry["str_addr"])
            staged_data[address:address + max_len] = raw + b"\x00" * (max_len - len(raw))

    work_data, work_entries, validation = repack_func(
        staged_data, profile, staged_entries, relocation_sites
    )
    if not validation.get("ok"):
        detail = validation.get("errors", ["Unknown Repack validation failure"])[0]
        raise StringExchangeError(f"Import Repack blocked: {detail}")
    if _suffix_links(work_entries, profile) != source_suffix_links:
        raise StringExchangeError("Import would change suffix-sharing relationships")
    try:
        font_result = font_validator(work_data, font_profile)
    except (FontSafetyError, ValueError, KeyError) as exc:
        raise StringExchangeError(f"Import font validation failed: {exc}") from exc
    return work_data, work_entries, validation, font_result


__all__ = [
    "FORMAT_NAME",
    "FORMAT_VERSION",
    "StringExchangeError",
    "build_export_document",
    "export_json_bytes",
    "parse_json_document",
    "preflight_import_json",
    "raw_to_exchange_text",
    "exchange_text_to_raw",
    "stage_import_transaction",
]
