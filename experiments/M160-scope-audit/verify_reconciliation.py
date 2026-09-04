#!/usr/bin/env python3
"""Verify the M160 gate, anti-cheat, and comparator reconciliation by content."""
from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/proposals/2026-08-sota-path.md"
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
BASE_REV = "6b966d8c"
RECONCILED_REV = "513ea3fe"

OWNER_GATES = ("M1", "M2", "M3", "M8", "M9", "M10", "M11")
DISCLOSURES = ("M4", "M5", "M6", "M7", "M12")


@dataclass(frozen=True)
class Check:
    group: str
    check_id: str
    passed: bool
    evidence: str


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def git_blob(revision: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{revision}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.decode("utf-8", errors="replace").strip()
            or f"git show failed for {revision}:{path}"
        )
    return completed.stdout.decode("utf-8")


def normalise(text: str) -> str:
    lines = [re.sub(r"^\s*(?:>\s*)+", "", line) for line in text.splitlines()]
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def phrase_count(text: str, phrase: str) -> int:
    return normalise(text).count(normalise(phrase))


def exact_line_hits(text: str, anchor: str) -> list[int]:
    return [index for index, line in enumerate(text.splitlines()) if line == anchor]


def slice_between(text: str, start_anchor: str, end_anchor: str | None) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line == start_anchor]
    if len(starts) != 1:
        raise ValueError(
            f"start anchor {start_anchor!r}: expected 1 exact line, found {len(starts)}"
        )
    start = starts[0]
    if end_anchor is None:
        end = len(lines)
    else:
        ends = [
            index
            for index, line in enumerate(lines)
            if index > start and line == end_anchor
        ]
        if len(ends) != 1:
            raise ValueError(
                f"end anchor {end_anchor!r}: expected 1 exact line after start, "
                f"found {len(ends)}"
            )
        end = ends[0]
    return "\n".join(lines[start:end])


def top_level_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+([0-9]+)\.\s+", line)
        if match:
            starts.append((index, match.group(1)))
    if not starts:
        raise ValueError("no numbered top-level sections found")
    sections = {"preamble": "\n".join(lines[: starts[0][0]])}
    for position, (start, number) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        sections[number] = "\n".join(lines[start:end])
    return sections


def metric_sections(text: str) -> dict[str, str]:
    section_four = slice_between(text, "## 4. Metric cards", "## 5. Metrics deliberately rejected as primary evidence")
    lines = section_four.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^###\s+(M(?:[1-9]|1[0-2]))\s+—", line)
        if match:
            starts.append((index, match.group(1)))
    sections: dict[str, str] = {}
    for position, (start, axis) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        sections[axis] = "\n".join(lines[start:end])
    return sections


def paragraph_blocks(text: str) -> list[str]:
    return [block for block in re.split(r"\n\s*\n", text) if block.strip()]


def success_blocks(text: str) -> list[str]:
    return [
        block
        for block in paragraph_blocks(slice_between(
            text,
            "## 4. Metric cards",
            "## 5. Metrics deliberately rejected as primary evidence",
        ))
        if block.startswith("**Success.**")
    ]


def metric_rows(text: str) -> dict[str, str]:
    glance = slice_between(
        text,
        "## 3. Scorecard at a glance",
        "### 3.1 Measurement readiness as of v1.7",
    )
    rows: dict[str, str] = {}
    for line in glance.splitlines():
        match = re.match(r"^\|\s+(M(?:[1-9]|1[0-2]))\s+\|", line)
        if match:
            rows[match.group(1)] = line
    return rows


def scoreboard_rows(text: str) -> dict[str, list[str]]:
    section_six = slice_between(
        text,
        "## 6. Honest current position",
        "## 7. Corrections and gaps in the governing proposal",
    )
    rows: dict[str, list[str]] = {}
    for line in section_six.splitlines():
        match = re.match(r"^\|\s+(M(?:[1-9]|1[0-2]))\s+\|", line)
        if match:
            rows[match.group(1)] = [cell.strip() for cell in line.strip("|").split("|")]
    return rows


def bullet(text: str, start_prefix: str) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith(start_prefix)]
    if len(starts) != 1:
        return ""
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("- **"):
            end = index
            break
    return "\n".join(lines[start:end])


