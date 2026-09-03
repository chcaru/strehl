"""Independent synthetic truth factory for M-PHASE0-ASTIG commissioning.

This module deliberately does not import ``astiglib``.  Image formation uses
separable Gaussian blurs on additive one-dimensional gratings.  The estimator
therefore cannot write its own stimulus or expected answer.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.ndimage import gaussian_filter1d


def _orientation_peaks(
    delta: float,
    centre: float,
    sector: str,
) -> tuple[float, float]:
    z_t = centre + delta / 2.0
    z_s = centre - delta / 2.0
    if sector in ("left", "right", "centre"):
        return z_t, z_s
    if sector in ("top", "bottom"):
        return z_s, z_t
    raise ValueError(f"unknown sector {sector!r}")


def oriented_cube(
    delta: float,
    *,
    sector: str = "right",
    centre: float = 9.0,
    frames: int = 19,
    size: int = 128,
    seed: int = 20260902,
    noise_sd: float = 5.0,
    flat: bool = False,
) -> tuple[np.ndarray, dict]:
    """Make a noisy oriented image cube with independently centred PSF arms."""
    if not (2.5 <= centre - abs(delta) / 2):
        raise ValueError("left peak is too close to the focus-axis boundary")
    if not (centre + abs(delta) / 2 <= frames - 3.5):
        raise ValueError("right peak is too close to the focus-axis boundary")
    rng = np.random.default_rng(seed)
    yy, xx = np.indices((size, size), dtype=np.float64)
    # Incommensurate components stop one fortunate grid phase from deciding it.
    vx = (
        np.sin(2.0 * np.pi * (xx + 0.37) / 11.0)
        + 0.45 * np.sin(2.0 * np.pi * (xx + 1.7) / 23.0)
    )
    hy = (
        np.sin(2.0 * np.pi * (yy + 0.61) / 13.0)
        + 0.45 * np.sin(2.0 * np.pi * (yy + 2.1) / 19.0)
    )
    zx, zy = _orientation_peaks(delta, centre, sector)
    out = []
    for k in range(frames):
        if flat:
            image = np.full((size, size), 2600.0)
        else:
            sigma_x = math.sqrt(0.45**2 + (0.52 * (k - zx)) ** 2)
            sigma_y = math.sqrt(0.45**2 + (0.52 * (k - zy)) ** 2)
            bx = gaussian_filter1d(vx, sigma_x, axis=1, mode="wrap")
            by = gaussian_filter1d(hy, sigma_y, axis=0, mode="wrap")
            # A common illumination drift exercises the registered denominator.
            gain = 1.0 + 0.004 * (k - centre)
            image = gain * (2600.0 + 390.0 * bx + 390.0 * by)
        image = image + rng.normal(0.0, noise_sd, image.shape)
        out.append(image.astype(np.float64))
    truth = {
        "delta": float(delta),
        "centre": float(centre),
        "sector": sector,
        "zx": float(zx),
        "zy": float(zy),
        "frames": int(frames),
        "size": int(size),
        "noise_sd": float(noise_sd),
        "flat": bool(flat),
        "seed": int(seed),
    }
    return np.stack(out), truth


def response_blocks(
    delta: float,
    *,
    datasets: int = 100,
    frames: int = 17,
    blocks: int = 16,
    centre: float = 8.0,
    width: float = 2.1,
    seed: int = 0xA571600,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], dict]:
    """Independent noisy response cubes for bootstrap-coverage commissioning.

    Each spatial block has a common focus displacement in both arms and a
    random local split drawn around the population truth. Correct paired
    resampling preserves that covariance; independently resampling the arms
    destroys it and inflates the reported uncertainty.
    """
    rng = np.random.default_rng(seed)
    k = np.arange(frames, dtype=np.float64)[:, None]
    pairs = []
    for _ in range(datasets):
        common = rng.normal(0.0, 0.38, size=(1, blocks))
        local_delta = delta + rng.normal(0.0, 0.10, size=(1, blocks))
        zt = centre + local_delta / 2.0 + common
        zs = centre - local_delta / 2.0 + common
        ex = np.exp(-0.5 * ((k - zt) / width) ** 2)
        ey = np.exp(-0.5 * ((k - zs) / width) ** 2)
        block_gain = np.exp(rng.normal(0.0, 0.12, size=(1, blocks)))
        ex *= block_gain
        ey *= block_gain
        # Independent response noise is deliberately modest; block covariance
        # is the dominant term that the paired bootstrap must handle.
        ex += rng.normal(0.0, 0.001, size=ex.shape)
        ey += rng.normal(0.0, 0.001, size=ey.shape)
        ex = np.maximum(ex, 1e-7)
        ey = np.maximum(ey, 1e-7)
        pairs.append((ex, ey))
    return pairs, {
        "delta": float(delta),
        "datasets": int(datasets),
        "frames": int(frames),
        "blocks": int(blocks),
        "centre": float(centre),
        "width": float(width),
        "seed": int(seed),
    }
