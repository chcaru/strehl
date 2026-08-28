"""Does the crop render show the same scene as the scale render?

Usage:
    python crop_vs_scale.py <scale.tiff> <crop.tiff> <k> <x0> <y0> <W> <H>

`W x H` is the full plane. Scale mode composes `p -> c + k*(p - c)` about the
plane centre `c = (W/2, H/2)` into every placement, so the scale output pixel
`p` carries the reference-plane point `q = c + k*(p - c)`. Crop mode composes
nothing and emits the window at `(x0, y0)`, so its pixel `r` carries
`q = r + (x0, y0)`. Equating the two gives the map used here:

    p = c + (r + (x0, y0) - c) / k

The test resamples the scale image at `p` and compares against the crop image,
then repeats the comparison over a grid of sub-pixel offsets applied to `p`.
If the rectangle is right the residual is minimised at offset (0, 0); a
half-pixel error in `cover_rect` moves the minimum to +-0.5, which is exactly
the failure this is here to catch.
"""

import sys

import numpy as np
import tifffile


def bilinear(img, px, py):
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx = (px - x0)[..., None]
    fy = (py - y0)[..., None]
    a = img[y0, x0]
    b = img[y0, x0 + 1]
    c = img[y0 + 1, x0]
    d = img[y0 + 1, x0 + 1]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def main() -> int:
    scale_p, crop_p = sys.argv[1], sys.argv[2]
    k = float(sys.argv[3])
    x0, y0, W, H = (int(v) for v in sys.argv[4:8])
    s = np.asarray(tifffile.imread(scale_p)).astype(np.float64)
    c = np.asarray(tifffile.imread(crop_p)).astype(np.float64)
    cx, cy = W * 0.5, H * 0.5

    # A central patch of the crop image, kept well inside so no sub-pixel probe
    # can sample off the edge of the scale image.
    ch, cw = c.shape[0], c.shape[1]
    ph, pw = ch // 2, cw // 2
    ry0, rx0 = ch // 4, cw // 4
    ry = np.arange(ry0, ry0 + ph, dtype=np.float64)
    rx = np.arange(rx0, rx0 + pw, dtype=np.float64)
    RX, RY = np.meshgrid(rx, ry)
    target = c[ry0 : ry0 + ph, rx0 : rx0 + pw]

    print(f"scale {s.shape}  crop {c.shape}  k={k}  off=({x0},{y0})  plane {W}x{H}")
    print(f"patch {pw}x{ph} at crop ({rx0},{ry0})")
    rows = []
    for dy in (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0):
        for dx in (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0):
            PX = cx + (RX + x0 - cx) / k + dx
            PY = cy + (RY + y0 - cy) / k + dy
            pred = bilinear(s, PX, PY)
            r = np.abs(pred - target)
            rows.append((float(r.mean()), dx, dy))
    rows.sort()
    for m, dx, dy in rows[:5]:
        print(f"   dx={dx:+.2f} dy={dy:+.2f}  mean |resid| = {m:9.4f} DN")
    m, dx, dy = rows[0]
    print(f"   ARGMIN: dx={dx:+.2f} dy={dy:+.2f}")
    # Correlation at the nominal mapping, as a plain "same scene" statistic.
    PX = cx + (RX + x0 - cx) / k
    PY = cy + (RY + y0 - cy) / k
    pred = bilinear(s, PX, PY)
    a, b = pred.ravel(), target.ravel()
    r = np.corrcoef(a, b)[0, 1]
    print(f"   at (0,0): pearson r = {r:.8f}, mean|resid| = {np.abs(a - b).mean():.4f} DN, "
          f"level ratio = {b.mean() / a.mean():.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
