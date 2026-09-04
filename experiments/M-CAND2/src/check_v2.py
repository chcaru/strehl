from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np

import cand2 as core
import cand2_v2 as amendment
import run_v2


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_preflight(record: dict) -> list[str]:
    errors = []
    if record.get("campaign") != amendment.CAMPAIGN:
        errors.append("wrong campaign")
    if record.get("stage") != "baseline-only-display-preflight":
        errors.append("wrong stage")
    if record.get("challenge_transforms_evaluated") != []:
        errors.append("challenge transform ran during preflight")
    source = record.get("source_preflight", {})
    if source.get("sha256") != amendment.SOURCE_PREFLIGHT_SHA256:
        errors.append("source preflight hash mismatch")
    if source.get("minimum") != amendment.DISPLAY_BLACK:
        errors.append("display black provenance mismatch")
    if source.get("maximum") != amendment.DISPLAY_WHITE:
        errors.append("display white provenance mismatch")
    map_audit = record.get("display_map_audit", {})
    if map_audit.get("black") != amendment.DISPLAY_BLACK:
        errors.append("display-map black mismatch")
    if map_audit.get("white") != amendment.DISPLAY_WHITE:
        errors.append("display-map white mismatch")
    pinned = record.get("pinned_task", {})
    if pinned.get("seed") != amendment.PINNED_TEMPLATE_SEED:
        errors.append("pinned task seed mismatch")
    if pinned.get("template_sha256") != amendment.PINNED_TEMPLATE_SHA256:
        errors.append("pinned template hash mismatch")
    if record.get("result_template_seed") != amendment.PINNED_TEMPLATE_SEED:
        errors.append("preflight result used wrong task seed")
    if not record.get("pass"):
        errors.append("preflight did not pass")
    if record["result"]["status"] != "NUMERIC":
        errors.append("mapped baseline refused")
    if record["result"]["site_count"] != 480:
        errors.append("site count changed")
    if not core.BASE_D2_MIN <= record["result"]["d2"] <= core.BASE_D2_MAX:
        errors.append("baseline d2 outside frozen range")
    if len(record["result"]["models"]) != 5:
        errors.append("wrong fold count")
    for model in record["result"]["models"]:
        if model["dimension"] != core.DIMENSION:
            errors.append("dimension changed")
        if model["train_count"] != 384:
            errors.append("covariance site count changed")
    if not record["display_map_audit"]["mapped_range"]["pass"]:
        errors.append("display map left representable range")
    return errors


def _arithmetic(comparison: dict) -> list[str]:
    errors = []
    expected = comparison["arm_d2"] / comparison["base_d2"]
    if not np.isclose(comparison["ratio"], expected, rtol=1e-12, atol=1e-12):
        errors.append("ratio arithmetic mismatch")
    return errors


