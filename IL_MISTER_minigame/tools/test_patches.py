"""Targeted tests for the gameplay patches (tackle aim, cursor aim, live steering, restart alignment, shot blocks, keeper odds).

Usage: python tools/test_patches.py [CODEDIR]   (defaults to the project root)
"""
import os, sys, math, random, time, argparse
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"; os.environ["SDL_VIDEODRIVER"] = "dummy"; os.environ["SDL_AUDIODRIVER"] = "dummy"
_root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root); sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stubs")); sys.argv = sys.argv[:1]
import pygame; pygame.init(); pygame.display.set_mode((64, 64))
import il_mister as M, geometry as geo, restart_system as RS, physics_system as PH
class DB:
    def __init__(s, *a, **k): s.hit_rows = []; s.gfx_icon = None
class FG: board_path = None; roster_icon = None; shadow_top = 0
M.Scoreboard = DB; M.load_data(["/nonexistent"]); random.seed(5)
args = argparse.Namespace(zoom=5, half=3.0, noscroll=False, no_replay=True, replay_secs=5, tore_dir=None, joy_dirs=[], joy_write_dir=None,
                          joy_img=None, no_slowmo=True, selftest=None)
def new_game():
    g = M.Game(args, FG(), M.Audio(False, os.path.join(os.environ.get("TMPDIR", "/tmp"), ".tore_audio")), pygame.Surface((300, 200)), [], __import__("resources").default_teams())
    g.user_team = 0; g.mode = "play"; g.restart = None; return g
ok = True
def check(name, cond, info=""):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name + (("  " + info) if info else ""))
dt = 1 / 60.0

# ---- 1. slide / tackle sends the ball where the user aims
def tackle_trial(aim, kind, seed):
    random.seed(seed); g = new_game(); b = g.ball
    t = g.team_p[0][5]; o = g.team_p[1][5]
    for q in g.players:
        if q not in (t, o): q.wx, q.wv, q.state = 5.0, 5.0, "out"
    o.wx, o.wv, o.vx, o.vv, o.dx, o.dv = 150.0, geo.V_GC, 0.0, 0.0, -1.0, 0.0
    t.wx, t.wv, t.state, t.dx, t.dv = 142.0, geo.V_GC, "free", 1.0, 0.0
    b.owner = o; b.wx, b.wv = o.wx - 4.5, o.wv
    ux, uv = M.unit(o.wx - t.wx, o.wv - t.wv)          # lunge direction toward the carrier
    g.give_ball = lambda q: None            # observe the raw knock-on, not the optional immediate pick-up
    t.act_cd = 0.0; g.start_tackle(t, ux, uv, kind, aim=aim)
    for _ in range(90):
        g.step_player(t, dt) if False else None
        if t.state == "action": g.step_action(t, dt)
        if b.owner is None and math.hypot(b.vx, b.vv) > 5: break
    return (b.owner is None and math.hypot(b.vx, b.vv) > 5), M.unit(b.vx, b.vv)
for kind in ("slide", "stand"):
    aim = (0.0, 1.0); cs = []; hits = 0
    for sd in range(200):
        won, d = tackle_trial(aim, kind, sd)
        if won: hits += 1; cs.append(d[0] * aim[0] + d[1] * aim[1])
    check(f"{kind} tackle: ball follows aim (cos>0.9)", hits > 5 and sum(1 for c in cs if c > 0.9) >= 0.9 * len(cs), f"{hits} ball wins, mean cos {sum(cs)/max(1,len(cs)):.3f}")
# no aim recorded -> old behaviour (facing/lunge direction)
random.seed(1); g = new_game(); t = g.team_p[0][5]; t.dx, t.dv = 1.0, 0.0; g.begin_action(t, "slide", "E", dx=1.0, dv=0.0, speed=88.0)
dx, dv = g.deflect_dir(t); check("deflect_dir falls back to facing without aim", abs(dx - 1.0) < 1e-9 and abs(dv) < 1e-9)

# ---- 2. mouse cursor aim
g = new_game(); p = g.team_p[0][5]; p.wx, p.wv = 150.0, geo.V_GC; p.kvec = None
g.field_y = 0
sx, sy = None, None
g.cam = [60.0, 8.0]
gx, gy, _w = g.screen_to_ground(100, 60)
tx, tv = _w
g.mouse_xy, g.mouse_moved_at = (100, 60), time.time()
d = g.aim_dir(p); exp = M.unit(tx - p.wx, tv - p.wv)
check("cursor aim points at the mouse when it just moved", d[0] * exp[0] + d[1] * exp[1] > 0.999, f"{d}")
g.mouse_moved_at = time.time() - 5
p.dx, p.dv = -1.0, 0.0
check("stale cursor is ignored (falls back to facing)", g.aim_dir(p) == (-1.0, 0.0))

