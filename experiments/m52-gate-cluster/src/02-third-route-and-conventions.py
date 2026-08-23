"""M52 step 2 - a THIRD route to the same constant, and what `k` is a property of.

Three parts.

A. AUTOCOVARIANCE CONTRACTION. Route 1 (step 01) filters the operator output and
   takes an SD. This route never filters it: it estimates the operator output's
   own autocovariance C(d) by FFT and contracts it with the analytic
   autocorrelation R(d) of the composed box27 (x) box17 kernel:

       Var(K * f) = sum_d R_K(d) C_f(d)

   A bug in the box filter cannot survive both routes, because this one uses no
   box filter at all - only the kernel's algebraic autocorrelation.

B. CONVENTION SENSITIVITY of fact 439. `k` is the SD of the operator response,
   so it is NOT invariant to the operator's arbitrary output scale. The shipped
   Sobel carries a 1/8 that focus.rs calls "cosmetic". If the same courtesy is
   extended to the Laplacian family, does the 10.4x span survive? Pre-registered
   expectation: it does not - the span is partly a statement about normalisation
   conventions, not only about operator shape. This is a rule-20 adversarial
   input for fact 439.

C. PAIRED separability for fact 510. Step 01 took ratios of seed-averaged SDs.
   Here the ratio is formed per seed and then averaged, which cancels the common
   noise plane exactly and is the estimator fact 510 needed to decide its own
   pre-registered non-separability prediction.
"""

import json
import pathlib

import numpy as np

FOCUS_NOISE_SD = 0.015214
WINDOW_RADIUS = 13
REGULARISER_RADIUS = 8
SIDE = 2048
SEEDS = 8
SEED_BASE = 52_000_017

import importlib.util
spec = importlib.util.spec_from_file_location(
    "m52a", pathlib.Path(__file__).with_name("01-operator-noise-independent.py"))
# Do not exec step 01 (it prints and measures). Re-declare the primitives here
# instead, which also means step 02 is a second chance to get them wrong.


def box_mean(a, r):
    if r == 0:
        return np.asarray(a, dtype=np.float64).copy()
    x = np.asarray(a, dtype=np.float64)
    n = 2 * r + 1
    for axis in (0, 1):
        padw = [(0, 0), (0, 0)]
        padw[axis] = (r, r)
        p = np.pad(x, padw, mode="edge")
        acc = np.zeros_like(x)
        for k in range(n):
            sl = [slice(None), slice(None)]
            sl[axis] = slice(k, k + x.shape[axis])
            acc += p[tuple(sl)]
        x = acc / n
    return x


def sh(a, dy, dx):
    p = np.pad(a, ((1, 1), (1, 1)), mode="edge")
    return p[1 + dy : 1 + dy + a.shape[0], 1 + dx : 1 + dx + a.shape[1]]


def sobel_xy(a):
    gx = (sh(a, -1, 1) + 2.0 * sh(a, 0, 1) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2.0 * sh(a, 0, -1) - sh(a, 1, -1)) * 0.125
    gy = (sh(a, 1, -1) + 2.0 * sh(a, 1, 0) + sh(a, 1, 1)
          - sh(a, -1, -1) - 2.0 * sh(a, -1, 0) - sh(a, -1, 1)) * 0.125
    return gx, gy


def op_tenengrad(a):
    gx, gy = sobel_xy(a)
    return np.hypot(gx, gy)


def op_tenengrad_sq(a):
    gx, gy = sobel_xy(a)
    return gx * gx + gy * gy


def op_brenner(a):
    p = np.pad(a, ((0, 0), (0, 2)), mode="edge")
    return np.abs(p[:, 2 : 2 + a.shape[1]] - a)


def op_laplacian(a):
    return np.abs(4.0 * a - sh(a, 0, 1) - sh(a, 0, -1) - sh(a, 1, 0) - sh(a, -1, 0))


def op_sml(a):
    return (np.abs(2.0 * a - sh(a, 0, 1) - sh(a, 0, -1))
            + np.abs(2.0 * a - sh(a, 1, 0) - sh(a, -1, 0)))


