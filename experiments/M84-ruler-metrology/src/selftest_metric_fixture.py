"""Recover metric-plane quantities from M84's independent synthetic fixture."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


def normalise_points(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    centre = np.mean(points, axis=0)
    centred = points - centre
    rms = math.sqrt(float(np.mean(np.sum(centred**2, axis=1))))
    scale = math.sqrt(2.0) / rms
    transform = np.array(
        [
            [scale, 0.0, -scale * centre[0]],
            [0.0, scale, -scale * centre[1]],
            [0.0, 0.0, 1.0],
        ]
    )
    homogeneous = np.column_stack([points, np.ones(points.shape[0])])
    normalised = (transform @ homogeneous.T).T
    return normalised[:, :2], transform


def fit_homography(source: np.ndarray, destination: np.ndarray) -> np.ndarray:
    source_n, source_transform = normalise_points(source)
    destination_n, destination_transform = normalise_points(destination)
    rows = []
    for (x, y), (u, v) in zip(source_n, destination_n, strict=True):
        rows.append([-x, -y, -1.0, 0.0, 0.0, 0.0, u * x, u * y, u])
        rows.append([0.0, 0.0, 0.0, -x, -y, -1.0, v * x, v * y, v])
    _, _, vh = np.linalg.svd(np.asarray(rows))
    homography_n = vh[-1].reshape(3, 3)
    homography = (
        np.linalg.inv(destination_transform)
        @ homography_n
        @ source_transform
    )
    return homography / homography[2, 2]


def decompose_homography(
    homography: np.ndarray, camera: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    basis = np.linalg.inv(camera) @ homography
    if basis[2, 2] < 0:
        basis = -basis
    scale = 2.0 / (
        np.linalg.norm(basis[:, 0]) + np.linalg.norm(basis[:, 1])
    )
    first = scale * basis[:, 0]
    second = scale * basis[:, 1]
    provisional = np.column_stack([first, second, np.cross(first, second)])
    u, _, vh = np.linalg.svd(provisional)
    rotation = u @ vh
    if np.linalg.det(rotation) < 0:
        u[:, -1] *= -1
        rotation = u @ vh
    translation = scale * basis[:, 2]
    return rotation, translation


def relative_error(measured: float, expected: float) -> float:
    return abs(measured - expected) / max(abs(expected), 1e-12)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()

    fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
    declared_pitch = float(fixture["declared_pitch_mm"])
    width_units = float(fixture["width_in_pitch_units"])
    intersections = fixture["intersections"]
    destination = np.asarray(
        [item["image_px"] for item in intersections], dtype=np.float64
    )
    anonymous_source = np.asarray(
        [
            [
                float(item["ordinal"]),
                float(item["boundary_sign"]) * width_units / 2.0,
            ]
            for item in intersections
        ],
        dtype=np.float64,
    )
    metric_source = anonymous_source * declared_pitch

    camera_values = fixture["camera"]
    focal_px = float(camera_values["focal_px"])
    cx, cy = (float(value) for value in camera_values["principal_point_px"])
    camera = np.array(
        [[focal_px, 0.0, cx], [0.0, focal_px, cy], [0.0, 0.0, 1.0]]
    )
    metric_homography = fit_homography(metric_source, destination)
    rotation, translation = decompose_homography(metric_homography, camera)
    anonymous_homography = fit_homography(anonymous_source, destination)
    _, anonymous_translation = decompose_homography(
        anonymous_homography, camera
    )

    truth = {key: float(value) for key, value in fixture["independent_truth"].items()}
    standard_error = {
        key: float(value)
        for key, value in fixture["reported_standard_error"].items()
    }
    recovered_pitch = truth["centre_depth_mm"] / anonymous_translation[2]
    centre_depth = float(translation[2])
    tilt = math.degrees(math.acos(np.clip(abs(float(rotation[2, 2])), 0.0, 1.0)))
    magnification = (
        focal_px
        * float(camera_values["sensor_pitch_um"])
        / 1000.0
        / centre_depth
    )

    ordinals = np.asarray(
        [float(item["ordinal"]) for item in fixture["focus_samples"]]
    )
    focus_frame = np.asarray(
        [float(item["best_focus_frame"]) for item in fixture["focus_samples"]]
    )
    depth = rotation[2, 0] * ordinals * declared_pitch + translation[2]
    design = np.column_stack([np.ones(focus_frame.size), focus_frame])
    focus_step_um = float(np.linalg.lstsq(design, depth, rcond=None)[0][1] * 1000.0)

    homogeneous = np.column_stack([metric_source, np.ones(metric_source.shape[0])])
    projected = (metric_homography @ homogeneous.T).T
    projected = projected[:, :2] / projected[:, 2, None]
    reprojection_rms = math.sqrt(
        float(np.mean(np.sum((projected - destination) ** 2, axis=1)))
    )
    measured = {
        "pitch_mm": recovered_pitch,
        "centre_depth_mm": centre_depth,
        "tilt_deg": tilt,
        "magnification": magnification,
        "focus_step_um_per_frame": focus_step_um,
    }

    failures = []
    checks = {}
    for key, value in measured.items():
        tolerance = min(standard_error[key], 0.01 * abs(truth[key]))
        error = abs(value - truth[key])
        checks[key] = {
            "measured": value,
            "expected": truth[key],
            "absolute_error": error,
            "relative_error": relative_error(value, truth[key]),
            "tolerance": tolerance,
            "pass": bool(error <= tolerance),
        }
        if error > tolerance:
            failures.append(
                f"{key}: measured={value:.12g} expected={truth[key]:.12g} "
                f"error={error:.12g} tolerance={tolerance:.12g}"
            )
    declared_pitch_error = abs(declared_pitch - recovered_pitch)
    declared_pitch_tolerance = min(
        standard_error["pitch_mm"], 0.01 * truth["pitch_mm"]
    )
    if declared_pitch_error > declared_pitch_tolerance:
        failures.insert(
            0,
            "declared_pitch_mm: "
            f"declared={declared_pitch:.12g} recovered={recovered_pitch:.12g} "
            f"error={declared_pitch_error:.12g} "
            f"tolerance={declared_pitch_tolerance:.12g}",
        )

    result = {
        "fixture_schema": fixture["schema"],
        "declared_pitch_mm": declared_pitch,
        "reprojection_rms_px": reprojection_rms,
        "checks": checks,
        "declared_pitch_check": {
            "declared": declared_pitch,
            "independently_recovered": recovered_pitch,
            "absolute_error": declared_pitch_error,
            "tolerance": declared_pitch_tolerance,
            "pass": bool(declared_pitch_error <= declared_pitch_tolerance),
        },
        "test_count": len(checks),
        "pass": not failures,
    }
    if args.result is not None:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(f"METRIC_FIXTURE_TESTS={len(checks)}")
    print(f"METRIC_FIXTURE_REPROJECTION_RMS_PX={reprojection_rms:.12g}")
    for key, check in checks.items():
        print(
            f"{key} measured={check['measured']:.12g} "
            f"expected={check['expected']:.12g} "
            f"tolerance={check['tolerance']:.12g} pass={check['pass']}"
        )
    if failures:
        print("PITCH_SCALE_ERROR: synthetic metric calibration rejected")
        for failure in failures:
            print(f"  {failure}")
        sys.exit(1)
    print("METRIC_FIXTURE_PASS")


if __name__ == "__main__":
    main()
