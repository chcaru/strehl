"""Is the PLANT a plant? scipy.ndimage.gaussian_filter at small sigma.

BUILD-THESIS's blureq.py and limits.py both plant blur with
scipy.ndimage.gaussian_filter(t, s) at default truncate=4.0, on a ladder
s = 0.00, 0.05, ... 2.50, and invert against that same ladder.

A kernel radius of int(truncate*sigma + 0.5) means the kernel has ZERO width
below sigma = 0.125 and three taps below sigma = 0.375. A three-tap kernel at
sigma = 0.2 has wings of 3.7e-6. If the ladder is flat over its first eight
rungs then any small difference -- of ANY origin -- inverts to the sigma where
the ladder finally moves, and every subject lands on the same number.
"""
import numpy as np
from scipy.ndimage import gaussian_filter, _ni_support

print("scipy gaussian_filter1d kernel radius = int(truncate*sigma + 0.5)")
print(f"{'sigma':>7}{'radius':>8}{'taps':>6}{'max wing weight':>18}{'MTF^2 at Nyquist':>20}")
for s in (0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40,0.50,0.60,0.80,1.20):
    r = int(4.0*s + 0.5)
    x = np.arange(-r, r+1)
    if r == 0:
        k = np.array([1.0]); wing = 0.0
    else:
        k = np.exp(-0.5*(x/s)**2); k /= k.sum(); wing = k[0]
    # MTF at Nyquist f=0.5 cyc/px  -> sum k_n exp(-2j pi f n)
    m = np.abs((k*np.exp(-2j*np.pi*0.5*x)).sum())
    print(f"{s:>7.2f}{r:>8d}{2*r+1:>6d}{wing:>18.3e}{m**2:>20.6f}")

print("\nTRUE Gaussian MTF^2 at Nyquist for comparison: exp(-4 pi^2 sigma^2 * 0.25)")
for s in (0.20,0.30,0.40,0.50,0.80):
    print(f"   sigma {s:.2f} -> {np.exp(-4*np.pi**2*s*s*0.25):.6f}")

print("\nIS gaussian_filter(t, s) LITERALLY THE IDENTITY?  (real tile)")
import tifffile, pathlib
R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
t = tifffile.imread(str(R/"leaf-2-cpl"/"merge.tif"))[900:1700,1400:2200,1].astype(np.float64)
for s in (0.05,0.10,0.12,0.13,0.20,0.30,0.375,0.40):
    d = np.abs(gaussian_filter(t, s) - t).max()
    print(f"   sigma {s:<6.3f} max |delta| = {d:.6g} DN   identical={d==0.0}")
