from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import tifffile


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
SUPPLIED_SCORECARD_COMMIT = "dd957dd5"
SUPPLIED_SCORECARD_VERSION = "v1.5"
REGISTERED_COUNTS = (33, 105, 299)
WORKERS = (1, 2, 4, 8, 16)
MODULO_COUNTS = (96, 97, 98, 99)
SAMPLE_INTERVAL_S = 0.010
DEFAULT_PRELOAD_SAMPLE_S = 5.0
DEFAULT_PRELOAD_BUSY_MAX = 0.15
DEFAULT_EXTERNAL_BUSY_MAX = 0.10
DEFAULT_QUIET_RETRY_S = 30.0

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
ntdll = ctypes.WinDLL("ntdll")

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
CREATE_SUSPENDED = 0x00000004
JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS = 1
JOB_OBJECT_BASIC_PROCESS_ID_LIST_CLASS = 3
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


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


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wt.DWORD),
        ("dwMemoryLoad", wt.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
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
kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
kernel32.GlobalMemoryStatusEx.restype = wt.BOOL
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
ntdll.NtResumeProcess.argtypes = [wt.HANDLE]
ntdll.NtResumeProcess.restype = ctypes.c_long


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(json.dumps(value, sort_keys=True) + "\n")
        output.flush()


def run_text(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    log: Path | None = None,
    measured_commit: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("w", encoding="utf-8", newline="\n") as output:
            if measured_commit is not None:
                output.write(f"measured_commit={measured_commit}\n")
            output.write("$ " + subprocess.list2cmdline(command) + "\n\n")
            output.write(result.stdout)
    if result.returncode:
        raise RuntimeError(
            f"{subprocess.list2cmdline(command)} failed with {result.returncode}\n"
            f"{result.stdout[-6000:]}"
        )
    return result


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{revision}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def git_text(*arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "--no-pager", *arguments],
        check=True,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
    ).stdout.strip()


def resolve_commit(revision: str) -> str:
    return git_text("rev-parse", f"{revision}^{{commit}}")


def ensure_commit_exists(revision: str) -> str:
    commit = resolve_commit(revision)
    if len(commit) != 40:
        raise RuntimeError(f"expected a full commit SHA, got {commit!r}")
    return commit


def scorecard_version(data: bytes) -> str | None:
    match = re.search(rb"PRE-REGISTRATION (v\d+\.\d+)", data)
    return match.group(1).decode("ascii") if match else None


def capture_inventory(path: Path, first: int, last: int) -> dict[str, Any]:
    files = sorted(path.glob("*.ARW"), key=lambda item: item.name.casefold())
    actual = {item.name.upper() for item in files}
    expected = {f"DSC{number:05d}.ARW" for number in range(first, last + 1)}
    return {
        "path": str(path),
        "exists": path.is_dir(),
        "arw_count": len(files),
        "first": files[0].name if files else None,
        "last": files[-1].name if files else None,
        "missing_expected": sorted(expected - actual),
        "unexpected_arw": sorted(actual - expected),
        "bytes": sum(item.stat().st_size for item in files),
    }


def source_line(path: Path, exact: str) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines, 1) if line == exact]
    return {
        "path": str(path.relative_to(ROOT)),
        "line": matches[0] if len(matches) == 1 else None,
        "matching_lines": matches,
    }


def section_lines(data: bytes, heading: str) -> list[int]:
    lines = data.decode("utf-8").splitlines()
    starts = [index for index, line in enumerate(lines, 1) if line == heading]
    if len(starts) != 1:
        raise RuntimeError(f"expected one {heading!r} heading, found {len(starts)}")
    start = starts[0]
    end = len(lines)
    for index in range(start + 1, len(lines) + 1):
        if lines[index - 1].startswith("### ") or lines[index - 1].startswith("## "):
            end = index - 1
            break
    while end > start and not lines[end - 1].strip():
        end -= 1
    return [start, end]


def preflight(output: Path, measured_revision: str) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    registered_rel = "docs/proposals/2026-09-sota-scorecard.md"
    current_commit = git_text(
        "log", "-1", "--format=%H", measured_commit, "--", registered_rel
    )
    registered = git_bytes(measured_commit, registered_rel)
    supplied = git_bytes(SUPPLIED_SCORECARD_COMMIT, registered_rel)
    working = SCORECARD.read_bytes()
    scorecard_status = git_text("status", "--short", "--", registered_rel)

    bee = capture_inventory(Path(r"D:\personal\macro\bee-1-cpl"), 1, 299)
    coffee = capture_inventory(Path(r"D:\personal\macro\coffee-bean"), 16, 120)
    bee_names = {
        item.name.upper()
        for item in Path(bee["path"]).glob("*.ARW")
    }
    prefix_availability = {
        str(count): all(
            f"DSC{number:05d}.ARW" in bee_names for number in range(1, count + 1)
        )
        for count in (33, *MODULO_COUNTS, 299)
    }

    registry = ROOT / "crates" / "strehl-cli" / "tests" / "byte-freezes.tsv"
    registry_rows = []
    for number, line in enumerate(registry.read_text(encoding="utf-8").splitlines(), 1):
        if not line or line.startswith("#") or line.startswith("id\t"):
            continue
        fields = line.split("\t")
        registry_rows.append(
            {
                "line": number,
                "id": fields[0],
                "stack": fields[1],
                "limit": int(fields[3]),
                "merge": fields[4],
                "alignment_mode": fields[11],
            }
        )

    expected_manifest = ROOT / "experiments" / "SCORECARD" / "RUN-MANIFEST.json"
    stale_manifest = ROOT / "experiments" / "SCORECARD-BASELINE" / "out" / "RUN-MANIFEST.json"
    stale = json.loads(stale_manifest.read_text(encoding="utf-8")) if stale_manifest.exists() else None

    merge_cmd = ROOT / "crates" / "strehl-cli" / "src" / "merge_cmd.rs"
    pyramid = ROOT / "crates" / "strehl-core" / "src" / "pyramid.rs"
    align = ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs"
    main = ROOT / "crates" / "strehl-cli" / "src" / "main.rs"
    product_candidate = {
        "registered": False,
        "reason": (
            "No current experiments/SCORECARD/RUN-MANIFEST.json freezes the scored "
            "commit, binary, resolved defaults, environment, and highest-precision output."
        ),
        "command_template": (
            "strehl.exe stack <STACK> --limit <N> --out <OUT>.tiff "
            "--linear-srgb --demosaic"
        ),
        "worker_environment": "STREHL_PYRAMID_WORKERS=<1|2|4|8|16>",
        "current_source_candidate_only": {
            "backend": "pyramid (resolved shipping default)",
            "pyramid_gate": 2.0,
            "photometric": "not applied on pyramid backend",
            "alignment": "on by default",
            "bit_depth": 16,
            "format": "TIFF",
            "colour": "linear sRGB",
            "resolution": "full sensor via --demosaic",
        },
        "source_citations": {
            "backend": source_line(
                merge_cmd,
                "pub const DEFAULT_MERGE_BACKEND: MergeBackend = MergeBackend::Pyramid;",
            ),
            "gate": source_line(pyramid, "            gate: 2.0,"),
            "alignment": source_line(align, "        Err(_) => true,"),
            "linear_srgb_flag": source_line(main, "        linear_srgb: bool,"),
            "demosaic_flag": source_line(main, "        demosaic: bool,"),
        },
    }

    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "crop_early_commit": {
            "commit": resolve_commit("248178b9"),
            "is_ancestor_of_measured_commit": subprocess.run(
                [
                    "git",
                    "-C",
                    str(ROOT),
                    "merge-base",
                    "--is-ancestor",
                    "248178b9",
                    measured_commit,
                ],
                check=False,
            ).returncode
            == 0,
        },
        "registered_scorecard": {
            "last_path_commit_at_measured_revision": current_commit,
            "measured_tree_commit": measured_commit,
            "version": scorecard_version(registered),
            "sha256": sha256_bytes(registered),
            "m12_lines": section_lines(
                registered, "### M12 — memory, determinism, and scaling invariance"
            ),
        },
        "supplied_scorecard_revision": {
            "commit": git_text("rev-parse", SUPPLIED_SCORECARD_COMMIT),
            "version": SUPPLIED_SCORECARD_VERSION,
            "sha256": sha256_bytes(supplied),
            "superseded_by_current_file": supplied != registered,
        },
        "working_scorecard": {
            "version": scorecard_version(working),
            "sha256": sha256_bytes(working),
            "git_status": scorecard_status,
            "matches_registered_bytes": working == registered,
            "matches_registered_text": (
                working.decode("utf-8").splitlines()
                == registered.decode("utf-8").splitlines()
            ),
        },
        "captures": {
            "bee-1-cpl": bee,
            "coffee-bean": coffee,
            "bee_prefixes": prefix_availability,
        },
        "byte_freeze_registry": {
            "path": str(registry.relative_to(ROOT)),
            "required_n_rows": [
                row for row in registry_rows if row["limit"] in (*REGISTERED_COUNTS, *MODULO_COUNTS)
            ],
            "diagnostic_rows": registry_rows,
        },
        "experiments": {
            "current_run_manifest": str(expected_manifest.relative_to(ROOT)),
            "current_run_manifest_exists": expected_manifest.exists(),
            "stale_run_manifest": str(stale_manifest.relative_to(ROOT)),
            "stale_run_manifest_exists": stale_manifest.exists(),
            "stale_scorecard_version": (
                stale.get("scorecard", {}).get("version") if stale is not None else None
            ),
            "stale_product_flags": (
                stale.get("quality_product_arm", {}).get("command_flags")
                if stale is not None
                else None
            ),
        },
        "product_arm": product_candidate,
    }
    write_json(output, result)
    print(json.dumps(result, indent=2))
    captures_ok = (
        result["crop_early_commit"]["is_ancestor_of_measured_commit"]
        and bee["arw_count"] == 299
        and not bee["missing_expected"]
        and coffee["arw_count"] == 105
        and not coffee["missing_expected"]
        and all(prefix_availability.values())
    )
    return 0 if captures_ok else 1


def process_table() -> dict[int, dict[str, Any]]:
    handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    rows: dict[int, dict[str, Any]] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            rows[int(entry.th32ProcessID)] = {
                "parent_pid": int(entry.th32ParentProcessID),
                "name": str(entry.szExeFile),
            }
            ok = kernel32.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(handle)
    return rows


def process_snapshot() -> dict[int, int]:
    return {pid: int(row["parent_pid"]) for pid, row in process_table().items()}


def descendants(root_pid: int, parents: dict[int, int]) -> set[int]:
    found = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, parent in parents.items():
            if parent in found and pid not in found:
                found.add(pid)
                changed = True
    return found


def create_process_job() -> wt.HANDLE:
    handle = kernel32.CreateJobObjectW(None, None)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    limits.basic_limit_information.limit_flags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    if not kernel32.SetInformationJobObject(
        handle,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    ):
        error = ctypes.get_last_error()
        kernel32.CloseHandle(handle)
        raise ctypes.WinError(error)
    return handle


