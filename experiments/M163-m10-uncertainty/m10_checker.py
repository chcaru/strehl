from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np


Z95 = 1.959963984540054
MIN_TARGET_PIXELS = 10_000
COVERAGE_RANGE = (0.93, 0.97)
VARIANCE_RATIO_RANGE = (0.90, 1.10)
DECILE_COUNT = 10
MIN_PASSING_DECILES = 9
MEDIAN_HALF_WIDTH_MAX = 0.5
P95_HALF_WIDTH_MAX = 1.0

VALUE_BARS = {
    "valid_fraction": (">=", 0.99),
    "rank_correlation": (">=", 0.99),
    "median_abs_error_steps": ("<=", 0.5),
    "p95_abs_error_steps": ("<=", 1.0),
    "ruler_slope_error_fraction": ("<=", 0.05),
    "flat_null_p95_range_steps": ("<=", 0.5),
    "synthetic_layer_confusion_fraction": ("<=", 0.01),
}


@dataclass(frozen=True)
class UncertaintyInput:
    residual_steps: np.ndarray
    candidate_sigma_steps: np.ndarray
    truth_sigma_steps: np.ndarray
    valid: np.ndarray


def _finite_float(value: float) -> float | None:
    return float(value) if math.isfinite(float(value)) else None


def _value_passes(name: str, value: float) -> bool:
    direction, bar = VALUE_BARS[name]
    if not math.isfinite(float(value)):
        return False
    if direction == ">=":
        return float(value) >= bar
    return float(value) <= bar


def score_value_metrics(metrics: dict[str, float]) -> dict[str, Any]:
    missing = sorted(set(VALUE_BARS) - set(metrics))
    components = {
        name: _value_passes(name, metrics[name])
        for name in VALUE_BARS
        if name in metrics
    }
    return {
        "metrics": {name: float(metrics[name]) for name in VALUE_BARS if name in metrics},
        "bars": VALUE_BARS,
        "missing": missing,
        "components": components,
        "pass": not missing and all(components.values()),
    }


def score_legacy(
    value_metrics: dict[str, float],
    reported_uncertainty: object,
) -> dict[str, Any]:
    """Executable transcription of the registered M10 success clause.

    `reported_uncertainty` is deliberately not inspected. That is the omission
    under test, not the repaired implementation.
    """
    value = score_value_metrics(value_metrics)
    return {
        "value": value,
        "pass": value["pass"],
        "uncertainty_quantities": {},
    }


def _gaussian_crps(errors: np.ndarray, sigma: np.ndarray) -> float:
    values = np.empty(errors.size, dtype=np.float64)
    positive = sigma > 0
    values[~positive] = np.abs(errors[~positive])
    if np.any(positive):
        z = errors[positive] / sigma[positive]
        phi = np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        cdf = np.fromiter(
            (0.5 * (1.0 + math.erf(float(v) / math.sqrt(2.0))) for v in z),
            dtype=np.float64,
            count=z.size,
        )
        values[positive] = sigma[positive] * (
            z * (2.0 * cdf - 1.0) + 2.0 * phi - 1.0 / math.sqrt(math.pi)
        )
    return float(np.mean(values))


