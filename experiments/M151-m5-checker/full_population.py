"""Full 128x128 candidate-tile census for the M151 capture ruling.

This lifts the earlier fixed 8x8 commissioning sample to every complete tile
in rawpy's RAW-visible active rectangle.  It computes only input eligibility:
no stacker or candidate output is opened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Any

# Keep the census serial while M139 owns the host timing window.
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

from checker import (  # noqa: E402
    BLOCK_COUNT,
    FAR_DISTANCE,
    POINT_RATIO_MIN,
    atomic_json,
    arrays_digest,
    build_manifest,
    regularize_curve,
    wilson_lower,
)
from commission import (  # noqa: E402
    BLOCK_SIDE,
    BLOCK_WINDOW,
    DEFAULT_GRID_SW10,
    DEFAULT_GRID_SW4,
    DEFAULT_REAL_STACK,
    ELECTION_BLOCK_MASK,
    EVALUATION_BLOCK_MASK,
    TILE_SIDE,
    real_stack_files,
)


LANE = Path(__file__).resolve().parent
OUT = LANE / "out"
RESULT = LANE / "full-population-results.json"
CHUNK_SITES = 64
EFFECTIVE_WILSON_MINIMUM = 133


def full_sites(height: int, width: int) -> tuple[list[str], np.ndarray, dict[str, int]]:
    rows = height // TILE_SIDE
    columns = width // TILE_SIDE
    if rows == 0 or columns == 0:
        raise ValueError(
            f"{width}x{height} active area cannot contain a {TILE_SIDE}px tile"
        )
    coordinates = np.asarray(
        [
            (column * TILE_SIDE, row * TILE_SIDE)
            for row in range(rows)
            for column in range(columns)
        ],
        dtype=np.int64,
    )
    identifiers = np.asarray(
        [
            f"full-r{row:02d}-c{column:02d}-x{column * TILE_SIDE:04d}"
            f"-y{row * TILE_SIDE:04d}"
            for row in range(rows)
            for column in range(columns)
        ]
    )
    geometry = {
        "candidate_columns": columns,
        "candidate_rows": rows,
        "candidate_tiles": rows * columns,
        "height": height,
        "right_remainder_px": width - columns * TILE_SIDE,
        "bottom_remainder_px": height - rows * TILE_SIDE,
        "tile_side_px": TILE_SIDE,
        "width": width,
    }
    return identifiers.tolist(), coordinates, geometry


def green_half_tiles(
    visible: np.ndarray,
    raw_pattern: np.ndarray,
    black_levels: list[int],
    white_level: int,
    rows: int,
    columns: int,
) -> np.ndarray:
    used_height = rows * TILE_SIDE
    used_width = columns * TILE_SIDE
    greens = [
        (row, column, int(raw_pattern[row, column]))
        for row in range(2)
        for column in range(2)
        if int(raw_pattern[row, column]) in (1, 3)
    ]
    if len(greens) != 2:
        raise ValueError(f"expected two Bayer green phases, found {greens}")
    phases = []
    for row, column, color in greens:
        black = float(black_levels[color])
        scale = float(white_level) - black
        if scale <= 0.0:
            raise ValueError("RAW white level does not exceed black")
        plane = visible[row:used_height:2, column:used_width:2]
        phases.append((plane.astype(np.float32, copy=True) - black) / scale)
    half = 0.5 * (phases[0] + phases[1])
    half_side = TILE_SIDE // 2
    return (
        half.reshape(rows, half_side, columns, half_side)
        .transpose(0, 2, 1, 3)
        .reshape(rows * columns, half_side, half_side)
    )


def block_spectra(half_tiles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    site_count = half_tiles.shape[0]
    election = np.empty(
        (
            site_count,
            BLOCK_COUNT,
            int(np.count_nonzero(ELECTION_BLOCK_MASK)),
        ),
        dtype=np.complex64,
    )
    evaluation = np.empty(
        (
            site_count,
            BLOCK_COUNT,
            int(np.count_nonzero(EVALUATION_BLOCK_MASK)),
        ),
        dtype=np.complex64,
    )
    for start in range(0, site_count, CHUNK_SITES):
        stop = min(start + CHUNK_SITES, site_count)
        channels = np.moveaxis(half_tiles[start:stop], 0, -1)
        resized = cv2.resize(
            channels,
            (TILE_SIDE, TILE_SIDE),
            interpolation=cv2.INTER_LINEAR,
        )
        if resized.ndim == 2:
            resized = resized[:, :, None]
        tiles = np.moveaxis(resized, -1, 0).astype(np.float64)
        count = tiles.shape[0]
        if count != stop - start:
            raise ValueError(
                f"batched resize returned {count} tiles, expected {stop - start}"
            )
        blocks = (
            tiles.reshape(count, 4, BLOCK_SIDE, 4, BLOCK_SIDE)
            .transpose(0, 1, 3, 2, 4)
            .reshape(count, BLOCK_COUNT, BLOCK_SIDE, BLOCK_SIDE)
        )
        means = np.mean(blocks, axis=(-2, -1))
        if np.any(~np.isfinite(means)) or np.any(means <= 0.0):
            raise ValueError("non-positive block mean in full census")
        normalized = (
            blocks / means[:, :, None, None] - 1.0
        ) * BLOCK_WINDOW[None, None, :, :]
        spectra = np.fft.rfft2(normalized, axes=(-2, -1))
        election[start:stop] = spectra[:, :, ELECTION_BLOCK_MASK]
        evaluation[start:stop] = spectra[:, :, EVALUATION_BLOCK_MASK]
    return election, evaluation


def extract_crosspower(
    stack: Path,
    output: Path,
    *,
    expected_frames: int,
) -> dict[str, Any]:
    files = real_stack_files(stack, expected_frames)
    started = time.perf_counter()
    election_cross: np.ndarray | None = None
    evaluation_cross: np.ndarray | None = None
    site_ids: list[str] | None = None
    site_xy: np.ndarray | None = None
    geometry: dict[str, Any] | None = None
    tile_geometry: dict[str, int] | None = None
    previous_election: np.ndarray | None = None
    previous_evaluation: np.ndarray | None = None
    current_election: np.ndarray | None = None
    current_evaluation: np.ndarray | None = None

    for frame_index, path in enumerate(files):
        with rawpy.imread(str(path)) as raw:
            height, width = map(int, raw.raw_image_visible.shape)
            frame_geometry = {
                "black_levels": [
                    int(value) for value in raw.black_level_per_channel
                ],
                "height": height,
                "raw_pattern": raw.raw_pattern.tolist(),
                "white_level": int(raw.white_level),
                "width": width,
            }
            if geometry is None:
                geometry = frame_geometry
                site_ids, site_xy, tile_geometry = full_sites(height, width)
                election_cross = np.full(
                    (len(site_ids), len(files), BLOCK_COUNT),
                    np.nan,
                    dtype=np.float64,
                )
                evaluation_cross = np.full_like(election_cross, np.nan)
            elif geometry != frame_geometry:
                raise ValueError(f"RAW geometry changed at {path.name}")
            assert site_ids is not None
            half_tiles = green_half_tiles(
                raw.raw_image_visible,
                raw.raw_pattern,
                list(raw.black_level_per_channel),
                int(raw.white_level),
                tile_geometry["candidate_rows"],
                tile_geometry["candidate_columns"],
            )

        next_election, next_evaluation = block_spectra(half_tiles)
        if frame_index >= 2:
            assert election_cross is not None
            assert evaluation_cross is not None
            assert previous_election is not None
            assert previous_evaluation is not None
            assert current_election is not None
            assert current_evaluation is not None
            center = frame_index - 1
            election_cross[:, center, :] = 0.5 * np.real(
                np.sum(current_election * np.conj(previous_election), axis=2)
                + np.sum(current_election * np.conj(next_election), axis=2)
            )
            evaluation_cross[:, center, :] = 0.5 * np.real(
                np.sum(current_evaluation * np.conj(previous_evaluation), axis=2)
                + np.sum(current_evaluation * np.conj(next_evaluation), axis=2)
            )
        previous_election, current_election = current_election, next_election
        previous_evaluation, current_evaluation = (
            current_evaluation,
            next_evaluation,
        )
        if (frame_index + 1) % 10 == 0 or frame_index + 1 == len(files):
            print(
                f"full-census {stack.name} frames={frame_index + 1}/{len(files)}",
                flush=True,
            )

    assert election_cross is not None
    assert evaluation_cross is not None
    assert site_ids is not None
    assert site_xy is not None
    assert geometry is not None
    assert tile_geometry is not None
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output,
        election_crosspower=election_cross,
        evaluation_crosspower=evaluation_cross,
        site_ids=np.asarray(site_ids),
        site_xy=site_xy,
    )
    inventory = {
        "elapsed_seconds": time.perf_counter() - started,
        "expected_frames": expected_frames,
        "first_file": files[0].name,
        "frames": len(files),
        "geometry": geometry,
        "last_file": files[-1].name,
        "path": str(stack),
        "prepared_bytes": output.stat().st_size,
        "prepared_path": str(output),
        "tile_geometry": tile_geometry,
        "total_source_bytes": int(sum(path.stat().st_size for path in files)),
    }
    atomic_json(output.with_suffix(".inventory.json"), inventory)
    return inventory


def ensure_crosspower(
    stack: Path,
    cache: Path,
    *,
    expected_frames: int,
    refresh: bool,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    inventory_path = cache.with_suffix(".inventory.json")
    if refresh and cache.exists():
        cache.unlink()
    if refresh and inventory_path.exists():
        inventory_path.unlink()
    if not cache.exists():
        inventory = extract_crosspower(
            stack,
            cache,
            expected_frames=expected_frames,
        )
    else:
        real_stack_files(stack, expected_frames)
        inventory = json.loads(inventory_path.read_text(encoding="ascii"))
    with np.load(cache, allow_pickle=False) as archive:
        prepared = {name: archive[name] for name in archive.files}
    return prepared, inventory


def _physical_site_keys(
    prepared: dict[str, np.ndarray],
    *,
    label: str,
) -> list[tuple[int, int]]:
    identifiers = np.asarray(prepared["site_ids"])
    coordinates = np.asarray(prepared["site_xy"])
    if identifiers.ndim != 1:
        raise ValueError(f"{label} site identifiers must be one-dimensional")
    if coordinates.shape != (identifiers.size, 2):
        raise ValueError(f"{label} site coordinates must have shape [sites,2]")
    normalized_ids = [str(value) for value in identifiers.tolist()]
    if len(set(normalized_ids)) != len(normalized_ids):
        raise ValueError(f"{label} has duplicate site identifiers")
    keys = [(int(x), int(y)) for x, y in coordinates.tolist()]
    if len(set(keys)) != len(keys):
        raise ValueError(f"{label} has duplicate physical site coordinates")
    return keys


def average_complete_passes(
    first: dict[str, np.ndarray],
    second: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """Average aligned A/B cross-powers before the nonlinear election."""

    required = (
        "election_crosspower",
        "evaluation_crosspower",
        "site_ids",
        "site_xy",
    )
    for key in required:
        if key not in first or key not in second:
            raise ValueError(f"complete-pass input is missing {key}")
    _physical_site_keys(first, label="first complete pass")
    _physical_site_keys(second, label="second complete pass")
    if not np.array_equal(first["site_ids"], second["site_ids"]):
        raise ValueError("complete passes have different site identifiers")
    if not np.array_equal(first["site_xy"], second["site_xy"]):
        raise ValueError("complete passes have different site coordinates")
    for key in ("election_crosspower", "evaluation_crosspower"):
        if first[key].shape != second[key].shape:
            raise ValueError(f"complete passes have different {key} shapes")
    return {
        "election_crosspower": 0.5
        * (
            np.asarray(first["election_crosspower"], dtype=np.float64)
            + np.asarray(second["election_crosspower"], dtype=np.float64)
        ),
        "evaluation_crosspower": 0.5
        * (
            np.asarray(first["evaluation_crosspower"], dtype=np.float64)
            + np.asarray(second["evaluation_crosspower"], dtype=np.float64)
        ),
        "site_ids": np.asarray(first["site_ids"]).copy(),
        "site_xy": np.asarray(first["site_xy"]).copy(),
    }


def rehearsal_gate(
    sw4_a: dict[str, np.ndarray],
    sw4_b: dict[str, np.ndarray],
    sw10_a: dict[str, np.ndarray],
    sw10_b: dict[str, np.ndarray],
    *,
    minimum: int = EFFECTIVE_WILSON_MINIMUM,
) -> dict[str, Any]:
    """Evaluate the frozen pass-averaged rehearsal eligibility gate."""

    if minimum <= 0:
        raise ValueError("rehearsal minimum must be positive")
    sw4_summary, sw4_manifest = exact_eligibility(
        average_complete_passes(sw4_a, sw4_b),
        capture_id="rehearsal-tc0-sw4-pass-average",
    )
    sw10_summary, sw10_manifest = exact_eligibility(
        average_complete_passes(sw10_a, sw10_b),
        capture_id="rehearsal-tc0-sw10-pass-average",
    )

    def eligible_coordinates(manifest: dict[str, Any]) -> set[tuple[int, int]]:
        return {
            (int(site["x"]), int(site["y"]))
            for site in manifest["sites"]
            if bool(site["eligible"])
        }

    sw4_sites = eligible_coordinates(sw4_manifest)
    sw10_sites = eligible_coordinates(sw10_manifest)
    common = sw4_sites & sw10_sites
    counts = {
        "pass_averaged_sw4": len(sw4_sites),
        "pass_averaged_sw10": len(sw10_sites),
        "required_step_width_intersection": len(common),
    }
    return {
        "counts": counts,
        "minimum": minimum,
        "pass": all(count >= minimum for count in counts.values()),
        "sw4": sw4_summary,
        "sw10": sw10_summary,
    }


def point_rows(
    election: np.ndarray,
    evaluation: np.ndarray,
) -> dict[str, np.ndarray]:
    site_count, node_count, block_count = election.shape
    if evaluation.shape != election.shape or block_count != BLOCK_COUNT:
        raise ValueError("invalid full-census cross-power arrays")
    election_curve = np.mean(election, axis=2)
    evaluation_curve = np.mean(evaluation, axis=2)
    regularized = regularize_curve(election_curve)
    candidates = np.arange(3, node_count - 3)
    best = candidates[np.argmax(regularized[:, candidates], axis=1)]
    ratios = np.zeros(site_count, dtype=np.float64)
    nodes = np.arange(node_count)
    for site, best_node in enumerate(best):
        far_mask = (
            (np.abs(nodes - best_node) >= FAR_DISTANCE)
            & (nodes >= 1)
            & (nodes < node_count - 1)
        )
        best_signal = max(float(evaluation_curve[site, best_node]), 0.0)
        far_signal = max(float(np.max(evaluation_curve[site, far_mask])), 0.0)
        if best_signal <= 0.0:
            ratios[site] = 0.0
        elif far_signal <= 0.0:
            ratios[site] = math.inf
        else:
            ratios[site] = best_signal / far_signal
    return {
        "best": best,
        "point_mask": ratios >= POINT_RATIO_MIN,
        "ratios": ratios,
    }


def exact_eligibility(
    prepared: dict[str, np.ndarray],
    *,
    capture_id: str,
    start: int = 0,
    length: int | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    election = prepared["election_crosspower"]
    evaluation = prepared["evaluation_crosspower"]
    if length is None:
        length = election.shape[1]
    stop = start + length
    election = np.asarray(election[:, start:stop, :], dtype=np.float64).copy()
    evaluation = np.asarray(evaluation[:, start:stop, :], dtype=np.float64).copy()
    election[:, (0, -1), :] = np.nan
    evaluation[:, (0, -1), :] = np.nan
    points = point_rows(election, evaluation)
    selected = np.flatnonzero(points["point_mask"])
    selected_ids = [
        str(prepared["site_ids"][index]) for index in selected
    ]
    selected_xy = prepared["site_xy"][selected]
    manifest = build_manifest(
        election[selected],
        evaluation[selected],
        selected_ids,
        selected_xy,
        input_digest=arrays_digest(
            (election, evaluation, prepared["site_xy"])
        ),
        capture_id=capture_id,
    )
    finite_ratios = points["ratios"][np.isfinite(points["ratios"])]
    summary = {
        "bootstrap_eligible_count": manifest["eligible_count"],
        "bootstrap_tested_point_eligible": int(selected.size),
        "bootstrap_subset_manifest_sha256": manifest["manifest_sha256"],
        "capture_id": capture_id,
        "end_node_inclusive": stop - 1,
        "maximum_point_ratio": (
            float(np.max(points["ratios"])) if points["ratios"].size else None
        ),
        "median_finite_point_ratio": (
            float(np.median(finite_ratios)) if finite_ratios.size else None
        ),
        "point_ineligible_skipped_bootstrap": int(
            election.shape[0] - selected.size
        ),
        "point_eligible_count": int(selected.size),
        "site_count": int(election.shape[0]),
        "start_node": start,
        "window_nodes": length,
    }
    eligible = int(summary["bootstrap_eligible_count"])
    summary["all_success_wilson_lcb95"] = (
        wilson_lower(eligible, eligible) if eligible else None
    )
    summary["effective_wilson_minimum_met"] = eligible >= 133
    return summary, manifest


def best_window(
    prepared: dict[str, np.ndarray],
    window_nodes: int,
) -> dict[str, int]:
    election = prepared["election_crosspower"]
    rows = []
    for start in range(election.shape[1] - window_nodes + 1):
        point = point_rows(
            np.asarray(
                election[:, start : start + window_nodes, :],
                dtype=np.float64,
            ),
            np.asarray(
                prepared["evaluation_crosspower"][
                    :, start : start + window_nodes, :
                ],
                dtype=np.float64,
            ),
        )
        rows.append(
            {
                "point_eligible_count": int(np.count_nonzero(point["point_mask"])),
                "start_node": start,
            }
        )
    winner = max(
        rows,
        key=lambda row: (row["point_eligible_count"], -row["start_node"]),
    )
    return winner | {
        "window_nodes": window_nodes,
        "windows_evaluated": len(rows),
    }


def compact_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    return {
        key: inventory[key]
        for key in (
            "expected_frames",
            "first_file",
            "frames",
            "geometry",
            "last_file",
            "path",
            "tile_geometry",
            "total_source_bytes",
        )
    }


def run(args: argparse.Namespace) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    arms = {}
    inventories = {}

    sw4, sw4_inventory = ensure_crosspower(
        Path(args.grid_sw4),
        OUT / "full-grid-sw4-crosspower.npz",
        expected_frames=55,
        refresh=args.refresh,
    )
    arms["burned_grid_sw4_exact_55"], sw4_manifest = exact_eligibility(
        sw4,
        capture_id="full-burned-grid-sw4-exact-55",
    )
    atomic_json(OUT / "full-grid-sw4-manifest.json", sw4_manifest)
    inventories["burned_grid_sw4"] = compact_inventory(sw4_inventory)

    sw10, sw10_inventory = ensure_crosspower(
        Path(args.grid_sw10),
        OUT / "full-grid-sw10-crosspower.npz",
        expected_frames=27,
        refresh=args.refresh,
    )
    arms["burned_grid_sw10_exact_27"], sw10_manifest = exact_eligibility(
        sw10,
        capture_id="full-burned-grid-sw10-exact-27",
    )
    atomic_json(OUT / "full-grid-sw10-manifest.json", sw10_manifest)
    inventories["burned_grid_sw10"] = compact_inventory(sw10_inventory)

    tilted, tilted_inventory = ensure_crosspower(
        Path(args.tilted_sw10),
        OUT / "full-tilted-sw10-crosspower.npz",
        expected_frames=92,
        refresh=args.refresh,
    )
    arms["tilted_sw10_full_92"], tilted_full_manifest = exact_eligibility(
        tilted,
        capture_id="full-development-tilted-sw10-92",
    )
    atomic_json(OUT / "full-tilted-sw10-92-manifest.json", tilted_full_manifest)
    window = best_window(tilted, 27)
    arms["tilted_sw10_best_27"], tilted_window_manifest = exact_eligibility(
        tilted,
        capture_id="full-development-tilted-sw10-best-27",
        start=int(window["start_node"]),
        length=27,
    )
    arms["tilted_sw10_best_27"]["windows_evaluated"] = window[
        "windows_evaluated"
    ]
    atomic_json(
        OUT / "full-tilted-sw10-best-27-manifest.json",
        tilted_window_manifest,
    )
    inventories["tilted_sw10"] = compact_inventory(tilted_inventory)

    active = inventories["tilted_sw10"]["tile_geometry"]
    if any(
        inventory["tile_geometry"] != active
        for inventory in inventories.values()
    ):
        raise ValueError("candidate-tile geometry differs across development arms")

    result = {
        "active_area_arithmetic": {
            "formula": (
                "floor(7028/128) * floor(4688/128) = 54 * 36 = 1944"
            ),
            **active,
        },
        "arms": arms,
        "definitions_sha256": hashlib.sha256(
            (LANE / "frozen-definitions.json").read_bytes()
        ).hexdigest(),
        "inventories": inventories,
        "prior_64_site_design": {
            "columns": 8,
            "kind": "fixed grid subsample",
            "reason": (
                "matched the pre-existing M131 8x8 focus-coverage audit and "
                "bounded commissioning cost; it was not the candidate population"
            ),
            "rows": 8,
            "sites": 64,
        },
        "protocol": "M151-M5-full-population-v1",
    }
    atomic_json(RESULT, result)
    for name, row in arms.items():
        print(
            f"{name} point={row['point_eligible_count']}/"
            f"{row['site_count']} eligible={row['bootstrap_eligible_count']}/"
            f"{row['site_count']}"
        )
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--grid-sw4", default=str(DEFAULT_GRID_SW4))
    result.add_argument("--grid-sw10", default=str(DEFAULT_GRID_SW10))
    result.add_argument("--tilted-sw10", default=str(DEFAULT_REAL_STACK))
    result.add_argument(
        "--refresh",
        action="store_true",
        help="discard only this lane's full-census caches and reread RAWs",
    )
    return result


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
