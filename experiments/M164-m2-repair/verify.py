"""Independently verify the M164 M2 synthetic commissioning artifact."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RESULT_PATH = HERE / "commission.json"
VERIFY_PATH = HERE / "verification.json"
REPORT_PATH = REPO / "docs" / "research" / "M164-m2-repair.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


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


def main() -> None:
    result = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
    checks: list[str] = []

    if result["schema"] != "m164-m2-repair-commission-v1":
        raise AssertionError("unexpected result schema")
    if result["seed"] != 164200 or result["trials"] != 256:
        raise AssertionError("registered population changed")
    if result["sites_per_trial"] != 64:
        raise AssertionError("registered site count changed")
    checks.append("schema, seed, trial count and site count are frozen")

    expected_hashes = {
        "preregistration_sha256": sha256(HERE / "PREREGISTRATION.md"),
        "amendment_1_sha256": sha256(HERE / "AMENDMENT-1.md"),
        "commission_py_sha256": sha256(HERE / "commission.py"),
    }
    if result["source_hashes"] != expected_hashes:
        raise AssertionError("source hash mismatch")
    checks.append("preregistration, amendment and implementation hashes match")

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
    checks.append("all arm summaries rederive from 256 stored trial ratios")

    for arm, fields in raw.items():
        q = np.asarray(fields["q_ein"])
        naive = np.asarray(fields["naive_output_noise_ratio"])
        transfer = np.asarray(fields["transfer_ratio"])
        if not np.allclose(q, naive / transfer, rtol=0.0, atol=1e-14):
            raise AssertionError(f"{arm}: Q_EIN identity does not rederive")
    checks.append("Q_EIN equals output-noise ratio divided by transfer ratio")

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
    if gates != result["gates"] or not all(gates.values()):
        raise AssertionError("registered gate rederivation failed")
    if result["status"] != "PASS":
        raise AssertionError("commissioning did not pass")
    checks.append("all 12 preregistered gates rederive and pass")

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
    checks.append("omitted-transfer and reversed-direction mutations are live")

    if not (
        crossfit["optical_improvement_crossfit"]["minimum"] > 1.0
        and crossfit["optical_improvement_truth_error"]["maximum"] < 1.0
    ):
        raise AssertionError("mandatory improvement conflict disappeared")
    checks.append(
        "same-resolution cross-fit rejects every genuinely improved trial"
    )

    report = REPORT_PATH.read_text(encoding="utf-8")
    anchors = (
        "NO OUTPUT-ONLY REPAIR; EXTERNAL-REFERENCE REPLACEMENT",
        "The normalization makes the residual",
        "There is no stand-alone, two-render-output repair",
        "Q_EIN                 = 0.583120x",
        "**CURRENT VERDICT: `UNMEASURED`.**",
        "**JUDGEMENT — LAND THE REPAIR NOW.**",
    )
    missing = [anchor for anchor in anchors if report.count(anchor) != 1]
    if missing:
        raise AssertionError(f"missing/non-unique report anchors: {missing}")
    checks.append("report carries the diagnosis, limitation and current verdict")

    verification = {
        "schema": "m164-m2-repair-verification-v1",
        "status": "PASS",
        "checks": checks,
        "commission_sha256": sha256(RESULT_PATH),
        "report_sha256": sha256(REPORT_PATH),
    }
    VERIFY_PATH.write_text(
        json.dumps(verification, indent=2) + "\n", encoding="utf-8"
    )
    print(f"PASS: {len(checks)} checks; wrote {VERIFY_PATH}")


if __name__ == "__main__":
    main()
