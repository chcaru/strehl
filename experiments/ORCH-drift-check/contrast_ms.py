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

# Band edges are placed deliberately, not by octave convention.
#
# A Gaussian of width sigma cuts at f = 1/(2*pi*sigma) cyc/px, so sigma is
# chosen to land the band boundaries on the frequencies V-LINEAR qualified
# per-tile on this corpus:
#
#   0.17-0.20  ratio 4.874           PASS  -- carries signal
#   0.20-0.25  ratio 2.419           PASS  -- carries signal
#   0.25-0.30  ratio 1.387       MARGINAL
#   0.25-0.48                       NOISE
#
# sigma = 1/(2*pi*0.25) = 0.6366   -> boundary at 0.25, the noise edge
# sigma = 1/(2*pi*0.17) = 0.9362   -> boundary at 0.17, the signal edge
#
# giving band 0 = the noise region and band 1 = the QUALIFIED SIGNAL region.
# An acuity criterion must be read off band 1, not band 0 and not the coarse
# bands: the coarse bands are 0.01-0.08 cyc/px and a merge can destroy all
# visible acuity without moving them at all.
SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]


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


hdr = f"{'band':>6s} {'cyc/px':>14s} {'kind':>7s} " + " ".join(
    f"{k + ' A':>10s} {k + ' B':>10s} {'ratio':>7s}" for k in sites
)
print(hdr)
print("-" * len(hdr))

edges = [1.0 / (2.0 * np.pi * s) for s in SIGMAS]
rows = []
for j in range(len(SIGMAS)):
    hi = 0.5 if j == 0 else edges[j - 1]
    lo = edges[j]
    tag = {0: "NOISE", 1: "SIGNAL"}.get(j, "")
    line = f"{j:6d} {f'{lo:.3f}-{hi:.3f}':>14s} {tag:>7s} "
    row = {"band": j}
    for k, idx in sites.items():
        sa, sb = band_std(idx, ba[j]), band_std(idx, bb[j])
        r = sb / sa if sa > 0 else float("nan")
        row[k] = r
        line += f" {sa:10.2f} {sb:10.2f} {r:7.4f}"
    rows.append(row)
    print(line)

print()
print("READING (band edges are placed on V-LINEAR's qualification, see source):")
print("  band 0 = 0.25-0.5 cyc/px  -- NOISE on this corpus. Grain lives here.")
print("  band 1 = 0.17-0.25 cyc/px -- QUALIFIED SIGNAL. Acuity lives here.")
print("  bands 2+ are 0.01-0.08 cyc/px, far too coarse to be an acuity test.")
print()
print(f"  GRAIN WIN      band-0 FLAT ratio : {rows[0]['FLAT']:.4f}   (want << 1)")
print(f"  ACUITY COST    band-1 EDGE ratio : {rows[1]['EDGE']:.4f}   (want >= 0.98)")
print(f"  INSTRUMENT NULL coarsest EDGE    : {rows[-1]['EDGE']:.4f}   (want ~1.000)")