def assign_process_to_job(job: wt.HANDLE, process: subprocess.Popen[str]) -> None:
    process_handle = wt.HANDLE(int(process._handle))
    if not kernel32.AssignProcessToJobObject(job, process_handle):
        raise ctypes.WinError(ctypes.get_last_error())
    status = ntdll.NtResumeProcess(process_handle)
    if status != 0:
        raise OSError(f"NtResumeProcess failed with NTSTATUS 0x{status & 0xFFFFFFFF:08X}")


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
        buffer, 2 * ctypes.sizeof(wt.DWORD)
    )
    return [int(pid) for pid in process_ids]


def job_accounting(job: wt.HANDLE) -> dict[str, int]:
    accounting = JOBOBJECT_BASIC_ACCOUNTING_INFORMATION()
    returned = wt.DWORD()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION_CLASS,
        ctypes.byref(accounting),
        ctypes.sizeof(accounting),
        ctypes.byref(returned),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "total_user_100ns": int(accounting.total_user_time),
        "total_kernel_100ns": int(accounting.total_kernel_time),
        "total_cpu_100ns": int(
            accounting.total_user_time + accounting.total_kernel_time
        ),
        "total_page_fault_count": int(accounting.total_page_fault_count),
        "total_processes": int(accounting.total_processes),
        "active_processes": int(accounting.active_processes),
        "total_terminated_processes": int(accounting.total_terminated_processes),
    }


def job_memory(job: wt.HANDLE) -> dict[str, int]:
    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    returned = wt.DWORD()
    if not kernel32.QueryInformationJobObject(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
        ctypes.byref(returned),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "peak_process_memory_used_bytes": int(limits.peak_process_memory_used),
        "peak_job_memory_used_bytes": int(limits.peak_job_memory_used),
    }


