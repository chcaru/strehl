"""Commission and run the owner's existing flat-ROI noise instrument.

This script is deliberately read-only with respect to every image input.  Its
only output is results.json beside this file.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, uniform_filter


ROOT = Path(__file__).resolve().parent
RESULTS_PATH = ROOT / "results.json"

TILE = 384
STEP = 192
SITE_COUNT = 12


@dataclass(frozen=True)
class Arm:
    name: str
    path: Path
    encoding: str


@dataclass(frozen=True)
class Geometry:
    reference: str
    target: str
    center_y: float
    center_x: float
    a: float
    b: float
    tx: float
    ty: float
    tile_count: int
    snr_tile_count: int
    inlier_tile_count: int
    residual_rms_px: float
    residual_max_px: float
    median_snr: float

    @property
    def scale(self) -> float:
        return math.hypot(self.a, self.b)

    @property
    def rotation_deg(self) -> float:
        return math.degrees(math.atan2(self.b, self.a))

    def point(self, y: float, x: float) -> tuple[float, float]:
        xx = x - self.center_x
        yy = y - self.center_y
        target_x = self.a * xx - self.b * yy + self.center_x + self.tx
        target_y = self.b * xx + self.a * yy + self.center_y + self.ty
        return target_y, target_x

    def box(self, y: int, x: int, size: int) -> tuple[int, int, int]:
        target_y, target_x = self.point(y + size / 2.0, x + size / 2.0)
        target_size = int(round(size * self.scale))
        y0 = int(round(target_y - target_size / 2.0))
        x0 = int(round(target_x - target_size / 2.0))
        return y0, x0, target_size

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference": self.reference,
            "target": self.target,
            "mapping": (
                "target = scale*R(reference - reference_center) "
                "+ reference_center + translation"
            ),
            "scale": self.scale,
            "rotation_deg": self.rotation_deg,
            "translation_x_px": self.tx,
            "translation_y_px": self.ty,
            "tiles_evaluated": self.tile_count,
            "tiles_passing_snr_gt_10": self.snr_tile_count,
            "similarity_inlier_tiles": self.inlier_tile_count,
            "residual_rms_px": self.residual_rms_px,
            "residual_max_px": self.residual_max_px,
            "median_snr_all_tiles": self.median_snr,
        }


COFFEE_FORK = Arm(
    "focus-stack fork",
    Path(r"C:\dev\macro\out\coffee-bean\stack.tif"),
    "linear-float",
)
SUBJECT2_FORK = Arm(
    "focus-stack fork",
    Path(r"C:\dev\macro\out\stack_test2_rec2020.tif"),
    "linear-float",
)
SUBJECT2_ZERENE = Arm(
    "Zerene Stacker PMax",
    Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
    "linear-u16",
)
COFFEE_STREHL = Arm(
    "strehl DELIVER-V6",
    Path(r"C:\dev\strehl-out\DELIVER-V6\masters\coffee-bean.tiff"),
    "strehl-srgb-u16",
)
SUBJECT2_STREHL = Arm(
    "strehl DELIVER-V6",
    Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff"),
    "strehl-srgb-u16",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def image_info(arm: Arm) -> dict[str, Any]:
    image = tifffile.memmap(arm.path, mode="r")
    info = {
        "name": arm.name,
        "path": str(arm.path),
        "bytes": arm.path.stat().st_size,
        "sha256": sha256(arm.path),
        "shape": list(image.shape),
        "dtype": str(image.dtype),
        "encoding": arm.encoding,
    }
    del image
    return info


def raw_green(arm: Arm) -> np.ndarray:
    image = tifffile.memmap(arm.path, mode="r")
    green = np.ascontiguousarray(image[:, :, 1], dtype=np.float32)
    if np.issubdtype(image.dtype, np.integer):
        green /= np.iinfo(image.dtype).max
    del image
    return green


def box_average(image: np.ndarray, factor: int) -> np.ndarray:
    height = (image.shape[0] // factor) * factor
    width = (image.shape[1] // factor) * factor
    return image[:height, :width].reshape(
        height // factor, factor, width // factor, factor
    ).mean(axis=(1, 3))


def phase_prepare(tile: np.ndarray) -> np.ndarray | None:
    tile = np.asarray(tile, np.float32)
    median = float(np.median(tile))
    tile = np.log1p(np.maximum(tile - tile.min(), 0) / (abs(median) + 1e-6))
    tile -= tile.mean()
    standard_deviation = float(tile.std())
    if standard_deviation < 1e-6:
        return None
    window = np.hanning(tile.shape[0])[:, None] * np.hanning(tile.shape[1])[None, :]
    return (tile / standard_deviation) * window


def phase_correlation(
    first: np.ndarray, second: np.ndarray
) -> tuple[int, int, float]:
    first_fft = np.fft.rfft2(first)
    second_fft = np.fft.rfft2(second)
    cross = first_fft * np.conj(second_fft)
    cross /= np.abs(cross) + 1e-12
    correlation = np.fft.irfft2(cross, s=first.shape)
    index = int(np.argmax(correlation))
    dy, dx = np.unravel_index(index, correlation.shape)
    peak = float(correlation.flat[index])
    standard_deviation = float(correlation.std())
    if dy > first.shape[0] // 2:
        dy -= first.shape[0]
    if dx > first.shape[1] // 2:
        dx -= first.shape[1]
    snr = peak / standard_deviation if standard_deviation > 0 else 0.0
    return int(dy), int(dx), float(snr)


def fit_geometry(reference: Arm, target: Arm) -> Geometry:
    reference_green = raw_green(reference)
    target_green = raw_green(target)

    reduction = 8
    reference_small = box_average(reference_green, reduction)
    target_small = box_average(target_green, reduction)
    height = min(reference_small.shape[0], target_small.shape[0])
    width = min(reference_small.shape[1], target_small.shape[1])
    gross_target = phase_prepare(target_small[:height, :width])
    gross_reference = phase_prepare(reference_small[:height, :width])
    if gross_target is None or gross_reference is None:
        raise RuntimeError("full-frame phase preparation unexpectedly failed")
    gross_dy, gross_dx, _ = phase_correlation(gross_target, gross_reference)
    gross_dy *= reduction
    gross_dx *= reduction

    tile_size = 512
    ys = np.linspace(
        300, reference_green.shape[0] - 300 - tile_size, 8
    ).astype(int)
    xs = np.linspace(
        300, reference_green.shape[1] - 300 - tile_size, 11
    ).astype(int)
    rows: list[tuple[float, float, float, float, float]] = []
    for y in ys:
        for x in xs:
            target_y = y + gross_dy
            target_x = x + gross_dx
            if (
                target_y < 0
                or target_x < 0
                or target_y + tile_size > target_green.shape[0]
                or target_x + tile_size > target_green.shape[1]
            ):
                continue
            reference_tile = reference_green[y : y + tile_size, x : x + tile_size]
            target_tile = target_green[
                target_y : target_y + tile_size,
                target_x : target_x + tile_size,
            ]
            prepared_reference = phase_prepare(reference_tile)
            prepared_target = phase_prepare(target_tile)
            if prepared_reference is None or prepared_target is None:
                continue
            dy, dx, snr = phase_correlation(prepared_target, prepared_reference)
            rows.append(
                (y + tile_size / 2, x + tile_size / 2, dy, dx, snr)
            )

    del reference_green, target_green
    measured = np.asarray(rows, dtype=np.float64)
    if measured.shape[0] < 12:
        raise RuntimeError(
            f"only {measured.shape[0]} geometry tiles were measurable for "
            f"{reference.name} -> {target.name}"
        )
    kept = measured[measured[:, 4] > 10.0]
    if kept.shape[0] < 8:
        raise RuntimeError(
            f"only {kept.shape[0]} geometry tiles passed SNR > 10 for "
            f"{reference.name} -> {target.name}"
        )

    center_y = tifffile.memmap(reference.path, mode="r").shape[0] / 2
    center_x = tifffile.memmap(reference.path, mode="r").shape[1] / 2
    centered_y = kept[:, 0] - center_y
    centered_x = kept[:, 1] - center_x
    residual_dy = kept[:, 2]
    residual_dx = kept[:, 3]
    design = np.zeros((2 * kept.shape[0], 4), dtype=np.float64)
    rhs = np.zeros(2 * kept.shape[0], dtype=np.float64)
    design[0::2, 0] = centered_x
    design[0::2, 1] = -centered_y
    design[0::2, 2] = 1.0
    design[1::2, 0] = centered_y
    design[1::2, 1] = centered_x
    design[1::2, 3] = 1.0
    rhs[0::2] = residual_dx
    rhs[1::2] = residual_dy

    def fit(indices: np.ndarray) -> np.ndarray:
        equations = np.ravel(
            np.column_stack((2 * indices, 2 * indices + 1))
        )
        solution, *_ = np.linalg.lstsq(design[equations], rhs[equations], rcond=None)
        return solution

    def radial_residual(solution: np.ndarray) -> np.ndarray:
        component = (design @ solution - rhs).reshape(-1, 2)
        return np.sqrt(np.sum(component * component, axis=1))

    best_inliers: np.ndarray | None = None
    best_score: tuple[int, float] | None = None
    threshold = 12.0
    for first in range(kept.shape[0] - 1):
        for second in range(first + 1, kept.shape[0]):
            pair = np.asarray([first, second])
            candidate = fit(pair)
            residual_radius = radial_residual(candidate)
            inliers = np.flatnonzero(residual_radius <= threshold)
            if inliers.size < 4:
                continue
            score = (
                int(inliers.size),
                -float(np.median(residual_radius[inliers])),
            )
            if best_score is None or score > best_score:
                best_score = score
                best_inliers = inliers
    if best_inliers is None or best_inliers.size < 6:
        raise RuntimeError(
            f"robust similarity found only "
            f"{0 if best_inliers is None else best_inliers.size} inliers for "
            f"{reference.name} -> {target.name}"
        )
    for _ in range(4):
        solution = fit(best_inliers)
        residual_radius = radial_residual(solution)
        revised = np.flatnonzero(residual_radius <= threshold)
        if np.array_equal(revised, best_inliers):
            break
        best_inliers = revised
    solution = fit(best_inliers)
    delta_a, b, local_tx, local_ty = solution
    component_residual = (design @ solution - rhs).reshape(-1, 2)
    inlier_residual = component_residual[best_inliers]
    return Geometry(
        reference=reference.name,
        target=target.name,
        center_y=center_y,
        center_x=center_x,
        a=1.0 + float(delta_a),
        b=float(b),
        tx=float(local_tx + gross_dx),
        ty=float(local_ty + gross_dy),
        tile_count=int(measured.shape[0]),
        snr_tile_count=int(kept.shape[0]),
        inlier_tile_count=int(best_inliers.size),
        residual_rms_px=float(np.sqrt(np.mean(inlier_residual**2))),
        residual_max_px=float(np.max(np.abs(inlier_residual))),
        median_snr=float(np.median(measured[:, 4])),
    )


def parse_strehl_tone(path: Path) -> dict[str, float]:
    with tifffile.TiffFile(path) as tiff:
        description = str(tiff.pages[0].tags["ImageDescription"].value)
    match = re.search(
        r"Tone rendering: black ([0-9]+(?:\.[0-9]+)?), "
        r"white ([0-9]+(?:\.[0-9]+)?).*?"
        r"display-space contrast ([0-9]+(?:\.[0-9]+)?)",
        description,
    )
    if match is None:
        raise RuntimeError(f"tone metadata not found in {path}")
    return {
        "black": float(match.group(1)),
        "white": float(match.group(2)),
        "contrast": float(match.group(3)),
        "toe": 0.004,
    }


def inverse_s_curve(values: np.ndarray, strength: float) -> np.ndarray:
    output = values.astype(np.float64)
    estimate = output.copy()
    for _ in range(8):
        smooth = estimate * estimate * (3.0 - 2.0 * estimate)
        function = estimate + strength * (smooth - estimate) - output
        derivative = 1.0 + strength * (6.0 * estimate - 6.0 * estimate**2 - 1.0)
        estimate -= function / np.maximum(derivative, 1e-6)
        estimate = np.clip(estimate, 0.0, 1.0)
    return estimate


def srgb_inverse(values: np.ndarray) -> np.ndarray:
    return np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )


def srgb_encode(values: np.ndarray) -> np.ndarray:
    return np.where(
        values <= 0.0031308,
        12.92 * values,
        1.055 * np.maximum(values, 0.0) ** (1.0 / 2.4) - 0.055,
    )


def s_curve(values: np.ndarray, strength: float) -> np.ndarray:
    smooth = values * values * (3.0 - 2.0 * values)
    return values + strength * (smooth - values)


def tone_gain(luminance: np.ndarray, tone: dict[str, float]) -> np.ndarray:
    luminance = np.maximum(luminance, 0.0)
    scale = 1.0 / (tone["white"] - tone["black"])
    y = (luminance - tone["black"]) * scale
    soft = 0.5 * (y + np.sqrt(y * y + tone["toe"] ** 2))
    gain = np.full_like(luminance, scale)
    positive = luminance > 1e-12
    gain[positive] = np.minimum(soft[positive] / luminance[positive], scale)
    gain[~positive] = 0.0
    return gain


def inverse_strehl_render(rgb: np.ndarray, tone: dict[str, float]) -> np.ndarray:
    display = inverse_s_curve(rgb, tone["contrast"])
    placed = srgb_inverse(display)
    placed_luminance = (
        0.2126 * placed[..., 0]
        + 0.7152 * placed[..., 1]
        + 0.0722 * placed[..., 2]
    )
    scale = 1.0 / (tone["white"] - tone["black"])
    upper = np.maximum(placed_luminance / max(scale, 1e-12), tone["white"] * 2)
    lower = np.zeros_like(placed_luminance)
    for _ in range(32):
        middle = 0.5 * (lower + upper)
        developed = middle * tone_gain(middle, tone)
        choose_upper = developed >= placed_luminance
        upper = np.where(choose_upper, middle, upper)
        lower = np.where(choose_upper, lower, middle)
    source_luminance = 0.5 * (lower + upper)
    gain = tone_gain(source_luminance, tone)
    return placed / np.maximum(gain[..., None], 1e-12)


def forward_neutral_strehl_render(
    rgb: np.ndarray, tone: dict[str, float]
) -> np.ndarray:
    luminance = (
        0.2126 * rgb[..., 0]
        + 0.7152 * rgb[..., 1]
        + 0.0722 * rgb[..., 2]
    )
    placed = rgb * tone_gain(luminance, tone)[..., None]
    if float(placed.min()) < 0.0 or float(placed.max()) > 1.0:
        raise RuntimeError("neutral inversion control unexpectedly left gamut")
    display = srgb_encode(placed)
    rendered = s_curve(display, tone["contrast"])
    return np.rint(np.clip(rendered, 0.0, 1.0) * 65535.0) / 65535.0


def raw_box(arm: Arm, y: int, x: int, size: int) -> np.ndarray:
    image = tifffile.memmap(arm.path, mode="r")
    box = np.asarray(image[y : y + size, x : x + size, :]).copy()
    del image
    return box


def linear_green_box(arm: Arm, y: int, x: int, size: int) -> np.ndarray:
    box = raw_box(arm, y, x, size)
    if arm.encoding == "linear-float":
        return box[:, :, 1].astype(np.float64)
    if arm.encoding == "linear-u16":
        return box[:, :, 1].astype(np.float64) / 65535.0
    if arm.encoding == "strehl-srgb-u16":
        rgb = box.astype(np.float64) / 65535.0
        return inverse_strehl_render(rgb, parse_strehl_tone(arm.path))[:, :, 1]
    raise ValueError(f"unsupported encoding {arm.encoding}")


def clipped(arm: Arm, y: int, x: int, size: int) -> bool:
    box = raw_box(arm, y, x, size)
    if np.issubdtype(box.dtype, np.integer):
        return bool(np.any(box >= np.iinfo(box.dtype).max))
    return bool(np.any(box >= 1.0))


def highpass_fractional_rms(green: np.ndarray) -> float:
    local_mean = uniform_filter(green, size=9)
    if float(local_mean.min()) <= 1e-9:
        raise RuntimeError("flat-ROI local mean reached zero")
    residual = green / local_mean - 1.0
    return float(np.std(residual))


def highpass_absolute_rms(green: np.ndarray) -> float:
    return float(np.std(green - uniform_filter(green, size=9)))


def in_bounds(arm: Arm, y: int, x: int, size: int) -> bool:
    shape = tifffile.memmap(arm.path, mode="r").shape
    return y >= 0 and x >= 0 and y + size <= shape[0] and x + size <= shape[1]


def percentile_summary(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "p25": float(np.percentile(array, 25)),
        "median": float(np.median(array)),
        "p75": float(np.percentile(array, 75)),
        "max": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


def bootstrap_median(values: list[float], seed: int) -> list[float]:
    array = np.asarray(values, dtype=np.float64)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, array.size, (20_000, array.size))
    medians = np.median(array[indices], axis=1)
    return [float(x) for x in np.percentile(medians, [2.5, 97.5])]


def coarse_box(image: np.ndarray, factor: int) -> np.ndarray:
    height = (image.shape[0] // factor) * factor
    width = (image.shape[1] // factor) * factor
    return image[:height, :width].reshape(
        height // factor, factor, width // factor, factor
    ).mean(axis=(1, 3))


def grade_elasticity(
    sites: list[dict[str, Any]],
    comparator_key: str,
) -> dict[str, Any]:
    comparator_samples: list[np.ndarray] = []
    strehl_samples: list[np.ndarray] = []
    for site in sites:
        comparator = np.asarray(site["_linear"][comparator_key])
        strehl = np.asarray(site["_linear"]["strehl"])
        comparator_coarse = coarse_box(comparator, max(1, round(24 * comparator.shape[0] / TILE)))
        strehl_coarse = coarse_box(strehl, max(1, round(24 * strehl.shape[0] / TILE)))
        height = min(comparator_coarse.shape[0], strehl_coarse.shape[0])
        width = min(comparator_coarse.shape[1], strehl_coarse.shape[1])
        comparator_samples.append(comparator_coarse[:height, :width].ravel())
        strehl_samples.append(strehl_coarse[:height, :width].ravel())
    comparator_values = np.concatenate(comparator_samples)
    strehl_values = np.concatenate(strehl_samples)
    quantiles = np.quantile(strehl_values, np.linspace(0.005, 0.995, 26))
    centers: list[float] = []
    values: list[float] = []
    counts: list[int] = []
    for lower, upper in zip(quantiles[:-1], quantiles[1:]):
        selected = (strehl_values >= lower) & (strehl_values < upper)
        if int(selected.sum()) < 50:
            continue
        centers.append(float(strehl_values[selected].mean()))
        values.append(float(comparator_values[selected].mean()))
        counts.append(int(selected.sum()))
    center = np.asarray(centers)
    value = np.asarray(values)
    slope = np.gradient(value, center)
    elasticity = slope / (value / center)
    finite_positive = elasticity[np.isfinite(elasticity) & (elasticity > 0)]
    if finite_positive.size < 5:
        raise RuntimeError(f"grade fit failed for {comparator_key}")
    return {
        "method": (
            "V-HEADTOHEAD grade.py method: matched 24-pixel scene-cell means, "
            "25 quantile bins of strehl linear level, numerical local slope; "
            "elasticity = d(comparator)/d(strehl) divided by comparator/strehl"
        ),
        "coarse_pairs": int(comparator_values.size),
        "bins": [
            {
                "strehl": float(c),
                "comparator": float(v),
                "count": int(n),
                "local_slope": float(s),
                "elasticity": float(e),
            }
            for c, v, n, s, e in zip(center, value, counts, slope, elasticity)
        ],
        "positive_finite_bins": int(finite_positive.size),
        "elasticity_median": float(np.median(finite_positive)),
        "elasticity_p95": float(np.percentile(finite_positive, 95)),
        "elasticity_max": float(np.max(finite_positive)),
    }


def measure_subject(
    subject: str,
    reference: Arm,
    strehl: Arm,
    comparator_arms: dict[str, Arm],
    geometries: dict[str, Geometry],
    seed: int,
    frozen_sites: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    reference_image = tifffile.memmap(reference.path, mode="r")
    reference_green = reference_image[:, :, 1]
    height, width = reference_green.shape

    reason_counts = {
        "candidate_grid": 0,
        "excluded_target_bounds": 0,
        "excluded_reference_clipping": 0,
        "excluded_reference_mean_gate": 0,
        "eligible_for_ranking": 0,
    }
    ranked: list[tuple[float, int, int, float]] = []
    for y in range(200, height - 200 - TILE, STEP):
        for x in range(200, width - 200 - TILE, STEP):
            reason_counts["candidate_grid"] += 1
            mapped_boxes: list[tuple[Arm, int, int, int]] = []
            bounds_ok = True
            for key, arm in {**comparator_arms, "strehl": strehl}.items():
                if arm == reference:
                    mapped_y, mapped_x, mapped_size = y, x, TILE
                else:
                    mapped_y, mapped_x, mapped_size = geometries[key].box(y, x, TILE)
                mapped_boxes.append((arm, mapped_y, mapped_x, mapped_size))
                if not in_bounds(arm, mapped_y, mapped_x, mapped_size):
                    bounds_ok = False
            if not bounds_ok:
                reason_counts["excluded_target_bounds"] += 1
                continue
            reference_box = np.asarray(
                reference_image[y : y + TILE, x : x + TILE, :]
            )
            if np.issubdtype(reference_box.dtype, np.integer):
                reference_is_clipped = np.any(
                    reference_box >= np.iinfo(reference_box.dtype).max
                )
                green = np.asarray(
                    reference_green[y : y + TILE, x : x + TILE],
                    dtype=np.float64,
                ) / np.iinfo(reference_box.dtype).max
            else:
                reference_is_clipped = np.any(reference_box >= 1.0)
                green = np.asarray(
                    reference_green[y : y + TILE, x : x + TILE],
                    dtype=np.float64,
                )
            if reference_is_clipped:
                reason_counts["excluded_reference_clipping"] += 1
                continue
            mean = float(green.mean())
            if not 0.05 < mean < 0.85:
                reason_counts["excluded_reference_mean_gate"] += 1
                continue
            reason_counts["eligible_for_ranking"] += 1
            ranked.append((highpass_absolute_rms(green), y, x, mean))
    del reference_image, reference_green

    ranked.sort(key=lambda row: row[0])
    eligible_by_coordinate = {
        (y, x): (selection_rms, mean)
        for selection_rms, y, x, mean in ranked
    }
    if frozen_sites is None:
        selected = ranked[:SITE_COUNT]
        selection_description = (
            "exact V-HEADTOHEAD survey.py policy: 384x384 reference-raster "
            "cells on a 192-pixel grid with 200-pixel margin; reject target "
            "bounds, any reference RGB clipping, and reference green means "
            "outside (0.05,0.85); rank by reference-only std(x-box9(x)); "
            "freeze the lowest 12 before reading strehl values"
        )
    else:
        selected = []
        for y, x in frozen_sites:
            if (y, x) not in eligible_by_coordinate:
                raise RuntimeError(
                    f"{subject}: frozen site {(y, x)} is no longer eligible"
                )
            selection_rms, mean = eligible_by_coordinate[(y, x)]
            selected.append((selection_rms, y, x, mean))
        selection_description = (
            "the 12 pre-existing 384x384 V-HEADTOHEAD spec.py FLAT_ROIS, "
            "originally selected by the comparator-only survey.py policy; "
            "eligibility was rechecked before any strehl value was read"
        )
    sites: list[dict[str, Any]] = []
    excluded_selected: list[dict[str, Any]] = []
    for rank, (selection_rms, y, x, reference_mean) in enumerate(selected, start=1):
        boxes: dict[str, tuple[int, int, int]] = {}
        linear: dict[str, np.ndarray] = {}
        exclusion_reasons: list[str] = []
        for key, arm in comparator_arms.items():
            if arm == reference:
                mapped_y, mapped_x, mapped_size = y, x, TILE
            else:
                mapped_y, mapped_x, mapped_size = geometries[key].box(y, x, TILE)
            boxes[key] = (mapped_y, mapped_x, mapped_size)
            if clipped(arm, mapped_y, mapped_x, mapped_size):
                exclusion_reasons.append(f"{key}: clipping")
            linear[key] = linear_green_box(arm, mapped_y, mapped_x, mapped_size)
        strehl_y, strehl_x, strehl_size = geometries["strehl"].box(y, x, TILE)
        boxes["strehl"] = (strehl_y, strehl_x, strehl_size)
        if clipped(strehl, strehl_y, strehl_x, strehl_size):
            exclusion_reasons.append("strehl: clipping")
        linear["strehl"] = linear_green_box(strehl, strehl_y, strehl_x, strehl_size)
        if exclusion_reasons:
            excluded_selected.append(
                {
                    "rank": rank,
                    "reference_y": y,
                    "reference_x": x,
                    "reasons": exclusion_reasons,
                }
            )
            continue

        rms = {key: highpass_fractional_rms(value) for key, value in linear.items()}
        ratios = {
            key: rms["strehl"] / rms[key]
            for key in comparator_arms
        }
        site = {
            "rank": rank,
            "reference_y": y,
            "reference_x": x,
            "reference_selection_absolute_rms": selection_rms,
            "reference_mean": reference_mean,
            "boxes_y_x_size": {key: list(value) for key, value in boxes.items()},
            "fractional_rms": rms,
            "strehl_over_comparator": ratios,
            "best_comparator_raw": max(ratios, key=ratios.get),
            "strehl_over_best_comparator_raw": max(ratios.values()),
            "_linear": linear,
        }
        sites.append(site)

    if not sites:
        raise RuntimeError(f"{subject}: no selected site was scoreable")

    grade = {
        key: grade_elasticity(sites, key)
        for key in comparator_arms
    }
    for site in sites:
        corrected_ratios: dict[str, float] = {}
        for key, raw_ratio in site["strehl_over_comparator"].items():
            conservative_elasticity = max(1.0, grade[key]["elasticity_max"])
            corrected_ratios[key] = raw_ratio * conservative_elasticity
        site["strehl_over_comparator_grade_corrected_max"] = corrected_ratios
        site["best_comparator_grade_corrected"] = max(
            corrected_ratios, key=corrected_ratios.get
        )
        site["strehl_over_best_comparator_grade_corrected_max"] = max(
            corrected_ratios.values()
        )

    raw_best = [site["strehl_over_best_comparator_raw"] for site in sites]
    corrected_best = [
        site["strehl_over_best_comparator_grade_corrected_max"] for site in sites
    ]
    for site in sites:
        del site["_linear"]

    result = {
        "subject": subject,
        "reference_raster": str(reference.path),
        "selection": {
            "method": selection_description,
            **reason_counts,
            "selected_for_scoring": len(selected),
            "scored": len(sites),
            "excluded_after_selection": len(excluded_selected),
            "selected_exclusions": excluded_selected,
        },
        "metric": (
            "population std(green / uniform_filter(green, 9) - 1), matching "
            "V-HEADTOHEAD hplook.py; every arm is decoded to linear light and "
            "each integer box covers the same scene area without resampling"
        ),
        "sign_convention": (
            "strehl/comparator; below 1 means strehl has lower measured "
            "flat-ROI high-pass RMS"
        ),
        "grade_correction": grade,
        "sites": sites,
        "raw_best_comparator_distribution": {
            **percentile_summary(raw_best),
            "bootstrap_95pct_interval_for_site_median": bootstrap_median(raw_best, seed),
            "sites_below_1": int(np.sum(np.asarray(raw_best) < 1.0)),
            "sites_scored": len(raw_best),
        },
        "grade_corrected_max_elasticity_distribution": {
            **percentile_summary(corrected_best),
            "bootstrap_95pct_interval_for_site_median": bootstrap_median(
                corrected_best, seed + 1
            ),
            "sites_below_1": int(np.sum(np.asarray(corrected_best) < 1.0)),
            "sites_scored": len(corrected_best),
        },
    }
    return result


def historical_coffee_site(geometry: Geometry) -> dict[str, Any]:
    y, x, size = 968, 584, 320
    target_y, target_x, target_size = geometry.box(y, x, size)
    comparator = linear_green_box(COFFEE_FORK, y, x, size)
    strehl = linear_green_box(COFFEE_STREHL, target_y, target_x, target_size)
    comparator_rms = highpass_fractional_rms(comparator)
    strehl_rms = highpass_fractional_rms(strehl)
    return {
        "site": {"reference_y": y, "reference_x": x, "reference_size": size},
        "strehl_box_y_x_size": [target_y, target_x, target_size],
        "comparator_fractional_rms": comparator_rms,
        "strehl_fractional_rms": strehl_rms,
        "strehl_over_comparator": strehl_rms / comparator_rms,
        "note": (
            "same frozen comparator site as hplook.py, but the old SHIP-V2 "
            "strehl render has been purged; this reads current DELIVER-V6"
        ),
    }


def commission(seed: int = 159) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    height = width = 384
    yy, xx = np.mgrid[0:height, 0:width]
    latent = (
        0.42
        + 0.035 * (xx / (width - 1) - 0.5)
        - 0.025 * (yy / (height - 1) - 0.5)
        + 0.002 * np.sin(2 * np.pi * xx / 160.0)
    )
    sigma = 0.004
    null_ratios: list[float] = []
    degraded_ratios: list[float] = []
    improved_ratios: list[float] = []
    for _ in range(128):
        baseline = latent + rng.normal(0.0, sigma, latent.shape)
        null = latent + rng.normal(0.0, sigma, latent.shape)
        degraded = null + rng.normal(0.0, 1.5 * sigma, latent.shape)
        captures = [
            latent + rng.normal(0.0, sigma, latent.shape)
            for _ in range(4)
        ]
        improved = np.mean(captures, axis=0)
        baseline_rms = highpass_fractional_rms(baseline)
        null_ratios.append(highpass_fractional_rms(null) / baseline_rms)
        degraded_ratios.append(highpass_fractional_rms(degraded) / baseline_rms)
        improved_ratios.append(highpass_fractional_rms(improved) / baseline_rms)

    texture = latent + 0.025 * np.sin(2 * np.pi * xx / 6.0)
    texture_noisy = texture + rng.normal(0.0, sigma, latent.shape)
    texture_blurred = gaussian_filter(texture_noisy, 1.0)
    blur_ratio = highpass_fractional_rms(texture_blurred) / highpass_fractional_rms(
        texture_noisy
    )
    tone = parse_strehl_tone(COFFEE_STREHL.path)
    neutral_green = latent + rng.normal(0.0, sigma, latent.shape)
    neutral_rgb = np.repeat(neutral_green[:, :, None], 3, axis=2)
    rendered = forward_neutral_strehl_render(neutral_rgb, tone)
    recovered = inverse_strehl_render(rendered, tone)
    inversion_hp_ratio = highpass_fractional_rms(
        recovered[:, :, 1]
    ) / highpass_fractional_rms(neutral_green)
    inversion_max_abs_error = float(np.max(np.abs(recovered - neutral_rgb)))
    return {
        "seed": seed,
        "trials": 128,
        "synthetic_field": (
            "same smooth latent flat field in every arm; independent Gaussian "
            "capture noise sigma=0.004"
        ),
        "movable_null": {
            "construction": (
                "two independent captures with equal noise, not identical bytes "
                "and not a subtraction from itself"
            ),
            **percentile_summary(null_ratios),
            "trials_below_1": int(np.sum(np.asarray(null_ratios) < 1.0)),
            "trials_above_1": int(np.sum(np.asarray(null_ratios) > 1.0)),
        },
        "planted_degradation": {
            "construction": "add independent noise with sigma=1.5 times capture sigma",
            **percentile_summary(degraded_ratios),
            "trials_above_1": int(np.sum(np.asarray(degraded_ratios) > 1.0)),
        },
        "planted_improvement": {
            "construction": (
                "average four independent noisy captures of the same latent "
                "field; expected noise amplitude ratio about 1/sqrt(4)=0.5"
            ),
            **percentile_summary(improved_ratios),
            "trials_below_1": int(np.sum(np.asarray(improved_ratios) < 1.0)),
        },
        "specificity_challenge": {
            "construction": (
                "Gaussian-blur a noisy field carrying a real 6-pixel-period "
                "texture; this destroys structure as well as noise"
            ),
            "blurred_over_unblurred": blur_ratio,
            "interpretation": (
                "the instrument rewards blur, so it licenses noise only on "
                "predeclared flat/defocused ground and cannot license detail"
            ),
        },
        "tone_inversion_round_trip": {
            "construction": (
                "neutral noisy linear field -> the current shipping tone "
                "placement, sRGB transfer, display S-curve and 16-bit "
                "quantisation -> the measurement inverse"
            ),
            "recovered_over_source_highpass_rms": inversion_hp_ratio,
            "max_abs_linear_error": inversion_max_abs_error,
        },
    }


def main() -> None:
    arms = [
        COFFEE_FORK,
        SUBJECT2_FORK,
        SUBJECT2_ZERENE,
        COFFEE_STREHL,
        SUBJECT2_STREHL,
    ]
    missing = [str(arm.path) for arm in arms if not arm.path.exists()]
    if missing:
        raise FileNotFoundError(f"missing inputs: {missing}")

    commissioning = commission()
    coffee_to_strehl = fit_geometry(COFFEE_FORK, COFFEE_STREHL)
    subject2_to_strehl = fit_geometry(SUBJECT2_ZERENE, SUBJECT2_STREHL)

    coffee = measure_subject(
        "coffee-bean",
        COFFEE_FORK,
        COFFEE_STREHL,
        {"fork": COFFEE_FORK},
        {"strehl": coffee_to_strehl},
        seed=1591,
        frozen_sites=[
            (968, 584),
            (1160, 584),
            (968, 392),
            (1160, 392),
            (1736, 392),
            (1736, 584),
            (968, 776),
            (1160, 776),
            (1928, 584),
            (1928, 392),
            (1352, 584),
            (776, 584),
        ],
    )
    subject2 = measure_subject(
        "113MSDCF",
        SUBJECT2_ZERENE,
        SUBJECT2_STREHL,
        {"zerene_pmax": SUBJECT2_ZERENE},
        {
            "strehl": subject2_to_strehl,
        },
        seed=1592,
    )

    results = {
        "schema": 1,
        "instrument": {
            "source": "experiments/V-HEADTOHEAD/hplook.py",
            "selection_source": "experiments/V-HEADTOHEAD/survey.py",
            "grade_source": "experiments/V-HEADTOHEAD/grade.py",
            "box_filter": "9x9 uniform_filter",
            "statistic": "population std(green / box9(green) - 1)",
        },
        "commissioning": commissioning,
        "inputs": [image_info(arm) for arm in arms],
        "geometry": {
            "coffee_fork_to_strehl": coffee_to_strehl.as_dict(),
            "subject2_zerene_to_strehl": subject2_to_strehl.as_dict(),
        },
        "unscored_existing_comparators": [
            {
                "subject": "113MSDCF",
                "comparator": str(SUBJECT2_FORK.path),
                "reason": (
                    "not used for the distribution: the existing V-HEADTOHEAD2 "
                    "registration audit found 5.3 px RMS local disagreement and "
                    "41/64 candidate regions failed its commissioned gate"
                ),
            }
        ],
        "subjects": [coffee, subject2],
        "historical_coffee_site_current_render": historical_coffee_site(
            coffee_to_strehl
        ),
    }
    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {RESULTS_PATH}")
    for subject in results["subjects"]:
        raw = subject["raw_best_comparator_distribution"]
        corrected = subject["grade_corrected_max_elasticity_distribution"]
        print(
            f"{subject['subject']}: raw median={raw['median']:.6f}, "
            f"max={raw['max']:.6f}, {raw['sites_below_1']}/{raw['sites_scored']} < 1; "
            f"grade-max median={corrected['median']:.6f}, "
            f"max={corrected['max']:.6f}, "
            f"{corrected['sites_below_1']}/{corrected['sites_scored']} < 1"
        )


if __name__ == "__main__":
    main()
