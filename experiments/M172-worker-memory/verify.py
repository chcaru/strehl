#!/usr/bin/env python3
"""Independently validate and summarize an M172 throughput campaign."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import statistics
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


LANE = Path(__file__).resolve().parent
SCHEMA = "M172-throughput-v1"
SUMMARY_SCHEMA = "M172-throughput-summary-v1"
ARMS = ("pre", "post")
KINDS = ("verification", "warmup", "timed")
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
GIT_OID_RE = re.compile(r"^[0-9a-f]{40}$")
REL_TOL = 1.0e-12
ABS_TOL = 1.0e-12


class VerificationError(ValueError):
    """Campaign evidence is malformed, incomplete, or internally inconsistent."""


@dataclass(frozen=True)
class Build:
    arm: str
    commit: str
    tree_hash: str
    binary_location: str
    binary_sha256: str
    bytes: int
    version_output: str


@dataclass(frozen=True)
class Run:
    run_id: str
    sequence_index: int
    arm: str
    kind: str
    workers: int
    repetition: int | None
    commit: str
    binary_sha256: str
    wall_seconds: float
    pixel_sha256: str
    tiff_sha256: str
    cpu_elapsed_seconds: tuple[float, ...]
    cpu_percent: tuple[float, ...]
    cpu_mean_percent: float
    cpu_min_percent: float
    cpu_max_percent: float


def _fail(path: str, message: str) -> None:
    raise VerificationError(f"{path}: {message}")


def _field(value: Mapping[str, Any], key: str, path: str) -> Any:
    if key not in value:
        _fail(path, f"missing required member {key!r}")
    return value[key]


def _object(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(path, "must be an object")
    return value


def _array(value: Any, path: str) -> list[Any]:
    if not isinstance(value, list):
        _fail(path, "must be an array")
    return value


def _text(value: Any, path: str, *, nonempty: bool = True) -> str:
    if not isinstance(value, str):
        _fail(path, "must be a string")
    if nonempty and not value:
        _fail(path, "must not be empty")
    return value


def _integer(
    value: Any,
    path: str,
    *,
    minimum: int | None = None,
) -> int:
    if type(value) is not int:
        _fail(path, "must be an integer")
    if minimum is not None and value < minimum:
        _fail(path, f"must be at least {minimum}")
    return value


def _number(
    value: Any,
    path: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
    exclusive_minimum: bool = False,
) -> float:
    if type(value) not in (int, float):
        _fail(path, "must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        _fail(path, "must be a finite number")
    if minimum is not None:
        if exclusive_minimum and result <= minimum:
            _fail(path, f"must be greater than {minimum}")
        if not exclusive_minimum and result < minimum:
            _fail(path, f"must be at least {minimum}")
    if maximum is not None and result > maximum:
        _fail(path, f"must be at most {maximum}")
    return result


def _sha256(value: Any, path: str) -> str:
    result = _text(value, path)
    if not SHA256_RE.fullmatch(result):
        _fail(path, "must be exactly 64 uppercase hexadecimal digits")
    return result


def _git_oid(value: Any, path: str) -> str:
    result = _text(value, path)
    if not GIT_OID_RE.fullmatch(result):
        _fail(path, "must be a full lowercase 40-hexadecimal Git object ID")
    return result


def _close(actual: float, expected: float, path: str) -> None:
    if not math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        _fail(path, f"recorded {actual:.17g}, recomputed {expected:.17g}")


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON number {value}")


def read_campaign(path: Path) -> Mapping[str, Any]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read input {path}: {exc}") from exc
    if payload.startswith(b"\xef\xbb\xbf"):
        raise VerificationError("input must be UTF-8 without a byte-order mark")
    try:
        decoded = payload.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except VerificationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"invalid input JSON: {exc}") from exc
    return _object(value, "$")


def _hash_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    count = 0
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 << 20), b""):
                digest.update(block)
                count += len(block)
    except OSError as exc:
        raise VerificationError(f"cannot re-read recorded binary {path}: {exc}") from exc
    return digest.hexdigest().upper(), count


def _validate_declared_sha256s(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, member in value.items():
            member_path = f"{path}.{key}"
            if "sha256" in key.casefold():
                _sha256(member, member_path)
            _validate_declared_sha256s(member, member_path)
    elif isinstance(value, list):
        for index, member in enumerate(value):
            _validate_declared_sha256s(member, f"{path}[{index}]")


def _artifact_location(
    value: Any,
    *,
    artifact_base: Path,
    path: str,
) -> tuple[str, Path]:
    location = _text(value, path)
    candidate = Path(location)
    if candidate.is_absolute():
        _fail(path, "must be relative to the M172 experiment directory")
    try:
        base = artifact_base.resolve()
        resolved = (base / candidate).resolve()
        common = os.path.commonpath((str(base), str(resolved)))
    except (OSError, ValueError) as exc:
        raise VerificationError(f"{path}: cannot resolve artifact path: {exc}") from exc
    if os.path.normcase(common) != os.path.normcase(str(base)):
        _fail(path, "must not escape the M172 experiment directory")
    return location, resolved


def _validate_builds(
    campaign: Mapping[str, Any],
    *,
    artifact_base: Path,
) -> dict[str, Build]:
    raw_builds = _object(_field(campaign, "builds", "$"), "$.builds")
    if set(raw_builds) != set(ARMS):
        _fail(
            "$.builds",
            f"must contain exactly {list(ARMS)!r}, got {sorted(raw_builds)!r}",
        )

    builds: dict[str, Build] = {}
    for arm in ARMS:
        path = f"$.builds.{arm}"
        raw = _object(raw_builds[arm], path)
        recorded_arm = _text(_field(raw, "arm", path), f"{path}.arm")
        if recorded_arm != arm:
            _fail(f"{path}.arm", f"must be {arm!r}")
        if _field(raw, "valid", path) is not True:
            _fail(f"{path}.valid", "must be exactly true")
        commit = _git_oid(_field(raw, "commit", path), f"{path}.commit")
        tree_hash = _git_oid(
            _field(raw, "tree_hash", path),
            f"{path}.tree_hash",
        )
        version_output = _text(
            _field(raw, "version_output", path),
            f"{path}.version_output",
        )
        if commit not in version_output:
            _fail(
                f"{path}.version_output",
                "must contain the full build commit",
            )

        binary_location, disk_path = _artifact_location(
            _field(raw, "binary_location", path),
            artifact_base=artifact_base,
            path=f"{path}.binary_location",
        )
        binary_sha256 = _sha256(
            _field(raw, "binary_sha256", path),
            f"{path}.binary_sha256",
        )
        binary_bytes = _integer(
            _field(raw, "bytes", path),
            f"{path}.bytes",
            minimum=1,
        )

        try:
            disk_path.stat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise VerificationError(
                f"{path}.binary_location: cannot inspect {disk_path}: {exc}"
            ) from exc
        else:
            if not disk_path.is_file():
                _fail(
                    f"{path}.binary_location",
                    "existing path is not a regular file",
                )
            actual_hash, actual_bytes = _hash_file(disk_path)
            if actual_hash != binary_sha256:
                _fail(
                    f"{path}.binary_sha256",
                    f"existing binary hashes to {actual_hash}, not {binary_sha256}",
                )
            if actual_bytes != binary_bytes:
                _fail(
                    f"{path}.bytes",
                    f"existing binary has {actual_bytes} bytes, not {binary_bytes}",
                )

        builds[arm] = Build(
            arm=arm,
            commit=commit,
            tree_hash=tree_hash,
            binary_location=binary_location,
            binary_sha256=binary_sha256,
            bytes=binary_bytes,
            version_output=version_output,
        )
    if builds["pre"].commit == builds["post"].commit:
        _fail("$.builds", "pre and post builds must use distinct commits")
    return builds


def _expected_run_policy(
    workers: Sequence[int],
    repetitions: int,
    verification_workers: Sequence[int],
) -> list[dict[str, Any]]:
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

    for worker in verification_workers:
        for arm in ARMS:
            add(
                "verification",
                arm,
                worker,
                None,
                f"verification-w{worker}-{arm}",
            )
    for worker in workers:
        for arm in ARMS:
            add("warmup", arm, worker, None, f"warmup-w{worker}-{arm}")
    for repetition in range(1, repetitions + 1):
        for worker in workers:
            for arm in ARMS:
                add(
                    "timed",
                    arm,
                    worker,
                    repetition,
                    f"timed-r{repetition:02d}-w{worker}-{arm}",
                )
    return policy


def _validate_protocol(
    campaign: Mapping[str, Any],
    builds: Mapping[str, Build],
    *,
    artifact_base: Path,
) -> tuple[tuple[int, ...], tuple[int, ...], int, int, list[dict[str, Any]]]:
    raw = _object(_field(campaign, "protocol", "$"), "$.protocol")
    worker_values = _array(
        _field(raw, "workers", "$.protocol"),
        "$.protocol.workers",
    )
    workers = tuple(
        _integer(value, f"$.protocol.workers[{index}]", minimum=1)
        for index, value in enumerate(worker_values)
    )
    if not workers:
        _fail("$.protocol.workers", "must not be empty")
    if len(set(workers)) != len(workers):
        _fail("$.protocol.workers", "must contain distinct worker groups")

    verification_values = _array(
        _field(raw, "verification_workers", "$.protocol"),
        "$.protocol.verification_workers",
    )
    verification_workers = tuple(
        _integer(
            value,
            f"$.protocol.verification_workers[{index}]",
            minimum=1,
        )
        for index, value in enumerate(verification_values)
    )
    if verification_workers != (1, 16):
        _fail(
            "$.protocol.verification_workers",
            "must be exactly [1, 16] for the registered repair contrast",
        )
    if set(workers) != set(verification_workers):
        _fail(
            "$.protocol.workers",
            "timed worker groups must exactly match verification worker groups",
        )

    repetitions = _integer(
        _field(raw, "repetitions", "$.protocol"),
        "$.protocol.repetitions",
        minimum=1,
    )

    warmups_per_arm_worker = _integer(
        _field(raw, "warmups_per_arm_worker", "$.protocol"),
        "$.protocol.warmups_per_arm_worker",
        minimum=0,
    )
    if warmups_per_arm_worker != 1:
        _fail(
            "$.protocol.warmups_per_arm_worker",
            "M172-throughput-v1 requires exactly one warmup per arm/worker",
        )
    if _field(raw, "warmups_excluded_from_ratios", "$.protocol") is not True:
        _fail(
            "$.protocol.warmups_excluded_from_ratios",
            "must be exactly true",
        )
    sequence_base = _integer(
        _field(raw, "sequence_index_base", "$.protocol"),
        "$.protocol.sequence_index_base",
        minimum=0,
    )
    if sequence_base != 0:
        _fail("$.protocol.sequence_index_base", "must be zero")
    cpu_semantics = _text(
        _field(raw, "cpu_semantics", "$.protocol"),
        "$.protocol.cpu_semantics",
    )
    if "Processor(_Total)" not in cpu_semantics:
        _fail(
            "$.protocol.cpu_semantics",
            "must identify Windows Processor(_Total)",
        )

    commits = _object(
        _field(raw, "commits", "$.protocol"),
        "$.protocol.commits",
    )
    if set(commits) != set(ARMS):
        _fail("$.protocol.commits", f"must contain exactly {list(ARMS)!r}")
    for arm in ARMS:
        commit = _git_oid(commits[arm], f"$.protocol.commits.{arm}")
        if commit != builds[arm].commit:
            _fail(
                f"$.protocol.commits.{arm}",
                f"does not match the {arm} build commit",
            )

    artifact_root_location, _ = _artifact_location(
        _field(raw, "artifact_output_root", "$.protocol"),
        artifact_base=artifact_base,
        path="$.protocol.artifact_output_root",
    )
    for arm in ARMS:
        expected_location = (
            Path(artifact_root_location)
            / "builds"
            / arm
            / "bin"
            / "strehl.exe"
        ).as_posix()
        if Path(builds[arm].binary_location).as_posix() != expected_location:
            _fail(
                f"$.builds.{arm}.binary_location",
                f"must be {expected_location!r} under protocol artifact_output_root",
            )

    expected_policy = _expected_run_policy(
        workers,
        repetitions,
        verification_workers,
    )
    raw_policy = _array(
        _field(raw, "ordered_run_policy", "$.protocol"),
        "$.protocol.ordered_run_policy",
    )
    if raw_policy != expected_policy:
        _fail(
            "$.protocol.ordered_run_policy",
            "does not equal the independently reconstructed complete run policy",
        )
    return (
        workers,
        verification_workers,
        repetitions,
        warmups_per_arm_worker,
        expected_policy,
    )


def _run_sections(
    campaign: Mapping[str, Any],
) -> dict[str, list[Any]]:
    names = {
        "verification": "verification",
        "warmup": "warmups",
        "timed": "timed_runs",
    }
    sections: dict[str, list[Any]] = {}
    for kind, member in names.items():
        sections[kind] = _array(
            _field(campaign, member, "$"),
            f"$.{member}",
        )
    return sections


def _validate_cpu_trace(raw_run: Mapping[str, Any], path: str) -> tuple[
    tuple[float, ...],
    tuple[float, ...],
    float,
    float,
    float,
]:
    raw_samples = _array(
        _field(raw_run, "cpu_trace", path),
        f"{path}.cpu_trace",
    )
    if not raw_samples:
        _fail(f"{path}.cpu_trace", "must not be empty")

    elapsed: list[float] = []
    percentages: list[float] = []
    for index, value in enumerate(raw_samples):
        sample_path = f"{path}.cpu_trace[{index}]"
        sample = _object(value, sample_path)
        elapsed_value = _number(
            _field(sample, "elapsed_seconds", sample_path),
            f"{sample_path}.elapsed_seconds",
        )
        percent_value = _number(
            _field(sample, "processor_total_percent", sample_path),
            f"{sample_path}.processor_total_percent",
            minimum=0.0,
            maximum=100.0,
        )
        if elapsed and elapsed_value <= elapsed[-1]:
            _fail(
                f"{sample_path}.elapsed_seconds",
                "must be strictly increasing",
            )
        elapsed.append(elapsed_value)
        percentages.append(percent_value)

    mean_percent = _number(
        _field(raw_run, "processor_total_percent_mean", path),
        f"{path}.processor_total_percent_mean",
        minimum=0.0,
        maximum=100.0,
    )
    min_percent = _number(
        _field(raw_run, "processor_total_percent_min", path),
        f"{path}.processor_total_percent_min",
        minimum=0.0,
        maximum=100.0,
    )
    max_percent = _number(
        _field(raw_run, "processor_total_percent_max", path),
        f"{path}.processor_total_percent_max",
        minimum=0.0,
        maximum=100.0,
    )
    _close(
        mean_percent,
        statistics.fmean(percentages),
        f"{path}.processor_total_percent_mean",
    )
    _close(
        min_percent,
        min(percentages),
        f"{path}.processor_total_percent_min",
    )
    _close(
        max_percent,
        max(percentages),
        f"{path}.processor_total_percent_max",
    )
    return (
        tuple(elapsed),
        tuple(percentages),
        mean_percent,
        min_percent,
        max_percent,
    )


def _validate_run(
    raw_value: Any,
    *,
    path: str,
    expected_kind: str,
    expected_plan: Mapping[str, Any],
    builds: Mapping[str, Build],
    workers: Sequence[int],
    repetitions: int,
) -> Run:
    raw = _object(raw_value, path)
    run_id = _text(_field(raw, "run_id", path), f"{path}.run_id")
    if run_id != expected_plan["run_id"]:
        _fail(
            f"{path}.run_id",
            f"must match protocol run ID {expected_plan['run_id']!r}",
        )
    sequence_index = _integer(
        _field(raw, "sequence_index", path),
        f"{path}.sequence_index",
        minimum=0,
    )
    if sequence_index != expected_plan["sequence_index"]:
        _fail(
            f"{path}.sequence_index",
            f"must match protocol index {expected_plan['sequence_index']}",
        )
    arm = _text(_field(raw, "arm", path), f"{path}.arm")
    if arm not in ARMS:
        _fail(f"{path}.arm", f"must be one of {list(ARMS)!r}")
    if arm != expected_plan["arm"]:
        _fail(f"{path}.arm", f"must match protocol arm {expected_plan['arm']!r}")
    kind = _text(_field(raw, "kind", path), f"{path}.kind")
    if kind != expected_kind:
        _fail(f"{path}.kind", f"must be {expected_kind!r}")
    if kind != expected_plan["kind"]:
        _fail(
            f"{path}.kind",
            f"must match protocol kind {expected_plan['kind']!r}",
        )
    worker_count = _integer(
        _field(raw, "workers", path),
        f"{path}.workers",
        minimum=1,
    )
    if worker_count not in workers:
        _fail(
            f"{path}.workers",
            f"W{worker_count} is not declared by protocol workers {list(workers)!r}",
        )
    if worker_count != expected_plan["workers"]:
        _fail(
            f"{path}.workers",
            f"must match protocol worker count {expected_plan['workers']}",
        )

    raw_repetition = _field(raw, "repetition", path)
    repetition: int | None
    if expected_kind == "timed":
        repetition = _integer(
            raw_repetition,
            f"{path}.repetition",
            minimum=1,
        )
        if repetition > repetitions:
            _fail(
                f"{path}.repetition",
                f"must not exceed protocol repetitions {repetitions}",
            )
    else:
        if raw_repetition is not None:
            _fail(f"{path}.repetition", "must be null outside timed runs")
        repetition = None
    if repetition != expected_plan["repetition"]:
        _fail(
            f"{path}.repetition",
            f"must match protocol repetition {expected_plan['repetition']!r}",
        )

    build = builds[arm]
    commit = _git_oid(
        _field(raw, "source_commit", path),
        f"{path}.source_commit",
    )
    if commit != build.commit:
        _fail(
            f"{path}.source_commit",
            f"does not match {arm} build commit {build.commit}",
        )
    binary_sha256 = _sha256(
        _field(raw, "binary_sha256", path),
        f"{path}.binary_sha256",
    )
    if binary_sha256 != build.binary_sha256:
        _fail(
            f"{path}.binary_sha256",
            f"does not match {arm} build binary {build.binary_sha256}",
        )
    returncode = _integer(
        _field(raw, "return_code", path),
        f"{path}.return_code",
    )
    if returncode != 0:
        _fail(f"{path}.return_code", "must be zero")
    if _field(raw, "valid", path) is not True:
        _fail(f"{path}.valid", "must be exactly true")
    invalid_reasons = _array(
        _field(raw, "invalid_reasons", path),
        f"{path}.invalid_reasons",
    )
    if invalid_reasons:
        _fail(f"{path}.invalid_reasons", "must be empty for a valid run")

    wall_seconds = _number(
        _field(raw, "wall_seconds", path),
        f"{path}.wall_seconds",
        minimum=0.0,
        exclusive_minimum=True,
    )
    pixel_sha256 = _sha256(
        _field(raw, "pixel_sha256", path),
        f"{path}.pixel_sha256",
    )
    tiff_sha256 = _sha256(
        _field(raw, "tiff_sha256", path),
        f"{path}.tiff_sha256",
    )
    tiff_software = _text(
        _field(raw, "tiff_software", path),
        f"{path}.tiff_software",
    )
    if commit not in tiff_software:
        _fail(
            f"{path}.tiff_software",
            "must contain the run's full source commit",
        )
    (
        cpu_elapsed_seconds,
        cpu_percent,
        cpu_mean_percent,
        cpu_min_percent,
        cpu_max_percent,
    ) = _validate_cpu_trace(raw, path)
    return Run(
        run_id=run_id,
        sequence_index=sequence_index,
        arm=arm,
        kind=kind,
        workers=worker_count,
        repetition=repetition,
        commit=commit,
        binary_sha256=binary_sha256,
        wall_seconds=wall_seconds,
        pixel_sha256=pixel_sha256,
        tiff_sha256=tiff_sha256,
        cpu_elapsed_seconds=cpu_elapsed_seconds,
        cpu_percent=cpu_percent,
        cpu_mean_percent=cpu_mean_percent,
        cpu_min_percent=cpu_min_percent,
        cpu_max_percent=cpu_max_percent,
    )


def percentile_type7(values: Sequence[float], probability: float) -> float:
    """Return the Hyndman-Fan Type-7 linear sample percentile."""
    if not values:
        raise ValueError("percentile requires at least one value")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0, 1]")
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def _ratio_statistics(values: Sequence[float]) -> dict[str, Any]:
    ordered_values = [float(value) for value in values]
    minimum = min(ordered_values)
    maximum = max(ordered_values)
    q1 = percentile_type7(ordered_values, 0.25)
    q3 = percentile_type7(ordered_values, 0.75)
    return {
        "count": len(ordered_values),
        "paired_ratios": ordered_values,
        "median": percentile_type7(ordered_values, 0.50),
        "mean": statistics.fmean(ordered_values),
        "min": minimum,
        "max": maximum,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "q1_type7": q1,
        "q3_type7": q3,
        "iqr_type7": q3 - q1,
        "range": {
            "low": minimum,
            "high": maximum,
            "width": maximum - minimum,
        },
    }


def _cpu_summary(runs: Sequence[Run]) -> dict[str, Any]:
    values = [sample for run in runs for sample in run.cpu_percent]
    if not runs or not values:
        raise VerificationError("internal error: CPU summary has no runs or samples")
    return {
        "run_count": len(runs),
        "sample_count": len(values),
        "mean_percent": statistics.fmean(values),
        "min_percent": min(values),
        "max_percent": max(values),
        "median_percent_type7": percentile_type7(values, 0.50),
    }


def validate_and_analyze(
    campaign_value: Any,
    *,
    artifact_base: Path = LANE,
) -> dict[str, Any]:
    campaign = _object(campaign_value, "$")
    schema = _text(_field(campaign, "schema", "$"), "$.schema")
    if schema != SCHEMA:
        _fail("$.schema", f"must be exactly {SCHEMA!r}")

    _validate_declared_sha256s(campaign)
    builds = _validate_builds(campaign, artifact_base=artifact_base)
    (
        workers,
        verification_workers,
        repetitions,
        warmups_per_arm_worker,
        expected_policy,
    ) = _validate_protocol(campaign, builds, artifact_base=artifact_base)
    raw_sections = _run_sections(campaign)
    sections: dict[str, list[Run]] = {}
    all_runs: list[Run] = []
    member_names = {
        "verification": "verification",
        "warmup": "warmups",
        "timed": "timed_runs",
    }
    for kind in KINDS:
        member = member_names[kind]
        expected_plans = [
            plan for plan in expected_policy if plan["kind"] == kind
        ]
        raw_rows = raw_sections[kind]
        if len(raw_rows) != len(expected_plans):
            _fail(
                f"$.{member}",
                f"expected {len(expected_plans)} registered runs, "
                f"found {len(raw_rows)}",
            )
        rows: list[Run] = []
        for index, (raw, plan) in enumerate(zip(raw_rows, expected_plans)):
            rows.append(
                _validate_run(
                    raw,
                    path=f"$.{member}[{index}]",
                    expected_kind=kind,
                    expected_plan=plan,
                    builds=builds,
                    workers=workers,
                    repetitions=repetitions,
                )
            )
        sections[kind] = rows
        all_runs.extend(rows)

    run_ids = [run.run_id for run in all_runs]
    if len(set(run_ids)) != len(run_ids):
        duplicates = sorted(
            run_id for run_id in set(run_ids) if run_ids.count(run_id) > 1
        )
        _fail("$.runs", f"run IDs must be unique; duplicates={duplicates!r}")
    sequence_indexes = [run.sequence_index for run in all_runs]
    if len(set(sequence_indexes)) != len(sequence_indexes):
        _fail("$.runs", "sequence_index values must be unique")
    ordered_indexes = sorted(sequence_indexes)
    if ordered_indexes != list(range(len(expected_policy))):
        _fail(
            "$.runs",
            "sequence_index values must be exactly 0 through policy length minus one",
        )

    measured_workers = {run.workers for run in sections["timed"]}
    if measured_workers != set(workers):
        _fail(
            "$.protocol.workers",
            "must contain exactly the worker groups present in timed runs; "
            f"protocol={sorted(workers)!r}, measured={sorted(measured_workers)!r}",
        )

    verification = sections["verification"]
    expected_verification = {
        (arm, worker) for arm in ARMS for worker in verification_workers
    }
    verification_counts: dict[tuple[str, int], int] = {}
    for run in verification:
        key = (run.arm, run.workers)
        verification_counts[key] = verification_counts.get(key, 0) + 1
    if set(verification_counts) != expected_verification or any(
        count != 1 for count in verification_counts.values()
    ):
        _fail(
            "$.verification",
            "must contain exactly one pre and one post run for every protocol worker",
        )
    verification_by_key = {
        (run.arm, run.workers): run for run in verification
    }

    warmups = sections["warmup"]
    warmup_counts = {
        (arm, worker): 0 for arm in ARMS for worker in workers
    }
    for run in warmups:
        warmup_counts[(run.arm, run.workers)] += 1
    if any(
        count != warmups_per_arm_worker
        for count in warmup_counts.values()
    ) or len(warmups) != (
        len(ARMS) * len(workers) * warmups_per_arm_worker
    ):
        _fail(
            "$.warmups",
            "does not match protocol warmups_per_arm_worker",
        )

    def hash_for(arm: str, worker: int, attribute: str) -> str:
        return getattr(verification_by_key[(arm, worker)], attribute)

    for attribute, label in (
        ("pixel_sha256", "pixel"),
        ("tiff_sha256", "TIFF"),
    ):
        if hash_for("pre", 1, attribute) == hash_for("pre", 16, attribute):
            _fail(
                "$.verification",
                f"pre W1 and W16 {label} hashes must differ",
            )
        post_hashes = {
            hash_for("post", worker, attribute)
            for worker in verification_workers
        }
        if len(post_hashes) != 1:
            _fail(
                "$.verification",
                f"post {label} hashes must match across worker counts",
            )

    outcome = _object(
        _field(campaign, "verification_outcome", "$"),
        "$.verification_outcome",
    )
    for arm in ARMS:
        hashes = _object(
            _field(
                outcome,
                f"{arm}_pixel_hashes",
                "$.verification_outcome",
            ),
            f"$.verification_outcome.{arm}_pixel_hashes",
        )
        expected_hashes = {
            f"w{worker}": hash_for(arm, worker, "pixel_sha256")
            for worker in verification_workers
        }
        if dict(hashes) != expected_hashes:
            _fail(
                f"$.verification_outcome.{arm}_pixel_hashes",
                "does not reproduce the verification run hashes",
            )
    expected_outcome_flags = {
        "pre_worker_hashes_differ": True,
        "post_worker_hashes_match": True,
        "worker_semantics_verified_in_stderr": True,
        "valid": True,
    }
    for key, expected in expected_outcome_flags.items():
        if _field(outcome, key, "$.verification_outcome") is not expected:
            _fail(
                f"$.verification_outcome.{key}",
                f"must be exactly {expected!r}",
            )

    timed = sections["timed"]
    expected_timed_count = repetitions * len(workers) * len(ARMS)
    if len(timed) != expected_timed_count:
        _fail(
            "$.timed_runs",
            f"expected {expected_timed_count} runs, found {len(timed)}",
        )
    timed_by_key: dict[tuple[int, int, str], Run] = {}
    for run in timed:
        if run.repetition is None:
            raise VerificationError(
                f"internal error: timed run {run.run_id} has no repetition"
            )
        key = (run.repetition, run.workers, run.arm)
        if key in timed_by_key:
            _fail(
                "$.timed_runs",
                "contains more than one run at "
                f"repetition={run.repetition}, W{run.workers}, arm={run.arm}",
            )
        timed_by_key[key] = run
        reference = verification_by_key[(run.arm, run.workers)]
        if run.pixel_sha256 != reference.pixel_sha256:
            _fail(
                f"run {run.run_id}.pixel_sha256",
                "does not reproduce its fixed-arm/fixed-worker verification hash",
            )
        if run.tiff_sha256 != reference.tiff_sha256:
            _fail(
                f"run {run.run_id}.tiff_sha256",
                "does not reproduce its fixed-arm/fixed-worker verification hash",
            )

    expected_timed_keys = {
        (repetition, worker, arm)
        for repetition in range(1, repetitions + 1)
        for worker in workers
        for arm in ARMS
    }
    if set(timed_by_key) != expected_timed_keys:
        missing = sorted(expected_timed_keys - set(timed_by_key))
        extras = sorted(set(timed_by_key) - expected_timed_keys)
        _fail(
            "$.timed_runs",
            f"incomplete timed matrix; missing={missing!r}, extras={extras!r}",
        )

    for attribute, label in (
        ("pixel_sha256", "pixel"),
        ("tiff_sha256", "TIFF"),
    ):
        post_hashes = {
            getattr(run, attribute) for run in timed if run.arm == "post"
        }
        if len(post_hashes) != 1:
            _fail(
                "$.timed_runs",
                f"post {label} hashes must be identical across worker counts",
            )
        pre_w1 = {
            getattr(run, attribute)
            for run in timed
            if run.arm == "pre" and run.workers == 1
        }
        pre_w16 = {
            getattr(run, attribute)
            for run in timed
            if run.arm == "pre" and run.workers == 16
        }
        if len(pre_w1) != 1 or len(pre_w16) != 1 or pre_w1 == pre_w16:
            _fail(
                "$.timed_runs",
                f"pre W1 and W16 {label} hashes must remain distinct",
            )

    ordered_campaign = sorted(all_runs, key=lambda run: run.sequence_index)
    campaign_position = {
        run.run_id: index for index, run in enumerate(ordered_campaign)
    }
    by_worker: dict[str, Any] = {}
    for worker in workers:
        pairs: list[dict[str, Any]] = []
        ratios: list[float] = []
        for repetition in range(1, repetitions + 1):
            pre = timed_by_key[(repetition, worker, "pre")]
            post = timed_by_key[(repetition, worker, "post")]
            if post.sequence_index != pre.sequence_index + 1:
                _fail(
                    "$.timed_runs",
                    f"repetition {repetition}, W{worker}: post must immediately "
                    "follow pre by sequence_index",
                )
            pre_position = campaign_position[pre.run_id]
            if (
                pre_position + 1 >= len(ordered_campaign)
                or ordered_campaign[pre_position + 1].run_id != post.run_id
            ):
                _fail(
                    "$.timed_runs",
                    f"repetition {repetition}, W{worker}: another run occurs "
                    "between paired pre and post runs",
                )
            ratio = post.wall_seconds / pre.wall_seconds
            ratios.append(ratio)
            pairs.append(
                {
                    "repetition": repetition,
                    "workers": worker,
                    "ratio_post_over_pre": ratio,
                    "pre": {
                        "run_id": pre.run_id,
                        "sequence_index": pre.sequence_index,
                        "wall_seconds": pre.wall_seconds,
                        "mean_cpu_percent": pre.cpu_mean_percent,
                    },
                    "post": {
                        "run_id": post.run_id,
                        "sequence_index": post.sequence_index,
                        "wall_seconds": post.wall_seconds,
                        "mean_cpu_percent": post.cpu_mean_percent,
                    },
                }
            )
        stats = _ratio_statistics(ratios)
        by_worker[str(worker)] = {
            **stats,
            "pairs": pairs,
        }

    cpu_summaries = {
        "all_runs_including_verification_and_warmups": _cpu_summary(all_runs),
        "timed_runs_only": _cpu_summary(timed),
        "timed_by_arm": {
            arm: _cpu_summary([run for run in timed if run.arm == arm])
            for arm in ARMS
        },
        "timed_by_worker": {
            str(worker): _cpu_summary(
                [run for run in timed if run.workers == worker]
            )
            for worker in workers
        },
    }
    headline = {
        "metric": "median paired post-repair/pre-repair wall_seconds ratio",
        "absolute_times_are_per_run_observations_not_performance_claims": True,
        "by_worker": {
            str(worker): {
                "median_post_over_pre": by_worker[str(worker)]["median"],
                "spread_iqr": by_worker[str(worker)]["iqr"],
                "spread_iqr_type7": by_worker[str(worker)]["iqr_type7"],
                "range": by_worker[str(worker)]["range"],
                "count": by_worker[str(worker)]["count"],
            }
            for worker in workers
        },
    }
    return {
        "schema": SUMMARY_SCHEMA,
        "source_schema": SCHEMA,
        "protocol": {
            "workers": list(workers),
            "repetitions": repetitions,
            "timed_pair_order": list(ARMS),
            "ratio_definition": "post wall_seconds / pre wall_seconds",
            "percentile_method": (
                "Hyndman-Fan Type 7 linear interpolation: "
                "h=(n-1)p, interpolate adjacent order statistics"
            ),
            "warmups_included_in_ratios": False,
            "absolute_time_interpretation": (
                "per-run raw observations only; no absolute performance claim"
            ),
        },
        "builds": {
            arm: {
                "commit": build.commit,
                "tree_hash": build.tree_hash,
                "binary_location": build.binary_location,
                "binary_sha256": build.binary_sha256,
                "bytes": build.bytes,
                "version_output": build.version_output,
            }
            for arm, build in builds.items()
        },
        "headline": headline,
        "by_worker": by_worker,
        "cpu_trace_summaries": cpu_summaries,
        "validated_run_counts": {
            "verification": len(verification),
            "warmup": len(warmups),
            "timed": len(timed),
            "total": len(all_runs),
        },
        "hash_contrast": {
            "pre_w1_w16_distinct": True,
            "post_all_workers_identical": True,
            "timed_fixed_arm_worker_reproduces_verification": True,
            "families_checked": ["pixel_sha256", "tiff_sha256"],
            "verification_by_arm_worker": {
                arm: {
                    f"w{worker}": {
                        "pixel_sha256": verification_by_key[
                            (arm, worker)
                        ].pixel_sha256,
                        "tiff_sha256": verification_by_key[
                            (arm, worker)
                        ].tiff_sha256,
                    }
                    for worker in verification_workers
                }
                for arm in ARMS
            },
        },
    }


def atomic_write_json(path: Path, value: Mapping[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise VerificationError(f"cannot create output directory {path.parent}: {exc}") from exc
    temporary: Path | None = None
    try:
        descriptor, raw_path = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
        )
        temporary = Path(raw_path)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(
                value,
                stream,
                indent=2,
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except (OSError, TypeError, ValueError) as exc:
        raise VerificationError(f"cannot atomically write output {path}: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _synthetic_cpu(offset: float = 0.0) -> dict[str, Any]:
    percentages = [10.0 + offset, 20.0 + offset, 30.0 + offset]
    return {
        "trace": [
            {
                "elapsed_seconds": index * 0.5,
                "processor_total_percent": value,
            }
            for index, value in enumerate(percentages)
        ],
        "mean": statistics.fmean(percentages),
        "min": min(percentages),
        "max": max(percentages),
    }


def _synthetic_campaign(directory: Path) -> dict[str, Any]:
    binary_payloads = {
        "pre": b"synthetic pre-repair executable\n",
        "post": b"synthetic post-repair executable\n",
    }
    commits = {
        "pre": "1" * 40,
        "post": "2" * 40,
    }
    trees = {
        "pre": "3" * 40,
        "post": "4" * 40,
    }
    builds: dict[str, Any] = {}
    for arm in ARMS:
        binary_name = f"out/builds/{arm}/bin/strehl.exe"
        binary_path = directory / Path(binary_name)
        binary_path.parent.mkdir(parents=True, exist_ok=True)
        binary_path.write_bytes(binary_payloads[arm])
        builds[arm] = {
            "valid": True,
            "arm": arm,
            "commit": commits[arm],
            "tree_hash": trees[arm],
            "binary_location": binary_name,
            "binary_sha256": hashlib.sha256(
                binary_payloads[arm]
            ).hexdigest().upper(),
            "bytes": len(binary_payloads[arm]),
            "version_output": f"strehl synthetic ({commits[arm]})",
        }

    pixel = {
        ("pre", 1): "A" * 64,
        ("pre", 16): "B" * 64,
        ("post", 1): "C" * 64,
        ("post", 16): "C" * 64,
    }
    tiff = {
        ("pre", 1): "D" * 64,
        ("pre", 16): "E" * 64,
        ("post", 1): "F" * 64,
        ("post", 16): "F" * 64,
    }
    workers = [1, 16]
    verification_workers = [1, 16]
    repetitions = 4
    policy = _expected_run_policy(
        workers,
        repetitions,
        verification_workers,
    )

    def make_run(
        plan: Mapping[str, Any],
        *,
        wall_seconds: float,
    ) -> dict[str, Any]:
        arm = plan["arm"]
        worker_count = plan["workers"]
        cpu = _synthetic_cpu(0.5 if arm == "post" else 0.0)
        return {
            "run_id": plan["run_id"],
            "sequence_index": plan["sequence_index"],
            "arm": arm,
            "kind": plan["kind"],
            "workers": worker_count,
            "repetition": plan["repetition"],
            "source_commit": builds[arm]["commit"],
            "binary_sha256": builds[arm]["binary_sha256"],
            "return_code": 0,
            "valid": True,
            "invalid_reasons": [],
            "wall_seconds": wall_seconds,
            "pixel_sha256": pixel[(arm, worker_count)],
            "tiff_sha256": tiff[(arm, worker_count)],
            "tiff_software": f"strehl synthetic ({commits[arm]})",
            "cpu_trace": cpu["trace"],
            "processor_total_percent_mean": cpu["mean"],
            "processor_total_percent_min": cpu["min"],
            "processor_total_percent_max": cpu["max"],
        }

    ratios = {
        1: [0.5, 1.0, 1.5, 2.5],
        16: [0.8, 0.9, 1.0, 1.1],
    }
    verification_runs: list[dict[str, Any]] = []
    warmup_runs: list[dict[str, Any]] = []
    timed_runs: list[dict[str, Any]] = []
    for plan in policy:
        if plan["kind"] == "verification":
            verification_runs.append(make_run(plan, wall_seconds=2.0))
        elif plan["kind"] == "warmup":
            warmup_runs.append(
                make_run(plan, wall_seconds=1000.0 + plan["workers"])
            )
        else:
            repetition = plan["repetition"]
            worker_count = plan["workers"]
            pre_wall = 10.0 + repetition + worker_count / 100.0
            wall = (
                pre_wall
                if plan["arm"] == "pre"
                else pre_wall * ratios[worker_count][repetition - 1]
            )
            timed_runs.append(make_run(plan, wall_seconds=wall))
    return {
        "schema": SCHEMA,
        "builds": builds,
        "protocol": {
            "commits": commits,
            "workers": workers,
            "verification_workers": verification_workers,
            "repetitions": repetitions,
            "warmups_per_arm_worker": 1,
            "warmups_excluded_from_ratios": True,
            "sequence_index_base": 0,
            "cpu_semantics": (
                "Windows Processor(_Total): synthetic whole-host percentage"
            ),
            "ordered_run_policy": policy,
            "artifact_output_root": "out",
        },
        "verification": verification_runs,
        "verification_outcome": {
            "pre_pixel_hashes": {
                "w1": pixel[("pre", 1)],
                "w16": pixel[("pre", 16)],
            },
            "post_pixel_hashes": {
                "w1": pixel[("post", 1)],
                "w16": pixel[("post", 16)],
            },
            "pre_worker_hashes_differ": True,
            "post_worker_hashes_match": True,
            "worker_semantics_verified_in_stderr": True,
            "valid": True,
        },
        "warmups": warmup_runs,
        "timed_runs": timed_runs,
    }


def _find_run(
    campaign: dict[str, Any],
    member: str,
    *,
    arm: str | None = None,
    workers: int | None = None,
    repetition: int | None = None,
) -> dict[str, Any]:
    matches = []
    for run in campaign[member]:
        if arm is not None and run["arm"] != arm:
            continue
        if workers is not None and run["workers"] != workers:
            continue
        if repetition is not None and run.get("repetition") != repetition:
            continue
        matches.append(run)
    if len(matches) != 1:
        raise RuntimeError(
            f"synthetic selector for {member} found {len(matches)} runs"
        )
    return matches[0]


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="m172-verify-self-test-") as raw_dir:
        directory = Path(raw_dir)
        baseline = _synthetic_campaign(directory)
        summary = validate_and_analyze(baseline, artifact_base=directory)
        output_path = directory / "atomic-summary.json"
        atomic_write_json(output_path, summary)
        if read_campaign(output_path) != summary:
            raise RuntimeError("atomic summary round-trip changed its JSON value")
        print("ARITHMETIC-control atomic-summary-round-trip: PASS")

        known = summary["by_worker"]["1"]
        if known["count"] != 4 or known["paired_ratios"] != [
            0.5,
            1.0,
            1.5,
            2.5,
        ]:
            raise RuntimeError(
                "known-ratio case did not retain its four individual pairs"
            )
        expected = {
            "median": 1.25,
            "mean": 1.375,
            "q1": 0.875,
            "q3": 1.75,
            "iqr": 0.875,
            "q1_type7": 0.875,
            "q3_type7": 1.75,
            "iqr_type7": 0.875,
            "min": 0.5,
            "max": 2.5,
        }
        for field, target in expected.items():
            actual = known[field]
            if not math.isclose(
                actual,
                target,
                rel_tol=REL_TOL,
                abs_tol=ABS_TOL,
            ):
                raise RuntimeError(
                    f"known-ratio arithmetic failed for {field}: "
                    f"{actual!r} != {target!r}"
                )
        print("ARITHMETIC-control known-ratio-median-iqr: PASS")

        changed_warmup = copy.deepcopy(baseline)
        for run in changed_warmup["warmups"]:
            run["wall_seconds"] *= 1_000_000.0
        warmup_summary = validate_and_analyze(
            changed_warmup,
            artifact_base=directory,
        )
        if warmup_summary["by_worker"] != summary["by_worker"]:
            raise RuntimeError("warm-up wall times leaked into paired ratios")
        print("ARITHMETIC-control warmups-excluded-from-ratios: PASS")

        controls: list[
            tuple[str, Callable[[dict[str, Any]], None]]
        ] = []

        def control(name: str) -> Callable[
            [Callable[[dict[str, Any]], None]],
            Callable[[dict[str, Any]], None],
        ]:
            def register(
                function: Callable[[dict[str, Any]], None],
            ) -> Callable[[dict[str, Any]], None]:
                controls.append((name, function))
                return function

            return register

        @control("missing-pre-build")
        def _(campaign: dict[str, Any]) -> None:
            del campaign["builds"]["pre"]

        @control("truncated-tree-hash")
        def _(campaign: dict[str, Any]) -> None:
            campaign["builds"]["pre"]["tree_hash"] = "1" * 12

        @control("invalid-build")
        def _(campaign: dict[str, Any]) -> None:
            campaign["builds"]["pre"]["valid"] = False

        @control("same-pre-post-commit")
        def _(campaign: dict[str, Any]) -> None:
            post_commit = campaign["builds"]["post"]["commit"]
            campaign["builds"]["pre"]["commit"] = post_commit
            campaign["builds"]["pre"]["version_output"] = (
                f"strehl synthetic ({post_commit})"
            )

        @control("version-commit-mismatch")
        def _(campaign: dict[str, Any]) -> None:
            campaign["builds"]["post"]["version_output"] = (
                "strehl synthetic (deadbeef)"
            )

        @control("existing-binary-content-mismatch")
        def _(campaign: dict[str, Any]) -> None:
            tampered = directory / "tampered.exe"
            tampered.write_bytes(b"not the recorded executable")
            campaign["builds"]["pre"]["binary_location"] = tampered.name

        @control("wrong-build-binary-hash")
        def _(campaign: dict[str, Any]) -> None:
            planted_hash = "0" * 64
            campaign["builds"]["pre"]["binary_sha256"] = planted_hash
            for member in ("verification", "warmups", "timed_runs"):
                for run in campaign[member]:
                    if run["arm"] == "pre":
                        run["binary_sha256"] = planted_hash

        @control("wrong-binary-byte-count")
        def _(campaign: dict[str, Any]) -> None:
            campaign["builds"]["post"]["bytes"] += 1

        @control("protocol-worker-mismatch")
        def _(campaign: dict[str, Any]) -> None:
            campaign["protocol"]["workers"].append(8)

        @control("nonpositive-repetitions")
        def _(campaign: dict[str, Any]) -> None:
            campaign["protocol"]["repetitions"] = 0

        @control("warmups-not-excluded")
        def _(campaign: dict[str, Any]) -> None:
            campaign["protocol"]["warmups_excluded_from_ratios"] = False

        @control("duplicate-run-id")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][1]["run_id"] = campaign["timed_runs"][0][
                "run_id"
            ]

        @control("missing-verification-run")
        def _(campaign: dict[str, Any]) -> None:
            campaign["verification"].pop()

        @control("missing-timed-run")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"].pop()

        @control("missing-warmup-run")
        def _(campaign: dict[str, Any]) -> None:
            campaign["warmups"].pop()

        @control("duplicate-timed-run")
        def _(campaign: dict[str, Any]) -> None:
            duplicate = copy.deepcopy(campaign["timed_runs"][0])
            duplicate["run_id"] = "extra-timed-run"
            duplicate["sequence_index"] = (
                max(
                    run["sequence_index"]
                    for member in (
                        "verification",
                        "warmups",
                        "timed_runs",
                    )
                    for run in campaign[member]
                )
                + 1
            )
            campaign["timed_runs"].append(duplicate)

        @control("run-commit-mismatch")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["source_commit"] = "9" * 40

        @control("wrong-binary-hash")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["binary_sha256"] = "9" * 64

        @control("run-worker-outside-protocol")
        def _(campaign: dict[str, Any]) -> None:
            campaign["warmups"][0]["workers"] = 2

        @control("wrong-run-kind")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["kind"] = "warmup"

        @control("nonzero-returncode")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["return_code"] = 1

        @control("invalid-run")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["valid"] = False

        @control("nonpositive-wall")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["wall_seconds"] = 0.0

        @control("empty-cpu-trace")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["cpu_trace"] = []

        @control("nonmonotonic-cpu-elapsed")
        def _(campaign: dict[str, Any]) -> None:
            samples = campaign["timed_runs"][0]["cpu_trace"]
            samples[1]["elapsed_seconds"] = samples[0]["elapsed_seconds"]

        @control("invalid-cpu-sample")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["cpu_trace"][1][
                "processor_total_percent"
            ] = 100.01

        @control("invalid-cpu-summary")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0][
                "processor_total_percent_mean"
            ] += 0.01

        @control("invalid-cpu-min-summary")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0][
                "processor_total_percent_min"
            ] += 0.01

        @control("lowercase-hash")
        def _(campaign: dict[str, Any]) -> None:
            campaign["timed_runs"][0]["pixel_sha256"] = "a" * 64

        @control("broken-adjacency")
        def _(campaign: dict[str, Any]) -> None:
            post = _find_run(
                campaign,
                "timed_runs",
                arm="post",
                workers=1,
                repetition=1,
            )
            following_pre = _find_run(
                campaign,
                "timed_runs",
                arm="pre",
                workers=16,
                repetition=1,
            )
            post["sequence_index"], following_pre["sequence_index"] = (
                following_pre["sequence_index"],
                post["sequence_index"],
            )

        @control("pre-falsely-invariant")
        def _(campaign: dict[str, Any]) -> None:
            for member in ("verification", "timed_runs"):
                for run in campaign[member]:
                    if run["arm"] == "pre" and run["workers"] == 16:
                        run["pixel_sha256"] = "A" * 64
                        run["tiff_sha256"] = "D" * 64

        @control("stale-verification-outcome")
        def _(campaign: dict[str, Any]) -> None:
            campaign["verification_outcome"]["pre_pixel_hashes"]["w1"] = (
                "9" * 64
            )

        @control("post-falsely-non-invariant")
        def _(campaign: dict[str, Any]) -> None:
            for member in ("verification", "timed_runs"):
                for run in campaign[member]:
                    if run["arm"] == "post" and run["workers"] == 16:
                        run["pixel_sha256"] = "8" * 64
                        run["tiff_sha256"] = "7" * 64

        @control("fixed-worker-hash-drift")
        def _(campaign: dict[str, Any]) -> None:
            run = _find_run(
                campaign,
                "timed_runs",
                arm="pre",
                workers=1,
                repetition=2,
            )
            run["pixel_sha256"] = "6" * 64

        @control("fixed-worker-tiff-hash-drift")
        def _(campaign: dict[str, Any]) -> None:
            run = _find_run(
                campaign,
                "timed_runs",
                arm="post",
                workers=16,
                repetition=3,
            )
            run["tiff_sha256"] = "5" * 64

        rejected = 0
        for name, mutate in controls:
            planted = copy.deepcopy(baseline)
            mutate(planted)
            try:
                validate_and_analyze(planted, artifact_base=directory)
            except VerificationError as exc:
                rejected += 1
                print(f"RED-control {name}: rejected ({exc})")
            else:
                raise RuntimeError(
                    f"RED-control {name} was incorrectly accepted"
                )
        print(
            f"SELF-TEST PASS: {rejected}/{len(controls)} planted defects rejected; "
            "known-ratio arithmetic and warm-up exclusion passed"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed validation and paired-ratio analysis for an "
            "M172-throughput-v1 campaign."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=LANE / "results" / "campaign.json",
        help=(
            "campaign JSON (default: "
            "experiments/M172-worker-memory/results/campaign.json)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=LANE / "results" / "summary.json",
        help=(
            "summary JSON (default: "
            "experiments/M172-worker-memory/results/summary.json)"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run deterministic in-memory positive and planted-defect controls",
    )
    return parser


def _print_headlines(summary: Mapping[str, Any]) -> None:
    print(
        "Paired post-repair/pre-repair wall-time ratios "
        "(absolute times are raw observations, not performance claims):"
    )
    workers = summary["protocol"]["workers"]
    by_worker = summary["by_worker"]
    for worker in workers:
        row = by_worker[str(worker)]
        value_range = row["range"]
        print(
            f"W{worker}: median {row['median']:.6f}x; "
            f"IQR {row['iqr_type7']:.6f}x "
            f"(Q1 {row['q1_type7']:.6f}x, Q3 {row['q3_type7']:.6f}x); "
            f"range {value_range['low']:.6f}x.."
            f"{value_range['high']:.6f}x; n={row['count']}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.self_test:
            run_self_test()
            return 0
        campaign = read_campaign(args.input)
        summary = validate_and_analyze(campaign)
        summary["input"] = str(args.input)
        atomic_write_json(args.output, summary)
        _print_headlines(summary)
        print(f"summary: {args.output}")
        return 0
    except (VerificationError, RuntimeError) as exc:
        print(f"verify.py: ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
