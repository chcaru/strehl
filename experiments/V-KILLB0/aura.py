"""V-KILLB0 halo instrument: the AURA PROFILE.

The slanted-edge version was tried first and abandoned with its evidence: on
112MSDCF the erf fit's median R^2 over 250 candidate edges is 0.26 (see
diag_edges.py), i.e. this corpus has almost no isolated straight step edges, so
a per-edge overshoot metric admits 4-8 sites and is not reportable.

This uses the definition the project already states in `strehl stack --help`
for the estimator-vs-pyramid halo: the BACKGROUND LEVEL AS A FUNCTION OF
DISTANCE FROM THE SUBJECT.  A halo is a region of background near the subject
whose level departs from the same background far away.  It needs no straight
edge and no isolated feature.

  subject mask : luma smoothed at sigma 12, thresholded at the midpoint of its
                 own 2nd and 98th percentiles.  Reported both ways so a bright
                 subject on a dark ground and a dark subject on a bright ground
                 are both handled.
  distance     : Euclidean distance transform of the background from the mask.
  profile      : mean background luma in distance rings.
  far field    : the 200-320 px ring.
  aura depth   : ring mean - far field, at 10-30, 30-80 and 80-200 px.

A positive number is a BRIGHT rim, a negative one a DARK aura.  |aura| growing
in the arm is the failure the owner cares about most.

CONTROLS, every run:
  C0 NULL   arm against itself -> every ring difference exactly 0.
  C1 PLANT  a synthetic halo is added to arm B: +2% of the far-field level
            applied in the 10-40 px ring only.  The instrument must recover
            approximately that amplitude in that ring and approximately zero
            elsewhere.  A halo metric that cannot see a planted halo is dead.
"""
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, binary_erosion

import bandprobe as bp

RINGS = [(10, 30), (30, 80), (80, 200)]
FAR = (200, 320)


def masks(lum):
    s = gaussian_filter(lum, 12.0)
    lo, hi = np.percentile(s, 2), np.percentile(s, 98)
    t = 0.5 * (lo + hi)
    bright = s > t
    # background is whichever side has more area; the subject is the other
    if bright.mean() > 0.5:
        subject = ~bright
    else:
        subject = bright
    subject = binary_erosion(subject, iterations=2)
    return subject


def profile(lum, dist):
    out = {}
    for a, b in RINGS + [FAR]:
        m = (dist >= a) & (dist < b)
        out[(a, b)] = float(lum[m].mean()) if m.sum() > 5000 else np.nan
    return out


def aura(lum, dist):
    p = profile(lum, dist)
    far = p[FAR]
    return {r: p[r] - far for r in RINGS}, far, {r: int(((dist >= r[0]) & (dist < r[1])).sum()) for r in RINGS}


def main():
    A, B, label = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    assert la.shape == lb.shape
    sub = masks(la)
    dist = distance_transform_edt(~sub)
    frac = float(sub.mean())
    print(f"== AURA {label}   subject fraction {frac:.3f}")
    if frac < 0.02 or frac > 0.98:
        print("   NO USABLE SUBJECT/BACKGROUND SPLIT -- not reportable")
        return

    aA, farA, counts = aura(la, dist)
    aB, farB, _ = aura(lb, dist)

    # C0
    aN, _, _ = aura(la.copy(), dist)
    c0 = all(aN[r] == aA[r] for r in RINGS)
    print(f"  [C0 NULL ] max ring diff {max(abs(aN[r]-aA[r]) for r in RINGS):.3e}  "
          f"{'PASS' if c0 else 'FAIL'}")
    # C1 plant
    amp = 0.02 * farA
    planted = la.copy()
    ring = (dist >= 10) & (dist < 40)
    planted[ring] += amp
    aP, _, _ = aura(planted, dist)
    rec = aP[(10, 30)] - aA[(10, 30)]
    c1 = 0.7 * amp < rec < 1.3 * amp
    print(f"  [C1 PLANT] +{amp:.0f} DN in the 10-40 px ring: recovered "
          f"{rec:+.1f} DN in the 10-30 ring  {'PASS' if c1 else 'FAIL'}")
    if not (c0 and c1):
        print("  INSTRUMENT NOT COMMISSIONED -- results below are void")

    print(f"   far field ({FAR[0]}-{FAR[1]} px): default {farA:.1f} DN   arm {farB:.1f} DN   "
          f"delta {farB-farA:+.1f}")
    print(f"   {'ring px':>12s} {'n':>10s} {'default':>10s} {'arm':>10s} {'delta':>9s}  verdict")
    for r in RINGS:
        d = aB[r] - aA[r]
        worse = abs(aB[r]) > abs(aA[r]) + 1.0
        print(f"   {f'{r[0]}-{r[1]}':>12s} {counts[r]:10d} {aA[r]:+10.1f} {aB[r]:+10.1f} "
              f"{d:+9.1f}  {'WORSE' if worse else 'ok'}")


if __name__ == "__main__":
    main()
