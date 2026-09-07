"""Capture the actual NumPy/runtime bytes before any released software-noise draw."""
import time
START_CPU, START_WALL = time.process_time(), time.monotonic()
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]


def binding(path):
    raw = path.read_bytes()
    return raw, dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def check_time():
    if time.process_time()-START_CPU > 30 or time.monotonic()-START_WALL > 60:
        raise ValueError("runtime capture exceeded 30CPU/60wall seconds")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw, release_binding = binding(args.release)
    if release_binding["sha256"] != args.release_sha256:
        raise ValueError("external runtime release pin differs")
    release = json.loads(raw)
    if (set(release) != {"schema", "scope", "source_bindings", "inputs", "commands"}
            or release["schema"] != "m194g-numerical-execution-release-v1"
            or release["scope"] != "noise-runtime-snapshot" or release["inputs"] != []):
        raise ValueError("runtime release scope/keys differ")
    expected = [[args.release_sha256 if x == "ACTUAL_EXECUTION_RELEASE_SHA256" else x for x in row] for row in release["commands"]]
    if list(sys.orig_argv) not in expected:
        raise ValueError("actual runtime capture command not released")
    sources = {}
    for name, wanted in release["source_bindings"].items():
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError("runtime source outside repository")
        data, actual = binding(path)
        if actual != wanted:
            raise ValueError("runtime capture source changed: "+name)
        sources[name] = data
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    core_name = "experiments/m194g-larger-pupil/software-noise.py"
    import_names = (core_name, "experiments/m194g-larger-pupil/software-noise-authority.py",
                    "experiments/m194g-larger-pupil/independent-noise-reader.py")
    if own not in sources or any(name not in sources for name in import_names):
        raise ValueError("actual runtime capture code omitted")
    args.output.mkdir(parents=True, exist_ok=False)
    modules = []
    # Match the released runner's startup import order before RuntimeGuard.
    # These imports define functions only; no sampler or encoder is called.
    for index, name in enumerate(import_names):
        spec = importlib.util.spec_from_loader("m194g_runtime_capture_"+str(index), loader=None, origin=str(ROOT/name))
        module = importlib.util.module_from_spec(spec)
        module.__file__ = str(ROOT/name)
        sys.modules[spec.name] = module
        exec(compile(sources[name], module.__file__, "exec"), module.__dict__)
        modules.append(module)
    core = modules[0]
    runtime = core.runtime_manifest()
    check_time()
    destination = args.output/"runtime.json"
    destination.write_bytes(core.canonical_bytes(runtime)+b"\n")
    if core.runtime_manifest() != runtime:
        raise ValueError("actual runtime changed through capture")
    for name, data in sources.items():
        saved = args.output/"source-snapshot"/name
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(data)
    receipt = dict(schema="m194g-noise-runtime-capture-v1", status="COMPLETE_RUNTIME_SNAPSHOT_ONLY",
                   invocation=list(sys.orig_argv), release_sha256=args.release_sha256,
                   sources=release["source_bindings"], runtime=dict(path=destination.resolve().relative_to(ROOT).as_posix(), **binding(destination)[1]),
                   cpu_seconds=time.process_time()-START_CPU, wall_seconds=time.monotonic()-START_WALL,
                   scope="runtime and source bytes only; no noise-law or emitted-CFA admission", error=None)
    result_path = args.output/"result.json"
    try:
        result_path.write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
        for name, data in sources.items():
            if (ROOT/name).read_bytes() != data or (args.output/"source-snapshot"/name).read_bytes() != data:
                raise ValueError("capture source changed through final persistence")
        if core.runtime_manifest() != runtime or binding(destination)[1] != {k: receipt["runtime"][k] for k in ("sha256", "bytes")}:
            raise ValueError("runtime bytes changed through final persistence")
        check_time()
    except Exception as original:
        receipt["status"] = "UNCOMMISSIONED_RUNTIME_SNAPSHOT"
        receipt["error"] = traceback.format_exc()
        try:
            result_path.write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
        except Exception as secondary:
            original.add_note("Failed to persist refused runtime snapshot: "+repr(secondary))
        raise
    print(json.dumps(receipt), flush=True)


if __name__ == "__main__":
    main()
