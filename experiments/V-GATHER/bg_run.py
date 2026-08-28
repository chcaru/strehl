r"""The measurement ORCH asked for: rim axis on the per-band gate-floor pair.

ORDER IS DELIBERATE. Every commissioning arm runs BEFORE the treatment arm, on
the identical frozen edge set, so the gauge has demonstrated on this exact
subject that it is quiet on a null, responds to a planted aura, and -- the point
of the exercise -- can tell an aura removal apart from a softening. A reduction
reported by a gauge that never showed sensitivity on the subject in hand is not
a result.

THE FOUR CONTROLS AND WHAT EACH WOULD REFUTE:
  NULL     byte-identical file. Any non-zero reading is instrument noise and
           becomes the floor below which the treatment cannot be interpreted.
  USM      a planted aura. A null reading here would mean the gauge is blind and
           the treatment's number means nothing.
  BLUR     ORCH's trap. It LOWERS the raw overshoot. It must be caught by the
           width rising and by the structural-null correction absorbing it.
  MEDIAN   a planted IMPROVEMENT -- a 1x5 median removes a thin ridge and
           preserves a step by construction. A suite planting only degradations
           cannot tell a blind gauge from a perverse one.
"""
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bg_ab                                                       # noqa: E402

D = r"C:\dev\strehl-out\V-BANDFLOOR"
SUB = sys.argv[1] if len(sys.argv) > 1 else "leaf-2-cpl"
A = os.path.join(D, SUB + "__A-unset.tiff")
N = os.path.join(D, SUB + "__N-null.tiff")
B = os.path.join(D, SUB + "__B-coarse8.tiff")

arms = []
if os.path.exists(N):
    arms.append(("NULL byte-identical (control)", N))
arms += [
    ("USM 1.4 -- plants an aura", lambda g: np.clip(
        g + 1.4 * (g - gaussian_filter(g, 1.2)), 0, 1).astype(np.float32)),
    ("BLUR sigma 1.2 -- the trap", lambda g: gaussian_filter(g, 1.2)),
    ("MEDIAN 1x5 -- improvement", lambda g: median_filter(g, size=(1, 5))),
    ("B coarse8 -- THE TREATMENT", B),
]

print("subject: %s" % SUB)
print("A = %s" % A)
print("B = %s" % B)
print()
bg_ab.run(A, arms, SUB, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "bg_%s.json" % SUB))