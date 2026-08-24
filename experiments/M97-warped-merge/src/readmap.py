"""B5: is the election map real content, or a degenerate probe?

Also gives M110/the blob hypothesis its first free datapoint: the density and
spatial structure of election boundaries.
"""
import sys
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
path = sys.argv[1]
a = np.array(Image.open(path))
print(f"file        : {path}")
print(f"shape/dtype : {a.shape} {a.dtype}")
n = a.size
vals, counts = np.unique(a, return_counts=True)
print(f"distinct    : {len(vals)} indices, range {vals.min()}..{vals.max()}")
print(f"sentinel    : {int((a == 65535).sum())} pixels at u16::MAX (must be 0)")

top = np.argsort(counts)[::-1][:6]
print("top indices : " + ", ".join(f"{vals[i]}={100.0*counts[i]/n:.1f}%" for i in top))
print(f"modal share : {100.0*counts.max()/n:.2f}%  (100% would mean a dead map)")

ai = a.astype(np.int32)
dx = ai[:, 1:] != ai[:, :-1]
dy = ai[1:, :] != ai[:-1, :]
print(f"boundaries  : {100.0*dx.mean():.2f}% of horizontal, "
      f"{100.0*dy.mean():.2f}% of vertical adjacent pairs elect different frames")

# Structure vs noise: a real depth map is piecewise smooth, so |delta| at a
# boundary should be small. Salt-and-pepper would jump far.
mag = np.abs(ai[:, 1:] - ai[:, :-1])[dx]
if mag.size:
    print(f"jump size   : median {np.median(mag):.1f}, mean {mag.mean():.2f}, "
          f"p99 {np.percentile(mag, 99):.1f} frames across a boundary")
    print(f"  |delta|=1 : {100.0*(mag == 1).mean():.1f}% of boundaries are single-frame steps")

# A shuffled control: if the map were spatially structureless, boundary density
# would be unchanged by permuting pixels. This is the plant for "is it smooth".
rng = np.random.default_rng(0)
flat = a.ravel().copy()
rng.shuffle(flat)
s = flat.reshape(a.shape).astype(np.int32)
sdx = (s[:, 1:] != s[:, :-1]).mean()
print(f"SHUFFLE CTRL: {100.0*sdx:.2f}% horizontal boundaries after permuting the "
      f"same values")
print(f"  -> structure factor {sdx / max(dx.mean(), 1e-12):.1f}x "
      f"(1.0x would mean the map is spatial noise)")
