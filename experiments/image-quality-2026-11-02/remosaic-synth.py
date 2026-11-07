"""Size the loss of the default consumer's remosaic step against RGB-domain fusion.

Truth is a real RGB image with no interpolation in it: one RAW frame binned by
quads (R, (G1+G2)/2, B). A sensor is simulated at that resolution by shifting the
truth with an exact band-limited (FFT) subpixel shift and sampling it RGGB.

Arms, all scored against the unshifted truth on the interior:
  direct : MHC of the unshifted mosaic (demosaic floor, no warp)
  rgb    : MHC of the shifted mosaic, Catmull-Rom pulled back to truth coordinates
  remos  : `rgb`, then re-mosaiced (keep each site's own colour) and MHC again --
           the default consumer's path for one source
Also a K-frame mean of several shifted sources, fused in each domain, because the
remosaic path averages mosaics and then demosaics once.

Self-test: shift 0 must make rgb == direct to float precision, and remos ==
direct exactly (MHC keeps native samples, so re-mosaic of an identity is lossless).
"""
import sys
import numpy as np
import rawpy
from scipy.ndimage import convolve

RNG = np.random.default_rng(7)


def load_truth(path):
    with rawpy.imread(path) as r:
        raw = r.raw_image_visible.astype(np.float64).copy()
        black = float(np.mean(r.black_level_per_channel))
        pat = r.raw_pattern.copy()
    raw = np.maximum(raw - black, 0)
    h, w = raw.shape
    h, w = h // 2 * 2, w // 2 * 2
    raw = raw[:h, :w]
    q = {}
    for dy in (0, 1):
        for dx in (0, 1):
            q[(dy, dx)] = raw[dy::2, dx::2]
    # colour index per quad position from the decoder's pattern (0 R,1 G,2 B,3 G)
    planes = {0: [], 1: [], 2: []}
    for (dy, dx), p in q.items():
        c = int(pat[dy, dx])
        planes[1 if c == 3 else c].append(p)
    rgb = np.stack([np.mean(planes[c], axis=0) for c in (0, 1, 2)], axis=-1)
    return rgb / np.quantile(rgb[..., 1], 0.999)


def fft_shift(img, dy, dx):
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    ph = np.exp(-2j * np.pi * (fy * dy + fx * dx))
    return np.real(np.fft.ifft2(np.fft.fft2(img) * ph))


def mosaic(rgb):
    h, w, _ = rgb.shape
    m = np.zeros((h, w))
    m[0::2, 0::2] = rgb[0::2, 0::2, 0]
    m[0::2, 1::2] = rgb[0::2, 1::2, 1]
    m[1::2, 0::2] = rgb[1::2, 0::2, 1]
    m[1::2, 1::2] = rgb[1::2, 1::2, 2]
    return m


# Malvar-He-Cutler 2004 5x5 filters (from the paper), scaled by 1/8.
G_AT_RB = np.array([[0, 0, -1, 0, 0], [0, 0, 2, 0, 0], [-1, 2, 4, 2, -1],
                    [0, 0, 2, 0, 0], [0, 0, -1, 0, 0]]) / 8
RB_AT_G_ROW = np.array([[0, 0, .5, 0, 0], [0, -1, 0, -1, 0], [-1, 4, 5, 4, -1],
                        [0, -1, 0, -1, 0], [0, 0, .5, 0, 0]]) / 8
RB_AT_G_COL = RB_AT_G_ROW.T
RB_AT_BR = np.array([[0, 0, -1.5, 0, 0], [0, 2, 0, 2, 0], [-1.5, 0, 6, 0, -1.5],
                     [0, 2, 0, 2, 0], [0, 0, -1.5, 0, 0]]) / 8


def mhc(m):
    h, w = m.shape
    r = np.zeros((h, w), bool); r[0::2, 0::2] = True
    b = np.zeros((h, w), bool); b[1::2, 1::2] = True
    g = ~(r | b)
    g_row_r = np.zeros((h, w), bool); g_row_r[0::2, 1::2] = True  # G in R rows
    g_row_b = np.zeros((h, w), bool); g_row_b[1::2, 0::2] = True  # G in B rows
    c_g = convolve(m, G_AT_RB, mode="mirror")
    c_row = convolve(m, RB_AT_G_ROW, mode="mirror")
    c_col = convolve(m, RB_AT_G_COL, mode="mirror")
    c_x = convolve(m, RB_AT_BR, mode="mirror")
    R = np.where(r, m, 0.0); G = np.where(g, m, 0.0); B = np.where(b, m, 0.0)
    G = np.where(r | b, c_g, G)
    R = np.where(g_row_r, c_row, R); R = np.where(g_row_b, c_col, R); R = np.where(b, c_x, R)
    B = np.where(g_row_b, c_row, B); B = np.where(g_row_r, c_col, B); B = np.where(r, c_x, B)
    return np.stack([R, G, B], axis=-1)


def cr_weights(t):
    a = -0.5
    t = np.abs(t)
    return np.where(t < 1, (a + 2) * t**3 - (a + 3) * t**2 + 1,
                    np.where(t < 2, a * t**3 - 5 * a * t**2 + 8 * a * t - 4 * a, 0.0))