def check_arm(record: dict) -> list[str]:
    errors = []
    name = record["arm"]
    comparison = record.get("comparison")
    potency = record.get("potency")
    if comparison is not None:
        errors.extend(_arithmetic(comparison))
    if potency is not None and not potency["pass"]:
        if record.get("scoring_performed"):
            errors.append("scoring ran after failed potency")
        if comparison is not None:
            errors.append("comparison exists after failed potency")
        if record.get("classification") != "INVALID_UNPOTENT":
            errors.append("failed potency not classified invalid")
        if record.get("pass"):
            errors.append("failed potency marked pass")
    if name in ("clipped-usm", "gamma3", "logistic") and potency is None:
        errors.append("mandatory potency record missing")
    if name == "clipped-usm" and potency is not None:
        if potency.get("pass") != amendment.clipping_potency_literal(potency):
            errors.append("clipping potency flag does not follow literal gates")
        if potency["pass"]:
            if not potency["exact_changed_mask_equals_outside_mask"]:
                errors.append("clipping changed-mask mismatch")
            if not potency["exact_outside_to_rail_mapping"]:
                errors.append("clipping rail mapping mismatch")
            if (
                potency["changed_fraction"]
                < amendment.POTENCY_CHANGED_FRACTION_MIN
            ):
                errors.append("clipping fraction below gate")
            if (
                potency["new_high_rail_fraction"]
                < amendment.POTENCY_HIGH_FRACTION_MIN
            ):
                errors.append("high-rail fraction below gate")
            if not potency["high_collision_witness"]:
                errors.append("missing high collision witness")
            for role in ("covariance", "derivative", "test"):
                role_record = potency["high_rail_role_records"][role]
                if (
                    role_record["independent_sites"]
                    < amendment.POTENCY_INDEPENDENT_SITES_MIN
                    or not role_record["all_blocks_represented"]
                ):
                    errors.append(f"high-rail role gate failed: {role}")
    if name in ("gamma3", "logistic") and potency is not None and potency["pass"]:
        if not amendment.tone_potency_literal(potency):
            errors.append("tone potency flag does not follow literal gates")
        if (
            potency["changed_fraction"]
            < amendment.TONE_CHANGED_FRACTION_MIN
        ):
            errors.append("tone changed fraction below gate")
        if (
            potency["materially_nonaffine_fraction"]
            < amendment.TONE_NONAFFINE_FRACTION_MIN
        ):
            errors.append("tone nonaffinity below gate")
        if potency["new_ties_between_distinct_inputs"] != 0:
            errors.append("tone introduced ties")
    if name == "unclipped-usm" and comparison is not None:
        algebra = record["algebra_audit"]
        expected = bool(
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
        if record["pass"] != expected:
            errors.append("unclipped verdict does not follow gate")
    elif name == "clipped-usm" and potency and potency["pass"]:
        expected = bool(
            comparison is not None
            and comparison["ratio_ucb95_one_sided"]
            <= core.NONLINEAR_RATIO_UCB_MAX
        )
        if record["pass"] != expected:
            errors.append("clipped verdict does not follow gate")
    elif name in ("gamma3", "logistic") and potency and potency["pass"]:
        interval = comparison["ratio_ci95_two_sided"] if comparison else None
        expected = bool(
            interval is not None
            and interval[0] >= 1.0 - core.TONE_EQUIVALENCE
            and interval[1] <= 1.0 + core.TONE_EQUIVALENCE
        )
        if record["pass"] != expected:
            errors.append("tone verdict does not follow gate")
    if name in ("unclipped-usm", "clipped-usm", "gamma3", "logistic"):
        state = run_v2._literal_mandatory_state(record, name)
        if state == "PASS":
            if not record.get("pass") or record.get("classification") != "PASS":
                errors.append("literal pass mislabeled")
        elif state == "DEAD":
            if record.get("pass") or record.get("classification") not in (
                "DEAD",
                "DEAD_REFUSED_RANK",
            ):
                errors.append("literal kill-arm failure not labeled dead")
        elif record.get("pass"):
            errors.append("invalid mandatory record marked pass")
    return errors


def _fixture(values: np.ndarray) -> core.ObservationSet:
    count = len(values)
    blocks = np.arange(count) % 5
    macros = np.arange(count)
    covariance = values[:, None]
    tasks = values[None, :, None]
    return core.ObservationSet(
        covariance=covariance,
        derivative_plus=tasks.copy(),
        derivative_minus=tasks.copy(),
        test_plus=tasks.copy(),
        test_minus=tasks.copy(),
        blocks=blocks,
        macros=macros,
    )


def self_test() -> int:
    base_values = np.linspace(0.05, 0.95, 100)
    base = _fixture(base_values)
    no_op = amendment.clipping_potency(base, base, base)
    if no_op["pass"]:
        print("SELF-TEST failed: clipping no-op passed")
        return 1

    high_values = np.linspace(1.01, 1.20, 100)
    unclipped = _fixture(high_values)
    clipped = _fixture(np.ones_like(high_values))
    potent = amendment.clipping_potency(base, unclipped, clipped)
    if not potent["pass"]:
        print(f"SELF-TEST failed: potent clipping rejected: {potent}")
        return 1
    fake_target = _fixture(np.full_like(high_values, 0.5))
    fake = amendment.clipping_potency(base, unclipped, fake_target)
    if fake["pass"]:
        print("SELF-TEST failed: non-rail fake clipping passed")
        return 1
    low_only_roles = core.ObservationSet(
        covariance=unclipped.covariance,
        derivative_plus=-unclipped.derivative_plus,
        derivative_minus=-unclipped.derivative_minus,
        test_plus=-unclipped.test_plus,
        test_minus=-unclipped.test_minus,
        blocks=unclipped.blocks,
        macros=unclipped.macros,
    )
    low_only_target = core.ObservationSet(
        covariance=clipped.covariance,
        derivative_plus=np.zeros_like(clipped.derivative_plus),
        derivative_minus=np.zeros_like(clipped.derivative_minus),
        test_plus=np.zeros_like(clipped.test_plus),
        test_minus=np.zeros_like(clipped.test_minus),
        blocks=clipped.blocks,
        macros=clipped.macros,
    )
    low_only = amendment.clipping_potency(
        base,
        low_only_roles,
        low_only_target,
    )
    if low_only["pass"]:
        print("SELF-TEST failed: low-only role coverage passed")
        return 1

    gamma = amendment.transform(base, "gamma3")
    gamma_potency = amendment.tone_potency(base, gamma, "gamma3")
    if not gamma_potency["pass"]:
        print(f"SELF-TEST failed: gamma potency rejected: {gamma_potency}")
        return 1
    identity_potency = amendment.tone_potency(base, base, "gamma3")
    if identity_potency["pass"]:
        print("SELF-TEST failed: identity passed tone potency")
        return 1

    fixture = {
        "arm": "gamma3",
        "potency": {"pass": False},
        "scoring_performed": False,
        "comparison": None,
        "classification": "INVALID_UNPOTENT",
        "pass": False,
    }
    if check_arm(fixture):
        print("SELF-TEST failed: valid invalid record rejected")
        return 1
    mutant = copy.deepcopy(fixture)
    mutant["scoring_performed"] = True
    if not check_arm(mutant):
        print("SELF-TEST failed: scoring-after-potency mutant escaped")
        return 1
    mutant = copy.deepcopy(fixture)
    mutant["pass"] = True
    if not check_arm(mutant):
        print("SELF-TEST failed: failed-potency green escaped")
        return 1
    fake_pass = {
        "arm": "gamma3",
        "classification": "PASS",
        "pass": False,
        "potency": gamma_potency,
        "comparison": {
            "base_d2": 1.0,
            "arm_d2": 1.0,
            "ratio": 1.0,
            "ratio_ci95_two_sided": [0.999, 1.001],
        },
        "scoring_performed": True,
        "base": {"status": "NUMERIC", "d2": 1.0},
        "candidate": {"status": "NUMERIC", "d2": 1.0},
    }
    if run_v2._literal_mandatory_pass(fake_pass, "gamma3"):
        print("SELF-TEST failed: false pass opened mandatory gate")
        return 1
    mislabeled_dead = copy.deepcopy(fake_pass)
    mislabeled_dead.update(
        {
            "pass": False,
            "classification": "INVALID_UNPOTENT",
            "comparison": {
                "base_d2": 1.0,
                "arm_d2": 1.02,
                "ratio": 1.02,
                "ratio_ci95_two_sided": [1.02, 1.03],
            },
            "base": {"status": "NUMERIC", "d2": 1.0},
            "candidate": {"status": "NUMERIC", "d2": 1.02},
        }
    )
    if not check_arm(mislabeled_dead):
        print("SELF-TEST failed: mislabeled valid death escaped")
        return 1
    inverted = copy.deepcopy(mislabeled_dead)
    inverted.update({"classification": "PASS", "pass": True})
    inverted["comparison"]["ratio_ci95_two_sided"] = [1.03, 1.02]
    if not check_arm(inverted):
        print("SELF-TEST failed: inverted interval escaped")
        return 1
    print("SELF-TEST GREEN: no-op, potency, tone and stop sentinels")
    return 0


def check_attempt(freeze: str) -> list[str]:
    errors = []
    amendment.verify_freeze(freeze)
    records = {}
    for name in ("unclipped-usm", "clipped-usm", "gamma3", "logistic"):
        path = amendment.output_path(name)
        if not path.exists():
            errors.append(f"missing mandatory record {name}")
            continue
        record = _read(path)
        records[name] = record
        if record.get("arm") != name:
            errors.append(f"arm identity mismatch {name}")
        if record["freeze"]["commit"] != freeze:
            errors.append(f"freeze mismatch {name}")
        errors.extend(f"{name}: {error}" for error in check_arm(record))
    if "gamma3" not in records or "logistic" not in records:
        errors.append("both tone arms were not run")
    gate_path = amendment.output_path("downstream-gate")
    if not gate_path.exists():
        errors.append("missing downstream gate")
    else:
        gate = _read(gate_path)
        present = [
            name
            for name in ("saturation", "quantization", "degraded", "improved", "null")
            if amendment.output_path(name).exists()
        ]
        if not gate["eligible"] and present:
            errors.append("downstream arm exists behind closed gate")
        if gate["eligible"] and not all(
            gate.get("mandatory_literal_pass", {}).values()
        ):
            errors.append("downstream gate trusted non-passing records")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", nargs="?", choices=("preflight", "arm", "attempt"))
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--freeze")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.kind == "preflight" and args.path:
        errors = check_preflight(_read(args.path))
    elif args.kind == "arm" and args.path:
        errors = check_arm(_read(args.path))
    elif args.kind == "attempt" and args.freeze:
        errors = check_attempt(args.freeze)
    else:
        parser.error("provide preflight/arm path or attempt --freeze")
    if errors:
        for error in errors:
            print(f"RED: {error}")
        return 1
    print(f"GREEN: {args.kind} follows amendment gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
