"""M52 step 3 - fact 324 re-derived from the RAW files by an independent merge.

This does NOT run `strehl merge`. It is a second implementation, in Python, of
pass one and pass two's admission rule, written from `merge.rs`, `focus.rs`,
`plane.rs` and `boxfilter.rs` semantics:

    luma   = 0.5 * (max(G1-black,0) + max(G2-black,0))          plane.rs
    grad   = 0.125 * hypot(Sobel_x, Sobel_y), replicate border   focus.rs
    focus  = clamped_box(grad, 13) / green_luma_sigma(luma)      focus.rs + noise.rs
    reg    = clamped_box(focus, 8)                               merge.rs
    best   = max over frames                                     merge.rs FocusStats
    n_eff  = #{k : best - reg_k <= t * sqrt(2) * FOCUS_NOISE_SD} merge.rs Estimator

Border policy matches `boxfilter.rs`: the window is intersected with the plane
and divided by the surviving count, NOT replicate-padded. The box itself is
scipy's uniform_filter in constant mode divided by the analytic count map --
a third implementation, agreeing with a naive per-pixel gather to 8e-16.

RULE 32: `raw_image_visible` is a VIEW. Every read copies inside the `with`.

LOADER CHECK (mandatory): reproduces M4 section 8.1's dark temporal sigma at two
ISOs before any stack is touched. If that misses, nothing else is printed.
"""

import json
import os
import pathlib
import sys
import time

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

FOCUS_NOISE_SD = 0.015214
WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SIGMA_EPS = 1e-3
BLACK = 512.0
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
SECOND_BASE_ISO = 400.0
RN_LOW = 4.20
RN_HIGH = 1.47
SQRT2 = float(np.sqrt(2.0))

GATES = [0.5, 1.0, 2.0, 4.0]

STACKS = [
    ("119MSDCF", r"D:\personal\macro\119MSDCF", 50.0),
    ("109MSDCF", r"D:\personal\macro\109MSDCF", 160.0),
    ("113MSDCF", r"D:\personal\macro\113MSDCF", 500.0),
    ("112MSDCF", r"D:\personal\macro\112MSDCF", 500.0),
    ("coffee-bean", r"D:\personal\macro\coffee-bean", 50.0),
]

# M4 section 1 folder -> ISO, and section 8.1's published temporal sigma.
DARK_TRUTH = {
    "118MSDCF": (100.0, {"R": 1.0048, "G1": 1.0042, "G2": 1.0105, "B": 0.9185}),
    "119MSDCF": (400.0, {"R": 1.2130, "G1": 1.2266, "G2": 1.2403, "B": 1.1146}),
}


def counts(n, r):
    i = np.arange(n)
    return (np.minimum(i + r, n - 1) - np.maximum(i - r, 0) + 1).astype(np.float64)


_COUNT_CACHE = {}


def clamped_box(a, r):
    """Mean over a (2r+1)^2 window intersected with the plane -- boxfilter.rs."""
    n = 2 * r + 1
    s = uniform_filter(a, size=n, mode="constant", cval=0.0) * float(n * n)
    key = (a.shape, r)
    d = _COUNT_CACHE.get(key)
    if d is None:
        d = counts(a.shape[0], r)[:, None] * counts(a.shape[1], r)[None, :]
        _COUNT_CACHE[key] = d
    return s / d


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")

    def at(dy, dx):
        return p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]

    gx = at(-1, 1) + 2.0 * at(0, 1) + at(1, 1) - at(-1, -1) - 2.0 * at(0, -1) - at(1, -1)
    gy = at(1, -1) + 2.0 * at(1, 0) + at(1, 1) - at(-1, -1) - 2.0 * at(-1, 0) - at(-1, 1)
    return np.hypot(0.125 * gx, 0.125 * gy)


