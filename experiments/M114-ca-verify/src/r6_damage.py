"""M114 R6 -- find where the correction does the most DAMAGE and look at it.

Falsification-first: the aggregate is better, so the question is whether there
is a LOCAL population that got worse and would be visible.

  P1  block-wise (384x384) change in fringe area (chroma>0.06 within 3px of a
      strong edge).  Report the 5 WORST blocks (largest increase) and crop them.
  P2  the same for mean |R-Y| near edges.
  P3  clipped/near-clipped highlights: pixels where any OFF channel >= 64000 DN.
      Moving red under a clipped green is a classic way to make a magenta rim.
  P4  the single worst 64x64 tile by increase in mean |R-Y|.
"""
import os
import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

OFF = r"C:\dev\strehl-out\M114-ca-verify\r1\unset.tif"
ON = r"C:\dev\strehl-out\M114-ca-verify\r1\on.tif"
OUT = r"C:\dev\strehl-out\M114-ca-verify\crops"
os.makedirs(OUT, exist_ok=True)
S = 384

a0 = tifffile.imread(OFF)
a1 = tifffile.imread(ON)
H, W, _ = a0.shape
f0 = a0.astype(np.float32) / np.float32(65535.0)
f1 = a1.astype(np.float32) / np.float32(65535.0)
r0, g0, b0 = f0[..., 0], f0[..., 1], f0[..., 2]
r1, g1, b1 = f1[..., 0], f1[..., 1], f1[..., 2]
y0 = 0.2126 * r0 + 0.7152 * g0 + 0.0722 * b0
y1 = 0.2126 * r1 + 0.7152 * g1 + 0.0722 * b1
gy, gx = np.gradient(y0)
edge = np.hypot(gx, gy) >= np.quantile(np.hypot(gx, gy), 0.99)
near = ndimage.distance_transform_edt(~edge) <= 3
c0 = np.maximum(np.abs(r0 - y0), np.abs(b0 - y0))
c1 = np.maximum(np.abs(r1 - y1), np.abs(b1 - y1))
hot0 = (near & (c0 > 0.06)).astype(np.float32)
hot1 = (near & (c1 > 0.06)).astype(np.float32)
d0 = np.where(near, np.abs(r0 - y0), 0).astype(np.float32)
d1 = np.where(near, np.abs(r1 - y1), 0).astype(np.float32)
nearf = near.astype(np.float32)

cx, cy = W * 0.5, H * 0.5


def blocks(a, s):
    ny, nx = H // s, W // s
    return a[:ny * s, :nx * s].reshape(ny, s, nx, s).sum(axis=(1, 3))


def to8(a):
    return np.clip(a.astype(np.float32) / 257.0, 0, 255).astype(np.uint8)


def save_pair(name, y, x, s):
    q0, q1 = a0[y:y + s, x:x + s], a1[y:y + s, x:x + s]
    pair = np.concatenate([to8(q0), np.full((s, 6, 3), 255, np.uint8), to8(q1)], axis=1)
    Image.fromarray(pair).save(os.path.join(OUT, name + "_1to1.png"))
    k = min(128, s)
    oy, ox = (s - k) // 2, (s - k) // 2
    z0 = np.kron(to8(q0[oy:oy + k, ox:ox + k]), np.ones((4, 4, 1), np.uint8))
    z1 = np.kron(to8(q1[oy:oy + k, ox:ox + k]), np.ones((4, 4, 1), np.uint8))
    Image.fromarray(np.concatenate(
        [z0, np.full((k * 4, 8, 3), 255, np.uint8), z1], axis=1)).save(
        os.path.join(OUT, name + "_zoom4x.png"))


