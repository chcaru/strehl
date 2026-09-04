from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable

import psutil

import instrument as base


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def preload_allowed(samples: list[float], threshold: float) -> bool:
    return len(samples) == 5 and mean(samples) <= threshold


def external_busy(
    total_busy_percent: float,
    own_cpu_seconds: float,
    elapsed_seconds: float,
    logical_cpus: int,
) -> float:
    if elapsed_seconds <= 0.0 or logical_cpus <= 0:
        raise ValueError("invalid CPU normalization")
    own_percent = 100.0 * own_cpu_seconds / (elapsed_seconds * logical_cpus)
    return max(total_busy_percent - own_percent, 0.0)


def should_pause(samples: Iterable[float], threshold: float) -> bool:
    values = list(samples)
    return len(values) == 5 and mean(values) > threshold


def system_cpu_snapshot() -> tuple[float, float]:
    fields = psutil.cpu_times()._asdict()
    total = float(sum(fields.values()))
    idle = float(fields.get("idle", 0.0) + fields.get("iowait", 0.0))
    return total, idle


def system_busy(previous: tuple[float, float], current: tuple[float, float]) -> float:
    total_delta = current[0] - previous[0]
    idle_delta = current[1] - previous[1]
    if total_delta <= 0.0:
        return 0.0
    return max(0.0, min(100.0, 100.0 * (total_delta - idle_delta) / total_delta))


def process_tree(root: psutil.Process) -> list[psutil.Process]:
    processes: dict[int, psutil.Process] = {}
    try:
        processes[root.pid] = root
        for child in root.children(recursive=True):
            processes[child.pid] = child
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return list(processes.values())


def tree_cpu_snapshot(root: psutil.Process) -> dict[int, float]:
    snapshot: dict[int, float] = {}
    for process in process_tree(root):
        try:
            times = process.cpu_times()
            snapshot[process.pid] = float(times.user + times.system)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return snapshot


def tree_cpu_delta(previous: dict[int, float], current: dict[int, float]) -> float:
    return sum(
        max(value - previous.get(pid, value), 0.0)
        for pid, value in current.items()
    )


