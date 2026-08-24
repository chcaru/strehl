"""M87 diagnostic: what does the merged luma histogram actually look like?

Written after the registered two-mode mask rule produced a foreground fraction
of 0.72 and put 54% of the registered background-only ROI inside the mask. The
rule is defective on this image; this script establishes what to replace it
with, and the replacement is disclosed in the report.
"""

import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

img = tifffile.imread(r"C:\dev\strehl-out\bee3-g0.tif").astype(np.float32)
g = img[..., 1]
print("full image percentiles:", np.round(np.percentile(g, [1, 5, 25, 50, 75, 90, 95, 99]), 0))
h, e = np.histogram(g, bins=48, range=(float(g.min()), float(g.max())))
for i in range(48):
    bar = "#" * int(60 * h[i] / h.max())
    print(f"  {e[i]:8.0f}-{e[i + 1]:8.0f}  {h[i]:9d}  {bar}")

for name, (y0, y1, x0, x1) in L.ROIS.items():
    r = g[y0:y1, x0:x1]
    print(f"{name} percentiles:", np.round(np.percentile(r, [1, 5, 25, 50, 75, 95, 99]), 0))

# Otsu on the full image, which is the standard two-class rule and needs no
# peak-finding heuristic.
hist, edges = np.histogram(g, bins=512, range=(float(g.min()), float(g.max())))
centres = 0.5 * (edges[:-1] + edges[1:])
w0 = np.cumsum(hist)
w1 = w0[-1] - w0
mu0 = np.cumsum(hist * centres) / np.maximum(w0, 1)
tot = (hist * centres).sum()
mu1 = (tot - np.cumsum(hist * centres)) / np.maximum(w1, 1)
between = w0 * w1 * (mu0 - mu1) ** 2
k = int(np.argmax(between))
print(f"\nOtsu threshold = {centres[k]:.1f}  ({centres[k] / 65535:.3f} of full scale)")
m = g < centres[k]
print(f"  foreground fraction at Otsu = {m.mean():.4f}")
for name, (y0, y1, x0, x1) in L.ROIS.items():
    print(f"  {name} foreground fraction at Otsu = {m[y0:y1, x0:x1].mean():.5f}")

# where is there clean background?
col = m.mean(axis=0)
row = m.mean(axis=1)
print("\ncolumn foreground fraction, every 200 px:")
print("  " + "  ".join(f"{i}:{col[i]:.2f}" for i in range(0, g.shape[1], 200)))
print("row foreground fraction, every 200 px:")
print("  " + "  ".join(f"{i}:{row[i]:.2f}" for i in range(0, g.shape[0], 200)))
