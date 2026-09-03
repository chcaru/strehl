from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import tifffile

from common import (
    OUT,
    SEED,
    WORK,
    Y_WEIGHTS,
    affine_fit,
    m1_tile,
    m2_eta,
    phase_translation,
    translate_fourier,
    write_json,
)


COMMON_SHAPE = (4608, 6912)
M1_TILE = 256
M2_TILE = 128


def output_luma(path: Path) -> np.ndarray:
    pixels = tifffile.memmap(path)
    if pixels.ndim != 3 or pixels.shape[2] != 3 or pixels.dtype != np.uint16:
        raise RuntimeError(f"{path}: expected HxWx3 uint16, found {pixels.shape} {pixels.dtype}")
    crop_h, crop_w = COMMON_SHAPE
    if pixels.shape[0] < crop_h or pixels.shape[1] < crop_w:
        raise RuntimeError(f"{path}: output smaller than frozen common crop")
    y0 = (pixels.shape[0] - crop_h) // 2
    x0 = (pixels.shape[1] - crop_w) // 2
    crop = pixels[y0 : y0 + crop_h, x0 : x0 + crop_w]
    luma = np.tensordot(crop.astype(np.float32), Y_WEIGHTS, axes=([2], [0]))
    luma *= np.float32(1.0 / 65535.0)
    return luma


