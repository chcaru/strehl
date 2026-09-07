"""Independent complete M194g expected-array reader; no optical imports/calls."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import traceback
import weakref

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
FIXTURE_SHA = "e84f0bbbda9bef039da86616c9f051d416929f4dbe78477cc5b3fc21206856bb"
ROLES = ("author-primary", "author-angle-refined", "author-cell-refined", "reference-primary", "reference-refined")
THREADS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")
for _name in THREADS:
    os.environ[_name] = "2"
C = np = None


def need(ok, message):
    if not ok:
        raise ValueError(message)


class Budget:
    def __init__(self, *, started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL,
                 cpu_clock=time.process_time, wall_clock=time.monotonic,
                 cpu_limit=120., wall_limit=240., array_limit=32*1024*1024):
        self.started_cpu, self.started_wall = started_cpu, started_wall
        self.cpu_clock, self.wall_clock = cpu_clock, wall_clock
        self.cpu_limit, self.wall_limit, self.array_limit = cpu_limit, wall_limit, array_limit
        self.owners, self.peak, self.checks = {}, 0, 0
        self.check()

    def check(self):
        self.checks += 1
        need(self.cpu_clock()-self.started_cpu <= self.cpu_limit, "full reader CPU budget")
        need(self.wall_clock()-self.started_wall <= self.wall_limit, "full reader wall budget")

    def watch(self, *arrays):
        for value in arrays:
            need(type(value) is np.ndarray, "reader named array required")
            owner = value
            while isinstance(owner.base, np.ndarray):
                owner = owner.base
            self.owners[id(owner)] = (weakref.ref(owner), owner.nbytes)
        self.owners = {k: v for k, v in self.owners.items() if v[0]() is not None}
        self.peak = max(self.peak, sum(v[1] for v in self.owners.values()))
        need(self.peak <= self.array_limit, "full reader named-array budget")
        self.check()

    def receipt(self):
        return dict(cpu_seconds=self.cpu_clock()-self.started_cpu, wall_seconds=self.wall_clock()-self.started_wall,
                    tracked_peak_named_array_bytes=self.peak, check_calls=self.checks,
                    limits=dict(cpu_seconds=self.cpu_limit, wall_seconds=self.wall_limit, named_array_bytes=self.array_limit),
                    scope="live unique ndarray backings; not process RSS")


def configure(module):
    global C, np
    C, np = module, module.np


def bootstrap(path, trusted, scope, argv):
    """Stdlib-only exact-byte bootstrap; no producer module is loaded."""
    with Path(path).open("rb") as stream:
        raw = stream.read(16*1024*1024+1)
    need(len(raw) <= 16*1024*1024 and hashlib.sha256(raw).hexdigest() == trusted, "full reader external release pin")
    boot = json.loads(raw)
    name = "experiments/m194g-larger-pupil/independent-component-reader.py"
    source = (REPO/name).read_bytes()
    wanted = boot["source_bindings"][name]
    need(dict(sha256=hashlib.sha256(source).hexdigest(), bytes=len(source)) == wanted, "full reader reused source pin")
    spec = importlib.util.spec_from_loader("m194g_full_reused_reader", loader=None, origin=str(REPO/name))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(REPO/name)
    sys.modules[spec.name] = module
    exec(compile(source, str(REPO/name), "exec"), module.__dict__)
    configure(module)
    reads = C.Reads()
    release = C.read_execution(reads, path, trusted, scope=scope, argv=argv)
    own = Path(__file__).resolve().relative_to(REPO).as_posix()
    need(own in release["source_bindings"], "full reader source absent from release")
    reads.finish()
    return release


def make_reads(budget):
    class FullReads(C.Reads):
        def bytes(self, *args, **kwargs):
            budget.check()
            data = super().bytes(*args, **kwargs)
            budget.check()
            return data

        def array(self, *args, **kwargs):
            value, raw = super().array(*args, **kwargs)
            budget.watch(value)
            return value, raw
    return FullReads()


def file_ref(reads, path):
    path = Path(path).resolve()
    need(path.is_relative_to(REPO), "reference outside repository")
    ref = reads.observed[str(path)]
    return dict(path=path.relative_to(REPO).as_posix(), **ref)


def repo_ref(parent, ref):
    path = C.relative_path(parent, ref["path"])
    need(path.is_relative_to(REPO), "array/receipt outside repository")
    return {**ref, "path": path.relative_to(REPO).as_posix()}


def distinct_refs(root, refs):
    paths, identities = set(), set()
    for ref in refs:
        path = C.relative_path(root, ref["path"])
        spelling = str(path).casefold()
        stat = path.stat()
        identity = (stat.st_dev, stat.st_ino)
        need(spelling not in paths and identity not in identities, "distinct full-array file identities required")
        paths.add(spelling)
        identities.add(identity)


def finite_array(value, budget, label, *, nonnegative=False):
    finite = np.isfinite(value)
    budget.watch(finite)
    need(bool(finite.all()), "nonfinite " + label)
    if nonnegative:
        need(float(value.min(initial=0.)) >= 0., "negative " + label)


def compare_arrays(value, target, mask, budget, *, maximum=None, rms=None):
    need(type(value) is np.ndarray and type(target) is np.ndarray and value.shape == target.shape
         and value.ndim == 2 and value.dtype.str == target.dtype.str == "<f8", "matched float64 image arrays required")
    need(type(mask) is np.ndarray and mask.dtype == np.dtype(bool) and mask.shape == value.shape,
         "typed full-image comparison mask required")
    need(bool(mask.any()), "nonempty comparison mask required")
    finite_array(value, budget, "value image")
    finite_array(target, budget, "target image")
    with np.errstate(over="ignore", invalid="ignore"):
        delta = np.subtract(value, target)
    budget.watch(delta)
    finite_array(delta, budget, "image residual")
    absolute = np.abs(delta)
    selected = delta[mask]
    selected_abs = absolute[mask]
    budget.watch(absolute, selected, selected_abs)
    peak = float(selected_abs.max())
    measured_rms = peak*math.sqrt(math.fsum((float(x)/peak)**2 for x in selected)/selected.size) if peak else 0.
    minimum_signed, maximum_signed = float(selected.min()), float(selected.max())
    equality = np.empty(value.shape, dtype=bool)
    budget.watch(equality)

    def location(array, wanted):
        np.equal(array, wanted, out=equality)
        np.logical_and(equality, mask, out=equality)
        locations = np.flatnonzero(equality)
        budget.watch(locations)
        index = int(locations[0])
        y, x = divmod(index, value.shape[1])
        return dict(x=x, y=y, ties=int(locations.size))

    record = dict(count=int(selected.size), maximum_abs_e=peak, rms_e=measured_rms,
                  minimum_signed_e=minimum_signed, maximum_signed_e=maximum_signed,
                  absolute_maximum_location=location(absolute, peak),
                  minimum_signed_location=location(delta, minimum_signed),
                  maximum_signed_location=location(delta, maximum_signed))
    need(maximum is None or peak <= maximum, "full-array maximum discrepancy bar: "+C.canonical(record).decode())
    need(rms is None or measured_rms <= rms, "full-array RMS discrepancy bar: "+C.canonical(record).decode())
    budget.check()
    return record


def descriptive(value, target, mask, budget):
    if not bool(mask.any()):
        return dict(count=0, empty=True)
    return dict(empty=False, **compare_arrays(value, target, mask, budget))


def full_author_work(work):
    names = ("scope", "limits", "point_calls", "angular_nodes", "peak_node_pairs", "tracked_peak_ndarray_bytes",
             "tracked_peak_ndarrays", "peak_live_scalar_frames", "observer", "observer_events", "optional_hook_calls",
             "cell_allocation", "cpu_seconds", "wall_seconds", "cumulative_point_calls", "cumulative_angular_nodes",
             "frames_started", "check_calls", "hybrid_hook_calls", "hybrid_collection", "transfer_cache_entries", "transfer_cache_limit")
    C.keys(work, names, "full author work")
    limits = dict(points=16000000, nodes=2400000000, cpu=1800, wall=3600, arrays=33554432, pairs=32768)
    C.equal_record(work["limits"], limits, "full author limits")
    need(work["scope"] == "full-arm" and work["observer"] == "count", "full author scope/mode")
    for name in set(names)-{"scope", "limits", "observer", "cell_allocation", "cpu_seconds", "wall_seconds", "hybrid_collection"}:
        C.integer(work[name], name)
    need(work["point_calls"] <= limits["points"] and work["angular_nodes"] <= limits["nodes"], "full author per-frame work cap")
    need(work["point_calls"] <= work["cumulative_point_calls"] <= work["frames_started"]*limits["points"]
         and work["angular_nodes"] <= work["cumulative_angular_nodes"] <= work["frames_started"]*limits["nodes"],
         "full author cumulative/frame work relation")
    need(work["peak_node_pairs"] <= limits["pairs"] and work["tracked_peak_ndarray_bytes"] <= limits["arrays"]
         and work["peak_live_scalar_frames"] <= 1 and work["transfer_cache_entries"] <= 20
         and work["transfer_cache_limit"] == 20, "full author storage/pair/cache cap")
    need(C.finite(work["cpu_seconds"], "full CPU", 0) <= 1800
         and C.finite(work["wall_seconds"], "full wall", 0) <= 3600, "full author arm time cap")
    need(type(work["hybrid_collection"]) is dict, "full hybrid collection map")
    for name, count in work["hybrid_collection"].items():
        need(type(name) is str, "full collection name")
        C.integer(count, "full collection count")
    allocation = work["cell_allocation"]
    C.keys(allocation, ("cells", "leaves", "minimum_depth", "maximum_depth", "locally_overallocated_leaves",
                        "cells_with_locally_overallocated_leaves"), "full cell allocation")
    for value in allocation.values():
        C.integer(value, "full allocation")
    need(allocation["minimum_depth"] <= allocation["maximum_depth"] <= 6, "full allocation depth")
    return work


def full_payload(scalar, branch, indices, diagnostics, budget, arm="primary"):
    need(scalar.dtype.str == "<f8" and scalar.ndim == 2 and branch.dtype.str == "|u1"
         and branch.shape == scalar.shape, "full scalar/branch interpretation")
    finite_array(scalar, budget, "full scalar", nonnegative=True)
    valid = branch <= 2
    budget.watch(valid)
    need(bool(valid.all()), "full branch code")
    numerical = branch == 2
    expected = np.flatnonzero(numerical)
    budget.watch(numerical, expected)
    need(indices.dtype.str == "<u4" and indices.ndim == 1 and np.array_equal(indices, expected),
         "full numerical index coverage")
    need(diagnostics.dtype.str == "<f8" and diagnostics.shape == (len(indices), 4), "full diagnostic shape/type")
    finite_array(diagnostics, budget, "full diagnostics", nonnegative=True)
    sums = diagnostics[:, 1]+diagnostics[:, 2]
    budget.watch(sums)
    need(np.array_equal(sums, diagnostics[:, 0]), "full diagnostic indicator sum")
    need(arm in ("primary", "angle-refined", "cell-refined"), "full diagnostic arm")
    cell_cap = .00075/4 if arm == "cell-refined" else .00075
    pupil_cap = .00025/4 if arm == "angle-refined" else .00025
    need(float(diagnostics[:, 1].max(initial=0.)) <= cell_cap
         and float(diagnostics[:, 2].max(initial=0.)) <= pupil_cap, "full diagnostic frozen arm ceilings")
    delta_valid = diagnostics[:, 3] <= diagnostics[:, 1]
    budget.watch(delta_valid)
    need(bool(delta_valid.all()), "full diagnostic cell delta exceeds indicator")
    counts = {}
    for code, name in enumerate(("foreground", "background", "numerical")):
        np.equal(branch, code, out=valid)
        counts[name] = int(np.count_nonzero(valid))
    return counts


def validate_frame_work(before, after, index):
    C.integer(index, "frame work original index")
    full_author_work(before)
    full_author_work(after)
    C.monotone_work(before, after, C.AUTHOR_CUMULATIVE, "full frame")
    need(before["frames_started"] == after["frames_started"] == index+1
         and before["point_calls"] == before["angular_nodes"] == 0, "full frame reset/start witness")
    need(after["cumulative_point_calls"]-before["cumulative_point_calls"] == after["point_calls"]
         and after["cumulative_angular_nodes"]-before["cumulative_angular_nodes"] == after["angular_nodes"], "full frame cumulative delta")
    return before, after


def read_author_frame(reads, path, trusted, inputs, source_digest, budget):
    r = reads.external(path, trusted)
    C.keys(r, ("schema", "status", "inputs", "source_set_sha256", "arrays", "diagnostic_columns", "branch_codes",
               "analytic_error_scope", "completed_cells", "traversal", "traversal_sha256", "work_before", "work_after"), "full author frame")
    need(r["schema"] == "m194g-author-frame-v1" and r["status"] == "complete-uncommissioned", "full author frame status/schema")
    C.equal_record(r["inputs"], inputs, "full frame actual inputs")
    need(r["source_set_sha256"] == source_digest, "full frame source digest")
    C.equal_record(r["branch_codes"], dict(foreground=0, background=1, numerical=2), "full branch codes")
    C.equal_record(r["diagnostic_columns"], list(C.DIAGNOSTIC_COLUMNS), "full diagnostic columns")
    need(r["analytic_error_scope"] == "no adaptive indicator; independent scalar comparison required", "full analytic limitation")
    height, width = inputs["height"], inputs["width"]
    need(C.integer(r["completed_cells"], "full completed cells") == width*height and r["traversal"] == "row-major", "full frame complete traversal")
    trace = hashlib.sha256()
    for index in range(width*height):
        trace.update(index.to_bytes(4, "little"))
    need(r["traversal_sha256"] == trace.hexdigest(), "full traversal hash")
    before, after = validate_frame_work(r["work_before"], r["work_after"], inputs["frame"]["index"])
    refs = r["arrays"]
    C.keys(refs, ("scalar", "branch", "fallback_indices", "fallback_diagnostics"), "full four array refs")
    root = Path(path).resolve().parent
    distinct_refs(root, list(refs.values()))
    scalar = reads.array(root, refs["scalar"], "<f8", (height, width))[0]
    branch = reads.array(root, refs["branch"], "|u1", (height, width))[0]
    numerical_mask = branch == 2
    budget.watch(numerical_mask)
    count = int(np.count_nonzero(numerical_mask))
    indices = reads.array(root, refs["fallback_indices"], "<u4", (count,))[0]
    diagnostics = reads.array(root, refs["fallback_diagnostics"], "<f8", (count, 4))[0]
    counts = full_payload(scalar, branch, indices, diagnostics, budget, inputs["arm"])
    need(after["cell_allocation"]["cells"] == counts["numerical"], "full allocation/numerical population")
    return r, scalar, branch, counts


def component_authority(reads, path, trusted):
    r = reads.external(path, trusted)
    C.keys(r, ("schema", "status", "invocation", "started_utc", "result", "exception", "traceback", "inputs_unchanged",
               "wall_seconds", "entry_input_bindings"), "component command authority")
    need(r["schema"] == "m194g-independent-component-reader-command-v1"
         and r["status"] == "PASS_COMPONENTS_AND_OBSERVER_ONLY"
         and r["exception"] is None and r["traceback"] is None and r["inputs_unchanged"] is True,
         "complete independent component command required")
    inner = r["result"]
    need(type(inner) is dict and inner.get("schema") == "m194g-independent-component-verification-v1"
         and inner.get("status") == "PASS_COMPONENTS_AND_OBSERVER_ONLY", "complete independent component result required")
    need(len(inner["components"]["comparisons"]) == 598 and len(inner["literal_oracles"]) == 52
         and inner["normalization_controls"]["direct_rows"] == 72
         and len(inner["normalization_controls"]["active_faults"]) == 12, "complete component deciding populations required")
    argv = r["invocation"]
    need(type(argv) is list and all(type(x) is str for x in argv), "component actual invocation")

    def argument(name):
        need(argv.count(name) == 1, "component invocation option " + name)
        index = argv.index(name)+1
        need(index < len(argv), "component invocation value " + name)
        return argv[index]

    execution_path = Path(argument("--execution-release"))
    execution_path = execution_path if execution_path.is_absolute() else REPO/execution_path
    C.read_execution(reads, execution_path, argument("--execution-release-sha256"), scope="components", argv=argv)
    controls_path = Path(argument("--controls"))
    controls_path = controls_path if controls_path.is_absolute() else REPO/controls_path
    C.verify_controls(reads, controls_path, argument("--controls-sha256"))
    for ledger in (r["entry_input_bindings"], inner["input_bindings"]):
        need(type(ledger) is dict and ledger, "component actual input ledger")
        for name, ref in ledger.items():
            C.keys(ref, ("sha256", "bytes"), "component ledger binding")
            target = Path(name).resolve()
            need(target.is_relative_to(REPO), "component input outside repository")
            reads.bytes(target, ref["sha256"], ref["bytes"], max(C.MAX_JSON, ref["bytes"]))
    return r


def frame_inputs(fixture, index, arm):
    return dict(scene=fixture["scene"], frame=dict(index=index, inverse_focus=fixture["inverse_foci"][index],
                K=fixture["K"], forward_similarity=fixture["forward_similarity"]),
                width=fixture["width"], height=fixture["height"], arm=arm, method="analytic-enabled")


def read_parent(reads, path, trusted, role, fixture, component):
    r = reads.external(path, trusted)
    root = Path(path).resolve().parent
    author = role.startswith("author-")
    arm = role.removeprefix("author-") if author else role.removeprefix("reference-")
    if author:
        C.keys(r, ("schema", "status", "scope", "arm", "invocation", "execution_release", "fixture", "inputs_sha256",
                   "sources_before", "sources_after", "source_capture_error", "frames", "error", "work", "runtime"), "complete author arm")
        need(r["schema"] == "m194g-author-render-v1" and r["status"] == "COMPLETE_AUTHOR_FLOATS_UNCOMMISSIONED"
             and r["scope"] == "full-author-arm" and r["error"] is None and r["source_capture_error"] is None,
             "complete author arm status")
        full_author_work(r["work"])
        need(r["work"]["frames_started"] == 5, "complete author five-frame work")
        C.equal_record(r["inputs_sha256"], hashlib.sha256(C.canonical(fixture)+b"\n").hexdigest(), "full author fixture digest")
        ex = r["execution_release"]
        C.keys(ex, ("path", "sha256", "bytes"), "author execution ref")
        execution_path = Path(ex["path"]).resolve()
        need(execution_path.is_relative_to(REPO), "author execution outside repository")
        scope, script, snapshots = "full-author-arm", "author-render.py", ("sources-before", "sources-after")
        invocation = r["invocation"]
        required = {"experiments/m194g-larger-pupil/"+name for name in
                    ("author-render.py", "author-components.py", "hybrid.py", "pinned-loader.py", "geometry.py")}
        required |= {"experiments/m194e-joint-pupil/model.py", "experiments/m194e-joint-pupil/render.py"}
        C.absolute_ref(reads, r["fixture"], HERE/"fixture.json")
        source_digest = hashlib.sha256(C.canonical(r["sources_before"])+b"\n").hexdigest()
    else:
        C.keys(r, ("schema", "status", "arm", "ref_root", "repository_provenance", "runtime", "frames", "sources_before",
                   "budget", "exception", "traceback", "finalization_errors", "execution_release", "controls", "fixture",
                   "input", "authority", "sources_after", "sources_unchanged"), "complete reference arm")
        need(r["schema"] == "m194g-independent-reference-arm-v1" and r["status"] == "PASS_COMPLETE_REFERENCE_ARM_ONLY"
             and r["ref_root"] == "repository" and r["exception"] is None and r["traceback"] is None
             and r["finalization_errors"] == [] and r["sources_unchanged"] is True, "complete reference arm status")
        C.reference_work(r["budget"])
        C.equal_record(r["input"], fixture, "full reference fixture inputs")
        ex = r["execution_release"]
        reads.bound(REPO, ex)
        execution_path = C.relative_path(REPO, ex["path"])
        scope, script, snapshots = "full-reference-arm", "independent-reference.py", ("source-snapshot",)
        invocation = r["runtime"]
        required = {"experiments/m194g-larger-pupil/"+name for name in
                    ("independent-reference.py", "independent-reference-components.py", "independent-normalized-interval.py",
                     "independent-normalized-interval-controls.py", "reference-interval-amendment-1.md")}
        required.add("experiments/m194e-joint-pupil/independent-model.py")
        reads.bound(REPO, r["fixture"])
        controls = reads.external(C.relative_path(REPO, r["controls"]["path"]), r["controls"]["sha256"])
        need(controls.get("status") == "PASS_REFERENCE_COMPONENTS_ONLY", "full reference component dependency")
        C.equal_record(controls["sources_before"], r["sources_before"], "reference component/current sources")
        C.equal_record(controls["sources_after"], r["sources_before"], "reference component final sources")
        component_argv = component["invocation"]
        ref_index = component_argv.index("--reference")+1
        expected_component = Path(component_argv[ref_index])
        expected_component = expected_component if expected_component.is_absolute() else REPO/expected_component
        need(C.relative_path(REPO, r["controls"]["path"]) == expected_component.resolve()
             and r["controls"]["sha256"] == component_argv[component_argv.index("--reference-sha256")+1],
             "full reference did not consume independently admitted reference components")
        source_digest = None
    need(r["arm"] == arm and r["fixture"]["sha256"] == FIXTURE_SHA, "full result actual arm/fixture")
    release = C.read_execution(reads, execution_path, ex["sha256"], scope=scope)
    C.check_invocation(invocation, release, ex["sha256"], root, script, reference=not author)
    env = r["runtime"]["thread_environment" if author else "environment"]
    C.equal_record(env, {name: "2" for name in THREADS}, "full recorded thread limits")
    C.source_closure(reads, r["sources_before"], r["sources_after"], root, snapshots, required, release)
    need(type(r["frames"]) is list and len(r["frames"]) == 5, "exact five full frame records")
    if author:
        for index, frame in enumerate(r["frames"]):
            C.keys(frame, ("frame_index", "receipt"), "full author frame entry")
            need(C.integer(frame["frame_index"], "full original frame index") == index, "full author frame order")
        distinct_refs(root, [frame["receipt"] for frame in r["frames"]])
    else:
        for index, frame in enumerate(r["frames"]):
            need(C.integer(frame["index"], "full reference index") == index and frame["arm"] == arm,
                 "full reference frame order")
        distinct_refs(REPO, [frame["array"] for frame in r["frames"]])
    return dict(record=r, root=root, source_digest=source_digest, release=release)


def read_reference_frame(reads, record, fixture, index, arm, previous, budget):
    C.keys(record, ("arm", "index", "inverse_focus", "frame", "input", "array", "indicators", "branches", "completed_cells",
                    "shape", "dtype", "minimum_e", "maximum_e", "maximum_indicator_e", "engine",
                    "indicator_scope_by_branch", "analytic_phase_arithmetic_engineering_reservation_e"), "full reference frame")
    inputs = frame_inputs(fixture, index, arm)
    C.equal_record(record["frame"], inputs["frame"], "full reference actual frame")
    need(record["arm"] == arm and C.integer(record["index"], "full reference index") == index
         and C.finite(record["inverse_focus"], "full reference focus") == fixture["inverse_foci"][index], "full reference frame identity")
    shape = [fixture["height"], fixture["width"]]
    C.equal_record(record["shape"], shape, "full reference shape")
    need(record["dtype"] == "<f8" and C.integer(record["completed_cells"], "reference completed cells") == math.prod(shape),
         "full reference completed population")
    input_record = C.strict_json(reads.bound(REPO, record["input"]))
    C.equal_record(input_record, {k: inputs[k] for k in ("scene", "frame", "width", "height")}, "full reference reopened inputs")
    distinct_refs(REPO, [record[key] for key in ("array", "indicators", "branches")])
    scalar = reads.array(REPO, record["array"], "<f8", shape)[0]
    indicators = reads.array(REPO, record["indicators"], "<f8", shape)[0]
    branches = reads.array(REPO, record["branches"], "|u1", shape)[0]
    finite_array(scalar, budget, "reference scalar", nonnegative=True)
    finite_array(indicators, budget, "reference indicators", nonnegative=True)
    valid = branches <= 2
    budget.watch(valid)
    need(bool(valid.all()), "reference branch codes")
    C.equal_record([record["minimum_e"], record["maximum_e"], record["maximum_indicator_e"]],
                   [float(scalar.min()), float(scalar.max()), float(indicators.max())], "actual reference array summaries")
    engine = record["engine"]
    C.keys(engine, ("method", "target_e", "cache_entries", "cache_hits", "cache_misses", "cache_evictions",
                    "transfer_consumptions", "branch_counts", "normalization"), "full reference engine")
    target = {"primary": .000125, "refined": .0000078125}[arm]
    need(engine["method"] == C.REFERENCE_METHOD and C.finite(engine["target_e"], "full reference target") == target,
         "full reference method/target")
    counts = C.normalization_receipt(engine["normalization"], target)
    for key in ("cache_entries", "cache_hits", "cache_misses", "cache_evictions", "transfer_consumptions"):
        C.integer(engine[key], "reference " + key)
    need(engine["cache_entries"] <= 20, "full reference cache cap")
    C.keys(engine["branch_counts"], ("foreground", "background", "numerical", "point"), "full reference branch population")
    before_counts = dict(foreground=0, background=0, numerical=0, point=0) if previous is None else previous["branch_counts"]
    actual = {}
    for code, name in enumerate(("foreground", "background", "numerical")):
        np.equal(branches, code, out=valid)
        actual[name] = int(np.count_nonzero(valid))
        need(C.integer(engine["branch_counts"][name], "reference cumulative branch")-before_counts[name] == actual[name],
             "actual reference per-frame branch delta")
    need(C.integer(engine["branch_counts"]["point"], "reference point count") == 0, "full reference point substitution")
    before_normal = (0, 0) if previous is None else C.normalization_receipt(previous["normalization"], target)
    delta = [new-old for old, new in zip(before_normal, counts)]
    need(all(value >= 0 for value in delta) and ((all(value > 0 for value in delta)) if actual["numerical"] else delta == [0, 0]),
         "full reference numerical work consumption")
    if previous is not None:
        C.monotone_work(previous, engine, ("cache_hits", "cache_misses", "cache_evictions", "transfer_consumptions"), "full reference engine")
    C.equal_record(record["indicator_scope_by_branch"], dict(foreground="conditional propagated spatial quadrature estimates",
                   background="conditional propagated spatial quadrature estimates", numerical="frozen independent Cartesian quadrature estimate"),
                   "reference indicator limitations")
    need(record["analytic_phase_arithmetic_engineering_reservation_e"] == target/2, "reference engineering reservation scope")
    return scalar, branches, engine, actual


def private_controls(reads, path, trusted):
    r = reads.external(path, trusted)
    need(r.get("schema") == "m194g-independent-full-array-controls-v1" and r.get("fixture_only") is True
         and r.get("status") == "PASS_PRIVATE_FULL_ARRAY_CONTROLS" and r.get("exception") is None
         and r.get("traceback") is None and r.get("finalization_error") is None, "complete full-reader private controls required")
    rows = r["checks"]
    need(type(rows) is list and C.integer(r["check_count"], "full control count", 1) == len(rows)
         and all(type(row) is dict and row.get("passed") is True for row in rows), "full-reader deciding control failure")
    names = [row.get("name") for row in rows]
    need(len(set(names)) == len(names), "duplicate full-reader control name")
    required = {"maximum-live-complement", "maximum-live-band", "rms-live", "actual-npy-huge-header",
                "actual-diagnostic-live", "full-author-frame-reset", "actual-full-entry-valid",
                "actual-full-entry-component-failed", "publication-final-budget-refusal", "authority-child-projection-live",
                "one-frame-failure-cannot-pool", "one-arm-failure-cannot-pool", "full-author-frame-reset-live",
                "full-author-frame-delta-live", "all-scalar-identities-alias-live", "actual-diagnostic-coherent-cap-live"}
    need(required <= set(names), "load-bearing full-reader controls absent")
    C.equal_record(r["sources_after"], r["sources_before"], "full controls source stability")
    for name, ref in r["sources_before"].items():
        reads.bound(REPO, dict(path=name, **ref))
        reads.bound(Path(path).resolve().parent/"source-snapshot", dict(path=name, **ref))
    for name in ("independent-full-array-reader.py", "independent-full-array-controls.py", "independent-component-reader.py"):
        need("experiments/m194g-larger-pupil/"+name in r["sources_before"], "full control actual dependency absent")
    return dict(check_count=len(rows), fixture_only=True)


def check_authority(authority, comparison):
    C.keys(authority, ("schema", "status", "ref_root", "fixture", "component_verification", "comparison", "width", "height",
                       "cell", "units", "reference_index", "primary_frames"), "full float authority")
    need(authority["schema"] == "m194g-float-commission-v1" and authority["status"] == "PASS_COMPLETE_FLOAT_MODEL",
         "full float authority status/schema")
    need(authority["ref_root"] == "repository" and authority["cell"] == "integer-centre-unit-square"
         and authority["units"] == "expected-electrons", "float authority path/cell/units")
    need(C.integer(authority["width"], "authority width") == 320 and C.integer(authority["height"], "authority height") == 240
         and C.integer(authority["reference_index"], "authority reference") == 2, "float authority native geometry")
    for name in ("fixture", "component_verification", "comparison"):
        C.keys(authority[name], ("path", "sha256", "bytes"), "authority FileRef")
        C.relative_path(REPO, authority[name]["path"])
        C.digest(authority[name]["sha256"])
        C.integer(authority[name]["bytes"], "authority file extent", 1)
    need(authority["fixture"]["sha256"] == FIXTURE_SHA, "authority registered fixture")
    need(type(authority["primary_frames"]) is list and len(authority["primary_frames"]) == 5, "authority complete primary population")
    for index, frame in enumerate(authority["primary_frames"]):
        C.keys(frame, ("index", "inverse_focus", "author_receipt", "scalar"), "authority primary frame")
        need(C.integer(frame["index"], "authority original index") == index
             and C.finite(frame["inverse_focus"], "authority focus") == (.5, .625, .75, .875, 1.)[index], "authority primary identity")
        C.keys(frame["author_receipt"], ("path", "sha256", "bytes"), "authority original receipt")
        C.keys(frame["scalar"], ("path", "sha256", "bytes", "dtype", "shape"), "authority scalar ArrayRef")
        need(frame["scalar"]["dtype"] == "<f8", "authority scalar dtype")
        C.equal_record(frame["scalar"]["shape"], [240, 320], "authority scalar shape")
        for ref in (frame["author_receipt"], frame["scalar"]):
            C.relative_path(REPO, ref["path"])
            C.digest(ref["sha256"])
            C.integer(ref["bytes"], "authority child extent", 1)
    need(comparison.get("schema") == "m194g-independent-full-array-verification-v1"
         and comparison.get("status") == "PASS_COMPLETE_FLOAT_MODEL", "authority complete comparison child required")
    projection = {k: v for k, v in authority.items() if k not in ("schema", "status", "comparison")}
    C.equal_record(comparison["admitted_inputs"], projection, "authority full admitted-input projection")
    C.keys(comparison["render_results"], ROLES, "authority complete role map")
    return projection


def compare_population(frames, whole, band, budget):
    """Actual streamed five-frame/three-arm schedule; shared with powered controls."""
    comparisons, refinements, subsets, seen = [], [], [], []
    for index, arrays, branches in frames:
        need(type(index) is int and index == len(seen) and index < 5, "fixed comparison frame order")
        C.keys(arrays, ROLES, "fixed comparison role arrays")
        C.keys(branches, ROLES, "fixed comparison role branches")
        seen.append(index)
        target = arrays["reference-refined"]
        for role in ROLES[:3]:
            for label, mask in (("whole", whole), ("fixed-native-band", band)):
                try:
                    summary = compare_arrays(arrays[role], target, mask, budget, maximum=.004, rms=.0008)
                except ValueError as exc:
                    raise ValueError(f"frame={index} role={role} population={label}: {exc}") from exc
                comparisons.append(dict(role=role, original_index=index, population=label, **summary))
            author_mask = branches[role] == 2
            reference_mask = branches["reference-refined"] == 2
            budget.watch(author_mask, reference_mask)
            subsets.append(dict(role=role, original_index=index,
                                author_actual_fallback=descriptive(arrays[role], target, author_mask, budget),
                                independent_actual_boundary=descriptive(arrays[role], target, reference_mask, budget),
                                scope="descriptive only; neither branch mask changes whole/band admission"))
        for role in ("author-angle-refined", "author-cell-refined"):
            refinements.append(dict(role=role, baseline="author-primary", original_index=index,
                                    **compare_arrays(arrays[role], arrays["author-primary"], whole, budget, maximum=.001)))
        refinements.append(dict(role="reference-refined", baseline="reference-primary", original_index=index,
                                **compare_arrays(arrays["reference-refined"], arrays["reference-primary"], whole, budget, maximum=.0005)))
        del target, author_mask, reference_mask
        budget.check()
    need(seen == list(range(5)) and len(comparisons) == 30 and len(refinements) == 15,
         "complete fixed comparison population")
    return comparisons, refinements, subsets


def verify(args, release, budget, reads=None):
    reads = make_reads(budget) if reads is None else reads
    component = component_authority(reads, args.component_verification, args.component_verification_sha256)
    controls = private_controls(reads, args.controls, args.controls_sha256)
    fixture = reads.external(HERE/"fixture.json", FIXTURE_SHA)
    need(fixture["frame_indices"] == list(range(5)) and all(type(i) is int for i in fixture["frame_indices"])
         and fixture["width"] == 320 and fixture["height"] == 240, "registered full fixture population")
    parents, result_refs = {}, {}
    for role in ROLES:
        key = role.replace("-", "_")
        path, trusted = getattr(args, key), getattr(args, key+"_sha256")
        parents[role] = read_parent(reads, path, trusted, role, fixture, component)
        result_refs[role] = file_ref(reads, path)
    distinct_refs(REPO, list(result_refs.values()))
    height, width = fixture["height"], fixture["width"]
    x, y = np.arange(width, dtype="<f8")[None, :], np.arange(height, dtype="<f8")[:, None]
    scaled_y = .15*y
    mask_height = np.empty((height, width), dtype="<f8")
    budget.watch(scaled_y, mask_height)
    np.subtract(x, scaled_y, out=mask_height)
    mask_height -= 142.
    absolute_height = np.abs(mask_height)
    band = absolute_height <= 8.
    whole = np.ones((height, width), dtype=bool)
    complement = np.logical_not(band)
    budget.watch(x, y, mask_height, absolute_height, band, whole, complement)
    need(bool(band.any()) and bool(complement.any()), "actual band and complement must occur")
    frame_summaries, primary_frames, scalar_refs = [], [], []
    previous_author, previous_reference = {}, {}
    def streamed_frames():
        for index in range(5):
            arrays, branches = {}, {}
            for role in ROLES:
                parent = parents[role]
                arm = role.split("-", 1)[1]
                if role.startswith("author-"):
                    item = parent["record"]["frames"][index]
                    ref = item["receipt"]
                    path = C.relative_path(parent["root"], ref["path"])
                    r, scalar, branch, counts = read_author_frame(reads, path, ref["sha256"], frame_inputs(fixture, index, arm),
                                                                 parent["source_digest"], budget)
                    before, after = r["work_before"], r["work_after"]
                    if role in previous_author:
                        C.monotone_work(previous_author[role], before, C.AUTHOR_CUMULATIVE, "between full frames")
                        need(previous_author[role]["cumulative_point_calls"] == before["cumulative_point_calls"]
                             and previous_author[role]["cumulative_angular_nodes"] == before["cumulative_angular_nodes"], "unaccounted full-frame work")
                    previous_author[role] = after
                    scalar_refs.append(repo_ref(path.parent, r["arrays"]["scalar"]))
                    if role == "author-primary":
                        primary_frames.append(dict(index=index, inverse_focus=fixture["inverse_foci"][index],
                                                   author_receipt=file_ref(reads, path), scalar=repo_ref(path.parent, r["arrays"]["scalar"])))
                else:
                    scalar, branch, engine, counts = read_reference_frame(reads, parent["record"]["frames"][index], fixture, index, arm,
                                                                         previous_reference.get(role), budget)
                    previous_reference[role] = engine
                    scalar_refs.append(parent["record"]["frames"][index]["array"])
                arrays[role], branches[role] = scalar, branch
                frame_summaries.append(dict(role=role, original_index=index, branch_counts=counts))
            yield index, arrays, branches
            arrays.clear()
            branches.clear()
            del scalar, branch
    comparisons, refinements, subsets = compare_population(streamed_frames(), whole, band, budget)
    for role in ROLES[:3]:
        final = parents[role]["record"]["work"]
        C.monotone_work(previous_author[role], final, C.AUTHOR_CUMULATIVE, "terminal full arm")
        need(final["cumulative_point_calls"] == previous_author[role]["cumulative_point_calls"]
             and final["cumulative_angular_nodes"] == previous_author[role]["cumulative_angular_nodes"], "terminal unaccounted author work")
    for role in ROLES[3:]:
        final = parents[role]["record"]["budget"]
        need(previous_reference[role]["normalization"]["integrand_calls"] == final["chord_evaluations"],
             "full reference cumulative chord work")
    need(len(comparisons) == 30 and len(refinements) == 15 and len(frame_summaries) == 25,
         "complete full deciding population required")
    need(len(scalar_refs) == 25, "all25 original scalar file refs required")
    distinct_refs(REPO, scalar_refs)
    distinct_refs(REPO, [frame["scalar"] for frame in primary_frames])
    distinct_refs(REPO, [frame["author_receipt"] for frame in primary_frames])
    admitted = dict(ref_root="repository", fixture=file_ref(reads, HERE/"fixture.json"),
                    component_verification=file_ref(reads, args.component_verification), width=320, height=240,
                    cell="integer-centre-unit-square", units="expected-electrons", reference_index=2,
                    primary_frames=primary_frames)
    reads.finish()
    return dict(schema="m194g-independent-full-array-verification-v1", status="PASS_COMPLETE_FLOAT_MODEL",
                admitted_inputs=admitted, render_results=result_refs, comparisons=comparisons, refinements=refinements,
                descriptive_subsets=subsets, frame_populations=frame_summaries, private_controls=controls,
                band=dict(equation="abs(x-0.15*y-142)<=8 at integer native centres", count=int(np.count_nonzero(band)),
                          complement=int(np.count_nonzero(complement))),
                authority_scope="fixed complete continuous shared-pupil numerical population; no physical optics, CFA or quality admission"), reads


def write_json(path, value):
    raw = C.canonical(value)+b"\n"
    with Path(path).open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(path=Path(path).resolve().relative_to(REPO).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def publish(output, result, reads, budget, *, final_check=None):
    """Acyclic publication. Any post-write failure invalidates the actual child."""
    output = Path(output)
    result_path, authority_path = output/"result.json", output/"float-commission.json"
    try:
        result["input_bindings"] = dict(reads.observed)
        result["resources"] = budget.receipt()
        comparison_ref = write_json(result_path, result)
        reads.finish()
        budget.check()
        authority = dict(schema="m194g-float-commission-v1", status="PASS_COMPLETE_FLOAT_MODEL",
                         comparison=comparison_ref, **result["admitted_inputs"])
        check_authority(authority, result)
        write_json(authority_path, authority)
        reads.finish()
        budget.check()
        if final_check is not None:
            final_check()
        return authority
    except Exception:
        original = traceback.format_exc()
        result["status"] = "UNCOMMISSIONED_FULL_ARRAYS"
        result["error"] = original
        result.setdefault("finalization_errors", [])
        try:
            if authority_path.exists():
                attempted = authority_path.read_bytes()
                (output/"refused-float-commission.json").write_bytes(attempted)
                rejected = C.strict_json(attempted)
                rejected["status"] = "UNCOMMISSIONED_FULL_ARRAYS"
                write_json(authority_path, rejected)
        except Exception:
            result["finalization_errors"].append(dict(stage="revoke-authority", error=traceback.format_exc()))
        try:
            write_json(result_path, result)
        except Exception:
            result["finalization_errors"].append(dict(stage="revoke-comparison", error=traceback.format_exc()))
            write_json(output/"publication-failure.json", result)
        raise


def main():
    parser = argparse.ArgumentParser()
    for name in (*ROLES, "component-verification", "controls", "execution-release"):
        parser.add_argument("--"+name, type=Path, required=True)
        parser.add_argument("--"+name+"-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-independent-full-array-verification-v1", status="UNCOMMISSIONED_FULL_ARRAYS",
                  error=None, finalization_errors=[])
    budget, reads, release, sources_before = None, None, None, None
    try:
        release = bootstrap(args.execution_release, args.execution_release_sha256, "full-array-reader", sys.orig_argv)
        budget = Budget()
        required = {(str(getattr(args, name.replace("-", "_")).resolve()), getattr(args, name.replace("-", "_")+"_sha256"))
                    for name in (*ROLES, "component-verification", "controls")}
        declared = {(str(C.relative_path(REPO, ref["path"])), ref["sha256"]) for ref in release["inputs"]}
        need(required <= declared, "full reader actual result inputs not released")
        reads = make_reads(budget)
        # Keep every released source and supplemental input in the same live
        # ledger used through comparison and final authority persistence.
        C.read_execution(reads, args.execution_release, args.execution_release_sha256,
                         scope="full-array-reader", argv=sys.orig_argv)
        sources_before = release["source_bindings"]
        for name, ref in sources_before.items():
            data = reads.bound(REPO, dict(path=name, **ref))
            dest = args.output/"source-snapshot"/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        result, reads = verify(args, release, budget, reads)
        result.update(error=None, finalization_errors=[], invocation=dict(orig_argv=list(sys.orig_argv), executable=sys.executable,
                      cwd=os.getcwd(), xoptions=dict(sys._xoptions), python=sys.version, numpy=np.__version__,
                      environment={name: os.environ.get(name) for name in THREADS}),
                      execution_release=dict(path=args.execution_release.resolve().relative_to(REPO).as_posix(),
                                             sha256=args.execution_release_sha256, bytes=args.execution_release.stat().st_size),
                      sources_before=sources_before, sources_after={})
        for name, ref in release["source_bindings"].items():
            data = reads.bound(REPO, dict(path=name, **ref))
            result["sources_after"][name] = dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
        C.equal_record(result["sources_after"], result["sources_before"], "full reader source stability")
        publish(args.output, result, reads, budget)
    except Exception:
        if result.get("error") is None:
            result["error"] = traceback.format_exc()
        result["status"] = "UNCOMMISSIONED_FULL_ARRAYS"
        result.setdefault("invocation", dict(orig_argv=list(sys.orig_argv), executable=sys.executable, cwd=os.getcwd()))
        result["sources_before"] = sources_before
        if reads is not None:
            result["input_bindings"] = dict(reads.observed)
            try:
                reads.finish()
            except Exception:
                result["finalization_errors"].append(dict(stage="failed-run-inputs", error=traceback.format_exc()))
        if budget is not None:
            result["resources"] = budget.receipt()
        if C is not None:
            write_json(args.output/"result.json", result)
        else:
            (args.output/"result.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(dict(status=result["status"], error=result.get("error"))), flush=True)
    return 0 if result["status"] == "PASS_COMPLETE_FLOAT_MODEL" else 1


if __name__ == "__main__":
    raise SystemExit(main())
