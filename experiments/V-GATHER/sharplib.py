"""V-GATHER statistic E: is the master sharper than the best frame that went in?

Every gauge argument in orch_sharp1to1.py is removed by construction, not by
correction: BOTH arms are renders from the SAME pinned binary with the SAME
flags and the SAME pinned exposure, and STREHL_COVER=0 on both so neither is
magnified relative to the other. Numerator and denominator therefore share
demosaic, CA, colour matrix, exposure gain, sRGB curve and output grid.

The statistic is a RATIO OF BANDS, so it is invariant to any overall contrast
scaling; it cannot be moved by an exposure or tone difference the way a raw
gradient energy can.
"""
import numpy as np
from scipy.signal import fftconvolve

P = 128          # patch, power of two for the FFT
SEARCH = 48      # integer registration half-range, px. INTEGER ONLY: a sub-pixel
                 # resample would blur the very quantity being measured.
LO = (0.04, 0.12)   # reference band, cyc/px  (features 8-25 px)
HI = (0.20, 0.40)   # detail band, cyc/px     (features 2.5-5 px)


def luma(rgb):
    return (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2])


def orig_detail(y):
    """Verbatim reimplementation of orch_sharp1to1.detail()[0], for comparison."""
    gx = np.abs(np.diff(y, axis=1))[:-1, :]
    gy = np.abs(np.diff(y, axis=0))[:, :-1]
    return float((gx + gy).mean())


_W = None
_RF = None


def _win_and_rings(n):
    global _W, _RF
    if _W is not None and _W.shape[0] == n:
        return _W, _RF
    w = np.hanning(n)
    _W = np.outer(w, w)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    _RF = np.sqrt(fy * fy + fx * fx)
    return _W, _RF


def acutance(y):
    """E(HI)/E(LO): band-limited contrast ratio. Amplitude-invariant."""
    n = y.shape[0]
    w, rf = _win_and_rings(n)
    a = y - y.mean()
    pw = np.abs(np.fft.fft2(a * w)) ** 2
    lo = pw[(rf >= LO[0]) & (rf < LO[1])].sum()
    hi = pw[(rf >= HI[0]) & (rf < HI[1])].sum()
    if lo <= 0:
        return float("nan")
    return float(hi / lo)


def register(ref, win, s=SEARCH):
    """Integer-shift normalised cross-correlation. Returns (dy, dx, corr)."""
    r = ref - ref.mean()
    rn = float(np.sqrt((r * r).sum()))
    if rn <= 0:
        return 0, 0, 0.0
    k = r[::-1, ::-1]
    num = fftconvolve(win, k, mode="valid")
    ones = np.ones_like(r)
    s1 = fftconvolve(win, ones, mode="valid")
    s2 = fftconvolve(win * win, ones, mode="valid")
    n = r.size
    var = np.maximum(s2 - s1 * s1 / n, 1e-9)
    corr = num / (rn * np.sqrt(var))
    i = int(np.argmax(corr))
    dy, dx = divmod(i, corr.shape[1])
    return dy - s, dx - s, float(corr[dy, dx])


def blur(a, sigma):
    """Separable Gaussian, reflect edges."""
    if sigma <= 0:
        return a.copy()
    r = max(1, int(np.ceil(3 * sigma)))
    x = np.arange(-r, r + 1, dtype=np.float64)
    g = np.exp(-0.5 * (x / sigma) ** 2)
    g /= g.sum()
    o = np.pad(a, ((0, 0), (r, r)), mode="reflect")
    o = np.apply_along_axis(lambda v: np.convolve(v, g, "valid"), 1, o)
    o = np.pad(o, ((r, r), (0, 0)), mode="reflect")
    return np.apply_along_axis(lambda v: np.convolve(v, g, "valid"), 0, o)


def usm(a, amount, sigma=1.0):
    return a + amount * (a - blur(a, sigma))
