#!/usr/bin/env python3
"""Commission every M160 reconciliation check on UTF-8 copies below %TEMP%."""
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
VERIFIER = Path(__file__).with_name("verify_reconciliation.py")
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"


@dataclass(frozen=True)
class Control:
    name: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False
    operation: str = "replace"
    following: str | None = None


M4_JOINT_ROW = (
    "| M1 information + M2 noise + M8 hull + retained M4 flat-power component | "
    "Harder averaging can lower noise by losing information; sharpening can flatter "
    "transfer while increasing flat power or leaving the source hull. | M1 presently "
    "has no admissible statistic. When it is replaced, publish the replacement detail "
    "value with `(eta, Q_flat, M8-R, M8-O)` from the same output bytes and settings. "
    "That output must pass M1, M2, and M8 and must have median `Q_flat<=1.00`. This "
    "retained M4 component is only the flat-power tell; M4's failed-site rate, "
    "ghost-ratio, and comparator bars remain mandatory disclosures and do not gate "
    "the owner's verdict. Until M1 is admitted, neither a noise-only nor a detail "
    "claim is valid. |"
)

M12_JOINT_ROW = (
    "| M11 runtime + retained M12 cross-worker byte identity | Serial execution can "
    "buy determinism by abandoning the speed claim, while worker-dependent output can "
    "make the fast arm a different product. | The primary CPU result is the 16-worker "
    "output and must meet M11. On the same fixed-width input, the outputs at 1, 2, 4, "
    "8, and 16 workers must be mutually byte-identical. That cross-worker ladder is "
    "the only M12-derived publication-gate component; M12's fixed-worker repeat, "
    "memory, N-scaling, and N-mod-4 bars remain mandatory disclosures. |"
)

M8_SCOREBOARD_ROW = (
    "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%`, "
    "M8-O `1.326144%` against a bar of exactly `0.0000%` | **UNMEASURED** | "
    "**UNMEASURED** | **UNMEASURED** | **READ AND ADMITTED `76b3d9cc`**, "
    "superseding the prior UNMEASURED cell. Checker commissioned in both directions "
    "before the reading. M8-R is 100% attributable to the Catmull-Rom gather; "
    "bilinear gives `0/6,131,678,976` but costs 0.3404 dex of band detail. M8-O is a "
    "separate downstream failure. See `docs/research/M8-overshoot.md`. |"
)

M2_GLANCE_ROW = (
    "| M2 | Noise efficiency at matched information | Cross-fit efficiency `<=1.10`; "
    "95% upper bound of strehl / quietest qualifying comparator `<=0.950`. |"
)

SCOREBOARD_HEADER = (
    "| ID | Metric | strehl | Zerene Stacker (PMax + DMap) | "
    "Fork (frozen best-known build) | Helicon Focus (when obtainable) | "
    "Current standing |"
)

CONTROLS = (
    Control(
        "remandate-unnamed-axis",
        "   and `M12` are mandatory disclosures, not independent publication gates: every",
        "   and `M12` are hard publication gates alongside the seven owner gates: every",
        expected_fail=("gate.disclosure-split",),
    ),
    Control(
        "delete-m4-anti-cheat-component",
        M4_JOINT_ROW,
        M4_JOINT_ROW.replace(
            " and must have median `Q_flat<=1.00`",
            " and reports median `Q_flat` without a required value",
        ),
        expected_fail=("anti.m4-flat-power-component",),
    ),
    Control(
        "delete-m12-anti-cheat-component",
        M12_JOINT_ROW,
        M12_JOINT_ROW.replace(
            "must be mutually byte-identical",
            "need not be mutually byte-identical",
        ),
        expected_fail=("anti.m12-cross-worker-component",),
    ),
    Control(
        "drop-fork-from-common-input",
        "5. Licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, the fork at its frozen",
        (
            "5. Licensed Zerene Stacker PMax, licensed Zerene Stacker DMap, and strehl must\n"
            "   receive the exact same TIFF bytes. Helicon"
        ),
        expected_fail=("comparator.common-input-required-set",),
        following="   best-known build, and strehl must receive the exact same TIFF bytes. Helicon",
    ),
    Control(
        "make-helicon-mandatory",
        "   never a reason for `UNMEASURED`.",
        "   instead makes the run `UNMEASURED`.",
        expected_fail=("gate.helicon-not-unmeasured",),
    ),
    Control(
        "drop-fork-binary-hash",
        "  compiler flags, final binary SHA-256, and a complete settings manifest. Select that",
        "  compiler flags and a complete settings manifest. Select that",
        expected_fail=("comparator.fork-freeze-protocol",),
    ),
    Control(
        "drop-fork-scoreboard-column",
        SCOREBOARD_HEADER,
        (
            "| ID | Metric | strehl | Zerene Stacker (PMax + DMap) | "
            "Helicon Focus (when obtainable) | Current standing |"
        ),
        expected_fail=("comparator.scoreboard-schema",),
    ),
    Control(
        "collapse-disclosure-miss-into-pass",
        "  This state is **neither `PASS` nor `FAIL`**. The verdict headline and every public",
        "  This state is a `PASS`. The verdict headline and every public",
        expected_fail=("gate.disclosure-miss-distinct",),
    ),
    Control(
        "retract-m8-fail",
        M8_SCOREBOARD_ROW,
        M8_SCOREBOARD_ROW.replace("**FAIL** — M8-R", "**PASS** — M8-R"),
        expected_fail=("integrity.m8-fail-preserved",),
    ),
    Control(
        "lower-m2-comparator-bar",
        M2_GLANCE_ROW,
        M2_GLANCE_ROW.replace("`<=0.950`", "`<=0.990`"),
        expected_fail=("integrity.at-glance-bars-unchanged",),
    ),
    Control(
        "benign-required-set-rewrap",
        "   Stacker DMap, and the fork at its frozen best-known build. Helicon Methods A, B,",
        (
            "   Stacker DMap, and the fork at its frozen best-known build.\n"
            "   Helicon Methods A, B,"
        ),
        benign=True,
    ),
    Control(
        "benign-disclosure-role-paragraph-break",
        "**Publication role: MANDATORY DISCLOSURE.** Full M5 must be measured and published;",
        "",
        benign=True,
        operation="insert_blank",
    ),
)