def score_uncertainty(data: UncertaintyInput) -> dict[str, Any]:
    residual = np.asarray(data.residual_steps, dtype=np.float64).reshape(-1)
    candidate_sigma = np.asarray(
        data.candidate_sigma_steps, dtype=np.float64
    ).reshape(-1)
    truth_sigma = np.asarray(data.truth_sigma_steps, dtype=np.float64).reshape(-1)
    valid = np.asarray(data.valid, dtype=bool).reshape(-1)

    shapes_match = (
        residual.size == candidate_sigma.size == truth_sigma.size == valid.size
    )
    if not shapes_match:
        return {
            "population": int(valid.size),
            "valid_target_pixels": int(np.count_nonzero(valid)),
            "metrics": {},
            "components": {"shapes_match": False},
            "pass": False,
        }

    target_count = int(np.count_nonzero(valid))
    if target_count == 0:
        return {
            "population": int(valid.size),
            "valid_target_pixels": 0,
            "metrics": {},
            "components": {
                "shapes_match": True,
                "minimum_population": False,
                "reported_sigma_complete": False,
                "truth_sigma_complete": False,
                "coverage": False,
                "decile_calibration": False,
                "median_width": False,
                "p95_width": False,
            },
            "pass": False,
        }

    e = residual[valid]
    s_candidate = candidate_sigma[valid]
    s_truth = truth_sigma[valid]
    residual_ok = np.isfinite(e)
    candidate_ok = np.isfinite(s_candidate) & (s_candidate >= 0)
    truth_ok = np.isfinite(s_truth) & (s_truth >= 0)
    residual_fraction = float(np.mean(residual_ok))
    reported_fraction = float(np.mean(candidate_ok))
    truth_fraction = float(np.mean(truth_ok))

    usable = residual_ok & candidate_ok & truth_ok
    calibration_count = int(np.count_nonzero(usable))
    if not np.any(usable):
        return {
            "population": int(valid.size),
            "valid_target_pixels": target_count,
            "calibration_pixels": calibration_count,
            "metrics": {
                "residual_fraction": residual_fraction,
                "reported_sigma_fraction": reported_fraction,
                "truth_sigma_fraction": truth_fraction,
                "interval_coverage_95": None,
                "deciles_within_variance_ratio_bar": 0,
                "median_reported_95_half_width_steps": None,
                "p95_reported_95_half_width_steps": None,
                "mean_gaussian_crps_steps": None,
            },
            "components": {
                "shapes_match": True,
                "minimum_population": False,
                "residual_complete": residual_fraction == 1.0,
                "reported_sigma_complete": reported_fraction == 1.0,
                "truth_sigma_complete": truth_fraction == 1.0,
                "coverage": False,
                "decile_calibration": False,
                "median_width": False,
                "p95_width": False,
            },
            "pass": False,
        }

    e = e[usable]
    s_candidate = s_candidate[usable]
    s_truth = s_truth[usable]
    e = e - float(np.mean(e))
    combined = np.hypot(s_candidate, s_truth)
    abs_e = np.abs(e)
    covered = np.where(combined > 0, abs_e <= Z95 * combined, abs_e == 0)
    coverage = float(np.mean(covered))
    exact_zero_uncertainty = bool(
        np.all(abs_e == 0.0)
        and np.all(s_candidate == 0.0)
        and np.all(s_truth == 0.0)
    )

    order = np.argsort(s_candidate, kind="stable")
    decile_ratios: list[float | None] = []
    for indices in np.array_split(order, DECILE_COUNT):
        empirical = float(np.mean(e[indices] ** 2))
        predicted = float(np.mean(combined[indices] ** 2))
        if predicted == 0.0:
            ratio = 1.0 if empirical == 0.0 else None
        else:
            ratio = empirical / predicted
        decile_ratios.append(_finite_float(ratio) if ratio is not None else None)
    passing_deciles = sum(
        ratio is not None
        and VARIANCE_RATIO_RANGE[0] <= ratio <= VARIANCE_RATIO_RANGE[1]
        for ratio in decile_ratios
    )

    half_widths = Z95 * s_candidate
    median_width = float(np.median(half_widths))
    p95_width = float(np.quantile(half_widths, 0.95))
    crps = _gaussian_crps(e, combined)

    components = {
        "shapes_match": True,
        "minimum_population": calibration_count >= MIN_TARGET_PIXELS,
        "residual_complete": residual_fraction == 1.0,
        "reported_sigma_complete": reported_fraction == 1.0,
        "truth_sigma_complete": truth_fraction == 1.0,
        "coverage": exact_zero_uncertainty
        or COVERAGE_RANGE[0] <= coverage <= COVERAGE_RANGE[1],
        "decile_calibration": passing_deciles >= MIN_PASSING_DECILES,
        "median_width": median_width <= MEDIAN_HALF_WIDTH_MAX,
        "p95_width": p95_width <= P95_HALF_WIDTH_MAX,
    }
    return {
        "population": int(valid.size),
        "valid_target_pixels": target_count,
        "calibration_pixels": calibration_count,
        "metrics": {
            "residual_fraction": residual_fraction,
            "reported_sigma_fraction": reported_fraction,
            "truth_sigma_fraction": truth_fraction,
            "interval_coverage_95": coverage,
            "exact_zero_error_zero_uncertainty": exact_zero_uncertainty,
            "decile_variance_ratios": decile_ratios,
            "deciles_within_variance_ratio_bar": passing_deciles,
            "median_reported_95_half_width_steps": median_width,
            "p95_reported_95_half_width_steps": p95_width,
            "mean_gaussian_crps_steps": crps,
        },
        "components": components,
        "pass": all(components.values()),
    }


def score_repaired(
    value_metrics: dict[str, float],
    uncertainty: UncertaintyInput,
) -> dict[str, Any]:
    value = score_value_metrics(value_metrics)
    uncertainty_result = score_uncertainty(uncertainty)
    return {
        "value": value,
        "uncertainty": uncertainty_result,
        "pass": value["pass"] and uncertainty_result["pass"],
    }
