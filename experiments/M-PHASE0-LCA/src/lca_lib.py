"""Shared instrument code for M-PHASE0-LCA.

The verdict-bearing path remains on native CFA planes.  This module contains
the small pieces that commissioning can mutate independently: CFA splitting,
phase-correlation sign, the baseline-subtracted log-domain peak fit, batched
Sobel energy, and cluster-bootstrap summaries.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


HERE = Path(__file__).resolve().parent
LANE = HERE.parent
OUT = LANE / "out"
FIXTURES = LANE / "fixtures"
REPO = LANE.parents[1]

CHANNELS = ("R", "G1", "G2", "B")
SITE = {
    "R": (0, 0),
    "G1": (0, 1),
    "G2": (1, 0),
    "B": (1, 1),
}
COLOR_INDEX = {"R": 0, "G1": 1, "G2": 3, "B": 2}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def array_sha256(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def numerical_dependency_record() -> dict:
    import rawpy
    import scipy
    import scipy.ndimage._nd_image as scipy_ndimage_binary

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "rawpy": rawpy.__version__,
        "binary_sha256": {
            "numpy_multiarray": file_sha256(
                Path(np._core._multiarray_umath.__file__)
            ),
            "rawpy": file_sha256(Path(rawpy._rawpy.__file__)),
            "scipy_ndimage": file_sha256(
                Path(scipy_ndimage_binary.__file__)
            ),
        },
    }


def environment_record() -> dict:
    return {
        **numerical_dependency_record(),
        "cwd": str(Path.cwd()),
        "repo_head": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip(),
        "environment": {
            name: os.environ.get(name)
            for name in (
                "PYTHONIOENCODING",
                "PYTHONPATH",
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
            )
        },
    }


def capture_inventory(root: Path) -> dict:
    files = sorted(root.glob("*.ARW"), key=lambda path: path.name.lower())
    return {
        "root": str(root),
        "count": len(files),
        "bytes": int(sum(path.stat().st_size for path in files)),
        "names": [path.name for path in files],
        "mtimes_ns": [path.stat().st_mtime_ns for path in files],
    }


def decode_visible(path: Path) -> tuple[np.ndarray, dict]:
    """Copy LibRaw's visible mosaic before its owning context closes."""
    import rawpy

    with rawpy.imread(str(path)) as raw:
        visible = np.array(raw.raw_image_visible, copy=True)
        pattern = None if raw.raw_pattern is None else np.array(raw.raw_pattern, copy=True)
        description = bytes(raw.color_desc).decode("ascii", errors="replace")
        black = [float(value) for value in raw.black_level_per_channel]
        metadata = {
            "shape": list(visible.shape),
            "dtype": str(visible.dtype),
            "pattern": None if pattern is None else pattern.tolist(),
            "color_desc": description,
            "black_levels": black,
            "container_white": int(raw.white_level),
        }
    return visible, metadata


def split_cfa(
    mosaic: np.ndarray,
    black_levels: Iterable[float] | None = None,
    sites: dict[str, tuple[int, int]] | None = None,
) -> dict[str, np.ndarray]:
    mapping = SITE if sites is None else sites
    blacks = None if black_levels is None else tuple(float(v) for v in black_levels)
    result: dict[str, np.ndarray] = {}
    for channel in CHANNELS:
        row, column = mapping[channel]
        plane = mosaic[row::2, column::2].astype(np.float32, copy=True)
        if blacks is not None:
            plane -= blacks[COLOR_INDEX[channel]]
        result[channel] = plane
    return result


@dataclass(frozen=True)
class PeakFit:
    peak: np.ndarray
    valid: np.ndarray
    prominence: np.ndarray
    baseline: np.ndarray
    discrete_index: np.ndarray
    vertex_offset: np.ndarray


