"""Ball motion model shared by live physics, previews and forecasts."""

import math

from geometry import depth_k, depth_v_k


STANDING_BALL_OFFSET = 4.5 # World units between a stationary player's anchor and the ball at his feet; shared by dribble() and restart placement.
G = 150.0 # Gravity applied to the ball in world units per second squared.


def step_ball_physics(x, v, z, vx, vv, vz, h, ds): # Advance the ball one physics step; shared by previews and forecasts.
    kk = depth_k(v)
    kv = depth_v_k(v, x)
    x += vx * h * kk
    v += vv * h * kv
    z += vz * h
    vz -= G * h
    if z <= 0.0:
        z = 0.0
        if vz < -35.0:
            vz, vx, vv = -vz * 0.55, vx * 0.88, vv * 0.88
        else:
            vz = 0.0
    f = math.exp(-(0.7 if z < 0.05 else 0.14) * h * ds)
    vx *= f
    vv *= f
    return x, v, z, vx, vv, vz
