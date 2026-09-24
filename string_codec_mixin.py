from __future__ import annotations
import copy
import json
import os

from charmap import CharmapEncodeError, charmap_decode, charmap_encode
from translator import CONTROL_TOKEN_PATTERN
from repack_validator import repack_transaction, validate_image
from string_exchange import StringExchangeError
from exe_handler import EXE_FONT_PROFILES
import extended_layout
from utils import DATA_DIR


class TextTransactionError(RuntimeError):
    pass


class StringCodecMixin:

    @staticmethod
    def _raw_text(raw_bytes: bytes) -> str:
        return raw_bytes.decode("latin-1")

    @staticmethod
    def _entry_raw_bytes(entry: dict) -> bytes:
        try:
            return entry["text"].encode("latin-1")
        except UnicodeEncodeError as exc:
            raise TextTransactionError(
                f"Entry {entry.get('string_id', '?')} contains non-byte Unicode text"
            ) from exc

    def _get_font_for_entry(self, entry: dict) -> str:
        gcfg     = self._game_cfg()
        mappings = gcfg["string_fonts"]
        key      = entry["string_id"]
        if key in mappings:
            return mappings[key]
        legacy_key = hex(entry.get("original_str_addr", entry["str_addr"]))
        if legacy_key in mappings:
            return mappings[legacy_key]
        ri = self.get_range_index(entry["str_addr"])
        if ri is None:
            ri = self._extended_home_range_index(entry)
        return gcfg["range_font_defaults"].get(str(ri), "FLOW.FON") if ri is not None else "FLOW.FON"

    def _extended_home_range_index(self, entry: dict):
        if not self.profile:
            return None
        extended = extended_layout.layout_for_profile(self.profile)
        if extended is None or not extended.in_pool(entry["str_addr"]):
            return None
        return extended.home_range_index(entry)

    def _charmap_for_entry(self, entry: dict) -> dict:
        font_key = self._get_font_for_entry(entry)
        return self._game_cfg().get("charmaps", {}).get(font_key, {})

    def _font_codes_for_entry(self, entry: dict) -> set[int]:
        font_key = self._get_font_for_entry(entry)
        try:
            font_profile = EXE_FONT_PROFILES[self.profile_name]["fonts"][font_key]
            first        = font_profile["ascii_start"]
            return set(range(first, first + font_profile["num_ptrs"]))
        except KeyError as exc:
            raise TextTransactionError(f"No font profile for {font_key}") from exc

    def _decode_raw_for_entry(self, entry: dict, raw_bytes: bytes,
                              *, preserve_controls=False) -> str:
        charmap = self._charmap_for_entry(entry)
        if not preserve_controls:
            return charmap_decode(raw_bytes, charmap)

        raw_text = self._raw_text(raw_bytes)
        decoded  = []
        cursor   = 0
        for match in CONTROL_TOKEN_PATTERN.finditer(raw_text):
            decoded.append(charmap_decode(raw_bytes[cursor:match.start()], charmap))
            decoded.append(match.group(0))
            cursor = match.end()
        decoded.append(charmap_decode(raw_bytes[cursor:], charmap))
        return "".join(decoded)

    def _decode_entry_text(self, entry: dict, *, preserve_controls=False) -> str:
        return self._decode_raw_for_entry(
            entry, self._entry_raw_bytes(entry),
            preserve_controls=preserve_controls,
        )

    def _encode_entry_text(self, entry: dict, display_text: str) -> bytes:
        charmap  = self._charmap_for_entry(entry)
        allowed  = self._font_codes_for_entry(entry)
        original = self._entry_raw_bytes(entry)
        encoded  = bytearray()
        cursor   = 0

        def encode_segment(segment: str):
            if not segment:
                return
            encoded.extend(charmap_encode(
                segment,
                charmap,
                allowed_bytes=allowed,
                preserve_bytes=original,
            ))

        for match in CONTROL_TOKEN_PATTERN.finditer(display_text):
            encode_segment(display_text[cursor:match.start()])
            try:
                token_bytes = match.group(0).encode("ascii")
            except UnicodeEncodeError as exc:
                raise CharmapEncodeError(
                    f"Invalid control token: {match.group(0)!r}"
                ) from exc
            if any(byte_value not in allowed for byte_value in token_bytes):
                raise CharmapEncodeError(
                    f"Control token outside active font: {match.group(0)!r}"
                )
            encoded.extend(token_bytes)
            cursor = match.end()
        encode_segment(display_text[cursor:])

        for byte_value in set(encoded) - allowed:
            if encoded.count(byte_value) > original.count(byte_value):
                raise CharmapEncodeError(
                    f"Unconfirmed byte 0x{byte_value:02X} was introduced or duplicated"
                )
        return bytes(encoded)

    def _suffix_group_ids(self, entries=None) -> set[str]:
        entries = self.entries if entries is None else entries
        dynamic = [entry for entry in entries if not entry.get("fixed")]
        grouped = set()
        for child in dynamic:
            child_bytes = self._entry_raw_bytes(child)
            for parent in dynamic:
                offset       = child["str_addr"] - parent["str_addr"]
                parent_bytes = self._entry_raw_bytes(parent)
                if 0 < offset < len(parent_bytes) and child_bytes == parent_bytes[offset:]:
                    grouped.update((child["string_id"], parent["string_id"]))
                    break
        return grouped

    def _layout_reference(self) -> dict:
        path = os.path.join(DATA_DIR, "layout-reference.json")
        try:
            with open(path, "r", encoding="utf-8") as handle:
                document = json.load(handle)
        except (OSError, ValueError):
            return {}
        if not isinstance(document, dict):
            return {}
        profiles = document.get("profiles")
        if not isinstance(profiles, dict):
            return {}
        reference = profiles.get(self.profile_name)
        if not isinstance(reference, dict):
            return {}
        return {
            key: value for key, value in reference.items()
            if isinstance(key, str) and isinstance(value, int) and value >= 0
        }

    def _string_exchange_arguments(self) -> dict:
        game_cfg   = self._game_cfg()
        font_codes = {}
        for font_name, font_desc in EXE_FONT_PROFILES[self.profile_name]["fonts"].items():
            first                = int(font_desc["ascii_start"])
            font_codes[font_name] = set(range(first, first + int(font_desc["num_ptrs"])))
        return {
            "profile_id":       self.profile_name,
            "profile":          self.profile,
            "entries":          self.entries,
            "charmaps":         copy.deepcopy(game_cfg.get("charmaps", {})),
            "effective_font":   self._get_font_for_entry,
            "font_codes":       font_codes,
            "layout_reference": self._layout_reference(),
        }

    def _prepare_entry_transaction(self, entry_index: int, display_text: str):
        source_entry   = self.entries[entry_index]
        new_bytes      = self._encode_entry_text(source_entry, display_text)
        staged_data    = bytearray(self.exe_data)
        staged_entries = copy.deepcopy(self.entries)
        staged_entry   = staged_entries[entry_index]

        if staged_entry.get("fixed"):
            max_len = staged_entry["max_len"]
            if len(new_bytes) > max_len - 1:
                raise TextTransactionError(
                    f"Fixed string exceeds {max_len - 1} bytes ({len(new_bytes)} bytes)"
                )
            staged_entry["text"] = self._raw_text(new_bytes)
            address = staged_entry["str_addr"]
            staged_data[address:address + max_len] = (
                new_bytes + b"\x00" * (max_len - len(new_bytes))
            )
            validation         = validate_image(
                staged_data, self.profile, staged_entries, self.relocation_sites
            )
            validation["stage"] = "fixed-output"
            return (staged_data, staged_entries, validation) if validation["ok"] \
                else (None, None, validation)

        staged_entry["text"] = self._raw_text(new_bytes)
        return repack_transaction(
            staged_data, self.profile, staged_entries, self.relocation_sites
        )

    def _prepare_translate_all_transaction(self, translator_func, on_progress=None):
        staged_data    = bytearray(self.exe_data)
        staged_entries = copy.deepcopy(self.entries)
        staged_by_id   = {entry["string_id"]: entry for entry in staged_entries}
        suffix_ids     = self._suffix_group_ids(self.entries)
        stats          = {"translated": 0, "unchanged": 0, "blank": 0, "suffix_skipped": 0}

        for index, source_entry in enumerate(self.entries):
            if on_progress:
                on_progress(index + 1, len(self.entries),
                            self._decode_entry_text(source_entry))
            if source_entry["string_id"] in suffix_ids:
                stats["suffix_skipped"] += 1
                continue

            original = self._decode_entry_text(source_entry, preserve_controls=True)
            if not original or original.isspace():
                stats["blank"] += 1
                continue

            translated = translator_func(original)
            if not isinstance(translated, str) or not translated:
                raise TextTransactionError(
                    f"Translator returned no text for {source_entry['string_id']}"
                )

            new_bytes = self._encode_entry_text(source_entry, translated)
            old_bytes = self._entry_raw_bytes(source_entry)
            if new_bytes == old_bytes:
                stats["unchanged"] += 1
                continue

            staged_entry = staged_by_id[source_entry["string_id"]]
            staged_entry["text"] = self._raw_text(new_bytes)
            if staged_entry.get("fixed"):
                max_len = staged_entry["max_len"]
                if len(new_bytes) > max_len - 1:
                    raise TextTransactionError(
                        f"Fixed string {staged_entry['string_id']} exceeds {max_len - 1} bytes"
                    )
                address = staged_entry["str_addr"]
                staged_data[address:address + max_len] = (
                    new_bytes + b"\x00" * (max_len - len(new_bytes))
                )
            stats["translated"] += 1

        if stats["translated"] == 0:
            return None, None, {
                "ok": True, "errors": [], "stage": "no-op", "noop": True,
            }, stats

        work_data, work_entries, validation = repack_transaction(
            staged_data, self.profile, staged_entries, self.relocation_sites
        )
        return work_data, work_entries, validation, stats

    def _commit_text_transaction(self, work_data, work_entries, validation):
        self.exe_data[:]         = work_data
        self.entries             = work_entries
        self.validation_errors   = []
        self.integrity_valid     = True
        self.repack_required     = False
        self._recalculate_max_lengths()
        self._invalidate_diff_preview("text-commit", refresh=False)
        self._update_save_state()


__all__ = ["StringCodecMixin", "TextTransactionError"]
