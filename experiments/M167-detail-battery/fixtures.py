"""Independent deterministic plants for the M167 detail battery.

This module owns observations only.  It contains no candidate implementation,
pass threshold, or adjudication code.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import gaussian_filter


SIDE = 256
OVERSAMPLE = 4
LATENT_SEED = 167001
FPN_SEED = 167002
NOISE_A_SEED = 167003
NOISE_B_SEED = 167004
NOISE_SD = 0.003
FPN_SD = 0.04
BASE_SIGMA = 1.00
IMPROVED_SIGMA = 0.55
DEGRADED_SIGMA = 1.65
BLUR_SIGMAS = (0.00, 0.50, 1.00, 1.50)
USM_SIGMA = 1.00
USM_AMOUNT = 0.75


@dataclass(frozen=True)
class Observation:
    """The candidate-visible views of one fixture."""

    image: np.ndarray
    repeat_a: np.ndarray
    repeat_b: np.ndarray


def _normalise(array: np.ndarray) -> np.ndarray:
    value = np.asarray(array, dtype=np.float64)
    return (value - float(np.mean(value))) / float(np.std(value))


def _render(latent: np.ndarray, sigma_output_px: float) -> np.ndarray:
    blurred = gaussian_filter(
        latent,
        sigma_output_px * OVERSAMPLE,
        mode="reflect",
        truncate=6.0,
    )
    return blurred.reshape(
        SIDE, OVERSAMPLE, SIDE, OVERSAMPLE
    ).mean(axis=(1, 3))


def _observation(
    scene: np.ndarray,
    noise_a: np.ndarray,
    noise_b: np.ndarray,
) -> Observation:
    a = np.asarray(scene + noise_a, dtype=np.float64)
    b = np.asarray(scene + noise_b, dtype=np.float64)
    return Observation(image=a, repeat_a=a, repeat_b=b)


def _postfilter(observation: Observation, sigma: float) -> Observation:
    if sigma == 0.0:
        return Observation(
            image=observation.image.copy(),
            repeat_a=observation.repeat_a.copy(),
            repeat_b=observation.repeat_b.copy(),
        )

    def blur(image: np.ndarray) -> np.ndarray:
        return gaussian_filter(
            image, sigma, mode="reflect", truncate=6.0
        )

    return Observation(
        image=blur(observation.image),
        repeat_a=blur(observation.repeat_a),
        repeat_b=blur(observation.repeat_b),
    )


def _unsharp(observation: Observation) -> Observation:
    def sharpen(image: np.ndarray) -> np.ndarray:
        low = gaussian_filter(
            image, USM_SIGMA, mode="reflect", truncate=6.0
        )
        return image + USM_AMOUNT * (image - low)

    return Observation(
        image=sharpen(observation.image),
        repeat_a=sharpen(observation.repeat_a),
        repeat_b=sharpen(observation.repeat_b),
    )


def build_fixtures() -> dict[str, object]:
    """Construct every candidate-visible fixture from the frozen recipe."""

    high_side = SIDE * OVERSAMPLE
    latent_rng = np.random.default_rng(LATENT_SEED)
    latent = latent_rng.standard_normal((high_side, high_side))
    latent = gaussian_filter(
        latent, 1.0, mode="reflect", truncate=6.0
    )
    latent = 0.5 + 0.12 * _normalise(latent)

    noise_a = NOISE_SD * np.random.default_rng(
        NOISE_A_SEED
    ).standard_normal((SIDE, SIDE))
    noise_b = NOISE_SD * np.random.default_rng(
        NOISE_B_SEED
    ).standard_normal((SIDE, SIDE))

    base_scene = _render(latent, BASE_SIGMA)
    improved_scene = _render(latent, IMPROVED_SIGMA)
    degraded_scene = _render(latent, DEGRADED_SIGMA)
    base = _observation(base_scene, noise_a, noise_b)
    improved = _observation(improved_scene, noise_a, noise_b)
    degraded = _observation(degraded_scene, noise_a, noise_b)

    fixed_pattern = FPN_SD * _normalise(
        np.random.default_rng(FPN_SEED).standard_normal((SIDE, SIDE))
    )
    flat_detail = _observation(
        base_scene + fixed_pattern, noise_a, noise_b
    )
    flat = _observation(
        np.full((SIDE, SIDE), 0.5, dtype=np.float64) + fixed_pattern,
        noise_a,
        noise_b,
    )

    nonfinite_image = base.image.copy()
    nonfinite_a = base.repeat_a.copy()
    nonfinite_b = base.repeat_b.copy()
    nonfinite_image[0, 0] = np.nan
    nonfinite_a[0, 0] = np.nan
    nonfinite_b[0, 0] = np.nan
    nonfinite = Observation(nonfinite_image, nonfinite_a, nonfinite_b)
    wrong_shape = Observation(
        image=base.image[0].copy(),
        repeat_a=base.repeat_a[0].copy(),
        repeat_b=base.repeat_b[0].copy(),
    )

    return {
        "flat_detail": flat_detail,
        "flat": flat,
        "base": base,
        "improved": improved,
        "degraded": degraded,
        "blur_ladder": [
            {
                "added_sigma_px": sigma,
                "observation": _postfilter(base, sigma),
            }
            for sigma in BLUR_SIGMAS
        ],
        "usm": _unsharp(base),
        "nonfinite": nonfinite,
        "wrong_shape": wrong_shape,
    }
