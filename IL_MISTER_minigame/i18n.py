import importlib.util
import os
import sys

LANG_SUBDIR = os.path.join("data", "lang")
FALLBACK_LANGUAGE = "en"
DEFAULT_PREFIX = "mister_lang_"
_SUFFIX = ".py"
_ROLE_CODES = {"GK", "DEF", "MID", "FWD"}


def _program_dir() -> str:
    """Return the folder containing the executable or source module."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir() -> str:
    """Return PyInstaller's extraction folder, or the source folder."""
    base = getattr(sys, "_MEIPASS", None)
    return os.path.abspath(base) if base else os.path.dirname(os.path.abspath(__file__))


def _language_dirs():
    """Return language roots in priority order: beside EXE, then bundled."""
    result = []
    for base in (_program_dir(), _bundle_dir()):
        base = os.path.abspath(base)
        key = os.path.normcase(base)
        if key not in {os.path.normcase(p) for p in result}:
            result.append(base)
    return result


def _load_module(path: str, modname: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise ImportError("no loader for %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Translator:
    """Load and manage translation dictionaries stored in data/lang."""

    def __init__(self, prefix: str = DEFAULT_PREFIX):
        self.prefix = prefix or DEFAULT_PREFIX
        self.current = FALLBACK_LANGUAGE
        self.problems = []
        self._reset()

    def _reset(self):
        self._tables = {}
        self._failed = set()
        self._paths = {}
        self._names = {}

    def configure(self, prefix: str = None) -> None:
        if prefix:
            self.prefix = prefix
        self._reset()

    def _lang_file(self, base: str, code: str) -> str:
        return os.path.join(base, LANG_SUBDIR, self.prefix + code + _SUFFIX)

    def _candidate_files(self, code: str):
        """Return existing files, external override first and bundle second."""
        found = []
        seen = set()
        for base in _language_dirs():
            path = self._lang_file(base, code)
            key = os.path.normcase(os.path.abspath(path))
            if key not in seen:
                seen.add(key)
                if os.path.isfile(path):
                    found.append(path)
        return found

    def _read_table(self, path: str, code: str):
        try:
            module = _load_module(path, "_il_mister_lang_%s_%s" % (self.prefix, code))
            table = getattr(module, "TEXTS_" + code.upper(), None)
            if table is None:
                table = getattr(module, "TEXTS", None)
            if not isinstance(table, dict) or not table:
                raise ValueError("TEXTS_%s missing or empty" % code.upper())
            for key, value in table.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("non-string entry for %r" % (key,))
            name = getattr(module, "LANG_NAME", None)
            return table, name if isinstance(name, str) and name else None
        except Exception as exc:  # A damaged translation must not stop the game.
            self.problems.append("%s: %s" % (os.path.basename(path), exc))
            return None, None

    def _load_language(self, code: str):
        """Load a language once, trying an external file before the bundle."""
        if code in self._tables:
            return self._tables[code]
        if code in self._failed:
            return None
        for path in self._candidate_files(code):
            table, name = self._read_table(path, code)
            if table is not None:
                self._tables[code] = table
                self._paths[code] = path
                self._names[code] = name
                return table
        self._failed.add(code)
        return None

    def available_languages(self) -> set:
        codes = set()
        for base in _language_dirs():
            folder = os.path.join(base, LANG_SUBDIR)
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if name.startswith(self.prefix) and name.endswith(_SUFFIX):
                    code = name[len(self.prefix):-len(_SUFFIX)]
                    if code and self._load_language(code) is not None:
                        codes.add(code)
        if self._load_language(FALLBACK_LANGUAGE) is not None:
            codes.add(FALLBACK_LANGUAGE)
        return codes

    def discover_languages(self):
        result = []
        for code in self.available_languages():
            name = self._names.get(code)
            if not name and code == FALLBACK_LANGUAGE:
                name = "English"
            result.append((code, name or code.upper()))
        result.sort(key=lambda item: (item[0] != FALLBACK_LANGUAGE, item[0]))
        return result

    def set_language(self, code: str) -> bool:
        code = str(code or "").strip().lower()
        if not code or self._load_language(code) is None:
            return False
        self.current = code
        return True

    def current_language(self) -> str:
        return self.current

    def take_problems(self):
        found = list(self.problems)
        self.problems.clear()
        return found

    def tr(self, key: str, **fmt) -> str:
        table = self._load_language(self.current)
        text = table.get(key) if table is not None else None
        if text is None:
            english = self._load_language(FALLBACK_LANGUAGE)
            text = english.get(key) if english is not None else None
        if text is None:
            return key
        if not fmt:
            return text
        try:
            return text.format(**fmt)
        except Exception:
            return text


class Note:
    """A localized startup or resource message shown by the game."""

    def __init__(self, key, warn=False, **kw):
        self.key, self.warn, self.kw = key, warn, kw

    def text(self):
        return tr(self.key, **self.kw)


class _RoleLabels:
    """Dictionary-style translation lookup for scoreboard role labels."""

    def __init__(self, prefix):
        self.prefix = prefix

    def get(self, role, default=""):
        return tr(self.prefix + role) if role in _ROLE_CODES else default

    def __getitem__(self, role):
        return tr(self.prefix + role)


T = Translator(prefix=DEFAULT_PREFIX)
tr = T.tr
ROLE_TAG = _RoleLabels("role.tag.")


def init_language(code):
    """Select the requested language, then Italian, then English."""
    requested = str(code or "it").strip().lower()
    tried = set()
    for candidate in (requested, "it", FALLBACK_LANGUAGE):
        if candidate and candidate not in tried:
            tried.add(candidate)
            if T.set_language(candidate):
                return candidate
    return T.current_language()


# Keep the generic translator API available to other IL MISTER modules.
configure = T.configure
available_languages = T.available_languages
discover_languages = T.discover_languages
set_language = T.set_language
current_language = T.current_language
take_problems = T.take_problems
