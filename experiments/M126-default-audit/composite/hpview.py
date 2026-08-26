"""M126: high-pass view -- shows the pixel-to-pixel component directly.

The flat crop's SD is nearly identical across arms (it is dominated by the
backdrop's smooth lighting ramp) while its gradient energy differs 3.5x.
Those two facts reconcile only if the arms differ in the HIGH-FREQUENCY
component. This renders that component so it can be looked at.

view = (crop - box5(crop)) * gain + 128, one fixed gain for every arm,
chosen from arm A. Still the pixels; a display transform, like a gamma.
"""
import sys, json, os
import numpy as np
import tifffile  # hard import -- no PIL fallback
from PIL import Image, ImageDraw  # 8-bit WRITE only

TAG, CROP, ARMS = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"
OUT = r"C:\dev\strehl-out\M126-COMPOSITE\crops"
S = 512
x0, y0 = json.load(open(rf"{ROOT}\crops.json"))[CROP]
K = 5


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a


def box(a, k=K):
    """Separable box mean via cumulative sums, edges replicated."""
    p = np.pad(a, ((k // 2, k // 2), (k // 2, k // 2), (0, 0)), mode="edge")
    c = np.cumsum(np.cumsum(p.astype(np.float64), axis=0), axis=1)
    c = np.pad(c, ((1, 0), (1, 0), (0, 0)))
    h, w = a.shape[:2]
    s = (c[k:k + h, k:k + w] - c[0:h, k:k + w]
         - c[k:k + h, 0:w] + c[0:h, 0:w])
    return (s / (k * k)).astype(np.float32)


def hp(p):
    c = load(p)[y0:y0 + S, x0:x0 + S].astype(np.float32)
    return c - box(c)


ref = hp(rf"{ROOT}\lin\A.tif")
gain = 96.0 / max(np.percentile(np.abs(ref), 99.5), 1e-6)
print(f"fixed gain from arm A: {gain:.3f}  (p99.5 |hp| = {np.percentile(np.abs(ref),99.5):.1f} DN)")
print()
tiles = []
for arm in ARMS:
    p = rf"{ROOT}\lin\{arm}.tif"
    if not os.path.exists(p):
        print(f"  MISSING {arm}")
        continue
    h = hp(p)
    v8 = np.clip(h * gain + 128, 0, 255).astype(np.uint8)
    Image.fromarray(v8).save(rf"{OUT}\{TAG}-{CROP}-HP-{arm}.png")
    tiles.append((arm, v8))
    print(f"{arm:4s} hp rms = {float(np.sqrt((h**2).mean())):8.2f} DN   "
          f"p99.5|hp| = {float(np.percentile(np.abs(h),99.5)):8.2f} DN")

W = S * len(tiles)
m = Image.new("RGB", (W, S + 22), (0, 0, 0))
for i, (arm, t) in enumerate(tiles):
    m.paste(Image.fromarray(t), (i * S, 22))
d = ImageDraw.Draw(m)
for i, (arm, _) in enumerate(tiles):
    d.text((i * S + 6, 5), arm, fill=(255, 255, 0))
m.save(rf"{OUT}\{TAG}-{CROP}-HP-MONTAGE.png")
print(f"\nwrote {OUT}\\{TAG}-{CROP}-HP-*.png")
