"""Compare two masters for local contrast AFTER removing the global tone-placement
confound.

Rationale: both renders place tone on their own 99.9th percentile.  If arm B
averages more, its brightest peaks fall, the white point falls with them, and the
tone stage applies MORE gain -- so B comes out globally brighter.  That brightness
difference is a tone artifact and will read to the eye as "haze" / lost contrast
even if no micro-contrast was lost at all.

So: normalise B to A's median before measuring anything.  Then report
  - high-pass energy (micro-contrast) in flat sites and in edge sites separately
  - the ratio B/A of each
A real micro-contrast loss shows as hp_ratio < 1 at EDGE sites.
A pure grain win shows as hp_ratio < 1 at FLAT sites only.
Those are different outcomes and the whole point is to tell them apart.
"""
import sys
import numpy as np
import tifffile

A, B = sys.argv[1], sys.argv[2]


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


a, b = lum(A), lum(B)
assert a.shape == b.shape, f"shape mismatch {a.shape} {b.shape}"

ma, mb = np.median(a), np.median(b)
# remove the tone-placement confound: put B on A's level
scale = ma / mb
bn = b * scale
print(f"median A = {ma:9.1f}   median B = {mb:9.1f}   B rescaled by {scale:.4f}")


def highpass(x):
    # 3x3 box blur, subtract -> cheap high-pass; measure its local std
    k = np.ones((3, 3)) / 9.0
    from scipy.signal import fftconvolve
    lo = fftconvolve(x, k, mode="same")
    return x - lo


ha, hb = highpass(a), highpass(bn)

# choose sites on A only, so the comparison is not a good-news generator
S = 256
H, W = a.shape
gy, gx = np.gradient(a)
g = np.hypot(gy, gx)
# block-reduce gradient to SxS tiles
ny, nx = H // S, W // S
tile_g = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
order = np.argsort(tile_g.ravel())

n = 12
flat_idx = order[: n]
edge_idx = order[-n:]


def energy(idx, arr):
    vals = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        y, x = ty * S, tx * S
        vals.append(arr[y:y + S, x:x + S].std())
    return float(np.mean(vals))


def level(idx, arr):
    vals = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        y, x = ty * S, tx * S
        vals.append(arr[y:y + S, x:x + S].mean())
    return float(np.mean(vals))


for name, idx in (("FLAT", flat_idx), ("EDGE", edge_idx)):
    ea, eb = energy(idx, ha), energy(idx, hb)
    la, lb = level(idx, a), level(idx, bn)
    print(f"{name:5s} sites (n={n})  hp_std A = {ea:8.2f}   B = {eb:8.2f}   ratio B/A = {eb / ea:6.4f}"
          f"   |  level A = {la:8.1f}  B = {lb:8.1f}  lift = {lb - la:+8.1f} DN")

print()
print("interpretation:")
print("  FLAT ratio < 1  -> grain reduced (the win)")
print("  EDGE ratio < 1  -> micro-contrast lost (the cost)")
print("  a good arm has FLAT well below 1 and EDGE at ~1.0")
