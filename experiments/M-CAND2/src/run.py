from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from cand2 import (
    ALGEBRA_RATIO_TOL,
    ALGEBRA_SCORE_TOL,
    BASE_D2_MAX,
    BASE_D2_MIN,
    CLIP_POTENCY_MIN,
    CONGRUENCE_REL_TOL,
    DEV_TEMPLATE_SEED,
    EXPERIMENT,
    NONLINEAR_RATIO_UCB_MAX,
    OPTICAL_RATIO_MARGIN,
    TONE_EQUIVALENCE,
    algebra_audit,
    apply_transform,
    bootstrap_comparison,
    configure_threads,
    crossfit,
    environment_record,
    load_backgrounds,
    make_observations,
    range_audit,
    result_record,
    sealed_template_seed,
    source_summary,
    template_audit,
    transform_audit,
    verify_freeze,
    write_json,
)


ORDER = (
    "unclipped-usm",
    "clipped-usm",
    "gamma3",
    "logistic",
    "saturation",
    "quantization",
)


def output_path(name: str) -> Path:
    return EXPERIMENT / "out" / f"{name}.json"


def preflight(output: Path) -> int:
    configure_threads()
    backgrounds, inputs = load_backgrounds()
    data = make_observations(backgrounds, DEV_TEMPLATE_SEED, "base")
    ranges = range_audit(data)
    ladder = []
    for macro_limit in (72, 84, 96):
        result = crossfit(data, "base", macro_limit=macro_limit)
        ladder.append(
            {
                "macrotiles_per_block": macro_limit,
                "result": result_record(result),
            }
        )
    final = ladder[-1]["result"]
    numeric = final["status"] == "NUMERIC"
    d2 = final["d2"] if numeric else None
    conditions = [
        model["condition_number"] for model in final["models"]
    ]
    pass_value = bool(
        ranges["pass"]
        and numeric
        and BASE_D2_MIN <= d2 <= BASE_D2_MAX
        and len(conditions) == 5
    )
    record = {
        "stage": "baseline-only-preflight",
        "inputs": inputs,
        "source": source_summary(),
        "environment": environment_record(),
        "template_audit": template_audit(DEV_TEMPLATE_SEED),
        "range_audit": ranges,
        "conditioning_ladder": ladder,
        "pass": pass_value,
    }
    write_json(output, record)
    if numeric:
        print(
            f"PRE-FLIGHT {'GREEN' if pass_value else 'RED'}: "
            f"d2={d2:.6f}, max condition={max(conditions):.6e}, "
            f"range=[{ranges['minimum']:.6f},{ranges['maximum']:.6f}]"
        )
    else:
        print(f"PRE-FLIGHT RED: {final['refusal']}")
    return 0 if pass_value else 1


def require_previous(name: str, freeze: str) -> None:
    index = ORDER.index(name)
    for previous in ORDER[:index]:
        path = output_path(previous)
        if not path.exists():
            raise RuntimeError(f"required prior arm missing: {previous}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["freeze"]["commit"] != freeze:
            raise RuntimeError(f"prior arm freeze differs: {previous}")
        if not record["pass"]:
            raise RuntimeError(
                f"{previous} failed; frozen stop rule forbids {name}"
            )


def run_arm(name: str, freeze: str, output: Path) -> int:
    configure_threads()
    frozen = verify_freeze(freeze)
    require_previous(name, frozen["commit"])
    template_seed = sealed_template_seed(frozen["commit"])
    backgrounds, inputs = load_backgrounds()
    base_data = make_observations(backgrounds, template_seed, "base")
    if not range_audit(base_data)["pass"]:
        raise RuntimeError("sealed baseline leaves representable [0,1] range")
    transformed_data = apply_transform(base_data, name)
    base = crossfit(base_data, "base")
    arm = crossfit(transformed_data, name)
    audit = transform_audit(base_data, transformed_data)
    nonlinearity_audit = None
    if name == "clipped-usm":
        nonlinearity_audit = transform_audit(
            apply_transform(base_data, "unclipped-usm"),
            transformed_data,
        )

    comparison = None
    algebra = None
    reason = None
    if base.status != "NUMERIC":
        passed = False
        reason = f"baseline refused: {base.refusal}"
    elif arm.status != "NUMERIC":
        passed = name in ("saturation", "quantization")
        reason = arm.refusal
    else:
        comparison = bootstrap_comparison(base, arm)
        if name == "unclipped-usm":
            algebra = algebra_audit(base, arm)
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
                abs(comparison["ratio"] - 1.0) <= ALGEBRA_RATIO_TOL
                and maximum_score_error <= ALGEBRA_SCORE_TOL
                and maximum_congruence_error <= CONGRUENCE_REL_TOL
                and algebra["operator_minimum_eigenvalue"] > 0.0
            )
        elif name == "clipped-usm":
            passed = bool(
                nonlinearity_audit["changed_fraction"] >= CLIP_POTENCY_MIN
                and comparison["ratio_ucb95_one_sided"]
                <= NONLINEAR_RATIO_UCB_MAX
            )
        elif name in ("gamma3", "logistic"):
            interval = comparison["ratio_ci95_two_sided"]
            passed = bool(
                interval[0] >= 1.0 - TONE_EQUIVALENCE
                and interval[1] <= 1.0 + TONE_EQUIVALENCE
            )
        else:
            passed = bool(
                comparison["ratio"] <= 1.0
                and comparison["ratio_ucb95_one_sided"]
                <= NONLINEAR_RATIO_UCB_MAX
            )

    record = {
        "stage": "ordered-adversary",
        "arm": name,
        "order": ORDER.index(name) + 1,
        "freeze": frozen,
        "sealed_template_seed": template_seed,
        "inputs": inputs,
        "source": source_summary(),
        "environment": environment_record(),
        "template_audit": template_audit(template_seed),
        "base_range": range_audit(base_data),
        "transform_audit": audit,
        "nonlinearity_audit": nonlinearity_audit,
        "base": result_record(base),
        "candidate": result_record(arm),
        "comparison": comparison,
        "algebra_audit": algebra,
        "pass": passed,
        "reason": reason,
        "verdict": (
            "IMPLEMENTATION CHECK PASSED"
            if name == "unclipped-usm" and passed
            else "CANDIDATE 2 LIVES"
            if passed
            else "CANDIDATE 2 IS DEAD"
        ),
        "stop_after_this_arm": not passed,
    }
    write_json(output, record)
    if comparison is None:
        print(
            f"{name}: {arm.status}, pass={passed}, reason={reason} -> "
            f"{record['verdict']}"
        )
    else:
        potency = (
            f", nonlinear_changed="
            f"{nonlinearity_audit['changed_fraction']:.6f}"
            if nonlinearity_audit is not None
            else ""
        )
        print(
            f"{name}: R={comparison['ratio']:.9f}, "
            f"CI95=[{comparison['ratio_ci95_two_sided'][0]:.9f},"
            f"{comparison['ratio_ci95_two_sided'][1]:.9f}], "
            f"UCB95={comparison['ratio_ucb95_one_sided']:.9f}, "
            f"changed={audit['changed_fraction']:.6f}"
            f"{potency} -> {record['verdict']}"
        )
    return 0 if passed else 2


