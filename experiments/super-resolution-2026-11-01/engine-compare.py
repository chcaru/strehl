"""Compare saved variants with the actual engine master at the same ROI.

The master (BT.709 linear) is mapped to the arms' camera RGB by a least-squares
3x3 + offset fit against arm A over the ROI (a linear colour map; it cannot add
or remove detail). Output: engine, A, and each variant under one display
transform. Also prints a flat-free detail statistic: high-band energy (image
minus Gaussian sigma 1.5) per arm, relative to the engine, and its value on a
pure-noise control made by the engine's own residual between two variants.
Usage: engine-compare.py master.tiff variants.npy grid_x0 grid_y0 crop_dx crop_dy out.png labels...
"""
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

master, var, gx, gy, cdx, cdy, out = sys.argv[1:8]
labels = sys.argv[8:]
gx, gy, cdx, cdy = int(gx), int(gy), int(cdx), int(cdy)
v = np.load(var)
_, _, h, w = v.shape
m = tifffile.imread(master)[gy - cdy:gy - cdy + h, gx - cdx:gx - cdx + w].astype(np.float64).transpose(2, 0, 1)
X = np.concatenate([m.reshape(3, -1), np.ones((1, h * w))]).T
coef, *_ = np.linalg.lstsq(X, v[0].reshape(3, -1).T, rcond=None)
eng = (X @ coef).T.reshape(3, h, w)
arms = np.concatenate([eng[None], v])
b = 8
core = arms[:, :, b:-b, b:-b]
for name, a in zip(["engine"] + labels, core):
    hb = a - np.stack([gaussian_filter(c, 1.5) for c in a])
    print(f"{name:>10}: high-band rms r/g/b " + " ".join(f"{np.sqrt(np.mean(c ** 2)):7.2f}" for c in hb))
np.save(out.replace(".png", ".npy"), arms)
import subprocess
subprocess.run([sys.executable, __file__.replace("engine-compare.py", "crops.py"), out.replace(".png", ".npy"), out,
                "engine"] + labels, check=True)
