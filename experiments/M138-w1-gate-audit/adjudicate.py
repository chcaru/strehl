#!/usr/bin/env python3
"""Reference adjudicator for the preregistered corrected W1 gate.

This file does not render or score a campaign.  It validates the frozen
contract and applies its deterministic verdict rule to a supplied result.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT_PATH = HERE / "corrected-gate-contract.json"
PREREG_PATH = HERE / "corrected-gate-preregistration.md"


SOURCE_ANCHORS = (
    ("experiments/PHASE1-DESIGN/measure.py", 29, 31, "FLAT_BAR = 0.90"),
    ("experiments/PHASE1-DESIGN/measure.py", 129, 141, "def exponent_at"),
    ("experiments/PHASE1-DESIGN/measure.py", 171, 180, "winner = np.argmax"),
    ("experiments/PHASE1-DESIGN/measure.py", 235, 250, "va_pyr = R.gaussian_pyramid"),
    ("experiments/PHASE1-DESIGN/measure.py", 407, 422, "weights[:, below] = 1.0"),
    ("experiments/PHASE1-DESIGN/measure.py", 568, 575, "if survivors:"),
    ("experiments/PHASE1-DESIGN/reference.py", 625, 633, "if band >= 4"),
    ("experiments/PHASE1-DESIGN/reference.py", 666, 727, "worst_frame_by_band"),
    (
        "experiments/PHASE1-DESIGN/reference.py",
        1052,
        1064,
        '"overall": coverage["overall_by_band"]',
    ),
    (
        "experiments/PHASE1-DESIGN/reference.py",
        1080,
        1134,
        "laplacian_pyramid(transformed, 1)[0]",
    ),
    ("experiments/PHASE1-DESIGN/reference.py", 1143, 1185, "detail-cross-power-metric"),
    ("crates/strehl-core/src/pyramid.rs", 372, 384, "pub fn build_gaussian"),
    ("crates/strehl-core/src/merge.rs", 421, 427, "maximum over N frames"),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        7,
        12,
        "does not qualify a physical",
    ),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        26,
        53,
        "They may never create a win",
    ),
    (
        "experiments/M135-detail-instrument/PREREGISTRATION.md",
        127,
        149,
        "Planted optical improvement",
    ),
    ("experiments/M135-detail-instrument/instrument.py", 152, 218, '"status": "OK"'),
    ("docs/research/M62-sqrt-n.md", 32, 45, "exactly √N"),
    ("docs/research/M62-sqrt-n.md", 64, 70, "real branch is not run"),
    ("docs/proposals/2026-09-phase1-design.md", 312, 316, "Width match"),
    ("docs/proposals/2026-09-phase1-design.md", 340, 350, "No common value means"),
    (
        "experiments/PHASE1-DESIGN/PREREGISTRATION.md",
        167,
        203,
        "Only width survivors are rendered",
    ),
    (
        "experiments/PHASE1-DESIGN/results/gate.json",
        1,
        1,
        '"seconds":263.6871026000008',
    ),
    ("experiments/PHASE1-DESIGN/results/run.json", 1, 1, '"pareto_rendered":false'),
)


REQUIRED_DOCUMENT_TEXT = (
    "# M138 corrected W1 gate preregistration",
    "Width is diagnostic, never dispositive",
    "BLOCKED_DETAIL_INSTRUMENT",
    "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT",
    "PHASE1_REFUTED_HOLDOUT",
    "PHASE1_GO",
    "Pooled-only coverage gating",
    "Positive-`q` commissioning",
    "All-band Poisson–Gaussian control",
    "Approximate variance propagation",
    "Selected-winner and stack-size calibration",
    "planted optical improvement",
    "Wall-clock and contention",
    "4,095",
    "8,192",
    "16 hours",
    "24 wall-hours",
    "Could not determine",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tau_keys(contract: dict[str, Any]) -> list[str]:
    cfg = contract["threshold_coordinate"]
    start = int(round(float(cfg["grid_start"]) * 100))
    stop = int(round(float(cfg["grid_stop"]) * 100))
    step = int(round(float(cfg["grid_step"]) * 100))
    if (start, stop, step) != (0, 100, 1):
        raise ValueError("the frozen tau grid must be 0.00 through 1.00 by 0.01")
    return [f"{value / 100:.2f}" for value in range(start, stop + 1, step)]


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema") != 1:
        raise ValueError("unsupported contract schema")
    if contract.get("status") != "PREREGISTERED_NO_CAMPAIGN_EXECUTED":
        raise ValueError("contract status no longer denotes an unrun preregistration")
    binding = contract["detail_instrument"]
    if binding.get("binding_state") not in {"UNBOUND", "BOUND"}:
        raise ValueError("invalid M135 binding state")
    if binding["binding_state"] == "BOUND":
        for field in (
            "preregistration_sha256",
            "physical_commissioning_sha256",
            "checker_sha256",
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", str(binding.get(field, ""))):
                raise ValueError(f"bound M135 contract lacks a valid {field}")
    ledgers = contract["capture_ledgers"]
    if ledgers.get("binding_state") not in {"UNBOUND", "BOUND"}:
        raise ValueError("invalid capture-ledger binding state")
    if ledgers["binding_state"] == "BOUND":
        if not valid_ledger(ledgers.get("development", {})):
            raise ValueError("bound development ledger is invalid")
        if not valid_ledger(ledgers.get("holdout", {})):
            raise ValueError("bound holdout ledger is invalid")
    if contract["output_gate"].get("width_role") != "DIAGNOSTIC_ONLY":
        raise ValueError("width was promoted back into the gate")
    if tau_keys(contract)[0] != "0.00" or tau_keys(contract)[-1] != "1.00":
        raise ValueError("tau endpoints changed")
    if int(contract["threshold_coordinate"]["robust_neighbour_steps"]) != 1:
        raise ValueError("robust-neighbour rule changed")
    required_bands = contract["standardisation"]["required_band_indices"]
    if required_bands != list(range(7)):
        raise ValueError("all seven bands are required")
    checkpoints = contract["standardisation"]["coverage_checkpoints"]
    if checkpoints != [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]:
        raise ValueError("coverage checkpoints changed")
    if int(contract["standardisation"]["calibration_replicates"]) != 4095:
        raise ValueError("calibration replicate count changed")
    if int(contract["standardisation"]["validation_replicates"]) != 8192:
        raise ValueError("validation replicate count changed")
    if float(contract["standardisation"]["maximum_absolute_admission_error"]) != 0.03:
        raise ValueError("calibration error bar changed")
    if (
        int(contract["standardisation"]["physical_null_minimum_sites_per_stratum"])
        != 256
    ):
        raise ValueError("physical null site floor changed")
    if float(contract["standardisation"]["physical_null_interval_confidence"]) != 0.99:
        raise ValueError("physical null confidence changed")
    expected_bins = [
        (0.0, 0.25, 0.0),
        (0.25, 1.0, 0.5),
        (1.0, 4.0, 2.0),
        (4.0, 16.0, 8.0),
        (16.0, None, 32.0),
    ]
    bins = [
        (
            float(row["lower_inclusive"]),
            None if row["upper_exclusive"] is None else float(row["upper_exclusive"]),
            float(row["anchor"]),
        )
        for row in contract["standardisation"]["q_over_f_bins"]
    ]
    if bins != expected_bins:
        raise ValueError("q/F bins changed")
    if float(contract["noise_instrument"]["power_ratio_upper95"]) != 0.90:
        raise ValueError("temporal-noise output bar changed")
    if float(contract["cost"]["exclusive_wall_hours"]) != 16.0:
        raise ValueError("exclusive scheduling estimate changed")
    if float(contract["cost"]["shared_host_wall_hours"]) != 24.0:
        raise ValueError("shared-host scheduling estimate changed")


def validate_sources(contract: dict[str, Any]) -> None:
    for relative, expected in contract["source_baseline"]["files"].items():
        path = ROOT / Path(relative)
        if not path.exists():
            raise FileNotFoundError(f"missing pinned source: {relative}")
        got = sha256(path)
        if got != expected:
            raise ValueError(f"source hash drift: {relative}: {got} != {expected}")
    for relative, first, last, needle in SOURCE_ANCHORS:
        path = ROOT / Path(relative)
        lines = path.read_text(encoding="utf-8").splitlines()
        if first < 1 or last > len(lines):
            raise ValueError(f"citation range outside file: {relative}:{first}-{last}")
        text = "\n".join(lines[first - 1 : last])
        if needle not in text:
            raise ValueError(
                f"citation anchor missing: {relative}:{first}-{last}: {needle!r}"
            )


def validate_document() -> None:
    text = PREREG_PATH.read_text(encoding="utf-8")
    collapsed = " ".join(text.split())
    for required in REQUIRED_DOCUMENT_TEXT:
        if " ".join(required.split()) not in collapsed:
            raise ValueError(f"preregistration is missing required text: {required!r}")
    for relative, first, last, _ in SOURCE_ANCHORS:
        citation = f"`{relative}:{first}-{last}`"
        if citation not in text:
            raise ValueError(f"preregistration is missing citation {citation}")
    if re.search(r"(?<!\[INHERITED\] )±5%", text):
        raise ValueError("an untagged inherited ±5% value remains")


def standardisation_passes(result: dict[str, Any], contract: dict[str, Any]) -> bool:
    standard = result.get("standardisation", {})
    required_bands = set(contract["standardisation"]["required_band_indices"])
    anchors = contract["standardisation"]["q_over_f_anchors"]
    max_error = float(contract["standardisation"]["maximum_absolute_admission_error"])
    manifests = standard.get("manifests", [])
    if not manifests:
        return False
    manifest_sizes: dict[str, int] = {}
    for manifest in manifests:
        digest = str(manifest.get("sha256", ""))
        stack_size = int(manifest.get("stack_size", -1))
        if (
            not re.fullmatch(r"[0-9a-f]{64}", digest)
            or stack_size < 2
            or digest in manifest_sizes
        ):
            return False
        manifest_sizes[digest] = stack_size
    strata = standard.get("strata", [])
    covered = {
        (
            str(row.get("manifest_sha256", "")),
            int(row.get("frame_ordinal", -1)),
            int(row.get("band", -1)),
            float(row.get("q_over_f_anchor", math.nan)),
        )
        for row in strata
    }
    required = {
        (digest, frame, band, float(anchor))
        for digest, stack_size in manifest_sizes.items()
        for frame in range(stack_size)
        for band in required_bands
        for anchor in anchors
    }
    focus_power = standard.get("focus_offset_power", [])
    offsets = [float(row.get("offset_sigma", math.nan)) for row in focus_power]
    intervals_separate = all(
        float(next_row.get("upper99", math.inf))
        < float(previous.get("lower99", -math.inf))
        for previous, next_row in zip(focus_power, focus_power[1:])
    )
    return bool(
        standard.get("status") == "PASS"
        and int(standard.get("calibration_replicates", -1))
        == int(contract["standardisation"]["calibration_replicates"])
        and int(standard.get("validation_replicates", -1))
        == int(contract["standardisation"]["validation_replicates"])
        and len(strata) == len(required)
        and covered == required
        and all(
            float(row.get("maximum_absolute_admission_error", math.inf)) <= max_error
            for row in strata
        )
        and set(standard.get("poisson_gaussian_bands", [])) == required_bands
        and int(standard.get("gain_modes", -1))
        == int(contract["standardisation"]["required_gain_modes"])
        and int(standard.get("signal_quantiles", -1))
        == int(contract["standardisation"]["required_signal_quantiles"])
        and standard.get("physical_null_status") == "PASS"
        and int(standard.get("physical_null_minimum_sites", -1))
        >= int(contract["standardisation"]["physical_null_minimum_sites_per_stratum"])
        and standard.get("physical_null_all_strata_pass") is True
        and standard.get("selected_winner_exact_stack_size") is True
        and standard.get("pooled_only") is False
        and offsets
        == [
            float(value)
            for value in contract["standardisation"]["focus_offset_sigma_anchors"]
        ]
        and intervals_separate
    )


def commissioning_passes(result: dict[str, Any], contract: dict[str, Any]) -> bool:
    flags = result.get("commissioning", {})
    return all(
        flags.get(name) is True
        for name in contract["output_gate"]["required_commissioning_flags"]
    )


def detail_binding_passes(result: dict[str, Any], contract: dict[str, Any]) -> bool:
    expected = contract["detail_instrument"]
    if expected.get("binding_state") != "BOUND":
        return False
    binding = result.get("detail_binding", {})
    return bool(
        binding.get("status") == "PASS"
        and binding.get("physical_commissioning_status") == "PASS"
        and binding.get("preregistration_sha256")
        == expected.get("preregistration_sha256")
        and binding.get("physical_commissioning_sha256")
        == expected.get("physical_commissioning_sha256")
        and binding.get("checker_sha256") == expected.get("checker_sha256")
    )


def valid_ledger(ledger: dict[str, Any]) -> bool:
    for name in ("detail", "noise", "hull"):
        values = ledger.get(name)
        if (
            not isinstance(values, list)
            or not values
            or len(values) != len(set(values))
            or any(not isinstance(value, str) or not value for value in values)
        ):
            return False
    return True


def arm_passes(
    arm: dict[str, Any], ledger: dict[str, Any], contract: dict[str, Any]
) -> bool:
    if arm.get("finite") is not True or arm.get("postfilter_identity") is not True:
        return False
    detail = arm.get("detail_pass_by_capture", {})
    if set(detail) != set(ledger["detail"]) or not all(detail.values()):
        return False
    hull = arm.get("maximum_hull_excess_dn_by_capture", {})
    if set(hull) != set(ledger["hull"]):
        return False
    hull_bar = float(contract["output_gate"]["maximum_hull_excess_dn"])
    if not all(
        math.isfinite(float(value)) and 0 <= float(value) <= hull_bar
        for value in hull.values()
    ):
        return False
    noise = arm.get("noise_power_upper95_by_capture", {})
    if set(noise) != set(ledger["noise"]):
        return False
    required_planes = contract["noise_instrument"]["cfa_planes"]
    bar = float(contract["noise_instrument"]["power_ratio_upper95"])
    for capture in ledger["noise"]:
        values = noise[capture]
        if set(values) != set(required_planes):
            return False
        if not all(
            math.isfinite(float(values[plane])) and 0 < float(values[plane]) <= bar
            for plane in required_planes
        ):
            return False
    return True


def adjudicate(result: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    verdicts = contract["verdicts"]
    if result.get("seal_valid") is not True:
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "seal or input validation failed",
        }
    if not detail_binding_passes(result, contract):
        return {
            "verdict": verdicts["blocked_detail"],
            "reason": "physical M135 binding is absent or invalid",
        }
    if not standardisation_passes(result, contract):
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "standardisation commissioning failed",
        }
    if not commissioning_passes(result, contract):
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "bidirectional commissioning failed",
        }

    keys = tau_keys(contract)
    expected_ledgers = contract["capture_ledgers"]
    if expected_ledgers.get("binding_state") != "BOUND":
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "capture ledgers are unbound",
        }
    ledger = result.get("development_ledger", {})
    if not valid_ledger(ledger) or ledger != expected_ledgers.get("development"):
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "development ledger is invalid",
        }
    arms = result.get("development_arms", {})
    if set(arms) != set(keys):
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "development grid is incomplete",
        }
    passing = {
        index
        for index, key in enumerate(keys)
        if arm_passes(arms[key], ledger, contract)
    }
    radius = int(contract["threshold_coordinate"]["robust_neighbour_steps"])
    centres = [
        index
        for index in range(radius, len(keys) - radius)
        if all(index + offset in passing for offset in range(-radius, radius + 1))
    ]
    if not centres:
        return {
            "verdict": verdicts["refuted_development"],
            "reason": "no robust global output-quality operating point",
            "passing_tau": [keys[index] for index in sorted(passing)],
        }

    selected_key = keys[max(centres)]
    holdout = result.get("holdout")
    if holdout is None:
        return {
            "verdict": verdicts["awaiting_holdout"],
            "selected_tau": selected_key,
        }
    if holdout.get("tau") != selected_key:
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "holdout used a different tau",
        }
    holdout_ledger = holdout.get("ledger", {})
    if not valid_ledger(holdout_ledger) or holdout_ledger != expected_ledgers.get(
        "holdout"
    ):
        return {
            "verdict": verdicts["invalid_instrument"],
            "reason": "holdout ledger is invalid",
        }
    if not arm_passes(holdout.get("arm", {}), holdout_ledger, contract):
        return {
            "verdict": verdicts["refuted_holdout"],
            "selected_tau": selected_key,
        }
    return {"verdict": verdicts["go"], "selected_tau": selected_key}


def passing_arm() -> dict[str, Any]:
    return {
        "finite": True,
        "postfilter_identity": True,
        "detail_pass_by_capture": {"detail-development": True},
        "maximum_hull_excess_dn_by_capture": {
            "detail-development": 0.0,
            "noise-development": 0.0,
        },
        "noise_power_upper95_by_capture": {
            "noise-development": {"R": 0.80, "G1": 0.80, "G2": 0.80, "B": 0.80}
        },
        "width_diagnostics": {"arbitrary": "ignored by verdict"},
    }


def failing_arm() -> dict[str, Any]:
    arm = passing_arm()
    arm["detail_pass_by_capture"]["detail-development"] = False
    return arm


def base_fixture(contract: dict[str, Any]) -> dict[str, Any]:
    keys = tau_keys(contract)
    arms = {key: failing_arm() for key in keys}
    for key in ("0.40", "0.41", "0.42"):
        arms[key] = passing_arm()
    manifest_sha = "d" * 64
    stack_size = 2
    strata = [
        {
            "manifest_sha256": manifest_sha,
            "frame_ordinal": frame,
            "band": band,
            "q_over_f_anchor": anchor,
            "maximum_absolute_admission_error": 0.02,
        }
        for frame in range(stack_size)
        for band in contract["standardisation"]["required_band_indices"]
        for anchor in contract["standardisation"]["q_over_f_anchors"]
    ]
    return {
        "seal_valid": True,
        "detail_binding": {
            "status": "PASS",
            "physical_commissioning_status": "PASS",
            "preregistration_sha256": "a" * 64,
            "checker_sha256": "b" * 64,
        },
        "standardisation": {
            "status": "PASS",
            "calibration_replicates": contract["standardisation"][
                "calibration_replicates"
            ],
            "validation_replicates": contract["standardisation"][
                "validation_replicates"
            ],
            "manifests": [{"sha256": manifest_sha, "stack_size": stack_size}],
            "strata": strata,
            "poisson_gaussian_bands": contract["standardisation"][
                "required_band_indices"
            ],
            "gain_modes": contract["standardisation"]["required_gain_modes"],
            "signal_quantiles": contract["standardisation"][
                "required_signal_quantiles"
            ],
            "physical_null_status": "PASS",
            "physical_null_minimum_sites": contract["standardisation"][
                "physical_null_minimum_sites_per_stratum"
            ],
            "physical_null_all_strata_pass": True,
            "selected_winner_exact_stack_size": True,
            "pooled_only": False,
            "focus_offset_power": [
                {"offset_sigma": 0.0, "lower99": 0.94, "upper99": 0.96},
                {"offset_sigma": 1.0, "lower99": 0.74, "upper99": 0.76},
                {"offset_sigma": 2.0, "lower99": 0.44, "upper99": 0.46},
                {"offset_sigma": 4.0, "lower99": 0.04, "upper99": 0.06},
            ],
        },
        "commissioning": {
            name: True
            for name in contract["output_gate"]["required_commissioning_flags"]
        },
        "development_ledger": {
            "detail": ["detail-development"],
            "noise": ["noise-development"],
            "hull": ["detail-development", "noise-development"],
        },
        "development_arms": arms,
    }


def run_self_test(contract: dict[str, Any]) -> None:
    assert (
        adjudicate(base_fixture(contract), contract)["verdict"]
        == "BLOCKED_DETAIL_INSTRUMENT"
    )

    bound_contract = copy.deepcopy(contract)
    bound_contract["detail_instrument"].update(
        {
            "binding_state": "BOUND",
            "preregistration_sha256": "a" * 64,
            "physical_commissioning_sha256": "c" * 64,
            "checker_sha256": "b" * 64,
        }
    )
    ledger = {
        "detail": ["detail-development"],
        "noise": ["noise-development"],
        "hull": ["detail-development", "noise-development"],
    }
    bound_contract["capture_ledgers"] = {
        "binding_state": "BOUND",
        "development": ledger,
        "holdout": ledger,
    }
    fixture = base_fixture(bound_contract)
    fixture["detail_binding"]["physical_commissioning_sha256"] = "c" * 64
    got = adjudicate(fixture, bound_contract)
    assert got == {"verdict": "AWAITING_HOLDOUT", "selected_tau": "0.41"}, got

    with_holdout = copy.deepcopy(fixture)
    with_holdout["holdout"] = {
        "tau": "0.41",
        "ledger": fixture["development_ledger"],
        "arm": passing_arm(),
    }
    assert adjudicate(with_holdout, bound_contract)["verdict"] == "PHASE1_GO"

    width_mutation = copy.deepcopy(with_holdout)
    for arm in width_mutation["development_arms"].values():
        arm["width_diagnostics"] = {"legacy_ratio": 1000000.0}
    assert adjudicate(width_mutation, bound_contract) == adjudicate(
        with_holdout, bound_contract
    )

    blocked = copy.deepcopy(fixture)
    blocked["detail_binding"]["status"] = "UNBOUND"
    assert adjudicate(blocked, bound_contract)["verdict"] == "BLOCKED_DETAIL_INSTRUMENT"

    invalid_standard = copy.deepcopy(fixture)
    invalid_standard["standardisation"]["strata"][0][
        "maximum_absolute_admission_error"
    ] = 0.031
    assert (
        adjudicate(invalid_standard, bound_contract)["verdict"] == "INSTRUMENT_INVALID"
    )

    missing_frame_stratum = copy.deepcopy(fixture)
    missing_frame_stratum["standardisation"]["strata"].pop()
    assert (
        adjudicate(missing_frame_stratum, bound_contract)["verdict"]
        == "INSTRUMENT_INVALID"
    )

    missing_pg_band = copy.deepcopy(fixture)
    missing_pg_band["standardisation"]["poisson_gaussian_bands"].pop()
    assert (
        adjudicate(missing_pg_band, bound_contract)["verdict"] == "INSTRUMENT_INVALID"
    )

    failed_physical_null = copy.deepcopy(fixture)
    failed_physical_null["standardisation"]["physical_null_all_strata_pass"] = False
    assert (
        adjudicate(failed_physical_null, bound_contract)["verdict"]
        == "INSTRUMENT_INVALID"
    )

    powerless = copy.deepcopy(fixture)
    powerless["standardisation"]["focus_offset_power"][1]["upper99"] = 0.95
    assert adjudicate(powerless, bound_contract)["verdict"] == "INSTRUMENT_INVALID"

    missing_improvement = copy.deepcopy(fixture)
    missing_improvement["commissioning"]["improvement_raises_score"] = False
    assert (
        adjudicate(missing_improvement, bound_contract)["verdict"]
        == "INSTRUMENT_INVALID"
    )

    wrong_detail_hash = copy.deepcopy(fixture)
    wrong_detail_hash["detail_binding"]["checker_sha256"] = "e" * 64
    assert (
        adjudicate(wrong_detail_hash, bound_contract)["verdict"]
        == "BLOCKED_DETAIL_INSTRUMENT"
    )

    incomplete_grid = copy.deepcopy(fixture)
    del incomplete_grid["development_arms"]["1.00"]
    assert (
        adjudicate(incomplete_grid, bound_contract)["verdict"] == "INSTRUMENT_INVALID"
    )

    no_operating_point = copy.deepcopy(fixture)
    no_operating_point["development_arms"] = {
        key: failing_arm() for key in tau_keys(bound_contract)
    }
    assert (
        adjudicate(no_operating_point, bound_contract)["verdict"]
        == "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT"
    )

    knife_edge = copy.deepcopy(no_operating_point)
    knife_edge["development_arms"]["0.40"] = passing_arm()
    knife_edge["development_arms"]["0.41"] = passing_arm()
    assert (
        adjudicate(knife_edge, bound_contract)["verdict"]
        == "PHASE1_REFUTED_NO_GLOBAL_OUTPUT_OPERATING_POINT"
    )

    holdout_fail = copy.deepcopy(with_holdout)
    holdout_fail["holdout"]["arm"]["noise_power_upper95_by_capture"][
        "noise-development"
    ]["B"] = 0.91
    assert (
        adjudicate(holdout_fail, bound_contract)["verdict"] == "PHASE1_REFUTED_HOLDOUT"
    )

    print(
        "self-test: null=GREEN defect=RED improvement-required=RED "
        "width-irrelevance=GREEN development-refutation=RED holdout-refutation=RED"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    if not (args.check or args.self_test or args.result):
        parser.error("choose --check, --self-test, or --result")

    contract = load_json(CONTRACT_PATH)
    validate_contract(contract)
    if args.check:
        validate_sources(contract)
        validate_document()
        print("preregistration check: PASS")
    if args.self_test:
        run_self_test(contract)
    if args.result:
        result = load_json(args.result)
        print(json.dumps(adjudicate(result, contract), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
