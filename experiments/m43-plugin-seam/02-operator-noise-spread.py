"""M43 step 2 - the realistic spread of `k` across contributable focus measures.

Question 102 asks what `k = SD_operator / FOCUS_NOISE_SD` actually looks like
for operators someone would plausibly contribute. M43 step 1 priced the damage
at k = 5.94 and said plainly that the number was an illustration taken from the
two operators that happen to be in this repository. This measures the
distribution instead of illustrating it.

WHY A PYTHON INSTRUMENT IS ADMISSIBLE HERE, given M31-V's standing complaint
that Python proxies were never checked against the crate:

  it is calibrated, and the calibration can fail. The crate measures its own
  operator's noise SD twice, at two window radii:

      FOCUS_NOISE_SD      = 0.015214 +/- 0.000075   (tenengrad, w13)
      FINE_FOCUS_NOISE_SD = 0.090400                (tenengrad, w2)

  Step A below reimplements exactly that operator and must reproduce BOTH
  numbers before any other operator is reported. Two independent targets at a
  7x separation in window area is a real test: an implementation that got the
  Sobel weights, the box normalisation, or the border convention wrong would
  have to be wrong in a way that is simultaneously right at w13 and w2. If
  step A fails, the script refuses to print step B.

The measured quantity, for a focus operator F:

    the plane is unit-variance white Gaussian noise and the noise model returns
    sigma = 1, so the "noise-normalised" focus field is just F(noise), and
    SD_operator is the standard deviation of that field across pixels. This is
    the same construction the crate's own test uses.

f64 throughout where the crate uses f32. That is a deliberate difference: f32
rounding is ~1e-7 relative on this statistic and the crate's own uncertainty is
5e-3 relative, so it cannot matter, and f64 removes it as a confound in the
calibration.
"""

import json
import pathlib

import numpy as np

# ---------------------------------------------------------------- the targets

FOCUS_NOISE_SD = 0.015214  # crates/strehl-core/src/merge.rs, measured in-crate
FOCUS_NOISE_SD_TOL = 0.000075
FINE_FOCUS_NOISE_SD = 0.090400
WINDOW_RADIUS = 13
FINE_WINDOW_RADIUS = 2

SIDE = 2048
SEEDS = 8


# ------------------------------------------------------------------ primitives


def replicate(a, dy, dx):
    """Shift by (dy, dx) with replicate-clamped borders, matching focus.rs."""
    out = a
    if dy:
        out = np.roll(out, -dy, axis=0)
        if dy > 0:
            out[-dy:, :] = a[-1, :]
        else:
            out[:-dy, :] = a[0, :]
    if dx:
        shifted = np.roll(out, -dx, axis=1)
        if dx > 0:
            shifted[:, -dx:] = out[:, -1][:, None]
        else:
            shifted[:, :-dx] = out[:, 0][:, None]
        out = shifted
    return out


def box_mean(a, r):
    """Separable box mean of radius r, replicate-clamped. Exact, via cumsum."""
    if r == 0:
        return a.copy()
    pad = np.pad(a, ((r, r), (r, r)), mode="edge")
    c = np.cumsum(pad, axis=0)
    c = np.vstack([np.zeros((1, c.shape[1])), c])
    a = (c[2 * r + 1 :, :] - c[: -(2 * r + 1), :]) / (2 * r + 1)
    c = np.cumsum(a, axis=1)
    c = np.hstack([np.zeros((c.shape[0], 1)), c])
    return (c[:, 2 * r + 1 :] - c[:, : -(2 * r + 1)]) / (2 * r + 1)


def sobel(a):
    gx = 0.125 * (
        replicate(a, -1, 1)
        + 2.0 * replicate(a, 0, 1)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, 0, -1)
        - replicate(a, 1, -1)
    )
    gy = 0.125 * (
        replicate(a, 1, -1)
        + 2.0 * replicate(a, 1, 0)
        + replicate(a, 1, 1)
        - replicate(a, -1, -1)
        - 2.0 * replicate(a, -1, 0)
        - replicate(a, -1, 1)
    )
    return gx, gy


# ------------------------------------------------------------------- operators
# Each returns the PER-PIXEL response BEFORE the box window. The box window and
# the sigma division are applied uniformly by `field()`, because that is what
# focus.rs does and the question is about the operator, not the window.


def op_tenengrad(a):
    gx, gy = sobel(a)
    return np.sqrt(gx * gx + gy * gy)


def op_tenengrad_sq(a):
    gx, gy = sobel(a)
    return gx * gx + gy * gy


def op_brenner(a):
    d = replicate(a, 0, 2) - a
    return np.abs(d)


def op_laplacian(a):
    return np.abs(
        4.0 * a
        - replicate(a, 0, 1)
        - replicate(a, 0, -1)
        - replicate(a, 1, 0)
        - replicate(a, -1, 0)
    )


def op_sml(a):
    """Sum-modified-Laplacian (Nayar & Nakagawa), the classic SFF operator."""
    return np.abs(2.0 * a - replicate(a, 0, 1) - replicate(a, 0, -1)) + np.abs(
        2.0 * a - replicate(a, 1, 0) - replicate(a, -1, 0)
    )


