"""Truth-referenced detail certificate used by the M135 commissioning probe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


FREQUENCIES = np.repeat(np.array([0.10, 0.15, 0.20, 0.25]), 4)
ANGLES_DEG = np.tile(np.array([0.0, 22.5, 45.0, 67.5]), 4)
MIN_SITES = 64
MIN_REFERENCE_COHERENCE = 0.50
MAX_REFERENCE_CONDITION = 100.0
MAX_CLIP_FRACTION = 0.001
MIN_EFFECTIVE_BITS = 12
MAX_CALIBRATION_CORRELATION = 0.05
NO_CLAIM_FLOOR_BITS = 0.10
PERMUTATION_COUNT = 32


@dataclass(frozen=True)
class CaptureSet:
    reference_a: np.ndarray
    reference_b: np.ndarray
    output_a: np.ndarray
    output_b: np.ndarray
    clip_fraction: float = 0.0
    effective_bits: int = 16
    calibration_correlation: float = 0.0
    target_lineage: str = "nonperiodic-random"


def _complex_cov(a: np.ndarray, b: np.ndarray) -> complex:
    ac = a - np.mean(a)
    bc = b - np.mean(b)
    return np.mean(ac * np.conj(bc))


def _complex_variance(a: np.ndarray) -> float:
    return float(np.real(_complex_cov(a, a)))


def _raw_information_bits(y: np.ndarray, r: np.ndarray) -> float:
    vy = _complex_variance(y)
    vr = _complex_variance(r)
    if vy <= 0.0 or vr <= 0.0:
        return 0.0
    rho2 = float(abs(_complex_cov(y, r)) ** 2 / (vy * vr))
    rho2 = min(max(rho2, 0.0), 1.0 - 1e-15)
    return float(-np.log2(1.0 - rho2))


def _permutations(n: int) -> list[np.ndarray]:
    rng = np.random.default_rng(202609135 + n)
    base = np.arange(n)
    result: list[np.ndarray] = []
    while len(result) < PERMUTATION_COUNT:
        p = rng.permutation(n)
        if np.any(p == base):
            continue
        if any(np.array_equal(p, old) for old in result):
            continue
        result.append(p)
    return result


def _corrected_cell_information(
    y: np.ndarray, r: np.ndarray, permutations: list[np.ndarray]
) -> float:
    observed = _raw_information_bits(y, r)
    nulls = np.array([_raw_information_bits(y, r[p]) for p in permutations])
    floor = float(np.quantile(nulls, 0.95, method="higher"))
    return max(0.0, observed - floor)


def _reference_diagnostics(r1: np.ndarray, r2: np.ndarray) -> dict[str, Any]:
    coherences = []
    for cell in range(r1.shape[1]):
        v1 = _complex_variance(r1[:, cell])
        v2 = _complex_variance(r2[:, cell])
        if v1 <= 0.0 or v2 <= 0.0:
            coherences.append(0.0)
            continue
        coherences.append(
            float(abs(_complex_cov(r1[:, cell], r2[:, cell])) / np.sqrt(v1 * v2))
        )

    rmean = (r1 + r2) / 2.0
    real_features = np.concatenate([rmean.real, rmean.imag], axis=1)
    covariance = np.cov(real_features, rowvar=False, ddof=1)
    rank = int(np.linalg.matrix_rank(covariance))
    condition = float(np.linalg.cond(covariance))
    return {
        "minimum_repeat_coherence": float(np.min(coherences)),
        "median_repeat_coherence": float(np.median(coherences)),
        "rank": rank,
        "dimension": int(covariance.shape[0]),
        "condition": condition,
    }


def _status(captures: CaptureSet) -> tuple[str, dict[str, Any]]:
    arrays = (
        captures.reference_a,
        captures.reference_b,
        captures.output_a,
        captures.output_b,
    )
    if any(a.ndim != 2 for a in arrays):
        return "INVALID_SHAPE", {}
    if len({a.shape for a in arrays}) != 1:
        return "INVALID_SHAPE", {}
    n, cells = arrays[0].shape
    if n < MIN_SITES or cells != len(FREQUENCIES):
        return "INVALID_SHAPE", {"sites": n, "cells": cells}
    if not all(np.all(np.isfinite(a)) for a in arrays):
        return "NONFINITE", {}
    if float(np.max(FREQUENCIES)) > 0.25:
        return "OUT_OF_BAND", {}
    if captures.clip_fraction > MAX_CLIP_FRACTION:
        return "NONLINEAR_OUTPUT", {"clip_fraction": captures.clip_fraction}
    if captures.effective_bits < MIN_EFFECTIVE_BITS:
        return "LOW_BIT_DEPTH", {"effective_bits": captures.effective_bits}
    if abs(captures.calibration_correlation) > MAX_CALIBRATION_CORRELATION:
        return "SHARED_REFERENCE", {
            "calibration_correlation": captures.calibration_correlation
        }
    if captures.target_lineage != "nonperiodic-random":
        return "PREDICTABLE_TARGET", {"target_lineage": captures.target_lineage}

    diagnostics = _reference_diagnostics(captures.reference_a, captures.reference_b)
    if diagnostics["minimum_repeat_coherence"] < MIN_REFERENCE_COHERENCE:
        return "NO_DETAIL", diagnostics
    if (
        diagnostics["rank"] < diagnostics["dimension"]
        or diagnostics["condition"] > MAX_REFERENCE_CONDITION
    ):
        return "ILL_CONDITIONED_REFERENCE", diagnostics
    return "ELIGIBLE", diagnostics


def evaluate(captures: CaptureSet) -> dict[str, Any]:
    status, diagnostics = _status(captures)
    if status != "ELIGIBLE":
        return {"status": status, "reference": diagnostics}

    r1 = captures.reference_a
    r2 = captures.reference_b
    y1 = captures.output_a
    y2 = captures.output_b
    permutations = _permutations(r1.shape[0])

    pair_scores = []
    cell_scores_by_pair = []
    for y in (y1, y2):
        for r in (r1, r2):
            cells = np.array(
                [
                    _corrected_cell_information(
                        y[:, cell], r[:, cell], permutations
                    )
                    for cell in range(r.shape[1])
                ]
            )
            cell_scores_by_pair.append(cells)
            pair_scores.append(float(np.mean(cells)))

    information = float(np.min(pair_scores))
    if information < NO_CLAIM_FLOOR_BITS:
        return {
            "status": "NO_EVIDENCE",
            "reference": diagnostics,
            "information_bits_per_site": information,
            "pair_scores": pair_scores,
        }

    transfers = []
    unexplained = []
    noise_ratios = []
    for cell in range(r1.shape[1]):
        pr = float(np.real(_complex_cov(r1[:, cell], r2[:, cell])))
        py = float(np.real(_complex_cov(y1[:, cell], y2[:, cell])))
        cross = np.mean(
            [
                _complex_cov(y1[:, cell], r1[:, cell]),
                _complex_cov(y1[:, cell], r2[:, cell]),
                _complex_cov(y2[:, cell], r1[:, cell]),
                _complex_cov(y2[:, cell], r2[:, cell]),
            ]
        )
        if pr <= 0.0:
            return {"status": "NO_DETAIL", "reference": diagnostics}
        explained = float(abs(cross) ** 2 / pr)
        residual = max(0.0, py - explained)
        noise = 0.5 * float(np.mean(abs(y1[:, cell] - y2[:, cell]) ** 2))
        transfers.append(abs(cross) / pr)
        unexplained.append(residual / max(py, np.finfo(float).tiny))
        noise_ratios.append(noise / max(explained, np.finfo(float).tiny))

    transfer = float(np.exp(np.mean(np.log(np.maximum(transfers, 1e-300)))))
    result = {
        "status": "OK",
        "information_bits_per_site": information,
        "transfer": transfer,
        "unexplained_fraction": float(np.median(unexplained)),
        "noise_to_explained": float(np.median(noise_ratios)),
        "pair_scores": pair_scores,
        "cell_scores_min_pair": cell_scores_by_pair[int(np.argmin(pair_scores))].tolist(),
        "reference": diagnostics,
    }
    return result


def postfilter(captures: CaptureSet, gains: np.ndarray) -> CaptureSet:
    gains = np.asarray(gains)
    if gains.shape != (len(FREQUENCIES),):
        raise ValueError("one gain is required for each registered cell")
    return CaptureSet(
        reference_a=captures.reference_a,
        reference_b=captures.reference_b,
        output_a=captures.output_a * gains[np.newaxis, :],
        output_b=captures.output_b * gains[np.newaxis, :],
        clip_fraction=captures.clip_fraction,
        effective_bits=captures.effective_bits,
        calibration_correlation=captures.calibration_correlation,
        target_lineage=captures.target_lineage,
    )


def rotate_cells(captures: CaptureSet, quarter_turns: int) -> CaptureSet:
    shift = quarter_turns % 4
    order = np.arange(len(FREQUENCIES)).reshape(4, 4)
    order = np.roll(order, shift, axis=1).ravel()
    phase = np.exp(1j * shift * np.pi / 7.0)

    def transform(a: np.ndarray) -> np.ndarray:
        return a[:, order] * phase

    return CaptureSet(
        reference_a=transform(captures.reference_a),
        reference_b=transform(captures.reference_b),
        output_a=transform(captures.output_a),
        output_b=transform(captures.output_b),
        clip_fraction=captures.clip_fraction,
        effective_bits=captures.effective_bits,
        calibration_correlation=captures.calibration_correlation,
        target_lineage=captures.target_lineage,
    )
