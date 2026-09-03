"""Independent checker for the externally fixed USM transfer amendment.

Commission mode is synthetic-only.  Outcome mode reads the frozen inputs but
imports no V-HEADTOHEAD3 implementation or result module.
"""

from __future__ import annotations

import os


THREAD_CAP = 8
_THREAD_ENVIRONMENT = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "OMP_THREAD_LIMIT",
    "TBB_NUM_THREADS",
)


def _capped_thread_value(value: str | None) -> str:
    try:
        return str(min(THREAD_CAP, max(1, int(value or THREAD_CAP))))
    except ValueError:
        return str(THREAD_CAP)


for _thread_name in _THREAD_ENVIRONMENT:
    os.environ[_thread_name] = _capped_thread_value(
        os.environ.get(_thread_name)
    )


import argparse
import ast
import copy
import hashlib
import io
import json
import math
import sys
from pathlib import Path
from typing import BinaryIO, Callable, Mapping, Sequence

import numpy as np
from skimage.registration import phase_cross_correlation
from skimage.transform import resize


SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-CHECK-1"
COMMISSION_SCHEMA = "V-HEADTOHEAD3-SHARPENING-TRANSFER-COMMISSION-1"
PRESENTATION_LABEL = "PRESENTATION_SENSITIVITY_NOT_RESOLUTION"
UNLICENSED = "UNLICENSED_GT_0.25"

