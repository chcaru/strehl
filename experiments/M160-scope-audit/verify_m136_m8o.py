#!/usr/bin/env python3
"""Verify the M136 M8-O correction by content, never by line number."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
M136_PATH = "docs/research/M136-m8o-bar.md"
M166_PATH = "docs/research/M166-bar-achievability.md"
ANALYSIS_PATH = "experiments/M136-m8o-bar/analysis.json"
BASE_REV = "7bee3738"
M136_REV = "7befe55c"
M166_REV = "02014c6e"
ANALYSIS_REV = "6712449e9defdd93e301c6ed5dcd949a3c17c4b6"
CHECKER_REV = "e5489d64"
DIAGNOSTIC_COUNT = "31" + ",148"
SUPERSEDED_LINE = (
    "> **M8-O v1.4 superseded figure:** `1.326144%` was read against the v1.4 "
    "bar, which has been shown impossible as written; see "
    "`docs/research/M136-m8o-bar.md` (commit `7befe55c`)."
)


@dataclass(frozen=True)
class Check:
    group: str
    name: str
    passed: bool
    detail: str


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def git_blob(rev: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout.decode("utf-8").replace("\r\n", "\n")


def git_subject(rev: str) -> str:
    completed = subprocess.run(
        ["git", "show", "-s", "--format=%s", rev],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout.decode("utf-8").strip()


def normalise(text: str) -> str:
    lines = [re.sub(r"^\s*>\s?", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def contains(text: str, phrase: str) -> bool:
    return normalise(phrase) in normalise(text)


def ncount(text: str, phrase: str) -> int:
    return normalise(text).count(normalise(phrase))


def top_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^## ([0-9]+)\. .+$", text))
    result = {"PREAMBLE": text[: matches[0].start()] if matches else text}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1)] = text[match.start() : end]
    return result


def subsection(text: str, heading: str, level: int = 3) -> str:
    marker = "#" * level
    match = re.search(rf"(?m)^{re.escape(marker)} {re.escape(heading)}\s*$", text)
    if not match:
        return ""
    following = re.search(rf"(?m)^#{{1,{level}}} ", text[match.end() :])
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


def metric_card(text: str, metric: str) -> str:
    match = re.search(rf"(?m)^### {re.escape(metric)}(?:\s|—|-)", text)
    if not match:
        return ""
    following = re.search(r"(?m)^#{1,3} ", text[match.end() :])
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


def success_block(card: str) -> str:
    match = re.search(r"\*\*Success(?: criterion)?\.\*\*", card)
    if not match:
        return ""
    following = re.search(r"(?m)^\*\*[A-Z][^*]+\.\*\*", card[match.end() :])
    end = match.end() + following.start() if following else len(card)
    return normalise(card[match.start() : end])


def metric_rows(section: str, metric: str) -> list[str]:
    return [
        line
        for line in section.splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]


def cells(row: str) -> list[str]:
    return [part.strip() for part in row.strip().strip("|").split("|")]


def m8_r_definition(card: str) -> str:
    start = card.find("1. **M8-R, per-frame resampler hull.**")
    end = card.find("4. **M8-O")
    if start < 0 or end < 0 or end <= start:
        return ""
    return card[start:end]


def add(
    checks: list[Check], group: str, name: str, passed: bool, detail: str
) -> None:
    checks.append(Check(group, name, passed, detail))


def run_checks(
    after: str,
    before: str,
    m136: str,
    m166: str,
    analysis: dict[str, object],
    checker_subject: str,
) -> list[Check]:
    checks: list[Check] = []
    after_sections = top_sections(after)
    before_sections = top_sections(before)
    section3 = after_sections.get("3", "")
    section6 = after_sections.get("6", "")
    m8 = metric_card(after, "M8")
    glance_rows = metric_rows(section3, "M8")
    readiness = glance_rows[1] if len(glance_rows) > 1 else ""
    glance = glance_rows[0] if glance_rows else ""
    result_rows = metric_rows(section6, "M8")
    result = result_rows[0] if result_rows else ""
    result_cells = cells(result)
    m8_value = result_cells[2] if len(result_cells) == 7 else ""
    m8_standing = result_cells[6] if len(result_cells) == 7 else ""

    # Primary evidence.
    add(checks, "source", "source.v14-impossible",
        contains(m136,
                 "Impossible for the 977,684 bilinear coordinates while output "
                 "remains the required `u16/65535` domain"),
        "M136 proves v1.4 impossible")
    add(checks, "source", "source.coord-count",
        "977,684" in m136,
        "M136 records 977,684 impossible coordinates")
    add(checks, "source", "source.diagnostic-not-score",
        contains(m136,
                 f"the {DIAGNOSTIC_COUNT} count is a diagnostic lower than the "
                 "old count, not a promoted score"),
        "M136 forbids promoting the diagnostic count")
    add(checks, "source", "source.v15-unmeasured",
        contains(m136,
                 "The formal result under the exact new M8-O definition is "
                 "nevertheless `UNMEASURED` until that checker is commissioned"),
        "M136 leaves v1.5 unmeasured")
    add(checks, "source", "source.v15-zero-achievable",
        contains(m136,
                 "Thus zero is mathematically achievable without a statistical "
                 "allowance."),
        "M136 proves the repaired zero bar achievable")
    add(checks, "source", "source.m8r-achievable",
        "| M8-R | **ACHIEVABLE** |" in m166,
        "M166 independently confirms M8-R achievability")
    add(checks, "source", "source.v14-impossible-independent",
        "| Historical M8-O v1.4 | **IMPOSSIBLE** |" in m166,
        "M166 independently confirms v1.4 impossibility")
    add(checks, "source", "source.v15-achievable-independent",
        "| Prospective M8-O v1.5 | **ACHIEVABLE** |" in m166,
        "M166 independently confirms v1.5 achievability")
    add(checks, "source", "source.checker-not-recommissioned",
        "NOT YET RECOMMISSIONED" in checker_subject,
        f"checker commit subject={checker_subject}")

    bilinear = analysis.get("bilinear_aggregate", {})
    by_channel = bilinear.get("by_channel", {}) if isinstance(bilinear, dict) else {}
    aggregate_zero = (
        isinstance(bilinear, dict)
        and bilinear.get("denominator") == 74173536
        and bilinear.get("projected_plus_internal_quant_violations") == 0
    )
    channel_zero = all(
        isinstance(by_channel.get(channel), dict)
        and by_channel[channel].get("projected_plus_internal_quant_violations") == 0
        for channel in ("R", "G", "B")
    )
    add(checks, "source", "source.bilinear-aggregate-zero",
        aggregate_zero, "bilinear aggregate=0/74,173,536")
    add(checks, "source", "source.bilinear-channel-zero",
        channel_zero, "bilinear R/G/B each equal zero")

    # Correct current status and superseded history.
    add(checks, "m8", "m8.axis-fail",
        m8_value.startswith("**FAIL** — M8-R"),
        "axis verdict remains FAIL on M8-R")
    add(checks, "m8", "m8.r-value",
        "`1.030569%`" in m8_value,
        "M8-R value remains 1.030569%")
    add(checks, "m8", "m8.r-zero-bar",
        "achievable bar of exactly `0.0000%`" in m8_value,
        "M8-R retains achievable exact-zero bar")
    add(checks, "m8", "m8.r-readiness-fail",
        contains(readiness,
                 "M8 remains `FAIL`: M8-R is `1.030569%` against the achievable "
                 "`0.0000%` bar."),
        "readiness table preserves the genuine failure")
    add(checks, "m8", "m8.superseded-line",
        after.splitlines().count(SUPERSEDED_LINE) == 1,
        f"exact superseded line count={after.splitlines().count(SUPERSEDED_LINE)}")
    v14_lines = [line for line in after.splitlines() if "`1.326144%`" in line]
    add(checks, "m8", "m8.v14-all-superseded",
        len(v14_lines) == 3
        and all("supersed" in line.lower() for line in v14_lines),
        f"v1.4 figure occurrences={len(v14_lines)}")
    add(checks, "m8", "m8.v14-impossibility-count",
        contains(m8,
                 "At `977,684` required census coordinates the hull has "
                 "`lo - tolerance > 1`"),
        "metric card states the impossibility population")
    add(checks, "m8", "m8.v15-unmeasured-readiness",
        "M8-O v1.5 `UNMEASURED`" in readiness
        and "no v1.5 M8-O score exists" in readiness,
        "readiness table records no v1.5 score")
    add(checks, "m8", "m8.v15-unmeasured-card",
        contains(m8,
                 "**Status: `UNMEASURED`.** The replacement checker was corrected "
                 "at `e5489d64` but has not been independently recommissioned, so "
                 "no v1.5 M8-O score exists."),
        "metric card records unrecommissioned checker")
    add(checks, "m8", "m8.v15-unmeasured-result",
        "M8-O v1.5 **UNMEASURED**" in m8_value
        and "`e5489d64` has not been recommissioned" in m8_value,
        "result table records v1.5 UNMEASURED")
    add(checks, "m8", "m8.no-diagnostic-count",
        DIAGNOSTIC_COUNT not in after,
        "diagnostic count is absent from the scorecard")
    add(checks, "m8", "m8.no-old-combined-failure",
        "M8-O `1.326144%` against a bar of exactly `0.0000%`" not in after
        and "M8-O is a separate downstream failure" not in after,
        "obsolete M8-O failure wording is absent")
    add(checks, "m8", "m8.only-r-produced-read-readiness",
        "M8-R is the only produced-and-read score against an achievable bar."
        in readiness,
        "readiness claim is narrowed to M8-R")
    add(checks, "m8", "m8.only-r-produced-read-card",
        contains(m8,
                 "M8-R is the only produced-and-read score against an achievable bar."),
        "metric-card claim is narrowed to M8-R")
    add(checks, "m8", "m8.only-r-produced-read-result",
        "M8-R is the only produced-and-read score against an achievable bar"
        in m8_standing,
        "result-table claim is narrowed to M8-R")
    add(checks, "m8", "m8.no-old-only-axis-claim",
        "only axis in the program with a produced-and-read score" not in after
        and "only scored axis result" not in after,
        "overbroad only-axis claims are absent")

    # Achievability and discrimination evidence without a promoted candidate score.
    add(checks, "discrimination", "m8.bilinear-zero-card",
        contains(m8,
                 "a clean bilinear kernel measures exactly `0/74,173,536`"),
        "metric card records clean bilinear zero")
    add(checks, "discrimination", "m8.bilinear-channels-card",
        contains(m8, "independently zero in R, G, and B"),
        "metric card records independent channel zeros")
    add(checks, "discrimination", "m8.bilinear-zero-result",
        "`0/74,173,536`" in m8_standing,
        "result standing records clean bilinear zero")
    add(checks, "discrimination", "m8.bilinear-channels-result",
        "independently zero in R, G, and B" in m8_standing,
        "result standing records channel-specific zeros")
    add(checks, "discrimination", "m8.discriminating-card",
        contains(m8,
                 "the shipping Catmull-Rom kernel does not clear the diagnostic "
                 "reanalysis. The latter is not promoted to a score."),
        "card records discrimination without a promoted score")
    add(checks, "discrimination", "m8.bilinear-not-candidate-score",
        contains(m8,
                 "The clean bilinear `0/74,173,536` result is achievability and "
                 "discrimination evidence, not a candidate score."),
        "clean control is not mislabeled as candidate score")
    add(checks, "discrimination", "m8.m166-citation",
        contains(m8,
                 "`docs/research/M166-bar-achievability.md`, "
                 "\"M8-R: ACHIEVABLE\" clause"),
        "M8-R achievability is cited")

    # Scope and non-weakening against the accepted M162 commit.
    expected_changed = {"3", "4", "6"}
    all_keys = set(before_sections) | set(after_sections)
    changed = {
        key for key in all_keys
        if before_sections.get(key) != after_sections.get(key)
    }
    add(checks, "integrity", "integrity.changed-sections",
        changed == expected_changed,
        f"changed={','.join(sorted(changed))}")
    for section in ("PREAMBLE", "0", "1", "2", "5", "7", "8"):
        add(checks, "integrity", f"integrity.section-{section.lower()}-unchanged",
            before_sections.get(section) == after_sections.get(section),
            "byte-identical")

    expected_ids = [f"M{number}" for number in range(1, 13)]
    before_section3 = before_sections.get("3", "")
    for metric in expected_ids:
        before_rows = metric_rows(before_section3, metric)
        after_rows = metric_rows(section3, metric)
        if metric == "M8":
            add(checks, "integrity", "integrity.m8-glance-zero-preserved",
                "`0.0000%`" in glance,
                "M8 exact-zero target remains")
        else:
            add(checks, "integrity", f"integrity.{metric.lower()}-section3-rows",
                before_rows == after_rows,
                "readiness and at-a-glance rows are byte-identical")

    for metric in expected_ids:
        if metric == "M8":
            continue
        add(checks, "integrity", f"integrity.{metric.lower()}-card",
            metric_card(before, metric) == metric_card(after, metric),
            "metric card is byte-identical")

    add(checks, "integrity", "integrity.m8-r-definition",
        m8_r_definition(metric_card(before, "M8")) == m8_r_definition(m8),
        "M8-R definition is byte-identical")

    before_results = before_sections.get("6", "")
    for metric in expected_ids:
        if metric == "M8":
            continue
        add(checks, "integrity", f"integrity.{metric.lower()}-result-row",
            metric_rows(before_results, metric) == metric_rows(section6, metric),
            "result row is byte-identical")

    before_m8_cells = cells(metric_rows(before_results, "M8")[0])
    preserved_indices = (0, 1, 3, 4, 5)
    add(checks, "integrity", "integrity.m8-non-strehl-cells",
        len(before_m8_cells) == 7
        and len(result_cells) == 7
        and all(
            before_m8_cells[index] == result_cells[index]
            for index in preserved_indices
        ),
        "M8 comparator cells and label are preserved")
    add(checks, "integrity", "integrity.fail-count",
        after.count("**FAIL**") == before.count("**FAIL**"),
        f"before={before.count('**FAIL**')} after={after.count('**FAIL**')}")
    add(checks, "integrity", "integrity.fork-blockers",
        sum(
            len(cells(row)) == 7
            and cells(row)[4] == "**UNMEASURED — blocker (d).**"
            for metric in expected_ids
            for row in metric_rows(section6, metric)
        ) == 12,
        "all twelve fork blocker cells remain")
    add(checks, "integrity", "integrity.joint-row-once",
        ncount(after,
               "| M2 flat/defocused-ground noise + M4 flat power + M8 hull; "
               "M1 detail when available |") == 1,
        "F4/F14 merged row remains single")
    add(checks, "integrity", "integrity.qflat-retained",
        contains(after,
                 "the same output must still have median `Q_flat<=1.00`"),
        "retained Q_flat guard remains")

    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default=BASE_REV)
    parser.add_argument("--after-rev")
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    args = parser.parse_args()

    try:
        before = git_blob(args.before_rev, SCORECARD_PATH)
        after = (
            git_blob(args.after_rev, SCORECARD_PATH)
            if args.after_rev
            else read_utf8(args.scorecard.resolve())
        )
        m136 = git_blob(M136_REV, M136_PATH)
        m166 = git_blob(M166_REV, M166_PATH)
        analysis = json.loads(git_blob(ANALYSIS_REV, ANALYSIS_PATH))
        checker_subject = git_subject(CHECKER_REV)
        checks = run_checks(after, before, m136, m166, analysis, checker_subject)
    except (OSError, UnicodeDecodeError, RuntimeError, json.JSONDecodeError) as exc:
        emit(f"ERROR {exc}")
        return 2

    groups: dict[str, list[int]] = {}
    for check in checks:
        emit(f"{'PASS' if check.passed else 'FAIL'} {check.name}: {check.detail}")
        counts = groups.setdefault(check.group, [0, 0])
        counts[0] += int(check.passed)
        counts[1] += int(not check.passed)

    for group in sorted(groups):
        passed, failed = groups[group]
        emit(f"GROUP_SUM {group} total={passed + failed} passed={passed} failed={failed}")

    passed = sum(check.passed for check in checks)
    failed = len(checks) - passed
    skipped = 0
    accounted = passed + failed + skipped
    emit(
        f"SUMMARY total={len(checks)} passed={passed} failed={failed} "
        f"skipped={skipped} accounted={accounted}"
    )
    emit("VERDICT GREEN" if failed == 0 else "VERDICT RED")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
