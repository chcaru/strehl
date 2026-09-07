"""Finite actual Windows process controls; exact release required before run."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
START = time.monotonic()


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def binding(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def file_ref(path):
    return dict(path=path.resolve().relative_to(ROOT).as_posix(), **binding(path))


def save(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    need(len(raw) <= 4 << 20, "bounded controller result")
    with path.open("wb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    need(path.read_bytes() == raw, "controller result persistence")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--release", type=Path, required=True)
    p.add_argument("--release-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    need(a.release.is_absolute() and a.output.is_absolute(), "absolute controller paths")
    with a.release.open("rb") as stream:
        release_raw = stream.read((4 << 20) + 1)
    need(len(release_raw) <= 4 << 20 and hashlib.sha256(release_raw).hexdigest() == a.release_sha256,
         "controller release external pin/extent")
    def unique(items):
        value = {}
        for key, item in items:
            need(key not in value, "duplicate release key")
            value[key] = item
        return value
    def nonfinite(token):
        raise ValueError("nonfinite release token: " + token)
    release = json.loads(release_raw, object_pairs_hook=unique, parse_constant=nonfinite)
    need(set(release) == {"schema", "scope", "source_bindings", "inputs", "commands"}
         and release["schema"] == "m193c-execution-release-v1" and release["scope"] == "controller-controls",
         "controller release scope")
    expected = {str((HERE/name).relative_to(ROOT).as_posix()) for name in
                ("controller-controls.py", "controller-child.py", "bounded-process.py")}
    expected.add("experiments/m12-scorecard/m12-harness.py")
    need(set(release["source_bindings"]) == expected, "controller source population")
    def check_sources():
        need(time.monotonic() - START <= 120, "complete controller wall bound")
        for name, ref in release["source_bindings"].items():
            need(binding(ROOT/name) == ref, "controller source changed")
        for ref in release["inputs"]:
            need(file_ref(ROOT/ref["path"]) == ref, "controller input changed")
        need(binding(a.release)["sha256"] == a.release_sha256, "controller release changed")
    check_sources()
    need(list(sys.orig_argv) in [[a.release_sha256 if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in c]
                               for c in release["commands"]], "actual controller invocation")
    a.output.mkdir(parents=True, exist_ok=False)
    proc_path = HERE/"bounded-process.py"
    raw = proc_path.read_bytes()
    need(dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
         == release["source_bindings"][proc_path.relative_to(ROOT).as_posix()], "actual helper import bytes")
    spec = importlib.util.spec_from_file_location("m193c_process_controls", proc_path)
    helper = importlib.util.module_from_spec(spec)
    exec(compile(raw, str(proc_path), "exec"), helper.__dict__)
    api = helper.load_job_api(release["source_bindings"]["experiments/m12-scorecard/m12-harness.py"])
    result = dict(schema="m193c-controller-controls-v1", status="UNCOMMISSIONED_CONTROLLER",
                  release=file_ref(a.release), command=list(sys.orig_argv), sources_before=release["source_bindings"],
                  sources_after=None, cases=[], error=None, finalization_errors=[])
    produced = []
    try:
        for name, ref in release["source_bindings"].items():
            destination = a.output/"sources"/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            source_raw = (ROOT/name).read_bytes()
            need(dict(sha256=hashlib.sha256(source_raw).hexdigest(), bytes=len(source_raw)) == ref, "source snapshot")
            destination.write_bytes(source_raw)
            produced.append(file_ref(destination))
        watched = a.output/"watched-input.txt"
        watched.write_bytes(b"original-private-input")
        watched_expected = binding(watched)
        modes = ("valid", "nonzero", "exact-log", "overflow-log", "timeout", "nested-timeout", "memory-allowed", "memory", "late-log-binding", "changed-input", "restored")
        for index, mode in enumerate(modes):
            check_sources()
            if mode == "restored":
                watched.write_bytes(b"original-private-input")
            log = a.output/f"{index:02}-{mode}.log"
            child_mode = "valid" if mode == "restored" else "overflow-log" if mode == "late-log-binding" else mode
            argv = [sys.executable, str(HERE/"controller-child.py"), child_mode]
            if mode == "changed-input":
                argv.append(str(watched))
            def unchanged():
                need(binding(watched) == watched_expected, "watched input changed")
            env, removed = helper.clean_environment()
            original_binding = helper.binding
            def unavailable_log(path):
                if Path(path) == log:
                    raise OSError("M193C_PRIVATE_LATE_LOG_READ")
                return original_binding(path)
            if mode == "late-log-binding":
                helper.binding = unavailable_log
            try:
                actual = helper.run(argv, env, ROOT, log, api=api,
                                    wall_seconds=5 if mode == "nested-timeout" else 1 if mode == "timeout" else 10,
                                    cpu_seconds=10, log_bytes=65536,
                                    committed_bytes=(256 if mode == "memory-allowed" else 64)<<20,
                                    check=unchanged if mode in ("changed-input", "restored") else lambda: None)
            finally:
                helper.binding = original_binding
            row = dict(index=index, mode=mode, actual=actual, removed_environment_names=removed, passed=False)
            result["cases"].append(row)
            produced.append(file_ref(log))
            text = log.read_bytes()
            clean = actual["error"] is None and actual["cleanup_errors"] == []
            if mode in ("valid", "restored"):
                row["passed"] = clean and actual["exit_code"] == 0 and text == b"M193C_VALID_CHILD\r\n"
            elif mode == "nonzero":
                row["passed"] = clean and actual["exit_code"] == 7 and b"M193C_EXIT_SEVEN" in text
            elif mode == "exact-log":
                row["passed"] = clean and actual["exit_code"] == 0 and text == b"x"*65536
            elif mode == "overflow-log":
                row["passed"] = "child log bound" in (actual["error"] or "") and text == b"x"*65536
            elif mode in ("timeout", "nested-timeout"):
                row["passed"] = ("child wall bound" in (actual["error"] or "")
                                 and b"M193C_SLEEP_STARTED" in text and actual["cleanup_errors"] == [])
                if mode == "nested-timeout":
                    parents = re.findall(rb"^M193C_PARENT_PID=(\d+)\r?$", text, re.M)
                    children = re.findall(rb"^M193C_SLEEP_PID=(\d+)\r?$", text, re.M)
                    requested = re.findall(rb"^M193C_NESTED_PID=(\d+)\r?$", text, re.M)
                    baseline = result["cases"][0]["actual"]["job_accounting"]["total_processes"]
                    row["nested_identity"] = dict(parent_pids=[int(v) for v in parents],
                                                   executing_child_pids=[int(v) for v in children],
                                                   requested_child_pids=[int(v) for v in requested],
                                                   single_companion_processes=baseline,
                                                   additional_job_processes=actual["job_accounting"]["total_processes"]-baseline)
                    row["passed"] &= (len(parents) == len(children) == len(requested) == 1
                                      and parents[0] != children[0]
                                      and baseline > 0
                                      and actual["job_accounting"]["total_processes"] > baseline)
            elif mode == "memory-allowed":
                row["passed"] = clean and actual["exit_code"] == 0 and b"M193C_MEMORY_ALLOWED=134217728" in text
            elif mode == "memory":
                os_refusal = clean and actual["exit_code"] == 7 and b"M193C_MEMORY_REFUSED" in text
                parent_refusal = (actual["error"] == "ValueError('child committed-memory bound')"
                                  and actual["job_memory"]["peak_job_memory_used_bytes"] > 64<<20)
                row["memory_refusal_route"] = "child-MemoryError" if os_refusal else "parent-observed-peak" if parent_refusal else None
                row["passed"] = (os_refusal or parent_refusal) and result["cases"][-2]["mode"] == "memory-allowed" and result["cases"][-2]["passed"] is True
            elif mode == "late-log-binding":
                row["passed"] = ("child log bound" in (actual["error"] or "") and text == b"x"*65536
                                 and len(actual["cleanup_errors"]) == 1
                                 and "M193C_PRIVATE_LATE_LOG_READ" in actual["cleanup_errors"][0])
            elif mode == "changed-input":
                row["passed"] = ("watched input changed" in (actual["error"] or "")
                                 and watched.read_bytes() == b"changed-private-input")
            if mode != "late-log-binding":
                row["passed"] = row["passed"] and actual["cleanup_errors"] == []
            row["passed"] = row["passed"] and actual["terminal_job_accounting"] is True
            row["passed"] = row["passed"] and actual["job_accounting"]["active_processes"] == 0
            row["passed"] = (row["passed"] and actual["configured_job_limits"]["flags"] & 0x200 != 0
                             and actual["configured_job_limits"]["committed_bytes"] == actual["limits"]["committed_bytes"])
            need(row["passed"] is True, "controller case refused its intended oracle: " + mode)
        need(len(result["cases"]) == 11, "complete finite controller population")
        need(binding(watched) == watched_expected, "watched input restored")
        produced.append(file_ref(watched))
        result["status"] = "PASS_OWNED_PROCESS_CONTROLS_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    try:
        check_sources()
        for ref in produced:
            need(file_ref(ROOT/ref["path"]) == ref, "controller artifact changed")
        result["sources_after"] = {name: binding(ROOT/name) for name in release["source_bindings"]}
        result["artifacts"] = produced
        result["elapsed_seconds_before_result"] = time.monotonic() - START
        save(a.output/"result.json", result)
        check_sources()
        for ref in produced:
            need(file_ref(ROOT/ref["path"]) == ref, "controller artifact changed through persistence")
    except Exception:
        result["status"] = "UNCOMMISSIONED_CONTROLLER"
        result["finalization_errors"].append(traceback.format_exc())
        save(a.output/"result.json", result)
    print(json.dumps({k: result[k] for k in ("status", "error", "finalization_errors")}), flush=True)
    return 0 if result["status"] == "PASS_OWNED_PROCESS_CONTROLS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
