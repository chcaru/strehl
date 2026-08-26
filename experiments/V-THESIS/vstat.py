"""V-THESIS: an INDEPENDENT detail instrument for the estimation-vs-selection A/B.

Written from scratch for the verification pass. It shares no code with
experiments/BUILD-THESIS/. The design targets the three things that can turn a
real difference into a false negative in this particular comparison:

  TRANSLATION.  `argmax-baseline` does not align; `stack` does. Any statistic
                that needs sub-pixel correspondence between the arms is
                measuring registration error. So the instrument is built on the
                POWER SPECTRUM, which is exactly translation invariant. A
                mis-located tile changes nothing as long as it holds the same
                scene content.

  SCALE.        `stack` crops the field of view to s (0.92-0.97 here) and
                upsamples back, so the merge arm is MAGNIFIED by 1/s relative
                to the argmax arm. Every per-pixel sharpness number is
                therefore biased. This instrument works in SCENE-REFERRED
                frequency: FFT bin index k IS "cycles across the tile", and if
                the two tiles span the same scene content then bin k of one
                means the same physical thing as bin k of the other, whatever
                the pixel counts are. The scale correction is structural, not
                a post-hoc factor.

  GAIN.         The fit carries a free additive constant in log power, so any
                overall exposure/contrast/window difference between the arms
                cancels. Nothing is normalised by a contrast estimate, which is
                the failure mode ORCH's control exists to catch.

THE STATISTIC (VA)

  If arm A is arm M convolved with a Gaussian of sigma_s (in scene units),
  then  ln P_A(k) - ln P_M(k) = c - 4 pi^2 sigma_s^2 k^2  exactly.
  Weighted least squares of the log power ratio against k^2 gives sigma_s from
  the slope; the intercept c absorbs gain. Reported in MERGE PIXELS,
  sigma_px = sigma_s * Tm, positive meaning THE MERGE RESOLVES FINER.

  White noise is flat in power and its contribution, sigma_DN^2 * sum(w^2), is
  computed exactly from the window and subtracted before the log. That is why
  the statistic can have a noise null rather than hope for one.

VB is a second, cheaper reading of the same spectra that does not assume a
Gaussian: the scene-referred frequency below which half the noise-corrected
band energy sits. It is a location, not a slope, so it fails differently.
"""
import numpy as np

# ----------------------------------------------------------------- noise

_IMM = np.array([[1.0, -2.0, 1.0], [-2.0, 4.0, -2.0], [1.0, -2.0, 1.0]])


def sigma_immerkaer(t):
    """Robust white-noise sigma via Immerkaer's 3x3 kernel with a MEDIAN.

    Deliberately NOT Donoho's diagonal difference (which is what BUILD-THESIS
    used) so that the two noise numbers are independent estimators. Kernel
    noise gain is sum(k^2) = 36, so sigma = median|conv| / (0.6745 * 6).
    The median makes it insensitive to the isolated impulses argmax produces.
    """
    a = np.asarray(t, dtype=np.float64)
    c = (_IMM[0, 0] * a[:-2, :-2] + _IMM[0, 1] * a[:-2, 1:-1] + _IMM[0, 2] * a[:-2, 2:]
         + _IMM[1, 0] * a[1:-1, :-2] + _IMM[1, 1] * a[1:-1, 1:-1] + _IMM[1, 2] * a[1:-1, 2:]
         + _IMM[2, 0] * a[2:, :-2] + _IMM[2, 1] * a[2:, 1:-1] + _IMM[2, 2] * a[2:, 2:])
    return float(np.median(np.abs(c)) / (0.6745 * 6.0))


# ----------------------------------------------------------------- spectrum

