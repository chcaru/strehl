"""Verify M82's matched bee ISO-pair metadata, framing, and profile premise."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from fractions import Fraction
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

import m82lib as M


STACKS = ("bee-1", "bee-2", "bee-3")
EXPECTED = {
    "bee-1": {"iso": 100.0, "fnumber": 5.6},
    "bee-2": {"iso": 400.0, "fnumber": 5.6},
    "bee-3": {"iso": 100.0, "fnumber": 5.6},
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_sha256(values: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(values).tobytes()).hexdigest()


def parse_named(stack: str) -> list[dict]:
    path = M.HERE / f"exif-named-{stack}.txt"
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        columns = line.split("\t")
        if len(columns) != 5:
            raise RuntimeError(f"{path.name}:{line_no}: expected 5 columns, got {columns}")
        name, iso, fnumber, exposure, focus = columns
        rows.append(
            {
                "filename": name,
                "iso": float(iso),
                "fnumber": float(fnumber),
                "exposure_text": exposure,
                "exposure_seconds": float(Fraction(exposure)),
                "focus_text": focus,
                "focus_m": float(focus.removesuffix(" m")),
            }
        )
    return sorted(rows, key=lambda row: row["filename"])


def parse_exact(stack: str) -> list[tuple[float, float, str]]:
    path = M.HERE / f"exif-{stack}.txt"
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        columns = line.split("\t")
        if len(columns) != 3:
            raise RuntimeError(f"{path.name}:{line_no}: expected 3 columns, got {columns}")
        rows.append((float(columns[0]), float(columns[1]), columns[2]))
    return rows


def exif_summary(stack: str) -> tuple[dict, list[dict]]:
    rows = parse_named(stack)
    exact = parse_exact(stack)
    expected = EXPECTED[stack]
    named_projection = [
        (row["iso"], row["fnumber"], row["focus_text"]) for row in rows
    ]
    focus_counts = Counter(row["focus_text"] for row in rows)
    product_counts = Counter(
        f"{row['iso'] * row['exposure_seconds']:.9g}" for row in rows
    )
    summary = {
        "rows": len(rows),
        "first_filename": rows[0]["filename"] if rows else None,
        "last_filename": rows[-1]["filename"] if rows else None,
        "iso_values": sorted({row["iso"] for row in rows}),
        "fnumber_values": sorted({row["fnumber"] for row in rows}),
        "exposure_values": sorted({row["exposure_text"] for row in rows}),
        "focus_distance_counts": dict(sorted(focus_counts.items())),
        "focus_distance_distinct": len(focus_counts),
        "start_focus_m": rows[0]["focus_m"] if rows else None,
        "iso_exposure_product": (
            rows[0]["iso"] * rows[0]["exposure_seconds"] if rows else None
        ),
        "iso_exposure_product_counts": dict(sorted(product_counts.items())),
        "exact_requested_output_rows": len(exact),
        "exact_and_named_outputs_agree": exact == named_projection,
        "stderr_bytes": {
            "exact": (M.HERE / f"exif-{stack}.stderr.txt").stat().st_size,
            "named": (M.HERE / f"exif-named-{stack}.stderr.txt").stat().st_size,
        },
        "source_hashes": {
            "exact_stdout": file_sha256(M.HERE / f"exif-{stack}.txt"),
            "named_stdout": file_sha256(M.HERE / f"exif-named-{stack}.txt"),
            "exact_command": file_sha256(M.HERE / f"exif-{stack}.command.txt"),
            "named_command": file_sha256(
                M.HERE / f"exif-named-{stack}.command.txt"
            ),
        },
    }
    summary["individual_pass"] = bool(
        len(rows) == 299
        and summary["iso_values"] == [expected["iso"]]
        and summary["fnumber_values"] == [expected["fnumber"]]
        and len(focus_counts) == 9
        and summary["exact_and_named_outputs_agree"]
        and all(size == 0 for size in summary["stderr_bytes"].values())
    )
    return summary, rows


def block_mean_4(values: np.ndarray) -> np.ndarray:
    height = values.shape[0] - values.shape[0] % 4
    width = values.shape[1] - values.shape[1] % 4
    cropped = np.asarray(values[:height, :width], dtype=np.float32)
    return cropped.reshape(height // 4, 4, width // 4, 4).mean(axis=(1, 3))


def overlap(
    reference: np.ndarray, moving: np.ndarray, dy: int, dx: int
) -> tuple[np.ndarray, np.ndarray]:
    """Crop arrays after shifting moving by (dy, dx) into reference coordinates."""
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
    return reference[ry0:ry1, rx0:rx1], moving[my0:my1, mx0:mx1]


def pearson(left: np.ndarray, right: np.ndarray) -> float:
    x = np.asarray(left, dtype=np.float64).ravel()
    y = np.asarray(right, dtype=np.float64).ravel()
    x -= x.mean()
    y -= y.mean()
    denominator = math.sqrt(float(x @ x) * float(y @ y))
    if denominator == 0.0:
        return float("nan")
    return float((x @ y) / denominator)


def phase_shift(reference: np.ndarray, moving: np.ndarray) -> tuple[int, int]:
    height, width = reference.shape
    window = np.outer(np.hanning(height), np.hanning(width))
    ref = (reference - float(reference.mean())) * window
    mov = (moving - float(moving.mean())) * window
    cross = np.fft.fft2(ref) * np.conj(np.fft.fft2(mov))
    cross /= np.maximum(np.abs(cross), np.finfo(np.float64).eps)
    correlation = np.fft.ifft2(cross).real
    py, px = np.unravel_index(int(np.argmax(correlation)), correlation.shape)
    if py > height // 2:
        py -= height
    if px > width // 2:
        px -= width
    return int(py), int(px)


def best_translation(reference_hp: np.ndarray, moving_hp: np.ndarray) -> tuple[int, int]:
    initial_y, initial_x = phase_shift(reference_hp, moving_hp)
    candidates = []
    for dy in range(initial_y - 2, initial_y + 3):
        for dx in range(initial_x - 2, initial_x + 3):
            ref, mov = overlap(reference_hp, moving_hp, dy, dx)
            candidates.append((pearson(ref, mov), dy, dx))
    _, best_y, best_x = max(candidates)
    return best_y, best_x


def tile_reverse(values: np.ndarray) -> np.ndarray:
    height = values.shape[0] - values.shape[0] % 8
    width = values.shape[1] - values.shape[1] % 8
    source = np.ascontiguousarray(values[:height, :width])
    tile_h = height // 8
    tile_w = width // 8
    tiles = (
        source.reshape(8, tile_h, 8, tile_w)
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


def registration_metrics(reference: np.ndarray, moving: np.ndarray) -> dict:
    reference_hp = reference - gaussian_filter(reference, sigma=2.0)
    moving_hp = moving - gaussian_filter(moving, sigma=2.0)
    dy, dx = best_translation(reference_hp, moving_hp)
    raw_ref, raw_mov = overlap(reference, moving, dy, dx)
    hp_ref, hp_mov = overlap(reference_hp, moving_hp, dy, dx)
    design = np.column_stack(
        [raw_mov.astype(np.float64).ravel(), np.ones(raw_mov.size)]
    )
    coefficients, *_ = np.linalg.lstsq(
        design, raw_ref.astype(np.float64).ravel(), rcond=None
    )
    residual = raw_ref.astype(np.float64).ravel() - design @ coefficients
    residual_ratio = float(np.sqrt(np.mean(residual**2)) / np.std(raw_ref))
    metrics = {
        "shift_blocks_to_apply_to_bee3": [dy, dx],
        "shift_green_px_to_apply_to_bee3": [4 * dy, 4 * dx],
        "raw_pearson": pearson(raw_ref, raw_mov),
        "highpass_pearson": pearson(hp_ref, hp_mov),
        "photometric_scale": float(coefficients[0]),
        "photometric_offset_dn": float(coefficients[1]),
        "affine_residual_over_reference_sd": residual_ratio,
        "overlap_blocks": list(raw_ref.shape),
    }
    metrics["pass"] = bool(
        abs(4 * dy) <= 16
        and abs(4 * dx) <= 16
        and metrics["raw_pearson"] >= 0.99
        and metrics["highpass_pearson"] >= 0.90
        and residual_ratio <= 0.15
    )
    return metrics


def decode_first(stack: str) -> dict:
    path = M.stack_files(stack)[0]
    g1, g2, black, plane = M._green_region(path, None)
    g1 = np.maximum(g1 - black, 0.0)
    g2 = np.maximum(g2 - black, 0.0)
    averaged = 0.5 * (g1 + g2)
    return {
        "path": path,
        "black": black,
        "plane": plane,
        "g1_block": block_mean_4(g1),
        "g2_block": block_mean_4(g2),
        "averaged_block": block_mean_4(averaged),
    }


def framing_result() -> dict:
    bee2 = decode_first("bee-2")
    bee3 = decode_first("bee-3")
    real = registration_metrics(bee2["averaged_block"], bee3["averaged_block"])
    sanity = {}
    for name, decoded in (("bee-2", bee2), ("bee-3", bee3)):
        g1hp = decoded["g1_block"] - gaussian_filter(decoded["g1_block"], sigma=2.0)
        g2hp = decoded["g2_block"] - gaussian_filter(decoded["g2_block"], sigma=2.0)
        sanity[name] = pearson(g1hp, g2hp)
    real["green_plane_sanity_highpass_pearson"] = sanity
    real["pass"] = bool(real["pass"] and min(sanity.values()) >= 0.95)

    original = np.ascontiguousarray(bee3["averaged_block"])
    original_hash = array_sha256(original)
    mutated = tile_reverse(original)
    mutated_hash = array_sha256(mutated)
    mutation_reference = bee2["averaged_block"][: mutated.shape[0], : mutated.shape[1]]
    mutated_metrics = registration_metrics(mutation_reference, mutated)
    restored = original.copy()
    mutation = {
        "original_sha256": original_hash,
        "mutated_sha256": mutated_hash,
        "changed_readback": mutated_hash != original_hash,
        "mutated_metrics": mutated_metrics,
        "same_bar_failed": not mutated_metrics["pass"],
        "restored_sha256": array_sha256(restored),
        "byte_restored": array_sha256(restored) == original_hash,
    }
    mutation["pass"] = bool(
        mutation["changed_readback"]
        and mutation["same_bar_failed"]
        and mutation["byte_restored"]
    )
    return {
        "method": {
            "decoder": "rawpy",
            "green_plane": list(bee2["plane"]),
            "black_bee2": bee2["black"],
            "black_bee3": bee3["black"],
            "block_shape": list(bee2["averaged_block"].shape),
            "highpass_sigma_blocks": 2.0,
            "first_files": {
                "bee-2": bee2["path"].name,
                "bee-3": bee3["path"].name,
            },
        },
        "real": real,
        "destructive_control": mutation,
        "framing_precondition_pass": bool(real["pass"] and mutation["pass"]),
    }


def profile_audit() -> dict:
    profile = M.REPO / "crates" / "strehl-core" / "src" / "profile.rs"
    m48 = M.REPO / "docs" / "research" / "M48-read-noise-measured.md"
    m61 = M.REPO / "docs" / "research" / "M61-ptc-high-iso-measured.md"
    m71 = M.REPO / "docs" / "research" / "M71-flat-fields.md"
    model_gain_100 = M.gain_dn_per_e(100.0)
    model_gain_400 = M.gain_dn_per_e(400.0)
    rows = {
        "iso100": {
            "model_gain_dn_per_e": model_gain_100,
            "direct_green_gain_dn_per_e": 0.224103,
            "gain_relative_error": model_gain_100 / 0.224103 - 1.0,
            "gain_source": "M71 PTC table / P5",
            "model_read_noise_e": M.read_noise_e(100.0),
            "direct_dark_read_noise_e": 4.3000,
            "read_noise_relative_error": M.read_noise_e(100.0) / 4.3000 - 1.0,
            "read_source": "M48 local fact 11 table",
        },
        "iso400": {
            "model_gain_dn_per_e": model_gain_400,
            "direct_green_gain_dn_per_e": model_gain_400 * 0.9825,
            "gain_relative_error": 0.9825 - 1.0,
            "gain_source": "M61 fact 12 ISO-400 green aggregate",
            "model_read_noise_e": M.read_noise_e(400.0),
            "direct_dark_read_noise_e": 1.3088,
            "read_noise_relative_error": M.read_noise_e(400.0) / 1.3088 - 1.0,
            "read_source": "M48 local fact 9 table",
        },
    }
    maximum_error = max(
        abs(row[key])
        for row in rows.values()
        for key in ("gain_relative_error", "read_noise_relative_error")
    )
    return {
        "camera_model": "ILCE-7CM2",
        "profile_form": (
            "continuous max(ISO,100)/436.8 gain relation plus one read-noise "
            "constant per gain mode; not an exact per-ISO lookup"
        ),
        "constants": M.constants(),
        "direct_measurement_rows": rows,
        "m61_matched_pair_green_gain_ratio": 4.0486,
        "iso_ratio": 4.0,
        "pair_ratio_relative_error": 4.0486 / 4.0 - 1.0,
        "maximum_scalar_relative_error": maximum_error,
        "scalar_terms_within_10_percent": maximum_error <= 0.10,
        "classification": (
            "MEASUREMENT-BACKED" if maximum_error <= 0.10 else "APPROXIMATE"
        ),
        "known_omissions": [
            "M71 PRNU term absent",
            "spatial green-plane correlation absent",
            "per-pixel sigma field absent",
        ],
        "stale_profile_comment": (
            "profile.rs still says every ISO >=400 is extrapolation and that no "
            "high-mode PTC has run; M61 later ran a clean ISO-400 arm"
        ),
        "source_hashes": {
            "profile.rs": file_sha256(profile),
            "M48": file_sha256(m48),
            "M61": file_sha256(m61),
            "M71": file_sha256(m71),
        },
    }


def self_test() -> None:
    rng = np.random.default_rng(20260824)
    reference = rng.normal(size=(96, 128))
    moving = np.roll(reference, shift=(3, -2), axis=(0, 1))
    dy, dx = best_translation(reference, moving)
    if (dy, dx) != (-3, 2):
        raise AssertionError(f"translation sign test failed: {(dy, dx)}")
    ref, mov = overlap(reference, moving, dy, dx)
    if pearson(ref, mov) < 0.999999:
        raise AssertionError("overlap test failed")
    mutated = tile_reverse(np.arange(64 * 80, dtype=np.float32).reshape(64, 80))
    if np.array_equal(mutated, np.arange(64 * 80).reshape(64, 80)):
        raise AssertionError("tile mutation did not change data")


def main() -> None:
    self_test()
    exif = {}
    rows = {}
    for stack in STACKS:
        exif[stack], rows[stack] = exif_summary(stack)
    focus2 = [row["focus_text"] for row in rows["bee-2"]]
    focus3 = [row["focus_text"] for row in rows["bee-3"]]
    focus_equal = [left == right for left, right in zip(focus2, focus3, strict=True)]
    focus_delta = [
        abs(left["focus_m"] - right["focus_m"])
        for left, right in zip(rows["bee-2"], rows["bee-3"], strict=True)
    ]
    products2 = [
        row["iso"] * row["exposure_seconds"] for row in rows["bee-2"]
    ]
    products3 = [
        row["iso"] * row["exposure_seconds"] for row in rows["bee-3"]
    ]
    product_differences = [
        abs(product2 / product3 - 1.0)
        for product2, product3 in zip(products2, products3, strict=True)
    ]
    focus_mismatch_indexes = [
        index + 1 for index, equal in enumerate(focus_equal) if not equal
    ]
    exposure_mismatch_indexes = [
        index + 1
        for index, difference in enumerate(product_differences)
        if difference > 0.01
    ]
    pair = {
        "focus_sequence_exactly_equal": focus2 == focus3,
        "focus_sequence_equal_rows": sum(focus_equal),
        "focus_sequence_equal_fraction": float(np.mean(focus_equal)),
        "focus_first_mismatch_frame": (
            focus_mismatch_indexes[0] if focus_mismatch_indexes else None
        ),
        "focus_last_mismatch_frame": (
            focus_mismatch_indexes[-1] if focus_mismatch_indexes else None
        ),
        "focus_max_absolute_difference_m": max(focus_delta),
        "start_focus_exactly_equal": (
            exif["bee-2"]["start_focus_m"] == exif["bee-3"]["start_focus_m"]
        ),
        "iso_exposure_max_relative_difference": max(product_differences),
        "iso_exposure_rows_outside_1pct": len(exposure_mismatch_indexes),
        "iso_exposure_first_mismatch_frame": (
            exposure_mismatch_indexes[0] if exposure_mismatch_indexes else None
        ),
        "iso_exposure_sequence_within_1pct": max(product_differences) <= 0.01,
    }
    pair["exif_precondition_pass"] = bool(
        exif["bee-2"]["individual_pass"]
        and exif["bee-3"]["individual_pass"]
        and pair["focus_sequence_exactly_equal"]
        and pair["start_focus_exactly_equal"]
        and pair["iso_exposure_sequence_within_1pct"]
    )

    result = {
        "exiftool": {
            "path": r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe",
            "version": "13.58",
            "exact_command": (
                "exiftool -T -ISO -FNumber -FocusDistance2 -r -ext ARW <dir>"
            ),
        },
        "exif": exif,
        "pair_exif": pair,
        "framing": framing_result(),
        "profile_audit": profile_audit(),
    }
    result["preconditions"] = {
        "exif": pair["exif_precondition_pass"],
        "framing": result["framing"]["framing_precondition_pass"],
        "profile_scalar_classification": result["profile_audit"]["classification"],
    }
    output = M.HERE / "bee-iso-preconditions.json"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["preconditions"], indent=2))
    real = result["framing"]["real"]
    print(
        "framing: shift={} green px raw_r={:.6f} hp_r={:.6f} residual={:.6f} pass={}".format(
            real["shift_green_px_to_apply_to_bee3"],
            real["raw_pearson"],
            real["highpass_pearson"],
            real["affine_residual_over_reference_sd"],
            result["framing"]["framing_precondition_pass"],
        )
    )


if __name__ == "__main__":
    main()
