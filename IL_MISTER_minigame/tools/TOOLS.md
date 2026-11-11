## Tools (no graphics assets required for these diagnostics)

```bash
python tools/test_patches.py              # Focused gameplay regression tests
python tools/test_tuning.py               # Scenario-based tuning checks
python tools/headless_match.py --seconds 900 --seed 1  # One deterministic AI-vs-AI match
python tools/calibrate.py --seeds 24 --jobs 4          # Multi-seed averages for goals, saves and team shape
python il_mister.py --selftest 900 --seed 1            # In-game simulation self-test (requires game assets)
```

`headless_match.py` accepts `--code DIR` to test another source tree. `calibrate.py` forwards
that option to each worker and can write per-match JSON with `--json output.json`.
