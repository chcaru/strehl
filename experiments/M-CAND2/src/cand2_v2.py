from __future__ import annotations

import hashlib
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy import special

import cand2 as core


EXPERIMENT = core.EXPERIMENT
REPO = core.REPO

CAMPAIGN = "display-amendment"
PINNED_TEMPLATE_SEED = 1687423341261369299
PINNED_TEMPLATE_SHA256 = (
    "f0a719587f7aa39165c7f0fce75835a631306b8b3f21b08e944a137b5a012bfe"
)

DISPLAY_BLACK = 0.1238397868362581
DISPLAY_WHITE = 0.8139398559872297
SOURCE_PREFLIGHT_SHA256 = (
    "93ee82f26d531908df7c23f2ce4afd7cc4cb268ff1daabb732999b52b9b05aa8"
)

POTENCY_CHANGED_FRACTION_MIN = 0.001
POTENCY_HIGH_FRACTION_MIN = 0.0005
POTENCY_MAX_ABS_CHANGE_MIN = 0.005
POTENCY_INDEPENDENT_SITES_MIN = 64
TONE_CHANGED_FRACTION_MIN = 0.95
TONE_NONAFFINE_FRACTION_MIN = 0.10
TONE_NONAFFINE_RESIDUAL_MIN = 0.05
TONE_RMS_CHANGE_MIN = 0.05
TONE_MAX_ABS_CHANGE_MIN = 0.10

FROZEN_PATHS = (
    "experiments/M-CAND1/input-manifest.json",
    "experiments/M-CAND1/src/cand1.py",
    "experiments/M-CAND2/README.md",
    "experiments/M-CAND2/PREREGISTRATION-V2.md",
    "experiments/M-CAND2/out/clipped-usm-invalidity.json",
    "experiments/M-CAND2/out/clipped-usm.json",
    "experiments/M-CAND2/out/preflight.json",
    "experiments/M-CAND2/out/unclipped-usm.json",
    "experiments/M-CAND2/out/amendment-display-preflight.json",
    "experiments/M-CAND2/src/cand2.py",
    "experiments/M-CAND2/src/cand2_v2.py",
    "experiments/M-CAND2/src/check_v2.py",
    "experiments/M-CAND2/src/run_v2.py",
)


