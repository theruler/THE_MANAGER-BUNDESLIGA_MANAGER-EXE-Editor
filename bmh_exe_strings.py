"""Bundesliga Manager Hattrick - strings stored inside the DOS/4GW (LE) executable.

How it works
------------
* Two executable formats are supported (see exe_handler.BMH_EXE_PROFILES):
    - "le"   (BMH.EXE, DOS/4GW): every string is reached through an LE fixup record
    - "flat" (FLTD.EXE, flat image without relocation tables): pointer slots listed in the profile
* LE format: every string of the EXE is reached through an LE fixup record (type "32-bit offset",
  internal reference).  A fixup stores (target object, target offset); the loader
  overwrites the pointer with  base(object) + offset  at start-up.
* A string whose new text still fits its original slot (text + NUL) is written in place.
* A longer string is moved: the old slot is zeroed and becomes free space, the string is
  written in a free interval and ONLY the target (object, offset) of its fixup records is
  patched.  Fixup records keep their size, so no table is rebuilt and the file size never changes.
* Free intervals = the old slots of the moved strings + the optional "cave" of the profile.  German
  build: the zeroed tail of the object-3 page (nothing references it).  English build: no cave
  (no provably free space), so strings can only be rearranged inside their own slots.

Pure logic, no tkinter: the panel in bmh_editor.py only displays/edits it.
"""
import struct
from exe_handler import BMH_EXE_PROFILES, detect_bmh_exe_profile, open_bmh_image


class BMHExeError(ValueError):
    pass


class BMHExeSpaceError(BMHExeError):
    pass


class ExeItem:
    __slots__ = ("obj", "off", "raw", "sources", "locked", "reason", "order", "pad")

    @property
    def slot(self):                      # text + NUL + the 0x00 padding that follows it (unreferenced)
        return len(self.raw) + 1 + self.pad


class _Plan:
    def __init__(self):
        self.in_place = []               # item indexes written over their own slot
        self.moved = {}                  # item index -> (obj, off)
        self.repacked = False            # True when every string was laid out again
        self.cave_used = 0               # bytes of the cave occupied after the plan
        self.cave_total = 0
        self.unchanged = 0


