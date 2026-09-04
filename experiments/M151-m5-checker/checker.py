"""M151 input-only M5 manifest builder and output scorer.

The two CLI phases are deliberately separate:

* ``manifest`` accepts prepared common-input spectra only.
* ``score`` accepts the frozen manifest and candidate spectra.

This file never renders a stack.  ``commission.py`` creates controlled
candidate spectra from development inputs to exercise both directions.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
from typing import Any, Iterable

import numpy as np


LANE = Path(__file__).resolve().parent
DEFINITIONS_PATH = LANE / "frozen-definitions.json"
DEFINITIONS = json.loads(DEFINITIONS_PATH.read_text(encoding="utf-8"))
DEFINITIONS_SHA256 = hashlib.sha256(DEFINITIONS_PATH.read_bytes()).hexdigest()
PROTOCOL = DEFINITIONS["protocol"]
BLOCK_COUNT = 16
BOOTSTRAP_DRAWS = int(DEFINITIONS["bootstrap"]["draws"])
BOOTSTRAP_SEED = int(DEFINITIONS["bootstrap"]["seed"])
BOOTSTRAP_LCB_PROBABILITY = float(
    DEFINITIONS["bootstrap"]["lcb_probability"]
)
REGULARIZER = np.asarray(
    DEFINITIONS["election"]["regularizer"]["kernel"], dtype=np.float64
)
FAR_DISTANCE = int(DEFINITIONS["eligibility"]["far_minimum_node_distance"])
POINT_RATIO_MIN = float(DEFINITIONS["eligibility"]["best_far_point_min"])
RATIO_LCB_MIN = float(
    DEFINITIONS["eligibility"]["best_far_ratio_lcb_min"]
)
RHO_BEST_MIN = float(DEFINITIONS["thresholds"]["rho_best_min"])
MARGIN_MIN = float(DEFINITIONS["thresholds"]["focus_margin_min"])
COVERAGE_MIN = float(DEFINITIONS["thresholds"]["coverage_point_min"])
WILSON_MIN = float(DEFINITIONS["thresholds"]["wilson_lcb95_min"])
RUN_MAX = float(DEFINITIONS["run"]["threshold_fraction"])
FOV_MIN = float(DEFINITIONS["fov"]["threshold"])
WILSON_Z = float(DEFINITIONS["wilson"]["z"])


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
    return value


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def file_sha256(path: Path, block_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block_size):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".new")
    temporary.write_text(
        json.dumps(
            _jsonable(value),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def arrays_digest(arrays: Iterable[np.ndarray]) -> str:
    digest = hashlib.sha256()
    for value in arrays:
        array = np.ascontiguousarray(value)
        digest.update(str(array.dtype).encode("ascii"))
        digest.update(canonical_json(list(array.shape)))
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def _validate_crosspower(
    election_crosspower: np.ndarray,
    evaluation_crosspower: np.ndarray,
    site_ids: list[str],
    site_xy: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    election = np.asarray(election_crosspower, dtype=np.float64)
    evaluation = np.asarray(evaluation_crosspower, dtype=np.float64)
    coordinates = np.asarray(site_xy, dtype=np.int64)
    if election.shape != evaluation.shape:
        raise ValueError(
            "election and evaluation cross-power arrays must have equal shape"
        )
    if election.ndim != 3 or election.shape[2] != BLOCK_COUNT:
        raise ValueError(
            f"cross-power shape must be [sites,nodes,{BLOCK_COUNT}], "
            f"found {election.shape}"
        )
    if election.shape[0] != len(site_ids):
        raise ValueError("site id count does not match cross-power site count")
    if coordinates.shape != (len(site_ids), 2):
        raise ValueError("site coordinates must have shape [sites,2]")
    if len(set(site_ids)) != len(site_ids):
        raise ValueError("site identifiers must be unique")
    if election.shape[1] < 8:
        raise ValueError("M5 needs at least eight focus nodes")
    if np.any(~np.isfinite(election[:, 1:-1])):
        raise ValueError("interior election cross-power is not finite")
    if np.any(~np.isfinite(evaluation[:, 1:-1])):
        raise ValueError("interior evaluation cross-power is not finite")
    return election, evaluation, coordinates


def regularize_curve(curve: np.ndarray) -> np.ndarray:
    """Regularise node curves with the frozen five-node binomial kernel."""

    values = np.asarray(curve, dtype=np.float64)
    if values.shape[-1] < 8:
        raise ValueError("M5 needs at least eight focus nodes")
    interior = values[..., 1:-1]
    padded = np.pad(interior, [(0, 0)] * (interior.ndim - 1) + [(2, 2)], mode="edge")
    windows = np.lib.stride_tricks.sliding_window_view(
        padded, REGULARIZER.size, axis=-1
    )
    filtered = np.sum(windows * REGULARIZER, axis=-1)
    result = np.full(values.shape, np.nan, dtype=np.float64)
    result[..., 1:-1] = filtered
    return result


def _candidate_nodes(node_count: int) -> np.ndarray:
    # Frozen prose: nodes 3 through N-4 inclusive, using zero-based indexing.
    candidates = np.arange(3, node_count - 3, dtype=np.int64)
    if candidates.size == 0:
        raise ValueError("no legal election node")
    return candidates


def _ratio(best_signal: np.ndarray, far_signal: np.ndarray) -> np.ndarray:
    best = np.maximum(np.asarray(best_signal, dtype=np.float64), 0.0)
    far = np.maximum(np.asarray(far_signal, dtype=np.float64), 0.0)
    result = np.zeros(np.broadcast_shapes(best.shape, far.shape), dtype=np.float64)
    best, far = np.broadcast_arrays(best, far)
    positive_best = best > 0.0
    positive_far = far > 0.0
    ordinary = positive_best & positive_far
    result[ordinary] = best[ordinary] / far[ordinary]
    result[positive_best & ~positive_far] = math.inf
    return result


def _nearest_rank(values: np.ndarray, probability: float) -> float:
    ordered = np.sort(np.asarray(values, dtype=np.float64))
    if ordered.size == 0:
        raise ValueError("nearest-rank quantile needs at least one value")
    rank = max(1, int(math.ceil(probability * ordered.size)))
    return float(ordered[rank - 1])


def _site_seed(site_id: str) -> int:
    mixed = int.from_bytes(
        hashlib.sha256(site_id.encode("utf-8")).digest()[:8], "little"
    )
    return BOOTSTRAP_SEED ^ mixed


def _bootstrap_ratio_lcb(
    election_blocks: np.ndarray,
    evaluation_blocks: np.ndarray,
    site_id: str,
) -> tuple[float, dict[str, int]]:
    """Re-elect the best node in every frozen spatial-block bootstrap draw."""

    election = np.asarray(election_blocks, dtype=np.float64)
    evaluation = np.asarray(evaluation_blocks, dtype=np.float64)
    if election.shape != evaluation.shape or election.ndim != 2:
        raise ValueError("site block arrays must have shape [nodes,blocks]")
    if election.shape[1] != BLOCK_COUNT:
        raise ValueError(f"expected {BLOCK_COUNT} bootstrap blocks")

    rng = np.random.Generator(np.random.PCG64(_site_seed(site_id)))
    counts = rng.multinomial(
        BLOCK_COUNT,
        np.full(BLOCK_COUNT, 1.0 / BLOCK_COUNT),
        size=BOOTSTRAP_DRAWS,
    )
    weights = counts.astype(np.float64) / BLOCK_COUNT
    election_draws = weights @ election.T
    evaluation_draws = weights @ evaluation.T
    regularized = regularize_curve(election_draws)
    candidates = _candidate_nodes(election.shape[0])
    best = candidates[
        np.argmax(regularized[:, candidates], axis=1)
    ]
    row = np.arange(BOOTSTRAP_DRAWS)
    best_signal = evaluation_draws[row, best]
    nodes = np.arange(election.shape[0], dtype=np.int64)[None, :]
    far_mask = (
        (np.abs(nodes - best[:, None]) >= FAR_DISTANCE)
        & (nodes >= 1)
        & (nodes < election.shape[0] - 1)
    )
    far_signal = np.max(
        np.where(far_mask, np.maximum(evaluation_draws, 0.0), -math.inf),
        axis=1,
    )
    ratios = _ratio(best_signal, far_signal)
    return _nearest_rank(ratios, BOOTSTRAP_LCB_PROBABILITY), {
        "zero_or_negative_best_draws": int(np.count_nonzero(best_signal <= 0.0)),
        "nonpositive_far_draws": int(
            np.count_nonzero((best_signal > 0.0) & (far_signal <= 0.0))
        ),
    }


def build_manifest(
    election_crosspower: np.ndarray,
    evaluation_crosspower: np.ndarray,
    site_ids: list[str],
    site_xy: np.ndarray,
    *,
    input_digest: str,
    capture_id: str,
) -> dict[str, Any]:
    """Build the immutable input-only manifest.

    Deliberately has no candidate/output argument.  Tests assert that this
    remains true.
    """

    election, evaluation, coordinates = _validate_crosspower(
        election_crosspower,
        evaluation_crosspower,
        site_ids,
        site_xy,
    )
    node_count = election.shape[1]
    candidates = _candidate_nodes(node_count)
    election_curve = np.mean(election, axis=2)
    evaluation_curve = np.mean(evaluation, axis=2)
    regularized = regularize_curve(election_curve)

    sites: list[dict[str, Any]] = []
    for index, site_id in enumerate(site_ids):
        best = int(candidates[np.argmax(regularized[index, candidates])])
        far_nodes = np.flatnonzero(
            (np.abs(np.arange(node_count) - best) >= FAR_DISTANCE)
            & (np.arange(node_count) >= 1)
            & (np.arange(node_count) < node_count - 1)
        )
        best_signal = float(evaluation_curve[index, best])
        far_signal = float(np.max(evaluation_curve[index, far_nodes]))
        point_ratio = float(_ratio(np.asarray(best_signal), np.asarray(far_signal)))
        ratio_lcb, bootstrap_diagnostics = _bootstrap_ratio_lcb(
            election[index],
            evaluation[index],
            site_id,
        )
        eligible = point_ratio >= POINT_RATIO_MIN and ratio_lcb >= RATIO_LCB_MIN
        sites.append(
            {
                "best_node": best,
                "bootstrap": bootstrap_diagnostics,
                "eligible": bool(eligible),
                "election_curve": election_curve[index].tolist(),
                "election_regularized": regularized[index].tolist(),
                "evaluation_curve": evaluation_curve[index].tolist(),
                "far_node_count": int(far_nodes.size),
                "far_source_signal": far_signal,
                "point_ratio": point_ratio,
                "ratio_lcb95": ratio_lcb,
                "site_id": site_id,
                "x": int(coordinates[index, 0]),
                "y": int(coordinates[index, 1]),
                "best_source_signal": best_signal,
            }
        )

    unsigned = {
        "capture_id": capture_id,
        "definitions_sha256": DEFINITIONS_SHA256,
        "input_digest": input_digest,
        "node_count": int(node_count),
        "protocol": PROTOCOL,
        "site_count": len(sites),
        "eligible_count": int(sum(site["eligible"] for site in sites)),
        "sites": sites,
    }
    manifest = dict(unsigned)
    manifest["manifest_sha256"] = payload_sha256(unsigned)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("protocol") != PROTOCOL:
        raise ValueError(
            f"manifest protocol {manifest.get('protocol')!r} != {PROTOCOL!r}"
        )
    if manifest.get("definitions_sha256") != DEFINITIONS_SHA256:
        raise ValueError("manifest definitions hash does not match frozen definitions")
    claimed = manifest.get("manifest_sha256")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    actual = payload_sha256(unsigned)
    if claimed != actual:
        raise ValueError(f"manifest hash mismatch: claimed {claimed}, actual {actual}")


def wilson_lower(successes: int, trials: int) -> float:
    if trials <= 0:
        return math.nan
    if successes < 0 or successes > trials:
        raise ValueError("Wilson successes must lie in [0,trials]")
    p = successes / trials
    z2 = WILSON_Z * WILSON_Z
    denominator = 1.0 + z2 / trials
    center = p + z2 / (2.0 * trials)
    radius = WILSON_Z * math.sqrt(
        p * (1.0 - p) / trials + z2 / (4.0 * trials * trials)
    )
    return (center - radius) / denominator


def aggregate_scores(scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse repeated outputs to distinct physical-site Bernoulli units.

    ``capture_id`` names the physical capture/session.  Multiple required
    outputs with the same capture and site id therefore collapse by logical
    AND.  Equal site ids in different captures remain distinct.
    """

    if not scores:
        raise ValueError("at least one score is required for aggregation")
    grouped: dict[str, list[dict[str, bool]]] = {}
    for score in scores:
        capture_id = str(score["capture_id"])
        output_sites: dict[str, bool] = {}
        for row in score["site_rows"]:
            site_id = str(row["site_id"])
            if site_id in output_sites:
                raise ValueError(
                    f"duplicate site {site_id!r} in output {score['candidate_id']!r}"
                )
            output_sites[site_id] = bool(row["passed"])
        grouped.setdefault(capture_id, []).append(output_sites)

    units: dict[tuple[str, str], bool] = {}
    per_capture: dict[str, dict[str, Any]] = {}
    for capture_id in sorted(grouped):
        outputs = grouped[capture_id]
        union_ids = set().union(*(set(output) for output in outputs))
        common_ids = set(outputs[0]).intersection(
            *(set(output) for output in outputs[1:])
        )
        for site_id in common_ids:
            units[(capture_id, site_id)] = all(
                output[site_id] for output in outputs
            )
        capture_units = [
            units[(capture_id, site_id)] for site_id in sorted(common_ids)
        ]
        trials = len(capture_units)
        successes = int(sum(capture_units))
        coverage = successes / trials if trials else math.nan
        lcb = wilson_lower(successes, trials)
        per_capture[capture_id] = {
            "coverage": coverage,
            "eligible_physical_sites": trials,
            "eligible_union_before_required_output_intersection": len(union_ids),
            "excluded_not_eligible_in_every_required_output": (
                len(union_ids) - len(common_ids)
            ),
            "outputs_collapsed": len(outputs),
            "passed_physical_sites": successes,
            "point_pass": trials > 0 and coverage >= COVERAGE_MIN,
            "wilson_lcb95": lcb,
            "wilson_pass": trials > 0 and lcb >= WILSON_MIN,
        }
        per_capture[capture_id]["rate_pass"] = bool(
            trials
            >= int(DEFINITIONS["eligibility"]["minimum_eligible_sites_per_capture"])
            and per_capture[capture_id]["point_pass"]
            and per_capture[capture_id]["wilson_pass"]
        )

    pooled_trials = len(units)
    pooled_successes = int(sum(units.values()))
    pooled_coverage = pooled_successes / pooled_trials if pooled_trials else math.nan
    pooled_lcb = wilson_lower(pooled_successes, pooled_trials)
    pooled = {
        "coverage": pooled_coverage,
        "eligible_physical_sites": pooled_trials,
        "minimum_sites_pass": pooled_trials
        >= int(DEFINITIONS["eligibility"]["minimum_eligible_sites_pooled"]),
        "passed_physical_sites": pooled_successes,
        "point_pass": pooled_trials > 0 and pooled_coverage >= COVERAGE_MIN,
        "wilson_lcb95": pooled_lcb,
        "wilson_pass": pooled_trials > 0 and pooled_lcb >= WILSON_MIN,
    }
    pooled["rate_pass"] = bool(
        pooled["minimum_sites_pass"]
        and pooled["point_pass"]
        and pooled["wilson_pass"]
        and all(row["rate_pass"] for row in per_capture.values())
    )
    return {
        "definitions_sha256": DEFINITIONS_SHA256,
        "per_capture": per_capture,
        "pooled": pooled,
        "protocol": PROTOCOL,
    }


