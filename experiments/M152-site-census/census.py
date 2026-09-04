"""Build the frozen M152 input-only M3/M4 site manifest.

There are three deliberately separate phases:

* ``calibrate-noise`` reads only the registered non-holdout dark control;
* ``probe`` runs only captures explicitly marked non-holdout; and
* ``run`` unlocks protected inputs only when the caller supplies the exact
  frozen definition SHA-256.

No command accepts an output image path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage

from census_common import (
    DEFINITION_PATH,
    HERE,
    REPO_ROOT,
    band_rms_tiles,
    bilinear_profile,
    canonical_json,
    decode_green,
    deterministic_frame_indices,
    image_blocks,
    load_definition,
    nearest_rank,
    sha256_bytes,
    sha256_file,
    temporal_sigma_green_luma_dn,
    tree_summary,
)


OUT = HERE / "out"
NOISE_PATH = OUT / "noise-calibration.json"
MANIFEST_PATH = OUT / "census-manifest.json"
READONLY_PATH = OUT / "readonly-verification.json"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    )
    path.write_text(encoded + "\n", encoding="ascii")


def allowed_roots(definition: dict[str, Any]) -> list[Path]:
    return [Path(value).resolve() for value in definition["allowed_read_roots"]]


def inventory_path(definition: dict[str, Any], key: str) -> Path:
    return REPO_ROOT / definition["inventory"][key]


def load_inventory(definition: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    capture_path = inventory_path(definition, "capture_manifest")
    holdout_path = inventory_path(definition, "holdout_register")
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    holdout = json.loads(holdout_path.read_text(encoding="utf-8"))
    return capture, holdout


def validate_evidence_classes(
    definition: dict[str, Any], holdout: dict[str, Any]
) -> None:
    clean = {
        row["stack_id"]: row["evidence_class"]
        for row in holdout["clean_registered_holdout_rows"]
    }
    explicit_not = {
        row["stack_id"]: row["evidence_class"]
        for row in holdout["explicit_not_holdout_rows"]
    }
    groups = [
        definition["m3"]["captures"],
        definition["m4"]["scored_flat_captures"],
        definition["m4"]["commissioning_flat_captures"],
        definition["m4"]["scored_edge_captures"],
    ]
    for capture in (item for group in groups for item in group):
        stack_id = capture["stack_id"]
        evidence = capture["evidence_class"]
        if evidence.startswith("HOLDOUT_"):
            if stack_id not in clean:
                raise RuntimeError(
                    f"{stack_id}: definition says holdout but M141 register does not"
                )
        elif evidence.endswith("_NOT_HOLDOUT"):
            if stack_id not in explicit_not:
                raise RuntimeError(
                    f"{stack_id}: definition says not-holdout but M141 register does not"
                )
        else:
            raise RuntimeError(
                f"{stack_id}: unsupported or indeterminate evidence class {evidence}"
            )


def capture_files(
    capture: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
) -> tuple[list[Path], dict[str, Any]]:
    stack_id = capture["stack_id"]
    if stack_id not in inventory_by_id:
        raise RuntimeError(f"capture is absent from M141 inventory: {stack_id}")
    inventory = inventory_by_id[stack_id]
    path = Path(capture["path"]).resolve()
    if path != Path(inventory["path"]).resolve():
        raise RuntimeError(f"path differs from M141 inventory for {stack_id}")
    files = sorted(path.glob("*.ARW"), key=lambda value: value.name)
    if len(files) != int(inventory["frame_count"]):
        raise RuntimeError(
            f"{stack_id}: found {len(files)} ARWs, inventory says "
            f"{inventory['frame_count']}"
        )
    if not bool(inventory["capture_contiguous"]):
        raise RuntimeError(f"{stack_id}: inventory does not establish continuity")
    return files, inventory


def noise_result_hash(value: dict[str, Any]) -> str:
    without_hash = {key: item for key, item in value.items() if key != "content_sha256"}
    return sha256_bytes(canonical_json(without_hash).encode("ascii"))


def calibrate_noise(
    definition: dict[str, Any], definition_sha256: str
) -> dict[str, Any]:
    roots = allowed_roots(definition)
    noise = definition["noise"]
    source = Path(noise["calibration_capture"]).resolve()
    model = noise["temporal_model"]
    band = noise["flat_band"]
    size = int(band["tile_size_green_px"])
    groups: list[dict[str, Any]] = []

    for group in noise["calibration_groups"]:
        all_files = sorted(source.glob("*.ARW"), key=lambda value: value.name)
        selected = [
            path
            for path in all_files
            if group["first_file"] <= path.name <= group["last_file"]
        ]
        if len(selected) != int(group["frame_count"]):
            raise RuntimeError(
                f"dark group ISO {group['iso']}: expected {group['frame_count']} "
                f"files, got {len(selected)}"
            )
        if len(selected) % 2:
            raise RuntimeError("dark calibration requires an even frame count")

        pair_band_values: list[np.ndarray] = []
        pair_spatial_sigmas: list[float] = []
        input_records: list[dict[str, Any]] = []
        for pair_start in range(0, len(selected), 2):
            expected_iso = float(group["iso"])
            first = decode_green(selected[pair_start], roots, expected_iso)
            second = decode_green(selected[pair_start + 1], roots, expected_iso)
            if first.green_luma_dn.shape != second.green_luma_dn.shape:
                raise RuntimeError("dark pair decoded to different shapes")
            difference = (
                first.green_luma_dn.astype(np.float64)
                - second.green_luma_dn.astype(np.float64)
            ) / math.sqrt(2.0)
            blocks, ny, nx = image_blocks(difference.astype(np.float32), size)
            yy, xx = np.divmod(np.arange(ny * nx), nx)
            interior = (yy > 0) & (yy < ny - 1) & (xx > 0) & (xx < nx - 1)
            band_values = band_rms_tiles(
                blocks[interior],
                sample_pitch_native_px=2.0,
                low=float(band["low_frequency_cycles_per_native_px"]),
                high=float(band["high_frequency_cycles_per_native_px"]),
            )
            pair_band_values.append(band_values)
            # Median per-tile spatial RMS is robust to the known hot-pixel tail.
            tile_rms = np.sqrt(np.mean(blocks[interior] ** 2, axis=(1, 2)))
            pair_spatial_sigmas.append(float(np.median(tile_rms)))
            input_records.extend([first.input_record(), second.input_record()])

        all_band = np.concatenate(pair_band_values)
        p99 = nearest_rank(all_band, 0.99)
        model_dark_sigma = float(
            temporal_sigma_green_luma_dn(0.0, float(group["iso"]), model)
        )
        groups.append(
            {
                "iso": int(group["iso"]),
                "exposure_seconds": float(group["exposure_seconds"]),
                "frame_count": len(selected),
                "pair_count": len(selected) // 2,
                "tile_observation_count": int(all_band.size),
                "band_rms_p50_dn": nearest_rank(all_band, 0.50),
                "band_rms_p99_dn": p99,
                "pair_spatial_sigma_p50_dn": nearest_rank(
                    np.asarray(pair_spatial_sigmas), 0.50
                ),
                "model_dark_sigma_green_luma_dn": model_dark_sigma,
                "band_p99_over_model_dark_sigma": p99 / model_dark_sigma,
                "inputs": input_records,
            }
        )

    # Rule 32 independent-decode sentinel: the same source is decoded in a new
    # LibRaw context and must reproduce the stored green-luma bytes exactly.
    sentinel_path = source / noise["calibration_groups"][0]["first_file"]
    sentinel_iso = float(noise["calibration_groups"][0]["iso"])
    sentinel_a = decode_green(sentinel_path, roots, sentinel_iso)
    sentinel_b = decode_green(sentinel_path, roots, sentinel_iso)
    sentinel_equal = (
        sentinel_a.decoded_green_sha256 == sentinel_b.decoded_green_sha256
    )
    if not sentinel_equal:
        raise RuntimeError("independent RAW decode sentinel was not byte-identical")

    result: dict[str, Any] = {
        "schema": "m152-noise-calibration-v1",
        "definition_sha256": definition_sha256,
        "definition_path": str(DEFINITION_PATH),
        "source_class": "CONTROL_NOT_HOLDOUT",
        "source_path": str(source),
        "groups": groups,
        "frozen_band_p99_over_model_dark_sigma": max(
            float(group["band_p99_over_model_dark_sigma"]) for group in groups
        ),
        "factor_rule": "maximum of the ISO-specific measured ratios",
        "independent_decode_sentinel": {
            "file": sentinel_path.name,
            "first_sha256": sentinel_a.decoded_green_sha256,
            "second_sha256": sentinel_b.decoded_green_sha256,
            "byte_identical": sentinel_equal,
        },
        "numeric_status": "MEASURED",
    }
    result["content_sha256"] = noise_result_hash(result)
    write_json(NOISE_PATH, result)
    print(
        "noise calibration: factor="
        f"{result['frozen_band_p99_over_model_dark_sigma']:.9f} "
        f"sha256={result['content_sha256']}"
    )
    return result


def load_noise(definition_sha256: str) -> dict[str, Any]:
    if not NOISE_PATH.is_file():
        raise RuntimeError("run calibrate-noise before a census")
    result = json.loads(NOISE_PATH.read_text(encoding="ascii"))
    if result.get("schema") != "m152-noise-calibration-v1":
        raise RuntimeError("unexpected noise calibration schema")
    if result.get("definition_sha256") != definition_sha256:
        raise RuntimeError("noise calibration was made under another definition")
    if noise_result_hash(result) != result.get("content_sha256"):
        raise RuntimeError("noise calibration content hash does not verify")
    return result


def robust_mad(values: np.ndarray) -> float:
    centre = float(np.median(values))
    return 1.4826 * float(np.median(np.abs(values - centre)))


def evaluate_edge_candidate(
    image: np.ndarray,
    y_green: float,
    x_green: float,
    normal_y: float,
    normal_x: float,
    reach_native_px: int,
    iso: float,
    model: dict[str, Any],
    selector: dict[str, Any],
    source_record: dict[str, Any],
    source_frame_index: int,
) -> tuple[dict[str, Any] | None, str]:
    try:
        offsets, profile = bilinear_profile(
            image,
            y_green,
            x_green,
            normal_y,
            normal_x,
            reach_native_px,
        )
    except ValueError:
        return None, "footprint_out_of_bounds"

    narrow_bounds = selector["narrow_plateaus_native_px"]
    narrow_left = (offsets >= float(narrow_bounds[0][0])) & (
        offsets <= float(narrow_bounds[0][1])
    )
    narrow_right = (offsets >= float(narrow_bounds[1][0])) & (
        offsets <= float(narrow_bounds[1][1])
    )
    if not np.any(narrow_left) or not np.any(narrow_right):
        return None, "narrow_plateau_missing"
    left_n = float(np.median(profile[narrow_left]))
    right_n = float(np.median(profile[narrow_right]))
    if right_n < left_n:
        profile = profile[::-1]
        normal_y = -normal_y
        normal_x = -normal_x
        left_n, right_n = right_n, left_n

    step_narrow = right_n - left_n
    mean_signal = max(0.0, 0.5 * (left_n + right_n))
    sigma = float(temporal_sigma_green_luma_dn(mean_signal, iso, model))
    if not np.isfinite(step_narrow) or step_narrow < float(
        selector["minimum_step_sigma"]
    ) * sigma:
        return None, "step_below_10_sigma"
    if max(
        robust_mad(profile[narrow_left]), robust_mad(profile[narrow_right])
    ) > float(selector["maximum_narrow_plateau_mad_fraction"]) * step_narrow:
        return None, "narrow_plateau_not_flat"

    centre = (offsets >= -int(selector["central_crossing_half_width_native_px"])) & (
        offsets <= int(selector["central_crossing_half_width_native_px"])
    )
    normalized = (profile - left_n) / step_narrow
    centre_values = normalized[centre]
    centre_offsets = offsets[centre]
    above = centre_values >= 0.5
    transitions = np.flatnonzero(above[1:] != above[:-1])
    if len(transitions) != 1 or not (not above[0] and above[-1]):
        return None, "not_one_dark_to_bright_crossing"
    crossing = int(transitions[0])
    z0 = float(centre_values[crossing])
    z1 = float(centre_values[crossing + 1])
    if z1 == z0:
        return None, "degenerate_midpoint_crossing"
    midpoint = float(
        centre_offsets[crossing]
        + (0.5 - z0)
        * (centre_offsets[crossing + 1] - centre_offsets[crossing])
        / (z1 - z0)
    )
    if abs(midpoint) > float(selector["maximum_midpoint_offset_native_px"]):
        return None, "midpoint_too_far_from_candidate"
    reverse = float(np.sum(np.maximum(-np.diff(centre_values), 0.0)))
    if reverse > float(selector["maximum_reverse_variation_fraction"]):
        return None, "central_profile_not_monotone_enough"

    broad_step: float | None = None
    broad_cnr: float | None = None
    broad_bounds = selector["broad_plateaus_native_px"]
    broad_reach = max(abs(float(value)) for pair in broad_bounds for value in pair)
    if reach_native_px >= broad_reach:
        broad_left = (offsets >= float(broad_bounds[0][0])) & (
            offsets <= float(broad_bounds[0][1])
        )
        broad_right = (offsets >= float(broad_bounds[1][0])) & (
            offsets <= float(broad_bounds[1][1])
        )
        left_b = float(np.median(profile[broad_left]))
        right_b = float(np.median(profile[broad_right]))
        broad_step = right_b - left_b
        if broad_step < float(selector["minimum_step_sigma"]) * sigma:
            return None, "broad_step_below_10_sigma"
        disagreement = abs(broad_step - step_narrow) / step_narrow
        if disagreement > float(
            selector["maximum_narrow_broad_step_disagreement_fraction"]
        ):
            return None, "narrow_broad_step_disagree"
        if max(
            robust_mad(profile[broad_left]), robust_mad(profile[broad_right])
        ) > float(selector["maximum_broad_plateau_mad_fraction"]) * broad_step:
            return None, "broad_plateau_not_flat"
        broad_cnr = broad_step / sigma

    narrow_cnr = step_narrow / sigma
    quality = min(narrow_cnr, broad_cnr if broad_cnr is not None else narrow_cnr)
    return (
        {
            "x_native_px": float(2.0 * x_green + 0.5),
            "y_native_px": float(2.0 * y_green + 0.5),
            "normal_x": float(normal_x),
            "normal_y": float(normal_y),
            "source_frame_index": int(source_frame_index),
            "source_file": source_record["file"],
            "source_decoded_green_sha256": source_record[
                "decoded_green_sha256"
            ],
            "step_narrow_dn": step_narrow,
            "step_broad_dn": broad_step,
            "sigma_temporal_dn": sigma,
            "narrow_step_sigma": narrow_cnr,
            "broad_step_sigma": broad_cnr,
            "midpoint_offset_native_px": midpoint,
            "reverse_variation_fraction": reverse,
            "reach_native_px": int(reach_native_px),
            "quality": quality,
        },
        "eligible",
    )


def edge_candidates_from_frame(
    decoded: Any,
    source_frame_index: int,
    reach_native_px: int,
    definition: dict[str, Any],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    selector = definition["edge_selector"]
    model = definition["noise"]["temporal_model"]
    image = ndimage.gaussian_filter(
        decoded.green_luma_dn,
        sigma=float(selector["discovery_blur_sigma_green_px"]),
        mode="reflect",
    )
    gx = ndimage.sobel(image, axis=1, mode="reflect") / np.float32(8.0)
    gy = ndimage.sobel(image, axis=0, mode="reflect") / np.float32(8.0)
    magnitude = np.hypot(gx, gy)

    grid = int(selector["candidate_grid_native_px"]) // 2
    margin = int(math.ceil(reach_native_px / 2.0)) + 2
    usable_h = ((image.shape[0] - 2 * margin) // grid) * grid
    usable_w = ((image.shape[1] - 2 * margin) // grid) * grid
    if usable_h <= 0 or usable_w <= 0:
        return [], Counter({"capture_too_small_for_reach": 1})
    region = magnitude[margin : margin + usable_h, margin : margin + usable_w]
    ny = usable_h // grid
    nx = usable_w // grid
    blocks = (
        region.reshape(ny, grid, nx, grid)
        .transpose(0, 2, 1, 3)
        .reshape(ny * nx, grid * grid)
    )
    local_index = np.argmax(blocks, axis=1)
    block_y, block_x = np.divmod(np.arange(ny * nx), nx)
    local_y, local_x = np.divmod(local_index, grid)
    ys = margin + block_y * grid + local_y
    xs = margin + block_x * grid + local_x
    strengths = magnitude[ys, xs]
    order = np.lexsort((xs, ys, -strengths))
    order = order[: int(selector["maximum_candidates_per_discovery_frame"])]

    accepted: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    source_record = decoded.input_record()
    for index in order:
        y = int(ys[index])
        x = int(xs[index])
        strength = float(strengths[index])
        if not np.isfinite(strength) or strength <= 0.0:
            reasons["nonpositive_gradient"] += 1
            continue
        normal_x = float(gx[y, x] / strength)
        normal_y = float(gy[y, x] / strength)
        site, reason = evaluate_edge_candidate(
            image=image,
            y_green=float(y),
            x_green=float(x),
            normal_y=normal_y,
            normal_x=normal_x,
            reach_native_px=reach_native_px,
            iso=decoded.iso,
            model=model,
            selector=selector,
            source_record=source_record,
            source_frame_index=source_frame_index,
        )
        reasons[reason] += 1
        if site is not None:
            accepted.append(site)
    return accepted, reasons


def deduplicate_sites(
    sites: list[dict[str, Any]], minimum_spacing_native_px: float
) -> list[dict[str, Any]]:
    ordered = sorted(
        sites,
        key=lambda site: (
            -float(site["quality"]),
            str(site["source_file"]),
            float(site["y_native_px"]),
            float(site["x_native_px"]),
        ),
    )
    buckets: dict[tuple[int, int], list[dict[str, Any]]] = {}
    accepted: list[dict[str, Any]] = []
    spacing2 = minimum_spacing_native_px**2
    for site in ordered:
        bx = int(math.floor(float(site["x_native_px"]) / minimum_spacing_native_px))
        by = int(math.floor(float(site["y_native_px"]) / minimum_spacing_native_px))
        too_close = False
        for nearby_y in range(by - 1, by + 2):
            for nearby_x in range(bx - 1, bx + 2):
                for other in buckets.get((nearby_x, nearby_y), []):
                    dx = float(site["x_native_px"]) - float(other["x_native_px"])
                    dy = float(site["y_native_px"]) - float(other["y_native_px"])
                    if dx * dx + dy * dy < spacing2:
                        too_close = True
                        break
                if too_close:
                    break
            if too_close:
                break
        if too_close:
            continue
        site = dict(site)
        site["quality_rank"] = len(accepted) + 1
        accepted.append(site)
        buckets.setdefault((bx, by), []).append(site)
    return accepted


def census_edge_capture(
    capture: dict[str, Any],
    reach_native_px: int,
    definition: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    files, inventory = capture_files(capture, inventory_by_id)
    requested = int(
        definition["common_input"]["frame_sampling"]["edge_discovery_count"]
    )
    indices = deterministic_frame_indices(len(files), requested)
    roots = allowed_roots(definition)
    iso_rows = inventory["settings"]["iso"]
    if len(iso_rows) != 1:
        raise RuntimeError(f"{capture['capture_id']}: edge stack has varying ISO")
    registered_iso = float(iso_rows[0]["value"])
    candidates: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    inputs: list[dict[str, Any]] = []
    for index in indices:
        decoded = decode_green(files[index], roots, registered_iso)
        frame_sites, frame_reasons = edge_candidates_from_frame(
            decoded, index, reach_native_px, definition
        )
        candidates.extend(frame_sites)
        reasons.update(frame_reasons)
        inputs.append(decoded.input_record())
        print(
            f"edge {capture['capture_id']}: frame {index + 1}/{len(files)} "
            f"eligible={len(frame_sites)}"
        )
    unique = deduplicate_sites(
        candidates,
        float(definition["edge_selector"]["minimum_site_spacing_native_px"]),
    )
    return {
        "capture_id": capture["capture_id"],
        "stack_id": capture["stack_id"],
        "path": capture["path"],
        "evidence_class": capture["evidence_class"],
        "inventory_frame_count": int(inventory["frame_count"]),
        "capture_contiguous": bool(inventory["capture_contiguous"]),
        "sampled_frame_indices_zero_based": indices,
        "sampled_frame_count": len(indices),
        "required_reach_native_px": reach_native_px,
        "pre_dedup_eligible_count": len(candidates),
        "eligible_site_count": len(unique),
        "rejection_counts": dict(sorted(reasons.items())),
        "decoded_inputs": inputs,
        "eligible_sites_quality_order": unique,
    }


def flat_grid_indices(
    ny: int, nx: int, margin_blocks: int
) -> np.ndarray:
    yy, xx = np.divmod(np.arange(ny * nx), nx)
    return np.flatnonzero(
        (yy >= margin_blocks)
        & (yy < ny - margin_blocks)
        & (xx >= margin_blocks)
        & (xx < nx - margin_blocks)
    )


def census_flat_capture(
    capture: dict[str, Any],
    definition: dict[str, Any],
    noise_calibration: dict[str, Any],
    inventory_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    files, inventory = capture_files(capture, inventory_by_id)
    roots = allowed_roots(definition)
    flat = definition["m4"]["flat_site_grid"]
    band = definition["noise"]["flat_band"]
    model = definition["noise"]["temporal_model"]
    size = int(band["tile_size_green_px"])
    margin_blocks = int(flat["outer_margin_native_px"]) // int(
        band["tile_size_native_px"]
    )
    factor = float(noise_calibration["frozen_band_p99_over_model_dark_sigma"])
    iso_rows = inventory["settings"]["iso"]
    if len(iso_rows) != 1:
        raise RuntimeError(f"{capture['capture_id']}: flat stack has varying ISO")
    registered_iso = float(iso_rows[0]["value"])

    alive: np.ndarray | None = None
    worst_ratio: np.ndarray | None = None
    worst_frame: np.ndarray | None = None
    ny = nx = 0
    input_records: list[dict[str, Any]] = []
    processed_frames = 0
    stopped_when_empty = False
    usable_range_dn: float | None = None
    capture_iso: float | None = None
    initial_candidate_count = 0
    survivor_trajectory: list[dict[str, Any]] = []
    first_failure_counts: Counter[str] = Counter()

    for frame_index, path in enumerate(files):
        decoded = decode_green(path, roots, registered_iso)
        processed_frames += 1
        input_records.append(decoded.input_record())
        blocks, frame_ny, frame_nx = image_blocks(decoded.green_luma_dn, size)
        if alive is None:
            ny, nx = frame_ny, frame_nx
            alive = np.zeros(ny * nx, dtype=bool)
            alive[flat_grid_indices(ny, nx, margin_blocks)] = True
            initial_candidate_count = int(np.count_nonzero(alive))
            worst_ratio = np.full(ny * nx, -np.inf, dtype=np.float64)
            worst_frame = np.full(ny * nx, -1, dtype=np.int32)
            usable_range_dn = decoded.usable_range_dn
            capture_iso = decoded.iso
        if frame_ny != ny or frame_nx != nx:
            raise RuntimeError(f"{capture['capture_id']}: decoded shape changed")
        if decoded.iso != capture_iso:
            raise RuntimeError(
                f"{capture['capture_id']}: varying ISO is not an admissible flat stack"
            )
        assert alive is not None and worst_ratio is not None and worst_frame is not None
        indices = np.flatnonzero(alive)
        if indices.size == 0:
            stopped_when_empty = True
            break

        selected = blocks[indices]
        medians = np.median(selected, axis=(1, 2))
        sigma = np.asarray(
            temporal_sigma_green_luma_dn(medians, decoded.iso, model)
        )
        threshold = factor * sigma
        measured = band_rms_tiles(
            selected,
            sample_pitch_native_px=2.0,
            low=float(band["low_frequency_cycles_per_native_px"]),
            high=float(band["high_frequency_cycles_per_native_px"]),
        )
        ratio = measured / threshold
        low_fraction = np.mean(selected <= 0.0, axis=(1, 2))
        high_fraction = np.mean(
            selected >= decoded.usable_range_dn - 1.0, axis=(1, 2)
        )
        signal_ok = medians >= float(flat["minimum_signal_sigma"]) * np.asarray(
            temporal_sigma_green_luma_dn(medians, decoded.iso, model)
        )
        valid = (
            (ratio < 1.0)
            & (low_fraction <= float(flat["maximum_low_rail_fraction"]))
            & (high_fraction <= float(flat["maximum_high_rail_fraction"]))
            & signal_ok
        )
        failing = ~valid
        if np.any(failing):
            fail_band = ratio >= 1.0
            fail_low = low_fraction > float(flat["maximum_low_rail_fraction"])
            fail_high = high_fraction > float(flat["maximum_high_rail_fraction"])
            fail_signal = ~signal_ok
            # A site is charged once, on the first frame where it fails.  The
            # priority is fixed only to make the diagnostic counts additive.
            assigned = np.zeros(len(indices), dtype=bool)
            for label, mask in (
                ("band_at_or_above_temporal_p99", fail_band),
                ("low_rail_fraction", fail_low),
                ("high_rail_fraction", fail_high),
                ("signal_below_10_sigma", fail_signal),
            ):
                chosen = failing & mask & ~assigned
                first_failure_counts[label] += int(np.count_nonzero(chosen))
                assigned |= chosen
        improved = ratio > worst_ratio[indices]
        worst_ratio[indices[improved]] = ratio[improved]
        worst_frame[indices[improved]] = frame_index
        alive[indices[~valid]] = False
        survivor_trajectory.append(
            {
                "frame_index_zero_based": frame_index,
                "file": path.name,
                "survivors": int(np.count_nonzero(alive)),
            }
        )
        print(
            f"flat {capture['capture_id']}: frame {frame_index + 1}/{len(files)} "
            f"survivors={int(np.count_nonzero(alive))}"
        )

    assert alive is not None and worst_ratio is not None and worst_frame is not None
    assert usable_range_dn is not None and capture_iso is not None
    sites: list[dict[str, Any]] = []
    for block_index in np.flatnonzero(alive):
        block_y, block_x = divmod(int(block_index), nx)
        sites.append(
            {
                "x_native_px": block_x * int(band["tile_size_native_px"])
                + int(band["tile_size_native_px"]) / 2.0
                - 0.5,
                "y_native_px": block_y * int(band["tile_size_native_px"])
                + int(band["tile_size_native_px"]) / 2.0
                - 0.5,
                "tile_size_native_px": int(band["tile_size_native_px"]),
                "maximum_band_over_noise_p99": float(worst_ratio[block_index]),
                "worst_frame_index_zero_based": int(worst_frame[block_index]),
            }
        )
    sites.sort(
        key=lambda site: (
            float(site["maximum_band_over_noise_p99"]),
            float(site["y_native_px"]),
            float(site["x_native_px"]),
        )
    )
    noise_floor = factor * float(
        temporal_sigma_green_luma_dn(0.0, capture_iso, model)
    ) / usable_range_dn
    return {
        "capture_id": capture["capture_id"],
        "stack_id": capture["stack_id"],
        "path": capture["path"],
        "evidence_class": capture["evidence_class"],
        "inventory_frame_count": int(inventory["frame_count"]),
        "capture_contiguous": bool(inventory["capture_contiguous"]),
        "processed_frame_count": processed_frames,
        "all_frames_required": True,
        "all_frames_evaluated": processed_frames == len(files),
        "logical_short_circuit_after_zero_survivors": stopped_when_empty,
        "initial_candidate_count": initial_candidate_count,
        "survivor_trajectory": survivor_trajectory,
        "first_failure_counts": dict(sorted(first_failure_counts.items())),
        "eligible_site_count": len(sites),
        "noise_floor_normalized_linear": noise_floor,
        "frozen_band_p99_over_model_dark_sigma": factor,
        "decoded_inputs": input_records,
        "eligible_sites_quality_order": sites,
    }


def select_m3(
    captures: list[dict[str, Any]], definition: dict[str, Any]
) -> dict[str, Any]:
    minimum_each = int(definition["m3"]["minimum_edges_per_capture"])
    minimum_total = int(definition["m3"]["minimum_edges_overall"])
    shortages = {
        capture["capture_id"]: max(
            0, minimum_each - int(capture["eligible_site_count"])
        )
        for capture in captures
        if int(capture["eligible_site_count"]) < minimum_each
    }
    selected: list[dict[str, Any]] = []
    positions = [0] * len(captures)
    for capture_index, capture in enumerate(captures):
        take = min(minimum_each, int(capture["eligible_site_count"]))
        for site in capture["eligible_sites_quality_order"][:take]:
            chosen = dict(site)
            chosen["capture_id"] = capture["capture_id"]
            selected.append(chosen)
        positions[capture_index] = take

    while len(selected) < minimum_total:
        progress = False
        for capture_index, capture in enumerate(captures):
            position = positions[capture_index]
            sites = capture["eligible_sites_quality_order"]
            if position < len(sites):
                chosen = dict(sites[position])
                chosen["capture_id"] = capture["capture_id"]
                selected.append(chosen)
                positions[capture_index] += 1
                progress = True
                if len(selected) == minimum_total:
                    break
        if not progress:
            break

    selected.sort(
        key=lambda site: (
            str(site["capture_id"]),
            float(site["y_native_px"]),
            float(site["x_native_px"]),
        )
    )
    for index, site in enumerate(selected, start=1):
        site["site_id"] = f"M3-{index:04d}"
    total_eligible = sum(int(capture["eligible_site_count"]) for capture in captures)
    sufficient = not shortages and total_eligible >= minimum_total
    return {
        "verdict": "SUFFICIENT" if sufficient else "NEEDS_NEW_CAPTURE",
        "eligible_edges_overall": total_eligible,
        "minimum_edges_overall": minimum_total,
        "per_capture_minimum": minimum_each,
        "per_capture_shortfalls": shortages,
        "selected_site_count": len(selected),
        "selected_sites": selected,
    }


def select_quota_sites(
    captures: list[dict[str, Any]], category: str
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    selected: list[dict[str, Any]] = []
    shortages: dict[str, int] = {}
    for capture in captures:
        quota = int(capture["quota"])
        available = int(capture["eligible_site_count"])
        if available < quota:
            shortages[capture["capture_id"]] = quota - available
        for site in capture["eligible_sites_quality_order"][:quota]:
            chosen = dict(site)
            chosen["capture_id"] = capture["capture_id"]
            chosen["category"] = category
            selected.append(chosen)
    return selected, shortages


def select_m4(
    flats: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    commissioning: list[dict[str, Any]],
    definition: dict[str, Any],
) -> dict[str, Any]:
    selected_flat, flat_short = select_quota_sites(flats, "flat")
    selected_edge, edge_short = select_quota_sites(edges, "edge")
    selected = selected_flat + selected_edge
    selected.sort(
        key=lambda site: (
            str(site["category"]),
            str(site["capture_id"]),
            float(site["y_native_px"]),
            float(site["x_native_px"]),
        )
    )
    for index, site in enumerate(selected, start=1):
        site["site_id"] = f"M4-{index:04d}"
    required = int(definition["m4"]["population_mix"]["scored_total"])
    sufficient = not flat_short and not edge_short and len(selected) == required
    commission_short = {
        capture["capture_id"]: max(
            0, int(capture["quota"]) - int(capture["eligible_site_count"])
        )
        for capture in commissioning
        if int(capture["eligible_site_count"]) < int(capture["quota"])
    }
    return {
        "verdict": (
            "SUFFICIENT_CONDITIONAL_ON_OWNER_ADOPTING_FROZEN_MIX"
            if sufficient
            else "NEEDS_NEW_CAPTURE"
        ),
        "scorecard_population_caveat": definition["m4"]["scorecard_status"],
        "eligible_flat_sites_overall": sum(
            int(capture["eligible_site_count"]) for capture in flats
        ),
        "eligible_edge_sites_overall": sum(
            int(capture["eligible_site_count"]) for capture in edges
        ),
        "selected_flat_site_count": len(selected_flat),
        "selected_edge_site_count": len(selected_edge),
        "selected_site_count": len(selected),
        "required_site_count": required,
        "flat_shortfalls": flat_short,
        "edge_shortfalls": edge_short,
        "commissioning_flat_shortfalls": commission_short,
        "selected_sites": selected,
    }


def capture_with_quota(
    specification: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    result = dict(result)
    result["quota"] = int(specification["quota"])
    return result


def run_census(
    definition: dict[str, Any],
    definition_sha256: str,
    confirmation: str,
) -> dict[str, Any]:
    if confirmation != definition_sha256:
        raise RuntimeError(
            "holdout census locked: pass the exact definition SHA-256 shown by "
            "the definition-hash command"
        )
    noise_calibration = load_noise(definition_sha256)
    capture_inventory, holdout_register = load_inventory(definition)
    validate_evidence_classes(definition, holdout_register)
    inventory_by_id = {
        stack["stack_id"]: stack for stack in capture_inventory["stacks"]
    }
    roots = allowed_roots(definition)
    before = {str(root): tree_summary(root) for root in roots}

    m3_captures = [
        census_edge_capture(
            capture,
            int(definition["m3"]["required_veil_reach_native_px"]),
            definition,
            inventory_by_id,
        )
        for capture in definition["m3"]["captures"]
    ]
    m3_selection = select_m3(m3_captures, definition)

    m4_flat_captures = [
        capture_with_quota(
            capture,
            census_flat_capture(
                capture, definition, noise_calibration, inventory_by_id
            ),
        )
        for capture in definition["m4"]["scored_flat_captures"]
    ]
    m4_commissioning = [
        capture_with_quota(
            capture,
            census_flat_capture(
                capture, definition, noise_calibration, inventory_by_id
            ),
        )
        for capture in definition["m4"]["commissioning_flat_captures"]
    ]
    m4_edge_captures = [
        capture_with_quota(
            capture,
            census_edge_capture(
                capture,
                int(definition["m4"]["edge_reach_native_px"]),
                definition,
                inventory_by_id,
            ),
        )
        for capture in definition["m4"]["scored_edge_captures"]
    ]
    m4_selection = select_m4(
        m4_flat_captures, m4_edge_captures, m4_commissioning, definition
    )

    after = {str(root): tree_summary(root) for root in roots}
    unchanged = before == after
    readonly = {
        "schema": "m152-readonly-verification-v1",
        "before": before,
        "after": after,
        "all_trees_unchanged": unchanged,
    }
    write_json(READONLY_PATH, readonly)
    if not unchanged:
        raise RuntimeError("a registered read-only source tree changed during census")

    manifest: dict[str, Any] = {
        "schema": "m152-input-only-site-census-v1",
        "definition_path": str(DEFINITION_PATH),
        "definition_sha256": definition_sha256,
        "noise_calibration_path": str(NOISE_PATH),
        "noise_calibration_content_sha256": noise_calibration["content_sha256"],
        "source_inventory_path": str(
            inventory_path(definition, "capture_manifest")
        ),
        "source_inventory_sha256": sha256_file(
            inventory_path(definition, "capture_manifest")
        ),
        "holdout_register_path": str(
            inventory_path(definition, "holdout_register")
        ),
        "holdout_register_sha256": sha256_file(
            inventory_path(definition, "holdout_register")
        ),
        "input_only_attestation": {
            "candidate_outputs_opened": 0,
            "comparator_outputs_opened": 0,
            "stacker_runs": 0,
            "site_selection_inputs": [
                "registered ARW pixels",
                "M141 input metadata",
                "non-holdout dark calibration",
            ],
        },
        "edited_macro": {
            "arw_file_count": int(
                before[str(Path(r"D:\edited\macro").resolve())][
                    "extension_counts"
                ].get(".arw", 0)
            ),
            "eligible_input_stack_contribution": 0,
            "reason": "no ARW stacks are present",
        },
        "m3": {
            "capture_results": m3_captures,
            "sufficiency": m3_selection,
        },
        "m4": {
            "bee_background_path": definition["m4"]["bee_background_path"],
            "population_mix": definition["m4"]["population_mix"],
            "noise_floor_rule": definition["noise"]["noise_floor_rule"],
            "flat_capture_results": m4_flat_captures,
            "edge_capture_results": m4_edge_captures,
            "commissioning_flat_results": m4_commissioning,
            "sufficiency": m4_selection,
        },
        "read_only_verification_path": str(READONLY_PATH),
        "numeric_status": "MEASURED_INPUT_ONLY",
    }
    write_json(MANIFEST_PATH, manifest)
    digest = sha256_file(MANIFEST_PATH)
    (OUT / "census-manifest.sha256").write_text(
        f"{digest}  census-manifest.json\n", encoding="ascii"
    )
    print(
        "M3 "
        f"{m3_selection['verdict']}: "
        f"eligible={m3_selection['eligible_edges_overall']} "
        f"selected={m3_selection['selected_site_count']}"
    )
    print(
        "M4 "
        f"{m4_selection['verdict']}: "
        f"flat={m4_selection['eligible_flat_sites_overall']} "
        f"edge={m4_selection['eligible_edge_sites_overall']} "
        f"selected={m4_selection['selected_site_count']}"
    )
    print(f"manifest sha256={digest}")
    return manifest


def find_capture(definition: dict[str, Any], capture_id: str) -> dict[str, Any]:
    groups = [
        definition["m3"]["captures"],
        definition["m4"]["scored_flat_captures"],
        definition["m4"]["commissioning_flat_captures"],
        definition["m4"]["scored_edge_captures"],
    ]
    for group in groups:
        for capture in group:
            if capture["capture_id"] == capture_id:
                return capture
    raise RuntimeError(f"unknown capture_id: {capture_id}")


def run_probe(
    definition: dict[str, Any],
    definition_sha256: str,
    capture_id: str,
    kind: str,
) -> dict[str, Any]:
    capture = find_capture(definition, capture_id)
    if "NOT_HOLDOUT" not in capture["evidence_class"]:
        raise RuntimeError("probe refuses protected or indeterminate capture pixels")
    noise_calibration = load_noise(definition_sha256)
    capture_inventory, holdout_register = load_inventory(definition)
    validate_evidence_classes(definition, holdout_register)
    inventory_by_id = {
        stack["stack_id"]: stack for stack in capture_inventory["stacks"]
    }
    if kind == "flat":
        result = census_flat_capture(
            capture, definition, noise_calibration, inventory_by_id
        )
    else:
        reach = (
            int(definition["m3"]["required_veil_reach_native_px"])
            if kind == "m3-edge"
            else int(definition["m4"]["edge_reach_native_px"])
        )
        result = census_edge_capture(
            capture, reach, definition, inventory_by_id
        )
    artifact = {
        "schema": "m152-non-holdout-probe-v1",
        "definition_sha256": definition_sha256,
        "capture": result,
    }
    output = OUT / f"probe-{capture_id}-{kind}.json"
    write_json(output, artifact)
    print(
        f"probe {capture_id} {kind}: eligible={result['eligible_site_count']} "
        f"output={output}"
    )
    return artifact


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("definition-hash")
    subparsers.add_parser("calibrate-noise")
    probe = subparsers.add_parser("probe")
    probe.add_argument("--capture-id", required=True)
    probe.add_argument(
        "--kind", choices=("flat", "m3-edge", "m4-edge"), required=True
    )
    run = subparsers.add_parser("run")
    run.add_argument("--confirm-definition-sha256", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    definition, definition_sha256 = load_definition()
    if args.command == "definition-hash":
        print(definition_sha256)
    elif args.command == "calibrate-noise":
        calibrate_noise(definition, definition_sha256)
    elif args.command == "probe":
        run_probe(definition, definition_sha256, args.capture_id, args.kind)
    elif args.command == "run":
        run_census(
            definition,
            definition_sha256,
            args.confirm_definition_sha256,
        )
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
