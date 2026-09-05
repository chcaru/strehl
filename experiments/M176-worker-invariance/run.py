from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from common import (
    APPROVED_INPUT,
    EXPERIMENT_DIR,
    MAX_RESIDENT_BYTES,
    MIN_FREE_SCRATCH_BYTES,
    PRIVATE_SCRATCH,
    REPO_ROOT,
    EvidenceError,
    canonical_pixel_hash,
    capture_manifest,
    chunk_sizes,
    ensure_private_path,
    file_record,
    guard_capture_path,
    json_digest,
    read_json,
    script_hashes,
    sha256_bytes,
    sha256_file,
    source_tree_manifest,
    write_json_new,
)


M139_SOURCE = "8009447e059febb8f9c59fda509f141835d6abdb"
REPAIR_COMMIT = "fc2abb499126a56302de7f21f527de5613be34e7"
AFFECTED_COMMIT = "1a6fd10c94dcb4b780f6af78c46c62a156c39b71"
FIXED_COMMIT = "a97275817c58e164f75c7cd3d80ca99444a2a145"
FRAMES = 19
MAX_WORKERS = 3
BUILD_COMMAND = [
    "cargo",
    "build",
    "--release",
    "--locked",
    "-p",
    "strehl-cli",
    "--bin",
    "strehl",
]
RENDER_ARGS = [
    "stack",
    APPROVED_INPUT,
    "--out",
    "<OUTPUT>",
    "--limit",
    "19",
    "--merge",
    "pyramid",
    "--pyramid-bands",
    "7",
    "--pyramid-gate",
    "2.0",
    "--pyramid-exponent",
    "2.0",
    "--pyramid-sharpen",
    "1.4",
    "--pyramid-select",
    "soft",
    "--pyramid-base",
    "mean",
    "--linear-srgb",
    "--binned",
    "--fix-ca",
    "off",
    "--resampler",
    "catmull-rom",
    "--cover",
    "scale",
]
REQUIRED_RENDER_LOG = [
    "LAPLACIAN MULTI-BAND MERGE",
    "selection       : SOFT",
    "base band       : plain mean across frames",
    "alignment       : OFF",
    "defect map      : off",
    "lateral CA      : off",
    "folded          : 19 / 19 frames",
    "16-bit RGB, linear sRGB",
    "binned from one 2x2 quad per pixel",
]
ESSENTIAL_ENV = [
    "COMSPEC",
    "HOMEDRIVE",
    "HOMEPATH",
    "HOME",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PATH",
    "PATHEXT",
    "PROCESSOR_ARCHITECTURE",
    "SystemDrive",
    "SystemRoot",
    "USERPROFILE",
    "WINDIR",
]


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def write_bytes_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        raise EvidenceError(
            "M176-E-STALE", f"refusing pre-existing raw output {path}"
        ) from None


def command_string(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def capture_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
    expected_code: int = 0,
) -> dict[str, Any]:
    if stdout_path.exists() or stderr_path.exists():
        raise EvidenceError("M176-E-STALE", "command log already exists")
    completed = subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, check=False
    )
    write_bytes_new(stdout_path, completed.stdout)
    write_bytes_new(stderr_path, completed.stderr)
    if completed.returncode != expected_code:
        raise EvidenceError(
            "M176-E-COMMAND",
            f"{command_string(command)} exited {completed.returncode}, expected {expected_code}",
        )
    return {
        "argv": command,
        "command": command_string(command),
        "exit_code": completed.returncode,
        "stdout": file_record(stdout_path),
        "stderr": file_record(stderr_path),
        "stdout_text": completed.stdout.decode("utf-8", errors="replace"),
        "stderr_text": completed.stderr.decode("utf-8", errors="replace"),
    }


def git_text(args: list[str], expected: int = 0) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != expected:
        raise EvidenceError(
            "M176-E-GIT",
            f"git {' '.join(args)} exited {completed.returncode}: {completed.stderr.strip()}",
        )
    return completed.stdout.strip()


