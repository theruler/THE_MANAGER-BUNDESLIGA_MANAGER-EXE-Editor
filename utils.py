"""Utility functions: config loading/saving, default profiles."""

import os
import sys
import json

try:
    from exe_handler import GAME_PROFILES
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from exe_handler import GAME_PROFILES

from font_safety import atomic_save_bytes


def _program_dir() -> str:
    """Directory of the running program, for source and frozen operation alike.

    Frozen (PyInstaller): the folder holding the executable, never the temporary
    extraction area.  From source: the folder holding this module.  The current
    working directory is deliberately never used.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# External, user-facing resources live next to the program in a small data
# folder.  They are the only two files that are not embedded.
DATA_DIR = os.path.join(_program_dir(), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "char-mapping.json")
DEEPL_KEY_FILE = os.path.join(DATA_DIR, "deepl_key.txt")
DEFAULT_PROFILE_NAME = next(iter(GAME_PROFILES))

# A damaged existing configuration must never be treated as an empty one.  While
# the lock is active every write path is blocked, so the unreadable file on disk
# stays intact and non-reconstructible entries cannot be silently discarded.
_CONFIG_LOCKED = False
_CONFIG_LOCK_REASON = None


_translate = None


def set_translator(func) -> None:
    """Install the UI translator used for the messages below.

    The editor injects :func:`i18n.tr` during startup.  This module
    deliberately does not import ``i18n`` itself: the configuration path
    has to keep working when no translation is available at all, and the
    English texts below stay the built-in fallback.
    """
    global _translate
    _translate = func


def _text(key: str, fallback: str, **fmt) -> str:
    """Localised configuration message, English when unavailable."""
    if _translate is not None:
        try:
            text = _translate(key, **fmt)
            if text != key:
                return text
        except Exception:
            pass
    return fallback.format(**fmt) if fmt else fallback


def _report_config_problem(message: str) -> None:
    """Make a configuration problem visible without depending on a live GUI."""
    try:
        from tkinter import messagebox
        messagebox.showwarning(_text("utils.cfg.title", "Config"), message)
    except Exception:
        print(f"Warning: {message}")


def _lock_config(reason: str) -> dict:
    """Enter the fail-closed state for an existing but unusable configuration."""
    global _CONFIG_LOCKED, _CONFIG_LOCK_REASON
    _CONFIG_LOCKED = True
    _CONFIG_LOCK_REASON = reason
    _report_config_problem(_text(
        "utils.cfg.damaged",
        "The existing configuration is damaged and was not replaced.\n"
        "Configuration changes stay blocked until it is repaired or removed.\n\n"
        "{reason}",
        reason=reason,
    ))
    return {}


def _unlock_config() -> None:
    global _CONFIG_LOCKED, _CONFIG_LOCK_REASON
    _CONFIG_LOCKED = False
    _CONFIG_LOCK_REASON = None


def load_config() -> dict:
    """Load the character mapping configuration, fail-closed on a damaged file.

    Three strictly separate states are distinguished: the file does not exist
    (legitimate default case), the file exists and is a valid configuration
    object, or the file exists but is damaged/unreadable/structurally invalid.
    Only the first case may produce an empty configuration.
    """
    if not os.path.exists(CONFIG_FILE):
        _unlock_config()
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        return _lock_config(f"{CONFIG_FILE} could not be read: {exc}")
    if not isinstance(data, dict):
        return _lock_config(f"{CONFIG_FILE} does not contain a configuration object")
    _unlock_config()
    return data


def save_config(cfg: dict) -> None:
    """Persist the configuration atomically; blocked while the config is locked.

    The lock is evaluated here rather than at the call sites, so every current
    and future writer is covered.  The serialized bytes match the previous text
    mode output exactly; only the write itself became atomic.
    """
    if _CONFIG_LOCKED:
        _report_config_problem(_text(
            "utils.cfg.locked",
            "Configuration changes are not saved while the existing configuration "
            "is damaged.\n\n{reason}",
            reason=_CONFIG_LOCK_REASON or "",
        ))
        return
    try:
        text = json.dumps(cfg, indent=2, ensure_ascii=False)
        payload = text.replace("\n", os.linesep).encode("utf-8")
        atomic_save_bytes(CONFIG_FILE, payload)
    except Exception as e:
        _report_config_problem(_text(
            "utils.cfg.save_failed",
            "Could not save config: {error}", error=e))


def get_default_config(profile_name: str) -> dict:
    """Get default configuration for a game profile."""
    prof = GAME_PROFILES.get(profile_name, {})
    defaults = prof.get("range_font_defaults", {})
    return {
        "string_fonts": {},
        "charmaps": {"NORMAL.FON": {}, "FLOW.FON": {}, "MICRO4.FON": {}},
        "range_font_defaults": {str(k): v for k, v in defaults.items()},
    }


def get_game_config(cfg: dict, game_profile: str) -> dict:
    """Get or create game-specific config."""
    if game_profile not in cfg:
        cfg[game_profile] = get_default_config(game_profile)
    return cfg[game_profile]


__all__ = ['load_config', 'save_config', 'get_default_config', 'get_game_config', 'CONFIG_FILE', 'DATA_DIR', 'DEEPL_KEY_FILE', 'DEFAULT_PROFILE_NAME']
