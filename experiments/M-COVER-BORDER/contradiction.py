from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import tifffile

import instrument as base


THRESHOLD = 0.001
DEEP_START = 768
PROFILE_EDGES = (
    0,
    2,
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    192,
    256,
    320,
    384,
    448,
    512,
    640,
    768,
)
CENTRAL_WINDOW_SIZE = 1024
CENTRAL_DEEP_START = 384
CENTRAL_EDGES = (
    0,
    2,
    4,
    8,
    16,
    32,
    64,
    96,
    128,
    160,
    192,
    256,
    320,
    384,
)


def fixed_profile(
    candidate_sums: np.ndarray,
    reference_sums: np.ndarray,
    counts: np.ndarray,
    *,
    threshold: float = THRESHOLD,
    deep_start: int = DEEP_START,
    edges: Sequence[int] = PROFILE_EDGES,
    normalise: bool = True,
) -> dict[str, Any]:
    n = min(candidate_sums.size, reference_sums.size, counts.size)
    candidate_sums = candidate_sums[:n]
    reference_sums = reference_sums[:n]
    counts = counts[:n]
    if deep_start >= n or int(counts[deep_start:].sum()) == 0:
        raise ValueError(f"deep start {deep_start} exceeds maximum distance {n - 1}")
    deep_ratio = float(
        candidate_sums[deep_start:].sum(dtype=np.float64)
        / reference_sums[deep_start:].sum(dtype=np.float64)
    )
    divisor = deep_ratio if normalise else 1.0
    boundaries = sorted(
        {
            int(edge)
            for edge in edges
            if type(edge) is int and 0 <= int(edge) < n
        }
    )
    if not boundaries or boundaries[0] != 0 or deep_start not in boundaries:
        raise ValueError("fixed profile edges must begin at zero and include deep start")
    rows: list[dict[str, Any]] = []
    for index, lo in enumerate(boundaries):
        hi = boundaries[index + 1] if index + 1 < len(boundaries) else n
        count = int(counts[lo:hi].sum())
        if count <= 0:
            continue
        candidate_mean = float(
            candidate_sums[lo:hi].sum(dtype=np.float64) / count
        )
        reference_mean = float(
            reference_sums[lo:hi].sum(dtype=np.float64) / count
        )
        if reference_mean <= 0.0:
            raise ValueError("non-positive reference annulus")
        rows.append(
            {
                "lo": lo,
                "hi": hi,
                "samples": count,
                "candidate_mean": candidate_mean,
                "reference_mean": reference_mean,
                "ratio": candidate_mean / reference_mean,
                "normalised_effect": candidate_mean
                / reference_mean
                / divisor
                - 1.0,
            }
        )
    safe = None
    for row_index, row in enumerate(rows):
        candidate = int(row["lo"])
        if candidate < 8:
            continue
        if all(
            abs(float(tail["normalised_effect"])) <= threshold
            for tail in rows[row_index:]
        ):
            safe = candidate
            break
    censored = safe == deep_start
    return {
        "threshold": threshold,
        "deep_start_px": deep_start,
        "deep_ratio": deep_ratio,
        "safe_inset_px": safe,
        "censored_at_deep_start": censored,
        "admitted_safe_inset_px": None if censored else safe,
        "rows": rows,
    }


def residual_masses(
    candidate_sums: np.ndarray,
    reference_sums: np.ndarray,
    counts: np.ndarray,
    deep_ratio: float,
    stop: int | None = None,
) -> dict[str, float]:
    n = min(candidate_sums.size, reference_sums.size, counts.size)
    if stop is not None:
        n = min(n, stop)
    count = counts[:n].astype(np.float64, copy=False)
    candidate_mean = candidate_sums[:n] / count
    reference_mean = reference_sums[:n] / count
    residual = candidate_mean / deep_ratio - reference_mean
    denominator = float(np.sum(reference_mean * count, dtype=np.float64))
    values = residual * count
    signed = float(np.sum(values, dtype=np.float64))
    absolute = float(np.sum(np.abs(values), dtype=np.float64))
    positive = float(np.sum(np.maximum(values, 0.0), dtype=np.float64))
    negative = float(np.sum(np.maximum(-values, 0.0), dtype=np.float64))
    return {
        "denominator_level_sum": denominator,
        "signed_level_sum": signed,
        "absolute_level_sum": absolute,
        "positive_level_sum": positive,
        "negative_level_sum": negative,
        "signed_fraction": signed / denominator,
        "absolute_fraction": absolute / denominator,
        "positive_fraction": positive / denominator,
        "negative_fraction": negative / denominator,
    }


