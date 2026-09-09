"""Compile-only owned-Job completion; derived from pinned M193c bounded process.

Reuses the project's Windows Job structures/functions from the pinned M12
harness. This module does not run its campaign or inspect any capture.
"""
import ctypes
import hashlib
import importlib.util
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "experiments/m12-scorecard/m12-harness.py"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def binding(path):
    h, size = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        while raw := stream.read(1 << 20):
            h.update(raw); size += len(raw)
    return {"sha256": h.hexdigest(), "bytes": size}


def load_job_api(expected):
    raw = HARNESS.read_bytes()
    need({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)} == expected,
         "job helper source changed")
    spec = importlib.util.spec_from_loader("m193c_pinned_job_api", loader=None, origin=str(HARNESS))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(HARNESS)
    sys.modules[spec.name] = module
    exec(compile(raw, str(HARNESS), "exec"), module.__dict__)
    return module


def clean_environment(fields=()):
    prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
    keys = {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_TARGET_DIR"}
    removed = sorted(k for k in os.environ if k.upper().startswith(prefixes) or k.upper() in keys)
    env = {k: v for k, v in os.environ.items() if k not in removed}
    env.update(dict(fields))
    return env, removed



BUILD_ONLY = True
BASE_PROCESS_SHA256 = "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"


def compile_cleanup_record():
    return dict(schema="m194h-compile-owned-descendant-cleanup-v1",
        policy="AFTER_DIRECT_ZERO_AND_PIPE_EOF", disposition="UNVISITED",
        attempted=False, succeeded=False, completed=False,
        before_accounting=None, after_accounting=None, remaining_process_ids=None,
        pid_query_performed=False, pid_query_error=None,
        started_wall_seconds=None, ended_wall_seconds=None, wait_seconds=None,
        max_wait_seconds=5, error=None,
        scope="Only this owned Job is terminated; PIDs are observations, never kill targets. "
              "No executable or creation-identity proof. Generic termination records failure cleanup only.")


def finish_compile_cleanup(result, api, job, started, wall_seconds, observe, check):
    record = result["compile_cleanup"]
    began = time.monotonic()
    deadline = min(began + 5, started + wall_seconds)
    record["started_wall_seconds"] = began - started
    try:
        need(result["direct_exit_observed"] and result["exit_code"] == 0
             and result["pipe_eof_observed"], "compile direct zero exit and EOF required")
        observe(); check()
        record["before_accounting"] = dict(result["job_accounting"])
        if result["job_accounting"]["active_processes"] > 0:
            record["pid_query_performed"] = True
            try:
                pids = api.job_process_ids(job)
                need(type(pids) is list and len(pids) <= 1024
                     and all(type(pid) is int and 0 < pid < (1 << 32) for pid in pids)
                     and len(set(pids)) == len(pids), "bounded observed Job PID list")
                record["remaining_process_ids"] = pids
            except Exception as exc:
                record["pid_query_error"] = repr(exc)[:256]
                raise
            # The census can race natural exit; decide from a fresh Job observation.
            observe(); check()
            record["before_accounting"] = dict(result["job_accounting"])
        if result["job_accounting"]["active_processes"] > 0:
            need(time.monotonic() <= deadline, "compile owned cleanup time bound")
            record["attempted"] = True
            api.kernel32.TerminateJobObject.argtypes = [api.wt.HANDLE, api.wt.UINT]
            api.kernel32.TerminateJobObject.restype = api.wt.BOOL
            if not api.kernel32.TerminateJobObject(job, 0xE194B002):
                raise ctypes.WinError(ctypes.get_last_error())
            record["succeeded"] = True
            while result["job_accounting"]["active_processes"]:
                need(time.monotonic() <= deadline, "compile owned cleanup time bound")
                time.sleep(.01)
                observe(); check()
        need(time.monotonic() <= deadline, "compile owned cleanup time bound")
        need(result["job_accounting"]["active_processes"] == 0, "compile owned cleanup final zero")
        record["disposition"] = ("INTENTIONAL_OWNED_JOB_CLEANUP" if record["attempted"]
                                  else "NATURAL_JOB_EXIT")
        record["completed"] = True
    except Exception as exc:
        record["disposition"] = "REFUSED"
        record["error"] = repr(exc)[:512]
        raise
    finally:
        record["after_accounting"] = (dict(result["job_accounting"])
                                      if result["job_accounting"] is not None else None)
        record["ended_wall_seconds"] = time.monotonic() - started
        record["wait_seconds"] = record["ended_wall_seconds"] - record["started_wall_seconds"]

def run(command, env, cwd, log, *, api, wall_seconds, cpu_seconds,
        log_bytes, committed_bytes, check=lambda: None):
    """Start suspended, assign only this child to our job, then resume.

    Memory is a committed-memory limit, not RSS. Total user+kernel CPU is
    polled and checked again after exit; no exact no-overshoot claim. All
    failures retain the bounded log and observed outcome. Closing our job
    terminates only its own remaining descendants.
    """
    need(os.name == "nt", "Windows process controller required")
    need(type(command) is list and command and all(type(v) is str for v in command), "child argv")
    for value in (wall_seconds, cpu_seconds, log_bytes, committed_bytes):
        need(value > 0, "positive child bound")
    target = ROOT / "target/common-tiff-stack-2"
    need(command == ["cargo", "build", "-p", "strehl-cli", "--bin", "strehl-common-input", "--jobs", "2",
                     "--target-dir", str(target), "--message-format=json-render-diagnostics",
                     "--locked", "--offline"], "exact common-TIFF compile-only owned helper")
    log = Path(log)
    need(not log.exists() and log.parent.is_dir(), "fresh child log")
    started = time.monotonic()
    events = queue.Queue(maxsize=8)
    stop = threading.Event()
    process = worker = job = None
    assigned = False
    result = dict(command=command, exit_code=None, error=None, cleanup_errors=[],
                  wall_seconds=None, log_bytes=0, job_accounting=None, job_memory=None,
                  terminal_job_accounting=False, configured_job_limits=None,
                  direct_exit_observed=False, pipe_eof_observed=False, post_exit_drain=None,
                  termination=dict(attempted=False, before_accounting=None, succeeded=False),
                  limits=dict(wall_seconds=wall_seconds, cpu_seconds=cpu_seconds,
                              log_bytes=log_bytes, committed_bytes=committed_bytes),
                  compile_cleanup=compile_cleanup_record(),
                  scope="compile-only owned job tree; intentional descendant cleanup is separate from natural exit; not a timing benchmark")

    def pump(stream):
        try:
            while not stop.is_set():
                raw = os.read(stream.fileno(), 65536)
                if not raw:
                    break
                while not stop.is_set():
                    try:
                        events.put(("data", raw), timeout=.05); break
                    except queue.Full:
                        pass
        except Exception as exc:
            while not stop.is_set():
                try:
                    events.put(("error", repr(exc)), timeout=.05); break
                except queue.Full:
                    pass
        finally:
            while not stop.is_set():
                try:
                    events.put(("eof", None), timeout=.05); break
                except queue.Full:
                    pass

    def observe():
        result["job_accounting"] = api.job_accounting(job)
        drain = result["post_exit_drain"]
        if drain is not None:
            actual = dict(result["job_accounting"])
            if drain["initial_accounting"] is None:
                drain["initial_accounting"] = actual
            drain["last_accounting"] = actual
            drain["observation_count"] += 1
            if len(drain["observations"]) < 16:
                drain["observations"].append(dict(wall_seconds=time.monotonic() - started, accounting=actual))
        result["job_memory"] = api.job_memory(job)
        need(result["job_accounting"]["total_cpu_100ns"] / 1e7 <= cpu_seconds, "child CPU bound")
        need(result["job_memory"]["peak_job_memory_used_bytes"] <= committed_bytes, "child committed-memory bound")
        need(time.monotonic() - started <= wall_seconds, "child wall bound")

    try:
        check()
        job = api.create_process_job()
        limits = api.JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        # Microsoft JOBOBJECT_BASIC_LIMIT_INFORMATION: 0x200 is JOB_MEMORY.
        limits.basic_limit_information.limit_flags = api.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | 0x200
        limits.job_memory_limit = committed_bytes
        if not api.kernel32.SetInformationJobObject(job, api.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                                                    ctypes.byref(limits), ctypes.sizeof(limits)):
            raise ctypes.WinError(ctypes.get_last_error())
        observed_limits = api.JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        returned = api.wt.DWORD()
        if not api.kernel32.QueryInformationJobObject(job, api.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                                                      ctypes.byref(observed_limits), ctypes.sizeof(observed_limits),
                                                      ctypes.byref(returned)):
            raise ctypes.WinError(ctypes.get_last_error())
        result["configured_job_limits"] = dict(flags=int(observed_limits.basic_limit_information.limit_flags),
                                                committed_bytes=int(observed_limits.job_memory_limit))
        need(result["configured_job_limits"]["flags"] & 0x200
             and result["configured_job_limits"]["committed_bytes"] == committed_bytes,
             "Job memory limit readback")
        with log.open("xb") as stream:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0,
                                       creationflags=api.CREATE_SUSPENDED | subprocess.CREATE_NO_WINDOW)
            api.assign_process_to_job(job, process)
            assigned = True
            worker = threading.Thread(target=pump, args=(process.stdout,), daemon=True)
            worker.start()
            eof = False
            while not eof or process.poll() is None:
                observe(); check()
                try:
                    kind, value = events.get(timeout=.02)
                except queue.Empty:
                    continue
                if kind == "eof":
                    eof = True
                    result["pipe_eof_observed"] = True
                    continue
                need(kind != "error", "child log read: " + str(value))
                remaining = log_bytes - result["log_bytes"]
                kept = value[:remaining]
                written = stream.write(kept)
                result["log_bytes"] += written
                need(written == len(kept), "short child log write")
                need(len(value) <= remaining, "child log bound")
            result["exit_code"] = process.wait(timeout=1)
            result["direct_exit_observed"] = True
            stream.flush(); os.fsync(stream.fileno())
        result["post_exit_drain"] = dict(initial_accounting=None, last_accounting=None,
            observations=[], observation_count=0, completed=False,
            started_wall_seconds=time.monotonic() - started, ended_wall_seconds=None)
        try:
            finish_compile_cleanup(result, api, job, started, wall_seconds, observe, check)
            result["post_exit_drain"]["completed"] = result["compile_cleanup"]["completed"]
        finally:
            result["post_exit_drain"]["ended_wall_seconds"] = time.monotonic() - started
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        # Retain the owned handle through termination and final accounting.
        if job:
            try:
                result["job_accounting"] = api.job_accounting(job)
                if result["job_accounting"]["active_processes"]:
                    result["termination"]["attempted"] = True
                    result["termination"]["before_accounting"] = dict(result["job_accounting"])
                    api.kernel32.TerminateJobObject.argtypes = [api.wt.HANDLE, api.wt.UINT]
                    api.kernel32.TerminateJobObject.restype = api.wt.BOOL
                    if not api.kernel32.TerminateJobObject(job, 0xE193C0DE):
                        raise ctypes.WinError(ctypes.get_last_error())
                    result["termination"]["succeeded"] = True
                    termination_deadline = time.monotonic() + 5
                    while result["job_accounting"]["active_processes"]:
                        need(time.monotonic() <= termination_deadline, "owned job termination did not complete")
                        time.sleep(.01)
                        result["job_accounting"] = api.job_accounting(job)
                result["terminal_job_accounting"] = assigned and result["job_accounting"]["active_processes"] == 0
                result["job_memory"] = api.job_memory(job)
            except Exception as exc:
                result["cleanup_errors"].append("final job observation: " + repr(exc))
            if not api.kernel32.CloseHandle(job):
                result["cleanup_errors"].append("CloseHandle(job) failed")
        if process is not None:
            # Covers assignment failure while the direct child is suspended.
            if not assigned and process.poll() is None:
                try:
                    process.kill()
                except Exception as exc:
                    result["cleanup_errors"].append("unassigned own child: " + repr(exc))
            try:
                result["exit_code"] = process.wait(timeout=5)
            except Exception as exc:
                result["cleanup_errors"].append("own child wait: " + repr(exc))
        stop.set()
        if worker is not None:
            worker.join(timeout=1)
            if worker.is_alive():
                result["cleanup_errors"].append("log worker still alive")
        if process is not None and process.stdout is not None and (worker is None or not worker.is_alive()):
            try:
                process.stdout.close()
            except Exception as exc:
                result["cleanup_errors"].append("final child stdout close: " + repr(exc))
        try:
            if log.exists():
                result["log"] = {"path": str(log.resolve()), **binding(log)}
                if result["log"]["bytes"] != result["log_bytes"]:
                    result["cleanup_errors"].append("actual child log extent mismatch")
        except Exception as exc:
            result["cleanup_errors"].append("final child log binding: " + repr(exc))
        result["wall_seconds"] = time.monotonic() - started
        if result["wall_seconds"] > wall_seconds and result["error"] is None:
            result["error"] = "child wall bound through final observation"
        if result["error"] is None and result["job_accounting"] is not None:
            if result["job_accounting"]["total_cpu_100ns"] / 1e7 > cpu_seconds:
                result["error"] = "child CPU bound through final observation"
        if result["error"] is None and result["job_memory"] is not None:
            if result["job_memory"]["peak_job_memory_used_bytes"] > committed_bytes:
                result["error"] = "child committed-memory bound through final observation"
    return result
