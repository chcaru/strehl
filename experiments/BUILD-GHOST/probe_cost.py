#!/usr/bin/env python3
"""BUILD-GHOST probe 1: decode cost, so the compute budget is measured not guessed."""
from __future__ import annotations

import time

import numpy as np
import rawpy

P = r"D:\personal\macro\bee-3-cpl\DSC00001.ARW"

t = time.time()
with rawpy.imread(P) as r:
    v = r.raw_image_visible.copy()
print(f"decode raw_image_visible : {time.time() - t:.3f}s  {v.shape}")

t = time.time()
h, w = v.shape
h2, w2 = h // 2, w // 2
q = v[: h2 * 2, : w2 * 2].astype(np.float32).reshape(h2, 2, w2, 2)
g = 0.5 * (q[:, 0, :, 1] + q[:, 1, :, 0])  # pattern [[R,G],[G,B]] -> the two greens
print(f"bin to quad-green        : {time.time() - t:.3f}s  {g.shape}")

t = time.time()
import exifread

with open(P, "rb") as fh:
    tags = exifread.process_file(fh, details=False)
print(f"exif                     : {time.time() - t:.3f}s  {len(tags)} tags")
for k in sorted(tags):
    if any(s in k for s in ("ExposureTime", "FNumber", "ISO", "Aperture", "DateTime", "Model", "FocalLength", "Shutter")):
        print(f"    {k:38s} {tags[k]}")
