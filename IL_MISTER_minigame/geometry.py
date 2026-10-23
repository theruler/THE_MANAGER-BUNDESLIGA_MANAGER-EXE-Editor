"""World/screen geometry: perspective model, pitch landmarks, depth scaling and coordinate conversions."""

import bisect
import math
import sys

from game_utils import clamp, unit
from graphics_system import GOAL_Y0, GOAL_Y1


Y_OFFSET = 35 # Vertical sprite-to-field alignment offset in virtual screen pixels.
ORIG_FW, ORIG_FH = 320, 112 # Field width/height for the original-geometry display mode.
ORIG_WIN_W, ORIG_WIN_H = 182, 96 # Visible viewport width/height in original-geometry mode.
ORIG_SCROLL_MAX_X, ORIG_SCROLL_MAX_Y = 137, 15 # Maximum horizontal/vertical scroll for the original-geometry viewport.
GEOMETRY = "originale" if any(a in ("--geometria-originale", "--original-geometry") for a in sys.argv) else "estesa" # Field geometry selected by command-line flags.
if GEOMETRY == "originale":
    FIELD_X0 = 0 # Horizontal origin of the field artwork in original-geometry mode.
    FW, FH = ORIG_FW, ORIG_FH # Virtual field width/height for original-geometry mode.
    RUNOFF_Y = 0 # Extra playable runoff beyond the field boundary.
    WIN_W, WIN_H = ORIG_WIN_W, ORIG_WIN_H # Visible viewport width/height in original-geometry mode.
else:
    FIELD_X0 = 79 # Horizontal origin of the field artwork in extended-geometry mode.
    FW, FH = 480, 124 # Virtual field width/height for extended-geometry mode.
    RUNOFF_Y = 6 # Extra playable runoff beyond the field boundary.
    WIN_W, WIN_H = 204, 80 # Visible viewport width/height in extended-geometry mode.
SCROLL_MAX_X, SCROLL_MAX_Y = FW - WIN_W, FH - WIN_H # Derived maximum horizontal/vertical scroll for the selected geometry.
MAX_Y = 66 # Maximum playable longitudinal field coordinate.
BALL_Y_MIN = -Y_OFFSET # Minimum world-depth coordinate allowed for the ball near the north runoff.
PERSP_LINES = [(10, 61.0, 258.0), (43, -5.0, 324.0), (76, -71.0, 390.0)] # Perspective calibration samples: screen row, left edge, and right edge.
PERSP_Y_REF = 39 # Reference screen row used to normalize the field perspective.
PERSP_Y_LAST = 76 # Last calibrated screen row used by the field projection.
PERSP_Y_SHIFT = PERSP_Y_LAST - MAX_Y # Derived vertical shift between the calibrated field and playable boundary.


def _edge_model(pts): # Build an interpolated model of the field edges from calibration points.
    n = len(pts)
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    slope = (n * sxy - sx * sy) / (n * sxx - sx * sx)

    def f(y): # Interpolate a calibration value along the field-edge model.
        if y <= pts[0][0]:
            return pts[0][1] + slope * (y - pts[0][0])
        if y >= pts[-1][0]:
            return pts[-1][1] + slope * (y - pts[-1][0])
        for i in range(1, n):
            if y <= pts[i][0]:
                (y0, x0), (y1, x1) = pts[i - 1], pts[i]
                return x0 + (x1 - x0) * (y - y0) / (y1 - y0)
    return f


_edge_l = _edge_model([(y, x0) for y, x0, _x1 in PERSP_LINES])
_edge_r = _edge_model([(y, x1) for y, _x0, x1 in PERSP_LINES])


def persp_edges(y): # Return the left and right projected field edges at a screen row.
    return _edge_l(y), _edge_r(y)


def persp_width(y): # Return the projected field width at a screen row.
    left, right = persp_edges(y)
    return max(20.0, right - left)


_PERSP_WREF = persp_width(PERSP_Y_REF) # Reference field width used to normalize perspective calculations.
_PV_Y0, _PV_STEP, _PV_N = -20.0, 0.5, 321 # _PV_Y0: first sampled row; _PV_STEP: row interval; _PV_N: sample count.


