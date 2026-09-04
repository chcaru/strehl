from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import time
import uuid
from collections import defaultdict
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

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

TH32CS_SNAPPROCESS = 0x00000002
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
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


def preflight(output: Path) -> int:
    registered_rel = "docs/proposals/2026-09-sota-scorecard.md"
    current_commit = git_text("log", "-1", "--format=%H", "--", registered_rel)
    registered = git_bytes(current_commit, registered_rel)
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
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "registered_scorecard": {
            "commit": current_commit,
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
        bee["arw_count"] == 299
        and not bee["missing_expected"]
        and coffee["arw_count"] == 105
        and not coffee["missing_expected"]
        and all(prefix_availability.values())
    )
    return 0 if captures_ok else 1


def process_snapshot() -> dict[int, int]:
    handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if handle == INVALID_HANDLE_VALUE:
        raise ctypes.WinError(ctypes.get_last_error())
    rows: dict[int, int] = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(entry)
        ok = kernel32.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            rows[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            ok = kernel32.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(handle)
    return rows


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
) -> dict[str, Any]:
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    start = time.perf_counter()
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

    with stdout_path.open("w", encoding="utf-8", newline="\n") as stdout, stderr_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as stderr:
        process = subprocess.Popen(
            argv,
            env=env,
            stdout=stdout,
            stderr=stderr,
            text=True,
            errors="replace",
        )
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

            parents = process_snapshot()
            live_tree = descendants(process.pid, parents) if process.pid in parents else set()
            candidate_pids = live_tree | (set(known) & set(parents))
            rows: list[tuple[int, dict[str, int]]] = []
            for pid in candidate_pids:
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
                        "first_seen_s": sampled_at - start,
                        "last_seen_s": sampled_at - start,
                        "samples": 1,
                    }
                else:
                    prior["last_seen_s"] = sampled_at - start
                    prior["samples"] += 1
                rows.append((pid, counters))

            peak_private = max(peak_private, sum(row["private"] for _, row in rows))
            peak_working_set = max(
                peak_working_set, sum(row["working_set"] for _, row in rows)
            )
            peak_page_faults = max(
                peak_page_faults, sum(row["page_faults"] for _, row in rows)
            )
            peak_process_count = max(peak_process_count, len(rows))
            if sample_count % 10 == 0:
                peak_temp_bytes = max(peak_temp_bytes, tree_bytes(temp))
            sample_count += 1

            root_done = process.poll() is not None
            if root_done and not rows:
                empty_after_exit += 1
            else:
                empty_after_exit = 0
            if root_done and empty_after_exit >= 2:
                break

            next_sample += SAMPLE_INTERVAL_S
            if next_sample <= sampled_at:
                skipped = int((sampled_at - next_sample) // SAMPLE_INTERVAL_S) + 1
                missed_intervals += skipped
                next_sample += skipped * SAMPLE_INTERVAL_S
        returncode = process.wait()

    wall = time.perf_counter() - start
    return {
        "started_utc": started_utc,
        "returncode": returncode,
        "wall_seconds": wall,
        "stdout_log": str(stdout_path.resolve()),
        "stderr_log": str(stderr_path.resolve()),
        "memory": {
            "sample_interval_ms": SAMPLE_INTERVAL_S * 1000.0,
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
            "process_lifetimes": [
                {"pid": pid, **details} for pid, details in sorted(known.items())
            ],
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
    )
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    record: dict[str, Any] = {
        "schema": 1,
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
    result = run_text(command, cwd=source, env=env, log=log)
    exe = target / "release" / "strehl.exe"
    if not exe.exists():
        raise RuntimeError(f"build completed but {exe} is missing")
    return exe, result.stdout


def commission(output: Path, work: Path, stack: Path, limit: int, workers: int) -> int:
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
    if crate_status:
        raise RuntimeError(
            "commissioning archive would omit live crate edits; refusing:\n" + crate_status
        )
    head = git_text("rev-parse", "HEAD")
    build_id = head[:12]
    archive = work / "source.tar"
    run_text(
        ["git", "-C", str(ROOT), "archive", "--format=tar", f"--output={archive}", head],
        log=output.parent / "commission-archive.log",
    )
    with tarfile.open(archive, "r") as bundle:
        bundle.extractall(source, filter="data")
    archive.unlink()

    initial_exe, initial_build = build_release(
        source,
        target,
        output.parent / "commission-build-initial.log",
        build_id,
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
        )
        if not record["valid"]:
            raise RuntimeError(f"{name} render invalid: {record['invalid_reasons']}")
        return record

    baseline = render("baseline", initial_exe)
    source_file = source / "crates" / "strehl-core" / "src" / "pyramid.rs"
    original_hash = sha256_file(source_file)
    temp_root = Path(os.environ["TEMP"])
    backup = temp_root / f"m12-pyramid-{uuid.uuid4().hex}.rs"
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
                raise RuntimeError("TEMP restore did not reproduce the original source bytes")
            restored_exe, restore_build = build_release(
                source,
                target,
                output.parent / "commission-build-restored.log",
                build_id,
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
        "status": (
            "COMMISSIONED"
            if red and pixel_red and green and pixel_green and provenance_green and lsb_red
            else "FAILED"
        ),
        "scope": (
            "Diagnostic N-limited, alignment-off native-RAW pyramid arm used only to "
            "commission byte detection; it is not an M12 score reading."
        ),
        "source_commit": head,
        "forced_build_id": build_id,
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
            "backup_was_under_env_TEMP": str(temp_root),
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


def commission_memory(output: Path, work: Path) -> int:
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


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    registration_status = manifest.get("registration_status")
    if registration_status not in {"registered", "operator-authorized-diagnostic"}:
        raise RuntimeError(
            "run manifest must be registrar-approved or explicitly operator-authorized "
            "as diagnostic (`registration_status`)"
        )
    expected_hash = manifest["scorecard"]["sha256"].upper()
    if sha256_file(SCORECARD) != expected_hash:
        raise RuntimeError("working scorecard bytes do not match the run manifest")
    status = git_text(
        "status",
        "--short",
        "--",
        str(SCORECARD.relative_to(ROOT)).replace("\\", "/"),
    )
    if status:
        raise RuntimeError("scorecard has uncommitted changes; refusing a formal run")
    binary = Path(manifest["binary"]["path"])
    if sha256_file(binary) != manifest["binary"]["sha256"].upper():
        raise RuntimeError("binary hash does not match the run manifest")
    return manifest


def matrix(manifest_path: Path, records_path: Path, output_root: Path) -> int:
    manifest_path = manifest_path.resolve()
    records_path = records_path.resolve()
    output_root = output_root.resolve()
    if records_path.exists():
        raise RuntimeError(f"refusing to append a second campaign to {records_path}")
    manifest = load_manifest(manifest_path)
    binary = Path(manifest["binary"]["path"])
    arm = manifest["product_arm"]
    flags = list(arm["flags"])
    fixed_env = {str(key): str(value) for key, value in arm.get("fixed_env", {}).items()}
    required = list(arm["required_log_substrings"])

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
    cache = output_root / "cache"

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
        tag = f"{kind}-n{count}-w{workers}-{sweep}"
        if repetition is not None:
            tag += f"-r{repetition}"
        record = run_once(
            exe=binary,
            stack=stack,
            limit=count,
            workers=workers,
            destination=output_root / "runs" / f"{tag}.tiff",
            cache=cache,
            temp=output_root / "runs" / f"{tag}-temp",
            flags=flags,
            sidecar=sidecar,
            align_off=False,
            fixed_env=fixed_env,
            required_log_substrings=required,
            kind=kind,
            repetition=repetition,
            sweep=sweep,
        )
        record["manifest_sha256"] = sha256_file(manifest_path)
        record["registration_status"] = manifest["registration_status"]
        append_jsonl(records_path, record)
        print(
            f"{'VALID' if record['valid'] else 'INVALID'} {tag} "
            f"wall={record['wall_seconds']:.3f}s "
            f"peak={record['memory']['peak_process_tree_private_committed_bytes'] / (1 << 30):.3f}GiB "
            f"hash={record.get('output_sha256', '-')[:16]}",
            flush=True,
        )
        if not record["valid"]:
            raise RuntimeError(f"{tag} invalid: {record['invalid_reasons']}")

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
    return 0


def summarize(records_path: Path, output: Path) -> int:
    records_path = records_path.resolve()
    output = output.resolve()
    records = [
        json.loads(line)
        for line in records_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    invalid = [row for row in records if not row.get("valid")]
    scored = [row for row in records if row.get("kind") == "scored" and row.get("valid")]
    cells: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in scored:
        cells[(int(row["limit"]), int(row["workers"]))].append(row)
    determinism = {}
    for count in REGISTERED_COUNTS:
        for workers in WORKERS:
            rows = cells[(count, workers)]
            hashes = sorted({row["output_sha256"] for row in rows})
            determinism[f"N{count}-W{workers}"] = {
                "runs": len(rows),
                "distinct_hashes": len(hashes),
                "hashes": hashes,
                "pass": len(rows) == 6 and len(hashes) == 1,
            }
    scaling = {}
    for count in REGISTERED_COUNTS:
        hashes = {
            row["output_sha256"]
            for workers in WORKERS
            for row in cells[(count, workers)]
        }
        scaling[str(count)] = {
            "distinct_hashes": len(hashes),
            "hashes": sorted(hashes),
            "byte_invariant": len(hashes) == 1,
        }
    peak_by_n = {
        count: max(
            (
                row["memory"]["peak_process_tree_private_committed_bytes"]
                for row in scored
                if int(row["limit"]) == count
            ),
            default=0,
        )
        for count in REGISTERED_COUNTS
    }
    modulo = [
        row
        for row in records
        if row.get("kind") == "modulo-scored" and row.get("valid")
    ]
    best_per_frame = {}
    for count in MODULO_COUNTS:
        walls = [float(row["wall_seconds"]) for row in modulo if int(row["limit"]) == count]
        best_per_frame[count] = min(walls) / count if walls else None
    valid_modulo_values = [value for value in best_per_frame.values() if value is not None]
    modulo_spread = (
        (max(valid_modulo_values) - min(valid_modulo_values)) / min(valid_modulo_values)
        if len(valid_modulo_values) == len(MODULO_COUNTS)
        else None
    )
    result = {
        "schema": 1,
        "invalid_run_count": len(invalid),
        "m12_d": {
            "cells": determinism,
            "pass": all(row["pass"] for row in determinism.values()),
        },
        "m12_s_byte_property": {
            "by_n": scaling,
            "pass": all(row["byte_invariant"] for row in scaling.values()),
            "m11_joint_requirement": "must be supplied separately",
        },
        "memory": {
            "peak_private_committed_bytes_by_n_max_over_scored_matrix": peak_by_n,
            "peak_gib_max": max(peak_by_n.values(), default=0) / (1 << 30),
            "six_gib_pass": max(peak_by_n.values(), default=0) <= 6 * (1 << 30),
            "peak_n299_over_peak_n33": (
                peak_by_n[299] / peak_by_n[33] if peak_by_n[33] else None
            ),
        },
        "modulo": {
            "best_wall_seconds_per_frame_by_n": best_per_frame,
            "spread": modulo_spread,
            "pass": modulo_spread is not None and modulo_spread <= 0.02,
        },
    }
    write_json(output, result)
    print(json.dumps(result, indent=2))
    complete = (
        not invalid
        and result["m12_d"]["pass"]
        and all(len(cells[(count, workers)]) == 6 for count in REGISTERED_COUNTS for workers in WORKERS)
        and len(modulo) == 6 * len(MODULO_COUNTS)
    )
    return 0 if complete else 1


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser()
    commands = root.add_subparsers(dest="command", required=True)

    pre = commands.add_parser("preflight")
    pre.add_argument("--output", type=Path, required=True)

    com = commands.add_parser("commission")
    com.add_argument("--output", type=Path, required=True)
    com.add_argument("--work", type=Path, required=True)
    com.add_argument("--stack", type=Path, default=Path(r"D:\personal\macro\coffee-bean"))
    com.add_argument("--limit", type=int, default=3)
    com.add_argument("--workers", type=int, default=1)

    memory = commands.add_parser("commission-memory")
    memory.add_argument("--output", type=Path, required=True)
    memory.add_argument("--work", type=Path, required=True)

    run = commands.add_parser("matrix")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--records", type=Path, required=True)
    run.add_argument("--output-root", type=Path, required=True)

    summary = commands.add_parser("summarize")
    summary.add_argument("--records", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "preflight":
        return preflight(args.output)
    if args.command == "commission":
        return commission(args.output, args.work, args.stack, args.limit, args.workers)
    if args.command == "commission-memory":
        return commission_memory(args.output, args.work)
    if args.command == "matrix":
        return matrix(args.manifest, args.records, args.output_root)
    if args.command == "summarize":
        return summarize(args.records, args.output)
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
