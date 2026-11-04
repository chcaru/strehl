"""Session arms on one subject: dark-ground noise, black level, glow by distance.

usage: sessmetrics.py BASE_MASTER ARM_MASTER [ARM_MASTER ...]

Dark ground: 33x33 mean luminance below 1% of its 99.5th percentile (from BASE,
so every arm is measured on the same pixels). Noise: RMS of green minus its 3x3
and 33x33 box mean there. Black: mean green there. Glow: mean luminance of the dark
ground binned by distance to bright pixels (BASE 33x33 mean above 25% of the
percentile), each arm over BASE -- a merge that spreads defocused light into dark
ground reads above 1 near bright edges.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter, distance_transform_edt

base = tifffile.imread(sys.argv[1]).astype(np.float32)
L0 = uniform_filter(base.mean(-1), 33)
top = np.quantile(L0, 0.995)
dark = L0 < 0.01 * top
dist = distance_transform_edt(~(L0 > 0.25 * top))
bins = [(0, 8), (8, 16), (16, 32), (32, 64), (64, 128), (128, 10**9)]
base_lum = base.mean(-1)
print(f"dark-ground share {dark.mean()*100:.1f}%")
print("arm".ljust(34), "hp3 e4  hp33 e4  black e4  ", "  ".join(f"glow {a}-{b if b < 10**9 else 'inf'}" for a, b in bins))
for p in sys.argv[1:]:
    X = tifffile.imread(p).astype(np.float32)
    g = X[..., 1]
    hp3 = np.sqrt(((g - uniform_filter(g, 3))[dark] ** 2).mean())
    hp33 = np.sqrt(((g - uniform_filter(g, 33))[dark] ** 2).mean())
    black = g[dark].mean()
    lum = X.mean(-1)
    glow = []
    for a, b in bins:
        m = dark & (dist >= a) & (dist < b)
        glow.append(lum[m].mean() / max(base_lum[m].mean(), 1e-12) if m.any() else float('nan'))
    print(p.replace('\\', '/').split('/')[-2].ljust(34), f"{hp3*1e4:6.3f}  {hp33*1e4:6.3f}  {black*1e4:7.3f}   ", "  ".join(f"{v:9.3f}" for v in glow))
