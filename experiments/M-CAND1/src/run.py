from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cand1 import (
    BASE_J_MAX,
    BASE_J_MIN,
    COMMISSION_RATIO_MARGIN,
    DEV_PATTERN_SEED,
    EXPERIMENT,
    NULL_EQUIVALENCE,
    USM_RATIO_UCB_MAX,
    arm_record,
    bootstrap_comparison,
    check_label_balance,
    configure_threads,
    crossfit_arm,
    ensure_no_holdout_paths,
    environment_record,
    learning_curve,
    load_backgrounds,
    make_samples,
    source_summary,
    task_audit,
    test_seed_from_freeze,
    transfer_audit,
    verify_freeze,
    write_json,
)


def preflight(output: Path) -> int:
    configure_threads()
    backgrounds, input_record = load_backgrounds()
    ensure_no_holdout_paths(input_record)
    balance = check_label_balance(
        make_samples(backgrounds, "base", DEV_PATTERN_SEED)
    )
    curve = learning_curve(backgrounds)
    result = {
        "stage": "preflight-before-sealed-test",
        "inputs": input_record,
        "source": source_summary(),
        "environment": environment_record(),
        "task_audit": task_audit(),
        "transfer_audit": transfer_audit(),
        "label_balance": balance,
        "learning_curve": curve,
        "pass": bool(
            balance["all_balanced"]
            and curve["plateau_pass"]
            and curve["base_dynamic_range_pass"]
            and curve["arm_blind_power"]["pass"]
        ),
    }
    write_json(output, result)
    print(
        f"PRE-FLIGHT {'GREEN' if result['pass'] else 'RED'}: "
        f"J={curve['points'][-1]['j_bits']:.6f} bits, "
        f"plateau delta={curve['plateau_delta_bits_72_to_96']:.6f} bits, "
        f"MDE={curve['arm_blind_power']['minimum_detectable_ratio_change']:.4f}"
    )
    return 0 if result["pass"] else 1


def run_usm(freeze: str, output: Path) -> int:
    configure_threads()
    frozen = verify_freeze(freeze)
    sealed_seed = test_seed_from_freeze(frozen["commit"])
    backgrounds, input_record = load_backgrounds()
    ensure_no_holdout_paths(input_record)
    base = crossfit_arm(backgrounds, "base", sealed_seed)
    usm = crossfit_arm(backgrounds, "usm", sealed_seed)
    comparison = bootstrap_comparison(base, usm)
    base_usable = BASE_J_MIN <= base.j_bits <= BASE_J_MAX
    passed = bool(
        base_usable
        and comparison["ratio_ucb95_one_sided"] <= USM_RATIO_UCB_MAX
    )
    result = {
        "stage": "first-scientific-comparison",
        "arm_order": 1,
        "freeze": frozen,
        "sealed_test_seed": sealed_seed,
        "inputs": input_record,
        "source": source_summary(),
        "environment": environment_record(),
        "task_audit": task_audit(),
        "transfer_audit": transfer_audit(),
        "base": arm_record(base),
        "usm": arm_record(usm),
        "comparison": comparison,
        "decision_rule": {
            "base_j_must_be_bits": [BASE_J_MIN, BASE_J_MAX],
            "one_sided_ratio_ucb95_must_be_lte": USM_RATIO_UCB_MAX,
            "base_usable": base_usable,
        },
        "pass": passed,
        "verdict": "CANDIDATE 1 LIVES" if passed else "CANDIDATE 1 IS DEAD",
        "stop_after_this_arm": not passed,
    }
    write_json(output, result)
    print(
        f"USM R={comparison['ratio']:.6f}, "
        f"UCB95={comparison['ratio_ucb95_one_sided']:.6f}, "
        f"delta={comparison['delta_bits']:+.6f} bits -> {result['verdict']}"
    )
    return 0 if passed else 2


