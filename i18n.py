from __future__ import annotations

import importlib
import os
import sys


_DEFAULT_LANG = "en"
_current_lang: str = _DEFAULT_LANG
_tables: dict[str, dict] = {}


def _lang_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def discover_languages() -> list[tuple[str, str]]:
    """Return (code, display_name) pairs for every lang_XX.py found in the app folder.

    The folder is scanned at call time so a newly dropped file is picked up
    without restarting.  English is always first; the rest follow alphabetically.
    """
    folder = _lang_dir()
    codes = set()
    for name in os.listdir(folder):
        if name.startswith("lang_") and name.endswith(".py"):
            code = name[5:-3]
            if code and code.isalpha():
                codes.add(code)
    codes.discard("en")
    ordered = ["en"] + sorted(codes)
    _DISPLAY = {"en": "English", "de": "Deutsch", "it": "Italiano",
                "fr": "Français", "es": "Español", "pl": "Polski"}
    return [(code, _DISPLAY.get(code, code.upper())) for code in ordered]


def _load_table(lang: str) -> dict:
    """Import lang_{lang}.py and return its TEXTS_{LANG} dict."""
    if lang in _tables:
        return _tables[lang]
    module_name = f"lang_{lang}"
    var_name = f"TEXTS_{lang.upper()}"
    try:
        mod = importlib.import_module(module_name)
        table = getattr(mod, var_name)
        if not isinstance(table, dict):
            raise TypeError(f"{var_name} is not a dict")
        _tables[lang] = table
        return table
    except (ImportError, AttributeError, TypeError):
        return {}


def set_language(lang: str) -> None:
    global _current_lang
    _load_table(lang)
    _current_lang = lang


def current_language() -> str:
    return _current_lang


def tr(key: str, **fmt) -> str:
    """Return the localised string for *key*.

    Lookup order: requested language → English fallback → key itself.
    Format placeholders ({name}) are expanded when kwargs are supplied.
    Technical values (profile names, hex addresses, status tokens such as
    PASS / FAIL, JSON field names) must NOT go through this function.
    """
    table = _load_table(_current_lang)
    text = table.get(key)
    if text is None and _current_lang != _DEFAULT_LANG:
        text = _load_table(_DEFAULT_LANG).get(key)
    if text is None:
        text = key
    return text.format(**fmt) if fmt else text


__all__ = ["tr", "set_language", "current_language", "discover_languages"]
