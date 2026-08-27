"""COMMISSION THE REGISTRATION. Two claims are being made; both are testable.

CLAIM 1  Low-pass registration recovers a known shift on a frame that is too
         defocused for direct registration to find it at all.
CLAIM 2  Band power is translation-invariant, so a few px of residual
         registration error does not corrupt the measurement.

Claim 2 is the reason claim 1 is allowed to be sloppy. If claim 2 fails, the
whole design fails, so it is tested on real pixels rather than argued from
|FFT| being phase-blind -- the Hann window makes it only approximately true.
"""
import os, sys, numpy as np, tifffile
from scipy.ndimage import gaussian_filter, shift as ndshift
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sharplib import luma, register, P, SEARCH
from sharp_bands import bandpow, B_HI
from sharp_bands2 import LP_SIGMA, LPCORR_MIN

d = r"C:\dev\strehl-out\V-GATHER\sharp\119MSDCF\MASTER.tiff"
my = luma(tifffile.imread(d)[..., :3].astype(np.float32))
Y, X = 1600, 2400
big = my[Y-SEARCH-64:Y+P+SEARCH+64, X-SEARCH-64:X+P+SEARCH+64].astype(np.float64)
ref = my[Y:Y+P, X:X+P].astype(np.float64)
rlp = gaussian_filter(ref, LP_SIGMA)
TRUE_DY, TRUE_DX = 17, -23

print("CLAIM 1  planted shift (%+d,%+d) under planted defocus" % (TRUE_DY, TRUE_DX))
print("%8s | %-28s | %-28s" % ("defocus", "DIRECT registration (v1)", "LOW-PASS registration (v2)"))
print("%8s | %8s %8s %8s | %8s %8s %8s" % ("sigma px", "dy", "dx", "corr", "dy", "dx", "corr"))
for sg in (0.0, 1.0, 2.0, 4.0, 6.0, 9.0, 12.0):
    sim = gaussian_filter(big, sg) if sg > 0 else big.copy()
    sim = ndshift(sim, (TRUE_DY, TRUE_DX), order=1, mode="nearest")
    o = sim[64:64+P+2*SEARCH, 64:64+P+2*SEARCH]
    dy1, dx1, c1 = register(ref, o)
    dy2, dx2, c2 = register(rlp, gaussian_filter(o, LP_SIGMA))
    f1 = "OK " if c1 >= 0.60 else "DROP"
    f2 = "OK " if c2 >= LPCORR_MIN else "DROP"
    print("%8.1f | %+8d %+8d %5.2f%s | %+8d %+8d %5.2f%s"
          % (sg, dy1, dx1, c1, f1, dy2, dx2, c2, f2))
print("  truth  | %+8d %+8d          | %+8d %+8d" % (TRUE_DY, TRUE_DX, TRUE_DY, TRUE_DX))

print()
print("CLAIM 2  how much does a residual shift of k px move the detail band?")
print("%6s %14s %12s" % ("k px", "HI band power", "vs k=0"))
b0 = None
for k in (0, 1, 2, 3, 5, 8, 12, 20, 40):
    c = my[Y+k:Y+k+P, X+k:X+k+P].astype(np.float64)
    hp = float(bandpow(c)[B_HI].sum())
    if k == 0: b0 = hp
    print("%6d %14.4g %11.4f" % (k, hp, hp/b0))
print("  (this is real texture moving under the patch, so it is an UPPER bound")
print("   on shift sensitivity: it includes genuine content change, not just phase)")
