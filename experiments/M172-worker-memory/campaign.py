from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import tarfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
HARNESS = ROOT / "experiments" / "m12-scorecard" / "m12-harness.py"
ALLOWED_OUTPUT_ROOT = LANE / "out"
DEFAULT_RECORD = LANE / "results" / "campaign.json"

SCHEMA = "M172-throughput-v1"
PRE_COMMIT = "1a6fd10c94dcb4b780f6af78c46c62a156c39b71"
POST_COMMIT = "a97275817c58e164f75c7cd3d80ca99444a2a145"
FLAGS = ("--merge", "pyramid", "--linear-srgb", "--demosaic")
VERIFICATION_WORKERS = (1, 16)
CPU_INTERVAL_SECONDS = 1.0
CPU_INTERVAL_TOLERANCE_SECONDS = 0.25
HEX40 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9A-F]{64}")

STACKS = {
    "bee-1-cpl": Path(r"D:\personal\macro\bee-1-cpl"),
    "coffee-bean": Path(r"D:\personal\macro\coffee-bean"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def compact_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest().upper()


def run_record_sha256(row: dict[str, Any]) -> str:
    return compact_sha256(
        {key: value for key, value in row.items() if key != "record_sha256"}
    )


def is_within(path: Path, parent: Path) -> bool:
    try:
        common = os.path.commonpath((str(path), str(parent)))
    except ValueError:
        return False
    return os.path.normcase(common) == os.path.normcase(str(parent))


def experiment_relative(path: Path) -> str:
    resolved = path.resolve()
    require(
        is_within(resolved, LANE),
        f"artifact path escapes the M172 experiment: {resolved}",
    )
    return resolved.relative_to(LANE).as_posix()


def repository_relative(path: Path) -> str:
    resolved = path.resolve()
    require(
        is_within(resolved, ROOT),
        f"path escapes the Strehl repository: {resolved}",
    )
    return resolved.relative_to(ROOT).as_posix()


def artifact_path(relative: Any, output_root: Path, label: str) -> Path:
    require(isinstance(relative, str), f"{label} must be a relative path")
    candidate = Path(relative)
    require(not candidate.is_absolute(), f"{label} must be relative: {relative!r}")
    resolved = (LANE / candidate).resolve()
    require(
        is_within(resolved, output_root),
        f"{label} escapes the configured output root: {relative!r}",
    )
    return resolved


def atomic_write(path: Path, campaign: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    campaign["updated_utc"] = utc_now()
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    encoded = (
        json.dumps(campaign, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    with temporary.open("w", encoding="utf-8", newline="\n") as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def git_text(*arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "--no-pager", *arguments],
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"git {subprocess.list2cmdline(list(arguments))} failed with "
            f"{result.returncode}: {detail}"
        )
    return result.stdout.strip()


def exact_commit(value: str, label: str) -> str:
    candidate = value.lower()
    require(
        HEX40.fullmatch(candidate) is not None,
        f"{label} must be a full 40-character commit SHA",
    )
    resolved = git_text("rev-parse", "--verify", f"{candidate}^{{commit}}").lower()
    require(
        resolved == candidate,
        f"{label} did not resolve to the exact requested commit: "
        f"{candidate} -> {resolved}",
    )
    return resolved


def load_harness() -> ModuleType:
    spec = importlib.util.spec_from_file_location("m172_m12_harness", HARNESS)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {HARNESS}")
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def parse_workers(values: list[str]) -> list[int]:
    workers: list[int] = []
    for value in values:
        for component in value.split(","):
            component = component.strip()
            require(component != "", f"invalid empty worker count in {value!r}")
            try:
                worker = int(component)
            except ValueError as error:
                raise RuntimeError(
                    f"worker count must be an integer, got {component!r}"
                ) from error
            require(worker >= 1, f"worker count must be at least 1, got {worker}")
            require(worker not in workers, f"duplicate worker count: {worker}")
            workers.append(worker)
    require(bool(workers), "at least one worker count is required")
    return workers


def make_run_policy(workers: list[int], repetitions: int) -> list[dict[str, Any]]:
    policy: list[dict[str, Any]] = []

    def add(
        kind: str,
        arm: str,
        worker: int,
        repetition: int | None,
        run_id: str,
    ) -> None:
        policy.append(
            {
                "run_id": run_id,
                "kind": kind,
                "arm": arm,
                "workers": worker,
                "repetition": repetition,
                "sequence_index": len(policy),
            }
        )

    for worker in VERIFICATION_WORKERS:
        for arm in ("pre", "post"):
            add(
                "verification",
                arm,
                worker,
                None,
                f"verification-w{worker}-{arm}",
            )
    for worker in workers:
        for arm in ("pre", "post"):
            add("warmup", arm, worker, None, f"warmup-w{worker}-{arm}")
    for repetition in range(1, repetitions + 1):
        for worker in workers:
            for arm in ("pre", "post"):
                add(
                    "timed",
                    arm,
                    worker,
                    repetition,
                    f"timed-r{repetition:02d}-w{worker}-{arm}",
                )
    return policy


def expected_protocol(
    *,
    pre_commit: str,
    post_commit: str,
    stack_label: str,
    output_root: Path,
    limit: int,
    workers: list[int],
    repetitions: int,
    policy: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "commits": {"pre": pre_commit, "post": post_commit},
        "stack": {
            "label": stack_label,
            "path": str(STACKS[stack_label]),
        },
        "limit": limit,
        "workers": workers,
        "verification_workers": list(VERIFICATION_WORKERS),
        "repetitions": repetitions,
        "flags": list(FLAGS),
        "alignment": {
            "enabled": False,
            "environment": {"STREHL_ALIGN": "0"},
        },
        "cpu_interval_seconds": CPU_INTERVAL_SECONDS,
        "cpu_interval_tolerance_seconds": CPU_INTERVAL_TOLERANCE_SECONDS,
        "cpu_semantics": (
            "Windows Processor(_Total): 100 * delta(system busy time) / "
            "delta(system total time), sampled with GetSystemTimes; complete "
            "one-second samples whose endpoints fall within raw wall_seconds"
        ),
        "load_gating": False,
        "automatic_retries": False,
        "warmups_per_arm_worker": 1,
        "warmups_excluded_from_ratios": True,
        "wall_seconds_interpretation": (
            "raw evidence only; this campaign makes no absolute performance claim"
        ),
        "timed_pairing": (
            "for each repetition, for each worker count in listed order, run "
            "pre then post adjacently"
        ),
        "sequence_index_base": 0,
        "ordered_run_policy": policy,
        "artifact_output_root": experiment_relative(output_root),
        "implementation": {
            "campaign": repository_relative(Path(__file__)),
            "campaign_sha256": sha256_file(Path(__file__)),
            "harness": repository_relative(HARNESS),
            "harness_sha256": sha256_file(HARNESS),
            "process_monitor": (
                "m12-harness.py run_once with Windows Job Object accounting"
            ),
            "tiff_witness": "m12-harness.py run_once/tiff_witness",
        },
    }


def new_campaign(protocol: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    return {
        "schema": SCHEMA,
        "created_utc": now,
        "updated_utc": now,
        "protocol": protocol,
        "builds": {},
        "verification": [],
        "verification_outcome": None,
        "warmups": [],
        "timed_runs": [],
    }


def collection_for_kind(kind: str) -> str:
    return {
        "verification": "verification",
        "warmup": "warmups",
        "timed": "timed_runs",
    }[kind]


def validate_campaign_structure(
    campaign: dict[str, Any],
    protocol: dict[str, Any],
    policy: list[dict[str, Any]],
) -> None:
    require(campaign.get("schema") == SCHEMA, "campaign schema does not agree")
    require(
        campaign.get("protocol") == protocol,
        "existing campaign protocol does not agree with this invocation",
    )
    builds = campaign.get("builds")
    require(isinstance(builds, dict), "campaign builds must be an object")
    require(
        set(builds).issubset({"pre", "post"}),
        "campaign contains an unknown build arm",
    )

    all_ids: list[str] = []
    for kind in ("verification", "warmup", "timed"):
        collection = collection_for_kind(kind)
        rows = campaign.get(collection)
        require(isinstance(rows, list), f"campaign {collection} must be a list")
        expected_ids = [
            plan["run_id"] for plan in policy if plan["kind"] == kind
        ]
        actual_ids = []
        for row in rows:
            require(isinstance(row, dict), f"{collection} contains a non-object")
            run_id = row.get("run_id")
            require(isinstance(run_id, str), f"{collection} row has no run_id")
            actual_ids.append(run_id)
        require(
            actual_ids == expected_ids[: len(actual_ids)],
            f"{collection} is not an ordered prefix of the registered policy",
        )
        all_ids.extend(actual_ids)

    require(
        len(all_ids) == len(set(all_ids)),
        "campaign contains duplicate run_id values",
    )
    verification_count = len(campaign["verification"])
    warmup_count = len(campaign["warmups"])
    verification_total = sum(
        plan["kind"] == "verification" for plan in policy
    )
    warmup_total = sum(plan["kind"] == "warmup" for plan in policy)
    if warmup_count:
        require(
            verification_count == verification_total,
            "warmups exist before all verification runs completed",
        )
        outcome = campaign.get("verification_outcome")
        require(
            isinstance(outcome, dict) and outcome.get("valid") is True,
            "warmups exist without a passing verification outcome",
        )
    if campaign["timed_runs"]:
        require(
            warmup_count == warmup_total,
            "timed runs exist before all warmups completed",
        )
    outcome = campaign.get("verification_outcome")
    require(
        outcome is None or isinstance(outcome, dict),
        "verification_outcome must be null or an object",
    )
    if outcome is not None:
        require(
            verification_count == verification_total,
            "verification outcome exists before verification completed",
        )


def build_paths(output_root: Path, arm: str) -> dict[str, Path]:
    root = output_root / "builds" / arm
    target = root / "target"
    return {
        "root": root,
        "archive": root / "source.tar",
        "source": root / "source",
        "target": target,
        "target_binary": target / "release" / "strehl.exe",
        "binary": root / "bin" / "strehl.exe",
        "log": root / "build.log",
    }


def version_output(binary: Path, commit: str) -> str:
    result = subprocess.run(
        [str(binary), "--version"],
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"{binary} --version failed with {result.returncode}: {detail}"
        )
    output = "\n".join(
        part.rstrip() for part in (result.stdout, result.stderr) if part.rstrip()
    )
    require(output != "", f"{binary} --version produced no output")
    require(
        commit in output,
        f"{binary} --version does not contain full commit {commit}: {output!r}",
    )
    return output


def run_git_archive(commit: str, archive: Path) -> None:
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
    result = subprocess.run(
        command,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"{subprocess.list2cmdline(command)} failed with "
            f"{result.returncode}: {detail}"
        )
    require(archive.is_file(), f"git archive did not create {archive}")


def build_arm(
    *,
    arm: str,
    commit: str,
    tree_hash: str,
    output_root: Path,
) -> dict[str, Any]:
    paths = build_paths(output_root, arm)
    if paths["root"].exists():
        shutil.rmtree(paths["root"])
    paths["source"].mkdir(parents=True)
    print(f"[build] {arm}: archiving {commit}", flush=True)
    run_git_archive(commit, paths["archive"])
    archive_sha256 = sha256_file(paths["archive"])
    archive_bytes = paths["archive"].stat().st_size
    with tarfile.open(paths["archive"], "r") as bundle:
        bundle.extractall(paths["source"], filter="data")
    require(
        (paths["source"] / "Cargo.toml").is_file()
        and (paths["source"] / "Cargo.lock").is_file(),
        f"archive for {arm} did not contain Cargo.toml and Cargo.lock",
    )

    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(paths["target"].resolve())
    env["CARGO_INCREMENTAL"] = "0"
    env["STREHL_BUILD_ID"] = commit
    env["CARGO_TERM_COLOR"] = "never"
    command = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--package",
        "strehl-cli",
        "--manifest-path",
        str(paths["source"] / "Cargo.toml"),
    ]
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    print(f"[build] {arm}: cargo build --release --locked", flush=True)
    with paths["log"].open("w", encoding="utf-8", newline="\n") as log:
        log.write(f"source_commit={commit}\n")
        log.write(f"CARGO_TARGET_DIR={env['CARGO_TARGET_DIR']}\n")
        log.write(f"CARGO_INCREMENTAL={env['CARGO_INCREMENTAL']}\n")
        log.write(f"STREHL_BUILD_ID={env['STREHL_BUILD_ID']}\n")
        log.write("$ " + subprocess.list2cmdline(command) + "\n\n")
        log.flush()
        result = subprocess.run(
            command,
            cwd=paths["source"],
            env=env,
            text=True,
            errors="replace",
            stdout=log,
            stderr=subprocess.STDOUT,
        )
    if result.returncode:
        tail = paths["log"].read_text(
            encoding="utf-8", errors="replace"
        )[-6000:]
        raise RuntimeError(
            f"{arm} cargo build failed with {result.returncode}; "
            f"log: {paths['log']}\n{tail}"
        )
    require(
        paths["target_binary"].is_file(),
        f"build completed but {paths['target_binary']} is missing",
    )
    target_sha256 = sha256_file(paths["target_binary"])
    paths["binary"].parent.mkdir(parents=True)
    shutil.copy2(paths["target_binary"], paths["binary"])
    binary_sha256 = sha256_file(paths["binary"])
    require(
        binary_sha256 == target_sha256,
        f"copied {arm} binary does not match the cargo output",
    )
    version = version_output(paths["binary"], commit)
    return {
        "valid": True,
        "arm": arm,
        "commit": commit,
        "tree_hash": tree_hash,
        "source_method": "git archive",
        "working_tree_source_used": False,
        "archive_location": experiment_relative(paths["archive"]),
        "archive_sha256": archive_sha256,
        "archive_bytes": archive_bytes,
        "source_location": experiment_relative(paths["source"]),
        "target_location": experiment_relative(paths["target"]),
        "build_command": command,
        "build_environment": {
            "CARGO_TARGET_DIR": env["CARGO_TARGET_DIR"],
            "CARGO_INCREMENTAL": env["CARGO_INCREMENTAL"],
            "STREHL_BUILD_ID": env["STREHL_BUILD_ID"],
        },
        "build_log_location": experiment_relative(paths["log"]),
        "build_log_sha256": sha256_file(paths["log"]),
        "target_binary_location": experiment_relative(paths["target_binary"]),
        "target_binary_sha256": target_sha256,
        "binary_location": experiment_relative(paths["binary"]),
        "binary_sha256": binary_sha256,
        "bytes": paths["binary"].stat().st_size,
        "version_output": version,
        "completed_utc": utc_now(),
    }


def validate_build_record(
    *,
    record: dict[str, Any],
    arm: str,
    commit: str,
    tree_hash: str,
    output_root: Path,
) -> None:
    paths = build_paths(output_root, arm)
    exact = {
        "valid": True,
        "arm": arm,
        "commit": commit,
        "tree_hash": tree_hash,
        "source_method": "git archive",
        "working_tree_source_used": False,
        "archive_location": experiment_relative(paths["archive"]),
        "source_location": experiment_relative(paths["source"]),
        "target_location": experiment_relative(paths["target"]),
        "build_log_location": experiment_relative(paths["log"]),
        "target_binary_location": experiment_relative(paths["target_binary"]),
        "binary_location": experiment_relative(paths["binary"]),
    }
    for key, expected in exact.items():
        require(
            record.get(key) == expected,
            f"{arm} build provenance disagrees at {key}",
        )

    archive = artifact_path(
        record["archive_location"], output_root, f"{arm} archive_location"
    )
    source = artifact_path(
        record["source_location"], output_root, f"{arm} source_location"
    )
    build_log = artifact_path(
        record["build_log_location"], output_root, f"{arm} build_log_location"
    )
    target_binary = artifact_path(
        record["target_binary_location"],
        output_root,
        f"{arm} target_binary_location",
    )
    binary = artifact_path(
        record["binary_location"], output_root, f"{arm} binary_location"
    )
    require(archive.is_file(), f"{arm} source archive is missing")
    require(source.is_dir(), f"{arm} extracted source is missing")
    require(
        (source / "Cargo.toml").is_file() and (source / "Cargo.lock").is_file(),
        f"{arm} extracted source is incomplete",
    )
    require(build_log.is_file(), f"{arm} build log is missing")
    require(target_binary.is_file(), f"{arm} cargo output binary is missing")
    require(binary.is_file(), f"{arm} copied binary is missing")

    require(
        record.get("archive_bytes") == archive.stat().st_size,
        f"{arm} source archive size disagrees",
    )
    require(
        SHA256.fullmatch(str(record.get("archive_sha256"))) is not None
        and sha256_file(archive) == record["archive_sha256"],
        f"{arm} source archive hash disagrees",
    )
    require(
        SHA256.fullmatch(str(record.get("build_log_sha256"))) is not None
        and sha256_file(build_log) == record["build_log_sha256"],
        f"{arm} build log hash disagrees",
    )
    target_sha256 = sha256_file(target_binary)
    binary_sha256 = sha256_file(binary)
    require(
        target_sha256 == record.get("target_binary_sha256"),
        f"{arm} cargo output binary hash disagrees",
    )
    require(
        binary_sha256 == record.get("binary_sha256"),
        f"{arm} copied binary hash disagrees",
    )
    require(
        target_sha256 == binary_sha256,
        f"{arm} copied binary no longer matches the cargo output",
    )
    require(
        record.get("bytes") == binary.stat().st_size,
        f"{arm} copied binary size disagrees",
    )
    require(
        record.get("build_environment")
        == {
            "CARGO_TARGET_DIR": str(paths["target"].resolve()),
            "CARGO_INCREMENTAL": "0",
            "STREHL_BUILD_ID": commit,
        },
        f"{arm} build environment provenance disagrees",
    )
    expected_command = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--package",
        "strehl-cli",
        "--manifest-path",
        str(paths["source"] / "Cargo.toml"),
    ]
    require(
        record.get("build_command") == expected_command,
        f"{arm} build command provenance disagrees",
    )
    observed_version = version_output(binary, commit)
    require(
        observed_version == record.get("version_output"),
        f"{arm} --version output changed",
    )


def ensure_builds(
    *,
    campaign: dict[str, Any],
    record_path: Path,
    output_root: Path,
    commits: dict[str, str],
    trees: dict[str, str],
) -> dict[str, dict[str, Any]]:
    builds = campaign["builds"]
    for arm in ("pre", "post"):
        existing = builds.get(arm)
        if existing is not None:
            require(isinstance(existing, dict), f"{arm} build record is not an object")
            validate_build_record(
                record=existing,
                arm=arm,
                commit=commits[arm],
                tree_hash=trees[arm],
                output_root=output_root,
            )
            print(
                f"[resume] build {arm}: {existing['binary_sha256'][:16]}",
                flush=True,
            )
            continue
        downstream = [
            row["run_id"]
            for collection in ("verification", "warmups", "timed_runs")
            for row in campaign[collection]
            if row.get("arm") == arm
        ]
        require(
            not downstream,
            f"{arm} build provenance is missing but runs already reference it",
        )
        builds[arm] = build_arm(
            arm=arm,
            commit=commits[arm],
            tree_hash=trees[arm],
            output_root=output_root,
        )
        atomic_write(record_path, campaign)
        print(
            f"[build] {arm}: {builds[arm]['binary_sha256'][:16]}",
            flush=True,
        )
    return builds


class HostCpuSampler:
    def __init__(
        self,
        system_times: Callable[[], dict[str, int]],
        interval_seconds: float,
    ) -> None:
        self._system_times = system_times
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start = 0.0
        self._previous: dict[str, int] | None = None
        self._error: OSError | RuntimeError | None = None
        self.trace: list[dict[str, float]] = []

    def start(self) -> None:
        require(self._thread is None, "CPU sampler was started twice")
        self._previous = self._system_times()
        self._start = time.perf_counter()
        self._thread = threading.Thread(
            target=self._sample,
            name="m172-host-cpu",
        )
        self._thread.start()

    def _sample(self) -> None:
        previous = self._previous
        if previous is None:
            self._error = RuntimeError("CPU sampler has no initial sample")
            return
        deadline = self._start + self._interval
        while True:
            delay = max(0.0, deadline - time.perf_counter())
            if self._stop.wait(delay):
                return
            sampled_at = time.perf_counter()
            try:
                current = self._system_times()
            except OSError as error:
                self._error = error
                return
            total = current["total_100ns"] - previous["total_100ns"]
            busy = current["busy_100ns"] - previous["busy_100ns"]
            if total <= 0 or busy < 0 or busy > total:
                self._error = RuntimeError(
                    f"invalid GetSystemTimes delta: total={total}, busy={busy}"
                )
                return
            self.trace.append(
                {
                    "elapsed_seconds": sampled_at - self._start,
                    "processor_total_percent": 100.0 * busy / total,
                }
            )
            previous = current
            deadline = sampled_at + self._interval

    def stop(self) -> str | None:
        thread = self._thread
        require(thread is not None, "CPU sampler was not started")
        self._stop.set()
        thread.join()
        if self._error is not None:
            return f"whole-host CPU sampling failed: {self._error}"
        return None


def worker_semantics_substrings(arm: str, workers: int) -> list[str]:
    if arm == "pre":
        return [
            f"memory plan     : {workers} workers x",
            f"{workers} workers)",
        ]
    return [
        "canonical chunks, 1 reusable frame worker",
        f"1 retained + 1 scratch accumulator, {workers} execution threads",
        "changes threads, never arithmetic.",
        f"{workers} execution threads)",
    ]


def required_stderr_substrings(arm: str, workers: int) -> list[str]:
    return [
        "strehl stack -- LAPLACIAN MULTI-BAND MERGE "
        "(--merge pyramid; THE DEFAULT PATH)",
        "alignment       : OFF",
        "16-bit RGB, linear sRGB",
        "Full sensor resolution",
        *worker_semantics_substrings(arm, workers),
    ]


def run_paths(
    output_root: Path,
    plan: dict[str, Any],
) -> dict[str, Path]:
    destination = output_root / "runs" / f"{plan['run_id']}.tiff"
    if plan["kind"] == "verification":
        cache = output_root / "cache" / "verification" / plan["run_id"]
    else:
        cache = (
            output_root
            / "cache"
            / "throughput"
            / plan["arm"]
            / f"w{plan['workers']}"
        )
    return {
        "destination": destination,
        "stdout": destination.with_suffix(destination.suffix + ".stdout.log"),
        "stderr": destination.with_suffix(destination.suffix + ".stderr.log"),
        "cache": cache,
        "temp": output_root / "temp" / plan["run_id"],
    }


def prepare_absent_run(paths: dict[str, Path], kind: str) -> None:
    for key in ("destination", "stdout", "stderr"):
        paths[key].unlink(missing_ok=True)
    if paths["temp"].exists():
        shutil.rmtree(paths["temp"])
    if kind in ("verification", "warmup") and paths["cache"].exists():
        shutil.rmtree(paths["cache"])


def stderr_witness(
    stderr_text: str,
    required: list[str],
) -> list[dict[str, str | None]]:
    lines = stderr_text.splitlines()
    return [
        {
            "substring": substring,
            "line": next((line for line in lines if substring in line), None),
        }
        for substring in required
    ]


def cpu_trace_quality_error(
    trace: list[dict[str, float]],
    wall_seconds: float,
) -> str | None:
    if not trace:
        return "whole-host CPU trace has no complete one-second sample"
    previous = 0.0
    lower = CPU_INTERVAL_SECONDS - CPU_INTERVAL_TOLERANCE_SECONDS
    upper = CPU_INTERVAL_SECONDS + CPU_INTERVAL_TOLERANCE_SECONDS
    for index, sample in enumerate(trace):
        elapsed = sample["elapsed_seconds"]
        gap = elapsed - previous
        if not lower <= gap <= upper:
            return (
                f"whole-host CPU sample {index} interval was {gap:.6f}s, "
                f"expected {CPU_INTERVAL_SECONDS:.3f}s +/- "
                f"{CPU_INTERVAL_TOLERANCE_SECONDS:.3f}s"
            )
        if elapsed > wall_seconds:
            return (
                f"whole-host CPU sample {index} endpoint {elapsed:.6f}s "
                f"exceeds raw wall_seconds {wall_seconds:.6f}s"
            )
        previous = elapsed
    uncovered_tail = wall_seconds - previous
    if uncovered_tail > upper:
        return (
            f"whole-host CPU trace leaves {uncovered_tail:.6f}s at the end "
            f"of raw wall_seconds without a complete sample"
        )
    return None


def summarize_run(
    *,
    raw: dict[str, Any],
    trace: list[dict[str, float]],
    plan: dict[str, Any],
    build: dict[str, Any],
    paths: dict[str, Path],
    required: list[str],
    cpu_sampler_error: str | None,
) -> dict[str, Any]:
    stderr_text = paths["stderr"].read_text(
        encoding="utf-8", errors="replace"
    )
    failures = list(raw.get("invalid_reasons", []))
    if cpu_sampler_error is not None:
        failures.append(cpu_sampler_error)
    trace_error = cpu_trace_quality_error(trace, raw["wall_seconds"])
    if trace_error is not None:
        failures.append(trace_error)
    if raw.get("binary", {}).get("sha256") != build["binary_sha256"]:
        failures.append("harness binary hash does not match registered build")
    if raw.get("environment", {}).get("STREHL_PYRAMID_WORKERS") != str(
        plan["workers"]
    ):
        failures.append("harness did not record the requested worker count")
    if raw.get("environment", {}).get("STREHL_ALIGN") != "0":
        failures.append("harness did not record alignment OFF")
    if build["commit"] not in str(raw.get("software", "")):
        failures.append("TIFF Software witness does not contain source commit")

    percentages = [sample["processor_total_percent"] for sample in trace]
    memory = raw["memory"]
    kernel_peak = memory["kernel_job_peak_memory"]
    summary = {
        "run_id": plan["run_id"],
        "kind": plan["kind"],
        "arm": plan["arm"],
        "source_commit": build["commit"],
        "binary_sha256": build["binary_sha256"],
        "workers": plan["workers"],
        "repetition": plan["repetition"],
        "sequence_index": plan["sequence_index"],
        "started_utc": raw["started_utc"],
        "completed_utc": raw["completed_utc"],
        "argv": raw["argv"],
        "environment": {
            "STREHL_PYRAMID_WORKERS": raw["environment"].get(
                "STREHL_PYRAMID_WORKERS"
            ),
            "STREHL_ALIGN": raw["environment"].get("STREHL_ALIGN"),
            "STREHL_CACHE_DIR": raw["environment"].get("STREHL_CACHE_DIR"),
            "TEMP": raw["environment"].get("TEMP"),
            "TMP": raw["environment"].get("TMP"),
        },
        "wall_seconds": raw["wall_seconds"],
        "cpu_trace": trace,
        "cpu_sampler_error": cpu_sampler_error,
        "processor_total_percent_mean": (
            statistics.fmean(percentages) if percentages else None
        ),
        "processor_total_percent_min": min(percentages) if percentages else None,
        "processor_total_percent_max": max(percentages) if percentages else None,
        "tiff_sha256": raw.get("output_sha256"),
        "pixel_sha256": raw.get("pixel_sha256"),
        "tiff_bytes": raw.get("output_bytes"),
        "tiff_shape": raw.get("shape"),
        "tiff_dtype": raw.get("dtype"),
        "tiff_bits_per_sample": raw.get("bits_per_sample"),
        "tiff_samples_per_pixel": raw.get("samples_per_pixel"),
        "tiff_software": raw.get("software"),
        "memory_peaks": {
            "peak_process_tree_private_committed_bytes": memory[
                "peak_process_tree_private_committed_bytes"
            ],
            "peak_process_tree_working_set_bytes": memory[
                "peak_process_tree_working_set_bytes"
            ],
            "peak_process_tree_page_fault_count": memory[
                "peak_process_tree_page_fault_count"
            ],
            "peak_process_count": memory["peak_process_count"],
            "kernel_job_peak_process_memory_used_bytes": kernel_peak[
                "peak_process_memory_used_bytes"
            ],
            "kernel_job_peak_memory_used_bytes": kernel_peak[
                "peak_job_memory_used_bytes"
            ],
        },
        "memory_monitor": {
            "sample_interval_ms": memory["sample_interval_ms"],
            "sample_count": memory["sample_count"],
            "missed_intervals": memory["missed_intervals"],
        },
        "stdout_log": experiment_relative(paths["stdout"]),
        "stdout_log_sha256": sha256_file(paths["stdout"]),
        "stderr_log": experiment_relative(paths["stderr"]),
        "stderr_log_sha256": sha256_file(paths["stderr"]),
        "stderr_witness": stderr_witness(stderr_text, required),
        "return_code": raw["returncode"],
        "valid": bool(raw.get("valid")) and not failures,
        "invalid_reasons": failures,
    }
    summary["record_sha256"] = run_record_sha256(summary)
    return summary


def run_one(
    *,
    harness: ModuleType,
    plan: dict[str, Any],
    build: dict[str, Any],
    stack: Path,
    limit: int,
    output_root: Path,
    campaign: dict[str, Any],
    record_path: Path,
) -> dict[str, Any]:
    paths = run_paths(output_root, plan)
    prepare_absent_run(paths, plan["kind"])
    required = required_stderr_substrings(plan["arm"], plan["workers"])
    binary = artifact_path(
        build["binary_location"],
        output_root,
        f"{plan['arm']} binary_location",
    )
    sampler = HostCpuSampler(harness.system_times, CPU_INTERVAL_SECONDS)
    print(
        f"[run {plan['sequence_index']:02d}] {plan['run_id']} starting",
        flush=True,
    )
    sampler.start()
    try:
        cpu_sampler_error: str | None = None
        try:
            raw = harness.run_once(
                exe=binary,
                stack=stack,
                limit=limit,
                workers=plan["workers"],
                destination=paths["destination"],
                cache=paths["cache"],
                temp=paths["temp"],
                flags=list(FLAGS),
                sidecar=None,
                align_off=True,
                fixed_env={},
                required_log_substrings=required,
                kind=plan["kind"],
                repetition=plan["repetition"],
                sweep="M172-interleaved-throughput",
                measured_commit=build["commit"],
                external_busy_max=float("inf"),
            )
        finally:
            cpu_sampler_error = sampler.stop()
        process_trace = [
            sample
            for sample in sampler.trace
            if sample["elapsed_seconds"] <= raw["wall_seconds"]
        ]
        summary = summarize_run(
            raw=raw,
            trace=process_trace,
            plan=plan,
            build=build,
            paths=paths,
            required=required,
            cpu_sampler_error=cpu_sampler_error,
        )
    finally:
        paths["destination"].unlink(missing_ok=True)

    campaign[collection_for_kind(plan["kind"])].append(summary)
    atomic_write(record_path, campaign)
    mean = summary["processor_total_percent_mean"]
    mean_text = f"{mean:.1f}%" if isinstance(mean, float) else "n/a"
    print(
        f"[run {plan['sequence_index']:02d}] {plan['run_id']} "
        f"valid={summary['valid']} wall(raw)={summary['wall_seconds']:.3f}s "
        f"cpu(mean)={mean_text}",
        flush=True,
    )
    if not summary["valid"]:
        raise RuntimeError(
            f"{plan['run_id']} failed: {summary['invalid_reasons']}"
        )
    return summary


def validate_hash(value: Any, label: str) -> None:
    require(
        isinstance(value, str) and SHA256.fullmatch(value) is not None,
        f"{label} is not an uppercase SHA-256",
    )


def validate_utc_timestamp(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} is not a timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise RuntimeError(f"{label} is not an ISO-8601 timestamp") from error
    require(parsed.tzinfo is not None, f"{label} has no timezone")
    return parsed


def validate_existing_run(
    *,
    row: dict[str, Any],
    plan: dict[str, Any],
    build: dict[str, Any],
    stack: Path,
    limit: int,
    output_root: Path,
) -> None:
    validate_hash(
        row.get("record_sha256"), f"{plan['run_id']} compact record hash"
    )
    require(
        run_record_sha256(row) == row["record_sha256"],
        f"{plan['run_id']} compact record hash disagrees",
    )
    exact = {
        "run_id": plan["run_id"],
        "kind": plan["kind"],
        "arm": plan["arm"],
        "source_commit": build["commit"],
        "binary_sha256": build["binary_sha256"],
        "workers": plan["workers"],
        "repetition": plan["repetition"],
        "sequence_index": plan["sequence_index"],
        "return_code": 0,
        "valid": True,
    }
    for key, expected in exact.items():
        require(
            row.get(key) == expected,
            f"{plan['run_id']} disagrees at {key}",
        )
    require(
        row.get("invalid_reasons") == [],
        f"{plan['run_id']} retains invalid reasons",
    )
    require(
        row.get("cpu_sampler_error") is None,
        f"{plan['run_id']} retains a CPU sampler error",
    )
    started = validate_utc_timestamp(
        row.get("started_utc"), f"{plan['run_id']} started_utc"
    )
    completed = validate_utc_timestamp(
        row.get("completed_utc"), f"{plan['run_id']} completed_utc"
    )
    require(
        completed >= started,
        f"{plan['run_id']} completed before it started",
    )
    require(
        isinstance(row.get("wall_seconds"), (int, float))
        and not isinstance(row["wall_seconds"], bool)
        and math.isfinite(row["wall_seconds"])
        and row["wall_seconds"] > 0,
        f"{plan['run_id']} has invalid wall_seconds",
    )
    validate_hash(row.get("tiff_sha256"), f"{plan['run_id']} TIFF hash")
    validate_hash(row.get("pixel_sha256"), f"{plan['run_id']} pixel hash")
    require(
        isinstance(row.get("tiff_bytes"), int)
        and not isinstance(row["tiff_bytes"], bool)
        and row["tiff_bytes"] > 0,
        f"{plan['run_id']} has invalid TIFF byte count",
    )
    shape = row.get("tiff_shape")
    require(
        isinstance(shape, list)
        and len(shape) == 3
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value > 0
            for value in shape
        ),
        f"{plan['run_id']} has invalid TIFF shape",
    )
    require(
        row.get("tiff_dtype") == "uint16"
        and row.get("tiff_bits_per_sample") == 16
        and row.get("tiff_samples_per_pixel") == 3,
        f"{plan['run_id']} TIFF witness is not 16-bit RGB",
    )
    require(
        isinstance(row.get("tiff_software"), str)
        and build["commit"] in row["tiff_software"],
        f"{plan['run_id']} TIFF Software witness lost its commit",
    )

    trace = row.get("cpu_trace")
    require(
        isinstance(trace, list) and bool(trace),
        f"{plan['run_id']} has no CPU trace",
    )
    percentages: list[float] = []
    previous_elapsed = 0.0
    for index, sample in enumerate(trace):
        require(
            isinstance(sample, dict),
            f"{plan['run_id']} CPU sample {index} is not an object",
        )
        elapsed = sample.get("elapsed_seconds")
        percent = sample.get("processor_total_percent")
        require(
            isinstance(elapsed, (int, float))
            and not isinstance(elapsed, bool)
            and math.isfinite(elapsed)
            and elapsed > previous_elapsed,
            f"{plan['run_id']} CPU sample {index} has invalid elapsed time",
        )
        require(
            isinstance(percent, (int, float))
            and not isinstance(percent, bool)
            and math.isfinite(percent)
            and 0.0 <= percent <= 100.000001,
            f"{plan['run_id']} CPU sample {index} has invalid percent",
        )
        previous_elapsed = float(elapsed)
        percentages.append(float(percent))
    trace_error = cpu_trace_quality_error(trace, float(row["wall_seconds"]))
    require(
        trace_error is None,
        f"{plan['run_id']} CPU trace is invalid: {trace_error}",
    )
    recomputed = {
        "processor_total_percent_mean": statistics.fmean(percentages),
        "processor_total_percent_min": min(percentages),
        "processor_total_percent_max": max(percentages),
    }
    for key, expected in recomputed.items():
        actual = row.get(key)
        require(
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isclose(float(actual), expected, rel_tol=1e-12, abs_tol=1e-12),
            f"{plan['run_id']} {key} is not the recomputed trace statistic",
        )

    memory_peaks = row.get("memory_peaks")
    require(
        isinstance(memory_peaks, dict),
        f"{plan['run_id']} has no memory peaks",
    )
    required_peaks = {
        "peak_process_tree_private_committed_bytes",
        "peak_process_tree_working_set_bytes",
        "peak_process_tree_page_fault_count",
        "peak_process_count",
        "kernel_job_peak_process_memory_used_bytes",
        "kernel_job_peak_memory_used_bytes",
    }
    for key in required_peaks:
        value = memory_peaks.get(key)
        require(
            isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0,
            f"{plan['run_id']} has invalid memory peak {key}",
        )
    memory_monitor = row.get("memory_monitor")
    require(
        isinstance(memory_monitor, dict)
        and isinstance(memory_monitor.get("sample_interval_ms"), (int, float))
        and not isinstance(memory_monitor["sample_interval_ms"], bool)
        and math.isfinite(memory_monitor["sample_interval_ms"])
        and memory_monitor["sample_interval_ms"] > 0
        and isinstance(memory_monitor.get("sample_count"), int)
        and not isinstance(memory_monitor["sample_count"], bool)
        and memory_monitor["sample_count"] > 0
        and isinstance(memory_monitor.get("missed_intervals"), int)
        and not isinstance(memory_monitor["missed_intervals"], bool)
        and memory_monitor["missed_intervals"] >= 0,
        f"{plan['run_id']} memory monitor record is incomplete",
    )

    paths = run_paths(output_root, plan)
    require(
        not paths["destination"].exists(),
        f"{plan['run_id']} retained a TIFF that should have been deleted",
    )
    require(paths["cache"].is_dir(), f"{plan['run_id']} cache directory is missing")
    require(paths["temp"].is_dir(), f"{plan['run_id']} temp directory is missing")
    stdout = artifact_path(
        row.get("stdout_log"), output_root, f"{plan['run_id']} stdout_log"
    )
    stderr = artifact_path(
        row.get("stderr_log"), output_root, f"{plan['run_id']} stderr_log"
    )
    require(
        stdout == paths["stdout"].resolve() and stderr == paths["stderr"].resolve(),
        f"{plan['run_id']} log locations disagree",
    )
    require(stdout.is_file(), f"{plan['run_id']} stdout log is missing")
    require(stderr.is_file(), f"{plan['run_id']} stderr log is missing")
    validate_hash(
        row.get("stdout_log_sha256"), f"{plan['run_id']} stdout log hash"
    )
    validate_hash(
        row.get("stderr_log_sha256"), f"{plan['run_id']} stderr log hash"
    )
    require(
        sha256_file(stdout) == row["stdout_log_sha256"],
        f"{plan['run_id']} stdout log hash disagrees",
    )
    require(
        sha256_file(stderr) == row["stderr_log_sha256"],
        f"{plan['run_id']} stderr log hash disagrees",
    )

    required = required_stderr_substrings(plan["arm"], plan["workers"])
    witness = row.get("stderr_witness")
    require(
        isinstance(witness, list) and len(witness) == len(required),
        f"{plan['run_id']} stderr witness is incomplete",
    )
    stderr_lines = stderr.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    for index, substring in enumerate(required):
        item = witness[index]
        require(
            isinstance(item, dict) and item.get("substring") == substring,
            f"{plan['run_id']} stderr witness {index} disagrees",
        )
        line = item.get("line")
        require(
            isinstance(line, str)
            and line in stderr_lines
            and substring in line,
            f"{plan['run_id']} stderr lacks {substring!r}",
        )

    binary = artifact_path(
        build["binary_location"],
        output_root,
        f"{plan['arm']} binary_location",
    )
    expected_argv = [
        str(binary.resolve()),
        "stack",
        str(stack.resolve()),
        "--limit",
        str(limit),
        "--out",
        str(paths["destination"].resolve()),
        *FLAGS,
    ]
    require(
        row.get("argv") == expected_argv,
        f"{plan['run_id']} command line disagrees",
    )
    environment = row.get("environment")
    expected_environment = {
        "STREHL_PYRAMID_WORKERS": str(plan["workers"]),
        "STREHL_ALIGN": "0",
        "STREHL_CACHE_DIR": str(paths["cache"].resolve()),
        "TEMP": str(paths["temp"].resolve()),
        "TMP": str(paths["temp"].resolve()),
    }
    require(
        environment == expected_environment,
        f"{plan['run_id']} worker/alignment environment disagrees",
    )


def validate_existing_runs(
    *,
    campaign: dict[str, Any],
    policy: list[dict[str, Any]],
    builds: dict[str, dict[str, Any]],
    stack: Path,
    limit: int,
    output_root: Path,
) -> None:
    plans = {plan["run_id"]: plan for plan in policy}
    for collection in ("verification", "warmups", "timed_runs"):
        for row in campaign[collection]:
            plan = plans[row["run_id"]]
            validate_existing_run(
                row=row,
                plan=plan,
                build=builds[plan["arm"]],
                stack=stack,
                limit=limit,
                output_root=output_root,
            )


def verification_outcome(campaign: dict[str, Any]) -> dict[str, Any]:
    rows = campaign["verification"]
    require(
        len(rows) == 2 * len(VERIFICATION_WORKERS),
        "verification outcome requested before all four runs completed",
    )
    by_arm_worker = {
        (row["arm"], row["workers"]): row["pixel_sha256"] for row in rows
    }
    pre_differ = (
        by_arm_worker[("pre", 1)] != by_arm_worker[("pre", 16)]
    )
    post_match = (
        by_arm_worker[("post", 1)] == by_arm_worker[("post", 16)]
    )
    return {
        "pre_pixel_hashes": {
            "w1": by_arm_worker[("pre", 1)],
            "w16": by_arm_worker[("pre", 16)],
        },
        "post_pixel_hashes": {
            "w1": by_arm_worker[("post", 1)],
            "w16": by_arm_worker[("post", 16)],
        },
        "pre_worker_hashes_differ": pre_differ,
        "post_worker_hashes_match": post_match,
        "worker_semantics_verified_in_stderr": all(
            row["valid"] for row in rows
        ),
        "valid": pre_differ and post_match and all(row["valid"] for row in rows),
    }


def run_registered_plans(
    *,
    kind: str,
    harness: ModuleType,
    policy: list[dict[str, Any]],
    builds: dict[str, dict[str, Any]],
    stack: Path,
    limit: int,
    output_root: Path,
    campaign: dict[str, Any],
    record_path: Path,
) -> None:
    collection = collection_for_kind(kind)
    existing = {row["run_id"] for row in campaign[collection]}
    for plan in policy:
        if plan["kind"] != kind:
            continue
        if plan["run_id"] in existing:
            print(f"[resume] run {plan['run_id']}: valid", flush=True)
            continue
        run_one(
            harness=harness,
            plan=plan,
            build=builds[plan["arm"]],
            stack=stack,
            limit=limit,
            output_root=output_root,
            campaign=campaign,
            record_path=record_path,
        )
        existing.add(plan["run_id"])


def print_final(
    record_path: Path,
    output_root: Path,
    builds: dict[str, dict[str, Any]],
) -> None:
    print(f"Campaign record: {record_path}", flush=True)
    print(f"Artifact root:   {output_root}", flush=True)
    for arm in ("pre", "post"):
        binary = artifact_path(
            builds[arm]["binary_location"],
            output_root,
            f"{arm} binary_location",
        )
        print(f"{arm.capitalize()} binary:      {binary}", flush=True)


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(
        description=(
            "Build and run the resumable M172 pre/post interleaved throughput "
            "campaign. RAW inputs are read only; all non-record artifacts stay "
            "under this experiment's out directory."
        )
    )
    argument_parser.add_argument(
        "--output-root",
        type=Path,
        default=ALLOWED_OUTPUT_ROOT,
        help=f"artifact directory under {ALLOWED_OUTPUT_ROOT} (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--record",
        type=Path,
        default=DEFAULT_RECORD,
        help="atomically rewritten compact campaign JSON (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--stack",
        choices=sorted(STACKS),
        default="bee-1-cpl",
        help="registered safe input stack (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--limit",
        type=int,
        default=16,
        help="number of input frames (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--repetitions",
        type=int,
        default=6,
        help="paired timed repetitions (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--workers",
        nargs="+",
        default=["1,16"],
        metavar="N",
        help="worker counts, space- or comma-separated (default: 1,16)",
    )
    argument_parser.add_argument(
        "--pre-commit",
        default=PRE_COMMIT,
        help="full pre-change commit SHA (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--post-commit",
        default=POST_COMMIT,
        help="full post-change commit SHA (default: %(default)s)",
    )
    argument_parser.add_argument(
        "--phase",
        choices=("build-only", "verification-only", "full"),
        default="full",
        help="stop after isolated builds, verification, or all runs (default: %(default)s)",
    )
    return argument_parser


def main() -> int:
    args = parser().parse_args()
    require(
        os.name == "nt" and sys.platform == "win32",
        "M172 measurement is Windows-only (GetSystemTimes and Job Objects)",
    )

    workers = parse_workers(args.workers)
    require(args.limit >= 16, "--limit must be at least 16 for W1/W16 verification")
    require(args.repetitions >= 1, "--repetitions must be at least 1")
    for worker in workers:
        require(
            worker <= args.limit,
            f"worker count {worker} exceeds frame limit {args.limit}",
        )

    allowed_output_root = ALLOWED_OUTPUT_ROOT.resolve()
    output_root = args.output_root.resolve()
    require(
        is_within(output_root, allowed_output_root),
        f"--output-root must be {allowed_output_root} or one of its descendants",
    )
    output_root.mkdir(parents=True, exist_ok=True)
    record_path = args.record.resolve()
    require(
        is_within(record_path, LANE),
        f"--record must stay within the M172 experiment directory {LANE}",
    )
    require(
        record_path != Path(__file__).resolve(),
        "--record must not overwrite campaign.py",
    )
    require(
        not is_within(record_path, output_root),
        "--record must be outside --output-root so atomic rewrites cannot "
        "replace or be deleted with managed artifacts",
    )

    pre_commit = exact_commit(args.pre_commit, "--pre-commit")
    post_commit = exact_commit(args.post_commit, "--post-commit")
    require(pre_commit != post_commit, "pre and post commits must differ")
    commits = {"pre": pre_commit, "post": post_commit}
    trees = {
        arm: git_text("rev-parse", f"{commit}^{{tree}}").lower()
        for arm, commit in commits.items()
    }
    policy = make_run_policy(workers, args.repetitions)
    protocol = expected_protocol(
        pre_commit=pre_commit,
        post_commit=post_commit,
        stack_label=args.stack,
        output_root=output_root,
        limit=args.limit,
        workers=workers,
        repetitions=args.repetitions,
        policy=policy,
    )

    if record_path.exists():
        loaded = json.loads(record_path.read_text(encoding="utf-8"))
        require(isinstance(loaded, dict), "campaign record must be one JSON object")
        campaign = loaded
        validate_campaign_structure(campaign, protocol, policy)
        print(f"[resume] campaign record: {record_path}", flush=True)
    else:
        campaign = new_campaign(protocol)
        atomic_write(record_path, campaign)
        print(f"[new] campaign record: {record_path}", flush=True)

    builds = ensure_builds(
        campaign=campaign,
        record_path=record_path,
        output_root=output_root,
        commits=commits,
        trees=trees,
    )
    stack = STACKS[args.stack]
    validate_existing_runs(
        campaign=campaign,
        policy=policy,
        builds=builds,
        stack=stack,
        limit=args.limit,
        output_root=output_root,
    )
    if args.phase == "build-only":
        print_final(record_path, output_root, builds)
        return 0

    require(stack.is_dir(), f"registered stack directory is missing: {stack}")
    harness = load_harness()
    run_registered_plans(
        kind="verification",
        harness=harness,
        policy=policy,
        builds=builds,
        stack=stack,
        limit=args.limit,
        output_root=output_root,
        campaign=campaign,
        record_path=record_path,
    )
    outcome = verification_outcome(campaign)
    if campaign.get("verification_outcome") != outcome:
        campaign["verification_outcome"] = outcome
        atomic_write(record_path, campaign)
    require(
        outcome["valid"],
        "verification failed: pre W1/W16 pixels must differ, post W1/W16 "
        "pixels must match, and all worker-semantics witnesses must be valid",
    )
    print("[verify] pre differs and post matches across W1/W16", flush=True)
    if args.phase == "verification-only":
        print_final(record_path, output_root, builds)
        return 0

    run_registered_plans(
        kind="warmup",
        harness=harness,
        policy=policy,
        builds=builds,
        stack=stack,
        limit=args.limit,
        output_root=output_root,
        campaign=campaign,
        record_path=record_path,
    )
    run_registered_plans(
        kind="timed",
        harness=harness,
        policy=policy,
        builds=builds,
        stack=stack,
        limit=args.limit,
        output_root=output_root,
        campaign=campaign,
        record_path=record_path,
    )
    print_final(record_path, output_root, builds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
