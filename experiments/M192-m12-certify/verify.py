#!/usr/bin/env python3
"""Independent structural and numerical verifier for the M192 M12 certificate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROTOCOL_PATH = HERE / "protocol.json"
DEFAULT_RESULTS = HERE / "results"
SHA256_RE = re.compile(r"^[0-9A-F]{64}$")
GIT_RE = re.compile(r"^[0-9a-f]{40}$")


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def reject_constant(value: str) -> None:
    raise VerificationError(f"non-finite JSON constant {value!r}")


def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def strict_json_bytes(payload: bytes, label: str) -> Any:
    require(not payload.startswith(b"\xef\xbb\xbf"), f"{label}: UTF-8 BOM is forbidden")
    try:
        text = payload.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"{label}: invalid UTF-8 JSON: {error}") from error


def read_json(path: Path) -> Any:
    try:
        payload = path.read_bytes()
    except OSError as error:
        raise VerificationError(f"cannot read {path}: {error}") from error
    return strict_json_bytes(payload, str(path))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


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


def strict_records(path: Path) -> list[dict[str, Any]]:
    payload = path.read_bytes()
    require(payload.endswith(b"\n"), f"{path}: JSONL must end in exactly one newline")
    require(not payload.endswith(b"\n\n"), f"{path}: JSONL has a blank terminal record")
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(payload.splitlines(), 1):
        require(raw.strip() == raw and raw, f"{path}:{line_number}: malformed JSONL line")
        value = strict_json_bytes(raw, f"{path}:{line_number}")
        require(isinstance(value, dict), f"{path}:{line_number}: record must be an object")
        rows.append(value)
    return rows


def protocol() -> dict[str, Any]:
    value = read_json(PROTOCOL_PATH)
    require(value.get("schema") == "m192-m12-protocol-v1", "wrong protocol schema")
    return value


def expected_runs(spec: dict[str, Any]) -> list[dict[str, Any]]:
    native = spec["registered_matrix"]["native"]
    modulo = spec["registered_matrix"]["modulo"]
    result: list[dict[str, Any]] = []

    def add(
        *,
        run_id: str,
        phase: str,
        kind: str,
        limit: int,
        workers: int,
        repetition: int | None,
        sweep: str,
        order_index: int,
    ) -> None:
        result.append(
            {
                "sequence_index": len(result),
                "run_id": run_id,
                "phase": phase,
                "kind": kind,
                "limit": limit,
                "workers": workers,
                "repetition": repetition,
                "sweep": sweep,
                "order_index": order_index,
            }
        )

    workers = tuple(int(value) for value in native["workers"])
    for count in native["frame_counts"]:
        count = int(count)
        for order_index, worker in enumerate(workers):
            add(
                run_id=f"native-n{count}-w{worker}-warmup",
                phase="native",
                kind="warmup",
                limit=count,
                workers=worker,
                repetition=None,
                sweep="ascending",
                order_index=order_index,
            )
        for repetition in range(1, int(native["scored_repetitions_per_cell"]) + 1):
            order = workers if repetition % 2 else tuple(reversed(workers))
            sweep = "ascending" if repetition % 2 else "descending"
            for order_index, worker in enumerate(order):
                add(
                    run_id=f"native-n{count}-w{worker}-r{repetition}",
                    phase="native",
                    kind="scored",
                    limit=count,
                    workers=worker,
                    repetition=repetition,
                    sweep=sweep,
                    order_index=order_index,
                )

    modulo_counts = tuple(int(value) for value in modulo["frame_counts"])
    for order_index, count in enumerate(modulo_counts):
        add(
            run_id=f"modulo-n{count}-warmup",
            phase="modulo",
            kind="warmup",
            limit=count,
            workers=int(modulo["workers"]),
            repetition=None,
            sweep="warmup-ascending",
            order_index=order_index,
        )
    for repetition in range(1, int(modulo["scored_sweeps"]) + 1):
        order = modulo_counts if repetition % 2 else tuple(reversed(modulo_counts))
        sweep = "ascending" if repetition % 2 else "descending"
        for order_index, count in enumerate(order):
            add(
                run_id=f"modulo-n{count}-r{repetition}",
                phase="modulo",
                kind="scored",
                limit=count,
                workers=int(modulo["workers"]),
                repetition=repetition,
                sweep=sweep,
                order_index=order_index,
            )
    return result


def coverage(row: dict[str, Any]) -> float:
    memory = row["memory"]
    scheduled = int(memory["sample_count"]) + int(memory["missed_intervals"])
    return int(memory["sample_count"]) / scheduled if scheduled else 0.0


def spread(values: Iterable[float]) -> float:
    items = list(values)
    require(items and min(items) > 0.0, "spread requires positive values")
    return (max(items) - min(items)) / min(items)


def timing_details(
    rows: list[dict[str, Any]],
    sweeps: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    counts = tuple(int(value) for value in spec["registered_matrix"]["modulo"]["frame_counts"])
    scored = [
        row for row in rows if row["phase"] == "modulo" and row["kind"] == "scored"
    ]
    by_rep_n = {
        (int(row["repetition"]), int(row["limit"])): row for row in scored
    }
    complete = (
        len(scored) == 24
        and len(by_rep_n) == 24
        and all((rep, count) in by_rep_n for rep in range(1, 7) for count in counts)
    )
    best_by_n: dict[str, float | None] = {}
    all_by_n: dict[str, list[float]] = {}
    for count in counts:
        values = [
            float(by_rep_n[(rep, count)]["wall_seconds"]) / count
            for rep in range(1, 7)
            if (rep, count) in by_rep_n
        ]
        all_by_n[str(count)] = values
        best_by_n[str(count)] = min(values) if len(values) == 6 else None
    best_values = [value for value in best_by_n.values() if value is not None]
    registered_spread = spread(best_values) if len(best_values) == 4 else None

    pairs: list[dict[str, Any]] = []
    for odd in (1, 3, 5):
        even = odd + 1
        arithmetic: dict[str, float] = {}
        geometric: dict[str, float] = {}
        if complete:
            for count in counts:
                a = float(by_rep_n[(odd, count)]["wall_seconds"]) / count
                b = float(by_rep_n[(even, count)]["wall_seconds"]) / count
                arithmetic[str(count)] = (a + b) / 2.0
                geometric[str(count)] = math.sqrt(a * b)
            arithmetic_spread = spread(arithmetic.values())
            geometric_spread = spread(geometric.values())
            conservative = max(arithmetic_spread, geometric_spread)
        else:
            arithmetic_spread = geometric_spread = conservative = None
        pairs.append(
            {
                "sweeps": [odd, even],
                "arithmetic_seconds_per_frame_by_n": arithmetic,
                "geometric_seconds_per_frame_by_n": geometric,
                "arithmetic_spread": arithmetic_spread,
                "geometric_spread": geometric_spread,
                "conservative_spread": conservative,
            }
        )
    conservative_values = [
        float(row["conservative_spread"])
        for row in pairs
        if row["conservative_spread"] is not None
    ]
    lower = min(conservative_values) if len(conservative_values) == 3 else None
    upper = max(conservative_values) if len(conservative_values) == 3 else None

    expected_sweep_ids = {"modulo-warmup", *(f"modulo-r{rep}" for rep in range(1, 7))}
    actual_sweep_ids = {str(row.get("sweep_id")) for row in sweeps}
    cpu_complete = (
        len(sweeps) == 7
        and actual_sweep_ids == expected_sweep_ids
        and all(
            row.get("trace_valid") is True
            and isinstance(row.get("whole_host_cpu_mean_percent"), (int, float))
            and isinstance(row.get("whole_host_cpu_peak_percent"), (int, float))
            and 0.0 <= float(row["whole_host_cpu_mean_percent"]) <= 100.0
            and 0.0 <= float(row["whole_host_cpu_peak_percent"]) <= 100.0
            and float(row["whole_host_cpu_peak_percent"])
            >= float(row["whole_host_cpu_mean_percent"])
            and len(row.get("run_ids", [])) == 4
            for row in sweeps
        )
    )

    limit = float(spec["bars"]["modulo_per_frame_spread_max"])
    if (
        complete
        and cpu_complete
        and registered_spread is not None
        and upper is not None
        and registered_spread <= limit
        and upper <= limit
    ):
        verdict = "PASS"
    elif (
        complete
        and cpu_complete
        and registered_spread is not None
        and lower is not None
        and registered_spread > limit
        and lower > limit
    ):
        verdict = "FAIL"
    else:
        verdict = "UNMEASURED_HOST_CONTENTION"
    return {
        "complete": complete,
        "host_cpu_complete": cpu_complete,
        "best_wall_seconds_per_frame_by_n": best_by_n,
        "all_wall_seconds_per_frame_by_n": all_by_n,
        "registered_spread": registered_spread,
        "reversal_pairs": pairs,
        "paired_envelope_lower": lower,
        "paired_envelope_upper": upper,
        "verdict": verdict,
    }


def recompute_bars(
    rows: list[dict[str, Any]],
    sweeps: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    native_counts = tuple(int(value) for value in spec["registered_matrix"]["native"]["frame_counts"])
    workers = tuple(int(value) for value in spec["registered_matrix"]["native"]["workers"])
    scored = [
        row for row in rows if row["phase"] == "native" and row["kind"] == "scored"
    ]
    cells: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for count in native_counts:
        for worker in workers:
            cells[(count, worker)] = [
                row
                for row in scored
                if int(row["limit"]) == count and int(row["workers"]) == worker
            ]
    matrix_complete = len(scored) == 90 and all(
        len(cells[(count, worker)]) == 6
        and {int(row["repetition"]) for row in cells[(count, worker)]}
        == set(range(1, 7))
        for count in native_counts
        for worker in workers
    )
    sample_rows = []
    for row in scored:
        value = coverage(row)
        sample_rows.append(
            {
                "run_id": row["run_id"],
                "coverage": value,
                "max_gap_ms": float(row["memory"]["max_gap_ms"]),
                "pass": (
                    value >= float(spec["memory_admission"]["coverage_min"])
                    and float(row["memory"]["max_gap_ms"])
                    <= float(spec["memory_admission"]["maximum_sample_gap_ms"])
                ),
            }
        )
    sampling_pass = matrix_complete and all(row["pass"] for row in sample_rows)

    sampled_peak = max(
        (
            int(row["memory"]["peak_process_tree_private_committed_bytes"])
            for row in scored
        ),
        default=0,
    )
    job_peak = max(
        (
            int(row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"])
            for row in scored
        ),
        default=0,
    )
    memory_limit = int(spec["bars"]["warm_peak_process_tree_bytes_max"])
    if max(sampled_peak, job_peak) > memory_limit:
        memory_verdict = "FAIL"
    elif matrix_complete and sampling_pass and job_peak > 0:
        memory_verdict = "PASS"
    else:
        memory_verdict = "UNMEASURED_SAMPLING_COVERAGE"

    fixed: dict[str, Any] = {}
    fixed_pass = matrix_complete
    for count in native_counts:
        for worker in workers:
            members = cells[(count, worker)]
            files = sorted({str(row["output_sha256"]) for row in members})
            pixels = sorted({str(row["pixel_sha256"]) for row in members})
            cell_pass = len(members) == 6 and len(files) == 1 and len(pixels) == 1
            fixed_pass = fixed_pass and cell_pass
            fixed[f"N{count}-W{worker}"] = {
                "runs": len(members),
                "complete_file_hashes": files,
                "canonical_pixel_hashes": pixels,
                "pass": cell_pass,
            }
    cross: dict[str, Any] = {}
    cross_pass = matrix_complete
    for count in native_counts:
        members = [
            row for row in scored if int(row["limit"]) == count
        ]
        files = sorted({str(row["output_sha256"]) for row in members})
        pixels = sorted({str(row["pixel_sha256"]) for row in members})
        value = len(members) == 30 and len(files) == 1 and len(pixels) == 1
        cross_pass = cross_pass and value
        cross[str(count)] = {
            "runs": len(members),
            "complete_file_hashes": files,
            "canonical_pixel_hashes": pixels,
            "pass": value,
        }
    if not matrix_complete:
        identity_verdict = "UNMEASURED_INCOMPLETE_MATRIX"
    elif fixed_pass and cross_pass:
        identity_verdict = "PASS"
    else:
        identity_verdict = "FAIL"

    sampled_by_worker: dict[str, float | None] = {}
    job_by_worker: dict[str, float | None] = {}
    for worker in workers:
        n33 = cells[(33, worker)]
        n299 = cells[(299, worker)]
        if len(n33) == 6 and len(n299) == 6:
            s33 = max(
                int(row["memory"]["peak_process_tree_private_committed_bytes"])
                for row in n33
            )
            s299 = max(
                int(row["memory"]["peak_process_tree_private_committed_bytes"])
                for row in n299
            )
            j33 = max(
                int(row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"])
                for row in n33
            )
            j299 = max(
                int(row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"])
                for row in n299
            )
            sampled_by_worker[str(worker)] = s299 / s33
            job_by_worker[str(worker)] = j299 / j33
        else:
            sampled_by_worker[str(worker)] = None
            job_by_worker[str(worker)] = None
    sampled_values = [value for value in sampled_by_worker.values() if value is not None]
    job_values = [value for value in job_by_worker.values() if value is not None]
    sampled_ratio = max(sampled_values) if len(sampled_values) == 5 else None
    job_ratio = max(job_values) if len(job_values) == 5 else None
    conservative_ratio = (
        max(float(sampled_ratio), float(job_ratio))
        if sampled_ratio is not None and job_ratio is not None
        else None
    )
    ratio_limit = float(spec["bars"]["peak_n299_over_peak_n33_max"])
    if not matrix_complete or not sampling_pass:
        ratio_verdict = "UNMEASURED_SAMPLING_COVERAGE"
    elif conservative_ratio is not None and conservative_ratio <= ratio_limit:
        ratio_verdict = "PASS"
    else:
        ratio_verdict = "FAIL"

    timing = timing_details(rows, sweeps, spec)
    bars = {
        "warm_peak_process_tree_memory": {
            "sampled_peak_bytes": sampled_peak,
            "job_peak_bytes": job_peak,
            "limit_bytes": memory_limit,
            "sampling_minimum_coverage": min(
                (row["coverage"] for row in sample_rows), default=None
            ),
            "sampling_maximum_gap_ms": max(
                (row["max_gap_ms"] for row in sample_rows), default=None
            ),
            "verdict": memory_verdict,
        },
        "byte_identity": {
            "fixed_worker": fixed,
            "cross_worker": cross,
            "verdict": identity_verdict,
        },
        "peak_n299_over_peak_n33": {
            "sampled_by_worker": sampled_by_worker,
            "job_by_worker": job_by_worker,
            "sampled_max": sampled_ratio,
            "job_max": job_ratio,
            "conservative_max": conservative_ratio,
            "limit": ratio_limit,
            "minimum_sampling_coverage": min(
                (row["coverage"] for row in sample_rows), default=None
            ),
            "verdict": ratio_verdict,
        },
        "n_mod_4_per_frame_spread": timing,
    }
    verdicts = [str(value["verdict"]) for value in bars.values()]
    pass_count = sum(value == "PASS" for value in verdicts)
    fail_count = sum(value == "FAIL" for value in verdicts)
    unmeasured_count = 4 - pass_count - fail_count
    require(pass_count + fail_count + unmeasured_count == 4, "bar partition is not four")
    if fail_count:
        overall = "FAIL"
    elif pass_count == 4:
        overall = "PASS"
    else:
        overall = "UNMEASURED"
    return {
        "matrix_complete": matrix_complete,
        "sampling_quality": {
            "pass": sampling_pass,
            "minimum_coverage": min(
                (row["coverage"] for row in sample_rows), default=None
            ),
            "maximum_gap_ms": max(
                (row["max_gap_ms"] for row in sample_rows), default=None
            ),
            "failed_runs": [row["run_id"] for row in sample_rows if not row["pass"]],
        },
        "bars": bars,
        "partition": {
            "pass": pass_count,
            "fail": fail_count,
            "unmeasured": unmeasured_count,
            "total": 4,
        },
        "overall_verdict": overall,
    }


def validate_record_structure(
    rows: list[dict[str, Any]],
    spec: dict[str, Any],
    results: Path | None,
) -> None:
    expected = expected_runs(spec)
    require(len(rows) == len(expected) == 133, f"expected 133 records, got {len(rows)}")
    campaign_ids = {str(row.get("campaign_id")) for row in rows}
    require(len(campaign_ids) == 1 and next(iter(campaign_ids)), "campaign_id is not unique")
    previous = "0" * 64
    binary_hashes: set[str] = set()
    output_bytes: set[int] = set()
    for index, (actual, wanted) in enumerate(zip(rows, expected, strict=True)):
        require(actual.get("schema") == "m192-run-v1", f"record {index}: wrong schema")
        for key, value in wanted.items():
            require(actual.get(key) == value, f"record {index}: {key} drifted")
        require(actual.get("measured_commit") == spec["lineage"]["measured_commit"], f"record {index}: wrong commit")
        digest = str(actual.get("record_sha256"))
        require(SHA256_RE.fullmatch(digest) is not None, f"record {index}: bad record hash")
        require(actual.get("previous_record_sha256") == previous, f"record {index}: broken hash chain")
        require(canonical_record_hash(actual) == digest, f"record {index}: record hash mismatch")
        previous = digest
        require(actual.get("valid") is True and actual.get("returncode") == 0, f"record {index}: invalid run")
        require(actual.get("artifact_cleanup", {}).get("output_removed") is True, f"record {index}: output cleanup absent")
        require(actual.get("terminal_witness", {}).get("all") is True, f"record {index}: terminal witness absent")
        require(actual.get("shape") == [4688, 7032, 3], f"record {index}: wrong TIFF shape")
        require(actual.get("dtype") == "uint16", f"record {index}: wrong TIFF dtype")
        require(actual.get("bits_per_sample") == 16, f"record {index}: wrong TIFF depth")
        require(actual.get("samples_per_pixel") == 3, f"record {index}: wrong TIFF channels")
        require(SHA256_RE.fullmatch(str(actual.get("output_sha256"))) is not None, f"record {index}: bad file hash")
        require(SHA256_RE.fullmatch(str(actual.get("pixel_sha256"))) is not None, f"record {index}: bad pixel hash")
        require(spec["lineage"]["measured_commit"] in str(actual.get("software")), f"record {index}: Software tag lacks commit")
        binary_hash = str(actual.get("binary", {}).get("sha256"))
        require(SHA256_RE.fullmatch(binary_hash) is not None, f"record {index}: bad binary hash")
        binary_hashes.add(binary_hash)
        output_bytes.add(int(actual.get("output_bytes", 0)))
        memory = actual.get("memory", {})
        require(memory.get("process_tree_membership_source") == "Windows Job Object", f"record {index}: wrong memory source")
        require(int(memory.get("sample_count", 0)) > 0, f"record {index}: no memory samples")
        require(memory.get("kernel_job_accounting", {}).get("active_processes") == 0, f"record {index}: process tree did not finish")
        require(memory.get("kernel_job_accounting", {}).get("total_processes", 0) >= 1, f"record {index}: no process accounted")
        for stream in ("stdout", "stderr"):
            log = actual.get("log_artifacts", {}).get(stream, {})
            require(SHA256_RE.fullmatch(str(log.get("sha256"))) is not None, f"record {index}: bad {stream} hash")
            require(int(log.get("bytes", 0)) > 0, f"record {index}: empty {stream} log")
            if results is not None:
                path = (results / str(log.get("path"))).resolve()
                require(os.path.commonpath((str(results.resolve()), str(path))) == str(results.resolve()), f"record {index}: log escapes results")
                require(path.is_file(), f"record {index}: missing {stream} log")
                require(path.stat().st_size == int(log["bytes"]), f"record {index}: {stream} byte count mismatch")
                require(sha256_file(path) == log["sha256"], f"record {index}: {stream} hash mismatch")
    require(len(binary_hashes) == 1, f"records use {len(binary_hashes)} executable hashes")
    require(len(output_bytes) == 1 and next(iter(output_bytes)) >= 197_796_096, "TIFF byte lengths are incomplete or inconsistent")


def git_output(*arguments: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(ROOT), *arguments],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise VerificationError(
            f"git {' '.join(arguments)} failed: {result.stderr.decode('utf-8', 'replace')}"
        )
    return result.stdout


def verify_artifact(results: Path) -> dict[str, Any]:
    spec = protocol()
    require(results.is_dir(), f"results directory is missing: {results}")
    copied_protocol = results / "protocol.json"
    require(copied_protocol.is_file(), "results/protocol.json is missing")
    require(copied_protocol.read_bytes() == PROTOCOL_PATH.read_bytes(), "protocol copy drifted")
    rows = strict_records(results / "records.jsonl")
    sweeps = read_json(results / "sweeps.json")
    require(isinstance(sweeps, list), "sweeps.json must be an array")
    validate_record_structure(rows, spec, results)
    recomputed = recompute_bars(rows, sweeps, spec)

    certificate = read_json(results / "certificate.json")
    require(certificate.get("schema") == "m192-m12-certificate-v1", "wrong certificate schema")
    require(certificate.get("lineage", {}).get("measured_commit") == spec["lineage"]["measured_commit"], "certificate commit drifted")
    require(certificate.get("bars") == recomputed["bars"], "certificate bars do not recompute")
    require(certificate.get("partition") == recomputed["partition"], "certificate partition does not recompute")
    require(certificate.get("overall_verdict") == recomputed["overall_verdict"], "certificate overall verdict does not recompute")

    inputs_before = read_json(results / "inputs-before.json")
    inputs_after = read_json(results / "inputs-after.json")
    require(inputs_before.get("files") == inputs_after.get("files"), "input bytes or metadata changed")
    require(inputs_before.get("selected_file_count") == 404, "expected 404 selected input files")
    require(inputs_after.get("selected_file_count") == 404, "post-run input count drifted")

    build = read_json(results / "builds.json")
    measured = build["measured"]
    require(measured["commit"] == spec["lineage"]["measured_commit"], "build commit drifted")
    require(measured["tree"] == spec["lineage"]["measured_tree"], "build tree drifted")
    require(SHA256_RE.fullmatch(measured["binary_sha256"]) is not None, "bad binary hash")
    require(measured["binary_sha256"] == rows[0]["binary"]["sha256"], "record/build binary hashes differ")
    require(spec["lineage"]["measured_commit"] in measured["version_output"], "binary version lacks commit")
    for name in ("measured", "unrepaired"):
        log = results / build[name]["build_log"]
        require(log.is_file(), f"missing {name} build log")
        require(sha256_file(log) == build[name]["build_log_sha256"], f"{name} build log hash drifted")
        text = log.read_text(encoding="utf-8", errors="replace")
        require("Compiling strehl-cli" in text, f"{name} build did not visibly compile strehl-cli")

    for ancestor in spec["lineage"]["required_ancestry"]:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", ancestor, spec["lineage"]["measured_commit"]]
        )
        require(result.returncode == 0, f"required ancestor absent: {ancestor}")
    diff = git_output(
        "diff",
        "--binary",
        spec["lineage"]["bounded_memory_repair_commit"],
        spec["lineage"]["measured_commit"],
        "--",
        *spec["lineage"]["repair_owned_paths"],
    )
    require(diff == b"", "repair-owned source differs after bounded repair")

    sidecars = read_json(results / "sidecars.json")
    require(len(sidecars.get("sidecars", [])) == 7, "sidecar set is incomplete")
    for row in sidecars["sidecars"]:
        path = results / row["artifact_path"]
        require(path.is_file(), f"missing sidecar {path}")
        require(path.stat().st_size == row["bytes"], f"sidecar length mismatch: {path}")
        require(sha256_file(path) == row["sha256"], f"sidecar hash mismatch: {path}")
        text = path.read_text(encoding="utf-8")
        require(
            f"frames {row['n']}" in text
            and row.get("header_frames") == row["n"]
            and "resampler catmull-rom" in text
            and row.get("header_resampler") == "catmull-rom",
            f"sidecar header validation failed: {path}",
        )

    commission = read_json(results / "commission.json")
    require(commission.get("status") == "COMMISSIONED", "instrument commission did not pass")
    gates = commission["gates"]
    require(gates["unrepaired_worker_gate_red"], "unrepaired worker gate stayed green")
    require(gates["unrepaired_memory_gate_red"], "unrepaired memory gate stayed green")
    require(gates["memory_null_green"], "memory null failed")
    require(gates["memory_plant_red"], "memory plant stayed green")
    require(gates["file_lsb_red"] and gates["pixel_lsb_red"], "LSB hash plant stayed green")
    require(gates["verifier_self_test_green"], "verifier self-test failed")

    complete = read_json(results / "campaign-complete.json")
    require(complete.get("schema") == "m192-campaign-complete-v1", "wrong terminal schema")
    require(complete.get("record_count") == 133, "terminal record count is not 133")
    require(complete.get("last_record_sha256") == rows[-1]["record_sha256"], "terminal chain hash drifted")
    for relative, digest in complete["artifact_sha256"].items():
        path = results / relative
        require(path.is_file(), f"terminal artifact missing: {relative}")
        require(sha256_file(path) == digest, f"terminal artifact hash drifted: {relative}")

    outcome = {
        "schema": "m192-verification-v1",
        "status": "PASS",
        "record_count": len(rows),
        "binary_sha256": rows[0]["binary"]["sha256"],
        "minimum_sampling_coverage": recomputed["sampling_quality"]["minimum_coverage"],
        "maximum_sampling_gap_ms": recomputed["sampling_quality"]["maximum_gap_ms"],
        "partition": recomputed["partition"],
        "overall_verdict": recomputed["overall_verdict"],
    }
    return outcome


def synthetic_fixture(spec: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    previous = "0" * 64
    hashes = {33: "A" * 64, 105: "B" * 64, 299: "C" * 64}
    for wanted in expected_runs(spec):
        count = int(wanted["limit"])
        if wanted["phase"] == "native":
            output_hash = hashes[count]
            pixel_hash = hashes[count]
            peak = 3_000_000_000 + int(wanted["workers"]) * 100_000
            wall = count * 0.1
        else:
            output_hash = chr(65 + count - 96) * 64
            pixel_hash = output_hash
            base = 1.0 + (count - 96) * 0.003
            repetition = int(wanted["repetition"] or 0)
            drift = 1.0 + repetition * 0.001
            wall = count * base * drift
            peak = 3_000_000_000
        row: dict[str, Any] = {
            "schema": "m192-run-v1",
            "campaign_id": "synthetic",
            **wanted,
            "measured_commit": spec["lineage"]["measured_commit"],
            "returncode": 0,
            "valid": True,
            "wall_seconds": wall,
            "output_bytes": 197_798_956,
            "output_sha256": output_hash,
            "pixel_sha256": pixel_hash,
            "shape": [4688, 7032, 3],
            "dtype": "uint16",
            "bits_per_sample": 16,
            "samples_per_pixel": 3,
            "software": f"strehl 0.0.0 ({spec['lineage']['measured_commit']})",
            "binary": {"sha256": "D" * 64},
            "memory": {
                "sample_count": 100,
                "missed_intervals": 0,
                "max_gap_ms": 10.0,
                "process_tree_membership_source": "Windows Job Object",
                "peak_process_tree_private_committed_bytes": peak,
                "kernel_job_peak_memory": {"peak_job_memory_used_bytes": peak},
                "kernel_job_accounting": {
                    "active_processes": 0,
                    "total_processes": 1,
                    "total_cpu_100ns": int(wall * 10_000_000),
                },
            },
            "terminal_witness": {"all": True},
            "artifact_cleanup": {"output_removed": True},
            "log_artifacts": {
                "stdout": {"path": "logs/x", "bytes": 1, "sha256": "E" * 64},
                "stderr": {"path": "logs/y", "bytes": 1, "sha256": "F" * 64},
            },
            "previous_record_sha256": previous,
        }
        row["record_sha256"] = canonical_record_hash(row)
        previous = row["record_sha256"]
        rows.append(row)
    sweeps = []
    for name in ("modulo-warmup", *(f"modulo-r{rep}" for rep in range(1, 7))):
        sweeps.append(
            {
                "sweep_id": name,
                "trace_valid": True,
                "whole_host_cpu_mean_percent": 40.0,
                "whole_host_cpu_peak_percent": 50.0,
                "run_ids": ["a", "b", "c", "d"],
            }
        )
    return rows, sweeps


def reseal(rows: list[dict[str, Any]]) -> None:
    previous = "0" * 64
    for index, row in enumerate(rows):
        row["sequence_index"] = index
        row["previous_record_sha256"] = previous
        row["record_sha256"] = canonical_record_hash(row)
        previous = row["record_sha256"]


def self_test(output: Path | None) -> dict[str, Any]:
    spec = protocol()
    base_rows, base_sweeps = synthetic_fixture(spec)
    validate_record_structure(base_rows, spec, None)
    base = recompute_bars(base_rows, base_sweeps, spec)
    require(base["overall_verdict"] == "PASS", "synthetic null did not pass")
    controls: list[dict[str, Any]] = []

    def control(name: str, mutate: Any, predicate: Any) -> None:
        rows = copy.deepcopy(base_rows)
        sweeps = copy.deepcopy(base_sweeps)
        mutate(rows, sweeps)
        caught = False
        detail = ""
        try:
            validate_record_structure(rows, spec, None)
            value = recompute_bars(rows, sweeps, spec)
            caught = bool(predicate(value))
            detail = value["overall_verdict"]
        except VerificationError as error:
            caught = True
            detail = str(error)
        controls.append({"name": name, "caught": caught, "detail": detail})

    control(
        "missing-terminal-record",
        lambda rows, sweeps: rows.pop(),
        lambda value: False,
    )
    control(
        "broken-hash-chain",
        lambda rows, sweeps: rows[10].__setitem__("previous_record_sha256", "A" * 64),
        lambda value: False,
    )

    def diverge(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        row = next(
            row
            for row in rows
            if row["phase"] == "native"
            and row["kind"] == "scored"
            and row["limit"] == 33
            and row["workers"] == 16
        )
        row["output_sha256"] = "9" * 64
        row["pixel_sha256"] = "8" * 64
        reseal(rows)

    control(
        "worker-hash-divergence",
        diverge,
        lambda value: value["bars"]["byte_identity"]["verdict"] == "FAIL",
    )

    def memory_fail(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        row = next(row for row in rows if row["phase"] == "native" and row["kind"] == "scored")
        row["memory"]["peak_process_tree_private_committed_bytes"] = 7 << 30
        row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"] = 7 << 30
        reseal(rows)

    control(
        "memory-overrun",
        memory_fail,
        lambda value: value["bars"]["warm_peak_process_tree_memory"]["verdict"] == "FAIL",
    )

    def ratio_fail(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        for row in rows:
            if row["phase"] == "native" and row["kind"] == "scored" and row["limit"] == 299:
                row["memory"]["peak_process_tree_private_committed_bytes"] = 3_700_000_000
                row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"] = 3_700_000_000
        reseal(rows)

    control(
        "ratio-overrun",
        ratio_fail,
        lambda value: value["bars"]["peak_n299_over_peak_n33"]["verdict"] == "FAIL",
    )

    def coverage_fail(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        row = next(row for row in rows if row["phase"] == "native" and row["kind"] == "scored")
        row["memory"]["sample_count"] = 89
        row["memory"]["missed_intervals"] = 11
        reseal(rows)

    control(
        "sampling-undercoverage",
        coverage_fail,
        lambda value: value["bars"]["peak_n299_over_peak_n33"]["verdict"]
        == "UNMEASURED_SAMPLING_COVERAGE",
    )

    def timing_fail(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        for row in rows:
            if row["phase"] == "modulo" and row["kind"] == "scored" and row["limit"] == 99:
                row["wall_seconds"] *= 1.08
        reseal(rows)

    control(
        "timing-overrun",
        timing_fail,
        lambda value: value["bars"]["n_mod_4_per_frame_spread"]["verdict"] == "FAIL",
    )

    def timing_ambiguous(rows: list[dict[str, Any]], sweeps: list[dict[str, Any]]) -> None:
        for row in rows:
            if (
                row["phase"] == "modulo"
                and row["kind"] == "scored"
                and row["limit"] == 99
                and row["repetition"] in (1, 2)
            ):
                row["wall_seconds"] *= 1.08
        reseal(rows)

    control(
        "timing-contention-ambiguity",
        timing_ambiguous,
        lambda value: value["bars"]["n_mod_4_per_frame_spread"]["verdict"]
        == "UNMEASURED_HOST_CONTENTION",
    )
    control(
        "missing-sweep-cpu",
        lambda rows, sweeps: sweeps.pop(),
        lambda value: value["bars"]["n_mod_4_per_frame_spread"]["verdict"]
        == "UNMEASURED_HOST_CONTENTION",
    )

    inert_rows = copy.deepcopy(base_rows)
    inert_rows[0]["inert_label"] = "changed"
    reseal(inert_rows)
    validate_record_structure(inert_rows, spec, None)
    inert = recompute_bars(inert_rows, copy.deepcopy(base_sweeps), spec)
    inert_green = inert["overall_verdict"] == "PASS"
    result = {
        "schema": "m192-verifier-self-test-v1",
        "status": (
            "COMMISSIONED"
            if all(row["caught"] for row in controls) and inert_green
            else "FAILED"
        ),
        "controls": controls,
        "caught": sum(row["caught"] for row in controls),
        "total": len(controls),
        "inert_label_survived": inert_green,
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    return result


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--artifact", type=Path)
    result.add_argument("--output", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.self_test:
            result = self_test(args.output)
        else:
            result = verify_artifact(args.artifact.resolve())
            if args.output is not None:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(result, indent=2) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
        print(json.dumps(result, indent=2))
        return 0 if result.get("status") in {"PASS", "COMMISSIONED"} else 1
    except Exception as error:
        print(f"VERIFY ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
