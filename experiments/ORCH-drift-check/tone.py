"""Is the shipped render tonally correct, or just dull?

The full-frame preview reads grey and flat. A white card under even light
should sit near the top of the range; if strehl's --srgb output puts it at
mid grey, every render this project has ever shown has been handicapped by
a scaling error rather than by its stacking.
"""
import numpy as np
import tifffile

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
a = tifffile.imread(SRC)
print("dtype %s shape %s" % (a.dtype, a.shape))
f = a.astype(np.float64) / 65535.0

for i, ch in enumerate("RGB"):
    c = f[..., i]
    print("%s  min %.4f  p1 %.4f  p50 %.4f  p99 %.4f  p99.9 %.4f  max %.4f"
          % (ch, c.min(), np.percentile(c, 1), np.percentile(c, 50),
             np.percentile(c, 99), np.percentile(c, 99.9), c.max()))

g = f.mean(axis=2)
print()
print("luma p99.9 = %.4f   -> headroom unused: %.2f stops"
      % (np.percentile(g, 99.9), -np.log2(max(np.percentile(g, 99.9), 1e-9))))

# The background is the brightest large flat area. What tone does it land on?
H, W = g.shape
corner = g[:H // 6, -W // 6:]
print("top-right background patch: mean %.4f  sd %.5f" % (corner.mean(), corner.std()))

# Clipping check: how much is at or near full scale?
print("fraction >= 0.999 : %.6f%%" % (100.0 * (g >= 0.999).mean()))
print("fraction <= 0.001 : %.6f%%" % (100.0 * (g <= 0.001).mean()))

# Saturation: how colourful is it?
mx = f.max(axis=2); mn = f.min(axis=2)
sat = np.where(mx > 1e-6, (mx - mn) / np.maximum(mx, 1e-6), 0.0)
print("saturation: median %.4f  p90 %.4f" % (np.median(sat), np.percentile(sat, 90)))
