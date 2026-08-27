r"""The mechanism behind every ratio above 1: SHARP IS DARK.

Claim to test, on data, not by argument: in the sRGB domain a defocused frame of
a high-contrast subject has a HIGHER window mean than a sharp one, because blur
is a local average and the sRGB encode is concave (Jensen).  The gate's blotch
is band/mean, so the sharpest render -- the master -- gets the smallest
denominator and the largest ratio without carrying any more structure.

PREDICTION, falsifiable: across the frames of one bracket, local sharpness
(relHF = noise_dn/mean_dn at the window) and window mean must be NEGATIVELY
correlated, and the master (sharp everywhere) must sit at or below the darkest
frame.  If the correlation is absent or positive on a subject, the mechanism
does not hold there and I must not use it.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

SUBJ = ["112MSDCF", "113MSDCF", "coffee-bubbles", "couch-fibers-cpl",
        "flat-on-ruler-cpl", "flower-inner-edge-cpl", "foam", "lead-1-cpl", "leaf-2-cpl"]
print("%-22s %6s  %-28s %-30s" % ("subject", "corr", "master mean vs frame means", "n"))
for s in SUBJ:
    with open(os.path.join(V.OUT, "source_%s.json" % s)) as fh:
        d = json.load(fh)
    ok = [r for r in d["rows"] if r["state"] == "OK"]
    hf = np.array([r["relhf"] for r in ok])
    mn = np.array([r["mean"] for r in ok])
    c = float(np.corrcoef(hf, mn)[0, 1])
    mm = d["master"]["blotch"]["mean"]
    below = int(np.sum(mn < mm))
    print("%-22s %+6.3f  master %8.1f, frames %8.1f..%8.1f, %d frame(s) darker  n=%d"
          % (s, c, mm, mn.min(), mn.max(), below, len(ok)))
