#!/usr/bin/env python3
"""Reduce M166's read-only EXIF and existing commissioning evidence.

The script never opens a capture.  It consumes the CSV produced by ExifTool and
tracked experiment artifacts.  Any error is serialized as FAIL without a
traceback so the lane cannot turn missing evidence into an apparent pass.
"""

from __future__ import annotations

import csv
import hashlib
import itertools
import json
import math
import statistics
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
STREHL = HERE.parents[1]
OUT = HERE / "analysis.json"

EXPECTED_COUNTS = {
    "diagonal-f5.6": 279,
    "diagonal-f8": 210,
    "diagonal-f11": 143,
    "horizontal-f5.6": 67,
    "horizontal-f8": 50,
    "horizontal-f11": 40,
}

FOCUS_FILES = {
    "f5.6": STREHL
    / "experiments/M128-razor-ladder/out/focus-hflat-f5.6.json",
    "f8": STREHL / "experiments/M128-razor-ladder/out/focus-hflat-f8.json",
    "f11": STREHL / "experiments/M128-razor-ladder/out/focus-hflat-f11.json",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def classify(row: dict[str, str]) -> tuple[str, str, str]:
    directory = row["Directory"]
    composition = (
        "diagonal" if "diagonal-tilt-all-axes" in directory else "horizontal"
    )
    if "f5.6" in directory:
        aperture = "f5.6"
    elif "f11" in directory:
        aperture = "f11"
    else:
        aperture = "f8"
    return composition, aperture, f"{composition}-{aperture}"


def one_value(rows: list[dict[str, str]], field: str):
    values = sorted({row[field] for row in rows})
    return values[0] if len(values) == 1 else values


def summarize_arm(rows: list[dict[str, str]]) -> dict:
    rows = sorted(rows, key=lambda row: row["FileName"])
    sony_n = float(one_value(rows, "SonyFNumber"))
    q = [float(row["SonyFNumber2"]) / sony_n for row in rows]
    span = abs(q[-1] - q[0])
    intervals = len(rows) - 1
    shutter = [int(row["ShutterCount"]) for row in rows]
    monotone = all(q[i + 1] <= q[i] for i in range(intervals))
    return {
        "count": len(rows),
        "first_file": rows[0]["FileName"],
        "last_file": rows[-1]["FileName"],
        "display_f_number": float(one_value(rows, "FNumber")),
        "sony_f_number": sony_n,
        "sony_f_number2_min": min(float(row["SonyFNumber2"]) for row in rows),
        "sony_f_number2_max": max(float(row["SonyFNumber2"]) for row in rows),
        "focus_coordinate_definition": "SonyFNumber2 / SonyFNumber",
        "focus_coordinate_start": q[0],
        "focus_coordinate_end": q[-1],
        "focus_coordinate_span": span,
        "focus_coordinate_unique_values": len(set(q)),
        "focus_coordinate_monotone_nonincreasing": monotone,
        "mean_coordinate_step_per_frame": span / intervals,
        "mean_coordinate_step_per_frame_per_f_number": (
            span / intervals / sony_n
        ),
        "coarse_focus_positions": sorted(
            {int(row["FocusPosition2"]) for row in rows}
        ),
        "coarse_focus_distances_m": sorted(
            {float(row["FocusDistance2"]) for row in rows}
        ),
        "exposure_s": float(one_value(rows, "ExposureTime")),
        "iso": int(one_value(rows, "ISO")),
        "focal_length_mm": float(one_value(rows, "FocalLength")),
        "lens_model": one_value(rows, "LensModel"),
        "image_stabilization_numeric": int(one_value(rows, "ImageStabilization")),
        "electronic_front_curtain_numeric": int(
            one_value(rows, "ElectronicFrontCurtainShutter")
        ),
        "shutter_count_first": shutter[0],
        "shutter_count_last": shutter[-1],
        "shutter_counts_consecutive": all(
            shutter[i + 1] == shutter[i] + 1 for i in range(intervals)
        ),
        "total_capture_photon_opportunity_proxy": (
            len(rows)
            * float(one_value(rows, "ExposureTime"))
            / (sony_n * sony_n)
        ),
    }


def focus_peak(
    aperture: str,
    rows: list[dict[str, str]],
    path: Path,
) -> dict:
    samples = json.loads(path.read_text(encoding="utf-8"))
    valid = [sample for sample in samples if "status" not in sample]
    best = max(valid, key=lambda sample: sample["maxgrad"])
    exif = next(row for row in rows if row["FileName"] == best["frame"])
    sony_n = float(exif["SonyFNumber"])
    return {
        "aperture": aperture,
        "survey_frames": len(samples),
        "valid_frames": len(valid),
        "best_index": best["index"],
        "best_file": best["frame"],
        "best_focus_coordinate": float(exif["SonyFNumber2"]) / sony_n,
        "best_coarse_focus_position": int(exif["FocusPosition2"]),
        "best_coarse_focus_distance_m": float(exif["FocusDistance2"]),
        "maxgrad_dn_per_green_px": best["maxgrad"],
        "local_step_dn": best["step_dn"],
        "contrast_dn": best["contrast_dn"],
        "w50_green_px": best["w50"],
    }


def coverage(arms: dict[str, dict], composition: str) -> dict:
    selected = {
        aperture: arms[f"{composition}-{aperture}"]
        for aperture in ("f5.6", "f8", "f11")
    }
    ranges = {
        aperture: sorted(
            [
                arm["focus_coordinate_start"],
                arm["focus_coordinate_end"],
            ]
        )
        for aperture, arm in selected.items()
    }
    intersection_lo = max(bounds[0] for bounds in ranges.values())
    intersection_hi = min(bounds[1] for bounds in ranges.values())
    union_lo = min(bounds[0] for bounds in ranges.values())
    union_hi = max(bounds[1] for bounds in ranges.values())
    intersection = max(0.0, intersection_hi - intersection_lo)
    union = union_hi - union_lo
    return {
        "ranges": {
            aperture: {
                "min": bounds[0],
                "max": bounds[1],
                "span": bounds[1] - bounds[0],
            }
            for aperture, bounds in ranges.items()
        },
        "intersection_span": intersection,
        "union_span": union,
        "intersection_over_union": intersection / union,
        "f5.6_span_over_f11_span": (
            selected["f5.6"]["focus_coordinate_span"]
            / selected["f11"]["focus_coordinate_span"]
        ),
    }


def main() -> int:
    exif_path = HERE / "exif.csv"
    with exif_path.open("r", encoding="utf-8-sig", newline="") as handle:
        exif_rows = list(csv.DictReader(handle))

    grouped: dict[str, list[dict[str, str]]] = {}
    for _, _, key in map(classify, exif_rows):
        grouped[key] = []
    for row in exif_rows:
        grouped[classify(row)[2]].append(row)
    arms = {key: summarize_arm(rows) for key, rows in sorted(grouped.items())}

    horizontal_rows = {
        aperture: [
            row
            for row in exif_rows
            if classify(row)[:2] == ("horizontal", aperture)
        ]
        for aperture in ("f5.6", "f8", "f11")
    }
    pixel_focus = {
        aperture: focus_peak(
            aperture,
            horizontal_rows[aperture],
            FOCUS_FILES[aperture],
        )
        for aperture in ("f5.6", "f8", "f11")
    }

    across_path = (
        STREHL / "experiments/M128-razor-ladder/out/across-best.json"
    )
    across = json.loads(across_path.read_text(encoding="utf-8"))
    controls_path = (
        STREHL / "experiments/M128-razor-ladder/out/controls.json"
    )
    controls = json.loads(controls_path.read_text(encoding="utf-8"))
    controls_by_id = {item["id"]: item for item in controls["controls"]}
    ragged_path = (
        STREHL / "experiments/M128-razor-ladder/out/ragged-tolerance.json"
    )
    ragged = json.loads(ragged_path.read_text(encoding="utf-8"))
    refit_path = (
        STREHL / "experiments/M128-razor-ladder/refit/refit.json"
    )
    refit = json.loads(refit_path.read_text(encoding="utf-8"))
    witness_path = (
        STREHL
        / "experiments/M164-aperture-identifiability/results.json"
    )
    witness = json.loads(witness_path.read_text(encoding="utf-8"))

    sensor_width_mm = 35.9
    sensor_height_mm = 23.9
    image_width_px = 7008
    image_height_px = 4672
    pitch_x_um = sensor_width_mm * 1000.0 / image_width_px
    pitch_y_um = sensor_height_mm * 1000.0 / image_height_px
    pitch_um = (pitch_x_um + pitch_y_um) / 2.0
    wavelength_um = 0.550

    airy = {}
    for aperture in ("f5.6", "f8", "f11"):
        arm = arms[f"horizontal-{aperture}"]
        n_display = arm["display_f_number"]
        n_sony = arm["sony_f_number"]
        nominal_um = 2.44 * wavelength_um * n_display
        precise_um = 2.44 * wavelength_um * n_sony
        effective_min_um = (
            2.44 * wavelength_um * arm["sony_f_number2_min"]
        )
        effective_max_um = (
            2.44 * wavelength_um * arm["sony_f_number2_max"]
        )
        airy[aperture] = {
            "display_f_number": n_display,
            "sony_f_number": n_sony,
            "marked_airy_diameter_um": nominal_um,
            "marked_airy_diameter_px": nominal_um / pitch_um,
            "sony_precise_airy_diameter_um": precise_um,
            "sony_precise_airy_diameter_px": precise_um / pitch_um,
            "sony_f_number2_airy_diameter_um_range": [
                effective_min_um,
                effective_max_um,
            ],
            "sony_f_number2_airy_diameter_px_range": [
                effective_min_um / pitch_um,
                effective_max_um / pitch_um,
            ],
            "caveat": (
                "ExifTool documents SonyFNumber2 as sometimes deviating; "
                "its optical meaning is not independently calibrated here."
            ),
        }

    step_norms = [
        arm["mean_coordinate_step_per_frame_per_f_number"]
        for arm in arms.values()
    ]
    peak_q = [item["best_focus_coordinate"] for item in pixel_focus.values()]

    f56_diag = arms["diagonal-f5.6"][
        "total_capture_photon_opportunity_proxy"
    ]
    f11_diag = arms["diagonal-f11"][
        "total_capture_photon_opportunity_proxy"
    ]
    f56_h = arms["horizontal-f5.6"][
        "total_capture_photon_opportunity_proxy"
    ]
    f11_h = arms["horizontal-f11"][
        "total_capture_photon_opportunity_proxy"
    ]

    result = {
        "schema": "strehl.m166.aperture-premise-analysis.v1",
        "status": "PASS",
        "captures_opened_by_analysis_script": 0,
        "inputs": {
            "exif_csv": {
                "path": str(exif_path.relative_to(STREHL)),
                "sha256": sha256(exif_path),
                "rows": len(exif_rows),
            },
            "existing_focus_surveys": {
                aperture: {
                    "path": str(path.relative_to(STREHL)),
                    "sha256": sha256(path),
                }
                for aperture, path in FOCUS_FILES.items()
            },
            "m128_across_best": {
                "path": str(across_path.relative_to(STREHL)),
                "sha256": sha256(across_path),
            },
            "m128_controls": {
                "path": str(controls_path.relative_to(STREHL)),
                "sha256": sha256(controls_path),
            },
            "m128_ragged_tolerance": {
                "path": str(ragged_path.relative_to(STREHL)),
                "sha256": sha256(ragged_path),
            },
            "m128_smooth_edge_refit": {
                "path": str(refit_path.relative_to(STREHL)),
                "sha256": sha256(refit_path),
            },
            "m164_witness": {
                "path": str(witness_path.relative_to(STREHL)),
                "sha256": sha256(witness_path),
            },
        },
        "arms": arms,
        "focus_step": {
            "coordinate": (
                "q = SonyFNumber2 / SonyFNumber; a fine monotone lens-state "
                "coordinate, not asserted here as a calibrated distance"
            ),
            "mean_delta_q_over_n_range": [
                min(step_norms),
                max(step_norms),
            ],
            "mean_delta_q_over_n_max_over_min": (
                max(step_norms) / min(step_norms)
            ),
            "interpretation": (
                "Delta q per frame scales approximately with f-number, "
                "contradicting an aperture-independent absolute focus step."
            ),
            "pixel_derived_horizontal_edge_peaks": pixel_focus,
            "pixel_peak_coordinate_range": [min(peak_q), max(peak_q)],
            "pixel_peak_coordinate_spread": max(peak_q) - min(peak_q),
        },
        "coverage": {
            "diagonal": coverage(arms, "diagonal"),
            "horizontal": coverage(arms, "horizontal"),
            "interpretation": (
                "All arms share a large common interval, but their total "
                "focus-coordinate spans are not equal."
            ),
        },
        "optics": {
            "sensor_mm": [sensor_width_mm, sensor_height_mm],
            "delivered_image_px": [image_width_px, image_height_px],
            "derived_pitch_um": {
                "horizontal": pitch_x_um,
                "vertical": pitch_y_um,
                "representative_mean": pitch_um,
            },
            "wavelength_um": wavelength_um,
            "airy_diameter_formula": "2.44 * wavelength * f_number",
            "airy": airy,
            "teleconverter_folded_into_exif": {
                "all_focal_lengths_mm": sorted(
                    {arm["focal_length_mm"] for arm in arms.values()}
                ),
                "all_lens_models": sorted(
                    {str(arm["lens_model"]) for arm in arms.values()}
                ),
                "all_maximum_apertures": sorted(
                    {
                        float(row["MaxApertureValue"])
                        for row in exif_rows
                    }
                ),
                "finding": (
                    "The 100 mm f/2.8 base lens reports 200 mm and an "
                    "approximately f/5.6 maximum with the 2X converter; EXIF "
                    "FNumber is already teleconverter-adjusted."
                ),
            },
        },
        "raggedness": {
            "common_coordinate_rms_green_px": across["rms_common_px"],
            "cross_aperture_correlations": across["corr"],
            "mean_offdiagonal_correlation": across["mean_offdiag_corr"],
            "shared_component_green_px": across["shared_px"],
            "independent_component_green_px": across["independent_px"],
            "commissioning_summary": controls["summary"],
            "subject_contamination_control": {
                "id": "C2",
                "status": controls_by_id["C2"]["status"],
                "headline": controls_by_id["C2"]["headline"],
            },
            "straight_line_tolerance": ragged["methods"]["straight_line"][
                "crossing"
            ],
            "per_column_tolerance": ragged["methods"][
                "measured_per_column"
            ]["crossing"],
            "per_column_result": ragged["interpretation"][
                "per_column_result"
            ],
            "smooth_edge_f11_over_f5.6_rise": {
                "sharp_diffraction_prediction": 11.0 / 5.6,
                "isotonic_measured": refit["t1"]["isotonic"]["ratio"],
                "erf_measured": refit["t1"]["erf"]["ratio"],
                "interpretation": (
                    "The one smooth detected feature becomes narrower rather "
                    "than broader at f/11 and is width-dominated, so it is not "
                    "an optical reference."
                ),
            },
        },
        "exposure_and_count": {
            "all_iso_values": sorted({arm["iso"] for arm in arms.values()}),
            "all_stabilization_values": sorted(
                {arm["image_stabilization_numeric"] for arm in arms.values()}
            ),
            "all_efcs_values": sorted(
                {
                    arm["electronic_front_curtain_numeric"]
                    for arm in arms.values()
                }
            ),
            "exposure_by_composition_s": {
                composition: sorted(
                    {
                        arm["exposure_s"]
                        for key, arm in arms.items()
                        if key.startswith(composition)
                    }
                )
                for composition in ("diagonal", "horizontal")
            },
            "best_edge_contrast_dn": {
                aperture: item["contrast_dn"]
                for aperture, item in pixel_focus.items()
            },
            "f5.6_over_f11_total_capture_photon_proxy": {
                "diagonal": f56_diag / f11_diag,
                "horizontal": f56_h / f11_h,
            },
            "warning": (
                "The total-capture proxy is not a per-output-pixel photon "
                "count; contribution maps are required for that.  It records "
                "the direction and size of the aligned acquisition budget."
            ),
        },
        "identifiability_witness": {
            "verdict": witness["verdict"],
            "two_world_identity": witness["two_world_witness"]["identity"],
            "maximum_absolute_output_difference": witness[
                "two_world_witness"
            ]["maximum_absolute_output_difference"],
            "sharpening_reward_ratio": witness["selected_frequency"][
                "sharpening_reward_ratio"
            ],
            "relative_unsharpened": witness["selected_frequency"][
                "observed_relative_unsharpened"
            ],
            "relative_sharpened": witness["selected_frequency"][
                "observed_relative_sharpened"
            ],
            "all_checks": witness["checks"],
        },
        "checks": {},
    }

    checks = {
        "C1_expected_six_arms_and_counts": {
            key: arms[key]["count"] == expected
            for key, expected in EXPECTED_COUNTS.items()
        },
        "C2_all_focus_coordinates_monotone": all(
            arm["focus_coordinate_monotone_nonincreasing"]
            for arm in arms.values()
        ),
        "C3_all_shutter_counts_consecutive": all(
            arm["shutter_counts_consecutive"] for arm in arms.values()
        ),
        "C4_step_is_not_aperture_independent": (
            max(
                arm["mean_coordinate_step_per_frame"]
                for arm in arms.values()
            )
            / min(
                arm["mean_coordinate_step_per_frame"]
                for arm in arms.values()
            )
            > 1.9
        ),
        "C5_delta_q_over_n_is_near_common": (
            max(step_norms) / min(step_norms) < 1.20
        ),
        "C6_pixel_focus_peaks_share_exact_metadata_coordinate": (
            max(peak_q) - min(peak_q) < 1e-12
        ),
        "C7_depth_coverage_is_not_equal": (
            coverage(arms, "diagonal")["f5.6_span_over_f11_span"] < 0.99
            and coverage(arms, "horizontal")["f5.6_span_over_f11_span"]
            < 0.99
        ),
        "C8_teleconverter_is_folded_into_exif": (
            all(arm["focal_length_mm"] == 200.0 for arm in arms.values())
            and all(
                "100mm F2.8" in str(arm["lens_model"])
                and "2X Teleconverter" in str(arm["lens_model"])
                for arm in arms.values()
            )
            and all(
                arm["display_f_number"] >= 5.6 for arm in arms.values()
            )
        ),
        "C9_m164_two_world_outputs_are_identical": (
            witness["two_world_witness"][
                "maximum_absolute_output_difference"
            ]
            == 0.0
        ),
        "C10_m164_sharpening_preserves_order_and_is_rewarded": all(
            witness["checks"][key]
            for key in (
                "C3_sharpened_metric_still_recovers_aperture_order",
                "C4_metric_rewards_sharpening_in_every_arm",
                "C5_relative_Airy_magnitude_survives_common_sharpening",
            )
        ),
        "C11_m128_subject_contamination_control_failed": (
            controls_by_id["C2"]["status"] == "FAIL"
        ),
        "C12_m128_smooth_edge_reverses_diffraction_prediction": (
            refit["t1"]["isotonic"]["ratio"] < 1.0
            and refit["t1"]["erf"]["ratio"] < 1.0
            and 11.0 / 5.6 > 1.0
        ),
    }
    result["checks"] = checks
    flattened = []
    for value in checks.values():
        if isinstance(value, dict):
            flattened.extend(value.values())
        else:
            flattened.append(value)
    result["status"] = "PASS" if all(flattened) else "FAIL"

    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['status']}: {sum(bool(v) for v in flattened)}/"
        f"{len(flattened)} checks; rows={len(exif_rows)}; "
        f"pixel_peak_spread={result['focus_step']['pixel_peak_coordinate_spread']:.3e}"
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # noqa: BLE001
        failure = {
            "schema": "strehl.m166.aperture-premise-analysis.v1",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
        }
        try:
            OUT.write_text(json.dumps(failure, indent=2) + "\n", encoding="utf-8")
        except BaseException:
            pass
        print(f"FAIL: {failure['error']}")
        raise SystemExit(1)
