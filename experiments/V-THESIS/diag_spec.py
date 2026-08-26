import pathlib, sys
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
sys.path.insert(0, str(pathlib.Path("experiments/V-THESIS").resolve()))
from vstat import radial_power, sigma_immerkaer

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
img = tifffile.imread(str(R / "leaf-2-cpl" / "merge.tif"))
t = img[900:1700, 1400:2200, 1].astype(np.float64)
s0 = sigma_immerkaer(t)
print("sigma0", s0)
k, P, N = radial_power(t, None, 320)
w = np.outer(np.hanning(800), np.hanning(800))
floor = s0**2 * (w*w).sum()
print("floor level", floor)
print(f"{'k':>5}{'P':>14}{'P/floor':>10}")
for kk in (10,20,34,50,80,120,160,200,240,280,320):
    print(f"{kk:>5}{P[kk]:>14.4g}{P[kk]/floor:>10.3f}")
tb = gaussian_filter(t, 0.3)
print("sigma_immerkaer after 0.3 blur:", sigma_immerkaer(tb))
tb8 = gaussian_filter(t, 0.8)
print("sigma_immerkaer after 0.8 blur:", sigma_immerkaer(tb8))
