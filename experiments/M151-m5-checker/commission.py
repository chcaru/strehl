"""Commission the frozen M151 M5 checker in both directions.

The real arm reads only the explicitly development-only tilted slide.  It
builds a lightweight green-channel spectral proxy directly from RAW pixels;
it never renders Strehl and never opens a holdout output.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import platform
import sys
import time
from pathlib import Path
from typing import Any

# Lane M139 owns the host timing window.  Keep every numerical backend serial.
for _variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_variable] = "1"

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import rawpy  # noqa: E402
from scipy.signal.windows import tukey  # noqa: E402

from checker import (  # noqa: E402
    BLOCK_COUNT,
    DEFINITIONS_SHA256,
    FAR_DISTANCE,
    PROTOCOL,
    aggregate_scores,
    arrays_digest,
    atomic_json,
    build_manifest,
    choose_depth_slab,
    payload_sha256,
    regularize_curve,
    score_candidate,
    selected_candidate,
)


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
DEFAULT_REAL_STACK = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl\tilted-sw10-cpl"
)
REAL_EXPECTED_FRAMES = 92
BURNED_GRID_ROOT = Path(r"D:\personal\macro\requests\30-calibration-grid")
DEFAULT_GRID_SW4 = BURNED_GRID_ROOT / "calibration-grid-1-sw4-cpl"
DEFAULT_GRID_SW10 = BURNED_GRID_ROOT / "calibration-grid-2-sw10-cpl"
GRID_ROWS = 8
GRID_COLS = 8
TILE_SIDE = 128
BLOCK_SIDE = 32


def frequency_mask(side: int, low: float, high: float) -> np.ndarray:
    fy = np.fft.fftfreq(side)[:, None]
    fx = np.fft.rfftfreq(side)[None, :]
    radius = np.hypot(fx, fy)
    return (radius >= low) & (radius < high)


ELECTION_BLOCK_MASK = frequency_mask(BLOCK_SIDE, 0.05, 0.12)
EVALUATION_BLOCK_MASK = frequency_mask(BLOCK_SIDE, 0.15, 0.25)
EVALUATION_TILE_MASK = frequency_mask(TILE_SIDE, 0.15, 0.25)
BLOCK_WINDOW = np.outer(
    tukey(BLOCK_SIDE, alpha=0.25, sym=True),
    tukey(BLOCK_SIDE, alpha=0.25, sym=True),
)
TILE_WINDOW = np.outer(
    tukey(TILE_SIDE, alpha=0.25, sym=True),
    tukey(TILE_SIDE, alpha=0.25, sym=True),
)


def normalized_fft(image: np.ndarray, window: np.ndarray) -> np.ndarray:
    values = np.asarray(image, dtype=np.float64)
    mean = float(np.mean(values))
    if not math.isfinite(mean) or mean <= 0.0:
        raise ValueError(f"non-positive tile mean {mean}")
    normalized = (values / mean - 1.0) * window
    return np.fft.rfft2(normalized)


def tile_features(tile: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(tile, dtype=np.float64)
    if values.shape != (TILE_SIDE, TILE_SIDE):
        raise ValueError(f"expected {TILE_SIDE}x{TILE_SIDE} tile, found {values.shape}")
    election_blocks = []
    evaluation_blocks = []
    for row in range(4):
        for col in range(4):
            block = values[
                row * BLOCK_SIDE : (row + 1) * BLOCK_SIDE,
                col * BLOCK_SIDE : (col + 1) * BLOCK_SIDE,
            ]
            spectrum = normalized_fft(block, BLOCK_WINDOW)
            election_blocks.append(spectrum[ELECTION_BLOCK_MASK])
            evaluation_blocks.append(spectrum[EVALUATION_BLOCK_MASK])
    full = normalized_fft(values, TILE_WINDOW)[EVALUATION_TILE_MASK]
    return (
        np.asarray(election_blocks, dtype=np.complex64),
        np.asarray(evaluation_blocks, dtype=np.complex64),
        np.asarray(full, dtype=np.complex64),
    )


def fixed_sites(height: int, width: int) -> tuple[list[str], np.ndarray]:
    y_edges = np.linspace(0.06 * height, 0.94 * height, GRID_ROWS + 1)
    x_edges = np.linspace(0.06 * width, 0.94 * width, GRID_COLS + 1)
    rows = []
    identifiers = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            center_y = 0.5 * (y_edges[row] + y_edges[row + 1])
            center_x = 0.5 * (x_edges[col] + x_edges[col + 1])
            y = int(math.floor((center_y - TILE_SIDE / 2) / TILE_SIDE) * TILE_SIDE)
            x = int(math.floor((center_x - TILE_SIDE / 2) / TILE_SIDE) * TILE_SIDE)
            y = min(max(0, y), height - TILE_SIDE)
            x = min(max(0, x), width - TILE_SIDE)
            y -= y % 2
            x -= x % 2
            rows.append((x, y))
            identifiers.append(f"r{row:02d}-c{col:02d}-x{x:04d}-y{y:04d}")
    coordinates = np.asarray(rows, dtype=np.int64)
    if len({tuple(row) for row in coordinates.tolist()}) != len(coordinates):
        raise ValueError("fixed site construction produced duplicate tiles")
    for left in range(len(coordinates)):
        x0, y0 = coordinates[left]
        for right in range(left + 1, len(coordinates)):
            x1, y1 = coordinates[right]
            overlap = not (
                x0 + TILE_SIDE <= x1
                or x1 + TILE_SIDE <= x0
                or y0 + TILE_SIDE <= y1
                or y1 + TILE_SIDE <= y0
            )
            if overlap:
                raise ValueError(
                    f"fixed sites {identifiers[left]} and {identifiers[right]} overlap"
                )
    return identifiers, coordinates


def green_proxy_tiles(
    visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
    site_xy: np.ndarray,
) -> np.ndarray:
    """Build 128-native-pixel green proxies from the two Bayer green phases."""

    greens = [
        (row, col, int(raw_pattern[row, col]))
        for row in range(2)
        for col in range(2)
        if int(raw_pattern[row, col]) in (1, 3)
    ]
    if len(greens) != 2:
        raise ValueError(f"expected two Bayer green phases, found {greens}")
    tiles = []
    for x, y in site_xy:
        crop = visible[y : y + TILE_SIDE, x : x + TILE_SIDE]
        phases = []
        for row, col, color in greens:
            black = float(black_levels[color])
            scale = float(white_level) - black
            if scale <= 0.0:
                raise ValueError("RAW white level does not exceed black")
            phase = crop[row::2, col::2].astype(np.float32, copy=True)
            phases.append((phase - black) / scale)
        green_half = 0.5 * (phases[0] + phases[1])
        tile = cv2.resize(
            green_half,
            (TILE_SIDE, TILE_SIDE),
            interpolation=cv2.INTER_LINEAR,
        )
        tiles.append(np.asarray(tile, dtype=np.float32))
    return np.asarray(tiles, dtype=np.float32)


def real_stack_files(path: Path, expected_frames: int) -> list[Path]:
    files = sorted(
        (
            entry
            for entry in path.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".arw"
        ),
        key=lambda entry: entry.name,
    )
    if len(files) != expected_frames:
        raise ValueError(
            f"{path}: found {len(files)} ARWs, expected {expected_frames}"
        )
    return files


def extract_real_prepared(
    stack: Path, output: Path, *, expected_frames: int
) -> dict[str, Any]:
    files = real_stack_files(stack, expected_frames)
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    source_eval: np.ndarray | None = None
    election_cross = np.full(
        (GRID_ROWS * GRID_COLS, len(files), BLOCK_COUNT),
        np.nan,
        dtype=np.float64,
    )
    evaluation_cross = np.full_like(election_cross, np.nan)
    site_ids: list[str] | None = None
    site_xy: np.ndarray | None = None
    geometry: dict[str, Any] | None = None
    prior_election: np.ndarray | None = None
    prior_evaluation: np.ndarray | None = None
    current_election: np.ndarray | None = None
    current_evaluation: np.ndarray | None = None

    for frame_index, path in enumerate(files):
        with rawpy.imread(str(path)) as raw:
            visible = raw.raw_image_visible
            frame_geometry = {
                "height": int(visible.shape[0]),
                "width": int(visible.shape[1]),
                "raw_pattern": raw.raw_pattern.tolist(),
                "black_levels": [int(value) for value in raw.black_level_per_channel],
                "white_level": int(raw.white_level),
            }
            if geometry is None:
                geometry = frame_geometry
                site_ids, site_xy = fixed_sites(
                    frame_geometry["height"], frame_geometry["width"]
                )
                source_eval = np.empty(
                    (
                        len(site_ids),
                        len(files),
                        int(np.count_nonzero(EVALUATION_TILE_MASK)),
                    ),
                    dtype=np.complex64,
                )
            elif frame_geometry != geometry:
                raise ValueError(f"RAW geometry changed at {path.name}")
            assert site_xy is not None
            tiles = green_proxy_tiles(
                visible,
                raw.raw_pattern,
                list(raw.black_level_per_channel),
                int(raw.white_level),
                site_xy,
            )

        frame_election = []
        frame_evaluation = []
        frame_full = []
        for tile in tiles:
            block_election, block_evaluation, full = tile_features(tile)
            frame_election.append(block_election)
            frame_evaluation.append(block_evaluation)
            frame_full.append(full)
        next_election = np.asarray(frame_election, dtype=np.complex64)
        next_evaluation = np.asarray(frame_evaluation, dtype=np.complex64)
        assert source_eval is not None
        source_eval[:, frame_index, :] = np.asarray(frame_full, dtype=np.complex64)

        if frame_index >= 2:
            assert prior_election is not None
            assert prior_evaluation is not None
            assert current_election is not None
            assert current_evaluation is not None
            center = frame_index - 1
            election_cross[:, center, :] = 0.5 * np.real(
                np.sum(current_election * np.conj(prior_election), axis=2)
                + np.sum(current_election * np.conj(next_election), axis=2)
            )
            evaluation_cross[:, center, :] = 0.5 * np.real(
                np.sum(current_evaluation * np.conj(prior_evaluation), axis=2)
                + np.sum(current_evaluation * np.conj(next_evaluation), axis=2)
            )
        prior_election, current_election = current_election, next_election
        prior_evaluation, current_evaluation = current_evaluation, next_evaluation
        if (frame_index + 1) % 20 == 0 or frame_index + 1 == len(files):
            print(
                f"real-extract frames={frame_index + 1}/{len(files)}",
                flush=True,
            )

    assert geometry is not None
    assert site_ids is not None
    assert site_xy is not None
    assert source_eval is not None
    np.savez(
        output,
        election_crosspower=election_cross,
        evaluation_crosspower=evaluation_cross,
        site_ids=np.asarray(site_ids),
        site_xy=site_xy,
        source_eval_real=source_eval.real.astype(np.float32),
        source_eval_imag=source_eval.imag.astype(np.float32),
        reference_height=np.asarray(geometry["height"], dtype=np.int64),
        reference_width=np.asarray(geometry["width"], dtype=np.int64),
    )
    inventory = {
        "elapsed_seconds": time.perf_counter() - started,
        "first_file": files[0].name,
        "frames": len(files),
        "geometry": geometry,
        "last_file": files[-1].name,
        "path": str(stack),
        "prepared_bytes": output.stat().st_size,
        "prepared_path": str(output),
        "site_count": len(site_ids),
        "total_source_bytes": int(sum(path.stat().st_size for path in files)),
    }
    atomic_json(output.with_suffix(".inventory.json"), inventory)
    return inventory


def load_prepared(path: Path) -> dict[str, Any]:
    with np.load(path, allow_pickle=False) as archive:
        return {name: archive[name] for name in archive.files}


def prepared_digest(prepared: dict[str, Any]) -> str:
    source = prepared["source_eval_real"] + 1j * prepared["source_eval_imag"]
    return arrays_digest(
        (
            prepared["election_crosspower"],
            prepared["evaluation_crosspower"],
            prepared["site_xy"],
            source,
        )
    )


def point_window_bound(
    prepared: dict[str, Any], window_nodes: int
) -> dict[str, Any]:
    """Best possible point-eligibility count over all contiguous windows.

    Bootstrap can reject a point-qualified site but cannot admit a site whose
    point ratio is below 2.0, so this is an upper bound on final eligibility.
    """

    election = np.asarray(prepared["election_crosspower"], dtype=np.float64)
    evaluation = np.asarray(prepared["evaluation_crosspower"], dtype=np.float64)
    if window_nodes < 8 or window_nodes > election.shape[1]:
        raise ValueError(
            f"invalid window {window_nodes} for {election.shape[1]} nodes"
        )
    rows = []
    local_nodes = np.arange(window_nodes)
    candidates = np.arange(3, window_nodes - 3)
    for start in range(election.shape[1] - window_nodes + 1):
        stop = start + window_nodes
        election_curve = np.mean(election[:, start:stop, :], axis=2)
        evaluation_curve = np.mean(evaluation[:, start:stop, :], axis=2)
        regularized = regularize_curve(election_curve)
        best = candidates[np.argmax(regularized[:, candidates], axis=1)]
        ratios = []
        for site, best_node in enumerate(best):
            far = (
                (np.abs(local_nodes - best_node) >= FAR_DISTANCE)
                & (local_nodes >= 1)
                & (local_nodes < window_nodes - 1)
            )
            best_signal = max(float(evaluation_curve[site, best_node]), 0.0)
            far_signal = max(float(np.max(evaluation_curve[site, far])), 0.0)
            if best_signal <= 0.0:
                ratio = 0.0
            elif far_signal <= 0.0:
                ratio = math.inf
            else:
                ratio = best_signal / far_signal
            ratios.append(ratio)
        ratio_array = np.asarray(ratios, dtype=np.float64)
        rows.append(
            {
                "end_node_inclusive": stop - 1,
                "maximum_point_ratio": float(np.max(ratio_array)),
                "median_point_ratio": float(np.median(ratio_array)),
                "point_eligible_upper_bound": int(
                    np.count_nonzero(ratio_array >= 2.0)
                ),
                "start_node": start,
            }
        )
    return max(
        rows,
        key=lambda row: (
            row["point_eligible_upper_bound"],
            -row["start_node"],
        ),
    ) | {
        "windows_evaluated": len(rows),
        "window_nodes": window_nodes,
    }


def sliced_prepared(
    prepared: dict[str, Any], start: int, length: int
) -> dict[str, Any]:
    stop = start + length
    result = dict(prepared)
    result["election_crosspower"] = np.asarray(
        prepared["election_crosspower"][:, start:stop, :], dtype=np.float64
    ).copy()
    result["evaluation_crosspower"] = np.asarray(
        prepared["evaluation_crosspower"][:, start:stop, :], dtype=np.float64
    ).copy()
    result["source_eval_real"] = prepared["source_eval_real"][:, start:stop, :]
    result["source_eval_imag"] = prepared["source_eval_imag"][:, start:stop, :]
    result["election_crosspower"][:, (0, -1), :] = np.nan
    result["evaluation_crosspower"][:, (0, -1), :] = np.nan
    return result


def eligibility_summary(
    prepared: dict[str, Any],
    *,
    capture_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = build_manifest(
        prepared["election_crosspower"],
        prepared["evaluation_crosspower"],
        [str(value) for value in prepared["site_ids"].tolist()],
        prepared["site_xy"],
        input_digest=prepared_digest(prepared),
        capture_id=capture_id,
    )

    def numeric(value: Any) -> float:
        return math.inf if value == "inf" else float(value)

    point = np.asarray(
        [numeric(site["point_ratio"]) for site in manifest["sites"]]
    )
    lcb = np.asarray(
        [numeric(site["ratio_lcb95"]) for site in manifest["sites"]]
    )
    eligible_depths = [
        int(site["best_node"]) for site in manifest["sites"] if site["eligible"]
    ]
    return {
        "at_least_133_effective_wilson_minimum": manifest["eligible_count"] >= 133,
        "at_least_50": manifest["eligible_count"] >= 50,
        "eligible_count": manifest["eligible_count"],
        "eligible_unique_depths": len(set(eligible_depths)),
        "lcb_at_least_1_5": int(np.count_nonzero(lcb >= 1.5)),
        "lcb_maximum": float(np.max(lcb)),
        "lcb_median": float(np.median(lcb)),
        "manifest_sha256": manifest["manifest_sha256"],
        "point_at_least_2": int(np.count_nonzero(point >= 2.0)),
        "point_maximum": float(np.max(point)),
        "point_median": float(np.median(point)),
        "site_count": manifest["site_count"],
    }, manifest


def synthetic_prepared(
    *,
    site_count: int = 160,
    node_count: int = 31,
    coefficient_count: int = 96,
) -> dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(1512026))
    depths = np.arange(5, 26, dtype=np.int64)
    assigned = np.resize(depths, site_count)
    rng.shuffle(assigned)
    rows = int(math.ceil(site_count / 16))
    site_xy = np.asarray(
        [(128 * (index % 16), 128 * (index // 16)) for index in range(site_count)],
        dtype=np.int64,
    )
    site_ids = np.asarray([f"synthetic-{index:04d}" for index in range(site_count)])
    election = np.full((site_count, node_count, BLOCK_COUNT), np.nan, dtype=np.float64)
    evaluation = np.full_like(election, np.nan)
    sources = np.empty(
        (site_count, node_count, coefficient_count), dtype=np.complex64
    )

    nodes = np.arange(node_count, dtype=np.float64)
    for site, best in enumerate(assigned):
        election_amplitude = np.exp(-0.5 * ((nodes - best) / 1.25) ** 2)
        evaluation_amplitude = np.exp(-0.5 * ((nodes - best) / 0.85) ** 2)
        block_scale = np.exp(rng.normal(0.0, 0.025, size=BLOCK_COUNT))
        block_jitter = rng.normal(
            0.0, 0.002, size=(node_count, BLOCK_COUNT)
        )
        for node in range(1, node_count - 1):
            election[site, node] = (
                election_amplitude[node]
                * 0.5
                * (
                    election_amplitude[node - 1]
                    + election_amplitude[node + 1]
                )
                * block_scale
                + block_jitter[node]
            )
            evaluation[site, node] = (
                evaluation_amplitude[node]
                * 0.5
                * (
                    evaluation_amplitude[node - 1]
                    + evaluation_amplitude[node + 1]
                )
                * block_scale
                + block_jitter[node]
            )

        shared = rng.normal(size=coefficient_count) + 1j * rng.normal(
            size=coefficient_count
        )
        shared /= np.linalg.norm(shared)
        for node in range(node_count):
            nuisance = rng.normal(size=coefficient_count) + 1j * rng.normal(
                size=coefficient_count
            )
            nuisance -= shared * np.vdot(shared, nuisance)
            nuisance /= np.linalg.norm(nuisance)
            amplitude = math.exp(-0.5 * ((node - best) / 0.70) ** 2)
            sources[site, node] = amplitude * shared + 0.12 * nuisance

    return {
        "election_crosspower": election,
        "evaluation_crosspower": evaluation,
        "reference_height": np.asarray(rows * TILE_SIDE, dtype=np.int64),
        "reference_width": np.asarray(16 * TILE_SIDE, dtype=np.int64),
        "site_ids": site_ids,
        "site_xy": site_xy,
        "source_eval_imag": sources.imag.astype(np.float32),
        "source_eval_real": sources.real.astype(np.float32),
    }


def noise_null_prepared(
    *, site_count: int = 64, node_count: int = 31
) -> dict[str, Any]:
    rng = np.random.Generator(np.random.PCG64(1519001))
    # Independent centered cross-power has no reproducible source component.
    election = rng.normal(
        0.0, 1.0, size=(site_count, node_count, BLOCK_COUNT)
    )
    evaluation = rng.normal(
        0.0, 1.0, size=(site_count, node_count, BLOCK_COUNT)
    )
    election[:, (0, -1)] = np.nan
    evaluation[:, (0, -1)] = np.nan
    return {
        "election_crosspower": election,
        "evaluation_crosspower": evaluation,
        "site_ids": np.asarray(
            [f"noise-null-{index:04d}" for index in range(site_count)]
        ),
        "site_xy": np.asarray(
            [(128 * (index % 8), 128 * (index // 8)) for index in range(site_count)],
            dtype=np.int64,
        ),
    }


def summarize_score(score: dict[str, Any]) -> dict[str, Any]:
    rows = score["site_rows"]
    return {
        key: value
        for key, value in score.items()
        if key != "site_rows"
    } | {
        "rho_best": {
            "minimum": min((row["rho_best"] for row in rows), default=None),
            "median": (
                float(np.median([row["rho_best"] for row in rows])) if rows else None
            ),
        },
        "rho_far": {
            "maximum": max((row["rho_far"] for row in rows), default=None),
            "median": (
                float(np.median([row["rho_far"] for row in rows])) if rows else None
            ),
        },
        "focus_margin": {
            "minimum": min((row["focus_margin"] for row in rows), default=None),
            "median": (
                float(np.median([row["focus_margin"] for row in rows]))
                if rows
                else None
            ),
        },
    }


def slab_overlap(score: dict[str, Any], slab: dict[str, Any]) -> float:
    interval = score["run"].get("interval")
    if interval is None:
        return 0.0
    left = max(float(interval[0]), float(slab["covered_depth_interval"][0]))
    right = min(float(interval[1]), float(slab["covered_depth_interval"][1]))
    return max(0.0, right - left)


def commission_prepared(
    prepared: dict[str, Any],
    *,
    capture_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sources = prepared["source_eval_real"] + 1j * prepared["source_eval_imag"]
    site_ids = [str(value) for value in prepared["site_ids"].tolist()]
    digest = prepared_digest(prepared)
    manifest = build_manifest(
        prepared["election_crosspower"],
        prepared["evaluation_crosspower"],
        site_ids,
        prepared["site_xy"],
        input_digest=digest,
        capture_id=capture_id,
    )
    reference_valid = np.ones((100, 100), dtype=bool)
    full_valid = reference_valid.copy()

    healthy_candidate, healthy_nodes = selected_candidate(
        manifest, sources, mode="best"
    )
    healthy = score_candidate(
        manifest,
        sources,
        healthy_candidate,
        reference_valid,
        full_valid,
        candidate_id=f"{capture_id}-complete-oracle",
    )

    slab = choose_depth_slab(manifest)
    deleted = set(
        range(int(slab["start_node"]), int(slab["end_node_inclusive"]) + 1)
    )
    defect_candidate, defect_nodes = selected_candidate(
        manifest,
        sources,
        mode="best",
        deleted_nodes=deleted,
    )
    defect = score_candidate(
        manifest,
        sources,
        defect_candidate,
        reference_valid,
        full_valid,
        candidate_id=f"{capture_id}-deleted-slab",
    )

    far_candidate, far_nodes = selected_candidate(manifest, sources, mode="far")
    far = score_candidate(
        manifest,
        sources,
        far_candidate,
        reference_valid,
        full_valid,
        candidate_id=f"{capture_id}-far-only",
    )

    cropped_valid = full_valid.copy()
    cropped_valid[:2] = False
    crop = score_candidate(
        manifest,
        sources,
        healthy_candidate,
        reference_valid,
        cropped_valid,
        candidate_id=f"{capture_id}-two-percent-crop",
    )

    eligible = np.asarray(
        [bool(site["eligible"]) for site in manifest["sites"]], dtype=bool
    )
    selected_changed = int(
        np.count_nonzero((defect_nodes != healthy_nodes) & eligible)
    )
    eligible_in_slab = int(
        sum(
            site["eligible"] and int(site["best_node"]) in deleted
            for site in manifest["sites"]
        )
    )
    permutation = np.random.Generator(np.random.PCG64(151777)).permutation(
        len(manifest["sites"])
    )
    permuted_coordinates = prepared["site_xy"][permutation]
    coordinate_digest = arrays_digest((permuted_coordinates,))
    permuted_manifest = copy.deepcopy(manifest)
    for index, (x, y) in enumerate(permuted_coordinates):
        permuted_manifest["sites"][index]["x"] = int(x)
        permuted_manifest["sites"][index]["y"] = int(y)
    unsigned_permuted = {
        key: value
        for key, value in permuted_manifest.items()
        if key != "manifest_sha256"
    }
    permuted_manifest["manifest_sha256"] = payload_sha256(unsigned_permuted)
    permuted_score = score_candidate(
        permuted_manifest,
        sources,
        healthy_candidate,
        reference_valid,
        full_valid,
        candidate_id=f"{capture_id}-nonplanar-coordinate-permutation",
    )
    topology_identical = (
        json.dumps(healthy["run"], sort_keys=True)
        == json.dumps(permuted_score["run"], sort_keys=True)
    )

    result = {
        "capture_id": capture_id,
        "input_digest": digest,
        "manifest": {
            "eligible_count": manifest["eligible_count"],
            "manifest_sha256": manifest["manifest_sha256"],
            "node_count": manifest["node_count"],
            "site_count": manifest["site_count"],
        },
        "healthy": summarize_score(healthy),
        "defect": summarize_score(defect),
        "far_baseline": summarize_score(far),
        "crop_plant": summarize_score(crop),
        "slab": slab,
        "response": {
            "coverage_drop_percentage_points": 100.0
            * (float(healthy["coverage"]) - float(defect["coverage"])),
            "defect_longest_run_increase_nodes": float(
                defect["run"]["length_nodes"] - healthy["run"]["length_nodes"]
            ),
            "defect_longest_run_increase_fraction": float(
                defect["run"]["fraction"] - healthy["run"]["fraction"]
            ),
            "eligible_sites_in_slab": eligible_in_slab,
            "improvement_coverage_percentage_points": 100.0
            * (float(healthy["coverage"]) - float(far["coverage"])),
            "improvement_failed_sites": int(
                far["failed_sites"] - healthy["failed_sites"]
            ),
            "selected_nodes_changed": selected_changed,
            "slab_longest_run_overlap_nodes": slab_overlap(defect, slab),
        },
        "topology_control": {
            "coordinate_permutation_digest": coordinate_digest,
            "run_byte_identical": topology_identical,
        },
        "selected_nodes": {
            "defect": defect_nodes.tolist(),
            "far": far_nodes.tolist(),
            "healthy": healthy_nodes.tolist(),
        },
    }
    full = {
        "manifest": manifest,
        "scores": {
            "crop": crop,
            "defect": defect,
            "far": far,
            "healthy": healthy,
        },
    }
    return result, full


def criteria(result: dict[str, Any], *, require_wilson: bool) -> dict[str, bool]:
    healthy = result["healthy"]
    crop = result["crop_plant"]
    response = result["response"]
    checks = {
        "at_least_50_eligible": result["manifest"]["eligible_count"] >= 50,
        "healthy_zero_failed": healthy["failed_sites"] == 0,
        "healthy_zero_run": healthy["run"]["fraction"] == 0.0,
        "healthy_full_fov": healthy["retained_fov"] == 1.0,
        "defect_drop_at_least_5pp": (
            response["coverage_drop_percentage_points"] >= 5.0
        ),
        "defect_run_increased": (
            response["defect_longest_run_increase_fraction"] > 0.0
        ),
        "defect_run_overlaps_slab": (
            response["slab_longest_run_overlap_nodes"] > 0.0
        ),
        "improvement_raises_coverage": (
            response["improvement_coverage_percentage_points"] > 0.0
        ),
        "crop_reads_98_percent": abs(float(crop["retained_fov"]) - 0.98) < 1.0e-12,
        "crop_fails_fov": not crop["fov_pass"],
        "topology_invariant": result["topology_control"]["run_byte_identical"],
    }
    if require_wilson:
        checks["healthy_wilson_pass"] = bool(healthy["wilson_pass"])
    return checks


def ensure_prepared(
    stack: Path,
    cache: Path,
    *,
    expected_frames: int,
    refresh: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    inventory_path = cache.with_suffix(".inventory.json")
    if refresh and cache.exists():
        cache.unlink()
    if refresh and inventory_path.exists():
        inventory_path.unlink()
    if not cache.exists():
        inventory = extract_real_prepared(
            stack,
            cache,
            expected_frames=expected_frames,
        )
    else:
        real_stack_files(stack, expected_frames)
        inventory = json.loads(inventory_path.read_text(encoding="ascii"))
        inventory["cache_reused"] = True
    return load_prepared(cache), inventory


def compact_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        key: inventory[key]
        for key in (
            "first_file",
            "frames",
            "geometry",
            "last_file",
            "path",
            "site_count",
            "total_source_bytes",
        )
    }


def run(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    synthetic = synthetic_prepared()
    synthetic_result, synthetic_full = commission_prepared(
        synthetic, capture_id="synthetic-nonplanar"
    )
    atomic_json(OUT / "synthetic-full.json", synthetic_full)
    pooled_inputs = []
    for capture_index in range(4):
        row = copy.deepcopy(synthetic_full["scores"]["healthy"])
        row["capture_id"] = f"synthetic-capture-{capture_index}"
        row["candidate_id"] = f"synthetic-healthy-{capture_index}"
        pooled_inputs.append(row)
    synthetic_pooled = aggregate_scores(pooled_inputs)

    noise = noise_null_prepared()
    noise_manifest = build_manifest(
        noise["election_crosspower"],
        noise["evaluation_crosspower"],
        [str(value) for value in noise["site_ids"].tolist()],
        noise["site_xy"],
        input_digest=arrays_digest(
            (
                noise["election_crosspower"],
                noise["evaluation_crosspower"],
                noise["site_xy"],
            )
        ),
        capture_id="synthetic-noise-null",
    )
    noise_result = {
        "eligible_count": noise_manifest["eligible_count"],
        "manifest_sha256": noise_manifest["manifest_sha256"],
        "site_count": noise_manifest["site_count"],
        "stayed_green": noise_manifest["eligible_count"] < 50,
    }

    real_prepared, real_inventory = ensure_prepared(
        Path(args.real_stack),
        OUT / "tilted-sw10-prepared.npz",
        expected_frames=REAL_EXPECTED_FRAMES,
        refresh=args.refresh,
    )
    real_result, real_full = commission_prepared(
        real_prepared, capture_id="development-tilted-sw10"
    )
    atomic_json(OUT / "real-full.json", real_full)

    best_sw10_window = point_window_bound(real_prepared, 27)
    sw10_window = sliced_prepared(
        real_prepared,
        int(best_sw10_window["start_node"]),
        int(best_sw10_window["window_nodes"]),
    )
    best_sw10_exact, best_sw10_manifest = eligibility_summary(
        sw10_window,
        capture_id="development-tilted-sw10-best-27-window",
    )
    atomic_json(OUT / "tilted-sw10-best-window-manifest.json", best_sw10_manifest)

    grid_sw4, grid_sw4_inventory = ensure_prepared(
        Path(args.grid_sw4),
        OUT / "burned-grid-sw4-prepared.npz",
        expected_frames=55,
        refresh=args.refresh,
    )
    grid_sw4_eligibility, grid_sw4_manifest = eligibility_summary(
        grid_sw4,
        capture_id="burned-grid-sw4-exact-55",
    )
    atomic_json(OUT / "burned-grid-sw4-manifest.json", grid_sw4_manifest)

    grid_sw10, grid_sw10_inventory = ensure_prepared(
        Path(args.grid_sw10),
        OUT / "burned-grid-sw10-prepared.npz",
        expected_frames=27,
        refresh=args.refresh,
    )
    grid_sw10_eligibility, grid_sw10_manifest = eligibility_summary(
        grid_sw10,
        capture_id="burned-grid-sw10-exact-27",
    )
    atomic_json(OUT / "burned-grid-sw10-manifest.json", grid_sw10_manifest)

    capture_sufficiency = {
        "burned_grid_sw10_exact_27": grid_sw10_eligibility,
        "burned_grid_sw4_exact_55": grid_sw4_eligibility,
        "development_tilted_sw10_best_27": {
            **best_sw10_window,
            "bootstrap_eligible_count": best_sw10_exact["eligible_count"],
            "bootstrap_lcb_at_least_1_5": best_sw10_exact["lcb_at_least_1_5"],
            "bootstrap_manifest_sha256": best_sw10_exact["manifest_sha256"],
        },
        "final_patch_exact_rehearsal_present": False,
        "minimum_all_success_sites_for_wilson_98": 133,
        "planned_capture_demonstrated_sufficient": False,
        "reason": (
            "No exact converter-on rehearsal exists on the final patch, and "
            "none of the measured exact-length development arms reaches even "
            "the nominal 50 eligible sites on the frozen 64-site lattice. "
            "The effective all-success Wilson minimum is 133 sites."
        ),
    }

    synthetic_checks = criteria(synthetic_result, require_wilson=True)
    real_checks = criteria(real_result, require_wilson=False)
    all_checks = {
        "capture_exact_development_arms_at_effective_minimum": bool(
            grid_sw4_eligibility["at_least_133_effective_wilson_minimum"]
            and grid_sw10_eligibility["at_least_133_effective_wilson_minimum"]
        ),
        "noise_null_not_eligible": bool(noise_result["stayed_green"]),
        "synthetic_pooled_wilson_pass": bool(
            synthetic_pooled["pooled"]["rate_pass"]
        ),
        **{f"synthetic_{key}": value for key, value in synthetic_checks.items()},
        **{f"real_{key}": value for key, value in real_checks.items()},
    }
    summary = {
        "all_commissioned": all(all_checks.values()),
        "checks": all_checks,
        "definitions_sha256": DEFINITIONS_SHA256,
        "environment": {
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "platform": platform.platform(),
            "python": sys.version,
            "rawpy": rawpy.__version__,
            "scipy": __import__("scipy").__version__,
            "thread_caps": {
                key: os.environ[key]
                for key in (
                    "OMP_NUM_THREADS",
                    "OPENBLAS_NUM_THREADS",
                    "MKL_NUM_THREADS",
                    "NUMEXPR_NUM_THREADS",
                )
            },
        },
        "capture_sufficiency": capture_sufficiency,
        "development_inventories": {
            "burned_grid_sw10": compact_inventory(grid_sw10_inventory),
            "burned_grid_sw4": compact_inventory(grid_sw4_inventory),
            "tilted_sw10": compact_inventory(real_inventory),
        },
        "noise_null": noise_result,
        "protocol": PROTOCOL,
        "real": real_result,
        "reproduction": [
            "python experiments/M151-m5-checker/checker.py self-test",
            (
                "python experiments/M151-m5-checker/commission.py "
                "--refresh"
            ),
            "python experiments/M151-m5-checker/test_checker.py",
        ],
        "synthetic": synthetic_result,
        "synthetic_pooled_wilson": synthetic_pooled,
    }
    atomic_json(LANE / "commission-results.json", summary)
    print(
        "synthetic "
        f"eligible={synthetic_result['manifest']['eligible_count']} "
        f"coverage={synthetic_result['healthy']['coverage']:.6f}->"
        f"{synthetic_result['defect']['coverage']:.6f} "
        f"run={synthetic_result['healthy']['run']['fraction']:.6f}->"
        f"{synthetic_result['defect']['run']['fraction']:.6f}"
    )
    print(
        "real "
        f"eligible={real_result['manifest']['eligible_count']} "
        f"coverage={real_result['healthy']['coverage']:.6f}->"
        f"{real_result['defect']['coverage']:.6f} "
        f"run={real_result['healthy']['run']['fraction']:.6f}->"
        f"{real_result['defect']['run']['fraction']:.6f}"
    )
    print(
        "capture-eligibility "
        f"grid-sw4-55={grid_sw4_eligibility['eligible_count']}/64 "
        f"grid-sw10-27={grid_sw10_eligibility['eligible_count']}/64 "
        f"tilted-sw10-best27={best_sw10_exact['eligible_count']}/64"
    )
    print(
        f"noise-null eligible={noise_result['eligible_count']} "
        f"all-commissioned={summary['all_commissioned']}"
    )
    return 0 if summary["all_commissioned"] else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "--real-stack",
        default=str(DEFAULT_REAL_STACK),
        help="explicitly development-only tilted-sw10 directory",
    )
    result.add_argument(
        "--grid-sw4",
        default=str(DEFAULT_GRID_SW4),
        help="explicitly burned 55-frame calibration-grid sw4 directory",
    )
    result.add_argument(
        "--grid-sw10",
        default=str(DEFAULT_GRID_SW10),
        help="explicitly burned 27-frame calibration-grid sw10 directory",
    )
    result.add_argument(
        "--refresh",
        action="store_true",
        help="discard only this lane's prepared cache and reread development RAWs",
    )
    return result


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
