"""Is black fill from outside the crop rectangle bleeding into it?

Usage:
    python bleedband.py <scale.tiff> <crop.tiff> <k> <x0> <y0> <W> <H>

In `scale` mode every frame is shrunk until it covers the whole plane, so the
merge sees no black fill anywhere. In `crop` mode the merge still runs on the
full plane and the region no frame reaches is filled, then discarded by the
window. A merge whose support is wider than a pixel -- the pyramid's coarse
bands are the worry -- could drag that fill inward past the rectangle edge.

Both renders carry the same scene, so their ratio should be flat. This prints
mean(crop) / mean(scale resampled to the crop grid) in bands at increasing
distance from the crop border. A bleed shows up as a ratio below one at the
edge that climbs towards one in the interior.
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
    s = np.asarray(tifffile.imread(sys.argv[1])).astype(np.float64)
    c = np.asarray(tifffile.imread(sys.argv[2])).astype(np.float64)
    k = float(sys.argv[3])
    x0, y0, W, H = (int(v) for v in sys.argv[4:8])
    cx, cy = W * 0.5, H * 0.5
    ch, cw = c.shape[0], c.shape[1]
    RX, RY = np.meshgrid(
        np.arange(cw, dtype=np.float64), np.arange(ch, dtype=np.float64)
    )
    # Clamp one pixel inside so the bilinear fetch cannot run off the far edge.
    PX = np.clip(cx + (RX + x0 - cx) / k, 0.0, s.shape[1] - 1.001)
    PY = np.clip(cy + (RY + y0 - cy) / k, 0.0, s.shape[0] - 1.001)
    pred = bilinear(s, PX, PY)
    dist = np.minimum(np.minimum(RX, cw - 1 - RX), np.minimum(RY, ch - 1 - RY))
    print(f"crop {cw}x{ch}, bands by distance to the crop border (green channel)")
    print(f"{'band px':>12}  {'n':>10}  {'crop mean':>11}  {'scale mean':>11}  {'ratio':>9}")
    edges = [(0, 2), (2, 4), (4, 8), (8, 16), (16, 32), (32, 64), (64, 128), (128, 10**9)]
    for lo, hi in edges:
        m = (dist >= lo) & (dist < hi)
        a = c[..., 1][m]
        b = pred[..., 1][m]
        lbl = f"{lo}-{hi}" if hi < 10**8 else f"{lo}+"
        print(f"{lbl:>12}  {a.size:>10}  {a.mean():11.2f}  {b.mean():11.2f}  {a.mean() / b.mean():9.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
