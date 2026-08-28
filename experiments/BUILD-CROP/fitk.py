"""Fit the coverage scale k empirically from a crop/scale render pair.

Usage:
    python fitk.py <scale.tiff> <crop.tiff> <k0> <x0> <y0> <W> <H>

The banner rounds k to four decimals. That is fine for reading and not fine
for resampling one 3246 px render onto another: at 1600 px from the centre a
k error of 1e-4 is a 0.19 px shift, which is enough to fake an edge effect.
This scans k around the printed value, minimising the residual against the
crop render over the WHOLE frame (the edges are where k matters), and reports
the minimising k so the band test can use a mapping that is actually correct.
"""

import sys

import numpy as np
import tifffile


def bilinear(img, px, py):
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx = (px - x0)[..., None]
    fy = (py - y0)[..., None]
    a, b = img[y0, x0], img[y0, x0 + 1]
    c, d = img[y0 + 1, x0], img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def main() -> int:
    s = np.asarray(tifffile.imread(sys.argv[1])).astype(np.float64)[..., 1]
    c = np.asarray(tifffile.imread(sys.argv[2])).astype(np.float64)[..., 1]
    k0 = float(sys.argv[3])
    x0, y0, W, H = (int(v) for v in sys.argv[4:8])
    cx, cy = W * 0.5, H * 0.5
    ch, cw = c.shape
    RX, RY = np.meshgrid(np.arange(cw, dtype=np.float64), np.arange(ch, dtype=np.float64))
    s3 = s[..., None]
    best = None
    print(f"scanning k around {k0}")
    for dk in np.arange(-6e-4, 6.01e-4, 5e-5):
        k = k0 + dk
        PX = np.clip(cx + (RX + x0 - cx) / k, 0.0, s.shape[1] - 1.001)
        PY = np.clip(cy + (RY + y0 - cy) / k, 0.0, s.shape[0] - 1.001)
        pred = bilinear(s3, PX, PY)[..., 0]
        r = float(np.abs(pred - c).mean())
        if best is None or r < best[0]:
            best = (r, k)
        print(f"   k={k:.6f}  mean|resid| = {r:9.4f} DN")
    print(f"   BEST k = {best[1]:.6f}  (mean |resid| {best[0]:.4f} DN)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
