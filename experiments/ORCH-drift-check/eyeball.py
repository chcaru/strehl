"""ORCH eyeball: pull true 1:1 crops from freshly rendered masters, no resampling.

Picks the sharpest tiles by gradient energy so the crop lands on subject detail
rather than background, then writes 8-bit PNGs at exactly 1:1.
"""
import os
import sys

import numpy as np
import tifffile
from PIL import Image

SRC = r"C:\dev\strehl-out\DELIVER-V6\masters"
OUT = r"D:\strehl-out\ORCH-EYEBALL"
CROP = 900


def to8(a):
    a = a.astype(np.float32)
    lo, hi = np.percentile(a, 0.2), np.percentile(a, 99.8)
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((a - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def pick_site(g, crop, margin=64):
    """Coarse gradient-energy search; returns top-left of the sharpest tile."""
    h, w = g.shape
    step = max(crop // 2, 1)
    best, bxy = -1.0, (margin, margin)
    for y in range(margin, max(margin + 1, h - crop - margin), step):
        for x in range(margin, max(margin + 1, w - crop - margin), step):
            t = g[y:y + crop:8, x:x + crop:8]
            if t.size == 0:
                continue
            e = float(np.mean(np.abs(np.diff(t, axis=0))) + np.mean(np.abs(np.diff(t, axis=1))))
            if e > best:
                best, bxy = e, (y, x)
    return bxy, best


def main(names):
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        path = os.path.join(SRC, name + ".tiff")
        if not os.path.exists(path):
            print(f"{name}: ABSENT")
            continue
        img = tifffile.imread(path)
        if img.ndim != 3:
            print(f"{name}: unexpected shape {img.shape}")
            continue
        h, w = img.shape[:2]
        luma = img[..., 1].astype(np.float32)
        (y, x), e = pick_site(luma, CROP)
        tile = img[y:y + CROP, x:x + CROP, :3]
        rgb = np.dstack([to8(tile[..., c]) for c in range(3)])
        dst = os.path.join(OUT, f"{name}-1to1-{x}_{y}.png")
        Image.fromarray(rgb).save(dst)
        print(f"{name}: {w}x{h} {img.dtype} -> site ({x},{y}) grad {e:.1f} -> {os.path.basename(dst)}")


if __name__ == "__main__":
    main(sys.argv[1:])
