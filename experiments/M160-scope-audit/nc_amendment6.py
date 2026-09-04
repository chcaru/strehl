#!/usr/bin/env python3
"""Commission the Amendment 6 verifier with targeted negative controls.

Scratch copies live under this lane's experiment directory and are removed in a
``finally`` block. No system temporary directory is used.
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
VERIFIER = Path(__file__).with_name("verify_amendment6.py")
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
REPORT = ROOT / "docs/research/M160-amendment6-reachability.md"
WORK = Path(__file__).with_name(".amendment6-controls")


@dataclass(frozen=True)
class Control:
    name: str
    target: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False


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


def line_with_prefix(text: str, prefix: str) -> str:
    matches = [line for line in text.splitlines() if line.startswith(prefix)]
    if len(matches) != 1:
        raise RuntimeError(f"expected one line with {prefix!r}, found {len(matches)}")
    return matches[0]


def run_verifier(scorecard: Path, report: Path) -> tuple[int, str, set[str]]:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(VERIFIER),
            "--scorecard",
            str(scorecard),
            "--report",
            str(report),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    failed = set(re.findall(r"^FAIL ([^:]+):", output, flags=re.MULTILINE))
    return completed.returncode, output, failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()

    scorecard_source = read_utf8(args.scorecard.resolve())
    report_source = read_utf8(args.report.resolve())
    m12_row = line_with_prefix(report_source, "| 11 | M12 |")

    controls = (
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
            "current usable instrument.",
            "Capture can replace and “shoot around” the instrument.",
            ("scorecard.capture-precondition",),
        ),
        Control(
            "assert-m1-uniqueness",
            "scorecard",
            "M1 is not the unique mathematical anchor.",
            "M1 is the unique mathematical anchor.",
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
            ("report.twelve-rows", "report.ranks", "report.one-class-each"),
        ),
        Control(
            "give-m8-two-classes",
            "report",
            "| 1 | M8 | **(e)** |",
            "| 1 | M8 | **(e)(f)** |",
            ("report.twelve-rows", "report.ranks", "report.one-class-each"),
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
            "D7AD61E0E9B37D0C761810620EE0F296C9E8DC188509E1E860CBA44D9FA905F5",
            "07AD61E0E9B37D0C761810620EE0F296C9E8DC188509E1E860CBA44D9FA905F5",
            ("report.source-hashes",),
        ),
        Control(
            "scope-reflow-benign",
            "scorecard",
            "The operative\nlimitation is that rendered outputs do not by themselves identify",
            "The operative limitation is that rendered outputs do not\nby themselves identify",
            benign=True,
        ),
    )

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    rows: list[tuple[str, int, str, str]] = []
    passed_controls = 0
    try:
        baseline_scorecard = WORK / "baseline-scorecard.md"
        baseline_report = WORK / "baseline-report.md"
        baseline_scorecard.write_bytes(scorecard_source.encode("utf-8"))
        baseline_report.write_bytes(report_source.encode("utf-8"))
        base_code, base_output, base_failed = run_verifier(
            baseline_scorecard, baseline_report
        )
        if base_code != 0 or base_failed or "VERDICT GREEN" not in base_output:
            emit(base_output)
            raise RuntimeError(f"unexpected baseline verifier exit={base_code}")
        base_passes = len(
            re.findall(r"^PASS [^:]+:", base_output, flags=re.MULTILINE)
        )
        emit(f"BASE exit=0 checks={base_passes} verdict=GREEN")

        for index, control in enumerate(controls, 1):
            scorecard = scorecard_source
            report = report_source
            if control.target == "scorecard":
                scorecard = mutate(scorecard, control)
            elif control.target == "report":
                report = mutate(report, control)
            else:
                raise RuntimeError(f"unknown target {control.target}")

            control_dir = WORK / f"{index:02d}-{control.name}"
            control_dir.mkdir()
            scorecard_path = control_dir / "scorecard.md"
            report_path = control_dir / "report.md"
            scorecard_path.write_bytes(scorecard.encode("utf-8"))
            report_path.write_bytes(report.encode("utf-8"))
            code, output, failed = run_verifier(scorecard_path, report_path)

            if control.benign:
                ok = code == 0 and not failed and "VERDICT GREEN" in output
                expected = "GREEN (benign)"
            else:
                ok = code == 1 and all(
                    check_id in failed for check_id in control.expected_fail
                )
                expected = "RED " + ",".join(control.expected_fail)
            passed_controls += int(ok)
            rows.append(
                (control.name, code, expected, "PASS" if ok else "FAIL")
            )
            if not ok:
                emit(f"\nCONTROL FAILURE {control.name}\n{output}")
    finally:
        if WORK.exists():
            shutil.rmtree(WORK)

    emit("| control | exit | expected | verdict |")
    emit("| --- | ---: | --- | --- |")
    for name, code, expected, verdict in rows:
        emit(f"| {name} | {code} | {expected} | {verdict} |")
    emit(f"CONTROL_SUMMARY passed={passed_controls}/{len(controls)}")
    return 0 if passed_controls == len(controls) else 1


if __name__ == "__main__":
    raise SystemExit(main())
