"""Registered author component batch; no numerical import before external release."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def canonical(record):
    return (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def write_json(path, record):
    with Path(path).open("wb") as stream:
        stream.write(canonical(record))
        stream.flush()
        os.fsync(stream.fileno())


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    def bad(value):
        raise ValueError("nonfinite JSON number: " + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad)


def runtime_record(H=None, started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL):
    return dict(cpu_seconds=time.process_time()-started_cpu, wall_seconds=time.monotonic()-started_wall,
                python_version=sys.version, numpy_version=None if H is None else H.np.__version__,
                scipy_version=None if H is None else H.scipy.__version__,
                thread_environment={name: os.environ.get(name) for name in
                                    ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})


def binding(path):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError("bounded source/input extent")
    return raw, dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def relative_path(name):
    if not isinstance(name, str) or not name or "\\" in name or Path(name).is_absolute() or any(p in ("", ".", "..") for p in name.split("/")):
        raise ValueError("canonical repository-relative path required")
    path = (ROOT / name).resolve(strict=True)
    path.relative_to(ROOT)
    return path


def authorize(path, expected, scope, argv=None):
    """Closed root release, externally pinned and exact actual interpreter argv."""
    if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise ValueError("external execution release SHA256 required")
    raw, ref = binding(path)
    if ref["sha256"] != expected:
        raise ValueError("external execution release digest mismatch")
    release = strict_json(raw)
    if set(release) != {"schema", "scope", "source_bindings", "inputs", "commands"} or release["schema"] != "m194g-numerical-execution-release-v1" or release["scope"] != scope:
        raise ValueError("exact execution release schema/scope required")
    actual = list(sys.orig_argv if argv is None else argv)
    commands = release["commands"]
    if not isinstance(commands, list) or not commands or any(not isinstance(c, list) or not c or any(not isinstance(v, str) for v in c) for c in commands):
        raise ValueError("literal command arrays required")
    if any(c.count("ACTUAL_EXECUTION_RELEASE_SHA256") != 1 for c in commands):
        raise ValueError("one exact execution digest placeholder per command required")
    permitted = [[expected if arg == "ACTUAL_EXECUTION_RELEASE_SHA256" else arg for arg in c] for c in commands]
    if actual not in permitted:
        raise ValueError("actual orig_argv is not released")
    if not isinstance(release["source_bindings"], dict) or not release["source_bindings"]:
        raise ValueError("nonempty source closure required")
    for name, wanted in release["source_bindings"].items():
        if set(wanted) != {"sha256", "bytes"} or type(wanted["bytes"]) is not int or wanted["bytes"] < 0:
            raise ValueError("typed source binding required")
        if binding(relative_path(name))[1] != wanted:
            raise ValueError("execution source mismatch: " + name)
    seen = set()
    for wanted in release["inputs"]:
        if set(wanted) != {"path", "sha256", "bytes"} or type(wanted["bytes"]) is not int or wanted["path"] in seen:
            raise ValueError("unique typed input binding required")
        seen.add(wanted["path"])
        if binding(relative_path(wanted["path"]))[1] != {k: wanted[k] for k in ("sha256", "bytes")}:
            raise ValueError("execution input mismatch")
    return release, dict(path=str(Path(path).resolve()), **ref)


def load_hybrid(release):
    name = "experiments/m194g-larger-pupil/hybrid.py"
    raw, ref = binding(ROOT / name)
    if release["source_bindings"].get(name) != ref:
        raise ValueError("actual hybrid must be in released source closure")
    spec = importlib.util.spec_from_loader("m194g_author_hybrid", loader=None, origin=str(ROOT / name))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(ROOT / name)
    module.__checked_source__ = ref
    sys.modules[spec.name] = module
    exec(compile(raw, module.__file__, "exec"), module.__dict__)
    return module


def require_source_closure(H, release, scripts):
    required = {"experiments/m194g-larger-pupil/" + name for name in ("hybrid.py", "geometry.py", "pinned-loader.py", *scripts)}
    required.update(Path(ref["path"]).relative_to(ROOT).as_posix() for ref in H.BOUND.bindings.values())
    if not required <= set(release["source_bindings"]):
        raise ValueError("execution source closure omits an actual compiler/import input")
    needed_inputs = {"experiments/m194g-larger-pupil/" + name for name in
                     ("component-population.json", "fixture.json", "numerical-implementation-release-1.json")}
    if not needed_inputs <= {ref["path"] for ref in release["inputs"]}:
        raise ValueError("execution release omits an actual registered input")


def snapshot_sources(H, release, output, name):
    sources = H.source_bindings(extra=[Path(__file__)])
    for rel, expected in release["source_bindings"].items():
        path = relative_path(rel)
        raw, actual = binding(path)
        if actual != expected:
            raise ValueError("released source changed: " + rel)
        sources[str(path)] = dict(path=str(path), **actual)
    normalized = {str(Path(path).relative_to(ROOT)).replace("\\", "/"): {k: ref[k] for k in ("sha256", "bytes")}
                  for path, ref in sources.items()}
    target = Path(output) / name
    target.mkdir()
    for rel, wanted in normalized.items():
        raw, actual = binding(ROOT / rel)
        if actual != wanted:
            raise ValueError("source changed during snapshot")
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
    return normalized


def capture_after(H, release, output):
    try:
        return snapshot_sources(H, release, output, "sources-after"), None
    except Exception:
        return None, traceback.format_exc()


def component_call(H, catalog, case, arm, method, phase, fault, meter, output, rows):
    if phase not in ("baseline", "fault", "restored", "cache-prime") or arm not in case["author_arms"] or method not in case["author_methods"]:
        raise ValueError("registered component phase/arm/method required")
    if (phase == "baseline") != (fault is None):
        raise ValueError("explicit fault lineage required outside baseline")
    scene, frame, inputs = H.resolve_case(catalog, case)
    row = dict(case_id=case["id"], group=case["group"], call=case["call"], arm=arm, method=method,
               phase=phase, fault_id=None if fault is None else fault["id"], inputs=inputs,
               status="refused", value_e=None, branch=None, receipt=None, error=None,
               work_before=meter.receipt(), work_after=None)
    try:
        integrator = H.FALLBACK.integrator_for(arm)
        actual_fault = fault if phase == "fault" else None
        if method == "frozen-point":
            value, receipt = H.render_point(scene, frame, case["native_xy"], integrator, meter, fault=actual_fault)
        else:
            value, receipt = H.render_cell(scene, frame, case["native_xy"], integrator, meter,
                                           analytic=method == "analytic-enabled", fault=actual_fault)
        if not math.isfinite(value):
            raise ValueError("finite component value required")
        row.update(status="returned", value_e=value, branch=receipt["branch"], receipt=receipt)
    except Exception:
        row["error"] = traceback.format_exc()
    row["work_after"] = meter.receipt()
    rows.append(row)
    H.write_json(output / "component-rows" / f"{len(rows)-1:04d}.json", row)
    meter.check()  # A resource refusal stops the batch even if the row caught it.
    return row


def same_payload(H, left_path, right_path, inputs, meter):
    """The actual consumer reopens and validates both inputs and four payloads."""
    left, arrays = H.read_frame(left_path, inputs, meter)
    del arrays
    right, arrays = H.read_frame(right_path, inputs, meter)
    del arrays
    for name in left["arrays"]:
        a = Path(left_path).parent / left["arrays"][name]["path"]
        b = Path(right_path).parent / right["arrays"][name]["path"]
        with a.open("rb") as first, b.open("rb") as second:
            while True:
                x, y = first.read(65536), second.read(65536)
                if x != y:
                    raise ValueError("actual payload differs: " + name)
                if not x:
                    break
                meter.check()
    return True


def persist_mutation(H, source, arrays, output, meter):
    output.mkdir()
    record = copy.deepcopy(source)
    for name, array in zip(("scalar", "branch", "fallback_indices", "fallback_diagnostics"), arrays):
        old = record["arrays"][name]
        path = output / old["path"]
        H.np.save(path, array, allow_pickle=False)
        record["arrays"][name] = H.array_ref(path, array, output)
    H.write_json(output / "receipt.json", record)
    meter.check()
    return output / "receipt.json"


def observer_controls(H, catalog, meter, output, sources, checks):
    population = catalog["observer_population"]
    records = []
    baseline = {}
    source_digest = H.digest(sources)
    for execution, setting in enumerate(population["executions"]):
        meter.observer(setting["observer"])
        before = meter.receipt()
        rows = []
        for arm in population["arms"]:
            for index, focus in zip(population["frame_indices"], population["inverse_foci"]):
                scene = H.scene_from(population["scene"])
                frame = H.frame_from(dict(index=index, inverse_focus=focus, K=population["K"], forward_similarity=population["forward_similarity"]))
                ref = H.render_frame(scene, frame, population["width"], population["height"], H.FALLBACK.integrator_for(arm), meter,
                                     output / f"observer-{execution}" / f"{arm}-{index}", traversal=setting["traversal"], source_set=source_digest)
                path = Path(ref["path"])
                receipt = H.strict_load(path, ref["sha256"])
                inputs = receipt["inputs"]
                _, arrays = H.read_frame(path, inputs, meter, expected_hash=ref["sha256"])
                for branch, (x, y) in population["branch_witnesses"].items():
                    checks.append(dict(id=f"observer-{execution}-{arm}-{index}-branch-{branch}", pass_=int(arrays[1][y, x]) == H.BRANCHES[branch]))
                del arrays
                key = (arm, index)
                if execution == 0:
                    baseline[key] = (path, inputs)
                else:
                    same_payload(H, baseline[key][0], path, inputs, meter)
                rows.append(dict(arm=arm, frame_index=index, receipt=H.file_ref(path, output)))
        after = meter.receipt()
        collected = {k: after["hybrid_collection"].get(k, 0) - before["hybrid_collection"].get(k, 0)
                     for k in set(before["hybrid_collection"]) | set(after["hybrid_collection"])}
        collected = {k: v for k, v in collected.items() if v}
        hooks = after["hybrid_hook_calls"] - before["hybrid_hook_calls"]
        fallback_hooks = after["optional_hook_calls"] - before["optional_hook_calls"]
        events = after["observer_events"] - before["observer_events"]
        if setting["observer"] == "off":
            live = hooks == fallback_hooks == events == 0 and not collected
        elif setting["observer"] == "placebo":
            live = hooks > 0 and fallback_hooks > 0 and events == 0 and not collected
        else:
            required = ["wave:" + b + ":" + d for b in ("foreground", "background") for d in ("zero-defocus", "nonzero-defocus")]
            signed = ["signed-wave:foreground:negative", "signed-wave:foreground:zero", "signed-wave:foreground:positive",
                      "signed-wave:background:zero", "signed-wave:background:positive"]
            live = hooks > 0 and fallback_hooks > 0 and events > 0 and all(collected.get(k, 0) > 0 for k in required + signed)
        checks.append(dict(id=f"observer-{execution}-actual-hook-power", pass_=live))
        records.append(dict(execution=execution, observer=setting["observer"], traversal=setting["traversal"],
                            frames=rows, work_before=before, work_after=after,
                            hybrid_hook_calls=hooks, fallback_hook_calls=fallback_hooks, collected_array_events=events,
                            hybrid_collection=collected))
        H.write_json(output / f"observer-{execution}.json", records[-1])

    meter.observer("count")
    path, inputs = baseline[("primary", 2)]
    source, arrays = H.read_frame(path, inputs, meter)
    # Actual written mutations are coherently rehashed: equality/semantics must
    # reject them without relying on an obsolete outer SHA.
    mutations = output / "payload-mutations"
    mutations.mkdir()
    def exercise(name, change, wanted, semantic=False):
        changed = [a.copy() for a in arrays]
        meter.watch(*changed)
        change(changed)
        candidate = persist_mutation(H, source, changed, mutations / name, meter)
        error = None
        try:
            if semantic:
                _, loaded = H.read_frame(candidate, inputs, meter)
                del loaded
            else:
                same_payload(H, path, candidate, inputs, meter)
        except ValueError as exc:
            error = repr(exc)
        checks.append(dict(id="payload-" + name, pass_=error is not None and wanted in error, refusal=error,
                           candidate=H.file_ref(candidate, output)))
        same_payload(H, path, path, inputs, meter)
    x, y = population["scalar_and_diagnostic_fault_site"]["native_xy"]
    index = y * population["width"] + x
    sparse = int(H.np.flatnonzero(arrays[2] == index)[0])
    if len(arrays[2]) < 2:
        raise ValueError("sparse duplicate/unsorted control lacks two real numerical sites")
    exercise("scalar-plus-one", lambda a: a[0].__setitem__((y, x), a[0][y, x] + 1.0), "actual payload differs: scalar")
    exercise("delta-plus-point01", lambda a: a[3].__setitem__((sparse, 3), a[3][sparse, 3] + .01), "actual payload differs: fallback_diagnostics")
    exercise("missing-row", lambda a: (a.__setitem__(2, H.np.delete(a[2], sparse)), a.__setitem__(3, H.np.delete(a[3], sparse, axis=0))), "fallback index set", True)
    exercise("analytic-row", lambda a: a[2].__setitem__(0, 0), "fallback index set", True)
    exercise("duplicate-index", lambda a: a[2].__setitem__(1, a[2][0]), "sorted unique", True)
    exercise("unsorted-index", lambda a: a.__setitem__(2, a[2][::-1].copy()), "sorted unique", True)
    exercise("invalid-branch", lambda a: a[1].__setitem__((0, 0), 3), "complete valid branch", True)
    restored = persist_mutation(H, source, arrays, mutations / "restored", meter)
    same_payload(H, path, restored, inputs, meter)
    checks.append(dict(id="payload-reopened-restored", pass_=True, receipt=H.file_ref(restored, output)))
    changed_inputs = copy.deepcopy(inputs)
    changed_inputs["scene"]["foreground"]["constant"] += 1
    error = None
    try:
        H.read_frame(path, changed_inputs, meter)
    except ValueError as exc:
        error = repr(exc)
    checks.append(dict(id="payload-changed-input", pass_=error is not None and "input/schema binding" in error, refusal=error))
    del arrays
    # Same actual traversal consumer, with the registered omission/duplicate.
    scene = H.scene_from(population["scene"])
    frame = H.frame_from(dict(index=2, inverse_focus=population["inverse_foci"][2], K=population["K"], forward_similarity=population["forward_similarity"]))
    def broken_coordinates(width, height):
        return (i + 1 if i == index else i for i in range(width * height))
    error = None
    try:
        H.render_frame(scene, frame, 9, 6, H.FALLBACK.integrator_for("primary"), meter,
                       output / "coverage-mutation", coordinates=broken_coordinates, source_set=source_digest)
    except ValueError as exc:
        error = repr(exc)
    checks.append(dict(id="actual-coverage-omission-duplicate", pass_=error is not None and "duplicate" in error, refusal=error))
    meter.check()
    return records


def planned_component_calls(catalog):
    calls = []
    cases = {c["id"]: c for c in catalog["cases"]}
    def add(case, phase, fault_id=None):
        calls.append(dict(case_id=case["id"], arm=case["author_arms"][0], method=case["author_methods"][0], phase=phase, fault_id=fault_id))
    for case in catalog["cases"]:
        for arm in case["author_arms"]:
            for method in case["author_methods"]:
                calls.append(dict(case_id=case["id"], arm=arm, method=method, phase="baseline", fault_id=None))
    for fault in catalog["active_fault_targets"]:
        if fault["id"] in ("stale-frequency-cache", "cached-phase-zero"):
            prime = "transfer-negative-one-full" if fault["id"] == "stale-frequency-cache" else "coordinate-centre-phase-zero"
            add(cases[prime], "cache-prime", fault["id"])
        add(cases[fault["target_case"]], "fault", fault["id"])
        add(cases[fault["target_case"]], "restored", fault["id"])
    add(cases["transfer-zero-full"], "fault", "zero-over-zero")
    add(cases["transfer-zero-full"], "restored", "zero-over-zero")
    return calls


def run(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    H = meter = release = None
    before = after = None
    result = dict(schema="m194g-author-components-v1", status="UNCOMMISSIONED_NUMERICS", scope="components",
                  invocation=dict(orig_argv=list(sys.orig_argv), argv=list(sys.argv), executable=sys.executable,
                                  xoptions=dict(sys._xoptions), cwd=os.getcwd()),
                  execution_release=None, catalog=None, inputs_sha256=None, sources_before=None, sources_after=None,
                  source_capture_error=None, planned_calls=[], rows=[], observer_executions=[], checks=[],
                  error=None, work=None, runtime=None)
    try:
        release, result["execution_release"] = authorize(args.execution_release, args.execution_release_sha256, "components")
        H = load_hybrid(release)
        require_source_closure(H, release, ("author-components.py",))
        meter = H.Budget("components", "count", started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
        before = snapshot_sources(H, release, output, "sources-before")
        result["sources_before"] = before
        catalog = H.load_catalog()
        result["catalog"] = H.file_ref(H.HERE / "component-population.json")
        result["inputs_sha256"] = H.digest(catalog)
        (output / "component-rows").mkdir()
        cases = {c["id"]: c for c in catalog["cases"]}
        result["planned_calls"] = planned_component_calls(catalog)
        rows, checks = result["rows"], result["checks"]
        baseline = {}
        for planned in result["planned_calls"]:
            if planned["phase"] != "baseline":
                continue
            case = cases[planned["case_id"]]
            row = component_call(H, catalog, case, planned["arm"], planned["method"], "baseline", None, meter, output, rows)
            baseline[(case["id"], planned["arm"], planned["method"])] = row
            branch_ok = planned["method"] != "analytic-enabled" or "expected_branch" not in case or row["branch"] == case["expected_branch"]
            checks.append(dict(id="baseline-" + str(len(rows)-1), pass_=row["status"] == "returned" and branch_ok))
        checks.append(dict(id="baseline-complete299", pass_=len(rows) == 299))

        for spec in catalog["active_fault_targets"]:
            case = cases[spec["target_case"]]
            arm, method = case["author_arms"][0], case["author_methods"][0]
            fault = dict(id=spec["id"])
            if spec["id"] in ("stale-frequency-cache", "cached-phase-zero"):
                prime_id = "transfer-negative-one-full" if spec["id"] == "stale-frequency-cache" else "coordinate-centre-phase-zero"
                prime_case = cases[prime_id]
                prime = component_call(H, catalog, prime_case, prime_case["author_arms"][0], "analytic-enabled", "cache-prime", fault, meter, output, rows)
                if prime["status"] != "returned":
                    raise ValueError("registered cache prime refused")
                wave = prime["receipt"]["transfer"]["waves"][0]
                fault["primed_key" if spec["id"] == "stale-frequency-cache" else "primed_phase"] = wave["cache_key" if spec["id"] == "stale-frequency-cache" else "field_phase"]
            bad = component_call(H, catalog, case, arm, method, "fault", fault, meter, output, rows)
            good = component_call(H, catalog, case, arm, method, "restored", fault, meter, output, rows)
            original = baseline[(case["id"], arm, method)]
            powered = all(r["status"] == "returned" for r in (bad, good, original))
            delta = abs(bad["value_e"] - good["value_e"]) if powered else None
            checks.append(dict(id="fault-" + spec["id"], pass_=powered and delta > spec["required_abs_value_discrepancy_gt_e"] and good["value_e"] == original["value_e"], abs_delta_e=delta))

        case = cases["transfer-zero-full"]
        bad = component_call(H, catalog, case, "primary", "analytic-enabled", "fault", dict(id="zero-over-zero"), meter, output, rows)
        good = component_call(H, catalog, case, "primary", "analytic-enabled", "restored", dict(id="zero-over-zero"), meter, output, rows)
        checks.append(dict(id="refusal-zero-over-zero", pass_=bad["status"] == "refused" and "nonfinite" in bad["error"] and good["status"] == "returned"))
        malformed = copy.deepcopy(catalog)
        malformed["cases"][1] = copy.deepcopy(malformed["cases"][0])
        error = None
        try:
            H.validate_catalog(malformed)
        except ValueError as exc:
            error = repr(exc)
        checks.append(dict(id="refusal-duplicate-case", pass_=error is not None and "unique150-case" in error, refusal=error))
        H.validate_catalog(H.load_catalog())
        retained = cases["legacy-30-4"]["retained_reference"]["array"]
        raw = H.checked_bytes(H.ROOT / retained["path"], retained["sha256"])
        mutant = output / "source-byte-mutant.npy"
        altered = bytearray(raw)
        altered[-1] ^= 1
        mutant.write_bytes(altered)
        error = None
        try:
            H.checked_bytes(mutant, retained["sha256"])
        except ValueError as exc:
            error = repr(exc)
        H.checked_bytes(H.ROOT / retained["path"], retained["sha256"])
        checks.append(dict(id="refusal-source-digest", pass_=error is not None and "binding mismatch" in error, refusal=error, mutated_file=H.file_ref(mutant, output)))
        actual_calls = [{k: row[k] for k in ("case_id", "arm", "method", "phase", "fault_id")} for row in rows]
        if actual_calls != result["planned_calls"]:
            raise ValueError("complete ordered baseline/fault/restored/cache call population required")
        result["observer_executions"] = observer_controls(H, catalog, meter, output, before, checks)
        if not all(c["pass_"] for c in checks):
            raise ValueError("one or more author component controls failed; retain every result")
        result["status"] = "PASS_AUTHOR_COMPONENTS"
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        if H is not None and release is not None:
            after, capture_error = capture_after(H, release, output)
            result["sources_after"], result["source_capture_error"] = after, capture_error
            if after != before or capture_error is not None:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = "source closure changed or final snapshot failed"
        if meter is not None:
            try:
                meter.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
            result["work"] = meter.receipt()
        result["runtime"] = runtime_record(H)
        write_json(output / "result.json", result)
        # Persistence is inside the final cumulative budget too. A failed last
        # check rewrites an explicit failed result, preserving the first error.
        if meter is not None:
            try:
                meter.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
            result["work"] = meter.receipt()
            result["runtime"] = runtime_record(H)
            write_json(output / "result.json", result)
            try:
                meter.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
                result["work"] = meter.receipt()
                write_json(output / "result.json", result)
    print(result["status"], flush=True)
    return 0 if result["status"] == "PASS_AUTHOR_COMPONENTS" else 1


def parser():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--execution-release", required=True)
    p.add_argument("--execution-release-sha256", required=True)
    return p


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
