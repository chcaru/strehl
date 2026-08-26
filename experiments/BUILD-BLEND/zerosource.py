"""Where do the exact-zero pixels actually come from?

The clamped/unclamped A/B (clampcause.py) showed the shipping arm's LINEAR
merge output has ZERO exact-zero pixels, while ORCH measured 723,429 (2.192%)
and described the source as "linear 16-bit merge output -- upstream of the tone
stage, so no per-image black point can reach it".

Both cannot be true of the same bytes. This checks the remaining candidate: the
tone stage. image_out.rs maps each image's own measured [black, white] window
onto [0,1], so every pixel at or below `black` becomes exactly 0. That is a
zero-manufacturing mechanism, and it is per-image -- so two arms with different
black points crush different amounts, which would show up as a merge difference
that is not one.

Reads the tone parameters out of each file's own ImageDescription rather than
assuming, and counts zeros in the same pass.
"""
import re
import sys
from pathlib import Path

import numpy as np
import tifffile

FILES = [
    ("linear  (blend-render --linear)",
     Path(r"C:\dev\strehl-out\BUILD-BLEND\clip\fb-clamped.tiff")),
    ("srgb    (strehl stack --srgb)",
     Path(r"C:\dev\strehl-out\BUILD-BLEND\flip\flower-bud-alone-cpl--pyramid.tiff")),
    ("srgb    (estimator control)",
     Path(r"C:\dev\strehl-out\BUILD-BLEND\flip\flower-bud-alone-cpl--estimator.tiff")),
]

TONE = re.compile(r"black\s+([0-9.]+),\s*white\s+([0-9.]+)")

for label, p in FILES:
    if not p.exists():
        print(f"{label:<36} MISSING {p}")
        continue
    with tifffile.TiffFile(p) as tf:
        desc = tf.pages[0].description or ""
        a = tf.asarray()
    m = TONE.search(desc)
    tone = (f"black {m.group(1)} white {m.group(2)}" if m
            else "NO TONE WINDOW IN HEADER -> untoned")
    h, w, _ = a.shape
    total = h * w
    print(f"\n{label}")
    print(f"  {p.name}")
    print(f"  tone: {tone}")
    for ci, cn in enumerate("RGB"):
        ch = a[:, :, ci]
        z = int((ch == 0).sum())
        print(f"    {cn}: == 0 {z:>10,}  ({100*z/total:6.3f}%)   "
              f"<=16 {int((ch<=16).sum()):>10,}")

print()
print("=" * 70)
print("READING")
print("=" * 70)
print("""  If the untoned linear render has no zeros and the toned renders do, then
  the exact-zero pixels are manufactured by the tone stage's black-point
  subtraction and are not a property of the merge. In that case the correct
  comparison between arms is on untoned output, and a zero count taken on a
  --srgb render measures the per-image tone window, not the reconstruction.""")
