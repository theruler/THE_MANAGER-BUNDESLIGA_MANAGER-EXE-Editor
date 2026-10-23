"""Before/after scenario tests for the tuning patches. Usage: python tools/test_tuning.py [CODEDIR]
Works on older code trees too (features that do not exist are reported, not failed), so you can compare two versions."""
import os, sys, math, random, argparse
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1"); os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
_root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stubs")); sys.argv = sys.argv[:1]
import pygame; pygame.init(); pygame.display.set_mode((64, 64))
import il_mister as M, geometry as geo
from resources import default_teams
for _kv in filter(None, os.environ.get('TUNE', '').split(',')): # e.g. TUNE=ai_system.SAVE_SLIDE_R=0 to experiment without editing code
    _k, _v = _kv.split('='); _m, _a = _k.split('.'); setattr(__import__(_m), _a, float(_v))
class DB:
    def __init__(s, *a, **k): s.hit_rows = []; s.gfx_icon = None
class FG: board_path = None; roster_icon = None; shadow_top = 0
M.Scoreboard = DB; M.load_data(["/nonexistent"])
args = argparse.Namespace(zoom=5, half=3.0, noscroll=False, no_replay=True, replay_secs=5, tore_dir=None, joy_dirs=[], joy_write_dir=None,
                          joy_img=None, no_slowmo=True, selftest=None)
def new_game(user=None):
    g = M.Game(args, FG(), M.Audio(False, os.path.join(os.environ.get("TMPDIR", "/tmp"), ".tore_audio")), pygame.Surface((300, 200)), [], default_teams())
    g.user_team = user; g.mode = "play"; g.restart = None; return g
ok = True; dt = 1 / 60.0
def check(name, cond, info=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (("  " + info) if info else ""))
def info(name, text): print("INFO " + name + "  " + text)

# ---------------------------------------------------------------- 1. goalkeeper foresight
g = new_game(); gk = g.team_p[1][0]; gk.skill = 0.8; b = g.ball
if hasattr(g, "keeper_reading"):
    def chance(dist, setp=None, pen=False):
        b.shot_team, b.shot_dist, b.shot_set, b.pen = 0, dist, setp, pen; b.wv = geo.V_GC + 2.0
        return g.keeper_save_chance(gk, 250.0, 3.0)
    near, far, vfar, fk, pen = chance(30), chance(90), chance(130), chance(40, "free"), chance(130, None, True)
    check("save chance grows with shot distance", near < far < vfar + 1e-9 or (far >= near and vfar >= far), f"near {near:.2f}  90u {far:.2f}  130u {vfar:.2f}")
    check("free kick is read better than an open-play shot from the same spot", fk > near + 0.1, f"{near:.2f} -> {fk:.2f}")
    check("penalty gets no foresight bonus", abs(pen - chance(30, None, True)) < 1e-9, f"{pen:.2f}")
    check("long shots can still score (chance < 1)", vfar < 0.95, f"{vfar:.2f}")
else:
    info("keeper foresight", "not present in this code tree")

# ---------------------------------------------------------------- 2. balls leaving over a touchline: how often are they kept in play?
def exit_trial(seed):
    random.seed(seed); g = new_game(); b = g.ball
    outs = [0]; orig = g.throw_in_out
    def counted(): outs[0] += 1; return orig()
    g.throw_in_out = counted
    side = random.choice((-1.0, 1.0))                                   # -1 north touchline, +1 south touchline
    edge = geo.V_TOP if side < 0 else geo.V_BOT
    while True:                                                         # fair scenarios: the ball leaves 0.4-1.4 s from now
        x = random.uniform(70, 240); v = edge - side * random.uniform(14, 60)
        speed = random.uniform(40, 150); ang = random.uniform(-0.5, 0.5)
        b.owner = None; b.wx, b.wv, b.z = x, v, 0.5; b.vx, b.vv, b.vz = speed * math.sin(ang), side * speed * math.cos(ang), 0.0
        b.ds = 1.0
        ex = None
        for i in range(1, 15):
            px, pv = g.ball_pred(i * 0.1)
            if pv < geo.V_TOP or pv > geo.V_BOT: ex = (i * 0.1, px, pv); break
        if ex and 0.4 <= ex[0] <= 1.4 and 20 < ex[1] < geo.L - 20: break
    b.shot_team = None; b.last_team = random.choice((0, 1)); b.intended = None; b.pass_active = False; b.age = 1.0
    team = random.choice((0, 1))
    mover = [q for q in g.team_p[team] if q.role != "GK"][random.randrange(10)]
    for q in g.players:
        q.state = "out"; q.wx, q.wv = 5.0, geo.V_GC; q.vx = q.vv = 0.0; q.tx = q.tv = None
    mover.state, mover.ctrl, mover.cool, mover.act_cd = "free", False, 0.0, 0.0
    ang2 = random.uniform(0, 2 * math.pi); r = random.uniform(10, 40)
    mover.wx = max(10, min(geo.L - 10, ex[1] + r * math.cos(ang2))); mover.wv = clamp_v(ex[2] - side * 2 + r * math.sin(ang2) * 0.5)
    g.role_timer = 0.0
    for _ in range(int(2.4 / dt)):
        g.update(dt)
        if outs[0] or b.owner is not None: break
    return outs[0] == 0
