#!/usr/bin/env python3
"""Prove every M166 cost-report check fires under a unique-anchor defect."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import verify


class AnchorError(RuntimeError):
    pass


@dataclass(frozen=True)
class Mutation:
    check: str
    target: str
    anchor: str
    replacement: str


MUTATIONS = [
    Mutation(
        "direct predicate total",
        "analysis",
        '"direct_predicate_frames": 676',
        '"direct_predicate_frames": 675',
    ),
    Mutation(
        "score execution total",
        "analysis",
        '"score_execution_frames": 224',
        '"score_execution_frames": 223',
    ),
    Mutation(
        "physical controls total",
        "analysis",
        '"physical_control_frames": 192',
        '"physical_control_frames": 191',
    ),
    Mutation(
        "full rehearsal total",
        "analysis",
        '"full_rehearsal_frames": 1092',
        '"full_rehearsal_frames": 1091',
    ),
    Mutation(
        "first release total",
        "analysis",
        '"first_stage_frames": 128',
        '"first_stage_frames": 127',
    ),
    Mutation(
        "stages close at full total",
        "analysis",
        '"final_cumulative": 1092',
        '"final_cumulative": 1091',
    ),
    Mutation(
        "score gap remains 123",
        "analysis",
        '"rehearsal_gap": 123',
        '"rehearsal_gap": 122',
    ),
    Mutation(
        "required lead",
        "report",
        "STAGED RELEASE: 128 frames",
        "STAGED RELEASE: 127 frames",
    ),
    Mutation(
        "no successful-path reduction",
        "report",
        "The successful path remains exactly `1,092` registered frames.",
        "The successful path remains exactly `1,091` registered frames.",
    ),
    Mutation(
        "optional stopping controlled",
        "report",
        (
            "No interim look may produce `PASS`; the complete frozen family "
            "is accepted or refused exactly once, after all `1,092` frames."
        ),
        (
            "An interim look may produce `PASS`; the complete frozen family "
            "need not wait for all `1,092` frames."
        ),
    ),
    Mutation(
        "development unit remains disjoint",
        "report",
        (
            "`D-REHEARSAL-01 — DEVELOPMENT; NEVER SCORE` remains the only "
            "subject class admitted to every rehearsal stage."
        ),
        (
            "The scored subject may replace the development subject in any "
            "rehearsal stage."
        ),
    ),
    Mutation(
        "owner text present",
        "report",
        (
            "### Development rehearsal — one clean pass still needs 1,092 "
            "registered frames"
        ),
        (
            "### Development rehearsal — one clean pass needs fewer "
            "registered frames"
        ),
    ),
]


def mutate_once(text: str, anchor: str, replacement: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise AnchorError(
            f"anchor matched {count} times, required exactly 1: {anchor!r}"
        )
    return text.replace(anchor, replacement, 1)


def check_map(data: dict[str, Any], report: str) -> dict[str, bool]:
    return {
        item["name"]: bool(item["passed"])
        for item in verify.run_checks(data, report)
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    analysis_text = (root / "analysis.json").read_text(encoding="utf-8")
    report_path = root.parents[1] / "docs" / "research" / (
        "M166-rehearsal-cost.md"
    )
    report_text = report_path.read_text(encoding="utf-8")
    output_path = root / "commission.json"

    baseline_data = json.loads(analysis_text)
    baseline_checks = check_map(baseline_data, report_text)
    expected = {mutation.check for mutation in MUTATIONS}
    if set(baseline_checks) != expected:
        missing = sorted(set(baseline_checks) - expected)
        extra = sorted(expected - set(baseline_checks))
        raise RuntimeError(
            f"mutation coverage mismatch: unplanted={missing}, unknown={extra}"
        )
    if not all(baseline_checks.values()):
        raise RuntimeError("baseline verifier is not green")

    results = []
    for mutation in MUTATIONS:
        mutated_analysis_text = analysis_text
        mutated_report_text = report_text
        if mutation.target == "analysis":
            mutated_analysis_text = mutate_once(
                analysis_text, mutation.anchor, mutation.replacement
            )
        elif mutation.target == "report":
            mutated_report_text = mutate_once(
                report_text, mutation.anchor, mutation.replacement
            )
        else:
            raise RuntimeError(f"unknown mutation target: {mutation.target}")

        mutated_data = json.loads(mutated_analysis_text)
        observed = check_map(mutated_data, mutated_report_text)
        caught = not observed[mutation.check]
        results.append(
            {
                "check": mutation.check,
                "target": mutation.target,
                "anchor": mutation.anchor,
                "caught": caught,
            }
        )
        if not caught:
            raise RuntimeError(
                f"planted defect did not fire check: {mutation.check}"
            )

    missing_anchor_guard_fired = False
    try:
        mutate_once(
            report_text,
            "THIS ANCHOR MUST NOT EXIST IN THE M166 COST REPORT",
            "replacement",
        )
    except AnchorError:
        missing_anchor_guard_fired = True
    if not missing_anchor_guard_fired:
        raise RuntimeError("missing-anchor guard did not hard-error")

    output = {
        "status": "PASS",
        "caught": sum(1 for item in results if item["caught"]),
        "total": len(results),
        "missing_anchor_guard_fired": missing_anchor_guard_fired,
        "mutations": deepcopy(results),
    }
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "COMMISSIONED: "
        f"{output['caught']}/{output['total']} planted defects caught; "
        "missing-anchor guard fired"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
