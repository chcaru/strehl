from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from pathlib import Path


BASE_MIN = 0.08
BASE_MAX = 0.85
USM_UCB_MAX = 1.01
NULL_LOW = 0.99
NULL_HIGH = 1.01
DEGRADED_UCB_MAX = 0.70
IMPROVED_LCB_MIN = 1.30


def close(a: float, b: float, tolerance: float = 1e-12) -> bool:
    return math.isclose(float(a), float(b), rel_tol=tolerance, abs_tol=tolerance)


def check_preflight(record: dict) -> list[str]:
    errors = []
    curve = record["learning_curve"]
    if record.get("stage") != "preflight-before-sealed-test":
        errors.append("wrong preflight stage")
    if not record.get("pass"):
        errors.append("preflight did not pass")
    if not curve["plateau_pass"]:
        errors.append("learning curve did not plateau")
    if not curve["base_dynamic_range_pass"]:
        errors.append("baseline outside dynamic range")
    if not curve["arm_blind_power"]["pass"]:
        errors.append("commissioning margin is under-powered")
    if not record["label_balance"]["all_balanced"]:
        errors.append("labels are not balanced within macro-tiles")
    if record["task_audit"]["active_frequency_max"] > 0.25:
        errors.append("task exceeds licensed frequency")
    if record["task_audit"]["worst_relative_magnitude_error"] > 1e-12:
        errors.append("target alternatives do not match in Fourier magnitude")
    if record["task_audit"]["worst_outside_band_energy_fraction"] > 1e-20:
        errors.append("target leaks outside task band")
    return errors


def comparison_arithmetic(comparison: dict) -> list[str]:
    errors = []
    base = float(comparison["base_j_bits"])
    arm = float(comparison["arm_j_bits"])
    if not close(comparison["ratio"], arm / base):
        errors.append("reported ratio does not equal arm/base")
    if not close(comparison["paired_log_ratio"], math.log(arm / base)):
        errors.append("reported log ratio is inconsistent")
    if not close(comparison["delta_bits"], arm - base):
        errors.append("reported delta is inconsistent")
    if comparison["minimum_bootstrap_base_j"] <= 0.0:
        errors.append("bootstrap ratio has a non-positive base")
    return errors


def check_usm(record: dict) -> list[str]:
    errors = []
    if record.get("stage") != "first-scientific-comparison":
        errors.append("USM was not labelled the first scientific comparison")
    if record.get("arm_order") != 1:
        errors.append("USM arm order is not one")
    if record["source"]["task"]["usm_radius"] != 1.0:
        errors.append("USM radius changed")
    if record["source"]["task"]["usm_amount"] != 0.5:
        errors.append("USM amount changed")
    comparison = record["comparison"]
    errors.extend(comparison_arithmetic(comparison))
    expected = bool(
        BASE_MIN <= comparison["base_j_bits"] <= BASE_MAX
        and comparison["ratio_ucb95_one_sided"] <= USM_UCB_MAX
    )
    if record.get("pass") != expected:
        errors.append("USM verdict does not follow literal gate")
    expected_text = "CANDIDATE 1 LIVES" if expected else "CANDIDATE 1 IS DEAD"
    if record.get("verdict") != expected_text:
        errors.append("USM verdict text is inconsistent")
    if record.get("stop_after_this_arm") != (not expected):
        errors.append("USM stop flag is inconsistent")
    return errors


def check_commission(record: dict) -> list[str]:
    errors = []
    if record.get("stage") != "post-usm-commissioning":
        errors.append("wrong commissioning stage")
    comparisons = record["comparisons"]
    for value in comparisons.values():
        errors.extend(comparison_arithmetic(value))
    null_ci = comparisons["null"]["ratio_ci95_two_sided"]
    null_pass = null_ci[0] >= NULL_LOW and null_ci[1] <= NULL_HIGH
    degraded_pass = (
        comparisons["degraded"]["ratio_ucb95_one_sided"] <= DEGRADED_UCB_MAX
    )
    improved_pass = (
        comparisons["improved"]["ratio_lcb95_one_sided"] >= IMPROVED_LCB_MIN
    )
    expected = {
        "null_pass": null_pass,
        "degraded_pass": degraded_pass,
        "improved_pass": improved_pass,
    }
    if record.get("decisions") != expected:
        errors.append("commissioning decisions do not follow literal gates")
    if record.get("pass") != all(expected.values()):
        errors.append("commissioning aggregate verdict is inconsistent")
    return errors


