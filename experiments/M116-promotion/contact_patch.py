"""contact_patch.py — a contact sheet of the shipped render, to FIND the artefact.

The registered ROI selector (lowest coarse-gradient decile) picked the pure
white background, which the M87 crop shows is the one region where the
patchwork is absent. The artefact lives in MID-TONE, partially structured
defocused areas. So this stops scoring and looks: it tiles the frame and
hard-stretches each tile locally.

Local autoscaling is legitimate for FINDING a region and illegitimate for
COMPARING arms, so nothing here is a measurement and no number from it is
reported.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = Path(r"C:\dev\strehl-out\M116")
OUT = ROOT / "images-patch"
OUT.mkdir(parents=True, exist_ok=True)

S = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
ARM = sys.argv[2] if len(sys.argv) > 2 else "A0"
TILE = 384
CELL = 192


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


g = luma(tifffile.imread(ROOT / "measure" / f"{S}__{ARM}.tif").astype(np.float32))
H, W = g.shape
ny, nx = H // TILE, W // TILE
sheet = np.full((ny * (CELL + 4), nx * (CELL + 4)), 255, np.uint8)
print(f"{S} {ARM}: {H}x{W} -> grid {ny}x{nx} of {TILE}px tiles")

for iy in range(ny):
    for ix in range(nx):
        t = g[iy * TILE:(iy + 1) * TILE, ix * TILE:(ix + 1) * TILE]
        sm = t.reshape(CELL, 2, CELL, 2).mean(axis=(1, 3))
        lo, hi = np.percentile(sm, 1.0), np.percentile(sm, 99.0)
        u8 = np.clip((sm - lo) / max(hi - lo, 1e-9) * 255, 0, 255).astype(np.uint8)
        sheet[iy * (CELL + 4):iy * (CELL + 4) + CELL,
              ix * (CELL + 4):ix * (CELL + 4) + CELL] = u8

name = OUT / f"{S}__contact-{ARM}.png"
Image.fromarray(sheet).save(name)
print(f"wrote {name}")
print(f"tile (iy,ix) origin = (iy*{TILE}, ix*{TILE})")
