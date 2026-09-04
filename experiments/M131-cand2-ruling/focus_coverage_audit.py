from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
import rawpy
from scipy import signal


HERE = Path(__file__).resolve().parent
ROOT = Path(
    r"D:\personal\macro\requests\misc-diagnostic"
    r"\high-res-calibration-slide-cpl"
)
STACKS = {
    "tilted-sw4": {
        "path": ROOT / "tilted-sw4-cpl",
        "expected_frames": 182,
        "tail_frames": 26,
        "smooth_window": 11,
        "jitter_window": 21,
        "endpoint_guard": 6,
    },
    "tilted-sw10": {
        "path": ROOT / "tilted-sw10-cpl",
        "expected_frames": 92,
        "tail_frames": 14,
        "smooth_window": 5,
        "jitter_window": 11,
        "endpoint_guard": 4,
    },
}
GRID_ROWS = 8
GRID_COLS = 8
QUAD_SAMPLE_STEP = 4
RAW_PIXELS_PER_LOWRES_PIXEL = 2 * QUAD_SAMPLE_STEP
PROMINENCE_THRESHOLDS = (1.02, 1.05, 1.10)


def files_for(path: Path) -> list[Path]:
    return sorted(
        (
            entry
            for entry in path.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".arw"
        ),
        key=lambda entry: entry.name,
    )


def decode_lowres(path: Path) -> tuple[np.ndarray, dict]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        pattern = raw.raw_pattern.copy()
        greens = [
            (row, col, int(pattern[row, col]))
            for row in range(2)
            for col in range(2)
            if int(pattern[row, col]) in (1, 3)
        ]
        if len(greens) != 2:
            raise RuntimeError(f"expected two green phases in {path}")
        planes = []
        for row, col, color in greens:
            black = float(raw.black_level_per_channel[color])
            white = float(raw.white_level)
            plane = visible[row::2, col::2]
            sampled = plane[
                ::QUAD_SAMPLE_STEP,
                ::QUAD_SAMPLE_STEP,
            ].astype(np.float32)
            sampled = (sampled - black) / (white - black)
            planes.append(sampled)
        image = (0.5 * (planes[0] + planes[1])).astype(
            np.float32,
            copy=True,
        )
        shape = [int(visible.shape[0]), int(visible.shape[1])]
        low_shape = [int(image.shape[0]), int(image.shape[1])]
    return image, {
        "visible_raw_shape": shape,
        "lowres_shape": low_shape,
        "raw_pattern": pattern.tolist(),
    }


def site_bounds(height: int, width: int) -> list[tuple[int, int, int, int]]:
    y_margin = int(round(0.06 * height))
    x_margin = int(round(0.06 * width))
    ys = np.linspace(y_margin, height - y_margin, GRID_ROWS + 1).round().astype(int)
    xs = np.linspace(x_margin, width - x_margin, GRID_COLS + 1).round().astype(int)
    return [
        (int(ys[row]), int(ys[row + 1]), int(xs[col]), int(xs[col + 1]))
        for row in range(GRID_ROWS)
        for col in range(GRID_COLS)
    ]


def focus_metrics(
    image: np.ndarray,
    bounds: list[tuple[int, int, int, int]],
) -> tuple[np.ndarray, np.ndarray]:
    tenengrad = []
    laplacian = []
    for y0, y1, x0, x1 in bounds:
        cell = image[y0 + 4 : y1 - 4, x0 + 4 : x1 - 4]
        level = max(float(np.mean(cell)), 1.0e-6)
        gx = cv2.Sobel(
            cell,
            cv2.CV_32F,
            1,
            0,
            ksize=3,
            borderType=cv2.BORDER_REFLECT101,
        )
        gy = cv2.Sobel(
            cell,
            cv2.CV_32F,
            0,
            1,
            ksize=3,
            borderType=cv2.BORDER_REFLECT101,
        )
        lap = cv2.Laplacian(
            cell,
            cv2.CV_32F,
            ksize=3,
            borderType=cv2.BORDER_REFLECT101,
        )
        tenengrad.append(float(np.mean(gx * gx + gy * gy) / (level * level)))
        laplacian.append(float(np.var(lap) / (level * level)))
    return (
        np.asarray(tenengrad, dtype=np.float64),
        np.asarray(laplacian, dtype=np.float64),
    )


