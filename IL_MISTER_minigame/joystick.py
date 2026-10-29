import json
import math
import os

import pygame

from game_utils import unit

JOY_EVENTS = tuple(getattr(pygame, n) for n in (  # Pygame joystick event types supported by this version of the input module.
    "JOYAXISMOTION", "JOYBUTTONDOWN", "JOYBUTTONUP", "JOYHATMOTION", "JOYDEVICEADDED", "JOYDEVICEREMOVED")
    if hasattr(pygame, n))
JOY_FILE = "mister-joy.json" # Persistent filename for saved controller mappings.
JOY_IMG = "mister-joy.png" # Optional controller illustration filename used by the mapping screen.

JOY_VERSION = 3 # Saved control-layout version; increment it when the serialized layout changes.
JOY_ACTIONS = [  # Available logical actions and their default keyboard/controller labels.
    ("pass", pygame.K_z, "z", ""),
    ("shot", pygame.K_x, "x", ""),
    ("cele", pygame.K_c, "c", ""),
    ("hints", pygame.K_F8, "", ""),
    ("switch_player", pygame.K_TAB, "", ""),
    ("pause", pygame.K_p, "p", ""),
    ("replay", pygame.K_r, "r", ""),
    ("help", pygame.K_h, "h", ""),
    ("speed_up", pygame.K_PLUS, "+", ""),
    ("speed_down", pygame.K_MINUS, "-", ""),
    ("formation_prev", pygame.K_F5, "", ""),
    ("formation_next", pygame.K_F6, "", ""),
    ("toggle_scroll", pygame.K_F2, "", ""),
    ("zoom_in", pygame.K_F4, "", ""),
    ("zoom_out", pygame.K_F3, "", ""),
    ("mute", pygame.K_m, "m", ""),
    ("fullscreen", pygame.K_F11, "", ""),
    ("spectator", pygame.K_q, "q", ""),
    ("agon_up", pygame.K_PERIOD, ".", ""),
    ("agon_down", pygame.K_COMMA, ",", ""),
    ("exit_match", pygame.K_ESCAPE, "", ""),
    ("confirm", pygame.K_RETURN, "", ""),
    ("back", pygame.K_ESCAPE, "", ""),
]
JOY_KEYS = {a: (k, u) for a, k, u, _l in JOY_ACTIONS} # Default keyboard mapping for each logical action.

JOY_HOTSPOTS = {  # Hitboxes used to assign controls through the controller mapping screen.
    "triangle": (742, 392), "circle": (793, 441), "cross": (741, 494), "square": (692, 441),
    "dpad_up": (272, 395), "dpad_left": (232, 441), "dpad_right": (318, 441), "dpad_down": (272, 486),
    "l1": (275, 305), "r1": (745, 305), "l2": (248, 272), "r2": (772, 272),
    "select": (435, 443), "start": (580, 443), "lstick": (398, 548), "rstick": (628, 548),
    "l3": (398, 548), "r3": (628, 548),
}
JOY_CTRL_LABELS = {  # Human-readable names for controls shown in the mapping interface.
    "triangle": "Triangle", "circle": "Circle", "cross": "Cross", "square": "Square",
    "dpad_up": "D-Pad UP", "dpad_down": "D-Pad DOWN", "dpad_left": "D-Pad LEFT", "dpad_right": "D-Pad RIGHT",
    "l1": "L1", "l2": "L2", "r1": "R1", "r2": "R2", "select": "Select", "start": "Start", "l3": "L3 (L stick)", "r3": "R3 (R stick)",
}

JOY_DEFAULT = {  # Default bindings restored when the user resets controller settings.
  "_help": [
    "Joypad mapping. You can also change it from the 'Joypad mapping' screen in the intro.",
    "Each action has a list of commands: 'button:N' (button N), 'hat:up|down|left|right' (directional pad),",
    "'axis:N+' or 'axis:N-' (axis used as a button, e.g., analog triggers). Empty list = unassigned.",
    "'button_names' associates the button number with the PS2 controller (used only for the joypad layout):",
    "triangle circle cross square l1 l2 r1 r2 select start l3 r3.",
    "'axes': stick axes (move = left stick for movement, aim = right stick for aiming)."
  ],
  "version": JOY_VERSION,
  "deadzone": 0.35,
  "dpad_moves": True,
  "axes": {
    "move_x": 0,
    "move_y": 1,
    "aim_x": 2,
    "aim_y": 3
  },
  "button_names": {
    "0": "cross",
    "1": "circle",
    "2": "square",
    "3": "triangle",
    "4": "l1",
    "5": "r1",
    "6": "select",
    "7": "start",
    "8": "l3",
    "9": "r3",
    "10": "l2",
    "11": "r2"
  },
  "buttons": {
    "pass": [
      "ctrl:r1"
    ],
    "shot": [
      "axis:5+"
    ],
    "cele": [
      "ctrl:triangle"
    ],
    "hints": [],
    "switch_player": [
      "ctrl:cross"
    ],
    "pause": [
      "ctrl:select"
    ],
    "replay": [
      "ctrl:start"
    ],
    "help": [],
    "speed_up": [],
    "speed_down": [],
    "formation_prev": [],
    "formation_next": [],
    "toggle_scroll": [
      "ctrl:l1"
    ],
    "zoom_in": [],
    "zoom_out": [
      "axis:4+"
    ],
    "mute": [],
    "agon_up": [],
    "agon_down": [],
    "fullscreen": [],
    "spectator": [],
    "exit_match": [],
    "confirm": [],
    "back": []
  }
}



