"""Coordinate grid over ORCH's exact region, so boxes are chosen by reading
them off the figure rather than guessed."""
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee\GRID.png")
X0, Y0, W, H = 700, 3150, 1100, 900


def main():
    a = tifffile.imread(SRC)
    g = a[Y0:Y0 + H, X0:X0 + W, 1].astype(np.float32)
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    u8 = np.clip((g - med) / span * 127.0 + 127.0, 0, 255).astype(np.uint8)
    im = Image.fromarray(np.dstack([u8] * 3)).convert("RGB")
    d = ImageDraw.Draw(im)
    for x in range(0, W, 100):
        d.line([(x, 0), (x, H)], fill=(255, 60, 60), width=1)
        d.text((x + 3, 3), str(x), fill=(255, 90, 90))
    for y in range(0, H, 100):
        d.line([(0, y), (W, y)], fill=(60, 160, 255), width=1)
        d.text((3, y + 3), str(y), fill=(90, 180, 255))
    im.save(OUT)
    print(f"wrote {OUT}  (crop coords, add ({X0},{Y0}) for full-frame)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
