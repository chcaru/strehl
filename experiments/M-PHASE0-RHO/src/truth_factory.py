"""Independent synthetic truth for M-PHASE0-RHO commissioning.

This module deliberately does not import rho_lib. Its alias grouping and truth
calculation are separately implemented so an estimator geometry defect does not
write its own expected answer.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import brentq


R0 = 0.02


def _wrap(f):
    a = np.asarray(f, dtype=float)
    return ((a + 0.5) % 1.0) - 0.5


def _key(points):
    return tuple(
        sorted(
            tuple(int(round(x * 1_000_000_000)) for x in p)
            for p in points
        )
    )


def _groups(kind, grid=8):
    values = -0.5 + (np.arange(grid) + 0.5) / grid
    seen = {}
    for y in values:
        for x in values:
            f = np.array([x, y], dtype=float)
            if kind == "G":
                pts = [f, _wrap(f + np.array([0.5, 0.5]))]
                base = [p for p in pts if np.abs(p).sum() <= 0.5 + 1e-12]
            elif kind == "RB":
                pts = [
                    f,
                    _wrap(f + np.array([0.5, 0.0])),
                    _wrap(f + np.array([0.0, 0.5])),
                    _wrap(f + np.array([0.5, 0.5])),
                ]
                base = [p for p in pts if np.max(np.abs(p)) <= 0.25 + 1e-12]
            else:
                raise ValueError(kind)
            k = _key(pts)
            if k in seen:
                continue
            if not base:
                raise RuntimeError(f"truth grouping failed for {kind}: {pts}")
            b = min(
                base,
                key=lambda p: (
                    round(float(np.linalg.norm(p)), 14),
                    tuple(int(round(x * 1_000_000_000)) for x in p),
                ),
            )
            aliases = [
                p
                for p in pts
                if tuple(np.round(p, 12)) != tuple(np.round(b, 12))
            ]
            seen[k] = (b, aliases)
    return list(seen.values())


def _power(f, beta, anisotropy=(0.0, 0.0, 0.0, 0.0)):
    a = np.asarray(f, dtype=float)
    r = max(float(np.linalg.norm(a)), R0)
    theta = math.atan2(float(a[1]), float(a[0]))
    c2, s2, c4, s4 = anisotropy
    ang = (
        c2 * math.cos(2 * theta)
        + s2 * math.sin(2 * theta)
        + c4 * math.cos(4 * theta)
        + s4 * math.sin(4 * theta)
    )
    return r ** (-beta) * math.exp(ang)


def truth_rho(kind, beta, anisotropy=(0.0, 0.0, 0.0, 0.0), grid=8):
    groups = _groups(kind, grid)
    bsum = 0.0
    asum = 0.0
    count = 0
    for base, aliases in groups:
        bsum += _power(base, beta, anisotropy)
        for alias in aliases:
            asum += _power(alias, beta, anisotropy)
            count += 1
    per = count / len(groups)
    return asum / (per * bsum)


def beta_for_rho(rho, kind="G"):
    if not (0 < rho <= 1):
        raise ValueError("rho must be in (0,1]")
    if rho == 1:
        return 0.0
    return float(brentq(lambda b: truth_rho(kind, b) - rho, 0.0, 12.0))


def powerlaw_field(
    n,
    beta,
    seed,
    anisotropy=(0.0, 0.0, 0.0, 0.0),
    cutoff=None,
):
    """Real stationary Gaussian field with the requested captured-scene PSD."""
    rng = np.random.default_rng(seed)
    white = rng.normal(size=(n, n))
    fy = np.fft.fftfreq(n)[:, None] * np.ones((1, n))
    fx = np.fft.fftfreq(n)[None, :] * np.ones((n, 1))
    r = np.maximum(np.hypot(fx, fy), R0)
    theta = np.arctan2(fy, fx)
    c2, s2, c4, s4 = anisotropy
    ang = (
        c2 * np.cos(2 * theta)
        + s2 * np.sin(2 * theta)
        + c4 * np.cos(4 * theta)
        + s4 * np.sin(4 * theta)
    )
    psd = np.power(r, -beta) * np.exp(ang)
    if cutoff is not None:
        # Smooth optical roll-off. This is a sensitivity plant, not the model
        # the primary power-law control is expected to fit exactly.
        psd *= np.exp(-2.0 * np.power(r / float(cutoff), 4.0))
    psd[0, 0] = 0.0
    field = np.fft.ifft2(np.fft.fft2(white) * np.sqrt(psd)).real
    field -= float(np.mean(field))
    field /= max(float(np.std(field)), 1e-12)
    return field


def sampled_raw(
    field,
    mean_dn=4000.0,
    contrast_dn=400.0,
    gain_dn_per_e=0.6,
    read_sd_dn=3.0,
    seed=1,
    add_noise=True,
):
    """Achromatic Bayer-like active array with optional signal-dependent noise."""
    signal = mean_dn + contrast_dn * np.asarray(field, dtype=float)
    signal = np.maximum(signal, 50.0)
    if add_noise:
        rng = np.random.default_rng(seed)
        var = gain_dn_per_e * signal + read_sd_dn**2
        signal = signal + rng.normal(0.0, np.sqrt(var), signal.shape)
    return signal


def independent_gq_extract(active, rc, cc, size):
    """Independent implementation of the green quincunx re-indexing."""
    src = np.asarray(active)
    out = np.empty((size, size), dtype=float)
    half = size // 2
    u0 = (rc + cc) // 2
    v0 = (rc - cc) // 2
    for i in range(size):
        u = u0 + i - half
        for j in range(size):
            v = v0 + j - half
            out[i, j] = src[u + v, u - v + 1]
    return out
