from __future__ import annotations

import argparse
import inspect
import json
import subprocess
import sys
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
M55_SRC = REPO / "experiments" / "M55-acceptance-spec" / "src"
CAND2_SRC = REPO / "experiments" / "M-CAND2" / "src"
sys.path[:0] = [str(M55_SRC), str(CAND2_SRC)]

import cand2 as core  # noqa: E402
import spec_v1 as spec  # noqa: E402


def run_property_test(relative: str) -> dict:
    path = REPO / relative
    completed = subprocess.run(
        [sys.executable, "-B", str(path)],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return {
        "path": relative,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def swap_identity() -> dict:
    rng = np.random.default_rng(0x131C2)
    plus = rng.normal(0.25, 1.0, size=(core.TEMPLATE_COUNT, 480))
    minus = rng.normal(-0.25, 1.0, size=(core.TEMPLATE_COUNT, 480))
    forward, forward_tasks, _ = core._score(plus, minus)
    reverse, reverse_tasks, _ = core._score(minus, plus)
    return {
        "forward_d2": forward,
        "reverse_d2": reverse,
        "absolute_difference": abs(forward - reverse),
        "template_absolute_difference_max": float(
            np.max(np.abs(forward_tasks - reverse_tasks))
        ),
        "exact_at_float_precision": bool(
            forward == reverse and np.array_equal(forward_tasks, reverse_tasks)
        ),
        "meaning": (
            "If dense and sparse are used as the plus/minus classes, d-prime "
            "squared is label-swap invariant and cannot order them."
        ),
    }


def null_ratio_instability(flat_record: dict) -> dict:
    values = np.asarray(
        [
            row["d2"]
            for row in flat_record["null_rows"]
            if row["status"] == "NUMERIC" and row["d2"] is not None
        ],
        dtype=np.float64,
    )
    ratios = np.asarray(
        [
            values[i] / values[j]
            for i in range(len(values))
            for j in range(len(values))
            if i != j
        ],
        dtype=np.float64,
    )
    return {
        "n_null_readings": len(values),
        "ordered_pair_ratios": len(ratios),
        "minimum_ratio": float(ratios.min()),
        "median_ratio": float(np.median(ratios)),
        "maximum_ratio": float(ratios.max()),
        "max_over_min_d2": float(values.max() / values.min()),
    }


def battery_rows(flat_record: dict) -> dict:
    return {
        "B0": {
            "status": "FAIL",
            "reason": (
                "Candidate 2 ships no M55 Candidate declaration and no "
                "value(a,b,ctx) natural-render pairwise entry point."
            ),
        },
        "B1": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "M55 supplies one pair of half-merges per MTF rung. Candidate "
                "2 requires zero-target covariance plus separate symmetric "
                "derivative and held-out target ensembles for each system."
            ),
        },
        "B2": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "There is no Candidate 2 scalar value(a,b) to apply one-sided "
                "gain or swap to. Making dense/sparse the target classes is "
                "label-swap invariant and changes the estimand."
            ),
        },
        "B3": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "Nuisance leverage needs the same lawful comparative reading "
                "under alternate nuisance settings; no natural-output reading "
                "exists."
            ),
        },
        "B4": {
            "status": "FAIL",
            "reason": (
                "The measured no-target plant returned NUMERIC in every "
                f"repeat ({flat_record['flat_gate']['numeric_rows']}/"
                f"{flat_record['flat_gate']['null_d2']['n']}) rather than "
                "rejecting the planted wrong answer."
            ),
        },
        "B5": {
            "status": "FAIL",
            "reason": (
                "Candidate 2 declares no M55 range/status contract, and its "
                "comparative ratio denominator is not bounded away from zero "
                "on no-target inputs."
            ),
        },
        "B6": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "Each held-out M55 cell provides a natural half-merge pair, "
                "not the target-labelled covariance/derivative/test streams "
                "Candidate 2 needs."
            ),
        },
        "B7": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "The M55 repetitions sweep cannot call Candidate 2 without "
                "inventing a target task and a pairwise adapter; null d2 is "
                "strictly positive and makes ratios unstable."
            ),
        },
        "B8": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "Candidate 2 has no M55 declaration of consumed calibration. "
                "Its synthetic generator supplies signal and noise constants, "
                "so perturbing them would audit that plant, not a natural "
                "image candidate."
            ),
        },
        "B9": {
            "status": "NOT_INSTANTIABLE",
            "reason": (
                "M55's roll-null acts on value(a,b); Candidate 2 has no such "
                "reading and no registered spatial roll-null for its labelled "
                "observation ensembles."
            ),
        },
    }


def run(output: Path) -> int:
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    flat_path = HERE / "flat-control.json"
    flat_record = json.loads(flat_path.read_text(encoding="utf-8"))
    calibration = json.loads(
        (
            REPO / "experiments" / "M55-acceptance-spec" / "out" / "calibrate.json"
        ).read_text(encoding="utf-8")
    )
    b0 = spec.b0_declaration(core)
    tests = [
        run_property_test("experiments/M55-acceptance-spec/src/e14_b6_rollup_test.py"),
        run_property_test(
            "experiments/M55-acceptance-spec/src/e18_m76_constant_z_test.py"
        ),
    ]
    battery = battery_rows(flat_record)
    record = {
        "protocol": "M131-M55-applicability-v1",
        "candidate_2_interface": {
            "module": str(Path(core.__file__).relative_to(REPO)).replace("\\", "/"),
            "has_value_method": hasattr(core, "value"),
            "make_observations_signature": str(
                inspect.signature(core.make_observations)
            ),
            "crossfit_signature": str(inspect.signature(core.crossfit)),
            "m55_b0": b0,
        },
        "class_swap_test": swap_identity(),
        "flat_null_ratio_instability": null_ratio_instability(flat_record),
        "battery": battery,
        "m55_power": {
            "calibration_artifact": (
                "experiments/M55-acceptance-spec/out/calibrate.json"
            ),
            "pr27_passability_met": calibration["pr27"]["met"],
            "pr28_known_bad_power_met": calibration["pr28"]["met"],
            "known_bad_killed": calibration["pr28"]["killed"],
            "property_tests": tests,
            "all_property_tests_passed": all(test["passed"] for test in tests),
        },
        "overall": {
            "verdict": "REJECT",
            "reason": (
                "B0 and the no-target specificity/range controls fail. The "
                "remaining batteries cannot be instantiated without defining "
                "a successor instrument."
            ),
        },
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"B0={b0['passed']} missing={len(b0['missing'])} "
        f"swap_exact={record['class_swap_test']['exact_at_float_precision']} "
        f"null_ratio_span="
        f"{record['flat_null_ratio_instability']['minimum_ratio']:.3f}-"
        f"{record['flat_null_ratio_instability']['maximum_ratio']:.3f} "
        f"power={record['m55_power']['pr27_passability_met']}/"
        f"{record['m55_power']['pr28_known_bad_power_met']}"
    )
    return 0 if record["overall"]["verdict"] == "ACCEPT" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "m55-audit.json",
    )
    args = parser.parse_args()
    return run(args.out.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
