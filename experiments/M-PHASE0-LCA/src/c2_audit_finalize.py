"""Finalize the frozen C2 audit after its tone-normalised arm declined."""

from __future__ import annotations

import copy
import json
import math
import warnings
from pathlib import Path

import numpy as np

import c2_audit as audit


PRODUCER_COMMIT = "cb66893eabf3822ff0485f9fbc9d9c2319a81e8c"


def finite_or_none(value):
    if isinstance(value, dict):
        return {key: finite_or_none(item) for key, item in value.items()}
    if isinstance(value, list):
        return [finite_or_none(item) for item in value]
    if isinstance(value, tuple):
        return [finite_or_none(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def legacy_path(stack: str) -> Path:
    return (
        audit.AUDIT_OUT
        / "legacy"
        / "json"
        / f"b1_{stack}_main.npz"
    )


def normalised_path(stack: str, variant: str = "normalised") -> Path:
    return audit.AUDIT_OUT / "normalised" / f"{stack}-{variant}.npz"


def loss_mapping_pass(summary: dict, target: dict) -> bool:
    return (
        abs(summary["loss_r"] - target["loss_r"]) <= 0.0025
        and abs(summary["loss_b"] - target["loss_b"]) <= 0.0025
    )


def focus_pass(summary: dict, target: dict) -> bool:
    null_ci = summary["delta_null_ci95"]
    null_half = max(
        abs(null_ci[0] - summary["delta_null"]),
        abs(null_ci[1] - summary["delta_null"]),
    )
    return (
        abs(summary["delta_r"] - target["delta_r"]) <= 0.05
        and abs(summary["delta_b"] - target["delta_b"]) <= 0.05
        and summary["delta_r"] < 0.0
        and summary["delta_b"] < 0.0
        and abs(summary["delta_null"]) + null_half < 0.125
    )


def available_tone_summary(summary: dict) -> bool:
    return (
        summary["tiles_used"] >= 2
        and summary["delta_r"] is not None
        and summary["delta_b"] is not None
        and summary["loss_r"] is not None
        and summary["loss_b"] is not None
    )


def derive_decision(result: dict) -> str:
    return (
        "GO"
        if all(result["decision_gates"].values())
        else "STOP"
    )


def audit_result(result: dict) -> list[str]:
    errors = []
    if result["decision"] != derive_decision(result):
        errors.append("decision does not follow registered gates")
    if set(result["legacy_reproduction"]) != set(audit.STACKS):
        errors.append("legacy stack identity set drift")
    if set(result["tone_normalised"]) != set(audit.STACKS):
        errors.append("tone stack identity set drift")
    derived_tone_count = sum(
        available_tone_summary(summary)
        for summary in result["tone_normalised"].values()
    )
    if result["tone_normalised_available_stacks"] != derived_tone_count:
        errors.append("tone-valid stack count drift")
    if result["claim_type"] != (
        "longitudinal/axial focus displacement, not lateral radial scale"
    ):
        errors.append("aberration type drift")
    return errors


def main() -> int:
    commission_path = audit.OUT / "c2-audit-commission.json"
    commission = json.loads(commission_path.read_text(encoding="utf-8"))
    inventories = {stack: audit.inventory(stack) for stack in audit.STACKS}

    legacy = {}
    details = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for index, stack in enumerate(audit.STACKS):
            summary, detail = audit.independent_summary(
                legacy_path(stack), seed=audit.SEED + 100 * index
            )
            target = audit.TARGETS[stack]
            legacy[stack] = {
                "target": target,
                "measured": summary,
                "focus_passes": focus_pass(summary, target),
                "registered_loss_mapping_passes": loss_mapping_pass(
                    summary, target
                ),
            }
            details[stack] = detail

    measured_r = sorted(
        row["measured"]["loss_r"] for row in legacy.values()
    )
    measured_b = sorted(
        row["measured"]["loss_b"] for row in legacy.values()
    )
    target_r = sorted(row["loss_r"] for row in audit.TARGETS.values())
    target_b = sorted(row["loss_b"] for row in audit.TARGETS.values())
    multiset_errors = {
        "R": [
            abs(measured - expected)
            for measured, expected in zip(measured_r, target_r, strict=True)
        ],
        "B": [
            abs(measured - expected)
            for measured, expected in zip(measured_b, target_b, strict=True)
        ],
    }
    published_multiset_passes = (
        max(multiset_errors["R"] + multiset_errors["B"]) <= 0.0025
    )

    tone = {}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for index, stack in enumerate(audit.STACKS):
            summary, _ = audit.independent_summary(
                normalised_path(stack),
                seed=audit.SEED + 1000 + 100 * index,
            )
            tone[stack] = finite_or_none(summary)
    available = [
        stack
        for stack, summary in tone.items()
        if available_tone_summary(summary)
    ]

    gamma = {}
    for variant in ("gamma_0p8", "gamma_1p2"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            summary, _ = audit.independent_summary(
                normalised_path("lavendar-cpl", variant),
                seed=audit.SEED + 2000,
            )
        gamma[variant] = finite_or_none(summary)

    radial = {
        stack: audit.radial_intercept(
            details[stack], audit.SEED + 5000 + index
        )
        for index, stack in enumerate(("lavendar-cpl", "coffee-bean"))
    }
    retractions = audit.retraction_audit()

    cache_identity = {}
    for stack in audit.STACKS:
        expected_fingerprint = audit.cache_fingerprint(
            stack, inventories[stack]
        )
        normalised_records = {}
        variants = ["normalised"]
        if stack == "lavendar-cpl":
            variants += ["gamma_0p8", "gamma_1p2"]
        for variant in variants:
            path = normalised_path(stack, variant)
            with np.load(path, allow_pickle=True) as source:
                embedded = str(source["fingerprint"])
            normalised_records[variant] = {
                "path": str(path),
                "sha256": audit.file_sha256(path),
                "embedded_fingerprint": embedded,
                "matches_frozen_producer_and_inputs": (
                    embedded == expected_fingerprint
                ),
            }
        legacy_file = legacy_path(stack)
        cache_identity[stack] = {
            "legacy": {
                "path": str(legacy_file),
                "sha256": audit.file_sha256(legacy_file),
            },
            "normalised": normalised_records,
        }

    decision_gates = {
        "commission_green": bool(commission["summary"]["all_passed"]),
        "all_focus_offsets_and_nulls_reproduced": all(
            row["focus_passes"] for row in legacy.values()
        ),
        "published_loss_multiset_reproduced": published_multiset_passes,
        "registered_per_stack_loss_mapping_reproduced": all(
            row["registered_loss_mapping_passes"]
            for row in legacy.values()
        ),
        "tone_normalised_metric_valid_on_all_four_stacks": (
            len(available) == len(audit.STACKS)
        ),
        "gamma_diagnostic_valid_on_lavendar": all(
            available_tone_summary(summary) for summary in gamma.values()
        ),
        "axial_centre_intercepts_pass": all(
            row["passes_axial_gate"] for row in radial.values()
        ),
        "no_axial_or_forfeit_retraction": not retractions[
            "axial_or_forfeit_retraction_found"
        ],
        "all_cache_fingerprints_match": all(
            record["matches_frozen_producer_and_inputs"]
            for stack in cache_identity.values()
            for record in stack["normalised"].values()
        ),
    }
    result = {
        "schema": 1,
        "producer_commit": PRODUCER_COMMIT,
        "question": (
            "Does the prior finding, as dispatched, support building the "
            "axial channel-epoch correction now?"
        ),
        "claim_type": (
            "longitudinal/axial focus displacement, not lateral radial scale"
        ),
        "decision_gates": decision_gates,
        "decision": "GO" if all(decision_gates.values()) else "STOP",
        "commission": {
            "path": str(commission_path),
            "sha256": audit.file_sha256(commission_path),
            "summary": commission["summary"],
        },
        "capture_inventory": inventories,
        "cache_identity": cache_identity,
        "legacy_reproduction": legacy,
        "published_loss_multiset": {
            "measured_R": measured_r,
            "target_R": target_r,
            "measured_B": measured_b,
            "target_B": target_b,
            "absolute_errors": multiset_errors,
            "passes": published_multiset_passes,
        },
        "preregistration_mapping_defect": (
            "BUILD-CHROMA printed each channel's four gains as an ordered "
            "range without associating values to stack names. The frozen "
            "preregistration incorrectly assigned that order to its stack "
            "rows. The measured multisets reproduce, but the registered "
            "per-stack mapping gate therefore fails and is not rewritten."
        ),
        "tone_normalised": tone,
        "tone_normalised_available_stacks": len(available),
        "tone_normalised_available_stack_names": available,
        "gamma_diagnostic": gamma,
        "tone_gate_failure": (
            "The affine-invariant E/variance focus curves retained enough "
            "valid points/tiles only on coffee-bean. Lavendar, couch, and "
            "bee had zero accepted tiles; both lavendar gamma arms also had "
            "zero. The audit cannot establish a tone-invariant four-stack "
            "payoff and the preregistered response is STOP."
        ),
        "radial_axial_discriminator": radial,
        "retraction_audit": retractions,
        "what_survives": (
            "All four raw linear through-focus offsets and same-wavelength "
            "nulls reproduce; the centre intercepts independently identify "
            "longitudinal/axial rather than lateral CA."
        ),
        "what_does_not_survive": (
            "The dispatch's lateral-CA label and its promotion of raw Sobel "
            "forfeit to a commissioned, tone-invariant recoverable output "
            "gain do not survive this audit."
        ),
        "required_before_build": [
            (
                "preregister and commission a tone-invariant through-focus "
                "payoff metric that retains valid peaks on all four stacks"
            ),
            (
                "freeze the correct per-stack legacy gain association rather "
                "than inferring an order from a printed range"
            ),
            (
                "then require zero-output identity and wrong-sign harm in an "
                "end-to-end flagged render before accepting a correction"
            ),
        ],
    }

    baseline_errors = audit_result(result)
    plants = []
    mutations = []

    changed_decision = copy.deepcopy(result)
    changed_decision["decision"] = "GO"
    mutations.append(("FP1_falsify_STOP_as_GO", changed_decision))

    changed_tone_count = copy.deepcopy(result)
    changed_tone_count["tone_normalised_available_stacks"] = 4
    mutations.append(("FP2_falsify_tone_valid_stack_count", changed_tone_count))

    missing_stack = copy.deepcopy(result)
    missing_stack["legacy_reproduction"].pop("bee-2-cpl")
    mutations.append(("FP3_delete_required_legacy_stack", missing_stack))

    changed_type = copy.deepcopy(result)
    changed_type["claim_type"] = "lateral chromatic aberration"
    mutations.append(("FP4_relabel_axial_as_lateral", changed_type))

    for name, mutated in mutations:
        plants.append({"name": name, "red": bool(audit_result(mutated))})
    verification = {
        "control_green": not baseline_errors,
        "control_errors": baseline_errors,
        "plants": plants,
        "all_passed": (
            not baseline_errors and all(plant["red"] for plant in plants)
        ),
    }
    result["self_verification"] = verification
    audit.write_json(audit.OUT / "c2-audit.json", finite_or_none(result))

    print("C2 AUDIT FINAL")
    for stack, row in legacy.items():
        measured = row["measured"]
        print(
            f"  {stack}: dR={measured['delta_r']:+.4f}, "
            f"dB={measured['delta_b']:+.4f}, "
            f"R/B={100*measured['loss_r']:.2f}%/"
            f"{100*measured['loss_b']:.2f}%"
        )
    print(
        f"  loss multiset reproduced={published_multiset_passes}; "
        f"tone-valid stacks={len(available)}/4; "
        f"axial intercepts={all(x['passes_axial_gate'] for x in radial.values())}"
    )
    print(
        f"  verifier control={'GREEN' if not baseline_errors else 'FAIL'}; "
        f"plants={sum(p['red'] for p in plants)}/{len(plants)} RED"
    )
    print(f"DECISION: {result['decision']}")
    return 0 if verification["all_passed"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
