"""Is BUILD-THESIS's inversion floor an artifact of the truncated kernel, or intrinsic?
Drive their invert() and an exact-Gaussian invert() with an infinitesimal target deficit."""
import pathlib, sys
import numpy as np, tifffile
B = pathlib.Path("experiments/BUILD-THESIS").resolve(); sys.path.insert(0, str(B))
V = pathlib.Path("experiments/V-THESIS").resolve(); sys.path.insert(0, str(V))
from stats import STATS
from blureq import invert, LADDER
from vplant import gauss_exact

def invert_exact(t, target, fn):
    prev_s, prev_v = 0.0, fn(t)
    if target >= prev_v: return 0.0
    for s in LADDER[1:]:
        v = fn(gauss_exact(t, s))
        if v <= target:
            w = 0.0 if prev_v == v else (prev_v-target)/(prev_v-v)
            return float(prev_s + w*(s-prev_s))
        prev_s, prev_v = s, v
    return float(LADDER[-1])

g = tifffile.imread(r"C:\dev\strehl-out\BUILD-THESIS\renders\bee-3-cpl\merge.tif")[:,:,1].astype(np.float64)
t = g[1200:2000, 700:1500]
print("relative deficit -> equivalent blur px   (theirs = truncated ladder, exact = Fourier Gaussian)")
print(f"{'deficit':>9}" + "".join(f"{k+' theirs':>12}{k+' exact':>11}" for k in STATS))
for d in (1e-6, 1e-4, 1e-2, 3e-2):
    row = f"{d:>9.0e}"
    for k, fn in STATS.items():
        v0 = fn(t)
        row += f"{invert(t, v0*(1-d), fn):>12.3f}{invert_exact(t, v0*(1-d), fn):>11.3f}"
    print(row)
