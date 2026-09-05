#!/usr/bin/env python3
"""Author commissioning plants for the M135 burned-slide instrument.

These are commissioning controls, not independent verification and not slide
measurements.  No capture path is opened.  Every load-bearing selector has a
named negative or mutation control in ``selector_coverage``.
"""

from __future__ import annotations

import argparse
import ast
import copy
import inspect
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path, PureWindowsPath
from typing import Any, Callable

import cv2
import numpy as np

import instrument as M


HERE = Path(__file__).resolve().parent
DEFAULT_CROSSCHECK_BINARY = (
    HERE
    / "target"
    / "release"
    / (
        "m135-slide-raw-crosscheck.exe"
        if sys.platform == "win32"
        else "m135-slide-raw-crosscheck"
    )
)


def gaussian_curve(n: int, peak: float, width: float = 0.08) -> np.ndarray:
    u = np.linspace(0.0, 1.0, n)
    return np.exp(-0.5 * ((u - peak) / width) ** 2) + 1e-8


def make_peak_set(
    n: int,
    mapping: Callable[[float, int], float],
    config: dict[str, Any],
) -> list[M.PeakEstimate]:
    base = np.linspace(0.16, 0.84, 64)
    return [
        M.estimate_peak(gaussian_curve(n, mapping(float(value), index)), config)
        for index, value in enumerate(base)
    ]


def synthetic_quad_image(
    shape: tuple[int, int] = (320, 400),
    quad: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if quad is None:
        quad = np.asarray(
            [[52.0, 42.0], [348.0, 55.0], [330.0, 278.0], [66.0, 264.0]],
            dtype=np.float32,
        )
    y, x = np.indices(shape, dtype=np.float32)
    image = 0.10 + 0.0006 * x + 0.0003 * y
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.rint(quad).astype(np.int32), 255)
    inside = mask > 0
    image[inside] += (
        0.75
        + 0.10 * np.sin(2.0 * np.pi * x[inside] / 117.0)
        + 0.08 * np.cos(2.0 * np.pi * y[inside] / 91.0)
    )
    image = cv2.GaussianBlur(image, (0, 0), 2.0)
    return image.astype(np.float32), quad.astype(np.float64)


def synthetic_registration_scene(shape: tuple[int, int] = (320, 400)) -> np.ndarray:
    y, x = np.indices(shape, dtype=np.float32)
    image = np.zeros(shape, dtype=np.float32)
    blobs = (
        (51.0, 63.0, 14.0, 1.0),
        (102.0, 310.0, 20.0, -0.8),
        (181.0, 127.0, 27.0, 1.2),
        (246.0, 292.0, 18.0, 0.7),
        (274.0, 67.0, 11.0, -0.9),
    )
    for cy, cx, sigma, amplitude in blobs:
        image += amplitude * np.exp(
            -0.5 * ((x - cx) ** 2 + (y - cy) ** 2) / sigma**2
        )
    image += 0.15 * np.sin(2.0 * np.pi * x / 83.0)
    return image.astype(np.float32)


def valid_role_fixture(
    config: dict[str, Any], matched_flat_manifest: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = config["roles"]["required_roles"]
    source_groups = {
        "R1": "flat-sw4-cpl",
        "R2": "flat-sw4-cpl",
        "sw4_Y1": "tilted-sw4-cpl",
        "sw4_Y2": "tilted-sw4-cpl",
        "sw10_Y1": "tilted-sw10-cpl",
        "sw10_Y2": "tilted-sw10-cpl",
        "flat_R1": "flat-sw4-cpl",
        "flat_R2": "flat-sw4-cpl",
        "sw4_flat_Y1": "flat-sw4-cpl",
        "sw4_flat_Y2": "flat-sw4-cpl",
        "sw10_flat_Y1": "flat-sw4-cpl",
        "sw10_flat_Y2": "flat-sw4-cpl",
    }
    inventory = {
        "stacks": {
            name: {"frames": [], "capture_units": []}
            for name in config["stacks"]
        }
    }
    assignments = {}
    for index, role in enumerate(required):
        reference = role in {"R1", "R2"}
        source_id = M.sha256_bytes(f"source-file-{index}".encode("ascii"))
        capture_unit = f"{source_groups[role]}\\unit-{index:02d}"
        inventory["stacks"][source_groups[role]]["frames"].append(
            {
                "raw_sha256": source_id,
                "relative_path": f"{capture_unit}\\frame-{index:02d}.ARW",
            }
        )
        assignments[role] = {
            "source_group": source_groups[role],
            "capture_unit_id": capture_unit,
            "parent_stack_id": capture_unit,
            "source_file_ids": [source_id],
            "geometry_id": "same-physical-sites",
            "subset": "all",
            "acquisition_kind": (
                "fixed-focus-reference" if reference else "focus-bracket"
            ),
            "flat_lineage_id": f"flat-lineage-{index}",
            "dark_lineage_id": f"dark-lineage-{index}",
            "subject_sampling_lcb95_px_per_object_unit": (
                2.1 if reference else 0.95
            ),
            "subject_sampling_ucb95_px_per_object_unit": (
                2.2 if reference else 1.0
            ),
        }
    for group in inventory["stacks"].values():
        group["capture_units"] = M.capture_units_from_frames(group["frames"])
    ledger = {
        "schema": "m135-slide-role-ledger-v1",
        "label": M.LABEL,
        "session_id": "synthetic-role-plant",
        "target": {
            "kind": "nonperiodic-random",
            "checker_template_available": False,
            "source_oracle_used": False,
            "same_physical_sites": True,
        },
        "site_count": 64,
        "matched_flat_evidence": True,
        "assignments": assignments,
        "flat_core_eligibility": {
            "lawful": True,
            "reason": None,
            "capture_unit_ids": [
                "flat-core-capture-0",
                "flat-core-capture-1",
                "flat-core-capture-2",
                "flat-core-capture-3"
            ],
            "parent_stack_ids": [
                "flat-core-parent-0",
                "flat-core-parent-1",
                "flat-core-parent-2",
                "flat-core-parent-3"
            ],
            "calibration_lineage_ids": [
                "flat-core-calibration-0",
                "flat-core-calibration-1",
                "flat-core-calibration-2",
                "flat-core-calibration-3"
            ],
            "target_kind": "nonperiodic-random",
            "featureless_source": True
        },
    }
    role_bindings = {
        role: {
            "capture_unit_id": row["capture_unit_id"],
            "parent_stack_id": row["parent_stack_id"],
            "source_group": row["source_group"],
            "source_file_ids": sorted(row["source_file_ids"]),
            "flat_lineage_id": row["flat_lineage_id"],
            "dark_lineage_id": row["dark_lineage_id"],
        }
        for role, row in assignments.items()
    }
    M.write_json(
        matched_flat_manifest,
        {
            "schema": "m135-matched-flat-evidence-v1",
            "status": "PASS",
            "lineage_ids": sorted(
                {
                    value
                    for row in assignments.values()
                    for value in (
                        row["flat_lineage_id"],
                        row["dark_lineage_id"],
                    )
                }
            ),
            "role_bindings": role_bindings,
        },
    )
    ledger["matched_flat_manifest_path"] = str(matched_flat_manifest.absolute())
    ledger["matched_flat_manifest_sha256"] = M.sha256_file(
        matched_flat_manifest
    )
    site_manifest = matched_flat_manifest.with_name("physical-sites.json")
    site_role_bindings = {
        role: {
            "capture_unit_id": assignments[role]["capture_unit_id"],
            "parent_stack_id": assignments[role]["parent_stack_id"],
            "source_group": assignments[role]["source_group"],
            "source_file_ids": sorted(assignments[role]["source_file_ids"]),
            "geometry_id": assignments[role]["geometry_id"],
        }
        for role in M.SAME_SITE_ROLES
    }
    sites = []
    for row in range(8):
        for column in range(8):
            site_id = f"site-{row:02d}-{column:02d}"
            coordinate = [(column + 0.5) / 8.0, (row + 0.5) / 8.0]
            sites.append(
                {
                    "site_id": site_id,
                    "normalized_slide_uv": coordinate,
                    "role_observations": {
                        role: {
                            "site_id": site_id,
                            "normalized_slide_uv": coordinate,
                        }
                        for role in M.SAME_SITE_ROLES
                    },
                }
            )
    M.write_json(
        site_manifest,
        {
            "schema": config["roles"]["site_manifest_schema"],
            "status": "PASS",
            "session_id": ledger["session_id"],
            "coordinate_system": config["roles"]["site_coordinate_system"],
            "roles": list(M.SAME_SITE_ROLES),
            "role_bindings": site_role_bindings,
            "sites": sites,
        },
    )
    ledger["site_manifest_path"] = str(site_manifest.absolute())
    ledger["site_manifest_sha256"] = M.sha256_file(site_manifest)
    return inventory, ledger


class Campaign:
    def __init__(self, config_path: Path, config: dict[str, Any]):
        self.config_path = config_path
        self.config = config
        self.checks: dict[str, bool] = {}
        self.plants: dict[str, Any] = {}

    def run(self, name: str, function: Callable[[], Any]) -> None:
        try:
            value = function()
            if isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], bool):
                passed, detail = value
            elif isinstance(value, bool):
                passed, detail = value, {"result": value}
            else:
                passed, detail = True, value
            self.checks[name] = bool(passed)
            self.plants[name] = detail
        except Exception as error:
            self.checks[name] = False
            self.plants[name] = {
                "error_type": type(error).__name__,
                "error": str(error),
            }

    def result(self) -> dict[str, Any]:
        selector_coverage = {
            "inventory-file-population-and-sort": [
                "inventory_hidden_file_and_sort_mutation",
                "inventory_unexpected_arw_control",
                "inventory_absolute_path_binding_control",
                "forged_coarse_encoder_control",
            ],
            "focusposition2-completeness-and-histogram": [
                "focus_histogram_missing_value_control",
                "empty_focus_histogram_control",
            ],
            "rawpy-buffer-lifetime": ["rawpy_copy_inside_context_static_control"],
            "active-area-not-padding": ["active_area_padding_control"],
            "independent-decoder-prefix": ["decoder_checksum_mutation_control"],
            "frozen-crosscheck-executable": [
                "crosscheck_binary_mismatch_control"
            ],
            "cargo-local-dependency-freeze": [
                "cargo_dependency_freeze_mutation_control"
            ],
            "python-native-runtime-freeze": [
                "python_native_runtime_closure_control"
            ],
            "decoder-stdout-no-write-transport": [
                "stdout_transport_no_write_control"
            ],
            "nonfinite-and-clipping-refusal": [
                "nonfinite_refusal_control",
                "clipping_refusal_control",
            ],
            "registration-lowpass-band": [
                "registration_stopband_control",
                "lowpass_registration_motion_control",
            ],
            "quadrilateral-choice-and-order": [
                "quadrilateral_identity_and_corner_mutation",
                "quadrilateral_ambiguity_control",
            ],
            "fixed-normalized-lattice": ["lattice_mutation_control"],
            "focus-band-cap": ["above_band_distractor_control"],
            "interior-peak-selector": ["endpoint_peak_control"],
            "joint-site-count": ["too_few_eligible_sites_control"],
            "robust-range-fit-bars": [
                "identity_range_control",
                "bad_offset_control",
                "bad_slope_control",
                "bad_residual_control",
                "nonconverged_fit_control",
            ],
            "role-ledger-identifiability": [
                "valid_role_fixture_passability",
                "missing_roles_no_jtr_control",
                "sw4_as_truth_control",
                "odd_even_independence_control",
                "all_axis_repeat_control",
                "shared_calibration_control",
                "shared_source_file_control",
                "invented_source_file_control",
                "flat_role_capture_unit_control",
                "flat_role_shared_calibration_control",
                "partial_source_group_control",
                "sampling_interval_control",
                "same_physical_sites_false_control",
                "bare_site_count_control",
                "duplicate_site_identity_control",
                "duplicate_site_coordinate_control",
                "missing_site_control",
                "site_coordinate_mismatch_control",
                "site_role_binding_control",
                "site_manifest_hash_control",
                "matched_flat_manifest_control",
                "matched_flat_role_binding_control",
                "checker_oracle_control",
            ],
            "artifact-chain-binding": [
                "summary_chain_splice_control",
                "forged_physical_binding_control",
                "forged_range_predicate_control",
                "forged_identifiable_predicate_control",
                "inventory_recompute_binding_control",
                "decode_recompute_binding_control",
                "range_recompute_binding_control",
                "flat_recompute_binding_control",
            ],
            "flat-ledger-binding": ["flat_ledger_binding_control"],
            "normalized-text-hash-domain": ["normalized_text_hash_control"],
            "flat-exposure-and-temporal-splits": [
                "three_exposure_group_control",
                "temporal_split_mutation_control",
            ],
            "flat-structure-selector": [
                "quiet_flat_control",
                "structured_flat_rejection_control",
                "alternating_sign_flat_rejection_control",
                "rotating_sign_flat_rejection_control",
                "one_pair_only_flat_rejection_control",
            ],
            "existing-m135-core-no-detail": ["lawful_core_no_detail_control"],
            "artifact-schema": ["artifact_schema_mutation_control"],
        }
        missing = [
            plant
            for plants in selector_coverage.values()
            for plant in plants
            if plant not in self.checks
        ]
        selector_checks = {
            selector: bool(
                plants
                and all(self.checks.get(plant, False) for plant in plants)
            )
            for selector, plants in selector_coverage.items()
        }
        self.checks["selector_coverage_complete"] = not missing and all(
            selector_checks.values()
        )
        self.plants["selector_coverage_complete"] = {
            "missing_plants": missing,
            "selectors": selector_checks,
        }
        status = "COMMISSIONED" if all(self.checks.values()) else "NOT_COMMISSIONED"
        payload = {
            "schema": "m135-slide-commission-v1",
            "label": M.LABEL,
            "status": status,
            "config_sha256": M.config_sha256(self.config_path),
            "invocation": M.invocation_record(self.config_path, self.config),
            "checks": self.checks,
            "plants": _round_diagnostic_floats(self.plants),
            "selector_coverage": selector_coverage,
            "claim_scope": (
                "author commissioning only; no authorized-session path opened "
                "and no independent verification claimed"
            ),
        }
        M.validate_artifact(payload)
        return payload


