"""Persistent user options: DATA/options.json (language, match settings, font, controlled team)."""

import json
import os

OPTIONS_FILE = "options.json"


def options_path(dirs): # options.json in the first folder that already has it, else in the first folder (created on save).
    for d in dirs:
        p = os.path.join(d, OPTIONS_FILE)
        if os.path.isfile(p):
            return p
    return os.path.join(dirs[0], OPTIONS_FILE)


def _num(v, lo, hi): # A number inside lo..hi, or None.
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and lo <= v <= hi else None


def load_options(path): # Saved options as a validated dict (unknown or invalid entries are dropped, a missing file gives {}).
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out = {}
    if isinstance(raw.get("lang"), str) and raw["lang"].strip():
        out["lang"] = raw["lang"].strip().lower()
    v = _num(raw.get("half_min"), 0.5, 45)
    if v is not None:
        out["half_min"] = v
    v = _num(raw.get("replay_secs"), 1, 60)
    if v is not None:
        out["replay_secs"] = int(v)
    for k in ("slowmo", "replay_auto", "font_modern", "hints"):
        if isinstance(raw.get(k), bool):
            out[k] = raw[k]
    if "user_team" in raw and (raw["user_team"] is None or raw["user_team"] in (0, 1) and not isinstance(raw["user_team"], bool)):
        out["user_team"] = raw["user_team"]
    return out


def save_options(path, opts): # Write the options; returns an error text or None.
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(opts, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    except OSError as ex:
        return str(ex)
    return None
