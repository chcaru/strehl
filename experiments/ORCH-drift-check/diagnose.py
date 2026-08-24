"""Survey the shipped render for visible defects at 100%.

Tiles a grid of full-resolution crops so the orchestrator can find what is
actually wrong with the photograph, rather than guessing from the corpus.
"""
import os
import numpy as np
import tifffile
from PIL import Image, ImageDraw

SRC = r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif"
OUT = r"C:\dev\strehl-out\ORCH-diagnose"
os.makedirs(OUT, exist_ok=True)

a = tifffile.imread(SRC)
H, W = a.shape[:2]
print("render %dx%d %s" % (W, H, a.dtype))

g = a.astype(np.float32).mean(axis=2)


def tenengrad_map(img, blk):
    gx = np.zeros_like(img); gy = np.zeros_like(img)
    gx[:, 1:-1] = img[:, 2:] - img[:, :-2]
    gy[1:-1, :] = img[2:, :] - img[:-2, :]
    e = gx * gx + gy * gy
    h, w = e.shape
    h2, w2 = h // blk, w // blk
    return e[:h2 * blk, :w2 * blk].reshape(h2, blk, w2, blk).mean(axis=(1, 3))


BLK = 64
tm = tenengrad_map(g, BLK)
print("detail map %dx%d blocks" % tm.shape[::-1])

# Downscale preview with the detail grid drawn on, so I can see where the
# render is sharp and where it is not, in one image.
prev = Image.fromarray(np.clip(a[::6, ::6] / 257.0, 0, 255).astype(np.uint8))
prev.save(os.path.join(OUT, "full.png"))
print("wrote full.png %dx%d" % prev.size)

hm = np.log10(tm + 1.0)
hm = (hm - hm.min()) / max(hm.max() - hm.min(), 1e-9)
Image.fromarray((hm * 255).astype(np.uint8)).resize(
    prev.size, Image.NEAREST).save(os.path.join(OUT, "detail-map.png"))

# A 4x3 grid of 100% crops covering the frame.
N = 460
ROWS, COLS = 3, 4
tile = Image.new("RGB", (COLS * (N + 6), ROWS * (N + 22)), (16, 16, 16))
dr = ImageDraw.Draw(tile)
for r in range(ROWS):
    for c in range(COLS):
        y = int((r + 0.5) * H / ROWS) - N // 2
        x = int((c + 0.5) * W / COLS) - N // 2
        y = max(0, min(H - N, y)); x = max(0, min(W - N, x))
        crop = np.clip(a[y:y + N, x:x + N] / 257.0, 0, 255).astype(np.uint8)
        px, py = c * (N + 6), r * (N + 22)
        tile.paste(Image.fromarray(crop), (px, py + 20))
        dr.text((px + 4, py + 5), "r%dc%d  x=%d y=%d" % (r, c, x, y),
                fill=(210, 210, 120))
tile.save(os.path.join(OUT, "grid.png"))
print("wrote grid.png %dx%d" % tile.size)

# Where is the render least detailed relative to its neighbourhood? Those
# blocks are candidate defects (smear, halo, wrong winner).
print()
print("global detail percentiles:", [round(float(np.percentile(tm, p)), 1)
                                     for p in (5, 25, 50, 75, 95, 99)])
