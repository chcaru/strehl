"""One preregistered private counter profile mode; never intended admission."""
from __future__ import annotations
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"
import argparse
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
E_DIR = HERE.parent / "m194e-joint-pupil"
PROTOCOL = HERE / "counter-profile-preregister.md"
PROTOCOL_SHA = "eadf399b5998fa4d458b44ea565e1f27d29eaaab39f65751c25739df67412f3e"
PINS = {
    HERE / "preflight.py": "829669612359e5f60a1610fbc36604eb4cef5647911df604124de9e13160b485",
    HERE / "geometry.py": "24b812071b8b6189423b9792a22c55abd9a4f4a78921a9d558ab24489f1923b3",
    HERE / "pinned-loader.py": "222fab4a932fe236c120d8a48e4521747474e2ef57ba58781bf5c59f644f4f76",
    E_DIR / "model.py": "a74cd9bd61ea2f717a185e86f725b5ed192431056a447581db0f8562cf9f70b8",
    E_DIR / "render.py": "487c1727ca3aab05dd66a7056fb368712ccaabbbe604818fdc8b47eda77b6e97",
    PROTOCOL: PROTOCOL_SHA,
}
ARMS = ("primary", "angle-refined", "cell-refined")
MODES = ("off", "count", "placebo", "mutated-cut")


def read_bound(path, expected=None):
    path = Path(path).resolve(strict=True)
    with path.open("rb") as stream:
        raw = stream.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("bounded source/receipt exceeds1MiB")
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError("source/receipt hash mismatch: " + str(path))
    return raw, dict(path=str(path), sha256=digest, bytes=len(raw))


def write_bytes(path, raw):
    with Path(path).open("wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return dict(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def write_json(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf-8")
    return write_bytes(path, raw)


def sources():
    paths = dict(PINS)
    paths[Path(__file__).resolve()] = None
    return {str(path.resolve()): read_bound(path, pin)[1] for path, pin in paths.items()}


def load_counter():
    path = HERE / "preflight.py"
    raw, binding = read_bound(path, PINS[path])
    spec = importlib.util.spec_from_loader("m194g_profile_counter", loader=None, origin=str(path))
    value = importlib.util.module_from_spec(spec)
    value.__file__ = str(path)
    value.__checked_source__ = binding
    sys.modules[spec.name] = value
    exec(compile(raw, str(path), "exec"), value.__dict__)
    if value.LOADER_IMPORT_SHA != PINS[HERE / "pinned-loader.py"]:
        raise ValueError("actual loader import mismatch")
    if value.geometry.__checked_source__["sha256"] != PINS[HERE / "geometry.py"]:
        raise ValueError("actual geometry import mismatch")
    return value


@contextmanager
def patch(obj, name, replacement):
    original = getattr(obj, name)
    setattr(obj, name, replacement)
    try:
        yield
    finally:
        setattr(obj, name, original)


class IntentionalRadianceTrap(RuntimeError):
    pass


def make_inputs(model):
    scene = model.Scene(model.Field(15000), model.Field(12000), (1, 2), (1, .25), 2)
    similarity = model.Similarity(2, 0, (.5, -.5), (1.25, -.75))
    frames = tuple(model.Frame(i, focus, 2, similarity)
                   for i, focus in enumerate((.5, .75, 1, 1.25, 1.5)))
    record = dict(width=9, height=6, scene=asdict(scene), frames=[asdict(f) for f in frames], arms=list(ARMS))
    return scene, frames, record


def geometry_payload(count, inputs):
    """Complete successful geometry record; observer/resource fields excluded."""
    required = ("status", "width", "height", "frame_indices", "arms", "frames",
                "completed_frames", "completed_cells", "ordered_stream_sha256")
    result = {key: count[key] for key in required}
    result.update(schema="m194g-profile-geometry-payload-v1", inputs=inputs,
                  total_points=sum(row["low_points"] + row["high_points"] for row in count["frames"]),
                  total_angular_nodes=sum(row["angular_nodes"] for row in count["frames"]))
    return result


