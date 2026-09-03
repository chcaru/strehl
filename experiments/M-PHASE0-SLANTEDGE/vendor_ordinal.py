"""Source-pinned ordinal functions vendored for the survivor audit.

The provenance checker requires each function AST below to equal its matching
V-HEADTOHEAD3 definition.  Keep candidate functions verbatim.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import rankdata


BANDS: tuple[tuple[float, float], ...] = (
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, 0.25),
    (0.25, 0.30),
    (0.30, 0.40),
)


def midrank_field(a: np.ndarray) -> np.ndarray:
    """Average ranks, centred and scaled exactly as preregistered."""
    x = np.asarray(a)
    n = x.size
    if n < 2:
        raise ValueError("rank field needs at least two samples")
    r = rankdata(x.ravel(), method="average").reshape(x.shape)
    return (r - (n + 1.0) / 2.0) / n


def _spectral_shares(field: np.ndarray, band_scale: float = 1.0) -> np.ndarray:
    x = np.asarray(field, np.float64)
    if x.ndim != 2:
        raise ValueError("spectral field must be 2-D")
    wy = np.hanning(x.shape[0])
    wx = np.hanning(x.shape[1])
    z = (x - np.mean(x)) * wy[:, None] * wx[None, :]
    power = np.abs(np.fft.fft2(z)) ** 2
    fy = np.fft.fftfreq(x.shape[0])[:, None]
    fx = np.fft.fftfreq(x.shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    values = []
    for lo, hi in BANDS:
        mask = (radius >= lo * band_scale) & (radius < hi * band_scale)
        values.append(float(np.sum(power[mask], dtype=np.float64)))
    values = np.asarray(values, np.float64)
    total = float(np.sum(values))
    if not np.isfinite(total) or total <= 0.0:
        raise ValueError("zero/non-finite admitted spectral power")
    return values / total


def ordinal_shares(a: np.ndarray, band_scale: float = 1.0) -> np.ndarray:
    return _spectral_shares(midrank_field(a), band_scale)


def _window(shape: tuple[int, int]) -> np.ndarray:
    return np.hanning(shape[0])[:, None] * np.hanning(shape[1])[None, :]


def frequency_radius(shape: tuple[int, int]) -> np.ndarray:
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.fftfreq(shape[1])[None, :]
    return np.sqrt(fx * fx + fy * fy)


def licensed_mask(shape: tuple[int, int], band_scale: float = 1.0) -> np.ndarray:
    r = frequency_radius(shape)
    return (r >= 0.20 * band_scale) & (r < 0.25 * band_scale)


def q25_rank_field(q: np.ndarray, band_scale: float = 1.0) -> float:
    """Licensed spectral backend for an already constructed rank field."""
    q = np.asarray(q, np.float64).copy()
    q -= np.mean(q)
    var = float(np.mean(q * q))
    if not var > 0:
        raise ValueError("Q25 requires a non-constant crop")
    w = _window(q.shape)
    z = q * w
    power = np.abs(np.fft.fft2(z)) ** 2
    num = float(np.sum(power[licensed_mask(q.shape, band_scale)], dtype=np.float64))
    den = q.size * float(np.sum(w * w, dtype=np.float64)) * var
    if not den > 0:
        raise ValueError("Q25 denominator is not positive")
    return num / den


def q25(a: np.ndarray, band_scale: float = 1.0) -> float:
    """Licensed-band energy per fixed average-rank variance.

    The denominator is Parseval's expected windowed energy from the rank
    variance.  It does not inspect any other measured frequency band.
    """
    return q25_rank_field(midrank_field(np.asarray(a)), band_scale)

