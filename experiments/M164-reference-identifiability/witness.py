"""Construct finite witnesses for optical-reference identifiability."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "results.json"
PROPOSAL = (
    HERE.parents[1]
    / "docs"
    / "proposals"
    / "2026-09-truth-referenced-detail.md"
)
SAMPLING_RATIO = 2.7015 / 1.33
SAMPLING_BAR = 2.0
NEAR_NULL_UNCERTAINTY = 1.0e-3


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def diagonal(values: list[float]) -> np.ndarray:
    return np.diag(np.asarray(values, dtype=np.float64))


def max_error(first: np.ndarray, second: np.ndarray) -> float:
    return float(np.max(np.abs(first - second)))


def information(transfer: float, noise_power: float) -> float:
    return 0.5 * float(np.log2(1.0 + transfer**2 / noise_power))


def covariance(first: np.ndarray, second: np.ndarray) -> float:
    centered_first = first - np.mean(first)
    centered_second = second - np.mean(second)
    return float(np.mean(centered_first * centered_second))


def common_mode_covariance_witness() -> dict[str, float]:
    rows = np.asarray(list(itertools.product((-1.0, 1.0), repeat=4)))
    signal = rows[:, 0]
    common = 0.2 * rows[:, 1]
    noise_1 = 0.1 * rows[:, 2]
    noise_2 = 0.1 * rows[:, 3]
    reference_1 = signal + common + noise_1
    reference_2 = signal + common + noise_2
    flat_1 = common + noise_1
    flat_2 = common + noise_2
    conditional_noise_covariance = covariance(noise_1, noise_2)
    covariance_of_conditional_means = covariance(
        signal + common,
        signal + common,
    )
    total = covariance(reference_1, reference_2)
    return {
        "conditional_noise_covariance": conditional_noise_covariance,
        "covariance_of_conditional_means": covariance_of_conditional_means,
        "total_reference_cross_covariance": total,
        "scene_cross_covariance": covariance(signal, signal),
        "common_mode_bias": total - covariance(signal, signal),
        "featureless_cross_covariance": covariance(flat_1, flat_2),
        "law_of_total_covariance_sum": (
            conditional_noise_covariance + covariance_of_conditional_means
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--plant-defect",
        choices=("informative-reference-collapse",),
    )
    arguments = parser.parse_args(argv)

    x = np.asarray([1.0, 0.8, 0.6, 0.4])
    scored_transfer = diagonal([0.90, 0.70, 0.50, 0.30])
    sharpening = diagonal([1.0, 1.0, 1.20, 1.0])
    reference_unknown = diagonal([0.95, 0.80, 0.60, 0.40])

    y_world_a = sharpening @ scored_transfer @ x
    r_world_a = reference_unknown @ x
    x_world_b = sharpening @ x
    reference_world_b = reference_unknown @ np.linalg.inv(sharpening)
    y_world_b = scored_transfer @ x_world_b
    r_world_b = reference_world_b @ x_world_b

    null_sharpening = diagonal([1.0, 1.0, 1.0, 2.0])
    reference_null = diagonal([0.95, 0.80, 0.60, 0.0])
    y_null_a = null_sharpening @ scored_transfer @ x
    r_null_a = reference_null @ x
    x_null_b = null_sharpening @ x
    y_null_b = scored_transfer @ x_null_b
    r_null_b = reference_null @ x_null_b

    reference_near_null = diagonal([0.95, 0.80, 0.60, 1.0e-4])
    near_null_reference_delta = max_error(
        reference_near_null @ x,
        reference_near_null @ x_null_b,
    )
    informative_last_mode = (
        1.0e-4
        if arguments.plant_defect == "informative-reference-collapse"
        else 0.20
    )
    reference_informative = diagonal(
        [0.95, 0.80, 0.60, informative_last_mode]
    )
    informative_reference_delta = max_error(
        reference_informative @ x,
        reference_informative @ x_null_b,
    )

    scored_information = information(0.30, 0.01)
    empty_magnification_reference_information = information(0.20, 0.01)
    dominant_reference_information = information(0.50, 0.01)

    covariance_witness = common_mode_covariance_witness()
    checks = {
        "C1_unknown_reference_transfer_gauge_is_exact": (
            max_error(y_world_a, y_world_b) == 0.0
            and max_error(r_world_a, r_world_b) == 0.0
        ),
        "C2_companion_reference_transfer_remains_positive_monotone": bool(
            np.all(np.diag(reference_world_b) > 0.0)
            and np.all(np.diff(np.diag(reference_world_b)) <= 0.0)
        ),
        "C3_fixed_reference_nullspace_hides_nonidentity_sharpening": (
            max_error(y_null_a, y_null_b) == 0.0
            and max_error(r_null_a, r_null_b) == 0.0
            and not np.array_equal(null_sharpening, np.eye(len(x)))
        ),
        "C4_near_null_change_is_below_uncertainty": (
            0.0 < near_null_reference_delta < NEAR_NULL_UNCERTAINTY
        ),
        "C5_informative_reference_exposes_same_change": (
            informative_reference_delta > NEAR_NULL_UNCERTAINTY
        ),
        "C6_sampling_gate_passes_while_nullspace_ambiguity_survives": (
            SAMPLING_RATIO >= SAMPLING_BAR
            and max_error(r_null_a, r_null_b) == 0.0
        ),
        "C7_positive_reference_information_need_not_dominate_scored": (
            empty_magnification_reference_information > 0.0
            and empty_magnification_reference_information < scored_information
        ),
        "C8_dominant_reference_information_can_exceed_scored": (
            dominant_reference_information > scored_information
        ),
        "C9_conditional_noise_independence_does_not_remove_common_mode": (
            covariance_witness["conditional_noise_covariance"] == 0.0
            and covariance_witness["common_mode_bias"] > 0.0
        ),
        "C10_law_of_total_covariance_closes": bool(
            np.isclose(
                covariance_witness["total_reference_cross_covariance"],
                covariance_witness["law_of_total_covariance_sum"],
                rtol=0.0,
                atol=1.0e-15,
            )
        ),
        "C11_featureless_split_exposes_common_mode": (
            covariance_witness["featureless_cross_covariance"] > 0.0
        ),
    }

    result: dict[str, Any] = {
        "schema": "m164-reference-identifiability-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verdict": "CONDITIONAL_ROUTE_SAMPLING_ALONE_INSUFFICIENT",
        "planted_defect": arguments.plant_defect,
        "captures_opened": 0,
        "sampling": {
            "reference": 2.7015,
            "scored": 1.33,
            "ratio": SAMPLING_RATIO,
            "bar": SAMPLING_BAR,
            "absolute_margin": SAMPLING_RATIO - SAMPLING_BAR,
            "relative_margin_over_bar": SAMPLING_RATIO / SAMPLING_BAR - 1.0,
            "relative_margin_of_achieved": (
                (SAMPLING_RATIO - SAMPLING_BAR) / SAMPLING_RATIO
            ),
            "interpretation": (
                "The geometric gate passes but contributes no constraint "
                "to either constructed transfer ambiguity."
            ),
        },
        "unknown_reference_transfer_witness": {
            "world_A": "Y=K H X, R=H_R X",
            "world_B": "Y=H K X, R=(H_R K^-1) K X",
            "candidate_output_max_error": max_error(y_world_a, y_world_b),
            "reference_max_error": max_error(r_world_a, r_world_b),
            "K_diagonal": np.diag(sharpening).tolist(),
            "H_R_world_A_diagonal": np.diag(reference_unknown).tolist(),
            "H_R_world_B_diagonal": np.diag(reference_world_b).tolist(),
        },
        "fixed_reference_nullspace_witness": {
            "world_A": "Y=K_null H X, R=H_R X",
            "world_B": "Y=H K_null X, R=H_R K_null X",
            "candidate_output_max_error": max_error(y_null_a, y_null_b),
            "reference_max_error": max_error(r_null_a, r_null_b),
            "K_null_diagonal": np.diag(null_sharpening).tolist(),
            "H_R_diagonal": np.diag(reference_null).tolist(),
            "near_null_H_R_diagonal": np.diag(
                reference_near_null
            ).tolist(),
            "near_null_reference_delta": near_null_reference_delta,
            "near_null_uncertainty": NEAR_NULL_UNCERTAINTY,
            "informative_H_R_diagonal": np.diag(
                reference_informative
            ).tolist(),
            "informative_reference_delta": informative_reference_delta,
        },
        "information_dominance_witness": {
            "latent_power": 1.0,
            "noise_power": 0.01,
            "scored_transfer": 0.30,
            "scored_information_bits": scored_information,
            "empty_magnification_reference_transfer": 0.20,
            "empty_magnification_reference_information_bits": (
                empty_magnification_reference_information
            ),
            "empty_reference_to_scored_information_ratio": (
                empty_magnification_reference_information
                / scored_information
            ),
            "dominant_reference_transfer": 0.50,
            "dominant_reference_information_bits": (
                dominant_reference_information
            ),
            "dominant_reference_to_scored_information_ratio": (
                dominant_reference_information / scored_information
            ),
        },
        "odd_even_independence_witness": covariance_witness,
        "checks": checks,
        "required_gate": {
            "name": "REFERENCE_INFORMATION_DOMINANCE",
            "shape": (
                "for every frozen channel/frequency/orientation cell, require "
                "a simultaneous lower confidence bound on independently "
                "calibrated reference/scored information ratio to exceed "
                "1 + delta_I, plus nonzero reference transfer and an "
                "independently measured scored/reference transfer baseline"
            ),
            "failure": "UNMEASURED",
        },
        "source": {
            "witness_py_sha256": sha256(Path(__file__)),
            "proposal_read": (
                "docs/proposals/2026-09-truth-referenced-detail.md section 3.1"
            ),
            "proposal_file_sha256": sha256(PROPOSAL),
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{result['status']}: {sum(checks.values())}/{len(checks)} checks; "
        f"verdict={result['verdict']}; "
        f"sampling={SAMPLING_RATIO:.6f}x; captures_opened=0"
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
