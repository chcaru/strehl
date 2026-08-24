"""Run M84's mandatory flat-ruler control before the tilted capture."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
import rawpy
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import least_squares
from scipy.signal import find_peaks, peak_widths
from scipy.stats import theilslopes

SEED = 0x4D842026


def load_greens(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.astype(np.float32)
        black = float(max(raw.black_level_per_channel))
        white = int(raw.white_level)
        pattern = raw.raw_pattern.copy()
    height, width = visible.shape
    height -= height % 2
    width -= width % 2
    visible = visible[:height, :width]
    g1 = visible[0::2, 1::2] - black
    g2 = visible[1::2, 0::2] - black
    metadata = {
        "visible_sensor_shape": [int(height), int(width)],
        "green_shape": [int(g1.shape[0]), int(g1.shape[1])],
        "black": black,
        "white": white,
        "raw_pattern": pattern.tolist(),
    }
    return g1, g2, metadata


def robust_contrast(image: np.ndarray) -> float:
    lo, hi = np.percentile(image, [5.0, 95.0])
    return max(float(hi - lo), 1.0)


def focus_field(image: np.ndarray) -> np.ndarray:
    gx = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    gy = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    magnitude = cv2.magnitude(gx, gy)
    return cv2.boxFilter(
        magnitude,
        cv2.CV_32F,
        (27, 27),
        normalize=True,
        borderType=cv2.BORDER_REFLECT_101,
    )


def global_focus_score(image: np.ndarray) -> float:
    field = focus_field(image)
    border_y = max(32, image.shape[0] // 20)
    border_x = max(32, image.shape[1] // 20)
    interior = field[border_y:-border_y, border_x:-border_x]
    return float(np.mean(interior) / robust_contrast(image[border_y:-border_y, border_x:-border_x]))


def localise_baseline(image: np.ndarray, expected: float | None = None) -> tuple[float, float]:
    height, width = image.shape
    row = np.median(image, axis=1)
    residual = row - gaussian_filter1d(row, 40.0, mode="nearest")
    if expected is None:
        lo, hi = int(0.25 * height), int(0.85 * height)
    else:
        lo = max(0, int(expected - 50))
        hi = min(height, int(expected + 51))
    seed = lo + int(np.argmin(residual[lo:hi]))

    xs: list[float] = []
    ys: list[float] = []
    half = 35
    for x0 in np.linspace(0, width, 33, dtype=int)[:-1]:
        x1 = min(width, x0 + max(width // 32, 1))
        profile = np.median(image[:, x0:x1], axis=1)
        smooth = gaussian_filter1d(profile, 2.0, mode="nearest")
        a, b = max(0, seed - half), min(height, seed + half + 1)
        y = a + int(np.argmin(smooth[a:b]))
        xs.append(0.5 * (x0 + x1 - 1))
        ys.append(float(y))

    x_values = np.asarray(xs, dtype=np.float64)
    y_values = np.asarray(ys, dtype=np.float64)
    slope, intercept, _, _ = theilslopes(y_values, x_values)
    centre = float(intercept + slope * (width - 1) / 2.0)
    if expected is not None and abs(centre - expected) > 50.0:
        raise RuntimeError(
            f"baseline tracker escaped its registered window: {centre:.3f} vs {expected:.3f}"
        )
    return centre, float(slope)


def rectify_rows(image: np.ndarray, baseline: float, slope: float) -> np.ndarray:
    height, width = image.shape
    centre = (width - 1) / 2.0
    matrix = np.array([[1.0, 0.0, 0.0], [-slope, 1.0, slope * centre]], dtype=np.float32)
    return cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REFLECT_101,
    )


def subpixel_minimum(profile: np.ndarray, index: int) -> float:
    if index <= 0 or index >= profile.size - 1:
        return float(index)
    ym, y0, yp = (float(profile[index - 1]), float(profile[index]), float(profile[index + 1]))
    denominator = ym - 2.0 * y0 + yp
    if denominator <= 0.0:
        return float(index)
    offset = 0.5 * (ym - yp) / denominator
    return float(index + np.clip(offset, -1.0, 1.0))


def subpixel_maximum(profile: np.ndarray, index: int) -> float:
    return subpixel_minimum(-np.asarray(profile), index)


def detect_ticks(image: np.ndarray, baseline: float) -> dict[str, object]:
    height, width = image.shape
    y0 = min(height - 2, int(round(baseline + 45)))
    y1 = height - max(20, height // 100)
    band = image[y0:y1]
    profile = np.median(band, axis=0)
    smooth = gaussian_filter1d(profile, 2.0, mode="nearest")
    background = gaussian_filter1d(profile, 75.0, mode="nearest")
    strength = background - smooth
    mad = max(1.4826 * np.median(np.abs(strength - np.median(strength))), 1e-6)
    peaks, properties = find_peaks(
        strength,
        prominence=5.0 * mad,
        distance=max(20, width // 80),
        width=(2.0, width / 20.0),
    )
    centres = np.array([subpixel_minimum(smooth, int(p)) for p in peaks], dtype=np.float64)
    order = np.argsort(centres)
    centres = centres[order]
    prominences = properties["prominences"][order]
    widths = properties["widths"][order]

    if centres.size >= 3:
        intervals = np.diff(centres)
        pitch_seed = float(np.median(intervals))
        keep = np.ones(centres.size, dtype=bool)
        for i, delta in enumerate(intervals):
            if delta < 0.55 * pitch_seed:
                if prominences[i] < prominences[i + 1]:
                    keep[i] = False
                else:
                    keep[i + 1] = False
        centres = centres[keep]
        prominences = prominences[keep]
        widths = widths[keep]

    intervals = np.diff(centres)
    return {
        "centres_green_px": centres,
        "intervals_green_px": intervals,
        "prominences": prominences,
        "bar_widths_green_px": widths,
        "profile": profile,
        "strength": strength,
        "mad": mad,
        "band": [y0, y1],
    }


def tick_localisation(
    image: np.ndarray,
    baseline: float,
    centres: np.ndarray,
    band: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    y0, y1 = band
    chunks = np.array_split(np.arange(y0, y1), 8)
    estimates = np.full((len(chunks), centres.size), np.nan, dtype=np.float64)
    row_centres = np.array([float(np.mean(rows)) for rows in chunks])
    edge_fwhm = np.full((len(chunks), centres.size, 2), np.nan, dtype=np.float64)
    pitch = float(np.median(np.diff(centres)))
    radius = max(10, int(round(0.25 * pitch)))
    for row_index, rows in enumerate(chunks):
        if rows.size < 2:
            continue
        profile = np.median(image[rows], axis=0)
        smooth = gaussian_filter1d(profile, 1.0, mode="nearest")
        signed_derivative = np.gradient(smooth)
        derivative = np.abs(signed_derivative)
        for tick_index, centre in enumerate(centres):
            lo = max(1, int(round(centre)) - radius)
            hi = min(profile.size - 1, int(round(centre)) + radius + 1)
            midpoint = int(round(centre))
            left_lo, left_hi = lo, max(lo + 2, midpoint)
            right_lo, right_hi = min(hi - 2, midpoint + 1), hi
            left_gradient = -signed_derivative[left_lo:left_hi]
            right_gradient = signed_derivative[right_lo:right_hi]
            if left_gradient.size < 3 or right_gradient.size < 3:
                continue
            left_edge = left_lo + subpixel_maximum(left_gradient, int(np.argmax(left_gradient)))
            right_edge = right_lo + subpixel_maximum(
                right_gradient, int(np.argmax(right_gradient))
            )
            estimates[row_index, tick_index] = 0.5 * (left_edge + right_edge)
            for side, (a, b, edge) in enumerate(
                (
                    (left_lo, left_hi, left_edge),
                    (right_lo, right_hi, right_edge),
                )
            ):
                segment = derivative[a:b]
                if segment.size >= 3 and np.max(segment) > 0:
                    peak = int(np.clip(round(edge - a), 0, segment.size - 1))
                    widths = peak_widths(segment, [peak], rel_height=0.5)[0]
                    edge_fwhm[row_index, tick_index, side] = float(widths[0])

    centre_at_baseline = np.full(centres.size, np.nan)
    ci_width = np.full(centres.size, np.nan)
    for tick_index in range(centres.size):
        valid = np.isfinite(estimates[:, tick_index])
        if np.count_nonzero(valid) < 4:
            continue
        design = np.column_stack(
            [
                np.ones(np.count_nonzero(valid)),
                row_centres[valid] - baseline,
            ]
        )
        fit, _, _, _ = np.linalg.lstsq(design, estimates[valid, tick_index], rcond=None)
        residual = estimates[valid, tick_index] - design @ fit
        dof = max(np.count_nonzero(valid) - 2, 1)
        sigma2 = float(np.sum(residual**2) / dof)
        covariance = sigma2 * np.linalg.inv(design.T @ design)
        centre_at_baseline[tick_index] = float(fit[0])
        ci_width[tick_index] = float(2.0 * 1.96 * math.sqrt(max(covariance[0, 0], 0.0)))
    return centre_at_baseline, ci_width, edge_fwhm


def track_ticks(
    image: np.ndarray,
    baseline: float,
    reference_centres: np.ndarray,
) -> np.ndarray:
    height, _ = image.shape
    y0 = min(height - 2, int(round(baseline + 45)))
    y1 = height - max(20, height // 100)
    profile = np.median(image[y0:y1], axis=0)
    smooth = gaussian_filter1d(profile, 2.0, mode="nearest")
    pitch = float(np.median(np.diff(reference_centres)))
    radius = max(8, int(round(0.22 * pitch)))
    tracked = []
    for centre in reference_centres:
        lo = max(1, int(round(centre)) - radius)
        hi = min(profile.size - 1, int(round(centre)) + radius + 1)
        local = smooth[lo:hi]
        tracked.append(lo + subpixel_minimum(local, int(np.argmin(local))))
    return np.asarray(tracked, dtype=np.float64)


def peak_position(curve: np.ndarray) -> tuple[float, str]:
    values = np.asarray(curve, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        return math.nan, "non-finite"
    winner = int(np.argmax(values))
    if winner < 3 or winner + 3 >= values.size:
        return float(winner), "boundary"
    indices = np.arange(winner - 3, winner + 4, dtype=np.float64)
    baseline = float(np.min(values))
    positive = values[winner - 3 : winner + 4] - baseline
    epsilon = max(float(np.max(positive)) * 1e-6, 1e-12)
    coefficients = np.polyfit(indices, np.log(np.maximum(positive, epsilon)), 2)
    if coefficients[0] >= 0.0:
        return float(winner), "not-concave"
    vertex = -coefficients[1] / (2.0 * coefficients[0])
    if vertex < indices[0] or vertex > indices[-1]:
        return float(winner), "outside"

    if winner == 0 or winner == values.size - 1:
        return float(vertex), "no-parabola"
    ym, y0, yp = values[winner - 1 : winner + 2]
    denominator = ym - 2.0 * y0 + yp
    alternate = float(winner if denominator <= 0 else winner + 0.5 * (ym - yp) / denominator)
    if abs(vertex - alternate) > 0.25:
        return float(vertex), "sensitivity-disagree"
    return float(vertex), "accepted"


def fit_focus_line(x: np.ndarray, k: np.ndarray) -> dict[str, object]:
    span = float(np.max(x) - np.min(x))
    slope, intercept, _, _ = theilslopes(k, x)
    prediction = intercept + slope * x
    raw_residual = k - prediction
    endpoint_change = float(slope * span)

    rng = np.random.default_rng(SEED)
    boot = []
    for _ in range(2000):
        sample = rng.integers(0, x.size, x.size)
        xx, yy = x[sample], k[sample]
        if np.ptp(xx) < 0.5 * span:
            continue
        try:
            bslope, _, _, _ = theilslopes(yy, xx)
            boot.append(float(bslope * span))
        except (ValueError, FloatingPointError):
            continue
    interval = np.percentile(boot, [2.5, 97.5]).tolist() if boot else [math.nan, math.nan]
    return {
        "intercept_frame_at_x0": float(intercept),
        "slope_frame_per_green_px": float(slope),
        "endpoint_change_frames": endpoint_change,
        "endpoint_change_95pct": interval,
        "residual_rms_frames": float(np.sqrt(np.mean(raw_residual**2))),
        "residual_p95_abs_frames": float(np.percentile(np.abs(raw_residual), 95)),
        "bootstrap_n": len(boot),
    }


def save_preview(
    image: np.ndarray,
    baseline: float,
    centres: np.ndarray,
    destination: Path,
) -> None:
    step = 2
    small = image[::step, ::step]
    lo, hi = np.percentile(small, [0.1, 99.9])
    rendered = np.round(255.0 * np.clip((small - lo) / max(float(hi - lo), 1.0), 0, 1)).astype(
        np.uint8
    )
    rgb = Image.fromarray(rendered).convert("RGB")
    draw = ImageDraw.Draw(rgb)
    y = baseline / step
    draw.line([(0, y), (rgb.width - 1, y)], fill=(255, 0, 0), width=2)
    for index, centre in enumerate(centres):
        x = centre / step
        draw.line([(x, y), (x, rgb.height - 1)], fill=(0, 255, 0), width=1)
        draw.text((x + 2, y + 4), str(index), fill=(255, 255, 0))
    rgb.save(destination)


def jsonable(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, dict):
        return {key: jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    frames = sorted(args.stack.glob("*.ARW"))
    if not frames:
        raise RuntimeError(f"no ARWs found in {args.stack}")

    print(f"CONTROL_FIRST stack={args.stack} frames={len(frames)}", flush=True)
    global_scores = []
    metadata = None
    for index, frame in enumerate(frames):
        g1, g2, current_metadata = load_greens(frame)
        if metadata is None:
            metadata = current_metadata
        elif current_metadata != metadata:
            raise RuntimeError(f"decoded metadata changed at {frame}")
        score = global_focus_score(0.5 * (g1 + g2))
        global_scores.append(score)
        if index % 10 == 0 or index + 1 == len(frames):
            print(f"pass1 frame={index:03d} global_focus={score:.9f}", flush=True)

    sharp_index = int(np.argmax(global_scores))
    sharp_g1, sharp_g2, _ = load_greens(frames[sharp_index])
    sharp = 0.5 * (sharp_g1 + sharp_g2)
    baseline, slope = localise_baseline(sharp)
    sharp_rectified = rectify_rows(sharp, baseline, slope)
    baseline_rectified = baseline
    ticks = detect_ticks(sharp_rectified, baseline_rectified)
    centres = np.asarray(ticks["centres_green_px"])
    intervals = np.asarray(ticks["intervals_green_px"])
    if centres.size < 3:
        raise RuntimeError(f"tick detector found only {centres.size} lines")

    centre_g1, ci_g1, fwhm_g1 = tick_localisation(
        rectify_rows(sharp_g1, baseline, slope),
        baseline_rectified,
        centres,
        tuple(ticks["band"]),
    )
    centre_g2, ci_g2, fwhm_g2 = tick_localisation(
        rectify_rows(sharp_g2, baseline, slope),
        baseline_rectified,
        centres,
        tuple(ticks["band"]),
    )
    centres_replicated = 0.5 * (centre_g1 + centre_g2)
    replicate_delta_sensor = 2.0 * (centre_g2 - centre_g1)
    localisation_ci_sensor = 2.0 * np.maximum(ci_g1, ci_g2)
    edge_fwhm_sensor = 2.0 * np.concatenate([fwhm_g1.ravel(), fwhm_g2.ravel()])
    edge_fwhm_sensor = edge_fwhm_sensor[np.isfinite(edge_fwhm_sensor)]

    print(
        f"geometry sharp_frame={sharp_index} baseline_green={baseline:.3f} "
        f"slope={slope:.9f} ticks={centres.size} intervals={intervals.size}",
        flush=True,
    )

    n_intervals = centres.size - 1
    curves = np.full((2, n_intervals, len(frames)), np.nan, dtype=np.float64)
    tracked_centres = np.full((len(frames), centres.size), np.nan, dtype=np.float64)
    baseline_by_frame = np.full(len(frames), np.nan, dtype=np.float64)
    for frame_index, frame in enumerate(frames):
        g1, g2, _ = load_greens(frame)
        mean = 0.5 * (g1 + g2)
        current_baseline, current_slope = localise_baseline(mean, baseline)
        g1 = rectify_rows(g1, current_baseline, current_slope)
        g2 = rectify_rows(g2, current_baseline, current_slope)
        mean = 0.5 * (g1 + g2)
        current_centres = track_ticks(mean, current_baseline, centres)
        tracked_centres[frame_index] = current_centres
        baseline_by_frame[frame_index] = current_baseline
        for plane_index, plane in enumerate((g1, g2)):
            field = focus_field(plane)
            y0 = min(plane.shape[0] - 2, int(round(current_baseline + 55)))
            y1 = plane.shape[0] - max(25, plane.shape[0] // 100)
            for interval_index in range(n_intervals):
                left, right = current_centres[interval_index : interval_index + 2]
                margin = 0.22 * (right - left)
                x0 = max(0, int(round(left + margin)))
                x1 = min(plane.shape[1], int(round(right - margin)))
                patch = plane[y0:y1, x0:x1]
                focus_patch = field[y0:y1, x0:x1]
                if patch.size == 0:
                    continue
                curves[plane_index, interval_index, frame_index] = float(
                    np.mean(focus_patch) / robust_contrast(patch)
                )
        if frame_index % 10 == 0 or frame_index + 1 == len(frames):
            print(f"pass2 frame={frame_index:03d}", flush=True)

    peak_by_plane = np.full((2, n_intervals), np.nan)
    status_by_plane: list[list[str]] = [[], []]
    for plane_index in range(2):
        for interval_index in range(n_intervals):
            peak, status = peak_position(curves[plane_index, interval_index])
            peak_by_plane[plane_index, interval_index] = peak
            status_by_plane[plane_index].append(status)

    accepted = np.array(
        [
            status_by_plane[0][i] == "accepted"
            and status_by_plane[1][i] == "accepted"
            and abs(peak_by_plane[0, i] - peak_by_plane[1, i]) <= 0.25
            for i in range(n_intervals)
        ]
    )
    interval_x = 0.5 * (centres_replicated[:-1] + centres_replicated[1:])
    peak_mean = np.mean(peak_by_plane, axis=0)
    focus_fit = (
        fit_focus_line(interval_x[accepted], peak_mean[accepted])
        if np.count_nonzero(accepted) >= 3
        else None
    )

    interval_sensor = 2.0 * np.diff(centres_replicated)
    coverage = float((centres_replicated[-1] - centres_replicated[0]) / sharp.shape[1])
    spacing_cv = float(np.std(interval_sensor, ddof=1) / np.mean(interval_sensor))
    output = {
        "claim_class": "MEASURED",
        "stack": str(args.stack),
        "frame_count": len(frames),
        "frame_order": [frame.name for frame in frames],
        "decoded": metadata,
        "global_focus": {
            "sharp_frame_zero_based": sharp_index,
            "sharp_file": frames[sharp_index].name,
            "scores": global_scores,
        },
        "geometry": {
            "baseline_centre_green_px": baseline,
            "baseline_slope_green_y_per_x": slope,
            "baseline_angle_deg": math.degrees(math.atan(slope)),
            "longitudinal_lines_detected": 1,
            "tick_lines": int(centres.size),
            "minor_intervals": int(intervals.size),
            "coverage_fraction_width": coverage,
            "centres_sensor_px": 2.0 * centres_replicated,
            "intervals_sensor_px": interval_sensor,
            "interval_median_sensor_px": float(np.median(interval_sensor)),
            "interval_min_sensor_px": float(np.min(interval_sensor)),
            "interval_max_sensor_px": float(np.max(interval_sensor)),
            "interval_cv": spacing_cv,
            "g2_minus_g1_centres_sensor_px": replicate_delta_sensor,
            "localisation_95pct_width_sensor_px": localisation_ci_sensor,
            "localisation_median_95pct_width_sensor_px": float(
                np.nanmedian(localisation_ci_sensor)
            ),
            "localisation_p95_95pct_width_sensor_px": float(
                np.nanpercentile(localisation_ci_sensor, 95)
            ),
            "edge_lsf_fwhm_median_sensor_px": float(np.median(edge_fwhm_sensor)),
            "edge_lsf_fwhm_p95_sensor_px": float(np.percentile(edge_fwhm_sensor, 95)),
            "second_boundary_available": False,
            "printed_labels_or_unit_legend_visible": False,
            "physical_pitch_identified": False,
        },
        "focus": {
            "peak_frame_by_green": peak_by_plane,
            "status_by_green": status_by_plane,
            "accepted_intervals": accepted,
            "accepted_count": int(np.count_nonzero(accepted)),
            "mean_peak_frame": peak_mean,
            "focus_line": focus_fit,
            "curves": curves,
            "tracked_centres_green_px": tracked_centres,
            "baseline_by_frame_green_px": baseline_by_frame,
        },
    }

    endpoint_pass = bool(
        focus_fit
        and abs(float(focus_fit["endpoint_change_frames"])) <= 1.0
        and float(focus_fit["endpoint_change_95pct"][0]) <= 0.0
        <= float(focus_fit["endpoint_change_95pct"][1])
    )
    localisation_pass = bool(
        output["geometry"]["localisation_median_95pct_width_sensor_px"] <= 1.0
        and output["geometry"]["localisation_p95_95pct_width_sensor_px"] <= 2.0
    )
    output["gates"] = {
        "at_least_20_graduations": bool(centres.size >= 21),
        "coverage_at_least_40pct": coverage >= 0.40,
        "at_least_20_accepted_focus_positions": int(np.count_nonzero(accepted)) >= 20,
        "focus_endpoint_change": endpoint_pass,
        "tick_localisation": localisation_pass,
        "two_longitudinal_boundaries": False,
        "physical_pitch_from_image": False,
    }
    output["control_pass"] = bool(all(output["gates"].values()))
    failures = [name for name, passed in output["gates"].items() if not passed]
    output["failure_reasons"] = failures

    result_path = args.output / "control-result.json"
    result_path.write_text(
        json.dumps(jsonable(output), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(
        args.output / "control-focus-curves.npz",
        curves=curves,
        peaks=peak_by_plane,
        accepted=accepted,
        interval_x_green=interval_x,
        tick_centres_green=centres_replicated,
        tracked_centres_green=tracked_centres,
    )
    save_preview(sharp_rectified, baseline_rectified, centres, args.output / "control-geometry.png")

    print(f"CONTROL_RESULT={result_path}", flush=True)
    print(f"CONTROL_PASS={output['control_pass']}", flush=True)
    print(f"CONTROL_FAILURES={','.join(failures)}", flush=True)
    if focus_fit:
        print(
            "CONTROL_FOCUS "
            f"endpoint={focus_fit['endpoint_change_frames']:.6f} "
            f"ci95={focus_fit['endpoint_change_95pct']} "
            f"rms={focus_fit['residual_rms_frames']:.6f}",
            flush=True,
        )
    print(
        "CONTROL_SPACING "
        f"median={output['geometry']['interval_median_sensor_px']:.6f} sensor_px "
        f"min={output['geometry']['interval_min_sensor_px']:.6f} "
        f"max={output['geometry']['interval_max_sensor_px']:.6f}",
        flush=True,
    )


if __name__ == "__main__":
    main()
