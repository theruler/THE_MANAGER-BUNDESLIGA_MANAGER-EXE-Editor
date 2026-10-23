"""Sprite/animation tables loaded from JSON (or defaults) and sprite-id helpers."""

import json
import os

from animation_config import DEFAULT_ACTIONS, DIRS
from lang import Note, tr


ACTIONS, MOVE_E, STAND_K = {}, {}, {}
REF_MOVE, REF_STAND, BALL_ROT = {}, {}, [142, 143, 144] # REF_MOVE/REF_STAND: referee movement/idle frames; BALL_ROT: ball frames.


def _ks(v, lo, hi): # Clamp a value using the requested lower and upper limits.
    out = [int(x) for x in v]
    if not out or any(not lo <= k <= hi for k in out):
        raise ValueError(tr("err.ids_range"))
    return out


def _read_json(path): # Read a JSON file and return its decoded data.
    try:
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def _parse_actions(raw): # Parse action definitions into the internal animation format.
    acts = {}
    for key, a in raw["actions"].items():
        e = _ks(a["E"], 0, 58)
        acts[str(key)] = {"E": e, "W": _ks(a["W"], 0, 58) if a.get("W") else [58 - k for k in e]}
    moves = {d: _ks(raw["moves"][d], 0, 58) for d in DIRS}
    stand = {d: int((raw.get("stand") or {}).get(d, moves[d][0])) for d in DIRS}
    rf = raw["referee"]
    rmove = {d: _ks(rf["move"][d], 118, 141) for d in DIRS}
    rstand = {d: int(rf["stand"][d]) if isinstance(rf["stand"], dict) and d in rf["stand"] else rmove[d][0] for d in DIRS}
    rot = _ks(raw.get("ball", {}).get("rotation", [142, 143, 144]), 142, 144)
    return acts, moves, stand, rmove, rstand, rot


def load_data(dirs): # Load animation, sprite, and gameplay data from the selected resource directories.
    notes = []

    def find(name): # Locate a font or asset candidate matching the requested name.
        for d in dirs:
            r = _read_json(os.path.join(d, name))
            if r:
                return r, os.path.join(d, name)
        return None, None

    raw, path = find("tore_actions.json")
    try:
        if raw is None:
            raise KeyError(tr("err.file_not_found"))
        parsed = _parse_actions(raw)
        notes.append(Note("note.actions_file", path=path))
    except (KeyError, ValueError, TypeError) as ex:
        parsed = _parse_actions(DEFAULT_ACTIONS)
        notes.append(Note("note.actions_default", True, reason=ex))
    # Refill the shared tables in place so modules that imported them keep seeing the live data.
    for table, fresh in zip((ACTIONS, MOVE_E, STAND_K, REF_MOVE, REF_STAND), parsed[:5]):
        table.clear()
        table.update(fresh)
    BALL_ROT[:] = parsed[5]
    default_actions = _parse_actions(DEFAULT_ACTIONS)[0]
    for need in ("kick", "header", "bicycle", "slide", "dive", "fall", "cele"):
        ACTIONS.setdefault(need, default_actions[need])
    return notes


def team_sprite_offset(team): # Return the sprite index offset for the specified team.
    return 0 if team == 0 else 59


def run_cycle(team, d): # Return the movement cycle for a team and direction.
    return [team_sprite_offset(team) + k for k in MOVE_E[d]]


def stand_sid(team, d): # Return the standing sprite ID for a team and direction.
    return team_sprite_offset(team) + STAND_K[d]


def action_sids(team, key, side): # Return the configured sprite IDs for an action and team direction.
    return [team_sprite_offset(team) + k for k in ACTIONS[key][side]]
