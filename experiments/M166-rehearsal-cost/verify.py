#!/usr/bin/env python3
"""Fail-closed checks for the M166 rehearsal-cost report."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


Check = dict[str, Any]


def run_checks(data: dict[str, Any], report_text: str) -> list[Check]:
    checks: list[Check] = []

    def check(name: str, condition: bool, detail: Any) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    categories = data["categories"]
    disjointness = data["score_disjointness"]
    rehearsal_disjointness = data["rehearsal_disjointness"]
    m151 = data["m151_rehearsal_exit_gate"]
    score = data["score"]
    staging = data["staging"]
    first_nonempty = next(
        (line for line in report_text.splitlines() if line.strip()), ""
    )

    check(
        "direct predicate total",
        categories["direct_predicate_frames"] == 676,
        categories["direct_predicate_frames"],
    )
    check(
        "score execution total",
        categories["score_execution_frames"] == 224,
        categories["score_execution_frames"],
    )
    check(
        "physical controls total",
        categories["physical_control_frames"] == 192,
        categories["physical_control_frames"],
    )
    check(
        "full rehearsal total",
        categories["full_rehearsal_frames"] == 1092,
        categories["full_rehearsal_frames"],
    )
    check(
        "first release total",
        staging["first_stage_frames"] == 128,
        staging["first_stage_frames"],
    )
    check(
        "stages close at full total",
        staging["final_cumulative"] == 1092,
        staging["final_cumulative"],
    )
    check(
        "score gap remains 123",
        score["rehearsal_gap"] == 123,
        score["rehearsal_gap"],
    )
    check(
        "reference change is net 32",
        disjointness["reference_net_increment"] == 32,
        disjointness["reference_net_increment"],
    )
    check(
        "expanded score reconstruction",
        disjointness["expanded_corrected_total"] == 1215,
        disjointness["expanded_corrected_total"],
    )
    check(
        "dominance witness is disjoint",
        disjointness["dominance_witness_vs_candidate_raw_overlap"] == 0,
        disjointness["dominance_witness_vs_candidate_raw_overlap"],
    )
    check(
        "held-out V is disjoint",
        disjointness["held_out_v_vs_ab_raw_overlap"] == 0,
        disjointness["held_out_v_vs_ab_raw_overlap"],
    )
    check(
        "rehearsal shares no score raws",
        rehearsal_disjointness["shared_raws_with_score"] == 0,
        rehearsal_disjointness["shared_raws_with_score"],
    )
    check(
        "m151 remains zero-frame",
        m151["m151_added_frames"] == 0,
        m151["m151_added_frames"],
    )
    check(
        "m151 survives staging",
        m151["survives_staged_structure"] is True,
        m151["survives_staged_structure"],
    )
    check(
        "required lead",
        first_nonempty == "STAGED RELEASE: 128 frames",
        first_nonempty,
    )
    check(
        "no successful-path reduction",
        (
            "The successful path remains exactly `1,092` registered frames."
            in report_text
        ),
        "successful path remains 1,092",
    )
    check(
        "optional stopping controlled",
        (
            "No interim look may produce `PASS`; the complete frozen family "
            "is accepted or refused exactly once, after all `1,092` frames."
            in report_text
        ),
        "one final acceptance look",
    )
    check(
        "development unit remains disjoint",
        (
            "`D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE` remains the only "
            "subject class admitted to every rehearsal stage."
            in report_text
        ),
        "development subject disjointness",
    )
    check(
        "owner text present",
        (
            "### Development rehearsal — one clean pass still needs 1,092 "
            "registered frames"
            in report_text
        ),
        "owner-facing replacement heading",
    )
    check(
        "disjointness quote present",
        (
            "The corrected `1,215`-frame plan double-counts nothing: `+32` "
            "is the net replacement of the base `96`-frame reference by "
            "`128` frames, `+164` is a new candidate-excluded `TC0-DOM-*` "
            "witness, and `+128` is new held-out V calibration; none of the "
            "new DOM or V RAWs is already inside the base `891`."
            in report_text
        ),
        "owner-verifier disjointness sentence",
    )
    return checks


def result_from_checks(checks: list[Check]) -> dict[str, Any]:
    passed = sum(1 for item in checks if item["passed"])
    return {
        "status": "PASS" if passed == len(checks) else "FAIL",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
    }


def default_paths() -> tuple[Path, Path, Path]:
    root = Path(__file__).resolve().parent
    report = root.parents[1] / "docs" / "research" / (
        "M166-rehearsal-cost.md"
    )
    return root / "analysis.json", report, root / "verification.json"


def main() -> int:
    analysis_path, report_path, output_path = default_paths()
    if len(sys.argv) == 4:
        analysis_path = Path(sys.argv[1])
        report_path = Path(sys.argv[2])
        output_path = Path(sys.argv[3])
    elif len(sys.argv) != 1:
        print("usage: verify.py [analysis.json report.md output.json]")
        return 2

    try:
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        report_text = report_path.read_text(encoding="utf-8")
        result = result_from_checks(run_checks(data, report_text))
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            f"{result['status']}: {result['passed']}/{result['total']} checks"
        )
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
