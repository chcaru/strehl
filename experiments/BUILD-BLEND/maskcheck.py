"""Which side of the threshold is the GROUND? Look, do not assume.

dnlevel.py refused coffee-bean on a >50% dark-fraction guard. That guard was
written for lavendar-cpl, where a BRIGHT subject on darker ground makes the
"largest dark component" the backdrop and the profile silently describes the
wrong pixels. But a >50% dark fraction has two causes and the guard cannot tell
them apart:

    dark GROUND   -> the mask is inverted, a profile would be wrong
    dark SUBJECT that is simply large -> the mask is right, the guard is a
                                         false positive

Guessing between them is how this project has repeatedly shipped a confident
number for the wrong region. So this measures it two ways and writes a picture.

THE TEST
    The backdrop is the thing that surrounds the subject, so it is the thing
    that touches the frame border. A subject can run off one or two edges; a
    sweep touches all four and dominates the border ring.

THE PICTURE
    A downsampled overlay, red where the mask says "subject". Looking at it
    settles in one second what a scalar argues about.
"""
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SRC = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else None

im = tifffile.imread(SRC)
assert im.dtype == np.uint16, f"expected uint16 linear, got {im.dtype}"
lum = im.astype(np.float32).mean(axis=2)

lo, hi = np.percentile(lum, [5, 95])
thr = 0.5 * (lo + hi)
dark = lum < thr
print(f"{SRC}")
print(f"  p5={lo:.0f} p95={hi:.0f} thr={thr:.0f} dark-fraction={dark.mean()*100:.2f}%")

lab, n = ndimage.label(dark)
sizes = ndimage.sum(dark, lab, range(1, n + 1))
order = np.argsort(sizes)[::-1]
big = lab == (1 + int(order[0]))
print(f"  {n} dark components; largest = {big.mean()*100:.2f}% of frame")

# --- border ring: the backdrop is what surrounds ----------------------------
W = 8
ring = np.zeros(lum.shape, bool)
ring[:W, :] = ring[-W:, :] = True
ring[:, :W] = ring[:, -W:] = True
print(f"  border ring ({W} px): {dark[ring].mean()*100:.1f}% dark, "
      f"largest-component covers {big[ring].mean()*100:.1f}% of it")

# Which edges does the largest dark component touch?
edges = {
    "top": big[:W, :].mean(), "bottom": big[-W:, :].mean(),
    "left": big[:, :W].mean(), "right": big[:, -W:].mean(),
}
touched = [k for k, v in edges.items() if v > 0.25]
print("  edges the largest dark component covers >25% of: "
      f"{touched if touched else 'none'}")
print("  per-edge coverage: " + "  ".join(f"{k}={v*100:.0f}%" for k, v in edges.items()))

verdict = ("GROUND (mask is inverted for a dark-subject profiler)"
           if len(touched) == 4 else
           "SUBJECT (a large subject, guard would be a false positive)")
print(f"  READING: the largest dark component is the {verdict}")

if OUT:
    step = max(1, lum.shape[0] // 900)
    small = lum[::step, ::step]
    m = big[::step, ::step]
    v = np.clip(small / max(np.percentile(small, 99.5), 1.0), 0, 1) ** (1 / 2.2)
    rgb = np.repeat((v * 255).astype(np.uint8)[:, :, None], 3, axis=2)
    rgb[m, 0] = np.minimum(255, rgb[m, 0].astype(int) + 110)
    rgb[m, 1] = (rgb[m, 1] * 0.45).astype(np.uint8)
    rgb[m, 2] = (rgb[m, 2] * 0.45).astype(np.uint8)
    Image.fromarray(rgb).save(OUT)
    print(f"  wrote {OUT}  (red = what the mask calls subject)")