def failed_run(best_nodes: np.ndarray, passed: np.ndarray) -> dict[str, Any]:
    depths = np.asarray(best_nodes, dtype=np.int64)
    status = np.asarray(passed, dtype=bool)
    if depths.ndim != 1 or status.shape != depths.shape:
        raise ValueError("run inputs must be equal one-dimensional arrays")
    if depths.size == 0:
        return {
            "measured": False,
            "reason": "no eligible sites",
            "fraction": None,
        }
    unique = np.unique(depths)
    if unique.size < 2:
        return {
            "measured": False,
            "reason": "fewer than two unique eligible depths",
            "fraction": None,
        }

    level_failed = np.asarray(
        [np.any(~status[depths == depth]) for depth in unique], dtype=bool
    )
    boundaries = np.empty(unique.size + 1, dtype=np.float64)
    boundaries[0] = unique[0] - 0.5
    boundaries[-1] = unique[-1] + 0.5
    boundaries[1:-1] = 0.5 * (unique[:-1] + unique[1:])
    widths = np.diff(boundaries)
    total = float(boundaries[-1] - boundaries[0])

    best_start = -1
    best_end = -1
    best_length = 0.0
    index = 0
    while index < unique.size:
        if not level_failed[index]:
            index += 1
            continue
        end = index + 1
        while end < unique.size and level_failed[end]:
            end += 1
        length = float(boundaries[end] - boundaries[index])
        if length > best_length:
            best_start = index
            best_end = end
            best_length = length
        index = end

    interval = None
    failed_depths: list[int] = []
    if best_start >= 0:
        interval = [float(boundaries[best_start]), float(boundaries[best_end])]
        failed_depths = [int(value) for value in unique[best_start:best_end]]
    return {
        "measured": True,
        "depth_interval": [float(boundaries[0]), float(boundaries[-1])],
        "failed_depths": failed_depths,
        "fraction": best_length / total,
        "interval": interval,
        "length_nodes": best_length,
        "max_depth_cell_fraction": float(np.max(widths) / total),
        "total_length_nodes": total,
        "unique_depth_count": int(unique.size),
    }


