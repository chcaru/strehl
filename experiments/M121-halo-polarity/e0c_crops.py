"""E0c -- 1:1 crops, chosen to contain both edge polarities.

Writes PNG previews only (PIL for WRITE); every read is tifffile + uint16 assert.

Run:  python experiments/M121-halo-polarity/e0c_crops.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from m121_io import OUT, arm_path, load_u16, luma  # noqa: E402

# (name, y, x, h, w) in plane pixels of the 2344x3516 binlin grid.
# Picked off `look/overview-armM4.png` at 1/4 scale, so preview (px,py) -> (4*px, 4*py).
CROPS = [
    ("A-leg-vs-white",       1100,  200, 320, 480),   # dark leg, bright defocused background
    ("B-antenna-vs-white",   1150, 2700, 320, 480),   # dark antenna over bright background
    ("C-wing-veins",          150,  600, 320, 480),   # dark veins on bright membrane
    ("D-thorax-hairs",        500, 2100, 320, 480),   # pale hairs on darker body
    ("E-eye-hairs",          1560, 1950, 320, 480),   # bright bristles over the dark eye
    ("F-abdomen-hairs",       700, 1000, 320, 480),   # pale hairs against darker abdomen
    ("G-silhouette-top",      120, 1900, 320, 480),   # top of head fur against white
    ("H-claw-vs-table",      1900, 1200, 320, 480),   # dark claw over the grey table
]


def stretch(a, lo=None, hi=None, gamma=0.5):
    if lo is None:
        lo, hi = np.percentile(a, [0.5, 99.5])
    b = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1) ** gamma
    return (b * 255).astype(np.uint8)


def main():
    d = OUT / "look"
    d.mkdir(parents=True, exist_ok=True)
    m = luma(load_u16(arm_path("armM4-gate4-binlin")))
    for name, y, x, h, w in CROPS:
        t = m[y:y + h, x:x + w]
        Image.fromarray(stretch(t)).save(d / f"crop-{name}.png")
        print(f"{name:22s} y={y} x={x}  mean={t.mean():8.1f} sd={t.std():8.1f} "
              f"p1={np.percentile(t,1):8.1f} p99={np.percentile(t,99):8.1f}")


if __name__ == "__main__":
    main()
