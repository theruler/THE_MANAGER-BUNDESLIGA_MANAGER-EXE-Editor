"""python test_bmh_exe_strings.py [BMH.EXE] [FLTD.EXE] [BMH_1.EXE]
Paths can also be given with the env vars BMH_EXE / FLTD_EXE / BMH1_EXE (defaults: ./BMH.EXE, ./FLTD.EXE, ./BMH_1.EXE;
a missing file just skips its tests)."""
import os, random, struct, sys, unittest
from exe_handler import detect_bmh_exe_profile, LEImage
from bmh_exe_strings import BMHExeStrings, BMHExeError, BMHExeSpaceError, resolve_strings

args = sys.argv[1:]
sys.argv = sys.argv[:1]
PATHS = {"GER": os.environ.get("BMH_EXE") or (args[0] if args else "BMH.EXE"),
         "ENG": os.environ.get("FLTD_EXE") or (args[1] if len(args) > 1 else "FLTD.EXE"),
         "GER37": os.environ.get("BMH1_EXE") or (args[2] if len(args) > 2 else "BMH_1.EXE")}


class Base:
    KEY = None

    @classmethod
    def setUpClass(cls):
        if not os.path.exists(PATHS[cls.KEY]):
            raise unittest.SkipTest(PATHS[cls.KEY] + " not found")
        cls.data = open(PATHS[cls.KEY], "rb").read()

    def setUp(self):
        self.m = BMHExeStrings(self.data)

    def check_pointers(self, out, texts):
        resolved = resolve_strings(out)
        for it, text in zip(self.m.items, texts):
            for f in it.sources:
                self.assertEqual(resolved[f.src_lin], text)

    def test_detect(self):
        self.assertIsNotNone(detect_bmh_exe_profile(self.data))
        self.assertIsNone(detect_bmh_exe_profile(self.data[:0x1000]))

    def test_noop_is_bit_identical(self):
        self.assertEqual(self.m.to_bytes(), self.data)

    def test_save_reopen_cycles(self):
        random.seed(11)
        cur, model = self.data, self.m
        for _ in range(6):
            texts = list(model.strings)
            for i in random.sample(range(len(texts)), max(3, len(texts) // 6)):
                raw = model.items[i].raw
                texts[i] = raw + b"k" * random.randint(1, 9) if random.random() < .5 else raw[:max(2, len(raw) - random.randint(1, 9))]
            try:
                cur = model.apply(texts)
            except BMHExeSpaceError:
                continue
            self.assertEqual(len(cur), len(self.data))
            self.assertIsNotNone(detect_bmh_exe_profile(cur))
            model = BMHExeStrings(cur)
            self.assertEqual(model.strings, texts)
            self.assertEqual(model.apply(model.strings), cur)

    def test_overflow_and_empty(self):
        with self.assertRaises(BMHExeSpaceError):
            self.m.apply([s + b"x" * 400 for s in self.m.strings])
        with self.assertRaises(BMHExeError):
            self.m.apply([b""] + self.m.strings[1:])


class German(Base, unittest.TestCase):
    KEY = "GER"

    def test_growth_moves_only_pointers(self):
        random.seed(7)
        new = list(self.m.strings)
        for i in random.sample(range(len(new)), 80):
            new[i] += b"+" * random.randint(1, 30)
        out = self.m.apply(new)
        self.assertEqual(LEImage(self.data).sources_sha256(), LEImage(out).sources_sha256())
        self.check_pointers(out, new)


class German37(German):
    KEY = "GER37"

    def test_profile(self):
        self.assertEqual(detect_bmh_exe_profile(self.data), "BUNDESLIGA MANAGER HATTRICK (GERMAN V3.7)")


class English(Base, unittest.TestCase):
    KEY = "ENG"

    def test_rearrange_inside_own_space(self):
        new = list(self.m.strings)
        new[34] = new[34][:96]                         # frees 150 bytes ...
        new[8] += b"x" * 40                            # ... used by two longer strings
        new[13] += b"y" * 30
        out = self.m.apply(new)
        self.assertEqual(len(out), len(self.data))
        self.check_pointers(out, new)
        changed = [i for i in range(len(out)) if out[i] != self.data[i]]
        base = 0x496D
        allowed = {p for it in self.m.items for f in it.sources for p in range(f.src_file, f.src_file + 4)}
        for lo, hi in self.m.profile["slot_regions"]:
            allowed.update(range(lo, hi))
        self.assertTrue(all(i in allowed for i in changed))
        self.assertIsNone(self.m.profile["cave"])      # no provably free space in this build


if __name__ == "__main__":
    unittest.main()
