"""Pictures for the out-of-sample subject, off vs on, at ONE shared gain.

The gain comes from the OFF arm and is applied to both panels. That is the whole
point here: the failure under investigation IS a global brightening (+5.15% of
the far field), and an arm-specific autostretch would normalise exactly that away
and show two identical-looking panels.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\VEILZ2")
STEM = sys.argv[2] if len(sys.argv) > 2 else "cb"


def encode(a: np.ndarray, scale: float) -> np.ndarray:
    x = np.clip(a / scale, 0.0, 1.0)
    s = np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)
    return (s * 255.0 + 0.5).astype(np.uint8)


off = tifffile.imread(str(OUT / f"{STEM}-off.tif")).astype(np.float32)
on = tifffile.imread(str(OUT / f"{STEM}-on.tif")).astype(np.float32)

scale = float(np.percentile(off, 99.5))
print(f"shared gain from the OFF arm: {scale:.0f} DN")

pics = OUT / "pics"
pics.mkdir(exist_ok=True)

step = max(1, off.shape[1] // 820)
pair = np.concatenate([encode(off[::step, ::step], scale),
                       encode(on[::step, ::step], scale)], axis=1)
Image.fromarray(pair).save(pics / f"{STEM}-full-off-vs-on.png")
print(f"wrote {STEM}-full-off-vs-on.png  off | on  {pair.shape[1]}x{pair.shape[0]}")

lum = 0.2126 * off[..., 0] + 0.7152 * off[..., 1] + 0.0722 * off[..., 2]
dark = lum < 0.35 * float(np.median(lum))
ys, xs = np.where(dark)
cy, cx = int(np.median(ys)), int(np.percentile(xs, 99))
h = 460
y0 = max(0, min(off.shape[0] - h, cy - h // 2))
x0 = max(0, min(off.shape[1] - 2 * h, cx - h // 3))
ca, cb = encode(off[y0:y0 + h, x0:x0 + 2 * h], scale), encode(on[y0:y0 + h, x0:x0 + 2 * h], scale)
gap = np.full((ca.shape[0], 10, 3), 255, np.uint8)
Image.fromarray(np.concatenate([ca, gap, cb], axis=1)).save(pics / f"{STEM}-rim-off-vs-on.png")
print(f"wrote {STEM}-rim-off-vs-on.png  rim crop at y={y0} x={x0}")
