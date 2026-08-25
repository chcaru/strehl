"""M120 step 2c — coarse registration on the LEG SILHOUETTE only.

Fine-scale registration between M87's unaligned per-pixel-argmax merge and the
shipped aligned render is IMPOSSIBLE IN PRINCIPLE: `sel` gathers each pixel from
whichever unwarped frame won, so its geometry is a patchwork of frames and no
single global offset exists. Measured: high-pass NCC peaks at 0.030.

What IS well defined is the coarse silhouette. This finds that offset with a
band-pass (difference-of-Gaussians) NCC over a wide search, so a background
REGION can be located in both images to within a few px. Region statistics are
what M120 compares; no pixel-to-pixel overlay is claimed between these two arms.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage as ndi

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")

ROI = (1200, 1900, 300, 1400)
MARGIN = 22
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)


def dog(a, s1=4.0, s2=32.0):
    a = a.astype(np.float32)
    return ndi.gaussian_filter(a, s1) - ndi.gaussian_filter(a, s2)


def main() -> int:
    sel = np.load(M87 / "bee3-leg-sel.npy").astype(np.float32)
    ship = tifffile.imread(M87 / "ship-before-linear.tif")[:, :, 1].astype(np.float32)
    h, w = sel.shape

    a = dog(sel)
    a = a[64:-64, 64:-64]
    a -= a.mean()
    an = np.sqrt((a * a).sum())
    ah, aw = a.shape

    S = 160
    best = (-2.0, 0, 0)
    surf = np.full((2 * S // 4 + 1, 2 * S // 4 + 1), -2.0, np.float32)
    big = ship[BOX[0] - S : BOX[0] + h + S, BOX[2] - S : BOX[2] + w + S]
    bd = dog(big)
    for i, oy in enumerate(range(-S, S + 1, 4)):
        for j, ox in enumerate(range(-S, S + 1, 4)):
            m = bd[S + oy + 64 : S + oy + 64 + ah, S + ox + 64 : S + ox + 64 + aw]
            m = m - m.mean()
            den = np.sqrt((m * m).sum()) * an
            s = float((a * m).sum() / den) if den > 0 else -2.0
            surf[i, j] = s
            if s > best[0]:
                best = (s, oy, ox)
    score, oy, ox = best
    print(f"coarse DoG NCC peak = {score:.4f} at (dy={oy}, dx={ox})   [4 px grid, +/-{S}]")
    flat = np.sort(surf.ravel())[::-1]
    print(f"  runner-up over the whole surface = {flat[1]:.4f}, 10th = {flat[9]:.4f}")
    yy, xx = np.mgrid[-S : S + 1 : 4, -S : S + 1 : 4]
    far = (np.abs(yy - oy) > 16) | (np.abs(xx - ox) > 16)
    print(f"  best value > 16 px from the peak = {surf[far].max():.4f}")
    print(f"  NCC at identity (0,0) = {surf[S // 4, S // 4]:.4f}")

    # refine on a 1 px grid within +/-6
    bestf = (-2.0, oy, ox)
    for dy2 in range(oy - 6, oy + 7):
        for dx2 in range(ox - 6, ox + 7):
            m = bd[S + dy2 + 64 : S + dy2 + 64 + ah, S + dx2 + 64 : S + dx2 + 64 + aw]
            m = m - m.mean()
            den = np.sqrt((m * m).sum()) * an
            s = float((a * m).sum() / den) if den > 0 else -2.0
            if s > bestf[0]:
                bestf = (s, dy2, dx2)
    print(f"refined: NCC = {bestf[0]:.4f} at (dy={bestf[1]}, dx={bestf[2]})")
    np.save(OUT / "pc1_offset.npy", np.array([bestf[1], bestf[2]]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
