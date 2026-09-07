"""Private, independently chosen M194g reader controls.

No optical result or authority is fabricated here. The command adapter and
actual resource controls are completed and frozen before any execution.
"""
from __future__ import annotations

import os
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import traceback
from types import SimpleNamespace

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


class Checks:
    def __init__(self):
        self.rows = []

    def check(self, name, function, refuses=False, expected=None):
        error = None
        error_type = None
        value = None
        try:
            value = function()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            error_type = type(exc).__name__
        if refuses and expected is None:
            patterns = {
                "payload-": r"scalar|branch|numerical indices|fallback diagnostic|nonnegative diagnostics|receipt value-indicator|same-method payload",
                "maximum-": r"numerical comparison bar failed",
                "rms-": r"numerical comparison bar failed",
                "single-maximum-": r"numerical comparison bar failed",
                "fault-power-": r"actual fixed fault lacks required power",
                "numeric-overflow-": r"nonfinite value difference",
                "numeric-bool-": r"finite real: value",
                "catalog-": r"required component population|duplicate/invalid|closed keys: normalized|finite real: reference scalar|numerical comparison bar failed",
                "json-": r"duplicate JSON key|nonfinite JSON token|nonfinite parsed JSON|top-level JSON object",
                "input-": r"record differs:",
                "actual-npy-": r"typed declared shape|integer: file length|declared dtype|closed keys: ArrayRef|relative child path|portable relative path|child resolves outside|actual NPY interpretation|exact bounded numeric NPY",
            }
            matches = [pattern for prefix, pattern in patterns.items() if name.startswith(prefix)]
            if len(matches) != 1:
                raise ValueError("every refusal control needs one explicit expected boundary: " + name)
            expected = ("ValueError", matches[0])
        passed = (error_type == expected[0] and re.search(expected[1], error or "") is not None) if refuses else (error is None)
        def recorded(item):
            if isinstance(item, np.ndarray):
                return dict(array_shape=list(item.shape), array_dtype=item.dtype.str,
                            array_payload_sha256=hashlib.sha256(item.tobytes()).hexdigest())
            if isinstance(item, np.generic):
                return item.item()
            if isinstance(item, bytes):
                return dict(bytes=len(item), sha256=hashlib.sha256(item).hexdigest())
            if isinstance(item, (list, tuple)):
                return [recorded(x) for x in item]
            if isinstance(item, dict):
                return {str(k): recorded(v) for k, v in item.items()}
            return item
        self.rows.append({"name": name, "passed": passed, "expected_refusal": refuses,
                          "expected_exception": None if expected is None else expected[0],
                          "expected_boundary": None if expected is None else expected[1],
                          "error": error, "value": recorded(value)})


def payload():
    # Different aspect ratio and two separated numerical rows, not author data.
    scalar = (9000.0 + np.arange(28, dtype=np.float64).reshape(4, 7) / 8).astype("<f8")
    branch = np.zeros((4, 7), dtype="u1")
    branch[1] = 1
    branch[2, 1:6] = 2
    branch[3, 0] = 2
    indices = np.flatnonzero(branch.ravel() == 2).astype("<u4")
    rows = np.empty((len(indices), 4), dtype="<f8")
    rows[:, 1] = np.arange(1, len(indices) + 1) / 2 ** 20
    rows[:, 2] = np.arange(2, len(indices) + 2) / 2 ** 21
    rows[:, 0] = rows[:, 1] + rows[:, 2]
    rows[:, 3] = np.arange(3, len(indices) + 3) / 2 ** 23
    return {"scalar": scalar, "branch": branch, "indices": indices, "diagnostics": rows}


def component_values(catalog):
    authors, references = [], []
    for index, case in enumerate(catalog["cases"]):
        # Arbitrary finite values commission the reader, never these optics.
        value = 10000.0 + index / 8
        for arm in case["author_arms"]:
            for method in case["author_methods"]:
                authors.append(dict(case_id=case["id"], arm=arm, method=method, value_e=value))
        for arm in case["reference_arms"]:
            references.append(dict(case_id=case["id"], arm=arm, value_e=value))
    return authors, references


def write_array(path, value):
    buffer = io.BytesIO()
    np.save(buffer, value, allow_pickle=False)
    data = buffer.getvalue()
    path.write_bytes(data)
    return dict(path=path.name, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                dtype=value.dtype.str, shape=list(value.shape))


