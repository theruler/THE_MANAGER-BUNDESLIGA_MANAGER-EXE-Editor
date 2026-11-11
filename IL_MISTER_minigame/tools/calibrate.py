"""Run many headless matches and print gameplay averages (goals, shots, saves, team shape).

Usage: python tools/calibrate.py [--seeds 24] [--jobs 2] [--code DIR] [--json out.json]
Compare two code trees by running it once for each (--code old_tree, --code new_tree).
"""
import argparse, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, default=24)
ap.add_argument("--jobs", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)))
ap.add_argument("--code", default=os.path.dirname(here))
ap.add_argument("--json", default=None)
cli = ap.parse_args()
if cli.seeds < 1 or cli.jobs < 1:
    ap.error("--seeds and --jobs must be positive")

def run(seed):
    proc = subprocess.run([sys.executable, os.path.join(here, "headless_match.py"), "--seed", str(seed), "--code", cli.code],
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"seed {seed} failed (exit {proc.returncode}):\n{proc.stderr or proc.stdout}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"seed {seed} returned no result: {proc.stderr}")
    try:
        return json.loads(lines[-1])
    except json.JSONDecodeError as ex:
        raise RuntimeError(f"seed {seed} returned invalid JSON: {lines[-1]!r}") from ex

with ThreadPoolExecutor(cli.jobs) as ex:
    rows = list(ex.map(run, range(1, cli.seeds + 1)))
if cli.json:
    with open(cli.json, "w") as f: f.write("\n".join(json.dumps(r) for r in rows))
n = len(rows)
avg = lambda k: sum(sum(r[k]) for r in rows if r.get(k)) / n
goals = sum(sum(r["score"]) for r in rows) / n
saves = avg("saves")
ns = sum(r["nsamp"] for r in rows) or 1
cv = lambda k: sum(r["cov"][k] * r["nsamp"] for r in rows) / ns
print(f"matches={n}  goals/match={goals:.2f}  shots={avg('shots'):.1f}  on_target={avg('on_target'):.1f}  saves={saves:.1f}  blocks={avg('blocks'):.1f}")
print(f"save/(save+goal)={saves / max(saves + goals, 1e-9) * 100:.0f}%   nearest_mate_to_carrier={cv('mate'):.1f}  mates<70={cv('mate70'):.1f}  "
      f"defending_block_depth={cv('depth'):.1f}%L  pitch_holes>45u={cv('hole'):.1f}%")
