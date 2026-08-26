"""Is the directional demosaic's gradient change detail, or noise?

An 11% rise in median gradient with no rise at the 99th percentile is equally
the signature of amplified noise and of recovered low-contrast texture. The
discriminator is WHERE it rises: real detail cannot appear in a region that is
out of focus, so a rise there is noise by construction.

Tiles are ranked by the MALVAR arm's own local structure so that the same
tiles are compared in both arms and the selection cannot be biased by the arm
being tested.
"""
import sys
from pathlib import Path
import numpy as np
import tifffile

PIN = Path(r"C:\dev\strehl-out\BUILD-SHARP\demo-ab")
T = 128


def luma(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def tile_stats(y, ty, tx):
    b = y[ty:ty + T, tx:tx + T]
    gx = np.diff(b, axis=1)[:-1, :]
    gy = np.diff(b, axis=0)[:, :-1]
    return float(np.hypot(gx, gy).mean())


def hf_energy(b):
    """Energy above half-Nyquist along x, via a simple 3-tap high-pass."""
    hp = b[:, 2:] - 2.0 * b[:, 1:-1] + b[:, :-2]
    return float((hp * hp).mean())


def main():
    for subj in ("bee-3-cpl", "tweezers-cpl"):
        d = tifffile.imread(PIN / f"{subj}--directional.tif").astype(np.float64)
        m = tifffile.imread(PIN / f"{subj}--malvar.tif").astype(np.float64)
        yd, ym = luma(d), luma(m)
        h, w = ym.shape
        ys = range(64, h - T - 64, T)
        xs = range(64, w - T - 64, T)
        coords = [(a, b) for a in ys for b in xs]
        gm = np.array([tile_stats(ym, a, b) for a, b in coords])
        gd = np.array([tile_stats(yd, a, b) for a, b in coords])

        order = np.argsort(gm)
        n = len(order)
        print(f"=== {subj} === {n} tiles of {T}x{T}, ranked by the MALVAR arm")
        bands = [("flattest 5%  (out of focus: any rise here is noise)", order[:n // 20]),
                 ("median 10%", order[n // 2 - n // 20:n // 2 + n // 20]),
                 ("sharpest 5% (detail sites)", order[-(n // 20):])]
        for name, idx in bands:
            a, b = gm[idx].mean(), gd[idx].mean()
            hm = np.mean([hf_energy(ym[coords[i][0]:coords[i][0] + T,
                                       coords[i][1]:coords[i][1] + T]) for i in idx])
            hd = np.mean([hf_energy(yd[coords[i][0]:coords[i][0] + T,
                                       coords[i][1]:coords[i][1] + T]) for i in idx])
            print(f"  {name:52s} n={len(idx):5d}")
            print(f"      mean gradient   malvar {a:9.3f}  directional {b:9.3f}  ratio {b/max(a,1e-9):.4f}")
            print(f"      high-freq power malvar {hm:11.1f}  directional {hd:11.1f}  ratio {hd/max(hm,1e-9):.4f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
