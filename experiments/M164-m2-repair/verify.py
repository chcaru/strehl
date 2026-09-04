"""Regenerate and verify the M164 M2 synthetic commissioning artifact."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, cast

for variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
):
    os.environ.setdefault(variable, "1")

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULT_PATH = HERE / "commission.json"
VERIFY_PATH = HERE / "verification.json"
REPORT_PATH = REPO / "docs" / "research" / "M164-m2-repair.md"
COMMISSION_PATH = HERE / "commission.py"
REDERIVATION = "rederivation"
ARTIFACT_CONSISTENCY = "artifact_consistency"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def load_commission() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "_m164_m2_commission_regeneration", COMMISSION_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {COMMISSION_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def regenerate_commission() -> tuple[bytes, str]:
    scratch = HERE / f".verify-regenerated-commission-{os.getpid()}.json"
    if scratch.exists():
        raise RuntimeError(f"refusing to overwrite scratch artifact: {scratch}")
    try:
        commission = load_commission()
        commission.OUTPUT = scratch
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            commission.main()
        if not scratch.is_file():
            raise RuntimeError("commission.py did not write its output")
        return scratch.read_bytes(), captured.getvalue().strip()
    finally:
        scratch.unlink(missing_ok=True)


def close(actual: float, expected: float, tolerance: float, label: str) -> None:
    if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=tolerance):
        raise AssertionError(f"{label}: {actual} != {expected} +/- {tolerance}")


def summarize(values: list[float]) -> dict[str, float | int]:
    a = np.asarray(values, dtype=np.float64)
    logs = np.log(a)
    mean_log = float(np.mean(logs))
    standard_error = float(np.std(logs, ddof=1) / math.sqrt(len(logs)))
    return {
        "minimum": float(np.min(a)),
        "q05": float(np.quantile(a, 0.05)),
        "median": float(np.median(a)),
        "geometric_mean": float(np.exp(mean_log)),
        "ci95_low": float(np.exp(mean_log - 1.96 * standard_error)),
        "ci95_high": float(np.exp(mean_log + 1.96 * standard_error)),
        "q95": float(np.quantile(a, 0.95)),
        "maximum": float(np.max(a)),
        "below_one": int(np.sum(a < 1.0)),
        "above_one": int(np.sum(a > 1.0)),
        "max_abs_from_one": float(np.max(np.abs(a - 1.0))),
    }


@dataclass(frozen=True)
class CheckOutcome:
    category: str
    name: str
    status: str
    detail: str | None = None


def two_world_witness(*, collapse_improvement_label: bool) -> dict[str, Any]:
    a = np.asarray([0.0, 0.0, 1.0, 0.0, 0.0])
    g = np.asarray(
        [
            [0.75, 0.25, 0.0, 0.0, 0.0],
            [0.25, 0.50, 0.25, 0.0, 0.0],
            [0.0, 0.25, 0.50, 0.25, 0.0],
            [0.0, 0.0, 0.25, 0.50, 0.25],
            [0.0, 0.0, 0.0, 0.25, 0.75],
        ]
    )
    b = g @ a
    degradation_observation = (a.copy(), b.copy())
    improvement_observation = (a.copy(), b.copy())
    degradation_truth = a
    improvement_truth = a if collapse_improvement_label else b

    def sse(value: np.ndarray, truth: np.ndarray) -> float:
        return float(np.sum((value - truth) ** 2))

    degradation_sse = {
        "A": sse(a, degradation_truth),
        "B": sse(b, degradation_truth),
    }
    improvement_sse = {
        "A": sse(a, improvement_truth),
        "B": sse(b, improvement_truth),
    }
    observations_identical = bool(
        np.array_equal(degradation_observation[0], improvement_observation[0])
        and np.array_equal(
            degradation_observation[1], improvement_observation[1]
        )
    )
    opposite_rankings = bool(
        degradation_sse["A"] < degradation_sse["B"]
        and improvement_sse["B"] < improvement_sse["A"]
    )
    return {
        "A": a.tolist(),
        "G": g.tolist(),
        "B": b.tolist(),
        "observations_identical": observations_identical,
        "degradation_truth_sse": degradation_sse,
        "improvement_truth_sse": improvement_sse,
        "opposite_rankings": opposite_rankings,
    }


def category_summary(
    outcomes: list[CheckOutcome], category: str
) -> dict[str, Any]:
    selected = [outcome for outcome in outcomes if outcome.category == category]
    passed = sum(outcome.status == "PASS" for outcome in selected)
    failed = sum(outcome.status == "FAIL" for outcome in selected)
    skipped = sum(outcome.status == "SKIP" for outcome in selected)
    total = len(selected)
    return {
        "status": "PASS" if passed == total else "RED",
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": total,
        "checks": [asdict(outcome) for outcome in selected],
    }


def print_summary(label: str, summary: dict[str, Any]) -> None:
    print(
        f"{label}: {summary['status']} "
        f"{summary['passed']}/{summary['total']} passed; "
        f"{summary['failed']} failed; {summary['skipped']} skipped"
    )
    for check in summary["checks"]:
        if check["status"] != "PASS":
            print(
                f"  {check['status']} {check['name']}: "
                f"{check['detail']}"
            )


def verify_schema(result: dict[str, Any]) -> None:
    if result["schema"] != "m164-m2-repair-commission-v1":
        raise AssertionError("unexpected result schema")
    if result["seed"] != 164200 or result["trials"] != 256:
        raise AssertionError("registered population changed")
    if result["sites_per_trial"] != 64:
        raise AssertionError("registered site count changed")


def verify_source_hashes(result: dict[str, Any]) -> None:
    expected_hashes = {
        "preregistration_sha256": sha256(HERE / "PREREGISTRATION.md"),
        "amendment_1_sha256": sha256(HERE / "AMENDMENT-1.md"),
        "commission_py_sha256": sha256(HERE / "commission.py"),
    }
    if result["source_hashes"] != expected_hashes:
        raise AssertionError("source hash mismatch")


def verify_summaries(result: dict[str, Any]) -> None:
    raw = result["raw_trial_ratios"]
    summaries = result["summaries"]
    for arm, fields in raw.items():
        for field, values in fields.items():
            rebuilt = summarize(values)
            recorded = summaries[arm][field]
            for key, expected in rebuilt.items():
                actual = recorded[key]
                if isinstance(expected, int):
                    if actual != expected:
                        raise AssertionError(
                            f"{arm}/{field}/{key}: {actual} != {expected}"
                        )
                else:
                    close(
                        float(actual),
                        float(expected),
                        1e-15,
                        f"{arm}/{field}/{key}",
                    )


def verify_q_ein_identity(result: dict[str, Any]) -> None:
    raw = result["raw_trial_ratios"]
    for arm, fields in raw.items():
        q = np.asarray(fields["q_ein"])
        naive = np.asarray(fields["naive_output_noise_ratio"])
        transfer = np.asarray(fields["transfer_ratio"])
        if not np.allclose(q, naive / transfer, rtol=0.0, atol=1e-14):
            raise AssertionError(f"{arm}: Q_EIN identity does not rederive")


def derived_gates(result: dict[str, Any]) -> dict[str, bool]:
    summaries = result["summaries"]
    gates = {
        "G0_identity": summaries["identity"]["q_ein"]["max_abs_from_one"]
        <= 1e-12,
        "G1_movable_null": (
            summaries["fresh_null"]["q_ein"]["minimum"] < 1.0
            < summaries["fresh_null"]["q_ein"]["maximum"]
            and 0.98
            <= summaries["fresh_null"]["q_ein"]["geometric_mean"]
            <= 1.02
        ),
        "G2_noise_degradation": (
            summaries["noise_degradation"]["q_ein"]["below_one"] == 0
            and summaries["noise_degradation"]["q_ein"]["q05"] > 1.20
        ),
        "G3_denoising_improvement": (
            summaries["denoising_improvement"]["q_ein"]["above_one"] == 0
            and summaries["denoising_improvement"]["q_ein"]["q95"] < 0.75
        ),
        "G4_pre_noise_blur": (
            summaries["pre_noise_blur"]["q_ein"]["below_one"] == 0
            and summaries["pre_noise_blur"]["q_ein"]["q05"] > 1.20
        ),
        "G5_optical_improvement": (
            summaries["optical_improvement"]["q_ein"]["above_one"] == 0
            and summaries["optical_improvement"]["q_ein"]["q95"] < 0.90
        ),
        "G6_post_blur_invariance": (
            summaries["post_blur"]["q_ein"]["max_abs_from_one"] <= 1e-12
            and summaries["post_blur"]["naive_output_noise_ratio"]["maximum"]
            < 0.90
        ),
        "G7_post_usm_invariance": (
            summaries["post_usm"]["q_ein"]["max_abs_from_one"] <= 1e-12
        ),
        "G8_gain_invariance": (
            summaries["post_gain"]["q_ein"]["max_abs_from_one"] <= 1e-12
        ),
    }

    mechanism = result["m159_mechanism_probe"]
    gates["G9_m159_mechanism"] = (
        mechanism["fractional_r_box9_blurred_over_unblurred"] < 0.90
        and mechanism["additive_box9_over_global_mean_blurred_over_unblurred"]
        < 0.90
        and 0.99
        <= mechanism["median_local_mean_blurred_over_unblurred"]
        <= 1.01
    )
    gates["G10_blur_plus_denoise_requires_m1"] = (
        summaries["blur_plus_denoise"]["q_ein"]["q95"] < 0.80
        and summaries["blur_plus_denoise"]["transfer_ratio"]["q95"] < 0.70
    )

    crossfit = result["same_resolution_crossfit_probe"]["summaries"]
    gates["G11_same_resolution_crossfit_fails_improvement"] = (
        crossfit["blur_crossfit"]["q05"] > 1.10
        and crossfit["optical_improvement_crossfit"]["q05"] > 1.10
        and crossfit["optical_improvement_truth_error"]["q95"] < 0.90
        and crossfit["blur_truth_error"]["q05"] > 1.10
        and crossfit["denoising_improvement_crossfit"]["q95"] < 0.90
    )
    return gates


def verify_gates(result: dict[str, Any]) -> None:
    gates = derived_gates(result)
    if gates != result["gates"] or not all(gates.values()):
        raise AssertionError("registered gate rederivation failed")
    if result["status"] != "PASS":
        raise AssertionError("commissioning did not pass")


def verify_mutations(result: dict[str, Any]) -> None:
    summaries = result["summaries"]
    if not (
        summaries["post_blur"]["naive_output_noise_ratio"]["geometric_mean"]
        < 0.90
        and summaries["post_blur"]["q_ein"]["max_abs_from_one"] <= 1e-12
    ):
        raise AssertionError("omitted-transfer mutation is not live")
    if not (
        1.0
        / summaries["noise_degradation"]["q_ein"]["geometric_mean"]
        < 1.0
    ):
        raise AssertionError("ratio-direction mutation is not live")


def verify_crossfit(result: dict[str, Any]) -> None:
    crossfit = result["same_resolution_crossfit_probe"]["summaries"]
    if not (
        crossfit["optical_improvement_crossfit"]["minimum"] > 1.0
        and crossfit["optical_improvement_truth_error"]["maximum"] < 1.0
    ):
        raise AssertionError("mandatory improvement conflict disappeared")


def verify_theorem(witness: dict[str, Any]) -> None:
    if not witness["observations_identical"]:
        raise AssertionError("the two latent worlds expose different observations")
    degradation = witness["degradation_truth_sse"]
    improvement = witness["improvement_truth_sse"]
    expected = (
        degradation["A"] == 0.0
        and degradation["B"] == 0.375
        and improvement["A"] == 0.375
        and improvement["B"] == 0.0
    )
    if not expected or not witness["opposite_rankings"]:
        raise AssertionError(
            "opposite rankings absent: "
            f"degradation=({degradation['A']:.6f},{degradation['B']:.6f}), "
            f"improvement=({improvement['A']:.6f},{improvement['B']:.6f})"
        )


def verify_report() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")
    anchors = (
        "NO OUTPUT-ONLY REPAIR; EXTERNAL-REFERENCE CANDIDATE",
        "The normalization makes the residual",
        "There is no stand-alone, two-render-output repair",
        "Q_EIN                 = 0.583120x",
        "**CURRENT VERDICT: `UNMEASURED`.**",
        "**JUDGEMENT — LAND THE CANDIDATE NOW, NOT THE CLAIM.**",
    )
    missing = [anchor for anchor in anchors if report.count(anchor) != 1]
    if missing:
        raise AssertionError(f"missing/non-unique report anchors: {missing}")


def verify_artifact_bytes(regenerated: bytes, committed: bytes) -> None:
    if regenerated != committed:
        raise AssertionError(
            "byte mismatch: "
            f"committed={sha256_bytes(committed)}, "
            f"regenerated={sha256_bytes(regenerated)}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--plant-defect",
        choices=("theorem-label-collapse",),
        help="commission the verifier by planting a known theorem defect",
    )
    arguments = parser.parse_args(argv)

    print(
        "VERIFY MODE: fresh regeneration + theorem re-derivation",
        flush=True,
    )
    if arguments.plant_defect:
        print(f"PLANTED DEFECT: {arguments.plant_defect}")

    outcomes: list[CheckOutcome] = []
    regenerated_bytes: bytes | None = None
    commission_stdout: str | None = None
    result: dict[str, Any] | None = None

    def run_check(
        category: str,
        name: str,
        function: Callable[[], None],
    ) -> None:
        try:
            function()
        except Exception as error:
            outcomes.append(
                CheckOutcome(
                    category,
                    name,
                    "FAIL",
                    f"{type(error).__name__}: {error}",
                )
            )
        else:
            outcomes.append(CheckOutcome(category, name, "PASS"))

    def skip_check(category: str, name: str, reason: str) -> None:
        outcomes.append(CheckOutcome(category, name, "SKIP", reason))

    def regenerate() -> None:
        nonlocal regenerated_bytes, commission_stdout, result
        regenerated_bytes, commission_stdout = regenerate_commission()
        result = json.loads(regenerated_bytes)

    run_check(
        REDERIVATION,
        "fresh commission regeneration",
        regenerate,
    )

    result_checks: tuple[tuple[str, Callable[[dict[str, Any]], None]], ...] = (
        ("registered schema and population", verify_schema),
        ("source hashes", verify_source_hashes),
        ("summaries from regenerated trial ratios", verify_summaries),
        ("Q_EIN algebraic identity", verify_q_ein_identity),
        ("all 12 registered gates", verify_gates),
        ("registered mutations are live", verify_mutations),
        ("same-resolution cross-fit conflict", verify_crossfit),
    )
    for name, function in result_checks:
        if result is None:
            skip_check(REDERIVATION, name, "fresh regeneration unavailable")
        else:
            run_check(
                REDERIVATION,
                name,
                lambda function=function: function(result),
            )

    witness = two_world_witness(
        collapse_improvement_label=(
            arguments.plant_defect == "theorem-label-collapse"
        )
    )
    run_check(
        REDERIVATION,
        "two-world witness has identical observations and opposite rankings",
        lambda: verify_theorem(witness),
    )

    if regenerated_bytes is None:
        skip_check(
            ARTIFACT_CONSISTENCY,
            "regenerated artifact equals committed commission.json",
            "fresh regeneration unavailable",
        )
    else:
        def compare_artifact() -> None:
            committed_bytes = RESULT_PATH.read_bytes()
            verify_artifact_bytes(regenerated_bytes, committed_bytes)

        run_check(
            ARTIFACT_CONSISTENCY,
            "regenerated artifact equals committed commission.json",
            compare_artifact,
        )
    run_check(
        ARTIFACT_CONSISTENCY,
        "report anchors",
        verify_report,
    )

    rederivation = category_summary(outcomes, REDERIVATION)
    artifact = category_summary(outcomes, ARTIFACT_CONSISTENCY)
    total_passed = rederivation["passed"] + artifact["passed"]
    total_failed = rederivation["failed"] + artifact["failed"]
    total_skipped = rederivation["skipped"] + artifact["skipped"]
    total = rederivation["total"] + artifact["total"]
    total_summary = {
        "status": (
            "PASS"
            if total_passed == total and total_failed == 0 and total_skipped == 0
            else "RED"
        ),
        "passed": total_passed,
        "failed": total_failed,
        "skipped": total_skipped,
        "total": total,
    }

    print_summary("REDERIVATION", rederivation)
    print_summary("ARTIFACT-CONSISTENCY", artifact)
    print(
        f"TOTAL: {total_summary['status']} "
        f"{total_summary['passed']}/{total_summary['total']} passed; "
        f"{total_summary['failed']} failed; "
        f"{total_summary['skipped']} skipped"
    )

    if total_summary["status"] != "PASS":
        return 1

    regenerated_bytes = cast(bytes, regenerated_bytes)
    commission_stdout = cast(str, commission_stdout)
    verification = {
        "schema": "m164-m2-repair-verification-v3",
        "status": "PASS",
        "verification_mode": (
            "fresh regeneration and theorem re-derivation, separately "
            "reported from artifact consistency"
        ),
        "categories": {
            REDERIVATION: rederivation,
            ARTIFACT_CONSISTENCY: artifact,
        },
        "summary": total_summary,
        "commission_sha256": sha256(RESULT_PATH),
        "verify_py_sha256": sha256(Path(__file__)),
        "regeneration": {
            "regenerated_sha256": sha256_bytes(regenerated_bytes),
            "commission_stdout": commission_stdout,
        },
        "two_world_witness": witness,
        "report_sha256": sha256(REPORT_PATH),
    }
    VERIFY_PATH.write_text(
        json.dumps(verification, indent=2) + "\n", encoding="utf-8"
    )
    print(f"WROTE: {VERIFY_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
