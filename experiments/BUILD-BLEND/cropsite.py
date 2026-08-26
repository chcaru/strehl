"""Crop one site from both arms with a SHARED tone mapping and look at it.

ORCH reports solid black axis-aligned blocks 40-60 px across at
(6136, 1360) on dry-erase-marker-head-cpl, present in the pyramid arm and
absent in the control.

Two things this has to get right or the picture lies:

  * **One mapping for both arms.**  Any per-image normalisation would rescale
    each panel independently and could manufacture or hide a black block.  The
    scale is taken once, from the BEFORE arm, and applied to both.
  * **No clipping in the view transform.**  A viewing gamma that crushes the
    bottom would produce black blocks on its own.  The mapping here is a plain
    power law with the black point pinned at 0, and the fraction of the crop
    that lands at output 0 is printed for each arm so the reader can tell a
    rendering artifact from a data artifact.

A third panel marks pixels that are exactly 0 in the linear data, so the
"is it black because it clipped, or black because it is ink?" question is
answered in the figure rather than in prose.

Usage:  python cropsite.py <dir> <subject> <x> <y> [size]
"""

import os
import sys

import numpy as np
import tifffile
from PIL import Image

D = sys.argv[1]
SUBJ = sys.argv[2]
X = int(sys.argv[3])
Y = int(sys.argv[4])
SIZE = int(sys.argv[5]) if len(sys.argv) > 5 else 600


def crop(img, x, y, s):
    h, w = img.shape[:2]
    x0, y0 = max(0, x - s // 2), max(0, y - s // 2)
    x1, y1 = min(w, x0 + s), min(h, y0 + s)
    return img[y0:y1, x0:x1]


def view(a, scale, gamma=2.2):
    """Shared linear -> 8-bit view.  `scale` is supplied, never recomputed."""
    v = np.clip(a.astype(np.float64) / scale, 0.0, 1.0)
    return (255.0 * v ** (1.0 / gamma) + 0.5).astype(np.uint8)


def main():
    pb = os.path.join(D, f"{SUBJ}-estimator.tiff")
    pa = os.path.join(D, f"{SUBJ}-pyramid.tiff")
    B = tifffile.imread(pb)
    A = tifffile.imread(pa)
    print(f"BEFORE {B.shape}  AFTER {A.shape}")

    cb = crop(B, X, Y, SIZE)
    ca = crop(A, X, Y, SIZE)

    # One scale for both panels, taken from the BEFORE arm only.
    scale = float(np.percentile(cb, 99.5))
    print(f"shared view scale (BEFORE p99.5) : {scale:.0f} DN")

    vb, va = view(cb, scale), view(ca, scale)
    for name, c, v in (("BEFORE", cb, vb), ("AFTER", ca, va)):
        z = 100.0 * float((c == 0).sum()) / c.size
        vz = 100.0 * float((v == 0).sum()) / v.size
        print(f"  {name:<6} linear min {int(c.min()):>6} DN   "
              f"exact-zero {z:6.3f}%   view-black {vz:6.3f}%")

    # Panel 3: where the LINEAR data is exactly 0, in red over the AFTER view.
    mask = (ca == 0).any(axis=2)
    vm = va.copy()
    vm[mask] = [255, 0, 0]
    print(f"  zero-mask pixels marked          : {int(mask.sum())}")

    gap = np.full((vb.shape[0], 12, 3), 40, np.uint8)
    sheet = np.concatenate([vb, gap, va, gap, vm], axis=1)
    out = os.path.join(D, f"{SUBJ}-{X}x{Y}-crop.png")
    Image.fromarray(sheet).save(out)
    print(f"\nwrote {out}")
    print("panels: BEFORE (estimator) | AFTER (pyramid) | AFTER with linear zeros in red")


if __name__ == "__main__":
    main()