def phase_shift(
    previous: np.ndarray,
    current: np.ndarray,
) -> tuple[float, float, float]:
    height, width = previous.shape
    y0, y1 = int(0.15 * height), int(0.85 * height)
    x0, x1 = int(0.15 * width), int(0.85 * width)
    left = cv2.GaussianBlur(previous[y0:y1, x0:x1], (0, 0), 1.5)
    right = cv2.GaussianBlur(current[y0:y1, x0:x1], (0, 0), 1.5)
    left = (left - float(left.mean())) / max(float(left.std()), 1.0e-6)
    right = (right - float(right.mean())) / max(float(right.std()), 1.0e-6)
    window = cv2.createHanningWindow(
        (left.shape[1], left.shape[0]),
        cv2.CV_32F,
    )
    (dx, dy), response = cv2.phaseCorrelate(left, right, window)
    return float(dx), float(dy), float(response)


def smooth_curves(values: np.ndarray, window: int) -> np.ndarray:
    return signal.savgol_filter(
        values,
        window_length=window,
        polyorder=2,
        axis=0,
        mode="interp",
    )


def curve_summary(
    values: np.ndarray,
    window: int,
    guard: int,
    tail_frames: int,
) -> dict:
    smoothed = smooth_curves(values, window)
    peaks = np.argmax(smoothed, axis=0)
    peak_values = smoothed[peaks, np.arange(smoothed.shape[1])]
    endpoint_values = np.maximum(
        np.max(smoothed[:guard], axis=0),
        np.max(smoothed[-guard:], axis=0),
    )
    prominence = peak_values / np.maximum(endpoint_values, 1.0e-30)
    interior = (peaks >= guard) & (peaks < len(smoothed) - guard)
    threshold_counts = {}
    threshold_masks = {}
    for threshold in PROMINENCE_THRESHOLDS:
        mask = interior & (prominence >= threshold)
        threshold_counts[str(threshold)] = int(np.count_nonzero(mask))
        threshold_masks[str(threshold)] = mask
    return {
        "peaks": peaks,
        "prominence": prominence,
        "interior": interior,
        "threshold_counts": threshold_counts,
        "threshold_masks": threshold_masks,
        "peaks_in_tail_bucket": int(
            np.count_nonzero(peaks >= len(smoothed) - tail_frames)
        ),
        "minimum_peak_index": int(peaks.min()),
        "maximum_peak_index": int(peaks.max()),
        "median_peak_index": float(np.median(peaks)),
    }


def jitter_summary(
    increments: np.ndarray,
    window: int,
) -> dict:
    cumulative = np.vstack(
        [np.zeros((1, 2), dtype=np.float64), np.cumsum(increments, axis=0)]
    )
    smooth = signal.savgol_filter(
        cumulative,
        window_length=window,
        polyorder=2,
        axis=0,
        mode="interp",
    )
    residual = cumulative - smooth
    increment_magnitude = np.linalg.norm(increments, axis=1)
    residual_magnitude = np.linalg.norm(residual, axis=1)
    return {
        "increment_lowres_px": {
            "rms": float(math.sqrt(np.mean(increment_magnitude**2))),
            "p95": float(np.quantile(increment_magnitude, 0.95)),
            "maximum": float(increment_magnitude.max()),
        },
        "increment_raw_px": {
            "rms": float(
                RAW_PIXELS_PER_LOWRES_PIXEL * math.sqrt(np.mean(increment_magnitude**2))
            ),
            "p95": float(
                RAW_PIXELS_PER_LOWRES_PIXEL * np.quantile(increment_magnitude, 0.95)
            ),
            "maximum": float(RAW_PIXELS_PER_LOWRES_PIXEL * increment_magnitude.max()),
        },
        "detrended_residual_raw_px": {
            "rms": float(
                RAW_PIXELS_PER_LOWRES_PIXEL * math.sqrt(np.mean(residual_magnitude**2))
            ),
            "p95": float(
                RAW_PIXELS_PER_LOWRES_PIXEL * np.quantile(residual_magnitude, 0.95)
            ),
            "maximum": float(RAW_PIXELS_PER_LOWRES_PIXEL * residual_magnitude.max()),
        },
        "cumulative_span_raw_px": {
            "x": float(
                RAW_PIXELS_PER_LOWRES_PIXEL
                * (cumulative[:, 0].max() - cumulative[:, 0].min())
            ),
            "y": float(
                RAW_PIXELS_PER_LOWRES_PIXEL
                * (cumulative[:, 1].max() - cumulative[:, 1].min())
            ),
        },
    }


