"""M114 r16: 3-way by-eye crops, off | on | tangential-placebo.

One tone map, derived from OFF only and applied UNCHANGED to all three arms, so
no arm gets a contrast advantage. Nearest-neighbour upscale only: no resize
filter, no sharpening, no per-arm tone change. Windows are chosen
programmatically as the highest-chroma windows at each target radius, which is
the hardest test for the correction rather than the most flattering.
"""
import numpy as np, tifffile
from scipy import ndimage
from pathlib import Path
from PIL import Image

R12 = Path(r"C:\dev\strehl-out\M114-ca-verify\r12")
OUTD = Path(r"C:\dev\strehl-out\M114-ca-verify\crops3"); OUTD.mkdir(parents=True, exist_ok=True)
off = tifffile.imread(str(R12 / "off.tif")).astype(np.float64)
on = tifffile.imread(str(R12 / "on.tif")).astype(np.float64)
tan = tifffile.imread(str(R12 / "tan.tif")).astype(np.float64)
H, W, _ = off.shape
cx, cy = W / 2.0, H / 2.0
RC = np.hypot(cx, cy)
N, UP = 160, 4

lo, hi = np.percentile(off, [0.5, 99.7])
def tone(a):
    return np.clip((a - lo) / (hi - lo), 0, 1) ** (1 / 1.6)

y_ = 0.2126 * off[:, :, 0] + 0.7152 * off[:, :, 1] + 0.0722 * off[:, :, 2]
ch = np.abs(off[:, :, 0] - y_)
rng = np.random.default_rng(16)
for tgt in (0.50, 0.83):
    best = None
    for _ in range(6000):
        y = int(rng.integers(0, H - N)); x = int(rng.integers(0, W - N))
        r = np.hypot(x + N/2 - cx, y + N/2 - cy) / RC
        if abs(r - tgt) > 0.02:
            continue
        s = float(np.mean(ch[y:y+N, x:x+N]))
        if best is None or s > best[0]:
            best = (s, y, x, r)
    s, y, x, r = best
    sl = (slice(y, y + N), slice(x, x + N))
    tiles = [tone(a[sl]) for a in (off, on, tan)]
    gap = np.ones((N, 4, 3))
    strip = np.concatenate([tiles[0], gap, tiles[1], gap, tiles[2]], axis=1)
    img = Image.fromarray((strip * 255).astype(np.uint8)).resize(
        (strip.shape[1] * UP, strip.shape[0] * UP), Image.NEAREST)
    p = OUTD / ("r%.2f_off_on_tan_at_%d_%d.png" % (tgt, x, y))
    img.save(p)
    print("r=%.3f  window (%d,%d)  mean|R-Y| %.1f DN  ->  %s" % (r, x, y, s, p.name))
