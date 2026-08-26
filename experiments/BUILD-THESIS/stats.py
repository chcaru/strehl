"""Detail statistics for the estimation-vs-selection A/B.

THREE statistics, deliberately of different kinds, because one statistic can
have a blind spot shaped exactly like the effect being chased.

  S1  norm     mean |laplacian| / local RMS contrast     (spatial amplitude)
  S2  f50      noise-floor-subtracted spectral half-energy frequency, cyc/px
  S3  acf      1 / half-height correlation length of the detail field, 1/px

S1 is imported, not reimplemented, from ORCH's validated
`experiments/ORCH-drift-check/sharpvscontrast.py`. Reimplementing it would be a
second chance to get it wrong, and its exact box-background and laplacian
kernels are what the 26-master control passed on.

WHY THESE THREE ARE INDEPENDENT

S1 is an amplitude in the spatial domain divided by another amplitude. S2 is a
*location* in the frequency domain and never looks at amplitude at all -- scale
the image by any constant and f50 does not move. S3 is a *count*: how many
distinct structures the image resolves at a scale where they are provably above
that image's own noise. Amplitude, frequency, count. A defect that fools one by
inflating amplitude cannot fool the other two the same way.

S2 and S3 are contrast-invariant by construction, so neither one can be accused
of dividing out the very thing blur destroys -- the failure mode ORCH's control
exists to catch in S1.

WHAT COMMISSIONING KILLED (commission.py, run before any of this voted)

  * A first S3, P99(|grad|)/P75(|grad|), was DISQUALIFIED: it RISES on blur, by
    up to 5.13x on a synthetic chirp with ground-truth blur. Blur erases the
    body of a texture faster than it erases its strongest edges, so the tail
    ratio grows as the image gets softer. It would have scored the softer arm
    as the sharper one. It is not in this file.
  * S1 FAILS the noise null: adding white noise at 5% of tile sigma RAISES
    `norm` by up to 4.7%, and 0.05% impulse noise raises it by up to 0.6%.
    S1 is kept, because it is ORCH's validated instrument and it is strongly
    blur-monotone, but it is kept with that bias stated and measured. It leans
    toward the NOISIER arm, and the noisier arm is `argmax-baseline`.
"""
import pathlib
import sys

import numpy as np

_ORCH = pathlib.Path(__file__).resolve().parents[1] / "ORCH-drift-check"
if str(_ORCH) not in sys.path:
    sys.path.insert(0, str(_ORCH))
import sharpvscontrast as svc  # noqa: E402  ORCH's instrument, imported not copied

BG = svc.BG  # 33 px background window, matched to S2's low-frequency cutoff


# ----------------------------------------------------------------- S1


def s1_norm(t):
    """mean |laplacian| / local RMS contrast. ORCH's `norm`, unmodified."""
    return svc.lap_mean(t) / max(svc.contrast(t), 1e-9)


def s1_parts(t):
    raw = svc.lap_mean(t)
    con = svc.contrast(t)
    return raw, con, raw / max(con, 1e-9)


# ----------------------------------------------------------------- S2

_FMIN = 1.0 / BG   # 0.0303 cyc/px: below this is the background S1 removes
_FMAX = 0.5        # Nyquist
_FLOOR_LO = 0.45   # band assumed to be noise-dominated for floor estimation


def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


def _radial_power(t):
    a = t.astype(np.float64)
    a = a - a.mean()
    h, w = a.shape
    a = a * _hann2(h, w)
    p = np.abs(np.fft.rfft2(a)) ** 2
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    r = np.sqrt(fy ** 2 + fx ** 2)
    nb = 256
    idx = np.clip((r / _FMAX * nb).astype(int), 0, nb - 1)
    tot = np.bincount(idx.ravel(), weights=p.ravel(), minlength=nb)
    cnt = np.bincount(idx.ravel(), minlength=nb)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(cnt > 0, tot / np.maximum(cnt, 1), np.nan)
    f = (np.arange(nb) + 0.5) / nb * _FMAX
    return f, mean, cnt


