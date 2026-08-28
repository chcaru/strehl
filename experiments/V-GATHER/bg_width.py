r"""Potency test for the WIDTH statistic alone, at the frozen edge set.

The A/B run produced an incoherent width column: a gaussian blur of sigma 1.2
widened the median edge by +0.06 px while a 1x5 median widened it by +0.40 px.
A blur must widen more than a median. Either edge_width is not responding, or
it is responding to something other than blur.

This plants blurs of KNOWN size and requires the statistic to recover them.
For a gaussian edge the 10-90 width adds in quadrature:

    w(s) = sqrt(w0^2 + (2*1.2816*s)^2)

so the prediction is a VALUE at every rung, not a direction. If width does not
track blur, it cannot be used as the softening detector and the trap ORCH named
has no instrument -- which must then be reported as a gap, not papered over.
"""
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
sys.path.insert(0, HERE)
import rimv6                                                       # noqa: E402
import bg_ab                                                       # noqa: E402

K = 2.0 * 1.2815515655446004
A = r"C:\dev\strehl-out\V-BANDFLOOR\leaf-2-cpl__A-unset.tiff"

ga, clip = bg_ab.lum(A)
rois = bg_ab.pick_rois(ga, clip)
ctrl0 = ndimage.gaussian_filter(ga, bg_ab.SMOOTH).astype(np.float32)
sel = rimv6.select(ctrl0, clip, rois, bg_ab.T, 0.03)
del ctrl0
print("frozen selection: %d edges\n" % len(sel))

r0, e0 = bg_ab.arm_stats(ga, sel)
w0 = r0["width"]
print("control width w0 = %.3f px   (implied sigma %.3f)\n" % (w0, w0 / K))
print("%8s %10s %10s %10s %9s" % ("sigma", "width", "predicted", "d width",
                                  "d pred"))
print("-" * 52)
rows = []
for s in (0.0, 0.4, 0.8, 1.2, 2.0, 3.0):
    arm = ga if s == 0 else ndimage.gaussian_filter(ga, s)
    r, e = bg_ab.arm_stats(arm, sel)
    if r is None:
        print("%8.1f    REFUSED (outside null table)" % s)
        continue
    pred = float(np.hypot(w0, K * s))
    print("%8.1f %9.3fpx %9.3fpx %+9.3f %+9.3f"
          % (s, r["width"], pred, r["width"] - w0, pred - w0))
    rows.append((s, r["width"], pred))
    del arm

print("\nACCEPTANCE: width must recover a planted blur within 35%")
ok = True
for s, got, pred in rows:
    if s == 0:
        continue
    d, dp = got - rows[0][1], pred - rows[0][1]
    v = abs(d - dp) <= 0.35 * abs(dp)
    ok = ok and v
    print("  sigma %.1f  got %+.3f px  predicted %+.3f px   %s"
          % (s, d, dp, "PASS" if v else "**FAIL**"))
print("\nWIDTH STATISTIC IS %s AS A SOFTENING DETECTOR"
      % ("ADMISSIBLE" if ok else "INADMISSIBLE"))