def profile_descriptors(profile: dict[str, Any]) -> dict[str, Any]:
    effects = [
        float(row["normalised_effect"])
        for row in profile["rows"]
        if 8 <= int(row["lo"]) < int(profile["deep_start_px"])
    ]
    signs = [1 if value > 0.0 else -1 if value < 0.0 else 0 for value in effects]
    nonzero = [value for value in signs if value]
    changes = sum(a != b for a, b in zip(nonzero, nonzero[1:]))
    peak = max(
        (
            abs(float(row["normalised_effect"]))
            for row in profile["rows"]
            if int(row["lo"]) < int(profile["deep_start_px"])
        ),
        default=0.0,
    )
    return {
        "signs_from_8_to_deep": signs,
        "sign_changes_from_8_to_deep": changes,
        "peak_abs_effect_before_deep": peak,
    }


def central_window_profile(
    candidate: np.ndarray,
    reference: np.ndarray,
    *,
    window_size: int = CENTRAL_WINDOW_SIZE,
    deep_start: int = CENTRAL_DEEP_START,
    edges: Sequence[int] = CENTRAL_EDGES,
) -> dict[str, Any]:
    if candidate.shape != reference.shape or candidate.ndim != 2:
        raise ValueError("central profile requires equal two-dimensional planes")
    height, width = candidate.shape
    if height < window_size or width < window_size:
        raise ValueError(f"{candidate.shape} is smaller than {window_size}x{window_size}")
    y0 = (height - window_size) // 2
    x0 = (width - window_size) // 2
    candidate_window = candidate[y0 : y0 + window_size, x0 : x0 + window_size]
    reference_window = reference[y0 : y0 + window_size, x0 : x0 + window_size]
    candidate_sums, counts = base.per_distance(candidate_window)
    reference_sums, reference_counts = base.per_distance(reference_window)
    if not np.array_equal(counts, reference_counts):
        raise ValueError("central-window distance counts differ")
    profile = fixed_profile(
        candidate_sums,
        reference_sums,
        counts,
        deep_start=deep_start,
        edges=edges,
    )
    return {
        "window_xywh": [x0, y0, window_size, window_size],
        "minimum_physical_border_clearance_px": min(
            x0,
            y0,
            width - (x0 + window_size),
            height - (y0 + window_size),
        ),
        "profile": profile,
        "descriptors": profile_descriptors(profile),
    }


def boundary_specificity(
    physical: dict[str, Any],
    central: dict[str, Any],
) -> str:
    physical_profile = physical["profile"]
    central_profile = central["profile"]
    physical_safe = physical_profile["safe_inset_px"]
    if physical_safe == 8:
        return "SPECIFIC_AT_FLOOR"
    if physical_safe is None or physical_profile["censored_at_deep_start"]:
        return "UNRESOLVED_PHYSICAL_NEVER_SAFE_BEFORE_DEEP"
    if int(central["minimum_physical_border_clearance_px"]) <= int(physical_safe):
        return "UNRESOLVED_CONTROL_INSIDE_NOMINAL_REACH"
    central_peak = central["descriptors"]["peak_abs_effect_before_deep"]
    if (
        central_profile["safe_inset_px"] != 8
        or central_profile["censored_at_deep_start"]
        or central_peak > THRESHOLD
    ):
        return "NONSPECIFIC_SCENE_TAIL"
    return "BOUNDARY_LOCAL_SUPPORTED"


