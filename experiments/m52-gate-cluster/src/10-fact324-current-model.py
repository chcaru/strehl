"""M52 step 10 - fact 324 re-derived under the CURRENT noise model, on all seven
stacks, by the independent Python merge.

Step 03 ran under `read_noise_e_high = 1.47`. Commit f95f6f4 (11:17 today)
changed it to 1.2392, which moves every ISO >= 400 stack. Step 03's five-stack
agreement with the shipped binary was established under the old value and stands
as a validation of the implementation; this re-runs under the new one and adds
`coffee-bubbles` and `foam`, which M38 never measured.

Loader check is unchanged: M4 section 8.1's dark temporal sigma is a direct
measurement off the files and does not depend on the noise model at all.

RULE 32: raw_image_visible is a VIEW - every read copies inside the `with`.
"""

import json
import pathlib
import sys
import time

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

FOCUS_NOISE_SD, WINDOW_RADIUS, REGULARISER_RADIUS, SIGMA_EPS = 0.015214, 13, 8, 1e-3
BLACK, GAIN_DIVISOR, BASE_ISO, SECOND_BASE_ISO = 512.0, 436.8, 100.0, 400.0
RN_LOW, RN_HIGH = 4.20, 1.2392          # <- profile.rs at HEAD
SQRT2 = float(np.sqrt(2.0))
GATES = [0.5, 1.0, 2.0, 4.0]

STACKS = [("119MSDCF", 50.0), ("109MSDCF", 160.0), ("113MSDCF", 500.0),
          ("112MSDCF", 500.0), ("coffee-bean", 50.0), ("coffee-bubbles", 1000.0),
          ("foam", 1000.0)]
# shipped binary at HEAD 4fb845c, mean n_eff at gate 2.0
BINARY = {"119MSDCF": 2.847, "109MSDCF": 2.891, "113MSDCF": 4.761, "112MSDCF": 6.190,
          "coffee-bean": 14.386, "coffee-bubbles": 2.109, "foam": 1.177}
DARK_TRUTH = {"118MSDCF": (100.0, {"R": 1.0048, "G1": 1.0042, "G2": 1.0105, "B": 0.9185}),
              "119MSDCF": (400.0, {"R": 1.2130, "G1": 1.2266, "G2": 1.2403, "B": 1.1146})}
_CC = {}


def counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


def clamped_box(a, r):
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    k = (a.shape, r)
    if k not in _CC:
        _CC[k] = counts(a.shape[0], r)[:, None] * counts(a.shape[1], r)[None, :]
    return s / _CC[k]


def sh(a, dy, dx):
    p = np.pad(a, 1, mode="edge")
    return p[1 + dy: 1 + dy + a.shape[0], 1 + dx: 1 + dx + a.shape[1]]


