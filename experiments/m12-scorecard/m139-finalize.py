import argparse
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path


MEASURED_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
COUNTS = (33, 105, 299)
WORKERS = (1, 2, 4, 8, 16)
MODULO_COUNTS = (96, 97, 98, 99)
SIX_GIB = 6 * (1 << 30)
LOCAL_ONLY_ROOT_LOGS = {
    "build-archive.log",
    "build-release.log",
    "commission-archive.log",
    "commission-build-initial.log",
    "commission-build-planted.log",
    "commission-build-restored.log",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def row_id(row: dict) -> tuple:
    return (
        row.get("position_key"),
        row.get("attempt"),
        row.get("started_utc"),
        row.get("completed_utc"),
    )


def validated_invalidation(artifact_value: dict) -> tuple[int, set[tuple]]:
    records = artifact_value["records"]
    backup = Path(records["backup_path"])
    if not backup.exists() or sha256(backup) != records["backup_sha256"]:
        raise RuntimeError(f"invalid invalidation backup: {backup}")
    backup_rows = {
        row_id(row): row
        for row in (
            json.loads(line)
            for line in backup.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    affected = records["affected"]
    affected_ids = {row_id(row) for row in affected}
    if len(affected_ids) != len(affected):
        raise RuntimeError("duplicate row in invalidation artifact")
    accepted = 0
    for affected_row in affected:
        identity = row_id(affected_row)
        if identity in backup_rows:
            was_accepted = (
                backup_rows[identity].get("accepted_for_protocol") is True
            )
        elif "original_accepted_for_protocol" in affected_row:
            was_accepted = (
                affected_row["original_accepted_for_protocol"] is True
            )
        else:
            raise RuntimeError(
                "cannot reconstruct invalidated row acceptance: "
                f"{identity}"
            )
        accepted += was_accepted
    if accepted != records["accepted_rows_invalidated"]:
        raise RuntimeError("invalidation artifact acceptance count mismatch")
    return accepted, affected_ids


def latest_preload_contenders(row: dict) -> list[dict]:
    attempts = row.get("preload_gate", {}).get("attempts", [])
    if not attempts:
        return []
    names = {"cargo.exe", "rustc.exe", "link.exe", "strehl.exe", "exiftool.exe"}
    return [
        process
        for process in attempts[-1].get("top_process_cpu", [])
        if str(process.get("name", "")).lower() in names
    ]


def artifact(path: Path) -> dict:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign-root", type=Path, required=True)
    args = parser.parse_args()
    root = args.campaign_root.resolve()

    paths = {
        name: root / filename
        for name, filename in {
            "manifest": "RUN-MANIFEST.json",
            "registration": "registration.json",
            "input_manifest": "input-manifest.json",
            "records": "records.jsonl",
            "summary": "summary.json",
            "memory_commission": "memory-commission.json",
            "determinism_commission": "determinism-commission.json",
            "smoke": "smoke.json",
            "host_start": "host-start.json",
            "host_end": "host-end.json",
            "read_only_before": "read-only-before.json",
            "read_only_after": "read-only-after.json",
            "m172_invalidation": "m172-overlap-invalidation.json",
            "modulo_window_invalidation": "final-modulo-window-invalidation.json",
            "tail_invalidation": "final-window-tail-invalidation.json",
            "final_window_gate": "final-window-start-r4.json",
            "runtime_quiesce": "runtime-quiesce-final.json",
            "closeout": "closeout.json",
            "audit": "audit.json",
        }.items()
    }
    missing = [str(path) for key, path in paths.items() if key not in {"closeout", "audit"} and not path.exists()]
    if missing:
        raise RuntimeError("missing finalization inputs:\n" + "\n".join(missing))

    manifest = read_json(paths["manifest"])
    registration = read_json(paths["registration"])
    summary = read_json(paths["summary"])
    memory_commission = read_json(paths["memory_commission"])
    determinism_commission = read_json(paths["determinism_commission"])
    smoke = read_json(paths["smoke"])
    host_start = read_json(paths["host_start"])
    host_end = read_json(paths["host_end"])
    read_only_before = read_json(paths["read_only_before"])
    read_only_after = read_json(paths["read_only_after"])
    m172_invalidation = read_json(paths["m172_invalidation"])
    modulo_window_invalidation = read_json(paths["modulo_window_invalidation"])
    tail_invalidation = read_json(paths["tail_invalidation"])
    final_window_gate = read_json(paths["final_window_gate"])
    runtime_quiesce = read_json(paths["runtime_quiesce"])
    rows = [
        json.loads(line)
        for line in paths["records"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    if manifest["measured_commit"] != MEASURED_COMMIT:
        raise RuntimeError("manifest measured commit mismatch")
    if any(row.get("measured_commit") != MEASURED_COMMIT for row in rows):
        raise RuntimeError("record measured commit mismatch")
    for value in (
        registration,
        summary,
        memory_commission,
        determinism_commission,
        smoke,
        host_start,
        host_end,
        read_only_before,
        read_only_after,
        m172_invalidation,
        modulo_window_invalidation,
        tail_invalidation,
        final_window_gate,
        runtime_quiesce,
    ):
        if value.get("measured_commit") != MEASURED_COMMIT:
            raise RuntimeError("artifact measured commit mismatch")

    accepted = [
        row
        for row in rows
        if row.get("valid") is True and row.get("accepted_for_protocol") is True
    ]
    excluded = [
        row
        for row in rows
        if row.get("valid") is True and row.get("accepted_for_protocol") is False
    ]
    invalid = [row for row in rows if row.get("valid") is not True]
    accepted_by_position = {}
    for row in accepted:
        key = row["position_key"]
        if key in accepted_by_position:
            raise RuntimeError(f"duplicate accepted position: {key}")
        accepted_by_position[key] = row

    expected_positions = {
        f"warmup:N{count}:W{workers}:R0"
        for count in COUNTS
        for workers in WORKERS
    }
    expected_positions.update(
        f"scored:N{count}:W{workers}:R{repetition}"
        for count in COUNTS
        for repetition in range(1, 7)
        for workers in WORKERS
    )
    expected_positions.update(
        f"modulo-warmup:N{count}:W16:R0" for count in MODULO_COUNTS
    )
    expected_positions.update(
        f"modulo-scored:N{count}:W16:R{repetition}"
        for repetition in range(1, 7)
        for count in MODULO_COUNTS
    )
    accepted_positions = set(accepted_by_position)
    if accepted_positions != expected_positions:
        missing_positions = sorted(expected_positions - accepted_positions)
        unexpected_positions = sorted(accepted_positions - expected_positions)
        raise RuntimeError(
            "accepted-position grid mismatch: "
            f"missing={missing_positions}, unexpected={unexpected_positions}"
        )
    if any(row.get("load_gate_valid") is not True for row in accepted):
        raise RuntimeError("accepted row does not pass the registered load gate")

    expected_matrix = 15 + 90
    expected_modulo = 4 + 24
    accepted_matrix = [
        row for row in accepted if row.get("kind") in {"warmup", "scored"}
    ]
    accepted_modulo = [
        row
        for row in accepted
        if row.get("kind") in {"modulo-warmup", "modulo-scored"}
    ]
    accepted_modulo_scored = [
        row for row in accepted if row.get("kind") == "modulo-scored"
    ]
    if (
        len(accepted_matrix) != expected_matrix
        or len(accepted_modulo) != expected_modulo
        or len(accepted_modulo_scored) != 24
        or invalid
    ):
        raise RuntimeError("registered accepted-position accounting is incomplete")
    if any(latest_preload_contenders(row) for row in accepted_modulo):
        raise RuntimeError("an accepted modulo row retains a named preload contender")

    cells = {}
    sampled_by_n_worker = {}
    job_by_n_worker = {}
    sample_quality = []
    for count in COUNTS:
        sampled_by_n_worker[str(count)] = {}
        job_by_n_worker[str(count)] = {}
        for workers in WORKERS:
            scored = sorted(
                (
                    row
                    for row in accepted
                    if row.get("kind") == "scored"
                    and int(row["limit"]) == count
                    and int(row["workers"]) == workers
                ),
                key=lambda row: int(row["repetition"]),
            )
            output_hashes = sorted({row["output_sha256"] for row in scored})
            pixel_hashes = sorted({row["pixel_sha256"] for row in scored})
            sampled_peak = max(
                row["memory"]["peak_process_tree_private_committed_bytes"]
                for row in scored
            )
            job_peak = max(
                row["memory"]["kernel_job_peak_memory"][
                    "peak_job_memory_used_bytes"
                ]
                for row in scored
            )
            for row in scored:
                memory = row["memory"]
                scheduled = memory["sample_count"] + memory["missed_intervals"]
                sample_quality.append(
                    {
                        "position_key": row["position_key"],
                        "coverage": memory["sample_count"] / scheduled,
                        "max_gap_ms": memory["max_gap_ms"],
                    }
                )
            key = f"N{count}-W{workers}"
            cells[key] = {
                "evidence_tag": "VERIFIED",
                "accepted_scored_runs": len(scored),
                "distinct_output_sha256": len(output_hashes),
                "output_sha256": output_hashes,
                "distinct_pixel_sha256": len(pixel_hashes),
                "pixel_sha256": pixel_hashes,
                "maximum_sampled_process_tree_private_committed_bytes": sampled_peak,
                "maximum_sampled_process_tree_private_committed_gib": sampled_peak
                / (1 << 30),
                "maximum_kernel_job_peak_memory_bytes": job_peak,
                "maximum_kernel_job_peak_memory_gib": job_peak / (1 << 30),
                "memory_ceiling_verdict": "PASS" if job_peak <= SIX_GIB else "FAIL",
                "fixed_worker_determinism_verdict": (
                    "PASS"
                    if len(scored) == 6
                    and len(output_hashes) == 1
                    and len(pixel_hashes) == 1
                    else "FAIL"
                ),
            }
            sampled_by_n_worker[str(count)][str(workers)] = sampled_peak
            job_by_n_worker[str(count)][str(workers)] = job_peak

    if any(
        cell["fixed_worker_determinism_verdict"] != "PASS"
        for cell in cells.values()
    ):
        raise RuntimeError("M12-D final matrix is not deterministic")

    cross_worker = {}
    for count in COUNTS:
        scored = [
            row
            for row in accepted
            if row.get("kind") == "scored" and int(row["limit"]) == count
        ]
        output_hashes = sorted({row["output_sha256"] for row in scored})
        pixel_hashes = sorted({row["pixel_sha256"] for row in scored})
        cross_worker[str(count)] = {
            "evidence_tag": "VERIFIED",
            "distinct_output_sha256": len(output_hashes),
            "output_sha256": output_hashes,
            "distinct_pixel_sha256": len(pixel_hashes),
            "pixel_sha256": pixel_hashes,
            "byte_invariance_verdict": (
                "PASS"
                if len(output_hashes) == 1 and len(pixel_hashes) == 1
                else "FAIL"
            ),
        }

    sampled_ratio_by_worker = {
        str(workers): sampled_by_n_worker["299"][str(workers)]
        / sampled_by_n_worker["33"][str(workers)]
        for workers in WORKERS
    }
    job_ratio_by_worker = {
        str(workers): job_by_n_worker["299"][str(workers)]
        / job_by_n_worker["33"][str(workers)]
        for workers in WORKERS
    }
    maximum_sampled_row = max(
        (
            row
            for row in accepted
            if row.get("kind") == "scored"
        ),
        key=lambda row: row["memory"]["peak_process_tree_private_committed_bytes"],
    )
    minimum_coverage = min(row["coverage"] for row in sample_quality)
    maximum_gap = max(row["max_gap_ms"] for row in sample_quality)

    quiesce_start = parse_time(runtime_quiesce["suspended_utc"])
    quiesce_end = parse_time(runtime_quiesce["harness_completed_utc"])
    modulo = {}
    minima = []
    for count in MODULO_COUNTS:
        scored = sorted(
            (
                row
                for row in accepted_modulo_scored
                if int(row["limit"]) == count
            ),
            key=lambda row: int(row["repetition"]),
        )
        if len(scored) != 6:
            raise RuntimeError(f"N={count} does not have six modulo runs")
        minimum = min(scored, key=lambda row: float(row["wall_seconds"]))
        within_quiesce = (
            parse_time(minimum["started_utc"]) >= quiesce_start
            and parse_time(minimum["completed_utc"]) <= quiesce_end
        )
        minima.append(float(minimum["wall_seconds"]) / count)
        modulo[str(count)] = {
            "evidence_tag": "VERIFIED",
            "accepted_scored_runs": len(scored),
            "wall_seconds": [float(row["wall_seconds"]) for row in scored],
            "minimum": {
                "position_key": minimum["position_key"],
                "attempt": minimum["attempt"],
                "wall_seconds": float(minimum["wall_seconds"]),
                "wall_seconds_per_frame": float(minimum["wall_seconds"]) / count,
                "started_utc": minimum["started_utc"],
                "completed_utc": minimum["completed_utc"],
                "within_runtime_quiesce": within_quiesce,
                "external_busy_fraction": minimum["host_load_during_run"][
                    "external_busy_fraction_of_wall_capacity"
                ],
            },
            "distinct_output_sha256": len(
                {row["output_sha256"] for row in scored}
            ),
            "distinct_pixel_sha256": len(
                {row["pixel_sha256"] for row in scored}
            ),
        }
    if not all(row["minimum"]["within_runtime_quiesce"] for row in modulo.values()):
        raise RuntimeError("not every scoring minimum is protected by runtime quiesce")
    modulo_spread = (max(minima) - min(minima)) / min(minima)
    if not math.isclose(
        modulo_spread,
        float(summary["modulo"]["spread"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise RuntimeError("modulo spread does not match mechanical summary")

    before_roots = {row["path"]: row for row in read_only_before["roots"]}
    after_roots = {row["path"]: row for row in read_only_after["roots"]}
    tree_comparison = {
        root_path: {
            "evidence_tag": "VERIFIED",
            "before": before_roots.get(root_path),
            "after": after_roots.get(root_path),
            "unchanged": before_roots.get(root_path) == after_roots.get(root_path),
        }
        for root_path in sorted(set(before_roots) | set(after_roots))
    }
    if not tree_comparison or not all(
        row["unchanged"] for row in tree_comparison.values()
    ):
        raise RuntimeError("protected input tree changed")

    external_rows = [
        row for row in excluded if row.get("external_invalidation") is not None
    ]
    load_only_rows = [
        row for row in excluded if row.get("external_invalidation") is None
    ]
    invalidation_results = [
        validated_invalidation(artifact_value)
        for artifact_value in (
            m172_invalidation,
            modulo_window_invalidation,
            tail_invalidation,
        )
    ]
    accepted_invalidated = sum(result[0] for result in invalidation_results)
    invalidated_ids = set()
    for _, affected_ids in invalidation_results:
        if invalidated_ids & affected_ids:
            raise RuntimeError("record appears in multiple invalidation artifacts")
        invalidated_ids.update(affected_ids)
    external_ids = {row_id(row) for row in external_rows}
    if invalidated_ids != external_ids:
        raise RuntimeError("record invalidation artifacts do not match final records")
    helper_root = root.parent.parent
    helper_paths = {
        name: helper_root / filename
        for name, filename in {
            "tree_snapshot": "m139-tree-snapshot.ps1",
            "overlap_invalidator": "m139-invalidate-overlap.py",
            "modulo_window_invalidator": "m139-invalidate-modulo-window.py",
            "tail_invalidator": "m139-invalidate-final-tail.py",
            "runtime_quiescer": "m139-quiesce-runtime.ps1",
            "finalizer": "m139-finalize.py",
        }.items()
    }
    missing_helpers = [
        str(path) for path in helper_paths.values() if not path.exists()
    ]
    if missing_helpers:
        raise RuntimeError(
            "missing finalization helpers:\n" + "\n".join(missing_helpers)
        )

    mechanical_formal = summary.get("mechanical_formal_m12", summary["formal_m12"])
    mechanical_nonaccepted = summary["host_load"].get(
        "mechanical_nonaccepted_valid_count",
        summary["host_load"]["rejected_run_count"],
    )
    summary["schema"] = 2
    summary.pop("adjudicated_utc", None)
    summary["adjudicated_evidence_cutoff_utc"] = host_end["generated_utc"]
    summary["mechanical_formal_m12"] = mechanical_formal
    summary["host_load"]["mechanical_nonaccepted_valid_count"] = (
        mechanical_nonaccepted
    )
    summary["host_load"]["rejected_run_count"] = len(load_only_rows)
    summary["host_load"]["externally_invalidated_run_count"] = len(external_rows)
    summary["records"]["non_protocol_valid"] = len(excluded)
    summary["records"]["rejected_for_host_load"] = len(load_only_rows)
    summary["records"]["rows_with_external_invalidation_metadata"] = len(
        external_rows
    )
    summary["records"]["accepted_rows_later_invalidated"] = accepted_invalidated
    summary["records"]["sha256"] = sha256(paths["records"])
    summary["m12_s_byte_property"]["m11_joint_requirement"] = (
        "BLOCKED-BY-LICENCE"
    )
    summary["m12_s"] = {
        "byte_property_verdict": "FAIL",
        "m11_precondition": "BLOCKED-BY-LICENCE",
        "formal_verdict": "BLOCKED-BY-LICENCE",
    }
    summary["formal_m12"] = {
        "verdict": "NOT_ASSIGNED",
        "reason": (
            "M12-D and M12-S are separately reported. M12-S has a "
            "BLOCKED-BY-LICENCE M11 precondition; no overall M12 verdict is "
            "manufactured."
        ),
    }
    write_json(paths["summary"], summary)

    closeout = {
        "schema": 2,
        "evidence_tag": "VERIFIED",
        "measured_commit": MEASURED_COMMIT,
        "adjudicated_evidence_cutoff_utc": host_end["generated_utc"],
        "campaign_status": {
            "registered_campaign_complete": True,
            "accepted_matrix_positions": len(accepted_matrix),
            "expected_matrix_positions": expected_matrix,
            "accepted_modulo_positions": len(accepted_modulo),
            "expected_modulo_positions": expected_modulo,
            "invalid_process_outputs": len(invalid),
        },
        "registration": {
            "evidence_tag": "INHERITED",
            "source": "docs/proposals/2026-09-sota-scorecard.md",
            "source_commit": MEASURED_COMMIT,
            "source_lines": "1038-1103",
            "scoreboard_line": "403",
            "joint_constraint_line": "122",
            "sha256": registration["governing_registration"]["sha256"],
            "design": registration["registered_design"],
            "bars": registration["bars"],
            "scored_vs_diagnostic": registration["scored_vs_diagnostic"],
        },
        "verdicts": {
            "frozen_registration_mechanical_result": {
                "evidence_tag": "VERIFIED",
                "verdict": mechanical_formal["verdict"],
                "hard_failures": mechanical_formal.get("hard_failures", []),
                "disposition": (
                    "Preserved as mechanical provenance. The program "
                    "orchestrator subsequently required split M12-D/M12-S "
                    "reporting and directed that no overall M12 verdict be "
                    "assigned while the M11 term is blocked by licensing."
                ),
            },
            "m12_d": {
                "evidence_tag": "VERIFIED",
                "verdict": "PASS",
                "complete_fixed_worker_cells": len(cells),
                "required_complete_fixed_worker_cells": 15,
            },
            "m12_s": {
                "evidence_tag": "VERIFIED",
                "formal_verdict": "BLOCKED-BY-LICENCE",
                "byte_property_verdict": "FAIL",
                "byte_property_by_n": cross_worker,
                "m11_precondition": {
                    "evidence_tag": "INHERITED",
                    "verdict": "BLOCKED-BY-LICENCE",
                    "reason": (
                        "The installed Zerene trial is expired and cannot save "
                        "the required comparator output; no Helicon installation "
                        "was found."
                    ),
                    "sources": [
                        {
                            "path": "docs/research/M132-blocker-d-routes.md",
                            "lines": "160-197",
                            "quotes": [
                                (
                                    "line 71: 0.448: license "
                                    "83ced522295099724b84c81abbb79f3199726fd7 "
                                    "expires on Sat Jun 06 20:13:34 PDT 2026"
                                ),
                                "line 75: 0.450: License category = TRIAL",
                                (
                                    "They found zero Helicon-named installation, "
                                    "state, log, licence, key, or registry matches."
                                ),
                            ],
                        },
                        {
                            "path": "docs/OWNER-ACTIONS.md",
                            "lines": "1560-1562",
                            "quote": (
                                "Zerene is already installed here at "
                                "1.04T2026-05-04-0750, but its trial is consumed "
                                "and expired (License category = TRIAL, expired "
                                "2026-06-06), so it currently cannot save output "
                                "at all."
                            ),
                        },
                    ],
                },
            },
            "overall_m12": {
                "evidence_tag": "VERIFIED",
                "verdict": "NOT_ASSIGNED",
                "reporting_basis": "ORCHESTRATOR_DIRECTIVE",
                "reason": (
                    "The registered sub-verdicts are not conflated, and the M11 "
                    "precondition for M12-S is blocked by comparator licensing."
                ),
            },
        },
        "cells": cells,
        "absolute_bars": {
            "memory_ceiling": {
                "evidence_tag": "VERIFIED",
                "bar_bytes": SIX_GIB,
                "bar_gib": 6.0,
                "verdict": "FAIL",
                "maximum_sampled_process_tree_private_committed_bytes": (
                    maximum_sampled_row["memory"][
                        "peak_process_tree_private_committed_bytes"
                    ]
                ),
                "maximum_sampled_process_tree_private_committed_gib": (
                    maximum_sampled_row["memory"][
                        "peak_process_tree_private_committed_bytes"
                    ]
                    / (1 << 30)
                ),
                "maximum_position_key": maximum_sampled_row["position_key"],
            },
            "memory_scaling": {
                "evidence_tag": "VERIFIED",
                "bar": 1.10,
                "sampled_peak_n299_over_n33_by_worker": sampled_ratio_by_worker,
                "sampled_maximum": max(sampled_ratio_by_worker.values()),
                "kernel_job_peak_n299_over_n33_by_worker": job_ratio_by_worker,
                "kernel_job_maximum": max(job_ratio_by_worker.values()),
                "numeric_bar_met": False,
                "formal_verdict": "UNMEASURED_SAMPLING_COVERAGE",
                "reason": (
                    "The observed maximum misses the bar, and independent kernel "
                    "Job Object peaks agree, but the frozen adjudication requires "
                    "every scored run to meet the 90% sampling-coverage rule "
                    "before assigning the ratio a formal PASS or FAIL."
                ),
                "sampling_quality": {
                    "minimum_coverage": minimum_coverage,
                    "maximum_gap_ms": maximum_gap,
                    "coverage_requirement": 0.90,
                    "maximum_gap_requirement_ms": 100.0,
                },
            },
            "n_mod_4": {
                "evidence_tag": "VERIFIED",
                "bar": 0.02,
                "spread": modulo_spread,
                "verdict": "FAIL",
                "by_n": modulo,
                "all_scoring_minima_within_runtime_quiesce": True,
            },
        },
        "commissioning": {
            "memory_probe": {
                "evidence_tag": "VERIFIED",
                "status": memory_commission["status"],
                "null": {
                    "requested_allocation_bytes": memory_commission["null"][
                        "requested_allocation_bytes"
                    ],
                    "sampled_peak_private_committed_bytes": memory_commission[
                        "null"
                    ]["memory"]["peak_process_tree_private_committed_bytes"],
                    "kernel_job_peak_bytes": memory_commission["null"]["memory"][
                        "kernel_job_peak_memory"
                    ]["peak_job_memory_used_bytes"],
                    "process_count": memory_commission["null"]["memory"][
                        "peak_process_count"
                    ],
                },
                "positive_plant": {
                    "requested_allocation_bytes": memory_commission["plant"][
                        "requested_allocation_bytes"
                    ],
                    "sampled_peak_private_committed_bytes": memory_commission[
                        "plant"
                    ]["memory"]["peak_process_tree_private_committed_bytes"],
                    "kernel_job_peak_bytes": memory_commission["plant"]["memory"][
                        "kernel_job_peak_memory"
                    ]["peak_job_memory_used_bytes"],
                    "process_count": memory_commission["plant"]["memory"][
                        "peak_process_count"
                    ],
                },
                "process_tree_membership_source": (
                    "Windows Job Object"
                ),
                "sample_interval_ms": 10.0,
            },
            "determinism_probe": {
                "evidence_tag": "VERIFIED",
                "status": determinism_commission["status"],
                "baseline_output_sha256": determinism_commission["hash_gate"][
                    "baseline_sha256"
                ],
                "baseline_pixel_sha256": determinism_commission["baseline"][
                    "pixel_sha256"
                ],
                "algorithm_plant_output_sha256": determinism_commission[
                    "hash_gate"
                ]["planted_sha256"],
                "algorithm_plant_pixel_sha256": determinism_commission[
                    "planted"
                ]["pixel_sha256"],
                "restored_output_sha256": determinism_commission["hash_gate"][
                    "restored_sha256"
                ],
                "restored_pixel_sha256": determinism_commission["restored"][
                    "pixel_sha256"
                ],
                "lsb_plant": {
                    "coordinate": determinism_commission["hash_gate"][
                        "lsb_coordinate"
                    ],
                    "before": determinism_commission["hash_gate"]["lsb_before"],
                    "after": determinism_commission["hash_gate"]["lsb_after"],
                    "output_sha256": determinism_commission["hash_gate"][
                        "lsb_sha256"
                    ],
                },
                "highest_precision_deliverable": (
                    "uncompressed 16-bit RGB TIFF plus canonical decoded uint16 "
                    "pixel payload"
                ),
            },
            "smoke": {
                "evidence_tag": "VERIFIED",
                "status": smoke["status"],
                "verdict": smoke["verdict"],
            },
        },
        "host_conditions": {
            "evidence_tag": "VERIFIED",
            "start": {
                "artifact": str(paths["host_start"].resolve()),
                "generated_utc": host_start["generated_utc"],
                "whole_host_busy_fraction_of_wall_capacity": host_start[
                    "gate"
                ]["attempts"][-1][
                    "whole_host_busy_fraction_of_wall_capacity"
                ],
                "rejected_preload_samples": host_start["gate"][
                    "rejected_sample_count"
                ],
            },
            "end": {
                "artifact": str(paths["host_end"].resolve()),
                "generated_utc": host_end["generated_utc"],
                "whole_host_busy_fraction_of_wall_capacity": host_end[
                    "sample"
                ]["whole_host_busy_fraction_of_wall_capacity"],
                "top_process_cpu": host_end["sample"]["top_process_cpu"],
            },
            "registered_gates": manifest["host_load_gate"],
            "self_imposed_five_percent_precondition": {
                "disposition": "DROPPED",
                "reason": (
                    "It added no CPU-validity protection beyond the registered "
                    "per-run <=15% preload and <=10% external-busy gates and was "
                    "unreachable while agent runtimes were active."
                ),
                "replacement_non_cpu_protection": (
                    "No named Cargo/Rust/Strehl/ExifTool contender before the "
                    "final tail, plus suspension of the shared agent runtime "
                    "while the scoring minima were produced."
                ),
            },
            "registered_120_minute_window": {
                "reserved": True,
                "uninterrupted": False,
                "reason": (
                    "Other lanes repeatedly launched compiler, byte-freeze, and "
                    "Strehl workloads. Every affected row was retained and "
                    "invalidated rather than adjusted."
                ),
            },
            "final_window_gate": final_window_gate,
            "runtime_quiesce": runtime_quiesce,
            "maximum_accepted_external_busy_fraction": summary["host_load"][
                "maximum_accepted_external_busy_fraction"
            ],
        },
        "record_accounting": {
            "evidence_tag": "VERIFIED",
            "total": len(rows),
            "accepted": len(accepted),
            "non_protocol_valid": len(excluded),
            "load_rejected_without_external_invalidation": len(load_only_rows),
            "rows_with_external_invalidation_metadata": len(external_rows),
            "accepted_rows_later_invalidated": accepted_invalidated,
            "invalid_process_outputs": len(invalid),
            "accepted_positions_are_unique": True,
        },
        "read_only_input_trees": tree_comparison,
        "provenance": {
            "manifest": artifact(paths["manifest"]),
            "registration": artifact(paths["registration"]),
            "input_manifest": artifact(paths["input_manifest"]),
            "records": artifact(paths["records"]),
            "summary": artifact(paths["summary"]),
            "harness": {
                "path": manifest["harness"]["path"],
                "sha256": manifest["harness"]["sha256"],
            },
            "binary": manifest["binary"],
            "helpers": {
                name: artifact(path) for name, path in helper_paths.items()
            },
        },
        "could_not_determine": [
            {
                "item": "formal peak_N299/peak_N33 verdict",
                "reason": (
                    "Minimum sampling coverage was below the frozen 90% "
                    "adjudication threshold. The observed sampled and kernel Job "
                    "Object ratios are still reported."
                ),
            },
            {
                "item": "M11 comparator throughput",
                "reason": (
                    "The installed Zerene trial is expired and cannot save the "
                    "required output; no Helicon installation is available."
                ),
            },
            {
                "item": "true unsampled instantaneous memory peak",
                "reason": (
                    "A sampled monitor can miss a higher instantaneous peak. It "
                    "cannot manufacture the observed above-6-GiB failure."
                ),
            },
            {
                "item": "complete process-tree I/O byte totals",
                "reason": (
                    "The instrument records temp bytes, page faults, CPU, hashes, "
                    "and memory, but not complete process-tree read/write totals."
                ),
            },
            {
                "item": "calibrated residual thermal, turbo, and cache state",
                "reason": (
                    "The registered CPU gates and named-contender exclusion do "
                    "not instrument those state variables directly. Alternating "
                    "sweeps and the guarded scoring-minimum interval mitigate "
                    "them without converting them into measured quantities."
                ),
            },
            {
                "item": "exact lane attribution for every host-load rejection",
                "reason": (
                    "Named contamination incidents were pinned where observed; "
                    "not every historical CPU interval can be assigned to one lane."
                ),
            },
        ],
    }
    write_json(paths["closeout"], closeout)

    audit_inputs = {
        path.name: artifact(path)
        for path in sorted(root.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file()
        and path != paths["audit"]
        and path.name not in LOCAL_ONLY_ROOT_LOGS
    }
    local_only_logs = [
        path.name
        for path in sorted(root.iterdir(), key=lambda candidate: candidate.name)
        if path.is_file() and path.name in LOCAL_ONLY_ROOT_LOGS
    ]
    audit = {
        "schema": 2,
        "evidence_tag": "VERIFIED",
        "measured_commit": MEASURED_COMMIT,
        "adjudicated_evidence_cutoff_utc": host_end["generated_utc"],
        "integrity": {
            "pass": True,
            "registered_campaign_complete": True,
            "record_measured_commits": sorted(
                {row.get("measured_commit") for row in rows}
            ),
            "accepted_positions_are_unique": True,
            "m12_d_complete": True,
            "m12_s_byte_property_complete": True,
            "modulo_complete": True,
            "modulo_minima_runtime_quiesced": True,
            "memory_probe_commissioned": (
                memory_commission["status"] == "COMMISSIONED"
            ),
            "determinism_probe_commissioned": (
                determinism_commission["status"] == "COMMISSIONED"
            ),
            "smoke_passed": smoke["status"] == "PASS",
            "protected_trees_unchanged": True,
        },
        "verdicts": closeout["verdicts"],
        "absolute_bars": closeout["absolute_bars"],
        "record_accounting": closeout["record_accounting"],
        "artifacts": audit_inputs,
        "local_only_nonpersistent_logs": local_only_logs,
        "could_not_determine": closeout["could_not_determine"],
    }
    write_json(paths["audit"], audit)
    print(
        json.dumps(
            {
                "closeout": artifact(paths["closeout"]),
                "audit": artifact(paths["audit"]),
                "m12_d": closeout["verdicts"]["m12_d"]["verdict"],
                "m12_s_bytes": closeout["verdicts"]["m12_s"][
                    "byte_property_verdict"
                ],
                "m12_s_precondition": closeout["verdicts"]["m12_s"][
                    "m11_precondition"
                ]["verdict"],
                "memory": closeout["absolute_bars"]["memory_ceiling"]["verdict"],
                "memory_ratio_formal": closeout["absolute_bars"][
                    "memory_scaling"
                ]["formal_verdict"],
                "modulo": closeout["absolute_bars"]["n_mod_4"]["verdict"],
                "overall_m12": closeout["verdicts"]["overall_m12"]["verdict"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
