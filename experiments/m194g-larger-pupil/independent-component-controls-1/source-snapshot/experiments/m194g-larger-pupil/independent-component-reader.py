"""Independent M194g component/payload reader. No renderer imports.

The private fixture controls do not create numerical authority. The concrete
completed-result adapters are fixed before the first released reader command.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import re
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CATALOG_SHA = "3814eeaf459e14a0a32e90ceeab6fc9d2994c92ee55bf17c824478accc3cbd41"
DESIGN_SHA = "b8fd755f53f7172405b398744915a344c09f72977c37b1eff2e73999478e314a"
MAX_JSON = 16 * 1024 * 1024
MAX_ARRAY = 32 * 1024 * 1024
DIAGNOSTIC_COLUMNS = (
    "value_error_indicator_e", "cell_indicator_e",
    "weighted_high_pupil_indicator_e", "cell_quadrature_delta_e",
)


def need(condition, message):
    if not condition:
        raise ValueError(message)


def keys(value, expected, label):
    need(type(value) is dict and set(value) == set(expected), "closed keys: " + label)


def integer(value, label, minimum=0):
    need(type(value) is int and value >= minimum, "integer: " + label)
    return value


def finite(value, label, minimum=None):
    need(type(value) in (int, float) and math.isfinite(value), "finite real: " + label)
    if minimum is not None:
        need(value >= minimum, "lower bound: " + label)
    return float(value)


def digest(value):
    need(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None,
         "lowercase SHA256 required")
    return value


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def equal_record(actual, expected, label):
    # Encoding retains bool/int/float distinctions, unlike Python dict equality.
    need(canonical(actual) == canonical(expected), "record differs: " + label)


def strict_json(data):
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, "duplicate JSON key: " + key)
            result[key] = value
        return result

    def invalid(token):
        raise ValueError("nonfinite JSON token: " + token)

    value = json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)
    need(type(value) is dict, "top-level JSON object required")

    def walk(item):
        if type(item) is float:
            need(math.isfinite(item), "nonfinite parsed JSON number")
        elif type(item) is list:
            for child in item:
                walk(child)
        elif type(item) is dict:
            for child in item.values():
                walk(child)

    walk(value)
    return value


def relative_path(root, name):
    need(type(name) is str and name and "\\" not in name and ":" not in name,
         "portable relative path required")
    pure = PurePosixPath(name)
    need(not pure.is_absolute() and all(x not in ("", ".", "..") for x in name.split("/")),
         "relative child path required")
    root = Path(root).resolve()
    path = root.joinpath(*pure.parts).resolve()
    need(path != root and path.is_relative_to(root), "child resolves outside package")
    return path


class Reads:
    """Bounded same-buffer parsing and a small before/after file ledger."""

    def __init__(self):
        self.observed = {}

    def bytes(self, path, trusted, length=None, limit=MAX_JSON):
        digest(trusted)
        if length is not None:
            integer(length, "file length")
            need(length <= limit, "declared file exceeds bound")
        path = Path(path).resolve()
        with path.open("rb") as stream:
            data = stream.read(limit + 1)
        need(len(data) <= limit, "actual file exceeds bound")
        actual = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
        need(actual["sha256"] == trusted and (length is None or len(data) == length),
             "actual file hash/length differs: " + str(path))
        old = self.observed.get(str(path))
        need(old is None or old == actual, "file changed between reads")
        self.observed[str(path)] = actual
        return data

    def external(self, path, trusted):
        return strict_json(self.bytes(path, trusted))

    def bound(self, root, ref, *, array=False, limit=MAX_JSON):
        names = ("path", "sha256", "bytes", "dtype", "shape") if array else ("path", "sha256", "bytes")
        keys(ref, names, "ArrayRef" if array else "FileRef")
        path = relative_path(root, ref["path"])
        return self.bytes(path, ref["sha256"], ref["bytes"], limit)

    def array(self, root, ref, dtype, shape):
        need(type(ref) is dict, "ArrayRef object required")
        need(type(ref.get("dtype")) is str and ref["dtype"] == dtype, "declared dtype differs")
        need(type(ref.get("shape")) is list and all(type(x) is int and x >= 0 for x in ref["shape"]),
             "typed declared shape required")
        need(ref["shape"] == list(shape), "declared shape differs")
        expected_bytes = math.prod(shape) * np.dtype(dtype).itemsize
        need(expected_bytes <= MAX_ARRAY, "array allocation exceeds bound")
        data = self.bound(root, ref, array=True, limit=min(MAX_ARRAY + 4096, expected_bytes + 4096))
        stream = io.BytesIO(data)
        # Inspect the bounded header before np.load can trust its allocation size.
        version = np.lib.format.read_magic(stream)
        need(version == (1, 0), "registered NPY v1 container required")
        actual_shape, fortran, actual_dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
        need(actual_shape == tuple(shape) and not fortran and actual_dtype.str == np.dtype(dtype).str,
             "actual NPY interpretation differs")
        need(not actual_dtype.hasobject and len(data) - stream.tell() == expected_bytes,
             "exact bounded numeric NPY payload required")
        value = np.load(io.BytesIO(data), allow_pickle=False)
        need(type(value) is np.ndarray and value.shape == tuple(shape) and value.flags.c_contiguous,
             "actual array layout differs")
        return value, data

    def finish(self):
        for name, ref in list(self.observed.items()):
            self.bytes(name, ref["sha256"], ref["bytes"], max(MAX_JSON, ref["bytes"]))


def validate_payload(scalar, branch, indices, diagnostics):
    """Actual array semantics, independently of their enclosing file hashes."""
    need(type(scalar) is np.ndarray and scalar.ndim == 2 and scalar.dtype.str == "<f8",
         "scalar must be 2D little-endian f64")
    height, width = scalar.shape
    need(height > 0 and width > 0 and np.isfinite(scalar).all(), "finite nonempty scalar required")
    need(type(branch) is np.ndarray and branch.shape == scalar.shape and branch.dtype.str == "|u1",
         "branch array interpretation differs")
    need(np.isin(branch, [0, 1, 2]).all(), "invalid branch code")
    need(type(indices) is np.ndarray and indices.ndim == 1 and indices.dtype.str == "<u4",
         "numerical indices must be little-endian u32")
    expected = np.flatnonzero(branch.ravel() == 2)
    need(np.array_equal(indices, expected), "numerical indices must exactly cover sorted numerical sites")
    need(type(diagnostics) is np.ndarray and diagnostics.shape == (len(indices), 4)
         and diagnostics.dtype.str == "<f8", "fallback diagnostic interpretation differs")
    need(np.isfinite(diagnostics).all() and (diagnostics >= 0).all(), "finite nonnegative diagnostics required")
    with np.errstate(over="ignore", invalid="ignore"):
        sums = diagnostics[:, 1] + diagnostics[:, 2]
    need(np.isfinite(sums).all() and np.array_equal(diagnostics[:, 0], sums),
         "direct receipt value-indicator sum differs")
    return {"height": height, "width": width, "numerical_sites": len(indices),
            "branch_counts": {name: int(np.count_nonzero(branch == code))
                              for code, name in enumerate(("foreground", "background", "numerical"))}}


def payload_equal(left, right):
    need(type(left) is dict and type(right) is dict and set(left) == set(right)
         == {"scalar", "branch", "indices", "diagnostics"}, "four payload arrays required")
    validate_payload(**left)
    validate_payload(**right)
    for name in left:
        need(left[name].shape == right[name].shape and left[name].dtype == right[name].dtype
             and left[name].tobytes(order="C") == right[name].tobytes(order="C"),
             "same-method payload bytes differ: " + name)


def comparison(values, targets, maximum, rms=None):
    need(len(values) == len(targets) and len(values) > 0, "nonempty matched value population required")
    differences = [finite(a, "value") - finite(b, "target") for a, b in zip(values, targets)]
    need(all(math.isfinite(v) for v in differences), "nonfinite value difference")
    measured_max = max(abs(v) for v in differences)
    # Scaling avoids overflow in a malformed but finite very-large vector.
    measured_rms = (measured_max * math.sqrt(math.fsum((v / measured_max) ** 2 for v in differences)
                                           / len(differences))) if measured_max else 0.0
    need(measured_max <= maximum and (rms is None or measured_rms <= rms), "numerical comparison bar failed")
    return {"count": len(differences), "maximum_abs_e": measured_max, "rms_e": measured_rms}


def fault_power(value, targets, threshold=.004):
    differences = [abs(finite(value, "fault value") - finite(v, "reference value")) for v in targets]
    need(len(differences) == 2 and all(math.isfinite(x) and x > threshold for x in differences),
         "actual fixed fault lacks required power against both references")
    return differences


def expected_keys(catalog):
    cases = catalog["cases"]
    need(type(cases) is list and len(cases) == 150, "all 150 catalog cases required")
    ids = [c["id"] for c in cases]
    need(len(set(ids)) == 150, "catalog IDs must be unique")
    author = {(c["id"], arm, method) for c in cases
              for arm in c["author_arms"] for method in c["author_methods"]}
    reference = {(c["id"], arm) for c in cases for arm in c["reference_arms"]}
    need(len(author) == 299 and len(reference) == 300, "literal expanded population differs")
    return author, reference


def textured_ids(catalog):
    def nonconstant(field):
        return any(x != 0 for x in field["affine"]) or any(w["amplitude"] != 0 for w in field["waves"])
    return {c["id"] for c in catalog["cases"]
            if any(nonconstant(catalog["fields"][c["scene"][name]])
                   for name in ("foreground_field", "background_field"))}


def compare_component_values(catalog, author_rows, reference_rows):
    """Normalized rows are produced only after closed source/result validation."""
    expected_author, expected_reference = expected_keys(catalog)
    author, reference = {}, {}
    for row in author_rows:
        keys(row, ("case_id", "arm", "method", "value_e"), "normalized author row")
        key = (row["case_id"], row["arm"], row["method"])
        need(all(type(x) is str for x in key) and key not in author, "duplicate/invalid author key")
        author[key] = finite(row["value_e"], "author scalar")
    for row in reference_rows:
        keys(row, ("case_id", "arm", "value_e"), "normalized reference row")
        key = (row["case_id"], row["arm"])
        need(all(type(x) is str for x in key) and key not in reference, "duplicate/invalid reference key")
        reference[key] = finite(row["value_e"], "reference scalar")
    need(set(author) == expected_author and set(reference) == expected_reference, "required component population differs")
    refinement = comparison([reference[(c["id"], "primary")] for c in catalog["cases"]],
                            [reference[(c["id"], "refined")] for c in catalog["cases"]], .0005)
    textured = textured_ids(catalog)
    groups = defaultdict(lambda: ([], []))
    rows = []
    for (case_id, arm, method), value in sorted(author.items()):
        for reference_arm in ("primary", "refined"):
            target = reference[(case_id, reference_arm)]
            record = comparison([value], [target], .004)
            rows.append({"case_id": case_id, "arm": arm, "method": method,
                         "reference_arm": reference_arm, **record})
            if case_id in textured:
                values, targets = groups[(arm, method, reference_arm)]
                values.append(value)
                targets.append(target)
    rms_rows = [{"arm": arm, "method": method, "reference_arm": ref_arm,
                 **comparison(values, targets, .004, .0008)}
                for (arm, method, ref_arm), (values, targets) in sorted(groups.items())]
    return {"comparisons": rows, "independent_refinement": refinement,
            "textured_ids": sorted(textured), "textured_groups": rms_rows}


def read_execution(reads, path, trusted, *, scope, argv=None):
    release = reads.external(path, trusted)
    keys(release, ("schema", "scope", "source_bindings", "inputs", "commands"), "execution release")
    need(release["schema"] == "m194g-numerical-execution-release-v1" and release["scope"] == scope,
         "execution release schema/scope differs")
    need(type(release["source_bindings"]) is dict and release["source_bindings"], "source binding map required")
    for name, ref in release["source_bindings"].items():
        keys(ref, ("sha256", "bytes"), "source binding")
        reads.bound(REPO, {"path": name, **ref})
    need(type(release["inputs"]) is list, "execution input list required")
    seen = set()
    for ref in release["inputs"]:
        keys(ref, ("path", "sha256", "bytes"), "execution input")
        resolved = str(relative_path(REPO, ref["path"])).casefold()
        need(resolved not in seen, "duplicate execution input")
        seen.add(resolved)
        reads.bound(REPO, ref, limit=MAX_ARRAY + 4096)
    commands = release["commands"]
    need(type(commands) is list and commands and all(type(row) is list and row
         and all(type(x) is str for x in row) for row in commands), "literal execution commands required")
    if argv is not None:
        permitted = [[trusted if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in row] for row in commands]
        need(list(argv) in permitted, "actual interpreter argv not released")
    return release


def author_work(work):
    names = ("scope", "limits", "point_calls", "angular_nodes", "peak_node_pairs",
             "tracked_peak_ndarray_bytes", "tracked_peak_ndarrays", "peak_live_scalar_frames",
             "observer", "observer_events", "optional_hook_calls", "cell_allocation",
             "cpu_seconds", "wall_seconds", "cumulative_point_calls", "cumulative_angular_nodes",
             "frames_started", "check_calls", "hybrid_hook_calls", "hybrid_collection",
             "transfer_cache_entries", "transfer_cache_limit")
    keys(work, names, "author component work")
    need(work["scope"] == "components" and work["observer"] in ("off", "count", "placebo"), "component work scope/mode")
    limits = dict(points=16000000, nodes=2400000000, cpu=600, wall=1200, arrays=33554432, pairs=32768)
    equal_record(work["limits"], limits, "component resource limits")
    for name in set(names) - {"scope", "limits", "observer", "cell_allocation", "cpu_seconds", "wall_seconds", "hybrid_collection"}:
        integer(work[name], name)
    need(work["point_calls"] == work["cumulative_point_calls"] <= limits["points"]
         and work["angular_nodes"] == work["cumulative_angular_nodes"] <= limits["nodes"], "component cumulative work bound")
    need(work["peak_node_pairs"] <= 32768 and work["tracked_peak_ndarray_bytes"] <= 33554432
         and work["peak_live_scalar_frames"] <= 1 and work["transfer_cache_entries"] <= 20
         and work["transfer_cache_limit"] == 20, "component storage/pair/cache bound")
    need(finite(work["cpu_seconds"], "CPU seconds", 0) <= 600
         and finite(work["wall_seconds"], "wall seconds", 0) <= 1200, "component time bound")
    need(type(work["hybrid_collection"]) is dict and all(type(k) is str for k in work["hybrid_collection"]), "hybrid event map")
    for key, count in work["hybrid_collection"].items():
        integer(count, "collection " + key)
    allocation = work["cell_allocation"]
    keys(allocation, ("cells", "leaves", "minimum_depth", "maximum_depth", "locally_overallocated_leaves",
                      "cells_with_locally_overallocated_leaves"), "cell allocation")
    for key, count in allocation.items():
        integer(count, "allocation " + key)
    need(allocation["minimum_depth"] <= allocation["maximum_depth"] <= 6, "allocation depth bound")
    return work


def author_frame(reads, path, trusted, expected_inputs, source_digest):
    receipt = reads.external(path, trusted)
    keys(receipt, ("schema", "status", "inputs", "source_set_sha256", "arrays", "diagnostic_columns",
                   "branch_codes", "analytic_error_scope", "completed_cells", "traversal", "traversal_sha256",
                   "work_before", "work_after"), "author frame receipt")
    need(receipt["schema"] == "m194g-author-frame-v1" and receipt["status"] == "complete-uncommissioned", "author frame status/schema")
    equal_record(receipt["inputs"], expected_inputs, "actual observer inputs")
    need(receipt["source_set_sha256"] == digest(source_digest), "frame exercised-source digest differs")
    equal_record(receipt["branch_codes"], {"foreground": 0, "background": 1, "numerical": 2}, "branch code map")
    equal_record(receipt["diagnostic_columns"], list(DIAGNOSTIC_COLUMNS), "diagnostic columns")
    need(type(receipt["analytic_error_scope"]) is str and receipt["analytic_error_scope"], "analytic limitation required")
    width, height = expected_inputs["width"], expected_inputs["height"]
    integer(width, "width", 1)
    integer(height, "height", 1)
    need(integer(receipt["completed_cells"], "completed cells") == width * height, "complete frame required")
    need(receipt["traversal"] in ("row-major", "reverse-row-major"), "registered traversal required")
    order = range(width * height) if receipt["traversal"] == "row-major" else range(width * height - 1, -1, -1)
    trace = hashlib.sha256()
    for index in order:
        trace.update(index.to_bytes(4, "little"))
    need(receipt["traversal_sha256"] == trace.hexdigest(), "actual traversal witness differs")
    for key in ("work_before", "work_after"):
        author_work(receipt[key])
    refs = receipt["arrays"]
    keys(refs, ("scalar", "branch", "fallback_indices", "fallback_diagnostics"), "four frame arrays")
    parent = Path(path).resolve().parent
    paths = [str(relative_path(parent, ref["path"])).casefold() for ref in refs.values()]
    need(len(set(paths)) == 4, "distinct frame payload paths required")
    scalar, scalar_raw = reads.array(parent, refs["scalar"], "<f8", (height, width))
    branch, branch_raw = reads.array(parent, refs["branch"], "|u1", (height, width))
    n = int(np.count_nonzero(branch == 2))
    indices, index_raw = reads.array(parent, refs["fallback_indices"], "<u4", (n,))
    diagnostics, diagnostics_raw = reads.array(parent, refs["fallback_diagnostics"], "<f8", (n, 4))
    arrays = dict(scalar=scalar, branch=branch, indices=indices, diagnostics=diagnostics)
    summary = validate_payload(**arrays)
    return receipt, arrays, {"scalar": scalar_raw, "branch": branch_raw,
                              "indices": index_raw, "diagnostics": diagnostics_raw}, summary


def case_inputs(catalog, case):
    record = case["scene"]
    scene = {"foreground": catalog["fields"][record["foreground_field"]],
             "background": catalog["fields"][record["background_field"]],
             **{key: record[key] for key in ("depths", "mask_normal", "mask_offset", "mask_state")}}
    return {"scene": scene, "frame": catalog["frames"][case["frame"]], "native_xy": case["native_xy"]}


def planned_calls(catalog):
    calls = [{"case_id": c["id"], "arm": arm, "method": method, "phase": "baseline", "fault_id": None}
             for c in catalog["cases"] for arm in c["author_arms"] for method in c["author_methods"]]
    cases = {c["id"]: c for c in catalog["cases"]}
    def add(case_id, phase, fault_id):
        c = cases[case_id]
        calls.append({"case_id": case_id, "arm": c["author_arms"][0], "method": c["author_methods"][0],
                      "phase": phase, "fault_id": fault_id})
    for spec in catalog["active_fault_targets"]:
        fid = spec["id"]
        if fid in ("stale-frequency-cache", "cached-phase-zero"):
            add("transfer-negative-one-full" if fid == "stale-frequency-cache" else "coordinate-centre-phase-zero", "cache-prime", fid)
        add(spec["target_case"], "fault", fid)
        add(spec["target_case"], "restored", fid)
    add("transfer-zero-full", "fault", "zero-over-zero")
    add("transfer-zero-full", "restored", "zero-over-zero")
    need(len(calls) == 331, "fixed complete author call schedule differs")
    return calls


def monotone_work(before, after, names, label):
    for name in names:
        need(after[name] >= before[name], "work reset: " + label + ":" + name)


AUTHOR_CUMULATIVE = ("cumulative_point_calls", "cumulative_angular_nodes", "frames_started", "check_calls",
                     "optional_hook_calls", "observer_events", "hybrid_hook_calls", "cpu_seconds", "wall_seconds")


def read_author_rows(reads, result, root, catalog):
    expected = planned_calls(catalog)
    equal_record(result["planned_calls"], expected, "fixed author plan")
    need(type(result["rows"]) is list and len(result["rows"]) == len(expected), "all331 author call records required")
    cases = {c["id"]: c for c in catalog["cases"]}
    normalized_rows, indexed, previous = [], {}, None
    for index, (row, planned) in enumerate(zip(result["rows"], expected)):
        keys(row, ("case_id", "group", "call", "arm", "method", "phase", "fault_id", "inputs", "status",
                   "value_e", "branch", "receipt", "error", "work_before", "work_after"), "author call row")
        equal_record({k: row[k] for k in planned}, planned, "actual author call order")
        case = cases[row["case_id"]]
        need(row["group"] == case["group"] and row["call"] == case["call"], "author call kind/group differs")
        equal_record(row["inputs"], case_inputs(catalog, case), "actual author component input")
        # Individual row files are directly persisted witnesses, not additional calls.
        path = Path(root) / "component-rows" / f"{index:04d}.json"
        raw = canonical(row) + b"\n"
        persisted = strict_json(reads.bytes(path, hashlib.sha256(raw).hexdigest(), len(raw)))
        equal_record(persisted, row, "persisted author call")
        before, after = author_work(row["work_before"]), author_work(row["work_after"])
        monotone_work(before, after, AUTHOR_CUMULATIVE, "author call")
        if previous is not None:
            monotone_work(previous, before, AUTHOR_CUMULATIVE, "between author calls")
        previous = after
        key = (row["case_id"], row["arm"], row["method"], row["phase"], row["fault_id"])
        need(key not in indexed, "duplicate author attempted call")
        indexed[key] = row
        if row["phase"] == "fault" and row["fault_id"] == "zero-over-zero":
            need(row["status"] == "refused" and row["value_e"] is None and row["receipt"] is None
                 and type(row["error"]) is str and "nonfinite" in row["error"], "actual nonfinite zero refusal required")
            continue
        need(row["status"] == "returned" and row["error"] is None, "all required ordinary/fault scalar calls must return")
        finite(row["value_e"], "actual author value", 0)
        receipt = row["receipt"]
        need(type(receipt) is dict and receipt["branch"] == row["branch"], "actual author branch receipt differs")
        need(receipt["active_fault"] == (row["fault_id"] if row["phase"] == "fault" else None), "fault active outside mutated phase")
        if row["phase"] != "fault":
            if row["method"] == "analytic-disabled":
                need(row["branch"] == "numerical" and "fallback" in receipt, "disabled method did not consume fallback")
            elif row["method"] == "frozen-point":
                need(row["branch"] == "point" and "fallback" in receipt, "point method differs")
            elif "expected_branch" in case:
                need(row["branch"] == case["expected_branch"], "author tight selector branch differs")
        if row["phase"] == "baseline":
            normalized_rows.append({k: row[k] for k in ("case_id", "arm", "method", "value_e")})
    author_work(result["work"])
    monotone_work(previous, result["work"], AUTHOR_CUMULATIVE, "terminal author work")
    return normalized_rows, indexed


def reference_work(work):
    keys(work, ("evaluations", "cpu_seconds", "wall_seconds", "limits", "factor_evaluations", "chord_evaluations",
                "peak_explicit_array_bytes", "live_scalar_frame_owners", "array_accounting_scope"), "reference work")
    keys(work["limits"], ("evaluations", "cpu_seconds", "wall_seconds"), "reference limits")
    need(integer(work["limits"]["evaluations"], "reference evaluation limit") == 30000000
         and finite(work["limits"]["cpu_seconds"], "reference CPU limit") == 600
         and finite(work["limits"]["wall_seconds"], "reference wall limit") == 1200, "fixed reference limits differ")
    for name in ("evaluations", "factor_evaluations", "chord_evaluations", "peak_explicit_array_bytes", "live_scalar_frame_owners"):
        integer(work[name], name)
    need(work["evaluations"] == work["factor_evaluations"] + work["chord_evaluations"] <= 30000000,
         "actual reference evaluation total differs")
    need(work["peak_explicit_array_bytes"] <= 33554432 and work["live_scalar_frame_owners"] <= 1, "reference storage bound")
    need(finite(work["cpu_seconds"], "reference CPU", 0) <= 600
         and finite(work["wall_seconds"], "reference wall", 0) <= 1200, "reference time bound")
    need(type(work["array_accounting_scope"]) is str and work["array_accounting_scope"], "reference storage scope required")
    return work


REFERENCE_CUMULATIVE = ("evaluations", "factor_evaluations", "chord_evaluations", "cpu_seconds", "wall_seconds")


def reference_row(row, catalog, *, case_id, arm, phase="baseline", fault_id=None):
    keys(row, ("case_id", "arm", "method", "phase", "fault_id", "call", "scene", "frame", "native_xy", "status",
               "value_e", "branch", "receipt", "work_before", "work_after", "engine_before", "engine_after", "error"), "reference component row")
    need(row["case_id"] == case_id and row["arm"] == arm and row["method"] == "m194g-independent-spatial-cache-v1"
         and row["phase"] == phase and row["fault_id"] == fault_id, "reference row identity differs")
    case = next(c for c in catalog["cases"] if c["id"] == case_id)
    expected = case_inputs(catalog, case)
    equal_record({k: row[k] for k in ("scene", "frame", "native_xy")}, expected, "independent reference input")
    need(row["call"] == case["call"], "reference point/cell call differs")
    before, after = reference_work(row["work_before"]), reference_work(row["work_after"])
    monotone_work(before, after, REFERENCE_CUMULATIVE, "reference call")
    target = {"primary": .000125, "refined": .0000078125}[arm]
    for key in ("engine_before", "engine_after"):
        engine = row[key]
        keys(engine, ("method", "target_e", "cache_entries", "cache_hits", "cache_misses", "cache_evictions",
                      "transfer_consumptions", "branch_counts"), "independent engine receipt")
        need(engine["method"] == "m194g-independent-spatial-cache-v1" and finite(engine["target_e"], "reference actual target") == target,
             "actual independent method/target differs")
        for count in ("cache_entries", "cache_hits", "cache_misses", "cache_evictions", "transfer_consumptions"):
            integer(engine[count], count)
        need(engine["cache_entries"] <= 20, "independent cache exceeds fixed bound")
        keys(engine["branch_counts"], ("foreground", "background", "numerical", "point"), "reference consumed branches")
        for count in engine["branch_counts"].values():
            integer(count, "reference branch count")
    if phase == "fault" and fault_id in ("zero-over-zero", "stale-target"):
        need(row["status"] == "REFUSED" and row["value_e"] is None and type(row["error"]) is str, "reference refusal required")
        return row
    need(row["status"] == "VALUE" and row["error"] is None and type(row["receipt"]) is dict,
         "all required reference values must complete")
    finite(row["value_e"], "independent actual scalar", 0)
    need(row["branch"] in ("foreground", "background", "numerical", "point")
         and row["receipt"]["branch"] == row["branch"], "independent branch receipt differs")
    # Wider independent selector branches intentionally need not match author.
    return row


def source_closure(reads, before, after, root, snapshot_dirs, required, release):
    need(type(before) is dict and before and type(after) is dict, "completed exercised source maps required")
    equal_record(after, before, "exercised source before/after")
    need(set(required) <= set(before), "exercised source closure omits actual dependency")
    for name, ref in before.items():
        keys(ref, ("sha256", "bytes"), "exercised source binding")
        reads.bound(REPO, {"path": name, **ref})
        if name in release["source_bindings"]:
            equal_record(ref, release["source_bindings"][name], "released exercised source")
        for directory in snapshot_dirs:
            reads.bound(Path(root) / directory, {"path": name, **ref})
    return {"exercised_sources": len(before), "entry_union_sources": len(release["source_bindings"]),
            "snapshot_directories": list(snapshot_dirs)}


def observer_inputs(catalog, arm, index):
    population = catalog["observer_population"]
    return {"scene": population["scene"], "frame": {"index": index,
            "inverse_focus": population["inverse_foci"][index], "K": population["K"],
            "forward_similarity": population["forward_similarity"]},
            "width": population["width"], "height": population["height"], "arm": arm, "method": "analytic-enabled"}


def read_observers(reads, result, root, catalog):
    executions = result["observer_executions"]
    population = catalog["observer_population"]
    need(type(executions) is list and len(executions) == 4, "all four observer executions required")
    source_digest = hashlib.sha256(canonical(result["sources_before"]) + b"\n").hexdigest()
    baseline_paths, summaries = {}, []
    expected_frames = [(arm, index) for arm in population["arms"] for index in population["frame_indices"]]
    for index, (execution, setting) in enumerate(zip(executions, population["executions"])):
        keys(execution, ("execution", "observer", "traversal", "frames", "work_before", "work_after",
                         "hybrid_hook_calls", "fallback_hook_calls", "collected_array_events", "hybrid_collection"), "observer execution")
        need(integer(execution["execution"], "execution index") == index and execution["observer"] == setting["observer"]
             and execution["traversal"] == setting["traversal"], "fixed observer schedule differs")
        before, after = author_work(execution["work_before"]), author_work(execution["work_after"])
        monotone_work(before, after, AUTHOR_CUMULATIVE, "observer execution")
        for name, counter in (("hybrid_hook_calls", "hybrid_hook_calls"), ("fallback_hook_calls", "optional_hook_calls"),
                              ("collected_array_events", "observer_events")):
            need(integer(execution[name], name) == after[counter] - before[counter], "observer actual count delta differs")
        delta = {key: after["hybrid_collection"].get(key, 0) - before["hybrid_collection"].get(key, 0)
                 for key in set(after["hybrid_collection"]) | set(before["hybrid_collection"])}
        delta = {key: value for key, value in delta.items() if value}
        equal_record(execution["hybrid_collection"], delta, "actual observer collection")
        mode = setting["observer"]
        if mode == "off":
            need(execution["hybrid_hook_calls"] == execution["fallback_hook_calls"] == execution["collected_array_events"] == 0
                 and not delta, "off observer must not collect or invoke optional hooks")
        elif mode == "placebo":
            need(execution["hybrid_hook_calls"] > 0 and execution["fallback_hook_calls"] > 0
                 and execution["collected_array_events"] == 0 and not delta, "placebo hook must execute without collecting")
        else:
            required_events = ["wave:" + layer + ":" + sign for layer in ("foreground", "background")
                               for sign in ("zero-defocus", "nonzero-defocus")]
            required_events += ["signed-wave:foreground:" + sign for sign in ("negative", "zero", "positive")]
            required_events += ["signed-wave:background:" + sign for sign in ("zero", "positive")]
            need(execution["hybrid_hook_calls"] > 0 and execution["fallback_hook_calls"] > 0
                 and execution["collected_array_events"] > 0 and all(delta.get(key, 0) > 0 for key in required_events),
                 "count observer lacks consumed wave/sign/collection witnesses")
        frames = execution["frames"]
        need(type(frames) is list and len(frames) == 15, "all15 observer frames required")
        seen_paths = set()
        for frame_row, (arm, frame_index) in zip(frames, expected_frames):
            keys(frame_row, ("arm", "frame_index", "receipt"), "observer frame reference")
            need(frame_row["arm"] == arm and integer(frame_row["frame_index"], "frame index") == frame_index,
                 "fixed observer frame/arm order differs")
            ref = frame_row["receipt"]
            reads.bound(root, ref)
            path = relative_path(root, ref["path"])
            need(str(path).casefold() not in seen_paths, "duplicate observer frame receipt")
            seen_paths.add(str(path).casefold())
            inputs = observer_inputs(catalog, arm, frame_index)
            receipt, arrays, raw, summary = author_frame(reads, path, ref["sha256"], inputs, source_digest)
            need(receipt["traversal"] == setting["traversal"], "actual frame traversal differs")
            for branch, (x, y) in population["branch_witnesses"].items():
                need(int(arrays["branch"][y, x]) == population["branch_codes"][branch], "independent observer branch witness fails")
            key = (arm, frame_index)
            if index == 0:
                baseline_paths[key] = (path, ref["sha256"])
            else:
                baseline_path, baseline_sha = baseline_paths[key]
                old_receipt, old_arrays, old_raw, _ = author_frame(reads, baseline_path, baseline_sha, inputs, source_digest)
                payload_equal(old_arrays, arrays)
                need(raw == old_raw, "actual same-method NPY bytes differ")
                need((receipt["traversal_sha256"] != old_receipt["traversal_sha256"]) == (index == 3),
                     "actual reversed traversal witness not powered")
                del old_arrays, old_raw
            summaries.append({"execution": index, "arm": arm, "frame_index": frame_index, **summary,
                              "payload_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()}})
            del arrays, raw
    need(len(summaries) == 60 and sum(row["height"] * row["width"] for row in summaries) == 3240,
         "complete observer scalar population differs")
    return summaries


def read_reference_values(result, catalog):
    rows = result["baseline"]
    expected = [(case["id"], arm) for case in catalog["cases"] for arm in ("primary", "refined")]
    need(type(rows) is list and len(rows) == 300, "all300 reference values required")
    values, indexed, previous = [], {}, None
    for row, (case_id, arm) in zip(rows, expected):
        reference_row(row, catalog, case_id=case_id, arm=arm)
        if previous is not None:
            monotone_work(previous, row["work_before"], REFERENCE_CUMULATIVE, "between reference calls")
        previous = row["work_after"]
        indexed[(case_id, arm)] = row
        values.append({k: row[k] for k in ("case_id", "arm", "value_e")})
    reference_work(result["budget"])
    monotone_work(previous, result["budget"], REFERENCE_CUMULATIVE, "terminal reference work")
    need(type(result["refinement"]) is list and len(result["refinement"]) == 150, "all150 refinement records required")
    for record, case in zip(result["refinement"], catalog["cases"]):
        keys(record, ("case_id", "maximum_e", "limit_e", "passed"), "reference refinement row")
        delta = abs(indexed[(case["id"], "primary")]["value_e"] - indexed[(case["id"], "refined")]["value_e"])
        need(record["case_id"] == case["id"] and record["passed"] is True and record["limit_e"] == .0005
             and finite(record["maximum_e"], "reported reference refinement", 0) == delta <= .0005,
             "actual reference refinement differs or fails")
    return values, indexed


def read_fault_values(author_index, reference_result, reference_index, catalog):
    summaries = []
    groups = reference_result["faults"]
    need(type(groups) is list and len(groups) == 14, "all14 reference faults required")
    cases = {c["id"]: c for c in catalog["cases"]}
    for spec, group in zip(catalog["active_fault_targets"], groups):
        fid, case_id = spec["id"], spec["target_case"]
        case = cases[case_id]
        arm, method = case["author_arms"][0], case["author_methods"][0]
        before = author_index[(case_id, arm, method, "baseline", None)]
        bad = author_index[(case_id, arm, method, "fault", fid)]
        restored = author_index[(case_id, arm, method, "restored", fid)]
        targets = [reference_index[(case_id, r)]["value_e"] for r in ("primary", "refined")]
        author_power = fault_power(bad["value_e"], targets)
        comparison([restored["value_e"]] * 2, targets, .004)
        need(np.float64(before["value_e"]).tobytes() == np.float64(restored["value_e"]).tobytes(), "author restored scalar bytes differ")
        keys(group, ("fault_id", "target_case", "before", "prime", "mutated", "restored", "difference_e",
                     "minimum_exclusive_e", "restored_scalar_bytes_equal", "passed"), "reference fault group")
        need(group["fault_id"] == fid and group["target_case"] == case_id and group["minimum_exclusive_e"] == .004,
             "fixed reference fault target differs")
        equal_record(group["before"], reference_index[(case_id, "refined")], "reference fault baseline")
        ref_bad = reference_row(group["mutated"], catalog, case_id=case_id, arm="refined", phase="fault", fault_id=fid)
        ref_good = reference_row(group["restored"], catalog, case_id=case_id, arm="refined", phase="restored", fault_id=fid)
        reference_power = fault_power(ref_bad["value_e"], targets)
        comparison([ref_good["value_e"]] * 2, targets, .004)
        need(np.float64(ref_good["value_e"]).tobytes() == np.float64(targets[1]).tobytes(), "reference restored scalar bytes differ")
        actual_delta = abs(ref_bad["value_e"] - targets[1])
        need(finite(group["difference_e"], "fault actual difference", 0) == actual_delta and group["passed"] is True
             and group["restored_scalar_bytes_equal"] is True, "reference fault summary differs from actual values")
        if fid in ("stale-frequency-cache", "cached-phase-zero"):
            prime_id = "transfer-negative-one-full" if fid == "stale-frequency-cache" else "coordinate-centre-phase-zero"
            reference_row(group["prime"], catalog, case_id=prime_id, arm="refined", phase="cache-prime", fault_id=fid)
        else:
            need(group["prime"] is None, "unexpected reference prime")
        summaries.append({"fault_id": fid, "case_id": case_id, "author_discrepancies_e": author_power,
                          "independent_discrepancies_e": reference_power, "required_strictly_greater_e": .004})
    return summaries


def read_oracles(reads, result, reference_index, author_index, catalog):
    cases = {c["id"]: c for c in catalog["cases"]}
    wanted = [c["id"] for c in catalog["cases"] if c["group"] in ("transfer", "coordinate", "joint", "preserved-whole-cell")
              or c["id"].endswith("equal-null")]
    expected_keys_set = {(case_id, arm) for case_id in wanted for arm in ("primary", "refined")}
    seen, summaries = set(), []
    for row in result["oracles"]:
        keys(row, ("case_id", "arm", "expected_e", "actual_e", "absolute_error_e", "limit_e", "passed", "evidence"), "literal oracle row")
        key = (row["case_id"], row["arm"])
        need(key in expected_keys_set and key not in seen, "oracle population differs")
        seen.add(key)
        expected = finite(row["expected_e"], "oracle expectation", 0)
        actual = reference_index[key]["value_e"]
        need(row["actual_e"] == actual and row["limit_e"] == .004 and row["passed"] is True,
             "oracle actual/limit/status differs")
        error = abs(actual - expected)
        need(finite(row["absolute_error_e"], "oracle discrepancy", 0) == error <= .004, "actual oracle comparison fails")
        case = cases[key[0]]
        literal = None
        if case["id"] == "joint-relative-sign-point":
            literal = 11000 + 400 / math.pi
        elif case["id"] == "joint-zero-pupil-cell":
            literal = 13816.0
        elif case["id"].endswith("equal-null"):
            literal = 12000.0
        elif case["id"].startswith("transfer-zero-"):
            literal = 11000.0
        elif case["id"] == "coordinate-affine":
            inp = case_inputs(catalog, case)
            sim = inp["frame"]["forward_similarity"]
            x, y = inp["native_xy"]
            cx, cy = sim["centre"]
            tx, ty = sim["translation"]
            cosine, sine = math.cos(sim["rotation"]), math.sin(sim["rotation"])
            qx = cx + (cosine * (x - cx - tx) + sine * (y - cy - ty)) / sim["scale"]
            qy = cy + (-sine * (x - cx - tx) + cosine * (y - cy - ty)) / sim["scale"]
            field = inp["scene"]["foreground"]
            literal = field["constant"] + field["affine"][0] * qx + field["affine"][1] * qy
        elif case["group"] == "preserved-whole-cell":
            retained = case["retained_reference"]["array"]
            path = relative_path(REPO, retained["path"])
            ref = {**retained, "bytes": path.stat().st_size, "dtype": "<f8", "shape": [48, 64]}
            values, _ = reads.array(REPO, ref, "<f8", (48, 64))
            literal = float(values[tuple(case["retained_reference"]["index_yx"])])
        if literal is not None:
            if case["id"] == "coordinate-affine":
                comparison([expected], [literal], .004)
            else:
                need(expected == literal, "fixed independent literal/archive oracle differs")
            comparison([actual], [literal], .004)
            for arm in case["author_arms"]:
                for method in case["author_methods"]:
                    comparison([author_index[(case["id"], arm, method, "baseline", None)]["value_e"]], [literal], .004)
        summaries.append({"case_id": key[0], "reference_arm": key[1], "expected_e": expected,
                          "actual_e": actual, "absolute_error_e": error, "separately_rechosen_literal": literal is not None})
    need(seen == expected_keys_set and len(seen) == 52, "all52 independent oracle comparisons required")
    return summaries


def absolute_ref(reads, ref, expected):
    keys(ref, ("path", "sha256", "bytes"), "absolute recorded witness")
    need(type(ref["path"]) is str and Path(ref["path"]).is_absolute()
         and Path(ref["path"]).resolve() == Path(expected).resolve(), "absolute witness path differs")
    return reads.bytes(expected, ref["sha256"], ref["bytes"])


def verify_controls(reads, path, trusted):
    controls = reads.external(path, trusted)
    need(controls["schema"] == "m194g-independent-component-controls-command-v1"
         and controls["status"] == "PASS_PRIVATE_COMPONENT_CONTROLS" and controls["fixture_only"] is True
         and controls["exception"] is None and controls["finalization_error"] is None
         and controls["sources_unchanged"] is True, "complete genuine private-control command required")
    groups = controls["groups"]
    need(type(groups) is list and len(groups) == 3, "all three private control groups required")
    expected = ("m194g-independent-component-private-controls-v1", "m194g-independent-component-resource-controls-v1",
                "m194g-independent-component-entry-controls-v1")
    names, count = set(), 0
    for group, schema in zip(groups, expected):
        keys(group, ("schema", "fixture_only", "status", "checks", "check_count"), "private control group")
        need(group["schema"] == schema and group["fixture_only"] is True and group["status"] == "PASS_PRIVATE_CONTROLS",
             "private control group status/schema differs")
        need(integer(group["check_count"], "private control count", 1) == len(group["checks"]), "private check extent differs")
        for row in group["checks"]:
            need(type(row) is dict and row["passed"] is True and type(row["name"]) is str and row["name"] not in names,
                 "all unique actual private controls must pass")
            names.add(row["name"])
            if row["expected_refusal"]:
                need(type(row["expected_exception"]) is str and type(row["expected_boundary"]) is str
                     and type(row["error"]) is str and row["error"].startswith(row["expected_exception"] + ":")
                     and re.search(row["expected_boundary"], row["error"]) is not None,
                     "private refusal has wrong actual exception/boundary")
        count += group["check_count"]
    need(integer(controls["check_count"], "complete private count") == count, "complete private count differs")
    required = {"actual-npy-all-four-reopened-byte-companion", "payload-numerical-delta-plus-point01",
                "payload-swapped-sum-preserving-columns", "fault-power-equality-is-not-power",
                "catalog-one-method-rms-cannot-be-diluted", "author-cumulative-one-more-refuses",
                "author-actual-analytic-cache-clock-crossing", "reference-live-owner-storage-one-byte-over",
                "author-second-live-scalar-refuses", "reference-second-live-scalar-refuses",
                "entry-rehashed-omitted-model", "entry-unreleased-actual-argv",
                "entry-actual-run-preserves-primary-and-secondary-errors"}
    need(required <= names, "deciding private controls omitted")
    for name, ref in controls["source_bindings"].items():
        reads.bound(REPO, {"path": name, **ref})
        reads.bound(Path(path).parent / "source-snapshot", {"path": name, **ref})
    for name in ("independent-component-reader.py", "independent-component-controls.py"):
        need("experiments/m194g-larger-pupil/" + name in controls["source_bindings"], "current reader/control source omitted")
    return {"actual_checks": count, "groups": len(groups), "fixture_scope": True}


def check_invocation(invocation, release, release_sha, root, script, *, reference=False):
    name = "interpreter_argv" if reference else "orig_argv"
    argv = invocation[name]
    need(type(argv) is list and argv and all(type(x) is str for x in argv), "original interpreter argv required")
    permitted = [[release_sha if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in row] for row in release["commands"]]
    need(argv in permitted, "actual recorded command not in original execution release")
    need("-X" in argv and "faulthandler" in argv and any(x.startswith("pycache_prefix=") for x in argv),
         "declared fresh-cache/faulthandler command absent")
    script_path = HERE / script
    need(any(Path(x).name == script and (Path(x) if Path(x).is_absolute() else REPO / x).resolve() == script_path for x in argv),
         "actual component script differs")
    need(argv.count("--output") == 1 and (REPO / argv[argv.index("--output") + 1]).resolve() == Path(root).resolve(),
         "actual output directory differs")
    need(type(invocation["executable"]) is str and Path(invocation["executable"]).is_absolute(), "actual interpreter provenance required")


def verify(author_path, author_sha, reference_path, reference_sha, execution_path, execution_sha,
           controls_path, controls_sha):
    reads = Reads()
    release = read_execution(reads, execution_path, execution_sha, scope="components")
    catalog = reads.external(HERE / "component-population.json", CATALOG_SHA)
    need(catalog["resolved_design"]["sha256"] == DESIGN_SHA, "fixed numerical design differs")
    author, reference = reads.external(author_path, author_sha), reads.external(reference_path, reference_sha)
    keys(author, ("schema", "status", "scope", "invocation", "execution_release", "catalog", "inputs_sha256",
                  "sources_before", "sources_after", "source_capture_error", "planned_calls", "rows", "observer_executions",
                  "checks", "error", "work", "runtime"), "author component result")
    keys(reference, ("schema", "status", "ref_root", "repository_provenance", "runtime", "sources_before", "sources_after",
                     "sources_unchanged", "execution_release", "catalog", "inputs", "baseline", "refinement", "oracles",
                     "faults", "checks", "budget", "exception", "traceback", "finalization_errors"), "reference component result")
    need(author["schema"] == "m194g-author-components-v1" and author["status"] == "PASS_AUTHOR_COMPONENTS"
         and author["scope"] == "components" and author["source_capture_error"] is None and author["error"] is None,
         "author complete component population uncommissioned")
    need(reference["schema"] == "m194g-independent-reference-components-v1" and reference["status"] == "PASS_REFERENCE_COMPONENTS_ONLY"
         and reference["ref_root"] == "repository" and reference["exception"] is None and reference["traceback"] is None
         and reference["finalization_errors"] == [] and reference["sources_unchanged"] is True,
         "independent complete reference component population uncommissioned")
    controls = verify_controls(reads, controls_path, controls_sha)
    author_root, reference_root = Path(author_path).resolve().parent, Path(reference_path).resolve().parent
    absolute_ref(reads, author["execution_release"], execution_path)
    need(author["execution_release"]["sha256"] == execution_sha, "author execution pin differs")
    reads.bound(REPO, reference["execution_release"])
    need(relative_path(REPO, reference["execution_release"]["path"]) == Path(execution_path).resolve()
         and reference["execution_release"]["sha256"] == execution_sha, "independent execution pin differs")
    absolute_ref(reads, author["catalog"], HERE / "component-population.json")
    need(author["catalog"]["sha256"] == CATALOG_SHA
         and author["inputs_sha256"] == hashlib.sha256(canonical(catalog) + b"\n").hexdigest(), "author catalog/input digest differs")
    reads.bound(REPO, reference["catalog"])
    need(reference["catalog"]["sha256"] == CATALOG_SHA
         and relative_path(REPO, reference["catalog"]["path"]) == HERE / "component-population.json", "reference catalog differs")
    for ref in reference["inputs"]:
        reads.bound(REPO, ref, limit=MAX_ARRAY + 4096)
    author_required = {"experiments/m194g-larger-pupil/" + name for name in
                       ("hybrid.py", "author-components.py", "pinned-loader.py", "geometry.py", "component-population.json")}
    author_required |= {"experiments/m194e-joint-pupil/model.py", "experiments/m194e-joint-pupil/render.py"}
    reference_required = {"experiments/m194g-larger-pupil/" + name for name in
                          ("independent-reference.py", "independent-reference-components.py", "component-population.json",
                           "fixture.json", "next-reference-plan.md", "next-numerical-release.md", "numerical-implementation-release-1.json")}
    reference_required.add("experiments/m194e-joint-pupil/independent-model.py")
    source_rows = {"author": source_closure(reads, author["sources_before"], author["sources_after"], author_root,
                                            ("sources-before", "sources-after"), author_required, release),
                   "reference": source_closure(reads, reference["sources_before"], reference["sources_after"], reference_root,
                                               ("source-snapshot",), reference_required, release)}
    check_invocation(author["invocation"], release, execution_sha, author_root, "author-components.py")
    check_invocation(reference["runtime"], release, execution_sha, reference_root, "independent-reference-components.py", reference=True)
    for runtime, key in ((author["runtime"], "thread_environment"), (reference["runtime"], "environment")):
        keys(runtime[key], ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"), "recorded thread environment")
        need(all(value == "2" for value in runtime[key].values()), "actual numerical thread setting differs")
    a_values, a_index = read_author_rows(reads, author, author_root, catalog)
    r_values, r_index = read_reference_values(reference, catalog)
    components = compare_component_values(catalog, a_values, r_values)
    faults = read_fault_values(a_index, reference, r_index, catalog)
    oracles = read_oracles(reads, reference, r_index, a_index, catalog)
    observers = read_observers(reads, author, author_root, catalog)
    need(type(author["checks"]) is list and author["checks"] and all(type(c) is dict and c["pass_"] is True for c in author["checks"]),
         "author deciding controls incomplete or failed")
    need(type(reference["checks"]) is list and reference["checks"] and all(type(c) is dict and c["passed"] is True for c in reference["checks"]),
         "reference deciding controls incomplete or failed")
    reads.finish()
    return {"schema": "m194g-independent-component-verification-v1", "status": "PASS_COMPONENTS_AND_OBSERVER_ONLY",
            "authority": "Fixed numerical components and small observer payload only; no all-image or CFA admission",
            "sources": source_rows, "private_controls": controls, "components": components,
            "faults": faults, "literal_oracles": oracles, "observer_frames": observers,
            "actual_author_work": author["work"], "actual_reference_work": reference["budget"],
            "input_bindings": reads.observed}


def main():
    parser = argparse.ArgumentParser()
    for name in ("author", "reference", "component-execution", "controls", "execution-release"):
        parser.add_argument("--" + name, type=Path, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    record = dict(schema="m194g-independent-component-reader-command-v1", status="UNCOMMISSIONED_COMPONENT_READER",
                  invocation=list(sys.orig_argv), started_utc=datetime.now(timezone.utc).isoformat(),
                  result=None, exception=None, traceback=None, inputs_unchanged=False)
    reads = Reads()
    try:
        release = read_execution(reads, args.execution_release, args.execution_release_sha256, scope="components", argv=sys.orig_argv)
        required = {str(path.resolve()): wanted for path, wanted in
                    ((args.author, args.author_sha256), (args.reference, args.reference_sha256),
                     (args.component_execution, args.component_execution_sha256), (args.controls, args.controls_sha256))}
        declared = {str(relative_path(REPO, ref["path"])): ref["sha256"] for ref in release["inputs"]}
        need(all(declared.get(path) == wanted for path, wanted in required.items()), "reader's externally pinned actual inputs not released")
        record["result"] = verify(args.author, args.author_sha256, args.reference, args.reference_sha256,
                                   args.component_execution, args.component_execution_sha256,
                                   args.controls, args.controls_sha256)
        reads.finish()
        record["inputs_unchanged"] = True
        record["status"] = "PASS_COMPONENTS_AND_OBSERVER_ONLY"
    except Exception as exc:
        record["exception"], record["traceback"] = repr(exc), traceback.format_exc()
    finally:
        record["wall_seconds"] = time.monotonic() - started
        record["entry_input_bindings"] = reads.observed
        (args.output / "result.json").write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": record["status"], "exception": record["exception"]}), flush=True)
    return 0 if record["status"] == "PASS_COMPONENTS_AND_OBSERVER_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
