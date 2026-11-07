"""Low-frequency (tone) agreement between two renders, and where it fails.

usage: tone.py A.tif B.tif OUT.png

Reports the signed mean difference and the distribution of the 31x31 low-pass
of B-A in 16-bit sRGB DN, and writes a map (grey = equal, white = B brighter)
at 1/4 scale with the same fixed display gain for every call (80 DN per level).
A noise-only change moves fine scales and leaves this map flat; a selection
change that alters tone shows up as structure.
"""
import sys
import numpy as np
import tifffile
from PIL import Image
from scipy.ndimage import uniform_filter

a = tifffile.imread(sys.argv[1]).astype(np.float32)
b = tifffile.imread(sys.argv[2]).astype(np.float32)
d = (b - a).mean(-1)
lp = uniform_filter(d, 31)
q = np.quantile(np.abs(lp), [0.5, 0.99, 0.999])
print(f"signed mean {d.mean():.2f} DN; |low-pass| p50 {q[0]:.1f} p99 {q[1]:.1f} "
      f"p99.9 {q[2]:.1f} max {np.abs(lp).max():.1f}")
Image.fromarray(np.clip(128 + lp[::4, ::4] / 80, 0, 255).astype(np.uint8)).save(sys.argv[3])
