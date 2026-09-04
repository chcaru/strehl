#!/usr/bin/env python3
"""Verify the M158 F5/F6/F14 reconciliation by content, never by line number.

The baseline and optional committed result are loaded as raw ``git show`` bytes and
decoded as UTF-8. Human quotations are compared after stripping Markdown blockquote
prefixes per physical line and collapsing whitespace, so wrapping cannot create a
false failure. Checks that could be satisfied by duplicate wording are scoped to a
named section or table row and assert occurrence counts where appropriate.
"""
from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
M158 = ROOT / "docs/research/M158-scorecard-amendment-text.md"
M159 = ROOT / "docs/research/M159-noise-clause.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
BASE_REV = "513ea3fe"
RECONCILED_REV = "7648d360"


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
    result: dict[str, str] = {
        "PREAMBLE": text[: matches[0].start()] if matches else text
    }
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result[match.group(1)] = text[match.start() : end]
    return result


def subsection(text: str, heading: str, level: int = 3) -> str:
    marker = "#" * level
    pattern = re.compile(
        rf"(?m)^{re.escape(marker)} {re.escape(heading)}\s*$"
    )
    match = pattern.search(text)
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


def metric_row(text: str, metric: str, occurrence: int = 0) -> str:
    rows = [
        line
        for line in text.splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]
    return rows[occurrence] if len(rows) > occurrence else ""


def success_block(card: str) -> str:
    match = re.search(r"\*\*Success(?: criterion)?\.\*\*", card)
    if not match:
        return ""
    following = re.search(r"(?m)^\*\*[A-Z][^*]+\.\*\*", card[match.end() :])
    end = match.end() + following.start() if following else len(card)
    return card[match.start() : end]


def numeric_tokens(text: str) -> collections.Counter[str]:
    scrubbed = re.sub(r"\bM(?:1[0-2]|[1-9])\b", "", text)
    return collections.Counter(
        re.findall(r"(?<![A-Za-z])\d+(?:,\d{3})*(?:\.\d+)?", scrubbed)
    )


def counter_subset(
    before: collections.Counter[str], after: collections.Counter[str]
) -> tuple[bool, list[str]]:
    missing = sorted(
        token
        for token, count in before.items()
        if after[token] < count
    )
    return not missing, missing


def add(
    checks: list[Check], group: str, name: str, passed: bool, detail: str
) -> None:
    checks.append(Check(group, name, passed, detail))