def _build_pv(): # Build the lookup table that maps screen rows to world depth.
    v = [0.0]
    for i in range(1, _PV_N):
        y0 = _PV_Y0 + (i - 1) * _PV_STEP
        v.append(v[-1] + _PERSP_WREF * _PV_STEP * 0.5 * (1.0 / persp_width(y0) + 1.0 / persp_width(y0 + _PV_STEP)))
    return v


_PV = _build_pv() # Precomputed mapping from projected screen rows to world-depth coordinates.


def _persp_v(y): # Convert a projected screen row into world-depth coordinates.
    t = (min(max(y, _PV_Y0), _PV_Y0 + _PV_STEP * (_PV_N - 1)) - _PV_Y0) / _PV_STEP
    i = min(int(t), _PV_N - 2)
    return _PV[i] + (_PV[i + 1] - _PV[i]) * (t - i)


def _persp_y(v): # Convert world depth into its projected screen row.
    i = min(max(bisect.bisect_right(_PV, v) - 1, 0), _PV_N - 2)
    return _PV_Y0 + (i + (v - _PV[i]) / (_PV[i + 1] - _PV[i])) * _PV_STEP


def persp_to_world(x, y): # Convert projected field coordinates into world coordinates.
    y += PERSP_Y_SHIFT
    x -= FIELD_X0
    left, right = persp_edges(y)
    return (x - left) / max(20.0, right - left) * _PERSP_WREF, _persp_v(y)


def persp_from_world(wx, wv): # Project world coordinates onto the field image.
    y = _persp_y(wv) - PERSP_Y_SHIFT
    left, right = persp_edges(y + PERSP_Y_SHIFT)
    return FIELD_X0 + left + wx / _PERSP_WREF * max(20.0, right - left), y


w2s = persp_from_world
s2w = persp_to_world
PITCH_TOP_Y, PITCH_BOT_Y = 0, 66 # World coordinate of the north/south touchline.
GOAL_D = 10.0 # Depth of the goal structure behind the goal line.
GOAL_NET_H = 10.0 # Vertical extent of the goal net used by collision and rendering code.
GATE_PX = 40.0 # Reference width of the goal opening in source pixels.
DEPTH_EXP = 0.5 # Exponent controlling how perspective depth changes with field position.
BALL_DEPTH_K = 0.4 # Depth-scaling factor used when projecting the ball.


def depth_slow(dx, dv): # Calculate the perspective speed factor for movement at a world position.
    n = math.hypot(dx, dv)
    if n < 1e-9:
        return 1.0
    return n / math.hypot(dx, dv / BALL_DEPTH_K)


GOAL_H = 10.0 # Goal height in world units.
POST_T = 1.2 # Goalpost thickness in world units.
BAR_LO, BAR_HI = 1.0, 1.0 # Lower/Upper vertical scale factor for the crossbar collision shape.
L = _PERSP_WREF


def pitch_v(gy): # Convert the field vertical coordinate into the internal world-depth coordinate.
    return persp_to_world(FW / 2.0, gy)[1]


V_TOP, V_BOT = pitch_v(PITCH_TOP_Y), pitch_v(PITCH_BOT_Y) # Derived world-depth coordinate of the north/south touchline.
V_MID = (V_TOP + V_BOT) / 2.0 # Derived midpoint between the two touchlines in world-depth space.
SPOT_Y = 27.5 # Longitudinal field coordinate of the penalty spot.
V_GC = (pitch_v(GOAL_Y0) + pitch_v(GOAL_Y1)) / 2.0 # Derived world-depth coordinate at the centre of the goal opening.
V_SPOT = pitch_v(SPOT_Y) # Derived world-depth coordinate of the penalty spot.
HALF_MOUTH = (pitch_v(GOAL_Y1) - pitch_v(GOAL_Y0)) / 2.0 # Half-width of the projected goal opening in world-depth space.
V_MIN_P, V_MAX_P = V_TOP, pitch_v(MAX_Y + RUNOFF_Y) # V_MIN_P: minimum player depth; V_MAX_P: maximum depth including runoff.
PITCH_W = V_BOT - V_TOP # Derived world-depth width of the playable pitch.
BOX_Y0, BOX_Y1 = 10, 46 # North/South edge of the penalty area in field coordinates.
GA_Y0, GA_Y1 = 18, 29 # North/South edge of the six-yard area in field coordinates.
PEN_Y = 25 # Longitudinal coordinate used for penalty placement.
BOX_V0, BOX_V1 = pitch_v(BOX_Y0), pitch_v(BOX_Y1)
GA_V0, GA_V1 = pitch_v(GA_Y0), pitch_v(GA_Y1)
V_PEN = pitch_v(PEN_Y) # Derived world-depth coordinate of the penalty spot.
BOX_D = 0.157 * L # Depth of the penalty area in world units.
GA_D = 0.052 * L # Depth of the six-yard area in world units.
PEN_D = 0.108 * L # Distance from goal line to the penalty spot in world units.


