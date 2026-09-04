"""Synthetic commissioning for REFERENCE_INFORMATION_DOMINANCE."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from dominance import (
    GateConfig,
    estimate_common_mode_bounds,
    evaluate_dominance,
)


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "commission.json"
CELLS = 4
SITES = 256


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def unit_complex(
    rng: np.random.Generator,
    sites: int,
    cells: int,
) -> np.ndarray:
    values = (
        rng.normal(size=(sites, cells))
        + 1j * rng.normal(size=(sites, cells))
    ) / np.sqrt(2.0)
    values -= np.mean(values, axis=0, keepdims=True)
    power = np.sum(np.abs(values) ** 2, axis=0) / (sites - 1)
    return values / np.sqrt(power)[np.newaxis, :]


def orthogonal_common_mode(
    rng: np.random.Generator,
    latent: np.ndarray,
    power: float,
) -> np.ndarray:
    common = unit_complex(rng, latent.shape[0], latent.shape[1])
    for cell in range(latent.shape[1]):
        projection = np.vdot(latent[:, cell], common[:, cell]) / np.vdot(
            latent[:, cell],
            latent[:, cell],
        )
        common[:, cell] -= projection * latent[:, cell]
    common -= np.mean(common, axis=0, keepdims=True)
    common_power = np.sum(np.abs(common) ** 2, axis=0) / (
        latent.shape[0] - 1
    )
    return (
        common
        / np.sqrt(common_power)[np.newaxis, :]
        * np.sqrt(power)
    )


def witnesses(
    rng: np.random.Generator,
    latent: np.ndarray,
    transfer: np.ndarray,
    noise_scale: float,
    common: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    common_term = 0.0 if common is None else common
    first = (
        latent * transfer[np.newaxis, :]
        + common_term
        + noise_scale * unit_complex(rng, *latent.shape)
    )
    second = (
        latent * transfer[np.newaxis, :]
        + common_term
        + noise_scale * unit_complex(rng, *latent.shape)
    )
    return first, second


def controls(
    rng: np.random.Generator,
    shape: tuple[int, int],
    noise_scale: float,
    common: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    common_term = 0.0 if common is None else common
    first = common_term + noise_scale * unit_complex(rng, *shape)
    second = common_term + noise_scale * unit_complex(rng, *shape)
    return first, second


def minimum(values: list[float]) -> float:
    return float(np.min(np.asarray(values, dtype=np.float64)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--plant-defect",
        choices=("ignore-common-mode",),
    )
    arguments = parser.parse_args(argv)

    rng = np.random.default_rng(164_176)
    latent = unit_complex(rng, SITES, CELLS)
    known_latent_power = np.ones(CELLS)
    shared_objective = np.asarray([1.0, 0.8, 0.5, 0.0])
    reference_specific = np.asarray([1.40, 1.30, 1.20, 1.10])
    scored_specific = np.asarray([1.00, 0.90, 0.80, 0.70])
    shared_reference_transfer = reference_specific * shared_objective
    shared_scored_transfer = scored_specific * shared_objective
    shared_support = shared_objective > 0.0
    shared_supported_ratio = (
        shared_reference_transfer[shared_support]
        / shared_scored_transfer[shared_support]
    )
    scored_transfer = np.ones(CELLS)
    config = GateConfig(
        delta_information=np.full(CELLS, 0.08),
        delta_transfer=np.full(CELLS, 0.08),
        bootstrap_draws=10_000,
        bootstrap_seed=164_177,
        dominance_alpha=0.025,
        minimum_power=1.0e-10,
        maximum_common_fraction=0.05,
    )
    clean_reference_control_1, clean_reference_control_2 = controls(
        rng,
        latent.shape,
        noise_scale=0.02,
    )
    clean_scored_control_1, clean_scored_control_2 = controls(
        rng,
        latent.shape,
        noise_scale=0.02,
    )
    clean_common_bounds = estimate_common_mode_bounds(
        clean_reference_control_1,
        clean_reference_control_2,
        clean_scored_control_1,
        clean_scored_control_2,
        alpha=0.025,
        bootstrap_draws=10_000,
        bootstrap_seed=164_175,
    )
    clean_reference_bound = np.asarray(
        clean_common_bounds["reference_ucb"]
    )
    clean_scored_bound = np.asarray(clean_common_bounds["scored_ucb"])

    scored_1, scored_2 = witnesses(
        rng,
        latent,
        scored_transfer,
        noise_scale=0.10,
    )
    legitimate_reference_1, legitimate_reference_2 = witnesses(
        rng,
        latent,
        np.asarray([1.40, 1.35, 1.30, 1.25]),
        noise_scale=0.07,
    )
    legitimate = evaluate_dominance(
        legitimate_reference_1,
        legitimate_reference_2,
        scored_1,
        scored_2,
        clean_reference_bound,
        clean_scored_bound,
        config,
        known_latent_power=known_latent_power,
    )
    legitimate_relative_only = evaluate_dominance(
        legitimate_reference_1,
        legitimate_reference_2,
        scored_1,
        scored_2,
        clean_reference_bound,
        clean_scored_bound,
        config,
    )

    weak_reference_1, weak_reference_2 = witnesses(
        rng,
        latent,
        np.asarray([1.40, 1.35, 1.30, 0.60]),
        noise_scale=0.07,
    )
    single_cell_violation = evaluate_dominance(
        weak_reference_1,
        weak_reference_2,
        scored_1,
        scored_2,
        clean_reference_bound,
        clean_scored_bound,
        config,
        known_latent_power=known_latent_power,
    )

    clean_reference_1, clean_reference_2 = witnesses(
        rng,
        latent,
        np.full(CELLS, 1.02),
        noise_scale=0.05,
    )
    clean_improvement_shape = evaluate_dominance(
        clean_reference_1,
        clean_reference_2,
        scored_1,
        scored_2,
        clean_reference_bound,
        clean_scored_bound,
        config,
        known_latent_power=known_latent_power,
    )

    common = orthogonal_common_mode(rng, latent, power=0.50)
    contaminated_reference_1 = clean_reference_1 + common
    contaminated_reference_2 = clean_reference_2 + common
    naive_improvement = evaluate_dominance(
        contaminated_reference_1,
        contaminated_reference_2,
        scored_1,
        scored_2,
        np.zeros(CELLS),
        np.zeros(CELLS),
        config,
        known_latent_power=known_latent_power,
    )
    contaminated_reference_control_1, contaminated_reference_control_2 = (
        controls(
            rng,
            latent.shape,
            noise_scale=0.02,
            common=common,
        )
    )
    contaminated_common_bounds = estimate_common_mode_bounds(
        contaminated_reference_control_1,
        contaminated_reference_control_2,
        clean_scored_control_1,
        clean_scored_control_2,
        alpha=0.025,
        bootstrap_draws=10_000,
        bootstrap_seed=164_178,
    )
    common_bound = np.asarray(
        contaminated_common_bounds["reference_ucb"]
    )
    charged_bound = (
        np.zeros(CELLS)
        if arguments.plant_defect == "ignore-common-mode"
        else common_bound
    )
    charged_improvement = evaluate_dominance(
        contaminated_reference_1,
        contaminated_reference_2,
        scored_1,
        scored_2,
        charged_bound,
        np.zeros(CELLS),
        config,
        known_latent_power=known_latent_power,
    )

    clean_min_information = minimum(
        clean_improvement_shape["point"]["information_ratio"]
    )
    clean_min_transfer = minimum(
        clean_improvement_shape["point"]["transfer_ratio"]
    )
    naive_min_information = minimum(
        naive_improvement["point"]["information_ratio"]
    )
    naive_min_transfer = minimum(
        naive_improvement["point"]["transfer_ratio"]
    )
    weak_transfer_mean = float(
        np.mean(single_cell_violation["point"]["transfer_ratio"])
    )
    checks = {
        "C1_shared_objective_allows_supported_dominance": bool(
            np.all(shared_supported_ratio > 1.0)
        ),
        "C2_shared_objective_null_remains_common": bool(
            shared_reference_transfer[-1] == 0.0
            and shared_scored_transfer[-1] == 0.0
        ),
        "C3_legitimate_case_is_admitted": legitimate["status"] == "PASS",
        "C4_legitimate_case_keeps_every_cell": all(
            legitimate["cell_pass"]
        ),
        "C5_known_input_yields_absolute_transfer_estimates": (
            legitimate["absolute_transfer_status"] == "KNOWN_INPUT"
            and "absolute_transfer" in legitimate
        ),
        "C6_unknown_input_refuses_absolute_transfer_labels": (
            legitimate_relative_only["status"] == "PASS"
            and legitimate_relative_only["absolute_transfer_status"]
            == "ABSOLUTE_TRANSFER_UNIDENTIFIED"
            and "absolute_transfer" not in legitimate_relative_only
        ),
        "C7_single_weak_cell_is_rejected": (
            single_cell_violation["status"] == "UNMEASURED"
        ),
        "C8_strong_cells_do_not_compensate": (
            single_cell_violation["cell_pass"][:3] == [True, True, True]
            and single_cell_violation["cell_pass"][3] is False
            and weak_transfer_mean > 1.08
        ),
        "C9_clean_improvement_shape_fails_transfer_margin": (
            clean_improvement_shape["status"] == "UNMEASURED"
            and clean_improvement_shape["information_pass"]
            == [True, True, True, True]
            and clean_improvement_shape["transfer_pass"]
            != [True, True, True, True]
        ),
        "C10_common_mode_raises_information_number": (
            naive_min_information > clean_min_information
        ),
        "C11_common_mode_raises_transfer_number": (
            naive_min_transfer > clean_min_transfer
        ),
        "C12_naive_improvement_shaped_case_would_pass": (
            naive_improvement["status"] == "PASS"
        ),
        "C13_charged_improvement_shaped_case_is_rejected": (
            charged_improvement["status"] == "UNMEASURED"
        ),
        "C14_common_mode_gate_names_the_failure": (
            charged_improvement["failure"] == "COMMON_MODE_BOUND"
        ),
        "C15_gate_uses_one_noncompensating_family": (
            legitimate["family"]["members"] == 2 * CELLS
            and legitimate["family"]["method"]
            == "paired-site one-sided max-t cluster bootstrap"
        ),
    }

    result: dict[str, Any] = {
        "schema": "m164-reference-dominance-commission-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "planted_defect": arguments.plant_defect,
        "captures_opened": 0,
        "config": {
            "sites": SITES,
            "cells": CELLS,
            "delta_information": 0.08,
            "delta_transfer": 0.08,
            "overall_familywise_alpha": 0.05,
            "common_bound_alpha": 0.025,
            "dominance_alpha": config.dominance_alpha,
            "bootstrap_draws": config.bootstrap_draws,
            "bootstrap_seed": config.bootstrap_seed,
            "maximum_common_fraction": config.maximum_common_fraction,
        },
        "shared_objective_ruling": {
            "verdict": "SUFFICIENT_ON_MEASURED_NON_NULL_PASSBAND",
            "factorization": "H_R=A*G; H_S=B*G",
            "ratio_on_support": "|H_R/H_S|=|A/B|",
            "G": _serialise_for_json(shared_objective),
            "A": _serialise_for_json(reference_specific),
            "B": _serialise_for_json(scored_specific),
            "H_R": _serialise_for_json(shared_reference_transfer),
            "H_S": _serialise_for_json(shared_scored_transfer),
            "supported_ratios": _serialise_for_json(
                shared_supported_ratio
            ),
            "permanent_exclusion": "null(G) and unresolved near-null cells",
        },
        "legitimate": legitimate,
        "legitimate_relative_only": legitimate_relative_only,
        "single_cell_violation": single_cell_violation,
        "improvement_shaped_common_mode": {
            "clean": clean_improvement_shape,
            "contaminated_naive": naive_improvement,
            "contaminated_charged": charged_improvement,
            "clean_min_information_ratio": clean_min_information,
            "contaminated_naive_min_information_ratio": (
                naive_min_information
            ),
            "clean_min_transfer_ratio": clean_min_transfer,
            "contaminated_naive_min_transfer_ratio": naive_min_transfer,
            "common_mode_true_power": 0.50,
            "common_mode_charged_bound": _serialise_for_json(
                charged_bound
            ),
            "common_mode_bound_estimator": contaminated_common_bounds,
        },
        "clean_common_mode_bound_estimator": clean_common_bounds,
        "checks": checks,
        "source": {
            "dominance_py_sha256": digest(HERE / "dominance.py"),
            "commission_py_sha256": digest(Path(__file__)),
        },
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    passed = sum(checks.values())
    print(
        f"{result['status']}: {passed}/{len(checks)} checks; "
        f"legitimate={legitimate['status']}; "
        f"weak-cell={single_cell_violation['status']}; "
        f"naive-improvement={naive_improvement['status']}; "
        f"charged-improvement={charged_improvement['status']}; "
        "captures_opened=0"
    )
    return 0 if result["status"] == "PASS" else 1


def _serialise_for_json(values: np.ndarray) -> list[float]:
    return [float(value) for value in values]


if __name__ == "__main__":
    raise SystemExit(main())
