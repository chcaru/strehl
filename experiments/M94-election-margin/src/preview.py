"""Downscale M94's rendered TIFFs to PNG previews for visual inspection.

The instrument writes full-plane and 1:1-crop TIFFs; this only makes them
viewable. It reads from C:\\dev\\strehl-out (write-allowed) and writes back
there, never into the repository.
"""

import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(r"C:\dev\strehl-out\M94-election-margin")
OUT = ROOT / "preview"
OUT.mkdir(parents=True, exist_ok=True)

wanted = sys.argv[1:] or ["elected-index-crop", "elected-index", "margin-q8-crop",
                          "confusion-radius-crop", "elected-index-null-iid-crop"]

for stack in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name != "preview"):
    for name in wanted:
        src = stack / f"{name}.tif"
        if not src.exists():
            continue
        im = Image.open(src)
        w, h = im.size
        scale = max(1, max(w, h) // 900)
        if scale > 1:
            im = im.resize((w // scale, h // scale), Image.Resampling.BOX)
        dst = OUT / f"{stack.name}--{name}.png"
        im.save(dst)
        print(f"{dst.name}: {w}x{h} -> {im.size[0]}x{im.size[1]}")
