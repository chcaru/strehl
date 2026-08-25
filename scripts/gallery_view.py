"""Turn one 16-bit sRGB TIFF into a viewable JPEG at a stated long edge.

Deliberately tiny, and deliberately does NOTHING to the pixels beyond
downsampling and 16 -> 8 bit. All the rendering -- black point, white point,
contrast, colour matrix, transfer curve -- happens in the Rust develop path and
is recorded in the render log. If this script started adjusting images, the
gallery would stop being a picture of what `strehl` produces, which is the only
thing it is for.

The 16-bit read goes through `tifffile`, never `PIL.Image.open`. PIL silently
downconverts a 16-bit RGB TIFF to 8 bits on open, and that has corrupted results
in this project before. The assert below is the guard, and it is deliberately
not wrapped in a try/except fallback: a lossier reader that "works" is strictly
worse than a loud failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: gallery_view.py <in.tiff> <out.jpg> <long-edge-px>", file=sys.stderr)
        return 2
    src, dst, long_edge = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3])

    a = tifffile.imread(src)
    assert a.dtype == np.uint16, f"{src} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{src} has shape {a.shape}, expected HxWx3"

    # 16 -> 8 bit by truncation, matching what any viewer does. Rounding would
    # be marginally more accurate and would also mean the gallery no longer
    # shows what a viewer shows.
    im = Image.fromarray((a >> 8).astype(np.uint8), mode="RGB")
    im.thumbnail((long_edge, long_edge), Image.LANCZOS)
    # 95 is high enough that JPEG artifacts are not what anyone is looking at,
    # while keeping a 26-image gallery small enough to open at once.
    im.save(dst, quality=95, subsampling=0, optimize=True)
    print(f"{dst.name}  {im.size[0]}x{im.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
