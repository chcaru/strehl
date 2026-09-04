#!/usr/bin/env python3
"""Fail-closed verification for the M166 physical capture calculation."""

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
        target = data["target"]
        strips = data["focus_strips"]
        frames = data["frame_count"]
        transfer = data["diffraction_only_transfer"]

        check(
            "analysis status",
            data["status"] == "PASS",
            data["status"],
        )
        check(
            "target remains 1.32x",
            target["decision"] == "TARGET HOLDS AT 1.32x",
            target["decision"],
        )
        check(
            "target ratio exceeds hard-max ratio",
            target["ratio_at_target"] > target["ratio_at_hard_max"] > 2.0,
            {
                "target": target["ratio_at_target"],
                "hard_max": target["ratio_at_hard_max"],
            },
        )
        check(
            "tolerance-compensated panel fits",
            target["tolerance_compensated_max_height_mm"]
            <= target["panel_height_limit_mm"],
            {
                "height": target[
                    "tolerance_compensated_max_height_mm"
                ],
                "limit": target["panel_height_limit_mm"],
            },
        )
        check(
            "reference admits two rows per strip",
            strips["reference_rows_per_strip"] == 2,
            strips["reference_rows_per_strip"],
        )
        check(
            "scored witness admits three rows without pupil assumption",
            strips["scored_rows_per_strip"] == 3,
            strips["scored_rows_per_strip"],
        )
        check(
            "exact reference strip count is four",
            strips["reference_strip_count"] == 4,
            strips["reference_strip_count"],
        )
        check(
            "exact scored witness strip count is three",
            strips["scored_witness_strip_count"] == 3,
            strips["scored_witness_strip_count"],
        )
        check(
            "scored witness costs 96 frames",
            frames["scored_path_witness"] == 96,
            frames["scored_path_witness"],
        )
        check(
            "held-out validation costs 128 frames",
            frames["held_out_flat_dark_validation"] == 128,
            frames["held_out_flat_dark_validation"],
        )
        check(
            "revised session is 1147 frames",
            frames["revised_session"] == 1147,
            frames["revised_session"],
        )
        check(
            "diffraction predicts positive transfer ratio",
            transfer["minimum_conservative_ratio"] > 1.0,
            transfer["minimum_conservative_ratio"],
        )
        check(
            "diffraction does not support ratio above two",
            transfer["maximum_conservative_ratio"] < 2.0,
            transfer["maximum_conservative_ratio"],
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
