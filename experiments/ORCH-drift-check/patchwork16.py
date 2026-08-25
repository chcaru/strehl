"""Patchwork test, done properly.

Fixes two defects in the first attempt:
  1. it ran on an 8-bit TIF, so quantisation contouring was not ruled out;
  2. its best-scoring windows sat on the frame border, where coverage falls off,
     so it may have been scoring an edge effect rather than the background.

The metric is validated in-run against two nulls and one plant every time, so a
result is never reported by an instrument that has not just been shown to work.

Reads only. Writes PNGs to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
"""
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def _read_pixels(path):
    """Read pixels honestly.

    Fact 1615: PIL silently returns uint8 for a 16-bit RGB TIFF (mode 'RGB',
    241x fewer levels, no warning). Never read TIFF pixels through PIL.
    `Image.open` for TIFF *tags* is fine; np.asarray on its pixels is not.
    """
    import numpy as _np
    if str(path).lower().endswith((".tif", ".tiff")):
        import tifffile
        return tifffile.imread(path)
    from PIL import Image as _I
    return _np.asarray(_I.open(path))


CANDIDATES = [
    r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif",
    r"C:\dev\strehl-out\M97-before-after\bee-3-AFTER-aligned.tif",
    r"C:\dev\strehl-out\M86-align\bee-3-ALIGNED.tif",
]

S = 256
BORDER = 512  # ignore anything this close to the frame edge


def excess_kurtosis(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    f = lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    if v <= 0:
        return float("nan")
    return ((f - mu) ** 4).mean() / v**2 - 3.0


def commission(sd, seed=20260825):
    """Two nulls and a plant. Returns (null_iid, null_ramp, plant_mosaic)."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:S, 0:S]
    k_iid = excess_kurtosis(rng.normal(0, sd, (S, S)))
    ramp = (xx + yy) * (sd / S) + rng.normal(0, sd * 0.05, (S, S))
    k_ramp = excess_kurtosis(ramp)
    cx = rng.integers(0, S, 40)
    cy = rng.integers(0, S, 40)
    lab = ((xx[..., None] - cx) ** 2 + (yy[..., None] - cy) ** 2).argmin(axis=2)
    k_plant = excess_kurtosis(rng.normal(0, sd, 40)[lab])
    return k_iid, k_ramp, k_plant


src = next((p for p in CANDIDATES if os.path.exists(p)), None)
if src is None:
    print("none of the candidate merges exist")
    sys.exit(1)

a = _read_pixels(src)
print("src   %s" % src)
print("shape %s  dtype %s  min %s max %s" % (a.shape, a.dtype, a.min(), a.max()))

bits = 16 if a.dtype == np.uint16 else (8 if a.dtype == np.uint8 else 0)
if bits != 16:
    print()
    print("!! NOT 16-BIT (%s). Quantisation contouring is NOT ruled out by this run." % a.dtype)
    sys.exit(3)  # M120: a warning that does not stop the run is not a check
full = float(np.iinfo(a.dtype).max) if np.issubdtype(a.dtype, np.integer) else 1.0

lum = a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)
H, W = lum.shape

cands = []
for y in range(BORDER, H - S - BORDER, S):
    for x in range(BORDER, W - S - BORDER, S):
        w = lum[y : y + S, x : x + S]
        m = w.mean()
        if m < 0.55 * full:
            continue
        cands.append((w[::16, ::16].std(), m, x, y))
cands.sort()
print("interior background windows (>=%d px from any edge): %d" % (BORDER, len(cands)))
if not cands:
    print("NO INTERIOR BACKGROUND WINDOW -- cannot run the test")
    sys.exit(2)

sds = [lum[y : y + S, x : x + S].std() for _, _, x, y in cands[:12]]
k_iid, k_ramp, k_plant = commission(float(np.median(sds)) or 1.0)
print()
print("COMMISSIONING at sd=%.3f levels" % (np.median(sds)))
print("  null  iid gaussian        %8.2f   (want ~0)" % k_iid)
print("  null  smooth ramp         %8.2f   (want ~0)" % k_ramp)
print("  plant voronoi mosaic      %8.2f   (want >>0)" % k_plant)
if not (abs(k_iid) < 1.0 and abs(k_ramp) < 1.0 and k_plant > 10.0):
    print("  INSTRUMENT FAILED COMMISSIONING -- results below are not interpretable")
    sys.exit(3)
print("  instrument OK")

print()
print("%-6s %-6s %8s %9s %12s" % ("x", "y", "mean%", "sd(lvl)", "excessKurt"))
rows = []
for _, m, x, y in cands[:12]:
    w = lum[y : y + S, x : x + S]
    k = excess_kurtosis(w)
    rows.append((k, x, y, m, w.std()))
    print("%-6d %-6d %7.1f%% %9.2f %12.2f" % (x, y, 100 * m / full, w.std(), k))

rows.sort(reverse=True)
n_patchy = sum(1 for k, *_ in rows if k > 10.0)
print()
print("windows scoring above the plant-calibrated bar (kurt>10): %d of %d" % (n_patchy, len(rows)))
print("worst %.2f at x=%d y=%d ; median %.2f" % (rows[0][0], rows[0][1], rows[0][2], np.median([r[0] for r in rows])))

k, x, y, m, sd = rows[0]
w = lum[y : y + S, x : x + S]
lo, hi = np.percentile(w, [0.5, 99.5])
st = np.clip((w - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
out = r"C:\dev\strehl-out\ORCH-morning\PATCHWORK-interior-worst.png"
Image.fromarray(st.astype(np.uint8)).resize((S * 3, S * 3), Image.NEAREST).save(out)
print("wrote %s  (x=%d y=%d, stretch span %.1f of %.0f = %.3f%%)" % (out, x, y, hi - lo, full, 100 * (hi - lo) / full))
