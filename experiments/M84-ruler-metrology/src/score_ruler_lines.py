"""Count the tilted capture's visible graduations on the all-focus diagnostic."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.signal import find_peaks


def segment_values(image: np.ndarray, line: np.ndarray) -> np.ndarray:
    x0, y0, x1, y1 = line
    count = max(int(round(math.hypot(x1 - x0, y1 - y0))), 2)
    x = np.linspace(x0, x1, count)
    y = np.linspace(y0, y1, count)
    return cv2.remap(
        image,
        x.astype(np.float32)[None, :],
        y.astype(np.float32)[None, :],
        cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )[0]


def choose_baseline(image: np.ndarray) -> tuple[np.ndarray, list[dict[str, float]]]:
    equalised = cv2.createCLAHE(2.0, (8, 8)).apply(image)
    edges = cv2.Canny(equalised, 40, 120, L2gradient=True)
    raw = cv2.HoughLinesP(
        edges,
        1.0,
        np.pi / 1800,
        threshold=30,
        minLineLength=100,
        maxLineGap=20,
    )
    if raw is None:
        raise RuntimeError("no line candidates")
    height, width = image.shape
    candidates = []
    for x0, y0, x1, y1 in raw[:, 0, :]:
        if x1 < x0:
            x0, x1, y0, y1 = x1, x0, y1, y0
        angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
        length = math.hypot(x1 - x0, y1 - y0)
        if not (-28.0 <= angle <= -14.0):
            continue
        if x1 < 0.50 * width or x0 > 0.72 * width:
            continue
        centre_x = 0.50 * width
        centre_y = y0 + (centre_x - x0) * (y1 - y0) / max(x1 - x0, 1)
        if not (0.62 * height <= centre_y <= 0.76 * height):
            continue
        values = segment_values(image, np.array([x0, y0, x1, y1], dtype=np.float64))
        darkness = float(np.percentile(values, 20))
        score = darkness - 0.05 * length
        candidates.append(
            {
                "line": [float(x0), float(y0), float(x1), float(y1)],
                "angle_deg": angle,
                "length_px": length,
                "dark_p20": darkness,
                "score": score,
            }
        )
    if not candidates:
        raise RuntimeError("no ruler-baseline candidate passed fixed geometry")
    candidates.sort(key=lambda item: item["score"])
    return np.asarray(candidates[0]["line"]), candidates


def projective_fit(position: np.ndarray) -> dict[str, object]:
    ordinal = np.arange(position.size, dtype=np.float64)
    slope = float(np.median(np.diff(position)))
    initial = np.array([slope, float(position[0]), 0.0])

    def predict(parameters: np.ndarray, x: np.ndarray) -> np.ndarray:
        return (parameters[0] * x + parameters[1]) / (parameters[2] * x + 1.0)

    raw_scale = max(1.4826 * np.median(np.abs(np.diff(position) - slope)), 0.25)
    fit = least_squares(
        lambda p: (predict(p, ordinal) - position) / raw_scale,
        initial,
        loss="huber",
        f_scale=1.5,
        max_nfev=1000,
    )
    prediction = predict(fit.x, ordinal)
    residual = position - prediction
    return {
        "parameters": fit.x.tolist(),
        "converged": bool(fit.success),
        "cost": float(fit.cost),
        "residual_rms_analysis_px": float(np.sqrt(np.mean(residual**2))),
        "residual_p95_abs_analysis_px": float(np.percentile(np.abs(residual), 95)),
        "predicted_analysis_px": prediction.tolist(),
        "residual_analysis_px": residual.tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("all_focus", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("annotated_png", type=Path)
    parser.add_argument("--sensor-pixels-per-analysis-pixel", type=float, default=8.0)
    args = parser.parse_args()

    image = cv2.imread(str(args.all_focus), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise RuntimeError(f"cannot read {args.all_focus}")
    line, candidates = choose_baseline(image)
    x0, y0, x1, y1 = line
    if x1 < x0:
        x0, x1, y0, y1 = x1, x0, y1, y0
    slope = (y1 - y0) / (x1 - x0)

    height, width = image.shape
    start = max(int(round(x0)), int(round(0.42 * width)))
    stop = min(int(round(x1)), int(round(0.70 * width)))
    xs = np.arange(start, stop + 1)
    profile = np.full(xs.size, np.nan)
    for index, x in enumerate(xs):
        baseline_y = y0 + (x - x0) * slope
        a = max(0, int(round(baseline_y + 12)))
        b = min(height, int(round(baseline_y + 105)))
        if b - a >= 10:
            profile[index] = float(np.percentile(image[a:b, x], 25))
    valid = np.isfinite(profile)
    if np.count_nonzero(valid) != profile.size:
        profile = np.interp(xs, xs[valid], profile[valid])
    smooth = gaussian_filter1d(profile, 0.8, mode="nearest")
    background = gaussian_filter1d(profile, 12.0, mode="nearest")
    darkness = background - smooth
    mad = max(1.4826 * np.median(np.abs(darkness - np.median(darkness))), 1e-6)
    threshold_sensitivity = []
    peaks_by_multiplier = {}
    for multiplier in (0.75, 1.0, 1.25, 1.5, 3.0, 5.0):
        candidate_peaks, _ = find_peaks(
            darkness,
            prominence=multiplier * mad,
            distance=3,
            width=(0.5, 8.0),
        )
        peaks_by_multiplier[multiplier] = candidate_peaks
        threshold_sensitivity.append(
            {
                "prominence_mad_multiplier": multiplier,
                "graduation_count": int(candidate_peaks.size),
                "graduation_x_analysis_px": xs[candidate_peaks].astype(float).tolist(),
            }
        )
    peaks = peaks_by_multiplier[1.0]
    positions = xs[peaks].astype(np.float64)
    fit = projective_fit(positions) if positions.size >= 4 else None

    result = {
        "claim_class": "MEASURED",
        "role": "diagnostic-only-after-control-failure",
        "baseline_analysis_px": line.tolist(),
        "baseline_angle_deg": math.degrees(math.atan2(y1 - y0, x1 - x0)),
        "baseline_candidates": candidates[:20],
        "profile_x_range_analysis_px": [int(start), int(stop)],
        "profile_mad": mad,
        "profile_darkness_max": float(np.max(darkness)),
        "profile_darkness_p95": float(np.percentile(darkness, 95)),
        "threshold_sensitivity": threshold_sensitivity,
        "selected_prominence_mad_multiplier": 1.0,
        "threshold_selection": (
            "post-control-failure diagnostic; an initial 3-MAD diagnostic found "
            "zero graduations, and 1 MAD was selected after inspecting that failure"
        ),
        "preregistered_contrast_requirement_mad": 5.0,
        "preregistered_contrast_requirement_met": bool(
            peaks_by_multiplier[5.0].size >= 20
        ),
        "graduation_count": int(positions.size),
        "minor_interval_count": max(int(positions.size) - 1, 0),
        "graduation_x_analysis_px": positions.tolist(),
        "interval_analysis_px": np.diff(positions).tolist(),
        "interval_sensor_px": (
            np.diff(positions) * args.sensor_pixels_per_analysis_pixel
        ).tolist(),
        "projective_fit": fit,
        "physical_pitch_identified": False,
        "printed_labels_or_unit_legend_visible": False,
    }
    args.output_json.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    rendered = Image.fromarray(image).convert("RGB")
    draw = ImageDraw.Draw(rendered)
    draw.line([(x0, y0), (x1, y1)], fill=(255, 0, 0), width=2)
    for ordinal, x in enumerate(positions):
        y = y0 + (x - x0) * slope
        draw.line([(x, y), (x, min(height - 1, y + 105))], fill=(0, 255, 0), width=1)
        draw.text((x + 1, y + 2), str(ordinal), fill=(255, 255, 0))
    rendered.save(args.annotated_png)

    print(
        f"RULER_LINES baseline_angle={result['baseline_angle_deg']:.6f} "
        f"graduations={positions.size} intervals={max(positions.size - 1, 0)} "
        f"projective_rms={fit['residual_rms_analysis_px'] if fit else None}",
        flush=True,
    )


if __name__ == "__main__":
    main()