def clamp_v(v): return max(geo.V_TOP + 1.0, min(geo.V_BOT - 1.0, v))
N = 300; kept = sum(exit_trial(s) for s in range(N))
info("balls kept in play", f"{kept}/{N} = {kept / N * 100:.0f}% of loose balls heading for the touchline exit 0.4-1.4 s away, one outfield player 10-40 units from the exit point")
SAVE_RATE = kept / N

# ---------------------------------------------------------------- 3. referee walks to the offender before the card
def card_trial(seed):
    random.seed(seed); g = new_game(); r = g.ref; off = g.team_p[0][6]; vic = g.team_p[1][6]
    for q in g.players:
        if q not in (off, vic): q.state = "out"
    off.wx, off.wv, vic.wx, vic.wv = 200.0, geo.V_GC + 6, 203.0, geo.V_GC + 5
    for q in (off, vic): q.state = "free"
    r.wx, r.wv = 120.0, geo.V_GC - 20
    g.ball.wx, g.ball.wv = vic.wx, vic.wv
    g.call_foul(off, vic, 1.0, 0.0)
    if g.foul is None: return None
    g.foul["card"] = "Y"; g.foul["shown"] = False
    glide = frames = 0; shown_dist = None; prev = (r.wx, r.wv); jump = 0.0
    for _ in range(int(9 / dt)):
        g.update(dt); frames += 1
        sp = math.hypot(r.wx - prev[0], r.wv - prev[1]) / dt; jump = max(jump, math.hypot(r.wx - prev[0], r.wv - prev[1])); prev = (r.wx, r.wv)
        walk = M.REF_MOVE[r.face] if hasattr(M, "REF_MOVE") else __import__("sprite_data").REF_MOVE[r.face]
        if sp > 4.0 and r.sid not in walk: glide += 1
        if r.card and shown_dist is None: shown_dist = math.hypot(r.wx - off.wx, r.wv - off.wv)
        if g.mode != "foul": break
    return glide, shown_dist, jump
res = [card_trial(s) for s in range(20)]; res = [x for x in res if x]
if res:
    gl = sum(r[0] for r in res) / len(res); dists = [r[1] for r in res if r[1] is not None]
    info("referee", f"gliding frames per card (moving without walk cycle): {gl:.1f};  distance to the player when the card appears: {sum(dists)/max(1,len(dists)):.1f} units over {len(res)} cards")
    check("referee never glides without walking", gl < 1.0, f"{gl:.1f} frames")
    check("card shown only when the referee is next to the player", dists and max(dists) < 16.0, f"max {max(dists):.1f}")
else:
    info("referee", "no foul could be staged")

# ---------------------------------------------------------------- 4. sub-pixel scrolling is pixel-exact and monotone
if hasattr(g, "cam_view") and hasattr(g, "scale_world"):
    g = new_game(user=0); g.scroll = True; g.replay = None; g.paused = False; g.cam_manual = False
    z = g.zoom; src = pygame.Surface((geo.FW, geo.FH))
    for x in range(geo.FW):
        for y in range(0, geo.FH, 1): src.set_at((x, y), (x * 7 % 256, y * 13 % 256, (x // 3 + y) % 256))
    ref = pygame.transform.scale(src, (geo.FW * z, geo.FH * z)); bad = 0; steps = []
    last = None
    for i in range(120):
        g.cam[0] = 20.0 + i * 0.173; g.cam[1] = 10.0 + i * 0.091
        cx, cy, ox, oy = g.cam_view()
        vs = pygame.Surface((g.view_w, g.view_h))
        w = g.world_surface((g.vw + (1 if ox else 0)) * z, (g.vh + (1 if oy else 0)) * z) if (ox or oy) else vs
        g.scale_world(src, cx, cy, ox, oy, dest=w)
        if w is not vs: vs.blit(w, (-ox, -oy))
        px, py = cx * z + ox, cy * z + oy
        for (sx, sy) in ((0, 0), (333, 77), (g.view_w - 1, g.view_h - 1), (500, 300)):
            if vs.get_at((sx, sy))[:3] != ref.get_at((px + sx, py + sy))[:3]: bad += 1
        if last is not None: steps.append(px - last)
        last = px
    check("sub-pixel view equals the exact screen-pixel crop of the world", bad == 0, f"{bad} mismatching samples")
    check("horizontal scroll advances in screen-pixel steps (not whole native pixels)", max(steps) <= 2 and min(steps) >= 0, f"max step {max(steps)} px (native pixel = {z} px)")
    g.replay = {"frames": [], "i": 0}; cx, cy, ox, oy = g.cam_view()
    check("replay keeps the original pixel-snapped camera", (ox, oy) == (0, 0))
else:
    info("camera", "not present in this code tree")
print("SAVE_RATE=%.3f" % SAVE_RATE)
print("ALL PASS" if ok else "SOME FAILED"); sys.exit(0 if ok else 1)
