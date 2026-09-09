import struct

POOL_FILL = 0xFF

BMP_V2_EXTENDED = {
    "profile_name": "BUNDESLIGA MANAGER PROFESSIONAL",
    "ds_start": 0x537E0,
    "base_const": bytes.fromhex("B34C"),
    "pool": (0x5ED70, 0x637B9),
    "pool_fill": POOL_FILL,
    "min_file_size": 0x637DF,
    "header_minalloc": 0x0381,
    "header_ss": 0x5CD8,
    "ptr_range_home": {1: 0, 2: 0, 3: 1, 4: 1, 5: 3},
    "newspaper_sources": ((0x58770, 0x58884), (0x5C8B2, 0x5CA6A)),
    "convertible_from": {
        "header_minalloc": 0x0381,
        "header_ss": 0x5709,
    },
}

TM_ITA_EXTENDED = {
    "profile_name": "THE MANAGER (ITALIAN)",
    "ds_start": 0x53CE0,
    "base_const": bytes.fromhex("F64C"),
    "pool": (0x5F680, 0x63CD0), 
    "pool_fill": POOL_FILL,
    "min_file_size": 0x63CDF,
    "header_minalloc": 0x0388, 
    "header_ss": 0x5D1C,     
    "ptr_range_home": {1: 0, 2: 0, 3: 0, 4: 0, 5: 1, 6: 1, 7: 1, 8: 3},
    "newspaper_sources": ((0x58E6A, 0x58F7E), (0x5D1AC, 0x5D364)),
    "convertible_from": {
        "header_minalloc": 0x0388, 
        "header_ss": 0x578D,   
    },
}

TM_ENG_EXTENDED = {
    "profile_name": "THE MANAGER (ENGLISH)",
    "ds_start": 0x52320,
    "base_const": bytes.fromhex("694B"),
    "pool": (0x5D2C0, 0x62310),
    "pool_fill": POOL_FILL,
    "min_file_size": 0x6231F,
    "header_minalloc": 0x0B21,
    "header_ss": 0x5B1C,
    "ptr_range_home": {1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 1, 7: 3},
    "newspaper_sources": ((0x56CB8, 0x56DCC), (0x5ADE8, 0x5AFA0)),
    "convertible_from": {
        "header_minalloc": 0x0B21,
        "header_ss": 0x555F,
    },
}

_LAYOUTS = (BMP_V2_EXTENDED, TM_ITA_EXTENDED, TM_ENG_EXTENDED,)


class ExtendedLayoutError(ValueError):
    pass


class ExtendedLayout:
    def __init__(self, descriptor, profile):
        self.descriptor = descriptor
        self.profile = profile
        self.profile_name = descriptor["profile_name"]
        self.pool_start, self.pool_end = descriptor["pool"]
        self.fill = descriptor["pool_fill"]
        self.ptr_range_home = dict(descriptor["ptr_range_home"])
        self.newspaper_sources = tuple(descriptor["newspaper_sources"])

    @property
    def pool_size(self):
        return self.pool_end - self.pool_start

    def in_pool(self, address):
        return self.pool_start <= address < self.pool_end

    def ptr_range_index(self, source):
        for index, (start, end) in enumerate(self.profile.get("ptr_ranges", ())):
            if start <= source < end:
                return index
        return None

    def home_range_index(self, entry):
        sources = sorted(set(entry.get("ptr_addrs", [])))
        if not sources:
            return None
        home = None
        for source in sources:
            index = self.ptr_range_index(source)
            if index is None:
                return None
            mapped = self.ptr_range_home.get(index)
            if mapped is None:
                return None
            if home is not None and home != mapped:
                return None
            home = mapped
        return home

    def is_newspaper_source(self, source):
        return any(start <= source < end for start, end in self.newspaper_sources)

    def is_spillable(self, entry):
        if entry.get("fixed") or entry.get("_shared_parent"):
            return False
        sources = sorted(set(entry.get("ptr_addrs", [])))
        if len(sources) != 1 or entry.get("code_ptr_addrs"):
            return False
        return True

    def home_map_errors(self, inventory):
        errors, observed = [], {}
        for source, target in inventory.get("normal", {}).items():
            index = self.ptr_range_index(source)
            if index is None or self.in_pool(target):
                continue
            for range_index, (start, end) in enumerate(self.profile["valid_ranges"]):
                if start <= target < end:
                    observed.setdefault(index, set()).add(range_index)
                    break
        for index, targets in sorted(observed.items()):
            if len(targets) > 1:
                errors.append(f"ptr_ranges[{index}] feeds several blocks: {sorted(targets)}")
                continue
            expected = self.ptr_range_home.get(index)
            actual = next(iter(targets))
            if expected is not None and expected != actual:
                errors.append(
                    f"ptr_ranges[{index}] home block is {actual}, extended layout says {expected}"
                )
        return errors


