"""M182 process-tree memory probe and intervention controls.

The production arm delegates accounting to M139's commissioned Windows Job
Object monitor.  The control arm commissions that same meter in both
directions and includes an inert source mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HARNESS_PATH = ROOT / "experiments" / "m12-scorecard" / "m12-harness.py"
WORK = HERE / "work"
RUNS = HERE / "runs"
CACHE = HERE / "cache"
TEMP = HERE / "temp"
ALLOCATION_TEMPLATE = """\
import time

ALLOCATION_BYTES = 268435456
LABEL = "baseline"

hold = bytearray(ALLOCATION_BYTES)
for offset in range(0, len(hold), 4096):
    hold[offset] = 1
print(f"{LABEL}:{len(hold)}", flush=True)
time.sleep(1.5)
"""
PARENT_SOURCE = """\
import subprocess
import sys

raise SystemExit(subprocess.call([sys.executable, sys.argv[1]]))
"""
ALLOCATION_ANCHOR = "ALLOCATION_BYTES = 268435456"
LABEL_ANCHOR = 'LABEL = "baseline"'


def load_harness() -> Any:
    spec = importlib.util.spec_from_file_location("m182_m139_harness", HARNESS_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {HARNESS_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def replace_unique_full_line(text: str, old: str, new: str, label: str) -> str:
    lines = text.splitlines()
    matches = [index for index, line in enumerate(lines) if line == old]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: full-line anchor matched {len(matches)} times, expected exactly one"
        )
    lines[matches[0]] = new
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)


def commission() -> int:
    harness = load_harness()
    control = WORK / "commission"
    clean_dir(control)
    parent = control / "parent.py"
    parent.write_text(PARENT_SOURCE, encoding="utf-8", newline="\n")

    variants = {
        "baseline": ALLOCATION_TEMPLATE,
        "allocation_plant": replace_unique_full_line(
            ALLOCATION_TEMPLATE,
            ALLOCATION_ANCHOR,
            "ALLOCATION_BYTES = 536870912",
            "allocation plant",
        ),
        "saving_plant": replace_unique_full_line(
            ALLOCATION_TEMPLATE,
            ALLOCATION_ANCHOR,
            "ALLOCATION_BYTES = 67108864",
            "saving plant",
        ),
        "inert": replace_unique_full_line(
            ALLOCATION_TEMPLATE,
            LABEL_ANCHOR,
            'LABEL = "inert"',
            "inert arm",
        ),
    }

    arms: dict[str, Any] = {}
    for name, source in variants.items():
        child = control / f"child-{name}.py"
        child.write_text(source, encoding="utf-8", newline="\n")
        arm_temp = control / f"temp-{name}"
        arm_temp.mkdir()
        env = os.environ.copy()
        env["TEMP"] = str(arm_temp)
        env["TMP"] = str(arm_temp)
        observed = harness.monitor_command(
            argv=[sys.executable, str(parent), str(child)],
            env=env,
            stdout_path=control / f"{name}.stdout.log",
            stderr_path=control / f"{name}.stderr.log",
            temp=arm_temp,
            measured_commit="M182-CONTROL",
        )
        stdout = Path(observed["stdout_log"]).read_text(encoding="utf-8")
        arms[name] = {
            "requested_allocation_bytes": {
                "baseline": 268_435_456,
                "allocation_plant": 536_870_912,
                "saving_plant": 67_108_864,
                "inert": 268_435_456,
            }[name],
            "source_sha256": sha256(child),
            "stdout": stdout.strip().splitlines()[-1],
            **observed,
        }

    peak = {
        name: arm["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]
        for name, arm in arms.items()
    }
    allocation_delta = peak["allocation_plant"] - peak["baseline"]
    saving_delta = peak["baseline"] - peak["saving_plant"]
    inert_delta = abs(peak["inert"] - peak["baseline"])
    checks = {
        "allocation_plant_raised_peak_by_at_least_192_mib": allocation_delta
        >= 192 * (1 << 20),
        "saving_plant_lowered_peak_by_at_least_128_mib": saving_delta
        >= 128 * (1 << 20),
        "inert_arm_within_16_mib": inert_delta <= 16 * (1 << 20),
        "all_arms_observed_parent_and_child": all(
            arm["memory"]["peak_process_count"] >= 2 for arm in arms.values()
        ),
        "all_arms_exited_zero": all(arm["returncode"] == 0 for arm in arms.values()),
    }
    result = {
        "schema": "m182-memory-probe-commission-v1",
        "harness_path": str(HARNESS_PATH.relative_to(ROOT)).replace("\\", "/"),
        "harness_sha256": sha256(HARNESS_PATH),
        "mutation_anchors": {
            "allocation": ALLOCATION_ANCHOR,
            "allocation_match_count": ALLOCATION_TEMPLATE.splitlines().count(
                ALLOCATION_ANCHOR
            ),
            "inert": LABEL_ANCHOR,
            "inert_match_count": ALLOCATION_TEMPLATE.splitlines().count(LABEL_ANCHOR),
        },
        "arms": arms,
        "deltas": {
            "allocation_plant_minus_baseline_bytes": allocation_delta,
            "baseline_minus_saving_plant_bytes": saving_delta,
            "absolute_inert_minus_baseline_bytes": inert_delta,
        },
        "checks": checks,
        "status": "COMMISSIONED" if all(checks.values()) else "FAILED",
    }
    write_json(HERE / "probe-commission.json", result)
    print(json.dumps({"peaks": peak, "deltas": result["deltas"], "checks": checks}, indent=2))
    print(result["status"])
    return 0 if result["status"] == "COMMISSIONED" else 1


def copy_cache(source: Path | None, destination: Path) -> None:
    clean_dir(destination)
    if source is None:
        return
    if not source.is_dir():
        raise FileNotFoundError(source)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def run_product(args: argparse.Namespace) -> int:
    harness = load_harness()
    exe = args.exe.resolve()
    if not exe.is_file():
        raise FileNotFoundError(exe)
    name = args.name
    destination = RUNS / f"{name}.tiff"
    record_path = HERE / f"{name}.json"
    cache = CACHE / name
    temp = TEMP / name
    RUNS.mkdir(parents=True, exist_ok=True)
    TEMP.mkdir(parents=True, exist_ok=True)
    copy_cache(args.cache_source.resolve() if args.cache_source else None, cache)
    clean_dir(temp)
    record = harness.run_once(
        exe=exe,
        stack=Path(r"D:\personal\macro\bee-1-cpl"),
        limit=args.limit,
        workers=args.workers,
        destination=destination,
        cache=cache,
        temp=temp,
        flags=["--linear-srgb", "--demosaic"],
        sidecar=None,
        align_off=False,
        fixed_env={},
        required_log_substrings=[
            "strehl stack -- LAPLACIAN MULTI-BAND MERGE (--merge pyramid; THE DEFAULT PATH)",
            "memory plan     :",
            "alignment       : ON (",
            "16-bit RGB, linear sRGB",
            "Full sensor resolution",
        ],
        kind="diagnostic-reproduction",
        repetition=None,
        sweep=None,
        measured_commit=args.commit,
    )
    record["probe"] = {
        "name": name,
        "binary_sha256": sha256(exe),
        "cache_seed": (
            str(args.cache_source.resolve()) if args.cache_source is not None else None
        ),
        "output_removed_after_hash": False,
    }
    if destination.exists():
        destination.unlink()
        record["probe"]["output_removed_after_hash"] = True
    if temp.exists():
        shutil.rmtree(temp)
    write_json(record_path, record)
    memory = record["memory"]
    summary = {
        "name": name,
        "valid": record["valid"],
        "returncode": record["returncode"],
        "limit": args.limit,
        "workers": args.workers,
        "peak_sampled_private_bytes": memory[
            "peak_process_tree_private_committed_bytes"
        ],
        "peak_job_bytes": memory["kernel_job_peak_memory"][
            "peak_job_memory_used_bytes"
        ],
        "wall_seconds": record["wall_seconds"],
        "record": str(record_path),
    }
    print(json.dumps(summary, indent=2))
    return 0 if record["valid"] and record["returncode"] == 0 else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("commission")
    run = sub.add_parser("run")
    run.add_argument("--name", required=True)
    run.add_argument("--exe", type=Path, required=True)
    run.add_argument("--commit", required=True)
    run.add_argument("--limit", type=int, required=True)
    run.add_argument("--workers", type=int, required=True)
    run.add_argument("--cache-source", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    if args.command == "commission":
        return commission()
    if args.command == "run":
        return run_product(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
