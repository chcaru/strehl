#!/usr/bin/env python3
"""Verify the M162 fork-provenance correction by content, not line number.

The scorecard baseline and optional committed result are read as raw ``git show``
bytes and decoded as UTF-8. Wrapped prose is compared after Markdown blockquote
prefixes are stripped per physical line and whitespace is collapsed.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
M162_PATH = "docs/research/M162-noise-regression.md"
BASE_REV = "7648d360"
RECONCILED_REV = "7bee3738"
M162_REV = "ed5fa20b"
FORK_COMMIT = "4bc7f95e448cf20ee2bdd758403ec43e2612a1c6"
FORK_CELL = "**UNMEASURED — blocker (d).**"


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


def git_blob(rev: str, path: str = SCORECARD_PATH) -> str:
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


def metric_row(section: str, metric: str) -> str:
    rows = [
        line
        for line in section.splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]
    return rows[0] if rows else ""


def cells(row: str) -> list[str]:
    return [part.strip() for part in row.strip().strip("|").split("|")]


def add(
    checks: list[Check], group: str, name: str, passed: bool, detail: str
) -> None:
    checks.append(Check(group, name, passed, detail))


def run_checks(after: str, before: str, source: str) -> list[Check]:
    checks: list[Check] = []
    after_sections = top_sections(after)
    before_sections = top_sections(before)
    decision = subsection(after, "0.1 Decision rule")
    contracts = subsection(after, "1.2 Two frozen input contracts")
    settings = subsection(after, "1.4 Comparator settings")
    readiness = subsection(after, "3.1 Measurement readiness as of v1.7")
    m2 = metric_card(after, "M2")
    results = after_sections.get("6", "")
    corrections = after_sections.get("7", "")
    publication = after_sections.get("8", "")

    # M162 primary evidence.
    add(checks, "source", "source.archived-input-count",
        contains(source, "The archived run used 105 Lightroom-developed TIFFs."),
        "M162 identifies 105 developed TIFF inputs")
    add(checks, "source", "source.no-bound-producer",
        contains(source,
                 "No executable or source revision is cryptographically bound "
                 "to the render."),
        "M162 finds no bound producer")
    add(checks, "source", "source.postdated-executable",
        contains(source,
                 "The retained May 17 executable postdates it by six days and "
                 "is not its producer."),
        "M162 rejects the retained executable as producer")
    add(checks, "source", "source.opaque-output",
        contains(source,
                 "the fork's “best-known build” is an opaque, byte-pinned output "
                 "and archived run, not a reproducible build"),
        "M162 classifies the old artifact")
    add(checks, "source", "source.first-retained-commit",
        FORK_COMMIT in source,
        "M162 records the first retained fork commit")
    add(checks, "source", "source.unrelated-histories",
        contains(source, "The repositories have unrelated Git histories."),
        "M162 rules out a cross-project bisect")

    # Archived artifact disposition.
    add(checks, "fork", "fork.archive-common-inadmissible",
        contains(after,
                 "The archived fork output is not an admissible common-merge arm."),
        "decision rule excludes the archive from common merge")
    add(checks, "fork", "fork.archive-labelled-historical-native",
        ncount(after, "HISTORICAL / `PRODUCT_NATIVE_END_TO_END` DIAGNOSTIC ONLY") == 2,
        "the archive has the explicit historical/product-native-only label twice")
    add(checks, "fork", "fork.archive-developed-input",
        contains(settings,
                 "the byte-pinned artifact used `105` Lightroom-developed TIFFs"),
        "comparator settings state the developed-input defect")
    add(checks, "fork", "fork.archive-no-bound-producer",
        contains(settings,
                 "has no producing binary or source revision bound to the render, "
                 "and is not reproducible"),
        "comparator settings state the provenance defect")
    add(checks, "fork", "fork.archive-postdated-exe",
        contains(settings,
                 "The retained May 17 executable postdates the render by six days "
                 "and is not its producer."),
        "comparator settings reject the retained executable")
    add(checks, "fork", "fork.archive-not-current-native-arm",
        contains(contracts,
                 "It also does not satisfy the registered product-native contract "
                 "below because neither its input lineage nor its producing binary "
                 "was frozen to that protocol."),
        "archive is not misrepresented as a current scored native arm")
    add(checks, "fork", "fork.archive-no-bisect",
        contains(settings,
                 "unrelated repository histories also prohibit a cross-project bisect"),
        "scorecard records the history boundary")
    add(checks, "fork", "fork.m2-diagnostic-qualified",
        ncount(after, "historical archived fork output") >= 3
        and contains(m2, "not an admissible common-merge comparator"),
        "M159 comparison is explicitly historical/product-native diagnostic")

    # Required replacement arm.
    add(checks, "rebuild", "fork.rebuild-required-set",
        contains(decision,
                 "a fresh fork rebuild from the best-known retained source revision, "
                 "pinned by commit before scoring, with the built executable's hash "
                 "frozen before rendering"),
        "required set names a fresh commit-pinned rebuild")
    add(checks, "rebuild", "fork.rebuild-common-identical-input",
        contains(contracts,
                 "the fresh commit-pinned best-known-source fork rebuild, and strehl "
                 "must receive the exact same TIFF bytes"),
        "fresh rebuild receives the common bytes")
    add(checks, "rebuild", "fork.rebuild-executable-pre-frozen",
        contains(contracts,
                 "The fork's built-executable hash must be frozen before rendering."),
        "executable hash is frozen before rendering")
    add(checks, "rebuild", "fork.rebuild-commit-pinned",
        contains(settings,
                 "The required fork arm must be a fresh rebuild from the best-known "
                 "retained source revision, pinned by commit before scoring."),
        "settings require the source commit pin")
    add(checks, "rebuild", "fork.rebuild-freeze-protocol",
        contains(settings,
                 "source-tree hash, toolchain and dependency lock, compiler flags, "
                 "final executable SHA-256, and complete settings manifest before "
                 "rendering")
        or contains(settings,
                    "source-tree hash, toolchain and dependency lock, compiler "
                    "flags, final executable SHA-256, and complete settings manifest "
                    "**before rendering**"),
        "settings freeze the complete build identity")
    add(checks, "rebuild", "fork.first-retained-commit",
        ncount(after, FORK_COMMIT) == 2,
        f"first retained commit occurrences={ncount(after, FORK_COMMIT)}")
    add(checks, "rebuild", "fork.build-not-assumed",
        contains(settings, "that proves a source pin exists, not that it builds"),
        "the scorecard does not claim that the retained commit builds")
    add(checks, "rebuild", "fork.readiness-requires-rebuild",
        contains(readiness,
                 "a fresh commit-pinned best-known-source fork rebuild whose "
                 "executable hash was frozen before rendering"),
        "readiness blocker names the admissible arm")
    add(checks, "rebuild", "fork.archive-cannot-clear-blocker",
        contains(readiness, "The archived fork output cannot clear `(d)`."),
        "readiness cannot be cleared by the archive")
    add(checks, "rebuild", "fork.clear-condition",
        contains(settings,
                 "Until the fork is rebuilt from its pinned best-known retained "
                 "source revision, its executable hash is frozen before rendering, "
                 "and it consumes the exact common-input TIFF bytes, the fork arm "
                 "is explicitly `UNMEASURED` under blocker `(d)`."),
        "the exact clearing condition is stated")
    add(checks, "rebuild", "fork.section7-required-arm",
        contains(corrections,
                 "a fresh fork rebuild from the best-known retained source revision, "
                 "pinned by commit before scoring, with its executable hash frozen "
                 "before rendering"),
        "§7 carries the corrected required arm")
    add(checks, "rebuild", "fork.public-sentence-required-arm",
        contains(publication,
                 "a fresh commit-pinned rebuild of the fork's best-known retained "
                 "source revision whose executable hash was frozen before rendering"),
        "public sentence names the admissible fork")
    add(checks, "rebuild", "fork.public-sentence-blocker",
        contains(publication,
                 "The fork arm is `UNMEASURED` under blocker `(d)` until that "
                 "rebuild consumes the exact common-input TIFFs"),
        "public sentence states current status and clearing condition")

    # Result schema: every fork cell has an explicit existing status token.
    expected_ids = [f"M{number}" for number in range(1, 13)]
    result_rows = {metric: metric_row(results, metric) for metric in expected_ids}
    parsed = {metric: cells(row) for metric, row in result_rows.items()}
    fork_cells = {
        metric: row_cells[4] if len(row_cells) == 7 else ""
        for metric, row_cells in parsed.items()
    }
    add(checks, "table", "fork.column-header",
        "| Fork (commit-pinned best-known-source common-merge rebuild) |" in results,
        "result schema names the required rebuild")
    add(checks, "table", "fork.column-status-count",
        sum(value == FORK_CELL for value in fork_cells.values()) == 12,
        f"explicit blocker cells={sum(value == FORK_CELL for value in fork_cells.values())}/12")
    add(checks, "table", "fork.column-no-blank",
        all(fork_cells.values()),
        "no fork result cell is blank")
    add(checks, "table", "fork.column-status-token",
        all("UNMEASURED" in value for value in fork_cells.values()),
        "all fork cells use the existing UNMEASURED token")
    add(checks, "table", "fork.column-blocker-token",
        all("blocker (d)" in value for value in fork_cells.values()),
        "all fork cells identify blocker (d)")
    add(checks, "table", "fork.column-explanation",
        contains(results,
                 "The fork column is explicitly `UNMEASURED` under blocker `(d)` "
                 "until a fresh rebuild of the best-known retained source revision "
                 "exists under a pre-scoring commit pin, its executable hash is "
                 "frozen before rendering, and it successfully consumes the exact "
                 "common-input TIFF bytes."),
        "table states what clears the blocker")
    add(checks, "table", "fork.archive-cannot-fill-column",
        contains(results,
                 "The historical archived fork output cannot populate this column."),
        "table excludes the archive")
    add(checks, "table", "fork.no-old-header",
        "| Fork (frozen best-known build) |" not in results,
        "obsolete header is absent")

    # Position-aware old wording: the plan quotation remains, operative text does not.
    add(checks, "position", "fork.plan-quote-retained",
        ncount(after, "the fork rebuilt at its best-known build") == 1,
        "the owner's quoted wording occurs exactly once")
    operative = "\n".join(
        [decision, contracts, settings, readiness, corrections, publication]
    )
    add(checks, "position", "fork.no-operative-best-known-label",
        "fork at its frozen best-known build" not in normalise(operative)
        and "best-known source revision" not in normalise(operative),
        "obsolete build label occurs nowhere operative")

    # No-bar-moved and no-FAIL-erased checks against the committed F5/F6/F14 blob.
    expected_changed = {"0", "1", "3", "4", "6", "7", "8"}
    all_keys = set(before_sections) | set(after_sections)
    changed = {
        key for key in all_keys
        if before_sections.get(key) != after_sections.get(key)
    }
    add(checks, "integrity", "integrity.changed-sections",
        changed == expected_changed,
        f"changed={','.join(sorted(changed))}")
    add(checks, "integrity", "integrity.section2-unchanged",
        before_sections.get("2") == after_sections.get("2"),
        "frozen capture set is byte-identical")
    add(checks, "integrity", "integrity.section5-unchanged",
        before_sections.get("5") == after_sections.get("5"),
        "rejected-primary-metrics section is byte-identical")
    add(checks, "integrity", "integrity.fail-count",
        after.count("**FAIL**") == before.count("**FAIL**"),
        f"before={before.count('**FAIL**')} after={after.count('**FAIL**')}")

    before_glance = before_sections.get("3", "")
    after_glance = after_sections.get("3", "")
    for metric in expected_ids:
        add(checks, "integrity", f"integrity.{metric.lower()}-glance-row",
            metric_row(before_glance, metric) == metric_row(after_glance, metric),
            "byte-identical")
        add(checks, "integrity", f"integrity.{metric.lower()}-success",
            success_block(metric_card(before, metric))
            == success_block(metric_card(after, metric)),
            "content-identical")

    # Every unchanged scoreboard field remains byte-identical; only the fork cells
    # and the M2 diagnostic qualification may differ.
    before_results = before_sections.get("6", "")
    for metric in expected_ids:
        before_cells = cells(metric_row(before_results, metric))
        after_cells = parsed[metric]
        if metric == "M2":
            indices = (0, 1, 3, 5, 6)
        else:
            indices = (0, 1, 2, 3, 5, 6)
        preserved = (
            len(before_cells) == 7
            and len(after_cells) == 7
            and all(before_cells[index] == after_cells[index] for index in indices)
        )
        add(checks, "integrity", f"integrity.{metric.lower()}-result-fields",
            preserved, "all non-fork fields preserved")

    m8 = parsed.get("M8", [])
    m8_strehl = m8[2] if len(m8) == 7 else ""
    add(checks, "integrity", "integrity.m8-fail",
        "**FAIL**" in m8_strehl, "M8 remains FAIL")
    add(checks, "integrity", "integrity.m8-r",
        "`1.030569%`" in m8_strehl, "M8-R remains 1.030569%")
    add(checks, "integrity", "integrity.m8-o",
        "`1.326144%`" in m8_strehl, "M8-O remains 1.326144%")
    add(checks, "integrity", "integrity.m8-bar",
        "exactly `0.0000%`" in m8_strehl, "M8's exact zero bar remains")
    add(checks, "integrity", "integrity.joint-row-once",
        ncount(after,
               "| M2 flat/defocused-ground noise + M4 flat power + M8 hull; "
               "M1 detail when available |") == 1,
        "F4/F14 merged row still occurs exactly once")
    add(checks, "integrity", "integrity.qflat-retained",
        contains(after,
                 "the same output must still have median `Q_flat<=1.00`"),
        "the retained F4/F14 anti-cheat component remains")

    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default=BASE_REV)
    parser.add_argument("--after-rev", default=RECONCILED_REV)
    parser.add_argument("--source-rev", default=M162_REV)
    parser.add_argument("--scorecard", type=Path)
    args = parser.parse_args()

    try:
        before = git_blob(args.before_rev)
        after = (
            read_utf8(args.scorecard.resolve())
            if args.scorecard
            else git_blob(args.after_rev)
        )
        source = git_blob(args.source_rev, M162_PATH)
        checks = run_checks(after, before, source)
    except (OSError, UnicodeDecodeError, RuntimeError) as exc:
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
