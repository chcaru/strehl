r"""The gate's blotch is band/mean.  Print BOTH terms for master and frames.

112MSDCF and coffee-bubbles both showed the ratio moving because the MEAN moved:
an all-in-focus master of a high-contrast subject is DARKER in the sRGB domain
than a defocused frame of it (blur plus a concave encode raises the mean -- the
same Jensen effect measured on foam), so the denominator shrinks.  Since both
arms are rendered by the same binary with the same exposure and the same sRGB
encode, band_DN is directly comparable between them and is the term that says
whether the merge added mid-scale STRUCTURE.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402

SUBJ = ["112MSDCF", "113MSDCF", "coffee-bubbles", "couch-fibers-cpl",
        "flat-on-ruler-cpl", "flower-inner-edge-cpl", "foam", "lead-1-cpl", "leaf-2-cpl"]

print("%-22s %8s %8s %8s | %8s %8s %8s | %6s %6s %6s"
      % ("subject", "M ctr", "M band", "M mean", "S ctr", "S band", "S mean",
         "r_ctr", "r_band", "r_mean"))
for s in SUBJ:
    with open(os.path.join(V.OUT, "source_%s.json" % s)) as fh:
        d = json.load(fh)
    ok = [r for r in d["rows"] if r["state"] == "OK"]
    m = d["master"]["blotch"]
    bb = max(r["band"] for r in ok)
    cc = max(r["blotch"] for r in ok)
    kb = max(ok, key=lambda r: r["band"])
    print("%-22s %8.5f %8.1f %8.1f | %8.5f %8.1f %8.1f | %6.3f %6.3f %6.3f"
          % (s, m["contrast"], m["band"], m["mean"], cc, bb, kb["mean"],
             m["contrast"] / cc, m["band"] / bb, m["mean"] / kb["mean"]))
    means = [r["mean"] for r in ok]
    bands = [r["band"] for r in ok]
    print("%-22s frames: band %.1f..%.1f (med %.1f)   mean %.1f..%.1f (med %.1f)"
          % ("", min(bands), max(bands), float(np.median(bands)),
             min(means), max(means), float(np.median(means))))
