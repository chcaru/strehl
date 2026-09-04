"""Independent serialized-result checker for the M167 detail battery.

This module imports neither fixtures.py nor measure.py nor candidate code.
Built-in measurements arrive only through child-process JSON.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULT_PATH = HERE / "results.json"
BLUR_SIGMAS = [0.0, 0.5, 1.0, 1.5]
PREDICATES = ("P1", "P2", "P3", "P4", "P5", "P6")
REJECTION_PRIORITY = PREDICATES

FIXTURE_SHA256 = (
    "7082DD08A51E3D74D9C402275F68342344AAB7E17112E753985FA4692F626B36"
)
D8_SHA256 = "C0408661BDDF15554BB8EC0F3D10C972D88CB632AF226C2E6944466855898288"
BAND_SHA256 = "4AAE9064AD89C7846492C00EA1FC60A1965CEC3A6AB7550BF84634C9E021EC1D"
BAND_EVIDENCE_SHA256 = (
    "79E257EA22103C2D0C17E84A518249BA69F61457301190BC07EBFB43CAEDB5EB"
)
BAND_REPORT_SHA256 = (
    "9BA4CA24C9DAB0656A2DD6F8CC3F9F3AF6225D291BE21180F2D733627D8689AA"
)
M2_SHA256 = "6109FAFFF52F3C287DE2DEACC57B76843215D72CA4AD155E3BBB92BC4F057DA9"
M2_RESULT_SHA256 = (
    "5EBA810719313ECD85116E268965FE699C43E0EA32BC4D43B6354FDE8DD30389"
)
BAND_DETAIL_GAP = 0.3403664343410666
BAND_FLAT_GAP = 0.3488548829813006
BAND_FLAT_DETAIL_RATIO = 1.0249391472947889
BAND_STRUCTURE_SHARE = 0.13314850036584688
M2_FROZEN_BLUR_RATIO = 0.5712148772282098


def point(score: float) -> dict[str, object]:
    return {"status": "VALUE", "score": float(score)}


def interval(record: object) -> tuple[float, float]:
    if not isinstance(record, dict):
        raise ValueError("record is not an object")
    status = record.get("status")
    if status not in ("VALUE", "LOWER_BOUND", "UPPER_BOUND"):
        raise ValueError(f"record is not numeric/bounded: {status!r}")
    score = record.get("score")
    if (
        isinstance(score, bool)
        or not isinstance(score, (int, float))
        or not math.isfinite(float(score))
    ):
        raise ValueError("record score is not finite")
    value = float(score)
    if status == "VALUE":
        return value, value
    if status == "LOWER_BOUND":
        return value, math.inf
    return -math.inf, value


def protected(
    function: Callable[[], tuple[bool, dict[str, object]]]
) -> tuple[bool, dict[str, object]]:
    try:
        passed, detail = function()
        return bool(passed), detail
    except Exception as error:
        return False, {
            "error": f"{type(error).__name__}: {error}",
        }


def adjudicate(result: dict[str, object]) -> dict[str, object]:
    arms = result.get("arms")
    if not isinstance(arms, dict):
        arms = {}

    def p1() -> tuple[bool, dict[str, object]]:
        arm = arms["flat_roi"]
        detail_record = arm["detail"]
        flat_record = arm["flat"]
        detail_interval = interval(detail_record)
        explicit_refusal = (
            isinstance(flat_record, dict)
            and flat_record.get("status") == "REFUSED"
            and flat_record.get("code") in ("NO_DETAIL", "FEATURELESS")
        )
        flat_interval = None
        separated = False
        if not explicit_refusal:
            flat_interval = interval(flat_record)
            separated = flat_interval[1] < detail_interval[0]
        return explicit_refusal or separated, {
            "detail": detail_record,
            "flat": flat_record,
            "explicit_featureless_refusal": explicit_refusal,
            "intervals_separated": separated,
        }

    def p2() -> tuple[bool, dict[str, object]]:
        arm = arms["planted_improvement"]
        base = interval(arm["base"])
        improved = interval(arm["improved"])
        return improved[0] > base[1], {
            "base": arm["base"],
            "improved": arm["improved"],
        }

    def p3() -> tuple[bool, dict[str, object]]:
        arm = arms["planted_degradation"]
        base = interval(arm["base"])
        degraded = interval(arm["degraded"])
        return degraded[1] < base[0], {
            "base": arm["base"],
            "degraded": arm["degraded"],
        }

    def p4() -> tuple[bool, dict[str, object]]:
        ladder = arms["blur_monotonicity"]
        if not isinstance(ladder, list) or len(ladder) != len(BLUR_SIGMAS):
            raise ValueError("blur ladder has wrong length")
        got_sigmas = [float(item["added_sigma_px"]) for item in ladder]
        if got_sigmas != BLUR_SIGMAS:
            raise ValueError(
                f"blur ladder sigmas {got_sigmas!r} != {BLUR_SIGMAS!r}"
            )
        intervals = [interval(item["measurement"]) for item in ladder]
        steps = [
            intervals[index + 1][1] < intervals[index][0]
            for index in range(len(intervals) - 1)
        ]
        return all(steps), {
            "ladder": ladder,
            "strictly_decreasing_steps": steps,
        }

    def p5() -> tuple[bool, dict[str, object]]:
        arm = arms["sharpening_discrimination"]
        base = interval(arm["base"])
        improved = interval(arm["improved"])
        usm_record = arm["usm"]
        true_improvement = improved[0] > base[1]
        sharp_refusal = (
            isinstance(usm_record, dict)
            and usm_record.get("status") == "REFUSED"
            and usm_record.get("code") == "SHARPENING_UNSAFE"
        )
        usm_not_improved = False
        if not sharp_refusal:
            usm = interval(usm_record)
            usm_not_improved = usm[1] <= base[0]
        return true_improvement and (
            sharp_refusal or usm_not_improved
        ), {
            "base": arm["base"],
            "usm": usm_record,
            "improved": arm["improved"],
            "true_improvement": true_improvement,
            "explicit_sharpening_refusal": sharp_refusal,
            "usm_not_improved": usm_not_improved,
        }

    def p6() -> tuple[bool, dict[str, object]]:
        arm = arms["fail_closed"]
        statuses = {}
        for name in ("nonfinite", "wrong_shape"):
            record = arm[name]
            if not isinstance(record, dict):
                raise ValueError(f"{name} record is not an object")
            statuses[name] = record.get("status")
        return all(
            status in ("REFUSED", "ERROR") for status in statuses.values()
        ), {
            "records": {
                name: arm[name] for name in ("nonfinite", "wrong_shape")
            },
            "statuses": statuses,
        }

    functions = {
        "P1": p1,
        "P2": p2,
        "P3": p3,
        "P4": p4,
        "P5": p5,
        "P6": p6,
    }
    gates = {}
    details = {}
    for name, function in functions.items():
        gates[name], details[name] = protected(function)
    passed = all(gates.values())
    failed = [name for name in REJECTION_PRIORITY if not gates[name]]
    return {
        "verdict": (
            "ACCEPTED_BY_SYNTHETIC_BATTERY"
            if passed
            else "REJECTED_BY_SYNTHETIC_BATTERY"
        ),
        "gates": gates,
        "details": details,
        "failed_arms": failed,
        "primary_rejecting_arm": failed[0] if failed else None,
    }


def literal_green_fixture() -> dict[str, object]:
    return {
        "schema": 1,
        "candidate": {"name": "literal-green"},
        "arms": {
            "flat_roi": {
                "detail": point(1.0),
                "flat": {
                    "status": "REFUSED",
                    "code": "NO_DETAIL",
                    "reason": "literal featureless truth",
                },
            },
            "planted_improvement": {
                "base": point(1.0),
                "improved": point(1.5),
            },
            "planted_degradation": {
                "base": point(1.0),
                "degraded": point(0.5),
            },
            "blur_monotonicity": [
                {
                    "added_sigma_px": sigma,
                    "measurement": point(score),
                }
                for sigma, score in zip(
                    BLUR_SIGMAS, (1.0, 0.8, 0.6, 0.4)
                )
            ],
            "sharpening_discrimination": {
                "base": point(1.0),
                "usm": point(1.0),
                "improved": point(1.5),
            },
            "fail_closed": {
                "nonfinite": {
                    "status": "REFUSED",
                    "code": "NONFINITE_INPUT",
                },
                "wrong_shape": {
                    "status": "ERROR",
                    "code": "INVALID_SHAPE",
                },
            },
        },
    }


def commission_checker() -> dict[str, object]:
    fixture = literal_green_fixture()
    baseline = adjudicate(fixture)
    mutations = []

    changed = copy.deepcopy(fixture)
    changed["arms"]["flat_roi"]["flat"] = point(1.0)
    mutations.append(("flat_equal", "P1", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["planted_improvement"]["improved"] = point(1.0)
    mutations.append(("improvement_blind", "P2", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["planted_degradation"]["degraded"] = point(1.0)
    mutations.append(("degradation_blind", "P3", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["blur_monotonicity"][2]["measurement"] = point(0.8)
    mutations.append(("blur_equal_rung", "P4", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["sharpening_discrimination"]["usm"] = point(1.1)
    mutations.append(("usm_rewarded", "P5", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["fail_closed"]["nonfinite"] = point(0.0)
    mutations.append(("malformed_numeric", "P6", changed))

    changed = copy.deepcopy(fixture)
    changed["arms"]["flat_roi"]["flat"] = {
        "status": "REFUSED",
        "code": "UNSPECIFIED",
    }
    mutations.append(("generic_flat_refusal", "P1", changed))

    changed = copy.deepcopy(fixture)
    del changed["arms"]["planted_improvement"]
    mutations.append(("missing_arm", "P2", changed))

    tests = {}
    for name, gate, mutated in mutations:
        verdict = adjudicate(mutated)
        tests[name] = {
            "target_gate": gate,
            "caught": not verdict["gates"][gate],
        }
    return {
        "literal_green_passes": all(baseline["gates"].values()),
        "sabotages": tests,
        "caught": sum(item["caught"] for item in tests.values()),
        "total": len(tests),
        "commissioned": (
            all(baseline["gates"].values())
            and all(item["caught"] for item in tests.values())
        ),
    }


def run_measurement(candidate: str) -> dict[str, object]:
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        env[key] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            str(HERE / "measure.py"),
            candidate,
        ],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if process.returncode != 0:
        return {
            "schema": 1,
            "candidate": {"name": candidate},
            "arms": {},
            "measurement_error": {
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
            },
        }
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        return {
            "schema": 1,
            "candidate": {"name": candidate},
            "arms": {},
            "measurement_error": {
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "parse_error": str(error),
            },
        }


def exact(value: object, expected: float) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and float(value) == expected
    )


def commission_battery() -> dict[str, object]:
    checker = commission_checker()
    measurements = {
        name: run_measurement(name)
        for name in ("oracle", "d8", "band-power", "m2")
    }
    verdicts = {
        name: adjudicate(measurement)
        for name, measurement in measurements.items()
    }

    d8_provenance = measurements["d8"].get("provenance", {})
    band_provenance = measurements["band-power"].get("provenance", {})
    m2_provenance = measurements["m2"].get("provenance", {})
    oracle_measurement = measurements["oracle"]
    oracle_diagnostics = oracle_measurement.get("diagnostics", {})
    oracle_construction = oracle_diagnostics.get("construction", {})
    oracle_checks = oracle_construction.get("checks", {})
    band_snapshot = measurements["band-power"].get(
        "diagnostics", {}
    ).get("historical_flat_snapshot", {})
    m2_replay = measurements["m2"].get(
        "diagnostics", {}
    ).get("m159_specificity_replay", {})
    reconstructed_ratio = m2_replay.get("blurred_over_unblurred")
    expected_oracle_checks = {
        "all_valid_observations_finite_256_square",
        "optical_renders_byte_distinct",
        "downstream_repeat_difference_held_fixed",
        "gaussian_transfer_strictly_ordered",
        "blur_sigma_vector_exact",
        "usm_pixels_differ_from_base",
        "nonfinite_fixture_contains_nonfinite",
        "wrong_shape_fixture_is_one_dimensional",
    }
    oracle_sigmas = oracle_construction.get("optical_sigmas_px")
    oracle_frequencies = oracle_construction.get(
        "positive_frequencies_cyc_per_output_px"
    )
    expected_oracle_sigmas = {
        "improved": 0.55,
        "base": 1.0,
        "degraded": 1.65,
    }
    expected_oracle_frequencies = [0.05, 0.1, 0.2, 0.3, 0.4]
    expected_gaussian_transfer = {
        name: [
            math.exp(-2.0 * math.pi**2 * sigma**2 * frequency**2)
            for frequency in expected_oracle_frequencies
        ]
        for name, sigma in expected_oracle_sigmas.items()
    }
    repeat_differences = oracle_construction.get(
        "repeat_difference_max_abs", {}
    )
    optical_hashes = oracle_construction.get("optical_image_sha256", {})

    checks = {
        "checker_commissioned": checker["commissioned"],
        "oracle_passes_all_arms": (
            verdicts["oracle"]["verdict"]
            == "ACCEPTED_BY_SYNTHETIC_BATTERY"
        ),
        "oracle_fixture_source_pinned": (
            oracle_construction.get("fixture_source_sha256")
            == FIXTURE_SHA256
        ),
        "oracle_construction_verified": (
            oracle_measurement.get("candidate", {}).get("kind")
            == "INELIGIBLE_CONSTRUCTION_TRUTH"
            and oracle_diagnostics.get("eligible_as_candidate") is False
            and oracle_sigmas == expected_oracle_sigmas
            and oracle_frequencies == expected_oracle_frequencies
            and oracle_construction.get("gaussian_transfer")
            == expected_gaussian_transfer
            and set(oracle_checks) == expected_oracle_checks
            and all(oracle_checks.values())
            and oracle_construction.get("all_checks") is True
            and set(repeat_differences)
            == {"base", "improved", "degraded"}
            and all(
                float(value) <= 1e-15
                for value in repeat_differences.values()
            )
            and set(optical_hashes) == {"base", "improved", "degraded"}
            and len(set(optical_hashes.values())) == 3
            and all(
                isinstance(value, str) and len(value) == 64
                for value in optical_hashes.values()
            )
        ),
        "d8_source_pinned": d8_provenance.get("sha256") == D8_SHA256,
        "d8_rejected": (
            verdicts["d8"]["verdict"]
            == "REJECTED_BY_SYNTHETIC_BATTERY"
        ),
        "d8_rejected_by_flat_null": not verdicts["d8"]["gates"]["P1"],
        "band_sources_pinned": (
            band_provenance.get("underlying_source_sha256") == BAND_SHA256
            and band_provenance.get("flat_evidence_sha256")
            == BAND_EVIDENCE_SHA256
            and band_provenance.get("report_sha256") == BAND_REPORT_SHA256
        ),
        "band_snapshot_exact": (
            exact(band_snapshot.get("detail_gap_dex"), BAND_DETAIL_GAP)
            and exact(band_snapshot.get("flat_gap_dex"), BAND_FLAT_GAP)
            and exact(
                band_snapshot.get("flat_over_detail"),
                BAND_FLAT_DETAIL_RATIO,
            )
            and exact(
                band_snapshot.get("recorded_flat_over_detail"),
                BAND_FLAT_DETAIL_RATIO,
            )
            and exact(
                band_snapshot.get("flat_structure_share"),
                BAND_STRUCTURE_SHARE,
            )
        ),
        "band_rejected": (
            verdicts["band-power"]["verdict"]
            == "REJECTED_BY_SYNTHETIC_BATTERY"
        ),
        "band_rejected_by_flat_null": not verdicts["band-power"]["gates"]["P1"],
        "m2_sources_pinned": (
            m2_provenance.get("source_sha256") == M2_SHA256
            and m2_provenance.get("frozen_result_sha256")
            == M2_RESULT_SHA256
        ),
        "m2_blur_ratio_reproduced": (
            isinstance(reconstructed_ratio, (int, float))
            and abs(float(reconstructed_ratio) - M2_FROZEN_BLUR_RATIO)
            <= 1e-9
        ),
        "m2_rejected": (
            verdicts["m2"]["verdict"]
            == "REJECTED_BY_SYNTHETIC_BATTERY"
        ),
        "m2_rejected_by_signed_blur": not verdicts["m2"]["gates"]["P4"],
    }
    commissioned = all(checks.values())
    return {
        "schema": 1,
        "status": "COMMISSIONED" if commissioned else "NOT_COMMISSIONED",
        "preregistration_commits": [
            "8a305128",
            "ca79eac7",
            "5fe75c14",
            "a183fd47",
        ],
        "checker": checker,
        "commissioning_checks": checks,
        "measurements": measurements,
        "verdicts": verdicts,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checker-only", action="store_true")
    parser.add_argument("--input", type=Path)
    args = parser.parse_args()

    if args.checker_only:
        result = commission_checker()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["commissioned"] else 1

    if args.input is not None:
        if not RESULT_PATH.exists():
            raise SystemExit(
                "battery has no results.json; commission it before judging"
            )
        state = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
        if state.get("status") != "COMMISSIONED":
            raise SystemExit("battery is not commissioned")
        candidate = json.loads(args.input.read_text(encoding="utf-8"))
        verdict = adjudicate(candidate)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return (
            0
            if verdict["verdict"] == "ACCEPTED_BY_SYNTHETIC_BATTERY"
            else 1
        )

    result = commission_battery()
    RESULT_PATH.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "status": result["status"],
        "commissioning_checks": result["commissioning_checks"],
        "verdicts": {
            name: {
                "verdict": verdict["verdict"],
                "failed_arms": verdict["failed_arms"],
                "primary_rejecting_arm": verdict[
                    "primary_rejecting_arm"
                ],
            }
            for name, verdict in result["verdicts"].items()
        },
        "m2_blurred_over_unblurred": result["measurements"]["m2"]
        .get("diagnostics", {})
        .get("m159_specificity_replay", {})
        .get("blurred_over_unblurred"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["status"] == "COMMISSIONED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
