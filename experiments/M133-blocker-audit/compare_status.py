#!/usr/bin/env python3
"""Compare STATUS §2.9.26 with the persisted independent Phase 1 derivation."""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path


BLOCKERS = ("a", "b", "c", "d")
AXIS_PATTERN = re.compile(r"\bM(?:1[0-2]|[1-9])\b")
CODE_PATTERN = re.compile(r"\(([a-e])\)")
COUNT_PATTERN = re.compile(r"\b(\d+)(?:\s+of\s+12)?\b")
STATUS_HEADING = re.compile(
    r"^###\s+2\.9\.26\s+The blockers are conjunctive, which is why nothing has moved"
)
NEXT_STATUS_HEADING = re.compile(r"^###\s+2\.9\.\d+\b")


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def find_section(lines: list[str]) -> tuple[int, int]:
    try:
        start = next(index for index, line in enumerate(lines) if STATUS_HEADING.match(line))
    except StopIteration as error:
        raise RuntimeError("Could not find STATUS §2.9.26") from error
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if NEXT_STATUS_HEADING.match(lines[index])
        ),
        len(lines),
    )
    return start, end


def find_table(
    lines: list[str], start: int, end: int, header: str
) -> list[tuple[int, list[str], str]]:
    try:
        header_index = next(
            index for index in range(start, end) if lines[index].strip() == header
        )
    except StopIteration as error:
        raise RuntimeError(f"Could not find table header: {header}") from error

    rows: list[tuple[int, list[str], str]] = []
    for index in range(header_index + 2, end):
        line = lines[index]
        if not line.startswith("|"):
            break
        rows.append((index + 1, table_cells(line), line))
    return rows


def subsets_claimed_by_label(label: str) -> list[frozenset[str]]:
    plain = re.sub(r"[*`]", "", label).lower()
    letters = tuple(re.findall(r"\b[abcd]\b", plain))
    if plain.startswith("nothing"):
        return [frozenset()]
    if "any one" in plain:
        return [frozenset((letter,)) for letter in letters]
    if "any two" in plain:
        excluded = frozenset(letters[-2:]) if "except" in plain else frozenset()
        return [
            frozenset(pair)
            for pair in itertools.combinations(BLOCKERS, 2)
            if frozenset(pair) != excluded
        ]
    return [frozenset(letters)]


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    experiment_dir = Path(__file__).resolve().parent
    repo_root = experiment_dir.parents[1]
    phase1_path = experiment_dir / "parsed_rows.json"
    status_path = repo_root / "docs" / "STATUS.md"

    phase1 = json.loads(phase1_path.read_text(encoding="utf-8"))
    combination_lookup = {
        frozenset(item["cleared"]): item for item in phase1["combinations"]
    }
    baseline_axes = set(combination_lookup[frozenset()]["axes"])

    status_lines = status_path.read_text(encoding="utf-8").splitlines()
    section_start, section_end = find_section(status_lines)
    code_rows = find_table(
        status_lines, section_start, section_end, "| code | blocks | axes |"
    )
    combination_rows = find_table(
        status_lines, section_start, section_end, "| cleared | axes measurable |"
    )

    code_comparisons: list[dict[str, object]] = []
    for line_number, cells, raw_line in code_rows:
        if len(cells) != 3:
            raise RuntimeError(f"Malformed per-code row at STATUS:{line_number}")
        code_match = CODE_PATTERN.search(cells[0])
        count_match = COUNT_PATTERN.search(cells[1])
        if not code_match or not count_match:
            raise RuntimeError(f"Could not parse per-code row at STATUS:{line_number}")
        code = code_match.group(1)
        claimed_count = int(count_match.group(1))
        claimed_axes = AXIS_PATTERN.findall(cells[2])
        derived_axes = phase1["per_code"][code]
        code_comparisons.append(
            {
                "line": line_number,
                "raw_line": raw_line,
                "code": code,
                "claimed_count": claimed_count,
                "derived_count": len(derived_axes),
                "claimed_axes": claimed_axes,
                "derived_axes": derived_axes,
                "matches": claimed_count == len(derived_axes)
                and claimed_axes == derived_axes,
            }
        )

    subset_comparisons: list[dict[str, object]] = []
    covered_subsets: set[frozenset[str]] = set()
    for line_number, cells, raw_line in combination_rows:
        if len(cells) != 2:
            raise RuntimeError(f"Malformed combination row at STATUS:{line_number}")
        claimed_subsets = subsets_claimed_by_label(cells[0])
        count_match = COUNT_PATTERN.search(cells[1])
        if not count_match:
            raise RuntimeError(f"Could not parse combination count at STATUS:{line_number}")
        claimed_count = int(count_match.group(1))
        named_axes = AXIS_PATTERN.findall(cells[1])
        says_adds = "adds" in re.sub(r"[*`]", "", cells[1]).lower()

        for subset in claimed_subsets:
            covered_subsets.add(subset)
            derived = combination_lookup[subset]
            derived_axes = list(derived["axes"])
            if says_adds:
                derived_named_axes = [
                    axis for axis in derived_axes if axis not in baseline_axes
                ]
            elif named_axes:
                derived_named_axes = derived_axes
            else:
                derived_named_axes = []
            subset_comparisons.append(
                {
                    "line": line_number,
                    "raw_line": raw_line,
                    "cleared": sorted(subset, key=BLOCKERS.index),
                    "claimed_count": claimed_count,
                    "derived_count": derived["count"],
                    "claimed_named_axes": named_axes,
                    "derived_named_axes": derived_named_axes,
                    "matches": claimed_count == derived["count"]
                    and (not named_axes or named_axes == derived_named_axes),
                }
            )

    all_subsets = {
        frozenset(combo)
        for size in range(len(BLOCKERS) + 1)
        for combo in itertools.combinations(BLOCKERS, size)
    }
    omitted_subsets = sorted(
        all_subsets - covered_subsets,
        key=lambda subset: (
            len(subset),
            tuple(BLOCKERS.index(code) for code in BLOCKERS if code in subset),
        ),
    )
    omitted = [
        {
            "cleared": sorted(subset, key=BLOCKERS.index),
            "count": combination_lookup[subset]["count"],
            "axes": combination_lookup[subset]["axes"],
        }
        for subset in omitted_subsets
    ]

    result = {
        "status_section_start_line": section_start + 1,
        "status_section_end_line": section_end,
        "code_comparisons": code_comparisons,
        "combination_comparisons": subset_comparisons,
        "omitted_subsets": omitted,
        "all_stated_cells_match": all(item["matches"] for item in code_comparisons)
        and all(item["matches"] for item in subset_comparisons),
    }
    output_path = experiment_dir / "status-comparison.json"
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print(f"All stated cells match: {result['all_stated_cells_match']}")
    print("Omitted subsets:")
    for item in omitted:
        label = "+".join(item["cleared"]) or "nothing"
        print(f"  {label}: {item['count']} ({' '.join(item['axes'])})")


if __name__ == "__main__":
    main()