def read_utf8(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def emit(text: str) -> None:
    print(text.encode("ascii", errors="replace").decode("ascii"))


def mutate(text: str, control: Control) -> str:
    lines = text.splitlines()
    hits = [index for index, line in enumerate(lines) if line == control.anchor]
    if len(hits) != 1:
        raise RuntimeError(
            f"{control.name}: anchor count={len(hits)}, expected exactly 1: "
            f"{control.anchor!r}"
        )
    index = hits[0]
    replacement = control.replacement.splitlines()
    if control.operation == "replace":
        consumed = 1
        if control.following is not None:
            if index + 1 >= len(lines) or lines[index + 1] != control.following:
                actual = lines[index + 1] if index + 1 < len(lines) else "<EOF>"
                raise RuntimeError(
                    f"{control.name}: following anchor mismatch: {actual!r}"
                )
            consumed = 2
        lines[index : index + consumed] = replacement
    elif control.operation == "insert_after":
        lines[index + 1 : index + 1] = replacement
    elif control.operation == "insert_blank":
        lines[index + 1 : index + 1] = [""]
    else:
        raise RuntimeError(f"{control.name}: unsupported operation={control.operation!r}")
    candidate = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    if candidate == text:
        raise RuntimeError(f"{control.name}: mutation was inert")
    return candidate


def run_verifier(scorecard: Path) -> tuple[int, str, set[str], set[str]]:
    completed = subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scorecard", type=Path, default=SCORECARD)
    args = parser.parse_args()

    scorecard = read_utf8(args.scorecard.resolve())
    temp_env = os.environ.get("TEMP")
    if not temp_env:
        raise RuntimeError("TEMP is unset")
    temp_root = Path(temp_env).resolve()
    if not temp_root.is_dir():
        raise RuntimeError(f"TEMP does not exist: {temp_root}")

    rows: list[tuple[str, str, int, str, str]] = []
    passed_controls = 0
    with tempfile.TemporaryDirectory(prefix="m160-reconciliation-", dir=temp_root) as name:
        temp_dir = Path(name)
        baseline = temp_dir / "baseline.md"
        baseline.write_bytes(scorecard.encode("utf-8"))
        base_code, base_output, base_passed, base_failed = run_verifier(baseline)
        if base_code != 0 or "VERDICT GREEN" not in base_output or base_failed:
            emit(base_output)
            raise RuntimeError(f"unexpected baseline verifier exit={base_code}")
        print(f"BASE exit=0 checks={len(base_passed)} verdict=GREEN")

        for index, control in enumerate(CONTROLS, 1):
            candidate = mutate(scorecard, control)
            control_dir = temp_dir / f"{index:02d}-{control.name}"
            control_dir.mkdir()
            candidate_path = control_dir / "scorecard.md"
            candidate_path.write_bytes(candidate.encode("utf-8"))
            code, output, passed, failed = run_verifier(candidate_path)

            if control.benign:
                ok = code == 0 and not failed and "VERDICT GREEN" in output
                expected = "GREEN (benign)"
            else:
                ok = code == 1 and all(check_id in failed for check_id in control.expected_fail)
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

    print("| control | anchor found | exit code | expected | verdict |")
    print("| --- | --- | ---: | --- | --- |")
    for name, anchor_found, code, expected, verdict in rows:
        print(f"| {name} | {anchor_found} | {code} | {expected} | {verdict} |")
    print(f"CONTROL_SUMMARY passed={passed_controls}/{len(CONTROLS)}")
    return 0 if passed_controls == len(CONTROLS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
