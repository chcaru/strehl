"""Can the pyramid's BASE band serve as a geometry reference between the arms?

THE STRUCTURAL CLAIM, taken from the binary's own banner and not from a
document: the merge is "7 Laplacian levels + 1 base" and the "base band : plain
mean across frames".  The selection exponent weights the LAPLACIAN levels.  If
that is true of the shipped code, then the base band is the same plain mean in
both arms, and a hard low-pass that keeps only the base should be very nearly
ARM-INVARIANT -- which makes it a geometry reference that is immune to the
content difference the arms are built to have, and that is precisely what
defeated the SSD-argmin guard.

This is falsifiable and this script falsifies or confirms it.  If the claim
holds, the residual between low-passed arms is tiny compared with the residual
between low-passed arm and low-passed SHIFTED arm, and the SSD argmin on the
low-passed pair sits crisply at (0, 0) with a deep well on every subject
including the three the old guard refused.  If it does not hold, the numbers
will say so and this idea is dead.

The control arm is the point: a 1 px and a 32 px planted shift must both be
visible in the low-passed SSD well, or the test cannot detect the thing it is
being proposed for.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from flatexp import DEF_DIR, FLAT_DIR, CROP, content_sites  # noqa: E402

SIGMA = 24.0          # well inside the base band for a 7040 px wide render
PAD = 64              # search margin


def lowpass(plane):
    return gaussian_filter(plane.astype(np.float32), SIGMA, mode="nearest")


def ssd_surface(la, lb, y, x, radius=4):
    pa = la[y:y + CROP, x:x + CROP]
    out = {}
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            pb = lb[y + dy:y + dy + CROP, x + dx:x + dx + CROP]
            if pb.shape != pa.shape:
                continue
            out[(dy, dx)] = float(np.mean((pa - pb) ** 2))
    return out


def report(tag, la, lb, sites):
    argmins, excesses, depths = [], [], []
    for (y, x) in sites:
        s = ssd_surface(la, lb, y, x)
        zero, mn = s[(0, 0)], min(s.values())
        am = min(s, key=s.get)
        ring = min(v for k, v in s.items() if max(abs(k[0]), abs(k[1])) == 1)
        argmins.append(am)
        excesses.append((zero / mn - 1.0) * 100.0 if mn > 0 else 0.0)
        depths.append(ring / zero if zero > 0 else float("inf"))
    print(f"  {tag:<34} argmins={sorted(set(argmins))}  "
          f"median excess={np.median(excesses):8.4f}%  "
          f"median ring/zero={np.median(depths):7.4f}")
    return float(np.median(excesses)), float(np.median(depths))


def main(names):
    if not names:
        names = ["coffee-bubbles", "flowers-cpl", "flower-bud-alone-cpl",
                 "dry-erase-marker-head-cpl"]
    for name in names:
        dp = DEF_DIR / f"{name}--DEF-2f858c62.tiff"
        fp = FLAT_DIR / f"{name}--FLAT1-2f858c62.tiff"
        if not (dp.exists() and fp.exists()):
            print(f"\n== {name}: MISSING")
            continue
        a = tifffile.imread(dp)
        b = tifffile.imread(fp)
        sites = [(y, x) for (y, x) in content_sites(a)
                 if y - PAD >= 0 and x - PAD >= 0
                 and y + CROP + PAD <= a.shape[0] and x + CROP + PAD <= a.shape[1]]
        if not sites:
            print(f"\n== {name}: no site survives a {PAD}px margin")
            continue

        ga = a[:, :, 1]
        gb = b[:, :, 1]
        la, lb = lowpass(ga), lowpass(gb)
        print(f"\n== {name}  sites={len(sites)}  sigma={SIGMA}")
        print("  -- raw green plane, for comparison --")
        report("RAW    default vs flat-1", ga.astype(np.float32),
               gb.astype(np.float32), sites)
        print("  -- low-passed into the base band --")
        e0, d0 = report("LP     default vs flat-1", la, lb, sites)
        # CONTROLS: the test must SEE a planted shift, or it is not a test.
        for s in (1, 4, 32):
            shifted = np.roll(lb, s, axis=0)
            report(f"LP     default vs flat-1 + {s}px", la, shifted, sites)


if __name__ == "__main__":
    main(sys.argv[1:])
