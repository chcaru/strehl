"""WHY DOES v6 FAIL TO COMMISSION ON 119, WHEN IT COMMISSIONS ON 113?

THE FAILURE, from logs/rim-both.txt.  A single line fails on all three arms:
the rim-free negative control does not read its structural null.

    subject 113   cut sweep residual  +13.143% -> -0.301%   n 15230 -> 2396
    subject 119   cut sweep residual   -4.589% -> -4.158%   n 34886 -> 16434

On 113 the sweep crosses through zero and `choose_cut` finds a real minimum.
On 119 the residual is PINNED near -4.3% at every cut, and the selection
barely cuts anything: 47% of candidates survive the tightest cut, against
16% on 113.  A knob that does not move the thing it is supposed to control
is not a knob, and a floor of 4.1% is larger than any arm difference this
lane has measured, so 119 reports nothing.

THE HYPOTHESIS THIS FILE TESTS.  `measure()` normalises each profile by its
own end plateaus and then reads max(q) over t=+2..+7.  That is only a rim
measurement if the profile HAS a plateau inside the zone.  If 119's selected
features are wide, soft gradients rather than isolated occluding steps, then
q is still climbing at t=+7, max(q[+2..+7]) < 1 by construction, and the
reading is strongly negative for reasons that have nothing to do with rims.
The structural null is computed from an ISOLATED blurred step, so it cannot
describe a feature that never plateaus, and the residual is then irreducible.

WHAT WOULD FALSIFY IT.  If 119's median profile reaches q >= 0.95 by t=+7
just as 113's does, the hypothesis is wrong and the residual has some other
cause.  The test is therefore capable of acquitting it.

    python rimdiag119.py
"""
import os
import sys

import numpy as np
from scipy import ndimage

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import ffarms                                                    # noqa: E402
import rimv6                                                     # noqa: E402

T = 256


def profile_report(key, cut):
    arms = ffarms.build(key)
    a = arms["strehl"]
    grid = ffarms.detail_grid(a.g, T=T)
    rois = a.rois_for(grid, T)
    ref = ndimage.gaussian_filter(a.g, 3.0)
    sel = rimv6.select(ref, a.clip, rois, T, max_flat=cut)
    e = rimv6.measure(ref, sel, T)
    q = np.median(e["prof"], axis=0)
    R = rimv6.R
    w = rimv6.edge_width(e)

    print(f"\n{'='*100}")
    print(f"SUBJECT {key}   cut {cut}   selected {len(sel)}   measured "
          f"{len(e['ov'])}   edge width {w:.2f} px")
    print(f"{'='*100}")
    print("  MEDIAN NORMALISED PROFILE of the RIM-FREE reference.")
    print("  q is normalised to its own end plateaus, so q=1 IS the plateau.")
    print("  The bright zone reads max(q) over t=+2..+7.")
    print(f"    {'t':>4}  " + "".join(f"{t:>8}" for t in range(-8, 9)))
    print(f"    {'q':>4}  " + "".join(
        f"{q[R + t]:8.4f}" if 0 <= R + t < len(q) else "     ---"
        for t in range(-8, 9)))

    tail = [t for t in range(2, 9) if 0 <= R + t < len(q)]
    print(f"\n  q at t=+7 : {q[R + 7]:.4f}   q at t=-7 : {q[R - 7]:.4f}")
    print(f"  max q over the bright zone t=+2..+7 : "
          f"{max(q[R + t] for t in tail if t <= 7):.4f}")

    prof = np.asarray(e["prof"])
    reach_hi = float((prof[:, R + 7] >= 0.95).mean())
    reach_lo = float((prof[:, R - 7] <= 0.05).mean())
    print(f"\n  PER-EDGE, not just the median:")
    print(f"    edges whose profile has reached q>=0.95 by t=+7 : "
          f"{reach_hi*100:6.2f}%")
    print(f"    edges whose profile has reached q<=0.05 by t=-7 : "
          f"{reach_lo*100:6.2f}%")
    print(f"    median step (normalised DN) : {np.median(e['st']):.5f}")
    return dict(key=key, q7=float(q[R + 7]), qm7=float(q[R - 7]),
                reach_hi=reach_hi, reach_lo=reach_lo, width=float(w),
                n=len(e["ov"]))


def main():
    print(__doc__)
    out = []
    for key, cut in (("113", 0.03), ("119", 0.06)):
        out.append(profile_report(key, cut))

    print(f"\n{'='*100}")
    print("VERDICT")
    print("=" * 100)
    a, b = out
    print(f"  {'subject':<10}{'width':>8}{'q(+7)':>9}{'q(-7)':>9}"
          f"{'reach hi':>10}{'reach lo':>10}")
    for r in out:
        print(f"  {r['key']:<10}{r['width']:8.2f}{r['q7']:9.4f}"
              f"{r['qm7']:9.4f}{r['reach_hi']*100:9.1f}%"
              f"{r['reach_lo']*100:9.1f}%")
    if b["reach_hi"] < a["reach_hi"] - 0.10:
        print("\n  CONFIRMED: on 119 a materially smaller fraction of selected")
        print("  features have plateaued inside the measurement zone.  The")
        print("  residual is a ZONE-vs-FEATURE-WIDTH mismatch, not a rim.")
    else:
        print("\n  NOT CONFIRMED: 119's profiles plateau as well as 113's, so")
        print("  the residual has some other cause and this file is wrong.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