def geometry(reference: np.ndarray, moving: np.ndarray) -> dict[str, object]:
    down = 8
    global_small = phase_translation(reference[::down, ::down], moving[::down, ::down])
    global_shift = (global_small[0] * down, global_small[1] * down)
    aligned = translate_fourier(moving, global_shift).astype(np.float32)
    local = []
    height, width = reference.shape
    for y in (height // 8, 5 * height // 8):
        for x in (width // 8, 5 * width // 8):
            side = min(height // 4, width // 4)
            ref_tile = reference[y : y + side, x : x + side]
            mov_tile = aligned[y : y + side, x : x + side]
            residual = phase_translation(ref_tile[::4, ::4], mov_tile[::4, ::4])
            local.append([residual[0] * 4, residual[1] * 4])
    rms = math.sqrt(
        sum(dy * dy + dx * dx for dy, dx in local) / max(1, len(local))
    )
    return {
        "global_translation_yx": list(global_shift),
        "local_residual_translations_yx": local,
        "non_translation_residual_rms_px": rms,
        "scale_disagreement_percent": None,
        "rotation_disagreement_deg": None,
        "scorecard_geometry_pass": rms <= 0.10,
        "aligned": aligned,
    }


def bootstrap_median(values: np.ndarray, *, draws: int = 10_000) -> dict[str, float | int]:
    values = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(SEED)
    medians = np.empty(draws, dtype=np.float64)
    for index in range(draws):
        sample = values[rng.integers(0, values.size, size=values.size)]
        medians[index] = np.median(sample)
    return {
        "draws": draws,
        "seed": SEED,
        "point": float(np.median(values)),
        "lcb95": float(np.quantile(medians, 0.05)),
        "ucb95": float(np.quantile(medians, 0.95)),
    }


def measure_m1(
    name: str,
    a_path: Path,
    b_path: Path,
    reference_path: Path,
) -> dict[str, object]:
    reference = np.load(reference_path, mmap_mode="r")
    a_raw = output_luma(a_path)
    b_raw = output_luma(b_path)
    geom_a = geometry(reference, a_raw)
    geom_b = geometry(reference, b_raw)
    a = geom_a.pop("aligned")
    b = geom_b.pop("aligned")
    readings = []
    for y in range(0, COMMON_SHAPE[0], M1_TILE):
        for x in range(0, COMMON_SHAPE[1], M1_TILE):
            readings.append(
                {
                    "y": y,
                    "x": x,
                    **m1_tile(
                        a[y : y + M1_TILE, x : x + M1_TILE],
                        b[y : y + M1_TILE, x : x + M1_TILE],
                        reference[y : y + M1_TILE, x : x + M1_TILE],
                    ),
                }
            )
    cutoffs = np.asarray([row["f_licensed"] for row in readings], dtype=np.float64)
    margins = np.asarray([row["S_25"] for row in readings], dtype=np.float64)
    gains = np.asarray([row["gain_median"] for row in readings], dtype=np.float64)
    return {
        "capture": name,
        "sites": len(readings),
        "geometry_a": geom_a,
        "geometry_b": geom_b,
        "f_licensed": bootstrap_median(cutoffs),
        "S_25": bootstrap_median(margins),
        "gain": bootstrap_median(gains),
        "endpoint_label": (
            "CENSORED_AT_0.25"
            if float(np.median(cutoffs)) >= 0.25
            else "MEASURED_BELOW_0.25"
        ),
        "formal_status": "UNMEASURED",
        "formal_reason": (
            "The registered bee dark/FPN floor is absent, the scorecard does not define "
            "the bee defocused-source eligibility denominator, and this is the native-RAW "
            "linear-sRGB diagnostic rather than the required common ProPhoto-TIFF arm."
        ),
        "readings": readings,
    }


def m2_arm(
    output_path: Path,
    reference_path: Path,
    sites: list[dict[str, object]],
) -> dict[str, object]:
    reference = np.load(reference_path, mmap_mode="r")
    moving = output_luma(output_path)
    geom = geometry(reference, moving)
    output = geom.pop("aligned")
    transfer = affine_fit(reference[::16, ::16], output[::16, ::16])
    rows = []
    for site in sites:
        y, x = int(site["y"]), int(site["x"])
        reading = m2_eta(
            output[y : y + M2_TILE, x : x + M2_TILE],
            reference[y : y + M2_TILE, x : x + M2_TILE],
            float(site["sigma_one"]),
        )
        rows.append({"y": y, "x": x, **reading})
    values = np.asarray([row["eta"] for row in rows], dtype=np.float64)
    return {
        "output": str(output_path),
        "reference": str(reference_path),
        "geometry": geom,
        "transfer": transfer,
        "eta": bootstrap_median(values),
        "sites": len(rows),
        "rows": rows,
    }


def measure_m2(
    name: str,
    first_output: Path,
    second_output: Path,
    first_reference: Path,
    second_reference: Path,
    sites: list[dict[str, object]],
) -> dict[str, object]:
    first = m2_arm(first_output, second_reference, sites)
    second = m2_arm(second_output, first_reference, sites)
    combined = np.asarray(
        [row["eta"] for row in first["rows"]]
        + [row["eta"] for row in second["rows"]],
        dtype=np.float64,
    )
    transfer_pass = all(
        0.995 <= arm["transfer"]["slope"] <= 1.005
        and abs(arm["transfer"]["intercept"]) <= 0.001
        for arm in (first, second)
    )
    geometry_pass = all(
        bool(arm["geometry"]["scorecard_geometry_pass"]) for arm in (first, second)
    )
    summary = bootstrap_median(combined)
    return {
        "capture": name,
        "arms": [first, second],
        "eta": summary,
        "absolute_bar": 1.10,
        "diagnostic_bar_pass": summary["point"] <= 1.10,
        "transfer_guard_pass": transfer_pass,
        "geometry_guard_pass": geometry_pass,
        "formal_status": "UNMEASURED",
        "formal_reason": (
            "M1 and common-input transfer qualification are prerequisites. The scorecard "
            "also omits the aggregation rule for eta; median plus a one-sided site bootstrap "
            "is reported without silently declaring it the registered statistic."
        ),
    }


def main() -> int:
    renders = OUT / "renders"
    cache = WORK / "input-cache"
    site_manifest = __import__("json").loads(
        (OUT / "SITE-MANIFEST.json").read_text(encoding="utf-8")
    )
    required = [
        renders / f"{name}.tiff"
        for name in (
            "m1-bright-a12",
            "m1-bright-b12",
            "m1-second-a12",
            "m1-second-b12",
            "m2-bright-first16",
            "m2-bright-second16",
            "m2-second-first16",
            "m2-second-second16",
        )
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"missing score renders: {missing}")

    result = {
        "m1": [
            measure_m1(
                "bee-repeat-bright",
                renders / "m1-bright-a12.tiff",
                renders / "m1-bright-b12.tiff",
                cache / "bright_reference8.npy",
            ),
            measure_m1(
                "bee-repeat-second-light",
                renders / "m1-second-a12.tiff",
                renders / "m1-second-b12.tiff",
                cache / "second_reference8.npy",
            ),
        ],
        "m2": [
            measure_m2(
                "bee-repeat-bright",
                renders / "m2-bright-first16.tiff",
                renders / "m2-bright-second16.tiff",
                cache / "bright_first16.npy",
                cache / "bright_second16.npy",
                site_manifest["m2"]["bright_sites"],
            ),
            measure_m2(
                "bee-repeat-second-light",
                renders / "m2-second-first16.tiff",
                renders / "m2-second-second16.tiff",
                cache / "second_first16.npy",
                cache / "second_second16.npy",
                site_manifest["m2"]["second_sites"],
            ),
        ],
        "licensing": (
            "No frequency above 0.25 cycles/native-pixel was inspected or reported. "
            "Endpoint results are censored at 0.25."
        ),
    }
    write_json(OUT / "MEASUREMENTS.json", result)
    for row in result["m1"]:
        print(
            row["capture"],
            "f=", row["f_licensed"]["point"],
            "S25=", row["S_25"]["point"],
            "formal=", row["formal_status"],
        )
    for row in result["m2"]:
        print(
            row["capture"],
            "eta=", row["eta"]["point"],
            "diagnostic_pass=", row["diagnostic_bar_pass"],
            "formal=", row["formal_status"],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
