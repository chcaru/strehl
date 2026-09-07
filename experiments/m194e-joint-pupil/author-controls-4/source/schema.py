"""Closed local evidence schemas; trusted commission authority is external."""
from dataclasses import asdict
import json
from pathlib import Path, PurePosixPath
import re

import numpy as np

from model import RAY_MODEL, file_ref, primary_frames, primary_scene, scene_record, sensor_record, sha256, strict_json_loads
from render import integrator_for

HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parents[1]
AUTHOR_SOURCES = ("model.py", "render.py", "schema.py", "commission.py", "emit-cfa.py", "author-controls.py")
DESIGNS = ("implementation-plan.md", "implementation-preregister.md", "independent-design.md", "numerical-amendment-1.md")
ARMS = ("primary", "angle-refined", "cell-refined")


def exact_keys(value, keys, name):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"{name}: exact keys required {sorted(keys)}")


def same_shape_value(value, expected, name):
    """Exact fixed scalar values, with JSON numbers allowing int/float, never bool."""
    if isinstance(expected, dict):
        exact_keys(value, expected, name)
        for k in expected:
            same_shape_value(value[k], expected[k], f"{name}.{k}")
    elif isinstance(expected, (list, tuple)):
        if not isinstance(value, list) or len(value) != len(expected):
            raise ValueError(f"{name}: fixed array required")
        for i, (v, e) in enumerate(zip(value, expected)):
            same_shape_value(v, e, f"{name}[{i}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if type(value) is not type(expected) or value != expected:
            raise ValueError(f"{name}: fixed value differs")
    elif type(expected) is int:
        if type(value) is not int or value != expected:
            raise ValueError(f"{name}: fixed integer differs")
    elif isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or value != expected:
        raise ValueError(f"{name}: fixed finite number differs")


def integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name}: nonnegative integer required")


def digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("lowercase SHA256 required")


def relative_path(value, root):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("relative POSIX path required")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in (".", "..", "") for part in value.split("/")):
        raise ValueError("absolute/traversing path refused")
    root = Path(root).resolve()
    result = (root / value).resolve()
    if not result.is_relative_to(root):
        raise ValueError("resolved path leaves bound root")
    return result


def validate_ref(ref, root, array=False):
    exact_keys(ref, ("path", "sha256", "bytes", "dtype", "shape") if array else ("path", "sha256", "bytes"), "file ref")
    digest(ref["sha256"])
    integer(ref["bytes"], "bytes")
    path = relative_path(ref["path"], root)
    if not path.is_file() or path.stat().st_size != ref["bytes"] or sha256(path) != ref["sha256"]:
        raise ValueError("file length/hash binding failed")
    if array:
        if ref["dtype"] not in ("<f8", "<u2"):
            raise ValueError("unsupported array dtype")
        if not isinstance(ref["shape"], list) or len(ref["shape"]) != 2:
            raise ValueError("fixed array shape required")
        for dimension in ref["shape"]:
            integer(dimension, "dimension")
        if ref["shape"] != [48, 64]:
            raise ValueError("fixed48x64 shape required")
    return path


def read_scalar(ref, root):
    path = validate_ref(ref, root, True)
    if ref["dtype"] != "<f8" or path.suffix != ".npy" or ref["bytes"] > 48 * 64 * 8 + 4096:
        raise ValueError("scalar must be bounded float64 NPY")
    # Mmap validates shape before any materialized copy. Object arrays refuse.
    value = np.load(path, mmap_mode="r", allow_pickle=False)
    if value.dtype.str != "<f8" or value.shape != (48, 64) or not value.flags.c_contiguous or not np.isfinite(value).all() or np.any(value < 0):
        raise ValueError("finite nonnegative row-major48x64 scalar required")
    if value.offset + value.nbytes != ref["bytes"]:
        raise ValueError("NPY payload must consume the complete file")
    return value


def source_bindings():
    result = {}
    for name in AUTHOR_SOURCES:
        p = HERE / name
        result[p.relative_to(REPOSITORY).as_posix()] = dict(sha256=sha256(p), bytes=p.stat().st_size)
    return result


def design_bindings():
    return {name: dict(sha256=sha256(HERE / name), bytes=(HERE / name).stat().st_size) for name in DESIGNS}


def numerical_contract():
    return dict(method="polar-radial-ladder32-clipped-cell-v2", radial_crossing_levels=32,
                arms={arm: asdict(integrator_for(arm)) for arm in ARMS},
                max_discrepancy_e=.004, rms_discrepancy_e=.0008, edge_distance_native=8,
                author_refinement_max_e=.001, independent_refinement_max_e=.0005,
                arrays="all-five-complete-float64-frames", indicators="weighted-low-and-high-pupil-plus-cell-delta")