def op_ring13(a):
    return np.abs(box_mean(a, 1) - box_mean(a, 3))


def op_local_variance(a):
    m = box_mean(a, 1)
    return box_mean(a * a, 1) - m * m


def plane(seed, side=SIDE):
    return np.random.Generator(np.random.Philox(seed)).standard_normal((side, side))


out = {}

# ----------------------------------------------------------------- part A
print("=" * 78)
print("A. AUTOCOVARIANCE CONTRACTION - a route that never applies a box filter")
print("=" * 78)

# Analytic autocorrelation of the composed kernel, built by polynomial
# convolution of 1-D uniform kernels. Separable, so R is an outer product.
def kernel_1d():
    b27 = np.ones(2 * WINDOW_RADIUS + 1) / (2 * WINDOW_RADIUS + 1)
    b17 = np.ones(2 * REGULARISER_RADIUS + 1) / (2 * REGULARISER_RADIUS + 1)
    return np.convolve(b27, b17)


k1 = kernel_1d()
r1 = np.correlate(k1, k1, mode="full")   # 1-D kernel autocorrelation
R = np.outer(r1, r1)                     # separable, so the 2-D one is the outer product
half = (len(r1) - 1) // 2
print(f"  composed kernel is {len(k1)} taps; R is {R.shape[0]}x{R.shape[1]},"
      f" sum(R) = {R.sum():.8f} (must be 1.0 -- kernel is normalised)")

rows_a = []
for name, op in [("tenengrad |grad| (shipped)", op_tenengrad),
                 ("sum-modified-laplacian", op_sml),
                 ("ring(1,3)", op_ring13)]:
    est = []
    for s in range(4):
        f = op(plane(SEED_BASE + 1000 * s, 1024))
        f = f[8:-8, 8:-8]                       # drop the operator's own border
        f = f - f.mean()
        F = np.fft.rfft2(f)
        ac = np.fft.irfft2(F * np.conj(F), s=f.shape) / f.size   # circular autocov
        # gather C(d) for |dy|,|dx| <= half
        idx = np.concatenate([np.arange(0, half + 1), np.arange(-half, 0)])
        C = ac[np.ix_(idx, idx)]
        C = np.roll(np.roll(C, half, axis=0), half, axis=1)
        est.append(float(np.sqrt((R * C).sum())))
    m = float(np.mean(est))
    rows_a.append({"operator": name, "sd_autocov": m})
    print(f"  {name:<30} SD via contraction = {m:.6f}")
out["autocovariance_route"] = rows_a
print("  (compare step 01's filtering route: 0.015318 / 0.101496 / 0.009835)\n")

# ----------------------------------------------------------------- part B
print("=" * 78)
print("B. CONVENTION SENSITIVITY - is fact 439's 10.4x a property of the")
print("   operators, or of the scale factors the survey happened to write down?")
print("=" * 78)


def measure(op, radius=WINDOW_RADIUS, seeds=SEEDS):
    v = []
    for s in range(seeds):
        f = box_mean(box_mean(op(plane(SEED_BASE + 1000 * s)), radius),
                     REGULARISER_RADIUS)
        m = radius + 2 + REGULARISER_RADIUS
        v.append(float(np.std(f[m:-m, m:-m], ddof=1)))
    return float(np.mean(v))


# Each of these is the SAME operator as a survey row, differing only by the
# kind of constant focus.rs calls "cosmetic" on the Sobel.
VARIANTS = [
    ("laplacian, 1/8 like the Sobel", lambda a: op_laplacian(a) / 8.0),
    ("laplacian / 4 (mean of the 4 diffs)", lambda a: op_laplacian(a) / 4.0),
    ("SML / 2 (mean of the two axes)", lambda a: op_sml(a) / 2.0),
    ("SML / 8 like the Sobel", lambda a: op_sml(a) / 8.0),
    ("brenner / 2 (per-px difference)", lambda a: op_brenner(a) / 2.0),
    ("local variance -> its sqrt (an SD)", lambda a: np.sqrt(np.maximum(op_local_variance(a), 0.0))),
    ("ring(1,3) x 2", lambda a: 2.0 * op_ring13(a)),
]
base_rows = {"ring(1,3)": 0.646, "tenengrad": 1.007, "tenengrad-sq": 1.367,
             "brenner": 1.971, "local variance": 2.479, "laplacian": 6.589,
             "SML": 6.671}
