#!/usr/bin/env python3
"""Fail-closed physical commissioning instrument for the burned M135 slide.

This file contains no authorized-session path and performs no work at import
time.  Every data command requires an explicit source root and writes a typed
JSON artifact.  The slide is development material only; no command in this
module emits a J_TR value when the required physical roles are absent.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib
import importlib.metadata
import json
import math
import os
import platform
import re
import stat
import struct
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PureWindowsPath
from typing import Any, Callable, Iterable, Sequence

import cv2
import numpy as np
from scipy import fft


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
DEFAULT_CONFIG = HERE / "config.json"
DEFAULT_SCHEMAS = HERE / "artifact-schemas.json"
EXISTING_INSTRUMENT = REPO / "experiments" / "M135-detail-instrument" / "instrument.py"
CROSSCHECK_MANIFEST = HERE / "Cargo.toml"
CROSSCHECK_SOURCE = HERE / "src" / "main.rs"
CROSSCHECK_LOCK = HERE / "Cargo.lock"

LABEL = "DEVELOPMENT — NEVER A SCORE"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ACTIVE_RE = re.compile(r"active\s*:\s*(\d+)x(\d+)\s+at\s+\((\d+),(\d+)\)")
BUFFER_HEIGHT_RE = re.compile(r"buffer h\s*:\s*(\d+)")
STRIDE_RE = re.compile(r"stride\s*:\s*(\d+)")
ROLE_PREDICATE_NAMES = (
    "all_required_roles_present",
    "sw4_never_truth",
    "independent_capture_units",
    "independent_parent_stacks",
    "source_files_bound_to_inventory",
    "disjoint_source_files",
    "odd_even_not_independent",
    "same_geometry_for_repeats",
    "disjoint_calibration_lineages",
    "reference_sampling_ratio",
    "minimum_sites",
    "matched_flat_evidence",
    "matched_flat_manifest",
    "nonperiodic_target",
    "checker_template_forbidden",
    "source_oracle_forbidden",
)


class InstrumentError(RuntimeError):
    """Malformed input, violated contract, or numerical refusal."""

    def __init__(self, message: str, *, status: str = "INSTRUMENT_ERROR"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class RawSnapshot:
    mosaic: np.ndarray
    raw_pattern: np.ndarray
    color_desc: bytes
    black_levels: np.ndarray
    container_white: int
    camera_whitebalance: np.ndarray
    full_buffer_shape: tuple[int, int] | None


@dataclass(frozen=True)
class GreenFrame:
    green: np.ndarray
    clip_mask: np.ndarray
    raw_g1: np.ndarray
    raw_g2: np.ndarray
    report: dict[str, Any]


@dataclass(frozen=True)
class PeakEstimate:
    eligible: bool
    status: str
    u: float | None
    argmax_index: int | None
    quadratic_coefficients: tuple[float, float, float] | None
    log_prominence: float | None


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def config_sha256(path: Path) -> str:
    return normalized_text_sha256(path)


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_json_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def write_json(path: Path, value: Any) -> None:
    path = path.absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = canonical_json_bytes(value)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded)
    os.replace(temporary, path)


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InstrumentError(f"{path}: cannot read JSON: {error}") from error
    if not isinstance(value, dict):
        raise InstrumentError(f"{path}: expected a JSON object")
    return value


def load_hashed_json_object(path: Path) -> tuple[dict[str, Any], str]:
    try:
        payload = path.read_bytes()
        digest = sha256_bytes(payload)
        value = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise InstrumentError(f"{path}: cannot read hashed JSON: {error}") from error
    if not isinstance(value, dict):
        raise InstrumentError(f"{path}: expected a JSON object")
    return value, digest


def exact_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def normalized_path(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def path_is_within(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((normalized_path(path), normalized_path(root))) == normalized_path(root)
    except ValueError:
        return False


def package_version(*names: str) -> str | None:
    for name in names:
        try:
            return importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            continue
    return None


def dependency_record() -> dict[str, Any]:
    import rawpy
    import scipy

    module_paths: dict[str, str | None] = {
        "numpy": getattr(np, "__file__", None),
        "scipy": getattr(scipy, "__file__", None),
        "rawpy": getattr(rawpy, "__file__", None),
        "rawpy_extension": getattr(rawpy._rawpy, "__file__", None),
        "opencv": getattr(cv2, "__file__", None),
    }
    modules: dict[str, Any] = {}
    for name, raw_path in module_paths.items():
        path = Path(raw_path).absolute() if raw_path else None
        modules[name] = {
            "path": str(path) if path is not None else None,
            "sha256": sha256_file(path) if path is not None and path.is_file() else None,
        }
    return {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "executable": str(Path(sys.executable).absolute()),
            "executable_sha256": sha256_file(Path(sys.executable)),
        },
        "packages": {
            "numpy": package_version("numpy"),
            "scipy": package_version("scipy"),
            "rawpy": package_version("rawpy"),
            "opencv": package_version(
                "opencv-python", "opencv-python-headless", "opencv-contrib-python"
            )
            or getattr(cv2, "__version__", None),
        },
        "modules": modules,
    }


def invocation_record(config_path: Path, config: dict[str, Any]) -> dict[str, Any]:
    environment_keys = list(config["environment"]["required"]) + list(
        config["environment"]["record_even_when_unset"]
    )
    return {
        "argv": [str(Path(sys.executable).absolute()), *sys.argv],
        "command_line_windows": subprocess.list2cmdline(
            [str(Path(sys.executable).absolute()), *sys.argv]
        ),
        "cwd": str(Path.cwd().absolute()),
        "platform": platform.platform(),
        "environment": {key: os.environ.get(key) for key in environment_keys},
        "opencv_threads": int(cv2.getNumThreads()),
        "config_path": str(config_path.absolute()),
        "config_sha256": config_sha256(config_path),
        "source_path": str(Path(__file__).absolute()),
        "source_sha256": normalized_text_sha256(Path(__file__)),
        "dependencies": dependency_record(),
    }


def require_environment(config: dict[str, Any]) -> None:
    mismatches = {
        key: {"required": expected, "observed": os.environ.get(key)}
        for key, expected in config["environment"]["required"].items()
        if os.environ.get(key) != expected
    }
    if mismatches:
        raise InstrumentError(
            "required deterministic environment is not set: "
            + json.dumps(mismatches, sort_keys=True)
        )
    cv2.setNumThreads(1)
    if cv2.getNumThreads() != 1:
        raise InstrumentError(
            f"OpenCV refused the one-thread contract: {cv2.getNumThreads()}"
        )


def load_config(path: Path) -> dict[str, Any]:
    config = load_json_object(path)
    if config.get("schema") != "m135-slide-physical-config-v1":
        raise InstrumentError("unsupported M135 physical config schema")
    if config.get("label") != LABEL:
        raise InstrumentError("development label changed")
    stacks = config.get("stacks")
    if not isinstance(stacks, dict) or set(stacks) != {
        "tilted-sw4-cpl",
        "tilted-sw10-cpl",
        "flat-sw4-cpl",
        "very-tilted-all-axis-sw10-cpl",
    }:
        raise InstrumentError("the four frozen slide groups changed")
    if [stacks[name]["expected_frames"] for name in stacks] != [182, 92, 186, 197]:
        raise InstrumentError("frozen expected frame counts changed")
    decode = config["decode"]
    if decode["green_plane_native_pitch_px"] != 2.0:
        raise InstrumentError("green-plane/native-pixel conversion changed")
    registration = config["registration"]
    if not (
        0.0
        < registration["lowpass_pass_native_cyc_per_px"]
        < registration["lowpass_stop_native_cyc_per_px"]
        < 0.10
    ):
        raise InstrumentError("registration is not strictly below 0.10 cyc/native px")
    focus = config["focus"]
    if not (
        0.0
        < focus["band_min_native_cyc_per_px"]
        < focus["band_max_native_cyc_per_px"]
        <= focus["lowpass_max_native_cyc_per_px"]
        <= 0.25
    ):
        raise InstrumentError("focus frequency contract exceeds 0.25 cyc/native px")
    lattice = config["lattice"]
    if lattice["rows"] != 8 or lattice["columns"] != 8:
        raise InstrumentError("the frozen 8x8 lattice changed")
    range_fit = config["range_fit"]
    if (
        range_fit["minimum_joint_eligible_sites"] != 48
        or range_fit["maximum_abs_intercept"] != 0.02
        or range_fit["maximum_abs_slope_error"] != 0.04
        or range_fit["maximum_q95_abs_residual"] != 0.03
    ):
        raise InstrumentError("the preregistered equivalence bars changed")
    flat_frequencies = config["flat"]["frequencies_native_cyc_per_px"]
    if max(flat_frequencies) > 0.25:
        raise InstrumentError("flat diagnostic exceeds 0.25 cyc/native px")
    if config["roles"]["minimum_reference_to_scored_sampling_ratio"] != 2.0:
        raise InstrumentError("reference/scored sampling floor changed")
    return config


def validate_artifact(payload: dict[str, Any], schemas_path: Path = DEFAULT_SCHEMAS) -> None:
    schemas = load_json_object(schemas_path)
    artifact = schemas.get("artifacts", {}).get(payload.get("schema"))
    if not isinstance(artifact, dict):
        raise InstrumentError(f"unknown artifact schema {payload.get('schema')!r}")
    missing = [key for key in artifact["required"] if key not in payload]
    if missing:
        raise InstrumentError(
            f"{payload.get('schema')}: missing required fields {missing}"
        )
    statuses = artifact.get("terminal_statuses", [])
    if statuses and payload.get("status") not in statuses:
        raise InstrumentError(
            f"{payload.get('schema')}: unsupported status {payload.get('status')!r}"
        )
    canonical_json_bytes(payload)


def validate_inventory_semantics(
    inventory: dict[str, Any], config: dict[str, Any]
) -> None:
    source_root_raw = inventory.get("source_root")
    if not isinstance(source_root_raw, str) or not source_root_raw:
        raise InstrumentError("inventory source_root is missing")
    source_root = Path(source_root_raw).absolute()
    try:
        _reject_reparse_components(source_root)
        source_resolved = source_root.resolve(strict=True)
    except OSError as error:
        raise InstrumentError(f"inventory source_root is unreadable: {error}") from error
    if set(inventory.get("stacks", {})) != set(config["stacks"]):
        raise InstrumentError("inventory stack set differs from the frozen four groups")
    all_counts_match = True
    seen_paths: set[str] = set()
    recomputed_focus: dict[str, dict[str, Any]] = {}
    for group, expected in config["stacks"].items():
        row = inventory["stacks"][group]
        frames = row.get("frames")
        if not isinstance(frames, list):
            raise InstrumentError(f"inventory {group} frames are missing")
        observed = row.get("observed_frames")
        expected_count = expected["expected_frames"]
        count_matches = bool(
            isinstance(observed, int)
            and not isinstance(observed, bool)
            and observed == len(frames) == expected_count
            and row.get("expected_frames") == expected_count
            and row.get("count_matches") is True
        )
        all_counts_match = all_counts_match and count_matches
        sort_rows: list[tuple[datetime, str, str]] = []
        for ordered_index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                raise InstrumentError(f"inventory {group} contains a non-object frame")
            relative = frame.get("relative_path")
            raw_hash = frame.get("raw_sha256")
            absolute_raw = frame.get("absolute_path")
            if (
                not isinstance(relative, str)
                or not relative
                or relative.casefold() in seen_paths
                or not isinstance(raw_hash, str)
                or HEX64.fullmatch(raw_hash) is None
                or not isinstance(absolute_raw, str)
                or not absolute_raw
            ):
                raise InstrumentError(f"inventory {group} has an invalid frame identity")
            if frame.get("ordered_index") != ordered_index:
                raise InstrumentError(
                    f"inventory {group} ordered_index sequence is invalid"
                )
            capture_time = frame.get("capture_time")
            filename = frame.get("filename")
            if not isinstance(capture_time, str) or not isinstance(filename, str):
                raise InstrumentError(
                    f"inventory {group} lacks capture_time/filename ordering fields"
                )
            parsed_time, _ = parse_capture_time(
                {"SubSecDateTimeOriginal": capture_time}
            )
            sort_rows.append(
                (parsed_time, filename.casefold(), relative.casefold())
            )
            relative_path = Path(*PureWindowsPath(relative).parts)
            expected_absolute = (source_root / relative_path).absolute()
            observed_absolute = Path(absolute_raw).absolute()
            if normalized_path(observed_absolute) != normalized_path(
                expected_absolute
            ):
                raise InstrumentError(
                    f"inventory {group} absolute_path is not source_root/relative_path"
                )
            try:
                _reject_reparse_components(observed_absolute)
                observed_resolved = observed_absolute.resolve(strict=True)
                info = observed_absolute.lstat()
            except OSError as error:
                raise InstrumentError(
                    f"inventory frame is unreadable: {observed_absolute}: {error}"
                ) from error
            if (
                observed_absolute.is_symlink()
                or _is_reparse(info)
                or not stat.S_ISREG(info.st_mode)
                or not path_is_within(observed_resolved, source_resolved)
                or sha256_file(observed_absolute) != raw_hash
                or frame.get("byte_size") != info.st_size
            ):
                raise InstrumentError(
                    f"inventory {group} frame path/hash/size is not bound to source_root"
                )
            seen_paths.add(relative.casefold())
        if sort_rows != sorted(sort_rows):
            raise InstrumentError(
                f"inventory {group} is not sorted by timestamp/subsecond/filename"
            )
        capture_units = row.get("capture_units")
        expected_units = capture_units_from_frames(frames)
        if capture_units != expected_units:
            raise InstrumentError(
                f"inventory {group} capture-unit ledger does not match its frames"
            )
        if group in {"tilted-sw4-cpl", "tilted-sw10-cpl"}:
            recomputed = focus_histogram(frames)
            if row.get("focus_position_2") != recomputed:
                raise InstrumentError(
                    f"inventory {group} FocusPosition2 histogram does not match its frames"
                )
            recomputed_focus[group] = recomputed
    unexpected = inventory.get("unexpected_arw")
    if not isinstance(unexpected, list):
        raise InstrumentError("inventory unexpected_arw is not a list")
    expected_status = (
        "INVENTORY_MATCH"
        if all_counts_match and not unexpected
        else "INVENTORY_MISMATCH"
    )
    if inventory.get("status") != expected_status:
        raise InstrumentError("inventory status does not match its frame census")
    if inventory.get("proceed_to_decode") is not (expected_status == "INVENTORY_MATCH"):
        raise InstrumentError("inventory proceed_to_decode contradicts its status")
    coarse = inventory.get("coarse_encoder")
    if not isinstance(coarse, dict):
        raise InstrumentError("inventory coarse encoder record is missing")
    left = recomputed_focus["tilted-sw4-cpl"]
    right = recomputed_focus["tilted-sw10-cpl"]
    if left["status"] != "COMPLETE" or right["status"] != "COMPLETE":
        derived_coarse = "COARSE_ENCODER_MISSING"
    elif (
        left["minimum"] == right["minimum"]
        and left["maximum"] == right["maximum"]
    ):
        derived_coarse = "COARSE_ENCODER_RANGE_EQUAL"
    else:
        derived_coarse = "COARSE_ENCODER_RANGE_NOT_EQUAL"
    if not (
        coarse.get("status") == derived_coarse
        and coarse.get("tilted_sw4") == left
        and coarse.get("tilted_sw10") == right
    ):
        raise InstrumentError(
            "coarse encoder status/histograms do not reproduce from frame metadata"
        )


def validate_decode_semantics(
    decode: dict[str, Any],
    inventory: dict[str, Any],
) -> None:
    if decode.get("inventory_sha256") is None:
        raise InstrumentError("decode artifact lacks its inventory binding")
    if decode.get("status") != "DECODE_CROSSCHECK_PASS":
        if decode.get("proceed_to_range") is not False:
            raise InstrumentError("failed decode cannot proceed to range")
        return
    if inventory.get("status") != "INVENTORY_MATCH":
        raise InstrumentError("passing decode is paired with a nonmatching inventory")
    expected = {
        frame["relative_path"].casefold(): frame
        for frame in _inventory_frames(inventory)
    }
    observed_rows = decode.get("frames")
    if (
        not isinstance(observed_rows, list)
        or len(observed_rows) != len(expected)
        or decode.get("proceed_to_range") is not True
        or decode.get("decoder_contract", {}).get("crosscheck_every_frame") is not True
    ):
        raise InstrumentError("decode PASS does not cover every inventoried frame")
    observed: set[str] = set()
    for row in observed_rows:
        relative = str(row.get("relative_path", "")).casefold()
        if (
            relative not in expected
            or relative in observed
            or row.get("status") != "PASS"
            or row.get("raw_sha256") != expected[relative]["raw_sha256"]
        ):
            raise InstrumentError("decode frame identity/status does not match inventory")
        observed.add(relative)
        rawpy = row.get("rawpy")
        crosscheck = row.get("rawler_crosscheck")
        comparison = (
            crosscheck.get("comparison")
            if isinstance(crosscheck, dict)
            else None
        )
        if not (
            isinstance(rawpy, dict)
            and isinstance(comparison, dict)
            and comparison.get("payload_matches_rawpy") is True
            and comparison.get("payload_sha256")
            == rawpy.get("visible_mosaic_sha256")
            == comparison.get("rawpy_payload_sha256")
            and isinstance(rawpy.get("camera_linear_green_sha256"), str)
            and HEX64.fullmatch(rawpy["camera_linear_green_sha256"])
        ):
            raise InstrumentError("decode PASS lacks a bit-exact independent checksum")


def validate_range_semantics(
    image_range: dict[str, Any], config: dict[str, Any]
) -> None:
    frequency = image_range.get("frequency_contract")
    if not isinstance(frequency, dict) or not (
        frequency.get("green_plane_native_pitch_px") == 2.0
        and frequency.get("registration_stop_native_cyc_per_px")
        == config["registration"]["lowpass_stop_native_cyc_per_px"]
        and frequency.get("focus_lowpass_cap_native_cyc_per_px")
        == config["focus"]["lowpass_max_native_cyc_per_px"]
        and frequency.get("focus_lowpass_cap_native_cyc_per_px") <= 0.25
    ):
        raise InstrumentError("range frequency contract is invalid")
    lattice = image_range.get("lattice", {}).get("normalized_xy")
    if not isinstance(lattice, list):
        raise InstrumentError("range artifact lacks the normalized lattice")
    validate_fixed_lattice(np.asarray(lattice, dtype=np.float64), config)
    stacks = image_range.get("stacks")
    if not isinstance(stacks, dict) or set(stacks) != {
        "tilted-sw4-cpl",
        "tilted-sw10-cpl",
    }:
        raise InstrumentError("range artifact lacks the two frozen stack records")

    def recorded_peaks(group: str) -> tuple[list[PeakEstimate], int] | None:
        row = stacks[group]
        if not isinstance(row, dict):
            raise InstrumentError(f"range stack {group} is not an object")
        sites = row.get("sites")
        if sites is None:
            return None
        if not isinstance(sites, list) or len(sites) != 64:
            raise InstrumentError(f"range stack {group} must record 64 sites")
        frame_count = row.get("frame_count")
        if not isinstance(frame_count, int) or isinstance(frame_count, bool):
            raise InstrumentError(f"range stack {group} frame_count is invalid")
        expected_lattice = fixed_lattice(config)
        peaks: list[PeakEstimate] = []
        for index, site in enumerate(sites):
            if not isinstance(site, dict) or site.get("site_index") != index:
                raise InstrumentError(f"range stack {group} site order changed")
            if site.get("normalized_xy") != expected_lattice[index].tolist():
                raise InstrumentError(f"range stack {group} lattice coordinate changed")
            peak = site.get("peak")
            if not isinstance(peak, dict):
                raise InstrumentError(f"range stack {group} site {index} lacks peak")
            curve = site.get("curve")
            if not isinstance(curve, list) or len(curve) != frame_count:
                raise InstrumentError(
                    f"range stack {group} site {index} curve length changed"
                )
            if any(value is None for value in curve):
                reproduced_peak = PeakEstimate(
                    False, "INCOMPLETE_CURVE", None, None, None, None
                )
            elif any(not exact_number(value) for value in curve):
                raise InstrumentError("range curve contains a non-finite value")
            else:
                reproduced_peak = estimate_peak(
                    [float(value) for value in curve], config
                )
            if canonical_json_sha256(peak) != canonical_json_sha256(
                asdict(reproduced_peak)
            ):
                raise InstrumentError(
                    f"range stack {group} site {index} peak does not reproduce"
                )
            peaks.append(reproduced_peak)
        return peaks, frame_count

    recorded4 = recorded_peaks("tilted-sw4-cpl")
    recorded10 = recorded_peaks("tilted-sw10-cpl")
    if (recorded4 is None) != (recorded10 is None):
        raise InstrumentError("only one range stack contains site peaks")
    if recorded4 is not None and recorded10 is not None:
        peaks4, frames4 = recorded4
        peaks10, frames10 = recorded10
        reproduced = adjudicate_range_pairs(
            peaks4, peaks10, frames4, frames10, config
        )
        actual_projection = {
            "status": image_range.get("status"),
            "joint_eligible_count": image_range.get("joint_sites", {}).get(
                "eligible_count"
            ),
            "joint_eligible_indices": image_range.get("joint_sites", {}).get(
                "eligible_indices"
            ),
            "u4": image_range.get("joint_sites", {}).get("u4"),
            "u10": image_range.get("joint_sites", {}).get("u10"),
            "robust_fit": image_range.get("robust_fit"),
            "equivalence_bars": image_range.get("equivalence_bars"),
            "node_density": image_range.get("node_density"),
        }
        expected_projection = {
            "status": reproduced["status"],
            "joint_eligible_count": reproduced["joint_eligible_count"],
            "joint_eligible_indices": reproduced["joint_eligible_indices"],
            "u4": reproduced.get("u4"),
            "u10": reproduced.get("u10"),
            "robust_fit": reproduced["robust_fit"],
            "equivalence_bars": reproduced["equivalence_bars"],
            "node_density": reproduced["node_density"],
        }
        if canonical_json_sha256(actual_projection) != canonical_json_sha256(
            expected_projection
        ):
            raise InstrumentError(
                "range fit/bars do not reproduce from the recorded site peaks"
            )
    elif image_range.get("status") != "IMAGE_RANGE_UNDETERMINED":
        raise InstrumentError("range status has no recorded site-peak population")
    status = image_range.get("status")
    joint = image_range.get("joint_sites")
    if not isinstance(joint, dict):
        raise InstrumentError("range joint-site record is missing")
    eligible = joint.get("eligible_count")
    eligible_indices = joint.get("eligible_indices")
    if not (
        isinstance(eligible, int)
        and not isinstance(eligible, bool)
        and isinstance(eligible_indices, list)
        and len(eligible_indices) == eligible
        and len(set(eligible_indices)) == eligible
        and all(
            isinstance(index, int)
            and not isinstance(index, bool)
            and 0 <= index < 64
            for index in eligible_indices
        )
    ):
        raise InstrumentError("range eligible-site census is invalid")
    minimum = config["range_fit"]["minimum_joint_eligible_sites"]
    fit = image_range.get("robust_fit")
    bars = image_range.get("equivalence_bars")
    expected_predicate_names = {
        "minimum_joint_eligible_sites",
        "fit_converged",
        "maximum_abs_intercept",
        "maximum_abs_slope_error",
        "maximum_q95_abs_residual",
        "positive_slope",
    }
    recomputed_predicates: dict[str, bool] | None = None
    if isinstance(fit, dict):
        intercept = fit.get("intercept")
        slope = fit.get("slope")
        q95 = fit.get("q95_abs_residual")
        residuals = fit.get("residuals")
        if not (
            exact_number(intercept)
            and exact_number(slope)
            and exact_number(q95)
            and isinstance(residuals, list)
            and len(residuals) == eligible
            and all(exact_number(value) for value in residuals)
            and isinstance(fit.get("converged"), bool)
        ):
            raise InstrumentError("range robust-fit record is malformed")
        recomputed_q95 = float(
            np.quantile(
                np.abs(np.asarray(residuals, dtype=np.float64)),
                config["range_fit"]["residual_quantile"],
                method=config["range_fit"]["quantile_method"],
            )
        )
        if not math.isclose(
            recomputed_q95, float(q95), rel_tol=0.0, abs_tol=1e-12
        ):
            raise InstrumentError("range q95 does not match its residual vector")
        recomputed_predicates = {
            "minimum_joint_eligible_sites": eligible >= minimum,
            "fit_converged": fit["converged"],
            "maximum_abs_intercept": abs(float(intercept))
            <= config["range_fit"]["maximum_abs_intercept"],
            "maximum_abs_slope_error": abs(float(slope) - 1.0)
            <= config["range_fit"]["maximum_abs_slope_error"],
            "maximum_q95_abs_residual": float(q95)
            <= config["range_fit"]["maximum_q95_abs_residual"],
            "positive_slope": float(slope) > 0.0,
        }
        if not isinstance(bars, dict) or not (
            bars.get("minimum_joint_eligible_sites") == minimum
            and bars.get("maximum_abs_intercept")
            == config["range_fit"]["maximum_abs_intercept"]
            and bars.get("maximum_abs_slope_error")
            == config["range_fit"]["maximum_abs_slope_error"]
            and bars.get("maximum_q95_abs_residual")
            == config["range_fit"]["maximum_q95_abs_residual"]
            and set(bars.get("predicates", {})) == expected_predicate_names
            and bars.get("predicates") == recomputed_predicates
        ):
            raise InstrumentError("range predicates do not reproduce the frozen bars")
    if status == "IMAGE_RANGE_EQUIVALENT":
        density = image_range.get("node_density")
        if not (
            recomputed_predicates is not None
            and all(recomputed_predicates.values())
            and isinstance(density, dict)
            and density.get("status") == "OK"
            and exact_number(density.get("ratio_sw4_over_sw10"))
            and float(density["ratio_sw4_over_sw10"]) > 0.0
            and isinstance(density.get("sw4_nodes"), int)
            and density["sw4_nodes"] > 0
            and isinstance(density.get("sw10_nodes"), int)
            and density["sw10_nodes"] > 0
        ):
            raise InstrumentError("equivalent range status is unsupported by its fit")
    elif status == "IMAGE_RANGE_NOT_EQUIVALENT":
        if not (
            recomputed_predicates is not None
            and any(value is False for value in recomputed_predicates.values())
        ):
            raise InstrumentError("non-equivalent range status has no failed bar")
    elif status == "IMAGE_RANGE_UNDETERMINED":
        if not (
            fit is None
            or not isinstance(eligible, int)
            or eligible < minimum
            or any(
                row.get("status") == "IMAGE_RANGE_UNDETERMINED"
                for row in image_range.get("stacks", {}).values()
                if isinstance(row, dict)
            )
        ):
            raise InstrumentError("undetermined range status has no refusal evidence")
    else:
        raise InstrumentError(f"unsupported range status {status!r}")


def validate_roles_semantics(
    roles: dict[str, Any], config: dict[str, Any]
) -> None:
    if roles.get("j_tr_computed") is not False or roles.get("j_tr") is not None:
        raise InstrumentError("role stage must not supply a J_TR value")
    status = roles.get("status")
    missing = roles.get("missing_roles")
    violations = roles.get("violations")
    predicates = roles.get("predicates")
    if not (
        isinstance(missing, list)
        and isinstance(violations, list)
        and isinstance(predicates, dict)
        and set(predicates) == set(ROLE_PREDICATE_NAMES)
    ):
        raise InstrumentError("role artifact has malformed evidence")
    if status == "REFERENCE_ROLE_ABSENT":
        if not missing or predicates.get("all_required_roles_present") is not False:
            raise InstrumentError("REFERENCE_ROLE_ABSENT lacks missing-role evidence")
        if any(role not in config["roles"]["required_roles"] for role in missing):
            raise InstrumentError("role artifact names an unknown missing role")
    elif status == "ROLE_LEDGER_INVALID":
        if missing or not violations:
            raise InstrumentError("ROLE_LEDGER_INVALID lacks violations")
    elif status == "IDENTIFIABLE":
        if (
            missing
            or violations
            or not predicates
            or any(value is not True for value in predicates.values())
        ):
            raise InstrumentError("IDENTIFIABLE has a failed or absent predicate")
    else:
        raise InstrumentError(f"unsupported role status {status!r}")


def validate_flat_semantics(flat: dict[str, Any], config: dict[str, Any]) -> None:
    if flat.get("certificate_sufficient") is not False:
        raise InstrumentError(
            "burned-slide flat schema cannot emit a sufficient physical certificate"
        )
    core = flat.get("core_probe")
    if not isinstance(core, dict) or core.get("invoked") is not False:
        raise InstrumentError("one-ladder temporal splits cannot invoke the M135 core")
    frequency = flat.get("frequency_contract")
    if not isinstance(frequency, dict) or (
        frequency.get("maximum_frequency_native_cyc_per_px") is None
        or frequency["maximum_frequency_native_cyc_per_px"] > 0.25
    ):
        raise InstrumentError("flat artifact exceeds the native-frequency cap")
    status = flat.get("status")
    groups = flat.get("exposure_groups")
    if not isinstance(groups, list):
        raise InstrumentError("flat exposure groups are missing")
    if status in {"QUIET_DIAGNOSTIC", "STRUCTURED_FLAT"}:
        if len(groups) != config["flat"]["expected_exposure_groups"]:
            raise InstrumentError("flat terminal status lacks three exposure groups")
        if any(
            not isinstance(row, dict)
            or row.get("status") not in {"QUIET_DIAGNOSTIC", "STRUCTURED_FLAT"}
            for row in groups
        ):
            raise InstrumentError("flat exposure group has an invalid state")
    elif status == "FLAT_DIAGNOSTIC_UNDETERMINED":
        if not any(
            isinstance(row, dict) and row.get("reason")
            for row in groups
        ):
            raise InstrumentError("undetermined flat status lacks a reason")
    else:
        raise InstrumentError(f"unsupported flat status {status!r}")


def _is_reparse(stat_result: os.stat_result) -> bool:
    attributes = getattr(stat_result, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    return bool(attributes & reparse)


def walk_regular_files(root: Path) -> list[Path]:
    root = root.absolute()
    if not root.is_dir():
        raise InstrumentError(f"missing directory: {root}")
    output: list[Path] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as entries:
            ordered = sorted(entries, key=lambda entry: entry.name.casefold())
        for entry in ordered:
            path = Path(entry.path)
            info = entry.stat(follow_symlinks=False)
            if entry.is_symlink() or _is_reparse(info):
                raise InstrumentError(f"reparse point/symlink is forbidden: {path}")
            if stat.S_ISDIR(info.st_mode):
                visit(path)
            elif stat.S_ISREG(info.st_mode):
                output.append(path.absolute())
            else:
                raise InstrumentError(f"non-regular filesystem entry is forbidden: {path}")

    visit(root)
    return output


def _reject_reparse_components(path: Path) -> None:
    absolute = path.absolute()
    chain = [absolute, *absolute.parents]
    for candidate in reversed(chain):
        if not candidate.exists():
            continue
        info = candidate.lstat()
        if candidate.is_symlink() or _is_reparse(info):
            raise InstrumentError(
                f"path contains a symlink/reparse component: {candidate}"
            )


def stat_snapshot(paths: Sequence[Path], root: Path) -> dict[str, Any]:
    rows = []
    for path in sorted(paths, key=lambda item: normalized_path(item)):
        info = path.stat()
        rows.append(
            {
                "relative_path": str(path.relative_to(root)).replace("/", "\\"),
                "size": int(info.st_size),
                "mtime_ns": int(info.st_mtime_ns),
            }
        )
    return {
        "file_count": len(rows),
        "total_bytes": sum(row["size"] for row in rows),
        "stat_digest_sha256": canonical_json_sha256(rows),
    }


def enumerate_session(session_root: Path, config: dict[str, Any]) -> dict[str, Any]:
    session_root = session_root.absolute()
    if session_root.name.casefold() != config["expected_session_basename"].casefold():
        raise InstrumentError(
            f"session basename {session_root.name!r} does not match "
            f"{config['expected_session_basename']!r}"
        )
    all_files = walk_regular_files(session_root)
    extension = config["inventory"]["extension"].casefold()
    all_arw = [path for path in all_files if path.suffix.casefold() == extension]
    groups: dict[str, list[Path]] = {}
    claimed: set[str] = set()
    for group_name in config["stacks"]:
        group_root = session_root / group_name
        group_files = [
            path
            for path in walk_regular_files(group_root)
            if path.suffix.casefold() == extension
        ]
        groups[group_name] = group_files
        for path in group_files:
            key = normalized_path(path)
            if key in claimed:
                raise InstrumentError(f"ARW belongs to more than one group: {path}")
            claimed.add(key)
    unexpected = [
        path for path in all_arw if normalized_path(path) not in claimed
    ]
    return {
        "all_regular_files": all_files,
        "all_arw": all_arw,
        "groups": groups,
        "unexpected_arw": unexpected,
    }


def exiftool_version(exiftool: Path) -> str:
    completed = subprocess.run(
        [str(exiftool), "-ver"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    if completed.returncode != 0:
        raise InstrumentError(
            f"ExifTool -ver failed with {completed.returncode}: {completed.stderr}"
        )
    return completed.stdout.strip()


def run_exiftool(
    exiftool: Path,
    group_root: Path,
    tags: Sequence[str],
    *,
    numeric: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    command = [str(exiftool), "-json", "-r", "-ext", "ARW"]
    if numeric:
        command.append("-n")
    command.extend(f"-{tag}" for tag in tags)
    command.extend(["--", str(group_root)])
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=False,
    )
    record = {
        "argv": command,
        "command_line_windows": subprocess.list2cmdline(command),
        "returncode": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "stderr": completed.stderr,
    }
    if completed.returncode != 0:
        raise InstrumentError(
            f"ExifTool failed for {group_root} with {completed.returncode}: "
            f"{completed.stderr}"
        )
    try:
        records = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise InstrumentError(f"ExifTool returned invalid JSON: {error}") from error
    if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
        raise InstrumentError("ExifTool JSON is not a list of objects")
    return records, record


def _capture_time_text(record: dict[str, Any]) -> str:
    direct = record.get("SubSecDateTimeOriginal")
    if direct:
        return str(direct)
    base = record.get("DateTimeOriginal")
    if not base:
        raise InstrumentError(
            f"capture timestamp missing: {record.get('SourceFile', '<unknown>')}"
        )
    subsecond = str(record.get("SubSecTimeOriginal") or "").strip()
    offset = str(record.get("OffsetTimeOriginal") or "").strip()
    suffix = f".{subsecond}" if subsecond else ""
    return f"{base}{suffix}{offset}"


def parse_capture_time(record: dict[str, Any]) -> tuple[datetime, str]:
    raw = _capture_time_text(record)
    for fmt in (
        "%Y:%m:%d %H:%M:%S.%f%z",
        "%Y:%m:%d %H:%M:%S%z",
        "%Y:%m:%d %H:%M:%S.%f",
        "%Y:%m:%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(raw, fmt), raw
        except ValueError:
            continue
    raise InstrumentError(f"unsupported capture timestamp {raw!r}")


def focus_histogram(frames: Sequence[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        return {
            "status": "MISSING_FOCUS_POSITION_2",
            "missing_count": 0,
            "histogram": [],
            "minimum": None,
            "maximum": None,
        }
    values = [frame.get("FocusPosition2") for frame in frames]
    if any(not exact_number(value) for value in values):
        return {
            "status": "MISSING_FOCUS_POSITION_2",
            "missing_count": sum(not exact_number(value) for value in values),
            "histogram": [],
            "minimum": None,
            "maximum": None,
        }
    counter = collections.Counter(float(value) for value in values)
    histogram = [
        {
            "value": int(value) if value.is_integer() else value,
            "frame_count": counter[value],
        }
        for value in sorted(counter)
    ]
    return {
        "status": "COMPLETE",
        "missing_count": 0,
        "histogram": histogram,
        "minimum": histogram[0]["value"],
        "maximum": histogram[-1]["value"],
    }


def capture_units_from_frames(
    frames: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for frame in frames:
        relative = frame.get("relative_path")
        if not isinstance(relative, str) or "\\" not in relative:
            raise InstrumentError("frame relative_path has no capture-unit directory")
        unit_id = relative.rsplit("\\", 1)[0]
        grouped[unit_id].append(frame)
    return [
        {
            "capture_unit_id": unit_id,
            "parent_stack_id": unit_id,
            "frame_count": len(grouped[unit_id]),
            "source_file_ids": sorted(
                frame["raw_sha256"] for frame in grouped[unit_id]
            ),
        }
        for unit_id in sorted(grouped, key=str.casefold)
    ]


def merge_exif_records(
    files: Sequence[Path],
    numeric_records: Sequence[dict[str, Any]],
    formatted_records: Sequence[dict[str, Any]],
    group_name: str,
    session_root: Path,
) -> list[dict[str, Any]]:
    expected = {normalized_path(path): path for path in files}
    numeric = {
        normalized_path(row.get("SourceFile", "")): row for row in numeric_records
    }
    formatted = {
        normalized_path(row.get("SourceFile", "")): row for row in formatted_records
    }
    if set(numeric) != set(expected):
        raise InstrumentError(
            f"numeric ExifTool/file enumeration mismatch for {group_name}: "
            f"missing={sorted(set(expected)-set(numeric))[:3]}, "
            f"extra={sorted(set(numeric)-set(expected))[:3]}"
        )
    if set(formatted) != set(expected):
        raise InstrumentError(
            f"formatted ExifTool/file enumeration mismatch for {group_name}"
        )
    output: list[dict[str, Any]] = []
    for key, path in expected.items():
        row = dict(numeric[key])
        formatted_row = formatted[key]
        for field, value in formatted_row.items():
            if field not in {"SourceFile", "FileName", "Directory"}:
                row[f"formatted_{field}"] = value
        captured, captured_text = parse_capture_time(row)
        info = path.stat()
        frame = {
            "group": group_name,
            "relative_path": str(path.relative_to(session_root)).replace("/", "\\"),
            "absolute_path": str(path),
            "filename": path.name,
            "byte_size": int(info.st_size),
            "raw_sha256": sha256_file(path),
            "capture_time": captured_text,
            "_capture_sort": captured,
        }
        for field, value in row.items():
            if field not in {"SourceFile", "Directory", "FileName"}:
                frame[field] = value
        output.append(frame)
    output.sort(
        key=lambda frame: (
            frame["_capture_sort"],
            frame["filename"].casefold(),
            frame["relative_path"].casefold(),
        )
    )
    for index, frame in enumerate(output):
        frame["ordered_index"] = index
        frame["sort_key"] = [
            frame["capture_time"],
            frame["filename"],
        ]
        del frame["_capture_sort"]
    return output


def inventory_payload(
    session_root: Path,
    exiftool: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    if not exiftool.is_file():
        raise InstrumentError(f"missing ExifTool binary: {exiftool}")
    enumerated = enumerate_session(session_root, config)
    before = stat_snapshot(enumerated["all_regular_files"], session_root)
    stacks: dict[str, Any] = {}
    command_records = []
    for group_name, files in enumerated["groups"].items():
        group_root = session_root / group_name
        numeric, numeric_command = run_exiftool(
            exiftool,
            group_root,
            config["inventory"]["numeric_tags"],
            numeric=True,
        )
        formatted, formatted_command = run_exiftool(
            exiftool,
            group_root,
            config["inventory"]["formatted_tags"],
            numeric=False,
        )
        command_records.extend(
            [
                {"group": group_name, "mode": "numeric", **numeric_command},
                {"group": group_name, "mode": "formatted", **formatted_command},
            ]
        )
        frames = merge_exif_records(
            files, numeric, formatted, group_name, session_root
        )
        stacks[group_name] = {
            "expected_frames": config["stacks"][group_name]["expected_frames"],
            "observed_frames": len(frames),
            "count_matches": len(frames)
            == config["stacks"][group_name]["expected_frames"],
            "role": config["stacks"][group_name]["role"],
            "focus_position_2": focus_histogram(frames),
            "exposure_time_histogram": [
                {"value": value, "frame_count": count}
                for value, count in sorted(
                    collections.Counter(
                        "<MISSING>"
                        if frame.get("ExposureTime") is None
                        else str(frame.get("ExposureTime"))
                        for frame in frames
                    ).items()
                )
            ],
            "capture_units": capture_units_from_frames(frames),
            "frames": frames,
        }
    after_files = walk_regular_files(session_root)
    after = stat_snapshot(after_files, session_root)
    unchanged = before == after
    if not unchanged:
        raise InstrumentError("source tree changed during metadata inventory")

    sw4 = stacks["tilted-sw4-cpl"]["focus_position_2"]
    sw10 = stacks["tilted-sw10-cpl"]["focus_position_2"]
    coarse_equal = bool(
        sw4["status"] == "COMPLETE"
        and sw10["status"] == "COMPLETE"
        and sw4["minimum"] == sw10["minimum"]
        and sw4["maximum"] == sw10["maximum"]
    )
    coarse_status = (
        "COARSE_ENCODER_RANGE_EQUAL"
        if coarse_equal
        else (
            "COARSE_ENCODER_MISSING"
            if sw4["status"] != "COMPLETE" or sw10["status"] != "COMPLETE"
            else "COARSE_ENCODER_RANGE_NOT_EQUAL"
        )
    )
    counts_match = all(row["count_matches"] for row in stacks.values())
    status = (
        "INVENTORY_MATCH"
        if counts_match and not enumerated["unexpected_arw"]
        else "INVENTORY_MISMATCH"
    )
    payload = {
        "schema": "m135-slide-inventory-v1",
        "label": LABEL,
        "stage": "A",
        "status": status,
        "config_sha256": config_sha256(config_path),
        "invocation": invocation_record(config_path, config),
        "source_root": str(session_root.absolute()),
        "source_snapshot": {
            "before": before,
            "after": after,
            "unchanged": unchanged,
        },
        "exiftool": {
            "path": str(exiftool.absolute()),
            "sha256": sha256_file(exiftool),
            "version": exiftool_version(exiftool),
            "commands": command_records,
        },
        "stacks": stacks,
        "unexpected_arw": [
            str(path.relative_to(session_root)).replace("/", "\\")
            for path in enumerated["unexpected_arw"]
        ],
        "coarse_encoder": {
            "status": coarse_status,
            "tilted_sw4": sw4,
            "tilted_sw10": sw10,
            "predicate": (
                "complete FocusPosition2 in both stacks and equal minima/maxima"
            ),
        },
        "proceed_to_decode": status == "INVENTORY_MATCH",
    }
    validate_artifact(payload)
    validate_inventory_semantics(payload, config)
    return payload


def decode_rawpy(path: Path) -> RawSnapshot:
    import rawpy

    # raw_image_visible is a borrowed LibRaw view.  Every array used after the
    # context exits is allocated and copied inside this with-block (rule 32).
    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, dtype=np.uint16, copy=True, order="C")
        pattern = np.array(raw.raw_pattern, copy=True)
        color_desc = bytes(raw.color_desc)
        black = np.array(raw.black_level_per_channel, dtype=np.float64, copy=True)
        white = int(raw.white_level)
        wb = np.array(raw.camera_whitebalance, dtype=np.float64, copy=True)
        full = getattr(raw, "raw_image", None)
        full_shape = tuple(int(value) for value in full.shape) if full is not None else None
        del full
    return RawSnapshot(
        mosaic=mosaic,
        raw_pattern=pattern,
        color_desc=color_desc,
        black_levels=black,
        container_white=white,
        camera_whitebalance=wb,
        full_buffer_shape=full_shape,
    )


def validate_raw_snapshot(snapshot: RawSnapshot, config: dict[str, Any]) -> None:
    expected = config["decode"]
    if snapshot.mosaic.shape != tuple(expected["expected_rawpy_visible_shape_yx"]):
        raise InstrumentError(
            f"rawpy visible shape {snapshot.mosaic.shape} != "
            f"{tuple(expected['expected_rawpy_visible_shape_yx'])}"
        )
    if snapshot.mosaic.dtype != np.dtype(np.uint16) or snapshot.mosaic.ndim != 2:
        raise InstrumentError(
            f"rawpy visible mosaic must be uint16 2-D, got "
            f"{snapshot.mosaic.shape} {snapshot.mosaic.dtype}"
        )
    if snapshot.mosaic.flags["OWNDATA"] is not True:
        raise InstrumentError("rawpy visible mosaic is not an owned copy")
    pattern = snapshot.raw_pattern.tolist()
    if pattern != expected["expected_cfa_pattern"]:
        raise InstrumentError(f"unsupported CFA pattern {pattern}")
    color_desc = snapshot.color_desc.rstrip(b"\0").decode("ascii", errors="strict")
    if color_desc != expected["expected_color_desc"]:
        raise InstrumentError(f"unsupported raw color_desc {color_desc!r}")
    if (
        snapshot.black_levels.shape != (4,)
        or not np.all(np.isfinite(snapshot.black_levels))
        or snapshot.black_levels.tolist() != expected["expected_black_levels"]
    ):
        raise InstrumentError(
            f"black-level contract mismatch: {snapshot.black_levels.tolist()}"
        )
    if snapshot.container_white != expected["expected_container_white"]:
        raise InstrumentError(
            f"container white {snapshot.container_white} != "
            f"{expected['expected_container_white']}"
        )


def array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return sha256_bytes(memoryview(contiguous).tobytes())


def canonical_array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    digest = hashlib.sha256()
    digest.update(contiguous.dtype.str.encode("ascii"))
    digest.update(b"\0")
    digest.update(struct.pack(">I", contiguous.ndim))
    for size in contiguous.shape:
        digest.update(struct.pack(">Q", int(size)))
    digest.update(memoryview(contiguous))
    return digest.hexdigest()


def green_from_snapshot(snapshot: RawSnapshot, config: dict[str, Any]) -> GreenFrame:
    validate_raw_snapshot(snapshot, config)
    mosaic = snapshot.mosaic
    g1_raw = np.array(mosaic[0::2, 1::2], copy=True)
    g2_raw = np.array(mosaic[1::2, 0::2], copy=True)
    if g1_raw.shape != g2_raw.shape:
        raise InstrumentError("G1/G2 active-area shapes differ")
    b1 = np.float32(snapshot.black_levels[1])
    b2 = np.float32(snapshot.black_levels[3])
    g1 = np.maximum(g1_raw.astype(np.float32) - b1, np.float32(0.0))
    g2 = np.maximum(g2_raw.astype(np.float32) - b2, np.float32(0.0))
    green = np.float32(0.5) * (g1 + g2)
    if not np.all(np.isfinite(green)):
        raise InstrumentError("camera-linear green decode is non-finite")
    clip_mask = (g1_raw >= snapshot.container_white) | (
        g2_raw >= snapshot.container_white
    )
    report = {
        "visible_mosaic_shape_yx": list(mosaic.shape),
        "full_buffer_shape_yx_not_used_for_statistics": (
            list(snapshot.full_buffer_shape)
            if snapshot.full_buffer_shape is not None
            else None
        ),
        "green_plane_shape_yx": list(green.shape),
        "green_plane_native_pitch_px": config["decode"][
            "green_plane_native_pitch_px"
        ],
        "frequency_conversion": (
            "f_native_cyc_per_px = f_green_plane_cyc_per_px / 2"
        ),
        "clip_fraction": float(np.mean(clip_mask, dtype=np.float64)),
        "container_white": snapshot.container_white,
        "raw_pattern": snapshot.raw_pattern.tolist(),
        "color_desc": snapshot.color_desc.rstrip(b"\0").decode("ascii"),
        "black_levels": snapshot.black_levels.tolist(),
        "camera_whitebalance": [
            float(value) if math.isfinite(float(value)) else None
            for value in snapshot.camera_whitebalance
        ],
    }
    return GreenFrame(
        green=green,
        clip_mask=clip_mask,
        raw_g1=g1_raw,
        raw_g2=g2_raw,
        report=report,
    )


def clip_fraction_allowed(mask: np.ndarray, config: dict[str, Any]) -> tuple[bool, float]:
    mask = np.asarray(mask)
    if mask.ndim != 2 or mask.size == 0:
        raise InstrumentError("clip selector requires a non-empty 2-D mask")
    fraction = float(np.mean(mask.astype(bool), dtype=np.float64))
    return fraction <= config["decode"]["maximum_clip_fraction"], fraction


def parse_rawler_payload(
    payload: bytes,
    expected: np.ndarray,
    *,
    keep_array: bool = False,
) -> dict[str, Any]:
    size = len(payload)
    if size < 16:
        raise InstrumentError("rawler crosscheck payload is truncated")
    header = payload[:16]
    y0, x0, height, width = struct.unpack("<IIII", header)
    expected_size = 16 + int(height) * int(width) * 2
    if size != expected_size:
        raise InstrumentError(
            f"rawler payload byte count {size} != expected {expected_size}"
        )
    if (y0, x0, height, width) != (0, 0, expected.shape[0], expected.shape[1]):
        raise InstrumentError(
            f"rawler payload header {(y0, x0, height, width)} does not match "
            f"rawpy overlap {(0, 0, expected.shape[0], expected.shape[1])}"
        )
    mapped = np.frombuffer(
        payload,
        dtype="<u2",
        offset=16,
        count=height * width,
    ).reshape((height, width))
    mismatch = np.argwhere(mapped != expected)
    if mismatch.size:
        y, x = (int(value) for value in mismatch[0])
        raise InstrumentError(
            f"rawpy/rawler pixel mismatch at ({x},{y}): "
            f"{int(expected[y, x])} != {int(mapped[y, x])}"
        )
    result = {
        "header_y_x_h_w": [y0, x0, height, width],
        "payload_sha256": sha256_bytes(payload[16:]),
        "payload_matches_rawpy": True,
        "rawpy_payload_sha256": array_sha256(expected.astype("<u2", copy=False)),
    }
    if keep_array:
        result["array"] = np.array(mapped, copy=True)
    del mapped
    return result


def parse_rawler_dump(
    path: Path,
    expected: np.ndarray,
    *,
    keep_array: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        raise InstrumentError(f"missing synthetic rawler payload: {path}")
    return parse_rawler_payload(
        path.read_bytes(), expected, keep_array=keep_array
    )


def run_rawler_crosscheck(
    binary: Path,
    raw_path: Path,
    expected_mosaic: np.ndarray,
    config: dict[str, Any],
) -> dict[str, Any]:
    if not binary.is_file():
        raise InstrumentError(f"missing rawler crosscheck binary: {binary}")
    command = [
        str(binary),
        str(raw_path),
        "0",
        "0",
        str(expected_mosaic.shape[0]),
        str(expected_mosaic.shape[1]),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=False,
        check=False,
    )
    stderr = completed.stderr.decode("utf-8", errors="strict")
    record = {
        "argv": command,
        "command_line_windows": subprocess.list2cmdline(command),
        "returncode": completed.returncode,
        "stdout_byte_count": len(completed.stdout),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr": stderr,
    }
    if completed.returncode != 0:
        raise InstrumentError(
            f"rawler crosscheck failed with {completed.returncode}: "
            f"{stderr}"
        )
    active = ACTIVE_RE.search(stderr)
    buffer_height = BUFFER_HEIGHT_RE.search(stderr)
    stride = STRIDE_RE.search(stderr)
    if active is None or buffer_height is None or stride is None:
        raise InstrumentError("rawler crosscheck stderr lacks geometry")
    active_width, active_height, active_x, active_y = (
        int(value) for value in active.groups()
    )
    expected_active_yx = tuple(
        config["decode"]["expected_rawler_active_shape_yx"]
    )
    if (active_height, active_width) != expected_active_yx:
        raise InstrumentError(
            f"rawler active shape {(active_height, active_width)} != "
            f"{expected_active_yx}"
        )
    if active_x != 0 or active_y != 0:
        raise InstrumentError(
            f"rawler active origin {(active_x, active_y)} is not the frozen origin"
        )
    if active_height != expected_mosaic.shape[0] or active_width < expected_mosaic.shape[1]:
        raise InstrumentError("rawpy visible area is not a leading rawler active prefix")
    comparison = parse_rawler_payload(completed.stdout, expected_mosaic)
    record.update(
        {
            "binary_sha256": sha256_file(binary),
            "active_shape_yx": [active_height, active_width],
            "active_origin_xy": [active_x, active_y],
            "buffer_shape_yx": [int(buffer_height.group(1)), int(stride.group(1))],
            "rawpy_overlap_shape_yx": list(expected_mosaic.shape),
            "trailing_active_columns_not_in_rawpy": (
                active_width - expected_mosaic.shape[1]
            ),
            "comparison": comparison,
        }
    )
    return record


def _inventory_frames(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    frames = []
    for group_name in inventory["stacks"]:
        frames.extend(inventory["stacks"][group_name]["frames"])
    return frames


def decode_payload(
    inventory_path: Path,
    crosscheck_binary: Path,
    config_path: Path,
    config: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    inventory = load_json_object(inventory_path)
    validate_artifact(inventory)
    validate_inventory_semantics(inventory, config)
    if inventory["status"] != "INVENTORY_MATCH" or not inventory["proceed_to_decode"]:
        raise InstrumentError("decode requires an INVENTORY_MATCH artifact")
    frames_out = []
    failure: str | None = None
    for frame in _inventory_frames(inventory):
        raw_path = Path(frame["absolute_path"])
        observed_raw_hash = sha256_file(raw_path)
        if observed_raw_hash != frame["raw_sha256"]:
            raise InstrumentError(f"RAW hash drift before decode: {raw_path}")
        snapshot = decode_rawpy(raw_path)
        green = green_from_snapshot(snapshot, config)
        try:
            rawler = run_rawler_crosscheck(
                crosscheck_binary,
                raw_path,
                snapshot.mosaic,
                config,
            )
        except InstrumentError as error:
            failure = str(error)
            frames_out.append(
                {
                    "group": frame["group"],
                    "ordered_index": frame["ordered_index"],
                    "relative_path": frame["relative_path"],
                    "raw_sha256": observed_raw_hash,
                    "status": "CROSSCHECK_FAILED",
                    "error": str(error),
                }
            )
            break
        frames_out.append(
            {
                "group": frame["group"],
                "ordered_index": frame["ordered_index"],
                "relative_path": frame["relative_path"],
                "absolute_path": frame["absolute_path"],
                "raw_sha256": observed_raw_hash,
                "status": "PASS",
                "rawpy": {
                    **green.report,
                    "visible_mosaic_sha256": array_sha256(snapshot.mosaic),
                    "visible_mosaic_canonical_sha256": canonical_array_sha256(
                        snapshot.mosaic
                    ),
                    "g1_sha256": array_sha256(green.raw_g1),
                    "g2_sha256": array_sha256(green.raw_g2),
                    "camera_linear_green_sha256": array_sha256(green.green),
                    "camera_linear_green_canonical_sha256": canonical_array_sha256(
                        green.green
                    ),
                },
                "rawler_crosscheck": rawler,
            }
        )
    status = (
        "DECODE_CROSSCHECK_PASS"
        if failure is None and len(frames_out) == len(_inventory_frames(inventory))
        else "DECODE_CROSSCHECK_FAILED"
    )
    payload = {
        "schema": "m135-slide-decode-v1",
        "label": LABEL,
        "stage": "B",
        "status": status,
        "config_sha256": config_sha256(config_path),
        "inventory_sha256": sha256_file(inventory_path),
        "invocation": invocation_record(config_path, config),
        "decoder_contract": {
            "primary": "rawpy/LibRaw raw_image_visible copied inside context",
            "secondary": (
                "lane-local executable using the existing strehl-raw/rawler API"
            ),
            "crosscheck_every_frame": True,
            "canonical_overlap": config["decode"]["canonical_overlap"],
            "crosscheck_manifest_path": str(CROSSCHECK_MANIFEST),
            "crosscheck_manifest_sha256": normalized_text_sha256(
                CROSSCHECK_MANIFEST
            ),
            "crosscheck_source_path": str(CROSSCHECK_SOURCE),
            "crosscheck_source_sha256": normalized_text_sha256(
                CROSSCHECK_SOURCE
            ),
            "crosscheck_lock_path": str(CROSSCHECK_LOCK),
            "crosscheck_lock_sha256": normalized_text_sha256(CROSSCHECK_LOCK),
            "binary_path": str(crosscheck_binary.absolute()),
            "binary_sha256": sha256_file(crosscheck_binary),
            "transport": (
                "binary active-area payload on stdout; metadata on stderr; "
                "no filesystem scratch or capture-tree write path"
            ),
            "failure": failure,
        },
        "frames": frames_out,
        "proceed_to_range": status == "DECODE_CROSSCHECK_PASS",
    }
    validate_artifact(payload)
    validate_decode_semantics(payload, inventory)
    return payload, 0 if status == "DECODE_CROSSCHECK_PASS" else 1


def green_frequency_grid_native(shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Frequency grid for a plane sampled every two native sensor pixels."""

    height, width = shape
    fy_plane = fft.fftfreq(height).astype(np.float32)[:, None]
    fx_plane = fft.rfftfreq(width).astype(np.float32)[None, :]
    fy_native = fy_plane / np.float32(2.0)
    fx_native = fx_plane / np.float32(2.0)
    radius_native = np.sqrt(
        fy_native * fy_native + fx_native * fx_native,
        dtype=np.float32,
    )
    return fy_native, fx_native, radius_native