def process_counters(pid: int) -> dict[str, int] | None:
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
        False,
        pid,
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
        created, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not kernel32.GetProcessTimes(
            handle,
            ctypes.byref(created),
            ctypes.byref(exited),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            return None
        return {
            "created": created.value(),
            "private": int(counters.private_usage),
            "working_set": int(counters.working_set_size),
            "page_faults": int(counters.page_fault_count),
            "cpu_100ns": kernel.value() + user.value(),
        }
    finally:
        kernel32.CloseHandle(handle)


def system_times() -> dict[str, int]:
    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    total = kernel.value() + user.value()
    busy = total - idle.value()
    return {
        "idle_100ns": idle.value(),
        "kernel_100ns": kernel.value(),
        "user_100ns": user.value(),
        "total_100ns": total,
        "busy_100ns": busy,
    }


def memory_status() -> dict[str, int]:
    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(status)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return {
        "memory_load_percent": int(status.dwMemoryLoad),
        "total_physical_bytes": int(status.ullTotalPhys),
        "available_physical_bytes": int(status.ullAvailPhys),
        "total_page_file_bytes": int(status.ullTotalPageFile),
        "available_page_file_bytes": int(status.ullAvailPageFile),
        "total_virtual_bytes": int(status.ullTotalVirtual),
        "available_virtual_bytes": int(status.ullAvailVirtual),
    }


def sample_host_load(duration_s: float) -> dict[str, Any]:
    started_utc = utc_now()
    started = time.perf_counter()
    system_start = system_times()
    table_start = process_table()
    process_start = {
        pid: counters
        for pid in table_start
        if (counters := process_counters(pid)) is not None
    }
    memory_start = memory_status()
    time.sleep(duration_s)
    system_end = system_times()
    table_end = process_table()
    process_end = {
        pid: counters
        for pid in table_end
        if (counters := process_counters(pid)) is not None
    }
    elapsed = time.perf_counter() - started
    total_delta = system_end["total_100ns"] - system_start["total_100ns"]
    busy_delta = system_end["busy_100ns"] - system_start["busy_100ns"]
    logical_processors = os.cpu_count() or 1
    capacity_seconds = elapsed * logical_processors
    process_rows = []
    for pid, end in process_end.items():
        start = process_start.get(pid)
        if start is not None and start["created"] != end["created"]:
            start = None
        cpu_delta = end["cpu_100ns"] - (start["cpu_100ns"] if start else 0)
        if cpu_delta <= 0:
            continue
        process_rows.append(
            {
                "pid": pid,
                "parent_pid": table_end[pid]["parent_pid"],
                "name": table_end[pid]["name"],
                "cpu_seconds": cpu_delta / 10_000_000.0,
                "capacity_fraction": (cpu_delta / 10_000_000.0) / capacity_seconds,
            }
        )
    process_rows.sort(key=lambda row: row["cpu_seconds"], reverse=True)
    busy_seconds = busy_delta / 10_000_000.0
    return {
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "requested_seconds": duration_s,
        "elapsed_seconds": elapsed,
        "logical_processors": logical_processors,
        "whole_host_busy_cpu_seconds": busy_seconds,
        "whole_host_busy_fraction": (
            busy_delta / total_delta if total_delta > 0 else None
        ),
        "whole_host_busy_fraction_of_wall_capacity": (
            busy_seconds / capacity_seconds if capacity_seconds > 0 else None
        ),
        "memory_start": memory_start,
        "memory_end": memory_status(),
        "top_process_cpu": process_rows[:20],
    }


def wait_for_quiet(
    *,
    sample_seconds: float,
    busy_max: float,
    retry_seconds: float,
) -> dict[str, Any]:
    attempts = []
    wait_started = time.perf_counter()
    while True:
        sample = sample_host_load(sample_seconds)
        busy = sample["whole_host_busy_fraction"]
        accepted = busy is not None and busy <= busy_max
        attempts.append({"accepted": accepted, **sample})
        if accepted:
            return {
                "threshold": busy_max,
                "sample_seconds": sample_seconds,
                "retry_seconds": retry_seconds,
                "wait_seconds": time.perf_counter() - wait_started,
                "rejected_sample_count": len(attempts) - 1,
                "attempts": attempts,
            }
        time.sleep(retry_seconds)


def tree_bytes(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def relevant_environment(env: dict[str, str]) -> dict[str, str | None]:
    audit = ROOT / "scripts" / "check-defaults.py"
    names = set(re.findall(r'"(STREHL_[A-Z0-9_]+)"\s*:\s*Declared\(', audit.read_text(encoding="utf-8")))
    names.update(
        {
            "RAYON_NUM_THREADS",
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
            "TEMP",
            "TMP",
        }
    )
    return {name: env.get(name) for name in sorted(names)}


def clean_environment(
    *,
    workers: int,
    cache: Path,
    temp: Path,
    sidecar: Path | None,
    align_off: bool,
    fixed: dict[str, str] | None = None,
) -> tuple[dict[str, str], dict[str, str | None]]:
    env = os.environ.copy()
    prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)
    env.update(fixed or {})
    env["STREHL_PYRAMID_WORKERS"] = str(workers)
    env["STREHL_CACHE_DIR"] = str(cache.resolve())
    env["TEMP"] = str(temp.resolve())
    env["TMP"] = str(temp.resolve())
    if align_off:
        env["STREHL_ALIGN"] = "0"
    elif sidecar is not None:
        env["STREHL_WARPMAP"] = str(sidecar.resolve())
    return env, relevant_environment(env)


def tiff_witness(path: Path) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tiff:
        if len(tiff.pages) != 1:
            raise RuntimeError(f"{path} has {len(tiff.pages)} TIFF pages, expected one")
        page = tiff.pages[0]
        shape = list(page.shape)
        dtype = str(page.dtype)
        bits = page.bitspersample
        samples = page.samplesperpixel
        software = page.tags["Software"].value
    if dtype != "uint16" or samples != 3 or bits != 16:
        raise RuntimeError(
            f"{path} is not the highest-precision 16-bit RGB TIFF: "
            f"shape={shape}, dtype={dtype}, bits={bits}, samples={samples}"
        )
    pixels = tifffile.memmap(path, mode="r")
    pixel_sha256 = hashlib.sha256(memoryview(pixels)).hexdigest().upper()
    del pixels
    return {
        "output_bytes": path.stat().st_size,
        "output_sha256": sha256_file(path),
        "pixel_sha256": pixel_sha256,
        "shape": shape,
        "dtype": dtype,
        "bits_per_sample": bits,
        "samples_per_pixel": samples,
        "software": software,
    }


def monitor_command(
    *,
    argv: list[str],
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    temp: Path,
    measured_commit: str,
    external_busy_max: float = DEFAULT_EXTERNAL_BUSY_MAX,
) -> dict[str, Any]:
    started_utc = utc_now()
    start = time.perf_counter()
    system_start = system_times()
    memory_start = memory_status()
    known: dict[int, dict[str, Any]] = {}
    peak_private = 0
    peak_working_set = 0
    peak_page_faults = 0
    peak_process_count = 0
    peak_temp_bytes = tree_bytes(temp)
    sample_count = 0
    missed_intervals = 0
    max_lateness = 0.0
    gaps: list[float] = []
    last_sample: float | None = None
    names: dict[int, str | None] = {}
    parents: dict[int, int | None] = {}
    job_peak_memory = {
        "peak_process_memory_used_bytes": 0,
        "peak_job_memory_used_bytes": 0,
    }
    final_job_accounting: dict[str, int] | None = None
    job = create_process_job()
    process: subprocess.Popen[str] | None = None
    try:
        with stdout_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as stdout, stderr_path.open(
            "w", encoding="utf-8", newline="\n"
        ) as stderr:
            stdout.write(f"measured_commit={measured_commit}\n")
            stdout.flush()
            stderr.write(f"measured_commit={measured_commit}\n")
            stderr.flush()
            process = subprocess.Popen(
                argv,
                env=env,
                stdout=stdout,
                stderr=stderr,
                text=True,
                errors="replace",
                creationflags=CREATE_SUSPENDED,
            )
            assign_process_to_job(job, process)
            next_sample = start
            empty_after_exit = 0
            while True:
                now = time.perf_counter()
                if now < next_sample:
                    time.sleep(next_sample - now)
                sampled_at = time.perf_counter()
                lateness = max(0.0, sampled_at - next_sample)
                max_lateness = max(max_lateness, lateness)
                if last_sample is not None:
                    gaps.append(sampled_at - last_sample)
                last_sample = sampled_at

                process_ids = set(job_process_ids(job))
                new_pids = process_ids - set(known)
                if new_pids:
                    table = process_table()
                    for pid in new_pids:
                        details = table.get(pid, {})
                        parents[pid] = details.get("parent_pid")
                        names[pid] = details.get("name")
                rows: list[tuple[int, dict[str, int]]] = []
                for pid in process_ids:
                    counters = process_counters(pid)
                    if counters is None:
                        continue
                    prior = known.get(pid)
                    if prior is not None and prior["created"] != counters["created"]:
                        continue
                    if prior is None:
                        known[pid] = {
                            "created": counters["created"],
                            "parent_pid": parents.get(pid),
                            "name": names.get(pid),
                            "first_seen_s": sampled_at - start,
                            "last_seen_s": sampled_at - start,
                            "samples": 1,
                            "max_cpu_100ns": counters["cpu_100ns"],
                        }
                    else:
                        prior["last_seen_s"] = sampled_at - start
                        prior["samples"] += 1
                        prior["max_cpu_100ns"] = max(
                            prior["max_cpu_100ns"], counters["cpu_100ns"]
                        )
                    rows.append((pid, counters))

                peak_private = max(
                    peak_private, sum(row["private"] for _, row in rows)
                )
                peak_working_set = max(
                    peak_working_set, sum(row["working_set"] for _, row in rows)
                )
                accounting = job_accounting(job)
                peak_page_faults = max(
                    peak_page_faults, accounting["total_page_fault_count"]
                )
                current_job_memory = job_memory(job)
                job_peak_memory = {
                    key: max(job_peak_memory[key], current_job_memory[key])
                    for key in job_peak_memory
                }
                peak_process_count = max(
                    peak_process_count,
                    len(process_ids),
                    accounting["active_processes"],
                )
                if sample_count % 10 == 0:
                    peak_temp_bytes = max(peak_temp_bytes, tree_bytes(temp))
                sample_count += 1

                root_done = process.poll() is not None
                if root_done and accounting["active_processes"] == 0:
                    empty_after_exit += 1
                else:
                    empty_after_exit = 0
                if root_done and empty_after_exit >= 2:
                    final_job_accounting = accounting
                    break

                next_sample += SAMPLE_INTERVAL_S
                if next_sample <= sampled_at:
                    skipped = (
                        int((sampled_at - next_sample) // SAMPLE_INTERVAL_S) + 1
                    )
                    missed_intervals += skipped
                    next_sample += skipped * SAMPLE_INTERVAL_S
            returncode = process.wait()
            final_job_accounting = job_accounting(job)
            current_job_memory = job_memory(job)
            job_peak_memory = {
                key: max(job_peak_memory[key], current_job_memory[key])
                for key in job_peak_memory
            }
    finally:
        kernel32.CloseHandle(job)
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()

    wall = time.perf_counter() - start
    system_end = system_times()
    memory_end = memory_status()
    system_total_cpu_seconds = (
        system_end["total_100ns"] - system_start["total_100ns"]
    ) / 10_000_000.0
    system_busy_cpu_seconds = (
        system_end["busy_100ns"] - system_start["busy_100ns"]
    ) / 10_000_000.0
    if final_job_accounting is None:
        raise RuntimeError("job accounting was not captured")
    process_tree_cpu_seconds = (
        final_job_accounting["total_cpu_100ns"] / 10_000_000.0
    )
    external_busy_cpu_seconds = max(
        0.0, system_busy_cpu_seconds - process_tree_cpu_seconds
    )
    logical_processors = os.cpu_count() or 1
    capacity_seconds = wall * logical_processors
    external_busy_fraction = (
        external_busy_cpu_seconds / capacity_seconds if capacity_seconds else None
    )
    return {
        "started_utc": started_utc,
        "completed_utc": utc_now(),
        "returncode": returncode,
        "wall_seconds": wall,
        "stdout_log": str(stdout_path.resolve()),
        "stderr_log": str(stderr_path.resolve()),
        "memory": {
            "sample_interval_ms": SAMPLE_INTERVAL_S * 1000.0,
            "process_discovery_interval_ms": SAMPLE_INTERVAL_S * 1000.0,
            "process_tree_membership_source": "Windows Job Object",
            "sample_count": sample_count,
            "missed_intervals": missed_intervals,
            "max_lateness_ms": max_lateness * 1000.0,
            "max_gap_ms": max(gaps, default=0.0) * 1000.0,
            "median_gap_ms": statistics.median(gaps) * 1000.0 if gaps else 0.0,
            "peak_process_tree_private_committed_bytes": peak_private,
            "peak_process_tree_working_set_bytes": peak_working_set,
            "peak_process_tree_page_fault_count": peak_page_faults,
            "peak_process_count": peak_process_count,
            "peak_temp_file_bytes": peak_temp_bytes,
            "kernel_job_peak_memory": job_peak_memory,
            "kernel_job_accounting": final_job_accounting,
            "process_lifetimes": [
                {"pid": pid, **details} for pid, details in sorted(known.items())
            ],
        },
        "host_load_during_run": {
            "logical_processors": logical_processors,
            "system_total_cpu_seconds": system_total_cpu_seconds,
            "system_busy_cpu_seconds": system_busy_cpu_seconds,
            "process_tree_cpu_seconds": process_tree_cpu_seconds,
            "external_busy_cpu_seconds": external_busy_cpu_seconds,
            "external_busy_fraction_of_wall_capacity": external_busy_fraction,
            "external_busy_max": external_busy_max,
            "pass": (
                external_busy_fraction is not None
                and external_busy_fraction <= external_busy_max
            ),
            "memory_start": memory_start,
            "memory_end": memory_end,
        },
    }


def run_once(
    *,
    exe: Path,
    stack: Path,
    limit: int,
    workers: int,
    destination: Path,
    cache: Path,
    temp: Path,
    flags: list[str],
    sidecar: Path | None,
    align_off: bool,
    fixed_env: dict[str, str] | None,
    required_log_substrings: list[str] | None,
    kind: str,
    repetition: int | None,
    sweep: str | None,
    measured_commit: str,
    external_busy_max: float = DEFAULT_EXTERNAL_BUSY_MAX,
) -> dict[str, Any]:
    if destination.exists():
        raise RuntimeError(f"refusing to overwrite {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    stdout_path = destination.with_suffix(destination.suffix + ".stdout.log")
    stderr_path = destination.with_suffix(destination.suffix + ".stderr.log")
    env, env_record = clean_environment(
        workers=workers,
        cache=cache,
        temp=temp,
        sidecar=sidecar,
        align_off=align_off,
        fixed=fixed_env,
    )
    argv = [
        str(exe.resolve()),
        "stack",
        str(stack.resolve()),
        "--limit",
        str(limit),
        "--out",
        str(destination.resolve()),
        *flags,
    ]
    observed = monitor_command(
        argv=argv,
        env=env,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        temp=temp,
        measured_commit=measured_commit,
        external_busy_max=external_busy_max,
    )
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    record: dict[str, Any] = {
        "schema": 1,
        "measured_commit": measured_commit,
        "kind": kind,
        **observed,
        "argv": argv,
        "environment": env_record,
        "binary": {
            "path": str(exe.resolve()),
            "bytes": exe.stat().st_size,
            "sha256": sha256_file(exe),
        },
        "stack": str(stack.resolve()),
        "limit": limit,
        "workers": workers,
        "repetition": repetition,
        "sweep": sweep,
    }
    failures = []
    if observed["returncode"] != 0:
        failures.append(f"returncode={observed['returncode']}")
    if not destination.exists():
        failures.append("output missing")
    else:
        try:
            record.update(tiff_witness(destination))
        except Exception as error:
            failures.append(str(error))
    for required in required_log_substrings or []:
        if required not in stderr_text:
            failures.append(f"stderr missing registered substring {required!r}")
    record["valid"] = not failures
    record["invalid_reasons"] = failures
    return record


def build_release(
    source: Path,
    target: Path,
    log: Path,
    build_id: str,
    measured_commit: str,
    jobs: int = 8,
) -> tuple[Path, str]:
    env = os.environ.copy()
    env["CARGO_BUILD_JOBS"] = str(jobs)
    env["RAYON_NUM_THREADS"] = str(jobs)
    env["CARGO_TERM_COLOR"] = "never"
    env["STREHL_BUILD_ID"] = build_id
    command = [
        "cargo",
        "build",
        "--release",
        "--jobs",
        str(jobs),
        "-p",
        "strehl-cli",
        "--manifest-path",
        str(source / "Cargo.toml"),
        "--target-dir",
        str(target),
    ]
    result = run_text(
        command,
        cwd=source,
        env=env,
        log=log,
        measured_commit=measured_commit,
    )
    exe = target / "release" / "strehl.exe"
    if not exe.exists():
        raise RuntimeError(f"build completed but {exe} is missing")
    return exe, result.stdout


def commission(
    output: Path,
    work: Path,
    stack: Path,
    limit: int,
    workers: int,
    measured_revision: str,
) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    output = output.resolve()
    work = work.resolve()
    stack = stack.resolve()
    source = work / "source"
    target = work / "target"
    if source.exists():
        shutil.rmtree(source)
    if target.exists():
        shutil.rmtree(target)
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    crate_status = git_text(
        "status",
        "--short",
        "--",
        "Cargo.toml",
        "Cargo.lock",
        "crates/strehl-cli",
        "crates/strehl-core",
        "crates/strehl-raw",
    )
    build_id = measured_commit[:12]
    archive = work / "source.tar"
    run_text(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=tar",
            f"--output={archive}",
            measured_commit,
        ],
        log=output.parent / "commission-archive.log",
        measured_commit=measured_commit,
    )
    with tarfile.open(archive, "r") as bundle:
        bundle.extractall(source, filter="data")
    archive.unlink()

    initial_exe, initial_build = build_release(
        source,
        target,
        output.parent / "commission-build-initial.log",
        build_id,
        measured_commit,
    )
    if "Compiling strehl-cli" not in initial_build:
        raise RuntimeError("initial build log lacks `Compiling strehl-cli`")

    run_root = work / "commission-runs"
    if run_root.exists():
        shutil.rmtree(run_root)
    run_root.mkdir(parents=True)
    flags = ["--linear-srgb", "--demosaic"]
    required = [
        "LAPLACIAN MULTI-BAND MERGE",
        "noise gate      : 2.00",
        "not applied     : photometric gain",
        "alignment       : OFF",
    ]

    def render(name: str, exe: Path) -> dict[str, Any]:
        record = run_once(
            exe=exe,
            stack=stack,
            limit=limit,
            workers=workers,
            destination=run_root / f"{name}.tiff",
            cache=run_root / f"{name}-cache",
            temp=run_root / f"{name}-temp",
            flags=flags,
            sidecar=None,
            align_off=True,
            fixed_env={"RAYON_NUM_THREADS": "8"},
            required_log_substrings=required,
            kind=f"commission-{name}",
            repetition=None,
            sweep=None,
            measured_commit=measured_commit,
        )
        if not record["valid"]:
            raise RuntimeError(f"{name} render invalid: {record['invalid_reasons']}")
        return record

    baseline = render("baseline", initial_exe)
    source_file = source / "crates" / "strehl-core" / "src" / "pyramid.rs"
    original_hash = sha256_file(source_file)
    backup_root = work / "source-backup"
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = backup_root / f"m12-pyramid-{uuid.uuid4().hex}.rs"
    shutil.copy2(source_file, backup)
    anchor = (
        "    *CACHED.get_or_init(|| match std::env::var(SIGNIFICANCE_ENV) {\n"
        "        Err(_) => 0.0,\n"
        "        Ok(raw) => match raw.trim() {\n"
    )
    replacement = (
        "    *CACHED.get_or_init(|| match std::env::var(SIGNIFICANCE_ENV) {\n"
        "        Err(_) => 1.0,\n"
        "        Ok(raw) => match raw.trim() {\n"
    )
    planted: dict[str, Any] | None = None
    restored: dict[str, Any] | None = None
    plant_hash: str | None = None
    plant_build = ""
    restore_build = ""
    restore_error: str | None = None
    try:
        text = source_file.read_text(encoding="utf-8")
        occurrences = text.count(anchor)
        if occurrences != 1:
            raise RuntimeError(
                f"potency anchor must occur exactly once, found {occurrences}"
            )
        changed = text.replace(anchor, replacement, 1)
        with source_file.open("w", encoding="utf-8", newline="\n") as target_file:
            target_file.write(changed)
        plant_hash = sha256_file(source_file)
        if plant_hash == original_hash:
            raise RuntimeError("potency mutation was a silent no-op")
        planted_exe, plant_build = build_release(
            source,
            target,
            output.parent / "commission-build-planted.log",
            build_id,
            measured_commit,
        )
        if "Compiling strehl-core" not in plant_build:
            raise RuntimeError("planted build log lacks `Compiling strehl-core`")
        planted = render("planted", planted_exe)
    finally:
        try:
            if source_file.exists() and sha256_file(source_file) not in {
                original_hash,
                plant_hash,
            }:
                raise RuntimeError("isolated source changed outside the potency mutation")
            shutil.copy2(backup, source_file)
            os.utime(source_file, None)
            if sha256_file(source_file) != original_hash:
                raise RuntimeError(
                    "project-work restore did not reproduce the original source bytes"
                )
            restored_exe, restore_build = build_release(
                source,
                target,
                output.parent / "commission-build-restored.log",
                build_id,
                measured_commit,
            )
            if "Compiling strehl-core" not in restore_build:
                raise RuntimeError("restored build log lacks `Compiling strehl-core`")
            restored = render("restored", restored_exe)
        except Exception as error:
            restore_error = str(error)
        finally:
            backup.unlink(missing_ok=True)

    if restore_error is not None:
        raise RuntimeError("restore failed: " + restore_error)
    if planted is None or restored is None:
        raise RuntimeError("commissioning did not produce all three renders")

    lsb_path = run_root / "baseline-lsb-control.tiff"
    shutil.copy2(run_root / "baseline.tiff", lsb_path)
    pixels = tifffile.memmap(lsb_path, mode="r+")
    coordinate = tuple(size // 2 for size in pixels.shape)
    original_value = int(pixels[coordinate])
    pixels[coordinate] = original_value ^ 1
    pixels.flush()
    del pixels
    lsb_hash = sha256_file(lsb_path)

    red = baseline["output_sha256"] != planted["output_sha256"]
    pixel_red = baseline["pixel_sha256"] != planted["pixel_sha256"]
    green = baseline["output_sha256"] == restored["output_sha256"]
    pixel_green = baseline["pixel_sha256"] == restored["pixel_sha256"]
    provenance_green = (
        baseline["software"] == planted["software"] == restored["software"]
        and build_id in baseline["software"]
    )
    lsb_red = baseline["output_sha256"] != lsb_hash
    result = {
        "schema": 1,
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "status": (
            "COMMISSIONED"
            if red and pixel_red and green and pixel_green and provenance_green and lsb_red
            else "FAILED"
        ),
        "scope": (
            "Diagnostic N-limited, alignment-off native-RAW pyramid arm used only to "
            "commission byte detection; it is not an M12 score reading."
        ),
        "source_commit": measured_commit,
        "forced_build_id": build_id,
        "working_tree_crate_status_ignored_because_source_was_archived": crate_status,
        "harness_sha256": sha256_file(Path(__file__)),
        "stack": str(stack.resolve()),
        "limit": limit,
        "workers": workers,
        "flags": flags,
        "source_plant": {
            "path": "crates/strehl-core/src/pyramid.rs",
            "unique_anchor_occurrences": 1,
            "change": "significance_scale_default() unset arm 0.0 -> 1.0",
            "original_source_sha256": original_hash,
            "planted_source_sha256": plant_hash,
            "restored_source_sha256": sha256_file(source_file),
            "backup_was_under_project_work": str(backup_root),
            "restored_last_write_time_was_refreshed": True,
        },
        "baseline": baseline,
        "planted": planted,
        "restored": restored,
        "hash_gate": {
            "plant_went_red": red,
            "plant_pixels_went_red": pixel_red,
            "restore_returned_green": green,
            "restore_pixels_returned_green": pixel_green,
            "provenance_stayed_green": provenance_green,
            "baseline_sha256": baseline["output_sha256"],
            "planted_sha256": planted["output_sha256"],
            "restored_sha256": restored["output_sha256"],
            "one_output_lsb_went_red": lsb_red,
            "lsb_coordinate": coordinate,
            "lsb_before": original_value,
            "lsb_after": original_value ^ 1,
            "lsb_sha256": lsb_hash,
        },
        "build_proof": {
            "initial_compiled_strehl_cli": "Compiling strehl-cli" in initial_build,
            "plant_compiled_strehl_core": "Compiling strehl-core" in plant_build,
            "restore_compiled_strehl_core": "Compiling strehl-core" in restore_build,
        },
    }
    write_json(output, result)
    print(json.dumps(result["hash_gate"], indent=2))
    print(result["status"])
    return 0 if result["status"] == "COMMISSIONED" else 1


def commission_memory(output: Path, work: Path, measured_revision: str) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    output = output.resolve()
    work = work.resolve()
    control = work / "memory-control"
    if control.exists():
        shutil.rmtree(control)
    control.mkdir(parents=True)
    child = control / "child.py"
    parent = control / "parent.py"
    with child.open("w", encoding="utf-8", newline="\n") as target:
        target.write(
            f"# measured_commit={measured_commit}\n"
            "import sys, time\n"
            "size = int(sys.argv[1])\n"
            "hold = bytearray(size)\n"
            "for index in range(0, size, 4096):\n"
            "    hold[index] = 1\n"
            "print(f'allocated={len(hold)}', flush=True)\n"
            "time.sleep(2.0)\n"
        )
    with parent.open("w", encoding="utf-8", newline="\n") as target:
        target.write(
            f"# measured_commit={measured_commit}\n"
            "import subprocess, sys\n"
            "raise SystemExit(subprocess.call([sys.executable, sys.argv[1], sys.argv[2]]))\n"
        )

    def arm(name: str, size: int) -> dict[str, Any]:
        temp = control / f"{name}-temp"
        temp.mkdir()
        env = os.environ.copy()
        env["TEMP"] = str(temp.resolve())
        env["TMP"] = str(temp.resolve())
        argv = [sys.executable, str(parent), str(child), str(size)]
        observed = monitor_command(
            argv=argv,
            env=env,
            stdout_path=control / f"{name}.stdout.log",
            stderr_path=control / f"{name}.stderr.log",
            temp=temp,
            measured_commit=measured_commit,
        )
        observed["argv"] = argv
        observed["requested_allocation_bytes"] = size
        return observed

    null = arm("null-64mib", 64 * (1 << 20))
    planted = arm("plant-7gib", 7 * (1 << 30))
    null_peak = null["memory"]["peak_process_tree_private_committed_bytes"]
    plant_peak = planted["memory"]["peak_process_tree_private_committed_bytes"]
    null_green = (
        null["returncode"] == 0
        and null_peak < 1 * (1 << 30)
        and null["memory"]["peak_process_count"] >= 2
    )
    plant_red = (
        planted["returncode"] == 0
        and plant_peak > 6 * (1 << 30)
        and planted["memory"]["peak_process_count"] >= 2
    )
    result = {
        "schema": 1,
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "harness_sha256": sha256_file(Path(__file__)),
        "status": "COMMISSIONED" if null_green and plant_red else "FAILED",
        "null": null,
        "plant": planted,
        "verdict": {
            "null_stayed_below_one_gib": null_green,
            "seven_gib_child_exceeded_six_gib_bar": plant_red,
            "null_peak_private_committed_bytes": null_peak,
            "plant_peak_private_committed_bytes": plant_peak,
            "plant_peak_process_count": planted["memory"]["peak_process_count"],
        },
    }
    write_json(output, result)
    print(json.dumps(result["verdict"], indent=2))
    print(result["status"])
    return 0 if result["status"] == "COMMISSIONED" else 1


def line_slice(data: bytes, start: int, end: int) -> dict[str, Any]:
    lines = data.decode("utf-8").splitlines()
    return {
        "start": start,
        "end": end,
        "text": "\n".join(lines[start - 1 : end]),
    }


def git_file_provenance(measured_commit: str, relative: str) -> dict[str, Any]:
    data = git_bytes(measured_commit, relative)
    last_path_commit = git_text(
        "log", "-1", "--format=%H", measured_commit, "--", relative
    )
    return {
        "path": relative.replace("/", "\\"),
        "measured_tree_commit": measured_commit,
        "last_path_commit": last_path_commit,
        "sha256": sha256_bytes(data),
        "bytes": len(data),
    }


def exiftool_records(executable: Path, capture: Path) -> list[dict[str, Any]]:
    command = [
        str(executable),
        "-json",
        "-n",
        "-ext",
        "ARW",
        str(capture),
    ]
    result = subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    rows = json.loads(result.stdout.decode("utf-8", errors="strict"))
    volatile = {"FileAccessDate", "FileInodeChangeDate", "FilePermissions"}
    cleaned = [
        {key: value for key, value in row.items() if key not in volatile}
        for row in rows
    ]
    return sorted(cleaned, key=lambda row: str(row.get("SourceFile", "")).casefold())


def input_manifest(
    *,
    output: Path,
    exif_output: Path,
    measured_revision: str,
) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    output = output.resolve()
    exif_output = exif_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    exif_output.parent.mkdir(parents=True, exist_ok=True)
    captures = [
        {
            "id": "bee-1-cpl",
            "path": Path(r"D:\personal\macro\bee-1-cpl"),
            "expected_first": 1,
            "expected_last": 299,
            "roles": ["N33", "N299", "modulo-N96-N99"],
        },
        {
            "id": "coffee-bean",
            "path": Path(r"D:\personal\macro\coffee-bean"),
            "expected_first": 16,
            "expected_last": 120,
            "roles": ["N105"],
        },
    ]
    exif_command = shutil.which("exiftool")
    if exif_command is None:
        raise RuntimeError("ExifTool is required by the registered input manifest")
    exif_exe = Path(exif_command).resolve()
    exif_version = run_text(
        [str(exif_exe), "-ver"], measured_commit=measured_commit
    ).stdout.strip()

    exif_by_capture = {}
    capture_rows = []
    for capture in captures:
        path = capture["path"]
        files = sorted(path.glob("*.ARW"), key=lambda item: item.name.casefold())
        expected = {
            f"DSC{number:05d}.ARW"
            for number in range(capture["expected_first"], capture["expected_last"] + 1)
        }
        actual = {item.name.upper() for item in files}
        if expected != actual:
            raise RuntimeError(
                f"{path} inventory mismatch: missing={sorted(expected - actual)}, "
                f"unexpected={sorted(actual - expected)}"
            )
        rows = []
        for index, item in enumerate(files, 1):
            stat = item.stat()
            rows.append(
                {
                    "name": item.name,
                    "path": str(item.resolve()),
                    "bytes": stat.st_size,
                    "last_write_utc": datetime.fromtimestamp(
                        stat.st_mtime, timezone.utc
                    ).isoformat(),
                    "sha256": sha256_file(item),
                }
            )
            if index % 25 == 0 or index == len(files):
                print(
                    f"hashed {capture['id']} {index}/{len(files)}",
                    flush=True,
                )
        canonical = "\n".join(
            f"{row['name']}\t{row['bytes']}\t{row['last_write_utc']}\t{row['sha256']}"
            for row in rows
        ).encode("utf-8")
        capture_rows.append(
            {
                "evidence_tag": "VERIFIED",
                "id": capture["id"],
                "path": str(path),
                "roles": capture["roles"],
                "file_count": len(rows),
                "bytes": sum(row["bytes"] for row in rows),
                "metadata_and_content_manifest_sha256": sha256_bytes(canonical),
                "files": rows,
            }
        )
        exif_by_capture[capture["id"]] = exiftool_records(exif_exe, path)

    exif_artifact = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "tool": {
            "path": str(exif_exe),
            "version": exif_version,
            "sha256": sha256_file(exif_exe),
        },
        "excluded_volatile_filesystem_fields": [
            "FileAccessDate",
            "FileInodeChangeDate",
            "FilePermissions",
        ],
        "captures": exif_by_capture,
    }
    write_json(exif_output, exif_artifact)
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "captures": capture_rows,
        "exif_dump": {
            "path": str(exif_output),
            "sha256": sha256_file(exif_output),
            "tool": exif_artifact["tool"],
        },
        "decoder": {
            "kind": "integrated Rust RAW decoder",
            "binary_is_frozen_in_run_manifest": True,
            "cargo_lock": git_file_provenance(measured_commit, "Cargo.lock"),
        },
    }
    write_json(output, result)
    print(
        json.dumps(
            {
                "measured_commit": measured_commit,
                "captures": [
                    {
                        "id": row["id"],
                        "file_count": row["file_count"],
                        "bytes": row["bytes"],
                        "manifest_sha256": row[
                            "metadata_and_content_manifest_sha256"
                        ],
                    }
                    for row in capture_rows
                ],
                "exif_sha256": result["exif_dump"]["sha256"],
            },
            indent=2,
        )
    )
    return 0


def registration_artifact(output: Path, measured_revision: str) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    scorecard_rel = "docs/proposals/2026-09-sota-scorecard.md"
    scorecard = git_bytes(measured_commit, scorecard_rel)
    phase0_rel = "docs/research/M-PHASE0-PIPE.md"
    phase0 = git_bytes(measured_commit, phase0_rel)
    m12_start, m12_end = section_lines(
        scorecard, "### M12 — memory, determinism, and scaling invariance"
    )
    result = {
        "schema": 1,
        "evidence_tag": "INHERITED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "execution_registration_revision": 3,
        "execution_registration_amendment": {
            "evidence_tag": "VERIFIED",
            "timing": "before any scored M12 repetition",
            "reason": (
                "Warm-up commissioning showed that scanning the complete host "
                "process table every 10 ms materially loaded the host. Revision "
                "2 proposed 100-ms topology refreshes but produced no scored "
                "repetition and is superseded. Revision 3 uses Windows Job Object "
                "membership at every 10-ms sample, preserving the registered "
                "whole-process-tree cadence without a full-host scan."
            ),
            "supersedes_execution_registration_revision": 2,
            "superseded_warmup_records_are_not_score_evidence": True,
        },
        "governing_registration": {
            **git_file_provenance(measured_commit, scorecard_rel),
            "version": scorecard_version(scorecard),
            "m12_section": line_slice(scorecard, m12_start, m12_end),
            "joint_constraint": line_slice(scorecard, 122, 122),
            "scoreboard_bar": line_slice(scorecard, 403, 405),
            "readiness": line_slice(scorecard, 433, 437),
        },
        "registered_design": {
            "native_frame_counts": list(REGISTERED_COUNTS),
            "worker_counts": list(WORKERS),
            "warmups_per_cell": 1,
            "scored_repetitions_per_cell": 6,
            "order": "alternating ascending/descending worker order",
            "modulo_frame_counts": list(MODULO_COUNTS),
            "modulo_workers": 16,
            "modulo_warmups_per_n": 1,
            "modulo_scored_repetitions_per_n": 6,
            "highest_precision_deliverable": "uncompressed 16-bit RGB TIFF",
            "memory_sample_interval_ms": SAMPLE_INTERVAL_S * 1000.0,
            "process_tree_discovery_interval_ms": SAMPLE_INTERVAL_S * 1000.0,
            "process_tree_membership_source": "Windows Job Object",
        },
        "bars": {
            "peak_process_tree_private_committed_bytes_max": 6 * (1 << 30),
            "peak_n299_over_peak_n33_max": 1.10,
            "fixed_worker_distinct_hashes_max": 1,
            "cross_worker_distinct_hashes_max": 1,
            "modulo_per_frame_spread_max": 0.02,
            "m12_s_joint_requirement": (
                "the 16-worker output must simultaneously pass M11"
            ),
        },
        "scored_vs_diagnostic": {
            "scored": (
                "The registered N=33/105/299 native-product matrix at "
                "workers 1/2/4/8/16, six accepted repetitions per cell, plus "
                "the registered N=96/97/98/99 modulo arm."
            ),
            "diagnostic_only": (
                "The older unaligned N=20 sweep at workers 1/4/8 and all "
                "commissioning/smoke outputs."
            ),
        },
        "host_load_gate": {
            "evidence_tag": "INHERITED",
            **git_file_provenance(measured_commit, phase0_rel),
            "source_lines": line_slice(phase0, 245, 257),
            "preload_sample_seconds": DEFAULT_PRELOAD_SAMPLE_S,
            "preload_busy_max": DEFAULT_PRELOAD_BUSY_MAX,
            "during_run_external_busy_max": DEFAULT_EXTERNAL_BUSY_MAX,
            "retry_seconds": DEFAULT_QUIET_RETRY_S,
            "application": (
                "Every formal warm-up and scored invocation waits for the "
                "preload gate; any invocation crossing the during-run gate is "
                "preserved as rejected and repeated in the same position."
            ),
        },
        "pre_registered_adjudication": {
            "memory_peak": (
                "Use the maximum observed process-tree private committed bytes "
                "over all accepted scored matrix runs."
            ),
            "memory_ratio": (
                "For each worker count, divide the maximum accepted N=299 peak "
                "by the maximum accepted N=33 peak; the maximum worker-specific "
                "ratio is the score."
            ),
            "memory_sampling": (
                "A sampled peak above 6 GiB is a valid one-sided FAIL even if "
                "sampling gaps occurred, because missed samples can hide a "
                "higher peak but cannot manufacture the observed allocation. "
                "A PASS would require every run's maximum sample gap <=100 ms "
                "and >=90% scheduled-sample coverage."
            ),
            "determinism": (
                "Hash both the complete TIFF and its uint16 pixel payload. Any "
                "disagreement in either hash fails the byte property."
            ),
            "modulo": (
                "Use the minimum accepted warm wall time per N across the six "
                "alternating-order scored repetitions, divide by N, then "
                "compute (max-min)/min."
            ),
            "overall": (
                "Any valid hard-gate failure makes M12 FAIL. PASS requires every "
                "M12 bar plus the M11 joint requirement. If no bar fails and a "
                "required validity/joint term is unavailable, M12 remains UNMEASURED."
            ),
        },
    }
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps(result["registered_design"], indent=2))
    return 0


