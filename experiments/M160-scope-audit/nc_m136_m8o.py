#!/usr/bin/env python3
"""Commission the M136 M8-O verifier on UTF-8 copies below %TEMP%."""
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
VERIFIER = Path(__file__).with_name("verify_m136_m8o.py")
SCORECARD = ROOT / "docs/proposals/2026-09-sota-scorecard.md"
DIAGNOSTIC_COUNT = "31" + ",148"


@dataclass(frozen=True)
class Control:
    name: str
    anchor: str
    replacement: str
    expected_fail: tuple[str, ...] = ()
    benign: bool = False


SUPERSEDED_LINE = (
    "> **M8-O v1.4 superseded figure:** `1.326144%` was read against the v1.4 "
    "bar, which has been shown impossible as written; see "
    "`docs/research/M136-m8o-bar.md` (commit `7befe55c`)."
)

M8_RESULT_ROW = (
    "| M8 | Independent source-hull census | **FAIL** — M8-R `1.030569%` against "
    "the achievable bar of exactly `0.0000%`; M8-O v1.5 **UNMEASURED** because "
    "the corrected checker at `e5489d64` has not been recommissioned. Historical "
    "M8-O v1.4 `1.326144%` is **SUPERSEDED** because that bar was impossible as "
    "written. | **UNMEASURED** | **UNMEASURED — blocker (d).** | "
    "**UNMEASURED** | **M8-R READ AND ADMITTED `76b3d9cc`.** M8-R is the only "
    "produced-and-read score against an achievable bar and remains a genuine "
    "axis-level failure. It is 100% attributable to the Catmull-Rom gather; "
    "bilinear gives `0/6,131,678,976` but costs 0.3404 dex of band detail. Under "
    "the repaired M8-O v1.5 predicate, clean bilinear measures `0/74,173,536`, "
    "independently zero in R, G, and B; this proves the bar discriminates but is "
    "not a v1.5 candidate score. |"
)

M8_READINESS_ROW = (
    "| M8 | **(e) for M8-R; M8-O v1.5 `UNMEASURED`** | **M8 remains `FAIL`: "
    "M8-R is `1.030569%` against the achievable `0.0000%` bar.** M8-R is the "
    "only produced-and-read score against an achievable bar. The historical "
    "M8-O v1.4 `1.326144%` figure is superseded because its bar was impossible "
    "as written; the corrected v1.5 checker at `e5489d64` has not been "
    "recommissioned, so no v1.5 M8-O score exists. |"
)

CONTROLS = (
    Control(
        "soften-m8-axis-verdict",
        M8_RESULT_ROW,
        M8_RESULT_ROW.replace("**FAIL** — M8-R", "**UNMEASURED** — M8-R"),
        ("m8.axis-fail",),
    ),
    Control(
        "make-readiness-v15-pass",
        M8_READINESS_ROW,
        M8_READINESS_ROW.replace(
            "M8-O v1.5 `UNMEASURED`", "M8-O v1.5 `PASS`"
        ),
        ("m8.v15-unmeasured-readiness",),
    ),
    Control(
        "make-result-v15-fail",
        M8_RESULT_ROW,
        M8_RESULT_ROW.replace(
            "M8-O v1.5 **UNMEASURED**", "M8-O v1.5 **FAIL**"
        ),
        ("m8.v15-unmeasured-result",),
    ),
    Control(
        "restore-v14-failure",
        SUPERSEDED_LINE,
        "> **M8-O v1.4 active failure:** `1.326144%` failed a valid v1.4 bar.",
        ("m8.superseded-line",),
    ),
    Control(
        "claim-v15-recommissioned",
        "> **Status: `UNMEASURED`.** The replacement checker was corrected at `e5489d64`",
        "> **Status: `PASS`.** The replacement checker at `e5489d64` was recommissioned",
        ("m8.v15-unmeasured-card",),
    ),
    Control(
        "promote-diagnostic-count",
        "> the shipping Catmull-Rom kernel does not clear the diagnostic reanalysis. The",
        f"> the shipping Catmull-Rom kernel has a promoted score of "
        f"`{DIAGNOSTIC_COUNT}` violations. The",
        ("m8.no-diagnostic-count",),
    ),
    Control(
        "break-bilinear-zero",
        "> bilinear kernel measures exactly `0/74,173,536`, independently zero in R, G,",
        "> bilinear kernel measures exactly `1/74,173,536`, independently zero in R, G,",
        ("m8.bilinear-zero-card",),
    ),
    Control(
        "erase-channel-independence",
        "> and B (`experiments/M136-m8o-bar/analysis.json`, `bilinear_aggregate`), while",
        "> only in aggregate (`experiments/M136-m8o-bar/analysis.json`, `bilinear_aggregate`), while",
        ("m8.bilinear-channels-card",),
    ),
    Control(
        "restore-only-axis-claim",
        "> is the only produced-and-read score against an achievable bar.",
        "> makes M8 the only axis in the program with a produced-and-read score.",
        ("m8.only-r-produced-read-card", "m8.no-old-only-axis-claim"),
    ),
    Control(
        "erase-impossibility-population",
        "> `[0,1]`. At `977,684` required census coordinates the hull has",
        "> `[0,1]`. At `0` required census coordinates the hull has",
        ("m8.v14-impossibility-count",),
    ),
    Control(
        "status-reflow-benign",
        "> **Status: `UNMEASURED`.** The replacement checker was corrected at `e5489d64`",
        "> **Status: `UNMEASURED`.** The replacement checker was\n"
        "> corrected at `e5489d64`",
        benign=True,
    ),
    Control(
        "bilinear-reflow-benign",
        "> bilinear kernel measures exactly `0/74,173,536`, independently zero in R, G,",
        "> bilinear kernel measures exactly `0/74,173,536`, independently\n"
        "> zero in R, G,",
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
    with tempfile.TemporaryDirectory(prefix="m160-m136-m8o-", dir=temp_root) as name:
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
