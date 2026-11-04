"""Locally-sharpest single-frame composite, and glow against it.

usage: localref.py build FRAMES_GLOB OUT.npy [tile]
       localref.py score REF.npy ARM.tif [ARM.tif ...]

build: single-frame renders made under one warp map (STREHL_FRAME_PARITY=i-i)
are pixel-aligned. For every tile the frame with the most high-pass green
energy is taken; the composite's linear luminance is saved. On a tilted planar
subject (no depth discontinuities inside a tile) each tile of the composite is
an in-focus observation, so its dark ground is the true local black level plus
the lens's own veiling glare -- and no merge.

score: dark pixels of the composite (9x9 mean below 2% of its 99.5th
percentile), binned by distance to bright pixels (above 25%). Per bin: arm mean
luminance / composite mean luminance. A merge that adds glow reads above 1.
Tile seams in the composite are excluded by using 9x9 means for the masks; the
glow measure itself is a low-frequency statistic, insensitive to noise.
"""
import glob
import re
import sys
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, uniform_filter


def lin(p):
    a = tifffile.imread(p).astype(np.float32) / 65535
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).mean(-1)


if sys.argv[1] == "build":
    files = sorted(glob.glob(sys.argv[2]), key=lambda p: int(re.findall(r"f(\d+)", p)[-1]))
    t = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    best = None
    for f in files:
        y = lin(f)
        h, w = y.shape[0] // t * t, y.shape[1] // t * t
        hp = (y - uniform_filter(y, 5))[:h, :w] ** 2
        e = hp.reshape(h // t, t, w // t, t).mean(axis=(1, 3))
        if best is None:
            best, ref = e, y.copy()
            continue
        better = e > best
        best = np.where(better, e, best)
        m = np.repeat(np.repeat(better, t, 0), t, 1)
        ref[:h, :w][m] = y[:h, :w][m]
    np.save(sys.argv[3], ref.astype(np.float32))
    print(f"composite of {len(files)} frames -> {sys.argv[3]}")
    sys.exit(0)

ref = np.load(sys.argv[2])
m = uniform_filter(ref, 9)
top = np.quantile(m, 0.995)
bright = m > 0.25 * top
dark = m < 0.02 * top
dist = distance_transform_edt(~bright)
inner = np.zeros_like(dark)
inner[100:-100, 100:-100] = True
edges = [2, 8, 16, 32, 64, 128, 256]
print(f"bright level {top:.4f}; dark fraction {dark.mean():.3f}")
for p in sys.argv[3:]:
    a = uniform_filter(lin(p), 3)
    parts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = dark & inner & (dist >= lo) & (dist < hi)
        if sel.sum() < 100:
            continue
        parts.append(f"{lo}-{hi}px {a[sel].mean() / max(m[sel].mean(), 1e-9):.2f}")
    band = dark & inner
    print(f"{p.split('/')[-1]:16s} dark mean {a[band].mean() / top:.5f} (ref {m[band].mean() / top:.5f}) | "
          + " ".join(parts))
