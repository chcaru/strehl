"""Characterise the two patches objectively, before any hypothesis is priced.

Prints, for hand-picked ROIs chosen by LOOKING at the render (not by a threshold
detector -- an auto-detector on guessed thresholds returns zero and looks exactly like a
negative result), the linear DN level, a band-pass detail statistic, the winner index and
the n_eff. It also writes a labelled picture of where the ROIs are, so the ROIs can be
checked by eye rather than trusted.
"""
import pathlib

import numpy as np
import tifffile
from PIL import Image, ImageDraw
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None
OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
REF = np.array([18735.0, 19249.0, 18686.0], dtype=np.float32)

# (name, cy, cx, half) on the full-resolution output grid. Chosen by eye from
# pics/A4-scallop-j20.png and pics/A3-patch-j1z2.png.
ROIS = [
    ("pale-wash",     2012, 2400, 60),   # inside the flat creamy region, upper lobe
    ("pale-wash-2",   2250, 2360, 60),   # second draw from the same region
    ("leaf-infocus",  2050, 2700, 60),   # across the scalloped seam, sharp green leaf
    ("backdrop-far",  2012, 1950, 60),   # white backdrop left of the bud
    ("dark-patch",    3148, 4002, 60),   # the "polygon", lower lobe
    ("patch-outside", 3148, 3760, 60),   # neighbour of the polygon, same lobe
    ("subject-sharp", 3400, 4300, 60),   # visibly detailed subject nearby
]


def tone(a):
    x = np.clip(a.astype(np.float32) / (REF[None, None, :] / 0.92), 0.0, 1.0)
    return (np.clip(x ** (1 / 2.2), 0, 1) * 255).astype(np.uint8)


def bandpass_rms(g):
    """sigma=2 minus sigma=8 -- the same band M120 measured its patchwork in."""
    return float(np.sqrt(np.mean(
        (ndimage.gaussian_filter(g, 2.0) - ndimage.gaussian_filter(g, 8.0)) ** 2)))


def main():
    merge = tifffile.imread(str(OUT / "A-merge.tif"))
    elect = tifffile.imread(str(OUT / "A-elect.tif"))
    neff = tifffile.imread(str(OUT / "A-neff.tif"))
    for a, n in ((merge, "merge"), (elect, "elect"), (neff, "neff")):
        assert a.dtype == np.uint16, f"{n} is {a.dtype}"
    lum = (0.2126 * merge[..., 0] + 0.7152 * merge[..., 1] + 0.0722 * merge[..., 2]).astype(np.float32)

    print(f"{'roi':<16}{'lum DN':>9}{'bp rms':>9}{'bp/lum %':>10}"
          f"{'idx med':>9}{'idx p5':>8}{'idx p95':>9}{'n_eff med':>11}")
    rows = []
    for name, cy, cx, half in ROIS:
        sl = (slice(cy - half, cy + half), slice(cx - half, cx + half))
        psl = (slice((cy - half) // 2, (cy + half) // 2), slice((cx - half) // 2, (cx + half) // 2))
        g = lum[sl]
        e = elect[psl].astype(np.float32)
        n = neff[psl].astype(np.float32)
        bp = bandpass_rms(g)
        m = float(np.mean(g))
        rows.append((name, m, bp, 100 * bp / m, np.median(e), np.percentile(e, 5),
                     np.percentile(e, 95), np.median(n)))
        print(f"{name:<16}{m:9.0f}{bp:9.1f}{100 * bp / m:10.3f}"
              f"{np.median(e):9.0f}{np.percentile(e, 5):8.0f}{np.percentile(e, 95):9.0f}"
              f"{np.median(n):11.0f}")

    # A picture of where the ROIs are, so they can be checked rather than believed.
    for tag, cy, cx, side in (("upper", 2112, 2464, 900), ("lower", 3168, 3960, 900)):
        y0 = int(np.clip(cy - side // 2, 0, lum.shape[0] - side))
        x0 = int(np.clip(cx - side // 2, 0, lum.shape[1] - side))
        im = Image.fromarray(tone(merge[y0:y0 + side, x0:x0 + side]))
        d = ImageDraw.Draw(im)
        for name, ry, rx, half in ROIS:
            if y0 <= ry - half and ry + half <= y0 + side and x0 <= rx - half and rx + half <= x0 + side:
                d.rectangle([rx - half - x0, ry - half - y0, rx + half - x0, ry + half - y0],
                            outline=(255, 0, 0), width=3)
                d.text((rx - half - x0 + 4, ry - half - y0 + 4), name, fill=(255, 0, 0))
        dst = OUT / "pics" / f"A5-rois-{tag}.png"
        im.save(dst)
        print(f"wrote {dst}")

    np.save(OUT / "roi_table.npy", np.array(rows, dtype=object), allow_pickle=True)


if __name__ == "__main__":
    main()
