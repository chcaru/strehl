#!/usr/bin/env python3
"""Small deterministic witnesses for the M166 truth-reference capture audit."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


def _complex_pairs(values: list[complex]) -> list[list[float]]:
    return [[value.real, value.imag] for value in values]


def _max_complex_error(left: list[complex], right: list[complex]) -> float:
    return max(abs(a - b) for a, b in zip(left, right, strict=True))


def build_analysis() -> dict[str, object]:
    sensor_width_mm = 35.9
    sensor_height_mm = 23.9
    active_width_px = 7008
    pixel_pitch_mm = sensor_width_mm / active_width_px
    pixel_pitch_um = pixel_pitch_mm * 1000.0

    m_reference_lower = 2.7015
    m_scored_max = 1.33
    sampling_ratio = m_reference_lower / m_scored_max
    licensed_frequency_scored = 0.25
    licensed_frequency_reference = licensed_frequency_scored / sampling_ratio

    # The absolute-scene gauge: all observed reference and output coefficients
    # are identical although scene and reference transfer differ.
    scene_a = [
        complex(0.7, -0.2),
        complex(-0.1, 0.9),
        complex(1.2, 0.4),
        complex(-0.6, -0.5),
    ]
    sharpening = 1.2
    reference_transfer_a = 0.8
    output_transfers = [0.35, 0.50]
    reference_a = [reference_transfer_a * value for value in scene_a]
    outputs_a = [
        [sharpening * transfer * value for value in scene_a]
        for transfer in output_transfers
    ]

    scene_b = [sharpening * value for value in scene_a]
    reference_transfer_b = reference_transfer_a / sharpening
    reference_b = [reference_transfer_b * value for value in scene_b]
    outputs_b = [
        [transfer * value for value in scene_b]
        for transfer in output_transfers
    ]
    observed_transfer_ratios_a = [
        sharpening * transfer / reference_transfer_a
        for transfer in output_transfers
    ]
    observed_transfer_ratios_b = [
        transfer / reference_transfer_b for transfer in output_transfers
    ]

    # A common reference error violates the zero cross-error assumption in the
    # split-reference denominator. These are population-power calculations.
    scene_power = 1.0
    g = 0.8
    h = 0.4
    common_reference_error_power = 0.2
    independent_reference_noise_power = 0.05
    independent_output_noise_power = 0.05
    output_common_error_gain = 0.5

    clean_cross_rr = g * g * scene_power
    clean_cross_yr = h * g * scene_power
    clean_h_hat = clean_cross_yr / clean_cross_rr

    contaminated_cross_rr = (
        clean_cross_rr + common_reference_error_power
    )
    contaminated_cross_yr_reference_only = clean_cross_yr
    contaminated_h_hat_reference_only = (
        contaminated_cross_yr_reference_only / contaminated_cross_rr
    )
    contaminated_cross_yr_shared = (
        clean_cross_yr
        + output_common_error_gain * common_reference_error_power
    )
    reference_variance = (
        clean_cross_rr
        + common_reference_error_power
        + independent_reference_noise_power
    )
    clean_output_variance = (
        h * h * scene_power + independent_output_noise_power
    )
    contaminated_output_variance = (
        h * h * scene_power
        + output_common_error_gain**2 * common_reference_error_power
        + independent_output_noise_power
    )
    clean_q = clean_cross_yr**2 / (
        clean_output_variance
        * (clean_cross_rr + independent_reference_noise_power)
    )
    contaminated_q = contaminated_cross_yr_shared**2 / (
        contaminated_output_variance * reference_variance
    )

    # Physical packing implied by M135's 10 x 8 layout. Every cell contains a
    # 128 px interior plus 64 px guard on each side, hence 256 scored pixels.
    cell_span_scored_px = 128 + 2 * 64

    def cell_span_mm(magnification: float) -> float:
        return cell_span_scored_px * pixel_pitch_mm / magnification

    panel_height_mm = 8.0
    panel_width_mm = 12.0
    rows = 8
    columns = 10
    minimum_magnification_for_height = (
        rows * cell_span_scored_px * pixel_pitch_mm / panel_height_mm
    )
    macro_sites = 64
    rank_ratio_floor = 1.5
    max_dimension_from_macro_sites_only = math.floor(
        macro_sites / rank_ratio_floor
    )
    full_interior_dimension = 128 * 128
    required_rows_for_full_interior = math.ceil(
        rank_ratio_floor * full_interior_dimension
    )

    # Macro DoF and tilted-plane coverage. The proposal uses reported f/5.6
    # and the measured converter-on bellows-factor interval.
    nominal_f_number = 5.6
    bellows_low = 2.412
    bellows_high = 3.064

    def dof_mm(coc_pixels: float, bellows_factor: float) -> float:
        coc_mm = coc_pixels * pixel_pitch_mm
        return (
            2
            * nominal_f_number
            * bellows_factor
            * coc_mm
            / (m_reference_lower**2)
        )

    tilt_rad = math.radians(1.0)

    def depth_span_mm(length_mm: float) -> float:
        return length_mm * math.sin(tilt_rad)

    dof_one_pixel_low = dof_mm(1.0, bellows_low)
    dof_one_pixel_high = dof_mm(1.0, bellows_high)
    dof_two_pixel_low = dof_mm(2.0, bellows_low)
    dof_two_pixel_high = dof_mm(2.0, bellows_high)
    depth_short = depth_span_mm(panel_height_mm)
    depth_long = depth_span_mm(panel_width_mm)
    depth_diagonal = depth_span_mm(
        math.hypot(panel_width_mm, panel_height_mm)
    )

    def strips_needed(depth_mm: float, dof_total_mm: float) -> int:
        return math.ceil(depth_mm / dof_total_mm)

    # Diffraction-only cutoffs from the proposal's object-side Airy ranges.
    reference_airy_um = [6.62, 8.52]
    scored_airy_um = [10.70, 13.21]
    licensed_object_frequency_cy_mm = (
        licensed_frequency_scored * m_scored_max / pixel_pitch_mm
    )

    def cutoff_cy_mm(airy_um: float) -> float:
        return 2.44 / (airy_um / 1000.0)

    analysis = {
        "status": "PASS",
        "absolute_scene_gauge": {
            "scene_a": _complex_pairs(scene_a),
            "scene_b": _complex_pairs(scene_b),
            "reference_transfer_a": reference_transfer_a,
            "reference_transfer_b": reference_transfer_b,
            "reference_observation_max_error": _max_complex_error(
                reference_a, reference_b
            ),
            "output_observation_max_errors": [
                _max_complex_error(a, b)
                for a, b in zip(outputs_a, outputs_b, strict=True)
            ],
            "observed_output_to_reference_ratios_a": (
                observed_transfer_ratios_a
            ),
            "observed_output_to_reference_ratios_b": (
                observed_transfer_ratios_b
            ),
            "both_worlds_reference_stronger": all(
                ratio < 1.0
                for ratio in (
                    observed_transfer_ratios_a
                    + observed_transfer_ratios_b
                )
            ),
            "interpretation": (
                "Absolute X and G are not separately identified; the "
                "observations do identify the scoped reference-path latent GX."
            ),
        },
        "sampling": {
            "pixel_pitch_um": pixel_pitch_um,
            "reference_lower_magnification": m_reference_lower,
            "scored_max_magnification": m_scored_max,
            "sampling_ratio": sampling_ratio,
            "margin_over_2x_relative_to_threshold_percent": (
                (sampling_ratio / 2.0 - 1.0) * 100.0
            ),
            "margin_over_2x_relative_to_achieved_percent": (
                (sampling_ratio - 2.0) / sampling_ratio * 100.0
            ),
            "licensed_frequency_scored_cyc_px": licensed_frequency_scored,
            "licensed_frequency_reference_cyc_px": (
                licensed_frequency_reference
            ),
            "reference_samples_per_licensed_cycle": (
                1.0 / licensed_frequency_reference
            ),
            "m147_nominal_point": 2.0329159,
            "m147_nominal_lower": 2.0126457,
            "m147_lower_headroom_percent": (
                (2.0126457 / 2.0 - 1.0) * 100.0
            ),
        },
        "diffraction": {
            "licensed_object_frequency_cy_mm": (
                licensed_object_frequency_cy_mm
            ),
            "reference_object_cutoff_range_cy_mm": [
                cutoff_cy_mm(reference_airy_um[1]),
                cutoff_cy_mm(reference_airy_um[0]),
            ],
            "scored_object_cutoff_range_cy_mm": [
                cutoff_cy_mm(scored_airy_um[1]),
                cutoff_cy_mm(scored_airy_um[0]),
            ],
            "interpretation": (
                "Diffraction-only cutoffs clear the licensed band, but this "
                "does not bound Viltrox aberration or establish information "
                "superiority."
            ),
        },
        "target_packing": {
            "cell_span_scored_px": cell_span_scored_px,
            "cell_span_mm_at_1_30": cell_span_mm(1.30),
            "cell_span_mm_at_1_32": cell_span_mm(1.32),
            "cell_span_mm_at_1_33": cell_span_mm(1.33),
            "eight_rows_mm_at_1_30": rows * cell_span_mm(1.30),
            "eight_rows_mm_at_1_32": rows * cell_span_mm(1.32),
            "eight_rows_mm_at_1_33": rows * cell_span_mm(1.33),
            "ten_columns_mm_at_1_32": columns * cell_span_mm(1.32),
            "minimum_magnification_for_eight_rows_in_8mm": (
                minimum_magnification_for_height
            ),
            "reference_field_width_mm": (
                sensor_width_mm / m_reference_lower
            ),
            "reference_field_height_mm": (
                sensor_height_mm / m_reference_lower
            ),
        },
        "rank_contract": {
            "macro_sites": macro_sites,
            "required_n_over_max_dimension": rank_ratio_floor,
            "largest_dimension_if_each_macro_site_is_one_row": (
                max_dimension_from_macro_sites_only
            ),
            "full_128_by_128_output_dimension": full_interior_dimension,
            "rows_required_for_full_128_by_128_output": (
                required_rows_for_full_interior
            ),
            "interpretation": (
                "The target must freeze additional independently coded "
                "micro-site rows or a smaller theorem-bearing output support; "
                "64 unspecified macro-sites do not determine covariance rank."
            ),
        },
        "fixed_focus_coverage": {
            "tilt_degrees": 1.0,
            "depth_span_um_across_8mm": depth_short * 1000.0,
            "depth_span_um_across_12mm": depth_long * 1000.0,
            "depth_span_um_across_diagonal": depth_diagonal * 1000.0,
            "one_pixel_dof_um_range": [
                dof_one_pixel_low * 1000.0,
                dof_one_pixel_high * 1000.0,
            ],
            "two_pixel_dof_um_range": [
                dof_two_pixel_low * 1000.0,
                dof_two_pixel_high * 1000.0,
            ],
            "strips_needed_two_pixel_short_axis_range": [
                strips_needed(depth_short, dof_two_pixel_high),
                strips_needed(depth_short, dof_two_pixel_low),
            ],
            "strips_needed_two_pixel_long_axis_range": [
                strips_needed(depth_long, dof_two_pixel_high),
                strips_needed(depth_long, dof_two_pixel_low),
            ],
            "strips_needed_two_pixel_diagonal_range": [
                strips_needed(depth_diagonal, dof_two_pixel_high),
                strips_needed(depth_diagonal, dof_two_pixel_low),
            ],
            "three_strip_coverage_um_range": [
                3.0 * dof_two_pixel_low * 1000.0,
                3.0 * dof_two_pixel_high * 1000.0,
            ],
            "interpretation": (
                "Three strips are not guaranteed even under a permissive "
                "two-pixel circle of confusion; overlap and seam guards reduce "
                "the listed ideal coverage further."
            ),
        },
        "correlated_reference_error": {
            "true_output_to_reference_transfer": clean_h_hat,
            "estimated_with_reference_only_common_error": (
                contaminated_h_hat_reference_only
            ),
            "relative_transfer_bias_percent": (
                (contaminated_h_hat_reference_only / clean_h_hat - 1.0)
                * 100.0
            ),
            "clean_squared_correlation": clean_q,
            "shared_error_squared_correlation": contaminated_q,
            "squared_correlation_change_percent": (
                (contaminated_q / clean_q - 1.0) * 100.0
            ),
            "interpretation": (
                "Disjoint fitted masters do not make reference-half errors "
                "independent; common residual covariance biases both the "
                "cross-transfer denominator and canonical information."
            ),
        },
    }
    return analysis


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
