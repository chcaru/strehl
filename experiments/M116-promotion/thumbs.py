"""Downscale the scout renders to small PNGs so a human can see what each
candidate subject actually depicts.

Subject selection only. No metric is computed here.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

SRC = Path(r"C:\dev\strehl-out\M116\scout")


def main() -> int:
    for tif in sorted(SRC.glob("*.tif")):
        a = tifffile.imread(tif)
        if a.dtype == np.uint16:
            a = (a >> 8).astype(np.uint8)
        img = Image.fromarray(a)
        img.thumbnail((900, 900))
        out = SRC / (tif.stem + ".png")
        img.save(out)
        print(f"{tif.name:48s} {a.shape} -> {out.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
