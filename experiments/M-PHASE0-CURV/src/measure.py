"""Decode the frozen M-PHASE0-CURV roster into site response curves.

All capture paths are read-only.  The only products are compact response
arrays and manifests below this lane's ``out`` directory.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import rawpy
from scipy import ndimage

import curvlib as C


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
VISIBLE_SHAPE = (4688, 7028)
VISIBLE_PATTERN = np.array([[0, 1], [3, 2]], dtype=np.uint8)
BLACK = 512
USABLE_WHITE = 15360
NX = 31
NY = 21

STACKS: dict[str, dict[str, object]] = {
    "primary-f5p6": {
        "path": Path(
            r"D:\personal\macro\requests\8-tilted-planar"
            r"\ruler-incline-ang10.26deg-inches-f5.6-sw7-cpl"
        ),
        "role": "primary",
        "expected_frames": 120,
        "aperture": 5.6,
    },
    "aperture-f8": {
        "path": Path(
            r"D:\personal\macro\requests\8-tilted-planar"
            r"\ruler-incline-ang10.26deg-inches-f8-sw7-cpl"
        ),
        "role": "aperture",
        "expected_frames": 85,
        "aperture": 8.0,
    },
    "aperture-f11": {
        "path": Path(
            r"D:\personal\macro\requests\8-tilted-planar"
            r"\ruler-incline-ang10.26deg-inches-f11-sw7-cpl"
        ),
        "role": "aperture",
        "expected_frames": 65,
        "aperture": 11.0,
    },
    "target-flat-ruler": {
        "path": Path(r"D:\personal\macro\flat-on-ruler-cpl"),
        "role": "independent-target",
        "expected_frames": 79,
        "aperture": 5.6,
    },
    "target-dime": {
        "path": Path(r"D:\personal\macro\dime-flat-narrow-slices-cpl"),
        "role": "independent-target",
        "expected_frames": 207,
        "aperture": 5.6,
    },
    "grid-1-sw1": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw1-cpl"
        ),
        "role": "diagnostic-target",
        "expected_frames": 91,
        "aperture": 5.6,
    },
    "grid-1-sw4": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw4-cpl"
        ),
        "role": "diagnostic-target",
        "expected_frames": 55,
        "aperture": 5.6,
    },
    "grid-1-sw10": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-1-sw10-cpl"
        ),
        "role": "diagnostic-target",
        "expected_frames": 23,
        "aperture": 5.6,
    },
    "grid-2-sw4": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-2-sw4-cpl"
        ),
        "role": "diagnostic-target",
        "expected_frames": 46,
        "aperture": 5.6,
    },
    "grid-2-sw10": {
        "path": Path(
            r"D:\personal\macro\requests\30-calibration-grid"
            r"\calibration-grid-2-sw10-cpl"
        ),
        "role": "diagnostic-target",
        "expected_frames": 27,
        "aperture": 5.6,
    },
}


def natural_key(path: Path) -> tuple[object, ...]:
    return tuple(
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", path.name)
    )


def exif_manifest(directory: Path) -> dict[str, dict[str, object]]:
    command = [
        "exiftool",
        "-json",
        "-n",
        "-FileName",
        "-FocusDistance2",
        "-FNumber",
        "-ISO",
        "-ExposureTime",
        "-DateTimeOriginal",
        "-ext",
        "ARW",
        str(directory),
    ]
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    rows = json.loads(completed.stdout)
    return {str(row["FileName"]): row for row in rows}


def ordered_files(config: dict[str, object]) -> tuple[list[Path], list[dict[str, object]]]:
    directory = Path(config["path"])
    files = sorted(directory.glob("*.ARW"), key=natural_key)
    expected = int(config["expected_frames"])
    if len(files) != expected:
        raise RuntimeError(f"{directory}: expected {expected} ARWs, found {len(files)}")
    metadata = exif_manifest(directory)
    try:
        rows = [metadata[p.name] for p in files]
        distance = np.asarray([float(row["FocusDistance2"]) for row in rows])
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"{directory}: incomplete FocusDistance2 metadata") from exc
    if not np.all(np.isfinite(distance)) or float(np.ptp(distance)) <= 0.0:
        raise RuntimeError(f"{directory}: focus distance does not span a bracket")
    if np.all(np.diff(distance) <= 1e-12):
        files.reverse()
        rows.reverse()
        distance = distance[::-1]
    if np.any(np.diff(distance) < -1e-12):
        raise RuntimeError(f"{directory}: filename focus-distance order is not monotonic")
    return files, rows


def fixed_sites() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    width = VISIBLE_SHAPE[1]
    height = VISIBLE_SHAPE[0]
    target_x = np.linspace(0.06, 0.94, NX) * width
    target_y = np.linspace(0.08, 0.92, NY) * height
    # The paired G1/G2 2x2 averages have mean raw-sensor centres at
    # (4*j+1.5, 4*i+1.5).
    ix = np.clip(np.rint((target_x - 1.5) / 4.0).astype(int), 0, width // 4 - 1)
    iy = np.clip(np.rint((target_y - 1.5) / 4.0).astype(int), 0, height // 4 - 1)
    gx, gy = np.meshgrid(ix, iy)
    x_sensor = 4.0 * gx.ravel() + 1.5
    y_sensor = 4.0 * gy.ravel() + 1.5
    return gx.ravel(), gy.ravel(), x_sensor, y_sensor


def decode_green_planes(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.copy()
        pattern = raw.raw_colors_visible[:2, :2].copy()
        black = tuple(int(v) for v in raw.black_level_per_channel)
        white = int(raw.white_level)
    if visible.shape != VISIBLE_SHAPE:
        raise RuntimeError(f"{path}: visible shape {visible.shape}, expected {VISIBLE_SHAPE}")
    if not np.array_equal(pattern, VISIBLE_PATTERN):
        raise RuntimeError(f"{path}: visible CFA {pattern.tolist()} is not registered RGGB")
    if black != (BLACK, BLACK, BLACK, BLACK):
        raise RuntimeError(f"{path}: black levels {black}, expected four {BLACK}s")
    if white != 16383:
        raise RuntimeError(f"{path}: rawpy container white {white}, expected 16383")
    # Channel IDs 1 and 3 are the two greens in rawpy's RGBG convention.
    g1_raw = visible[0::2, 1::2]
    g2_raw = visible[1::2, 0::2]
    return g1_raw, g2_raw


def plane_observables(
    raw_green: np.ndarray,
    sample_x: np.ndarray,
    sample_y: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    plane = C.area_average_2x2(raw_green.astype(np.float32) - BLACK)
    response, level = C.focus_response(plane, box=17)
    clipped = C.area_average_2x2((raw_green >= USABLE_WHITE).astype(np.float32))
    clip_fraction = ndimage.uniform_filter(clipped, size=17, mode="reflect")
    return (
        response[sample_y, sample_x],
        level[sample_y, sample_x],
        clip_fraction[sample_y, sample_x],
    )


def measure_stack(stack_id: str, force: bool = False) -> dict[str, object]:
    config = STACKS[stack_id]
    npz_path = OUT / f"{stack_id}-responses.npz"
    json_path = OUT / f"{stack_id}-measure.json"
    if (npz_path.exists() or json_path.exists()) and not force:
        raise FileExistsError(f"{stack_id}: output exists; pass --force to replace it")
    files, exif_rows = ordered_files(config)
    sample_x, sample_y, x_sensor, y_sensor = fixed_sites()
    nframe = len(files)
    nsite = len(sample_x)
    arrays = {
        name: np.empty((nframe, nsite), dtype=np.float32)
        for name in (
            "response_g1",
            "response_g2",
            "mean_g1",
            "mean_g2",
            "clip_g1",
            "clip_g2",
        )
    }
    started = time.time()
    for frame, path in enumerate(files):
        g1, g2 = decode_green_planes(path)
        r1, m1, c1 = plane_observables(g1, sample_x, sample_y)
        r2, m2, c2 = plane_observables(g2, sample_x, sample_y)
        arrays["response_g1"][frame] = r1
        arrays["response_g2"][frame] = r2
        arrays["mean_g1"][frame] = m1
        arrays["mean_g2"][frame] = m2
        arrays["clip_g1"][frame] = c1
        arrays["clip_g2"][frame] = c2
        if frame == 0 or (frame + 1) % 10 == 0 or frame + 1 == nframe:
            elapsed = time.time() - started
            rate = (frame + 1) / max(elapsed, 1e-9)
            print(
                f"{stack_id}: {frame + 1}/{nframe}, {rate:.2f} frame/s",
                file=sys.stderr,
                flush=True,
            )

    np.savez_compressed(
        npz_path,
        **arrays,
        x_sensor=x_sensor.astype(np.float64),
        y_sensor=y_sensor.astype(np.float64),
        grid_x=sample_x.reshape(NY, NX).astype(np.int16),
        grid_y=sample_y.reshape(NY, NX).astype(np.int16),
    )
    focus_distance = [float(row["FocusDistance2"]) for row in exif_rows]
    manifest = {
        "schema": 1,
        "stack_id": stack_id,
        "role": config["role"],
        "capture_path": str(config["path"]),
        "response_npz": str(npz_path.relative_to(ROOT)).replace("\\", "/"),
        "response_npz_sha256": C.sha256_file(npz_path),
        "frames": nframe,
        "sites": nsite,
        "grid": [NX, NY],
        "active_width": VISIBLE_SHAPE[1],
        "active_height": VISIBLE_SHAPE[0],
        "black": BLACK,
        "usable_white": USABLE_WHITE,
        "aperture": float(config["aperture"]),
        "focus_distance_first_m": focus_distance[0],
        "focus_distance_last_m": focus_distance[-1],
        "focus_distance_nondecreasing": bool(
            np.all(np.diff(np.asarray(focus_distance)) >= -1e-12)
        ),
        "elapsed_seconds": time.time() - started,
        "files": [
            {
                "name": path.name,
                "bytes": path.stat().st_size,
                "mtime_ns": path.stat().st_mtime_ns,
                "focus_distance_m": float(row["FocusDistance2"]),
                "f_number": float(row["FNumber"]),
                "iso": int(row["ISO"]),
                "exposure_seconds": float(row["ExposureTime"]),
            }
            for path, row in zip(files, exif_rows)
        ],
    }
    json_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stack",
        action="append",
        choices=sorted(STACKS),
        help="stack ID; repeat to run several (default: all)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(STACKS))
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    selected = args.stack or list(STACKS)
    results = [measure_stack(stack_id, force=args.force) for stack_id in selected]
    print(
        json.dumps(
            [
                {
                    "stack_id": row["stack_id"],
                    "frames": row["frames"],
                    "seconds": row["elapsed_seconds"],
                    "sha256": row["response_npz_sha256"],
                }
                for row in results
            ],
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
