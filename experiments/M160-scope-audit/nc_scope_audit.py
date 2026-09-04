#!/usr/bin/env python3
"""Commission the independent M160 scope audit on temporary text copies."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDITOR = Path(__file__).with_name("verify_scope_audit.py")
AUTHOR_VERIFIER = ROOT / "experiments/ORCH-verify/v-scope.ps1"
PLAN = ROOT / "docs/proposals/2026-08-sota-path.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
TARGET_REV = "6b966d8c"


@dataclass(frozen=True)
class Control:
    name: str
    target: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    expected_pass: tuple[str, ...] = ()
    same_failure_set: bool = False
    operation: str = "replace"
    author_must_green: bool = False


M8_ROW = (
    "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%`, "
    "M8-O `1.326144%` against a bar of exactly `0.0000%` | **UNMEASURED** | "
    "**UNMEASURED** | **READ AND ADMITTED `76b3d9cc`**, superseding the prior "
    "UNMEASURED cell. Checker commissioned in both directions before the reading. "
    "M8-R is 100% attributable to the Catmull-Rom gather; bilinear gives "
    "`0/6,131,678,976` but costs 0.3404 dex of band detail. M8-O is a separate "
    "downstream failure. See `docs/research/M8-overshoot.md`. |"
)

CONTROLS = (
    Control(
        "plan-detail-instrument-wording",
        "plan",
        "> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise",
        "> (D1: no licensed detail instrument), at strictly lower noise",
        expected_fail=("A.map-M1",),
    ),
    Control(
        "plan-helicon-made-mandatory",
        "plan",
        "speed quote against it), Helicon if obtainable. Every scorecard run archives hashes",
        "speed quote against it), Helicon is mandatory. Every scorecard run archives hashes",
        expected_fail=("B.helicon-optional",),
    ),
    Control(
        "plan-purchase-adds-helicon",
        "plan",
        "session has room. *Owner (purchase):* the Zerene licence — D1 is blocked on it and",
        "session has room. *Owner (purchase):* the Zerene and Helicon licences — D1 is blocked on them and",
        expected_fail=("B.owner-purchase-zerene-only",),
    ),
    Control(
        "m8-fail-retracted",
        "scorecard",
        M8_ROW,
        M8_ROW.replace("**FAIL** — M8-R", "**PASS** — M8-R"),
        expected_fail=("C.m8-fail-preserved", "C.no-fail-text-retracted"),
    ),
    Control(
        "withdrawn-wording-outside-block",
        "scorecard",
        "### 0.1 Decision rule",
        (
            "The shipping default passes every primary bar below against licensed "
            "Zerene Stacker and Helicon Focus.\n\n### 0.1 Decision rule"
        ),
        expected_fail=("C.withdrawn-old-text-position",),
    ),
    Control(
        "author-position-counterexample",
        "scorecard",
        '> restored to optional.** This paragraph previously read *"passes every primary bar',
        "> restored to optional.** This paragraph previously read a withdrawn all-primary rule.",
        expected_fail=("C.withdrawn-old-text-position",),
        operation="move_withdrawal",
        author_must_green=True,
    ),
    Control(
        "repair-primary-gate-scope",
        "scorecard",
        "1. Every primary metric is a hard gate. No win compensates for a loss.",
        (
            "1. Each owner-required metric (`M1`, `M2`, `M3`, `M8`, `M9`, `M10`, "
            "`M11`) is a hard gate. Other axes remain mandatory disclosures."
        ),
        expected_pass=("D.scope-every-primary-hard",),
    ),
    Control(
        "repair-required-fork-settings",
        "scorecard",
        "  DMap; no retouching; output contrast/brightness/sharpening at neutral/off.",
        (
            "  DMap; no retouching; output contrast/brightness/sharpening at neutral/off.\n"
            "- **fork:** frozen best-known build and frozen settings."
        ),
        expected_pass=("D.comparator-settings-missing-fork",),
    ),
    Control(
        "repair-helicon-optional-settings",
        "scorecard",
        "- **Helicon Focus:** licensed current shipping build; Methods A, B, and C at factory",
        "- **Helicon Focus, when obtainable:** licensed current shipping build; Methods A, B, and C at factory",
        expected_pass=("D.comparator-settings-helicon-not-optional",),
    ),
    Control(
        "benign-scorecard-line-shift",
        "scorecard",
        "> `1.030569%`. It removes prerequisites this document invented. Nothing else.",
        "> <!-- benign line-shift control -->",
        same_failure_set=True,
        operation="insert_after",
    ),
    Control(
        "benign-plan-quote-rewrap",
        "plan",
        "> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly lower noise",
        (
            "> (D1: FRC + slant-edge, licensed Zerene PMax *and* DMap), at strictly\n"
            "> lower noise"
        ),
        same_failure_set=True,
    ),
)


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def emit(text: str) -> None:
    print(text.encode("ascii", errors="replace").decode("ascii"))


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


def mutate(text: str, control: Control) -> str:
    lines = text.splitlines()
    hits = [index for index, line in enumerate(lines) if line == control.anchor]
    if len(hits) != 1:
        raise RuntimeError(
            f"{control.name}: anchor count={len(hits)}, expected exactly 1: {control.anchor!r}"
        )
    index = hits[0]
    replacement = control.replacement.splitlines()
    if control.operation == "replace":
        lines[index:index + 1] = replacement
    elif control.operation == "insert_after":
        lines[index + 1:index + 1] = replacement
    elif control.operation == "move_withdrawal":
        decision_anchor = "### 0.1 Decision rule"
        decision_hits = [
            line_index
            for line_index, line in enumerate(lines)
            if line == decision_anchor
        ]
        if len(decision_hits) != 1:
            raise RuntimeError(
                f"{control.name}: secondary anchor count={len(decision_hits)}, "
                f"expected exactly 1: {decision_anchor!r}"
            )
        lines[index:index + 1] = replacement
        decision_index = decision_hits[0]
        lines[decision_index + 1:decision_index + 1] = [
            "The shipping default passes every primary bar below against licensed "
            "Zerene Stacker and Helicon Focus.",
            "",
        ]
    else:
        raise RuntimeError(f"{control.name}: unsupported operation={control.operation!r}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def run_audit(plan: Path, scorecard: Path) -> tuple[int, str, set[str], set[str]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(AUDITOR),
            "--plan",
            str(plan),
            "--after-file",
            str(scorecard),
            "--verbose",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    passed = set(re.findall(r"^PASS ([^:]+):", output, flags=re.MULTILINE))
    failed = set(re.findall(r"^FAIL ([^:]+):", output, flags=re.MULTILINE))
    return completed.returncode, output, passed, failed


def run_author_verifier(scorecard: Path) -> tuple[int, str]:
    completed = subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(AUTHOR_VERIFIER),
            "-ScorecardPath",
            str(scorecard),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return completed.returncode, completed.stdout.decode("utf-8", errors="replace")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=PLAN)
    parser.add_argument("--scorecard-rev", default=TARGET_REV)
    args = parser.parse_args()

    plan = read_utf8(args.plan.resolve())
    scorecard = git_blob(args.scorecard_rev, SCORECARD_PATH)
    temp_env = os.environ.get("TEMP")
    if not temp_env:
        raise RuntimeError("TEMP is unset")
    temp_root = Path(temp_env).resolve()
    if not temp_root.is_dir():
        raise RuntimeError(f"TEMP does not exist: {temp_root}")

    rows: list[tuple[str, str, int, str, str]] = []
    passed_controls = 0
    with tempfile.TemporaryDirectory(prefix="m160-scope-audit-", dir=temp_root) as name:
        temp_dir = Path(name)
        base_plan = temp_dir / "plan.md"
        base_scorecard = temp_dir / "scorecard.md"
        base_plan.write_bytes(plan.encode("utf-8"))
        base_scorecard.write_bytes(scorecard.encode("utf-8"))
        base_code, base_output, base_passed, base_failed = run_audit(
            base_plan, base_scorecard
        )
        required_claims = (
            "CLAIM A CONFIRMED",
            "CLAIM B CONFIRMED",
            "CLAIM C CONFIRMED",
            "CLAIM D REFUTED",
        )
        if base_code != 1 or not all(text in base_output for text in required_claims):
            emit(base_output)
            raise RuntimeError(f"unexpected baseline audit exit={base_code}")
        print(
            f"BASE exit={base_code} passed_checks={len(base_passed)} "
            f"failed_checks={len(base_failed)} verdict=REFUTED"
        )

        for index, control in enumerate(CONTROLS, 1):
            candidate_plan = plan
            candidate_scorecard = scorecard
            if control.target == "plan":
                candidate_plan = mutate(plan, control)
            elif control.target == "scorecard":
                candidate_scorecard = mutate(scorecard, control)
            else:
                raise RuntimeError(f"{control.name}: unknown target={control.target!r}")

            control_dir = temp_dir / f"{index:02d}-{control.name}"
            control_dir.mkdir()
            plan_path = control_dir / "plan.md"
            scorecard_path = control_dir / "scorecard.md"
            plan_path.write_bytes(candidate_plan.encode("utf-8"))
            scorecard_path.write_bytes(candidate_scorecard.encode("utf-8"))
            code, output, passed, failed = run_audit(plan_path, scorecard_path)

            fail_ok = all(check_id in failed for check_id in control.expected_fail)
            pass_ok = all(check_id in passed for check_id in control.expected_pass)
            same_ok = not control.same_failure_set or failed == base_failed
            author_ok = True
            if control.author_must_green:
                author_code, author_output = run_author_verifier(scorecard_path)
                author_ok = author_code == 0 and "RESULT: 35 passed, 0 failed" in author_output
            ok = code in (1, 2) and fail_ok and pass_ok and same_ok and author_ok
            passed_controls += int(ok)
            transition_parts = []
            if control.expected_fail:
                transition_parts.append("FAIL " + ",".join(control.expected_fail))
            if control.expected_pass:
                transition_parts.append("PASS " + ",".join(control.expected_pass))
            if control.same_failure_set:
                transition_parts.append("same failure set")
            if control.author_must_green:
                transition_parts.append("author verifier false-GREEN")
            rows.append(
                (
                    control.name,
                    "yes",
                    code,
                    "; ".join(transition_parts),
                    "PASS" if ok else "FAIL",
                )
            )
            if not ok:
                emit(f"\nCONTROL FAILURE {control.name}\n{output}")

    print("| control | anchor found | exit code | expected transition | verdict |")
    print("| --- | --- | ---: | --- | --- |")
    for name, anchor, code, transition, verdict in rows:
        print(f"| {name} | {anchor} | {code} | {transition} | {verdict} |")
    print(f"CONTROL_SUMMARY passed={passed_controls}/{len(CONTROLS)}")
    return 0 if passed_controls == len(CONTROLS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
