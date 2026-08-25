"""Downscale renders so ORCH can actually look at them.

Writes to %TEMP%\orch-view only. Never writes to D:\ and never writes inside the
repo -- these are throwaway viewing aids, not artifacts.
"""
import os
import sys
from PIL import Image

DST = os.path.join(os.environ["TEMP"], "orch-view")
os.makedirs(DST, exist_ok=True)

JOBS = [
    ("full", r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl-preview.png", 1100),
    ("eye", r"C:\dev\strehl-out\ORCH-look\crop-head-eye.png", 900),
    ("hair", r"C:\dev\strehl-out\ORCH-look\crop-thorax-hair.png", 900),
    ("wing", r"C:\dev\strehl-out\ORCH-look\crop-wing-venation.png", 900),
    ("spines", r"C:\dev\strehl-out\ORCH-look\crop-leg-spines.png", 900),
    ("halo", r"C:\dev\strehl-out\crop-leg-halo.png", 900),
]

for name, src, width in JOBS:
    if not os.path.exists(src):
        print("MISSING %-8s %s" % (name, src))
        continue
    im = Image.open(src)
    w, h = im.size
    if w > width:
        im = im.resize((width, max(1, round(h * width / w))), Image.LANCZOS)
    out = os.path.join(DST, name + ".jpg")
    im.convert("RGB").save(out, quality=88)
    print(
        "%-8s src=%dx%d -> %dx%d  %s (%.0f KB)"
        % (name, w, h, im.size[0], im.size[1], out, os.path.getsize(out) / 1024.0)
    )
