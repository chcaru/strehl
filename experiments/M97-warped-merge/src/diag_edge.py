"""Diagnostic: overlay the tracked baseline edge on the render, and dump the
residual profile. An instrument that has not been looked at is not an
instrument.

Usage: diag_edge.py <render.tif> <out.png>
"""

import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from geometry import find_baseline_band, luma, reject_tall_ticks, subpixel_top_edge  # noqa: E402

Image.MAX_IMAGE_PIXELS = None


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    img = luma(src)
    y0, y1 = find_baseline_band(img)
    ys, strength = subpixel_top_edge(img, y0, y1)
    ok = reject_tall_ticks(img, ys, y0)
    ok &= strength > np.nanmedian(strength[ok]) * 0.25
    x = np.arange(len(ys), dtype=np.float64)

    print(f"band = {y0}..{y1}   centre {(y0 + y1) // 2}")
    print(f"columns total {len(ys)}, non-nan {int(np.sum(~np.isnan(ys)))}, ok {int(ok.sum())}")
    yv = ys[ok]
    print(f"edge y: min {np.nanmin(yv):.1f}  p1 {np.nanpercentile(yv, 1):.1f}  "
          f"median {np.nanmedian(yv):.1f}  p99 {np.nanpercentile(yv, 99):.1f}  max {np.nanmax(yv):.1f}")
    c = np.polyfit(x[ok], yv, 1)
    r = yv - np.polyval(c, x[ok])
    print(f"line fit: slope {c[0]:+.6e}  rms resid {np.sqrt(np.mean(r**2)):.3f} px")
    for q in (0.1, 1, 5, 50, 95, 99, 99.9):
        print(f"  resid p{q:<5} {np.percentile(r, q):+9.2f}")

    # Overlay: mark the tracked edge in a downscaled copy.
    a = np.asarray(Image.open(src))
    if a.ndim == 3:
        a = a[..., 1]
    a = a.astype(np.float32)
    a = (a / a.max() * 255).clip(0, 255)
    rgb = np.dstack([a, a, a]).astype(np.uint8)
    for xi in range(len(ys)):
        if np.isnan(ys[xi]):
            continue
        yi = int(round(ys[xi]))
        if 0 <= yi < rgb.shape[0]:
            colour = (255, 0, 0) if ok[xi] else (0, 128, 255)
            for dy in (-2, -1, 0, 1, 2):
                if 0 <= yi + dy < rgb.shape[0]:
                    rgb[yi + dy, xi] = colour
    crop = rgb[max(0, y0 - 120) : min(rgb.shape[0], y1 + 120), :, :]
    im = Image.fromarray(crop)
    im.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    im.save(dst)
    print(f"wrote {dst} {im.size}")


if __name__ == "__main__":
    main()
