"""Compose M116's tone-mapped renders into before/after sheets for the owner.

Uses M116's own --srgb renders, which were produced at an exposure solved ONCE
on the A0 arm and then passed literally to every other arm, so the panels differ
in the merge and not in the gain (M116 run_view.ps1 lines 8-10).

No re-rendering, no re-stretching: these are the shipped tone curve.
"""
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

SRC = r"C:\dev\strehl-out\M116\images"
OUT = r"C:\dev\strehl-out\ORCH-morning"
SUBJ = sys.argv[1] if len(sys.argv) > 1 else "tweezers-cpl"
LEFT, RIGHT = "A0", "A1"
os.makedirs(OUT, exist_ok=True)


def panel(arm, kind):
    p = os.path.join(SRC, "%s__%s__%s.png" % (SUBJ, arm, kind))
    if not os.path.exists(p):
        return None, p
    return np.asarray(Image.open(p).convert("RGB")), p


for kind, width in (("flat", 1500), ("detail", 1500), ("full", 1700)):
    a, pa = panel(LEFT, kind)
    b, pb = panel(RIGHT, kind)
    if a is None or b is None:
        print("skip %s (missing %s)" % (kind, os.path.basename(pa if a is None else pb)))
        continue
    if a.shape != b.shape:
        print("skip %s (shape %s vs %s)" % (kind, a.shape, b.shape))
        continue

    half = width // 2
    scale = half / a.shape[1]
    h = max(int(round(a.shape[0] * scale)), 1)
    ims = [Image.fromarray(x).resize((half, h), Image.LANCZOS) for x in (a, b)]
    gap = Image.new("RGB", (10, h), (255, 255, 255))
    sheet = Image.new("RGB", (half * 2 + 10, h), (255, 255, 255))
    sheet.paste(ims[0], (0, 0))
    sheet.paste(gap, (half, 0))
    sheet.paste(ims[1], (half + 10, 0))
    q = os.path.join(OUT, "OWNER-%s-%s.jpg" % (SUBJ, kind))
    sheet.save(q, quality=92)
    print("%-7s  %-42s %9d B   |  %-42s %9d B   -> %s"
          % (kind, os.path.basename(pa), os.path.getsize(pa),
             os.path.basename(pb), os.path.getsize(pb), os.path.basename(q)))

print()
print("left = A0 default (shipped), right = A1 --photometric; identical exposure")