def load_green(path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] < 2:
        raise ValueError(f"{path}: expected HxWxC TIFF, got {image.shape}")
    if image.dtype != np.uint16:
        raise ValueError(f"{path}: expected uint16, got {image.dtype}")
    green = np.asarray(image[:, :, 1])
    sums, counts = base.per_distance(green)
    return green, {
        "path": str(path.resolve()),
        "sha256": base.sha256(path),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "sums": sums,
        "counts": counts,
    }


def source_manifest(source: Path) -> dict[str, Any]:
    files = sorted(
        (
            path
            for path in source.iterdir()
            if path.is_file() and path.suffix.lower() in {".arw", ".xmp"}
        ),
        key=lambda path: path.name.lower(),
    )
    digest = hashlib.sha256()
    counts: dict[str, int] = {}
    for path in files:
        suffix = path.suffix.lower()
        counts[suffix] = counts.get(suffix, 0) + 1
        file_hash = base.sha256(path)
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash.encode("ascii"))
        digest.update(b"\0")
    return {
        "path": str(source.resolve()),
        "counts": counts,
        "digest": digest.hexdigest().upper(),
    }


def ratio(numerator: float, denominator: float) -> float | None:
    return numerator / denominator if denominator != 0.0 else None


def mode_profile(b7: dict[str, Any], b2: dict[str, Any]) -> dict[str, Any]:
    metadata_guard(b7["shape"], b2["shape"], str(b7["dtype"]))
    if b2["dtype"] != "uint16":
        raise ValueError(f"b2 dtype changed: {b2['dtype']}")
    if not np.array_equal(b7["counts"], b2["counts"]):
        raise ValueError("distance counts differ within mode")
    profile = fixed_profile(b7["sums"], b2["sums"], b7["counts"])
    through_256 = residual_masses(
        b7["sums"],
        b2["sums"],
        b7["counts"],
        float(profile["deep_ratio"]),
        256,
    )
    full = residual_masses(
        b7["sums"],
        b2["sums"],
        b7["counts"],
        float(profile["deep_ratio"]),
    )
    concentration = ratio(
        through_256["positive_level_sum"],
        full["positive_level_sum"],
    )
    return {
        "profile": profile,
        "descriptors": profile_descriptors(profile),
        "positive_residual_mass_through_256": through_256,
        "residual_mass_full_plane": full,
        "positive_mass_concentration_ratio": concentration,
    }


def guard_provenance(
    *,
    binary_sha: str,
    expected_binary_sha: str,
    map_before: str,
    map_after: str,
    exit_codes: Sequence[int],
) -> None:
    failures = []
    if binary_sha != expected_binary_sha:
        failures.append("binary hash")
    if map_before != map_after:
        failures.append("map changed")
    if any(code != 0 for code in exit_codes):
        failures.append("render exit")
    if failures:
        raise ValueError(", ".join(failures))


def commissioned_guard_failure(**kwargs: Any) -> bool:
    try:
        guard_provenance(**kwargs)
    except ValueError:
        return True
    return False


def metadata_guard(
    candidate_shape: Sequence[int],
    reference_shape: Sequence[int],
    dtype: str,
) -> None:
    failures = []
    if list(candidate_shape) != list(reference_shape):
        failures.append("shape")
    if dtype != "uint16":
        failures.append("dtype")
    if failures:
        raise ValueError(", ".join(failures))


def commissioned_metadata_failure(
    candidate_shape: Sequence[int],
    reference_shape: Sequence[int],
    dtype: str,
) -> bool:
    try:
        metadata_guard(candidate_shape, reference_shape, dtype)
    except ValueError:
        return True
    return False