def in_box_fn(x, v, own_gx): # Check whether a world position lies inside a goal-area box.
    return abs(x - own_gx) < BOX_D and BOX_V0 <= v <= BOX_V1


GATE_K = _PERSP_WREF / persp_width(PERSP_Y_LAST) # Scale factor converting goal artwork measurements to world-space width.
GATE_HALF = GATE_PX / 2.0 * GATE_K # Half-width of the goal mouth in world-space units.
GATE_SPREAD = GATE_HALF - 6.0 * GATE_K # Effective goal-mouth half-width after the side-margin allowance.
_DK = {} # Cache of perspective scale factors indexed by quantized world depth.
_DVK = {} # Cache of vertical movement scale factors indexed by quantized field position.


def depth_k(v): # Return the perspective scaling factor for a given field depth.
    key = int(round(v * 2.0))
    k = _DK.get(key)
    if k is None:
        k = _DK[key] = (_PERSP_WREF / persp_width(_persp_y(key / 2.0))) ** DEPTH_EXP
    return k


def depth_v_k(v, x=None): # Match vertical movement speed to horizontal speed at the same field position.
    x = L * 0.5 if x is None else clamp(x, 0.0, L)
    key = (int(round(x * 2.0)), int(round(v * 2.0)))
    k = _DVK.get(key)
    if k is None:
        x0, v0 = key[0] / 2.0, key[1] / 2.0
        left_x, left_y = persp_from_world(x0 - 0.5, v0)
        right_x, right_y = persp_from_world(x0 + 0.5, v0)
        top_x, top_y = persp_from_world(x0, v0 - 0.5)
        bottom_x, bottom_y = persp_from_world(x0, v0 + 0.5)
        horizontal_scale = math.hypot(right_x - left_x, right_y - left_y)
        vertical_scale = math.hypot(bottom_x - top_x, bottom_y - top_y)
        k = _DVK[key] = depth_k(v0) * horizontal_scale / max(vertical_scale, 1e-9)
    return k


def seg_dist(px, py, ax, ay, bx, by): # Calculate the minimum distance between a point and a line segment.
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else clamp(((px - ax) * dx + (py - ay) * dy) / l2, 0.0, 1.0)
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def ground_to_img(wx, wv): # Convert world field coordinates to projected image coordinates.
    px, gy = persp_from_world(wx, wv)
    return px, gy + Y_OFFSET + 10


FIELD_ROW0 = PITCH_TOP_Y + Y_OFFSET + 10 # Derived first source row used to align field artwork.


def w2s_jac(wx, wv, h=0.5): # Calculate the local screen-to-world Jacobian at a projected field point.
    a, b = w2s(wx + h, wv), w2s(wx - h, wv)
    c, d = w2s(wx, wv + h), w2s(wx, wv - h)
    return ((a[0] - b[0]) / (2 * h), (c[0] - d[0]) / (2 * h)), ((a[1] - b[1]) / (2 * h), (c[1] - d[1]) / (2 * h))


def screen_to_world_dir(wx, wv, ux, uy): # Convert a screen-space direction into a world-space direction at the supplied field position.
    (a, b), (c, d) = w2s_jac(wx, wv)
    det = a * d - b * c
    if abs(det) < 1e-9:
        return unit(ux, uy)
    return unit((d * ux - b * uy) / det, (-c * ux + a * uy) / det)


def screen_x_of(wx, wv, dx, dv): # Estimate the screen-space horizontal displacement produced by a world-space movement.
    (a, b), _ = w2s_jac(wx, wv)
    return a * dx + b * dv
