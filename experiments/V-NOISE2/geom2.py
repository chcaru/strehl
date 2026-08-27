"""Per-subject geometry between strehl's raster and each comparator's.

PREREGISTRATION.md sec.2 item 5: geometry is RE-DERIVED for every subject and
never carried across.  The scale depends on which frame `align_image_stack`
anchored on, and that frame is a different focus -- hence a different
magnification -- in every bracket.  V-HEADTOHEAD2 sec.7 names trusting geometry
as one of the three things that invalidated an entire previous pass.

The fit itself is the prior lane's instrument used AS-IS: `geom.fit` and
`geom.offsets` are imported from experiments/V-HEADTOHEAD2/geom.py, not copied
and not modified.  Only the list of pairs is new.

A sweep with NO INTERIOR MAXIMUM is a FAILED FIT.  It is reported and the
subject's comparator is abandoned, not refined -- refining an edge maximum
invents a scale.

WHICH PAIR IS FITTED, and why it is the half and not a full stack.  Both
comparator halves are fused from ONE shared aligned set, so they are in the
same raster by construction; strehl's A half defines strehl's raster.  Fitting
strehl-A against coh-enfuse-A therefore measures exactly the scale h2h2b-style
crop addressing needs, and costs one fewer full-stack render per subject.

INVOCATION (rule 47).  Reads C:\\dev\\strehl-out\\V-NOISE2\\<key>\\arms\\*.tif*.
Writes C:\\dev\\strehl-out\\V-NOISE2\\<key>\\geom.json.

    python geom2.py <key> [<key> ...]
"""
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import geom                                                      # noqa: E402

ROOT = r"C:\dev\strehl-out\V-NOISE2"
COMPARATORS = {
    "enfuse": ("coh-enfuse-A.tif",
               "Hugin align_image_stack + enfuse --hard-mask (GPL)"),
    "fs15-coh": ("coh-fs15-A.tif",
                 "focus-stack merge on Hugin-aligned frames (MIT)"),
}


def fit_subject(key):
    arm = os.path.join(ROOT, key, "arms")
    strehl = os.path.join(arm, "strehl-A.tiff")
    if not os.path.exists(strehl):
        print(f"{key}: NO strehl-A.tiff -- subject not built")
        return None
    out = {}
    for k, (fn, label) in COMPARATORS.items():
        cp = os.path.join(arm, fn)
        print(f"\n=== {key} / {k}: strehl vs {label} ===")
        if not os.path.exists(cp):
            print(f"  NOT PRESENT: {cp} -- FAILED (missing output)")
            out[k] = {"ok": False, "why": "missing output"}
            continue
        coarse = np.arange(0.970, 1.0301, 0.005)
        s, sc, ok, _ = geom.fit(strehl, cp, coarse)
        if not ok:
            print("  coarse sweep has NO INTERIOR MAXIMUM -- FAILED FIT, "
                  "refusing to refine.")
            out[k] = {"ok": False, "why": "no interior maximum"}
            continue
        fine = np.arange(s - 0.006, s + 0.0061, 0.001)
        s2, sc2, ok2, _ = geom.fit(strehl, cp, fine, verbose=False)
        off = geom.offsets(strehl, cp, s2)
        dy, dx, pk = off[:, 2], off[:, 3], off[:, 4]
        rms = float(np.sqrt(((dy - np.median(dy)) ** 2 +
                             (dx - np.median(dx)) ** 2).mean()))
        print(f"  REFINED scale {s2:.4f} score {sc2:.4f} "
              f"{'(interior)' if ok2 else '(EDGE -- treat with suspicion)'}")
        print(f"  per-tile offsets ({len(off)} tiles): "
              f"dy median {np.median(dy):+.1f} dx median {np.median(dx):+.1f}")
        print(f"  peak median {np.median(pk):.4f} min {pk.min():.4f}")
        print(f"  residual after one global integer shift: {rms:.1f} px rms")
        out[k] = {"ok": True, "scale": round(float(s2), 4),
                  "score": round(float(sc2), 4), "interior": bool(ok2),
                  "rms_px": round(rms, 2), "label": label}
    p = os.path.join(ROOT, key, "geom.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {p}")
    return out


def main():
    keys = sys.argv[1:]
    if not keys:
        raise SystemExit(__doc__)
    for k in keys:
        fit_subject(k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
