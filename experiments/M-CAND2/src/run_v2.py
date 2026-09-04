from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cand2 as core
import cand2_v2 as amendment


MANDATORY = ("unclipped-usm", "clipped-usm", "gamma3", "logistic")
DOWNSTREAM = ("saturation", "quantization", "degraded", "improved", "null")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, record: dict) -> None:
    core.write_json(path, record)


def _common(freeze: str) -> tuple[dict, object, dict]:
    amendment.require_frozen_preregistration()
    frozen = amendment.verify_freeze(freeze)
    source_preflight = amendment.verify_source_preflight()
    pinned_task = amendment.verify_pinned_task()
    backgrounds, inputs = core.load_backgrounds()
    return (
        {
            "freeze": frozen,
            "source_preflight": source_preflight,
            "pinned_task": pinned_task,
            "inputs": inputs,
            "source": amendment.amendment_source_summary(),
            "environment": core.environment_record(),
        },
        backgrounds,
        frozen,
    )


def preflight(output: Path) -> int:
    core.configure_threads()
    expected_output = amendment.output_path("display-preflight")
    if output.resolve() != expected_output.resolve():
        raise RuntimeError("display preflight output path is fixed")
    preregistration = amendment.EXPERIMENT / "PREREGISTRATION-V2.md"
    preregistration_text = preregistration.read_text(encoding="utf-8")
    draft = (
        preregistration_text.count("**Status: DRAFT.") == 1
        and "**Status: FROZEN before any amendment arm.**"
        not in preregistration_text
    )
    if output.exists() and not draft:
        raise RuntimeError("refusing to overwrite frozen display preflight")
    source_preflight = amendment.verify_source_preflight()
    pinned_task = amendment.verify_pinned_task()
    backgrounds, inputs = core.load_backgrounds()
    raw = core.make_observations(
        backgrounds,
        amendment.PINNED_TEMPLATE_SEED,
        "base",
    )
    mapped = amendment.display_map(raw)
    result = core.crossfit(mapped, "display-base")
    map_audit = amendment.display_map_audit(raw, mapped)
    conditions = [
        model.condition_number for model in result.models
    ]
    passed = bool(
        result.status == "NUMERIC"
        and result.d2 is not None
        and core.BASE_D2_MIN <= result.d2 <= core.BASE_D2_MAX
        and map_audit["mapped_range"]["pass"]
        and len(result.blocks) == 480
        and len(conditions) == 5
    )
    record = {
        "campaign": amendment.CAMPAIGN,
        "stage": "baseline-only-display-preflight",
        "source_preflight": source_preflight,
        "pinned_task": pinned_task,
        "result_template_seed": amendment.PINNED_TEMPLATE_SEED,
        "inputs": inputs,
        "source": amendment.amendment_source_summary(),
        "environment": core.environment_record(),
        "display_map_audit": map_audit,
        "result": core.result_record(result),
        "pass": passed,
        "challenge_transforms_evaluated": [],
    }
    _write(output, record)
    if result.status == "NUMERIC":
        print(
            f"DISPLAY PRE-FLIGHT {'GREEN' if passed else 'RED'}: "
            f"d2={result.d2:.6f}, max condition={max(conditions):.6e}, "
            f"input rails={map_audit['mapped_rail_fraction']:.6f}"
        )
    else:
        print(f"DISPLAY PRE-FLIGHT RED: {result.refusal}")
    return 0 if passed else 1


def verify(freeze: str) -> int:
    amendment.require_frozen_preregistration()
    frozen = amendment.verify_freeze(freeze)
    amendment.verify_source_preflight()
    amendment.verify_pinned_task()
    print(f"FREEZE GREEN: {frozen['commit']} ({len(frozen) - 1} paths)")
    return 0


