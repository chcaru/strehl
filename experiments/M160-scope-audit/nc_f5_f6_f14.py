#!/usr/bin/env python3
"""Commission the F5/F6/F14 verifier on UTF-8 copies below %TEMP%."""
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
VERIFIER = Path(__file__).with_name("verify_f5_f6_f14.py")
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
SCORECARD_PATH = "docs/proposals/2026-09-sota-scorecard.md"
RECONCILED_REV = "7648d360"


@dataclass(frozen=True)
class Control:
    name: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False


M8_ROW = (
    "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%`, "
    "M8-O `1.326144%` against a bar of exactly `0.0000%` | **UNMEASURED** | "
    "**UNMEASURED** | **UNMEASURED** | **READ AND ADMITTED `76b3d9cc`**, "
    "superseding the prior UNMEASURED cell. Checker commissioned in both directions "
    "before the reading. M8-R is 100% attributable to the Catmull-Rom gather; "
    "bilinear gives `0/6,131,678,976` but costs 0.3404 dex of band detail. M8-O is a "
    "separate downstream failure. See `docs/research/M8-overshoot.md`. |"
)

M2_GLANCE_ROW = (
    "| M2 | Flat/defocused-ground noise | Cross-fit efficiency `<=1.10`; "
    "95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |"
)

CONTROLS = (
    Control(
        "product-native-satisfies-sota",
        "only on that common-merge track.** Product-native results are separately publishable",
        "on either common-merge or product-native evidence.** Product-native results are separately publishable",
        ("track.sota-common-only",),
    ),
    Control(
        "high-frequency-without-instrument",
        "   `0.25 cyc/native px` remains `UNLICENSED_GT_0.25`. Absence of such an instrument",
        "   `0.25 cyc/native px` may be reported as licensed without an instrument. Absence of such an instrument",
        ("frequency.unlicensed-stays-unlicensed",),
    ),
    Control(
        "m4-m8-converts-m2",
        "  published beside M2 but does not convert M2 to `FAIL` or `UNMEASURED`; likewise an",
        "  published beside M2 and converts M2 to `FAIL`; likewise an",
        ("m2.disposition-independent",),
    ),
    Control(
        "delete-improvement-control",
        "   **improvement** that the instrument rewards in the claimed direction, an untuned",
        "   degradation-only challenge that the instrument penalizes, an untuned",
        ("frequency.improvement-control",),
    ),
    Control(
        "allow-cross-track-splicing",
        "or verdict from one into the other. SOTA is not an average, a weighted score, or",
        "or verdict from one into the other, except when selecting the best value. SOTA is not an average, a weighted score, or",
        ("track.scope-no-splicing",),
    ),
    Control(
        "erase-m2-instrument-void",
        "**Instrument status: INSTRUMENT VOID; current axis verdict `UNMEASURED`.** The",
        "**Instrument status: MEASURABLE; current axis verdict `PASS`.** The",
        ("m2.instrument-void-card",),
    ),
    Control(
        "hide-adverse-m2-reading",
        "diagnostic instead measures an adverse median `1.515208x` the fork's fractional box9",
        "diagnostic instead measures a favourable median `0.900000x` the fork's fractional box9",
        ("m2.adverse-residual",),
    ),
    Control(
        "drop-retained-qflat",
        "  retained median-`Q_flat<=1.00` component still protects the owner's overall",
        "  median flat power is informational only and does not protect the owner's overall",
        ("m2.disposition-qflat",),
    ),
    Control(
        "erase-m8-fail",
        M8_ROW,
        M8_ROW.replace("**FAIL** — M8-R", "**PASS** — M8-R"),
        ("integrity.m8-fail",),
    ),
    Control(
        "lower-m2-bar",
        M2_GLANCE_ROW,
        M2_GLANCE_ROW.replace("`<=1.10`", "`<=1.20`"),
        ("m2.target",),
    ),
    Control(
        "scope-reflow-benign",
        "only on that common-merge track.** Product-native results are separately publishable",
        "only on that common-merge track.** Product-native results are\nseparately publishable",
        benign=True,
    ),
    Control(
        "frequency-reflow-benign",
        "   high-frequency instrument exists in v1.7, so every current reading above",
        "   high-frequency instrument exists in v1.7, so every current\n   reading above",
        benign=True,
    ),
)


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