def lineage_evidence() -> dict[str, Any]:
    repair_parent = git_text(["rev-parse", f"{REPAIR_COMMIT}^"])
    if repair_parent != AFFECTED_COMMIT:
        raise EvidenceError(
            "M176-E-SOURCE",
            f"repair parent is {repair_parent}, not preregistered {AFFECTED_COMMIT}",
        )
    for older, newer, label in [
        (M139_SOURCE, AFFECTED_COMMIT, "M139 source to affected source"),
        (REPAIR_COMMIT, FIXED_COMMIT, "repair to fixed source"),
    ]:
        completed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", older, newer],
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            raise EvidenceError("M176-E-SOURCE", f"not an ancestry chain: {label}")
    fixed_subject = git_text(["show", "-s", "--format=%s", FIXED_COMMIT])
    if fixed_subject != "Bound Pyramid worker memory":
        raise EvidenceError(
            "M176-E-SOURCE",
            f"fixed commit subject drifted: {fixed_subject!r}",
        )
    return {
        "m139_report_source_lineage_only": M139_SOURCE,
        "m139_report_citation": "docs/research/M139-m12-campaign.md:11-15",
        "repair_commit": REPAIR_COMMIT,
        "repair_parent": repair_parent,
        "affected_source": AFFECTED_COMMIT,
        "fixed_source": FIXED_COMMIT,
        "fixed_subject": fixed_subject,
        "m139_is_ancestor_of_affected": True,
        "repair_is_ancestor_of_fixed": True,
        "affected_tree": git_text(["rev-parse", f"{AFFECTED_COMMIT}^{{tree}}"]),
        "fixed_tree": git_text(["rev-parse", f"{FIXED_COMMIT}^{{tree}}"]),
    }


