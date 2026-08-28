"""Multi-scale version of contrast_ab.py.

WHY THIS EXISTS.  contrast_ab.py measures a single high-pass band (image minus a
3x3 box), which passes roughly 0.17-0.5 cyc/px.  V-LINEAR measured 0.20-0.48
cyc/px to be a NOISE band on this corpus -- in-focus/defocused band power ratios
of 1.004-1.138 where real signal gives >= 2.  If that holds here, then a "loss of
micro-contrast" measured in that band is a loss of NOISE, and using it as an
acuity criterion would reject an arm for the very thing it is supposed to do.

So decompose into octaves and report each separately.  The question is not "did
high-frequency energy drop" but "AT WHICH SCALES did it drop, and do those
scales carry structure".

  band 0  = x - G(1)          finest, noise-dominated on this corpus
  band 1  = G(1) - G(2)
  band 2  = G(2) - G(4)
  band 3  = G(4) - G(8)
  band 4  = G(8) - G(16)      coarse, unambiguously structure

Real acuity loss shows up in bands 1-3 at EDGE sites.
A pure grain win is confined to band 0, and shows at FLAT sites.
Those are different signatures and the whole point is to tell them apart.

The tone-placement confound is removed first (see contrast_ab.py).
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

A, B = sys.argv[1], sys.argv[2]
SIGMAS = [1.0, 2.0, 4.0, 8.0, 16.0]


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


a, b = lum(A), lum(B)
assert a.shape == b.shape, f"shape mismatch {a.shape} {b.shape}"

ma, mb = np.median(a), np.median(b)
scale = ma / mb
bn = b * scale
print(f"median A = {ma:9.1f}   median B = {mb:9.1f}   B rescaled by {scale:.4f}  (tone confound removed)")
print()


def octaves(x):
    """Return list of band images, finest first."""
    bands = []
    prev = x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        bands.append(prev - cur)
        prev = cur
    return bands


ba, bb = octaves(a), octaves(bn)

# sites chosen on A only, using a MID-scale gradient so that site selection is
# not itself driven by the noise band under test
mid = gaussian_filter(a, 2.0)
gy, gx = np.gradient(mid)
g = np.hypot(gy, gx)

S = 256
H, W = a.shape
ny, nx = H // S, W // S
tile_g = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
order = np.argsort(tile_g.ravel())

n = 12
sites = {"FLAT": order[:n], "EDGE": order[-n:]}


def band_std(idx, arr):
    vals = []
    for f in idx:
        ty, tx = divmod(int(f), nx)
        y, x = ty * S, tx * S
        vals.append(arr[y:y + S, x:x + S].std())
    return float(np.mean(vals))


hdr = f"{'band':>6s} {'approx cyc/px':>14s} " + " ".join(
    f"{k + ' A':>10s} {k + ' B':>10s} {'ratio':>7s}" for k in sites
)
print(hdr)
print("-" * len(hdr))

edges = [0.5 / s for s in SIGMAS]
rows = []
for j in range(len(SIGMAS)):
    hi = 0.5 if j == 0 else edges[j - 1]
    lo = edges[j]
    line = f"{j:6d} {f'{lo:.3f}-{hi:.3f}':>14s} "
    row = {"band": j}
    for k, idx in sites.items():
        sa, sb = band_std(idx, ba[j]), band_std(idx, bb[j])
        r = sb / sa if sa > 0 else float("nan")
        row[k] = r
        line += f" {sa:10.2f} {sb:10.2f} {r:7.4f}"
    rows.append(row)
    print(line)

print()
print("READING:")
print("  grain win  = band 0 FLAT ratio well below 1")
print("  acuity cost= bands 1-3 EDGE ratio below 1")
print("  if the change is confined to band 0, the single-band 'micro-contrast")
print("  cost' was a noise measurement, not an acuity measurement")
worst = min(rows[1:4], key=lambda r: r["EDGE"])
print()
print(f"  worst structural EDGE ratio (bands 1-3): {worst['EDGE']:.4f} at band {worst['band']}")
print(f"  band 0 FLAT ratio:                       {rows[0]['FLAT']:.4f}")
