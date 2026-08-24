import os
import numpy as np
import tifffile
from PIL import Image, ImageDraw

OUT = r"C:\dev\strehl-out\ORCH-morning"
D = r"C:\dev\strehl-out\M86-align"

a = tifffile.imread(os.path.join(OUT, "bee-3-strehl.tif"))
z = tifffile.imread(os.path.join(D, "bee3-zoomnull.tif"))
H, W = a.shape[:2]
assert z.shape[:2] == (H, W)

# Sanity: the fresh HEAD render must match M86's aligned render, since nothing
# between them touched a pixel (only lib.rs/main.rs doc + a module registration).
ref = tifffile.imread(os.path.join(D, "bee-3-ALIGNED.tif"))
d = np.abs(a.astype(np.int32) - ref.astype(np.int32))
print("fresh-vs-M86 aligned: max abs diff %d DN, mean %.4f" % (d.max(), d.mean()))

S = W / 1400.0
REGIONS = {
    "wing bristles": (int(300 * S), int(100 * S)),
    "leg spines":    (int(250 * S), int(560 * S)),
}
N = 620

for name, (x, y) in REGIONS.items():
    x = max(0, min(W - N, x)); y = max(0, min(H - N, y))
    ca = np.clip(a[y:y + N, x:x + N] / 257.0, 0, 255).astype(np.uint8)
    cz = np.clip(z[y:y + N, x:x + N] / 257.0, 0, 255).astype(np.uint8)
    bar = 34
    canvas = Image.new("RGB", (N * 2 + 12, N + bar), (18, 18, 18))
    canvas.paste(Image.fromarray(ca), (0, bar))
    canvas.paste(Image.fromarray(cz), (N + 12, bar))
    dr = ImageDraw.Draw(canvas)
    dr.text((8, 10), "strehl, ALIGNED (default)", fill=(120, 255, 120))
    dr.text((N + 20, 10), "same pixels, registration discarded", fill=(255, 150, 150))
    slug = name.replace(" ", "-")
    canvas.save(os.path.join(OUT, "compare-%s.png" % slug))
    print("wrote compare-%s.png" % slug)

im = Image.fromarray(np.clip(a / 257.0, 0, 255).astype(np.uint8))
im.thumbnail((1600, 1600), Image.LANCZOS)
im.save(os.path.join(OUT, "bee-3-strehl-preview.png"))
print("wrote bee-3-strehl-preview.png", im.size)
