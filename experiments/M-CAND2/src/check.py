from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path


BASE_MIN = 0.25
BASE_MAX = 64.0
ALGEBRA_RATIO_TOL = 1e-8
ALGEBRA_SCORE_TOL = 1e-7
CONGRUENCE_TOL = 1e-10
NONLINEAR_UCB_MAX = 1.01
TONE_LOW = 0.99
TONE_HIGH = 1.01
CLIP_POTENCY_MIN = 0.001


def arithmetic(comparison: dict) -> list[str]:
    errors = []
    base = float(comparison["base_d2"])
    arm = float(comparison["arm_d2"])
    if not math.isclose(
        float(comparison["ratio"]),
        arm / base,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        errors.append("ratio arithmetic mismatch")
    if comparison["minimum_bootstrap_base_d2"] <= 0.0:
        errors.append("non-positive bootstrap base")
    return errors


def check_preflight(record: dict) -> list[str]:
    errors = []
    if record.get("stage") != "baseline-only-preflight":
        errors.append("wrong preflight stage")
    if not record.get("pass"):
        errors.append("preflight did not pass")
    if not record["range_audit"]["pass"]:
        errors.append("baseline leaves representable range")
    final = record["conditioning_ladder"][-1]["result"]
    if final["status"] != "NUMERIC":
        errors.append("baseline covariance refused")
    elif not BASE_MIN <= final["d2"] <= BASE_MAX:
        errors.append("baseline d2 outside frozen range")
    for model in final["models"]:
        if model["train_count"] <= model["dimension"]:
            errors.append("n is not greater than p")
        if model["train_to_dimension"] < 1.4:
            errors.append("n/p margin failed")
        if model["condition_number"] > 1e8:
            errors.append("conditioning gate failed")
    return errors


def check_arm(record: dict) -> list[str]:
    errors = []
    name = record["arm"]
    comparison = record.get("comparison")
    candidate = record["candidate"]
    if record.get("stage") != "ordered-adversary":
        errors.append("wrong arm stage")
    expected = False
    if comparison is not None:
        errors.extend(arithmetic(comparison))
        if name == "unclipped-usm":
            algebra = record["algebra_audit"]
            expected = bool(
                abs(comparison["ratio"] - 1.0) <= ALGEBRA_RATIO_TOL
                and max(
                    algebra["maximum_plus_score_absolute_error"],
                    algebra["maximum_minus_score_absolute_error"],
                )
                <= ALGEBRA_SCORE_TOL
                and max(
                    algebra["maximum_covariance_relative_error"],
                    algebra["maximum_derivative_relative_error"],
                    algebra["maximum_midpoint_relative_error"],
                )
                <= CONGRUENCE_TOL
                and algebra["operator_minimum_eigenvalue"] > 0.0
            )
        elif name == "clipped-usm":
            nonlinear = record.get("nonlinearity_audit")
            expected = bool(
                nonlinear is not None
                and nonlinear["changed_fraction"] >= CLIP_POTENCY_MIN
                and comparison["ratio_ucb95_one_sided"]
                <= NONLINEAR_UCB_MAX
            )
        elif name in ("gamma3", "logistic"):
            interval = comparison["ratio_ci95_two_sided"]
            expected = interval[0] >= TONE_LOW and interval[1] <= TONE_HIGH
        else:
            expected = bool(
                comparison["ratio"] <= 1.0
                and comparison["ratio_ucb95_one_sided"]
                <= NONLINEAR_UCB_MAX
            )
    elif candidate["status"] == "REFUSED_RANK":
        expected = name in ("saturation", "quantization")
    if record.get("pass") != expected:
        errors.append("arm verdict does not follow literal gate")
    if record.get("stop_after_this_arm") != (not expected):
        errors.append("stop flag mismatch")
    return errors


def green_fixture() -> dict:
    comparison = {
        "base_d2": 2.0,
        "arm_d2": 2.0,
        "ratio": 1.0,
        "ratio_lcb95_one_sided": 0.999,
        "ratio_ucb95_one_sided": 1.001,
        "ratio_ci95_two_sided": [0.999, 1.001],
        "minimum_bootstrap_base_d2": 1.0,
    }
    algebra = {
        "maximum_plus_score_absolute_error": 1e-10,
        "maximum_minus_score_absolute_error": 1e-10,
        "maximum_covariance_relative_error": 1e-12,
        "maximum_derivative_relative_error": 1e-12,
        "maximum_midpoint_relative_error": 1e-12,
        "operator_minimum_eigenvalue": 1.0,
    }
    return {
        "stage": "ordered-adversary",
        "arm": "unclipped-usm",
        "candidate": {"status": "NUMERIC"},
        "comparison": comparison,
        "algebra_audit": algebra,
        "transform_audit": {"changed_fraction": 1.0},
        "pass": True,
        "stop_after_this_arm": False,
    }


def self_test() -> int:
    fixture = green_fixture()
    if check_arm(fixture):
        print("SELF-TEST green fixture failed")
        return 1
    plants = [
        lambda x: x["comparison"].update(ratio=1.1),
        lambda x: x["algebra_audit"].update(
            maximum_plus_score_absolute_error=1e-5
        ),
        lambda x: x["algebra_audit"].update(
            maximum_covariance_relative_error=1e-5
        ),
        lambda x: x.update({"pass": False}),
    ]
    caught = 0
    for plant in plants:
        mutant = copy.deepcopy(fixture)
        plant(mutant)
        if check_arm(mutant):
            caught += 1
    print(f"SELF-TEST caught {caught}/{len(plants)} arm mutations")
    clipped = copy.deepcopy(fixture)
    clipped.update(
        {
            "arm": "clipped-usm",
            "algebra_audit": None,
            "nonlinearity_audit": {"changed_fraction": 0.0},
            "pass": True,
        }
    )
    no_op_caught = bool(check_arm(clipped))
    print(f"SELF-TEST caught clipped no-op: {no_op_caught}")
    return 0 if caught == len(plants) and no_op_caught else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", nargs="?", choices=("preflight", "arm"))
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.kind is None or args.path is None:
        parser.error("kind and path required without --self-test")
    record = json.loads(args.path.read_text(encoding="utf-8"))
    errors = check_preflight(record) if args.kind == "preflight" else check_arm(record)
    if errors:
        for error in errors:
            print(f"RED: {error}")
        return 1
    print(f"GREEN: {args.kind} follows frozen literal gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