def _read_u16(data, offset):
    return struct.unpack_from("<H", data, offset)[0]


def _write_u16(data, offset, value):
    struct.pack_into("<H", data, offset, value)


def layout_for_profile(profile):
    if profile is None:
        return None
    for descriptor in _LAYOUTS:
        if profile.get("ds_start") != descriptor["ds_start"]:
            continue
        if bytes(profile.get("base_const") or b"") != descriptor["base_const"]:
            continue
        return ExtendedLayout(descriptor, profile)
    return None


def detect(data, profile):
    if profile is None or len(data) < 0x20:
        return None
    for descriptor in _LAYOUTS:
        if profile.get("ds_start") != descriptor["ds_start"]:
            continue
        if bytes(profile.get("base_const") or b"") != descriptor["base_const"]:
            continue
        if len(data) < descriptor["min_file_size"]:
            continue
        if _read_u16(data, 0x0A) != descriptor["header_minalloc"]:
            continue
        if _read_u16(data, 0x0E) != descriptor["header_ss"]:
            continue
        pool_start, pool_end = descriptor["pool"]
        if pool_end > len(data):
            continue
        return ExtendedLayout(descriptor, profile)
    return None


def can_convert(data, profile):
    if profile is None or len(data) < 0x20:
        return None
    for descriptor in _LAYOUTS:
        conv = descriptor.get("convertible_from")
        if not conv:
            continue
        if profile.get("ds_start") != descriptor["ds_start"]:
            continue
        if bytes(profile.get("base_const") or b"") != descriptor["base_const"]:
            continue
        if _read_u16(data, 0x0A) != conv["header_minalloc"]:
            continue
        if _read_u16(data, 0x0E) != conv["header_ss"]:
            continue
        # Non deve essere già extended
        if detect(data, profile) is not None:
            return None
        return descriptor
    return None


def convert_to_extended(data, profile):
    descriptor = can_convert(data, profile)
    if descriptor is None:
        raise ExtendedLayoutError("This EXE is not convertible to extended layout")

    result = bytearray(data)
    import struct
    pool_start, pool_end = descriptor["pool"]
    needed = descriptor["min_file_size"]
    if len(result) < needed:
        result.extend(b"\x00" * (needed - len(result)))
    result[pool_start:pool_end] = bytes([descriptor["pool_fill"]]) * (pool_end - pool_start)
    _write_u16(result, 0x0A, descriptor["header_minalloc"])
    _write_u16(result, 0x0E, descriptor["header_ss"])
    total_size = len(result)
    last_page_bytes = total_size % 512
    total_pages = (total_size + 511) // 512
    _write_u16(result, 0x02, last_page_bytes)
    _write_u16(result, 0x04, total_pages)

    extended = ExtendedLayout(descriptor, profile)
    return result, extended


__all__ = [
    "ExtendedLayout",
    "ExtendedLayoutError",
    "detect",
    "layout_for_profile",
    "can_convert",
    "convert_to_extended",
    "POOL_FILL",
    "BMP_V2_EXTENDED", "TM_ITA_EXTENDED", "TM_ENG_EXTENDED",
]