def suspend_tree(root: psutil.Process) -> list[int]:
    members = process_tree(root)
    ordered = [process for process in members if process.pid != root.pid] + [root]
    suspended: list[int] = []
    for process in ordered:
        try:
            process.suspend()
            suspended.append(process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return suspended


def resume_tree(root: psutil.Process, pids: Iterable[int]) -> list[int]:
    resumed: list[int] = []
    for pid in pids:
        try:
            psutil.Process(pid).resume()
            resumed.append(pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    if root.pid not in resumed:
        try:
            root.resume()
            resumed.append(root.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return resumed


def render_environment(cache: Path) -> dict[str, str]:
    env = dict(os.environ)
    for name in tuple(env):
        if name.upper().startswith("STREHL_"):
            del env[name]
    env.update(
        {
            "STREHL_CACHE_DIR": str(cache.resolve()),
            "STREHL_FULLRES_GATHER": "1",
            "STREHL_DEFECT": "off",
            "STREHL_FIX_CA": "off",
            "STREHL_PYRAMID_WORKERS": "2",
            "RAYON_NUM_THREADS": "6",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    return env


def command_commission(args: argparse.Namespace) -> int:
    checks = {
        "preload_green": preload_allowed([10.0, 12.0, 14.0, 8.0, 11.0], 15.0),
        "preload_red": not preload_allowed([20.0, 20.0, 20.0, 20.0, 20.0], 15.0),
        "external_subtraction": abs(
            external_busy(60.0, 4.0, 1.0, 8) - 10.0
        )
        <= 1e-12,
        "external_zero": external_busy(50.0, 4.0, 1.0, 8) == 0.0,
        "pause_red": should_pause([8.0, 9.0, 11.0, 12.0, 11.0], 10.0),
        "pause_green": not should_pause([8.0, 9.0, 10.0, 10.0, 10.0], 10.0),
    }
    child = psutil.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    pid = child.pid
    try:
        child.suspend()
        time.sleep(0.1)
        suspended = child.status() == psutil.STATUS_STOPPED
        child.resume()
        time.sleep(0.1)
        resumed = child.status() != psutil.STATUS_STOPPED
    finally:
        try:
            child.terminate()
            child.wait(timeout=5)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
    checks["pid_specific_suspend"] = suspended
    checks["pid_specific_resume"] = resumed
    payload = {
        "schema": "M-COVER-BORDER-LOAD-GOVERNOR-COMMISSION-1",
        "checks": checks,
        "passed": all(checks.values()),
        "readings": {
            "commission_child_pid": pid,
            "external_subtraction_percent": external_busy(60.0, 4.0, 1.0, 8),
        },
    }
    base.write_json(args.out, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["passed"] else 1


def command_run(args: argparse.Namespace) -> int:
    for path in (args.out, args.render_log, args.load_log):
        if path.exists():
            raise SystemExit(f"refusing to overwrite {path}")
    binary_sha = base.sha256(args.binary)
    if binary_sha != args.expected_binary_sha.upper():
        raise SystemExit(
            f"binary hash mismatch: {binary_sha} != {args.expected_binary_sha.upper()}"
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.render_log.parent.mkdir(parents=True, exist_ok=True)
    args.load_log.parent.mkdir(parents=True, exist_ok=True)
    args.cache.mkdir(parents=True, exist_ok=True)

    state: dict[str, Any] = {
        "schema": "M-COVER-BORDER-LOAD-GOVERNED-RENDER-1",
        "binary": {
            "path": str(args.binary.resolve()),
            "sha256": binary_sha,
        },
        "source": str(args.source.resolve()),
        "mode": args.mode,
        "bands": args.bands,
        "thresholds": {
            "preload_five_second_mean_percent": args.preload_threshold,
            "external_five_second_mean_percent": args.external_threshold,
        },
        "logical_cpus": psutil.cpu_count(logical=True) or 1,
        "preload_attempts": [],
        "samples": [],
        "events": [],
    }

    wait_started = time.monotonic()
    while True:
        samples = [psutil.cpu_percent(interval=1.0) for _ in range(5)]
        attempt = {
            "samples_percent": samples,
            "mean_percent": mean(samples),
            "passed": preload_allowed(samples, args.preload_threshold),
        }
        state["preload_attempts"].append(attempt)
        print(
            f"pre-load mean {attempt['mean_percent']:.2f}% "
            f"({'PASS' if attempt['passed'] else 'WAIT'})",
            flush=True,
        )
        if attempt["passed"]:
            break
        if time.monotonic() - wait_started > args.max_wait_seconds:
            state["status"] = "PRELOAD_TIMEOUT"
            base.write_json(args.load_log, state)
            return 2
        time.sleep(args.retry_delay_seconds)

    argv = [
        str(args.binary.resolve()),
        "stack",
        str(args.source.resolve()),
        "--merge",
        "pyramid",
        "--pyramid-bands",
        str(args.bands),
        "--resampler",
        "catmull-rom",
        "--cover",
        args.mode,
        "--out",
        str(args.out.resolve()),
    ]
    env = render_environment(args.cache)
    state["argv"] = argv
    state["environment"] = {
        name: env[name]
        for name in (
            "STREHL_CACHE_DIR",
            "STREHL_FULLRES_GATHER",
            "STREHL_DEFECT",
            "STREHL_FIX_CA",
            "STREHL_PYRAMID_WORKERS",
            "RAYON_NUM_THREADS",
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    }
    started = time.monotonic()
    with args.render_log.open("wb") as log:
        process = psutil.Popen(
            argv,
            cwd=str(args.repo.resolve()),
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        state["render_pid"] = process.pid
        system_previous = system_cpu_snapshot()
        tree_previous = tree_cpu_snapshot(process)
        sample_previous = time.monotonic()
        rolling: collections.deque[float] = collections.deque(maxlen=5)
        accepted_max = 0.0
        observed_max = 0.0
        while process.poll() is None:
            time.sleep(1.0)
            now = time.monotonic()
            system_current = system_cpu_snapshot()
            tree_current = tree_cpu_snapshot(process)
            total_busy = system_busy(system_previous, system_current)
            own_seconds = tree_cpu_delta(tree_previous, tree_current)
            elapsed = now - sample_previous
            own_percent = (
                100.0
                * own_seconds
                / (elapsed * int(state["logical_cpus"]))
                if elapsed > 0.0
                else 0.0
            )
            external = external_busy(
                total_busy,
                own_seconds,
                elapsed,
                int(state["logical_cpus"]),
            )
            rolling.append(external)
            rolling_mean = mean(rolling)
            if len(rolling) == 5:
                observed_max = max(observed_max, rolling_mean)
            sample = {
                "elapsed_seconds": now - started,
                "total_busy_percent": total_busy,
                "render_tree_busy_percent": own_percent,
                "external_busy_percent": external,
                "external_five_second_mean_percent": rolling_mean,
                "window_samples": len(rolling),
            }
            state["samples"].append(sample)
            if len(rolling) == 5 and should_pause(rolling, args.external_threshold):
                suspended = suspend_tree(process)
                event: dict[str, Any] = {
                    "event": "suspend",
                    "elapsed_seconds": now - started,
                    "trigger_mean_percent": rolling_mean,
                    "pids": suspended,
                    "wait_windows": [],
                }
                state["events"].append(event)
                print(
                    f"external mean {rolling_mean:.2f}% > "
                    f"{args.external_threshold:.2f}%: suspended PID {process.pid}",
                    flush=True,
                )
                while process.poll() is None:
                    paused_samples = [
                        psutil.cpu_percent(interval=1.0) for _ in range(5)
                    ]
                    paused_mean = mean(paused_samples)
                    event["wait_windows"].append(
                        {
                            "samples_percent": paused_samples,
                            "mean_percent": paused_mean,
                        }
                    )
                    if paused_mean <= args.external_threshold:
                        break
                    if time.monotonic() - wait_started > args.max_wait_seconds:
                        resume_tree(process, suspended)
                        try:
                            process.terminate()
                            process.wait(timeout=30)
                        except (psutil.NoSuchProcess, psutil.TimeoutExpired):
                            try:
                                process.kill()
                            except psutil.NoSuchProcess:
                                pass
                        state["status"] = "DURING_LOAD_TIMEOUT"
                        base.write_json(args.load_log, state)
                        return 3
                    time.sleep(args.retry_delay_seconds)
                resumed = resume_tree(process, suspended)
                event["resume_elapsed_seconds"] = time.monotonic() - started
                event["resumed_pids"] = resumed
                print(f"resumed PID {process.pid}", flush=True)
                rolling.clear()
                system_previous = system_cpu_snapshot()
                tree_previous = tree_cpu_snapshot(process)
                sample_previous = time.monotonic()
                continue
            if len(rolling) == 5:
                accepted_max = max(accepted_max, rolling_mean)
            system_previous = system_current
            tree_previous = tree_current
            sample_previous = now
        returncode = process.wait()

    state["duration_seconds"] = time.monotonic() - started
    state["returncode"] = returncode
    state["max_observed_external_five_second_mean_percent"] = observed_max
    state["max_accepted_external_five_second_mean_percent"] = accepted_max
    state["pause_count"] = sum(
        event["event"] == "suspend" for event in state["events"]
    )
    state["status"] = "PASS" if returncode == 0 and args.out.is_file() else "FAIL"
    if args.out.is_file():
        state["output"] = {
            "path": str(args.out.resolve()),
            "bytes": args.out.stat().st_size,
            "sha256": base.sha256(args.out),
        }
    base.write_json(args.load_log, state)
    print(
        json.dumps(
            {
                "status": state["status"],
                "duration_seconds": state["duration_seconds"],
                "pause_count": state["pause_count"],
                "max_accepted_external_five_second_mean_percent": accepted_max,
                "output": state.get("output"),
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )
    return 0 if state["status"] == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    commission = subparsers.add_parser("commission")
    commission.add_argument("--out", type=Path, required=True)
    commission.set_defaults(func=command_commission)

    run = subparsers.add_parser("run")
    run.add_argument("--repo", type=Path, required=True)
    run.add_argument("--binary", type=Path, required=True)
    run.add_argument("--expected-binary-sha", required=True)
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--cache", type=Path, required=True)
    run.add_argument("--mode", choices=("scale", "crop"), required=True)
    run.add_argument("--bands", type=int, choices=(2, 7), required=True)
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--render-log", type=Path, required=True)
    run.add_argument("--load-log", type=Path, required=True)
    run.add_argument("--preload-threshold", type=float, default=15.0)
    run.add_argument("--external-threshold", type=float, default=10.0)
    run.add_argument("--retry-delay-seconds", type=float, default=15.0)
    run.add_argument("--max-wait-seconds", type=float, default=21600.0)
    run.set_defaults(func=command_run)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
