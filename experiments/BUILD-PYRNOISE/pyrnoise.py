"""BUILD-PYRNOISE -- the external instrument.

The shipping pyramid backend REFUSES `--flat-roi`, `--detail-roi`, `--stats`,
`--n-eff-map` and five other estimator flags, so it cannot be asked to measure
itself. Everything here is external: it reads the byte-frozen measurement TIFF
(binned, linear, camera-native RGB, one real sensor quad per pixel) that every
arm writes, and computes on the GREEN plane only.

Two statistics, both reported, because they are not the same question.

  raw_sd  -- the LEGACY flat-ROI statistic. Spatial sd of the region. This is
             the statistic behind the README's 1.253x / 0.890x / 0.534x column
             (M53 §1.2 labels it "LEGACY ratio"), so it is what a new row must
             be quoted in to be commensurable. It is contaminated by scene
             structure, which is identical across arms and therefore compresses
             every ratio toward 1.0. Known failure direction: it UNDER-reports
             a noise excess (M53 finding 3: 1.068x legacy against 1.223x
             high-pass on the same ROI).

  hp_sd   -- M53's replacement: sd of `x - box9(x)`, de-biased by the kernel's
             own white-noise gain sqrt(1 - 1/81) = 0.993808. Structure above
             the box scale is removed, so this is much closer to a pure noise
             ratio. Known failure direction: it still reads high on texture
             finer than the box, so it is an upper bound on noise, never a
             lower one.

  f50     -- noise-corrected spectral half-power frequency, the DETAIL
             statistic. See `f50()` for why it is built the way it is and for
             the two ways it can be fooled.
"""

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

BOX = 9
HP_GAIN = np.sqrt(1.0 - 1.0 / (BOX * BOX))  # 0.9938079900...


def green(path):
    """Green plane of a strehl measurement TIFF, as float64 DN.

    The measurement output is ALWAYS binned: R = R, G = (G1+G2)/2, B = B, one
    output pixel per 2x2 CFA quad. Channel 1 is therefore the mean of the two
    green sites of that quad, already in camera-linear DN.
    """
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"{path}: expected HxWx3, got {a.shape}")
    return a[:, :, 1].astype(np.float64)


def crop(a, roi, pad=0):
    x, y, w, h = roi
    return a[y - pad:y + h + pad, x - pad:x + w + pad]


def raw_sd(a):
    """Legacy statistic: plain spatial sd over the region."""
    return float(a.std(ddof=1))


def hp_sd(a, w=BOX):
    """M53's high-pass residual sd, de-biased for the kernel's noise gain.

    `a` must already carry `w` pixels of real margin on every side; the caller
    crops it back. Filtering a bare ROI and keeping its edges would mix a
    reflected boundary into the statistic.
    """
    r = a - uniform_filter(a, size=w, mode="reflect")
    r = r[w:-w, w:-w]
    gain = np.sqrt(1.0 - 1.0 / (w * w))
    return float(r.std(ddof=1) / gain)


def roi_stats(img, roi):
    """Both noise statistics on one ROI of one image."""
    pad = BOX
    x, y, w, h = roi
    if x - pad < 0 or y - pad < 0 or y + h + pad > img.shape[0] or x + w + pad > img.shape[1]:
        raise ValueError(f"roi {roi} too close to the border of {img.shape}")
    big = crop(img, roi, pad)
    return {
        "raw_sd": raw_sd(crop(img, roi)),
        "hp_sd": hp_sd(big),
        "mean": float(crop(img, roi).mean()),
    }


# --------------------------------------------------------------------------
# detail
# --------------------------------------------------------------------------