def retained_fov(reference_valid: np.ndarray, output_valid: np.ndarray) -> float:
    reference = np.asarray(reference_valid, dtype=bool)
    output = np.asarray(output_valid, dtype=bool)
    if reference.shape != output.shape:
        raise ValueError("reference and output validity masks must have equal shape")
    denominator = int(np.count_nonzero(reference))
    if denominator == 0:
        raise ValueError("reference validity mask is empty")
    return float(np.count_nonzero(reference & output) / denominator)


def coherence(candidate: np.ndarray, sources: np.ndarray) -> np.ndarray:
    output = np.asarray(candidate)
    frames = np.asarray(sources)
    if output.ndim != 1 or frames.ndim != 2:
        raise ValueError("coherence expects candidate [coeff] and sources [node,coeff]")
    if frames.shape[1] != output.shape[0]:
        raise ValueError("candidate/source coefficient counts differ")
    numerator = np.abs(np.sum(output[None, :] * np.conj(frames), axis=1))
    output_power = float(np.sum(np.abs(output) ** 2))
    source_power = np.sum(np.abs(frames) ** 2, axis=1)
    denominator = np.sqrt(output_power * source_power)
    result = np.zeros(frames.shape[0], dtype=np.float64)
    valid = denominator > 0.0
    result[valid] = numerator[valid] / denominator[valid]
    return np.clip(result, 0.0, 1.0)


