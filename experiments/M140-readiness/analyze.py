#!/usr/bin/env python3
"""Mechanically re-derive scorecard readiness under three rule-4 scenarios."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
PLAN = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
OUTPUT = Path(__file__).with_name("readiness.json")

AXES = tuple(f"M{i}" for i in range(1, 13))
BLOCKERS = ("a", "b", "c", "d")

# This is the judgement requested by M140, not text parsed from the readiness table.
# Citations point to each metric card's own definition and success bar.
A_RULINGS = {
    "M1": {
        "ruling": "intrinsic",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:491-560",
        "reason": "The axis is the missing sharpening-safe information instrument itself.",
        "s2_action": "retain",
        "s3_action": "retain",
    },
    "M2": {
        "ruling": "propagated",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:579-615",
        "reason": "Its own success bar is eta and a noise ratio; the future-M1 mode qualifier is rule-4 propagation.",
        "s2_action": "replace_with_matched_output",
        "s3_action": "remove",
    },
    "M3": {
        "ruling": "propagated",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:621-662",
        "reason": "Its own bar is halo, veil, edge width, and local coherence; replacement M1 appears only as an added blur control.",
        "s2_action": "remove",
        "s3_action": "remove",
    },
    "M4": {
        "ruling": "propagated",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:667-697",
        "reason": "Its own bar is flat patchwork and ghost rate; replacement M1 appears only in the control paragraph.",
        "s2_action": "remove",
        "s3_action": "remove",
    },
    "M5": {
        "ruling": "intrinsic",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:704-743",
        "reason": "Coverage is defined by source-band coherence and focus margin, so a detail-bearing test is part of the axis.",
        "s2_action": "retain",
        "s3_action": "retain",
    },
    "M6": {
        "ruling": "intrinsic",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:750-779",
        "reason": "Highlight-detail retention is an explicit member of the success bar.",
        "s2_action": "retain",
        "s3_action": "retain",
    },
    "M7": {
        "ruling": "not_assigned",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:782-817",
        "reason": "The source readiness row assigns no blocker (a); the bar is external-target colour fidelity.",
        "s2_action": "not_applicable",
        "s3_action": "not_applicable",
    },
    "M8": {
        "ruling": "not_assigned",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:819-888",
        "reason": "The source readiness row assigns no blocker (a); the bar is an exact source-support invariant.",
        "s2_action": "not_applicable",
        "s3_action": "not_applicable",
    },
    "M9": {
        "ruling": "intrinsic",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:890-936",
        "reason": "Empirical acuity truth is explicitly the future independently commissioned M1 condition.",
        "s2_action": "retain",
        "s3_action": "retain",
    },
    "M10": {
        "ruling": "not_assigned",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:938-979",
        "reason": "The source readiness row assigns no blocker (a); the bar uses external geometric truth.",
        "s2_action": "not_applicable",
        "s3_action": "not_applicable",
    },
    "M11": {
        "ruling": "propagated",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:981-1036",
        "reason": "Its numeric bar is elapsed time; replacement-M1 qualification enters through comparator quality qualification.",
        "s2_action": "remove",
        "s3_action": "remove",
    },
    "M12": {
        "ruling": "not_assigned",
        "citation": "docs/proposals/2026-09-sota-scorecard.md:1038-1103",
        "reason": "The source readiness row assigns no blocker (a); the bar is memory and reproducibility.",
        "s2_action": "not_applicable",
        "s3_action": "not_applicable",
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def line_number(lines: list[str], exact: str) -> int:
    matches = [index for index, line in enumerate(lines, 1) if line == exact]
    if len(matches) != 1:
        raise AssertionError(f"expected one exact line, found {len(matches)}: {exact}")
    return matches[0]


def section(lines: list[str], start_heading: str, end_heading: str) -> list[tuple[int, str]]:
    start = line_number(lines, start_heading)
    end = line_number(lines, end_heading)
    if end <= start:
        raise AssertionError(f"bad section order: {start_heading} -> {end_heading}")
    return list(enumerate(lines[start:end - 1], start + 1))


def parse_readiness(lines: list[str]) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    for number, line in section(
        lines,
        "### 3.1 Measurement readiness as of v1.7",
        "### 3.2 Closed program decision gates",
    ):
        match = re.match(r"^\| (M(?:[1-9]|1[0-2])) \| (.*?) \| (.*?) \|$", line)
        if not match:
            continue
        axis, class_cell, description = match.groups()
        codes = re.findall(r"\(([a-e])\)", class_cell)
        rows[axis] = {
            "source_line": number,
            "class_cell": class_cell,
            "description": description,
            "codes": codes,
            "blockers": [code for code in codes if code in BLOCKERS],
        }
    if tuple(rows) != AXES:
        raise AssertionError(f"readiness parse mismatch: {tuple(rows)}")
    return rows


def parse_amendment_table(lines: list[str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    in_table = False
    for number, line in section(
        lines,
        "## 12. Amendment 2 — the blockers are conjunctive, and what that does to section 9 (orchestrator, 2026-09-04)",
        "## 13. Amendment 3 — Phase 1's refutation is withdrawn, and section 9 cannot run as written (orchestrator, 2026-09-05)",
    ):
        if line == "| cleared | axes measurable |":
            in_table = True
            continue
        if not in_table:
            continue
        if line == "|---|---|":
            continue
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 2:
            raise AssertionError(f"unexpected Amendment 2 row at {number}: {line}")
        count_match = re.search(r"\*\*(\d+)", cells[1])
        if not count_match:
            raise AssertionError(f"missing count at {number}: {line}")
        rows.append(
            {
                "source_line": number,
                "cleared_cell": cells[0],
                "measurable_cell": cells[1],
                "published_count": int(count_match.group(1)),
            }
        )
    if len(rows) != 6:
        raise AssertionError(f"expected 6 Amendment 2 rows, found {len(rows)}")
    return rows


def canonical_subsets() -> list[tuple[str, ...]]:
    return [
        subset
        for count in range(len(BLOCKERS) + 1)
        for subset in itertools.combinations(BLOCKERS, count)
    ]


def table_for(blockers_by_axis: dict[str, list[str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for subset in canonical_subsets():
        cleared = set(subset)
        measurable = [
            axis for axis in AXES if set(blockers_by_axis[axis]).issubset(cleared)
        ]
        rows.append(
            {
                "cleared": list(subset),
                "cleared_label": "+".join(subset) if subset else "nothing",
                "measurable_count": len(measurable),
                "measurable_axes": measurable,
                "evidence_status": "VERIFIED",
            }
        )
    return rows


def row_by_label(table: list[dict[str, object]], label: str) -> dict[str, object]:
    return next(row for row in table if row["cleared_label"] == label)


def compare_amendment(
    published: list[dict[str, object]], s1_table: list[dict[str, object]]
) -> dict[str, object]:
    published_by_prefix = {row["cleared_cell"]: row for row in published}
    checks = [
        (
            "nothing",
            published_by_prefix["nothing -- today"]["published_count"],
            row_by_label(s1_table, "nothing")["measurable_count"],
        ),
        (
            "any_one",
            published_by_prefix["any **one** blocker"]["published_count"],
            {
                row_by_label(s1_table, label)["measurable_count"]
                for label in BLOCKERS
            },
        ),
        (
            "any_two_except_b+c",
            published_by_prefix["any **two** except `b+c`"]["published_count"],
            {
                row_by_label(s1_table, label)["measurable_count"]
                for label in ("a+b", "a+c", "a+d", "b+d", "c+d")
            },
        ),
        (
            "b+c",
            published_by_prefix["`b+c`"]["published_count"],
            row_by_label(s1_table, "b+c")["measurable_count"],
        ),
        (
            "a+b+d",
            published_by_prefix["**`a+b+d`**"]["published_count"],
            row_by_label(s1_table, "a+b+d")["measurable_count"],
        ),
        (
            "a+b+c+d",
            published_by_prefix["**`a+b+c+d`**"]["published_count"],
            row_by_label(s1_table, "a+b+c+d")["measurable_count"],
        ),
    ]
    results = []
    for name, expected, observed in checks:
        observed_values = sorted(observed) if isinstance(observed, set) else observed
        matches = (
            observed == {expected} if isinstance(observed, set) else observed == expected
        )
        results.append(
            {
                "claim": name,
                "published_count": expected,
                "computed": observed_values,
                "matches": matches,
            }
        )
    return {
        "all_published_numbers_reproduced_exactly": all(
            result["matches"] for result in results
        ),
        "checks": results,
        "evidence_status": "VERIFIED",
    }


def scenario_blockers(
    source: dict[str, dict[str, object]], scenario: str
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for axis in AXES:
        blockers = list(source[axis]["blockers"])
        if "a" in blockers:
            action = A_RULINGS[axis][f"{scenario.lower()}_action"]
            if action in {"remove", "replace_with_matched_output"}:
                blockers.remove("a")
        result[axis] = blockers
    return result


def blocker_census(blockers_by_axis: dict[str, list[str]]) -> dict[str, object]:
    return {
        blocker: {
            "count": sum(blocker in blockers for blockers in blockers_by_axis.values()),
            "axes": [
                axis for axis in AXES if blocker in blockers_by_axis[axis]
            ],
            "evidence_status": "VERIFIED",
        }
        for blocker in BLOCKERS
    }


def main() -> int:
    scorecard_lines = SCORECARD.read_text(encoding="utf-8").splitlines()
    plan_lines = PLAN.read_text(encoding="utf-8").splitlines()
    parsed = parse_readiness(scorecard_lines)
    amendment = parse_amendment_table(plan_lines)

    s1_blockers = {axis: list(parsed[axis]["blockers"]) for axis in AXES}
    s2_blockers = scenario_blockers(parsed, "s2")
    s3_blockers = scenario_blockers(parsed, "s3")
    scenario_specs = {
        "S1": {
            "name": "rule 4 in force as written",
            "blockers_by_axis": s1_blockers,
            "rule": "No blocker assignment is changed.",
        },
        "S2": {
            "name": "rule 4 narrowed to matched output",
            "blockers_by_axis": s2_blockers,
            "rule": (
                "Comparator eligibility requires the same hashed common input; "
                "native-size 16-bit linear output; frozen ICC, tone-ramp, geometry, "
                "crop, dimensions, and bit depth; and no post-processing. It does "
                "not require replacement-M1 or a 98% information score. This "
                "substitutes matched output for M2's comparator-information "
                "qualification while leaving M5, M6, and M9 intrinsic detail "
                "requirements intact."
            ),
        },
        "S3": {
            "name": "rule 4 removed",
            "blockers_by_axis": s3_blockers,
            "rule": (
                "Remove blocker (a) only from axes where it is propagated. Retain "
                "it for M1, M5, M6, and M9 because their own definitions need "
                "detail or information truth."
            ),
        },
    }

    scenarios = {}
    for key, spec in scenario_specs.items():
        table = table_for(spec["blockers_by_axis"])
        scenarios[key] = {
            "name": spec["name"],
            "rule": spec["rule"],
            "blockers_by_axis": {
                axis: {
                    "blockers": spec["blockers_by_axis"][axis],
                    "source_class_cell": parsed[axis]["class_cell"],
                    "source_line": parsed[axis]["source_line"],
                    "a_ruling": A_RULINGS[axis],
                }
                for axis in AXES
            },
            "blocker_census": blocker_census(spec["blockers_by_axis"]),
            "subset_table": table,
            "today": {
                "cleared": ["b"],
                "open": ["a", "c", "d"],
                "scoreable_count": row_by_label(table, "b")["measurable_count"],
                "scoreable_axes": row_by_label(table, "b")["measurable_axes"],
                "evidence_status": "VERIFIED",
            },
        }

    result = {
        "schema": 1,
        "artifact": "M140 scorecard readiness re-derivation",
        "generated_by": "experiments/M140-readiness/analyze.py",
        "repository_head": git_head(),
        "sources": {
            "scorecard": {
                "path": SCORECARD.relative_to(ROOT).as_posix(),
                "sha256": sha256(SCORECARD),
                "readiness_lines": [412, 437],
                "rule_4_lines": [93, 98],
            },
            "plan": {
                "path": PLAN.relative_to(ROOT).as_posix(),
                "sha256": sha256(PLAN),
                "matched_output_lines": [1975, 1978],
                "amendment_1_live_instruments_lines": [2208, 2210],
                "amendment_2_table_lines": [
                    amendment[0]["source_line"],
                    amendment[-1]["source_line"],
                ],
            },
        },
        "mechanical_parse": {
            "axes": parsed,
            "blocker_census": blocker_census(s1_blockers),
            "amendment_2_published_rows": amendment,
            "amendment_2_comparison": compare_amendment(
                amendment, table_for(s1_blockers)
            ),
            "evidence_status": "VERIFIED",
        },
        "a_rulings": A_RULINGS,
        "matched_output_operationalization": {
            "requirements": [
                "identical hashed common linear input TIFF bytes",
                "native-size 16-bit linear output",
                "same dimensions, crop, bit depth, and frozen ICC",
                "pass the frozen affine tone-ramp sentinel",
                "pass native-scale geometry and site-retention gates",
                "no output post-processing",
            ],
            "excluded_requirement": "No replacement-M1 score and no 98% information threshold.",
            "citations": [
                "docs/proposals/2026-08-sota-path.md:1975-1978",
                "docs/proposals/2026-09-sota-scorecard.md:147-169",
                "docs/proposals/2026-09-sota-scorecard.md:173-196",
                "docs/proposals/2026-09-sota-scorecard.md:223-235",
            ],
        },
        "scenarios": scenarios,
    }

    if not result["mechanical_parse"]["amendment_2_comparison"][
        "all_published_numbers_reproduced_exactly"
    ]:
        raise AssertionError("Amendment 2 published numbers were not reproduced")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT.relative_to(ROOT)),
                "amendment_2_exact": True,
                "today": {
                    key: value["today"]["scoreable_axes"]
                    for key, value in scenarios.items()
                },
                "b_plus_d_counts": {
                    key: row_by_label(value["subset_table"], "b+d")[
                        "measurable_count"
                    ]
                    for key, value in scenarios.items()
                },
                "b_plus_c_plus_d_counts": {
                    key: row_by_label(value["subset_table"], "b+c+d")[
                        "measurable_count"
                    ]
                    for key, value in scenarios.items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
