#!/usr/bin/env python3
"""Fail-closed verification for M166 capture reconciliation."""

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

    first_line = report_text.splitlines()[0] if report_text else ""
    chronology = data["chronology"]
    old = data["m164_m1_roles"]
    current = data["current_m1_roles"]
    score = data["score"]
    rehearsal = data["rehearsal"]
    budget = data["budget"]
    stages = data["stages"]
    policy = data["policy"]

    check(
        "required lead",
        first_line
        == "RECONCILED: rehearsal 1,092, scored 1,215, total 2,307",
        first_line,
    )
    check(
        "M164 chronology precedes M166",
        chronology["m164_is_ancestor_of_m166"] is True,
        chronology,
    )
    check(
        "M164 named M1 roles sum to 704",
        sum(value for key, value in old.items() if key != "total")
        == old["total"]
        == 704,
        old,
    )
    check(
        "current M1 named roles sum to 900",
        sum(value for key, value in current.items() if key != "total")
        == current["total"]
        == 900,
        current,
    )
    check(
        "M164 reference is replaced not retained",
        (
            old["total"]
            - old["old_three_strip_reference"]
            + current["four_strip_reference"]
            == 736
        ),
        {
            "old_total": old["total"],
            "old_reference": old["old_three_strip_reference"],
            "new_reference": current["four_strip_reference"],
        },
    )
    check(
        "current M1 containment reaches 900",
        (
            736
            + current["candidate_excluded_dom_sw4"]
            + current["candidate_excluded_dom_sw10"]
            == current["total"]
        ),
        current,
    )
    check(
        "combined score re-derives to 1215",
        (
            score["base_combined"]
            - score["old_reference_removed"]
            + score["four_strip_reference_added"]
            + score["candidate_excluded_dominance_witness_added"]
            + score["held_out_v_calibration_added"]
            == score["current_combined"]
            == 1215
        ),
        score,
    )
    check(
        "current M1 plus M5/M9 reaches 1215",
        (
            score["current_m1_only"]
            + score["combined_m5_m9_roles"]
            == score["current_combined"]
        ),
        score,
    )
    check(
        "rehearsal predecessor changes by 196",
        (
            rehearsal["m164_predecessor"]
            - rehearsal["old_reference_removed"]
            + rehearsal["four_strip_reference_added"]
            + rehearsal["candidate_excluded_dominance_witness_added"]
            == rehearsal["current"]
            == 1092
            and rehearsal["delta"] == 196
        ),
        rehearsal,
    )
    check(
        "rehearsal categories sum to 1092",
        (
            rehearsal["dominance_kernel"]
            + rehearsal["exact_candidate_execution"]
            + rehearsal["physical_controls"]
            == rehearsal["current"]
        ),
        rehearsal,
    )
    check(
        "two sitting budget is 2307",
        (
            budget["rehearsal"] + budget["scored"]
            == budget["two_sittings"]
            == 2307
        ),
        budget,
    )
    check(
        "preflight-inclusive budget is 2309",
        (
            budget["preflight"] + budget["two_sittings"]
            == budget["including_preflight"]
            == 2309
        ),
        budget,
    )
    check(
        "conditional M1-only branch is named and consistent",
        (
            budget["rehearsal"] + score["current_m1_only"]
            == budget["conditional_m1_only_two_sittings"]
            == 1992
            and budget["preflight"]
            + budget["conditional_m1_only_two_sittings"]
            == budget["conditional_m1_only_including_preflight"]
            == 1994
        ),
        budget,
    )
    check(
        "rehearsal stage increments sum to 1092",
        sum(stage["new_frames"] for stage in stages[2:-1]) == 1092,
        stages[2:-1],
    )
    check(
        "stage cumulative sequence closes at 2309",
        [stage["cumulative_with_preflight"] for stage in stages]
        == [
            0,
            2,
            130,
            162,
            194,
            226,
            258,
            322,
            450,
            560,
            614,
            838,
            934,
            1030,
            1094,
            2309,
        ],
        [stage["cumulative_with_preflight"] for stage in stages],
    )
    check(
        "interim PASS is prohibited",
        policy["interim_pass_allowed"] is False
        and policy["rehearsal_acceptance_looks"] == 1,
        policy,
    )
    check(
        "M164 certificate question preserved",
        policy[
            "dominance_interim_margin_stop_requires_m164_certificate"
        ]
        is True,
        policy,
    )
    check(
        "report states role not literal containment",
        (
            "M164's `704` is not a literal subset of M166's `1,215`"
            in report_text
        ),
        "literal-subset warning",
    )
    check(
        "M166 additions table is evidence-labelled",
        (
            "### 1.2 What M166 adds beyond the superseded M1-only package\n\n"
            "**INFERRED BY READING.** The current complete-input and "
            "combined-score\ncontracts add these named roles beyond the "
            "superseded M1-only package:"
            in report_text
        ),
        "M166 additions table label",
    )
    check(
        "report distinguishes both 164-frame roles",
        (
            "candidate-**excluded dominance witness**:" in report_text
            and "candidate **input**:" in report_text
        ),
        "two named 164-frame roles",
    )
    check(
        "report identifies the four V groups",
        (
            "`TR-FLAT-V`, `TR-DARK-V`, `TC0-FLAT-V`, and `TC0-DARK-V`"
            in report_text
        ),
        "four held-out V groups",
    )
    check(
        "owner replacement is present",
        (
            "## 5. Paste-ready replacement for the owner document"
            in report_text
            and "> **The capture budget is now reconciled.**"
            in report_text
        ),
        "owner replacement",
    )
    check(
        "owner text preserves two-frame off-ramp",
        (
            "> **The two-frame off-ramp remains the most valuable one.**"
            in report_text
        ),
        "two-frame off-ramp",
    )
    check(
        "owner text preserves fail-only property",
        (
            "> disk. Every interim look is **fail-only**: it may stop and "
            "refuse, but it may\n> never produce an early `PASS`."
            in report_text
        ),
        "fail-only owner wording",
    )
    check(
        "no wall-clock promise",
        all(
            token not in report_text
            for token in [
                "five minutes",
                "45 minutes",
                "60 minutes",
                "25.40 s",
            ]
        ),
        "wall-clock tokens absent",
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
        "M166-capture-reconciliation.md"
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