def core_controls(reader, catalog, output):
    """Pure small reader fixtures. Run only after source/command release."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    checks = Checks()
    original = payload()
    checks.check("payload-valid-different-aspect", lambda: reader.validate_payload(**original))
    checks.check("payload-valid-memory-copy", lambda: reader.payload_equal(original, copy.deepcopy(original)))

    def mutate_array(name, edit, equality=False):
        changed = copy.deepcopy(original)
        edit(changed)
        checks.check(name, lambda: reader.payload_equal(original, changed) if equality
                     else reader.validate_payload(**changed), refuses=True)

    mutate_array("payload-scalar-plus-one-analytic", lambda x: x["scalar"].__setitem__((0, 0), x["scalar"][0, 0] + 1), True)
    mutate_array("payload-numerical-delta-plus-point01", lambda x: x["diagnostics"].__setitem__((0, 3), x["diagnostics"][0, 3] + .01), True)
    mutate_array("payload-missing-numerical-row", lambda x: (x.__setitem__("indices", x["indices"][1:].copy()), x.__setitem__("diagnostics", x["diagnostics"][1:].copy())))
    mutate_array("payload-analytic-extra-row", lambda x: (x.__setitem__("indices", np.concatenate([np.array([0], dtype="<u4"), x["indices"]])), x.__setitem__("diagnostics", np.vstack([x["diagnostics"][0], x["diagnostics"]]))))
    mutate_array("payload-duplicate-index", lambda x: x["indices"].__setitem__(1, x["indices"][0]))
    mutate_array("payload-unsorted-index", lambda x: x["indices"].__setitem__(slice(0, 2), x["indices"][:2][::-1]))
    mutate_array("payload-index-outside-frame", lambda x: x["indices"].__setitem__(-1, 28))
    mutate_array("payload-invalid-branch", lambda x: x["branch"].__setitem__((0, 0), 3))
    mutate_array("payload-missing-branch-site", lambda x: x["branch"].__setitem__((2, 1), 0))
    mutate_array("payload-scalar-nan", lambda x: x["scalar"].__setitem__((1, 2), np.nan))
    mutate_array("payload-scalar-inf", lambda x: x["scalar"].__setitem__((1, 2), np.inf))
    mutate_array("payload-negative-indicator", lambda x: x["diagnostics"].__setitem__((0, 3), -1.0))
    mutate_array("payload-nan-indicator", lambda x: x["diagnostics"].__setitem__((0, 2), np.nan))
    mutate_array("payload-swapped-sum-preserving-columns", lambda x: x["diagnostics"].__setitem__((slice(None), slice(1, 3)), x["diagnostics"][:, 1:3][:, ::-1]), True)
    mutate_array("payload-false-sum", lambda x: x["diagnostics"].__setitem__((0, 0), x["diagnostics"][0, 0] + .001))
    mutate_array("payload-wrong-scalar-endianness", lambda x: x.__setitem__("scalar", x["scalar"].astype(">f8")))
    mutate_array("payload-f32-scalar", lambda x: x.__setitem__("scalar", x["scalar"].astype("<f4")))
    mutate_array("payload-u64-indices", lambda x: x.__setitem__("indices", x["indices"].astype("<u8")))
    mutate_array("payload-wrong-diagnostic-shape", lambda x: x.__setitem__("diagnostics", x["diagnostics"][:, :3].copy()))
    checks.check("payload-restored-after-mutations", lambda: reader.payload_equal(original, payload()))

    # Threshold tests use zero references, avoiding ambiguous subtraction ulps.
    for label, value, refuses in (("below", .003999, False), ("equal", .004, False), ("above", .004001, True)):
        checks.check("maximum-" + label, lambda value=value: reader.comparison([value], [0.0], .004), refuses)
    checks.check("rms-equal", lambda: reader.comparison([.0008, -.0008], [0., 0.], .004, .0008))
    checks.check("rms-above-while-every-max-pass", lambda: reader.comparison([.000801] * 4, [0.] * 4, .004, .0008), True)
    checks.check("single-maximum-hidden-in-aggregate", lambda: reader.comparison([.004001] + [0.] * 99, [0.] * 100, .004, .0008), True)
    checks.check("fault-power-below", lambda: reader.fault_power(.003999, [0., 0.]), True)
    checks.check("fault-power-equality-is-not-power", lambda: reader.fault_power(.004, [0., 0.]), True)
    checks.check("fault-power-above", lambda: reader.fault_power(.004001, [0., 0.]))
    checks.check("fault-power-one-reference-only", lambda: reader.fault_power(.005, [0., .005]), True)
    checks.check("numeric-overflow-refuses", lambda: reader.comparison([1e308], [-1e308], .004), True)
    checks.check("numeric-bool-refuses", lambda: reader.comparison([True], [0.], .004), True)

    authors, references = component_values(catalog)
    checks.check("catalog-299-and300-valid-toy-values", lambda: reader.compare_component_values(catalog, authors, references))

    def mutate_rows(name, edit_author=None, edit_reference=None):
        a, r = copy.deepcopy(authors), copy.deepcopy(references)
        if edit_author:
            edit_author(a)
        if edit_reference:
            edit_reference(r)
        checks.check(name, lambda: reader.compare_component_values(catalog, a, r), True)

    mutate_rows("catalog-missing-author", lambda a: a.pop())
    mutate_rows("catalog-duplicate-replaces-author", lambda a: a.__setitem__(-1, copy.deepcopy(a[0])))
    mutate_rows("catalog-wrong-author-method", lambda a: a[0].__setitem__("method", "frozen-point"))
    mutate_rows("catalog-wrong-author-arm", lambda a: a[0].__setitem__("arm", "cell-refined"))
    mutate_rows("catalog-unknown-row-key", lambda a: a[0].__setitem__("accepted", True))
    mutate_rows("catalog-missing-reference-arm", edit_reference=lambda r: r.pop())
    mutate_rows("catalog-duplicate-reference-arm", edit_reference=lambda r: r.__setitem__(1, copy.deepcopy(r[0])))
    mutate_rows("catalog-nonfinite-reference", edit_reference=lambda r: r[0].__setitem__("value_e", np.nan))
    mutate_rows("catalog-reference-refinement-fails", edit_reference=lambda r: r[1].__setitem__("value_e", r[1]["value_e"] + .000501))
    mutate_rows("catalog-one-value-max-fails", lambda a: a[0].__setitem__("value_e", a[0]["value_e"] + .0041))

    def diluted_method(a):
        ids = reader.textured_ids(catalog)
        for row in a:
            if row["case_id"] in ids and row["arm"] == "primary" and row["method"] == "analytic-enabled":
                row["value_e"] += .000801

    mutate_rows("catalog-one-method-rms-cannot-be-diluted", diluted_method)
    checks.check("catalog-restored-reopened-toy-values", lambda: reader.compare_component_values(
        json.loads(json.dumps(catalog)), json.loads(json.dumps(authors)), json.loads(json.dumps(references))))

    checks.check("json-reopened-valid", lambda: reader.strict_json(b'{"a":[0,1,2],"x":0.5}'))
    for label, data in (("duplicate", b'{"a":1,"a":2}'), ("nan", b'{"a":NaN}'),
                        ("infinity", b'{"a":Infinity}'), ("overflow", b'{"a":1e999}'),
                        ("top-list", b'[]')):
        checks.check("json-" + label, lambda data=data: reader.strict_json(data), True)
    checks.check("input-tuple-json-normalizes", lambda: reader.equal_record({"xy": [1., 2.]}, {"xy": (1., 2.)}, "normalized input"))
    checks.check("input-bool-not-integer", lambda: reader.equal_record({"index": True}, {"index": 1}, "typed index"), True)
    checks.check("input-float-not-integer", lambda: reader.equal_record({"index": 1.0}, {"index": 1}, "typed index"), True)
    checks.check("input-changed-phase", lambda: reader.equal_record({"phase": .37}, {"phase": .38}, "phase"), True)

    array_dir = output / "arrays"
    array_dir.mkdir()
    ref = write_array(array_dir / "scalar.npy", original["scalar"])
    reads = reader.Reads()
    checks.check("actual-npy-valid", lambda: list(reads.array(array_dir, ref, "<f8", (4, 7))[0].shape))
    def reopened_payload():
        refs = {name: write_array(array_dir / (name + "-reopened.npy"), value)
                for name, value in original.items()}
        path = array_dir / "refs.json"
        path.write_text(json.dumps(refs), encoding="utf-8")
        reopened = reader.strict_json(path.read_bytes())
        actual = {name: reads.array(array_dir, reference, original[name].dtype.str, original[name].shape)[0]
                  for name, reference in reopened.items()}
        reader.payload_equal(original, actual)
    checks.check("actual-npy-all-four-reopened-byte-companion", reopened_payload)
    reads.finish()
    for label, changed in (
        ("float-shape", {**ref, "shape": [4.0, 7]}),
        ("bool-length", {**ref, "bytes": True}),
        ("wrong-declared-dtype", {**ref, "dtype": ">f8"}),
        ("unknown-ref-key", {**ref, "container": "npy"}),
        ("traversal", {**ref, "path": "../scalar.npy"}),
        ("absolute", {**ref, "path": str((array_dir / "scalar.npy").resolve())}),
    ):
        checks.check("actual-npy-" + label, lambda changed=changed: reader.Reads().array(array_dir, changed, "<f8", (4, 7)), True)
    wrong_endian = write_array(array_dir / "endian.npy", original["scalar"].astype(">f8"))
    wrong_endian["dtype"] = "<f8"
    checks.check("actual-npy-rehashed-wrong-endian", lambda: reader.Reads().array(array_dir, wrong_endian, "<f8", (4, 7)), True)
    wrong_shape = write_array(array_dir / "shape.npy", original["scalar"].reshape(7, 4))
    wrong_shape["shape"] = [4, 7]
    checks.check("actual-npy-rehashed-wrong-shape", lambda: reader.Reads().array(array_dir, wrong_shape, "<f8", (4, 7)), True)
    fortran = write_array(array_dir / "fortran.npy", np.asfortranarray(original["scalar"]))
    checks.check("actual-npy-rehashed-fortran", lambda: reader.Reads().array(array_dir, fortran, "<f8", (4, 7)), True)
    extra_path = array_dir / "trailing.npy"
    extra_path.write_bytes((array_dir / "scalar.npy").read_bytes() + b"\x00")
    extra = {**ref, "path": extra_path.name, "bytes": extra_path.stat().st_size,
             "sha256": hashlib.sha256(extra_path.read_bytes()).hexdigest()}
    checks.check("actual-npy-rehashed-trailing-byte", lambda: reader.Reads().array(array_dir, extra, "<f8", (4, 7)), True)
    checks.check("actual-npy-restored", lambda: list(reader.Reads().array(array_dir, ref, "<f8", (4, 7))[0].shape))
    return {"schema": "m194g-independent-component-private-controls-v1", "fixture_only": True,
            "status": "PASS_PRIVATE_CONTROLS" if all(r["passed"] for r in checks.rows) else "FAILED_PRIVATE_CONTROLS",
            "checks": checks.rows, "check_count": len(checks.rows)}


def resource_controls(author, reference, catalog):
    """Actual limiters with private clocks/buffers; no intended image run."""
    checks = Checks()
    clocks = SimpleNamespace(cpu=0.0, wall=0.0)
    fake_time = SimpleNamespace(process_time=lambda: clocks.cpu, monotonic=lambda: clocks.wall)
    saved_author_time = author.FALLBACK.time
    saved_reference_time = reference.m.time
    saved_reference_module_time = reference.time
    author.FALLBACK.time = reference.m.time = reference.time = fake_time

    def a_budget():
        return author.Budget("components", "count", started_cpu=0.0, started_wall=0.0)

    def r_budget():
        return reference.Budget(start_cpu=0.0, start_wall=0.0)

    def a_test(name, fn, refuses=False, boundary=""):
        checks.check(name, fn, refuses, ("NumericalFailure", boundary) if refuses else None)

    def r_test(name, fn, refuses=False, boundary=""):
        checks.check(name, fn, refuses, ("Refusal", boundary) if refuses else None)

    try:
        for axis, limit in (("cpu", 600.0), ("wall", 1200.0)):
            for label, value in (("below", limit - .001), ("equal", limit), ("above", limit + .001)):
                clocks.cpu = clocks.wall = 0.0
                a = a_budget()
                r = r_budget()
                setattr(clocks, axis, value)
                a_test("author-" + axis + "-" + label, a.check, label == "above", "own-process time ceiling")
                r_test("reference-" + axis + "-" + label, r.check, label == "above", "CPU budget|wall budget")
        clocks.cpu = clocks.wall = 0.0
        for charge, limit in (("points", 16000000), ("nodes", 2400000000), ("pairs", 32768)):
            for label, value in (("below", limit - 1), ("equal", limit), ("above", limit + 1)):
                a_test("author-" + charge + "-" + label,
                       lambda charge=charge, value=value: a_budget().check(**{charge: value}),
                       label == "above", "evaluation ceiling")
        for label, previous in (("below", 29999998), ("equal", 29999999), ("above", 30000000)):
            def tick(previous=previous):
                meter = r_budget()
                meter.evaluations = previous
                meter.tick(factor=True)
                return {"evaluations": meter.evaluations, "factor_evaluations": meter.factor_evaluations}
            r_test("reference-integrands-" + label, tick, label == "above", "independent evaluation budget")

        def aggregate_author(over=False):
            meter = a_budget()
            meter.check(points=8000000, nodes=1200000000)
            meter.new_frame()
            meter.observer("off")
            meter.bind(author.FALLBACK.integrator_for("angle-refined"))
            meter.observer("placebo")
            meter.new_frame()
            meter.observer("count")
            meter.bind(author.FALLBACK.integrator_for("cell-refined"))
            meter.check(points=8000000, nodes=1200000000)
            result = meter.receipt()
            if result["point_calls"] != 16000000 or result["angular_nodes"] != 2400000000:
                raise AssertionError("component work reset across bind/frame/observer")
            if over:
                meter.check(points=1)
            return result

        a_test("author-cumulative-work-survives-frames-methods-observers", aggregate_author)
        a_test("author-cumulative-one-more-refuses", lambda: aggregate_author(True), True, "evaluation ceiling")

        def analytic_clock(over=False):
            clocks.cpu = clocks.wall = 0.0
            meter = a_budget()
            case = next(c for c in catalog["cases"] if c["id"] == "transfer-small-full")
            scene, frame, _ = author.resolve_case(catalog, case)
            integrator = author.FALLBACK.integrator_for("primary")
            first, receipt = author.render_cell(scene, frame, case["native_xy"], integrator, meter)
            if receipt["branch"] != "foreground" or not receipt["transfer"]["waves"]:
                raise AssertionError("private actual analytic wave path not reached")
            if meter.receipt()["cumulative_point_calls"] != 0 or not meter.cache:
                raise AssertionError("private analytic cache witness differs")
            clocks.cpu = 600.001 if over else 600.0
            # Reusing the same full-layer factors must still check the clock.
            second, _ = author.render_cell(scene, frame, case["native_xy"], integrator, meter)
            if first != second:
                raise AssertionError("clock-only companion changed analytic value")
            return {"branch": receipt["branch"], "cache_entries": len(meter.cache), "value_e": first}

        a_test("author-actual-analytic-cache-clock-equality", analytic_clock)
        a_test("author-actual-analytic-cache-clock-crossing", lambda: analytic_clock(True), True, "own-process time ceiling")
        clocks.cpu = clocks.wall = 0.0

        def author_storage(over=False):
            meter = a_budget()
            meter.limits["arrays"] = 1024
            meter.base.config = meter.config_for(author.FALLBACK.integrator_for("primary"))
            first = np.empty(64, dtype="<f8")
            meter.watch(first, first[::2], first.reshape(8, 8))
            second = np.empty(64, dtype="<f8")
            meter.watch(second)
            if meter.receipt()["tracked_peak_ndarray_bytes"] != 1024:
                raise AssertionError("author aliases/distinct owners counted incorrectly")
            if over:
                third = np.empty(1, dtype="u1")
                meter.watch(third)
            return meter.receipt()["tracked_peak_ndarray_bytes"]

        a_test("author-live-owner-storage-equality", author_storage)
        a_test("author-live-owner-storage-one-byte-over", lambda: author_storage(True), True, "tracked ndarray byte ceiling")

        def reference_storage(over=False):
            meter = r_budget()
            if meter.max_array_bytes != 33554432:
                raise AssertionError("reference default32MiB storage limit differs")
            meter.max_array_bytes = 1024
            first = np.empty(64, dtype="<f8")
            meter.arrays(first, first[::2], first.reshape(8, 8))
            second = np.empty(64, dtype="<f8")
            meter.arrays(second)
            if meter.receipt()["peak_explicit_array_bytes"] != 1024:
                raise AssertionError("reference aliases/distinct owners counted incorrectly")
            if over:
                third = np.empty(1, dtype="u1")
                meter.arrays(third)
            return meter.receipt()["peak_explicit_array_bytes"]

        r_test("reference-live-owner-storage-equality", reference_storage)
        r_test("reference-live-owner-storage-one-byte-over", lambda: reference_storage(True), True, "independent explicit array budget")

        def scalar_retention(which, release):
            meter = a_budget() if which == "author" else r_budget()
            first = np.empty((3, 5), dtype="<f8")
            if which == "author":
                meter.frame(first)
            else:
                meter.arrays(first, scalar_frame=first)
            if release:
                del first
            second = np.empty((3, 5), dtype="<f8")
            if which == "author":
                meter.frame(second)
            else:
                meter.arrays(second, scalar_frame=second)

        a_test("author-second-live-scalar-refuses", lambda: scalar_retention("author", False), True, "more than one scalar frame retained")
        a_test("author-released-scalar-companion", lambda: scalar_retention("author", True))
        r_test("reference-second-live-scalar-refuses", lambda: scalar_retention("reference", False), True, "second live scalar reference frame")
        r_test("reference-released-scalar-companion", lambda: scalar_retention("reference", True))
    finally:
        author.FALLBACK.time = saved_author_time
        reference.m.time = saved_reference_time
        reference.time = saved_reference_module_time
    return {"schema": "m194g-independent-component-resource-controls-v1", "fixture_only": True,
            "status": "PASS_PRIVATE_CONTROLS" if all(r["passed"] for r in checks.rows) else "FAILED_PRIVATE_CONTROLS",
            "checks": checks.rows, "check_count": len(checks.rows)}


def entry_controls(reader, controller, hybrid, release, output):
    """Actual author authorization/finalization paths on clearly private inputs."""
    output = Path(output)
    output.mkdir()
    checks = Checks()
    private = copy.deepcopy(release)
    private["commands"] = [["private-entry-fixture", "ACTUAL_EXECUTION_RELEASE_SHA256"]]

    def attempt(record, name, *, argv=None, expected_override=None, check_closure=True):
        path = output / (name + ".json")
        raw = reader.canonical(record) + b"\n"
        path.write_bytes(raw)
        trusted = hashlib.sha256(raw).hexdigest()
        actual = ["private-entry-fixture", trusted] if argv is None else argv
        accepted, _ = controller.authorize(path, trusted if expected_override is None else expected_override,
                                           "components", argv=actual)
        if check_closure:
            controller.require_source_closure(hybrid, accepted, ("author-components.py",))
        return {"fixture_release_sha256": trusted, "source_count": len(accepted["source_bindings"])}

    checks.check("entry-valid-reopened-private-release", lambda: attempt(private, "valid"))
    boundaries = [
        ("schema", lambda r: r.__setitem__("schema", "m194g-numerical-execution-release-v0"), "schema/scope"),
        ("scope", lambda r: r.__setitem__("scope", "full-author-arm"), "schema/scope"),
        ("unknown-key", lambda r: r.__setitem__("admitted", True), "schema/scope"),
        ("source-bool-bytes", lambda r: next(iter(r["source_bindings"].values())).__setitem__("bytes", True), "typed source binding"),
        ("changed-source-hash", lambda r: next(iter(r["source_bindings"].values())).__setitem__("sha256", "0" * 64), "execution source mismatch"),
        ("omitted-loader", lambda r: r["source_bindings"].pop("experiments/m194g-larger-pupil/pinned-loader.py"), "omits an actual compiler/import input"),
        ("omitted-model", lambda r: r["source_bindings"].pop("experiments/m194e-joint-pupil/model.py"), "omits an actual compiler/import input"),
        ("omitted-controller", lambda r: r["source_bindings"].pop("experiments/m194g-larger-pupil/author-components.py"), "omits an actual compiler/import input"),
        ("duplicate-input", lambda r: r["inputs"].append(copy.deepcopy(r["inputs"][0])), "unique typed input binding"),
        ("changed-input-byte-count", lambda r: r["inputs"][0].__setitem__("bytes", r["inputs"][0]["bytes"] + 1), "execution input mismatch"),
    ]
    for name, change, boundary in boundaries:
        mutated = copy.deepcopy(private)
        change(mutated)
        checks.check("entry-rehashed-" + name, lambda mutated=mutated, name=name: attempt(mutated, name), True,
                     ("ValueError", boundary))
    checks.check("entry-unreleased-actual-argv", lambda: attempt(private, "argv", argv=["wrong-child"]), True,
                 ("ValueError", "actual orig_argv is not released"))
    checks.check("entry-wrong-external-release-pin", lambda: attempt(private, "pin", expected_override="0" * 64), True,
                 ("ValueError", "external execution release digest mismatch"))
    checks.check("entry-restored-private-release", lambda: attempt(private, "restored"))

    def preserve_original_and_capture():
        destination = output / "private-capture-refusal"
        saved = {key: getattr(controller, key) for key in ("authorize", "load_hybrid", "snapshot_sources")}
        called = []
        try:
            controller.authorize = lambda *args, **kw: (release, {"path": "PRIVATE_FIXTURE_ONLY", "sha256": "0" * 64, "bytes": 0})
            controller.load_hybrid = lambda *args, **kw: hybrid
            def fail_snapshot(h, bound, path, name):
                called.append(name)
                if name == "sources-before":
                    raise RuntimeError("independent-original-before-numerics")
                raise RuntimeError("independent-secondary-final-capture")
            controller.snapshot_sources = fail_snapshot
            code = controller.run(SimpleNamespace(output=str(destination), execution_release="PRIVATE_FIXTURE_ONLY",
                                                 execution_release_sha256="0" * 64))
        finally:
            for key, value in saved.items():
                setattr(controller, key, value)
        result = reader.strict_json((destination / "result.json").read_bytes())
        if not (code == 1 and result["status"] == "UNCOMMISSIONED_NUMERICS" and result["rows"] == []
                and result["observer_executions"] == [] and "independent-original-before-numerics" in result["error"]
                and "independent-secondary-final-capture" in result["source_capture_error"]
                and called == ["sources-before", "sources-after"]):
            raise AssertionError("actual run did not preserve primary and secondary refusal before numerical work")
        return {"exit_code": code, "status": result["status"], "actual_rows": len(result["rows"]), "snapshot_calls": called}

    checks.check("entry-actual-run-preserves-primary-and-secondary-errors", preserve_original_and_capture)
    return {"schema": "m194g-independent-component-entry-controls-v1", "fixture_only": True,
            "status": "PASS_PRIVATE_CONTROLS" if all(r["passed"] for r in checks.rows) else "FAILED_PRIVATE_CONTROLS",
            "checks": checks.rows, "check_count": len(checks.rows)}


def author_fixture_controls(reader, reference_module, catalog, path, trusted, output):
    """Real author payloads, private mutations; no successful reference invented."""
    output = Path(output)
    output.mkdir()
    reads, checks = reader.Reads(), Checks()
    author = reads.external(path, trusted)
    root = Path(path).resolve().parent
    if author["status"] != "PASS_AUTHOR_COMPONENTS":
        raise ValueError("externally pinned completed author fixture required")
    checks.check("actual-author-all331-persisted-call-rows", lambda: len(reader.read_author_rows(reads, author, root, catalog)[0]))
    checks.check("actual-author-all60-observer-frames", lambda: reader.read_observers(reads, author, root, catalog))
    source_digest = hashlib.sha256(reader.canonical(author["sources_before"]) + b"\n").hexdigest()
    ref = next(f["receipt"] for f in author["observer_executions"][0]["frames"]
               if f["arm"] == "primary" and f["frame_index"] == 2)
    original_path = reader.relative_path(root, ref["path"])
    original = reads.external(original_path, ref["sha256"])
    inputs = reader.observer_inputs(catalog, "primary", 2)

    def frame_attempt(name, change=None):
        directory = output / name
        directory.mkdir()
        row = copy.deepcopy(original)
        for array_ref in row["arrays"].values():
            data = reads.bound(original_path.parent, array_ref, array=True)
            (directory / array_ref["path"]).write_bytes(data)
        if change is not None:
            change(row)
        raw = reader.canonical(row) + b"\n"
        dest = directory / "receipt.json"
        dest.write_bytes(raw)
        result = reader.author_frame(reader.Reads(), dest, hashlib.sha256(raw).hexdigest(), inputs, source_digest)
        return result[3]

    checks.check("actual-author-private-relocated-frame-companion", lambda: frame_attempt("valid"))
    for name, change, boundary in (
        ("unknown-schema", lambda r: r.__setitem__("schema", "m194e-author-frame-v1"), "frame status/schema"),
        ("unknown-field", lambda r: r.__setitem__("accepted", True), "closed keys: author frame receipt"),
        ("missing-status", lambda r: r.pop("status"), "closed keys: author frame receipt"),
        ("nonterminal", lambda r: r.__setitem__("status", "RUNNING"), "frame status/schema"),
        ("changed-source-digest", lambda r: r.__setitem__("source_set_sha256", "0" * 64), "frame exercised-source digest"),
        ("bool-branch-code", lambda r: r["branch_codes"].__setitem__("background", True), "record differs: branch code map"),
        ("float-branch-code", lambda r: r["branch_codes"].__setitem__("foreground", 0.0), "record differs: branch code map"),
        ("float-completed", lambda r: r.__setitem__("completed_cells", 54.0), "integer: completed cells"),
        ("bool-frame-index", lambda r: r["inputs"]["frame"].__setitem__("index", True), "record differs: actual observer inputs"),
        ("changed-phase", lambda r: r["inputs"]["scene"]["foreground"]["waves"][0].__setitem__("phase", .8), "record differs: actual observer inputs"),
        ("changed-arm", lambda r: r["inputs"].__setitem__("arm", "angle-refined"), "record differs: actual observer inputs"),
        ("false-traversal-digest", lambda r: r.__setitem__("traversal_sha256", "0" * 64), "actual traversal witness"),
        ("duplicated-array-path", lambda r: r["arrays"]["branch"].__setitem__("path", r["arrays"]["scalar"]["path"]), "distinct frame payload paths"),
        ("unknown-diagnostic-column", lambda r: r["diagnostic_columns"].__setitem__(3, "signed_delta_e"), "record differs: diagnostic columns"),
        ("false-cumulative-work", lambda r: r["work_after"].__setitem__("point_calls", 0), "component cumulative work bound"),
    ):
        checks.check("actual-author-rehashed-" + name, lambda name=name, change=change: frame_attempt(name, change),
                     True, ("ValueError", boundary))
    checks.check("actual-author-private-frame-restored", lambda: frame_attempt("restored"))

    def missing_observer():
        changed = copy.deepcopy(author)
        changed["observer_executions"].pop()
        reader.read_observers(reads, changed, root, catalog)
    checks.check("actual-author-missing-observer-execution", missing_observer, True,
                 ("ValueError", "all four observer executions required"))
    def duplicated_frame():
        changed = copy.deepcopy(author)
        changed["observer_executions"][0]["frames"][1] = copy.deepcopy(changed["observer_executions"][0]["frames"][0])
        reader.read_observers(reads, changed, root, catalog)
    checks.check("actual-author-duplicate-frame-replaces-required-frame", duplicated_frame, True,
                 ("ValueError", "fixed observer frame/arm order differs"))

    # Actual independently authored NPY reader, not only the new verifier's one.
    reference_dir = output / "private-reference-array"
    reference_dir.mkdir()
    good = np.arange(15, dtype="<f8").reshape(3, 5)
    ref = write_array(reference_dir / "valid.npy", good)
    ref["path"] = (reference_dir / "valid.npy").resolve().relative_to(REPO).as_posix()
    checks.check("actual-reference-bounded-array-valid", lambda: reference_module.read_array(ref, (3, 5), "<f8", reference_module.Budget()))
    buffer = io.BytesIO()
    np.lib.format.write_array_header_1_0(buffer, dict(descr="<f8", fortran_order=False, shape=(2147483647, 2147483647)))
    buffer.write(good.tobytes())
    raw = buffer.getvalue()
    huge = reference_dir / "huge-header-tiny-payload.npy"
    huge.write_bytes(raw)
    huge_ref = dict(path=huge.resolve().relative_to(REPO).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    checks.check("actual-reference-rehashed-huge-header-before-allocation", lambda: reference_module.read_array(huge_ref, (3, 5), "<f8", reference_module.Budget()),
                 True, ("Refusal", "bounded NPY header/extent mismatch"))
    checks.check("actual-reference-bounded-array-restored", lambda: reference_module.read_array(ref, (3, 5), "<f8", reference_module.Budget()))
    reads.finish()
    return checks.rows


def reference_fixture_controls(reader, catalog, path, trusted, output, release):
    """Actual v2 reference rows, private rehashed metadata, no invented values."""
    output = Path(output)
    output.mkdir()
    reads, checks = reader.Reads(), Checks()
    reference = reads.external(path, trusted)
    if reference.get("schema") != "m194g-independent-reference-components-v1" or reference.get("status") != "PASS_REFERENCE_COMPONENTS_ONLY":
        raise ValueError("externally pinned completed v2 reference fixture required")
    root = Path(path).resolve().parent
    checks.check("actual-reference-v2-all300-returned-rows",
                 lambda: len(reader.read_reference_values(reference, catalog)[0]))
    companions = (("geometry-060", "primary"), ("geometry-060", "refined"),
                  ("transfer-small-full", "primary"), ("joint-relative-sign-point", "refined"))
    selected = {}
    for case_id, arm in companions:
        rows = [row for row in reference["baseline"] if (row["case_id"], row["arm"]) == (case_id, arm)]
        reader.need(len(rows) == 1, "fixed actual v2 metadata companion absent or duplicated")
        selected[(case_id, arm)] = rows[0]

    def attempt(name, change=None, *, key=("geometry-060", "refined")):
        row = copy.deepcopy(selected[key])
        if change is not None:
            change(row)
        # Persist and hash a private metadata fixture, then reopen it. This is
        # not a rewritten successful reference result or numerical authority.
        raw = reader.canonical({"schema": "m194g-private-reference-row-fixture-v1",
                                "fixture_only": True, "row": row}) + b"\n"
        dest = output / (name + ".json")
        dest.write_bytes(raw)
        reopened = reads.external(dest, hashlib.sha256(raw).hexdigest())
        verified = reader.reference_row(reopened["row"], catalog, case_id=key[0], arm=key[1])
        return {"case_id": key[0], "arm": key[1], "branch": verified["branch"],
                "value_e": verified["value_e"], "normalization": verified["receipt"]["normalization"]}

    for key in companions:
        name = "actual-reference-v2-valid-" + key[0] + "-" + key[1]
        checks.check(name, lambda name=name, key=key: attempt(name, key=key))

    def chord_delta(row):
        row["work_after"]["chord_evaluations"] += 1
        row["work_after"]["evaluations"] += 1

    def coherent_work(row, intervals, calls):
        row["receipt"]["normalization"]["intervals"] = intervals
        row["receipt"]["normalization"]["integrand_calls"] = calls
        for field, count in (("intervals", intervals), ("integrand_calls", calls)):
            row["engine_after"]["normalization"][field] = row["engine_before"]["normalization"][field] + count
        row["work_after"]["chord_evaluations"] = row["work_before"]["chord_evaluations"] + calls
        row["work_after"]["evaluations"] = row["work_after"]["factor_evaluations"] + row["work_after"]["chord_evaluations"]

    mutations = (
        ("row-method-v1", lambda r: r.__setitem__("method", "m194g-independent-spatial-cache-v1"), "reference row identity"),
        ("engine-method-v1", lambda r: r["engine_after"].__setitem__("method", "m194g-independent-spatial-cache-v1"), "actual independent method/target"),
        ("returned-integrand-method", lambda r: r["receipt"].__setitem__("method", reader.REFERENCE_METHOD), "returned reference integrand method"),
        ("missing-row-normalization", lambda r: r["receipt"].pop("normalization"), "reference normalization receipt absent"),
        ("missing-engine-normalization", lambda r: r["engine_before"].pop("normalization"), "closed keys: independent engine receipt"),
        ("unknown-normalization-field", lambda r: r["receipt"]["normalization"].__setitem__("accepted", True), "closed keys: reference normalization"),
        ("missing-normalization-field", lambda r: r["receipt"]["normalization"].pop("request"), "closed keys: reference normalization"),
        ("adapter-v0", lambda r: r["receipt"]["normalization"].__setitem__("adapter", "cartesian-unit-interval-v0"), "record differs: normalization convention"),
        ("mapping", lambda r: r["receipt"]["normalization"].__setitem__("mapping", "midpoint"), "record differs: normalization convention"),
        ("jacobian", lambda r: r["receipt"]["normalization"].__setitem__("jacobian", "outside-return-value"), "record differs: normalization convention"),
        ("request-convention", lambda r: r["receipt"]["normalization"].__setitem__("request", "epsabs-divided-by-width"), "record differs: normalization convention"),
        ("target-bool", lambda r: r["receipt"]["normalization"].__setitem__("target_e", True), "finite real: normalization actual target"),
        ("target-other-arm", lambda r: r["receipt"]["normalization"].__setitem__("target_e", .000125), "normalization actual target differs"),
        ("row-count-bool", lambda r: r["receipt"]["normalization"].__setitem__("intervals", True), "integer: normalization intervals"),
        ("row-count-float", lambda r: r["receipt"]["normalization"].__setitem__("integrand_calls", float(r["receipt"]["normalization"]["integrand_calls"])), "integer: normalization integrand calls"),
        ("engine-count-bool", lambda r: r["engine_before"]["normalization"].__setitem__("integrand_calls", False), "integer: normalization integrand calls"),
        ("engine-count-float", lambda r: r["engine_after"]["normalization"].__setitem__("intervals", float(r["engine_after"]["normalization"]["intervals"])), "integer: normalization intervals"),
        ("count-negative", lambda r: r["receipt"]["normalization"].__setitem__("integrand_calls", -1), "integer: normalization integrand calls"),
        ("counter-decreases", lambda r: r["engine_before"]["normalization"].__setitem__("intervals", r["engine_after"]["normalization"]["intervals"] + 1), "reference normalization counters decreased"),
        ("row-engine-delta", lambda r: r["receipt"]["normalization"].__setitem__("integrand_calls", r["receipt"]["normalization"]["integrand_calls"] + 1), "reference row normalization differs from engine delta"),
        ("chord-delta", chord_delta, "reference normalization differs from chord work"),
        ("frozen-interval-count", lambda r: r["receipt"].__setitem__("intervals", r["receipt"]["intervals"] + 1), "reference normalization differs from frozen interval count"),
        ("frozen-interval-float", lambda r: r["receipt"].__setitem__("intervals", float(r["receipt"]["intervals"])), "integer: frozen interval count"),
        ("actual-request", lambda r: r["receipt"].__setitem__("request_e", .000125), "reference receipt actual target differs"),
        ("coherent-zero-numerical-work", lambda r: coherent_work(r, 0, 0), "returned numerical reference lacks normalization work"),
    )
    for suffix, change, boundary in mutations:
        name = "actual-reference-v2-" + suffix
        checks.check(name, lambda name=name, change=change: attempt(name, change),
                     True, ("ValueError", boundary))
    checks.check("actual-reference-v2-analytic-coherent-positive-work",
                 lambda: attempt("analytic-coherent-positive-work", lambda r: coherent_work(r, 1, 21),
                                 key=("transfer-small-full", "primary")),
                 True, ("ValueError", "analytic reference must have zero normalization work"))
    checks.check("actual-reference-v2-analytic-returned-method-v1",
                 lambda: attempt("analytic-returned-method-v1", lambda r: r["receipt"].__setitem__("method", "m194g-independent-spatial-cache-v1"),
                                 key=("transfer-small-full", "primary")),
                 True, ("ValueError", "returned analytic reference method differs"))
    checks.check("actual-reference-v2-restored-numerical", lambda: attempt("restored-numerical"))
    checks.check("actual-reference-v2-restored-analytic",
                 lambda: attempt("restored-analytic", key=("transfer-small-full", "primary")))

    required = {"experiments/m194g-larger-pupil/" + name for name in
                ("independent-normalized-interval.py", "independent-normalized-interval-controls.py",
                 "reference-interval-amendment-1.md")}
    adapter_name = "experiments/m194g-larger-pupil/independent-normalized-interval.py"

    def source_attempt(*, omit_exercised=False, omit_released=False):
        before, after, private_release = (copy.deepcopy(reference["sources_before"]),
                                          copy.deepcopy(reference["sources_after"]), copy.deepcopy(release))
        if omit_exercised:
            before.pop(adapter_name)
            after.pop(adapter_name)
        if omit_released:
            private_release["source_bindings"].pop(adapter_name)
        return reader.source_closure(reads, before, after, root, ("source-snapshot",), required, private_release)

    checks.check("actual-reference-v2-source-closure-valid", source_attempt)
    checks.check("actual-reference-v2-omitted-adapter-exercised",
                 lambda: source_attempt(omit_exercised=True), True,
                 ("ValueError", "exercised source closure omits actual dependency"))
    checks.check("actual-reference-v2-omitted-adapter-release",
                 lambda: source_attempt(omit_released=True), True,
                 ("ValueError", "entry release omits exercised dependency"))
    checks.check("actual-reference-v2-source-closure-restored", source_attempt)

    def interval_attempt(name, change=None):
        # The externally pinned result embeds these actual direct-call records.
        # A rehashed private envelope tests their interpretation, not authority.
        fixture = {"checks": copy.deepcopy(reference["checks"])}
        if change is not None:
            change(fixture)
        raw = reader.canonical({"schema": "m194g-private-normalization-evidence-v1",
                                "fixture_only": True, "record": fixture}) + b"\n"
        destination = output / ("normalization-" + name + ".json")
        destination.write_bytes(raw)
        reopened = reads.external(destination, hashlib.sha256(raw).hexdigest())
        return reader.read_normalization_evidence(reopened["record"])

    def interval_case(fixture, group="jacobian-faults"):
        return next(x for x in fixture["checks"] if x["name"] == "normalized-interval-" + group)["evidence"]["cases"][0]

    def erase_scalar_fault(fixture):
        case = interval_case(fixture)
        case["active"]["value"] = float(reader.Fraction(case["active"]["oracle_fraction"]))

    def erase_request_fault(fixture):
        case = interval_case(fixture, "request-faults")
        case["active"]["delegated"][0]["kwargs"]["epsabs"] = case["active"]["request"]

    checks.check("actual-normalization-evidence-valid", lambda: interval_attempt("valid"))
    for suffix, change, boundary in (
        ("scalar-fault-inert", erase_scalar_fault, "normalization actual scalar fault not powered"),
        ("request-fault-inert", erase_request_fault, "normalization actual request fault not powered"),
        ("relaxed-error-limit", lambda f: interval_case(f)["active"].__setitem__("error_limit", 1.), "record differs: normalization fixed request/error limit"),
        ("false-oracle", lambda f: interval_case(f)["active"].__setitem__("oracle_fraction", "0"), "normalization independent polynomial oracle"),
        ("zero-callbacks", lambda f: interval_case(f)["active"].__setitem__("delegated_callbacks", 0), "integer: normalization actual callbacks"),
        ("unrelated-exception", lambda f: interval_case(f)["active"].__setitem__("exception", "TypeError('private fixture')"), "normalization direct unexpected exception"),
        ("false-fault-magnitude", lambda f: interval_case(f).__setitem__("actual_scalar_error_fraction", "0"), "normalization recorded actual fault magnitude"),
        ("restoration-changed", lambda f: interval_case(f)["restored"].__setitem__("value", interval_case(f)["restored"]["value"] + 1.), "normalization actual direct polynomial error/indicator"),
    ):
        checks.check("actual-normalization-evidence-" + suffix,
                     lambda suffix=suffix, change=change: interval_attempt(suffix, change),
                     True, ("ValueError", boundary))
    checks.check("actual-normalization-evidence-restored", lambda: interval_attempt("restored"))
    reads.finish()
    return checks.rows


def top_level_verify_controls(reader, author_path, author_sha, reference_path, reference_sha, release):
    """Actual verify entry; stop at its controls dependency, not a fake PASS."""
    checks, reads = Checks(), reader.Reads()
    author = reads.external(author_path, author_sha)
    numerical = author["execution_release"]
    numerical_path = Path(numerical["path"]).resolve()
    reader.need(any(reader.relative_path(REPO, item["path"]) == numerical_path
                    and item["sha256"] == numerical["sha256"] and item["bytes"] == numerical["bytes"]
                    for item in release["inputs"]), "top-level numerical release is not an explicit input")
    amendment_path = (HERE / "reference-interval-amendment-1.md").resolve()

    class ReachedControlsBoundary(RuntimeError):
        pass

    def attempt(*, bad_pin=False, old_json_choice=False):
        saved_pin = reader.INTERVAL_AMENDMENT_SHA
        saved_controls = reader.verify_controls
        saved_bytes = reader.Reads.bytes
        observed = {}

        def boundary(actual_reads, path, trusted):
            expected = {str(amendment_path): saved_pin,
                        str(Path(author_path).resolve()): author_sha,
                        str(Path(reference_path).resolve()): reference_sha}
            reader.need(all(actual_reads.observed.get(path, {}).get("sha256") == sha
                            for path, sha in expected.items()), "actual verify did not read its complete entry inputs")
            observed.update({path: actual_reads.observed[path] for path in expected})
            actual_reads.finish()
            raise ReachedControlsBoundary("actual verify reached controls after pinned Markdown and result reads")

        def regress_json(actual_reads, path, trusted, *args, **kwargs):
            data = saved_bytes(actual_reads, path, trusted, *args, **kwargs)
            # Target verify's explicit byte-pin call, not the release's earlier
            # length-bound source/input checks or final ledger rechecks.
            if Path(path).resolve() == amendment_path and not args and not kwargs:
                reader.strict_json(data)
            return data

        try:
            reader.verify_controls = boundary
            if bad_pin:
                reader.INTERVAL_AMENDMENT_SHA = "0" * 64
            if old_json_choice:
                reader.Reads.bytes = regress_json
            try:
                reader.verify(author_path, author_sha, reference_path, reference_sha,
                              numerical_path, numerical["sha256"], "PRIVATE_UNREACHED_CONTROLS", "0" * 64)
            except ReachedControlsBoundary:
                return {"fixture_only": True, "reached": "verify_controls",
                        "numerical_comparison_executed": False, "actual_entry_inputs": observed}
            raise AssertionError("actual verify returned without the required private boundary")
        finally:
            reader.INTERVAL_AMENDMENT_SHA = saved_pin
            reader.verify_controls = saved_controls
            reader.Reads.bytes = saved_bytes

    checks.check("actual-verify-entry-pinned-markdown-and-results", attempt)
    checks.check("actual-verify-entry-wrong-amendment-pin", lambda: attempt(bad_pin=True),
                 True, ("ValueError", "actual file hash/length differs"))
    checks.check("actual-verify-entry-old-json-choice", lambda: attempt(old_json_choice=True),
                 True, ("JSONDecodeError", "Expecting value"))
    checks.check("actual-verify-entry-restored", attempt)
    reads.finish()
    return checks.rows


def load_checked_module(path, wanted, name):
    path = Path(path).resolve()
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != wanted["sha256"] or len(raw) != wanted["bytes"]:
        raise ValueError("released module bytes differ: " + str(path))
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execution-release", type=Path, required=True)
    parser.add_argument("--execution-release-sha256", required=True)
    parser.add_argument("--author-fixture", type=Path, required=True)
    parser.add_argument("--author-fixture-sha256", required=True)
    parser.add_argument("--reference-fixture", type=Path, required=True)
    parser.add_argument("--reference-fixture-sha256", required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-independent-component-controls-command-v1", fixture_only=True,
                  status="UNCOMMISSIONED_PRIVATE_CONTROLS", invocation=list(sys.orig_argv),
                  command=list(sys.argv), executable=sys.executable, xoptions=dict(sys._xoptions),
                  source_bindings=None, input_bindings=None, groups=[], exception=None, traceback=None,
                  finalization_error=None, sources_unchanged=False, runtime=None)
    reads = None
    try:
        with args.execution_release.open("rb") as stream:
            raw = stream.read(16 * 1024 * 1024 + 1)
        if len(raw) > 16 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != args.execution_release_sha256:
            raise ValueError("external private execution release differs")
        # Bootstrap only the reader from externally bound exact bytes. Its strict
        # parser then validates the full release before any numerical imports.
        boot = json.loads(raw)
        relative_reader = "experiments/m194g-larger-pupil/independent-component-reader.py"
        reader = load_checked_module(REPO / relative_reader, boot["source_bindings"][relative_reader], "m194g_private_reader")
        reads = reader.Reads()
        release = reader.read_execution(reads, args.execution_release, args.execution_release_sha256,
                                        scope="components", argv=sys.orig_argv)
        self_name = Path(__file__).resolve().relative_to(REPO).as_posix()
        if self_name not in release["source_bindings"]:
            raise ValueError("actual private controller omitted from release")
        sources = release["source_bindings"]
        result["source_bindings"] = sources
        for name, ref in sources.items():
            destination = args.output / "source-snapshot" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(reads.bound(REPO, {"path": name, **ref}))
        catalog = reads.external(HERE / "component-population.json", reader.CATALOG_SHA)
        result["groups"].append(core_controls(reader, catalog, args.output / "reader-fixtures"))
        modules = {}
        for filename, name in (("hybrid.py", "m194g_private_hybrid"),
                               ("independent-reference.py", "m194g_private_reference"),
                               ("author-components.py", "m194g_private_author_controller")):
            relative = "experiments/m194g-larger-pupil/" + filename
            modules[filename] = load_checked_module(REPO / relative, sources[relative], name)
        if not any((REPO / item["path"]).resolve() == args.author_fixture.resolve()
                   and item["sha256"] == args.author_fixture_sha256 for item in release["inputs"]):
            raise ValueError("actual author fixture must be an explicitly pinned release input")
        actual = author_fixture_controls(reader, modules["independent-reference.py"], catalog,
                                         args.author_fixture, args.author_fixture_sha256, args.output / "actual-author-fixtures")
        if not any((REPO / item["path"]).resolve() == args.reference_fixture.resolve()
                   and item["sha256"] == args.reference_fixture_sha256 for item in release["inputs"]):
            raise ValueError("actual reference fixture must be an explicitly pinned release input")
        actual.extend(reference_fixture_controls(reader, catalog, args.reference_fixture, args.reference_fixture_sha256,
                                                  args.output / "actual-reference-fixtures", release))
        actual.extend(top_level_verify_controls(reader, args.author_fixture, args.author_fixture_sha256,
                                                 args.reference_fixture, args.reference_fixture_sha256, release))
        core = result["groups"][0]
        core["checks"].extend(actual)
        core["check_count"] = len(core["checks"])
        core["status"] = "PASS_PRIVATE_CONTROLS" if all(row["passed"] for row in core["checks"]) else "FAILED_PRIVATE_CONTROLS"
        result["groups"].append(resource_controls(modules["hybrid.py"], modules["independent-reference.py"], catalog))
        result["groups"].append(entry_controls(reader, modules["author-components.py"], modules["hybrid.py"], release,
                                               args.output / "entry-fixtures"))
        if all(group["status"] == "PASS_PRIVATE_CONTROLS" for group in result["groups"]):
            result["status"] = "PASS_PRIVATE_COMPONENT_CONTROLS"
    except Exception as exc:
        result["exception"], result["traceback"] = repr(exc), traceback.format_exc()
    finally:
        if reads is not None:
            try:
                reads.finish()
                result["sources_unchanged"] = True
            except Exception as exc:
                result["finalization_error"] = repr(exc)
                result["status"] = "UNCOMMISSIONED_PRIVATE_CONTROLS"
            result["input_bindings"] = reads.observed
        result["runtime"] = dict(cpu_seconds=time.process_time() - ENTRY_CPU,
                                 wall_seconds=time.monotonic() - ENTRY_WALL,
                                 python=sys.version, numpy=np.__version__,
                                 thread_environment={k: os.environ.get(k) for k in
                                                     ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        result["check_count"] = sum(group["check_count"] for group in result["groups"])
        (args.output / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "checks": result["check_count"]}), flush=True)
    return 0 if result["status"] == "PASS_PRIVATE_COMPONENT_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
