"""Compare spatial admission maps on M82's matched bee ISO pair."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

import m82lib as M


PAIR = ("bee-2", "bee-3")
GUARD = 32
PRIMARY = "0.70"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def load_fields(stack: str) -> np.ndarray:
    cfg = M.STACKS[stack]
    x, y, width, height = cfg["sharp_detail"]
    padded = (x - M.PAD, y - M.PAD, width + 2 * M.PAD, height + 2 * M.PAD)
    files = M.stack_files(stack)
    iso = float(cfg["iso"])
    cube = None
    started = time.time()
    black = None
    plane = None
    for index, path in enumerate(files):
        _, _, field, _, frame_black, frame_plane = M.frame_arrays(path, iso, padded)
        if cube is None:
            cube = np.empty((len(files), height, width), dtype=np.float32)
            black = frame_black
            plane = frame_plane
        if frame_black != black or frame_plane != plane:
            raise RuntimeError(f"{stack}: frame levels or geometry changed")
        cube[index] = field[
            M.PAD : M.PAD + height, M.PAD : M.PAD + width
        ]
        if index == 0 or (index + 1) % 30 == 0 or index + 1 == len(files):
            print(
                f"{stack}: {index + 1}/{len(files)} fields "
                f"({time.time() - started:.1f}s)",
                flush=True,
            )
    if cube is None:
        raise RuntimeError(f"{stack}: no frames")
    return cube


def count_map(
    fields: np.ndarray, indexes: np.ndarray, gate: float
) -> np.ndarray:
    best, winner = M.subset_reference(fields, indexes)
    tolerance = np.float32(
        gate * math.sqrt(2.0) * float(M.constants()["focus_noise_sd"])
    )
    count = np.zeros(best.shape, dtype=np.uint16)
    for frame_index in indexes:
        gap = best - fields[frame_index]
        admitted = gap <= tolerance  # M82_ISO_CORE_ADMISSION
        admitted |= winner == frame_index
        count += admitted
    if np.any(count == 0):
        raise RuntimeError("admission produced an empty pixel")
    return count


def map_stats(count: np.ndarray) -> dict:
    quantiles = np.quantile(count, [0.1, 0.5, 0.9])
    return {
        "mean": float(count.mean()),
        "p10": float(quantiles[0]),
        "p50": float(quantiles[1]),
        "p90": float(quantiles[2]),
        "singleton_percent": float(100.0 * np.mean(count == 1)),
        "sha256": array_sha256(count),
    }


def overlap(
    reference: np.ndarray, moving: np.ndarray, dy: int, dx: int, guard: int
) -> tuple[np.ndarray, np.ndarray]:
    height, width = reference.shape
    if moving.shape != reference.shape:
        raise ValueError("overlap requires equal shapes")
    ry0 = max(dy, 0)
    ry1 = min(height, height + dy)
    rx0 = max(dx, 0)
    rx1 = min(width, width + dx)
    my0 = max(-dy, 0)
    my1 = min(height, height - dy)
    mx0 = max(-dx, 0)
    mx1 = min(width, width - dx)
    ref = reference[ry0:ry1, rx0:rx1]
    mov = moving[my0:my1, mx0:mx1]
    if min(ref.shape) <= 2 * guard:
        raise RuntimeError(f"guard {guard} empties overlap {ref.shape}")
    return (
        ref[guard:-guard, guard:-guard],
        mov[guard:-guard, guard:-guard],
    )


def spatial_metrics(
    reference: np.ndarray,
    moving: np.ndarray,
    shift: tuple[int, int] = (0, 0),
) -> dict:
    ref, mov = overlap(reference, moving, shift[0], shift[1], GUARD)
    ref_log = np.log1p(ref.astype(np.float64)).ravel()
    mov_log = np.log1p(mov.astype(np.float64)).ravel()
    rho = float(spearmanr(ref_log, mov_log).statistic)
    ref_single = ref == 1
    mov_single = mov == 1
    intersection = int(np.sum(ref_single & mov_single))
    union = int(np.sum(ref_single | mov_single))
    return {
        "spearman_log1p": rho,
        "exact_count_agreement": float(np.mean(ref == mov)),
        "mean_absolute_count_difference": float(
            np.mean(np.abs(ref.astype(np.int32) - mov.astype(np.int32)))
        ),
        "singleton_symmetric_difference": float(np.mean(ref_single != mov_single)),
        "singleton_jaccard": float(intersection / union) if union else 1.0,
        "overlap_shape": list(ref.shape),
    }


def tile_reverse(values: np.ndarray) -> np.ndarray:
    if values.shape[0] % 8 or values.shape[1] % 8:
        raise ValueError("tile mutation requires dimensions divisible by 8")
    height, width = values.shape
    tile_h = height // 8
    tile_w = width // 8
    tiles = (
        values.reshape(8, tile_h, 8, tile_w)
        .transpose(0, 2, 1, 3)
        .reshape(64, tile_h, tile_w)
    )
    return (
        tiles[::-1]
        .reshape(8, 8, tile_h, tile_w)
        .transpose(0, 2, 1, 3)
        .reshape(height, width)
        .copy()
    )


def evaluate_bar(cross: dict, within2: dict, within3: dict) -> dict:
    repeatability_floor = min(
        within2["spearman_log1p"], within3["spearman_log1p"]
    )
    repeatability_xor = max(
        within2["singleton_symmetric_difference"],
        within3["singleton_symmetric_difference"],
    )
    capable = bool(
        within2["spearman_log1p"] >= 0.50
        and within3["spearman_log1p"] >= 0.50
    )
    rho_pass = bool(
        cross["spearman_log1p"] >= 0.50
        and cross["spearman_log1p"] >= repeatability_floor - 0.10
    )
    singleton_pass = bool(
        cross["singleton_symmetric_difference"] <= repeatability_xor + 0.10
    )
    return {
        "within_spearman_floor": repeatability_floor,
        "within_singleton_xor_ceiling": repeatability_xor,
        "capable": capable,
        "rho_pass": rho_pass,
        "singleton_pass": singleton_pass,
        "co_location_bar_pass": bool(capable and rho_pass and singleton_pass),
    }


def self_test() -> None:
    fields = np.array(
        [
            [[3.0, 0.0], [0.0, 3.0]],
            [[2.9, 2.0], [2.0, 2.9]],
            [[0.0, 3.0], [3.0, 0.0]],
        ],
        dtype=np.float32,
    )
    indexes = np.arange(3, dtype=np.int64)
    selector = count_map(fields, indexes, 0.0)
    if not np.array_equal(selector, np.ones((2, 2), dtype=np.uint16)):
        raise AssertionError(f"selector count wrong: {selector}")
    broad = count_map(fields, indexes, 1000.0)
    if not np.array_equal(broad, np.full((2, 2), 3, dtype=np.uint16)):
        raise AssertionError(f"broad count wrong: {broad}")
    base = np.arange(64 * 64, dtype=np.uint16).reshape(64, 64)
    if np.array_equal(base, tile_reverse(base)):
        raise AssertionError("tile mutation did not change map")
    print("M82_ISO_SELF_TEST_COUNT=3")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args()
    self_test()
    if args.self_test_only:
        return

    preconditions_path = M.HERE / "bee-iso-preconditions.json"
    confirm_path = M.HERE / "bee-confirm-results.json"
    preconditions = json.loads(preconditions_path.read_text(encoding="utf-8"))
    confirm = json.loads(confirm_path.read_text(encoding="utf-8"))
    shift = tuple(
        int(round(value))
        for value in preconditions["framing"]["real"][
            "shift_green_px_to_apply_to_bee3"
        ]
    )
    gates = {
        stack: {
            f"{request:.2f}": float(
                confirm["stacks"][stack]["targets"][f"{request:.2f}"][
                    "solved_gate"
                ]
            )
            for request in M.REQUESTS
        }
        for stack in PAIR
    }

    maps = {}
    stats = {}
    for stack in PAIR:
        fields = load_fields(stack)
        n = fields.shape[0]
        subsets = {
            "full": np.arange(n, dtype=np.int64),
            "even": np.arange(0, n, 2, dtype=np.int64),
            "odd": np.arange(1, n, 2, dtype=np.int64),
        }
        maps[stack] = {}
        stats[stack] = {}
        for request, gate in gates[stack].items():
            maps[stack][request] = {}
            stats[stack][request] = {}
            for subset, indexes in subsets.items():
                count = count_map(fields, indexes, gate)
                maps[stack][request][subset] = count
                stats[stack][request][subset] = map_stats(count)
        del fields
        gc.collect()

    comparisons = {}
    decisions = {}
    for request in gates["bee-2"]:
        cross = spatial_metrics(
            maps["bee-2"][request]["full"],
            maps["bee-3"][request]["full"],
            shift,
        )
        within2 = spatial_metrics(
            maps["bee-2"][request]["even"],
            maps["bee-2"][request]["odd"],
        )
        within3 = spatial_metrics(
            maps["bee-3"][request]["even"],
            maps["bee-3"][request]["odd"],
        )
        comparisons[request] = {
            "cross_iso_full": cross,
            "within_bee2_even_odd": within2,
            "within_bee3_even_odd": within3,
        }
        decisions[request] = evaluate_bar(cross, within2, within3)

    primary_bee3 = maps["bee-3"][PRIMARY]["full"]
    original_hash = array_sha256(primary_bee3)
    mutated = tile_reverse(primary_bee3)
    mutated_hash = array_sha256(mutated)
    mutated_cross = spatial_metrics(
        maps["bee-2"][PRIMARY]["full"], mutated, shift
    )
    mutation_bar = evaluate_bar(
        mutated_cross,
        comparisons[PRIMARY]["within_bee2_even_odd"],
        comparisons[PRIMARY]["within_bee3_even_odd"],
    )
    restored = primary_bee3.copy()
    mutation = {
        "original_sha256": original_hash,
        "mutated_sha256": mutated_hash,
        "changed_readback": mutated_hash != original_hash,
        "mutated_cross": mutated_cross,
        "mutated_bar": mutation_bar,
        "same_bar_failed": not mutation_bar["co_location_bar_pass"],
        "spearman_drop": (
            comparisons[PRIMARY]["cross_iso_full"]["spearman_log1p"]
            - mutated_cross["spearman_log1p"]
        ),
        "restored_sha256": array_sha256(restored),
        "byte_restored": array_sha256(restored) == original_hash,
    }
    mutation["pass"] = bool(
        mutation["changed_readback"]
        and mutation["same_bar_failed"]
        and mutation["spearman_drop"] >= 0.20
        and mutation["byte_restored"]
    )

    prereqs_pass = bool(
        preconditions["preconditions"]["exif"]
        and preconditions["preconditions"]["framing"]
    )
    primary_decision = decisions[PRIMARY]
    if not prereqs_pass or not mutation["pass"] or not primary_decision["capable"]:
        status = "NOT ESTABLISHED"
    elif primary_decision["co_location_bar_pass"]:
        status = "ADMISSION CO-LOCATED"
    else:
        status = "ADMISSION NOT CO-LOCATED"

    result = {
        "pair": list(PAIR),
        "roi": list(M.STACKS["bee-2"]["sharp_detail"]),
        "guard": GUARD,
        "shift_green_px_to_apply_to_bee3": list(shift),
        "gates": gates,
        "map_stats": stats,
        "comparisons": comparisons,
        "bars": decisions,
        "map_mutation_control": mutation,
        "preconditions_pass": prereqs_pass,
        "status": status,
        "numerical_primary_bar_pass": primary_decision["co_location_bar_pass"],
        "top_level_m82_verdict_changed": False,
        "provenance": {
            "python": __import__("platform").python_version(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "source_sha256": sha256(Path(__file__)),
            "m82lib_sha256": sha256(M.HERE / "m82lib.py"),
            "preconditions_sha256": sha256(preconditions_path),
            "confirm_sha256": sha256(confirm_path),
        },
    }
    output = M.HERE / "bee-iso-admission.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"primary status={status} numerical_bar="
        f"{primary_decision['co_location_bar_pass']} "
        f"rho={comparisons[PRIMARY]['cross_iso_full']['spearman_log1p']:.6f} "
        f"singleton_xor="
        f"{comparisons[PRIMARY]['cross_iso_full']['singleton_symmetric_difference']:.6f} "
        f"mutation={mutation['pass']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