def json_read(path):
    return strict_json_loads(Path(path).read_text(encoding="utf-8"))


def validate_sources(sources):
    same_shape_value(sources, source_bindings(), "source bindings")
    for name, ref in sources.items():
        exact_keys(ref, ("sha256", "bytes"), "source ref")
        digest(ref["sha256"])
        integer(ref["bytes"], "source bytes")
        path = relative_path(name, REPOSITORY)
        if path.stat().st_size != ref["bytes"] or sha256(path) != ref["sha256"]:
            raise ValueError("actual producer source changed")


def validate_frames(frames, root, arm):
    if not isinstance(frames, list) or len(frames) != 5:
        raise ValueError("exactly five ordered frames required")
    for i, (record, expected) in enumerate(zip(frames, primary_frames())):
        exact_keys(record, ("index", "inverse_focus", "K", "forward_similarity", "expected_scalar", "numerical_receipt"), "frame")
        integer(record["index"], "frame index")
        same_shape_value({k: record[k] for k in asdict(expected)}, asdict(expected), "frame geometry")
        array = read_scalar(record["expected_scalar"], root)
        del array
        receipt_path = validate_ref(record["numerical_receipt"], root)
        receipt = json_read(receipt_path)
        exact_keys(receipt, ("schema", "status", "frame", "expected_scalar", "error_indicator", "max_error_indicator_e", "integrator", "tile", "work"), "numerical receipt")
        same_shape_value(receipt["schema"], "m194e-float-frame-v1", "numerical schema")
        same_shape_value(receipt["status"], "uncommissioned", "numerical status")
        same_shape_value(receipt["frame"], asdict(expected), "numerical frame")
        same_shape_value(receipt["integrator"], asdict(integrator_for(arm)), "consumed integrator")
        # Numerical receipts resolve their child arrays relative to themselves.
        scalar_path = validate_ref(receipt["expected_scalar"], receipt_path.parent, True)
        if scalar_path != relative_path(record["expected_scalar"]["path"], root):
            raise ValueError("numerical receipt refers to another scalar")
        error = read_scalar(receipt["error_indicator"], receipt_path.parent)
        limit = integrator_for(arm).cell_tolerance + integrator_for(arm).pupil_tolerance
        maximum = float(error.max())
        declared = receipt["max_error_indicator_e"]
        if isinstance(declared, bool) or not isinstance(declared, (int, float)) or not np.isfinite(declared):
            raise ValueError("finite numeric maximum indicator required")
        if maximum > limit * (1 + 1e-11) or maximum != declared:
            raise ValueError("numerical indicator exceeds registered bound")
        del error
        if type(receipt["tile"]) is not int or receipt["tile"] not in (8, 16):
            raise ValueError("unregistered tile size")
        work = receipt["work"]
        exact_keys(work, ("point_calls", "angular_nodes", "peak_node_pairs", "tracked_peak_ndarray_bytes", "tracked_peak_ndarrays", "peak_live_scalar_frames",
                         "observer", "observer_events", "optional_hook_calls", "cpu_seconds", "wall_seconds"), "work")
        for key in ("point_calls", "angular_nodes", "peak_node_pairs", "tracked_peak_ndarray_bytes", "tracked_peak_ndarrays", "peak_live_scalar_frames", "observer_events", "optional_hook_calls"):
            integer(work[key], key)
        if not (work["point_calls"] <= 4_000_000 and work["angular_nodes"] <= 600_000_000 and work["peak_node_pairs"] <= 32768
                and work["tracked_peak_ndarray_bytes"] <= 32 * 1024 * 1024 and work["peak_live_scalar_frames"] == 1):
            raise ValueError("registered work/storage bound exceeded")
        for key, limit in (("cpu_seconds", 600), ("wall_seconds", 1200)):
            if isinstance(work[key], bool) or not isinstance(work[key], (int, float)) or not np.isfinite(work[key]) or not 0 <= work[key] <= limit:
                raise ValueError("registered time bound exceeded")
        if work["observer"] not in ("off", "count", "placebo"):
            raise ValueError("unknown observer")
        if work["observer"] == "off" and (work["optional_hook_calls"] != 0 or work["observer_events"] != 0):
            raise ValueError("off observer must have no optional hook calls/events")
        if work["observer"] != "off" and work["optional_hook_calls"] == 0:
            raise ValueError("active/placebo observer hook was not exercised")
        if work["observer"] == "placebo" and work["observer_events"] != 0:
            raise ValueError("placebo must not collect optional events")
        if work["observer"] == "count" and work["observer_events"] == 0:
            raise ValueError("count observer must collect events")


