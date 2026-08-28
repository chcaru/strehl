"""V-KILLB0 benefit/cost ladder.

Puts the win and the damage on ONE axis so the trade can be seen.  Tiles are
split by arm-A mid-frequency energy: bottom quartile = FLAT (where a grain win
lives), top quartile = STRUCTURED (where a softening would live).  If the
"self-targeting" story is true, FLAT should fall a lot and STRUCTURED should
sit at 1.000.  Absolute DN amplitudes are printed next to every ratio, because
a large ratio change on a 90 DN signal and a large ratio change on a 460 DN
signal are not the same event.
"""
import glob
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

BOX = 512


def run(A, B, label, arm):
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
                rows.append((st, sa, sb, sb / sa))
    rows.sort(key=lambda r: r[0])
    n = max(1, len(rows) // 4)
    flat, struct = rows[:n], rows[-n:]
    fr = np.median([r[3] for r in flat]); fa_dn = np.median([r[1] for r in flat])
    sr = np.median([r[3] for r in struct]); sa_dn = np.median([r[1] for r in struct])
    print(f"{label:<26} {arm:>5} FLAT {fr:7.4f} (A={fa_dn:6.1f}DN -> {fa_dn*fr:6.1f}DN)"
          f"   STRUCT {sr:7.4f} (A={sa_dn:6.1f}DN -> {sa_dn*sr:6.1f}DN)"
          f"   medianDN={np.median(la):6.0f} clip%={100*(la>=65000).mean():5.2f} "
          f"blk%={100*(la<=200).mean():5.2f}")


def main():
    da = sys.argv[1]
    arms = sys.argv[2:]
    print("FLAT   = median fine-band ratio over the LEAST structured quartile of 512px tiles (the win)")
    print("STRUCT = median fine-band ratio over the MOST  structured quartile (the cost). "
          "1.0000 = inert on structure.")
    names = sorted(os.path.basename(p)[:-5]
                   for p in glob.glob(os.path.join(da.replace('default', arms[0]), "*.tiff")))
    for nm in names:
        for arm in arms:
            pb = os.path.join(os.path.dirname(da), arm, nm + ".tiff")
            pa = os.path.join(da, nm + ".tiff")
            if os.path.exists(pa) and os.path.exists(pb):
                run(pa, pb, nm, arm)
        print()


if __name__ == "__main__":
    main()