def verify_freeze(commit: str) -> dict[str, str]:
    resolved = core.git_output("rev-parse", f"{commit}^{{commit}}").decode().strip()
    hashes: dict[str, str] = {}
    for relative in FROZEN_PATHS:
        path = REPO / relative
        frozen_blob = core.git_output(
            "rev-parse",
            f"{resolved}:{relative}",
        ).decode().strip()
        disk_blob = subprocess.check_output(
            ["git", "hash-object", f"--path={relative}", str(path)],
            cwd=REPO,
            stderr=subprocess.STDOUT,
        ).decode().strip()
        if frozen_blob != disk_blob:
            raise RuntimeError(f"frozen path differs from {resolved}: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"commit": resolved, **hashes}


def require_frozen_preregistration() -> None:
    path = EXPERIMENT / "PREREGISTRATION-V2.md"
    text = path.read_text(encoding="utf-8")
    if (
        "**Status: DRAFT." in text
        or text.count("**Status: FROZEN before any amendment arm.**") != 1
    ):
        raise RuntimeError("amendment preregistration is not FROZEN")


def verify_source_preflight() -> dict:
    path = EXPERIMENT / "out" / "preflight.json"
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SOURCE_PREFLIGHT_SHA256:
        raise RuntimeError(
            f"baseline preflight hash {digest} differs from frozen source"
        )
    import json

    record = json.loads(path.read_text(encoding="utf-8"))
    observed = record["range_audit"]
    if observed["minimum"] != DISPLAY_BLACK or observed["maximum"] != DISPLAY_WHITE:
        raise RuntimeError("display endpoints differ from baseline-only extrema")
    return {
        "path": str(path.relative_to(REPO)).replace("\\", "/"),
        "sha256": digest,
        "minimum": observed["minimum"],
        "maximum": observed["maximum"],
    }


def verify_pinned_task() -> dict:
    audit = core.template_audit(PINNED_TEMPLATE_SEED)
    if audit["template_sha256"] != PINNED_TEMPLATE_SHA256:
        raise RuntimeError("pinned template identity changed")
    return {
        "seed": PINNED_TEMPLATE_SEED,
        "template_sha256": PINNED_TEMPLATE_SHA256,
        "audit": audit,
    }


def _map(data: core.ObservationSet, function) -> core.ObservationSet:
    return core._map_arrays(data, function)


def display_values(values: np.ndarray) -> np.ndarray:
    normalized = (values - DISPLAY_BLACK) / (DISPLAY_WHITE - DISPLAY_BLACK)
    return np.clip(normalized, 0.0, 1.0)


def display_map(data: core.ObservationSet) -> core.ObservationSet:
    return _map(data, display_values)


def transform(data: core.ObservationSet, arm: str) -> core.ObservationSet:
    if arm in ("base", "null"):
        return _map(data, lambda values: values.copy())
    if arm == "unclipped-usm":
        return _map(data, core.usm)
    if arm == "clipped-usm":
        return _map(data, lambda values: np.clip(core.usm(values), 0.0, 1.0))
    if arm == "gamma3":
        return _map(data, lambda values: values**3)
    if arm == "logistic":
        return _map(
            data,
            lambda values: special.expit(
                core.LOGISTIC_SLOPE * (values - 0.5)
            ),
        )
    if arm == "saturation":
        return _map(
            data,
            lambda values: np.clip(
                values,
                core.SATURATION_LOW,
                core.SATURATION_HIGH,
            ),
        )
    if arm == "quantization":
        return _map(
            data,
            lambda values: np.rint(values * core.QUANTIZATION_LEVELS)
            / core.QUANTIZATION_LEVELS,
        )
    raise ValueError(f"unknown amendment transform {arm}")


def make_display_observations(
    backgrounds: np.ndarray,
    arm: str = "base",
    template_seed: int = PINNED_TEMPLATE_SEED,
) -> core.ObservationSet:
    return display_map(
        core.make_observations(
            backgrounds,
            template_seed,
            arm,
        )
    )


def _named_arrays(data: core.ObservationSet) -> dict[str, tuple[np.ndarray, ...]]:
    return {
        "covariance": (data.covariance,),
        "derivative": (data.derivative_plus, data.derivative_minus),
        "test": (data.test_plus, data.test_minus),
    }


def _site_mask(mask: np.ndarray) -> np.ndarray:
    if mask.ndim == 2:
        return np.any(mask, axis=1)
    if mask.ndim == 3:
        return np.any(mask, axis=(0, 2))
    raise RuntimeError(f"unsupported audit mask shape {mask.shape}")


def _role_record(
    data: core.ObservationSet,
    masks: tuple[np.ndarray, ...],
) -> dict:
    site_mask = np.zeros(len(data.blocks), dtype=bool)
    scalar_count = 0
    scalar_total = 0
    for mask in masks:
        scalar_count += int(np.count_nonzero(mask))
        scalar_total += mask.size
        site_mask |= _site_mask(mask)
    sites = np.flatnonzero(site_mask)
    blocks = sorted(int(value) for value in np.unique(data.blocks[sites]))
    return {
        "changed_scalars": scalar_count,
        "total_scalars": scalar_total,
        "changed_fraction": scalar_count / scalar_total,
        "independent_sites": int(len(sites)),
        "blocks": blocks,
        "all_blocks_represented": blocks == [0, 1, 2, 3, 4],
    }


def display_map_audit(
    raw: core.ObservationSet,
    mapped: core.ObservationSet,
) -> dict:
    below = 0
    above = 0
    low = 0
    high = 0
    total = 0
    for source, target in zip(
        core.all_values(raw),
        core.all_values(mapped),
        strict=True,
    ):
        below += int(np.count_nonzero(source < DISPLAY_BLACK))
        above += int(np.count_nonzero(source > DISPLAY_WHITE))
        low += int(np.count_nonzero(target == 0.0))
        high += int(np.count_nonzero(target == 1.0))
        total += source.size
    return {
        "black": DISPLAY_BLACK,
        "white": DISPLAY_WHITE,
        "raw_below_black_count": below,
        "raw_above_white_count": above,
        "mapped_low_rail_count": low,
        "mapped_high_rail_count": high,
        "mapped_rail_fraction": (low + high) / total,
        "total_values": total,
        "mapped_range": core.range_audit(mapped),
    }


def clipping_potency(
    base: core.ObservationSet,
    unclipped: core.ObservationSet,
    clipped: core.ObservationSet,
) -> dict:
    total = 0
    changed = 0
    outside = 0
    low = 0
    high = 0
    sum_square = 0.0
    maximum = 0.0
    role_records = {}
    high_role_records = {}
    low_values = []
    high_values = []
    base_roles = _named_arrays(base)
    unclipped_roles = _named_arrays(unclipped)
    clipped_roles = _named_arrays(clipped)
    exact_masks_match = True
    rail_mapping_exact = True
    for role in base_roles:
        role_masks = []
        high_role_masks = []
        for source, target in zip(
            unclipped_roles[role],
            clipped_roles[role],
            strict=True,
        ):
            changed_mask = source != target
            outside_mask = (source < 0.0) | (source > 1.0)
            high_mask = (source > 1.0) & (target == 1.0)
            exact_masks_match &= bool(np.array_equal(changed_mask, outside_mask))
            rail_mapping_exact &= bool(
                np.all(target[source < 0.0] == 0.0)
                and np.all(target[source > 1.0] == 1.0)
                and np.all(target[~outside_mask] == source[~outside_mask])
            )
            role_masks.append(changed_mask)
            high_role_masks.append(high_mask)
            difference = np.abs(source - target)
            total += source.size
            changed += int(np.count_nonzero(changed_mask))
            outside += int(np.count_nonzero(outside_mask))
            low += int(np.count_nonzero(source < 0.0))
            high += int(np.count_nonzero(source > 1.0))
            sum_square += float(np.sum(difference * difference))
            maximum = max(maximum, float(np.max(difference)))
            low_values.append(source[source < 0.0])
            high_values.append(source[source > 1.0])
        role_records[role] = _role_record(base, tuple(role_masks))
        high_role_records[role] = _role_record(base, tuple(high_role_masks))

    low_samples = np.concatenate(low_values) if low_values else np.empty(0)
    high_samples = np.concatenate(high_values) if high_values else np.empty(0)
    low_collision = bool(
        len(low_samples) >= 2
        and float(np.max(low_samples) - np.min(low_samples)) > 1e-12
    )
    high_collision = bool(
        len(high_samples) >= 2
        and float(np.max(high_samples) - np.min(high_samples)) > 1e-12
    )
    role_gate = all(
        record["independent_sites"] >= POTENCY_INDEPENDENT_SITES_MIN
        and record["all_blocks_represented"]
        for record in role_records.values()
    )
    high_role_gate = all(
        record["independent_sites"] >= POTENCY_INDEPENDENT_SITES_MIN
        and record["all_blocks_represented"]
        for record in high_role_records.values()
    )
    finite = all(
        bool(np.all(np.isfinite(values)))
        for values in core.all_values(unclipped) + core.all_values(clipped)
    )
    changed_fraction = changed / total
    high_fraction = high / total
    passed = bool(
        finite
        and exact_masks_match
        and rail_mapping_exact
        and changed == outside
        and changed_fraction >= POTENCY_CHANGED_FRACTION_MIN
        and high_fraction >= POTENCY_HIGH_FRACTION_MIN
        and maximum >= POTENCY_MAX_ABS_CHANGE_MIN
        and role_gate
        and high_role_gate
        and high_collision
    )
    return {
        "finite": finite,
        "exact_changed_mask_equals_outside_mask": exact_masks_match,
        "exact_outside_to_rail_mapping": rail_mapping_exact,
        "changed_count": changed,
        "outside_count": outside,
        "total_values": total,
        "changed_fraction": changed_fraction,
        "new_low_rail_count": low,
        "new_low_rail_fraction": low / total,
        "new_high_rail_count": high,
        "new_high_rail_fraction": high_fraction,
        "rms_absolute_change": math.sqrt(sum_square / total),
        "maximum_absolute_change": maximum,
        "low_collision_witness": low_collision,
        "high_collision_witness": high_collision,
        "role_records": role_records,
        "high_rail_role_records": high_role_records,
        "gates": {
            "changed_fraction_min": POTENCY_CHANGED_FRACTION_MIN,
            "high_fraction_min": POTENCY_HIGH_FRACTION_MIN,
            "maximum_absolute_change_min": POTENCY_MAX_ABS_CHANGE_MIN,
            "independent_sites_per_role_min": POTENCY_INDEPENDENT_SITES_MIN,
            "all_five_blocks_per_role": True,
            "same_high_rail_site_and_block_gate": True,
            "high_collision_required": True,
        },
        "pass": passed,
    }


def clipping_potency_literal(record: dict) -> bool:
    role_records = record.get("role_records", {})
    high_role_records = record.get("high_rail_role_records", {})
    return bool(
        record.get("finite")
        and record.get("exact_changed_mask_equals_outside_mask")
        and record.get("exact_outside_to_rail_mapping")
        and record.get("changed_count") == record.get("outside_count")
        and record.get("changed_fraction", -1.0)
        >= POTENCY_CHANGED_FRACTION_MIN
        and record.get("new_high_rail_fraction", -1.0)
        >= POTENCY_HIGH_FRACTION_MIN
        and record.get("maximum_absolute_change", -1.0)
        >= POTENCY_MAX_ABS_CHANGE_MIN
        and record.get("high_collision_witness")
        and all(
            role_records.get(role, {}).get("independent_sites", -1)
            >= POTENCY_INDEPENDENT_SITES_MIN
            and role_records.get(role, {}).get("all_blocks_represented")
            and high_role_records.get(role, {}).get("independent_sites", -1)
            >= POTENCY_INDEPENDENT_SITES_MIN
            and high_role_records.get(role, {}).get("all_blocks_represented")
            for role in ("covariance", "derivative", "test")
        )
    )


def _new_ties(source: np.ndarray, target: np.ndarray) -> int:
    source_flat = source.reshape(-1)
    target_flat = target.reshape(-1)
    order = np.argsort(source_flat, kind="mergesort")
    source_sorted = source_flat[order]
    target_sorted = target_flat[order]
    return int(
        np.count_nonzero(
            (np.diff(source_sorted) > 0.0)
            & (np.diff(target_sorted) == 0.0)
        )
    )


def tone_potency(
    base: core.ObservationSet,
    transformed: core.ObservationSet,
    arm: str,
) -> dict:
    if arm == "gamma3":
        endpoint_low = 0.0
        endpoint_high = 1.0
    elif arm == "logistic":
        endpoint_low = float(special.expit(-0.5 * core.LOGISTIC_SLOPE))
        endpoint_high = float(special.expit(0.5 * core.LOGISTIC_SLOPE))
    else:
        raise ValueError(f"tone potency unavailable for {arm}")

    total = 0
    changed = 0
    material = 0
    sum_square = 0.0
    maximum = 0.0
    new_ties = 0
    role_records = {}
    base_roles = _named_arrays(base)
    transformed_roles = _named_arrays(transformed)
    for role in base_roles:
        role_masks = []
        for source, target in zip(
            base_roles[role],
            transformed_roles[role],
            strict=True,
        ):
            chord = endpoint_low + (endpoint_high - endpoint_low) * source
            residual = np.abs(target - chord) / (endpoint_high - endpoint_low)
            material_mask = residual >= TONE_NONAFFINE_RESIDUAL_MIN
            role_masks.append(material_mask)
            difference = np.abs(source - target)
            total += source.size
            changed += int(np.count_nonzero(source != target))
            material += int(np.count_nonzero(material_mask))
            sum_square += float(np.sum(difference * difference))
            maximum = max(maximum, float(np.max(difference)))
            new_ties += _new_ties(source, target)
        role_records[role] = _role_record(base, tuple(role_masks))

    finite = all(
        bool(np.all(np.isfinite(values)))
        for values in core.all_values(transformed)
    )
    role_gate = all(
        record["independent_sites"] >= POTENCY_INDEPENDENT_SITES_MIN
        and record["all_blocks_represented"]
        for record in role_records.values()
    )
    changed_fraction = changed / total
    material_fraction = material / total
    rms = math.sqrt(sum_square / total)
    passed = bool(
        finite
        and changed_fraction >= TONE_CHANGED_FRACTION_MIN
        and material_fraction >= TONE_NONAFFINE_FRACTION_MIN
        and rms >= TONE_RMS_CHANGE_MIN
        and maximum >= TONE_MAX_ABS_CHANGE_MIN
        and new_ties == 0
        and role_gate
    )
    return {
        "finite": finite,
        "changed_count": changed,
        "total_values": total,
        "changed_fraction": changed_fraction,
        "materially_nonaffine_count": material,
        "materially_nonaffine_fraction": material_fraction,
        "nonaffine_residual_threshold": TONE_NONAFFINE_RESIDUAL_MIN,
        "rms_absolute_change": rms,
        "maximum_absolute_change": maximum,
        "new_ties_between_distinct_inputs": new_ties,
        "role_records": role_records,
        "gates": {
            "changed_fraction_min": TONE_CHANGED_FRACTION_MIN,
            "materially_nonaffine_fraction_min": TONE_NONAFFINE_FRACTION_MIN,
            "rms_absolute_change_min": TONE_RMS_CHANGE_MIN,
            "maximum_absolute_change_min": TONE_MAX_ABS_CHANGE_MIN,
            "independent_sites_per_role_min": POTENCY_INDEPENDENT_SITES_MIN,
            "all_five_blocks_per_role": True,
            "new_ties_required": 0,
        },
        "pass": passed,
    }


def tone_potency_literal(record: dict) -> bool:
    role_records = record.get("role_records", {})
    return bool(
        record.get("finite")
        and record.get("changed_fraction", -1.0)
        >= TONE_CHANGED_FRACTION_MIN
        and record.get("materially_nonaffine_fraction", -1.0)
        >= TONE_NONAFFINE_FRACTION_MIN
        and record.get("rms_absolute_change", -1.0)
        >= TONE_RMS_CHANGE_MIN
        and record.get("maximum_absolute_change", -1.0)
        >= TONE_MAX_ABS_CHANGE_MIN
        and record.get("new_ties_between_distinct_inputs") == 0
        and all(
            role_records.get(role, {}).get("independent_sites", -1)
            >= POTENCY_INDEPENDENT_SITES_MIN
            and role_records.get(role, {}).get("all_blocks_represented")
            for role in ("covariance", "derivative", "test")
        )
    )


def lossy_potency(
    base: core.ObservationSet,
    transformed: core.ObservationSet,
    arm: str,
) -> dict:
    total = 0
    changed = 0
    sum_square = 0.0
    maximum = 0.0
    role_records = {}
    collision = False
    base_roles = _named_arrays(base)
    transformed_roles = _named_arrays(transformed)
    for role in base_roles:
        role_masks = []
        for source, target in zip(
            base_roles[role],
            transformed_roles[role],
            strict=True,
        ):
            mask = source != target
            role_masks.append(mask)
            difference = np.abs(source - target)
            total += source.size
            changed += int(np.count_nonzero(mask))
            sum_square += float(np.sum(difference * difference))
            maximum = max(maximum, float(np.max(difference)))
            collision |= _new_ties(source, target) > 0
        role_records[role] = _role_record(base, tuple(role_masks))
    changed_fraction = changed / total
    role_gate = all(
        record["independent_sites"] >= POTENCY_INDEPENDENT_SITES_MIN
        and record["all_blocks_represented"]
        for record in role_records.values()
    )
    minimum_fraction = (
        POTENCY_CHANGED_FRACTION_MIN
        if arm == "saturation"
        else TONE_CHANGED_FRACTION_MIN
    )
    minimum_maximum = (
        POTENCY_MAX_ABS_CHANGE_MIN if arm == "saturation" else 1e-4
    )
    passed = bool(
        changed_fraction >= minimum_fraction
        and maximum >= minimum_maximum
        and role_gate
        and collision
    )
    return {
        "changed_count": changed,
        "total_values": total,
        "changed_fraction": changed_fraction,
        "rms_absolute_change": math.sqrt(sum_square / total),
        "maximum_absolute_change": maximum,
        "many_to_one_collision": collision,
        "role_records": role_records,
        "gates": {
            "changed_fraction_min": minimum_fraction,
            "maximum_absolute_change_min": minimum_maximum,
            "independent_sites_per_role_min": POTENCY_INDEPENDENT_SITES_MIN,
            "all_five_blocks_per_role": True,
            "many_to_one_collision_required": True,
        },
        "pass": passed,
    }


def amendment_source_summary() -> dict:
    return {
        "campaign": CAMPAIGN,
        "base_estimator": core.source_summary(),
        "pinned_task": {
            "seed": PINNED_TEMPLATE_SEED,
            "template_sha256": PINNED_TEMPLATE_SHA256,
        },
        "display_map": {
            "equation": "clip((Y-black)/(white-black), 0, 1)",
            "black": DISPLAY_BLACK,
            "white": DISPLAY_WHITE,
            "selection": "exact baseline-only preflight extrema",
            "source_preflight_sha256": SOURCE_PREFLIGHT_SHA256,
            "global": True,
            "per_image_or_site_adaptation": False,
        },
        "potency": {
            "clipped_usm": {
                "changed_fraction_min": POTENCY_CHANGED_FRACTION_MIN,
                "new_high_rail_fraction_min": POTENCY_HIGH_FRACTION_MIN,
                "maximum_absolute_change_min": POTENCY_MAX_ABS_CHANGE_MIN,
                "independent_sites_per_role_min": POTENCY_INDEPENDENT_SITES_MIN,
                "high_collision_required": True,
            },
            "tone": {
                "changed_fraction_min": TONE_CHANGED_FRACTION_MIN,
                "materially_nonaffine_fraction_min": TONE_NONAFFINE_FRACTION_MIN,
                "nonaffine_residual_min": TONE_NONAFFINE_RESIDUAL_MIN,
                "rms_absolute_change_min": TONE_RMS_CHANGE_MIN,
                "maximum_absolute_change_min": TONE_MAX_ABS_CHANGE_MIN,
                "new_ties": 0,
            },
        },
    }


def output_path(arm: str) -> Path:
    return EXPERIMENT / "out" / f"amendment-{arm}.json"
