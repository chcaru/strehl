#!/usr/bin/env python3
"""Fail-closed structural checks for the M166 physical protocol report."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    report_path = root.parents[1] / "docs" / "research" / (
        "M166-reference-information-dominance-physical.md"
    )
    output = root / "report-verification.json"
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    try:
        report = report_path.read_text(encoding="utf-8")
        analysis = json.loads(
            (root / "analysis.json").read_text(encoding="utf-8")
        )
        witness = json.loads(
            (root / "verification.json").read_text(encoding="utf-8")
        )

        required = [
            "TARGET HOLDS AT 1.32x",
            "EXACT REFERENCE COUNT: `4`",
            "EXACT SCORED-WITNESS COUNT: `3`",
            "3 strips x (16 A + 16 B) = 96 frames",
            "revised registered session",
            "**`1,147`**",
            "`1,148` shutter releases",
            "does **not** require `delta_H,k > 1`",
            "`1.03405`",
            "`1.10985`",
            "No existing archive frame",
            "PASTE-READY TEXT FOLLOWS",
            "TC0-DOM-S01-R01-03",
            "TR-S04-R07-08",
            "same uninterrupted",
        ]
        for fragment in required:
            check(
                f"report contains {fragment}",
                fragment in report,
                fragment,
            )

        check(
            "analysis passed",
            analysis.get("status") == "PASS",
            analysis.get("status"),
        )
        check(
            "calculation verifier passed",
            witness.get("status") == "PASS"
            and witness.get("passed") == witness.get("total") == 13,
            {
                "status": witness.get("status"),
                "passed": witness.get("passed"),
                "total": witness.get("total"),
            },
        )
        check(
            "owner text retains no-shoot gate",
            "Do not begin the scored session" in report,
            "blocking owner text",
        )
        check(
            "all evidence label classes present",
            all(
                label in report
                for label in (
                    "**VERIFIED BY RUNNING.**",
                    "**VERIFIED BY READING.**",
                    "**INFERRED.",
                )
            ),
            "running/reading/inferred",
        )

        passed = sum(1 for item in checks if item["passed"])
        result = {
            "status": "PASS" if passed == len(checks) else "FAIL",
            "passed": passed,
            "total": len(checks),
            "checks": checks,
        }
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"{result['status']}: {passed}/{len(checks)} checks")
        return 0 if result["status"] == "PASS" else 1
    except Exception as exc:
        failure = {
            "status": "FAIL",
            "passed": 0,
            "total": len(checks),
            "checks": checks,
            "error": f"{type(exc).__name__}: {exc}",
        }
        try:
            output.write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        print(f"FAIL: {failure['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
