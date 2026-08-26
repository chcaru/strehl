"""Downsampled overview of a master with a MERGE-pixel coordinate grid.

Purpose: choose probe sites by LOOKING at the picture, then feed their exact
coordinates to sitescan.py.  Nothing here is a measurement -- it exists so a
site can be named honestly ("the engraved mark at 3120,2260") instead of
"somewhere in block (2,2)".

Reads the camera-linear render, not the --srgb master, and applies a display
gamma purely so the eye can see it.  The gamma is presentation only; no number
is ever taken from this image.
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

GRID = 500          # merge px between gridlines
LONG = 1800         # long edge of the overview


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--grid", type=int, default=GRID)
    ap.add_argument("--crop", default="",
                    help="X0,Y0,W,H in merge px -- overview of a sub-region")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    path = os.path.join(tri.LIN, args.subject + ".tiff")
    img = tri.load16(path)
    y = tri.luma(img)
    h, w = y.shape
    x0 = y0 = 0
    if args.crop:
        x0, y0, cw, ch = (int(v) for v in args.crop.split(","))
        assert 0 <= x0 < w and 0 <= y0 < h, f"crop origin outside {w}x{h}"
        img = img[y0:y0 + ch, x0:x0 + cw]
        h, w = img.shape[:2]

    # Presentation-only display transform: normalise then gamma.  Stated loudly
    # because this project's most expensive recurring error is measuring across
    # exactly such a curve.
    a = img.astype(np.float64)
    hi = float(np.percentile(a, 99.7)) or 1.0
    disp = np.clip(a / hi, 0, 1) ** (1 / 2.2)
    scale = LONG / max(h, w)
    sh, sw = max(1, int(h * scale)), max(1, int(w * scale))
    im = Image.fromarray((disp * 255).astype(np.uint8)).resize(
        (sw, sh), Image.LANCZOS)

    dr = ImageDraw.Draw(im)
    g = args.grid
    for gx in range(int(np.ceil(x0 / g)) * g, x0 + w, g):
        px = (gx - x0) * scale
        dr.line([(px, 0), (px, sh)], fill=(255, 80, 80), width=1)
        dr.text((px + 2, 2), str(gx), fill=(255, 220, 60))
    for gy in range(int(np.ceil(y0 / g)) * g, y0 + h, g):
        py = (gy - y0) * scale
        dr.line([(0, py), (sw, py)], fill=(255, 80, 80), width=1)
        dr.text((2, py + 2), str(gy), fill=(255, 220, 60))
    dr.text((2, sh - 12),
            f"{args.subject}  merge px {x0},{y0} +{w}x{h}  grid {g} px"
            f"  [PRESENTATION ONLY -- no number is taken from this image]",
            fill=(120, 255, 120))

    out = args.out or os.path.join(tri.OUT, "sitepick", args.subject + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, quality=92)
    print(f"{args.subject}: {w}x{h} at ({x0},{y0}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
