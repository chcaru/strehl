#!/usr/bin/env python3
"""Commission verify_capture_request.py with isolated negative and benign controls."""
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
CHECKER = Path(__file__).with_name("verify_capture_request.py")
DEFAULT_CAPTURE = ROOT / "docs/capture-requests/2026-09-319-frame-session.md"
DEFAULT_SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"


@dataclass(frozen=True)
class Control:
    name: str
    target: str
    anchor: str
    replacement: str
    expected_failed: tuple[str, ...] = ()
    expect_red: bool = True
    operation: str = "replace"
    expected_block: tuple[str, ...] = ()
    required_output: tuple[str, ...] = ()


CONTROLS = [
    Control(
        "arithmetic-block-count",
        "capture",
        "| `TC0-sw10-B` | 27 | identical independent repeat of `TC0-sw10-A` |",
        "| `TC0-sw10-B` | 26 | identical independent repeat of `TC0-sw10-A` |",
        ("arith.physical.TC0-sw10-B", "arith.physical-sum", "arith.stated-total"),
    ),
    Control(
        "arithmetic-stated-total",
        "capture",
        "| **scored session total `T_session`** | **891** | `383 + 60 + 96 + 164 + 60 + 128` |",
        "| **scored session total `T_session`** | **890** | `383 + 60 + 96 + 164 + 60 + 128` |",
        ("arith.stated-total", "arith.total-expression"),
    ),
    Control(
        "stale-603-wrapped",
        "capture",
        "Superseded: the 603-frame design, on 2026-09-04",
        "Current session total is 603\nframes.",
        ("numbers.603-only-historical",),
    ),
    Control(
        "stale-duration-budget",
        "capture",
        "promise 45 minutes.** The fixed scored blocks include 419 automated-bracket",
        "promise 45 minutes.** The fixed scored blocks include 255 automated-bracket",
        ("numbers.duration.bracket-frames",),
    ),
    Control(
        "mwork-silent-default",
        "capture",
        "- **TC0 phase:** use the bare lens at **`M_work`**, an explicitly unset",
        "- **TC0 phase:** use the bare lens at **1.30x**, a silently defaulted setting",
        ("mwork.settings-placeholder", "mwork.no-concrete-instruction"),
    ),
    Control(
        "converter-every-frame-wrapped",
        "capture",
        "off for every TC0 sweep, TC0 witness, TC0 flat and TC0 dark. This is an optical",
        "Keep the teleconverter installed for every\nframe in the session. This is an optical",
        ("converter.no-all-frame-instruction", "converter.keep-off-tc0"),
    ),
    Control(
        "stop-banner-removed",
        "capture",
        "> # ⛔ STOP — THIS DOCUMENT IS NOT SAFE TO SHOOT FROM",
        "> # READY TO SHOOT",
        ("stop.exact-banner",),
    ),
    Control(
        "stop-condition-softened",
        "capture",
        "> **This banner is removed only after M147's preflight has been delivered and",
        "> **This banner may be removed before M147's preflight has been delivered and",
        ("stop.removal-condition", "stop.not-softened"),
    ),
    Control(
        "control-row-in-scored-table",
        "capture",
        "| **existing claim/calibration** | **383** | 255 converter-on focus + 128 converter-on calibration |",
        "| `TC0-CTRL-BLUR` | 32 | scored-session physical blur control |\n"
        "| **existing claim/calibration** | **383** | 255 converter-on focus + 128 converter-on calibration |",
        (
            "controls.no-scored-table-row",
            "arith.physical-row-order",
            "internal.no-unknown-block-identifiers",
        ),
    ),
    Control(
        "unknown-block-reference",
        "capture",
        "`TC0-S10-B`, `TC0-sw10-B`, `TC0-E10-B`. Use the same counts, direction,",
        "`TC0-S10-B`, `TC0-sw10-B`, `TC0-E10-C`. Use the same counts, direction,",
        ("internal.no-unknown-block-identifiers",),
    ),
    Control(
        "missing-block-purpose",
        "capture",
        "| reset pre-flight `P0` | 6 | converter on, fixed focus at the existing maximum-reproduction reset |",
        "| reset pre-flight `P0` | 6 | |",
        ("internal.all-block-purposes-present",),
    ),
    Control(
        "inert-owner-metadata",
        "capture",
        "Owning lane: **lane-FRC**",
        "Owning lane: **lane-FRC** (administrative note)",
        expect_red=False,
    ),
    Control(
        "missing-required-citation",
        "capture",
        'session (`docs/proposals/2026-09-sota-scorecard.md`, "2.3 Holdout units and burn log" section), so it cannot be',
        "session, so it cannot be",
        ("xref.count", "xref.holdout-rule"),
    ),
    Control(
        "legacy-line-citation",
        "capture",
        '(`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Exact computation" clause) — and SOTA here is a',
        "(`docs/proposals/2026-09-sota-scorecard.md:609-611`) — and SOTA here is a",
        ("xref.no-line-number-citations",),
    ),
    Control(
        "nonliteral-citation-path",
        "capture",
        'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Input needed by a future replacement" clause).',
        'its scored value"* (`2026-09-sota-scorecard.md`, "M1 / Input needed by a future replacement" clause).',
        ("xref.paths-resolve-literally",),
    ),
    Control(
        "unknown-citation-anchor",
        "capture",
        '(`docs/proposals/2026-09-sota-scorecard.md`, "M5 / Input" clause) still governs the complete',
        '(`docs/proposals/2026-09-sota-scorecard.md`, "M5 / Missing input" clause) still governs the complete',
        ("xref.anchors-unique",),
    ),
    Control(
        "misbound-citation-count-preserved",
        "capture",
        'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Input needed by a future replacement" clause).',
        'its scored value"* (`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Exact computation" clause) '
        '(`docs/proposals/2026-09-sota-scorecard.md`, "M1 / Input needed by a future replacement" clause).',
        ("xref.citations-bound-to-claims", "xref.commission-quote"),
        required_output=("PASS xref.count: citations=7 ",),
    ),
    Control(
        "commission-source-wording",
        "scorecard",
        "instrument but may never provide its scored value.",
        "instrument but may never supply its scored value.",
        ("xref.commission-quote", "xref.all-citations-substantive"),
    ),
    Control(
        "commission-source-duplicate",
        "scorecard",
        "instrument but may never provide its scored value.",
        "instrument but may never provide its scored value.\n"
        "The burned grid and the development-only high-resolution slide may commission a new\n"
        "instrument but may never provide its scored value.",
        ("xref.commission-quote", "xref.all-citations-substantive"),
    ),
    Control(
        "frequency-source-wording",
        "scorecard",
        "pre-registered before its fresh holdout is rendered, must use no frequency above",
        "pre-registered before its fresh holdout is rendered, must use no spatial frequency above",
        ("xref.frequency-quote", "xref.all-citations-substantive"),
    ),
    Control(
        "holdout-source-wording",
        "scorecard",
        "step width. Rendering, tuning, or reading an outcome on any member burns every member",
        "step width. Rendering, tuning, or reading an outcome on any member invalidates every member",
        (
            "truth.holdout-content-anchor",
            "xref.holdout-rule",
            "xref.all-citations-substantive",
        ),
    ),
    Control(
        "m5-wilson-source-wording",
        "scorecard",
        "**Success.** **SCORECARD ADDITION:** coverage point estimate `>=99%`, Wilson LCB95",
        "**Success.** **SCORECARD ADDITION:** coverage point estimate `>=99%`, Wilson lower bound",
        ("xref.m5-wilson-quote", "xref.all-citations-substantive"),
    ),
    Control(
        "m5-input-source-wording",
        "scorecard",
        "500 eligible tiles overall and 50 per capture must qualify. M5 remains",
        "500 eligible tiles overall and 51 per capture must qualify. M5 remains",
        ("xref.m5-eligibility-floor", "xref.all-citations-substantive"),
    ),
    Control(
        "blockquote-lines-benign",
        "scorecard",
        "The holdout unit is **subject plus uninterrupted capture session**, not a directory or",
        "",
        expect_red=False,
        operation="blockquote",
        expected_block=(
            "The holdout unit is **subject plus uninterrupted capture session**, not a directory or",
            "step width. Rendering, tuning, or reading an outcome on any member burns every member",
            "of that unit. A `HOLDOUT` capture may be decoded to build the frozen common input and",
            "input-only site manifest, but no output, metric, visual verdict, parameter sweep, or",
            "code-acceptance decision may be seen before the registered score run.",
        ),
        required_output=(
            "PASS truth.holdout-content-anchor:",
            "PASS xref.holdout-rule:",
        ),
    ),
    Control(
        "source-line-shift-benign",
        "scorecard",
        "# strehl — pre-registered SOTA scorecard",
        "<!-- benign line-shift control -->",
        expect_red=False,
        operation="insert_after",
    ),
    Control(
        "seventh-citation-benign",
        "capture",
        "- **This session provides the scored value. It is HOLDOUT.**",
        '  The same rule is cited again (`docs/proposals/2026-09-sota-scorecard.md`, "2.3 Holdout units and burn log" section).',
        expect_red=False,
        operation="insert_after",
        required_output=("PASS xref.count: citations=7 ",),
    ),
]


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def mutate(text: str, control: Control) -> str:
    lines = text.splitlines()
    hits = [index for index, line in enumerate(lines) if line == control.anchor]
    if len(hits) != 1:
        raise RuntimeError(
            f"{control.name}: anchor count={len(hits)}, expected exactly 1: {control.anchor!r}"
        )
    index = hits[0]
    if control.operation == "replace":
        lines[index:index + 1] = control.replacement.splitlines()
    elif control.operation == "insert_after":
        lines[index + 1:index + 1] = control.replacement.splitlines()
    elif control.operation == "blockquote":
        block = tuple(lines[index:index + len(control.expected_block)])
        if block != control.expected_block:
            raise RuntimeError(
                f"{control.name}: anchored block differs: actual={block!r}"
            )
        lines[index:index + len(block)] = [f"> {line}" for line in block]
    else:
        raise RuntimeError(f"{control.name}: unsupported operation {control.operation!r}")
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def run_checker(capture: Path, scorecard: Path) -> tuple[int, str, set[str], str, int | None]:
    completed = subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--capture",
            str(capture),
            "--scorecard",
            str(scorecard),
            "--verbose",
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    failed = set(re.findall(r"^FAIL ([^:]+):", output, flags=re.MULTILINE))
    verdicts = re.findall(r"^VERDICT (GREEN|RED)\r?$", output, flags=re.MULTILINE)
    totals = re.findall(r"^CHECKS total=(\d+) ", output, flags=re.MULTILINE)
    verdict = verdicts[-1] if verdicts else "MISSING"
    total = int(totals[-1]) if totals else None
    return completed.returncode, output, failed, verdict, total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", type=Path, default=DEFAULT_CAPTURE)
    parser.add_argument("--scorecard", type=Path, default=DEFAULT_SCORECARD)
    args = parser.parse_args()

    capture = read_utf8(args.capture.resolve())
    scorecard = read_utf8(args.scorecard.resolve())
    temp_env = os.environ.get("TEMP")
    if not temp_env:
        raise RuntimeError("TEMP is unset; controls require an explicit $env:TEMP copy")
    temp_root = Path(temp_env).resolve()
    if not temp_root.is_dir():
        raise RuntimeError(f"TEMP does not exist: {temp_root}")

    rows: list[tuple[str, str, int, str, str]] = []
    passed_controls = 0
    negative_total = sum(control.expect_red for control in CONTROLS)
    benign_total = len(CONTROLS) - negative_total
    negative_red = 0
    benign_green = 0

    with tempfile.TemporaryDirectory(prefix="m160-capreq-", dir=temp_root) as temp_name:
        temp_dir = Path(temp_name)
        base_capture = temp_dir / "base-capture.md"
        base_scorecard = temp_dir / "base-scorecard.md"
        base_capture.write_bytes(capture.encode("utf-8"))
        base_scorecard.write_bytes(scorecard.encode("utf-8"))
        base_code, base_output, base_failed, base_verdict, base_total = run_checker(
            base_capture, base_scorecard
        )
        if (
            base_code != 0
            or base_verdict != "GREEN"
            or base_failed
            or base_total is None
            or base_total < 136
        ):
            print(base_output)
            raise RuntimeError(
                f"commissioning baseline is not GREEN with >=136 checks: "
                f"exit={base_code} verdict={base_verdict} total={base_total}"
            )
        print(f"BASE checks={base_total} exit={base_code} verdict={base_verdict}")

        for index, control in enumerate(CONTROLS, 1):
            control_dir = temp_dir / f"{index:02d}-{control.name}"
            control_dir.mkdir()
            candidate_capture = capture
            candidate_scorecard = scorecard
            if control.target == "capture":
                candidate_capture = mutate(capture, control)
            elif control.target == "scorecard":
                candidate_scorecard = mutate(scorecard, control)
            else:
                raise RuntimeError(f"{control.name}: unsupported target {control.target!r}")

            capture_path = control_dir / "capture.md"
            scorecard_path = control_dir / "scorecard.md"
            capture_path.write_bytes(candidate_capture.encode("utf-8"))
            scorecard_path.write_bytes(candidate_scorecard.encode("utf-8"))
            code, output, failed, verdict, _ = run_checker(capture_path, scorecard_path)
            output_ok = all(fragment in output for fragment in control.required_output)
            if control.expect_red:
                expected_observed = all(check_id in failed for check_id in control.expected_failed)
                passed = (
                    code == 1
                    and verdict == "RED"
                    and expected_observed
                    and output_ok
                )
                if passed:
                    negative_red += 1
                expected_cell = (
                    f"{'yes' if expected_observed else 'no'}: "
                    + ", ".join(control.expected_failed)
                )
            else:
                expected_observed = not failed and output_ok
                passed = code == 0 and verdict == "GREEN" and expected_observed
                if passed:
                    benign_green += 1
                expected_cell = (
                    "n/a (GREEN observed)"
                    if expected_observed
                    else "n/a (unexpected failure)"
                )
            if passed:
                passed_controls += 1
            rows.append(
                (
                    control.name,
                    "yes",
                    code,
                    expected_cell,
                    f"{verdict} / {'PASS' if passed else 'FAIL'}",
                )
            )
            if not passed:
                print(f"\nCONTROL FAILURE: {control.name}\n{output}")

    print("| control | anchor found | exit code | expected check failed | verdict |")
    print("| --- | --- | ---: | --- | --- |")
    for name, anchor_found, code, expected_cell, verdict in rows:
        print(f"| {name} | {anchor_found} | {code} | {expected_cell} | {verdict} |")
    print(
        f"CONTROL_SUMMARY passed={passed_controls}/{len(CONTROLS)} "
        f"negative_red={negative_red}/{negative_total} "
        f"benign_green={benign_green}/{benign_total}"
    )
    return 0 if passed_controls == len(CONTROLS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