def score_candidate(
    manifest: dict[str, Any],
    source_eval_spectra: np.ndarray,
    candidate_eval_spectra: np.ndarray,
    reference_valid: np.ndarray,
    output_valid: np.ndarray,
    *,
    candidate_id: str,
) -> dict[str, Any]:
    validate_manifest(manifest)
    sources = np.asarray(source_eval_spectra)
    candidate = np.asarray(candidate_eval_spectra)
    site_count = len(manifest["sites"])
    node_count = int(manifest["node_count"])
    if sources.ndim != 3 or sources.shape[:2] != (site_count, node_count):
        raise ValueError(
            "source spectra must have shape [manifest sites,manifest nodes,coeff]"
        )
    if candidate.shape != (site_count, sources.shape[2]):
        raise ValueError("candidate spectra must have shape [sites,coeff]")
    if np.any(~np.isfinite(sources)) or np.any(~np.isfinite(candidate)):
        raise ValueError("source/candidate spectra contain non-finite values")

    rows: list[dict[str, Any]] = []
    for index, site in enumerate(manifest["sites"]):
        if not site["eligible"]:
            continue
        best = int(site["best_node"])
        correlations = coherence(candidate[index], sources[index])
        far_nodes = np.flatnonzero(
            np.abs(np.arange(node_count) - best) >= FAR_DISTANCE
        )
        rho_best = float(correlations[best])
        rho_far = float(np.max(correlations[far_nodes]))
        margin = rho_best - rho_far
        passed = rho_best >= RHO_BEST_MIN and margin >= MARGIN_MIN
        rows.append(
            {
                "best_node": best,
                "focus_margin": margin,
                "passed": bool(passed),
                "rho_best": rho_best,
                "rho_far": rho_far,
                "site_id": site["site_id"],
                "x": int(site["x"]),
                "y": int(site["y"]),
            }
        )

    successes = int(sum(row["passed"] for row in rows))
    trials = len(rows)
    coverage = successes / trials if trials else math.nan
    lcb = wilson_lower(successes, trials)
    run = failed_run(
        np.asarray([row["best_node"] for row in rows], dtype=np.int64),
        np.asarray([row["passed"] for row in rows], dtype=bool),
    )
    fov = retained_fov(reference_valid, output_valid)
    run_pass = bool(run["measured"] and run["fraction"] <= RUN_MAX)
    result = {
        "candidate_id": candidate_id,
        "capture_id": manifest["capture_id"],
        "coverage": coverage,
        "definitions_sha256": DEFINITIONS_SHA256,
        "eligible_sites": trials,
        "failed_sites": trials - successes,
        "fov_pass": fov >= FOV_MIN,
        "manifest_sha256": manifest["manifest_sha256"],
        "point_pass": trials > 0 and coverage >= COVERAGE_MIN,
        "retained_fov": fov,
        "run": run,
        "run_pass": run_pass,
        "site_rows": rows,
        "wilson_lcb95": lcb,
        "wilson_pass": trials > 0 and lcb >= WILSON_MIN,
    }
    result["capture_pass"] = bool(
        trials >= int(DEFINITIONS["eligibility"]["minimum_eligible_sites_per_capture"])
        and result["point_pass"]
        and result["wilson_pass"]
        and result["run_pass"]
        and result["fov_pass"]
    )
    return result