def build_measured(
    *,
    output: Path,
    work: Path,
    measured_revision: str,
    jobs: int,
) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    output = output.resolve()
    work = work.resolve()
    source = work / "source"
    target = work / "target"
    binary_dir = work / "bin"
    for path in (source, target, binary_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    archive = work / "source.tar"
    run_text(
        [
            "git",
            "-C",
            str(ROOT),
            "archive",
            "--format=tar",
            f"--output={archive}",
            measured_commit,
        ],
        log=output.parent / "build-archive.log",
        measured_commit=measured_commit,
    )
    archive_sha256 = sha256_file(archive)
    with tarfile.open(archive, "r") as bundle:
        bundle.extractall(source, filter="data")
    archive.unlink()
    built, build_stdout = build_release(
        source,
        target,
        output.parent / "build-release.log",
        measured_commit[:12],
        measured_commit,
        jobs=jobs,
    )
    if "Compiling strehl-cli" not in build_stdout:
        raise RuntimeError("fresh release build did not report `Compiling strehl-cli`")
    binary = binary_dir / "strehl.exe"
    shutil.copy2(built, binary)
    version = run_text(
        [str(binary), "--version"], measured_commit=measured_commit
    ).stdout.strip()
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "source": {
            "archive": "git archive",
            "archive_sha256": archive_sha256,
            "commit": measured_commit,
            "tree": git_text("rev-parse", f"{measured_commit}^{{tree}}"),
            "working_tree_source_used": False,
        },
        "build": {
            "command": (
                f"cargo build --release --jobs {jobs} -p strehl-cli "
                "--manifest-path <archived-source>\\Cargo.toml "
                "--target-dir <campaign-target>"
            ),
            "jobs": jobs,
            "cargo": run_text(
                ["cargo", "--version"], measured_commit=measured_commit
            ).stdout.strip(),
            "rustc": run_text(
                ["rustc", "--version"], measured_commit=measured_commit
            ).stdout.strip(),
            "compiled_strehl_cli_observed": True,
        },
        "binary": {
            "path": str(binary.resolve()),
            "bytes": binary.stat().st_size,
            "sha256": sha256_file(binary),
            "version": version,
        },
    }
    write_json(output, result)
    print(json.dumps(result, indent=2))
    return 0


