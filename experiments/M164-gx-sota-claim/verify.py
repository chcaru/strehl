"""Verify the M164 GX claim audit and its red canary."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
AUDIT = HERE / "audit.py"
COMMITTED = HERE / "audit.json"
REGENERATED = HERE / ".verify-regenerated.json"
RED = HERE / ".verify-red.json"
ROOT = HERE.parents[1]
PLAN = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
REPORT = ROOT / "docs" / "research" / "M164-gx-sota-claim.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def run_audit(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AUDIT), *arguments],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    checks: dict[str, bool] = {}
    try:
        generated = run_audit("--output", str(REGENERATED))
        checks["generator_passes"] = (
            generated.returncode == 0
            and generated.stdout.startswith("PASS: 12/12 checks")
        )
        checks["artifact_is_byte_identical"] = (
            REGENERATED.exists()
            and COMMITTED.exists()
            and REGENERATED.read_bytes() == COMMITTED.read_bytes()
        )
        artifact = json.loads(COMMITTED.read_text(encoding="utf-8"))
        checks["source_hashes_match"] = (
            artifact["source"]["audit_py_sha256"] == digest(AUDIT)
            and artifact["source"]["plan_sha256"] == digest(PLAN)
            and artifact["source"]["scorecard_sha256"] == digest(SCORECARD)
            and artifact["source"]["report_sha256"] == digest(REPORT)
        )
        dependency = artifact["scorecard_section_3_1"]
        checks["seven_explicit_d_axes_are_exact"] = (
            dependency["explicit_blocker_d_axes"]
            == ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]
            and dependency["explicit_blocker_d_count"] == 7
        )
        checks["m11_is_eighth_semantic_dependency"] = (
            dependency["semantic_comparator_axes"]
            == ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M11"]
        )
        checks["gx_removes_zero_comparator_dependencies"] = (
            dependency["gx_removed_explicit_blocker_d_axes"] == []
        )
        checks["claim_is_explicitly_reference_conditional"] = all(
            phrase in artifact["claim"]
            for phrase in (
                "recoverable covariance information about GX",
                "not a claim to recover absolute object detail",
                "licensed Zerene Stacker PMax",
                "licensed Zerene Stacker DMap",
                "commit-pinned best-known-source fork",
            )
        )

        red = run_audit(
            "--plant-defect",
            "drop-m7",
            "--output",
            str(RED),
        )
        red_artifact = json.loads(RED.read_text(encoding="utf-8"))
        failed = [
            name
            for name, passed in red_artifact["checks"].items()
            if not passed
        ]
        checks["red_canary_has_nonzero_exit"] = (
            red.returncode == 1
            and red.stdout.startswith("FAIL: 8/12 checks")
        )
        checks["red_canary_is_targeted"] = failed == [
            "C4_exactly_seven_rows_explicitly_carry_d",
            "C5_explicit_d_rows_are_M1_through_M7",
            "C6_M11_has_untagged_semantic_comparator_dependency",
            "C8_GX_scope_removes_no_explicit_d_dependency",
        ]
    finally:
        REGENERATED.unlink(missing_ok=True)
        RED.unlink(missing_ok=True)

    passed = sum(checks.values())
    total = len(checks)
    for name, result in checks.items():
        if not result:
            print(f"FAIL: {name}")
    label = "PASS" if passed == total else "RED"
    print(
        f"TOTAL: {label} {passed}/{total} passed; "
        f"{total - passed} failed; 0 skipped"
    )
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
