"""Commission the frozen USM plant and interpret unchanged M8-O evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter
import tifffile


INSET = 256
GRID = 8
MATERIAL_PERCENT = 0.0100
MATERIAL_PIXELS = 64
MATERIAL_EXCESS_DN = 16.0
TREND_DELTA_PP = 0.0100
TREND_RATIO = 1.25
TREND_BLOCKS = 40
PLANT_CHANGED_PERCENT = 0.1
PLANT_SIGN_COUNT = 1_000
PLANT_DISPLACEMENT_DN = 16
PLANT_MAX_NEW_RAIL_PERCENT = 1.0

ARMS = (
    {"name": "clean-full", "frames": 65, "exposure_s": 6.0, "ladder": "full"},
    {"name": "middle-full", "frames": 61, "exposure_s": 2.5, "ladder": "full"},
    {"name": "noisy-full", "frames": 60, "exposure_s": 1.0, "ladder": "full"},
    {"name": "clean-n60", "frames": 60, "exposure_s": 6.0, "ladder": "n60"},
    {"name": "middle-n60", "frames": 60, "exposure_s": 2.5, "ladder": "n60"},
    {"name": "noisy-n60", "frames": 60, "exposure_s": 1.0, "ladder": "n60"},
)

PRIOR_FULL_PERCENT = {
    "clean-full": 3.888440750620275,
    "middle-full": 0.0594066325758017,
    "noisy-full": 0.030585032375967623,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def finite_ratio(numerator: float, denominator: float) -> float | str:
    if denominator == 0.0:
        return "Infinity" if numerator > 0.0 else 1.0
    return numerator / denominator


def apply_usm(image: np.ndarray, amount: float = 1.0) -> np.ndarray:
    if image.dtype != np.uint16 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"expected HxWx3 uint16 input, got {image.dtype} {image.shape}")
    linear = image.astype(np.float64) / 65535.0
    blurred = gaussian_filter(
        linear,
        sigma=(1.0, 1.0, 0.0),
        mode="reflect",
        truncate=4.0,
    )
    planted = np.clip(linear + amount * (linear - blurred), 0.0, 1.0)
    return np.floor(planted * 65535.0 + 0.5).astype(np.uint16)


def displacement_metrics(before: np.ndarray, after: np.ndarray, inset: int) -> dict:
    if before.shape != after.shape or before.dtype != after.dtype:
        raise ValueError("USM displacement arrays do not match")
    if 2 * inset >= min(before.shape[:2]):
        raise ValueError(f"inset {inset} leaves no image interior")
    before_i = before[inset:-inset, inset:-inset]
    after_i = after[inset:-inset, inset:-inset]
    delta = after_i.astype(np.int32) - before_i.astype(np.int32)
    samples = int(delta.size)
    changed = int(np.count_nonzero(delta))
    positive = int(np.count_nonzero(delta > 0))
    negative = int(np.count_nonzero(delta < 0))
    newly_low = int(np.count_nonzero((after_i == 0) & (before_i != 0)))
    newly_high = int(np.count_nonzero((after_i == 65535) & (before_i != 65535)))
    return {
        "inset_px": inset,
        "samples": samples,
        "changed_samples": changed,
        "changed_percent": 100.0 * changed / samples,
        "positive_changes": positive,
        "negative_changes": negative,
        "max_positive_dn": int(np.max(delta, initial=0)),
        "min_negative_dn": int(np.min(delta, initial=0)),
        "max_abs_change_dn": int(np.max(np.abs(delta), initial=0)),
        "new_low_rail": newly_low,
        "new_high_rail": newly_high,
        "new_low_rail_percent": 100.0 * newly_low / samples,
        "new_high_rail_percent": 100.0 * newly_high / samples,
    }


def commission_usm(output: Path) -> dict:
    height = width = 256
    step = np.full((height, width, 3), np.uint16(round(0.25 * 65535)))
    step[:, width // 2 :, :] = np.uint16(round(0.75 * 65535))
    zero = apply_usm(step, amount=0.0)
    constant = np.full_like(step, np.uint16(32768))
    constant_planted = apply_usm(constant, amount=1.0)
    planted = apply_usm(step, amount=1.0)
    metrics = displacement_metrics(step, planted, inset=0)
    checks = {
        "amount_zero_exact": bool(np.array_equal(step, zero)),
        "constant_unchanged": bool(np.array_equal(constant, constant_planted)),
        "both_signs": (
            metrics["positive_changes"] > 0 and metrics["negative_changes"] > 0
        ),
        "changed_at_least_0_1_percent": (
            metrics["changed_percent"] >= PLANT_CHANGED_PERCENT
        ),
        "max_displacement_at_least_16_dn": (
            metrics["max_abs_change_dn"] >= PLANT_DISPLACEMENT_DN
        ),
    }
    payload = {
        "protocol": 1,
        "operator": {
            "sigma": [1.0, 1.0, 0.0],
            "mode": "reflect",
            "truncate": 4.0,
            "amount": 1.0,
            "encoding": "clip [0,1], floor(x*65535+0.5), uint16",
        },
        "fixture": {
            "shape": list(step.shape),
            "left_u16": int(step[0, 0, 0]),
            "right_u16": int(step[0, -1, 0]),
            "constant_u16": int(constant[0, 0, 0]),
        },
        "metrics": metrics,
        "checks": checks,
        "passed": all(checks.values()),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
        },
    }
    write_json(output, payload)
    if not payload["passed"]:
        raise RuntimeError("frozen USM commissioning failed")
    return payload


def plant_real(input_tiff: Path, zero_tiff: Path, output_tiff: Path, manifest: Path) -> dict:
    image = np.asarray(tifffile.imread(input_tiff))
    if image.dtype != np.uint16 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(
            f"{input_tiff}: expected HxWx3 uint16, got {image.dtype} {image.shape}"
        )
    shutil.copyfile(input_tiff, zero_tiff)
    if sha256(input_tiff) != sha256(zero_tiff):
        raise RuntimeError("amount-0 control is not a byte-exact copy")
    planted = apply_usm(image, amount=1.0)
    metrics = displacement_metrics(image, planted, inset=INSET)
    tifffile.imwrite(
        output_tiff,
        planted,
        photometric="rgb",
        metadata=None,
    )
    reread = np.asarray(tifffile.imread(output_tiff))
    if not np.array_equal(planted, reread):
        raise RuntimeError("USM TIFF did not round-trip exactly")
    checks = {
        "changed_at_least_0_1_percent": (
            metrics["changed_percent"] >= PLANT_CHANGED_PERCENT
        ),
        "at_least_1000_positive": (
            metrics["positive_changes"] >= PLANT_SIGN_COUNT
        ),
        "at_least_1000_negative": (
            metrics["negative_changes"] >= PLANT_SIGN_COUNT
        ),
        "max_displacement_at_least_16_dn": (
            metrics["max_abs_change_dn"] >= PLANT_DISPLACEMENT_DN
        ),
        "new_low_rail_at_most_1_percent": (
            metrics["new_low_rail_percent"] <= PLANT_MAX_NEW_RAIL_PERCENT
        ),
        "new_high_rail_at_most_1_percent": (
            metrics["new_high_rail_percent"] <= PLANT_MAX_NEW_RAIL_PERCENT
        ),
    }
    payload = {
        "protocol": 1,
        "input": str(input_tiff.resolve()),
        "input_sha256": sha256(input_tiff),
        "zero_control": str(zero_tiff.resolve()),
        "zero_control_sha256": sha256(zero_tiff),
        "output": str(output_tiff.resolve()),
        "output_sha256": sha256(output_tiff),
        "shape": list(image.shape),
        "operator": {
            "sigma": [1.0, 1.0, 0.0],
            "mode": "reflect",
            "truncate": 4.0,
            "amount": 1.0,
            "encoding": "clip [0,1], floor(x*65535+0.5), uint16",
        },
        "metrics": metrics,
        "checks": checks,
        "potent": all(checks.values()),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
        },
    }
    write_json(manifest, payload)
    if not payload["potent"]:
        raise RuntimeError("real USM plant failed its frozen potency gate")
    return payload


def checked_o_result(
    state: Path, label: str | None = None
) -> tuple[dict[str, Any], np.ndarray, str, str]:
    suffix = f"-{label}" if label else ""
    result_path = state / f"m8-o{suffix}.json"
    violation_path = state / f"m8-o{suffix}-violations.npy"
    result = read_json(result_path)
    result_sha = sha256(result_path)
    violation_sha = sha256(violation_path)
    if violation_sha != result["violations_sha256"]:
        raise RuntimeError(f"{violation_path}: M8-O evidence hash mismatch")
    rows = np.load(violation_path, mmap_mode="r")
    if int(rows.shape[0]) != int(result["violations"]):
        raise RuntimeError(
            f"{violation_path}: {rows.shape[0]} rows != {result['violations']}"
        )
    if int(result["unbracketed_samples"]) != 0:
        raise RuntimeError(f"{state}: M8-O has unbracketed samples")
    return result, rows, result_sha, violation_sha


def checked_r_result(state: Path, expected_frames: int) -> dict[str, Any]:
    result_path = state / "m8-r.json"
    result = read_json(result_path)
    expected_sites = 4 * expected_frames
    if int(result["frames"]) != expected_frames or int(result["sites"]) != expected_sites:
        raise RuntimeError(
            f"{state}: expected {expected_frames}/{expected_sites} frames/sites, "
            f"got {result['frames']}/{result['sites']}"
        )
    if int(result["coverage_mismatches"]) != 0:
        raise RuntimeError(f"{state}: coordinate-validity mismatch")
    blocks = list((state / "blocks").glob("*.m8site"))
    if blocks:
        raise RuntimeError(f"{state}: {len(blocks)} trace blocks remain")
    seen = list((state / "seen").iterdir())
    if len(seen) != expected_sites:
        raise RuntimeError(f"{state}: expected {expected_sites} seen markers, got {len(seen)}")
    manifest_rows = result["violation_manifests"]
    counted = 0
    evidence_lines = []
    state_root = state.resolve()
    for row in manifest_rows:
        path = Path(row["path"]).resolve()
        if not path.is_relative_to(state_root):
            raise RuntimeError(f"{path}: R evidence escapes its state directory")
        actual_hash = sha256(path)
        if actual_hash != row["sha256"]:
            raise RuntimeError(f"{path}: R evidence hash mismatch")
        count = int(np.load(path, mmap_mode="r").shape[0])
        if count != int(row["count"]):
            raise RuntimeError(f"{path}: {count} rows != {row['count']}")
        counted += count
        evidence_lines.append(f"{row['frame']}|{row['site']}|{count}|{actual_hash}")
    if counted != int(result["violations"]):
        raise RuntimeError(f"{state}: R evidence count mismatch")
    evidence_index = hashlib.sha256(
        "\n".join(sorted(evidence_lines)).encode("utf-8")
    ).hexdigest().upper()
    return {
        "frames": expected_frames,
        "sites": expected_sites,
        "denominator": int(result["denominator"]),
        "violations": int(result["violations"]),
        "percent": float(result["percent"]),
        "lower_violations": int(result["lower_violations"]),
        "upper_violations": int(result["upper_violations"]),
        "coverage_mismatches": int(result["coverage_mismatches"]),
        "result_sha256": sha256(result_path),
        "violation_manifest_count": len(manifest_rows),
        "violation_coordinates": counted,
        "violation_index_sha256": evidence_index,
    }


def serialise_row(row: np.void) -> dict[str, int | float]:
    return {
        name: (
            int(row[name])
            if np.issubdtype(row.dtype[name], np.integer)
            else float(row[name])
        )
        for name in row.dtype.names or ()
    }


def grid_metrics(rows: np.ndarray, width: int, height: int) -> dict:
    x_edges = np.linspace(INSET, width - INSET, GRID + 1, dtype=np.int64)
    y_edges = np.linspace(INSET, height - INSET, GRID + 1, dtype=np.int64)
    counts = np.zeros((GRID, GRID), dtype=np.int64)
    if rows.shape[0]:
        gx = np.searchsorted(x_edges[1:-1], rows["x"], side="right")
        gy = np.searchsorted(y_edges[1:-1], rows["y"], side="right")
        np.add.at(counts, (gy, gx), 1)
    denominators = np.empty((GRID, GRID), dtype=np.int64)
    for gy in range(GRID):
        for gx in range(GRID):
            denominators[gy, gx] = (
                (y_edges[gy + 1] - y_edges[gy])
                * (x_edges[gx + 1] - x_edges[gx])
                * 3
            )
    rates = 100.0 * counts.astype(np.float64) / denominators
    return {
        "shape": [GRID, GRID],
        "x_edges": x_edges.tolist(),
        "y_edges": y_edges.tolist(),
        "counts": counts.reshape(-1).tolist(),
        "denominators": denominators.reshape(-1).tolist(),
        "percent": rates.reshape(-1).tolist(),
        "blocks_with_violations": int(np.count_nonzero(counts)),
    }


def spatial_o_metrics(
    result: dict[str, Any],
    rows: np.ndarray,
    tiff_path: Path,
    result_sha: str,
    violation_sha: str,
) -> dict[str, Any]:
    image = np.asarray(tifffile.imread(tiff_path))
    if image.dtype != np.uint16 or image.ndim != 3 or image.shape[2] != 3:
        raise ValueError(f"{tiff_path}: invalid M8-O image {image.dtype} {image.shape}")
    height, width, channels = image.shape
    if 2 * INSET >= min(height, width):
        raise RuntimeError(f"{tiff_path}: frozen inset leaves no interior")
    expected_denominator = height * width * channels
    if int(result["denominator"]) != expected_denominator:
        raise RuntimeError(
            f"{tiff_path}: M8-O denominator {result['denominator']} != "
            f"{expected_denominator}"
        )
    actual_tiff_sha = sha256(tiff_path)
    if actual_tiff_sha != result["tiff_sha256"]:
        raise RuntimeError(f"{tiff_path}: TIFF hash differs from M8-O result")

    inset_mask = (
        (rows["x"] >= INSET)
        & (rows["x"] < width - INSET)
        & (rows["y"] >= INSET)
        & (rows["y"] < height - INSET)
    )
    inset_rows = rows[inset_mask]
    inset_denominator = (height - 2 * INSET) * (width - 2 * INSET) * channels
    inset_count = int(inset_rows.shape[0])
    full_count = int(rows.shape[0])
    lower = inset_rows[inset_rows["direction"] < 0]
    upper = inset_rows[inset_rows["direction"] > 0]
    if inset_count:
        pixel_ids = (
            inset_rows["y"].astype(np.uint64) * np.uint64(width)
            + inset_rows["x"].astype(np.uint64)
        )
        distinct_pixels = int(np.unique(pixel_ids).size)
        max_abs = float(np.max(np.abs(inset_rows["signed_excess"])))
        min_lower = float(np.min(lower["signed_excess"])) if lower.size else 0.0
        max_upper = float(np.max(upper["signed_excess"])) if upper.size else 0.0
        worst_lower = (
            serialise_row(lower[int(np.argmin(lower["signed_excess"]))])
            if lower.size
            else None
        )
        worst_upper = (
            serialise_row(upper[int(np.argmax(upper["signed_excess"]))])
            if upper.size
            else None
        )
        hull_lo_gt_one = int(np.count_nonzero(inset_rows["lo"] > 1.0))
        hull_hi_lt_zero = int(np.count_nonzero(inset_rows["hi"] < 0.0))
        encoded_low = int(np.count_nonzero(inset_rows["encoded"] == 0))
        encoded_high = int(np.count_nonzero(inset_rows["encoded"] == 65535))
    else:
        distinct_pixels = 0
        max_abs = min_lower = max_upper = 0.0
        worst_lower = worst_upper = None
        hull_lo_gt_one = hull_hi_lt_zero = encoded_low = encoded_high = 0

    interior = image[INSET:-INSET, INSET:-INSET]
    grid = grid_metrics(inset_rows, width, height)
    return {
        "tiff": str(tiff_path.resolve()),
        "tiff_sha256": actual_tiff_sha,
        "shape": [height, width, channels],
        "result_sha256": result_sha,
        "violations_sha256": violation_sha,
        "full": {
            "denominator": int(result["denominator"]),
            "violations": full_count,
            "lower_violations": int(result["lower_violations"]),
            "upper_violations": int(result["upper_violations"]),
            "fraction": float(result["fraction"]),
            "percent": float(result["percent"]),
            "min_lower_signed_excess_linear": float(
                result["min_lower_signed_excess_linear"]
            ),
            "max_upper_signed_excess_linear": float(
                result["max_upper_signed_excess_linear"]
            ),
            "max_abs_signed_excess_linear": float(
                result["max_abs_signed_excess_linear"]
            ),
            "max_abs_signed_excess_u16_dn": float(
                result["max_abs_signed_excess_u16_lsb"]
            ),
            "low_rail_samples": int(np.count_nonzero(image == 0)),
            "high_rail_samples": int(np.count_nonzero(image == 65535)),
        },
        "inset_256": {
            "denominator": int(inset_denominator),
            "violations": inset_count,
            "lower_violations": int(lower.shape[0]),
            "upper_violations": int(upper.shape[0]),
            "fraction": inset_count / inset_denominator,
            "percent": 100.0 * inset_count / inset_denominator,
            "distinct_violating_pixels": distinct_pixels,
            "min_lower_signed_excess_linear": min_lower,
            "max_upper_signed_excess_linear": max_upper,
            "max_abs_signed_excess_linear": max_abs,
            "max_abs_signed_excess_u16_dn": max_abs * 65535.0,
            "worst_lower": worst_lower,
            "worst_upper": worst_upper,
            "violation_rows_with_hull_lo_gt_one": hull_lo_gt_one,
            "violation_rows_with_hull_hi_lt_zero": hull_hi_lt_zero,
            "violating_encoded_low_rail": encoded_low,
            "violating_encoded_high_rail": encoded_high,
            "low_rail_samples": int(np.count_nonzero(interior == 0)),
            "high_rail_samples": int(np.count_nonzero(interior == 65535)),
        },
        "boundary": {
            "violations_outside_inset": full_count - inset_count,
            "fraction_of_violations_outside_inset": (
                (full_count - inset_count) / full_count if full_count else 0.0
            ),
        },
        "grid_8x8_inset": grid,
    }


def material(metrics: dict[str, Any], region: str) -> bool:
    row = metrics[region]
    return bool(
        row["percent"] >= MATERIAL_PERCENT
        or (
            row.get("distinct_violating_pixels", row["violations"])
            >= MATERIAL_PIXELS
            and row["max_abs_signed_excess_u16_dn"] >= MATERIAL_EXCESS_DN
        )
    )


def evaluate_null(clean: dict[str, Any]) -> dict[str, Any]:
    exact_green = clean["full"]["violations"] == 0
    inset_material = material(clean, "inset_256")
    full_material = material(clean, "full")
    if inset_material:
        verdict = "NULL-MATERIAL"
    elif full_material:
        verdict = "BOUNDARY-CONCENTRATED"
    else:
        verdict = "NULL-NOT-MATERIAL"
    return {
        "scorecard_exact_zero": exact_green,
        "material_full": full_material,
        "material_inset_256": inset_material,
        "inset_blocks_with_violations": clean["grid_8x8_inset"][
            "blocks_with_violations"
        ],
        "verdict": verdict,
    }


def ladder_conditions(
    clean: dict[str, Any],
    middle: dict[str, Any],
    noisy: dict[str, Any],
) -> dict[str, Any]:
    p_clean = clean["inset_256"]["percent"]
    p_middle = middle["inset_256"]["percent"]
    p_noisy = noisy["inset_256"]["percent"]
    block_clean = np.asarray(clean["grid_8x8_inset"]["percent"])
    block_noisy = np.asarray(noisy["grid_8x8_inset"]["percent"])
    increasing_blocks = int(np.count_nonzero(block_noisy > block_clean))
    ratio = finite_ratio(p_noisy, p_clean)
    ratio_pass = ratio == "Infinity" or float(ratio) >= TREND_RATIO
    checks = {
        "strict_clean_middle_noisy": p_clean < p_middle < p_noisy,
        "noisy_minus_clean_at_least_0_0100_pp": (
            p_noisy - p_clean >= TREND_DELTA_PP
        ),
        "noisy_over_clean_at_least_1_25": ratio_pass,
        "at_least_40_of_64_blocks_increase": increasing_blocks >= TREND_BLOCKS,
    }
    return {
        "clean_percent": p_clean,
        "middle_percent": p_middle,
        "noisy_percent": p_noisy,
        "noisy_minus_clean_percentage_points": p_noisy - p_clean,
        "noisy_over_clean": ratio,
        "blocks_noisy_gt_clean": increasing_blocks,
        "checks": checks,
        "passes": all(checks.values()),
    }


def evaluate_noise(arms: dict[str, Any]) -> dict[str, Any]:
    full = ladder_conditions(
        arms["clean-full"]["m8_o"],
        arms["middle-full"]["m8_o"],
        arms["noisy-full"]["m8_o"],
    )
    n60 = ladder_conditions(
        arms["clean-n60"]["m8_o"],
        arms["middle-n60"]["m8_o"],
        arms["noisy-n60"]["m8_o"],
    )
    if n60["passes"] and full["passes"]:
        verdict = "NOISE-SENSITIVE"
    elif n60["passes"] or full["passes"]:
        verdict = "NOISE-INCONCLUSIVE"
    else:
        verdict = "NOISE-TREND-NOT-OBSERVED"
    return {"full_n": full, "matched_n60": n60, "verdict": verdict}


def evaluate_sensitivity(
    base: dict[str, Any],
    zero: dict[str, Any],
    planted: dict[str, Any],
    plant_manifest: dict[str, Any],
) -> dict[str, Any]:
    p_base = base["inset_256"]["percent"]
    p_planted = planted["inset_256"]["percent"]
    ratio = finite_ratio(p_planted, p_base)
    ratio_pass = ratio == "Infinity" or float(ratio) >= TREND_RATIO
    base_blocks = np.asarray(base["grid_8x8_inset"]["percent"])
    planted_blocks = np.asarray(planted["grid_8x8_inset"]["percent"])
    blocks_increase = int(np.count_nonzero(planted_blocks > base_blocks))
    zero_checks = {
        "tiff_byte_exact": (
            base["tiff_sha256"] == zero["tiff_sha256"]
            == plant_manifest["zero_control_sha256"]
        ),
        "counts_exact": (
            base["full"]["violations"] == zero["full"]["violations"]
            and base["full"]["lower_violations"] == zero["full"]["lower_violations"]
            and base["full"]["upper_violations"] == zero["full"]["upper_violations"]
        ),
        "violation_manifest_exact": (
            base["violations_sha256"] == zero["violations_sha256"]
        ),
    }
    response_checks = {
        "increase_at_least_0_0100_pp": (
            p_planted - p_base >= TREND_DELTA_PP
        ),
        "ratio_at_least_1_25": ratio_pass,
        "at_least_40_of_64_blocks_increase": blocks_increase >= TREND_BLOCKS,
        "maximum_excess_not_smaller": (
            planted["inset_256"]["max_abs_signed_excess_linear"]
            >= base["inset_256"]["max_abs_signed_excess_linear"]
        ),
    }
    passed = (
        bool(plant_manifest["potent"])
        and all(zero_checks.values())
        and all(response_checks.values())
    )
    return {
        "baseline_inset_percent": p_base,
        "planted_inset_percent": p_planted,
        "increase_percentage_points": p_planted - p_base,
        "planted_over_baseline": ratio,
        "blocks_increase": blocks_increase,
        "plant_potent": bool(plant_manifest["potent"]),
        "zero_control_checks": zero_checks,
        "response_checks": response_checks,
        "verdict": "SENSITIVITY-PASS" if passed else "UNCOMMISSIONED",
    }


def validate_input_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict:
    unchanged = before["captures"] == after["captures"]
    if not unchanged:
        raise RuntimeError("strictly read-only capture manifest changed during run")
    return {
        "unchanged": True,
        "method": before["method"],
        "before_utc": before["captured_utc"],
        "after_utc": after["captured_utc"],
        "captures": before["captures"],
    }


def summarize(out: Path, output: Path) -> dict[str, Any]:
    before = read_json(out / "inputs-before.json")
    after = read_json(out / "inputs-after.json")
    input_integrity = validate_input_snapshots(before, after)
    commission = read_json(out / "commission" / "commission.json")
    if not commission["passed"]:
        raise RuntimeError("pinned M8 checker commissioning did not pass")
    independence = read_json(out / "independence-audit.json")
    if not independence["independent"]:
        raise RuntimeError("pinned M8 checker imported Strehl")
    usm_commission = read_json(out / "usm-commission.json")
    if not usm_commission["passed"]:
        raise RuntimeError("USM implementation commissioning did not pass")

    arms: dict[str, Any] = {}
    for arm in ARMS:
        name = arm["name"]
        state = out / f"{name}-state"
        tiff_path = out / f"{name}.tiff"
        r_result = checked_r_result(state, int(arm["frames"]))
        o_result, o_rows, o_result_sha, o_violation_sha = checked_o_result(
            state, "base" if name == "clean-full" else None
        )
        o_metrics = spatial_o_metrics(
            o_result, o_rows, tiff_path, o_result_sha, o_violation_sha
        )
        arms[name] = {
            "frames": int(arm["frames"]),
            "exposure_s": float(arm["exposure_s"]),
            "ladder": arm["ladder"],
            "m8_r_integrity": r_result,
            "m8_o": o_metrics,
            "completion": read_json(out / f"{name}-complete.json"),
        }

    clean_state = out / "clean-full-state"
    zero_result, zero_rows, zero_result_sha, zero_violation_sha = checked_o_result(
        clean_state, "zero"
    )
    zero_metrics = spatial_o_metrics(
        zero_result,
        zero_rows,
        out / "clean-full-usm-a0.tiff",
        zero_result_sha,
        zero_violation_sha,
    )
    usm_result, usm_rows, usm_result_sha, usm_violation_sha = checked_o_result(
        clean_state, "usm"
    )
    usm_metrics = spatial_o_metrics(
        usm_result,
        usm_rows,
        out / "clean-full-usm-a1.tiff",
        usm_result_sha,
        usm_violation_sha,
    )
    plant_manifest = read_json(out / "clean-full-usm-plant.json")

    null = evaluate_null(arms["clean-full"]["m8_o"])
    noise = evaluate_noise(arms)
    sensitivity = evaluate_sensitivity(
        arms["clean-full"]["m8_o"],
        zero_metrics,
        usm_metrics,
        plant_manifest,
    )
    prior_comparison = {
        name: {
            "prior_percent": prior,
            "replication_percent": arms[name]["m8_o"]["full"]["percent"],
            "difference_percentage_points": (
                arms[name]["m8_o"]["full"]["percent"] - prior
            ),
        }
        for name, prior in PRIOR_FULL_PERCENT.items()
    }
    payload = {
        "protocol": 1,
        "predicates": {
            "inset_px": INSET,
            "grid": [GRID, GRID],
            "material_percent": MATERIAL_PERCENT,
            "material_pixels": MATERIAL_PIXELS,
            "material_excess_dn": MATERIAL_EXCESS_DN,
            "trend_delta_percentage_points": TREND_DELTA_PP,
            "trend_ratio": TREND_RATIO,
            "trend_blocks": TREND_BLOCKS,
        },
        "commissioning": {
            "m8": commission,
            "independence": independence,
            "usm": usm_commission,
        },
        "arms": arms,
        "controls": {
            "clean_full_zero": zero_metrics,
            "clean_full_usm": usm_metrics,
            "plant": plant_manifest,
        },
        "verdicts": {
            "flat_null": null,
            "noise_ladder": noise,
            "usm_sensitivity": sensitivity,
        },
        "prior_result_disclosure": {
            "not_blind": True,
            "comparison": prior_comparison,
        },
        "read_only_inputs": input_integrity,
        "provenance": read_json(out / "provenance.json"),
        "versions": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "tifffile": tifffile.__version__,
        },
    }
    write_json(output, payload)
    print(
        json.dumps(
            {
                "output": str(output.resolve()),
                "output_sha256": sha256(output),
                "verdicts": payload["verdicts"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    commission = sub.add_parser("commission-usm")
    commission.add_argument("--output", type=Path, required=True)

    plant = sub.add_parser("plant")
    plant.add_argument("--input", type=Path, required=True)
    plant.add_argument("--zero", type=Path, required=True)
    plant.add_argument("--output", type=Path, required=True)
    plant.add_argument("--manifest", type=Path, required=True)

    summary = sub.add_parser("summarize")
    summary.add_argument("--out-root", type=Path, required=True)
    summary.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "commission-usm":
        commission_usm(args.output)
    elif args.command == "plant":
        plant_real(args.input, args.zero, args.output, args.manifest)
    elif args.command == "summarize":
        summarize(args.out_root.resolve(), args.output.resolve())
    else:
        raise AssertionError(args.command)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
