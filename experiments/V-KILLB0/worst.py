"""V-KILLB0 worst-structured-tile scan.

The claim is that the knob is inert where real structure dominates.  A single
counterexample kills it, so this looks for the worst one on every subject
instead of averaging the evidence away.

Tiles are 512px.  A tile is called STRUCTURED if its arm-A mid-frequency energy
(0.05-0.17 cyc/px, a band the knob barely touches, so the classification is
very nearly arm-independent) is in the top quartile for that subject.  Reported
per subject: the median fine ratio over structured tiles (the typical case) and
the minimum (the worst case), with the location so it can be looked at, plus
median/clip%/black% of the worst tile so a saturated or empty region cannot
masquerade as a clean result.
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

BOX = 512


def run(A, B, label):
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    h, w = la.shape
    fa = la - gaussian_filter(la, 0.6366)
    fb = lb - gaussian_filter(lb, 0.6366)
    mid = gaussian_filter(la, 2.0) - gaussian_filter(la, 8.0)
    rows = []
    for i in range(0, h - BOX + 1, BOX):
        for j in range(0, w - BOX + 1, BOX):
            sa = np.sqrt((fa[i:i+BOX, j:j+BOX] ** 2).mean())
            sb = np.sqrt((fb[i:i+BOX, j:j+BOX] ** 2).mean())
            st = np.sqrt((mid[i:i+BOX, j:j+BOX] ** 2).mean())
            if sa > 0:
                rows.append((st, sb / sa, i, j))
    rows.sort(key=lambda r: -r[0])
    n = max(1, len(rows) // 4)
    top = rows[:n]
    ratios = np.array([r[1] for r in top])
    worst = min(top, key=lambda r: r[1])
    i, j = worst[2], worst[3]
    ta = la[i:i+BOX, j:j+BOX]
    tb = lb[i:i+BOX, j:j+BOX]
    print(f"{label:<28} nTiles={len(rows):5d} structured={n:4d} "
          f"med={np.median(ratios):6.4f} p10={np.percentile(ratios,10):6.4f} "
          f"min={worst[1]:6.4f} @({i},{j}) "
          f"medDN={np.median(ta):6.0f} clip%={100*(ta>=65000).mean():5.2f} "
          f"blk%={100*(ta<=200).mean():5.2f} dMean%={100*(tb.mean()/ta.mean()-1):+6.3f}")
    return worst


def main():
    da, db = sys.argv[1], sys.argv[2]
    names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(db, "*.tiff")))
    print(f"{'subject':<28} {'nTiles':>11} {'struct':>9} {'med':>10} {'p10':>10} "
          f"{'min':>10}  location / tile stats")
    print("  ratio = arm-B fine(0.25-0.50) rms / arm-A, over STRUCTURED tiles only. "
          "1.0 = inert on structure.")
    for nm in names:
        pa = os.path.join(da, nm + ".tiff")
        if not os.path.exists(pa):
            continue
        try:
            run(pa, os.path.join(db, nm + ".tiff"), nm)
        except Exception as e:
            print(f"{nm:<28} ERROR {e}")


if __name__ == "__main__":
    main()