class JoyPad: # Joystick discovery, binding persistence, and normalized control input.

    def __init__(self, read_dirs, write_dir): # Initialize device state, bindings, recent-input tracking, and axis values.
        self.path = None
        for d in read_dirs:
            if d:
                f = os.path.join(d, JOY_FILE)
                if os.path.isfile(f):
                    self.path = f
                    break
        # Save back to the file that was read (e.g. .\data\mister-joy.json); write_dir is used only when no file exists yet.
        self.write_path = self.path or (os.path.join(write_dir, JOY_FILE) if write_dir else JOY_FILE)
        self.cfg = json.loads(json.dumps(JOY_DEFAULT))
        self.error = ""
        self.migrated = False
        self.load()
        self.pads = {}
        self.held = set()
        self.last_use = -999.0
        try:
            pygame.joystick.init()
            for i in range(pygame.joystick.get_count()):
                self.add_device(i)
        except pygame.error:
            pass
        if self.migrated or not os.path.isfile(self.write_path):
            self.save()

    def load(self): # Load saved bindings and merge them with valid defaults.
        if not self.path:
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                user = json.load(f)
        except (OSError, ValueError) as ex:
            self.error = str(ex)
            return
        c = self.cfg
        for k in ("deadzone", "dpad_moves"):
            if k in user:
                c[k] = user[k]
        for k in ("axes", "button_names"):
            if isinstance(user.get(k), dict):
                c[k].update(user[k])
        if user.get("version") != JOY_VERSION:
            self.migrated = True
        elif isinstance(user.get("buttons"), dict):
            for a, v in user["buttons"].items():
                if a in JOY_KEYS:
                    c["buttons"][a] = [self.norm(t) for t in (v if isinstance(v, list) else [v]) if t is not None]
        if isinstance(user.get("_help"), list):
            c["_help"] = user["_help"]
        c["version"] = JOY_VERSION

    def by_name(self, t): # Find a joystick control token by its display name.
        if t.startswith("button:"):
            n = self.cfg["button_names"].get(t[7:])
            if n:
                return "ctrl:" + n
        return t

    def canon(self, t): # Normalize a joystick or keyboard token into its canonical form.
        if t.startswith("ctrl:"):
            for i, n in self.cfg["button_names"].items():
                if n == t[5:]:
                    return "button:" + i
            return t
        return t

    def swap_controls(self, a, b): # Swap the assignments of two control actions.
        names = self.cfg["button_names"]
        ia = next((i for i, n in names.items() if n == a), None)
        ib = next((i for i, n in names.items() if n == b), None)
        if ia is not None:
            names[ia] = b
        if ib is not None:
            names[ib] = a
        self.save()

    @staticmethod
    def norm(t): # Normalize a control token from saved or user-provided data.
        return "button:%d" % t if isinstance(t, int) else str(t)

    def save(self): # Write the current bindings to persistent configuration storage.
        try:
            os.makedirs(os.path.dirname(self.write_path) or ".", exist_ok=True)
            with open(self.write_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2, ensure_ascii=False)
            self.error = ""
        except OSError as ex:
            self.error = str(ex)

    def reset(self): # Restore the default joystick mappings.
        self.cfg = json.loads(json.dumps(JOY_DEFAULT))
        self.save()

    def add_device(self, index): # Initialize and register the joystick at the specified device index.
        try:
            j = pygame.joystick.Joystick(index)
            if pygame.version.vernum < (2, 0, 0):
                try:
                    j.init()
                except pygame.error:
                    pass
            iid = j.get_instance_id() if hasattr(j, "get_instance_id") else index
            self.pads[iid] = j
            self._autodetect_aim_axes(j)
        except pygame.error:
            pass

    def _autodetect_aim_axes(self, joystick): # Detect which joystick axes are most likely used for aiming.
        axes = self.cfg.get("axes", {})
        ax, ay = axes.get("aim_x", 2), axes.get("aim_y", 3)
        try:
            pygame.event.pump()
            n = joystick.get_numaxes()
            if n < 5 or ax is None or ay is None or max(ax, ay) >= n:
                return
            values = [float(joystick.get_axis(i)) for i in range(n)]
            current = math.hypot(values[ax], values[ay])
            if current < 0.75:
                return
            candidates = []
            for i in range(2, n - 1):
                pair_mag = math.hypot(values[i], values[i + 1])
                if (i, i + 1) != (ax, ay) and pair_mag < 0.45:
                    candidates.append((pair_mag, i != 3, i, i + 1))
            if candidates:
                _mag, _prefer, new_x, new_y = min(candidates)
                axes["aim_x"], axes["aim_y"] = new_x, new_y
        except (pygame.error, IndexError, TypeError, ValueError):
            return

    def names(self): # Return the names of the available joystick devices.
        out = []
        for j in self.pads.values():
            try:
                out.append(j.get_name())
            except pygame.error:
                pass
        return out

    def recent(self, now): # Return whether a control event occurred within the recent-input window.
        return now - self.last_use < 12.0

    def process(self, ev, now=0.0): # Process a joystick event and update the active input state.
        t = ev.type
        if t == getattr(pygame, "JOYDEVICEADDED", -1):
            self.add_device(ev.device_index)
            return []
        if t == getattr(pygame, "JOYDEVICEREMOVED", -1):
            self.pads.pop(getattr(ev, "instance_id", -1), None)
            self.held.clear()
            return []
        new = []
        self.last_use = now
        if t == pygame.JOYBUTTONDOWN:
            tok = "button:%d" % ev.button
            if tok not in self.held:
                self.held.add(tok)
                new.append(tok)
        elif t == pygame.JOYBUTTONUP:
            self.held.discard("button:%d" % ev.button)
        elif t == pygame.JOYHATMOTION:
            hx, hy = ev.value
            now_tok = set()
            if hx:
                now_tok.add("hat:right" if hx > 0 else "hat:left")
            if hy:
                now_tok.add("hat:up" if hy > 0 else "hat:down")
            for tok in ("hat:left", "hat:right", "hat:up", "hat:down"):
                if tok in now_tok and tok not in self.held:
                    self.held.add(tok)
                    new.append(tok)
                elif tok not in now_tok:
                    self.held.discard(tok)
        elif t == pygame.JOYAXISMOTION:
            if ev.axis in self.stick_axes():
                return []
            for sign, ch in ((1, "+"), (-1, "-")):
                tok = "axis:%d%s" % (ev.axis, ch)
                if ev.value * sign > 0.6:
                    if tok not in self.held:
                        self.held.add(tok)
                        new.append(tok)
                elif ev.value * sign < 0.3:
                    self.held.discard(tok)
        return new

    def stick_axes(self): # Return the current normalized stick-axis values.
        a = self.cfg["axes"]
        return {a.get(k) for k in ("move_x", "move_y", "aim_x", "aim_y")}

    def actions_for(self, tok): # Return all game actions bound to the supplied control token.
        return [a for a, toks in self.cfg["buttons"].items() if tok in [self.canon(t) for t in toks]]

    def is_held(self, action): # Check whether a game action is currently held.
        return any(self.canon(t) in self.held for t in self.cfg["buttons"].get(action, ()))

    def control_of(self, tok): # Return the control token assigned to an action.
        if tok.startswith("ctrl:"):
            return tok[5:]
        if tok.startswith("hat:"):
            return "dpad_" + tok[4:]
        if tok.startswith("button:"):
            return self.cfg["button_names"].get(tok[7:])
        return None

    def token_label(self, tok): # Return a readable label for a keyboard or joystick token.
        c = self.control_of(tok)
        if c:
            return JOY_CTRL_LABELS.get(c, c)
        if tok.startswith("button:"):
            return "Button " + tok[7:]
        if tok.startswith("axis:"):
            return "Axis " + tok[5:]
        return tok

    def assign(self, action, tok): # Assign a control token to a game action.
        if tok is None:
            self.cfg["buttons"][action] = []
        else:
            self.cfg["buttons"][action] = [self.by_name(tok)]
        self.save()

    def _axis(self, idx): # Read and normalize one joystick axis.
        best = 0.0
        for j in self.pads.values():
            try:
                if idx is not None and idx < j.get_numaxes():
                    v = j.get_axis(idx)
                    if abs(v) > abs(best):
                        best = v
            except pygame.error:
                pass
        return best

    def _stick(self, kx, ky): # Read and normalize the requested stick direction.
        a = self.cfg["axes"]
        x, y = self._axis(a.get(kx)), self._axis(a.get(ky))
        dz = float(self.cfg.get("deadzone", 0.35))
        if math.hypot(x, y) < dz:
            return None
        return unit(x, y)

    def move_vec(self): # Return the current movement vector from the configured controls.
        v = self._stick("move_x", "move_y")
        if v:
            return v
        if self.cfg.get("dpad_moves", True):
            hx = hy = 0
            for j in self.pads.values():
                try:
                    for h in range(j.get_numhats()):
                        a, b = j.get_hat(h)
                        hx, hy = hx or a, hy or b
                except pygame.error:
                    pass
            if hx or hy:
                return unit(float(hx), float(-hy))
        return None

    def aim_vec(self): # Return the current aiming vector from the configured controls.
        return self._stick("aim_x", "aim_y")

    def aim_mag(self): # Return the magnitude of the current aiming input.
        a = self.cfg["axes"]
        x, y = self._axis(a.get("aim_x")), self._axis(a.get("aim_y"))
        return min(1.0, math.hypot(x, y))



