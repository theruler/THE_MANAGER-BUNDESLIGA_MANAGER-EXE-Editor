"""Run many headless matches and print gameplay averages (goals, shots, saves, team shape).

Usage: python tools/calibrate.py [--seeds 24] [--jobs 2] [--code DIR] [--json out.json]
Compare two code trees by running it once for each (--code old_tree, --code new_tree).
"""
import argparse, json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

here = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--seeds", type=int, default=24)
ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
ap.add_argument("--code", default=os.path.dirname(here))
ap.add_argument("--json", default=None)
cli = ap.parse_args()

def run(seed):
    out = subprocess.run([sys.executable, os.path.join(here, "headless_match.py"), "--seed", str(seed), "--code", cli.code],
                         capture_output=True, text=True).stdout.strip().splitlines()
    return json.loads(out[-1])

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
