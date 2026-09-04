#!/usr/bin/env python3
"""Commission the M162 fork-provenance verifier on copies below %TEMP%."""
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
VERIFIER = Path(__file__).with_name("verify_m162_fork.py")
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"


@dataclass(frozen=True)
class Control:
    name: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False


M1_ROW = (
    "| M1 | Sharpening-safe resolved information | **UNMEASURED** | "
    "**UNMEASURED** | **UNMEASURED — blocker (d).** | **UNMEASURED** | "
    "CAND1 is killed; no admissible instrument or active bar remains, and fresh "
    "matched captures are absent. |"
)

M3_ROW = (
    "| M3 | Halo / veil | **UNMEASURED** | **UNMEASURED** | "
    "**UNMEASURED — blocker (d).** | **UNMEASURED** | VEIL2 stops the A2 build "
    "premise but does not measure M3; full-reach sites and its checker remain absent. |"
)

M8_ROW = (
    "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%`, "
    "M8-O `1.326144%` against a bar of exactly `0.0000%` | **UNMEASURED** | "
    "**UNMEASURED — blocker (d).** | **UNMEASURED** | **READ AND ADMITTED "
    "`76b3d9cc`**, superseding the prior UNMEASURED cell. Checker commissioned in "
    "both directions before the reading. M8-R is 100% attributable to the "
    "Catmull-Rom gather; bilinear gives `0/6,131,678,976` but costs 0.3404 dex of "
    "band detail. M8-O is a separate downstream failure. See "
    "`docs/research/M8-overshoot.md`. |"
)

M2_GLANCE_ROW = (
    "| M2 | Flat/defocused-ground noise | Cross-fit efficiency `<=1.10`; "
    "95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |"
)

CONTROLS = (
    Control(
        "admit-archive-to-common-merge",
        "   fork output is not an admissible common-merge arm.",
        "   fork output is an admissible common-merge arm.",
        ("fork.archive-common-inadmissible",),
    ),
    Control(
        "drop-source-commit-pin",
        "   revision, pinned by commit before scoring, with the built executable's hash frozen",
        "   revision selected after scoring without a commit pin, with the built executable's hash frozen",
        ("fork.rebuild-required-set",),
    ),
    Control(
        "freeze-executable-after-render",
        "this track. The fork's built-executable hash must be frozen before rendering. Helicon",
        "this track. The fork's built-executable hash may be recorded after rendering. Helicon",
        ("fork.rebuild-executable-pre-frozen",),
    ),
    Control(
        "blank-one-fork-cell",
        M1_ROW,
        M1_ROW.replace("**UNMEASURED — blocker (d).**", ""),
        ("fork.column-status-count", "fork.column-no-blank"),
    ),
    Control(
        "erase-developed-input-defect",
        "  artifact used `105` Lightroom-developed TIFFs, has no producing binary or source",
        "  artifact used the common-input TIFFs and has no producing binary or source",
        ("fork.archive-developed-input",),
    ),
    Control(
        "claim-bound-producer",
        "  revision bound to the render, and is not reproducible. The retained May 17",
        "  revision bound to the render, and is reproducible. The retained May 17",
        ("fork.archive-no-bound-producer",),
    ),
    Control(
        "mark-fork-cell-pass",
        M3_ROW,
        M3_ROW.replace("**UNMEASURED — blocker (d).**", "**PASS**"),
        ("fork.column-status-count", "fork.column-status-token"),
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
        ("integrity.m2-glance-row",),
    ),
    Control(
        "commit-pin-reflow-benign",
        "   revision, pinned by commit before scoring, with the built executable's hash frozen",
        "   revision, pinned by commit before scoring, with the built\n"
        "   executable's hash frozen",
        benign=True,
    ),
    Control(
        "archive-reason-reflow-benign",
        "  artifact used `105` Lightroom-developed TIFFs, has no producing binary or source",
        "  artifact used `105` Lightroom-developed TIFFs, has no producing\n"
        "  binary or source",
        benign=True,
    ),
)


def emit(message: str) -> None:
    sys.stdout.buffer.write((message + "\n").encode("utf-8"))


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8").replace("\r\n", "\n")


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
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    args = parser.parse_args()

    source = read_utf8(args.scorecard.resolve())
    temp_env = os.environ.get("TEMP")
    if not temp_env:
        raise RuntimeError("TEMP is unset")
    temp_root = Path(temp_env).resolve()
    if not temp_root.is_dir():
        raise RuntimeError(f"TEMP does not exist: {temp_root}")

    rows: list[tuple[str, str, int, str, str]] = []
    passed_controls = 0
    with tempfile.TemporaryDirectory(prefix="m160-m162-fork-", dir=temp_root) as name:
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
