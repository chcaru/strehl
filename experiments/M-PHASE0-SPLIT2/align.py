"""Scorecard-licensed analytical translation for SPLIT2 repeat pairs."""

from __future__ import annotations

import math

import numpy as np
from scipy.signal.windows import tukey
from skimage.registration import phase_cross_correlation


UPSAMPLE = 100


def window2(shape: tuple[int, int]) -> np.ndarray:
    wy = tukey(shape[0], alpha=0.25)
    wx = tukey(shape[1], alpha=0.25)
    return wy[:, None] * wx[None, :]


def estimate_alignment(
    reference: np.ndarray,
    moving: np.ndarray,
) -> tuple[float, float]:
    """Return the (dy, dx) translation to apply to moving to match reference."""
    if reference.shape != moving.shape or reference.ndim != 2:
        raise ValueError("alignment needs equal 2-D arrays")
    window = window2(reference.shape)
    reference_windowed = (
        np.asarray(reference, dtype=np.float64) - float(np.mean(reference))
    ) * window
    moving_windowed = (
        np.asarray(moving, dtype=np.float64) - float(np.mean(moving))
    ) * window
    shift, _, _ = phase_cross_correlation(
        reference_windowed,
        moving_windowed,
        upsample_factor=UPSAMPLE,
        # Unnormalised cross-correlation is deliberate. Phase-only
        # normalisation overweights empty/noise Fourier modes and missed the
        # fixed external smooth-feature control by more than a pixel.
        normalization=None,
    )
    return float(shift[0]), float(shift[1])


def quadrant_alignments(
    reference: np.ndarray,
    moving: np.ndarray,
) -> list[tuple[float, float]]:
    if reference.shape != moving.shape or reference.shape[0] % 2 or reference.shape[1] % 2:
        raise ValueError("quadrant alignment needs equal even-sized arrays")
    half_y = reference.shape[0] // 2
    half_x = reference.shape[1] // 2
    return [
        estimate_alignment(
            reference[y : y + half_y, x : x + half_x],
            moving[y : y + half_y, x : x + half_x],
        )
        for y in (0, half_y)
        for x in (0, half_x)
    ]


def quadrant_residual_rms_native_pixels(
    global_alignment: tuple[float, float],
    quadrants: list[tuple[float, float]],
) -> float:
    if len(quadrants) != 4:
        raise ValueError("exactly four quadrant alignments are required")
    return 2.0 * math.sqrt(
        sum(
            (shift[0] - global_alignment[0]) ** 2
            + (shift[1] - global_alignment[1]) ** 2
            for shift in quadrants
        )
        / len(quadrants)
    )


def fourier_translate(
    image: np.ndarray,
    shift: tuple[float, float],
    *,
    wrong_sign: bool = False,
) -> tuple[np.ndarray, float, float]:
    """Apply a translation by a unit-modulus Fourier phase ramp."""
    image = np.asarray(image, dtype=np.float64)
    dy, dx = shift
    if wrong_sign:
        dy, dx = -dy, -dx
    fy = np.fft.fftfreq(image.shape[0])[:, None]
    fx = np.fft.fftfreq(image.shape[1])[None, :]
    phase = np.exp(-2.0j * math.pi * (fy * dy + fx * dx))
    transformed = np.fft.fft2(image)
    shifted_spectrum = transformed * phase
    magnitude_error = float(
        np.max(np.abs(np.abs(shifted_spectrum) - np.abs(transformed)))
        / max(float(np.max(np.abs(transformed))), 1e-30)
    )
    shifted_complex = np.fft.ifft2(shifted_spectrum)
    imaginary_rms = float(
        np.sqrt(np.mean(shifted_complex.imag * shifted_complex.imag))
        / max(np.sqrt(np.mean(shifted_complex.real * shifted_complex.real)), 1e-30)
    )
    return shifted_complex.real, magnitude_error, imaginary_rms


COMPONENTS = (
    # ky, kx, amplitude, phase
    (1, 2, 1.2, 0.10),
    (2, -3, 0.8, 1.30),
    (3, 5, 0.6, -0.40),
    (4, 1, 0.5, 2.10),
    (5, -7, 0.4, 0.70),
    (7, 4, 0.35, -1.10),
    (9, -2, 0.30, 1.90),
    (11, 8, 0.24, -2.30),
    (13, -5, 0.20, 0.45),
    (17, 3, 0.15, 2.70),
)

BLOBS = (
    # y, x, sigma, amplitude
    (31.0, 43.0, 3.0, 2.0),
    (52.0, 198.0, 7.0, -1.4),
    (77.0, 119.0, 5.0, 1.1),
    (95.0, 223.0, 11.0, 0.9),
    (121.0, 36.0, 4.0, -1.7),
    (142.0, 151.0, 8.0, 1.5),
    (166.0, 89.0, 6.0, -1.2),
    (188.0, 211.0, 4.0, 1.8),
    (217.0, 57.0, 9.0, 1.0),
    (231.0, 174.0, 5.0, -1.3),
)