def git_blob(rev: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{rev}:{SCORECARD_PATH}"],
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


def mutate(source: str, control: Control) -> str:
    count = source.splitlines().count(control.anchor)
    if count != 1:
        raise RuntimeError(
            f"{control.name}: expected one full-line anchor, found {count}: "
            f"{control.anchor!r}"
        )
    candidate = source.replace(control.anchor, control.replacement, 1)
    if candidate == source:
        raise RuntimeError(f"{control.name}: mutation did not land")
    return candidate


def run_verifier(path: Path) -> tuple[int, str, set[str], set[str]]:
    completed = subprocess.run(
        [sys.executable, str(VERIFIER), "--scorecard", str(path)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout.decode("utf-8", errors="replace")
    passed = set(re.findall(r"^PASS ([^:]+):", output, flags=re.MULTILINE))
    failed = set(re.findall(r"^FAIL ([^:]+):", output, flags=re.MULTILINE))
    return completed.returncode, output, passed, failed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path)
    parser.add_argument("--scorecard-rev", default=RECONCILED_REV)
    args = parser.parse_args()

    source = (
        read_utf8(args.scorecard.resolve())
        if args.scorecard
        else git_blob(args.scorecard_rev)
    )
    temp_env = os.environ.get("TEMP")
    if not temp_env:
        raise RuntimeError("TEMP is unset")
    temp_root = Path(temp_env).resolve()
    if not temp_root.is_dir():
        raise RuntimeError(f"TEMP does not exist: {temp_root}")

    rows: list[tuple[str, str, int, str, str]] = []
    passed_controls = 0
    with tempfile.TemporaryDirectory(prefix="m160-f5-f6-f14-", dir=temp_root) as name:
        temp_dir = Path(name)
        baseline = temp_dir / "baseline.md"
        baseline.write_bytes(source.encode("utf-8"))
        base_code, base_output, base_passed, base_failed = run_verifier(baseline)
        if base_code != 0 or "VERDICT GREEN" not in base_output or base_failed:
            emit(base_output)
            raise RuntimeError(f"unexpected baseline verifier exit={base_code}")
        emit(f"BASE exit=0 checks={len(base_passed)} verdict=GREEN")

        for index, control in enumerate(CONTROLS, 1):
            candidate = mutate(source, control)
            control_dir = temp_dir / f"{index:02d}-{control.name}"
            control_dir.mkdir()
            candidate_path = control_dir / "scorecard.md"
            candidate_path.write_bytes(candidate.encode("utf-8"))
            code, output, _passed, failed = run_verifier(candidate_path)

            if control.benign:
                ok = code == 0 and not failed and "VERDICT GREEN" in output
                expected = "GREEN (benign)"
            else:
                ok = (
                    code == 1
                    and all(check_id in failed for check_id in control.expected_fail)
                )
                expected = "RED " + ",".join(control.expected_fail)

            passed_controls += int(ok)
            rows.append(
                (
                    control.name,
                    "yes",
                    code,
                    expected,
                    "PASS" if ok else "FAIL",
                )
            )
            if not ok:
                emit(f"\nCONTROL FAILURE {control.name}\n{output}")

    emit("| control | anchor found | exit code | expected check failed | verdict |")
    emit("| --- | --- | ---: | --- | --- |")
    for name, anchor_found, code, expected, verdict in rows:
        emit(f"| {name} | {anchor_found} | {code} | {expected} | {verdict} |")
    emit(f"CONTROL_SUMMARY passed={passed_controls}/{len(CONTROLS)}")
    return 0 if passed_controls == len(CONTROLS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
