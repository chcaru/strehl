"""Convert the M95 kernel BMP contact strips to PNG at 2x, so the panels can be
inspected by eye at a size where ringing is visible on screen.

Nearest-neighbour upscale only: any smooth interpolation here would be the
same operation under measurement and would soften the very artefact being
looked for.
"""
import sys
from pathlib import Path

from PIL import Image

SRC = Path(r"C:\dev\strehl-out\M95-kernel")
for p in sorted(SRC.glob("*.bmp")):
    im = Image.open(p)
    w, h = im.size
    big = im.resize((w * 2, h * 2), Image.NEAREST)
    out = p.with_suffix(".png")
    big.save(out)
    print(f"{p.name} {w}x{h} -> {out.name} {big.size[0]}x{big.size[1]}")
sys.exit(0)
