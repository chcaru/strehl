#!/usr/bin/env python3
"""Run targeted mutation controls against verify_razor_ruling.py."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCORECARD = REPO / "docs/proposals/2026-09-sota-scorecard.md"
VERIFIER = HERE / "verify_razor_ruling.py"
SCRATCH = HERE / ".razor-controls"


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"mutation anchor count={text.count(old)} for {old!r}")
    return text.replace(old, new, 1)


def replace_in_row(text: str, path: str, old: str, new: str) -> str:
    lines = text.splitlines(keepends=True)
    hits = [
        index
        for index, line in enumerate(lines)
        if line.startswith(f"| `{path}` |")
    ]
    if len(hits) != 1:
        raise RuntimeError(f"row count={len(hits)} for {path}")
    index = hits[0]
    if old not in lines[index]:
        raise RuntimeError(f"row mutation anchor absent for {path}: {old}")
    lines[index] = lines[index].replace(old, new, 1)
    return "".join(lines)


def delete_row(text: str, path: str) -> str:
    lines = text.splitlines(keepends=True)
    kept = [line for line in lines if not line.startswith(f"| `{path}` |")]
    if len(kept) != len(lines) - 1:
        raise RuntimeError(f"expected one row for deletion: {path}")
    return "".join(kept)


def run_verifier(scorecard: Path) -> tuple[int, str]:
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(VERIFIER),
            "--scorecard",
            str(scorecard),
        ],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout.decode(
        "utf-8", errors="replace"
    )


def main() -> int:
    canonical = SCORECARD.read_text(encoding="utf-8")
    base_exit, base_output = run_verifier(SCORECARD)
    if base_exit or "VERDICT GREEN" not in base_output:
        print("BASE RED")
        print(base_output)
        return 1

    controls = [
        (
            "permit-ordering",
            lambda text: replace_once(
                text,
                "It therefore bars the proposed three-aperture ordering statistic",
                "It therefore permits the proposed three-aperture ordering statistic",
            ),
            "FAIL ruling.ordering-refused",
            True,
        ),
        (
            "erase-no-cancellation",
            lambda text: replace_once(
                text,
                "the fixed subject `S` remains inside the arm-specific\n"
                "convolution and therefore does not cancel",
                "the fixed subject `S` cancels",
            ),
            "FAIL ruling.no-cancellation",
            True,
        ),
        (
            "erase-two-world-counterexample",
            lambda text: replace_once(
                text,
                "`Y_i = K H_i X = H_i K X`",
                "`Y_i` differs between the two worlds",
            ),
            "FAIL ruling.two-worlds",
            True,
        ),
        (
            "erase-aperture-specific-locus",
            lambda text: replace_once(
                text,
                "`0.70697 px` aperture-specific components",
                "`0.00000 px` aperture-specific components",
            ),
            "FAIL ruling.actual-capture",
            True,
        ),
        (
            "generalize-m3-exception",
            lambda text: replace_once(
                text,
                "The existing broad-boundary exception is specific to M3",
                "The existing broad-boundary exception is general beyond M3",
            ),
            "FAIL ruling.m3-only",
            True,
        ),
        (
            "waive-common-defect",
            lambda text: replace_once(
                text,
                "the defect is common across arms” never overrides",
                "the defect is common across arms” sometimes overrides",
            ),
            "FAIL ruling.precedent",
            True,
        ),
        (
            "promote-diagonal-razor",
            lambda text: replace_in_row(
                text,
                r"requests\19-razor-edge\diagonal-tilt-all-axes"
                r"\diagonal-tilt-all-axes-sw4-f5.6-cpl",
                "**CONTROL — NOT HOLDOUT**",
                "**HOLDOUT — QUALITY**",
            ),
            "FAIL paths.requests\\19-razor-edge",
            True,
        ),
        (
            "drop-battery-row",
            lambda text: delete_row(
                text,
                r"requests\misc-diagnostic\flat-round-3V-battery-cpl"
                r"\flat-round-3V-battery-iso400-sw4-cpl",
            ),
            "FAIL audit.current-complete",
            True,
        ),
        (
            "soften-m3-bar",
            lambda text: replace_once(
                text,
                "literal `max(a_e)<=0.05`",
                "literal `max(a_e)<=0.06`",
            ),
            "FAIL bars.M3",
            True,
        ),
        (
            "erase-m8-fail",
            lambda text: replace_once(
                text,
                "| M8 | Independent source-hull census | **FAIL** — M8-R "
                "`1.030569%` against the achievable bar of exactly `0.0000%`",
                "| M8 | Independent source-hull census | **PASS** — M8-R "
                "`1.030569%` against the achievable bar of exactly `0.0000%`",
            ),
            "FAIL guard.m8",
            True,
        ),
        (
            "ruling-reflow-benign",
            lambda text: replace_once(
                text,
                "The common-subject argument does not clear the bar. For arm `N`, "
                "the observation is",
                "The common-subject argument does not clear the bar.\n"
                "For arm `N`, the observation is",
            ),
            "VERDICT GREEN",
            False,
        ),
    ]

    if SCRATCH.exists():
        shutil.rmtree(SCRATCH)
    SCRATCH.mkdir(parents=True)
    passed = 0
    try:
        print("BASE exit=0 checks=48 verdict=GREEN")
        print("| control | exit | expected | verdict |")
        print("| --- | ---: | --- | --- |")
        for name, mutate, expected, should_fail in controls:
            candidate = mutate(canonical)
            path = SCRATCH / f"{name}.md"
            path.write_text(candidate, encoding="utf-8", newline="\n")
            exit_code, output = run_verifier(path)
            ok = (
                exit_code != 0 and expected in output
                if should_fail
                else exit_code == 0 and expected in output
            )
            passed += int(ok)
            print(
                f"| {name} | {exit_code} | {expected} | "
                f"{'PASS' if ok else 'FAIL'} |"
            )
            if not ok:
                print(output)
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)

    print(f"CONTROL_SUMMARY passed={passed}/{len(controls)}")
    return 0 if passed == len(controls) else 1


if __name__ == "__main__":
    raise SystemExit(main())
