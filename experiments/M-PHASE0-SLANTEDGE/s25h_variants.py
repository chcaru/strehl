"""Preregistered S25-hardening candidates.

This module owns candidate computation only.  It imports no fixture generator,
arm labels, expected score ratios or acceptance checker.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter

from vendor_m1 import frequency_grid, m1_tile, window_2d


VARIANT_SPECS: dict[str, dict[str, Any]] = {
    "C0_NATIVE_MIN": {
        "score": "MIN",
        "floor": False,
        "eligibility": False,
        "ramp": False,
        "angle_gate": False,
    },
    "V1_FLOOR_ELIG_MIN": {
        "score": "MIN",
        "floor": True,
        "eligibility": True,
        "ramp": False,
        "angle_gate": False,
    },
    "V2_GES_OLS": {
        "score": "OLS",
        "floor": True,
        "eligibility": True,
        "ramp": False,
        "angle_gate": False,
    },
    "V3_RAMP_GES_OLS": {
        "score": "OLS",
        "floor": True,
        "eligibility": True,
        "ramp": True,
        "angle_gate": False,
    },
    "V4_RAMP_GES_OLS_ANGLE": {
        "score": "OLS",
        "floor": True,
        "eligibility": True,
        "ramp": True,
        "angle_gate": True,
    },
    "V5_RAMP_GES_TS_ANGLE": {
        "score": "TS",
        "floor": True,
        "eligibility": True,
        "ramp": True,
        "angle_gate": True,
    },
}

BOOTSTRAP_SEED = 2026095000
BOOTSTRAP_DRAWS = 10_000
MIN_VALID_SITES = 58
ANGLE_MIN = 2.0
ANGLE_MAX = 10.0


def _spectra(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float64)
    window = window_2d(image.shape[0])
    centered = (image - float(np.mean(image))) * window
    return np.fft.rfft2(centered)


def _bin_masks(shape: tuple[int, int]) -> list[np.ndarray]:
    frequency = frequency_grid(shape)
    return [
        (frequency >= 0.15 + 0.01 * index)
        & (frequency < 0.16 + 0.01 * index)
        for index in range(10)
    ]


def noise_calibration(
    pairs: Iterable[tuple[np.ndarray, np.ndarray]],
) -> dict[str, object]:
    rows = []
    masks = _bin_masks((256, 256))
    for a, b in pairs:
        difference = _spectra(a) - _spectra(b)
        rows.append([
            0.5 * float(np.sum(np.abs(difference[mask]) ** 2))
            for mask in masks
        ])
    values = np.asarray(rows, dtype=np.float64)
    if values.shape != (128, 10):
        raise ValueError(f"expected 128x10 calibration, got {values.shape}")
    return {
        "pairs": int(values.shape[0]),
        "median": np.median(values, axis=0).tolist(),
        "p95_higher": np.quantile(
            values,
            0.95,
            axis=0,
            method="higher",
        ).tolist(),
    }


def _band_powers(image: np.ndarray) -> np.ndarray:
    transformed = _spectra(image)
    return np.asarray([
        float(np.sum(np.abs(transformed[mask]) ** 2))
        for mask in _bin_masks(image.shape)
    ])


def eligibility_from_power_rows(
    focused: np.ndarray,
    defocused: np.ndarray,
) -> dict[str, object]:
    focused = np.asarray(focused, dtype=np.float64)
    defocused = np.asarray(defocused, dtype=np.float64)
    if focused.shape != (64, 5) or defocused.shape != (64, 5):
        raise ValueError("eligibility power rows must be 64x5")

    point = np.full(5, -math.inf, dtype=np.float64)
    focused_sum = np.sum(focused, axis=0)
    defocused_sum = np.sum(defocused, axis=0)
    valid_point = (focused_sum > 0.0) & (defocused_sum > 0.0)
    point[valid_point] = (
        focused_sum[valid_point] / defocused_sum[valid_point]
    )

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(
        0,
        focused.shape[0],
        size=(BOOTSTRAP_DRAWS, focused.shape[0]),
    )
    lower = []
    for index in range(5):
        numerator = np.sum(focused[indices, index], axis=1)
        denominator = np.sum(defocused[indices, index], axis=1)
        ratios = np.full(BOOTSTRAP_DRAWS, -math.inf, dtype=np.float64)
        valid = (numerator > 0.0) & (denominator > 0.0)
        ratios[valid] = numerator[valid] / denominator[valid]
        lower.append(float(np.sort(ratios)[499]))

    rows = []
    for index in range(5):
        point_value = (
            float(point[index])
            if math.isfinite(float(point[index])) else None
        )
        lower_value = (
            lower[index] if math.isfinite(lower[index]) else None
        )
        rows.append({
            "low": 0.20 + 0.01 * index,
            "high": 0.21 + 0.01 * index,
            "point_ratio": point_value,
            "lcb95": lower_value,
            "pass": bool(
                point_value is not None
                and lower_value is not None
                and point_value >= 2.0
                and lower_value >= 1.5
            ),
        })
    return {
        "rows": rows,
        "point_pass": all(
            row["point_ratio"] is not None
            and row["point_ratio"] >= 2.0
            for row in rows
        ),
        "lcb_pass": all(
            row["lcb95"] is not None
            and row["lcb95"] >= 1.5
            for row in rows
        ),
        "pass": all(row["pass"] for row in rows),
    }


def eligibility_from_sites(
    sites: Iterable[tuple[np.ndarray, np.ndarray]],
    calibration: dict[str, object],
) -> dict[str, object]:
    noise = np.asarray(calibration["median"], dtype=np.float64)[5:10]
    focused_rows = []
    defocused_rows = []
    for focused, defocused in sites:
        focused_rows.append(_band_powers(focused)[5:10] - noise)
        defocused_rows.append(_band_powers(defocused)[5:10] - noise)
    return eligibility_from_power_rows(
        np.asarray(focused_rows),
        np.asarray(defocused_rows),
    )


def fit_linearizer(
    nominal_ramp: np.ndarray,
    observed_ramp: np.ndarray,
) -> PchipInterpolator:
    nominal = np.asarray(nominal_ramp, dtype=np.float64)
    observed = np.asarray(observed_ramp, dtype=np.float64)
    if nominal.shape != (8, 33) or observed.shape != (8, 33):
        raise ValueError("tone witness must be eight copies of 33 steps")
    target = np.median(nominal, axis=0)
    measured = np.median(observed, axis=0)
    if (
        not np.all(np.isfinite(target))
        or not np.all(np.isfinite(measured))
        or not np.all(np.diff(target) > 0.0)
        or not np.all(np.diff(measured) > 0.0)
    ):
        raise ValueError("tone witness is not finite and strictly monotone")
    return PchipInterpolator(measured, target, extrapolate=False)


def _linearize_sites(
    sites: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    nominal_ramp: np.ndarray,
    observed_ramp: np.ndarray,
) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    inverse = fit_linearizer(nominal_ramp, observed_ramp)
    output = []
    for triplet in sites:
        transformed = tuple(
            np.asarray(inverse(image), dtype=np.float64)
            for image in triplet
        )
        if not all(np.all(np.isfinite(image)) for image in transformed):
            raise ValueError("scored pixels are outside the tone witness")
        output.append(transformed)
    return output


def reference_angle_deg(
    sites: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> float:
    reference = np.mean(
        np.stack([row[2] for row in sites], axis=0),
        axis=0,
    )
    smoothed = gaussian_filter(
        reference,
        1.0,
        mode="nearest",
        truncate=6.0,
    )
    gradient_y, gradient_x = np.gradient(smoothed)
    crop = np.s_[16:240, 16:240]
    gx = gradient_x[crop]
    gy = gradient_y[crop]
    jxx = float(np.sum(gx * gx))
    jyy = float(np.sum(gy * gy))
    jxy = float(np.sum(gx * gy))
    direction = 0.5 * math.degrees(math.atan2(
        2.0 * jxy,
        jxx - jyy,
    ))
    direction = abs(((direction + 90.0) % 180.0) - 90.0)
    return min(direction, 90.0 - direction)


def _slope_ols(x: np.ndarray, y: np.ndarray) -> float:
    design = np.column_stack([x, np.ones_like(x)])
    return float(np.linalg.lstsq(design, y, rcond=None)[0][0])


def _slope_theil_sen(x: np.ndarray, y: np.ndarray) -> float:
    slopes = [
        float((y[j] - y[i]) / (x[j] - x[i]))
        for i in range(len(x))
        for j in range(i + 1, len(x))
    ]
    return float(np.median(np.asarray(slopes, dtype=np.float64)))


def _refusal(
    reason: str,
    *,
    angle_deg: float | None = None,
) -> dict[str, object]:
    output: dict[str, object] = {
        "status": "REFUSED",
        "reason": reason,
    }
    if angle_deg is not None:
        output["angle_deg"] = angle_deg
    return output


def evaluate(
    variant_id: str,
    sites: list[tuple[np.ndarray, np.ndarray, np.ndarray]],
    calibration: dict[str, object],
    eligibility: dict[str, object],
    nominal_ramp: np.ndarray,
    observed_ramp: np.ndarray,
) -> dict[str, object]:
    spec = VARIANT_SPECS[variant_id]
    try:
        prepared = (
            _linearize_sites(sites, nominal_ramp, observed_ramp)
            if spec["ramp"] else sites
        )
    except ValueError as exc:
        return _refusal(f"TONE_CALIBRATION: {exc}")

    angle = reference_angle_deg(prepared)
    refusal_reasons = []
    if spec["eligibility"] and not eligibility.get("pass"):
        refusal_reasons.append("SOURCE_INELIGIBLE")
    if spec["angle_gate"] and not ANGLE_MIN <= angle <= ANGLE_MAX:
        refusal_reasons.append("ANGLE_OUT_OF_RANGE")

    floors = (
        [float(value) for value in calibration["p95_higher"]]
        if spec["floor"] else None
    )
    rows = [
        m1_tile(a, b, reference, noise_floor=floors)
        for a, b, reference in prepared
    ]

    if floors is None:
        activation_fraction = 0.0
    else:
        active = sum(
            math.isclose(
                float(row["bins"][index]["noise"]),
                floors[index],
                rel_tol=0.0,
                abs_tol=0.0,
            )
            for row in rows
            for index in range(10)
        )
        activation_fraction = active / (len(rows) * 10)

    bin_medians = []
    for index in range(10):
        bin_medians.append({
            key: float(np.median([
                float(row["bins"][index][key])
                for row in rows
            ]))
            for key in ("low", "high", "gain", "noise", "D", "FRC")
        })

    if spec["score"] == "MIN":
        score = float(np.median([
            float(row["S_25"])
            for row in rows
        ]))
        metric_name = "native_S_25"
        slope = None
    else:
        log_d = []
        valid_counts = []
        for index in range(5, 10):
            values = np.asarray([
                float(row["bins"][index]["D"])
                for row in rows
            ])
            valid = np.isfinite(values) & (values > 0.0)
            valid_counts.append(int(np.sum(valid)))
            if int(np.sum(valid)) < MIN_VALID_SITES:
                return _refusal(
                    f"INSUFFICIENT_D_BIN_{index}",
                    angle_deg=angle,
                )
            log_d.append(float(np.median(np.log(values[valid]))))
        centers = np.arange(0.205, 0.250, 0.01, dtype=np.float64)
        x = centers * centers
        floor_profile = np.asarray(
            calibration["p95_higher"],
            dtype=np.float64,
        )[5:10]
        y = (
            np.asarray(log_d)
            + np.log(floor_profile)
            + 2.0 * np.log(centers)
        )
        slope = (
            _slope_ols(x, y)
            if spec["score"] == "OLS"
            else _slope_theil_sen(x, y)
        )
        if not math.isfinite(slope) or slope >= 0.0:
            return _refusal("NONNEGATIVE_GES_SLOPE", angle_deg=angle)
        score = 2.0 * math.pi / math.sqrt(-slope)
        metric_name = "comparative_inverse_pixel_scale"

    if not math.isfinite(score) or score <= 0.0:
        return _refusal("NONPOSITIVE_SCORE", angle_deg=angle)
    output = {
        "status": "REFUSED" if refusal_reasons else "VALUE",
        "metric_name": metric_name,
        "angle_deg": angle,
        "floor_activation_fraction": activation_fraction,
        "slope": slope,
        "bin_medians": bin_medians,
    }
    if refusal_reasons:
        output["reason"] = "+".join(refusal_reasons)
        output["diagnostic_value"] = score
    else:
        output["value"] = score
    return output
