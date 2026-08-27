"""Geometry between strehl's raster and a comparator's, measured, not assumed.

Nothing is resampled to make a MEASUREMENT.  Resampling happens only inside
this file, to FIND the transform; every reported number downstream reads an
integer box in each arm's own grid and scales its band edges.  That is the same
discipline the prior pass used and the reason the integer-only-shift rule
exists: sub-pixel resampling adds blur to the very quantity being measured.

Method: downsample both by D (block mean, which is exact for integer D and adds
no ringing), sweep a global scale, and at each scale phase-correlate a grid of
tiles.  The score is the median tile peak; the winner is the scale with the
highest score.  A scale sweep that has no interior maximum is a FAILED fit and
says so -- the prior pass abandoned a third subject pairing for exactly that
(peak 0.0277, no maximum from 0.90 to 1.12).
"""
import sys

import numpy as np
import tifffile
from scipy import ndimage


def block_mean(a, d):
    h = (a.shape[0] // d) * d
    w = (a.shape[1] // d) * d
    return a[:h, :w].reshape(h // d, d, w // d, d).mean((1, 3))


def load_grey(path, chan="luma", weights=(0.2126, 0.7152, 0.0722)):
    a = tifffile.imread(path)
    a = np.asarray(a[:, :, :3], np.float64)
    return (weights[0] * a[:, :, 0] + weights[1] * a[:, :, 1]
            + weights[2] * a[:, :, 2])


def peak(ref, mov):
    """Normalised phase-correlation peak and its integer offset."""
    w = np.hanning(ref.shape[0])[:, None] * np.hanning(ref.shape[1])[None, :]
    A = np.fft.fft2((ref - ref.mean()) * w)
    B = np.fft.fft2((mov - mov.mean()) * w)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-30
    c = np.real(np.fft.ifft2(R))
    i = np.unravel_index(np.argmax(c), c.shape)
    dy = i[0] - (ref.shape[0] if i[0] > ref.shape[0] // 2 else 0)
    dx = i[1] - (ref.shape[1] if i[1] > ref.shape[1] // 2 else 0)
    return float(c[i]), dy, dx


def fit(sp, cp, scales, d=8, tile=128, ntile=6, verbose=True):
    """sp = strehl path, cp = comparator path.  Returns (best_scale, score,
    per-tile offsets at the best scale, the whole sweep)."""
    S = block_mean(load_grey(sp), d)
    C = block_mean(load_grey(cp), d)
    if verbose:
        print(f"  strehl     {S.shape[1]*d} x {S.shape[0]*d} -> /{d} {S.shape}")
        print(f"  comparator {C.shape[1]*d} x {C.shape[0]*d} -> /{d} {C.shape}")
    ys = np.linspace(tile, S.shape[0] - 2 * tile, ntile).astype(int)
    xs = np.linspace(tile, S.shape[1] - 2 * tile, ntile).astype(int)
    sweep = []
    for s in scales:
        Cz = ndimage.zoom(C, s, order=3)
        pk = []
        for y in ys:
            for x in xs:
                if y + tile > Cz.shape[0] or x + tile > Cz.shape[1]:
                    continue
                p, _, _ = peak(S[y:y + tile, x:x + tile],
                               Cz[y:y + tile, x:x + tile])
                pk.append(p)
        sweep.append((s, float(np.median(pk)), len(pk)))
        if verbose:
            print(f"    scale {s:.4f}: median tile peak {np.median(pk):.4f} "
                  f"over {len(pk)} tiles")
    best = max(sweep, key=lambda t: t[1])
    interior = sweep[0][1] < best[1] and sweep[-1][1] < best[1]
    if verbose:
        print(f"  best scale {best[0]:.4f} score {best[1]:.4f}  "
              f"{'INTERIOR MAXIMUM (fit is real)' if interior else 'NO INTERIOR MAXIMUM -- FIT FAILED'}")
    return best[0], best[1], interior, sweep


def offsets(sp, cp, scale, d=8, tile=128, ntile=8):
    """Per-tile integer offsets at the fitted scale, in strehl pixels."""
    S = block_mean(load_grey(sp), d)
    C = block_mean(load_grey(cp), d)
    Cz = ndimage.zoom(C, scale, order=3)
    ys = np.linspace(tile, S.shape[0] - 2 * tile, ntile).astype(int)
    xs = np.linspace(tile, S.shape[1] - 2 * tile, ntile).astype(int)
    rows = []
    for y in ys:
        for x in xs:
            if y + tile > Cz.shape[0] or x + tile > Cz.shape[1]:
                continue
            p, dy, dx = peak(S[y:y + tile, x:x + tile], Cz[y:y + tile, x:x + tile])
            rows.append((y * d, x * d, dy * d, dx * d, p))
    return np.array(rows)


PAIRS = {
    "cb": (r"C:\dev\strehl-out\V-H2H2\lin\cb-full-g1.tiff",
           r"C:\dev\macro\out\coffee-bean\stack.tif", "focus-stack fork"),
    "113": (r"C:\dev\strehl-out\V-H2H2\lin\113-full-g1.tiff",
            r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif",
            "Zerene Stacker PMax"),
}


def main():
    which = sys.argv[1:] or list(PAIRS)
    for k in which:
        sp, cp, label = PAIRS[k]
        print(f"\n=== {k}: strehl vs {label} ===")
        coarse = np.arange(0.98, 1.081, 0.01)
        s, sc, ok, sweep = fit(sp, cp, coarse)
        if not ok:
            print("  coarse sweep has no interior maximum; refusing to refine")
            continue
        fine = np.arange(s - 0.012, s + 0.0121, 0.002)
        s2, sc2, ok2, _ = fit(sp, cp, fine)
        print(f"  REFINED scale {s2:.4f} score {sc2:.4f}")
        off = offsets(sp, cp, s2)
        print(f"  per-tile offsets at that scale ({len(off)} tiles):")
        print(f"    dy median {np.median(off[:,2]):+.1f} "
              f"[{off[:,2].min():+.0f},{off[:,2].max():+.0f}]  "
              f"dx median {np.median(off[:,3]):+.1f} "
              f"[{off[:,3].min():+.0f},{off[:,3].max():+.0f}]  "
              f"peak median {np.median(off[:,4]):.4f}")
        rms = np.sqrt(((off[:, 2] - np.median(off[:, 2])) ** 2 +
                       (off[:, 3] - np.median(off[:, 3])) ** 2).mean())
        print(f"    residual after a single global integer shift: {rms:.1f} px rms"
              f"   -> {'one shift is enough' if rms < 4 else 'a single integer shift is NOT globally satisfiable; per-ROI offsets required'}")
        np.save(rf"C:\dev\strehl-out\V-H2H2\logs\geom-{k}.npy",
                np.array([s2, sc2] + list(off.ravel())))


if __name__ == "__main__":
    sys.exit(main())