bh0, bh1 = blocks(hot0, S), blocks(hot1, S)
bn = blocks(nearf, S)
bd0, bd1 = blocks(d0, S), blocks(d1, S)
ny, nx = bh0.shape
delta_area = bh1 - bh0
ok = bn > 2000
print("=== P1 blocks (384x384) ranked by INCREASE in fringe area ===")
print("  rank   y     x     r      near_px   area_off  area_on   delta")
flat_idx = np.argsort(np.where(ok, delta_area, -1e18).ravel())[::-1]
worst = []
for k in range(5):
    j, i = divmod(int(flat_idx[k]), nx)
    y, x = j * S, i * S
    rr = float(np.hypot(x + S / 2 - cx, y + S / 2 - cy) / np.hypot(cx, cy))
    print("  %4d %5d %5d  %.3f  %8d  %8d  %8d  %+7d"
          % (k + 1, y, x, rr, bn[j, i], bh0[j, i], bh1[j, i], delta_area[j, i]))
    worst.append((y, x))
save_pair("worst_area", worst[0][0], worst[0][1], S)

print("\n=== P2 blocks ranked by INCREASE in summed |R-Y| near edges ===")
dd = bd1 - bd0
flat_idx = np.argsort(np.where(ok, dd, -1e18).ravel())[::-1]
for k in range(5):
    j, i = divmod(int(flat_idx[k]), nx)
    y, x = j * S, i * S
    rr = float(np.hypot(x + S / 2 - cx, y + S / 2 - cy) / np.hypot(cx, cy))
    m_off = bd0[j, i] / max(bn[j, i], 1)
    m_on = bd1[j, i] / max(bn[j, i], 1)
    print("  %4d %5d %5d  %.3f  near=%7d  mean|R-Y| off=%.6f on=%.6f  %+.2f%%"
          % (k + 1, y, x, rr, bn[j, i], m_off, m_on, 100 * (m_on - m_off) / m_off))
    if k == 0:
        save_pair("worst_rdev", y, x, S)

print("\n=== P3 clipped / near-clipped highlights ===")
clip = (a0.max(axis=2) >= 64000)
print("  near-clipped px = %d (%.4f%% of frame)" % (clip.sum(), 100 * clip.mean()))
if clip.sum() > 0:
    halo = ndimage.binary_dilation(clip, iterations=4) & ~clip
    h0 = np.abs(r0 - y0)[halo].astype(np.float64)
    h1 = np.abs(r1 - y1)[halo].astype(np.float64)
    print("  halo ring (<=4px around a clipped px), n=%d" % halo.sum())
    print("  mean |R-Y| off=%.6f (%.1f DN)  on=%.6f (%.1f DN)  %+.2f%%"
          % (h0.mean(), h0.mean() * 65535, h1.mean(), h1.mean() * 65535,
             100 * (h1.mean() - h0.mean()) / h0.mean()))
    for p in [90, 99, 99.9]:
        print("    P%-5.1f off=%.6f  on=%.6f" % (p, np.percentile(h0, p),
                                                 np.percentile(h1, p)))

print("\n=== P4 worst 64x64 tile by increase in mean |R-Y| near edges ===")
T = 64
t0, t1, tn = blocks(d0, T), blocks(d1, T), blocks(nearf, T)
tny, tnx = t0.shape
okt = tn > 200
gain = np.where(okt, (t1 - t0) / np.maximum(tn, 1), -1e18)
idx = int(np.argmax(gain))
j, i = divmod(idx, tnx)
y, x = j * T, i * T
rr = float(np.hypot(x + T / 2 - cx, y + T / 2 - cy) / np.hypot(cx, cy))
print("  tile at y=%d x=%d r=%.3f  near=%d  mean|R-Y| off=%.6f on=%.6f %+.1f%%"
      % (y, x, rr, tn[j, i], t0[j, i] / tn[j, i], t1[j, i] / tn[j, i],
         100 * (t1[j, i] - t0[j, i]) / t0[j, i]))
yy = max(0, min(H - S, y - S // 2 + T // 2))
xx = max(0, min(W - S, x - S // 2 + T // 2))
save_pair("worst_tile", yy, xx, S)
print("\nwrote crops to", OUT)
