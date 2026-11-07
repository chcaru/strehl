"""Score a glint-taming arm against its untreated development.

usage: python glint-score.py UNTREATED.tif TREATED.tif [...TREATED.tif]

Both are developed 16-bit sRGB TIFFs of the same master. Prints the share of
pixels above 95% white (any channel) and, per untreated-luma bin, the mean
treated/untreated luma ratio. A glint control should leave the lower bins at
~1.00 (the lit subject) and lower only the top bins (the glints).
"""
import sys

import numpy as np
import tifffile

BINS = [(0.05, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 0.9), (0.9, 1.01)]


def load(path):
    a = tifffile.imread(path).astype(np.float32) / 65535.0
    return a[..., :3]


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


base = load(sys.argv[1])
by = luma(base)
print("arm".ljust(28), "above95  ", "  ".join(f"{lo:.2f}-{min(hi, 1):.2f}(n%)" for lo, hi in BINS))
rows = [(sys.argv[1], base)] + [(p, load(p)) for p in sys.argv[2:]]
for path, img in rows:
    ty = luma(img)
    above = (img.max(axis=-1) > 0.95).mean() * 100
    cells = []
    for lo, hi in BINS:
        m = (by >= lo) & (by < hi)
        share = m.mean() * 100
        ratio = ty[m].mean() / max(by[m].mean(), 1e-9) if m.any() else float("nan")
        cells.append(f"{ratio:.3f}({share:5.2f})")
    print(path.split("/")[-1].ljust(28), f"{above:7.3f}%", "  ".join(cells))
