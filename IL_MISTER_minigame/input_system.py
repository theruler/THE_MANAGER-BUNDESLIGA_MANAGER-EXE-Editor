import math
import time

import pygame

from camera_system import CAM_GLIDE_SECS, PAN_DEAD_PX, PAN_HYSTERESIS_MS
from celebration_system import T_AFTER, T_CELE
from game_utils import clamp
from geometry import L, SCROLL_MAX_X, SCROLL_MAX_Y, V_MAX_P, V_MIN_P
from joystick import JOY_EVENTS, JOY_KEYS
from lang import tr
from match_config import SPEED_DEFAULT, SPEEDS


class InputMixin: # Keyboard, mouse, and joystick input handling.
    def handle_event(self, ev): # Route a Pygame event to the appropriate input handler.
        if ev.type == pygame.MOUSEMOTION:
            self.mouse_xy, self.mouse_moved_at = ev.pos, time.time()
        if ev.type == pygame.QUIT:
            return "quit"
        if ev.type in JOY_EVENTS:
            return self.handle_joy(ev)
        if self.joymap_open and self.mode == "intro" and ev.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONUP):
            self.jm_mouse(ev)
            return None
        if ev.type == pygame.KEYDOWN and self.joymap_open and self.mode == "intro":
            if ev.key == pygame.K_ESCAPE:
                if self.jm_wait:
                    self.jm_wait = None
                else:
                    self.joymap_open = False
            return None
        if ev.type == pygame.KEYDOWN:
            return self._handle_keydown(ev)
        return self._handle_mouse_event(ev)

    def _handle_keydown(self, ev): # Handle keyboard key-down actions and shortcuts.
        k, uni = ev.key, ev.unicode
        if self.confirm_exit:
            if k in (pygame.K_s, pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                self.abort_match()
            elif k in (pygame.K_n, pygame.K_ESCAPE):
                self.confirm_exit = False
            return None
        if k == pygame.K_ESCAPE:
            if self.mode == "intro" and self.options_open:
                self.options_open, self.lang_open = False, False
                return None
            if self.mode in ("intro", "full"):
                return "quit"
            self.confirm_exit = True
            return None
        self.idle_t = 0.0
        if self.replay and k in (pygame.K_r, pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_p):
            self.stop_replay()
            return None
        if k == pygame.K_SPACE and self.mode == "goal" and self.goal:
            self.goal["t"] = T_CELE + T_AFTER + 0.25
            self.goal["released"] = True
            self.goal["replayed"] = True
            for pl in self.players:
                if pl.state in ("cele", "down"):
                    pl.state, pl.lift = "free", 0.0
            return None
        if self.replay and k not in (pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4, pygame.K_F11, pygame.K_m, pygame.K_h,
                                     pygame.K_PAGEUP, pygame.K_PAGEDOWN, pygame.K_PLUS, pygame.K_MINUS, pygame.K_KP_PLUS,
                                     pygame.K_HOME, pygame.K_END,
                                     pygame.K_KP_MINUS, pygame.K_EQUALS) and uni not in ("+", "-"):
            return None
        if k == pygame.K_F11:
            self.fullscreen = not self.fullscreen
            self.apply_view()
        elif k == pygame.K_F1:
            self.debug = not self.debug
        elif k == pygame.K_F2:
            self.set_scroll(not self.scroll)
        elif k in (pygame.K_F3, pygame.K_F4):
            want = self.zoom + (1 if k == pygame.K_F4 else -1)
            self.zoom = want
            self.apply_view()
            if self.zoom != want and self.mode != "intro": # The screen is too small for the requested zoom.
                self.say(tr("msg.zoom_limit", zoom=self.zoom), (255, 200, 140), 2.0)
        elif k == pygame.K_m:
            self.audio.toggle_mute()
        elif k == pygame.K_l:
            self.slowmo_on = not self.slowmo_on
            if not self.slowmo_on:
                self.slowmo_p = None
            self.save_options()
            if self.mode != "intro":
                self.say(tr("msg.slowmo_on" if self.slowmo_on else "msg.slowmo_off"), (150, 230, 160), 1.8)
        elif k == pygame.K_h:
            self.help_toggle()
        elif self.mode != "intro" and (k in (pygame.K_F5, pygame.K_F6) or uni in ("[", "]")):
            team = self.user_team if self.user_team is not None else (self.cp.team if self.cp else 0)
            self.change_formation(team, -1 if (k == pygame.K_F5 or uni == "[") else 1)
        elif k in (pygame.K_PAGEUP, pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS) or uni == "+":
            self.change_speed(+1)
        elif k in (pygame.K_PAGEDOWN, pygame.K_MINUS, pygame.K_KP_MINUS) or uni == "-":
            self.change_speed(-1)
        elif k == pygame.K_HOME:
            self.set_speed(SPEED_DEFAULT)
        elif k == pygame.K_END:
            self.set_speed(len(SPEEDS) - 1)
        elif k == pygame.K_r and self.mode != "intro":
            self.start_replay()
        elif self.mode == "intro":
            self.su_key(k)
        elif self.mode == "full":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.start_match()
            elif k == pygame.K_s:
                self.mode = "intro"
        elif k in (pygame.K_p, pygame.K_SPACE):
            was_paused = self.paused
            self.paused = not self.paused
            self.charge = None
            self.pan_return_at = 0
            if was_paused and not self.paused and self.cam_manual:
                self.cam_manual = False
                self.cam_glide = CAM_GLIDE_SECS
            if was_paused and not self.paused and self.paused_gesture is not None:
                rs = self.restart if self.mode == "restart" else None
                waiting_for_restart = self.mode in ("foul", "outball", "injury") or (
                    rs is not None and not rs.get("ready")
                )
                if not waiting_for_restart:
                    kind, vec, lob, inten = self.paused_gesture
                    self.paused_gesture = None
                    self.paused_traj_data = None
                    self._applying_paused_gesture = True
                    try:
                        self.user_action(kind, vec, lob, inten)
                    finally:
                        self._applying_paused_gesture = False
        else:
            shift = bool(ev.mod & pygame.KMOD_SHIFT)
            if k == pygame.K_TAB:
                self.switch_player()
            elif k == pygame.K_q:
                self.user_team = None
                self.select_player(None)
                self.say(tr("msg.spectator"), (200, 200, 220), 3)
            elif k == pygame.K_z:
                self.press_action("pass")
            elif k == pygame.K_x:
                self.press_action("shot")
            elif k == pygame.K_c:
                self.press_celebrate()
            elif k == pygame.K_F8:
                self.show_hints = not self.show_hints
                self.save_options()

    def _handle_mouse_event(self, ev): # Handle mouse movement, clicks, and gesture input.
        if ev.type == pygame.MOUSEWHEEL and self.mode == "intro":
            self.su_wheel(ev.y)
        elif ev.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_exit:
                if ev.button == 1:
                    for r, yes in self.exit_btns:
                        if r.collidepoint(ev.pos):
                            if yes:
                                self.abort_match()
                            else:
                                self.confirm_exit = False
                return None
            self.idle_t = 0.0
            if self.replay:
                return None
            if self.mode == "intro":
                if self.joymap_open:
                    self.jm_click(ev.pos, ev.button)
                elif ev.button in (1, 3):
                    self.su_click(ev.pos, ev.button) # Right button removes a shirt number.
                return None
            x, y = ev.pos
            if self.sub_menu:
                self.sub_menu_click(ev.pos) if ev.button == 1 else setattr(self, "sub_menu", None)
                return None
            if ev.button == 2:
                if self.scroll and self.field_y <= y < self.field_y + self.view_h:
                    self.pan_return_at = 0
                    self.pan_drag = {
                        "start": ev.pos,
                        "cam": tuple(self.cam),
                        "moved": False,
                    }
                return None
            if y < self.field_y:
                if ev.button == 3 and self.mode not in ("half", "full"):
                    for r, pl_ in self.board.hit_rows:
                        if r.collidepoint(ev.pos):
                            self.open_sub_menu(pl_, r)
                            return None
                if ev.button in (1, 3):
                    self.board.click(ev.pos, self)
            elif y < self.field_y + self.view_h:
                my = y - self.field_y
                if ev.button == 3:
                    q = self.path_player_at(x, my) if self.paused else None
                    if q is not None and q.path:
                        q.path = None
                    elif self.drag is None:
                        self.drag = [x, my, x, my]
                        self.drag_act, self.drag_btn = "shot", 3
                elif ev.button == 1:
                    ballmod = bool(pygame.key.get_mods() & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT))
                    if self.paused and not ballmod and self.paused_gesture is not None:
                        self.paused_gesture = None
                        self.paused_traj_data = None
                    q = self.path_player_at(x, my) if (self.paused and not ballmod) else None
                    if q is not None:
                        self.pathdrag = dict(p=q, pts=[(q.wx, q.wv)], px=(x, my))
                    elif self.drag is None:
                        self.drag = [x, my, x, my]
                        self.drag_act, self.drag_btn = "pass", 1
        elif ev.type == pygame.MOUSEMOTION and self.pan_drag:
            pd = self.pan_drag
            raw_dx = ev.pos[0] - pd["start"][0]
            raw_dy = ev.pos[1] - pd["start"][1]
            if not pd["moved"] and abs(raw_dx) + abs(raw_dy) >= PAN_DEAD_PX:
                pd["moved"] = True
                self.cam_manual = True
                self.cam_glide = 0.0
                self.pan_return_at = 0
            if pd["moved"]:
                dx = raw_dx / float(max(1, self.zoom))
                dy = raw_dy / float(max(1, self.zoom))
                self.cam[0] = clamp(pd["cam"][0] - dx, 0, SCROLL_MAX_X)
                self.cam[1] = clamp(pd["cam"][1] - dy, 0, SCROLL_MAX_Y)
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 2:
            if self.pan_drag is not None:
                if not self.pan_drag["moved"] and self.cam_manual:
                    self.cam_manual = False
                    self.cam_glide = CAM_GLIDE_SECS
                    self.pan_return_at = 0
                    self.say(tr("msg.camera_ball"), (200, 220, 255), 1.5)
                    if self.paused:
                        self.update_cam(0.0, True)
                elif self.pan_drag["moved"] and self.cam_manual:
                    self.pan_return_at = (0 if self.paused else pygame.time.get_ticks() + PAN_HYSTERESIS_MS)
            self.pan_drag = None
        elif ev.type == pygame.MOUSEMOTION and self.pathdrag:
            pd = self.pathdrag
            _fx, _row, (wx, wv) = self.screen_to_ground(ev.pos[0], ev.pos[1] - self.field_y)
            wx, wv = clamp(wx, 4.0, L - 4.0), clamp(wv, V_MIN_P, V_MAX_P)
            if math.hypot(wx - pd["pts"][-1][0], wv - pd["pts"][-1][1]) >= 3.5:
                pd["pts"].append((wx, wv))
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.pathdrag:
            pd, self.pathdrag = self.pathdrag, None
            q = pd["p"]
            moved = math.hypot(ev.pos[0] - pd["px"][0], ev.pos[1] - self.field_y - pd["px"][1])
            if moved < 8 or len(pd["pts"]) < 2:
                self.pick_player(q)
            else:
                q.path = pd["pts"][1:]
                q.tag = None
                self.say(tr("msg.path_assigned", name=q.name, n=len(q.path)), (255, 255, 255), 2.0)
        elif ev.type == pygame.MOUSEMOTION and self.drag:
            self.drag[2], self.drag[3] = ev.pos[0], ev.pos[1] - self.field_y
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button in (1, 3) and self.drag and ev.button == self.drag_btn:
            x0, y0 = self.drag[0], self.drag[1]
            self.drag = None
            self.idle_t = 0.0
            x1, y1 = ev.pos[0], ev.pos[1] - self.field_y
            if ev.button == 3 and math.hypot(x1 - x0, y1 - y0) < 12:
                self.pick_at(x0, y0)
            else:
                self.finish_gesture(x0, y0, x1, y1, pygame.key.get_mods(), "shot" if ev.button == 3 else "pass")
        return None

    def handle_joy(self, ev): # Translate a joystick event into a game action.
        j = self.joy
        toks = j.process(ev, time.time())
        if not toks:
            return None
        self.idle_t = 0.0
        for tok in toks:
            self.jm_flash[tok] = 0.35
        if self.mode == "intro" and self.joymap_open:
            if self.jm_wait:
                act = self.jm_wait
                self.jm_wait = None
                j.assign(act, toks[0])
            else:
                if any(a == "back" for t in toks for a in j.actions_for(t)):
                    self.joymap_open = False
            return None
        for tok in toks:
            if self.mode == "intro" and tok.startswith("hat:"):
                key = {"hat:up": pygame.K_UP, "hat:down": pygame.K_DOWN, "hat:left": pygame.K_LEFT, "hat:right": pygame.K_RIGHT}[tok]
                self.su_key(key)
                continue
            for act in j.actions_for(tok):
                if self.joy_fire(act) == "quit":
                    return "quit"
        return None

    def joy_fire(self, act): # Execute a joystick-triggered action after checking its binding.
        key = JOY_KEYS.get(act)
        if key is None or key[0] is None:
            return None
        k, uni = key
        if act == "confirm":
            if self.confirm_exit or self.mode in ("intro", "full"):
                pass
            elif self.mode == "goal":
                k = pygame.K_SPACE
            else:
                return None
        elif act == "back":
            if not self.confirm_exit:
                return None
        elif act == "exit_match":
            if self.mode in ("intro", "full") or self.confirm_exit:
                return None
        elif self.confirm_exit or self.mode == "intro":
            return None
        mod = pygame.KMOD_SHIFT if self.joy.is_held("lob") else 0
        return self.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k, unicode=uni, mod=mod))
