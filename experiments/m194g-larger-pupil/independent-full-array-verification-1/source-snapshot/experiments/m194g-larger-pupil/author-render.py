"""One separately released five-frame author arm; no component result is authority."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def load_controller(release_path, external_sha):
    # This stdlib-only bootstrap loads the exact controller bytes authorized by
    # the externally pinned release. Its strict parser/argv gate runs next,
    # before hybrid imports or any model/helper invocation.
    with Path(release_path).open("rb") as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != external_sha:
        raise ValueError("external release binding mismatch")
    release = json.loads(raw)
    rel = "experiments/m194g-larger-pupil/author-components.py"
    path = ROOT / rel
    with path.open("rb") as stream:
        source = stream.read(4 * 1024 * 1024 + 1)
    actual = dict(sha256=hashlib.sha256(source).hexdigest(), bytes=len(source))
    if len(source) > 4 * 1024 * 1024 or release["source_bindings"].get(rel) != actual:
        raise ValueError("released controller source required")
    spec = importlib.util.spec_from_loader("m194g_author_controller", loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[spec.name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def run(args):
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    C = H = meter = release = None
    result = dict(schema="m194g-author-render-v1", status="UNCOMMISSIONED_NUMERICS", scope="full-author-arm", arm=args.arm,
                  invocation=dict(orig_argv=list(sys.orig_argv), argv=list(sys.argv), executable=sys.executable,
                                  xoptions=dict(sys._xoptions), cwd=os.getcwd()),
                  execution_release=None, fixture=None, inputs_sha256=None, sources_before=None, sources_after=None,
                  source_capture_error=None, frames=[], error=None, work=None, runtime=None)
    try:
        C = load_controller(args.execution_release, args.execution_release_sha256)
        release, result["execution_release"] = C.authorize(args.execution_release, args.execution_release_sha256, "full-author-arm")
        H = C.load_hybrid(release)
        C.require_source_closure(H, release, ("author-components.py", "author-render.py"))
        meter = H.Budget("full-arm", "count", started_cpu=ENTRY_CPU, started_wall=ENTRY_WALL)
        before = C.snapshot_sources(H, release, output, "sources-before")
        result["sources_before"] = before
        fixture = H.strict_load(H.HERE / "fixture.json", H.FIXTURE_SHA)
        if fixture["schema"] != "m194g-expected-fixture-v1" or args.arm not in fixture["arms"]:
            raise ValueError("registered fixture/arm required")
        if fixture["frame_indices"] != list(range(5)) or any(type(i) is not int for i in fixture["frame_indices"]):
            raise ValueError("all five original frame indices required")
        result["fixture"] = H.file_ref(H.HERE / "fixture.json")
        result["inputs_sha256"] = H.digest(fixture)
        source_digest = H.digest(before)
        scene = H.scene_from(fixture["scene"])
        for index, focus in zip(fixture["frame_indices"], fixture["inverse_foci"]):
            frame = H.frame_from(dict(index=index, inverse_focus=focus, K=fixture["K"], forward_similarity=fixture["forward_similarity"]))
            ref = H.render_frame(scene, frame, fixture["width"], fixture["height"], H.FALLBACK.integrator_for(args.arm), meter,
                                 output / f"frame-{index}", source_set=source_digest)
            path = Path(ref["path"])
            record = H.strict_load(path, ref["sha256"])
            expected = H.normalized(dict(scene=H.asdict(scene), frame=H.asdict(frame), width=fixture["width"], height=fixture["height"], arm=args.arm, method="analytic-enabled"))
            _, arrays = H.read_frame(path, expected, meter, expected_hash=ref["sha256"])
            del arrays
            result["frames"].append(dict(frame_index=index, receipt=H.file_ref(path, output)))
            H.write_json(output / "progress.json", dict(status="running", arm=args.arm, frames=list(result["frames"]), work=meter.receipt()))
            print(f"completed {args.arm} frame {index}: {record['completed_cells']} cells", flush=True)
        if len(result["frames"]) != 5:
            raise ValueError("incomplete full arm")
        result["status"] = "COMPLETE_AUTHOR_FLOATS_UNCOMMISSIONED"
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        if C is not None and H is not None and release is not None:
            after, capture_error = C.capture_after(H, release, output)
            result["sources_after"], result["source_capture_error"] = after, capture_error
            if after != result["sources_before"] or capture_error:
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
        result["runtime"] = C.runtime_record(H, ENTRY_CPU, ENTRY_WALL) if C is not None else dict(
            cpu_seconds=time.process_time()-ENTRY_CPU, wall_seconds=time.monotonic()-ENTRY_WALL,
            python_version=sys.version, numpy_version=None, scipy_version=None,
            thread_environment={name: os.environ.get(name) for name in
                                ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")})
        path = output / "result.json"
        raw = (json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        with path.open("wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if meter is not None:
            try:
                meter.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
            result["work"] = meter.receipt()
            result["runtime"] = C.runtime_record(H, ENTRY_CPU, ENTRY_WALL)
            C.write_json(path, result)
            try:
                meter.check()
            except Exception:
                result["status"] = "UNCOMMISSIONED_NUMERICS"
                if result["error"] is None:
                    result["error"] = traceback.format_exc()
                result["work"] = meter.receipt()
                C.write_json(path, result)
    print(result["status"], flush=True)
    return 0 if result["status"] == "COMPLETE_AUTHOR_FLOATS_UNCOMMISSIONED" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=("primary", "angle-refined", "cell-refined"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--execution-release", required=True)
    parser.add_argument("--execution-release-sha256", required=True)
    raise SystemExit(run(parser.parse_args()))
