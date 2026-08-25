"""R16 -- re-run the R13 gates with the support floor R15 showed was missing.

R15 established two things:

  * ORCH's ~12-levels-per-window bound does NOT explain R14's 23% narrowing
    shift (median 25 levels/window, Y1 FALSIFIED).
  * A support floor DOES: narrowing bias falls monotonically 22.9% -> 0.8%
    as an M113-style MIN_EDGE_ENERGY rises 0 -> 480 (Y2 HOLDS, Y3 valid at
    3.5x window-count variation).

But R15's table carries a second result I was not looking for, and it is the
bigger one. The uint16 column -- no narrowing anywhere -- also moves:

    floor    0 -> t16 = 0.8338      (what R13 reported as "X1 FAIL")
    floor  120 -> t16 = 0.9148
    floor  480 -> t16 = 0.9167

R13's X1 failure was NOT residual contamination, as section 23 concluded. It
was my estimator integrating low-contrast windows that M113's shipped
MIN_EDGE_ENERGY = 60.0 would have refused. So section 23's headline needs
correcting, and the correction is testable: with a floor, do R13's other
gates pass, and does `needed` then agree with M113's registered 529.9 ppm?

FLOOR SELECTION -- fixed before running this script, and derived from R15's
already-printed table rather than from anything R16 computes: take the
SMALLEST floor whose narrowing bias is under 5% while admitting at least 1000
windows. That is 120 (bias 4.2%, n = 1287). Floor 240 is run alongside as a
robustness check, NOT as a second chance: if the two floors disagree, the
result is unstable and I report no number.

BARS -- registered before running.

  Z1  Transfer check applied/eps_r in [0.90, 1.05] at BOTH floors.
      This is R13's X1 band, unchanged, so the comparison is honest.
      Falsified if either floor lands outside.

  Z2  All four planted gains in [0.95, 1.05] and sign asymmetry under 10%,
      at the selected floor. R13 without a floor gave 0.940/0.927/0.771/0.655
      and 30.3% asymmetry. Falsified if the floor does not fix this -- which
      is a live possibility, because amplitude saturation is a DIFFERENT
      mechanism from low support and a floor need not touch it.

  Z3  Tangential placebo leak under 10%.

  Z4  Reported ONLY if Z1-Z3 all pass at both floors. `needed` vs M113's
      registered 529.9 ppm. I register in advance that agreement means
      within 15%; a larger gap is a disagreement I must report as such and
      must NOT explain away.

If Z2 fails, Z1 still stands on its own and section 23's correction is real
regardless -- the two bars test different claims.
"""

import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r13_clean_calib import EPS, M113_NEEDED_PPM, R13, plant  # noqa: E402
from r15_reconcile import estimate_floored  # noqa: E402

SEL, CHECK = 120.0, 240.0


def tan_plant(red, mag):
    h, w = red.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - cx, yy - cy
    n = np.hypot(dx, dy)
    n[n < 1e-6] = 1e-6
    sx = xx + mag * (-dy)
    sy = yy + mag * dx
    return ndimage.map_coordinates(red, [sy, sx], order=3, mode="nearest").astype(np.float32)


def main():
    print("=" * 72)
    print("R16 -- R13's gates, with the support floor R15 showed was missing")
    print("=" * 72)
    off = tifffile.imread(os.path.join(R13, "off.tif"))
    on = tifffile.imread(os.path.join(R13, "on.tif"))
    ro, go = off[..., 0].astype(np.float32), off[..., 1].astype(np.float32)
    rn, gn = on[..., 0].astype(np.float32), on[..., 1].astype(np.float32)

    print("\nZ1  TRANSFER CHECK at the selected floor and the robustness floor")
    res = {}
    for f in (SEL, CHECK):
        e_off, n_off, _ = estimate_floored(ro, go, f)
        e_on, _, _ = estimate_floored(rn, gn, f)
        tr = (e_on - e_off) / EPS
        res[f] = (e_off, e_on, tr, n_off)
        print(f"    floor {f:5.0f}  n {n_off:5d}   off {e_off*1e6:+8.1f}  "
              f"on {e_on*1e6:+8.1f}   applied/eps_r = {tr:.4f}")
    print(f"    R13 without a floor: 0.8338  (reported as X1 FAIL)")
    print(f"    M113 clean space:    0.9399 / 0.9813")
    z1 = all(0.90 <= res[f][2] <= 1.05 for f in (SEL, CHECK))
    spread = abs(res[SEL][2] - res[CHECK][2])
    print(f"    floor-to-floor spread {spread:.4f}")
    print(f"    Z1 {'PASS -- the space was clean; my instrument was not' if z1 else 'FAIL'}")

    print("\nZ2  PLANTED RECOVERY at the selected floor")
    base, _, _ = estimate_floored(plant(ro, 0.0), go, SEL)
    gains = []
    for lab, e in (("-704.5", EPS), ("+704.5", -EPS),
                   ("-352.2", EPS / 2), ("+352.2", -EPS / 2)):
        got, _, _ = estimate_floored(plant(ro, e), go, SEL)
        got -= base
        gains.append(got / e)
        print(f"    plant {lab:>8s} -> recovered {got*1e6:+9.1f} ppm   gain {got/e:.4f}")
    asym = abs(abs(gains[1]) - abs(gains[0])) / max(abs(gains[0]), 1e-12)
    z2 = all(0.95 <= g <= 1.05 for g in gains) and asym < 0.10
    print(f"    spread {max(gains)-min(gains):.4f}   asymmetry {100*asym:.1f}%")
    print(f"    R13 without a floor: 0.940/0.655/0.927/0.771, asymmetry 30.3%")
    print(f"    Z2 {'PASS -- CALIBRATED' if z2 else 'FAIL -- floor does not fix amplitude saturation'}")

    rot = abs(EPS)
    got, _, _ = estimate_floored(tan_plant(ro, rot), go, SEL)
    leak = abs(got - base) / abs(rot)
    z3 = leak < 0.10
    print(f"\nZ3  TANGENTIAL PLACEBO -- radial leak {100*leak:.1f}%  "
          f"{'PASS' if z3 else 'FAIL'}")

    print("\n" + "=" * 72)
    if not (z1 and z2 and z3):
        print("Z4 NOT REPORTED -- gates failed. No `needed` value from M107.")
        if z1:
            print("Z1 stands on its own: section 23's 'still contaminated' is WRONG.")
        print("=" * 72)
        return
    print("Z4  CALIBRATED -- the scene's own lateral CA")
    for f in (SEL, CHECK):
        need = -res[f][0]
        gap = 100 * abs(need * 1e6 - M113_NEEDED_PPM) / M113_NEEDED_PPM
        print(f"    floor {f:5.0f}:  needed {need*1e6:8.1f} ppm   "
              f"shipped {abs(EPS)*1e6:.1f}   gain {abs(EPS)/need:.4f}   "
              f"vs M113 {M113_NEEDED_PPM}: {gap:.1f}% apart")
    g1 = 100 * abs(-res[SEL][0] * 1e6 - M113_NEEDED_PPM) / M113_NEEDED_PPM
    print(f"    {'AGREES with M113 (within 15%)' if g1 <= 15 else 'DISAGREES with M113 -- report as a disagreement'}")
    print("=" * 72)


if __name__ == "__main__":
    main()
