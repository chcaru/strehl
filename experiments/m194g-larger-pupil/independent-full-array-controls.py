"""Private full-reader controls. No optical producer imports or numerical calls."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import traceback
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


class Checks:
    def __init__(self):
        self.rows = []

    def check(self, name, call, expected=None):
        row = dict(name=name, expected=expected, passed=False, value=None, exception=None)
        try:
            row["value"] = call()
            row["passed"] = expected is None
        except Exception as exc:
            row["exception"] = repr(exc)
            row["passed"] = expected is not None and type(exc).__name__ == expected[0] and expected[1] in str(exc)
            if not row["passed"]:
                row["traceback"] = traceback.format_exc()
        self.rows.append(row)


def run(F, args, release, budget):
    C, np = F.C, F.np
    checks = Checks()
    output = args.output/"private-fixtures"
    output.mkdir()
    zero = np.zeros((7, 11), dtype="<f8")
    whole = np.ones(zero.shape, dtype=bool)
    yy, xx = np.indices(zero.shape)
    band = np.abs(xx-.15*yy-4) <= 1
    complement = np.logical_not(band)
    budget.watch(zero, whole, xx, yy, band, complement)
    F.need(band.any() and complement.any(), "private band/complement power")

    def compare(level=0., *, location=None, mask=whole, maximum=.004, rms=.0008):
        values = np.full(zero.shape, level, dtype="<f8") if location is None else zero.copy()
        if location is not None:
            values[location] = level
        budget.watch(values)
        return F.compare_arrays(values, zero, mask, budget, maximum=maximum, rms=rms)

    checks.check("comparison-zero", compare)
    checks.check("maximum-equality", lambda: compare(.004, rms=None))
    checks.check("maximum-nextafter", lambda: compare(float(np.nextafter(.004, np.inf)), rms=None), ("ValueError", "maximum discrepancy bar"))
    checks.check("rms-equality", lambda: compare(.0008))
    checks.check("rms-live", lambda: compare(.0009), ("ValueError", "RMS discrepancy bar"))
    checks.check("maximum-live-complement", lambda: compare(.0041, location=(5, 9), mask=complement), ("ValueError", "maximum discrepancy bar"))
    checks.check("maximum-live-band", lambda: compare(.0041, location=(3, 4), mask=band), ("ValueError", "maximum discrepancy bar"))
    checks.check("comparison-restored", compare)

    def signed_ties():
        values = zero.copy()
        values[1, 2], values[2, 3], values[6, 10] = -.003, .003, -.002
        budget.watch(values)
        row = F.compare_arrays(values, zero, whole, budget, maximum=.004, rms=None)
        F.need(row["minimum_signed_e"] == -.003 and row["maximum_signed_e"] == .003
               and row["absolute_maximum_location"] == dict(x=2, y=1, ties=2), "signed/tied location oracle")
        return row
    checks.check("signed-and-tied-locations", signed_ties)
    checks.check("comparison-nan", lambda: compare(float("nan")), ("ValueError", "nonfinite value image"))
    checks.check("comparison-infinite", lambda: compare(float("inf")), ("ValueError", "nonfinite value image"))
    checks.check("comparison-empty-mask", lambda: compare(mask=np.zeros(zero.shape, dtype=bool)), ("ValueError", "nonempty comparison mask"))
    checks.check("comparison-mask-type", lambda: compare(mask=np.ones(zero.shape, dtype="u1")), ("ValueError", "typed full-image comparison mask"))
    checks.check("comparison-shape", lambda: F.compare_arrays(zero[:, :-1], zero, whole, budget), ("ValueError", "matched float64 image arrays"))
    checks.check("descriptive-empty", lambda: F.descriptive(zero, zero, np.zeros(zero.shape, dtype=bool), budget))

    def overflow():
        large, small = np.full(zero.shape, 1e308), np.full(zero.shape, -1e308)
        budget.watch(large, small)
        return F.compare_arrays(large, small, whole, budget)
    checks.check("comparison-finite-overflow", overflow, ("ValueError", "nonfinite image residual"))
    def population(fault=None):
        def frames():
            for index in range(5):
                arrays = {role: zero.copy() for role in F.ROLES}
                branches = {role: np.zeros(zero.shape, dtype="u1") for role in F.ROLES}
                if fault == "frame" and index == 3:
                    for role in F.ROLES[:3]: arrays[role].fill(.0009)
                if fault == "arm": arrays["author-angle-refined"].fill(.0009)
                budget.watch(*arrays.values(), *branches.values())
                yield index, arrays, branches
                arrays.clear()
                branches.clear()
        return F.compare_population(frames(), whole, band, budget)
    checks.check("actual-population-valid", population)
    checks.check("one-frame-failure-cannot-pool", lambda: population("frame"), ("ValueError", "RMS discrepancy bar"))
    checks.check("one-arm-failure-cannot-pool", lambda: population("arm"), ("ValueError", "RMS discrepancy bar"))
    checks.check("actual-population-restored", population)

    def save_array(name, array):
        path = output/name
        np.save(path, array, allow_pickle=False)
        raw = path.read_bytes()
        return dict(path=name, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), dtype=array.dtype.str, shape=list(array.shape))
    valid_ref = save_array("scalar.npy", zero)
    reads = F.make_reads(budget)
    checks.check("actual-npy-valid", lambda: list(reads.array(output, valid_ref, "<f8", zero.shape)[0].shape))
    def changed_array(stale=False, *, trailing=False, huge=False, dtype=False, fortran=False):
        name = "array-"+str(len(checks.rows))+".npy"
        if huge:
            stream = io.BytesIO()
            np.lib.format.write_array_header_1_0(stream, dict(descr="<f8", fortran_order=False, shape=(2**31, 2**31)))
            stream.write(zero.tobytes())
            raw = stream.getvalue()
        else:
            value = zero.astype("<f4") if dtype else np.asfortranarray(zero) if fortran else zero.copy()
            budget.watch(value)
            value[5, 9] = 1.
            stream = io.BytesIO()
            np.save(stream, value, allow_pickle=False)
            raw = stream.getvalue()+(b"extra" if trailing else b"")
        (output/name).write_bytes(raw)
        ref = {**valid_ref, "path": name}
        if not stale:
            ref.update(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        value = F.make_reads(budget).array(output, ref, "<f8", zero.shape)[0]
        return F.compare_arrays(value, zero, whole, budget, maximum=.004)
    checks.check("actual-npy-stale-bytes", lambda: changed_array(stale=True), ("ValueError", "actual file hash/length differs"))
    checks.check("actual-npy-rehashed-value", changed_array, ("ValueError", "maximum discrepancy bar"))
    checks.check("actual-npy-huge-header", lambda: changed_array(huge=True), ("ValueError", "actual NPY interpretation differs"))
    checks.check("actual-npy-trailing", lambda: changed_array(trailing=True), ("ValueError", "exact bounded numeric NPY payload"))
    checks.check("actual-npy-dtype", lambda: changed_array(dtype=True), ("ValueError", "actual NPY interpretation differs"))
    checks.check("actual-npy-fortran", lambda: changed_array(fortran=True), ("ValueError", "actual NPY interpretation differs"))
    checks.check("actual-npy-restored", lambda: list(reads.array(output, valid_ref, "<f8", zero.shape)[0].shape))
    identity_refs = [save_array(f"identity-{i}.npy", zero) for i in range(25)]
    checks.check("all-scalar-identities-equal-bytes-distinct", lambda: F.distinct_refs(output, identity_refs))
    def alias_identity():
        copied = list(identity_refs)
        copied[24] = copied[3]
        return F.distinct_refs(output, copied)
    checks.check("all-scalar-identities-alias-live", alias_identity, ("ValueError", "distinct full-array file identities"))
    checks.check("all-scalar-identities-restored", lambda: F.distinct_refs(output, identity_refs))

    def payload(which=None):
        scalar = zero.copy()
        branch = np.zeros(zero.shape, dtype="u1")
        branch[2, 3] = branch[5, 9] = 2
        indices = np.array([25, 64], dtype="<u4")
        diagnostics = np.array([[.0003, .0001, .0002, .00001], [.0003, .0001, .0002, .00001]], dtype="<f8")
        diagnostics[:, 0] = diagnostics[:, 1]+diagnostics[:, 2]
        if which == "branch": branch[0, 0] = 3
        if which == "missing": indices = indices[:1].copy()
        if which == "duplicate": indices[1] = indices[0]
        if which == "diagnostic": diagnostics[0, 1] += .0001
        if which == "coherent-cap":
            diagnostics[0, 2] = .000251
            diagnostics[0, 0] = diagnostics[0, 1]+diagnostics[0, 2]
        refs = [save_array(f"payload-{len(checks.rows)}-{name}.npy", array) for name, array in
                (("scalar", scalar), ("branch", branch), ("indices", indices), ("diagnostics", diagnostics))]
        reopened = [F.make_reads(budget).array(output, ref, ref["dtype"], tuple(ref["shape"]))[0] for ref in refs]
        return F.full_payload(*reopened, budget)
    checks.check("actual-payload-valid", payload)
    checks.check("actual-branch-live", lambda: payload("branch"), ("ValueError", "full branch code"))
    checks.check("actual-index-missing", lambda: payload("missing"), ("ValueError", "full numerical index coverage"))
    checks.check("actual-index-duplicate", lambda: payload("duplicate"), ("ValueError", "full numerical index coverage"))
    checks.check("actual-diagnostic-live", lambda: payload("diagnostic"), ("ValueError", "full diagnostic indicator sum"))
    checks.check("actual-diagnostic-coherent-cap-live", lambda: payload("coherent-cap"), ("ValueError", "full diagnostic frozen arm ceilings"))
    checks.check("actual-payload-restored", payload)

    allocation = dict(cells=0, leaves=0, minimum_depth=0, maximum_depth=0, locally_overallocated_leaves=0, cells_with_locally_overallocated_leaves=0)
    work = dict(scope="full-arm", limits=dict(points=16000000, nodes=2400000000, cpu=1800, wall=3600, arrays=33554432, pairs=32768),
                point_calls=16000000, angular_nodes=2400000000, peak_node_pairs=32768, tracked_peak_ndarray_bytes=33554432,
                tracked_peak_ndarrays=4, peak_live_scalar_frames=1, observer="count", observer_events=1, optional_hook_calls=1,
                cell_allocation=allocation, cpu_seconds=1800., wall_seconds=3600., cumulative_point_calls=32000000,
                cumulative_angular_nodes=4800000000, frames_started=2, check_calls=1, hybrid_hook_calls=1,
                hybrid_collection={}, transfer_cache_entries=20, transfer_cache_limit=20)
    def metadata(key=None, value=None):
        row = copy.deepcopy(work)
        if key: row[key] = value
        F.full_author_work(row)
        return {k: row[k] for k in ("scope", "point_calls", "cumulative_point_calls", "frames_started")}
    checks.check("full-author-equality", metadata)
    checks.check("full-author-zero-current-points", lambda: metadata("point_calls", 0))
    for name, key, value, boundary in (
        ("points-over", "point_calls", 16000001, "per-frame work cap"),
        ("nodes-over", "angular_nodes", 2400000001, "per-frame work cap"),
        ("cpu-over", "cpu_seconds", 1800.0001, "arm time cap"),
        ("wall-over", "wall_seconds", 3600.0001, "arm time cap"),
        ("storage-over", "tracked_peak_ndarray_bytes", 33554433, "storage/pair/cache cap"),
        ("scope", "scope", "components", "scope/mode"),
        ("bool", "frames_started", True, "integer:"),
        ("float", "frames_started", 2., "integer:"),
        ("cumulative", "cumulative_point_calls", 1, "cumulative/frame work relation"),
        ("missing-frame", "frames_started", 1, "cumulative/frame work relation"),
    ):
        checks.check("full-author-"+name, lambda key=key, value=value: metadata(key, value), ("ValueError", boundary))
    checks.check("full-author-restored", metadata)

    def frame_work(fault=None):
        after = copy.deepcopy(work)
        before = copy.deepcopy(work)
        before.update(point_calls=0, angular_nodes=0, cumulative_point_calls=16000000, cumulative_angular_nodes=2400000000)
        if fault == "not-reset": before["point_calls"] = 1
        if fault == "delta": before["cumulative_point_calls"] += 1
        if fault == "index": before["frames_started"] = 1
        F.validate_frame_work(before, after, 1)
        return dict(index=1, before_points=before["point_calls"], after_points=after["point_calls"],
                    cumulative_delta=after["cumulative_point_calls"]-before["cumulative_point_calls"])
    checks.check("full-author-frame-reset", frame_work)
    checks.check("full-author-frame-reset-live", lambda: frame_work("not-reset"), ("ValueError", "full frame reset/start witness"))
    checks.check("full-author-frame-delta-live", lambda: frame_work("delta"), ("ValueError", "full frame cumulative delta"))
    checks.check("full-author-frame-index-live", lambda: frame_work("index"), ("ValueError", "full frame reset/start witness"))
    checks.check("full-author-frame-reset-restored", frame_work)

    def local_budget(cpu=0., wall=0.):
        return F.Budget(started_cpu=0., started_wall=0., cpu_clock=lambda: cpu, wall_clock=lambda: wall,
                        cpu_limit=2., wall_limit=3., array_limit=1024)
    checks.check("reader-clock-equality", lambda: local_budget(2., 3.).receipt())
    checks.check("reader-cpu-over", lambda: local_budget(2.0001, 0.), ("ValueError", "full reader CPU budget"))
    checks.check("reader-wall-over", lambda: local_budget(0., 3.0001), ("ValueError", "full reader wall budget"))
    def storage(over=False, released=False):
        meter = local_budget()
        first = np.empty(64, dtype="<f8")
        meter.watch(first, first[::2])
        if released: del first
        second = np.empty(64 if not released else 128, dtype="<f8")
        meter.watch(second)
        F.need(meter.peak == 1024, "reader actual backing ledger")
        if over:
            extra = np.empty(1, dtype="u1")
            meter.watch(extra)
        return meter.receipt()
    checks.check("reader-owner-alias-equality", storage)
    checks.check("reader-owner-over", lambda: storage(over=True), ("ValueError", "full reader named-array budget"))
    checks.check("reader-owner-released", lambda: storage(released=True))

    def entry(failed=False, wrong_pin=False):
        path, trusted = args.component_verification, args.component_verification_sha256
        if failed:
            actual = C.strict_json(Path(path).read_bytes())
            actual["status"] = "UNCOMMISSIONED_COMPONENT_READER"
            data = C.canonical(actual)+b"\n"
            path = output/"private-failed-component.json"
            path.write_bytes(data)
            trusted = hashlib.sha256(data).hexdigest()
        namespace = SimpleNamespace(component_verification=path, component_verification_sha256="0"*64 if wrong_pin else trusted,
                                    controls="PRIVATE_UNREACHED", controls_sha256="0"*64)
        class Boundary(RuntimeError): pass
        saved = F.private_controls
        def stop(reads, path, sha):
            F.need(str(Path(namespace.component_verification).resolve()) in reads.observed, "actual full entry read witness")
            raise Boundary()
        try:
            F.private_controls = stop
            try: F.verify(namespace, release, budget)
            except Boundary: return dict(reached="private_controls", fixture_only=True, full_array_admission=False)
            raise AssertionError("full entry failed to reach named boundary")
        finally:
            F.private_controls = saved
    checks.check("actual-full-entry-valid", entry)
    checks.check("actual-full-entry-component-failed", lambda: entry(failed=True), ("ValueError", "complete independent component command required"))
    checks.check("actual-full-entry-wrong-pin", lambda: entry(wrong_pin=True), ("ValueError", "actual file hash/length differs"))
    checks.check("actual-full-entry-restored", entry)

    # Clearly private publication fixtures contain no admitted optical arrays.
    fixture_ref = dict(path="experiments/m194g-larger-pupil/fixture.json", sha256=F.FIXTURE_SHA, bytes=(HERE/"fixture.json").stat().st_size)
    component_ref = dict(path=args.component_verification.resolve().relative_to(REPO).as_posix(),
                         sha256=args.component_verification_sha256, bytes=args.component_verification.stat().st_size)
    frames = [dict(index=i, inverse_focus=(.5,.625,.75,.875,1.)[i],
                   author_receipt=dict(path=f"experiments/m194g-larger-pupil/PRIVATE-ONLY-{i}.json", sha256="0"*64, bytes=1),
                   scalar=dict(path=f"experiments/m194g-larger-pupil/PRIVATE-ONLY-{i}.npy", sha256="0"*64, bytes=1, dtype="<f8", shape=[240,320])) for i in range(5)]
    admission = dict(ref_root="repository", fixture=fixture_ref, component_verification=component_ref,
                     width=320, height=240, cell="integer-centre-unit-square", units="expected-electrons", reference_index=2, primary_frames=frames)
    comparison = dict(schema="m194g-independent-full-array-verification-v1", status="PASS_COMPLETE_FLOAT_MODEL",
                      admitted_inputs=admission, render_results={role: fixture_ref for role in F.ROLES},
                      private_fixture_notice="WRITER/SCHEMA CONTROL ONLY; nonexistent optical children")
    authority = dict(schema="m194g-float-commission-v1", status="PASS_COMPLETE_FLOAT_MODEL", comparison=fixture_ref, **admission)
    checks.check("authority-projection-valid-private", lambda: F.check_authority(authority, comparison))
    def authority_fault(kind):
        changed, child = copy.deepcopy(authority), copy.deepcopy(comparison)
        if kind == "projection": child["admitted_inputs"]["primary_frames"][0]["scalar"]["sha256"] = "1"*64
        elif kind == "schema": changed["schema"] = "m194e-float-commission-v1"
        elif kind == "bool": changed["primary_frames"][0]["index"] = False
        elif kind == "focus": changed["primary_frames"][2]["inverse_focus"] = .5
        elif kind == "shape": changed["primary_frames"][0]["scalar"]["shape"] = [320,240]
        elif kind == "escape": changed["primary_frames"][0]["scalar"]["path"] = "../escape.npy"
        elif kind == "missing": changed["primary_frames"].pop()
        elif kind == "child": child["status"] = "RUNNING"
        elif kind == "unknown": changed["admitted"] = True
        return F.check_authority(changed, child)
    for kind, boundary in (("projection", "admitted-input projection"), ("schema", "status/schema"), ("bool", "integer:"),
                           ("focus", "primary identity"), ("shape", "scalar shape"), ("escape", "relative child path"),
                           ("missing", "complete primary population"), ("child", "complete comparison child"), ("unknown", "closed keys:")):
        checks.check("authority-child-projection-live" if kind == "projection" else "authority-"+kind,
                     lambda kind=kind: authority_fault(kind), ("ValueError", boundary))
    checks.check("authority-projection-restored-private", lambda: F.check_authority(authority, comparison))
    def publication(fail=False):
        directory = output/("private-publication-refused" if fail else "private-publication-valid")
        directory.mkdir()
        record = copy.deepcopy(comparison)
        record.update(error=None, finalization_errors=[])
        meter = local_budget()
        def finish():
            if fail:
                meter.wall_clock = lambda: 4.
                meter.check()
        try:
            F.publish(directory, record, C.Reads(), meter, final_check=finish)
        except ValueError:
            child = C.strict_json((directory/"result.json").read_bytes())
            gate = C.strict_json((directory/"float-commission.json").read_bytes())
            F.need(child["status"] == gate["status"] == "UNCOMMISSIONED_FULL_ARRAYS"
                   and "full reader wall budget" in child["error"]
                   and (directory/"refused-float-commission.json").exists(), "actual failed publication not revoked")
            return dict(refused=True, child_status=child["status"], fixture_only=True)
        F.need(not fail, "final budget destroyer failed to fire")
        return dict(fixture_only=True, writer_path_completed=True, optical_authority=False)
    checks.check("publication-valid-private", publication)
    checks.check("publication-final-budget-refusal", lambda: publication(True))
    reads.finish()
    return checks.rows


def main():
    parser = argparse.ArgumentParser()
    for name in ("component-verification", "execution-release"):
        parser.add_argument("--"+name, type=Path, required=True)
        parser.add_argument("--"+name+"-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    record = dict(schema="m194g-independent-full-array-controls-v1", fixture_only=True, status="UNCOMMISSIONED_PRIVATE_CONTROLS",
                  checks=[], check_count=0, exception=None, traceback=None, finalization_error=None,
                  invocation=list(sys.orig_argv), sources_before=None, sources_after=None, resources=None)
    F = budget = entry_reads = None
    try:
        with args.execution_release.open("rb") as stream:
            raw = stream.read(16*1024*1024+1)
        if len(raw) > 16*1024*1024 or hashlib.sha256(raw).hexdigest() != args.execution_release_sha256:
            raise ValueError("private full release pin/extent")
        release = json.loads(raw)
        path = HERE/"independent-full-array-reader.py"
        source = path.read_bytes()
        key = path.relative_to(REPO).as_posix()
        if release["source_bindings"][key] != dict(sha256=hashlib.sha256(source).hexdigest(), bytes=len(source)):
            raise ValueError("private full reader source pin")
        spec = importlib.util.spec_from_loader("m194g_private_full_reader", loader=None, origin=str(path))
        F = importlib.util.module_from_spec(spec)
        F.__file__ = str(path)
        sys.modules[spec.name] = F
        exec(compile(source, str(path), "exec"), F.__dict__)
        release = F.bootstrap(args.execution_release, args.execution_release_sha256, "full-array-reader-controls", sys.orig_argv)
        budget = F.Budget(started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
        entry_reads = F.make_reads(budget)
        F.C.read_execution(entry_reads, args.execution_release, args.execution_release_sha256,
                           scope="full-array-reader-controls", argv=sys.orig_argv)
        if not any(F.C.relative_path(REPO, r["path"]) == args.component_verification.resolve()
                   and r["sha256"] == args.component_verification_sha256 for r in release["inputs"]):
            raise ValueError("actual full-entry component input not released")
        record["sources_before"] = release["source_bindings"]
        for name, ref in release["source_bindings"].items():
            dest = args.output/"source-snapshot"/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((REPO/name).read_bytes())
        record["checks"] = run(F, args, release, budget)
        record["check_count"] = len(record["checks"])
        if all(row["passed"] for row in record["checks"]): record["status"] = "PASS_PRIVATE_FULL_ARRAY_CONTROLS"
    except Exception:
        record["exception"], record["traceback"] = repr(sys.exception()), traceback.format_exc()
    finally:
        try:
            if record["sources_before"] is not None:
                record["sources_after"] = {name: dict(sha256=hashlib.sha256((REPO/name).read_bytes()).hexdigest(), bytes=(REPO/name).stat().st_size)
                                           for name in record["sources_before"]}
                if record["sources_after"] != record["sources_before"]: raise ValueError("full private source changed")
            if budget is not None:
                entry_reads.finish()
                budget.check()
                record["resources"] = budget.receipt()
        except Exception:
            record["finalization_error"] = traceback.format_exc()
            record["status"] = "UNCOMMISSIONED_PRIVATE_CONTROLS"
        (args.output/"result.json").write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
        if budget is not None:
            try: budget.check()
            except Exception:
                record["finalization_error"] = traceback.format_exc()
                record["status"] = "UNCOMMISSIONED_PRIVATE_CONTROLS"
                (args.output/"result.json").write_text(json.dumps(record, indent=2, sort_keys=True, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps(dict(status=record["status"], checks=record["check_count"], exception=record["exception"])), flush=True)
    return 0 if record["status"] == "PASS_PRIVATE_FULL_ARRAY_CONTROLS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