def s2_f50(t):
    """Half-energy frequency of the noise-floor-subtracted radial spectrum.

    The floor is the mean power over [0.45, 0.5] cyc/px, subtracted from every
    band. A white noise field is flat in power, so this removes it; that is the
    whole reason the statistic can have a noise null at all. It also removes a
    little real detail at the very top, which makes any difference it reports
    an UNDERSTATEMENT, not an overstatement.

    Returns cycles per pixel. Higher = the structure that is present sits at
    higher spatial frequency = more finely resolved. Multiplying the image by
    any constant leaves it unchanged.
    """
    f, mean, cnt = _radial_power(t)
    ok = cnt > 0
    floor_band = ok & (f >= _FLOOR_LO) & (f <= _FMAX)
    floor = np.nanmean(mean[floor_band]) if floor_band.any() else 0.0
    band = ok & (f >= _FMIN) & (f <= _FMAX)
    # weight each radial band by its pixel count: this is energy, not mean power
    e = np.clip(mean[band] - floor, 0.0, None) * cnt[band]
    fb = f[band]
    tot = e.sum()
    if tot <= 0:
        return float("nan")
    c = np.cumsum(e) / tot
    i = int(np.searchsorted(c, 0.5))
    if i == 0:
        return float(fb[0])
    if i >= len(fb):
        return float(fb[-1])
    # linear interpolation inside the crossing band
    c0, c1 = c[i - 1], c[i]
    w = 0.0 if c1 == c0 else (0.5 - c0) / (c1 - c0)
    return float(fb[i - 1] + w * (fb[i] - fb[i - 1]))


# ----------------------------------------------------------------- S3


def _grad(t):
    a = t.astype(np.float64)
    gy = 0.5 * (a[2:, 1:-1] - a[:-2, 1:-1])
    gx = 0.5 * (a[1:-1, 2:] - a[1:-1, :-2])
    return np.sqrt(gy * gy + gx * gx)


def noise_sigma(t):
    """Donoho's robust white-noise sigma from the finest diagonal difference.

    d = (I[y+1,x+1] - I[y+1,x] - I[y,x+1] + I[y,x]) / 2 has unit gain on white
    noise and kills any locally linear signal. The MEDIAN absolute value of d,
    divided by 0.6745, is the noise sigma; being a median it is unmoved by the
    isolated impulses `argmax-baseline` produces, and it is dominated by noise
    rather than structure wherever structure is not everywhere at once.
    """
    a = t.astype(np.float64)
    d = 0.5 * (a[1:, 1:] - a[1:, :-1] - a[:-1, 1:] + a[:-1, :-1])
    return float(np.median(np.abs(d)) / 0.6745)


_LAGS = 12


def s3_acf(t):
    """Inverse half-height correlation length of the background-removed detail.

    D = t - boxmean(t, 33), then the normalised autocorrelation c(k) of D along
    x and y, averaged. The half-height lag L is where c falls to half of its
    lag-zero value, and the statistic is 1/L: shorter correlation length means
    finer structure.

    THE POINT IS THE LAG-ZERO ESTIMATE. White noise is uncorrelated, so it adds
    a delta at lag zero and NOTHING at any lag beyond it. So c(0) is discarded
    and re-estimated by extrapolating a quadratic through c(1), c(2), c(3).
    Every quantity the statistic uses is therefore taken from lags the noise
    cannot reach. That is a structural immunity, not a hoped-for one -- which
    is what a null has to be after two candidate statistics have already been
    killed for having only a hoped-for one.

    Related to S2 by Wiener-Khinchin, and said plainly rather than sold as
    independence: a spectrum and an autocorrelation carry the same information.
    The ESTIMATORS are not the same and do not fail the same way. S2 subtracts
    a flat floor read off the top of the spectrum, which costs it a little real
    detail; S3 never estimates a floor at all and instead extrapolates through
    a corner it cannot see. If those two disagreed it would mean one of the two
    estimators had broken, and that is worth knowing.
    """
    a = t.astype(np.float64)
    d = a - svc.boxmean(a, BG)
    d = d - d.mean()
    cs = []
    for arr in (d, d.T):
        c = [float((arr * arr).mean())]
        for k in range(1, _LAGS + 1):
            c.append(float((arr[:, :-k] * arr[:, k:]).mean()))
        cs.append(np.array(c))
    c = (cs[0] + cs[1]) / 2.0
    # re-estimate lag 0 from lags 1..3: white noise contributes only to lag 0
    p = np.polyfit([1.0, 2.0, 3.0], c[1:4], 2)
    c0 = float(np.polyval(p, 0.0))
    if c0 <= 0:
        return float("nan")
    half = 0.5 * c0
    prev_k, prev_v = 0.0, c0
    for k in range(1, _LAGS + 1):
        v = c[k]
        if v <= half:
            w = 0.0 if prev_v == v else (prev_v - half) / (prev_v - v)
            return float(1.0 / max(prev_k + w * (k - prev_k), 1e-9))
        prev_k, prev_v = float(k), v
    return float(1.0 / _LAGS)


# ----------------------------------------------------------------- all

STATS = {"S1_norm": s1_norm, "S2_f50": s2_f50, "S3_acf": s3_acf}


def all_stats(t):
    return {k: fn(t) for k, fn in STATS.items()}
