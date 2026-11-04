"""Noise of a stack render, separated from scene texture by an even/odd split.

usage: halfnoise.py EVEN.tif ODD.tif SINGLE_A.tif SINGLE_B.tif FULL.tif y,x [y,x ...]

EVEN and ODD are renders of the even- and odd-indexed frames of one stack (each
aligned on its own, so their grids differ slightly by cover scale). For each
patch origin (given in FULL's coordinates), the matching EVEN and ODD patches
are located by a coarse search on smoothed green, then ODD is registered to EVEN
by phase correlation. Texture common to both halves cancels in EVEN-ODD; what
remains is the two halves' independent noise, so std(EVEN-ODD)/sqrt(2) is one
half-stack's noise. SINGLE_A/SINGLE_B are two adjacent unaligned single frames;
std(A-B)/sqrt(2) is single-frame noise. Both are high-passed (minus a 7x7 box)
first. Reported per channel in linear light, and as luma.

The instrument fails if registration leaves texture: that inflates the
half-stack figure, so it can only understate an improvement.
"""
import sys
import numpy as np
import tifffile
from scipy.ndimage import uniform_filter, shift as nd_shift


def lin(p):
    a = tifffile.imread(p).astype(np.float32) / 65535
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def hp(p):
    return p - uniform_filter(p, (7, 7, 1))


def luma(x):
    return 0.2126 * x[..., 0] + 0.7152 * x[..., 1] + 0.0722 * x[..., 2]


def reg(a, b):
    A = np.fft.fft2(a[..., 1] - a[..., 1].mean())
    B = np.fft.fft2(b[..., 1] - b[..., 1].mean())
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-12
    r = np.real(np.fft.ifft2(R))
    iy, ix = np.unravel_index(r.argmax(), r.shape)
    h, w = r.shape
    dy = iy if iy < h // 2 else iy - h
    dx = ix if ix < w // 2 else ix - w
    return nd_shift(b, (dy, dx, 0), order=3, mode="nearest")


def main():
    ev, od, s1, s2, full = (lin(p) for p in sys.argv[1:6])
    P = 96
    rows = []
    for spec in sys.argv[6:]:
        y, x = (int(v) for v in spec.split(","))
        a = full[y:y + P, x:x + P]

        def find(img):
            best = None
            for dy in range(-64, 65, 4):
                for dx in range(-64, 65, 4):
                    yy, xx = y + dy, x + dx
                    if yy < 0 or xx < 0:
                        continue
                    c = img[yy:yy + P, xx:xx + P]
                    if c.shape != a.shape:
                        continue
                    e = np.mean((uniform_filter(c[..., 1], 9) - uniform_filter(a[..., 1], 9)) ** 2)
                    if best is None or e < best[0]:
                        best = (e, yy, xx)
            return img[best[1]:best[1] + P, best[2]:best[2] + P]

        e = find(ev)
        o = reg(e, find(od))
        d = (hp(e) - hp(o))[8:-8, 8:-8]
        sd = (hp(s1[y:y + P, x:x + P]) - hp(s2[y:y + P, x:x + P]))[8:-8, 8:-8]
        half = luma(d).std() / np.sqrt(2)
        single = luma(sd).std() / np.sqrt(2)
        rows.append(half / single)
        print(f"({y},{x}) luma noise single {single*1e4:7.1f} half-stack {half*1e4:7.1f} "
              f"ratio {half/single:.3f}  per-channel ratio "
              f"{np.round(d.std((0, 1)) / sd.std((0, 1)), 3)}")
    print(f"median luma ratio {np.median(rows):.3f}")


if __name__ == "__main__":
    main()
