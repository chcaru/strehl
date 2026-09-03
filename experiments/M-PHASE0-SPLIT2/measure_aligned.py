"""Amendment-1 repeat FRC after scorecard-licensed Fourier translation."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

import align
import frc
import measure


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
MANIFEST = OUT / "capture-manifest.json"
CAPTURE = measure.CAPTURE
ALIGNMENT_SIDE = 512
LOCAL_RMS_LIMIT_NATIVE_PIXEL = 0.10
EXCLUDED_TILE_COORDINATES = {
    (2, 2),
    (2, 3),
    (3, 2),
    (3, 3),
}


def jsonable(value: object) -> object:
    return measure.jsonable(value)


def write_json(path: Path, value: object) -> None:
    measure.write_json(path, value)


def registered_groups() -> list[dict[str, object]]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    groups = [
        group for group in manifest["groups"] if int(group["iso"]) == 100
    ]
    groups.sort(key=lambda group: int(group["pass"]))
    expected = [
        ("DSC00328.ARW", "DSC00359.ARW"),
        ("DSC00584.ARW", "DSC00615.ARW"),
    ]
    got = [
        (str(group["files"][0]), str(group["files"][-1]))
        for group in groups
    ]
    if got != expected:
        raise RuntimeError(f"scorecard ISO-100 inputs changed: {got}")
    return groups


def alignment_crop(evaluation: np.ndarray) -> np.ndarray:
    offset = (evaluation.shape[0] - ALIGNMENT_SIDE) // 2
    return evaluation[
        offset : offset + ALIGNMENT_SIDE,
        offset : offset + ALIGNMENT_SIDE,
    ]


def inspect_group_alignment(group: dict[str, object]) -> dict[str, object]:
    start = time.perf_counter()
    reference = None
    rows = []
    maximum_local_range = 0.0
    maximum_residual_rms_native = 0.0
    for index, filename in enumerate(group["files"]):
        decoded = measure.decode_regions(CAPTURE / str(filename))
        crop = alignment_crop(decoded["evaluation"])
        if reference is None:
            reference = crop.copy()
        global_shift = align.estimate_alignment(reference, crop)
        quadrants = align.quadrant_alignments(reference, crop)
        range_y = max(value[0] for value in quadrants) - min(
            value[0] for value in quadrants
        )
        range_x = max(value[1] for value in quadrants) - min(
            value[1] for value in quadrants
        )
        local_range = max(range_y, range_x)
        maximum_local_range = max(maximum_local_range, local_range)
        residual_rms_native = align.quadrant_residual_rms_native_pixels(
            global_shift,
            quadrants,
        )
        maximum_residual_rms_native = max(
            maximum_residual_rms_native,
            residual_rms_native,
        )
        rows.append(
            {
                "index": index,
                "file": str(filename),
                "global_alignment_shift_quad_pixels": list(global_shift),
                "quadrant_alignment_shifts_quad_pixels": [
                    list(value) for value in quadrants
                ],
                "maximum_quadrant_range_quad_pixels": local_range,
                "nontranslation_residual_rms_native_pixels": (
                    residual_rms_native
                ),
            }
        )
    return {
        "pass": int(group["pass"]),
        "iso": int(group["iso"]),
        "first_file": str(group["files"][0]),
        "last_file": str(group["files"][-1]),
        "nontranslation_residual_rms_limit_native_pixels": (
            LOCAL_RMS_LIMIT_NATIVE_PIXEL
        ),
        "maximum_quadrant_range_quad_pixels": maximum_local_range,
        "maximum_nontranslation_residual_rms_native_pixels": (
            maximum_residual_rms_native
        ),
        "passes_translation_only_gate": maximum_residual_rms_native
        <= LOCAL_RMS_LIMIT_NATIVE_PIXEL,
        "frames": rows,
        "elapsed_seconds": time.perf_counter() - start,
    }


def analyse_heldout(a: np.ndarray, b: np.ndarray) -> frc.Analysis:
    if a.shape != (measure.EVALUATION_SIDE, measure.EVALUATION_SIDE):
        raise ValueError(f"unexpected held-out image shape {a.shape}")
    tiles = []
    for tile_y, y in enumerate(range(0, a.shape[0], frc.TILE)):
        for tile_x, x in enumerate(range(0, a.shape[1], frc.TILE)):
            if (tile_y, tile_x) in EXCLUDED_TILE_COORDINATES:
                continue
            tiles.append(
                frc.spectrum_tile(
                    a[y : y + frc.TILE, x : x + frc.TILE],
                    b[y : y + frc.TILE, x : x + frc.TILE],
                )
            )
    if len(tiles) != 32:
        raise RuntimeError(f"held-out tile count is {len(tiles)}, expected 32")
    return frc.Analysis(frc.aggregate_spectra(tiles), tiles)


def partition_name(index: int) -> str:
    if index % 4 == 0:
        return "reference"
    if index % 4 == 1 or index % 8 == 3:
        return "a"
    return "b"


def bars(summary: dict[str, object]) -> dict[str, bool]:
    return {
        "mean_abs_frc_lt_0_05": float(summary["mean_abs_frc"]) < 0.05,
        "max_ring_abs_t_lt_4": float(summary["max_ring_abs_t"]) < 4.0,
        "bands_abs_lt_0_08": all(
            abs(float(row["frc"])) < 0.08 for row in summary["band_frc"]
        ),
        "snr_point_lt_0_25": float(summary["max_midband_snr"]) < 0.25,
        "snr_upper_95_lt_0_25": float(
            summary["max_midband_snr_bootstrap"]["interval_95"][1]
        )
        < 0.25,
    }


def licensed_crossing(result: dict[str, object]) -> dict[str, object]:
    outcome = str(result["outcome"])
    value = result["frequency_or_bound"]
    if value is None:
        return {
            "outcome": outcome,
            "frequency_quad_pixel": None,
            "frequency_native_pixel": None,
        }
    quad = float(value)
    native = quad / 2.0
    if native > 0.25 + 1e-12:
        return {
            "outcome": "UNLICENSED_GT_0.25",
            "frequency_quad_pixel": None,
            "frequency_native_pixel": None,
        }
    return {
        "outcome": outcome,
        "frequency_quad_pixel": quad,
        "frequency_native_pixel": native,
    }


def scene_summary(analysis: frc.Analysis) -> dict[str, object]:
    result = measure.scene_summary(analysis, include_rings=True)
    result["licensed_crossing"] = licensed_crossing(result["crossing"])
    bootstrap = result["crossing_bootstrap"]
    if "interval_95" in bootstrap:
        bootstrap["interval_95_native_pixel"] = [
            float(value) / 2.0 for value in bootstrap["interval_95"]
        ]
        bootstrap["median_native_pixel"] = float(bootstrap["median"]) / 2.0
    return result


def heldout_sharpening_sensitivity(
    scene_a: np.ndarray,
    scene_b: np.ndarray,
    baseline: frc.Analysis,
) -> dict[str, object]:
    sharpened_a = frc.unsharp(scene_a)
    sharpened_b = frc.unsharp(scene_b)
    sharpened = analyse_heldout(sharpened_a, sharpened_b)
    before = frc.classify(baseline.aggregate)
    after = frc.classify(sharpened.aggregate)
    movement = None
    if before["outcome"] == "MEASURED" and after["outcome"] == "MEASURED":
        movement = float(after["frequency_or_bound"]) - float(
            before["frequency_or_bound"]
        )
    return {
        "before": before,
        "after": after,
        "crossing_movement": movement,
        "naive_acuity_gain": frc.gradient_acuity(sharpened_a)
        / frc.gradient_acuity(scene_a),
    }


def process_aligned_group(
    group: dict[str, object],
    gate: dict[str, object],
) -> dict[str, object]:
    start = time.perf_counter()
    shape = (measure.EVALUATION_SIDE, measure.EVALUATION_SIDE)
    sums = {
        name: np.zeros(shape, dtype=np.float64)
        for name in (
            "reference",
            "a",
            "b",
            "normalized_reference",
            "normalized_a",
            "normalized_b",
            "d1",
            "d2",
            "normalized_d1",
            "normalized_d2",
        )
    }
    counts = {"reference": 0, "a": 0, "b": 0}
    levels = []
    maximum_phase_magnitude_error = 0.0
    maximum_ifft_imaginary_ratio = 0.0
    reference_crop = None
    applied_shifts = []

    expected_rows = gate["frames"]
    for index, filename in enumerate(group["files"]):
        decoded = measure.decode_regions(CAPTURE / str(filename))
        evaluation = decoded["evaluation"]
        crop = alignment_crop(evaluation)
        if reference_crop is None:
            reference_crop = crop.copy()
        shift = align.estimate_alignment(reference_crop, crop)
        expected = expected_rows[index]["global_alignment_shift_quad_pixels"]
        if max(abs(shift[axis] - float(expected[axis])) for axis in (0, 1)) > 1e-12:
            raise RuntimeError(
                f"alignment gate was not deterministic for {filename}: "
                f"{shift} != {expected}"
            )
        aligned, magnitude_error, imaginary_ratio = align.fourier_translate(
            evaluation,
            shift,
        )
        maximum_phase_magnitude_error = max(
            maximum_phase_magnitude_error, magnitude_error
        )
        maximum_ifft_imaginary_ratio = max(
            maximum_ifft_imaginary_ratio, imaginary_ratio
        )
        applied_shifts.append(list(shift))

        level = measure.robust_level(decoded["normalization"])
        levels.append(level)
        normalized = aligned / level
        partition = partition_name(index)
        sums[partition] += aligned
        sums[f"normalized_{partition}"] += normalized
        counts[partition] += 1

        block = index // 4
        weight = measure.ABBA[index % 4]
        null_name = "d1" if block % 2 == 0 else "d2"
        sums[null_name] += weight * aligned
        sums[f"normalized_{null_name}"] += weight * normalized

    if counts != {"reference": 8, "a": 12, "b": 12}:
        raise RuntimeError(f"partition counts changed: {counts}")
    for name, count in counts.items():
        sums[name] /= count
        sums[f"normalized_{name}"] /= count
    for name in ("d1", "d2", "normalized_d1", "normalized_d2"):
        sums[name] /= 8.0

    scene = analyse_heldout(sums["a"], sums["b"])
    normalized_scene = analyse_heldout(
        sums["normalized_a"],
        sums["normalized_b"],
    )
    null = analyse_heldout(sums["d1"], sums["d2"])
    normalized_null = analyse_heldout(
        sums["normalized_d1"],
        sums["normalized_d2"],
    )
    reference_a = analyse_heldout(sums["reference"], sums["a"])
    reference_b = analyse_heldout(sums["reference"], sums["b"])

    null_result = measure.null_summary(null, include_rings=True)
    null_result["max_midband_snr_bootstrap"] = frc.bootstrap_snr_max(null.tiles)
    null_result["bars"] = bars(null_result)
    null_result["all_bars_pass"] = all(null_result["bars"].values())

    normalized_null_result = measure.null_summary(
        normalized_null,
        include_rings=True,
    )
    normalized_null_result["max_midband_snr_bootstrap"] = frc.bootstrap_snr_max(
        normalized_null.tiles
    )
    normalized_null_result["bars"] = bars(normalized_null_result)
    normalized_null_result["all_bars_pass"] = all(
        normalized_null_result["bars"].values()
    )

    return {
        "report": {
            "pass": int(group["pass"]),
            "iso": int(group["iso"]),
            "first_file": str(group["files"][0]),
            "last_file": str(group["files"][-1]),
            "partition_counts": counts,
            "alignment": {
                "maximum_quadrant_range_quad_pixels": gate[
                    "maximum_quadrant_range_quad_pixels"
                ],
                "maximum_nontranslation_residual_rms_native_pixels": gate[
                    "maximum_nontranslation_residual_rms_native_pixels"
                ],
                "maximum_phase_ramp_magnitude_relative_error": (
                    maximum_phase_magnitude_error
                ),
                "maximum_ifft_imaginary_relative_rms": (
                    maximum_ifft_imaginary_ratio
                ),
                "applied_shifts_quad_pixels": applied_shifts,
            },
            "photometric_strip_level": {
                "minimum": min(levels),
                "maximum": max(levels),
                "mean": float(np.mean(levels)),
                "cv": float(np.std(levels) / np.mean(levels)),
            },
            "scene": scene_summary(scene),
            "normalized_scene": scene_summary(normalized_scene),
            "reference_repeat_band_frc": {
                "reference_a_0_15_0_30": frc.band_frc(
                    reference_a.aggregate, 0.15, 0.30
                ),
                "reference_b_0_15_0_30": frc.band_frc(
                    reference_b.aggregate, 0.15, 0.30
                ),
            },
            "identical_sharpening": heldout_sharpening_sensitivity(
                sums["a"], sums["b"], scene
            ),
            "abba_null": null_result,
            "normalized_abba_null": normalized_null_result,
            "elapsed_seconds": time.perf_counter() - start,
        },
        "raw_null_tiles": null.tiles,
        "normalized_null_tiles": normalized_null.tiles,
    }


def pooled_null(tiles: list[frc.Spectrum]) -> dict[str, object]:
    analysis = frc.Analysis(frc.aggregate_spectra(tiles), tiles)
    result = measure.null_summary(analysis, include_rings=True)
    result["max_midband_snr_bootstrap"] = frc.bootstrap_snr_max(tiles)
    result["bars"] = bars(result)
    result["all_bars_pass"] = all(result["bars"].values())
    return result


def main() -> int:
    groups = registered_groups()
    gate_runs = []
    for group in groups:
        print(
            f"alignment gate: pass {group['pass']} ISO 100 "
            f"({group['files'][0]}..{group['files'][-1]})",
            flush=True,
        )
        gate_runs.append(inspect_group_alignment(group))
    gate_passed = all(run["passes_translation_only_gate"] for run in gate_runs)
    gate_result = {
        "status": "ALIGNMENT_GATE_GREEN" if gate_passed else "ALIGNMENT_GATE_RED",
        "scorecard_translation_rule": (
            "analytic Fourier phase ramp; 0.10 native-pixel local residual limit"
        ),
        "runs": gate_runs,
    }
    write_json(OUT / "alignment-gate.json", gate_result)
    print(
        json.dumps(
            {
                "status": gate_result["status"],
                "runs": [
                    {
                        "pass": run["pass"],
                        "maximum_quadrant_range_quad_pixels": run[
                            "maximum_quadrant_range_quad_pixels"
                        ],
                        "maximum_nontranslation_residual_rms_native_pixels": run[
                            "maximum_nontranslation_residual_rms_native_pixels"
                        ],
                        "passes": run["passes_translation_only_gate"],
                    }
                    for run in gate_runs
                ],
            },
            indent=2,
        ),
        flush=True,
    )
    if not gate_passed:
        print("alignment is not translation-only; amended FRC is forbidden", file=sys.stderr)
        return 2
    if "--alignment-gate-only" in sys.argv:
        return 0

    reports = []
    raw_tiles = []
    normalized_tiles = []
    for group, gate in zip(groups, gate_runs):
        print(f"measuring aligned pass {group['pass']} ISO 100", flush=True)
        processed = process_aligned_group(group, gate)
        reports.append(processed["report"])
        raw_tiles.extend(processed["raw_null_tiles"])
        normalized_tiles.extend(processed["normalized_null_tiles"])

    raw_pooled = pooled_null(raw_tiles)
    normalized_pooled = pooled_null(normalized_tiles)
    conditions = {
        "alignment_gate": gate_passed,
        "each_raw_run_all_null_bars": all(
            report["abba_null"]["all_bars_pass"] for report in reports
        ),
        "each_normalized_run_all_null_bars": all(
            report["normalized_abba_null"]["all_bars_pass"]
            for report in reports
        ),
        "pooled_raw_all_null_bars": raw_pooled["all_bars_pass"],
        "pooled_normalized_all_null_bars": normalized_pooled["all_bars_pass"],
        "real_sharpening_never_improves_crossing": all(
            report["identical_sharpening"]["crossing_movement"] is not None
            and report["identical_sharpening"]["crossing_movement"] <= 1e-6
            for report in reports
        ),
        "both_scene_crossings_not_fallback": all(
            report["scene"]["crossing"]["outcome"]
            in ("MEASURED", "CENSORED_ABOVE")
            for report in reports
        ),
    }
    viable = all(conditions.values())
    result = {
        "status": "MEASURED",
        "verdict": "REPEAT_FRC_VIABLE" if viable else "NO_BUILD",
        "conditions": conditions,
        "scorecard_admission": "UNMEASURED",
        "scorecard_admission_missing": [
            "frozen common-linear RGB boundary",
            "matched independent dark/flat N_floor",
            "target-locked D statistic and eligible source sites",
            "comparator outputs",
            "holdout site manifest",
        ],
        "frequency_contract": {
            "analysis_units": "cycles/quad-pixel",
            "native_conversion": "f_native=f_quad/2",
            "licensed_max_cycles_per_native_pixel": 0.25,
        },
        "runs": reports,
        "raw_pooled_abba_null": raw_pooled,
        "normalized_pooled_abba_null": normalized_pooled,
        "historic_comparison": {
            "split_half_common_mode_low_band_frc": 0.972099,
            "split_half_null_max_midband_snr": 0.438734,
            "snr_bar": 0.25,
        },
        "illumination": (
            "Each light run is measured independently; only within-run pairs "
            "form a null. Disjoint-strip normalization is a sensitivity arm."
        ),
    }
    write_json(OUT / "aligned-measurement.json", result)
    print(
        json.dumps(
            {
                "verdict": result["verdict"],
                "conditions": conditions,
                "run_summary": [
                    {
                        "pass": report["pass"],
                        "alignment_local_range": report["alignment"][
                            "maximum_quadrant_range_quad_pixels"
                        ],
                        "alignment_residual_rms_native": report["alignment"][
                            "maximum_nontranslation_residual_rms_native_pixels"
                        ],
                        "scene_crossing": report["scene"]["licensed_crossing"],
                        "raw_null": {
                            "low_band_frc": report["abba_null"]["band_frc"][0][
                                "frc"
                            ],
                            "max_midband_snr": report["abba_null"][
                                "max_midband_snr"
                            ],
                            "snr_bootstrap": report["abba_null"][
                                "max_midband_snr_bootstrap"
                            ],
                            "all_bars_pass": report["abba_null"]["all_bars_pass"],
                        },
                        "normalized_null": {
                            "low_band_frc": report["normalized_abba_null"][
                                "band_frc"
                            ][0]["frc"],
                            "max_midband_snr": report["normalized_abba_null"][
                                "max_midband_snr"
                            ],
                            "snr_bootstrap": report["normalized_abba_null"][
                                "max_midband_snr_bootstrap"
                            ],
                            "all_bars_pass": report["normalized_abba_null"][
                                "all_bars_pass"
                            ],
                        },
                    }
                    for report in reports
                ],
                "pooled_raw": {
                    "low_band_frc": raw_pooled["band_frc"][0]["frc"],
                    "max_midband_snr": raw_pooled["max_midband_snr"],
                    "snr_bootstrap": raw_pooled["max_midband_snr_bootstrap"],
                    "all_bars_pass": raw_pooled["all_bars_pass"],
                },
                "pooled_normalized": {
                    "low_band_frc": normalized_pooled["band_frc"][0]["frc"],
                    "max_midband_snr": normalized_pooled["max_midband_snr"],
                    "snr_bootstrap": normalized_pooled[
                        "max_midband_snr_bootstrap"
                    ],
                    "all_bars_pass": normalized_pooled["all_bars_pass"],
                },
            },
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ALIGNED MEASUREMENT FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise
