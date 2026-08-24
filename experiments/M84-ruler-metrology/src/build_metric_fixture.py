"""Build M84's deterministic synthetic metric-plane fixture."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


def rotation_x(angle: float) -> np.ndarray:
    c = math.cos(angle)
    s = math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def rotation_y(angle: float) -> np.ndarray:
    c = math.cos(angle)
    s = math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    pitch_mm = 1.0
    width_in_pitch_units = 8.0
    focal_px = 9800.0
    principal_point_px = np.array([3514.0, 2344.0])
    sensor_pitch_um = 5.122
    centre_depth_mm = 120.0
    focus_step_mm_per_frame = 0.040
    rotation = rotation_y(math.radians(38.0)) @ rotation_x(math.radians(7.0))
    translation = np.array([0.0, 0.0, centre_depth_mm])
    camera = np.array(
        [
            [focal_px, 0.0, principal_point_px[0]],
            [0.0, focal_px, principal_point_px[1]],
            [0.0, 0.0, 1.0],
        ]
    )

    intersections = []
    for ordinal in range(-10, 11):
        for boundary_sign in (-1, 1):
            point = np.array(
                [
                    ordinal * pitch_mm,
                    boundary_sign * width_in_pitch_units * pitch_mm / 2.0,
                    0.0,
                ]
            )
            camera_point = rotation @ point + translation
            image = camera @ camera_point
            image = image[:2] / image[2]
            intersections.append(
                {
                    "ordinal": ordinal,
                    "boundary_sign": boundary_sign,
                    "image_px": [round(float(value), 9) for value in image],
                }
            )

    focus_samples = []
    for ordinal in range(-10, 11):
        point = np.array([ordinal * pitch_mm, 0.0, 0.0])
        depth_mm = float((rotation @ point + translation)[2])
        frame = 150.0 + (depth_mm - centre_depth_mm) / focus_step_mm_per_frame
        focus_samples.append(
            {
                "ordinal": ordinal,
                "best_focus_frame": round(frame, 9),
            }
        )

    tilt_deg = math.degrees(math.acos(abs(float(rotation[2, 2]))))
    magnification = focal_px * sensor_pitch_um / 1000.0 / centre_depth_mm
    fixture = {
        "schema": "M84-synthetic-metric-plane-v1",
        "declared_pitch_mm": 1.0,
        "width_in_pitch_units": width_in_pitch_units,
        "camera": {
            "focal_px": focal_px,
            "principal_point_px": principal_point_px.tolist(),
            "sensor_pitch_um": sensor_pitch_um,
        },
        "intersections": intersections,
        "focus_samples": focus_samples,
        "independent_truth": {
            "pitch_mm": pitch_mm,
            "centre_depth_mm": centre_depth_mm,
            "tilt_deg": tilt_deg,
            "magnification": magnification,
            "focus_step_um_per_frame": focus_step_mm_per_frame * 1000.0,
        },
        "reported_standard_error": {
            "pitch_mm": 0.001,
            "centre_depth_mm": 0.02,
            "tilt_deg": 0.01,
            "magnification": 0.0001,
            "focus_step_um_per_frame": 0.02,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(fixture, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"METRIC_FIXTURE_BUILT path={args.output}", flush=True)


if __name__ == "__main__":
    main()
