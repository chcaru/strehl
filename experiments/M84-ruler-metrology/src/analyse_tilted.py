"""Measure what remains readable after M84's mandatory control failed.

This is deliberately diagnostic: it never promotes a focus-index plane into
metric depth. The registered control failed before this script was run.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import cv2
import numpy as np
import rawpy
from PIL import Image
from scipy.optimize import least_squares


def load_green(path: Path, step: int = 4) -> tuple[np.ndarray, dict[str, object]]:
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.astype(np.float32)
        black = float(max(raw.black_level_per_channel))
        white = int(raw.white_level)
    height, width = visible.shape
    height -= height % 2
    width -= width % 2
    g1 = visible[:height:2, 1:width:2]
    g2 = visible[1:height:2, :width:2]
    green = 0.5 * (g1 + g2) - black
    sampled = green[::step, ::step].copy()
    return sampled, {
        "visible_sensor_shape": [height, width],
        "green_shape": list(green.shape),
        "analysis_shape": list(sampled.shape),
        "green_downsample": step,
        "sensor_pixels_per_analysis_pixel": 2 * step,
        "black": black,
        "white": white,
    }


def response(image: np.ndarray, green_step: int) -> np.ndarray:
    gx = cv2.Sobel(image, cv2.CV_32F, 1, 0, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    gy = cv2.Sobel(image, cv2.CV_32F, 0, 1, ksize=3, borderType=cv2.BORDER_REFLECT_101)
    magnitude = cv2.magnitude(gx, gy)
    support = max(3, int(round(27 / green_step)))
    if support % 2 == 0:
        support += 1
    field = cv2.boxFilter(
        magnitude,
        cv2.CV_32F,
        (support, support),
        normalize=True,
        borderType=cv2.BORDER_REFLECT_101,
    )
    level = cv2.boxFilter(
        np.abs(image),
        cv2.CV_32F,
        (support, support),
        normalize=True,
        borderType=cv2.BORDER_REFLECT_101,
    )
    return field / np.maximum(level, 1.0)


def fit_index_plane(
    index: np.ndarray,
    mask: np.ndarray,
    seed: int = 0x4D842026,
) -> dict[str, object] | None:
    yy, xx = np.nonzero(mask)
    if xx.size < 100:
        return None
    rng = np.random.default_rng(seed)
    if xx.size > 100_000:
        chosen = rng.choice(xx.size, 100_000, replace=False)
        xx, yy = xx[chosen], yy[chosen]
    zz = index[yy, xx].astype(np.float64)
    x0, y0 = float(np.mean(xx)), float(np.mean(yy))
    sx, sy = max(float(np.std(xx)), 1.0), max(float(np.std(yy)), 1.0)
    design = np.column_stack(
        [
            np.ones(xx.size),
            (xx - x0) / sx,
            (yy - y0) / sy,
        ]
    )
    initial, _, _, _ = np.linalg.lstsq(design, zz, rcond=None)
    scale = max(1.4826 * np.median(np.abs(zz - np.median(zz))), 1.0)
    fit = least_squares(
        lambda p: (design @ p - zz) / scale,
        initial,
        loss="huber",
        f_scale=1.5,
        max_nfev=200,
    )
    residual = zz - design @ fit.x
    return {
        "sample_count": int(xx.size),
        "coefficients_standardised": fit.x.tolist(),
        "x_mean": x0,
        "y_mean": y0,
        "x_sd": sx,
        "y_sd": sy,
        "residual_rms_frames": float(np.sqrt(np.mean(residual**2))),
        "residual_p95_abs_frames": float(np.percentile(np.abs(residual), 95)),
        "index_span_fitted_frames": float(
            np.ptp(
                [
                    fit.x[0]
                    + fit.x[1] * ((x - x0) / sx)
                    + fit.x[2] * ((y - y0) / sy)
                    for x in (float(np.min(xx)), float(np.max(xx)))
                    for y in (float(np.min(yy)), float(np.max(yy)))
                ]
            )
        ),
    }


def line_inventory(composite: np.ndarray) -> dict[str, object]:
    lo, hi = np.percentile(composite, [1.0, 99.0])
    scaled = np.clip((composite - lo) / max(float(hi - lo), 1.0), 0.0, 1.0)
    image = np.round(255.0 * scaled).astype(np.uint8)
    equalised = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(image)
    edges = cv2.Canny(equalised, 50, 150, apertureSize=3, L2gradient=True)
    lines = cv2.HoughLinesP(
        edges,
        1.0,
        np.pi / 1800.0,
        threshold=60,
        minLineLength=max(30, image.shape[0] // 12),
        maxLineGap=15,
    )
    records = []
    if lines is not None:
        for raw in lines[:, 0, :]:
            x0, y0, x1, y1 = (int(value) for value in raw)
            length = math.hypot(x1 - x0, y1 - y0)
            angle = math.degrees(math.atan2(y1 - y0, x1 - x0))
            if angle < -90:
                angle += 180
            if angle >= 90:
                angle -= 180
            records.append(
                {
                    "x0": x0,
                    "y0": y0,
                    "x1": x1,
                    "y1": y1,
                    "length_analysis_px": length,
                    "angle_deg": angle,
                }
            )
    records.sort(key=lambda item: item["length_analysis_px"], reverse=True)
    return {
        "line_count": len(records),
        "longest_lines": records[:100],
        "edge_fraction": float(np.mean(edges > 0)),
        "rendered": image,
        "edges": edges,
    }


def save_index(index: np.ndarray, confidence: np.ndarray, destination: Path, n: int) -> None:
    value = np.clip(index.astype(np.float32) / max(n - 1, 1), 0.0, 1.0)
    rgb = np.empty(index.shape + (3,), dtype=np.uint8)
    rgb[..., 0] = np.round(255 * value).astype(np.uint8)
    rgb[..., 1] = np.round(255 * (1.0 - np.abs(2.0 * value - 1.0))).astype(np.uint8)
    rgb[..., 2] = np.round(255 * (1.0 - value)).astype(np.uint8)
    rgb[confidence < 5.0] = [20, 20, 20]
    Image.fromarray(rgb).save(destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stack", type=Path)
    parser.add_argument("control_result", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--green-step", type=int, default=4)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    control = json.loads(args.control_result.read_text(encoding="utf-8"))
    if control["control_pass"]:
        raise RuntimeError("diagnostic tilted script expects the registered control to have failed")

    frames = sorted(args.stack.glob("*.ARW"))
    if not frames:
        raise RuntimeError(f"no ARWs in {args.stack}")

    count = 0
    mean = None
    m2 = None
    maximum = None
    minimum = None
    best_index = None
    best_intensity = None
    metadata = None
    global_scores: list[float] = []

    for frame_index, frame in enumerate(frames):
        image, current_metadata = load_green(frame, args.green_step)
        if metadata is None:
            metadata = current_metadata
            mean = np.zeros_like(image, dtype=np.float64)
            m2 = np.zeros_like(image, dtype=np.float64)
            maximum = np.full_like(image, -np.inf, dtype=np.float32)
            minimum = np.full_like(image, np.inf, dtype=np.float32)
            best_index = np.zeros(image.shape, dtype=np.uint16)
            best_intensity = np.zeros_like(image, dtype=np.float32)
        elif metadata != current_metadata:
            raise RuntimeError(f"decode metadata changed at {frame}")

        field = response(image, args.green_step)
        count += 1
        delta = field - mean
        mean += delta / count
        m2 += delta * (field - mean)
        better = field > maximum
        maximum[better] = field[better]
        best_index[better] = frame_index
        best_intensity[better] = image[better]
        np.minimum(minimum, field, out=minimum)
        global_scores.append(float(np.mean(field)))
        if frame_index % 25 == 0 or frame_index + 1 == len(frames):
            print(f"tilted frame={frame_index:03d} global={global_scores[-1]:.9f}", flush=True)

    assert mean is not None
    assert m2 is not None
    assert maximum is not None
    assert minimum is not None
    assert best_index is not None
    assert best_intensity is not None
    sd = np.sqrt(np.maximum(m2 / max(count - 1, 1), 1e-18))
    confidence = (maximum - mean) / sd
    interior = np.ones(best_index.shape, dtype=bool)
    border = max(2, int(round(27 / args.green_step)))
    interior[:border] = False
    interior[-border:] = False
    interior[:, :border] = False
    interior[:, -border:] = False
    not_endpoint = (best_index > 0) & (best_index < len(frames) - 1)
    readable = (confidence >= 5.0) & interior & not_endpoint

    components, labels, stats, _ = cv2.connectedComponentsWithStats(
        readable.astype(np.uint8), connectivity=8
    )
    component_areas = sorted(
        (int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, components)),
        reverse=True,
    )
    largest_fraction = (
        component_areas[0] / readable.size if component_areas else 0.0
    )
    plane = fit_index_plane(best_index, readable)
    inventory = line_inventory(best_intensity)

    result = {
        "claim_class": "MEASURED",
        "role": "diagnostic-only-after-mandatory-control-failure",
        "stack": str(args.stack),
        "frame_count": len(frames),
        "decoded": metadata,
        "control_pass": False,
        "control_failures": control["failure_reasons"],
        "focus_readability": {
            "confidence_definition": "(max - temporal_mean) / temporal_sd",
            "confidence_threshold": 5.0,
            "readable_fraction_full_frame": float(np.mean(readable)),
            "readable_pixels": int(np.count_nonzero(readable)),
            "largest_connected_readable_fraction_full_frame": largest_fraction,
            "component_count": len(component_areas),
            "component_area_top10": component_areas[:10],
            "best_index_p05_p50_p95": (
                np.percentile(best_index[readable], [5, 50, 95]).tolist()
                if np.any(readable)
                else None
            ),
            "global_scores": global_scores,
        },
        "unmasked_index_plane": plane,
        "line_inventory": {
            key: value
            for key, value in inventory.items()
            if key not in {"rendered", "edges"}
        },
        "metric_geometry": {
            "tilt_deg": None,
            "magnification": None,
            "focus_step_um_per_frame": None,
            "reason": (
                "The zero-tilt control failed, physical pitch is not image-identified, "
                "and the capture supplies no two-boundary metric ruler plane."
            ),
        },
        "depth_map": {
            "emitted": False,
            "valid_pixels": 0,
            "reason": "pose and physical scale are unidentified; an all-false map would be misleading",
        },
    }

    (args.output / "tilted-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    np.save(args.output / "tilted-best-index.npy", best_index)
    np.save(args.output / "tilted-confidence.npy", confidence.astype(np.float32))
    save_index(
        best_index,
        confidence,
        args.output / "tilted-best-index.png",
        len(frames),
    )
    Image.fromarray(inventory["rendered"]).save(args.output / "tilted-all-focus.png")
    Image.fromarray(inventory["edges"]).save(args.output / "tilted-all-focus-edges.png")

    print(
        "TILTED_DIAGNOSTIC "
        f"readable={result['focus_readability']['readable_fraction_full_frame']:.6f} "
        f"largest_component={largest_fraction:.6f} "
        f"lines={result['line_inventory']['line_count']} "
        f"depth_map_emitted=False",
        flush=True,
    )


if __name__ == "__main__":
    main()
