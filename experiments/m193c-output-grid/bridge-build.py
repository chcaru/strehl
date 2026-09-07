"""Source-bound build-only controller for the M193c native output-grid and registration derivative bridge."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
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
SOURCE = HERE / "private-adapter.rs"
PARENT = ROOT / "crates/strehl-cli/src/merge_cmd/production-truth.rs"
PROCESS = HERE / "bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"


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

    As in M194d, this is not a general Rust/cfg parser; explicit include_bytes/include_str files are also bound. Both test crates' sources
    are bound even when a dependency build omits their cfg(test) modules.
    """
    tracked = subprocess.check_output(["git", "--no-optional-locks", "ls-files", "-z",
                                       "crates", "Cargo.toml", "Cargo.lock"], cwd=ROOT)
    paths = {ROOT / p for p in tracked.decode("utf-8").split("\0") if p and (ROOT / p).is_file()}
    paths.update((SOURCE, PROCESS, HARNESS))
    pending = [(p, ROOT / "crates" / p.relative_to(ROOT).parts[1] if p.is_relative_to(ROOT/"crates") else ROOT/"crates/strehl-cli")
               for p in paths if p.suffix == ".rs"]
    seen = set()
    while pending:
        source, crate = pending.pop()
        if (source, crate) in seen:
            continue
        seen.add((source, crate))
        text = source.read_text(encoding="utf-8")
        targets = [(crate / relative.lstrip("/")).resolve() for relative in re.findall(
            r'include(?:_bytes|_str)?!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)', text, re.M)]
        targets += [(source.parent / relative).resolve() for relative in
                    re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]', text, re.M)]
        for target in targets:
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError("invalid external Rust include " + str(target))
            paths.add(target)
            if target.suffix == ".rs": pending.append((target, crate))
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
    need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands", "build_command", "expected_tests"}
         and release["schema"] == "m193c-bridge-build-release-v1" and release["scope"] == "build-only", "build release schema/scope")
    commands = [[args.release_sha256 if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in row] for row in release["commands"]]
    need(list(sys.orig_argv) in commands, "actual build-controller invocation not released")
    before = sources()
    own = Path(__file__).resolve().relative_to(ROOT).as_posix()
    required = {**before, own: file_binding(__file__)}
    need(required == release["source_bindings"], "exact compiled/controller source closure required")
    for ref in release["inputs"]:
        need(file_binding(ROOT/ref["path"]) == {k: ref[k] for k in ("sha256", "bytes")}, "build input changed")
    command = release["build_command"]
    need(command == ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir", "target/m193c-output-grid-build-1", "--no-run", "--message-format=json-render-diagnostics"], "exact build command")
    output = args.output.resolve()
    need(output.is_relative_to(ROOT), "build output outside repository")
    output.mkdir(parents=True, exist_ok=False)
    result = dict(schema="m193c-bridge-build-v1", status="UNCOMMISSIONED_BUILD", invocation=list(sys.orig_argv),
                  execution_release=dict(path=args.release.resolve().relative_to(ROOT).as_posix(),
                                         sha256=args.release_sha256, bytes=len(raw)), command=command, sources_before=before,
                  sources_after=None, driver=file_ref(__file__), started_utc=datetime.now(timezone.utc).isoformat(),
                  ended_utc=None, wall_seconds=None, exit_code=None, compiler_artifact_message=None,
                  compiler_artifact=None, test_executable=None, test_listing=None, rebuilt_cli=False,
                  build_script_message=None, software=None,
                  compiler_log=None, compiler_environment={k: environment().get(k) for k in
                       ("PATH", "RUSTUP_TOOLCHAIN", "RUSTUP_HOME", "CARGO_HOME", "RUSTC", "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER")},
                  compiler_identity_scope="observed command/environment and source-to-artifact bytes; not a hermetic toolchain certificate",
                  error=None, finalization_errors=[])
    started = time.monotonic()
    log = output/"compiler.log"
    try:
        need(not (ROOT/"target/m193c-output-grid-build-1").exists(), "replacement build target must be fresh")
        proc_spec = importlib.util.spec_from_file_location("m193c_build_process", PROCESS)
        process_api = importlib.util.module_from_spec(proc_spec)
        process_raw = PROCESS.read_bytes()
        need(dict(sha256=hashlib.sha256(process_raw).hexdigest(), bytes=len(process_raw))
             == before[PROCESS.relative_to(ROOT).as_posix()], "actual process helper bytes")
        exec(compile(process_raw, str(PROCESS), "exec"), process_api.__dict__)
        job_api = process_api.load_job_api(before[HARNESS.relative_to(ROOT).as_posix()])
        SOURCE.touch(); PARENT.touch()
        # Build only. Compiler output is retained directly rather than in a pipe
        # buffer. The build has its own1800-second wall/CPU allowance and8GiB committed-memory cap.
        observation = process_api.run(command, environment(), ROOT, log, api=job_api,
                                      wall_seconds=1800, cpu_seconds=1800,
                                      log_bytes=64<<20, committed_bytes=8<<30)
        result["compiler_process"] = observation
        result["exit_code"] = observation["exit_code"]
        need(observation["error"] is None and observation["cleanup_errors"] == []
             and observation["terminal_job_accounting"] is True
             and observation["job_accounting"]["active_processes"] == 0, "bounded compiler process")
        need(log.stat().st_size <= 64*1024*1024, "compiler log exceeds64MiB operational cap")
        result["compiler_log"] = file_ref(log)
        artifacts = []
        build_scripts = []
        rebuilt = False
        with log.open("rb") as stream:
            for line in stream:
                rebuilt |= b"Compiling strehl-cli" in line
                if line.startswith(b"{"):
                    value = strict(line)
                    if (value.get("reason") == "build-script-executed"
                            and value.get("package_id") == "path+"+(ROOT/"crates/strehl-cli").as_uri()+"#0.0.0"):
                        build_scripts.append(value)
                    if (value.get("reason") == "compiler-artifact" and value.get("executable")
                            and value.get("target", {}).get("name") == "strehl"
                            and Path(value.get("target", {}).get("src_path", "")).resolve() == ROOT/"crates/strehl-cli/src/main.rs"
                            and Path(value.get("manifest_path", "")).resolve() == ROOT/"crates/strehl-cli/Cargo.toml"
                            and value.get("package_id") == "path+"+(ROOT/"crates/strehl-cli").as_uri()+"#0.0.0"
                            and value.get("profile", {}).get("test") is True):
                        artifacts.append(value)
        result["rebuilt_cli"] = rebuilt
        need(result["exit_code"] == 0 and rebuilt and len(artifacts) == 1, "successful fresh compiler artifact required")
        need(len(build_scripts) == 1, "one actual CLI build-script observation")
        stamps = [v for k, v in build_scripts[0]["env"] if k == "STREHL_BUILD_ID"]
        need(len(stamps) == 1 and re.fullmatch(r"[0-9a-f]{12}(?:-dirty)?", stamps[0]) is not None,
             "actual versioned CLI build stamp")
        result["build_script_message"] = build_scripts[0]
        result["software"] = "strehl 0.0.0 ("+stamps[0]+")"
        original = Path(artifacts[0]["executable"]).resolve()
        need(original.is_relative_to(ROOT), "compiler artifact outside workspace")
        destination = output/"output-grid-tests.exe"
        result["compiler_artifact_message"] = artifacts[0]
        result["compiler_artifact"] = file_ref(original)
        shutil.copyfile(original, destination)
        result["test_executable"] = file_ref(destination)
        need(file_binding(original) == file_binding(destination), "compiler/copy bytes differ")
        list_path = output/"test-list.log"
        listing = process_api.run([str(destination), "--list"], environment(), ROOT, list_path,
                                  api=job_api, wall_seconds=30, cpu_seconds=30,
                                  log_bytes=1<<20, committed_bytes=1<<30)
        result["listing_process"] = listing
        need(listing["exit_code"] == 0 and listing["error"] is None and listing["cleanup_errors"] == []
             and listing["terminal_job_accounting"] is True and listing["job_accounting"]["active_processes"] == 0,
             "bounded successful test listing required")
        lines = list_path.read_text(encoding="utf8", errors="strict").splitlines()
        expected_list = release["expected_tests"]
        need(type(expected_list) is list and expected_list and all(type(n) is str for n in expected_list)
             and len(expected_list) == len(set(expected_list)), "unique expected test strings")
        expected_names = set(expected_list)
        need(expected_names and all(n.startswith("merge_cmd::production_truth::m193c_") for n in expected_names),
             "explicit M193c test population")
        names = [line[:-6] for line in lines if line.endswith(": test") and "::m193c_" in line]
        need(len(names) == len(expected_names) and set(names) == expected_names,
             "actual exact M193c bridge/control test listing required")
        result["test_listing"] = file_ref(list_path)
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
                need(file_ref(output/"output-grid-tests.exe") == result["test_executable"], "copied executable changed through persistence")
                need(file_ref(ROOT/result["compiler_artifact"]["path"]) == result["compiler_artifact"], "original executable changed through persistence")
        except Exception as exc:
            result["status"] = "UNCOMMISSIONED_BUILD"
            result["finalization_errors"].append(repr(exc))
            try:
                if result_path.exists():
                    result_path.rename(output/"result.json.rejected")
                write_json(result_path, result)
            except Exception as second:
                print("build final failure persistence: "+repr(second), file=sys.stderr, flush=True)
    print(json.dumps(dict(status=result["status"], result=str(output/"result.json"), error=result["error"], finalization_errors=result["finalization_errors"])), flush=True)
    return 0 if result["status"] == "COMPLETE_COMPILED_TESTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