def peak_fit(
    curves: np.ndarray,
    *,
    baseline_percentile: float = 5.0,
    baseline_override: float | np.ndarray | None = None,
    mode: str = "log",
    vertex_sign: float = 1.0,
    coordinate_scale: float = 1.0,
    prominence_min: float = 0.0,
    offset_limit: float = 0.75,
) -> PeakFit:
    """Fit M33's baseline-subtracted log parabola around each curve's argmax.

    `curves` is `[frame, unit]`; a one-dimensional curve is accepted and
    returned as one unit.  Mutation parameters exist only so commissioning can
    plant the exact sign/domain/unit defects this function is intended to
    catch.
    """
    values = np.asarray(curves, dtype=np.float64)
    if values.ndim == 1:
        values = values[:, None]
    if values.ndim != 2 or values.shape[0] < 5:
        raise ValueError("curves must be [at least five frames, units]")

    nframe, nunit = values.shape
    if baseline_override is None:
        baseline = np.percentile(values, baseline_percentile, axis=0)
    else:
        baseline = np.broadcast_to(
            np.asarray(baseline_override, dtype=np.float64), (nunit,)
        ).copy()

    discrete = np.argmax(values, axis=0)
    clipped = np.clip(discrete, 1, nframe - 2)
    unit = np.arange(nunit)
    raw_minus = values[clipped - 1, unit]
    raw_centre = values[clipped, unit]
    raw_plus = values[clipped + 1, unit]

    shifted = np.stack(
        [raw_minus - baseline, raw_centre - baseline, raw_plus - baseline],
        axis=0,
    )
    positive = np.all(shifted > np.finfo(np.float64).tiny, axis=0)
    if mode == "log":
        fitted = np.log(np.maximum(shifted, np.finfo(np.float64).tiny))
    elif mode == "linear":
        fitted = shifted
    else:
        raise ValueError(f"unknown peak mode {mode!r}")

    denominator = fitted[0] - 2.0 * fitted[1] + fitted[2]
    concave = denominator < -1.0e-12
    safe_denominator = np.where(concave, denominator, -1.0)
    offset = (
        vertex_sign
        * 0.5
        * (fitted[0] - fitted[2])
        / safe_denominator
    )
    peak = coordinate_scale * (clipped.astype(np.float64) + offset)

    median = np.median(values, axis=0)
    prominence = (raw_centre - baseline) / np.maximum(
        median - baseline, np.finfo(np.float64).eps
    )
    half = baseline + 0.5 * (raw_centre - baseline)
    local = (
        (values[1:-1] > values[:-2])
        & (values[1:-1] >= values[2:])
        & (values[1:-1] > half[None, :])
    )
    unimodal = np.sum(local, axis=0) <= 1
    interior = (discrete > 0) & (discrete < nframe - 1)
    valid = (
        interior
        & positive
        & concave
        & np.isfinite(peak)
        & (np.abs(offset) <= offset_limit)
        & unimodal
        & (prominence >= prominence_min)
    )
    return PeakFit(
        peak=peak,
        valid=valid,
        prominence=prominence,
        baseline=baseline,
        discrete_index=discrete,
        vertex_offset=offset,
    )


