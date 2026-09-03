from __future__ import annotations

import concurrent.futures
import json
import math
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rawpy
from scipy.ndimage import shift as spatial_shift

from common import (
    OUT,
    SCORECARD,
    SEED,
    WORK,
    Y_WEIGHTS,
    band_power,
    bandpass,
    phase_translation,
    robust_sigma,
    sha256,
    write_json,
)


MACRO = Path(r"D:\personal\macro")
BEE = MACRO / "requests" / "12-bee-iso-var-no-bracket-32-repeat-diff-light"
DARKS = MACRO / "requests" / "6-11-extended-dark-frames"
PAPER = MACRO / "requests" / "10-paper-iso-var"
COMMON_SHAPE = (4608, 6912)
M1_TILE = 256
M2_TILE = 128

GROUPS = {
    "bright_first16": list(range(328, 344)),
    "bright_second16": list(range(344, 360)),
    "bright_reference8": list(range(328, 336)),
    "second_first16": list(range(584, 600)),
    "second_second16": list(range(600, 616)),
    "second_reference8": list(range(584, 592)),
}

CAPTURES = {
    "calibration-grid-sw1": MACRO
    / "requests"
    / "30-calibration-grid"
    / "calibration-grid-1-sw1-cpl",
    "calibration-grid-1-sw4": MACRO
    / "requests"
    / "30-calibration-grid"
    / "calibration-grid-1-sw4-cpl",
    "calibration-grid-2-sw4": MACRO
    / "requests"
    / "30-calibration-grid"
    / "calibration-grid-2-sw4-cpl",
    "calibration-grid-1-sw10": MACRO
    / "requests"
    / "30-calibration-grid"
    / "calibration-grid-1-sw10-cpl",
    "calibration-grid-2-sw10": MACRO
    / "requests"
    / "30-calibration-grid"
    / "calibration-grid-2-sw10-cpl",
    "fabric-f5.6": MACRO
    / "requests"
    / "7-aperture-pairs"
    / "fabric-weave-f5.6-sw5-cpl",
    "fabric-f8": MACRO
    / "requests"
    / "7-aperture-pairs"
    / "fabric-weave-f8-sw5-cpl",
    "fabric-f11": MACRO
    / "requests"
    / "7-aperture-pairs"
    / "fabric-weave-f11-sw5-cpl",
    "ruler-f5.6": MACRO
    / "requests"
    / "8-tilted-planar"
    / "ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl",
    "ruler-f8": MACRO
    / "requests"
    / "8-tilted-planar"
    / "ruler-incline-ang10.26deg-inches-f8-sw7-cpl",
    "ruler-f11": MACRO
    / "requests"
    / "8-tilted-planar"
    / "ruler-incline-ang10.26deg-inches-f11-sw7-cpl",
    "bee-repeat": BEE,
    "paper": PAPER,
    "darks": DARKS,
    "razor": MACRO
    / "requests"
    / "19-razor-edge"
    / "horizontal-flat"
    / "razor-edge-horizontal-flat-sw4-f5.6-cpl",
    "duck-tape": MACRO / "duck-tape-side-layers-cpl",
    "chia": MACRO / "chia-seeds-cpl",
    "flower-fern": MACRO / "flower-bud-with-background-fern-cpl",
    "coffee-bubbles": MACRO / "coffee-bubbles",
    "medication-pill": MACRO / "medication-pill-cpl",
    "foam": MACRO / "foam",
    "battery": MACRO
    / "requests"
    / "misc-diagnostic"
    / "flat-round-3V-battery-cpl"
    / "flat-round-3V-battery-iso100-sw4-cpl",
    "salt": MACRO / "maldon-sea-salt-cpl",
    "angled-ruler": MACRO / "highly-angled-ruler-mm-cpl",
    "bee-1": MACRO / "bee-1-cpl",
    "coffee-bean": MACRO / "coffee-bean",
    "113MSDCF": MACRO / "113MSDCF",
}


def frame(number: int) -> Path:
    return BEE / f"DSC{number:05d}.ARW"