class BMHExeStrings:
    """Model used by BMHExeStringsPanel (it mimics the TextDb attributes the panel relies on)."""

    def __init__(self, data, profile_name=None):
        self.data = bytes(data)
        self.profile_name = profile_name or detect_bmh_exe_profile(self.data)
        if self.profile_name is None:
            raise BMHExeError("This executable is not a supported Bundesliga Manager Hattrick build")
        self.profile = BMH_EXE_PROFILES[self.profile_name]
        self.image = open_bmh_image(self.data, self.profile)
        self._cave = self.profile.get("cave")
        self._build_items()
        self.strings = [it.raw for it in self.items]

    # ------------------------------------------------------------ discovery
    def _file_offset(self, obj, off):
        try:
            return self.image.object_to_file(obj, off)
        except ValueError:
            return None

    def _in_ranges(self, file_off, ranges):
        return any(a <= file_off <= b for a, b in ranges)

    def _is_candidate(self, f):
        if f.kind != 7 or f.toff is None:
            return False
        if self._cave and f.tobj == self._cave["object"]:
            return self._cave["start"] <= f.toff < self._cave["end"]
        if f.tobj == self.profile["string_object"]:
            fo = self._file_offset(f.tobj, f.toff)
            return fo is not None and self._in_ranges(fo, self.profile["string_ranges"])
        return False

    def _read_cstring(self, obj, off):
        start = self._file_offset(obj, off)
        if start is None:
            return None
        end = self.data.find(b"\0", start)
        limit = self.image.object_file_offset(obj) + self.image.objects[obj - 1]["count"] * self.image.page_size
        if end < 0 or end >= limit:
            return None
        return self.data[start:end]

    def _build_items(self):
        groups = {}
        for f in self.image.fixups:
            if self._is_candidate(f):
                groups.setdefault((f.tobj, f.toff), []).append(f)
        locked_ranges = self.profile["locked_ranges"]
        everything = []
        for (obj, off), sources in groups.items():
            raw = self._read_cstring(obj, off)
            if not raw:                                      # empty / unterminated: nothing to translate
                continue
            it = ExeItem()
            it.obj, it.off, it.raw, it.sources = obj, off, raw, sources
            it.locked, it.reason, it.pad = False, "", 0
            fo = self._file_offset(obj, off)
            if self._in_ranges(fo, locked_ranges):
                it.locked, it.reason = True, "locked range"
            elif any(s.additive for s in sources):
                it.locked, it.reason = True, "additive fixup"
            it.order = min(s.src_lin for s in sources)
            everything.append(it)
        # an item that starts inside another item's slot shares its bytes: pin both
        spans = sorted(((it.obj, it.off, it.off + len(it.raw) + 1, it) for it in everything), key=lambda t: t[:2])
        for a, b in zip(spans, spans[1:]):
            if a[0] == b[0] and b[1] < a[2]:
                for it in (a[3], b[3]):
                    it.locked, it.reason = True, "overlapping string"
        self._claim_padding(everything)
        self.all_items = sorted(everything, key=lambda it: it.order)
        self.items = [it for it in self.all_items if not it.locked]
        self.locked_count = len(self.all_items) - len(self.items)

    def _reference_offsets(self):
        """File offsets that anything could point at inside the string object (stops padding claims)."""
        refs = set()
        so = self.profile["string_object"]
        for f in self.image.fixups:
            if f.tobj == so and f.toff is not None:
                fo = self._file_offset(so, f.toff)
                if fo is not None:
                    refs.add(fo)
        if hasattr(self.image, "scan_references"):
            refs |= self.image.scan_references(self.data, self.profile["string_ranges"])
        return refs

    def _claim_padding(self, items):
        """Zero bytes right after a string's NUL belong to it, up to the next possible reference."""
        refs = self._reference_offsets()
        ranges = self.profile["string_ranges"]
        for it in items:
            if it.locked:
                continue
            start = self._file_offset(it.obj, it.off)
            limit = next((b for a, b in ranges if a <= start <= b), start)
            pos = start + len(it.raw) + 1
            while pos <= limit and self.data[pos] == 0 and pos not in refs:
                pos += 1
            it.pad = pos - (start + len(it.raw) + 1)

    # ----------------------------------------------------- panel-facing API
    @property
    def offsets(self):
        return [self._file_offset(it.obj, it.off) for it in self.items]

    def slot_sizes(self):
        return [it.slot for it in self.items]

    def to_bytes(self) -> bytes:
        return self.apply(self.strings)

    # ------------------------------------------------------------- planning
    def _regions(self):
        """Space of the translatable strings as laid out in the original EXE (profile 'slot_regions')."""
        out = []
        for a, b in self.profile.get("slot_regions", ()):
            lo, hi = self.image.file_to_object(a), self.image.file_to_object(b - 1)
            if lo and hi and lo[0] == hi[0]:
                out.append((lo[0], lo[1], hi[1] + 1))
        return out

    def _cave_interval(self):
        c = self._cave
        return (c["object"], c["start"], c["end"]) if c else None

    def plan(self, strings) -> _Plan:
        """Fewest pointer changes first; when the free space is too fragmented, lay every string out again."""
        try:
            return self._plan(strings, repack=False)
        except BMHExeSpaceError as first:
            try:
                return self._plan(strings, repack=True)
            except BMHExeSpaceError:
                raise first

    def _plan(self, strings, repack) -> _Plan:
        if len(strings) != len(self.items):
            raise BMHExeError("string count mismatch")
        plan = _Plan()
        plan.repacked = repack
        moving = []
        for i, (it, new) in enumerate(zip(self.items, strings)):
            if b"\0" in new:
                raise BMHExeError("a string contains a NUL byte")
            if not new:
                raise BMHExeError("empty strings are not supported (it could not be edited again); use a space")
            if repack:
                moving.append(i)
            elif new == it.raw:
                plan.unchanged += 1
            elif len(new) + 1 <= it.slot:
                plan.in_place.append(i)
            else:
                moving.append(i)
        moving_set = set(moving)
        cave = self._cave_interval()
        cobj, cstart, cend = cave if cave else (None, 0, 0)
        # universe = cave + the extent (text, NUL, padding) of every listed string;
        # occupied = what the listed strings that stay put really need; the rest is free.
        universe = [(it.obj, it.off, it.off + it.slot) for it in self.items] + self._regions()
        occupied = []
        for i, it in enumerate(self.items):
            if i not in moving_set:
                occupied.append((it.obj, it.off, it.off + len(strings[i]) + 1))
        for it in self.all_items:
            if it.locked:
                occupied.append((it.obj, it.off, it.off + len(it.raw) + 1))
        if cave:
            universe.append(cave)
        free = self._subtract(self._merge(universe), self._merge(occupied))
        plan.cave_total = cend - cstart
        for i in sorted(moving, key=lambda k: -len(strings[k])):
            need = len(strings[i]) + 1
            fits = [iv for iv in free if iv[2] - iv[1] >= need]
            if not fits:
                raise BMHExeSpaceError(
                    "Not enough free space in the executable for string #%d (%d bytes needed, "
                    "largest free block: %d bytes)." % (i, need, max((iv[2] - iv[1] for iv in free), default=0)))
            iv = min(fits, key=lambda v: (v[2] - v[1], v[0], v[1]))
            free.remove(iv)
            plan.moved[i] = (iv[0], iv[1])
            if iv[1] + need < iv[2]:
                free.append((iv[0], iv[1] + need, iv[2]))
        used = 0
        if cave:
            used = sum(b - a for o, a, b in occupied if o == cobj and cstart <= a < cend)
            used += sum(len(strings[i]) + 1 for i, (o, _) in plan.moved.items() if o == cobj)
        plan.cave_used = used
        return plan

    @staticmethod
    def _subtract(intervals, holes):
        out = []
        for obj, a, b in intervals:
            cur = a
            for o2, c, d in sorted(h for h in holes if h[0] == obj and h[2] > a and h[1] < b):
                if c > cur:
                    out.append((obj, cur, c))
                cur = max(cur, d)
            if cur < b:
                out.append((obj, cur, b))
        return out

    @staticmethod
    def _merge(intervals):
        out = []
        for obj, a, b in sorted(intervals):
            if out and out[-1][0] == obj and out[-1][2] >= a:
                out[-1] = (obj, out[-1][1], max(out[-1][2], b))
            else:
                out.append((obj, a, b))
        return out

    # ------------------------------------------------------------- applying
    def apply(self, strings) -> bytes:
        plan = self.plan(strings)
        out = bytearray(self.data)
        # 1) zero the slots that change owner, 2) write the strings, 3) patch the fixups
        for i in list(plan.moved) + plan.in_place:
            it = self.items[i]
            fo = self._file_offset(it.obj, it.off)
            out[fo:fo + it.slot] = bytes(it.slot)
        for i in plan.in_place:
            it = self.items[i]
            fo = self._file_offset(it.obj, it.off)
            out[fo:fo + len(strings[i])] = strings[i]
        for i, (obj, off) in plan.moved.items():
            fo = self._file_offset(obj, off)
            out[fo:fo + len(strings[i])] = strings[i]
            for f in self.items[i].sources:
                self._patch_fixup(out, f, obj, off)
        result = bytes(out)
        self.verify(result, strings)
        return result

    def verify(self, out, strings):
        """Self-check of a written image (the BMH counterpart of repack_validator.validate_image):
        the file keeps its size, re-opening it gives back exactly `strings`, every pointer the model
        does not own still has its original target, and bytes changed only inside the string space,
        the cave and the pointer fields of the strings that were written."""
        fail = lambda why: BMHExeError("Self-check failed, nothing was written: " + why)
        if len(out) != len(self.data):
            raise fail("the file size changed")
        try:
            check = BMHExeStrings(out, self.profile_name)
        except BMHExeError as exc:
            raise fail(str(exc))
        if check.strings != list(strings):
            raise fail("re-reading the image does not give back the edited strings")
        owned = {id(f) for it in self.items for f in it.sources}
        after = {(f.src_lin, f.kind): (f.tobj, f.toff) for f in check.image.fixups}
        for f in self.image.fixups:
            if id(f) not in owned and after.get((f.src_lin, f.kind)) != (f.tobj, f.toff):
                raise fail("a pointer that does not belong to the strings changed (source 0x%X)" % f.src_lin)
        allowed = set()
        for it in self.items:
            fo = self._file_offset(it.obj, it.off)
            allowed.update(range(fo, fo + it.slot))
            for f in it.sources:
                allowed.update(range(f.src_file, f.src_file + 4))
                for pos, size in ((f.obj_pos, f.obj_size), (f.off_pos, f.off_size)):
                    if pos is not None:
                        allowed.update(range(pos, pos + size))
        for obj, a, b in self._regions() + ([self._cave_interval()] if self._cave else []):
            allowed.update(range(self._file_offset(obj, a), self._file_offset(obj, b - 1) + 1))
        for index, (before, now) in enumerate(zip(self.data, out)):
            if before != now and index not in allowed:
                raise fail("byte 0x%X changed outside the string space" % index)
        return True

    @staticmethod
    def _patch_fixup(out, f, obj, off):
        if off >= 1 << (8 * f.off_size) or (f.obj_size and obj >= 1 << (8 * f.obj_size)):
            raise BMHExeError("fixup field too small for target %d:%#x" % (obj, off))
        if f.obj_size:
            out[f.obj_pos:f.obj_pos + f.obj_size] = obj.to_bytes(f.obj_size, "little")
        out[f.off_pos:f.off_pos + f.off_size] = off.to_bytes(f.off_size, "little")
        stored = struct.unpack_from("<I", out, f.src_file)[0]
        if stored == f.toff:                                  # keep the in-page copy coherent
            struct.pack_into("<I", out, f.src_file, off)

    # ---------------------------------------------------------------- info
    def status(self, index, new):
        """'same' | 'in place' | 'moved' for one string against the loaded layout."""
        it = self.items[index]
        if new == it.raw:
            return "same"
        return "in place" if len(new) + 1 <= it.slot else "moved"

    def space_info(self, strings):
        """Numbers for the space display.  capacity = slots of the listed strings + the cave;
        used = bytes of the current texts (incl. NULs).  ok is False when the strings cannot be placed."""
        regions = self._merge(self._regions() + [(it.obj, it.off, it.off + it.slot) for it in self.items])
        slots = sum(b - a for _, a, b in regions)
        cave = (self._cave["end"] - self._cave["start"]) if self._cave else 0
        used = sum(len(s) + 1 for s in strings)
        info = {"slots": slots, "cave": cave, "capacity": slots + cave, "used": used,
                "free": slots + cave - used, "moved": 0, "cave_used": 0, "ok": True, "error": ""}
        try:
            plan = self.plan(strings)
            info["moved"], info["cave_used"] = len(plan.moved), plan.cave_used
        except BMHExeSpaceError as exc:
            info["ok"], info["error"] = False, str(exc)
        return info

    def summary(self, strings):
        info = self.space_info(strings)
        if not info["ok"]:
            return False, info["error"]
        return True, "moved %d - EXE free space used %d / %d bytes" % (
            info["moved"], info["cave_used"], info["cave"])

    def repacked(self, strings):
        try:
            return self.plan(strings).repacked
        except BMHExeError:
            return False


def resolve_strings(data):
    """Independent check helper: {pointer source (image address): C string} for every string pointer
    the profile knows about (all LE fixups of the German build, the listed slots of the English one)."""
    data = bytes(data)
    name = detect_bmh_exe_profile(data)
    if name is None:
        raise BMHExeError("unsupported executable")
    image = open_bmh_image(data, BMH_EXE_PROFILES[name])
    result = {}
    for f in image.fixups:
        if f.kind == 7 and f.toff is not None:
            try:
                fo = image.object_to_file(f.tobj, f.toff)
            except ValueError:
                continue
            result[f.src_lin] = data[fo:data.find(b"\0", fo)]
    return result