print("  step 01 survey k, unchanged:", ", ".join(f"{k}={v}" for k, v in base_rows.items()))
print()
rows_b = []
for name, op in VARIANTS:
    sd = measure(op)
    rows_b.append({"variant": name, "sd": sd, "k": sd / FOCUS_NOISE_SD})
    print(f"  {name:<38}{sd:>12.6f}   k = {sd / FOCUS_NOISE_SD:.3f}")
out["convention_variants"] = rows_b

# A defensible alternative convention set: every operator divided by the L1 norm
# of its own linear stencil where it has one, so a unit-step edge gives a
# comparable response. Report the span it produces.
alt = {
    "ring(1,3)": 0.646,
    "tenengrad": 1.007,
    "tenengrad-sq": 1.367,
    "brenner": [r for r in rows_b if r["variant"].startswith("brenner")][0]["k"],
    "local variance(sqrt)": [r for r in rows_b if r["variant"].startswith("local")][0]["k"],
    "laplacian/8": [r for r in rows_b if r["variant"].startswith("laplacian, 1/8")][0]["k"],
    "SML/8": [r for r in rows_b if r["variant"].startswith("SML / 8")][0]["k"],
}
vals = list(alt.values())
print()
print("  An equally defensible convention set (Sobel-style 1/8 on the Laplacian")
print("  family, per-pixel difference for Brenner, SD rather than variance):")
for kk, vv in alt.items():
    print(f"    {kk:<24}k = {vv:.3f}")
print(f"\n  span under that convention = {max(vals) / min(vals):.2f}x"
      f"   (fact 439 reports 10.4x)")
out["alternative_convention_span"] = {"k": alt, "span": max(vals) / min(vals)}

# ----------------------------------------------------------------- part C
print()
print("=" * 78)
print("C. PAIRED SEPARABILITY for fact 510 - ratio formed per seed, then averaged")
print("=" * 78)


def per_seed(op, radius):
    v = []
    for s in range(SEEDS):
        f = box_mean(box_mean(op(plane(SEED_BASE + 1000 * s)), radius),
                     REGULARISER_RADIUS)
        m = radius + 2 + REGULARISER_RADIUS
        v.append(float(np.std(f[m:-m, m:-m], ddof=1)))
    return np.array(v)


s_ship = per_seed(op_tenengrad, 13)
s_rad = per_seed(op_tenengrad, 11)
s_op = per_seed(op_tenengrad_sq, 13)
s_joint = per_seed(op_tenengrad_sq, 11)
kr = s_rad / s_ship
ko = s_op / s_ship
kj = s_joint / s_ship
resid = kr * ko / kj - 1.0
print(f"  radius alone    k = {kr.mean():.5f} +/- {kr.std(ddof=1) / np.sqrt(SEEDS):.5f}"
      f"   (fact 510: 1.125)")
print(f"  operator alone  k = {ko.mean():.5f} +/- {ko.std(ddof=1) / np.sqrt(SEEDS):.5f}"
      f"   (fact 510: 1.364)")
print(f"  joint           k = {kj.mean():.5f} +/- {kj.std(ddof=1) / np.sqrt(SEEDS):.5f}"
      f"   (fact 510: 1.528)")
print(f"  product/joint - 1 = {resid.mean():+.5%} +/- {resid.std(ddof=1) / np.sqrt(SEEDS):.5%}"
      f"   (fact 510: +0.47%, declared NOT DECIDED)")
out["fact510_paired"] = {
    "radius_alone": float(kr.mean()), "operator_alone": float(ko.mean()),
    "joint": float(kj.mean()), "residual": float(resid.mean()),
    "residual_sem": float(resid.std(ddof=1) / np.sqrt(SEEDS)),
    "per_seed_residual": [float(x) for x in resid],
}

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "02-routes-and-conventions.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
