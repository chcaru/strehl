"""Read-only diagnosis of the completed M192 measurement, without RAW access.

Rejection controls: a constant ordered timing series must have no step; a planted
10% step must be found at its actual transition. A known 101-ms sampler gap must
remain over the frozen 100-ms bar. These describe diagnostics, not new score bars.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def spread(values: list[float]) -> float:
    return (max(values) - min(values)) / min(values)


def largest_step(values: list[float]) -> dict:
    changes = [(values[i] / values[i - 1] - 1.0, i) for i in range(1, len(values))]
    fraction, index = max(changes, key=lambda pair: abs(pair[0]))
    return {"destination_index": index, "fraction": fraction}


def sampling_admissible(coverage: float, gap_ms: float, minimum: float, maximum: float) -> bool:
    return coverage >= minimum and gap_ms <= maximum


def self_test() -> None:
    assert largest_step([1.0] * 8)["fraction"] == 0.0
    planted = largest_step([1.0] * 4 + [0.9] * 4)
    assert planted["destination_index"] == 4
    assert abs(planted["fraction"] + 0.1) < 1e-12
    assert sampling_admissible(0.99, 99.0, 0.90, 100.0)
    assert not sampling_admissible(0.99, 101.0, 0.90, 100.0)
    assert not sampling_admissible(0.89, 99.0, 0.90, 100.0)


def main() -> None:
    self_test()
    before: dict[Path, str] = {}

    def read(path: Path) -> bytes:
        resolved = path.resolve()
        assert resolved.is_relative_to(RESULTS.resolve())
        payload = resolved.read_bytes()
        before[resolved] = digest(payload)
        return payload

    rows = [json.loads(line) for line in read(RESULTS / "records.jsonl").splitlines()]
    protocol = json.loads(read(RESULTS / "protocol.json"))
    certificate = json.loads(read(RESULTS / "certificate.json"))
    sweeps = json.loads(read(RESULTS / "sweeps.json"))

    def summary(row: dict) -> dict:
        memory = row["memory"]
        host = row["host_load_during_run"]
        samples = memory["sample_count"]
        missed = memory["missed_intervals"]
        stderr = read(RESULTS / row["log_artifacts"]["stderr"]["path"]).decode("utf-8")
        fold_match = re.search(r"(?m)^folded\s+:\s+\d+\s+/\s+\d+ frames in ([\d.]+) s", stderr)
        assert fold_match
        return {
            "run_id": row["run_id"],
            "kind": row["kind"],
            "n": row["limit"],
            "workers": row["workers"],
            "repetition": row["repetition"],
            "started_utc": row["started_utc"],
            "completed_utc": row["completed_utc"],
            "wall_seconds": row["wall_seconds"],
            "wall_seconds_per_frame": row["wall_seconds"] / row["limit"],
            "product_cpu_seconds_per_frame": host["process_tree_cpu_seconds"] / row["limit"],
            "product_fold_seconds_per_frame_rounded_log": float(fold_match[1]) / row["limit"],
            "host_cpu_mean_percent": row["whole_host_cpu_mean_percent"],
            "external_busy_fraction": host["external_busy_fraction_of_wall_capacity"],
            "sample_count": samples,
            "missed_intervals": missed,
            "coverage": samples / (samples + missed),
            "max_gap_ms": memory["max_gap_ms"],
            "median_gap_ms": memory["median_gap_ms"],
            "max_lateness_ms": memory["max_lateness_ms"],
            "sampled_peak_bytes": memory["peak_process_tree_private_committed_bytes"],
            "job_peak_bytes": memory["kernel_job_peak_memory"]["peak_job_memory_used_bytes"],
            "temp_peak_bytes": memory["peak_temp_file_bytes"],
            "process_count": memory["kernel_job_accounting"]["total_processes"],
            "memory_load_start_percent": host["memory_start"]["memory_load_percent"],
            "memory_load_end_percent": host["memory_end"]["memory_load_percent"],
        }

    native = [summary(row) for row in rows if row["phase"] == "native" and row["kind"] == "scored"]
    modulo = [summary(row) for row in rows if row["phase"] == "modulo"]
    scored = [row for row in modulo if row["kind"] == "scored"]
    timing = [row["wall_seconds_per_frame"] for row in scored]
    step = largest_step(timing)
    index = step["destination_index"]
    failed = [row for row in native if not sampling_admissible(row["coverage"], row["max_gap_ms"], protocol["memory_admission"]["coverage_min"], protocol["memory_admission"]["maximum_sample_gap_ms"])]
    counts = protocol["registered_matrix"]["modulo"]["frame_counts"]
    minima = {str(n): min(row["wall_seconds_per_frame"] for row in scored if row["n"] == n) for n in counts}
    pairs = []
    for odd in (1, 3, 5):
        means = {"arithmetic": [], "geometric": []}
        for n in counts:
            values = [row["wall_seconds_per_frame"] for row in scored if row["n"] == n and row["repetition"] in (odd, odd + 1)]
            assert len(values) == 2
            means["arithmetic"].append(sum(values) / 2)
            means["geometric"].append(math.sqrt(math.prod(values)))
        pairs.append({"repetitions": [odd, odd + 1], **{name + "_spread": spread(values) for name, values in means.items()}})
    original_timing = certificate["bars"]["n_mod_4_per_frame_spread"]
    assert spread(list(minima.values())) == original_timing["registered_spread"]
    assert [row["run_id"] for row in failed] == certificate["sampling_quality"]["failed_runs"]
    same_n_changes = []
    for n in counts:
        ladder = sorted([row for row in scored if row["n"] == n], key=lambda row: row["repetition"])
        for a, b in zip(ladder, ladder[1:]):
            same_n_changes.append({
                "from": a["run_id"], "to": b["run_id"],
                "wall_fraction_change": b["wall_seconds_per_frame"] / a["wall_seconds_per_frame"] - 1,
                "product_cpu_fraction_change": b["product_cpu_seconds_per_frame"] / a["product_cpu_seconds_per_frame"] - 1,
            })
    trace_summaries = []
    for sweep in sweeps:
        timestamps = [0.0] + [row["elapsed_seconds"] for row in sweep["trace"]] + [sweep["elapsed_seconds"]]
        trace_summaries.append({
            "sweep_id": sweep["sweep_id"], "trace_valid": sweep["trace_valid"],
            "trace_samples": len(sweep["trace"]),
            "max_trace_gap_seconds": max(b-a for a,b in zip(timestamps,timestamps[1:])),
            "host_cpu_mean_percent": sweep["whole_host_cpu_mean_percent"],
            "host_cpu_peak_percent": sweep["whole_host_cpu_peak_percent"],
        })
    result = {
        "scope": "Diagnostic continuation only. Registered verdicts unchanged; no RAW opened.",
        "controls": "constant timing and planted step controls passed; frozen 100-ms bar retained",
        "record_count": len(rows),
        "native_scored_count": len(native),
        "failed_sampler_rows": failed,
        "native_gap_top_twelve": sorted(native, key=lambda row: row["max_gap_ms"], reverse=True)[:12],
        "native_global_peak_bytes": max(row["job_peak_bytes"] for row in native),
        "native_maximum_sampled_job_difference_bytes": max(abs(row["job_peak_bytes"] - row["sampled_peak_bytes"]) for row in native),
        "minimum_raw_spread": spread(list(minima.values())),
        "paired_spreads": pairs,
        "largest_consecutive_timing_step": {**step, "from": scored[index - 1], "to": scored[index]},
        "same_n_temporal_changes": same_n_changes,
        "all_modulo_rows": modulo,
        "sweep_trace_summaries": trace_summaries,
        "sample_trace_limitation": "Native memory records retain aggregate maximum/median gaps but no timestamp or phase duration for the failed sample. Native runs have no per-second host trace.",
    }
    assert all(digest(path.read_bytes()) == value for path, value in before.items()), "frozen input changed during read"
    result["read_only_inputs"] = {str(path.relative_to(ROOT)): value for path, value in before.items()}
    (HERE / "diagnosis.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("record_count", "native_scored_count", "native_global_peak_bytes", "native_maximum_sampled_job_difference_bytes", "minimum_raw_spread", "paired_spreads")}, indent=2))


if __name__ == "__main__":
    main()
