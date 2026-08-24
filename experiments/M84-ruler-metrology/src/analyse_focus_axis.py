"""Measure tilted-ruler focus sampling in graduation units.

Absolute microns remain deliberately unavailable because the mandatory control
and physical-pitch gates failed. This diagnostic can still test whether equal
graduation-depth increments map to a constant number of focus frames.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
import rawpy
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.stats import theilslopes

from analyse_control import peak_position, robust_contrast, subpixel_minimum

SEED = 0x4D842026


def load_greens(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.astype(np.float32)
        black = float(max(raw.black_level_per_channel))
    height, width = visible.shape
    height -= height % 2
    width -= width % 2
    return (
        visible[:height:2, 1:width:2] - black,
        visible[1:height:2, :width:2] - black,
    )


def focus_score(patch: np.ndarray) -> float:
    if min(patch.shape) < 7:
        return math.nan
    gx = cv2.Sobel(patch, cv2.CV_32F, 1, 0, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    gy = cv2.Sobel(patch, cv2.CV_32F, 0, 1, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    magnitude = cv2.magnitude(gx, gy)
    field = cv2.boxFilter(
        magnitude,
        cv2.CV_32F,
        (27, 27),
        normalize=True,
        borderType=cv2.BORDER_REFLECT_101,
    )
    return float(np.mean(field) / robust_contrast(patch))


def track_centres(
    mean: np.ndarray,
    seed_x: np.ndarray,
    baseline: np.ndarray,
    radius: int = 28,
) -> np.ndarray:
    height, width = mean.shape
    candidates = np.full(seed_x.size, np.nan)
    for index, (x, y) in enumerate(zip(seed_x, baseline, strict=True)):
        y0 = max(0, int(round(y + 25)))
        y1 = min(height, int(round(y + 260)))
        x0 = max(1, int(round(x)) - radius)
        x1 = min(width - 1, int(round(x)) + radius + 1)
        if y1 - y0 < 20 or x1 - x0 < 5:
            continue
        profile = np.median(mean[y0:y1, x0:x1], axis=0)
        smooth = gaussian_filter1d(profile, 1.5, mode="nearest")
        candidates[index] = x0 + subpixel_minimum(smooth, int(np.argmin(smooth)))
    valid = np.isfinite(candidates)
    if np.count_nonzero(valid) < 4:
        return seed_x.copy()
    scale, intercept, _, _ = theilslopes(candidates[valid], seed_x[valid])
    if not 0.90 <= scale <= 1.10:
        return seed_x.copy()
    return intercept + scale * seed_x


def robust_fit(
    design: np.ndarray,
    value: np.ndarray,
    initial: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if initial is None:
        initial, _, _, _ = np.linalg.lstsq(design, value, rcond=None)
    scale = max(1.4826 * np.median(np.abs(value - np.median(value))), 0.1)
    fit = least_squares(
        lambda parameters: (design @ parameters - value) / scale,
        initial,
        loss="huber",
        f_scale=1.5,
        max_nfev=1000,
    )
    residual = value - design @ fit.x
    return fit.x, residual


def sampling_fit(ordinal: np.ndarray, peak: np.ndarray) -> dict[str, object]:
    centre = float(np.mean(ordinal))
    x = ordinal - centre
    linear_design = np.column_stack([np.ones(x.size), x])
    linear, linear_residual = robust_fit(linear_design, peak)
    quadratic_design = np.column_stack([np.ones(x.size), x, x * x])
    quadratic, quadratic_residual = robust_fit(
        quadratic_design,
        peak,
        np.array([linear[0], linear[1], 0.0]),
    )
    linear_rms = float(np.sqrt(np.mean(linear_residual**2)))
    quadratic_rms = float(np.sqrt(np.mean(quadratic_residual**2)))

    q1, q3 = np.percentile(ordinal, [25, 75])
    derivative_q1 = float(quadratic[1] + 2.0 * quadratic[2] * (q1 - centre))
    derivative_q3 = float(quadratic[1] + 2.0 * quadratic[2] * (q3 - centre))
    if derivative_q1 > 0.0 and derivative_q3 > 0.0:
        step_q1 = 1.0 / derivative_q1
        step_q3 = 1.0 / derivative_q3
        step_drift = abs(step_q3 - step_q1) / (0.5 * (step_q1 + step_q3))
    else:
        step_q1 = math.nan
        step_q3 = math.nan
        step_drift = math.nan

    rng = np.random.default_rng(SEED)
    drift_boot = []
    slope_boot = []
    for _ in range(2000):
        chosen = rng.integers(0, ordinal.size, ordinal.size)
        oo = ordinal[chosen]
        pp = peak[chosen]
        if np.unique(oo).size < 4 or np.ptp(oo) < 0.5 * np.ptp(ordinal):
            continue
        cc = float(np.mean(oo))
        xx = oo - cc
        ld = np.column_stack([np.ones(xx.size), xx])
        qd = np.column_stack([np.ones(xx.size), xx, xx * xx])
        try:
            lp, _ = robust_fit(ld, pp)
            qp, _ = robust_fit(qd, pp, np.array([lp[0], lp[1], 0.0]))
        except (ValueError, np.linalg.LinAlgError):
            continue
        slope_boot.append(float(lp[1]))
        bq1 = float(qp[1] + 2.0 * qp[2] * (q1 - cc))
        bq3 = float(qp[1] + 2.0 * qp[2] * (q3 - cc))
        if bq1 > 0.0 and bq3 > 0.0:
            s1, s3 = 1.0 / bq1, 1.0 / bq3
            drift_boot.append(abs(s3 - s1) / (0.5 * (s1 + s3)))

    return {
        "linear_frames_per_graduation": float(linear[1]),
        "linear_frames_per_graduation_95pct": (
            np.percentile(slope_boot, [2.5, 97.5]).tolist()
            if slope_boot
            else [math.nan, math.nan]
        ),
        "linear_intercept_at_mean_ordinal": float(linear[0]),
        "linear_residual_rms_frames": linear_rms,
        "linear_residual_p95_abs_frames": float(
            np.percentile(np.abs(linear_residual), 95)
        ),
        "quadratic_coefficients": quadratic.tolist(),
        "quadratic_residual_rms_frames": quadratic_rms,
        "quadratic_rmse_improvement_fraction": (
            (linear_rms - quadratic_rms) / linear_rms if linear_rms > 0 else 0.0
        ),
        "focus_step_relative_at_q1_graduation_per_frame": step_q1,
        "focus_step_relative_at_q3_graduation_per_frame": step_q3,
        "focus_step_fractional_drift_q1_to_q3": step_drift,
        "focus_step_fractional_drift_95pct": (
            np.percentile(drift_boot, [2.5, 97.5]).tolist()
            if drift_boot
            else [math.nan, math.nan]
        ),
        "bootstrap_n": len(slope_boot),
        "drift_bootstrap_n": len(drift_boot),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack", type=Path)
    parser.add_argument("line_result", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--analysis-to-green", type=float, default=4.0)
    args = parser.parse_args()

    line_result = json.loads(args.line_result.read_text(encoding="utf-8"))
    position_analysis = np.asarray(line_result["graduation_x_analysis_px"], dtype=np.float64)
    if position_analysis.size < 4:
        raise RuntimeError("not enough graduation seeds")
    x0, y0, x1, y1 = np.asarray(line_result["baseline_analysis_px"], dtype=np.float64)
    slope = (y1 - y0) / (x1 - x0)
    seed_x = position_analysis * args.analysis_to_green
    baseline = (
        y0 + (position_analysis - x0) * slope
    ) * args.analysis_to_green

    frames = sorted(args.stack.glob("*.ARW"))
    n_intervals = seed_x.size - 1
    curves = np.full((2, n_intervals, len(frames)), np.nan, dtype=np.float64)
    tracked = np.full((len(frames), seed_x.size), np.nan, dtype=np.float64)
    for frame_index, frame in enumerate(frames):
        g1, g2 = load_greens(frame)
        mean = 0.5 * (g1 + g2)
        centres = track_centres(mean, seed_x, baseline)
        tracked[frame_index] = centres
        for plane_index, plane in enumerate((g1, g2)):
            for interval_index in range(n_intervals):
                left, right = centres[interval_index : interval_index + 2]
                if not np.isfinite(left + right) or right <= left:
                    continue
                margin = 0.25 * (right - left)
                xa = max(0, int(round(left + margin)))
                xb = min(plane.shape[1], int(round(right - margin)))
                x_mid = 0.5 * (left + right)
                y_base = (
                    y0 + (x_mid / args.analysis_to_green - x0) * slope
                ) * args.analysis_to_green
                ya = max(0, int(round(y_base + 35)))
                yb = min(plane.shape[0], int(round(y_base + 240)))
                curves[plane_index, interval_index, frame_index] = focus_score(
                    plane[ya:yb, xa:xb]
                )
        if frame_index % 25 == 0 or frame_index + 1 == len(frames):
            print(f"focus-axis frame={frame_index:03d}", flush=True)

    peaks = np.full((2, n_intervals), np.nan)
    status: list[list[str]] = [[], []]
    for plane_index in range(2):
        for interval_index in range(n_intervals):
            peak, state = peak_position(curves[plane_index, interval_index])
            peaks[plane_index, interval_index] = peak
            status[plane_index].append(state)

    green_agreement = np.abs(peaks[1] - peaks[0])
    accepted = (
        np.isfinite(peaks[0])
        & np.isfinite(peaks[1])
        & (green_agreement <= 0.25)
        & np.array([state == "accepted" for state in status[0]])
        & np.array([state == "accepted" for state in status[1]])
    )
    ordinal = np.arange(n_intervals, dtype=np.float64) + 0.5
    mean_peak = np.mean(peaks, axis=0)
    fit = (
        sampling_fit(ordinal[accepted], mean_peak[accepted])
        if np.count_nonzero(accepted) >= 4
        else None
    )

    result = {
        "claim_class": "MEASURED",
        "role": "relative-focus-diagnostic-after-control-failure",
        "frame_count": len(frames),
        "graduation_count": int(seed_x.size),
        "interval_count": n_intervals,
        "curves_operator": (
            "native-G1/G2 3x3 Sobel magnitude, 27x27 green support, "
            "local p95-p05 contrast normalisation"
        ),
        "peak_frame_by_green": peaks.tolist(),
        "peak_status_by_green": status,
        "green_peak_difference_frames": green_agreement.tolist(),
        "accepted_interval": accepted.tolist(),
        "accepted_count": int(np.count_nonzero(accepted)),
        "mean_peak_frame": mean_peak.tolist(),
        "sampling_fit": fit,
        "absolute_step_um_per_frame": None,
        "absolute_step_reason": (
            "physical graduation pitch and metric plane tilt were not identified"
        ),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "focus-axis-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(
        args.output / "focus-axis-curves.npz",
        curves=curves,
        peaks=peaks,
        accepted=accepted,
        tracked_centres_green=tracked,
        ordinal=ordinal,
    )
    print(
        "FOCUS_AXIS "
        f"accepted={np.count_nonzero(accepted)}/{n_intervals} "
        f"frames_per_graduation={fit['linear_frames_per_graduation'] if fit else None} "
        f"drift={fit['focus_step_fractional_drift_q1_to_q3'] if fit else None}",
        flush=True,
    )


if __name__ == "__main__":
    main()
