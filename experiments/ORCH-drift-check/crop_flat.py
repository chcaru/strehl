"""Crop two masters at the SAME sites, chosen as the lowest-gradient tiles of A.

crop_ab.py picks high-gradient sites, which is right for showing acuity and
wrong for showing grain.  This is its complement: it shows the flat ground,
which is where the noise defect lives.

Sites are chosen on A only and reused verbatim on B.  B is rescaled to A's
median first, so the pair differs only by what the merge did -- not by where the
tone stage happened to place each arm's white point (see contrast_ab.py).
"""
import sys
import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

A, B, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LA = sys.argv[4] if len(sys.argv) > 4 else "A"
LB = sys.argv[5] if len(sys.argv) > 5 else "B"
N = int(sys.argv[6]) if len(sys.argv) > 6 else 2
S = 384

import os
os.makedirs(OUT, exist_ok=True)

a16 = tifffile.imread(A)
b16 = tifffile.imread(B)
assert a16.shape == b16.shape

la = a16[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
lb = b16[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
scale = np.median(la) / np.median(lb)
print(f"B rescaled by {scale:.4f} to remove the tone-placement confound")

mid = gaussian_filter(la, 2.0)
gy, gx = np.gradient(mid)
g = np.hypot(gy, gx)
H, W = la.shape
ny, nx = H // S, W // S
tile = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
order = np.argsort(tile.ravel())


def to8(x):
    return np.clip(x / 257.0, 0, 255).astype(np.uint8)


picked = 0
for f in order:
    if picked >= N:
        break
    ty, tx = divmod(int(f), nx)
    y, x = ty * S, tx * S
    ca = a16[y:y + S, x:x + S, :3].astype(np.float64)
    cb = b16[y:y + S, x:x + S, :3].astype(np.float64) * scale
    # skip near-black tiles: nothing to see and they flatter the smoother arm
    if ca.mean() < 3000:
        continue
    picked += 1
    pane = Image.new("RGB", (S * 2 + 30, S + 26), (20, 20, 20))
    pane.paste(Image.fromarray(to8(ca)), (10, 20))
    pane.paste(Image.fromarray(to8(cb)), (S + 20, 20))
    d = ImageDraw.Draw(pane)
    d.text((10, 5), f"{LA} @ ({x},{y}) 1:1 FLAT", fill=(230, 230, 230))
    d.text((S + 20, 5), f"{LB} @ ({x},{y}) 1:1 FLAT", fill=(230, 230, 230))
    p = os.path.join(OUT, f"flat{picked:02d}_y{y}_x{x}.png")
    pane.save(p)
    sa = (ca[..., 1] - gaussian_filter(ca[..., 1], 1.0)).std()
    sb = (cb[..., 1] - gaussian_filter(cb[..., 1], 1.0)).std()
    print(f"{p}  mean={ca.mean():8.0f}  fine-grain A={sa:7.2f} B={sb:7.2f}  ratio={sb / sa:.4f}")
