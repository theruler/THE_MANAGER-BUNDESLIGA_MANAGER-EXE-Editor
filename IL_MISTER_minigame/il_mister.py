import argparse
import collections
import math
import os
import random
import sys
import time
import pygame
from agonism_system import AGON_DEFAULT, AgonismMixin
from aim_system import AimMixin
from ai_system import AIMixin
from animation_config import ACT_SPEC
from audio_system import Audio
from ball_model import G
from camera_system import CAM_GLIDE_SECS, CameraMixin
from celebration_system import CELE_KINDS, CelebrationMixin, GOAL_FETCH_MAX, T_AFTER, T_CELE
from entities import Ball, Flag, Player, Ref
from fonts import FONTS
from formation_system import DEFAULT_FORMATION, formation_slots, FormationMixin
from game_utils import clamp, dir8, unit
from geometry import (
    depth_k, depth_v_k, FH, FIELD_X0, FW, in_box_fn, L, MAX_Y, PEN_D, pitch_v, s2w, screen_to_world_dir,
    V_BOT, V_GC, V_MAX_P, V_MID, V_MIN_P, V_PEN, V_SPOT, V_TOP, w2s, w2s_jac, Y_OFFSET,
)
from graphics_system import find_file, Graphics, Scoreboard
from input_system import InputMixin
from intro_system import IntroMixin
from options_store import load_options, options_path
from joystick import JOY_IMG, JOY_KEYS, JoyPad
from lang import init_language, Note, ROLE_TAG, T, tr
from layout import compute_layout, SU_H, SU_W
from match_config import FLAG_H, FLAG_R, SPEED_DEFAULT, SPEED_UNIT, SPEEDS, TEAM_COL, TEAM_NAMES
from match_log_system import MatchLogMixin, set_match_log_dir
from path_system import PathMixin
from physics_system import AIR_MIN_Z, PhysicsMixin, REACH_FIRST, STRIKE_REACH, THROW_HOLD_Z
from rendering_system import RenderingMixin
from replay_system import REPLAY_MAX_SECS, ReplayMixin, TORE_FPS
from resources import ask_pic_dir, fatal, find_asset, find_original_sound, load_teams, locate_pic
from restart_system import RestartMixin
from sprite_data import load_data, REF_MOVE, REF_STAND, team_sprite_offset
from stats_system import StatsMixin
from substitution_system import SubstitutionMixin

VERSION = "1.5.2"

