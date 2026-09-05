"""Verify M182 memory evidence, attribution, controls, and canonical report rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = HERE / "results.json"
REPORT = ROOT / "docs" / "research" / "M182-memory-budget.md"
COMMISSION = HERE / "probe-commission.json"
M139_CLOSEOUT = (
    ROOT
    / "experiments"
    / "m12-scorecard"
    / "out"
    / "campaign-8009447e-m139"
    / "closeout.json"
)
M139_RECORDS = M139_CLOSEOUT.with_name("records.jsonl")
M172_ARTIFACTS = {
    "experiments/M172-worker-memory/measure_memory.py": (
        ROOT / "experiments" / "M172-worker-memory" / "measure_memory.py"
    ),
    "experiments/M172-worker-memory/results/campaign.json": (
        ROOT / "experiments" / "M172-worker-memory" / "results" / "campaign.json"
    ),
    "experiments/M172-worker-memory/results/negative-control-summary.json": (
        ROOT
        / "experiments"
        / "M172-worker-memory"
        / "results"
        / "negative-control-summary.json"
    ),
    "docs/research/M172-worker-invariance-control.md": (
        ROOT / "docs" / "research" / "M172-worker-invariance-control.md"
    ),
    "docs/research/M172-m12s-closure.md": (
        ROOT / "docs" / "research" / "M172-m12s-closure.md"
    ),
    "docs/research/M172-memory-planner-handoff.md": (
        ROOT / "docs" / "research" / "M172-memory-planner-handoff.md"
    ),
}
M139_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
BOUNDED_COMMIT = "a97275817c58e164f75c7cd3d80ca99444a2a145"
PLANNER_COMMIT = "fb42b9a1c6481dba3d7ef54c8505ec5ca69b649d"
PLANNER_PARENT = "30575dca5812d2c06efec2b0eca116f3aa05f959"
PLANNER_LIVE_BYTES = 3_045_147_112
BAR_BYTES = 6 << 30


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def git(*args: str, text: bool = True) -> str | bytes:
    result = subprocess.check_output(["git", "-C", str(ROOT), *args])
    return result.decode("utf-8").strip() if text else result


def git_blob_sha256(commit: str, relative: str) -> str:
    return sha256_bytes(git("show", f"{commit}:{relative}", text=False))


def expected_report_lines(result: dict[str, Any]) -> dict[str, str]:
    lines: dict[str, str] = {
        "bar-ruling": (
            "**CANONICAL BAR RULING:** The documents do not disagree: this is one "
            "6-GiB process-tree budget, including the 16-worker cell, not 6 GiB per "
            "process or per worker."
        ),
        "m139-peak": (
            "**CANONICAL M139 PEAK:** At N299/W16, sampled private commit reached "
            f"`{result['m139']['maximum_sampled_private_bytes']:,} B = "
            f"{result['m139']['maximum_sampled_private_bytes'] / 2**30:.9f} GiB` "
            f"(`{result['m139']['maximum_position_key']}`); the cell's independent "
            f"kernel Job peak was `{result['m139']['maximum_job_peak_bytes']:,} B = "
            f"{result['m139']['maximum_job_peak_bytes'] / 2**30:.9f} GiB`, only "
            f"`{result['m139']['maximum_job_peak_bytes'] - result['m139']['maximum_sampled_private_bytes']:,} B` higher."
        ),
    }

    for row in result["reproduction"]["rows"]:
        lines[f"reproduction-w{row['workers']}"] = (
            f"| {row['workers']} | `{row['fresh_job_peak_bytes']:,} B` | "
            f"`{row['canonical_n33_max_job_peak_bytes']:,} B` | "
            f"`{100 * row['relative_delta']:+.6f}%` |"
        )

    fit = result["m139"]["active_chunk_fit"]
    lines["scaling-law"] = (
        "**CANONICAL SCALING LAW:** "
        f"`peak = {fit['intercept_bytes']:,.0f} B + "
        f"{fit['slope_bytes_per_active_chunk']:,.3f} B * active_chunks`, "
        f"with `R²={fit['r_squared']:.9f}` across all 15 M139 cells."
    )

    descriptions = {
        "band_merge": "`BandMerge`: 9 pyramids plus 8 level-0 input-hull planes",
        "frame_workspace": (
            "`FrameWorkspace`: two operator workspaces, seven pyramids, four "
            "level-0 fields"
        ),
        "fullres_gather_transient": (
            "full-resolution gather: mosaic plus R/G/B f32 planes"
        ),
    }
    for index, row in enumerate(
        result["allocation_accounting"]["n299_w16_top_three"], start=1
    ):
        lines[f"consumer-{index}"] = (
            f"| {index} | {descriptions[row['name']]} | "
            f"`{row['bytes_per_active_chunk']:,} B "
            f"({row['bytes_per_active_chunk'] / 2**20:.3f} MiB)` | "
            f"`{row['bytes_at_16_active_chunks']:,} B "
            f"({row['bytes_at_16_active_chunks'] / 2**30:.3f} GiB)` |"
        )

    accounting = result["allocation_accounting"]
    slope = fit["slope_bytes_per_active_chunk"]
    lines["attribution"] = (
        "**CANONICAL ATTRIBUTION CHECK:** Source accounting totals "
        f"`{accounting['source_accounted_bytes_per_active_chunk']:,} B = "
        f"{accounting['source_accounted_bytes_per_active_chunk'] / 2**30:.9f} GiB` "
        f"per active chunk, `{100 * accounting['fraction_of_fitted_slope_accounted']:.6f}%` "
        f"of the fitted `{slope / 2**30:.9f} GiB` slope; the unexplained remainder "
        f"is `{accounting['fit_minus_accounting_bytes_per_active_chunk']:,.0f} B` per chunk."
    )

    steps = result["plan"]["steps"]
    lines["plan-1"] = (
        "| 1 | `merge_cmd.rs::run_pyramid`, `BandWorker::reset_chunk` | run "
        "canonical chunks serially through one reusable frame worker; keep a "
        "16-thread pool for spatial work | "
        f"`{steps[0]['estimated_saving_bytes']:,} B "
        f"({steps[0]['estimated_saving_bytes'] / 2**30:.3f} GiB)` from 15 "
        "duplicate non-accumulator bundles |"
    )
    lines["plan-2"] = (
        "| 2 | `pyramid.rs::BandMerge::reset_for_reuse` | retain the result plus "
        "one resettable scratch accumulator instead of 16 partials, preserving "
        "chunk boundaries and absorb order | "
        f"`{steps[1]['estimated_saving_bytes']:,} B "
        f"({steps[1]['estimated_saving_bytes'] / 2**30:.3f} GiB)` from 14 accumulators |"
    )
    lines["plan-3"] = (
        "| 3 | pyramid row operators plus `extract_planes`/`load_frame` | "
        "parallelise disjoint rows and planes inside that one worker | no direct "
        "byte saving; this preserves 16-thread execution without restoring the allocations |"
    )

    bounded = result["bounded_implementation"]
    for frames in (33, 299):
        peak = bounded[f"n{frames}_w16_job_peak_bytes"]
        lines[f"bounded-n{frames}"] = (
            f"| N{frames}/W16 | `{peak:,} B = {peak / 2**30:.9f} GiB` | pass |"
        )
    lines["bounded-verdict"] = (
        "**CANONICAL BOUNDED VERDICT:** The current memory implementation is "
        f"`{bounded['reduction_factor']:.6f}x` below M139's N299/W16 peak, leaves "
        f"`{bounded['headroom_bytes']:,} B = {bounded['headroom_bytes'] / 2**30:.9f} GiB` "
        "headroom, and measures "
        f"`peak_N299/peak_N33 = {bounded['n299_over_n33_ratio']:.9f}`."
    )
    planner = result["planner_hypothesis"]
    w4 = planner["w4_model_cell"]
    w2 = planner["w2_third_point"]
    prediction = planner["bounded_prediction"]
    lines["m172-boundary"] = (
        "**CANONICAL M172 BOUNDARY:** the routed M172 planner handoff supplies the "
        f"same `{planner['source_accounted_bytes_per_active_chunk']:,} B/chunk` "
        "allocation ledger and reusable-worker/two-accumulator design; M182 "
        "independently derived that ledger from frozen `8009447e` source and "
        "tested the hypothesis against registered and fresh process-tree "
        "measurements; no unrerun M172 M12-S finding enters this memory verdict."
    )
    lines["planner-estimand"] = (
        "**CANONICAL PLANNER ESTIMAND:** at N33/W4 the payload model predicts "
        f"`{w4['predicted_payload_bytes']:,} B`; registered peak Job memory is "
        f"`{w4['observed_job_peak_bytes']:,} B` and sampled process-tree private "
        f"commit is `{w4['observed_private_peak_bytes']:,} B`, differing by only "
        f"`{w4['job_minus_private_bytes']:,} B`; Job accounting reports one "
        "process, so the model's single-process payload and the governed "
        "process-tree estimand coincide in this cell."
    )
    lines["third-worker"] = (
        "**CANONICAL THIRD-WORKER TEST:** W2 predicts "
        f"`{w2['predicted_payload_bytes']:,} B`; M139 registered "
        f"`{w2['registered_job_peak_bytes']:,} B` Job and "
        f"`{w2['registered_private_peak_bytes']:,} B` private commit, a Job "
        f"residual of `{w2['registered_job_residual_bytes']:,} B = "
        f"{100 * w2['registered_job_residual_fraction']:.6f}%`; M182's fresh W2 "
        f"Job peak is `{w2['fresh_job_peak_bytes']:,} B`, residual "
        f"`{w2['fresh_job_residual_bytes']:,} B = "
        f"{100 * w2['fresh_job_residual_fraction']:.6f}%`; the third point does "
        "not falsify the replicated-whole-frame-state mechanism."
    )
    lines["tiling-ruling"] = (
        "**CANONICAL TILING RULING:** tiling is unnecessary to reach the 6-GiB "
        "memory bar: bounded canonical recycling is independently measured at "
        f"`{prediction['observed_n299_w16_job_peak_bytes']:,} B`, leaving "
        f"`{BAR_BYTES - prediction['observed_n299_w16_job_peak_bytes']:,} B` "
        "headroom; this is still diagnostic evidence, not a formal M12 pass."
    )
    n7 = result["n7"]
    lines["n7-ruling"] = (
        "**CANONICAL N7 RULING:** the registered M139 process-tree gate is already "
        f"RED on unrepaired `8009447e` at "
        f"`{n7['unrepaired_registered_job_peak_bytes']:,} B > {BAR_BYTES:,} B`, "
        "and M182's commissioned probe uses the same harness hash and independently "
        "reproduces RED; `a9727581` remains diagnostic, and any changed future "
        "certifying gate must first be shown RED on the unrepaired binary."
    )

    probe = result["probe_commission"]["deltas"]
    raw_probe = read_json(COMMISSION)
    peaks = {
        name: arm["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]
        for name, arm in raw_probe["arms"].items()
    }
    lines["probe-commission"] = (
        "**CANONICAL PROBE COMMISSION:** "
        f"baseline `{peaks['baseline']:,} B`; planted allocation "
        f"`{peaks['allocation_plant']:,} B` "
        f"(`+{probe['allocation_plant_minus_baseline_bytes']:,} B`); planted saving "
        f"`{peaks['saving_plant']:,} B` "
        f"(`-{probe['baseline_minus_saving_plant_bytes']:,} B`); inert label-only arm "
        f"`{peaks['inert']:,} B` "
        f"(`|delta|={probe['absolute_inert_minus_baseline_bytes']:,} B`); all five gates passed."
    )
    lines["briefing-correction"] = (
        "**CANONICAL BRIEFING CORRECTION:** Replace “N-mod-4 per-frame spread "
        "passes at `0.07618677189815302%` against `<=2%`” with “the fraction is "
        "`0.07618677189815302`, i.e. `7.618677189815302%`, so the numeric bar "
        "fails; M139 formally records `UNMEASURED_HOST_QUARANTINE`.”"
    )
    lines["check-commission"] = (
        "**CANONICAL CHECK COMMISSION:** `49/49` baseline checks passed; `49/49` "
        "uniquely anchored planted defects were caught; `0` were missed; `2/2` "
        "inert arms survived; both allocation-up and saving-down positive controls "
        "remained discriminating."
    )
    return lines


def semantic_checks(
    result: dict[str, Any],
    *,
    record_overrides: dict[str, dict[str, Any]] | None = None,
    own_text_override: str | None = None,
) -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    def add(check_id: str, condition: bool, message: str) -> None:
        checks.append((check_id, condition, message))

    bar = result["bar"]
    add("S01-schema", result["schema"] == "m182-memory-budget-v1", "wrong schema")
    add(
        "S02-bar-definition",
        bar["bytes"] == BAR_BYTES
        and not bar["documents_disagree"]
        and bar["intended_at_16_workers"],
        "bar is not one six-GiB budget including W16",
    )
    add(
        "S03-warm-lifecycle",
        bar["warm_semantics"]["accepted_warmup_invocations"] == 15
        and bar["warm_semantics"]["accepted_scored_invocations"] == 90
        and bar["warm_semantics"]["warmup_and_scored_are_separate_processes"]
        and "first-frame allocations remain in scope"
        in bar["warm_semantics"]["interpretation"],
        "warm semantics or process counts drifted",
    )
    add(
        "S04-harness-lifecycle-anchors",
        bar["harness_source_lines"] == {
            "spawn": 934,
            "suspended": 941,
            "first_sample": 944,
        },
        "monitor no longer starts at suspended process creation",
    )

    closeout = read_json(M139_CLOSEOUT)
    add(
        "S05-m139-peak",
        result["m139"]["maximum_job_peak_bytes"]
        == closeout["cells"]["N299-W16"]["maximum_kernel_job_peak_memory_bytes"]
        and result["m139"]["maximum_sampled_private_bytes"]
        == closeout["absolute_bars"]["memory_ceiling"][
            "maximum_sampled_process_tree_private_committed_bytes"
        ]
        and result["m139"]["maximum_position_key"]
        == closeout["absolute_bars"]["memory_ceiling"]["maximum_position_key"],
        "M139 maximum was not reproduced from closeout",
    )
    add(
        "S06-independent-counters",
        0
        <= result["m139"]["maximum_job_peak_bytes"]
        - result["m139"]["maximum_sampled_private_bytes"]
        < 1 << 20,
        "sampled and kernel peaks disagree by at least one MiB",
    )
    add(
        "S07-active-chunk-model",
        all(
            row["active_chunks"]
            == math.ceil(row["frames"] / math.ceil(row["frames"] / row["workers"]))
            for row in result["m139"]["matrix"]
        )
        and len(result["m139"]["matrix"]) == 15,
        "active chunk count is wrong",
    )
    fit = result["m139"]["active_chunk_fit"]
    add(
        "S08-scaling-fit",
        fit["r_squared"] > 0.9999
        and 2.20 * 2**30
        < fit["slope_bytes_per_active_chunk"]
        < 2.25 * 2**30,
        "matrix no longer has the claimed whole-worker slope",
    )
    reproduction = result["reproduction"]
    add(
        "S09-fresh-reproduction",
        reproduction["worker_fit"]["r_squared"] > 0.99999
        and all(row["valid"] and abs(row["relative_delta"]) < 0.001 for row in reproduction["rows"])
        and {row["workers"] for row in reproduction["rows"]} == {1, 2, 4},
        "fresh reduced-scale runs do not reproduce M139",
    )
    geometry = result["allocation_accounting"]["geometry"]
    add(
        "S10-geometry",
        geometry["plane_width"] == 3516
        and geometry["plane_height"] == 2344
        and geometry["plane_pixels"] == 8_241_504
        and geometry["pyramid_pixels"] == 10_988_941,
        "allocation geometry changed",
    )
    consumers = result["allocation_accounting"]["consumers_bytes_per_active_chunk"]
    add(
        "S11-consumer-arithmetic",
        consumers
        == {
            "band_merge": 659_330_004,
            "frame_workspace": 571_460_668,
            "fullres_gather_transient": 527_456_256,
            "gate_floor_probe": 208_799_908,
            "planes_luma_variance": 197_796_096,
            "warp_scratch": 74_173_536,
            "two_decoded_frames": 146_800_640,
        },
        "source allocation arithmetic changed",
    )
    add(
        "S12-top-three-order",
        [row["name"] for row in result["allocation_accounting"]["top_three"]]
        == ["band_merge", "frame_workspace", "fullres_gather_transient"],
        "top-three ordering is wrong",
    )
    accounted = result["allocation_accounting"]
    add(
        "S13-attribution-closure",
        accounted["source_accounted_bytes_per_active_chunk"] == sum(consumers.values())
        and accounted["fraction_of_fitted_slope_accounted"] > 0.998
        and abs(accounted["fit_minus_accounting_bytes_per_active_chunk"]) < 4 << 20,
        "source accounting does not close against empirical slope",
    )

    source_ok = True
    for path, recorded in result["provenance"]["measured_source"].items():
        data = git("show", f"{M139_COMMIT}:{path}", text=False)
        assert isinstance(data, bytes)
        source_ok &= sha256_bytes(data) == recorded["sha256"]
        text = data.decode("utf-8").splitlines()
        source_ok &= all(text.count(anchor) == 1 for anchor in recorded["anchors"])
    add(
        "S14-measured-source-provenance",
        source_ok and len(result["provenance"]["measured_source"]) == 5,
        "measured source hashes or unique anchors drifted",
    )
    m139_harness_hashes = {
        row["harness_sha256"]
        for row in (
            json.loads(line)
            for line in M139_RECORDS.read_text(encoding="utf-8").splitlines()
            if line
        )
        if row["accepted_for_protocol"] and row["kind"] == "scored"
    }
    add(
        "S15-input-evidence-provenance",
        result["provenance"]["closeout_sha256"] == sha256(M139_CLOSEOUT)
        and result["provenance"]["records_sha256"] == sha256(M139_RECORDS)
        and result["provenance"]["governing_text_commit"] == PLANNER_COMMIT
        and m139_harness_hashes == {result["provenance"]["harness_sha256"]}
        and result["provenance"]["proposal_sha256"]
        == git_blob_sha256(
            PLANNER_COMMIT, "docs/proposals/2026-08-sota-path.md"
        )
        and result["provenance"]["scorecard_sha256"]
        == git_blob_sha256(
            PLANNER_COMMIT, "docs/proposals/2026-09-sota-scorecard.md"
        ),
        "campaign, harness, or governing documents changed",
    )

    bounded = result["bounded_implementation"]
    current_source_clean = (
        subprocess.run(
            [
                "git",
                "-C",
                str(ROOT),
                "diff",
                "--quiet",
                "--",
                "crates/strehl-cli/src/merge_cmd.rs",
                "crates/strehl-core/src/pyramid.rs",
            ],
            check=False,
        ).returncode
        == 0
    )
    add(
        "S16-current-memory-revision",
        bounded["commit"] == BOUNDED_COMMIT
        and set(bounded["current_memory_files_last_commit"].values())
        == {BOUNDED_COMMIT}
        and current_source_clean,
        "current memory-owning source is not clean at a9727581",
    )
    add(
        "S17-bounded-memory-result",
        bounded["n33_valid"]
        and bounded["n299_valid"]
        and bounded["n299_w16_job_peak_bytes"] <= BAR_BYTES
        and bounded["n299_over_n33_ratio"] <= 1.10,
        "bounded implementation misses memory or ratio bar",
    )
    add(
        "S18-saving-arithmetic",
        bounded["saving_from_m139_peak_bytes"]
        == result["m139"]["maximum_job_peak_bytes"]
        - bounded["n299_w16_job_peak_bytes"]
        and bounded["headroom_bytes"] == BAR_BYTES - bounded["n299_w16_job_peak_bytes"]
        and abs(
            bounded["reduction_factor"]
            - result["m139"]["maximum_job_peak_bytes"]
            / bounded["n299_w16_job_peak_bytes"]
        )
        < 1e-12,
        "bounded saving arithmetic is inconsistent",
    )
    plan = result["plan"]
    add(
        "S19-plan-reaches-bar",
        plan["bounded_change_reachable"]
        and not plan["architectural_tiling_required"]
        and plan["already_landed_concurrently_at"] == BOUNDED_COMMIT
        and abs(
            sum(step["estimated_saving_bytes"] for step in plan["steps"])
            - bounded["saving_from_m139_peak_bytes"]
        )
        < 256 * (1 << 20),
        "plan is not concrete or does not price the observed saving",
    )
    probe = result["probe_commission"]
    add(
        "S20-probe-directions",
        probe["status"] == "COMMISSIONED"
        and all(probe["checks"].values())
        and probe["deltas"]["allocation_plant_minus_baseline_bytes"] >= 192 * (1 << 20)
        and probe["deltas"]["baseline_minus_saving_plant_bytes"] >= 128 * (1 << 20)
        and probe["deltas"]["absolute_inert_minus_baseline_bytes"] <= 16 * (1 << 20),
        "memory meter did not respond in both directions or inert arm moved",
    )
    records_ok = True
    for name in (
        "pre-n33-w1",
        "pre-n33-w2",
        "pre-n33-w4",
        "post-n33-w16",
        "post-n299-w16",
    ):
        record = (
            record_overrides[name]
            if record_overrides is not None and name in record_overrides
            else read_json(HERE / f"{name}.json")
        )
        records_ok &= (
            record["valid"]
            and record["returncode"] == 0
            and record["probe"]["output_removed_after_hash"]
            and not (HERE / "runs" / f"{name}.tiff").exists()
            and record["output_sha256"] is not None
            and record["pixel_sha256"] is not None
        )
    add(
        "S21-product-run-witnesses",
        records_ok,
        "a product reproduction is invalid or lacks a removed hashed TIFF witness",
    )
    own_text = (
        own_text_override
        if own_text_override is not None
        else "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                REPORT,
                HERE / "probe.py",
                HERE / "analyze.py",
                HERE / "verify.py",
            ]
        )
    )
    prohibited_name = "7-" + "aperture" + "-pairs"
    add(
        "S22-holdout-exclusion",
        prohibited_name not in own_text,
        "owned artifacts name the prohibited holdout",
    )
    boundary = result["m172_evidence_boundary"]
    n7 = result["n7"]
    m172_artifacts_ok = set(boundary["artifacts"]) == set(M172_ARTIFACTS) and all(
        boundary["artifacts"][relative]["sha256"]
        == git_blob_sha256(
            boundary["artifacts"][relative]["last_commit"], relative
        )
        for relative in M172_ARTIFACTS
    )
    fresh_w4 = next(
        row["fresh_job_peak_bytes"]
        for row in result["reproduction"]["rows"]
        if row["workers"] == 4
    )
    add(
        "S23-m172-boundary-and-n7",
        boundary["authored_bounded_memory_commit"] == BOUNDED_COMMIT
        and boundary["m172_answered_step4"]
        and boundary["m172_answered_step3"]
        and boundary["m172_throughput_campaign_timed_runs"] == 0
        and not boundary["unrerun_m172_claims_used_in_memory_verdict"]
        and not boundary["m12_s_acted_on"]
        and not boundary["m179_outputs_read_or_acted_on"]
        and boundary["closure_doc_is_downstream_of_m182"]
        and boundary["planner_preservation_commit"] == PLANNER_COMMIT
        and boundary["planner_preservation_parent"] == PLANNER_PARENT
        and boundary["artifacts"][
            "docs/research/M172-memory-planner-handoff.md"
        ]["last_commit"]
        == PLANNER_COMMIT
        and m172_artifacts_ok
        and n7["unrepaired_certifying_commit"] == M139_COMMIT
        and n7["unrepaired_registered_job_peak_bytes"]
        == result["m139"]["maximum_job_peak_bytes"]
        and n7["unrepaired_registered_test_failed"]
        and n7["fresh_unrepaired_w4_job_peak_bytes"] == fresh_w4
        and n7["fresh_unrepaired_w4_failed"]
        and not n7["repaired_result_cashed_as_formal_pass"]
        and n7["certifying_rerun_owner"] == "M179-m12-rerun"
        and n7["same_registered_gate_observed_red"]
        and n7["registered_gate_harness_sha256"]
        == result["provenance"]["harness_sha256"]
        and n7["owned_probe_harness_sha256"]
        == result["provenance"]["harness_sha256"]
        and n7["changed_future_gate_requires_new_unrepaired_red"]
        and n7["rule_document_commit"] == PLANNER_COMMIT
        and n7["rule_document_sha256"]
        == git_blob_sha256(
            PLANNER_COMMIT, "docs/research/ORCH-clamp-default-decision.md"
        ),
        "M172 provenance boundary or N7 fail-before-pass record is inconsistent",
    )
    planner = result["planner_hypothesis"]
    w4 = planner["w4_model_cell"]
    w2 = planner["w2_third_point"]
    matrix = {
        (row["frames"], row["workers"]): row for row in result["m139"]["matrix"]
    }
    fresh_w2 = next(
        row["fresh_job_peak_bytes"]
        for row in result["reproduction"]["rows"]
        if row["workers"] == 2
    )
    add(
        "S24-planner-estimand-and-third-point",
        planner["source_accounted_bytes_per_active_chunk"]
        == result["allocation_accounting"][
            "source_accounted_bytes_per_active_chunk"
        ]
        and w4["predicted_payload_bytes"]
        == 4 * planner["source_accounted_bytes_per_active_chunk"]
        and w4["observed_job_peak_bytes"]
        == matrix[(33, 4)]["maximum_job_peak_bytes"]
        and w4["observed_private_peak_bytes"]
        == matrix[(33, 4)]["maximum_sampled_private_bytes"]
        and w4["job_minus_private_bytes"] == 12_288
        and w4["total_processes"] == 1
        and w4["peak_process_count"] == 1
        and w4["same_run_holds_both_maxima"]
        and w2["predicted_payload_bytes"]
        == 2 * planner["source_accounted_bytes_per_active_chunk"]
        and w2["registered_job_peak_bytes"]
        == matrix[(33, 2)]["maximum_job_peak_bytes"]
        and w2["registered_private_peak_bytes"]
        == matrix[(33, 2)]["maximum_sampled_private_bytes"]
        and w2["fresh_job_peak_bytes"] == fresh_w2
        and w2["total_processes"] == 1
        and w2["peak_process_count"] == 1
        and w2["same_run_holds_both_maxima"]
        and abs(w2["registered_job_residual_fraction"])
        <= planner["payload_only_error_limit_fraction"]
        and abs(w2["fresh_job_residual_fraction"])
        <= planner["payload_only_error_limit_fraction"]
        and not planner["third_point_falsifies_mechanism"],
        "planner model targets the wrong estimand or fails at W2",
    )
    prediction = planner["bounded_prediction"]
    add(
        "S25-tiling-ruling",
        prediction["predicted_live_payload_bytes"] == PLANNER_LIVE_BYTES
        and prediction["observed_n299_w16_job_peak_bytes"]
        == result["bounded_implementation"]["n299_w16_job_peak_bytes"]
        and prediction["residual_bytes"]
        == prediction["observed_n299_w16_job_peak_bytes"] - PLANNER_LIVE_BYTES
        and abs(prediction["residual_fraction"]) <= 0.01
        and prediction["observed_under_bar"]
        and not prediction["tiling_required_for_memory_bar"]
        and not result["plan"]["architectural_tiling_required"],
        "bounded recycling does not support the no-tiling ruling",
    )
    return checks


def audit(result: dict[str, Any], report: str) -> tuple[list[str], dict[str, str]]:
    failures: list[str] = []
    for check_id, passed, message in semantic_checks(result):
        if not passed:
            failures.append(f"{check_id}: {message}")
    lines = expected_report_lines(result)
    report_lines = report.splitlines()
    for line_id, line in lines.items():
        count = report_lines.count(line)
        if count != 1:
            failures.append(
                f"R-{line_id}: canonical full line occurs {count} times, expected one"
            )
    return failures, lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = read_json(RESULTS)
    report = REPORT.read_text(encoding="utf-8")
    failures, report_lines = audit(result, report)
    total = len(semantic_checks(result)) + len(report_lines)
    payload = {
        "status": "PASS" if not failures else "FAIL",
        "checks": total,
        "passed": total - len(failures),
        "failures": failures,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"{payload['status']}: {payload['passed']}/{total} checks passed")
        for failure in failures:
            print(f"  {failure}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
