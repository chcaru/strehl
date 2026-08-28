r"""Overshoot census AFTER neutralising the tone-stage difference.

The two arms do not share a tone curve (the black/white points are placed from
the merged image, so changing the merge changes the curve). A black-point shift
is an offset plus a gamma, which scales local contrast globally and therefore
scales the overshoot statistic. This re-runs the commissioned overshoot census
on a tone-neutralised B so the number is structure, not tone.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import tonematch as tm                                             # noqa: E402
import overshoot as ov                                             # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR"

print("%-22s %10s %10s %10s   %s" % ("subject", "raw B-A", "tone-neut", "shift DN", "verdict"))
for s in ("leaf-2-cpl", "coffee-bubbles", "119MSDCF", "wrapped-text-1", "bee-2-cpl"):
    gA, cmA, cA = bm.load(os.path.join(OUT, "%s__A-unset.tiff" % s))
    gB, cmB, cB = bm.load(os.path.join(OUT, "%s__B-coarse8.tiff" % s))
    cm = cmA | cmB
    raw = ov.score(gA, gB, cm)
    x, y = tm.transfer(gA, gB)
    gBc = tm.apply_inverse(gB, x, y)
    neu = ov.score(gA, gBc, cm)
    med = float(np.median(np.abs(y - x)))
    v = "MORE overshoot" if neu[3] > 0 else ("LESS overshoot" if neu[4] < 0 else "indistinguishable")
    print("%-22s %+9.3f%% %+9.3f%% [%+.3f,%+.3f] %8.1f   %s"
          % (s, raw[2], neu[2], neu[3], neu[4], med * 65535, v))
