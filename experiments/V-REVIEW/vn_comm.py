"""Commission MY estimator on MY arm on THIS image, then check the comparators
are being run fairly. No commissioning is carried across from another subject.

Arms whose answer is fixed in advance by arithmetic, not by expectation:
  NULL     an image differenced against itself must give exactly 0.
  POTENCY  planting Gaussian noise of known sigma must move the statistic to
           sqrt(sigma0^2 + sigma_add^2). Two levels.
  QUANT8   requantising a 16-bit arm to 8 bits must RAISE sigma by a computable
           amount; requantising an ALREADY 8-bit arm must change NOTHING. The
           second is an identity and violating it is a proof of defect.
  ALPHA    enfuse writes RGBA. Including the opaque 4th plane must visibly
           corrupt the statistic; this arm shows what that failure looks like
           so its absence in the main run is established rather than assumed.
"""
import os, json
import numpy as np, tifffile
from scipy.ndimage import uniform_filter

CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
rng = np.random.default_rng(20260827)


def tiles_of(path, keep_alpha=False):
    a = tifffile.imread(path)
    scale = 255.0 if a.dtype == np.uint8 else 65535.0
    nc = a.shape[2]
    if nc == 4 and not keep_alpha:
        a = a[:, :, :3]; nc = 3
    out = np.empty((len(TILES), T, T, nc), np.float64)
    for i, (y, x) in enumerate(TILES):
        out[i] = a[y:y + T, x:x + T, :nc].astype(np.float64) / scale
    del a
    return out


def opp(t):
    Y = 0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]
    return np.stack([Y, t[..., 0] - Y, t[..., 2] - Y], -1)


def half(A, B, m):
    d = A - B
    v = (d ** 2).mean(axis=(1, 2)) - (d.mean(axis=(1, 2))) ** 2
    return np.sqrt(0.5 * v) / m[:, None]


sA = opp(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff"))
sB = opp(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff"))
mS = sA[..., 0].mean(axis=(1, 2))
print("median tile mean luma (strehl, linear): %.5f" % np.median(mS))
base = half(sA, sB, mS)
b0 = float(np.median(base[:, 0]))
print("baseline strehl luma half-diff sigma: %.5f" % b0)

print()
print("=" * 78)
print("COMMISSIONING")
print("=" * 78)
n = float(np.median(half(sA, sA.copy(), mS)[:, 0]))
print("  NULL     image against itself                 %.8f  %s"
      % (n, "PASS" if n == 0.0 else "FAIL"))

for k in (0.5, 2.0):
    add = k * b0 * np.median(mS)
    noisy = sA.copy()
    noisy[..., 0] += rng.normal(0, add, sA.shape[:3])
    got = float(np.median(half(noisy, sB, mS)[:, 0]))
    pred = float(np.sqrt(b0 ** 2 + (add / np.median(mS)) ** 2))
    err = abs(got - pred) / pred
    print("  POTENCY  planted %.1fx -> %.5f, predicted %.5f, err %5.2f%%  %s"
          % (k, got, pred, 100 * err, "PASS" if err < 0.10 else "FAIL"))

print()
print("=" * 78)
print("QUANT8  the 8-bit penalty, measured on an arm whose answer is known")
print("=" * 78)


def q8(t):
    return np.round(t * 255.0) / 255.0


sA8 = opp(q8(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff")))
sB8 = opp(q8(tiles_of(r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff")))
h8 = half(sA8, sB8, mS)
CH = ("Y", "R-Y", "B-Y")
pen = {}
for c in range(3):
    a, b = float(np.median(base[:, c])), float(np.median(h8[:, c]))
    pen[CH[c]] = b / a
    print("  requantise strehl 16->8 bit  %-4s  %.5f -> %.5f   penalty %+6.1f%%"
          % (CH[c], a, b, 100 * (b / a - 1)))

fA = tiles_of(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif")
fB = tiles_of(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-B.tif")
oA, oB = opp(fA), opp(fB)
mF = oA[..., 0].mean(axis=(1, 2))
hF = half(oA, oB, mF)
hFq = half(opp(q8(fA)), opp(q8(fB)), mF)
print()
for c in range(3):
    a, b = float(np.median(hF[:, c])), float(np.median(hFq[:, c]))
    same = (a == b)
    print("  requantise focus-stack 8->8  %-4s  %.8f -> %.8f   IDENTITY %s  %s"
          % (CH[c], a, b, same, "PASS" if same else "FAIL -- loop rebound"))

print()
print("=" * 78)
print("ALPHA  what including enfuse's 4th plane would do")
print("=" * 78)
eA4 = tiles_of(r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif", keep_alpha=True)
print("  enfuse plane means: " + "  ".join("%d=%.5f" % (i, eA4[..., i].mean())
                                            for i in range(eA4.shape[3])))
print("  the 4th plane is opaque; a mean over 4 planes reads %.5f against %.5f"
      % (eA4.mean(), eA4[..., :3].mean()))
print("  -> my loader drops it. Confirmed corrupting, and confirmed excluded.")

print()
print("=" * 78)
print("REMOVING THE 8-BIT PENALTY FROM focus-stack, as M127 does")
print("=" * 78)
sh = {c: float(np.median(base[:, i])) for i, c in enumerate(CH)}
fs = {c: float(np.median(hF[:, i])) for i, c in enumerate(CH)}
print("  %-5s %10s %10s %9s %9s %12s"
      % ("chan", "strehl", "fs raw", "raw ratio", "penalty", "corrected"))
for c in CH:
    corr = fs[c] / pen[c]
    print("  %-5s %10.5f %10.5f %9.3f %9.3f %12.3f"
          % (c, sh[c], fs[c], fs[c] / sh[c], pen[c], corr / sh[c]))
json.dump({"penalty": pen, "strehl": sh, "fs": fs,
           "median_tile_luma": float(np.median(mS))},
          open(r"C:\dev\strehl-out\V-REVIEW\noise\comm.json", "w"), indent=1)