def add(
    checks: list[Check],
    group: str,
    check_id: str,
    passed: bool,
    evidence: str,
) -> None:
    checks.append(Check(group, check_id, bool(passed), evidence))


def audit(plan: str, before: str, after: str) -> list[Check]:
    checks: list[Check] = []

    d1 = slice_between(
        plan,
        "### D1. The scorecard, built once, first",
        "### D2. The certified-acuity map — \"which file am I holding\"",
    )
    source_phrases = {
        "source.zerene-pmax-dmap": "licensed Zerene (PMax *and* DMap",
        "source.fork-best-known": "the fork rebuilt at its best-known build",
        "source.helicon-optional": "Helicon if obtainable",
    }
    for check_id, phrase in source_phrases.items():
        count = phrase_count(d1, phrase)
        add(checks, "source", check_id, count == 1, f"occurrences={count}")

    decision = slice_between(after, "### 0.1 Decision rule", "### 0.2 Joint anti-cheat constraints")
    decision_flat = normalise(decision)
    owner_phrase = (
        "The publication gates are exactly `M1`, `M2`, `M3`, `M8`, `M9`, `M10`, "
        "and `M11`."
    )
    disclosure_phrase = (
        "`M4`, `M5`, `M6`, `M7`, and `M12` are mandatory disclosures, not "
        "independent publication gates"
    )
    add(
        checks,
        "gate",
        "gate.owner-set",
        phrase_count(decision, owner_phrase) == 1,
        f"owner_gate_phrase_hits={phrase_count(decision, owner_phrase)}",
    )
    add(
        checks,
        "gate",
        "gate.disclosure-split",
        phrase_count(decision, disclosure_phrase) == 1
        and "every one must still be measured, published in the results table" in decision_flat
        and "any miss stated prominently and without softening" in decision_flat,
        "five axes are disclosures with mandatory measurement/publication",
    )
    add(
        checks,
        "gate",
        "gate.all-twelve-measured",
        phrase_count(decision, "A verdict requires measurements for all twelve axes.") == 1,
        "all twelve measurements required before a verdict",
    )
    add(
        checks,
        "gate",
        "gate.helicon-not-unmeasured",
        "its absence is recorded and is never a reason for `UNMEASURED`" in decision_flat,
        "optional Helicon absence is non-fatal",
    )

    publication = slice_between(after, "## 8. Publication rule", None)
    publication_flat = normalise(publication)
    verdict_prefixes = (
        "- `PASS — SOTA under scorecard v1.7`,",
        "- `DISCLOSURE MISS — owner's seven-axis SOTA claim supported`,",
        "- `FAIL — owner's seven-axis SOTA claim not supported`,",
        "- `UNMEASURED`,",
    )
    verdict_prefix_hits = [
        sum(line.startswith(prefix) for line in publication.splitlines())
        for prefix in verdict_prefixes
    ]
    add(
        checks,
        "gate",
        "gate.four-verdict-states",
        all(count == 1 for count in verdict_prefix_hits),
        f"verdict_prefix_hits={verdict_prefix_hits}",
    )
    add(
        checks,
        "gate",
        "gate.clean-pass-definition",
        "only when all seven owner gates pass, including the retained M4 flat-power "
        "component within M1/M2/M8 and the retained M12 cross-worker byte-identity "
        "component within M11" in publication_flat
        and "all five meet their complete registered bars" in publication_flat
        and "This is the only clean pass." in publication_flat,
        "PASS requires seven gates including both guards, and five clean disclosures",
    )
    add(
        checks,
        "gate",
        "gate.disclosure-miss-distinct",
        "This state is **neither `PASS` nor `FAIL`**." in publication_flat
        and "must name each missed axis, its value, and its bar" in publication_flat,
        "DISCLOSURE MISS is explicitly neither PASS nor FAIL and names every miss",
    )
    add(
        checks,
        "gate",
        "gate.fail-definition",
        "when any commissioned owner gate misses, including either retained anti-cheat "
        "component within its named gate" in publication_flat
        and "A full-axis M4, M5, M6, M7, or M12 miss alone never triggers `FAIL`"
        in publication_flat,
        "FAIL is limited to owner gates and retained guards",
    )
    add(
        checks,
        "gate",
        "gate.unmeasured-definition",
        "All twelve axes are required measurements." in publication_flat
        and "required comparator arm is absent or invalid" in publication_flat
        and "when no owner gate, including its retained anti-cheat component, has failed"
        in publication_flat
        and "its absence or invalidity never triggers `UNMEASURED`" in publication_flat,
        "UNMEASURED covers incomplete required evidence but not optional Helicon",
    )
    withdrawal = slice_between(
        after,
        "> **AMENDMENT — publication scope corrected to the owner's sentence, and Helicon",
        "### 0.1 Decision rule",
    )
    old_requirement = "passes every primary bar below against licensed Zerene Stacker and Helicon Focus"
    old_inside = phrase_count(withdrawal, old_requirement)
    lines = after.splitlines()
    withdraw_start = exact_line_hits(
        after,
        "> **AMENDMENT — publication scope corrected to the owner's sentence, and Helicon",
    )[0]
    decision_start = exact_line_hits(after, "### 0.1 Decision rule")[0]
    outside_withdrawal = "\n".join(lines[:withdraw_start] + lines[decision_start:])
    legacy_phrases = (
        "Every primary metric is a hard gate.",
        "when any commissioned primary gate misses",
        "passes the complete quality scorecard",
        "passes all quality gates",
        "pass every bar simultaneously",
    )
    legacy_counts = {
        phrase: phrase_count(outside_withdrawal, phrase) for phrase in legacy_phrases
    }
    add(
        checks,
        "gate",
        "gate.withdrawal-position",
        phrase_count(after, old_requirement) == 1 and old_inside == 1,
        f"total={phrase_count(after, old_requirement)} inside={old_inside}",
    )
    add(
        checks,
        "gate",
        "gate.no-operative-broad-rule",
        all(count == 0 for count in legacy_counts.values()),
        f"legacy_counts={legacy_counts}",
    )
    glance = slice_between(
        after,
        "## 3. Scorecard at a glance",
        "### 3.1 Measurement readiness as of v1.7",
    )
    add(
        checks,
        "gate",
        "gate.at-glance-roles",
        phrase_count(
            glance,
            "`M1`, `M2`, `M3`, `M8`, `M9`, `M10`, and `M11` are **OWNER GATES**.",
        )
        == 1
        and phrase_count(
            glance,
            "`M4`, `M5`, `M6`, `M7`, and `M12` are **MANDATORY DISCLOSURES**",
        )
        == 1,
        "at-a-glance roles name both exact sets",
    )
    metric_after = metric_sections(after)
    role_hits = {
        axis: phrase_count(metric_after[axis], "**Publication role: MANDATORY DISCLOSURE.**")
        for axis in DISCLOSURES
    }
    add(
        checks,
        "gate",
        "gate.disclosure-card-labels",
        all(count == 1 for count in role_hits.values()),
        f"role_hits={role_hits}",
    )

    anti = slice_between(after, "### 0.2 Joint anti-cheat constraints", "## 1. Measurement contract")
    m4_rows = [
        line
        for line in anti.splitlines()
        if line.startswith("| M1 information + M2 noise + M8 hull + retained M4")
    ]
    m4_row = m4_rows[0] if len(m4_rows) == 1 else ""
    add(
        checks,
        "anti",
        "anti.m4-flat-power-component",
        len(m4_rows) == 1
        and "same output bytes and settings" in m4_row
        and "median `Q_flat<=1.00`" in m4_row,
        f"row_hits={len(m4_rows)} same_output={'same output bytes and settings' in m4_row} "
        f"q_flat={'median `Q_flat<=1.00`' in m4_row}",
    )
    add(
        checks,
        "anti",
        "anti.m4-full-axis-excluded",
        "failed-site rate, ghost-ratio, and comparator bars remain mandatory disclosures "
        "and do not gate the owner's verdict" in m4_row,
        "full M4 bars excluded from owner verdict",
    )
    m12_rows = [
        line
        for line in anti.splitlines()
        if line.startswith("| M11 runtime + retained M12 cross-worker byte identity")
    ]
    m12_row = m12_rows[0] if len(m12_rows) == 1 else ""
    add(
        checks,
        "anti",
        "anti.m12-cross-worker-component",
        len(m12_rows) == 1
        and "same fixed-width input" in m12_row
        and "1, 2, 4, 8, and 16 workers must be mutually byte-identical" in m12_row
        and "16-worker output and must meet M11" in m12_row,
        f"row_hits={len(m12_rows)} ladder={'mutually byte-identical' in m12_row}",
    )
    add(
        checks,
        "anti",
        "anti.m12-full-axis-excluded",
        "fixed-worker repeat, memory, N-scaling, and N-mod-4 bars remain mandatory "
        "disclosures" in m12_row,
        "full M12 bars excluded from owner verdict",
    )
    anti_flat = normalise(anti)
    add(
        checks,
        "anti",
        "anti.owner-claim-rationale",
        "protect the owner's own sentence from being satisfied by a cheat" in anti_flat
        and "retaining the full M4 or M12 axes as prerequisites would contradict the "
        "seven-axis scope" in anti_flat,
        "narrow guards are justified as fidelity rather than extra axes",
    )
    add(
        checks,
        "anti",
        "anti.m3-not-full-m5",
        "that local coherence is an M3 anti-blur component, not the full M5 axis" in anti_flat,
        "M3 local coherence is not a full M5 prerequisite",
    )
    add(
        checks,
        "anti",
        "anti.m5-m6-disclosure-only",
        "M5 and M6 remain mandatory disclosures; their misses produce `DISCLOSURE MISS`, "
        "not `FAIL`, when all seven owner gates pass, including their retained "
        "anti-cheat components" in anti_flat,
        "M5/M6 joint tuple is disclosure-only",
    )
    m11 = metric_after["M11"]
    add(
        checks,
        "anti",
        "anti.m11-comparator-qualification",
        phrase_count(
            m11,
            "Comparator speed uses the fastest mode that passes `M1`, `M2`, `M3`, and "
            "`M8` plus the retained median-`Q_flat<=1.00` anti-cheat component",
        )
        == 1
        and "full M4, M5, M6, M7, and M12 bars do not select the M11 comparator"
        in normalise(m11),
        "M11 comparator quality set is explicit and narrow",
    )
    add(
        checks,
        "anti",
        "anti.m4-card-role",
        "Only median `Q_flat<=1.00`, computed from the same output bytes and settings"
        in normalise(metric_after["M4"])
        and "do not independently gate the owner's verdict" in normalise(metric_after["M4"]),
        "M4 card separates retained component from full disclosure",
    )
    add(
        checks,
        "anti",
        "anti.m12-card-role",
        "Only mutually byte-identical output across the fixed-width 1/2/4/8/16-worker ladder"
        in normalise(metric_after["M12"])
        and "do not independently gate the owner's verdict" in normalise(metric_after["M12"]),
        "M12 card separates retained component from full disclosure",
    )
    section_seven = slice_between(
        after,
        "## 7. Corrections and gaps in the governing proposal",
        "## 8. Publication rule",
    )
    section_seven_flat = normalise(section_seven)
    add(
        checks,
        "anti",
        "anti.section-seven-reconciled",
        "fixed-width 1/2/4/8/16-worker outputs must be mutually byte-identical" in section_seven_flat
        and "retained M4 median-`Q_flat<=1.00` component" in section_seven_flat
        and "Full M4 remains a mandatory disclosure" in section_seven_flat,
        "section 7.1 repeats the narrow guards",
    )

    required_phrase = (
        "The required set is exactly licensed Zerene Stacker PMax, licensed Zerene "
        "Stacker DMap, and the fork at its frozen best-known build."
    )
    add(
        checks,
        "comparator",
        "comparator.decision-required-set",
        phrase_count(decision, required_phrase) == 1
        and phrase_count(decision, "Helicon Methods A, B, and C are added when obtainable.") == 1,
        "decision rule names three required arms and optional Helicon",
    )
    common_input = slice_between(
        after,
        "### 1.2 One common linear input",
        "### 1.3 Output transfer and the tone sentinel",
    )
    add(
        checks,
        "comparator",
        "comparator.common-input-required-set",
        phrase_count(
            common_input,
            "Licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, the fork at "
            "its frozen best-known build, and strehl must receive the exact same TIFF bytes.",
        )
        == 1
        and phrase_count(
            common_input,
            "Helicon Methods A, B, and C, when obtainable, must receive those bytes too.",
        )
        == 1,
        "common-input contract covers every required arm and optional Helicon",
    )
    settings = slice_between(after, "### 1.4 Comparator settings", "### 1.5 Geometry and exclusions")
    zerene_bullet = bullet(settings, "- **Zerene Stacker:**")
    fork_bullet = bullet(settings, "- **Fork:**")
    helicon_bullet = bullet(settings, "- **Helicon Focus, when obtainable:**")
    add(
        checks,
        "comparator",
        "comparator.zerene-settings",
        "licensed current shipping build" in zerene_bullet
        and "automatic PMax and automatic" in zerene_bullet
        and "DMap" in zerene_bullet,
        "Zerene bullet includes licensed PMax and DMap",
    )
    fork_terms = (
        "best-known source revision",
        "version and source commit",
        "source-tree hash",
        "toolchain and dependency lock",
        "compiler flags",
        "final binary SHA-256",
        "complete settings manifest",
        "before any scored output",
        "no per-subject tuning or post-result rebuild is allowed",
    )
    fork_term_hits = {
        term: term in normalise(fork_bullet) for term in fork_terms
    }
    add(
        checks,
        "comparator",
        "comparator.fork-freeze-protocol",
        bool(fork_bullet)
        and all(fork_term_hits.values())
        and "no per-subject tuning or post-result rebuild is allowed"
        in normalise(fork_bullet),
        f"fork_terms={fork_term_hits}",
    )
    add(
        checks,
        "comparator",
        "comparator.helicon-settings-optional",
        bool(helicon_bullet)
        and "when obtainable" in normalise(helicon_bullet)
        and "Methods A, B, and C" in normalise(helicon_bullet),
        "Helicon settings are explicitly optional",
    )
    settings_flat = normalise(settings)
    add(
        checks,
        "comparator",
        "comparator.required-arm-failure",
        "If any required arm — Zerene PMax, Zerene DMap, or the fork at its frozen "
        "best-known build — cannot produce a linear output that passes §1.3" in settings_flat,
        "required comparator failure remains UNMEASURED",
    )
    add(
        checks,
        "comparator",
        "comparator.optional-helicon-nonfatal",
        "If an obtainable Helicon arm is invalid, record and exclude it rather than "
        "changing the required-comparator verdict" in settings_flat,
        "invalid optional Helicon arm is non-fatal",
    )
    add(
        checks,
        "comparator",
        "comparator.speed-quality-set",
        "passes `M1`, `M2`, `M3`, and `M8` plus the retained M4 flat-power anti-cheat "
        "component" in settings_flat
        and "without making a disclosure axis an independent gate" in settings_flat,
        "speed envelope uses only applicable owner gates and retained guard",
    )
    readiness = slice_between(
        after,
        "### 3.1 Measurement readiness as of v1.7",
        "### 3.2 Closed program decision gates",
    )
    readiness_flat = normalise(readiness)
    add(
        checks,
        "comparator",
        "comparator.readiness-blocker",
        "unavailable common-input output from licensed Zerene PMax, licensed Zerene "
        "DMap, or the fork at its frozen best-known build" in readiness_flat
        and "Helicon, when obtainable, is recorded separately and never supplies blocker `(d)`"
        in readiness_flat,
        "readiness blocker requires fork and excludes optional Helicon",
    )
    scoreboard = slice_between(
        after,
        "## 6. Honest current position",
        "## 7. Corrections and gaps in the governing proposal",
    )
    header = (
        "| ID | Metric | strehl | Zerene Stacker (PMax + DMap) | "
        "Fork (frozen best-known build) | Helicon Focus (when obtainable) | "
        "Current standing |"
    )
    add(
        checks,
        "comparator",
        "comparator.scoreboard-schema",
        len(exact_line_hits(scoreboard, header)) == 1,
        f"header_hits={len(exact_line_hits(scoreboard, header))}",
    )
    after_score_rows = scoreboard_rows(after)
    fork_cells = {
        axis: row[4] if len(row) == 7 else f"column_count={len(row)}"
        for axis, row in after_score_rows.items()
    }
    add(
        checks,
        "comparator",
        "comparator.scoreboard-fork-cells",
        set(after_score_rows) == {f"M{i}" for i in range(1, 13)}
        and all(len(row) == 7 and row[4] == "**UNMEASURED**" for row in after_score_rows.values()),
        f"fork_cells={fork_cells}",
    )
    public_sentence = normalise(
        slice_between(
            after,
            "Until such a report exists, the only defensible public sentence is:",
            None,
        )
    )
    add(
        checks,
        "comparator",
        "comparator.public-sentence",
        "licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, and the fork at "
        "its frozen best-known build" in public_sentence
        and "Helicon Focus, when obtainable, is an additional optional comparator"
        in public_sentence,
        "public sentence names required set and separates optional Helicon",
    )
    add(
        checks,
        "comparator",
        "comparator.section-seven-required-set",
        "operative required arms are licensed Zerene PMax, licensed Zerene DMap, and "
        "the fork at its frozen best-known build" in section_seven_flat
        and "Helicon is added when obtainable" in section_seven_flat,
        "section 7 correction names the reconciled set",
    )
    unqualified_helicon: list[str] = []
    after_lines = after.splitlines()
    for index, line in enumerate(after_lines):
        if "Helicon" not in line or withdraw_start <= index < decision_start:
            continue
        window = normalise("\n".join(after_lines[max(0, index - 1) : index + 2])).lower()
        if "when obtainable" not in window:
            unqualified_helicon.append(line)
    add(
        checks,
        "comparator",
        "comparator.helicon-all-operative-qualified",
        not unqualified_helicon,
        f"unqualified={unqualified_helicon}",
    )
    legacy_comparator_lines = (
        "5. Zerene, Helicon, and strehl must receive the exact same TIFF bytes. A strehl TIFF",
        "exclude that mode. If either product cannot produce a linear output that passes §1.3,",
        "Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)** does not",
        "| ID | Metric | strehl | Zerene Stacker | Helicon Focus | Current standing |",
    )
    legacy_comparator_counts = {
        line: len(exact_line_hits(after, line)) for line in legacy_comparator_lines
    }
    add(
        checks,
        "comparator",
        "comparator.no-legacy-operative-rules",
        all(count == 0 for count in legacy_comparator_counts.values()),
        f"legacy_counts={legacy_comparator_counts}",
    )

    before_sections = top_level_sections(before)
    after_sections = top_level_sections(after)
    changed_sections = sorted(
        key
        for key in set(before_sections) | set(after_sections)
        if before_sections.get(key) != after_sections.get(key)
    )
    add(
        checks,
        "integrity",
        "integrity.changed-sections",
        changed_sections == ["0", "1", "3", "4", "6", "7", "8"],
        f"changed_sections={changed_sections}",
    )
    protected_top = ("preamble", "2", "5")
    protected_top_equal = {
        key: before_sections[key] == after_sections[key] for key in protected_top
    }
    add(
        checks,
        "integrity",
        "integrity.protected-top-sections",
        all(protected_top_equal.values()),
        f"byte_equal={protected_top_equal}",
    )
    protected_subsections = (
        ("### 1.1 Freeze before outputs", "### 1.2 One common linear input"),
        ("### 1.3 Output transfer and the tone sentinel", "### 1.4 Comparator settings"),
        ("### 1.5 Geometry and exclusions", "### 1.6 Commissioning before scoring"),
        ("### 1.6 Commissioning before scoring", "## 2. Frozen capture set"),
        ("### 3.2 Closed program decision gates", "## 4. Metric cards"),
    )
    subsection_equal = {
        start: slice_between(before, start, end) == slice_between(after, start, end)
        for start, end in protected_subsections
    }
    add(
        checks,
        "integrity",
        "integrity.protected-subsections",
        all(subsection_equal.values()),
        f"byte_equal={subsection_equal}",
    )
    before_metric = metric_sections(before)
    protected_metric_axes = ("M1", "M2", "M3", "M9", "M10")
    protected_metric_equal = {
        axis: before_metric[axis] == metric_after[axis] for axis in protected_metric_axes
    }
    add(
        checks,
        "integrity",
        "integrity.protected-metric-cards",
        all(protected_metric_equal.values()),
        f"byte_equal={protected_metric_equal}",
    )
    before_rows = metric_rows(before)
    after_rows = metric_rows(after)
    row_equal = {
        axis: before_rows.get(axis) == after_rows.get(axis)
        for axis in (f"M{i}" for i in range(1, 13))
    }
    add(
        checks,
        "integrity",
        "integrity.at-glance-bars-unchanged",
        all(row_equal.values()),
        f"byte_equal={row_equal}",
    )
    before_success = success_blocks(before)
    after_success = success_blocks(after)
    add(
        checks,
        "integrity",
        "integrity.success-bars-unchanged",
        before_success == after_success,
        f"before_blocks={len(before_success)} after_blocks={len(after_success)} "
        f"byte_equal={before_success == after_success}",
    )
    before_score_rows = scoreboard_rows(before)
    preserved_cells: dict[str, bool] = {}
    for axis in (f"M{i}" for i in range(1, 13)):
        old = before_score_rows.get(axis, [])
        new = after_score_rows.get(axis, [])
        preserved_cells[axis] = (
            len(old) == 6
            and len(new) == 7
            and new[:4] == old[:4]
            and new[4] == "**UNMEASURED**"
            and new[5:] == old[4:]
        )
    add(
        checks,
        "integrity",
        "integrity.scoreboard-values-preserved",
        all(preserved_cells.values()),
        f"rows_preserved={preserved_cells}",
    )
    m8 = after_score_rows.get("M8", [])
    add(
        checks,
        "integrity",
        "integrity.m8-fail-preserved",
        len(m8) == 7
        and m8[2].startswith("**FAIL** — M8-R `1.030569%`, M8-O `1.326144%`")
        and "bar of exactly `0.0000%`" in m8[2],
        f"strehl_cell={m8[2] if len(m8) == 7 else m8}",
    )
    old_m8_line = next(
        line
        for line in before.splitlines()
        if line.startswith("| M8 | Independent source-hull census |")
    )
    old_public_fail = "- `FAIL`, when any commissioned primary gate misses;"
    before_scoreboard_lines = set(
        slice_between(
            before,
            "## 6. Honest current position",
            "## 7. Corrections and gaps in the governing proposal",
        ).splitlines()
    )
    preserved_fail_lines = Counter(
        line
        for line in before.splitlines()
        if "FAIL" in line
        and line not in (old_m8_line, old_public_fail)
        and line not in before_scoreboard_lines
    )
    after_line_counts = Counter(after.splitlines())
    lost_fail_lines = {
        line: count - after_line_counts[line]
        for line, count in preserved_fail_lines.items()
        if after_line_counts[line] < count
    }
    add(
        checks,
        "integrity",
        "integrity.no-existing-fail-erased",
        not lost_fail_lines and after.count("**FAIL**") == before.count("**FAIL**"),
        f"lost_fail_lines={lost_fail_lines} bold_fail_before={before.count('**FAIL**')} "
        f"bold_fail_after={after.count('**FAIL**')}",
    )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--before-rev", default=BASE_REV)
    parser.add_argument("--after-rev", default=RECONCILED_REV)
    parser.add_argument("--after-file", type=Path)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    try:
        plan = read_utf8(args.plan.resolve())
        before = git_blob(args.before_rev, SCORECARD_PATH)
        after = (
            read_utf8(args.after_file.resolve())
            if args.after_file
            else git_blob(args.after_rev, SCORECARD_PATH)
        )
        checks = audit(plan, before, after)
    except Exception as exc:
        print(f"VERIFY_ERROR {exc!r}")
        return 2

    failed = [check for check in checks if not check.passed]
    passed = len(checks) - len(failed)
    print(
        f"CHECKS total={len(checks)} passed={passed} failed={len(failed)} "
        f"skipped=0 accounted={passed + len(failed)}"
    )
    groups = ("source", "gate", "anti", "comparator", "integrity")
    for group in groups:
        selected = [check for check in checks if check.group == group]
        group_failed = sum(not check.passed for check in selected)
        print(
            f"GROUP {group} total={len(selected)} "
            f"passed={len(selected) - group_failed} failed={group_failed}"
        )
    for check in checks if args.verbose else failed:
        print(
            f"{'PASS' if check.passed else 'FAIL'} "
            f"{check.check_id}: {check.evidence}"
        )
    verdict = "GREEN" if not failed else "RED"
    print(f"VERDICT {verdict}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