def validate_bundle(path):
    path = Path(path).resolve()
    bundle = json_read(path)
    exact_keys(bundle, ("schema", "status", "producer", "sensor", "scene", "ray_model", "numerical_contract", "frames", "refinements"), "float bundle")
    same_shape_value(bundle["schema"], "m194e-float-bundle-v1", "float schema")
    same_shape_value(bundle["status"], "uncommissioned", "float status")
    same_shape_value(bundle["sensor"], sensor_record(), "sensor")
    for key in ("width", "height", "black", "white"):
        integer(bundle["sensor"][key], key)
    for value in bundle["sensor"]["active_origin"]:
        integer(value, "origin")
    same_shape_value(bundle["scene"], scene_record(primary_scene()), "scene")
    same_shape_value(bundle["ray_model"], RAY_MODEL, "ray model")
    same_shape_value(bundle["numerical_contract"], numerical_contract(), "numerical contract")
    producer = bundle["producer"]
    exact_keys(producer, ("source_base", "sources", "designs", "command", "author_controls"), "producer")
    same_shape_value(producer["source_base"], "repository", "source base")
    validate_sources(producer["sources"])
    same_shape_value(producer["designs"], design_bindings(), "designs")
    if not isinstance(producer["command"], list) or not producer["command"] or any(type(v) is not str for v in producer["command"]):
        raise ValueError("command must be nonempty string list")
    control_path = validate_ref(producer["author_controls"], REPOSITORY)
    controls = json_read(control_path)
    if controls.get("schema") != "m194e-author-controls-v1" or controls.get("status") != "PASS" or not controls.get("checks") or any(c.get("pass_") is not True for c in controls["checks"]):
        raise ValueError("author control result did not pass")
    # Exact current author sources are required in the run's pre/post bindings.
    for name in AUTHOR_SOURCES:
        expected = sha256(HERE / name)
        if controls.get("sources_before", {}).get(name) != expected or controls.get("sources_after", {}).get(name) != expected:
            raise ValueError("author controls source binding changed")
    validate_frames(bundle["frames"], path.parent, "primary")
    exact_keys(bundle["refinements"], ("angle-refined", "cell-refined"), "refinements")
    for arm in ("angle-refined", "cell-refined"):
        validate_frames(bundle["refinements"][arm], path.parent, arm)
    return bundle


def validate_commission(bundle_path, commission_path, trusted_hash):
    digest(trusted_hash)
    commission_path = Path(commission_path).resolve()
    if sha256(commission_path) != trusted_hash:
        raise ValueError("external trusted float-commission digest differs")
    bundle_path = Path(bundle_path).resolve()
    bundle = validate_bundle(bundle_path)
    commission = json_read(commission_path)
    exact_keys(commission, ("schema", "status", "author_root", "author_bundle", "producer_sources", "scene", "ray_model", "numerical_contract",
                            "expected_scalars", "numerical_receipts", "author_controls", "independent_evidence"), "float commission")
    same_shape_value(commission["schema"], "m194e-float-commission-v1", "commission schema")
    same_shape_value(commission["status"], "PASS", "commission status")
    # author_root preserves original run provenance. The externally admitted
    # bundle bytes may be relocated with their unchanged relative children.
    relative_path(commission["author_root"], REPOSITORY)
    if validate_ref(commission["author_bundle"], bundle_path.parent) != bundle_path:
        raise ValueError("commission binds another author bundle")
    same_shape_value(commission["producer_sources"], bundle["producer"]["sources"], "commission sources")
    for key in ("scene", "ray_model", "numerical_contract"):
        same_shape_value(commission[key], bundle[key], "commission " + key)
    same_shape_value(commission["author_controls"], bundle["producer"]["author_controls"], "commission controls")
    for key, field in (("expected_scalars", "expected_scalar"), ("numerical_receipts", "numerical_receipt")):
        exact_keys(commission[key], (str(i) for i in range(5)), key)
        for i, frame in enumerate(bundle["frames"]):
            same_shape_value(commission[key][str(i)], frame[field], key)
    exact_keys(commission["independent_evidence"], ("controls", "author_api", "reference", "comparison"), "independent evidence")
    for ref in commission["independent_evidence"].values():
        validate_ref(ref, REPOSITORY)
    return bundle, commission
