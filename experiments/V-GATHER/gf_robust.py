r"""Two ways the 'detail preserved' reading could be an artifact of my choices.

1. THE QUANTILE. 'detail' is the top decile of local variance. If the reading
   flips at a different cut, it is a property of the cut and not the picture.
2. ALIGNMENT. A one-pixel shift between arms would fabricate a band-energy
   difference. Integer-only, per the rule that sub-pixel resampling adds blur
   to the quantity being measured.
"""
import json
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter

import gf_measure as M
import gf_discriminate as D

OUT = r"C:\dev\strehl-out\V-GATHER\gatefloor"
SUBS = ["leaf-2-cpl", "109MSDCF", "112MSDCF", "flat-on-ruler-cpl"]


def detail_ratio(gw, gm, ref, q):
    loc = gaussian_filter(ref, 1.0)
    var = uniform_filter(loc ** 2, 33) - uniform_filter(loc, 33) ** 2
    var = np.clip(var, 0, None)
    m = var >= np.quantile(var, q)
    return D.band_rms(gm, m) / D.band_rms(gw, m), int(m.sum())


def main():
    print("%-20s %8s %8s %8s %8s %8s   %s"
          % ("subject", "q=0.50", "q=0.75", "q=0.90", "q=0.95", "q=0.99",
             "int shift"))
    print("-" * 78)
    for s in SUBS:
        fw = os.path.join(OUT, "%s--white.tiff" % s)
        fm = os.path.join(OUT, "%s--measured.tiff" % s)
        if not (os.path.exists(fw) and os.path.exists(fm)):
            print("%-20s NOT EXAMINED" % s)
            continue
        gw = M.luma(tifffile.imread(fw))
        gm = M.luma(tifffile.imread(fm))
        ref = gaussian_filter(0.5 * (gw + gm), 1.5)
        vals = []
        for q in (0.50, 0.75, 0.90, 0.95, 0.99):
            r, n = detail_ratio(gw, gm, ref, q)
            vals.append(r)
        sh, err = M.int_shift(gw, gm)
        print("%-20s %8.4f %8.4f %8.4f %8.4f %8.4f   %s"
              % (s, vals[0], vals[1], vals[2], vals[3], vals[4], sh))
        del gw, gm, ref
    print("\nA reading that survives 0.50..0.99 is not an artifact of the cut.")
    print("Any shift other than (0,0) would fabricate a band difference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
