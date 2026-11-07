"""Score renders of a fixed-focus subset against the mean of held-out frames.

usage: truth-score.py TRUTH.tif ARM.tif [ARM.tif ...]

Inputs are scene-linear float masters (or 16-bit sRGB). All share one warp map, so they are pixel-aligned. TRUTH is the plain
mean of disjoint frames of the same fixed-focus burst; its own noise is
independent of every arm and adds the same constant to each arm's error, so arm
differences are unbiased. Linear luma; error power reported overall and by band
(fine = x - box3, mid = box3 - box9, coarse = box9 - box33), and split into
flat and textured tiles by the truth's own mid-band power.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter


def luma(p):
    a = tifffile.imread(p).astype(np.float32)
    if a.dtype != np.float32 or a.max() > 64.0:  # 16-bit sRGB delivery file
        a = a / 65535
        a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def split(y):
    b3, b9, b33 = (uniform_filter(y, k) for k in (3, 9, 33))
    return {"fine": y - b3, "mid": b3 - b9, "coarse": b9 - b33}


def tiles(x, t=64):
    h, w = x.shape[0] // t * t, x.shape[1] // t * t
    return x[:h, :w].reshape(h // t, t, w // t, t).mean(axis=(1, 3))


truth = luma(sys.argv[1])
tb = split(truth)
texture = tiles(tb["mid"] ** 2)
lit = tiles(truth) > 0.005
q30, q70 = np.quantile(texture[lit], [0.3, 0.7])
cls = {"flat": lit & (texture <= q30), "textured": lit & (texture >= q70)}
print(f"truth tiles lit {lit.sum()}; flat {cls['flat'].sum()} textured {cls['textured'].sum()}")
for p in sys.argv[2:]:
    a = luma(p)
    ab = split(a)
    parts = []
    for band in ("fine", "mid", "coarse"):
        err = tiles((ab[band] - tb[band]) ** 2)
        for c, m in cls.items():
            parts.append(f"{band}/{c} {err[m].mean():.3e}")
    print(f"{p:28s} " + " ".join(parts))