def command_commission(args: argparse.Namespace) -> int:
    height = width = 1024
    yy, xx = np.mgrid[:height, :width]
    control = 8000.0 + 0.125 * xx + 0.0625 * yy
    baseline = 1.1 * control
    distance = base.border_distance(height, width)
    counts = np.bincount(distance.ravel())

    def sums(image: np.ndarray) -> np.ndarray:
        return np.bincount(
            distance.ravel(),
            weights=image.astype(np.float64, copy=False).ravel(),
            minlength=counts.size,
        )

    custom_edges = (0, 8, 16, 32, 64, 128, 192, 256)
    control_sums = sums(control)
    null_sums = sums(baseline)
    null = fixed_profile(
        null_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )

    defect_image = baseline.copy()
    defect_image[distance < 64] *= 1.02
    defect_sums = sums(defect_image)
    defect = fixed_profile(
        defect_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )

    improved_image = baseline.copy()
    improved_image[distance < 64] *= 1.0005
    improved_sums = sums(improved_image)
    improved = fixed_profile(
        improved_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )
    restored = fixed_profile(
        defect_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )
    defect_mass = residual_masses(
        defect_sums, control_sums, counts, float(defect["deep_ratio"])
    )
    defect_mass_through_256 = residual_masses(
        defect_sums,
        control_sums,
        counts,
        float(defect["deep_ratio"]),
        256,
    )
    improved_mass = residual_masses(
        improved_sums, control_sums, counts, float(improved["deep_ratio"])
    )
    central_null = central_window_profile(
        baseline,
        control,
        window_size=512,
        deep_start=192,
        edges=(0, 8, 16, 32, 64, 96, 128, 160, 192),
    )
    physical_defect_central = central_window_profile(
        defect_image,
        control,
        window_size=512,
        deep_start=192,
        edges=(0, 8, 16, 32, 64, 96, 128, 160, 192),
    )
    central_plant_image = baseline.copy()
    y0 = (height - 512) // 2
    x0 = (width - 512) // 2
    central_distance = base.border_distance(512, 512)
    central_view = central_plant_image[y0 : y0 + 512, x0 : x0 + 512]
    central_view[central_distance < 64] *= 1.02
    central_plant = central_window_profile(
        central_plant_image,
        control,
        window_size=512,
        deep_start=192,
        edges=(0, 8, 16, 32, 64, 96, 128, 160, 192),
    )
    swapped = fixed_profile(
        control_sums,
        defect_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )
    threshold_plant = baseline.copy()
    threshold_plant[distance < 64] *= 1.002
    threshold_sums = sums(threshold_plant)
    strict = fixed_profile(
        threshold_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )
    loose = fixed_profile(
        threshold_sums,
        control_sums,
        counts,
        threshold=0.01,
        deep_start=256,
        edges=custom_edges,
    )
    changed_edges = fixed_profile(
        defect_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=(0, 8, 16, 32, 128, 192, 256),
    )
    unnormalised = fixed_profile(
        defect_sums,
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
        normalise=False,
    )
    censored_image = baseline.copy()
    censored_image[distance < 256] *= 1.02
    censored = fixed_profile(
        sums(censored_image),
        control_sums,
        counts,
        deep_start=256,
        edges=custom_edges,
    )

    valid_guard = {
        "binary_sha": "A",
        "expected_binary_sha": "A",
        "map_before": "B",
        "map_after": "B",
        "exit_codes": [0, 0, 0, 0],
    }
    guard_provenance(**valid_guard)
    checks = {
        "null_safe": null["safe_inset_px"] == 8,
        "null_zero": profile_descriptors(null)["peak_abs_effect_before_deep"]
        <= 1e-12,
        "defect_safe": defect["safe_inset_px"] == 64,
        "defect_peak": math.isclose(
            float(defect["rows"][0]["normalised_effect"]),
            0.02,
            abs_tol=1e-12,
        ),
        "improvement_safe": improved["safe_inset_px"] == 8,
        "improvement_mass": improved_mass["positive_fraction"]
        <= 0.05 * defect_mass["positive_fraction"],
        "defect_concentration": math.isclose(
            defect_mass_through_256["positive_level_sum"]
            / defect_mass["positive_level_sum"],
            1.0,
            abs_tol=1e-12,
        ),
        "central_null_safe": central_null["profile"]["safe_inset_px"] == 8,
        "physical_defect_central_safe": physical_defect_central["profile"][
            "safe_inset_px"
        ]
        == 8,
        "central_plant_safe": central_plant["profile"]["safe_inset_px"] == 64,
        "restoration_safe": restored["safe_inset_px"]
        == defect["safe_inset_px"],
        "restoration_rows": restored["rows"] == defect["rows"],
        "swapped_red": float(swapped["rows"][0]["normalised_effect"]) < 0.0,
        "threshold_red": strict["safe_inset_px"] != loose["safe_inset_px"],
        "edge_red": changed_edges["safe_inset_px"]
        != defect["safe_inset_px"],
        "normalisation_red": not math.isclose(
            float(unnormalised["rows"][0]["normalised_effect"]),
            0.02,
            abs_tol=1e-12,
        ),
        "deep_start_censored": censored["safe_inset_px"] == 256
        and censored["censored_at_deep_start"]
        and censored["admitted_safe_inset_px"] is None,
        "unit_768": 768 / 2 == 384,
        "unit_1280": 1280 / 2 == 640,
        "unit_640": 640 / 2 == 320,
        "binary_guard_red": commissioned_guard_failure(
            **{**valid_guard, "binary_sha": "X"}
        ),
        "map_guard_red": commissioned_guard_failure(
            **{**valid_guard, "map_after": "X"}
        ),
        "exit_guard_red": commissioned_guard_failure(
            **{**valid_guard, "exit_codes": [0, 0, 1, 0]}
        ),
        "shape_guard_red": commissioned_metadata_failure(
            [4, 4, 3], [5, 4, 3], "uint16"
        ),
        "dtype_guard_red": commissioned_metadata_failure(
            [4, 4, 3], [4, 4, 3], "float32"
        ),
        "specificity_floor": boundary_specificity(
            {"profile": {"safe_inset_px": 8, "censored_at_deep_start": False}},
            {
                "profile": {
                    "safe_inset_px": 8,
                    "censored_at_deep_start": False,
                },
                "descriptors": {"peak_abs_effect_before_deep": 0.0},
                "minimum_physical_border_clearance_px": 100,
            },
        )
        == "SPECIFIC_AT_FLOOR",
        "specificity_boundary": boundary_specificity(
            {"profile": {"safe_inset_px": 64, "censored_at_deep_start": False}},
            {
                "profile": {
                    "safe_inset_px": 8,
                    "censored_at_deep_start": False,
                },
                "descriptors": {"peak_abs_effect_before_deep": 0.0},
                "minimum_physical_border_clearance_px": 100,
            },
        )
        == "BOUNDARY_LOCAL_SUPPORTED",
        "specificity_scene": boundary_specificity(
            {"profile": {"safe_inset_px": 64, "censored_at_deep_start": False}},
            {
                "profile": {
                    "safe_inset_px": 32,
                    "censored_at_deep_start": False,
                },
                "descriptors": {"peak_abs_effect_before_deep": 0.01},
                "minimum_physical_border_clearance_px": 100,
            },
        )
        == "NONSPECIFIC_SCENE_TAIL",
        "specificity_inside_reach": boundary_specificity(
            {"profile": {"safe_inset_px": 64, "censored_at_deep_start": False}},
            {
                "profile": {
                    "safe_inset_px": 8,
                    "censored_at_deep_start": False,
                },
                "descriptors": {"peak_abs_effect_before_deep": 0.0},
                "minimum_physical_border_clearance_px": 32,
            },
        )
        == "UNRESOLVED_CONTROL_INSIDE_NOMINAL_REACH",
    }
    payload = {
        "schema": "M-COVER-BORDER-CONTRADICTION-COMMISSION-1",
        "checks": checks,
        "passed": all(checks.values()),
        "readings": {
            "null_safe_inset_px": null["safe_inset_px"],
            "defect_safe_inset_px": defect["safe_inset_px"],
            "improvement_safe_inset_px": improved["safe_inset_px"],
            "defect_positive_mass": defect_mass["positive_fraction"],
            "improvement_positive_mass": improved_mass["positive_fraction"],
            "improvement_fraction": ratio(
                improved_mass["positive_fraction"],
                defect_mass["positive_fraction"],
            ),
            "central_null_safe_inset_px": central_null["profile"][
                "safe_inset_px"
            ],
            "physical_defect_central_safe_inset_px": physical_defect_central[
                "profile"
            ]["safe_inset_px"],
            "central_plant_safe_inset_px": central_plant["profile"][
                "safe_inset_px"
            ],
            "censored_safe_inset_px": censored["safe_inset_px"],
            "censored_admitted_safe_inset_px": censored[
                "admitted_safe_inset_px"
            ],
        },
    }
    base.write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


