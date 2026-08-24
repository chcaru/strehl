"""M114 R5 -- 1:1 crops for an independent by-eye read.

Windows are chosen by STATED criteria, not by hand:
  W_fringe   highest count of near-edge pixels with chroma > 0.06, r in 0.5-0.75
  W_corner   same, restricted to r > 0.85 (PAST the declared 0.788 support)
  W_flat     lowest luminance-gradient energy with non-trivial signal
             (the population where injected chroma would be most visible)
  W_centre   highest edge-chroma count with r < 0.20 (correction ~ 0 there)
Each is written OFF | ON side by side at 1:1, plus a 4x nearest-neighbour zoom
of the central 128x128, plus a x8-amplified |on-off| difference image.
"""
import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
OUT = r"C:\dev\strehl-out\M114-ca-verify\crops"
S = 384
import os
os.makedirs(OUT, exist_ok=True)

a0 = tifffile.imread(OFF)
a1 = tifffile.imread(ON)
H, W, _ = a0.shape
f0 = a0.astype(np.float32) / np.float32(65535.0)
r0, g0, b0 = f0[..., 0], f0[..., 1], f0[..., 2]
y0 = 0.2126 * r0 + 0.7152 * g0 + 0.0722 * b0
gy, gx = np.gradient(y0)
gm = np.hypot(gx, gy)
edge = gm >= np.quantile(gm, 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3
chroma = np.maximum(np.abs(r0 - y0), np.abs(b0 - y0))
hot = (near & (chroma > 0.06)).astype(np.float32)

cx, cy = W * 0.5, H * 0.5
yy, xx = np.mgrid[0:H, 0:W]
rad = (np.hypot(xx - cx, yy - cy) / np.hypot(cx, cy)).astype(np.float32)

# block-sum on an S-grid
def blocks(a):
    ny, nx = H // S, W // S
    return a[:ny * S, :nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))

bh = blocks(hot)
br = blocks(rad)
bg = blocks(gm)
ny, nx = bh.shape


def pick(mask, arr, want_max=True):
    m = np.where(mask, arr, -np.inf if want_max else np.inf)
    idx = np.argmax(m) if want_max else np.argmin(m)
    j, i = divmod(int(idx), nx)
    return j * S, i * S


wins = {}
wins["fringe"] = pick((br > 0.50) & (br < 0.75), bh)
wins["corner"] = pick(br > 0.85, bh)
wins["centre"] = pick(br < 0.20, bh)
wins["flat"] = pick((bh < np.quantile(bh, 0.30)) & (br > 0.4), bg, want_max=False)

def to8(a):
    return (np.clip(a.astype(np.float32) / 257.0, 0, 255)).astype(np.uint8)

print("window   y0    x0     r      hot-density  meanGrad")
for name, (y, x) in wins.items():
    c0 = a0[y:y + S, x:x + S]
    c1 = a1[y:y + S, x:x + S]
    rr = float(rad[y + S // 2, x + S // 2])
    print("%-7s %5d %5d  %.3f   %.4f      %.5f"
          % (name, y, x, rr, hot[y:y + S, x:x + S].mean(),
             float(gm[y:y + S, x:x + S].mean())))
    pair = np.concatenate([to8(c0), np.full((S, 6, 3), 255, np.uint8), to8(c1)], axis=1)
    Image.fromarray(pair).save(os.path.join(OUT, "%s_1to1.png" % name))
    k = 128
    oy, ox = (S - k) // 2, (S - k) // 2
    z0 = np.kron(to8(c0[oy:oy + k, ox:ox + k]), np.ones((4, 4, 1), np.uint8))
    z1 = np.kron(to8(c1[oy:oy + k, ox:ox + k]), np.ones((4, 4, 1), np.uint8))
    zp = np.concatenate([z0, np.full((k * 4, 8, 3), 255, np.uint8), z1], axis=1)
    Image.fromarray(zp).save(os.path.join(OUT, "%s_zoom4x.png" % name))
    d = (c1.astype(np.int32) - c0.astype(np.int32))
    dv = np.clip(128 + d * 8 / 257.0, 0, 255).astype(np.uint8)
    Image.fromarray(dv).save(os.path.join(OUT, "%s_diff8x.png" % name))

print("wrote", OUT)
