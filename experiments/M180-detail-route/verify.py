from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASELINE_VERDICT = "UNDECIDED_REFERENCE_ROUTE_OPEN_PHYSICAL_UNMEASURED"
FAILED_VERDICT = "EVIDENCE_FAILED"


DEFAULTS = {
    "fixture": HERE / "evidence" / "model-fixtures.json",
    "m164_report": ROOT / "docs" / "research" / "M164-m2-repair.md",
    "m168_report": ROOT / "docs" / "research" / "M168-m2-identifiability.md",
    "m135_commission": (
        ROOT / "experiments" / "M135-detail-instrument" / "commission.json"
    ),
    "m135_results": (
        ROOT / "experiments" / "M135-detail-instrument" / "RESULTS.md"
    ),
    "dominance_commission": (
        ROOT
        / "experiments"
        / "M164-reference-dominance"
        / "commission.json"
    ),
    "m167_admission": (
        ROOT
        / "experiments"
        / "M167-detail-battery"
        / "admission-results.json"
    ),
    "m167_preregistration": (
        ROOT
        / "experiments"
        / "M167-detail-battery"
        / "PREREGISTRATION.md"
    ),
    "archive_report": (
        ROOT / "docs" / "research" / "M168-cheap-reference-feasibility.md"
    ),
    "slanted_report": (
        ROOT / "docs" / "research" / "M-PHASE0-SLANTEDGE.md"
    ),
    "manifest_report": (
        ROOT / "docs" / "research" / "M164-dominance-manifest.md"
    ),
}


M164_SCOPE = (
    "Any deterministic statistic of `(A,B)` receives the same input in both\n"
    "worlds. It cannot reject `B` in the first and reward `B` in the second "
    "without\n"
    "an assumption or observation outside those outputs."
)
M168_SCOPE = (
    "> **WARNING — INFERRED BY READING.** The distribution-free impossibility "
    "is sound, but it must not be shortened to “no reference-free metric can "
    "ever ground the claim.” The words **“without an assumption or observation "
    "outside those outputs” are load-bearing and may not be dropped.** A prior, "
    "restricted scene model, calibrated generative model, reference, or "
    "controlled target can add identifying information; any resulting claim "
    "inherits that assumption and its scope."
)
M167_REFERENCE_SCHEMA = (
    "- a future explicitly preregistered reference-bearing mode."
)
PCHIP_SCOPE = (
    "Independent 33-step PCHIP linearisation is the one clean success: V3–V5 "
    "move\n"
    "under affine/gamma/logistic by at most **0.0141%**, without losing their "
    "USM\n"
    "result.  Tone can therefore be fixed without ordinality, but that does "
    "not fix\n"
    "the optical/noise defeats."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    for name, default in DEFAULTS.items():
        parser.add_argument(
            f"--{name.replace('_', '-')}",
            type=Path,
            default=default,
        )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} does not contain a JSON object")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def matvec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        sum(float(value) * float(vector[index]) for index, value in enumerate(row))
        for row in matrix
    ]


def vectors_close(
    left: list[float],
    right: list[float],
    *,
    tolerance: float = 1e-15,
) -> bool:
    return len(left) == len(right) and all(
        abs(float(a) - float(b)) <= tolerance
        for a, b in zip(left, right, strict=True)
    )


def make_smoother(fixture: dict[str, Any]) -> list[list[float]]:
    edge_self = float(fixture["smoother_edge_self"])
    edge_neighbor = float(fixture["smoother_edge_neighbor"])
    neighbor = float(fixture["smoother_interior_neighbor"])
    center = float(fixture["smoother_interior_self"])
    return [
        [edge_self, edge_neighbor, 0.0, 0.0, 0.0],
        [neighbor, center, neighbor, 0.0, 0.0],
        [0.0, neighbor, center, neighbor, 0.0],
        [0.0, 0.0, neighbor, center, neighbor],
        [0.0, 0.0, 0.0, edge_neighbor, edge_self],
    ]


