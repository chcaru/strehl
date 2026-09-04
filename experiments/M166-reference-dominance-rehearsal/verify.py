#!/usr/bin/env python3
"""Fail-closed verification for M166 rehearsal frame accounting."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    source = root / "analysis.json"
    output = root / "verification.json"
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        correction = data["formal_witness_correction"]
        score = data["score"]
        rehearsal = data["rehearsal"]

        check("analysis status", data["status"] == "PASS", data["status"])
        check(
            "headline count",
            data["headline"] == "REHEARSAL SPECIFIED: 1,092 frames",
            data["headline"],
        )
        check(
            "complete witness is 164 frames",
            correction["complete_scored_path_witness"] == 164,
            correction["complete_scored_path_witness"],
        )
        check(
            "witness correction is 68 frames",
            correction["difference"] == 68,
            correction["difference"],
        )
        check(
            "prior score reconstruction is 1147",
            score["stale_1147_total"] == 1147,
            score["stale_1147_total"],
        )
        check(
            "corrected combined score is 1215",
            score["corrected_combined_score"] == 1215,
            score["corrected_combined_score"],
        )
        check(
            "converter-on rehearsal subtotal is 320",
            rehearsal["converter_on_total"] == 320,
            rehearsal["converter_on_total"],
        )
        check(
            "TC0 rehearsal subtotal is 772",
            rehearsal["tc0_total"] == 772,
            rehearsal["tc0_total"],
        )
        check(
            "registered rehearsal is 1092",
            rehearsal["registered_frames"] == 1092,
            rehearsal["registered_frames"],
        )
        check(
            "rehearsal is M1-only score plus controls",
            rehearsal["registered_frames"]
            == score["m1_only_score"] + rehearsal["physical_control_frames"],
            {
                "rehearsal": rehearsal["registered_frames"],
                "m1_only_score": score["m1_only_score"],
                "controls": rehearsal["physical_control_frames"],
            },
        )
        check(
            "full-dress rehearsal is 1407",
            rehearsal["full_dress_with_unrelated_combined_inputs"] == 1407,
            rehearsal["full_dress_with_unrelated_combined_inputs"],
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
