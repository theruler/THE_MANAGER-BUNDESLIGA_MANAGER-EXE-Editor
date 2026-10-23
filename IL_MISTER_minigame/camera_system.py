import pygame

from game_utils import clamp
from geometry import SCROLL_MAX_X, SCROLL_MAX_Y, w2s, WIN_H, WIN_W, Y_OFFSET
from layout import compute_layout


SMOOTH_SCROLL = True # Sub-pixel scrolling in live play (the replay always uses the original pixel-snapped camera).
PAN_DEAD_PX = 10 # Screen-space dead zone before the camera begins horizontal or vertical tracking.
PAN_HYSTERESIS_MS = 2000 # Time window used to prevent rapid camera direction changes.
CAM_GLIDE_SECS = 0.6 # Seconds used to ease the camera toward a new target position.


class CameraMixin: # View sizing, zoom fitting, and camera tracking.
    def set_view_dims(self): # Calculate the virtual view size and its visible field bounds.
        d = compute_layout(self.zoom, self.scroll)
        self.vw, self.vh = d["vw"], d["vh"]
        self.view_w, self.view_h, self.W, self.H = d["view_w"], d["view_h"], d["W"], d["H"]
        self.bs, self.bh, self.bar_h = d["bs"], d["bh"], d["bar_h"]
        self.field_y = self.bh
        self.bar_y = self.bh + self.view_h
        self.hud_y = self.bar_y + self.bar_h
        if self.vsurf is None or self.vsurf.get_size() != (self.view_w, self.view_h):
            self.vsurf = pygame.Surface((self.view_w, self.view_h))

    def fit_zoom(self, zoom): # Clamp and fit the requested zoom to the available display area.
        try:
            dw, dh = pygame.display.get_desktop_sizes()[0]
        except (AttributeError, IndexError, pygame.error):
            dw, dh = 0, 0
        if dw <= 0 or dh <= 0:
            dw, dh = 1920, 1080
        zoom = int(clamp(zoom, 2, 8))
        while zoom > 2:
            d = compute_layout(zoom, self.scroll)
            if d["W"] <= dw * 0.98 and d["H"] <= dh * 0.92:
                break
            zoom -= 1
        return zoom

    def apply_view(self): # Apply the current view dimensions and refresh camera limits.
        self.zoom = self.fit_zoom(self.zoom)
        self.vsurf = None
        self.paused_gesture = None
        self.paused_traj_data = None
        self.set_view_dims()
        flags = pygame.FULLSCREEN if self.fullscreen else pygame.RESIZABLE
        try:
            screen = pygame.display.set_mode((int(self.W), int(self.H)), flags)
        except pygame.error:
            screen = pygame.display.set_mode((int(self.W), int(self.H)))
        self.screen = screen
        self.target = screen
        self.update_cam(0.0, True)

    def cam_int(self): # Return the camera offset rounded to integer pixels.
        if not self.scroll:
            return 0, 0
        return int(clamp(self.cam[0], 0, SCROLL_MAX_X)), int(clamp(self.cam[1], 0, SCROLL_MAX_Y))

    def cam_view(self): # Integer crop origin plus the leftover sub-pixel offset in screen pixels (0 in replay, pause and manual camera).
        cx, cy = self.cam_int()
        if not (SMOOTH_SCROLL and self.scroll) or self.replay or self.paused or self.cam_manual:
            return cx, cy, 0, 0
        z = self.zoom
        fx = clamp(self.cam[0], 0, SCROLL_MAX_X) - cx
        fy = clamp(self.cam[1], 0, SCROLL_MAX_Y) - cy
        return cx, cy, int(fx * z), int(fy * z)

    def scale_world(self, src, cx, cy, ox, oy, dest=None): # Scale the camera crop of a native-resolution layer to screen size (one extra native pixel on each shifted axis).
        z = self.zoom
        w, h = self.vw + (1 if ox else 0), self.vh + (1 if oy else 0)
        view = src.subsurface(pygame.Rect(cx, cy, w, h))
        if dest is not None and dest.get_size() == (w * z, h * z):
            pygame.transform.scale(view, (w * z, h * z), dest)
            return dest
        return pygame.transform.scale(view, (w * z, h * z))

    def world_surface(self, w, h): # Cached scratch surface for the oversized world layer used by sub-pixel scrolling.
        cache = self.__dict__.setdefault("_world_surfs", {})
        if (w, h) not in cache:
            cache[(w, h)] = pygame.Surface((w, h))
        return cache[(w, h)]

    def update_cam(self, dt, snap=False): # Move the camera toward its target using the configured easing and dead zone.
        if not self.scroll:
            self.cam[0] = self.cam[1] = 0.0
            return
        if self.cam_manual:
            return
        b = self.ball
        px, gy = w2s(b.wx, b.wv)
        tx, ty = px + clamp(b.vx * 0.15, -28, 28), gy + Y_OFFSET + 4 - b.z * 0.4
        if self.mode == "goal" and self.goal and self.goal["t"] > 0.6:
            sc = self.goal["scorer"]
            tx, ty = sc.sx, sc.sy + Y_OFFSET + 6
        elif self.mode == "foul" and self.foul:
            v = self.foul["victim"]
            tx, ty = v.sx, v.sy + Y_OFFSET + 6
        wx = clamp(tx - WIN_W / 2.0, 0, SCROLL_MAX_X)
        wy = clamp(ty - WIN_H / 2.0, 0, SCROLL_MAX_Y)
        k = 1.0 if snap else min(1.0, (16.0 if self.cam_glide > 0.0 else 6.5) * dt)
        if self.cam_glide > 0.0:
            self.cam_glide = max(0.0, self.cam_glide - dt)
        self.cam[0] += (wx - self.cam[0]) * k
        self.cam[1] += (wy - self.cam[1]) * k
