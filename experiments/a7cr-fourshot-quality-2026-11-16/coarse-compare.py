"""Q4: do two renders agree in their coarse content?

  python -X utf8 coarse-compare.py MASK.tif BASE.tif ARM.tif [ARM.tif ...]

Green, low-passed with a Gaussian at 32 and at 64 px; per arm the ratio to
the base's low-pass: median and 1st/99th percentile over the frame, and the
mean over bright pixels and over dark pixels 30-100, 100-200 and 200+ px
from the nearest bright one (classes from MASK, an independent render:
green at 2 px, bright above 50 % of the 99.5th percentile, dark below 12 %).

Used to ask whether `STREHL_FUSION_COARSE=election` gives the election's
coarse levels: if it did, its low-pass would match the election arm's
everywhere a guided (fine) level cannot reach.
"""
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, gaussian_filter


def green(path, sigma):
    return gaussian_filter(tifffile.imread(path)[..., 1].astype(np.float32), sigma)


m = green(sys.argv[1], 2.0)
top = np.percentile(m, 99.5)
dark, bright = m < 0.12 * top, m > 0.5 * top
dist = distance_transform_edt(~bright)
zones = [('dark 30-100', dark & (dist >= 30) & (dist < 100)), ('dark 100-200', dark & (dist >= 100) & (dist < 200)),
         ('dark 200+', dark & (dist >= 200)), ('bright', bright)]
for sigma in (32.0, 64.0):
    base = green(sys.argv[2], sigma)
    for arm in sys.argv[3:]:
        r = green(arm, sigma) / np.maximum(base, 1)
        s = r[::7, ::7]
        print(f'sigma {sigma:.0f} px, {Path(arm).name[:34]:34s}: median {np.median(s):.4f}, p1 {np.percentile(s, 1):.3f}, p99 {np.percentile(s, 99):.3f}; '
              + '; '.join(f'{name} {r[z].mean():.3f}' for name, z in zones))
