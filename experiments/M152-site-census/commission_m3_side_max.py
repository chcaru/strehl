"""Supplemental side-max commissioning for M152.

M152's v1 checker and red artifact remain historical. This script imports the
hash-pinned canonical M161 scorer, replays M152's original synthetic battery,
and adds movable clean-noise arms built from non-holdout dark-frame
differences. Protected site pixels and product outputs are never opened.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import numpy as np
from scipy import ndimage

from census_common import (
    HERE,
    bilinear_profile,
    decode_green,
    load_definition,
    nearest_rank,
    sha256_bytes,
    sha256_file,
)


STUDY_DEFINITION_PATH = HERE / "side-max-commission-definition.json"
MANIFEST_PATH = HERE / "out" / "census-manifest.json"
NOISE_PATH = HERE / "out" / "noise-calibration.json"
OUT_PATH = HERE / "out" / "m3-side-max-commission.json"
PROFILE_OFFSETS = np.arange(-400.0, 401.0, 1.0)
SOURCE_TRACE_OFFSETS = np.arange(-402.0, 403.0, 2.0)


def write_json(path: Path, value: Any) -> None:
    encoded = json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    )
    path.write_text(encoded + "\n", encoding="ascii")


def load_study_definition() -> tuple[dict[str, Any], str]:
    raw = STUDY_DEFINITION_PATH.read_bytes()
    value = json.loads(raw)
    if value.get("schema") != "m152-side-max-commission-definition-v1":
        raise RuntimeError("unexpected M152 side-max commission schema")
    return value, sha256_bytes(raw)


def load_canonical_checker(
    study: dict[str, Any],
) -> tuple[ModuleType, dict[str, Any], str]:
    authority = study["authority"]
    checker_path = (HERE / authority["canonical_checker"]).resolve()
    definition_path = (HERE / authority["canonical_definition"]).resolve()
    if sha256_file(checker_path) != authority["canonical_checker_sha256"]:
        raise RuntimeError("canonical M3 checker hash changed")
    definition_hash = sha256_file(definition_path)
    if definition_hash != authority["canonical_definition_sha256"]:
        raise RuntimeError("canonical M3 definition hash changed")
    module_name = "m152_pinned_m161_checker"
    spec = importlib.util.spec_from_file_location(module_name, checker_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import canonical M3 checker")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    definition = json.loads(definition_path.read_text(encoding="ascii"))
    return module, definition, definition_hash


def verify_frozen_dependencies(
    study: dict[str, Any], census_definition_hash: str
) -> None:
    authority = study["authority"]
    for relative, expected in authority["historical_m152_v1_hashes"].items():
        if sha256_file(HERE / relative) != expected:
            raise RuntimeError(f"historical M152 v1 changed: {relative}")
    local = authority["local_dependency_hashes"]
    if sha256_file(HERE / "census_common.py") != local["census_common.py"]:
        raise RuntimeError("local census_common.py hash changed")
    if census_definition_hash != local["census-definition.json"]:
        raise RuntimeError("frozen census-definition.json hash changed")


def load_frozen_sites(study: dict[str, Any]) -> list[dict[str, Any]]:
    population = study["site_population"]
    if sha256_file(MANIFEST_PATH) != population["manifest_sha256"]:
        raise RuntimeError("frozen census manifest hash changed")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="ascii"))
    sites = manifest["m3"]["sufficiency"]["selected_sites"]
    counts = Counter(str(site["capture_id"]) for site in sites)
    if len(sites) != int(population["selected_site_count"]):
        raise RuntimeError("frozen site count changed")
    if counts != Counter(
        {str(key): int(value) for key, value in population["capture_counts"].items()}
    ):
        raise RuntimeError("frozen per-capture site population changed")
    if len({str(site["site_id"]) for site in sites}) != len(sites):
        raise RuntimeError("frozen site IDs are not unique")
    required = ("step_broad_dn", "sigma_temporal_dn")
    if any(
        not np.isfinite(float(site[key])) or float(site[key]) <= 0.0
        for site in sites
        for key in required
    ):
        raise RuntimeError("frozen site step or sigma is invalid")
    return sites


def logistic_profile(
    offsets: np.ndarray, dark: float, step: float, width: float
) -> np.ndarray:
    return dark + step / (1.0 + np.exp(-offsets / width))


def edge_patch(dark: float, step: float, width: float) -> np.ndarray:
    _, xx = np.indices((128, 128), dtype=np.float64)
    return logistic_profile(xx - 63.5, dark, step, width)


def rim_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    output[(offsets >= -24.0) & (offsets <= -12.0)] -= amplitude * step
    output[(offsets >= 12.0) & (offsets <= 24.0)] += amplitude * step
    return output


def opposite_sign_rim_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    output[(offsets >= -24.0) & (offsets <= -12.0)] += amplitude * step
    output[(offsets >= 12.0) & (offsets <= 24.0)] -= amplitude * step
    return output


def veil_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    support = (np.abs(offsets) >= 16.0) & (np.abs(offsets) <= 200.0)
    output[support] += amplitude * step
    return output


def one_sided_far_veil_plant(
    profile: np.ndarray, offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    output = profile.copy()
    support = (offsets >= 33.0) & (offsets <= 232.0)
    output[support] += amplitude * step
    return output


def planted_patch(
    base: np.ndarray, step: float, rim: float = 0.0, veil: float = 0.0
) -> np.ndarray:
    _, xx = np.indices(base.shape, dtype=np.float64)
    normal = xx - 63.5
    output = base.copy()
    if rim:
        output[(normal >= -24.0) & (normal <= -12.0)] -= rim * step
        output[(normal >= 12.0) & (normal <= 24.0)] += rim * step
    if veil:
        output[(np.abs(normal) >= 16.0) & (np.abs(normal) <= 63.5)] += veil * step
    return output


ProfilePlant = Callable[[np.ndarray, np.ndarray, float], np.ndarray]
PatchPlant = Callable[[np.ndarray, float], np.ndarray]


def synthetic_population(
    sites: list[dict[str, Any]],
    plant: ProfilePlant,
    patch_plant: PatchPlant,
    checker: ModuleType,
    checker_definition: dict[str, Any],
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(152_202_609_04)
    results: list[dict[str, Any]] = []
    for index, metadata in enumerate(sites):
        step = float(rng.uniform(0.25, 0.75))
        dark = float(rng.uniform(0.05, 0.15))
        width = float(rng.uniform(1.6, 2.4))
        base = logistic_profile(PROFILE_OFFSETS, dark, step, width)
        ripple = 0.001 * step * np.sin(
            2.0 * math.pi * PROFILE_OFFSETS / 37.0 + index
        )
        sources = np.stack([base - ripple, base, base + ripple])
        output = plant(base, PROFILE_OFFSETS, step)
        patch = edge_patch(dark, step, width)
        record = checker.SiteProfiles(
            site_id=str(metadata["site_id"]),
            capture_id=str(metadata["capture_id"]),
            offsets_native_px=PROFILE_OFFSETS,
            source_profiles=sources,
            output_profile=output,
            normalization_source_index=1,
            far_reference_source_index=1,
            sharp_source_index=1,
            output_patch=patch_plant(patch, step),
            sharp_source_patch=patch,
        )
        results.append(checker.score_site(record, checker_definition))
    return results


def arm_summary(
    name: str,
    sites: list[dict[str, Any]],
    plant: ProfilePlant,
    patch_plant: PatchPlant,
    checker: ModuleType,
    checker_definition: dict[str, Any],
    planted_amplitude: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = synthetic_population(
        sites, plant, patch_plant, checker, checker_definition
    )
    summary = checker.summarize(rows, definition=checker_definition)
    legacy = np.asarray(
        [float(row["v_e_pooled_diagnostic"]) for row in rows], dtype=np.float64
    )
    summary.update(
        {
            "name": name,
            "planted_amplitude_fraction_of_step": planted_amplitude,
            "detection_rate": summary["affected_edge_rate"],
            "median_v_e_mean_legacy": nearest_rank(legacy, 0.50),
            "p99_v_e_mean_legacy": nearest_rank(legacy, 0.99),
        }
    )
    return summary, rows


def real_raw_identity_null(
    sites: list[dict[str, Any]],
    census_definition: dict[str, Any],
    checker: ModuleType,
    checker_definition: dict[str, Any],
) -> dict[str, Any]:
    selected = [
        site for site in sites if site["capture_id"] == "m3-razor-control"
    ][:50]
    if len(selected) != 50:
        raise RuntimeError("frozen manifest lacks 50 razor-control sites")
    capture = next(
        item
        for item in census_definition["m3"]["captures"]
        if item["capture_id"] == "m3-razor-control"
    )
    source_dir = Path(capture["path"])
    roots = [Path(value) for value in census_definition["allowed_read_roots"]]
    cache: dict[str, Any] = {}
    rows: list[dict[str, Any]] = []
    decoded_inputs: list[dict[str, Any]] = []
    for site in selected:
        name = str(site["source_file"])
        if name not in cache:
            decoded = decode_green(source_dir / name, roots, registered_iso=100.0)
            if decoded.decoded_green_sha256 != site["source_decoded_green_sha256"]:
                raise RuntimeError(f"razor decode hash changed for {name}")
            cache[name] = decoded
            decoded_inputs.append(decoded.input_record())
        decoded = cache[name]
        offsets, profile = bilinear_profile(
            decoded.green_luma_dn,
            (float(site["y_native_px"]) - 0.5) / 2.0,
            (float(site["x_native_px"]) - 0.5) / 2.0,
            float(site["normal_y"]),
            float(site["normal_x"]),
            reach_native_px=400,
        )
        patch = np.outer(
            np.ones(128, dtype=np.float64),
            np.interp(np.linspace(-32.0, 32.0, 128), offsets, profile),
        )
        record = checker.SiteProfiles(
            site_id=str(site["site_id"]),
            capture_id="m3-razor-control",
            offsets_native_px=offsets,
            source_profiles=profile[None, :],
            output_profile=profile.copy(),
            normalization_source_index=0,
            far_reference_source_index=0,
            sharp_source_index=0,
            output_patch=patch,
            sharp_source_patch=patch.copy(),
        )
        rows.append(checker.score_site(record, checker_definition))
    amended = np.asarray([float(row["v_e"]) for row in rows])
    legacy = np.asarray([float(row["v_e_pooled_diagnostic"]) for row in rows])
    affected = int(sum(bool(row["affected"]) for row in rows))
    return {
        "name": "untouched_raw_identity_wiring_null",
        "source_capture": capture["path"],
        "source_class": capture["evidence_class"],
        "site_count": len(rows),
        "median_v_e_mean_legacy": nearest_rank(legacy, 0.50),
        "p99_v_e_mean_legacy": nearest_rank(legacy, 0.99),
        "median_v_e_side_max": nearest_rank(amended, 0.50),
        "p99_v_e_side_max": nearest_rank(amended, 0.99),
        "affected_edge_count": affected,
        "affected_edge_rate": affected / len(rows),
        "decoded_inputs": decoded_inputs,
        "pass": bool(
            np.all(legacy == 0.0)
            and np.all(amended == 0.0)
            and affected == 0
        ),
        "limitation": (
            "Wiring check only: output and far reference are identical, so this "
            "arm has no power to measure side-max inflation."
        ),
    }


@dataclass(frozen=True)
class TraceLocation:
    orientation: str
    line: int
    center: int
    reverse: bool


def allocate_trace_locations(
    sites: list[dict[str, Any]],
    green_shape: tuple[int, int],
    seed: int,
) -> list[TraceLocation]:
    height, width = green_shape
    half = len(SOURCE_TRACE_OFFSETS) // 2
    if min(height, width) <= 2 * half + 1:
        raise RuntimeError("dark frame is too small for empirical traces")
    horizontal = [
        index
        for index, site in enumerate(sites)
        if abs(float(site["normal_x"])) >= abs(float(site["normal_y"]))
    ]
    horizontal_set = set(horizontal)
    vertical = [
        index for index in range(len(sites)) if index not in horizontal_set
    ]
    rng = np.random.default_rng(seed)
    horizontal_lines = rng.choice(
        np.arange(1, height - 1), size=len(horizontal), replace=False
    )
    horizontal_centers = rng.integers(
        half, width - half, size=len(horizontal)
    )
    vertical_lines = rng.choice(
        np.arange(1, width - 1), size=len(vertical), replace=False
    )
    vertical_centers = rng.integers(half, height - half, size=len(vertical))
    locations: list[TraceLocation | None] = [None] * len(sites)
    for slot, index in enumerate(horizontal):
        locations[index] = TraceLocation(
            orientation="horizontal",
            line=int(horizontal_lines[slot]),
            center=int(horizontal_centers[slot]),
            reverse=float(sites[index]["normal_x"]) < 0.0,
        )
    for slot, index in enumerate(vertical):
        locations[index] = TraceLocation(
            orientation="vertical",
            line=int(vertical_lines[slot]),
            center=int(vertical_centers[slot]),
            reverse=float(sites[index]["normal_y"]) < 0.0,
        )
    if any(location is None for location in locations):
        raise RuntimeError("trace allocation left an unassigned site")
    return [location for location in locations if location is not None]


def extract_empirical_trace(
    difference: np.ndarray, location: TraceLocation
) -> np.ndarray:
    half = len(SOURCE_TRACE_OFFSETS) // 2
    if location.orientation == "horizontal":
        samples = difference[
            location.line, location.center - half : location.center + half + 1
        ]
    elif location.orientation == "vertical":
        samples = difference[
            location.center - half : location.center + half + 1, location.line
        ]
    else:
        raise RuntimeError(f"unknown trace orientation {location.orientation}")
    if samples.size != SOURCE_TRACE_OFFSETS.size:
        raise RuntimeError("empirical trace lost full support")
    trace = np.interp(PROFILE_OFFSETS, SOURCE_TRACE_OFFSETS, samples)
    return trace[::-1].copy() if location.reverse else trace


def decode_empirical_traces(
    iso: int,
    sites: list[dict[str, Any]],
    study: dict[str, Any],
    census_definition: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    if sha256_file(NOISE_PATH) != study["empirical_noise"][
        "calibration_artifact_sha256"
    ]:
        raise RuntimeError("frozen noise-calibration artifact hash changed")
    calibration = json.loads(NOISE_PATH.read_text(encoding="ascii"))
    if calibration["source_class"] != "CONTROL_NOT_HOLDOUT":
        raise RuntimeError("empirical noise source is not registered non-holdout")
    group = next(item for item in calibration["groups"] if item["iso"] == iso)
    records = group["inputs"]
    pair_count = int(study["empirical_noise"]["pair_count_per_group"])
    if len(records) != 2 * pair_count or group["pair_count"] != pair_count:
        raise RuntimeError(f"ISO {iso} dark-pair count changed")
    native_shape = tuple(int(value) for value in records[0]["visible_shape_native_px"])
    green_shape = (native_shape[0] // 2, native_shape[1] // 2)
    locations = allocate_trace_locations(
        sites,
        green_shape,
        int(study["empirical_noise"]["trace_allocation_seed"]),
    )
    roots = [Path(value) for value in census_definition["allowed_read_roots"]]
    source = Path(calibration["source_path"])
    traces = np.empty(
        (pair_count, len(sites), PROFILE_OFFSETS.size), dtype=np.float64
    )
    decoded_inputs: list[dict[str, Any]] = []
    for pair_index in range(pair_count):
        first_record = records[2 * pair_index]
        second_record = records[2 * pair_index + 1]
        first = decode_green(
            source / first_record["file"], roots, registered_iso=float(iso)
        )
        second = decode_green(
            source / second_record["file"], roots, registered_iso=float(iso)
        )
        for decoded, expected in (
            (first, first_record),
            (second, second_record),
        ):
            if decoded.decoded_green_sha256 != expected["decoded_green_sha256"]:
                raise RuntimeError(f"independent decode mismatch for {decoded.path.name}")
            decoded_inputs.append(decoded.input_record())
        difference = (
            first.green_luma_dn.astype(np.float64)
            - second.green_luma_dn.astype(np.float64)
        ) / math.sqrt(2.0)
        for site_index, location in enumerate(locations):
            traces[pair_index, site_index] = extract_empirical_trace(
                difference, location
            )
    allocation = {
        "horizontal_count": sum(
            location.orientation == "horizontal" for location in locations
        ),
        "vertical_count": sum(
            location.orientation == "vertical" for location in locations
        ),
        "unique_horizontal_lines": len(
            {
                location.line
                for location in locations
                if location.orientation == "horizontal"
            }
        ),
        "unique_vertical_lines": len(
            {
                location.line
                for location in locations
                if location.orientation == "vertical"
            }
        ),
    }
    provenance = {
        "iso": iso,
        "pair_count": pair_count,
        "frozen_pair_spatial_sigma_p50_dn": float(
            group["pair_spatial_sigma_p50_dn"]
        ),
        "allocation": allocation,
        "decoded_inputs": decoded_inputs,
    }
    return traces, provenance


def evaluate_side_asymmetry(
    negative: np.ndarray,
    positive: np.ndarray,
    ratios: np.ndarray,
    gate: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    tolerance = float(gate["absolute_side_difference_tolerance"])
    difference = negative - positive
    asymmetric = np.abs(difference) > tolerance
    negative_dominates = difference > tolerance
    positive_dominates = difference < -tolerance
    count = int(difference.size)
    metrics = {
        "absolute_side_difference_tolerance": tolerance,
        "asymmetric_site_count": int(np.count_nonzero(asymmetric)),
        "asymmetric_site_fraction": float(np.mean(asymmetric)),
        "negative_side_dominates_count": int(np.count_nonzero(negative_dominates)),
        "positive_side_dominates_count": int(np.count_nonzero(positive_dominates)),
        "median_side_max_over_mean": nearest_rank(ratios, 0.50),
    }
    minimum_direction_count = math.ceil(
        float(gate["minimum_each_side_dominance_fraction"]) * count
    )
    passed = (
        metrics["asymmetric_site_fraction"]
        >= float(gate["minimum_asymmetric_site_fraction"])
        and metrics["negative_side_dominates_count"] >= minimum_direction_count
        and metrics["positive_side_dominates_count"] >= minimum_direction_count
        and metrics["median_side_max_over_mean"]
        >= float(gate["minimum_median_side_max_over_mean"])
    )
    return metrics, bool(passed)


def empirical_arm(
    name: str,
    role: str,
    traces: np.ndarray,
    provenance: dict[str, Any],
    sites: list[dict[str, Any]],
    checker: ModuleType,
    checker_definition: dict[str, Any],
    include_far_in_output: bool,
    exercise_gate: dict[str, Any],
) -> dict[str, Any]:
    pair_count, site_count, _ = traces.shape
    scale = float(provenance["frozen_pair_spatial_sigma_p50_dn"])
    rows: list[dict[str, Any]] = []
    site_rows: list[dict[str, Any]] = []
    output_reference_identical = 0
    for index, metadata in enumerate(sites):
        step = float(metadata["step_broad_dn"])
        sigma = float(metadata["sigma_temporal_dn"])
        dark = max(100.0, 0.05 * step)
        base = logistic_profile(PROFILE_OFFSETS, dark, step, width=2.0)
        noise = traces[:, index, :] * (sigma / scale)
        sources = base[None, :] + noise
        far_index = index % pair_count
        if include_far_in_output:
            output = np.mean(sources, axis=0)
        else:
            output = np.mean(
                sources[np.arange(pair_count) != far_index], axis=0
            )
        if np.array_equal(output, sources[far_index]):
            output_reference_identical += 1
        patch = edge_patch(dark, step, width=2.0)
        record = checker.SiteProfiles(
            site_id=str(metadata["site_id"]),
            capture_id=str(metadata["capture_id"]),
            offsets_native_px=PROFILE_OFFSETS,
            source_profiles=sources,
            output_profile=output,
            normalization_source_index=far_index,
            far_reference_source_index=far_index,
            sharp_source_index=far_index,
            output_patch=patch,
            sharp_source_patch=patch.copy(),
        )
        row = checker.score_site(record, checker_definition)
        legacy = float(row["v_e_pooled_diagnostic"])
        amended = float(row["v_e"])
        ratio = amended / legacy if legacy > 0.0 else math.inf
        rows.append(row)
        site_rows.append(
            {
                "site_id": str(metadata["site_id"]),
                "capture_id": str(metadata["capture_id"]),
                "v_e_negative_side": float(row["v_e_negative_side"]),
                "v_e_positive_side": float(row["v_e_positive_side"]),
                "v_e_mean_legacy": legacy,
                "v_e_side_max": amended,
                "side_max_over_mean": ratio,
                "affected": bool(row["affected"]),
            }
        )
    legacy_values = np.asarray(
        [item["v_e_mean_legacy"] for item in site_rows], dtype=np.float64
    )
    amended_values = np.asarray(
        [item["v_e_side_max"] for item in site_rows], dtype=np.float64
    )
    ratios = np.asarray(
        [item["side_max_over_mean"] for item in site_rows], dtype=np.float64
    )
    negative_values = np.asarray(
        [item["v_e_negative_side"] for item in site_rows], dtype=np.float64
    )
    positive_values = np.asarray(
        [item["v_e_positive_side"] for item in site_rows], dtype=np.float64
    )
    asymmetry, asymmetry_passed = evaluate_side_asymmetry(
        negative_values, positive_values, ratios, exercise_gate
    )
    affected = int(sum(bool(item["affected"]) for item in site_rows))
    threshold = float(checker_definition["site_failure"]["threshold_max_h_v"])
    new_only = int(
        np.count_nonzero((amended_values > threshold) & (legacy_values <= threshold))
    )
    pooled = {
        "site_count": site_count,
        "median_v_e_mean_legacy": nearest_rank(legacy_values, 0.50),
        "p99_v_e_mean_legacy": nearest_rank(legacy_values, 0.99),
        "median_v_e_side_max": nearest_rank(amended_values, 0.50),
        "p99_v_e_side_max": nearest_rank(amended_values, 0.99),
        "maximum_v_e_side_max": float(np.max(amended_values)),
        "inflation_side_max_over_mean": {
            "median": nearest_rank(ratios, 0.50),
            "p95": nearest_rank(ratios, 0.95),
            "maximum": float(np.max(ratios)),
        },
        "side_asymmetry": asymmetry,
        "zero_legacy_denominator_count": int(np.count_nonzero(legacy_values <= 0.0)),
        "affected_edge_count": affected,
        "affected_edge_rate": affected / site_count,
        "affected_edge_wilson_ucb95": checker.wilson_upper_one_sided(
            affected, site_count
        ),
        "new_only_threshold_crossings": new_only,
    }
    bars = checker_definition["bars"]
    checks = {
        "movable_nonzero": pooled["median_v_e_side_max"] > 0.0,
        "median_v_e": pooled["median_v_e_side_max"]
        <= float(bars["median_v_e_max"]),
        "p99_v_e": pooled["p99_v_e_side_max"] <= float(bars["p99_v_e_max"]),
        "affected_rate": pooled["affected_edge_rate"]
        <= float(bars["affected_point_rate_max"]),
        "affected_wilson": pooled["affected_edge_wilson_ucb95"]
        <= float(bars["affected_wilson_ucb95_max"]),
        "finite_ratio": pooled["zero_legacy_denominator_count"] == 0
        and bool(np.all(np.isfinite(ratios))),
        "monotone_reduction": bool(
            np.all(amended_values >= legacy_values)
            and np.all(amended_values <= 2.0 * legacy_values)
        ),
        "output_differs_from_reference": output_reference_identical == 0,
        "side_asymmetry_exercised": asymmetry_passed,
    }
    per_capture: dict[str, Any] = {}
    for capture_id in sorted({str(site["capture_id"]) for site in sites}):
        capture_rows = [
            item for item in site_rows if item["capture_id"] == capture_id
        ]
        capture_legacy = np.asarray(
            [item["v_e_mean_legacy"] for item in capture_rows]
        )
        capture_amended = np.asarray(
            [item["v_e_side_max"] for item in capture_rows]
        )
        per_capture[capture_id] = {
            "site_count": len(capture_rows),
            "median_v_e_mean_legacy": nearest_rank(capture_legacy, 0.50),
            "p99_v_e_mean_legacy": nearest_rank(capture_legacy, 0.99),
            "median_v_e_side_max": nearest_rank(capture_amended, 0.50),
            "p99_v_e_side_max": nearest_rank(capture_amended, 0.99),
            "affected_edge_count": int(
                sum(bool(item["affected"]) for item in capture_rows)
            ),
        }
    return {
        "name": name,
        "role": role,
        "defect_free": True,
        "far_reference_in_output_mean": include_far_in_output,
        "output_mean_profile_count": pair_count
        if include_far_in_output
        else pair_count - 1,
        "output_reference_identical_count": output_reference_identical,
        "pooled": pooled,
        "per_capture": per_capture,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "site_rows": site_rows,
    }


def main() -> None:
    study, study_hash = load_study_definition()
    census_definition, census_definition_hash = load_definition()
    verify_frozen_dependencies(study, census_definition_hash)
    checker, checker_definition, checker_definition_hash = load_canonical_checker(
        study
    )
    sites = load_frozen_sites(study)

    identity = lambda base, offsets, step: base.copy()
    identity_patch = lambda patch, step: patch.copy()
    rim6 = lambda base, offsets, step: rim_plant(base, offsets, step, 0.06)
    rim6_patch = lambda patch, step: planted_patch(patch, step, rim=0.06)
    opposite6 = lambda base, offsets, step: opposite_sign_rim_plant(
        base, offsets, step, 0.06
    )
    opposite6_patch = lambda patch, step: planted_patch(patch, step, rim=-0.06)
    veil6 = lambda base, offsets, step: veil_plant(base, offsets, step, 0.06)
    veil6_patch = lambda patch, step: planted_patch(patch, step, veil=0.06)
    one_side6 = lambda base, offsets, step: one_sided_far_veil_plant(
        base, offsets, step, 0.06
    )
    combined6 = lambda base, offsets, step: veil_plant(
        rim_plant(base, offsets, step, 0.06), offsets, step, 0.06
    )
    combined6_patch = lambda patch, step: planted_patch(
        patch, step, rim=0.06, veil=0.06
    )
    improved = lambda base, offsets, step: veil_plant(
        rim_plant(base, offsets, step, 0.005), offsets, step, 0.005
    )
    improved_patch = lambda patch, step: planted_patch(
        patch, step, rim=0.005, veil=0.005
    )
    blurred = lambda base, offsets, step: ndimage.gaussian_filter1d(
        base, sigma=5.0, mode="nearest"
    )
    blurred_patch = lambda patch, step: ndimage.gaussian_filter(
        patch, sigma=5.0, mode="nearest"
    )

    arm_specs = [
        ("synthetic_identity_wiring_null", identity, identity_patch, 0.0),
        ("planted_6pct_rim", rim6, rim6_patch, 0.06),
        (
            "planted_6pct_opposite_sign_rim",
            opposite6,
            opposite6_patch,
            0.06,
        ),
        ("planted_6pct_two_sided_veil", veil6, veil6_patch, 0.06),
        (
            "planted_6pct_one_sided_far_veil",
            one_side6,
            identity_patch,
            0.06,
        ),
        (
            "planted_6pct_rim_and_veil",
            combined6,
            combined6_patch,
            0.06,
        ),
        (
            "planted_improvement_0_5pct_rim_and_veil",
            improved,
            improved_patch,
            0.005,
        ),
        ("planted_blur_guard", blurred, blurred_patch, 0.0),
    ]
    synthetic_arms: list[dict[str, Any]] = []
    synthetic_rows: dict[str, list[dict[str, Any]]] = {}
    for name, profile_plant, patch_plant, amplitude in arm_specs:
        summary, rows = arm_summary(
            name,
            sites,
            profile_plant,
            patch_plant,
            checker,
            checker_definition,
            amplitude,
        )
        synthetic_arms.append(summary)
        synthetic_rows[name] = rows
    by_name = {arm["name"]: arm for arm in synthetic_arms}

    raw_identity = real_raw_identity_null(
        sites, census_definition, checker, checker_definition
    )

    empirical_arms: list[dict[str, Any]] = []
    empirical_provenance: list[dict[str, Any]] = []
    configured_arms = study["empirical_noise"]["arms"]
    for iso in (100, 1000):
        traces, provenance = decode_empirical_traces(
            iso, sites, study, census_definition
        )
        empirical_provenance.append(provenance)
        for configured in configured_arms:
            if not str(configured["name"]).startswith(f"iso{iso}_"):
                continue
            empirical_arms.append(
                empirical_arm(
                    str(configured["name"]),
                    str(configured["role"]),
                    traces,
                    provenance,
                    sites,
                    checker,
                    checker_definition,
                    include_far_in_output=(
                        "production_covariance" in configured["name"]
                    ),
                    exercise_gate=study["empirical_noise"]["exercise_gate"],
                )
            )

    one_sided = by_name["planted_6pct_one_sided_far_veil"]
    one_sided_rows = synthetic_rows[one_sided["name"]]
    one_sided_ratios = np.asarray(
        [
            float(row["v_e"]) / float(row["v_e_pooled_diagnostic"])
            for row in one_sided_rows
        ]
    )
    mutations = [
        "planted_6pct_rim",
        "planted_6pct_opposite_sign_rim",
        "planted_6pct_two_sided_veil",
        "planted_6pct_one_sided_far_veil",
        "planted_6pct_rim_and_veil",
        "planted_blur_guard",
    ]
    mutation_kills = {
        name: (
            by_name[name]["detection_rate"] >= 0.95
            if name != "planted_blur_guard"
            else by_name[name]["verdict"] == "FAIL"
        )
        for name in mutations
    }
    improvement = by_name["planted_improvement_0_5pct_rim_and_veil"]
    combined = by_name["planted_6pct_rim_and_veil"]
    empirical_all_pass = all(arm["verdict"] == "PASS" for arm in empirical_arms)
    assertions = {
        "synthetic_identity_passes": by_name[
            "synthetic_identity_wiring_null"
        ]["verdict"]
        == "PASS",
        "raw_identity_is_exactly_zero": raw_identity["pass"],
        "all_empirical_clean_arms_pass": empirical_all_pass,
        "empirical_clean_arms_are_movable": all(
            arm["pooled"]["median_v_e_side_max"] > 0.0 for arm in empirical_arms
        ),
        "empirical_reduction_is_monotone": all(
            arm["checks"]["monotone_reduction"] for arm in empirical_arms
        ),
        "both_rim_signs_killed": mutation_kills["planted_6pct_rim"]
        and mutation_kills["planted_6pct_opposite_sign_rim"],
        "two_sided_veil_killed": mutation_kills[
            "planted_6pct_two_sided_veil"
        ],
        "one_sided_far_veil_killed": mutation_kills[
            "planted_6pct_one_sided_far_veil"
        ],
        "one_sided_ratio_is_two": bool(
            np.all(np.abs(one_sided_ratios - 2.0) <= 1.0e-12)
        ),
        "one_sided_measured_value_matches_analytic": abs(
            float(one_sided["median_v_e"]) - (0.06 * 168.0 / 185.0)
        )
        <= 1.0e-12,
        "combined_defect_killed": mutation_kills[
            "planted_6pct_rim_and_veil"
        ],
        "blur_guard_killed": mutation_kills["planted_blur_guard"],
        "improvement_reduces_h_by_at_least_5pp": (
            float(combined["median_h_e"]) - float(improvement["median_h_e"])
        )
        >= 0.05,
        "improvement_reduces_v_by_at_least_5pp": (
            float(combined["median_v_e"]) - float(improvement["median_v_e"])
        )
        >= 0.05,
        "improvement_control_passes": improvement["verdict"] == "PASS",
    }
    failed = [name for name, passed in assertions.items() if not passed]
    inert_control_results = {
        "synthetic_identity_wiring_null": by_name[
            "synthetic_identity_wiring_null"
        ]["verdict"]
        == "PASS",
        "untouched_raw_identity_wiring_null": raw_identity["pass"],
        **{arm["name"]: arm["verdict"] == "PASS" for arm in empirical_arms},
    }
    regressed = [
        name
        for name, passed in {
            **mutation_kills,
            "synthetic_identity_wiring_null": inert_control_results[
                "synthetic_identity_wiring_null"
            ],
            "untouched_raw_identity_wiring_null": inert_control_results[
                "untouched_raw_identity_wiring_null"
            ],
            "improvement_control": improvement["verdict"] == "PASS",
        }.items()
        if not passed
    ]
    mutated_sites_charged = sum(
        int(by_name[name]["affected_edge_count"])
        if name != "planted_blur_guard"
        else (
            len(sites)
            if by_name[name]["verdict"] == "FAIL"
            else 0
        )
        for name in mutations
    )
    counts = {
        "checks_run": len(assertions),
        "checks_passed": sum(bool(value) for value in assertions.values()),
        "mutation_arms_planted": len(mutations),
        "mutation_arms_killed": sum(bool(value) for value in mutation_kills.values()),
        "mutated_sites_planted": len(mutations) * len(sites),
        "mutated_sites_charged": mutated_sites_charged,
        "inert_control_arms_run": len(inert_control_results),
        "inert_control_arms_survived": sum(
            bool(value) for value in inert_control_results.values()
        ),
        "improvement_control_arms_run": 1,
        "improvement_control_arms_preserved": int(
            improvement["verdict"] == "PASS"
        ),
        "arms_regressed": len(regressed),
        "regressed_arm_names": regressed,
    }
    result = {
        "schema": "m152-m3-side-max-commission-v1",
        "study_definition_sha256": study_hash,
        "census_definition_sha256": census_definition_hash,
        "census_manifest_sha256": sha256_file(MANIFEST_PATH),
        "canonical_checker_sha256": study["authority"][
            "canonical_checker_sha256"
        ],
        "canonical_definition_sha256": checker_definition_hash,
        "historical_m152_v1_hashes_verified": True,
        "candidate_outputs_opened": 0,
        "comparator_outputs_opened": 0,
        "holdout_pixels_opened": 0,
        "non_holdout_dark_inputs_decoded": sum(
            len(item["decoded_inputs"]) for item in empirical_provenance
        ),
        "synthetic_arms": synthetic_arms,
        "untouched_raw_identity_null": raw_identity,
        "empirical_clean_noise": {
            "classification": "REDUCTION_LEVEL_COMMISSIONING_NOT_PRODUCT_SCORE",
            "provenance": empirical_provenance,
            "arms": empirical_arms,
        },
        "one_sided_ratio": {
            "median": nearest_rank(one_sided_ratios, 0.50),
            "minimum": float(np.min(one_sided_ratios)),
            "maximum": float(np.max(one_sided_ratios)),
            "analytic": 2.0,
        },
        "assertions": assertions,
        "failed_assertions": failed,
        "commissioning_counts": counts,
        "verdict": (
            "SIDE_MAX_REDUCTION_COMMISSIONING_PASS"
            if not failed
            else "NOT_ADMITTED_COMMISSIONING_FAILED"
        ),
        "m3_axis_verdict": "UNMEASURED_COMPARATOR_QUALIFICATION",
        "scope_limit": study["empirical_noise"]["scope_limit"],
    }
    write_json(OUT_PATH, result)
    digest = sha256_file(OUT_PATH)
    OUT_PATH.with_suffix(".sha256").write_text(
        f"{digest}  {OUT_PATH.name}\n", encoding="ascii"
    )

    for arm in empirical_arms:
        pooled = arm["pooled"]
        inflation = pooled["inflation_side_max_over_mean"]
        print(
            f"{arm['name']}: legacy50={pooled['median_v_e_mean_legacy']:.9f} "
            f"side50={pooled['median_v_e_side_max']:.9f} "
            f"side99={pooled['p99_v_e_side_max']:.9f} "
            f"inflation50={inflation['median']:.6f} "
            f"inflation95={inflation['p95']:.6f} "
            f"inflation_max={inflation['maximum']:.6f} "
            f"affected={pooled['affected_edge_count']}/{pooled['site_count']}"
        )
    print(
        "one_sided_far_veil: "
        f"legacy={one_sided['median_v_e_mean_legacy']:.9f} "
        f"side_max={one_sided['median_v_e']:.9f} "
        f"ratio={nearest_rank(one_sided_ratios, 0.50):.12f}"
    )
    print(
        "counts: "
        f"checks={counts['checks_passed']}/{counts['checks_run']} "
        f"mutations={counts['mutation_arms_killed']}/"
        f"{counts['mutation_arms_planted']} "
        f"inert={counts['inert_control_arms_survived']}/"
        f"{counts['inert_control_arms_run']} "
        f"improvement={counts['improvement_control_arms_preserved']}/1 "
        f"regressed={counts['arms_regressed']}"
    )
    print(f"commission_sha256={digest}")
    print(f"verdict={result['verdict']}")
    if failed:
        print("failed=" + ",".join(failed))
        raise SystemExit(3)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
