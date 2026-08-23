"""M52 step 8 - what the sigma=1 calibration costs at REAL signal levels.

crates/strehl-plugin/src/calibrate.rs:309 calibrates every operator with
`unit_sigma_model()`, i.e. on a plane whose green_luma_sigma is 1 DN. Step 07
showed that is sound for a degree-1 homogeneous operator and exactly wrong,
by a factor of sigma, for a degree-2 one. Two of fact 439's seven operators are
degree 2, and one of them - tenengrad-squared - is the operator in the pending
M17+M42 edit that fact 509 prices at k = 1.528.

This measures the size of that on real signal levels, two ways:

  (i)  the actual distribution of green_luma_sigma on one frame of every stack;
  (ii) a synthetic flat field carrying the SENSOR's own noise at signal level S,
       pushed through the shipped normalisation, for the degree-1 shipped
       operator and the degree-2 pending one.

Negative control: the degree-1 rows must be flat across the whole S sweep. If
they are not, the instrument is wrong and the degree-2 rows mean nothing.

RULE 32: raw_image_visible is a VIEW - every read copies inside the `with`.
"""

import json
import pathlib

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

BLACK = 512.0
GAIN_DIVISOR, BASE_ISO, SECOND_BASE_ISO = 436.8, 100.0, 400.0
RN_LOW, RN_HIGH = 4.20, 1.47
SIGMA_EPS = 1e-3
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


def sobel(a):
    gx = (sh(a, -1, 1) + 2 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return gx, gy


def gain_read(iso):
    g = max(iso, BASE_ISO) / GAIN_DIVISOR
    rn = RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW
    return g, rn * g


STACKS = [("119MSDCF", 50.0), ("109MSDCF", 160.0), ("113MSDCF", 500.0),
          ("112MSDCF", 500.0), ("coffee-bean", 50.0), ("coffee-bubbles", 1000.0),
          ("foam", 1000.0)]

print("(i) green_luma_sigma on one real frame per stack (DN)")
print(f"{'stack':<16}{'ISO':>6}{'p10':>9}{'median':>9}{'p90':>9}{'mean':>9}")
sig = {}
for name, iso in STACKS:
    d = pathlib.Path(r"D:\personal\macro") / name
    f = sorted(p for p in d.iterdir() if p.suffix.upper() == ".ARW")[len(list(d.glob('*.ARW'))) // 2]
    with rawpy.imread(str(f)) as rr:
        v = rr.raw_image_visible
        h, w = (v.shape[0] // 2) * 2, (v.shape[1] // 2) * 2
        g1 = np.array(v[0:h:2, 1:w:2], dtype=np.float64)
        g2 = np.array(v[1:h:2, 0:w:2], dtype=np.float64)
    luma = 0.5 * (np.maximum(g1 - BLACK, 0.0) + np.maximum(g2 - BLACK, 0.0))
    g, rd = gain_read(iso)
    s = np.sqrt(0.5 * (g * luma + rd * rd))
    q = np.percentile(s, [10, 50, 90])
    sig[name] = {"iso": iso, "p10": q[0], "median": q[1], "p90": q[2], "mean": float(s.mean())}
    print(f"{name:<16}{iso:>6.0f}{q[0]:>9.2f}{q[1]:>9.2f}{q[2]:>9.2f}{s.mean():>9.2f}")

print("\n(ii) field noise SD at real signal levels, ISO 160 sensor model")
print("     degree-1 = |grad| w13 (SHIPPED). degree-2 = |grad|^2 w11 (PENDING M17+M42).")
print(f"{'signal S (DN)':>14}{'sigma (DN)':>12}{'|grad| w13':>14}{'ratio':>9}"
      f"{'|grad|^2 w11':>15}{'ratio':>9}")
rng = np.random.Generator(np.random.Philox(52080823))
g, rd = gain_read(160.0)
rows = []
base_shape = (1400, 1400)
z1 = rng.standard_normal(base_shape)
z2 = rng.standard_normal(base_shape)
ref = {}
for S in (0.0, 10.0, 100.0, 500.0, 2000.0, 8000.0, 14000.0):
    sd_dn = np.sqrt(g * S + rd * rd)
    luma = S + 0.5 * sd_dn * (z1 + z2)
    sm = max(np.sqrt(0.5 * (g * max(S, 0.0) + rd * rd)), SIGMA_EPS)
    gx, gy = sobel(luma)
    f1 = clamped_box(clamped_box(np.hypot(gx, gy), 13) / sm, 8)
    f2 = clamped_box(clamped_box(gx * gx + gy * gy, 11) / sm, 8)
    m = 96
    v1 = float(f1[m:-m, m:-m].std(ddof=1))
    v2 = float(f2[m:-m, m:-m].std(ddof=1))
    if not ref:
        ref = {"d1": v1, "d2": v2}
    rows.append({"S": S, "sigma": sm, "d1": v1, "d2": v2,
                 "r1": v1 / ref["d1"], "r2": v2 / ref["d2"]})
    print(f"{S:>14.0f}{sm:>12.3f}{v1:>14.6f}{v1 / ref['d1']:>9.3f}"
          f"{v2:>15.6f}{v2 / ref['d2']:>9.3f}")

r1 = [r["r1"] for r in rows]
print(f"\nNEGATIVE CONTROL, degree-1 across the sweep: {min(r1):.4f}..{max(r1):.4f} "
      f"({max(r1) / min(r1):.4f}x) - must be ~1.000")
med = sig["109MSDCF"]["median"]
print(f"degree-2 grows exactly as sigma: at 109MSDCF's median sigma = {med:.2f} DN the "
      f"pending operator's true constant is ~{med:.1f}x the sigma=1 calibration,")
print(f"so fact 509's k = 1.528 understates the real gate shift by about that factor,")
print(f"and the shift is not a single number - it varies pixel to pixel with S.")

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "08-real-sigma-cost.json"
p.write_text(json.dumps({"sigma_per_stack": sig, "sweep": rows}, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