def radial_power(a, nbins=96):
    """Radially averaged power spectrum of a Hann-windowed, mean-removed tile.

    Returns (f, P) with f in cycles/pixel on (0, 0.5].
    """
    a = np.asarray(a, dtype=np.float64)
    a = a - a.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.fft.rfft2(a * win)
    P = (F.real ** 2 + F.imag ** 2)
    fy = np.fft.fftfreq(a.shape[0])[:, None]
    fx = np.fft.rfftfreq(a.shape[1])[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2).ravel()
    P = P.ravel()
    keep = (r > 0) & (r <= 0.5)
    r, P = r[keep], P[keep]
    edges = np.linspace(0.0, 0.5, nbins + 1)
    idx = np.clip(np.digitize(r, edges) - 1, 0, nbins - 1)
    cnt = np.bincount(idx, minlength=nbins)
    tot = np.bincount(idx, weights=P, minlength=nbins)
    ok = cnt > 0
    f = 0.5 * (edges[:-1] + edges[1:])
    return f[ok], tot[ok] / cnt[ok]


def f50(a, noise_band=(0.42, 0.50), f_lo=0.05, return_parts=False):
    """Noise-corrected spectral half-power frequency, in cycles/pixel.

    Why this shape. A plain gradient-energy or spectral statistic RISES on
    added noise, which is the failure that killed three detail statistics in
    this project already -- a gradient norm read +33% under 15% added noise and
    that turned out to be its entire apparent result on five of six subjects.
    Here the flat white-noise pedestal is ESTIMATED from the top frequency
    band, where an optically band-limited capture has essentially no signal,
    and SUBTRACTED before any frequency is read off.

    `f_lo` is load-bearing and was added BECAUSE THE FIRST VERSION FAILED ITS
    OWN BLUR NULL. Without it the cumulative-50% point of a real macro tile
    lands at 0.0033 c/px -- a period of 300 px -- because the scene's
    low-frequency envelope carries almost all the power. A statistic sitting
    there cannot see a 1 px blur and measured only 2.9% of one. Restricting the
    cumulative to f >= f_lo puts the statistic in the band where resolved
    detail actually lives. The pedestal is still estimated and subtracted on
    the UNRESTRICTED spectrum, so the white-noise correction is unaffected by
    the choice. `f50_sensitivity()` sweeps f_lo and is reported.

    Properties:
      * exactly invariant to contrast AND to a DC offset: scaling the tile by
        g scales P, the pedestal estimate and the residual all by g^2, and the
        normalised cumulative is unchanged. Arithmetic, asserted as such.
      * approximately invariant to added white noise, because the added power
        is flat and is what the pedestal estimate removes. NOT arithmetic --
        the estimate is a median over a finite band -- so it is commissioned by
        planting noise across the full range of the effect being measured.
      * falls under blur, because blur multiplies P(f) by a decreasing function
        of f and the subtraction cannot put that back.

    HOW IT CAN BE FOOLED, stated next to where it is used (rule 18):
      * it will read HIGH on an arm that has been sharpened or that carries
        aliasing, because both put power at high f that is not resolved
        detail. It is admissible as evidence of detail LOSS, and inadmissible
        on its own as evidence of detail GAIN.
      * if real signal survives into `noise_band` the pedestal estimate eats
        it. That biases every arm the same way only if every arm has the same
        signal there, which is not guaranteed after resampling -- and the
        aligned arms ARE resampled. Read the aligned/unaligned split.
    """
    f, P = radial_power(a)
    band = (f >= noise_band[0]) & (f <= noise_band[1])
    n0 = float(np.median(P[band])) if band.any() else 0.0
    S = np.clip(P - n0, 0.0, None)
    # power per annulus ~ P(f) * 2*pi*f * df; df is constant across bins
    wgt = S * f
    keep = f >= f_lo
    f, wgt = f[keep], wgt[keep]
    c = np.cumsum(wgt)
    if c[-1] <= 0:
        return (np.nan, n0, f, P) if return_parts else np.nan
    c = c / c[-1]
    # first crossing of 0.5, linearly interpolated
    k = int(np.searchsorted(c, 0.5))
    if k == 0:
        val = float(f[0])
    else:
        f0, f1, c0, c1 = f[k - 1], f[k], c[k - 1], c[k]
        val = float(f0 + (0.5 - c0) * (f1 - f0) / (c1 - c0)) if c1 > c0 else float(f1)
    return (val, n0, f, P) if return_parts else val