def bernoulli_joint(
    reference_probability: float,
    output_probability: float,
    *,
    coupled: bool,
) -> dict[tuple[int, int], float]:
    if coupled:
        if abs(reference_probability - output_probability) > 1e-15:
            raise ValueError("coupled Bernoulli marginals must match")
        return {
            (0, 0): 1.0 - reference_probability,
            (0, 1): 0.0,
            (1, 0): 0.0,
            (1, 1): reference_probability,
        }
    return {
        (reference, output): (
            (reference_probability if reference else 1.0 - reference_probability)
            * (output_probability if output else 1.0 - output_probability)
        )
        for reference in (0, 1)
        for output in (0, 1)
    }


def joint_moments(
    joint: dict[tuple[int, int], float],
) -> tuple[float, float, float]:
    reference_mean = sum(
        reference * probability
        for (reference, _), probability in joint.items()
    )
    output_mean = sum(
        output * probability
        for (_, output), probability in joint.items()
    )
    product_mean = sum(
        reference * output * probability
        for (reference, output), probability in joint.items()
    )
    return (
        reference_mean,
        output_mean,
        product_mean - reference_mean * output_mean,
    )


def finite_models(fixture: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any]]:
    smoother = make_smoother(fixture)
    impulse = [0.0, 0.0, float(fixture["impulse_center"]), 0.0, 0.0]
    blurred = matvec(smoother, impulse)
    row_sums = [sum(row) for row in smoother]
    operator_valid = (
        all(value >= 0.0 for row in smoother for value in row)
        and all(abs(value - 1.0) <= 1e-15 for value in row_sums)
        and not vectors_close(impulse, blurred)
    )
    artifact = [
        value - low
        for value, low in zip(impulse, blurred, strict=True)
    ]
    reconstructed_impulse = [
        low + residue
        for low, residue in zip(blurred, artifact, strict=True)
    ]
    degradation_observation = json.dumps(
        {"A": impulse, "B": blurred},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    improvement_observation = json.dumps(
        {"A": reconstructed_impulse, "B": blurred},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    collision_operator_valid = (
        operator_valid
        and vectors_close(impulse, reconstructed_impulse)
        and degradation_observation == improvement_observation
    )

    collision_labels_opposite = (
        fixture["degradation_label"] != fixture["improvement_label"]
        and fixture["degradation_label"] == "prefer_A"
        and fixture["improvement_label"] == "prefer_B"
    )

    featureless = [float(value) for value in fixture["featureless_profile"]]
    featureless_blur = matvec(smoother, featureless)
    usm_amount = float(fixture["usm_amount"])
    featureless_usm = [
        value + usm_amount * (value - low)
        for value, low in zip(featureless, featureless_blur, strict=True)
    ]
    featureless_blur_usm_blind = (
        max(featureless) == min(featureless)
        and vectors_close(featureless, featureless_blur)
        and vectors_close(featureless, featureless_usm)
    )

    faithful_probability = float(fixture["faithful_signal_probability"])
    hallucination_probability = float(
        fixture["hallucination_signal_probability"]
    )
    faithful_joint = bernoulli_joint(
        faithful_probability,
        faithful_probability,
        coupled=fixture["reference_link"] == "same_latent",
    )
    hallucination_joint = bernoulli_joint(
        faithful_probability,
        hallucination_probability,
        coupled=False,
    )
    _, faithful_output_probability, faithful_reference_covariance = (
        joint_moments(faithful_joint)
    )
    _, hallucinated_output_probability, hallucination_reference_covariance = (
        joint_moments(hallucination_joint)
    )
    marginal_total_variation = 0.5 * (
        abs(
            (1.0 - faithful_output_probability)
            - (1.0 - hallucinated_output_probability)
        )
        + abs(
            faithful_output_probability - hallucinated_output_probability
        )
    )
    marginal_prior_collision = (
        0.0 < faithful_probability < 1.0
        and 0.0 < hallucination_probability < 1.0
        and marginal_total_variation <= 1e-15
    )

    reference_breaks_collision = (
        marginal_prior_collision
        and faithful_reference_covariance > 0.0
        and abs(hallucination_reference_covariance) <= 1e-15
    )

    checks = {
        "collision_operator_valid": collision_operator_valid,
        "collision_labels_opposite": collision_labels_opposite,
        "featureless_blur_usm_blind": featureless_blur_usm_blind,
        "marginal_prior_collision": marginal_prior_collision,
        "reference_breaks_collision": reference_breaks_collision,
    }
    derived = {
        "collision": {
            "A": impulse,
            "B": blurred,
            "A_minus_B": artifact,
            "improvement_world_reconstructed_A": reconstructed_impulse,
            "row_sums": row_sums,
            "observation_bytes_identical": (
                degradation_observation == improvement_observation
            ),
            "labels": [
                fixture["degradation_label"],
                fixture["improvement_label"],
            ],
        },
        "featureless": {
            "input": featureless,
            "blurred": featureless_blur,
            "usm": featureless_usm,
        },
        "generative_prior": {
            "faithful_output_probability": faithful_output_probability,
            "hallucinated_output_probability": (
                hallucinated_output_probability
            ),
            "marginal_total_variation": marginal_total_variation,
            "faithful_output_reference_covariance": (
                faithful_reference_covariance
            ),
            "hallucinated_output_reference_covariance": (
                hallucination_reference_covariance
            ),
        },
    }
    return checks, derived


def min_number(values: list[Any]) -> float:
    return min(float(value) for value in values)


def verify_sources(args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        name: Path(getattr(args, name))
        for name in DEFAULTS
    }
    fixture = read_json(paths["fixture"])
    m164_report = paths["m164_report"].read_text(encoding="utf-8")
    m168_report = paths["m168_report"].read_text(encoding="utf-8")
    m135 = read_json(paths["m135_commission"])
    m135_results = paths["m135_results"].read_text(encoding="utf-8")
    dominance = read_json(paths["dominance_commission"])
    m167 = read_json(paths["m167_admission"])
    m167_preregistration = paths["m167_preregistration"].read_text(
        encoding="utf-8"
    )
    archive_report = paths["archive_report"].read_text(encoding="utf-8")
    slanted_report = paths["slanted_report"].read_text(encoding="utf-8")
    manifest_report = paths["manifest_report"].read_text(encoding="utf-8")

    checks, derived = finite_models(fixture)

    checks["m164_output_only_scope"] = (
        M164_SCOPE in m164_report
        and "There is no stand-alone, two-render-output repair" in m164_report
    )
    checks["m168_distribution_free_scope"] = (
        M168_SCOPE in m168_report
        and "Model-conditional inference remains possible." in m168_report
    )

    information = m135["information_ratio_summaries"]
    transfer = m135["transfer_ratio_summaries"]
    m135_gates = m135["gates"]
    m135_checker = m135["checker_mutation_controls"]
    checks["m135_estimator_commissioned"] = (
        m135["status"] == "PASS"
        and len(m135_gates) == 25
        and all(value is True for value in m135_gates.values())
        and len(m135_checker) == 4
        and all(value is True for value in m135_checker.values())
    )
    checks["m135_blur_defect_direction"] = (
        float(information["blur"]["q95"]) < 1.0
        and float(information["blur"]["maximum"]) < 1.0
    )
    checks["m135_improvement_direction"] = (
        float(information["improvement"]["q05"]) > 1.0
        and float(information["improvement"]["minimum"]) > 1.0
    )
    checks["m135_usm_not_rewarded"] = (
        float(information["usm"]["maximum"]) <= 1.01
        and float(information["improvement"]["q05"])
        > float(information["usm"]["maximum"])
    )
    checks["m135_postblur_transfer_veto"] = (
        abs(float(information["post_blur"]["geometric_mean"]) - 1.0) <= 1e-12
        and float(transfer["post_blur"]["q95"]) < 0.98
    )
    checks["m135_averaging_veto"] = (
        float(information["averaging"]["q05"]) > 1.0
        and float(transfer["averaging"]["q95"]) < 0.98
        and int(m135["averaging_promotions"]) == 0
    )
    flat = m135["flat_control_ratio_summaries"]
    flat_worst = {
        "information": max(
            float(value["information"]["maximum"]) for value in flat.values()
        ),
        "reference": max(
            float(value["reference_repeatable_power"]["maximum"])
            for value in flat.values()
        ),
        "output": max(
            float(value["output_repeatable_power"]["maximum"])
            for value in flat.values()
        ),
    }
    checks["m135_flat_common_mode"] = (
        m135["common_flat_status_counts"] == {"FLAT_NULL_FAILED": 128}
        and m135["refusals"]["structured_flat"]["status"] == "FLAT_NULL_FAILED"
        and flat_worst["information"] <= 0.10
        and flat_worst["reference"] <= 0.25
        and flat_worst["output"] <= 0.10
    )

    dominance_checks = dominance["checks"]
    legitimate = dominance["legitimate"]
    checks["dominance_legitimate_moves"] = (
        dominance["status"] == "PASS"
        and dominance_checks["C3_legitimate_case_is_admitted"] is True
        and legitimate["status"] == "PASS"
        and min_number(legitimate["information_simultaneous_lcb"]) > 0.0
        and min_number(legitimate["transfer_simultaneous_lcb"]) > 0.0
    )
    weak = dominance["single_cell_violation"]
    checks["dominance_no_compensation"] = (
        dominance_checks["C8_strong_cells_do_not_compensate"] is True
        and weak["status"] == "UNMEASURED"
        and weak["failed_cells"] == [3]
        and min_number(weak["point"]["transfer_ratio"]) < 1.0
        and sum(float(value) for value in weak["point"]["transfer_ratio"])
        / len(weak["point"]["transfer_ratio"])
        > 1.08
    )
    common = dominance["improvement_shaped_common_mode"]
    checks["dominance_improvement_shaped_defect"] = (
        dominance_checks[
            "C13_charged_improvement_shaped_case_is_rejected"
        ]
        is True
        and common["contaminated_naive"]["status"] == "PASS"
        and common["contaminated_charged"]["status"] == "UNMEASURED"
        and common["contaminated_charged"]["failure"] == "COMMON_MODE_BOUND"
        and float(common["contaminated_naive_min_information_ratio"])
        > float(common["clean_min_information_ratio"])
        and float(common["contaminated_naive_min_transfer_ratio"])
        > float(common["clean_min_transfer_ratio"])
    )

    blinded_instances = m167["blinded_instances"]
    checks["m167_canary_bites"] = (
        m167["admission_verdict"] == "REJECTED_BY_BLINDED_ADMISSION"
        and len(blinded_instances) == 3
        and all(
            instance["P1_to_P6"]["verdict"]
            == "REJECTED_BY_SYNTHETIC_BATTERY"
            for instance in blinded_instances
        )
        and m167["commissioning_checks"][
            "cheating_canary_rejected_on_all_instances"
        ]
        is True
    )
    checks["m167_a6_fail_closed"] = (
        m167["admission_gates"]["A6_capability_sandbox"] is False
        and "real candidate admission remains fail-closed"
        in m167["sandbox_note"]
    )
    checks["m167_reference_schema_pending"] = (
        M167_REFERENCE_SCHEMA in m167_preregistration
    )
    checks["archive_route_closed"] = (
        "Status: **NO ARCHIVE-ONLY ROUTE;" in archive_report
        and "MATCHED_SETTINGS=0" in archive_report
    )

    tone_extrema = [
        float(information[name][bound])
        for name in ("gamma", "logistic")
        for bound in ("minimum", "maximum")
    ]
    pchip_max_relative_movement = max(
        abs(value - 1.0) for value in tone_extrema
    )
    checks["pchip_is_enabler_only"] = (
        PCHIP_SCOPE in slanted_report
        and pchip_max_relative_movement <= 0.000141
        and float(information["usm"]["maximum"]) <= 1.01
    )
    checks["physical_route_uncommissioned"] = (
        "Status: **PASS at estimator level; physical capture path not "
        "commissioned**"
        in m135_results
        and manifest_report.startswith("MANIFEST BLOCKED:")
        and int(dominance["captures_opened"]) == 0
    )

    derived.update(
        {
            "m135": {
                "gates_passed": sum(
                    value is True for value in m135_gates.values()
                ),
                "gates_total": len(m135_gates),
                "blur_q95_ratio": float(information["blur"]["q95"]),
                "improvement_q05_ratio": float(
                    information["improvement"]["q05"]
                ),
                "usm_maximum_ratio": float(information["usm"]["maximum"]),
                "postblur_information_geometric_mean": float(
                    information["post_blur"]["geometric_mean"]
                ),
                "postblur_transfer_q95_ratio": float(
                    transfer["post_blur"]["q95"]
                ),
                "averaging_information_q05_ratio": float(
                    information["averaging"]["q05"]
                ),
                "averaging_transfer_q95_ratio": float(
                    transfer["averaging"]["q95"]
                ),
                "averaging_promotions": int(m135["averaging_promotions"]),
                "common_flat_rejections": int(
                    m135["common_flat_status_counts"]["FLAT_NULL_FAILED"]
                ),
                "flat_worst_ratios": flat_worst,
                "pchip_max_relative_movement": (
                    pchip_max_relative_movement
                ),
            },
            "reference_dominance": {
                "minimum_information_lcb": min_number(
                    legitimate["information_simultaneous_lcb"]
                ),
                "minimum_transfer_lcb": min_number(
                    legitimate["transfer_simultaneous_lcb"]
                ),
                "weak_cell_transfer_ratio": min_number(
                    weak["point"]["transfer_ratio"]
                ),
                "weak_family_mean_transfer_ratio": (
                    sum(
                        float(value)
                        for value in weak["point"]["transfer_ratio"]
                    )
                    / len(weak["point"]["transfer_ratio"])
                ),
                "common_mode_clean_min_information_ratio": float(
                    common["clean_min_information_ratio"]
                ),
                "common_mode_naive_min_information_ratio": float(
                    common["contaminated_naive_min_information_ratio"]
                ),
                "common_mode_clean_min_transfer_ratio": float(
                    common["clean_min_transfer_ratio"]
                ),
                "common_mode_naive_min_transfer_ratio": float(
                    common["contaminated_naive_min_transfer_ratio"]
                ),
                "charged_status": common["contaminated_charged"]["status"],
                "charged_failure": common["contaminated_charged"]["failure"],
            },
            "m167": {
                "hidden_instances": len(blinded_instances),
                "hidden_instances_rejected": sum(
                    instance["P1_to_P6"]["verdict"]
                    == "REJECTED_BY_SYNTHETIC_BATTERY"
                    for instance in blinded_instances
                ),
                "A6_capability_sandbox": m167["admission_gates"][
                    "A6_capability_sandbox"
                ],
            },
        }
    )

    ordered_names = [
        "collision_operator_valid",
        "collision_labels_opposite",
        "featureless_blur_usm_blind",
        "marginal_prior_collision",
        "reference_breaks_collision",
        "m164_output_only_scope",
        "m168_distribution_free_scope",
        "m135_estimator_commissioned",
        "m135_blur_defect_direction",
        "m135_improvement_direction",
        "m135_usm_not_rewarded",
        "m135_postblur_transfer_veto",
        "m135_averaging_veto",
        "m135_flat_common_mode",
        "dominance_legitimate_moves",
        "dominance_no_compensation",
        "dominance_improvement_shaped_defect",
        "m167_canary_bites",
        "m167_a6_fail_closed",
        "m167_reference_schema_pending",
        "archive_route_closed",
        "pchip_is_enabler_only",
        "physical_route_uncommissioned",
    ]
    ordered_checks = {name: bool(checks[name]) for name in ordered_names}
    passed = sum(ordered_checks.values())
    all_green = passed == len(ordered_checks)
    return {
        "schema": 1,
        "status": "PASS" if all_green else "FAIL",
        "verdict": BASELINE_VERDICT if all_green else FAILED_VERDICT,
        "counts": {
            "checks_run": len(ordered_checks),
            "checks_passed": passed,
            "checks_failed": len(ordered_checks) - passed,
        },
        "checks": ordered_checks,
        "derived": derived,
        "sources": {
            name: {
                "path": display_path(path),
                "sha256": sha256(path),
            }
            for name, path in paths.items()
        },
    }


def main() -> int:
    args = parse_args()
    try:
        result = verify_sources(args)
    except Exception as exc:
        result = {
            "schema": 1,
            "status": "ERROR",
            "verdict": FAILED_VERDICT,
            "error": f"{type(exc).__name__}: {exc}",
        }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8", newline="\n")
    sys.stdout.write(encoded)
    return 0 if result.get("status") == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
