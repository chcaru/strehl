r"""Choose the isolation strictness by an EXTERNAL known truth, not by taste.

The gauge read base rim +0.277 on leaf-2-cpl and could not recover a planted
blur of 1.2 px. Both symptoms have one cause: at FLATTEN=0.06 the admitted
sites are textured, and a max over a textured band is not an overshoot -- the
pathology rimindep.py already documents at +27% on a subject rimv6 calls clean.

The strictness is therefore swept and chosen by the criterion that the arm must
recover a PLANTED BLUR OF KNOWN SIZE. That truth is external to the A/B under
test, so tightening to satisfy it cannot bias the comparison. Choosing the cut
to make the A/B look better would be the opposite, and is not done here.

Also swept: a dark-side flatness requirement. Texture is two-sided; requiring
only the bright shoulder to settle admits sites that are ramping on the left.
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, median_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bg_lib as L                                                 # noqa: E402

K1090 = 2.0 * 1.2815515655446004
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bg_A.npy")


def load(path):
    if os.path.exists(CACHE):
        return np.load(CACHE)
    g = L.luma(tifffile.imread(path))
    np.save(CACHE, g)
    return g


def main():
    g = load(sys.argv[1])
    sites = L.select(gaussian_filter(g, 2.0))
    blur = gaussian_filter(g, 1.2)
    med = median_filter(g, size=(1, 5))
    couple = float(np.load(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "bg_couple.npy"))[0])
    print("using COUPLE = %+.3f px per unit rim (fitted on synthetic)\n" % couple)
    print("%8s %6s %8s %9s %11s %11s %11s"
          % ("FLATTEN", "n", "rim", "rise", "BLUR dsig", "MED dsig", "predicted"))
    print("-" * 74)
    for fl in (0.060, 0.030, 0.015, 0.008, 0.004, 0.002):
        L.FLATTEN = fl
        ctl = L.measure(g, sites)
        if ctl["n"] < 30:
            print("%8.3f %6d   REFUSED: fewer than 30 isolated edges" % (fl, ctl["n"]))
            continue
        keep = ctl["keep"]
        s0 = ctl["rise"] / K1090
        pred = K1090 * (float(np.hypot(s0, 1.2)) - s0)
        row = []
        for arm in (blur, med):
            m = L.measure(arm, sites, keep)
            resid = (m["rise"] - ctl["rise"]) - couple * (m["rim"] - ctl["rim"])
            row.append(resid / K1090)
        print("%8.3f %6d %+8.4f %9.3f %+11.3f %+11.3f %+11.3f"
              % (fl, ctl["n"], ctl["rim"], ctl["rise"], row[0], row[1],
                 pred / K1090))
    print("\nCHOOSE the strictest cut that recovers the planted blur within 35%")
    print("AND leaves >=30 edges. The planted blur is external truth; the A/B is not.")


if __name__ == "__main__":
    main()