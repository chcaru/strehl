"""Glow (halo) next to bright edges: a render against an in-focus reference.

usage: glow.py REF.tif ARM.tif [ARM.tif ...]

REF is a single frame in which the (flat) subject is in focus, rendered under
the same warp map, so it is pixel-aligned with every arm. Dark pixels are those
whose REF luminance (linear, 9x9 mean) is below 2% of the image's 99.5th
percentile; they are binned by distance to the nearest bright pixel (REF above
25% of that percentile). Per distance bin the mean linear luminance of each arm
is reported relative to REF's: a merge that blends defocused frames' spread-out
light into dark ground reads above 1 near edges and ~1 far away. Also printed:
the arm's mean over the 0-40 px band as a fraction of bright level.

Can be fooled: REF's own noise and residual defocus; a 9x9 mean in REF keeps
noise out of the dark mask. The flat subject is the control that makes REF a
near-truth for edge sharpness; on a tilted subject no single frame is.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, uniform_filter


def lin(p):
    a = tifffile.imread(p).astype(np.float32) / 65535
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4).mean(-1)


ref = lin(sys.argv[1])
m = uniform_filter(ref, 9)
top = np.quantile(m, 0.995)
bright = m > 0.25 * top
dark = m < 0.02 * top
dist = distance_transform_edt(~bright)
edges = [1, 4, 8, 16, 32, 64, 128, 256]
inner = np.zeros_like(dark)
inner[100:-100, 100:-100] = True
print(f"bright level {top:.4f}; dark pixels {dark.mean():.3f}")
for p in sys.argv[2:]:
    a = uniform_filter(lin(p), 3)
    parts = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        sel = dark & inner & (dist >= lo) & (dist < hi)
        if sel.sum() < 100:
            continue
        parts.append(f"{lo}-{hi}px {a[sel].mean() / max(m[sel].mean(), 1e-9):.2f}")
    band = dark & inner & (dist < 40)
    print(f"{p.split('/')[-1]:14s} glow 0-40px {a[band].mean() / top:.5f} of bright | " + " ".join(parts))