def validate(kind: str, record: dict) -> list[str]:
    if kind == "preflight":
        return check_preflight(record)
    if kind == "usm":
        return check_usm(record)
    return check_commission(record)


def green_fixture(kind: str) -> dict:
    comparison = {
        "base_j_bits": 0.20,
        "arm_j_bits": 0.20,
        "ratio": 1.0,
        "paired_log_ratio": 0.0,
        "delta_bits": 0.0,
        "ratio_lcb95_one_sided": 0.999,
        "ratio_ucb95_one_sided": 1.001,
        "ratio_ci95_two_sided": [0.999, 1.001],
        "delta_ci95_two_sided": [-0.001, 0.001],
        "minimum_bootstrap_base_j": 0.10,
    }
    if kind == "preflight":
        return {
            "stage": "preflight-before-sealed-test",
            "pass": True,
            "learning_curve": {
                "plateau_pass": True,
                "base_dynamic_range_pass": True,
                "arm_blind_power": {"pass": True},
            },
            "label_balance": {"all_balanced": True},
            "task_audit": {
                "active_frequency_max": 0.24,
                "worst_relative_magnitude_error": 1e-15,
                "worst_outside_band_energy_fraction": 1e-30,
            },
        }
    if kind == "usm":
        return {
            "stage": "first-scientific-comparison",
            "arm_order": 1,
            "source": {"task": {"usm_radius": 1.0, "usm_amount": 0.5}},
            "comparison": comparison,
            "pass": True,
            "verdict": "CANDIDATE 1 LIVES",
            "stop_after_this_arm": False,
        }
    degraded = copy.deepcopy(comparison)
    degraded.update(
        {
            "arm_j_bits": 0.10,
            "ratio": 0.5,
            "paired_log_ratio": math.log(0.5),
            "delta_bits": -0.10,
            "ratio_ucb95_one_sided": 0.60,
        }
    )
    improved = copy.deepcopy(comparison)
    improved.update(
        {
            "arm_j_bits": 0.40,
            "ratio": 2.0,
            "paired_log_ratio": math.log(2.0),
            "delta_bits": 0.20,
            "ratio_lcb95_one_sided": 1.80,
        }
    )
    return {
        "stage": "post-usm-commissioning",
        "comparisons": {
            "null": comparison,
            "degraded": degraded,
            "improved": improved,
        },
        "decisions": {
            "null_pass": True,
            "degraded_pass": True,
            "improved_pass": True,
        },
        "pass": True,
    }


def self_test() -> int:
    mutations = {
        "preflight": [
            lambda x: x.update(stage="wrong"),
            lambda x: x["learning_curve"].update(plateau_pass=False),
            lambda x: x["task_audit"].update(active_frequency_max=0.3),
        ],
        "usm": [
            lambda x: x.update(arm_order=2),
            lambda x: x["source"]["task"].update(usm_amount=0.4),
            lambda x: x["comparison"].update(ratio_ucb95_one_sided=1.02),
            lambda x: x["comparison"].update(ratio=1.2),
        ],
        "commission": [
            lambda x: x["comparisons"]["null"].update(
                ratio_ci95_two_sided=[0.98, 1.02]
            ),
            lambda x: x["comparisons"]["degraded"].update(
                ratio_ucb95_one_sided=0.8
            ),
            lambda x: x["comparisons"]["improved"].update(
                ratio_lcb95_one_sided=1.2
            ),
        ],
    }
    caught = 0
    total = 0
    for kind, plants in mutations.items():
        fixture = green_fixture(kind)
        if validate(kind, fixture):
            print(f"SELF-TEST base fixture failed for {kind}")
            return 1
        for plant in plants:
            total += 1
            mutant = copy.deepcopy(fixture)
            plant(mutant)
            if validate(kind, mutant):
                caught += 1
            else:
                print(f"SELF-TEST missed {kind} mutation {total}")
    print(f"SELF-TEST caught {caught}/{total} literal-gate mutations")
    return 0 if caught == total else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", nargs="?", choices=("preflight", "usm", "commission"))
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.kind is None or args.path is None:
        parser.error("kind and path are required without --self-test")
    record = json.loads(args.path.read_text(encoding="utf-8"))
    errors = validate(args.kind, record)
    if errors:
        for error in errors:
            print(f"RED: {error}")
        return 1
    print(f"GREEN: {args.kind} result follows frozen literal gates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