def decode_luma(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    with rawpy.imread(str(path)) as raw:
        rgb = raw.postprocess(
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD,
            use_camera_wb=True,
            use_auto_wb=False,
            output_color=rawpy.ColorSpace.sRGB,
            output_bps=16,
            user_flip=0,
            no_auto_bright=True,
            no_auto_scale=False,
            adjust_maximum_thr=0.0,
            gamma=(1.0, 1.0),
            highlight_mode=rawpy.HighlightMode.Clip,
        )
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise RuntimeError(f"{path.name}: unexpected postprocess shape {rgb.shape}")
        height, width = rgb.shape[:2]
        crop_h, crop_w = COMMON_SHAPE
        if height < crop_h or width < crop_w:
            raise RuntimeError(f"{path.name}: {rgb.shape} smaller than {COMMON_SHAPE}")
        y0 = (height - crop_h) // 2
        x0 = (width - crop_w) // 2
        crop = rgb[y0 : y0 + crop_h, x0 : x0 + crop_w]
        luma = np.tensordot(crop.astype(np.float32), Y_WEIGHTS, axes=([2], [0]))
        luma *= np.float32(1.0 / 65535.0)
        clipped = np.any(crop >= 65534, axis=2)
        metadata = {
            "postprocess_shape": list(rgb.shape),
            "crop_yxhw": [y0, x0, crop_h, crop_w],
            "raw_visible_shape": list(raw.raw_image_visible.shape),
            "raw_pattern": raw.raw_pattern.tolist(),
            "black_levels": list(raw.black_level_per_channel),
            "white_level": int(raw.white_level),
            "camera_whitebalance": list(raw.camera_whitebalance),
            "rgb_xyz_matrix": np.asarray(raw.rgb_xyz_matrix).tolist(),
        }
    return luma, clipped, metadata


def exif_dump(paths: list[Path], output: Path) -> None:
    command = ["exiftool", "-json", "-G", "-a", "-s", *map(str, paths)]
    process = subprocess.run(command, text=True, capture_output=True)
    if process.returncode:
        raise RuntimeError(f"ExifTool failed: {process.stderr}")
    output.write_text(process.stdout, encoding="utf-8")


def exif_rows(directory: Path) -> list[dict[str, object]]:
    command = [
        "exiftool",
        "-json",
        "-n",
        "-ISO",
        "-ExposureTime",
        "-FNumber",
        "-FileName",
        str(directory / "*.ARW"),
    ]
    process = subprocess.run(command, text=True, capture_output=True)
    if process.returncode:
        raise RuntimeError(f"ExifTool failed: {process.stderr}")
    return json.loads(process.stdout)


def capture_inventory() -> dict[str, object]:
    result = {}
    for name, directory in CAPTURES.items():
        files = sorted(
            (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".arw"),
            key=lambda path: path.name.lower(),
        ) if directory.exists() else []
        result[name] = {
            "path": str(directory),
            "exists": directory.exists(),
            "arw_count": len(files),
            "first": files[0].name if files else None,
            "last": files[-1].name if files else None,
            "bytes": sum(path.stat().st_size for path in files),
        }
    return result


def tree_census(directory: Path) -> dict[str, int]:
    files = [path for path in directory.rglob("*") if path.is_file()]
    return {
        "files": len(files),
        "arw": sum(path.suffix.lower() == ".arw" for path in files),
        "bytes": sum(path.stat().st_size for path in files),
    }


def hash_record(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "path": str(path),
        "size": stat.st_size,
        "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256(path),
    }


def all_sites(tile: int) -> list[dict[str, int]]:
    height, width = COMMON_SHAPE
    return [
        {"y": y, "x": x, "height": tile, "width": tile}
        for y in range(0, height, tile)
        for x in range(0, width, tile)
    ]


def select_m2_sites(
    selection_image: np.ndarray,
    clipped: np.ndarray,
) -> list[dict[str, float | int]]:
    rows = []
    for site in all_sites(M2_TILE):
        y, x = site["y"], site["x"]
        if np.any(clipped[y : y + M2_TILE, x : x + M2_TILE]):
            continue
        tile = selection_image[y : y + M2_TILE, x : x + M2_TILE]
        rows.append({**site, "selection_power": band_power(tile, 0.02, 0.08)})
    if len(rows) < 64:
        raise RuntimeError(f"only {len(rows)} unclipped M2 candidates")
    threshold = float(np.quantile([row["selection_power"] for row in rows], 0.25))
    selected = [row for row in rows if row["selection_power"] <= threshold]
    if len(selected) < 16:
        raise RuntimeError(f"only {len(selected)} lowest-quartile M2 sites")
    return selected


def sigma_one_for_sites(
    numbers: list[int],
    sites: list[dict[str, float | int]],
    shifts: dict[int, tuple[float, float]],
) -> list[float]:
    readings: list[list[float]] = [[] for _ in sites]
    for left, right in zip(numbers[0::2], numbers[1::2]):
        a, _, _ = decode_luma(frame(left))
        b, _, _ = decode_luma(frame(right))
        a = spatial_shift(a, shifts[left], order=1, mode="constant", cval=0.0, prefilter=False)
        b = spatial_shift(b, shifts[right], order=1, mode="constant", cval=0.0, prefilter=False)
        for index, site in enumerate(sites):
            y, x = int(site["y"]), int(site["x"])
            difference = (
                a[y : y + M2_TILE, x : x + M2_TILE]
                - b[y : y + M2_TILE, x : x + M2_TILE]
            )
            sigma = robust_sigma(bandpass(difference, 0.15, 0.35)) / math.sqrt(2.0)
            readings[index].append(sigma)
    return [float(np.median(values)) for values in readings]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cache = WORK / "input-cache"
    cache.mkdir(parents=True, exist_ok=True)

    used_numbers = sorted({number for numbers in GROUPS.values() for number in numbers})
    used_paths = [frame(number) for number in used_numbers]
    missing = [str(path) for path in used_paths if not path.exists()]
    if missing:
        raise RuntimeError(f"missing registered bee frames: {missing}")

    exif_path = OUT / "exif-bee.json"
    exif_dump(used_paths, exif_path)

    print("hashing 64 registered bee inputs with 8 workers")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        file_records = list(pool.map(hash_record, used_paths))

    sums: dict[str, np.ndarray] = {}
    counts = Counter()
    clipped_by_light: dict[str, np.ndarray] = {}
    stability: dict[str, list[np.ndarray]] = {"bright": [], "second": []}
    reference_crops: dict[str, np.ndarray] = {}
    frame_shifts: dict[int, tuple[float, float]] = {}
    decode_metadata = None
    memberships: dict[int, list[str]] = {
        number: [name for name, values in GROUPS.items() if number in values]
        for number in used_numbers
    }
    print("decoding registered bee inputs for input-only sites")
    for number in used_numbers:
        image, clipped, metadata = decode_luma(frame(number))
        decode_metadata = decode_metadata or metadata
        light = "bright" if number < 500 else "second"
        center_y = (image.shape[0] - 512) // 2
        center_x = (image.shape[1] - 512) // 2
        center = image[center_y : center_y + 512, center_x : center_x + 512].copy()
        if light not in reference_crops:
            reference_crops[light] = center
        shift = phase_translation(reference_crops[light], center)
        frame_shifts[number] = shift
        aligned_image = spatial_shift(
            image,
            shift,
            order=1,
            mode="constant",
            cval=0.0,
            prefilter=False,
        ).astype(np.float32, copy=False)
        aligned_clipped = spatial_shift(
            clipped.astype(np.uint8),
            shift,
            order=0,
            mode="constant",
            cval=1,
            prefilter=False,
        ).astype(bool)
        if light not in clipped_by_light:
            clipped_by_light[light] = np.zeros(image.shape, dtype=bool)
        clipped_by_light[light] |= aligned_clipped
        stability[light].append(center)
        for name in memberships[number]:
            if name not in sums:
                sums[name] = np.zeros(image.shape, dtype=np.float32)
            sums[name] += aligned_image
            counts[name] += 1
        print(f"  {number} decoded", flush=True)

    means = {}
    for name, total in sums.items():
        means[name] = total / np.float32(counts[name])
        np.save(cache / f"{name}.npy", means[name])
    bright_all = 0.5 * (means["bright_first16"] + means["bright_second16"])
    second_all = 0.5 * (means["second_first16"] + means["second_second16"])
    np.save(cache / "bright_all32.npy", bright_all)
    np.save(cache / "second_all32.npy", second_all)

    m2_bright = select_m2_sites(second_all, clipped_by_light["bright"])
    m2_second = select_m2_sites(bright_all, clipped_by_light["second"])
    print(f"M2 sites: bright={len(m2_bright)} second={len(m2_second)}")
    bright_sigma = sigma_one_for_sites(
        list(range(328, 360)), m2_bright, frame_shifts
    )
    second_sigma = sigma_one_for_sites(
        list(range(584, 616)), m2_second, frame_shifts
    )
    for site, sigma in zip(m2_bright, bright_sigma):
        site["sigma_one"] = sigma
    for site, sigma in zip(m2_second, second_sigma):
        site["sigma_one"] = sigma

    stability_rows = {}
    for light, frames in stability.items():
        reference = frames[0]
        shifts = [phase_translation(reference, image) for image in frames]
        ratios = [
            math.log(
                max(band_power(image, 0.18, 0.35), 1e-30)
                / max(band_power(image, 0.05, 0.15), 1e-30)
            )
            for image in frames
        ]
        stability_rows[light] = {
            "shifts_yx": [list(shift) for shift in shifts],
            "maximum_abs_shift": max(max(abs(v) for v in shift) for shift in shifts),
            "log_high_mid": ratios,
            "maximum_deviation_from_median": max(
                abs(value - float(np.median(ratios))) for value in ratios
            ),
        }

    dark_rows = exif_rows(DARKS)
    paper_rows = exif_rows(PAPER)
    dark_groups = Counter(
        (
            row.get("ISO"),
            row.get("ExposureTime"),
            row.get("FNumber"),
        )
        for row in dark_rows
    )
    paper_groups = Counter(
        (
            row.get("ISO"),
            row.get("ExposureTime"),
            row.get("FNumber"),
        )
        for row in paper_rows
    )

    colour_candidates = sorted(
        str(path)
        for path in MACRO.rglob("*")
        if any(
            token in path.name.lower()
            for token in ("colorchecker", "colourchecker", "gray-card", "grey-card")
        )
    )
    inventory = capture_inventory()
    requests_census = tree_census(MACRO / "requests")

    rawpy_binary = Path(rawpy._rawpy.__file__)
    input_manifest = {
        "scorecard_sha256": sha256(SCORECARD),
        "source_tree_read_only": True,
        "requests_census": requests_census,
        "capture_inventory": inventory,
        "used_files": file_records,
        "exif_dump": {
            "path": str(exif_path),
            "sha256": sha256(exif_path),
            "command": "exiftool -json -G -a -s <64 registered bee ARWs>",
        },
        "decoder": {
            "implementation": "rawpy/LibRaw, independent of strehl/rawler",
            "rawpy_version": rawpy.__version__,
            "libraw_version": getattr(rawpy, "libraw_version", None),
            "extension_path": str(rawpy_binary),
            "extension_sha256": sha256(rawpy_binary),
            "settings": {
                "demosaic_algorithm": "AHD",
                "camera_white_balance": True,
                "auto_white_balance": False,
                "output_color": "linear sRGB",
                "output_bps": 16,
                "user_flip": 0,
                "no_auto_bright": True,
                "no_auto_scale": False,
                "adjust_maximum_thr": 0.0,
                "gamma": [1.0, 1.0],
                "highlight_mode": "Clip",
                "xmp": "not read",
                "sharpening": "off",
                "denoising": "off",
                "lens_correction": "off",
            },
            "first_frame_metadata": decode_metadata,
        },
        "m1_floor_preflight": {
            "bee_exposure": [100, 1.6, 5.6],
            "matching_dark_count": dark_groups.get((100, 1.6, 5.6), 0),
            "matching_flat_count": paper_groups.get((100, 1.6, 5.6), 0),
            "scorecard_consequence": (
                "M1/M9 formal bee truth is UNMEASURED when no matching dark/FPN map exists"
            ),
        },
        "m7_preflight": {
            "traceable_target_candidates": colour_candidates,
            "candidate_count": len(colour_candidates),
        },
        "colour_space_conflict": {
            "common_contract": "linear ProPhoto RGB D50",
            "M1_luma_coefficients": [0.2627, 0.6780, 0.0593],
            "coefficient_identity": "Rec.2020/D65 luminance coefficients, not ProPhoto/D50",
        },
        "exif_group_census": {
            "dark": [
                {"iso": key[0], "exposure": key[1], "f_number": key[2], "count": count}
                for key, count in sorted(dark_groups.items(), key=lambda item: str(item[0]))
            ],
            "paper": [
                {"iso": key[0], "exposure": key[1], "f_number": key[2], "count": count}
                for key, count in sorted(paper_groups.items(), key=lambda item: str(item[0]))
            ],
        },
    }
    write_json(OUT / "INPUT-MANIFEST.json", input_manifest)

    site_manifest = {
        "seed": SEED,
        "output_independence": "All coordinates and sigma estimates came only from common inputs.",
        "common_crop_shape": list(COMMON_SHAPE),
        "input_crop": decode_metadata["crop_yxhw"],
        "m1": {
            "tile": M1_TILE,
            "tukey_alpha": 0.25,
            "sites": all_sites(M1_TILE),
            "formal_status": (
                "Sites frozen, but bee eligibility/noise floor is blocked by absent matching "
                "dark/FPN calibration and the scorecard does not define a bee defocused source."
            ),
        },
        "m2": {
            "tile": M2_TILE,
            "selection_band": [0.02, 0.08],
            "evaluation_band": [0.15, 0.35],
            "selection_rule": (
                "lowest quartile of opposite-light input-only structure; any site clipped in "
                "the scored light is excluded"
            ),
            "bright_sites": m2_bright,
            "second_sites": m2_second,
            "sigma_one": (
                "median robust bandpassed sigma across 16 disjoint consecutive frame pairs, "
                "divided by sqrt(2)"
            ),
        },
        "input_stability": stability_rows,
        "input_registration": {
            "method": (
                "phase correlation on an input-only 512x512 centre crop; full luma translated "
                "with fixed bilinear interpolation before site selection and temporal sigma"
            ),
            "shifts_yx_by_frame": {
                f"DSC{number:05d}.ARW": list(shift)
                for number, shift in sorted(frame_shifts.items())
            },
        },
    }
    write_json(OUT / "SITE-MANIFEST.json", site_manifest)
    print(f"wrote {OUT / 'INPUT-MANIFEST.json'}")
    print(f"wrote {OUT / 'SITE-MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
