"""BUILD-CHROMA common helpers.

Longitudinal (axial) chromatic aberration measured straight from the CFA.

Design commitments, each one traceable to a project rule:

* **No demosaic, ever.** Every number is computed on the four native CFA
  lattices R / G1 / G2 / B. Demosaicing mixes channels spatially and would
  manufacture or mask exactly the effect under test.
* **Integer-only registration** (rule 6). Sub-pixel resampling adds blur to
  the very quantity being measured -- a through-focus sharpness peak. Shifts
  are estimated to sub-pixel precision, smoothed over frame index, and then
  ROUNDED before they are ever applied. `map_coordinates` appears nowhere.
* **The registration shift is estimated on GREEN ONLY and applied identically
  to all four planes.** Estimating a per-channel shift would absorb lateral CA
  into the registration and contaminate the axial question.
* **The independent statistical unit is the TILE, not the point.** The focus
  operator has a 27-plane-px box support, so sample points 10 px apart are
  heavily correlated. Uncertainty is quoted from between-tile scatter.

Geometry, verified against `rawpy` on `lavendar-cpl/DSC00001.ARW`:
    raw_pattern [[0,1],[3,2]], color_desc b'RGBG'  ->  RGGB
    raw_image_visible 4688 x 7028 (h x w)  ->  each plane 2344 x 3514
"""

import os
import glob
import json

import numpy as np
from scipy.ndimage import uniform_filter, sobel, median_filter

OUT = r"C:\dev\strehl-out\BUILD-CHROMA"
LIB = r"D:\personal\macro"

PLANES = ("R", "G1", "G2", "B")

# (x_offset, y_offset) of each plane's site inside the 2x2 RGGB quad.
SITE = {"R": (0, 0), "G1": (1, 0), "G2": (0, 1), "B": (1, 1)}

# Focus operator support, in plane px. 27 matches the shipped box_mean_27 and
# M107's Instrument B, so the two are directly comparable.
WIN = 27


def frames(stack):
    fs = sorted(glob.glob(os.path.join(LIB, stack, "*.ARW")))
    if not fs:
        raise SystemExit(f"no ARW frames for {stack}")
    return fs


def read_cfa(path):
    """Black-subtracted visible CFA as float32. No demosaic, no white balance.

    White balance is deliberately NOT applied: it is a per-channel scalar gain,
    and the focus statistic used here is scale-invariant per channel (the peak
    index of a curve does not move when the curve is multiplied by a constant),
    so applying it would change nothing and add a dependency on metadata.
    """
    import rawpy
    with rawpy.imread(path) as r:
        cfa = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
    return cfa - black


def planes_of(cfa):
    """Split a CFA frame into the four native lattices. No interpolation."""
    return {n: cfa[oy::2, ox::2] for n, (ox, oy) in SITE.items()}


def grad_energy(plane):
    """Sobel gradient energy, unsmoothed."""
    gx = sobel(plane, axis=1, mode="nearest")
    gy = sobel(plane, axis=0, mode="nearest")
    return gx * gx + gy * gy


def integral(img):
    """Summed-area table with a zero first row/column."""
    s = np.cumsum(np.cumsum(img.astype(np.float64), axis=0), axis=1)
    out = np.zeros((s.shape[0] + 1, s.shape[1] + 1), np.float64)
    out[1:, 1:] = s
    return out


def box_at(sat, ys, xs, win=WIN):
    """Box mean of side `win` centred on (ys, xs), read from a summed-area table.

    Exactly equal to `uniform_filter(img, win)` at interior points -- asserted
    in `b0_validate.py` V5. Points must be at least win//2 from the border;
    every sample point in B1 is >= 66 px from the plane edge, so no border
    convention is involved.
    """
    h = win // 2
    y0 = ys - h
    x0 = xs - h
    y1 = ys + h + 1
    x1 = xs + h + 1
    tot = (sat[y1, x1] - sat[y0, x1] - sat[y1, x0] + sat[y0, x0])
    return tot / float(win * win)


def focus(plane, win=WIN):
    """Sobel gradient energy, box-averaged. Same operator as M107 Instrument B."""
    return uniform_filter(grad_energy(plane), win, mode="nearest")


def _win(shape):
    h, w = shape
    return np.hanning(h)[:, None] * np.hanning(w)[None, :]


def ref_spectrum(ref):
    """Pre-compute the windowed reference FFT once, for reuse over all frames."""
    a = (ref - ref.mean()) * _win(ref.shape)
    return np.fft.rfft2(a), ref.shape