def analytic_fixture(
    n: int,
    displacement: tuple[float, float],
) -> tuple[np.ndarray, np.ndarray]:
    """External analytic image; no FFT or translation helper generates it."""
    dy, dx = displacement
    y, x = np.indices((n, n), dtype=np.float64)

    def evaluate(y_coordinate: np.ndarray, x_coordinate: np.ndarray) -> np.ndarray:
        result = np.zeros((n, n), dtype=np.float64)
        for cy, cx, sigma, amplitude in BLOBS:
            radius_squared = (
                (y_coordinate - cy) ** 2 + (x_coordinate - cx) ** 2
            )
            result += amplitude * np.exp(-0.5 * radius_squared / sigma**2)
        for ky, kx, amplitude, phase in COMPONENTS:
            angle = 2.0 * math.pi * (
                ky * y_coordinate / n + kx * x_coordinate / n
            ) + phase
            result += 0.05 * amplitude * np.sin(angle)
        return result

    reference = evaluate(y, x)
    moving = evaluate(y - dy, x - dx)
    return reference, moving


def commission_alignment(*, wrong_sign: bool = False) -> dict[str, object]:
    displacement = (1.25, -0.40)
    reference, moving = analytic_fixture(256, displacement)
    estimated_alignment = estimate_alignment(reference, moving)
    estimated_displacement = (
        -estimated_alignment[0],
        -estimated_alignment[1],
    )
    estimation_error = max(
        abs(estimated_displacement[axis] - displacement[axis])
        for axis in (0, 1)
    )
    aligned, magnitude_error, imaginary_rms = fourier_translate(
        moving,
        estimated_alignment,
        wrong_sign=wrong_sign,
    )
    residual_rms = float(
        np.sqrt(np.mean((aligned - reference) ** 2))
        / np.sqrt(np.mean(reference * reference))
    )
    result = {
        "true_displacement": list(displacement),
        "estimated_alignment": list(estimated_alignment),
        "estimated_displacement": list(estimated_displacement),
        "maximum_estimation_error": estimation_error,
        "aligned_relative_rms": residual_rms,
        "phase_ramp_magnitude_relative_error": magnitude_error,
        "ifft_imaginary_relative_rms": imaginary_rms,
    }
    if estimation_error >= 0.05:
        raise AssertionError(f"translation estimate missed external truth: {result}")
    if magnitude_error > 1e-12:
        raise AssertionError(f"phase ramp changed Fourier magnitude: {result}")
    if residual_rms >= 0.01:
        raise AssertionError(f"translation did not align external truth: {result}")
    return result


def analytic_quadrant_fixture(
    *,
    warped: bool,
) -> tuple[np.ndarray, np.ndarray, float]:
    base = (1.25, -0.40)
    residuals = (
        ((-0.06, 0.0), (0.06, 0.0), (-0.06, 0.0), (0.06, 0.0))
        if warped
        else ((0.0, 0.0),) * 4
    )
    reference = np.zeros((512, 512), dtype=np.float64)
    moving = np.zeros_like(reference)
    for index, (residual_y, residual_x) in enumerate(residuals):
        displacement = (
            base[0] + residual_y,
            base[1] + residual_x,
        )
        ref_quadrant, moving_quadrant = analytic_fixture(256, displacement)
        y = 256 * (index // 2)
        x = 256 * (index % 2)
        reference[y : y + 256, x : x + 256] = ref_quadrant
        moving[y : y + 256, x : x + 256] = moving_quadrant
    true_rms_native = 2.0 * math.sqrt(
        sum(dy * dy + dx * dx for dy, dx in residuals) / 4.0
    )
    return reference, moving, true_rms_native


def commission_local_residual(*, warped: bool = False) -> dict[str, object]:
    reference, moving, true_rms_native = analytic_quadrant_fixture(warped=warped)
    global_alignment = estimate_alignment(reference, moving)
    quadrants = quadrant_alignments(reference, moving)
    measured_rms_native = quadrant_residual_rms_native_pixels(
        global_alignment,
        quadrants,
    )
    result = {
        "warped": warped,
        "global_alignment_quad_pixels": list(global_alignment),
        "quadrant_alignments_quad_pixels": [list(value) for value in quadrants],
        "true_residual_rms_native_pixels": true_rms_native,
        "measured_residual_rms_native_pixels": measured_rms_native,
    }
    if warped:
        if true_rms_native <= 0.10 or measured_rms_native <= 0.10:
            raise AssertionError(f"local-warp plant did not go RED: {result}")
    elif measured_rms_native >= 0.03:
        raise AssertionError(f"pure translation invented local residual: {result}")
    return result