STREHL = Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff")
PMAX0 = Path(r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif")
PMAX40 = Path(r"D:\edited\macro\test\2026-05-07-21.31.06 ZS PMax.tif")
FROZEN_MANIFEST = Path(__file__).with_name("sharpening_frozen.py")

EXPECTED_HASHES = {
    "strehl": "4E915024ED32DB0A9AF5F28B71C32832FEA49121A61E10E1BE2EE86EC46BAC0F",
    "pmax0": "B240FE4016E97EBB194497B2798A095C63C490C4FFF54018D48D34C7523719A0",
    "pmax40": "4D490F71EF63DA33758A49BF583AD2166CD014A5401ED64EDB5E5EDCABB47A3E",
}
INPUT_PATHS = {
    "strehl": STREHL,
    "pmax0": PMAX0,
    "pmax40": PMAX40,
}

FLAT_0 = (
    (2560, 2560),
    (2048, 2048),
    (3072, 5120),
    (2560, 5632),
    (1536, 2560),
    (3584, 4608),
    (2560, 4608),
    (3072, 3072),
    (2560, 3584),
    (2048, 5120),
    (3584, 2560),
    (4096, 3072),
)
FLAT_1 = (
    (2560, 4096),
    (2560, 3072),
    (2048, 5632),
    (3584, 4096),
    (2048, 4608),
    (3584, 3072),
    (4096, 3584),
    (4096, 2560),
    (3072, 3584),
    (3072, 5632),
    (2048, 2560),
    (2560, 5120),
)
DETAIL_0 = (
    (2048, 3072),
    (3584, 3584),
    (512, 4608),
    (3072, 4096),
    (3584, 5632),
    (3072, 6144),
    (1536, 5632),
    (2048, 6144),
    (1024, 4096),
    (512, 5632),
    (4096, 6144),
    (4096, 5120),
)
DETAIL_1 = (
    (512, 5120),
    (1024, 5632),
    (3072, 2560),
    (1024, 4608),
    (3584, 2048),
    (512, 6144),
    (1536, 4096),
    (4096, 4608),
    (3584, 5120),
    (4096, 5632),
    (3584, 6144),
    (3072, 4608),
)
DETAIL_SITES = DETAIL_0 + DETAIL_1

SITE_DIGEST = "B3A2F5279069A3CC85FB42F49F6FDA39397423D9A65565CAB88CCF8E627679F6"
SITE_CANDIDATES = 96
SITE_ELIGIBLE = 58
SITE_REJECTED = 38
EXPECTED_SITE_MANIFEST = {
    "SITE_DIGEST": SITE_DIGEST,
    "SITE_CANDIDATES": SITE_CANDIDATES,
    "SITE_ELIGIBLE": SITE_ELIGIBLE,
    "SITE_REJECTED": SITE_REJECTED,
    "FLAT_0": FLAT_0,
    "FLAT_1": FLAT_1,
    "DETAIL_0": DETAIL_0,
    "DETAIL_1": DETAIL_1,
}

SIDE = 512
SAMPLE_STEP = 8
MAX_SHIFT = 32
Q25_LOW = 0.20
Q25_HIGH = 0.25
USM_SIGMA = 1.0
USM_TRUNCATE = 6.0
USM_RADIUS = 6
USM_AMOUNT = 0.5
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260919
SYNTHETIC_TRANSFER = 5.560744
MIN_RETAINED_SITES = 12


class OutcomeStop(RuntimeError):
    """A preregistered stop that must not emit a numerical verdict."""


class SiteRejected(ValueError):
    """A technical inability to produce all measurements for one frozen site."""


def average_rank_field(a: np.ndarray) -> np.ndarray:
    """Return centred average ranks, using numpy.unique rather than rankdata."""
    x = np.asarray(a)
    if x.ndim != 2 or x.size < 2:
        raise ValueError("rank field requires a two-dimensional sample")
    _, inverse, counts = np.unique(
        x.ravel(), return_inverse=True, return_counts=True
    )
    ends = np.cumsum(counts, dtype=np.int64)
    starts = ends - counts
    average_one_based = (starts + 1.0 + ends) / 2.0
    n = x.size
    return (
        (average_one_based[inverse] - (n + 1.0) / 2.0) / n
    ).reshape(x.shape)


def licensed_mask(
    shape: tuple[int, int], band_scale: float = 1.0
) -> np.ndarray:
    if (
        len(shape) != 2
        or min(shape) < 2
        or not np.isfinite(band_scale)
        or band_scale <= 0.0
    ):
        raise ValueError("invalid Q25 shape or geometry scale")
    fy = np.fft.fftfreq(shape[0])[:, None]
    fx = np.fft.rfftfreq(shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    return (
        (radius >= Q25_LOW * band_scale)
        & (radius < Q25_HIGH * band_scale)
    )


def q25_rank_field(q: np.ndarray, band_scale: float = 1.0) -> float:
    """Hann-weighted real-FFT Q25 with a fixed spatial-rank denominator."""
    x = np.asarray(q, np.float64).copy()
    if x.ndim != 2:
        raise ValueError("Q25 rank field must be two-dimensional")
    x -= np.mean(x)
    variance = float(np.mean(x * x))
    if not np.isfinite(variance) or variance <= 0.0:
        raise ValueError("Q25 requires non-constant finite ranks")
    window = (
        np.hanning(x.shape[0])[:, None]
        * np.hanning(x.shape[1])[None, :]
    )
    power = np.abs(np.fft.rfft2(x * window)) ** 2
    if x.shape[1] % 2 == 0:
        power[:, 1:-1] *= 2.0
    else:
        power[:, 1:] *= 2.0
    numerator = float(
        np.sum(
            power[licensed_mask(x.shape, band_scale)],
            dtype=np.float64,
        )
    )
    denominator = (
        x.size
        * float(np.sum(window * window, dtype=np.float64))
        * variance
    )
    if (
        not np.isfinite(numerator)
        or numerator < 0.0
        or not np.isfinite(denominator)
        or denominator <= 0.0
    ):
        raise ValueError("Q25 has invalid admitted power or denominator")
    return numerator / denominator


def q25(a: np.ndarray, band_scale: float = 1.0) -> float:
    return q25_rank_field(average_rank_field(np.asarray(a)), band_scale)


def gaussian_kernel_1d(
    sigma: float = USM_SIGMA, truncate: float = USM_TRUNCATE
) -> np.ndarray:
    """Construct the normalized sampled Gaussian used by scipy.ndimage."""
    if (
        not np.isfinite(sigma)
        or sigma <= 0.0
        or not np.isfinite(truncate)
        or truncate <= 0.0
    ):
        raise ValueError("Gaussian sigma and truncate must be positive")
    radius = int(truncate * sigma + 0.5)
    coordinate = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-0.5 * (coordinate / sigma) ** 2)
    kernel /= np.sum(kernel, dtype=np.float64)
    return kernel


def gaussian_kernel_2d(
    sigma: float = USM_SIGMA, truncate: float = USM_TRUNCATE
) -> np.ndarray:
    kernel = gaussian_kernel_1d(sigma, truncate)
    return np.multiply.outer(kernel, kernel)


def _convolve_axis(
    a: np.ndarray,
    kernel: np.ndarray,
    axis: int,
    *,
    pad_mode: str,
) -> np.ndarray:
    x = np.asarray(a, np.float64)
    if x.ndim != 2 or axis not in (0, 1):
        raise ValueError("Gaussian convolution requires a 2-D field")
    weights = np.asarray(kernel, np.float64)
    if weights.ndim != 1 or weights.size % 2 != 1:
        raise ValueError("Gaussian kernel must have odd one-dimensional support")
    radius = weights.size // 2
    padding = ((radius, radius), (0, 0))
    if axis == 1:
        padding = ((0, 0), (radius, radius))
    padded = np.pad(x, padding, mode=pad_mode)
    if axis == 0:
        out = weights[radius] * padded[
            radius : radius + x.shape[0], :
        ]
    else:
        out = weights[radius] * padded[
            :, radius : radius + x.shape[1]
        ]
    # scipy.ndimage's symmetric correlate path accumulates the centre first,
    # then equidistant pairs.  Preserve that order: rank ties on the analytic
    # edge fixture are intentionally sensitive to last-bit differences.
    out = np.asarray(out, np.float64)
    if axis == 0:
        for delta in range(radius, 0, -1):
            out += weights[radius + delta] * (
                padded[
                    radius - delta : radius - delta + x.shape[0],
                    :,
                ]
                + padded[
                    radius + delta : radius + delta + x.shape[0],
                    :,
                ]
            )
    else:
        for delta in range(radius, 0, -1):
            out += weights[radius + delta] * (
                padded[
                    :,
                    radius - delta : radius - delta + x.shape[1],
                ]
                + padded[
                    :,
                    radius + delta : radius + delta + x.shape[1],
                ]
            )
    return out


def _analytic_gaussian_blur(
    a: np.ndarray,
    sigma: float,
    truncate: float,
    *,
    pad_mode: str,
) -> np.ndarray:
    kernel = gaussian_kernel_1d(sigma, truncate)
    vertical = _convolve_axis(a, kernel, 0, pad_mode=pad_mode)
    return _convolve_axis(vertical, kernel, 1, pad_mode=pad_mode)


def gaussian_blur_nearest(a: np.ndarray) -> np.ndarray:
    """Exact analytic sigma-1/truncate-6 separable blur with nearest edges."""
    return _analytic_gaussian_blur(
        a,
        USM_SIGMA,
        USM_TRUNCATE,
        pad_mode="edge",
    )


def usm05(a: np.ndarray) -> np.ndarray:
    """The frozen unclipped radius-1/amount-0.5 unsharp mask."""
    x = np.asarray(a, np.float64)
    low = gaussian_blur_nearest(x)
    return x + USM_AMOUNT * (x - low)


def sha256_stream(handle: BinaryIO, chunk: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    while True:
        block = handle.read(chunk)
        if not block:
            break
        digest.update(block)
    return digest.hexdigest().upper()


def sha256_path(path: Path) -> str:
    with path.open("rb") as handle:
        return sha256_stream(handle)


def _canonical_sites(value: object) -> tuple[tuple[int, int], ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    rows: list[tuple[int, int]] = []
    for row in value:
        if (
            not isinstance(row, (list, tuple))
            or len(row) != 2
            or type(row[0]) is not int
            or type(row[1]) is not int
        ):
            return None
        rows.append((row[0], row[1]))
    return tuple(rows)


def provenance_mismatches(
    hashes: Mapping[str, object],
    manifest: Mapping[str, object],
) -> list[str]:
    mismatches: list[str] = []
    if set(hashes) != set(EXPECTED_HASHES):
        mismatches.append("input_hash_keys")
    for name, expected in EXPECTED_HASHES.items():
        if hashes.get(name) != expected:
            mismatches.append(f"input_hash:{name}")
    if set(manifest) != set(EXPECTED_SITE_MANIFEST):
        mismatches.append("site_manifest_keys")
    for name in (
        "SITE_DIGEST",
        "SITE_CANDIDATES",
        "SITE_ELIGIBLE",
        "SITE_REJECTED",
    ):
        if manifest.get(name) != EXPECTED_SITE_MANIFEST[name]:
            mismatches.append(f"site_manifest:{name}")
    for name in ("FLAT_0", "FLAT_1", "DETAIL_0", "DETAIL_1"):
        if _canonical_sites(manifest.get(name)) != EXPECTED_SITE_MANIFEST[name]:
            mismatches.append(f"site_manifest:{name}")
    return mismatches


def parse_frozen_manifest(path: Path) -> dict[str, object]:
    required = set(EXPECTED_SITE_MANIFEST)
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        raise OutcomeStop(f"cannot read frozen site manifest: {exc}") from exc
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in required:
            continue
        if target.id in values:
            raise OutcomeStop(f"duplicate frozen assignment: {target.id}")
        try:
            values[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError) as exc:
            raise OutcomeStop(
                f"non-literal frozen assignment: {target.id}"
            ) from exc
    if set(values) != required:
        missing = sorted(required - set(values))
        raise OutcomeStop(f"frozen site manifest is incomplete: {missing}")
    return values


def verify_frozen_provenance() -> tuple[dict[str, str], dict[str, object]]:
    actual_hashes: dict[str, str] = {}
    try:
        for name, path in INPUT_PATHS.items():
            actual_hashes[name] = sha256_path(path)
    except OSError as exc:
        raise OutcomeStop(f"cannot hash frozen input: {exc}") from exc
    manifest = parse_frozen_manifest(FROZEN_MANIFEST)
    mismatches = provenance_mismatches(actual_hashes, manifest)
    if mismatches:
        raise OutcomeStop(
            "frozen provenance changed: " + ",".join(mismatches)
        )
    return actual_hashes, manifest


def pearson(a: np.ndarray, b: np.ndarray) -> float:
    x = np.asarray(a, np.float64).ravel()
    y = np.asarray(b, np.float64).ravel()
    if x.shape != y.shape:
        raise ValueError("Pearson inputs differ in shape")
    x -= np.mean(x)
    y -= np.mean(y)
    denominator = math.sqrt(float(np.dot(x, x) * np.dot(y, y)))
    return float(np.dot(x, y) / denominator) if denominator > 0.0 else math.nan


def overlap_after_shift(
    reference: np.ndarray,
    moving: np.ndarray,
    correction: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    dy, dx = correction
    h, w = reference.shape
    return (
        np.asarray(reference)[
            max(0, dy) : min(h, h + dy),
            max(0, dx) : min(w, w + dx),
        ],
        np.asarray(moving)[
            max(0, -dy) : min(h, h - dy),
            max(0, -dx) : min(w, w - dx),
        ],
    )


def phase_correction(
    reference: np.ndarray,
    moving: np.ndarray,
) -> tuple[int, int, float]:
    a = np.asarray(reference, np.float64)
    b = np.asarray(moving, np.float64)
    if a.shape != b.shape or a.ndim != 2:
        raise ValueError("phase correlation requires equal 2-D shapes")
    shift, _, _ = phase_cross_correlation(
        a,
        b,
        upsample_factor=1,
        normalization="phase",
    )
    if shift.shape != (2,) or not np.all(np.isfinite(shift)):
        raise ValueError("phase correlation returned a non-finite shift")
    correction = (
        int(round(float(shift[0]))),
        int(round(float(shift[1]))),
    )
    aa, bb = overlap_after_shift(a, b, correction)
    return correction[0], correction[1], pearson(aa, bb)


def resized_rank(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    return resize(
        average_rank_field(np.asarray(a)),
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )


def green_memmap(path: Path) -> np.ndarray:
    import tifffile

    image = tifffile.memmap(path)
    if image.ndim != 3 or image.shape[2] < 2:
        raise OutcomeStop(f"{path}: expected an HxWxC TIFF, got {image.shape}")
    return image[:, :, 1]


def sampled_rank(path: Path) -> np.ndarray:
    green = green_memmap(path)
    sample = np.asarray(green[::SAMPLE_STEP, ::SAMPLE_STEP], np.float64)
    return average_rank_field(sample)


def scale_score(
    strehl_rank: np.ndarray,
    comparator_rank: np.ndarray,
    scale: float,
) -> tuple[float, np.ndarray]:
    shape = (
        int(round(comparator_rank.shape[0] * scale)),
        int(round(comparator_rank.shape[1] * scale)),
    )
    moved = resize(
        comparator_rank,
        shape,
        order=1,
        mode="reflect",
        anti_aliasing=False,
        preserve_range=True,
    )
    tile = 128
    high_y = min(strehl_rank.shape[0], moved.shape[0]) - tile
    high_x = min(strehl_rank.shape[1], moved.shape[1]) - tile
    if high_y <= tile or high_x <= tile:
        return float("-inf"), np.empty((0, 3), np.float64)
    ys = np.linspace(tile // 2, high_y - tile // 2, 6).astype(int)
    xs = np.linspace(tile // 2, high_x - tile // 2, 6).astype(int)
    rows: list[tuple[float, float, float]] = []
    for y in ys:
        for x in xs:
            a = strehl_rank[y : y + tile, x : x + tile]
            b = moved[y : y + tile, x : x + tile]
            dy, dx, _ = phase_correction(a, b)
            if abs(dy) > tile // 4 or abs(dx) > tile // 4:
                continue
            aa, bb = overlap_after_shift(a, b, (dy, dx))
            score = pearson(aa, bb)
            if np.isfinite(score):
                rows.append((float(dy), float(dx), score))
    if not rows:
        return float("-inf"), np.empty((0, 3), np.float64)
    offsets = np.asarray(rows, np.float64)
    return float(np.median(offsets[:, 2])), offsets


def fit_geometry(strehl_path: Path, comparator_path: Path) -> dict:
    strehl_rank = sampled_rank(strehl_path)
    comparator_rank = sampled_rank(comparator_path)
    coarse_scales = np.arange(0.96, 1.081, 0.005, dtype=np.float64)
    coarse_values = [
        scale_score(strehl_rank, comparator_rank, float(scale))
        for scale in coarse_scales
    ]
    coarse_index = int(np.argmax([row[0] for row in coarse_values]))
    coarse_interior = 0 < coarse_index < len(coarse_scales) - 1
    coarse_best = float(coarse_scales[coarse_index])
    fine_scales = np.arange(
        coarse_best - 0.006,
        coarse_best + 0.0061,
        0.001,
        dtype=np.float64,
    )
    fine_values = [
        scale_score(strehl_rank, comparator_rank, float(scale))
        for scale in fine_scales
    ]
    fine_index = int(np.argmax([row[0] for row in fine_values]))
    fine_interior = 0 < fine_index < len(fine_scales) - 1
    offsets = fine_values[fine_index][1]
    if offsets.size == 0:
        raise OutcomeStop("geometry fit produced no admissible tiles")
    median_offset = np.median(offsets[:, :2], axis=0)
    correction = median_offset * SAMPLE_STEP
    residual = (offsets[:, :2] - median_offset) * SAMPLE_STEP
    residual_rms = float(
        np.sqrt(np.mean(np.sum(residual * residual, axis=1)))
    )
    return {
        "scale": float(fine_scales[fine_index]),
        "score": float(fine_values[fine_index][0]),
        "coarse_interior": bool(coarse_interior),
        "fine_interior": bool(fine_interior),
        "global_correction": [
            float(correction[0]),
            float(correction[1]),
        ],
        "residual_rms": residual_rms,
        "sample_shapes": [
            list(strehl_rank.shape),
            list(comparator_rank.shape),
        ],
    }


def crop_centered(
    a: np.ndarray,
    cy: float,
    cx: float,
    side: int,
) -> np.ndarray | None:
    y0 = int(round(cy - side / 2.0))
    x0 = int(round(cx - side / 2.0))
    if (
        y0 < 0
        or x0 < 0
        or y0 + side > a.shape[0]
        or x0 + side > a.shape[1]
    ):
        return None
    return np.asarray(a[y0 : y0 + side, x0 : x0 + side])


def _local_correction(
    reference_rank: np.ndarray,
    moving_rank: np.ndarray,
    label: str,
) -> tuple[int, int, float]:
    dy, dx, score = phase_correction(reference_rank, moving_rank)
    if (
        not np.isfinite(dy)
        or not np.isfinite(dx)
        or abs(dy) > MAX_SHIFT
        or abs(dx) > MAX_SHIFT
    ):
        raise SiteRejected(f"{label}:correction_out_of_range")
    if not np.isfinite(score):
        raise SiteRejected(f"{label}:non_finite_correlation")
    return dy, dx, score


def registered_pmax_pair(
    reference: np.ndarray,
    moving: np.ndarray,
    centre: Sequence[int],
) -> tuple[np.ndarray, np.ndarray, dict]:
    cy, cx = map(float, centre)
    pad = MAX_SHIFT + 8
    large_side = SIDE + 2 * pad
    a_large = crop_centered(reference, cy, cx, large_side)
    b_large = crop_centered(moving, cy, cx, large_side)
    if a_large is None or b_large is None:
        raise SiteRejected("pmax_pair:bounds")
    dy, dx, score = _local_correction(
        average_rank_field(a_large),
        average_rank_field(b_large),
        "pmax_pair",
    )
    a = crop_centered(reference, cy, cx, SIDE)
    b = crop_centered(moving, cy - dy, cx - dx, SIDE)
    if a is None or b is None:
        raise SiteRejected("pmax_pair:corrected_bounds")
    return a, b, {
        "correction": [dy, dx],
        "correlation": score,
    }


def registered_strehl_pair(
    strehl: np.ndarray,
    comparator: np.ndarray,
    comparator_centre: Sequence[int],
    geometry: Mapping[str, object],
    label: str,
) -> tuple[np.ndarray, np.ndarray, dict]:
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    cy, cx = map(float, comparator_centre)
    sy = scale * cy + gy
    sx = scale * cx + gx
    comparator_side = int(round(SIDE / scale))
    s = crop_centered(strehl, sy, sx, SIDE)
    c0 = crop_centered(comparator, cy, cx, comparator_side)
    if s is None or c0 is None:
        raise SiteRejected(f"{label}:mapped_bounds")
    dy, dx, score = _local_correction(
        average_rank_field(s),
        resized_rank(c0, s.shape),
        label,
    )
    c = crop_centered(
        comparator,
        cy - dy / scale,
        cx - dx / scale,
        comparator_side,
    )
    if c is None:
        raise SiteRejected(f"{label}:corrected_bounds")
    return s, c, {
        "correction": [dy, dx],
        "correlation": score,
        "comparator_side": comparator_side,
    }


def _required_q25(
    label: str,
    image: np.ndarray,
    band_scale: float = 1.0,
) -> float:
    try:
        value = q25(image, band_scale)
    except ValueError as exc:
        raise SiteRejected(f"{label}:{exc}") from exc
    if not np.isfinite(value) or value <= 0.0:
        raise SiteRejected(f"{label}:non_positive")
    return value


def measure_site(
    pmax0: np.ndarray,
    pmax40: np.ndarray,
    strehl: np.ndarray,
    centre: Sequence[int],
    geometry0: Mapping[str, object],
    geometry40: Mapping[str, object],
) -> tuple[dict[str, float], dict]:
    p0, p40, pmax_diagnostic = registered_pmax_pair(
        pmax0, pmax40, centre
    )
    s40, p40s, strehl40_diagnostic = registered_strehl_pair(
        strehl,
        pmax40,
        centre,
        geometry40,
        "strehl_to_pmax40",
    )
    s0, p0s, strehl0_diagnostic = registered_strehl_pair(
        strehl,
        pmax0,
        centre,
        geometry0,
        "strehl_to_pmax0",
    )

    q_p0 = _required_q25("pmax0", p0)
    q_p40 = _required_q25("pmax40", p40)
    q_usm_p0 = _required_q25("usm_pmax0", usm05(p0))
    q_s40 = _required_q25("strehl_for_pmax40", s40)
    q_usm_s40 = _required_q25("usm_strehl", usm05(s40))
    q_p40s = _required_q25(
        "pmax40_for_strehl",
        p40s,
        float(geometry40["scale"]),
    )
    q_s0 = _required_q25("strehl_for_pmax0", s0)
    q_p0s = _required_q25(
        "pmax0_for_strehl",
        p0s,
        float(geometry0["scale"]),
    )

    logs = {
        "T0": math.log(q_usm_p0) - math.log(q_p0),
        "M40": math.log(q_usm_p0) - math.log(q_p40),
        "TS": math.log(q_usm_s40) - math.log(q_s40),
        "S40": math.log(q_usm_s40) - math.log(q_p40s),
        "R0": math.log(q_s0) - math.log(q_p0s),
        "O40": math.log(q_p40) - math.log(q_p0),
    }
    if not all(np.isfinite(value) for value in logs.values()):
        raise SiteRejected("non_finite_log_ratio")
    return logs, {
        "centre": list(map(int, centre)),
        "pmax40_to_pmax0": pmax_diagnostic,
        "strehl_to_pmax40": strehl40_diagnostic,
        "strehl_to_pmax0": strehl0_diagnostic,
    }


def bootstrap_log_summaries(
    logs: Mapping[str, Sequence[float]],
    *,
    seed: int = BOOTSTRAP_SEED,
    draws: int = BOOTSTRAP_DRAWS,
) -> dict[str, dict[str, float | int]]:
    if not logs:
        raise ValueError("bootstrap requires at least one quantity")
    names = list(logs)
    columns = [np.asarray(logs[name], np.float64) for name in names]
    n = len(columns[0])
    if (
        n < 6
        or any(column.ndim != 1 or len(column) != n for column in columns)
        or any(not np.all(np.isfinite(column)) for column in columns)
    ):
        raise ValueError("bootstrap requires equal finite site-log vectors")
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, n, size=(draws, n))
    result: dict[str, dict[str, float | int]] = {}
    for name, column in zip(names, columns):
        boot = np.mean(column[indices], axis=1)
        low, high = np.quantile(boot, [0.025, 0.975])
        point_log = float(np.mean(column))
        result[name] = {
            "n": n,
            "point_log": point_log,
            "point": float(np.exp(point_log)),
            "ci_low": float(np.exp(low)),
            "ci_high": float(np.exp(high)),
        }
    return result


def frozen_verdict(
    t0: Mapping[str, float],
    m40: Mapping[str, float],
) -> str:
    if t0["ci_low"] > 1.05 and m40["ci_low"] > 1.0:
        return "REAL_TRANSFER_SUFFICIENT"
    if t0["ci_low"] > 1.05 and m40["ci_high"] < 1.0:
        return "REAL_TRANSFER_PARTIAL"
    if t0["ci_low"] >= 0.95 and t0["ci_high"] <= 1.05:
        return "NO_REAL_TRANSFER"
    return "UNRESOLVED"


def _transfer_comparisons(t0: Mapping[str, float]) -> dict:
    synthetic_log = math.log(SYNTHETIC_TRANSFER)
    return {
        "T0_over_synthetic": {
            "point": t0["point"] / SYNTHETIC_TRANSFER,
            "ci_low": t0["ci_low"] / SYNTHETIC_TRANSFER,
            "ci_high": t0["ci_high"] / SYNTHETIC_TRANSFER,
        },
        "log_T0_over_log_synthetic": {
            "point": math.log(t0["point"]) / synthetic_log,
            "ci_low": math.log(t0["ci_low"]) / synthetic_log,
            "ci_high": math.log(t0["ci_high"]) / synthetic_log,
        },
        "synthetic_reference": SYNTHETIC_TRANSFER,
    }


def _public_geometry(geometry: Mapping[str, object]) -> dict:
    return {
        "scale": geometry["scale"],
        "score": geometry["score"],
        "coarse_interior": geometry["coarse_interior"],
        "fine_interior": geometry["fine_interior"],
        "global_correction": geometry["global_correction"],
        "residual_rms": geometry["residual_rms"],
        "sample_shapes": geometry["sample_shapes"],
    }


def outcome() -> dict:
    commission = commission_result()
    if not commission["green"]:
        raise OutcomeStop("synthetic commission failed")
    actual_hashes, _ = verify_frozen_provenance()

    geometry0 = fit_geometry(STREHL, PMAX0)
    geometry40 = fit_geometry(STREHL, PMAX40)
    for name, geometry in (
        ("pmax0", geometry0),
        ("pmax40", geometry40),
    ):
        if (
            not geometry["coarse_interior"]
            or not geometry["fine_interior"]
        ):
            raise OutcomeStop(f"{name} geometry optimum is not interior")

    pmax0 = green_memmap(PMAX0)
    pmax40 = green_memmap(PMAX40)
    strehl = green_memmap(STREHL)
    logs: dict[str, list[float]] = {
        name: [] for name in ("T0", "M40", "TS", "S40", "R0", "O40")
    }
    retained: list[dict] = []
    rejected: list[dict] = []
    for centre in DETAIL_SITES:
        try:
            site_logs, diagnostic = measure_site(
                pmax0,
                pmax40,
                strehl,
                centre,
                geometry0,
                geometry40,
            )
        except SiteRejected as exc:
            rejected.append(
                {"centre": list(centre), "reason": str(exc)}
            )
            continue
        for name in logs:
            logs[name].append(site_logs[name])
        retained.append(diagnostic)

    if len(retained) < MIN_RETAINED_SITES:
        raise OutcomeStop(
            f"only {len(retained)} of {len(DETAIL_SITES)} sites retained"
        )
    summaries = bootstrap_log_summaries(logs)
    verdict = frozen_verdict(summaries["T0"], summaries["M40"])
    return {
        "schema": SCHEMA,
        "status": "MEASURED_PENDING_CROSSCHECK",
        "label": PRESENTATION_LABEL,
        "provenance": {
            "status": "GREEN",
            "hashes": actual_hashes,
            "site_digest": SITE_DIGEST,
            "site_candidates": SITE_CANDIDATES,
            "site_eligible": SITE_ELIGIBLE,
            "site_rejected": SITE_REJECTED,
        },
        "operator": {
            "sigma": USM_SIGMA,
            "truncate": USM_TRUNCATE,
            "radius": USM_RADIUS,
            "amount": USM_AMOUNT,
            "boundary": "nearest",
            "clipping": False,
        },
        "licensed_band": {
            "low_inclusive": Q25_LOW,
            "high_exclusive": Q25_HIGH,
            "unit": "cycles_per_native_pixel",
        },
        "bootstrap": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "paired_site_indices": True,
        },
        "geometry": {
            "pmax0": _public_geometry(geometry0),
            "pmax40": _public_geometry(geometry40),
        },
        "frozen_sites": [list(site) for site in DETAIL_SITES],
        "retained_count": len(retained),
        "retained_sites": retained,
        "rejected_sites": rejected,
        "quantities": summaries,
        "transfer_vs_synthetic": _transfer_comparisons(summaries["T0"]),
        "unlicensed": UNLICENSED,
        "candidate_verdict": verdict,
    }


def _q25_full_fft_oracle(
    q: np.ndarray,
    band_scale: float = 1.0,
) -> float:
    x = np.asarray(q, np.float64).copy()
    x -= np.mean(x)
    variance = float(np.mean(x * x))
    window = (
        np.hanning(x.shape[0])[:, None]
        * np.hanning(x.shape[1])[None, :]
    )
    power = np.abs(np.fft.fft2(x * window)) ** 2
    fy = np.fft.fftfreq(x.shape[0])[:, None]
    fx = np.fft.fftfreq(x.shape[1])[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    admitted = (
        (radius >= Q25_LOW * band_scale)
        & (radius < Q25_HIGH * band_scale)
    )
    numerator = float(np.sum(power[admitted], dtype=np.float64))
    denominator = (
        x.size
        * float(np.sum(window * window, dtype=np.float64))
        * variance
    )
    return numerator / denominator


def _direct_nearest_blur_oracle(a: np.ndarray) -> np.ndarray:
    x = np.asarray(a, np.float64)
    coordinate = np.arange(-USM_RADIUS, USM_RADIUS + 1)
    yy, xx = np.meshgrid(coordinate, coordinate, indexing="ij")
    kernel = np.exp(
        -0.5 * (yy.astype(np.float64) ** 2 + xx.astype(np.float64) ** 2)
        / (USM_SIGMA**2)
    )
    kernel /= np.sum(kernel, dtype=np.float64)
    out = np.empty_like(x, dtype=np.float64)
    for y in range(x.shape[0]):
        rows = np.clip(y + coordinate, 0, x.shape[0] - 1)
        for column in range(x.shape[1]):
            columns = np.clip(
                column + coordinate, 0, x.shape[1] - 1
            )
            out[y, column] = float(
                np.sum(x[np.ix_(rows, columns)] * kernel)
            )
    return out


def _operator_matches_oracle(
    candidate: Callable[[np.ndarray], np.ndarray],
) -> bool:
    impulse = np.zeros((31, 33), np.float64)
    impulse[15, 16] = 1.0
    border = (
        np.arange(17, dtype=np.float64)[:, None] ** 2
        + 0.37 * np.arange(19, dtype=np.float64)[None, :]
    )
    for fixture in (impulse, border):
        expected_low = _direct_nearest_blur_oracle(fixture)
        expected = fixture + USM_AMOUNT * (fixture - expected_low)
        if not np.allclose(
            candidate(fixture),
            expected,
            rtol=2e-14,
            atol=2e-14,
        ):
            return False
    return True


def _vertical_edge(
    sigma: float,
    *,
    angle_degrees: float = 5.0,
    side: int = 256,
) -> np.ndarray:
    from scipy.special import ndtr

    yy, xx = np.mgrid[0:side, 0:side]
    slope = math.tan(math.radians(angle_degrees))
    intercept = side / 2.0 - slope * (side - 1) / 2.0
    distance = (
        xx - (slope * yy + intercept)
    ) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def _tone_maps(a: np.ndarray) -> dict[str, np.ndarray]:
    x = np.asarray(a, np.float64)
    return {
        "affine": 1.7 * x + 0.13,
        "gamma3": np.power(x, 3.0),
        "logistic": 1.0 / (1.0 + np.exp(-10.0 * (x - 0.5))),
    }


def _matches_six_places(value: float, expected: float) -> bool:
    return round(float(value), 6) == expected


def _translate_nonwrapping(
    a: np.ndarray,
    displacement: tuple[int, int],
) -> np.ndarray:
    x = np.asarray(a)
    dy, dx = displacement
    out = np.zeros_like(x)
    height = x.shape[0] - abs(dy)
    width = x.shape[1] - abs(dx)
    source_y = max(0, -dy)
    source_x = max(0, -dx)
    target_y = max(0, dy)
    target_x = max(0, dx)
    out[
        target_y : target_y + height,
        target_x : target_x + width,
    ] = x[
        source_y : source_y + height,
        source_x : source_x + width,
    ]
    return out


def _shift_gate(
    reference: np.ndarray,
    moving: np.ndarray,
    planted: tuple[int, int],
    estimator: Callable[
        [np.ndarray, np.ndarray], tuple[int, int, float]
    ],
) -> bool:
    dy, dx, score = estimator(reference, moving)
    if (dy, dx) != (-planted[0], -planted[1]):
        return False
    before = pearson(reference, moving)
    a, b = overlap_after_shift(reference, moving, (dy, dx))
    after = pearson(a, b)
    return (
        np.isfinite(score)
        and np.isfinite(before)
        and np.isfinite(after)
        and after > before
        and after > 0.999999999
    )


def _expected_manifest_copy() -> dict[str, object]:
    return {
        "SITE_DIGEST": SITE_DIGEST,
        "SITE_CANDIDATES": SITE_CANDIDATES,
        "SITE_ELIGIBLE": SITE_ELIGIBLE,
        "SITE_REJECTED": SITE_REJECTED,
        "FLAT_0": [list(row) for row in FLAT_0],
        "FLAT_1": [list(row) for row in FLAT_1],
        "DETAIL_0": [list(row) for row in DETAIL_0],
        "DETAIL_1": [list(row) for row in DETAIL_1],
    }


def commission_result() -> dict:
    controls: dict[str, bool] = {}
    mutants: dict[str, bool] = {}

    tied = np.array(
        [[4, 1, 1], [0, 2, 8], [7, 3, 6]], np.float64
    )
    expected_rank = np.array(
        [[6, 2.5, 2.5], [1, 4, 9], [8, 5, 7]], np.float64
    )
    expected_rank = (expected_rank - 5.0) / 9.0
    controls["numpy_unique_average_ranks"] = np.array_equal(
        average_rank_field(tied), expected_rank
    )

    rng = np.random.default_rng(2026091901)
    for label, shape in (("even", (31, 32)), ("odd", (32, 31))):
        rank = average_rank_field(rng.normal(size=shape))
        controls[f"weighted_real_fft_{label}"] = math.isclose(
            q25_rank_field(rank),
            _q25_full_fft_oracle(rank),
            rel_tol=2e-14,
            abs_tol=2e-14,
        )

    impulse = np.zeros((31, 33), np.float64)
    impulse[15, 16] = 1.0
    expected_impulse = _direct_nearest_blur_oracle(impulse)
    actual_impulse = gaussian_blur_nearest(impulse)
    support = np.argwhere(actual_impulse > 0.0)
    controls["analytic_radius6_gaussian_impulse"] = (
        gaussian_kernel_1d().size == 2 * USM_RADIUS + 1
        and np.array_equal(support.min(axis=0), [9, 10])
        and np.array_equal(support.max(axis=0), [21, 22])
        and np.allclose(
            actual_impulse,
            expected_impulse,
            rtol=2e-14,
            atol=2e-14,
        )
    )
    controls["nearest_boundary_operator"] = _operator_matches_oracle(usm05)

    changed_amount = lambda x: np.asarray(x, np.float64) + 0.6 * (
        np.asarray(x, np.float64) - gaussian_blur_nearest(x)
    )
    changed_boundary = lambda x: np.asarray(x, np.float64) + USM_AMOUNT * (
        np.asarray(x, np.float64)
        - _analytic_gaussian_blur(
            x,
            USM_SIGMA,
            USM_TRUNCATE,
            pad_mode="reflect",
        )
    )
    mutants["changed_amount"] = not _operator_matches_oracle(changed_amount)
    mutants["changed_boundary"] = not _operator_matches_oracle(
        changed_boundary
    )

    base_image = _vertical_edge(1.5)
    base = q25(base_image)
    identity_ratio = q25(base_image.copy()) / base
    blurred = _analytic_gaussian_blur(
        base_image,
        0.75,
        USM_TRUNCATE,
        pad_mode="edge",
    )
    blur_ratio = q25(blurred) / base
    improvement_ratio = q25(_vertical_edge(1.2)) / base
    usm_ratio = q25(usm05(base_image)) / base
    controls["base_anchor"] = round(base, 9) == 0.000952160
    controls["identity_parity"] = identity_ratio == 1.0
    controls["blur_degradation"] = _matches_six_places(
        blur_ratio, 0.841501
    )
    controls["physical_improvement"] = _matches_six_places(
        improvement_ratio, 0.977981
    )
    controls["exact_r1_a0_5_usm_improvement"] = _matches_six_places(
        usm_ratio, SYNTHETIC_TRANSFER
    )
    mutants["blur_disabled"] = not _matches_six_places(
        identity_ratio, 0.841501
    )
    mutants["usm_disabled"] = not _matches_six_places(
        identity_ratio, SYNTHETIC_TRANSFER
    )

    tone_expected = {
        "affine": 0.999963,
        "gamma3": 1.000000,
        "logistic": 0.999966,
    }
    tone_ratios = {
        name: q25(image) / base
        for name, image in _tone_maps(base_image).items()
    }
    for name, expected in tone_expected.items():
        controls[f"tone_{name}"] = _matches_six_places(
            tone_ratios[name], expected
        )

    cap_mask = licensed_mask((128, 128))
    controls["licensed_bin_admitted"] = bool(cap_mask[0, 28])
    controls["above_cap_bin_rejected"] = not bool(cap_mask[0, 36])
    fy = np.fft.fftfreq(128)[:, None]
    fx = np.fft.rfftfreq(128)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    reversed_mask = radius >= Q25_HIGH
    mutants["above_cap_mask"] = not (
        bool(reversed_mask[0, 28])
        and not bool(reversed_mask[0, 36])
    )

    shift_reference = rng.normal(size=(96, 104))
    shift_plants = ((5, -7), (-6, 4))
    for index, planted in enumerate(shift_plants):
        moving = _translate_nonwrapping(shift_reference, planted)
        controls[f"shift_sign_{index}"] = _shift_gate(
            shift_reference,
            moving,
            planted,
            phase_correction,
        )
    first_plant = shift_plants[0]
    first_moving = _translate_nonwrapping(shift_reference, first_plant)
    mutants["shift_noop"] = not _shift_gate(
        shift_reference,
        first_moving,
        first_plant,
        lambda a, b: (0, 0, pearson(a, b)),
    )
    mutants["shift_wrong_sign"] = not _shift_gate(
        shift_reference,
        first_moving,
        first_plant,
        lambda a, b: (
            first_plant[0],
            first_plant[1],
            pearson(a, b),
        ),
    )

    oracle_ratios = np.asarray(
        [0.8, 0.9, 1.0, 1.1, 1.4, 2.0],
        np.float64,
    )
    bootstrap = bootstrap_log_summaries(
        {"oracle": np.log(oracle_ratios)}
    )["oracle"]
    bootstrap_expected = {
        "point": 1.1419502979318024,
        "ci_low": 0.9121587193141124,
        "ci_high": 1.4932832815948553,
    }
    controls["bootstrap_seed_20260919_oracle"] = all(
        math.isclose(
            float(bootstrap[name]),
            expected,
            rel_tol=1e-13,
            abs_tol=1e-13,
        )
        for name, expected in bootstrap_expected.items()
    )

    verdicts = {
        "sufficient": frozen_verdict(
            {"ci_low": 1.06, "ci_high": 1.20},
            {"ci_low": 1.01, "ci_high": 1.20},
        ),
        "partial": frozen_verdict(
            {"ci_low": 1.06, "ci_high": 1.20},
            {"ci_low": 0.80, "ci_high": 0.99},
        ),
        "null": frozen_verdict(
            {"ci_low": 0.95, "ci_high": 1.05},
            {"ci_low": 0.70, "ci_high": 1.30},
        ),
        "unresolved": frozen_verdict(
            {"ci_low": 1.04, "ci_high": 1.20},
            {"ci_low": 0.99, "ci_high": 1.01},
        ),
    }
    controls["verdict_sufficient"] = (
        verdicts["sufficient"] == "REAL_TRANSFER_SUFFICIENT"
    )
    controls["verdict_partial"] = (
        verdicts["partial"] == "REAL_TRANSFER_PARTIAL"
    )
    controls["verdict_null"] = verdicts["null"] == "NO_REAL_TRANSFER"
    controls["verdict_unresolved"] = verdicts["unresolved"] == "UNRESOLVED"
    controls["verdict_strict_t0"] = frozen_verdict(
        {"ci_low": 1.05, "ci_high": 1.20},
        {"ci_low": 1.01, "ci_high": 1.20},
    ) == "UNRESOLVED"
    controls["verdict_strict_m40_low"] = frozen_verdict(
        {"ci_low": 1.06, "ci_high": 1.20},
        {"ci_low": 1.00, "ci_high": 1.20},
    ) == "UNRESOLVED"
    controls["verdict_strict_m40_high"] = frozen_verdict(
        {"ci_low": 1.06, "ci_high": 1.20},
        {"ci_low": 0.80, "ci_high": 1.00},
    ) == "UNRESOLVED"
    controls["verdict_inclusive_null"] = frozen_verdict(
        {"ci_low": 0.95, "ci_high": 1.05},
        {"ci_low": 1.10, "ci_high": 1.20},
    ) == "NO_REAL_TRANSFER"

    controls["stream_hash_oracle"] = (
        sha256_stream(io.BytesIO(b"V-HEADTOHEAD3"))
        == "48F234FE34275DE6009A8ACE5A135B58EF775B9BE5DCDBC0D5468FCAAC7B7394"
    )
    baseline_manifest = _expected_manifest_copy()
    controls["provenance_baseline"] = not provenance_mismatches(
        EXPECTED_HASHES, baseline_manifest
    )
    for name in EXPECTED_HASHES:
        changed_hashes = dict(EXPECTED_HASHES)
        changed_hashes[name] = "0" * 64
        mutants[f"hash_{name}"] = bool(
            provenance_mismatches(changed_hashes, baseline_manifest)
        )
    changed_digest = copy.deepcopy(baseline_manifest)
    changed_digest["SITE_DIGEST"] = "0" * 64
    mutants["site_digest"] = bool(
        provenance_mismatches(EXPECTED_HASHES, changed_digest)
    )
    changed_site = copy.deepcopy(baseline_manifest)
    changed_site["DETAIL_0"][0][0] += 1
    mutants["site_coordinate"] = bool(
        provenance_mismatches(EXPECTED_HASHES, changed_site)
    )

    green = all(controls.values()) and all(mutants.values())
    return {
        "schema": COMMISSION_SCHEMA,
        "mode": "SYNTHETIC_ONLY",
        "status": "GREEN" if green else "RED",
        "green": green,
        "controls": controls,
        "caught_red_mutants": mutants,
        "control_count": len(controls),
        "caught_mutant_count": sum(mutants.values()),
        "mutant_count": len(mutants),
        "synthetic_readings": {
            "base_q25": base,
            "identity_ratio": identity_ratio,
            "blur_ratio": blur_ratio,
            "physical_improvement_ratio": improvement_ratio,
            "usm_ratio": usm_ratio,
            "tone_ratios": tone_ratios,
            "bootstrap_oracle": bootstrap,
        },
        "verdict_branches": verdicts,
        "unlicensed": UNLICENSED,
        "thread_cap": THREAD_CAP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Independent V-HEADTOHEAD3 USM transfer checker"
    )
    parser.add_argument(
        "--commission",
        action="store_true",
        help="run only the synthetic instrument commission",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.commission:
        if args.output is not None:
            parser.error("--commission does not write an outcome")
        result = commission_result()
        print(
            "SHARPENING_TRANSFER_COMMISSION_JSON="
            + json.dumps(
                result,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return 0 if result["green"] else 2
    try:
        result = outcome()
    except OutcomeStop as exc:
        print(
            "SHARPENING_TRANSFER_CHECK_ERROR="
            + json.dumps(
                {
                    "schema": SCHEMA,
                    "status": "STOPPED",
                    "reason": str(exc),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 2
    encoded = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    if args.output is not None:
        args.output.write_text(
            json.dumps(result, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    print("SHARPENING_TRANSFER_CHECK_JSON=" + encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
