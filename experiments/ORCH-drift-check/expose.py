"""Show the owner what the stack actually contains, correctly exposed.

MEASURED: the RAW background sits at 0.296 of the sensor's usable range and
nothing in any of the 299 frames reaches 0.99 of white, so the bracket is
~1.76 stops under-exposed. strehl reproduces that faithfully (render 0.5734
vs RAW-predicted 0.5752). So the render looks grey because the capture is
grey, not because the stacking is weak.

This applies exposure only -- the operation a raw converter's exposure slider
performs -- so nothing here is strehl's output being flattered. No contrast
curve, no saturation, no sharpening, no local adjustment.
"""
import os
import numpy as np
import tifffile
from PIL import Image

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
OUT = r"C:\dev\strehl-out\ORCH-exposure"
os.makedirs(OUT, exist_ok=True)

BG_LINEAR = 0.296   # MEASURED from the RAWs, rawlevel.py
TARGET = 0.88       # where a white card should sit


def srgb_to_linear(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


a = tifffile.imread(SRC).astype(np.float32) / 65535.0
lin = srgb_to_linear(a)

gain = TARGET / BG_LINEAR
stops = np.log2(gain)
print("applying +%.2f stops (gain %.3fx)" % (stops, gain))

boosted = lin * gain
clipped = float((boosted.max(axis=2) > 1.0).mean())
print("fraction of pixels with any channel clipped: %.4f%%" % (100 * clipped))

outsrgb = linear_to_srgb(boosted)
g = outsrgb.mean(axis=2)
print("after: luma p50 %.4f  p99 %.4f  p99.9 %.4f"
      % tuple(float(np.percentile(g, q)) for q in (50, 99, 99.9)))

tifffile.imwrite(os.path.join(OUT, "bee-3-exposed.tif"),
                 (outsrgb * 65535.0).astype(np.uint16))
print("wrote bee-3-exposed.tif")

before = Image.fromarray((a[::6, ::6] * 255).astype(np.uint8))
after = Image.fromarray((outsrgb[::6, ::6] * 255).astype(np.uint8))
W, H = before.size
sbs = Image.new("RGB", (W * 2 + 10, H), (20, 20, 20))
sbs.paste(before, (0, 0))
sbs.paste(after, (W + 10, 0))
sbs.save(os.path.join(OUT, "exposure-before-after.png"))
after.save(os.path.join(OUT, "bee-3-exposed-preview.png"))
print("wrote exposure-before-after.png and bee-3-exposed-preview.png")

# A 100% crop of the head, correctly exposed, so the owner can judge the
# stacking rather than the tone.
Hf, Wf = a.shape[:2]
y, x, N = int(Hf * 0.62), int(Wf * 0.52), 1100
crop = (outsrgb[y:y + N, x:x + N] * 255).astype(np.uint8)
Image.fromarray(crop).save(os.path.join(OUT, "bee-3-exposed-head-100pct.png"))
print("wrote bee-3-exposed-head-100pct.png (100%% crop)")
