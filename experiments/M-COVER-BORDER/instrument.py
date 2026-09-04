"""M-COVER-BORDER commissioned geometry, pyramid, and TIFF profiler."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


KERNEL = np.asarray([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float64) / 16.0
EXPECTED_HASHES = {
    "crop_b2": "02C1470ED0750248EFB5D321F05205CF1F1BD502931D2E50C0B65C46FFC2EC34",
    "crop_b7": "B2489C692AA924AEF230B21388407B902845219851C54FCA892E2DB362A0A83D",
    "scale_b2": "23EBAA7DE115D1294DC7A2220EF371F54E4B6CCB5B3BE7495B31737875C12E47",
    "scale_b7": "F9101E47F21726125EB0D46A12B0415DC439EDBC30FA3DD2CA47AACCAAD4B684",
    "sidecar": "C29CAB9C6F944F4D03C4402998E54AAD4D4221CC450AC4BEF42A453DE848434D",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def border_distance(height: int, width: int) -> np.ndarray:
    ys = np.minimum(np.arange(height), np.arange(height)[::-1])
    xs = np.minimum(np.arange(width), np.arange(width)[::-1])
    return np.minimum(ys[:, None], xs[None, :]).astype(np.int32, copy=False)


def per_distance(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if image.ndim != 2:
        raise ValueError(f"expected one plane, got {image.shape}")
    distance = border_distance(*image.shape)
    counts = np.bincount(distance.ravel())
    sums = np.bincount(
        distance.ravel(),
        weights=image.astype(np.float64, copy=False).ravel(),
        minlength=counts.size,
    )
    return sums, counts


def annular_effect(
    candidate_sums: np.ndarray,
    reference_sums: np.ndarray,
    counts: np.ndarray,
    *,
    threshold: float,
    deep_start: int,
    bin_width: int,
) -> dict[str, Any]:
    n = min(candidate_sums.size, reference_sums.size, counts.size)
    candidate_sums = candidate_sums[:n]
    reference_sums = reference_sums[:n]
    counts = counts[:n]
    if deep_start >= n or counts[deep_start:].sum() == 0:
        raise ValueError(f"no samples at deep-start {deep_start}; max distance is {n - 1}")
    deep_ratio = float(
        candidate_sums[deep_start:].sum(dtype=np.float64)
        / reference_sums[deep_start:].sum(dtype=np.float64)
    )
    rows: list[dict[str, Any]] = []
    annular_stop = min(deep_start, n)
    edges = [(0, min(8, annular_stop))]
    for lo in range(8, annular_stop, bin_width):
        edges.append((lo, min(lo + bin_width, annular_stop)))
    for lo, hi in edges:
        if hi <= lo:
            continue
        count = int(counts[lo:hi].sum())
        if count == 0:
            continue
        cmean = float(candidate_sums[lo:hi].sum(dtype=np.float64) / count)
        rmean = float(reference_sums[lo:hi].sum(dtype=np.float64) / count)
        effect = cmean / rmean / deep_ratio - 1.0
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "samples": count,
                "candidate_mean": cmean,
                "reference_mean": rmean,
                "normalised_effect": effect,
            }
        )
    deep_count = int(counts[deep_start:].sum())
    deep_candidate_mean = float(candidate_sums[deep_start:].sum(dtype=np.float64) / deep_count)
    deep_reference_mean = float(reference_sums[deep_start:].sum(dtype=np.float64) / deep_count)
    rows.append(
        {
            "lo": deep_start,
            "hi": n,
            "samples": deep_count,
            "candidate_mean": deep_candidate_mean,
            "reference_mean": deep_reference_mean,
            "normalised_effect": deep_candidate_mean / deep_reference_mean / deep_ratio - 1.0,
        }
    )
    safe = None
    for row_index, row in enumerate(rows):
        candidate = int(row["lo"])
        if candidate < 8:
            continue
        if all(abs(float(tail["normalised_effect"])) <= threshold for tail in rows[row_index:]):
            safe = candidate
            break
    return {"deep_ratio": deep_ratio, "safe_inset_px": safe, "rows": rows}


def detector_profile(
    candidate: np.ndarray,
    reference: np.ndarray,
    *,
    threshold: float = 0.001,
    deep_start: int = 256,
    bin_width: int = 8,
) -> dict[str, Any]:
    if candidate.shape != reference.shape:
        raise ValueError(f"shape mismatch: {candidate.shape} != {reference.shape}")
    candidate_sums, counts = per_distance(candidate)
    reference_sums, reference_counts = per_distance(reference)
    if not np.array_equal(counts, reference_counts):
        raise AssertionError("same-shaped images produced different distance counts")
    return annular_effect(
        candidate_sums,
        reference_sums,
        counts,
        threshold=threshold,
        deep_start=deep_start,
        bin_width=bin_width,
    )


def profile_peak(profile: dict[str, Any], stop: int | None = None) -> float:
    rows = profile["rows"]
    if stop is not None:
        rows = [row for row in rows if int(row["lo"]) < stop]
    return max((abs(float(row["normalised_effect"])) for row in rows), default=0.0)


def commission_detector() -> dict[str, Any]:
    height = width = 1024
    yy, xx = np.mgrid[:height, :width]
    base = 8000.0 + 0.25 * xx + 0.125 * yy
    distance = border_distance(height, width)

    null = detector_profile(base.copy(), base)

    defect_image = base.copy()
    defect_image[distance < 64] *= 1.02
    defect = detector_profile(defect_image, base)

    improved_image = base.copy()
    improved_image[distance < 64] *= 1.0005
    improved = detector_profile(improved_image, base)

    restored = detector_profile(defect_image.copy(), base)
    defect_peak = profile_peak(defect, 64)
    improvement_peak = profile_peak(improved, 64)
    checks = {
        "null_peak": profile_peak(null) <= 1e-12,
        "null_safe": null["safe_inset_px"] == 8,
        "defect_peak": abs(defect_peak - 0.02) <= 1e-6,
        "defect_safe": defect["safe_inset_px"] == 64,
        "improvement_peak": abs(improvement_peak - 0.0005) <= 1e-6,
        "improvement_safe": improved["safe_inset_px"] == 8,
        "improvement_reduction": improvement_peak <= 0.05 * defect_peak,
        "restoration_peak": abs(profile_peak(restored, 64) - defect_peak) <= 1e-12,
        "restoration_safe": restored["safe_inset_px"] == defect["safe_inset_px"],
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "readings": {
            "null_peak": profile_peak(null),
            "null_safe_inset_px": null["safe_inset_px"],
            "defect_peak": defect_peak,
            "defect_safe_inset_px": defect["safe_inset_px"],
            "improvement_peak": improvement_peak,
            "improvement_safe_inset_px": improved["safe_inset_px"],
            "improvement_fraction_of_defect": improvement_peak / defect_peak,
            "restored_peak": profile_peak(restored, 64),
            "restored_safe_inset_px": restored["safe_inset_px"],
        },
    }


def reduce_1d(source: np.ndarray) -> np.ndarray:
    n = source.size
    centers = 2 * np.arange((n + 1) // 2)
    taps = np.clip(centers[:, None] + np.arange(-2, 3)[None, :], 0, n - 1)
    return np.sum(source[taps] * KERNEL[None, :], axis=1)


def expand_1d(source: np.ndarray, output_size: int) -> np.ndarray:
    expected = (output_size + 1) // 2
    if source.size != expected:
        raise ValueError(f"cannot expand {source.size} values to {output_size}")
    x = np.arange(output_size)
    center = x // 2
    left = np.clip(center - 1, 0, source.size - 1)
    right = np.clip(center + 1, 0, source.size - 1)
    output = np.empty(output_size, dtype=np.float64)
    even = x % 2 == 0
    output[even] = (
        0.125 * source[left[even]]
        + 0.75 * source[center[even]]
        + 0.125 * source[right[even]]
    )
    output[~even] = 0.5 * (source[center[~even]] + source[right[~even]])
    return output


def build_pyramid(signal: np.ndarray, bands: int) -> list[np.ndarray]:
    gaussians = [signal.astype(np.float64, copy=True)]
    for _ in range(bands):
        gaussians.append(reduce_1d(gaussians[-1]))
    levels = [
        gaussians[k] - expand_1d(gaussians[k + 1], gaussians[k].size)
        for k in range(bands)
    ]
    levels.append(gaussians[-1])
    return levels


def collapse_pyramid(levels: list[np.ndarray]) -> np.ndarray:
    accumulator = levels[-1].copy()
    for level in reversed(levels[:-1]):
        accumulator = expand_1d(accumulator, level.size) + level
    return accumulator


def threshold_reach(error: np.ndarray, threshold: float) -> int:
    hits = np.flatnonzero(np.abs(error) > threshold)
    return int(hits[-1] + 1) if hits.size else 0


def fit_log2_reach(bands: list[int], reaches: list[int]) -> dict[str, float]:
    if any(reach <= 0 for reach in reaches):
        return {"slope": math.nan, "intercept": math.nan, "r2": math.nan}
    x = np.asarray(bands, dtype=np.float64)
    y = np.log2(np.asarray(reaches, dtype=np.float64))
    slope, intercept = np.polyfit(x, y, 1)
    predicted = slope * x + intercept
    residual = float(np.sum((y - predicted) ** 2))
    total = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 if total == 0.0 and residual == 0.0 else 1.0 - residual / total
    return {"slope": float(slope), "intercept": float(intercept), "r2": float(r2)}


def commission_pyramid() -> dict[str, Any]:
    length = 8192
    boundary = 2048
    continuous = np.ones(length, dtype=np.float64)
    black_step = continuous.copy()
    black_step[:boundary] = 0.0
    restored_step = black_step.copy()
    bands_values = [2, 4, 7]
    readings: dict[str, Any] = {}
    reaches: list[int] = []
    worst_null = 0.0
    worst_improved = 0.0
    worst_restoration = 0.0

    for bands in bands_values:
        step_pyramid = build_pyramid(black_step, bands)
        continuous_pyramid = build_pyramid(continuous, bands)
        null_reconstruction = collapse_pyramid(step_pyramid)
        mixed = [level.copy() for level in step_pyramid[:-1]] + [
            continuous_pyramid[-1].copy()
        ]
        defect_reconstruction = collapse_pyramid(mixed)
        improved_pyramid = build_pyramid(continuous, bands)
        improved_mixed = [level.copy() for level in improved_pyramid[:-1]] + [
            continuous_pyramid[-1].copy()
        ]
        improved_reconstruction = collapse_pyramid(improved_mixed)
        restored_pyramid = build_pyramid(restored_step, bands)
        restored_mixed = [level.copy() for level in restored_pyramid[:-1]] + [
            continuous_pyramid[-1].copy()
        ]
        restored_reconstruction = collapse_pyramid(restored_mixed)

        valid = slice(boundary, None)
        defect_error = defect_reconstruction[valid] - continuous[valid]
        improved_error = improved_reconstruction[valid] - continuous[valid]
        restored_error = restored_reconstruction[valid] - continuous[valid]
        reach = threshold_reach(defect_error, 0.001)
        reaches.append(reach)
        null_error = float(np.max(np.abs(null_reconstruction - black_step)))
        improvement_peak = float(np.max(np.abs(improved_error)))
        restoration_error = float(np.max(np.abs(restored_error - defect_error)))
        worst_null = max(worst_null, null_error)
        worst_improved = max(worst_improved, improvement_peak)
        worst_restoration = max(worst_restoration, restoration_error)
        readings[str(bands)] = {
            "operator_null_max_abs": null_error,
            "defect_positive_peak": float(np.max(defect_error)),
            "defect_abs_peak": float(np.max(np.abs(defect_error))),
            "threshold_reach_px": reach,
            "improved_abs_peak": improvement_peak,
            "restoration_max_abs_delta": restoration_error,
        }

    fit = fit_log2_reach(bands_values, reaches)
    defect_peak = max(float(readings[str(b)]["defect_abs_peak"]) for b in bands_values)
    checks = {
        "operator_null": worst_null <= 1e-6,
        "defect_fires": all(float(readings[str(b)]["defect_positive_peak"]) > 0.001 for b in bands_values),
        "improvement_reduces_95pct": worst_improved <= 0.05 * defect_peak,
        "restoration_returns": worst_restoration <= 1e-6,
        "reach_monotone": reaches == sorted(reaches) and len(set(reaches)) == len(reaches),
        "reach_slope": 0.5 <= fit["slope"] <= 1.5,
    }
    return {
        "checks": checks,
        "passed": all(checks.values()),
        "bands": readings,
        "fit": fit,
    }


@dataclass(frozen=True)
class Similarity:
    a: complex
    b: complex

    def apply_at(self, x: float, y: float, cx: float, cy: float) -> tuple[float, float]:
        point = self.a * complex(x - cx, y - cy) + self.b
        return point.real + cx, point.imag + cy


def bits_to_f64(value: str) -> float:
    return struct.unpack(">d", struct.pack(">Q", int(value, 16)))[0]


def parse_sidecar(path: Path) -> tuple[int, int, list[Similarity]]:
    width = height = None
    placements: list[Similarity] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("plane "):
            width, height = (int(part) for part in line.split()[1].split("x"))
        fields = line.split()
        if len(fields) >= 7 and fields[0].isdigit() and fields[1] == "placed":
            a_re, a_im, b_re, b_im = (bits_to_f64(value) for value in fields[2:6])
            placements.append(Similarity(complex(a_re, a_im), complex(b_re, b_im)))
    if width is None or height is None or not placements:
        raise ValueError(f"failed to parse geometry/placements from {path}")
    return width, height, placements


def apply_scaled(
    transform: Similarity,
    x: float,
    y: float,
    cx: float,
    cy: float,
    scale: float,
) -> tuple[float, float]:
    scaled_x = cx + scale * (x - cx)
    scaled_y = cy + scale * (y - cy)
    return transform.apply_at(scaled_x, scaled_y, cx, cy)


def cover_scale(width: int, height: int, placements: list[Similarity], margin: float) -> float:
    cx, cy = width * 0.5, height * 0.5
    corners = [(0.0, 0.0), (width - 1.0, 0.0), (0.0, height - 1.0), (width - 1.0, height - 1.0)]

    def covers(scale: float) -> bool:
        for transform in placements:
            for x, y in corners:
                sx, sy = apply_scaled(transform, x, y, cx, cy, scale)
                if not (
                    sx >= margin
                    and sy >= margin
                    and sx <= width - 1.0 - margin
                    and sy <= height - 1.0 - margin
                ):
                    return False
        return True

    if covers(1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if covers(mid):
            lo = mid
        else:
            hi = mid
    return lo


def crop_axis(size: int, scale: float) -> tuple[int, int]:
    n = float(size)
    lo = 0.5 * n * (1.0 - scale)
    hi = lo + scale * (n - 1.0)
    start = max(0, math.ceil(lo))
    end = max(start, min(size - 1, math.floor(hi)))
    return start, end - start + 1


def conservative_slack(
    transform: Similarity,
    points: list[tuple[float, float]],
    width: int,
    height: int,
    *,
    scale: float = 1.0,
) -> float:
    cx, cy = width * 0.5, height * 0.5
    slack = math.inf
    for x, y in points:
        sx, sy = apply_scaled(transform, x, y, cx, cy, scale)
        slack = min(slack, sx - 3.0, sy - 3.0, width - 1.0 - 3.0 - sx, height - 1.0 - 3.0 - sy)
    return slack


def exact_site_slack(
    transform: Similarity,
    points: list[tuple[float, float]],
    width: int,
    height: int,
    *,
    scale: float = 1.0,
) -> float:
    cx, cy = width * 0.5, height * 0.5
    low = 0.75
    high_x = width - 1.25
    high_y = height - 1.25
    slack = math.inf
    for ox, oy in ((0.0, 0.0), (0.5, 0.0), (0.0, 0.5), (0.5, 0.5)):
        for x, y in points:
            sx, sy = apply_scaled(transform, x + ox, y + oy, cx, cy, scale)
            slack = min(slack, sx - low, sy - low, high_x - sx, high_y - sy)
    return slack


def command_coverage(args: argparse.Namespace) -> int:
    sidecar = args.sidecar.resolve()
    actual_hash = sha256(sidecar)
    if actual_hash != EXPECTED_HASHES["sidecar"]:
        raise SystemExit(f"sidecar hash mismatch: {actual_hash}")
    width, height, placements = parse_sidecar(sidecar)
    scale = cover_scale(width, height, placements, 3.0)
    crop_x, crop_width = crop_axis(width, scale)
    crop_y, crop_height = crop_axis(height, scale)
    crop_points = [
        (float(crop_x), float(crop_y)),
        (float(crop_x + crop_width - 1), float(crop_y)),
        (float(crop_x), float(crop_y + crop_height - 1)),
        (float(crop_x + crop_width - 1), float(crop_y + crop_height - 1)),
    ]
    full_points = [
        (0.0, 0.0),
        (float(width - 1), 0.0),
        (0.0, float(height - 1)),
        (float(width - 1), float(height - 1)),
    ]
    crop_conservative = [
        conservative_slack(transform, crop_points, width, height) for transform in placements
    ]
    crop_exact = [exact_site_slack(transform, crop_points, width, height) for transform in placements]
    scale_conservative = [
        conservative_slack(transform, full_points, width, height, scale=scale)
        for transform in placements
    ]
    scale_exact = [
        exact_site_slack(transform, full_points, width, height, scale=scale)
        for transform in placements
    ]
    unscaled_whole = [
        conservative_slack(transform, full_points, width, height) >= 0.0
        for transform in placements
    ]
    expected_rect = (23, 16, 3470, 2312)
    measured_rect = (crop_x, crop_y, crop_width, crop_height)
    checks = {
        "rect_matches_cover": measured_rect == expected_rect,
        "all_22_crop_conservative": len(placements) == 22 and min(crop_conservative) >= 0.0,
        "all_22_crop_exact_sites": len(placements) == 22 and min(crop_exact) >= 0.0,
        "all_22_scale_conservative": len(placements) == 22 and min(scale_conservative) >= -1e-12,
        "all_22_scale_exact_sites": len(placements) == 22 and min(scale_exact) >= 0.0,
        "unscaled_grid_has_missing_frames": not all(unscaled_whole),
    }
    payload = {
        "sidecar": str(sidecar),
        "sidecar_sha256": actual_hash,
        "plane": [width, height],
        "placements": len(placements),
        "cover_scale": scale,
        "crop_rect": {
            "x": crop_x,
            "y": crop_y,
            "width": crop_width,
            "height": crop_height,
        },
        "crop_min_conservative_margin_slack_px": min(crop_conservative),
        "crop_min_exact_fullres_site_slack_px": min(crop_exact),
        "scale_min_conservative_margin_slack_px": min(scale_conservative),
        "scale_min_exact_fullres_site_slack_px": min(scale_exact),
        "frames_covering_whole_unscaled_grid_at_margin3": int(sum(unscaled_whole)),
        "crop_contribution_count_min": len(placements) if min(crop_exact) >= 0.0 else None,
        "crop_contribution_count_max": len(placements) if min(crop_exact) >= 0.0 else None,
        "checks": checks,
        "passed": all(checks.values()),
    }
    write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def green_distance_stats(path: Path) -> dict[str, Any]:
    image = tifffile.imread(path)
    if image.ndim != 3 or image.shape[2] < 2:
        raise ValueError(f"{path} is not an interleaved RGB TIFF: {image.shape}")
    green = image[..., 1]
    sums, counts = per_distance(green)
    return {
        "path": str(path.resolve()),
        "sha256": sha256(path),
        "shape": list(image.shape),
        "sums": sums,
        "counts": counts,
    }


def radial_positive_mass(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    deep_ratio: float,
    stop: int,
) -> float:
    n = min(stop, candidate["sums"].size, reference["sums"].size)
    counts = candidate["counts"][:n].astype(np.float64)
    candidate_mean = candidate["sums"][:n] / counts
    reference_mean = reference["sums"][:n] / counts
    positive = np.maximum(candidate_mean / deep_ratio - reference_mean, 0.0)
    denominator = float(np.sum(reference_mean * counts))
    return float(np.sum(positive * counts) / denominator)


def command_profile(args: argparse.Namespace) -> int:
    paths = {
        "crop_b2": args.crop_b2.resolve(),
        "crop_b4": args.crop_b4.resolve(),
        "crop_b7": args.crop_b7.resolve(),
        "scale_b2": args.scale_b2.resolve(),
        "scale_b7": args.scale_b7.resolve(),
    }
    stats = {name: green_distance_stats(path) for name, path in paths.items()}
    for name, expected in EXPECTED_HASHES.items():
        if name in stats and stats[name]["sha256"] != expected:
            raise SystemExit(f"{name} hash mismatch: {stats[name]['sha256']} != {expected}")
    if stats["crop_b2"]["shape"] != stats["crop_b4"]["shape"] or stats["crop_b2"]["shape"] != stats["crop_b7"]["shape"]:
        raise SystemExit("Crop shapes differ")
    if stats["scale_b2"]["shape"] != stats["scale_b7"]["shape"]:
        raise SystemExit("Scale shapes differ")

    scale_calibration: dict[str, Any] = {}
    selected_bin_width = None
    scale_profile = None
    for bin_width in (8, 16, 32, 64, 128):
        candidate_profile = annular_effect(
            stats["scale_b7"]["sums"],
            stats["scale_b2"]["sums"],
            stats["scale_b7"]["counts"],
            threshold=0.001,
            deep_start=768,
            bin_width=bin_width,
        )
        peak = profile_peak(candidate_profile, 768)
        clears = candidate_profile["safe_inset_px"] == 8 and peak <= 0.001
        scale_calibration[str(bin_width)] = {
            "safe_inset_px": candidate_profile["safe_inset_px"],
            "peak_abs_effect_before_deep": peak,
            "clears": clears,
        }
        if clears and selected_bin_width is None:
            selected_bin_width = bin_width
            scale_profile = candidate_profile
    if selected_bin_width is None or scale_profile is None:
        raise SystemExit("no preregistered annulus width cleared the Scale specificity control")

    crop_profiles: dict[str, Any] = {}
    reaches: list[int] = []
    for bands in (2, 4, 7):
        candidate = stats[f"crop_b{bands}"]
        reference = stats["crop_b2"]
        profile = annular_effect(
            candidate["sums"],
            reference["sums"],
            candidate["counts"],
            threshold=0.001,
            deep_start=768,
            bin_width=selected_bin_width,
        )
        crop_profiles[str(bands)] = profile
        reaches.append(profile["safe_inset_px"] or 0)
    fit = fit_log2_reach([2, 4, 7], reaches)
    crop_peak = profile_peak(crop_profiles["7"], 256)
    scale_peak = profile_peak(scale_profile, 256)
    crop_mass = radial_positive_mass(
        stats["crop_b7"],
        stats["crop_b2"],
        float(crop_profiles["7"]["deep_ratio"]),
        256,
    )
    scale_mass = radial_positive_mass(
        stats["scale_b7"],
        stats["scale_b2"],
        float(scale_profile["deep_ratio"]),
        256,
    )
    mass_ratio = scale_mass / crop_mass if crop_mass > 0.0 else math.inf
    peak_ratio = scale_peak / crop_peak if crop_peak > 0.0 else math.inf
    h2_checks = {
        "reach_monotone": reaches == sorted(reaches),
        "slope": 0.75 <= fit["slope"] <= 1.25,
        "r2": fit["r2"] >= 0.90,
        "endpoint_ratio": reaches[0] > 0 and reaches[-1] / reaches[0] >= 16.0,
    }
    h5_checks = {
        "scale_peak_below_20pct": peak_ratio < 0.20,
        "scale_positive_mass_below_20pct": mass_ratio < 0.20,
    }
    payload = {
        "inputs": {
            name: {
                "path": value["path"],
                "sha256": value["sha256"],
                "shape": value["shape"],
            }
            for name, value in stats.items()
        },
        "crop": {
            "profiles": crop_profiles,
            "reaches_px": {"2": reaches[0], "4": reaches[1], "7": reaches[2]},
            "log2_reach_fit": fit,
            "h2_checks": h2_checks,
            "h2_passed": all(h2_checks.values()),
            "b7_peak_abs_effect_through_256": crop_peak,
            "b7_positive_radial_level_mass_through_256": crop_mass,
        },
        "scale": {
            "calibration": scale_calibration,
            "selected_bin_width_px": selected_bin_width,
            "profile_b7_vs_b2": scale_profile,
            "peak_abs_effect_through_256": scale_peak,
            "positive_radial_level_mass_through_256": scale_mass,
        },
        "scale_vs_crop": {
            "peak_ratio": peak_ratio,
            "positive_mass_ratio": mass_ratio,
            "h5_checks": h5_checks,
            "h5_measurement_passed": all(h5_checks.values()),
        },
    }
    write_json(args.out, payload)
    printable = {
        "inputs": payload["inputs"],
        "crop_reaches_px": payload["crop"]["reaches_px"],
        "crop_fit": fit,
        "crop_h2_checks": h2_checks,
        "crop_peak": crop_peak,
        "crop_positive_mass": crop_mass,
        "scale_safe_inset_px": scale_profile["safe_inset_px"],
        "selected_bin_width_px": selected_bin_width,
        "scale_peak": scale_peak,
        "scale_positive_mass": scale_mass,
        "scale_vs_crop": payload["scale_vs_crop"],
    }
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


def git_file(commit: str, path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def command_source_audit(args: argparse.Namespace) -> int:
    commit = args.commit
    files = [
        "crates/strehl-cli/src/align_cmd.rs",
        "crates/strehl-cli/src/merge_cmd.rs",
        "crates/strehl-core/src/pyramid.rs",
        "crates/strehl-core/src/align.rs",
        "crates/strehl-core/src/photometric.rs",
    ]
    needles = {
        "crates/strehl-cli/src/align_cmd.rs": [
            "if mode == CoverMode::Crop",
            "pub const COVER_MARGIN_PX",
            "pub fn cover_rect",
            "match resampler.sample_checked",
            "black_dn",
        ],
        "crates/strehl-cli/src/merge_cmd.rs": [
            "fn prepare_frame",
            "align_cmd::warp_frame_in_place",
            "fn run_pyramid",
            "not applied     : photometric gain",
            "let planes = merge.finish",
            "alignment.as_ref().and_then(|(_, _, fit)| fit.rect())",
            "fn write_merged",
            "THE ONE PLACE THE CROP IS APPLIED",
        ],
        "crates/strehl-core/src/pyramid.rs": [
            "pub const KERNEL",
            "pub const DEFAULT_BANDS",
            "pub fn reduce",
            "pub fn expand",
            "pub fn add_frame_with_gain",
            "pub fn finish",
            "fn smooth5",
        ],
        "crates/strehl-core/src/align.rs": [
            "pub fn support",
            "pub fn sample_checked",
            "one more px of the coverage-cropped field is unavailable per side",
        ],
    }
    payload: dict[str, Any] = {"commit": commit, "files": {}}
    literal_pattern = re.compile(r"(?<![\w.])(128|256)(?![\w.])")
    for path in files:
        text = git_file(commit, path)
        lines = text.splitlines()
        literal_hits = []
        for number, line in enumerate(lines, start=1):
            if literal_pattern.search(line):
                literal_hits.append({"line": number, "text": line.strip()})
        symbol_hits: dict[str, list[int]] = {}
        for needle in needles.get(path, []):
            symbol_hits[needle] = [
                number for number, line in enumerate(lines, start=1) if needle in line
            ]
        payload["files"][path] = {
            "literal_128_256_hits": literal_hits,
            "symbol_lines": symbol_hits,
        }
    write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_commission(args: argparse.Namespace) -> int:
    detector = commission_detector()
    pyramid = commission_pyramid()
    payload = {
        "detector": detector,
        "pyramid_model": pyramid,
        "passed": detector["passed"] and pyramid["passed"],
    }
    write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    commission = subparsers.add_parser("commission")
    commission.add_argument("--out", type=Path, required=True)
    commission.set_defaults(func=command_commission)

    coverage = subparsers.add_parser("coverage")
    coverage.add_argument("sidecar", type=Path)
    coverage.add_argument("--out", type=Path, required=True)
    coverage.set_defaults(func=command_coverage)

    profile = subparsers.add_parser("profile")
    profile.add_argument("--crop-b2", type=Path, required=True)
    profile.add_argument("--crop-b4", type=Path, required=True)
    profile.add_argument("--crop-b7", type=Path, required=True)
    profile.add_argument("--scale-b2", type=Path, required=True)
    profile.add_argument("--scale-b7", type=Path, required=True)
    profile.add_argument("--out", type=Path, required=True)
    profile.set_defaults(func=command_profile)

    source = subparsers.add_parser("source-audit")
    source.add_argument("--commit", required=True)
    source.add_argument("--out", type=Path, required=True)
    source.set_defaults(func=command_source_audit)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
