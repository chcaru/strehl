"""Is the background patchwork present in the 16-bit merge, or is it an artifact
of the 8-bit PNG crop it was first seen in?

Rival to kill: quantisation contouring. If the polygons only exist after an
8-bit export, they are a display artifact and not a stacker defect.

Reads only. Writes one PNG to C:\\dev\\strehl-out\\ORCH-morning. Never touches D:\\.
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
    r"C:\dev\strehl-out\bee3-full.tif",
    r"C:\dev\strehl-out\ORCH-morning\bee-3-strehl.tif",
]

src = next((p for p in CANDIDATES if os.path.exists(p)), None)
if src is None:
    print("no 16-bit merge found; candidates:", CANDIDATES)
    sys.exit(1)

a = _read_pixels(src)
print("src   %s" % src)
if a.dtype != np.uint16:
    print("!! NOT 16-BIT (%s) -- this script exists to rule OUT quantisation\n"
          "   contouring, so it cannot run on quantised input." % a.dtype)
    sys.exit(3)

print("array shape %s dtype %s  min %s max %s" % (a.shape, a.dtype, a.min(), a.max()))
if a.ndim == 3:
    lum = a[..., :3].astype(np.float64).mean(axis=2)
else:
    lum = a.astype(np.float64)

full = float(np.iinfo(a.dtype).max) if np.issubdtype(a.dtype, np.integer) else 1.0
print("assumed full scale %.0f" % full)

# Find background windows automatically: bright, and smooth at a coarse scale, so
# we are not accidentally scoring the subject or a silhouette edge.
H, W = lum.shape
S = 256
best = []
for y in range(0, H - S, S):
    for x in range(0, W - S, S):
        w = lum[y : y + S, x : x + S]
        m = w.mean()
        if m < 0.55 * full:
            continue
        # coarse roughness: sd of a 16x-downsampled version, to reject subject
        c = w[::16, ::16]
        best.append((c.std(), m, x, y))
best.sort()
print("background candidates found: %d" % len(best))
if not best:
    print("NO BACKGROUND WINDOW FOUND -- cannot run this test")
    sys.exit(2)


def excess_kurtosis(win):
    lap = (
        -4 * win[1:-1, 1:-1]
        + win[:-2, 1:-1]
        + win[2:, 1:-1]
        + win[1:-1, :-2]
        + win[1:-1, 2:]
    )
    f = lap.ravea() if False else lap.ravel()
    mu = f.mean()
    v = ((f - mu) ** 2).mean()
    if v <= 0:
        return float("nan"), 0.0
    return ((f - mu) ** 4).mean() / v**2 - 3.0, float(np.sqrt(v))


print()
print("%-6s %-6s %8s %9s %10s %12s" % ("x", "y", "mean%", "sd(lvl)", "lapSD", "excessKurt"))
picks = best[:6]
for rough, m, x, y in picks:
    win = lum[y : y + S, x : x + S]
    k, lsd = excess_kurtosis(win)
    print(
        "%-6d %-6d %7.1f%% %9.1f %10.3f %12.2f"
        % (x, y, 100 * m / full, win.std(), lsd, k)
    )

# A same-size null: pure gaussian noise at the measured sd has excess kurtosis 0
# for its laplacian. A smooth ramp has near-zero laplacian everywhere. Neither
# produces a heavy tail; a piecewise-constant mosaic does.
rng = np.random.default_rng(20260825)
_, m0, x0, y0 = picks[0]
win = lum[y0 : y0 + S, x0 : x0 + S]
noise = rng.normal(win.mean(), max(win.std(), 1e-9), win.shape)
yy, xx = np.mgrid[0:S, 0:S]
ramp = win.mean() + (xx + yy) * (win.std() / S)
kn, _ = excess_kurtosis(noise)
kr, _ = excess_kurtosis(ramp + rng.normal(0, max(win.std(), 1e-9) * 0.05, win.shape))
print()
print("NULL  iid gaussian, same sd      excess kurtosis %8.2f" % kn)
print("NULL  smooth ramp + faint noise  excess kurtosis %8.2f" % kr)

# And a positive control: a real piecewise-constant mosaic at the same amplitude.
lab = np.zeros((S, S), dtype=int)
cx = rng.integers(0, S, 40)
cy = rng.integers(0, S, 40)
d = (xx[..., None] - cx) ** 2 + (yy[..., None] - cy) ** 2
lab = d.argmin(axis=2)
levels = rng.normal(win.mean(), max(win.std(), 1e-9), 40)
mosaic = levels[lab]
km, _ = excess_kurtosis(mosaic)
print("PLANT voronoi mosaic, same sd    excess kurtosis %8.2f" % km)

# Save a stretched view of the best background window straight from 16-bit.
lo, hi = np.percentile(win, [0.5, 99.5])
st = np.clip((win - lo) / max(hi - lo, 1e-9), 0, 1) * 255.0
out = r"C:\dev\strehl-out\ORCH-morning\PATCHWORK-16bit-background.png"
Image.fromarray(st.astype(np.uint8)).resize((S * 3, S * 3), Image.NEAREST).save(out)
print()
print("wrote %s from the 16-bit source, window x=%d y=%d" % (out, x0, y0))
print("stretch span %.1f levels of %.0f full scale (%.3f%%)" % (hi - lo, full, 100 * (hi - lo) / full))