def profile_artifacts(profiler, output, counter, bound):
    """Complete tables, not a top-functions extract. Called with collection off."""
    import pstats
    binary = output / "profile.pstats"
    profiler.dump_stats(str(binary))
    buffer = io.StringIO()
    # Python3.12 Stats rejects an empty profile. A never-enabled placebo is
    # intentionally empty; do not turn its absence of calls into a false error.
    profiler.create_stats()
    entries = profiler.stats
    if entries:
        stats = pstats.Stats(profiler, stream=buffer)
        stats.sort_stats("cumulative").print_stats()
    else:
        buffer.write("No collected calls: profiler was constructed with collection disabled.\n")
    text_ref = write_bytes(output / "profile-functions.txt", buffer.getvalue().encode("utf-8"))
    table = []
    for key, values in sorted(entries.items()):
        primitive, calls, own_time, cumulative, callers = values
        table.append(dict(filename=key[0], line=key[1], function=key[2], primitive_calls=primitive,
                          total_calls=calls, own_seconds=own_time, cumulative_seconds=cumulative,
                          callers=[dict(filename=caller[0], line=caller[1], function=caller[2],
                                        values=list(detail) if isinstance(detail, tuple) else detail)
                                   for caller, detail in sorted(callers.items())]))
    table_ref = write_json(output / "profile-functions.json", table)
    def calls_for(filename, name):
        return sum(row["total_calls"] for row in table
                   if Path(row["filename"]).as_posix() == Path(filename).as_posix() and row["function"] == name)
    liveness = {name: calls_for(counter.__file__, name)
                for name in ("count_geometry", "point_cuts", "_stream", "check")}
    liveness["angular_cuts"] = calls_for(bound.render.__file__, "angular_cuts")
    raw = binary.read_bytes()
    return dict(binary=dict(path=str(binary.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)),
                function_table=table_ref, text_table=text_ref, function_count=len(table),
                total_calls=sum(row["total_calls"] for row in table), required_function_calls=liveness)


def baseline_payload(path, expected_hash, before, input_record):
    if not isinstance(expected_hash, str) or len(expected_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_hash):
        raise ValueError("external baseline result SHA256 required")
    raw, binding = read_bound(path, expected_hash.lower())
    record = json.loads(raw)
    if (record.get("schema") != "m194g-counter-profile-v1" or record.get("status") != "PASS_PROFILE_MODE"
            or record.get("mode") != "off" or record.get("sources_before") != before
            or record.get("sources_after") != before or record.get("inputs") != input_record
            or record.get("protocol", {}).get("sha256") != PROTOCOL_SHA):
        raise ValueError("baseline is not the same-source completed off mode")
    payload_ref = record["payload"]
    payload_path = Path(path).resolve().parent / "geometry-payload.json"
    payload_bytes, actual = read_bound(payload_path, payload_ref["sha256"])
    if actual != payload_ref or canonical(json.loads(payload_bytes)) != payload_bytes:
        raise ValueError("baseline payload binding/canonical encoding mismatch")
    payload = json.loads(payload_bytes)
    if (payload["inputs"] != input_record or payload["status"] != "PASS_COST_ONLY"
            or payload["completed_frames"] != 15 or payload["completed_cells"] != 810):
        raise ValueError("baseline private population mismatch")
    return payload_bytes, payload, dict(result=binding, payload=actual)


