"""M120 step 3 — PC1 deliverable: the SAME crop from the shipped render.

Uses the coarse silhouette offset measured in 02c (dy=+33, dx=-29, DoG NCC
0.690, beating everything >16 px away at 0.539). Region-level correspondence
only; no pixel-to-pixel claim is made between these two arms.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

M87 = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
OUT = Path(r"C:\dev\strehl-out\M120")
OUT.mkdir(parents=True, exist_ok=True)

ROI = (1200, 1900, 300, 1400)
MARGIN = 22
BOX = (ROI[0] - MARGIN, ROI[1] + MARGIN, ROI[2] - MARGIN, ROI[3] + MARGIN)
TIGHT = (330, 610, 150, 570)
SUB = (300, 800, 100, 800)


def png(a, path, lo, hi, gamma=2.2, scale=1):
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** (1.0 / gamma)
    im = Image.fromarray((v * 255).astype(np.uint8))
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def main() -> int:
    dy, dx = np.load(OUT / "pc1_offset.npy")
    dy, dx = int(dy), int(dx)
    sel = np.load(M87 / "bee3-leg-sel.npy").astype(np.float32)
    g2 = np.load(M87 / "bee3-leg-g2.npy").astype(np.float32)
    ship = tifffile.imread(M87 / "ship-before-linear.tif")[:, :, 1].astype(np.float32)

    lo, hi = np.percentile(sel[SUB[0] : SUB[1], SUB[2] : SUB[3]], (0.5, 99.7))
    print(f"M87 common stretch lo={lo:.0f} hi={hi:.0f}   offset dy={dy} dx={dx}")

    y0, y1, x0, x1 = TIGHT
    sel_t = sel[y0:y1, x0:x1]
    g2_t = g2[y0:y1, x0:x1]
    ship_t = ship[BOX[0] + dy + y0 : BOX[0] + dy + y1, BOX[2] + dx + x0 : BOX[2] + dx + x1]

    # affine level match on the crop, so the comparison is of structure
    A = np.vstack([ship_t.ravel(), np.ones(ship_t.size)]).T
    coef, *_ = np.linalg.lstsq(A, sel_t.ravel().astype(np.float64), rcond=None)
    ship_m = coef[0] * ship_t + coef[1]
    print(f"level match: sel ~= {coef[0]:.5f} * ship + {coef[1]:.1f}")

    png(sel_t, OUT / "PC1-A-M87python-gate0-argmax.png", lo, hi, scale=2)
    png(g2_t, OUT / "PC1-B-M87python-gate2.png", lo, hi, scale=2)
    png(ship_m, OUT / "PC1-C-SHIPPED-strehl-gate4.png", lo, hi, scale=2)
    for tag, arr in (("A", sel_t), ("B", g2_t), ("C", ship_m)):
        print(f"  {tag}: mean={arr.mean():.1f}  sd={arr.std():.1f}")
    print(f"wrote 3 crops to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