def require_all_adversaries(freeze: str) -> None:
    for name in ORDER:
        path = output_path(name)
        if not path.exists():
            raise RuntimeError(f"required adversary missing: {name}")
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["freeze"]["commit"] != freeze or not record["pass"]:
            raise RuntimeError(f"adversary did not pass: {name}")


def run_commission(freeze: str, output: Path) -> int:
    configure_threads()
    frozen = verify_freeze(freeze)
    require_all_adversaries(frozen["commit"])
    template_seed = sealed_template_seed(frozen["commit"])
    backgrounds, inputs = load_backgrounds()
    base_data = make_observations(backgrounds, template_seed, "base")
    degraded_data = make_observations(backgrounds, template_seed, "degraded")
    improved_data = make_observations(backgrounds, template_seed, "improved")
    null_data = apply_transform(base_data, "null")
    base = crossfit(base_data, "base")
    degraded = crossfit(degraded_data, "degraded")
    improved = crossfit(improved_data, "improved")
    null = crossfit(null_data, "null")
    comparisons = {
        "degraded": bootstrap_comparison(base, degraded),
        "improved": bootstrap_comparison(base, improved),
        "null": bootstrap_comparison(base, null),
    }
    decisions = {
        "degraded": (
            comparisons["degraded"]["ratio_ucb95_one_sided"]
            <= 1.0 - OPTICAL_RATIO_MARGIN
        ),
        "improved": (
            comparisons["improved"]["ratio_lcb95_one_sided"]
            >= 1.0 + OPTICAL_RATIO_MARGIN
        ),
        "null": abs(comparisons["null"]["ratio"] - 1.0) <= ALGEBRA_RATIO_TOL,
    }
    passed = all(decisions.values())
    record = {
        "stage": "optical-commissioning",
        "freeze": frozen,
        "sealed_template_seed": template_seed,
        "inputs": inputs,
        "source": source_summary(),
        "environment": environment_record(),
        "base": result_record(base),
        "degraded": result_record(degraded),
        "improved": result_record(improved),
        "null": result_record(null),
        "comparisons": comparisons,
        "decisions": decisions,
        "pass": passed,
        "verdict": "COMMISSIONED" if passed else "CANDIDATE 2 IS DEAD",
    }
    write_json(output, record)
    print(
        "COMMISSION "
        f"degraded={comparisons['degraded']['ratio']:.6f}, "
        f"improved={comparisons['improved']['ratio']:.6f}, "
        f"null={comparisons['null']['ratio']:.9f} -> {record['verdict']}"
    )
    return 0 if passed else 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight")
    pre.add_argument(
        "--out",
        type=Path,
        default=EXPERIMENT / "out" / "preflight.json",
    )
    arm = sub.add_parser("arm")
    arm.add_argument("name", choices=ORDER)
    arm.add_argument("--freeze", required=True)
    arm.add_argument("--out", type=Path)
    commission = sub.add_parser("commission")
    commission.add_argument("--freeze", required=True)
    commission.add_argument(
        "--out",
        type=Path,
        default=EXPERIMENT / "out" / "commission.json",
    )
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return preflight(args.out)
    if args.command == "arm":
        return run_arm(
            args.name,
            args.freeze,
            args.out or output_path(args.name),
        )
    return run_commission(args.freeze, args.out)


if __name__ == "__main__":
    sys.exit(main())