def process_stack(label: str, config: dict) -> tuple[dict, dict[str, np.ndarray]]:
    files = files_for(config["path"])
    if len(files) != config["expected_frames"]:
        raise RuntimeError(
            f"{label}: {len(files)} frames, expected {config['expected_frames']}"
        )
    tenengrad_rows = []
    laplacian_rows = []
    shifts = []
    responses = []
    previous = None
    geometry = None
    bounds = None
    for index, path in enumerate(files):
        image, frame_geometry = decode_lowres(path)
        if geometry is None:
            geometry = frame_geometry
            bounds = site_bounds(*image.shape)
        elif frame_geometry != geometry:
            raise RuntimeError(f"{label}: RAW geometry changed at {path.name}")
        tenengrad, laplacian = focus_metrics(image, bounds)
        tenengrad_rows.append(tenengrad)
        laplacian_rows.append(laplacian)
        if previous is not None:
            dx, dy, response = phase_shift(previous, image)
            shifts.append((dx, dy))
            responses.append(response)
        previous = image
        if (index + 1) % 25 == 0 or index + 1 == len(files):
            print(f"{label}: decoded {index + 1}/{len(files)}", flush=True)
    tenengrad_values = np.asarray(tenengrad_rows, dtype=np.float64)
    laplacian_values = np.asarray(laplacian_rows, dtype=np.float64)
    increments = np.asarray(shifts, dtype=np.float64)
    tenengrad_summary = curve_summary(
        tenengrad_values,
        config["smooth_window"],
        config["endpoint_guard"],
        config["tail_frames"],
    )
    laplacian_summary = curve_summary(
        laplacian_values,
        config["smooth_window"],
        config["endpoint_guard"],
        config["tail_frames"],
    )
    intersections = {}
    for threshold in PROMINENCE_THRESHOLDS:
        key = str(threshold)
        intersections[key] = int(
            np.count_nonzero(
                tenengrad_summary["threshold_masks"][key]
                & laplacian_summary["threshold_masks"][key]
            )
        )
    record = {
        "path": str(config["path"]),
        "frames": len(files),
        "first_file": files[0].name,
        "last_file": files[-1].name,
        "total_bytes": sum(path.stat().st_size for path in files),
        "geometry": geometry,
        "site_grid": [GRID_ROWS, GRID_COLS],
        "site_count": GRID_ROWS * GRID_COLS,
        "quad_sample_step": QUAD_SAMPLE_STEP,
        "raw_pixels_per_lowres_pixel": RAW_PIXELS_PER_LOWRES_PIXEL,
        "smooth_window": config["smooth_window"],
        "endpoint_guard": config["endpoint_guard"],
        "tail_frames": config["tail_frames"],
        "tenengrad": {
            key: value
            for key, value in tenengrad_summary.items()
            if key not in ("peaks", "prominence", "interior", "threshold_masks")
        },
        "laplacian": {
            key: value
            for key, value in laplacian_summary.items()
            if key not in ("peaks", "prominence", "interior", "threshold_masks")
        },
        "both_metrics_qualifying_sites": intersections,
        "phase_correlation": {
            "response_minimum": float(np.min(responses)),
            "response_median": float(np.median(responses)),
            "response_maximum": float(np.max(responses)),
            **jitter_summary(increments, config["jitter_window"]),
        },
    }
    arrays = {
        "tenengrad": tenengrad_values,
        "laplacian": laplacian_values,
        "tenengrad_peaks": tenengrad_summary["peaks"],
        "tenengrad_prominence": tenengrad_summary["prominence"],
        "laplacian_peaks": laplacian_summary["peaks"],
        "laplacian_prominence": laplacian_summary["prominence"],
        "phase_increments": increments,
        "phase_responses": np.asarray(responses, dtype=np.float64),
    }
    return record, arrays


