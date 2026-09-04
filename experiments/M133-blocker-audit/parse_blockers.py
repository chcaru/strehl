#!/usr/bin/env python3
"""Mechanically derive the §3.1 blocker combinations from the SOTA scorecard."""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from pathlib import Path


ALL_CODES = ("a", "b", "c", "d", "e")
BLOCKER_CODES = ("a", "b", "c", "d")
EXPECTED_AXES = tuple(f"M{i}" for i in range(1, 13))
SECTION_HEADING = re.compile(r"^###\s+3\.1\b")
NEXT_SECTION_HEADING = re.compile(r"^###\s+")
ROW_PATTERN = re.compile(
    r"^\|\s*(M(?:[1-9]|1[0-2]))\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$"
)
CODE_PATTERN = re.compile(r"\(([a-e])\)")
ANY_SINGLE_LETTER_CODE_PATTERN = re.compile(r"\(([A-Za-z])\)")


def display_set(codes: set[str] | frozenset[str]) -> str:
    ordered = [code for code in ALL_CODES if code in codes]
    return "{" + ",".join(ordered) + "}" if ordered else "{}"


def display_subset(codes: frozenset[str]) -> str:
    return "+".join(code for code in BLOCKER_CODES if code in codes) or "nothing"


def parse_scorecard(source: Path) -> tuple[list[str], int, int, list[dict[str, object]]]:
    lines = source.read_text(encoding="utf-8").splitlines()

    try:
        section_start = next(
            index for index, line in enumerate(lines) if SECTION_HEADING.match(line)
        )
    except StopIteration as error:
        raise RuntimeError("Could not find the §3.1 heading") from error

    section_end = next(
        (
            index
            for index in range(section_start + 1, len(lines))
            if NEXT_SECTION_HEADING.match(lines[index])
        ),
        len(lines),
    )

    rows: list[dict[str, object]] = []
    for index in range(section_start + 1, section_end):
        raw_line = lines[index]
        match = ROW_PATTERN.match(raw_line)
        if not match:
            continue

        axis, class_cell, description = match.groups()
        codes_in_order = CODE_PATTERN.findall(class_cell)
        codes = set(codes_in_order)
        all_single_letter_codes = set(ANY_SINGLE_LETTER_CODE_PATTERN.findall(class_cell))
        unknown_codes = all_single_letter_codes - set(ALL_CODES)

        if unknown_codes:
            raise RuntimeError(
                f"{axis} has unknown single-letter codes: {sorted(unknown_codes)}"
            )
        if len(codes_in_order) != len(codes):
            raise RuntimeError(f"{axis} repeats a code in its Class cell: {class_cell}")

        rows.append(
            {
                "axis": axis,
                "line": index + 1,
                "raw_line": raw_line,
                "class_cell": class_cell,
                "description": description,
                "codes": sorted(codes, key=ALL_CODES.index),
                "blockers": sorted(codes - {"e"}, key=BLOCKER_CODES.index),
            }
        )

    axes = tuple(row["axis"] for row in rows)
    if axes != EXPECTED_AXES:
        raise RuntimeError(
            "Expected exactly M1 through M12 in order; "
            f"parsed {len(rows)} rows: {', '.join(str(axis) for axis in axes)}"
        )

    return lines, section_start, section_end, rows


def derive(rows: list[dict[str, object]]) -> dict[str, object]:
    per_code: dict[str, list[str]] = {
        code: [
            str(row["axis"])
            for row in rows
            if code in set(row["codes"])  # type: ignore[arg-type]
        ]
        for code in ALL_CODES
    }

    combinations: list[dict[str, object]] = []
    for size in range(len(BLOCKER_CODES) + 1):
        for combination in itertools.combinations(BLOCKER_CODES, size):
            cleared = frozenset(combination)
            measurable = [
                str(row["axis"])
                for row in rows
                if set(row["blockers"]).issubset(cleared)  # type: ignore[arg-type]
            ]
            combinations.append(
                {
                    "cleared": list(combination),
                    "count": len(measurable),
                    "axes": measurable,
                }
            )

    consistency = {
        "row_count": len(rows),
        "rows_with_e_and_blocker": [
            str(row["axis"])
            for row in rows
            if "e" in set(row["codes"]) and row["blockers"]  # type: ignore[arg-type]
        ],
        "rows_with_no_codes": [
            str(row["axis"]) for row in rows if not row["codes"]
        ],
    }

    return {
        "per_code": per_code,
        "combinations": combinations,
        "consistency": consistency,
    }


