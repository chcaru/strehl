"""Owned Windows child tree, bounded logs and observed CPU; no launch on import.

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
                  limits=dict(wall_seconds=wall_seconds, cpu_seconds=cpu_seconds,
                              log_bytes=log_bytes, committed_bytes=committed_bytes),
                  scope="owned job tree; committed memory, observed user+kernel CPU; not RSS or a timing benchmark")

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
                    eof = True; continue
                need(kind != "error", "child log read: " + str(value))
                remaining = log_bytes - result["log_bytes"]
                kept = value[:remaining]
                written = stream.write(kept)
                result["log_bytes"] += written
                need(written == len(kept), "short child log write")
                need(len(value) <= remaining, "child log bound")
            result["exit_code"] = process.wait(timeout=1)
            stream.flush(); os.fsync(stream.fileno())
        observe(); check()
        need(result["job_accounting"]["active_processes"] == 0, "child left an active descendant")
    except Exception as exc:
        result["error"] = repr(exc)
    finally:
        # Retain the owned handle through termination and final accounting.
        if job:
            try:
                result["job_accounting"] = api.job_accounting(job)
                if result["job_accounting"]["active_processes"]:
                    api.kernel32.TerminateJobObject.argtypes = [api.wt.HANDLE, api.wt.UINT]
                    api.kernel32.TerminateJobObject.restype = api.wt.BOOL
                    if not api.kernel32.TerminateJobObject(job, 0xE193C0DE):
                        raise ctypes.WinError(ctypes.get_last_error())
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
    return result
