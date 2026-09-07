"""Prospective bounded phase diagnostics; inherited sampler remains untouched."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import importlib.util
import os
from pathlib import Path
from collections import deque
import subprocess
import sys
import time
import uuid
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INHERITED = ROOT / "experiments/m12-scorecard/m12-harness.py"
spec = importlib.util.spec_from_file_location("m192c_inherited", INHERITED)
h = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = h
spec.loader.exec_module(h)

PHASES = ("sleep-wakeup", "job-pids", "process-table", "process-counters",
          "job-accounting", "job-memory", "temp-scan", "telemetry",
          "final-accounting", "final-memory", "final-poll")
INTERVAL_NS = 10_000_000
k32 = h.kernel32
k32.GetCurrentProcessorNumber.restype = wt.DWORD
power = ctypes.WinDLL("powrprof", use_last_error=True)
power.CallNtPowerInformation.argtypes = [ctypes.c_int, ctypes.c_void_p, wt.ULONG,
                                       ctypes.c_void_p, wt.ULONG]
power.CallNtPowerInformation.restype = ctypes.c_long
power.PowerGetActiveScheme.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
power.PowerGetActiveScheme.restype = wt.DWORD
k32.LocalFree.argtypes = [ctypes.c_void_p]
k32.LocalFree.restype = ctypes.c_void_p


class ProcessorPower(ctypes.Structure):
    _fields_ = [(n, wt.ULONG) for n in
                ("number", "max_mhz", "current_mhz", "mhz_limit", "max_idle_state", "current_idle_state")]


def telemetry():
    begin = time.perf_counter_ns()
    row = {"start_ns": begin, "observer_cpu_number": int(k32.GetCurrentProcessorNumber()),
           "observer_process_cpu_s": time.process_time(),
           "observer_thread_cpu_s": time.thread_time(), "host": h.system_times()}
    try:
        row["per_core_cpu_seconds"] = [r._asdict() for r in psutil.cpu_times(percpu=True)]
    except Exception as exc:
        row["per_core_cpu_seconds"] = {"unavailable": repr(exc)}
    buffer = (ProcessorPower * (os.cpu_count() or 1))()
    status = power.CallNtPowerInformation(11, None, 0, buffer, ctypes.sizeof(buffer))
    row["power_query_status"] = int(status)
    row["processor_power"] = ([{n: int(getattr(p, n)) for n, _ in ProcessorPower._fields_}
                               for p in buffer] if status == 0 else {"unavailable": int(status)})
    ptr = ctypes.c_void_p()
    status = power.PowerGetActiveScheme(None, ctypes.byref(ptr))
    if status == 0:
        try:
            row["active_power_scheme"] = str(uuid.UUID(bytes_le=ctypes.string_at(ptr, 16)))
        finally:
            k32.LocalFree(ptr)
    else:
        row["active_power_scheme"] = {"unavailable": int(status)}
    row["end_ns"] = time.perf_counter_ns()
    return row


class Trace:
    def __init__(self, enabled, injection=None, delay_s=.150, placebo=False):
        self.enabled, self.injection, self.delay_s = enabled, injection, delay_s
        self.placebo = placebo
        self.injected = False
        self.events = deque(maxlen=4096)
        self.observations = deque(maxlen=1000)
        self.incidents = deque(maxlen=32)
        self.pending = []
        self.dropped = {"events": 0, "observations": 0, "incidents": 0, "telemetry": 0}
        self.phase_max_ms = {}
        self.phase_counts = {}
        self.poll = -1

    def incident(self, trigger):
        incident = {"trigger": trigger, "context": list(self.events)[-16:], "following": []}
        if len(self.incidents) == self.incidents.maxlen:
            self.dropped["incidents"] += 1
        self.incidents.append(incident)
        self.pending.append(incident)

    def event(self, row):
        for incident in self.pending:
            incident["following"].append(row)
        self.pending = [r for r in self.pending if len(r["following"]) < 16]
        if len(self.events) == self.events.maxlen:
            self.dropped["events"] += 1
        self.events.append(row)
        if row["wall_ms"] > 50:
            self.incident({"kind": "phase", "phase": row["phase"], "end_ns": row["end_ns"]})

    def call(self, phase, function, *args, **kwargs):
        if not self.enabled:
            return function(*args, **kwargs)
        begin, cpu_begin = time.perf_counter_ns(), time.thread_time_ns()
        inject = phase == self.injection and not self.injected
        try:
            if inject:
                self.injected = True
                if not self.placebo:
                    time.sleep(self.delay_s)
            return function(*args, **kwargs)
        finally:
            end, cpu_end = time.perf_counter_ns(), time.thread_time_ns()
            duration = (end - begin) / 1e6
            self.phase_max_ms[phase] = max(self.phase_max_ms.get(phase, 0), duration)
            self.phase_counts[phase] = self.phase_counts.get(phase, 0) + 1
            self.event({"phase": phase, "poll": self.poll, "start_ns": begin,
                "end_ns": end, "wall_ms": duration, "observer_thread_cpu_ms": (cpu_end-cpu_begin)/1e6,
                "injection_label": inject, "injected_delay_ms": self.delay_s*1000 if inject and not self.placebo else 0})

    def observe(self, row):
        if len(self.observations) == self.observations.maxlen:
            self.dropped["observations"] += 1
        self.observations.append(row)

    def result(self):
        return {"enabled": self.enabled, "phase_max_ms": self.phase_max_ms,
            "phase_counts": self.phase_counts, "events": list(self.events),
            "observations": list(self.observations), "incidents": list(self.incidents),
            "dropped": self.dropped, "injection": self.injection, "injected": self.injected,
            "placebo": self.placebo}


def monitor(*, argv, env, folder, mode="on", injection=None, delay_s=.150):
    folder.mkdir(parents=True, exist_ok=False)
    temp = folder / "temp"
    temp.mkdir()
    # Fixed temp content makes scan active without writing outside this run.
    (temp / "fixture.bin").write_bytes(bytes(4096))
    trace = Trace(mode != "off", injection, delay_s, placebo=(mode == "placebo"))
    start, observer_start, system_start = time.perf_counter_ns(), time.process_time(), h.system_times()
    memory_start = h.memory_status()
    known, samples, previous_start, legacy_max_gap = {}, 0, None, 0
    last_observation = start
    maximum_interval_ns, missed, peak_private = 0, 0, 0
    job_peak, max_temp, telemetry_rows = 0, 0, deque(maxlen=1000)
    final_accounting = None
    # No kill-on-close flag: even an observer exception waits for natural child exit.
    job = k32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    process = None
    try:
        with (folder / "stdout.log").open("w", encoding="utf-8") as out, \
             (folder / "stderr.log").open("w", encoding="utf-8") as err:
            process = subprocess.Popen(argv, env=env, stdout=out, stderr=err,
                creationflags=h.CREATE_SUSPENDED)
            # Assignment and resume occur before any injected phase.
            h.assign_process_to_job(job, process)
            next_sample, empty = start, 0
            while True:
                trace.poll = samples
                def sleep_until_due():
                    delay = (next_sample - time.perf_counter_ns()) / 1e9
                    if delay > 0:
                        time.sleep(delay)
                trace.call("sleep-wakeup", sleep_until_due)
                sampled_at = time.perf_counter_ns()
                if previous_start is not None:
                    legacy_max_gap = max(legacy_max_gap, sampled_at-previous_start)
                previous_start = sampled_at
                pids = set(trace.call("job-pids", h.job_process_ids, job))
                new = pids - set(known)
                table = trace.call("process-table", h.process_table) if new else {}
                rows = []
                for pid in pids:
                    counters = trace.call("process-counters", h.process_counters, pid)
                    if counters is None:
                        continue
                    prior = known.get(pid)
                    if prior is not None and prior["created"] != counters["created"]:
                        raise RuntimeError("PID reuse requires a new creation-identity entry")
                    known.setdefault(pid, {"pid": pid, "created": counters["created"],
                        "parent_pid": table.get(pid, {}).get("parent_pid"),
                        "name": table.get(pid, {}).get("name"), "first_seen_ns": sampled_at,
                        "peak_private_bytes": 0, "max_cpu_100ns": 0})
                    known[pid]["last_seen_ns"] = sampled_at
                    known[pid]["peak_private_bytes"] = max(known[pid]["peak_private_bytes"], counters["private"])
                    known[pid]["max_cpu_100ns"] = max(known[pid]["max_cpu_100ns"], counters["cpu_100ns"])
                    rows.append({"pid": pid, **counters})
                observed = time.perf_counter_ns()
                interval = observed - last_observation
                maximum_interval_ns = max(maximum_interval_ns, interval)
                if trace.enabled and interval > 50_000_000:
                    trace.incident({"kind": "observation-gap", "start_ns": last_observation,
                                    "end_ns": observed, "gap_ms": interval/1e6})
                last_observation = observed
                private = sum(r["private"] for r in rows)
                peak_private = max(peak_private, private)
                trace.observe({"poll": samples, "start_ns": sampled_at, "observed_ns": observed,
                               "private_bytes": private, "processes": rows})
                accounting = trace.call("job-accounting", h.job_accounting, job)
                memory = trace.call("job-memory", h.job_memory, job)
                job_peak = max(job_peak, memory["peak_job_memory_used_bytes"])
                if samples % 10 == 0:
                    max_temp = max(max_temp, trace.call("temp-scan", h.tree_bytes, temp))
                    if trace.enabled:
                        trow = trace.call("telemetry", telemetry)
                        trow["product_cpu_100ns"] = accounting["total_cpu_100ns"]
                        if len(telemetry_rows) == telemetry_rows.maxlen:
                            trace.dropped["telemetry"] += 1
                        telemetry_rows.append(trow)
                samples += 1
                root_done = process.poll() is not None
                empty = empty+1 if root_done and accounting["active_processes"] == 0 else 0
                if empty >= 2:
                    break
                next_sample += INTERVAL_NS
                if next_sample <= sampled_at:
                    skipped = (sampled_at - next_sample) // INTERVAL_NS + 1
                    missed += skipped
                    next_sample += skipped * INTERVAL_NS
            returncode = trace.call("final-poll", process.wait)
            final_accounting = trace.call("final-accounting", h.job_accounting, job)
            final_memory = trace.call("final-memory", h.job_memory, job)
            job_peak = max(job_peak, final_memory["peak_job_memory_used_bytes"])
            closed_at = time.perf_counter_ns()
            tail_interval_ns = closed_at - last_observation
            maximum_interval_ns = max(maximum_interval_ns, tail_interval_ns)
            if trace.enabled and tail_interval_ns > 50_000_000:
                trace.incident({"kind": "final-closure-gap", "start_ns": last_observation,
                                "end_ns": closed_at, "gap_ms": tail_interval_ns/1e6})
    finally:
        if process is not None:
            process.wait()  # Own, bounded synthetic process; never terminate it.
        k32.CloseHandle(job)
    end, observer_end, system_end = time.perf_counter_ns(), time.process_time(), h.system_times()
    wall = (end-start)/1e9
    product_cpu = final_accounting["total_cpu_100ns"]/1e7
    host_cpu = (system_end["busy_100ns"]-system_start["busy_100ns"])/1e7
    coverage = samples/(samples+missed)
    return {"argv": argv, "mode": mode, "start_ns": start, "end_ns": end,
        "returncode": returncode, "wall_seconds": wall, "observer_cpu_seconds": observer_end-observer_start,
        "product_cpu_seconds": product_cpu, "host_busy_cpu_seconds": host_cpu,
        "external_busy_fraction": max(0, host_cpu-product_cpu-(observer_end-observer_start))/(wall*(os.cpu_count() or 1)),
        "host_start": system_start, "host_end": system_end, "memory_start": memory_start,
        "max_interval_ms_including_final": maximum_interval_ns/1e6, "final_interval_ms": tail_interval_ns/1e6,
        "legacy_start_max_gap_ms": legacy_max_gap/1e6,
        "sample_count": samples, "missed_intervals": int(missed), "coverage": coverage,
        "sampling_pass": maximum_interval_ns <= 100_000_000 and coverage >= .9,
        "peak_private_bytes": peak_private, "job_peak_bytes": job_peak, "temp_peak_bytes": max_temp,
        "job_accounting": final_accounting, "processes": list(known.values()),
        "telemetry": list(telemetry_rows), "trace": trace.result(),
        "unavailable": ["effective CPU frequency", "per-core residency", "all-thread migration history",
                        "ready-queue latency", "spin versus useful CPU", "thermal sensor telemetry"],
        "frequency_semantics": "OS CurrentMhz = specified maximum times throttle; not effective cycles/wall"}
