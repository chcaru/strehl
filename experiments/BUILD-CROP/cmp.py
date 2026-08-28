"""Compare a cropped render against a window of a full-plane render.

Usage:
    python cmp.py <full.tiff> <crop.tiff> <x> <y>

Prints the exact-match count, the max absolute difference and a few
percentiles, on the 16-bit integers as written -- no float rescaling, because
the question is whether the bytes are the same, not whether they are close in
some tolerant sense.
"""

import sys

import numpy as np
import tifffile


def main() -> int:
    full_p, crop_p, x, y = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    full = np.asarray(tifffile.imread(full_p))
    crop = np.asarray(tifffile.imread(crop_p))
    print(f"full {full_p}  {full.shape} {full.dtype}")
    print(f"crop {crop_p}  {crop.shape} {crop.dtype}")
    h, w = crop.shape[0], crop.shape[1]
    win = full[y : y + h, x : x + w]
    if win.shape != crop.shape:
        print(f"SHAPE MISMATCH window {win.shape} vs crop {crop.shape}")
        return 2
    a = win.astype(np.int64)
    b = crop.astype(np.int64)
    d = np.abs(a - b)
    n = d.size
    eq = int((d == 0).sum())
    print(f"window at ({x},{y}) size {w}x{h}, {n} samples")
    print(f"  exact-equal samples : {eq} / {n}  ({100.0 * eq / n:.4f} %)")
    print(f"  max |diff|          : {int(d.max())} DN")
    print(f"  mean |diff|         : {d.mean():.6f} DN")
    for q in (50, 90, 99, 99.9):
        print(f"  p{q} |diff|         : {np.percentile(d, q):.3f} DN")
    print(f"  VERDICT             : {'BIT-IDENTICAL' if eq == n else 'DIFFERS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
