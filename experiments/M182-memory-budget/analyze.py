"""Build the canonical M182 memory attribution from frozen evidence and probes."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROPOSAL = ROOT / "docs" / "proposals" / "2026-08-sota-path.md"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
M172_CLOSURE = ROOT / "docs" / "research" / "M172-m12s-closure.md"
M172_INVARIANCE = (
    ROOT / "docs" / "research" / "M172-worker-invariance-control.md"
)
M172_PLANNER = (
    ROOT / "docs" / "research" / "M172-memory-planner-handoff.md"
)
M172_EXPERIMENT = ROOT / "experiments" / "M172-worker-memory"
M172_MEASURE = M172_EXPERIMENT / "measure_memory.py"
M172_CAMPAIGN = M172_EXPERIMENT / "results" / "campaign.json"
M172_NEGATIVE_SUMMARY = (
    M172_EXPERIMENT / "results" / "negative-control-summary.json"
)
HARNESS = ROOT / "experiments" / "m12-scorecard" / "m12-harness.py"
N7_DOC = ROOT / "docs" / "research" / "ORCH-clamp-default-decision.md"
M139 = (
    ROOT
    / "experiments"
    / "m12-scorecard"
    / "out"
    / "campaign-8009447e-m139"
)
CLOSEOUT = M139 / "closeout.json"
RECORDS = M139 / "records.jsonl"
MEASURED_CORE = ROOT / "crates" / "strehl-core" / "src" / "pyramid.rs"
MEASURED_MERGE = ROOT / "crates" / "strehl-cli" / "src" / "merge_cmd.rs"
MEASURED_ALIGN = ROOT / "crates" / "strehl-cli" / "src" / "align_cmd.rs"
MEASURED_SOURCE_PATHS = (
    "crates/strehl-cli/src/merge_cmd.rs",
    "crates/strehl-cli/src/merge_cmd/gatefloor.rs",
    "crates/strehl-cli/src/align_cmd.rs",
    "crates/strehl-core/src/pyramid.rs",
    "crates/strehl-raw/src/lib.rs",
)
MEASURED_SOURCE_ANCHORS = {
    "crates/strehl-cli/src/merge_cmd.rs": (
        "    let parts: Vec<Result<FoldPart>> = indexed",
        "        .par_chunks(per_chunk)",
        "            fws: FrameWorkspace::new(&sizes, BAND_PLANES),",
    ),
    "crates/strehl-cli/src/merge_cmd/gatefloor.rs": (
        "        let mut probe = template.clone();",
        "            planes: (0..2).map(|_| vec![0.0f32; px]).collect(),",
        "            pyr: Pyramid::zeros(&sizes),",
    ),
    "crates/strehl-cli/src/align_cmd.rs": (
        "    let mut mos = vec![0f32; fw * fh];",
        "    let mut rp = vec![0f32; fw * fh];",
        "    let mut gp = vec![0f32; fw * fh];",
        "    let mut bp = vec![0f32; fw * fh];",
    ),
    "crates/strehl-core/src/pyramid.rs": (
        "    pub fn accumulator_floats(&self) -> usize {",
        "pub struct FrameWorkspace {",
        "            ghull: Pyramid::zeros(sizes),",
        "            plane: PlaneCache::new(sizes, planes),",
    ),
    "crates/strehl-raw/src/lib.rs": (
        "        assert_eq!(allocated, 73_400_320);",
    ),
}
BAR_BYTES = 6 << 30
M139_COMMIT = "8009447e059febb8f9c59fda509f141835d6abdb"
BOUNDED_COMMIT = "a97275817c58e164f75c7cd3d80ca99444a2a145"
PLANNER_COMMIT = "fb42b9a1c6481dba3d7ef54c8505ec5ca69b649d"
PLANNER_SOURCE_COMMIT = "fc2abb499126a56302de7f21f527de5613be34e7"
PLANNER_LIVE_BYTES = 3_045_147_112
PLANNER_PER_CHUNK_LINE = (
    "| **Total** | **`2,385,817,108`** | "
    "**`2,275.29 MiB / 2.222 GiB`** |"
)
PLANNER_LIVE_LINE = "`3,045,147,112 B = 2.836 GiB`. Allowing allocator, decoder, writer, and Rayon"
PROPOSAL_BAR = (
    "then lands as: decode on CPU, everything after the channel on GPU, end state"
)
PROPOSAL_TARGET_FRAGMENT = (
    "memory ≤6 GiB warm; bytes invariant to"
)
SCORECARD_BAR = (
    "| M12 | Memory, determinism, and scaling invariance | Warm peak process-tree "
    "memory `<=6 GiB`; 299/33-frame peak ratio `<=1.10`; every fixed-worker repeat "
    "is byte-identical and the outputs at 1/2/4/8/16 workers are mutually "
    "byte-identical; N-mod-4 per-frame spread `<=2%`. |"
)
SCORECARD_WARM = (
    "3. After one warm-up, hash the highest-precision delivered bytes from each of the six"
)
HARNESS_SPAWN = "            process = subprocess.Popen("
HARNESS_SUSPEND = "                creationflags=CREATE_SUSPENDED,"
HARNESS_START_SAMPLE = "            next_sample = start"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_unique_fragment_in_text(text: str, fragment: str, label: str) -> int:
    matches = [
        index + 1
        for index, line in enumerate(text.splitlines())
        if fragment in line
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: fragment matched {len(matches)} lines, expected exactly one"
        )
    return matches[0]


def require_unique_line_in_text(text: str, line: str, label: str) -> int:
    matches = [
        index + 1
        for index, candidate in enumerate(text.splitlines())
        if candidate == line
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: full line matched {len(matches)} times, expected exactly one"
        )
    return matches[0]


def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), *args], text=True, encoding="utf-8"
    ).strip()


def git_bytes(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def active_chunks(frames: int, workers: int) -> int:
    return math.ceil(frames / math.ceil(frames / workers))


def linear_fit(xs: list[float], ys: list[float]) -> dict[str, float]:
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    slope = sum(
        (x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True)
    ) / sum((x - x_mean) ** 2 for x in xs)
    intercept = y_mean - slope * x_mean
    fitted = [intercept + slope * x for x in xs]
    residual = sum(
        (y - estimate) ** 2 for y, estimate in zip(ys, fitted, strict=True)
    )
    total = sum((y - y_mean) ** 2 for y in ys)
    return {
        "intercept_bytes": intercept,
        "slope_bytes_per_active_chunk": slope,
        "r_squared": 1.0 - residual / total,
        "maximum_absolute_residual_bytes": max(
            abs(y - estimate) for y, estimate in zip(ys, fitted, strict=True)
        ),
    }


def pyramid_sizes(width: int, height: int, bands: int = 7) -> list[dict[str, int]]:
    result = []
    for _ in range(bands + 1):
        result.append({"width": width, "height": height, "pixels": width * height})
        width = (width + 1) // 2
        height = (height + 1) // 2
    return result


def allocation_accounting(width: int, height: int) -> dict[str, Any]:
    planes = 4
    px = width * height
    full_px = 4 * px
    sizes = pyramid_sizes(width, height)
    pyramid_px = sum(level["pixels"] for level in sizes)
    frame_bytes = 73_400_320

    consumers = {
        # num + usum + den are 9 complete pyramids; level-0 lo/hi are
        # another 8 planes under the shipping InputRange hull.
        "band_merge": 4 * (9 * pyramid_px + 8 * px),
        # Two operator Workspaces, seven pyramids, and four level-0 fields.
        # FrameWorkspace::floats at the measured revision omitted ghull and
        # PlaneCache.ws; this is the allocation, not the printed estimate.
        "frame_workspace": 4 * (8 * px + 7 * pyramid_px + 3 * width),
        # mos + R + G + B, all simultaneously live during full-res demosaic.
        "fullres_gather_transient": 4 * 4 * full_px,
        # Two green fields, luma, one Workspace, and one pyramid.
        "gate_floor_probe": 4 * (5 * px + width + pyramid_px),
        "planes_luma_variance": 4 * 6 * px,
        # Two f32 plane buffers and one bool coverage plane.
        "warp_scratch": 9 * px,
        # The decoded real frame plus gatefloor's template.clone() probe.
        "two_decoded_frames": 2 * frame_bytes,
    }
    per_chunk = sum(consumers.values())
    ordered = sorted(consumers.items(), key=lambda item: item[1], reverse=True)
    return {
        "geometry": {
            "plane_width": width,
            "plane_height": height,
            "plane_pixels": px,
            "full_pixels": full_px,
            "pyramid_levels": sizes,
            "pyramid_pixels": pyramid_px,
        },
        "consumers_bytes_per_active_chunk": consumers,
        "top_three": [
            {"name": name, "bytes_per_active_chunk": value} for name, value in ordered[:3]
        ],
        "source_accounted_bytes_per_active_chunk": per_chunk,
    }


def accepted_scored_records() -> list[dict[str, Any]]:
    result = []
    for line in RECORDS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["accepted_for_protocol"] and row["kind"] == "scored":
            result.append(row)
    return result


def build() -> dict[str, Any]:
    proposal_relative = str(PROPOSAL.relative_to(ROOT)).replace("\\", "/")
    scorecard_relative = str(SCORECARD.relative_to(ROOT)).replace("\\", "/")
    harness_relative = str(HARNESS.relative_to(ROOT)).replace("\\", "/")
    planner_relative = str(M172_PLANNER.relative_to(ROOT)).replace("\\", "/")
    n7_relative = str(N7_DOC.relative_to(ROOT)).replace("\\", "/")
    proposal_blob = git_bytes("show", f"{PLANNER_COMMIT}:{proposal_relative}")
    scorecard_blob = git_bytes("show", f"{PLANNER_COMMIT}:{scorecard_relative}")
    harness_blob = git_bytes("show", f"{PLANNER_COMMIT}:{harness_relative}")
    planner_blob = git_bytes("show", f"{PLANNER_COMMIT}:{planner_relative}")
    n7_blob = git_bytes("show", f"{PLANNER_COMMIT}:{n7_relative}")
    proposal_text = proposal_blob.decode("utf-8")
    scorecard_text = scorecard_blob.decode("utf-8")
    harness_text = harness_blob.decode("utf-8")
    planner_text = planner_blob.decode("utf-8")
    proposal_target_line = require_unique_fragment_in_text(
        proposal_text, PROPOSAL_TARGET_FRAGMENT, "proposal memory target"
    )
    scorecard_bar_line = require_unique_line_in_text(
        scorecard_text, SCORECARD_BAR, "scorecard M12 bar"
    )
    scorecard_warm_line = require_unique_line_in_text(
        scorecard_text, SCORECARD_WARM, "scorecard warm protocol"
    )
    harness_lines = {
        "spawn": require_unique_line_in_text(
            harness_text, HARNESS_SPAWN, "harness spawn"
        ),
        "suspended": require_unique_line_in_text(
            harness_text, HARNESS_SUSPEND, "harness suspended creation"
        ),
        "first_sample": require_unique_line_in_text(
            harness_text, HARNESS_START_SAMPLE, "harness first sample"
        ),
    }

    closeout = read_json(CLOSEOUT)
    matrix = []
    for key, cell in closeout["cells"].items():
        n_part, worker_part = key.split("-")
        frames = int(n_part[1:])
        workers = int(worker_part[1:])
        matrix.append(
            {
                "frames": frames,
                "workers": workers,
                "active_chunks": active_chunks(frames, workers),
                "maximum_job_peak_bytes": cell[
                    "maximum_kernel_job_peak_memory_bytes"
                ],
                "maximum_sampled_private_bytes": cell[
                    "maximum_sampled_process_tree_private_committed_bytes"
                ],
            }
        )
    matrix.sort(key=lambda row: (row["frames"], row["workers"]))
    formal_fit = linear_fit(
        [row["active_chunks"] for row in matrix],
        [row["maximum_job_peak_bytes"] for row in matrix],
    )

    scored = accepted_scored_records()
    warmups = []
    for line in RECORDS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["accepted_for_protocol"] and row["kind"] == "warmup":
            warmups.append(row)
    process_semantics = {
        "accepted_warmup_invocations": len(warmups),
        "accepted_scored_invocations": len(scored),
        "warmup_and_scored_are_separate_processes": all(
            len(row["memory"]["process_lifetimes"]) >= 1 for row in warmups + scored
        ),
        "interpretation": (
            "warm excludes the dedicated warm-up invocation; each scored process is "
            "sampled from suspended creation through process-tree exit, so its startup "
            "and first-frame allocations remain in scope"
        ),
    }
    m139_harness_hashes = {row["harness_sha256"] for row in scored}
    if len(m139_harness_hashes) != 1:
        raise RuntimeError(
            f"M139 scored rows name {len(m139_harness_hashes)} harness hashes"
        )
    m139_harness_sha256 = next(iter(m139_harness_hashes))

    reproduction = []
    for name in ("pre-n33-w1", "pre-n33-w2", "pre-n33-w4"):
        row = read_json(HERE / f"{name}.json")
        cell = closeout["cells"][f"N33-W{row['workers']}"]
        fresh = row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]
        canonical = cell["maximum_kernel_job_peak_memory_bytes"]
        reproduction.append(
            {
                "name": name,
                "frames": row["limit"],
                "workers": row["workers"],
                "fresh_job_peak_bytes": fresh,
                "canonical_n33_max_job_peak_bytes": canonical,
                "relative_delta": fresh / canonical - 1.0,
                "binary_sha256": row["probe"]["binary_sha256"],
                "valid": row["valid"],
            }
        )
    reproduction_fit = linear_fit(
        [row["workers"] for row in reproduction],
        [row["fresh_job_peak_bytes"] for row in reproduction],
    )

    accounting = allocation_accounting(3516, 2344)
    source_gap = (
        formal_fit["slope_bytes_per_active_chunk"]
        - accounting["source_accounted_bytes_per_active_chunk"]
    )
    planner_per_chunk_line = require_unique_line_in_text(
        planner_text,
        PLANNER_PER_CHUNK_LINE,
        "M172 planner per-chunk total",
    )
    planner_live_line = require_unique_line_in_text(
        planner_text,
        PLANNER_LIVE_LINE,
        "M172 planner bounded live payload",
    )

    def peak_record(
        workers: int, key: str
    ) -> dict[str, Any]:
        rows = [
            row
            for row in scored
            if row["limit"] == 33 and row["workers"] == workers
        ]
        if len(rows) != 6:
            raise RuntimeError(
                f"M139 N33/W{workers}: found {len(rows)} scored rows, expected six"
            )
        if key == "job":
            return max(
                rows,
                key=lambda row: row["memory"]["kernel_job_peak_memory"][
                    "peak_job_memory_used_bytes"
                ],
            )
        if key == "private":
            return max(
                rows,
                key=lambda row: row["memory"][
                    "peak_process_tree_private_committed_bytes"
                ],
            )
        raise RuntimeError(f"unsupported peak record key {key!r}")

    planner_per_chunk = accounting["source_accounted_bytes_per_active_chunk"]
    w2_job_record = peak_record(2, "job")
    w2_private_record = peak_record(2, "private")
    w4_job_record = peak_record(4, "job")
    w4_private_record = peak_record(4, "private")

    def memory_values(row: dict[str, Any]) -> tuple[int, int]:
        memory = row["memory"]
        return (
            memory["kernel_job_peak_memory"]["peak_job_memory_used_bytes"],
            memory["peak_process_tree_private_committed_bytes"],
        )

    w2_job_peak, w2_private_at_job_peak = memory_values(w2_job_record)
    w2_job_at_private_peak, w2_private_peak = memory_values(w2_private_record)
    w4_job_peak, w4_private_at_job_peak = memory_values(w4_job_record)
    w4_job_at_private_peak, w4_private_peak = memory_values(w4_private_record)
    if w2_job_record["position_key"] != w2_private_record["position_key"]:
        raise RuntimeError("M139 N33/W2 Job and private maxima came from different runs")
    if w4_job_record["position_key"] != w4_private_record["position_key"]:
        raise RuntimeError("M139 N33/W4 Job and private maxima came from different runs")
    if w2_job_peak != w2_job_at_private_peak or w4_job_peak != w4_job_at_private_peak:
        raise RuntimeError("M139 peak record accounting is inconsistent")
    fresh_w2_record = read_json(HERE / "pre-n33-w2.json")
    fresh_w2_job = fresh_w2_record["memory"]["kernel_job_peak_memory"][
        "peak_job_memory_used_bytes"
    ]
    planner_w2_prediction = 2 * planner_per_chunk
    planner_w4_prediction = 4 * planner_per_chunk

    post33 = read_json(HERE / "post-n33-w16.json")
    post299 = read_json(HERE / "post-n299-w16.json")
    post33_peak = post33["memory"]["kernel_job_peak_memory"][
        "peak_job_memory_used_bytes"
    ]
    post299_peak = post299["memory"]["kernel_job_peak_memory"][
        "peak_job_memory_used_bytes"
    ]
    old_peak = closeout["cells"]["N299-W16"][
        "maximum_kernel_job_peak_memory_bytes"
    ]
    bounded = {
        "commit": BOUNDED_COMMIT,
        "current_memory_files_last_commit": {
            "merge_cmd": git(
                "log",
                "-1",
                "--format=%H",
                "--",
                "crates/strehl-cli/src/merge_cmd.rs",
            ),
            "pyramid": git(
                "log",
                "-1",
                "--format=%H",
                "--",
                "crates/strehl-core/src/pyramid.rs",
            ),
        },
        "n33_w16_job_peak_bytes": post33_peak,
        "n299_w16_job_peak_bytes": post299_peak,
        "n299_over_n33_ratio": post299_peak / post33_peak,
        "n299_w16_under_bar": post299_peak <= BAR_BYTES,
        "headroom_bytes": BAR_BYTES - post299_peak,
        "saving_from_m139_peak_bytes": old_peak - post299_peak,
        "reduction_factor": old_peak / post299_peak,
        "n33_valid": post33["valid"],
        "n299_valid": post299["valid"],
        "binary_sha256": post299["probe"]["binary_sha256"],
        "diagnostic_not_formal_scorecard_rerun": True,
    }

    band_merge = accounting["consumers_bytes_per_active_chunk"]["band_merge"]
    non_accumulator_bundle = (
        accounting["source_accounted_bytes_per_active_chunk"] - band_merge
    )
    plan = {
        "bounded_change_reachable": True,
        "architectural_tiling_required": False,
        "reason": (
            "the frame fold was already streaming; the defect was coupling execution "
            "threads to simultaneously resident whole-frame workers"
        ),
        "steps": [
            {
                "files": ["crates/strehl-cli/src/merge_cmd.rs"],
                "functions": ["run_pyramid", "BandWorker::reset_chunk"],
                "change": (
                    "run canonical arithmetic chunks serially through one reusable "
                    "BandWorker while a fixed Rayon pool parallelizes spatial work"
                ),
                "estimated_saving_bytes": 15 * non_accumulator_bundle,
                "saving_scope": (
                    "N299/W16; removes 15 duplicate non-accumulator worker bundles"
                ),
            },
            {
                "files": ["crates/strehl-core/src/pyramid.rs"],
                "functions": ["BandMerge::reset_for_reuse"],
                "change": (
                    "zero and reuse one scratch partial, retaining only the accumulated "
                    "result; preserve canonical chunk boundaries and absorb order"
                ),
                "estimated_saving_bytes": 14 * band_merge,
                "saving_scope": "N299/W16; reduces 16 simultaneous accumulators to two",
            },
            {
                "files": [
                    "crates/strehl-core/src/pyramid.rs",
                    "crates/strehl-cli/src/merge_cmd.rs",
                ],
                "functions": [
                    "pyramid spatial operators",
                    "extract_planes",
                    "load_frame",
                ],
                "change": (
                    "parallelize disjoint rows/planes inside the reusable worker so 16 "
                    "threads do not require 16 whole-frame states"
                ),
                "estimated_saving_bytes": 0,
                "saving_scope": "enabler; its benefit is retained parallel execution",
            },
        ],
        "already_landed_concurrently_at": BOUNDED_COMMIT,
    }

    probe_commission = read_json(HERE / "probe-commission.json")
    measured_source: dict[str, Any] = {}
    for path in MEASURED_SOURCE_PATHS:
        data = git_bytes("show", f"{M139_COMMIT}:{path}")
        text = data.decode("utf-8")
        anchors = {}
        for anchor in MEASURED_SOURCE_ANCHORS[path]:
            count = text.splitlines().count(anchor)
            if count != 1:
                raise RuntimeError(
                    f"{M139_COMMIT}:{path}: source anchor {anchor!r} matched "
                    f"{count} full lines"
                )
            anchors[anchor] = count
        measured_source[path] = {
            "sha256": sha256_bytes(data),
            "bytes": len(data),
            "anchors": anchors,
        }
    m172_artifacts = {}
    for path in (
        M172_MEASURE,
        M172_CAMPAIGN,
        M172_NEGATIVE_SUMMARY,
        M172_INVARIANCE,
        M172_CLOSURE,
        M172_PLANNER,
    ):
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        last_commit = git("log", "-1", "--format=%H", "--", relative)
        artifact_blob = git_bytes("show", f"{last_commit}:{relative}")
        m172_artifacts[relative] = {
            "sha256": sha256_bytes(artifact_blob),
            "last_commit": last_commit,
        }
    fresh_w4_peak = next(
        row["fresh_job_peak_bytes"] for row in reproduction if row["workers"] == 4
    )
    return {
        "schema": "m182-memory-budget-v1",
        "bar": {
            "bytes": BAR_BYTES,
            "proposal_quote": "memory ≤6 GiB warm",
            "proposal_line": proposal_target_line,
            "proposal_context_heading": (
                "D13. Scaling — all sixteen cores inside the same six gigabytes"
            ),
            "scorecard_quote": "Warm peak process-tree memory `<=6 GiB`",
            "scorecard_line": scorecard_bar_line,
            "scorecard_warm_protocol_line": scorecard_warm_line,
            "documents_disagree": False,
            "intended_at_16_workers": True,
            "warm_semantics": process_semantics,
            "harness_source_lines": harness_lines,
        },
        "m139": {
            "measured_commit": M139_COMMIT,
            "maximum_position_key": closeout["absolute_bars"]["memory_ceiling"][
                "maximum_position_key"
            ],
            "maximum_job_peak_bytes": old_peak,
            "maximum_sampled_private_bytes": closeout["absolute_bars"][
                "memory_ceiling"
            ]["maximum_sampled_process_tree_private_committed_bytes"],
            "matrix": matrix,
            "active_chunk_fit": formal_fit,
        },
        "reproduction": {
            "rows": reproduction,
            "worker_fit": reproduction_fit,
        },
        "allocation_accounting": {
            **accounting,
            "fit_minus_accounting_bytes_per_active_chunk": source_gap,
            "fraction_of_fitted_slope_accounted": (
                accounting["source_accounted_bytes_per_active_chunk"]
                / formal_fit["slope_bytes_per_active_chunk"]
            ),
            "n299_w16_top_three": [
                {
                    **row,
                    "bytes_at_16_active_chunks": 16 * row["bytes_per_active_chunk"],
                }
                for row in accounting["top_three"]
            ],
        },
        "bounded_implementation": bounded,
        "plan": plan,
        "m172_evidence_boundary": {
            "authored_bounded_memory_commit": BOUNDED_COMMIT,
            "m172_answered_step4": True,
            "m172_answered_step3": True,
            "step4_imported_conclusion": (
                "one reusable BandWorker, two BandMerge accumulators, and spatial "
                "parallelism bound memory without tiling"
            ),
            "step3_overlap": (
                "the routed planner handoff contains the same ranked source allocation "
                "ledger that M182 independently derived"
            ),
            "independently_verified_by_m182": [
                "bar and warm lifecycle semantics from governing documents and harness",
                "registered unrepaired M139 failure and fifteen-cell scaling law",
                "fresh unrepaired N33 W1/W2/W4 Job peaks",
                "exact source allocation ledger and 99.847647 percent slope closure",
                "a9727581 source shape, binary identity, and aligned N33/N299 W16 memory",
                "bidirectional and inert commissioning of the Job Object meter",
            ],
            "accepted_from_m172_without_independent_rerun": [
                "post-D9 cross-worker byte invariance on the registered N33 arm",
                "prequantization f32 negative-control results",
            ],
            "m172_throughput_campaign_timed_runs": len(
                read_json(M172_CAMPAIGN)["timed_runs"]
            ),
            "unrerun_m172_claims_used_in_memory_verdict": False,
            "m12_s_acted_on": False,
            "m179_outputs_read_or_acted_on": False,
            "closure_doc_is_downstream_of_m182": (
                m172_artifacts[
                    "docs/research/M172-m12s-closure.md"
                ]["last_commit"]
                == "15b5f2f671a062dff0c0620bd5af16c7ffcead67"
            ),
            "planner_preservation_commit": PLANNER_COMMIT,
            "planner_source_commit": PLANNER_SOURCE_COMMIT,
            "planner_preservation_parent": git(
                "show", "-s", "--format=%P", PLANNER_COMMIT
            ),
            "artifacts": m172_artifacts,
        },
        "planner_hypothesis": {
            "source_accounted_bytes_per_active_chunk": planner_per_chunk,
            "handoff_per_chunk_line": planner_per_chunk_line,
            "modeled_live_payload_bytes": PLANNER_LIVE_BYTES,
            "handoff_live_line": planner_live_line,
            "w4_model_cell": {
                "frames": 33,
                "workers": 4,
                "active_chunks": 4,
                "position_key": w4_job_record["position_key"],
                "predicted_payload_bytes": planner_w4_prediction,
                "observed_job_peak_bytes": w4_job_peak,
                "observed_private_peak_bytes": w4_private_peak,
                "job_minus_private_bytes": w4_job_peak - w4_private_peak,
                "job_residual_bytes": w4_job_peak - planner_w4_prediction,
                "job_residual_fraction": (
                    w4_job_peak - planner_w4_prediction
                )
                / w4_job_peak,
                "total_processes": w4_job_record["memory"][
                    "kernel_job_accounting"
                ]["total_processes"],
                "peak_process_count": w4_job_record["memory"][
                    "peak_process_count"
                ],
                "same_run_holds_both_maxima": True,
            },
            "w2_third_point": {
                "frames": 33,
                "workers": 2,
                "active_chunks": 2,
                "position_key": w2_job_record["position_key"],
                "predicted_payload_bytes": planner_w2_prediction,
                "registered_job_peak_bytes": w2_job_peak,
                "registered_private_peak_bytes": w2_private_peak,
                "job_minus_private_bytes": w2_job_peak - w2_private_peak,
                "registered_job_residual_bytes": (
                    w2_job_peak - planner_w2_prediction
                ),
                "registered_job_residual_fraction": (
                    w2_job_peak - planner_w2_prediction
                )
                / w2_job_peak,
                "fresh_job_peak_bytes": fresh_w2_job,
                "fresh_job_residual_bytes": (
                    fresh_w2_job - planner_w2_prediction
                ),
                "fresh_job_residual_fraction": (
                    fresh_w2_job - planner_w2_prediction
                )
                / fresh_w2_job,
                "total_processes": w2_job_record["memory"][
                    "kernel_job_accounting"
                ]["total_processes"],
                "peak_process_count": w2_job_record["memory"][
                    "peak_process_count"
                ],
                "same_run_holds_both_maxima": True,
            },
            "payload_only_error_limit_fraction": 0.01,
            "third_point_falsifies_mechanism": (
                abs(w2_job_peak - planner_w2_prediction) / w2_job_peak
                > 0.01
            ),
            "bounded_prediction": {
                "predicted_live_payload_bytes": PLANNER_LIVE_BYTES,
                "observed_n299_w16_job_peak_bytes": post299_peak,
                "residual_bytes": post299_peak - PLANNER_LIVE_BYTES,
                "residual_fraction": (
                    post299_peak - PLANNER_LIVE_BYTES
                )
                / post299_peak,
                "observed_under_bar": post299_peak <= BAR_BYTES,
                "tiling_required_for_memory_bar": False,
            },
        },
        "n7": {
            "unrepaired_certifying_commit": M139_COMMIT,
            "unrepaired_registered_job_peak_bytes": old_peak,
            "unrepaired_registered_test_failed": old_peak > BAR_BYTES,
            "fresh_unrepaired_w4_job_peak_bytes": fresh_w4_peak,
            "fresh_unrepaired_w4_failed": fresh_w4_peak > BAR_BYTES,
            "repaired_result_cashed_as_formal_pass": False,
            "certifying_rerun_owner": "M179-m12-rerun",
            "registered_gate_harness_sha256": m139_harness_sha256,
            "owned_probe_harness_sha256": probe_commission["harness_sha256"],
            "same_registered_gate_observed_red": (
                m139_harness_sha256
                == probe_commission["harness_sha256"]
            ),
            "changed_future_gate_requires_new_unrepaired_red": True,
            "rule_document_commit": PLANNER_COMMIT,
            "rule_document_sha256": sha256_bytes(n7_blob),
        },
        "probe_commission": {
            "status": probe_commission["status"],
            "harness_sha256": probe_commission["harness_sha256"],
            "deltas": probe_commission["deltas"],
            "checks": probe_commission["checks"],
        },
        "provenance": {
            "closeout_sha256": sha256(CLOSEOUT),
            "records_sha256": sha256(RECORDS),
            "harness_sha256": m139_harness_sha256,
            "governing_text_commit": PLANNER_COMMIT,
            "proposal_sha256": sha256_bytes(proposal_blob),
            "scorecard_sha256": sha256_bytes(scorecard_blob),
            "current_merge_cmd_sha256": sha256(MEASURED_MERGE),
            "current_pyramid_sha256": sha256(MEASURED_CORE),
            "current_align_cmd_sha256": sha256(MEASURED_ALIGN),
            "measured_source": measured_source,
        },
        "briefing_correction": {
            "given": (
                "N-mod-4 per-frame spread passes at 0.07618677189815302% "
                "against <=2%"
            ),
            "correct": (
                "the registered fraction is 0.07618677189815302 = 7.618677%, "
                "so the numeric bar fails; M139 formally quarantines the timing verdict"
            ),
        },
    }


def main() -> int:
    result = build()
    output = HERE / "results.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "old_peak_gib": result["m139"]["maximum_job_peak_bytes"] / 2**30,
                "fit_gib_per_active_chunk": result["m139"]["active_chunk_fit"][
                    "slope_bytes_per_active_chunk"
                ]
                / 2**30,
                "source_accounted_fraction": result["allocation_accounting"][
                    "fraction_of_fitted_slope_accounted"
                ],
                "post_n299_w16_gib": result["bounded_implementation"][
                    "n299_w16_job_peak_bytes"
                ]
                / 2**30,
                "post_n299_over_n33": result["bounded_implementation"][
                    "n299_over_n33_ratio"
                ],
                "probe_commission": result["probe_commission"]["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
