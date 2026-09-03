"""Measure C2's per-channel through-focus offsets on controlled RAW stacks.

Run only after ``commission.py`` succeeds.  The first pass obtains one common
integer registration track from G1.  The second pass measures native-CFA Sobel
energy curves for all registered tile sizes and an unregistered dissenting arm.
No rendered image, demosaic, white balance, or colour matrix enters the path.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

from lca_lib import (
    CHANNELS,
    FIXTURES,
    LANE,
    OUT,
    REPO,
    capture_inventory,
    decode_visible,
    environment_record,
    extract_patches,
    file_sha256,
    interpolate_curves,
    median_ci,
    numerical_dependency_record,
    offset_values,
    peak_fit,
    phase_shift,
    robust_polynomial_track,
    sobel_energy_means,
    split_cfa,
    tile_centres,
    write_json,
)


STACKS = {
    "grid_sw1": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw1-cpl"
        ),
        "expected_frames": 91,
        "subject": "grid",
        "step_width": 1,
        "aperture": 5.6,
        "primary": False,
    },
    "grid_sw4": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw4-cpl"
        ),
        "expected_frames": 55,
        "subject": "grid",
        "step_width": 4,
        "aperture": 5.6,
        "primary": True,
    },
    "grid_sw10": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw10-cpl"
        ),
        "expected_frames": 23,
        "subject": "grid",
        "step_width": 10,
        "aperture": 5.6,
        "primary": False,
    },
    "fabric_f11_sw5": {
        "path": Path(
            r"D:\personal\macro\requests\7-aperture-pairs"
            r"\fabric-weave-f11-sw5-cpl"
        ),
        "expected_frames": 109,
        "subject": "fabric",
        "step_width": 5,
        "aperture": 11.0,
        "primary": True,
    },
    "ruler_f11_sw7": {
        "path": Path(
            r"D:\personal\macro\requests\8-tilted-planar"
            r"\ruler-incline-ang10.26deg-inches-f11-sw7-cpl"
        ),
        "expected_frames": 65,
        "subject": "ruler",
        "step_width": 7,
        "aperture": 11.0,
        "primary": True,
    },
}
PRIMARY = ("grid_sw4", "fabric_f11_sw5", "ruler_f11_sw7")
STEP_LADDER = ("grid_sw1", "grid_sw4", "grid_sw10")

TILE_SIDES = (96, 144, 192)
PRIMARY_SIDE = 144
ARMS = ("registered", "unregistered")
PRIMARY_ARM = "registered"
BASELINE_LADDER = (0.0, 5.0, 10.0)
PRIMARY_BASELINE = 5.0
PROMINENCE_LADDER = (1.2, 1.5, 2.0)
PRIMARY_PROMINENCE = 1.5
CORRELATION_SIDE = 256
REGISTRATION_STRIDE = 4
TILE_ROWS = 6
TILE_COLUMNS = 8
TILE_MARGIN = 320
PRIMARY_DRAWS = 10_000
LADDER_DRAWS = 4_000
SEED = 20260902


def stable_seed(label: str, extra: int = 0) -> int:
    digest = hashlib.sha256(label.encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "little") + SEED + extra) % (2**32)


def stack_files(spec: dict) -> list[Path]:
    files = sorted(spec["path"].glob("*.ARW"), key=lambda path: path.name.lower())
    if len(files) != spec["expected_frames"]:
        raise RuntimeError(
            f"{spec['path']}: expected {spec['expected_frames']} frames, "
            f"found {len(files)}"
        )
    return files


def config_record() -> dict:
    return {
        "tile_sides_plane_px": list(TILE_SIDES),
        "primary_tile_side_plane_px": PRIMARY_SIDE,
        "arms": list(ARMS),
        "primary_arm": PRIMARY_ARM,
        "baseline_percentile_ladder": list(BASELINE_LADDER),
        "primary_baseline_percentile": PRIMARY_BASELINE,
        "prominence_ladder": list(PROMINENCE_LADDER),
        "primary_prominence": PRIMARY_PROMINENCE,
        "correlation_side_plane_px": CORRELATION_SIDE,
        "registration_stride_frames": REGISTRATION_STRIDE,
        "tile_grid": [TILE_ROWS, TILE_COLUMNS],
        "tile_margin_plane_px": TILE_MARGIN,
        "bootstrap_draws_primary": PRIMARY_DRAWS,
        "bootstrap_draws_ladder": LADDER_DRAWS,
        "seed": SEED,
        "peak_fit": "baseline-subtracted log-domain three-point parabola",
        "focus_operator": "native-CFA 3x3 Sobel Gx^2+Gy^2 tile mean",
    }


def cache_fingerprint(label: str, spec: dict, files: list[Path]) -> str:
    payload = {
        "label": label,
        "config": config_record(),
        "files": [
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
            }
            for path in files
        ],
        "source_sha256": {
            "measure.py": file_sha256(Path(__file__)),
            "lca_lib.py": file_sha256(Path(__file__).with_name("lca_lib.py")),
        },
        "numerical_dependencies": numerical_dependency_record(),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def crop_at(plane: np.ndarray, centre: np.ndarray, side: int) -> np.ndarray:
    row, column = (int(v) for v in centre)
    half = side // 2
    crop = plane[row - half : row + half, column - half : column + half]
    if crop.shape != (side, side):
        raise ValueError(f"correlation crop leaves plane at {centre.tolist()}")
    return crop


def registration_pass(
    files: list[Path],
    centres: np.ndarray,
    reference_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    nframe = len(files)
    sampled = np.unique(
        np.r_[
            np.arange(0, nframe, REGISTRATION_STRIDE),
            nframe - 1,
            reference_index,
        ]
    ).astype(np.int32)
    ref_mosaic, ref_meta = decode_visible(files[reference_index])
    reference = split_cfa(ref_mosaic, ref_meta["black_levels"])["G1"]
    ref_crops = [
        crop_at(reference, centre, CORRELATION_SIDE) for centre in centres
    ]
    raw_dy = np.zeros((sampled.size, centres.shape[0]), dtype=np.float64)
    raw_dx = np.zeros_like(raw_dy)
    raw_peak = np.zeros_like(raw_dy)

    started = time.perf_counter()
    for sample_index, frame_index in enumerate(sampled):
        if frame_index == reference_index:
            green = reference
        else:
            mosaic, metadata = decode_visible(files[int(frame_index)])
            if metadata["shape"] != ref_meta["shape"]:
                raise RuntimeError(f"geometry changed at {files[int(frame_index)]}")
            green = split_cfa(mosaic, metadata["black_levels"])["G1"]
        for tile_index, centre in enumerate(centres):
            dy, dx, peak = phase_shift(
                ref_crops[tile_index],
                crop_at(green, centre, CORRELATION_SIDE),
            )
            raw_dy[sample_index, tile_index] = dy
            raw_dx[sample_index, tile_index] = dx
            raw_peak[sample_index, tile_index] = peak
        if sample_index % 8 == 0 or sample_index + 1 == sampled.size:
            print(
                f"    registration {sample_index + 1:3d}/{sampled.size}"
                f" ({time.perf_counter() - started:.1f}s)",
                flush=True,
            )

    track_y = np.zeros((nframe, centres.shape[0]), dtype=np.int32)
    track_x = np.zeros_like(track_y)
    tile_records = []
    registration_ok = np.zeros(centres.shape[0], dtype=bool)
    for tile_index in range(centres.shape[0]):
        fitted_y, record_y = robust_polynomial_track(
            sampled, raw_dy[:, tile_index], nframe
        )
        fitted_x, record_x = robust_polynomial_track(
            sampled, raw_dx[:, tile_index], nframe
        )
        fitted_y -= fitted_y[reference_index]
        fitted_x -= fitted_x[reference_index]
        track_y[:, tile_index] = fitted_y
        track_x[:, tile_index] = fitted_x
        registration_ok[tile_index] = record_y["ok"] and record_x["ok"]
        tile_records.append(
            {
                "tile": tile_index,
                "y": record_y,
                "x": record_x,
                "ok": bool(registration_ok[tile_index]),
                "correlation_peak_median": float(
                    np.median(raw_peak[:, tile_index])
                ),
            }
        )

    record = {
        "reference_index": reference_index,
        "sampled_indices": sampled.tolist(),
        "tile_records": tile_records,
        "tiles_ok": int(np.sum(registration_ok)),
        "tiles_total": int(registration_ok.size),
        "raw_shift_y_range": [float(np.min(raw_dy)), float(np.max(raw_dy))],
        "raw_shift_x_range": [float(np.min(raw_dx)), float(np.max(raw_dx))],
        "fit_shift_y_range": [int(np.min(track_y)), int(np.max(track_y))],
        "fit_shift_x_range": [int(np.min(track_x)), int(np.max(track_x))],
    }
    return track_y, track_x, registration_ok, {
        "record": record,
        "sampled": sampled,
        "raw_dy": raw_dy,
        "raw_dx": raw_dx,
        "raw_peak": raw_peak,
    }


def build_stack_cache(label: str, spec: dict) -> tuple[Path, bool]:
    files = stack_files(spec)
    fingerprint = cache_fingerprint(label, spec, files)
    cache_path = OUT / "curves" / f"{label}.npz"
    if cache_path.exists():
        with np.load(cache_path, allow_pickle=False) as cached:
            saved_fingerprint = str(cached["fingerprint"].item())
        if saved_fingerprint == fingerprint:
            print(f"  {label}: reuse commissioned cache {cache_path}")
            return cache_path, True

    first_mosaic, first_meta = decode_visible(files[0])
    first_planes = split_cfa(first_mosaic, first_meta["black_levels"])
    plane_shape = first_planes["G1"].shape
    centres = tile_centres(
        plane_shape,
        rows=TILE_ROWS,
        columns=TILE_COLUMNS,
        margin=TILE_MARGIN,
    )
    centre_y = plane_shape[0] / 2.0
    centre_x = plane_shape[1] / 2.0
    radii = np.hypot(centres[:, 0] - centre_y, centres[:, 1] - centre_x)
    reference_index = len(files) // 2

    print(
        f"  {label}: {len(files)} frames, plane {plane_shape}, "
        f"{centres.shape[0]} tiles"
    )
    track_y, track_x, registration_ok, registration = registration_pass(
        files, centres, reference_index
    )

    responses = np.zeros(
        (
            len(ARMS),
            len(TILE_SIDES),
            len(CHANNELS),
            len(files),
            centres.shape[0],
        ),
        dtype=np.float32,
    )
    zeros = np.zeros((centres.shape[0], 2), dtype=np.int32)
    started = time.perf_counter()
    for frame_index, path in enumerate(files):
        mosaic, metadata = decode_visible(path)
        if (
            metadata["shape"] != first_meta["shape"]
            or metadata["pattern"] != first_meta["pattern"]
            or metadata["black_levels"] != first_meta["black_levels"]
        ):
            raise RuntimeError(f"RAW contract changed at {path}")
        planes = split_cfa(mosaic, metadata["black_levels"])
        registered = np.stack(
            [track_y[frame_index], track_x[frame_index]], axis=1
        )
        for arm_index, shifts in enumerate((registered, zeros)):
            for channel_index, channel in enumerate(CHANNELS):
                patches = extract_patches(
                    planes[channel],
                    centres,
                    shifts,
                    side=max(TILE_SIDES),
                )
                responses[
                    arm_index, :, channel_index, frame_index, :
                ] = sobel_energy_means(patches, TILE_SIDES).astype(np.float32)
        if frame_index % 10 == 0 or frame_index + 1 == len(files):
            print(
                f"    focus {frame_index + 1:3d}/{len(files)}"
                f" ({time.perf_counter() - started:.1f}s)",
                flush=True,
            )

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_record = {
        "label": label,
        "spec": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in spec.items()
        },
        "files": [str(path) for path in files],
        "first_metadata": first_meta,
        "plane_shape": list(plane_shape),
        "config": config_record(),
        "fingerprint": fingerprint,
        "registration": registration["record"],
        "elapsed_focus_seconds": time.perf_counter() - started,
    }
    np.savez_compressed(
        cache_path,
        responses=responses,
        centres=centres,
        radii=radii,
        track_y=track_y,
        track_x=track_x,
        registration_ok=registration_ok,
        reg_sampled=registration["sampled"],
        reg_raw_dy=registration["raw_dy"],
        reg_raw_dx=registration["raw_dx"],
        reg_raw_peak=registration["raw_peak"],
        metadata=np.array(json.dumps(metadata_record, sort_keys=True)),
        fingerprint=np.array(fingerprint),
    )
    print(f"    wrote {cache_path}")
    return cache_path, False


def summarise_cache(
    cache_path: Path,
    *,
    side: int = PRIMARY_SIDE,
    arm: str = PRIMARY_ARM,
    baseline_percentile: float = PRIMARY_BASELINE,
    prominence: float = PRIMARY_PROMINENCE,
    mode: str = "log",
    draws: int = PRIMARY_DRAWS,
) -> dict:
    with np.load(cache_path, allow_pickle=False) as cache:
        responses = cache["responses"].astype(np.float64)
        centres = cache["centres"]
        radii = cache["radii"].astype(np.float64)
        registration_ok = cache["registration_ok"].astype(bool)
        metadata = json.loads(str(cache["metadata"].item()))

    arm_index = ARMS.index(arm)
    side_index = TILE_SIDES.index(side)
    curves = {
        channel: responses[
            arm_index, side_index, channel_index, :, :
        ]
        for channel_index, channel in enumerate(CHANNELS)
    }
    fits = {
        channel: peak_fit(
            curve,
            baseline_percentile=baseline_percentile,
            mode=mode,
            prominence_min=prominence,
        )
        for channel, curve in curves.items()
    }
    valid = np.ones(centres.shape[0], dtype=bool)
    for channel in CHANNELS:
        valid &= fits[channel].valid
    if arm == "registered":
        valid &= registration_ok

    delta_r, delta_b, delta_null = offset_values(fits)
    seed = stable_seed(
        f"{metadata['label']}:{side}:{arm}:{baseline_percentile}:"
        f"{prominence}:{mode}"
    )
    summaries = {
        "delta_r": median_ci(delta_r[valid], draws=draws, seed=seed),
        "delta_b": median_ci(delta_b[valid], draws=draws, seed=seed + 1),
        "delta_null": median_ci(
            delta_null[valid], draws=draws, seed=seed + 2
        ),
    }

    green_peak = 0.5 * (fits["G1"].peak + fits["G2"].peak)
    red_own = interpolate_curves(curves["R"], fits["R"].peak)
    red_at_green = interpolate_curves(curves["R"], green_peak)
    blue_own = interpolate_curves(curves["B"], fits["B"].peak)
    blue_at_green = interpolate_curves(curves["B"], green_peak)
    red_loss = 1.0 - red_at_green / np.maximum(red_own, 1.0e-12)
    blue_loss = 1.0 - blue_at_green / np.maximum(blue_own, 1.0e-12)

    green_curve = 0.5 * (curves["G1"] + curves["G2"])
    green_base = np.percentile(green_curve, baseline_percentile, axis=0)
    green_max = np.max(green_curve, axis=0)
    half = green_base + 0.5 * (green_max - green_base)
    hwhm = 0.5 * np.sum(green_curve > half[None, :], axis=0)

    max_radius = float(np.hypot(metadata["plane_shape"][0] / 2, metadata["plane_shape"][1] / 2))
    radial_edges = np.quantile(radii, np.linspace(0.0, 1.0, 5))
    radial_edges[-1] += 1.0e-9
    radial = []
    for index in range(4):
        selected = valid & (radii >= radial_edges[index]) & (radii < radial_edges[index + 1])
        radial.append(
            {
                "quartile": index + 1,
                "radius_plane_px": [
                    float(radial_edges[index]),
                    float(radial_edges[index + 1]),
                ],
                "n_valid": int(np.sum(selected)),
                "delta_r_median": (
                    float(np.median(delta_r[selected])) if np.any(selected) else None
                ),
                "delta_b_median": (
                    float(np.median(delta_b[selected])) if np.any(selected) else None
                ),
                "delta_null_median": (
                    float(np.median(delta_null[selected]))
                    if np.any(selected)
                    else None
                ),
            }
        )

    tile_rows = []
    for index, centre in enumerate(centres):
        tile_rows.append(
            {
                "tile": index,
                "centre_plane_yx": [int(centre[0]), int(centre[1])],
                "radius_plane_px": float(radii[index]),
                "radius_fraction_of_corner": float(radii[index] / max_radius),
                "registration_ok": bool(registration_ok[index]),
                "valid": bool(valid[index]),
                "peak_r": float(fits["R"].peak[index]),
                "peak_g1": float(fits["G1"].peak[index]),
                "peak_g2": float(fits["G2"].peak[index]),
                "peak_b": float(fits["B"].peak[index]),
                "prominence_r": float(fits["R"].prominence[index]),
                "prominence_g1": float(fits["G1"].prominence[index]),
                "prominence_g2": float(fits["G2"].prominence[index]),
                "prominence_b": float(fits["B"].prominence[index]),
                "delta_r": float(delta_r[index]),
                "delta_b": float(delta_b[index]),
                "delta_null": float(delta_null[index]),
            }
        )

    valid_count = int(np.sum(valid))
    return {
        "label": metadata["label"],
        "spec": metadata["spec"],
        "analysis": {
            "tile_side_plane_px": side,
            "arm": arm,
            "baseline_percentile": baseline_percentile,
            "prominence_min": prominence,
            "peak_mode": mode,
            "bootstrap_draws": draws,
        },
        "n_tiles_total": int(valid.size),
        "n_tiles_valid": valid_count,
        "valid_fraction": float(np.mean(valid)),
        "registration": metadata["registration"],
        "summaries": summaries,
        "median_red_gradient_energy_forfeit": (
            float(np.median(red_loss[valid])) if valid_count else None
        ),
        "median_blue_gradient_energy_forfeit": (
            float(np.median(blue_loss[valid])) if valid_count else None
        ),
        "median_green_hwhm_frames": (
            float(np.median(hwhm[valid])) if valid_count else None
        ),
        "radial_quartiles": radial,
        "tile_rows": tile_rows,
    }


def valid_values(summary: dict, name: str, radius_group: str | None = None) -> np.ndarray:
    rows = summary["tile_rows"]
    keep = [row for row in rows if row["valid"]]
    if radius_group == "centre":
        keep = [
            row for row in keep if row["radius_fraction_of_corner"] <= 0.35
        ]
    elif radius_group and radius_group.startswith("q"):
        quartile = int(radius_group[1:])
        ordered = sorted(
            range(len(rows)), key=lambda index: rows[index]["radius_plane_px"]
        )
        chunks = np.array_split(np.asarray(ordered), 4)
        selected = set(int(index) for index in chunks[quartile - 1])
        keep = [row for row in keep if row["tile"] in selected]
    return np.asarray([row[name] for row in keep], dtype=np.float64)


def classify_interval(
    lower: float,
    upper: float,
    negative_count: int,
    subject_count: int,
    null_gate: bool,
) -> str:
    if not null_gate:
        return "VOID_NULL_GATE"
    if negative_count <= 1:
        return "KILL"
    if lower >= 0.50 and negative_count == subject_count:
        return "SURVIVE"
    if lower >= 0.25 and negative_count == subject_count:
        return "NARROWED"
    if upper < 0.25:
        return "KILL"
    return "INDETERMINATE"


def combined_actionability(
    summaries: list[dict],
    *,
    draws: int,
    seed: int,
    radius_group: str | None = None,
) -> dict:
    red_values = [
        valid_values(summary, "delta_r", radius_group) for summary in summaries
    ]
    null_values = [
        valid_values(summary, "delta_null", radius_group)
        for summary in summaries
    ]
    if any(values.size < 2 for values in red_values + null_values):
        return {
            "category": "INDETERMINATE",
            "reason": "fewer than two valid tiles in a subject stratum",
            "radius_group": radius_group,
        }

    rng = np.random.default_rng(seed)
    boot_medians = []
    null_records = []
    point_medians = []
    for index, values in enumerate(red_values):
        indices = rng.integers(0, values.size, size=(draws, values.size))
        boot = np.median(values[indices], axis=1)
        boot_medians.append(boot)
        point_medians.append(float(np.median(values)))

        null = null_values[index]
        null_indices = rng.integers(0, null.size, size=(draws, null.size))
        null_boot = np.median(null[null_indices], axis=1)
        null_median = float(np.median(null))
        null_ci = [
            float(np.percentile(null_boot, 2.5)),
            float(np.percentile(null_boot, 97.5)),
        ]
        null_half = max(
            abs(null_ci[0] - null_median), abs(null_ci[1] - null_median)
        )
        null_records.append(
            {
                "label": summaries[index]["label"],
                "median": null_median,
                "ci95": null_ci,
                "abs_median_plus_halfwidth": abs(null_median) + null_half,
                "passes_0p125": abs(null_median) + null_half < 0.125,
            }
        )

    actionability_boot = np.min(np.abs(np.stack(boot_medians, axis=1)), axis=1)
    interval = [
        float(np.percentile(actionability_boot, 2.5)),
        float(np.percentile(actionability_boot, 97.5)),
    ]
    point = float(np.min(np.abs(point_medians)))
    negative_count = sum(value < 0.0 for value in point_medians)
    null_gate = all(record["passes_0p125"] for record in null_records)
    category = classify_interval(
        interval[0],
        interval[1],
        negative_count,
        len(point_medians),
        null_gate,
    )
    return {
        "category": category,
        "radius_group": radius_group,
        "A_min_abs_subject_median_frames": point,
        "A_ci95_frames": interval,
        "subject_delta_r_medians_frames": {
            summary["label"]: point_medians[index]
            for index, summary in enumerate(summaries)
        },
        "negative_subjects": negative_count,
        "subject_count": len(summaries),
        "null_gate_passed": null_gate,
        "null_records": null_records,
        "bootstrap_draws": draws,
        "seed": seed,
    }


def single_stack_category(summary: dict, *, draws: int, seed: int) -> dict:
    red = valid_values(summary, "delta_r")
    null = valid_values(summary, "delta_null")
    if red.size < 2 or null.size < 2:
        return {"category": "INDETERMINATE", "reason": "too few valid tiles"}
    rng = np.random.default_rng(seed)
    red_boot = np.median(
        red[rng.integers(0, red.size, size=(draws, red.size))], axis=1
    )
    magnitude = np.abs(red_boot)
    interval = [
        float(np.percentile(magnitude, 2.5)),
        float(np.percentile(magnitude, 97.5)),
    ]
    null_boot = np.median(
        null[rng.integers(0, null.size, size=(draws, null.size))], axis=1
    )
    null_median = float(np.median(null))
    null_ci = [
        float(np.percentile(null_boot, 2.5)),
        float(np.percentile(null_boot, 97.5)),
    ]
    null_half = max(
        abs(null_ci[0] - null_median), abs(null_ci[1] - null_median)
    )
    null_gate = abs(null_median) + null_half < 0.125
    negative = int(np.median(red) < 0)
    category = classify_interval(interval[0], interval[1], negative, 1, null_gate)
    # For one stack, the preregistered sign requirement is simply negative.
    if null_gate and negative:
        if interval[0] >= 0.50:
            category = "SURVIVE"
        elif interval[0] >= 0.25:
            category = "NARROWED"
        elif interval[1] < 0.25:
            category = "KILL"
        else:
            category = "INDETERMINATE"
    elif null_gate:
        category = "KILL"
    return {
        "category": category,
        "delta_r_median_frames": float(np.median(red)),
        "abs_delta_r_ci95_frames": interval,
        "delta_null_median_frames": null_median,
        "delta_null_ci95_frames": null_ci,
        "null_gate_passed": null_gate,
        "n_tiles": int(red.size),
    }


def main() -> int:
    commission_path = OUT / "commission.json"
    if not commission_path.exists():
        raise RuntimeError("run commission.py before measure.py")
    with commission_path.open("r", encoding="utf-8") as handle:
        commission = json.load(handle)
    if not commission["summary"]["all_passed"]:
        raise RuntimeError("commission.json is not green")
    commission_inputs = [
        Path(__file__).with_name("commission.py").resolve(),
        Path(__file__).with_name("lca_lib.py").resolve(),
        *sorted(FIXTURES.glob("*.json")),
    ]
    current_commission_hashes = {
        path.relative_to(LANE).as_posix(): file_sha256(path)
        for path in commission_inputs
    }
    if commission.get("input_sha256") != current_commission_hashes:
        raise RuntimeError(
            "commission inputs drifted; rerun commission.py before measurement"
        )

    before = {
        label: capture_inventory(spec["path"]) for label, spec in STACKS.items()
    }
    cache_paths = {}
    cache_reused = {}
    for label, spec in STACKS.items():
        cache_paths[label], cache_reused[label] = build_stack_cache(label, spec)

    primary_summaries = {
        label: summarise_cache(cache_paths[label]) for label in STACKS
    }
    primary = [primary_summaries[label] for label in PRIMARY]
    primary_action = combined_actionability(
        primary, draws=PRIMARY_DRAWS, seed=SEED
    )

    parameter_ladder = []
    for arm in ARMS:
        for side in TILE_SIDES:
            for baseline in BASELINE_LADDER:
                for prominence in PROMINENCE_LADDER:
                    summaries = [
                        summarise_cache(
                            cache_paths[label],
                            side=side,
                            arm=arm,
                            baseline_percentile=baseline,
                            prominence=prominence,
                            draws=LADDER_DRAWS,
                        )
                        for label in PRIMARY
                    ]
                    action = combined_actionability(
                        summaries,
                        draws=LADDER_DRAWS,
                        seed=stable_seed(
                            f"ladder:{arm}:{side}:{baseline}:{prominence}"
                        ),
                    )
                    parameter_ladder.append(
                        {
                            "arm": arm,
                            "tile_side_plane_px": side,
                            "baseline_percentile": baseline,
                            "prominence": prominence,
                            "action": action,
                            "valid_tiles": {
                                summary["label"]: summary["n_tiles_valid"]
                                for summary in summaries
                            },
                        }
                    )

    radial_ladder = []
    for group in ("centre", "q1", "q2", "q3", "q4"):
        radial_ladder.append(
            combined_actionability(
                primary,
                draws=LADDER_DRAWS,
                seed=stable_seed(f"radial:{group}"),
                radius_group=group,
            )
        )

    step_ladder = []
    for label in STEP_LADDER:
        category = single_stack_category(
            primary_summaries[label],
            draws=LADDER_DRAWS,
            seed=stable_seed(f"step:{label}"),
        )
        category["label"] = label
        category["step_width"] = STACKS[label]["step_width"]
        if "delta_r_median_frames" in category:
            category["delta_r_times_step_setting"] = (
                category["delta_r_median_frames"]
                * STACKS[label]["step_width"]
            )
        step_ladder.append(category)

    linear_summaries = [
        summarise_cache(
            cache_paths[label],
            mode="linear",
            draws=LADDER_DRAWS,
        )
        for label in PRIMARY
    ]
    linear_dissent = combined_actionability(
        linear_summaries,
        draws=LADDER_DRAWS,
        seed=stable_seed("linear-dissent"),
    )

    primary_category = primary_action["category"]
    parameter_categories = sorted(
        {row["action"]["category"] for row in parameter_ladder}
    )
    radial_categories = sorted({row["category"] for row in radial_ladder})
    step_categories = sorted({row["category"] for row in step_ladder})
    all_ladder_categories = set(
        parameter_categories + radial_categories + step_categories
    )
    changed = any(category != primary_category for category in all_ladder_categories)
    audit_classification = "NOT ROBUST" if changed else primary_category

    after = {
        label: capture_inventory(spec["path"]) for label, spec in STACKS.items()
    }
    if before != after:
        raise RuntimeError("read-only capture inventory changed during measurement")

    result = {
        "schema": 1,
        "claim": (
            "C2 longitudinal/axial chromatic focus-axis diversity; "
            "not lateral chromatic magnification"
        ),
        "environment": environment_record(),
        "config": config_record(),
        "commission": {
            "path": str(commission_path),
            "sha256": file_sha256(commission_path),
            "summary": commission["summary"],
        },
        "capture_inventory_before": before,
        "capture_inventory_after_identical": before == after,
        "cache": {
            label: {
                "path": str(cache_paths[label]),
                "reused": cache_reused[label],
                "sha256": file_sha256(cache_paths[label]),
            }
            for label in STACKS
        },
        "primary_stack_summaries": primary_summaries,
        "primary_actionability": primary_action,
        "robustness": {
            "parameter_ladder": parameter_ladder,
            "radial_ladder": radial_ladder,
            "step_ladder": step_ladder,
            "linear_domain_dissent": linear_dissent,
            "primary_category": primary_category,
            "parameter_categories": parameter_categories,
            "radial_categories": radial_categories,
            "step_categories": step_categories,
            "any_category_changed": changed,
            "audit_classification": audit_classification,
        },
        "corpus_disposition": {
            "current_fact": 1413,
            "m107_registered_before_measurement": True,
            "build_chroma_independent_replication": True,
            "retraction_found": False,
            "verdict_if_trust_audit_stands": "ALREADY ANSWERED IN CORPUS",
        },
    }
    write_json(OUT / "measurement.json", result)

    print("\nPRIMARY")
    print(
        f"  A = {primary_action.get('A_min_abs_subject_median_frames')} "
        f"frames; 95% CI {primary_action.get('A_ci95_frames')}; "
        f"{primary_category}"
    )
    for label in PRIMARY:
        summary = primary_summaries[label]
        print(
            f"  {label}: dR={summary['summaries']['delta_r']['median']} "
            f"dB={summary['summaries']['delta_b']['median']} "
            f"null={summary['summaries']['delta_null']['median']} "
            f"tiles={summary['n_tiles_valid']}/{summary['n_tiles_total']}"
        )
    print(
        f"  ladder categories parameter={parameter_categories} "
        f"radial={radial_categories} step={step_categories}"
    )
    print(f"  audit classification: {audit_classification}")
    print(f"wrote {OUT / 'measurement.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