def write_run_manifest(
    *,
    output: Path,
    measured_revision: str,
    registration_path: Path,
    input_path: Path,
    build_path: Path,
    preflight_path: Path,
) -> int:
    measured_commit = ensure_commit_exists(measured_revision)
    registration_path = registration_path.resolve()
    input_path = input_path.resolve()
    build_path = build_path.resolve()
    preflight_path = preflight_path.resolve()
    registration = read_json(registration_path)
    inputs = read_json(input_path)
    build = read_json(build_path)
    preflight_record = read_json(preflight_path)
    for label, artifact in (
        ("registration", registration),
        ("input", inputs),
        ("build", build),
        ("preflight", preflight_record),
    ):
        if artifact.get("measured_commit") != measured_commit:
            raise RuntimeError(f"{label} artifact measured a different commit")
    scorecard_rel = str(SCORECARD.relative_to(ROOT)).replace("\\", "/")
    scorecard = git_bytes(measured_commit, scorecard_rel)
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "registration_status": "registered",
        "scope": (
            "Formal M12 native-ARW scorecard campaign authorized as M139. "
            "Commissioning and smoke outputs remain diagnostic."
        ),
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "scorecard": {
            "path": str(SCORECARD.relative_to(ROOT)),
            "version": scorecard_version(scorecard),
            "last_path_commit": git_text(
                "log",
                "-1",
                "--format=%H",
                measured_commit,
                "--",
                scorecard_rel,
            ),
            "sha256": sha256_bytes(scorecard),
        },
        "registration": {
            "path": str(registration_path),
            "sha256": sha256_file(registration_path),
        },
        "input_manifest": {
            "path": str(input_path),
            "sha256": sha256_file(input_path),
            "capture_manifest_sha256": {
                row["id"]: row["metadata_and_content_manifest_sha256"]
                for row in inputs["captures"]
            },
        },
        "preflight": {
            "path": str(preflight_path),
            "sha256": sha256_file(preflight_path),
        },
        "harness": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__)),
        },
        "read_only_snapshot": {
            "tool_path": str((LANE / "m139-tree-snapshot.ps1").resolve()),
            "tool_sha256": sha256_file(LANE / "m139-tree-snapshot.ps1"),
            "before_path": str((output.resolve().parent / "read-only-before.json")),
            "before_sha256": sha256_file(
                output.resolve().parent / "read-only-before.json"
            ),
        },
        "binary": build["binary"],
        "build": {
            "artifact_path": str(build_path),
            "artifact_sha256": sha256_file(build_path),
            **build["build"],
            "source": build["source"],
        },
        "product_arm": {
            "classification": "registered native-ARW shipping product arm",
            "flags": ["--linear-srgb", "--demosaic"],
            "fixed_env": {},
            "worker_control": "STREHL_PYRAMID_WORKERS",
            "backend": "pyramid shipping default",
            "gate": 2.0,
            "photometric": "not applied on the pyramid backend",
            "alignment": (
                "shipping default on; one warm-up populates an N-isolated "
                "STREHL_CACHE_DIR and scored runs load that same validated sidecar"
            ),
            "cache_policy": "separate project-local cache directory for every N",
            "cover": {
                "value": "scale",
                "source": "shipping default",
                "source_citation": {
                    "path": "crates\\strehl-cli\\src\\align_cmd.rs",
                    "line": 1003,
                    "text": (
                        "pub const DEFAULT_COVER_MODE: CoverMode = CoverMode::Scale;"
                    ),
                },
            },
            "bit_depth": 16,
            "output_format": "uncompressed full-sensor linear-sRGB TIFF",
            "required_log_substrings": [
                "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)",
                "noise gate      : 2.00 x",
                "not applied     : photometric gain, clip census, outlier rejection, halo correction, through-focus",
                "alignment       : ON (",
                "16-bit RGB, linear sRGB",
                "Full sensor resolution",
            ],
            "captures": {
                "33": {"path": r"D:\personal\macro\bee-1-cpl", "sidecar": None},
                "105": {"path": r"D:\personal\macro\coffee-bean", "sidecar": None},
                "299": {"path": r"D:\personal\macro\bee-1-cpl", "sidecar": None},
            },
            "modulo_capture": {
                "path": r"D:\personal\macro\bee-1-cpl",
                "sidecars": {str(count): None for count in MODULO_COUNTS},
            },
            "smoke": {
                "path": r"D:\personal\macro\coffee-bean",
                "limit": 3,
                "workers": 1,
                "repetitions": 2,
            },
        },
        "host_load_gate": registration["host_load_gate"],
        "adjudication": registration["pre_registered_adjudication"],
    }
    if measured_commit[:12] not in str(result["binary"]["version"]):
        raise RuntimeError("binary version does not carry the measured commit")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps(result, indent=2))
    return 0


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = read_json(path)
    registration_status = manifest.get("registration_status")
    if registration_status not in {"registered", "operator-authorized-diagnostic"}:
        raise RuntimeError(
            "run manifest must be registrar-approved or explicitly operator-authorized "
            "as diagnostic (`registration_status`)"
        )
    expected_hash = manifest["scorecard"]["sha256"].upper()
    measured_commit = ensure_commit_exists(manifest["measured_commit"])
    if measured_commit != manifest["measured_commit"]:
        raise RuntimeError("manifest does not contain a full canonical measured commit")
    scorecard_rel = str(SCORECARD.relative_to(ROOT)).replace("\\", "/")
    if sha256_bytes(git_bytes(measured_commit, scorecard_rel)) != expected_hash:
        raise RuntimeError(
            "scorecard blob at the measured commit does not match the run manifest"
        )
    for label in ("registration", "input_manifest", "preflight"):
        artifact = manifest[label]
        artifact_path = Path(artifact["path"])
        if sha256_file(artifact_path) != artifact["sha256"].upper():
            raise RuntimeError(f"{label} artifact hash does not match the run manifest")
    harness = manifest.get("harness")
    if harness and sha256_file(Path(harness["path"])) != harness["sha256"].upper():
        raise RuntimeError("harness hash does not match the run manifest")
    read_only = manifest.get("read_only_snapshot")
    if read_only:
        if (
            sha256_file(Path(read_only["tool_path"]))
            != read_only["tool_sha256"].upper()
        ):
            raise RuntimeError("read-only snapshot tool hash does not match")
        if (
            sha256_file(Path(read_only["before_path"]))
            != read_only["before_sha256"].upper()
        ):
            raise RuntimeError("read-only before snapshot hash does not match")
    build = manifest.get("build")
    if build:
        build_path = Path(build["artifact_path"])
        if sha256_file(build_path) != build["artifact_sha256"].upper():
            raise RuntimeError("build artifact hash does not match the run manifest")
    binary = Path(manifest["binary"]["path"])
    if sha256_file(binary) != manifest["binary"]["sha256"].upper():
        raise RuntimeError("binary hash does not match the run manifest")
    return manifest


