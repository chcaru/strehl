"""53-linear-delivered-gain.py -- does the patched shipping path deliver the
commanded exposure IN LINEAR LIGHT?

WHY A DISPLAY-SPACE SLOPE IS NOT THE ANSWER
===========================================
The first measurement of the patched binary regressed the encoded u16 values of
`--exposure 3` against `--exposure -3` and got 0.0447894 against a commanded
0.015625. Read naively that is "the flag over-delivers by 2.9x". It is nothing
of the kind. `--srgb` applies, AFTER the gain:

  1. the sRGB transfer curve (`color::srgb_encode`, a ~1/2.4 power law), and
  2. an s-curve in display space (`s_curve(x, c) = x + (x*x*(3-2x) - x)*c`),

and at +/-3 stops 87% of the samples clip. A ratio of linear quantities is NOT
preserved through a power law, so the display-space slope is a confounded
number and cannot be compared with a commanded LINEAR gain at all. Reporting
one against the other would be a units error dressed as a result -- exactly the
kind of legible-token-for-the-real-thing substitution this whole investigation
has been about.

So this inverts the display pipeline and measures where the quantity is
defined. Both stages are monotone on [0,1], so both invert: `srgb_encode`
analytically, `s_curve` by bisection.

WHAT IS PREDICTED, WRITTEN BEFORE READING THE RESULT
----------------------------------------------------
The fix multiplies the placed value by `g`, and the tone stage's own
normalisation has already cancelled the `g` folded in upstream. So the
pre-encode linear output is `g * (v * gain_base)` -- i.e. proportional to `g`.
For the pair `--exposure +0.25` and `--exposure -0.25` the commanded linear
ratio is `2^-0.5 = 0.7071068`, and that is what the regression must return.

A low exposure pair is used ON PURPOSE: at +/-0.25 stops almost nothing clips,
and a clipped sample has had its gain removed by the ceiling rather than by the
pipeline, which drags any slope toward 1.0 -- toward the null this test exists
to exclude.

COMMISSIONING
-------------
The inversion chain is commissioned before it is trusted, on this very data:
take arm E's decoded linear values, multiply by an exactly known factor, push
them FORWARD through the same encode + s-curve + quantise the renderer uses,
then invert and regress. A planted 2.0 must return 2.000 and a planted 0.5 must
return 0.500. The 0.5 arm is not decoration -- an estimator bounded below at
1.0, or one whose inversion is subtly not an inverse, passes the 2.0 arm.
"""

import sys

import numpy as np
import tifffile

D = r"C:\dev\strehl-out\BUILD-DEFECT\52-patched"
CONTRAST = 0.55  # from the render banner: `contrast 0.55`
FULL = 65535
ROWS = 256

# Commanded LINEAR gain of each arm, relative to no exposure flag.
COMMANDED = {"E-p025": 2.0**0.25, "F-m025": 2.0**-0.25}


def srgb_decode(e):
    return np.where(e <= 0.040_448_237, e / 12.92, ((e + 0.055) / 1.055) ** 2.4)


def s_curve_fwd(x, c):
    return x + (x * x * (3.0 - 2.0 * x) - x) * c


def s_curve_inv(y, c, iters=60):
    """Bisection. `s_curve` is monotone on [0,1] for c in [0,1], so this is a
    genuine inverse rather than an approximation that happens to be close."""
    lo = np.zeros_like(y)
    hi = np.ones_like(y)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        too_low = s_curve_fwd(mid, c) < y
        lo = np.where(too_low, mid, lo)
        hi = np.where(too_low, hi, mid)
    return 0.5 * (lo + hi)


def build_lut():
    """The renderer emits u16, so the display chain has exactly 65536 possible
    inputs. Inverting all of them once and indexing is not an optimisation of
    the bisection -- it is the same arithmetic, evaluated on every value the
    inverse can ever be asked for."""
    x = np.arange(FULL + 1, dtype=np.float64) / FULL
    return srgb_decode(s_curve_inv(x, CONTRAST))


LUT = build_lut()


def to_linear(u16):
    return LUT[u16]


def forward(lin):
    """The renderer's own display chain, used only to commission the inverse."""
    v = np.clip(lin, 0.0, 1.0)
    e = np.where(v <= 0.003_130_8, 12.92 * v, 1.055 * v ** (1.0 / 2.4) - 0.055)
    return np.clip(np.floor(s_curve_fwd(e, CONTRAST) * FULL + 0.5), 0, FULL).astype(
        np.int64
    )


def slope(x, y):
    sxx = float(x @ x)
    if sxx <= 0:
        sys.exit("degenerate regression: no signal in x")
    return float(x @ y) / sxx


def main():
    a = tifffile.memmap(D + r"\E-p025.tif", mode="r")
    b = tifffile.memmap(D + r"\F-m025.tif", mode="r")

    print("=" * 72)
    print("53 -- delivered exposure gain, measured in LINEAR light")
    print("=" * 72)
    commanded = COMMANDED["F-m025"] / COMMANDED["E-p025"]
    print(f"arms      : --exposure +0.25  vs  --exposure -0.25")
    print(f"commanded : {commanded:.7f}  (F/E linear ratio)")
    print("PREDICTION: the regression returns the commanded ratio, because the")
    print("            fix applies g on the far side of the normalisation.")

    # Commission on a real row before any verdict is read.
    print("\n-- commissioning the inversion + regression chain --")
    row = np.asarray(a[: 8 * ROWS]).ravel()
    lin = to_linear(row)
    keep0 = (row > 0) & (row < FULL)
    for planted in (2.0, 0.5, 1.0):
        replayed = to_linear(forward(lin * planted))
        k = keep0 & (replayed > 0) & (lin > 0) & (lin * planted < 1.0)
        got = slope(lin[k], replayed[k])
        ok = abs(got - planted) < 5e-3
        print(f"  planted {planted:<5} -> recovered {got:.6f}  {'OK' if ok else 'FAIL'}")
        if not ok:
            sys.exit("inversion chain is not commissioned; no verdict is readable")

    sxx = sxy = 0.0
    n = 0
    clipped = 0
    total = 0
    for r0 in range(0, a.shape[0], ROWS):
        x16 = np.asarray(a[r0 : r0 + ROWS]).ravel()
        y16 = np.asarray(b[r0 : r0 + ROWS]).ravel()
        total += x16.size
        keep = (x16 > 0) & (x16 < FULL) & (y16 > 0) & (y16 < FULL)
        clipped += int((~keep).sum())
        xl = to_linear(x16[keep])
        yl = to_linear(y16[keep])
        sxx += float(xl @ xl)
        sxy += float(xl @ yl)
        n += xl.size

    delivered = sxy / sxx
    print(f"\n  usable (unclipped) : {n:,} of {total:,}")
    print(f"  clipped/excluded   : {clipped:,}")
    print(f"  commanded          : {commanded:.7f}")
    print(f"  DELIVERED          : {delivered:.7f}")
    print(f"  error              : {100 * (delivered / commanded - 1):+.3f}%")

    if n < total // 4:
        print("\nFAIL: too few usable samples; the arms clipped away the evidence")
        return 1
    if abs(delivered / commanded - 1) > 0.02:
        print("\nFAIL: the delivered gain is not the commanded gain")
        return 1
    print("\nVERDICT: GREEN -- the commanded exposure is DELIVERED in linear light")
    return 0


if __name__ == "__main__":
    sys.exit(main())