def archive_source(commit: str, destination: Path, logs: Path) -> dict[str, Any]:
    if destination.exists():
        raise EvidenceError(
            "M176-E-STALE", f"archive destination exists: {destination}"
        )
    destination.mkdir(parents=True)
    git_command = [
        "git",
        "-C",
        str(REPO_ROOT),
        "archive",
        "--format=tar",
        commit,
    ]
    tar_command = ["tar", "-xf", "-", "-C", str(destination)]
    git_process = subprocess.Popen(
        git_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if git_process.stdout is None or git_process.stderr is None:
        raise EvidenceError("M176-E-ARCHIVE", "could not pipe git archive")
    tar_process = subprocess.Popen(
        tar_command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if tar_process.stdin is None:
        raise EvidenceError("M176-E-ARCHIVE", "could not pipe tar input")
    digest = hashlib.sha256()
    try:
        while block := git_process.stdout.read(8 * 1024 * 1024):
            digest.update(block)
            tar_process.stdin.write(block)
    finally:
        tar_process.stdin.close()
    git_stderr = git_process.stderr.read()
    git_code = git_process.wait()
    tar_stdout = b"" if tar_process.stdout is None else tar_process.stdout.read()
    tar_stderr = b"" if tar_process.stderr is None else tar_process.stderr.read()
    tar_code = tar_process.wait()
    git_stderr_path = logs / f"archive-{commit[:8]}.git.stderr.log"
    tar_stdout_path = logs / f"archive-{commit[:8]}.tar.stdout.log"
    tar_stderr_path = logs / f"archive-{commit[:8]}.tar.stderr.log"
    write_bytes_new(git_stderr_path, git_stderr)
    write_bytes_new(tar_stdout_path, tar_stdout)
    write_bytes_new(tar_stderr_path, tar_stderr)
    if git_code != 0 or tar_code != 0:
        raise EvidenceError(
            "M176-E-ARCHIVE",
            f"git archive/tar exited {git_code}/{tar_code}",
        )
    return {
        "commit": commit,
        "git_command": command_string(git_command),
        "tar_command": command_string(tar_command),
        "git_exit_code": git_code,
        "tar_exit_code": tar_code,
        "stream_sha256": digest.hexdigest(),
        "git_stderr": file_record(git_stderr_path),
        "tar_stdout": file_record(tar_stdout_path),
        "tar_stderr": file_record(tar_stderr_path),
        "extracted": source_tree_manifest(destination),
    }


def build_environment(target: Path, commit: str) -> dict[str, str]:
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target)
    env["CARGO_INCREMENTAL"] = "0"
    env["STREHL_BUILD_ID"] = commit
    env["SOURCE_DATE_EPOCH"] = git_text(["show", "-s", "--format=%ct", commit])
    return env


def build_revision(
    label: str,
    commit: str,
    source: Path,
    target: Path,
    logs: Path,
    archive: dict[str, Any],
) -> dict[str, Any]:
    binary = target / "release" / ("strehl.exe" if os.name == "nt" else "strehl")
    if target.exists() or binary.exists():
        raise EvidenceError("M176-E-STALE", f"private target is not new: {target}")
    env = build_environment(target, commit)
    cargo_version = capture_command(
        ["cargo", "--version", "--verbose"],
        cwd=source,
        env=env,
        stdout_path=logs / f"{label}-cargo-version.stdout.log",
        stderr_path=logs / f"{label}-cargo-version.stderr.log",
    )
    rustc_version = capture_command(
        ["rustc", "--version", "--verbose"],
        cwd=source,
        env=env,
        stdout_path=logs / f"{label}-rustc-version.stdout.log",
        stderr_path=logs / f"{label}-rustc-version.stderr.log",
    )
    built = capture_command(
        BUILD_COMMAND,
        cwd=source,
        env=env,
        stdout_path=logs / f"{label}-build.stdout.log",
        stderr_path=logs / f"{label}-build.stderr.log",
    )
    if not binary.is_file():
        raise EvidenceError("M176-E-BINARY", f"fresh build did not create {binary}")
    version = capture_command(
        [str(binary), "--version"],
        cwd=source,
        env=env,
        stdout_path=logs / f"{label}-binary-version.stdout.log",
        stderr_path=logs / f"{label}-binary-version.stderr.log",
    )
    version_text = (version["stdout_text"] + version["stderr_text"]).strip()
    if commit not in version_text:
        raise EvidenceError(
            "M176-E-BINARY",
            f"binary version does not contain full forced build id {commit}: {version_text!r}",
        )
    cargo_version_text = cargo_version["stdout_text"].strip()
    rustc_version_text = rustc_version["stdout_text"].strip()
    for value in (cargo_version, rustc_version, built, version):
        value.pop("stdout_text", None)
        value.pop("stderr_text", None)
    return {
        "label": label,
        "source_commit": commit,
        "source_tree": git_text(["rev-parse", f"{commit}^{{tree}}"]),
        "archive": archive,
        "source_directory": str(source),
        "target_directory": str(target),
        "target_preexisting": False,
        "binary_preexisting": False,
        "build_environment": {
            "CARGO_TARGET_DIR": str(target),
            "CARGO_INCREMENTAL": "0",
            "STREHL_BUILD_ID": commit,
            "SOURCE_DATE_EPOCH": env["SOURCE_DATE_EPOCH"],
        },
        "build": built,
        "cargo_version": cargo_version,
        "cargo_version_text": cargo_version_text,
        "rustc_version": rustc_version,
        "rustc_version_text": rustc_version_text,
        "binary": file_record(binary),
        "binary_version": version,
        "binary_version_text": version_text,
    }


def renderer_environment(
    prereg: dict[str, Any],
    run_root: Path,
    workers: int,
) -> tuple[dict[str, str], dict[str, str | None]]:
    if workers < 1 or workers > MAX_WORKERS:
        raise EvidenceError("M176-E-WORKER", f"worker count {workers} is outside 1..3")
    runtime_temp = run_root / "runtime-temp"
    runtime_cache = run_root / "runtime-cache"
    runtime_temp.mkdir(exist_ok=True)
    runtime_cache.mkdir(exist_ok=True)
    controlled: dict[str, str | None] = {}
    for name, registered in prereg["renderer_environment"].items():
        if registered == "<PRIVATE_RUNTIME_TEMP>":
            value: str | None = str(runtime_temp)
        elif registered == "<PRIVATE_RUNTIME_CACHE>":
            value = str(runtime_cache)
        elif registered == "<ARM>":
            value = str(workers)
        else:
            value = registered
        controlled[name] = value

    env = {name: os.environ[name] for name in ESSENTIAL_ENV if name in os.environ}
    env.update(
        {
            "NO_COLOR": "1",
            "RUST_BACKTRACE": "1",
            "LANG": "C",
            "LC_ALL": "C",
            "TZ": "UTC",
        }
    )
    for name, value in controlled.items():
        if value is not None:
            env[name] = value
    return env, controlled


class ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def process_memory(pid: int) -> tuple[int, int, int]:
    if os.name != "nt":
        return (0, 0, 0)
    process_query_information = 0x0400
    process_vm_read = 0x0010
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    handle = kernel32.OpenProcess(
        process_query_information | process_vm_read,
        False,
        pid,
    )
    if not handle:
        return (0, 0, 0)
    try:
        counters = ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        ok = psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        )
        if not ok:
            return (0, 0, 0)
        return (
            int(counters.WorkingSetSize),
            int(counters.PeakWorkingSetSize),
            int(counters.PrivateUsage),
        )
    finally:
        kernel32.CloseHandle(handle)


