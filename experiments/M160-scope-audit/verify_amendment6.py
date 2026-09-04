#!/usr/bin/env python3
"""Verify the Amendment 6 reconciliation by content, never by live line number.

Human quotations are compared after stripping Markdown blockquote prefixes from
each physical line and then collapsing whitespace. This preserves multiline
quotations and avoids the known bug where stripping ``>`` only after joining
leaves false mismatches. Bar preservation is checked against the committed
v1.8 scorecard blob, and every metric row is required to have one unique anchor.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "docs/proposals/2026-08-sota-path.md"
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
REPORT = ROOT / "docs/research/M160-amendment6-reachability.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
BASE_REV = "1549df47"
PLAN_SHA256 = "D7AD61E0E9B37D0C761810620EE0F296C9E8DC188509E1E860CBA44D9FA905F5"
EVIDENCE_PATHS = {
    "m152": ROOT / "docs/research/M152-site-census.md",
    "m164_m2": ROOT / "docs/research/M164-m2-repair.md",
    "m166_m10": ROOT / "docs/research/M166-m10-definition-repair.md",
    "m167": ROOT / "docs/research/M167-detail-battery.md",
    "m167_admission": ROOT
    / "experiments/M167-detail-battery/ADMISSION-PREREGISTRATION.md",
    "m168": ROOT / "docs/research/M168-cheap-reference-feasibility.md",
    "status": ROOT / "docs/STATUS.md",
    "capture": ROOT / "docs/capture-requests/2026-09-319-frame-session.md",
    "owner": ROOT / "docs/OWNER-ACTIONS.md",
}


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


def normalise(text: str) -> str:
    lines = [re.sub(r"^\s*>\s?", "", line) for line in text.splitlines()]
    collapsed = re.sub(r"\s+", " ", "\n".join(lines)).strip()
    return collapsed.replace("**", "").replace("*", "").replace("`", "")


def contains(text: str, phrase: str) -> bool:
    return normalise(phrase) in normalise(text)


def ncount(text: str, phrase: str) -> int:
    return normalise(text).count(normalise(phrase))


def line_range(text: str, start: int, end: int) -> str:
    return "\n".join(text.splitlines()[start - 1 : end])


def top_section(text: str, number: int) -> str:
    match = re.search(rf"(?m)^## {number}\. .+$", text)
    if not match:
        return ""
    following = re.search(r"(?m)^## \d+\. ", text[match.end() :])
    end = match.end() + following.start() if following else len(text)
    return text[match.start() : end]


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


def metric_rows(text: str, metric: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if re.match(rf"^\| {re.escape(metric)} \|", line)
    ]


def add(
    checks: list[Check], group: str, name: str, passed: bool, detail: str
) -> None:
    checks.append(Check(group, name, passed, detail))


def run_checks(
    plan: str,
    scorecard: str,
    report: str,
    base: str,
    plan_bytes: bytes,
    evidence: dict[str, str],
) -> list[Check]:
    checks: list[Check] = []
    amendment = top_section(plan, 16)
    m1 = metric_card(scorecard, "M1")
    m2 = metric_card(scorecard, "M2")
    m9 = metric_card(scorecard, "M9")
    results = top_section(scorecard, 6)

    source_checks = (
        (
            "source.plan-hash",
            hashlib.sha256(plan_bytes).hexdigest().upper() == PLAN_SHA256,
            f"sha256={hashlib.sha256(plan_bytes).hexdigest().upper()}",
        ),
        (
            "source.amendment-unique",
            scorecard.count("## 16. Amendment 6") == 0
            and plan.count("## 16. Amendment 6") == 1,
            f"plan headings={plan.count('## 16. Amendment 6')}",
        ),
        (
            "source.hedge",
            contains(
                amendment,
                "without an assumption or observation outside those outputs",
            ),
            "load-bearing hedge present",
        ),
        (
            "source.no-universal",
            contains(
                amendment,
                "This does not prove that every no-reference metric is impossible",
            ),
            "universal impossibility expressly rejected",
        ),
        (
            "source.mechanisms-distinct",
            contains(amendment, "are not all instances of one theorem")
            and contains(amendment, "common-filter invariance is a separate algebraic fact")
            and contains(amendment, "band-power flat-null failure is empirical")
            and contains(amendment, "only M2's is the identifiability construction"),
            "three proof statuses present",
        ),
        (
            "source.capture-precondition",
            contains(amendment, "Capture is therefore a precondition of the instrument")
            and contains(amendment, "not a way around it"),
            "capture framing present",
        ),
        (
            "source.m1-not-unique",
            contains(
                amendment,
                "M1 is the current proposed implementation of that condition, not "
                "the only mathematically possible one",
            ),
            "non-uniqueness present",
        ),
        (
            "source.m1-current-route",
            contains(amendment, "M1 remains the only route with a path to an admissible result"),
            "current practical route retained",
        ),
    )
    for name, passed, detail in source_checks:
        add(checks, "source", name, passed, detail)

    evidence_checks = (
        (
            "evidence.m152",
            contains(evidence["m152"], "M3 has enough existing input capture")
            and contains(
                evidence["m152"],
                "medication pill 55, exact bee background 123, foam 0",
            )
            and contains(evidence["m152"], "existing M4 corpus selects only 138"),
            "M3 sufficiency and M4 deficit match M152",
        ),
        (
            "evidence.m164-m2",
            contains(evidence["m164_m2"], "This is not an accepted M2 instrument")
            and contains(evidence["m164_m2"], "M2 therefore remains `UNMEASURED`"),
            "Q_EIN remains development-only",
        ),
        (
            "evidence.m166-m10",
            contains(
                evidence["m166_m10"],
                "the definition is closed; execution remains UNMEASURED — "
                "MISSING PHYSICAL TRUTH AND PRODUCT",
            )
            and contains(
                evidence["m166_m10"],
                "Strehl emits none of the three required planes today",
            ),
            "M10 definition and product blocker match M166",
        ),
        (
            "evidence.m167",
            contains(evidence["m167"], "NO DEPLOYABLE DETAIL INSTRUMENT ADMITTED")
            and contains(evidence["m167"], "all `15` hard commissioning checks are true"),
            "detail battery is live but admits no candidate",
        ),
        (
            "evidence.m167-admission",
            contains(
                evidence["m167_admission"],
                "FROZEN BEFORE THE ARM-IDENTITY CANARY IS EXECUTED",
            )
            and contains(
                evidence["m167_admission"],
                "If that facility is absent, the result is "
                "`REFUSED_SANDBOX_UNAVAILABLE`, never a pass",
            ),
            "blinded admission is frozen and fail-closed on sandbox absence",
        ),
        (
            "evidence.m168",
            contains(evidence["m168"], "NO ARCHIVE-ONLY ROUTE")
            and contains(
                evidence["m168"],
                "archive-only same-resolution route cannot be physically commissioned today",
            ),
            "archive-only reference route is absent",
        ),
        (
            "evidence.status",
            contains(
                evidence["status"],
                "salt `1,193`, battery `1,230`, angled ruler/grid `0`",
            )
            and contains(
                evidence["status"],
                "M12-D, fixed-worker determinism -- diagnostic PASS",
            )
            and contains(
                evidence["status"],
                "M12-S, cross-worker scaling invariance -- diagnostic FAIL",
            ),
            "M6 and M12 documentary states match",
        ),
        (
            "evidence.capture",
            contains(evidence["capture"], "THIS DOCUMENT IS NOT SAFE TO SHOOT FROM")
            and contains(
                evidence["capture"],
                "fresh nonperiodic patch, coplanar with the grid",
            ),
            "combined M1/M5/M9 capture remains blocked",
        ),
        (
            "evidence.owner",
            contains(evidence["owner"], "buy Zerene Professional, $289")
            and contains(evidence["owner"], "ISA ColorGauge Nano")
            and contains(evidence["owner"], "Sekonic C-800 illuminant meter"),
            "owner-controlled M7/comparator purchases are named",
        ),
    )
    for name, passed, detail in evidence_checks:
        add(checks, "evidence", name, passed, detail)

    scorecard_checks = (
        (
            "scorecard.version",
            scorecard.startswith(
                "# strehl — pre-registered SOTA scorecard\n\n"
                "**Status: SPEC / PRE-REGISTRATION v1.9"
            ),
            "v1.9 status",
        ),
        (
            "scorecard.revision",
            scorecard.count("**Revision 1.9 — Amendment 6 scope correction") == 1,
            "one v1.9 revision entry",
        ),
        (
            "scorecard.no-stale-version",
            "v1.8" not in scorecard,
            f"v1.8 occurrences={scorecard.count('v1.8')}",
        ),
        (
            "scorecard.scope-hedge",
            contains(
                scorecard,
                "The operative limitation is that rendered outputs do not by "
                "themselves identify whether reduced high-frequency variation is "
                "removed noise or artifact, or removed scene signal, without an "
                "assumption or observation outside those outputs.",
            ),
            "operative limitation retains hedge",
        ),
        (
            "scorecard.no-universal",
            contains(
                scorecard,
                "That does not prove every conceivable no-reference metric impossible.",
            ),
            "no-reference claim remains qualified",
        ),
        (
            "scorecard.external-routes",
            contains(scorecard, "independently anchored signal/transfer reference")
            and contains(scorecard, "certified featureless-target protocol")
            and contains(scorecard, "validated generative prior or constraint"),
            "external information routes stated",
        ),
        (
            "scorecard.mechanisms-distinct",
            contains(scorecard, "D8 common-filter invariance is an algebraic result")
            and contains(scorecard, "band-power flat-null failure is an empirical defeat")
            and contains(scorecard, "only M2's two-output ambiguity is the identifiability construction"),
            "three failures retain separate proof status",
        ),
        (
            "scorecard.capture-precondition",
            contains(
                scorecard,
                "Capture likewise does not replace or “shoot around” an instrument: "
                "it supplies identifying information and is a precondition of the "
                "current usable instrument.",
            )
            and contains(
                m1,
                "These captures are part of the instrument's construction, not an "
                "alternative to the instrument or a way to “shoot around” it",
            ),
            "capture is an instrument precondition",
        ),
        (
            "scorecard.m1-not-unique",
            ncount(scorecard, "M1 is not the unique mathematical anchor") >= 1
            and ncount(scorecard, "not the unique mathematical anchor") >= 2,
            f"non-unique count={ncount(scorecard, 'not the unique mathematical anchor')}",
        ),
        (
            "scorecard.m1-current-route",
            contains(scorecard, "registry shorthand for the current usable route")
            and contains(scorecard, "no such archive-qualified route is admitted today"),
            "registry and practical state separated",
        ),
        (
            "scorecard.same-resolution-route",
            contains(
                scorecard,
                "A sufficiently powered independent same-resolution reference could "
                "in principle normalize relative transfer",
            ),
            "same-resolution alternative recorded",
        ),
        (
            "scorecard.m1-inventory-scoped",
            contains(
                m1,
                "Among the candidates tested in this repository under the current "
                "output-only observation contract",
            )
            and contains(m1, "not a theorem that every conceivable no-reference metric must fail"),
            "M1 inventory is empirical and scoped",
        ),
        (
            "scorecard.m2-mechanism",
            contains(m2, "The `0.571215x` blur result is an empirical defeat")
            and contains(m2, "M2's output-only ambiguity is an identifiability construction")
            and contains(m2, "This is not D8's separate common-filter algebra"),
            "M2 mechanism is separated",
        ),
        (
            "scorecard.m2-qein",
            contains(
                m2,
                "M164's external-reference `Q_EIN` candidate has author-generated "
                "synthetic evidence only",
            )
            and contains(m2, "is not an admitted M2 instrument"),
            "Q_EIN remains unadmitted",
        ),
        (
            "scorecard.m2-unmeasured",
            contains(
                m2,
                "Instrument status: INSTRUMENT VOID; current axis verdict `UNMEASURED`",
            )
            and contains(m2, "The current verdict therefore remains `UNMEASURED`"),
            "M2 remains unmeasured",
        ),
        (
            "scorecard.m9-blocked",
            contains(m9, "DEFINITION BLOCKED")
            and contains(m9, "no such route is admitted today")
            and contains(m9, "No threshold invented inside M9 may substitute for external truth"),
            "M9 remains blocked",
        ),
        (
            "scorecard.m8-fail",
            any(
                "**FAIL** — M8-R `1.030569%` against the achievable bar of exactly `0.0000%`"
                in row
                for row in metric_rows(results, "M8")
            ),
            "M8 result remains FAIL at the exact value and bar",
        ),
        (
            "scorecard.m8o-unmeasured",
            any(
                "M8-O v1.5 **UNMEASURED**" in row
                for row in metric_rows(results, "M8")
            ),
            "M8-O v1.5 remains unmeasured",
        ),
    )
    for name, passed, detail in scorecard_checks:
        add(checks, "scorecard", name, passed, detail)

    for metric_number in range(1, 13):
        metric = f"M{metric_number}"
        before_rows = metric_rows(top_section(base, 3), metric)
        after_rows = metric_rows(top_section(scorecard, 3), metric)
        before = before_rows[0] if before_rows else ""
        after = after_rows[0] if after_rows else ""
        add(
            checks,
            "bars",
            f"bars.{metric}",
            bool(before) and after == before,
            "at-a-glance success row byte-identical to v1.8",
        )

    add(
        checks,
        "report",
        "report.source-hashes",
        PLAN_SHA256 in report
        and "EF7CBB5CD740C647BDAF360DD574421449BE4F24A17D971F295531A569892CCF"
        in report,
        "both source hashes recorded",
    )
    for index, (phrase, start, end) in enumerate(
        (
            (
                "No admissible detail statistic in this repository is sharpening-safe",
                792,
                801,
            ),
            ("a blur challenge improves it to `0.571215x`", 855, 863),
            ("The capture deficiency remains", 815, 815),
            (
                "M9 remains DEFINITION BLOCKED until M1 admits an independent, "
                "higher-sampling",
                1454,
                1459,
            ),
        ),
        1,
    ):
        add(
            checks,
            "report",
            f"report.preedit-quote-{index}",
            contains(report, phrase)
            and contains(line_range(base, start, end), phrase)
            and ncount(base, phrase) == 1,
            f"{phrase} @ scorecard {start}-{end}",
        )
    for index, (report_phrase, source_phrase, start, end) in enumerate(
        (
            (
                "without additional identifying assumptions or evidence",
                "without additional identifying assumptions or evidence",
                2678,
                2693,
            ),
            (
                "The three instrument deaths ... are not all instances of one theorem",
                "The three instrument deaths in §13.5 are not all instances of one theorem",
                2701,
                2717,
            ),
            (
                "Capture is therefore a precondition of the instrument, not a way around it",
                "Capture is therefore a precondition of the instrument, not a way around it",
                2721,
                2726,
            ),
            (
                "M1 is the current proposed implementation of that condition, not the "
                "only mathematically possible one",
                "M1 is the current proposed implementation of that condition, not the "
                "only mathematically possible one",
                2690,
                2693,
            ),
        ),
        1,
    ):
        add(
            checks,
            "report",
            f"report.plan-quote-{index}",
            contains(report, report_phrase)
            and contains(line_range(plan, start, end), source_phrase)
            and ncount(plan, source_phrase) == 1,
            f"{source_phrase} @ plan {start}-{end}",
        )

    row_pattern = re.compile(
        r"(?m)^\| (?P<rank>\d+) \| (?P<axis>M(?:1[0-2]|[1-9])) "
        r"\| \*\*\((?P<class>[a-f])\)\*\* \| (?P<body>.+) \|$"
    )
    rows = list(row_pattern.finditer(report))
    axes = [match.group("axis") for match in rows]
    ranks = [int(match.group("rank")) for match in rows]
    classes = collections.Counter(match.group("class") for match in rows)
    expected_axes = {f"M{number}" for number in range(1, 13)}
    expected_order = {
        1: "M8",
        2: "M4",
        3: "M7",
        4: "M10",
        5: "M1",
        6: "M3",
        7: "M5",
        8: "M6",
        9: "M2",
        10: "M11",
        11: "M12",
        12: "M9",
    }
    add(
        checks,
        "report",
        "report.twelve-rows",
        len(rows) == 12 and set(axes) == expected_axes and len(set(axes)) == 12,
        f"rows={len(rows)} unique_axes={len(set(axes))}",
    )
    add(
        checks,
        "report",
        "report.ranks",
        sorted(ranks) == list(range(1, 13))
        and all(
            any(
                int(match.group("rank")) == rank
                and match.group("axis") == axis
                for match in rows
            )
            for rank, axis in expected_order.items()
        ),
        f"ranks={ranks}",
    )
    add(
        checks,
        "report",
        "report.one-class-each",
        len(rows) == 12
        and classes
        == collections.Counter({"a": 5, "c": 3, "d": 1, "e": 3}),
        f"classes={dict(sorted(classes.items()))}",
    )
    add(
        checks,
        "report",
        "report.labels",
        len(rows) == 12
        and all("**INFERRED BY READING" in match.group("body") for match in rows),
        "every classification row is labelled",
    )
    add(
        checks,
        "report",
        "report.m3-not-investigated",
        contains(report, "LIVE M169 WORK NOT INVESTIGATED"),
        "M3 live lane respected",
    )
    add(
        checks,
        "report",
        "report.m8-not-investigated",
        contains(
            report,
            "M3 and M8 are classified from the orchestrator's assignment and "
            "committed scorecard only; this lane did not investigate the live "
            "M169 or M170 work.",
        ),
        "M8 live lane respected",
    )
    add(
        checks,
        "report",
        "report.top-pick",
        contains(report, "Spend the next block on M8"),
        "M8 ranked first",
    )
    add(
        checks,
        "report",
        "report.case-against",
        contains(report, "M8-R zero does not imply M8-O zero")
        and contains(report, "Any single M8-O violation leaves the axis failed"),
        "case against top pick is explicit",
    )
    add(
        checks,
        "report",
        "report.partition",
        contains(
            report,
            "Classification partition: `(a)=5`, `(b)=0`, `(c)=3`, `(d)=1`, "
            "`(e)=3`, `(f)=0`; total `12`.",
        ),
        "classification partition sums to twelve",
    )
    add(
        checks,
        "report",
        "report.routed-defects",
        report.count("Exact proposed replacement:") == 4,
        f"replacement count={report.count('Exact proposed replacement:')}",
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    parser.add_argument("--report", type=Path, default=REPORT)
    parser.add_argument("--base-rev", default=BASE_REV)
    args = parser.parse_args()

    plan_path = args.plan.resolve()
    plan_bytes = plan_path.read_bytes()
    plan = plan_bytes.decode("utf-8").replace("\r\n", "\n")
    scorecard = read_utf8(args.scorecard.resolve())
    report = read_utf8(args.report.resolve())
    base = git_blob(args.base_rev, SCORECARD_PATH)
    evidence = {name: read_utf8(path) for name, path in EVIDENCE_PATHS.items()}
    checks = run_checks(plan, scorecard, report, base, plan_bytes, evidence)

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        emit(f"{status} {check.name}: {check.detail}")

    counts = collections.Counter(
        "pass" if check.passed else "fail" for check in checks
    )
    counts["skip"] = 0
    for group in sorted({check.group for check in checks}):
        members = [check for check in checks if check.group == group]
        passed = sum(check.passed for check in members)
        emit(f"GROUP {group}: pass={passed} fail={len(members) - passed}")
    emit(
        "SUMMARY "
        f"total={len(checks)} pass={counts['pass']} "
        f"fail={counts['fail']} skip={counts['skip']}"
    )
    emit("VERDICT GREEN" if counts["fail"] == 0 else "VERDICT RED")
    return 0 if counts["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