def planes(path):
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h, w = (v.shape[0] // 2) * 2, (v.shape[1] // 2) * 2
        return (np.array(v[0:h:2, 0:w:2], dtype=np.float64),
                np.array(v[0:h:2, 1:w:2], dtype=np.float64),
                np.array(v[1:h:2, 0:w:2], dtype=np.float64),
                np.array(v[1:h:2, 1:w:2], dtype=np.float64))


def field(path, iso):
    _, g1, g2, _ = planes(path)
    luma = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
    gx = (sh(luma, -1, 1) + 2 * sh(luma, 0, 1) + sh(luma, 1, 1)
          - sh(luma, -1, -1) - 2 * sh(luma, 0, -1) - sh(luma, 1, -1)) * 0.125
    gy = (sh(luma, 1, -1) + 2 * sh(luma, 1, 0) + sh(luma, 1, 1)
          - sh(luma, -1, -1) - 2 * sh(luma, -1, 0) - sh(luma, -1, 1)) * 0.125
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    sig = np.maximum(np.sqrt(0.5 * (g * luma + (rn * g) ** 2)), SIGMA_EPS)
    return clamped_box(clamped_box(np.hypot(gx, gy), WINDOW_RADIUS) / sig,
                       REGULARISER_RADIUS).astype(np.float32)


print("LOADER CHECK - M4 section 8.1 dark temporal sigma")
worst = 0.0
for folder, (iso, truth) in DARK_TRUTH.items():
    files = sorted(p for p in (pathlib.Path(r"D:\macro-dark-frames") / folder).iterdir()
                   if p.suffix.upper() == ".ARW")[2:]
    assert len(files) == 20
    cubes = {k: [] for k in ("R", "G1", "G2", "B")}
    for p in files:
        for k, v in zip(("R", "G1", "G2", "B"), planes(str(p))):
            cubes[k].append(v)
    row = {k: float(np.sqrt(np.stack(cubes[k]).var(axis=0, ddof=1).mean()))
           for k in cubes}
    worst = max(worst, max(abs(row[k] / truth[k] - 1) for k in row))
    print(f"  {folder} ISO {iso:.0f}: " + " ".join(
        f"{k} {row[k]:.4f}({row[k] / truth[k] - 1:+.2%})" for k in ("R", "G1", "G2", "B")))
print(f"  worst deviation {worst:.3%}")
if worst > 0.01:
    sys.exit("LOADER CHECK FAILED")
print("  LOADER OK\n")

out = {}
print(f"{'stack':<16}{'N':>4}{'ISO':>6}" + "".join(f"{'g' + str(g):>9}" for g in GATES)
      + f"{'binary g2':>11}{'dev':>9}{'n_eff/N':>9}")
for name, iso in STACKS:
    files = sorted(str(p) for p in (pathlib.Path(r"D:\personal\macro") / name).iterdir()
                   if p.suffix.upper() == ".ARW")
    t0 = time.time()
    best = None
    cube = None
    for i, p in enumerate(files):
        f = field(p, iso)
        if cube is None:
            cube = np.empty((len(files),) + f.shape, dtype=np.float32)
        cube[i] = f
    best = cube.max(axis=0)
    row = {}
    for t in GATES:
        tol = np.float32(t * SQRT2 * FOCUS_NOISE_SD)
        n = np.zeros(best.shape, dtype=np.uint16)
        for k in range(cube.shape[0]):
            n += best - cube[k] <= tol
        row[t] = float(n.mean())
    dev = row[2.0] / BINARY[name] - 1
    out[name] = {"iso": iso, "N": len(files), "gates": row,
                 "binary_g2": BINARY[name], "dev_vs_binary": dev,
                 "n_eff_over_N_at_2": row[2.0] / len(files)}
    print(f"{name:<16}{len(files):>4}{iso:>6.0f}" + "".join(f"{row[g]:>9.3f}" for g in GATES)
          + f"{BINARY[name]:>11.3f}{dev:>+9.2%}{row[2.0] / len(files):>9.4f}"
          + f"  [{time.time() - t0:.0f}s]", flush=True)
    del cube, best

v = [o["gates"][2.0] for o in out.values()]
r = [o["n_eff_over_N_at_2"] for o in out.values()]
print(f"\nseven-stack spread at gate 2.0: {min(v):.3f}..{max(v):.3f} = {max(v) / min(v):.2f}x"
      f"   (fact 324 claims 3.3x over five)")
five = [out[k]["gates"][2.0] for k in
        ("119MSDCF", "109MSDCF", "113MSDCF", "112MSDCF", "coffee-bean")]
print(f"M38's own five stacks:          {min(five):.3f}..{max(five):.3f} = "
      f"{max(five) / min(five):.2f}x")
print(f"n_eff/N at gate 2.0: {', '.join(f'{x:.4f}' for x in r)}  "
      f"-> range {max(r) / min(r):.1f}x  (fact 324 claims a cluster at 0.068-0.079)")
print(f"worst |deviation| from the shipped binary: {max(abs(o['dev_vs_binary']) for o in out.values()):.2%}")

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "10-fact324-current-model.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
