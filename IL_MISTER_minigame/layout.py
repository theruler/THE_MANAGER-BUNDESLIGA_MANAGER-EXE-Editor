"""Window/view layout calculations."""

from game_utils import clamp
from geometry import FH, FW, WIN_H, WIN_W
from graphics_system import BAR_DH, BOARD_H, BOARD_W, SB_DW


HUD_H = 76 # Height reserved for the bottom match HUD.


def board_scale(view_w): # Calculate the scoreboard scale for the current view width.
    return clamp(view_w / float(SB_DW), 0.4, 1.12)


def compute_layout(zoom, scroll): # Calculate the field viewport layout for the requested zoom and scroll.
    vw, vh = (WIN_W, WIN_H) if scroll else (FW, FH)
    view_w, view_h = vw * zoom, vh * zoom
    s = board_scale(view_w)
    kb = max(1, int(view_w // BOARD_W))
    bh = BOARD_H * kb
    bar_h = int(round(BAR_DH * s))
    return dict(vw=vw, vh=vh, view_w=view_w, view_h=view_h, bs=s, kb=kb, bh=bh, bar_h=bar_h, W=view_w, H=bh + view_h + bar_h + HUD_H)


SU_W, SU_H = 1020, 716 # Virtual width/height of the substitution interface.
