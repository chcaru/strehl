#!/usr/bin/env python3
"""Commission the Amendment 6 verifier with targeted negative controls.

Every arm runs from a minimal copied tree under this lane's experiment
directory. Mutations never touch the shared working files, and the copied trees
are removed in a ``finally`` block. No system temporary directory is used.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VERIFIER_REL = Path("experiments/M160-scope-audit/verify_amendment6.py")
SCORECARD_REL = Path("docs/proposals/2026-09-sota-scorecard.md")
REPORT_REL = Path("docs/research/M160-amendment6-reachability.md")
SCORECARD = ROOT / SCORECARD_REL
REPORT = ROOT / REPORT_REL
WORK = Path(__file__).with_name(".amendment6-controls")
TREE_FILES = (
    VERIFIER_REL,
    SCORECARD_REL,
    REPORT_REL,
    Path("docs/research/M152-site-census.md"),
    Path("docs/research/M164-m2-repair.md"),
    Path("docs/research/M166-m10-definition-repair.md"),
    Path("docs/research/M167-detail-battery.md"),
    Path("experiments/M167-detail-battery/ADMISSION-PREREGISTRATION.md"),
    Path("docs/research/M168-cheap-reference-feasibility.md"),
    Path("docs/STATUS.md"),
    Path("docs/capture-requests/2026-09-319-frame-session.md"),
    Path("docs/OWNER-ACTIONS.md"),
)


@dataclass(frozen=True)
class Control:
    name: str
    target: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False


@dataclass(frozen=True)
class VerifierRun:
    code: int
    output: str
    failed: set[str]
    total: int
    passed: int
    fail: int
    skip: int


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def mutate(source: str, control: Control) -> str:
    count = source.count(control.anchor)
    if count != 1:
        raise RuntimeError(
            f"{control.name}: expected one anchor, found {count}: "
            f"{control.anchor!r}"
        )
    candidate = source.replace(control.anchor, control.replacement, 1)
    if candidate == source:
        raise RuntimeError(f"{control.name}: mutation did not land")
    return candidate


def replace_once(source: str, old: str, new: str, name: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{name}: expected one replacement token, found {count}: {old!r}"
        )
    candidate = source.replace(old, new, 1)
    if candidate == source:
        raise RuntimeError(f"{name}: replacement did not land")
    return candidate


def line_with_prefix(text: str, prefix: str) -> str:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one line with {prefix!r}, found {len(matches)}")
    return matches[0]


def build_tree(tree: Path, scorecard_source: str, report_source: str) -> None:
    for relative in TREE_FILES:
        source = ROOT / relative
        destination = tree / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    (tree / SCORECARD_REL).write_bytes(scorecard_source.encode("utf-8"))
    (tree / REPORT_REL).write_bytes(report_source.encode("utf-8"))


def run_verifier(tree: Path) -> VerifierRun:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(tree / VERIFIER_REL),
        ],
        cwd=tree,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    failed = set(re.findall(r"^FAIL ([^:]+):", output, flags=re.MULTILINE))
    summary = re.search(
        r"^SUMMARY total=(\d+) pass=(\d+) fail=(\d+) skip=(\d+)$",
        output,
        flags=re.MULTILINE,
    )
    if not summary:
        raise RuntimeError(f"verifier emitted no parseable summary:\n{output}")
    total, passed, fail, skip = map(int, summary.groups())
    if passed + fail + skip != total:
        raise RuntimeError(
            f"verifier partition mismatch: total={total} pass={passed} "
            f"fail={fail} skip={skip}"
        )
    return VerifierRun(
        completed.returncode,
        output,
        failed,
        total,
        passed,
        fail,
        skip,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    scorecard_source = read_utf8(args.scorecard.resolve())
    report_source = read_utf8(args.report.resolve())
    m12_row = line_with_prefix(report_source, "| 11 | M12 |")
    m10_bar_row = line_with_prefix(
        scorecard_source, "| M10 | Physical depth product |"
    )
    m12_bar_row = line_with_prefix(
        scorecard_source,
        "| M12 | Memory, determinism, and scaling invariance |",
    )
    status_anchor = (
        "# strehl — pre-registered SOTA scorecard\n\n"
        "**Status: SPEC / PRE-REGISTRATION v1.11 (2026-09-06).**"
    )
    m12_revision_reflow = (
        "*forward* guard is untouched and still binds at §3.3: M11's claimed\n"
        "production-speed output must be byte-identical across the worker ladder."
    )

    controls = (
        Control(
            "advance-current-version",
            "scorecard",
            status_anchor,
            replace_once(
                status_anchor,
                "v1.11",
                "v1.12",
                "advance-current-version",
            ),
            ("scorecard.version",),
        ),
        Control(
            "declare-m10-fully-defined",
            "scorecard",
            m10_bar_row,
            replace_once(
                m10_bar_row,
                "**PARTIALLY DEFINED; DEFINITION BLOCKED.**",
                "**DEFINED.**",
                "declare-m10-fully-defined",
            ),
            ("bars.M10",),
        ),
        Control(
            "restore-m12-reverse-m11-dependency",
            "scorecard",
            m12_bar_row,
            replace_once(
                m12_bar_row,
                "mutually byte-identical;",
                "mutually byte-identical while 16 workers passes M11;",
                "restore-m12-reverse-m11-dependency",
            ),
            ("bars.M12",),
        ),
        Control(
            "drop-load-bearing-hedge",
            "scorecard",
            "high-frequency variation is removed noise or artifact, or removed scene signal,\n"
            "**without an assumption or observation outside those outputs**.",
            "high-frequency variation is removed noise or artifact, or removed scene signal.",
            ("scorecard.scope-hedge",),
        ),
        Control(
            "universalize-no-reference-claim",
            "scorecard",
            "That does not prove\nevery conceivable no-reference metric impossible.",
            "That proves every conceivable no-reference metric impossible.",
            ("scorecard.no-universal",),
        ),
        Control(
            "merge-proof-statuses",
            "scorecard",
            "D8 common-filter invariance is an\nalgebraic result;",
            "D8 common-filter invariance is an\nempirical result;",
            ("scorecard.mechanisms-distinct",),
        ),
        Control(
            "make-capture-a-workaround",
            "scorecard",
            "Capture likewise\ndoes not replace or “shoot around” an instrument: "
            "it supplies identifying information\nand is a precondition of the "
            "currently specified instrument route.",
            "Capture can replace and “shoot around” the instrument.",
            ("scorecard.capture-precondition",),
        ),
        Control(
            "assert-m1-uniqueness",
            "scorecard",
            "M1 is not the unique\nmathematical anchor.",
            "M1 is the unique\nmathematical anchor.",
            ("scorecard.m1-not-unique",),
        ),
        Control(
            "promote-m2-to-pass",
            "scorecard",
            "**Instrument status: INSTRUMENT VOID; current axis verdict `UNMEASURED`.**",
            "**Instrument status: ADMITTED; current axis verdict `PASS`.**",
            ("scorecard.m2-unmeasured",),
        ),
        Control(
            "erase-m8-fail",
            "scorecard",
            "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%` "
            "against the achievable bar of exactly `0.0000%`;",
            "| M8 | Independent source-hull census | **PASS** — M8-R `0.000000%` "
            "against the achievable bar of exactly `0.0000%`;",
            ("scorecard.m8-fail",),
        ),
        Control(
            "soften-m3-bar",
            "scorecard",
            "literal `max(a_e)<=0.05`",
            "literal `max(a_e)<=0.06`",
            ("bars.M3",),
        ),
        Control(
            "delete-m12-classification",
            "report",
            m12_row,
            "",
            (
                "report.twelve-rows",
                "report.ranks",
                "report.one-class-each",
                "report.labels",
            ),
        ),
        Control(
            "give-m8-two-classes",
            "report",
            "| 1 | M8 | **(e)** |",
            "| 1 | M8 | **(e)(f)** |",
            (
                "report.twelve-rows",
                "report.ranks",
                "report.one-class-each",
                "report.labels",
            ),
        ),
        Control(
            "replace-top-pick",
            "report",
            "### Spend the next block on M8",
            "### Spend the next block on M10",
            ("report.top-pick",),
        ),
        Control(
            "erase-case-against",
            "report",
            "M8-R zero does not imply M8-O zero.",
            "M8-R zero guarantees M8-O zero.",
            ("report.case-against",),
        ),
        Control(
            "corrupt-source-hash",
            "report",
            "1E075C8BECEC35BC67231868781E614DC0748989F14E2F172C777E3964CEB443",
            "0E075C8BECEC35BC67231868781E614DC0748989F14E2F172C777E3964CEB443",
            ("report.source-hashes",),
        ),
        Control(
            "scope-reflow-benign",
            "scorecard",
            "The operative\nlimitation is that rendered outputs do not by themselves identify",
            "The operative limitation is that rendered outputs do not\nby themselves identify",
            benign=True,
        ),
        Control(
            "m12-revision-reflow-benign",
            "scorecard",
            m12_revision_reflow,
            "*forward* guard is untouched and still binds at §3.3:\n"
            "M11's claimed production-speed output must be byte-identical across "
            "the worker ladder.",
            benign=True,
        ),
    )

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    rows: list[tuple[str, int, str, str, str]] = []
    caught = 0
    missed = 0
    inert = 0
    try:
        baseline_tree = WORK / "00-baseline" / "tree"
        build_tree(baseline_tree, scorecard_source, report_source)
        baseline = run_verifier(baseline_tree)
        if (
            baseline.code != 0
            or baseline.failed
            or baseline.fail != 0
            or baseline.skip != 0
            or "VERDICT GREEN" not in baseline.output
        ):
            emit(baseline.output)
            raise RuntimeError(
                f"unexpected baseline verifier exit={baseline.code}"
            )
        emit(
            "BASE "
            f"total={baseline.total} pass={baseline.passed} "
            f"fail={baseline.fail} skip={baseline.skip} "
            f"accounted={baseline.passed + baseline.fail + baseline.skip} "
            "verdict=GREEN"
        )

        for index, control in enumerate(controls, 1):
            control_tree = WORK / f"{index:02d}-{control.name}" / "tree"
            shutil.copytree(baseline_tree, control_tree)
            if control.target == "scorecard":
                target = control_tree / SCORECARD_REL
            elif control.target == "report":
                target = control_tree / REPORT_REL
            else:
                raise RuntimeError(f"unknown target {control.target}")
            source = read_utf8(target)
            target.write_bytes(mutate(source, control).encode("utf-8"))
            run = run_verifier(control_tree)

            if control.benign:
                ok = (
                    run.code == 0
                    and not run.failed
                    and run.fail == 0
                    and run.skip == 0
                    and "VERDICT GREEN" in run.output
                )
                expected = "GREEN (benign)"
                outcome = "INERT" if ok else "MISSED"
            else:
                expected_fail = set(control.expected_fail)
                ok = (
                    run.code == 1
                    and run.failed == expected_fail
                    and run.fail == len(expected_fail)
                    and run.skip == 0
                )
                expected = "RED " + ",".join(control.expected_fail)
                outcome = "CAUGHT" if ok else "MISSED"
            if outcome == "CAUGHT":
                caught += 1
            elif outcome == "INERT":
                inert += 1
            else:
                missed += 1
            observed = (
                "GREEN"
                if not run.failed
                else "RED " + ",".join(sorted(run.failed))
            )
            rows.append(
                (control.name, run.code, expected, observed, outcome)
            )
            if not ok:
                emit(f"\nCONTROL FAILURE {control.name}\n{run.output}")
    finally:
        if WORK.exists():
            shutil.rmtree(WORK)

    accounted = caught + missed + inert
    emit("| control | exit | expected | observed | outcome |")
    emit("| --- | ---: | --- | --- | --- |")
    for name, code, expected, observed, outcome in rows:
        emit(f"| {name} | {code} | {expected} | {observed} | {outcome} |")
    emit(
        "COMMISSION_SUMMARY "
        f"ARMS={len(controls)} CAUGHT={caught} MISSED={missed} INERT={inert} "
        f"ACCOUNTED={accounted}"
    )
    return 0 if missed == 0 and accounted == len(controls) else 1


if __name__ == "__main__":
    raise SystemExit(main())
