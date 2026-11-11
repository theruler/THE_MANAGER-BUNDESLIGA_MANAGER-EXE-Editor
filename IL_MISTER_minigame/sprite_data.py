"""Built-in sprite/animation tables and sprite-id helpers."""

from i18n import tr

SLOWMO_KEYS = ("header", "header_dive", "bicycle", "volley") # Actions that trigger slow motion; remove or add keys to change the list.

DEFAULT_ACTIONS = { # Fallback frame sequences; E/W are ordered frames; travel moves; single shares facing.
    "order": ["kick", "dive", "header", "bicycle", "fall", "slide", "moonwalk", "cele"],
    "actions": {
        "kick": {"label": "Power Kick", "E": [1, 10, 11], "W": [49, 48, 47]},
        "dive": {"label": "Dive", "E": [12, 13, 14, 14, 14, 14], "W": [46, 45, 44, 44, 44, 44]},
        "header": {"label": "Header", "E": [16, 17, 18, 19, 20], "W": [42, 41, 40, 39, 38]},
        "bicycle": {"label": "Bicycle kick", "E": [18, 26, 12, 22, 23, 23, 24, 24], "W": [26, 36, 46, 35, 35, 34, 34]},
        "fall": {"label": "Collision fall", "E": [12, 13, 14, 14, 14], "W": [46, 45, 44, 44, 44]},
        "slide": {"label": "Sliding kick", "E": [36, 11, 11, 45, 34, 34, 34], "W": [22, 47, 47, 13, 24, 24, 24]},
        "moonwalk": {"label": "Moonwalk", "E": [55, 54, 55, 53], "W": [3, 4, 3, 5], "travel": True},
        "cele": {"label": "Celebration", "E": [25, 26, 27, 26, 27, 26, 27], "W": [25, 26, 27, 26, 27, 26, 27], "single": True},
    },
    "moves": {"E": [3, 4, 3, 5], "NE": [0, 1, 0, 2], "N": [28, 29, 28, 30], "NW": [58, 57, 58, 56],
              "W": [55, 54, 55, 53], "SW": [52, 51, 52, 50], "S": [31, 32, 31, 33], "SE": [6, 7, 6, 8]},
    "referee": {
        "move": {"E": [121, 122, 121, 123], "NE": [118, 119, 118, 120], "N": [126, 127, 126, 128],
                 "NW": [139, 138, 139, 137], "W": [136, 135, 136, 134], "SW": [133, 132, 133, 134],
                 "S": [129, 130, 129, 131], "SE": [124, 125, 124, 123]},
        "stand": {"E": 121, "NE": 118, "N": 126, "NW": 139, "W": 136, "SW": 133, "S": 129, "SE": 124}},
    "ball": {"rotation": [142, 143, 144]},
}
DIRS = ["E", "NE", "N", "NW", "W", "SW", "S", "SE"] # Supported eight-way movement directions and their ordering.
NORTH_TO_SOUTH = {"N": "S", "NE": "SE", "NW": "SW"} # Direction remapping when the team attacks toward the opposite end.
STOP_FLIP = {"N": "S", "NE": "SE", "NW": "SW", "S": "N", "SE": "NE", "SW": "NW"} # Facing-direction correction applied when a moving player stops.
CELE_SLIDE = {"E": [13, 14, 14, 14], "W": [45, 44, 44, 44]} # Sprite-frame sequences used for the short slide-celebration pose.

ACT_SPEC = { # Action timing: frame duration, contact frame, hold time, optional active range.
    "kick": dict(fdur=0.075, contact=1, hold=0.10),
    "header": dict(fdur=0.085, contact=2, hold=0.08),
    "header_dive": dict(fdur=0.090, contact=2, hold=0.60),
    "bicycle": dict(fdur=0.075, contact=4, hold=0.20),
    "slide": dict(fdur=0.080, contact=1, hold=0.30, active=(1, 4)),
    "dive": dict(fdur=0.110, contact=99, hold=0.60, active=(1, 4)),
    "fall": dict(fdur=0.090, contact=99, hold=1.10),
    "throw": dict(fdur=0.120, contact=1, hold=0.10),
    "moonwalk": dict(fdur=0.110, contact=99, hold=0.15),
    "cele": dict(fdur=0.110, contact=99, hold=0.30),
    "punch": dict(fdur=0.085, contact=1, hold=0.30),
}


ACTIONS, MOVE_E, STAND_K = {}, {}, {}
REF_MOVE, REF_STAND, BALL_ROT = {}, {}, [142, 143, 144] # REF_MOVE/REF_STAND: referee movement/idle frames; BALL_ROT: ball frames.


def _ks(v, lo, hi): # Clamp a value using the requested lower and upper limits.
    out = [int(x) for x in v]
    if not out or any(not lo <= k <= hi for k in out):
        raise ValueError(tr("err.ids_range"))
    return out


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


def _install_defaults(): # Populate the shared animation tables from the built-in definitions.
    parsed = _parse_actions(DEFAULT_ACTIONS)
    for table, values in zip((ACTIONS, MOVE_E, STAND_K, REF_MOVE, REF_STAND), parsed[:5]):
        table.update(values)
    BALL_ROT[:] = parsed[5]


_install_defaults()


def team_sprite_offset(team): # Return the sprite index offset for the specified team.
    return 0 if team == 0 else 59


def run_cycle(team, d): # Return the movement cycle for a team and direction.
    return [team_sprite_offset(team) + k for k in MOVE_E[d]]


def stand_sid(team, d): # Return the standing sprite ID for a team and direction.
    return team_sprite_offset(team) + STAND_K[d]


def action_sids(team, key, side): # Return the configured sprite IDs for an action and team direction.
    return [team_sprite_offset(team) + k for k in ACTIONS[key][side]]
