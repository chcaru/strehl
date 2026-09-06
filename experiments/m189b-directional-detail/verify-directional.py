"""Root verification: change orientation, frequencies, filter and noise draws.

Pre-run falsifiers: a common diagonal three-tap filter must not raise a
generally LSI-safe score by >1%; identity must hold; genuine optical narrowing
must raise it; a flat region must not score detail. This is synthetic operator
verification, not external validation of the shared noise calibration.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "M189-noise-colour-detail" / "metric_v2.py"
sys.path.insert(0, str(SOURCE.parent))
from metric_v2 import measure

N, PAIRS, BATCHES = 256, 16, 4
GAIN, READ = 0.221113, 1.2392
yy, xx = np.mgrid[:N, :N]

def scene(sigma):
    value = np.full((N, N), 8000.0)
    for k, phase in ((47, .7), (49, 1.9), (51, 2.8)):
        attenuation = np.exp(-2 * np.pi**2 * sigma**2 * 2 * (k / N)**2)
        value += 600 * attenuation * np.cos(2 * np.pi * k * (xx + yy) / N + phase)
    return value

def sharpen(value, perpendicular=False):
    direction = (1, -1) if perpendicular else (1, 1)
    neighbor = np.roll(value, direction, axis=(-2, -1))
    neighbor += np.roll(value, tuple(-v for v in direction), axis=(-2, -1))
    return 1.4 * value - .2 * neighbor

def score(pair):
    return measure(*pair, gain_dn_per_e=GAIN, read_noise_e=READ).score

def observe(value, noise):
    sigma = np.sqrt(GAIN * value + (GAIN * READ)**2)
    return tuple(value + sigma * v for v in noise)

def summary(values):
    values = np.asarray(values)
    return {"values": values.tolist(), "mean": float(values.mean()),
            "sem": float(values.std(ddof=1) / np.sqrt(len(values)))}

source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
noise = [tuple(np.random.default_rng(193900 + 2 * j + k).normal(size=(PAIRS, N, N))
               for k in (0, 1)) for j in range(BATCHES)]
# Flat control is executed before any scene score.
flat = [score(observe(np.full((N, N), 8000.0), n)) for n in noise]
flat_summary = summary(flat)
assert abs(flat_summary["mean"]) + 3 * flat_summary["sem"] < 100
flat_pair = observe(np.full((N, N), 8000.0), noise[0])
assert score((flat_pair[0], flat_pair[0])) > 100
ratios = {"diagonal_sharpen": [], "perpendicular_placebo": [], "optical_improved": [], "identity": []}
for n in noise:
    base = observe(scene(.85), n)
    baseline = score(base)
    ratios["diagonal_sharpen"].append(score(tuple(sharpen(v) for v in base)) / baseline)
    ratios["perpendicular_placebo"].append(score(tuple(sharpen(v, True) for v in base)) / baseline)
    ratios["optical_improved"].append(score(observe(scene(.45), n)) / baseline)
    ratios["identity"].append(score(tuple(v.copy() for v in base)) / baseline)
result = {"scope": "independent synthetic re-choice; no capture or scorecard admission",
          "command": "python -B experiments/m189b-directional-detail/verify-directional.py",
          "metric_sha256": source_hash, "flat_first": flat_summary,
          "ratios": {key: summary(value) for key, value in ratios.items()}}
for key in ("diagonal_sharpen", "optical_improved"):
    s = result["ratios"][key]
    assert s["mean"] - 3 * s["sem"] > 1.01
assert all(v == 1.0 for v in ratios["identity"])
s = result["ratios"]["perpendicular_placebo"]
assert s["mean"] + 3 * s["sem"] < 1.0
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
result["verdict"] = "VERIFIED_DIRECTIONAL_LIMITATION"
(HERE / "out" / "independent-verification.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
