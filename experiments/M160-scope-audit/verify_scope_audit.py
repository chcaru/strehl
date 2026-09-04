#!/usr/bin/env python3
"""Independent audit of scorecard commit 6b966d8c against the owner's plan."""
from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/proposals/2026-08-sota-path.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
TARGET_REV = "6b966d8c"
PARENT_REV = "c30c93b0"


@dataclass(frozen=True)
class Check:
    claim: str
    check_id: str
    passed: bool
    evidence: str


@dataclass(frozen=True)
class Mapping:
    axis: str
    predicate: str
    instrument: str
    scorecard_metric: str
    source_phrases: tuple[str, ...]
    confidence: str
    rationale: str


MAPPINGS = (
    Mapping(
        "M1",
        "resolves detail at or beyond the best shipping comparator",
        "D1: FRC + slant-edge; licensed Zerene PMax and DMap",
        "Sharpening-safe resolved information",
        (
            "resolves detail at or beyond the best shipping comparator",
            "D1: FRC + slant-edge, licensed Zerene PMax *and* DMap",
        ),
        "HIGH (0.99)",
        "M1 is the scorecard's sharpening-safe resolved-information axis.",
    ),
    Mapping(
        "M2",
        "at strictly lower noise",
        "existing flat-ROI instrument",
        "Noise efficiency at matched information",
        ("at strictly lower noise", "existing flat-ROI instrument"),
        "HIGH (0.99)",
        "M2 is the noise-efficiency axis.",
    ),
    Mapping(
        "M8",
        "with zero invented structure",
        "hull census, stamped per file",
        "Invented values / source-hull certificate",
        ("with zero invented structure", "hull census, stamped per file"),
        "HIGH (1.00)",
        "M8 is explicitly the independent source-hull census.",
    ),
    Mapping(
        "M3",
        "no occlusion veil above [bar]",
        "halo instrument at full reach",
        "Occlusion halo and broad veil",
        ("no occlusion veil above [bar]", "halo instrument at full reach"),
        "HIGH (0.99)",
        "M3 is the occlusion-halo and broad-veil axis.",
    ),
    Mapping(
        "M9",
        "per-pixel certified acuity and n_eff",
        "D2/D8 empirical and model certificate channels",
        "Acuity / `n_eff` certificate calibration",
        (
            "emitting per-pixel certified acuity, n_eff",
            "D2/D8/A5/C5",
        ),
        "HIGH (0.98)",
        "M9 is titled acuity / n_eff certificate calibration; D2 and D8 supply those channels.",
    ),
    Mapping(
        "M10",
        "depth in physical units",
        "A5 depth field + C5 metric conversion",
        "Physical depth product",
        ("depth in physical units", "D2/D8/A5/C5"),
        "HIGH (0.98)",
        "M10 is the physical-depth-product axis; A5 supplies z and C5 converts it to metric units.",
    ),
    Mapping(
        "M11",
        "[X] seconds per frame on CPU",
        "existing harness",
        "Wall-clock throughput",
        ("s per frame on CPU", "existing harness"),
        "HIGH (1.00)",
        "M11 is wall-clock throughput; the sentence names time, not memory or determinism.",
    ),
)


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


def containing_line_hits(text: str, anchor: str) -> list[tuple[int, str]]:
    return [
        (index, line)
        for index, line in enumerate(text.splitlines())
        if anchor in line
    ]


def unique_line(text: str, anchor: str) -> tuple[int, str]:
    hits = exact_line_hits(text, anchor)
    if len(hits) != 1:
        raise ValueError(f"anchor {anchor!r}: expected 1 exact line, found {len(hits)}")
    return hits[0], text.splitlines()[hits[0]]


def slice_between(text: str, start_anchor: str, end_anchor: str | None) -> str:
    lines = text.splitlines()
    start_hits = [index for index, line in enumerate(lines) if line == start_anchor]
    if len(start_hits) != 1:
        raise ValueError(
            f"start anchor {start_anchor!r}: expected 1 exact line, found {len(start_hits)}"
        )
    start = start_hits[0]
    if end_anchor is None:
        end = len(lines)
    else:
        end_hits = [
            index
            for index, line in enumerate(lines)
            if index > start and line == end_anchor
        ]
        if len(end_hits) != 1:
            raise ValueError(
                f"end anchor {end_anchor!r}: expected 1 exact line after start, found {len(end_hits)}"
            )
        end = end_hits[0]
    return "\n".join(lines[start:end])


def blockquote_after(text: str, anchor: str) -> str:
    lines = text.splitlines()
    start, _ = unique_line(text, anchor)
    quoted: list[str] = []
    started = False
    for line in lines[start + 1:]:
        if line.startswith(">"):
            started = True
            quoted.append(line)
        elif started:
            break
        elif line.strip():
            raise ValueError(f"expected blockquote after {anchor!r}, found {line!r}")
    if not quoted:
        raise ValueError(f"no blockquote after {anchor!r}")
    return "\n".join(quoted)


def top_level_sections(text: str) -> dict[str, str]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^##\s+([0-9]+)\.\s+", line)
        if match:
            starts.append((index, match.group(1)))
    sections: dict[str, str] = {"preamble": "\n".join(lines[:starts[0][0]])}
    for position, (start, number) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        sections[number] = "\n".join(lines[start:end])
    return sections


def add(
    results: list[Check],
    claim: str,
    check_id: str,
    passed: bool,
    evidence: str,
) -> None:
    results.append(Check(claim, check_id, bool(passed), evidence))


def audit(plan: str, before: str, after: str) -> tuple[list[Check], str]:
    results: list[Check] = []

    sentence_anchor = "licensing instrument in parentheses:"
    sentence = blockquote_after(plan, sentence_anchor)
    add(
        results,
        "A",
        "A.end-state-anchor-unique",
        len(exact_line_hits(plan, sentence_anchor)) == 1,
        f"anchor_hits={len(exact_line_hits(plan, sentence_anchor))}",
    )
    scorecard_glance = slice_between(
        after,
        "## 3. Scorecard at a glance",
        "### 3.1 Measurement readiness as of v1.7",
    )
    for mapping in MAPPINGS:
        counts = {
            phrase: phrase_count(sentence, phrase)
            for phrase in mapping.source_phrases
        }
        metric_anchor = f"| {mapping.axis} | {mapping.scorecard_metric} |"
        metric_rows = containing_line_hits(scorecard_glance, metric_anchor)
        add(
            results,
            "A",
            f"A.map-{mapping.axis}",
            all(count == 1 for count in counts.values()) and len(metric_rows) == 1,
            (
                f"axis={mapping.axis} confidence={mapping.confidence} "
                f"instrument={mapping.instrument!r} phrase_counts={counts} "
                f"metric_row_hits={len(metric_rows)}"
            ),
        )
    mapped_axes = {mapping.axis for mapping in MAPPINGS}
    add(
        results,
        "A",
        "A.exact-seven-axes",
        mapped_axes == {"M1", "M2", "M3", "M8", "M9", "M10", "M11"},
        f"mapped_axes={sorted(mapped_axes)}",
    )
    unnamed_terms = (
        "non-edge artifact",
        "depth-of-field coverage",
        "highlight",
        "colour fidelity",
        "memory",
        "determinism",
        "scaling invariance",
    )
    sentence_flat = normalise(sentence).lower()
    present_unnamed = [term for term in unnamed_terms if term in sentence_flat]
    present_unnamed_axes = [
        axis
        for axis in ("M4", "M5", "M6", "M7", "M12")
        if re.search(rf"(?<![A-Z0-9]){axis}(?![A-Z0-9])", sentence)
    ]
    add(
        results,
        "A",
        "A.five-axes-unnamed",
        not present_unnamed and not present_unnamed_axes,
        (
            f"present_unnamed_terms={present_unnamed} "
            f"present_unnamed_axes={present_unnamed_axes}"
        ),
    )

    d1 = slice_between(
        plan,
        "### D1. The scorecard, built once, first",
        "### D2. The certified-acuity map — \"which file am I holding\"",
    )
    add(
        results,
        "B",
        "B.helicon-optional",
        phrase_count(d1, "Helicon if obtainable") == 1,
        f"occurrences={phrase_count(d1, 'Helicon if obtainable')}",
    )
    add(
        results,
        "B",
        "B.fork-best-known-comparator",
        phrase_count(d1, "the fork rebuilt at its best-known build") == 1,
        f"occurrences={phrase_count(d1, 'the fork rebuilt at its best-known build')}",
    )
    add(
        results,
        "B",
        "B.zerene-pmax-dmap",
        phrase_count(d1, "licensed Zerene (PMax *and* DMap") == 1,
        f"occurrences={phrase_count(d1, 'licensed Zerene (PMax *and* DMap')}",
    )

    phase_zero = slice_between(
        plan,
        "**Phase 0 — measurements and purchases (corpus-only + one capture session).**",
        "*Corpus-only lanes, no captures:*",
    )
    purchase_match = re.search(
        r"\*Owner \(purchase\):\*(.*)$",
        normalise(phase_zero),
    )
    purchase_text = purchase_match.group(1) if purchase_match else ""
    add(
        results,
        "B",
        "B.owner-purchase-zerene-only",
        bool(purchase_match)
        and "Zerene licence" in purchase_text
        and "Helicon" not in purchase_text
        and "fork" not in purchase_text.lower(),
        f"purchase={purchase_text!r}",
    )

    amendment_two = slice_between(
        plan,
        "## 12. Amendment 2 — the blockers are conjunctive, and what that does to section 9 (orchestrator, 2026-09-04)",
        "## 13. Amendment 3 — Phase 1's refutation is withdrawn, and section 9 cannot run as written (orchestrator, 2026-09-05)",
    )
    amendment_two_flat = normalise(amendment_two)
    price_start = amendment_two_flat.find("2. **`(d)` -- licence a commercial comparator.**")
    price_end = amendment_two_flat.find("3. **`(a)`+`(c)` -- one capture session.**")
    price_text = (
        amendment_two_flat[price_start:price_end]
        if price_start >= 0 and price_end > price_start
        else ""
    )
    add(
        results,
        "B",
        "B.purchase-price-points",
        "Prosumer ($189)" in price_text
        and "Professional ($289)" in price_text
        and "Helicon" not in price_text,
        f"price_clause_found={bool(price_text)}",
    )

    before_sections = top_level_sections(before)
    after_sections = top_level_sections(after)
    changed_sections = sorted(
        key
        for key in set(before_sections) | set(after_sections)
        if before_sections.get(key) != after_sections.get(key)
    )
    add(
        results,
        "C",
        "C.changed-sections-only-0-and-8",
        changed_sections == ["0", "8"],
        f"changed_sections={changed_sections}",
    )

    before_rules = slice_between(
        before,
        "### 0.1 Decision rule",
        "## 1. Measurement contract",
    )
    after_rules = slice_between(
        after,
        "### 0.1 Decision rule",
        "## 1. Measurement contract",
    )
    add(
        results,
        "C",
        "C.preexisting-decision-rules-unchanged",
        before_rules == after_rules,
        f"byte_equal={before_rules == after_rules}",
    )

    before_metric_body = slice_between(
        before,
        "## 1. Measurement contract",
        "## 8. Publication rule",
    )
    after_metric_body = slice_between(
        after,
        "## 1. Measurement contract",
        "## 8. Publication rule",
    )
    add(
        results,
        "C",
        "C.metric-bars-and-statuses-unchanged",
        before_metric_body == after_metric_body,
        f"byte_equal={before_metric_body == after_metric_body}",
    )

    before_publication = slice_between(before, "## 8. Publication rule", None)
    after_publication = slice_between(after, "## 8. Publication rule", None)
    add(
        results,
        "C",
        "C.publication-change-is-append-only",
        after_publication.startswith(before_publication.rstrip("\n")),
        f"before_chars={len(before_publication)} after_chars={len(after_publication)}",
    )

    def m8_row(text: str) -> str | None:
        rows = [
            line
            for line in text.splitlines()
            if line.startswith("| M8 | Independent source-hull census |")
        ]
        return rows[0] if len(rows) == 1 else None

    before_m8 = m8_row(before)
    after_m8 = m8_row(after)
    add(
        results,
        "C",
        "C.m8-fail-preserved",
        before_m8 is not None
        and before_m8 == after_m8
        and "**FAIL** — M8-R `1.030569%`" in after_m8,
        f"row_equal={before_m8 == after_m8} value_present={bool(after_m8 and '1.030569%' in after_m8)}",
    )

    before_fail_lines = Counter(line for line in before.splitlines() if "FAIL" in line)
    after_fail_lines = Counter(line for line in after.splitlines() if "FAIL" in line)
    lost_fail_lines = {
        line: count - after_fail_lines[line]
        for line, count in before_fail_lines.items()
        if after_fail_lines[line] < count
    }
    add(
        results,
        "C",
        "C.no-fail-text-retracted",
        not lost_fail_lines,
        f"lost_fail_lines={lost_fail_lines}",
    )

    old_requirement = (
        "passes every primary bar below against licensed Zerene Stacker and Helicon Focus"
    )
    amendment_start = (
        "> **AMENDMENT — publication scope corrected to the owner's sentence, and Helicon"
    )
    amendment_region = slice_between(
        after,
        amendment_start,
        "### 0.1 Decision rule",
    )
    amendment_start_index, _ = unique_line(after, amendment_start)
    decision_index, _ = unique_line(after, "### 0.1 Decision rule")
    after_lines = after.splitlines()
    outside_amendment = "\n".join(
        after_lines[:amendment_start_index] + after_lines[decision_index:]
    )
    old_total = phrase_count(after, old_requirement)
    old_inside = phrase_count(amendment_region, old_requirement)
    old_outside = phrase_count(outside_amendment, old_requirement)
    add(
        results,
        "C",
        "C.withdrawn-old-text-position",
        old_total == 1
        and old_inside == 1
        and old_outside == 0
        and phrase_count(amendment_region, "This paragraph previously read") == 1,
        (
            f"total={old_total} inside_withdrawal={old_inside} "
            f"outside_withdrawal={old_outside}"
        ),
    )

    def forbidden(check_id: str, anchor: str, rationale: str) -> None:
        hits = exact_line_hits(after, anchor)
        add(
            results,
            "D",
            check_id,
            len(hits) == 0,
            f"occurrences={len(hits)} anchor={anchor!r}; {rationale}",
        )

    forbidden(
        "D.scope-every-primary-hard",
        "1. Every primary metric is a hard gate. No win compensates for a loss.",
        "still makes all twelve primary metrics publication gates",
    )
    forbidden(
        "D.scope-m4-joint-hard",
        "| M1 information + M2 noise + M4 flat power + M8 hull | Harder averaging can lower noise by losing information; sharpening can flatter transfer while increasing flat power or leaving the source hull. | M1 presently has no admissible statistic. When it is replaced, publish the replacement detail value with `(eta, Q_flat, M8-R, M8-O)` from the same output and pass every bar simultaneously. Until then neither a noise-only nor a detail claim is valid. |",
        "still makes the unnamed M4 bar a prerequisite for named M1/M2/M8 claims",
    )
    forbidden(
        "D.scope-m12-joint-hard",
        "| M11 runtime + M12 determinism/scaling invariance/memory | Serial execution can make fixed-worker runs deterministic by abandoning the speed claim. | The primary CPU result is the 16-worker output; it must meet M11, reproduce at fixed width, and be byte-identical to 1/2/4/8-worker outputs while meeting M12. |",
        "still makes the unnamed M12 axis a prerequisite for named M11",
    )
    forbidden(
        "D.comparator-envelope-still-mandates-helicon",
        "   Zerene PMax, Zerene DMap, and Helicon Methods A, B, and C, each at its frozen",
        "operative envelope includes Helicon without an optional qualifier and omits the required fork",
    )
    forbidden(
        "D.common-input-still-mandates-helicon",
        "5. Zerene, Helicon, and strehl must receive the exact same TIFF bytes. A strehl TIFF",
        "operative common-input rule requires Helicon and omits the fork",
    )

    comparator_settings = slice_between(
        after,
        "### 1.4 Comparator settings",
        "### 1.5 Geometry and exclusions",
    )
    add(
        results,
        "D",
        "D.comparator-settings-missing-fork",
        bool(re.search(r"(?m)^- \*\*(?:the )?fork:", comparator_settings, re.IGNORECASE)),
        "anchor='### 1.4 Comparator settings'; no required-fork settings row",
    )
    settings_lines = comparator_settings.splitlines()
    helicon_starts = [
        index
        for index, line in enumerate(settings_lines)
        if line.startswith("- **Helicon Focus")
    ]
    strehl_starts = [
        index
        for index, line in enumerate(settings_lines)
        if line.startswith("- **strehl:**")
    ]
    helicon_bullet = ""
    if len(helicon_starts) == 1 and len(strehl_starts) == 1:
        helicon_bullet = "\n".join(
            settings_lines[helicon_starts[0]:strehl_starts[0]]
        )
    add(
        results,
        "D",
        "D.comparator-settings-helicon-not-optional",
        "when obtainable" in normalise(helicon_bullet).lower(),
        (
            "anchor='- **Helicon Focus:** licensed current shipping build; Methods A, B, "
            "and C at factory'; optional qualifier absent"
        ),
    )
    forbidden(
        "D.either-product-still-fatal",
        "exclude that mode. If either product cannot produce a linear output that passes §1.3,",
        "with only two configured products, unavailable Helicon remains fatal",
    )
    forbidden(
        "D.speed-envelope-requires-complete-scorecard",
        "is the fastest mode that passes the complete quality scorecard. This is intentionally",
        "unnamed quality axes still gate the named M11 comparator",
    )
    forbidden(
        "D.readiness-blocker-still-zerene-helicon",
        "Zerene/Helicon output, and **(e)** scientifically measurable now. An **(e)** does not",
        "blocker (d) still requires Helicon and omits the fork",
    )
    forbidden(
        "D.m11-still-requires-all-quality-gates",
        "7. Comparator speed uses the fastest mode that passes all quality gates at identical",
        "unnamed quality axes still gate M11",
    )

    scoreboard_headers = containing_line_hits(
        after,
        "| ID | Metric | strehl | Zerene Stacker | Helicon Focus | Current standing |",
    )
    add(
        results,
        "D",
        "D.scoreboard-schema-omits-fork",
        len(scoreboard_headers) == 0,
        (
            "occurrences="
            f"{len(scoreboard_headers)} anchor='| ID | Metric | strehl | Zerene Stacker | "
            "Helicon Focus | Current standing |'; required fork has no result column"
        ),
    )
    forbidden(
        "D.publication-fail-still-any-primary",
        "- `FAIL`, when any commissioned primary gate misses;",
        "an unnamed-axis miss still forces the sole FAIL verdict",
    )

    public_sentence = slice_between(
        after,
        "Until such a report exists, the only defensible public sentence is:",
        "> **AMENDMENT — what \"required\" means here.** Consistent with the §0 amendment, the",
    )
    public_flat = normalise(public_sentence).lower()
    add(
        results,
        "D",
        "D.public-sentence-uses-required-comparator-set",
        "fork" in public_flat
        and "zerene stacker" in public_flat
        and ("when obtainable" in public_flat or "optional" in public_flat),
        (
            "anchor='> **strehl’s competitive position against Zerene Stacker and "
            "Helicon Focus is'; required fork absent and optional Helicon presented as core"
        ),
    )

    return results, sentence


