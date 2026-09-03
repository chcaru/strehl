"""Independent fixtures for the preregistered S25-hardening search.

This module owns plants only.  It imports neither candidate variants nor
expected acceptance predicates.
"""

from __future__ import annotations

import math
from collections.abc import Iterator

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.special import expit, ndtr


SIDE = 256
SITE_COUNT = 64
CALIBRATION_PAIRS = 128
BASE_SIGMA = 1.50
BLUR_SIGMA = 0.75
IMPROVED_SIGMA = 1.20
USM_RADIUS = 1.00
USM_AMOUNT = 0.50
NOISE_SD = 0.02
ANGLE_DEG = 5.0
ANGLES = (0.5, 1.0, 5.0, 12.0)
NOISE_SEEDS = tuple(range(2026090300, 2026090324))
SCORE_NAMESPACE = 2026092000
CALIBRATION_NAMESPACE = 2026091000
ELIGIBILITY_NAMESPACE = 2026094000
FLAT_NAMESPACE = 2026096000


def vertical_edge(
    sigma: float,
    angle_deg: float = ANGLE_DEG,
) -> np.ndarray:
    yy, xx = np.mgrid[0:SIDE, 0:SIDE]
    slope = math.tan(math.radians(angle_deg))
    intercept = SIDE / 2.0 - slope * (SIDE - 1) / 2.0
    distance = (xx - (slope * yy + intercept)) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def gaussian_blur(image: np.ndarray) -> np.ndarray:
    return gaussian_filter(
        image,
        BLUR_SIGMA,
        mode="nearest",
        truncate=6.0,
    )


def unsharp(image: np.ndarray) -> np.ndarray:
    low = gaussian_filter(
        image,
        USM_RADIUS,
        mode="nearest",
        truncate=6.0,
    )
    return image + USM_AMOUNT * (image - low)


def tone_map(image: np.ndarray, name: str) -> np.ndarray:
    if name == "identity":
        return np.asarray(image, dtype=np.float64).copy()
    if name == "affine":
        return 1.7 * image + 0.13
    if name == "gamma3":
        return np.power(image, 3.0)
    if name == "logistic":
        return expit(10.0 * (image - 0.5))
    raise KeyError(name)


def _noise(namespace: int, item: int, role: int) -> np.ndarray:
    seed = np.random.SeedSequence([namespace, item, role])
    rng = np.random.default_rng(seed)
    return rng.normal(0.0, NOISE_SD, (SIDE, SIDE))


def calibration_pairs() -> Iterator[tuple[np.ndarray, np.ndarray]]:
    for pair in range(CALIBRATION_PAIRS):
        yield (
            _noise(CALIBRATION_NAMESPACE, pair, 0),
            _noise(CALIBRATION_NAMESPACE, pair, 1),
        )


def score_sites(
    arm: str,
    *,
    noise_index: int | None = None,
    angle_deg: float = ANGLE_DEG,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    if arm == "noise" and noise_index is None:
        raise ValueError("noise arm needs its frozen seed index")
    if arm != "noise" and noise_index is not None:
        raise ValueError("noise index supplied to a non-noise arm")

    base = vertical_edge(BASE_SIGMA, angle_deg)
    blurred = gaussian_blur(base)
    improved = vertical_edge(IMPROVED_SIGMA, angle_deg)
    rows = []
    for site in range(SITE_COUNT):
        noise_a = _noise(SCORE_NAMESPACE, site, 0)
        noise_b = _noise(SCORE_NAMESPACE, site, 1)
        noise_r = _noise(SCORE_NAMESPACE, site, 2)
        a = base + noise_a
        b = base + noise_b
        reference = base + noise_r

        if arm in ("base", "identity", "angle"):
            pass
        elif arm == "blur":
            a = blurred + noise_a
            b = blurred + noise_b
        elif arm == "improvement":
            a = improved + noise_a
            b = improved + noise_b
        elif arm == "sharpen":
            a = unsharp(a)
            b = unsharp(b)
        elif arm in ("affine", "gamma3", "logistic"):
            a = tone_map(a, arm)
            b = tone_map(b, arm)
            reference = tone_map(reference, arm)
        elif arm == "noise":
            assert noise_index is not None
            namespace = NOISE_SEEDS[noise_index]
            a = a + _noise(namespace, site, 0)
            b = b + _noise(namespace, site, 1)
        else:
            raise KeyError(arm)
        rows.append((a, b, reference))
    return rows


def flat_sites(
    *,
    sharpened: bool,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    rows = []
    constant = np.full((SIDE, SIDE), 0.5, dtype=np.float64)
    for site in range(SITE_COUNT):
        a = constant + _noise(FLAT_NAMESPACE, site, 0)
        b = constant + _noise(FLAT_NAMESPACE, site, 1)
        reference = constant + _noise(FLAT_NAMESPACE, site, 2)
        if sharpened:
            a = unsharp(a)
            b = unsharp(b)
        rows.append((a, b, reference))
    return rows


def eligibility_sites(
    kind: str,
) -> list[tuple[np.ndarray, np.ndarray]]:
    rows = []
    edge = vertical_edge(BASE_SIGMA)
    defocused = gaussian_blur(edge)
    constant = np.full((SIDE, SIDE), 0.5, dtype=np.float64)
    for site in range(SITE_COUNT):
        first_noise = _noise(ELIGIBILITY_NAMESPACE, site, 0)
        second_noise = _noise(ELIGIBILITY_NAMESPACE, site, 1)
        if kind == "edge":
            focused = edge + first_noise
            moving = defocused + second_noise
        elif kind == "equal":
            focused = edge + first_noise
            moving = edge + second_noise
        elif kind == "flat":
            focused = constant + first_noise
            moving = constant + second_noise
        else:
            raise KeyError(kind)
        rows.append((focused, moving))
    return rows


def nominal_ramp() -> np.ndarray:
    return np.tile(
        np.linspace(0.02, 0.98, 33, dtype=np.float64),
        (8, 1),
    )


def observed_ramp(arm: str) -> np.ndarray:
    nominal = nominal_ramp()
    if arm in ("affine", "gamma3", "logistic"):
        return tone_map(nominal, arm)
    return nominal.copy()


def heterogeneous_power_control() -> tuple[np.ndarray, np.ndarray]:
    focused = np.ones((SITE_COUNT, 5), dtype=np.float64)
    defocused = np.ones((SITE_COUNT, 5), dtype=np.float64)
    focused[-4:, :] = 20.0
    return focused, defocused