def phase_shift_ref(refspec, img):
    """Sub-pixel translation (dy, dx) of `img` relative to the reference.

    Convention, verified by the planted-roll test in `b0_validate.py`: the scene
    point sitting at reference position p appears in `img` at p + (dy, dx), so a
    sample is taken at p + d.

    The result is deliberately returned as a float and rounded LATER, after
    smoothing over frame index -- see `integer_track`. Nothing is resampled.
    """
    A, shape = refspec
    b = (img - img.mean()) * _win(img.shape)
    B = np.fft.rfft2(b)
    C = A * np.conj(B)
    m = np.abs(C)
    C = np.where(m > 1e-12, C / np.maximum(m, 1e-12), 0.0)
    c = np.fft.irfft2(C, s=shape)
    h, w = shape
    py, px = np.unravel_index(np.argmax(c), c.shape)
    dy = py - h if py > h // 2 else py
    dx = px - w if px > w // 2 else px
    return -float(dy), -float(dx)


def phase_shift(ref, img):
    return phase_shift_ref(ref_spectrum(ref), img)


def integer_track(dy, dx, med_win=9, max_shift=40):
    """Robustly smooth a per-frame shift track and round it to integers.

    Defocused or low-structure tiles make phase correlation fail outright --
    measured on `coffee-bean`, one tile in six returned 91 px and -51 px on its
    last three frames while every other tile correctly returned 0. A plain
    median filter does not remove a run of outliers at the end of the track, so
    the track is repaired against a robust MODEL first:

      1. Theil-Sen line in frame index (the true drift is focus-breathing
         magnification, which is smooth and near-linear in k).
      2. Samples further than max(2 px, 3*MAD) from that line are REPLACED by
         the line -- they are correlator failures, not measurements.
      3. The repaired track is median-filtered to retain genuine smooth
         curvature, then ROUNDED. The applied shift is always an integer
         (rule 6); nothing is ever resampled.

    Returns (idy, idx, residual) where `residual` is the median absolute
    deviation of the RAW estimate from the final track -- a per-tile
    registration-quality number that analysis gates on rather than trusting.
    """
    out, res = [], []
    for raw in (np.asarray(dy, float), np.asarray(dx, float)):
        n = raw.size
        k = np.arange(n, dtype=float)
        # Theil-Sen on a subsample of pairs -- exact for n small, cheap for n large
        i = np.arange(0, n, max(1, n // 200))
        a, b = np.meshgrid(i, i)
        m = a < b
        with np.errstate(invalid="ignore", divide="ignore"):
            sl = (raw[b[m]] - raw[a[m]]) / (k[b[m]] - k[a[m]])
        slope = float(np.median(sl[np.isfinite(sl)])) if np.isfinite(sl).any() else 0.0
        icept = float(np.median(raw - slope * k))
        line = slope * k + icept
        d = raw - line
        mad = float(np.median(np.abs(d - np.median(d)))) * 1.4826
        bad = np.abs(d) > max(2.0, 3.0 * mad)
        rep = np.where(bad, line, raw)
        sm = median_filter(rep, size=med_win, mode="nearest")
        sm = np.clip(sm, -max_shift, max_shift)
        out.append(np.rint(sm).astype(int))
        res.append(float(np.median(np.abs(raw - sm))))
    return out[0], out[1], max(res)


def parabola_peak(F, axis=0):
    """Sub-frame peak index of a through-focus curve by 3-point parabola fit.

    F is (nk, npts). Returns (k_hat, peak_value, prominence, interior, unimodal).

    The fit is the classic vertex of the parabola through the argmax sample and
    its two neighbours:  k* = k0 + 0.5*(y_-1 - y_+1) / (y_-1 - 2*y_0 + y_+1).
    The offset is clipped to +-1 frame; a fit that wants to leave the bracketing
    triple is not a parabola peak.
    """
    nk = F.shape[0]
    ki = F.argmax(axis=0)
    interior = (ki > 0) & (ki < nk - 1)
    kk = np.clip(ki, 1, nk - 2)
    idx = np.arange(F.shape[1])
    y0 = F[kk - 1, idx]
    y1 = F[kk, idx]
    y2 = F[kk + 1, idx]
    den = y0 - 2.0 * y1 + y2
    off = np.where(np.abs(den) > 1e-12,
                   0.5 * (y0 - y2) / np.where(np.abs(den) > 1e-12, den, 1.0), 0.0)
    off = np.clip(off, -1.0, 1.0)
    k_hat = kk.astype(np.float64) + off
    med = np.median(F, axis=0)
    prom = y1 / np.maximum(med, 1e-9)
    lo = F.min(axis=0)
    thr = lo + 0.5 * (y1 - lo)
    up = (F[1:-1] > F[:-2]) & (F[1:-1] >= F[2:]) & (F[1:-1] > thr)
    unimodal = up.sum(axis=0) <= 1
    return k_hat, y1, prom, interior, unimodal


def dump(name, obj):
    p = os.path.join(OUT, "json", f"{name}.json")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        json.dump(obj, fh, indent=1, default=float)
    print(f"  -> {p}")
    return p