def claim_verdict(results: list[Check], claim: str) -> str:
    selected = [result for result in results if result.claim == claim]
    if not selected:
        return "CANNOT DETERMINE"
    return "CONFIRMED" if all(result.passed for result in selected) else "REFUTED"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--before-rev", default=PARENT_REV)
    parser.add_argument("--after-rev", default=TARGET_REV)
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
        results, sentence = audit(plan, before, after)
    except Exception as exc:
        print(f"AUDIT_ERROR {exc!r}")
        return 2

    failed = [result for result in results if not result.passed]
    passed = len(results) - len(failed)
    print(
        f"CHECKS total={len(results)} passed={passed} failed={len(failed)} "
        f"skipped=0 accounted={passed + len(failed)}"
    )
    for claim in "ABCD":
        selected = [result for result in results if result.claim == claim]
        claim_failed = sum(not result.passed for result in selected)
        print(
            f"CLAIM {claim} {claim_verdict(results, claim)} "
            f"checks={len(selected)} passed={len(selected)-claim_failed} failed={claim_failed}"
        )
    print("PLAN_SENTENCE " + normalise(sentence))
    for mapping in MAPPINGS:
        print(
            f"MAP {mapping.axis} confidence={mapping.confidence} "
            f"predicate={mapping.predicate!r} instrument={mapping.instrument!r}"
        )
    for result in results if args.verbose else failed:
        print(
            f"{'PASS' if result.passed else 'FAIL'} "
            f"{result.check_id}: {result.evidence}"
        )
    overall = (
        "CONFIRMED"
        if all(claim_verdict(results, claim) == "CONFIRMED" for claim in "ABCD")
        else "REFUTED"
    )
    print(f"AUDIT_VERDICT {overall}")
    return 0 if overall == "CONFIRMED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
