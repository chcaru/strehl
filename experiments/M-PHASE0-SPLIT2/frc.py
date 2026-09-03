"""Pure-Python FRC and repeat-null primitives for M-PHASE0-SPLIT2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np


TILE = 256
THRESHOLD = 1.0 / 7.0
MIN_RING_SAMPLES = 16
MIDBAND = (0.10, 0.2762)
NULL_BANDS = ((0.02, 0.15), (0.15, 0.30), (0.30, 0.48))


@dataclass
class Spectrum:
    """Full-plane-equivalent radial sums from an rfft2 half plane."""

    count: np.ndarray
    cross: np.ndarray
    power_a: np.ndarray
    power_b: np.ndarray
    noise: np.ndarray

    @classmethod
    def zeros(cls, rings: int) -> "Spectrum":
        return cls(*(np.zeros(rings, dtype=np.float64) for _ in range(5)))

    def copy(self) -> "Spectrum":
        return Spectrum(
            self.count.copy(),
            self.cross.copy(),
            self.power_a.copy(),
            self.power_b.copy(),
            self.noise.copy(),
        )

    def add(self, other: "Spectrum") -> None:
        self.count += other.count
        self.cross += other.cross
        self.power_a += other.power_a
        self.power_b += other.power_b
        self.noise += other.noise

    @property
    def frequencies(self) -> np.ndarray:
        return np.arange(self.count.size, dtype=np.float64) / (
            2.0 * (self.count.size - 1)
        )

    def frc(self) -> np.ndarray:
        denominator = np.sqrt(self.power_a * self.power_b)
        out = np.full(self.count.size, np.nan, dtype=np.float64)
        valid = (
            (self.count >= MIN_RING_SAMPLES)
            & np.isfinite(denominator)
            & (denominator > 0.0)
        )
        np.divide(self.cross, denominator, out=out, where=valid)
        return out

    def snr(self) -> np.ndarray:
        out = np.full(self.count.size, np.nan, dtype=np.float64)
        valid = (
            (self.count >= MIN_RING_SAMPLES)
            & np.isfinite(self.noise)
            & (self.noise > 0.0)
        )
        np.divide(self.cross, self.noise, out=out, where=valid)
        return out


@dataclass
class Analysis:
    aggregate: Spectrum
    tiles: list[Spectrum]


def _frequency_grid(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ky = np.fft.fftfreq(n)[:, None] * n
    kx = np.fft.rfftfreq(n)[None, :] * n
    radius = np.floor(np.hypot(kx, ky) + 0.5).astype(np.int32)
    weights = np.full((n, n // 2 + 1), 2.0, dtype=np.float64)
    weights[:, 0] = 1.0
    if n % 2 == 0:
        weights[:, -1] = 1.0
    valid = (radius > 0) & (radius <= n // 2)
    return radius, weights, valid


def spectrum_tile(
    a: np.ndarray,
    b: np.ndarray,
    *,
    wrong_conjugate: bool = False,
) -> Spectrum:
    if a.ndim != 2 or b.shape != a.shape or a.shape[0] != a.shape[1]:
        raise ValueError("spectrum_tile needs equal square 2-D arrays")
    n = a.shape[0]
    if n < 8 or n % 2:
        raise ValueError("tile side must be even and at least 8")

    window_1d = np.hanning(n)
    window = window_1d[:, None] * window_1d[None, :]
    aw = (np.asarray(a, dtype=np.float64) - float(np.mean(a))) * window
    bw = (np.asarray(b, dtype=np.float64) - float(np.mean(b))) * window
    fa = np.fft.rfft2(aw)
    fb = np.fft.rfft2(bw)
    if wrong_conjugate:
        cross = np.real(fa * fb)
    else:
        cross = np.real(fa * np.conj(fb))
    power_a = np.abs(fa) ** 2
    power_b = np.abs(fb) ** 2
    noise = 0.5 * np.abs(fa - fb) ** 2

    radius, weights, valid = _frequency_grid(n)
    indices = radius[valid]
    rings = n // 2 + 1

    def radial_sum(values: np.ndarray) -> np.ndarray:
        return np.bincount(
            indices,
            weights=(values * weights)[valid],
            minlength=rings,
        ).astype(np.float64, copy=False)

    return Spectrum(
        radial_sum(np.ones_like(cross)),
        radial_sum(cross),
        radial_sum(power_a),
        radial_sum(power_b),
        radial_sum(noise),
    )


def analyse_pair(
    a: np.ndarray,
    b: np.ndarray,
    *,
    tile: int = TILE,
    wrong_conjugate: bool = False,
) -> Analysis:
    if a.ndim != 2 or b.shape != a.shape:
        raise ValueError("analyse_pair needs equal 2-D arrays")
    height, width = a.shape
    if height < tile or width < tile:
        raise ValueError("image is smaller than one tile")
    if height % tile or width % tile:
        raise ValueError("image dimensions must be exact multiples of tile size")
    tiles = []
    for y in range(0, height, tile):
        for x in range(0, width, tile):
            tiles.append(
                spectrum_tile(
                    a[y : y + tile, x : x + tile],
                    b[y : y + tile, x : x + tile],
                    wrong_conjugate=wrong_conjugate,
                )
            )
    aggregate = Spectrum.zeros(tile // 2 + 1)
    for item in tiles:
        aggregate.add(item)
    return Analysis(aggregate, tiles)


def aggregate_spectra(items: Iterable[Spectrum]) -> Spectrum:
    items = list(items)
    if not items:
        raise ValueError("cannot aggregate no spectra")
    out = Spectrum.zeros(items[0].count.size)
    for item in items:
        if item.count.size != out.count.size:
            raise ValueError("spectrum ring counts differ")
        out.add(item)
    return out


def band_frc(spectrum: Spectrum, lo: float, hi: float) -> float:
    frequency = spectrum.frequencies
    selected = (frequency >= lo) & (frequency < hi)
    cross = float(np.sum(spectrum.cross[selected]))
    power_a = float(np.sum(spectrum.power_a[selected]))
    power_b = float(np.sum(spectrum.power_b[selected]))
    denominator = math.sqrt(power_a * power_b)
    return cross / denominator if denominator > 0.0 else math.nan


def mean_abs_frc(spectrum: Spectrum) -> float:
    values = spectrum.frc()
    valid = np.isfinite(values)
    return float(np.mean(np.abs(values[valid])))


def max_ring_null_t(tiles: list[Spectrum]) -> float:
    if len(tiles) < 4:
        return math.nan
    result = 0.0
    rings = tiles[0].count.size
    for radius in range(1, rings):
        values = np.asarray(
            [
                tile.frc()[radius]
                for tile in tiles
                if np.isfinite(tile.frc()[radius])
            ],
            dtype=np.float64,
        )
        if values.size < 4:
            continue
        mean = float(np.mean(values))
        standard_error = float(np.std(values, ddof=1) / math.sqrt(values.size))
        if standard_error > 0.0:
            value = abs(mean / standard_error)
        elif mean == 0.0:
            value = 0.0
        else:
            value = math.inf
        result = max(result, value)
    return result


def max_midband_snr(spectrum: Spectrum) -> float:
    frequency = spectrum.frequencies
    values = spectrum.snr()
    selected = (
        (frequency >= MIDBAND[0])
        & (frequency < MIDBAND[1])
        & np.isfinite(values)
    )
    if not np.any(selected):
        return math.nan
    return float(np.max(values[selected]))


def classify(
    spectrum: Spectrum,
    *,
    last_bin_fallback: bool = False,
    ignore_ring_gaps: bool = False,
    false_above_tail: bool = False,
) -> dict[str, float | str | None]:
    values = spectrum.frc()
    usable = [
        (radius, spectrum.frequencies[radius], float(values[radius]))
        for radius in range(1, values.size)
        if np.isfinite(values[radius])
    ]
    if len(usable) < 4:
        return {"outcome": "INSUFFICIENT", "frequency_or_bound": None}
    if usable[0][2] < THRESHOLD:
        return {
            "outcome": "CENSORED_BELOW",
            "frequency_or_bound": usable[0][1],
        }
    for index in range(1, len(usable) - 2):
        _, frequency0, value0 = usable[index - 1]
        _, frequency1, value1 = usable[index]
        consecutive = all(
            right[0] == left[0] + 1
            for left, right in zip(
                usable[index - 1 : index + 2],
                usable[index : index + 3],
            )
        )
        if (
            value0 >= THRESHOLD
            and all(value < THRESHOLD for _, _, value in usable[index : index + 3])
            and (ignore_ring_gaps or consecutive)
        ):
            delta = value0 - value1
            if abs(delta) > np.finfo(np.float64).eps:
                fraction = min(1.0, max(0.0, (value0 - THRESHOLD) / delta))
            else:
                fraction = 1.0
            return {
                "outcome": "MEASURED",
                "frequency_or_bound": frequency0
                + fraction * (frequency1 - frequency0),
            }
    _, last_frequency, last_value = usable[-1]
    if last_bin_fallback:
        return {"outcome": "MEASURED", "frequency_or_bound": last_frequency}
    if false_above_tail or last_value >= THRESHOLD:
        return {
            "outcome": "CENSORED_ABOVE",
            "frequency_or_bound": last_frequency,
        }
    return {"outcome": "INSUFFICIENT", "frequency_or_bound": None}


def quantile(values: Iterable[float], probability: float) -> float:
    values = np.sort(np.asarray(list(values), dtype=np.float64))
    if values.size == 0:
        return math.nan
    at = probability * (values.size - 1)
    low = int(math.floor(at))
    high = int(math.ceil(at))
    if low == high:
        return float(values[low])
    return float(values[low] * (high - at) + values[high] * (at - low))


def bootstrap_snr_max(
    tiles: list[Spectrum],
    *,
    resamples: int = 1_000,
    seed: int = 0xD8_22026,
) -> dict[str, object]:
    if not tiles:
        raise ValueError("bootstrap needs tiles")
    rng = np.random.default_rng(seed)
    values = []
    for _ in range(resamples):
        indices = rng.integers(0, len(tiles), size=len(tiles))
        spectrum = aggregate_spectra(tiles[index] for index in indices)
        values.append(max_midband_snr(spectrum))
    finite = [value for value in values if math.isfinite(value)]
    return {
        "resamples": resamples,
        "seed": seed,
        "finite": len(finite),
        "median": quantile(finite, 0.5),
        "interval_95": [quantile(finite, 0.025), quantile(finite, 0.975)],
    }


def bootstrap_crossing(
    tiles: list[Spectrum],
    *,
    resamples: int = 1_000,
    seed: int = 0xD8_22027,
) -> dict[str, object]:
    if not tiles:
        raise ValueError("bootstrap needs tiles")
    rng = np.random.default_rng(seed)
    outcomes: dict[str, int] = {}
    measured = []
    for _ in range(resamples):
        indices = rng.integers(0, len(tiles), size=len(tiles))
        result = classify(aggregate_spectra(tiles[index] for index in indices))
        outcome = str(result["outcome"])
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if outcome == "MEASURED":
            measured.append(float(result["frequency_or_bound"]))
    result: dict[str, object] = {
        "resamples": resamples,
        "seed": seed,
        "outcomes": outcomes,
        "measured_fraction": len(measured) / resamples,
    }
    if len(measured) >= 0.9 * resamples:
        result["median"] = quantile(measured, 0.5)
        result["interval_95"] = [
            quantile(measured, 0.025),
            quantile(measured, 0.975),
        ]
    return result


def spectrum_rows(spectrum: Spectrum) -> list[dict[str, float]]:
    frc = spectrum.frc()
    snr = spectrum.snr()
    return [
        {
            "radius": radius,
            "frequency": float(spectrum.frequencies[radius]),
            "count": float(spectrum.count[radius]),
            "cross": float(spectrum.cross[radius]),
            "power_a": float(spectrum.power_a[radius]),
            "power_b": float(spectrum.power_b[radius]),
            "noise": float(spectrum.noise[radius]),
            "frc": float(frc[radius]),
            "snr": float(snr[radius]),
        }
        for radius in range(1, spectrum.count.size)
        if np.isfinite(frc[radius]) or np.isfinite(snr[radius])
    ]


def unsharp(image: np.ndarray, amount: float = 1.5) -> np.ndarray:
    image = np.asarray(image, dtype=np.float64)
    blur = sum(
        np.roll(np.roll(image, dy, axis=0), dx, axis=1)
        for dy in (-1, 0, 1)
        for dx in (-1, 0, 1)
    ) / 9.0
    return image + amount * (image - blur)


def gradient_acuity(image: np.ndarray) -> float:
    image = np.asarray(image, dtype=np.float64)
    dx = image[1:-1, 2:] - image[1:-1, :-2]
    dy = image[2:, 1:-1] - image[:-2, 1:-1]
    return float(np.sqrt(np.mean(dx * dx + dy * dy)))


def integer_phase_shift(reference: np.ndarray, moving: np.ndarray) -> tuple[int, int]:
    if reference.shape != moving.shape or reference.ndim != 2:
        raise ValueError("phase correlation needs equal 2-D arrays")
    ref = np.asarray(reference, dtype=np.float64) - float(np.mean(reference))
    mov = np.asarray(moving, dtype=np.float64) - float(np.mean(moving))
    cross = np.fft.fft2(ref) * np.conj(np.fft.fft2(mov))
    magnitude = np.abs(cross)
    cross = np.divide(cross, magnitude, out=np.zeros_like(cross), where=magnitude > 0)
    correlation = np.fft.ifft2(cross).real
    peak = np.unravel_index(int(np.argmax(correlation)), correlation.shape)
    shift = []
    for coordinate, size in zip(peak, reference.shape):
        shift.append(int(coordinate if coordinate <= size // 2 else coordinate - size))
    return shift[0], shift[1]


def log_high_mid_ratio(image: np.ndarray) -> float:
    image = np.asarray(image, dtype=np.float64)
    if image.ndim != 2 or image.shape[0] != image.shape[1]:
        raise ValueError("focus proxy needs a square 2-D crop")
    n = image.shape[0]
    window = np.hanning(n)
    transformed = np.fft.rfft2(
        (image - float(np.mean(image))) * window[:, None] * window[None, :]
    )
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    frequency = np.hypot(fx, fy)
    power = np.abs(transformed) ** 2
    mid = float(np.mean(power[(frequency >= 0.05) & (frequency < 0.15)]))
    high = float(np.mean(power[(frequency >= 0.18) & (frequency < 0.35)]))
    return math.log(max(high, 1e-300) / max(mid, 1e-300))


def stability_readings(frames: list[np.ndarray]) -> dict[str, object]:
    if len(frames) < 2:
        raise ValueError("stability gate needs at least two frames")
    shifts = [integer_phase_shift(frames[0], frame) for frame in frames]
    ratios = [log_high_mid_ratio(frame) for frame in frames]
    median = float(np.median(ratios))
    maximum_deviation = max(abs(value - median) for value in ratios)
    return {
        "shifts": [list(shift) for shift in shifts],
        "log_high_mid_ratio": ratios,
        "median": median,
        "maximum_deviation": maximum_deviation,
    }


def stability_gate(frames: list[np.ndarray]) -> dict[str, object]:
    result = stability_readings(frames)
    shifts = [tuple(shift) for shift in result["shifts"]]
    maximum_deviation = float(result["maximum_deviation"])
    if any(shift != (0, 0) for shift in shifts):
        raise ValueError(f"nonzero integer phase shift: {shifts}")
    if maximum_deviation >= 0.10:
        raise ValueError(f"focus-proxy deviation {maximum_deviation:.6f} >=0.10")
    return result
