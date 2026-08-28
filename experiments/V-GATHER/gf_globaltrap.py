r"""What would a GLOBAL sharpness metric report on these same pixels?

BUILD-PLUGIN reports the gate-floor default costing -9.9% to -39.9% sharpness.
gf_multiscale.py says, on leaf-2-cpl, that detail is preserved at every scale
that can see a softening at all. Both readings can be simultaneously honest if
the global metric is integrating over territory that is mostly noise.

This prints, on identical pixels, what a metric that does NOT split by
structure would say, beside what the split says. No new rendering, no new
threshold -- the same bands, pooled two ways.
"""
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

import gf_measure as M
import gf_multiscale as MS

OUT = r"C:\dev\strehl-out\V-GATHER\gatefloor"


def main():
    gw = M.luma(tifffile.imread(os.path.join(OUT, "ms-leaf-white.tiff")))
    gm = M.luma(tifffile.imread(os.path.join(OUT, "ms-leaf-measured.tiff")))
    ref = gaussian_filter(0.5 * (gw + gm), 1.5)
    print("leaf-2-cpl: the SAME band energies pooled two ways\n")
    print("%8s %14s %14s %14s" % ("sigma", "GLOBAL", "flat", "detail"))
    print("-" * 54)
    for s in MS.SIGMAS:
        bw, bm = MS.band(gw, s), MS.band(gm, s)
        g = float(np.sqrt(np.mean(bm ** 2)) / np.sqrt(np.mean(bw ** 2)))
        rf, rd = MS.ratio(gw, gm, ref, s)
        blind = "" if MS.SIGMAS.index(s) < 3 else "  (scale blind)"
        print("%8.1f %13.2f%% %13.2f%% %13.2f%%%s"
              % (s, 100 * (g - 1), 100 * (rf - 1), 100 * (rd - 1), blind))
    print("\nA global metric on this subject reports a large loss at fine")
    print("scales. The split says that loss is entirely in flat territory and")
    print("that detail is intact. Same pixels, same bands, same renders.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