def green_luma_sigma(luma, iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    read_dn = rn * g
    var = g * np.maximum(luma, 0.0) + read_dn * read_dn
    return np.sqrt(0.25 * (var + var))


def read_planes(path):
    """R, G1, G2, B as f64, black NOT subtracted. Copies inside the `with`."""
    with rawpy.imread(path) as rr:
        v = rr.raw_image_visible
        h = (v.shape[0] // 2) * 2
        w = (v.shape[1] // 2) * 2
        r = np.array(v[0:h:2, 0:w:2], dtype=np.float64)
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
        b = np.array(v[1:h:2, 1:w:2], dtype=np.float64)
    return r, g1, g2, b


def luma_of(path):
    _, g1, g2, _ = read_planes(path)
    return 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))


def regularised_field(path, iso):
    luma = luma_of(path)
    f = clamped_box(sobel_mag(luma), WINDOW_RADIUS)
    f /= np.maximum(green_luma_sigma(luma, iso), SIGMA_EPS)
    return clamped_box(f, REGULARISER_RADIUS).astype(np.float32)


# ------------------------------------------------------------ loader check
print("=" * 78)
print("LOADER CHECK - reproduce M4 section 8.1 dark temporal sigma (rule: prove the loader)")
print("=" * 78)
worst = 0.0
loader = {}
for folder, (iso, truth) in DARK_TRUTH.items():
    d = pathlib.Path(r"D:\macro-dark-frames") / folder
    files = sorted(p for p in d.iterdir() if p.suffix.upper() == ".ARW")[2:]
    assert len(files) == 20, f"{folder}: expected 20 usable darks, got {len(files)}"
    acc = {k: [] for k in ("R", "G1", "G2", "B")}
    for p in files:
        r, g1, g2, b = read_planes(str(p))
        for k, v in zip(("R", "G1", "G2", "B"), (r, g1, g2, b)):
            acc[k].append(v)
    row = {}
    for k in ("R", "G1", "G2", "B"):
        cube = np.stack(acc[k])                    # (20, H, W)
        var = cube.var(axis=0, ddof=1)             # per-pixel temporal variance
        row[k] = float(np.sqrt(var.mean()))        # pooled RMS temporal sigma
        worst = max(worst, abs(row[k] / truth[k] - 1.0))
    loader[folder] = {"iso": iso, "mine": row, "m4": truth}
    print(f"  {folder} ISO {iso:.0f}: " + "  ".join(
        f"{k} {row[k]:.4f} (M4 {truth[k]:.4f}, {row[k] / truth[k] - 1:+.2%})"
        for k in ("R", "G1", "G2", "B")))
print(f"\n  worst deviation from M4 section 8.1: {worst:.2%}")
if worst > 0.01:
    print("  LOADER CHECK FAILED - refusing to report anything else.")
    sys.exit(1)
print("  LOADER OK.\n")

# ------------------------------------------------------------ fact 324
print("=" * 78)
print("FACT 324 - mean n_eff per stack, independently computed")
print("=" * 78)
out = {"loader": loader, "gates": GATES, "stacks": {}}
for name, d, iso in STACKS:
    files = sorted(str(p) for p in pathlib.Path(d).iterdir() if p.suffix.upper() == ".ARW")
    t0 = time.time()
    fields = []
    for p in files:
        fields.append(regularised_field(p, iso))
    cube = np.stack(fields)                       # (N, H, W) float32
    del fields
    best = cube.max(axis=0)
    res = {}
    for t in GATES:
        tol = np.float32(t) * np.float32(SQRT2) * np.float32(FOCUS_NOISE_SD)
        n = np.zeros(best.shape, dtype=np.uint16)
        for k in range(cube.shape[0]):
            n += (best - cube[k] <= tol)
        res[t] = {"mean_n_eff": float(n.mean()),
                  "frac_n1": float((n == 1).mean()),
                  "n_eff_over_N": float(n.mean()) / len(files)}
    # gate needed for mean n_eff = 3, by log-log interpolation on the ladder
    lad = [(t, res[t]["mean_n_eff"]) for t in GATES]
    solved = None
    for (g0, n0), (g1, n1) in zip(lad, lad[1:]):
        if n0 <= 3.0 <= n1:
            f = (np.log(3.0) - np.log(n0)) / (np.log(n1) - np.log(n0))
            solved = float(np.exp(np.log(g0) + f * (np.log(g1) - np.log(g0))))
            break
    out["stacks"][name] = {"dir": d, "iso": iso, "frames": len(files),
                           "shape": list(best.shape), "gates": res,
                           "gate_for_n_eff_3": solved,
                           "seconds": time.time() - t0}
    print(f"  {name:<12} N={len(files):>3} ISO {iso:>5.0f}  " +
          "  ".join(f"g{t}={res[t]['mean_n_eff']:.3f}" for t in GATES) +
          f"   n_eff/N@2.0={res[2.0]['n_eff_over_N']:.3f}"
          f"   gate(n_eff=3)={solved if solved is None else round(solved, 4)}"
          f"   [{time.time() - t0:.0f}s]")
    del cube, best

ne2 = [v["gates"][2.0]["mean_n_eff"] for v in out["stacks"].values()]
print(f"\n  spread at gate 2.0 = {max(ne2) / min(ne2):.2f}x   (fact 324 says 3.3x)")
ratios = [v["gates"][2.0]["n_eff_over_N"] for k, v in out["stacks"].items() if k != "109MSDCF"]
print(f"  n_eff/N for the four non-109 stacks: "
      f"{', '.join(f'{r:.3f}' for r in ratios)}   (fact 324 says 0.068-0.079)")
solves = [v["gate_for_n_eff_3"] for v in out["stacks"].values() if v["gate_for_n_eff_3"]]
print(f"  gates for n_eff = 3: {', '.join(f'{s:.2f}' for s in solves)}   "
      f"(fact 324 says 1.1 to 2.9)")

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "03-fact324-n-eff.json"
p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {p}")