def f50_sensitivity(a, los=(0.03, 0.05, 0.08, 0.12)):
    """f50 over a sweep of the one free choice in it, so the choice is visible."""
    return {lo: f50(a, f_lo=lo) for lo in los}


def hf_share(a, noise_band=(0.42, 0.50), f_lo=0.05, f_hi=0.25):
    """Share of noise-corrected band power that sits in the TOP OCTAVE.

    Built after `f50` failed its own blur null. The reason it failed is
    structural and worth stating: a macro tile's spectrum is very red (fitted
    here at roughly f^-3.2), so the power-weighted MEDIAN frequency is pinned
    near `f_lo` and a 1 px blur -- which annihilates the top end and barely
    touches the median -- moves it only 2%. The median is a weak blur detector
    on red content no matter how it is tuned.

    This reads the end of the spectrum that blur actually destroys: the
    fraction of annulus-integrated, noise-corrected power above `f_hi`. Same
    pedestal subtraction, so the same white-noise immunity; and it is a ratio
    of two powers, so contrast invariance is again exact.

    HOW IT CAN BE FOOLED (rule 18): it rises on sharpening, on aliasing, and on
    any residual noise the pedestal estimate fails to remove -- all three put
    power at high f that is not resolved detail. It is admissible as evidence
    of detail LOSS. A RISE in it is not evidence of detail gain without a
    separate check that the extra high-f power is correlated with truth.
    """
    f, P = radial_power(a)
    band = (f >= noise_band[0]) & (f <= noise_band[1])
    n0 = float(np.median(P[band])) if band.any() else 0.0
    S = np.clip(P - n0, 0.0, None) * f
    lo = S[f >= f_lo].sum()
    hi = S[f >= f_hi].sum()
    return float(hi / lo) if lo > 0 else np.nan


def spectral_centroid(a, noise_band=(0.42, 0.50), f_lo=0.05):
    """Power-weighted mean frequency of the noise-corrected spectrum."""
    f, P = radial_power(a)
    band = (f >= noise_band[0]) & (f <= noise_band[1])
    n0 = float(np.median(P[band])) if band.any() else 0.0
    S = np.clip(P - n0, 0.0, None) * f
    keep = f >= f_lo
    f, S = f[keep], S[keep]
    return float((S * f).sum() / S.sum()) if S.sum() > 0 else np.nan


def acf_length(a, thresh=0.5):
    """Autocorrelation half-length in pixels, on the box9 high-pass residual.

    Second, independent detail statistic. High-passing first is what makes it
    respond to detail rather than to the scene's low-frequency envelope. A
    LONGER length means a BLURRED image. Reported as its reciprocal-free raw
    value; commissioned in `commission.py` exactly like f50.
    """
    a = np.asarray(a, dtype=np.float64)
    a = a - uniform_filter(a, size=BOX, mode="reflect")
    a = a[BOX:-BOX, BOX:-BOX]
    a = a - a.mean()
    win = np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    F = np.fft.rfft2(a * win)
    ac = np.fft.irfft2(F.real ** 2 + F.imag ** 2, s=a.shape)
    ac = np.fft.fftshift(ac)
    ac = ac / ac.max()
    cy, cx = ac.shape[0] // 2, ac.shape[1] // 2
    n = 24
    prof = []
    for d in range(n):
        vals = []
        if cx + d < ac.shape[1]:
            vals.append(ac[cy, cx + d])
        if cx - d >= 0:
            vals.append(ac[cy, cx - d])
        if cy + d < ac.shape[0]:
            vals.append(ac[cy + d, cx])
        if cy - d >= 0:
            vals.append(ac[cy - d, cx])
        prof.append(np.mean(vals))
    prof = np.array(prof)
    for d in range(1, n):
        if prof[d] <= thresh:
            p0, p1 = prof[d - 1], prof[d]
            return float((d - 1) + (p0 - thresh) / (p0 - p1)) if p0 > p1 else float(d)
    return float(n)