def smoke(manifest_path: Path, output: Path, work: Path) -> int:
    manifest_path = manifest_path.resolve()
    output = output.resolve()
    work = work.resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    manifest = load_manifest(manifest_path)
    measured_commit = manifest["measured_commit"]
    arm = manifest["product_arm"]
    config = arm["smoke"]
    binary = Path(manifest["binary"]["path"])
    flags = list(arm["flags"])
    required = list(arm["required_log_substrings"])
    records = []
    total = 1 + int(config["repetitions"])
    for index in range(total):
        kind = "smoke-warmup" if index == 0 else "smoke-repeat"
        record = run_once(
            exe=binary,
            stack=Path(config["path"]),
            limit=int(config["limit"]),
            workers=int(config["workers"]),
            destination=work / f"{kind}-{index}.tiff",
            cache=work / "cache",
            temp=work / f"{kind}-{index}-temp",
            flags=flags,
            sidecar=None,
            align_off=False,
            fixed_env={
                str(key): str(value)
                for key, value in arm.get("fixed_env", {}).items()
            },
            required_log_substrings=required,
            kind=kind,
            repetition=index if index else None,
            sweep="smoke",
            measured_commit=measured_commit,
            external_busy_max=float(
                manifest["host_load_gate"]["during_run_external_busy_max"]
            ),
        )
        records.append(record)
        if not record["valid"]:
            raise RuntimeError(f"smoke run {index} invalid: {record['invalid_reasons']}")
    repeats = [row for row in records if row["kind"] == "smoke-repeat"]
    output_hashes = sorted({row["output_sha256"] for row in repeats})
    pixel_hashes = sorted({row["pixel_sha256"] for row in repeats})
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "scope": "Diagnostic end-to-end smoke; not a scored M12 cell.",
        "manifest_sha256": sha256_file(manifest_path),
        "records": records,
        "verdict": {
            "all_runs_valid": all(row["valid"] for row in records),
            "repeat_count": len(repeats),
            "repeat_output_hashes": output_hashes,
            "repeat_pixel_hashes": pixel_hashes,
            "repeat_byte_identical": (
                len(repeats) == int(config["repetitions"])
                and len(output_hashes) == 1
                and len(pixel_hashes) == 1
            ),
        },
    }
    result["status"] = (
        "PASS"
        if result["verdict"]["all_runs_valid"]
        and result["verdict"]["repeat_byte_identical"]
        else "FAIL"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps(result["verdict"], indent=2))
    return 0 if result["status"] == "PASS" else 1