def cr_shift(img, dy, dx):
    """Catmull-Rom pull: out(y,x) = img(y+dy, x+dx), separable, integer + frac."""
    def along(a, d, axis):
        i = int(np.floor(d)); f = d - i
        out = np.zeros_like(a)
        for k in (-1, 0, 1, 2):
            out += cr_weights(k - f) * np.roll(a, -(i + k), axis=axis)
        return out
    return along(along(img, dy, 0), dx, 1)


def psnr_bands(est, truth, border=24):
    e = est[border:-border, border:-border] - truth[border:-border, border:-border]
    t = truth[border:-border, border:-border]
    out = {}
    for c, name in enumerate("RGB"):
        mse = np.mean(e[..., c] ** 2)
        out[name] = 10 * np.log10(np.mean(t[..., c] ** 2) / mse)
    # luminance error power by radial frequency band (cycles/pixel)
    yl = 0.2126 * e[..., 0] + 0.7152 * e[..., 1] + 0.0722 * e[..., 2]
    tl = 0.2126 * t[..., 0] + 0.7152 * t[..., 1] + 0.0722 * t[..., 2]
    ch = e[..., 0] - e[..., 1], e[..., 2] - e[..., 1]
    win = np.outer(np.hanning(yl.shape[0]), np.hanning(yl.shape[1]))
    fy = np.fft.fftfreq(yl.shape[0])[:, None]; fx = np.fft.fftfreq(yl.shape[1])[None, :]
    rad = np.hypot(fy, fx)
    E = np.abs(np.fft.fft2(yl * win)) ** 2
    T = np.abs(np.fft.fft2(tl * win)) ** 2
    for lo, hi in ((0, .1), (.1, .2), (.2, .3), (.3, .4), (.4, .5)):
        sel = (rad >= lo) & (rad < hi)
        out[f"Y{lo:.1f}-{hi:.1f}"] = 10 * np.log10(T[sel].sum() / E[sel].sum())
    out["chromaErr"] = float(np.sqrt(np.mean(ch[0] ** 2 + ch[1] ** 2)))
    return out


def main():
    path = sys.argv[1]
    y0, x0, size = (int(v) for v in sys.argv[2:5])
    noise = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    truth_full = load_truth(path)
    truth = truth_full[y0:y0 + size, x0:x0 + size]
    up = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
    if up != 1.0:
        # band-limit the truth to a diffraction cutoff below the new Nyquist: zero-pad
        # its spectrum by `up`, then apply an incoherent circular-pupil MTF whose cutoff
        # is 0.84 cycles/pixel * 0.5 (f/16 at 3.76 um, 550 nm).
        h = int(round(size * up)) // 2 * 2
        out = []
        fy = np.fft.fftfreq(h)[:, None]; fx = np.fft.fftfreq(h)[None, :]
        nu = np.hypot(fy, fx) / 0.42
        mtf = np.where(nu < 1, 2 / np.pi * (np.arccos(np.minimum(nu, 1)) - nu * np.sqrt(np.maximum(1 - nu**2, 0))), 0)
        for c in range(3):
            F = np.fft.fftshift(np.fft.fft2(truth[..., c]))
            P = np.zeros((h, h), complex)
            o = (h - size) // 2
            P[o:o + size, o:o + size] = F
            out.append(np.real(np.fft.ifft2(np.fft.ifftshift(P) * mtf)) * (h * h) / (size * size))
        truth = np.stack(out, -1)
    truth = truth.copy()
    # self-test at zero shift
    m0 = mosaic(truth)
    d0 = mhc(m0)
    assert np.allclose(cr_shift(d0, 0.0, 0.0), d0)
    assert np.allclose(mhc(mosaic(d0)), d0)
    print("self-test ok")

    def source(dy, dx):
        sh = np.stack([fft_shift(truth[..., c], dy, dx) for c in range(3)], -1)
        m = mosaic(sh)
        if noise > 0:
            m = m + RNG.normal(0, noise, m.shape) * np.sqrt(np.maximum(m, 1e-4))
        rgb = mhc(m)
        # source(y,x) = truth(y-dy, x-dx); pull back: out(y,x) = rgb(y+dy, x+dx)
        return cr_shift(np.stack([rgb[..., c] for c in range(3)], -1).copy(), dy, dx)

    def score(name, est):
        s = psnr_bands(est, truth)
        print(f"{name:14s} " + " ".join(f"{k}={v:7.3f}" for k, v in s.items()))

    score("direct", mhc(mosaic(truth if noise == 0 else truth)))
    for K in (1, 4, 16):
        shifts = [(0.5, 0.5)] if K == 1 else [tuple(RNG.uniform(-2, 2, 2)) for _ in range(K)]
        rgbs = [np.stack([source(dy, dx)[..., c] for c in range(3)], -1) for dy, dx in shifts]
        rgb_mean = np.mean(rgbs, axis=0)
        remos_mean = mhc(np.mean([mosaic(r) for r in rgbs], axis=0))
        score(f"rgb K={K}", rgb_mean)
        score(f"remos K={K}", remos_mean)


if __name__ == "__main__":
    main()