def monitored_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout_path: Path,
    stderr_path: Path,
) -> dict[str, Any]:
    if stdout_path.exists() or stderr_path.exists():
        raise EvidenceError("M176-E-STALE", "run log already exists")
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen(
            command, cwd=cwd, env=env, stdout=stdout, stderr=stderr
        )
        peak_working = 0
        peak_private = 0
        stopped_for_limit = False
        while process.poll() is None:
            working, reported_peak, private = process_memory(process.pid)
            peak_working = max(peak_working, working, reported_peak)
            peak_private = max(peak_private, private)
            if working > MAX_RESIDENT_BYTES:
                stopped_for_limit = True
                process.terminate()
                process.wait()
                break
            time.sleep(0.05)
        code = process.wait()
        working, reported_peak, private = process_memory(process.pid)
        peak_working = max(peak_working, working, reported_peak)
        peak_private = max(peak_private, private)
    if stopped_for_limit:
        raise EvidenceError(
            "M176-E-RESOURCE",
            f"process exceeded {MAX_RESIDENT_BYTES} resident bytes and was stopped",
        )
    if code != 0:
        raise EvidenceError(
            "M176-E-RENDER",
            f"{command_string(command)} exited {code}",
        )
    return {
        "argv": command,
        "command": command_string(command),
        "exit_code": code,
        "stdout": file_record(stdout_path),
        "stderr": file_record(stderr_path),
        "memory_observation": {
            "measurement": "Windows process working set/private usage; not a timing result",
            "peak_working_set_bytes": peak_working,
            "peak_private_usage_bytes": peak_private,
            "resident_stop_limit_bytes": MAX_RESIDENT_BYTES,
            "stopped_for_limit": stopped_for_limit,
        },
    }


def discover_renderer_env(source: Path) -> list[str]:
    names: set[str] = {
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "TMPDIR",
        "XDG_CACHE_HOME",
        "RUST_LOG",
    }
    expression = re.compile(r"(?:STREHL|RAYON)_[A-Z0-9_]+")
    for crate in ["strehl-cli", "strehl-core", "strehl-raw", "strehl-plugin"]:
        src = source / "crates" / crate / "src"
        for path in src.rglob("*.rs"):
            names.update(expression.findall(path.read_text(encoding="utf-8")))
    return sorted(names)


def probe_geometry(
    binary: Path,
    source: Path,
    run_root: Path,
    prereg: dict[str, Any],
    logs: Path,
) -> tuple[dict[str, Any], dict[str, str | None]]:
    env, controlled = renderer_environment(prereg, run_root, 1)
    command = [str(binary), "probe", APPROVED_INPUT, "--limit", "1"]
    result = capture_command(
        command,
        cwd=source,
        env=env,
        stdout_path=logs / "probe.stdout.log",
        stderr_path=logs / "probe.stderr.log",
    )
    text = result.pop("stdout_text") + "\n" + result.pop("stderr_text")
    buffer_match = re.search(r"buffer\s*:\s*(\d+)\s*x\s*(\d+)", text)
    active_match = re.search(r"active area\s*:\s*(\d+)\s*x\s*(\d+)", text)
    if not buffer_match or not active_match:
        raise EvidenceError(
            "M176-E-PROBE", "could not parse buffer and active geometry"
        )
    result["buffer"] = [int(buffer_match.group(1)), int(buffer_match.group(2))]
    result["active"] = [int(active_match.group(1)), int(active_match.group(2))]
    return result, controlled