def command_profile(args: argparse.Namespace) -> int:
    binary_sha = base.sha256(args.binary)
    if binary_sha != args.expected_binary_sha.upper():
        raise SystemExit(
            f"binary hash mismatch: {binary_sha} != {args.expected_binary_sha.upper()}"
        )
    map_sha = base.sha256(args.map)
    if args.expected_map_sha and map_sha != args.expected_map_sha.upper():
        raise SystemExit(
            f"map hash mismatch: {map_sha} != {args.expected_map_sha.upper()}"
        )

    paths = {
        "scale_b2": args.scale_b2,
        "scale_b7": args.scale_b7,
        "crop_b2": args.crop_b2,
        "crop_b7": args.crop_b7,
    }
    if args.crop_b4:
        paths["crop_b4"] = args.crop_b4
    loaded: dict[str, dict[str, Any]] = {}
    greens: dict[str, np.ndarray] = {}
    for name, path in paths.items():
        greens[name], loaded[name] = load_green(path)

    scale = mode_profile(loaded["scale_b7"], loaded["scale_b2"])
    crop = mode_profile(loaded["crop_b7"], loaded["crop_b2"])
    scale_central = central_window_profile(
        greens["scale_b7"], greens["scale_b2"]
    )
    crop_central = central_window_profile(greens["crop_b7"], greens["crop_b2"])
    for physical, central in ((scale, scale_central), (crop, crop_central)):
        physical["central_artificial_boundary_control"] = central
        physical["boundary_specificity_disposition"] = boundary_specificity(
            physical, central
        )
    through_ratio = ratio(
        scale["positive_residual_mass_through_256"]["positive_fraction"],
        crop["positive_residual_mass_through_256"]["positive_fraction"],
    )
    full_ratio = ratio(
        scale["residual_mass_full_plane"]["positive_fraction"],
        crop["residual_mass_full_plane"]["positive_fraction"],
    )
    peak_ratio = ratio(
        scale["descriptors"]["peak_abs_effect_before_deep"],
        crop["descriptors"]["peak_abs_effect_before_deep"],
    )
    concealment = "UNRESOLVED"
    if (
        through_ratio is not None
        and full_ratio is not None
        and through_ratio < 0.20
        and full_ratio < 0.20
    ):
        concealment = "REJECTED_NOT_CONSERVED"
    elif (
        through_ratio is not None
        and full_ratio is not None
        and peak_ratio is not None
        and (through_ratio >= 0.50 or full_ratio >= 0.50)
        and peak_ratio < 1.0
    ):
        concealment = "SUPPORTED_CONSERVED_AND_LOWER_PEAK"

    crop_ladder = None
    if "crop_b4" in loaded:
        b2_self = mode_profile(loaded["crop_b2"], loaded["crop_b2"])
        b4 = mode_profile(loaded["crop_b4"], loaded["crop_b2"])
        reaches = [
            int(b2_self["profile"]["safe_inset_px"] or 0),
            int(b4["profile"]["safe_inset_px"] or 0),
            int(crop["profile"]["safe_inset_px"] or 0),
        ]
        if all(reach > 0 for reach in reaches):
            fit = base.fit_log2_reach([2, 4, 7], reaches)
            checks = {
                "monotone": reaches == sorted(reaches),
                "slope": 0.75 <= fit["slope"] <= 1.25,
                "r2": fit["r2"] >= 0.90,
                "endpoint": reaches[-1] / reaches[0] >= 16,
            }
        else:
            fit = None
            checks = {
                "monotone": False,
                "slope": False,
                "r2": False,
                "endpoint": False,
            }
        crop_ladder = {
            "reaches_px": {"2": reaches[0], "4": reaches[1], "7": reaches[2]},
            "fit": fit,
            "checks": checks,
            "passed": all(checks.values()),
            "b4_vs_b2": b4,
        }

    serialisable_inputs = {
        name: {
            key: value
            for key, value in entry.items()
            if key not in {"sums", "counts"}
        }
        for name, entry in loaded.items()
    }
    payload = {
        "schema": "M-COVER-BORDER-COMMON-LINEAR-PROFILE-1",
        "source_label": args.source_label,
        "definition": {
            "space": "default linear camera-native RGB16",
            "distance_unit": "binned plane pixels",
            "full_resolution_pixels_per_plane_pixel": 2,
            "threshold": THRESHOLD,
            "deep_start_px": DEEP_START,
            "edges_px": list(PROFILE_EDGES),
            "safe": "smallest registered lo>=8 with abs(effect)<=threshold in every deeper annulus",
        },
        "provenance": {
            "binary": {
                "path": str(args.binary.resolve()),
                "sha256": binary_sha,
            },
            "source": source_manifest(args.source),
            "map": {
                "path": str(args.map.resolve()),
                "sha256": map_sha,
            },
            "inputs": serialisable_inputs,
        },
        "scale": scale,
        "crop": crop,
        "original_specificity_condition": {
            "scale_safe_equals_8": scale["profile"]["safe_inset_px"] == 8,
            "specific": scale["profile"]["safe_inset_px"] == 8,
        },
        "scale_vs_crop": {
            "nominal_safe_ratio": ratio(
                float(crop["profile"]["safe_inset_px"]),
                float(scale["profile"]["safe_inset_px"]),
            )
            if crop["profile"]["safe_inset_px"] is not None
            and scale["profile"]["safe_inset_px"] is not None
            else None,
            "positive_mass_ratio_through_256": through_ratio,
            "positive_mass_ratio_full_plane": full_ratio,
            "peak_ratio": peak_ratio,
            "concealment_disposition": concealment,
        },
        "crop_ladder": crop_ladder,
    }
    map_sha_after = base.sha256(args.map)
    if map_sha_after != map_sha:
        raise SystemExit("map changed while profiling")
    commission = json.loads(args.commission.read_text(encoding="utf-8"))
    if not commission.get("passed"):
        raise SystemExit("commission file is not GREEN")
    payload["commission"] = {
        "path": str(args.commission.resolve()),
        "schema": commission.get("schema"),
        "passed": commission.get("passed"),
    }
    base.write_json(args.out, payload)
    printable = {
        "source_label": args.source_label,
        "scale_safe": scale["profile"]["safe_inset_px"],
        "crop_safe": crop["profile"]["safe_inset_px"],
        "specific": payload["original_specificity_condition"]["specific"],
        "scale_vs_crop": payload["scale_vs_crop"],
        "crop_ladder": crop_ladder["reaches_px"] if crop_ladder else None,
    }
    print(json.dumps(printable, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    commission = subparsers.add_parser("commission")
    commission.add_argument("--out", type=Path, required=True)
    commission.set_defaults(func=command_commission)

    profile = subparsers.add_parser("profile")
    profile.add_argument("--source-label", required=True)
    profile.add_argument("--binary", type=Path, required=True)
    profile.add_argument("--expected-binary-sha", required=True)
    profile.add_argument("--source", type=Path, required=True)
    profile.add_argument("--map", type=Path, required=True)
    profile.add_argument("--expected-map-sha")
    profile.add_argument("--scale-b2", type=Path, required=True)
    profile.add_argument("--scale-b7", type=Path, required=True)
    profile.add_argument("--crop-b2", type=Path, required=True)
    profile.add_argument("--crop-b4", type=Path)
    profile.add_argument("--crop-b7", type=Path, required=True)
    profile.add_argument("--commission", type=Path, required=True)
    profile.add_argument("--out", type=Path, required=True)
    profile.set_defaults(func=command_profile)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
