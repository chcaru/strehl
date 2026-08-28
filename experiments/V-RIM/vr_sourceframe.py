r"""coffee-bean, THE SAME SUBJECT, WITH NO STACKING AT ALL.

coffee-bean is the second-largest of the thirteen rim FAILs (+33.2%). Its
individual developed source frames sit in D:\edited\macro\coffee-bean. A single
capture has been through no merge, no pyramid, no election, so it cannot carry
a rim this project put there. Anything the axis reads on one of these frames is
the reading it would give strehl for doing nothing at all.

THREE FRAMES, NOT ONE. One frame cannot separate "this is what the axis reads
on an unstacked capture" from "this frame happened to read high". Three prices
the spread.

WHAT THIS CONTROL DOES NOT SETTLE, stated rather than buried: these frames are
Lightroom-developed and Lightroom applies capture sharpening, so a small
1-2 px overshoot may be present that the master does not have. The axis
measures at t=+2..+7 px, outside that radius, and the synthetic arm in
vr_specificity.py carries no develop step at all and reaches the same
conclusion; but this arm alone would not be enough.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

import vr_lib as V
import rimaxis

OUT = os.path.join(V.SCRATCH, "sourceframe.json")
D = r"D:\edited\macro\coffee-bean"
FRAMES = ["DSC00030.tif", "DSC00060.tif", "DSC00090.tif"]


def main():
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for f in FRAMES:
        if f in doc:
            continue
        p = os.path.join(D, f)
        if not os.path.exists(p):
            print("%s MISSING" % f)
            continue
        a = tifffile.imread(p)
        g = rimaxis.lum_of(a)
        hi = 1.0 if a.max() <= 1.5 else float(a.max())
        clip = (a.max(axis=2) >= hi) | (a.min(axis=2) <= 0.0)
        print("%s  %s %s  range %.4f..%.4f  clip %.3f%%"
              % (f, a.shape, a.dtype, float(a.min()), float(a.max()),
                 100 * clip.mean()))
        del a
        rec, sel, ref, em = V.run_pipeline(g, clip)
        del g, clip, ref
        rec["verdict"] = V.verdict(rec)[0]
        doc[f] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        cm = rec.get("coh_master")
        if cm is None:
            print("   %-8s %s" % (rec["verdict"], rec.get("refused", "")))
            continue
        print("   %-8s corrected %+7.3f%%  dark %+7.3f%%  n=%d  iso %.1f%%  "
              "max-then-med %+7.3f%%  MED-THEN-MAX %+7.3f%%  shoulder sd %6.4f"
              % (rec["verdict"], 100 * rec["corrected_bright"],
                 100 * rec["corrected_dark"], rec["n_sel"],
                 100 * rec["isolated_frac"], 100 * cm["max_then_median"],
                 100 * cm["median_then_max"], cm["shoulder_sd_median"]))
    print("\nMASTER FOR COMPARISON: coffee-bean--SHIP-V4 reads +33.246%%")
    print("wrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
