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
