"""M95 arm 4 - END-TO-END control through the SHIPPED code path.

x2 measured that one strehl gather costs 0.2851 dex. x3 showed an independently written
Catmull-Rom costs 0.2006 dex phase-averaged and 0.3897 dex at the worst phase, and the
in-crate M86b `align --resampler-cost` instrument reports Catmull-Rom retaining 0.5139 of
gradient energy at a half-pixel shift. Those agree in sign and order but they are all
models of the gather, not the gather itself.

This script closes that gap. It re-renders the SAME single frame through the SAME binary
with the sidecar's resampler switched to Nearest and to Bilinear, and measures all three
with the same instrument.

The decisive prediction, stated before the numbers were read:

  * NEAREST is a PERMUTATION of samples. It moves pixels and interpolates nothing, so it
    must cost approximately ZERO. If it does not, the loss is NOT the interpolation
    kernel and the whole diagnosis is wrong.
  * BILINEAR is strictly blurrier than Catmull-Rom. It must cost MORE.

Nearest is therefore both the null and the falsifier: a near-zero reading proves the
instrument is not simply charging for "a gather happened", and a large reading would
falsify the kernel diagnosis outright.
"""

import json
import os

import numpy as np

import x2_pairs as X

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "out")
R = r"C:\dev\strehl-out\M95-resample"

X.IMAGES["Bnear"] = dict(path=os.path.join(R, "single-nearest.tif"), k=0.9974, what="1 frame, gather = NEAREST")
X.IMAGES["Bbilin"] = dict(path=os.path.join(R, "single-bilinear.tif"), k=0.9974, what="1 frame, gather = BILINEAR")


def main():
    b0 = X.load_luma(X.IMAGES["B0"]["path"])
    tiles = X.pick_tiles(b0)
    base = np.array([X.band_ratio(b0[y : y + X.TILE, x : x + X.TILE], 1.0) for y, x in tiles])
    print(f"{len(tiles)} tiles, B0 baseline {base.mean():+.4f} dex\n")

    order = ["Bnear", "B1", "Bbilin"]
    labels = {"Bnear": "nearest", "B1": "catmull-rom", "Bbilin": "bilinear"}
    res = {}
    print(f"{'gather':14s} {'delta vs B0':>12s} {'power':>9s} {'amplitude':>11s} {'reg cc':>8s}  n")
    for name in order:
        if not os.path.exists(X.IMAGES[name]["path"]):
            print(f"  MISSING {name}")
            continue
        img = X.load_luma(X.IMAGES[name]["path"])
        vals, ccs = [], []
        for i, (y, x) in enumerate(tiles):
            r = X.register(b0, img, y, x, X.IMAGES[name]["k"])
            if r is None or r[0] < X.CC_FLOOR:
                continue
            cc, oy, ox, _, _ = r
            vals.append(X.band_ratio(img[oy : oy + X.TILE, ox : ox + X.TILE], X.IMAGES[name]["k"]) - base[i])
            ccs.append(cc)
        v = np.array(vals)
        res[labels[name]] = dict(delta=float(v.mean()), sd=float(v.std()), n=int(v.size), cc=float(np.mean(ccs)))
        print(
            f"{labels[name]:14s} {v.mean():+12.4f} {10**abs(v.mean()):9.3f}x "
            f"{10**(abs(v.mean())/2):10.3f}x {np.mean(ccs):8.4f}  {v.size}"
        )
        del img

    print("\n--- pre-registered predictions ---")
    ok = {}
    n = res.get("nearest", {}).get("delta")
    c = res.get("catmull-rom", {}).get("delta")
    b = res.get("bilinear", {}).get("delta")
    if n is not None:
        ok["nearest_is_free"] = abs(n) < 0.05
        print(f"  NEAREST costs ~0 (|delta| < 0.05 dex): {n:+.4f} -> {'PASS' if ok['nearest_is_free'] else 'FAIL'}")
    if b is not None and c is not None:
        ok["bilinear_worse"] = b < c
        print(f"  BILINEAR worse than CATMULL-ROM: {b:+.4f} < {c:+.4f} -> {'PASS' if ok['bilinear_worse'] else 'FAIL'}")
    if n is not None and c is not None:
        print(f"\n  attributable to the INTERPOLATION KERNEL alone: {c - n:+.4f} dex")
        print(f"  ({10**abs(c-n):.3f}x power, {10**(abs(c-n)/2):.3f}x amplitude)")

    json.dump(dict(results=res, checks=ok, baseline=float(base.mean())), open(os.path.join(OUT, "x4_endtoend.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'x4_endtoend.json')}")
    return 0 if all(ok.values()) else 3


if __name__ == "__main__":
    raise SystemExit(main())