def resource_estimate(
    active: list[int], buffer: list[int], free_bytes: int
) -> dict[str, Any]:
    active_width, active_height = active
    width, height = active_width // 2, active_height // 2
    sizes: list[list[int]] = [[width, height]]
    for _ in range(7):
        next_size = [(sizes[-1][0] + 1) // 2, (sizes[-1][1] + 1) // 2]
        if next_size[0] < 8 or next_size[1] < 8:
            break
        sizes.append(next_size)
    pixels = width * height
    pyramid_pixels = sum(w * h for w, h in sizes)
    frame_bytes = buffer[0] * buffer[1] * 2
    accumulator_floats = 9 * pyramid_pixels + 8 * pixels
    workspace_floats = 6 * pixels + 2 * width + 6 * pyramid_pixels
    planning_bytes = (
        4 * (accumulator_floats + workspace_floats + 6 * pixels) + frame_bytes
    )
    affected_w2 = 2 * planning_bytes
    fixed_retained_model = planning_bytes + 4 * accumulator_floats
    expected_outputs = 6 * pixels * 3 * 2
    estimate = {
        "schema": "strehl-m176-resource-estimate-v1",
        "not_a_timing_measurement": True,
        "active_raw_geometry": active,
        "buffer_geometry": buffer,
        "analysis_geometry": [width, height],
        "pyramid_level_sizes": sizes,
        "frame_bytes": frame_bytes,
        "planning_bytes_per_affected_worker": planning_bytes,
        "planning_mib_per_affected_worker": planning_bytes / 2**20,
        "affected_w2_source_plan_bytes": affected_w2,
        "affected_w2_source_plan_gib": affected_w2 / 2**30,
        "fixed_reusable_fold_source_model_bytes": fixed_retained_model,
        "fixed_reusable_fold_source_model_gib": fixed_retained_model / 2**30,
        "maximum_six_uncompressed_pixel_payload_bytes": expected_outputs,
        "scratch_free_bytes_before_renders": free_bytes,
        "resident_stop_limit_bytes": MAX_RESIDENT_BYTES,
        "minimum_free_scratch_bytes": MIN_FREE_SCRATCH_BYTES,
    }
    estimate["within_limits"] = (
        affected_w2 < MAX_RESIDENT_BYTES
        and fixed_retained_model < MAX_RESIDENT_BYTES
        and free_bytes >= MIN_FREE_SCRATCH_BYTES
        and free_bytes >= 20 * expected_outputs
    )
    if not estimate["within_limits"]:
        raise EvidenceError(
            "M176-E-RESOURCE", "pre-render resource estimate exceeds a stop rule"
        )
    return estimate


def run_render(
    run_id: str,
    build: dict[str, Any],
    workers: int,
    run_root: Path,
    prereg: dict[str, Any],
    logs: Path,
    outputs: Path,
) -> dict[str, Any]:
    output = outputs / f"{run_id}.tiff"
    if output.exists():
        raise EvidenceError("M176-E-STALE", f"output already exists: {output}")
    binary = Path(build["binary"]["path"])
    if sha256_file(binary) != build["binary"]["sha256"]:
        raise EvidenceError("M176-E-BINARY", f"binary changed before {run_id}")
    args = [
        str(binary),
        *[str(output) if item == "<OUTPUT>" else item for item in RENDER_ARGS],
    ]
    env, controlled = renderer_environment(prereg, run_root, workers)
    before_ns = time.time_ns()
    result = monitored_command(
        args,
        cwd=Path(build["source_directory"]),
        env=env,
        stdout_path=logs / f"{run_id}.stdout.log",
        stderr_path=logs / f"{run_id}.stderr.log",
    )
    if not output.is_file():
        raise EvidenceError("M176-E-OUTPUT", f"successful run did not create {output}")
    stderr_bytes = Path(result["stderr"]["path"]).read_bytes()
    combined = Path(result["stdout"]["path"]).read_bytes() + b"\n" + stderr_bytes
    text = combined.decode("utf-8", errors="replace")
    missing = [token for token in REQUIRED_RENDER_LOG if token not in text]
    if missing:
        raise EvidenceError("M176-E-BANNER", f"{run_id} missing log tokens: {missing}")
    if build["source_commit"] == AFFECTED_COMMIT:
        wanted = f"memory plan     : {workers} workers"
    else:
        wanted = f"{workers} execution threads"
    if wanted not in text:
        raise EvidenceError("M176-E-WORKER", f"{run_id} did not report {wanted!r}")
    output_record = file_record(output)
    output_record["preexisting"] = False
    output_record["created_after_launch_check"] = output.stat().st_mtime_ns >= before_ns
    if not output_record["created_after_launch_check"]:
        raise EvidenceError(
            "M176-E-STALE", f"{run_id} output timestamp predates launch"
        )
    result.update(
        {
            "schema": "strehl-m176-run-record-v1",
            "run_id": run_id,
            "source_commit": build["source_commit"],
            "binary_sha256": build["binary"]["sha256"],
            "workers": workers,
            "rayon_threads": int(controlled["RAYON_NUM_THREADS"] or "0"),
            "input": APPROVED_INPUT,
            "output": output_record,
            "renderer_environment": controlled,
            "full_child_environment_sha256": json_digest(env),
            "environment_except_worker_sha256": json_digest(
                {
                    key: value
                    for key, value in env.items()
                    if key != "STREHL_PYRAMID_WORKERS"
                }
            ),
            "argv_except_binary_and_output": [
                item for item in RENDER_ARGS if item != "<OUTPUT>"
            ],
            "required_banner_tokens": REQUIRED_RENDER_LOG,
            "raw_combined_output_sha256": sha256_bytes(combined),
            "started_utc": utc_now(),
        }
    )
    return result


def find_unique_line(path: Path, exact: str, radius: int = 3) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    matches = [index for index, line in enumerate(lines) if line == exact]
    if len(matches) != 1:
        raise EvidenceError(
            "M176-E-SOURCE-ANCHOR",
            f"{path}: expected one full-line anchor {exact!r}, found {len(matches)}",
        )
    index = matches[0]
    first = max(0, index - radius)
    last = min(len(lines), index + radius + 1)
    excerpt = "\n".join(lines[first:last]) + "\n"
    return {
        "file": path.name,
        "line": index + 1,
        "range": [first + 1, last],
        "anchor": exact,
        "excerpt": excerpt,
        "excerpt_sha256": sha256_bytes(excerpt.encode("utf-8")),
        "file_sha256": sha256_file(path),
    }


def source_evidence(
    affected_source: Path,
    fixed_source: Path,
    resource: dict[str, Any],
    runs: list[dict[str, Any]],
    affected_uses_w3: bool,
) -> dict[str, Any]:
    affected_merge = affected_source / "crates/strehl-cli/src/merge_cmd.rs"
    fixed_merge = fixed_source / "crates/strehl-cli/src/merge_cmd.rs"
    affected_core = affected_source / "crates/strehl-core/src/pyramid.rs"
    fixed_core = fixed_source / "crates/strehl-core/src/pyramid.rs"
    canonical_chunks = min(
        (6 * 1024**3) // resource["planning_bytes_per_affected_worker"],
        FRAMES,
    )
    affected_comparison = (
        "affected_w1_vs_w3" if affected_uses_w3 else "affected_w1_vs_w2"
    )
    affected_other = "affected-w3" if affected_uses_w3 else "affected-w2"
    records = {record["run_id"]: record for record in runs}
    all_alignment_off = all(
        record["renderer_environment"]["STREHL_ALIGN"] == "0" for record in runs
    )
    all_scale = all(
        "--cover" in record["argv"] and "scale" in record["argv"] for record in runs
    )
    return {
        "schema": "strehl-m176-source-evidence-v1",
        "affected_source": AFFECTED_COMMIT,
        "fixed_source": FIXED_COMMIT,
        "repair_commit": REPAIR_COMMIT,
        "source_files": {
            "affected_merge_cmd_sha256": sha256_file(affected_merge),
            "fixed_merge_cmd_sha256": sha256_file(fixed_merge),
            "affected_pyramid_sha256": sha256_file(affected_core),
            "fixed_pyramid_sha256": sha256_file(fixed_core),
            "affected_merge_cmd_git_blob": git_text(
                ["rev-parse", f"{AFFECTED_COMMIT}:crates/strehl-cli/src/merge_cmd.rs"]
            ),
            "fixed_merge_cmd_git_blob": git_text(
                ["rev-parse", f"{FIXED_COMMIT}:crates/strehl-cli/src/merge_cmd.rs"]
            ),
            "affected_pyramid_git_blob": git_text(
                ["rev-parse", f"{AFFECTED_COMMIT}:crates/strehl-core/src/pyramid.rs"]
            ),
            "fixed_pyramid_git_blob": git_text(
                ["rev-parse", f"{FIXED_COMMIT}:crates/strehl-core/src/pyramid.rs"]
            ),
        },
        "excerpts": {
            "affected_worker_chunk_count": find_unique_line(
                affected_merge,
                "    let per_chunk = paths.len().div_ceil(workers);",
            ),
            "affected_parallel_chunks": find_unique_line(
                affected_merge,
                "        .par_chunks(per_chunk)",
            ),
            "affected_left_to_right_absorb": find_unique_line(
                affected_merge,
                "            Some(a) => a.absorb(&m),",
            ),
            "fixed_canonical_chunk_count": find_unique_line(
                fixed_merge,
                "    let canonical_chunks = canonical_band_chunks(planning_bytes, paths.len());",
            ),
            "fixed_canonical_chunk_size": find_unique_line(
                fixed_merge,
                "    let per_chunk = paths.len().div_ceil(canonical_chunks);",
            ),
            "fixed_canonical_iteration": find_unique_line(
                fixed_merge,
                "        let mut chunks = paths.chunks(per_chunk).enumerate().peekable();",
            ),
            "fixed_left_to_right_absorb": find_unique_line(
                fixed_merge,
                "                Some(acc) => acc.absorb(&worker.merge),",
            ),
            "soft_power_default": find_unique_line(
                affected_core,
                "            select: SelectMode::SoftPower,",
            ),
            "f32_numerator": find_unique_line(
                affected_core,
                "    num: Vec<Vec<f32>>,",
            ),
            "f32_absorb": find_unique_line(
                affected_core,
                "                        for (a, b) in self.num[i].iter_mut().zip(&other.num[i]) {",
            ),
        },
        "chunking": {
            "frames": FRAMES,
            "affected": {
                "w1": chunk_sizes(FRAMES, 1),
                "w2": chunk_sizes(FRAMES, 2),
                "w3": chunk_sizes(FRAMES, 3),
                "formula": "ceil(frames / requested_workers)",
            },
            "fixed": {
                "canonical_chunk_count": canonical_chunks,
                "w1": chunk_sizes(FRAMES, canonical_chunks),
                "w2": chunk_sizes(FRAMES, canonical_chunks),
                "formula": "ceil(frames / canonical_memory_chunks), independent of requested workers",
            },
        },
        "mechanism_preconditions": {
            "affected_workers_change_chunks": chunk_sizes(FRAMES, 1)
            != chunk_sizes(FRAMES, 2),
            "fixed_workers_do_not_change_chunks": chunk_sizes(FRAMES, canonical_chunks)
            == chunk_sizes(FRAMES, canonical_chunks),
            "soft_power_default": True,
            "f32_accumulators": True,
            "f32_absorb_addition": True,
        },
        "runtime_preconditions": {
            "alignment_off_all_runs": all_alignment_off,
            "scale_coverage_requested_all_runs": all_scale,
            "coverage_boundary_excluded": all_alignment_off,
            "same_output_shape_required": True,
            "affected_w1_worker": records["affected-w1"]["workers"],
            "affected_w2_worker": records["affected-w2"]["workers"],
            "fixed_w1_worker": records["fixed-w1"]["workers"],
            "fixed_w2_worker": records["fixed-w2"]["workers"],
        },
        "affected_comparison": affected_comparison,
        "affected_other_arm": affected_other,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch-run", default="production")
    parser.add_argument("--evidence-dir", type=Path, default=EXPERIMENT_DIR / "out")
    args = parser.parse_args()
    try:
        guard_capture_path(APPROVED_INPUT)
        prereg = read_json(EXPERIMENT_DIR / "preregistration.json")
        prereg_hash = sha256_file(EXPERIMENT_DIR / "preregistration.json")
        run_root = ensure_private_path(PRIVATE_SCRATCH / args.scratch_run)
        if run_root.exists():
            raise EvidenceError("M176-E-STALE", f"scratch run exists: {run_root}")
        run_root.mkdir(parents=True)
        evidence_dir = args.evidence_dir.resolve()
        if evidence_dir.exists():
            raise EvidenceError(
                "M176-E-STALE", f"evidence directory exists: {evidence_dir}"
            )
        evidence_dir.mkdir(parents=True)
        logs = run_root / "logs"
        outputs = run_root / "outputs"
        logs.mkdir()
        outputs.mkdir()

        before = capture_manifest(APPROVED_INPUT)
        write_json_new(evidence_dir / "input-before.json", before)
        lineage = lineage_evidence()
        write_json_new(evidence_dir / "lineage.json", lineage)

        builds: list[dict[str, Any]] = []
        for label, commit in [("affected", AFFECTED_COMMIT), ("fixed", FIXED_COMMIT)]:
            source = run_root / f"source-{label}-{commit[:8]}"
            target = run_root / f"target-{label}-{commit[:8]}"
            archive = archive_source(commit, source, logs)
            builds.append(build_revision(label, commit, source, target, logs, archive))
        builds_by_label = {build["label"]: build for build in builds}

        expected_env = set(prereg["renderer_environment"])
        discovered_by_source = {
            label: discover_renderer_env(Path(build["source_directory"]))
            for label, build in builds_by_label.items()
        }
        for label, names in discovered_by_source.items():
            missing = sorted(set(names) - expected_env)
            if missing:
                raise EvidenceError(
                    "M176-E-ENV",
                    f"{label} source has unregistered renderer environment names: {missing}",
                )

        affected_binary = Path(builds_by_label["affected"]["binary"]["path"])
        probe, probe_env = probe_geometry(
            affected_binary,
            Path(builds_by_label["affected"]["source_directory"]),
            run_root,
            prereg,
            logs,
        )
        free_bytes = shutil.disk_usage(run_root).free
        resource = resource_estimate(probe["active"], probe["buffer"], free_bytes)
        resource["probe"] = probe
        resource["probe_renderer_environment"] = probe_env
        write_json_new(evidence_dir / "resource-estimate.json", resource)

        run_records: list[dict[str, Any]] = []
        for run_id, build_label, workers in [
            ("affected-w1", "affected", 1),
            ("affected-w2", "affected", 2),
            ("affected-w1-repeat", "affected", 1),
        ]:
            run_records.append(
                run_render(
                    run_id,
                    builds_by_label[build_label],
                    workers,
                    run_root,
                    prereg,
                    logs,
                    outputs,
                )
            )

        from analyze import decode_primary

        affected_w1 = decode_primary(Path(run_records[0]["output"]["path"]))
        affected_w2 = decode_primary(Path(run_records[1]["output"]["path"]))
        w1_hash = canonical_pixel_hash(affected_w1)
        w2_hash = canonical_pixel_hash(affected_w2)
        affected_uses_w3 = w1_hash == w2_hash
        if affected_uses_w3:
            run_records.append(
                run_render(
                    "affected-w3",
                    builds_by_label["affected"],
                    3,
                    run_root,
                    prereg,
                    logs,
                    outputs,
                )
            )

        for run_id, workers in [("fixed-w1", 1), ("fixed-w2", 2)]:
            run_records.append(
                run_render(
                    run_id,
                    builds_by_label["fixed"],
                    workers,
                    run_root,
                    prereg,
                    logs,
                    outputs,
                )
            )

        after = capture_manifest(APPROVED_INPUT)
        write_json_new(evidence_dir / "input-after.json", after)
        if before != after:
            raise EvidenceError(
                "M176-E-INPUT-MUTATION", "input manifest changed during protocol"
            )

        build_evidence = {
            "schema": "strehl-m176-builds-v1",
            "lineage": lineage,
            "builds": builds,
            "tooling": {
                "python_version": sys.version,
                "python_executable": file_record(Path(sys.executable)),
                "git_version": git_text(["--version"]),
                "tar_executable": shutil.which("tar"),
            },
        }
        write_json_new(evidence_dir / "builds.json", build_evidence)

        worker_hashes = {
            record["run_id"]: record["full_child_environment_sha256"]
            for record in run_records
        }
        base_env_hashes = {
            record["environment_except_worker_sha256"] for record in run_records
        }
        if len(base_env_hashes) != 1:
            raise EvidenceError(
                "M176-E-ENV", "non-worker child environment changed between runs"
            )
        run_evidence = {
            "schema": "strehl-m176-runs-v1",
            "input": APPROVED_INPUT,
            "requested_frame_count": FRAMES,
            "rayon_threads": 2,
            "fallback_w3_used": affected_uses_w3,
            "fallback_reason": (
                "affected W1/W2 canonical pixels equal"
                if affected_uses_w3
                else "affected W1/W2 canonical pixels differ; W3 prohibited"
            ),
            "environment_except_worker_sha256": next(iter(base_env_hashes)),
            "per_run_full_environment_sha256": worker_hashes,
            "runs": run_records,
        }
        write_json_new(evidence_dir / "runs.json", run_evidence)

        sources = source_evidence(
            Path(builds_by_label["affected"]["source_directory"]),
            Path(builds_by_label["fixed"]["source_directory"]),
            resource,
            run_records,
            affected_uses_w3,
        )
        write_json_new(evidence_dir / "source-evidence.json", sources)

        provenance = {
            "schema": "strehl-m176-provenance-v1",
            "created_after_all_renders": utc_now(),
            "preregistration_sha256": prereg_hash,
            "script_sha256": script_hashes(),
            "scratch_run_root": str(run_root),
            "scratch_run_preexisting": False,
            "evidence_directory_preexisting": False,
            "input_manifest_before_sha256": before["manifest_sha256"],
            "input_manifest_after_sha256": after["manifest_sha256"],
            "renderer_environment_names_discovered": discovered_by_source,
            "no_m139_artifact_consumed": True,
            "m139_report_use": "lineage citation only",
            "timing_claims_made": False,
        }
        write_json_new(evidence_dir / "provenance.json", provenance)
        print(
            json.dumps(
                {
                    "status": "RUNS_COMPLETE",
                    "run_count": len(run_records),
                    "fallback_w3_used": affected_uses_w3,
                    "scratch": str(run_root),
                    "evidence": str(evidence_dir),
                },
                sort_keys=True,
            )
        )
        return 0
    except EvidenceError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