def cross_stack_summary(arrays: dict[str, dict[str, np.ndarray]]) -> dict:
    rows = {}
    for metric in ("tenengrad", "laplacian"):
        peaks4 = arrays["tilted-sw4"][f"{metric}_peaks"].astype(np.float64)
        peaks10 = arrays["tilted-sw10"][f"{metric}_peaks"].astype(np.float64)
        slope, intercept = np.polyfit(peaks10, peaks4, 1)
        predicted = slope * peaks10 + intercept
        residual = peaks4 - predicted
        normalized4 = peaks4 / (STACKS["tilted-sw4"]["expected_frames"] - 1)
        normalized10 = peaks10 / (STACKS["tilted-sw10"]["expected_frames"] - 1)
        rows[metric] = {
            "sw4_from_sw10_linear_slope": float(slope),
            "sw4_from_sw10_linear_intercept": float(intercept),
            "peak_mapping_residual_rms_frames": float(math.sqrt(np.mean(residual**2))),
            "normalized_peak_difference": {
                "mean": float(np.mean(normalized4 - normalized10)),
                "rms": float(math.sqrt(np.mean((normalized4 - normalized10) ** 2))),
                "maximum_absolute": float(np.max(np.abs(normalized4 - normalized10))),
            },
            "peak_rank_correlation": float(np.corrcoef(peaks4, peaks10)[0, 1]),
        }
    return rows


def run(output: Path, arrays_path: Path) -> int:
    if output.exists() or arrays_path.exists():
        raise RuntimeError("refusing to overwrite focus audit artifacts")
    records = {}
    arrays = {}
    for label, config in STACKS.items():
        records[label], arrays[label] = process_stack(label, config)
    packed = {
        f"{label}_{name}": values
        for label, stack_arrays in arrays.items()
        for name, values in stack_arrays.items()
    }
    np.savez_compressed(arrays_path, **packed)
    cross = cross_stack_summary(arrays)
    record = {
        "protocol": "M131-image-focus-coverage-v1",
        "method": {
            "pixels": (
                "rawpy raw_image_visible; both green phases sampled inside the "
                "LibRaw context, converted/copied before close"
            ),
            "visible_area_only": True,
            "focus_metrics": [
                "mean squared Sobel gradient / local mean squared",
                "Laplacian variance / local mean squared",
            ],
            "sites": "fixed non-overlapping central 8x8 grid",
            "motion": (
                "adjacent-frame phase correlation on central low-frequency "
                "content; reports image motion, not a unique IBIS decomposition"
            ),
        },
        "stacks": records,
        "cross_stack_peak_mapping": cross,
        "arrays": {
            "path": str(arrays_path),
            "keys": sorted(packed),
        },
        "interpretation_rule": (
            "A 64-peak claim is made only if all 64 sites qualify in both "
            "metrics at a stated prominence threshold. EXIF focus bins are "
            "not used to locate peaks."
        ),
    }
    output.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        "sw4 both@1.05="
        f"{records['tilted-sw4']['both_metrics_qualifying_sites']['1.05']} "
        "sw10 both@1.05="
        f"{records['tilted-sw10']['both_metrics_qualifying_sites']['1.05']}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=HERE / "focus-coverage-audit.json",
    )
    parser.add_argument(
        "--arrays",
        type=Path,
        default=HERE / "focus-coverage-curves.npz",
    )
    args = parser.parse_args()
    return run(args.out.resolve(), args.arrays.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
