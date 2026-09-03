"""Measure repeat-pair FRC on the commissioned 32-repeat Sony RAW capture."""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import rawpy

import frc


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
CAPTURE = Path(
    r"D:\personal\macro\requests\12-bee-iso-var-no-bracket-32-repeat-diff-light"
)
MANIFEST = OUT / "capture-manifest.json"
EVALUATION_SIDE = 1536
NORMALIZATION_WIDTH = 256
STABILITY_SIDE = 512
EXPECTED_RAW_SHAPE = (4688, 7028)
EXPECTED_PATTERN = [[0, 1], [3, 2]]
EXPECTED_BLACK = [512, 512, 512, 512]
EXPECTED_WHITE = 16383
ABBA = (1.0, -1.0, -1.0, 1.0)


def jsonable(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(jsonable(value), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def quad_region(
    visible: np.ndarray,
    *,
    y: int,
    x: int,
    height: int,
    width: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    green_1 = visible[
        2 * y : 2 * (y + height) : 2,
        2 * x + 1 : 2 * (x + width) + 1 : 2,
    ]
    green_2 = visible[
        2 * y + 1 : 2 * (y + height) + 1 : 2,
        2 * x : 2 * (x + width) : 2,
    ]
    if green_1.shape != (height, width) or green_2.shape != (height, width):
        raise RuntimeError(
            f"quad-green extraction shape mismatch: {green_1.shape}, {green_2.shape}"
        )
    averaged = 0.5 * (
        green_1.astype(np.float32) + green_2.astype(np.float32)
    ) - 512.0
    return averaged, green_1, green_2


def decode_regions(path: Path) -> dict[str, object]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        pattern = raw.raw_pattern.tolist()
        black = list(raw.black_level_per_channel)
        if visible.shape != EXPECTED_RAW_SHAPE:
            raise RuntimeError(f"{path.name}: RAW shape {visible.shape}")
        if pattern != EXPECTED_PATTERN:
            raise RuntimeError(f"{path.name}: Bayer pattern {pattern}")
        if black != EXPECTED_BLACK:
            raise RuntimeError(f"{path.name}: black levels {black}")
        if int(raw.white_level) != EXPECTED_WHITE:
            raise RuntimeError(f"{path.name}: white level {raw.white_level}")

        quad_height = visible.shape[0] // 2
        quad_width = visible.shape[1] // 2
        evaluation_y = (quad_height - EVALUATION_SIDE) // 2
        evaluation_x = (quad_width - EVALUATION_SIDE) // 2
        evaluation, green_1, green_2 = quad_region(
            visible,
            y=evaluation_y,
            x=evaluation_x,
            height=EVALUATION_SIDE,
            width=EVALUATION_SIDE,
        )
        normalization, _, _ = quad_region(
            visible,
            y=evaluation_y,
            x=0,
            height=EVALUATION_SIDE,
            width=NORMALIZATION_WIDTH,
        )
        saturated = int(
            np.count_nonzero((green_1 >= EXPECTED_WHITE) | (green_2 >= EXPECTED_WHITE))
        )
        return {
            "evaluation": evaluation,
            "normalization": normalization,
            "saturated": saturated,
            "pixels": evaluation.size,
            "geometry": {
                "raw_visible": list(visible.shape),
                "quad_green": [quad_height, quad_width],
                "evaluation": [
                    evaluation_y,
                    evaluation_x,
                    EVALUATION_SIDE,
                    EVALUATION_SIDE,
                ],
                "normalization": [
                    evaluation_y,
                    0,
                    EVALUATION_SIDE,
                    NORMALIZATION_WIDTH,
                ],
                "bayer_pattern": pattern,
                "black_levels": black,
                "white_level": int(raw.white_level),
            },
        }


def robust_level(image: np.ndarray) -> float:
    level = float(np.median(image))
    if not math.isfinite(level) or level <= 10.0:
        raise RuntimeError(f"normalization-strip median is unusable: {level}")
    return level


def null_summary(analysis: frc.Analysis, *, include_rings: bool) -> dict[str, object]:
    summary = {
        "mean_abs_frc": frc.mean_abs_frc(analysis.aggregate),
        "max_ring_abs_t": frc.max_ring_null_t(analysis.tiles),
        "band_frc": [
            {
                "low": low,
                "high": high,
                "frc": frc.band_frc(analysis.aggregate, low, high),
            }
            for low, high in frc.NULL_BANDS
        ],
        "max_midband_snr": frc.max_midband_snr(analysis.aggregate),
    }
    if include_rings:
        summary["rings"] = frc.spectrum_rows(analysis.aggregate)
    return summary


def scene_summary(analysis: frc.Analysis, *, include_rings: bool) -> dict[str, object]:
    summary = {
        "crossing": frc.classify(analysis.aggregate),
        "crossing_bootstrap": frc.bootstrap_crossing(analysis.tiles),
        "band_frc": [
            {
                "low": low,
                "high": high,
                "frc": frc.band_frc(analysis.aggregate, low, high),
            }
            for low, high in frc.NULL_BANDS
        ],
    }
    if include_rings:
        summary["rings"] = frc.spectrum_rows(analysis.aggregate)
    return summary


def sharpening_sensitivity(
    scene_a: np.ndarray,
    scene_b: np.ndarray,
    baseline: frc.Analysis,
) -> dict[str, object]:
    sharpened_a = frc.unsharp(scene_a)
    sharpened_b = frc.unsharp(scene_b)
    sharpened = frc.analyse_pair(sharpened_a, sharpened_b)
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


def process_group(
    group: dict[str, object],
    *,
    retain_stability_frames: bool,
) -> dict[str, object]:
    start = time.perf_counter()
    shape = (EVALUATION_SIDE, EVALUATION_SIDE)
    even = np.zeros(shape, dtype=np.float64)
    odd = np.zeros(shape, dtype=np.float64)
    difference_1 = np.zeros(shape, dtype=np.float64)
    difference_2 = np.zeros(shape, dtype=np.float64)
    normalized_difference_1 = np.zeros(shape, dtype=np.float64)
    normalized_difference_2 = np.zeros(shape, dtype=np.float64)
    total = np.zeros(shape, dtype=np.float64)
    normalization_total = np.zeros(
        (EVALUATION_SIDE, NORMALIZATION_WIDTH), dtype=np.float64
    )
    levels = []
    saturated = 0
    pixels = 0
    stability_frames = []
    geometry = None

    for index, filename in enumerate(group["files"]):
        decoded = decode_regions(CAPTURE / str(filename))
        evaluation = decoded["evaluation"]
        normalization = decoded["normalization"]
        geometry = decoded["geometry"]
        level = robust_level(normalization)
        levels.append(level)
        saturated += int(decoded["saturated"])
        pixels += int(decoded["pixels"])

        total += evaluation
        normalization_total += normalization
        if index % 2 == 0:
            even += evaluation
        else:
            odd += evaluation

        block = index // 4
        weight = ABBA[index % 4]
        target = block % 2
        if target == 0:
            difference_1 += weight * evaluation
            normalized_difference_1 += weight * (evaluation / level)
        else:
            difference_2 += weight * evaluation
            normalized_difference_2 += weight * (evaluation / level)

        if retain_stability_frames:
            offset = (EVALUATION_SIDE - STABILITY_SIDE) // 2
            stability_frames.append(
                evaluation[
                    offset : offset + STABILITY_SIDE,
                    offset : offset + STABILITY_SIDE,
                ].copy()
            )

    scene_a = even / 16.0
    scene_b = odd / 16.0
    # Each contrast has eight positive and eight negative observations.
    difference_1 /= 8.0
    difference_2 /= 8.0
    normalized_difference_1 /= 8.0
    normalized_difference_2 /= 8.0
    mean_image = total / 32.0
    mean_normalization = normalization_total / 32.0

    stability = None
    if retain_stability_frames:
        readings = frc.stability_readings(stability_frames)
        try:
            frc.stability_gate(stability_frames)
        except ValueError as error:
            stability = {
                "status": "RED",
                "error": str(error),
                **readings,
            }
        else:
            stability = {"status": "GREEN", **readings}

    level_mean = float(np.mean(levels))
    level_cv = float(np.std(levels) / level_mean)
    result: dict[str, object] = {
        "pass": int(group["pass"]),
        "iso": int(group["iso"]),
        "first_file": str(group["files"][0]),
        "last_file": str(group["files"][-1]),
        "photometric_strip_level": {
            "minimum": min(levels),
            "maximum": max(levels),
            "mean": level_mean,
            "cv": level_cv,
        },
        "saturated_quad_samples": saturated,
        "saturated_fraction": saturated / pixels,
        "pixel_stability": stability,
        "elapsed_seconds": time.perf_counter() - start,
    }
    if stability is not None and stability["status"] == "RED":
        # Eligibility is load-bearing. Do not even calculate an FRC outcome
        # after it fails, so no unregistered result can influence the STOP.
        return {
            "report": result,
            "geometry": geometry,
        }

    scene_analysis = frc.analyse_pair(scene_a, scene_b)
    null_analysis = frc.analyse_pair(difference_1, difference_2)
    normalized_null_analysis = frc.analyse_pair(
        normalized_difference_1,
        normalized_difference_2,
    )
    result.update({
        "scene": scene_summary(scene_analysis, include_rings=True),
        "scene_identical_sharpening": sharpening_sensitivity(
            scene_a, scene_b, scene_analysis
        ),
        "abba_null": null_summary(null_analysis, include_rings=True),
        "normalized_abba_null": null_summary(
            normalized_null_analysis, include_rings=True
        ),
        "elapsed_seconds": time.perf_counter() - start,
    })
    return {
        "report": result,
        "geometry": geometry,
        "mean_image": mean_image,
        "mean_normalization": mean_normalization,
        "raw_null_tiles": null_analysis.tiles,
        "normalized_null_tiles": normalized_null_analysis.tiles,
    }


def cross_light(
    first: dict[str, np.ndarray],
    second: dict[str, np.ndarray],
) -> dict[str, object]:
    norm_a = first["normalization"]
    norm_b = second["normalization"]
    denominator = float(np.sum(norm_b * norm_b))
    if denominator <= 0.0:
        raise RuntimeError("cross-light normalization fit has zero denominator")
    scale = float(np.sum(norm_a * norm_b) / denominator)
    image_a = first["image"]
    image_b = scale * second["image"]
    analysis = frc.analyse_pair(image_a, image_b)
    residual = image_a - image_b
    centred = image_a - float(np.mean(image_a))
    relative_residual_rms = float(
        np.sqrt(np.mean(residual * residual))
        / max(np.sqrt(np.mean(centred * centred)), 1e-30)
    )
    return {
        "pass2_to_pass1_scale": scale,
        "normalization_strip_fit_relative_rms": float(
            np.sqrt(np.mean((norm_a - scale * norm_b) ** 2))
            / max(np.sqrt(np.mean((norm_a - float(np.mean(norm_a))) ** 2)), 1e-30)
        ),
        "evaluation_relative_residual_rms": relative_residual_rms,
        "scene": scene_summary(analysis, include_rings=True),
    }


def pooled_null(
    tiles: list[frc.Spectrum],
    *,
    include_rings: bool,
) -> dict[str, object]:
    analysis = frc.Analysis(frc.aggregate_spectra(tiles), tiles)
    summary = null_summary(analysis, include_rings=include_rings)
    summary["max_midband_snr_bootstrap"] = frc.bootstrap_snr_max(tiles)
    summary["bars"] = {
        "mean_abs_frc_lt_0_05": summary["mean_abs_frc"] < 0.05,
        "max_ring_abs_t_lt_4": summary["max_ring_abs_t"] < 4.0,
        "bands_abs_lt_0_08": all(
            abs(row["frc"]) < 0.08 for row in summary["band_frc"]
        ),
        "snr_point_lt_0_25": summary["max_midband_snr"] < 0.25,
        "snr_upper_95_lt_0_25": summary["max_midband_snr_bootstrap"][
            "interval_95"
        ][1]
        < 0.25,
    }
    summary["all_bars_pass"] = all(summary["bars"].values())
    return summary


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["status"] != "METADATA_VALIDATED":
        raise RuntimeError("capture metadata gate is not GREEN")
    groups = manifest["groups"]
    gate_group = next(
        group for group in groups if group["pass"] == 1 and group["iso"] == 50
    )

    print("pixel gate: pass 1 ISO 50 (32 RAWs)", flush=True)
    gate = process_group(gate_group, retain_stability_frames=True)
    pixel_gate_passed = gate["report"]["pixel_stability"]["status"] == "GREEN"
    pixel_gate = {
        "status": "PIXEL_GATE_GREEN" if pixel_gate_passed else "PIXEL_GATE_RED",
        "pass": 1,
        "iso": 50,
        "first_file": gate_group["files"][0],
        "last_file": gate_group["files"][-1],
        "geometry": gate["geometry"],
        "stability": gate["report"]["pixel_stability"],
        "photometric_strip_level": gate["report"]["photometric_strip_level"],
        "saturated_fraction": gate["report"]["saturated_fraction"],
    }
    write_json(OUT / "pixel-gate.json", pixel_gate)
    print(json.dumps(jsonable(pixel_gate), indent=2), flush=True)
    if not pixel_gate_passed:
        print("eligibility gate failed; real FRC measurement is forbidden", file=sys.stderr)
        return 2
    if "--gate-only" in sys.argv:
        return 0

    ordered = [gate_group] + [group for group in groups if group is not gate_group]
    group_outputs = []
    raw_null_tiles: list[frc.Spectrum] = []
    normalized_null_tiles: list[frc.Spectrum] = []
    pass_one: dict[int, dict[str, np.ndarray]] = {}
    cross_light_outputs = []
    geometry = gate["geometry"]

    for group_index, group in enumerate(ordered):
        if group is gate_group:
            processed = gate
        else:
            print(
                f"group {group_index + 1:02d}/18: pass {group['pass']} "
                f"ISO {group['iso']} ({group['files'][0]}..{group['files'][-1]})",
                flush=True,
            )
            processed = process_group(group, retain_stability_frames=False)
        group_outputs.append(processed["report"])
        raw_null_tiles.extend(processed["raw_null_tiles"])
        normalized_null_tiles.extend(processed["normalized_null_tiles"])

        iso = int(group["iso"])
        pair_value = {
            "image": processed["mean_image"],
            "normalization": processed["mean_normalization"],
        }
        if int(group["pass"]) == 1:
            pass_one[iso] = pair_value
        else:
            comparison = cross_light(pass_one.pop(iso), pair_value)
            comparison["iso"] = iso
            cross_light_outputs.append(comparison)

    if pass_one:
        raise RuntimeError(f"unmatched pass-one groups: {sorted(pass_one)}")

    raw_pooled = pooled_null(raw_null_tiles, include_rings=True)
    normalized_pooled = pooled_null(normalized_null_tiles, include_rings=True)
    group_ladder_raw = {
        f"pass{row['pass']}_iso{row['iso']}": row["abba_null"][
            "max_midband_snr"
        ]
        for row in group_outputs
    }
    group_ladder_normalized = {
        f"pass{row['pass']}_iso{row['iso']}": row["normalized_abba_null"][
            "max_midband_snr"
        ]
        for row in group_outputs
    }
    group_raw_pass = {
        key: value < 0.25 for key, value in group_ladder_raw.items()
    }
    group_normalized_pass = {
        key: value < 0.25 for key, value in group_ladder_normalized.items()
    }
    verdict_conditions = {
        "raw_pooled_all_bars": raw_pooled["all_bars_pass"],
        "normalized_pooled_all_bars": normalized_pooled["all_bars_pass"],
        "all_raw_group_snr_bars": all(group_raw_pass.values()),
        "all_normalized_group_snr_bars": all(group_normalized_pass.values()),
        "all_scene_crossings_measured": all(
            row["scene"]["crossing"]["outcome"] == "MEASURED"
            and row["scene"]["crossing_bootstrap"]["measured_fraction"] >= 0.9
            for row in group_outputs
        ),
        "all_sharpening_non_improving": all(
            row["scene_identical_sharpening"]["crossing_movement"] is not None
            and row["scene_identical_sharpening"]["crossing_movement"] <= 1e-6
            for row in group_outputs
        ),
        "all_cross_light_crossings_measured": all(
            row["scene"]["crossing"]["outcome"] == "MEASURED"
            and row["scene"]["crossing_bootstrap"]["measured_fraction"] >= 0.9
            for row in cross_light_outputs
        ),
    }
    verdict = "SALVAGE_BUILD" if all(verdict_conditions.values()) else "NO_BUILD"

    result = {
        "status": "MEASURED",
        "verdict": verdict,
        "verdict_conditions": verdict_conditions,
        "capture": str(CAPTURE),
        "metadata_manifest": str(MANIFEST.relative_to(LANE)),
        "geometry": geometry,
        "partition": {
            "scene": "mean even frames versus mean odd frames",
            "null": (
                "ABBA (+1,-1,-1,+1) within four-frame blocks; "
                "alternating disjoint blocks form D1,D2"
            ),
        },
        "raw_pooled_abba_null": raw_pooled,
        "normalized_pooled_abba_null": normalized_pooled,
        "group_ladder_raw_max_midband_snr": group_ladder_raw,
        "group_ladder_raw_pass": group_raw_pass,
        "group_ladder_normalized_max_midband_snr": group_ladder_normalized,
        "group_ladder_normalized_pass": group_normalized_pass,
        "groups": sorted(group_outputs, key=lambda row: (row["pass"], row["iso"])),
        "cross_light": sorted(cross_light_outputs, key=lambda row: row["iso"]),
        "comparison_constants": {
            "historic_split_half_common_mode_low_band_frc": 0.972099,
            "historic_split_half_null_mean_max_midband_snr": 0.438734,
            "historic_snr_bar": 0.25,
        },
        "interpretation_limit": (
            "ABBA differences cancel stable scene, PRNU/DSNU, and deterministic "
            "quantisation together; a passing temporal null cannot bound those "
            "terms in ordinary scene-pair FRC."
        ),
    }
    write_json(OUT / "measurement.json", result)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "verdict_conditions": verdict_conditions,
                "raw_pooled": {
                    key: raw_pooled[key]
                    for key in (
                        "mean_abs_frc",
                        "max_ring_abs_t",
                        "band_frc",
                        "max_midband_snr",
                        "max_midband_snr_bootstrap",
                        "all_bars_pass",
                    )
                },
                "normalized_pooled": {
                    key: normalized_pooled[key]
                    for key in (
                        "mean_abs_frc",
                        "max_ring_abs_t",
                        "band_frc",
                        "max_midband_snr",
                        "max_midband_snr_bootstrap",
                        "all_bars_pass",
                    )
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"MEASUREMENT FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        raise
