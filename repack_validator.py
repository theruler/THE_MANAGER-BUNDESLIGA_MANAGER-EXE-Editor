import copy
import struct
from i18n import tr


def _strict_text_bytes(entry):
    try:
        return entry["text"].encode("latin-1")
    except UnicodeEncodeError as exc:
        string_id = entry.get("string_id", f"address {entry.get('str_addr', -1):#x}")
        raise ValueError(tr("repack.err.encoding", sid=string_id)) from exc


def _text_encoding_errors(entries):
    errors = []
    for entry in entries:
        try:
            _strict_text_bytes(entry)
        except ValueError as exc:
            errors.append(str(exc))
    return errors


def _inside_ranges(profile, address):
    return any(start <= address < end for start, end in profile["valid_ranges"])


def _range_index(profile, address):
    for index, (start, end) in enumerate(profile["valid_ranges"]):
        if start <= address < end:
            return index
    return None


def make_string_id(entry):
    if entry.get("fixed"):
        return f"fixed:0x{entry['original_str_addr']:X}"
    ptr_addrs = sorted(set(entry.get("ptr_addrs", [])))
    if ptr_addrs:
        return f"ptr:0x{ptr_addrs[0]:X}"
    code_addrs = sorted(set(entry.get("code_ptr_addrs", [])))
    if code_addrs:
        return f"code:0x{code_addrs[0]:X}"
    raise ValueError(f"Entry at {entry.get('str_addr', -1):#x} has no stable source")


def build_reference_inventory(data, profile, relocation_sites):
    normal, code, errors = {}, {}, []
    base_const = profile["base_const"]
    ds_start = profile["ds_start"]

    for site in sorted(set(relocation_sites)):
        if site < 0 or site + 2 > len(data):
            errors.append(tr("repack.err.site_outside", addr=site))
            continue
        if bytes(data[site:site + 2]) != base_const:
            continue

        code_source = site - 3
        is_mov_pair = (
            code_source >= 1
            and code_source + 5 <= len(data)
            and 0xB8 <= data[code_source - 1] <= 0xBF
            and 0xB8 <= data[code_source + 2] <= 0xBF
        )
        if is_mov_pair:
            target = ds_start + struct.unpack_from("<H", data, code_source)[0]
            if _inside_ranges(profile, target):
                code[code_source] = target
                continue

        ptr_source = site - 2
        if ptr_source < 0 or ptr_source + 4 > len(data):
            continue
        target = ds_start + struct.unpack_from("<H", data, ptr_source)[0]
        if _inside_ranges(profile, target):
            normal[ptr_source] = target

    expected_code = dict(profile.get("code_ptrs", []))
    if code != expected_code:
        missing = sorted(set(expected_code) - set(code))
        extra = sorted(set(code) - set(expected_code))
        mismatched = sorted(source for source in set(code) & set(expected_code)
                            if code[source] != expected_code[source])
        if missing:
            addrs = ", ".join(f"{x:#x}" for x in missing)
            errors.append(tr("repack.err.missing_code_ptrs", addrs=addrs))
        if extra:
            addrs = ", ".join(f"{x:#x}" for x in extra)
            errors.append(tr("repack.err.extra_code_ptrs", addrs=addrs))
        if mismatched:
            addrs = ", ".join(f"{x:#x}" for x in mismatched)
            errors.append(tr("repack.err.mismatched_ptrs", addrs=addrs))

    return {
        "normal": normal,
        "code": code,
        "errors": errors,
        "normal_count": len(normal),
        "code_count": len(code),
    }


def _validate_reference_ownership(entries, inventory):
    errors, normal_owner, code_owner = list(inventory.get("errors", [])), {}, {}
    ids = set()

    for entry in entries:
        string_id = entry.get("string_id")
        if not string_id:
            errors.append(tr("repack.err.no_sid", addr=entry.get('str_addr', -1)))
        elif string_id in ids:
            errors.append(tr("repack.err.dup_sid", sid=string_id))
        else:
            ids.add(string_id)

        if entry.get("fixed"):
            if entry.get("ptr_addrs") or entry.get("code_ptr_addrs"):
                errors.append(tr("repack.err.fixed_has_ptrs", sid=string_id))
            continue

        target = entry["str_addr"]
        for source in entry.get("ptr_addrs", []):
            if source in normal_owner:
                errors.append(tr("repack.err.dup_normal_src", addr=source))
            normal_owner[source] = string_id
            expected = inventory["normal"].get(source)
            if expected is None:
                errors.append(tr("repack.err.uninv_normal_src", addr=source))
            elif expected != target:
                errors.append(tr("repack.err.normal_target", src=source, expected=expected, actual=target))

        for source in entry.get("code_ptr_addrs", []):
            if source in code_owner:
                errors.append(tr("repack.err.dup_code_src", addr=source))
            code_owner[source] = string_id
            expected = inventory["code"].get(source)
            if expected is None:
                errors.append(tr("repack.err.uninv_code_src", addr=source))
            elif expected != target:
                errors.append(tr("repack.err.code_target", src=source, expected=expected, actual=target))

    missing_normal = sorted(set(inventory["normal"]) - set(normal_owner))
    missing_code = sorted(set(inventory["code"]) - set(code_owner))
    if missing_normal:
        errors.append(tr("repack.err.unowned_normal", n=len(missing_normal)))
    if missing_code:
        errors.append(tr("repack.err.unowned_code", n=len(missing_code)))
    return errors


def _validate_layout(data, profile, entries):
    errors, intervals, encoded_by_entry = [], [], {}
    fixed_by_addr = {address: max_len for address, max_len in profile.get("fixed_strings", [])}

    for entry in entries:
        address = entry["str_addr"]
        try:
            encoded = _strict_text_bytes(entry)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        encoded_by_entry[id(entry)] = encoded
        expected = encoded + b"\x00"

        if entry.get("fixed"):
            max_len = fixed_by_addr.get(address)
            if max_len is None:
                errors.append(tr("repack.err.unknown_fixed", addr=address))
                continue
            if len(expected) > max_len:
                errors.append(tr("repack.err.fixed_slot_size", addr=address))
                continue
            if bytes(data[address:address + len(expected)]) != expected:
                errors.append(tr("repack.err.fixed_mismatch", addr=address))
            continue

        range_index = _range_index(profile, address)
        if range_index is None:
            errors.append(tr("repack.err.outside_ranges", addr=address))
            continue
        range_start, range_end = profile["valid_ranges"][range_index]
        end = address + len(expected)
        if end > range_end:
            errors.append(tr("repack.err.crosses_range", start=address, end=end))
            continue
        if bytes(data[address:end]) != expected:
            errors.append(tr("repack.err.bytes_mismatch", addr=address))
            continue
        intervals.append((address, end, entry, range_index))

    ordered = sorted(intervals, key=lambda item: (item[3], item[0], item[1]))
    for index, current in enumerate(ordered):
        c_start, c_end, c_entry, c_range = current
        for previous in ordered[:index]:
            p_start, p_end, p_entry, p_range = previous
            if p_range != c_range or p_end <= c_start:
                continue
            allowed_suffix = (
                p_start < c_start
                and p_end == c_end
                and encoded_by_entry[id(c_entry)]
                    == encoded_by_entry[id(p_entry)][c_start - p_start:]
            )
            if not allowed_suffix:
                errors.append(tr("repack.err.illegal_overlap", a_start=p_start, a_end=p_end, b_start=c_start, b_end=c_end))

    for range_index, (range_start, range_end) in enumerate(profile["valid_ranges"]):
        covered = bytearray(range_end - range_start)
        for start, end, _entry, entry_range in intervals:
            if entry_range != range_index:
                continue
            covered[start - range_start:end - range_start] = b"\x01" * (end - start)
        unknown = [address for address in range(range_start, range_end)
                   if data[address] != 0 and not covered[address - range_start]]
        if unknown:
            errors.append(tr("repack.err.unknown_bytes", idx=range_index, n=len(unknown), addr=unknown[0]))
    return errors


def validate_image(data, profile, entries, relocation_sites):
    inventory = build_reference_inventory(data, profile, relocation_sites)
    errors = _validate_reference_ownership(entries, inventory)
    errors.extend(_validate_layout(data, profile, entries))
    return {
        "ok": not errors,
        "errors": errors,
        "inventory": inventory,
        "normal_count": inventory["normal_count"],
        "code_count": inventory["code_count"],
        "entry_count": len(entries),
    }


def _mark_suffix_sharing(entries, profile):
    for entry in entries:
        entry.pop("_shared_parent", None)
        entry.pop("_shared_offset", None)
        entry.pop("_placed", None)

    for range_index, _range in enumerate(profile["valid_ranges"]):
        group = sorted(
            (entry for entry in entries if not entry.get("fixed")
             and _range_index(profile, entry["str_addr"]) == range_index),
            key=lambda item: item["str_addr"],
        )
        for child in group:
            candidates = []
            child_bytes = _strict_text_bytes(child)
            for parent in group:
                offset = child["str_addr"] - parent["str_addr"]
                parent_bytes = _strict_text_bytes(parent)
                if 0 < offset < len(parent_bytes) and child_bytes == parent_bytes[offset:]:
                    candidates.append((parent["str_addr"], parent, offset))
            if candidates:
                _address, parent, offset = max(candidates, key=lambda item: item[0])
                child["_shared_parent"] = parent
                child["_shared_offset"] = offset