def op_ring13(a):
    """The M11 ring(1,3) operator: |mean(inner) - mean(outer)| style contrast."""
    return np.abs(box_mean(a, 1) - box_mean(a, 3))


def op_local_variance(a):
    m = box_mean(a, 1)
    return box_mean(a * a, 1) - m * m


OPERATORS = {
    "tenengrad |grad|": op_tenengrad,
    "tenengrad-squared |grad|^2": op_tenengrad_sq,
    "brenner |I(x+2)-I(x)|": op_brenner,
    "laplacian |4I - N4|": op_laplacian,
    "sum-modified-laplacian": op_sml,
    "ring(1,3)": op_ring13,
    "local variance (3x3)": op_local_variance,
}


def field(rng, op, radius):
    """SD of the noise-normalised focus field, interior only and whole plane."""
    a = rng.standard_normal((SIDE, SIDE))
    f = box_mean(op(a), radius)
    m = radius + 2  # drop the border the replicate convention distorts
    return float(np.std(f[m:-m, m:-m], ddof=1)), float(np.std(f, ddof=1))


def measure(op, radius, seeds=SEEDS):
    inner, whole = [], []
    for s in range(seeds):
        i, w = field(np.random.default_rng(20260810 + s), op, radius)
        inner.append(i)
        whole.append(w)
    return {
        "interior_mean": float(np.mean(inner)),
        "interior_sem": float(np.std(inner, ddof=1) / np.sqrt(len(inner))),
        "whole_mean": float(np.mean(whole)),
    }


# ------------------------------------------------------- step A: calibration


print("=" * 74)
print("STEP A - calibrate the instrument against the crate's own two constants")
print("=" * 74)
print(f"  {SEEDS} seeds x {SIDE}x{SIDE} unit-variance white Gaussian noise\n")

cal = {}
ok = True
for label, radius, target, tol in [
    ("FOCUS_NOISE_SD (w13)", WINDOW_RADIUS, FOCUS_NOISE_SD, FOCUS_NOISE_SD_TOL),
    ("FINE_FOCUS_NOISE_SD (w2)", FINE_WINDOW_RADIUS, FINE_FOCUS_NOISE_SD, None),
]:
    r = measure(op_tenengrad, radius)
    cal[label] = {**r, "crate": target}
    dev = r["interior_mean"] - target
    rel = dev / target
    # Without an in-crate uncertainty for the fine constant, hold both to the
    # relative tolerance the crate published for the coarse one.
    lim = tol if tol is not None else target * (FOCUS_NOISE_SD_TOL / FOCUS_NOISE_SD)
    hit = abs(dev) <= lim
    ok &= hit
    print(
        f"  {label:<28} crate {target:.6f}   python {r['interior_mean']:.6f}"
        f" +/- {r['interior_sem']:.6f}   dev {rel:+.2%}   "
        f"{'MATCH' if hit else 'MISMATCH'}"
    )
    print(f"  {'':<28} (whole plane incl. border: {r['whole_mean']:.6f})")

print()
if not ok:
    print("  CALIBRATION FAILED - the instrument does not reproduce the crate.")
    print("  Refusing to report step B. Nothing below would be trustworthy.")
    raise SystemExit(1)
print("  CALIBRATED. Both constants reproduced; step B may be reported.\n")


# --------------------------------------------- step B: the spread of k


print("=" * 74)
print("STEP B - k for operators someone would plausibly contribute")
print("=" * 74)
print(f"  k = SD_operator / {FOCUS_NOISE_SD} (the constant a plugin would inherit)")
print(f"  effective gate = intended gate / k\n")
print(f"  {'operator':<30}{'window':>8}{'SD':>13}{'k':>10}{'eff. gate @1.0':>17}")
print("  " + "-" * 76)

rows = []
for name, op in OPERATORS.items():
    for radius in (WINDOW_RADIUS, FINE_WINDOW_RADIUS):
        r = measure(op, radius, seeds=4)
        k = r["interior_mean"] / FOCUS_NOISE_SD
        rows.append(
            {
                "operator": name,
                "window_radius": radius,
                "sd": r["interior_mean"],
                "sem": r["interior_sem"],
                "k": k,
                "effective_gate_at_1": 1.0 / k,
            }
        )
        print(
            f"  {name:<30}{f'w{radius}':>8}{r['interior_mean']:>13.6f}"
            f"{k:>10.3f}{1.0 / k:>17.4f}"
        )

ks = [r["k"] for r in rows]
print()
print(f"  k spans {min(ks):.3f} to {max(ks):.3f}  =  {max(ks) / min(ks):.1f}x")
print(f"  M43 step 1 priced the damage at k = 5.942 (tenengrad w2 / w13).")

out = pathlib.Path(__file__).with_name("02-operator-noise-spread.json")
out.write_text(
    json.dumps(
        {
            "calibration": cal,
            "focus_noise_sd": FOCUS_NOISE_SD,
            "side": SIDE,
            "rows": rows,
        },
        indent=2,
    ),
    encoding="utf-8",
)
print(f"\n  wrote {out.name}")
