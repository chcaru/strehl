"""V-KILLB0 speck.py -- does the 4x arm make dark specks MORE conspicuous?

Trading grain for visible dust is not an improvement.  A speck is a small dark
outlier against its own local background, so it is detected as a pixel sitting
more than K robust sigma BELOW a local median, with sigma estimated from the
same neighbourhood.  Conspicuousness is not just the count: it is the count
times how far the speck sits below its surroundings in units of the LOCAL
texture, because a speck on a busy ground is camouflaged and the same speck on
a smooth ground is not.  Both are reported.

CONTROLS printed before any result:
  S0 NULL     arm against itself -> identical counts
  S1 PLANTED  200 synthetic specks of known depth dropped into a copy; the
              detector must recover most of them, or its zero means nothing.
"""
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import median_filter, uniform_filter

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-HEADTOHEAD2")
import h2                                    # noqa: E402

OUT = r"C:\dev\strehl-out\V-KILLB0"
K = 6.0
BOX = 9


def detect(a):
    med = median_filter(a, BOX)
    d = med - a                       # positive where darker than surroundings
    loc = np.sqrt(np.maximum(uniform_filter(d * d, 31) - uniform_filter(d, 31) ** 2, 1e-9))
    z = d / loc
    m = z > K
    return m, z, loc


def stats(a, name):
    m, z, loc = detect(a)
    n = int(m.sum())
    return n, (float(z[m].mean()) if n else float("nan")), float(loc.mean()), name


key = sys.argv[1]
y, x, S = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1200
A = h2.luma709(tifffile.imread(os.path.join(OUT, "default", key + ".tiff"))[y:y+S, x:x+S, :3].astype(np.float64))
B = h2.luma709(tifffile.imread(os.path.join(OUT, "b0x4", key + ".tiff"))[y:y+S, x:x+S, :3].astype(np.float64))

na = stats(A, "default")[0]
nn = stats(A.copy(), "null")[0]
print(f"== SPECKS {key} at ({y},{x}) {S}x{S}   threshold {K} local sigma")
print(f"   S0 NULL   default vs its own copy: {na} vs {nn}  "
      f"{'PASS' if na == nn else 'FAIL'}")
rng = np.random.default_rng(11)
P = A.copy()
yy = rng.integers(40, S - 40, 200); xx = rng.integers(40, S - 40, 200)
depth = np.median(A) * 0.35
for j in range(200):
    P[yy[j], xx[j]] -= depth
    P[yy[j], xx[j]] = max(P[yy[j], xx[j]], 0)
np_ = stats(P, "planted")[0]
rec = np_ - na
print(f"   S1 PLANTED 200 specks of {depth:.0f} DN: detector found {rec} more  "
      f"{'PASS' if rec > 120 else 'FAIL - detector is not sensitive enough to be trusted at 0'}")

print(f"\n   {'arm':<9} {'specks':>8} {'mean depth (local sigma)':>26} "
      f"{'local texture sigma DN':>24} {'median DN':>10}")
for img, nm in ((A, "default"), (B, "b0x4")):
    n, zm, lm, _ = stats(img, nm)
    print(f"   {nm:<9} {n:8d} {zm:26.2f} {lm:24.1f} {np.median(img):10.0f}")
