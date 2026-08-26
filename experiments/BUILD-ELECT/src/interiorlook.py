"""Look at the deep-interior softening on flower-bud at 1:1.

biascheck.py survived its own reversal control and says the flower-bud subject
interior is 14.8% to 16.1% softer in the blend arm. That is a number, and the
number disagrees with the one 1:1 crop I have already looked at, where the
control held a flat pale wash and the blend held hairs. House rule: when a number
and a picture disagree, the picture is right - so go and get enough pictures to
settle it rather than trusting either.

Crops are chosen at the largest LOCAL DECREASE in gradient energy, restricted to
the deep interior and spread apart so they are not four views of one blob. That
is where the -16% lives by construction, so it is the least favourable place to
look and the right place to judge.
"""
import pathlib
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import ndimage

B = pathlib.Path(r"C:\dev\strehl-out\BUILD-BLEND\bm")
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\pics")
ERODE = 60
HALF = 150
NCROP = 4
APART = 900


def luma(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} is {a.dtype}"
    return (a.astype(np.float32).mean(axis=2) if a.ndim == 3
            else a.astype(np.float32))


def grad(l):
    return np.hypot(ndimage.sobel(l, axis=1) * 0.125,
                    ndimage.sobel(l, axis=0) * 0.125)


def main():
    lc = luma(B / "flower-bud-alone-cpl-ctrl.tif")
    lb = luma(B / "flower-bud-alone-cpl-blend.tif")
    lb = lb / (float(np.median(lb)) / float(np.median(lc)))

    s = lc[::4, ::4]
    hist, edges = np.histogram(s, 512)
    p = hist / hist.sum()
    om, mu = np.cumsum(p), np.cumsum(p * ((edges[:-1] + edges[1:]) / 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        var = (mu[-1] * om - mu) ** 2 / (om * (1 - om))
    thr = float((edges[:-1] + edges[1:])[np.nanargmax(var)] / 2)
    m = ndimage.binary_fill_holes(lc < thr)
    lab, n = ndimage.label(m)
    sz = ndimage.sum(m, lab, range(1, n + 1))
    m = ndimage.binary_fill_holes(lab == (1 + int(np.argmax(sz))))
    pad = np.zeros((m.shape[0] + 2, m.shape[1] + 2), bool)
    pad[1:-1, 1:-1] = m
    deep = ndimage.distance_transform_edt(pad)[1:-1, 1:-1] > ERODE

    drop = ndimage.uniform_filter(grad(lc) - grad(lb), 65)
    drop[~deep] = -1e9
    drop[:HALF + 5] = drop[-HALF - 5:] = -1e9
    drop[:, :HALF + 5] = drop[:, -HALF - 5:] = -1e9

    pts = []
    work = drop.copy()
    for _ in range(NCROP):
        y, x = np.unravel_index(int(np.argmax(work)), work.shape)
        pts.append((int(y), int(x), float(drop[y, x])))
        yy, xx = np.ogrid[:work.shape[0], :work.shape[1]]
        work[(yy - y) ** 2 + (xx - x) ** 2 < APART ** 2] = -1e9

    print("crops at the largest local gradient DECREASE inside the subject:")
    fig, ax = plt.subplots(3, NCROP, figsize=(4.1 * NCROP, 12.4))
    for i, (y, x, d) in enumerate(pts):
        sl = (slice(y - HALF, y + HALF), slice(x - HALF, x + HALF))
        gc = float(grad(lc)[sl].mean())
        gb = float(grad(lb)[sl].mean())
        print(f"  ({y:5d},{x:5d})  local drop {d:8.1f} DN/px   "
              f"crop mean gradient  ctrl {gc:7.1f}  blend {gb:7.1f}  "
              f"{100 * (gb / gc - 1):+6.1f}%   "
              f"level ctrl {np.median(lc[sl]):6.0f} DN blend {np.median(lb[sl]):6.0f} DN")
        lo = float(np.percentile(lc[sl], 1))
        hi = float(np.percentile(lc[sl], 99))
        for r, (img, tag) in enumerate(((lc, "CONTROL"), (lb, "BLEND"))):
            v = np.clip((img[sl] - lo) / max(hi - lo, 1e-6), 0, 1) ** (1 / 2.2)
            ax[r][i].imshow(v, cmap="gray")
            ax[r][i].set_xticks([]); ax[r][i].set_yticks([])
            ax[r][i].set_title(
                f"{tag}  (y={y}, x={x})\nmean |grad| "
                f"{(gc if r == 0 else gb):.0f} DN/px", fontsize=9)
        dv = np.abs(lb[sl] - lc[sl])
        ax[2][i].imshow(np.clip(dv / max(np.percentile(dv, 99), 1), 0, 1), cmap="inferno")
        ax[2][i].set_xticks([]); ax[2][i].set_yticks([])
        ax[2][i].set_title(f"|difference|, p99 = {np.percentile(dv, 99):.0f} DN",
                           fontsize=9)
    fig.suptitle("flower-bud deep interior, 1:1 linear, at the four largest "
                 "gradient decreases\n(identical display stretch per column; "
                 "this is where the -16% lives)", fontsize=13)
    plt.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / "BLEND-interior.png"
    plt.savefig(p, dpi=74)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