def run_commission(freeze: str, usm_path: Path, output: Path) -> int:
    configure_threads()
    frozen = verify_freeze(freeze)
    usm_record = __import__("json").loads(usm_path.read_text(encoding="utf-8"))
    if not usm_record.get("pass"):
        raise RuntimeError("USM did not pass; frozen stop rule forbids later arms")
    if usm_record["freeze"]["commit"] != frozen["commit"]:
        raise RuntimeError("commissioning freeze differs from USM freeze")
    sealed_seed = int(usm_record["sealed_test_seed"])
    backgrounds, input_record = load_backgrounds()
    ensure_no_holdout_paths(input_record)
    base = crossfit_arm(backgrounds, "base", sealed_seed)
    null = crossfit_arm(backgrounds, "null", sealed_seed)
    degraded = crossfit_arm(backgrounds, "degraded", sealed_seed)
    improved = crossfit_arm(backgrounds, "improved", sealed_seed)

    null_comparison = bootstrap_comparison(base, null)
    degraded_comparison = bootstrap_comparison(base, degraded)
    improved_comparison = bootstrap_comparison(base, improved)
    null_pass = bool(
        null_comparison["ratio_ci95_two_sided"][0] >= 1.0 - NULL_EQUIVALENCE
        and null_comparison["ratio_ci95_two_sided"][1] <= 1.0 + NULL_EQUIVALENCE
    )
    degraded_pass = bool(
        degraded_comparison["ratio_ucb95_one_sided"]
        <= 1.0 - COMMISSION_RATIO_MARGIN
    )
    improved_pass = bool(
        improved_comparison["ratio_lcb95_one_sided"]
        >= 1.0 + COMMISSION_RATIO_MARGIN
    )
    passed = null_pass and degraded_pass and improved_pass
    result = {
        "stage": "post-usm-commissioning",
        "freeze": frozen,
        "sealed_test_seed": sealed_seed,
        "inputs": input_record,
        "source": source_summary(),
        "environment": environment_record(),
        "base": arm_record(base),
        "null": arm_record(null),
        "degraded": arm_record(degraded),
        "improved": arm_record(improved),
        "comparisons": {
            "null": null_comparison,
            "degraded": degraded_comparison,
            "improved": improved_comparison,
        },
        "decision_rule": {
            "null_ratio_ci95_inside": [
                1.0 - NULL_EQUIVALENCE,
                1.0 + NULL_EQUIVALENCE,
            ],
            "degraded_ratio_ucb95_lte": 1.0 - COMMISSION_RATIO_MARGIN,
            "improved_ratio_lcb95_gte": 1.0 + COMMISSION_RATIO_MARGIN,
        },
        "decisions": {
            "null_pass": null_pass,
            "degraded_pass": degraded_pass,
            "improved_pass": improved_pass,
        },
        "pass": passed,
        "verdict": "COMMISSIONED" if passed else "COMMISSIONING FAILED",
    }
    write_json(output, result)
    print(
        f"NULL R={null_comparison['ratio']:.6f}; "
        f"DEGRADE R={degraded_comparison['ratio']:.6f}, "
        f"UCB95={degraded_comparison['ratio_ucb95_one_sided']:.6f}; "
        f"IMPROVE R={improved_comparison['ratio']:.6f}, "
        f"LCB95={improved_comparison['ratio_lcb95_one_sided']:.6f} -> "
        f"{result['verdict']}"
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

    usm = sub.add_parser("usm")
    usm.add_argument("--freeze", required=True)
    usm.add_argument(
        "--out",
        type=Path,
        default=EXPERIMENT / "out" / "usm.json",
    )

    commission = sub.add_parser("commission")
    commission.add_argument("--freeze", required=True)
    commission.add_argument(
        "--usm",
        type=Path,
        default=EXPERIMENT / "out" / "usm.json",
    )
    commission.add_argument(
        "--out",
        type=Path,
        default=EXPERIMENT / "out" / "commission.json",
    )

    args = parser.parse_args(argv)
    if args.command == "preflight":
        return preflight(args.out)
    if args.command == "usm":
        return run_usm(args.freeze, args.out)
    return run_commission(args.freeze, args.usm, args.out)


if __name__ == "__main__":
    sys.exit(main())