def _required_record(name: str, freeze: str) -> dict:
    path = amendment.output_path(name)
    if not path.exists():
        raise RuntimeError(f"required amendment record missing: {name}")
    record = _read(path)
    if record["freeze"]["commit"] != freeze:
        raise RuntimeError(f"freeze differs in amendment record: {name}")
    if record.get("arm") != name:
        raise RuntimeError(
            f"arm identity mismatch: expected {name}, got {record.get('arm')}"
        )
    return record


def _literal_mandatory_state(record: dict, expected_name: str) -> str:
    name = record["arm"]
    if name != expected_name:
        return "INVALID"
    comparison = record.get("comparison")
    potency = record.get("potency")
    base = record.get("base")
    candidate = record.get("candidate")
    scoring_performed = record.get("scoring_performed") is True

    def valid_comparison(value: dict | None) -> bool:
        if (
            value is None
            or not isinstance(base, dict)
            or not isinstance(candidate, dict)
        ):
            return False
        numeric = []
        for key in ("base_d2", "arm_d2", "ratio"):
            numeric.append(value.get(key))
        interval = value.get("ratio_ci95_two_sided")
        if not isinstance(interval, list) or len(interval) != 2:
            return False
        numeric.extend(interval)
        if "ratio_ucb95_one_sided" in value:
            numeric.append(value["ratio_ucb95_one_sided"])
        if "ratio_lcb95_one_sided" in value:
            numeric.append(value["ratio_lcb95_one_sided"])
        try:
            base_d2 = float(value["base_d2"])
            arm_d2 = float(value["arm_d2"])
            ratio = float(value["ratio"])
            low = float(interval[0])
            high = float(interval[1])
            result_base_d2 = float(base.get("d2"))
            result_arm_d2 = float(candidate.get("d2"))
            return bool(
                all(math.isfinite(float(item)) for item in numeric)
                and math.isfinite(result_base_d2)
                and math.isfinite(result_arm_d2)
                and base_d2 > 0.0
                and arm_d2 >= 0.0
                and ratio >= 0.0
                and 0.0 <= low <= high
                and (
                    "ratio_ucb95_one_sided" not in value
                    or float(value["ratio_ucb95_one_sided"]) >= 0.0
                )
                and (
                    "ratio_lcb95_one_sided" not in value
                    or float(value["ratio_lcb95_one_sided"]) >= 0.0
                )
                and math.isclose(ratio, arm_d2 / base_d2, rel_tol=1e-12)
                and math.isclose(
                    result_base_d2,
                    base_d2,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
                and math.isclose(
                    result_arm_d2,
                    arm_d2,
                    rel_tol=1e-12,
                    abs_tol=1e-12,
                )
            )
        except (TypeError, ValueError, ZeroDivisionError):
            return False

    if name == "unclipped-usm":
        algebra = record.get("algebra_audit")
        if (
            not scoring_performed
            or not isinstance(base, dict)
            or base.get("status") != "NUMERIC"
            or not isinstance(candidate, dict)
            or candidate.get("status") != "NUMERIC"
            or not valid_comparison(comparison)
            or algebra is None
        ):
            return "INVALID"
        passed = bool(
            abs(comparison["ratio"] - 1.0) <= core.ALGEBRA_RATIO_TOL
            and max(
                algebra["maximum_plus_score_absolute_error"],
                algebra["maximum_minus_score_absolute_error"],
            )
            <= core.ALGEBRA_SCORE_TOL
            and max(
                algebra["maximum_covariance_relative_error"],
                algebra["maximum_derivative_relative_error"],
                algebra["maximum_midpoint_relative_error"],
            )
            <= core.CONGRUENCE_REL_TOL
            and algebra["operator_minimum_eigenvalue"] > 0.0
        )
        return "PASS" if passed else "INVALID"
    if potency is None:
        return "INVALID"
    if name == "clipped-usm":
        if not amendment.clipping_potency_literal(potency):
            return "INVALID"
        if not scoring_performed or not isinstance(base, dict):
            return "INVALID"
        if base.get("status") != "NUMERIC":
            return "INVALID"
        if not isinstance(candidate, dict):
            return "INVALID"
        if candidate.get("status") == "REFUSED_RANK":
            return "DEAD" if comparison is None else "INVALID"
        if candidate.get("status") != "NUMERIC" or not valid_comparison(comparison):
            return "INVALID"
        passed = bool(
            comparison["ratio_ucb95_one_sided"]
            <= core.NONLINEAR_RATIO_UCB_MAX
        )
        return "PASS" if passed else "DEAD"
    if name in ("gamma3", "logistic"):
        if not amendment.tone_potency_literal(potency):
            return "INVALID"
        if not scoring_performed or not isinstance(base, dict):
            return "INVALID"
        if base.get("status") != "NUMERIC":
            return "INVALID"
        if not isinstance(candidate, dict):
            return "INVALID"
        if candidate.get("status") == "REFUSED_RANK":
            return "DEAD" if comparison is None else "INVALID"
        if candidate.get("status") != "NUMERIC" or not valid_comparison(comparison):
            return "INVALID"
        interval = comparison["ratio_ci95_two_sided"]
        passed = bool(
            interval[0] >= 1.0 - core.TONE_EQUIVALENCE
            and interval[1] <= 1.0 + core.TONE_EQUIVALENCE
        )
        return "PASS" if passed else "DEAD"
    return "INVALID"


def _literal_mandatory_pass(record: dict, expected_name: str | None = None) -> bool:
    name = expected_name or record.get("arm")
    return bool(
        _literal_mandatory_state(record, name) == "PASS"
        and record.get("pass")
        and record.get("classification") == "PASS"
    )


def _require_mandatory_predecessor(name: str, freeze: str) -> None:
    if name == "unclipped-usm":
        return
    unclip = _required_record("unclipped-usm", freeze)
    if not _literal_mandatory_pass(unclip, "unclipped-usm"):
        raise RuntimeError("unclipped implementation check failed")
    if name == "gamma3":
        _required_record("clipped-usm", freeze)
    elif name == "logistic":
        _required_record("clipped-usm", freeze)
        _required_record("gamma3", freeze)


def _blank_record(common: dict, name: str, map_audit: dict) -> dict:
    return {
        "campaign": amendment.CAMPAIGN,
        "stage": "mandatory-adversary",
        "arm": name,
        **common,
        "display_map_audit": map_audit,
        "potency": None,
        "scoring_performed": False,
        "base": None,
        "candidate": None,
        "comparison": None,
        "algebra_audit": None,
        "pass": False,
        "classification": None,
        "candidate_status": None,
    }


def _score_pair(
    record: dict,
    name: str,
    base_data: core.ObservationSet,
    arm_data: core.ObservationSet,
) -> tuple[core.HotellingResult, core.HotellingResult, dict | None]:
    base = core.crossfit(base_data, "display-base")
    arm = core.crossfit(arm_data, name)
    comparison = None
    if base.status == "NUMERIC" and arm.status == "NUMERIC":
        comparison = core.bootstrap_comparison(base, arm)
    record["scoring_performed"] = True
    record["base"] = core.result_record(base)
    record["candidate"] = core.result_record(arm)
    record["comparison"] = comparison
    return base, arm, comparison


def run_mandatory(name: str, freeze: str, output: Path) -> int:
    import numpy as np

    core.configure_threads()
    common, backgrounds, frozen = _common(freeze)
    _require_mandatory_predecessor(name, frozen["commit"])
    if output.exists():
        raise RuntimeError(f"refusing to overwrite arm output: {output}")
    raw_base = core.make_observations(
        backgrounds,
        amendment.PINNED_TEMPLATE_SEED,
        "base",
    )
    base_data = amendment.display_map(raw_base)
    map_audit = amendment.display_map_audit(raw_base, base_data)
    record = _blank_record(common, name, map_audit)

    if name == "unclipped-usm":
        arm_data = amendment.transform(base_data, name)
        base, arm, comparison = _score_pair(
            record,
            name,
            base_data,
            arm_data,
        )
        if comparison is None:
            passed = False
            classification = "INVALID_IMPLEMENTATION"
        else:
            algebra = core.algebra_audit(base, arm)
            record["algebra_audit"] = algebra
            maximum_score_error = max(
                algebra["maximum_plus_score_absolute_error"],
                algebra["maximum_minus_score_absolute_error"],
            )
            maximum_congruence_error = max(
                algebra["maximum_covariance_relative_error"],
                algebra["maximum_derivative_relative_error"],
                algebra["maximum_midpoint_relative_error"],
            )
            passed = bool(
                abs(comparison["ratio"] - 1.0)
                <= core.ALGEBRA_RATIO_TOL
                and maximum_score_error <= core.ALGEBRA_SCORE_TOL
                and maximum_congruence_error <= core.CONGRUENCE_REL_TOL
                and algebra["operator_minimum_eigenvalue"] > 0.0
            )
            classification = "PASS" if passed else "INVALID_IMPLEMENTATION"
        record["pass"] = passed
        record["classification"] = classification
        record["candidate_status"] = (
            "PENDING_KILL_ARMS" if passed else "UNCOMMISSIONED"
        )
    elif name == "clipped-usm":
        unclipped = amendment.transform(base_data, "unclipped-usm")
        arm_data = amendment.transform(base_data, name)
        potency = amendment.clipping_potency(
            base_data,
            unclipped,
            arm_data,
        )
        record["potency"] = potency
        if not amendment.clipping_potency_literal(potency):
            record["classification"] = "INVALID_UNPOTENT"
            record["candidate_status"] = "UNCOMMISSIONED_PENDING_TONES"
        else:
            base, arm, comparison = _score_pair(
                record,
                name,
                base_data,
                arm_data,
            )
            if base.status != "NUMERIC":
                record["classification"] = "INVALID_BASE_REFUSAL"
                record["candidate_status"] = "UNCOMMISSIONED"
            elif arm.status == "REFUSED_RANK":
                record["classification"] = "DEAD_REFUSED_RANK"
                record["candidate_status"] = "DEAD"
            elif comparison is None:
                record["classification"] = "INVALID_NUMERIC"
                record["candidate_status"] = "UNCOMMISSIONED"
            else:
                passed = bool(
                    comparison["ratio_ucb95_one_sided"]
                    <= core.NONLINEAR_RATIO_UCB_MAX
                )
                record["pass"] = passed
                record["classification"] = "PASS" if passed else "DEAD"
                record["candidate_status"] = (
                    "PENDING_TONES" if passed else "DEAD"
                )
    else:
        arm_data = amendment.transform(base_data, name)
        potency = amendment.tone_potency(base_data, arm_data, name)
        record["potency"] = potency
        if not amendment.tone_potency_literal(potency):
            record["classification"] = "INVALID_UNPOTENT"
            record["candidate_status"] = "UNCOMMISSIONED"
        else:
            base, arm, comparison = _score_pair(
                record,
                name,
                base_data,
                arm_data,
            )
            if base.status != "NUMERIC":
                record["classification"] = "INVALID_BASE_REFUSAL"
                record["candidate_status"] = "UNCOMMISSIONED"
            elif arm.status == "REFUSED_RANK":
                record["classification"] = "DEAD_REFUSED_RANK"
                record["candidate_status"] = "DEAD"
            elif comparison is None:
                record["classification"] = "INVALID_NUMERIC"
                record["candidate_status"] = "UNCOMMISSIONED"
            else:
                interval = comparison["ratio_ci95_two_sided"]
                passed = bool(
                    interval[0] >= 1.0 - core.TONE_EQUIVALENCE
                    and interval[1] <= 1.0 + core.TONE_EQUIVALENCE
                )
                record["pass"] = passed
                record["classification"] = "PASS" if passed else "DEAD"
                record["candidate_status"] = (
                    "PENDING_MANDATORY_GATE" if passed else "DEAD"
                )

    _write(output, record)
    comparison = record["comparison"]
    potency = record["potency"]
    if comparison is None:
        potency_text = (
            f", potency={potency['pass']}"
            if potency is not None
            else ""
        )
        print(
            f"{name}: {record['classification']}{potency_text}, "
            f"scored={record['scoring_performed']}"
        )
    else:
        print(
            f"{name}: R={comparison['ratio']:.9f}, "
            f"CI95=[{comparison['ratio_ci95_two_sided'][0]:.9f},"
            f"{comparison['ratio_ci95_two_sided'][1]:.9f}], "
            f"UCB95={comparison['ratio_ucb95_one_sided']:.9f} -> "
            f"{record['classification']}"
        )
    return 0 if record["pass"] else 2


def gate(freeze: str, output: Path) -> int:
    amendment.require_frozen_preregistration()
    frozen = amendment.verify_freeze(freeze)
    expected_output = amendment.output_path("downstream-gate")
    if output.resolve() != expected_output.resolve():
        raise RuntimeError("downstream gate output path is fixed")
    if output.exists():
        raise RuntimeError("refusing to overwrite downstream gate")
    records = {
        name: _required_record(name, frozen["commit"])
        for name in MANDATORY
    }
    classifications = {
        name: record["classification"] for name, record in records.items()
    }
    literal_state = {
        name: _literal_mandatory_state(record, name)
        for name, record in records.items()
    }
    dead = any(state == "DEAD" for state in literal_state.values())
    literal_pass = {
        name: _literal_mandatory_pass(records[name], name)
        for name in records
    }
    eligible = all(literal_pass.values())
    status = "DEAD" if dead else "ELIGIBLE" if eligible else "UNCOMMISSIONED"
    record = {
        "campaign": amendment.CAMPAIGN,
        "stage": "downstream-gate",
        "freeze": frozen,
        "mandatory_classifications": classifications,
        "mandatory_literal_state": literal_state,
        "mandatory_literal_pass": literal_pass,
        "eligible": eligible,
        "candidate_status": status,
        "downstream_arms_run": [
            name for name in DOWNSTREAM if amendment.output_path(name).exists()
        ],
    }
    if not eligible and record["downstream_arms_run"]:
        raise RuntimeError("downstream output exists despite closed gate")
    _write(output, record)
    print(f"DOWNSTREAM GATE: eligible={eligible}, status={status}")
    return 0 if eligible else 2


def _require_downstream_predecessor(name: str, freeze: str) -> None:
    gate_record = _read(amendment.output_path("downstream-gate"))
    mandatory = {
        arm: _required_record(arm, freeze)
        for arm in MANDATORY
    }
    literal_pass = {
        arm: _literal_mandatory_pass(record, arm)
        for arm, record in mandatory.items()
    }
    if (
        gate_record["freeze"]["commit"] != freeze
        or not gate_record["eligible"]
        or not all(literal_pass.values())
        or gate_record.get("mandatory_literal_pass") != literal_pass
    ):
        raise RuntimeError("mandatory adversaries did not open downstream gate")
    index = DOWNSTREAM.index(name)
    for prior in DOWNSTREAM[:index]:
        record = _required_record(prior, freeze)
        if not record["pass"]:
            raise RuntimeError(f"downstream predecessor failed: {prior}")


def run_downstream(name: str, freeze: str, output: Path) -> int:
    core.configure_threads()
    common, backgrounds, frozen = _common(freeze)
    _require_downstream_predecessor(name, frozen["commit"])
    if output.exists():
        raise RuntimeError(f"refusing to overwrite arm output: {output}")
    raw_base = core.make_observations(
        backgrounds,
        amendment.PINNED_TEMPLATE_SEED,
        "base",
    )
    base_data = amendment.display_map(raw_base)
    record = {
        "campaign": amendment.CAMPAIGN,
        "stage": "downstream-arm",
        "arm": name,
        **common,
        "display_map_audit": amendment.display_map_audit(raw_base, base_data),
        "potency": None,
        "scoring_performed": False,
        "base": None,
        "candidate": None,
        "comparison": None,
        "pass": False,
        "classification": None,
    }

    if name in ("saturation", "quantization"):
        arm_data = amendment.transform(base_data, name)
        potency = amendment.lossy_potency(base_data, arm_data, name)
        record["potency"] = potency
        if not potency["pass"]:
            record["classification"] = "INVALID_UNPOTENT"
        else:
            base, arm, comparison = _score_pair(
                record,
                name,
                base_data,
                arm_data,
            )
            if base.status != "NUMERIC":
                record["classification"] = "DEAD_BASE_REFUSAL"
            elif arm.status == "REFUSED_RANK":
                record["pass"] = True
                record["classification"] = "PASS_REFUSED_RANK"
            elif comparison is None:
                record["classification"] = "DEAD"
            else:
                passed = bool(
                    comparison["ratio"] <= 1.0
                    and comparison["ratio_ucb95_one_sided"]
                    <= core.NONLINEAR_RATIO_UCB_MAX
                )
                record["pass"] = passed
                record["classification"] = "PASS" if passed else "DEAD"
    else:
        if name in ("degraded", "improved"):
            arm_data = amendment.make_display_observations(
                backgrounds,
                name,
                amendment.PINNED_TEMPLATE_SEED,
            )
        else:
            arm_data = amendment.transform(base_data, "null")
        base, arm, comparison = _score_pair(
            record,
            name,
            base_data,
            arm_data,
        )
        if comparison is None:
            record["classification"] = "DEAD_REFUSED_RANK"
        elif name == "degraded":
            passed = bool(
                comparison["ratio_ucb95_one_sided"]
                <= 1.0 - core.OPTICAL_RATIO_MARGIN
            )
            record["pass"] = passed
            record["classification"] = "PASS" if passed else "DEAD"
        elif name == "improved":
            passed = bool(
                comparison["ratio_lcb95_one_sided"]
                >= 1.0 + core.OPTICAL_RATIO_MARGIN
            )
            record["pass"] = passed
            record["classification"] = "PASS" if passed else "DEAD"
        else:
            passed = abs(comparison["ratio"] - 1.0) <= core.ALGEBRA_RATIO_TOL
            record["pass"] = passed
            record["classification"] = "PASS" if passed else "DEAD"

    _write(output, record)
    comparison = record["comparison"]
    if comparison is None:
        print(f"{name}: {record['classification']}")
    else:
        print(
            f"{name}: R={comparison['ratio']:.9f}, "
            f"CI95=[{comparison['ratio_ci95_two_sided'][0]:.9f},"
            f"{comparison['ratio_ci95_two_sided'][1]:.9f}] -> "
            f"{record['classification']}"
        )
    return 0 if record["pass"] else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight")
    pre.add_argument(
        "--out",
        type=Path,
        default=amendment.output_path("display-preflight"),
    )
    verify_parser = sub.add_parser("verify-freeze")
    verify_parser.add_argument("--freeze", required=True)
    arm = sub.add_parser("arm")
    arm.add_argument("name", choices=MANDATORY + DOWNSTREAM)
    arm.add_argument("--freeze", required=True)
    gate_parser = sub.add_parser("gate")
    gate_parser.add_argument("--freeze", required=True)
    args = parser.parse_args(argv)

    if args.command == "preflight":
        return preflight(args.out)
    if args.command == "verify-freeze":
        return verify(args.freeze)
    if args.command == "gate":
        return gate(args.freeze, amendment.output_path("downstream-gate"))
    output = amendment.output_path(args.name)
    if args.name in MANDATORY:
        return run_mandatory(args.name, args.freeze, output)
    return run_downstream(args.name, args.freeze, output)


if __name__ == "__main__":
    sys.exit(main())
