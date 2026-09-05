#!/usr/bin/env python3
"""Run the uninterrupted M192 M12 certification campaign."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Callable

import tifffile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROTOCOL_PATH = HERE / "protocol.json"
VERIFY_PATH = HERE / "verify.py"
WORK = HERE / "work"
RESULTS = HERE / "results"
FLAGS = [
    "--merge",
    "pyramid",
    "--pyramid-gate",
    "2.0",
    "--resampler",
    "catmull-rom",
    "--cover",
    "scale",
    "--linear-srgb",
    "--demosaic",
]
BAR_BYTES = 6 << 30
CPU_INTERVAL_SECONDS = 1.0
CPU_INTERVAL_TOLERANCE_SECONDS = 0.25


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.new")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def run_capture(
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
        with log.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write("$ " + subprocess.list2cmdline(command) + "\n\n")
            stream.write(result.stdout)
            if result.stdout and not result.stdout.endswith("\n"):
                stream.write("\n")
    return result


def git_bytes(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise RuntimeError(
            f"git {' '.join(arguments)} failed: "
            f"{result.stderr.decode('utf-8', 'replace')}"
        )
    return result.stdout


def git_text(*arguments: str) -> str:
    return git_bytes(*arguments).decode("utf-8").strip()


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def clean_process_environment(
    *,
    cache: Path,
    temp: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    prefixes = ("STREHL_", "RAYON_", "OMP_", "OPENBLAS_", "MKL_", "NUMEXPR_")
    for key in list(env):
        if key.startswith(prefixes):
            env.pop(key, None)
    env["STREHL_CACHE_DIR"] = str(cache.resolve())
    env["TEMP"] = str(temp.resolve())
    env["TMP"] = str(temp.resolve())
    return env


def verify_frozen_sources(spec: dict[str, Any]) -> dict[str, Any]:
    measured = spec["lineage"]["measured_commit"]
    require(git_text("rev-parse", measured) == measured, "measured commit is not exact")
    require(
        git_text("show", "-s", "--format=%T", measured)
        == spec["lineage"]["measured_tree"],
        "measured tree hash drifted",
    )
    ancestry: dict[str, bool] = {}
    for ancestor in spec["lineage"]["required_ancestry"]:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", ancestor, measured]
        )
        ancestry[ancestor] = result.returncode == 0
        require(ancestry[ancestor], f"{ancestor} is not an ancestor of {measured}")
    diff = git_bytes(
        "diff",
        "--binary",
        spec["lineage"]["bounded_memory_repair_commit"],
        measured,
        "--",
        *spec["lineage"]["repair_owned_paths"],
    )
    require(diff == b"", "repair-owned source changed after the bounded repair")
    source_status = git_text(
        "status",
        "--short",
        "--",
        "Cargo.toml",
        "Cargo.lock",
        "crates/strehl-cli",
        "crates/strehl-core",
        "crates/strehl-raw",
    )
    inherited = spec["governing_sources"]["inherited_monitor"]
    monitor_path = ROOT / inherited["path"]
    checkout_hash = sha256_file(monitor_path)
    blob = git_bytes("show", f"{measured}:{inherited['path']}")
    require(
        checkout_hash == inherited["checkout_sha256_crlf"],
        "inherited monitor checkout bytes drifted",
    )
    require(
        sha256_bytes(blob) == inherited["git_blob_sha256_lf"],
        "inherited monitor Git blob bytes drifted",
    )
    require(
        git_text("rev-parse", f"{measured}:{inherited['path']}")
        == inherited["git_blob_oid_lf"],
        "inherited monitor blob OID drifted",
    )
    return {
        "measured_commit": measured,
        "measured_tree": spec["lineage"]["measured_tree"],
        "ancestry": ancestry,
        "repair_owned_diff_bytes": len(diff),
        "working_tree_crate_status_ignored_because_build_uses_git_archive": source_status,
        "monitor": {
            "path": inherited["path"],
            "checkout_sha256_crlf": checkout_hash,
            "git_blob_sha256_lf": sha256_bytes(blob),
            "git_blob_oid_lf": inherited["git_blob_oid_lf"],
        },
    }


def archive_build(
    *,
    label: str,
    commit: str,
    jobs: int,
) -> dict[str, Any]:
    root = WORK / "builds" / label
    archive = root / "source.tar"
    source = root / "source"
    target = root / "target"
    binary = root / "bin" / "strehl.exe"
    log = root / "build.log"
    if root.exists():
        shutil.rmtree(root)
    source.mkdir(parents=True)
    command = [
        "git",
        "-C",
        str(ROOT),
        "--no-pager",
        "archive",
        "--format=tar",
        f"--output={archive}",
        commit,
    ]
    archive_result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if archive_result.returncode:
        raise RuntimeError(
            f"git archive failed for {label}: "
            f"{archive_result.stderr.decode('utf-8', 'replace')}"
        )
    archive_sha = sha256_file(archive)
    archive_bytes = archive.stat().st_size
    with tarfile.open(archive, "r") as bundle:
        bundle.extractall(source, filter="data")
    require((source / "Cargo.toml").is_file(), f"{label}: Cargo.toml absent")
    require((source / "Cargo.lock").is_file(), f"{label}: Cargo.lock absent")
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(target.resolve())
    env["CARGO_INCREMENTAL"] = "0"
    env["CARGO_BUILD_JOBS"] = str(jobs)
    env["CARGO_TERM_COLOR"] = "never"
    env["STREHL_BUILD_ID"] = commit
    build_command = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--jobs",
        str(jobs),
        "--package",
        "strehl-cli",
        "--manifest-path",
        str(source / "Cargo.toml"),
    ]
    print(f"[build] {label} {commit[:12]}", flush=True)
    result = run_capture(build_command, cwd=source, env=env, log=log)
    if result.returncode:
        raise RuntimeError(
            f"{label} build failed with {result.returncode}: "
            f"{result.stdout[-6000:]}"
        )
    require("Compiling strehl-cli" in result.stdout, f"{label}: no compile proof")
    target_binary = target / "release" / "strehl.exe"
    require(target_binary.is_file(), f"{label}: output executable absent")
    binary.parent.mkdir(parents=True)
    shutil.copy2(target_binary, binary)
    require(sha256_file(binary) == sha256_file(target_binary), f"{label}: copy drifted")
    version = subprocess.run(
        [str(binary), "--version"],
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    require(version.returncode == 0, f"{label}: --version failed")
    require(commit in version.stdout, f"{label}: --version lacks full commit")
    tree = git_text("show", "-s", "--format=%T", commit)
    return {
        "label": label,
        "commit": commit,
        "tree": tree,
        "archive_sha256": archive_sha,
        "archive_bytes": archive_bytes,
        "binary_path": str(binary.resolve()),
        "binary_bytes": binary.stat().st_size,
        "binary_sha256": sha256_file(binary),
        "version_output": version.stdout.strip(),
        "build_command": build_command,
        "build_environment": {
            "CARGO_TARGET_DIR": env["CARGO_TARGET_DIR"],
            "CARGO_INCREMENTAL": env["CARGO_INCREMENTAL"],
            "CARGO_BUILD_JOBS": env["CARGO_BUILD_JOBS"],
            "STREHL_BUILD_ID": env["STREHL_BUILD_ID"],
        },
        "build_log_source": str(log.resolve()),
        "build_log_sha256": sha256_file(log),
        "rustc_version": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "cargo_version": subprocess.check_output(["cargo", "--version"], text=True).strip(),
        "completed_utc": utc_now(),
    }


def selected_arws(path: Path, count: int) -> list[Path]:
    files = sorted(path.glob("*.ARW"), key=lambda item: item.name.casefold())
    require(len(files) >= count, f"{path}: only {len(files)} ARWs for N={count}")
    return files[:count]


def input_manifest(spec: dict[str, Any], phase: str) -> dict[str, Any]:
    selected: dict[str, Path] = {}
    for raw_count, raw_path in spec["inputs"].items():
        if not str(raw_count).isdigit():
            continue
        count = int(raw_count)
        capture = Path(raw_path)
        require(capture.is_dir(), f"input directory absent: {capture}")
        for path in selected_arws(capture, count):
            selected[str(path.resolve()).casefold()] = path.resolve()
    rows = []
    started = utc_now()
    for index, path in enumerate(sorted(selected.values(), key=lambda item: str(item).casefold()), 1):
        stat = path.stat()
        rows.append(
            {
                "path": str(path),
                "bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
                "sha256": sha256_file(path),
            }
        )
        if index % 50 == 0:
            print(f"[inputs:{phase}] hashed {index}/{len(selected)}", flush=True)
    require(len(rows) == 404, f"expected 404 unique selected ARWs, found {len(rows)}")
    return {
        "schema": "m192-input-manifest-v1",
        "phase": phase,
        "started_utc": started,
        "completed_utc": utc_now(),
        "selected_file_count": len(rows),
        "selected_bytes": sum(row["bytes"] for row in rows),
        "files": rows,
    }


def prepare_sidecars(
    spec: dict[str, Any],
    measured_binary: Path,
) -> tuple[dict[int, Path], dict[str, Any]]:
    destination_root = WORK / "sidecars"
    destination_root.mkdir(parents=True)
    sidecars: dict[int, Path] = {}
    records = []
    for count in (33, 105, 299, 96, 97, 98, 99):
        source = ROOT / spec["sidecars"][str(count)]["path"]
        require(source.is_file(), f"sidecar source absent: {source}")
        require(
            sha256_file(source) == spec["sidecars"][str(count)]["sha256"],
            f"sidecar source hash drifted for N={count}",
        )
        destination = destination_root / f"n{count}.warpmap.txt"
        shutil.copy2(source, destination)
        text = destination.read_text(encoding="utf-8")
        require(f"frames {count}" in text, f"sidecar N={count} frame count absent")
        require("resampler catmull-rom" in text, f"sidecar N={count} wrong resampler")
        sidecars[count] = destination
        records.append(
            {
                "n": count,
                "source_path": spec["sidecars"][str(count)]["path"],
                "artifact_path": f"sidecars/n{count}.warpmap.txt",
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "header_frames": count,
                "header_resampler": "catmull-rom",
                "measured_executable_validation": (
                    "Every registered stack invocation must print alignment ON "
                    f"(sidecar), {count} placed / 0 refused; the terminal witness "
                    "fails closed otherwise."
                ),
            }
        )
    return sidecars, {
        "schema": "m192-sidecars-v1",
        "source": spec["sidecars"]["source"],
        "sidecars": records,
    }


class HostCpuSampler:
    def __init__(
        self,
        system_times: Callable[[], dict[str, int]],
        interval_seconds: float = CPU_INTERVAL_SECONDS,
    ) -> None:
        self.system_times = system_times
        self.interval = interval_seconds
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.started = 0.0
        self.previous: dict[str, int] | None = None
        self.start_times: dict[str, int] | None = None
        self.end_times: dict[str, int] | None = None
        self.error: str | None = None
        self.trace: list[dict[str, float]] = []

    def start(self) -> None:
        require(self.thread is None, "CPU sampler started twice")
        self.start_times = self.system_times()
        self.previous = self.start_times
        self.started = time.perf_counter()
        self.thread = threading.Thread(target=self._run, name="m192-host-cpu")
        self.thread.start()

    def _run(self) -> None:
        previous = self.previous
        if previous is None:
            self.error = "missing initial GetSystemTimes sample"
            return
        deadline = self.started + self.interval
        while True:
            delay = max(0.0, deadline - time.perf_counter())
            if self.stop_event.wait(delay):
                return
            sampled_at = time.perf_counter()
            try:
                current = self.system_times()
            except Exception as error:
                self.error = str(error)
                return
            total = current["total_100ns"] - previous["total_100ns"]
            busy = current["busy_100ns"] - previous["busy_100ns"]
            if total <= 0 or not 0 <= busy <= total:
                self.error = f"invalid GetSystemTimes delta total={total} busy={busy}"
                return
            self.trace.append(
                {
                    "elapsed_seconds": sampled_at - self.started,
                    "whole_host_cpu_percent": 100.0 * busy / total,
                }
            )
            previous = current
            deadline = sampled_at + self.interval

    def finish(self) -> dict[str, Any]:
        require(self.thread is not None, "CPU sampler was not started")
        self.stop_event.set()
        self.thread.join()
        self.end_times = self.system_times()
        elapsed = time.perf_counter() - self.started
        start = self.start_times
        end = self.end_times
        require(start is not None and end is not None, "CPU boundary samples absent")
        total = end["total_100ns"] - start["total_100ns"]
        busy = end["busy_100ns"] - start["busy_100ns"]
        exact_mean = 100.0 * busy / total if total > 0 else None
        values = [row["whole_host_cpu_percent"] for row in self.trace]
        trace_error = self.error
        previous = 0.0
        if trace_error is None and not values:
            trace_error = "no complete one-second CPU sample"
        if trace_error is None:
            for index, row in enumerate(self.trace):
                gap = row["elapsed_seconds"] - previous
                if not (
                    CPU_INTERVAL_SECONDS - CPU_INTERVAL_TOLERANCE_SECONDS
                    <= gap
                    <= CPU_INTERVAL_SECONDS + CPU_INTERVAL_TOLERANCE_SECONDS
                ):
                    trace_error = f"sample {index} gap {gap:.6f}s"
                    break
                previous = row["elapsed_seconds"]
        if (
            trace_error is None
            and elapsed - previous
            > CPU_INTERVAL_SECONDS + CPU_INTERVAL_TOLERANCE_SECONDS
        ):
            trace_error = f"uncovered tail {elapsed - previous:.6f}s"
        peak = max([float(exact_mean or 0.0), *values], default=float(exact_mean or 0.0))
        return {
            "elapsed_seconds": elapsed,
            "sample_interval_seconds": CPU_INTERVAL_SECONDS,
            "trace": self.trace,
            "trace_valid": trace_error is None,
            "trace_error": trace_error,
            "whole_host_cpu_mean_percent": exact_mean,
            "whole_host_cpu_trace_mean_percent": (
                sum(values) / len(values) if values else None
            ),
            "whole_host_cpu_peak_percent": peak,
        }


def terminal_witness(
    stderr_text: str,
    *,
    count: int,
    workers: int,
    destination: Path,
    repaired: bool,
) -> dict[str, Any]:
    checks = {
        "frames": re.search(rf"(?m)^frames\s+:\s+{count}\s+from\s+", stderr_text)
        is not None,
        "alignment": re.search(
            rf"(?m)^alignment\s+:\s+ON \(sidecar(?:-override)?\).*$", stderr_text
        )
        is not None
        and f"{count} placed / 0 refused" in stderr_text,
        "worker": (
            f"{workers} execution threads" in stderr_text
            if repaired
            else f"{workers} workers)" in stderr_text
        ),
        "repair_banner": (
            "STREHL_PYRAMID_WORKERS=N changes threads, never arithmetic."
            in stderr_text
            if repaired
            else True
        ),
        "folded_all": re.search(
            rf"(?m)^folded\s+:\s+{count}\s+/\s+{count}\s+frames", stderr_text
        )
        is not None,
        "wrote_exact_path": str(destination.resolve()) in stderr_text
        and re.search(r"(?m)^wrote\s+:", stderr_text) is not None,
        "total_terminal": re.search(r"(?m)^total\s+:\s+[0-9.]+\s+s\s*$", stderr_text)
        is not None,
    }
    return {**checks, "all": all(checks.values())}


def run_product(
    *,
    monitor: ModuleType,
    campaign_id: str,
    binary: Path,
    commit: str,
    run_id: str,
    phase: str,
    kind: str,
    count: int,
    workers: int,
    repetition: int | None,
    sweep: str,
    order_index: int,
    stack: Path,
    sidecar: Path,
    repaired: bool,
    retain_output: bool = False,
) -> tuple[dict[str, Any], Path | None]:
    output = WORK / "outputs" / f"{run_id}.tiff"
    cache = WORK / "cache" / phase / f"n{count}"
    temp = WORK / "temp" / run_id
    if output.exists():
        raise RuntimeError(f"refusing to overwrite {output}")
    required = [
        "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)",
        "noise gate      : 2.00 x",
        "not applied     : photometric gain, clip census, outlier rejection, halo correction, through-focus",
        "alignment       : ON (sidecar",
        "16-bit RGB, linear sRGB",
        "Full sensor resolution",
    ]
    record = monitor.run_once(
        exe=binary,
        stack=stack,
        limit=count,
        workers=workers,
        destination=output,
        cache=cache,
        temp=temp,
        flags=FLAGS,
        sidecar=sidecar,
        align_off=False,
        fixed_env={},
        required_log_substrings=required,
        kind=kind,
        repetition=repetition,
        sweep=sweep,
        measured_commit=commit,
        external_busy_max=1.0,
    )
    stdout_path = output.with_suffix(output.suffix + ".stdout.log")
    stderr_path = output.with_suffix(output.suffix + ".stderr.log")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    witness = terminal_witness(
        stderr_text,
        count=count,
        workers=workers,
        destination=output,
        repaired=repaired,
    )
    if not witness["all"]:
        record["valid"] = False
        record.setdefault("invalid_reasons", []).append(
            f"terminal witness failed: {witness}"
        )
    if record.get("software") and commit not in record["software"]:
        record["valid"] = False
        record.setdefault("invalid_reasons", []).append(
            "TIFF Software tag lacks full measured commit"
        )
    memory = record["memory"]
    scheduled = int(memory["sample_count"]) + int(memory["missed_intervals"])
    sampling_coverage = int(memory["sample_count"]) / scheduled if scheduled else 0.0
    host = record["host_load_during_run"]
    host_mean = (
        100.0
        * float(host["system_busy_cpu_seconds"])
        / float(host["system_total_cpu_seconds"])
        if float(host["system_total_cpu_seconds"]) > 0
        else None
    )
    record.update(
        {
            "schema": "m192-run-v1",
            "campaign_id": campaign_id,
            "run_id": run_id,
            "phase": phase,
            "kind": kind,
            "limit": count,
            "workers": workers,
            "repetition": repetition,
            "sweep": sweep,
            "order_index": order_index,
            "terminal_witness": witness,
            "sampling_coverage": sampling_coverage,
            "whole_host_cpu_mean_percent": host_mean,
            "log_artifacts": {
                "stdout": {
                    "path": f"logs/{stdout_path.name}",
                    "bytes": stdout_path.stat().st_size,
                    "sha256": sha256_file(stdout_path),
                },
                "stderr": {
                    "path": f"logs/{stderr_path.name}",
                    "bytes": stderr_path.stat().st_size,
                    "sha256": sha256_file(stderr_path),
                },
            },
        }
    )
    require(record["valid"], f"{run_id} invalid: {record['invalid_reasons']}")
    require(record["returncode"] == 0, f"{run_id} returned {record['returncode']}")
    require(output.is_file(), f"{run_id} output vanished before cleanup")
    if retain_output:
        record["artifact_cleanup"] = {"output_removed": False}
        return record, output
    output.unlink()
    require(not output.exists(), f"{run_id} output deletion failed")
    if temp.exists():
        shutil.rmtree(temp)
    record["artifact_cleanup"] = {"output_removed": True}
    return record, None


def canonical_record_hash(record: dict[str, Any]) -> str:
    value = {key: member for key, member in record.items() if key != "record_sha256"}
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return sha256_bytes(payload)


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.previous = "0" * 64
        self.count = 0
        path.parent.mkdir(parents=True, exist_ok=True)
        require(not path.exists(), f"refusing to resume journal {path}")

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        value = dict(record)
        value["sequence_index"] = self.count
        value["previous_record_sha256"] = self.previous
        value["record_sha256"] = canonical_record_hash(value)
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.previous = value["record_sha256"]
        self.count += 1
        return value


def run_memory_plant(monitor: ModuleType, measured_commit: str) -> dict[str, Any]:
    root = WORK / "commission" / "memory"
    root.mkdir(parents=True)
    child = root / "child.py"
    parent = root / "parent.py"
    child.write_text(
        "import sys,time\n"
        "size=int(sys.argv[1])\n"
        "hold=bytearray(size)\n"
        "for i in range(0,size,4096): hold[i]=1\n"
        "print(f'allocated={len(hold)}',flush=True)\n"
        "time.sleep(2.0)\n",
        encoding="utf-8",
        newline="\n",
    )
    parent.write_text(
        "import subprocess,sys\n"
        "raise SystemExit(subprocess.call([sys.executable,sys.argv[1],sys.argv[2]]))\n",
        encoding="utf-8",
        newline="\n",
    )

    def arm(name: str, amount: int) -> dict[str, Any]:
        temp = root / f"{name}-temp"
        temp.mkdir()
        env = clean_process_environment(cache=root / f"{name}-cache", temp=temp)
        return monitor.monitor_command(
            argv=[sys.executable, str(parent), str(child), str(amount)],
            env=env,
            stdout_path=root / f"{name}.stdout.log",
            stderr_path=root / f"{name}.stderr.log",
            temp=temp,
            measured_commit=measured_commit,
            external_busy_max=1.0,
        )

    null = arm("null-64mib", 64 << 20)
    plant = arm("plant-7gib", 7 << 30)
    null_peak = max(
        int(null["memory"]["peak_process_tree_private_committed_bytes"]),
        int(null["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]),
    )
    plant_peak = max(
        int(plant["memory"]["peak_process_tree_private_committed_bytes"]),
        int(plant["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]),
    )
    return {
        "null": null,
        "plant": plant,
        "null_green": (
            null["returncode"] == 0
            and null_peak < (1 << 30)
            and null["memory"]["peak_process_count"] >= 2
        ),
        "plant_red": (
            plant["returncode"] == 0
            and plant_peak > BAR_BYTES
            and plant["memory"]["peak_process_count"] >= 2
        ),
        "null_peak_bytes": null_peak,
        "plant_peak_bytes": plant_peak,
    }


def commission(
    *,
    monitor: ModuleType,
    campaign_id: str,
    spec: dict[str, Any],
    builds: dict[str, Any],
    sidecars: dict[int, Path],
) -> dict[str, Any]:
    measured_commit = spec["lineage"]["measured_commit"]
    pre_commit = spec["lineage"]["unrepaired_control_commit"]
    pre_binary = Path(builds["unrepaired"]["binary_path"])
    stack = Path(spec["inputs"]["33"])
    pre_records: dict[int, dict[str, Any]] = {}
    retained: Path | None = None
    for worker in (1, 2, 4):
        record, output = run_product(
            monitor=monitor,
            campaign_id=campaign_id,
            binary=pre_binary,
            commit=pre_commit,
            run_id=f"commission-pre-n33-w{worker}",
            phase="commission",
            kind="commission",
            count=33,
            workers=worker,
            repetition=None,
            sweep="commission",
            order_index=worker,
            stack=stack,
            sidecar=sidecars[33],
            repaired=False,
            retain_output=worker == 1,
        )
        pre_records[worker] = record
        if output is not None:
            retained = output
    require(retained is not None and retained.is_file(), "commission baseline absent")
    planted = retained.with_name(retained.stem + "-lsb-plant.tiff")
    shutil.copy2(retained, planted)
    baseline_witness = monitor.tiff_witness(retained)
    pixels = tifffile.memmap(planted, mode="r+")
    coordinate = tuple(size // 2 for size in pixels.shape)
    before = int(pixels[coordinate])
    pixels[coordinate] = before ^ 1
    pixels.flush()
    del pixels
    planted_witness = monitor.tiff_witness(planted)
    file_lsb_red = (
        baseline_witness["output_sha256"] != planted_witness["output_sha256"]
    )
    pixel_lsb_red = (
        baseline_witness["pixel_sha256"] != planted_witness["pixel_sha256"]
    )
    retained.unlink()
    planted.unlink()
    pre_records[1]["artifact_cleanup"] = {"output_removed": True}

    w1 = pre_records[1]
    w2 = pre_records[2]
    w4 = pre_records[4]
    worker_red = (
        w1["output_sha256"] != w2["output_sha256"]
        and w1["pixel_sha256"] != w2["pixel_sha256"]
    )
    w4_peak = max(
        int(w4["memory"]["peak_process_tree_private_committed_bytes"]),
        int(w4["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]),
    )
    memory_red = w4_peak > BAR_BYTES
    memory_plant = run_memory_plant(monitor, measured_commit)

    self_test_path = WORK / "commission" / "verifier-self-test.json"
    self_test_log = WORK / "commission" / "verifier-self-test.log"
    verify_result = run_capture(
        [
            sys.executable,
            str(VERIFY_PATH),
            "--self-test",
            "--output",
            str(self_test_path),
        ],
        log=self_test_log,
    )
    self_test = read_json(self_test_path)
    self_test_green = (
        verify_result.returncode == 0 and self_test.get("status") == "COMMISSIONED"
    )
    gates = {
        "unrepaired_worker_gate_red": worker_red,
        "unrepaired_memory_gate_red": memory_red,
        "memory_null_green": memory_plant["null_green"],
        "memory_plant_red": memory_plant["plant_red"],
        "file_lsb_red": file_lsb_red,
        "pixel_lsb_red": pixel_lsb_red,
        "verifier_self_test_green": self_test_green,
    }
    require(all(gates.values()), f"commissioning failed: {gates}")
    return {
        "schema": "m192-commission-v1",
        "status": "COMMISSIONED",
        "generated_utc": utc_now(),
        "gates": gates,
        "unrepaired": {
            "commit": pre_commit,
            "binary_sha256": builds["unrepaired"]["binary_sha256"],
            "n33_w1": pre_records[1],
            "n33_w2": pre_records[2],
            "n33_w4": pre_records[4],
            "w1_w2_file_hashes_differ": (
                w1["output_sha256"] != w2["output_sha256"]
            ),
            "w1_w2_pixel_hashes_differ": (
                w1["pixel_sha256"] != w2["pixel_sha256"]
            ),
            "n33_w4_conservative_peak_bytes": w4_peak,
        },
        "lsb_plant": {
            "coordinate": list(coordinate),
            "before": before,
            "after": before ^ 1,
            "baseline_file_sha256": baseline_witness["output_sha256"],
            "planted_file_sha256": planted_witness["output_sha256"],
            "baseline_pixel_sha256": baseline_witness["pixel_sha256"],
            "planted_pixel_sha256": planted_witness["pixel_sha256"],
        },
        "memory_plant": memory_plant,
        "verifier_self_test": self_test,
        "verifier_self_test_log_sha256": sha256_file(self_test_log),
    }


def progress(record: dict[str, Any]) -> None:
    memory = record["memory"]
    peak = max(
        int(memory["peak_process_tree_private_committed_bytes"]),
        int(memory["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]),
    )
    print(
        f"[run {record['sequence_index'] + 1:03d}/133] {record['run_id']} "
        f"wall={record['wall_seconds']:.2f}s "
        f"peak={peak / (1 << 30):.4f}GiB "
        f"coverage={record['sampling_coverage']:.6f} "
        f"host_mean={record['whole_host_cpu_mean_percent']:.1f}% "
        f"hash={record['output_sha256'][:12]}",
        flush=True,
    )


def finalize_results(
    *,
    spec: dict[str, Any],
    campaign_id: str,
    lineage: dict[str, Any],
    builds: dict[str, Any],
    sidecar_record: dict[str, Any],
    inputs_before: dict[str, Any],
    inputs_after: dict[str, Any],
    commission_record: dict[str, Any],
    journal: Journal,
    sweeps: list[dict[str, Any]],
    certificate: dict[str, Any],
) -> None:
    staging = WORK / "final-results"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copy2(PROTOCOL_PATH, staging / "protocol.json")
    shutil.copy2(journal.path, staging / "records.jsonl")
    write_json(staging / "sweeps.json", sweeps)
    write_json(staging / "inputs-before.json", inputs_before)
    write_json(staging / "inputs-after.json", inputs_after)
    write_json(staging / "commission.json", commission_record)
    write_json(staging / "sidecars.json", sidecar_record)

    public_builds: dict[str, Any] = {
        "schema": "m192-builds-v1",
        "lineage_proof": lineage,
    }
    build_logs = staging / "build-logs"
    build_logs.mkdir()
    for label, record in builds.items():
        copied = dict(record)
        source_log = Path(copied.pop("build_log_source"))
        relative_log = f"build-logs/{label}.log"
        shutil.copy2(source_log, staging / relative_log)
        copied["build_log"] = relative_log
        public_builds[label] = copied
    write_json(staging / "builds.json", public_builds)

    sidecar_dir = staging / "sidecars"
    sidecar_dir.mkdir()
    for row in sidecar_record["sidecars"]:
        source = WORK / "sidecars" / f"n{row['n']}.warpmap.txt"
        shutil.copy2(source, staging / row["artifact_path"])

    log_dir = staging / "logs"
    log_dir.mkdir()
    log_manifest = []
    registered_logs = [
        path
        for path in (WORK / "outputs").glob("*.log")
        if not path.name.startswith("commission-")
    ]
    for path in sorted(registered_logs, key=lambda item: item.name):
        destination = log_dir / path.name
        shutil.copy2(path, destination)
        log_manifest.append(
            {
                "path": f"logs/{path.name}",
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )
    require(len(log_manifest) == 266, f"expected 266 registered logs, found {len(log_manifest)}")
    write_json(
        staging / "logs-manifest.json",
        {
            "schema": "m192-logs-v1",
            "count": len(log_manifest),
            "logs": log_manifest,
        },
    )
    commission_log_dir = staging / "commission-logs"
    commission_log_dir.mkdir()
    commission_log_manifest = []
    commission_sources = [
        *sorted((WORK / "outputs").glob("commission-*.log")),
        *sorted((WORK / "commission").rglob("*.log")),
    ]
    for index, path in enumerate(commission_sources):
        destination = commission_log_dir / f"{index:02d}-{path.name}"
        shutil.copy2(path, destination)
        commission_log_manifest.append(
            {
                "path": f"commission-logs/{destination.name}",
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
            }
        )
    write_json(
        staging / "commission-logs-manifest.json",
        {
            "schema": "m192-commission-logs-v1",
            "count": len(commission_log_manifest),
            "logs": commission_log_manifest,
        },
    )
    shutil.copy2(
        WORK / "commission" / "verifier-self-test.json",
        staging / "verifier-self-test.json",
    )
    write_json(staging / "certificate.json", certificate)

    artifact_names = [
        "protocol.json",
        "records.jsonl",
        "sweeps.json",
        "inputs-before.json",
        "inputs-after.json",
        "commission.json",
        "sidecars.json",
        "builds.json",
        "logs-manifest.json",
        "commission-logs-manifest.json",
        "verifier-self-test.json",
        "certificate.json",
    ]
    complete = {
        "schema": "m192-campaign-complete-v1",
        "campaign_id": campaign_id,
        "completed_utc": utc_now(),
        "record_count": journal.count,
        "last_record_sha256": journal.previous,
        "artifact_sha256": {
            name: sha256_file(staging / name) for name in artifact_names
        },
        "interrupted_or_resumed": False,
    }
    write_json(staging / "campaign-complete.json", complete)
    require(not RESULTS.exists(), f"refusing to replace existing {RESULTS}")
    os.replace(staging, RESULTS)


def run_campaign(spec: dict[str, Any], jobs: int) -> dict[str, Any]:
    require(not RESULTS.exists(), "results already exist; no resume or overwrite is allowed")
    require(not WORK.exists(), "work directory already exists; interrupted work must be discarded")
    WORK.mkdir(parents=True)
    campaign_id = str(uuid.uuid4())
    write_json(
        WORK / "campaign-start.json",
        {
            "schema": "m192-campaign-start-v1",
            "campaign_id": campaign_id,
            "started_utc": utc_now(),
            "pid": os.getpid(),
            "host": platform.node(),
            "measured_commit": spec["lineage"]["measured_commit"],
            "resume_allowed": False,
        },
    )
    lineage = verify_frozen_sources(spec)
    monitor_path = ROOT / spec["governing_sources"]["inherited_monitor"]["path"]
    monitor = load_module("m192_inherited_m139_monitor", monitor_path)
    verifier = load_module("m192_independent_verifier", VERIFY_PATH)
    builds = {
        "unrepaired": archive_build(
            label="unrepaired",
            commit=spec["lineage"]["unrepaired_control_commit"],
            jobs=jobs,
        ),
        "measured": archive_build(
            label="measured",
            commit=spec["lineage"]["measured_commit"],
            jobs=jobs,
        ),
    }
    measured_binary = Path(builds["measured"]["binary_path"])
    sidecars, sidecar_record = prepare_sidecars(spec, measured_binary)
    print("[inputs] hashing pre-campaign selection", flush=True)
    inputs_before = input_manifest(spec, "before")
    commission_record = commission(
        monitor=monitor,
        campaign_id=campaign_id,
        spec=spec,
        builds=builds,
        sidecars=sidecars,
    )
    print("[commission] all planted defects fired", flush=True)

    journal = Journal(WORK / "records.jsonl")
    workers = tuple(int(value) for value in spec["registered_matrix"]["native"]["workers"])
    measured_commit = spec["lineage"]["measured_commit"]

    def execute(
        *,
        run_id: str,
        phase: str,
        kind: str,
        count: int,
        worker: int,
        repetition: int | None,
        sweep: str,
        order_index: int,
    ) -> dict[str, Any]:
        record, _ = run_product(
            monitor=monitor,
            campaign_id=campaign_id,
            binary=measured_binary,
            commit=measured_commit,
            run_id=run_id,
            phase=phase,
            kind=kind,
            count=count,
            workers=worker,
            repetition=repetition,
            sweep=sweep,
            order_index=order_index,
            stack=Path(spec["inputs"][str(count)]),
            sidecar=sidecars[count],
            repaired=True,
        )
        sealed = journal.append(record)
        progress(sealed)
        return sealed

    for count in (33, 105, 299):
        for order_index, worker in enumerate(workers):
            execute(
                run_id=f"native-n{count}-w{worker}-warmup",
                phase="native",
                kind="warmup",
                count=count,
                worker=worker,
                repetition=None,
                sweep="ascending",
                order_index=order_index,
            )
        for repetition in range(1, 7):
            order = workers if repetition % 2 else tuple(reversed(workers))
            sweep = "ascending" if repetition % 2 else "descending"
            for order_index, worker in enumerate(order):
                execute(
                    run_id=f"native-n{count}-w{worker}-r{repetition}",
                    phase="native",
                    kind="scored",
                    count=count,
                    worker=worker,
                    repetition=repetition,
                    sweep=sweep,
                    order_index=order_index,
                )

    sweeps: list[dict[str, Any]] = []

    def timed_sweep(
        sweep_id: str,
        repetition: int | None,
        order: tuple[int, ...],
        kind: str,
        sweep_name: str,
    ) -> None:
        sampler = HostCpuSampler(monitor.system_times)
        sampler.start()
        run_rows: list[dict[str, Any]] = []
        try:
            for order_index, count in enumerate(order):
                run_rows.append(
                    execute(
                        run_id=(
                            f"modulo-n{count}-warmup"
                            if kind == "warmup"
                            else f"modulo-n{count}-r{repetition}"
                        ),
                        phase="modulo",
                        kind=kind,
                        count=count,
                        worker=16,
                        repetition=repetition,
                        sweep=sweep_name,
                        order_index=order_index,
                    )
                )
        finally:
            cpu = sampler.finish()
        total_external = sum(
            float(row["host_load_during_run"]["external_busy_cpu_seconds"])
            for row in run_rows
        )
        total_capacity = sum(
            float(row["wall_seconds"])
            * int(row["host_load_during_run"]["logical_processors"])
            for row in run_rows
        )
        sweeps.append(
            {
                "schema": "m192-sweep-cpu-v1",
                "sweep_id": sweep_id,
                "kind": kind,
                "repetition": repetition,
                "order": list(order),
                "run_ids": [row["run_id"] for row in run_rows],
                **cpu,
                "external_busy_fraction_of_wall_capacity": (
                    total_external / total_capacity if total_capacity else None
                ),
                "per_run_host_cpu_mean_percent": {
                    row["run_id"]: row["whole_host_cpu_mean_percent"]
                    for row in run_rows
                },
                "per_run_external_busy_fraction": {
                    row["run_id"]: row["host_load_during_run"][
                        "external_busy_fraction_of_wall_capacity"
                    ]
                    for row in run_rows
                },
            }
        )
        print(
            f"[sweep] {sweep_id} host mean="
            f"{sweeps[-1]['whole_host_cpu_mean_percent']:.1f}% peak="
            f"{sweeps[-1]['whole_host_cpu_peak_percent']:.1f}% external="
            f"{100 * sweeps[-1]['external_busy_fraction_of_wall_capacity']:.1f}%",
            flush=True,
        )

    counts = (96, 97, 98, 99)
    timed_sweep("modulo-warmup", None, counts, "warmup", "warmup-ascending")
    for repetition in range(1, 7):
        order = counts if repetition % 2 else tuple(reversed(counts))
        timed_sweep(
            f"modulo-r{repetition}",
            repetition,
            order,
            "scored",
            "ascending" if repetition % 2 else "descending",
        )

    require(journal.count == 133, f"campaign produced {journal.count} records")
    print("[inputs] hashing post-campaign selection", flush=True)
    inputs_after = input_manifest(spec, "after")
    require(
        inputs_before["files"] == inputs_after["files"],
        "read-only input selection changed during campaign",
    )
    rows = verifier.strict_records(journal.path)
    verifier.validate_record_structure(rows, spec, None)
    recomputed = verifier.recompute_bars(rows, sweeps, spec)
    measured_hash = builds["measured"]["binary_sha256"]
    failed_bars = [
        name for name, value in recomputed["bars"].items() if value["verdict"] == "FAIL"
    ]
    unmeasured_bars = [
        name
        for name, value in recomputed["bars"].items()
        if value["verdict"] not in {"PASS", "FAIL"}
    ]
    if recomputed["overall_verdict"] == "PASS":
        one_line = "M12 PASSES"
    elif recomputed["overall_verdict"] == "FAIL":
        one_line = "M12 FAILS — " + ", ".join(failed_bars)
    else:
        one_line = "M12 UNMEASURED — " + ", ".join(unmeasured_bars)
    certificate = {
        "schema": "m192-m12-certificate-v1",
        "campaign_id": campaign_id,
        "generated_utc": utc_now(),
        "lineage": {
            "measured_commit": measured_commit,
            "measured_tree": spec["lineage"]["measured_tree"],
            "binary_sha256": measured_hash,
            "binary_bytes": builds["measured"]["binary_bytes"],
            "version_output": builds["measured"]["version_output"],
            "d9_repair_commit": spec["lineage"]["d9_repair_commit"],
            "bounded_memory_repair_commit": spec["lineage"][
                "bounded_memory_repair_commit"
            ],
            "repair_owned_diff_bytes": lineage["repair_owned_diff_bytes"],
        },
        "protocol_sha256_checkout": sha256_file(PROTOCOL_PATH),
        "records": {
            "count": journal.count,
            "sha256": sha256_file(journal.path),
            "last_record_sha256": journal.previous,
        },
        "configuration": spec["configuration"],
        "sampling_quality": recomputed["sampling_quality"],
        "bars": recomputed["bars"],
        "partition": recomputed["partition"],
        "overall_verdict": recomputed["overall_verdict"],
        "one_line_verdict": one_line,
    }
    finalize_results(
        spec=spec,
        campaign_id=campaign_id,
        lineage=lineage,
        builds=builds,
        sidecar_record=sidecar_record,
        inputs_before=inputs_before,
        inputs_after=inputs_after,
        commission_record=commission_record,
        journal=journal,
        sweeps=sweeps,
        certificate=certificate,
    )
    verified = verifier.verify_artifact(RESULTS)
    write_json(RESULTS / "verification.json", verified)
    print(json.dumps(certificate, indent=2), flush=True)
    return certificate


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--jobs", type=int, default=8)
    result.add_argument(
        "--discard-interrupted",
        action="store_true",
        help="Delete only M192 work/results before starting a full zero-resume rerun.",
    )
    result.add_argument(
        "--verify-only",
        action="store_true",
        help="Run the independent verifier on an existing complete artifact.",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    spec = read_json(PROTOCOL_PATH)
    try:
        if args.verify_only:
            verifier = load_module("m192_independent_verifier", VERIFY_PATH)
            result = verifier.verify_artifact(RESULTS)
            print(json.dumps(result, indent=2))
            return 0
        if args.discard_interrupted:
            if WORK.exists():
                shutil.rmtree(WORK)
            if RESULTS.exists():
                shutil.rmtree(RESULTS)
        certificate = run_campaign(spec, args.jobs)
        return 0 if certificate["overall_verdict"] in {"PASS", "FAIL", "UNMEASURED"} else 1
    except Exception as error:
        if WORK.exists():
            try:
                write_json(
                    WORK / "campaign-aborted.json",
                    {
                        "schema": "m192-campaign-aborted-v1",
                        "generated_utc": utc_now(),
                        "error": str(error),
                        "resume_allowed": False,
                    },
                )
            except Exception:
                pass
        print(f"CAMPAIGN ERROR: {error}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
