#!/usr/bin/env python3
"""Frozen dark/flat estimator for the M165 common-input pattern map.

The estimator fits two independent maps (A and B) for one optical-state class,
then validates their shared residual on a third, never-fitted V block. Real RAW
estimation is intentionally streaming because one 33 MP calibration group is
too large to retain in memory.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import io
import json
import math
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterable, Iterator
import zipfile

import converter


ESTIMATOR_ID = "m165-dark-flat-map"
ESTIMATOR_VERSION = "1.0.0"
SETTINGS_SCHEMA = "m165-pattern-map-settings-v1"
FREEZE_SCHEMA = converter.PATTERN_ESTIMATOR_FREEZE_SCHEMA
CAPTURE_SCHEMA = "m165-pattern-map-capture-v1"
SITTING_SCHEMA = "m165-pattern-map-sitting-v1"
VALIDATION_SCHEMA = converter.PATTERN_VALIDATION_SCHEMA
PACKAGE_SCHEMA = "m165-pattern-map-package-v1"
COMMISSION_SCHEMA = "m165-pattern-map-commission-v1"
SETTINGS_CANONICAL_SHA256 = (
    "1cd6219aaae226c6d8bc71c0e4d7122b15036eae80146d2a02d6cb709714f840"
)

GROUPS = ("dark_a", "flat_a", "dark_b", "flat_b", "dark_v", "flat_v")


def _finite_number(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID", f"{label} must be numeric"
        ) from exc
    if not math.isfinite(result):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID", f"{label} must be finite"
        )
    return result


def _nonempty(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID", f"{label} must be a non-empty string"
        )
    return value


def _artifact_path(base: Path, value: Any, label: str) -> Path:
    path = Path(_nonempty(value, label))
    if not path.is_absolute():
        path = base.parent / path
    return path.resolve()


def _parse_utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID", f"{label} is absent"
        )
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID",
            f"{label} is not ISO-8601: {value!r}",
        ) from exc
    if result.utcoffset() is None:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID", f"{label} must include a UTC offset"
        )
    return result


def load_settings(path: Path) -> dict[str, Any]:
    settings = converter.load_json(path, "pattern-map settings")
    if settings.get("schema") != SETTINGS_SCHEMA:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_SETTINGS_INVALID",
            f"settings schema must be {SETTINGS_SCHEMA}",
        )
    identity = settings.get("estimator", {})
    if identity != {"id": ESTIMATOR_ID, "version": ESTIMATOR_VERSION}:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_SETTINGS_INVALID",
            "settings do not identify this estimator and version",
        )
    expected_policy = {
        "capture_counts": {
            "dark_frames_acquired_per_group": 32,
            "dark_settling_frames_excluded": 2,
            "dark_frames_minimum_usable": 30,
            "flat_frames_acquired_per_group": 32,
            "flat_frames_minimum_usable": 32,
        },
        "class_counts": {
            "dark_temperature_classes_per_sitting": 2,
            "flat_focus_classes_per_sitting": 2,
            "fitted_maps_per_optical_state": 2,
        },
        "temperature": {
            "id_rule": "{session_id}:{optical_state_id}:temperature",
            "center_rule": "temperature sample referenced by dark_a capture_index 0",
            "maximum_sample_age_s": 10.0,
            "maximum_absolute_delta_c": 0.5,
            "maximum_calibration_uncertainty_c": 0.2,
            "interpolation": "forbidden",
        },
        "focus": {
            "id_rule": "{session_id}:{optical_state_id}:focus",
            "fit_position_normalized": 0.5,
            "fit_position_abs_tolerance": 0.05,
            "validation_endpoint_abs_tolerance": 0.05,
            "validation_frames_per_endpoint": 16,
            "application_domain_normalized": [0.0, 1.0],
            "schedule_membership_abs_tolerance": 1e-9,
            "interpolation": "forbidden",
        },
        "validation": {
            "dark_residual_statistic": "per-CFA-plane-demeaned corrected DN; split means use map A on even and map B on odd usable V frames",
            "flat_residual_statistic": "corrected divided by its per-CFA-plane 61-pixel triple-reflect-box field minus one; split means use map A on even and map B on odd V frames",
            "common_rms_statistic": "RMS of one half the sum of the two split means over every active photosite",
            "ring_coherence_statistic": "maximum of zero and real cross-power coherence over admitted Hann-windowed radial rings and all complete CFA-plane tiles",
            "dark_common_rms_maximum_dn": 0.3,
            "flat_common_rms_maximum_fraction": 0.0015,
            "flat_endpoint_common_rms_maximum_fraction": 0.0025,
            "maximum_positive_ring_coherence": 0.05,
            "tile_size_plane_pixels": 128,
            "radial_ring_count": 12,
            "minimum_frequency_cycles_per_plane_pixel": 0.015625,
            "maximum_frequency_cycles_per_plane_pixel": 0.5,
            "minimum_modes_per_ring": 128,
            "split_rule": "capture-index-parity-after-dark-settling-exclusion",
        },
    }
    counts = settings.get("capture_counts", {})
    for key, value in expected_policy["capture_counts"].items():
        if counts.get(key) != value:
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_SETTINGS_INVALID",
                f"capture_counts.{key} must be {value!r}",
            )
    cardinality = settings.get("cardinality", {})
    for key, value in expected_policy["class_counts"].items():
        if cardinality.get(key) != value:
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_SETTINGS_INVALID",
                f"cardinality.{key} must be {value!r}",
            )
    temperature = settings.get("temperature_class", {})
    for key, value in expected_policy["temperature"].items():
        if temperature.get(key) != value:
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_SETTINGS_INVALID",
                f"temperature_class.{key} must be {value!r}",
            )
    focus = settings.get("focus_class", {})
    for key, value in expected_policy["focus"].items():
        if focus.get(key) != value:
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_SETTINGS_INVALID",
                f"focus_class.{key} must be {value!r}",
            )
    if settings.get("held_out_validation") != expected_policy["validation"]:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_SETTINGS_INVALID",
            "held_out_validation differs from the estimator v1 contract",
        )
    if set(settings.get("camera_match", {}).get("by_optical_state", {})) != {
        "converter-on",
        "tc0",
    }:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_SETTINGS_INVALID",
            "camera_match must define converter-on and tc0",
        )
    actual_hash = converter.hash_bytes(converter.canonical_json(settings))
    if actual_hash != SETTINGS_CANONICAL_SHA256:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_SETTINGS_INVALID",
            f"settings canonical hash {actual_hash} differs from "
            f"{SETTINGS_CANONICAL_SHA256}",
        )
    return settings


def _runtime_inventory(settings_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    np, rawpy = converter.import_runtime()
    script = Path(__file__).resolve()
    converter_script = Path(converter.__file__).resolve()
    python = Path(sys.executable).resolve()
    rawpy_module = Path(rawpy.__file__).resolve()
    rawpy_extension = Path(rawpy._rawpy.__file__).resolve()
    numpy_module = Path(np.__file__).resolve()
    numpy_extension = Path(np._core._multiarray_umath.__file__).resolve()
    exiftool_name = shutil.which("exiftool")
    if exiftool_name is None:
        raise converter.ContractFailure("EXIFTOOL_ABSENT", "ExifTool is required")
    exiftool = Path(exiftool_name).resolve()
    try:
        exiftool_version = subprocess.run(
            [str(exiftool), "-ver"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise converter.ContractFailure("EXIFTOOL_FAILED", str(exc)) from exc
    members = {
        "estimator_id": ESTIMATOR_ID,
        "estimator_version": ESTIMATOR_VERSION,
        "estimator_script_sha256": converter.hash_file(script),
        "converter_script_sha256": converter.hash_file(converter_script),
        "settings_sha256": converter.hash_file(settings_path),
        "python_executable_sha256": converter.hash_file(python),
        "rawpy_module_sha256": converter.hash_file(rawpy_module),
        "rawpy_extension_sha256": converter.hash_file(rawpy_extension),
        "numpy_module_sha256": converter.hash_file(numpy_module),
        "numpy_extension_sha256": converter.hash_file(numpy_extension),
        "python_version": platform.python_version(),
        "rawpy_version": rawpy.__version__,
        "libraw_version": ".".join(str(value) for value in rawpy.libraw_version),
        "numpy_version": np.__version__,
        "exiftool_executable_sha256": converter.hash_file(exiftool),
        "exiftool_version": exiftool_version,
    }
    artifacts = {
        "estimator_script": {
            "path": str(script),
            "sha256": members["estimator_script_sha256"],
        },
        "converter_script": {
            "path": str(converter_script),
            "sha256": members["converter_script_sha256"],
        },
        "settings": {
            "path": str(settings_path.resolve()),
            "sha256": members["settings_sha256"],
        },
        "python_executable": {
            "path": str(python),
            "sha256": members["python_executable_sha256"],
        },
        "rawpy_module": {
            "path": str(rawpy_module),
            "sha256": members["rawpy_module_sha256"],
        },
        "rawpy_extension": {
            "path": str(rawpy_extension),
            "sha256": members["rawpy_extension_sha256"],
        },
        "numpy_module": {
            "path": str(numpy_module),
            "sha256": members["numpy_module_sha256"],
        },
        "numpy_extension": {
            "path": str(numpy_extension),
            "sha256": members["numpy_extension_sha256"],
        },
        "exiftool_executable": {
            "path": str(exiftool),
            "sha256": members["exiftool_executable_sha256"],
            "version": exiftool_version,
        },
    }
    return members, artifacts


def build_freeze(settings_path: Path) -> dict[str, Any]:
    load_settings(settings_path)
    members, artifacts = _runtime_inventory(settings_path)
    return {
        "schema": FREEZE_SCHEMA,
        "status": "FROZEN",
        "estimator": {
            "id": ESTIMATOR_ID,
            "version": ESTIMATOR_VERSION,
            "executable_bundle_sha256": converter.hash_bytes(
                converter.canonical_json(members)
            ),
            "bundle_members": members,
        },
        "artifacts": artifacts,
    }


def verify_freeze(path: Path, settings_path: Path) -> dict[str, Any]:
    freeze = converter.load_json(path, "pattern-map estimator freeze")
    if freeze.get("schema") != FREEZE_SCHEMA or freeze.get("status") != "FROZEN":
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_FREEZE_INVALID",
            "pattern-map estimator freeze is absent or not FROZEN",
        )
    members, _ = _runtime_inventory(settings_path)
    expected = converter.check_hash(
        str(freeze.get("estimator", {}).get("executable_bundle_sha256", "")),
        "pattern-map estimator bundle",
    )
    actual = converter.hash_bytes(converter.canonical_json(members))
    if (
        actual != expected
        or freeze.get("estimator", {}).get("bundle_members") != members
    ):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_FREEZE_MISMATCH",
            f"current estimator bundle {actual} differs from frozen {expected}",
        )
    return freeze


def _camera_match_for(settings: dict[str, Any], optical_state: str) -> dict[str, Any]:
    camera = settings["camera_match"]
    state = camera["by_optical_state"].get(optical_state)
    if not isinstance(state, dict):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_INPUT_INVALID",
            f"unknown optical state {optical_state!r}",
        )
    return {**camera["common"], **state}


def validate_capture_manifest(
    path: Path, settings: dict[str, Any], verify_source_hashes: bool = True
) -> dict[str, Any]:
    manifest = converter.load_json(path, "pattern-map capture manifest")
    if manifest.get("schema") != CAPTURE_SCHEMA or manifest.get("status") != "FROZEN":
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_NOT_FROZEN",
            f"capture manifest must be frozen {CAPTURE_SCHEMA}",
        )
    session_id = _nonempty(manifest.get("session_id"), "session_id")
    optical_state = _nonempty(manifest.get("optical_state_id"), "optical_state_id")
    expected_camera = _camera_match_for(settings, optical_state)
    if manifest.get("camera_match") != expected_camera:
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_CAMERA_MISMATCH",
            "capture manifest camera_match differs from frozen settings",
        )

    body = converter.validate_physical_body_artifact(
        path, manifest.get("physical_body")
    )
    body_id = body["id"]
    capture_record = manifest.get("capture_record")
    if not isinstance(capture_record, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_RECORD_INVALID", "capture_record must be an object"
        )
    expected_state = {
        key: expected_camera[key]
        for key in ("raw_mode", "shutter_mode", "steadyshot", "lens_oss")
    }
    capture_record_artifact = converter.validate_capture_record_artifact(
        path,
        capture_record.get("path"),
        capture_record.get("sha256"),
        session_id,
        optical_state,
        body_id,
        expected_state,
    )
    capture_record_path = Path(capture_record_artifact["path"])
    capture_record_hash = capture_record_artifact["sha256"]
    flat_field_record = manifest.get("flat_field_record")
    if not isinstance(flat_field_record, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
            "flat_field_record must be an object",
        )
    flat_field_record_path = _artifact_path(
        path, flat_field_record.get("path"), "flat-field state record"
    )
    flat_field_record_hash = converter.check_hash(
        str(flat_field_record.get("sha256", "")), "flat-field state record"
    )
    if (
        not flat_field_record_path.is_file()
        or converter.hash_file(flat_field_record_path) != flat_field_record_hash
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
            "flat-field state record is absent or changed",
        )
    flat_field = converter.load_json(
        flat_field_record_path, "flat-field state record"
    )
    states = flat_field.get("states")
    if (
        flat_field.get("schema") != "m165-flat-field-state-record-v1"
        or flat_field.get("status") != "FROZEN"
        or flat_field.get("session_id") != session_id
        or flat_field.get("optical_state_id") != optical_state
        or not isinstance(states, dict)
        or set(states) != {"flat_a", "flat_b", "flat_v"}
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
            "flat-field state record schema or identity is invalid",
        )
    state_ids: list[str] = []
    for index, group_name in enumerate(("flat_a", "flat_b", "flat_v")):
        state = states[group_name]
        if not isinstance(state, dict):
            raise converter.ContractFailure(
                "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
                f"{group_name} flat-field state must be an object",
            )
        state_ids.append(
            _nonempty(state.get("state_id"), f"{group_name} flat-field state_id")
        )
        if (
            state.get("diffuser_moved_or_rotated_since_previous") != (index > 0)
            or state.get("spatially_uniform_unresolved_field_verified") is not True
        ):
            raise converter.ContractFailure(
                "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
                f"{group_name} does not record the frozen diffuser action/field check",
            )
        _parse_utc(
            state.get("recorded_at_utc"), f"{group_name} flat-field recorded_at_utc"
        )
    if len(set(state_ids)) != 3:
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
            "A, B, and V must use three independently named flat-field states",
        )

    temperature = manifest.get("temperature_class")
    if not isinstance(temperature, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature_class must be an object",
        )
    temperature_settings = settings["temperature_class"]
    expected_temperature_id = temperature_settings["id_rule"].format(
        session_id=session_id, optical_state_id=optical_state
    )
    if (
        temperature.get("id") != expected_temperature_id
        or temperature.get("interpolation") != temperature_settings["interpolation"]
        or
        _finite_number(
            temperature.get("maximum_absolute_delta_c"),
            "temperature maximum delta",
        )
        != float(temperature_settings["maximum_absolute_delta_c"])
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature tolerance or interpolation differs from frozen settings",
        )
    temperature_id = _nonempty(temperature.get("id"), "temperature_class.id")
    center_c = _finite_number(temperature.get("center_c"), "temperature center")
    center_sample_index = temperature.get("center_sample_index")
    if not isinstance(center_sample_index, int) or center_sample_index < 0:
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature center_sample_index must be a non-negative integer",
        )
    witness = temperature.get("witness")
    if not isinstance(witness, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature witness must be an object",
        )
    if (
        witness.get("kind") != temperature_settings["witness_kind"]
        or _finite_number(
            witness.get("maximum_sample_age_s"),
            "temperature maximum sample age",
        )
        != float(temperature_settings["maximum_sample_age_s"])
        or _finite_number(
            witness.get("maximum_calibration_uncertainty_c"),
            "temperature maximum calibration uncertainty",
        )
        != float(temperature_settings["maximum_calibration_uncertainty_c"])
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature witness policy differs from frozen settings",
        )
    temperature_artifacts = converter.validate_temperature_artifacts(
        path,
        witness,
        float(temperature_settings["maximum_calibration_uncertainty_c"]),
    )
    calibration_path = Path(temperature_artifacts["calibration_path"])
    log_path = Path(temperature_artifacts["log_path"])
    log_hash = temperature_artifacts["log_sha256"]
    samples = temperature_artifacts["samples"]
    maximum_age = float(temperature_settings["maximum_sample_age_s"])
    if center_sample_index >= len(samples):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature center_sample_index is outside the frozen log",
        )
    if center_c != float(samples[center_sample_index]["temperature_c"]):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature center differs from its frozen log sample",
        )

    focus = manifest.get("focus_class")
    if not isinstance(focus, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FOCUS_INVALID", "focus_class must be an object"
        )
    focus_settings = settings["focus_class"]
    expected_focus_id = focus_settings["id_rule"].format(
        session_id=session_id, optical_state_id=optical_state
    )
    expected_focus_values = {
        "domain_normalized": focus_settings["application_domain_normalized"],
        "fit_position_normalized": focus_settings["fit_position_normalized"],
        "fit_position_abs_tolerance": focus_settings["fit_position_abs_tolerance"],
        "validation_endpoint_abs_tolerance": focus_settings[
            "validation_endpoint_abs_tolerance"
        ],
        "interpolation": "forbidden",
    }
    if (
        focus.get("id") != expected_focus_id
        or any(focus.get(key) != value for key, value in expected_focus_values.items())
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FOCUS_INVALID",
            "focus class domain differs from frozen settings",
        )
    focus_id = _nonempty(focus.get("id"), "focus_class.id")
    schedule_artifact = converter.validate_focus_schedule_artifact(
        path,
        focus.get("schedule_path"),
        focus.get("schedule_sha256"),
        session_id,
        optical_state,
        focus_id,
    )
    schedule_path = Path(schedule_artifact["path"])
    schedule_hash = schedule_artifact["sha256"]
    schedule = schedule_artifact["schedule"]
    if (
        schedule.get("fit_position_normalized")
        != focus_settings["fit_position_normalized"]
        or schedule.get("validation_endpoint_positions")
        != focus_settings["validation_endpoint_positions"]
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FOCUS_INVALID",
            "focus schedule does not match the capture class",
        )

    sensor = manifest.get("sensor_fingerprint")
    if not isinstance(sensor, dict):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_SENSOR_INVALID", "sensor_fingerprint must be an object"
        )
    active_shape = sensor.get("active_shape")
    raw_shape = sensor.get("raw_shape")
    black_levels = sensor.get("black_levels")
    white_levels = sensor.get("white_levels")
    raw_pattern = sensor.get("raw_pattern")
    if (
        not isinstance(active_shape, list)
        or len(active_shape) != 2
        or any(not isinstance(value, int) or value <= 0 for value in active_shape)
        or not isinstance(raw_shape, list)
        or len(raw_shape) != 2
        or any(not isinstance(value, int) or value <= 0 for value in raw_shape)
        or not isinstance(black_levels, list)
        or len(black_levels) != 4
        or not isinstance(white_levels, list)
        or len(white_levels) != 4
        or not isinstance(raw_pattern, list)
        or len(raw_pattern) != 2
        or any(not isinstance(row, list) or len(row) != 2 for row in raw_pattern)
        or not isinstance(sensor.get("color_description"), str)
        or not sensor["color_description"]
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_SENSOR_INVALID",
            "sensor fingerprint structure or dimensions are invalid",
        )
    groups = manifest.get("groups")
    if not isinstance(groups, dict) or set(groups) != set(GROUPS):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_GROUPS_INVALID",
            f"groups must be exactly {list(GROUPS)!r}",
        )
    counts = settings["capture_counts"]
    required_counts = {
        "dark_a": counts["dark_frames_acquired_per_group"],
        "dark_b": counts["dark_frames_acquired_per_group"],
        "dark_v": counts["dark_frames_acquired_per_group"],
        "flat_a": counts["flat_frames_acquired_per_group"],
        "flat_b": counts["flat_frames_acquired_per_group"],
        "flat_v": counts["flat_frames_acquired_per_group"],
    }
    seen_hashes: set[str] = set()
    normalized_groups: dict[str, list[dict[str, Any]]] = {}
    for group_name in GROUPS:
        records = groups[group_name]
        if not isinstance(records, list) or len(records) != required_counts[group_name]:
            raise converter.ContractFailure(
                "PATTERN_CAPTURE_COUNT_MISMATCH",
                f"{group_name} must contain exactly {required_counts[group_name]} frames",
            )
        normalized_records: list[dict[str, Any]] = []
        for expected_index, record in enumerate(records):
            if not isinstance(record, dict) or record.get("capture_index") != expected_index:
                raise converter.ContractFailure(
                    "PATTERN_CAPTURE_ORDER_INVALID",
                    f"{group_name} capture_index must be contiguous from zero",
                )
            source_path = _artifact_path(
                path, record.get("path"), f"{group_name}[{expected_index}]"
            )
            source_hash = converter.check_hash(
                str(record.get("sha256", "")),
                f"{group_name}[{expected_index}] source",
            )
            if source_hash in seen_hashes:
                raise converter.ContractFailure(
                    "PATTERN_CAPTURE_SOURCES_NOT_INDEPENDENT",
                    f"source hash {source_hash} occurs in more than one role",
                )
            seen_hashes.add(source_hash)
            if verify_source_hashes and (
                not source_path.is_file()
                or converter.hash_file(source_path) != source_hash
            ):
                raise converter.ContractFailure(
                    "PATTERN_CAPTURE_SOURCE_MISMATCH",
                    f"{group_name}[{expected_index}] is absent or changed",
                )
            sample_index = record.get("temperature_sample_index")
            if (
                not isinstance(sample_index, int)
                or sample_index < 0
                or sample_index >= len(samples)
                or not isinstance(samples[sample_index], dict)
            ):
                raise converter.ContractFailure(
                    "PATTERN_CAPTURE_TEMPERATURE_INVALID",
                    f"{group_name}[{expected_index}] has no valid temperature sample",
                )
            sample = samples[sample_index]
            sample_c = _finite_number(
                sample.get("temperature_c"),
                f"{group_name}[{expected_index}] temperature",
            )
            captured_at = _parse_utc(
                record.get("captured_at_utc"),
                f"{group_name}[{expected_index}] captured_at_utc",
            )
            sampled_at = _parse_utc(
                sample.get("timestamp_utc"),
                f"{group_name}[{expected_index}] temperature timestamp",
            )
            sample_age = abs((captured_at - sampled_at).total_seconds())
            if (
                sample_age > maximum_age
                or abs(sample_c - center_c)
                > float(temperature_settings["maximum_absolute_delta_c"])
            ):
                raise converter.ContractFailure(
                    "PATTERN_CAPTURE_TEMPERATURE_MISMATCH",
                    f"{group_name}[{expected_index}] temperature {sample_c} C / "
                    f"age {sample_age} s is outside the class",
                )
            focus_position = record.get("focus_position_normalized")
            if group_name.startswith("dark"):
                if focus_position is not None:
                    raise converter.ContractFailure(
                        "PATTERN_CAPTURE_FOCUS_INVALID",
                        f"{group_name} dark records must not claim a focus position",
                    )
                normalized_focus = None
            else:
                normalized_focus = _finite_number(
                    focus_position,
                    f"{group_name}[{expected_index}] focus position",
                )
                if not 0.0 <= normalized_focus <= 1.0:
                    raise converter.ContractFailure(
                        "PATTERN_CAPTURE_FOCUS_INVALID",
                        f"{group_name}[{expected_index}] focus is outside [0,1]",
                    )
            normalized_records.append(
                {
                    **record,
                    "resolved_path": str(source_path),
                    "sha256": source_hash,
                    "temperature_c": sample_c,
                    "temperature_sample_age_s": sample_age,
                    "focus_position_normalized": normalized_focus,
                }
            )
        normalized_groups[group_name] = normalized_records

    first_dark_sample = normalized_groups["dark_a"][0]["temperature_sample_index"]
    if (
        temperature_settings["center_rule"]
        != "temperature sample referenced by dark_a capture_index 0"
        or center_sample_index != first_dark_sample
    ):
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_TEMPERATURE_INVALID",
            "temperature class center must be the sample referenced by DARK-A frame 0",
        )

    fit_center = float(focus_settings["fit_position_normalized"])
    fit_tolerance = float(focus_settings["fit_position_abs_tolerance"])
    for group_name in ("flat_a", "flat_b"):
        if any(
            abs(float(record["focus_position_normalized"]) - fit_center)
            > fit_tolerance
            for record in normalized_groups[group_name]
        ):
            raise converter.ContractFailure(
                "PATTERN_CAPTURE_FOCUS_MISMATCH",
                f"{group_name} must be within {fit_center} +/- {fit_tolerance}",
            )
    endpoint_tolerance = float(focus_settings["validation_endpoint_abs_tolerance"])
    endpoint_count = int(focus_settings["validation_frames_per_endpoint"])
    validation_positions = [
        float(record["focus_position_normalized"])
        for record in normalized_groups["flat_v"]
    ]
    near_count = sum(position <= endpoint_tolerance for position in validation_positions)
    far_count = sum(
        position >= 1.0 - endpoint_tolerance for position in validation_positions
    )
    if near_count != endpoint_count or far_count != endpoint_count:
        raise converter.ContractFailure(
            "PATTERN_CAPTURE_FOCUS_MISMATCH",
            f"flat_v must contain {endpoint_count} near and {endpoint_count} far frames",
        )

    return {
        **manifest,
        "manifest_path": str(path.resolve()),
        "manifest_sha256": converter.hash_file(path),
        "body_witness_path": body["witness_path"],
        "body_witness_sha256": body["witness_sha256"],
        "capture_record_path": str(capture_record_path),
        "capture_record_sha256": capture_record_hash,
        "flat_field_record_path": str(flat_field_record_path),
        "flat_field_record_sha256": flat_field_record_hash,
        "temperature_calibration_path": str(calibration_path),
        "temperature_calibration_sha256": temperature_artifacts[
            "calibration_sha256"
        ],
        "temperature_calibration_uncertainty_c": temperature_artifacts[
            "calibration_uncertainty_c"
        ],
        "temperature_log_path": str(log_path),
        "temperature_log_sha256": log_hash,
        "focus_schedule_path": str(schedule_path),
        "focus_schedule_sha256": schedule_hash,
        "groups": normalized_groups,
    }


def validate_sitting_manifest(
    path: Path,
    settings_path: Path,
    settings: dict[str, Any],
    verify_source_hashes: bool = True,
) -> dict[str, Any]:
    manifest = converter.load_json(path, "pattern-map sitting manifest")
    if manifest.get("schema") != SITTING_SCHEMA or manifest.get("status") != "FROZEN":
        raise converter.ContractFailure(
            "PATTERN_SITTING_NOT_FROZEN",
            f"sitting manifest must be frozen {SITTING_SCHEMA}",
        )
    session_id = _nonempty(manifest.get("session_id"), "sitting session_id")
    expected_settings = converter.check_hash(
        str(manifest.get("settings_sha256", "")), "pattern-map settings"
    )
    actual_settings = converter.hash_file(settings_path)
    if expected_settings != actual_settings:
        raise converter.ContractFailure(
            "PATTERN_SITTING_SETTINGS_MISMATCH",
            f"sitting settings hash {expected_settings} != {actual_settings}",
        )
    classes = manifest.get("classes")
    if not isinstance(classes, list) or len(classes) != 2:
        raise converter.ContractFailure(
            "PATTERN_SITTING_CARDINALITY_MISMATCH",
            "sitting must contain exactly two optical-state classes",
        )
    by_state: dict[str, dict[str, Any]] = {}
    all_sources: set[str] = set()
    body_identity: tuple[str, str] | None = None
    capture_record_hashes: set[str] = set()
    for entry in classes:
        if not isinstance(entry, dict):
            raise converter.ContractFailure(
                "PATTERN_SITTING_CARDINALITY_MISMATCH",
                "every sitting class entry must be an object",
            )
        optical_state = _nonempty(
            entry.get("optical_state_id"), "sitting optical_state_id"
        )
        if optical_state in by_state:
            raise converter.ContractFailure(
                "PATTERN_SITTING_CARDINALITY_MISMATCH",
                f"duplicate sitting optical state {optical_state!r}",
            )
        capture_path = _artifact_path(
            path,
            entry.get("capture_manifest_path"),
            f"{optical_state} capture manifest",
        )
        capture_sha = converter.check_hash(
            str(entry.get("capture_manifest_sha256", "")),
            f"{optical_state} capture manifest",
        )
        if not capture_path.is_file() or converter.hash_file(capture_path) != capture_sha:
            raise converter.ContractFailure(
                "PATTERN_SITTING_CAPTURE_MISMATCH",
                f"{optical_state} capture manifest is absent or changed",
            )
        capture = validate_capture_manifest(
            capture_path, settings, verify_source_hashes=verify_source_hashes
        )
        expected_temperature_id = settings["temperature_class"]["id_rule"].format(
            session_id=session_id, optical_state_id=optical_state
        )
        expected_focus_id = settings["focus_class"]["id_rule"].format(
            session_id=session_id, optical_state_id=optical_state
        )
        if (
            capture["session_id"] != session_id
            or capture["optical_state_id"] != optical_state
            or entry.get("temperature_class_id") != expected_temperature_id
            or capture["temperature_class"]["id"] != expected_temperature_id
            or entry.get("focus_class_id") != expected_focus_id
            or capture["focus_class"]["id"] != expected_focus_id
        ):
            raise converter.ContractFailure(
                "PATTERN_SITTING_CLASS_MISMATCH",
                f"{optical_state} class identity does not match the sitting",
            )
        identity = (
            capture["physical_body"]["id"],
            capture["physical_body"]["witness_sha256"],
        )
        if body_identity is None:
            body_identity = identity
        elif identity != body_identity:
            raise converter.ContractFailure(
                "PATTERN_SITTING_BODY_MISMATCH",
                "optical-state classes do not identify the same physical body",
            )
        if capture["capture_record_sha256"] in capture_record_hashes:
            raise converter.ContractFailure(
                "PATTERN_SITTING_CAPTURE_MISMATCH",
                "optical states must have distinct physical capture records",
            )
        capture_record_hashes.add(capture["capture_record_sha256"])
        for group in GROUPS:
            for record in capture["groups"][group]:
                source_sha = record["sha256"]
                if source_sha in all_sources:
                    raise converter.ContractFailure(
                        "PATTERN_SITTING_SOURCES_NOT_INDEPENDENT",
                        "a calibration source is shared across optical states",
                    )
                all_sources.add(source_sha)
        by_state[optical_state] = capture
    expected_states = set(settings["cardinality"]["optical_states"])
    if set(by_state) != expected_states:
        raise converter.ContractFailure(
            "PATTERN_SITTING_CARDINALITY_MISMATCH",
            f"sitting optical states must be exactly {sorted(expected_states)!r}",
        )
    return {
        **manifest,
        "manifest_path": str(path.resolve()),
        "manifest_sha256": converter.hash_file(path),
        "dark_temperature_class_count": len(by_state),
        "flat_focus_class_count": len(by_state),
        "fitted_map_count": len(by_state)
        * int(settings["cardinality"]["fitted_maps_per_optical_state"]),
        "classes_by_optical_state": by_state,
    }


def _box_filter_reflect(values: Any, width: int, axis: int) -> Any:
    np, _ = converter.import_runtime()
    radius = width // 2
    pad = [(0, 0)] * values.ndim
    pad[axis] = (radius, radius)
    padded = np.pad(values, pad, mode="reflect")
    cumulative = np.cumsum(padded, axis=axis, dtype=np.float64)
    zero_shape = list(cumulative.shape)
    zero_shape[axis] = 1
    cumulative = np.concatenate(
        [np.zeros(zero_shape, dtype=np.float64), cumulative], axis=axis
    )
    high = [slice(None)] * values.ndim
    low = [slice(None)] * values.ndim
    high[axis] = slice(width, None)
    low[axis] = slice(None, -width)
    return (cumulative[tuple(high)] - cumulative[tuple(low)]) / float(width)


def _triple_box_plane(values: Any, width: int) -> Any:
    result = values
    for _ in range(3):
        result = _box_filter_reflect(result, width, 0)
        result = _box_filter_reflect(result, width, 1)
    return result


def _smooth_cfa(values: Any, width: int) -> Any:
    np, _ = converter.import_runtime()
    result = np.empty(values.shape, dtype=np.float64)
    for y_offset in range(2):
        for x_offset in range(2):
            result[y_offset::2, x_offset::2] = _triple_box_plane(
                values[y_offset::2, x_offset::2], width
            )
    return result


def _black_white_at(sample: dict[str, Any]) -> tuple[Any, Any]:
    np, _ = converter.import_runtime()
    colors = np.asarray(sample["colors"], dtype=np.intp)
    black = np.asarray(sample["black_levels"], dtype=np.float64)
    white = np.asarray(sample["white_levels"], dtype=np.float64)
    return black[colors], white[colors]


def estimate_dark(samples: Iterable[dict[str, Any]], settings: dict[str, Any]) -> Any:
    np, _ = converter.import_runtime()
    excluded = int(settings["capture_counts"]["dark_settling_frames_excluded"])
    total = None
    used = 0
    for sample in samples:
        if int(sample["capture_index"]) < excluded:
            continue
        black_at, _ = _black_white_at(sample)
        signal = np.asarray(sample["raw"], dtype=np.float64) - black_at
        if total is None:
            total = np.zeros(signal.shape, dtype=np.float64)
        total += signal
        used += 1
    expected = int(settings["capture_counts"]["dark_frames_minimum_usable"])
    if total is None or used != expected:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_DARK_COUNT",
            f"dark estimator used {used} frames, expected {expected}",
        )
    return (total / float(used)).astype(np.float32)


def _flat_ratio(
    sample: dict[str, Any],
    offset_dn: Any,
    settings: dict[str, Any],
    enforce_quality: bool,
) -> tuple[Any, dict[str, Any]]:
    np, _ = converter.import_runtime()
    raw = np.asarray(sample["raw"], dtype=np.float64)
    black_at, white_at = _black_white_at(sample)
    signal = raw - black_at - np.asarray(offset_dn, dtype=np.float64)
    width = int(
        settings["estimation"]["flat_smooth_filter"]["width_plane_pixels"]
    )
    smooth = _smooth_cfa(signal, width)
    if not np.all(np.isfinite(signal)) or not np.all(np.isfinite(smooth)):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_FLAT_INVALID", "flat signal contains non-finite values"
        )
    if np.any(smooth <= 0.0):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_FLAT_INVALID", "flat smooth field is not positive"
        )
    ratio = signal / smooth
    plane_means = []
    for y_offset in range(2):
        for x_offset in range(2):
            plane_means.append(
                float(np.mean(signal[y_offset::2, x_offset::2], dtype=np.float64))
            )
    clipped_fraction = float(np.mean(raw >= white_at))
    highpass_rms = float(np.sqrt(np.mean((ratio - 1.0) ** 2, dtype=np.float64)))
    quality = {
        "plane_mean_dn": plane_means,
        "clipped_fraction": clipped_fraction,
        "highpass_rms_fraction": highpass_rms,
    }
    if enforce_quality:
        lower = float(settings["estimation"]["flat_plane_mean_minimum_dn"])
        upper = float(settings["estimation"]["flat_plane_mean_maximum_dn"])
        if any(value < lower or value > upper for value in plane_means):
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_FLAT_LEVEL",
                f"flat plane means {plane_means!r} are outside [{lower},{upper}] DN",
            )
        if clipped_fraction > float(
            settings["estimation"]["flat_clipped_fraction_maximum"]
        ):
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_FLAT_CLIPPED",
                f"flat clipped fraction {clipped_fraction} exceeds the frozen limit",
            )
        if highpass_rms > float(
            settings["estimation"]["flat_input_highpass_rms_maximum"]
        ):
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_FLAT_TEXTURED",
                f"flat high-pass RMS {highpass_rms} exceeds the frozen limit",
            )
    return ratio, quality


def estimate_gain(
    samples: Iterable[dict[str, Any]], offset_dn: Any, settings: dict[str, Any]
) -> tuple[Any, dict[str, Any]]:
    np, _ = converter.import_runtime()
    total = None
    used = 0
    quality: list[dict[str, Any]] = []
    for sample in samples:
        ratio, frame_quality = _flat_ratio(sample, offset_dn, settings, True)
        if total is None:
            total = np.zeros(ratio.shape, dtype=np.float64)
        total += ratio
        quality.append(frame_quality)
        used += 1
    expected = int(settings["capture_counts"]["flat_frames_minimum_usable"])
    if total is None or used != expected:
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_FLAT_COUNT",
            f"flat estimator used {used} frames, expected {expected}",
        )
    mean_ratio = total / float(used)
    if np.any(mean_ratio <= 0.0) or not np.all(np.isfinite(mean_ratio)):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_GAIN_INVALID",
            "mean normalized flat is not finite and positive",
        )
    gain = 1.0 / mean_ratio
    minimum = float(settings["estimation"]["gain_minimum"])
    maximum = float(settings["estimation"]["gain_maximum"])
    if np.any(gain < minimum) or np.any(gain > maximum):
        raise converter.ContractFailure(
            "PATTERN_ESTIMATOR_GAIN_INVALID",
            f"gain lies outside [{minimum},{maximum}]",
        )
    return gain.astype(np.float32), {
        "used_frames": used,
        "maximum_clipped_fraction": max(item["clipped_fraction"] for item in quality),
        "maximum_input_highpass_rms_fraction": max(
            item["highpass_rms_fraction"] for item in quality
        ),
        "plane_mean_dn_minimum": min(
            min(item["plane_mean_dn"]) for item in quality
        ),
        "plane_mean_dn_maximum": max(
            max(item["plane_mean_dn"]) for item in quality
        ),
    }


def _dark_residual(sample: dict[str, Any], gain: Any, offset: Any) -> Any:
    np, _ = converter.import_runtime()
    raw = np.asarray(sample["raw"], dtype=np.float64)
    black_at, _ = _black_white_at(sample)
    residual = (raw - black_at - np.asarray(offset, dtype=np.float64)) * np.asarray(
        gain, dtype=np.float64
    )
    for y_offset in range(2):
        for x_offset in range(2):
            plane = residual[y_offset::2, x_offset::2]
            plane -= float(np.mean(plane, dtype=np.float64))
    return residual


def _flat_residual(
    sample: dict[str, Any], gain: Any, offset: Any, settings: dict[str, Any]
) -> Any:
    np, _ = converter.import_runtime()
    raw = np.asarray(sample["raw"], dtype=np.float64)
    black_at, _ = _black_white_at(sample)
    corrected = (raw - black_at - np.asarray(offset, dtype=np.float64)) * np.asarray(
        gain, dtype=np.float64
    )
    smooth = _smooth_cfa(
        corrected,
        int(settings["estimation"]["flat_smooth_filter"]["width_plane_pixels"]),
    )
    if np.any(smooth <= 0.0) or not np.all(np.isfinite(smooth)):
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_FLAT_INVALID",
            "corrected held-out flat has an invalid smooth field",
        )
    return corrected / smooth - 1.0


def _mean_or_fail(total: Any, count: int, label: str) -> Any:
    if total is None or count <= 0:
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_COUNT_MISMATCH", f"{label} has no samples"
        )
    return total / float(count)


def _ring_coherence(left: Any, right: Any, settings: dict[str, Any]) -> dict[str, Any]:
    np, _ = converter.import_runtime()
    validation = settings["held_out_validation"]
    tile_size = int(validation["tile_size_plane_pixels"])
    ring_count = int(validation["radial_ring_count"])
    minimum_frequency = float(
        validation["minimum_frequency_cycles_per_plane_pixel"]
    )
    maximum_frequency = float(
        validation["maximum_frequency_cycles_per_plane_pixel"]
    )
    minimum_modes = int(validation["minimum_modes_per_ring"])
    window_1d = np.hanning(tile_size).astype(np.float64)
    window = window_1d[:, None] * window_1d[None, :]
    fy = np.fft.fftfreq(tile_size)[:, None]
    fx = np.fft.rfftfreq(tile_size)[None, :]
    radial = np.sqrt(fx * fx + fy * fy)
    edges = np.linspace(minimum_frequency, maximum_frequency, ring_count + 1)
    cross = np.zeros(ring_count, dtype=np.float64)
    auto_left = np.zeros(ring_count, dtype=np.float64)
    auto_right = np.zeros(ring_count, dtype=np.float64)
    modes = np.zeros(ring_count, dtype=np.int64)
    tile_count = 0
    for y_offset in range(2):
        for x_offset in range(2):
            plane_left = np.asarray(left[y_offset::2, x_offset::2], dtype=np.float64)
            plane_right = np.asarray(right[y_offset::2, x_offset::2], dtype=np.float64)
            height = plane_left.shape[0] // tile_size * tile_size
            width = plane_left.shape[1] // tile_size * tile_size
            for y in range(0, height, tile_size):
                for x in range(0, width, tile_size):
                    a = plane_left[y : y + tile_size, x : x + tile_size]
                    b = plane_right[y : y + tile_size, x : x + tile_size]
                    a = (a - float(np.mean(a))) * window
                    b = (b - float(np.mean(b))) * window
                    fa = np.fft.rfft2(a)
                    fb = np.fft.rfft2(b)
                    for ring in range(ring_count):
                        mask = (radial >= edges[ring]) & (radial < edges[ring + 1])
                        if not np.any(mask):
                            continue
                        cross[ring] += float(
                            np.sum((fa[mask] * np.conj(fb[mask])).real)
                        )
                        auto_left[ring] += float(np.sum(np.abs(fa[mask]) ** 2))
                        auto_right[ring] += float(np.sum(np.abs(fb[mask]) ** 2))
                        modes[ring] += int(np.count_nonzero(mask))
                    tile_count += 1
    if tile_count == 0:
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_GEOMETRY",
            f"residual planes are smaller than one {tile_size}x{tile_size} tile",
        )
    rings = []
    for index in range(ring_count):
        denominator = math.sqrt(auto_left[index] * auto_right[index])
        coherence = cross[index] / denominator if denominator > 0.0 else 0.0
        rings.append(
            {
                "index": index,
                "frequency_min": float(edges[index]),
                "frequency_max": float(edges[index + 1]),
                "modes": int(modes[index]),
                "coherence": float(coherence),
            }
        )
    admitted = [ring for ring in rings if ring["modes"] >= minimum_modes]
    if not admitted:
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_GEOMETRY",
            "no radial ring has the frozen minimum mode count",
        )
    return {
        "tile_size_plane_pixels": tile_size,
        "tile_count": tile_count,
        "rings": rings,
        "maximum_positive_coherence": max(
            0.0, max(ring["coherence"] for ring in admitted)
        ),
    }


def validate_maps(
    dark_v: Iterable[dict[str, Any]],
    flat_v: Iterable[dict[str, Any]],
    map_a: dict[str, Any],
    map_b: dict[str, Any],
    settings: dict[str, Any],
) -> dict[str, Any]:
    np, _ = converter.import_runtime()
    excluded = int(settings["capture_counts"]["dark_settling_frames_excluded"])
    dark_totals = [None, None]
    dark_counts = [0, 0]
    for sample in dark_v:
        index = int(sample["capture_index"])
        if index < excluded:
            continue
        arm = index & 1
        selected = map_a if arm == 0 else map_b
        residual = _dark_residual(sample, selected["gain"], selected["offset_dn"])
        if dark_totals[arm] is None:
            dark_totals[arm] = np.zeros(residual.shape, dtype=np.float64)
        dark_totals[arm] += residual
        dark_counts[arm] += 1
    expected_dark_each = int(
        settings["capture_counts"]["dark_frames_minimum_usable"]
    ) // 2
    if dark_counts != [expected_dark_each, expected_dark_each]:
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_COUNT_MISMATCH",
            f"held-out dark split is {dark_counts}, expected "
            f"[{expected_dark_each},{expected_dark_each}]",
        )
    dark_left = _mean_or_fail(dark_totals[0], dark_counts[0], "dark A")
    dark_right = _mean_or_fail(dark_totals[1], dark_counts[1], "dark B")
    dark_common = (dark_left + dark_right) * 0.5
    dark_rms = float(np.sqrt(np.mean(dark_common * dark_common, dtype=np.float64)))
    dark_ring = _ring_coherence(dark_left, dark_right, settings)

    flat_totals = [None, None]
    flat_counts = [0, 0]
    endpoint_totals = {
        "near": [None, None],
        "far": [None, None],
    }
    endpoint_counts = {
        "near": [0, 0],
        "far": [0, 0],
    }
    endpoint_tolerance = float(
        settings["focus_class"]["validation_endpoint_abs_tolerance"]
    )
    for sample in flat_v:
        index = int(sample["capture_index"])
        arm = index & 1
        selected = map_a if arm == 0 else map_b
        residual = _flat_residual(
            sample, selected["gain"], selected["offset_dn"], settings
        )
        if flat_totals[arm] is None:
            flat_totals[arm] = np.zeros(residual.shape, dtype=np.float64)
        flat_totals[arm] += residual
        flat_counts[arm] += 1
        position = float(sample["focus_position_normalized"])
        endpoint = "near" if position <= endpoint_tolerance else "far"
        if endpoint_totals[endpoint][arm] is None:
            endpoint_totals[endpoint][arm] = np.zeros(
                residual.shape, dtype=np.float64
            )
        endpoint_totals[endpoint][arm] += residual
        endpoint_counts[endpoint][arm] += 1
    expected_flat_each = int(
        settings["capture_counts"]["flat_frames_minimum_usable"]
    ) // 2
    if flat_counts != [expected_flat_each, expected_flat_each]:
        raise converter.ContractFailure(
            "PATTERN_VALIDATION_COUNT_MISMATCH",
            f"held-out flat split is {flat_counts}, expected "
            f"[{expected_flat_each},{expected_flat_each}]",
        )
    flat_left = _mean_or_fail(flat_totals[0], flat_counts[0], "flat A")
    flat_right = _mean_or_fail(flat_totals[1], flat_counts[1], "flat B")
    flat_common = (flat_left + flat_right) * 0.5
    flat_rms = float(np.sqrt(np.mean(flat_common * flat_common, dtype=np.float64)))
    flat_ring = _ring_coherence(flat_left, flat_right, settings)
    endpoint_rms = {}
    expected_endpoint_each = (
        int(settings["focus_class"]["validation_frames_per_endpoint"]) // 2
    )
    for endpoint in ("near", "far"):
        if endpoint_counts[endpoint] != [
            expected_endpoint_each,
            expected_endpoint_each,
        ]:
            raise converter.ContractFailure(
                "PATTERN_VALIDATION_COUNT_MISMATCH",
                f"{endpoint} flat split is {endpoint_counts[endpoint]}, expected "
                f"[{expected_endpoint_each},{expected_endpoint_each}]",
            )
        left = _mean_or_fail(
            endpoint_totals[endpoint][0],
            endpoint_counts[endpoint][0],
            f"{endpoint} flat A",
        )
        right = _mean_or_fail(
            endpoint_totals[endpoint][1],
            endpoint_counts[endpoint][1],
            f"{endpoint} flat B",
        )
        common = (left + right) * 0.5
        endpoint_rms[endpoint] = float(
            np.sqrt(np.mean(common * common, dtype=np.float64))
        )

    thresholds = settings["held_out_validation"]
    checks = {
        "dark_count": dark_counts == [expected_dark_each, expected_dark_each],
        "flat_count": flat_counts == [expected_flat_each, expected_flat_each],
        "dark_common_rms": dark_rms
        <= float(thresholds["dark_common_rms_maximum_dn"]),
        "flat_common_rms": flat_rms
        <= float(thresholds["flat_common_rms_maximum_fraction"]),
        "flat_near_common_rms": endpoint_rms["near"]
        <= float(thresholds["flat_endpoint_common_rms_maximum_fraction"]),
        "flat_far_common_rms": endpoint_rms["far"]
        <= float(thresholds["flat_endpoint_common_rms_maximum_fraction"]),
        "dark_ring_coherence": dark_ring["maximum_positive_coherence"]
        <= float(thresholds["maximum_positive_ring_coherence"]),
        "flat_ring_coherence": flat_ring["maximum_positive_coherence"]
        <= float(thresholds["maximum_positive_ring_coherence"]),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "dark": {
            "split_counts": dark_counts,
            "common_rms_dn": dark_rms,
            "ring": dark_ring,
        },
        "flat": {
            "split_counts": flat_counts,
            "common_rms_fraction": flat_rms,
            "endpoint_common_rms_fraction": endpoint_rms,
            "ring": flat_ring,
        },
        "thresholds": thresholds,
    }


def _decode_record(
    record: dict[str, Any],
    capture: dict[str, Any],
) -> dict[str, Any]:
    np, rawpy = converter.import_runtime()
    source = Path(record["resolved_path"])
    camera = converter.read_camera_metadata(source)
    converter._validate_camera_match(camera, capture["camera_match"], source)
    with rawpy.imread(str(source)) as raw:
        fingerprint = converter.sensor_fingerprint(raw)
        if fingerprint != capture["sensor_fingerprint"]:
            raise converter.ContractFailure(
                "PATTERN_CAPTURE_SENSOR_MISMATCH",
                f"sensor fingerprint differs for {source}",
            )
        raw_values = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True)
        colors = np.array(raw.raw_colors_visible, dtype=np.uint8, copy=True)
        black = np.asarray(raw.black_level_per_channel, dtype=np.float64)
        camera_whites = raw.camera_white_level_per_channel
        white = np.asarray(
            camera_whites if camera_whites else [int(raw.white_level)] * 4,
            dtype=np.float64,
        )
    return {
        **record,
        "raw": raw_values,
        "colors": colors,
        "black_levels": black,
        "white_levels": white,
    }


def _group_stream(
    capture: dict[str, Any], group_name: str
) -> Iterator[dict[str, Any]]:
    for record in capture["groups"][group_name]:
        yield _decode_record(record, capture)


def _npy_bytes(array: Any) -> bytes:
    np, _ = converter.import_runtime()
    output = io.BytesIO()
    np.lib.format.write_array(output, np.asarray(array), allow_pickle=False)
    return output.getvalue()


def write_deterministic_npz(path: Path, gain: Any, offset_dn: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    with zipfile.ZipFile(partial, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, value in (("gain.npy", gain), ("offset_dn.npy", offset_dn)):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, _npy_bytes(value))
    os.replace(partial, path)


def _relative(from_path: Path, target: Path) -> str:
    return os.path.relpath(target.resolve(), from_path.parent.resolve())


def _source_hashes(
    capture: dict[str, Any], group_name: str, start: int = 0
) -> list[str]:
    return [record["sha256"] for record in capture["groups"][group_name][start:]]


def _map_manifest(
    manifest_path: Path,
    map_path: Path,
    lineage: str,
    capture: dict[str, Any],
    freeze_path: Path,
    freeze: dict[str, Any],
    settings_path: Path,
    settings: dict[str, Any],
    validation_path: Path,
) -> dict[str, Any]:
    dark_group = f"dark_{lineage.lower()}"
    flat_group = f"flat_{lineage.lower()}"
    excluded = int(settings["capture_counts"]["dark_settling_frames_excluded"])
    return {
        "schema": converter.PATTERN_SCHEMA,
        "status": "FROZEN",
        "map_id": (
            f"{capture['session_id']}:{capture['optical_state_id']}:"
            f"{capture['temperature_class']['id']}:"
            f"{capture['focus_class']['id']}:{lineage}"
        ),
        "session_id": capture["session_id"],
        "optical_state_id": capture["optical_state_id"],
        "lineage_id": lineage,
        "capture_manifest_sha256": capture["manifest_sha256"],
        "physical_body": {
            "id": capture["physical_body"]["id"],
            "witness_sha256": capture["physical_body"]["witness_sha256"],
        },
        "capture_record_sha256": capture["capture_record_sha256"],
        "flat_field_record_sha256": capture["flat_field_record_sha256"],
        "capture_match": capture["camera_match"],
        "temperature_class": {
            "id": capture["temperature_class"]["id"],
            "center_c": capture["temperature_class"]["center_c"],
            "center_sample_index": capture["temperature_class"][
                "center_sample_index"
            ],
            "maximum_absolute_delta_c": capture["temperature_class"][
                "maximum_absolute_delta_c"
            ],
            "interpolation": "forbidden",
            "witness": {
                "kind": capture["temperature_class"]["witness"]["kind"],
                "device_id": capture["temperature_class"]["witness"]["device_id"],
                "mount_location": capture["temperature_class"]["witness"][
                    "mount_location"
                ],
                "calibration_sha256": capture["temperature_class"]["witness"][
                    "calibration_sha256"
                ],
                "maximum_calibration_uncertainty_c": capture[
                    "temperature_class"
                ]["witness"]["maximum_calibration_uncertainty_c"],
                "log_sha256": capture["temperature_class"]["witness"]["log_sha256"],
                "maximum_sample_age_s": capture["temperature_class"]["witness"][
                    "maximum_sample_age_s"
                ],
            },
        },
        "focus_class": {
            "id": capture["focus_class"]["id"],
            "schedule_sha256": capture["focus_class"]["schedule_sha256"],
            "domain_normalized": capture["focus_class"]["domain_normalized"],
            "fit_position_normalized": capture["focus_class"][
                "fit_position_normalized"
            ],
            "fit_position_abs_tolerance": capture["focus_class"][
                "fit_position_abs_tolerance"
            ],
            "validation_endpoint_abs_tolerance": capture["focus_class"][
                "validation_endpoint_abs_tolerance"
            ],
            "interpolation": "forbidden",
        },
        "sensor_fingerprint": capture["sensor_fingerprint"],
        "active_shape": capture["sensor_fingerprint"]["active_shape"],
        "semantics": (
            "corrected = black + clip((raw - black - offset_dn) * gain, "
            "0, white - black)"
        ),
        "arrays": {
            "gain": {
                "dtype": "float32",
                "shape": capture["sensor_fingerprint"]["active_shape"],
            },
            "offset_dn": {
                "dtype": "float32",
                "shape": capture["sensor_fingerprint"]["active_shape"],
            },
        },
        "map_npz_sha256": converter.hash_file(map_path),
        "estimator": {
            "id": ESTIMATOR_ID,
            "version": ESTIMATOR_VERSION,
            "executable_sha256": freeze["estimator"]["executable_bundle_sha256"],
            "freeze_path": _relative(manifest_path, freeze_path),
            "freeze_sha256": converter.hash_file(freeze_path),
            "settings_path": _relative(manifest_path, settings_path),
            "settings_sha256": converter.hash_file(settings_path),
        },
        "independent_dark_source_sha256": _source_hashes(
            capture, dark_group, excluded
        ),
        "excluded_settling_dark_source_sha256": _source_hashes(
            capture, dark_group
        )[:excluded],
        "independent_flat_source_sha256": _source_hashes(capture, flat_group),
        "held_out_validation": {
            "result_path": _relative(manifest_path, validation_path),
            "result_sha256": converter.hash_file(validation_path),
            "dark_source_sha256": _source_hashes(
                capture, "dark_v", excluded
            ),
            "flat_source_sha256": _source_hashes(capture, "flat_v"),
            "thresholds": settings["held_out_validation"],
        },
    }


def estimate_capture(args: argparse.Namespace) -> dict[str, Any]:
    settings_path = Path(args.settings)
    freeze_path = Path(args.freeze)
    capture_path = Path(args.capture_manifest)
    output = Path(args.output_dir)
    settings = load_settings(settings_path)
    freeze = verify_freeze(freeze_path, settings_path)
    capture = validate_capture_manifest(capture_path, settings)
    offset_a = estimate_dark(_group_stream(capture, "dark_a"), settings)
    offset_b = estimate_dark(_group_stream(capture, "dark_b"), settings)
    gain_a, quality_a = estimate_gain(
        _group_stream(capture, "flat_a"), offset_a, settings
    )
    gain_b, quality_b = estimate_gain(
        _group_stream(capture, "flat_b"), offset_b, settings
    )
    map_a = {"gain": gain_a, "offset_dn": offset_a}
    map_b = {"gain": gain_b, "offset_dn": offset_b}
    validation = validate_maps(
        _group_stream(capture, "dark_v"),
        _group_stream(capture, "flat_v"),
        map_a,
        map_b,
        settings,
    )
    output.mkdir(parents=True, exist_ok=True)
    map_a_path = output / "map-A.npz"
    map_b_path = output / "map-B.npz"
    write_deterministic_npz(map_a_path, gain_a, offset_a)
    write_deterministic_npz(map_b_path, gain_b, offset_b)
    validation_path = output / "validation.json"
    validation_record = {
        "schema": VALIDATION_SCHEMA,
        "status": validation["status"],
        "session_id": capture["session_id"],
        "optical_state_id": capture["optical_state_id"],
        "physical_body_id": capture["physical_body"]["id"],
        "temperature_class_id": capture["temperature_class"]["id"],
        "focus_class_id": capture["focus_class"]["id"],
        "capture_manifest_sha256": capture["manifest_sha256"],
        "flat_field_record_sha256": capture["flat_field_record_sha256"],
        "estimator_executable_sha256": freeze["estimator"][
            "executable_bundle_sha256"
        ],
        "settings_sha256": converter.hash_file(settings_path),
        "held_out_dark_source_sha256": _source_hashes(
            capture,
            "dark_v",
            int(settings["capture_counts"]["dark_settling_frames_excluded"]),
        ),
        "held_out_flat_source_sha256": _source_hashes(capture, "flat_v"),
        "maps": {
            "A": {"path": str(map_a_path.resolve()), "sha256": converter.hash_file(map_a_path)},
            "B": {"path": str(map_b_path.resolve()), "sha256": converter.hash_file(map_b_path)},
        },
        "fit_quality": {"A": quality_a, "B": quality_b},
        **validation,
    }
    converter.write_json(validation_path, validation_record)
    if validation["status"] != "PASS":
        raise converter.ContractFailure(
            "PATTERN_MAP_VALIDATION_FAILED",
            "held-out V block rejected the fitted A/B map pair",
        )
    manifest_a_path = output / "map-A.manifest.json"
    manifest_b_path = output / "map-B.manifest.json"
    converter.write_json(
        manifest_a_path,
        _map_manifest(
            manifest_a_path,
            map_a_path,
            "A",
            capture,
            freeze_path,
            freeze,
            settings_path,
            settings,
            validation_path,
        ),
    )
    converter.write_json(
        manifest_b_path,
        _map_manifest(
            manifest_b_path,
            map_b_path,
            "B",
            capture,
            freeze_path,
            freeze,
            settings_path,
            settings,
            validation_path,
        ),
    )
    package = {
        "schema": PACKAGE_SCHEMA,
        "status": "FROZEN",
        "capture_manifest_path": str(capture_path.resolve()),
        "capture_manifest_sha256": capture["manifest_sha256"],
        "estimator_executable_sha256": freeze["estimator"][
            "executable_bundle_sha256"
        ],
        "settings_sha256": converter.hash_file(settings_path),
        "validation_path": str(validation_path.resolve()),
        "validation_sha256": converter.hash_file(validation_path),
        "maps": {
            "A": {
                "path": str(map_a_path.resolve()),
                "sha256": converter.hash_file(map_a_path),
                "manifest_path": str(manifest_a_path.resolve()),
                "manifest_sha256": converter.hash_file(manifest_a_path),
            },
            "B": {
                "path": str(map_b_path.resolve()),
                "sha256": converter.hash_file(map_b_path),
                "manifest_path": str(manifest_b_path.resolve()),
                "manifest_sha256": converter.hash_file(manifest_b_path),
            },
        },
    }
    converter.write_json(output / "package.json", package)
    return package


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _caught(call: Callable[[], Any]) -> dict[str, Any]:
    try:
        call()
    except BaseException as exc:
        return failure_record(exc, PACKAGE_SCHEMA)
    return {"schema": PACKAGE_SCHEMA, "status": "PASS"}


def _commission_contract(
    output: Path,
    settings_path: Path,
    freeze_path: Path,
    settings: dict[str, Any],
    freeze: dict[str, Any],
) -> dict[str, Any]:
    np, _ = converter.import_runtime()
    work = output / "_contract-work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    try:
        session_id = "m165-synthetic-stage0m"
        optical_state = "converter-on"
        body_id = "m165-synthetic-body"
        temperature_id = f"{session_id}:{optical_state}:temperature"
        focus_id = f"{session_id}:{optical_state}:focus"
        timestamp_0 = "2026-09-04T12:00:00+00:00"
        timestamp_1 = "2026-09-04T12:00:01+00:00"

        body_path = work / "body-witness.json"
        converter.write_json(
            body_path,
            {
                "schema": "m165-physical-body-witness-v1",
                "status": "FROZEN",
                "physical_body_id": body_id,
                "observation_method": "synthetic-commission",
                "evidence_sha256": converter.hash_bytes(
                    b"m165 synthetic body identifier"
                ),
                "recorded_at_utc": timestamp_0,
                "recorder": "M165 synthetic fixture",
            },
        )
        body_sha = converter.hash_file(body_path)
        capture_record_path = work / "capture-record.json"
        expected_camera = _camera_match_for(settings, optical_state)
        capture_state = {
            key: expected_camera[key]
            for key in ("raw_mode", "shutter_mode", "steadyshot", "lens_oss")
        }
        converter.write_json(
            capture_record_path,
            {
                "schema": "m165-physical-capture-record-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": optical_state,
                "physical_body_id": body_id,
                **capture_state,
                "camera_power_continuous": True,
                "dark_lens_capped_and_light_sealed": True,
                "lens_and_converter_identity": "synthetic converter-on optic",
                "aperture_marking": "f/5.6",
                "operator_recorded_at_utc": timestamp_0,
            },
        )
        capture_record_sha = converter.hash_file(capture_record_path)
        flat_field_record_path = work / "flat-field-record.json"
        converter.write_json(
            flat_field_record_path,
            {
                "schema": "m165-flat-field-state-record-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": optical_state,
                "states": {
                    group_name: {
                        "state_id": f"{session_id}:{optical_state}:{group_name}",
                        "diffuser_moved_or_rotated_since_previous": index > 0,
                        "spatially_uniform_unresolved_field_verified": True,
                        "recorded_at_utc": timestamp_0,
                    }
                    for index, group_name in enumerate(
                        ("flat_a", "flat_b", "flat_v")
                    )
                },
            },
        )
        flat_field_record_sha = converter.hash_file(flat_field_record_path)
        calibration_path = work / "temperature-calibration.json"
        converter.write_json(
            calibration_path,
            {
                "schema": "m165-temperature-probe-calibration-v1",
                "status": "FROZEN",
                "device_id": "m165-synthetic-probe",
                "calibrated_at_utc": timestamp_0,
                "reference": "synthetic exact reference",
                "uncertainty_c": 0.1,
            },
        )
        calibration_sha = converter.hash_file(calibration_path)
        log_path = work / "temperature-log.json"
        converter.write_json(
            log_path,
            {
                "schema": "m165-temperature-log-v1",
                "status": "FROZEN",
                "device_id": "m165-synthetic-probe",
                "mount_location": "synthetic-fixed-body-location",
                "unit": "celsius",
                "samples": [
                    {"timestamp_utc": timestamp_0, "temperature_c": 20.0},
                    {"timestamp_utc": timestamp_1, "temperature_c": 20.6},
                ],
            },
        )
        log_sha = converter.hash_file(log_path)
        schedule_path = work / "focus-schedule.json"
        converter.write_json(
            schedule_path,
            {
                "schema": "m165-focus-schedule-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": optical_state,
                "focus_class_id": focus_id,
                "coordinate": "normalized-registered-schedule-position",
                "domain": [0.0, 1.0],
                "direction": "0-to-1",
                "reset_method": "synthetic-fixed-reset",
                "fit_position_normalized": 0.5,
                "validation_endpoint_positions": [0.0, 1.0],
                "subject_positions_normalized": [0.0, 0.5, 1.0],
            },
        )
        schedule_sha = converter.hash_file(schedule_path)
        sensor = {
            "active_shape": [8, 10],
            "raw_shape": [10, 12],
            "black_levels": [512, 512, 512, 512],
            "white_levels": [15360, 15360, 15360, 15360],
            "raw_pattern": [[0, 1], [3, 2]],
            "color_description": "RGBG",
        }

        groups: dict[str, list[dict[str, Any]]] = {}
        for group in GROUPS:
            records = []
            for index in range(32):
                focus_position: float | None = None
                if group in {"flat_a", "flat_b"}:
                    focus_position = 0.5
                elif group == "flat_v":
                    focus_position = 0.0 if index < 16 else 1.0
                records.append(
                    {
                        "path": f"synthetic-{group}-{index:02d}.ARW",
                        "sha256": converter.hash_bytes(
                            f"m165:{group}:{index}".encode("ascii")
                        ),
                        "capture_index": index,
                        "captured_at_utc": timestamp_0,
                        "temperature_sample_index": 0,
                        "focus_position_normalized": focus_position,
                    }
                )
            groups[group] = records
        capture_manifest = {
            "schema": CAPTURE_SCHEMA,
            "status": "FROZEN",
            "session_id": session_id,
            "optical_state_id": optical_state,
            "physical_body": {
                "id": body_id,
                "witness_kind": "m165-physical-body-witness-v1",
                "witness_path": body_path.name,
                "witness_sha256": body_sha,
            },
            "capture_record": {
                "path": capture_record_path.name,
                "sha256": capture_record_sha,
            },
            "flat_field_record": {
                "path": flat_field_record_path.name,
                "sha256": flat_field_record_sha,
            },
            "camera_match": expected_camera,
            "temperature_class": {
                "id": temperature_id,
                "center_c": 20.0,
                "center_sample_index": 0,
                "maximum_absolute_delta_c": 0.5,
                "interpolation": "forbidden",
                "witness": {
                    "kind": "external-contact-probe",
                    "device_id": "m165-synthetic-probe",
                    "mount_location": "synthetic-fixed-body-location",
                    "calibration_path": calibration_path.name,
                    "calibration_sha256": calibration_sha,
                    "maximum_calibration_uncertainty_c": 0.2,
                    "log_path": log_path.name,
                    "log_sha256": log_sha,
                    "maximum_sample_age_s": 10.0,
                },
            },
            "focus_class": {
                "id": focus_id,
                "schedule_path": schedule_path.name,
                "schedule_sha256": schedule_sha,
                "domain_normalized": [0.0, 1.0],
                "fit_position_normalized": 0.5,
                "fit_position_abs_tolerance": 0.05,
                "validation_endpoint_abs_tolerance": 0.05,
                "interpolation": "forbidden",
            },
            "sensor_fingerprint": sensor,
            "groups": groups,
        }
        capture_path = work / "capture-manifest.json"
        converter.write_json(capture_path, capture_manifest)
        capture = validate_capture_manifest(
            capture_path, settings, verify_source_hashes=False
        )

        tc0_capture_record_path = work / "capture-record-tc0.json"
        tc0_camera = _camera_match_for(settings, "tc0")
        converter.write_json(
            tc0_capture_record_path,
            {
                "schema": "m165-physical-capture-record-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": "tc0",
                "physical_body_id": body_id,
                **{
                    key: tc0_camera[key]
                    for key in (
                        "raw_mode",
                        "shutter_mode",
                        "steadyshot",
                        "lens_oss",
                    )
                },
                "camera_power_continuous": True,
                "dark_lens_capped_and_light_sealed": True,
                "lens_and_converter_identity": "synthetic tc0 optic",
                "aperture_marking": "f/5.6",
                "operator_recorded_at_utc": timestamp_0,
            },
        )
        tc0_flat_field_record_path = work / "flat-field-record-tc0.json"
        converter.write_json(
            tc0_flat_field_record_path,
            {
                "schema": "m165-flat-field-state-record-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": "tc0",
                "states": {
                    group_name: {
                        "state_id": f"{session_id}:tc0:{group_name}",
                        "diffuser_moved_or_rotated_since_previous": index > 0,
                        "spatially_uniform_unresolved_field_verified": True,
                        "recorded_at_utc": timestamp_0,
                    }
                    for index, group_name in enumerate(
                        ("flat_a", "flat_b", "flat_v")
                    )
                },
            },
        )
        tc0_focus_id = f"{session_id}:tc0:focus"
        tc0_schedule_path = work / "focus-schedule-tc0.json"
        converter.write_json(
            tc0_schedule_path,
            {
                "schema": "m165-focus-schedule-v1",
                "status": "FROZEN",
                "session_id": session_id,
                "optical_state_id": "tc0",
                "focus_class_id": tc0_focus_id,
                "coordinate": "normalized-registered-schedule-position",
                "domain": [0.0, 1.0],
                "direction": "0-to-1",
                "reset_method": "synthetic-fixed-reset",
                "fit_position_normalized": 0.5,
                "validation_endpoint_positions": [0.0, 1.0],
                "subject_positions_normalized": [0.0, 0.5, 1.0],
            },
        )
        tc0_manifest = _copy_json(capture_manifest)
        tc0_manifest["optical_state_id"] = "tc0"
        tc0_manifest["camera_match"] = tc0_camera
        tc0_manifest["capture_record"] = {
            "path": tc0_capture_record_path.name,
            "sha256": converter.hash_file(tc0_capture_record_path),
        }
        tc0_manifest["flat_field_record"] = {
            "path": tc0_flat_field_record_path.name,
            "sha256": converter.hash_file(tc0_flat_field_record_path),
        }
        tc0_manifest["temperature_class"]["id"] = (
            f"{session_id}:tc0:temperature"
        )
        tc0_manifest["focus_class"].update(
            {
                "id": tc0_focus_id,
                "schedule_path": tc0_schedule_path.name,
                "schedule_sha256": converter.hash_file(tc0_schedule_path),
            }
        )
        for group_name, records in tc0_manifest["groups"].items():
            for record in records:
                record["sha256"] = converter.hash_bytes(
                    f"m165:tc0:{group_name}:{record['capture_index']}".encode(
                        "ascii"
                    )
                )
        tc0_capture_path = work / "capture-manifest-tc0.json"
        converter.write_json(tc0_capture_path, tc0_manifest)
        validate_capture_manifest(
            tc0_capture_path, settings, verify_source_hashes=False
        )
        sitting_manifest = {
            "schema": SITTING_SCHEMA,
            "status": "FROZEN",
            "session_id": session_id,
            "settings_sha256": converter.hash_file(settings_path),
            "classes": [
                {
                    "optical_state_id": optical_state,
                    "temperature_class_id": temperature_id,
                    "focus_class_id": focus_id,
                    "capture_manifest_path": capture_path.name,
                    "capture_manifest_sha256": converter.hash_file(capture_path),
                },
                {
                    "optical_state_id": "tc0",
                    "temperature_class_id": f"{session_id}:tc0:temperature",
                    "focus_class_id": tc0_focus_id,
                    "capture_manifest_path": tc0_capture_path.name,
                    "capture_manifest_sha256": converter.hash_file(
                        tc0_capture_path
                    ),
                },
            ],
        }
        sitting_path = work / "sitting-manifest.json"
        converter.write_json(sitting_path, sitting_manifest)
        sitting = validate_sitting_manifest(
            sitting_path, settings_path, settings, verify_source_hashes=False
        )
        missing_class_sitting = _copy_json(sitting_manifest)
        missing_class_sitting["classes"].pop()
        missing_class_path = work / "sitting-missing-class.json"
        converter.write_json(missing_class_path, missing_class_sitting)
        sitting_cardinality_refusal = _caught(
            lambda: validate_sitting_manifest(
                missing_class_path,
                settings_path,
                settings,
                verify_source_hashes=False,
            )
        )
        shared_source_capture = _copy_json(tc0_manifest)
        shared_source_capture["groups"]["dark_a"][0]["sha256"] = capture_manifest[
            "groups"
        ]["dark_a"][0]["sha256"]
        shared_source_capture_path = work / "capture-tc0-shared-source.json"
        converter.write_json(shared_source_capture_path, shared_source_capture)
        shared_source_sitting = _copy_json(sitting_manifest)
        shared_source_sitting["classes"][1].update(
            {
                "capture_manifest_path": shared_source_capture_path.name,
                "capture_manifest_sha256": converter.hash_file(
                    shared_source_capture_path
                ),
            }
        )
        shared_source_sitting_path = work / "sitting-shared-source.json"
        converter.write_json(shared_source_sitting_path, shared_source_sitting)
        sitting_source_refusal = _caught(
            lambda: validate_sitting_manifest(
                shared_source_sitting_path,
                settings_path,
                settings,
                verify_source_hashes=False,
            )
        )

        def capture_variant(name: str, value: dict[str, Any]) -> dict[str, Any]:
            variant_path = work / f"capture-{name}.json"
            converter.write_json(variant_path, value)
            return _caught(
                lambda: validate_capture_manifest(
                    variant_path, settings, verify_source_hashes=False
                )
            )

        wrong_body = _copy_json(capture_manifest)
        wrong_body["physical_body"]["id"] = "another-body"
        body_refusal = capture_variant("wrong-body", wrong_body)
        wrong_temperature = _copy_json(capture_manifest)
        wrong_temperature["groups"]["dark_v"][7].update(
            {
                "captured_at_utc": timestamp_1,
                "temperature_sample_index": 1,
            }
        )
        temperature_refusal = capture_variant(
            "wrong-temperature", wrong_temperature
        )
        wrong_focus = _copy_json(capture_manifest)
        wrong_focus["groups"]["flat_a"][0]["focus_position_normalized"] = 0.6
        focus_refusal = capture_variant("wrong-focus", wrong_focus)
        wrong_count = _copy_json(capture_manifest)
        wrong_count["groups"]["dark_b"].pop()
        count_refusal = capture_variant("wrong-count", wrong_count)
        invalid_flat_field_path = work / "flat-field-record-invalid.json"
        invalid_flat_field = converter.load_json(
            flat_field_record_path, "flat-field state record"
        )
        invalid_flat_field["states"]["flat_b"][
            "diffuser_moved_or_rotated_since_previous"
        ] = False
        converter.write_json(invalid_flat_field_path, invalid_flat_field)
        wrong_flat_field = _copy_json(capture_manifest)
        wrong_flat_field["flat_field_record"] = {
            "path": invalid_flat_field_path.name,
            "sha256": converter.hash_file(invalid_flat_field_path),
        }
        flat_field_refusal = capture_variant(
            "wrong-flat-field", wrong_flat_field
        )

        malformed_path = work / "capture-malformed.json"
        malformed_path.write_text("{", encoding="utf-8")
        malformed_report_path = work / "capture-malformed-report.json"
        malformed_process = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "validate-capture",
                "--settings",
                str(settings_path.resolve()),
                "--capture-manifest",
                str(malformed_path.resolve()),
                "--out",
                str(malformed_report_path.resolve()),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        malformed_report = converter.load_json(
            malformed_report_path, "malformed capture report"
        )

        gain_a = np.ones(sensor["active_shape"], dtype=np.float32)
        gain_b = gain_a.copy()
        gain_b[0, 0] = np.float32(1.0001)
        offset = np.zeros(sensor["active_shape"], dtype=np.float32)
        map_a_path = work / "map-A.npz"
        map_b_path = work / "map-B.npz"
        write_deterministic_npz(map_a_path, gain_a, offset)
        write_deterministic_npz(map_b_path, gain_b, offset)
        validation_path = work / "validation.json"
        validation_record = {
            "schema": VALIDATION_SCHEMA,
            "status": "PASS",
            "session_id": session_id,
            "optical_state_id": optical_state,
            "physical_body_id": body_id,
            "temperature_class_id": temperature_id,
            "focus_class_id": focus_id,
            "capture_manifest_sha256": capture["manifest_sha256"],
            "flat_field_record_sha256": capture[
                "flat_field_record_sha256"
            ],
            "estimator_executable_sha256": freeze["estimator"][
                "executable_bundle_sha256"
            ],
            "settings_sha256": converter.hash_file(settings_path),
            "held_out_dark_source_sha256": _source_hashes(capture, "dark_v", 2),
            "held_out_flat_source_sha256": _source_hashes(capture, "flat_v"),
            "maps": {
                "A": {
                    "path": str(map_a_path.resolve()),
                    "sha256": converter.hash_file(map_a_path),
                },
                "B": {
                    "path": str(map_b_path.resolve()),
                    "sha256": converter.hash_file(map_b_path),
                },
            },
            "fit_quality": {"A": {}, "B": {}},
            "checks": {"synthetic_contract_fixture": True},
            "dark": {},
            "flat": {},
            "thresholds": settings["held_out_validation"],
        }
        converter.write_json(validation_path, validation_record)
        map_a_manifest_path = work / "map-A.manifest.json"
        map_a_manifest = _map_manifest(
            map_a_manifest_path,
            map_a_path,
            "A",
            capture,
            freeze_path,
            freeze,
            settings_path,
            settings,
            validation_path,
        )
        converter.write_json(map_a_manifest_path, map_a_manifest)

        source_sha = converter.hash_bytes(b"m165 synthetic subject source")
        context = {
            "schema": converter.SOURCE_CONTEXT_SCHEMA,
            "status": "FROZEN",
            "source_sha256": source_sha,
            "captured_at_utc": timestamp_0,
            "session_id": session_id,
            "optical_state_id": optical_state,
            "lineage_id": "A",
            "physical_body": {
                "id": body_id,
                "witness_kind": "m165-physical-body-witness-v1",
                "witness_path": body_path.name,
                "witness_sha256": body_sha,
            },
            "capture_record_path": capture_record_path.name,
            "capture_record_sha256": capture_record_sha,
            "capture_state": capture_state,
            "temperature_witness": {
                "class_id": temperature_id,
                "device_id": "m165-synthetic-probe",
                "mount_location": "synthetic-fixed-body-location",
                "calibration_path": calibration_path.name,
                "calibration_sha256": calibration_sha,
                "log_path": log_path.name,
                "log_sha256": log_sha,
                "sample_index": 0,
                "sample_temperature_c": 20.0,
                "sample_age_s": 0.0,
            },
            "focus_state": {
                "class_id": focus_id,
                "schedule_path": schedule_path.name,
                "schedule_sha256": schedule_sha,
                "position_normalized": 0.5,
            },
        }
        context_path = work / "source-context.json"
        converter.write_json(context_path, context)
        normalized_context = converter.validate_source_context(
            context_path, source_sha
        )

        class SyntheticSizes:
            raw_height = 10
            raw_width = 12

        class SyntheticRaw:
            raw_image_visible = np.zeros(sensor["active_shape"], dtype=np.uint16)
            sizes = SyntheticSizes()
            black_level_per_channel = sensor["black_levels"]
            camera_white_level_per_channel = sensor["white_levels"]
            white_level = sensor["white_levels"][0]
            raw_pattern = np.asarray(sensor["raw_pattern"], dtype=np.uint8)
            color_desc = b"RGBG"

        raw = SyntheticRaw()
        baseline_map = _caught(
            lambda: converter.validate_pattern_manifest(
                map_a_manifest_path,
                map_a_path,
                raw,
                expected_camera,
                source_sha,
                Path("synthetic-subject.ARW"),
                normalized_context,
            )
        )

        alternate_body_path = work / "alternate-body-witness.json"
        converter.write_json(
            alternate_body_path,
            {
                "schema": "m165-physical-body-witness-v1",
                "status": "FROZEN",
                "physical_body_id": "another-body",
                "observation_method": "synthetic-commission",
                "evidence_sha256": converter.hash_bytes(
                    b"another synthetic body identifier"
                ),
                "recorded_at_utc": timestamp_0,
                "recorder": "M165 synthetic fixture",
            },
        )
        alternate_capture_record_path = work / "alternate-capture-record.json"
        converter.write_json(
            alternate_capture_record_path,
            {
                **converter.load_json(
                    capture_record_path, "physical capture record"
                ),
                "physical_body_id": "another-body",
            },
        )
        body_context = _copy_json(context)
        body_context["physical_body"] = {
            "id": "another-body",
            "witness_kind": "m165-physical-body-witness-v1",
            "witness_path": alternate_body_path.name,
            "witness_sha256": converter.hash_file(alternate_body_path),
        }
        body_context["capture_record_path"] = alternate_capture_record_path.name
        body_context["capture_record_sha256"] = converter.hash_file(
            alternate_capture_record_path
        )
        body_context_path = work / "source-context-wrong-body.json"
        converter.write_json(body_context_path, body_context)
        normalized_body_context = converter.validate_source_context(
            body_context_path, source_sha
        )
        map_body_refusal = _caught(
            lambda: converter.validate_pattern_manifest(
                map_a_manifest_path,
                map_a_path,
                raw,
                expected_camera,
                source_sha,
                Path("synthetic-subject.ARW"),
                normalized_body_context,
            )
        )

        temperature_context = _copy_json(context)
        temperature_context["captured_at_utc"] = timestamp_1
        temperature_context["temperature_witness"].update(
            {
                "sample_index": 1,
                "sample_temperature_c": 20.6,
                "sample_age_s": 0.0,
            }
        )
        temperature_context_path = work / "source-context-wrong-temperature.json"
        converter.write_json(temperature_context_path, temperature_context)
        normalized_temperature_context = converter.validate_source_context(
            temperature_context_path, source_sha
        )
        map_temperature_refusal = _caught(
            lambda: converter.validate_pattern_manifest(
                map_a_manifest_path,
                map_a_path,
                raw,
                expected_camera,
                source_sha,
                Path("synthetic-subject.ARW"),
                normalized_temperature_context,
            )
        )

        alternate_schedule_path = work / "alternate-focus-schedule.json"
        alternate_schedule = converter.load_json(
            schedule_path, "focus schedule"
        )
        alternate_schedule["subject_positions_normalized"] = [
            0.0,
            0.25,
            0.5,
            1.0,
        ]
        converter.write_json(alternate_schedule_path, alternate_schedule)
        focus_context = _copy_json(context)
        focus_context["focus_state"].update(
            {
                "schedule_path": alternate_schedule_path.name,
                "schedule_sha256": converter.hash_file(alternate_schedule_path),
                "position_normalized": 0.25,
            }
        )
        focus_context_path = work / "source-context-wrong-focus.json"
        converter.write_json(focus_context_path, focus_context)
        normalized_focus_context = converter.validate_source_context(
            focus_context_path, source_sha
        )
        map_focus_refusal = _caught(
            lambda: converter.validate_pattern_manifest(
                map_a_manifest_path,
                map_a_path,
                raw,
                expected_camera,
                source_sha,
                Path("synthetic-subject.ARW"),
                normalized_focus_context,
            )
        )

        failed_validation_path = work / "validation-failed.json"
        failed_validation = _copy_json(validation_record)
        failed_validation["status"] = "FAIL"
        failed_validation["checks"]["synthetic_contract_fixture"] = False
        converter.write_json(failed_validation_path, failed_validation)
        failed_manifest_path = work / "map-A.failed-validation.manifest.json"
        converter.write_json(
            failed_manifest_path,
            _map_manifest(
                failed_manifest_path,
                map_a_path,
                "A",
                capture,
                freeze_path,
                freeze,
                settings_path,
                settings,
                failed_validation_path,
            ),
        )
        map_validation_refusal = _caught(
            lambda: converter.validate_pattern_manifest(
                failed_manifest_path,
                map_a_path,
                raw,
                expected_camera,
                source_sha,
                Path("synthetic-subject.ARW"),
                normalized_context,
            )
        )

        checks = {
            "capture_contract_passes": capture["session_id"] == session_id,
            "sitting_contract_passes": sitting["dark_temperature_class_count"]
            == 2
            and sitting["flat_focus_class_count"] == 2
            and sitting["fitted_map_count"] == 4,
            "sitting_cardinality_mismatch_refused": sitting_cardinality_refusal.get(
                "failure_class"
            )
            == "PATTERN_SITTING_CARDINALITY_MISMATCH",
            "sitting_shared_source_refused": sitting_source_refusal.get(
                "failure_class"
            )
            == "PATTERN_SITTING_SOURCES_NOT_INDEPENDENT",
            "body_mismatch_refused": body_refusal.get("failure_class")
            == "PHYSICAL_BODY_WITNESS_INVALID",
            "temperature_mismatch_refused": temperature_refusal.get(
                "failure_class"
            )
            == "PATTERN_CAPTURE_TEMPERATURE_MISMATCH",
            "focus_mismatch_refused": focus_refusal.get("failure_class")
            == "PATTERN_CAPTURE_FOCUS_MISMATCH",
            "count_mismatch_refused": count_refusal.get("failure_class")
            == "PATTERN_CAPTURE_COUNT_MISMATCH",
            "flat_field_lineage_mismatch_refused": flat_field_refusal.get(
                "failure_class"
            )
            == "PATTERN_CAPTURE_FLAT_FIELD_INVALID",
            "malformed_cli_degrades_to_fail": malformed_process.returncode != 0
            and malformed_report.get("status") == "FAIL",
            "map_contract_passes": baseline_map.get("status") == "PASS",
            "map_body_mismatch_refused": map_body_refusal.get("failure_class")
            == "PATTERN_MAP_BODY_MISMATCH",
            "map_temperature_mismatch_refused": map_temperature_refusal.get(
                "failure_class"
            )
            == "PATTERN_MAP_TEMPERATURE_MISMATCH",
            "map_focus_schedule_mismatch_refused": map_focus_refusal.get(
                "failure_class"
            )
            == "PATTERN_MAP_FOCUS_MISMATCH",
            "failed_held_out_result_refused": map_validation_refusal.get(
                "failure_class"
            )
            == "PATTERN_MAP_VALIDATION_FAILED",
        }
        return {
            "status": "PASS" if all(checks.values()) else "FAIL",
            "checks": checks,
            "baseline": {
                "capture_manifest_sha256": capture["manifest_sha256"],
                "sitting_manifest_sha256": sitting["manifest_sha256"],
                "dark_temperature_class_count": sitting[
                    "dark_temperature_class_count"
                ],
                "flat_focus_class_count": sitting["flat_focus_class_count"],
                "fitted_map_count": sitting["fitted_map_count"],
                "source_context_sha256": normalized_context["context_sha256"],
                "map_sha256": converter.hash_file(map_a_path),
                "map_validation": baseline_map,
            },
            "refusals": {
                "capture_body": body_refusal,
                "sitting_cardinality": sitting_cardinality_refusal,
                "sitting_shared_source": sitting_source_refusal,
                "capture_temperature": temperature_refusal,
                "capture_focus": focus_refusal,
                "capture_count": count_refusal,
                "capture_flat_field": flat_field_refusal,
                "malformed_cli": {
                    "exit_code": malformed_process.returncode,
                    "report": malformed_report,
                },
                "map_body": map_body_refusal,
                "map_temperature": map_temperature_refusal,
                "map_focus_schedule": map_focus_refusal,
                "map_held_out_result": map_validation_refusal,
            },
        }
    finally:
        if work.exists():
            shutil.rmtree(work)


def _synthetic_stream(
    group: str,
    offset_truth: Any,
    gain_truth: Any,
    settings: dict[str, Any],
    seed: int,
) -> Iterator[dict[str, Any]]:
    np, _ = converter.import_runtime()
    height, width = offset_truth.shape
    yy, xx = np.mgrid[0:height, 0:width]
    colors = ((yy & 1) * 2 + (xx & 1)).astype(np.uint8)
    black = np.asarray([512.0] * 4)
    white = np.asarray([15360.0] * 4)
    rng = np.random.default_rng(seed)
    count = 32
    is_flat = group.startswith("flat")
    for index in range(count):
        if is_flat:
            focus_u = 0.5
            if group == "flat_v":
                focus_u = 0.0 if index < 16 else 1.0
            focus_curve = (focus_u - 0.5) * 0.002 * (
                ((xx - width / 2) / width) ** 2
                + ((yy - height / 2) / height) ** 2
            )
            illumination = (
                10000.0
                * (1.0 + 0.002 * (xx / width - 0.5))
                * (1.0 + focus_curve)
            )
            noise = rng.normal(0.0, 47.0, size=(height, width))
            values = 512.0 + offset_truth + illumination / gain_truth + noise
        else:
            focus_u = None
            noise = rng.normal(0.0, 1.0, size=(height, width))
            values = 512.0 + offset_truth + noise
        yield {
            "capture_index": index,
            "focus_position_normalized": focus_u,
            "raw": np.clip(np.rint(values), 0, 65535).astype(np.uint16),
            "colors": colors,
            "black_levels": black,
            "white_levels": white,
            "sha256": converter.hash_bytes(f"{group}:{index}:{seed}".encode("ascii")),
        }


def _synthetic_arm(
    offset_truth: Any,
    gain_truth: Any,
    settings: dict[str, Any],
    maps: tuple[dict[str, Any], dict[str, Any]] | None,
    seed_base: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if maps is None:
        offset_a = estimate_dark(
            _synthetic_stream("dark_a", offset_truth, gain_truth, settings, seed_base),
            settings,
        )
        offset_b = estimate_dark(
            _synthetic_stream(
                "dark_b", offset_truth, gain_truth, settings, seed_base + 1
            ),
            settings,
        )
        gain_a, _ = estimate_gain(
            _synthetic_stream(
                "flat_a", offset_truth, gain_truth, settings, seed_base + 2
            ),
            offset_a,
            settings,
        )
        gain_b, _ = estimate_gain(
            _synthetic_stream(
                "flat_b", offset_truth, gain_truth, settings, seed_base + 3
            ),
            offset_b,
            settings,
        )
        map_a = {"gain": gain_a, "offset_dn": offset_a}
        map_b = {"gain": gain_b, "offset_dn": offset_b}
    else:
        map_a, map_b = maps
    validation = validate_maps(
        _synthetic_stream(
            "dark_v", offset_truth, gain_truth, settings, seed_base + 4
        ),
        _synthetic_stream(
            "flat_v", offset_truth, gain_truth, settings, seed_base + 5
        ),
        map_a,
        map_b,
        settings,
    )
    return map_a, map_b, validation


def commission(args: argparse.Namespace) -> dict[str, Any]:
    np, _ = converter.import_runtime()
    settings_path = Path(args.settings)
    freeze_path = Path(args.freeze)
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=True)
    settings = load_settings(settings_path)
    freeze = verify_freeze(freeze_path, settings_path)
    contract = _commission_contract(
        output, settings_path, freeze_path, settings, freeze
    )
    height = 1024
    width = 1024
    yy, xx = np.mgrid[0:height, 0:width]
    rng = np.random.default_rng(20260904)
    offset_truth = (
        2.0 * np.sin(2.0 * np.pi * xx / 17.0)
        + 1.5 * np.cos(2.0 * np.pi * yy / 23.0)
        + rng.normal(0.0, 0.35, size=(height, width))
    )
    gain_truth = (
        1.0
        + 0.006 * rng.normal(size=(height, width))
        + 0.002 * np.sin(2.0 * np.pi * (xx + yy) / 13.0)
    )
    zeros = np.zeros((height, width), dtype=np.float32)
    ones = np.ones((height, width), dtype=np.float32)
    identity = ({"gain": ones, "offset_dn": zeros}, {"gain": ones, "offset_dn": zeros})
    clean_null = _synthetic_arm(
        np.zeros_like(offset_truth),
        np.ones_like(gain_truth),
        settings,
        identity,
        1000,
    )[2]
    disturbed = _synthetic_arm(
        offset_truth, gain_truth, settings, identity, 2000
    )[2]
    map_a, map_b, improved = _synthetic_arm(
        offset_truth, gain_truth, settings, None, 3000
    )
    degraded_maps = (
        {
            "gain": np.asarray(2.0 - map_a["gain"], dtype=np.float32),
            "offset_dn": np.asarray(-map_a["offset_dn"], dtype=np.float32),
        },
        {
            "gain": np.asarray(2.0 - map_b["gain"], dtype=np.float32),
            "offset_dn": np.asarray(-map_b["offset_dn"], dtype=np.float32),
        },
    )
    degraded = _synthetic_arm(
        offset_truth, gain_truth, settings, degraded_maps, 3000
    )[2]
    map_a_path = output / "commission-map-A.npz"
    map_b_path = output / "commission-map-B.npz"
    write_deterministic_npz(
        map_a_path, map_a["gain"], map_a["offset_dn"]
    )
    write_deterministic_npz(
        map_b_path, map_b["gain"], map_b["offset_dn"]
    )
    checks = {
        "stage0m_contract_passes": contract["status"] == "PASS",
        "clean_null_passes": clean_null["status"] == "PASS",
        "null_moves_under_disturbance": disturbed["status"] == "FAIL"
        and disturbed["dark"]["common_rms_dn"]
        > clean_null["dark"]["common_rms_dn"]
        and disturbed["flat"]["common_rms_fraction"]
        > clean_null["flat"]["common_rms_fraction"],
        "planted_degradation_fails": degraded["status"] == "FAIL"
        and degraded["dark"]["common_rms_dn"]
        > disturbed["dark"]["common_rms_dn"]
        and degraded["flat"]["common_rms_fraction"]
        > disturbed["flat"]["common_rms_fraction"],
        "planted_improvement_passes": improved["status"] == "PASS"
        and improved["dark"]["common_rms_dn"]
        < disturbed["dark"]["common_rms_dn"]
        and improved["flat"]["common_rms_fraction"]
        < disturbed["flat"]["common_rms_fraction"],
        "map_files_are_distinct": converter.hash_file(map_a_path)
        != converter.hash_file(map_b_path),
    }
    report = {
        "schema": COMMISSION_SCHEMA,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "estimator": {
            "id": ESTIMATOR_ID,
            "version": ESTIMATOR_VERSION,
            "executable_sha256": freeze["estimator"]["executable_bundle_sha256"],
            "freeze_sha256": converter.hash_file(freeze_path),
            "settings_sha256": converter.hash_file(settings_path),
        },
        "synthetic_shape": [height, width],
        "checks": checks,
        "stage0m_contract": contract,
        "movable_null": {
            "clean": clean_null,
            "disturbed_without_correction": disturbed,
        },
        "planted_degradation": degraded,
        "planted_improvement": improved,
        "maps": {
            "A": {
                "path": str(map_a_path.resolve()),
                "sha256": converter.hash_file(map_a_path),
            },
            "B": {
                "path": str(map_b_path.resolve()),
                "sha256": converter.hash_file(map_b_path),
            },
        },
    }
    converter.write_json(output / "commission.json", report)
    return report


def failure_record(exc: BaseException, schema: str) -> dict[str, Any]:
    return converter.failure_record(exc, schema)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze")
    freeze.add_argument("--settings", required=True)
    freeze.add_argument("--out", required=True)
    validate = subparsers.add_parser("validate-capture")
    validate.add_argument("--settings", required=True)
    validate.add_argument("--capture-manifest", required=True)
    validate.add_argument("--out", required=True)
    validate_sitting = subparsers.add_parser("validate-sitting")
    validate_sitting.add_argument("--settings", required=True)
    validate_sitting.add_argument("--sitting-manifest", required=True)
    validate_sitting.add_argument("--out", required=True)
    estimate = subparsers.add_parser("estimate")
    estimate.add_argument("--settings", required=True)
    estimate.add_argument("--freeze", required=True)
    estimate.add_argument("--capture-manifest", required=True)
    estimate.add_argument("--output-dir", required=True)
    estimate.add_argument("--report", required=True)
    commissioned = subparsers.add_parser("commission")
    commissioned.add_argument("--settings", required=True)
    commissioned.add_argument("--freeze", required=True)
    commissioned.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path: Path | None = None
    schema = {
        "freeze": FREEZE_SCHEMA,
        "validate-capture": CAPTURE_SCHEMA,
        "validate-sitting": SITTING_SCHEMA,
        "estimate": PACKAGE_SCHEMA,
        "commission": COMMISSION_SCHEMA,
    }[args.command]
    try:
        if args.command == "freeze":
            report_path = Path(args.out)
            result = build_freeze(Path(args.settings))
            result["complete_freeze_invocation"] = [
                sys.executable,
                str(Path(__file__).resolve()),
            ] + sys.argv[1:]
            result["working_directory"] = str(Path.cwd())
            converter.write_json(report_path, result)
        elif args.command == "validate-capture":
            report_path = Path(args.out)
            settings = load_settings(Path(args.settings))
            capture = validate_capture_manifest(
                Path(args.capture_manifest), settings
            )
            result = {
                "schema": CAPTURE_SCHEMA,
                "status": "PASS",
                "manifest_path": capture["manifest_path"],
                "manifest_sha256": capture["manifest_sha256"],
                "session_id": capture["session_id"],
                "optical_state_id": capture["optical_state_id"],
                "physical_body_id": capture["physical_body"]["id"],
                "temperature_class_id": capture["temperature_class"]["id"],
                "focus_class_id": capture["focus_class"]["id"],
                "counts": {
                    name: len(capture["groups"][name]) for name in GROUPS
                },
            }
            converter.write_json(report_path, result)
        elif args.command == "validate-sitting":
            report_path = Path(args.out)
            settings_path = Path(args.settings)
            settings = load_settings(settings_path)
            sitting = validate_sitting_manifest(
                Path(args.sitting_manifest), settings_path, settings
            )
            result = {
                "schema": SITTING_SCHEMA,
                "status": "PASS",
                "manifest_path": sitting["manifest_path"],
                "manifest_sha256": sitting["manifest_sha256"],
                "session_id": sitting["session_id"],
                "dark_temperature_class_count": sitting[
                    "dark_temperature_class_count"
                ],
                "flat_focus_class_count": sitting["flat_focus_class_count"],
                "fitted_map_count": sitting["fitted_map_count"],
            }
            converter.write_json(report_path, result)
        elif args.command == "estimate":
            report_path = Path(args.report)
            result = estimate_capture(args)
            converter.write_json(report_path, result)
        elif args.command == "commission":
            report_path = Path(args.out) / "commission.json"
            result = commission(args)
        else:
            raise converter.ContractFailure(
                "PATTERN_ESTIMATOR_COMMAND_INVALID", str(args.command)
            )
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("status") in {"PASS", "FROZEN"} else 1
    except BaseException as exc:
        result = failure_record(exc, schema)
        if report_path is not None:
            try:
                converter.write_json(report_path, result)
            except BaseException as write_exc:
                result["report_write_failure"] = str(write_exc)
        print(json.dumps(result, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
