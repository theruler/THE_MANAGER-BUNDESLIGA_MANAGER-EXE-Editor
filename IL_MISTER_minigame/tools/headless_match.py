"""Run one deterministic AI-vs-AI match without a window, sound or game assets.

Usage: python tools/headless_match.py [--seed N] [--seconds S] [--code DIR]

Prints one JSON line with score, shots, on-target shots, saves, blocks and team-shape metrics.
Used by calibrate.py; also handy for before/after comparisons when tuning gameplay constants.
"""
import argparse, hashlib, json, math, os, random, sys

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--seconds", type=float, default=900.0)
ap.add_argument("--code", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
cli = ap.parse_args()

sys.path.insert(0, cli.code)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stubs")) # Only used when the real i18n module is absent.
sys.argv = [sys.argv[0]]

import pygame
pygame.init()
pygame.display.set_mode((64, 64))
import geometry as geo
import il_mister as M
from resources import default_teams


class DummyBoard: # Scoreboard stand-in: the simulation never draws.
    def __init__(self, *a, **k): self.hit_rows, self.gfx_icon = [], None


class FakeGfx:
    board_path = roster_icon = None
    shadow_top = 0


M.Scoreboard = DummyBoard

# ---- read-only instrumentation: shot/goal distance buckets and touchline exits with a player nearby ----
shot_b = dict(near=0, mid=0, far=0, free=0, penalty=0); goal_b = dict(shot_b); exits = dict(n=0, near12=0, near20=0)
def _bucket(dist, kind):
    return kind if kind in ("free", "penalty") else ("near" if dist < 60 else "mid" if dist < 100 else "far")
_o_ot, _o_sg, _o_tio = M.Game.shot_is_on_target, M.Game.score_goal, M.Game.throw_in_out
def _ot(self, shooter):
    b = self.ball; gx = geo.L if self.att[shooter.team] > 0 else 0.0
    kind = self.restart["kind"] if self.mode == "restart" and self.restart else None
    self._h_last = _bucket(math.hypot(gx - b.wx, geo.V_GC - b.wv), kind); shot_b[self._h_last] += 1
    return _o_ot(self, shooter)
def _sg(self, team, gx):
    if getattr(self, "_h_last", None): goal_b[self._h_last] += 1
    return _o_sg(self, team, gx)
def _tio(self):
    b = self.ball; d = min((math.hypot(q.wx - b.wx, q.wv - min(max(b.wv, geo.V_TOP), geo.V_BOT)) for q in self.players if q.state == "free" and q.role != "GK"), default=999.0)
    exits["n"] += 1; exits["near12"] += d < 12; exits["near20"] += d < 20
    return _o_tio(self)
M.Game.shot_is_on_target, M.Game.score_goal, M.Game.throw_in_out = _ot, _sg, _tio
attempts = [] # (distance, restart kind, speed, reach, keeper skill, aim offset 0..1, penalty) of every shot save roll
if hasattr(M.Game, "keeper_save_chance"):
    _o_ksc = M.Game.keeper_save_chance
    def _ksc(self, gk, speed, reach_d):
        b = self.ball
        if b.shot_team is not None:
            attempts.append((round(getattr(b, "shot_dist", 0.0), 1), getattr(b, "shot_set", None), round(speed, 1), round(reach_d, 2), round(gk.skill, 3),
                             round(abs(b.wv - geo.V_GC) / geo.HALF_MOUTH, 3), bool(b.pen)))
        return _o_ksc(self, gk, speed, reach_d)
    M.Game.keeper_save_chance = _ksc
M.load_data(["/nonexistent"]) # Built-in default animation tables.
random.seed(cli.seed)
args = argparse.Namespace(zoom=5, half=3.0, noscroll=False, no_replay=True, replay_secs=5, tore_dir=None, joy_dirs=[],
                          joy_write_dir=None, joy_img=None, no_slowmo=True, selftest=None)
game = M.Game(args, FakeGfx(), M.Audio(False, os.path.join(os.environ.get("TMPDIR", "/tmp"), ".tore_audio")),
              pygame.Surface((300, 200)), [], default_teams())
game.user_team = None # Both sides are driven by the AI.
game.mode = "restart"

L, VT, PW = geo.L, geo.V_TOP, geo.PITCH_W
grid = [(x, VT + PW * i / 6.0) for x in range(0, int(L) + 1, 20) for i in range(7)]
cov = dict(n=0, mate=0.0, mate70=0.0, depth=0.0, hole=0.0)
digest, dt, t, n = hashlib.sha1(), 1.0 / 60.0, 0.0, 0
while t < cli.seconds and game.mode != "full":
    game.update(dt); t += dt; n += 1
    o = game.ball.owner
    if n % 30 == 0 and game.mode == "play" and o is not None and o.role != "GK":
        mates = sorted(math.hypot(q.wx - o.wx, q.wv - o.wv) for q in game.team_p[o.team] if q is not o and q.role != "GK")
        opp = [q for q in game.team_p[1 - o.team] if q.role != "GK"]
        xs = [q.wx for q in opp]
        cov["n"] += 1; cov["mate"] += mates[0]; cov["mate70"] += sum(1 for d in mates if d < 70)
        cov["depth"] += (max(xs) - min(xs)) / L * 100
        cov["hole"] += sum(1 for (gx, gv) in grid if min(math.hypot(gx - q.wx, gv - q.wv) for q in opp) > 45) / len(grid) * 100
    if n % 60 == 0:
        for p in game.players: digest.update(("%.3f,%.3f;" % (p.wx, p.wv)).encode())
        digest.update(("%.3f,%.3f,%.3f|" % (game.ball.wx, game.ball.wv, game.ball.z)).encode())
st = game.stats
print(json.dumps(dict(seed=cli.seed, t=round(t), score=game.score, shots=st["shots"], on_target=st.get("on_target"),
                      saves=st.get("saves"), blocks=st.get("blocks"), fouls=st["fouls"], corners=st["corners"],
                      hash=digest.hexdigest()[:16], nsamp=cov["n"], shot_b=shot_b, goal_b=goal_b, exits=exits, attempts=attempts,
                      cov={k: round(v / max(1, cov["n"]), 2) for k, v in cov.items() if k != "n"})))