def render_markdown(
    source: Path,
    lines: list[str],
    section_start: int,
    rows: list[dict[str, object]],
    derived: dict[str, object],
) -> str:
    source_label = source.as_posix()
    try:
        source_label = source.relative_to(Path(__file__).resolve().parents[2]).as_posix()
    except ValueError:
        pass

    output: list[str] = [
        "# M133 Phase 1 independent blocker derivation",
        "",
        "Generated mechanically by `parse_blockers.py` before reading or comparing",
        "`docs/STATUS.md` §2.9.26.",
        "",
        "## Rule",
        "",
        "The cleared set ranges over `{a,b,c,d}`. An axis is measurable iff its",
        "blocking-code set (its extracted codes minus `e`) is a subset of the",
        "cleared set. Code `e` is retained in the exact extracted code set and in",
        "the per-code census, but is excluded from the blocking-code set because",
        "the source defines it as “scientifically measurable now” and warns that",
        "it does not imply a run has occurred.",
        "",
        "Source definition:",
        "",
        "```text",
    ]

    table_header_index = next(
        index
        for index in range(section_start + 1, len(lines))
        if lines[index].startswith("| Axis | Class |")
    )
    for index in range(section_start + 2, table_header_index):
        if lines[index]:
            output.append(f"{source_label}:{index + 1}: {lines[index]}")
    output.extend(["```", "", "## Extracted rows", "", "| Axis | Source | Exact codes | Blocking codes | Blocker count |", "|---|---:|---|---|---:|"])

    for row in rows:
        codes = set(row["codes"])  # type: ignore[arg-type]
        blockers = set(row["blockers"])  # type: ignore[arg-type]
        output.append(
            f"| {row['axis']} | `{source_label}:{row['line']}` | "
            f"`{display_set(codes)}` | `{display_set(blockers)}` | "
            f"{len(blockers)} |"
        )

    output.extend(["", "## Verbatim row audit", ""])
    for row in rows:
        codes = set(row["codes"])  # type: ignore[arg-type]
        output.extend(
            [
                f"**{row['axis']} → `{display_set(codes)}` "
                f"({source_label}:{row['line']})**",
                "",
                "```text",
                str(row["raw_line"]),
                "```",
                "",
            ]
        )

    output.extend(
        [
            "## Per-code census",
            "",
            "| Code | Count | Axes |",
            "|---|---:|---|",
        ]
    )
    per_code = derived["per_code"]
    assert isinstance(per_code, dict)
    for code in ALL_CODES:
        axes = per_code[code]
        assert isinstance(axes, list)
        output.append(f"| `{code}` | {len(axes)} | {' '.join(axes)} |")

    output.extend(
        [
            "",
            "## Full brute-force table",
            "",
            "| Cleared | Count | Measurable axes |",
            "|---|---:|---|",
        ]
    )
    combinations = derived["combinations"]
    assert isinstance(combinations, list)
    for combination in combinations:
        assert isinstance(combination, dict)
        cleared = frozenset(combination["cleared"])
        axes = combination["axes"]
        assert isinstance(axes, list)
        output.append(
            f"| `{display_subset(cleared)}` | {combination['count']} | "
            f"{' '.join(axes)} |"
        )

    consistency = derived["consistency"]
    assert isinstance(consistency, dict)
    output.extend(
        [
            "",
            "## Internal consistency",
            "",
            f"- Parsed row count: {consistency['row_count']}.",
            "- Rows carrying both `e` and a blocker: "
            + (
                ", ".join(consistency["rows_with_e_and_blocker"])
                if consistency["rows_with_e_and_blocker"]
                else "none"
            )
            + ".",
            "- Rows carrying no codes: "
            + (
                ", ".join(consistency["rows_with_no_codes"])
                if consistency["rows_with_no_codes"]
                else "none"
            )
            + ".",
            "",
        ]
    )
    return "\n".join(output)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=repo_root / "docs" / "proposals" / "2026-09-sota-scorecard.md",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()

    source = args.source.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    lines, section_start, section_end, rows = parse_scorecard(source)
    derived = derive(rows)
    markdown = render_markdown(source, lines, section_start, rows, derived)

    payload = {
        "source": str(source),
        "section_start_line": section_start + 1,
        "section_end_line": section_end,
        "rows": rows,
        **derived,
    }
    (out_dir / "parsed_rows.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "phase1-independent-derivation.md").write_text(
        markdown.rstrip() + "\n", encoding="utf-8"
    )
    print(markdown.rstrip())


if __name__ == "__main__":
    main()