def matrix(manifest_path: Path, records_path: Path, output_root: Path) -> int:
    manifest_path = manifest_path.resolve()
    records_path = records_path.resolve()
    output_root = output_root.resolve()
    manifest = load_manifest(manifest_path)
    measured_commit = manifest["measured_commit"]
    binary = Path(manifest["binary"]["path"])
    arm = manifest["product_arm"]
    flags = list(arm["flags"])
    fixed_env = {str(key): str(value) for key, value in arm.get("fixed_env", {}).items()}
    required = list(arm["required_log_substrings"])
    load_gate = manifest["host_load_gate"]
    preload_sample_seconds = float(load_gate["preload_sample_seconds"])
    preload_busy_max = float(load_gate["preload_busy_max"])
    external_busy_max = float(load_gate["during_run_external_busy_max"])
    retry_seconds = float(load_gate["retry_seconds"])
    output_root.mkdir(parents=True, exist_ok=True)
    existing = (
        [
            json.loads(line)
            for line in records_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if records_path.exists()
        else []
    )
    if any(row.get("measured_commit") != measured_commit for row in existing):
        raise RuntimeError("existing campaign records contain another measured commit")

    def optional_path(value: str | None) -> Path | None:
        return Path(value) if value else None

    captures = {
        33: (
            Path(arm["captures"]["33"]["path"]),
            optional_path(arm["captures"]["33"].get("sidecar")),
        ),
        105: (
            Path(arm["captures"]["105"]["path"]),
            optional_path(arm["captures"]["105"].get("sidecar")),
        ),
        299: (
            Path(arm["captures"]["299"]["path"]),
            optional_path(arm["captures"]["299"].get("sidecar")),
        ),
    }
    modulo_capture = Path(arm["modulo_capture"]["path"])
    modulo_sidecars = {
        count: optional_path(arm["modulo_capture"].get("sidecars", {}).get(str(count)))
        for count in MODULO_COUNTS
    }

    def position_key(
        kind: str, count: int, workers: int, repetition: int | None
    ) -> str:
        return f"{kind}:N{count}:W{workers}:R{repetition or 0}"

    accepted_positions = {
        row["position_key"]
        for row in existing
        if row.get("accepted_for_protocol") is True and row.get("position_key")
    }
    attempts_by_position: dict[str, int] = defaultdict(int)
    for row in existing:
        if row.get("position_key"):
            attempts_by_position[row["position_key"]] = max(
                attempts_by_position[row["position_key"]],
                int(row.get("attempt", 1)),
            )

    host_start_path = output_root / "host-start.json"
    if not host_start_path.exists():
        campaign_gate = wait_for_quiet(
            sample_seconds=preload_sample_seconds,
            busy_max=preload_busy_max,
            retry_seconds=retry_seconds,
        )
        write_json(
            host_start_path,
            {
                "schema": 1,
                "evidence_tag": "VERIFIED",
                "measured_commit": measured_commit,
                "generated_utc": utc_now(),
                "phase": "campaign-start",
                "gate": campaign_gate,
                "host": {
                    "node": platform.node(),
                    "platform": platform.platform(),
                    "logical_processors": os.cpu_count(),
                    "memory": memory_status(),
                    "workspace_drive": shutil.disk_usage(ROOT.anchor)._asdict(),
                },
            },
        )

    def execute(
        *,
        count: int,
        workers: int,
        stack: Path,
        sidecar: Path | None,
        kind: str,
        repetition: int | None,
        sweep: str,
    ) -> None:
        key = position_key(kind, count, workers, repetition)
        if key in accepted_positions:
            print(f"SKIP accepted {key}", flush=True)
            return
        while True:
            attempts_by_position[key] += 1
            attempt = attempts_by_position[key]
            preload = wait_for_quiet(
                sample_seconds=preload_sample_seconds,
                busy_max=preload_busy_max,
                retry_seconds=retry_seconds,
            )
            tag = f"{kind}-n{count}-w{workers}-{sweep}"
            if repetition is not None:
                tag += f"-r{repetition}"
            tag += f"-a{attempt}"
            record = run_once(
                exe=binary,
                stack=stack,
                limit=count,
                workers=workers,
                destination=output_root / "runs" / f"{tag}.tiff",
                cache=output_root / "cache" / f"n{count}",
                temp=output_root / "runs" / f"{tag}-temp",
                flags=flags,
                sidecar=sidecar,
                align_off=False,
                fixed_env=fixed_env,
                required_log_substrings=required,
                kind=kind,
                repetition=repetition,
                sweep=sweep,
                measured_commit=measured_commit,
                external_busy_max=external_busy_max,
            )
            load_valid = (
                preload["attempts"][-1]["accepted"]
                and record["host_load_during_run"]["pass"]
            )
            record.update(
                {
                    "evidence_tag": "VERIFIED",
                    "position_key": key,
                    "attempt": attempt,
                    "preload_gate": preload,
                    "load_gate_valid": load_valid,
                    "accepted_for_protocol": record["valid"] and load_valid,
                    "manifest_path": str(manifest_path),
                    "manifest_sha256": sha256_file(manifest_path),
                    "input_manifest_sha256": manifest["input_manifest"]["sha256"],
                    "harness_sha256": manifest["harness"]["sha256"],
                    "registration_status": manifest["registration_status"],
                }
            )
            append_jsonl(records_path, record)
            print(
                f"{'ACCEPT' if record['accepted_for_protocol'] else 'REJECT'} {tag} "
                f"wall={record['wall_seconds']:.3f}s "
                f"external={record['host_load_during_run']['external_busy_fraction_of_wall_capacity']:.4f} "
                f"peak={record['memory']['peak_process_tree_private_committed_bytes'] / (1 << 30):.3f}GiB "
                f"hash={record.get('output_sha256', '-')[:16]}",
                flush=True,
            )
            if not record["valid"]:
                raise RuntimeError(f"{tag} invalid: {record['invalid_reasons']}")
            if load_valid:
                accepted_positions.add(key)
                return
            time.sleep(retry_seconds)

    for count in REGISTERED_COUNTS:
        stack, sidecar = captures[count]
        for workers in WORKERS:
            execute(
                count=count,
                workers=workers,
                stack=stack,
                sidecar=sidecar,
                kind="warmup",
                repetition=None,
                sweep="ascending",
            )
        for repetition in range(1, 7):
            order = WORKERS if repetition % 2 else tuple(reversed(WORKERS))
            sweep = "ascending" if repetition % 2 else "descending"
            for workers in order:
                execute(
                    count=count,
                    workers=workers,
                    stack=stack,
                    sidecar=sidecar,
                    kind="scored",
                    repetition=repetition,
                    sweep=sweep,
                )

    for count in MODULO_COUNTS:
        execute(
            count=count,
            workers=16,
            stack=modulo_capture,
            sidecar=modulo_sidecars[count],
            kind="modulo-warmup",
            repetition=None,
            sweep="ascending",
        )
    for repetition in range(1, 7):
        order = MODULO_COUNTS if repetition % 2 else tuple(reversed(MODULO_COUNTS))
        sweep = "ascending" if repetition % 2 else "descending"
        for count in order:
            execute(
                count=count,
                workers=16,
                stack=modulo_capture,
                sidecar=modulo_sidecars[count],
                kind="modulo-scored",
                repetition=repetition,
                sweep=sweep,
            )
    end_sample = sample_host_load(preload_sample_seconds)
    write_json(
        output_root / "host-end.json",
        {
            "schema": 1,
            "evidence_tag": "VERIFIED",
            "measured_commit": measured_commit,
            "generated_utc": utc_now(),
            "phase": "campaign-end",
            "sample": end_sample,
            "record_count": sum(
                1
                for line in records_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ),
            "records_sha256": sha256_file(records_path),
        },
    )
    return 0


def summarize(records_path: Path, output: Path, manifest_path: Path) -> int:
    records_path = records_path.resolve()
    output = output.resolve()
    manifest_path = manifest_path.resolve()
    manifest = load_manifest(manifest_path)
    measured_commit = manifest["measured_commit"]
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(row.get("measured_commit") != measured_commit for row in records):
        raise RuntimeError("campaign records do not all match the manifest commit")
    invalid = [row for row in records if not row.get("valid")]
    rejected = [
        row
        for row in records
        if row.get("valid") and row.get("accepted_for_protocol") is False
    ]
    accepted = [
        row
        for row in records
        if row.get("valid") and row.get("accepted_for_protocol") is True
    ]
    scored = [row for row in accepted if row.get("kind") == "scored"]
    cells: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        cells[(int(row["limit"]), int(row["workers"]))].append(row)
    determinism = {}
    for count in REGISTERED_COUNTS:
        for workers in WORKERS:
            rows = cells[(count, workers)]
            output_hashes = sorted({row["output_sha256"] for row in rows})
            pixel_hashes = sorted({row["pixel_sha256"] for row in rows})
            determinism[f"N{count}-W{workers}"] = {
                "runs": len(rows),
                "distinct_output_sha256": len(output_hashes),
                "output_sha256": output_hashes,
                "distinct_pixel_sha256": len(pixel_hashes),
                "pixel_sha256": pixel_hashes,
                "peak_private_committed_bytes": [
                    row["memory"]["peak_process_tree_private_committed_bytes"]
                    for row in rows
                ],
                "wall_seconds": [row["wall_seconds"] for row in rows],
                "pass": (
                    len(rows) == 6
                    and len(output_hashes) == 1
                    and len(pixel_hashes) == 1
                ),
            }
    scaling = {}
    for count in REGISTERED_COUNTS:
        output_hashes = {
            row["output_sha256"]
            for workers in WORKERS
            for row in cells[(count, workers)]
        }
        pixel_hashes = {
            row["pixel_sha256"]
            for workers in WORKERS
            for row in cells[(count, workers)]
        }
        scaling[str(count)] = {
            "distinct_output_sha256": len(output_hashes),
            "output_sha256": sorted(output_hashes),
            "distinct_pixel_sha256": len(pixel_hashes),
            "pixel_sha256": sorted(pixel_hashes),
            "byte_invariant": len(output_hashes) == 1 and len(pixel_hashes) == 1,
        }
    peak_by_n_worker = {
        count: {
            workers: max(
                (
                    row["memory"]["peak_process_tree_private_committed_bytes"]
                    for row in cells[(count, workers)]
                ),
                default=0,
            )
            for workers in WORKERS
        }
        for count in REGISTERED_COUNTS
    }
    peak_by_n = {
        count: max(peak_by_n_worker[count].values(), default=0)
        for count in REGISTERED_COUNTS
    }
    ratio_by_worker = {
        workers: (
            peak_by_n_worker[299][workers] / peak_by_n_worker[33][workers]
            if peak_by_n_worker[33][workers]
            else None
        )
        for workers in WORKERS
    }
    sample_quality_rows = []
    for row in scored:
        memory = row["memory"]
        scheduled = memory["sample_count"] + memory["missed_intervals"]
        coverage = memory["sample_count"] / scheduled if scheduled else 0.0
        sample_quality_rows.append(
            {
                "position_key": row["position_key"],
                "coverage": coverage,
                "max_gap_ms": memory["max_gap_ms"],
                "pass": coverage >= 0.90 and memory["max_gap_ms"] <= 100.0,
            }
        )
    sample_quality_pass = (
        len(sample_quality_rows) == 6 * len(REGISTERED_COUNTS) * len(WORKERS)
        and all(row["pass"] for row in sample_quality_rows)
    )
    absolute_peak = max(peak_by_n.values(), default=0)
    absolute_memory_verdict = (
        "FAIL"
        if absolute_peak > 6 * (1 << 30)
        else "PASS"
        if sample_quality_pass and absolute_peak > 0
        else "UNMEASURED"
    )
    ratio_values = [value for value in ratio_by_worker.values() if value is not None]
    ratio_max = max(ratio_values) if len(ratio_values) == len(WORKERS) else None
    ratio_verdict = (
        "PASS"
        if sample_quality_pass and ratio_max is not None and ratio_max <= 1.10
        else "FAIL"
        if sample_quality_pass and ratio_max is not None
        else "UNMEASURED"
    )
    modulo = [
        row
        for row in accepted
        if row.get("kind") == "modulo-scored"
    ]
    best_per_frame = {}
    modulo_by_n = {}
    for count in MODULO_COUNTS:
        walls = [float(row["wall_seconds"]) for row in modulo if int(row["limit"]) == count]
        best_per_frame[count] = min(walls) / count if walls else None
        modulo_by_n[count] = {
            "runs": len(walls),
            "wall_seconds": walls,
            "best_wall_seconds": min(walls) if walls else None,
            "best_wall_seconds_per_frame": best_per_frame[count],
            "output_sha256": sorted(
                {
                    row["output_sha256"]
                    for row in modulo
                    if int(row["limit"]) == count
                }
            ),
            "pixel_sha256": sorted(
                {
                    row["pixel_sha256"]
                    for row in modulo
                    if int(row["limit"]) == count
                }
            ),
        }
    valid_modulo_values = [value for value in best_per_frame.values() if value is not None]
    modulo_spread = (
        (max(valid_modulo_values) - min(valid_modulo_values)) / min(valid_modulo_values)
        if len(valid_modulo_values) == len(MODULO_COUNTS)
        else None
    )
    modulo_load_verified = (
        len(modulo) == 6 * len(MODULO_COUNTS)
        and all(row.get("load_gate_valid") is True for row in modulo)
    )
    observed_modulo_pass = modulo_spread is not None and modulo_spread <= 0.02
    modulo_verdict = (
        "PASS"
        if observed_modulo_pass and modulo_load_verified
        else "FAIL"
        if modulo_load_verified and modulo_spread is not None
        else "UNMEASURED"
    )
    matrix_complete = all(
        len(cells[(count, workers)]) == 6
        for count in REGISTERED_COUNTS
        for workers in WORKERS
    )
    m12_d_pass = matrix_complete and all(
        row["pass"] for row in determinism.values()
    )
    m12_s_pass = matrix_complete and all(
        row["byte_invariant"] for row in scaling.values()
    )
    m12_d_verdict = "PASS" if m12_d_pass else "FAIL" if matrix_complete else "UNMEASURED"
    m12_s_byte_verdict = (
        "PASS" if m12_s_pass else "FAIL" if matrix_complete else "UNMEASURED"
    )
    hard_failures = []
    if absolute_memory_verdict == "FAIL":
        hard_failures.append("absolute-memory")
    if ratio_verdict == "FAIL":
        hard_failures.append("memory-scaling")
    if m12_d_verdict == "FAIL":
        hard_failures.append("fixed-worker-determinism")
    if m12_s_byte_verdict == "FAIL":
        hard_failures.append("cross-worker-scaling-invariance")
    if modulo_verdict == "FAIL":
        hard_failures.append("n-mod-4-spread")
    m11_joint_verdict = "UNMEASURED"
    if hard_failures:
        overall_verdict = "FAIL"
    elif all(
        verdict == "PASS"
        for verdict in (
            absolute_memory_verdict,
            ratio_verdict,
            m12_d_verdict,
            m12_s_byte_verdict,
            modulo_verdict,
        )
    ) and m11_joint_verdict == "PASS":
        overall_verdict = "PASS"
    else:
        overall_verdict = "UNMEASURED"
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "records": {
            "path": str(records_path),
            "sha256": sha256_file(records_path),
            "total": len(records),
            "accepted": len(accepted),
            "rejected_for_host_load": len(rejected),
        },
        "manifest": {
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        "invalid_run_count": len(invalid),
        "m12_d": {
            "cells": determinism,
            "pass": m12_d_pass,
            "verdict": m12_d_verdict,
        },
        "m12_s_byte_property": {
            "by_n": scaling,
            "pass": m12_s_pass,
            "verdict": m12_s_byte_verdict,
            "m11_joint_requirement": m11_joint_verdict,
        },
        "memory": {
            "peak_private_committed_bytes_by_n_worker": peak_by_n_worker,
            "peak_private_committed_bytes_by_n_max_over_scored_matrix": peak_by_n,
            "peak_gib_max": absolute_peak / (1 << 30),
            "six_gib_pass": absolute_memory_verdict == "PASS",
            "six_gib_verdict": absolute_memory_verdict,
            "peak_n299_over_peak_n33_by_worker": ratio_by_worker,
            "peak_n299_over_peak_n33_max": ratio_max,
            "ratio_pass": ratio_verdict == "PASS",
            "ratio_verdict": ratio_verdict,
            "sampling_quality": {
                "pre_registered_pass_rule": (
                    "every scored run coverage >=0.90 and max gap <=100 ms"
                ),
                "pass": sample_quality_pass,
                "minimum_coverage": min(
                    (row["coverage"] for row in sample_quality_rows), default=None
                ),
                "maximum_gap_ms": max(
                    (row["max_gap_ms"] for row in sample_quality_rows), default=None
                ),
                "failed_positions": [
                    row["position_key"]
                    for row in sample_quality_rows
                    if not row["pass"]
                ],
            },
        },
        "modulo": {
            "by_n": modulo_by_n,
            "best_wall_seconds_per_frame_by_n": best_per_frame,
            "spread": modulo_spread,
            "observed_pass_without_load_gate": observed_modulo_pass,
            "load_gate_verified": modulo_load_verified,
            "rejected_run_count": sum(
                row.get("load_gate_valid") is False
                for row in records
                if row.get("kind") in {"modulo-scored", "modulo-rejected"}
            ),
            "pass": observed_modulo_pass and modulo_load_verified,
            "scorecard_verdict": modulo_verdict,
        },
        "host_load": {
            "accepted_runs_all_passed": all(
                row.get("load_gate_valid") is True for row in accepted
            ),
            "rejected_run_count": len(rejected),
            "total_preload_rejected_samples": sum(
                row.get("preload_gate", {}).get("rejected_sample_count", 0)
                for row in records
            ),
            "total_wait_seconds": sum(
                row.get("preload_gate", {}).get("wait_seconds", 0.0)
                for row in records
            ),
            "maximum_accepted_external_busy_fraction": max(
                (
                    row["host_load_during_run"][
                        "external_busy_fraction_of_wall_capacity"
                    ]
                    for row in accepted
                ),
                default=None,
            ),
        },
        "formal_m12": {
            "verdict": overall_verdict,
            "hard_failures": hard_failures,
            "m11_joint_verdict": m11_joint_verdict,
            "reason_if_unmeasured": (
                "M11 joint requirement is not supplied"
                if overall_verdict == "UNMEASURED"
                else None
            ),
        },
    }
    write_json(output, result)
    print(json.dumps(result, indent=2))
    complete = (
        not invalid
        and matrix_complete
        and len(modulo) == 6 * len(MODULO_COUNTS)
        and all(row.get("load_gate_valid") is True for row in accepted)
    )
    return 0 if complete else 1


def audit_campaign(campaign_root: Path, output: Path) -> int:
    campaign_root = campaign_root.resolve()
    output = output.resolve()
    names = {
        "registration": "registration.json",
        "input_manifest": "input-manifest.json",
        "input_exif": "input-exif.json",
        "preflight": "preflight.json",
        "build": "build.json",
        "run_manifest": "RUN-MANIFEST.json",
        "determinism_commission": "determinism-commission.json",
        "memory_commission": "memory-commission.json",
        "smoke": "smoke.json",
        "records": "records.jsonl",
        "summary": "summary.json",
        "host_start": "host-start.json",
        "host_end": "host-end.json",
        "read_only_before": "read-only-before.json",
        "read_only_after": "read-only-after.json",
    }
    paths = {key: campaign_root / name for key, name in names.items()}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise RuntimeError("missing campaign artifacts:\n" + "\n".join(missing))
    manifest = read_json(paths["run_manifest"])
    measured_commit = manifest["measured_commit"]
    summary = read_json(paths["summary"])
    determinism_commission = read_json(paths["determinism_commission"])
    memory_commission = read_json(paths["memory_commission"])
    smoke_record = read_json(paths["smoke"])
    before = read_json(paths["read_only_before"])
    after = read_json(paths["read_only_after"])
    json_artifacts = {
        key: read_json(path)
        for key, path in paths.items()
        if path.suffix.lower() == ".json"
    }
    mismatched_commits = {
        key: artifact.get("measured_commit")
        for key, artifact in json_artifacts.items()
        if artifact.get("measured_commit") != measured_commit
    }
    before_roots = {row["path"]: row for row in before["roots"]}
    after_roots = {row["path"]: row for row in after["roots"]}
    tree_comparison = {}
    for root in sorted(set(before_roots) | set(after_roots)):
        left = before_roots.get(root)
        right = after_roots.get(root)
        tree_comparison[root] = {
            "before": left,
            "after": right,
            "unchanged": left == right,
        }
    records = [
        json.loads(line)
        for line in paths["records"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    result = {
        "schema": 1,
        "evidence_tag": "VERIFIED",
        "measured_commit": measured_commit,
        "generated_utc": utc_now(),
        "formal_m12": summary["formal_m12"],
        "commissioning": {
            "determinism": {
                "status": determinism_commission["status"],
                "hash_gate": determinism_commission["hash_gate"],
            },
            "memory": {
                "status": memory_commission["status"],
                "verdict": memory_commission["verdict"],
            },
            "smoke": {
                "status": smoke_record["status"],
                "verdict": smoke_record["verdict"],
            },
        },
        "read_only_inputs": {
            "comparison": tree_comparison,
            "unchanged": bool(tree_comparison)
            and all(row["unchanged"] for row in tree_comparison.values()),
        },
        "host_conditions": {
            "start": read_json(paths["host_start"]),
            "end": read_json(paths["host_end"]),
            "campaign": summary["host_load"],
        },
        "integrity": {
            "mismatched_measured_commits": mismatched_commits,
            "record_count": len(records),
            "record_measured_commits": sorted(
                {row.get("measured_commit") for row in records}
            ),
            "artifacts": {
                key: {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for key, path in paths.items()
            },
        },
        "could_not_determine": [
            {
                "item": "M11 joint requirement",
                "reason": (
                    "M11 remains UNMEASURED; M12 can nevertheless close FAIL if "
                    "an independent M12 hard bar fails."
                ),
            },
            {
                "item": "comparative common-TIFF memory",
                "reason": (
                    "No registered common-TIFF product/comparator arm exists; "
                    "the M12 absolute bars apply to the native product arm."
                ),
            },
            {
                "item": "true unsampled instantaneous memory peak",
                "reason": (
                    "A sampled monitor reports an observed lower bound. Any "
                    "sampling gaps can hide a higher peak but cannot manufacture "
                    "an observed above-bar allocation."
                ),
            },
        ],
    }
    result["integrity"]["pass"] = (
        not mismatched_commits
        and result["read_only_inputs"]["unchanged"]
        and result["commissioning"]["determinism"]["status"] == "COMMISSIONED"
        and result["commissioning"]["memory"]["status"] == "COMMISSIONED"
        and result["commissioning"]["smoke"]["status"] == "PASS"
        and result["integrity"]["record_measured_commits"] == [measured_commit]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    write_json(output, result)
    print(json.dumps(result, indent=2))
    return 0 if result["integrity"]["pass"] else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    pre = commands.add_parser("preflight")
    pre.add_argument("--output", type=Path, required=True)
    pre.add_argument("--measured-commit", required=True)

    registration = commands.add_parser("registration")
    registration.add_argument("--output", type=Path, required=True)
    registration.add_argument("--measured-commit", required=True)

    inputs = commands.add_parser("input-manifest")
    inputs.add_argument("--output", type=Path, required=True)
    inputs.add_argument("--exif-output", type=Path, required=True)
    inputs.add_argument("--measured-commit", required=True)

    build = commands.add_parser("build")
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--work", type=Path, required=True)
    build.add_argument("--measured-commit", required=True)
    build.add_argument("--jobs", type=int, default=4)

    manifest = commands.add_parser("manifest")
    manifest.add_argument("--output", type=Path, required=True)
    manifest.add_argument("--measured-commit", required=True)
    manifest.add_argument("--registration", type=Path, required=True)
    manifest.add_argument("--input-manifest", type=Path, required=True)
    manifest.add_argument("--build", type=Path, required=True)
    manifest.add_argument("--preflight", type=Path, required=True)

    com = commands.add_parser("commission")
    com.add_argument("--output", type=Path, required=True)
    com.add_argument("--work", type=Path, required=True)
    com.add_argument("--stack", type=Path, default=Path(r"D:\personal\macro\coffee-bean"))
    com.add_argument("--limit", type=int, default=3)
    com.add_argument("--workers", type=int, default=1)
    com.add_argument("--measured-commit", required=True)

    memory = commands.add_parser("commission-memory")
    memory.add_argument("--output", type=Path, required=True)
    memory.add_argument("--work", type=Path, required=True)
    memory.add_argument("--measured-commit", required=True)

    smoke_command = commands.add_parser("smoke")
    smoke_command.add_argument("--manifest", type=Path, required=True)
    smoke_command.add_argument("--output", type=Path, required=True)
    smoke_command.add_argument("--work", type=Path, required=True)

    run = commands.add_parser("matrix")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--records", type=Path, required=True)
    run.add_argument("--output-root", type=Path, required=True)

    summary = commands.add_parser("summarize")
    summary.add_argument("--records", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    summary.add_argument("--manifest", type=Path, required=True)

    audit = commands.add_parser("audit")
    audit.add_argument("--campaign-root", type=Path, required=True)
    audit.add_argument("--output", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "preflight":
        return preflight(args.output, args.measured_commit)
    if args.command == "registration":
        return registration_artifact(args.output, args.measured_commit)
    if args.command == "input-manifest":
        return input_manifest(
            output=args.output,
            exif_output=args.exif_output,
            measured_revision=args.measured_commit,
        )
    if args.command == "build":
        return build_measured(
            output=args.output,
            work=args.work,
            measured_revision=args.measured_commit,
            jobs=args.jobs,
        )
    if args.command == "manifest":
        return write_run_manifest(
            output=args.output,
            measured_revision=args.measured_commit,
            registration_path=args.registration,
            input_path=args.input_manifest,
            build_path=args.build,
            preflight_path=args.preflight,
        )
    if args.command == "commission":
        return commission(
            args.output,
            args.work,
            args.stack,
            args.limit,
            args.workers,
            args.measured_commit,
        )
    if args.command == "commission-memory":
        return commission_memory(args.output, args.work, args.measured_commit)
    if args.command == "smoke":
        return smoke(args.manifest, args.output, args.work)
    if args.command == "matrix":
        return matrix(args.manifest, args.records, args.output_root)
    if args.command == "summarize":
        return summarize(args.records, args.output, args.manifest)
    if args.command == "audit":
        return audit_campaign(args.campaign_root, args.output)
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