def raised_cosine_lowpass(
    radius_native: np.ndarray, passband: float, stopband: float
) -> np.ndarray:
    if not 0.0 <= passband <= stopband:
        raise InstrumentError("invalid low-pass transition")
    mask = np.zeros(radius_native.shape, dtype=np.float32)
    mask[radius_native <= passband] = np.float32(1.0)
    transition = (radius_native > passband) & (radius_native < stopband)
    if stopband > passband:
        phase = (radius_native[transition] - passband) / (stopband - passband)
        mask[transition] = np.float32(0.5) * (
            np.float32(1.0) + np.cos(np.pi * phase).astype(np.float32)
        )
    return mask


def spectral_views(
    green: np.ndarray, config: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if green.dtype != np.dtype(np.float32) or green.ndim != 2:
        raise InstrumentError("spectral views require a float32 green plane")
    if not np.all(np.isfinite(green)):
        raise InstrumentError("spectral input is non-finite")
    _, _, radius = green_frequency_grid_native(green.shape)
    registration = config["registration"]
    focus = config["focus"]
    spectrum = fft.rfft2(green, workers=1)
    registration_mask = raised_cosine_lowpass(
        radius,
        registration["lowpass_pass_native_cyc_per_px"],
        registration["lowpass_stop_native_cyc_per_px"],
    )
    focus_mask = (radius <= focus["lowpass_max_native_cyc_per_px"]).astype(
        np.float32
    )
    registration_full = fft.irfft2(
        spectrum * registration_mask,
        s=green.shape,
        workers=1,
    ).astype(np.float32)
    focus_full = fft.irfft2(
        spectrum * focus_mask,
        s=green.shape,
        workers=1,
    ).astype(np.float32)
    downsample = int(registration["downsample_green_plane"])
    registration_small = np.ascontiguousarray(
        registration_full[::downsample, ::downsample]
    )
    if not (
        np.all(np.isfinite(registration_small))
        and np.all(np.isfinite(focus_full))
    ):
        raise InstrumentError("spectral filtering produced non-finite values")
    report = {
        "green_plane_native_pitch_px": 2.0,
        "frequency_conversion": "f_native=f_green_plane/2",
        "registration_pass_native_cyc_per_px": registration[
            "lowpass_pass_native_cyc_per_px"
        ],
        "registration_stop_native_cyc_per_px": registration[
            "lowpass_stop_native_cyc_per_px"
        ],
        "registration_mask_max_above_stop": float(
            np.max(
                registration_mask[
                    radius >= registration["lowpass_stop_native_cyc_per_px"]
                ],
                initial=np.float32(0.0),
            )
        ),
        "focus_hard_cap_native_cyc_per_px": focus[
            "lowpass_max_native_cyc_per_px"
        ],
        "focus_mask_max_frequency_native_cyc_per_px": float(
            np.max(radius[focus_mask > 0], initial=np.float32(0.0))
        ),
        "registration_downsample_green_plane": downsample,
    }
    return registration_small, focus_full, report


def robust_normalize(image: np.ndarray) -> np.ndarray:
    image = np.asarray(image, dtype=np.float32)
    median = float(np.median(image))
    mad = float(np.median(np.abs(image - median)))
    scale = max(1.4826 * mad, float(np.std(image)), 1e-12)
    return np.ascontiguousarray((image - median) / scale, dtype=np.float32)


def order_quad(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    if points.shape != (4, 2) or not np.all(np.isfinite(points)):
        raise InstrumentError("quadrilateral must be finite 4x2 coordinates")
    centre = np.mean(points, axis=0)
    angles = np.arctan2(points[:, 1] - centre[1], points[:, 0] - centre[0])
    ordered = points[np.argsort(angles)]
    start = int(np.argmin(np.sum(ordered, axis=1)))
    ordered = np.roll(ordered, -start, axis=0)
    cross = np.cross(ordered[1] - ordered[0], ordered[2] - ordered[1])
    if cross < 0:
        ordered = ordered[[0, 3, 2, 1]]
    contour = ordered.astype(np.float32)[:, None, :]
    if not cv2.isContourConvex(contour):
        raise InstrumentError("quadrilateral is not convex")
    if abs(float(cv2.contourArea(contour))) <= 0.0:
        raise InstrumentError("quadrilateral has zero area")
    return ordered


def _quad_key(points: np.ndarray) -> tuple[int, ...]:
    return tuple(int(round(value * 4.0)) for value in points.ravel())


def _candidate_quads(mask: np.ndarray, gradient: np.ndarray, config: dict[str, Any]) -> list[dict[str, Any]]:
    quad_config = config["registration"]["quadrilateral"]
    contours, _ = cv2.findContours(
        mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    height, width = mask.shape
    frame_area = float(height * width)
    candidates: dict[tuple[int, ...], dict[str, Any]] = {}
    for contour in contours:
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0.0:
            continue
        approximation = cv2.approxPolyDP(
            contour,
            quad_config["approximation_fraction"] * perimeter,
            True,
        )
        if len(approximation) != 4 or not cv2.isContourConvex(approximation):
            continue
        points = order_quad(approximation[:, 0, :])
        area = abs(float(cv2.contourArea(points.astype(np.float32)[:, None, :])))
        area_fraction = area / frame_area
        if not (
            quad_config["minimum_area_fraction"]
            <= area_fraction
            <= quad_config["maximum_area_fraction"]
        ):
            continue
        edges = np.roll(points, -1, axis=0) - points
        lengths = np.sqrt(np.sum(edges * edges, axis=1))
        if float(np.min(lengths)) < quad_config["minimum_edge_px_downsampled"]:
            continue
        edge_mask = np.zeros(mask.shape, dtype=np.uint8)
        cv2.polylines(
            edge_mask,
            [np.rint(points).astype(np.int32)[:, None, :]],
            True,
            255,
            2,
        )
        support = float(np.mean(gradient[edge_mask > 0], dtype=np.float64))
        score = area_fraction * (1.0 + support)
        key = _quad_key(points)
        row = {
            "points": points,
            "area_fraction": area_fraction,
            "edge_support": support,
            "score": score,
        }
        if key not in candidates or score > candidates[key]["score"]:
            candidates[key] = row
    return list(candidates.values())


def detect_quadrilateral(
    lowpass_image: np.ndarray, config: dict[str, Any]
) -> tuple[np.ndarray, dict[str, Any]]:
    normalized = robust_normalize(lowpass_image)
    low = float(np.percentile(normalized, 1.0))
    high = float(np.percentile(normalized, 99.0))
    if not high > low:
        raise InstrumentError("low-pass quadrilateral input has no dynamic range")
    u8 = np.clip((normalized - low) / (high - low) * 255.0, 0.0, 255.0).astype(
        np.uint8
    )
    quad_config = config["registration"]["quadrilateral"]
    gradient_x = cv2.Sobel(u8, cv2.CV_32F, 1, 0, ksize=3)
    gradient_y = cv2.Sobel(u8, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(gradient_x, gradient_y)
    if float(np.max(gradient)) > 0.0:
        gradient = gradient / float(np.max(gradient))
    edges = cv2.Canny(
        u8,
        int(quad_config["canny_low"]),
        int(quad_config["canny_high"]),
    )
    kernel_size = int(quad_config["morphology_kernel"])
    kernel = np.ones((kernel_size, kernel_size), dtype=np.uint8)
    edge_mask = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    edge_mask = cv2.dilate(edge_mask, kernel, iterations=1)
    _, otsu = cv2.threshold(u8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks = [edge_mask, otsu, cv2.bitwise_not(otsu)]
    candidates: dict[tuple[int, ...], dict[str, Any]] = {}
    for mask in masks:
        for row in _candidate_quads(mask, gradient, config):
            key = _quad_key(row["points"])
            if key not in candidates or row["score"] > candidates[key]["score"]:
                candidates[key] = row
    ordered = sorted(candidates.values(), key=lambda row: row["score"], reverse=True)
    if not ordered:
        raise InstrumentError("no low-pass quadrilateral satisfied the frozen selector")
    best = ordered[0]
    second_score = ordered[1]["score"] if len(ordered) > 1 else 0.0
    ratio = (
        float("inf") if second_score <= 0.0 else best["score"] / second_score
    )
    if (
        len(ordered) > 1
        and ratio
        < quad_config["minimum_best_to_second_score_ratio"]
    ):
        raise InstrumentError(
            f"quadrilateral selector is ambiguous: best/second={ratio:.6f}"
        )
    return best["points"], {
        "candidate_count": len(ordered),
        "best_score": round(float(best["score"]), 8),
        "second_score": round(float(second_score), 8),
        "best_to_second_score_ratio": (
            round(float(ratio), 8) if math.isfinite(ratio) else None
        ),
        "area_fraction": round(float(best["area_fraction"]), 8),
        "edge_support": round(float(best["edge_support"]), 8),
        "points_downsampled_xy": best["points"].tolist(),
        "input_domain": (
            "raised-cosine low-pass with exact zero at and above the "
            "registered stop frequency"
        ),
    }


def fixed_lattice(config: dict[str, Any]) -> np.ndarray:
    rows = int(config["lattice"]["rows"])
    columns = int(config["lattice"]["columns"])
    return np.asarray(
        [
            ((column + 0.5) / columns, (row + 0.5) / rows)
            for row in range(rows)
            for column in range(columns)
        ],
        dtype=np.float64,
    )


def validate_fixed_lattice(points: np.ndarray, config: dict[str, Any]) -> None:
    expected = fixed_lattice(config)
    if points.shape != expected.shape or not np.array_equal(points, expected):
        raise InstrumentError("normalized 8x8 lattice was mutated")


def map_lattice_to_quad(lattice: np.ndarray, quad: np.ndarray) -> np.ndarray:
    validate = np.asarray(lattice, dtype=np.float64)
    quad = order_quad(quad)
    unit = np.asarray([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=np.float32)
    transform = cv2.getPerspectiveTransform(unit, quad.astype(np.float32))
    homogeneous = np.column_stack([validate, np.ones(len(validate))])
    mapped = homogeneous @ transform.T
    if np.any(np.abs(mapped[:, 2]) < 1e-12):
        raise InstrumentError("quadrilateral homography maps a lattice point to infinity")
    return mapped[:, :2] / mapped[:, 2:3]


def _polygon_mask(shape: tuple[int, int], quad: np.ndarray) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    cv2.fillConvexPoly(mask, np.rint(order_quad(quad)).astype(np.int32), 255)
    return mask


def register_affine(
    reference: np.ndarray,
    moving: np.ndarray,
    reference_quad: np.ndarray,
    config: dict[str, Any],
) -> tuple[np.ndarray, dict[str, Any]]:
    if reference.shape != moving.shape:
        raise InstrumentError("registration images have different shapes")
    ref = robust_normalize(reference)
    mov = robust_normalize(moving)
    registration = config["registration"]
    phase_shift, phase_response = cv2.phaseCorrelate(ref, mov)
    cx = reference.shape[1] / 2.0
    cy = reference.shape[0] / 2.0
    criteria = (
        cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,
        int(registration["ecc_iterations"]),
        float(registration["ecc_epsilon"]),
    )
    mask = _polygon_mask(reference.shape, reference_quad)
    best: tuple[float, np.ndarray] | None = None
    errors = []
    for scale in registration["scale_seeds"]:
        seed = np.asarray(
            [
                [
                    scale,
                    0.0,
                    float(phase_shift[0]) + cx * (1.0 - scale),
                ],
                [
                    0.0,
                    scale,
                    float(phase_shift[1]) + cy * (1.0 - scale),
                ],
            ],
            dtype=np.float32,
        )
        try:
            correlation, fitted = cv2.findTransformECC(
                ref,
                mov,
                seed,
                cv2.MOTION_AFFINE,
                criteria,
                mask,
                int(registration["ecc_gaussian_filter_size"]),
            )
        except cv2.error as error:
            errors.append(str(error))
            continue
        if best is None or float(correlation) > best[0]:
            best = (float(correlation), fitted.copy())
    if best is None:
        raise InstrumentError(
            "low-pass ECC registration failed for every seed: "
            + " | ".join(errors[:2])
        )
    correlation, affine = best
    if correlation < registration["minimum_ecc_correlation"]:
        raise InstrumentError(
            f"low-pass ECC correlation {correlation:.6f} is below "
            f"{registration['minimum_ecc_correlation']}"
        )
    return affine.astype(np.float64), {
        "ecc_correlation": round(float(correlation), 8),
        "phase_seed_shift_xy_downsampled": [
            round(float(phase_shift[0]), 8),
            round(float(phase_shift[1]), 8),
        ],
        "phase_seed_response": round(float(phase_response), 8),
        "affine_reference_to_input_downsampled": np.round(
            affine.astype(np.float64), 8
        ).tolist(),
    }


def affine_to_full_green(affine: np.ndarray, downsample: int) -> np.ndarray:
    full = np.asarray(affine, dtype=np.float64).copy()
    if full.shape != (2, 3):
        raise InstrumentError("affine transform must be 2x3")
    full[:, 2] *= float(downsample)
    return full


def apply_affine(points: np.ndarray, affine: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float64)
    homogeneous = np.column_stack([points, np.ones(len(points))])
    return homogeneous @ np.asarray(affine, dtype=np.float64).T


def patch_is_guarded(
    centre: Sequence[float],
    patch_size: int,
    image_shape: tuple[int, int],
    quad: np.ndarray,
    minimum_guard: float,
) -> bool:
    x, y = (float(value) for value in centre)
    half = patch_size / 2.0
    corners = (
        (x - half, y - half),
        (x + half, y - half),
        (x + half, y + half),
        (x - half, y + half),
    )
    height, width = image_shape
    contour = order_quad(quad).astype(np.float32)[:, None, :]
    for px, py in corners:
        if px < 0 or py < 0 or px >= width or py >= height:
            return False
        distance = cv2.pointPolygonTest(contour, (float(px), float(py)), True)
        if distance < minimum_guard:
            return False
    return True


def extract_patch(image: np.ndarray, centre: Sequence[float], size: int) -> np.ndarray:
    if size <= 0 or size % 2:
        raise InstrumentError("patch size must be a positive even integer")
    x, y = (float(value) for value in centre)
    x0 = int(round(x)) - size // 2
    y0 = int(round(y)) - size // 2
    patch = image[y0 : y0 + size, x0 : x0 + size]
    if patch.shape != (size, size):
        raise InstrumentError(
            f"patch at {(x, y)} is outside image {image.shape}"
        )
    if not np.all(np.isfinite(patch)):
        raise InstrumentError("patch contains non-finite samples")
    return np.ascontiguousarray(patch)


def focus_band_power(patch: np.ndarray, config: dict[str, Any]) -> float:
    patch = np.asarray(patch, dtype=np.float32)
    mean = float(np.mean(patch, dtype=np.float64))
    if mean < config["focus"]["minimum_patch_mean_dn"]:
        raise InstrumentError(f"patch mean {mean:.6g} is below the focus floor")
    normalized = patch / np.float32(mean) - np.float32(1.0)
    window_y = np.hanning(patch.shape[0]).astype(np.float32)
    window_x = np.hanning(patch.shape[1]).astype(np.float32)
    window = window_y[:, None] * window_x[None, :]
    spectrum = fft.rfft2(normalized * window, workers=1)
    _, _, radius = green_frequency_grid_native(patch.shape)
    focus = config["focus"]
    band = (
        (radius >= focus["band_min_native_cyc_per_px"])
        & (radius <= focus["band_max_native_cyc_per_px"])
    )
    if not np.any(band):
        raise InstrumentError("focus band contains no Fourier bins")
    power = float(np.mean(np.abs(spectrum[band]) ** 2, dtype=np.float64))
    if not math.isfinite(power) or power <= 0.0:
        raise InstrumentError(f"focus power is invalid: {power}")
    return power


def estimate_peak(curve: Sequence[float], config: dict[str, Any]) -> PeakEstimate:
    values = np.asarray(curve, dtype=np.float64)
    if values.ndim != 1 or len(values) < 7 or not np.all(np.isfinite(values)):
        return PeakEstimate(False, "INVALID_CURVE", None, None, None, None)
    if np.any(values <= 0.0):
        return PeakEstimate(False, "NONPOSITIVE_CURVE", None, None, None, None)
    log_values = np.log(values)
    index = int(np.argmax(log_values))
    guard = int(config["focus"]["endpoint_guard_frames"])
    if index < guard or index >= len(values) - guard:
        return PeakEstimate(False, "ENDPOINT_PEAK", None, index, None, None)
    points = int(config["focus"]["quadratic_points"])
    half = points // 2
    if points % 2 == 0 or index - half < 0 or index + half >= len(values):
        return PeakEstimate(False, "INSUFFICIENT_LOCAL_SUPPORT", None, index, None, None)
    u = np.linspace(0.0, 1.0, len(values), dtype=np.float64)
    local_u = u[index - half : index + half + 1]
    local_y = log_values[index - half : index + half + 1]
    design = np.column_stack([local_u**2, local_u, np.ones_like(local_u)])
    coefficients, *_ = np.linalg.lstsq(design, local_y, rcond=None)
    quadratic, linear, intercept = (float(value) for value in coefficients)
    if not quadratic < 0.0:
        return PeakEstimate(
            False,
            "NONCONCAVE_PEAK",
            None,
            index,
            (quadratic, linear, intercept),
            None,
        )
    vertex = -linear / (2.0 * quadratic)
    if not local_u[0] <= vertex <= local_u[-1]:
        return PeakEstimate(
            False,
            "VERTEX_OUTSIDE_LOCAL_SUPPORT",
            None,
            index,
            (quadratic, linear, intercept),
            None,
        )
    fitted_peak = quadratic * vertex * vertex + linear * vertex + intercept
    prominence = min(
        fitted_peak - float(log_values[0]),
        fitted_peak - float(log_values[-1]),
    )
    if prominence < config["focus"]["minimum_log_prominence"]:
        return PeakEstimate(
            False,
            "LOW_PROMINENCE",
            None,
            index,
            (quadratic, linear, intercept),
            prominence,
        )
    return PeakEstimate(
        True,
        "INTERIOR_PEAK",
        float(vertex),
        index,
        (quadratic, linear, intercept),
        float(prominence),
    )


def huber_line_fit(
    x: np.ndarray, y: np.ndarray, config: dict[str, Any]
) -> dict[str, Any]:
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.ndim != 1 or y.shape != x.shape or len(x) < 2:
        raise InstrumentError("robust line fit requires matched 1-D arrays")
    design = np.column_stack([np.ones_like(x), x])
    weights = np.ones(len(x), dtype=np.float64)
    beta = np.linalg.lstsq(design, y, rcond=None)[0]
    converged = False
    iterations = 0
    for iterations in range(1, int(config["range_fit"]["maximum_iterations"]) + 1):
        root = np.sqrt(weights)
        candidate = np.linalg.lstsq(
            design * root[:, None], y * root, rcond=None
        )[0]
        residual = y - design @ candidate
        median = float(np.median(residual))
        mad = float(np.median(np.abs(residual - median)))
        scale = max(mad / 0.6744897501960817, 1e-12)
        cutoff = float(config["range_fit"]["huber_k"]) * scale
        new_weights = np.minimum(
            1.0, cutoff / np.maximum(np.abs(residual), 1e-12)
        )
        if (
            float(np.max(np.abs(candidate - beta)))
            <= config["range_fit"]["coefficient_tolerance"]
            and float(np.max(np.abs(new_weights - weights)))
            <= config["range_fit"]["weight_tolerance"]
        ):
            beta = candidate
            weights = new_weights
            converged = True
            break
        beta = candidate
        weights = new_weights
    residual = y - design @ beta
    quantile = float(
        np.quantile(
            np.abs(residual),
            config["range_fit"]["residual_quantile"],
            method=config["range_fit"]["quantile_method"],
        )
    )
    return {
        "intercept": float(beta[0]),
        "slope": float(beta[1]),
        "residuals": residual.tolist(),
        "weights": weights.tolist(),
        "q95_abs_residual": quantile,
        "iterations": iterations,
        "converged": converged,
    }


def node_density_ratio(
    frame_count_sw4: int,
    frame_count_sw10: int,
    u4: np.ndarray,
    u10: np.ndarray,
    intercept: float,
    slope: float,
) -> dict[str, Any]:
    if slope <= 0.0:
        return {
            "status": "UNDETERMINED_NONPOSITIVE_SLOPE",
            "common_interval_u4": None,
            "sw4_nodes": None,
            "sw10_nodes": None,
            "ratio_sw4_over_sw10": None,
        }
    mapped_u10 = (u10 - intercept) / slope
    lower = max(float(np.min(u4)), float(np.min(mapped_u10)))
    upper = min(float(np.max(u4)), float(np.max(mapped_u10)))
    if not upper > lower:
        return {
            "status": "UNDETERMINED_EMPTY_INTERVAL",
            "common_interval_u4": [lower, upper],
            "sw4_nodes": 0,
            "sw10_nodes": 0,
            "ratio_sw4_over_sw10": None,
        }
    nodes4 = np.linspace(0.0, 1.0, frame_count_sw4)
    nodes10_u4 = (
        np.linspace(0.0, 1.0, frame_count_sw10) - intercept
    ) / slope
    count4 = int(np.count_nonzero((nodes4 >= lower) & (nodes4 <= upper)))
    count10 = int(
        np.count_nonzero((nodes10_u4 >= lower) & (nodes10_u4 <= upper))
    )
    ratio = float(count4 / count10) if count10 > 0 else None
    return {
        "status": "OK" if ratio is not None else "UNDETERMINED_NO_SW10_NODES",
        "common_interval_u4": [lower, upper],
        "interval_width_u4": upper - lower,
        "sw4_nodes": count4,
        "sw10_nodes": count10,
        "ratio_sw4_over_sw10": ratio,
        "definition": (
            "frame-node counts per common u4-equivalent interval; interval "
            "width cancels from the reported ratio"
        ),
    }


def adjudicate_range_pairs(
    peaks4: Sequence[PeakEstimate],
    peaks10: Sequence[PeakEstimate],
    frame_count_sw4: int,
    frame_count_sw10: int,
    config: dict[str, Any],
) -> dict[str, Any]:
    if len(peaks4) != 64 or len(peaks10) != 64:
        raise InstrumentError("range adjudication requires the fixed 64 sites")
    joint_indices = [
        index
        for index, (left, right) in enumerate(zip(peaks4, peaks10, strict=True))
        if left.eligible and right.eligible
    ]
    minimum = int(config["range_fit"]["minimum_joint_eligible_sites"])
    if len(joint_indices) < minimum:
        return {
            "status": "IMAGE_RANGE_UNDETERMINED",
            "joint_eligible_count": len(joint_indices),
            "joint_eligible_indices": joint_indices,
            "robust_fit": None,
            "equivalence_bars": {
                "minimum_joint_eligible_sites": minimum,
                "maximum_abs_intercept": config["range_fit"][
                    "maximum_abs_intercept"
                ],
                "maximum_abs_slope_error": config["range_fit"][
                    "maximum_abs_slope_error"
                ],
                "maximum_q95_abs_residual": config["range_fit"][
                    "maximum_q95_abs_residual"
                ],
            },
            "node_density": None,
        }
    u4 = np.asarray([peaks4[index].u for index in joint_indices], dtype=np.float64)
    u10 = np.asarray([peaks10[index].u for index in joint_indices], dtype=np.float64)
    fit = huber_line_fit(u4, u10, config)
    predicates = {
        "minimum_joint_eligible_sites": len(joint_indices) >= minimum,
        "fit_converged": fit["converged"],
        "maximum_abs_intercept": abs(fit["intercept"])
        <= config["range_fit"]["maximum_abs_intercept"],
        "maximum_abs_slope_error": abs(fit["slope"] - 1.0)
        <= config["range_fit"]["maximum_abs_slope_error"],
        "maximum_q95_abs_residual": fit["q95_abs_residual"]
        <= config["range_fit"]["maximum_q95_abs_residual"],
        "positive_slope": fit["slope"] > 0.0,
    }
    status = (
        "IMAGE_RANGE_EQUIVALENT"
        if all(predicates.values())
        else "IMAGE_RANGE_NOT_EQUIVALENT"
    )
    density = node_density_ratio(
        frame_count_sw4,
        frame_count_sw10,
        u4,
        u10,
        fit["intercept"],
        fit["slope"],
    )
    return {
        "status": status,
        "joint_eligible_count": len(joint_indices),
        "joint_eligible_indices": joint_indices,
        "u4": u4.tolist(),
        "u10": u10.tolist(),
        "robust_fit": fit,
        "equivalence_bars": {
            "minimum_joint_eligible_sites": minimum,
            "maximum_abs_intercept": config["range_fit"][
                "maximum_abs_intercept"
            ],
            "maximum_abs_slope_error": config["range_fit"][
                "maximum_abs_slope_error"
            ],
            "maximum_q95_abs_residual": config["range_fit"][
                "maximum_q95_abs_residual"
            ],
            "predicates": predicates,
        },
        "node_density": density,
    }


def _decode_index(decode: dict[str, Any]) -> dict[str, dict[str, Any]]:
    output = {}
    for row in decode["frames"]:
        if row.get("status") != "PASS":
            continue
        key = row["relative_path"].casefold()
        if key in output:
            raise InstrumentError(f"duplicate decode row {row['relative_path']}")
        output[key] = row
    return output


def decode_green_checked(
    frame: dict[str, Any],
    decode_rows: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> tuple[GreenFrame, RawSnapshot]:
    key = frame["relative_path"].casefold()
    if key not in decode_rows:
        raise InstrumentError(f"decode artifact lacks {frame['relative_path']}")
    row = decode_rows[key]
    path = Path(frame["absolute_path"])
    if sha256_file(path) != frame["raw_sha256"]:
        raise InstrumentError(f"RAW hash drift: {path}", status="DATA_INTEGRITY_ERROR")
    snapshot = decode_rawpy(path)
    green = green_from_snapshot(snapshot, config)
    if array_sha256(snapshot.mosaic) != row["rawpy"]["visible_mosaic_sha256"]:
        raise InstrumentError(
            f"rawpy mosaic hash drift: {path}", status="DATA_INTEGRITY_ERROR"
        )
    if (
        array_sha256(green.green)
        != row["rawpy"]["camera_linear_green_sha256"]
    ):
        raise InstrumentError(
            f"camera-linear green hash drift: {path}",
            status="DATA_INTEGRITY_ERROR",
        )
    return green, snapshot


def _scaled_quad(quad_small: np.ndarray, downsample: int) -> np.ndarray:
    return np.asarray(quad_small, dtype=np.float64) * float(downsample)


def analyze_range_stack(
    group_name: str,
    inventory: dict[str, Any],
    decode_rows: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    frames = inventory["stacks"][group_name]["frames"]
    if len(frames) < 7:
        raise InstrumentError(f"{group_name}: too few frames for peak fitting")
    reference_index = len(frames) // 2
    reference_frame = frames[reference_index]
    reference_green, _ = decode_green_checked(reference_frame, decode_rows, config)
    reference_registration, reference_focus, spectral_report = spectral_views(
        reference_green.green, config
    )
    quad_small, quad_report = detect_quadrilateral(reference_registration, config)
    downsample = int(config["registration"]["downsample_green_plane"])
    quad_full = _scaled_quad(quad_small, downsample)
    lattice = fixed_lattice(config)
    validate_fixed_lattice(lattice, config)
    reference_centres = map_lattice_to_quad(lattice, quad_full)
    patch_size = int(config["lattice"]["patch_size_green_px"])
    guard = float(config["lattice"]["minimum_quad_guard_green_px"])
    for centre in reference_centres:
        if not patch_is_guarded(
            centre,
            patch_size,
            reference_focus.shape,
            quad_full,
            guard,
        ):
            raise InstrumentError(
                f"{group_name}: fixed lattice is not guarded inside the detected quad",
                status="IMAGE_RANGE_UNDETERMINED",
            )
    curves: list[list[float | None]] = [[] for _ in range(64)]
    site_reasons: list[list[str]] = [[] for _ in range(64)]
    registrations = []
    reference_quad_small = quad_small
    for index, frame in enumerate(frames):
        if index == reference_index:
            green = reference_green
            registration_small = reference_registration
            focus_image = reference_focus
            affine_small = np.asarray([[1, 0, 0], [0, 1, 0]], dtype=np.float64)
            registration_report = {
                "ecc_correlation": 1.0,
                "phase_seed_shift_xy_downsampled": [0.0, 0.0],
                "phase_seed_response": 1.0,
                "affine_reference_to_input_downsampled": affine_small.tolist(),
            }
        else:
            green, _ = decode_green_checked(frame, decode_rows, config)
            registration_small, focus_image, _ = spectral_views(green.green, config)
            affine_small, registration_report = register_affine(
                reference_registration,
                registration_small,
                reference_quad_small,
                config,
            )
        affine_full = affine_to_full_green(affine_small, downsample)
        centres = apply_affine(reference_centres, affine_full)
        moving_quad = apply_affine(quad_full, affine_full)
        registrations.append(
            {
                "ordered_index": index,
                "relative_path": frame["relative_path"],
                **registration_report,
                "affine_reference_to_input_full_green": np.round(
                    affine_full, 8
                ).tolist(),
            }
        )
        for site, centre in enumerate(centres):
            if not patch_is_guarded(
                centre,
                patch_size,
                focus_image.shape,
                moving_quad,
                guard,
            ):
                curves[site].append(None)
                site_reasons[site].append("PATCH_OUTSIDE_GUARDED_QUAD")
                continue
            focus_patch = extract_patch(focus_image, centre, patch_size)
            clip_patch = extract_patch(
                green.clip_mask.astype(np.float32), centre, patch_size
            )
            clip_allowed, _ = clip_fraction_allowed(clip_patch, config)
            if not clip_allowed:
                curves[site].append(None)
                site_reasons[site].append("CLIPPING")
                continue
            try:
                score = focus_band_power(focus_patch, config)
            except InstrumentError as error:
                curves[site].append(None)
                site_reasons[site].append(error.status)
                continue
            curves[site].append(score)
            site_reasons[site].append("OK")
    peaks = []
    site_rows = []
    for site, curve in enumerate(curves):
        if any(value is None for value in curve):
            peak = PeakEstimate(False, "INCOMPLETE_CURVE", None, None, None, None)
        else:
            peak = estimate_peak([float(value) for value in curve], config)
        peaks.append(peak)
        site_rows.append(
            {
                "site_index": site,
                "normalized_xy": lattice[site].tolist(),
                "reference_green_xy": reference_centres[site].tolist(),
                "curve": curve,
                "frame_statuses": site_reasons[site],
                "peak": asdict(peak),
            }
        )
    return {
        "group": group_name,
        "frame_count": len(frames),
        "reference_index": reference_index,
        "reference_relative_path": reference_frame["relative_path"],
        "spectral_contract": spectral_report,
        "quadrilateral": {
            **quad_report,
            "points_full_green_xy": quad_full.tolist(),
        },
        "registrations": registrations,
        "sites": site_rows,
        "_peaks": peaks,
    }


def range_payload(
    inventory_path: Path,
    decode_path: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    inventory = load_json_object(inventory_path)
    decode = load_json_object(decode_path)
    validate_artifact(inventory)
    validate_artifact(decode)
    validate_inventory_semantics(inventory, config)
    validate_decode_semantics(decode, inventory)
    if inventory["status"] != "INVENTORY_MATCH":
        raise InstrumentError("range stage requires INVENTORY_MATCH")
    if decode["status"] != "DECODE_CROSSCHECK_PASS":
        raise InstrumentError("range stage requires DECODE_CROSSCHECK_PASS")
    if decode["inventory_sha256"] != sha256_file(inventory_path):
        raise InstrumentError("decode artifact is bound to a different inventory")
    decode_rows = _decode_index(decode)
    def analyze_or_refuse(group_name: str) -> tuple[dict[str, Any], list[PeakEstimate] | None]:
        try:
            result = analyze_range_stack(group_name, inventory, decode_rows, config)
        except InstrumentError as error:
            if error.status == "DATA_INTEGRITY_ERROR":
                raise
            return (
                {
                    "group": group_name,
                    "status": "IMAGE_RANGE_UNDETERMINED",
                    "reason": str(error),
                },
                None,
            )
        peaks = result.pop("_peaks")
        return result, peaks

    sw4, peaks4 = analyze_or_refuse("tilted-sw4-cpl")
    sw10, peaks10 = analyze_or_refuse("tilted-sw10-cpl")
    if peaks4 is not None and peaks10 is not None:
        adjudication = adjudicate_range_pairs(
            peaks4,
            peaks10,
            sw4["frame_count"],
            sw10["frame_count"],
            config,
        )
        status = adjudication["status"]
    else:
        adjudication = {
            "status": "IMAGE_RANGE_UNDETERMINED",
            "joint_eligible_count": 0,
            "joint_eligible_indices": [],
            "robust_fit": None,
            "equivalence_bars": {
                "minimum_joint_eligible_sites": config["range_fit"][
                    "minimum_joint_eligible_sites"
                ],
                "maximum_abs_intercept": config["range_fit"][
                    "maximum_abs_intercept"
                ],
                "maximum_abs_slope_error": config["range_fit"][
                    "maximum_abs_slope_error"
                ],
                "maximum_q95_abs_residual": config["range_fit"][
                    "maximum_q95_abs_residual"
                ],
            },
            "node_density": None,
            "reason": "one or both stack analyses returned a typed refusal",
        }
        status = "IMAGE_RANGE_UNDETERMINED"
    payload = {
        "schema": "m135-slide-range-v1",
        "label": LABEL,
        "stage": "C",
        "status": status,
        "config_sha256": config_sha256(config_path),
        "inventory_sha256": sha256_file(inventory_path),
        "decode_sha256": sha256_file(decode_path),
        "invocation": invocation_record(config_path, config),
        "frequency_contract": {
            "green_plane_native_pitch_px": 2.0,
            "conversion": "f_native=f_green_plane/2",
            "registration_stop_native_cyc_per_px": config["registration"][
                "lowpass_stop_native_cyc_per_px"
            ],
            "focus_lowpass_cap_native_cyc_per_px": config["focus"][
                "lowpass_max_native_cyc_per_px"
            ],
            "focus_band_native_cyc_per_px": [
                config["focus"]["band_min_native_cyc_per_px"],
                config["focus"]["band_max_native_cyc_per_px"],
            ],
        },
        "lattice": {
            "normalized_xy": fixed_lattice(config).tolist(),
            "rows": 8,
            "columns": 8,
            "selection": "fixed before image outcomes",
        },
        "stacks": {
            "tilted-sw4-cpl": sw4,
            "tilted-sw10-cpl": sw10,
        },
        "joint_sites": {
            "eligible_count": adjudication["joint_eligible_count"],
            "eligible_indices": adjudication["joint_eligible_indices"],
            "u4": adjudication.get("u4"),
            "u10": adjudication.get("u10"),
        },
        "robust_fit": adjudication["robust_fit"],
        "equivalence_bars": adjudication["equivalence_bars"],
        "node_density": adjudication["node_density"],
    }
    validate_artifact(payload)
    validate_range_semantics(payload, config)
    return payload


def temporal_split_indices(frame_count: int, split_count: int = 4) -> list[list[int]]:
    if frame_count < split_count:
        raise InstrumentError("too few frames for temporal splits")
    return [
        [index for index in range(frame_count) if index % split_count == split]
        for split in range(split_count)
    ]


def flat_frequency_kernels(
    size: int, config: dict[str, Any]
) -> tuple[np.ndarray, list[dict[str, float]]]:
    if size <= 0 or size % 2:
        raise InstrumentError("flat coefficient patch must be positive and even")
    y, x = np.indices((size, size), dtype=np.float64)
    window = np.hanning(size)[:, None] * np.hanning(size)[None, :]
    normalizer = math.sqrt(float(np.sum(window * window)))
    kernels = []
    labels = []
    for frequency in config["flat"]["frequencies_native_cyc_per_px"]:
        if frequency > 0.25:
            raise InstrumentError("flat coefficient exceeds native 0.25 cap")
        frequency_plane = 2.0 * float(frequency)
        for angle_deg in config["flat"]["angles_deg"]:
            angle = math.radians(float(angle_deg))
            fx = frequency_plane * math.cos(angle)
            fy = frequency_plane * math.sin(angle)
            if abs(fx) > 0.5 + 1e-12 or abs(fy) > 0.5 + 1e-12:
                raise InstrumentError("flat carrier is outside green-plane Nyquist")
            carrier = np.exp(-2j * np.pi * (fx * x + fy * y))
            kernels.append(window * carrier / normalizer)
            labels.append(
                {
                    "frequency_native_cyc_per_px": float(frequency),
                    "frequency_green_plane_cyc_per_px": frequency_plane,
                    "angle_deg": float(angle_deg),
                }
            )
    return np.asarray(kernels, dtype=np.complex128), labels


def coefficients_from_patches(
    patches: np.ndarray, kernels: np.ndarray
) -> np.ndarray:
    patches = np.asarray(patches, dtype=np.float64)
    if patches.ndim != 3 or patches.shape[1:] != kernels.shape[1:]:
        raise InstrumentError("flat patches/kernels have incompatible shapes")
    if not np.all(np.isfinite(patches)):
        raise InstrumentError("flat patches contain non-finite values")
    centred = patches - 1.0
    return np.einsum("sxy,kxy->sk", centred, kernels, optimize=True)


def flat_repeatability(
    split_coefficients: np.ndarray, config: dict[str, Any]
) -> dict[str, Any]:
    values = np.asarray(split_coefficients, dtype=np.complex128)
    if values.shape != (4, 64, 16) or not np.all(np.isfinite(values)):
        raise InstrumentError(
            f"flat repeatability requires finite (4,64,16), got {values.shape}"
        )
    pairs = [(a, b) for a in range(4) for b in range(a + 1, 4)]

    def statistic(a: np.ndarray, b: np.ndarray) -> float:
        cross = np.mean(a * np.conj(b), axis=0)
        return float(np.mean(np.maximum(np.real(cross), 0.0)))

    pair_values = [statistic(values[a], values[b]) for a, b in pairs]
    observed = float(np.median(pair_values))
    rng = np.random.default_rng(int(config["flat"]["phase_scramble_seed"]))
    null = []
    for _ in range(int(config["flat"]["phase_scramble_count"])):
        pair_null = []
        for a, b in pairs:
            phase = np.exp(
                2j
                * np.pi
                * rng.random((values.shape[1], values.shape[2]))
            )
            pair_null.append(statistic(values[a], values[b] * phase))
        null.append(float(np.median(pair_null)))
    null_array = np.asarray(null, dtype=np.float64)
    p_upper = float(
        (1 + np.count_nonzero(null_array >= observed)) / (1 + len(null_array))
    )
    threshold = float(np.quantile(null_array, 0.99, method="higher"))
    structured = bool(
        observed > threshold
        and p_upper <= float(config["flat"]["structured_alpha"])
    )
    auto_power = float(np.mean(np.abs(values) ** 2, dtype=np.float64))
    return {
        "status": "STRUCTURED_FLAT" if structured else "QUIET_DIAGNOSTIC",
        "observed_repeatable_power": observed,
        "pair_repeatable_power": pair_values,
        "phase_scramble_q99": threshold,
        "phase_scramble_p_upper": p_upper,
        "phase_scramble_count": len(null),
        "structured_alpha": config["flat"]["structured_alpha"],
        "mean_split_power": auto_power,
        "repeatable_to_total_power_ratio": (
            observed / auto_power if auto_power > 0.0 else None
        ),
    }


def _load_existing_instrument() -> Any:
    module_name = "m135_existing_instrument_for_physical_commissioning"
    spec = importlib.util.spec_from_file_location(
        module_name,
        EXISTING_INSTRUMENT,
    )
    if spec is None or spec.loader is None:
        raise InstrumentError("cannot load existing M135 instrument")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def existing_core_no_detail_probe(
    split_coefficients: np.ndarray,
    *,
    lawful: bool,
    reason: str | None,
) -> dict[str, Any]:
    if not lawful:
        return {
            "invoked": False,
            "status": "NOT_EVALUATED_REFERENCE_ROLE_ABSENT",
            "reason": reason or "flat core roles are not lawful",
            "existing_instrument_path": str(EXISTING_INSTRUMENT),
            "existing_instrument_sha256": sha256_file(EXISTING_INSTRUMENT),
            "existing_instrument_normalized_sha256": normalized_text_sha256(
                EXISTING_INSTRUMENT
            ),
        }
    module = _load_existing_instrument()
    values = np.asarray(split_coefficients, dtype=np.complex128)
    captures = module.CaptureSet(
        reference_a=values[0],
        reference_b=values[1],
        output_a=values[2],
        output_b=values[3],
        clip_fraction=0.0,
        effective_bits=16,
        calibration_correlation=0.0,
        target_lineage="nonperiodic-random",
    )
    result = module.evaluate(captures, captures)
    return {
        "invoked": True,
        "status": result.get("status"),
        "result": result,
        "existing_instrument_path": str(EXISTING_INSTRUMENT),
        "existing_instrument_sha256": sha256_file(EXISTING_INSTRUMENT),
        "existing_instrument_normalized_sha256": normalized_text_sha256(
            EXISTING_INSTRUMENT
        ),
    }


def flat_core_role_contract(
    ledger: dict[str, Any], role_status: str
) -> tuple[bool, str | None]:
    row = ledger.get("flat_core_eligibility")
    if not isinstance(row, dict) or row.get("lawful") is not True:
        reason = (
            row.get("reason")
            if isinstance(row, dict)
            else "flat_core_eligibility is absent"
        )
        return False, str(reason)
    if role_status != "IDENTIFIABLE":
        return False, "full physical role gate is not IDENTIFIABLE"
    required_lists = (
        "capture_unit_ids",
        "parent_stack_ids",
        "calibration_lineage_ids",
    )
    for field in required_lists:
        values = row.get(field)
        if (
            not isinstance(values, list)
            or len(values) != 4
            or any(not isinstance(value, str) or not value for value in values)
            or len(set(values)) != 4
        ):
            return False, f"flat core {field} must contain four distinct strings"
    if row.get("target_kind") != "nonperiodic-random":
        return False, "flat core target is not nonperiodic-random"
    if row.get("featureless_source") is not True:
        return False, "flat core source is not registered featureless"
    return True, None


def _assignment_record(assignments: dict[str, Any], role: str) -> dict[str, Any]:
    row = assignments.get(role)
    if not isinstance(row, dict):
        raise InstrumentError(f"role {role} is not an object")
    return row


def role_gate_result(
    ledger: dict[str, Any],
    inventory: dict[str, Any],
    config: dict[str, Any],
    *,
    ledger_path: Path | None = None,
    score_callback: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    if ledger.get("schema") != "m135-slide-role-ledger-v1":
        raise InstrumentError("unsupported role-ledger schema")
    if ledger.get("label") != LABEL:
        raise InstrumentError("role-ledger development label changed")
    assignments = ledger.get("assignments")
    if not isinstance(assignments, dict):
        raise InstrumentError("role-ledger assignments must be an object")
    required = list(config["roles"]["required_roles"])
    missing = [role for role in required if role not in assignments]
    predicates: dict[str, bool | None] = {
        "all_required_roles_present": not missing,
        "sw4_never_truth": None,
        "independent_capture_units": None,
        "independent_parent_stacks": None,
        "source_files_bound_to_inventory": None,
        "disjoint_source_files": None,
        "odd_even_not_independent": None,
        "same_geometry_for_repeats": None,
        "disjoint_calibration_lineages": None,
        "reference_sampling_ratio": None,
        "minimum_sites": None,
        "matched_flat_evidence": None,
        "matched_flat_manifest": None,
        "nonperiodic_target": None,
        "checker_template_forbidden": None,
        "source_oracle_forbidden": None,
    }
    violations: list[str] = []
    if missing:
        return {
            "status": "REFERENCE_ROLE_ABSENT",
            "missing_roles": missing,
            "predicates": predicates,
            "violations": [],
            "j_tr_computed": False,
            "j_tr": None,
            "score_callback_called": False,
        }

    rows = {role: _assignment_record(assignments, role) for role in required}
    known_groups = set(inventory["stacks"])
    group_capture_units = {
        group: {
            unit["capture_unit_id"]: set(unit["source_file_ids"])
            for unit in inventory["stacks"][group].get("capture_units", [])
            if isinstance(unit, dict)
            and isinstance(unit.get("capture_unit_id"), str)
            and isinstance(unit.get("source_file_ids"), list)
        }
        for group in known_groups
    }
    source_membership_ok = True
    for role, row in rows.items():
        source_group = row.get("source_group")
        if source_group not in known_groups:
            violations.append(f"{role}: source_group is absent from inventory")
            source_membership_ok = False
        if not isinstance(row.get("capture_unit_id"), str) or not row["capture_unit_id"]:
            violations.append(f"{role}: missing capture_unit_id")
        if not isinstance(row.get("parent_stack_id"), str) or not row["parent_stack_id"]:
            violations.append(f"{role}: missing parent_stack_id")
        elif row.get("parent_stack_id") != row.get("capture_unit_id"):
            violations.append(
                f"{role}: parent_stack_id must equal the inventoried capture_unit_id"
            )
        if not isinstance(row.get("geometry_id"), str) or not row["geometry_id"]:
            violations.append(f"{role}: missing geometry_id")
        for lineage in ("flat_lineage_id", "dark_lineage_id"):
            if not isinstance(row.get(lineage), str) or not row[lineage]:
                violations.append(f"{role}: missing {lineage}")
        source_file_ids = row.get("source_file_ids")
        if (
            not isinstance(source_file_ids, list)
            or not source_file_ids
            or any(
                not isinstance(value, str) or not value
                for value in source_file_ids
            )
        ):
            violations.append(f"{role}: source_file_ids must be a non-empty string list")
            source_membership_ok = False
        else:
            identifiers = set(source_file_ids)
            if len(identifiers) != len(source_file_ids):
                violations.append(f"{role}: source_file_ids contain duplicates")
                source_membership_ok = False
            elif any(HEX64.fullmatch(value) is None for value in identifiers):
                violations.append(f"{role}: source_file_ids must be RAW SHA-256 values")
                source_membership_ok = False
            elif (
                source_group in group_capture_units
                and row.get("capture_unit_id") not in group_capture_units[source_group]
            ):
                violations.append(
                    f"{role}: capture_unit_id is not inventoried under {source_group}"
                )
                source_membership_ok = False
            elif (
                source_group in group_capture_units
                and identifiers
                != group_capture_units[source_group][row["capture_unit_id"]]
            ):
                violations.append(
                    f"{role}: source_file_ids do not exactly consume "
                    f"{row['capture_unit_id']}"
                )
                source_membership_ok = False
    predicates["source_files_bound_to_inventory"] = source_membership_ok

    reference_roles = ("R1", "R2")
    forbidden_reference_groups = set(
        config["roles"]["forbidden_reference_source_groups"]
    )
    predicates["sw4_never_truth"] = all(
        rows[role].get("source_group") not in forbidden_reference_groups
        and rows[role].get("acquisition_kind") == "fixed-focus-reference"
        for role in reference_roles
    )
    if not predicates["sw4_never_truth"]:
        violations.append("sw4/sw10/all-axis focus ladders cannot be truth roles")

    capture_units = [rows[role].get("capture_unit_id") for role in required]
    predicates["independent_capture_units"] = len(set(capture_units)) == len(
        capture_units
    )
    if not predicates["independent_capture_units"]:
        violations.append("required roles reuse a capture_unit_id")

    all_parent_ids = [rows[role].get("parent_stack_id") for role in required]
    predicates["independent_parent_stacks"] = len(set(all_parent_ids)) == len(
        all_parent_ids
    )
    if not predicates["independent_parent_stacks"]:
        violations.append("required roles reuse a parent_stack_id")

    source_sets = [
        set(rows[role].get("source_file_ids", [])) for role in required
    ]
    predicates["disjoint_source_files"] = all(
        source_sets[left].isdisjoint(source_sets[right])
        for left in range(len(source_sets))
        for right in range(left + 1, len(source_sets))
    )
    if not predicates["disjoint_source_files"]:
        violations.append("required roles reuse source files")

    independent_primary = ("R1", "R2", "sw4_Y1", "sw4_Y2", "sw10_Y1", "sw10_Y2")
    parent_ids = [rows[role].get("parent_stack_id") for role in independent_primary]
    subset_labels = {
        str(rows[role].get("subset", "all")).casefold()
        for role in independent_primary
    }
    predicates["odd_even_not_independent"] = bool(
        len(set(parent_ids)) == len(parent_ids)
        and not (
            subset_labels
            & set(config["roles"]["forbidden_subset_independence_labels"])
        )
    )
    if not predicates["odd_even_not_independent"]:
        violations.append("odd/even/interleaved subsets are not independent captures")

    primary_geometry = {rows[role].get("geometry_id") for role in independent_primary}
    all_axis_group = "very-tilted-all-axis-sw10-cpl"
    predicates["same_geometry_for_repeats"] = bool(
        len(primary_geometry) == 1
        and all(
            rows[role].get("source_group") != all_axis_group
            for role in independent_primary
        )
    )
    if not predicates["same_geometry_for_repeats"]:
        violations.append("all-axis/different-geometry capture was used as a repeat")

    flat_lineages = [rows[role].get("flat_lineage_id") for role in required]
    dark_lineages = [rows[role].get("dark_lineage_id") for role in required]
    predicates["disjoint_calibration_lineages"] = bool(
        len(set(flat_lineages)) == len(flat_lineages)
        and len(set(dark_lineages)) == len(dark_lineages)
    )
    if not predicates["disjoint_calibration_lineages"]:
        violations.append("required output/reference roles share calibration lineages")

    reference_sampling = [
        rows[role].get("subject_sampling_lcb95_px_per_object_unit")
        for role in reference_roles
    ]
    scored_sampling = [
        rows[role].get("subject_sampling_ucb95_px_per_object_unit")
        for role in ("sw4_Y1", "sw4_Y2", "sw10_Y1", "sw10_Y2")
    ]
    sampling_valid = all(exact_number(value) and float(value) > 0.0 for value in reference_sampling + scored_sampling)
    sampling_ratio = (
        min(float(value) for value in reference_sampling)
        / max(float(value) for value in scored_sampling)
        if sampling_valid
        else None
    )
    predicates["reference_sampling_ratio"] = bool(
        sampling_ratio is not None
        and sampling_ratio
        >= config["roles"]["minimum_reference_to_scored_sampling_ratio"]
    )
    if not predicates["reference_sampling_ratio"]:
        violations.append("reference/scored subject-sampling lower bound is below 2.0")

    site_count = ledger.get("site_count")
    predicates["minimum_sites"] = bool(
        isinstance(site_count, int)
        and not isinstance(site_count, bool)
        and site_count >= config["roles"]["minimum_sites"]
    )
    if not predicates["minimum_sites"]:
        violations.append("role ledger has fewer than 64 eligible sites")

    predicates["matched_flat_evidence"] = ledger.get("matched_flat_evidence") is True
    if not predicates["matched_flat_evidence"]:
        violations.append("matched flat evidence is absent")
    flat_manifest = ledger.get("matched_flat_manifest_sha256")
    flat_manifest_path_raw = ledger.get("matched_flat_manifest_path")
    flat_manifest_path: Path | None = None
    if isinstance(flat_manifest_path_raw, str) and flat_manifest_path_raw:
        candidate = Path(flat_manifest_path_raw)
        if not candidate.is_absolute():
            candidate = (
                (ledger_path.absolute().parent if ledger_path is not None else Path.cwd())
                / candidate
            )
        flat_manifest_path = candidate.absolute()
    manifest_file_valid = False
    manifest_content_valid = False
    if flat_manifest_path is not None:
        try:
            info = flat_manifest_path.lstat()
            manifest_file_valid = bool(
                stat.S_ISREG(info.st_mode)
                and not flat_manifest_path.is_symlink()
                and not _is_reparse(info)
            )
            if manifest_file_valid:
                evidence, evidence_hash = load_hashed_json_object(
                    flat_manifest_path
                )
                manifest_file_valid = evidence_hash == flat_manifest
                expected_lineages = {
                    rows[role][field]
                    for role in required
                    for field in ("flat_lineage_id", "dark_lineage_id")
                }
                observed_lineages = evidence.get("lineage_ids")
                expected_bindings = {
                    role: {
                        "capture_unit_id": rows[role]["capture_unit_id"],
                        "parent_stack_id": rows[role]["parent_stack_id"],
                        "source_group": rows[role]["source_group"],
                        "source_file_ids": sorted(rows[role]["source_file_ids"]),
                        "flat_lineage_id": rows[role]["flat_lineage_id"],
                        "dark_lineage_id": rows[role]["dark_lineage_id"],
                    }
                    for role in required
                }
                manifest_content_valid = bool(
                    evidence.get("schema") == "m135-matched-flat-evidence-v1"
                    and evidence.get("status") == "PASS"
                    and isinstance(observed_lineages, list)
                    and all(
                        isinstance(value, str) and value
                        for value in observed_lineages
                    )
                    and set(observed_lineages) == expected_lineages
                    and evidence.get("role_bindings") == expected_bindings
                )
        except (OSError, InstrumentError):
            manifest_file_valid = False
            manifest_content_valid = False
    predicates["matched_flat_manifest"] = bool(
        isinstance(flat_manifest, str)
        and HEX64.fullmatch(flat_manifest)
        and manifest_file_valid
        and manifest_content_valid
    )
    if not predicates["matched_flat_manifest"]:
        violations.append(
            "matched flat manifest is absent, malformed, unreadable, or hash-mismatched"
        )

    target = ledger.get("target")
    if not isinstance(target, dict):
        target = {}
    predicates["nonperiodic_target"] = (
        target.get("kind") == config["roles"]["allowed_target_kind"]
    )
    predicates["checker_template_forbidden"] = (
        target.get("checker_template_available") is False
    )
    predicates["source_oracle_forbidden"] = (
        target.get("source_oracle_used") is False
    )
    if not predicates["nonperiodic_target"]:
        violations.append("public/periodic target cannot be a truth source")
    if not predicates["checker_template_forbidden"]:
        violations.append("checker template is available to the truth path")
    if not predicates["source_oracle_forbidden"]:
        violations.append("source/template oracle was used")

    if violations:
        return {
            "status": "ROLE_LEDGER_INVALID",
            "missing_roles": [],
            "predicates": predicates,
            "violations": violations,
            "sampling_ratio": sampling_ratio,
            "j_tr_computed": False,
            "j_tr": None,
            "score_callback_called": False,
        }
    callback_called = False
    if score_callback is not None:
        score_callback()
        callback_called = True
    return {
        "status": "IDENTIFIABLE",
        "missing_roles": [],
        "predicates": predicates,
        "violations": [],
        "sampling_ratio": sampling_ratio,
        "j_tr_computed": False,
        "j_tr": None,
        "score_callback_called": callback_called,
        "note": (
            "this commissioning lane establishes identifiability only; the "
            "separately frozen M135 estimator remains the scoring implementation"
        ),
    }


def roles_payload(
    inventory_path: Path,
    ledger_path: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    inventory = load_json_object(inventory_path)
    validate_artifact(inventory)
    validate_inventory_semantics(inventory, config)
    ledger, ledger_hash = load_hashed_json_object(ledger_path)
    result = role_gate_result(
        ledger, inventory, config, ledger_path=ledger_path
    )
    payload = {
        "schema": "m135-slide-role-gate-v1",
        "label": LABEL,
        "stage": "D",
        "status": result["status"],
        "config_sha256": config_sha256(config_path),
        "inventory_sha256": sha256_file(inventory_path),
        "role_ledger_path": str(ledger_path.absolute()),
        "role_ledger_sha256": ledger_hash,
        "invocation": invocation_record(config_path, config),
        "missing_roles": result["missing_roles"],
        "predicates": result["predicates"],
        "violations": result["violations"],
        "sampling_ratio": result.get("sampling_ratio"),
        "j_tr_computed": result["j_tr_computed"],
        "j_tr": result["j_tr"],
        "score_callback_called": result["score_callback_called"],
    }
    validate_artifact(payload)
    validate_roles_semantics(payload, config)
    return payload


def _flat_group_frames_by_exposure(
    inventory: dict[str, Any], config: dict[str, Any]
) -> list[tuple[str, list[dict[str, Any]]]]:
    frames = inventory["stacks"]["flat-sw4-cpl"]["frames"]
    groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for frame in frames:
        exposure = frame.get("ExposureTime")
        if not exact_number(exposure):
            raise InstrumentError("flat frame lacks numeric ExposureTime")
        key = format(float(exposure), ".17g")
        groups[key].append(frame)
    ordered = sorted(groups.items(), key=lambda item: float(item[0]))
    if len(ordered) != config["flat"]["expected_exposure_groups"]:
        raise InstrumentError(
            f"flat exposure-group count {len(ordered)} != "
            f"{config['flat']['expected_exposure_groups']}"
        )
    return ordered


def analyze_flat_exposure_group(
    exposure: str,
    frames: list[dict[str, Any]],
    centres: np.ndarray,
    quad: np.ndarray,
    decode_rows: dict[str, dict[str, Any]],
    config: dict[str, Any],
    kernels: np.ndarray,
    labels: list[dict[str, float]],
) -> tuple[dict[str, Any], np.ndarray]:
    split_indices = temporal_split_indices(
        len(frames), int(config["flat"]["split_count"])
    )
    if min(len(indices) for indices in split_indices) < config["flat"][
        "minimum_frames_per_split"
    ]:
        raise InstrumentError(
            f"exposure {exposure}: a temporal split has too few frames"
        )
    patch_size = int(config["lattice"]["patch_size_green_px"])
    patch_sums = np.zeros((4, 64, patch_size, patch_size), dtype=np.float64)
    split_counts = np.zeros(4, dtype=np.int64)
    clipped_frames = []
    for index, frame in enumerate(frames):
        green, _ = decode_green_checked(frame, decode_rows, config)
        split = index % 4
        split_counts[split] += 1
        frame_clipped = False
        for site, centre in enumerate(centres):
            if not patch_is_guarded(
                centre,
                patch_size,
                green.green.shape,
                quad,
                config["lattice"]["minimum_quad_guard_green_px"],
            ):
                raise InstrumentError(
                    f"flat site {site} is outside the fixed sensor-coordinate quad"
                )
            patch = extract_patch(green.green, centre, patch_size)
            clip_patch = extract_patch(
                green.clip_mask.astype(np.float32), centre, patch_size
            )
            clip_allowed, _ = clip_fraction_allowed(clip_patch, config)
            if not clip_allowed:
                frame_clipped = True
                break
            mean = float(np.mean(patch, dtype=np.float64))
            if mean < config["focus"]["minimum_patch_mean_dn"]:
                raise InstrumentError(
                    f"flat patch mean {mean:.6g} is below the signal floor"
                )
            patch_sums[split, site] += patch.astype(np.float64) / mean
        if frame_clipped:
            clipped_frames.append(frame["relative_path"])
    if clipped_frames:
        raise InstrumentError(
            f"exposure {exposure}: clipping refusal in {len(clipped_frames)} frames"
        )
    split_patches = patch_sums / split_counts[:, None, None, None]
    coefficients = np.stack(
        [
            coefficients_from_patches(split_patches[split], kernels)
            for split in range(4)
        ],
        axis=0,
    )
    repeatability = flat_repeatability(coefficients, config)
    frequency_power = []
    for frequency in config["flat"]["frequencies_native_cyc_per_px"]:
        cells = [
            index
            for index, label in enumerate(labels)
            if label["frequency_native_cyc_per_px"] == frequency
        ]
        frequency_power.append(
            {
                "frequency_native_cyc_per_px": frequency,
                "mean_power": float(
                    np.mean(np.abs(coefficients[:, :, cells]) ** 2)
                ),
            }
        )
    return (
        {
            "exposure_seconds": float(exposure),
            "frame_count": len(frames),
            "ordered_relative_paths": [frame["relative_path"] for frame in frames],
            "temporal_split_rule": config["flat"]["temporal_split_rule"],
            "temporal_splits": split_indices,
            "split_frame_counts": split_counts.tolist(),
            "frequency_power": frequency_power,
            "repeatability": repeatability,
            "status": repeatability["status"],
        },
        coefficients,
    )


def flat_payload(
    inventory_path: Path,
    decode_path: Path,
    roles_path: Path,
    ledger_path: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    inventory = load_json_object(inventory_path)
    decode = load_json_object(decode_path)
    roles = load_json_object(roles_path)
    ledger, ledger_hash = load_hashed_json_object(ledger_path)
    validate_artifact(inventory)
    validate_artifact(decode)
    validate_artifact(roles)
    validate_inventory_semantics(inventory, config)
    validate_decode_semantics(decode, inventory)
    validate_roles_semantics(roles, config)
    if inventory["status"] != "INVENTORY_MATCH":
        raise InstrumentError("flat stage requires INVENTORY_MATCH")
    if decode["status"] != "DECODE_CROSSCHECK_PASS":
        raise InstrumentError("flat stage requires DECODE_CROSSCHECK_PASS")
    if roles["inventory_sha256"] != sha256_file(inventory_path):
        raise InstrumentError("role gate is bound to a different inventory")
    if roles["role_ledger_sha256"] != ledger_hash:
        raise InstrumentError("flat ledger differs from the Stage D ledger")
    decode_rows = _decode_index(decode)
    lattice = fixed_lattice(config)
    kernels, labels = flat_frequency_kernels(
        int(config["lattice"]["patch_size_green_px"]), config
    )
    exposure_rows = []
    coefficient_sets = []
    sensor_lattice: dict[str, Any] = {
        "reference_relative_path": None,
        "normalized_xy": lattice.tolist(),
        "green_xy": None,
        "quadrilateral_full_green_xy": None,
        "quadrilateral_selector": None,
        "spectral_input": None,
        "per_frame_registration": False,
        "definition": (
            "one fixed sensor-coordinate lattice is reused at all three "
            "exposures and in all four temporal splits"
        ),
    }
    try:
        grouped = _flat_group_frames_by_exposure(inventory, config)
        all_flat_frames = inventory["stacks"]["flat-sw4-cpl"]["frames"]
        if not all_flat_frames:
            raise InstrumentError("flat stack contains no frames")
        reference_frame = all_flat_frames[0]
        reference_green, _ = decode_green_checked(
            reference_frame, decode_rows, config
        )
        registration_small, _, spectral_report = spectral_views(
            reference_green.green, config
        )
        quad_small, quad_report = detect_quadrilateral(
            registration_small, config
        )
        downsample = int(config["registration"]["downsample_green_plane"])
        quad_full = _scaled_quad(quad_small, downsample)
        centres = map_lattice_to_quad(lattice, quad_full)
        sensor_lattice.update(
            {
                "reference_relative_path": reference_frame["relative_path"],
                "green_xy": centres.tolist(),
                "quadrilateral_full_green_xy": quad_full.tolist(),
                "quadrilateral_selector": quad_report,
                "spectral_input": spectral_report,
            }
        )
        for exposure, frames in grouped:
            row, coefficients = analyze_flat_exposure_group(
                exposure,
                frames,
                centres,
                quad_full,
                decode_rows,
                config,
                kernels,
                labels,
            )
            exposure_rows.append(row)
            coefficient_sets.append(coefficients)
        if all(row["status"] == "QUIET_DIAGNOSTIC" for row in exposure_rows):
            status = "QUIET_DIAGNOSTIC"
        else:
            status = "STRUCTURED_FLAT"
    except InstrumentError as error:
        if error.status == "DATA_INTEGRITY_ERROR":
            raise
        status = "FLAT_DIAGNOSTIC_UNDETERMINED"
        exposure_rows.append(
            {
                "status": "FLAT_DIAGNOSTIC_UNDETERMINED",
                "reason": str(error),
            }
        )

    core_probe = existing_core_no_detail_probe(
        np.zeros((4, 64, 16), dtype=np.complex128),
        lawful=False,
        reason=(
            "the four temporal splits come from one flat-sw4 focus ladder; "
            "odd/even/modulo subsets are not independent capture or calibration roles"
        ),
    )
    certificate_sufficient = False
    payload = {
        "schema": "m135-slide-flat-v1",
        "label": LABEL,
        "stage": "E",
        "status": status,
        "config_sha256": config_sha256(config_path),
        "inventory_sha256": sha256_file(inventory_path),
        "decode_sha256": sha256_file(decode_path),
        "role_gate_sha256": sha256_file(roles_path),
        "role_ledger_sha256": ledger_hash,
        "invocation": invocation_record(config_path, config),
        "frequency_contract": {
            "green_plane_native_pitch_px": 2.0,
            "conversion": "f_native=f_green_plane/2",
            "cells": labels,
            "maximum_frequency_native_cyc_per_px": max(
                config["flat"]["frequencies_native_cyc_per_px"]
            ),
        },
        "sensor_coordinate_lattice": sensor_lattice,
        "exposure_groups": exposure_rows,
        "core_probe": core_probe,
        "certificate_sufficient": certificate_sufficient,
        "insufficiency_reason": (
            None
            if certificate_sufficient
            else "quiet diagnostics are necessary but calibration/reference roles are absent"
        ),
    }
    validate_artifact(payload)
    validate_flat_semantics(payload, config)
    return payload


def range_measurement_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "frequency_contract": payload.get("frequency_contract"),
        "lattice": payload.get("lattice"),
        "stacks": payload.get("stacks"),
        "joint_sites": payload.get("joint_sites"),
        "robust_fit": payload.get("robust_fit"),
        "equivalence_bars": payload.get("equivalence_bars"),
        "node_density": payload.get("node_density"),
    }


def decode_measurement_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "decoder_contract": payload.get("decoder_contract"),
        "frames": payload.get("frames"),
        "proceed_to_range": payload.get("proceed_to_range"),
    }


def flat_measurement_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "frequency_contract": payload.get("frequency_contract"),
        "sensor_coordinate_lattice": payload.get("sensor_coordinate_lattice"),
        "exposure_groups": payload.get("exposure_groups"),
        "core_probe": payload.get("core_probe"),
        "certificate_sufficient": payload.get("certificate_sufficient"),
        "insufficiency_reason": payload.get("insufficiency_reason"),
    }


def inventory_measurement_projection(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": payload.get("status"),
        "source_root": payload.get("source_root"),
        "source_snapshot": payload.get("source_snapshot"),
        "exiftool": payload.get("exiftool"),
        "stacks": payload.get("stacks"),
        "unexpected_arw": payload.get("unexpected_arw"),
        "coarse_encoder": payload.get("coarse_encoder"),
        "proceed_to_decode": payload.get("proceed_to_decode"),
    }


def summary_payload(
    inventory_path: Path,
    decode_path: Path,
    range_path: Path,
    roles_path: Path,
    flat_path: Path,
    config_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    inventory = load_json_object(inventory_path)
    decode = load_json_object(decode_path)
    image_range = load_json_object(range_path)
    roles = load_json_object(roles_path)
    flat = load_json_object(flat_path)
    for payload in (inventory, decode, image_range, roles, flat):
        validate_artifact(payload)
        if payload["config_sha256"] != config_sha256(config_path):
            raise InstrumentError(
                f"{payload['schema']} is bound to a different config"
            )
    validate_inventory_semantics(inventory, config)
    validate_decode_semantics(decode, inventory)
    validate_range_semantics(image_range, config)
    validate_roles_semantics(roles, config)
    validate_flat_semantics(flat, config)
    role_ledger_path_raw = roles.get("role_ledger_path")
    if not isinstance(role_ledger_path_raw, str) or not role_ledger_path_raw:
        raise InstrumentError("role artifact lacks role_ledger_path")
    role_ledger_path = Path(role_ledger_path_raw).absolute()
    try:
        ledger_info = role_ledger_path.lstat()
        role_ledger, role_ledger_hash = load_hashed_json_object(
            role_ledger_path
        )
    except (OSError, InstrumentError) as error:
        raise InstrumentError(
            f"role ledger path cannot be read atomically: {error}"
        ) from error
    if not (
        stat.S_ISREG(ledger_info.st_mode)
        and not role_ledger_path.is_symlink()
        and not _is_reparse(ledger_info)
        and role_ledger_hash == roles.get("role_ledger_sha256")
    ):
        raise InstrumentError("role ledger path/hash no longer matches Stage D")
    recomputed_roles = role_gate_result(
        role_ledger,
        inventory,
        config,
        ledger_path=role_ledger_path,
    )
    role_fields = (
        "status",
        "missing_roles",
        "predicates",
        "violations",
        "sampling_ratio",
        "j_tr_computed",
        "j_tr",
        "score_callback_called",
    )
    if any(roles.get(field) != recomputed_roles.get(field) for field in role_fields):
        raise InstrumentError("Stage D role evidence does not recompute from its ledger")
    inventory_hash = sha256_file(inventory_path)
    decode_hash = sha256_file(decode_path)
    range_hash = sha256_file(range_path)
    roles_hash = sha256_file(roles_path)
    flat_hash = sha256_file(flat_path)
    link_checks = {
        "decode_to_inventory": decode.get("inventory_sha256")
        == inventory_hash,
        "range_to_inventory": image_range.get("inventory_sha256")
        == inventory_hash,
        "range_to_decode": image_range.get("decode_sha256") == decode_hash,
        "roles_to_inventory": roles.get("inventory_sha256")
        == inventory_hash,
        "flat_to_inventory": flat.get("inventory_sha256") == inventory_hash,
        "flat_to_decode": flat.get("decode_sha256") == decode_hash,
        "flat_to_roles": flat.get("role_gate_sha256") == roles_hash,
        "flat_to_role_ledger": flat.get("role_ledger_sha256")
        == roles.get("role_ledger_sha256"),
    }
    if not all(link_checks.values()):
        raise InstrumentError(
            "artifact chain mismatch: "
            + json.dumps(link_checks, sort_keys=True)
        )
    exiftool_record_value = inventory.get("exiftool")
    if not isinstance(exiftool_record_value, dict) or not isinstance(
        exiftool_record_value.get("path"), str
    ):
        raise InstrumentError("inventory lacks the frozen ExifTool path")
    recomputed_inventory = inventory_payload(
        Path(inventory["source_root"]),
        Path(exiftool_record_value["path"]),
        config_path,
        config,
    )
    if canonical_json_sha256(
        inventory_measurement_projection(recomputed_inventory)
    ) != canonical_json_sha256(inventory_measurement_projection(inventory)):
        raise InstrumentError(
            "Stage A metadata/order does not reproduce from the bound RAW files"
        )
    decoder_contract = decode.get("decoder_contract")
    if not isinstance(decoder_contract, dict) or not isinstance(
        decoder_contract.get("binary_path"), str
    ):
        raise InstrumentError("decode artifact lacks the frozen rawler binary path")
    recomputed_decode, decode_exit = decode_payload(
        inventory_path,
        Path(decoder_contract["binary_path"]),
        config_path,
        config,
    )
    if decode_exit != 0 or canonical_json_sha256(
        decode_measurement_projection(recomputed_decode)
    ) != canonical_json_sha256(decode_measurement_projection(decode)):
        raise InstrumentError(
            "Stage B decode/checksum does not reproduce from the bound RAW files"
        )
    recomputed_range = range_payload(
        inventory_path,
        decode_path,
        config_path,
        config,
    )
    if canonical_json_sha256(
        range_measurement_projection(recomputed_range)
    ) != canonical_json_sha256(range_measurement_projection(image_range)):
        raise InstrumentError(
            "Stage C measurement does not reproduce from the bound RAW/decode inputs"
        )
    recomputed_flat = flat_payload(
        inventory_path,
        decode_path,
        roles_path,
        role_ledger_path,
        config_path,
        config,
    )
    if canonical_json_sha256(
        flat_measurement_projection(recomputed_flat)
    ) != canonical_json_sha256(flat_measurement_projection(flat)):
        raise InstrumentError(
            "Stage E flat diagnostic does not reproduce from the bound inputs"
        )
    real_optical = bool(
        inventory["status"] == "INVENTORY_MATCH"
        and decode["status"] == "DECODE_CROSSCHECK_PASS"
        and inventory["coarse_encoder"]["status"]
        == "COARSE_ENCODER_RANGE_EQUAL"
        and image_range["status"] == "IMAGE_RANGE_EQUIVALENT"
    )
    physical_bound = bool(
        real_optical
        and roles["status"] == "IDENTIFIABLE"
        and flat["certificate_sufficient"]
    )
    payload = {
        "schema": "m135-slide-summary-v1",
        "label": LABEL,
        "stage": "summary",
        "status": (
            "DEVELOPMENT_COMPLETE"
            if all(
                item["status"]
                in {
                    "INVENTORY_MATCH",
                    "DECODE_CROSSCHECK_PASS",
                    "IMAGE_RANGE_EQUIVALENT",
                    "IMAGE_RANGE_NOT_EQUIVALENT",
                    "IMAGE_RANGE_UNDETERMINED",
                    "REFERENCE_ROLE_ABSENT",
                    "ROLE_LEDGER_INVALID",
                    "IDENTIFIABLE",
                    "QUIET_DIAGNOSTIC",
                    "STRUCTURED_FLAT",
                    "FLAT_DIAGNOSTIC_UNDETERMINED",
                }
                for item in (inventory, decode, image_range, roles, flat)
            )
            else "DEVELOPMENT_BLOCKED"
        ),
        "config_sha256": config_sha256(config_path),
        "invocation": invocation_record(config_path, config),
        "inventory": inventory["status"],
        "coarse_encoder": inventory["coarse_encoder"]["status"],
        "image_range": image_range["status"],
        "identifiability": roles["status"],
        "real_optical_intervention": (
            "REAL_OPTICAL_ARM_PRESENT"
            if real_optical
            else "REAL_OPTICAL_ARM_NOT_ESTABLISHED"
        ),
        "flat_diagnostic": flat["status"],
        "physical_binding": (
            "PHYSICAL_BOUND" if physical_bound else "UNBOUND"
        ),
        "quiet_flat_is_necessary_not_sufficient": True,
        "j_tr_computed": False,
        "j_tr": None,
        "artifact_hashes": {
            "inventory_sha256": inventory_hash,
            "decode_sha256": decode_hash,
            "range_sha256": range_hash,
            "roles_sha256": roles_hash,
            "flat_sha256": flat_hash,
        },
        "artifact_link_checks": link_checks,
        "inventory_recomputed_from_bound_inputs": True,
        "decode_recomputed_from_bound_inputs": True,
        "range_recomputed_from_bound_inputs": True,
        "flat_recomputed_from_bound_inputs": True,
    }
    if roles["status"] == "REFERENCE_ROLE_ABSENT":
        payload["physical_binding"] = "UNBOUND"
        payload["j_tr_computed"] = False
        payload["j_tr"] = None
    validate_artifact(payload)
    return payload


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="M135 burned-slide physical commissioning instrument"
    )
    root.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = root.add_subparsers(dest="command", required=True)

    inventory = commands.add_parser("inventory")
    inventory.add_argument("--session-root", type=Path, required=True)
    inventory.add_argument("--exiftool", type=Path, required=True)
    inventory.add_argument("--output", type=Path, required=True)

    decode = commands.add_parser("decode")
    decode.add_argument("--inventory", type=Path, required=True)
    decode.add_argument("--rawler-crosscheck-bin", type=Path, required=True)
    decode.add_argument("--output", type=Path, required=True)

    range_command = commands.add_parser("range")
    range_command.add_argument("--inventory", type=Path, required=True)
    range_command.add_argument("--decode", type=Path, required=True)
    range_command.add_argument("--output", type=Path, required=True)

    roles = commands.add_parser("roles")
    roles.add_argument("--inventory", type=Path, required=True)
    roles.add_argument("--ledger", type=Path, required=True)
    roles.add_argument("--output", type=Path, required=True)

    flat = commands.add_parser("flat")
    flat.add_argument("--inventory", type=Path, required=True)
    flat.add_argument("--decode", type=Path, required=True)
    flat.add_argument("--roles", type=Path, required=True)
    flat.add_argument("--ledger", type=Path, required=True)
    flat.add_argument("--output", type=Path, required=True)

    summary = commands.add_parser("summarize")
    summary.add_argument("--inventory", type=Path, required=True)
    summary.add_argument("--decode", type=Path, required=True)
    summary.add_argument("--range", dest="range_path", type=Path, required=True)
    summary.add_argument("--roles", type=Path, required=True)
    summary.add_argument("--flat", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    return root


def _error_payload(
    error: Exception, config_path: Path, config: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "schema": "m135-slide-error-v1",
        "label": LABEL,
        "status": getattr(error, "status", "INSTRUMENT_ERROR"),
        "error_type": type(error).__name__,
        "error": str(error),
        "config_path": str(config_path.absolute()),
        "config_sha256": (
            config_sha256(config_path) if config_path.is_file() else None
        ),
        "argv": [str(Path(sys.executable).absolute()), *sys.argv],
        "environment": (
            {
                key: os.environ.get(key)
                for key in (
                    list(config["environment"]["required"])
                    + list(config["environment"]["record_even_when_unset"])
                )
            }
            if config is not None
            else None
        ),
    }


def main() -> int:
    args = parser().parse_args()
    config: dict[str, Any] | None = None
    output = getattr(args, "output", None)
    try:
        config = load_config(args.config)
        require_environment(config)
        if args.command == "inventory":
            payload = inventory_payload(
                args.session_root.absolute(),
                args.exiftool.absolute(),
                args.config.absolute(),
                config,
            )
            exit_code = 0
        elif args.command == "decode":
            payload, exit_code = decode_payload(
                args.inventory.absolute(),
                args.rawler_crosscheck_bin.absolute(),
                args.config.absolute(),
                config,
            )
        elif args.command == "range":
            payload = range_payload(
                args.inventory.absolute(),
                args.decode.absolute(),
                args.config.absolute(),
                config,
            )
            exit_code = 0
        elif args.command == "roles":
            payload = roles_payload(
                args.inventory.absolute(),
                args.ledger.absolute(),
                args.config.absolute(),
                config,
            )
            exit_code = 0
        elif args.command == "flat":
            payload = flat_payload(
                args.inventory.absolute(),
                args.decode.absolute(),
                args.roles.absolute(),
                args.ledger.absolute(),
                args.config.absolute(),
                config,
            )
            exit_code = 0
        elif args.command == "summarize":
            payload = summary_payload(
                args.inventory.absolute(),
                args.decode.absolute(),
                args.range_path.absolute(),
                args.roles.absolute(),
                args.flat.absolute(),
                args.config.absolute(),
                config,
            )
            exit_code = 0
        else:
            raise AssertionError(args.command)
        write_json(output, payload)
        print(
            json.dumps(
                {
                    "schema": payload["schema"],
                    "status": payload["status"],
                    "output": str(output.absolute()),
                },
                sort_keys=True,
            )
        )
        return exit_code
    except Exception as error:
        payload = _error_payload(error, args.config, config)
        if output is not None:
            write_json(output, payload)
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
