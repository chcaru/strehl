from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import ImageCms

from common import (
    CHECKER,
    COMPARATOR,
    EXPECTED,
    ROOT,
    atomic_json,
    bounded_environment,
    byte_sha256,
    canonicalize_with_icc,
    comparator_command,
    image_census,
    linear_rec2020_icc,
    pixel_sha256,
    read_rgb16,
    sha256,
    tiff_tags,
    write_icc,
    write_rgb16,
)
from identity_adapter import build_state, final_output


CONTROL = ROOT / "controls"
WIDTH = EXPECTED["crop"]["width"]
HEIGHT = EXPECTED["crop"]["height"]
FRAME_COUNT = EXPECTED["frames"]
MARKERS = [
    (32, 32),
    (WIDTH - 33, 39),
    (47, HEIGHT - 41),
    (WIDTH - 52, HEIGHT - 49),
    (WIDTH // 2 - 317, HEIGHT // 2 + 211),
    (WIDTH // 2 + 401, HEIGHT // 2 - 293),
    (WIDTH // 3, HEIGHT // 3),
    (2 * WIDTH // 3, 2 * HEIGHT // 3),
]
PATCHES = [
    {"x": 128, "y": 128, "w": 256, "h": 192, "rgb": [8192, 16384, 24576]},
    {
        "x": WIDTH - 448,
        "y": 144,
        "w": 256,
        "h": 192,
        "rgb": [32768, 40960, 49152],
    },
    {
        "x": 176,
        "y": HEIGHT - 384,
        "w": 256,
        "h": 192,
        "rgb": [12288, 36864, 57344],
    },
]
VALUE_TOLERANCE_DN = 4
FULL_ARRAY_NEAR_FRACTION = 0.999


def witness_image() -> np.ndarray:
    y = np.arange(HEIGHT, dtype=np.uint32)[:, None]
    x = np.arange(WIDTH, dtype=np.uint32)[None, :]
    image = np.empty((HEIGHT, WIDTH, 3), dtype=np.uint16)
    seeds = [0x13579BDF, 0x2468ACE1, 0x10293847]
    for channel, seed in enumerate(seeds):
        hashed = (
            (x * np.uint32(73856093))
            ^ (y * np.uint32(19349663))
            ^ np.uint32(seed)
        )
        image[..., channel] = (4096 + hashed % 53248).astype(np.uint16)
    for patch in PATCHES:
        x0, y0 = patch["x"], patch["y"]
        image[y0 : y0 + patch["h"], x0 : x0 + patch["w"]] = np.array(
            patch["rgb"], dtype=np.uint16
        )
    for index, (x0, y0) in enumerate(MARKERS):
        image[y0 - 2 : y0 + 3, x0 - 2 : x0 + 3] = np.array(
            [1024 + index, 2048 + 2 * index, 3072 + 3 * index], dtype=np.uint16
        )
        image[y0, x0] = np.array(
            [62000 - 101 * index, 59000 - 137 * index, 56000 - 173 * index],
            dtype=np.uint16,
        )
    # Four asymmetric, coordinate-coded borders reject crop-then-resize.
    for row in range(8):
        image[row, :, 0] = ((np.arange(WIDTH) * 13 + 101 * row) % 65536).astype(
            np.uint16
        )
        image[HEIGHT - 1 - row, :, 1] = (
            (np.arange(WIDTH) * 29 + 173 * row + 7000) % 65536
        ).astype(np.uint16)
    for column in range(8):
        image[:, column, 2] = (
            (np.arange(HEIGHT) * 37 + 211 * column + 11000) % 65536
        ).astype(np.uint16)
        image[:, WIDTH - 1 - column, 0] = (
            (np.arange(HEIGHT) * 43 + 251 * column + 15000) % 65536
        ).astype(np.uint16)
    return image


def verify_witness(
    candidate: np.ndarray,
    expected: np.ndarray,
    candidate_icc_sha256: str | None,
    expected_icc_sha256: str,
) -> dict:
    errors: list[str] = []
    if candidate.dtype != np.uint16:
        errors.append(f"dtype {candidate.dtype}, expected uint16")
    if candidate.shape != expected.shape:
        errors.append(f"shape {candidate.shape}, expected {expected.shape}")
        return {"pass": False, "errors": errors}
    if candidate_icc_sha256 != expected_icc_sha256:
        errors.append(
            f"ICC {candidate_icc_sha256!r}, expected {expected_icc_sha256}"
        )
    diff = np.abs(candidate.astype(np.int32) - expected.astype(np.int32))
    marker_rows = []
    for index, (x, y) in enumerate(MARKERS):
        local = diff[y - 2 : y + 3, x - 2 : x + 3]
        maximum = int(local.max())
        marker_rows.append({"index": index, "x": x, "y": y, "max_abs_dn": maximum})
        if maximum > VALUE_TOLERANCE_DN:
            errors.append(f"marker {index} at {(x, y)} differs by {maximum} DN")
    border_points = []
    xs = np.linspace(0, WIDTH - 1, 257, dtype=np.intp)
    ys = np.linspace(0, HEIGHT - 1, 193, dtype=np.intp)
    samples = [
        diff[0:8, xs, :],
        diff[HEIGHT - 8 : HEIGHT, xs, :],
        diff[ys, 0:8, :],
        diff[ys, WIDTH - 8 : WIDTH, :],
    ]
    for index, sample in enumerate(samples):
        maximum = int(sample.max())
        border_points.append({"edge": index, "max_abs_dn": maximum})
        if maximum > VALUE_TOLERANCE_DN:
            errors.append(f"border {index} differs by {maximum} DN")
    patch_rows = []
    for index, patch in enumerate(PATCHES):
        x0, y0 = patch["x"], patch["y"]
        inner = candidate[
            y0 + 16 : y0 + patch["h"] - 16,
            x0 + 16 : x0 + patch["w"] - 16,
        ]
        target = np.array(patch["rgb"], dtype=np.float64)
        median = np.median(inner.reshape(-1, 3), axis=0)
        max_median_error = float(np.max(np.abs(median - target)))
        patch_rows.append(
            {
                "index": index,
                "median": median.tolist(),
                "target": target.tolist(),
                "max_median_error_dn": max_median_error,
            }
        )
        if max_median_error > VALUE_TOLERANCE_DN:
            errors.append(
                f"constant patch {index} median differs by {max_median_error} DN"
            )
    near_fraction = float(np.mean(np.max(diff, axis=2) <= VALUE_TOLERANCE_DN))
    if near_fraction < FULL_ARRAY_NEAR_FRACTION:
        errors.append(
            f"only {near_fraction:.9f} of coordinates are within "
            f"{VALUE_TOLERANCE_DN} DN; require {FULL_ARRAY_NEAR_FRACTION:.9f}"
        )
    return {
        "pass": not errors,
        "errors": errors,
        "marker_checks": marker_rows,
        "border_checks": border_points,
        "patch_checks": patch_rows,
        "full_array_near_fraction": near_fraction,
        "max_abs_dn": int(diff.max()),
    }


def transformed_plants(image: np.ndarray) -> dict[str, np.ndarray]:
    h, w, _ = image.shape
    x, y = np.meshgrid(
        np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32)
    )
    translated = cv2.remap(
        image,
        x + np.float32(0.25),
        y,
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    cx, cy = w * 0.5, h * 0.5
    scaled = cv2.remap(
        image,
        (cx + (x - cx) * np.float32(1.001)).astype(np.float32),
        (cy + (y - cy) * np.float32(1.001)).astype(np.float32),
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )
    rotated = np.rot90(image, 1).copy()
    cropped = cv2.resize(
        image[1:, 1:],
        (w, h),
        interpolation=cv2.INTER_LINEAR,
    )
    gamma = np.rint(
        np.power(image.astype(np.float64) / 65535.0, 1.0 / 2.2) * 65535.0
    ).clip(0, 65535).astype(np.uint16)
    matrix = image[..., [1, 0, 2]].copy()
    return {
        "translation-plus-0p25": translated,
        "scale-1p001": scaled,
        "orientation-90": rotated,
        "crop-one-resize": cropped,
        "wrong-gamma": gamma,
        "wrong-matrix": matrix,
    }


def run_comparator(inputs: list[Path], output: Path, work: Path) -> dict:
    command = comparator_command(inputs, output)
    help_run = subprocess.run(
        [str(COMPARATOR), "--help"],
        cwd=work,
        env=bounded_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    help_text = help_run.stdout + help_run.stderr
    (CONTROL / "focus-stack-help.txt").write_text(help_text, encoding="utf-8")
    run = subprocess.run(
        command,
        cwd=work,
        env=bounded_environment(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    (CONTROL / "focus-stack.stdout.txt").write_text(run.stdout, encoding="utf-8")
    (CONTROL / "focus-stack.stderr.txt").write_text(run.stderr, encoding="utf-8")
    payload = {
        "command": command,
        "cwd": str(work.resolve()),
        "returncode": run.returncode,
        "binary": str(COMPARATOR),
        "binary_sha256": sha256(COMPARATOR),
        "help_returncode": help_run.returncode,
        "help_sha256": byte_sha256(help_text.encode("utf-8")),
        "stdout_sha256": byte_sha256(run.stdout.encode("utf-8")),
        "stderr_sha256": byte_sha256(run.stderr.encode("utf-8")),
    }
    atomic_json(CONTROL / "focus-stack-command.json", payload)
    if run.returncode != 0 or not output.is_file():
        raise RuntimeError(
            f"focus-stack witness failed with return code {run.returncode}"
        )
    return payload


def adapter_controls(icc: bytes) -> dict:
    root = CONTROL / "adapter"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    height, width = 24, 32
    y, x = np.meshgrid(
        np.arange(height, dtype=np.uint16),
        np.arange(width, dtype=np.uint16),
        indexing="ij",
    )
    frames = []
    arrays = []
    for index in range(3):
        image = np.stack(
            [
                10000 + 17 * x + 31 * y + 200 * index,
                20000 + 13 * x + 23 * y + 150 * index,
                30000 + 11 * x + 19 * y + 100 * index,
            ],
            axis=2,
        ).astype(np.uint16)
        path = root / f"frame-{index}.tif"
        write_rgb16(path, image, icc, "M8 identity-adapter commissioning source")
        frames.append(path)
        arrays.append(image)
    state = CONTROL / "checker-state"
    build = build_state(frames, state, "identity-adapter-control", CONTROL / "blocks")
    lo = np.minimum.reduce(arrays)
    hi = np.maximum.reduce(arrays)
    null = arrays[1].copy()
    null_path = root / "null.tif"
    write_rgb16(null_path, null, icc, "M8 adapter null")
    null_result = final_output(state, null_path)
    if null_result["violations"] != 0:
        raise RuntimeError(f"adapter GREEN returned {null_result['violations']}")
    planted = null.copy()
    upper_coord = (5, 7, 0)
    lower_coord = (14, 19, 2)
    planted[upper_coord] = np.uint16(int(hi[upper_coord]) + 2)
    planted[lower_coord] = np.uint16(int(lo[lower_coord]) - 2)
    plant_path = root / "plant.tif"
    write_rgb16(plant_path, planted, icc, "M8 adapter two-sided plant")
    plant_result = final_output(state, plant_path)
    planted_rows = np.load(state / "m8-o-violations.npy")
    if (
        plant_result["violations"] != 2
        or plant_result["upper_violations"] != 1
        or plant_result["lower_violations"] != 1
    ):
        raise RuntimeError(f"adapter RED did not find exact 2/1/1: {plant_result}")
    improvement_path = root / "improvement.tif"
    write_rgb16(improvement_path, null, icc, "M8 adapter restored null")
    improvement_result = final_output(state, improvement_path)
    if improvement_result["violations"] != 0:
        raise RuntimeError("adapter improvement did not restore zero")
    payload = {
        "build": build,
        "green": null_result,
        "red": plant_result,
        "red_rows": [
            {
                name: (
                    int(row[name])
                    if np.issubdtype(planted_rows.dtype[name], np.integer)
                    else float(row[name])
                )
                for name in planted_rows.dtype.names
            }
            for row in planted_rows
        ],
        "improvement": improvement_result,
    }
    atomic_json(CONTROL / "adapter-controls.json", payload)
    return payload


def main() -> None:
    cv2.setNumThreads(6)
    if CONTROL.exists():
        shutil.rmtree(CONTROL)
    CONTROL.mkdir(parents=True)
    work = CONTROL / "work"
    input_dir = CONTROL / "input"
    work.mkdir()
    input_dir.mkdir()
    if sha256(COMPARATOR) != EXPECTED["comparator_sha256"]:
        raise RuntimeError("comparator binary changed after preregistration")
    if sha256(CHECKER) != EXPECTED["checker_sha256"]:
        raise RuntimeError("commissioned checker changed after preregistration")

    icc = linear_rec2020_icc()
    icc_record = write_icc(CONTROL / "linear-rec2020-v2.icc")
    profile = ImageCms.getOpenProfile(io.BytesIO(icc))
    description = ImageCms.getProfileDescription(profile).strip()
    if "Linear Rec.2020" not in description:
        raise RuntimeError(f"generated ICC did not validate: {description!r}")

    expected = witness_image()
    base = CONTROL / "geometry-domain-witness.tif"
    write_rgb16(
        base,
        expected,
        icc,
        "M8 full-size aperiodic coordinate and linear-domain witness",
    )
    input_paths = []
    for index in range(FRAME_COUNT):
        path = input_dir / f"{index:03d}-identity-witness.tif"
        os.link(base, path)
        input_paths.append(path)
    expected_pixel_hash = pixel_sha256(expected)
    for path in input_paths:
        if pixel_sha256(read_rgb16(path)) != expected_pixel_hash:
            raise RuntimeError(f"witness hardlink changed pixels: {path}")

    direct = CONTROL / "witness-direct.tif"
    command = run_comparator(input_paths, direct, work)
    canonical = CONTROL / "witness-canonical.tif"
    canonical_record = canonicalize_with_icc(direct, canonical, icc)
    actual = read_rgb16(canonical)
    tags = tiff_tags(canonical)
    green = verify_witness(actual, expected, tags["icc_sha256"], icc_record["sha256"])
    if not green["pass"]:
        raise RuntimeError("geometry/domain GREEN failed: " + "; ".join(green["errors"]))

    red = {}
    for name, plant in transformed_plants(actual).items():
        plant_icc = icc_record["sha256"]
        if name == "wrong-matrix":
            plant_icc = icc_record["sha256"]
        result = verify_witness(plant, expected, plant_icc, icc_record["sha256"])
        red[name] = result
        if result["pass"]:
            raise RuntimeError(f"geometry/domain RED plant {name} passed")
    wrong_profile = verify_witness(
        actual,
        expected,
        byte_sha256(icc[:-1] + bytes([icc[-1] ^ 1])),
        icc_record["sha256"],
    )
    red["wrong-profile"] = wrong_profile
    if wrong_profile["pass"]:
        raise RuntimeError("wrong-profile RED plant passed")
    improvement = verify_witness(
        actual, expected, tags["icc_sha256"], icc_record["sha256"]
    )
    if not improvement["pass"]:
        raise RuntimeError("restored identity improvement did not pass")

    adapter = adapter_controls(icc)
    payload = {
        "status": "PASS",
        "predicate_version": 1,
        "dimensions": [HEIGHT, WIDTH, 3],
        "source_count": FRAME_COUNT,
        "value_tolerance_dn": VALUE_TOLERANCE_DN,
        "full_array_near_fraction_required": FULL_ARRAY_NEAR_FRACTION,
        "icc": icc_record,
        "icc_description": description,
        "input_pixel_sha256": expected_pixel_hash,
        "input_file_sha256": sha256(base),
        "input_census": image_census(expected),
        "command": command,
        "canonicalization": canonical_record,
        "green": green,
        "red": red,
        "improvement": improvement,
        "adapter": adapter,
    }
    atomic_json(CONTROL / "PASS.json", payload)
    print(json.dumps({"status": "PASS", "path": str(CONTROL / "PASS.json")}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        CONTROL.mkdir(parents=True, exist_ok=True)
        atomic_json(
            CONTROL / "FAIL.json",
            {"status": "FAIL", "error": f"{type(error).__name__}: {error}"},
        )
        raise
