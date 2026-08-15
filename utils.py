"""Utility functions: config loading/saving, default profiles."""

import os
import sys
import json

try:
    from exe_handler import GAME_PROFILES
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from exe_handler import GAME_PROFILES

# Configuration file location
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "char-mapping.json")
DEFAULT_PROFILE_NAME = next(iter(GAME_PROFILES))


def load_config() -> dict:
    """Load character mapping configuration from file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_config(cfg: dict) -> None:
    """Save character mapping configuration to file."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        try:
            from tkinter import messagebox
            messagebox.showwarning("Config", f"Could not save config: {e}")
        except Exception:
            print(f"Warning: Could not save config: {e}")


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


__all__ = ['load_config', 'save_config', 'get_default_config', 'get_game_config', 'CONFIG_FILE', 'DEFAULT_PROFILE_NAME']
