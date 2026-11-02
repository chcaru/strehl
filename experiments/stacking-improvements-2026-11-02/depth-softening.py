"""Compare fine-band energy of two renders of the same scene, block by block.

Usage: depth-softening.py a.tif b.tif [--block 128] [--out json]

Both renders are 16-bit sRGB from the same pipeline. Luma is linearised. Each
block of `a` is registered to `b` by phase correlation within a search window
(sub-pixel by parabolic peak, then Fourier shift), so a small breathing offset
between the two references does not read as blur. For each block, band energy
is the power of luma in the radial band [lo, hi] cycles/px, computed with a
Hann window. Blocks are classified by their texture: the band energy of the
coarser band [0.05, 0.12] in `b`, so classification does not use the band being
compared. Reports, per texture decile, the median ratio a/b of fine-band
energy. A ratio below 1 in textured deciles means `a` is softer; in flat deciles
fine-band energy is mostly noise, so a ratio below 1 there means less noise.

Commissioning: `--self-test` compares an image with (i) itself shifted by a
sub-pixel amount (expected 1.0 everywhere), (ii) itself blurred by a Gaussian
(expected < 1 in textured deciles), (iii) itself plus white noise (expected > 1
in flat deciles).
"""
import argparse
import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import fourier_shift, gaussian_filter


def luma(path):
    im = tifffile.imread(path).astype(np.float64) / 65535.0
    lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def band_power(block, lo, hi, win):
    f = np.fft.fft2((block - block.mean()) * win)
    p = np.abs(f) ** 2
    n = block.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fx, fy)
    m = (r >= lo) & (r < hi)
    return p[m].sum() / (n * n)


def register(a, b):
    """Sub-pixel shift taking a onto b (phase correlation)."""
    fa = np.fft.fft2(a - a.mean())
    fb = np.fft.fft2(b - b.mean())
    c = fb * np.conj(fa)
    c /= np.abs(c) + 1e-12
    r = np.real(np.fft.ifft2(c))
    iy, ix = np.unravel_index(np.argmax(r), r.shape)
    n = a.shape[0]

    def sub(v, m, p):
        d = v[m] - 2 * v[0] + v[p]
        return 0.0 if d == 0 else 0.5 * (v[m] - v[p]) / d

    dy = sub(np.array([r[(iy - 1) % n, ix], r[iy, ix], r[(iy + 1) % n, ix]]), 0, 2)
    dx = sub(np.array([r[iy, (ix - 1) % n], r[iy, ix], r[iy, (ix + 1) % n]]), 0, 2)
    sy = iy + dy
    sx = ix + dx
    if sy > n / 2:
        sy -= n
    if sx > n / 2:
        sx -= n
    peak = r.max()
    return sy, sx, peak


def compare(A, B, block, lo, hi, offset=(0, 0)):
    h = min(A.shape[0], B.shape[0])
    w = min(A.shape[1], B.shape[1])
    win1 = np.hanning(block)
    win = np.outer(win1, win1)
    rows = []
    pad = 16
    oy, ox = offset
    for y in range(pad + abs(oy), h - block - pad - abs(oy), block):
        for x in range(pad + abs(ox), w - block - pad - abs(ox), block):
            b = B[y:y + block, x:x + block]
            a = A[y - oy:y - oy + block, x - ox:x - ox + block]
            sy, sx, peak = register(a, b)
            if abs(sy) > 6 or abs(sx) > 6 or peak < 0.05:
                continue
            a2 = np.real(np.fft.ifft2(fourier_shift(np.fft.fft2(a), (sy, sx))))
            core = slice(8, block - 8)
            a2c = a2[core, core]
            bc = b[core, core]
            n = a2c.shape[0]
            wn = np.outer(np.hanning(n), np.hanning(n))
            rows.append((
                band_power(bc, 0.05, 0.12, wn),
                band_power(a2c, lo, hi, wn),
                band_power(bc, lo, hi, wn),
                bc.mean(),
            ))
    return np.array(rows)


def summarise(rows, deciles=10):
    tex = rows[:, 0]
    order = np.argsort(tex)
    out = []
    for k, idx in enumerate(np.array_split(order, deciles)):
        ratio = rows[idx, 1] / np.maximum(rows[idx, 2], 1e-30)
        out.append({"decile": k, "blocks": int(len(idx)), "median_ratio": float(np.median(ratio)),
                    "texture_median": float(np.median(tex[idx]))})
    return out


def coarse_offset(A, B):
    s = 8
    a = A[: A.shape[0] // s * s, : A.shape[1] // s * s].reshape(A.shape[0] // s, s, A.shape[1] // s, s).mean((1, 3))
    b = B[: B.shape[0] // s * s, : B.shape[1] // s * s].reshape(B.shape[0] // s, s, B.shape[1] // s, s).mean((1, 3))
    h = min(a.shape[0], b.shape[0]) // 2 * 2
    w = min(a.shape[1], b.shape[1]) // 2 * 2
    n = min(h, w)
    sy, sx, _ = register(a[:n, :n], b[:n, :n])
    return int(round(sy * s)), int(round(sx * s))


def self_test():
    rng = np.random.default_rng(1)
    base = gaussian_filter(rng.normal(size=(1024, 1024)), 1.2)
    base += 3 * gaussian_filter(rng.normal(size=(1024, 1024)), 6) * (np.arange(1024)[None, :] / 1024)
    base = base - base.min() + 0.1
    shifted = np.real(np.fft.ifft2(fourier_shift(np.fft.fft2(base), (0.37, -0.61))))
    blurred = gaussian_filter(shifted, 0.8)
    noisy = shifted + rng.normal(0, 0.1, base.shape)
    ok = True
    for name, img, check in [
        ("shift", shifted, lambda s: all(0.9 < d["median_ratio"] < 1.1 for d in s)),
        ("blur", blurred, lambda s: s[-1]["median_ratio"] < 0.8),
        ("noise", noisy, lambda s: s[0]["median_ratio"] > 1.1),
    ]:
        s = summarise(compare(img, base, 128, 0.20, 0.35))
        passed = check(s)
        ok &= passed
        print(name, "PASS" if passed else "FAIL", [round(d["median_ratio"], 3) for d in s])
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--block", type=int, default=128)
    ap.add_argument("--band", type=float, nargs=2, default=[0.20, 0.35])
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        sys.exit(0 if self_test() else 1)
    A = luma(args.a)
    B = luma(args.b)
    off = coarse_offset(A, B)
    rows = compare(A, B, args.block, *args.band, offset=off)
    s = summarise(rows)
    print(f"coarse offset {off}, {len(rows)} registered blocks, band {args.band}")
    for d in s:
        print(f"  texture decile {d['decile']}: ratio a/b {d['median_ratio']:.3f} ({d['blocks']} blocks)")
    if args.out:
        json.dump({"a": args.a, "b": args.b, "offset": off, "band": args.band, "deciles": s}, open(args.out, "w"), indent=1)


if __name__ == "__main__":
    main()
