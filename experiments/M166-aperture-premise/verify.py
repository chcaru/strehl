#!/usr/bin/env python3
"""Check that M166's report says no more than its stored evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
STREHL = HERE.parents[1]
REPORT = STREHL / "docs/research/M166-aperture-premise.md"
OUT = HERE / "verification.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    analysis_path = HERE / "analysis.json"
    readonly_path = HERE / "readonly-verification.json"
    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    readonly = json.loads(readonly_path.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")

    diagonal = analysis["coverage"]["diagonal"]["f5.6_span_over_f11_span"]
    horizontal = analysis["coverage"]["horizontal"]["f5.6_span_over_f11_span"]
    peak_spread = analysis["focus_step"]["pixel_peak_coordinate_spread"]
    reward = analysis["identifiability_witness"]["sharpening_reward_ratio"][0]
    controls = analysis["raggedness"]["subject_contamination_control"]
    photo = analysis["exposure_and_count"][
        "f5.6_over_f11_total_capture_photon_proxy"
    ]
    rise = analysis["raggedness"]["smooth_edge_f11_over_f5.6_rise"]

    checks = {
        "V1_analysis_passes": analysis["status"] == "PASS",
        "V2_capture_tree_unchanged": readonly["status"] == "PASS",
        "V3_verdict_is_not_forced": (
            "**Status: COMPLETE. Verdict: `NOT FORCED`.**" in report
        ),
        "V4_exact_two_world_identity_reported": (
            "K H_i X = H_i K X" in report
            and analysis["identifiability_witness"][
                "maximum_absolute_output_difference"
            ]
            == 0.0
        ),
        "V5_sharpening_reward_not_promoted_to_pass": (
            f"`{reward:.9f}x`" in report
            and "FATAL COUNTEREXAMPLE" in report
        ),
        "V6_focus_threat_rejected": (
            "fixed absolute focus step" in report.lower()
            and "NOT FOUND" in report
            and peak_spread < 1e-12
        ),
        "V7_coverage_mismatch_reported": (
            f"`{100.0 * diagonal:.2f}%`" in report
            and f"`{100.0 * horizontal:.2f}%`" in report
            and diagonal < 0.99
            and horizontal < 0.99
        ),
        "V8_tc_is_not_doubled": (
            "already folded" in report
            and analysis["checks"]["C8_teleconverter_is_folded_into_exif"]
        ),
        "V9_subject_control_failure_reported": (
            controls["status"] == "FAIL"
            and "1/15" in report
            and "359.770%" in report
        ),
        "V10_smooth_edge_reversal_reported": (
            f"`{rise['isotonic_measured']:.5f}`" in report
            and f"`{rise['erf_measured']:.5f}`" in report
            and rise["isotonic_measured"] < 1.0
            and rise["erf_measured"] < 1.0
        ),
        "V11_photon_proxy_is_caveated": (
            f"`{photo['diagonal']:.3f}x`" in report
            and f"`{photo['horizontal']:.3f}x`" in report
            and "not asserted as a per-output-pixel" in report
        ),
        "V12_no_new_capture_decode_claim": (
            analysis["captures_opened_by_analysis_script"] == 0
            and "pixel evidence below comes from already-existing M128 artifacts"
            in report
        ),
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    result = {
        "schema": "strehl.m166.aperture-premise-verification.v1",
        "status": status,
        "checks": checks,
        "inputs": {
            "analysis_sha256": sha256(analysis_path),
            "readonly_verification_sha256": sha256(readonly_path),
            "report_sha256": sha256(REPORT),
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"{status}: {sum(checks.values())}/{len(checks)} report checks")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        failure = {
            "schema": "strehl.m166.aperture-premise-verification.v1",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }
        try:
            OUT.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        except BaseException:
            pass
        print(f"FAIL: {failure['error']}")
        raise SystemExit(1)
