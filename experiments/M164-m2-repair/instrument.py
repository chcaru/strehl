"""Fail-closed candidate implementation for M2 equivalent-input noise."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


MIN_SITES = 64
MIN_REFERENCE_COHERENCE = 0.50
MAX_REFERENCE_CONDITION = 100.0
MAX_CLIP_FRACTION = 0.001
MIN_EFFECTIVE_BITS = 12
MAX_CALIBRATION_CORRELATION = 0.05
NO_CLAIM_FLOOR_BITS = 0.10
PERMUTATION_COUNT = 32
MAX_FLAT_INFORMATION_RATIO = 0.10
MAX_FLAT_REFERENCE_POWER_RATIO = 0.25
MAX_FLAT_OUTPUT_POWER_RATIO = 0.10
M2_BAND = (0.15, 0.35)


@dataclass(frozen=True)
class Admission:
    m1_admitted: bool
    linear_input_valid: bool
    pattern_map_valid: bool
    tone_witness_valid: bool
    independent_repeats: bool
    complete_m2_band: bool
    clip_fraction: float | None
    effective_bits: int | None
    calibration_correlation: float | None
    target_lineage: str


@dataclass(frozen=True)
class ArmInputs:
    reference_a: np.ndarray
    reference_b: np.ndarray
    detail_output_a: np.ndarray
    detail_output_b: np.ndarray
    flat_reference_a: np.ndarray
    flat_reference_b: np.ndarray
    flat_output_a: np.ndarray
    flat_output_b: np.ndarray
    frequencies: np.ndarray
    admission: Admission


def _complex_cov(a: np.ndarray, b: np.ndarray) -> complex:
    ac = a - np.mean(a)
    bc = b - np.mean(b)
    return np.mean(ac * np.conj(bc))


def _complex_variance(a: np.ndarray) -> float:
    return float(np.real(_complex_cov(a, a)))


def _coherence(a: np.ndarray, b: np.ndarray) -> float:
    va = _complex_variance(a)
    vb = _complex_variance(b)
    if va <= 0.0 or vb <= 0.0:
        return 0.0
    return float(abs(_complex_cov(a, b)) / np.sqrt(va * vb))


def _raw_information_bits(output: np.ndarray, reference: np.ndarray) -> float:
    vo = _complex_variance(output)
    vr = _complex_variance(reference)
    if vo <= 0.0 or vr <= 0.0:
        return 0.0
    rho2 = float(abs(_complex_cov(output, reference)) ** 2 / (vo * vr))
    rho2 = min(max(rho2, 0.0), 1.0 - 1e-15)
    return float(-np.log2(1.0 - rho2))


def _permutations(site_count: int) -> list[np.ndarray]:
    rng = np.random.default_rng(202_609_135 + site_count)
    identity = np.arange(site_count)
    result: list[np.ndarray] = []
    while len(result) < PERMUTATION_COUNT:
        candidate = rng.permutation(site_count)
        if np.any(candidate == identity):
            continue
        if any(np.array_equal(candidate, existing) for existing in result):
            continue
        result.append(candidate)
    return result


def _corrected_information(
    output: np.ndarray,
    reference: np.ndarray,
    permutations: list[np.ndarray],
) -> float:
    observed = _raw_information_bits(output, reference)
    nulls = np.asarray(
        [_raw_information_bits(output, reference[p]) for p in permutations]
    )
    floor = float(np.quantile(nulls, 0.95, method="higher"))
    return max(0.0, observed - floor)


def _information_summary(
    reference_a: np.ndarray,
    reference_b: np.ndarray,
    output_a: np.ndarray,
    output_b: np.ndarray,
) -> float:
    permutations = _permutations(reference_a.shape[0])
    pair_scores = []
    for output in (output_a, output_b):
        for reference in (reference_a, reference_b):
            cells = [
                _corrected_information(
                    output[:, cell],
                    reference[:, cell],
                    permutations,
                )
                for cell in range(reference.shape[1])
            ]
            pair_scores.append(float(np.mean(cells)))
    return float(min(pair_scores))


def _repeatable_power(first: np.ndarray, second: np.ndarray) -> float:
    cells = [
        max(0.0, float(np.real(_complex_cov(first[:, cell], second[:, cell]))))
        for cell in range(first.shape[1])
    ]
    return float(np.mean(cells))


def _arrays(inputs: ArmInputs) -> tuple[np.ndarray, ...]:
    return (
        inputs.reference_a,
        inputs.reference_b,
        inputs.detail_output_a,
        inputs.detail_output_b,
        inputs.flat_reference_a,
        inputs.flat_reference_b,
        inputs.flat_output_a,
        inputs.flat_output_b,
    )


def _validate(inputs: ArmInputs) -> tuple[str, dict[str, Any]]:
    arrays = _arrays(inputs)
    if any(not isinstance(array, np.ndarray) or array.ndim != 2 for array in arrays):
        return "INVALID_SHAPE", {}
    if len({array.shape for array in arrays}) != 1:
        return "INVALID_SHAPE", {}
    sites, cells = arrays[0].shape
    frequencies = np.asarray(inputs.frequencies)
    if frequencies.shape != (cells,):
        return "INVALID_FREQUENCIES", {"cells": cells}
    if sites < MIN_SITES:
        return "INSUFFICIENT_SITES", {"sites": sites, "minimum": MIN_SITES}
    if not all(np.all(np.isfinite(array)) for array in arrays):
        return "NONFINITE", {}
    if not np.all(np.isfinite(frequencies)):
        return "INVALID_FREQUENCIES", {}
    if np.any(frequencies < M2_BAND[0]) or np.any(frequencies > M2_BAND[1]):
        return "OUT_OF_BAND", {"minimum": float(np.min(frequencies)), "maximum": float(np.max(frequencies))}

    admission = inputs.admission
    if not admission.m1_admitted:
        return "M1_REQUIRED", {}
    if not admission.linear_input_valid:
        return "COMMON_INPUT_REQUIRED", {}
    if not admission.pattern_map_valid:
        return "PATTERN_MAP_REQUIRED", {}
    if not admission.tone_witness_valid:
        return "TONE_WITNESS_REQUIRED", {}
    if not admission.independent_repeats:
        return "INDEPENDENT_REPEATS_REQUIRED", {}
    if not admission.complete_m2_band:
        return "INCOMPLETE_M2_BAND", {}
    if (
        admission.clip_fraction is None
        or admission.effective_bits is None
        or admission.calibration_correlation is None
    ):
        return "MISSING_LINEAGE", {}
    if admission.clip_fraction > MAX_CLIP_FRACTION:
        return "NONLINEAR_OUTPUT", {"clip_fraction": admission.clip_fraction}
    if admission.effective_bits < MIN_EFFECTIVE_BITS:
        return "LOW_BIT_DEPTH", {"effective_bits": admission.effective_bits}
    if abs(admission.calibration_correlation) > MAX_CALIBRATION_CORRELATION:
        return "SHARED_REFERENCE", {
            "calibration_correlation": admission.calibration_correlation
        }
    if admission.target_lineage != "nonperiodic-random":
        return "PREDICTABLE_TARGET", {
            "target_lineage": admission.target_lineage
        }

    coherences = np.asarray(
        [
            _coherence(
                inputs.reference_a[:, cell],
                inputs.reference_b[:, cell],
            )
            for cell in range(cells)
        ]
    )
    if float(np.min(coherences)) < MIN_REFERENCE_COHERENCE:
        return "NO_DETAIL", {
            "minimum_reference_coherence": float(np.min(coherences))
        }

    reference_mean = (inputs.reference_a + inputs.reference_b) / 2.0
    features = np.concatenate(
        [reference_mean.real, reference_mean.imag], axis=1
    )
    feature_sd = np.std(features, axis=0, ddof=1)
    real_features = features[:, feature_sd > np.finfo(float).eps]
    if real_features.shape[1] == 0:
        return "ILL_CONDITIONED_REFERENCE", {
            "rank": 0,
            "dimension": 0,
            "condition": float("inf"),
        }
    covariance = np.atleast_2d(np.cov(real_features, rowvar=False, ddof=1))
    rank = int(np.linalg.matrix_rank(covariance))
    condition = float(np.linalg.cond(covariance))
    if rank < covariance.shape[0] or condition > MAX_REFERENCE_CONDITION:
        return "ILL_CONDITIONED_REFERENCE", {
            "rank": rank,
            "dimension": int(covariance.shape[0]),
            "condition": condition,
        }

    return "ELIGIBLE", {
        "sites": sites,
        "cells": cells,
        "minimum_reference_coherence": float(np.min(coherences)),
        "median_reference_coherence": float(np.median(coherences)),
        "reference_condition": condition,
    }


def evaluate_arm(inputs: ArmInputs) -> dict[str, Any]:
    status, diagnostics = _validate(inputs)
    if status != "ELIGIBLE":
        return {"status": status, "diagnostics": diagnostics}

    detail_information = _information_summary(
        inputs.reference_a,
        inputs.reference_b,
        inputs.detail_output_a,
        inputs.detail_output_b,
    )
    if detail_information < NO_CLAIM_FLOOR_BITS:
        return {
            "status": "NO_EVIDENCE",
            "information_bits_per_site": detail_information,
            "diagnostics": diagnostics,
        }

    flat_information = _information_summary(
        inputs.flat_reference_a,
        inputs.flat_reference_b,
        inputs.flat_output_a,
        inputs.flat_output_b,
    )
    detail_reference_power = _repeatable_power(
        inputs.reference_a, inputs.reference_b
    )
    detail_output_power = _repeatable_power(
        inputs.detail_output_a, inputs.detail_output_b
    )
    flat_reference_power = _repeatable_power(
        inputs.flat_reference_a, inputs.flat_reference_b
    )
    flat_output_power = _repeatable_power(
        inputs.flat_output_a, inputs.flat_output_b
    )
    if detail_reference_power <= 0.0 or detail_output_power <= 0.0:
        return {
            "status": "UNRESOLVED_DETAIL_POWER",
            "detail_reference_repeatable_power": detail_reference_power,
            "detail_output_repeatable_power": detail_output_power,
            "diagnostics": diagnostics,
        }
    information_ratio = flat_information / detail_information
    reference_ratio = flat_reference_power / detail_reference_power
    output_ratio = flat_output_power / detail_output_power
    flat_coherences = np.asarray(
        [
            _coherence(
                inputs.flat_reference_a[:, cell],
                inputs.flat_reference_b[:, cell],
            )
            for cell in range(inputs.reference_a.shape[1])
        ]
    )
    flat_passes = bool(
        float(np.min(flat_coherences)) < MIN_REFERENCE_COHERENCE
        and information_ratio <= MAX_FLAT_INFORMATION_RATIO
        and reference_ratio <= MAX_FLAT_REFERENCE_POWER_RATIO
        and output_ratio <= MAX_FLAT_OUTPUT_POWER_RATIO
    )
    flat_control = {
        "passes": flat_passes,
        "minimum_reference_coherence": float(np.min(flat_coherences)),
        "flat_to_detail_information_ratio": float(information_ratio),
        "flat_to_detail_reference_repeatable_power_ratio": float(reference_ratio),
        "flat_to_detail_output_repeatable_power_ratio": float(output_ratio),
    }
    if not flat_passes:
        return {
            "status": "FLAT_NULL_FAILED",
            "information_bits_per_site": detail_information,
            "flat_control": flat_control,
            "diagnostics": diagnostics,
        }

    transfer = []
    flat_noise_power = []
    equivalent_input_noise = []
    for cell in range(inputs.reference_a.shape[1]):
        pr = float(
            np.real(
                _complex_cov(
                    inputs.reference_a[:, cell],
                    inputs.reference_b[:, cell],
                )
            )
        )
        if pr <= 0.0:
            return {
                "status": "UNRESOLVED_REFERENCE_CELL",
                "cell": cell,
                "reference_power": pr,
            }
        cross = np.mean(
            [
                _complex_cov(
                    inputs.detail_output_a[:, cell],
                    inputs.reference_a[:, cell],
                ),
                _complex_cov(
                    inputs.detail_output_a[:, cell],
                    inputs.reference_b[:, cell],
                ),
                _complex_cov(
                    inputs.detail_output_b[:, cell],
                    inputs.reference_a[:, cell],
                ),
                _complex_cov(
                    inputs.detail_output_b[:, cell],
                    inputs.reference_b[:, cell],
                ),
            ]
        )
        cell_transfer = float(abs(cross) / pr)
        cell_noise = 0.5 * float(
            np.mean(
                np.abs(
                    inputs.flat_output_a[:, cell]
                    - inputs.flat_output_b[:, cell]
                )
                ** 2
            )
        )
        if cell_transfer <= 0.0 or cell_noise <= 0.0:
            return {
                "status": "UNRESOLVED_CELL",
                "cell": cell,
                "transfer": cell_transfer,
                "flat_noise_power": cell_noise,
            }
        transfer.append(cell_transfer)
        flat_noise_power.append(cell_noise)
        equivalent_input_noise.append(np.sqrt(cell_noise) / cell_transfer)

    ein = np.asarray(equivalent_input_noise)
    quality_score = float(-np.mean(np.log(ein)))
    return {
        "status": "OK",
        "quality_score": quality_score,
        "information_bits_per_site": detail_information,
        "frequencies": np.asarray(inputs.frequencies).tolist(),
        "transfer": transfer,
        "flat_noise_power": flat_noise_power,
        "equivalent_input_noise": ein.tolist(),
        "flat_control": flat_control,
        "diagnostics": diagnostics,
    }


def compare_arms(
    candidate: ArmInputs,
    comparator: ArmInputs,
    *,
    transfer_veto_status: str,
) -> dict[str, Any]:
    if transfer_veto_status == "INADMISSIBLE_COMMON_TRANSFER":
        return {"status": "INADMISSIBLE_COMMON_TRANSFER"}
    if transfer_veto_status != "NOT_VETOED":
        return {"status": "TRANSFER_VETO_REQUIRED"}

    if not (
        np.array_equal(candidate.reference_a, comparator.reference_a)
        and np.array_equal(candidate.reference_b, comparator.reference_b)
        and np.array_equal(candidate.flat_reference_a, comparator.flat_reference_a)
        and np.array_equal(candidate.flat_reference_b, comparator.flat_reference_b)
        and np.array_equal(candidate.frequencies, comparator.frequencies)
    ):
        return {"status": "REFERENCE_MISMATCH"}

    candidate_result = evaluate_arm(candidate)
    comparator_result = evaluate_arm(comparator)
    if candidate_result["status"] != "OK" or comparator_result["status"] != "OK":
        return {
            "status": "ARM_REFUSED",
            "candidate_status": candidate_result["status"],
            "comparator_status": comparator_result["status"],
        }

    candidate_ein = np.asarray(candidate_result["equivalent_input_noise"])
    comparator_ein = np.asarray(comparator_result["equivalent_input_noise"])
    cell_ratios = candidate_ein / comparator_ein
    q_ein = float(np.exp(np.mean(np.log(cell_ratios))))
    return {
        "status": "OK",
        "q_ein": q_ein,
        "quality_score_delta": float(-np.log(q_ein)),
        "cell_ratios": cell_ratios.tolist(),
        "direction": "q_ein below one and quality_score_delta above zero favor candidate",
        "candidate": candidate_result,
        "comparator": comparator_result,
    }
