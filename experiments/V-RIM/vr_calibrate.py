r"""WHAT RIM WOULD IT TAKE TO PRODUCE THE NUMBER THE MASTER READS?

rimcommission.py runs its ladder on ONE subject (a 2048 px crop of 109MSDCF,
which PASSES) and shows the reading is monotone in planted unsharp-mask amount.
It never runs the ladder on a subject that FAILS, so the number a failing master
reads has never been converted back into the rim amplitude it implies.

This runs the identical ladder -- rimcommission.usm, same amounts, same
radius -- on the convicted subjects. Two things fall out:

  CALIBRATION  the amount of planted unsharp mask whose reading equals the
               master's own. If that amount is one no renderer would apply,
               the reading is not a rim amplitude.

  HEADROOM     how far the reading still moves when a real rim IS added. A
               statistic already saturated by something else moves little.

MATCHED CONTROL: the same ladder on a PASS subject, same crop size, same seed,
so a difference between them is a difference in the subject.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

import vr_lib as V
import rimaxis

OUT = os.path.join(V.SCRATCH, "calibrate.json")
CROP = (1200, 3600, 2048, 2048)
AMTS = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0)
SUBJ = [("coffee-bean", "FAIL +33.2%"), ("wrapped-text-2", "FAIL +10.9%"),
        ("113MSDCF", "FAIL +17.3%"), ("109MSDCF", "PASS -2.2% (control)")]


def usm(g, amt, r=2.0):
    return g + amt * (g - ndimage.gaussian_filter(g, r))


def main():
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for s, tag in SUBJ:
        if s in doc:
            continue
        a = tifffile.imread(os.path.join(V.SHIP, s + "--SHIP-V4.tiff"))
        y, x, h, w = CROP
        a = a[y:y + h, x:x + w]
        g0 = rimaxis.lum_of(a)
        clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
        del a
        rois = rimaxis.pick_rois(g0, clip, n=64)
        ref, sel, n_all, cut, fl = rimaxis.select_for(g0, clip, rois)
        if fl is None:
            print("%-16s NO FLOOR -- cannot calibrate" % s)
            doc[s] = dict(refused="no floor")
            continue
        base_floor = fl["resid_bright"]
        print("\n%-16s %s   crop %s  %d/%d edges  cut %.2f  floor %+.4f%%"
              % (s, tag, CROP, len(sel), n_all, cut, 100 * base_floor))
        rows = []
        for amt in AMTS:
            r = rimaxis.measure_arm(usm(g0, amt).astype(np.float32), sel)
            if r is None:
                print("   usm %-5.2f  REFUSED (width out of null range)" % amt)
                rows.append(dict(amt=amt, refused=True))
                continue
            sc = r["resid_bright"] - base_floor
            rows.append(dict(amt=amt, score=sc, width=r["width"]))
            print("   usm %-5.2f -> %+8.4f%%   (edge width %.2f px)"
                  % (amt, 100 * sc, r["width"]))
        doc[s] = dict(tag=tag, cut=cut, floor=base_floor, n_sel=len(sel),
                      rows=rows)
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        del g0, clip, ref
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