def repack_transaction(data, profile, entries, relocation_sites):
    encoding_errors = _text_encoding_errors(entries)
    if encoding_errors:
        return None, None, {
            "ok": False,
            "errors": encoding_errors,
            "stage": "encoding",
        }
    before = bytearray(data)
    before_inventory = build_reference_inventory(before, profile, relocation_sites)
    source_errors = _validate_reference_ownership(entries, before_inventory)
    if source_errors:
        return None, None, {"ok": False, "errors": source_errors, "stage": "source-inventory"}

    work_data = bytearray(before)
    work_entries = copy.deepcopy(entries)
    _mark_suffix_sharing(work_entries, profile)

    groups = [[] for _ in profile["valid_ranges"]]
    for entry in work_entries:
        if entry.get("fixed"):
            continue
        range_index = _range_index(profile, entry["str_addr"])
        if range_index is None:
            return None, None, {"ok": False, "errors": [tr("repack.err.entry_outside", addr=entry['str_addr'])], "stage": "layout"}
        groups[range_index].append(entry)

    for range_index, group in enumerate(groups):
        range_start, range_end = profile["valid_ranges"][range_index]
        writable = [entry for entry in group if not entry.get("_shared_parent")]
        required = sum(len(_strict_text_bytes(entry)) + 1 for entry in writable)
        if required > range_end - range_start:
            return None, None, {
                "ok": False,
                "errors": [tr("repack.err.range_overflow", idx=range_index, required=required, total=range_end - range_start)],
                "stage": "capacity",
            }

        work_data[range_start:range_end] = b"\x00" * (range_end - range_start)
        write_ptr = range_start
        for entry in sorted(writable, key=lambda item: item["str_addr"]):
            encoded = _strict_text_bytes(entry) + b"\x00"
            work_data[write_ptr:write_ptr + len(encoded)] = encoded
            entry["str_addr"] = write_ptr
            entry["slot_len"] = len(encoded)
            entry["_placed"] = True
            write_ptr += len(encoded)

        unresolved = [entry for entry in group if entry.get("_shared_parent")]
        while unresolved:
            progress = False
            for entry in list(unresolved):
                parent = entry["_shared_parent"]
                if not parent.get("_placed"):
                    continue
                entry["str_addr"] = parent["str_addr"] + entry["_shared_offset"]
                entry["slot_len"] = parent["slot_len"] - entry["_shared_offset"]
                entry["_placed"] = True
                unresolved.remove(entry)
                progress = True
            if not progress:
                return None, None, {"ok": False, "errors": [tr("repack.err.suffix_chain")], "stage": "layout"}

    base_const = profile["base_const"]
    ds_start = profile["ds_start"]
    for entry in work_entries:
        if entry.get("fixed"):
            continue
        ptr_value = entry["str_addr"] - ds_start
        if not 0 <= ptr_value <= 0xFFFF:
            return None, None, {"ok": False, "errors": [tr("repack.err.ptr_value_range", value=ptr_value)], "stage": "pointers"}
        for source in entry.get("ptr_addrs", []):
            if source < 0 or source + 4 > len(work_data):
                return None, None, {"ok": False, "errors": [tr("repack.err.normal_src_file", addr=source)], "stage": "pointers"}
            struct.pack_into("<H", work_data, source, ptr_value)
            work_data[source + 2:source + 4] = base_const
        for source in entry.get("code_ptr_addrs", []):
            if source < 1 or source + 5 > len(work_data):
                return None, None, {"ok": False, "errors": [tr("repack.err.code_src_file", addr=source)], "stage": "pointers"}
            struct.pack_into("<H", work_data, source, ptr_value)
            work_data[source + 3:source + 5] = base_const

    validation = validate_image(work_data, profile, work_entries, relocation_sites)
    validation["stage"] = "output"

    allowed = set()
    for start, end in profile["valid_ranges"]:
        allowed.update(range(start, end))
    for source in before_inventory["normal"]:
        allowed.update((source, source + 1))
    for source in before_inventory["code"]:
        allowed.update((source, source + 1))
    extra_diffs = [index for index, (old, new) in enumerate(zip(before, work_data))
                   if old != new and index not in allowed]
    if len(before) != len(work_data):
        validation["errors"].append(tr("repack.err.file_size_changed"))
    if extra_diffs:
        validation["errors"].append(tr("repack.err.extra_diffs", n=len(extra_diffs), addr=extra_diffs[0]))
    validation["extra_diffs"] = len(extra_diffs)
    validation["ok"] = not validation["errors"]
    return (work_data, work_entries, validation) if validation["ok"] else (None, None, validation)


__all__ = [
    "build_reference_inventory",
    "make_string_id",
    "repack_transaction",
    "validate_image",
]
