#!/usr/bin/env python3
"""Fail-closed structural checks for the M166 audit report."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    experiment = Path(__file__).resolve().parent
    report = experiment.parents[1] / "docs" / "research" / (
        "M166-truth-reference-capture-audit.md"
    )
    output = experiment / "report-verification.json"
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    try:
        text = report.read_text(encoding="utf-8")
        analysis = json.loads(
            (experiment / "analysis.json").read_text(encoding="utf-8")
        )
        witness = json.loads(
            (experiment / "verification.json").read_text(encoding="utf-8")
        )

        required_fragments = [
            "VERDICT: `SOUND WITH REPAIRS`",
            "Threat 1",
            "Threat 2",
            "Threat 3",
            "Threat 4",
            "Threat 5",
            "Threat 6",
            "X'=KX",
            "reference-path",
            "2.0312030",
            "0.1230798",
            "-23.81%",
            "7.87%",
            "139.62 um",
            "37.92–48.18 um",
            "24,576",
            "Exact pre-capture repair set",
            "FATALLY FLAWED",
        ]
        for fragment in required_fragments:
            check(
                f"report contains {fragment}",
                fragment in text,
                fragment,
            )

        check(
            "analysis artifact passed",
            analysis.get("status") == "PASS",
            analysis.get("status"),
        )
        check(
            "witness verifier passed",
            witness.get("status") == "PASS"
            and witness.get("passed") == witness.get("total") == 14,
            {
                "status": witness.get("status"),
                "passed": witness.get("passed"),
                "total": witness.get("total"),
            },
        )
        check(
            "all evidence labels are present",
            all(
                label in text
                for label in (
                    "**VERIFIED BY RUNNING.**",
                    "**VERIFIED BY READING.**",
                    "**INFERRED.",
                )
            ),
            "running/reading/inferred",
        )
        check(
            "report does not claim design sound without qualification",
            "VERDICT: `DESIGN SOUND`" not in text,
            "no unqualified sound verdict",
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