# ---- 3. live steering of a spectacular action
g = new_game(); p = g.team_p[0][5]; p.ctrl = True; p.wx, p.wv = 100.0, geo.V_GC
g.begin_action(p, "bicycle", "E", dx=1.0, dv=0.0, power=255.0, lift=30.0, kind="shot", assist=True, steer=True)
g.aim_input = lambda q: (0.0, 1.0)
a = p.act
for _ in range(8): g.steer_action_aim(p, a, dt)
c = a["kw"]["dv"]
check("steering rotates the pending shot toward live aim", 0.3 < c < 1.0 and abs(math.hypot(a["kw"]["dx"], a["kw"]["dv"]) - 1.0) < 1e-6, f"dv after 8 frames = {c:.2f}")
g.aim_input = lambda q: None; before = (a["kw"]["dx"], a["kw"]["dv"]); g.steer_action_aim(p, a, dt)
check("no input -> direction unchanged", before == (a["kw"]["dx"], a["kw"]["dv"]))

# ---- 4. restart alignment: every kick restart uses the same feet-on-ball model
g = new_game(); g.att = {0: 1, 1: -1}
res = {}
for kind in ("kickoff", "free", "penalty", "corner", "goal", "goalkick", "throw"):
    for team in (0, 1):
        pos = (60.0, geo.V_GC) if kind != "corner" else (2.0, geo.V_TOP + 1.0)
        rs = dict(kind=kind, pos=pos, team=team); wx, wv = g.taker_stand(rs)
        bsx, bsy = geo.w2s(*pos); psx, psy = geo.w2s(wx, wv)
        res[(kind, team)] = (round(psx - bsx, 2), round(psy - bsy, 2))
kick_rows = {k: v for k, v in res.items() if k[0] not in ("throw", "corner")}
spread = max(v[1] for v in kick_rows.values()) - min(v[1] for v in kick_rows.values())
check("kickoff/free/penalty/goal kick share one vertical screen offset", spread < 0.01, f"dy values {sorted(set(v[1] for v in kick_rows.values()))}")
bsx, bsy = geo.w2s(60.0, geo.V_GC); psx, psy = geo.w2s(*g.taker_stand(dict(kind='free', pos=(60.0, geo.V_GC), team=0)))
check("stand point: BALL_AHEAD behind the ball (screen x) and FOOT_PX below/above it (screen y)",
      abs(psx - (geo.w2s(60.0 - RS.BALL_AHEAD, geo.V_GC)[0] + RS.FOOT_PX["E"][0])) < 0.05 and abs(psy - (bsy + RS.FOOT_PX["E"][1])) < 0.05,
      f"dx_px={psx-bsx:.2f} dy_px={psy-bsy:.2f}")
check("dribble() and restart share the standing offset", RS.BALL_AHEAD == PH.STANDING_BALL_OFFSET == 4.5)

# ---- 5. shot blocks: only hard shots by the other team; passes untouched
random.seed(3); g = new_game(); b = g.ball; d = g.team_p[1][4]
for q in g.players:
    if q is not d: q.wx, q.wv, q.state = 5.0, 5.0, "out"
n_block = 0; n = 2000
for i in range(n):
    b.owner = None; b.wx, b.wv, b.z = d.wx + 1.0, d.wv, 1.0; b.vx, b.vv, b.vz = 240.0, 0.0, 0.0
    b.shot_team, b.last_team, b.last, b.intended, b.pass_active, b.gk_attempted = 0, 0, g.team_p[0][3], None, False, False
    d.cool = 0.0; d.state = "free"; d.ctrl = False; g.mode = "play"; g.check_possession()
    if b.owner is None and b.shot_team is None: n_block += 1
check("hard shot is blocked ~BLOCK_CHANCE of the time", abs(n_block / n - PH.BLOCK_CHANCE) < 0.04, f"{n_block/n:.3f}")
b.owner = None; b.wx, b.wv, b.z = d.wx + 1.0, d.wv, 1.0; b.vx, b.vv, b.vz = 240.0, 0.0, 0.0
b.shot_team, b.last_team, b.pass_active = None, 0, True; d.cool = 0.0
g.check_possession(); check("fast pass (not a shot) is not 'blocked'", b.owner is None)

# ---- 6. keeper formula sanity
g = new_game(); gk = g.team_p[1][0]; gk.skill = 0.8; g.ball.shot_team = 0
g.ball.wv = geo.V_GC
c0 = g.keeper_save_chance(gk, 250.0, 3.0); g.ball.wv = geo.V_GC + geo.HALF_MOUTH * 0.85
c1 = g.keeper_save_chance(gk, 250.0, 3.0)
check("corner shot is harder to save than a central one", c1 < c0 - 0.1, f"centre {c0:.2f} vs corner {c1:.2f}")
check("harder shots are harder to save", g.keeper_save_chance(gk, 300.0, 3.0) < g.keeper_save_chance(gk, 150.0, 3.0))
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
