"""Source-bound build-only controller for the larger production bridge."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs"
PARENT = SOURCE.with_name("known-scene-benchmark.rs")


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for raw in iter(lambda: stream.read(65536), b""):
            h.update(raw)
    return h.hexdigest()


def file_binding(path):
    return dict(sha256=sha(path), bytes=Path(path).stat().st_size)


def file_ref(path):
    return dict(path=Path(path).resolve().relative_to(ROOT).as_posix(), **file_binding(path))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def strict(raw):
    def unique(items):
        out = {}
        for k, v in items:
            need(k not in out, "duplicate JSON key")
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=unique, parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def environment():
    values = {k: v for k, v in os.environ.items()
              if not k.upper().startswith("STREHL_") and k.upper() not in
              {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RAYON_NUM_THREADS", "CARGO_TARGET_DIR"}}
    return values


def sources():
    """Bind tracked crates plus this tree's explicit external Rust include forms.

    As in M194d, this is not a general Rust/cfg parser. Both test crates' sources
    are bound even when a dependency build omits their cfg(test) modules.
    """
    tracked = subprocess.check_output(["git", "--no-optional-locks", "ls-files", "-z",
                                       "crates", "Cargo.toml", "Cargo.lock"], cwd=ROOT)
    paths = {ROOT / p for p in tracked.decode("utf-8").split("\0") if p and (ROOT / p).is_file()}
    paths.add(SOURCE)
    pending = [(p, ROOT / "crates" / p.relative_to(ROOT).parts[1])
               for p in paths if p.suffix == ".rs"]
    seen = set()
    while pending:
        source, crate = pending.pop()
        if (source, crate) in seen:
            continue
        seen.add((source, crate))
        text = source.read_text(encoding="utf-8")
        targets = [(crate / relative.lstrip("/")).resolve() for relative in re.findall(
            r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)', text, re.M)]
        targets += [(source.parent / relative).resolve() for relative in
                    re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]', text, re.M)]
        for target in targets:
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError("invalid external Rust include " + str(target))
            paths.add(target)
            pending.append((target, crate))
    return {p.relative_to(ROOT).as_posix(): file_binding(p) for p in sorted(paths)}



def write_json(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+"\n").encode()
    need(len(raw) <= 4*1024*1024, "bounded build metadata")
    path.write_bytes(raw)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.release.open("rb") as f:
        raw = f.read(4*1024*1024+1)
    need(len(raw) <= 4*1024*1024 and hashlib.sha256(raw).hexdigest() == args.release_sha256, "build release pin/extent")
    release = strict(raw)
    need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands", "build_command"}
         and release["schema"] == "m194g-bridge-build-release-v1" and release["scope"] == "build-only", "build release schema/scope")
    commands = [[args.release_sha256 if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in row] for row in release["commands"]]
    need(list(sys.orig_argv) in commands, "actual build-controller invocation not released")
    before = sources()
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    required = {**before, own: file_binding(__file__)}
    need(required == release["source_bindings"], "exact compiled/controller source closure required")
    for ref in release["inputs"]:
        need(file_binding(ROOT/ref["path"]) == {k: ref[k] for k in ("sha256", "bytes")}, "build input changed")
    command = release["build_command"]
    need(command == ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir", "target/m194g-noisy-bridge", "--no-run", "--message-format=json-render-diagnostics"], "exact build command")
    output = args.output.resolve()
    need(output.is_relative_to(ROOT), "build output outside repository")
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m194g-bridge-build-v1", status="UNCOMMISSIONED_BUILD", invocation=list(sys.orig_argv),
                  execution_release=file_ref(args.release), command=command, sources_before=before,
                  sources_after=None, driver=file_ref(__file__), started_utc=datetime.now(timezone.utc).isoformat(),
                  ended_utc=None, wall_seconds=None, exit_code=None, compiler_artifact_message=None,
                  compiler_artifact=None, test_executable=None, test_listing=None, rebuilt_cli=False,
                  compiler_log=None, compiler_environment={k: environment().get(k) for k in
                       ("PATH", "RUSTUP_TOOLCHAIN", "RUSTUP_HOME", "CARGO_HOME", "RUSTC", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER")},
                  compiler_identity_scope="observed command/environment and source-to-artifact bytes; not a hermetic toolchain certificate",
                  error=None, finalization_errors=[])
    started = time.monotonic()
    log = output/"compiler.log"
    try:
        need(not (ROOT/"target/m194g-noisy-bridge").exists(), "first build target must be fresh")
        SOURCE.touch(); PARENT.touch()
        # Build only. Compiler output is retained directly rather than in a pipe
        # buffer. The build has its own1800-second operational wall allowance.
        with log.open("xb") as stream:
            proc = subprocess.run(command, cwd=ROOT, env=environment(), stdout=stream,
                                  stderr=subprocess.STDOUT, timeout=1800, check=False)
        result["exit_code"] = proc.returncode
        need(log.stat().st_size <= 64*1024*1024, "compiler log exceeds64MiB operational cap")
        result["compiler_log"] = file_ref(log)
        artifacts = []
        rebuilt = False
        with log.open("rb") as stream:
            for line in stream:
                rebuilt |= b"Compiling strehl-cli" in line
                if line.startswith(b"{"):
                    value = strict(line)
                    if (value.get("reason") == "compiler-artifact" and value.get("executable")
                            and value.get("target", {}).get("name") == "strehl"
                            and Path(value.get("target", {}).get("src_path", "")).resolve() == ROOT/"crates/strehl-cli/src/main.rs"
                            and Path(value.get("manifest_path", "")).resolve() == ROOT/"crates/strehl-cli/Cargo.toml"
                            and value.get("package_id") == "path+"+(ROOT/"crates/strehl-cli").as_uri()+"#0.0.0"
                            and value.get("profile", {}).get("test") is True):
                        artifacts.append(value)
        result["rebuilt_cli"] = rebuilt
        need(proc.returncode == 0 and rebuilt and len(artifacts) == 1, "successful fresh compiler artifact required")
        original = Path(artifacts[0]["executable"]).resolve()
        need(original.is_relative_to(ROOT), "compiler artifact outside workspace")
        destination = output/"noise-pupil-bridge-tests.exe"
        result["compiler_artifact_message"] = artifacts[0]
        result["compiler_artifact"] = file_ref(original)
        shutil.copyfile(original, destination)
        result["test_executable"] = file_ref(destination)
        need(file_binding(original) == file_binding(destination), "compiler/copy bytes differ")
        listing = subprocess.run([str(destination), "--list"], cwd=ROOT, env=environment(), capture_output=True, timeout=30, check=False)
        need(listing.returncode == 0 and len(listing.stdout)+len(listing.stderr) <= 1024*1024, "bounded successful test listing required")
        lines = listing.stdout.decode("utf8", "strict").splitlines()
        expected_tests = {"m194g_noise_production_bridge", "m194g_private_production_outputs",
                          "m194g_private_source_rails_and_fault", "m194g_private_bounded_json_paths_aliases",
                          "m194g_private_settings_geometry", "m194g_private_manifest_schema_tuple_controls",
                          "m194g_private_ledger_changed_input", "m194g_private_actual_plan_controls"}
        names = [line[:-6] for line in lines if line.endswith(": test") and "::noise_pupil_bridge::" in line]
        need(len(names) == len(expected_tests) and {name.rsplit("::", 1)[1] for name in names} == expected_tests,
             "actual new bridge/control test listing required")
        (output/"test-list.log").write_bytes(listing.stdout+listing.stderr)
        result["test_listing"] = file_ref(output/"test-list.log")
        result["sources_after"] = sources()
        need(result["sources_after"] == before and required[own] == file_binding(__file__), "source changed during build/listing")
        for ref in release["inputs"]:
            need(file_binding(ROOT/ref["path"]) == {k: ref[k] for k in ("sha256", "bytes")}, "build input changed after compile")
        result["status"] = "COMPLETE_COMPILED_TESTS_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    finally:
        result["ended_utc"] = datetime.now(timezone.utc).isoformat()
        result["wall_seconds"] = time.monotonic()-started
        try:
            if log.exists(): result["compiler_log"] = file_ref(log)
        except Exception as exc:
            result["status"] = "UNCOMMISSIONED_BUILD"
            result["finalization_errors"].append("compiler log binding: "+repr(exc))
        result_path = output/"result.json"
        try:
            write_json(result_path, result)
            need(sources() == before and required[own] == file_binding(__file__), "source changed through build persistence")
            need(file_ref(args.release) == result["execution_release"], "build release changed through persistence")
            for ref in release["inputs"]:
                need(file_binding(ROOT/ref["path"]) == {k: ref[k] for k in ("sha256", "bytes")}, "build input changed through persistence")
            for key in ("compiler_log", "test_listing"):
                if result[key] is not None:
                    need(file_ref(ROOT/result[key]["path"]) == result[key], key+" changed through persistence")
            if result["test_executable"] is not None:
                need(file_ref(output/"noise-pupil-bridge-tests.exe") == result["test_executable"], "copied executable changed through persistence")
                need(file_ref(ROOT/result["compiler_artifact"]["path"]) == result["compiler_artifact"], "original executable changed through persistence")
        except Exception as exc:
            result["status"] = "UNCOMMISSIONED_BUILD"
            result["finalization_errors"].append(repr(exc))
            try: write_json(result_path, result)
            except Exception as second:
                print("build final failure persistence: "+repr(second), file=sys.stderr, flush=True)
    print(json.dumps(dict(status=result["status"], result=str(output/"result.json"), error=result["error"], finalization_errors=result["finalization_errors"])), flush=True)
    return 0 if result["status"] == "COMPLETE_COMPILED_TESTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
