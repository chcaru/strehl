r"""A PLANTED RIM IS SYMMETRIC. TEXTURE IS NOT.

An unsharp mask is a linear high-pass added back: it overshoots on the bright
side and undershoots on the dark side by the same amount. So does any ringing a
merge or a resample introduces. rimv6 measures both -- `bright` = max q over
+2..+7, `dark` = -min q over -7..-2 -- and rimaxis reports both, but the axis
convicts on `bright` alone.

If the thirteen carried a rim, bright and dark would move together. If they
carry texture that happens to sit on the bright side of the features the
selector picked, they will not.

MATCHED CONTROL: the identical ladder measures bright and dark on the SAME
edges of the SAME crop, so the ratio is a property of the arm and not of what
was sampled.
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

OUT = os.path.join(V.SCRATCH, "symmetry.json")
CROP = (1200, 3600, 2048, 2048)


def usm(g, amt, r=2.0):
    return g + amt * (g - ndimage.gaussian_filter(g, r))


def main():
    doc = {}
    print("== PLANTED RIM: bright and dark on the same edges ==")
    a = tifffile.imread(os.path.join(V.SHIP, "109MSDCF--SHIP-V4.tiff"))
    y, x, h, w = CROP
    a = a[y:y + h, x:x + w]
    g0 = rimaxis.lum_of(a)
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a
    rois = rimaxis.pick_rois(g0, clip, n=64)
    ref, sel, n_all, cut, fl = rimaxis.select_for(g0, clip, rois)
    print("   109MSDCF crop, %d edges, floor bright %+.4f%% dark %+.4f%%"
          % (len(sel), 100 * fl["resid_bright"], 100 * fl["resid_dark"]))
    print("   %8s %11s %11s %8s" % ("usm", "bright", "dark", "dark/bright"))
    rows = []
    for amt in (0.0, 0.5, 1.0, 2.0, 3.0, 4.0):
        r = rimaxis.measure_arm(usm(g0, amt).astype(np.float32), sel)
        if r is None:
            print("   %8.2f  REFUSED" % amt)
            continue
        b = r["resid_bright"] - fl["resid_bright"]
        d = r["resid_dark"] - fl["resid_dark"]
        db = (d - (rows[0]["dark"] if rows else d)) if rows else 0.0
        bb = (b - (rows[0]["bright"] if rows else b)) if rows else 0.0
        rows.append(dict(amt=amt, bright=b, dark=d))
        print("   %8.2f %+10.4f%% %+10.4f%% %8s"
              % (amt, 100 * b, 100 * d,
                 ("%.3f" % (db / bb)) if bb else "  --"))
    doc["planted"] = rows
    del g0, clip, ref

    print("\n== THE THIRTEEN, AS MEASURED, from experiments/V-GATHER/rim.json ==")
    d = json.load(io.open(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "V-GATHER", "rim.json"), encoding="utf-8"))
    print("   %-38s %10s %10s %8s" % ("subject", "bright", "dark", "dark/bright"))
    for k in sorted(d, key=lambda k: -(d[k].get("corrected_bright") or -9)):
        v = d[k]
        if "corrected_bright" not in v:
            continue
        b, dk = v["corrected_bright"], v["corrected_dark"]
        print("   %-38s %+9.3f%% %+9.3f%% %8s"
              % (k, 100 * b, 100 * dk, ("%.3f" % (dk / b)) if abs(b) > 1e-6 else "--"))
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
