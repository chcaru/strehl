"""M52 step 7 - probe D redone EXACTLY.

Step 6's sigma sweep drew a fresh noise realisation per sigma, so sampling noise
(a few percent on one 1024^2 plane) was mixed into the homogeneity signal and
SML read 1.068x when theory says exactly 1.000x. Here the SAME realisation is
scaled: x_sigma = sigma * x_1. A degree-1 homogeneous operator must then give a
bit-for-bit identical normalised field, so any departure from 1.000 is real.

This is the placebo design rule 11 asks for: the degree-1 rows are the negative
control and MUST read 1.000000.
"""

import json
import pathlib

import numpy as np
from scipy.ndimage import uniform_filter

WINDOW_RADIUS, REGULARISER_RADIUS = 13, 8
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


def _sobel(a):
    gx = (sh(a, -1, 1) + 2 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return gx, gy


OPS = {
    "ring(1,3)": lambda a: np.abs(clamped_box(a, 1) - clamped_box(a, 3)),
    "tenengrad |grad| (SHIPPED)": lambda a: np.hypot(*_sobel(a)),
    "tenengrad-squared": lambda a: (lambda g: g[0] ** 2 + g[1] ** 2)(_sobel(a)),
    "brenner": lambda a: np.abs(
        np.pad(a, ((0, 0), (0, 2)), mode="edge")[:, 2:2 + a.shape[1]] - a),
    "local variance (3x3)": lambda a: clamped_box(a * a, 1) - clamped_box(a, 1) ** 2,
    "laplacian |4I-N4|": lambda a: np.abs(
        4 * a - sh(a, 0, 1) - sh(a, 0, -1) - sh(a, 1, 0) - sh(a, -1, 0)),
    "sum-modified-laplacian": lambda a: (
        np.abs(2 * a - sh(a, 0, 1) - sh(a, 0, -1))
        + np.abs(2 * a - sh(a, 1, 0) - sh(a, -1, 0))),
}

SIGMAS = [1.0, 4.0, 16.0, 64.0]
rng = np.random.Generator(np.random.Philox(52070823))
base = rng.normal(0.0, 1.0, size=(1536, 1536))
m = 96
print("Same realisation scaled by sigma. Normalised field = reg8(box13(op(x))/sigma).")
print("Degree-1 operators are the negative control and must read exactly 1.000000x.\n")
print(f"{'operator':<28}" + "".join(f"{'sd@s=' + str(int(s)):>14}" for s in SIGMAS)
      + f"{'ratio 64/1':>13}")
out = {}
for name, fn in OPS.items():
    vals = []
    for sg in SIGMAS:
        f = clamped_box(clamped_box(fn(sg * base), WINDOW_RADIUS) / sg, REGULARISER_RADIUS)
        vals.append(float(f[m:-m, m:-m].std(ddof=1)))
    out[name] = {"sigmas": SIGMAS, "sd": vals, "ratio": vals[-1] / vals[0]}
    print(f"{name:<28}" + "".join(f"{v:14.6f}" for v in vals)
          + f"{vals[-1] / vals[0]:12.4f}x")

flat = [v["ratio"] for k, v in out.items()
        if k not in ("tenengrad-squared", "local variance (3x3)")]
quad = [v["ratio"] for k, v in out.items()
        if k in ("tenengrad-squared", "local variance (3x3)")]
print(f"\nnegative control (5 degree-1 operators): ratios "
      f"{', '.join(f'{r:.6f}' for r in flat)}  -> max |dev| {max(abs(r - 1) for r in flat):.2e}")
print(f"degree-2 operators: ratios {', '.join(f'{r:.4f}' for r in quad)}  "
      f"(sigma sweep is 64x; predicted 64.0000x)")

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "07-homogeneity-exact.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