def _round_diagnostic_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, list):
        return [_round_diagnostic_floats(item) for item in value]
    if isinstance(value, tuple):
        return [_round_diagnostic_floats(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _round_diagnostic_floats(item)
            for key, item in value.items()
        }
    return value


def commission(
    config_path: Path,
    freeze_manifest_path: Path,
    crosscheck_binary: Path,
) -> dict[str, Any]:
    config = M.load_config(config_path)
    M.require_environment(config)
    campaign = Campaign(config_path, config)

    def inventory_sort_plant() -> tuple[bool, dict[str, Any]]:
        with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
            root = Path(raw_temp)
            files = [root / name for name in ("a.ARW", ".hidden.ARW", "z.ARW")]
            for index, path in enumerate(files):
                path.write_bytes(bytes([index + 1]))
            records = [
                {
                    "SourceFile": str(files[0]),
                    "FileName": files[0].name,
                    "Directory": str(root),
                    "SubSecDateTimeOriginal": "2026:09:02 20:00:00.300",
                    "FocusPosition2": 58,
                },
                {
                    "SourceFile": str(files[1]),
                    "FileName": files[1].name,
                    "Directory": str(root),
                    "SubSecDateTimeOriginal": "2026:09:02 20:00:00.100",
                    "FocusPosition2": 57,
                },
                {
                    "SourceFile": str(files[2]),
                    "FileName": files[2].name,
                    "Directory": str(root),
                    "SubSecDateTimeOriginal": "2026:09:02 20:00:00.200",
                    "FocusPosition2": 59,
                },
            ]
            merged = M.merge_exif_records(
                files, records, records, "synthetic", root
            )
            observed = [row["filename"] for row in merged]
            filename_only = sorted(path.name for path in files)
            pass_value = bool(
                observed == [".hidden.ARW", "z.ARW", "a.ARW"]
                and observed != filename_only
                and ".hidden.ARW" in observed
            )
            return pass_value, {
                "timestamp_then_filename": observed,
                "filename_only_mutation": filename_only,
            }

    campaign.run(
        "inventory_hidden_file_and_sort_mutation", inventory_sort_plant
    )

    def unexpected_arw_plant() -> tuple[bool, dict[str, Any]]:
        with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
            root = Path(raw_temp) / config["expected_session_basename"]
            root.mkdir()
            for group in config["stacks"]:
                (root / group).mkdir()
                (root / group / "one.ARW").write_bytes(b"group")
            unexpected = root / "outside.ARW"
            unexpected.write_bytes(b"outside")
            result = M.enumerate_session(root, config)
            return len(result["unexpected_arw"]) == 1, {
                "unexpected": [
                    str(path.relative_to(root))
                    for path in result["unexpected_arw"]
                ]
            }

    campaign.run(    "inventory_unexpected_arw_control", unexpected_arw_plant
    )

    campaign.run(
    "inventory_absolute_path_binding_control",
    lambda: _inventory_absolute_path_binding_control(config),
    )
    campaign.run(
    "forged_coarse_encoder_control",
    lambda: _forged_coarse_encoder_control(config),)

    campaign.run(
        "focus_histogram_missing_value_control",
        lambda: (
            M.focus_histogram(
                [{"FocusPosition2": 57}, {"FocusPosition2": None}]
            )["status"]
            == "MISSING_FOCUS_POSITION_2",
            M.focus_histogram(
                [{"FocusPosition2": 57}, {"FocusPosition2": None}]
            ),
        ),
    )
    campaign.run(
        "empty_focus_histogram_control",
        lambda: (
            M.focus_histogram([])["status"] == "MISSING_FOCUS_POSITION_2"
            and M.focus_histogram([])["minimum"] is None
            and M.focus_histogram([])["maximum"] is None,
            M.focus_histogram([]),
        ),
    )

    def rawpy_lifetime_static() -> tuple[bool, dict[str, Any]]:
        source = inspect.getsource(M.decode_rawpy)
        tree = ast.parse(source)
        with_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.With)]
        copies = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "array"
            and any(
                keyword.arg == "copy"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
        ]
        mosaic_copy = bool(
            "raw.raw_image_visible" in source
            and "copy=True" in source
            and source.index("raw.raw_image_visible") < source.index("full =")
        )
        return bool(with_nodes and len(copies) >= 4 and mosaic_copy), {
            "with_nodes": len(with_nodes),
            "np_array_copy_true_calls": len(copies),
            "mosaic_copy_inside_context": mosaic_copy,
        }

    campaign.run("rawpy_copy_inside_context_static_control", rawpy_lifetime_static)

    def active_area_plant() -> tuple[bool, dict[str, Any]]:
        small = copy.deepcopy(config)
        small["decode"]["expected_rawpy_visible_shape_yx"] = [8, 8]
        small["decode"]["expected_rawler_active_shape_yx"] = [8, 10]
        mosaic = np.arange(64, dtype=np.uint16).reshape(8, 8) + 512
        snapshot = M.RawSnapshot(
            mosaic=mosaic.copy(),
            raw_pattern=np.asarray([[0, 1], [3, 2]], dtype=np.uint8),
            color_desc=b"RGBG",
            black_levels=np.asarray([512.0] * 4),
            container_white=16383,
            camera_whitebalance=np.asarray([2.0, 1.0, 1.5, np.nan]),
            full_buffer_shape=(10, 10),
        )
        green = M.green_from_snapshot(snapshot, small)
        padded = np.zeros((10, 10), dtype=np.uint16)
        padded[:8, :8] = mosaic
        active_mean = float(np.mean(mosaic))
        padded_mean = float(np.mean(padded))
        return bool(
            green.green.shape == (4, 4)
            and active_mean != padded_mean
            and green.report["full_buffer_shape_yx_not_used_for_statistics"]
            == [10, 10]
        ), {
            "active_mean": active_mean,
            "padded_mean_wrong_path": padded_mean,
            "green_shape": list(green.green.shape),
        }

    campaign.run("active_area_padding_control", active_area_plant)

    def decoder_dump_plant() -> tuple[bool, dict[str, Any]]:
        with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
            root = Path(raw_temp)
            expected = np.arange(48, dtype=np.uint16).reshape(6, 8)
            good = root / "good.bin"
            good.write_bytes(
                struct.pack("<IIII", 0, 0, 6, 8)
                + expected.astype("<u2").tobytes()
            )
            identity = M.parse_rawler_dump(good, expected)
            bad = root / "bad.bin"
            mutated = expected.copy()
            mutated[3, 4] ^= np.uint16(1)
            bad.write_bytes(
                struct.pack("<IIII", 0, 0, 6, 8)
                + mutated.astype("<u2").tobytes()
            )
            caught = False
            message = None
            try:
                M.parse_rawler_dump(bad, expected)
            except M.InstrumentError as error:
                caught = True
                message = str(error)
            return bool(identity["payload_matches_rawpy"] and caught), {
                "identity": identity,
                "mutation_caught": caught,
                "mutation_message": message,
            }

    campaign.run("decoder_checksum_mutation_control", decoder_dump_plant)
    campaign.run(
        "crosscheck_binary_mismatch_control",
        lambda: _crosscheck_binary_mismatch_control(config),
    )
    campaign.run(
        "cargo_dependency_freeze_mutation_control",
        lambda: _cargo_dependency_freeze_mutation_control(
            freeze_manifest_path, crosscheck_binary
        ),
    )
    campaign.run(
        "python_native_runtime_closure_control",
        _python_native_runtime_closure_control,
    )

    def stdout_transport_plant() -> tuple[bool, dict[str, Any]]:
        rust = M.CROSSCHECK_SOURCE.read_text(encoding="utf-8")
        python = inspect.getsource(M.run_rawler_crosscheck)
        passed = bool(
            "stdout.lock()" in rust
            and "BufWriter" in rust
            and "File::create" not in rust
            and "create_dir_all" not in rust
            and "text=False" in python
            and "parse_rawler_payload(completed.stdout" in python
        )
        return passed, {
            "rust_stdout_stream": "stdout.lock()" in rust,
            "rust_file_create_absent": "File::create" not in rust,
            "rust_directory_create_absent": "create_dir_all" not in rust,
            "python_binary_capture": "text=False" in python,
            "python_direct_payload_parse": (
                "parse_rawler_payload(completed.stdout" in python
            ),
        }

    campaign.run("stdout_transport_no_write_control", stdout_transport_plant)

    campaign.run(
        "nonfinite_refusal_control",
        lambda: _expect_instrument_error(
            lambda: M.spectral_views(
                np.asarray([[1.0, np.nan], [2.0, 3.0]], dtype=np.float32),
                config,
            )
        ),
    )

    def clipping_plant() -> tuple[bool, dict[str, Any]]:
        mask = np.zeros((100, 100), dtype=bool)
        mask.ravel()[:11] = True
        allowed, fraction = M.clip_fraction_allowed(mask, config)
        control_allowed, control_fraction = M.clip_fraction_allowed(
            np.zeros_like(mask), config
        )
        return bool(not allowed and control_allowed), {
            "planted_fraction": fraction,
            "maximum": config["decode"]["maximum_clip_fraction"],
            "identity_fraction": control_fraction,
        }

    campaign.run("clipping_refusal_control", clipping_plant)

    def stopband_plant() -> tuple[bool, dict[str, Any]]:
        size = 256
        y, x = np.indices((size, size), dtype=np.float32)
        low = np.sin(2.0 * np.pi * 8.0 * x / size)
        high = 5.0 * np.sin(2.0 * np.pi * 96.0 * x / size)
        registration, _, report = M.spectral_views(
            (low + high).astype(np.float32), config
        )
        downsample = config["registration"]["downsample_green_plane"]
        expected_low = low[::downsample, ::downsample]
        alpha = float(
            np.sum(registration * expected_low)
            / np.sum(expected_low * expected_low)
        )
        residual = registration - alpha * expected_low
        relative = float(
            np.sqrt(np.mean(residual**2))
            / np.sqrt(np.mean((alpha * expected_low) ** 2))
        )
        return bool(
            report["registration_mask_max_above_stop"] == 0.0
            and relative < 2e-5
        ), {
            "report": report,
            "low_frequency_reconstruction_relative_rms": relative,
        }

    campaign.run("registration_stopband_control", stopband_plant)

    def quad_plant() -> tuple[bool, dict[str, Any]]:
        image, truth = synthetic_quad_image()
        detected, report = M.detect_quadrilateral(image, config)
        ordered_truth = M.order_quad(truth)
        rmse = float(np.sqrt(np.mean((detected - ordered_truth) ** 2)))
        mutation = detected.copy()
        mutation[1] = np.asarray(
            [detected[:, 0].min() - 50.0, detected[:, 1].max() + 50.0]
        )
        mutation_caught = False
        try:
            M.order_quad(mutation)
        except M.InstrumentError:
            mutation_caught = True
        return bool(rmse < 8.0 and mutation_caught), {
            "truth": ordered_truth.tolist(),
            "detected": detected.tolist(),
            "corner_rmse_px": rmse,
            "selector": report,
            "crossed_corner_mutation_caught": mutation_caught,
        }

    campaign.run("quadrilateral_identity_and_corner_mutation", quad_plant)

    def ambiguous_quad_plant() -> tuple[bool, dict[str, Any]]:
        image = np.zeros((320, 500), dtype=np.float32)
        cv2.rectangle(image, (35, 55), (220, 270), 1.0, -1)
        cv2.rectangle(image, (280, 55), (465, 270), 1.0, -1)
        image = cv2.GaussianBlur(image, (0, 0), 2.0)
        caught = False
        message = None
        try:
            M.detect_quadrilateral(image, config)
        except M.InstrumentError as error:
            caught = "ambiguous" in str(error) or "no low-pass" in str(error)
            message = str(error)
        return caught, {"caught": caught, "message": message}

    campaign.run("quadrilateral_ambiguity_control", ambiguous_quad_plant)

    def registration_motion_plant() -> tuple[bool, dict[str, Any]]:
        reference = synthetic_registration_scene()
        truth = np.asarray(
            [[1.015, 0.008, 4.25], [-0.006, 1.015, -3.50]],
            dtype=np.float32,
        )
        moving = cv2.warpAffine(
            reference,
            truth,
            (reference.shape[1], reference.shape[0]),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REFLECT,
        )
        quad = np.asarray(
            [[35, 30], [365, 30], [365, 290], [35, 290]],
            dtype=np.float64,
        )
        reference_low, _, _ = M.spectral_views(reference, config)
        moving_low, _, _ = M.spectral_views(moving, config)
        downsample = config["registration"]["downsample_green_plane"]
        fitted_small, report = M.register_affine(
            reference_low,
            moving_low,
            quad / downsample,
            config,
        )
        fitted = M.affine_to_full_green(fitted_small, downsample)
        points = np.asarray(
            [[70, 60], [330, 70], [310, 250], [90, 260]], dtype=np.float64
        )
        truth_points = M.apply_affine(points, truth)
        fitted_points = M.apply_affine(points, fitted)
        rmse = float(np.sqrt(np.mean((truth_points - fitted_points) ** 2)))

        y, x = np.indices(reference.shape, dtype=np.int32)
        checker = np.where((x + y) % 2 == 0, 1.0, -1.0).astype(np.float32)
        ref_green = reference + 4.0 * checker
        mov_green = moving - 4.0 * checker
        ref_low, _, _ = M.spectral_views(ref_green.astype(np.float32), config)
        mov_low, _, _ = M.spectral_views(mov_green.astype(np.float32), config)
        fitted_distractor, distractor_report = M.register_affine(
            ref_low,
            mov_low,
            quad / downsample,
            config,
        )
        fitted_baseline, _ = M.register_affine(
            reference_low,
            moving_low,
            quad / downsample,
            config,
        )
        distractor_delta = float(
            np.max(np.abs(fitted_distractor - fitted_baseline))
        )
        probe_points = np.asarray(
            [[12.0, 10.0], [88.0, 12.0], [84.0, 68.0], [16.0, 70.0]]
        )
        baseline_points = M.apply_affine(probe_points, fitted_baseline)
        distractor_points = M.apply_affine(probe_points, fitted_distractor)
        point_delta_small = float(
            np.max(
                np.sqrt(
                    np.sum(
                        (baseline_points - distractor_points) ** 2,
                        axis=1,
                    )
                )
            )
        )
        point_delta_native = point_delta_small * downsample * 2.0
        return bool(rmse < 0.75 and point_delta_native < 0.05), {
            "truth_affine": truth.tolist(),
            "fitted_affine": fitted.tolist(),
            "point_rmse_px": rmse,
            "lowpass_distractor_affine_delta": distractor_delta,
            "lowpass_distractor_max_mapped_displacement_native_px": (
                point_delta_native
            ),
            "registration_report": report,
            "distractor_report": distractor_report,
        }

    campaign.run("lowpass_registration_motion_control", registration_motion_plant)

    def lattice_mutation() -> tuple[bool, dict[str, Any]]:
        lattice = M.fixed_lattice(config)
        M.validate_fixed_lattice(lattice, config)
        mutated = lattice.copy()
        mutated[17, 0] += 1e-12
        caught = False
        try:
            M.validate_fixed_lattice(mutated, config)
        except M.InstrumentError:
            caught = True
        return caught, {
            "lattice_sha256": M.array_sha256(lattice),
            "mutation_caught": caught,
        }

    campaign.run("lattice_mutation_control", lattice_mutation)

    peaks4 = make_peak_set(101, lambda value, _: value, config)
    peaks10_identity = make_peak_set(51, lambda value, _: value, config)

    campaign.run(
        "identity_range_control",
        lambda: _range_expectation(
            peaks4,
            peaks10_identity,
            101,
            51,
            config,
            "IMAGE_RANGE_EQUIVALENT",
            lambda result: abs(result["robust_fit"]["intercept"]) < 5e-4
            and abs(result["robust_fit"]["slope"] - 1.0) < 5e-4,
        ),
    )
    campaign.run(
        "bad_offset_control",
        lambda: _range_expectation(
            peaks4,
            make_peak_set(51, lambda value, _: value + 0.045, config),
            101,
            51,
            config,
            "IMAGE_RANGE_NOT_EQUIVALENT",
            lambda result: not result["equivalence_bars"]["predicates"][
                "maximum_abs_intercept"
            ],
        ),
    )
    campaign.run(
        "bad_slope_control",
        lambda: _range_expectation(
            peaks4,
            make_peak_set(51, lambda value, _: 0.5 + 1.09 * (value - 0.5), config),
            101,
            51,
            config,
            "IMAGE_RANGE_NOT_EQUIVALENT",
            lambda result: not result["equivalence_bars"]["predicates"][
                "maximum_abs_slope_error"
            ],
        ),
    )
    campaign.run(
        "bad_residual_control",
        lambda: _range_expectation(
            peaks4,
            make_peak_set(
                51,
                lambda value, index: value + (0.055 if index % 2 else -0.055),
                config,
            ),
            101,
            51,
            config,
            "IMAGE_RANGE_NOT_EQUIVALENT",
            lambda result: not result["equivalence_bars"]["predicates"][
                "maximum_q95_abs_residual"
            ],
        ),
    )

    def nonconverged_fit() -> tuple[bool, dict[str, Any]]:
        mutated_config = copy.deepcopy(config)
        mutated_config["range_fit"]["maximum_iterations"] = 0
        result = M.adjudicate_range_pairs(
            peaks4, peaks10_identity, 101, 51, mutated_config
        )
        return bool(
            result["status"] == "IMAGE_RANGE_NOT_EQUIVALENT"
            and not result["equivalence_bars"]["predicates"]["fit_converged"]
        ), result

    campaign.run("nonconverged_fit_control", nonconverged_fit)

    def too_few() -> tuple[bool, dict[str, Any]]:
        failed = list(peaks10_identity)
        for index in range(20, 64):
            failed[index] = replace(
                failed[index],
                eligible=False,
                status="PLANTED_INELIGIBLE",
                u=None,
            )
        result = M.adjudicate_range_pairs(peaks4, failed, 101, 51, config)
        return result["status"] == "IMAGE_RANGE_UNDETERMINED", result

    campaign.run("too_few_eligible_sites_control", too_few)

    def endpoint_peak() -> tuple[bool, dict[str, Any]]:
        endpoint = M.estimate_peak(gaussian_curve(51, 0.0), config)
        interior = M.estimate_peak(gaussian_curve(51, 0.5), config)
        return bool(
            endpoint.status == "ENDPOINT_PEAK"
            and not endpoint.eligible
            and interior.status == "INTERIOR_PEAK"
            and interior.eligible
        ), {
            "endpoint": M.asdict(endpoint),
            "interior": M.asdict(interior),
        }

    campaign.run("endpoint_peak_control", endpoint_peak)

    def above_band_distractor() -> tuple[bool, dict[str, Any]]:
        size = 64
        frames = 31
        y, x = np.indices((size, size), dtype=np.float32)
        in_band = np.sin(2.0 * np.pi * 16.0 * x / size)
        above = np.sin(2.0 * np.pi * 30.0 * x / size)
        u = np.linspace(0.0, 1.0, frames)
        signal_amp = 0.02 + np.exp(-0.5 * ((u - 0.70) / 0.10) ** 2)
        distractor_amp = 6.0 * np.exp(-0.5 * ((u - 0.20) / 0.07) ** 2)
        clean_curve = []
        distracted_curve = []
        unfiltered_curve = []
        for signal, distractor in zip(signal_amp, distractor_amp, strict=True):
            clean = 1000.0 + 50.0 * signal * in_band
            mixed = clean + 50.0 * distractor * above
            _, clean_focus, _ = M.spectral_views(clean.astype(np.float32), config)
            _, mixed_focus, _ = M.spectral_views(mixed.astype(np.float32), config)
            clean_curve.append(M.focus_band_power(clean_focus, config))
            distracted_curve.append(M.focus_band_power(mixed_focus, config))
            unfiltered_curve.append(float(np.var(mixed)))
        clean_peak = M.estimate_peak(clean_curve, config)
        distracted_peak = M.estimate_peak(distracted_curve, config)
        unfiltered_index = int(np.argmax(unfiltered_curve))
        delta = abs(float(clean_peak.u) - float(distracted_peak.u))
        return bool(
            clean_peak.eligible
            and distracted_peak.eligible
            and delta < 1e-8
            and unfiltered_index < frames // 2
        ), {
            "clean_peak_u": clean_peak.u,
            "distracted_peak_u": distracted_peak.u,
            "bandlimited_peak_delta": delta,
            "unfiltered_peak_index": unfiltered_index,
            "distractor_native_frequency": 30.0 / size / 2.0,
            "focus_cap_native_frequency": config["focus"][
                "lowpass_max_native_cyc_per_px"
            ],
        }

    campaign.run("above_band_distractor_control", above_band_distractor)

    role_temp = tempfile.TemporaryDirectory(dir=HERE)
    matched_flat_manifest = Path(role_temp.name) / "matched-flat.json"
    inventory_fixture, valid_ledger = valid_role_fixture(
        config, matched_flat_manifest
    )

    def valid_roles() -> tuple[bool, dict[str, Any]]:
        calls = {"count": 0}

        def callback() -> None:
            calls["count"] += 1

        result = M.role_gate_result(
            valid_ledger,
            inventory_fixture,
            config,
            score_callback=callback,
        )
        return bool(
            result["status"] == "IDENTIFIABLE"
            and calls["count"] == 1
            and result["j_tr_computed"] is False
            and result["predicates"]["same_physical_sites"] is True
            and result["predicates"]["site_manifest_bound"] is True
            and result["predicates"]["unique_site_identities"] is True
            and result["predicates"]["unique_site_coordinates"] is True
            and result["predicates"]["same_site_role_mapping"] is True
            and result["site_evidence"]["site_count_from_manifest"] == 64
        ), {"result": result, "callback_count": calls["count"]}

    campaign.run("valid_role_fixture_passability", valid_roles)

    def missing_roles() -> tuple[bool, dict[str, Any]]:
        calls = {"count": 0}

        def callback() -> None:
            calls["count"] += 1
            raise AssertionError("J_TR callback must not run")

        ledger = copy.deepcopy(valid_ledger)
        ledger["assignments"] = {}
        result = M.role_gate_result(
            ledger,
            inventory_fixture,
            config,
            score_callback=callback,
        )
        return bool(
            result["status"] == "REFERENCE_ROLE_ABSENT"
            and result["j_tr"] is None
            and not result["j_tr_computed"]
            and calls["count"] == 0
        ), {"result": result, "callback_count": calls["count"]}

    campaign.run("missing_roles_no_jtr_control", missing_roles)

    campaign.run(
        "sw4_as_truth_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["assignments"]["R1"].update(
                {
                    "source_group": "tilted-sw4-cpl",
                    "acquisition_kind": "focus-bracket",
                }
            ),
            "sw4",
        ),
    )
    campaign.run(
        "odd_even_independence_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_odd_even,
            "odd/even",
        ),
    )
    campaign.run(
        "all_axis_repeat_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["assignments"]["sw10_Y2"].update(
                {
                    "source_group": "very-tilted-all-axis-sw10-cpl",
                    "geometry_id": "all-axis",
                }
            ),
            "all-axis",
        ),
    )
    campaign.run(
        "shared_calibration_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_shared_calibration,
            "calibration",
        ),
    )
    campaign.run(
        "shared_source_file_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_shared_source,
            "source files",
        ),
    )
    campaign.run(
        "invented_source_file_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["assignments"]["R1"].update(
                {"source_file_ids": ["f" * 64]}
            ),
            "exactly consume",
        ),
    )
    campaign.run(
        "flat_role_capture_unit_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_flat_capture_unit,
            "capture_unit",
        ),
    )
    campaign.run(
        "flat_role_shared_calibration_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["assignments"]["flat_R2"].update(
                {
                    "flat_lineage_id": ledger["assignments"]["flat_R1"][
                        "flat_lineage_id"
                    ]
                }
            ),
            "calibration",
        ),
    )
    campaign.run(
        "partial_source_group_control",
        lambda: _partial_source_group_control(
            valid_ledger, inventory_fixture, config
        ),
    )
    campaign.run(
        "sampling_interval_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_sampling_interval,
            "sampling",
        ),
    )
    campaign.run(
        "same_physical_sites_false_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["target"].update(
                {"same_physical_sites": False}
            ),
            "same_physical_sites",
        ),
    )
    campaign.run(
        "bare_site_count_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger.update(
                {
                    "site_count": 64,
                    "site_manifest_path": None,
                    "site_manifest_sha256": None,
                }
            ),
            "site manifest",
        ),
    )
    campaign.run(
        "duplicate_site_identity_control",
        lambda: _site_manifest_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _duplicate_site_identity,
            "unique site identities",
        ),
    )
    campaign.run(
        "duplicate_site_coordinate_control",
        lambda: _site_manifest_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _duplicate_site_coordinate,
            "unique normalized coordinates",
        ),
    )
    campaign.run(
        "missing_site_control",
        lambda: _site_manifest_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _remove_site,
            "at least 64",
        ),
    )
    campaign.run(
        "site_coordinate_mismatch_control",
        lambda: _site_manifest_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mismatch_site_coordinate,
            "coordinates mismatch",
        ),
    )
    campaign.run(
        "site_role_binding_control",
        lambda: _site_manifest_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mismatch_site_role_binding,
            "six R1/R2/Y1/Y2 capture roles",
        ),
    )
    campaign.run(
        "site_manifest_hash_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger.update(
                {"site_manifest_sha256": "0" * 64}
            ),
            "site manifest",
        ),
    )
    campaign.run(
        "matched_flat_manifest_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger.update(
                {"matched_flat_manifest_sha256": "not-a-hash"}
            ),
            "manifest",
        ),
    )
    campaign.run(
        "matched_flat_role_binding_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            lambda ledger: ledger["assignments"]["flat_R1"].update(
                {"capture_unit_id": "changed-after-manifest"}
            ),
            "manifest",
        ),
    )
    campaign.run(
        "checker_oracle_control",
        lambda: _role_mutation(
            valid_ledger,
            inventory_fixture,
            config,
            _mutate_checker_oracle,
            "oracle",
        ),
    )

    campaign.run(
        "temporal_split_mutation_control",
        lambda: _temporal_split_control(),
    )

    def exposure_group_control() -> tuple[bool, dict[str, Any]]:
        inventory = {
            "stacks": {
                "flat-sw4-cpl": {
                    "frames": [
                        {"ExposureTime": value}
                        for value in ([1.0] * 8 + [2.5] * 8 + [6.0] * 8)
                    ]
                }
            }
        }
        groups = M._flat_group_frames_by_exposure(inventory, config)
        mutation = copy.deepcopy(inventory)
        for frame in mutation["stacks"]["flat-sw4-cpl"]["frames"]:
            if frame["ExposureTime"] == 2.5:
                frame["ExposureTime"] = 1.0
        caught = False
        try:
            M._flat_group_frames_by_exposure(mutation, config)
        except M.InstrumentError:
            caught = True
        return bool(len(groups) == 3 and caught), {
            "groups": [key for key, _ in groups],
            "merged_group_mutation_caught": caught,
        }

    campaign.run("three_exposure_group_control", exposure_group_control)

    rng = np.random.default_rng(135041)
    quiet = (
        rng.standard_normal((4, 64, 16))
        + 1j * rng.standard_normal((4, 64, 16))
    ) / math.sqrt(2.0)
    campaign.run(
        "quiet_flat_control",
        lambda: (
            M.flat_repeatability(quiet, config)["status"] == "QUIET_DIAGNOSTIC",
            M.flat_repeatability(quiet, config),
        ),
    )

    def structured_flat() -> tuple[bool, dict[str, Any]]:
        local_rng = np.random.default_rng(135042)
        common = (
            local_rng.standard_normal((64, 16))
            + 1j * local_rng.standard_normal((64, 16))
        )
        noise = 0.05 * (
            local_rng.standard_normal((4, 64, 16))
            + 1j * local_rng.standard_normal((4, 64, 16))
        )
        result = M.flat_repeatability(common[None, :, :] + noise, config)
        return result["status"] == "STRUCTURED_FLAT", result

    campaign.run("structured_flat_rejection_control", structured_flat)

    def alternating_sign_flat() -> tuple[bool, dict[str, Any]]:
        plant = np.full((64, 16), 100.0 + 0.0j, dtype=np.complex128)
        values = np.stack([plant, -plant, plant, -plant], axis=0)
        result = M.flat_repeatability(values, config)
        return bool(
            result["status"] == "STRUCTURED_FLAT"
            and result["mean_split_power"] == 10000.0
            and result["legacy_positive_cross_power_median"] == 0.0
            and result["observed_repeatable_power"]
            > result["null_threshold"]
        ), result

    campaign.run(
        "alternating_sign_flat_rejection_control",
        alternating_sign_flat,
    )

    def rotating_sign_flat() -> tuple[bool, dict[str, Any]]:
        plant = np.full((64, 16), 100.0 + 0.0j, dtype=np.complex128)
        values = np.stack(
            [plant, 1j * plant, -plant, -1j * plant],
            axis=0,
        )
        result = M.flat_repeatability(values, config)
        return bool(
            result["status"] == "STRUCTURED_FLAT"
            and result["mean_split_power"] == 10000.0
            and result["observed_repeatable_power"]
            > result["null_threshold"]
        ), result

    campaign.run(
        "rotating_sign_flat_rejection_control",
        rotating_sign_flat,
    )

    def one_pair_only_flat() -> tuple[bool, dict[str, Any]]:
        local_rng = np.random.default_rng(135044)
        values = 0.05 * (
            local_rng.standard_normal((4, 64, 16))
            + 1j * local_rng.standard_normal((4, 64, 16))
        )
        plant = np.full((64, 16), 100.0 + 0.0j, dtype=np.complex128)
        values[0] += plant
        values[1] += plant
        result = M.flat_repeatability(values, config)
        dominant_pair = int(np.argmax(result["pair_repeatable_power"]))
        return bool(
            result["status"] == "STRUCTURED_FLAT"
            and dominant_pair == 0
            and result["pair_order"][dominant_pair] == [0, 1]
            and result["observed_repeatable_power"]
            > result["null_threshold"]
        ), {
            **result,
            "planted_structured_pair": [0, 1],
            "detected_maximum_pair": result["pair_order"][dominant_pair],
        }

    campaign.run(
        "one_pair_only_flat_rejection_control",
        one_pair_only_flat,
    )

    def core_no_detail() -> tuple[bool, dict[str, Any]]:
        local_rng = np.random.default_rng(135043)
        values = 0.1 * (
            local_rng.standard_normal((4, 64, 16))
            + 1j * local_rng.standard_normal((4, 64, 16))
        )
        result = M.existing_core_no_detail_probe(
            values, lawful=True, reason=None
        )
        lawful, reason = M.flat_core_role_contract(
            valid_ledger, "IDENTIFIABLE"
        )
        mutated = copy.deepcopy(valid_ledger)
        mutated["flat_core_eligibility"]["capture_unit_ids"][1] = mutated[
            "flat_core_eligibility"
        ]["capture_unit_ids"][0]
        mutation_lawful, mutation_reason = M.flat_core_role_contract(
            mutated, "IDENTIFIABLE"
        )
        return bool(
            result["invoked"]
            and result["status"] == "NO_DETAIL"
            and lawful
            and reason is None
            and not mutation_lawful
        ), {
            "core": result,
            "role_contract_lawful": lawful,
            "role_contract_reason": reason,
            "duplicate_capture_mutation_lawful": mutation_lawful,
            "duplicate_capture_mutation_reason": mutation_reason,
        }

    campaign.run("lawful_core_no_detail_control", core_no_detail)

    def schema_mutation() -> tuple[bool, dict[str, Any]]:
        payload = {
            "schema": "m135-slide-role-gate-v1",
            "label": M.LABEL,
            "stage": "D",
            "status": "REFERENCE_ROLE_ABSENT",
            "config_sha256": "0" * 64,
            "inventory_sha256": "1" * 64,
            "role_ledger_path": "synthetic-ledger.json",
            "role_ledger_sha256": "2" * 64,
            "invocation": {},
            "missing_roles": ["R1"],
            "predicates": {"all_required_roles_present": False},
            "violations": [],
            "site_evidence": {
                "required_roles": list(M.SAME_SITE_ROLES)
            },
            "j_tr_computed": False,
            "j_tr": None,
        }
        M.validate_artifact(payload)
        del payload["j_tr"]
        caught = False
        try:
            M.validate_artifact(payload)
        except M.InstrumentError:
            caught = True
        return caught, {"missing_required_field_caught": caught}

    campaign.run("artifact_schema_mutation_control", schema_mutation)

    campaign.run(
        "normalized_text_hash_control",
        lambda: _normalized_text_hash_control(),
    )
    campaign.run(
        "summary_chain_splice_control",
        lambda: _summary_chain_splice_control(config),
    )
    campaign.run(
        "forged_physical_binding_control",
        lambda: _forged_physical_binding_control(config),
    )
    campaign.run(
        "forged_range_predicate_control",
        lambda: _forged_range_predicate_control(config),
    )
    campaign.run(
        "forged_identifiable_predicate_control",
        lambda: _forged_identifiable_predicate_control(config),
    )
    campaign.run(
        "range_recompute_binding_control",
        lambda: _range_recompute_binding_control(config),
    )
    campaign.run(
        "inventory_recompute_binding_control",
        lambda: _inventory_recompute_binding_control(config),
    )
    campaign.run(
        "decode_recompute_binding_control",
        lambda: _decode_recompute_binding_control(config),
    )
    campaign.run(
        "flat_recompute_binding_control",
        lambda: _flat_recompute_binding_control(config),
    )
    campaign.run(
        "flat_ledger_binding_control",
        lambda: _flat_ledger_binding_control(config),
    )
    result = campaign.result()
    role_temp.cleanup()
    return result


