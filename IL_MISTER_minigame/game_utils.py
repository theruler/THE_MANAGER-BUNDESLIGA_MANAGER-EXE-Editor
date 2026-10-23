import math


def clamp(v, lo, hi): # Return a value restricted to the inclusive lower and upper bounds.
    return lo if v < lo else hi if v > hi else v


def unit(x, y, default=(1.0, 0.0)): # Return a normalized 2D vector, or the fallback vector when its length is zero.
    length = math.hypot(x, y)
    return (x / length, y / length) if length > 1e-9 else default


def dir8(dx, dy, diag=True): # Map a movement vector to one of the eight supported directions.
    ax, ay = abs(dx), abs(dy)
    if ax == 0 and ay == 0:
        return None
    if ay < 0.41 * ax:
        d = "E" if dx > 0 else "W"
    elif ax < 0.41 * ay:
        d = "S" if dy > 0 else "N"
    else:
        d = ("S" if dy > 0 else "N") + ("E" if dx > 0 else "W")
        if not diag:
            d = d[1]
    return d


def wline(a, b, n=24): # Return evenly spaced values between two endpoints.
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
