#!/usr/bin/env python3
"""BUILD-GHOST probe 0: establish the shapes and levels we will measure on.

Prints, for one RAW and one delivered master:
  * the CFA mosaic geometry, pattern, black and white levels (camera-linear),
  * the delivered TIFF's dtype and shape,
so that every later number in this workstream has a stated grid.

Nothing here is a measurement of the question; it is the ruler check.
"""
from __future__ import annotations

import sys

import numpy as np
import rawpy
import tifffile


def probe_raw(path: str) -> None:
    print(f"RAW  {path}")
    with rawpy.imread(path) as r:
        print(f"  raw_image           {r.raw_image.shape} {r.raw_image.dtype}")
        print(f"  raw_image_visible   {r.raw_image_visible.shape}")
        print(f"  sizes               {r.sizes}")
        print(f"  raw_pattern\n{r.raw_pattern}")
        print(f"  color_desc          {r.color_desc}")
        print(f"  black_level_per_ch  {r.black_level_per_channel}")
        print(f"  white_level         {r.white_level}")
        print(f"  camera_whitebalance {r.camera_whitebalance}")
        v = r.raw_image_visible
        print(f"  visible min/med/max {v.min()} {np.median(v)} {v.max()}")


def probe_tiff(path: str) -> None:
    print(f"TIFF {path}")
    with tifffile.TiffFile(path) as tf:
        p = tf.pages[0]
        print(f"  shape {p.shape} dtype {p.dtype} photometric {p.photometric}")
        for tag in p.tags.values():
            if tag.name in ("ImageDescription", "Software", "BitsPerSample"):
                val = str(tag.value)
                print(f"  {tag.name}: {val[:400]}")


if __name__ == "__main__":
    probe_raw(sys.argv[1])
    probe_tiff(sys.argv[2])