def run_checks(after: str, before: str, m158: str, m159: str) -> list[Check]:
    checks: list[Check] = []
    after_sections = top_sections(after)
    before_sections = top_sections(before)
    decision = subsection(after, "0.1 Decision rule")
    joint = subsection(after, "0.2 Joint anti-cheat constraints")
    contracts = subsection(after, "1.2 Two frozen input contracts")
    readiness = subsection(after, "3.1 Measurement readiness as of v1.7")
    disposition = subsection(
        after, "7.1 Disposition of the independent opposed-pair stress test"
    )
    m1 = metric_card(after, "M1")
    m2 = metric_card(after, "M2")
    m9 = metric_card(after, "M9")
    m11 = metric_card(after, "M11")
    m12 = metric_card(after, "M12")
    publication = after_sections.get("8", "")

    # Primary-source traceability.
    add(checks, "source", "source.m158-f5",
        contains(m158, "F5 — native-RAW competitive path"),
        "M158 contains the F5 amendment")
    add(checks, "source", "source.m158-f6",
        contains(m158, "F6 — blanket prohibition above 0.25 cyc/native px"),
        "M158 contains the F6 amendment")
    add(checks, "source", "source.m158-f14",
        contains(m158, "F14 — M4/M8 veto on the independent M2 noise verdict"),
        "M158 contains the F14 amendment")
    add(checks, "source", "source.m159-adverse",
        contains(m159.replace("×", "x"), "1.515208x"),
        "M159 records the adverse 1.515208x residual")
    add(checks, "source", "source.m159-sites",
        contains(m159, "0/12 sites are below one"),
        "M159 records zero of twelve sites below one")
    add(checks, "source", "source.m159-blur",
        contains(m159.replace("×", "x"), "0.571215x"),
        "M159 records the blur reward")

    # F5: two tracks with common merge as the sole publication path.
    add(checks, "track", "track.two-contracts-heading",
        bool(contracts), "§1.2 is the two-contract section")
    add(checks, "track", "track.sota-common-only",
        contains(after,
                 "The owner's publication claim is satisfiable only on that "
                 "common-merge track."),
        "owner sentence is satisfiable only on common merge")
    add(checks, "track", "track.product-native-no-competitive-wins",
        contains(after,
                 "they cannot establish a competitive detail, noise, clipping, "
                 "or colour win"),
        "product-native evidence cannot establish the four competitive wins")
    add(checks, "track", "track.scope-no-splicing",
        contains(after,
                 "Competitive reports must distinguish the tracks and may not "
                 "splice a value, setting, or verdict from one into the other.")
        and not contains(after, "except when selecting the best value"),
        "scope forbids cross-track splicing")
    add(checks, "track", "track.contracts-separate",
        contains(contracts,
                 "They answer different questions, and neither may borrow a value, "
                 "setting, or verdict from the other."),
        "§1.2 separates the tracks")
    add(checks, "track", "track.common-sole-publication",
        contains(contracts, "Common-merge track — sole publication track."),
        "common merge is labelled the sole publication track")
    add(checks, "track", "track.common-identical-bytes",
        contains(contracts,
                 "Licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, the "
                 "fork at its frozen best-known build, and strehl must receive the "
                 "exact same TIFF bytes"),
        "required arms receive identical TIFF bytes")
    add(checks, "track", "track.helicon-qualified",
        contains(contracts,
                 "Helicon Methods A, B, and C, when obtainable, must receive those "
                 "bytes too."),
        "Helicon remains when-obtainable")
    add(checks, "track", "track.native-original-arw",
        contains(contracts,
                 "Strehl receives those original ARWs through its shipping native path."),
        "native track preserves strehl's original-RAW path")
    add(checks, "track", "track.native-comparator-input",
        contains(contracts,
                 "Each registered comparator receives the earliest linear input its "
                 "frozen native stack path supports"),
        "comparators receive their earliest supported native-stack input")
    add(checks, "track", "track.native-labelled",
        contains(contracts, "labelled `PRODUCT_NATIVE_END_TO_END`"),
        "product-native results have an explicit label")
    add(checks, "track", "track.native-product-only",
        contains(contracts,
                 "may support only an explicitly labelled end-to-end product statement"),
        "native track supports product statements only")
    add(checks, "track", "track.product-native-no-gates",
        contains(contracts,
                 "cannot satisfy, rescue, veto, or otherwise alter any publication gate"),
        "native track cannot affect a publication gate")
    add(checks, "track", "track.contract-no-splicing",
        contains(contracts,
                 "No report may splice values, settings, or verdicts across tracks "
                 "into one fictional arm."),
        "§1.2 independently forbids splicing")
    add(checks, "track", "track.all-results-name-track",
        contains(contracts, "Every metric result must name its track."),
        "every metric result names a track")
    add(checks, "track", "track.gates-common-in-readiness",
        contains(after_sections.get("3", ""),
                 "Every owner gate and both retained components are evaluated on the "
                 "common-merge track."),
        "readiness section pins all gates to common merge")
    add(checks, "track", "track.m11-common-publication-bar",
        contains(m11, "COMMON-MERGE PUBLICATION BAR"),
        "M11 has a common-merge publication bar")
    add(checks, "track", "track.m11-native-product-bars",
        contains(m11, "UNCHANGED PRODUCT-NATIVE PRODUCT BARS"),
        "M11 preserves separate product-native bars")
    add(checks, "track", "track.m11-native-no-verdict",
        contains(m11,
                 "Product-native bar results are reported in full but do not "
                 "determine the publication verdict."),
        "M11 native results cannot determine the verdict")
    add(checks, "track", "track.m12-track-split",
        contains(m12,
                 "The absolute 6-GiB, scaling, determinism, and N-mod-4 bars apply "
                 "to the native product arm; comparative memory is reported but is "
                 "not a substitute."),
        "M12 distinguishes native bars from comparative memory")
    add(checks, "track", "track.section7-two-contracts",
        contains(after_sections.get("7", ""),
                 "The comparator prerequisite has two input contracts."),
        "§7 records the two-contract correction")
    add(checks, "track", "track.section8-common-only",
        ncount(publication, "pass on the common-merge track") == 2
        and contains(publication,
                     "when any commissioned owner gate misses on the "
                     "common-merge track"),
        "all three measured verdicts are common-merge-only")
    add(checks, "track", "track.section8-native-no-gate",
        contains(publication,
                 "they never supply, rescue, veto, or alter an owner gate"),
        "§8 excludes native evidence from owner gates")
    add(checks, "track", "track.section8-m12-disclosure-only",
        contains(publication,
                 "The registered product-native M12 disclosure enters only the "
                 "all-axes measurement requirement and the `PASS` / `DISCLOSURE "
                 "MISS` distinction stated above"),
        "§8 limits native M12 to disclosure accounting")
    add(checks, "track", "track.no-overbroad-native-verdict-ban",
        not contains(publication,
                     "they never supply, rescue, veto, or alter one of the four "
                     "verdicts above"),
        "§8 does not contradict registered product-native M12 disclosure accounting")
    add(checks, "track", "track.no-old-single-contract-heading",
        "### 1.2 One common linear input" not in after,
        "the obsolete one-contract heading is absent")

    # F6: conditional high-frequency licensing with three directional plants.
    add(checks, "frequency", "frequency.instrument-required",
        contains(decision,
                 "a pre-registered, independently commissioned instrument "
                 "distinguishes real scene information from aliasing, "
                 "interpolation, sharpening, and noise"),
        "a licensed independent instrument is mandatory")
    add(checks, "frequency", "frequency.input-verified",
        contains(decision,
                 "the scored subject has input-verified real contrast in that band"),
        "the subject must contain verified real high-band contrast")
    add(checks, "frequency", "frequency.physical-ceiling",
        contains(decision,
                 "The instrument must state its physical optical/sampling ceiling "
                 "and refuse above it."),
        "the instrument must enforce its physical ceiling")
    add(checks, "frequency", "frequency.improvement-control",
        contains(decision,
                 "a planted **improvement** that the instrument rewards in the "
                 "claimed direction"),
        "commissioning includes a planted improvement")
    add(checks, "frequency", "frequency.null-control",
        contains(decision, "an untuned null it does not spuriously reward"),
        "commissioning includes an untuned null")
    add(checks, "frequency", "frequency.degradation-control",
        contains(decision, "a planted degradation it penalizes"),
        "commissioning includes a planted degradation")
    add(checks, "frequency", "frequency.unlicensed-stays-unlicensed",
        contains(decision,
                 "every current reading above `0.25 cyc/native px` remains "
                 "`UNLICENSED_GT_0.25`"),
        "all current high-band readings remain unlicensed")
    add(checks, "frequency", "frequency.no-current-instrument",
        contains(decision,
                 "No licensed high-frequency instrument exists in v1.7"),
        "the current instrument void is explicit")
    add(checks, "frequency", "frequency.present-effect-unchanged",
        contains(after,
                 "This is not a relaxation in present effect: no licensed "
                 "high-frequency instrument exists"),
        "the effect on current evidence is unchanged")
    add(checks, "frequency", "frequency.not-permanent-ban",
        contains(after,
                 "It replaces a permanent prohibition with hard, named admission "
                 "conditions"),
        "the change is conditional rather than a permanent ban")
    add(checks, "frequency", "frequency.m1-declares-range",
        contains(m1,
                 "must declare and commission its licensed frequency range"),
        "M1 replacement declares its licensed range")
    add(checks, "frequency", "frequency.m1-three-directions",
        contains(m1,
                 "planted-improvement, untuned-null, and planted-degradation "
                 "requirements"),
        "M1 incorporates all three directional controls")
    add(checks, "frequency", "frequency.m9-output-status",
        contains(m9,
                 "A band above `0.25 cyc/native px` may improve the score only "
                 "when its truth instrument separately satisfies decision rule 7"),
        "M9 high-band evidence is conditional on the licensed truth instrument")
    add(checks, "frequency", "frequency.m9-no-instrument",
        contains(m9,
                 "M9 has no independently commissioned empirical acuity truth"),
        "M9 records the missing instrument")
    add(checks, "frequency", "frequency.m9-remains-unmeasured",
        contains(m9,
                 "M9 has no independently commissioned empirical acuity truth and "
                 "is `UNMEASURED`. No current above-`0.25 cyc/native px` reading "
                 "satisfies decision rule 7, so every such band remains "
                 "`UNLICENSED_GT_0.25`."),
        "M9's current status did not improve")
    add(checks, "frequency", "frequency.old-blanket-ban-gone",
        not contains(after,
                     "No score above `0.25 cyc/native px` is admissible evidence "
                     "for any pass/fail decision or public numerical detail claim."),
        "the superseded permanent prohibition is absent")

    # F14: independent M2 verdict, honest void, and preserved adverse readings.
    joint_rows = [
        line for line in joint.splitlines()
        if line.startswith("| M2 flat/defocused-ground noise")
    ]
    add(checks, "m2", "m2.joint-row-once",
        len(joint_rows) == 1,
        f"merged F4/F14 joint row count={len(joint_rows)}")
    add(checks, "m2", "m2.joint-independent-verdicts",
        len(joint_rows) == 1
        and contains(joint_rows[0],
                     "Each full axis retains its own bar and verdict; the tuple "
                     "has no aggregate axis verdict."),
        "the joint tuple does not replace axis verdicts")
    add(checks, "m2", "m2.joint-no-conversion",
        len(joint_rows) == 1
        and contains(joint_rows[0],
                     "does not convert M2 to `FAIL` or `UNMEASURED`"),
        "joint M4/M8 misses do not convert M2")
    add(checks, "m2", "m2.joint-no-excuse",
        len(joint_rows) == 1
        and contains(joint_rows[0],
                     "never excuses either failure or licenses detail"),
        "an M2 pass excuses no M4/M8 miss or detail claim")
    add(checks, "m2", "m2.retained-qflat",
        len(joint_rows) == 1
        and contains(joint_rows[0],
                     "the same output must still have median `Q_flat<=1.00`"),
        "the accepted narrow M4 anti-cheat component remains")
    add(checks, "m2", "m2.disposition-independent",
        contains(disposition,
                 "does not convert M2 to `FAIL` or `UNMEASURED`"),
        "§7.1 repeats the independent-verdict rule")
    add(checks, "m2", "m2.disposition-qflat",
        contains(disposition,
                 "retained median-`Q_flat<=1.00` component still protects the "
                 "owner's overall M1/M2/M8 gate"),
        "§7.1 preserves the accepted narrow M4 component")
    add(checks, "m2", "m2.name-at-glance",
        "Flat/defocused-ground noise" in metric_row(after_sections.get("3", ""), "M2", 0),
        "at-a-glance M2 name is corrected")
    add(checks, "m2", "m2.name-card",
        m2.startswith("### M2 — flat/defocused-ground noise"),
        "M2 card name is corrected")
    add(checks, "m2", "m2.name-scoreboard",
        "Flat/defocused-ground noise" in metric_row(after_sections.get("6", ""), "M2", 0),
        "results-table M2 name is corrected")
    add(checks, "m2", "m2.old-name-absent",
        ncount(after, "Noise efficiency at matched information") == 0,
        "the unsupported matched-information name is absent")
    add(checks, "m2", "m2.target",
        contains(metric_row(after_sections.get("3", ""), "M2", 0),
                 "Cross-fit efficiency `<=1.10`; 95% upper bound of strehl / "
                 "quietest qualifying comparator `<=0.950`."),
        "M2's numerical target is unchanged")
    add(checks, "m2", "m2.instrument-void-card",
        contains(m2, "Instrument status: INSTRUMENT VOID; current axis verdict `UNMEASURED`."),
        "M2 card retains the instrument void")
    add(checks, "m2", "m2.instrument-void-readiness",
        contains(readiness, "M2 | **INSTRUMENT VOID;"),
        "readiness table retains the instrument void")
    add(checks, "m2", "m2.instrument-void-scoreboard",
        contains(after_sections.get("6", ""),
                 "M2 | Flat/defocused-ground noise | **UNMEASURED — INSTRUMENT VOID.**"),
        "scoreboard retains the instrument void")
    add(checks, "m2", "m2.adverse-residual",
        ncount(after, "`1.515208x`") == 4,
        f"adverse residual occurrences={ncount(after, '`1.515208x`')}")
    add(checks, "m2", "m2.zero-of-twelve",
        ncount(after, "`0 of 12`") == 3,
        f"zero-of-twelve occurrences={ncount(after, '`0 of 12`')}")
    add(checks, "m2", "m2.blur-reward",
        ncount(after, "`0.571215x`") == 4,
        f"blur-reward occurrences={ncount(after, '`0.571215x`')}")
    add(checks, "m2", "m2.product-native-diagnostic",
        ncount(after.lower(), "product-native diagnostic") >= 2
        and contains(m2, "product-native DELIVER-V6 diagnostic"),
        "adverse reading is scoped to the product-native track")
    add(checks, "m2", "m2.current-unmeasured",
        contains(m2,
                 "M2 remains `UNMEASURED` until a replacement instrument is "
                 "independently commissioned."),
        "the rename creates no pass")
    add(checks, "m2", "m2.no-detail-claim",
        contains(m2,
                 "licenses only its stated flat/defocused-ground noise claim, "
                 "never a detail claim."),
        "M2 licenses no detail claim")
    add(checks, "m2", "m2.natural-detail-98-retained",
        contains(m2,
                 "only modes within `98%` of a future replacement-M1 information "
                 "envelope"),
        "the existing natural-detail qualification remains")
    add(checks, "m2", "m2.featureless-route-narrow",
        contains(m2,
                 "pre-registered, input-certified featureless or deliberately "
                 "defocused target whose scope makes no photographic-detail claim"),
        "the M1-independent route is narrowly scoped")
    add(checks, "m2", "m2.no-current-route",
        contains(m2,
                 "No such instrument or qualifying common-merge comparator output "
                 "exists today."),
        "the narrow route does not create current evidence")

    # Non-weakening and byte-based before/after scope checks.
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

    before_fail_rows = sorted(
        line for line in before.splitlines()
        if line.startswith("| M") and "**FAIL**" in line
    )
    after_fail_rows = sorted(
        line for line in after.splitlines()
        if line.startswith("| M") and "**FAIL**" in line
    )
    add(checks, "integrity", "integrity.fail-rows-preserved",
        before_fail_rows == after_fail_rows,
        f"before={len(before_fail_rows)} after={len(after_fail_rows)}")

    m8_row = metric_row(after_sections.get("6", ""), "M8", 0)
    add(checks, "integrity", "integrity.m8-fail",
        "**FAIL**" in m8_row,
        "M8 remains FAIL")
    add(checks, "integrity", "integrity.m8-r",
        "`1.030569%`" in m8_row,
        "M8-R remains 1.030569%")
    add(checks, "integrity", "integrity.m8-o",
        "`1.326144%`" in m8_row,
        "M8-O remains 1.326144%")
    add(checks, "integrity", "integrity.m8-zero-bar",
        "exactly `0.0000%`" in m8_row,
        "M8's exact zero bar remains")

    for metric in [f"M{number}" for number in range(1, 13)]:
        before_row = metric_row(before_sections.get("3", ""), metric, 0)
        after_row = metric_row(after_sections.get("3", ""), metric, 0)
        ok, missing = counter_subset(
            numeric_tokens(before_row), numeric_tokens(after_row)
        )
        add(checks, "integrity", f"integrity.{metric.lower()}-glance-numbers",
            bool(before_row and after_row and ok),
            "preserved" if ok else f"missing={','.join(missing)}")

        before_success = success_block(metric_card(before, metric))
        after_success = success_block(metric_card(after, metric))
        ok, missing = counter_subset(
            numeric_tokens(before_success), numeric_tokens(after_success)
        )
        add(checks, "integrity", f"integrity.{metric.lower()}-success-numbers",
            bool(before_success and after_success and ok),
            "preserved" if ok else f"missing={','.join(missing)}")

    add(checks, "integrity", "integrity.gate-set",
        contains(decision,
                 "The publication gates are exactly `M1`, `M2`, `M3`, `M8`, "
                 "`M9`, `M10`, and `M11`"),
        "the accepted seven-axis gate set remains")
    add(checks, "integrity", "integrity.disclosure-set",
        contains(decision,
                 "`M4`, `M5`, `M6`, `M7`, and `M12` are mandatory disclosures, "
                 "not independent publication gates"),
        "the accepted disclosure set remains")
    add(checks, "integrity", "integrity.comparator-set",
        contains(decision,
                 "The required set is exactly licensed Zerene Stacker PMax, "
                 "licensed Zerene Stacker DMap, and the fork at its frozen "
                 "best-known build."),
        "required comparator set remains")
    add(checks, "integrity", "integrity.disclosure-miss",
        contains(publication,
                 "`DISCLOSURE MISS — owner's seven-axis SOTA claim supported`"),
        "third verdict remains")

    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-rev", default=BASE_REV)
    parser.add_argument("--after-rev", default=RECONCILED_REV)
    parser.add_argument("--scorecard", type=Path)
    args = parser.parse_args()

    try:
        before = git_blob(args.before_rev)
        after = (
            read_utf8(args.scorecard.resolve())
            if args.scorecard
            else git_blob(args.after_rev)
        )
        checks = run_checks(after, before, read_utf8(M158), read_utf8(M159))
    except (OSError, UnicodeDecodeError, RuntimeError) as exc:
        emit(f"ERROR {exc}")
        return 2

    group_counts: dict[str, list[int]] = {}
    for check in checks:
        label = "PASS" if check.passed else "FAIL"
        emit(f"{label} {check.name}: {check.detail}")
        counts = group_counts.setdefault(check.group, [0, 0])
        counts[0] += int(check.passed)
        counts[1] += int(not check.passed)

    for group in sorted(group_counts):
        passed, failed = group_counts[group]
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