def run(mode, output, baseline_result=None, baseline_result_sha256=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-counter-profile-v1", status="running", mode=mode,
                  scope="private geometry attribution only; no full cost/radiance admission",
                  invocation=dict(orig_argv=sys.orig_argv, argv=sys.argv, xoptions=sys._xoptions,
                                  executable=sys.executable, cwd=str(Path.cwd())),
                  started_utc=datetime.now(timezone.utc).isoformat(), checks=[])
    budget, profiler, before, counter, bound = None, None, None, None, None
    profiler_enabled = False
    def check(name, passed, detail=None):
        result["checks"].append(dict(name=name, passed=bool(passed), detail=detail))
        if not passed:
            raise AssertionError(name)
    try:
        if (mode not in MODES or (mode == "off") != (baseline_result is None)
                or (mode == "off") != (baseline_result_sha256 is None)):
            raise ValueError("off forbids baseline; other modes require completed off result")
        before = sources()
        result["sources_before"] = before
        result["protocol"] = before[str(PROTOCOL.resolve())]
        counter = load_counter()
        limits = dict(counter.DEFAULT_LIMITS, whole_run_cpu_seconds=10., whole_run_wall_seconds=20.)
        budget = counter.Budget(limits, started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
        bound = counter.loader.load_frozen()
        budget.check()
        result["actual_imports"] = dict(counter=counter.__checked_source__,
                                       loader_sha256=counter.LOADER_IMPORT_SHA,
                                       geometry=counter.geometry.__checked_source__, frozen=bound.bindings)
        result["versions"] = dict(python=sys.version, numpy=counter.np.__version__)
        result["thread_environment"] = {name: os.environ.get(name) for name in
                                       ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
        snapshot = output / "source"
        snapshot.mkdir()
        for binding in before.values():
            raw, actual = read_bound(binding["path"], binding["sha256"])
            if binding != actual:
                raise ValueError("source snapshot binding changed")
            write_bytes(snapshot / Path(binding["path"]).name, raw)
        budget.check()
        scene, frames, inputs = make_inputs(bound.model)
        result["inputs"] = inputs
        prior_bytes = prior_payload = None
        if baseline_result is not None:
            prior_bytes, prior_payload, prior_refs = baseline_payload(baseline_result, baseline_result_sha256, before, inputs)
            result["baseline"] = prior_refs
        if mode in ("count", "placebo"):
            import cProfile
            profiler = cProfile.Profile()
        result["profiler"] = dict(constructed=profiler is not None, collection_enabled=mode == "count")
        trap_rows = {}
        mutation = dict(applied=False, angular_calls=0)
        count = {}
        result["count"] = count
        traps = [(bound.model.Field, "evaluate"), (bound.model, "evaluate_rays"),
                 (bound.render, "render_points"), (bound.render, "render_cell"),
                 (bound.render, "render_frame"), (bound.render, "angular_integrand"),
                 (bound.render, "field_radial")]
        with ExitStack() as stack:
            phase = ["intentional-direct-liveness"]
            for index, (owner, name) in enumerate(traps):
                label = f"{index}:{name}"
                trap_rows[label] = dict(intentional_calls=0, genuine_calls=0)
                def trap(*_args, _label=label, **_kwargs):
                    field = "intentional_calls" if phase[0] == "intentional-direct-liveness" else "genuine_calls"
                    trap_rows[_label][field] += 1
                    raise IntentionalRadianceTrap(_label)
                stack.enter_context(patch(owner, name, trap))
                try:
                    getattr(owner, name)()
                except IntentionalRadianceTrap as exc:
                    check("direct trap liveness " + label, str(exc) == label)
                else:
                    check("direct trap liveness " + label, False)
            phase[0] = "actual-counter"
            if mode == "mutated-cut":
                original = bound.render.angular_cuts
                def changed_cut(height, radius, alpha, state, include_ladder=True):
                    cuts = original(height, radius, alpha, state, include_ladder)
                    mutation["angular_calls"] += 1
                    if not mutation["applied"] and len(cuts) > 2:
                        changed = cuts[:1] + cuts[2:]
                        mutation.update(applied=True, actual_call=mutation["angular_calls"], height=height,
                                        radius=radius, alpha=alpha, mask_state=state,
                                        original_cuts=list(cuts), changed_cuts=list(changed))
                        return changed
                    return cuts
                stack.enter_context(patch(bound.render, "angular_cuts", changed_cut))
            budget.check()
            if mode == "count":
                profiler.enable()
                profiler_enabled = True
            try:
                counter.count_geometry(bound, scene, frames, 9, 6, ARMS, budget, result=count)
            finally:
                if profiler_enabled:
                    profiler.disable()
                    profiler_enabled = False
                result["radiance_traps"] = trap_rows
                result["mutation"] = mutation
        budget.check()
        counter.validate_completion(count, dict(width=9, height=6, frame_indices=list(range(5)), arms=list(ARMS)), budget)
        check("complete actual private population", count["completed_cells"] == 810 and count["completed_frames"] == 15)
        check("genuine radiance call count zero", all(row == dict(intentional_calls=1, genuine_calls=0) for row in trap_rows.values()))
        if profiler is not None:
            artifacts = profile_artifacts(profiler, output, counter, bound)
            result["profiler"].update(artifacts)
            if mode == "count":
                check("count reaches every required actual function", all(v > 0 for v in artifacts["required_function_calls"].values()), artifacts["required_function_calls"])
            else:
                check("constructed placebo collects no calls", artifacts["total_calls"] == 0 and artifacts["function_count"] == 0)
        else:
            check("off/mutation construct no profiler", profiler is None)
        budget.check()
        payload = geometry_payload(count, inputs)
        payload_bytes = canonical(payload)
        result["payload"] = write_bytes(output / "geometry-payload.json", payload_bytes)
        if mode in ("count", "placebo"):
            check("canonical payload byte-identical to off", payload_bytes == prior_bytes)
            check("ordered geometry digest identical to off", payload["ordered_stream_sha256"] == prior_payload["ordered_stream_sha256"])
        elif mode == "mutated-cut":
            check("first actual multi-interval cut removed", mutation["applied"]
                  and len(mutation["original_cuts"]) == len(mutation["changed_cuts"]) + 1
                  and all(a < b for a, b in zip(mutation["changed_cuts"], mutation["changed_cuts"][1:])))
            check("equality comparison rejects actual mutant", payload_bytes != prior_bytes
                  and payload["ordered_stream_sha256"] != prior_payload["ordered_stream_sha256"])
            check("actual nominal work decreased by one primary interval", payload["total_angular_nodes"] == prior_payload["total_angular_nodes"] - 48
                  and payload["total_points"] == prior_payload["total_points"])
        budget.check()
        bound.assert_unchanged()
        after = sources()
        result["sources_after"] = after
        check("all bound source bytes unchanged", before == after)
        budget.check()
        result["work"] = budget.receipt()
        result["status"] = "PASS_PROFILE_MODE"
    except Exception as exc:
        if profiler_enabled:
            profiler.disable()
        result.update(status="UNCOMMISSIONED_PROFILE", error=repr(exc), traceback=traceback.format_exc())
        if profiler is not None and counter is not None and bound is not None and "function_table" not in result.get("profiler", {}):
            try:
                result.setdefault("profiler", {}).update(profile_artifacts(profiler, output, counter, bound))
            except Exception as profile_exc:
                result["profile_persistence_error"] = repr(profile_exc)
                result["profile_persistence_traceback"] = traceback.format_exc()
        if budget is not None:
            result["work"] = budget.receipt()
        try:
            result["sources_after"] = sources()
        except Exception as source_exc:
            result["sources_after_error"] = repr(source_exc)
            result["sources_after_traceback"] = traceback.format_exc()
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output / "result.json", result)
    print(json.dumps(dict(status=result["status"], mode=mode, output=str(output))), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--baseline-result", type=Path)
    parser.add_argument("--baseline-result-sha256")
    args = parser.parse_args()
    raise SystemExit(0 if run(args.mode, args.output, args.baseline_result, args.baseline_result_sha256)["status"] == "PASS_PROFILE_MODE" else 1)