def _expect_instrument_error(function: Callable[[], Any]) -> tuple[bool, dict[str, Any]]:
    try:
        function()
    except M.InstrumentError as error:
        return True, {"caught": True, "message": str(error)}
    return False, {"caught": False}


def _crosscheck_binary_mismatch_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        root = Path(raw_temp)
        paths = _minimal_artifacts(root, config)
        expected_bytes = b"m135-frozen-crosscheck-executable"
        wrong_bytes = b"m135-wrong-crosscheck-executable"
        expected = root / "expected-crosscheck.exe"
        wrong = root / "wrong-crosscheck.exe"
        expected.write_bytes(expected_bytes)
        wrong.write_bytes(wrong_bytes)
        freeze_manifest = root / "freeze.json"
        M.write_json(
            freeze_manifest,
            {
                "schema": "m135-slide-freeze-v1",
                "label": M.LABEL,
                "status": "FROZEN",
                "source_tree_parent_commit": "synthetic",
                "preregistration": {},
                "existing_estimator": {},
                "source_files": [],
                "commissioning_artifacts": {},
                "dependencies": {},
                "external_decoder_path": {
                    "executable": {
                        "bytes": len(expected_bytes),
                        "sha256": M.sha256_bytes(expected_bytes),
                    }
                },
                "documented_commands": {},
                "config_sha256": M.config_sha256(HERE / "config.json"),
                "artifact_schemas_sha256": M.normalized_text_sha256(
                    HERE / "artifact-schemas.json"
                ),
            },
        )
        caught = False
        message = None
        try:
            M.decode_payload(
                paths["inventory"],
                wrong,
                HERE / "config.json",
                config,
                freeze_manifest,
            )
        except M.InstrumentError as error:
            caught = True
            message = str(error)
        passed = bool(
            caught
            and message is not None
            and "Stage B refused crosscheck executable" in message
        )
        return passed, {
            "stage": "B",
            "expected_input_bytes_hex": expected_bytes.hex(),
            "wrong_input_bytes_hex": wrong_bytes.hex(),
            "expected_sha256": M.sha256_file(expected),
            "wrong_sha256": M.sha256_file(wrong),
            "refused": caught,
            "message": message,
        }


