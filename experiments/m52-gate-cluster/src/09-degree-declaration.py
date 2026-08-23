"""M52 step 9 - the one declaration the calibration seam still contains, and
why measuring on a sigma=1 plane cannot check it.

`crates/strehl-plugin/src/measure.rs` opens by saying the design removed every
declared number: "There is no `fn noise_sd(&self) -> f32` ... a declaration can
be wrong; a measurement cannot be wrong in the same way. Fault 5 of section
F4.6 becomes unrepresentable."

One declaration survives: `Normalisation::LumaSigma { degree }` (measure.rs:123),
which decides whether the response is divided by sigma or sigma^2.
`calibrate.rs:309` measures every operator's constant on `unit_sigma_model()` -
a plane whose green_luma_sigma is 1 DN. At sigma = 1, sigma^1 == sigma^2 == 1.

Pre-registered prediction (direction fixed before running):
  1. the calibrated constant is IDENTICAL under degree 1 and degree 2, to
     within floating point, for every operator;
  2. on a realistic-sigma plane the two fields differ by exactly sigma^(d-1);
  3. the negative control - an operator whose degree is declared CORRECTLY -
     shows ratio exactly 1.000 across the same sigma sweep.

If 1 holds, the host cannot distinguish a right declaration from a wrong one,
and the seam's residual declaration is unchecked by construction.

All seven shipped `reference.rs` operators declare the CORRECT degree today, so
this is a latent hole in the contract, not a live wrong number.
"""

import json
import pathlib

import numpy as np
from scipy.ndimage import uniform_filter

WINDOW_RADIUS, REGULARISER_RADIUS, SIGMA_EPS = 13, 8, 1e-3
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


# (operator, TRUE homogeneity degree)
OPS = {
    "tenengrad |grad|": (lambda a: np.hypot(*sobel(a)), 1),
    "sum-modified-laplacian": (lambda a: np.abs(2 * a - sh(a, 0, 1) - sh(a, 0, -1))
                               + np.abs(2 * a - sh(a, 1, 0) - sh(a, -1, 0)), 1),
    "tenengrad-squared": (lambda a: (lambda g: g[0] ** 2 + g[1] ** 2)(sobel(a)), 2),
    "local variance (3x3)": (lambda a: clamped_box(a * a, 1) - clamped_box(a, 1) ** 2, 2),
}

rng = np.random.Generator(np.random.Philox(52090823))
base = rng.standard_normal((1536, 1536))
m = 96


def field_sd(fn, x, sigma, declared_degree):
    resp = clamped_box(fn(x), WINDOW_RADIUS)
    resp = resp / max(sigma, SIGMA_EPS) ** declared_degree
    f = clamped_box(resp, REGULARISER_RADIUS)
    return float(f[m:-m, m:-m].std(ddof=1))


print("1. THE CALIBRATION PLANE (sigma = 1 DN, as calibrate.rs:309 uses)")
print(f"{'operator':<26}{'true deg':>9}{'as deg 1':>12}{'as deg 2':>12}{'ratio':>12}")
out = {"calib_sigma1": {}, "real_sigma": {}}
for name, (fn, deg) in OPS.items():
    a = field_sd(fn, base, 1.0, 1)
    b = field_sd(fn, base, 1.0, 2)
    out["calib_sigma1"][name] = {"true_degree": deg, "as_deg1": a, "as_deg2": b,
                                 "ratio": b / a}
    print(f"{name:<26}{deg:>9}{a:>12.6f}{b:>12.6f}{b / a:>12.8f}")
print("   -> the host measures the SAME constant whatever degree is declared.\n")

SIG = 17.48  # 109MSDCF median green_luma_sigma, step 08
print(f"2. A REALISTIC PLANE (sigma = {SIG} DN, 109MSDCF's median)")
print(f"{'operator':<26}{'true deg':>9}{'correct':>12}{'mis-declared':>14}{'error':>12}")
for name, (fn, deg) in OPS.items():
    x = SIG * base
    good = field_sd(fn, x, SIG, deg)
    bad = field_sd(fn, x, SIG, 3 - deg)          # the other declaration
    out["real_sigma"][name] = {"true_degree": deg, "sigma": SIG,
                               "correct": good, "misdeclared": bad,
                               "error_factor": bad / good}
    print(f"{name:<26}{deg:>9}{good:>12.6f}{bad:>14.6f}{bad / good:>11.3f}x")

ctrl = [v["correct"] / out["calib_sigma1"][k][f"as_deg{v['true_degree']}"]
        for k, v in out["real_sigma"].items()]
print(f"\n   NEGATIVE CONTROL - correctly declared operators, sigma=1 constant vs")
print(f"   sigma={SIG} field: ratios {', '.join(f'{c:.6f}' for c in ctrl)}")
print(f"   max |deviation| from 1.000000 = {max(abs(c - 1) for c in ctrl):.2e}")
errs = [v["error_factor"] for v in out["real_sigma"].values()]
print(f"   MIS-DECLARED: error factors {', '.join(f'{e:.3f}x' for e in errs)} "
      f"(predicted sigma^(+-1) = {SIG:.2f} and {1 / SIG:.4f})")

p = pathlib.Path(__file__).resolve().parents[1] / "data" / "09-degree-declaration.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\nwrote {p}")
