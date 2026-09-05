#!/usr/bin/env python3
"""Fail-closed verifier and commissioning harness for M177's capture programme."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORT_PATH = ROOT / "docs" / "research" / "M177-capture-programme.md"
ALLOWED_CAPTURE = Path(
    r"D:\personal\macro\requests\misc-diagnostic\high-res-calibration-slide-cpl"
)
FORBIDDEN_CAPTURE_TEXT = (
    r"d:\personal\macro\requests\7-aperture-pairs".replace("/", "\\").casefold()
)

SOURCE_PATHS = {
    "m166_cost": ROOT / "docs" / "research" / "M166-rehearsal-cost.md",
    "m166_reconcile": ROOT / "docs" / "research" / "M166-capture-reconciliation.md",
    "m166_rehearsal": ROOT
    / "docs"
    / "research"
    / "M166-reference-dominance-rehearsal.md",
    "m167": ROOT / "docs" / "research" / "M167-detail-battery.md",
    "m146": ROOT / "docs" / "research" / "M146-unlock-audit.md",
    "m152": ROOT / "docs" / "research" / "M152-site-census.md",
    "m154": ROOT / "docs" / "research" / "M154-m10-angle.md",
    "m160": ROOT / "docs" / "research" / "M160-amendment6-reachability.md",
    "m144": ROOT / "docs" / "research" / "M144-reference-uncertainty.md",
    "m169": ROOT / "docs" / "research" / "M169-ratification-stakes.md",
    "owner": ROOT / "docs" / "OWNER-ACTIONS.md",
    "capture": ROOT
    / "docs"
    / "capture-requests"
    / "2026-09-319-frame-session.md",
}

LABELS = ("**VERIFIED BY RUNNING.**", "**INFERRED BY READING.**")


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class Survey:
    count: int
    groups: dict[str, int]
    tags: dict[str, set[str]]


def comma_int(value: str) -> int:
    return int(value.replace(",", "").replace(" ", ""))


def unique_match(pattern: str, text: str, label: str, flags: int = 0) -> re.Match[str]:
    matches = list(re.finditer(pattern, text, flags))
    if len(matches) != 1:
        raise ValueError(f"{label}: expected one match, found {len(matches)}")
    return matches[0]


def unique_int(pattern: str, text: str, label: str, flags: int = 0) -> int:
    return comma_int(unique_match(pattern, text, label, flags).group(1))


def contains_once(text: str, needle: str) -> bool:
    return text.count(needle) == 1


def load_sources() -> dict[str, str]:
    loaded: dict[str, str] = {}
    for name, path in SOURCE_PATHS.items():
        loaded[name] = path.read_text(encoding="utf-8")
    return loaded


def survey_allowed_capture() -> Survey:
    # Resolve only the explicitly allowed subtree. Never probe its parent or sibling.
    root = ALLOWED_CAPTURE.resolve(strict=True)
    folded = str(root).replace("/", "\\").casefold()
    if FORBIDDEN_CAPTURE_TEXT in folded:
        raise RuntimeError("safety guard: allowed survey path resolves inside holdout")
    expected_suffix = (
        r"\requests\misc-diagnostic\high-res-calibration-slide-cpl".casefold()
    )
    if not folded.endswith(expected_suffix):
        raise RuntimeError(f"safety guard: unexpected survey root {root}")

    files = sorted(
        (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".arw"),
        key=lambda path: str(path).casefold(),
    )
    groups: dict[str, int] = {}
    for path in files:
        relative_parent = str(path.parent.relative_to(root)).replace("/", "\\")
        groups[relative_parent] = groups.get(relative_parent, 0) + 1

    executable = shutil.which("exiftool")
    if executable is None:
        raise RuntimeError("ExifTool not found")
    command = [
        executable,
        "-json",
        "-n",
        "-Model",
        "-LensModel",
        "-FocalLength",
        "-ISO",
        "-FNumber",
        "-ImageWidth",
        "-ImageHeight",
        "-ImageStabilization",
        "-r",
        "-ext",
        "ARW",
        str(root),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ExifTool failed with {completed.returncode}: {completed.stderr[-1000:]}"
        )
    rows = json.loads(completed.stdout)
    tags: dict[str, set[str]] = {}
    for tag in (
        "Model",
        "LensModel",
        "FocalLength",
        "ISO",
        "FNumber",
        "ImageWidth",
        "ImageHeight",
        "ImageStabilization",
    ):
        tags[tag] = {str(row.get(tag)) for row in rows}
    if len(rows) != len(files):
        raise RuntimeError(
            f"header/file mismatch: {len(rows)} headers for {len(files)} files"
        )
    return Survey(count=len(files), groups=groups, tags=tags)


def derive(sources: dict[str, str]) -> dict[str, object]:
    reconcile = sources["m166_reconcile"]
    rehearsal_match = unique_match(
        r"(?m)^([\d,]+) - ([\d,]+) \+ ([\d,]+) \+ ([\d,]+) = ([\d,]+)$",
        reconcile,
        "reconciled rehearsal bridge",
    )
    rehearsal_bridge = [comma_int(group) for group in rehearsal_match.groups()]
    rehearsal_parts = rehearsal_bridge[:4]
    rehearsal_total = (
        rehearsal_parts[0]
        - rehearsal_parts[1]
        + rehearsal_parts[2]
        + rehearsal_parts[3]
    )
    if rehearsal_total != rehearsal_bridge[4]:
        raise ValueError(
            "reconciled rehearsal bridge arithmetic disagrees with its stated total"
        )

    m1_score = unique_int(
        r"current M1-only scored sitting\s+([\d,]+)",
        reconcile,
        "reconciled M1-only score",
    )
    m5_m9 = unique_int(
        r"named decision: defer the ([\d,]+)-frame M5/M9 converter-on package",
        reconcile,
        "reconciled M5/M9 package",
    )
    score_parts = [m1_score, m5_m9]
    score_total = sum(score_parts)
    headline = unique_match(
        r"RECONCILED: rehearsal ([\d,]+), scored ([\d,]+), total ([\d,]+)",
        reconcile,
        "reconciliation headline",
    )
    headline_totals = [comma_int(group) for group in headline.groups()]
    if headline_totals != [rehearsal_total, score_total, rehearsal_total + score_total]:
        raise ValueError(
            f"reconciliation headline disagrees with bridges: {headline_totals}"
        )

    m167 = sources["m167"]
    m167_patterns = (
        r"\| `TR-REF-NEAR/MID/FAR` .+?\| 3 bursts, ([\d,]+) frames \|",
        r"\| `TEST-sw4-A/B` .+?\| 2 complete stacks, ([\d,]+) frames \|",
        r"\| `TEST-sw10-A/B` .+?\| 2 complete stacks, ([\d,]+) frames \|",
        r"\| reset/start/end witnesses .+?\| 10 bursts, ([\d,]+) frames \|",
        r"\| `NULL-sw4-A/B` .+?\| 2 complete stacks, ([\d,]+) frames \|",
        r"\| reference calibration .+?\| 4 groups, ([\d,]+) frames \|",
        r"\| test calibration .+?\| 4 groups, ([\d,]+) frames \|",
    )
    m167_parts = [
        unique_int(pattern, m167, f"M167 part {index}")
        for index, pattern in enumerate(m167_patterns, start=1)
    ]

    m2_group = unique_int(
        r"two fixed-focus, ISO-100, ([\d,]+)-frame bee blocks",
        sources["m146"],
        "M2 group",
    )

    ask5_match = unique_match(
        r"frames across `tilted-sw4` \(([\d,]+)\), `tilted-sw10` \(([\d,]+)\), "
        r"`flat-sw4` \(([\d,]+)\) and\s+`very-tilted-all-axis-sw10` \(([\d,]+)\)",
        sources["owner"],
        "Ask 5 components",
    )
    ask5_parts = [comma_int(group) for group in ask5_match.groups()]

    diagnostic_names = (
        "flat-sw4-cpl/flat-et6s-sw4-cpl",
        "flat-sw4-cpl/flat-et2.5s-sw4-cpl",
        "flat-sw4-cpl/flat-et1s-sw4-cpl",
        "tilted-sw4-cpl",
        "tilted-sw10-cpl",
        "very-tilted-all-axis-sw10-cpl",
    )
    diagnostic_parts = [
        unique_int(
            rf"\| `{re.escape(name)}` \| ([\d,]+) \|",
            m167,
            f"diagnostic {name}",
        )
        for name in diagnostic_names
    ]

    preflight = unique_int(
        r"two-frame scale/field preflight, outside both sittings\s+([\d,]+)",
        sources["m166_reconcile"],
        "preflight",
    )
    zero_axes = unique_int(
        r"\| Axes that become newly scoreable \| \*\*([\d,]+) of 12\*\* \| none \|",
        sources["m169"],
        "M169 zero axes",
    )

    m167_total = sum(m167_parts)
    m2_total = 2 * m2_group
    ask5_total = sum(ask5_parts)
    specified_floor = (
        preflight + rehearsal_total + score_total + m167_total + m2_total + ask5_total
    )
    return {
        "rehearsal_parts": rehearsal_parts,
        "rehearsal_total": rehearsal_total,
        "score_parts": score_parts,
        "score_total": score_total,
        "m167_parts": m167_parts,
        "m167_total": m167_total,
        "m2_group": m2_group,
        "m2_total": m2_total,
        "ask5_parts": ask5_parts,
        "ask5_total": ask5_total,
        "diagnostic_parts": diagnostic_parts,
        "diagnostic_total": sum(diagnostic_parts),
        "preflight": preflight,
        "core_three": rehearsal_total + score_total + m167_total,
        "landed_campaigns": preflight + rehearsal_total + score_total + m167_total,
        "score_path": preflight + rehearsal_total + score_total,
        "specified_floor": specified_floor,
        "post_cut": specified_floor - m167_total,
        "budget_remainder": 300 - preflight,
        "zero_axes": zero_axes,
        "rehearsal_bracket": 164 + 164,
        "rehearsal_fixed": rehearsal_total - 328,
        "score_bracket": 255 + 164 + 164,
        "score_fixed": score_total - 583,
        "m167_bracket": m167_parts[1] + m167_parts[2] + m167_parts[4],
        "m167_fixed": m167_total
        - (m167_parts[1] + m167_parts[2] + m167_parts[4]),
    }


def check_labels(report: str) -> tuple[bool, str]:
    if any(report.count(label) < 10 for label in LABELS):
        return False, "too few explicit evidence labels"
    in_fence = False
    bad_rows: list[int] = []
    for number, line in enumerate(report.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not stripped.startswith("|"):
            continue
        if re.fullmatch(r"\|?[\s:|-]+\|?", stripped):
            continue
        if "Evidence" in stripped:
            continue
        if not any(label in line for label in LABELS):
            bad_rows.append(number)
    return (not bad_rows, f"unlabelled table rows={bad_rows[:12]}")


def audit(
    report: str,
    sources: dict[str, str],
    survey: Survey,
) -> list[Check]:
    checks: list[Check] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(Check(name, bool(passed), detail))

    try:
        facts = derive(sources)
    except Exception as exc:  # fail closed on source drift
        return [Check("source.derivation", False, str(exc))]

    add(
        "arithmetic.rehearsal",
        facts["rehearsal_total"] == 1092
        and contains_once(
            report,
            "CHECK[rehearsal] 896 - 96 + 128 + 164 = 1,092",
        ),
        str(facts["rehearsal_parts"]),
    )
    add(
        "arithmetic.score",
        facts["score_total"] == 1215
        and contains_once(
            report,
            "CHECK[score] 900 + 315 = 1,215",
        ),
        str(facts["score_parts"]),
    )
    add(
        "arithmetic.core-three",
        facts["core_three"] == 2993
        and contains_once(
            report, "CHECK[core-three] 1,092 + 1,215 + 686 = 2,993"
        ),
        str(facts["core_three"]),
    )
    add(
        "arithmetic.landed-campaigns",
        facts["landed_campaigns"] == 2995
        and contains_once(
            report,
            "CHECK[landed-campaigns] 2 + 1,092 + 1,215 + 686 = 2,995",
        ),
        str(facts["landed_campaigns"]),
    )
    add(
        "arithmetic.m167",
        facts["m167_total"] == 686
        and contains_once(
            report,
            "CHECK[m167] 96 + 110 + 54 + 60 + 110 + 128 + 128 = 686",
        ),
        str(facts["m167_parts"]),
    )
    add(
        "arithmetic.m2",
        facts["m2_total"] == 64
        and contains_once(report, "CHECK[m2] 2 x 32 = 64"),
        str(facts["m2_total"]),
    )
    add(
        "arithmetic.ask5",
        facts["ask5_total"] == 657
        and facts["diagnostic_parts"][:3] == [65, 61, 60]
        and contains_once(
            report, "CHECK[ask5] 182 + 92 + (65 + 61 + 60) + 197 = 657"
        ),
        f"ask5={facts['ask5_parts']}, diagnostic={facts['diagnostic_parts']}",
    )
    add(
        "arithmetic.specified-floor",
        facts["specified_floor"] == 3716
        and contains_once(
            report,
            "CHECK[specified-floor] 2 + 1,092 + 1,215 + 686 + 64 + 657 = 3,716",
        ),
        str(facts["specified_floor"]),
    )
    add(
        "arithmetic.score-path",
        facts["score_path"] == 2309
        and contains_once(
            report, "CHECK[score-path] 2 + 1,092 + 1,215 = 2,309"
        ),
        str(facts["score_path"]),
    )
    add(
        "arithmetic.post-cut",
        facts["post_cut"] == 3030
        and contains_once(report, "CHECK[post-cut] 3,716 - 686 = 3,030"),
        str(facts["post_cut"]),
    )
    add(
        "arithmetic.budget",
        facts["budget_remainder"] == 298
        and contains_once(report, "CHECK[budget-300] 300 - 2 = 298"),
        str(facts["budget_remainder"]),
    )
    add(
        "structure.rehearsal",
        facts["rehearsal_bracket"] == 328
        and facts["rehearsal_fixed"] == 764
        and contains_once(
            report,
            "CHECK[rehearsal-structure] bracket 164 + 164 = 328; "
            "fixed 1,092 - 328 = 764; stacks 4 + 4 = 8",
        ),
        f"{facts['rehearsal_bracket']}/{facts['rehearsal_fixed']}",
    )
    add(
        "structure.score",
        facts["score_bracket"] == 583
        and facts["score_fixed"] == 632
        and contains_once(
            report,
            "CHECK[score-structure] bracket 255 + 164 + 164 = 583; "
            "fixed 1,215 - 583 = 632; stacks 5 + 4 + 4 = 13",
        ),
        f"{facts['score_bracket']}/{facts['score_fixed']}",
    )
    add(
        "structure.m167-correction",
        facts["m167_bracket"] == 274
        and facts["m167_fixed"] == 412
        and contains_once(
            report, "CHECK[m167-structure] bracket 110 + 54 + 110 = 274"
        )
        and "M167's\nthree bracket rows total `274`, not `328`" in report,
        f"{facts['m167_bracket']}/{facts['m167_fixed']}",
    )
    expected_groups = {
        r"flat-sw4-cpl\flat-et1s-sw4-cpl": 60,
        r"flat-sw4-cpl\flat-et2.5s-sw4-cpl": 61,
        r"flat-sw4-cpl\flat-et6s-sw4-cpl": 65,
        "tilted-sw10-cpl": 92,
        "tilted-sw4-cpl": 182,
        "very-tilted-all-axis-sw10-cpl": 197,
    }
    add(
        "survey.files",
        survey.count == 657
        and survey.groups == expected_groups
        and facts["diagnostic_total"] == 657
        and contains_once(
            report, "CHECK[survey] 65 + 61 + 60 + 182 + 92 + 197 = 657"
        ),
        f"count={survey.count}, groups={survey.groups}",
    )
    expected_tags = {
        "Model": {"ILCE-7CM2"},
        "LensModel": {"FE 100mm F2.8 Macro GM OSS + 2X Teleconverter"},
        "FocalLength": {"200"},
        "ISO": {"100"},
        "FNumber": {"5.6"},
        "ImageWidth": {"7168"},
        "ImageHeight": {"5120"},
        "ImageStabilization": {"1"},
    }
    add(
        "survey.headers",
        survey.tags == expected_tags
        and contains_once(
            report,
            "CHECK[survey-groups] 6 runs; 657 headers; stabilisation-on = 657",
        ),
        str(survey.tags),
    )
    add(
        "dedup.m166-two-164",
        "Equal budgets do not make the files interchangeable." in sources["m166_cost"]
        and "DOM RAWs are candidate-excluded witnesses; candidate RAWs are renderer inputs"
        in report,
        "candidate and witness lineages remain distinct",
    )
    add(
        "dedup.session-separation",
        "shares zero RAWs, calibration" in sources["m166_cost"]
        and "There is **no legitimate cross-request RAW merge**" in report,
        "development/holdout separation",
    )
    add(
        "dedup.m167-condition",
        "Do not duplicate it if the already planned M1 non-holdout rehearsal"
        in sources["m167"]
        and "M167 fixes `M_test <= 1.30x`, ABBA order" in report
        and "M166 fixes the accepted `1.32x` placement" in report,
        "conditional same-block clause checked against acquisition laws",
    )
    add(
        "dedup.optical-state-correction",
        "| `TC0-DOM-sw4-A/B` | converter off |" in sources["m166_rehearsal"]
        and "| `TC0-DOM-sw10-A/B` | converter off |" in sources["m166_rehearsal"]
        and "| `TEST-sw4-A/B` | teleconverter removed," in sources["m167"]
        and "M166 registers both `TC0-DOM` blocks as\n**converter off**" in report
        and "No 164-frame merge is credited." in report,
        "both packages are converter-off but differ in magnification and role",
    )
    add(
        "axes.zero-newly-scoreable",
        facts["zero_axes"] == 0
        and contains_once(
            report,
            "CHECK[axes-zero] comparator relaxation -> 0 of 12 newly scoreable",
        ),
        str(facts["zero_axes"]),
    )
    add(
        "cut.m167",
        "NO DEPLOYABLE DETAIL INSTRUMENT ADMITTED" in sources["m167"]
        and "Cut all 686 M167 frames from the owner queue." in report
        and "686 frames cut as unblocking nothing" in report.splitlines()[0],
        "M167 has diagnostic, not scorecard-axis, licence",
    )
    add(
        "rig.impossible-paired-node",
        "It cannot expose A and B back-to-back at one node before" in sources["capture"]
        and "The superseded 383-frame paired-node proposal is\nimpossible" in report,
        "standing equipment constraint",
    )
    add(
        "rig.whole-pass-substitute",
        "whole-pass sequence below replaces every earlier" in sources["capture"]
        and "one complete automated\n+pass for A followed" not in report
        and "one complete automated\npass for A followed" in report,
        "sequential complete-pass substitute",
    )
    add(
        "inventory.unsized",
        "a fresh untouched medication-pill" in sources["m152"]
        and "A fresh registered ruler unit is required." in sources["m154"]
        and "Acquire fresh controlled highlight/shadow stacks" in sources["m160"]
        and "M7 presently has no target capture." in sources["m144"]
        and "Current but unsized asks" in report,
        "four unsized asks remain outside finite total",
    )
    add(
        "report.no-duration-promises",
        not re.search(r"\b(minutes?|hours?|wall-clock|duration estimate)\b", report, re.I),
        "no quarantined sitting-duration claim",
    )
    labels_ok, labels_detail = check_labels(report)
    add("report.labels", labels_ok, labels_detail)
    add(
        "report.commission-record",
        contains_once(
            report,
            "CHECK[commission] planted defects caught = 13; missed = 0; "
            "inert edits passed = 1 of 1",
        ),
        "commission record anchor",
    )
    return checks


def mutate_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"{label}: mutation anchor count is {count}, expected 1")
    return text.replace(old, new, 1)


def commissioned(
    report: str, sources: dict[str, str], survey: Survey
) -> tuple[int, int, int, int]:
    defects: list[
        tuple[str, Callable[[str, dict[str, str]], tuple[str, dict[str, str]]]]
    ] = []

    def report_mutation(name: str, old: str, new: str) -> None:
        def apply(
            current_report: str, current_sources: dict[str, str]
        ) -> tuple[str, dict[str, str]]:
            return mutate_once(current_report, old, new, name), current_sources

        defects.append((name, apply))

    def source_mutation(name: str, source: str, old: str, new: str) -> None:
        def apply(
            current_report: str, current_sources: dict[str, str]
        ) -> tuple[str, dict[str, str]]:
            changed = dict(current_sources)
            changed[source] = mutate_once(changed[source], old, new, name)
            return current_report, changed

        defects.append((name, apply))

    report_mutation(
        "report-grand-total",
        "CHECK[specified-floor] 2 + 1,092 + 1,215 + 686 + 64 + 657 = 3,716",
        "CHECK[specified-floor] 2 + 1,092 + 1,215 + 686 + 64 + 657 = 3,715",
    )
    source_mutation(
        "m166-rehearsal-source",
        "m166_reconcile",
        "896 - 96 + 128 + 164 = 1,092",
        "895 - 96 + 128 + 164 = 1,092",
    )
    source_mutation(
        "m166-score-source",
        "m166_reconcile",
        "named decision: defer the 315-frame M5/M9 converter-on package",
        "named decision: defer the 314-frame M5/M9 converter-on package",
    )
    source_mutation(
        "m167-null-source",
        "m167",
        "| 2 complete stacks, 110 frames | Supplies a physical no-scene-detail",
        "| 2 complete stacks, 109 frames | Supplies a physical no-scene-detail",
    )
    source_mutation(
        "m2-group-source",
        "m146",
        "two fixed-focus, ISO-100, 32-frame bee blocks",
        "two fixed-focus, ISO-100, 31-frame bee blocks",
    )
    source_mutation(
        "ask5-source",
        "owner",
        "`flat-sw4` (186) and",
        "`flat-sw4` (185) and",
    )
    report_mutation(
        "report-cut-total",
        "CHECK[post-cut] 3,716 - 686 = 3,030",
        "CHECK[post-cut] 3,716 - 685 = 3,031",
    )
    report_mutation(
        "dedup-role-collapse",
        "DOM RAWs are candidate-excluded witnesses; candidate RAWs are renderer inputs",
        "DOM RAWs and candidate RAWs are interchangeable renderer inputs",
    )
    report_mutation(
        "m167-magnification-collapse",
        "M167 fixes `M_test <= 1.30x`, ABBA order",
        "M167 fixes `M_test <= 1.32x`, any order",
    )
    report_mutation(
        "m166-dom-optical-state-collapse",
        "M166 registers both `TC0-DOM` blocks as\n**converter off**",
        "M166 registers both `TC0-DOM` blocks as\n**converter on**",
    )
    source_mutation(
        "m169-zero-axis-source",
        "m169",
        "| Axes that become newly scoreable | **0 of 12** | none |",
        "| Axes that become newly scoreable | **1 of 12** | M3 |",
    )
    report_mutation(
        "paired-node-made-possible",
        "The superseded 383-frame paired-node proposal is\nimpossible",
        "The superseded 383-frame paired-node proposal is\npossible",
    )
    report_mutation(
        "whole-pass-substitute-removed",
        "one complete automated\npass for A followed",
        "one interleaved per-node\npass for A followed",
    )

    caught = 0
    missed = 0
    for name, mutation in defects:
        mutated_report, mutated_sources = mutation(report, dict(sources))
        result = audit(mutated_report, mutated_sources, survey)
        if result and all(check.passed for check in result):
            missed += 1
            print(f"MISS planted defect: {name}")
        else:
            caught += 1
            failed = ", ".join(check.name for check in result if not check.passed)
            print(f"CAUGHT planted defect: {name} -> {failed}")

    inert_report = report + "\n<!-- M177 inert commissioning edit -->\n"
    inert_result = audit(inert_report, dict(sources), survey)
    inert_passed = int(bool(inert_result) and all(check.passed for check in inert_result))
    inert_total = 1
    if not inert_passed:
        failed = ", ".join(check.name for check in inert_result if not check.passed)
        print(f"INERT EDIT FALSE RED -> {failed}")
    return caught, missed, inert_passed, inert_total


def print_checks(checks: list[Check]) -> bool:
    for check in checks:
        state = "PASS" if check.passed else "FAIL"
        print(f"{state} {check.name}: {check.detail}")
    passed = sum(check.passed for check in checks)
    print(f"{'PASS' if passed == len(checks) else 'FAIL'}: {passed}/{len(checks)} checks")
    return passed == len(checks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commission",
        action="store_true",
        help="plant source/report defects and one inert edit in memory",
    )
    args = parser.parse_args()

    try:
        report = REPORT_PATH.read_text(encoding="utf-8")
        sources = load_sources()
        survey = survey_allowed_capture()
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    checks = audit(report, sources, survey)
    if not print_checks(checks):
        return 1
    if not args.commission:
        return 0

    try:
        caught, missed, inert_passed, inert_total = commissioned(
            report, sources, survey
        )
    except Exception as exc:
        print(f"ERROR commissioning: {exc}")
        return 2
    print(
        f"COMMISSIONED: {caught} caught, {missed} missed; "
        f"inert {inert_passed}/{inert_total} passed"
    )
    return 0 if caught == 13 and missed == 0 and inert_passed == inert_total else 1


if __name__ == "__main__":
    sys.exit(main())
