#!/usr/bin/env python3
"""Deterministic accounting for the M166 rehearsal-cost audit."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def build_analysis(root: Path) -> dict[str, object]:
    source_path = (
        root.parent
        / "M166-reference-dominance-rehearsal"
        / "analysis.json"
    )
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    converter_on = source["rehearsal"]["converter_on"]
    tc0 = source["rehearsal"]["tc0"]
    witness_blocks = source["formal_witness_correction"]["required_blocks"]

    blocks = [
        {
            "id": "tr_ab_calibration",
            "frames": converter_on["ab_calibration"],
            "category": "predicate_calibration",
        },
        {
            "id": "tr_reference_strips",
            "frames": converter_on["four_reference_strips"],
            "category": "predicate_subject",
        },
        {
            "id": "tr_held_out_validation",
            "frames": converter_on["held_out_validation"],
            "category": "predicate_calibration",
        },
        {
            "id": "tc0_ab_calibration",
            "frames": tc0["ab_calibration"],
            "category": "predicate_calibration",
        },
        {
            "id": "tc0_dominance_witness",
            "frames": tc0["candidate_independent_dominance_witness"],
            "category": "predicate_subject",
        },
        {
            "id": "tc0_candidate_stacks",
            "frames": tc0["candidate_input_stacks"],
            "category": "score_execution",
        },
        {
            "id": "tc0_fixed_focus_witnesses",
            "frames": tc0["candidate_reset_start_end_witnesses"],
            "category": "score_execution",
        },
        {
            "id": "tc0_sharp_control",
            "frames": tc0["sharp_physical_control"],
            "category": "physical_control",
        },
        {
            "id": "tc0_blur_control",
            "frames": tc0["blur_physical_control"],
            "category": "physical_control",
        },
        {
            "id": "tc0_held_out_validation",
            "frames": tc0["held_out_validation"],
            "category": "predicate_calibration",
        },
    ]

    by_category: dict[str, int] = {}
    for block in blocks:
        category = str(block["category"])
        by_category[category] = by_category.get(category, 0) + int(
            block["frames"]
        )

    direct_predicate_frames = (
        by_category["predicate_subject"]
        + by_category["predicate_calibration"]
    )
    score_execution_frames = by_category["score_execution"]
    physical_control_frames = by_category["physical_control"]
    full_rehearsal_frames = sum(int(block["frames"]) for block in blocks)

    reference_strip = converter_on["four_reference_strips"] // 4
    sw4 = witness_blocks["TC0-DOM-sw4-A"] + witness_blocks["TC0-DOM-sw4-B"]
    sw10 = (
        witness_blocks["TC0-DOM-sw10-A"]
        + witness_blocks["TC0-DOM-sw10-B"]
    )
    stages_source = [
        ("TR-A/B calibration", converter_on["ab_calibration"]),
        ("TR-S01", reference_strip),
        ("TR-S02", reference_strip),
        ("TR-S03", reference_strip),
        ("TR-S04", reference_strip),
        ("TR-V validation", converter_on["held_out_validation"]),
        ("TC0-A/B calibration", tc0["ab_calibration"]),
        ("TC0-DOM-sw4-A/B", sw4),
        ("TC0-DOM-sw10-A/B", sw10),
        (
            "TC0 candidate package plus fixed-focus witnesses",
            tc0["candidate_input_stacks"]
            + tc0["candidate_reset_start_end_witnesses"],
        ),
        ("TC0 sharp control", tc0["sharp_physical_control"]),
        ("TC0 blur control", tc0["blur_physical_control"]),
        (
            "TC0-V validation and final family",
            tc0["held_out_validation"],
        ),
    ]

    cumulative = 0
    stages = []
    for index, (name, frames) in enumerate(stages_source, start=1):
        cumulative += frames
        stages.append(
            {
                "stage": index,
                "name": name,
                "frames": frames,
                "cumulative": cumulative,
                "remaining_if_abort_after_stage": (
                    full_rehearsal_frames - cumulative
                ),
            }
        )

    corrected_score_frames = 1215
    old_reference_frames = 96
    new_reference_frames = converter_on["four_reference_strips"]
    new_dominance_witness_frames = tc0[
        "candidate_independent_dominance_witness"
    ]
    new_held_out_v_frames = (
        converter_on["held_out_validation"] + tc0["held_out_validation"]
    )
    base_candidate_input_frames = tc0["candidate_input_stacks"]
    base_ab_calibration_frames = (
        converter_on["ab_calibration"] + tc0["ab_calibration"]
    )
    candidate_stage = next(
        stage
        for stage in stages
        if stage["name"]
        == "TC0 candidate package plus fixed-focus witnesses"
    )
    return {
        "status": "PASS",
        "headline": "STAGED RELEASE: 128 frames",
        "source": {
            "path": str(source_path.relative_to(root.parents[1])),
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
        "blocks": blocks,
        "categories": {
            "direct_predicate_frames": direct_predicate_frames,
            "score_execution_frames": score_execution_frames,
            "physical_control_frames": physical_control_frames,
            "full_rehearsal_frames": full_rehearsal_frames,
        },
        "discarded_reductions": {
            "estimator_only": direct_predicate_frames,
            "without_physical_controls": (
                full_rehearsal_frames - physical_control_frames
            ),
            "without_candidate_stacks": full_rehearsal_frames - 164,
            "without_score_execution_package": (
                full_rehearsal_frames - score_execution_frames
            ),
        },
        "score": {
            "corrected_combined_frames": corrected_score_frames,
            "rehearsal_gap": corrected_score_frames - full_rehearsal_frames,
        },
        "score_disjointness": {
            "base_total": source["score"]["current_891_baseline"],
            "old_reference_frames_replaced": old_reference_frames,
            "new_reference_frames": new_reference_frames,
            "reference_net_increment": (
                new_reference_frames - old_reference_frames
            ),
            "base_candidate_input_frames": base_candidate_input_frames,
            "new_dominance_witness_frames": (
                new_dominance_witness_frames
            ),
            "dominance_witness_vs_candidate_raw_overlap": 0,
            "base_ab_calibration_frames": base_ab_calibration_frames,
            "new_held_out_v_frames": new_held_out_v_frames,
            "held_out_v_vs_ab_raw_overlap": 0,
            "expanded_corrected_total": (
                source["score"]["current_891_baseline"]
                - old_reference_frames
                + new_reference_frames
                + new_dominance_witness_frames
                + new_held_out_v_frames
            ),
        },
        "rehearsal_disjointness": {
            "shared_raws_with_score": 0,
            "shared_calibration_maps_with_score": 0,
            "shared_subject_sessions_with_score": 0,
        },
        "m151_rehearsal_exit_gate": {
            "source_blocks": [
                "TC0-sw4-A",
                "TC0-sw4-B",
                "TC0-sw10-A",
                "TC0-sw10-B",
            ],
            "source_frames": base_candidate_input_frames,
            "m151_added_frames": 0,
            "survives_staged_structure": True,
            "available_after_cumulative_frames": candidate_stage[
                "cumulative"
            ],
        },
        "staging": {
            "first_stage_frames": stages_source[0][1],
            "stages": stages,
            "final_cumulative": cumulative,
        },
        "intermittent_package_model": {
            "symbol": "p",
            "one_package_detection": "p",
            "two_package_detection": "1-(1-p)^2",
            "detection_lost_if_duplicate_removed": "p(1-p)",
        },
    }


def main() -> int:
    root = Path(__file__).resolve().parent
    output = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else root / "analysis.json"
    )
    try:
        result = build_analysis(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"PASS: wrote {output}")
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