def radial_power(t, sigma_dn=None, kmax=None):
    """Radially binned power spectrum indexed by CYCLES ACROSS THE TILE.

    Returns (k, power, nmodes). k is an integer bin index and therefore a
    scene-referred frequency: bin k means k cycles across whatever scene span
    the tile covers, independent of how many pixels were used to sample it.

    If sigma_dn is given, the exact flat contribution of white noise of that
    sigma through the same window, sigma^2 * sum(w^2), is subtracted.
    """
    a = np.asarray(t, dtype=np.float64)
    a = a - a.mean()
    n, m = a.shape
    w = np.outer(np.hanning(n), np.hanning(m))
    F = np.fft.rfft2(a * w)
    P = F.real ** 2 + F.imag ** 2
    if sigma_dn is not None:
        P = P - (sigma_dn ** 2) * float((w * w).sum())
    ky = np.fft.fftfreq(n, d=1.0 / n)[:, None]      # integer cycles across tile
    kx = np.fft.rfftfreq(m, d=1.0 / m)[None, :]
    kr = np.sqrt(ky * ky + kx * kx)
    if kmax is None:
        kmax = int(min(n, m) // 2)
    idx = np.rint(kr).astype(np.int64)
    keep = (idx >= 0) & (idx <= kmax)
    tot = np.bincount(idx[keep], weights=P[keep], minlength=kmax + 1)
    cnt = np.bincount(idx[keep], minlength=kmax + 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    return np.arange(kmax + 1), mean, cnt


# ----------------------------------------------------------------- VA

def va_blur_px(tm, ta, band_periods=(24.0, 4.0), denoise=True, return_fit=False):
    """Equivalent Gaussian blur separating two tiles of the SAME scene content.

    tm, ta may have different pixel counts; that is the point. Positive means
    the merge tile (tm) resolves finer, in MERGE pixels.

    band_periods is the fit band expressed as merge-pixel periods, converted to
    scene-referred bin indices as k = Tm / period. Fixed, not data-chosen.
    """
    tm = np.asarray(tm, dtype=np.float64)
    ta = np.asarray(ta, dtype=np.float64)
    Tm = min(tm.shape)
    Ta = min(ta.shape)
    sm = sigma_immerkaer(tm) if denoise else None
    sa = sigma_immerkaer(ta) if denoise else None
    kcap = int(0.80 * (min(Tm, Ta) // 2))            # stay clear of EITHER Nyquist
    km, Pm, Nm = radial_power(tm, sm, kcap)
    ka, Pa, Na = radial_power(ta, sa, kcap)
    klo = max(2, int(np.ceil(Tm / band_periods[0])))
    khi = min(kcap, int(np.floor(Tm / band_periods[1])))
    if khi <= klo + 4:
        return (np.nan, {}) if return_fit else np.nan
    sel = np.zeros_like(Pm, dtype=bool)
    sel[klo:khi + 1] = True
    sel &= (Nm > 0) & (Na > 0) & np.isfinite(Pm) & np.isfinite(Pa) & (Pm > 0) & (Pa > 0)
    if sel.sum() < 6:
        return (np.nan, {}) if return_fit else np.nan
    k = km[sel].astype(np.float64)
    y = np.log(Pa[sel]) - np.log(Pm[sel])
    wt = Nm[sel].astype(np.float64)
    x = k * k
    # weighted least squares y = c + b x
    sw = wt.sum()
    mx = (wt * x).sum() / sw
    my = (wt * y).sum() / sw
    b = (wt * (x - mx) * (y - my)).sum() / max((wt * (x - mx) ** 2).sum(), 1e-30)
    sigma_s = np.sqrt(abs(b)) / (2.0 * np.pi)
    sigma_px = float(np.sign(-b) * sigma_s * Tm)
    if return_fit:
        c = my - b * mx
        resid = y - (c + b * x)
        return sigma_px, dict(slope=float(b), klo=int(klo), khi=int(khi),
                              nbins=int(sel.sum()), sigma_dn_merge=sm,
                              sigma_dn_argmax=sa,
                              resid_rms=float(np.sqrt((wt * resid ** 2).sum() / sw)),
                              Tm=int(Tm), Ta=int(Ta))
    return sigma_px


# ----------------------------------------------------------------- VB

def vb_f50_scene(t, sigma_dn=None, band_periods=(24.0, 4.0)):
    """Scene-referred half-energy frequency, in cycles across the tile.

    A location rather than a slope, computed on the same noise-corrected
    spectra. Contrast invariant. Comparable between arms WITHOUT a per-pixel
    scale factor because the axis is cycles-across-the-tile, not cycles/pixel.
    """
    t = np.asarray(t, dtype=np.float64)
    T = min(t.shape)
    s = sigma_immerkaer(t) if sigma_dn is None else sigma_dn
    kcap = int(0.80 * (T // 2))
    k, P, N = radial_power(t, s, kcap)
    klo = max(2, int(np.ceil(T / band_periods[0])))
    khi = min(kcap, int(np.floor(T / band_periods[1])))
    sel = np.zeros_like(P, dtype=bool)
    sel[klo:khi + 1] = True
    sel &= (N > 0) & np.isfinite(P)
    e = np.clip(P[sel], 0.0, None) * N[sel]
    kk = k[sel].astype(np.float64)
    tot = e.sum()
    if tot <= 0:
        return float("nan")
    c = np.cumsum(e) / tot
    i = int(np.searchsorted(c, 0.5))
    if i == 0:
        return float(kk[0])
    if i >= len(kk):
        return float(kk[-1])
    c0, c1 = c[i - 1], c[i]
    wgt = 0.0 if c1 == c0 else (0.5 - c0) / (c1 - c0)
    return float(kk[i - 1] + wgt * (kk[i] - kk[i - 1]))
