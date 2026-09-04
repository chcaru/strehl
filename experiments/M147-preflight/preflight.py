"""M147 in-field magnification preflight.

The decision quantity is the ratio of the same grid's sensor-pixel period in
the converter-on reference frame and the converter-off TC0 frame.  Absolute
grid pitch, sensor pitch, and EXIF focal length are deliberately unused.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import rawpy
from scipy import ndimage


TOOL_VERSION = "1.0.0"

# There are intentionally no CLI overrides for these values.  The canonical
# serialization and SHA-256 are written into every result artifact.
FROZEN_PARAMETERS: dict[str, Any] = {
    "schema": "m147-preflight-parameters-v1",
    "decision": {
        "minimum_sampling_ratio": 2.0,
        "confidence_level": 0.95,
        "maximum_relative_interval_width": 0.015,
    },
    "raw": {
        "extensions": [".arw"],
        "maximum_low_rail_fraction": 0.005,
        "maximum_high_rail_fraction": 0.001,
        "minimum_robust_range_fraction": 0.01,
    },
    "estimator": {
        "green_plane_step_native_px": 2,
        "tile_size_green_px": 512,
        "tile_stride_green_px": 256,
        "fft_size": 1024,
        "minimum_period_green_px": 20.0,
        "maximum_period_green_px": 128.0,
        "minimum_tile_robust_range_dn": 50.0,
        "minimum_peak_snr_db": 12.0,
        "minimum_median_peak_snr_db": 20.0,
        "reciprocal_angle_degrees": [70.0, 90.0],
        "maximum_axis_period_ratio": 1.5,
        "period_cluster_relative_half_width": 0.018,
        "minimum_cluster_candidates_per_green": 12,
        "minimum_cluster_fraction": 0.25,
        "maximum_competing_cluster_fraction": 0.65,
        "minimum_spatial_blocks": 6,
        "spatial_block_size_green_px": 512,
        "maximum_period_mad_fraction": 0.01,
        "maximum_orientation_mad_degrees": 5.0,
        "maximum_green_disagreement_fraction": 0.003,
        "maximum_pair_anisotropy_fraction": 0.015,
        "maximum_relative_rotation_degrees": 15.0,
    },
    "uncertainty": {
        "method": "independent spatial-block percentile bootstrap plus phase envelope",
        "draws": 10000,
        "seed": 14720260904,
        "lower_quantile": 0.025,
        "upper_quantile": 0.975,
        "relative_systematic_allowance": 0.0025,
    },
    "operator_target_ratio": 2.0312,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


PARAMETERS_SHA256 = hashlib.sha256(
    canonical_json(FROZEN_PARAMETERS).encode("ascii")
).hexdigest()


class MeasurementRefusal(RuntimeError):
    def __init__(self, code: str, message: str, action: str):
        super().__init__(message)
        self.code = code
        self.message = message
        self.action = action


class UsageError(RuntimeError):
    pass


@dataclass
class DecodedRaw:
    path: Path
    file_sha256: str
    decoded_sha256: str
    visible_shape: tuple[int, int]
    raw_pattern: list[list[int]]
    color_desc: str
    black_levels: list[float]
    white_level: int
    pixel_aspect: float
    green_planes: tuple[np.ndarray, np.ndarray]
    low_rail_fraction: float
    high_rail_fraction: float
    robust_range_fraction: float

    def input_record(self) -> dict[str, Any]:
        return {
            "path": str(self.path.resolve()),
            "sha256": self.file_sha256,
            "size_bytes": self.path.stat().st_size,
            "decoded_visible_sha256": self.decoded_sha256,
            "visible_shape": list(self.visible_shape),
            "raw_pattern": self.raw_pattern,
            "color_desc": self.color_desc,
            "black_levels_dn": self.black_levels,
            "white_level_dn": self.white_level,
            "pixel_aspect": self.pixel_aspect,
            "low_rail_fraction": self.low_rail_fraction,
            "high_rail_fraction": self.high_rail_fraction,
            "robust_range_fraction": self.robust_range_fraction,
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_input_path(path: Path, role: str) -> Path:
    path = path.expanduser()
    if not path.is_file():
        raise UsageError(f"{role} input is not a file: {path}")
    if path.suffix.lower() not in FROZEN_PARAMETERS["raw"]["extensions"]:
        raise UsageError(f"{role} input must be a Sony .ARW file: {path}")
    return path.resolve()


def decode_arw(path: Path) -> DecodedRaw:
    file_hash = sha256_file(path)
    try:
        with rawpy.imread(str(path)) as raw:
            mosaic = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
            pattern = np.array(raw.raw_pattern, dtype=np.int16, copy=True)
            black = np.array(raw.black_level_per_channel, dtype=np.float64, copy=True)
            color_desc_bytes = bytes(raw.color_desc)
            white = int(raw.white_level)
            pixel_aspect = float(raw.sizes.pixel_aspect)
    except Exception as error:
        raise MeasurementRefusal(
            "RAW_DECODE_FAILED",
            f"rawpy could not decode {path.name}: {error}",
            "Check that this is an intact Sony ARW and retake the preflight frame.",
        ) from error

    if pattern.shape != (2, 2):
        raise MeasurementRefusal(
            "UNSUPPORTED_CFA",
            f"Expected a 2x2 Bayer CFA, found {pattern.shape}.",
            "Use an unmodified Sony ARW from the capture camera.",
        )
    green_indices = [
        index for index, value in enumerate(color_desc_bytes) if value == ord("G")
    ]
    green_positions = np.argwhere(np.isin(pattern, green_indices))
    if len(green_positions) != 2:
        raise MeasurementRefusal(
            "UNSUPPORTED_CFA",
            f"Expected two green CFA sites, found {len(green_positions)}.",
            "Use an unmodified Bayer Sony ARW from the capture camera.",
        )
    if not math.isclose(pixel_aspect, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise MeasurementRefusal(
            "NON_SQUARE_PIXELS",
            f"RAW decoder reports pixel aspect {pixel_aspect}, not 1.0.",
            "Use the original camera ARW rather than a converted or rescaled file.",
        )

    decoded_hash = hashlib.sha256(memoryview(np.ascontiguousarray(mosaic))).hexdigest()
    planes: list[np.ndarray] = []
    low_count = 0
    high_count = 0
    sample_count = 0
    robust_ranges = []
    for row, column in green_positions:
        channel = int(pattern[row, column])
        raw_plane = mosaic[row::2, column::2]
        plane = raw_plane.astype(np.float32) - np.float32(black[channel])
        planes.append(plane)
        low_count += int(np.count_nonzero(raw_plane <= black[channel]))
        high_count += int(np.count_nonzero(raw_plane >= white - 1))
        sample_count += raw_plane.size
        robust_ranges.append(float(np.percentile(plane, 95) - np.percentile(plane, 5)))

    usable_span = max(1.0, white - float(np.mean(black)))
    low_fraction = low_count / sample_count
    high_fraction = high_count / sample_count
    robust_fraction = min(robust_ranges) / usable_span
    raw_rules = FROZEN_PARAMETERS["raw"]
    if low_fraction > raw_rules["maximum_low_rail_fraction"]:
        raise MeasurementRefusal(
            "LOW_RAIL_CLIPPING",
            f"Low-rail fraction {low_fraction:.6f} exceeds "
            f"{raw_rules['maximum_low_rail_fraction']:.6f}.",
            "Increase illumination or exposure without clipping highlights, then retake.",
        )
    if high_fraction > raw_rules["maximum_high_rail_fraction"]:
        raise MeasurementRefusal(
            "HIGH_RAIL_CLIPPING",
            f"High-rail fraction {high_fraction:.6f} exceeds "
            f"{raw_rules['maximum_high_rail_fraction']:.6f}.",
            "Reduce illumination or exposure, then retake both preflight frames.",
        )
    if robust_fraction < raw_rules["minimum_robust_range_fraction"]:
        raise MeasurementRefusal(
            "INSUFFICIENT_CONTRAST",
            f"Robust RAW range {robust_fraction:.6f} of usable span is too small.",
            "Reframe on the grid, improve illumination, and focus before retaking.",
        )

    return DecodedRaw(
        path=path,
        file_sha256=file_hash,
        decoded_sha256=decoded_hash,
        visible_shape=tuple(int(value) for value in mosaic.shape),
        raw_pattern=pattern.tolist(),
        color_desc=color_desc_bytes.decode("ascii", errors="replace").rstrip("\x00"),
        black_levels=[float(value) for value in black],
        white_level=white,
        pixel_aspect=pixel_aspect,
        green_planes=(planes[0], planes[1]),
        low_rail_fraction=float(low_fraction),
        high_rail_fraction=float(high_fraction),
        robust_range_fraction=float(robust_fraction),
    )


@lru_cache(maxsize=1)
def _spectral_context() -> dict[str, np.ndarray]:
    estimator = FROZEN_PARAMETERS["estimator"]
    tile_size = int(estimator["tile_size_green_px"])
    fft_size = int(estimator["fft_size"])
    coordinate = np.linspace(-1.0, 1.0, tile_size, dtype=np.float32)
    window_1d = np.hanning(tile_size).astype(np.float32)
    window = window_1d[:, None] * window_1d[None, :]
    frequency = np.fft.fftshift(np.fft.fftfreq(fft_size))
    fy, fx = np.meshgrid(frequency, frequency, indexing="ij")
    radius = np.hypot(fx, fy)
    annulus = (
        (radius >= 1.0 / estimator["maximum_period_green_px"])
        & (radius <= 1.0 / estimator["minimum_period_green_px"])
    )
    positive = (fy > 0.0) | ((fy == 0.0) & (fx > 0.0))
    return {
        "coordinate": coordinate,
        "window": window,
        "frequency": frequency,
        "annulus": annulus,
        "search": annulus & positive,
    }


def _parabolic_peak(power: np.ndarray, row: int, column: int) -> tuple[float, float]:
    log_power = np.log(np.maximum(power, np.finfo(np.float64).tiny))

    def offset(a: float, b: float, c: float) -> float:
        denominator = a - 2.0 * b + c
        if denominator >= -1e-12:
            return 0.0
        return float(np.clip(0.5 * (a - c) / denominator, -0.5, 0.5))

    dy = offset(
        log_power[row - 1, column],
        log_power[row, column],
        log_power[row + 1, column],
    )
    dx = offset(
        log_power[row, column - 1],
        log_power[row, column],
        log_power[row, column + 1],
    )
    return row + dy, column + dx


def _orientation_mod_90(vector: np.ndarray) -> float:
    return math.degrees(math.atan2(float(vector[1]), float(vector[0]))) % 90.0


def _angle_distance_mod_90(first: float, second: float) -> float:
    delta = abs(first - second) % 90.0
    return min(delta, 90.0 - delta)


def _tile_candidate(tile: np.ndarray) -> dict[str, Any] | None:
    estimator = FROZEN_PARAMETERS["estimator"]
    tile_size = int(estimator["tile_size_green_px"])
    fft_size = int(estimator["fft_size"])
    robust_range = float(np.percentile(tile, 95) - np.percentile(tile, 5))
    if robust_range < estimator["minimum_tile_robust_range_dn"]:
        return None

    context = _spectral_context()
    coordinate = context["coordinate"]
    centered = tile.astype(np.float32, copy=False) - np.float32(np.mean(tile))
    denominator = float(np.sum(coordinate * coordinate) * tile_size)
    slope_x = float(np.sum(centered * coordinate[None, :]) / denominator)
    slope_y = float(np.sum(centered * coordinate[:, None]) / denominator)
    residual = centered - slope_x * coordinate[None, :] - slope_y * coordinate[:, None]
    spectrum = np.fft.fftshift(
        np.fft.fft2(residual * context["window"], s=(fft_size, fft_size))
    )
    power = np.square(np.abs(spectrum))
    local = power == ndimage.maximum_filter(power, size=5, mode="constant")
    coordinates = np.argwhere(context["search"] & local)
    if len(coordinates) < 2:
        return None
    coordinates = sorted(
        coordinates,
        key=lambda rc: float(power[int(rc[0]), int(rc[1])]),
        reverse=True,
    )[:30]
    background = max(float(np.median(power[context["annulus"]])), 1e-30)

    frequency = context["frequency"]
    best: tuple[float, np.ndarray, np.ndarray, float] | None = None
    maximum_axis_ratio = float(estimator["maximum_axis_period_ratio"])
    minimum_angle, maximum_angle = estimator["reciprocal_angle_degrees"]
    for index, first in enumerate(coordinates):
        for second in coordinates[index + 1 :]:
            vector_1 = np.array(
                [frequency[int(first[1])], frequency[int(first[0])]],
                dtype=np.float64,
            )
            vector_2 = np.array(
                [frequency[int(second[1])], frequency[int(second[0])]],
                dtype=np.float64,
            )
            norm_1 = float(np.linalg.norm(vector_1))
            norm_2 = float(np.linalg.norm(vector_2))
            cosine = abs(float(vector_1 @ vector_2)) / (norm_1 * norm_2)
            angle = math.degrees(math.acos(float(np.clip(cosine, 0.0, 1.0))))
            axis_ratio = max(norm_1, norm_2) / min(norm_1, norm_2)
            if not (
                minimum_angle <= angle <= maximum_angle
                and axis_ratio <= maximum_axis_ratio
            ):
                continue
            strength = math.sqrt(
                float(power[int(first[0]), int(first[1])])
                * float(power[int(second[0]), int(second[1])])
            )
            if best is None or strength > best[0]:
                best = (strength, first, second, angle)
    if best is None:
        return None

    strength, first, second, _ = best
    row_1, column_1 = _parabolic_peak(
        power, int(first[0]), int(first[1])
    )
    row_2, column_2 = _parabolic_peak(
        power, int(second[0]), int(second[1])
    )
    vector_1 = np.array(
        [(column_1 - fft_size / 2) / fft_size, (row_1 - fft_size / 2) / fft_size]
    )
    vector_2 = np.array(
        [(column_2 - fft_size / 2) / fft_size, (row_2 - fft_size / 2) / fft_size]
    )
    norm_1 = float(np.linalg.norm(vector_1))
    norm_2 = float(np.linalg.norm(vector_2))
    determinant = abs(float(np.linalg.det(np.stack([vector_1, vector_2]))))
    if determinant <= 0.0:
        return None
    period = 1.0 / math.sqrt(determinant)
    if not (
        estimator["minimum_period_green_px"]
        <= period
        <= estimator["maximum_period_green_px"]
    ):
        return None
    cosine = abs(float(vector_1 @ vector_2)) / (norm_1 * norm_2)
    angle = math.degrees(math.acos(float(np.clip(cosine, 0.0, 1.0))))
    orientations = [_orientation_mod_90(vector_1), _orientation_mod_90(vector_2)]
    if _angle_distance_mod_90(orientations[0], orientations[1]) <= 10.0:
        orientation = float(np.mean(orientations))
    else:
        orientation = orientations[0]
    return {
        "period_green_px": float(period),
        "axis_periods_green_px": sorted([1.0 / norm_1, 1.0 / norm_2]),
        "reciprocal_angle_degrees": float(angle),
        "orientation_degrees_mod_90": float(orientation),
        "peak_snr_db": float(10.0 * math.log10(max(strength / background, 1e-30))),
    }


def _find_cluster(
    candidates: list[dict[str, Any]],
    image_shape: tuple[int, int],
    phase_name: str,
) -> dict[str, Any]:
    estimator = FROZEN_PARAMETERS["estimator"]
    candidates = [
        candidate
        for candidate in candidates
        if candidate["peak_snr_db"] >= estimator["minimum_peak_snr_db"]
    ]
    minimum_count = int(estimator["minimum_cluster_candidates_per_green"])
    if len(candidates) < minimum_count:
        raise MeasurementRefusal(
            "NO_COHERENT_GRID",
            f"{phase_name}: only {len(candidates)} spectral lattice candidates "
            f"cleared the evidence floor; {minimum_count} are required.",
            "Refocus and reframe so the regular grid occupies a large part of the frame.",
        )

    tolerance = math.log1p(float(estimator["period_cluster_relative_half_width"]))

    def cluster_around(center: float, pool: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            candidate
            for candidate in pool
            if abs(math.log(candidate["period_green_px"] / center)) <= tolerance
        ]

    best: list[dict[str, Any]] = []
    for candidate in candidates:
        members = cluster_around(candidate["period_green_px"], candidates)
        if (
            len(members),
            float(np.median([item["peak_snr_db"] for item in members])),
        ) > (
            len(best),
            float(np.median([item["peak_snr_db"] for item in best]))
            if best
            else -math.inf,
        ):
            best = members
    center = float(np.median([item["period_green_px"] for item in best]))
    best = cluster_around(center, candidates)

    if len(best) < minimum_count:
        raise MeasurementRefusal(
            "NO_COHERENT_GRID",
            f"{phase_name}: the largest period cluster has {len(best)} candidates; "
            f"{minimum_count} are required.",
            "Refocus and reframe so the same regular grid fills more of the frame.",
        )
    cluster_fraction = len(best) / len(candidates)
    if cluster_fraction < estimator["minimum_cluster_fraction"]:
        raise MeasurementRefusal(
            "AMBIGUOUS_LATTICE",
            f"{phase_name}: the winning grid accounts for only "
            f"{100.0 * cluster_fraction:.1f}% of lattice candidates.",
            "Reframe to exclude other periodic charts and make the intended grid dominant.",
        )

    best_ids = {id(item) for item in best}
    remainder = [item for item in candidates if id(item) not in best_ids]
    competing: list[dict[str, Any]] = []
    for candidate in remainder:
        members = cluster_around(candidate["period_green_px"], remainder)
        if len(members) > len(competing):
            competing = members
    if (
        competing
        and len(competing) / len(best)
        > estimator["maximum_competing_cluster_fraction"]
        and abs(
            math.log(
                np.median([item["period_green_px"] for item in competing]) / center
            )
        )
        > 2.0 * tolerance
    ):
        raise MeasurementRefusal(
            "AMBIGUOUS_LATTICE",
            f"{phase_name}: a second period family is too competitive "
            f"({len(competing)} versus {len(best)} tiles).",
            "Reframe so only one regular grid pitch dominates the image.",
        )

    block_size = int(estimator["spatial_block_size_green_px"])
    grouped: dict[str, list[float]] = {}
    for candidate in best:
        block_row = int(candidate["center_y_green_px"] // block_size)
        block_column = int(candidate["center_x_green_px"] // block_size)
        key = f"{block_row},{block_column}"
        grouped.setdefault(key, []).append(candidate["period_green_px"])
    block_periods = {
        key: float(np.median(values)) for key, values in sorted(grouped.items())
    }
    if len(block_periods) < estimator["minimum_spatial_blocks"]:
        raise MeasurementRefusal(
            "GRID_TOO_SMALL",
            f"{phase_name}: coherent grid occupies {len(block_periods)} spatial "
            f"blocks; {estimator['minimum_spatial_blocks']} are required.",
            "Move or reframe so the grid occupies more of the sensor.",
        )

    periods = np.asarray(list(block_periods.values()), dtype=np.float64)
    period = float(np.median(periods))
    mad_fraction = float(np.median(np.abs(periods - period)) / period)
    if mad_fraction > estimator["maximum_period_mad_fraction"]:
        raise MeasurementRefusal(
            "GRID_SCALE_NONUNIFORM",
            f"{phase_name}: spatial period MAD is {100.0 * mad_fraction:.3f}%, "
            f"above {100.0 * estimator['maximum_period_mad_fraction']:.3f}%.",
            "Flatten the target/camera alignment and reframe on a coplanar grid.",
        )

    orientations = np.asarray(
        [item["orientation_degrees_mod_90"] for item in best], dtype=np.float64
    )
    orientation_candidates = np.linspace(0.0, 90.0, 901, endpoint=False)
    losses = np.asarray(
        [
            np.median(
                [
                    _angle_distance_mod_90(float(value), float(candidate))
                    for value in orientations
                ]
            )
            for candidate in orientation_candidates
        ]
    )
    orientation = float(orientation_candidates[int(np.argmin(losses))])
    orientation_mad = float(np.min(losses))
    if orientation_mad > estimator["maximum_orientation_mad_degrees"]:
        raise MeasurementRefusal(
            "GRID_ORIENTATION_NONUNIFORM",
            f"{phase_name}: orientation MAD is {orientation_mad:.3f} degrees.",
            "Flatten the target and ensure one coplanar grid dominates the frame.",
        )

    median_snr = float(np.median([item["peak_snr_db"] for item in best]))
    if median_snr < estimator["minimum_median_peak_snr_db"]:
        raise MeasurementRefusal(
            "GRID_SIGNAL_TOO_WEAK",
            f"{phase_name}: median lattice peak SNR is {median_snr:.2f} dB, "
            f"below {estimator['minimum_median_peak_snr_db']:.2f} dB.",
            "Improve focus/illumination and make the grid larger in the frame.",
        )

    axis_periods = np.median(
        np.asarray([item["axis_periods_green_px"] for item in best]), axis=0
    )
    return {
        "period_green_px": period,
        "period_sensor_px": 2.0 * period,
        "axis_periods_green_px": [float(value) for value in axis_periods],
        "axis_periods_sensor_px": [2.0 * float(value) for value in axis_periods],
        "block_periods_green_px": block_periods,
        "candidate_count": len(candidates),
        "cluster_candidate_count": len(best),
        "cluster_fraction": float(cluster_fraction),
        "competing_cluster_count": len(competing),
        "spatial_block_count": len(block_periods),
        "period_mad_fraction": mad_fraction,
        "median_peak_snr_db": median_snr,
        "median_reciprocal_angle_degrees": float(
            np.median([item["reciprocal_angle_degrees"] for item in best])
        ),
        "orientation_degrees_mod_90": orientation,
        "orientation_mad_degrees": orientation_mad,
        "image_shape_green_px": list(image_shape),
    }


def estimate_green_plane(plane: np.ndarray, phase_name: str) -> dict[str, Any]:
    estimator = FROZEN_PARAMETERS["estimator"]
    tile_size = int(estimator["tile_size_green_px"])
    stride = int(estimator["tile_stride_green_px"])
    if plane.ndim != 2 or min(plane.shape) < tile_size:
        raise MeasurementRefusal(
            "FRAME_TOO_SMALL",
            f"{phase_name}: green plane shape {plane.shape} is smaller than one tile.",
            "Use the original full-resolution ARW.",
        )
    candidates = []
    for top in range(0, plane.shape[0] - tile_size + 1, stride):
        for left in range(0, plane.shape[1] - tile_size + 1, stride):
            candidate = _tile_candidate(plane[top : top + tile_size, left : left + tile_size])
            if candidate is None:
                continue
            candidate["center_y_green_px"] = top + tile_size / 2.0
            candidate["center_x_green_px"] = left + tile_size / 2.0
            candidates.append(candidate)
    return _find_cluster(candidates, tuple(int(value) for value in plane.shape), phase_name)


def estimate_decoded(decoded: DecodedRaw, role: str) -> dict[str, Any]:
    phases = [
        estimate_green_plane(plane, f"{role}:{name}")
        for plane, name in zip(decoded.green_planes, ("G1", "G2"), strict=True)
    ]
    period_1 = phases[0]["period_green_px"]
    period_2 = phases[1]["period_green_px"]
    disagreement = abs(period_1 - period_2) / math.sqrt(period_1 * period_2)
    limit = FROZEN_PARAMETERS["estimator"]["maximum_green_disagreement_fraction"]
    if disagreement > limit:
        raise MeasurementRefusal(
            "GREEN_PHASE_DISAGREEMENT",
            f"{role}: green phases disagree by {100.0 * disagreement:.3f}%, "
            f"above {100.0 * limit:.3f}%.",
            "Retake after improving focus and checking for motion or patterned lighting.",
        )

    common_blocks = sorted(
        set(phases[0]["block_periods_green_px"])
        & set(phases[1]["block_periods_green_px"])
    )
    minimum_blocks = FROZEN_PARAMETERS["estimator"]["minimum_spatial_blocks"]
    if len(common_blocks) < minimum_blocks:
        raise MeasurementRefusal(
            "GREEN_PHASE_COVERAGE",
            f"{role}: green phases share only {len(common_blocks)} coherent blocks; "
            f"{minimum_blocks} are required.",
            "Reframe so a high-contrast grid occupies more of the frame.",
        )
    combined_blocks = {
        key: math.sqrt(
            phases[0]["block_periods_green_px"][key]
            * phases[1]["block_periods_green_px"][key]
        )
        for key in common_blocks
    }
    combined_values = np.asarray(list(combined_blocks.values()), dtype=np.float64)
    period = float(np.median(combined_values))
    axis_periods = np.sqrt(
        np.asarray(phases[0]["axis_periods_green_px"])
        * np.asarray(phases[1]["axis_periods_green_px"])
    )
    orientation = phases[0]["orientation_degrees_mod_90"]
    other_orientation = phases[1]["orientation_degrees_mod_90"]
    if _angle_distance_mod_90(orientation, other_orientation) > 5.0:
        orientation = float(
            (orientation + other_orientation) / 2.0
        )
    return {
        "status": "OK",
        "period_green_px": period,
        "period_sensor_px": 2.0 * period,
        "axis_periods_green_px": [float(value) for value in axis_periods],
        "axis_periods_sensor_px": [2.0 * float(value) for value in axis_periods],
        "green_phase_disagreement_fraction": float(disagreement),
        "orientation_degrees_mod_90": float(orientation),
        "block_periods_green_px": combined_blocks,
        "spatial_block_count": len(combined_blocks),
        "green_phases": phases,
    }


def estimate_planes(
    planes: tuple[np.ndarray, np.ndarray],
    role: str,
) -> dict[str, Any]:
    """Commissioning entry point for already-decoded or planted green planes."""

    placeholder = DecodedRaw(
        path=Path("<in-memory>"),
        file_sha256="",
        decoded_sha256="",
        visible_shape=(planes[0].shape[0] * 2, planes[0].shape[1] * 2),
        raw_pattern=[[0, 1], [3, 2]],
        color_desc="RGBG",
        black_levels=[0.0, 0.0, 0.0, 0.0],
        white_level=65535,
        pixel_aspect=1.0,
        green_planes=planes,
        low_rail_fraction=0.0,
        high_rail_fraction=0.0,
        robust_range_fraction=1.0,
    )
    return estimate_decoded(placeholder, role)


def _bootstrap_ratio(
    reference: dict[str, Any], scored: dict[str, Any]
) -> dict[str, Any]:
    uncertainty = FROZEN_PARAMETERS["uncertainty"]
    reference_blocks = np.asarray(
        list(reference["block_periods_green_px"].values()), dtype=np.float64
    )
    scored_blocks = np.asarray(
        list(scored["block_periods_green_px"].values()), dtype=np.float64
    )
    draws = int(uncertainty["draws"])
    rng = np.random.default_rng(int(uncertainty["seed"]))
    reference_draws = np.median(
        reference_blocks[
            rng.integers(0, len(reference_blocks), size=(draws, len(reference_blocks)))
        ],
        axis=1,
    )
    scored_draws = np.median(
        scored_blocks[
            rng.integers(0, len(scored_blocks), size=(draws, len(scored_blocks)))
        ],
        axis=1,
    )
    ratios = reference_draws / scored_draws
    q_low = float(
        np.quantile(
            ratios,
            uncertainty["lower_quantile"],
            method="linear",
        )
    )
    q_high = float(
        np.quantile(
            ratios,
            uncertainty["upper_quantile"],
            method="linear",
        )
    )
    phase_ratios = [
        reference_phase["period_green_px"] / scored_phase["period_green_px"]
        for reference_phase in reference["green_phases"]
        for scored_phase in scored["green_phases"]
    ]
    systematic = float(uncertainty["relative_systematic_allowance"])
    lower = min(q_low, min(phase_ratios)) * (1.0 - systematic)
    upper = max(q_high, max(phase_ratios)) * (1.0 + systematic)
    point = reference["period_green_px"] / scored["period_green_px"]
    return {
        "method": uncertainty["method"],
        "confidence_level": FROZEN_PARAMETERS["decision"]["confidence_level"],
        "draws": draws,
        "seed": uncertainty["seed"],
        "bootstrap_percentile_interval": [q_low, q_high],
        "green_phase_ratio_envelope": [min(phase_ratios), max(phase_ratios)],
        "relative_systematic_allowance": systematic,
        "lower": float(lower),
        "upper": float(upper),
        "point": float(point),
        "relative_width": float((upper - lower) / point),
    }


def evaluate_measurements(
    reference: dict[str, Any], scored: dict[str, Any]
) -> dict[str, Any]:
    estimator = FROZEN_PARAMETERS["estimator"]
    reference_axes = np.asarray(reference["axis_periods_green_px"], dtype=np.float64)
    scored_axes = np.asarray(scored["axis_periods_green_px"], dtype=np.float64)
    axis_ratios = np.sort(reference_axes / scored_axes)
    anisotropy = float(axis_ratios[-1] / axis_ratios[0] - 1.0)
    if anisotropy > estimator["maximum_pair_anisotropy_fraction"]:
        raise MeasurementRefusal(
            "ANISOTROPIC_SCALE_CHANGE",
            f"Grid-axis ratios differ by {100.0 * anisotropy:.3f}%, above "
            f"{100.0 * estimator['maximum_pair_anisotropy_fraction']:.3f}%.",
            "Restore the same camera yaw/target plane and retake both frames.",
        )
    rotation = _angle_distance_mod_90(
        reference["orientation_degrees_mod_90"],
        scored["orientation_degrees_mod_90"],
    )
    if rotation > estimator["maximum_relative_rotation_degrees"]:
        raise MeasurementRefusal(
            "EXCESSIVE_RELATIVE_ROTATION",
            f"Relative grid rotation is {rotation:.3f} degrees, above "
            f"{estimator['maximum_relative_rotation_degrees']:.3f} degrees.",
            "Restore camera roll and yaw, then retake both frames.",
        )

    interval = _bootstrap_ratio(reference, scored)
    width_limit = FROZEN_PARAMETERS["decision"]["maximum_relative_interval_width"]
    if interval["relative_width"] > width_limit:
        raise MeasurementRefusal(
            "INSUFFICIENT_PRECISION",
            f"The {100.0 * FROZEN_PARAMETERS['decision']['confidence_level']:.1f}% "
            f"interval is {100.0 * interval['relative_width']:.3f}% wide, above "
            f"the frozen {100.0 * width_limit:.3f}% limit.",
            "Improve focus, make the grid fill more of both frames, and retake.",
        )

    threshold = FROZEN_PARAMETERS["decision"]["minimum_sampling_ratio"]
    passed = interval["lower"] >= threshold
    if passed:
        action = (
            "PASS: the interval lower bound is at least 2.0. Preserve the rig "
            "settings and proceed with the capture protocol."
        )
    else:
        reduction_for_gate = max(0.0, 1.0 - interval["lower"] / threshold)
        reduction_for_target = max(
            0.0,
            1.0
            - interval["lower"] / FROZEN_PARAMETERS["operator_target_ratio"],
        )
        if interval["point"] > threshold:
            prefix = (
                "FAIL: the point estimate is above 2.0, but its lower uncertainty "
                "bound is below 2.0."
            )
        elif interval["point"] < 0.75:
            prefix = (
                "FAIL: the ratio is far below 1.0; the reference and TC0 inputs "
                "may be reversed."
            )
        else:
            prefix = "FAIL: the sampling ratio is not safely at or above 2.0."
        action = (
            f"{prefix} Reduce TC0 magnification by at least about "
            f"{100.0 * reduction_for_gate:.2f}% (about "
            f"{100.0 * reduction_for_target:.2f}% to restore the registered "
            "2.0312 target), or verify that the converter is seated and the "
            "reference is at maximum reproduction; then retake both preflight frames."
        )
    return {
        "sampling_ratio": interval["point"],
        "axis_sampling_ratios": [float(value) for value in axis_ratios],
        "axis_anisotropy_fraction": anisotropy,
        "relative_rotation_degrees": float(rotation),
        "interval": interval,
        "threshold": threshold,
        "verdict": "PASS" if passed else "FAIL",
        "reason_code": "LOWER_BOUND_AT_LEAST_2" if passed else "LOWER_BOUND_BELOW_2",
        "action": action,
    }


def _tool_record() -> dict[str, Any]:
    source = Path(__file__).resolve()
    return {
        "name": "M147 in-field magnification preflight",
        "version": TOOL_VERSION,
        "source_path": str(source),
        "source_sha256": sha256_file(source),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": __import__("scipy").__version__,
        "rawpy": rawpy.__version__,
    }


def run_preflight(reference_path: Path, scored_path: Path) -> tuple[dict[str, Any], int]:
    started = time.perf_counter()
    artifact: dict[str, Any] = {
        "schema": "m147-preflight-result-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "tool": _tool_record(),
        "parameters": FROZEN_PARAMETERS,
        "parameters_sha256": PARAMETERS_SHA256,
        "roles": {
            "reference": "converter-on maximum-reproduction grid frame",
            "scored": "converter-off TC0 grid frame",
        },
    }
    reference_path = _validate_input_path(reference_path, "reference")
    scored_path = _validate_input_path(scored_path, "TC0")
    if reference_path == scored_path:
        raise UsageError("reference and TC0 paths must be different files")

    decoded_reference: DecodedRaw | None = None
    decoded_scored: DecodedRaw | None = None
    try:
        decoded_reference = decode_arw(reference_path)
        decoded_scored = decode_arw(scored_path)
        artifact["inputs"] = {
            "reference": decoded_reference.input_record(),
            "scored": decoded_scored.input_record(),
        }
        if decoded_reference.file_sha256 == decoded_scored.file_sha256:
            raise MeasurementRefusal(
                "IDENTICAL_INPUT_BYTES",
                "Reference and TC0 files have identical SHA-256 hashes.",
                "Capture and supply one frame from each optical state.",
            )
        compatibility_fields = (
            ("visible_shape", decoded_reference.visible_shape, decoded_scored.visible_shape),
            ("raw_pattern", decoded_reference.raw_pattern, decoded_scored.raw_pattern),
            ("color_desc", decoded_reference.color_desc, decoded_scored.color_desc),
            ("white_level", decoded_reference.white_level, decoded_scored.white_level),
        )
        mismatches = [
            name for name, first, second in compatibility_fields if first != second
        ]
        if mismatches:
            raise MeasurementRefusal(
                "RAW_GEOMETRY_MISMATCH",
                f"Reference and TC0 RAW metadata differ in: {', '.join(mismatches)}.",
                "Use original ARWs from the same camera and unchanged RAW format.",
            )

        reference_measurement = estimate_decoded(decoded_reference, "reference")
        scored_measurement = estimate_decoded(decoded_scored, "TC0")
        artifact["measurements"] = {
            "reference": reference_measurement,
            "scored": scored_measurement,
        }
        decision = evaluate_measurements(reference_measurement, scored_measurement)
        artifact["decision"] = decision
        artifact["status"] = "OK"
        exit_code = 0 if decision["verdict"] == "PASS" else 2
    except MeasurementRefusal as refusal:
        if "inputs" not in artifact:
            inputs: dict[str, Any] = {}
            if decoded_reference is not None:
                inputs["reference"] = decoded_reference.input_record()
            if decoded_scored is not None:
                inputs["scored"] = decoded_scored.input_record()
            artifact["inputs"] = inputs
        artifact["status"] = "REFUSED"
        artifact["decision"] = {
            "verdict": "FAIL",
            "reason_code": refusal.code,
            "sampling_ratio": None,
            "interval": None,
            "action": f"FAIL / REFUSAL: {refusal.message} {refusal.action}",
        }
        exit_code = 2
    artifact["elapsed_seconds"] = float(time.perf_counter() - started)
    return artifact, exit_code


def _print_result(artifact: dict[str, Any], output_path: Path) -> None:
    decision = artifact["decision"]
    print("M147 MAGNIFICATION PREFLIGHT")
    measurements = artifact.get("measurements")
    if measurements:
        print(
            "Reference period: "
            f"{measurements['reference']['period_sensor_px']:.4f} sensor px"
        )
        print(
            "TC0 period:      "
            f"{measurements['scored']['period_sensor_px']:.4f} sensor px"
        )
    if decision.get("sampling_ratio") is not None:
        interval = decision["interval"]
        print(f"Sampling ratio:  {decision['sampling_ratio']:.6f}")
        print(
            f"Conservative 95% interval: [{interval['lower']:.6f}, "
            f"{interval['upper']:.6f}]"
        )
    print(f"Verdict: {decision['verdict']}")
    print(decision["action"])
    print(f"Artifact: {output_path.resolve()}")
    print(f"Elapsed: {artifact['elapsed_seconds']:.2f} s")


class Exit64Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        raise SystemExit(64)


def main() -> int:
    parser = Exit64Parser(
        description=(
            "Gate a capture session using the converter-on/reference to "
            "converter-off/TC0 grid-period ratio."
        )
    )
    parser.add_argument("--reference-arw", required=True, type=Path)
    parser.add_argument("--tc0-arw", required=True, type=Path)
    parser.add_argument("--output-json", required=True, type=Path)
    args = parser.parse_args()

    try:
        artifact, exit_code = run_preflight(args.reference_arw, args.tc0_arw)
    except UsageError as error:
        print(f"INPUT ERROR: {error}", file=sys.stderr)
        return 64
    except Exception as error:
        print(f"INTERNAL ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        return 70

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    _print_result(artifact, args.output_json)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
