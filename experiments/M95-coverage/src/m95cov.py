"""Shared machinery for M95 arm 5 — pricing coverage scale against warp phase.

Band-matching, reused from arm 4 (`M95-resample/src/x2_pairs.py`), is the step
that makes arms with different sampling densities comparable. An arm whose
output samples the source at step k carries the scene's Nyquist at 0.5*k cyc/px,
so its band limits must be scaled by its own k. Comparing at a FIXED cyc/px band
across arms with different k is a units error that penalises the magnified arm,
and above 0.5*k it compares real content against a guaranteed hole.

Blur is applied as the exact transfer function exp(-2*pi^2*sigma^2*f^2). A
sampled Gaussian kernel of radius ceil(4*sigma) collapses to a delta for small
sigma and reads ~0, which is indistinguishable from a genuine sensitivity floor.
"""
import numpy as np
import tifffile

BAND = (0.30, 0.48)
LOWBAND = (0.02, 0.10)
TILE = 256
PAD = 384
NTILES = 40


def load_luma(path):
    a = tifffile.imread(str(path))
    if a.ndim == 3:
        a = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return np.asarray(a, dtype=np.float64)


def pick_tiles(img, n=NTILES, tile=TILE, pad=PAD):
    """The n sharpest non-overlapping tiles, kept clear of the border by `pad`."""
    h, w = img.shape
    m = pad
    cand = []
    for y in range(m, h - m - tile, tile):
        for x in range(m, w - m - tile, tile):
            t = img[y : y + tile, x : x + tile]
            s = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
            cand.append((s, y, x))
    cand.sort(reverse=True)
    taken = []
    for s, y, x in cand:
        if all(abs(y - ty) >= tile or abs(x - tx) >= tile for ty, tx in taken):
            taken.append((y, x))
        if len(taken) == n:
            break
    return taken


# ---------------------------------------------------------------- kernels


def catmull_rom(t):
    """Cubic convolution, a = -0.5. Taps for fractional offset t in [0,1)."""
    t2, t3 = t * t, t * t * t
    return np.stack([
        -0.5 * t3 + t2 - 0.5 * t,
        1.5 * t3 - 2.5 * t2 + 1.0,
        -1.5 * t3 + 2.0 * t2 + 0.5 * t,
        0.5 * t3 - 0.5 * t2,
    ])


def lanczos(t, a):
    """Lanczos-a taps for fractional offset t in [0,1). Support 2a."""
    ks = np.arange(-a + 1, a + 1, dtype=np.float64)
    x = ks[:, None] - t[None, :]
    with np.errstate(invalid="ignore", divide="ignore"):
        w = np.sinc(x) * np.sinc(x / a)
    w = np.where(np.abs(x) < 1e-12, 1.0, w)
    w = np.where(np.abs(x) >= a, 0.0, w)
    return w / w.sum(axis=0, keepdims=True)


KERNELS = {
    "catmull-rom": (4, lambda t: catmull_rom(t)),
    "lanczos3": (6, lambda t: lanczos(t, 3)),
    "lanczos8": (16, lambda t: lanczos(t, 8)),
}


def gather_1d(a, coords, axis, kernel="catmull-rom"):
    """Separable gather along one axis at float `coords`."""
    taps, fn = KERNELS[kernel]
    half = taps // 2
    a = np.moveaxis(np.asarray(a, dtype=np.float64), axis, 0)
    i0 = np.floor(coords).astype(np.int64)
    w = fn((coords - i0).astype(np.float64))
    n = a.shape[0]
    out = np.zeros((len(coords),) + a.shape[1:], dtype=np.float64)
    for j in range(taps):
        idx = np.clip(i0 - half + 1 + j, 0, n - 1)
        out += w[j][:, None] * a[idx]
    return np.moveaxis(out, 0, axis)


def gather(src, step, off_y, off_x, n_out=TILE, kernel="catmull-rom"):
    """One gather. Output pixel i samples the source at centre + i*step + off.

    `step` < 1 magnifies: the output covers n_out*step source pixels. This is
    the same convention `fit_to_cover` uses, where k is the coverage factor.
    """
    h, w = src.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    co = (n_out - 1) / 2.0
    i = np.arange(n_out, dtype=np.float64) - co
    vy = cy + i * step + off_y
    vx = cx + i * step + off_x
    out = gather_1d(src, vy, 0, kernel)
    return gather_1d(out, vx, 1, kernel)


def centre_crop(src, n=TILE):
    h, w = src.shape
    y, x = (h - n) // 2, (w - n) // 2
    return src[y : y + n, x : x + n]


# ------------------------------------------------------------- spectrum


def _window(n):
    return np.outer(np.hanning(n), np.hanning(n))


def _freqs(n):
    f = np.fft.fftfreq(n)
    return np.sqrt(f[:, None] ** 2 + f[None, :] ** 2)


def band_ratio(t, k):
    """log10 of high-band power normalised by low-band power, band-matched by k."""
    n = t.shape[0]
    p = np.abs(np.fft.fft2((t - t.mean()) * _window(n))) ** 2
    fr = _freqs(n)
    hi = (fr >= BAND[0] * k) & (fr < BAND[1] * k)
    lo = (fr >= LOWBAND[0] * k) & (fr < LOWBAND[1] * k)
    return float(np.log10(p[hi].mean() / p[lo].mean()))


def band_ratio_fixed(t):
    """The orchestrator's convention: a FIXED band regardless of the arm's k."""
    return band_ratio(t, 1.0)


def fourier_blur(t, sigma):
    """Exact Gaussian blur as a transfer function, not a sampled kernel."""
    n = t.shape[0]
    f = np.fft.fftfreq(n)
    fr2 = f[:, None] ** 2 + f[None, :] ** 2
    return np.real(np.fft.ifft2(np.fft.fft2(t) * np.exp(-2 * np.pi**2 * sigma**2 * fr2)))


def mean_sd(vals):
    v = np.asarray(vals, dtype=np.float64)
    return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v)))
