from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import tifffile

from m11_core import (
    LANE_ROOT,
    require_guard,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)


SAMPLE_INTERVAL_S = 0.010
CREATE_SUSPENDED = 0x00000004
TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_VM_READ = 0x0010
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS = 3
JOB_OBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION_CLASS = 8
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
FILE_SHARE_READ = 0x00000001
FILE_FLAG_NO_BUFFERING = 0x20000000
FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
MEM_RELEASE = 0x00008000
PAGE_READWRITE = 0x04

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

kernel32.QueryPerformanceCounter.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
kernel32.QueryPerformanceCounter.restype = wt.BOOL
kernel32.QueryPerformanceFrequency.argtypes = [ctypes.POINTER(ctypes.c_longlong)]
kernel32.QueryPerformanceFrequency.restype = wt.BOOL


def qpc_frequency() -> int:
    value = ctypes.c_longlong()
    if not kernel32.QueryPerformanceFrequency(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    if value.value <= 0:
        raise RuntimeError("QueryPerformanceFrequency returned a non-positive value")
    return int(value.value)


def qpc_ticks() -> int:
    value = ctypes.c_longlong()
    if not kernel32.QueryPerformanceCounter(ctypes.byref(value)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(value.value)


def qpc_ticks_to_ns(ticks: int, frequency: int) -> int:
    return (int(ticks) * 1_000_000_000) // int(frequency)


class FILETIME(ctypes.Structure):
    _fields_ = [("low", wt.DWORD), ("high", wt.DWORD)]

    def value(self) -> int:
        return (int(self.high) << 32) | int(self.low)


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", wt.WCHAR * 260),
    ]


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("page_fault_count", wt.DWORD),
        ("peak_working_set_size", ctypes.c_size_t),
        ("working_set_size", ctypes.c_size_t),
        ("quota_peak_paged_pool_usage", ctypes.c_size_t),
        ("quota_paged_pool_usage", ctypes.c_size_t),
        ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
        ("quota_non_paged_pool_usage", ctypes.c_size_t),
        ("pagefile_usage", ctypes.c_size_t),
        ("peak_pagefile_usage", ctypes.c_size_t),
        ("private_usage", ctypes.c_size_t),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("read_operation_count", ctypes.c_ulonglong),
        ("write_operation_count", ctypes.c_ulonglong),
        ("other_operation_count", ctypes.c_ulonglong),
        ("read_transfer_count", ctypes.c_ulonglong),
        ("write_transfer_count", ctypes.c_ulonglong),
        ("other_transfer_count", ctypes.c_ulonglong),
    ]

    def to_json(self) -> dict[str, int]:
        return {
            "read_operations": int(self.read_operation_count),
            "write_operations": int(self.write_operation_count),
            "other_operations": int(self.other_operation_count),
            "read_bytes": int(self.read_transfer_count),
            "write_bytes": int(self.write_transfer_count),
            "other_bytes": int(self.other_transfer_count),
        }


class JOBOBJECT_BASIC_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("total_user_time", ctypes.c_longlong),
        ("total_kernel_time", ctypes.c_longlong),
        ("this_period_total_user_time", ctypes.c_longlong),
        ("this_period_total_kernel_time", ctypes.c_longlong),
        ("total_page_fault_count", wt.DWORD),
        ("total_processes", wt.DWORD),
        ("active_processes", wt.DWORD),
        ("total_terminated_processes", wt.DWORD),
    ]

    def to_json(self) -> dict[str, int]:
        return {
            "total_user_100ns": int(self.total_user_time),
            "total_kernel_100ns": int(self.total_kernel_time),
            "total_cpu_100ns": int(self.total_user_time + self.total_kernel_time),
            "total_page_fault_count": int(self.total_page_fault_count),
            "total_processes": int(self.total_processes),
            "active_processes": int(self.active_processes),
            "total_terminated_processes": int(self.total_terminated_processes),
        }


class JOBOBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("basic_info", JOBOBJECT_BASIC_ACCOUNTING_INFORMATION),
        ("io_info", IO_COUNTERS),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("per_process_user_time_limit", ctypes.c_longlong),
        ("per_job_user_time_limit", ctypes.c_longlong),
        ("limit_flags", wt.DWORD),
        ("minimum_working_set_size", ctypes.c_size_t),
        ("maximum_working_set_size", ctypes.c_size_t),
        ("active_process_limit", wt.DWORD),
        ("affinity", ctypes.c_size_t),
        ("priority_class", wt.DWORD),
        ("scheduling_class", wt.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("basic_limit_information", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("io_info", IO_COUNTERS),
        ("process_memory_limit", ctypes.c_size_t),
        ("job_memory_limit", ctypes.c_size_t),
        ("peak_process_memory_used", ctypes.c_size_t),
        ("peak_job_memory_used", ctypes.c_size_t),
    ]


kernel32.CreateToolhelp32Snapshot.argtypes = [wt.DWORD, wt.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wt.HANDLE
kernel32.Process32FirstW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32FirstW.restype = wt.BOOL
kernel32.Process32NextW.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
kernel32.Process32NextW.restype = wt.BOOL
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.CloseHandle.restype = wt.BOOL
kernel32.GetProcessTimes.argtypes = [
    wt.HANDLE,
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
]
kernel32.GetProcessTimes.restype = wt.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wt.HANDLE,
    wt.DWORD,
    wt.LPWSTR,
    ctypes.POINTER(wt.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wt.BOOL
kernel32.K32GetProcessMemoryInfo.argtypes = [
    wt.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX),
    wt.DWORD,
]
kernel32.K32GetProcessMemoryInfo.restype = wt.BOOL
kernel32.GetSystemTimes.argtypes = [
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
    ctypes.POINTER(FILETIME),
]
kernel32.GetSystemTimes.restype = wt.BOOL
kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
kernel32.CreateJobObjectW.restype = wt.HANDLE
kernel32.AssignProcessToJobObject.argtypes = [wt.HANDLE, wt.HANDLE]
kernel32.AssignProcessToJobObject.restype = wt.BOOL
kernel32.SetInformationJobObject.argtypes = [
    wt.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wt.DWORD,
]
kernel32.SetInformationJobObject.restype = wt.BOOL
kernel32.QueryInformationJobObject.argtypes = [
    wt.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    wt.DWORD,
    ctypes.POINTER(wt.DWORD),
]
kernel32.QueryInformationJobObject.restype = wt.BOOL
kernel32.CreateFileW.argtypes = [
    wt.LPCWSTR,
    wt.DWORD,
    wt.DWORD,
    ctypes.c_void_p,
    wt.DWORD,
    wt.DWORD,
    wt.HANDLE,
]
kernel32.CreateFileW.restype = wt.HANDLE
kernel32.FlushFileBuffers.argtypes = [wt.HANDLE]
kernel32.FlushFileBuffers.restype = wt.BOOL
kernel32.ReadFile.argtypes = [
    wt.HANDLE,
    ctypes.c_void_p,
    wt.DWORD,
    ctypes.POINTER(wt.DWORD),
    ctypes.c_void_p,
]
kernel32.ReadFile.restype = wt.BOOL
kernel32.VirtualAlloc.argtypes = [
    ctypes.c_void_p,
    ctypes.c_size_t,
    wt.DWORD,
    wt.DWORD,
]
kernel32.VirtualAlloc.restype = ctypes.c_void_p
kernel32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
kernel32.VirtualFree.restype = wt.BOOL
kernel32.GetDiskFreeSpaceW.argtypes = [
    wt.LPCWSTR,
    ctypes.POINTER(wt.DWORD),
    ctypes.POINTER(wt.DWORD),
    ctypes.POINTER(wt.DWORD),
    ctypes.POINTER(wt.DWORD),
]
kernel32.GetDiskFreeSpaceW.restype = wt.BOOL


def sha256_file_uncached(path: Path, block_size: int = 8 << 20) -> str:
    """Hash through an unbuffered Windows handle without warming the page cache."""

    resolved = path.resolve(strict=True)
    sectors_per_cluster = wt.DWORD()
    bytes_per_sector = wt.DWORD()
    free_clusters = wt.DWORD()
    total_clusters = wt.DWORD()
    if not kernel32.GetDiskFreeSpaceW(
        resolved.anchor,
        ctypes.byref(sectors_per_cluster),
        ctypes.byref(bytes_per_sector),
        ctypes.byref(free_clusters),
        ctypes.byref(total_clusters),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    sector = int(bytes_per_sector.value)
    request_size = max(sector, (int(block_size) // sector) * sector)
    handle = kernel32.CreateFileW(
        str(resolved),
        GENERIC_READ,
        FILE_SHARE_READ,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL | FILE_FLAG_NO_BUFFERING | FILE_FLAG_SEQUENTIAL_SCAN,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    buffer = kernel32.VirtualAlloc(
        None,
        request_size,
        MEM_COMMIT | MEM_RESERVE,
        PAGE_READWRITE,
    )
    if not buffer:
        error = ctypes.get_last_error()
        kernel32.CloseHandle(handle)
        raise ctypes.WinError(error)
    digest = hashlib.sha256()
    try:
        while True:
            read = wt.DWORD()
            if not kernel32.ReadFile(
                handle,
                buffer,
                request_size,
                ctypes.byref(read),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())
            if read.value == 0:
                break
            digest.update(ctypes.string_at(buffer, read.value))
    finally:
        kernel32.VirtualFree(buffer, 0, MEM_RELEASE)
        kernel32.CloseHandle(handle)
    return digest.hexdigest().upper()


ntdll.NtResumeProcess.argtypes = [wt.HANDLE]
ntdll.NtResumeProcess.restype = ctypes.c_long


class ReadOnlyFileLocks:
    def __init__(self, paths: list[Path]) -> None:
        self._handles: list[wt.HANDLE] = []
        try:
            for path in paths:
                handle = kernel32.CreateFileW(
                    str(path.resolve(strict=True)),
                    GENERIC_READ,
                    FILE_SHARE_READ,
                    None,
                    OPEN_EXISTING,
                    FILE_ATTRIBUTE_NORMAL,
                    None,
                )
                if handle == INVALID_HANDLE_VALUE:
                    raise ctypes.WinError(ctypes.get_last_error())
                self._handles.append(handle)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        while self._handles:
            kernel32.CloseHandle(self._handles.pop())

    def __enter__(self) -> ReadOnlyFileLocks:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def __del__(self) -> None:
        self.close()


def process_table() -> dict[int, dict[str, Any]]:
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    rows: dict[int, dict[str, Any]] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while ok:
            rows[int(entry.th32ProcessID)] = {
                "parent_pid": int(entry.th32ParentProcessID),
                "name": str(entry.szExeFile),
            }
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)
    return rows


def process_counters(pid: int) -> dict[str, int] | None:
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
    )
    if not handle:
        return None
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(counters)
        if not kernel32.K32GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            return None
        created = FILETIME()
        exited = FILETIME()
        kernel = FILETIME()
        user = FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        return {
            "created_100ns": created.value(),
            "private_bytes": int(counters.private_usage),
            "working_set_bytes": int(counters.working_set_size),
            "page_faults": int(counters.page_fault_count),
            "cpu_100ns": kernel.value() + user.value(),
        }
    finally:
        kernel32.CloseHandle(handle)


def system_times() -> dict[str, int]:
    idle = FILETIME()
    kernel = FILETIME()
    user = FILETIME()
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    total = kernel.value() + user.value()
    return {
        "idle_100ns": idle.value(),
        "kernel_100ns": kernel.value(),
        "user_100ns": user.value(),
        "total_100ns": total,
        "busy_100ns": total - idle.value(),
    }


def create_job() -> wt.HANDLE:
    job = kernel32.CreateJobObjectW(None, None)
    if not job:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    limits.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(job)
        raise ctypes.WinError(error)
    return job


def assign_and_resume(job: wt.HANDLE, process: subprocess.Popen[bytes]) -> None:
    process_handle = wt.HANDLE(int(process._handle))
    if not kernel32.AssignProcessToJobObject(job, process_handle):
        raise ctypes.WinError(ctypes.get_last_error())
    status = ntdll.NtResumeProcess(process_handle)
    if status != 0:
        raise OSError(
            f"NtResumeProcess failed with NTSTATUS 0x{status & 0xFFFFFFFF:08X}"
        )


def job_process_ids(job: wt.HANDLE) -> list[int]:
    capacity = 1024
    buffer = ctypes.create_string_buffer(
        2 * ctypes.sizeof(wt.DWORD) + capacity * ctypes.sizeof(ctypes.c_size_t)
    )
    returned = wt.DWORD()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS,
        buffer,
        ctypes.sizeof(buffer),
        ctypes.byref(returned),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    header = (wt.DWORD * 2).from_buffer(buffer)
    count = int(header[1])
    if count > capacity:
        raise RuntimeError(f"job process count {count} exceeds capacity {capacity}")
    process_ids = (ctypes.c_size_t * count).from_buffer(
        buffer,
        2 * ctypes.sizeof(wt.DWORD),
    )
    return [int(pid) for pid in process_ids]


def job_accounting(job: wt.HANDLE) -> dict[str, Any]:
    value = JOBOBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION()
    returned = wt.DWORD()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION_CLASS,
        ctypes.byref(value),
        ctypes.sizeof(value),
        ctypes.byref(returned),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        **value.basic_info.to_json(),
        "io": value.io_info.to_json(),
    }


def job_memory(job: wt.HANDLE) -> dict[str, int]:
    value = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    returned = wt.DWORD()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(value),
        ctypes.sizeof(value),
        ctypes.byref(returned),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "peak_process_memory_used_bytes": int(value.peak_process_memory_used),
        "peak_job_memory_used_bytes": int(value.peak_job_memory_used),
    }


class GpuSampler:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.samples: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._process: subprocess.Popen[str] | None = None

    @property
    def source(self) -> str:
        return str(self.config.get("source", ""))

    def start(self) -> None:
        if self.config.get("kind") == "synthetic-zero":
            self.capture_synthetic()
            self._ready.set()
            return
        if self.config.get("kind") != "command":
            self.errors.append("unsupported GPU sampler kind")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        argv = [str(token) for token in self.config.get("argv", [])]
        try:
            self._process = subprocess.Popen(
                argv,
                cwd=self.config.get("cwd"),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            if self._process.stdout is None:
                raise RuntimeError("hardware telemetry probe has no stdout stream")
            while not self._stop.is_set():
                line = self._process.stdout.readline()
                if not line:
                    if self._process.poll() is not None:
                        if not self._stop.is_set():
                            self.errors.append(
                                "hardware telemetry probe exited before stop"
                            )
                        break
                    continue
                try:
                    observed = strict_json_loads(line)
                    value = float(observed["gpu_utilization_percent"])
                    thermal_c = float(observed["thermal_c"])
                    throttle = observed["hardware_throttle"]
                    gpu_processes = observed["gpu_processes"]
                    if (
                        not 0.0 <= value <= 100.0
                        or not (-100.0 <= thermal_c <= 200.0)
                        or not isinstance(throttle, bool)
                        or not isinstance(gpu_processes, list)
                        or any(
                            not isinstance(row, dict)
                            or not isinstance(row.get("pid"), int)
                            or row["pid"] < 0
                            or not isinstance(row.get("image_path"), str)
                            or not row["image_path"]
                            for row in gpu_processes
                        )
                    ):
                        raise ValueError(
                            "hardware telemetry probe emitted an invalid row"
                        )
                    self.samples.append(
                        {
                            "qpc_ticks": qpc_ticks(),
                            "qpc_frequency": qpc_frequency(),
                            "utilization_percent": value,
                            "thermal_c": thermal_c,
                            "hardware_throttle": throttle,
                            "gpu_processes": gpu_processes,
                        }
                    )
                    self._ready.set()
                except (KeyError, TypeError, ValueError) as error:
                    self.errors.append(str(error))
        except OSError as error:
            self.errors.append(str(error))
        finally:
            process = self._process
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=1.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process is not None and process.stdout is not None:
                process.stdout.close()
            self._process = None
            self._ready.set()

    def wait_ready(self, timeout: float = 5.0) -> None:
        if not self._ready.wait(timeout) or not self.samples:
            detail = "; ".join(self.errors) if self.errors else "no sample received"
            raise RuntimeError(
                f"hardware telemetry probe did not become ready: {detail}"
            )

    def stop(self) -> None:
        if self.config.get("kind") == "synthetic-zero":
            self.capture_synthetic()
            return
        self._stop.set()
        process = self._process
        if process is not None and process.poll() is None:
            process.terminate()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                process = self._process
                if process is not None and process.poll() is None:
                    process.kill()
                self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                self.errors.append("hardware telemetry sampler thread did not stop")

    def capture_synthetic(self) -> None:
        if self.config.get("kind") != "synthetic-zero":
            return
        self.samples.append(
            {
                "qpc_ticks": qpc_ticks(),
                "qpc_frequency": qpc_frequency(),
                "utilization_percent": 0.0,
                "thermal_c": 0.0,
                "hardware_throttle": False,
                "gpu_processes": [],
            }
        )


class CpuSampler:
    def __init__(self) -> None:
        self.samples: list[dict[str, int]] = []
        self.missed_intervals = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        frequency = qpc_frequency()
        next_sample = time.perf_counter()
        while not self._stop.is_set():
            now = time.perf_counter()
            if now < next_sample:
                self._stop.wait(next_sample - now)
                if self._stop.is_set():
                    break
            sampled = time.perf_counter()
            self.capture(frequency)
            next_sample += SAMPLE_INTERVAL_S
            if next_sample <= sampled:
                skipped = int((sampled - next_sample) // SAMPLE_INTERVAL_S) + 1
                self.missed_intervals += skipped
                next_sample += skipped * SAMPLE_INTERVAL_S

    def capture(self, frequency: int | None = None) -> None:
        self.samples.append(
            {
                "qpc_ticks": qpc_ticks(),
                "qpc_frequency": frequency or qpc_frequency(),
                **system_times(),
            }
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            if self._thread.is_alive():
                raise RuntimeError("CPU telemetry sampler thread did not stop")


def unapproved_gpu_processes(
    samples: list[dict[str, Any]],
    allowlist: list[dict[str, Any]],
    timed_pids: set[int],
) -> list[dict[str, Any]]:
    allowed_display = {
        (
            str(Path(row["image_path"]).resolve(strict=True)).casefold(),
            str(row["sha256"]).upper(),
        )
        for row in allowlist
    }
    observed: list[dict[str, Any]] = []
    observed_identities: set[tuple[int, str, str]] = set()
    for sample in samples:
        for gpu_process in sample["gpu_processes"]:
            pid = int(gpu_process["pid"])
            if pid in timed_pids:
                continue
            image_path = Path(gpu_process["image_path"]).resolve(strict=True)
            image_sha256 = sha256_file(image_path)
            identity = (str(image_path).casefold(), image_sha256)
            if identity in allowed_display:
                continue
            row_identity = (pid, str(image_path).casefold(), image_sha256)
            if row_identity not in observed_identities:
                observed_identities.add(row_identity)
                observed.append(
                    {
                        "pid": pid,
                        "image_path": str(image_path),
                        "image_sha256": image_sha256,
                    }
                )
    return observed


def exclusive_flush(path: Path) -> bool:
    handle = kernel32.CreateFileW(
        str(path.resolve()),
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        FILE_ATTRIBUTE_NORMAL,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not kernel32.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)
    return True


def write_json_flushed(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, allow_nan=False, indent=2, sort_keys=True)
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())


def tiff_witness(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tiff:
        if len(tiff.pages) != 1:
            raise ValueError(f"expected one TIFF page, got {len(tiff.pages)}")
        page = tiff.pages[0]
        shape = list(page.shape)
        bits = int(page.bitspersample)
        samples = int(page.samplesperpixel)
        compression = int(page.compression)
        dtype = str(page.dtype)
        icc_tag = page.tags.get(34675)
        icc = bytes(icc_tag.value) if icc_tag is not None else b""
        image_description = str(page.description or "")
        pixels = page.asarray()
        pixel_sha256 = sha256_bytes(memoryview(pixels).cast("B"))
    expected_shape = [
        int(contract["height"]),
        int(contract["width"]),
        int(contract.get("samples_per_pixel", 3)),
    ]
    expected_icc = str(contract["icc_sha256"]).upper()
    valid = (
        shape == expected_shape
        and dtype == "uint16"
        and bits == int(contract.get("bits_per_sample", 16))
        and samples == int(contract.get("samples_per_pixel", 3))
        and compression == 1
        and sha256_bytes(icc) == expected_icc
    )
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "shape": shape,
        "dtype": dtype,
        "bits_per_sample": bits,
        "samples_per_pixel": samples,
        "compression_code": compression,
        "compression": "NONE" if compression == 1 else f"TIFF-{compression}",
        "icc_sha256": sha256_bytes(icc),
        "image_description": image_description,
        "output_sha256": sha256_file(path),
        "pixel_sha256": pixel_sha256,
        "tiff_valid": valid,
        "highest_precision": dtype == "uint16" and bits == 16 and samples == 3,
    }


def stage_measurements(log_text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(?m)^M153_STAGE\s+(?P<stage>[A-Za-z0-9_-]+)"
        r"\s+wall_seconds=(?P<wall>[0-9]+(?:\.[0-9]+)?|unavailable)"
        r"\s+cpu_seconds=(?P<cpu>[0-9]+(?:\.[0-9]+)?|unavailable)"
        r"\s+source=(?P<source>[A-Za-z0-9_.-]+)\s*$"
    )
    rows = []
    for match in pattern.finditer(log_text):
        rows.append(
            {
                "stage": match.group("stage"),
                "wall_seconds": (
                    None
                    if match.group("wall") == "unavailable"
                    else float(match.group("wall"))
                ),
                "cpu_seconds": (
                    None
                    if match.group("cpu") == "unavailable"
                    else float(match.group("cpu"))
                ),
                "source": match.group("source"),
            }
        )
    return rows


def stage_banners(log_text: str) -> list[str]:
    return sorted({row["stage"] for row in stage_measurements(log_text)})


def process_image_witness(
    pid: int,
    preverified_hashes: dict[str, str] | None = None,
) -> dict[str, str | None] | None:
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION,
        False,
        pid,
    )
    if not handle:
        return None
    try:
        size = wt.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle,
            0,
            buffer,
            ctypes.byref(size),
        ):
            return None
        path = Path(buffer.value).resolve(strict=True)
        digest = (
            preverified_hashes.get(str(path).casefold())
            if preverified_hashes is not None
            else sha256_file(path)
        )
        return {"path": str(path), "sha256": digest}
    finally:
        kernel32.CloseHandle(handle)


def _monitor_process(
    *,
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    preverified_process_hashes: dict[str, str],
) -> dict[str, Any]:
    job = create_job()
    process: subprocess.Popen[bytes] | None = None
    known: dict[int, dict[str, Any]] = {}
    peak_private = 0
    peak_working_set = 0
    peak_process_count = 0
    sample_count = 0
    missed_intervals = 0
    counter_failures = 0
    gaps: list[float] = []
    last_sample: float | None = None
    root_exit_qpc_ticks: int | None = None
    drained_qpc_ticks: int | None = None
    final_accounting: dict[str, Any] | None = None
    started_qpc_ticks: int | None = None
    frequency = qpc_frequency()
    root_image: dict[str, str] | None = None
    peak_job_memory = {
        "peak_process_memory_used_bytes": 0,
        "peak_job_memory_used_bytes": 0,
    }
    assigned_before_resume = False
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            started_qpc_ticks = qpc_ticks()
            process = subprocess.Popen(
                argv,
                cwd=cwd,
                env=env,
                stdout=stdout,
                stderr=stderr,
                creationflags=CREATE_SUSPENDED,
            )
            root_image = process_image_witness(
                process.pid,
                preverified_process_hashes,
            )
            if root_image is None or root_image["sha256"] is None:
                raise RuntimeError("cannot identify the suspended root process image")
            root_counters = process_counters(process.pid)
            if root_counters is None:
                raise RuntimeError("cannot read suspended root process counters")
            root_seen_ticks = qpc_ticks()
            gaps.append((root_seen_ticks - started_qpc_ticks) / frequency)
            known[process.pid] = {
                "pid": process.pid,
                "parent_pid": process_table().get(process.pid, {}).get("parent_pid"),
                "name": process_table().get(process.pid, {}).get("name"),
                "created_100ns": root_counters["created_100ns"],
                "first_seen_qpc_ticks": root_seen_ticks,
                "last_seen_qpc_ticks": root_seen_ticks,
                "samples": 1,
                "image_path": root_image["path"],
                "image_sha256": root_image["sha256"],
            }
            peak_private = int(root_counters["private_bytes"])
            peak_working_set = int(root_counters["working_set_bytes"])
            sample_count = 1
            last_sample = time.perf_counter()
            next_sample = last_sample + SAMPLE_INTERVAL_S
            assign_and_resume(job, process)
            assigned_before_resume = True
            empty_after_root = 0
            while True:
                now = time.perf_counter()
                if now < next_sample:
                    time.sleep(next_sample - now)
                sampled = time.perf_counter()
                if last_sample is not None:
                    gaps.append(sampled - last_sample)
                last_sample = sampled
                pids = set(job_process_ids(job))
                table = process_table()
                rows: list[dict[str, int]] = []
                for pid in pids:
                    counters = process_counters(pid)
                    if counters is None:
                        counter_failures += 1
                        continue
                    prior = known.get(pid)
                    if prior is None:
                        image = process_image_witness(
                            pid,
                            preverified_process_hashes,
                        )
                        known[pid] = {
                            "pid": pid,
                            "parent_pid": table.get(pid, {}).get("parent_pid"),
                            "name": table.get(pid, {}).get("name"),
                            "created_100ns": counters["created_100ns"],
                            "first_seen_qpc_ticks": qpc_ticks(),
                            "last_seen_qpc_ticks": qpc_ticks(),
                            "samples": 1,
                            "image_path": image["path"] if image else None,
                            "image_sha256": image["sha256"] if image else None,
                        }
                    elif prior["created_100ns"] == counters["created_100ns"]:
                        prior["last_seen_qpc_ticks"] = qpc_ticks()
                        prior["samples"] += 1
                    rows.append(counters)
                peak_private = max(
                    peak_private,
                    sum(row["private_bytes"] for row in rows),
                )
                peak_working_set = max(
                    peak_working_set,
                    sum(row["working_set_bytes"] for row in rows),
                )
                accounting = job_accounting(job)
                memory = job_memory(job)
                peak_job_memory = {
                    key: max(peak_job_memory[key], memory[key])
                    for key in peak_job_memory
                }
                peak_process_count = max(
                    peak_process_count,
                    len(pids),
                    int(accounting["active_processes"]),
                )
                sample_count += 1
                root_done = process.poll() is not None
                if root_done and root_exit_qpc_ticks is None:
                    root_exit_qpc_ticks = qpc_ticks()
                if root_done and accounting["active_processes"] == 0:
                    empty_after_root += 1
                else:
                    empty_after_root = 0
                if root_done and empty_after_root >= 2:
                    drained_qpc_ticks = qpc_ticks()
                    final_accounting = accounting
                    break
                next_sample += SAMPLE_INTERVAL_S
                if next_sample <= sampled:
                    skipped = int((sampled - next_sample) // SAMPLE_INTERVAL_S) + 1
                    missed_intervals += skipped
                    next_sample += skipped * SAMPLE_INTERVAL_S
            returncode = process.wait()
            final_accounting = job_accounting(job)
            final_memory = job_memory(job)
            peak_job_memory = {
                key: max(peak_job_memory[key], final_memory[key])
                for key in peak_job_memory
            }
    finally:
        kernel32.CloseHandle(job)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
    if (
        final_accounting is None
        or started_qpc_ticks is None
        or root_exit_qpc_ticks is None
        or drained_qpc_ticks is None
        or root_image is None
    ):
        raise RuntimeError("process-tree accounting did not reach a drained state")
    return {
        "root_returncode": returncode,
        "root_image": root_image,
        "qpc_frequency": frequency,
        "started_qpc_ticks": started_qpc_ticks,
        "started_qpc_ns": qpc_ticks_to_ns(started_qpc_ticks, frequency),
        "job_assigned_before_resume": assigned_before_resume,
        "root_exit_qpc_ticks": root_exit_qpc_ticks,
        "root_exit_qpc_ns": qpc_ticks_to_ns(root_exit_qpc_ticks, frequency),
        "drained_qpc_ticks": drained_qpc_ticks,
        "drained_qpc_ns": qpc_ticks_to_ns(drained_qpc_ticks, frequency),
        "active_processes_final": int(final_accounting["active_processes"]),
        "process_count_total": int(final_accounting["total_processes"]),
        "process_images_preverified_before_timing": True,
        "accounting": final_accounting,
        "peak_private_committed_bytes": peak_private,
        "peak_working_set_bytes": peak_working_set,
        "peak_process_count": peak_process_count,
        "peak_job_memory": peak_job_memory,
        "sample_count": sample_count,
        "sample_interval_ms": int(SAMPLE_INTERVAL_S * 1000),
        "missed_intervals": missed_intervals,
        "counter_failures": counter_failures,
        "max_gap_ms": max(gaps, default=0.0) * 1000.0,
        "median_gap_ms": (sorted(gaps)[len(gaps) // 2] * 1000.0 if gaps else 0.0),
        "process_lifetimes": list(known.values()),
    }


def run_timed_invocation(
    *,
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    declared_environment: dict[str, str | None],
    output_path: Path,
    invocation_manifest_path: Path,
    stdout_path: Path,
    stderr_path: Path,
    output_contract: dict[str, Any],
    run_identity: dict[str, Any],
    required_stages: list[str],
    numeric_stage_timings_required: list[str] | None = None,
    gpu_config: dict[str, Any],
    child_expected: bool = False,
    live_marker_path: Path | None = None,
    process_image_bindings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    for path in (output_path, invocation_manifest_path, stdout_path, stderr_path):
        require_guard(
            "G01-owned-output",
            {"path": str(path), "lane_root": str(LANE_ROOT)},
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError(f"refusing to overwrite {path}")
    if process_image_bindings is None:
        root_path = Path(argv[0]).resolve(strict=True)
        preverified_process_hashes = {str(root_path).casefold(): sha256_file(root_path)}
    else:
        preverified_process_hashes = {
            str(Path(row["path"]).resolve(strict=True)).casefold(): str(
                row.get("sha256", row.get("actual_sha256"))
            )
            for row in process_image_bindings
        }
    gpu = GpuSampler(gpu_config)
    cpu = CpuSampler()
    gpu.start()
    gpu.wait_ready()
    cpu.start()
    system_start = system_times()
    observer_cpu_start = time.process_time()
    try:
        process = _monitor_process(
            argv=argv,
            cwd=cwd,
            env=env,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            preverified_process_hashes=preverified_process_hashes,
        )
        qpc_frequency_hz = int(process["qpc_frequency"])
        started_qpc_ticks = int(process["started_qpc_ticks"])
        if process["root_returncode"] != 0:
            raise RuntimeError(
                f"timed command exited {process['root_returncode']}: "
                f"{stderr_path.read_text(encoding='utf-8', errors='replace')[-4000:]}"
            )
        exclusive = exclusive_flush(output_path)
        output = tiff_witness(output_path, output_contract)
        log_text = stdout_path.read_text(encoding="utf-8", errors="replace")
        log_text += "\n" + stderr_path.read_text(encoding="utf-8", errors="replace")
        measurements = stage_measurements(log_text)
        stages = sorted({row["stage"] for row in measurements})
        live_marker = None
        if live_marker_path is not None:
            live_marker = strict_json_loads(
                live_marker_path.read_text(encoding="utf-8")
            )
            live_marker["path"] = str(live_marker_path.resolve())
            live_marker["sha256"] = sha256_file(live_marker_path)
        invocation_manifest = {
            "schema": "m153-invocation-manifest-v1",
            "run_identity": run_identity,
            "argv": argv,
            "cwd": str(cwd.resolve()),
            "declared_environment": declared_environment,
            "qpc_frequency": qpc_frequency_hz,
            "process_started_qpc_ticks": started_qpc_ticks,
            "process_drained_qpc_ticks": process["drained_qpc_ticks"],
            "process_tree": process,
            "stdout": {
                "path": str(stdout_path.resolve()),
                "sha256": sha256_file(stdout_path),
            },
            "stderr": {
                "path": str(stderr_path.resolve()),
                "sha256": sha256_file(stderr_path),
            },
            "stage_banners": stages,
            "stage_measurements": measurements,
            "gpu": {
                "source": gpu.source,
                "samples": list(gpu.samples),
                "errors": list(gpu.errors),
            },
            "live_marker": live_marker,
            "output": output,
            "output_flush_succeeded": exclusive,
            "timing_boundary": (
                "QPC starts immediately before suspended process creation; QPC stops "
                "only after process-tree drain, exclusive TIFF flush/validation/hash, "
                "and closed/flushed invocation-manifest hash."
            ),
        }
        write_json_flushed(invocation_manifest_path, invocation_manifest)
        manifest_flushed = exclusive_flush(invocation_manifest_path)
        manifest_structurally_valid = (
            strict_json_loads(invocation_manifest_path.read_text(encoding="utf-8"))
            == invocation_manifest
        )
        if not manifest_structurally_valid:
            raise RuntimeError("invocation manifest failed structural round-trip")
        manifest_sha256 = sha256_file(invocation_manifest_path)
        gpu.capture_synthetic()
        cpu.capture(qpc_frequency_hz)
        finalized_qpc_ticks = qpc_ticks()
        observer_cpu_seconds = time.process_time() - observer_cpu_start
        system_end = system_times()
    finally:
        cpu.stop()
        gpu.stop()
    wall_seconds = (finalized_qpc_ticks - started_qpc_ticks) / qpc_frequency_hz
    process_cpu_seconds = process["accounting"]["total_cpu_100ns"] / 10_000_000.0
    logical_processors = os.cpu_count() or 1
    busy_fraction = process_cpu_seconds / (wall_seconds * logical_processors)
    system_busy_seconds = (
        system_end["busy_100ns"] - system_start["busy_100ns"]
    ) / 10_000_000.0
    external_busy_seconds = max(
        0.0,
        system_busy_seconds - process_cpu_seconds,
    )
    external_busy_fraction = external_busy_seconds / (wall_seconds * logical_processors)
    timed_pids = {int(row["pid"]) for row in process["process_lifetimes"]}
    cpu_samples = sorted(
        [
            sample
            for sample in cpu.samples
            if started_qpc_ticks <= int(sample["qpc_ticks"]) <= finalized_qpc_ticks
        ],
        key=lambda sample: int(sample["qpc_ticks"]),
    )
    hardware_samples = [
        sample
        for sample in gpu.samples
        if started_qpc_ticks <= int(sample["qpc_ticks"]) <= finalized_qpc_ticks
    ]
    observed_external_gpu = unapproved_gpu_processes(
        hardware_samples,
        gpu_config.get("os_display_process_allowlist", []),
        timed_pids,
    )
    finalization = {
        "exclusive_open_succeeded": exclusive,
        "output_flush_succeeded": exclusive,
        "manifest_flush_succeeded": manifest_flushed,
        "manifest_structurally_valid": manifest_structurally_valid,
        "tiff_valid": output["tiff_valid"],
        "highest_precision": output["highest_precision"],
        "compression": output["compression"],
        "output_sha256": output["output_sha256"],
        "pixel_sha256": output["pixel_sha256"],
        "manifest_sha256": manifest_sha256,
        "qpc_frequency": qpc_frequency_hz,
        "process_drained_qpc_ticks": process["drained_qpc_ticks"],
        "finalized_qpc_ticks": finalized_qpc_ticks,
    }
    telemetry = {
        "wall_seconds": wall_seconds,
        "qpc_frequency": qpc_frequency_hz,
        "started_qpc_ticks": started_qpc_ticks,
        "finalized_qpc_ticks": finalized_qpc_ticks,
        "process_tree_cpu_seconds": process_cpu_seconds,
        "observer_cpu_seconds": observer_cpu_seconds,
        "system_times_start": system_start,
        "system_times_end": system_end,
        "logical_processor_count": logical_processors,
        "busy_fraction": busy_fraction,
        "external_busy_fraction": external_busy_fraction,
        "read_bytes": int(process["accounting"]["io"]["read_bytes"])
        + int(output["bytes"]),
        "write_bytes": int(process["accounting"]["io"]["write_bytes"])
        + int(output["bytes"])
        + int(invocation_manifest_path.stat().st_size),
        "sample_count": len(cpu_samples),
        "process_tree_sample_count": int(process["sample_count"]),
        "process_tree_counter_failures": int(process["counter_failures"]),
        "sample_interval_ms": int(process["sample_interval_ms"]),
        "missed_intervals": int(process["missed_intervals"])
        + int(cpu.missed_intervals),
        "cpu_samples": cpu_samples,
        "gpu_source": gpu.source,
        "gpu_utilization_percent": [
            float(sample["utilization_percent"]) for sample in hardware_samples
        ],
        "hardware_samples": hardware_samples,
        "synthetic_telemetry": gpu_config.get("kind") == "synthetic-zero",
        "hardware_throttle_observed": any(
            sample["hardware_throttle"] for sample in gpu.samples
        ),
        "unapproved_gpu_processes": observed_external_gpu,
        "gpu_process_allowlist_pass": not observed_external_gpu,
        "stage_banners": stages,
        "stage_measurements": measurements,
        "required_stages": required_stages,
        "numeric_stage_timings_required": (
            required_stages
            if numeric_stage_timings_required is None
            else numeric_stage_timings_required
        ),
    }
    process_guard = {
        **process,
        "child_expected": child_expected,
    }
    guards = [
        require_guard("G09-process-tree-drained", process_guard).to_json(),
        require_guard("G10-deliverable-finalized", finalization).to_json(),
        require_guard("G11-telemetry-complete", telemetry).to_json(),
    ]
    live_latency_seconds = None
    if live_marker is not None:
        live_payload = {
            **live_marker,
            "marker_qpc_frequency": live_marker.get("qpc_frequency"),
            "qpc_frequency": qpc_frequency_hz,
            "process_started_qpc_ticks": started_qpc_ticks,
            "finalized_qpc_ticks": finalized_qpc_ticks,
            "latency_seconds": (
                finalized_qpc_ticks
                - int(live_marker["frame_100_shutter_close_qpc_ticks"])
            )
            / qpc_frequency_hz,
        }
        guards.append(require_guard("G16-live-epoch", live_payload).to_json())
        live_latency_seconds = live_payload["latency_seconds"]
    if gpu.errors:
        raise RuntimeError(f"GPU telemetry failed: {gpu.errors}")
    if not output["tiff_valid"]:
        raise RuntimeError(f"output TIFF violates contract: {output}")
    return {
        "schema": "m153-run-record-v1",
        **run_identity,
        "argv": argv,
        "qpc_frequency": qpc_frequency_hz,
        "started_qpc_ticks": started_qpc_ticks,
        "process_drained_qpc_ticks": process["drained_qpc_ticks"],
        "finalized_qpc_ticks": finalized_qpc_ticks,
        "started_qpc_ns": qpc_ticks_to_ns(started_qpc_ticks, qpc_frequency_hz),
        "process_drained_qpc_ns": qpc_ticks_to_ns(
            process["drained_qpc_ticks"], qpc_frequency_hz
        ),
        "finalized_qpc_ns": qpc_ticks_to_ns(finalized_qpc_ticks, qpc_frequency_hz),
        "wall_seconds": wall_seconds,
        "process_tree": process,
        "output": output,
        "invocation_manifest": {
            "path": str(invocation_manifest_path.resolve()),
            "sha256": manifest_sha256,
            "bytes": invocation_manifest_path.stat().st_size,
        },
        "telemetry": telemetry,
        "finalization": finalization,
        "guards": guards,
        "live_latency_seconds": live_latency_seconds,
        "accepted": True,
    }
