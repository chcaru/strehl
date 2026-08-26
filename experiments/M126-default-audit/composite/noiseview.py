"""M126: high-gain view of a near-saturated flat field.

The global display transform maps the 99.7th percentile to white, which
saturates a bright background and hides exactly the noise the flat crop
exists to show. This windows tightly around the background level instead.

The window is computed from ARM A ONLY and reused byte-for-byte on every
arm, so any visible difference between arms is real. For LOOKING, not for
measuring -- the linear TIFFs remain the measurement.
"""
import sys, json, os
import numpy as np
import tifffile  # hard import -- no PIL fallback
from PIL import Image, ImageDraw  # 8-bit WRITE only

TAG = sys.argv[1]
CROP = sys.argv[2]
ARMS = sys.argv[3].split(",")
NSD = float(sys.argv[4]) if len(sys.argv) > 4 else 4.0
ROOT = rf"C:\dev\strehl-out\M126-COMPOSITE\{TAG}"
OUT = r"C:\dev\strehl-out\M126-COMPOSITE\crops"
S = 512
x0, y0 = json.load(open(rf"{ROOT}\crops.json"))[CROP]


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: dtype {a.dtype}, expected uint16"
    return a


ref = load(rf"{ROOT}\lin\A.tif")[y0:y0 + S, x0:x0 + S].astype(np.float32)
mu = ref.mean(axis=(0, 1))
sd = ref.std(axis=(0, 1))
lo = mu - NSD * sd
hi = mu + NSD * sd
print(f"window from arm A: mean={mu.round(1).tolist()} sd={sd.round(1).tolist()}")
print(f"  lo={lo.round(1).tolist()} hi={hi.round(1).tolist()}  (+/-{NSD} sd)")
print()
tiles = []
for arm in ARMS:
    p = rf"{ROOT}\lin\{arm}.tif"
    if not os.path.exists(p):
        print(f"  MISSING {arm}")
        continue
    c = load(p)[y0:y0 + S, x0:x0 + S].astype(np.float32)
    v = np.clip((c - lo) / np.maximum(hi - lo, 1e-6), 0, 1)
    v8 = (v * 255 + 0.5).astype(np.uint8)
    Image.fromarray(v8).save(rf"{OUT}\{TAG}-{CROP}-HIGAIN-{arm}.png")
    tiles.append((arm, v8))
    print(f"{arm:4s} sd={c.std(axis=(0,1)).round(1).tolist()}  "
          f"mean={c.mean(axis=(0,1)).round(1).tolist()}")

W = S * len(tiles)
m = Image.new("RGB", (W, S + 22), (0, 0, 0))
for i, (arm, t) in enumerate(tiles):
    m.paste(Image.fromarray(t), (i * S, 22))
d = ImageDraw.Draw(m)
for i, (arm, _) in enumerate(tiles):
    d.text((i * S + 6, 5), arm, fill=(255, 255, 0))
m.save(rf"{OUT}\{TAG}-{CROP}-HIGAIN-MONTAGE.png")
print(f"\nwrote {OUT}\\{TAG}-{CROP}-HIGAIN-*.png")
