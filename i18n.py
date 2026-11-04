# -*- coding: utf-8 -*-
"""Runtime UI translation for THE MANAGER - Bundesliga Manager String-Editor.

``_bundle_dir()``
    The folder holding resources embedded in the executable.  Frozen:
    ``sys._MEIPASS``, the temporary extraction area.  From source: the folder
    of this module.  Only English lives here, as the guaranteed fallback for
    the case where the external English file is missing or damaged.


Several programs can share this module in one process (the main editor and the
embedded TORE panel, for instance).  Each one owns a :class:`Translator` with
its own file prefix, tables, problems and current language, so they can never
overwrite each other's settings.  The module-level functions (``tr``,
``set_language`` ...) drive one default translator with the prefix ``lang_``.

The lookup order is: selected language, then English, then the raw key.  A key
that is missing everywhere renders as ``menu.file.open`` rather than as an
empty label, so a mistake is visible instead of silent.  A damaged optional
language is reported once and then ignored; it can never keep the editor from
starting.
"""

import importlib.util
import os
import sys

LANG_SUBDIR = os.path.join("data", "lang")
FALLBACK_LANGUAGE = "en"
DEFAULT_PREFIX = "lang_"
_SUFFIX = ".py"



def _bundle_dir() -> str:
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def _load_module(path: str, modname: str):
    spec = importlib.util.spec_from_file_location(modname, path)
    if spec is None or spec.loader is None:
        raise ImportError("no loader for %s" % path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Translator:
    """Independent translation state for one family of ``<prefix><code>.py`` files."""

    def __init__(self, prefix: str = DEFAULT_PREFIX):
        self.prefix = prefix or DEFAULT_PREFIX
        self.current = FALLBACK_LANGUAGE
        self.problems = []        # human-readable load problems, drained by the GUI
        self._reset()

    def _reset(self):
        self._tables = {}         # code -> table dict (successful external loads)
        self._failed = set()      # codes whose external file could not be used
        self._embedded = None     # embedded English table, loaded at most once
        self._embedded_tried = False

    def configure(self, prefix: str = None) -> None:
        """Use a different language-file prefix and forget everything loaded."""
        if prefix:
            self.prefix = prefix
        self._reset()

    def _lang_file(self, base: str, code: str) -> str:
        return os.path.join(base, LANG_SUBDIR, self.prefix + code + _SUFFIX)

    def _read_table(self, path: str, code: str):
        """Load one language file by absolute path; return its table or ``None``.

        Every failure is caught, including ``SyntaxError``: a broken translation
        is a cosmetic problem and must never propagate into the editor start.
        """
        try:
            if not os.path.isfile(path):
                return None
            module = _load_module(path, "_bmh_lang_%s%s" % (self.prefix, code))
            table = getattr(module, "TEXTS_" + code.upper(), None)
            if table is None:
                table = getattr(module, "TEXTS", None)
            if not isinstance(table, dict) or not table:
                raise ValueError("TEXTS_%s missing or empty" % code.upper())
            for key, value in table.items():
                if not isinstance(key, str) or not isinstance(value, str):
                    raise ValueError("non-string entry for %r" % (key,))
            return table
        except Exception as exc:                  # noqa: BLE001 - fail visible
            self.problems.append("%s: %s" % (os.path.basename(path), exc))
            return None

    def _external(self, code: str):
        """Load an embedded language table once."""
        if code in self._tables:
            return self._tables[code]
        if code in self._failed:
            return None
    
        table = self._read_table(
            self._lang_file(_bundle_dir(), code), code
        )
    
        if table is None:
            self._failed.add(code)
            return None
    
        self._tables[code] = table
        return table

    def _english(self):
        return self._external(FALLBACK_LANGUAGE)

    def available_languages(self) -> set:
        """Return all loadable embedded languages."""
        codes = set()
        folder = os.path.join(_bundle_dir(), LANG_SUBDIR)
    
        try:
            names = os.listdir(folder)
        except OSError:
            names = []
    
        for name in names:
            if not (name.startswith(self.prefix) and name.endswith(_SUFFIX)):
                continue
    
            code = name[len(self.prefix):-len(_SUFFIX)]
            if code and self._external(code) is not None:
                codes.add(code)
    
        return codes

    def discover_languages(self):
        """Loadable languages as [(code, display name)], English first."""
        result = []
    
        for code in self.available_languages():
            name = self._lang_name(
                self._lang_file(_bundle_dir(), code), code
            )
            result.append((code, name or code.upper()))
    
        result.sort(key=lambda item: (
            item[0] != FALLBACK_LANGUAGE, item[0]
        ))
        return result

    def _lang_name(self, path: str, code: str):
        try:
            name = getattr(_load_module(path, "_bmh_langname_%s%s" % (self.prefix, code)), "LANG_NAME", None)
            return name if isinstance(name, str) and name else None
        except Exception:                         # noqa: BLE001
            return None

    def set_language(self, code: str) -> bool:
        """Select ``code``; returns whether it is actually usable."""
        if self._external(code) is None and code != FALLBACK_LANGUAGE:
            return False
        self.current = code
        return True

    def current_language(self) -> str:
        return self.current

    def take_problems(self):
        """Drain collected load problems so the GUI can report them once."""
        found = list(self.problems)
        del self.problems[:]
        return found

    def tr(self, key: str, **fmt) -> str:
        """Translate ``key``; fall back to English, then to the raw key.

        Formatting is guarded: a translation with a wrong placeholder yields the
        unformatted text instead of raising, so a single bad entry can never
        abort building a dialog.
        """
        text = None
        table = self._external(self.current) if self.current != FALLBACK_LANGUAGE else self._english()
        if table is not None:
            text = table.get(key)
        if text is None:
            english = self._english()
            if english is not None:
                text = english.get(key)
        if text is None:
            return key
        if not fmt:
            return text
        try:
            return text.format(**fmt)
        except Exception:                         # noqa: BLE001
            return text


# Default translator (prefix ``lang_``): the module-level API used by the main editor.
_default = Translator()
configure = _default.configure
available_languages = _default.available_languages
discover_languages = _default.discover_languages
set_language = _default.set_language
current_language = _default.current_language
take_problems = _default.take_problems
tr = _default.tr