def choose_depth_slab(manifest: dict[str, Any]) -> dict[str, Any]:
    """Choose the frozen shortest/earliest >=3-node, >=10%-depth plant."""

    validate_manifest(manifest)
    depths = np.asarray(
        [site["best_node"] for site in manifest["sites"] if site["eligible"]],
        dtype=np.int64,
    )
    if np.unique(depths).size < 2:
        raise ValueError("cannot choose a slab without at least two eligible depths")
    unique = np.unique(depths)
    boundaries = np.empty(unique.size + 1, dtype=np.float64)
    boundaries[0] = unique[0] - 0.5
    boundaries[-1] = unique[-1] + 0.5
    boundaries[1:-1] = 0.5 * (unique[:-1] + unique[1:])
    total = float(boundaries[-1] - boundaries[0])

    node_count = int(manifest["node_count"])
    candidates: list[tuple[int, int, float, float, float]] = []
    for start in range(node_count):
        for end in range(start + 2, node_count):
            selected = (unique >= start) & (unique <= end)
            if not np.any(selected):
                continue
            first = int(np.flatnonzero(selected)[0])
            last = int(np.flatnonzero(selected)[-1]) + 1
            covered_start = max(float(start) - 0.5, float(boundaries[first]))
            covered_end = min(float(end) + 0.5, float(boundaries[last]))
            width = max(0.0, covered_end - covered_start)
            fraction = width / total
            if fraction >= 0.10:
                candidates.append((end - start + 1, start, fraction, covered_start, covered_end))
    if not candidates:
        raise ValueError("no contiguous >=3-node slab covers 10 percent of depth")
    length, start, fraction, covered_start, covered_end = min(
        candidates, key=lambda row: (row[0], row[1])
    )
    return {
        "covered_depth_fraction": fraction,
        "covered_depth_interval": [covered_start, covered_end],
        "end_node_inclusive": start + length - 1,
        "length_nodes": length,
        "start_node": start,
    }


