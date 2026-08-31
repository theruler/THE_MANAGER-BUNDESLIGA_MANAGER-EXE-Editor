# -*- coding: utf-8 -*-
"""Runtime UI translation for THE MANAGER - Bundesliga Manager String-Editor.

Language tables live in plain Python files under ``data/lang/`` next to the
program, so a translation can be corrected, replaced or added without
rebuilding the editor.  Loading deliberately uses an explicit absolute path
(``importlib.util.spec_from_file_location``) and never ``sys.path``: under
PyInstaller onefile ``sys.path`` points into the temporary extraction area, so
an import by name would silently ignore a file the user dropped next to the
executable.

Two base directories are involved, and keeping them apart is the whole point:

``_program_dir()``
    The folder holding the program.  Frozen: the folder of the executable.
    From source: the folder of this module.  This is where the five external,
    user-replaceable language files live, and it always wins.

``_bundle_dir()``
    The folder holding resources embedded in the executable.  Frozen:
    ``sys._MEIPASS``, the temporary extraction area.  From source: the folder
    of this module.  Only English lives here, as the guaranteed fallback for
    the case where the external English file is missing or damaged.

Running from source both resolve to the same folder, so there is exactly one
English file and no duplication.  Only a frozen build has two copies, and they
are produced by the same build step from the same source file.

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
_PREFIX = "lang_"
_SUFFIX = ".py"

_tables = {}          # code -> table dict (successful external loads)
_failed = set()       # codes whose external file could not be used
_problems = []        # human-readable load problems, drained by the GUI
_embedded = None      # embedded English table, loaded at most once
_embedded_tried = False
_current = FALLBACK_LANGUAGE


def _program_dir() -> str:
    """Directory of the running program, for source and frozen operation alike.

    Frozen (PyInstaller): the folder holding the executable, never the
    temporary extraction area.  From source: the folder holding this module.
    The current working directory is deliberately never used.  This mirrors
    ``utils._program_dir()`` exactly; both must stay in step.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir() -> str:
    """Directory of resources embedded in the executable.

    Frozen (PyInstaller onefile): ``sys._MEIPASS``, the temporary folder the
    bootloader extracts the bundle into.  Anything added with ``--add-data``
    lives there and nowhere else -- in particular it is *not* next to the
    executable.  From source there is no bundle, so this falls back to the
    module folder and coincides with :func:`_program_dir`.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return base
    return os.path.dirname(os.path.abspath(__file__))


def _lang_file(base: str, code: str) -> str:
    return os.path.join(base, LANG_SUBDIR, _PREFIX + code + _SUFFIX)


def _read_table(path: str, code: str):
    """Load one language file by absolute path; return its table or ``None``.

    Every failure is caught, including ``SyntaxError``: a broken translation is
    a cosmetic problem and must never propagate into the editor start.
    """
    try:
        if not os.path.isfile(path):
            return None
        spec = importlib.util.spec_from_file_location(
            "_bmh_lang_" + code, path)
        if spec is None or spec.loader is None:
            raise ImportError("no loader for %s" % path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        table = getattr(module, "TEXTS_" + code.upper(), None)
        if table is None:
            table = getattr(module, "TEXTS", None)
        if not isinstance(table, dict) or not table:
            raise ValueError("TEXTS_%s missing or empty" % code.upper())
        for key, value in table.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("non-string entry for %r" % (key,))
        return table
    except Exception as exc:                      # noqa: BLE001 - fail visible
        _problems.append("%s: %s" % (os.path.basename(path), exc))
        return None


def _external(code: str):
    """External table for ``code``, loaded once; ``None`` when unusable."""
    if code in _tables:
        return _tables[code]
    if code in _failed:
        return None
    table = _read_table(_lang_file(_program_dir(), code), code)
    if table is None:
        _failed.add(code)
        return None
    _tables[code] = table
    return table


def _embedded_english():
    """Embedded English table from the bundle; ``None`` when unavailable."""
    global _embedded, _embedded_tried
    if _embedded_tried:
        return _embedded
    _embedded_tried = True
    external = _lang_file(_program_dir(), FALLBACK_LANGUAGE)
    path = _lang_file(_bundle_dir(), FALLBACK_LANGUAGE)
    # Running from source both paths are the same file.  It already failed as
    # the external table, so retrying it would only duplicate the message.
    if os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(external)):
        return None
    _embedded = _read_table(path, FALLBACK_LANGUAGE)
    return _embedded


def _english():
    """English table: external first, embedded copy as guaranteed fallback."""
    return _external(FALLBACK_LANGUAGE) or _embedded_english()


def available_languages() -> set:
    """Codes that can actually be loaded right now.

    English is always included: even without an external file the embedded
    copy answers for it.
    """
    codes = set()
    folder = os.path.join(_program_dir(), LANG_SUBDIR)
    try:
        names = os.listdir(folder)
    except Exception:                             # noqa: BLE001
        names = []
    for name in names:
        if not (name.startswith(_PREFIX) and name.endswith(_SUFFIX)):
            continue
        code = name[len(_PREFIX):-len(_SUFFIX)]
        if code and _external(code) is not None:
            codes.add(code)
    if _english() is not None:
        codes.add(FALLBACK_LANGUAGE)
    return codes


def discover_languages():
    """Loadable languages as ``[(code, display name)]``, English first.

    The display name is the ``LANG_NAME`` of the language file itself, so a new
    translation names itself and needs no editor change.
    """
    result = []
    for code in sorted(available_languages()):
        table = _external(code)
        name = None
        if table is not None:
            path = _lang_file(_program_dir(), code)
            name = _lang_name(path, code)
        if not name and code == FALLBACK_LANGUAGE:
            name = "English"
        result.append((code, name or code.upper()))
    result.sort(key=lambda item: (item[0] != FALLBACK_LANGUAGE, item[0]))
    return result


def _lang_name(path: str, code: str):
    try:
        spec = importlib.util.spec_from_file_location(
            "_bmh_langname_" + code, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        name = getattr(module, "LANG_NAME", None)
        return name if isinstance(name, str) and name else None
    except Exception:                             # noqa: BLE001
        return None


def set_language(code: str) -> bool:
    """Select ``code``; returns whether it is actually usable."""
    global _current
    if _external(code) is None and code != FALLBACK_LANGUAGE:
        return False
    _current = code
    return True


def current_language() -> str:
    return _current


def take_problems():
    """Drain collected load problems so the GUI can report them once."""
    found = list(_problems)
    del _problems[:]
    return found


def tr(key: str, **fmt) -> str:
    """Translate ``key``; fall back to English, then to the raw key.

    Formatting is guarded: a translation with a wrong placeholder yields the
    unformatted text instead of raising, so a single bad entry can never abort
    building a dialog.
    """
    text = None
    table = _external(_current) if _current != FALLBACK_LANGUAGE else _english()
    if table is not None:
        text = table.get(key)
    if text is None:
        english = _english()
        if english is not None:
            text = english.get(key)
    if text is None:
        return key
    if not fmt:
        return text
    try:
        return text.format(**fmt)
    except Exception:                             # noqa: BLE001
        return text
