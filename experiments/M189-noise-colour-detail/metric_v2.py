"""Conservative-envelope PTC-anchored repeat-detail candidate."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


FREQ_LO = 0.12
FREQ_HI = 0.30
RADIAL_BINS = 36


@dataclass(frozen=True)
class Measurement:
    score: float
    local_score: float
    raw_coherent_power: float
    reference_noise_power: float
    observed_noise_power: float
    weighted_noise_gain: float
    bin_gain_min: float
    bin_gain_median: float
    bin_gain_max: float
    licensed_modes: int
    populated_bins: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


def _validate(repeat_a: np.ndarray, repeat_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(repeat_a, dtype=np.float64)
    b = np.asarray(repeat_b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("repeat arrays must have identical shapes")
    if a.ndim != 3:
        raise ValueError("repeat arrays must have shape (pairs, height, width)")
    if a.shape[0] < 2 or a.shape[1] < 32 or a.shape[2] < 32:
        raise ValueError("insufficient repeat or spatial support")
    if not np.all(np.isfinite(a)) or not np.all(np.isfinite(b)):
        raise ValueError("repeat arrays must be finite")
    return a, b


def measure(
    repeat_a: np.ndarray,
    repeat_b: np.ndarray,
    *,
    gain_dn_per_e: float,
    read_noise_e: float,
) -> Measurement:
    a, b = _validate(repeat_a, repeat_b)
    gain = float(gain_dn_per_e)
    read = float(read_noise_e)
    if not np.isfinite(gain) or gain <= 0.0:
        raise ValueError("gain_dn_per_e must be positive and finite")
    if not np.isfinite(read) or read < 0.0:
        raise ValueError("read_noise_e must be nonnegative and finite")

    mean_level = float(np.mean((a + b) * 0.5))
    reference_noise = gain * mean_level + (gain * read) ** 2
    if not np.isfinite(reference_noise) or reference_noise <= 0.0:
        raise ValueError("predicted noise power must be positive and finite")

    fa = np.fft.fft2(a, axes=(-2, -1), norm="ortho")
    fb = np.fft.fft2(b, axes=(-2, -1), norm="ortho")
    coherent = np.mean(np.real(fa * np.conj(fb)), axis=0)
    difference_noise = np.mean(0.5 * np.abs(fa - fb) ** 2, axis=0)

    height, width = a.shape[-2:]
    fy = np.fft.fftfreq(height)[:, None]
    fx = np.fft.fftfreq(width)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    licensed = (radius >= FREQ_LO) & (radius < FREQ_HI)
    licensed_modes = int(np.count_nonzero(licensed))
    if licensed_modes == 0:
        raise ValueError("licensed frequency band is empty")

    edges = np.linspace(FREQ_LO, FREQ_HI, RADIAL_BINS + 1)
    local_score_sum = 0.0
    raw_sum = 0.0
    noise_sum = 0.0
    mode_sum = 0
    gains: list[float] = []

    for index in range(RADIAL_BINS):
        mask = (radius >= edges[index]) & (radius < edges[index + 1])
        count = int(np.count_nonzero(mask))
        if count == 0:
            continue
        coherent_sum = float(np.sum(coherent[mask]))
        observed_noise = float(np.mean(difference_noise[mask]))
        noise_gain = observed_noise / reference_noise
        local_score_sum += coherent_sum / max(1.0, noise_gain)
        raw_sum += coherent_sum
        noise_sum += float(np.sum(difference_noise[mask]))
        mode_sum += count
        gains.append(noise_gain)

    if mode_sum != licensed_modes or not gains:
        raise RuntimeError("radial bin accounting does not cover the licensed band")

    gain_array = np.asarray(gains, dtype=np.float64)
    gain_sup = float(np.max(gain_array))
    raw_coherent = raw_sum / mode_sum
    observed_noise_power = noise_sum / mode_sum
    return Measurement(
        score=raw_coherent / max(1.0, gain_sup),
        local_score=local_score_sum / mode_sum,
        raw_coherent_power=raw_coherent,
        reference_noise_power=reference_noise,
        observed_noise_power=observed_noise_power,
        weighted_noise_gain=observed_noise_power / reference_noise,
        bin_gain_min=float(np.min(gain_array)),
        bin_gain_median=float(np.median(gain_array)),
        bin_gain_max=gain_sup,
        licensed_modes=licensed_modes,
        populated_bins=len(gains),
    )

