import math
import os
import time

import pygame

from fonts import FONTS, ScaledFont
from formation_system import formation_slots, FORMATIONS, ROLE_POOLS
from game_utils import clamp, unit, wline
from geometry import (
    BAR_HI, BOX_D, BOX_V0, BOX_V1, FIELD_ROW0, GA_D, GA_V0, GA_V1, GOAL_D, GOAL_H, GOAL_NET_H, ground_to_img,
    HALF_MOUTH, L, PITCH_W, POST_T, V_BOT, V_GC, V_TOP, Y_OFFSET,
)
from graphics_system import CELL_H, GOAL_Y1
from joystick import JOY_ACTIONS, JOY_HOTSPOTS, JOY_IMG
from lang import ROLE_LETTER, ROLE_TAG, T, tr
from layout import HUD_H, SU_H, SU_W
from match_config import FLAG_R, TEAM_COL, TEAM_NAMES
from physics_system import KEEPER_CATCH_HEIGHT, KEEPER_CATCH_RADIUS, PLAYER_CATCH_RADIUS, REACH_FIRST
from sprite_data import BALL_ROT


class RenderingMixin: # Rendering of the pitch, HUD, menus, debug overlays, and help screens.
    def draw_shot_preview_data(self, data): # Draw a precomputed shot or pass trajectory preview.
        if not data or not data.get("points"):
            return
        cx, cy = self.cam_int()
        z = self.zoom
        ov = pygame.Surface((self.view_w, self.view_h), pygame.SRCALPHA)
        scr = []
        for wx, wv, wz, _speed in data["points"]:
            ix, iy = ground_to_img(wx, wv)
            scr.append(((ix - cx) * z, (iy - cy) * z, (iy - wz - cy) * z))
        for i in range(1, len(scr)):
            pygame.draw.line(ov, (255, 255, 255, 60), scr[i - 1][:2], scr[i][:2], 1)
        n = len(scr)
        balls = {}
        for i, (sx, sy, sy2) in enumerate(scr):
            a = int(235 - 150 * i / max(1, n))
            if abs(sy2 - sy) > 2:
                pygame.draw.line(ov, (255, 255, 255, 45), (sx, sy), (sx, sy2), 1)
            frame = BALL_ROT[i % len(BALL_ROT)]
            spr = balls.get((frame, a))
            if spr is None:
                spr = pygame.transform.scale(self.gfx.sprite(frame), (4 * z, CELL_H * z))
                spr.set_alpha(a)
                balls[(frame, a)] = spr
            ov.blit(spr, (int(sx) - 2 * z, int(sy2) - 7 * z))
        ex, ey, _e2 = scr[-1]
        pygame.draw.circle(ov, (255, 200, 40, 220), (int(ex), int(ey)), max(3, int(z * 1.6)), 2)
        if data.get("target") is not None:
            tx, ty = ground_to_img(*data["target"])
            pygame.draw.circle(ov, (90, 255, 130, 230),
                               (int((tx - cx) * z), int((ty - cy) * z)), max(6, int(z * 3.2)), 3)
        self.target.blit(ov, (0, 0))

    def draw_shot_preview(self, x0, y0, x1, y1, act=None): # Build and draw a trajectory preview for the current user gesture.
        data = self.build_shot_preview(x0, y0, x1, y1, act)
        if data is not None:
            self.draw_shot_preview_data(data)
        return data

    def draw_sub_menu(self): # Draw the active substitution menu and its selectable entries.
        m = self.sub_menu
        panel, items = self.sub_menu_layout()
        pygame.draw.rect(self.screen, (10, 12, 26), panel)
        pygame.draw.rect(self.screen, (255, 215, 0), panel, 2)
        t = m["p"].team
        used = self.subs_used[t] + len(self.sub_q[t])
        self.text(tr("hud.sub_title", name=m["p"].name, used=used), self.font_s, (255, 215, 0), (panel.x + 8, panel.y + 6), shadow=False)
        pl = self.team_data[t]["players"]
        mp = pygame.mouse.get_pos()
        for r, idx in items:
            if r.collidepoint(mp):
                pygame.draw.rect(self.screen, (60, 70, 130), r)
            self.text("%2d  %s  [%s]" % (idx + 1, pl[idx], ROLE_TAG[self.natural_role(idx)]), self.font_s, (235, 235, 245), (r.x + 4, r.y + 3), shadow=False)

    def draw_exit_dialog(self): # Draw the confirmation dialog used when exiting the match.
        s = self.screen
        dim = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        s.blit(dim, (0, 0))
        w, h = min(self.W - 40, 560), 190
        box = pygame.Rect(0, 0, w, h)
        box.center = (self.W // 2, self.H // 2)
        pygame.draw.rect(s, (22, 26, 52), box, border_radius=10)
        pygame.draw.rect(s, (214, 218, 238), box, 2, border_radius=10)
        bd = self.board
        bd.put(s, bd.font(40).render(tr("dlg.exit_title"), True, (255, 255, 255)), cx=box.centerx, cy=box.top + 66)
        yes = pygame.Rect(0, 0, 140, 40)
        no = pygame.Rect(0, 0, 140, 40)
        yes.center = (box.centerx - 110, box.bottom - 42)
        no.center = (box.centerx + 110, box.bottom - 42)
        mp = pygame.mouse.get_pos()
        for r, label, col in ((yes, tr("dlg.exit_yes"), (200, 90, 90)), (no, tr("dlg.exit_no"), (90, 170, 110))):
            pygame.draw.rect(s, col if r.collidepoint(mp) else tuple(int(c * 0.6) for c in col), r, border_radius=8)
            pygame.draw.rect(s, (240, 240, 250), r, 2, border_radius=8)
            bd.put(s, bd.font(20).render(label, True, (255, 255, 255)), cx=r.centerx, cy=r.centery)
        self.exit_btns = ((yes, True), (no, False))

    def draw_replay_badge(self): # Draw the indicator showing that replay recording or playback is active.
        r = self.replay
        s = self.target
        size = max(70, int(self.view_h * 0.30))
        f = self._fr.get(size)
        if f is None:
            f = self._fr[size] = FONTS.get(size)
        if int(pygame.time.get_ticks() / 400) % 2 == 0:
            img = f.render("R", True, (236, 30, 30))
            edge = f.render("R", True, (0, 0, 0))
            for dx, dy in ((-3, 0), (3, 0), (0, -3), (0, 3), (-2, -2), (2, 2), (-2, 2), (2, -2)):
                s.blit(edge, (16 + dx, 8 + dy))
            s.blit(img, (16, 8))
        self.text(tr("hud.replay"), self.font_m, (255, 255, 255), (16 + int(size * 0.55), 14))
        prog = (r["i"] + 1) / float(len(r["frames"]))
        pygame.draw.rect(s, (0, 0, 0), (0, self.view_h - 7, self.view_w, 7))
        pygame.draw.rect(s, (236, 30, 30), (0, self.view_h - 6, int(self.view_w * prog), 5))

    def draw_field(self, snap=None, split=False): # Render the pitch and all visible field entities.
        s = self.field_surf
        fg = self.sprite_surf if split else s
        s.blit(self.gfx.field, (0, 0))
        s.blit(self.gfx.crowd_frame(), (0, 0))
        if split:
            fg.fill((0, 0, 0, 0))
        snap = snap or self.snapshot()
        pl, rf, bl = snap[:3]
        flags = snap[3] if len(snap) > 3 else ()
        bpx, bgy, bz, bsid = bl
        items = [(sy, 2, "p", (sx, sy, sid)) for sx, sy, sid, vis in pl if vis]
        items += [(bgy, 0, "s", None), (bgy, 1, "b", None), (rf[1], 2, "r", rf)]
        for goal_img in self.gfx.goals:
            items.append((GOAL_Y1, 3, "g", goal_img))
        items += [(fl[1] - FIELD_ROW0, 2, "f", fl) for fl in flags]
        items.sort(key=lambda t: (t[0], t[1]))
        for _k, _r, kind, p in items:
            if kind == "f":
                self.draw_flag(fg, p)
            elif kind == "p":
                fg.blit(self.gfx.sprite(p[2]), (int(round(p[0])) - 6, int(round(p[1])) + Y_OFFSET))
            elif kind == "r":
                fg.blit(self.gfx.sprite(rf[2]), (int(round(rf[0])) - 6, int(round(rf[1])) + Y_OFFSET))
            elif kind == "s":
                sy_ = max(int(round(bgy)) + 3 + Y_OFFSET, FIELD_ROW0 - 2 - self.gfx.shadow_top)
                fg.blit(self.gfx.sprite(145), (int(round(bpx)) - 2, sy_))
            elif kind == "b":
                fg.blit(self.gfx.sprite(bsid), (int(round(bpx)) - 2, int(round(bgy + 3 - bz)) + Y_OFFSET))
            else:
                fg.blit(p[0], p[1])
        if rf[3]:
            cx, cy = int(round(rf[0])) + 4, int(round(rf[1])) + Y_OFFSET - 8
            pygame.draw.rect(fg, (0, 0, 0), (cx - 1, cy - 1, 6, 8))
            pygame.draw.rect(fg, (255, 220, 0) if rf[3] == "Y" else (230, 30, 30), (cx, cy, 4, 6))
        if snap is None and self.click_mark:
            x, y = int(self.click_mark[0]), int(self.click_mark[1])
            pygame.draw.line(fg, (255, 255, 255), (x - 2, y), (x + 2, y))
            pygame.draw.line(fg, (255, 255, 255), (x, y - 2), (x, y + 2))
        if self.debug:
            self.draw_debug(fg)

    def draw_flag(self, s, fl): # Draw the referee flag using its current animation frame.
        bx, by, tx, ty, sg = fl
        pygame.draw.line(s, (240, 240, 240), (int(round(bx)), int(round(by))), (int(round(tx)), int(round(ty))))
        ux, uy = unit(tx - bx, ty - by, (0.0, -1.0))
        nx, ny = -uy * sg, ux * sg
        pts = [(tx, ty), (tx - ux * 3.2, ty - uy * 3.2), (tx - ux * 1.6 + nx * 4.2, ty - uy * 1.6 + ny * 4.2)]
        pygame.draw.polygon(s, (230, 40, 40), [(int(round(x)), int(round(y))) for x, y in pts])

    def draw_debug(self, s): # Draw debug geometry and collision or movement overlays.
        def gp(x, v, z=0.0): # Project a world field point onto screen coordinates.
            ix, iy = ground_to_img(x, v)
            return (ix, iy - z)

        def pl(pts, col, closed=False): # Draw a polyline or closed polygon on the supplied surface.
            pygame.draw.lines(s, col, closed, [gp(*p) for p in pts], 1)

        def ring(x, v, r, col, n=20): # Draw a ring around a world-space field point.
            pl([(x + r * math.cos(2 * math.pi * i / n), v + r * math.sin(2 * math.pi * i / n)) for i in range(n)], col, True)

        def reach_oval(x, v, r, col): # Draw the projected player reach zone as an oval.
            cx, cy = gp(x, v)
            left = gp(x - r, v)[0]
            right = gp(x + r, v)[0]
            rx = max(1.0, abs(right - left) * 0.5)
            ry = max(1.0, rx * 0.62)
            rect = pygame.Rect(round(cx - rx), round(cy - ry), round(rx * 2), round(ry * 2))
            pygame.draw.ellipse(s, col, rect, 1)
        pl(wline((0, V_TOP), (L, V_TOP)) + wline((L, V_TOP), (L, V_BOT)) + wline((L, V_BOT), (0, V_BOT)) + wline((0, V_BOT), (0, V_TOP)), (255, 255, 0))
        pl(wline((L / 2, V_TOP), (L / 2, V_BOT)), (255, 255, 0))
        v0, v1 = V_GC - HALF_MOUTH, V_GC + HALF_MOUTH
        for x0, sg in ((0, 1), (L, -1)):
            pl([(x0, v0), (x0, v1)], (0, 255, 255))
            pl([(x0, BOX_V0), (x0 + sg * BOX_D, BOX_V0), (x0 + sg * BOX_D, BOX_V1), (x0, BOX_V1)], (255, 120, 0))
            pl([(x0, GA_V0), (x0 + sg * GA_D, GA_V0), (x0 + sg * GA_D, GA_V1), (x0, GA_V1)], (255, 60, 200))
            xd = x0 - sg * GOAL_D
            pl([(x0, v0, 0), (x0, v0, GOAL_H), (x0, v1, GOAL_H), (x0, v1, 0)], (0, 255, 255))
            pl([(x0, v0, GOAL_H + BAR_HI), (x0, v1, GOAL_H + BAR_HI)], (255, 0, 0))
            pl([(x0, v0 - POST_T, 0), (x0, v0 - POST_T, GOAL_H + BAR_HI), (x0, v1 + POST_T, GOAL_H + BAR_HI), (x0, v1 + POST_T, 0)], (255, 255, 255))
            pl([(x0, v0, 0), (xd, v0, 0), (xd, v1, 0), (x0, v1, 0)], (0, 150, 255))
            pl([(x0, v0, GOAL_NET_H), (xd, v0, GOAL_NET_H), (xd, v1, GOAL_NET_H), (x0, v1, GOAL_NET_H)], (0, 150, 255), True)
        b = self.ball
        pl([(b.wx - 2, b.wv), (b.wx + 2, b.wv)], (255, 255, 255))
        pl([(b.wx, b.wv, 0), (b.wx, b.wv, b.z)], (255, 255, 255))
        pl([(b.wx, b.wv, b.z), (b.wx + b.vx * 0.15, b.wv + b.vv * 0.15, b.z)], (255, 0, 255))
        for f in self.flags:
            ring(f.x, f.v, FLAG_R, (255, 160, 0), 12)
        rs = self.restart if self.mode == "restart" else None
        if rs and rs.get("taker") is not None:
            # Alignment aid: white cross = ball ground point, green cross = taker anchor (feet should sit on the white one).
            tk = rs["taker"]
            for (cx, cv), col in (((b.wx, b.wv), (255, 255, 255)), ((tk.wx, tk.wv), (0, 255, 0))):
                pl([(cx - 3, cv), (cx + 3, cv)], col)
                pl([(cx, cv - 3), (cx, cv + 3)], col)
        cp = self.cp
        if cp and cp.state != "out":
            d = self.att[cp.team]
            xa, xb = [(u * L if d > 0 else (1 - u) * L) for u in cp.zu]
            va, vb = V_TOP + cp.zw[0] * PITCH_W, V_TOP + cp.zw[1] * PITCH_W
            pl(wline((xa, va), (xb, va), 12) + wline((xb, va), (xb, vb), 12) + wline((xb, vb), (xa, vb), 12) + wline((xa, vb), (xa, va), 12),
               (120, 255, 120))
            reach_oval(cp.wx, cp.wv, REACH_FIRST, (120, 255, 120))
            reach_oval(cp.wx, cp.wv, PLAYER_CATCH_RADIUS, (255, 255, 255))
            reach_oval(cp.wx, cp.wv, self.AIR_REACH, (0, 200, 255))
        for p in self.players:
            if p.state != "out" and p.tx is not None:
                pygame.draw.line(s, TEAM_COL[p.team], gp(p.wx, p.wv), gp(p.tx, p.tv), 1)
            if p.role == "GK" and p.state != "out":
                ring(p.wx, p.wv, KEEPER_CATCH_RADIUS, (255, 140, 0))
                pl([(p.wx, p.wv, 0), (p.wx, p.wv, KEEPER_CATCH_HEIGHT)], (255, 140, 0))
                own_x = 0.0 if self.att[p.team] > 0 else L
                if b.owner is None and (b.wx - own_x) * self.att[p.team] > 0:
                    fc = self.ball_forecast(own_x)
                    if fc is not None:
                        pl([(own_x, fc["v"] - 2, fc["z"]), (own_x, fc["v"] + 2, fc["z"])], (255, 0, 255))
                        pl([(own_x, fc["v"], fc["z"] - 2), (own_x, fc["v"], fc["z"] + 2)], (255, 0, 255))

    def draw_debug_text(self): # Draw textual debug values for the current game state.
        b = self.ball
        own = b.owner.label() if b.owner is not None else "-"
        lines = [tr("dbg.title", mode=self.mode, speed=self.speed),
                 tr("dbg.ball", x=b.wx, v=b.wv, z=b.z, vx=b.vx, vv=b.vv, vz=b.vz, ds=b.ds),
                 tr("dbg.owner", owner=own, lt=b.last_team, st=b.shot_team, age=b.age),
                 tr("dbg.goal", vgc=V_GC, hm=HALF_MOUTH, v0=V_GC - HALF_MOUTH, v1=V_GC + HALF_MOUTH, gh=GOAL_H,
                    bh=BAR_HI, pt=POST_T, gd=GOAL_D, gn=GOAL_NET_H),
                 tr("dbg.legend1"),
                 tr("dbg.legend2", air=self.AIR_REACH, fr=FLAG_R),
                 "Raggi: primo contatto (verde), controllo palla (bianco), gioco aereo (azzurro)"]
        for p in self.players:
            if p.role == "GK" and p.state != "out":
                lines.append(tr("dbg.gk", team=p.team, name=p.label(), skill=p.skill,
                                alert=getattr(p, "alert", False), state=p.state, cd=p.act_cd))
        cp = self.cp
        if cp is not None:
            opts = self.air_options(cp, True)
            lines.append(tr("dbg.cp", name=cp.label(), state=cp.state, opts=",".join(opts) or "-"))
        y = 4
        for ln in lines:
            self.text(ln, self.font_t, (255, 255, 120), (6, y), shadow=True)
            y += self.font_t.get_height() + 1

    def draw_ground_arrow_fx(self, surface, a, k): # Draw the ground-projected arrow effect for the selected action.
        p = self.cp
        if p is None or a is None or k <= 0.0:
            return
        ux, uv = a["dx"], a["dv"]
        Ln = max(a["length"], 9.0)
        f = a["f"]
        hl = clamp(Ln * 0.34, 4.5, 10.0)
        sh = Ln - hl
        w0, w1, hw = 1.0, 1.9, 4.6
        nx, nv = -uv, ux
        camx, camy = self.cam_int()
        z = self.zoom

        def scr(s, off): # Project a screen coordinate with the supplied vertical offset.
            ix, iy = ground_to_img(p.wx + ux * s + nx * off, p.wv + uv * s + nv * off)
            return ((ix - camx) * z, (iy - camy) * z)
        slices = []
        n1, n2 = 10, 6
        for i in range(n1):
            sa, sb = sh * i / n1, sh * (i + 1) / n1
            slices.append((sa, w0 + (w1 - w0) * sa / sh, sb, w0 + (w1 - w0) * sb / sh))
        for i in range(n2):
            sa, sb = sh + hl * i / n2, sh + hl * (i + 1) / n2
            slices.append((sa, hw * (Ln - sa) / hl, sb, hw * (Ln - sb) / hl))
        polys = []
        xs, ys = [], []
        for sa, wa, sb, wb in slices:
            pts = [scr(sa, wa), scr(sb, wb), scr(sb, -wb), scr(sa, -wa)]
            polys.append(((sa + sb) * 0.5 / Ln, pts))
            for px, py in pts:
                xs.append(px)
                ys.append(py)
        vw, vh = surface.get_size()
        bx0, by0 = int(max(math.floor(min(xs)) - 3, -4)), int(max(math.floor(min(ys)) - 3, -4))
        bx1, by1 = int(min(math.ceil(max(xs)) + 3, vw + 4)), int(min(math.ceil(max(ys)) + 3, vh + 4))
        bw, bh = bx1 - bx0, by1 - by0
        if bw < 2 or bh < 2:
            return
        ss = 3 if bw * bh < 360000 else 2
        tmp = pygame.Surface((bw * ss, bh * ss), pygame.SRCALPHA)
        amax = 80.0 + 70.0 * f
        for t, pts in polys:
            alpha = int(clamp(k * amax * (0.30 + 0.70 * t), 0, 255))
            pygame.draw.polygon(tmp, (0, 0, 0, alpha), [((x - bx0) * ss, (y - by0) * ss) for x, y in pts])
        surface.blit(pygame.transform.smoothscale(tmp, (bw, bh)), (bx0, by0))

    def draw_key_hints(self): # Draw the current keyboard and controller hints.
        p = self.cp
        if not self.show_hints or p is None or self.user_team is None or self.mode not in ("play", "restart") \
                or self.show_help or self.drag:
            return
        rs = self.restart if self.mode == "restart" else None
        have = self.can_kick_now() or (rs is not None and rs.get("taker") is p)
        pad = self.joy.recent(time.time())

        def key(act, kb): # Resolve a readable label for the supplied action binding.
            if not pad:
                return kb
            t = self.joy.cfg["buttons"].get(act)
            return self.joy.token_label(t[0]) if t else None
        if self.paused:
            items = [(tr("hint.pause_path_k"), tr("hint.pause_path")),
                     (tr("hint.pause_kick_k"), tr("hint.pause_kick")),
                     (key("pause", "Spazio"), tr("hint.pause_resume")),
                     ("F8", tr("hint.off"))]
            text = "   ".join("[%s] %s" % (k, d) for k, d in items if k)
            img = self.font_t.render(text, True, (255, 255, 255))
            bar = pygame.Surface((min(self.view_w, img.get_width() + 16), img.get_height() + 6), pygame.SRCALPHA)
            bar.fill((0, 0, 0, 120))
            by = self.view_h - bar.get_height() - 4
            self.target.blit(bar, (4, by))
            self.target.blit(img, (12, by + 3))
            return
        if have:
            items = [(key("pass", "Z"), tr("hint.pass2")),
                     (key("shot", "X"), tr("hint.shot2"))]
            if not pad:
                items.append((tr("hint.mouse_k"), tr("hint.mouse_d")))
        else:
            items = [(key("pass", "Z"), tr("hint.pass3")),
                     (key("shot", "X"), tr("hint.shot3"))]
        items.append((key("cele", "C"), tr("hint.cele")))
        items.append((key("switch_player", "Tab"), tr("hint.switch")))
        items.append(("F8", tr("hint.off")))
        text = "   ".join("[%s] %s" % (k, d) for k, d in items if k)
        img = self.font_t.render(text, True, (255, 255, 255))
        bar = pygame.Surface((min(self.view_w, img.get_width() + 16), img.get_height() + 6), pygame.SRCALPHA)
        bar.fill((0, 0, 0, 120))
        by = self.view_h - bar.get_height() - 4
        self.target.blit(bar, (4, by))
        self.target.blit(img, (12, by + 3))

    def draw_marker(self): # Draw the active player-selection marker.
        cp = self.cp
        if not cp or cp.state == "out":
            return
        z = self.zoom
        sx, sy = self.img_to_screen(cp.sx, cp.sy + Y_OFFSET)
        bob = math.sin(self.t_all * 7.0) * 0.5 * z
        tip = (sx, sy - 0.6 * z + bob)
        pts = [(tip[0] - 1.9 * z, tip[1] - 3.6 * z), (tip[0] + 1.9 * z, tip[1] - 3.6 * z), tip]
        pygame.draw.polygon(self.target, (255, 215, 0), pts)
        pygame.draw.polygon(self.target, (0, 0, 0), pts, max(2, z // 2))

    def draw_tactics(self): # Draw tactical zones and formation-position overlays.
        z = self.zoom
        size = (self.view_w, self.view_h)
        ov = getattr(self, "_tactics_overlay", None)
        if ov is None or ov.get_size() != size:
            ov = pygame.Surface(size, pygame.SRCALPHA)
            self._tactics_overlay = ov
        else:
            ov.fill((0, 0, 0, 0))

        camx, camy = self.cam_int()
        def P(wx, wv): # Project world field coordinates into the current screen view.
            ix, iy = ground_to_img(wx, wv)
            return (ix - camx) * z, (iy - camy) * z

        def arrow(a, b, col, w=3): # Draw an arrow between two points with the requested width and colour.
            pygame.draw.line(ov, col, a, b, w)
            ang = math.atan2(b[1] - a[1], b[0] - a[0])
            h = 4 * z / 2.0 + 5
            pygame.draw.polygon(ov, col, [b,
                (b[0] - h * math.cos(ang - 0.45), b[1] - h * math.sin(ang - 0.45)),
                (b[0] - h * math.cos(ang + 0.45), b[1] - h * math.sin(ang + 0.45))])

        for p in self.players:
            if p.state == "out":
                continue
            col = TEAM_COL[p.team]
            radius = p.speed * 0.6
            pts = [P(p.wx + radius * math.cos(a * math.pi / 12),
                     p.wv + radius * math.sin(a * math.pi / 12)) for a in range(24)]
            pygame.draw.polygon(ov, col + (16,), pts)
            pygame.draw.polygon(ov, col + (120,), pts, 1)
            speed = math.hypot(p.vx, p.vv)
            length = 12 + speed * 0.45
            arrow(P(p.wx, p.wv), P(p.wx + p.dx * length, p.wv + p.dv * length), col + (255,))
            if p.tx is not None and p.tv is not None:
                a, dest = P(p.wx, p.wv), P(p.tx, p.tv)
                pygame.draw.line(ov, col + (120,), a, dest, 1)
                pygame.draw.circle(ov, col + (230,), (int(dest[0]), int(dest[1])), max(3, z), 2)

        paths = [(p, [(p.wx, p.wv)] + list(p.path))
                 for p in self.players if p.path and p.state != "out"]
        pd = self.pathdrag
        if pd and len(pd["pts"]) >= 2:
            paths.append((pd["p"], list(pd["pts"])))
        for player, pts in paths:
            col = TEAM_COL[player.team]
            screen_pts = [P(*pt) for pt in pts]
            if len(screen_pts) >= 2:
                pygame.draw.lines(ov, col + (230,), False, screen_pts, 3)
                for pt in screen_pts[1:]:
                    pygame.draw.circle(ov, col + (255,), (int(pt[0]), int(pt[1])), max(2, z // 2))
                arrow(screen_pts[-2], screen_pts[-1], col + (255,), 3)

        b = self.ball
        prev = P(b.wx, b.wv)
        for i in range(1, 7):
            nxt = P(*self.ball_pred(i * 0.25))
            pygame.draw.circle(ov, (255, 255, 255, 220), (int(nxt[0]), int(nxt[1])), max(2, z // 2))
            pygame.draw.line(ov, (255, 255, 255, 110), prev, nxt, 1)
            prev = nxt

        self.target.blit(ov, (0, 0))
        for p in self.players:
            if p.state == "out":
                continue
            fx, fy = P(p.wx, p.wv)
            self.text(str(p.num), self.font_t, TEAM_COL[p.team], (fx, fy - 11.5 * z), True)

    def draw_tactics_panel(self): # Draw the tactical panel and its current settings.
        surf = self.screen
        x, y = 8, self.hud_y + 2
        bw = min(540, max(180, self.W // 2 - 14))
        bh = HUD_H - 4
        pygame.draw.rect(surf, (30, 34, 52), (x, y, bw, bh))
        pygame.draw.rect(surf, (112, 122, 172), (x, y, bw, bh), 1)
        title_font = ScaledFont(FONTS.flow, 2) if FONTS.flow is not None else self.font_s
        self.text(tr("hud.tactical"), title_font, (255, 215, 0), (x + 8, y + 3), False, False)
        rows = (tr("hud.tactical_1"), tr("hud.tactical_2"), tr("hud.tactical_3"))
        for i, line in enumerate(rows):
            self.text(line, self.font_t, (220, 220, 230), (x + 8, y + 21 + i * 13), False, False)

    def draw_action_log(self): # Draw recent match actions in the on-screen log.
        if not self.mlog or (FONTS.flow is None and not FONTS.modern):
            return
        font = self.font_s if FONTS.modern else ScaledFont(FONTS.flow, 2)
        maxw = max(100, self.W - 100)
        y0 = self.hud_y + 8
        for i, (entry, col) in enumerate(self.mlog[-3:]):
            line = entry.split("] ", 1)[-1]
            original = line
            while line and font.size(line)[0] > maxw:
                line = line[:-1]
            if line != original and len(line) > 3:
                line = line[:-3] + "..."
            self.text(line, font, col, (10, y0 + i * 20), False, False)

    def draw_hud(self): # Draw the match HUD, timer, score, and status indicators.
        y = self.hud_y
        pygame.draw.rect(self.screen, (22, 24, 34), (0, y, self.W, HUD_H))
        if not self.replay:
            if self.paused:
                self.draw_tactics_panel()
            else:
                self.draw_action_log()
        margin = 8
        available = self.W - margin * 2
        yy = y + 3
        for t, col, _s in self.msgs[-3:]:
            line = t
            while line and self.font_s.size(line)[0] > available:
                line = line[:-1]
            if line != t and len(line) > 3:
                line = line[:-3] + "..."
            text_w = self.font_s.size(line)[0]
            self.text(line, self.font_s, col, (self.W - margin - text_w, yy), shadow=False)
            yy += 18

    def su_chip(self, s, r, label, active, hover, col=(120, 130, 210), px=18): # Draw one selectable chip in the substitution interface.
        bd = self.board
        pygame.draw.rect(s,tuple(int(v * 0.5) for v in col) if active else (30, 34, 66),r,border_radius=6,)
        pygame.draw.rect(s,(255, 224, 90) if active else (col if hover else (70, 78, 130)),r,2,border_radius=6,)
        t = bd.font(px).render(label, True, (255, 255, 255) if active else (190, 196, 230))
        bd.put(s, t, cx=r.centerx, cy=r.centery)

    def draw_intro(self): # Draw the match intro and team-selection screen.
        if self.joymap_open:
            return self.draw_joymap()
        s = self.su_surf
        s.fill((10, 12, 28))
        bd = self.board
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        W = SU_W
        bd.put(s, bd.font(58).render(tr("intro.title"), True, (232, 236, 255)), cx=W // 2, cy=32)
        bd.put(s, bd.font(24).render(tr("intro.subtitle"), True, bd.LIT), cx=W // 2, cy=68)
        note = " | ".join(n.text() for n in self.notes[:2]) if self.notes else ""
        warn = any(n.warn for n in self.notes)
        bd.put(s, bd.font(14).render(self.fit_text(note, 16, W - 40), True, (255, 170, 110) if warn else (130, 140, 190)), cx=W // 2, cy=92)
        names_ctl = (tr("intro.team_home"), tr("intro.team_away"))
        for c in (0, 1):
            self._draw_intro_team(s, bd, hits, vx, vy, c, names_ctl)

        bd.put(s, bd.font(20).render(tr("intro.half_len"), True, bd.LIT), left=30, cy=526)
        for i, m in enumerate((1, 2, 3, 5)):
            r = pygame.Rect(330 + i * 54, 512, 46, 28)
            self.su_chip(s, r, str(m), abs(self.half_secs - m * 60.0) < 1, r.collidepoint(vx, vy))
            hits.append((r, ("half", m * 60.0)))
        bd.put(s, bd.font(20).render(tr("intro.slowmo"), True, bd.LIT), left=650, cy=526)
        r = pygame.Rect(790, 512, 70, 28)
        self.su_chip(s, r, tr("intro.on") if self.slowmo_on else tr("intro.off"), self.slowmo_on, r.collidepoint(vx, vy), (90, 200, 120))
        hits.append((r, ("slowmo",)))
        bd.put(s, bd.font(20).render(tr("intro.controls"), True, bd.LIT), left=30, cy=564)
        for i, (lab, val) in enumerate(((tr("intro.ctrl_home"), 0), (tr("intro.ctrl_away"), 1), (tr("intro.ctrl_spec"), None))):
            r = pygame.Rect(330 + i * 150, 550, 142, 28)
            self.su_chip(s, r, lab, self.user_team == val, r.collidepoint(vx, vy))
            hits.append((r, ("ctrl", val)))
        bd.put(s, bd.font(20).render(tr("intro.replay_auto"), True, bd.LIT), left=30, cy=602)
        r = pygame.Rect(400, 588, 70, 28)
        self.su_chip(s, r, tr("intro.on") if self.replay_auto else tr("intro.off"), self.replay_auto, r.collidepoint(vx, vy), (90, 200, 120))
        hits.append((r, ("replay_auto",)))
        bd.put(s, bd.font(20).render(tr("intro.replay_secs"), True, bd.LIT), left=530, cy=602)
        for i, m in enumerate((3, 5, 8, 10, 15)):
            r = pygame.Rect(690 + i * 54, 588, 46, 28)
            self.su_chip(s, r, str(m), self.replay_secs == m, r.collidepoint(vx, vy))
            hits.append((r, ("replay_secs", m)))
        bd.put(s, bd.font(20).render(tr("intro.font"), True, bd.LIT), left=30, cy=660)
        for i, (lab, val) in enumerate(((tr("intro.font_modern"), True), (tr("intro.font_old"), False))):
            r = pygame.Rect(110 + i * 112, 646, 104, 28)
            self.su_chip(s, r, lab, FONTS.modern == val, r.collidepoint(vx, vy))
            hits.append((r, ("font", val)))
        sb = pygame.Rect(W // 2 - 140, 636, 280, 46)
        hov = sb.collidepoint(vx, vy)
        pygame.draw.rect(s, (60, 150, 90) if hov else (44, 112, 70), sb, border_radius=8)
        pygame.draw.rect(s, (200, 255, 210), sb, 2, border_radius=8)
        bd.put(s, bd.font(28).render(tr("intro.start"), True, (255, 255, 255)), cx=sb.centerx, cy=sb.centery)
        hits.append((sb, ("start",)))
        jb = pygame.Rect(W // 2 + 200, 641, 220, 36)
        self.su_chip(s, jb, tr("intro.joymap"), False, jb.collidepoint(vx, vy), (120, 170, 230), 20)
        hits.append((jb, ("joymap",)))
        bd.put(s, bd.font(20).render(tr("intro.footer"), True, (110, 118, 160)), cx=W // 2, cy=708)
        self.draw_lang_dropdown(s, bd, hits, vx, vy)
        sc, ox, oy = self.su_scale()
        out = pygame.transform.smoothscale(s, (int(SU_W * sc), int(SU_H * sc)))
        self.screen.blit(out, (int(ox), int(oy)))

    def _draw_intro_team(self, s, bd, hits, vx, vy, c, names_ctl): # Draw one team card in the intro screen.
        x0 = 30 + c * 495
        col = TEAM_COL[c]
        hb = pygame.Rect(x0, 108, 465, 28)
        pygame.draw.rect(s, tuple(int(v * 0.55) for v in col), hb, border_radius=5)
        if self.su_active == c:
            pygame.draw.rect(s, (255, 224, 90), hb, 2, border_radius=5)
        bd.put(s, bd.font(21).render(names_ctl[c], True, (255, 255, 255)), cx=hb.centerx, cy=hb.centery)

        lr = pygame.Rect(x0, 142, 232, 360)
        pygame.draw.rect(s, bd.BG, lr)
        sc0 = int(clamp(self.su_scroll[c], 0, max(0, len(self.teams) - 15)))
        self.su_scroll[c] = sc0
        s.set_clip(lr)
        for i in range(15):
            idx = sc0 + i
            if idx >= len(self.teams):
                break
            rr = pygame.Rect(x0, 142 + i * 24, 226, 24)
            if idx == self.sel[c]:
                pygame.draw.rect(s, tuple(int(v * 0.6) for v in col), rr)
            elif rr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), rr)
            t = bd.font(20).render(self.fit_text(self.teams[idx]["name"], 20, 212), True, (255, 255, 255) if idx == self.sel[c] else bd.WHITE)
            bd.put(s, t, left=x0 + 8, cy=rr.centery)
            hits.append((rr, ("team", c, idx)))
        s.set_clip(None)
        if len(self.teams) > 15:
            th = max(18, int(360 * 15 / len(self.teams)))
            ty = 142 + int((360 - th) * sc0 / float(len(self.teams) - 15))
            pygame.draw.rect(s, (80, 90, 150), (x0 + 226, ty, 5, th), border_radius=2)
        pygame.draw.rect(s, bd.FRAME, lr, 2)

        td = self.teams[self.sel[c]]
        px0 = x0 + 248
        lg = pygame.Rect(px0, 142, 110, 110)
        pygame.draw.rect(s, (8, 10, 24), lg)
        img = self.gfx.logo(td["logo"])
        if img is not None:
            k = min(98.0 / img.get_width(), 98.0 / img.get_height())
            im = pygame.transform.smoothscale(img, (max(1, int(img.get_width() * k)), max(1, int(img.get_height() * k))))
            s.blit(im, im.get_rect(center=lg.center))
        pygame.draw.rect(s, bd.FRAME, lg, 3)

        mp = pygame.Rect(px0 + 118, 142, 98, 110)
        pygame.draw.rect(s, (40, 104, 48), mp)
        pygame.draw.rect(s, (220, 226, 220), mp, 1)
        pygame.draw.line(s, (220, 226, 220), (mp.left, mp.top + 2), (mp.right, mp.top + 2), 1)
        pygame.draw.arc(s, (220, 226, 220), (mp.left + 28, mp.top - 20, 42, 40), math.pi, 2 * math.pi, 1)
        for sl in formation_slots(self.form_names[c]):
            pygame.draw.circle(s, col, (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16))), 5)
            pygame.draw.circle(s, (250, 250, 250), (int(mp.left + 6 + sl["w"] * (mp.w - 12)), int(mp.bottom - 8 - sl["u"] / 0.5 * (mp.h - 16))), 5, 1)
        bd.put(s, bd.font(26).render(self.fit_text(td["name"].upper(), 26, 215), True, (232, 236, 255)), left=px0, cy=270)
        for i, fname in enumerate(FORMATIONS):
            r = pygame.Rect(px0 + (i % 3) * 72, 290 + (i // 3) * 33, 66, 28)
            self.su_chip(s, r, fname, self.form_names[c] == fname, r.collidepoint(vx, vy), col)
            hits.append((r, ("form", c, fname)))
        rows = (len(FORMATIONS) + 2) // 3
        ry = 290 + rows * 33 + 8
        bd.put(s, bd.font(16).render(tr("intro.starters"), True, bd.DIM), left=px0, top=ry)
        slots = self.lineup_slots(c)
        for i, (role, ni) in enumerate(slots):
            rr = pygame.Rect(px0 + (i // 6) * 110, ry + 18 + (i % 6) * 17, 108, 16)
            sel = self.su_pick == (c, i)
            if sel:
                pygame.draw.rect(s, tuple(int(v * 0.6) for v in col), rr, border_radius=3)
            elif rr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), rr, border_radius=3)
            nm = td["players"][ni] if ni < len(td["players"]) else ""
            bd.put(s, bd.font(15).render(ROLE_LETTER[role], True, bd.DIM), left=rr.left + 2, cy=rr.centery)
            bd.put(s, bd.font(15).render(self.fit_text(nm or "-", 15, 90), True, bd.WHITE), left=rr.left + 14, cy=rr.centery)
            hits.append((rr, ("slot", c, i)))
        if self.su_pick and self.su_pick[0] == c:
            pi = self.su_pick[1]
            role = slots[pi][0]
            lo, hi = ROLE_POOLS[role]
            used = set(self.lineup[c][role])
            cands = [n for n in range(lo, hi) if n not in used]
            ph = 30 + max(1, len(cands)) * 22
            pr = pygame.Rect(px0 - 6, 286, 222, ph)
            pygame.draw.rect(s, (14, 18, 44), pr, border_radius=6)
            pygame.draw.rect(s, (255, 224, 90), pr, 2, border_radius=6)
            lab = tr("role.long." + role)
            bd.put(s, bd.font(16).render(tr("intro.pick_new", role=lab), True, bd.DIM), left=pr.left + 8, top=pr.top + 5)
            if not cands:
                bd.put(s, bd.font(17).render(tr("intro.no_other"), True, bd.LIT), left=pr.left + 10, top=pr.top + 28)
            pops = []
            for k2, ni in enumerate(cands):
                cr = pygame.Rect(pr.left + 4, pr.top + 26 + k2 * 22, pr.w - 8, 21)
                if cr.collidepoint(vx, vy):
                    pygame.draw.rect(s, (46, 56, 112), cr, border_radius=3)
                nm = td["players"][ni] if ni < len(td["players"]) else ""
                bd.put(s, bd.font(18).render(self.fit_text("%s" % (nm or "-"), 18, pr.w - 24), True, bd.WHITE), left=cr.left + 6, cy=cr.centery)
                pops.append((cr, ("cand", ni)))
            hits[0:0] = pops

    def draw_joymap(self): # Draw the joystick-mapping and control-assignment screen.
        s, bd, j = self.su_surf, self.board, self.joy
        s.fill((10, 12, 28))
        hits = self.su_hits = []
        vx, vy = self.su_to_virtual(pygame.mouse.get_pos())
        W = SU_W
        bd.put(s, bd.font(46).render(tr("intro.joymap"), True, (232, 236, 255)), cx=W // 2, cy=26)
        pads = j.names()
        st = ", ".join(pads) if pads else tr("joy.none")
        bd.put(s, bd.font(26).render(self.fit_text(st, 16, W - 40), True, (140, 220, 160) if pads else (255, 170, 110)), cx=W // 2, cy=58)
        dt = 1.0 / 60.0
        self.jm_flash = {k: v - dt for k, v in self.jm_flash.items() if v - dt > 0}
        flash_ctrl = {j.control_of(t) for t in self.jm_flash}
        focus = None
        y = 80
        for act, _k, _u, label in JOY_ACTIONS:
            r = pygame.Rect(20, y, 410, 24)
            toks = j.cfg["buttons"].get(act, [])
            hov = r.collidepoint(vx, vy)
            waiting = self.jm_wait == act
            if waiting or (hov and not self.jm_wait):
                focus = act
            col = (96, 82, 20) if waiting else ((36, 44, 92) if hov else (22, 26, 56))
            pygame.draw.rect(s, col, r, border_radius=4)
            if j.is_held(act):
                pygame.draw.rect(s, (90, 220, 120), r, 2, border_radius=4)
            bd.put(s, bd.font(16).render(tr("joy.act." + act), True, (255, 236, 150) if waiting else bd.WHITE), left=r.left + 8, cy=r.centery)
            txt = tr("joy.press") if waiting else (", ".join(j.token_label(t) for t in toks) or "-")
            bd.put(s, bd.font(16).render(self.fit_text(txt, 16, 150), True, (255, 224, 90) if waiting else bd.LIT), cx=r.right - 80, cy=r.centery)
            hits.append((r, ("act", act)))
            y += 26
        bx, by0, bw, bh = 48, 0, 945, 800
        sc = min(560.0 / bw, 500.0 / bh)
        ox, oy = 450, 92
        if self.jm_img is None and self.joy_img_path:
            try:
                im = pygame.image.load(self.joy_img_path).convert_alpha()
                self.jm_img = pygame.transform.smoothscale(im.subsurface(pygame.Rect(bx, by0, bw, bh)).copy(), (int(bw * sc), int(bh * sc)))
            except (pygame.error, ValueError, OSError):
                self.jm_img = False
        if self.jm_img:
            pygame.draw.rect(s, (22, 26, 56), (ox - 6, oy - 6, self.jm_img.get_width() + 12, self.jm_img.get_height() + 12), border_radius=8)
            s.blit(self.jm_img, (ox, oy))
        else:
            bd.put(s, bd.font(18).render(tr("joy.img_missing", name=JOY_IMG), True, (255, 170, 110)), cx=ox + 280, cy=oy + 200)
        sel_ctrl = {j.control_of(t) for t in j.cfg["buttons"].get(focus, [])} if focus else set()
        bound = {j.control_of(t) for toks in j.cfg["buttons"].values() for t in toks}
        self.jm_spots = {}
        drag = self.jm_drag
        tgt = self.jm_near(drag["pos"][0], drag["pos"][1], skip=drag["ctrl"], rad=self.JM_SNAP) if drag else None
        chip = {"triangle": "Tri", "circle": "Cer", "cross": "Cro", "square": "Qua", "select": "Sel", "start": "Sta"}
        for name, (hx, hy) in JOY_HOTSPOTS.items():
            if name in ("lstick", "rstick"):
                continue
            cx, cy = int(ox + (hx - bx) * sc), int(oy + (hy - by0) * sc)
            self.jm_spots[name] = (cx, cy)
            if name in self.JM_DRAGGABLE:
                lab = chip.get(name, name.upper())
                moving = drag is not None and drag["ctrl"] == name
                if name in flash_ctrl:
                    pygame.draw.circle(s, (90, 255, 140), (cx, cy), 16, 0)
                elif name == tgt:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 19, 3)
                elif name in sel_ctrl:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 16, 3)
                if not moving:
                    pygame.draw.circle(s, (24, 34, 80), (cx, cy), 11, 0)
                    pygame.draw.circle(s, (120, 150, 230), (cx, cy), 11, 1)
                    bd.put(s, bd.font(11).render(lab, True, (230, 236, 255)), cx=cx, cy=cy)
            else:
                if name in flash_ctrl:
                    pygame.draw.circle(s, (90, 255, 140), (cx, cy), 15, 0)
                elif name in sel_ctrl:
                    pygame.draw.circle(s, (255, 215, 0), (cx, cy), 15, 3)
                elif name in bound:
                    pygame.draw.circle(s, (80, 140, 255), (cx, cy), 4, 0)
        if drag:
            dxp, dyp = int(drag["pos"][0]), int(drag["pos"][1])
            pygame.draw.circle(s, (255, 215, 0), (dxp, dyp), 14, 0)
            bd.put(s, bd.font(12).render(chip.get(drag["ctrl"], drag["ctrl"].upper()), True, (20, 20, 20)), cx=dxp, cy=dyp)
        for name, lab, dx_ in (("lstick", tr("joy.lstick"), 0), ("rstick", tr("joy.rstick"), 0)):
            hx, hy = JOY_HOTSPOTS[name]
            cx, cy = int(ox + (hx - bx) * sc), int(oy + (hy - by0) * sc)
            bd.put(s, bd.font(14).render(lab, True, (80, 84, 120)), cx=cx, cy=int(oy + (712 - by0) * sc))
        if self.jm_wait:
            msg = tr("joy.wait") + tr("joy.act." + self.jm_wait) + tr("joy.cancel_hint")
            colr = (255, 224, 90)
        else:
            msg = tr("joy.hint")
            colr = bd.LIT
        for i, line in enumerate(self._wrap(msg, bd.font(16), 560)):
            bd.put(s, bd.font(16).render(line, True, colr), cx=ox + 280, cy=oy + int(bh * sc) + 28 + i * 20)
        for rect, lab, tag in ((pygame.Rect(690, 660, 140, 34), tr("joy.reset"), ("reset",)),
                               (pygame.Rect(850, 660, 140, 34), tr("joy.close"), ("close",))):
            self.su_chip(s, rect, lab, False, rect.collidepoint(vx, vy), (120, 170, 230), 18)
            hits.append((rect, tag))
        info = "File: " + os.path.abspath(j.write_path)
        if j.error:
            info += "   !  " + j.error
        bd.put(s, bd.font(13).render(self.fit_text(info, 13, 640), True, (255, 170, 110) if j.error else (110, 118, 160)), left=450, cy=700)
        sc_, ox_, oy_ = self.su_scale()
        out = pygame.transform.smoothscale(s, (int(SU_W * sc_), int(SU_H * sc_)))
        self.screen.blit(out, (int(ox_), int(oy_)))

    def draw_lang_dropdown(self, s, bd, hits, vx, vy): # Draw the language selection dropdown.
        if not self.langs:
            return
        cur = T.current_language()
        names = dict(self.langs)
        btn = pygame.Rect(SU_W - 30 - 160, 12, 160, 26)
        lab = bd.font(16).render(tr("intro.language"), True, bd.DIM)
        bd.put(s, lab, left=btn.left - lab.get_width() - 8, cy=btn.centery)
        pygame.draw.rect(s, (30, 34, 66), btn, border_radius=6)
        edge = (255, 224, 90) if self.lang_open else ((120, 130, 210) if btn.collidepoint(vx, vy) else (70, 78, 130))
        pygame.draw.rect(s, edge, btn, 2, border_radius=6)
        shown = self.fit_text(names.get(cur, cur.upper()), 18, btn.w - 36)
        bd.put(s, bd.font(18).render(shown, True, (255, 255, 255)), left=btn.left + 8, cy=btn.centery)
        ax, ay = btn.right - 15, btn.centery
        arrow = [(ax - 5, ay + 3), (ax + 5, ay + 3), (ax, ay - 3)] if self.lang_open else [(ax - 5, ay - 3), (ax + 5, ay - 3), (ax, ay + 3)]
        pygame.draw.polygon(s, (190, 196, 230), arrow)
        hits.insert(0, (btn, ("lang_toggle",)))
        if not self.lang_open:
            return
        pr = pygame.Rect(btn.left, btn.bottom + 2, btn.w, 6 + len(self.langs) * 24)
        pygame.draw.rect(s, (14, 18, 44), pr, border_radius=6)
        pygame.draw.rect(s, (255, 224, 90), pr, 2, border_radius=6)
        pops = []
        for i, (code, name) in enumerate(self.langs):
            cr = pygame.Rect(pr.left + 3, pr.top + 3 + i * 24, pr.w - 6, 22)
            if code == cur:
                pygame.draw.rect(s, (46, 56, 112), cr, border_radius=3)
            elif cr.collidepoint(vx, vy):
                pygame.draw.rect(s, (36, 44, 92), cr, border_radius=3)
            bd.put(s, bd.font(18).render(self.fit_text(name, 18, cr.w - 12), True, bd.WHITE), left=cr.left + 6, cy=cr.centery)
            pops.append((cr, ("lang", code)))
        hits[0:0] = pops

    def draw_summary(self): # Draw the end-of-match summary and statistics.
        W, _H = self.overlay(150)
        title = tr("sum.half") if self.mode == "half" else tr("sum.full")
        self.text(title, self.font_l, (255, 255, 255), (W // 2, 70), True)
        self.text("%s %d - %d %s" % (TEAM_NAMES[0], self.score[0], self.score[1], TEAM_NAMES[1]), self.font_m, (255, 255, 255), (W // 2, 120), True)
        st = self.stats
        tot = max(0.001, st["poss"][0] + st["poss"][1])
        rows = [(tr("sum.poss"), "%d%%" % round(100 * st["poss"][0] / tot), "%d%%" % round(100 * st["poss"][1] / tot)),
                (tr("sum.shots"), st["shots"][0], st["shots"][1]), (tr("sum.fouls"), st["fouls"][0], st["fouls"][1]),
                (tr("sum.yellow"), st["yellow"][0], st["yellow"][1]), (tr("sum.red"), st["red"][0], st["red"][1]),
                (tr("sum.corners"), st["corners"][0], st["corners"][1])]
        y = 170
        for name, a, b in rows:
            self.text(str(a), self.font_m, TEAM_COL[0], (W // 2 - 150, y), True)
            self.text(name, self.font_s, (230, 230, 240), (W // 2, y), True)
            self.text(str(b), self.font_m, TEAM_COL[1], (W // 2 + 150, y), True)
            y += 34
        if self.mode == "full":
            self.text(tr("sum.hint"), self.font_s, (255, 230, 120), (W // 2, y + 18), True)

    def _help_layout(self, px, W, H, cols=None): # Calculate help-screen text and column positions.
        f = FONTS.get(px)
        tf = FONTS.get(int(px * 1.35))
        m = max(10, W // 50)
        gap = max(10, W // 60)
        cols = self.help_columns() if cols is None else cols
        cw = (W - 2 * m - (len(cols) - 1) * gap) // len(cols)
        lh = f.size("Ag")[1] + max(1, px // 8)
        sec_gap = lh // 2
        top = m + tf.size("Ag")[1] + max(6, px // 2)
        draws, worst = [], 0
        for ci, sections in enumerate(cols):
            x0 = m + ci * (cw + gap)
            y = top
            for title, entries in sections:
                draws.append(("title", title, x0, y, cw, tf))
                y += tf.size("Ag")[1] * 0 + f.size("Ag")[1] + max(4, px // 4)
                draws.append(("rule", None, x0, y - max(2, px // 8), cw, None))
                for key, desc in entries:
                    kl = self._wrap(key, f, int(cw * 0.46))
                    kw = int(cw * 0.46)
                    dl = self._wrap(desc, f, cw - kw - max(6, px // 2))
                    n = max(len(kl), len(dl))
                    for li in range(n):
                        if li < len(kl):
                            draws.append(("key", kl[li], x0, y + li * lh, kw, f))
                        if li < len(dl):
                            draws.append(("desc", dl[li], x0 + kw + max(6, px // 2), y + li * lh, cw - kw, f))
                    y += n * lh + max(2, px // 6)
                y += sec_gap
            worst = max(worst, y)
        return worst <= H - m, draws, m, tf

    def draw_help(self): # Draw the current page of in-game help.
        W, H = self.overlay(236)
        page = getattr(self, "help_page", 0)
        key = (W, H, page, T.current_language())

        cache = getattr(self, "_help_cache", None)
        if cache is None or cache[0] != key:
            help_cols = self.help_columns()
            chosen, paged = None, True
            page_cols = tuple((col,) for col in help_cols)
            page = min(page, len(page_cols) - 1)
            self.help_page = page
            for px in range(30, 7, -1):
                ok, draws, m, tf = self._help_layout(
                    px, W, H, page_cols[page]
                )
                chosen = (px, draws, m, tf)
                if ok:
                    break
            self._help_paged = True
            self._help_page_count = len(page_cols)
            cache = self._help_cache = (key, chosen)
        px, draws, m, tf = cache[1]
        f = FONTS.get(px)
        t = self.target

        t.blit(tf.render(tr("help.title"), True, (255, 215, 0)), (m, m // 2 + 2))

        label = tr("help.close_hint")
        if self._help_paged:
            last = page >= self._help_page_count - 1
            label = tr("help.page", page=page + 1, pages=self._help_page_count,
                       action=tr("help.close") if last else tr("help.next"))

        hint = f.render(label, True, (170, 176, 210))
        t.blit(hint, (W - m - hint.get_width(), m // 2 + 4))

        for kind, text, x, y, w, fnt in draws:
            if kind == "title":
                t.blit(fnt.render(text, True, (255, 215, 0)), (x, y))
            elif kind == "rule":
                pygame.draw.line(t, (110, 96, 30), (x, y), (x + w - 2, y))
            elif kind == "key":
                t.blit(fnt.render(text, True, (150, 220, 255)), (x, y))
            else:
                t.blit(fnt.render(text, True, (236, 236, 246)), (x, y))
