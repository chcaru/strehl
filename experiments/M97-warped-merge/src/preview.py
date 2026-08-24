"""Downscale a 16-bit TIFF render to an 8-bit PNG so it can actually be looked at.

Usage: preview.py <in.tif> <out.png> [max_edge] [x0 y0 w h]

A crop is given in FULL-RESOLUTION pixels of the source render.
"""

import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main() -> None:
    src, dst = sys.argv[1], sys.argv[2]
    max_edge = int(sys.argv[3]) if len(sys.argv) > 3 else 1400
    im = Image.open(src)
    a = np.asarray(im)
    if len(sys.argv) > 7:
        x0, y0, w, h = (int(v) for v in sys.argv[4:8])
        a = a[y0 : y0 + h, x0 : x0 + w]
    print(f"{src}: shape={a.shape} dtype={a.dtype} min={a.min()} max={a.max()}")
    if a.dtype == np.uint16:
        a8 = (a.astype(np.float32) / 65535.0 * 255.0).round().clip(0, 255).astype(np.uint8)
    else:
        a8 = a.astype(np.uint8)
    out = Image.fromarray(a8)
    out.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    out.save(dst)
    print(f"wrote {dst}  {out.size[0]}x{out.size[1]}")


if __name__ == "__main__":
    main()
