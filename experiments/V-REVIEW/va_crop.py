"""1:1 crops for the visual call, plus the gradient actually inside each crop.

ORCH rule: a visual verdict above ~400 px is invalid. Every crop below is
400x400 at NATIVE resolution -- no decimation, no resampling, no stretch.
The PNG is written from the encoded sRGB master, which is what a print gets.

Each crop is placed on the subject boundary so it spans roughly 0-400 px of
ground, i.e. the whole band in which an aura is claimed to live.
"""
import os, sys, json
import numpy as np, tifffile
from scipy import ndimage
from PIL import Image   # PIL is used ONLY to WRITE png. Every tiff read is tifffile.

ACC = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"C:\dev\strehl-out\V-REVIEW\aura-ship"
CROP = r"C:\dev\strehl-out\V-REVIEW\aura-ship\crops"
os.makedirs(CROP, exist_ok=True)
LEVEL = 257.0
N = 400


def luma(a): return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def otsu(v):
    h, _ = np.histogram(v, bins=512, range=(0, 65535)); h = h.astype(np.float64)
    w = np.cumsum(h); m = np.cumsum(h * np.arange(512)); tot, mt = w[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        vb = (mt * w / tot - m) ** 2 / (w * (tot - w))
    vb[~np.isfinite(vb)] = -1
    return (np.argmax(vb) + 0.5) * 65535.0 / 512.0


def pick(full):
    """Find a boundary point whose outward 400 px is ground, not more subject."""
    s = full[::8, ::8]
    t = otsu(s); d = s < t
    if d.mean() > 0.5: d = ~d
    d = ndimage.binary_closing(ndimage.binary_opening(d, np.ones((3, 3))), np.ones((5, 5)))
    lab, k = ndimage.label(d)
    sz = ndimage.sum(d, lab, range(1, k + 1))
    d = ndimage.binary_fill_holes(lab == (int(np.argmax(sz)) + 1))
    dist = ndimage.distance_transform_edt(~d) * 8.0
    edge = d & ~ndimage.binary_erosion(d, np.ones((3, 3)))
    ys, xs = np.nonzero(edge)
    best, bxy = -1, None
    for y, x in zip(ys[::7], xs[::7]):
        Y, X = y * 8, x * 8
        if Y < N or X < N or Y > full.shape[0] - N or X > full.shape[1] - N:
            continue
        win = dist[max(0, y - 25):y + 25, max(0, x - 25):x + 25]
        sc = float(win.max())
        if sc > best:
            best, bxy = sc, (Y, X)
    return bxy, best


rows = {}
for sub in ("flower-bud-alone-cpl", "109MSDCF", "bee-1-cpl"):
    m = tifffile.imread(os.path.join(ACC, "%s--SHIP-V4.tiff" % sub))
    L = luma(m.astype(np.float64))
    xy, reach = pick(L)
    if xy is None:
        print("%-28s no boundary with 400 px of clear ground -> REFUSED" % sub); continue
    y, x = xy
    y0, x0 = max(0, y - N // 2), max(0, x - N // 2)
    tile = m[y0:y0 + N, x0:x0 + N]
    Image.fromarray((tile.astype(np.float64) / 257.0).clip(0, 255).astype(np.uint8)).save(
        os.path.join(CROP, "%s--master-1to1.png" % sub))
    tl = luma(tile.astype(np.float64))
    # what a viewer would have to see: the spread across the crop's ground
    lo, hi = np.percentile(tl, [40, 95])
    rows[sub] = {"xy": [int(y), int(x)], "reach_px": reach,
                 "crop_p40_levels": lo / LEVEL, "crop_p95_levels": hi / LEVEL,
                 "crop_spread_levels": (hi - lo) / LEVEL}
    print("%-28s crop at (%d,%d)  ground reach %.0f px  spread across crop %.1f levels"
          % (sub, y, x, reach, (hi - lo) / LEVEL))
    ep = os.path.join(OUT, "%s--estimator.tiff" % sub)
    if os.path.exists(ep):
        e = tifffile.imread(ep)[y0:y0 + N, x0:x0 + N]
        Image.fromarray((e.astype(np.float64) / 257.0).clip(0, 255).astype(np.uint8)).save(
            os.path.join(CROP, "%s--estimator-1to1.png" % sub))
        d = luma(tile.astype(np.float64)) - luma(e.astype(np.float64))
        print("%-28s   pyramid-minus-estimator inside this crop: median %+.2f levels,"
              " p5..p95 %+.2f..%+.2f" % ("", np.median(d) / LEVEL,
              np.percentile(d, 5) / LEVEL, np.percentile(d, 95) / LEVEL))
json.dump(rows, open(os.path.join(OUT, "crops.json"), "w"), indent=1)
print()
print("wrote", CROP)
for f in sorted(os.listdir(CROP)):
    print("   ", f)