def selected_candidate(
    manifest: dict[str, Any],
    source_eval_spectra: np.ndarray,
    *,
    mode: str,
    deleted_nodes: set[int] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Create an input-only oracle candidate and return selected node per site."""

    validate_manifest(manifest)
    sources = np.asarray(source_eval_spectra)
    if sources.ndim != 3:
        raise ValueError("source spectra must have shape [sites,nodes,coeff]")
    deleted = deleted_nodes or set()
    selected = np.zeros(len(manifest["sites"]), dtype=np.int64)
    nodes = np.arange(int(manifest["node_count"]), dtype=np.int64)
    for index, site in enumerate(manifest["sites"]):
        best = int(site["best_node"])
        curve = np.asarray(site["election_regularized"], dtype=np.float64)
        legal = np.isfinite(curve) & (nodes >= 3) & (nodes < len(nodes) - 3)
        if mode == "best":
            legal &= np.asarray([node not in deleted for node in nodes])
        elif mode == "far":
            legal &= np.abs(nodes - best) >= FAR_DISTANCE
        else:
            raise ValueError(f"unknown candidate selection mode {mode!r}")
        choices = np.flatnonzero(legal)
        if choices.size == 0:
            raise ValueError(f"site {site['site_id']} has no legal source node")
        selected[index] = int(choices[np.argmax(curve[choices])])
    candidate = sources[np.arange(sources.shape[0]), selected]
    return candidate, selected


def _load_prepared(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        required = {
            "election_crosspower",
            "evaluation_crosspower",
            "site_ids",
            "site_xy",
            "source_eval_real",
            "source_eval_imag",
        }
        missing = required - set(archive.files)
        if missing:
            raise ValueError(f"{path}: missing arrays {sorted(missing)}")
        return {name: archive[name] for name in archive.files}


def _manifest_command(args: argparse.Namespace) -> int:
    prepared_path = Path(args.prepared).resolve()
    prepared = _load_prepared(prepared_path)
    source = prepared["source_eval_real"] + 1j * prepared["source_eval_imag"]
    digest = arrays_digest(
        (
            prepared["election_crosspower"],
            prepared["evaluation_crosspower"],
            prepared["site_xy"],
            source,
        )
    )
    manifest = build_manifest(
        prepared["election_crosspower"],
        prepared["evaluation_crosspower"],
        [str(value) for value in prepared["site_ids"].tolist()],
        prepared["site_xy"],
        input_digest=digest,
        capture_id=args.capture_id,
    )
    atomic_json(Path(args.output), manifest)
    print(
        f"manifest sites={manifest['site_count']} "
        f"eligible={manifest['eligible_count']} "
        f"sha256={manifest['manifest_sha256']}"
    )
    return 0


def _score_command(args: argparse.Namespace) -> int:
    prepared = _load_prepared(Path(args.prepared).resolve())
    manifest = json.loads(Path(args.manifest).read_text(encoding="ascii"))
    prepared_source = (
        prepared["source_eval_real"] + 1j * prepared["source_eval_imag"]
    )
    digest = arrays_digest(
        (
            prepared["election_crosspower"],
            prepared["evaluation_crosspower"],
            prepared["site_xy"],
            prepared_source,
        )
    )
    if manifest.get("input_digest") != digest:
        raise ValueError(
            "prepared input digest differs from the input-only frozen manifest"
        )
    with np.load(Path(args.candidate).resolve(), allow_pickle=False) as archive:
        candidate = archive["candidate_real"] + 1j * archive["candidate_imag"]
        reference_valid = archive["reference_valid"]
        output_valid = archive["output_valid"]
    result = score_candidate(
        manifest,
        prepared_source,
        candidate,
        reference_valid,
        output_valid,
        candidate_id=args.candidate_id,
    )
    atomic_json(Path(args.output), result)
    print(
        f"score eligible={result['eligible_sites']} "
        f"coverage={result['coverage']:.6f} "
        f"wilson_lcb95={result['wilson_lcb95']:.6f} "
        f"longest_run={result['run']['fraction']:.6f} "
        f"retained_fov={result['retained_fov']:.6f}"
    )
    return 0 if result["capture_pass"] else 1


def _aggregate_command(args: argparse.Namespace) -> int:
    scores = [
        json.loads(Path(path).read_text(encoding="ascii")) for path in args.scores
    ]
    result = aggregate_scores(scores)
    atomic_json(Path(args.output), result)
    pooled = result["pooled"]
    print(
        f"aggregate eligible={pooled['eligible_physical_sites']} "
        f"coverage={pooled['coverage']:.6f} "
        f"wilson_lcb95={pooled['wilson_lcb95']:.6f}"
    )
    return 0 if pooled["rate_pass"] else 1


def _self_test() -> int:
    if "candidate" in inspect.signature(build_manifest).parameters:
        raise AssertionError("input-only manifest API accepts a candidate")
    expected = 500.0 / (500.0 + WILSON_Z * WILSON_Z)
    if abs(wilson_lower(500, 500) - expected) > 1.0e-15:
        raise AssertionError("Wilson all-success identity failed")
    run = failed_run(
        np.asarray([3, 4, 5, 6, 7]),
        np.asarray([True, False, False, True, True]),
    )
    if abs(float(run["length_nodes"]) - 2.0) > 1.0e-12:
        raise AssertionError(f"unexpected failed run {run}")
    source = np.asarray(
        [[1.0 + 0.0j, 0.5 + 0.5j], [0.0 + 1.0j, 1.0 + 0.0j]]
    )
    measured = coherence(source[0], source)
    if abs(float(measured[0]) - 1.0) > 1.0e-15:
        raise AssertionError("identity coherence is not one")
    reference = np.ones((10, 10), dtype=bool)
    output = reference.copy()
    output[:2] = False
    if retained_fov(reference, output) != 0.8:
        raise AssertionError("FOV arithmetic failed")
    print(
        f"self-test ok protocol={PROTOCOL} "
        f"definitions_sha256={DEFINITIONS_SHA256}"
    )
    return 0


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    subparsers = root.add_subparsers(dest="command", required=True)
    subparsers.add_parser("self-test")

    manifest = subparsers.add_parser(
        "manifest", help="build an input-only site manifest"
    )
    manifest.add_argument("--prepared", required=True)
    manifest.add_argument("--capture-id", required=True)
    manifest.add_argument("--output", required=True)

    score = subparsers.add_parser("score", help="score one frozen candidate")
    score.add_argument("--prepared", required=True)
    score.add_argument("--manifest", required=True)
    score.add_argument("--candidate", required=True)
    score.add_argument("--candidate-id", required=True)
    score.add_argument("--output", required=True)

    aggregate = subparsers.add_parser(
        "aggregate", help="collapse required outputs to physical-site Wilson units"
    )
    aggregate.add_argument("--scores", nargs="+", required=True)
    aggregate.add_argument("--output", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command == "self-test":
        return _self_test()
    if args.command == "manifest":
        return _manifest_command(args)
    if args.command == "score":
        return _score_command(args)
    if args.command == "aggregate":
        return _aggregate_command(args)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
