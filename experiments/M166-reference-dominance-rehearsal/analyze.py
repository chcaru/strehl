#!/usr/bin/env python3
"""Deterministic frame accounting for the M166 dominance rehearsal."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def build_analysis() -> dict[str, object]:
    current_combined_score = 891
    reference_increment = 32
    held_out_validation = 128
    old_fixed_focus_witness = 96
    complete_scored_path_witness = 2 * 55 + 2 * 27

    stale_score = (
        current_combined_score
        + reference_increment
        + held_out_validation
        + old_fixed_focus_witness
    )
    corrected_score = (
        current_combined_score
        + reference_increment
        + held_out_validation
        + complete_scored_path_witness
    )

    converter_on = {
        "ab_calibration": 128,
        "four_reference_strips": 128,
        "held_out_validation": 64,
    }
    tc0 = {
        "ab_calibration": 128,
        "candidate_independent_dominance_witness": (
            complete_scored_path_witness
        ),
        "candidate_input_stacks": 164,
        "candidate_reset_start_end_witnesses": 60,
        "sharp_physical_control": 96,
        "blur_physical_control": 96,
        "held_out_validation": 64,
    }

    converter_on_total = sum(converter_on.values())
    tc0_total = sum(tc0.values())
    rehearsal_registered = converter_on_total + tc0_total
    physical_controls = (
        tc0["sharp_physical_control"] + tc0["blur_physical_control"]
    )
    unrelated_combined_inputs = 315
    full_dress_rehearsal = rehearsal_registered + unrelated_combined_inputs

    return {
        "status": "PASS",
        "headline": "REHEARSAL SPECIFIED: 1,092 frames",
        "formal_witness_correction": {
            "old_fixed_focus_witness": old_fixed_focus_witness,
            "complete_scored_path_witness": (
                complete_scored_path_witness
            ),
            "difference": (
                complete_scored_path_witness - old_fixed_focus_witness
            ),
            "required_blocks": {
                "TC0-DOM-sw4-A": 55,
                "TC0-DOM-sw4-B": 55,
                "TC0-DOM-sw10-A": 27,
                "TC0-DOM-sw10-B": 27,
            },
        },
        "score": {
            "current_891_baseline": current_combined_score,
            "stale_1147_total": stale_score,
            "corrected_combined_score": corrected_score,
            "correction_from_1147": corrected_score - stale_score,
            "m1_only_score": corrected_score - unrelated_combined_inputs,
        },
        "rehearsal": {
            "converter_on": converter_on,
            "converter_on_total": converter_on_total,
            "tc0": tc0,
            "tc0_total": tc0_total,
            "registered_frames": rehearsal_registered,
            "histogram_setup_frames": 1,
            "shutter_releases_in_sitting": rehearsal_registered + 1,
            "m147_preflight_frames_outside_sitting": 2,
            "difference_from_corrected_score": (
                rehearsal_registered - corrected_score
            ),
            "difference_from_stale_1147": (
                rehearsal_registered - stale_score
            ),
            "full_dress_with_unrelated_combined_inputs": (
                full_dress_rehearsal
            ),
            "unrelated_combined_inputs_omitted": unrelated_combined_inputs,
            "physical_control_frames": physical_controls,
        },
    }


def main() -> int:
    output_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).with_name("analysis.json")
    )
    try:
        result = build_analysis()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"PASS: wrote {output_path}")
        return 0
    except Exception as exc:
        failure = {"status": "FAIL", "error": f"{type(exc).__name__}: {exc}"}
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
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
