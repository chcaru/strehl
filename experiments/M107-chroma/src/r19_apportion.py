"""R19 -- complete the apportionment inside ONE instrument.

R18 measured, with my estimator on my clean data:

    clean binned-linear      0.9148
    + colour matrix only     1.4382   (forward model, no demosaic exists)

and compared the second to ORCH's full-sRGB 1.3073. That comparison CROSSES
INSTRUMENTS -- 1.3073 is M113's estimator on M114's render -- so it cannot
support the claim I was tempted to draw from it, that the matrix alone
overshoots the full sRGB path and the demosaic therefore pulls back. This
script either earns that claim or withdraws it, by measuring the full sRGB
path with MY estimator on MY render.

The r7 arms are the same stack rendered --srgb --auto-exposure, so they are
the full path: demosaic + matrix + tone curve, at full resolution.

CONFOUND, and the control for it. r7 is 4688x7032 full-resolution and
auto-exposed; r13 is 2344x3516 binned and linear. An absolute gradient floor
of 120 DN does not mean the same thing in the two spaces, so holding the
NUMBER fixed would not hold the SELECTIVITY fixed. The control is therefore to
match on the admitted-window FRACTION -- 1287/1707 = 75.4% on r13 at floor 120
-- by bisecting the r7 floor until it admits the same fraction. Matching the
floor's effect is the comparison; matching its value would be a coincidence.

BARS -- registered before running.

  F1  CONTROL VALIDITY.  The bisection must land within 2 percentage points
      of the 75.4% target, and the admitted count must be non-trivial
      (>= 200 windows).  If it cannot, the spaces are not comparable at
      matched selectivity and F2 must be discarded rather than reported.

  F2  APPORTIONMENT.  Registered from R18's numbers: the full sRGB path
      measured by MY estimator lands BELOW the matrix-only forward model of
      1.4382.  If it does, the demosaic and tone curve partially CANCEL the
      matrix error, and R18's reading was right for the right reason.
      Falsified if full-sRGB lands at or above 1.4382 -- in which case the
      operators compose additively, R18's cross-instrument comparison was
      misleading, and I must withdraw the cancellation claim outright.

  F3  MAGNITUDE SANITY.  Registered: my full-sRGB transfer lands within 0.25
      of ORCH's 1.3073.  This is a cross-instrument agreement check, not a
      bar on the physics; a miss means the two estimators disagree about the
      same space and that disagreement is itself worth reporting.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import EPS  # noqa: E402
from r15_reconcile import estimate_floored  # noqa: E402

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
TARGET_FRAC = 1287.0 / 1707.0
MATRIX_ONLY = 1.4382   # R18
CLEAN = 0.9148         # R16 Z1
ORCH_SRGB = 1.3073


def main():
    print("=" * 74)
    print("R19 -- full sRGB path, my estimator, floor matched on selectivity")
    print("=" * 74)
    off = tifffile.imread(os.path.join(R7, "off1.tif")).astype(np.float32)
    on = tifffile.imread(os.path.join(R7, "on.tif")).astype(np.float32)
    ro, go = off[..., 0], off[..., 1]
    rn, gn = on[..., 0], on[..., 1]
    print(f"\nr7 arms {ro.shape[1]}x{ro.shape[0]} (full res, --srgb --auto-exposure)")

    _, n_all, _ = estimate_floored(ro, go, 0.0)
    print(f"target admitted fraction {100*TARGET_FRAC:.1f}% (r13 floor 120)")
    print(f"r7 windows at floor 0: {n_all}")

    print("\nF1  BISECT the r7 floor to matched selectivity")
    lo, hi = 0.0, 20000.0
    best = None
    for i in range(14):
        mid = 0.5 * (lo + hi)
        _, n, _ = estimate_floored(ro, go, mid)
        frac = n / n_all
        print(f"    iter {i:2d}  floor {mid:9.1f}  n {n:6d}  frac {100*frac:5.1f}%")
        if best is None or abs(frac - TARGET_FRAC) < abs(best[2] - TARGET_FRAC):
            best = (mid, n, frac)
        if frac > TARGET_FRAC:
            lo = mid
        else:
            hi = mid
        if abs(frac - TARGET_FRAC) < 0.005:
            break
    floor, n_sel, frac = best
    f1 = abs(frac - TARGET_FRAC) <= 0.02 and n_sel >= 200
    print(f"    selected floor {floor:.1f}  n {n_sel}  frac {100*frac:.1f}% "
          f"(target {100*TARGET_FRAC:.1f}%)")
    print(f"    F1 {'HOLDS' if f1 else 'FAILED -- spaces not comparable at matched selectivity'}")
    if not f1:
        print("\nF2/F3 DISCARDED -- control failed.")
        print("=" * 74)
        return

    a, _, _ = estimate_floored(ro, go, floor)
    b, _, _ = estimate_floored(rn, gn, floor)
    t_srgb = (b - a) / EPS
    print(f"\nF2  off {a*1e6:+8.1f}  on {b*1e6:+8.1f}   full-sRGB transfer {t_srgb:.4f}")
    f2 = t_srgb < MATRIX_ONLY
    print(f"    matrix-only forward model {MATRIX_ONLY:.4f}")
    print(f"    F2 {'HOLDS -- demosaic + tone curve partially CANCEL the matrix error' if f2 else 'FALSIFIED -- operators compose additively; WITHDRAW the cancellation claim'}")
    f3 = abs(t_srgb - ORCH_SRGB) <= 0.25
    print(f"\nF3  vs ORCH's 1.3073: {abs(t_srgb-ORCH_SRGB):.4f} apart   "
          f"{'HOLDS -- two estimators agree about this space' if f3 else 'FALSIFIED -- estimators disagree, report it'}")

    print("\n" + "=" * 74)
    print("APPORTIONMENT, single instrument, matched selectivity:")
    print(f"    clean binned-linear                {CLEAN:.4f}   (ground truth 1.0)")
    print(f"    + colour matrix alone              {MATRIX_ONLY:.4f}")
    print(f"    + demosaic + matrix + tone curve   {t_srgb:.4f}")
    print(f"    ORCH, different instrument         {ORCH_SRGB:.4f}")
    print("=" * 74)


if __name__ == "__main__":
    main()
