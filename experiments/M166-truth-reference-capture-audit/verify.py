#!/usr/bin/env python3
"""Fail-closed verifier for the M166 analytical audit artifact."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    analysis_path = root / "analysis.json"
    output_path = root / "verification.json"
    checks: list[dict[str, object]] = []

    def check(name: str, condition: bool, detail: object) -> None:
        checks.append(
            {"name": name, "passed": bool(condition), "detail": detail}
        )

    try:
        data = json.loads(analysis_path.read_text(encoding="utf-8"))
        gauge = data["absolute_scene_gauge"]
        sampling = data["sampling"]
        packing = data["target_packing"]
        rank = data["rank_contract"]
        focus = data["fixed_focus_coverage"]
        correlated = data["correlated_reference_error"]

        check("analysis status", data["status"] == "PASS", data["status"])
        check(
            "gauge preserves reference",
            gauge["reference_observation_max_error"] < 1e-12,
            gauge["reference_observation_max_error"],
        )
        check(
            "gauge preserves every output",
            max(gauge["output_observation_max_errors"]) < 1e-12,
            gauge["output_observation_max_errors"],
        )
        check(
            "relative transfer gate passes both worlds",
            gauge["both_worlds_reference_stronger"],
            {
                "world_a": gauge[
                    "observed_output_to_reference_ratios_a"
                ],
                "world_b": gauge[
                    "observed_output_to_reference_ratios_b"
                ],
            },
        )
        check(
            "licensed band is far below reference Nyquist",
            sampling["licensed_frequency_reference_cyc_px"] < 0.125,
            sampling["licensed_frequency_reference_cyc_px"],
        )
        check(
            "M147 nominal lower bound clears 2x",
            sampling["m147_nominal_lower"] >= 2.0,
            sampling["m147_nominal_lower"],
        )
        check(
            "1.30 target does not fit eight guarded rows",
            packing["eight_rows_mm_at_1_30"] > 8.0,
            packing["eight_rows_mm_at_1_30"],
        )
        check(
            "1.32 target barely fits eight guarded rows",
            packing["eight_rows_mm_at_1_32"] <= 8.0,
            packing["eight_rows_mm_at_1_32"],
        )
        check(
            "64 macro rows limit unspecified feature dimensions",
            rank["largest_dimension_if_each_macro_site_is_one_row"] == 42,
            rank["largest_dimension_if_each_macro_site_is_one_row"],
        )
        check(
            "full 128-square support needs explicit micro-sites",
            rank["rows_required_for_full_128_by_128_output"] == 24576,
            rank["rows_required_for_full_128_by_128_output"],
        )
        check(
            "three strips are not guaranteed on short axis",
            focus["strips_needed_two_pixel_short_axis_range"][1] >= 4,
            focus["strips_needed_two_pixel_short_axis_range"],
        )
        check(
            "long-axis tilt needs more than three strips",
            focus["strips_needed_two_pixel_long_axis_range"][0] > 3,
            focus["strips_needed_two_pixel_long_axis_range"],
        )
        check(
            "common reference error materially biases transfer",
            abs(correlated["relative_transfer_bias_percent"]) > 20.0,
            correlated["relative_transfer_bias_percent"],
        )
        check(
            "shared error can inflate squared correlation",
            correlated["squared_correlation_change_percent"] > 0.0,
            correlated["squared_correlation_change_percent"],
        )

        passed = sum(1 for item in checks if item["passed"])
        result = {
            "status": "PASS" if passed == len(checks) else "FAIL",
            "passed": passed,
            "total": len(checks),
            "checks": checks,
        }
        output_path.write_text(
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
            output_path.write_text(
                json.dumps(failure, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except Exception:
            pass
        print(f"FAIL: {failure['error']}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