class Game(IntroMixin, StatsMixin, AgonismMixin, AimMixin, RestartMixin, InputMixin, MatchLogMixin, ReplayMixin, SubstitutionMixin, FormationMixin, PathMixin, PhysicsMixin, AIMixin, RenderingMixin, CameraMixin, CelebrationMixin): # Main match state, rule sequencing, user control, and frame coordination.
    def __init__(self, args, gfx, audio, screen, notes, teams): # Initialize the match engine and connect resources, teams, and subsystem state.
        self.args, self.gfx, self.audio, self.screen, self.notes = args, gfx, audio, screen, notes
        self.target = screen
        self.teams = teams
        self.sel = [0, 1 if len(teams) > 1 else 0]
        self.form_names = [DEFAULT_FORMATION, DEFAULT_FORMATION]
        self.team_data = [teams[self.sel[0]], teams[self.sel[1]]]
        self.board = Scoreboard(gfx.board_path, FONTS, ROLE_TAG, TEAM_COL, TEAM_NAMES, tr)
        self.board.gfx_icon = gfx.roster_icon
        self.lineup = [None, None]
        self.su_pick = None
        self.replay_auto = not getattr(args, "no_replay", False)
        self.replay_secs = int(getattr(args, "replay_secs", 5) or 5)
        self.tore_dir = getattr(args, "tore_dir", None) or "TORE_OUT"
        self.rec = collections.deque(maxlen=60 * (REPLAY_MAX_SECS + 14))
        self.tick = 0
        self.replay = None
        self.last_scorer = ""
        self._fr = {}
        self._help_cache = None
        self.lang_open = False
        self._su_last_sel = {}
        self.options_path = getattr(args, "options_path", None) # DATA/options.json
        self.options_open = False # OPTIONS page (language, joypad mapping, font, replay...) reached from the INTRO.
        self.langs = T.discover_languages()
        self.help_page = 0
        self._help_paged = False
        self.vsurf = None
        self.su_surf = pygame.Surface((SU_W, SU_H))
        self.su_scroll, self.su_active, self.su_hits = [0, 0], 0, []
        self.joy = JoyPad(getattr(args, "joy_dirs", []), getattr(args, "joy_write_dir", None))
        self.joy_img_path = getattr(args, "joy_img", None)
        self.joymap_open, self.jm_wait, self.jm_rows, self.jm_btns, self.jm_img = False, None, [], [], None
        self.jm_drag, self.jm_spots = None, {}
        self.jm_flash = {}
        self.zoom = args.zoom
        self.scroll = not getattr(args, "noscroll", False)
        self.speed_idx = SPEED_DEFAULT
        self.user_team = 0
        self.ctrl_choice = 0
        self.slowmo_p = None
        self.slowmo_on = not getattr(args, "no_slowmo", False)
        self._gk_press_owner = None
        self._gk_press_idx = None
        self.manual = False
        self.idle_t = 0.0
        self._last_owner = None
        self._poss_prev = None
        self.show_help = False
        self.fullscreen = False
        self.set_view_dims()
        self.font_s = FONTS.get(22)
        self.font_m = FONTS.get(34)
        self.font_t = FONTS.get(18)
        self.font_l = FONTS.get(72)
        self.field_surf = pygame.Surface((FW, FH))
        self.half_secs = max(20.0, args.half * 60.0)
        self.mode = "intro"
        self.paused = False
        self.confirm_exit = False
        self.exit_btns = ()
        self.pathdrag = None
        self.mouse_xy, self.mouse_moved_at = None, -1e9 # Last mouse position and when it moved (cursor aim source).
        self.sub_menu = None
        self.subs_list = []
        self.walk_t = 0.0
        self._preview = None
        self.inj_t = 1.0
        self.flags = []
        self.sub_q, self.subs_used, self.sub_out = [[], []], [0, 0], [set(), set()]
        self.mlog, self.log_saved, self.injury = [], True, None
        self.debug = False
        self.cp = None
        self.msgs = []
        self.big = None
        self.cam = [60.0, 8.0]
        self.cam_manual = False
        self.cam_glide = 0.0 
        self.pan_return_at = 0
        self.pan_drag = None
        self.drag = None
        self.sel_hold_until = 0.0
        self.box_t = {}
        self.ov_set = set()
        self.show_hints = True
        self.flag_grace = 0.0
        self.drag_act = "pass"
        self.drag_btn = 1
        self.charge = None
        self._arrow = None
        self.sprite_surf = pygame.Surface((FW, FH), pygame.SRCALPHA)
        self.paused_gesture = None
        self.paused_traj_data = None
        self.click_mark = None
        self.t_all = 0.0
        self.role_timer = 0.0
        self.stats = self.new_stats()
        self.reset_match()
        self.mode = "intro"

    @staticmethod
    def new_stats(): # Create a new statistics record for the current match.
        return dict(fouls=[0, 0], yellow=[0, 0], red=[0, 0], injured=[0, 0], shots=[0, 0], on_target=[0, 0], saves=[0, 0], blocks=[0, 0], goals=[0, 0], corners=[0, 0],
                    poss=[0.0, 0.0])

    def reset_match(self): # Reset match objects, timers, statistics, and temporary state for a new match.
        self.slowmo_p = None
        self._gk_dribble_attempted = None
        self.agon_lv, self.agon_drag = [AGON_DEFAULT, AGON_DEFAULT], None
        self._backpass_src, self._gk_out_t = None, 0.0
        self.score = [0, 0]
        self.half, self.real_t, self.extra = 1, 0.0, 0.0
        self.stoppage_target = 1.0
        self.att = {0: 1, 1: -1}
        self.players, self.team_p = [], [[], []]
        self.sync_teams()
        for team in (0, 1):
            slots = formation_slots(self.form_names[team])
            self.fix_lineup(team)
            names = self.lineup_names(team)
            for i in range(11):
                p = Player(team, i, names[i] if i < len(names) else "")
                p.apply_slot(slots[i])
                self.players.append(p)
                self.team_p[team].append(p)
        self.ball, self.ref = Ball(), Ref()
        self.first_kick = random.randint(0, 1)
        self.cp = None
        self.foul = self.goal = self.restart = self.outball = None
        self.half_t = 0.0
        self.msgs, self.big = [], None
        self.stats = self.new_stats()
        self.flags = [Flag(0.0, V_TOP, 1.0), Flag(L, V_TOP, -1.0), Flag(0.0, V_BOT, 1.0), Flag(L, V_BOT, -1.0)]
        self.sub_q, self.subs_used, self.sub_out = [[], []], [0, 0], [set(), set()]
        self.injury, self.sub_menu, self.pathdrag = None, None, None
        self.paused = False
        self.paused_gesture = self.paused_traj_data = None
        self._gk_area_violator = None
        self.charge = None
        self._arrow = None
        for t_ in (0, 1):
            for p_, (_r, sq) in zip(self.team_p[t_], self.lineup_slots(t_)):
                p_.sq = sq
                self.apply_skill(p_, self.team_data[t_]["stats"][sq])
        self.mlog, self.log_saved = [], False
        self.log_event(tr("ev.match_start", home=TEAM_NAMES[0], away=TEAM_NAMES[1], fh=self.form_names[0], fa=self.form_names[1]), show=False)
        self.manual, self._last_owner, self._poss_prev = False, None, None
        self.setup_kickoff(self.first_kick, sound=False)


    def update_flags(self, dt): # Animate the referee's flag state.
        live = self.mode in ("play", "goal", "outball")
        b = self.ball
        if self.mode == "restart" and self.restart and self.restart.get("kind") == "corner":
            self.flag_grace = 1.6
        elif self.flag_grace > 0.0:
            self.flag_grace -= dt
        for f in self.flags:
            if live and f.state == "planted":
                if b.owner is None and self.flag_grace <= 0.0:
                    sp = math.hypot(b.vx, b.vv)
                    if abs(b.wx - f.x) < FLAG_R and abs(b.wv - f.v) < FLAG_R * 1.2 and b.z < FLAG_H + 1.5 and sp > 20.0:
                        if f.hit(b.vx, b.vv, sp):
                            self.audio.play("bar" if b.z > 4.5 else "post", clamp(0.4 + sp / 260.0, 0.4, 1.0))
                            b.vx *= -0.4
                            b.vv *= 0.6
                            continue
                for p in self.players:
                    if p.state in ("out", "leaving", "down", "subout", "subin"):
                        continue
                    ddx, ddv = f.x - p.wx, f.v - p.wv
                    dist = math.hypot(ddx, ddv)
                    if dist > FLAG_R * 1.1:
                        continue
                    sp = math.hypot(p.vx, p.vv)
                    if sp > 32.0 and (p.vx * ddx + p.vv * ddv) > 0.4 * sp * max(dist, 0.1):
                        if f.hit(p.vx, p.vv, sp * (1.3 if p.state == "action" else 1.0)):
                            self.audio.play("post", clamp(0.35 + sp / 300.0, 0.35, 0.8))
                            break
            ev = f.update(dt)
            if ev == "thud":
                self.audio.play("bounce", 0.4)
            elif ev == "plant":
                self.audio.play("bounce", 0.25)

    GESTURE_FULL = 0.55
    PASS_LOW = 0.30
    PASS_LONG = 0.70
    REF_CARD_DIST = 9.0 # World units the referee keeps from a player he is carding.
    REF_CARD_TIMEOUT = 4.0 # Seconds after which the card is shown even if the referee has not arrived.
    PASS_CONE = 0.82 # Aim-assist cone (cosine, ~35 deg) for the softest passes.
    PASS_CONE_TIGHT = 0.93 # Cone (~21 deg) reached by the firmest ground passes.
    PASS_NEAR = 70.0
    CHARGE_FULL = 1.0
    AIR_REACH = 18.0 
    ARROW_FADE = 0.45
    ARROW_MIN, ARROW_MAX = 14.0, 64.0

    def gesture_intensity(self, ln): # Convert gesture length and timing into an action intensity.
        return clamp(ln / max(160.0, self.view_w * self.GESTURE_FULL), 0.0, 1.0)

    def gesture_plan(self, x0, y0, x1, y1, act=None): # Convert a user gesture into a planned kick direction and type.
        p = self.cp
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        if p is None or ln < 12:
            return None
        ux, uy = dx / ln, dy / ln
        f = self.gesture_intensity(ln)
        return (act or self.drag_act), screen_to_world_dir(p.wx, p.wv, ux, uy), f

    def kick_plan(self, p, dx, dv, f, lob, free): # Build the launch parameters for a kick using direction, power, and lift.
        D = 14.0 + f * (L * 0.85 - 14.0)
        lx, lv = p.wx + dx * D, p.wv + dv * D
        rad = 12.0 if free else max(14.0, 0.18 * D)
        best = None
        for q in self.team_p[p.team]:
            if q is p or q.state in ("out", "leaving", "down", "subout", "subin", "tunnel"):
                continue
            dd = math.hypot(q.wx - lx, q.wv - lv)
            if dd < rad and (best is None or dd < best[0]):
                best = (dd, q)
        target = None
        if best:
            target = best[1]
            dx, dv = unit(target.wx - p.wx, target.wv - p.wv)
            D = math.hypot(target.wx - p.wx, target.wv - p.wv)
        kind = "pass" if target else "shot"
        if target:
            power = clamp(D * 1.55 + 55.0, 95.0, 300.0)
            lift = max(self.lob_lift(D, power), 18.0) if lob else 0.0
        elif lob:
            power = clamp(D * 1.55 + 55.0, 60.0, 300.0)
            lift = max(self.lob_lift(D, power), 18.0)
        else:
            lift = 28.0
            power = self.power_for_range(dx, dv, D, lift)
        return dict(dx=dx, dv=dv, power=power, lift=lift, kind=kind, target=target, D=D)

    def power_for_range(self, dx, dv, D, lift): # Estimate the power and lift required to reach a target distance.
        b = self.ball
        lo, hi = 25.0, 320.0
        for _ in range(11):
            mid = (lo + hi) / 2.0
            e = self.simulate_ball("kick", dict(dx=dx, dv=dv, power=mid, lift=lift))[-1]
            if math.hypot(e[0] - b.wx, e[1] - b.wv) < D:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    def ground_plan(self, p, kind, dx, dv, f, free=False): # Build a ground-pass or shot plan from the supplied direction and power.
        goalx = L if self.att[p.team] > 0 else 0.0
        gx, gv = unit(goalx - p.wx, V_GC - p.wv)

        def lofted(): # Return whether the current planned action sends the ball into the air.
            kp = self.kick_plan(p, dx, dv, f, True, free)
            if kp["target"] is None and kp["dx"] * gx + kp["dv"] * gv < 0.8:
                kp["kind"] = "pass"
            return kp
        if kind == "shot":
            sx, sv = dx, dv
            if sx * gx + sv * gv > 0.94:
                sx, sv = unit(sx * 0.5 + gx * 0.5, sv * 0.5 + gv * 0.5)
            return dict(dx=sx, dv=sv, power=clamp(140.0 + 180.0 * f, 140.0, 320.0), lift=22.0 + 16.0 * f,
                        kind="shot", target=None, D=0.0)
        if free:
            kp = self.kick_plan(p, dx, dv, f, f >= self.PASS_LOW, True)
            if kp["target"] is None and kp["dx"] * gx + kp["dv"] * gv < 0.8:
                kp["kind"] = "pass"
            return kp
        if f >= self.PASS_LONG:
            return lofted()
        cone = self.PASS_CONE + (self.PASS_CONE_TIGHT - self.PASS_CONE) * clamp(f / self.PASS_LONG, 0.0, 1.0) # Firmer passes obey the aim more.
        bp = self.best_pass(p, aim=(dx, dv), cone=cone)
        if bp:
            _s, q, qx, qv = bp
            dist = math.hypot(qx - p.wx, qv - p.wv)
            ddx, ddv = unit(qx - p.wx, qv - p.wv)
            high = dist >= self.PASS_NEAR and f >= self.PASS_LOW
            power = clamp(dist * 1.55 + 55.0, 95.0, 300.0)
            lift = max(self.lob_lift(dist, power), 18.0) if high else 0.0
            return dict(dx=ddx, dv=ddv, power=power, lift=lift, kind="pass", target=q, D=dist)
        if f < self.PASS_LOW:
            return dict(dx=dx, dv=dv, power=150.0, lift=0.0, kind="pass", target=None, D=0.0)
        return lofted()

    def can_kick_now(self): # Check whether the selected player can start a kick at this moment.
        p, b = self.cp, self.ball
        if p is None or p.state != "free":
            return False
        return b.owner is p or (b.owner is None and math.hypot(b.wx - p.wx, b.wv - p.wv) < REACH_FIRST and b.z < 7.5)


    def pick_player(self, p): # Set the active player and prepare control state for that player.
        if self.mode == "intro" or p.state in ("out", "leaving", "subin", "subout", "tunnel") or p.red:
            return
        if self.ctrl_choice in (0, 1) and p.team != self.ctrl_choice:
            return
        if self.ctrl_choice not in (0, 1):
            self.user_team = p.team
        self.manual = True
        self.sel_hold_until = time.time() + 2.0
        self.select_player(p)

    def minute_label(self): # Format the current match time for display.
        if self.time_over():
            extra = max(1, int(self.extra / max(1.0, self.half_secs) * 45.0) + 1)
            return tr("hud.minute_extra", base=45 * self.half, extra=extra)
        return tr("hud.minute", n=int(self.minute()) + 1)

    def start_match(self): # Initialize and start a new match (needs 11 numbered players per team).
        if not self.lineup_ready():
            return
        self.ctrl_choice = self.user_team if self.user_team in (0, 1) else None
        self.reset_match()
        self.begin_walkon(self.first_kick)

    def minute(self): # Return the current match minute.
        return (self.half - 1) * 45 + clamp(self.real_t / self.half_secs, 0.0, 1.0) * 45

    def time_over(self): # Check whether the current period has reached its end.
        return self.real_t >= self.half_secs

    def update_clock(self, dt): # Advance the match clock while respecting stoppage and speed settings.
        if self.mode in ("restart", "outball", "play"):
            if self.mode == "restart" and self.restart and self.restart["kind"] == "kickoff":
                return
            self.real_t += dt
            if self.time_over():
                self.extra += dt
                own = self.ball.owner
                danger = own is not None and (own.wx / L if self.att[own.team] > 0 else 1 - own.wx / L) > 0.72
                extra_minutes = self.extra / max(1.0, self.half_secs) * 45.0
                if extra_minutes >= self.stoppage_target and not danger:
                    if self.mode == "outball":
                        self.outball = None
                    self.end_half()

    def end_half(self): # Finish the current half and prepare the next match phase.
        self.log_event(tr("ev.end_first" if self.half == 1 else "ev.end_full", a=self.score[0], b=self.score[1]), show=False)
        if self.half == 2:
            self.save_log("finale")
        self.audio.play("whistle_end")
        self.mode = "half" if self.half == 1 else "full"
        self.half_t = 0.0
        self.restart = self.foul = None
        b = self.ball
        b.owner, b.vx, b.vv, b.vz = None, 0.0, 0.0, 0.0
        for p in self.players:
            p.tx = p.tv = None
        self.big = (tr("big.end_first" if self.half == 1 else "big.end_full"), 4.5)
        self.audio.react("whistle_end")
        if self.half == 1:
            self.begin_walkoff()


    def begin_walkoff(self): # Start the players' walk-off sequence at the end of a period.
        for p in self.players:
            if p.state == "out":
                continue
            p.state, p.act, p.path, p.tx, p.tv = "subout", None, None, None, None
            p.walk, p.limp = "off", False
            self.set_gate(p, -1 if p.team == 0 else 1)

    def begin_walkon(self, team): # Start the players' walk-on sequence for a new period.
        self.setup_kickoff(team, sound=False)
        vexit, cx = pitch_v(MAX_Y + 30), L / 2.0
        for t in (0, 1):
            for k, p in enumerate([q for q in self.team_p[t] if q.state != "out"]):
                p.wk_to = (p.wx, p.wv)
                p.tx, p.tv = p.wk_to
                self.set_gate(p, -1 if t == 0 else 1)
                p.wx = cx + p.gate
                p.wv = vexit + 7.0 * k + random.uniform(0.0, 2.0)
                p.state, p.walk, p.act, p.path = "subin", "on", None, None
                p.vx = p.vv = 0.0
                self.post_move(p)
        self.mode, self.walk_t = "walkon", 0.0

    def update_walkon(self, dt): # Advance the player walk-on animation.
        self.walk_t += dt
        busy = [p for p in self.players if p.state == "subin"]
        if busy and self.walk_t < 25.0:
            return
        for p in busy:
            p.state = "free"
            p.wx, p.wv = p.wk_to
        for p in self.players:
            p.walk = None
            p.tx = p.tv = None
            if p.state != "out":
                p.vx = p.vv = 0.0
            self.post_move(p)
        self.mode = "restart"
        rs = self.restart
        if rs is not None:
            rs["t"], rs["ready"], rs["said"] = 0.0, False, False
            self.auto_taker(rs["taker"])
        self.audio.play("whistle")
        if self.half == 1:
            self.audio.react("start")

    def update_half(self, dt): # Advance the half-time or period-transition sequence.
        self.half_t += dt
        walking = any(p.state == "subout" for p in self.players)
        if self.half_t > 5.0 and (not walking or self.half_t > 20.0):
            self.instant_subs()
            self.half, self.real_t, self.extra = 2, 0.0, 0.0
            self.stoppage_target = 1.0
            self._gk_press_owner = None
            self._gk_press_idx = None
            self.att = {0: -1, 1: 1}
            self.big = (tr("big.second_half"), 2.5)
            self.half_t = 0.0
            self.begin_walkon(1 - self.first_kick)


    def call_foul(self, off, victim, yellow_p, red_p, fall=True, spot=None): # Register a foul and start its associated referee and player reactions.
        rs = self.restart if self.mode == "restart" else None
        if rs is not None and rs.get("kind") == "goalkick":
            return
        tracked = getattr(self, "_gk_area_violator", None)
        if tracked is off and victim.role == "GK" and self.ball.owner is victim:
            own_gx = 0.0 if self.att[victim.team] > 0 else L
            if in_box_fn(off.wx, off.wv, own_gx):
                return
        b = self.ball
        self.stoppage_target += 0.28
        if spot is None:
            spot = (clamp(victim.wx, 3.0, L - 3.0), clamp(victim.wv, V_TOP + 1.0, V_BOT - 1.0))
        own_gx = 0.0 if self.att[off.team] > 0 else L
        in_box = in_box_fn(spot[0], spot[1], own_gx)
        card = None
        r = random.random()
        if r < red_p:
            card = "R"
        elif r < red_p + yellow_p:
            card = "Y"
        self.mode = "foul"
        self.foul = dict(off=off, victim=victim, card=card, kind="penalty" if in_box else "free", spot=spot, t=0.0, shown=False)
        b.owner, b.vx, b.vv, b.vz = None, 0.0, 0.0, 0.0
        self.stats["fouls"][off.team] += 1
        self.log_event(tr("ev.foul", off=off.label(), victim=victim.label(), team=TEAM_NAMES[off.team]), team=off.team)
        if fall:
            self.begin_action(victim, "fall", "E" if victim.dx >= 0 else "W")
        for p in self.players:
            if p is not victim and not p.busy():
                p.tx = p.tv = None
        self.audio.play("whistle_long")
        self.audio.play("tackle", 0.9)
        if card or random.random() < 0.5:
            self.audio.react("foul")

    def update_foul(self, dt): # Advance the foul, card, and player-recovery sequence.
        f = self.foul
        f["t"] += dt
        off = f["off"]
        ref_ready = math.hypot(self.ref.wx - off.wx, self.ref.wv - off.wv) < self.REF_CARD_DIST + 3.0 or f["t"] > self.REF_CARD_TIMEOUT
        if f["card"] and not f["shown"] and f["t"] > 1.3 and ref_ready: # The referee must have walked up to the player first.
            f["shown"] = True
            card = f["card"]
            second = False
            if card == "Y":
                off.yellow += 1
                self.stats["yellow"][off.team] += 1
                if off.yellow >= 2:
                    card = "R"
                    f["card"] = "R"
                    second = True
            if card == "R":
                self.stats["red"][off.team] += 1
            self.ref.card, self.ref.card_t = card, 1.8
            if card == "Y":
                ckey, ccol, csecs = "ev.card_yellow", (255, 230, 70), 4
            else:
                ckey, ccol, csecs = ("ev.card_red_second" if second else "ev.card_red"), (255, 90, 90), 5
            self.log_event(tr(ckey, p=off.label(), team=TEAM_NAMES[off.team]), ccol, csecs)
            self.audio.react("card")
        end_t = 3.6 if f["card"] else 2.2
        if f["t"] > end_t and not self.ref.card and (f["shown"] or not f["card"]):
            if f["card"] == "R" or off.yellow >= 2:
                off.red = True
                off.state, off.act = "leaving", None
                self.set_gate(off)
                off.tx, off.tv = L / 2.0 + off.gate, V_MAX_P
                if self.cp is off:
                    self.select_player(None)
            if self.time_over() and f["kind"] != "penalty":
                self.end_half()
                return
            self.start_restart(f["kind"], f["victim"].team, f["spot"])
            if f["kind"] == "penalty":
                own_gx = 0.0 if self.att[off.team] > 0 else L
                px = PEN_D if own_gx == 0.0 else L - PEN_D
                self.ball.wx, self.ball.wv = px, V_PEN
                self.restart["pos"] = (px, V_PEN)
                self.log_event(tr("ev.penalty"), secs=3, team=f["victim"].team)
                self.big = (tr("big.penalty"), 2.0)

    def score_goal(self, team, gx): # Register a goal and update the score and match statistics.
        b = self.ball
        b.pass_active = False
        self.stoppage_target += 0.45
        self.score[team] += 1
        self.stats["goals"][team] += 1
        own_goal = b.last is not None and b.last.team != team
        if own_goal:
            sc = b.last
        elif b.last is not None and b.last.team == team:
            sc = b.last
        else:
            candidates = [p for p in self.team_p[team] if p.state != "out" and p.role != "GK"]
            sc = min(candidates, key=lambda p: math.hypot(p.wx - b.wx, p.wv - b.wv)) if candidates else self.team_p[team][0]
        kinds = [k for k, w in CELE_KINDS for _ in range(w)]
        self.goal = dict(team=team, scorer=sc, t=0.0, kick=1 - team, own=own_goal, kind=random.choice(kinds), s={}, part=set(),
                         released=False, pairs=None)
        self.mode = "goal"
        if own_goal:
            self.log_event(tr("ev.own_goal", p=sc.label(), own_team=TEAM_NAMES[sc.team], team=TEAM_NAMES[team],
                              a=self.score[0], b=self.score[1]), secs=6, team=team)
        else:
            self.log_event(tr("ev.goal", p=sc.label(), team=TEAM_NAMES[team], a=self.score[0], b=self.score[1]), secs=6, team=team)
        self.last_scorer = sc.name
        b.owner = None
        b.vx *= 0.25
        b.vv *= 0.25
        b.vz = 0.0
        self.big = (tr("big.goal", team=TEAM_NAMES[team]), 4.0)
        self.audio.play("net")
        self.audio.play("whistle")
        self.audio.react("goal")


    def update_goal(self, dt): # Advance the goal presentation and celebration sequence.
        g = self.goal
        g["t"] += dt
        t = g["t"]
        sc = g["scorer"]
        team = g["team"]
        if t < 0.05 and not g["own"]:
            sc.state, sc.act = "free", None
        mates = [p for p in self.team_p[team] if p.role != "GK" and p is not sc and p.state not in ("out", "leaving") and not p.red]
        if t > 0.5 and not g["own"] and not g["released"] and sc.state not in ("out", "leaving"):
            if g.get("said") is None:
                g["said"] = True
                self.log_event(tr("ev.cele." + g["kind"]), secs=3, team=g["team"])
            getattr(self, "cele_" + g["kind"])(g, t, sc, mates)
        if t >= T_CELE and not g["released"]:
            g["released"] = True
            for p in self.players:
                p.lift = 0.0
                if p.state in ("cele", "down"):
                    p.state = "free"
        self.goal_fetch_ball(g, t)
        self.cele_walk_home(g, t)
        done_t = T_CELE + T_AFTER
        if g["own"]:
            done_t = 4.0
        if not g.get("fetched") and t < done_t + GOAL_FETCH_MAX:
            return # Replay and kickoff wait until the ball has been carried back to the centre.
        if t > done_t and not g.get("replayed"):
            g["replayed"] = True
            if self.replay_auto:
                if self.start_replay(end_tick=self.tick, secs=self.replay_secs + t + 0.5):
                    return
        if t > done_t + 0.2:
            if self.time_over():
                extra_minutes = self.extra / max(1.0, self.half_secs) * 45.0
                if extra_minutes >= self.stoppage_target:
                    self.end_half()
                    return
            self.log_event(tr("ev.kickoff", team=TEAM_NAMES[g["kick"]]), secs=3, team=g["kick"])
            self.setup_kickoff(g["kick"], walk=True)

    def teams_at(self, gx): # Return the teams positioned near the supplied field coordinate.
        a = next(t for t in (0, 1) if self.att[t] == (-1 if gx == 0.0 else 1))
        return a, 1 - a


    def opponents(self, team): # Return the opposing team for the supplied team index.
        return [q for q in self.team_p[1 - team] if q.state not in ("out", "leaving")]


    def update_ref(self, dt): # Update referee movement and animation state.
        r, b, m = self.ref, self.ball, self.mode
        if r.card_t > 0:
            r.card_t -= dt
            if r.card_t <= 0:
                r.card = None
        if m == "foul" and self.foul and self.foul["card"]:
            # Carding: walk up to the offender (stopping at talking distance on the side the referee comes from).
            off = self.foul["off"]
            ux, uv = unit(r.wx - off.wx, r.wv - off.wv, (-1.0, 0.0))
            tx = clamp(off.wx + ux * self.REF_CARD_DIST, 8.0, L - 8.0)
            tv = clamp(off.wv + uv * self.REF_CARD_DIST, V_TOP + 2.0, V_BOT + 2.0)
        elif m == "foul" and self.foul:
            sx, sv = self.foul["spot"]
            tx, tv = sx - 8, sv + (11 if sv < V_MID else -11)
        elif m == "goal":
            tx, tv = L / 2 - 30, V_SPOT + 24
        elif m == "restart" and self.restart:
            rs = self.restart
            offender = rs.get("area_violator")
            if (rs["kind"] == "goalkick" and rs.get("area_stage", 0) >= 1
                    and offender is not None and offender.state not in ("out", "leaving")):
                own_gx = 0.0 if self.att[rs["team"]] > 0 else L
                toward_pitch = 1.0 if own_gx == 0.0 else -1.0
                tx = clamp(offender.wx + toward_pitch * 7.0, 12.0, L - 12.0)
                tv = clamp(offender.wv + (4.0 if offender.wv < V_MID else -4.0),
                           V_TOP + 8.0, V_BOT - 8.0)
            else:
                x, v = rs["pos"]
                d = self.att[rs["team"]]
                tx = clamp(x - d * 14.0, 12.0, L - 12.0)
                tv = clamp(v + (20.0 if v < V_MID else -20.0), V_TOP + 8.0, V_BOT - 8.0)
        elif m == "outball" and self.outball:
            rs = self.outball
            x, v = self.visible_pos(rs["pos"])
            d = self.att[rs["team"]]
            tx = clamp(x - d * 14.0, 12.0, L - 12.0)
            tv = clamp(v + (20.0 if v < V_MID else -20.0), V_TOP + 8.0, V_BOT - 8.0)
        elif m == "injury" and self.injury:
            q = self.injury["p"]
            tx, tv = q.wx + 6, q.wv + (4 if q.wv < V_MID else -4)
        elif m in ("half", "full", "intro"):
            tx, tv = L / 2 - 30, V_SPOT + 24
        else:
            tx, tv = b.wx - 12, b.wv + (24 if b.wv < V_MID else -24)
        tx, tv = self.visible_pos((tx, tv), 16.0) # Target well inside the screen edges: the final edge clamp must never pull him sideways.
        dx, dv = tx - r.wx, tv - r.wv
        dist = math.hypot(dx, dv)
        spd = 48.0 * min(1.0, max(0.35, dist / 20.0)) # Never creep: a minimum walking pace until the target is reached.
        if dist > 30.0:
            spd = 48.0 * min(1.7, 1.0 + (dist - 30.0) / 50.0) # Far away (corner on the opposite side): jog so he arrives in time, never teleports.
        if dist > 0.8:
            r.vx += (dx / dist * spd - r.vx) * min(1.0, 6 * dt)
            r.vv += (dv / dist * spd - r.vv) * min(1.0, 6 * dt)
        else:
            r.vx *= 0.8
            r.vv *= 0.8
        r.wx += r.vx * dt * depth_k(r.wv)
        r.wv = clamp(r.wv + r.vv * dt * depth_v_k(r.wv, r.wx), V_MIN_P, V_MAX_P)
        px, gy = w2s(r.wx, r.wv)
        if px < 6.5 or px > FW - 6.5:
            r.wx = s2w(clamp(px, 6.5, FW - 6.5), gy)[0]
            px, gy = w2s(r.wx, r.wv)
        r.sx, r.sy = px, gy
        sp = math.hypot(r.vx, r.vv)
        r.stride += sp * dt
        if r.face_t > 0:
            r.face_t -= dt
        if r.card and self.foul:
            fx, fv = self.foul["off"].sx, self.foul["off"].sy
            nd = dir8(fx - px, fv - gy, True)
            if nd and r.face_t <= 0:
                r.face, r.face_t = nd, 0.2
        elif sp > 2.5:
            x1, y1 = w2s(r.wx + r.vx * 0.06 * depth_k(r.wv),
                         r.wv + r.vv * 0.06 * depth_v_k(r.wv, r.wx))
            nd = dir8(x1 - px, y1 - gy, True)
            if nd and nd != r.face and r.face_t <= 0:
                r.face, r.face_t = nd, 0.12
        if sp > 2.5:
            cyc = REF_MOVE[r.face] # Any visible movement uses the walking cycle (also while a card is up).
            r.sid = cyc[int(r.stride / 5.0) % len(cyc)]
        else:
            r.sid = REF_STAND[r.face]


    @property
    def speed(self): # Return the current match simulation speed multiplier.
        base = SPEEDS[self.speed_idx] * SPEED_UNIT
        sp = getattr(self, "slowmo_p", None)
        if sp is not None:
            a = sp.act
            w = a.get("slow") if (sp.state == "action" and a is not None) else None
            if w is not None and a["t"] < w[1]:
                if a["t"] >= w[0]:
                    return min(base, SPEEDS[0] * SPEED_UNIT)
                return base
            self.slowmo_p = None
        return base

    def strike_will_hit(self, p, key, kw): # Estimate whether the specified player action can contact the ball.
        b = self.ball
        if b.owner is not None or self.mode != "play":
            return False
        spec = ACT_SPEC[key]
        T = spec["contact"] * spec["fdur"]
        tx, tv = self.ball_pred(T)
        zt = max(0.0, b.z + b.vz * T - 0.5 * G * T * T)
        reach, zlo, zhi = STRIKE_REACH[key]
        travel = 0.0
        if kw.get("assist"):
            reach, zlo, zhi = reach + 7.0, (-2.0 if key == "bicycle" else zlo - 3.0), zhi + 8.0
            travel = (85.0 if key == "header_dive" else 65.0) * T * 0.6
        elif key in ("header", "header_dive"):
            travel = (95.0 if key == "header_dive" else 34.0) * T * 0.5
        d = math.hypot(tx - p.wx, tv - p.wv)
        return d - travel <= reach and zlo <= zt <= zhi

    @property
    def speed_label(self): # Format the current simulation speed for the interface.
        return SPEEDS[self.speed_idx]

    def select_player(self, p, quiet=False): # Select a player and update the user-control state.
        if self.cp is p:
            return
        self.paused_gesture = None
        self.paused_traj_data = None
        if self.cp:
            self.cp.ctrl = False
            self.cp.kvec = None
        self.cp = p
        if p:
            p.ctrl = True
            if not quiet:
                if p.state not in ("subin", "subout"):
                    p.tx = p.tv = None
                self.say(tr("msg.control", name=p.label(), role=self.natural_role(p.sq)), (255, 255, 255), 2.5)


    def user_move_input(self): # Read manual movement input for the currently controlled player.
        p = self.cp
        if p is None:
            return
        if p.state == "out" or p.red:
            self.select_player(None)
            return
        if p.state in ("subin", "subout", "tunnel"):
            return
        rs = self.restart if self.mode == "restart" else None
        if rs is not None and rs.get("taker") is p:
            p.kvec = None
            return
        k = pygame.key.get_pressed()
        x = (k[pygame.K_RIGHT] or k[pygame.K_d]) - (k[pygame.K_LEFT] or k[pygame.K_a])
        v = (k[pygame.K_DOWN] or k[pygame.K_s]) - (k[pygame.K_UP] or k[pygame.K_w])
        jv = None if (x or v) else self.joy.move_vec()
        if x or v:
            p.kvec = unit(float(x), float(v))
        elif jv:
            p.kvec = jv
        else:
            p.kvec = None
        if p.kvec:
            p.tx = p.tv = None
            p.path = None
            self.idle_t = 0.0

    def screen_to_ground(self, mx, my): # Convert a mouse position into projected field coordinates.
        cx, cy, ox, oy = self.cam_view()
        fx = cx + (mx + ox) / self.zoom
        row = cy + (my + oy) / self.zoom
        return fx, row, s2w(fx, row - Y_OFFSET - 10)

    def user_action(self, kind, vec=None, lob=False, inten=None): # Execute a manual player action from the selected input and direction.
        p = self.cp
        if p is None or p.state != "free":
            return
        self.idle_t = 0.0
        b = self.ball
        dx, dv = unit(*(vec or self.aim_dir(p)))
        d = math.hypot(b.wx - p.wx, b.wv - p.wv)
        have = b.owner is p
        rs = self.restart if self.mode == "restart" else None
        setp = rs is not None and rs["taker"] is p
        if setp and not rs["ready"] and rs["t"] < 1.0:
            return
        if kind == "cele":
            if setp:
                return
            return self.user_celebrate(p, dx, dv)
        f = clamp(inten if inten is not None else (0.25 if kind == "pass" else 0.75), 0.0, 1.0)
        if setp and rs["kind"] == "throw":
            bp = self.best_pass(p, aim=(dx, dv), cone=0.6)
            if bp:
                _s, q, qx, qv = bp
                dist = math.hypot(qx - p.wx, qv - p.wv)
                ddx, ddv = unit(qx - p.wx, qv - p.wv)
                power = clamp(dist * 1.4 + 40, 80, 170)
                self.start_throw(p, ddx, ddv, power, self.lob_lift(dist, power, -10.0), q)
            else:
                self.start_throw(p, dx, dv, 80.0 + 90.0 * f, 45.0)
            return
        ground = have or setp or (self.mode == "play" and b.owner is None and
                                  d < REACH_FIRST and b.z <= AIR_MIN_Z)
        if ground:
            applying = bool(getattr(self, "_applying_paused_gesture", False))
            kp = self.ground_plan(p, kind, dx, dv, f, self.paused or applying)
            tactical_pass = bool(applying and kp["kind"] == "pass" and kp["target"] is not None)
            self.start_kick(p, kp["dx"], kp["dv"], kp["power"], kp["lift"], kp["kind"],
                            target=kp["target"], tactical_pass=tactical_pass)
            return
        shot = kind == "shot"
        if p.role == "GK" and self.mode == "play" and b.owner is None and b.z >= 5 and d < 20:
            self.begin_action(p, "punch", "E" if b.wx > p.wx else "W", assist=True)
            return
        air = self.air_action(p, shot, (dx, dv))
        if air:
            if air == "volley":
                self.log_move("volley", p)
                self.start_kick(p, dx, dv, (170.0 + 110.0 * f) if shot else (120.0 + 80.0 * f), 20.0,
                                "shot" if shot else "pass", special=True, steer=True)
            elif air == "bicycle":
                self.start_aerial(p, "bicycle", dx, dv, 255.0, 30.0, "shot", assist=True, steer=True)
            elif air == "header_dive":
                self.start_aerial(p, "header_dive", dx, dv, 230.0 if shot else 150.0, 22.0,
                                  "shot" if shot else "pass", assist=True, steer=True)
            else:
                self.start_aerial(p, "header", dx, dv, 230.0 if shot else 150.0, 22.0,
                                  "shot" if shot else "pass", assist=True, steer=True)
            return
        if p.role == "GK" and self.mode == "play" and shot:
            self.start_dive(p, p.wv + dv * 20)
            return
        aim = (dx, dv) # What the user is pointing at: where a successful tackle should send the ball.
        if b.owner is not None and b.owner.team != p.team and vec is None:
            dx, dv = unit(b.owner.wx - p.wx, b.owner.wv - p.wv) # The lunge itself still homes in on the carrier.
        self.start_tackle(p, dx, dv, "slide" if shot else "stand", aim=aim)

    def user_show(self, p, kind, dx, dv): # Display the feedback associated with a manual player action.
        near = [q for q in self.opponents(p.team) if math.hypot(q.wx - p.wx, q.wv - p.wv) < 10 and not q.busy()]
        if near and self.mode == "play" and random.random() < 0.5:
            self.call_foul(near[0], p, 0.35, 0.02)
        else:
            self.begin_action(p, "fall", "E" if p.dx >= 0 else "W")
            if self.mode == "play" and random.random() < 0.6:
                self.log_event(tr("ev.dive_fake", p=p.label()), secs=2.5, team=p.team)
                self.audio.react("foul")

    def user_celebrate(self, p, dx, dv): # Start a celebration requested by the user.
        pool = ["moon", "moon_back", "dance", "pump"]
        if self.mode == "play" and any(math.hypot(q.wx - p.wx, q.wv - p.wv) < 14 and not q.busy() for q in self.opponents(p.team)):
            pool.append("fall")
        pick = random.choice(pool)
        if pick == "fall":
            return self.user_show(p, "fall", dx, dv)
        if pick == "moon":
            self.begin_action(p, "moonwalk", self.side_of(p, dx, dv), dx=dx, dv=dv, vel=(dx * 22.0, dv * 22.0), repeat=5)
        elif pick == "moon_back":
            self.begin_action(p, "moonwalk", self.side_of(p, -dx, -dv), dx=-dx, dv=-dv, vel=(-dx * 22.0, -dv * 22.0), repeat=5)
        elif pick == "dance":
            self.begin_action(p, "cele", "E", repeat=5)
        else:
            self.begin_action(p, "punch", self.side_of(p, dx, dv), show=True, repeat=3)

    def press_celebrate(self): # Handle the user command to trigger a celebration.
        if self.mode == "goal":
            return self.goal_celebrate()
        self.user_action("cele")

    def goal_celebrate(self): # Choose and start the scorer's celebration sequence.
        g = self.goal
        if g is None or g["own"] or g.get("replayed") or self.user_team is None or g["team"] != self.user_team:
            return
        if not g["released"] and g["t"] > 0.5:
            return
        g["kind"] = random.choice([k for k, w in CELE_KINDS for _ in range(w)])
        g.update(released=False, said=None, s={}, part=set(), pairs=None)
        g["t"] = 0.5
        for pl in self.players:
            if pl.state in ("cele", "down"):
                pl.state, pl.lift = "free", 0.0

    def air_options(self, p, shot=True, aim=None): # Calculate available actions for a player contesting an aerial ball.
        b = self.ball
        if self.mode != "play" or b.owner is not None or b.z < AIR_MIN_Z:
            return []
        d = math.hypot(b.wx - p.wx, b.wv - p.wv)
        if d >= self.AIR_REACH:
            return []
        out = []
        if b.z >= 5.0:
            out.append("header")
        if b.z < 9.0 and d < 12.0:
            out.append("volley")
        if shot and b.z >= 6.5 and d < 14.0:
            out.append("bicycle")
        if aim is not None and 5.0 <= b.z <= 14.0 and 10.0 <= d < self.AIR_REACH:
            ux, uv = unit(b.wx - p.wx, b.wv - p.wv)
            if ux * aim[0] + uv * aim[1] >= 0.6:
                out.append("header_dive")
        return out

    def air_action(self, p, shot=True, aim=None): # Execute the selected aerial action.
        opts = self.air_options(p, shot, aim)
        if not opts:
            return None
        for k, pr in (("header_dive", 0.45), ("bicycle", 0.40), ("volley", 0.40)):
            if k in opts and random.random() < pr:
                return k
        return "header" if "header" in opts else opts[0]


    def press_action(self, act): # Execute a user-requested action button.
        p = self.cp
        if p is None or p.state != "free" or self.charge is not None:
            return
        rs = self.restart if self.mode == "restart" else None
        setp = rs is not None and rs.get("taker") is p
        if setp and not rs["ready"] and rs["t"] < 1.0:
            return
        if (self.can_kick_now() or setp) and not self.paused and not self.replay and self.mode in ("play", "restart"):
            self.charge = dict(act=act, t0=time.time())
            self.idle_t = 0.0
            return
        self.user_action(act)

    def charge_level(self): # Return the current accumulated shot or pass charge.
        c = self.charge
        return 0.0 if c is None else clamp((time.time() - c["t0"]) / self.CHARGE_FULL, 0.0, 1.0)

    def update_charge(self): # Advance charge accumulation while the action button is held.
        c = self.charge
        if c is None:
            return
        p = self.cp
        if p is None or p.state != "free" or self.paused or self.replay or self.mode not in ("play", "restart"):
            self.charge = None
            return
        act = c["act"]
        key = JOY_KEYS.get(act)
        held = self.joy.is_held(act) or bool(key and key[0] is not None and pygame.key.get_pressed()[key[0]])
        if held:
            self.idle_t = 0.0
            return
        f = self.charge_level()
        self.charge = None
        self.user_action(act, None, False, f)

    def set_font_mode(self, modern): # Switch between the bitmap and modern text-rendering modes.
        FONTS.modern = modern
        self.font_s = FONTS.get(22)
        self.font_m = FONTS.get(34)
        self.font_t = FONTS.get(18)
        self.font_l = FONTS.get(72)
        self._fr = {}
        self._help_cache = None

    def abort_match(self): # Abort the current match and clean up its transient state.
        self.confirm_exit = False
        self.slowmo_p = None
        self._gk_dribble_attempted = None
        self.save_log("interrotta")
        self.replay = None
        self.paused = False
        self.paused_gesture = self.paused_traj_data = None
        self.charge = None
        self._arrow = None
        self.sub_menu = None
        self.drag = self.pathdrag = None
        self.show_help = False
        self.help_page = 0
        self.audio.silence()
        self.options_open = False
        self.mode = "intro"


    def set_speed(self, idx): # Set the match simulation speed from the available presets.
        self.speed_idx = int(clamp(idx, 0, len(SPEEDS) - 1))
        self.say(tr("msg.speed", speed=self.speed_label), (150, 230, 160), 1.8)

    def change_speed(self, delta): # Move to the adjacent simulation-speed preset.
        self.speed_idx = int(clamp(self.speed_idx + delta, 0, len(SPEEDS) - 1))
        self.say(tr("msg.speed", speed=self.speed_label), (150, 230, 160), 1.8)

    def set_scroll(self, on): # Enable or disable field scrolling.
        mem = getattr(self, "zoom_mem", {})
        mem[bool(self.scroll)] = self.zoom
        self.scroll = on
        self.cam_manual = False
        self.pan_drag = None
        self.zoom = mem.get(bool(on), 5 if on else 3) # Each mode remembers its own zoom.
        self.apply_view()


    JM_SNAP = 34.0
    JM_DRAGGABLE = ("triangle", "circle", "cross", "square", "l1", "l2", "r1", "r2", "select", "start", "l3", "r3")

    def jm_near(self, vx, vy, skip=None, rad=16.0): # Find the nearest joystick-mapping hotspot to the supplied point.
        best = None
        for name, (cx, cy) in self.jm_spots.items():
            if name == skip or name not in self.JM_DRAGGABLE:
                continue
            d = math.hypot(cx - vx, cy - vy)
            if d <= rad and (best is None or d < best[0]):
                best = (d, name)
        return best[1] if best else None

    def jm_mouse(self, ev): # Handle mouse interaction with the joystick-mapping screen.
        d = self.jm_drag
        if d is None:
            return
        d["pos"] = self.su_to_virtual(ev.pos)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            tgt = self.jm_near(d["pos"][0], d["pos"][1], skip=d["ctrl"], rad=self.JM_SNAP)
            if tgt:
                self.joy.swap_controls(d["ctrl"], tgt)
            self.jm_drag = None

    def jm_click(self, pos, button=1): # Apply a click to the joystick-mapping interface.
        vx, vy = self.su_to_virtual(pos)
        if self.jm_wait:
            self.jm_wait = None
            return
        if button == 1:
            c = self.jm_near(vx, vy)
            if c:
                self.jm_drag = {"ctrl": c, "pos": (vx, vy)}
                return
        for r, tag in self.su_hits:
            if r.collidepoint(vx, vy):
                if tag[0] == "close":
                    self.joymap_open = False
                elif tag[0] == "reset":
                    self.joy.reset()
                elif tag[0] == "act":
                    if button == 3:
                        self.joy.assign(tag[1], None)
                    else:
                        self.jm_wait = tag[1]
                return

    def su_scale(self): # Calculate the scale factor for the substitution interface.
        sc = min(self.W / float(SU_W), self.H / float(SU_H))
        return sc, (self.W - SU_W * sc) / 2.0, (self.H - SU_H * sc) / 2.0

    def su_to_virtual(self, pos): # Convert screen coordinates to substitution-panel coordinates.
        sc, ox, oy = self.su_scale()
        return (pos[0] - ox) / sc, (pos[1] - oy) / sc

    def switch_player(self): # Switch manual control to another eligible player.
        if self.cp:
            team = self.cp.team
        elif self.ctrl_choice in (0, 1):
            team = self.ctrl_choice
        elif self.user_team is not None:
            team = self.user_team
        else:
            team = self.ball.last_team if self.ball.last_team in (0, 1) else 0
        self.user_team = team
        self.manual = True
        c = self.sel_candidates(team)[:5]
        if not c:
            return
        nxt = c[(c.index(self.cp) + 1) % len(c)] if self.cp in c else c[0]
        self.sel_hold_until = time.time() + 2.0
        self.select_player(nxt)

    def pick_at(self, mx, my): # Find the selectable player at the supplied screen position.
        if mx < 0 or my < 0 or mx >= self.view_w or my >= self.view_h:
            return
        fx, row, _w = self.screen_to_ground(mx, my)
        best = None
        for p in self.players:
            if p.state == "out":
                continue
            dd = math.hypot(p.sx - fx, (p.sy + Y_OFFSET + 5) - row)
            if dd < 20 and (best is None or dd < best[0]):
                best = (dd, p)
        if best:
            self.pick_player(best[1])

    def finish_gesture(self, x0, y0, x1, y1, mods, act="pass"): # Finalize a user gesture and dispatch the resulting action.
        if x0 < 0 or y0 < 0 or x0 >= self.view_w or y0 >= self.view_h:
            return
        dx, dy = x1 - x0, y1 - y0
        ln = math.hypot(dx, dy)
        p = self.cp
        if p is None:
            return
        if ln < 12:
            fx, row, (wx, wv) = self.screen_to_ground(x1, y1)
            p.tx, p.tv = wx, clamp(wv, V_MIN_P, V_MAX_P)
            p.path = None
            self.click_mark = [fx, row, 2.0]
            return
        plan = self.gesture_plan(x0, y0, x1, y1, act)
        if plan is None:
            return
        if self.paused and (act == "shot" or mods & (pygame.KMOD_SHIFT | pygame.KMOD_CTRL)):
            self.paused_gesture = (plan[0], plan[1], False, plan[2])
            self.paused_traj_data = self.build_shot_preview(x0, y0, x1, y1, act)
            return
        self.user_action(plan[0], plan[1], False, plan[2])

    def intensity(self): # Calculate the current action intensity from the user input state.
        b = self.ball
        if self.mode == "goal":
            return 1.0
        near = max(0.0, 1.0 - min(b.wx, L - b.wx) / 110.0)
        return clamp(0.15 + 0.7 * near * (0.5 + 0.5 * min(1.0, math.hypot(b.vx, b.vv) / 200.0)), 0.0, 1.0)

    def update(self, dt): # Advance match state, input, physics, AI, camera, and timers for one frame.
        if self.mode == "intro":
            self.update_cam(dt, True)
            self.audio.intro_tick(dt) # Original intro music (BM2TITLE.CMF) while INTRO / OPTIONS are shown.
            return
        self.t_all += dt
        self.idle_t += dt
        self.audio.focus = clamp((self.ball.wx - L / 2.0) / (L / 2.0), -1.0, 1.0)
        self.update_clock(dt)
        if self.mode == "play" and self.ball.owner is not None:
            self.stats["poss"][self.ball.owner.team] += dt
        if self.mode == "restart":
            self.update_restart(dt)
        elif self.mode == "foul":
            self.update_foul(dt)
        elif self.mode == "goal":
            self.update_goal(dt)
        elif self.mode == "outball":
            self.update_outball(dt)
        elif self.mode == "subs":
            self.update_subs(dt)
        elif self.mode == "injury":
            self.update_injury(dt)
        elif self.mode == "half":
            self.update_half(dt)
        elif self.mode == "walkon":
            self.update_walkon(dt)
        if self.mode == "restart" and self.restart is not None:
            self.maybe_ai_subs()
            rs = self.restart
            if any(self.sub_q) and not rs["ready"] and not rs["taker"].busy():
                self.begin_subs()
        if self.mode == "play":
            self.update_injuries(dt)
        if self.ball.pen and (self.mode != "play" or self.ball.owner is not None or self.ball.last_team != self.ball.pen_team):
            self.ball.pen = False
        self.check_gk_box_time(dt)
        self.check_gk_handling(dt)
        self.update_agonism(dt)
        self.check_overlap_steal()
        self.update_flags(dt)
        self.auto_select()
        self.ai_update(dt)
        self.user_move_input()
        self.update_charge()
        for p in self.players:
            self.step_player(p, dt)
        self.throw_pose()
        if self.mode in ("play", "goal", "restart", "foul", "half", "full", "outball"):
            self.update_ball(dt)
        self.update_ref(dt)
        self.update_cam(dt)
        self.rec.append((self.tick, self.snapshot(), (self.cam[0], self.cam[1])))
        self.tick += 1
        self.audio.update(dt, self.intensity(), self.mode)
        for m in self.msgs:
            m[2] -= dt
        self.msgs = [m for m in self.msgs if m[2] > 0]
        if self.big:
            self.big = (self.big[0], self.big[1] - dt)
            if self.big[1] <= 0:
                self.big = None
        if self.click_mark:
            self.click_mark[2] -= dt
            if self.click_mark[2] <= 0:
                self.click_mark = None


    def check_gk_handling(self, dt): # A keeper carrying the ball in his hands outside his own area: yellow card and free kick for the opponents.
        b = self.ball
        o = b.owner
        if self.mode != "play" or o is None or o.role != "GK" or getattr(o, "feet", False) or o.state in ("out", "leaving"):
            self._gk_out_t = 0.0
            return
        own_gx = 0.0 if self.att[o.team] > 0 else L
        if in_box_fn(b.wx, b.wv, own_gx) or in_box_fn(o.wx, o.wv, own_gx):
            self._gk_out_t = 0.0
            return
        self._gk_out_t += dt
        if self._gk_out_t < 0.12: # Tiny debounce so touching the line is not punished.
            return
        self._gk_out_t = 0.0
        victims = [q for q in self.team_p[1 - o.team] if q.state not in ("out", "leaving") and not q.red]
        if not victims:
            return
        v = min(victims, key=lambda q: math.hypot(q.wx - o.wx, q.wv - o.wv))
        spot = (clamp(o.wx, 3.0, L - 3.0), clamp(o.wv, V_TOP + 1.0, V_BOT - 1.0))
        self.call_foul(o, v, 1.0, 0.0, fall=False, spot=spot)

    def check_gk_box_time(self, dt): # Update the goalkeeper-area timing rule for possession.
        b = self.ball
        o = b.owner
        if self.mode != "play" or o is None or o.role != "GK" or getattr(o, "feet", False) or o.state in ("out", "leaving"):
            self.box_t.clear()
            return
        own_gx = 0.0 if self.att[o.team] > 0 else L
        seen = set()
        for q in self.team_p[1 - o.team]:
            if q.role == "GK" or q.state in ("out", "leaving") or q.red:
                continue
            if q is getattr(self, "_gk_area_violator", None):
                if in_box_fn(q.wx, q.wv, own_gx):
                    self.box_t.pop(id(q), None)
                    continue
                self._gk_area_violator = None
            if in_box_fn(q.wx, q.wv, own_gx):
                k = id(q)
                seen.add(k)
                self.box_t[k] = self.box_t.get(k, 0.0) + dt
                if self.box_t[k] > 2.0:
                    self.box_t.clear()
                    self.call_foul(q, o, 0.15, 0.0, fall=False)
                    self.log_event(tr("ev.gk_danger"), secs=3, team=q.team)
                    return
        for k in list(self.box_t):
            if k not in seen:
                del self.box_t[k]

    def throw_pose(self): # Return the player pose used while preparing a throw or release.
        rs = self.restart if self.mode == "restart" else None
        if rs is None or rs.get("kind") != "throw":
            return
        tk = rs.get("taker")
        if tk is None or tk.state in ("out", "leaving"):
            return
        if tk.state == "free" and rs.get("ready"):
            tk.sid = team_sprite_offset(tk.team) + 27
        elif not (tk.state == "action" and tk.act is not None and tk.act["key"] == "throw" and not tk.act["fired"]):
            return
        b = self.ball
        b.wx, b.wv, b.z = tk.wx, tk.wv, THROW_HOLD_Z
        b.vx = b.vv = b.vz = 0.0

    def text(self, s, font, col, pos, center=False, shadow=True): # Draw text with alignment and optional shadow.
        img = font.render(s, True, col)
        r = img.get_rect()
        if center:
            r.center = pos
        else:
            r.topleft = pos
        if shadow:
            self.target.blit(font.render(s, True, (0, 0, 0)), r.move(2, 2))
        self.target.blit(img, r)

    def img_to_screen(self, ix, iy): # Convert an image coordinate into screen coordinates.
        cx, cy = self.cam_int()
        return (ix - cx) * self.zoom, (iy - cy) * self.zoom


    def draw(self): # Render the current frame and delegate graphics to the rendering subsystem.
        if self.mode == "intro":
            self.target = self.screen
            self.screen.fill((10, 12, 28))
            self.draw_intro()
            return
        for p in self.players:
            if p.sx == 0 and p.sy == 0:
                self.post_move(p)
        rp = self.replay
        ak = 0.0 if rp else self.update_arrow_state()
        split = ak > 0.0
        self.draw_field(rp["frames"][min(rp["i"], len(rp["frames"]) - 1)][1] if rp else None, split)
        cx, cy, ox, oy = self.cam_view()
        self.screen.fill((6, 6, 12))
        vs, z = self.vsurf, self.zoom
        # World layer: normally drawn straight into vs; with sub-pixel scrolling it is one native pixel larger and shifted on blit.
        world = self.world_surface((self.vw + (1 if ox else 0)) * z, (self.vh + (1 if oy else 0)) * z) if (ox or oy) else vs
        self.scale_world(self.field_surf, cx, cy, ox, oy, dest=world)
        self.target = world
        if split:
            self.draw_ground_arrow_fx(world, self._arrow, ak)
            world.blit(self.scale_world(self.sprite_surf, cx, cy, ox, oy), (0, 0))
        if not rp:
            self.draw_marker()
        if self.paused and not rp:
            self.draw_tactics()
        if self.drag and self.cp and not rp:
            x0, y0, x1, y1 = self.drag
            if self.paused and math.hypot(x1 - x0, y1 - y0) > 6:
                self.draw_shot_preview(x0, y0, x1, y1, self.drag_act)
        if self.paused and self.paused_traj_data is not None and not self.drag and not rp:
            self.draw_shot_preview_data(self.paused_traj_data)
        if world is not vs:
            vs.blit(world, (-ox, -oy)) # Apply the sub-pixel offset, then draw the screen-fixed UI on top.
        self.target = vs
        if self.debug and not rp:
            self.draw_debug_text()
        if self.big and not rp:
            self.text(self.big[0], self.font_l, (255, 255, 255), (self.view_w // 2, self.view_h // 3), True)
        if self.mode in ("half", "full") and not rp:
            self.draw_summary()
        if rp:
            self.draw_replay_badge()
        if not rp:
            self.draw_key_hints()
        if self.show_help:
            self.draw_help()
        self.target = self.screen
        self.screen.blit(vs, (0, self.field_y))
        pygame.draw.rect(self.screen, (214, 218, 238), (0, self.field_y, self.view_w, self.view_h), 2)
        self.board.draw(self.screen, self, self.W, self.bh)
        self.board.draw_bar(self.screen, self, self.bar_y, self.W, self.bar_h)
        self.draw_agonism(self.screen)
        self.draw_hud()
        if self.sub_menu:
            self.draw_sub_menu()
        if self.confirm_exit:
            self.draw_exit_dialog()

    def arrow_source(self): # Return the source point for the current movement or aim arrow.
        p = self.cp
        if p is None or p.state != "free" or self.replay or self.mode not in ("play", "restart"):
            return None
        if self.drag:
            x0, y0, x1, y1 = self.drag
            ln = math.hypot(x1 - x0, y1 - y0)
            if ln <= 6:
                return None
            (a, b), (c, d) = w2s_jac(p.wx, p.wv)
            det = a * d - b * c
            if abs(det) < 1e-9:
                return None
            sx, sy = (x1 - x0) / float(max(1, self.zoom)), (y1 - y0) / float(max(1, self.zoom))
            wdx, wdv = (d * sx - b * sy) / det, (-c * sx + a * sy) / det
            ux, uv = unit(wdx, wdv)
            return dict(dx=ux, dv=uv, length=clamp(math.hypot(wdx, wdv), 8.0, 110.0),
                        f=self.gesture_intensity(ln), pid=id(p))
        if self.paused:
            return None
        if self.charge is not None:
            dx, dv = self.aim_dir(p)
            f = self.charge_level()
            return dict(dx=dx, dv=dv, length=self.ARROW_MIN + f * (self.ARROW_MAX - self.ARROW_MIN), f=f, pid=id(p))
        a = self.joy.aim_vec()
        if a:
            dx, dv = screen_to_world_dir(p.wx, p.wv, a[0], a[1])
            f = clamp(self.joy.aim_mag(), 0.25, 1.0)
            return dict(dx=dx, dv=dv, length=self.ARROW_MIN + f * 0.6 * (self.ARROW_MAX - self.ARROW_MIN), f=f * 0.6,
                        pid=id(p))
        return None

    def update_arrow_state(self): # Update the arrow display state after player or camera movement.
        now = time.time()
        src = self.arrow_source()
        if src:
            src["t"] = now
            self._arrow = src
            return 1.0
        a = self._arrow
        if a is None:
            return 0.0
        if self.cp is None or id(self.cp) != a["pid"] or self.paused or self.mode not in ("play", "restart"):
            self._arrow = None
            return 0.0
        k = 1.0 - (now - a["t"]) / self.ARROW_FADE
        if k <= 0.0:
            self._arrow = None
            return 0.0
        return k


    def overlay(self, alpha=190): # Draw a translucent overlay over the game view.
        o = pygame.Surface((self.view_w, self.view_h), pygame.SRCALPHA)
        o.fill((0, 0, 0, alpha))
        self.target.blit(o, (0, 0))
        return self.view_w, self.view_h


    def set_language(self, code): # Change the interface language and refresh translated text.
        if T.set_language(code):
            self._help_cache = None
            pygame.display.set_caption(f"{tr('app.caption')} v{VERSION}")
            for detail in T.take_problems():
                self.notes.append(Note("note.lang_problem", True, detail=detail))

    def fit_text(self, text, px, maxw): # Fit text into a maximum width using the requested font size.
        return self.board.fit(text, self.board.font(px), maxw)


    HELP_LAYOUT = (
        (("mf", 7), ("mb", 3)),
        (("kg", 11), ("pt", 4)),
        (("view", 6), ("other", 8)),
    )

    @classmethod
    def help_columns(cls): # Calculate the column layout used by the help screen.
        return tuple(
            tuple(
                (tr("help.%s.title" % sec),
                 tuple((tr("help.%s.%d.k" % (sec, i)), tr("help.%s.%d.d" % (sec, i))) for i in range(1, n + 1)))
                for sec, n in col)
            for col in cls.HELP_LAYOUT)

    @staticmethod
    def _wrap(text, font, maxw): # Wrap a text line to fit within the requested width.
        lines, cur = [], ""
        for word in text.split(" "):
            trial = word if not cur else cur + " " + word
            if cur and font.size(trial)[0] > maxw:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines or [""]


    HELP_MIN_PX = 11

    @classmethod
    def help_sections(cls): # Build the structured sections displayed by the help screen.
        return [sec for col in cls.help_columns() for sec in col]

    def help_pages(self): # Build the pages used by the in-game help.
        return len(self.HELP_LAYOUT)

    def help_toggle(self): # Open or close the in-game help screen.
        if self.show_help and self.help_page < self.help_pages() - 1:
            self.help_page += 1
        else:
            self.show_help = not self.show_help
            self.help_page = 0


def selftest(game, seconds, shots_dir=None): # Run the automated match self-test for the requested duration and settings.
    game.mode = "restart"
    dt = 1.0 / 60.0
    t = 0.0
    last_shot = -99.0
    n = 0
    while t < seconds and game.mode != "full":
        game.update(dt)
        t += dt
        if shots_dir and t - last_shot > 12:
            last_shot = t
            game.draw()
            pygame.image.save(game.screen, os.path.join(shots_dir, "shot_%03d.png" % n))
            n += 1
    st = game.stats
    print("tempo sim %.0fs  modo=%s tempo=%dT %.0f'" % (t, game.mode, game.half, game.minute()))
    print("punteggio", game.score, "tiri", st["shots"], "falli", st["fouls"], "gialli", st["yellow"], "rossi", st["red"],
          "angoli", st["corners"])
    # Shot-quality counters used to calibrate goalkeeper and block constants (see tools/calibrate.py).
    print("in porta", st["on_target"], "parate", st["saves"], "respinti", st["blocks"])


def main(): # Parse launch options, load resources, initialize the game, and run the main loop.
    ap = argparse.ArgumentParser(description="IL MISTER (pygame)")
    ap.add_argument("--pic", help="cartella PIC con 27.VGA (sprite) e i loghi delle squadre")
    ap.add_argument("--data", help="cartella con tore_actions.json")
    ap.add_argument("--mana", help="percorso di MANA.DAT (default: cartella del programma)")
    ap.add_argument("--geometria-originale", "--original-geometry", action="store_true", dest="orig_geom",
                    help="tela 320x112 come nell'editor TORE (default: tela estesa con gli angoli vicini)")
    ap.add_argument("--no-replay", action="store_true", help="replay automatico disattivato di default")
    ap.add_argument("--replay-secs", type=int, default=None, help="durata del replay in secondi (default: opzioni salvate, altrimenti 5)")
    ap.add_argument("--tore-fps", type=int, default=TORE_FPS, help="frame al secondo dei file TORE (default %d: nel viewer imposta lo stesso fps)" % TORE_FPS)
    ap.add_argument("--tore-dir", help="cartella dove salvare i file TORE dei replay (default: TORE_OUT accanto al programma)")
    ap.add_argument("--half", type=float, default=None, help="durata (minuti REALI) di ogni tempo (default: opzioni salvate, altrimenti 3)")
    ap.add_argument("--zoom", type=int, help="ingrandimento (default 5 con scroll, 3 a campo intero)")
    ap.add_argument("--noscroll", action="store_true", help="vedi sempre tutto il campo (senza scroll)")
    ap.add_argument("--no-sound", action="store_true")
    ap.add_argument("--lang", default=None, help="lingua dell'interfaccia (codice di data/lang/mister_lang_<codice>.py; default: opzioni salvate, altrimenti it)")
    ap.add_argument("--no-dialog", action="store_true", help="non chiedere la cartella PIC")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--selftest", type=float, help=argparse.SUPPRESS)
    ap.add_argument("--shots", help=argparse.SUPPRESS)
    args = ap.parse_args()
    app_dir = os.path.dirname(os.path.abspath(__file__))
    exe_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, "frozen", False) else app_dir
    cwd = os.getcwd()
    # Saved options (data/options.json); an explicit command-line flag always wins over them.
    args.options_path = options_path([os.path.join(exe_dir, "data"), os.path.join(app_dir, "data"), os.path.join(cwd, "data")])
    saved = load_options(args.options_path)
    init_language(args.lang or saved.get("lang") or "en")
    if args.half is None:
        args.half = saved.get("half_min", 3.0)
    if args.replay_secs is None:
        args.replay_secs = saved.get("replay_secs", 5)
    if saved.get("replay_auto") is False:
        args.no_replay = True
    if saved.get("slowmo") is False and not getattr(args, "no_slowmo", False):
        args.no_slowmo = True
    if args.seed is not None:
        random.seed(args.seed)
    dirs = ([args.data] if args.data else []) + [os.path.join(exe_dir, "data"), exe_dir, os.path.join(app_dir, "data"), app_dir, os.path.join(cwd, "data"), cwd]
    notes = load_data(dirs)
    teams, team_note = load_teams([exe_dir, app_dir, cwd], args.mana)
    pic = locate_pic(exe_dir, args.pic) or (locate_pic(app_dir, args.pic) if app_dir != exe_dir else None)
    if pic is None and not (args.selftest or args.no_dialog):
        pic = ask_pic_dir(exe_dir)
    asset_dirs = [exe_dir, os.path.join(exe_dir, "data"), app_dir, os.path.join(app_dir, "data"), cwd, os.path.join(cwd, "data")] + ([pic] if pic else [])
    field_path = find_asset("campo.png", asset_dirs)
    board_path = find_asset("tabellone.png", asset_dirs)
    sheet_path = find_file(pic, "27") if pic else None
    missing = [n for n, p in (("campo.png", field_path), ("tabellone.png", board_path), ("27.vga", sheet_path)) if p is None]
    if missing:
        fatal(missing, [d for d in asset_dirs if d])
    pygame.display.init()
    pygame.font.init()
    FONTS.load([exe_dir, os.path.join(exe_dir, "data"), app_dir, os.path.join(app_dir, "data"), cwd, os.path.join(cwd, "data")])
    if "font_modern" in saved:
        FONTS.modern = saved["font_modern"]
    miss_fon = [n for n, f in (("MICRO4.FON", FONTS.micro), ("FLOW.FON", FONTS.flow)) if f is None]
    if miss_fon:
        fatal(miss_fon, [d for d in asset_dirs if d])
    pygame.display.set_caption(f"{tr('app.caption')} v{VERSION}")
    args.zoom = args.zoom or (3 if args.noscroll else 5)
    d = compute_layout(args.zoom, not args.noscroll)
    try:
        screen = pygame.display.set_mode((int(d["W"]), int(d["H"])), pygame.RESIZABLE)
    except pygame.error:
        screen = pygame.display.set_mode((d["W"], d["H"]))
    set_match_log_dir(os.path.join(exe_dir, "log"))
    args.tore_dir = args.tore_dir or os.path.join(exe_dir, "TORE_OUT")
    try:
        gfx = Graphics(pic, field_path, board_path, sheet_path, (FW, FH), FIELD_X0, Y_OFFSET, tr)
    except OSError as ex:
        fatal([str(ex)], [])
    notes = [team_note] + notes
    print(team_note.text())
    voc_path = find_original_sound("digi.voc", asset_dirs) # .\SOUND\DIGI.VOC: crowd chorus loop.
    cmf_path = find_original_sound("bm2title.cmf", asset_dirs) # .\SOUNDS\BM2TITLE.CMF: intro music.
    audio = Audio(not args.no_sound and not args.selftest, os.path.join(app_dir, ".tore_audio"), voc_path, cmf_path)
    if saved.get("orig_audio") is False:
        audio.set_original(False)
    args.joy_dirs = [os.path.join(exe_dir, "data"), os.path.join(app_dir, "data"), os.path.join(cwd, "data"), exe_dir, app_dir, cwd]
    args.joy_write_dir = os.path.join(exe_dir, "data")
    args.joy_img = find_asset(JOY_IMG, asset_dirs)
    game = Game(args, gfx, audio, screen, notes, teams)
    if "user_team" in saved:
        game.user_team = saved["user_team"]
    if "hints" in saved:
        game.show_hints = saved["hints"]
    game.notes.extend(Note("note.lang_problem", True, detail=d) for d in T.take_problems())
    game.apply_view()
    if args.selftest:
        selftest(game, args.selftest, args.shots)
        return
    clock = pygame.time.Clock()
    DT = 1.0 / 60.0
    acc = 0.0
    running = True
    
    while running:
        acc = min(acc + clock.tick(60) / 1000.0 * game.speed, max(0.5, game.speed / 30.0))
    
        for ev in pygame.event.get():
            if game.handle_event(ev) == "quit":
                running = False
        now = pygame.time.get_ticks()
        if (
            game.cam_manual
            and not game.paused
            and game.pan_return_at
            and now >= game.pan_return_at
        ):
            game.cam_manual = False
            game.cam_glide = CAM_GLIDE_SECS
            game.pan_return_at = 0
            game.say(tr("msg.camera_ball"), (200, 220, 255), 1.5)
        while acc >= DT:
            if game.confirm_exit:
                pass
            elif game.replay:
                game.replay_step()
            elif not game.paused and not game.confirm_exit:
                game.update(DT)
            acc -= DT
        game.draw()
        pygame.display.flip()
    game.save_log("interrotta")
    pygame.quit()


if __name__ == "__main__":
    main()
