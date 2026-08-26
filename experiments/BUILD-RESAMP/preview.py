"""Downsampled PNG preview so I can look at what is actually in a render."""
import sys
import numpy as np
import tifffile
from PIL import Image

path, out = sys.argv[1], sys.argv[2]
f = int(sys.argv[3]) if len(sys.argv) > 3 else 8
y0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
x0 = int(sys.argv[5]) if len(sys.argv) > 5 else 0
hh = int(sys.argv[6]) if len(sys.argv) > 6 else 0
ww = int(sys.argv[7]) if len(sys.argv) > 7 else 0

a = tifffile.imread(path)
if a.ndim == 3:
    a = a[:, :, 1]
a = a.astype(np.float64)
if hh:
    a = a[y0:y0 + hh, x0:x0 + ww]
if f > 1:
    h = (a.shape[0] // f) * f
    w = (a.shape[1] // f) * f
    a = a[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))
lo, hi = np.percentile(a, [0.5, 99.5])
b = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
b = b ** (1 / 2.2)
Image.fromarray((b * 255).astype(np.uint8)).save(out)
print(out, b.shape, "src pct", np.round([lo, hi], 1))
