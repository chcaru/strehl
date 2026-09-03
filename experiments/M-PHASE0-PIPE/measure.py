"""Commissioned Windows timing harness for M-PHASE0-PIPE.

The harness times the real `strehl stack` process, records whole-machine and
child CPU use, consumes the complete TIFF, and keeps every arm in JSONL.  It
does not decide whether a queue implementation is correct; independent hash
checks and the repository tests do that.
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


LOGICAL_CPUS = os.cpu_count() or 1
QUEUE_ENV = "STREHL_DECODE_FOLD_QUEUE"
WORKERS_ENV = "STREHL_PYRAMID_WORKERS"
RAYON_ENV = "RAYON_NUM_THREADS"

FOLD_RE = re.compile(
    r"folded\s+:\s+(\d+)\s+/\s+(\d+)\s+frames in\s+([\d.]+)\s+s"
)
PLAN_RE = re.compile(
    r"memory plan\s+:\s+(\d+)\s+workers x\s+([\d.]+)\s+MB"
)
TOTAL_RE = re.compile(r"^total\s+:\s+([\d.]+)\s+s", re.MULTILINE)
QUEUE_RE = re.compile(r"decode.fold queue\s+:\s+(.+)", re.IGNORECASE)

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class FILETIME(ctypes.Structure):
    _fields_ = [("low", wt.DWORD), ("high", wt.DWORD)]

    def value(self) -> int:
        return (self.high << 32) | self.low


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("length", wt.DWORD),
        ("memory_load", wt.DWORD),
        ("total_phys", ctypes.c_ulonglong),
        ("avail_phys", ctypes.c_ulonglong),
        ("total_page", ctypes.c_ulonglong),
        ("avail_page", ctypes.c_ulonglong),
        ("total_virtual", ctypes.c_ulonglong),
        ("avail_virtual", ctypes.c_ulonglong),
        ("avail_extended_virtual", ctypes.c_ulonglong),
    ]


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
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
    ]


def system_times() -> tuple[int, int, int]:
    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    if not kernel32.GetSystemTimes(
        ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return idle.value(), kernel.value(), user.value()


def busy_between(
    before: tuple[int, int, int], after: tuple[int, int, int]
) -> tuple[float, float]:
    idle = after[0] - before[0]
    total = (after[1] - before[1]) + (after[2] - before[2])
    busy = max(0, total - idle)
    return (busy / total if total else 0.0), busy / 10_000_000.0


def sample_busy(seconds: float) -> float:
    before = system_times()
    time.sleep(seconds)
    return busy_between(before, system_times())[0]


def memory_status() -> tuple[int, int]:
    status = MEMORYSTATUSEX()
    status.length = ctypes.sizeof(status)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(status.total_phys), int(status.avail_phys)


def process_cpu_seconds(handle: int) -> float:
    created, exited, kernel, user = FILETIME(), FILETIME(), FILETIME(), FILETIME()
    if not kernel32.GetProcessTimes(
        wt.HANDLE(handle),
        ctypes.byref(created),
        ctypes.byref(exited),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return (kernel.value() + user.value()) / 10_000_000.0


def peak_working_set(handle: int) -> int:
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(counters)
    fn = kernel32.K32GetProcessMemoryInfo
    if not fn(wt.HANDLE(handle), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.peak_working_set_size)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def tiff_witness(path: Path) -> dict[str, Any]:
    image = tifffile.imread(path)
    pixels = int(image.size)
    nonzero = int(np.count_nonzero(image))
    total = int(image.sum(dtype=np.uint64))
    if pixels == 0 or nonzero == 0 or total == 0:
        raise ValueError(
            f"zero output witness: pixels={pixels}, nonzero={nonzero}, sum={total}"
        )
    return {
        "out_bytes": path.stat().st_size,
        "out_sha256": sha256(path),
        "out_shape": list(image.shape),
        "out_dtype": str(image.dtype),
        "out_pixels": pixels,
        "out_nonzero": nonzero,
        "out_sum": total,
    }


def executable_provenance(exe: Path) -> dict[str, Any]:
    return {
        "exe": str(exe.resolve()),
        "exe_bytes": exe.stat().st_size,
        "exe_sha256": sha256(exe),
    }


def capture_manifest(stack: Path) -> dict[str, Any]:
    # Rule 14 requires Get-ChildItem -Force.  Keep the listing in memory and
    # hash stdout; the capture remains read-only.
    escaped = str(stack.resolve()).replace("'", "''")
    script = (
        f"$p='{escaped}'; "
        "Get-ChildItem -LiteralPath $p -Force -Recurse | "
        "Sort-Object FullName | ForEach-Object { "
        "'{0}|{1}|{2}|{3}' -f $_.FullName, "
        "($(if ($_.PSIsContainer) {'D'} else {$_.Length})), "
        "$_.LastWriteTimeUtc.Ticks, [int]$_.Attributes }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    payload = result.stdout.encode("utf-8")
    arws = sorted(stack.glob("*.ARW"), key=lambda p: p.name.lower())
    return {
        "stack": str(stack.resolve()),
        "entries": len(result.stdout.splitlines()),
        "manifest_sha256": hashlib.sha256(payload).hexdigest().upper(),
        "arw_count": len(arws),
        "arw_bytes": sum(path.stat().st_size for path in arws),
    }


def parse_stderr(stderr: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    if match := FOLD_RE.search(stderr):
        parsed["folded"] = int(match.group(1))
        parsed["frames"] = int(match.group(2))
        parsed["fold_s"] = float(match.group(3))
    if match := PLAN_RE.search(stderr):
        parsed["planned_workers"] = int(match.group(1))
        parsed["worker_mb"] = float(match.group(2))
    if match := TOTAL_RE.search(stderr):
        parsed["reported_total_s"] = float(match.group(1))
    if match := QUEUE_RE.search(stderr):
        parsed["queue_banner"] = match.group(1).strip()
    return parsed


def clean_environment(
    sidecar: Path | None, workers: int | None, queue: str
) -> tuple[dict[str, str], dict[str, str | None]]:
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("STREHL_") or key.startswith("RAYON_"):
            env.pop(key, None)
    env[RAYON_ENV] = str(LOGICAL_CPUS)
    if sidecar is None:
        env["STREHL_ALIGN"] = "0"
    else:
        env["STREHL_WARPMAP"] = str(sidecar.resolve())
    if workers is not None:
        env[WORKERS_ENV] = str(workers)
    if queue != "unset":
        env[QUEUE_ENV] = queue
    recorded = {
        "STREHL_ALIGN": env.get("STREHL_ALIGN"),
        "STREHL_WARPMAP": env.get("STREHL_WARPMAP"),
        WORKERS_ENV: env.get(WORKERS_ENV),
        QUEUE_ENV: env.get(QUEUE_ENV),
        RAYON_ENV: env.get(RAYON_ENV),
    }
    return env, recorded


def wait_for_resources(
    worker_mb: float | None,
    workers: int,
    frames: int,
    idle_wait_s: float,
    memory_wait_s: float,
) -> tuple[float, int, int, float]:
    active_chunks = math.ceil(frames / math.ceil(frames / workers))
    required = 0
    if worker_mb is not None and workers >= 16:
        required = int(active_chunks * worker_mb * (1 << 20) + 4 * (1 << 30))

    deadline = time.monotonic() + memory_wait_s
    total, available = memory_status()
    while required and available < required and time.monotonic() < deadline:
        print(
            f"waiting for RAM: {available / (1 << 30):.1f} GiB available, "
            f"{required / (1 << 30):.1f} GiB required",
            flush=True,
        )
        time.sleep(min(15.0, max(0.0, deadline - time.monotonic())))
        total, available = memory_status()
    if required and available < required:
        raise RuntimeError(
            f"resource guard: {available / (1 << 30):.1f} GiB available < "
            f"{required / (1 << 30):.1f} GiB required"
        )

    deadline = time.monotonic() + idle_wait_s
    pre_busy = sample_busy(5.0)
    while pre_busy > 0.15 and time.monotonic() < deadline:
        print(f"waiting for idle host: pre-run busy {100 * pre_busy:.1f}%", flush=True)
        pre_busy = sample_busy(5.0)
    return pre_busy, total, available, required / (1 << 30)


def append_record(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(json.dumps(record, sort_keys=True) + "\n")


def run_stack(
    *,
    exe: Path,
    stack: Path,
    sidecar: Path | None,
    destination: Path,
    limit: int,
    workers: int | None,
    queue: str,
    label: str,
    kind: str,
    record_path: Path,
    source_commit: str,
    pass_name: str,
    repetition: int,
    plant_ms: int,
    known_worker_mb: float | None,
    idle_wait_s: float,
    memory_wait_s: float,
) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.unlink(missing_ok=True)
    stderr_path = destination.with_suffix(destination.suffix + ".stderr.txt")
    stderr_path.unlink(missing_ok=True)
    use_workers = workers or 1

    base: dict[str, Any] = {
        "schema": 1,
        "when_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "kind": kind,
        "label": label,
        "pass": pass_name,
        "repetition": repetition,
        "source_commit": source_commit,
        "stack": str(stack.resolve()),
        "limit": limit,
        "workers": workers,
        "queue": queue,
        "plant_ms": plant_ms,
        "logical_cpus": LOGICAL_CPUS,
    }
    base.update(executable_provenance(exe))

    try:
        pre_busy, total_mem, avail_mem, required_gib = wait_for_resources(
            known_worker_mb,
            use_workers,
            limit,
            idle_wait_s,
            memory_wait_s,
        )
    except RuntimeError as error:
        base.update(
            {
                "skipped": True,
                "valid": False,
                "invalid_reasons": [str(error)],
            }
        )
        append_record(record_path, base)
        print(f"SKIP {label}: {error}", flush=True)
        return base

    env, env_record = clean_environment(sidecar, workers, queue)
    argv = [
        str(exe.resolve()),
        "stack",
        str(stack.resolve()),
        "--out",
        str(destination.resolve()),
        "--limit",
        str(limit),
        "--merge",
        "pyramid",
    ]
    before = system_times()
    start = time.perf_counter()
    if plant_ms:
        time.sleep(plant_ms / 1000.0)
    process = subprocess.Popen(
        argv,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )
    stdout, stderr = process.communicate()
    wall = time.perf_counter() - start
    after = system_times()
    handle = int(process._handle)  # Windows handle remains valid after exit.
    child_cpu = process_cpu_seconds(handle)
    peak_ws = peak_working_set(handle)
    system_busy_frac, system_busy_cpu_s = busy_between(before, after)
    external_cpu_s = max(0.0, system_busy_cpu_s - child_cpu)
    external_busy_frac = min(1.0, external_cpu_s / (wall * LOGICAL_CPUS))

    stderr_path.write_text(stderr, encoding="utf-8")
    record = {
        **base,
        "skipped": False,
        "argv": argv,
        "env": env_record,
        "sidecar": str(sidecar.resolve()) if sidecar else None,
        "wall_s": wall,
        "rc": process.returncode,
        "stdout": stdout,
        "stderr_path": str(stderr_path.resolve()),
        "pre_busy_frac": pre_busy,
        "system_busy_frac": system_busy_frac,
        "system_busy_cpu_s": system_busy_cpu_s,
        "child_cpu_s": child_cpu,
        "external_cpu_s": external_cpu_s,
        "external_busy_frac": external_busy_frac,
        "peak_ws_bytes": peak_ws,
        "total_phys_bytes": total_mem,
        "available_phys_before_bytes": avail_mem,
        "required_free_gib": required_gib,
    }
    record.update(parse_stderr(stderr))

    reasons: list[str] = []
    if process.returncode != 0:
        reasons.append(f"rc={process.returncode}")
    if record.get("folded") != limit or record.get("frames") != limit:
        reasons.append(
            f"fold count {record.get('folded')}/{record.get('frames')} != {limit}/{limit}"
        )
    if not (0.0 < float(record.get("fold_s", 0.0)) <= wall):
        reasons.append(f"fold_s={record.get('fold_s')} outside (0, wall]")
    if pre_busy > 0.15:
        reasons.append(f"pre_busy={pre_busy:.4f} > 0.15")
    if external_busy_frac > 0.10:
        reasons.append(f"external_busy={external_busy_frac:.4f} > 0.10")

    if process.returncode == 0 and destination.exists():
        try:
            record.update(tiff_witness(destination))
        except Exception as error:  # noqa: BLE001 -- invalid artifacts stay recorded.
            reasons.append(f"TIFF validation failed: {error}")
    else:
        reasons.append("output TIFF missing")

    record["valid"] = not reasons
    record["invalid_reasons"] = reasons
    append_record(record_path, record)
    status = "VALID" if record["valid"] else "INVALID"
    print(
        f"{status} {label} {pass_name} W={workers} N={limit} queue={queue}: "
        f"wall={wall:.3f}s fold={record.get('fold_s')}s "
        f"busy={100 * system_busy_frac:.1f}% "
        f"external={100 * external_busy_frac:.1f}% "
        f"cpu={child_cpu:.1f}s peak={peak_ws / (1 << 30):.2f}GiB "
        f"hash={record.get('out_sha256', '-')[:16]}",
        flush=True,
    )
    if reasons:
        print("  " + "; ".join(reasons), flush=True)
    return record


def add_common_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--stack", type=Path, required=True)
    parser.add_argument("--sidecar", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--limit", type=int, default=64)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--idle-wait-s", type=float, default=60.0)
    parser.add_argument("--memory-wait-s", type=float, default=300.0)


def command_manifest(args: argparse.Namespace) -> int:
    manifests = [capture_manifest(stack) for stack in args.stack]
    record = {
        "schema": 1,
        "kind": "manifest",
        "phase": args.phase,
        "when_local": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "manifests": manifests,
    }
    append_record(args.records, record)
    print(json.dumps(record, indent=2))
    return 0


def command_commission(args: argparse.Namespace) -> int:
    common = dict(
        exe=args.exe,
        stack=args.stack,
        sidecar=args.sidecar,
        limit=args.limit,
        workers=args.workers,
        queue="unset",
        label=args.label,
        kind="commission",
        record_path=args.records,
        source_commit=args.source_commit,
        idle_wait_s=args.idle_wait_s,
        memory_wait_s=args.memory_wait_s,
    )
    baseline = run_stack(
        **common,
        destination=args.out_dir / "commission-baseline.tif",
        pass_name="baseline",
        repetition=0,
        plant_ms=0,
        known_worker_mb=None,
    )
    planted = run_stack(
        **common,
        destination=args.out_dir / "commission-planted.tif",
        pass_name="planted-2000ms",
        repetition=0,
        plant_ms=2000,
        known_worker_mb=baseline.get("worker_mb"),
    )
    if not baseline.get("valid") or not planted.get("valid"):
        print("COMMISSION RED: one or both timing arms invalid")
        return 1
    delta = float(planted["wall_s"]) - float(baseline["wall_s"])
    same_hash = planted.get("out_sha256") == baseline.get("out_sha256")
    passed = 1.750 <= delta <= 2.500 and same_hash
    verdict = {
        "schema": 1,
        "kind": "commission-verdict",
        "wall_delta_s": delta,
        "accepted_range_s": [1.750, 2.500],
        "same_output_hash": same_hash,
        "baseline_hash": baseline.get("out_sha256"),
        "planted_hash": planted.get("out_sha256"),
        "passed": passed,
    }
    append_record(args.records, verdict)
    print(json.dumps(verdict, indent=2))
    return 0 if passed else 1


def command_sweep(args: argparse.Namespace) -> int:
    settings = [int(value) for value in args.workers.split(",")]
    passes: list[tuple[str, list[int]]] = [
        ("up", settings),
        ("down", list(reversed(settings))),
    ]
    known_worker_mb: float | None = None
    for pass_name, order in passes:
        for workers in order:
            record = run_stack(
                exe=args.exe,
                stack=args.stack,
                sidecar=args.sidecar,
                destination=args.out_dir / f"{args.label}-{pass_name}-w{workers}.tif",
                limit=args.limit,
                workers=workers,
                queue="unset",
                label=args.label,
                kind="d13-sweep",
                record_path=args.records,
                source_commit=args.source_commit,
                pass_name=pass_name,
                repetition=0,
                plant_ms=0,
                known_worker_mb=known_worker_mb,
                idle_wait_s=args.idle_wait_s,
                memory_wait_s=args.memory_wait_s,
            )
            if record.get("worker_mb"):
                known_worker_mb = float(record["worker_mb"])
    return 0


def command_bench(args: argparse.Namespace) -> int:
    known_worker_mb: float | None = None
    for repetition in range(args.repetitions):
        modes = ["off", "on"] if repetition % 2 == 0 else ["on", "off"]
        for mode in modes:
            record = run_stack(
                exe=args.exe,
                stack=args.stack,
                sidecar=args.sidecar,
                destination=args.out_dir
                / f"{args.label}-r{repetition}-{mode}.tif",
                limit=args.limit,
                workers=None,
                queue=mode,
                label=args.label,
                kind="queue-bench",
                record_path=args.records,
                source_commit=args.source_commit,
                pass_name=f"r{repetition}-{mode}",
                repetition=repetition,
                plant_ms=0,
                known_worker_mb=known_worker_mb,
                idle_wait_s=args.idle_wait_s,
                memory_wait_s=args.memory_wait_s,
            )
            if record.get("worker_mb"):
                known_worker_mb = float(record["worker_mb"])
    return 0


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                records.append(json.loads(line))
    return records


def median(values: list[float]) -> float:
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered).is_multiple_of(2):
        return 0.5 * (ordered[middle - 1] + ordered[middle])
    return ordered[middle]


def command_summary(args: argparse.Namespace) -> int:
    records = load_records(args.records)
    manifests = [r for r in records if r.get("kind") == "manifest"]
    if len(manifests) >= 2:
        print(
            "manifest match:",
            manifests[0].get("manifests") == manifests[-1].get("manifests"),
        )

    sweeps: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("kind") == "d13-sweep" and record.get("valid"):
            sweeps[(record["label"], int(record["workers"]))].append(record)
    for label in sorted({key[0] for key in sweeps}):
        print(f"\nD13 {label}")
        chosen: dict[int, float] = {}
        for workers in sorted(key[1] for key in sweeps if key[0] == label):
            arms = sweeps[(label, workers)]
            best = min(arms, key=lambda r: float(r["fold_s"]))
            chosen[workers] = float(best["fold_s"])
            print(
                f"  W={workers:2d} fold={best['fold_s']:7.3f}s "
                f"wall={best['wall_s']:7.3f}s "
                f"external={100 * best['external_busy_frac']:5.1f}% "
                f"peak={best['peak_ws_bytes'] / (1 << 30):5.2f}GiB "
                f"hash={best['out_sha256'][:16]}"
            )
        for low, high in zip(sorted(chosen), sorted(chosen)[1:]):
            print(f"  {low}->{high}: {chosen[low] / chosen[high]:.3f}x")

    benches: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("kind") == "queue-bench" and record.get("valid"):
            benches[(record["label"], record["queue"])].append(record)
    for label in sorted({key[0] for key in benches}):
        print(f"\nQUEUE {label}")
        by_mode: dict[str, list[float]] = {}
        hashes: dict[str, set[str]] = {}
        for mode in ("off", "on"):
            arms = benches.get((label, mode), [])
            walls = [float(r["wall_s"]) for r in arms]
            by_mode[mode] = walls
            hashes[mode] = {str(r["out_sha256"]) for r in arms}
            if walls:
                print(
                    f"  {mode}: n={len(walls)} best={min(walls):.3f}s "
                    f"median={median(walls):.3f}s hashes={len(hashes[mode])}"
                )
        if by_mode.get("off") and by_mode.get("on"):
            print(
                f"  best speedup={min(by_mode['off']) / min(by_mode['on']):.4f}x "
                f"hash-equal={hashes['off'] == hashes['on']}"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    manifest = commands.add_parser("manifest")
    manifest.add_argument("--stack", action="append", type=Path, required=True)
    manifest.add_argument("--records", type=Path, required=True)
    manifest.add_argument("--phase", required=True)
    manifest.set_defaults(func=command_manifest)

    commission = commands.add_parser("commission")
    add_common_run_args(commission)
    commission.add_argument("--workers", type=int, default=4)
    commission.set_defaults(func=command_commission)

    sweep = commands.add_parser("sweep")
    add_common_run_args(sweep)
    sweep.add_argument("--workers", default="1,2,4,8,16,32")
    sweep.set_defaults(func=command_sweep)

    bench = commands.add_parser("bench")
    add_common_run_args(bench)
    bench.add_argument("--repetitions", type=int, default=5)
    bench.set_defaults(func=command_bench)

    summary = commands.add_parser("summary")
    summary.add_argument("--records", type=Path, required=True)
    summary.set_defaults(func=command_summary)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