def _copy_freeze_check_tree(destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    for relative in (
        "Cargo.toml",
        "Cargo.lock",
        "rust-toolchain",
        "rust-toolchain.toml",
    ):
        source = M.REPO / relative
        if source.is_file():
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    cargo_config = M.REPO / ".cargo"
    if cargo_config.is_dir():
        shutil.copytree(
            cargo_config,
            destination / ".cargo",
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("target", "__pycache__"),
        )
    shutil.copytree(
        M.REPO / "crates",
        destination / "crates",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("target", "__pycache__"),
    )
    existing_target = destination / M.EXISTING_INSTRUMENT.relative_to(M.REPO)
    existing_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(M.EXISTING_INSTRUMENT, existing_target)
    lane_target = destination / HERE.relative_to(M.REPO)
    shutil.copytree(
        HERE,
        lane_target,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "target",
            "author-target-*",
            "out",
            "__pycache__",
            "tmp*",
        ),
    )
    return lane_target


def _freeze_check_process(
    lane: Path,
    crosscheck_binary: Path,
) -> tuple[int, dict[str, Any]]:
    command = [
        str(Path(sys.executable).absolute()),
        "-B",
        str(lane / "freeze.py"),
        "check",
        "--manifest",
        str(lane / "freeze-manifest.json"),
        "--crosscheck-bin",
        str(crosscheck_binary.absolute()),
    ]
    completed = subprocess.run(
        command,
        cwd=lane.parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    output = completed.stdout if completed.returncode == 0 else completed.stderr
    try:
        payload = json.loads(output.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as error:
        return completed.returncode, {
            "status": "UNPARSEABLE",
            "error": str(error),
        }
    return completed.returncode, {
        "status": payload.get("status"),
        "error_type": payload.get("error_type"),
        "error": payload.get("error"),
        "source_file_count": payload.get("source_file_count"),
    }


def _cargo_dependency_freeze_mutation_control(
    freeze_manifest_path: Path,
    crosscheck_binary: Path,
) -> tuple[bool, dict[str, Any]]:
    if not freeze_manifest_path.is_file():
        return False, {"error": "freeze manifest is missing"}
    with tempfile.TemporaryDirectory() as raw_temp:
        root = Path(raw_temp) / "strehl"
        lane = _copy_freeze_check_tree(root)
        shutil.copy2(freeze_manifest_path, lane / "freeze-manifest.json")
        baseline_code, baseline = _freeze_check_process(
            lane, crosscheck_binary
        )
        dependency = root / "crates" / "strehl-raw" / "src" / "lib.rs"
        before = dependency.read_text(encoding="utf-8")
        old = (
            "let start = (self.active.y + y) * self.stride + self.active.x;"
        )
        new = (
            "let start = (self.active.y + y) * self.stride "
            "+ self.active.x + 1;"
        )
        if before.count(old) != 1:
            return False, {
                "error": "active_row mutation anchor count was not one",
                "anchor_count": before.count(old),
            }
        dependency.write_text(before.replace(old, new, 1), encoding="utf-8")
        after_hash = M.normalized_text_sha256(dependency)
        mutation_code, mutation = _freeze_check_process(
            lane, crosscheck_binary
        )
        passed = bool(
            baseline_code == 0
            and baseline.get("status") == "PASS"
            and mutation_code != 0
            and mutation.get("status") == "FAIL"
            and "external_decoder_path" in str(mutation.get("error"))
        )
        return passed, {
            "copy_kind": "temporary repository-layout copy",
            "mutated_relative_path": "crates/strehl-raw/src/lib.rs",
            "symbol": "Frame::active_row",
            "exact_old": old,
            "exact_new": new,
            "before_sha256": M.sha256_bytes(before.encode("utf-8")),
            "after_sha256": after_hash,
            "baseline_exit_code": baseline_code,
            "baseline": baseline,
            "mutation_exit_code": mutation_code,
            "mutation": mutation,
        }


def _python_native_runtime_closure_control() -> tuple[bool, dict[str, Any]]:
    record = M.dependency_record()
    distributions = record["distributions"]
    selections = {
        name: distribution["load_bearing_native_files"]["selection"]
        for name, distribution in distributions.items()
    }
    runtime_paths = {
        M.normalized_path(row["path"])
        for row in record["python"]["runtime_files"]["files"]
    }
    executable_bound = M.normalized_path(Path(sys.executable)) in runtime_paths
    required = {
        "numpy_core": any("numpy/_core/" in path for path in selections["numpy"]),
        "numpy_fft": any("numpy/fft/" in path for path in selections["numpy"]),
        "scipy_fft": any("scipy/fft/" in path for path in selections["scipy"]),
        "scipy_ndimage": any(
            "scipy/ndimage/" in path for path in selections["scipy"]
        ),
        "scipy_optimize": any(
            "scipy/optimize/" in path for path in selections["scipy"]
        ),
        "cv2_loaded_binary": any(
            path.casefold().endswith(("cv2/cv2.pyd", "cv2/cv2.so"))
            for path in selections["opencv"]
        ),
    }
    selected = next(
        path for path in selections["numpy"] if "numpy/fft/" in path
    )
    original = (
        Path(distributions["numpy"]["root"])
        / Path(*selected.split("/"))
    )
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        root = Path(raw_temp)
        copied = root / original.name
        shutil.copy2(original, copied)
        before = M.semantic_file_closure([copied], root=root)
        payload = bytearray(copied.read_bytes())
        payload[-1] ^= 1
        copied.write_bytes(payload)
        after = M.semantic_file_closure([copied], root=root)
    mutation_detected = (
        before["aggregate_sha256"] != after["aggregate_sha256"]
    )
    return bool(
        executable_bound
        and all(required.values())
        and mutation_detected
    ), {
        "sys_executable_bound": executable_bound,
        "required_native_scopes": required,
        "native_file_counts": {
            name: distribution["load_bearing_native_files"]["file_count"]
            for name, distribution in distributions.items()
        },
        "semantic_file_counts": {
            name: distribution["semantic_file_closure"]["file_count"]
            for name, distribution in distributions.items()
        },
        "mutation_relative_file": selected,
        "mutation_before_aggregate_sha256": before["aggregate_sha256"],
        "mutation_after_aggregate_sha256": after["aggregate_sha256"],
        "semantic_replacement_detected": mutation_detected,
    }


def _range_expectation(
    peaks4: list[M.PeakEstimate],
    peaks10: list[M.PeakEstimate],
    n4: int,
    n10: int,
    config: dict[str, Any],
    expected_status: str,
    predicate: Callable[[dict[str, Any]], bool],
) -> tuple[bool, dict[str, Any]]:
    result = M.adjudicate_range_pairs(peaks4, peaks10, n4, n10, config)
    return bool(result["status"] == expected_status and predicate(result)), result


def _mutate_odd_even(ledger: dict[str, Any]) -> None:
    first = ledger["assignments"]["sw4_Y1"]
    second = ledger["assignments"]["sw4_Y2"]
    second["parent_stack_id"] = first["parent_stack_id"]
    first["subset"] = "odd"
    second["subset"] = "even"


def _mutate_shared_calibration(ledger: dict[str, Any]) -> None:
    first = ledger["assignments"]["R1"]
    second = ledger["assignments"]["R2"]
    second["flat_lineage_id"] = first["flat_lineage_id"]


def _mutate_shared_source(ledger: dict[str, Any]) -> None:
    ledger["assignments"]["R2"]["source_file_ids"] = list(
        ledger["assignments"]["R1"]["source_file_ids"]
    )


def _mutate_flat_capture_unit(ledger: dict[str, Any]) -> None:
    first = ledger["assignments"]["sw4_flat_Y1"]
    second = ledger["assignments"]["sw4_flat_Y2"]
    second["capture_unit_id"] = first["capture_unit_id"]
    second["parent_stack_id"] = first["parent_stack_id"]
    second["source_file_ids"] = list(first["source_file_ids"])


def _mutate_sampling_interval(ledger: dict[str, Any]) -> None:
    ledger["assignments"]["R1"][
        "subject_sampling_lcb95_px_per_object_unit"
    ] = 1.8
    ledger["assignments"]["R2"][
        "subject_sampling_lcb95_px_per_object_unit"
    ] = 1.8


def _mutate_checker_oracle(ledger: dict[str, Any]) -> None:
    ledger["target"] = {
        "kind": "public-periodic-slide",
        "checker_template_available": True,
        "source_oracle_used": True,
        "same_physical_sites": True,
    }


def _role_mutation(
    ledger: dict[str, Any],
    inventory: dict[str, Any],
    config: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
    expected_word: str,
) -> tuple[bool, dict[str, Any]]:
    changed = copy.deepcopy(ledger)
    changed_inventory = copy.deepcopy(inventory)
    mutation(changed)
    for row in changed["assignments"].values():
        changed_inventory["stacks"].setdefault(
            row["source_group"], {"frames": []}
        )
    result = M.role_gate_result(changed, changed_inventory, config)
    text = " ".join(result["violations"]).casefold()
    return bool(
        result["status"] == "ROLE_LEDGER_INVALID"
        and expected_word.casefold() in text
        and not result["j_tr_computed"]
        and result["j_tr"] is None
    ), result


def _site_manifest_mutation(
    ledger: dict[str, Any],
    inventory: dict[str, Any],
    config: dict[str, Any],
    mutation: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    expected_word: str,
) -> tuple[bool, dict[str, Any]]:
    changed = copy.deepcopy(ledger)
    source_manifest = Path(changed["site_manifest_path"])
    evidence = M.load_json_object(source_manifest)
    mutation_detail = mutation(evidence, changed)
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        manifest = Path(raw_temp) / "mutated-physical-sites.json"
        M.write_json(manifest, evidence)
        changed["site_manifest_path"] = str(manifest.absolute())
        changed["site_manifest_sha256"] = M.sha256_file(manifest)
        result = M.role_gate_result(changed, inventory, config)
    text = " ".join(result["violations"]).casefold()
    return bool(
        result["status"] == "ROLE_LEDGER_INVALID"
        and expected_word.casefold() in text
        and result["j_tr_computed"] is False
        and result["j_tr"] is None
    ), {
        "mutation": mutation_detail,
        "result": result,
    }


def _duplicate_site_identity(
    evidence: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    source = evidence["sites"][0]["site_id"]
    replaced = evidence["sites"][1]["site_id"]
    evidence["sites"][1]["site_id"] = source
    for observation in evidence["sites"][1]["role_observations"].values():
        observation["site_id"] = source
    return {
        "site_index": 1,
        "old_site_id": replaced,
        "new_site_id": source,
    }


def _duplicate_site_coordinate(
    evidence: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    coordinate = list(evidence["sites"][0]["normalized_slide_uv"])
    previous = list(evidence["sites"][1]["normalized_slide_uv"])
    evidence["sites"][1]["normalized_slide_uv"] = coordinate
    for observation in evidence["sites"][1]["role_observations"].values():
        observation["normalized_slide_uv"] = coordinate
    return {
        "site_index": 1,
        "old_coordinate": previous,
        "new_coordinate": coordinate,
    }


def _remove_site(
    evidence: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    removed = evidence["sites"].pop()
    ledger["site_count"] = len(evidence["sites"])
    return {
        "removed_site_id": removed["site_id"],
        "remaining_site_count": len(evidence["sites"]),
    }


def _mismatch_site_coordinate(
    evidence: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    observation = evidence["sites"][0]["role_observations"]["R2"]
    previous = list(observation["normalized_slide_uv"])
    observation["normalized_slide_uv"] = [
        previous[0] + 0.001,
        previous[1],
    ]
    return {
        "site_id": evidence["sites"][0]["site_id"],
        "role": "R2",
        "manifest_coordinate": evidence["sites"][0][
            "normalized_slide_uv"
        ],
        "mismatched_role_coordinate": observation["normalized_slide_uv"],
    }


def _mismatch_site_role_binding(
    evidence: dict[str, Any], ledger: dict[str, Any]
) -> dict[str, Any]:
    previous = evidence["role_bindings"]["R2"]["capture_unit_id"]
    evidence["role_bindings"]["R2"][
        "capture_unit_id"
    ] = "wrong-site-capture-unit"
    return {
        "role": "R2",
        "old_capture_unit_id": previous,
        "new_capture_unit_id": "wrong-site-capture-unit",
    }


def _partial_source_group_control(
    ledger: dict[str, Any],
    inventory: dict[str, Any],
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    changed_inventory = copy.deepcopy(inventory)
    changed_ledger = copy.deepcopy(ledger)
    group = changed_ledger["assignments"]["R1"]["source_group"]
    changed_inventory["stacks"][group]["frames"].append(
        {
            "raw_sha256": M.sha256_bytes(b"unassigned-extra-frame"),
            "relative_path": (
                changed_ledger["assignments"]["R1"]["capture_unit_id"]
                + "\\extra.ARW"
            ),
        }
    )
    changed_inventory["stacks"][group]["capture_units"] = (
        M.capture_units_from_frames(changed_inventory["stacks"][group]["frames"])
    )
    result = M.role_gate_result(changed_ledger, changed_inventory, config)
    text = " ".join(result["violations"]).casefold()
    return bool(
        result["status"] == "ROLE_LEDGER_INVALID"
        and "exactly consume" in text
    ), result


def _temporal_split_control() -> tuple[bool, dict[str, Any]]:
    observed = M.temporal_split_indices(10, 4)
    expected = [[0, 4, 8], [1, 5, 9], [2, 6], [3, 7]]
    contiguous_mutation = [
        [0, 1, 2],
        [3, 4, 5],
        [6, 7],
        [8, 9],
    ]
    return bool(observed == expected and observed != contiguous_mutation), {
        "observed": observed,
        "contiguous_mutation": contiguous_mutation,
    }


def _normalized_text_hash_control() -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        root = Path(raw_temp)
        lf = root / "lf.txt"
        crlf = root / "crlf.txt"
        lf.write_bytes(b"alpha\nbeta\n")
        crlf.write_bytes(b"alpha\r\nbeta\r\n")
        normalized_equal = (
            M.normalized_text_sha256(lf) == M.normalized_text_sha256(crlf)
        )
        raw_different = M.sha256_file(lf) != M.sha256_file(crlf)
        return bool(normalized_equal and raw_different), {
            "normalized_lf": M.normalized_text_sha256(lf),
            "normalized_crlf": M.normalized_text_sha256(crlf),
            "raw_lf": M.sha256_file(lf),
            "raw_crlf": M.sha256_file(crlf),
        }


def _minimal_artifacts(
    root: Path, config: dict[str, Any]
) -> dict[str, Path]:
    config_hash = M.config_sha256(HERE / "config.json")
    source_root = root / "capture-source"
    source_root.mkdir(parents=True, exist_ok=True)
    stacks = {}
    all_frames = []
    for group, specification in config["stacks"].items():
        frames = []
        capture_unit = f"{group}\\synthetic-unit"
        for index in range(specification["expected_frames"]):
            raw_bytes = f"{group}-raw-{index}".encode("ascii")
            raw_hash = M.sha256_bytes(raw_bytes)
            relative_path = f"{capture_unit}\\frame-{index:04d}.ARW"
            absolute_path = source_root / Path(*PureWindowsPath(relative_path).parts)
            absolute_path.parent.mkdir(parents=True, exist_ok=True)
            absolute_path.write_bytes(raw_bytes)
            frame = {
                "group": group,
                "ordered_index": index,
                "relative_path": relative_path,
                "absolute_path": str(absolute_path.absolute()),
                "filename": absolute_path.name,
                "capture_time": (
                    f"2026:09:02 20:{index // 60:02d}:{index % 60:02d}.000"
                ),
                "byte_size": len(raw_bytes),
                "raw_sha256": raw_hash,
            }
            if group in {"tilted-sw4-cpl", "tilted-sw10-cpl"}:
                frame["FocusPosition2"] = 10 + (index % 11)
            frames.append(frame)
            all_frames.append(frame)
        stacks[group] = {
            "expected_frames": specification["expected_frames"],
            "observed_frames": len(frames),
            "count_matches": True,
            "frames": frames,
            "capture_units": M.capture_units_from_frames(frames),
        }
        if group in {"tilted-sw4-cpl", "tilted-sw10-cpl"}:
            stacks[group]["focus_position_2"] = M.focus_histogram(frames)
    inventory_path = root / "inventory.json"
    inventory = {
        "schema": "m135-slide-inventory-v1",
        "label": M.LABEL,
        "stage": "A",
        "status": "INVENTORY_MATCH",
        "config_sha256": config_hash,
        "invocation": {},
        "source_root": str(source_root),
        "source_snapshot": {},
        "exiftool": {
            "path": str((root / "synthetic-exiftool.exe").absolute())
        },
        "stacks": stacks,
        "unexpected_arw": [],
        "coarse_encoder": {
            "status": "COARSE_ENCODER_RANGE_EQUAL",
            "tilted_sw4": stacks["tilted-sw4-cpl"]["focus_position_2"],
            "tilted_sw10": stacks["tilted-sw10-cpl"]["focus_position_2"],
        },
        "proceed_to_decode": True,
    }
    M.write_json(inventory_path, inventory)
    inventory_hash = M.sha256_file(inventory_path)

    decode_path = root / "decode.json"
    synthetic_binary_hash = M.sha256_bytes(b"synthetic-crosscheck")
    synthetic_freeze_hash = M.sha256_bytes(b"synthetic-freeze")
    decode = {
        "schema": "m135-slide-decode-v1",
        "label": M.LABEL,
        "stage": "B",
        "status": "DECODE_CROSSCHECK_PASS",
        "config_sha256": config_hash,
        "inventory_sha256": inventory_hash,
        "invocation": {},
        "decoder_contract": {
            "crosscheck_every_frame": True,
            "binary_path": str((root / "synthetic-crosscheck.exe").absolute()),
            "binary_sha256": synthetic_binary_hash,
            "freeze_manifest_path": str(
                (root / "synthetic-freeze.json").absolute()
            ),
            "freeze_manifest_sha256": synthetic_freeze_hash,
            "frozen_binary_bytes": len(b"synthetic-crosscheck"),
            "frozen_binary_sha256": synthetic_binary_hash,
            "binary_hash_bound_before_stage_b": True,
        },
        "frames": [
            {
                "relative_path": frame["relative_path"],
                "raw_sha256": frame["raw_sha256"],
                "status": "PASS",
                "rawpy": {
                    "visible_mosaic_sha256": M.sha256_bytes(
                        f"mosaic-{frame['relative_path']}".encode("utf-8")
                    ),
                    "camera_linear_green_sha256": M.sha256_bytes(
                        f"green-{frame['relative_path']}".encode("utf-8")
                    ),
                },
                "rawler_crosscheck": {
                    "binary_sha256": synthetic_binary_hash,
                    "comparison": {
                        "payload_matches_rawpy": True,
                        "payload_sha256": M.sha256_bytes(
                            f"mosaic-{frame['relative_path']}".encode("utf-8")
                        ),
                        "rawpy_payload_sha256": M.sha256_bytes(
                            f"mosaic-{frame['relative_path']}".encode("utf-8")
                        ),
                    }
                },
            }
            for frame in all_frames
        ],
        "proceed_to_range": True,
    }
    M.write_json(decode_path, decode)
    decode_hash = M.sha256_file(decode_path)

    range_path = root / "range.json"
    image_range = {
        "schema": "m135-slide-range-v1",
        "label": M.LABEL,
        "stage": "C",
        "status": "IMAGE_RANGE_UNDETERMINED",
        "config_sha256": config_hash,
        "inventory_sha256": inventory_hash,
        "decode_sha256": decode_hash,
        "invocation": {},
        "frequency_contract": {
            "green_plane_native_pitch_px": 2.0,
            "registration_stop_native_cyc_per_px": config["registration"][
                "lowpass_stop_native_cyc_per_px"
            ],
            "focus_lowpass_cap_native_cyc_per_px": config["focus"][
                "lowpass_max_native_cyc_per_px"
            ],
        },
        "lattice": {"normalized_xy": M.fixed_lattice(config).tolist()},
        "stacks": {
            "tilted-sw4-cpl": {
                "status": "IMAGE_RANGE_UNDETERMINED",
                "reason": "synthetic chain fixture",
            },
            "tilted-sw10-cpl": {
                "status": "IMAGE_RANGE_UNDETERMINED",
                "reason": "synthetic chain fixture",
            },
        },
        "joint_sites": {"eligible_count": 0, "eligible_indices": []},
        "robust_fit": None,
        "equivalence_bars": {},
        "node_density": None,
    }
    M.write_json(range_path, image_range)

    ledger_a = root / "ledger-a.json"
    ledger_b = root / "ledger-b.json"
    ledger_base = {
        "schema": "m135-slide-role-ledger-v1",
        "label": M.LABEL,
        "assignments": {},
    }
    M.write_json(ledger_a, {**ledger_base, "session_id": "a"})
    M.write_json(ledger_b, {**ledger_base, "session_id": "b"})
    role_result = M.role_gate_result(
        M.load_json_object(ledger_a),
        inventory,
        config,
        ledger_path=ledger_a,
    )

    roles_path = root / "roles.json"
    roles = {
        "schema": "m135-slide-role-gate-v1",
        "label": M.LABEL,
        "stage": "D",
        "status": role_result["status"],
        "config_sha256": config_hash,
        "inventory_sha256": inventory_hash,
        "role_ledger_path": str(ledger_a.absolute()),
        "role_ledger_sha256": M.sha256_file(ledger_a),
        "invocation": {},
        "missing_roles": role_result["missing_roles"],
        "predicates": role_result["predicates"],
        "violations": role_result["violations"],
        "sampling_ratio": role_result.get("sampling_ratio"),
        "site_evidence": role_result["site_evidence"],
        "j_tr_computed": role_result["j_tr_computed"],
        "j_tr": role_result["j_tr"],
        "score_callback_called": role_result["score_callback_called"],
    }
    M.write_json(roles_path, roles)
    roles_hash = M.sha256_file(roles_path)

    flat_path = root / "flat.json"
    flat = {
        "schema": "m135-slide-flat-v1",
        "label": M.LABEL,
        "stage": "E",
        "status": "QUIET_DIAGNOSTIC",
        "config_sha256": config_hash,
        "inventory_sha256": inventory_hash,
        "decode_sha256": decode_hash,
        "role_gate_sha256": roles_hash,
        "role_ledger_sha256": M.sha256_file(ledger_a),
        "invocation": {},
        "frequency_contract": {
            "maximum_frequency_native_cyc_per_px": 0.25
        },
        "sensor_coordinate_lattice": {},
        "exposure_groups": [
            {
                "status": "QUIET_DIAGNOSTIC",
                "exposure_seconds": value,
                "repeatability": {
                    "status": "QUIET_DIAGNOSTIC",
                    "statistic": config["flat"]["repeatability_statistic"],
                    "null_statistic": config["flat"]["null_statistic"],
                    "null_quantile": config["flat"]["null_quantile"],
                    "observed_repeatable_power": 0.0,
                    "pair_repeatable_power": [0.0] * 6,
                    "null_threshold": 1.0,
                    "phase_scramble_q99": 1.0,
                    "phase_scramble_p_upper": 1.0,
                    "structured_alpha": config["flat"]["structured_alpha"],
                },
            }
            for value in (1.0, 2.5, 6.0)
        ],
        "core_probe": {"invoked": False},
        "certificate_sufficient": False,
    }
    M.write_json(flat_path, flat)
    return {
        "inventory": inventory_path,
        "decode": decode_path,
        "range": range_path,
        "roles": roles_path,
        "flat": flat_path,
        "ledger_a": ledger_a,
        "ledger_b": ledger_b,
    }


def _summary_chain_splice_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        baseline = _summary_with_fixture_range(paths, config)
        decode = M.load_json_object(paths["decode"])
        decode["inventory_sha256"] = "f" * 64
        M.write_json(paths["decode"], decode)
        caught = False
        message = None
        try:
            _summary_with_fixture_range(paths, config)
        except M.InstrumentError as error:
            caught = "artifact chain mismatch" in str(error)
            message = str(error)
        return bool(
            baseline["physical_binding"] == "UNBOUND" and caught
        ), {
            "baseline_physical_binding": baseline["physical_binding"],
            "spliced_chain_caught": caught,
            "message": message,
        }


def _inventory_absolute_path_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        root = Path(raw_temp)
        paths = _minimal_artifacts(root, config)
        inventory = M.load_json_object(paths["inventory"])
        frame = inventory["stacks"]["tilted-sw4-cpl"]["frames"][0]
        source = Path(frame["absolute_path"])
        outside = root / "outside-source.ARW"
        outside.write_bytes(source.read_bytes())
        frame["absolute_path"] = str(outside.absolute())
        caught = False
        message = None
        try:
            M.validate_inventory_semantics(inventory, config)
        except M.InstrumentError as error:
            caught = "source_root/relative_path" in str(error)
            message = str(error)
        return caught, {"caught": caught, "message": message}


def _forged_coarse_encoder_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        inventory = M.load_json_object(paths["inventory"])
        inventory["coarse_encoder"]["tilted_sw4"]["minimum"] = -999
        caught = False
        message = None
        try:
            M.validate_inventory_semantics(inventory, config)
        except M.InstrumentError as error:
            caught = "reproduce from frame metadata" in str(error)
            message = str(error)
        return caught, {"caught": caught, "message": message}


def _flat_ledger_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        caught = False
        message = None
        try:
            M.flat_payload(
                paths["inventory"],
                paths["decode"],
                paths["roles"],
                paths["ledger_b"],
                HERE / "config.json",
                config,
            )
        except M.InstrumentError as error:
            caught = "differs from the Stage D ledger" in str(error)
            message = str(error)
        return caught, {"caught": caught, "message": message}


def _forged_physical_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        flat = M.load_json_object(paths["flat"])
        flat["certificate_sufficient"] = True
        M.write_json(paths["flat"], flat)
        caught = False
        message = None
        try:
            _summary_with_fixture_range(paths, config)
        except M.InstrumentError as error:
            caught = "cannot emit a sufficient physical certificate" in str(error)
            message = str(error)
        return caught, {"caught": caught, "message": message}


def _forged_range_predicate_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    lattice = M.fixed_lattice(config)

    def stack(n: int) -> dict[str, Any]:
        sites = []
        for index, peak_u in enumerate(np.linspace(0.16, 0.84, 64)):
            curve = gaussian_curve(n, float(peak_u)).tolist()
            peak = M.estimate_peak(curve, config)
            sites.append(
                {
                    "site_index": index,
                    "normalized_xy": lattice[index].tolist(),
                    "curve": curve,
                    "peak": M.asdict(peak),
                }
            )
        return {"frame_count": n, "sites": sites}

    predicate_names = {
        "minimum_joint_eligible_sites": True,
        "fit_converged": True,
        "maximum_abs_intercept": True,
        "maximum_abs_slope_error": True,
        "maximum_q95_abs_residual": True,
        "positive_slope": True,
    }
    forged = {
        "status": "IMAGE_RANGE_EQUIVALENT",
        "frequency_contract": {
            "green_plane_native_pitch_px": 2.0,
            "registration_stop_native_cyc_per_px": config["registration"][
                "lowpass_stop_native_cyc_per_px"
            ],
            "focus_lowpass_cap_native_cyc_per_px": config["focus"][
                "lowpass_max_native_cyc_per_px"
            ],
        },
        "lattice": {"normalized_xy": lattice.tolist()},
        "joint_sites": {
            "eligible_count": 64,
            "eligible_indices": list(range(64)),
            "u4": np.linspace(0.16, 0.84, 64).tolist(),
            "u10": np.linspace(0.16, 0.84, 64).tolist(),
        },
        "robust_fit": {
            "intercept": 999.0,
            "slope": -10.0,
            "q95_abs_residual": 0.0,
            "residuals": [0.0] * 64,
            "converged": True,
        },
        "equivalence_bars": {
            "minimum_joint_eligible_sites": 48,
            "maximum_abs_intercept": 0.02,
            "maximum_abs_slope_error": 0.04,
            "maximum_q95_abs_residual": 0.03,
            "predicates": predicate_names,
        },
        "node_density": {
            "status": "OK",
            "ratio_sw4_over_sw10": 2.0,
            "sw4_nodes": 20,
            "sw10_nodes": 10,
        },
        "stacks": {
            "tilted-sw4-cpl": stack(101),
            "tilted-sw10-cpl": stack(51),
        },
    }
    caught = False
    message = None
    try:
        M.validate_range_semantics(forged, config)
    except M.InstrumentError as error:
        caught = True
        message = str(error)
    return caught, {"caught": caught, "message": message}


def _forged_identifiable_predicate_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    forged = {
        "status": "IDENTIFIABLE",
        "missing_roles": [],
        "violations": [],
        "predicates": {"invented_predicate": True},
        "j_tr_computed": False,
        "j_tr": None,
    }
    caught = False
    message = None
    try:
        M.validate_roles_semantics(forged, config)
    except M.InstrumentError as error:
        caught = True
        message = str(error)
    return caught, {"caught": caught, "message": message}


def _summary_with_fixture_range(
    paths: dict[str, Path], config: dict[str, Any]
) -> dict[str, Any]:
    original_range = M.range_payload
    original_inventory = M.inventory_payload
    original_decode = M.decode_payload
    original_flat = M.flat_payload

    def fixture_range(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
        return M.load_json_object(paths["range"])

    def fixture_inventory(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
        return M.load_json_object(paths["inventory"])

    def fixture_decode(
        *_arguments: Any, **_keywords: Any
    ) -> tuple[dict[str, Any], int]:
        return M.load_json_object(paths["decode"]), 0

    def fixture_flat(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
        return M.load_json_object(paths["flat"])

    M.range_payload = fixture_range
    M.inventory_payload = fixture_inventory
    M.decode_payload = fixture_decode
    M.flat_payload = fixture_flat
    try:
        return M.summary_payload(
            paths["inventory"],
            paths["decode"],
            paths["range"],
            paths["roles"],
            paths["flat"],
            HERE / "config.json",
            config,
        )
    finally:
        M.range_payload = original_range
        M.inventory_payload = original_inventory
        M.decode_payload = original_decode
        M.flat_payload = original_flat


def _range_recompute_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        original_range = M.range_payload
        original_inventory = M.inventory_payload
        original_decode = M.decode_payload
        original_flat = M.flat_payload

        def mismatched_range(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            result = M.load_json_object(paths["range"])
            result["stacks"]["tilted-sw4-cpl"]["reason"] = "mutated recomputation"
            return result

        def fixture_inventory(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["inventory"])

        def fixture_decode(
            *_arguments: Any, **_keywords: Any
        ) -> tuple[dict[str, Any], int]:
            return M.load_json_object(paths["decode"]), 0

        def fixture_flat(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["flat"])

        M.range_payload = mismatched_range
        M.inventory_payload = fixture_inventory
        M.decode_payload = fixture_decode
        M.flat_payload = fixture_flat
        caught = False
        message = None
        try:
            M.summary_payload(
                paths["inventory"],
                paths["decode"],
                paths["range"],
                paths["roles"],
                paths["flat"],
                HERE / "config.json",
                config,
            )
        except M.InstrumentError as error:
            caught = "does not reproduce from the bound RAW/decode inputs" in str(
                error
            )
            message = str(error)
        finally:
            M.range_payload = original_range
            M.inventory_payload = original_inventory
            M.decode_payload = original_decode
            M.flat_payload = original_flat
        return caught, {"caught": caught, "message": message}


def _inventory_recompute_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        original_range = M.range_payload
        original_inventory = M.inventory_payload
        original_decode = M.decode_payload
        original_flat = M.flat_payload

        def fixture_range(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["range"])

        def mismatched_inventory(
            *_arguments: Any, **_keywords: Any
        ) -> dict[str, Any]:
            result = M.load_json_object(paths["inventory"])
            frames = result["stacks"]["tilted-sw4-cpl"]["frames"]
            frames[0], frames[1] = frames[1], frames[0]
            frames[0]["ordered_index"] = 0
            frames[1]["ordered_index"] = 1
            return result

        def fixture_decode(
            *_arguments: Any, **_keywords: Any
        ) -> tuple[dict[str, Any], int]:
            return M.load_json_object(paths["decode"]), 0

        def fixture_flat(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["flat"])

        M.range_payload = fixture_range
        M.inventory_payload = mismatched_inventory
        M.decode_payload = fixture_decode
        M.flat_payload = fixture_flat
        caught = False
        message = None
        try:
            M.summary_payload(
                paths["inventory"],
                paths["decode"],
                paths["range"],
                paths["roles"],
                paths["flat"],
                HERE / "config.json",
                config,
            )
        except M.InstrumentError as error:
            caught = "metadata/order does not reproduce" in str(error)
            message = str(error)
        finally:
            M.range_payload = original_range
            M.inventory_payload = original_inventory
            M.decode_payload = original_decode
            M.flat_payload = original_flat
        return caught, {"caught": caught, "message": message}


def _decode_recompute_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        original_range = M.range_payload
        original_inventory = M.inventory_payload
        original_decode = M.decode_payload
        original_flat = M.flat_payload

        def fixture_range(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["range"])

        def fixture_inventory(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["inventory"])

        def mismatched_decode(
            *_arguments: Any, **_keywords: Any
        ) -> tuple[dict[str, Any], int]:
            result = M.load_json_object(paths["decode"])
            result["frames"][0]["rawler_crosscheck"]["comparison"][
                "payload_sha256"
            ] = "f" * 64
            return result, 0

        def fixture_flat(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["flat"])

        M.range_payload = fixture_range
        M.inventory_payload = fixture_inventory
        M.decode_payload = mismatched_decode
        M.flat_payload = fixture_flat
        caught = False
        message = None
        try:
            M.summary_payload(
                paths["inventory"],
                paths["decode"],
                paths["range"],
                paths["roles"],
                paths["flat"],
                HERE / "config.json",
                config,
            )
        except M.InstrumentError as error:
            caught = "decode/checksum does not reproduce" in str(error)
            message = str(error)
        finally:
            M.range_payload = original_range
            M.inventory_payload = original_inventory
            M.decode_payload = original_decode
            M.flat_payload = original_flat
        return caught, {"caught": caught, "message": message}


def _flat_recompute_binding_control(
    config: dict[str, Any],
) -> tuple[bool, dict[str, Any]]:
    with tempfile.TemporaryDirectory(dir=HERE) as raw_temp:
        paths = _minimal_artifacts(Path(raw_temp), config)
        original_range = M.range_payload
        original_inventory = M.inventory_payload
        original_decode = M.decode_payload
        original_flat = M.flat_payload

        def fixture_range(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["range"])

        def fixture_inventory(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            return M.load_json_object(paths["inventory"])

        def fixture_decode(
            *_arguments: Any, **_keywords: Any
        ) -> tuple[dict[str, Any], int]:
            return M.load_json_object(paths["decode"]), 0

        def mismatched_flat(*_arguments: Any, **_keywords: Any) -> dict[str, Any]:
            result = M.load_json_object(paths["flat"])
            result["exposure_groups"][0]["exposure_seconds"] = 9.0
            return result

        M.range_payload = fixture_range
        M.inventory_payload = fixture_inventory
        M.decode_payload = fixture_decode
        M.flat_payload = mismatched_flat
        caught = False
        message = None
        try:
            M.summary_payload(
                paths["inventory"],
                paths["decode"],
                paths["range"],
                paths["roles"],
                paths["flat"],
                HERE / "config.json",
                config,
            )
        except M.InstrumentError as error:
            caught = "flat diagnostic does not reproduce" in str(error)
            message = str(error)
        finally:
            M.range_payload = original_range
            M.inventory_payload = original_inventory
            M.decode_payload = original_decode
            M.flat_payload = original_flat
        return caught, {"caught": caught, "message": message}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    root.add_argument("--config", type=Path, default=HERE / "config.json")
    root.add_argument("--output", type=Path, default=HERE / "commission.json")
    root.add_argument(
        "--freeze-manifest",
        type=Path,
        default=HERE / "freeze-manifest.json",
    )
    root.add_argument(
        "--crosscheck-bin",
        type=Path,
        default=DEFAULT_CROSSCHECK_BINARY,
    )
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        payload = commission(
            args.config.absolute(),
            args.freeze_manifest.absolute(),
            args.crosscheck_bin.absolute(),
        )
        M.write_json(args.output.absolute(), payload)
        print(
            json.dumps(
                {
                    "schema": payload["schema"],
                    "status": payload["status"],
                    "checks": len(payload["checks"]),
                    "output": str(args.output.absolute()),
                },
                sort_keys=True,
            )
        )
        return 0 if payload["status"] == "COMMISSIONED" else 1
    except Exception as error:
        payload = {
            "schema": "m135-slide-commission-error-v1",
            "label": M.LABEL,
            "status": "NOT_COMMISSIONED",
            "error_type": type(error).__name__,
            "error": str(error),
            "argv": [str(Path(__file__).absolute()), *json.loads(json.dumps(__import__("sys").argv))],
        }
        M.write_json(args.output.absolute(), payload)
        print(json.dumps(payload, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
