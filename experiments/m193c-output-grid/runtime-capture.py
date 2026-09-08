"""Root-released dependency capture only; no subject imports or launch on import."""
import time
START = time.monotonic()
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "runtime-capture-1"
RUNTIME = HERE / "derivative-runtime-1.json"
PROCESS = HERE / "bounded-process.py"
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"
READER = HERE / "independent-derivative-read.py"
HELPER_SHA = "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"
SUCCESS = "COMPLETE_DEPENDENCY_RUNTIME_CAPTURE_ONLY"
MIB = 1 << 20


def need(ok, message):
    if not ok:
        raise ValueError(message)


def closed(value, names, label):
    need(type(value) is dict and set(value) == set(names), label + " closed fields")


def sha_form(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def strict(raw):
    def pairs(items):
        value = {}
        for key, item in items:
            need(key not in value, "duplicate JSON key")
            value[key] = item
        return value
    value = json.loads(raw, object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    def finite(item):
        if type(item) is float:
            need(math.isfinite(item), "nonfinite JSON number")
        elif type(item) is dict:
            for child in item.values(): finite(child)
        elif type(item) is list:
            for child in item: finite(child)
    finite(value)
    return value


def ref_path(ref, external=False):
    closed(ref, ("path", "sha256", "bytes"), "FileRef")
    need(type(ref["path"]) is str and sha_form(ref["sha256"]) and type(ref["bytes"]) is int and
         0 <= ref["bytes"] <= 128 * MIB, "typed bounded FileRef")
    path = Path(ref["path"])
    if not path.is_absolute():
        relative = PurePosixPath(ref["path"])
        need(str(relative) == ref["path"] and ".." not in relative.parts and "\\" not in ref["path"], "relative POSIX ref")
        path = ROOT / path
    path = path.resolve()
    need(path.is_relative_to(ROOT) or external and path.suffix.lower() in (".exe", ".py", ".pyd", ".dll"),
         "contained evidence or actual dependency binary/source")
    need(path.suffix.lower() not in (".arw", ".raw", ".tif", ".tiff", ".npy"), "no capture/image payload access")
    return path


class State:
    def __init__(self):
        self.child_cpu = 0.0
        self.cpu_accounting_complete = True
        self.child_cpu_accounting = "not-launched"
        self.bound = {}

    def work(self):
        observed = time.process_time() + (self.child_cpu if self.child_cpu is not None else 0.0)
        return dict(cpu_seconds=observed if self.cpu_accounting_complete else None,
                    observed_cpu_seconds=observed, cpu_accounting_complete=self.cpu_accounting_complete,
                    child_cpu_accounting=self.child_cpu_accounting,
                    wall_seconds=time.monotonic() - START, child_cpu_seconds=self.child_cpu,
                    scope="parent CPU plus observed child CPU once; total unavailable until terminal child accounting; original wall clock")

    def check(self):
        work = self.work()
        # During a live child this is a lower-bound check; the helper separately
        # checks actual Job CPU. Incomplete accounting alone must not abort it.
        need(work["observed_cpu_seconds"] <= 30 and work["wall_seconds"] <= 60, "complete runtime capture time budget")

    def binding(self, path, cap=32 * MIB, emergency=False):
        before = path.stat(follow_symlinks=False)
        need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes & 0x400 and
             0 <= before.st_size <= cap, "ordinary bounded file")
        digest, count = hashlib.sha256(), 0
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened file identity")
            while block := stream.read(MIB):
                count += len(block); digest.update(block)
                need(count <= cap, "file growth bound")
                if not emergency: self.check()
        after = path.stat(follow_symlinks=False)
        need(all(getattr(before, k) == getattr(after, k) for k in
                 ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_file_attributes")) and count == before.st_size,
             "file changed during binding")
        return dict(sha256=digest.hexdigest(), bytes=count)

    def ref(self, path, external=False, cap=32 * MIB, emergency=False):
        path = path.resolve()
        return dict(path=str(path) if external else path.relative_to(ROOT).as_posix(),
                    **self.binding(path, cap, emergency))

    def verify(self, ref, external=False):
        path = ref_path(ref, external)
        expected = {k: ref[k] for k in ("sha256", "bytes")}
        need(self.binding(path, max(1, ref["bytes"])) == expected, "FileRef changed: " + str(path))
        need(self.bound.setdefault(path, expected) == expected, "changed previously bound file")
        return path

    def read(self, ref, cap=MIB):
        path = self.verify(ref)
        need(ref["bytes"] <= cap, "JSON input cap")
        with path.open("rb") as stream: raw = stream.read(cap + 1)
        need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "same-buffer JSON pin")
        return strict(raw)

    def recheck(self):
        for path, expected in self.bound.items():
            need(self.binding(path, max(1, expected["bytes"])) == expected, "final bound input/source/runtime changed")
        self.check()


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    need(len(raw) <= 4 * MIB, "bounded capture result")
    with path.open("xb") as stream:
        need(stream.write(raw) == len(raw), "short result write")
        stream.flush(); os.fsync(stream.fileno())
    need(path.read_bytes() == raw, "persisted capture result bytes")
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def fail(result, label):
    message = label + ": " + traceback.format_exc()
    if result["error"] is None: result["error"] = message
    else: result["finalization_errors"].append(message)
    result["status"] = "REFUSED_RUNTIME_CAPTURE"


def revoke(path, result):
    try:
        if path.exists():
            names = ("result.first.json", "result.refused-1.json", "result.refused-2.json")
            retained = next((path.parent / name for name in names if not (path.parent / name).exists()), None)
            need(retained is not None, "bounded capture publication retention")
            path.rename(retained)
        save(path, result)
    except Exception:
        result["finalization_errors"].append("refused result persistence: " + traceback.format_exc())
        try:
            print(json.dumps(dict(error=result["error"], finalization_errors=result["finalization_errors"])), file=sys.stderr, flush=True)
        except Exception:
            result["finalization_errors"].append("secondary stderr: " + traceback.format_exc())


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--release", type=Path, required=True)
    cli.add_argument("--release-sha256", required=True)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT and sys.dont_write_bytecode, "Windows ROOT and -B")
    need(args.release.is_absolute() and args.output.is_absolute() and args.output.resolve() == OUTPUT and
         args.release.resolve().is_relative_to(HERE) and sha_form(args.release_sha256), "fixed contained capture locations")
    need(not OUTPUT.exists() and not RUNTIME.exists(), "fresh output and actual runtime destination")
    state = State()
    release_ref = state.ref(args.release.resolve())
    need(release_ref["sha256"] == args.release_sha256, "external release pin")
    release = state.read(release_ref, 4 * MIB)
    closed(release, ("schema", "scope", "source_bindings", "inputs", "commands", "build", "private_admission",
                     "independent_review", "python_executable"), "capture release")
    need(release["schema"] == "m193c-runtime-capture-release-v1" and release["scope"] == "dependency-runtime-only", "capture scope")
    closed(release["commands"], ("parent", "reader"), "exact capture commands")
    python = state.verify(release["python_executable"], True)
    need(python == Path(sys.executable).resolve(), "actual parent interpreter")
    expected_parent = [str(python), "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(OUTPUT / "cache-parent"),
                       str(Path(__file__).resolve()), "--release", str(args.release.resolve()), "--release-sha256",
                       "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(OUTPUT)]
    expected_reader = [str(python), "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(OUTPUT / "cache-reader"),
                       str(READER), "--capture-runtime", str(RUNTIME)]
    need(release["commands"] == dict(parent=expected_parent, reader=expected_reader) and list(sys.orig_argv) ==
         [args.release_sha256 if word == "ACTUAL_EXECUTION_RELEASE_SHA256" else word for word in expected_parent], "actual exact argv")
    OUTPUT.mkdir()
    result = dict(schema="m193c-runtime-capture-v1", status="REFUSED_RUNTIME_CAPTURE", execution_release=release_ref,
                  command=list(sys.orig_argv), child_command=expected_reader, build=release["build"],
                  private_admission=release["private_admission"], independent_review=release["independent_review"],
                  sources_before=release["source_bindings"], sources_after=None, inputs_before=release["inputs"], inputs_after=None,
                  environment=None, removed_environment=None, observation=None, log=None, runtime=None,
                  runtime_module_refs=[], work=None, error=None, finalization_errors=[])
    path = OUTPUT / "result.json"
    try:
        required = {p.relative_to(ROOT).as_posix() for p in (Path(__file__).resolve(), HERE / "runtime-capture-preregister.md",
                    PROCESS, HARNESS, READER, HERE / "independent-derivative-tiff.py",
                    HERE / "independent-derivative-reader-preregister.md", ROOT / "experiments/m194g-larger-pupil/independent-rgb-tiff.py")}
        need(type(release["source_bindings"]) is dict and required <= set(release["source_bindings"]), "complete capture source closure")
        for name, expected in release["source_bindings"].items():
            state.verify(dict(path=name, **expected))
        need(release["source_bindings"][PROCESS.relative_to(ROOT).as_posix()]["sha256"] == HELPER_SHA, "held repaired process helper")
        need(type(release["inputs"]) is list and len({str(ref_path(ref)) for ref in release["inputs"]}) == len(release["inputs"]), "unique capture inputs")
        for ref in release["inputs"]: state.verify(ref)
        for ref in (release["build"], release["private_admission"], release["independent_review"]):
            need(ref in release["inputs"], "actual prerequisite in released inputs")
        need(ref_path(release["build"]) == HERE / "bridge-build-3/result.json" and
             ref_path(release["private_admission"]) == HERE / "private-campaign-2/derivative-private-admission.json", "actual build3/private2 paths")
        build, gate = state.read(release["build"]), state.read(release["private_admission"])
        need(build["schema"] == "m193c-bridge-build-v1" and build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and
             type(build["exit_code"]) is int and build["exit_code"] == 0 and build["error"] is None and
             build["finalization_errors"] == [] and build["sources_before"] == build["sources_after"], "actual stable build3")
        need(gate["schema"] == "m193c-derivative-private-admission-v1" and gate["status"] == "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY"
             and gate["build"] == release["build"] and gate["error"] is None and gate["finalization_errors"] == [], "actual independent private2 gate")
        campaign_ref = next(ref for ref in release["inputs"] if ref_path(ref) == HERE / "private-campaign-2/result.json")
        campaign = state.read(campaign_ref)
        need(campaign["status"] == "PASS_M193C_PRIVATE_STAGE_ONLY" and campaign["error"] is None and
             campaign["finalization_errors"] == [] and campaign["build"] == release["build"] and
             campaign["derivative_admission"] == release["private_admission"] and campaign["derivative_read"] == gate["independent_read"], "actual completed private2 parent")
        for ref in (gate["private_result"], gate["independent_read"]):
            need(ref in release["inputs"], "private reader/producer actual prerequisite refs")
        # The independent review may be Markdown: bind bytes, never parse it as JSON.
        state.verify(release["independent_review"])
        helper_raw = PROCESS.read_bytes()
        need(hashlib.sha256(helper_raw).hexdigest() == HELPER_SHA, "executed helper exact bytes")
        spec = importlib.util.spec_from_loader("m193c_runtime_capture_process", loader=None, origin=str(PROCESS))
        helper = importlib.util.module_from_spec(spec); helper.__file__ = str(PROCESS)
        exec(compile(helper_raw, str(PROCESS), "exec"), helper.__dict__)
        api = helper.load_job_api(release["source_bindings"][HARNESS.relative_to(ROOT).as_posix()])
        env, removed = helper.clean_environment()
        python_removed = [name for name in env if name.upper().startswith("PYTHON")]
        for name in python_removed: del env[name]
        result["removed_environment"] = sorted(set(removed + python_removed))
        controlled = ("PYTHON", "STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
        remaining = {k: v for k, v in env.items() if k.upper().startswith(controlled) or
                     k.upper() in ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_TARGET_DIR")}
        need(remaining == {}, "all controlled child overrides cleared")
        result["environment"] = dict(explicit_overrides={}, remaining_controlled_variables=remaining,
                                     other_variables="inherited unchanged; unrelated values are not persisted")
        state.recheck()
        work = state.work()
        state.cpu_accounting_complete = False
        state.child_cpu_accounting = "unavailable"
        state.child_cpu = None
        result["observation"] = helper.run(expected_reader, env, ROOT, OUTPUT / "capture.log", api=api,
            wall_seconds=60 - work["wall_seconds"], cpu_seconds=30 - work["observed_cpu_seconds"],
            log_bytes=MIB, committed_bytes=2 << 30, check=state.check)
        actual = result["observation"]
        account = actual.get("job_accounting")
        if type(account) is dict and type(account.get("total_cpu_100ns")) is int and account["total_cpu_100ns"] >= 0:
            state.child_cpu = account["total_cpu_100ns"] / 1e7
            state.child_cpu_accounting = "observed-partial"
            if actual.get("terminal_job_accounting") is True and type(account.get("active_processes")) is int and account["active_processes"] == 0:
                state.cpu_accounting_complete = True
                state.child_cpu_accounting = "terminal"
        need(state.cpu_accounting_complete, "actual complete terminal child CPU accounting required")
        need(actual["command"] == expected_reader and type(actual["exit_code"]) is int and actual["exit_code"] == 0 and
             actual["error"] is None and actual["cleanup_errors"] == [] and actual["terminal_job_accounting"] is True and
             account["active_processes"] == 0 and actual["direct_exit_observed"] is True and actual["pipe_eof_observed"] is True,
             "actual complete capture child exit and terminal Job")
        result["log"] = state.ref(OUTPUT / "capture.log", cap=MIB)
        need(state.verify(actual["log"]) == OUTPUT / "capture.log" and
             all(actual["log"][k] == result["log"][k] for k in ("sha256", "bytes")), "actual capture log association")
        result["runtime"] = state.ref(RUNTIME, cap=MIB)
        record = state.read(result["runtime"])
        closed(record, ("schema", "python_executable", "python_version", "numpy_version", "rawpy_version", "libraw_version",
                        "module_files", "thread_environment"), "captured runtime")
        need(record["schema"] == "m193c-derivative-reader-runtime-v1" and record["python_executable"] == release["python_executable"]
             and all(type(record[k]) is str and record[k] for k in ("python_version", "numpy_version", "rawpy_version"))
             and type(record["libraw_version"]) is list and all(type(v) is int for v in record["libraw_version"])
             and record["thread_environment"] == {k: "2" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}, "actual native dependency runtime")
        need(type(record["module_files"]) is list and 4 <= len(record["module_files"]) <= 32 and
             len({str(ref_path(ref, True)) for ref in record["module_files"]}) == len(record["module_files"]), "distinct bounded actual dependency files")
        for ref in record["module_files"]: state.verify(ref, True)
        result["runtime_module_refs"] = record["module_files"]
        log_lines = (OUTPUT / "capture.log").read_bytes().splitlines()
        need(len(log_lines) == 1, "single actual capture completion message")
        message = strict(log_lines[0])
        closed(message, ("status", "runtime"), "capture completion message")
        need(message["status"] == "CAPTURED_DEPENDENCY_RUNTIME_ONLY" and state.verify(message["runtime"]) == RUNTIME and
             all(message["runtime"][k] == result["runtime"][k] for k in ("sha256", "bytes")), "actual capture message/runtime bytes")
        state.recheck()
        result["sources_after"], result["inputs_after"] = release["source_bindings"], release["inputs"]
        result["status"] = SUCCESS
    except Exception:
        fail(result, "capture")
    # Preserve actual bounded files even when capture/validation refused. A hash
    # of a failed runtime attempt cannot substitute for this parent's completion.
    for name, actual_path, cap in (("log", OUTPUT / "capture.log", MIB), ("runtime", RUNTIME, MIB)):
        try:
            if actual_path.exists():
                actual_ref = state.ref(actual_path, cap=cap, emergency=result["status"] != SUCCESS)
                need(result[name] is None or actual_ref == result[name], "capture artifact changed after validation")
                result[name] = actual_ref
        except Exception:
            fail(result, "retained " + name)
    try:
        result["work"] = state.work()
        final_ref = save(path, result)
        if result["status"] == SUCCESS:
            state.recheck()
            state.verify(final_ref)
            state.check()
    except Exception:
        fail(result, "capture publication")
        revoke(path, result)
    try:
        final_ref = state.ref(path, cap=4 * MIB, emergency=result["status"] != SUCCESS)
        if result["status"] == SUCCESS: state.check()
        print(json.dumps(dict(status=result["status"], result=final_ref, work_through_final_checks=state.work(),
                              error=result["error"], finalization_errors=result["finalization_errors"]), allow_nan=False), flush=True)
    except Exception:
        fail(result, "capture terminal receipt")
        revoke(path, result)
    return 0 if result["status"] == SUCCESS else 1


if __name__ == "__main__":
    raise SystemExit(main())
