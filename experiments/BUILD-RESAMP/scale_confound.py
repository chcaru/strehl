"""BUILD-RESAMP -- how much of the reported deficit is raster scale alone?

The two tools do not write the same raster from the same 22 frames:

    fork    6748 x 4472
    strehl  7032 x 4688      ->  1.0421x in x, 1.0483x in y

A band ratio computed in cycles per PIXEL is scale-sensitive, so a
magnification difference reads as a fine-detail difference with no resampling
involved at all.  This measures that confound directly, with nothing assumed
about the spectrum's slope: take ONE render, resample it to the OTHER tool's
raster with an exact band-limited kernel, and compute the 0.20-0.40 cyc/px band
power ratio between the two.  Same pixels, same tool, same everything -- the
only difference is the raster.

The NULL is k=1.0, which must return exactly 1.000.

Usage:  python scale_confound.py <strehl.tiff> <fork.tif>
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commission_edge import green, rescale  # noqa: E402


def band(img, lo=0.20, hi=0.40, tile=128, stride=512):
    fy = np.fft.fftfreq(tile)[:, None]
    fx = np.fft.rfftfreq(tile)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    mask = (r >= lo) & (r < hi)
    win = np.hanning(tile)[:, None] * np.hanning(tile)[None, :]
    out = []
    for y in range(tile, img.shape[0] - 2 * tile, stride):
        for x in range(tile, img.shape[1] - 2 * tile, stride):
            t = img[y:y + tile, x:x + tile]
            if t.std() < 1e-6:
                continue
            t = (t - t.mean()) * win
            out.append((np.abs(np.fft.rfft2(t)) ** 2)[mask].mean())
    return np.array(out)


def main():
    sp, fp = sys.argv[1], sys.argv[2]
    g = green(sp)
    f = tifffile.imread(fp)
    fg = f[:, :, 1].astype(np.float64)
    print(f"  strehl raster {g.shape[1]} x {g.shape[0]}")
    print(f"  fork   raster {fg.shape[1]} x {fg.shape[0]}")
    kx = fg.shape[1] / g.shape[1]
    ky = fg.shape[0] / g.shape[0]
    print(f"  fork/strehl scale: {kx:.4f} in x, {ky:.4f} in y\n")

    b0 = band(g)
    print(f"  {'k':>8}{'band 0.20-0.40 vs k=1':>26}   what")
    for k, what in ((1.0, "NULL -- must be exactly 1.000"),
                    (kx, "strehl resampled to the fork's raster"),
                    (0.9476, "strehl's own coverage k, for scale"),
                    (0.50, "absurd-value arm")):
        gk = rescale(g, k) if k != 1.0 else g
        bk = band(gk)
        n = min(len(b0), len(bk))
        r = float(np.median(bk[:n]) / np.median(b0[:n]))
        print(f"  {k:>8.4f}{r:>26.4f}   {what}")
    print("\n  A ratio BELOW 1 means: shrinking the raster REMOVES 0.20-0.40")
    print("  band power, so the tool that writes the smaller raster is")
    print("  PENALISED by this statistic, not rewarded.")


if __name__ == "__main__":
    main()
