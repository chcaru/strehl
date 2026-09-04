"""Conservative output-only witness for a common post-render transfer.

This module deliberately does not score image quality.  It only asks whether
the realized difference between two registered linear-light images is almost
entirely predicted by one of two frozen low-complexity transfer families.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter


BORDER = 12
SAMPLE_STRIDE = 3
MACROTILE = 64
RIDGE = 1.0e-8

GAUSSIAN_SIGMAS = (0.20, 0.25, 0.30, 0.40, 0.60, 0.80, 1.00, 1.50, 2.00, 3.00)

MIN_DIFFERENCE_LSB = 0.50
MIN_KERNEL_EFFECT_LSB = 0.50
MIN_INFORMATIVE_TILES = 8
INFORMATIVE_TILE_LSB = 2.0
MAX_RESIDUAL_OVER_DIFFERENCE = 0.12
MAX_RESIDUAL_LSB = 0.75
MAX_TILE_Q90 = 0.25
MAX_FOLD_DISAGREEMENT = 0.20
METRIC_SENTINEL = 1.0e100


def _rms(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    maximum = float(np.max(np.abs(values)))
    if maximum == 0.0:
        return 0.0
    if not np.isfinite(maximum):
        return METRIC_SENTINEL
    scaled = values / maximum
    result = maximum * float(np.sqrt(np.mean(scaled * scaled)))
    return min(result, METRIC_SENTINEL)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= np.finfo(float).tiny:
        return METRIC_SENTINEL
    value = numerator / denominator
    return min(float(value), METRIC_SENTINEL) if np.isfinite(value) else METRIC_SENTINEL


def _finite_scalar(value: float) -> bool:
    return bool(np.isfinite(value))


def _diagnostic_scalar(value: float) -> float | None:
    return float(value) if np.isfinite(value) else None


def _d4_orbits(radius: int) -> list[tuple[tuple[int, int], ...]]:
    orbits: list[tuple[tuple[int, int], ...]] = []
    for major in range(1, radius + 1):
        for minor in range(0, major + 1):
            offsets: set[tuple[int, int]] = set()
            for y, x in ((major, minor), (minor, major)):
                for sy in (-1, 1):
                    for sx in (-1, 1):
                        offsets.add((sy * y, sx * x))
            orbits.append(tuple(sorted(offsets)))
    return orbits


def _sample_coordinates(shape: tuple[int, int]) -> tuple[np.ndarray, ...]:
    height, width = shape
    ys = np.arange(BORDER, height - BORDER, SAMPLE_STRIDE, dtype=np.int32)
    xs = np.arange(BORDER, width - BORDER, SAMPLE_STRIDE, dtype=np.int32)
    yy, xx = np.meshgrid(ys, xs, indexing="ij")
    y = yy.ravel()
    x = xx.ravel()
    tile_y = y // MACROTILE
    tile_x = x // MACROTILE
    fold = (tile_y + tile_x) & 1
    tile_id = tile_y.astype(np.int64) * 100000 + tile_x.astype(np.int64)
    return y, x, fold, tile_id


def _lsi_features(image: np.ndarray, y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, list[str]]:
    center = image[y, x]
    columns = [center]
    names = ["gain_delta"]
    for index, offsets in enumerate(_d4_orbits(3)):
        shifted = np.zeros_like(center)
        for dy, dx in offsets:
            shifted += image[y + dy, x + dx]
        columns.append(shifted / len(offsets) - center)
        names.append(f"orbit_r3_{index}")
    for sigma in GAUSSIAN_SIGMAS:
        blurred = gaussian_filter(image, sigma=sigma, mode="reflect", truncate=4.0)
        columns.append(blurred[y, x] - center)
        names.append(f"gaussian_{sigma:.2f}")
    return np.column_stack(columns), names


def _phase2_features(
    image: np.ndarray, y: np.ndarray, x: np.ndarray
) -> tuple[np.ndarray, list[str]]:
    center = image[y, x]
    base_columns = [center]
    base_names = ["gain_delta"]
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            if dy == 0 and dx == 0:
                continue
            base_columns.append(image[y + dy, x + dx] - center)
            base_names.append(f"shift_{dy:+d}_{dx:+d}")
    base = np.column_stack(base_columns)
    phase = ((y & 1) << 1) | (x & 1)
    features = np.zeros((y.size, base.shape[1] * 4), dtype=np.float64)
    names: list[str] = []
    width = base.shape[1]
    for phase_index in range(4):
        selected = phase == phase_index
        start = phase_index * width
        features[selected, start : start + width] = base[selected]
        names.extend(f"phase{phase_index}_{name}" for name in base_names)
    return features, names


@dataclass
class _FoldDesign:
    train: np.ndarray
    test: np.ndarray
    mean: np.ndarray
    scale: np.ndarray
    normalized_train: np.ndarray
    cholesky: np.ndarray

    @classmethod
    def build(cls, features: np.ndarray, train: np.ndarray, test: np.ndarray) -> "_FoldDesign":
        train_features = features[train]
        mean = np.mean(train_features, axis=0)
        scale = np.std(train_features, axis=0)
        scale = np.where(scale > 1.0e-12, scale, 1.0)
        normalized = (train_features - mean) / scale
        design = np.column_stack((np.ones(train_features.shape[0]), normalized))
        gram = design.T @ design
        gram[1:, 1:] += np.eye(features.shape[1]) * (RIDGE * train_features.shape[0])
        cholesky = np.linalg.cholesky(gram)
        return cls(train, test, mean, scale, normalized, cholesky)

    def fit(
        self, features: np.ndarray, target: np.ndarray
    ) -> tuple[float, np.ndarray, np.ndarray, np.ndarray]:
        train_target = target[self.train]
        rhs = np.empty(features.shape[1] + 1, dtype=np.float64)
        rhs[0] = float(np.sum(train_target))
        rhs[1:] = self.normalized_train.T @ train_target
        intermediate = np.linalg.solve(self.cholesky, rhs)
        standardized = np.linalg.solve(self.cholesky.T, intermediate)
        coefficients = standardized[1:] / self.scale
        intercept = float(standardized[0] - coefficients @ self.mean)
        kernel_prediction = features @ coefficients
        prediction = kernel_prediction + intercept
        return intercept, coefficients, prediction, kernel_prediction


class _PreparedFamily:
    def __init__(
        self,
        name: str,
        features: np.ndarray,
        feature_names: list[str],
        folds: np.ndarray,
        tile_ids: np.ndarray,
        quantization_step: float,
    ) -> None:
        self.name = name
        self.features = np.asarray(features, dtype=np.float64)
        self.feature_names = feature_names
        self.folds = folds
        self.tile_ids = tile_ids
        self.quantization_step = quantization_step
        self.designs = [
            _FoldDesign.build(
                self.features,
                train=np.flatnonzero(folds == train_fold),
                test=np.flatnonzero(folds != train_fold),
            )
            for train_fold in (0, 1)
        ]

    def evaluate(self, difference: np.ndarray) -> dict[str, Any]:
        held_prediction = np.empty_like(difference)
        held_kernel = np.empty_like(difference)
        all_predictions: list[np.ndarray] = []
        all_kernel_predictions: list[np.ndarray] = []
        fold_coefficients: list[np.ndarray] = []
        fold_intercepts: list[float] = []

        for design in self.designs:
            intercept, coefficients, prediction, kernel_prediction = design.fit(
                self.features, difference
            )
            held_prediction[design.test] = prediction[design.test]
            held_kernel[design.test] = kernel_prediction[design.test]
            all_predictions.append(prediction)
            all_kernel_predictions.append(kernel_prediction)
            fold_coefficients.append(coefficients)
            fold_intercepts.append(intercept)

        residual = difference - held_prediction
        difference_rms = _rms(difference)
        residual_rms = _rms(residual)
        relative = _safe_ratio(residual_rms, difference_rms)
        difference_rms_lsb = _safe_ratio(
            difference_rms, self.quantization_step
        )
        residual_rms_lsb = _safe_ratio(residual_rms, self.quantization_step)
        kernel_effect_rms_lsb = _safe_ratio(
            _rms(held_kernel), self.quantization_step
        )

        tile_ratios: list[float] = []
        for tile_id in np.unique(self.tile_ids):
            selected = self.tile_ids == tile_id
            tile_difference = _rms(difference[selected])
            if tile_difference < INFORMATIVE_TILE_LSB * self.quantization_step:
                continue
            tile_ratios.append(_safe_ratio(_rms(residual[selected]), tile_difference))

        average_kernel = 0.5 * (
            all_kernel_predictions[0] + all_kernel_predictions[1]
        )
        average_kernel_rms = _rms(average_kernel)
        fold_disagreement = _safe_ratio(
            _rms(all_kernel_predictions[0] - all_kernel_predictions[1]),
            average_kernel_rms,
        )
        tile_q90 = (
            float(np.quantile(tile_ratios, 0.90))
            if tile_ratios
            else METRIC_SENTINEL
        )

        checks = {
            "difference": difference_rms_lsb >= MIN_DIFFERENCE_LSB,
            "kernel_effect": kernel_effect_rms_lsb >= MIN_KERNEL_EFFECT_LSB,
            "informative_tiles": len(tile_ratios) >= MIN_INFORMATIVE_TILES,
            "relative_residual": relative <= MAX_RESIDUAL_OVER_DIFFERENCE,
            "absolute_residual": residual_rms_lsb <= MAX_RESIDUAL_LSB,
            "tile_q90": tile_q90 <= MAX_TILE_Q90,
            "fold_disagreement": fold_disagreement <= MAX_FOLD_DISAGREEMENT,
        }
        fired = all(checks.values())

        gain_indices = [
            index
            for index, feature_name in enumerate(self.feature_names)
            if feature_name.endswith("gain_delta")
        ]
        gain_by_fold = [
            [_diagnostic_scalar(coefficients[index]) for index in gain_indices]
            for coefficients in fold_coefficients
        ]

        return {
            "family": self.name,
            "fired": fired,
            "checks": checks,
            "parameter_count": len(self.feature_names),
            "difference_rms_lsb": difference_rms_lsb,
            "kernel_effect_rms_lsb": kernel_effect_rms_lsb,
            "residual_rms_lsb": residual_rms_lsb,
            "residual_over_difference": relative,
            "informative_tiles": len(tile_ratios),
            "tile_q90": tile_q90,
            "fold_disagreement": fold_disagreement,
            "intercepts_lsb": [
                _diagnostic_scalar(
                    _safe_ratio(abs(float(value)), self.quantization_step)
                    * (-1.0 if value < 0.0 else 1.0)
                )
                for value in fold_intercepts
            ],
            "gain_delta_by_fold": gain_by_fold,
        }


class _InvalidPreparedVeto:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def evaluate(self, _: np.ndarray) -> dict[str, Any]:
        return {
            "status": "INSTRUMENT_INVALID",
            "fired": False,
            "reason": self.reason,
        }


class PreparedTransferVeto:
    def __init__(self, image_a: np.ndarray, quantization_step: float) -> None:
        image = np.asarray(image_a, dtype=np.float64)
        if image.ndim != 2:
            raise ValueError("A must be one two-dimensional linear-light plane")
        if min(image.shape) < 256:
            raise ValueError("each image dimension must be at least 256 pixels")
        if not np.all(np.isfinite(image)):
            raise ValueError("A contains non-finite samples")
        if not _finite_scalar(quantization_step) or quantization_step <= 0.0:
            raise ValueError("quantization_step must be finite and positive")

        self.image = image
        self.quantization_step = float(quantization_step)
        self.y, self.x, folds, tile_ids = _sample_coordinates(image.shape)
        lsi, lsi_names = _lsi_features(image, self.y, self.x)
        phase2, phase2_names = _phase2_features(image, self.y, self.x)
        self.families = [
            _PreparedFamily(
                "smooth-zero-phase-lsi",
                lsi,
                lsi_names,
                folds,
                tile_ids,
                self.quantization_step,
            ),
            _PreparedFamily(
                "period-2-resampling",
                phase2,
                phase2_names,
                folds,
                tile_ids,
                self.quantization_step,
            ),
        ]

    def evaluate(self, image_b: np.ndarray) -> dict[str, Any]:
        try:
            other = np.asarray(image_b, dtype=np.float64)
            if other.shape != self.image.shape:
                raise ValueError("A and B shapes differ")
            if not np.all(np.isfinite(other)):
                raise ValueError("B contains non-finite samples")
            sampled_difference = other[self.y, self.x] - self.image[self.y, self.x]
            difference_rms_lsb = _safe_ratio(
                _rms(sampled_difference), self.quantization_step
            )
            if difference_rms_lsb < MIN_DIFFERENCE_LSB:
                return {
                    "status": "IDENTITY_EQUIVALENT",
                    "fired": False,
                    "difference_rms_lsb": difference_rms_lsb,
                    "threshold_lsb": MIN_DIFFERENCE_LSB,
                }

            family_results = [
                family.evaluate(sampled_difference) for family in self.families
            ]
            selected = min(
                family_results,
                key=lambda result: (
                    result["residual_rms_lsb"],
                    result["residual_over_difference"],
                    result["parameter_count"],
                ),
            )
            fired = any(result["fired"] for result in family_results)
            firing_families = [
                result["family"] for result in family_results if result["fired"]
            ]
            return {
                "status": (
                    "INADMISSIBLE_COMMON_TRANSFER" if fired else "NOT_VETOED"
                ),
                "fired": fired,
                "difference_rms_lsb": difference_rms_lsb,
                "selected_family": selected["family"],
                "firing_families": firing_families,
                "families": family_results,
            }
        except Exception as error:
            return {
                "status": "INSTRUMENT_INVALID",
                "fired": False,
                "reason": f"{type(error).__name__}: {error}",
            }


def prepare_transfer_veto(
    image_a: np.ndarray, quantization_step: float
) -> PreparedTransferVeto | _InvalidPreparedVeto:
    try:
        return PreparedTransferVeto(image_a, quantization_step)
    except Exception as error:
        return _InvalidPreparedVeto(f"{type(error).__name__}: {error}")


def evaluate_transfer_veto(
    image_a: np.ndarray, image_b: np.ndarray, quantization_step: float
) -> dict[str, Any]:
    return prepare_transfer_veto(image_a, quantization_step).evaluate(image_b)


def _load_plane(path: Path) -> tuple[np.ndarray, float]:
    import tifffile

    image = tifffile.imread(path)
    if image.ndim == 3:
        image = image[:, :, 1]
    if image.ndim != 2:
        raise ValueError(f"{path} is not a scalar or RGB image")
    if np.issubdtype(image.dtype, np.integer):
        maximum = float(np.iinfo(image.dtype).max)
        return image.astype(np.float64) / maximum, 1.0 / maximum
    raise ValueError("CLI inputs must be integer linear-light TIFFs")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--out", type=Path)
    arguments = parser.parse_args()
    try:
        image_a, quantization_a = _load_plane(arguments.a)
        image_b, quantization_b = _load_plane(arguments.b)
        if quantization_a != quantization_b:
            raise ValueError("A and B quantization steps differ")
        result = evaluate_transfer_veto(image_a, image_b, quantization_a)
    except Exception as error:
        result = {
            "status": "INSTRUMENT_INVALID",
            "fired": False,
            "reason": f"{type(error).__name__}: {error}",
        }
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
    if arguments.out is not None:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 2 if result["status"] == "INSTRUMENT_INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
