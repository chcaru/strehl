"""Commission the M145 input-defined focus-boundary seam instrument.

The source photograph is read from the project's read-only macro corpus.  Its
real luminance texture drives a deterministic synthetic tilted-focus sweep;
only the known defocus field and the colour-seam plants are synthetic.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rawpy
import scipy
import skimage
from scipy import ndimage
from skimage.color import deltaE_ciede2000


SOURCE = Path(r"D:\personal\macro\couch-fibers-cpl\DSC00150.ARW")
OUT = Path(__file__).with_name("results.json")

CROP_SIZE = 1024
FRAME_COUNT = 25
TILE = 32
SITE_SPACING = 12.0
MASK_MARGIN = 64.0
FOCUS_SIGMA = 0.62
DEFOCUS_SIGMA_PX = 3.0
MIN_PEAK_RATIO = 1.15
MIN_FOCUS_TILES = 256
MIN_FOCUS_TILES_PER_QUADRANT = 32
MAX_FOCUS_RESIDUAL = 0.25
MIN_SITES = 1_000
MIN_BOUNDARIES = 10
MIN_SITES_PER_BOUNDARY = 50

# Linear ProPhoto RGB (D50) to XYZ (D50), as used by the commissioning input.
PROPHOTO_TO_XYZ_D50 = np.array(
    [
        [0.7976749, 0.1351917, 0.0313534],
        [0.2880402, 0.7118741, 0.0000857],
        [0.0, 0.0, 0.8252100],
    ],
    dtype=np.float64,
)
D50 = np.array([0.96422, 1.0, 0.82521], dtype=np.float64)


@dataclass(frozen=True)
class Plane:
    ax: float
    ay: float
    c: float

    def at(self, x: np.ndarray | float, y: np.ndarray | float) -> np.ndarray | float:
        return self.ax * x + self.ay * y + self.c

    @property
    def gradient(self) -> np.ndarray:
        return np.array([self.ax, self.ay], dtype=np.float64)


@dataclass(frozen=True)
class Site:
    boundary: int
    x: float
    y: float
    nx: float
    ny: float
    tx: float
    ty: float
    search_half_width: int


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_real_crop(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        rgb16 = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            gamma=(1.0, 1.0),
            output_bps=16,
            output_color=rawpy.ColorSpace.ProPhoto,
            user_flip=0,
        )

    h, w, _ = rgb16.shape
    if h < CROP_SIZE or w < CROP_SIZE:
        raise RuntimeError(f"{path} is only {w}x{h}, smaller than the requested crop")

    # Fixed fractional centre: deterministic and independent of every plant.
    cx = int(round(0.54 * (w - 1)))
    cy = int(round(0.48 * (h - 1)))
    x0 = min(max(cx - CROP_SIZE // 2, 0), w - CROP_SIZE)
    y0 = min(max(cy - CROP_SIZE // 2, 0), h - CROP_SIZE)
    crop = rgb16[y0 : y0 + CROP_SIZE, x0 : x0 + CROP_SIZE].astype(np.float64)
    crop /= 65535.0

    return crop, {
        "decoded_width": int(w),
        "decoded_height": int(h),
        "crop_x": int(x0),
        "crop_y": int(y0),
        "crop_width": CROP_SIZE,
        "crop_height": CROP_SIZE,
    }


def linear_prophoto_to_lab(rgb: np.ndarray) -> np.ndarray:
    xyz = np.einsum("...c,dc->...d", rgb, PROPHOTO_TO_XYZ_D50)
    ratio = xyz / D50
    delta = 6.0 / 29.0
    f = np.where(
        ratio > delta**3,
        np.cbrt(ratio),
        ratio / (3.0 * delta**2) + 4.0 / 29.0,
    )
    lab = np.empty_like(f)
    lab[..., 0] = 116.0 * f[..., 1] - 16.0
    lab[..., 1] = 500.0 * (f[..., 0] - f[..., 1])
    lab[..., 2] = 200.0 * (f[..., 1] - f[..., 2])
    return lab


def make_true_focus_plane(width: int, height: int) -> Plane:
    # The best-focus coordinate spans 1.25 .. FRAME_COUNT-2.25 across the crop
    # and has a smaller orthogonal slope, like a mildly rotated tilted target.
    ax = (FRAME_COUNT - 3.5) / (width - 1)
    ay = 0.40 / (height - 1)
    c = 1.25
    return Plane(ax=ax, ay=ay, c=c)


def focus_scores_from_real_texture(
    luma: np.ndarray, true_plane: Plane
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    height, width = luma.shape
    yy, xx = np.mgrid[0:height, 0:width]
    k_true = true_plane.at(xx, yy)
    blurred = ndimage.gaussian_filter(luma, DEFOCUS_SIGMA_PX, mode="reflect")

    centres_x = np.arange(TILE // 2, width, TILE, dtype=np.int32)
    centres_y = np.arange(TILE // 2, height, TILE, dtype=np.int32)
    tile_x, tile_y = np.meshgrid(centres_x, centres_y)
    points = np.column_stack([tile_x.ravel(), tile_y.ravel()])
    scores = np.empty((FRAME_COUNT, len(points)), dtype=np.float64)

    for frame in range(FRAME_COUNT):
        sharp_weight = np.exp(-0.5 * ((k_true - frame) / FOCUS_SIGMA) ** 2)
        image = sharp_weight * luma + (1.0 - sharp_weight) * blurred
        gx = ndimage.sobel(image, axis=1, mode="reflect") / 8.0
        gy = ndimage.sobel(image, axis=0, mode="reflect") / 8.0
        energy = gx * gx + gy * gy

        for i, (x, y) in enumerate(points):
            tile = image[
                y - TILE // 2 : y + TILE // 2,
                x - TILE // 2 : x + TILE // 2,
            ]
            e = energy[
                y - TILE // 2 : y + TILE // 2,
                x - TILE // 2 : x + TILE // 2,
            ]
            scale = float(np.median(tile))
            scores[frame, i] = float(np.mean(e)) / max(scale * scale, 1e-12)

    return scores, points[:, 0].astype(np.float64), points[:, 1].astype(np.float64)


def fit_focus_plane(
    scores: np.ndarray, xs: np.ndarray, ys: np.ndarray
) -> tuple[Plane | None, dict[str, float | int | str], np.ndarray]:
    if scores.shape[0] < 3:
        return None, {"status": "UNMEASURED_TOO_FEW_FRAMES", "valid_tiles": 0}, np.zeros(
            scores.shape[1], dtype=bool
        )

    peaks = np.argmax(scores, axis=0)
    coords = np.full(scores.shape[1], np.nan, dtype=np.float64)
    ratios = np.max(scores, axis=0) / np.maximum(np.median(scores, axis=0), 1e-15)
    ordered = np.sort(scores, axis=0)
    unique_peak = ordered[-1] > ordered[-2]

    valid = (
        (peaks > 0)
        & (peaks < scores.shape[0] - 1)
        & (ratios >= MIN_PEAK_RATIO)
        & unique_peak
    )
    for i in np.flatnonzero(valid):
        j = int(peaks[i])
        left, centre, right = scores[j - 1, i], scores[j, i], scores[j + 1, i]
        denom = left - 2.0 * centre + right
        if not np.isfinite(denom) or denom >= -1e-15:
            valid[i] = False
            continue
        offset = 0.5 * (left - right) / denom
        if not np.isfinite(offset) or abs(offset) > 1.0:
            valid[i] = False
            continue
        coords[i] = j + offset

    if int(np.count_nonzero(valid)) < MIN_FOCUS_TILES:
        return (
            None,
            {
                "status": "UNMEASURED_FOCUS_FIT",
                "valid_tiles": int(np.count_nonzero(valid)),
            },
            valid,
        )

    design = np.column_stack([xs[valid], ys[valid], np.ones(np.count_nonzero(valid))])
    beta, *_ = np.linalg.lstsq(design, coords[valid], rcond=None)
    residual = coords[valid] - design @ beta
    centre = float(np.median(residual))
    mad = float(np.median(np.abs(residual - centre)))
    scale = 1.4826 * mad
    if scale <= 1e-12:
        keep_local = np.abs(residual - centre) <= 1e-9
    else:
        keep_local = np.abs(residual - centre) <= 3.0 * scale

    valid_indices = np.flatnonzero(valid)
    kept_indices = valid_indices[keep_local]
    final_valid = np.zeros_like(valid)
    final_valid[kept_indices] = True
    if len(kept_indices) < MIN_FOCUS_TILES:
        return (
            None,
            {
                "status": "UNMEASURED_FOCUS_FIT",
                "valid_tiles": int(len(kept_indices)),
            },
            final_valid,
        )

    final_design = np.column_stack(
        [xs[final_valid], ys[final_valid], np.ones(np.count_nonzero(final_valid))]
    )
    beta, *_ = np.linalg.lstsq(final_design, coords[final_valid], rcond=None)
    final_residual = coords[final_valid] - final_design @ beta
    residual_p95 = float(np.quantile(np.abs(final_residual), 0.95))
    residual_max = float(np.max(np.abs(final_residual)))
    x_mid = float(np.median(xs))
    y_mid = float(np.median(ys))
    quadrant_counts = [
        int(
            np.count_nonzero(
                final_valid
                & ((xs >= x_mid) if right else (xs < x_mid))
                & ((ys >= y_mid) if bottom else (ys < y_mid))
            )
        )
        for bottom in (False, True)
        for right in (False, True)
    ]
    if (
        residual_max > MAX_FOCUS_RESIDUAL
        or min(quadrant_counts) < MIN_FOCUS_TILES_PER_QUADRANT
    ):
        return (
            None,
            {
                "status": "UNMEASURED_FOCUS_FIT",
                "valid_tiles": int(np.count_nonzero(final_valid)),
                "residual_p95_abs_frames": residual_p95,
                "residual_max_abs_frames": residual_max,
                "quadrant_counts": quadrant_counts,
            },
            final_valid,
        )
    plane = Plane(ax=float(beta[0]), ay=float(beta[1]), c=float(beta[2]))
    return (
        plane,
        {
            "status": "OK",
            "valid_tiles": int(np.count_nonzero(final_valid)),
            "rejected_tiles": int(np.count_nonzero(valid) - np.count_nonzero(final_valid)),
            "residual_rmse_frames": float(np.sqrt(np.mean(final_residual**2))),
            "residual_p95_abs_frames": residual_p95,
            "residual_max_abs_frames": residual_max,
            "quadrant_counts": quadrant_counts,
        },
        final_valid,
    )


def clip_line_to_rect(
    plane: Plane, value: float, xmin: float, xmax: float, ymin: float, ymax: float
) -> tuple[np.ndarray, np.ndarray] | None:
    points: list[np.ndarray] = []
    eps = 1e-12
    if abs(plane.ay) > eps:
        for x in (xmin, xmax):
            y = (value - plane.ax * x - plane.c) / plane.ay
            if ymin - 1e-9 <= y <= ymax + 1e-9:
                points.append(np.array([x, y], dtype=np.float64))
    if abs(plane.ax) > eps:
        for y in (ymin, ymax):
            x = (value - plane.ay * y - plane.c) / plane.ax
            if xmin - 1e-9 <= x <= xmax + 1e-9:
                points.append(np.array([x, y], dtype=np.float64))

    unique: list[np.ndarray] = []
    for p in points:
        if not any(float(np.linalg.norm(p - q)) < 1e-7 for q in unique):
            unique.append(p)
    if len(unique) < 2:
        return None

    best = max(
        ((p, q) for i, p in enumerate(unique) for q in unique[i + 1 :]),
        key=lambda pair: float(np.linalg.norm(pair[1] - pair[0])),
    )
    p0, p1 = best
    if (p1[1], p1[0]) < (p0[1], p0[0]):
        p0, p1 = p1, p0
    return p0, p1


def make_sites(plane: Plane, width: int, height: int) -> tuple[list[Site], dict[str, float | int]]:
    grad = plane.gradient
    grad_norm = float(np.linalg.norm(grad))
    if grad_norm <= 0.0:
        return [], {"boundary_components": 0, "focus_pitch_px": math.inf}
    normal = grad / grad_norm
    tangent = np.array([-normal[1], normal[0]])
    pitch = 1.0 / grad_norm
    search_half = max(1, int(math.floor(0.25 * pitch)))

    # Reserve every possible profile footprint before creating the population.
    footprint = search_half + 5.0
    xmin = MASK_MARGIN + footprint
    xmax = width - 1.0 - MASK_MARGIN - footprint
    ymin = MASK_MARGIN + footprint
    ymax = height - 1.0 - MASK_MARGIN - footprint

    corners = [
        plane.at(xmin, ymin),
        plane.at(xmin, ymax),
        plane.at(xmax, ymin),
        plane.at(xmax, ymax),
    ]
    first = int(math.ceil(min(corners) - 0.5))
    last = int(math.floor(max(corners) - 0.5))

    sites: list[Site] = []
    component_counts: dict[int, int] = {}
    for boundary in range(first, last + 1):
        value = boundary + 0.5
        segment = clip_line_to_rect(plane, value, xmin, xmax, ymin, ymax)
        if segment is None:
            continue
        p0, p1 = segment
        length = float(np.linalg.norm(p1 - p0))
        if length < SITE_SPACING:
            continue
        direction = (p1 - p0) / length
        before = len(sites)
        for s in np.arange(SITE_SPACING / 2.0, length, SITE_SPACING):
            p = p0 + s * direction
            sites.append(
                Site(
                    boundary=boundary,
                    x=float(p[0]),
                    y=float(p[1]),
                    nx=float(normal[0]),
                    ny=float(normal[1]),
                    tx=float(tangent[0]),
                    ty=float(tangent[1]),
                    search_half_width=search_half,
                )
            )
        component_counts[boundary] = len(sites) - before

    return sites, {
        "boundary_components": int(len(component_counts)),
        "minimum_sites_per_boundary": int(min(component_counts.values(), default=0)),
        "maximum_sites_per_boundary": int(max(component_counts.values(), default=0)),
        "focus_pitch_px": float(pitch),
        "search_half_width_px": int(search_half),
    }


def sample_window(
    lab: np.ndarray, site: Site, centre_offset: float
) -> np.ndarray:
    tangent_offsets = np.arange(-4.0, 5.0)
    normal_offsets = np.arange(-1.0, 2.0)
    tt, nn = np.meshgrid(tangent_offsets, normal_offsets)
    x = (
        site.x
        + centre_offset * site.nx
        + tt.ravel() * site.tx
        + nn.ravel() * site.nx
    )
    y = (
        site.y
        + centre_offset * site.ny
        + tt.ravel() * site.ty
        + nn.ravel() * site.ny
    )
    values = np.column_stack(
        [
            ndimage.map_coordinates(lab[..., channel], [y, x], order=1, mode="nearest")
            for channel in range(3)
        ]
    )
    return np.median(values, axis=0)


def score_sites(output_lab: np.ndarray, truth_lab: np.ndarray, sites: list[Site]) -> np.ndarray:
    values = np.empty(len(sites), dtype=np.float64)
    for i, site in enumerate(sites):
        best = 0.0
        for offset in range(-site.search_half_width, site.search_half_width + 1):
            out_left = sample_window(output_lab, site, offset - 3.0)
            out_right = sample_window(output_lab, site, offset + 3.0)
            truth_left = sample_window(truth_lab, site, offset - 3.0)
            truth_right = sample_window(truth_lab, site, offset + 3.0)
            anchor = 0.5 * (truth_left + truth_right)
            corrected_left = anchor + (out_left - truth_left)
            corrected_right = anchor + (out_right - truth_right)
            differential_error = float(
                deltaE_ciede2000(corrected_left[None, :], corrected_right[None, :])[0]
            )
            best = max(best, differential_error)
        values[i] = best
    return values


def nearest_rank(values: np.ndarray, q: float) -> float:
    if len(values) == 0:
        raise ValueError("nearest-rank quantile is undefined for an empty population")
    ordered = np.sort(values)
    rank = int(math.ceil(q * len(ordered)))
    return float(ordered[rank - 1])


def longest_excursion_run(values: np.ndarray, sites: list[Site], threshold: float) -> int:
    longest = 0
    current = 0
    previous_boundary: int | None = None
    for value, site in zip(values, sites, strict=True):
        if site.boundary != previous_boundary:
            current = 0
            previous_boundary = site.boundary
        if value > threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def summarize_arm(
    name: str, output_lab: np.ndarray, truth_lab: np.ndarray, sites: list[Site]
) -> dict[str, float | int | str]:
    if len(sites) < MIN_SITES:
        return {
            "name": name,
            "eligible_sites": len(sites),
            "p99_nearest_rank_delta_e00": None,
            "verdict": "UNMEASURED_CAPTURE_INADEQUATE",
        }
    scores = score_sites(output_lab, truth_lab, sites)
    p99 = nearest_rank(scores, 0.99)
    longest_run = longest_excursion_run(scores, sites, 1.0)
    return {
        "name": name,
        "eligible_sites": int(len(scores)),
        "p50_delta_e00": nearest_rank(scores, 0.50),
        "p95_delta_e00": nearest_rank(scores, 0.95),
        "p99_nearest_rank_delta_e00": p99,
        "maximum_delta_e00": float(np.max(scores)),
        "sites_over_1_delta_e00": int(np.count_nonzero(scores > 1.0)),
        "longest_consecutive_run_over_1": longest_run,
        "verdict": "PASS" if p99 <= 1.0 and longest_run < 3 else "FAIL",
    }


def planted_output(truth_lab: np.ndarray, plane: Plane, step_delta_a: float) -> np.ndarray:
    height, width, _ = truth_lab.shape
    yy, xx = np.mgrid[0:height, 0:width]
    region = np.floor(plane.at(xx, yy) + 0.5).astype(np.int32)
    sign = np.where(region % 2 == 0, -0.5, 0.5)
    output = truth_lab.copy()
    output[..., 1] += step_delta_a * sign
    return output


def sparse_planted_output(
    truth_lab: np.ndarray, sites: list[Site], step_delta_a: float
) -> tuple[np.ndarray, dict[str, int]]:
    boundaries = sorted({site.boundary for site in sites})
    boundary = boundaries[len(boundaries) // 2]
    component = [site for site in sites if site.boundary == boundary]
    start = len(component) // 2 - 1
    selected = component[start : start + 3]
    centre = np.array(
        [
            0.5 * (selected[0].x + selected[-1].x),
            0.5 * (selected[0].y + selected[-1].y),
        ]
    )
    normal = np.array([selected[0].nx, selected[0].ny])
    tangent = np.array([selected[0].tx, selected[0].ty])
    half_tangent = 0.5 * float(
        np.linalg.norm(
            np.array([selected[-1].x, selected[-1].y])
            - np.array([selected[0].x, selected[0].y])
        )
    ) + 4.0
    half_normal = selected[0].search_half_width + 5.0

    height, width, _ = truth_lab.shape
    yy, xx = np.mgrid[0:height, 0:width]
    dx = xx - centre[0]
    dy = yy - centre[1]
    normal_coordinate = dx * normal[0] + dy * normal[1]
    tangent_coordinate = dx * tangent[0] + dy * tangent[1]
    mask = (
        (np.abs(normal_coordinate) <= half_normal)
        & (np.abs(tangent_coordinate) <= half_tangent)
    )
    output = truth_lab.copy()
    output[..., 1][mask] += np.where(
        normal_coordinate[mask] < 0.0, -0.5 * step_delta_a, 0.5 * step_delta_a
    )
    return output, {
        "boundary": int(boundary),
        "intended_consecutive_sites": len(selected),
    }


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)

    source_hash = sha256(SOURCE)
    rgb, crop = load_real_crop(SOURCE)
    truth_lab = linear_prophoto_to_lab(rgb)
    patch_value = np.median(
        truth_lab[
            int(MASK_MARGIN) : CROP_SIZE - int(MASK_MARGIN),
            int(MASK_MARGIN) : CROP_SIZE - int(MASK_MARGIN),
        ],
        axis=(0, 1),
    )
    luma = np.einsum("...c,c->...", rgb, PROPHOTO_TO_XYZ_D50[1])

    true_plane = make_true_focus_plane(CROP_SIZE, CROP_SIZE)
    scores, tile_x, tile_y = focus_scores_from_real_texture(luma, true_plane)
    fitted, fit, valid_tiles = fit_focus_plane(scores, tile_x, tile_y)
    if fitted is None:
        raise RuntimeError(f"positive focus plant failed: {fit}")

    sites, population = make_sites(fitted, CROP_SIZE, CROP_SIZE)
    tile_truth = true_plane.at(tile_x[valid_tiles], tile_y[valid_tiles])
    tile_fit = fitted.at(tile_x[valid_tiles], tile_y[valid_tiles])
    focus_error = np.abs(tile_fit - tile_truth)
    position_error = focus_error / float(np.linalg.norm(true_plane.gradient))

    sparse_output, sparse_plant = sparse_planted_output(
        truth_lab, sites, step_delta_a=3.00
    )
    arms = [
        summarize_arm(
            "baseline",
            planted_output(truth_lab, true_plane, step_delta_a=0.50),
            truth_lab,
            sites,
        ),
        summarize_arm(
            "planted_defect",
            planted_output(truth_lab, true_plane, step_delta_a=3.00),
            truth_lab,
            sites,
        ),
        summarize_arm(
            "planted_improvement",
            planted_output(truth_lab, true_plane, step_delta_a=0.15),
            truth_lab,
            sites,
        ),
        summarize_arm(
            "sparse_planted_defect",
            sparse_output,
            truth_lab,
            sites,
        ),
    ]

    identical_scores = np.repeat(scores[:1, :], FRAME_COUNT, axis=0)
    null_plane, null_fit, _ = fit_focus_plane(identical_scores, tile_x, tile_y)
    null_sites: list[Site] = []
    if null_plane is not None:
        null_sites, _ = make_sites(null_plane, CROP_SIZE, CROP_SIZE)
    null = {
        "name": "identical_frames_null",
        "focus_fit_status": null_fit["status"],
        "eligible_sites": len(null_sites),
        "p99_nearest_rank_delta_e00": None,
        "verdict": "UNMEASURED_CAPTURE_INADEQUATE",
    }

    result = {
        "experiment": "M145 seam-population commissioning",
        "source": {
            "path": str(SOURCE),
            "sha256": source_hash,
            **crop,
        },
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_image": skimage.__version__,
            "rawpy": rawpy.__version__,
        },
        "parameters": {
            "frame_count": FRAME_COUNT,
            "tile_px": TILE,
            "site_spacing_px": SITE_SPACING,
            "minimum_sites": MIN_SITES,
            "minimum_boundaries": MIN_BOUNDARIES,
            "minimum_sites_per_boundary": MIN_SITES_PER_BOUNDARY,
            "focus_sigma_frames": FOCUS_SIGMA,
            "defocus_sigma_px": DEFOCUS_SIGMA_PX,
            "minimum_peak_to_median_ratio": MIN_PEAK_RATIO,
            "minimum_focus_tiles": MIN_FOCUS_TILES,
            "minimum_focus_tiles_per_quadrant": MIN_FOCUS_TILES_PER_QUADRANT,
            "maximum_focus_fit_absolute_residual_frames": MAX_FOCUS_RESIDUAL,
            "scoring_target": (
                "the decoded real crop as a frozen local Lab reference map; "
                "score compares differential Lab errors at a shared local anchor"
            ),
            "scoring_target_lab_d50": [float(v) for v in patch_value],
            "baseline_step_delta_a": 0.50,
            "planted_defect_step_delta_a": 3.00,
            "planted_improvement_step_delta_a": 0.15,
            "sparse_planted_defect": sparse_plant,
            "profile_window": "two 3x9 median-Lab windows centred +/-3 px",
            "profile_search": "+/- floor(one_focus_step_pitch/4)",
            "quantile": "nearest-rank, rank ceil(q*n), one-based",
        },
        "focus_fit": {
            **fit,
            "true_ax_frames_per_px": true_plane.ax,
            "true_ay_frames_per_px": true_plane.ay,
            "true_c_frames": true_plane.c,
            "fitted_ax_frames_per_px": fitted.ax,
            "fitted_ay_frames_per_px": fitted.ay,
            "fitted_c_frames": fitted.c,
            "fit_vs_truth_p50_abs_frames": float(np.quantile(focus_error, 0.50)),
            "fit_vs_truth_p95_abs_frames": float(np.quantile(focus_error, 0.95)),
            "fit_vs_truth_max_abs_frames": float(np.max(focus_error)),
            "boundary_position_p95_abs_px": float(np.quantile(position_error, 0.95)),
            "boundary_position_max_abs_px": float(np.max(position_error)),
        },
        "population": {
            **population,
            "eligible_sites": len(sites),
            "minimum_met": (
                len(sites) >= MIN_SITES
                and population["boundary_components"] >= MIN_BOUNDARIES
                and population["minimum_sites_per_boundary"] >= MIN_SITES_PER_BOUNDARY
            ),
        },
        "arms": arms,
        "null": null,
    }

    arm_by_name = {arm["name"]: arm for arm in arms}
    checks = {
        "population_minimum_met": bool(result["population"]["minimum_met"]),
        "defect_raises_p99": (
            arm_by_name["planted_defect"]["p99_nearest_rank_delta_e00"]
            > arm_by_name["baseline"]["p99_nearest_rank_delta_e00"]
        ),
        "improvement_does_not_raise_p99": (
            arm_by_name["planted_improvement"]["p99_nearest_rank_delta_e00"]
            <= arm_by_name["baseline"]["p99_nearest_rank_delta_e00"]
        ),
        "sparse_defect_exposes_p99_dilution": (
            arm_by_name["sparse_planted_defect"]["p99_nearest_rank_delta_e00"] <= 1.0
            and arm_by_name["sparse_planted_defect"]["longest_consecutive_run_over_1"]
            >= 3
            and arm_by_name["sparse_planted_defect"]["verdict"] == "FAIL"
        ),
        "null_is_unmeasured_with_zero_sites": (
            null["eligible_sites"] == 0
            and null["p99_nearest_rank_delta_e00"] is None
            and null["verdict"] == "UNMEASURED_CAPTURE_INADEQUATE"
        ),
    }
    result["commissioning_checks"] = checks
    if not all(checks.values()):
        raise RuntimeError(f"commissioning check failed: {checks}")

    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"commissioning failed: {exc}", file=sys.stderr)
        raise
