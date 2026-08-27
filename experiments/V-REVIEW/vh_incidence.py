"""Exact incidence for the claim's four headline subjects.  The hull test is a
LOWER BOUND: ringing that stays inside the master's local range is real and
uncounted.  Report the floor honestly."""
import sys, os
import numpy as np, tifffile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vh_hull as V

print("%-16s %9s %8s %8s %9s %9s" % ("subject", "gallery", "max+DN", "max-DN", "n>2DN", "ppm"))
for subj in ["lead-1-cpl", "109MSDCF", "tweezers-cpl", "lavendar-cpl",
             "foam", "coffee-bubbles", "flowers-cpl"]:
    a8 = V.to8(tifffile.imread(os.path.join(V.SHIP_V4, subj + "--SHIP-V4.tiff")))
    tot, mx, mn, npx = 0, 0.0, 0.0, 0
    for c in range(3):
        p = a8[:, :, c]
        hi, lo = V.hull_bounds(p)
        out = V.reduce_f(p, "lanczos")
        e = np.maximum(out - hi, 0.0)
        d = np.maximum(lo - out, 0.0)
        both = np.maximum(e, d)
        mx = max(mx, float(e.max())); mn = max(mn, float(d.max()))
        npx = max(npx, int((both > 2.0).sum()))
        tot = both.size
    print("%-16s %9d %8.2f %8.2f %9d %9.1f" % (subj, tot, mx, mn, npx, 1e6 * npx / tot))