def offset_values(fits: dict[str, PeakFit]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    green = 0.5 * (fits["G1"].peak + fits["G2"].peak)
    return (
        fits["R"].peak - green,
        fits["B"].peak - green,
        fits["G1"].peak - fits["G2"].peak,
    )


def phase_shift(reference: np.ndarray, image: np.ndarray) -> tuple[float, float, float]:
    """Return where reference content appears in `image`, as `(dy, dx, peak)`."""
    ref = np.asarray(reference, dtype=np.float64)
    img = np.asarray(image, dtype=np.float64)
    if ref.shape != img.shape or ref.ndim != 2:
        raise ValueError("phase-correlation inputs must be same-shape 2-D arrays")
    window = np.hanning(ref.shape[0])[:, None] * np.hanning(ref.shape[1])[None, :]
    a = np.fft.rfft2((ref - np.mean(ref)) * window)
    b = np.fft.rfft2((img - np.mean(img)) * window)
    cross = a * np.conj(b)
    magnitude = np.abs(cross)
    cross = np.where(magnitude > 1.0e-12, cross / magnitude, 0.0)
    correlation = np.fft.irfft2(cross, s=ref.shape)
    row, column = np.unravel_index(np.argmax(correlation), correlation.shape)
    dy = row - ref.shape[0] if row > ref.shape[0] // 2 else row
    dx = column - ref.shape[1] if column > ref.shape[1] // 2 else column
    return -float(dy), -float(dx), float(correlation[row, column])


def robust_polynomial_track(
    sampled_indices: np.ndarray,
    sampled_values: np.ndarray,
    nframe: int,
    *,
    degree: int = 3,
    max_abs_shift: float = 100.0,
) -> tuple[np.ndarray, dict]:
    """Huber-IRLS smooth direct-to-reference shifts, then round to integers."""
    x = np.asarray(sampled_indices, dtype=np.float64)
    y = np.asarray(sampled_values, dtype=np.float64)
    xn = 2.0 * x / max(nframe - 1, 1) - 1.0
    design = np.stack([xn**power for power in range(degree + 1)], axis=1)
    finite = np.isfinite(y) & (np.abs(y) <= max_abs_shift)
    if np.sum(finite) < degree + 2:
        return np.zeros(nframe, dtype=np.int32), {
            "ok": False,
            "reason": "too_few_finite_samples",
            "n_used": int(np.sum(finite)),
        }

    weights = finite.astype(np.float64)
    coefficients = np.zeros(degree + 1)
    for _ in range(12):
        root_w = np.sqrt(weights)
        coefficients, *_ = np.linalg.lstsq(
            design * root_w[:, None], y * root_w, rcond=None
        )
        residual = y - design @ coefficients
        centre = np.median(residual[finite])
        scale = 1.4826 * np.median(np.abs(residual[finite] - centre))
        scale = max(float(scale), 0.25)
        distance = np.abs(residual - centre)
        huber = np.minimum(1.0, 1.5 * scale / np.maximum(distance, 1.0e-12))
        new_weights = finite.astype(np.float64) * huber
        if np.max(np.abs(new_weights - weights)) < 1.0e-4:
            weights = new_weights
            break
        weights = new_weights

    all_x = np.arange(nframe, dtype=np.float64)
    all_xn = 2.0 * all_x / max(nframe - 1, 1) - 1.0
    all_design = np.stack(
        [all_xn**power for power in range(degree + 1)], axis=1
    )
    predicted = all_design @ coefficients
    residual = y - design @ coefficients
    used = finite & (weights >= 0.25)
    mad = (
        1.4826 * np.median(np.abs(residual[used] - np.median(residual[used])))
        if np.any(used)
        else math.inf
    )
    return np.rint(predicted).astype(np.int32), {
        "ok": bool(np.sum(used) >= degree + 2 and mad <= 2.0),
        "n_used": int(np.sum(used)),
        "n_sampled": int(x.size),
        "residual_mad_plane_px": float(mad),
        "raw_min": float(np.min(y[finite])),
        "raw_max": float(np.max(y[finite])),
        "fit_min": float(np.min(predicted)),
        "fit_max": float(np.max(predicted)),
        "coefficients": coefficients.tolist(),
    }


def tile_centres(
    plane_shape: tuple[int, int],
    *,
    rows: int = 6,
    columns: int = 8,
    margin: int = 320,
) -> np.ndarray:
    height, width = plane_shape
    ys = np.linspace(margin, height - margin - 1, rows)
    xs = np.linspace(margin, width - margin - 1, columns)
    return np.array(
        [(int(round(y)), int(round(x))) for y in ys for x in xs],
        dtype=np.int32,
    )


def extract_patches(
    plane: np.ndarray,
    centres: np.ndarray,
    shifts: np.ndarray,
    *,
    side: int,
) -> np.ndarray:
    """Extract `[tile, side+2, side+2]`, one-pixel padded for Sobel."""
    half = side // 2
    patches = []
    for (row, column), (dy, dx) in zip(centres, shifts, strict=True):
        centre_y = int(row + dy)
        centre_x = int(column + dx)
        y0 = centre_y - half - 1
        x0 = centre_x - half - 1
        patch = plane[y0 : y0 + side + 2, x0 : x0 + side + 2]
        if patch.shape != (side + 2, side + 2):
            raise ValueError(
                f"tile {(row, column)} shift {(dy, dx)} leaves plane {plane.shape}"
            )
        patches.append(patch)
    return np.stack(patches).astype(np.float32, copy=False)


def sobel_energy_means(
    padded_patches: np.ndarray,
    sides: tuple[int, ...],
) -> np.ndarray:
    """Exact 3x3 Sobel energy without filtering across the tile batch axis."""
    patches = np.asarray(padded_patches, dtype=np.float32)
    top = patches[:, :-2]
    middle = patches[:, 1:-1]
    bottom = patches[:, 2:]
    gx = (
        top[:, :, 2:]
        + 2.0 * middle[:, :, 2:]
        + bottom[:, :, 2:]
        - top[:, :, :-2]
        - 2.0 * middle[:, :, :-2]
        - bottom[:, :, :-2]
    )
    gy = (
        bottom[:, :, :-2]
        + 2.0 * bottom[:, :, 1:-1]
        + bottom[:, :, 2:]
        - top[:, :, :-2]
        - 2.0 * top[:, :, 1:-1]
        - top[:, :, 2:]
    )
    energy = gx * gx + gy * gy
    full_side = energy.shape[1]
    if energy.shape[2] != full_side:
        raise ValueError("Sobel energy patches must be square")
    result = np.empty((len(sides), energy.shape[0]), dtype=np.float64)
    for index, side in enumerate(sides):
        if side > full_side or side % 2:
            raise ValueError(f"invalid tile side {side}")
        offset = (full_side - side) // 2
        crop = energy[:, offset : offset + side, offset : offset + side]
        result[index] = np.mean(crop, axis=(1, 2), dtype=np.float64)
    return result


def median_ci(
    values: np.ndarray,
    *,
    draws: int = 10_000,
    seed: int = 20260902,
) -> dict:
    data = np.asarray(values, dtype=np.float64)
    data = data[np.isfinite(data)]
    if data.size < 2:
        return {
            "n": int(data.size),
            "median": None,
            "ci95": [None, None],
        }
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, data.size, size=(draws, data.size))
    boot = np.median(data[indices], axis=1)
    return {
        "n": int(data.size),
        "median": float(np.median(data)),
        "ci95": [
            float(np.percentile(boot, 2.5)),
            float(np.percentile(boot, 97.5)),
        ],
    }


def interpolate_curves(curves: np.ndarray, positions: np.ndarray) -> np.ndarray:
    values = np.asarray(curves, dtype=np.float64)
    pos = np.clip(np.asarray(positions, dtype=np.float64), 0.0, values.shape[0] - 1.000001)
    low = np.floor(pos).astype(int)
    fraction = pos - low
    unit = np.arange(values.shape[1])
    return values[low, unit] * (1.0 - fraction) + values[low + 1, unit] * fraction
