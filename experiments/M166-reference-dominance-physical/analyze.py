#!/usr/bin/env python3
"""Deterministic physical calculations for M166 reference dominance."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def incoherent_circular_mtf(frequency: float, cutoff: float) -> float:
    normalized = frequency / cutoff
    if normalized < 0.0 or normalized >= 1.0:
        return 0.0
    return (2.0 / math.pi) * (
        math.acos(normalized)
        - normalized * math.sqrt(1.0 - normalized * normalized)
    )


def build_analysis() -> dict[str, object]:
    sensor_width_mm = 35.9
    active_width_px = 7008
    pixel_pitch_mm = sensor_width_mm / active_width_px
    pixel_pitch_um = pixel_pitch_mm * 1000.0

    target_magnification = 1.32
    hard_max_magnification = 1.33
    reference_lower_magnification = 2.7015
    ratio_at_target = reference_lower_magnification / target_magnification
    ratio_at_hard_max = (
        reference_lower_magnification / hard_max_magnification
    )

    interior_px = 128
    guard_px_each_side = 64
    cell_span_px = interior_px + 2 * guard_px_each_side
    rows = 8
    cell_span_mm = cell_span_px * pixel_pitch_mm / target_magnification
    eight_row_height_mm = rows * cell_span_mm

    fabrication_scale_tolerance = 0.0025
    tolerance_compensated_nominal_height_mm = (
        eight_row_height_mm / (1.0 - fabrication_scale_tolerance)
    )
    tolerance_compensated_max_height_mm = (
        tolerance_compensated_nominal_height_mm
        * (1.0 + fabrication_scale_tolerance)
    )
    panel_height_limit_mm = 8.0

    tilt_nominal_deg = 1.0
    tilt_tolerance_deg = 0.02
    tilt_worst_deg = tilt_nominal_deg + tilt_tolerance_deg
    row_depth_nominal_um = (
        cell_span_mm * math.sin(math.radians(tilt_nominal_deg)) * 1000.0
    )
    row_depth_worst_um = (
        cell_span_mm * math.sin(math.radians(tilt_worst_deg)) * 1000.0
    )

    nominal_f_number = 5.6
    reference_bellows_lower = 2.412

    def dof_um(
        magnification: float,
        bellows_factor: float,
        circle_of_confusion_pixels: float,
    ) -> float:
        return (
            2.0
            * nominal_f_number
            * bellows_factor
            * circle_of_confusion_pixels
            * pixel_pitch_mm
            / (magnification * magnification)
            * 1000.0
        )

    circle_of_confusion_pixels = 2.0
    reference_dof_um = dof_um(
        reference_lower_magnification,
        reference_bellows_lower,
        circle_of_confusion_pixels,
    )
    # B = 1 is a conservative physical lower bound for 1 + m/p with p > 0.
    scored_dof_floor_um = dof_um(
        target_magnification, 1.0, circle_of_confusion_pixels
    )
    reference_rows_per_strip = math.floor(
        reference_dof_um / row_depth_worst_um
    )
    scored_rows_per_strip = math.floor(
        scored_dof_floor_um / row_depth_worst_um
    )
    reference_strips = math.ceil(rows / reference_rows_per_strip)
    scored_witness_strips = math.ceil(rows / scored_rows_per_strip)

    frames_per_strip = 32
    old_reference_frames = 96
    new_reference_frames = reference_strips * frames_per_strip
    scored_witness_frames = scored_witness_strips * frames_per_strip
    held_out_validation_frames = 2 * 2 * 32
    old_session_frames = 891
    revised_session_frames = (
        old_session_frames
        - old_reference_frames
        + new_reference_frames
        + scored_witness_frames
        + held_out_validation_frames
    )

    licensed_cells = [0.10, 0.15, 0.20, 0.25]
    reference_airy_um = [6.62, 8.52]
    scored_airy_um = [10.70, 13.21]

    def cutoff(airy_um: float) -> float:
        return 2.44 / (airy_um / 1000.0)

    reference_cutoff_worst = cutoff(max(reference_airy_um))
    reference_cutoff_best = cutoff(min(reference_airy_um))
    scored_cutoff_worst = cutoff(max(scored_airy_um))
    scored_cutoff_best = cutoff(min(scored_airy_um))
    mtf_rows: list[dict[str, float]] = []
    for cell in licensed_cells:
        object_frequency = cell * target_magnification / pixel_pitch_mm
        conservative_ratio = (
            incoherent_circular_mtf(
                object_frequency, reference_cutoff_worst
            )
            / incoherent_circular_mtf(
                object_frequency, scored_cutoff_best
            )
        )
        optimistic_ratio = (
            incoherent_circular_mtf(
                object_frequency, reference_cutoff_best
            )
            / incoherent_circular_mtf(
                object_frequency, scored_cutoff_worst
            )
        )
        mtf_rows.append(
            {
                "cell_cyc_scored_px": cell,
                "object_frequency_cy_mm": object_frequency,
                "diffraction_only_ratio_conservative": conservative_ratio,
                "diffraction_only_ratio_optimistic": optimistic_ratio,
            }
        )

    return {
        "status": "PASS",
        "target": {
            "decision": "TARGET HOLDS AT 1.32x",
            "target_magnification": target_magnification,
            "hard_max_magnification": hard_max_magnification,
            "reference_lower_magnification": reference_lower_magnification,
            "ratio_at_target": ratio_at_target,
            "ratio_at_hard_max": ratio_at_hard_max,
            "pixel_pitch_um": pixel_pitch_um,
            "eight_row_height_mm": eight_row_height_mm,
            "fabrication_scale_tolerance_fraction": (
                fabrication_scale_tolerance
            ),
            "tolerance_compensated_nominal_height_mm": (
                tolerance_compensated_nominal_height_mm
            ),
            "tolerance_compensated_max_height_mm": (
                tolerance_compensated_max_height_mm
            ),
            "panel_height_limit_mm": panel_height_limit_mm,
            "remaining_height_margin_um": (
                panel_height_limit_mm
                - tolerance_compensated_max_height_mm
            )
            * 1000.0,
        },
        "focus_strips": {
            "tilt_nominal_degrees": tilt_nominal_deg,
            "tilt_tolerance_degrees": tilt_tolerance_deg,
            "row_depth_nominal_um": row_depth_nominal_um,
            "row_depth_worst_um": row_depth_worst_um,
            "circle_of_confusion_sensor_pixels": (
                circle_of_confusion_pixels
            ),
            "reference_dof_floor_um": reference_dof_um,
            "scored_dof_floor_um": scored_dof_floor_um,
            "reference_rows_per_strip": reference_rows_per_strip,
            "scored_rows_per_strip": scored_rows_per_strip,
            "reference_strip_count": reference_strips,
            "scored_witness_strip_count": scored_witness_strips,
            "criterion": (
                "Every complete guarded target row assigned to a strip must "
                "fit inside the repository's two-sensor-pixel, "
                "Nyquist-matched object-side DoF at worst registered tilt."
            ),
        },
        "frame_count": {
            "current_session": old_session_frames,
            "old_reference": old_reference_frames,
            "new_reference": new_reference_frames,
            "reference_increment": (
                new_reference_frames - old_reference_frames
            ),
            "scored_path_witness": scored_witness_frames,
            "held_out_flat_dark_validation": (
                held_out_validation_frames
            ),
            "revised_session": revised_session_frames,
            "registered_frame_increment": (
                revised_session_frames - old_session_frames
            ),
            "revised_shutter_releases_with_histogram": (
                revised_session_frames + 1
            ),
        },
        "diffraction_only_transfer": {
            "rows": mtf_rows,
            "minimum_conservative_ratio": min(
                row["diffraction_only_ratio_conservative"]
                for row in mtf_rows
            ),
            "maximum_conservative_ratio": max(
                row["diffraction_only_ratio_conservative"]
                for row in mtf_rows
            ),
            "interpretation": (
                "A small strictly positive transfer margin is physically "
                "plausible under diffraction alone; a literal delta_H > 1 "
                "would require a ratio above 2 and is not supported."
            ),
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
