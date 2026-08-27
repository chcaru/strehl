"""How much of the delivered master's stated resolution is real?

The deliverable states 7032 x 4688 and "at 300 DPI it is 23.4 x 15.6 inches".
That is a claim about resolved detail, and it is testable. Two things in the
render's own provenance say it may not hold:

  * "planes : 3516 x 2344 per CFA plane" and "one focus decision per quad.
    Interpolated -- do not measure resolution on it." The focus decision is
    made at half the output pitch in each axis.
  * "coverage : field of view scaled to X so that EVERY frame covers every
    pixel (N% of width dropped, then upsampled to keep the output dimensions)."
    That is an explicit upsample, by 1/X, on top of everything else.

A radial power spectrum answers it directly. An image carrying genuine detail
at its own sampling pitch has power out to near Nyquist. An image that was
built at half pitch and interpolated up has a spectrum that collapses at 0.5
Nyquist, because interpolation cannot create the octave it never sampled.

Reported as f50 and f10: the normalised spatial frequency (1.0 = Nyquist of the
delivered pixel grid) at which the azimuthally averaged power has fallen to 50%
and 10% of its value at 0.05 Nyquist. Windowed with a Hann window in both axes
first, because a hard tile edge is a step function whose spectrum is a sinc
that would swamp the measurement.

For scale, the same statistic is computed on the raw green CFA plane of a
source frame, which is genuine unreconstructed sensor sampling. Its Nyquist is
half the master's, so a master carrying real detail at ITS pitch should reach
roughly twice as far in absolute terms.

Usage: python spectrum.py <tiff> <x> <y> <size> [more tiffs...]
"""

import sys
import pathlib
import numpy as np
import tifffile


def radial_spectrum(tile):
    a = tile.astype(np.float64)
    a = a - a.mean()
    n = a.shape[0]
    w = np.hanning(n)
    a = a * w[:, None] * w[None, :]
    f = np.fft.fftshift(np.abs(np.fft.fft2(a)) ** 2)
    cy, cx = n // 2, n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    rb = r.astype(int)
    nb = n // 2
    prof = np.bincount(rb.ravel(), f.ravel(), minlength=nb + 1)[: nb + 1]
    cnt = np.bincount(rb.ravel(), minlength=nb + 1)[: nb + 1]
    prof = prof / np.maximum(cnt, 1)
    freq = np.arange(nb + 1) / float(nb)  # 1.0 == Nyquist
    return freq, prof


def cutoffs(freq, prof):
    ref_i = np.argmin(np.abs(freq - 0.05))
    ref = prof[ref_i]
    out = {}
    for frac, name in ((0.5, "f50"), (0.1, "f10"), (0.01, "f01")):
        below = np.where((freq > 0.05) & (prof < ref * frac))[0]
        out[name] = float(freq[below[0]]) if below.size else 1.0
    return out


def green_of(path, x, y, size):
    p = pathlib.Path(path)
    if p.suffix.lower() in (".tif", ".tiff"):
        m = tifffile.imread(str(p))
        return m[y : y + size, x : x + size, 1].astype(np.float64), "master-G"
    import rawpy

    with rawpy.imread(str(p)) as raw:
        v = raw.raw_image_visible.astype(np.float32).copy()  # rule 32
    g0 = v[0::2, 1::2]
    g1 = v[1::2, 0::2]
    ny, nx = min(g0.shape[0], g1.shape[0]), min(g0.shape[1], g1.shape[1])
    g = (g0[:ny, :nx] + g1[:ny, :nx]) * 0.5
    return g[y // 2 : y // 2 + size // 2, x // 2 : x // 2 + size // 2].astype(
        np.float64
    ), "raw-greenplane"


def main():
    x, y, size = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    paths = [sys.argv[1]] + sys.argv[5:]
    print(f"tile ({x},{y}) {size}x{size}   1.0 = Nyquist of that file's own grid")
    print(f"{'file':<52} {'kind':<16} {'f50':>7} {'f10':>7} {'f01':>7}")
    print("-" * 94)
    for p in paths:
        tile, kind = green_of(p, x, y, size)
        if tile.size == 0:
            print(f"{pathlib.Path(p).name:<52} EMPTY TILE")
            continue
        freq, prof = radial_spectrum(tile)
        c = cutoffs(freq, prof)
        print(
            f"{pathlib.Path(p).name:<52} {kind:<16} "
            f"{c['f50']:>7.3f} {c['f10']:>7.3f} {c['f01']:>7.3f}"
        )


if __name__ == "__main__":
    main()
