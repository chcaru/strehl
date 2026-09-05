#!/usr/bin/env python3
"""Commission every M166 reconciliation check with an exact-anchor defect."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

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
        "required lead",
        "report",
        "RECONCILED: rehearsal 1,092, scored 1,215, total 2,307",
        "RECONCILED: rehearsal 1,091, scored 1,215, total 2,306",
    ),
    Mutation(
        "M164 chronology precedes M166",
        "analysis",
        '"m164_is_ancestor_of_m166": true',
        '"m164_is_ancestor_of_m166": false',
    ),
    Mutation(
        "M164 named M1 roles sum to 704",
        "analysis",
        '"old_three_strip_reference": 96',
        '"old_three_strip_reference": 95',
    ),
    Mutation(
        "current M1 named roles sum to 900",
        "analysis",
        '"candidate_excluded_dom_sw10": 54',
        '"candidate_excluded_dom_sw10": 53',
    ),
    Mutation(
        "M164 reference is replaced not retained",
        "analysis",
        '"four_strip_reference": 128',
        '"four_strip_reference": 127',
    ),
    Mutation(
        "current M1 containment reaches 900",
        "analysis",
        '"candidate_excluded_dom_sw4": 110',
        '"candidate_excluded_dom_sw4": 109',
    ),
    Mutation(
        "combined score re-derives to 1215",
        "analysis",
        (
            '"base_combined": 891,\n'
            '    "old_reference_removed": 96,\n'
            '    "four_strip_reference_added": 128'
        ),
        (
            '"base_combined": 891,\n'
            '    "old_reference_removed": 95,\n'
            '    "four_strip_reference_added": 128'
        ),
    ),
    Mutation(
        "current M1 plus M5/M9 reaches 1215",
        "analysis",
        '"combined_m5_m9_roles": 315',
        '"combined_m5_m9_roles": 314',
    ),
    Mutation(
        "rehearsal predecessor changes by 196",
        "analysis",
        '"m164_predecessor": 896',
        '"m164_predecessor": 895',
    ),
    Mutation(
        "rehearsal categories sum to 1092",
        "analysis",
        '"dominance_kernel": 676',
        '"dominance_kernel": 675',
    ),
    Mutation(
        "two sitting budget is 2307",
        "analysis",
        '"two_sittings": 2307',
        '"two_sittings": 2306',
    ),
    Mutation(
        "preflight-inclusive budget is 2309",
        "analysis",
        '"including_preflight": 2309',
        '"including_preflight": 2308',
    ),
    Mutation(
        "conditional M1-only branch is named and consistent",
        "analysis",
        '"conditional_m1_only_two_sittings": 1992',
        '"conditional_m1_only_two_sittings": 1991',
    ),
    Mutation(
        "rehearsal stage increments sum to 1092",
        "analysis",
        '"name": "6b blur physical control",\n      "new_frames": 96',
        '"name": "6b blur physical control",\n      "new_frames": 95',
    ),
    Mutation(
        "stage cumulative sequence closes at 2309",
        "analysis",
        '"cumulative_with_preflight": 1030',
        '"cumulative_with_preflight": 1029',
    ),
    Mutation(
        "interim PASS is prohibited",
        "analysis",
        '"interim_pass_allowed": false',
        '"interim_pass_allowed": true',
    ),
    Mutation(
        "M164 certificate question preserved",
        "analysis",
        '"dominance_interim_margin_stop_requires_m164_certificate": true',
        '"dominance_interim_margin_stop_requires_m164_certificate": false',
    ),
    Mutation(
        "report states role not literal containment",
        "report",
        "### 1.1 M164's `704` is not a literal subset of M166's `1,215`",
        "### 1.1 M164's `704` is a literal subset of M166's `1,215`",
    ),
    Mutation(
        "M166 additions table is evidence-labelled",
        "report",
        (
            "**INFERRED BY READING.** The current complete-input and "
            "combined-score\ncontracts add these named roles beyond the "
            "superseded M1-only package:"
        ),
        (
            "The current complete-input and combined-score contracts add "
            "these named roles beyond the superseded M1-only package:"
        ),
    ),
    Mutation(
        "report distinguishes both 164-frame roles",
        "report",
        "- candidate-**excluded dominance witness**:",
        "- candidate dominance witness:",
    ),
    Mutation(
        "report identifies the four V groups",
        "report",
        "`TR-FLAT-V`, `TR-DARK-V`, `TC0-FLAT-V`, and `TC0-DARK-V`",
        "`TR-FLAT-V` and `TC0-FLAT-V`",
    ),
    Mutation(
        "owner replacement is present",
        "report",
        "> **The capture budget is now reconciled.**",
        "> **The capture budget remains unresolved.**",
    ),
    Mutation(
        "owner text preserves two-frame off-ramp",
        "report",
        "> **The two-frame off-ramp remains the most valuable one.**",
        "> **The two-frame off-ramp is removed.**",
    ),
    Mutation(
        "owner text preserves fail-only property",
        "report",
        (
            "> disk. Every interim look is **fail-only**: it may stop and "
            "refuse, but it may\n> never produce an early `PASS`."
        ),
        (
            "> disk. Every interim look may stop, refuse, or produce an "
            "early\n> `PASS`."
        ),
    ),
    Mutation(
        "no wall-clock promise",
        "report",
        "The current M164 record is `BLOCKED`.",
        "The current M164 record is `BLOCKED`; allow 45 minutes.",
    ),
]


def mutate_once(text: str, anchor: str, replacement: str) -> str:
    count = text.count(anchor)
    if count != 1:
        raise AnchorError(
            f"anchor matched {count} times, required exactly 1: {anchor!r}"
        )
    return text.replace(anchor, replacement, 1)


def check_map(data: dict[str, object], report: str) -> dict[str, bool]:
    return {
        item["name"]: bool(item["passed"])
        for item in verify.run_checks(data, report)
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    analysis_text = (root / "analysis.json").read_text(encoding="utf-8")
    report_path = root.parents[1] / "docs" / "research" / (
        "M166-capture-reconciliation.md"
    )
    report_text = report_path.read_text(encoding="utf-8")
    output_path = root / "commission.json"

    baseline = check_map(json.loads(analysis_text), report_text)
    expected = {mutation.check for mutation in MUTATIONS}
    if set(baseline) != expected:
        missing_mutations = sorted(set(baseline) - expected)
        unknown_mutations = sorted(expected - set(baseline))
        raise RuntimeError(
            "mutation coverage mismatch: "
            f"unplanted={missing_mutations}, unknown={unknown_mutations}"
        )
    if not all(baseline.values()):
        failed = sorted(name for name, passed in baseline.items() if not passed)
        raise RuntimeError(f"baseline verifier is not green: {failed}")

    results: list[dict[str, object]] = []
    for mutation in MUTATIONS:
        analysis_mutant = analysis_text
        report_mutant = report_text
        if mutation.target == "analysis":
            analysis_mutant = mutate_once(
                analysis_text, mutation.anchor, mutation.replacement
            )
        elif mutation.target == "report":
            report_mutant = mutate_once(
                report_text, mutation.anchor, mutation.replacement
            )
        else:
            raise RuntimeError(f"unknown target: {mutation.target}")

        observed = check_map(json.loads(analysis_mutant), report_mutant)
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
    duplicate_anchor_guard_fired = False
    try:
        mutate_once(
            report_text,
            "THIS M166 RECONCILIATION ANCHOR MUST NOT EXIST",
            "replacement",
        )
    except AnchorError:
        missing_anchor_guard_fired = True
    try:
        mutate_once(report_text, "**INFERRED BY READING.**", "replacement")
    except AnchorError:
        duplicate_anchor_guard_fired = True

    if not missing_anchor_guard_fired:
        raise RuntimeError("missing-anchor guard did not hard-error")
    if not duplicate_anchor_guard_fired:
        raise RuntimeError("duplicate-anchor guard did not hard-error")

    output = {
        "status": "PASS",
        "caught": sum(1 for item in results if item["caught"]),
        "total": len(results),
        "missing_anchor_guard_fired": missing_anchor_guard_fired,
        "duplicate_anchor_guard_fired": duplicate_anchor_guard_fired,
        "mutations": results,
    }
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        "COMMISSIONED: "
        f"{output['caught']}/{output['total']} planted defects caught; "
        "missing- and duplicate-anchor guards fired"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
