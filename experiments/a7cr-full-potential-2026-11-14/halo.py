"""Halo at bright-on-dark edges: light a merge spreads from a bright subject
into an adjacent dark gap (defocused frames' blur), per arm, against a base.

  python -X utf8 halo.py BASE.tif ARM.tif [ARM.tif ...]

Mask, from the base arm's green (smoothed at 2 px): dark pixels (below 12 %
of the 99.5th percentile) that lie within 3-12 px of bright ones (above
50 %). Per arm and channel: mean value over that mask divided by the base's,
and the same over dark pixels 30+ px from anything bright (the far control:
a merge that lifts all shadows, not just edge shadows, shows there too).
Reported as ratios; above one is more light in the gap.

Fooled by: genuine scene detail in the gap (common to all arms, so it
cancels in the ratio only if every arm resolves it alike); misregistration
between arms (all arms here are one capture's renders).
"""
import sys

import numpy as np
import tifffile
from scipy.ndimage import binary_dilation, gaussian_filter

base = tifffile.imread(sys.argv[1]).astype(np.float32)
g = gaussian_filter(base[..., 1], 2.0)
top = np.percentile(g, 99.5)
dark, bright = g < 0.12 * top, g > 0.50 * top
near = binary_dilation(bright, iterations=12) & ~binary_dilation(bright, iterations=3) & dark
far = dark & ~binary_dilation(bright, iterations=30)
print(f'near-edge dark px {int(near.sum())}, far dark px {int(far.sum())}')


def stats(img):
    return [(float(img[..., c][near].mean()), float(img[..., c][far].mean())) for c in range(3)]


b = stats(base)
for p in sys.argv[2:]:
    a = stats(tifffile.imread(p).astype(np.float32))
    print(p.split('/')[-1].ljust(40), '  '.join(
        f'{"RGB"[c]} near {a[c][0] / b[c][0]:.3f} far {a[c][1] / b[c][1]:.3f}' for c in range(3)))
