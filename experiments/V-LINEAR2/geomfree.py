"""Geometry between strehl's raster and each FREE comparator's -- re-derived.

V-HEADTOHEAD2 sec.7 names trusting geometry as one of the three things that
invalidated the previous pass: a single global similarity fit against the
focus-stack fork left 5.3 px rms of local disagreement, which destroyed 41 of 64
regions.  docs/research/V-LINEAR.md sec.3 repeated the lesson in a different key
-- a "NON-LINEAR RADIAL WARP" verdict that evaporated when the rich and simple
models were finally fitted on the SAME rows.

So nothing here is assumed.  Every comparator gets its own scale sweep, and a
sweep without an interior maximum is reported as a FAILED FIT rather than
refined.  The scale that comes out is what h2free.py uses to size the
comparator's crop box, so that both arms read the same scene area.

This is the prior lane's instrument used AS-IS: geom.fit and geom.offsets are
imported from experiments/V-HEADTOHEAD2/geom.py, not copied and not modified.
Only the list of pairs is new.

INVOCATION (rule 47).  Reads:
    strehl     C:\\dev\\strehl-out\\V-H2H2\\lin\\113-full-g1.tiff
    comparator C:\\dev\\strehl-out\\V-LINEAR2\\out\\*.tif  (see PAIRS below)
Writes nothing but a .npy of the fit under C:\\dev\\strehl-out\\V-LINEAR2\\logs\\.

    python geomfree.py [tag ...]      (default: all present)
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import geom                                                      # noqa: E402

STREHL = r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff"
OUT = r"C:\dev\strehl-out\V-LINEAR2\out"
LOGS = r"C:\dev\strehl-out\V-LINEAR2\logs"

PAIRS = {
    "enfuse":  (rf"{OUT}\enfuse-hardmask.tif",  "Hugin align_image_stack + enfuse --hard-mask (GPL)"),
    "fs15":    (rf"{OUT}\focusstack-1.5.tif",   "focus-stack 1.5 upstream (MIT)"),
    "fsfork":  (rf"{OUT}\focusstack-fork.tif",  "focus-stack, owner's local build"),
    "coh-fs15": (rf"{OUT}\coh-fs15-full.tif",   "focus-stack 1.5 merge on Hugin-aligned frames (MIT)"),
    "enfuse-lv1": (rf"{OUT}\enfuse-lv1.tif",    "enfuse --hard-mask --levels=1 (GPL) [mechanism arm]"),
}


def main():
    want = sys.argv[1:] or list(PAIRS)
    for k in want:
        cp, label = PAIRS[k]
        if not os.path.exists(cp):
            print(f"\n=== {k}: {label} ===\n  NOT PRESENT: {cp} -- skipped")
            continue
        print(f"\n=== {k}: strehl vs {label} ===")
        coarse = np.arange(0.970, 1.0301, 0.005)
        s, sc, ok, _ = geom.fit(STREHL, cp, coarse)
        if not ok:
            print("  coarse sweep has NO INTERIOR MAXIMUM -- fit failed, "
                  "refusing to refine.\n  This pairing cannot be measured and "
                  "is abandoned, not reported.")
            continue
        fine = np.arange(s - 0.006, s + 0.0061, 0.001)
        s2, sc2, ok2, _ = geom.fit(STREHL, cp, fine, verbose=False)
        print(f"  REFINED scale {s2:.4f} score {sc2:.4f} "
              f"{'(interior)' if ok2 else '(EDGE -- treat with suspicion)'}")
        off = geom.offsets(STREHL, cp, s2)
        dy, dx, pk = off[:, 2], off[:, 3], off[:, 4]
        rms = np.sqrt(((dy - np.median(dy)) ** 2 +
                       (dx - np.median(dx)) ** 2).mean())
        print(f"  per-tile offsets ({len(off)} tiles): "
              f"dy median {np.median(dy):+.1f} [{dy.min():+.0f},{dy.max():+.0f}] "
              f"dx median {np.median(dx):+.1f} [{dx.min():+.0f},{dx.max():+.0f}]")
        print(f"  peak median {np.median(pk):.4f} min {pk.min():.4f}")
        print(f"  residual after one global integer shift: {rms:.1f} px rms  -> "
              f"{'one shift is enough' if rms < 4 else 'per-ROI offsets REQUIRED'}")
        np.save(os.path.join(LOGS, f"geom-{k}.npy"),
                np.array([s2, sc2] + list(off.ravel())))
        print(f"  scale for h2free.py: {s2:.4f}")


if __name__ == "__main__":
    sys.exit(main())
