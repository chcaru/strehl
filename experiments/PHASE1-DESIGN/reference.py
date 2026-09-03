#!/usr/bin/env python3
"""Independent LibRaw reference and commissioning harness for phase-1 W1.

This file deliberately imports no strehl package and consumes no Rust merge
output.  The only production artifact it accepts is the text alignment
sidecar.  RAW samples are decoded through rawpy/LibRaw, transformed by a
separately implemented Catmull-Rom pull, and processed by NumPy/SciPy code.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import rawpy
import scipy
from scipy.ndimage import correlate1d, gaussian_filter


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TRANSFORMS = HERE / "transforms"
MANIFEST_PATH = RESULTS / "preregistered-manifest.json"
COMMISSION_PATH = RESULTS / "commissioning.json"
PREREG_PATH = HERE / "PREREGISTRATION.md"
MEASURE_PATH = HERE / "measure.py"

BANDS = 7
SCORE_SIZE = 512
HALO = 256
WORK_SIZE = SCORE_SIZE + 2 * HALO
TILE = 32
FREQ_OUTPUT = (0.10, 0.25)
BOOTSTRAP_SEED = 0x5A17_2026
BOOTSTRAP_REPLICATES = 8192
K_GRID = tuple(round(i * 0.05, 2) for i in range(161))
PHASE_GRID = tuple(i / 8.0 for i in range(8))
CAL_SIZE = 512
CAL_REALISATIONS = 8
VALIDATION_REALISATIONS = 4
NU_ANALYTIC = 13.37469

# Filled after the deterministic synthetic calibration and sealed by the
# preregistration commit.  --commission refuses drift from these values.
FROZEN_NU_EFF = (
    8.5,
    9.0,
    8.0,
    7.5,
    6.5,
    2.5,
    0.5,
)
FROZEN_MANIFEST_SHA256 = "79b74a013e6598c985b6ad7bc969c732cf4189d8467eec3e13313ca23ab13b09"

KERNEL = np.asarray([1, 4, 6, 4, 1], dtype=np.float64) / 16.0


def _pairs(values: Sequence[tuple[int, int]]) -> list[list[int]]:
    return [[int(x), int(y)] for x, y in values]


SW4_DETAIL = _pairs(
    [(x, y) for y in (45, 97, 149, 201) for x in (48, 100, 152, 204, 256, 308, 360, 412)]
)
SW4_FLAT = _pairs(
    [(x, y) for y in (21, 73, 125, 177) for x in (24, 76, 128, 180, 232, 284, 336, 388)]
)
COFFEE_DETAIL = _pairs(
    [
        (448, 256), (352, 128), (224, 192), (224, 288), (416, 256), (192, 256),
        (256, 32), (32, 32), (224, 64), (160, 192), (448, 384), (192, 384),
        (320, 448), (448, 352), (448, 192), (320, 480), (96, 64), (288, 224),
        (384, 320), (288, 96), (352, 256), (96, 320), (352, 0), (192, 64),
        (64, 96), (352, 224), (480, 128), (352, 288), (384, 160), (160, 64),
        (256, 96), (192, 224),
    ]
)
COFFEE_FLAT = _pairs(
    [
        (352, 352), (32, 128), (64, 384), (0, 416), (32, 384), (160, 416),
        (128, 416), (0, 96), (0, 288), (320, 352), (32, 192), (32, 160),
        (0, 352), (32, 352), (32, 320), (0, 384), (384, 32), (0, 320),
        (96, 384), (384, 352), (0, 128), (288, 416), (32, 288), (0, 256),
        (128, 384), (320, 320), (32, 256), (320, 384), (64, 192), (416, 384),
        (288, 288), (352, 320),
    ]
)
DCF113_DETAIL = _pairs(
    [
        (480, 384), (448, 480), (480, 320), (448, 384), (480, 96), (448, 416),
        (448, 448), (480, 256), (416, 448), (448, 352), (480, 416), (0, 224),
        (32, 128), (0, 256), (32, 192), (480, 288), (480, 224), (416, 320),
        (416, 384), (416, 416), (64, 192), (480, 352), (0, 192), (416, 352),
        (480, 192), (32, 0), (480, 448), (448, 64), (416, 288), (96, 160),
        (160, 32), (192, 384),
    ]
)
DCF113_FLAT = _pairs(
    [
        (224, 128), (64, 384), (64, 352), (224, 448), (352, 32), (224, 480),
        (128, 320), (224, 64), (96, 352), (256, 64), (224, 416), (256, 480),
        (352, 0), (352, 64), (128, 352), (96, 384), (320, 32), (416, 192),
        (128, 224), (256, 448), (160, 288), (288, 224), (32, 416), (224, 160),
        (96, 416), (224, 96), (320, 0), (96, 448), (320, 384), (224, 0),
        (256, 128), (256, 96),
    ]
)


CAPTURES = {
    "sw4": {
        "path": Path(r"D:\personal\macro\requests\30-calibration-grid\calibration-grid-1-sw4-cpl"),
        "frames": 55,
        "score_origin": [1500, 916],
        "transform": TRANSFORMS / "sw4.warpmap.txt",
        "detail_tiles": SW4_DETAIL,
        "flat_tiles": SW4_FLAT,
        "align_threads": 8,
    },
    "coffee-bubbles": {
        "path": Path(r"D:\personal\macro\coffee-bubbles"),
        "frames": 19,
        "score_origin": [1450, 700],
        "transform": TRANSFORMS / "coffee-bubbles.warpmap.txt",
        "detail_tiles": COFFEE_DETAIL,
        "flat_tiles": COFFEE_FLAT,
        "align_threads": 4,
    },
    "113MSDCF": {
        "path": Path(r"D:\personal\macro\113MSDCF"),
        "frames": 63,
        "score_origin": [1500, 900],
        "transform": TRANSFORMS / "113MSDCF.warpmap.txt",
        "detail_tiles": DCF113_DETAIL,
        "flat_tiles": DCF113_FLAT,
        "align_threads": 4,
    },
}


@dataclass(frozen=True)
class Similarity:
    a_re: float
    a_im: float
    b_re: float
    b_im: float

    def apply(self, x: np.ndarray, y: np.ndarray, cx: float, cy: float) -> tuple[np.ndarray, np.ndarray]:
        xr = x - cx
        yr = y - cy
        return (
            self.a_re * xr - self.a_im * yr + self.b_re + cx,
            self.a_im * xr + self.a_re * yr + self.b_im + cy,
        )


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def ordered_raws(config: dict) -> list[Path]:
    paths = sorted(config["path"].rglob("*.ARW"), key=lambda p: str(p.relative_to(config["path"])).casefold())
    if len(paths) != config["frames"]:
        raise RuntimeError(f"{config['path']}: expected {config['frames']} ARWs, found {len(paths)}")
    return paths


def _f64_bits(text: str) -> float:
    return struct.unpack(">d", bytes.fromhex(text))[0]


def parse_warpmap(path: Path) -> tuple[dict, list[Similarity]]:
    meta: dict[str, object] = {}
    rows: dict[int, Similarity] = {}
    refused: list[int] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        p = line.split()
        if p[0] == "plane":
            meta["plane"] = [int(v) for v in p[1].split("x")]
        elif p[0] == "frames":
            meta["frames"] = int(p[1])
        elif p[0] == "reference":
            meta["reference"] = int(p[1])
        elif p[0] in {"stack-name", "stack-digest", "strategy", "resampler", "heldout-px", "cycle-floor-px"}:
            meta[p[0]] = p[1]
        elif p[0].isdigit() and p[1] == "placed":
            rows[int(p[0])] = Similarity(*(_f64_bits(v) for v in p[2:6]))
        elif p[0].isdigit() and p[1] == "refused":
            refused.append(int(p[0]))
    if meta.get("resampler") != "catmull-rom":
        raise RuntimeError(f"{path}: expected catmull-rom, found {meta.get('resampler')}")
    n = int(meta.get("frames", -1))
    if refused or sorted(rows) != list(range(n)):
        raise RuntimeError(f"{path}: requires every frame placed, refused={refused}, rows={len(rows)}/{n}")
    return meta, [rows[i] for i in range(n)]


def catmull_weights(fraction: np.ndarray) -> tuple[np.ndarray, ...]:
    f = np.asarray(fraction, dtype=np.float64)
    f2 = f * f
    f3 = f2 * f
    return (
        -0.5 * f3 + f2 - 0.5 * f,
        1.5 * f3 - 2.5 * f2 + 1.0,
        -1.5 * f3 + 2.0 * f2 + 0.5 * f,
        0.5 * f3 - 0.5 * f2,
    )


def gather_crop(
    source: np.ndarray,
    transform: Similarity,
    origin: tuple[int, int],
    shape: tuple[int, int] = (WORK_SIZE, WORK_SIZE),
    sidecar_plane: tuple[int, int] = (3516, 2344),
) -> np.ndarray:
    """Pull one crop using global sidecar coordinates and Catmull-Rom a=-1/2."""
    src = np.asarray(source, dtype=np.float64)
    if src.ndim != 2:
        raise ValueError("gather source must be a 2-D CFA plane")
    height, width = shape
    ox, oy = origin
    cx, cy = sidecar_plane[0] * 0.5, sidecar_plane[1] * 0.5
    out = np.empty((height, width), dtype=np.float32)
    gx = np.arange(ox, ox + width, dtype=np.float64)
    for row0 in range(0, height, 32):
        gy = np.arange(oy + row0, oy + min(row0 + 32, height), dtype=np.float64)
        yy, xx = np.meshgrid(gy, gx, indexing="ij")
        sx, sy = transform.apply(xx, yy, cx, cy)
        x0 = np.floor(sx).astype(np.intp)
        y0 = np.floor(sy).astype(np.intp)
        if x0.min() < 1 or y0.min() < 1 or x0.max() > src.shape[1] - 3 or y0.max() > src.shape[0] - 3:
            raise RuntimeError(
                f"crop {origin}+{shape} leaves LibRaw plane {src.shape}; "
                f"x floors {x0.min()}..{x0.max()}, y {y0.min()}..{y0.max()}"
            )
        wx = catmull_weights(sx - x0)
        wy = catmull_weights(sy - y0)
        acc = np.zeros_like(sx)
        for j in range(4):
            horizontal = np.zeros_like(sx)
            for i in range(4):
                horizontal += src[y0 + j - 1, x0 + i - 1] * wx[i]
            acc += horizontal * wy[j]
        out[row0 : row0 + len(gy)] = acc.astype(np.float32)
    return out


def _cubic_kernel(distance: float) -> float:
    """Independent scalar Keys cubic predicate, not the vector weight formula."""
    x = abs(float(distance))
    if x <= 1.0:
        return 1.5 * x**3 - 2.5 * x**2 + 1.0
    if x < 2.0:
        return -0.5 * x**3 + 2.5 * x**2 - 4.0 * x + 2.0
    return 0.0


def scalar_catmull(source: np.ndarray, x: float, y: float) -> float:
    ix, iy = math.floor(x), math.floor(y)
    total = 0.0
    for sy in range(iy - 1, iy + 3):
        for sx in range(ix - 1, ix + 3):
            total += float(source[sy, sx]) * _cubic_kernel(x - sx) * _cubic_kernel(y - sy)
    return total


def extract_greens(mosaic: np.ndarray, pattern: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = np.asarray(pattern)
    if p.shape != (2, 2) or not np.array_equal(p, np.asarray([[0, 1], [3, 2]])):
        raise RuntimeError(f"W1 requires LibRaw RGGB/RGBG phase [[0,1],[3,2]], got {p.tolist()}")
    a = np.asarray(mosaic)
    return np.array(a[0::2, 1::2], copy=True), np.array(a[1::2, 0::2], copy=True)


def decode_green_planes(path: Path) -> tuple[np.ndarray, np.ndarray, dict]:
    with rawpy.imread(str(path)) as raw:
        visible = np.array(raw.raw_image_visible, dtype=np.float32, copy=True)
        g1, g2 = extract_greens(visible, raw.raw_pattern)
        black = [float(v) for v in raw.black_level_per_channel]
        camera_white = raw.camera_white_level_per_channel
        meta = {
            "visible_shape": list(visible.shape),
            "plane_shape": list(g1.shape),
            "black": black,
            "container_white": float(raw.white_level),
            "camera_white": None if camera_white is None else [float(v) for v in camera_white],
            "iso": float(raw.other.iso_speed),
        }
    if g1.shape != g2.shape or g1.shape[0] != 2344 or g1.shape[1] != 3514:
        raise RuntimeError(f"{path}: unexpected LibRaw green geometry {g1.shape}/{g2.shape}")
    if max(black) - min(black) != 0:
        raise RuntimeError(f"{path}: W1 decoder convention requires equal black levels, got {black}")
    return g1, g2, meta


def prepared_crop(path: Path, transform: Similarity, score_origin: Sequence[int]) -> tuple[np.ndarray, np.ndarray, dict]:
    g1, g2, meta = decode_green_planes(path)
    work_origin = (int(score_origin[0]) - HALO, int(score_origin[1]) - HALO)
    plane = (3516, 2344)
    a = gather_crop(g1, transform, work_origin, sidecar_plane=plane)
    b = gather_crop(g2, transform, work_origin, sidecar_plane=plane)
    # Black subtraction follows interpolation.  Catmull undershoot below black
    # is clipped at physical zero before both policy arms see the same bytes.
    black = float(meta["black"][1])
    a = np.maximum(a - black, 0.0, dtype=np.float32)
    b = np.maximum(b - black, 0.0, dtype=np.float32)
    return a, b, meta


def noise_coefficients(iso: float) -> tuple[float, float]:
    gain = max(float(iso), 100.0) / 436.8
    read_noise_e = 4.20 if iso < 400.0 else 1.2392
    # Variance of (G1+G2)/2 for two equal, independent green channels.
    return gain / 2.0, (read_noise_e * gain) ** 2 / 2.0


def anscombe(signal: np.ndarray, a: float, b: float) -> np.ndarray:
    s = np.maximum(np.asarray(signal, dtype=np.float64), 0.0)
    inside = a * s + 3.0 * a * a / 8.0 + b
    return (2.0 / a * np.sqrt(np.maximum(inside, 0.0))).astype(np.float32)


def anscombe_variance(signal: np.ndarray, a: float, b: float) -> np.ndarray:
    s = np.maximum(np.asarray(signal, dtype=np.float64), 0.0)
    den = a * s + 3.0 * a * a / 8.0 + b
    value = (a * s + b) / den
    if not np.all(np.isfinite(value) & (value > 0)):
        raise RuntimeError("non-finite/non-positive generalized-Anscombe variance")
    return value.astype(np.float32)


def smooth5(array: np.ndarray) -> np.ndarray:
    a = correlate1d(np.asarray(array, dtype=np.float64), KERNEL, axis=1, mode="nearest")
    return correlate1d(a, KERNEL, axis=0, mode="nearest").astype(np.float32)


def reduce5(array: np.ndarray) -> np.ndarray:
    return smooth5(array)[::2, ::2]


def _expand_axis(array: np.ndarray, length: int, axis: int) -> np.ndarray:
    a = np.moveaxis(np.asarray(array, dtype=np.float64), axis, 0)
    n = a.shape[0]
    prev = np.concatenate((a[:1], a[:-1]), axis=0)
    nxt = np.concatenate((a[1:], a[-1:]), axis=0)
    shape = (length,) + a.shape[1:]
    out = np.empty(shape, dtype=np.float64)
    even = out[0::2]
    odd = out[1::2]
    even[...] = (0.125 * prev + 0.75 * a + 0.125 * nxt)[: len(even)]
    if len(odd):
        odd[...] = (0.5 * (a + nxt))[: len(odd)]
    return np.moveaxis(out, 0, axis)


def expand5(array: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    horizontal = _expand_axis(array, shape[1], axis=1)
    return _expand_axis(horizontal, shape[0], axis=0).astype(np.float32)


def gaussian_pyramid(image: np.ndarray, bands: int = BANDS) -> list[np.ndarray]:
    levels = [np.asarray(image, dtype=np.float32)]
    for _ in range(bands):
        levels.append(reduce5(levels[-1]))
    return levels


def laplacian_pyramid(image: np.ndarray, bands: int = BANDS) -> list[np.ndarray]:
    gauss = gaussian_pyramid(image, bands)
    return [(gauss[k] - expand5(gauss[k + 1], gauss[k].shape)).astype(np.float32) for k in range(bands)] + [
        gauss[-1]
    ]


def collapse_pyramid(levels: Sequence[np.ndarray]) -> np.ndarray:
    out = np.array(levels[-1], dtype=np.float32, copy=True)
    for band in range(len(levels) - 2, -1, -1):
        out = expand5(out, levels[band].shape) + levels[band]
    return out.astype(np.float32)


def _translated_white(rng: np.random.Generator, size: int, fx: float, fy: float) -> np.ndarray:
    source = rng.standard_normal((size + 3, size + 3), dtype=np.float64)
    wx = catmull_weights(np.asarray(fx))
    wy = catmull_weights(np.asarray(fy))
    out = np.zeros((size, size), dtype=np.float64)
    for j in range(4):
        row = np.zeros_like(out)
        for i in range(4):
            row += source[j : j + size, i : i + size] * float(wx[i])
        out += row * float(wy[j])
    return out.astype(np.float32)


def _interior_values(array: np.ndarray, max_values: int = 24000) -> np.ndarray:
    margin = max(1, min(8, min(array.shape) // 8))
    core = np.asarray(array, dtype=np.float64)[margin:-margin, margin:-margin]
    flat = core.ravel()
    step = max(1, math.ceil(len(flat) / max_values))
    return flat[::step][:max_values]


def calibrate_phase_model(
    realisations: int = CAL_REALISATIONS,
    seed: int = 0xB37A_1101,
) -> dict:
    beta = np.zeros((len(PHASE_GRID), len(PHASE_GRID), BANDS), dtype=np.float64)
    phase_q95 = np.zeros_like(beta)
    phase_nu_moment = np.zeros_like(beta)
    for iy, fy in enumerate(PHASE_GRID):
        for ix, fx in enumerate(PHASE_GRID):
            sums = np.zeros(BANDS, dtype=np.float64)
            sums2_e = np.zeros(BANDS, dtype=np.float64)
            counts = np.zeros(BANDS, dtype=np.int64)
            sampled: list[list[np.ndarray]] = [[] for _ in range(BANDS)]
            for r in range(realisations):
                rng = np.random.default_rng(seed + 100000 * iy + 1000 * ix + r)
                field = _translated_white(rng, CAL_SIZE, fx, fy)
                bands = laplacian_pyramid(field, BANDS)
                for b in range(BANDS):
                    lv = _interior_values(bands[b], max_values=24000)
                    e = _interior_values(smooth5(bands[b] * bands[b]), max_values=24000)
                    sums[b] += float(np.sum(lv * lv))
                    counts[b] += len(lv)
                    sampled[b].append(e)
            for b in range(BANDS):
                floor = sums[b] / counts[b]
                values = np.concatenate(sampled[b])
                beta[iy, ix, b] = floor
                sums2_e[b] = float(np.var(values, ddof=1))
                phase_nu_moment[iy, ix, b] = 2.0 * floor * floor / sums2_e[b]
                phase_q95[iy, ix, b] = float(np.quantile(np.abs(values / floor - 1.0), 0.95))
    worst_q95 = phase_q95.max(axis=(0, 1))
    # Largest nu whose symmetric 1.96-sigma interval covers at least the
    # measured 95th absolute deviation, with a 2% preregistered safety margin.
    nu_from_coverage = 0.98 * 2.0 * (1.96 / worst_q95) ** 2
    nu = np.minimum(nu_from_coverage, phase_nu_moment.min(axis=(0, 1)))
    return {
        "phase_grid": list(PHASE_GRID),
        "realisations": realisations,
        "size": CAL_SIZE,
        "seed": seed,
        "beta": beta.tolist(),
        "phase_q95": phase_q95.tolist(),
        "phase_nu_moment": phase_nu_moment.tolist(),
        "nu_eff": nu.tolist(),
    }


def validate_phase_coverage(
    beta_table: np.ndarray,
    nu: Sequence[float],
    seed: int = 0xE771_9000,
) -> dict:
    covered = np.zeros((8, 8, BANDS), dtype=np.int64)
    total = np.zeros_like(covered)
    for iy, fy in enumerate(PHASE_GRID):
        for ix, fx in enumerate(PHASE_GRID):
            for r in range(VALIDATION_REALISATIONS):
                rng = np.random.default_rng(seed + 100000 * iy + 1000 * ix + r)
                bands = laplacian_pyramid(_translated_white(rng, CAL_SIZE, fx, fy), BANDS)
                for b in range(BANDS):
                    e = _interior_values(smooth5(bands[b] * bands[b]), max_values=30000)
                    f = float(beta_table[iy, ix, b])
                    half = 1.96 * math.sqrt(2.0 * f * f / float(nu[b]))
                    covered[iy, ix, b] += int(np.count_nonzero(np.abs(e - f) <= half))
                    total[iy, ix, b] += len(e)
    coverage = covered / total
    return {
        "per_phase_band": coverage.tolist(),
        "worst_by_band": coverage.min(axis=(0, 1)).tolist(),
        "median_by_band": np.median(coverage, axis=(0, 1)).tolist(),
        "overall_by_band": (covered.sum(axis=(0, 1)) / total.sum(axis=(0, 1))).tolist(),
        "worst": float(coverage.min()),
        "seed": seed,
    }


def beta_for_transform(
    transform: Similarity,
    score_origin: Sequence[int],
    beta_table: np.ndarray,
) -> np.ndarray:
    """Frame/warp/ROI-specific gain from the commissioned periodic phase table."""
    ox, oy = int(score_origin[0]) - HALO, int(score_origin[1]) - HALO
    coords = np.arange(0, WORK_SIZE, 8, dtype=np.float64)
    yy, xx = np.meshgrid(oy + coords, ox + coords, indexing="ij")
    sx, sy = transform.apply(xx, yy, 3516 * 0.5, 2344 * 0.5)
    ux = np.mod(sx, 1.0) * 8.0
    uy = np.mod(sy, 1.0) * 8.0
    x0 = np.floor(ux).astype(np.intp) % 8
    y0 = np.floor(uy).astype(np.intp) % 8
    x1 = (x0 + 1) % 8
    y1 = (y0 + 1) % 8
    tx = ux - np.floor(ux)
    ty = uy - np.floor(uy)
    values = []
    for b in range(BANDS):
        table = beta_table[:, :, b]
        interp = (
            (1 - tx) * (1 - ty) * table[y0, x0]
            + tx * (1 - ty) * table[y0, x1]
            + (1 - tx) * ty * table[y1, x0]
            + tx * ty * table[y1, x1]
        )
        values.append(float(np.mean(interp)))
    out = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(out) & (out > 0)):
        raise RuntimeError("invalid frame-specific beta")
    return out


def candidate_terms(energy: np.ndarray, floor: np.ndarray, nu: float) -> tuple[np.ndarray, np.ndarray]:
    q = np.maximum(np.asarray(energy, dtype=np.float64) - np.asarray(floor, dtype=np.float64), 0.0)
    sigma2 = (2.0 * floor * floor + 4.0 * floor * q) / float(nu)
    return q.astype(np.float32), sigma2.astype(np.float32)


def kish(weights: np.ndarray, axis: int = 0) -> np.ndarray:
    w = np.asarray(weights, dtype=np.float64)
    sw = np.sum(w, axis=axis)
    sw2 = np.sum(w * w, axis=axis)
    return sw * sw / sw2


def frequency_mask(size: int, band: tuple[float, float] = FREQ_OUTPUT) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fy = np.fft.fftfreq(size)
    fx = np.fft.rfftfreq(size)
    yy, xx = np.meshgrid(fy, fx, indexing="ij")
    output_frequency = np.hypot(xx, yy) / 2.0
    mask = (output_frequency >= band[0]) & (output_frequency <= band[1] + 1e-15)
    if output_frequency[mask].max(initial=0.0) > 0.25 + 1e-12:
        raise RuntimeError("UNLICENSED_GT_0.25")
    return mask, xx, yy


def detail_tile_power(g1: np.ndarray, g2: np.ndarray) -> float:
    n = g1.shape[0]
    if g1.shape != (n, n) or g2.shape != (n, n):
        raise ValueError("detail metric requires equal square tiles")
    win = np.outer(np.hanning(n), np.hanning(n))
    a = np.fft.rfft2((np.asarray(g1, dtype=np.float64) - np.mean(g1)) * win)
    b = np.fft.rfft2((np.asarray(g2, dtype=np.float64) - np.mean(g2)) * win)
    mask, fx, fy = frequency_mask(n)
    # G1 is at (+0.5,0) and G2 at (0,+0.5) in plane-pixel units.
    phase = np.exp(-1j * np.pi * (fx - fy))
    return float(np.real(a * np.conj(b) * phase)[mask].sum())


def flat_tile_power(luma: np.ndarray) -> float:
    n = luma.shape[0]
    win = np.outer(np.hanning(n), np.hanning(n))
    spectrum = np.fft.rfft2((np.asarray(luma, dtype=np.float64) - np.mean(luma)) * win)
    mask, _, _ = frequency_mask(n)
    return float((np.abs(spectrum) ** 2)[mask].sum())


def bootstrap_ratio(
    candidate: Sequence[float],
    legacy: Sequence[float],
    kind: str,
    seed: int = BOOTSTRAP_SEED,
    replicates: int = BOOTSTRAP_REPLICATES,
) -> dict:
    c = np.asarray(candidate, dtype=np.float64)
    l = np.asarray(legacy, dtype=np.float64)
    if c.shape != l.shape or c.ndim != 1 or len(c) < 8:
        raise ValueError("bootstrap requires paired one-dimensional tile readings")
    rng = np.random.default_rng(seed)
    picks = rng.integers(0, len(c), size=(replicates, len(c)))
    cs = c[picks].sum(axis=1)
    ls = l[picks].sum(axis=1)
    if kind == "detail":
        good = (cs > 0) & (ls > 0)
        if np.count_nonzero(good) != replicates:
            raise RuntimeError("detail cross-power was non-positive in a bootstrap replicate")
        samples = np.sqrt(cs / ls)
        point = math.sqrt(float(c.sum() / l.sum()))
    elif kind == "flat":
        if np.any(ls <= 0):
            raise RuntimeError("flat legacy power was non-positive")
        samples = cs / ls
        point = float(c.sum() / l.sum())
    else:
        raise ValueError(kind)
    lo, hi = np.quantile(samples, [0.025, 0.975])
    return {
        "point": point,
        "lower95": float(lo),
        "upper95": float(hi),
        "candidate_raw": c.tolist(),
        "legacy_raw": l.tolist(),
        "seed": int(seed),
        "replicates": int(replicates),
    }


def metric_values(g1: np.ndarray, g2: np.ndarray, tiles: Sequence[Sequence[int]], kind: str) -> list[float]:
    values = []
    for x, y in tiles:
        a = g1[y : y + TILE, x : x + TILE]
        b = g2[y : y + TILE, x : x + TILE]
        if a.shape != (TILE, TILE) or b.shape != (TILE, TILE):
            raise RuntimeError(f"tile {(x, y)} leaves score crop")
        if kind == "detail":
            values.append(detail_tile_power(a, b))
        elif kind == "flat":
            values.append(flat_tile_power(0.5 * (a + b)))
        else:
            raise ValueError(kind)
    return values


def _row(identifier: str, null_name: str, null_reading: object, null_green: bool, plant_name: str, plant_reading: object, plant_red: bool) -> dict:
    return {
        "id": identifier,
        "null": {"name": null_name, "reading": null_reading, "state": "GREEN" if null_green else "RED"},
        "plant": {"name": plant_name, "reading": plant_reading, "state": "RED" if plant_red else "GREEN"},
        "pass": bool(null_green and plant_red),
    }


def run_commissioning() -> dict:
    calibration = calibrate_phase_model()
    measured_nu = np.asarray(calibration["nu_eff"], dtype=np.float64)
    frozen = np.asarray(FROZEN_NU_EFF, dtype=np.float64)
    if np.any(frozen <= 0):
        raise RuntimeError("FROZEN_NU_EFF is not sealed; run --calibrate-nu, preregister, then patch constants")
    conservatism = frozen / measured_nu
    beta = np.asarray(calibration["beta"], dtype=np.float64)
    coverage = validate_phase_coverage(beta, frozen)
    analytic_coverage = validate_phase_coverage(beta, [NU_ANALYTIC] * BANDS)

    rows: list[dict] = []

    # Hand predicates for F/q/sigma/admission/tie/fallback/Kish.
    energy = np.asarray([10.0, 8.0, 4.0])
    floor = np.asarray([2.0, 4.0, 4.0])
    q, sigma2 = candidate_terms(energy, floor, 2.0)
    expected_q = np.asarray([8.0, 4.0, 0.0])
    expected_sigma = np.asarray([36.0, 48.0, 16.0])
    tiny_error = float(max(np.max(np.abs(q - expected_q)), np.max(np.abs(sigma2 - expected_sigma))))
    planted_sigma = (2 * floor * floor + 2 * floor * expected_q) / 2.0
    plant_error = float(np.max(np.abs(planted_sigma - expected_sigma)))
    rows.append(_row("tiny-F-q-sigma", "hand equations", tiny_error, tiny_error == 0.0, "missing factor 4Fq", plant_error, plant_error > 0))

    tied = np.asarray([7.0, 7.0, 6.0])
    winner = int(np.flatnonzero(np.isfinite(tied) & (tied == np.nanmax(tied)))[0])
    planted_winner = int(np.flatnonzero(tied == tied.max())[-1])
    rows.append(_row("stable-winner", "lower ordinal tie", winner, winner == 0, "upper ordinal tie", planted_winner, planted_winner != 0))

    weights = np.asarray([1.0, 0.5])
    neff = float(kish(weights))
    count_plant = float(np.count_nonzero(weights))
    rows.append(_row("kish-width", "weighted Kish", neff, abs(neff - 1.8) < 1e-14, "admission count", count_plant, abs(count_plant - 1.8) > 0.1))

    mean_values = np.asarray([2.0, 5.0, 8.0])
    fallback = float(np.average(mean_values, weights=np.ones(3)))
    inverse_floor_plant = float(np.average(mean_values, weights=[1.0, 0.5, 0.25]))
    rows.append(_row("below-floor-unit-mean", "unit fallback", fallback, fallback == 5.0, "inverse-F below floor", inverse_floor_plant, abs(inverse_floor_plant - 5.0) > 0.5))

    ew, ei, sw, si = 10.0, 8.0, 0.5, 0.5
    admissions = [bool(ew - ei <= k * math.sqrt(sw + si)) for k in (0, 1, 2, 3)]
    reversed_plant = [bool(ei - ew >= k * math.sqrt(sw + si)) for k in (0, 1, 2, 3)]
    monotone = all((not admissions[i]) or admissions[i + 1] for i in range(3)) and admissions == [False, False, True, True]
    plant_monotone = reversed_plant == [False, False, True, True]
    rows.append(_row("admission-boundary", "known k*=2 ladder", admissions, monotone, "reversed inequality", reversed_plant, not plant_monotone))

    ordinals = np.asarray([2, 0, 1])
    vals = np.asarray([3.0, 3.0, 2.0])
    tied_ordinal = int(ordinals[np.lexsort((ordinals, -vals))[0]])
    first_encountered = int(ordinals[np.argmax(vals)])
    sums = [float(np.sum(np.asarray(p, dtype=np.float64))) for p in ([1e-4, 2.0, -1e-4], [-1e-4, 1e-4, 2.0])]
    order_error = abs(sums[0] - sums[1])
    rows.append(
        _row(
            "frame-order-and-ties",
            "ordinal carried through permutation",
            {"winner": tied_ordinal, "sum_error": order_error},
            tied_ordinal == 0 and order_error < 1e-12,
            "encounter-order tie",
            first_encountered,
            first_encountered != 0,
        )
    )

    # Generalized-Anscombe gain invariance and its wrong-b transform plant.
    s = np.geomspace(0.01, 14000.0, 257)
    a0, b0, c = 0.73, 1.91, 1.37
    base = anscombe(s, a0, b0).astype(np.float64)
    scaled = anscombe(c * s, c * a0, c * c * b0).astype(np.float64)
    wrong = anscombe(c * s, c * a0, b0).astype(np.float64)
    vst_error = float(np.max(np.abs(base - scaled)))
    wrong_error = float(np.max(np.abs(base - wrong)))
    rows.append(_row("vst-photometric-invariance", "consistent a,b scaling", vst_error, vst_error <= 2e-5, "unscaled b", wrong_error, wrong_error > 2e-5))

    # Independent vector gather checked by a linear analytic predicate and a
    # scalar Keys-kernel implementation.
    yy, xx = np.mgrid[0:32, 0:32]
    ramp = (3.0 * xx + 5.0 * yy + 11.0).astype(np.float32)
    t = Similarity(1.0, 0.0, 0.25, 0.40)
    got = gather_crop(ramp, t, (8, 8), (8, 8), (32, 32)).astype(np.float64)
    ey, ex = np.mgrid[8:16, 8:16]
    expected = 3.0 * (ex + 0.25) + 5.0 * (ey + 0.40) + 11.0
    gather_error = float(np.max(np.abs(got - expected)))
    scalar_read = scalar_catmull(ramp, 11.25, 12.40)
    vector_read = float(got[4, 3])
    inverse = gather_crop(ramp, Similarity(1.0, 0.0, -0.25, -0.40), (8, 8), (8, 8), (32, 32))
    inverse_error = float(np.max(np.abs(inverse - expected)))
    rows.append(
        _row(
            "independent-crop-gather",
            "analytic ramp + scalar Keys cubic",
            {"analytic_max_error": gather_error, "scalar_vector_error": abs(scalar_read - vector_read)},
            gather_error < 2e-5 and abs(scalar_read - vector_read) < 2e-5,
            "inverted placement",
            inverse_error,
            inverse_error > 1.0,
        )
    )

    mosaic = np.arange(64, dtype=np.float32).reshape(8, 8)
    eg1, eg2 = extract_greens(mosaic, np.asarray([[0, 1], [3, 2]]))
    decode_ok = np.array_equal(eg1, mosaic[0::2, 1::2]) and np.array_equal(eg2, mosaic[1::2, 0::2])
    blue_plant = mosaic[1::2, 1::2]
    rows.append(_row("cfa-green-extraction", "RGGB two-green phases", decode_ok, decode_ok, "G2 replaced by blue", float(np.max(np.abs(blue_plant - eg2))), not np.array_equal(blue_plant, eg2)))

    constant = np.full((256, 256), 1234.5, dtype=np.float32)
    constant_error = max(float(np.max(np.abs(x))) for x in laplacian_pyramid(constant, BANDS)[:-1])
    edge_plant = constant.copy()
    edge_plant[:, 128:] += 20
    edge_read = float(np.max(np.abs(laplacian_pyramid(edge_plant, BANDS)[0])))
    rows.append(_row("constant-field-pyramid", "constant has zero bands", constant_error, constant_error < 1e-5, "planted step", edge_read, edge_read > 1.0))

    rows.append(
        _row(
            "correlated-nu-coverage",
            "held-out phase/null seeds",
            {
                "worst": coverage["worst"],
                "overall": coverage["overall_by_band"],
                "frozen_over_calibrated": conservatism.tolist(),
            },
            coverage["worst"] >= 0.93
            and min(coverage["overall_by_band"]) >= 0.94
            and max(coverage["overall_by_band"]) <= 0.997
            and np.all((conservatism >= 0.40) & (conservatism <= 1.0)),
            "analytic independent-sample nu",
            {"worst": analytic_coverage["worst"], "nu": NU_ANALYTIC},
            analytic_coverage["worst"] < 0.93,
        )
    )

    # Poisson-Gaussian null is not part of the Gaussian phase fit.
    pg_cover = []
    for iso in (100.0, 500.0, 1000.0):
        a_eff, b_eff = noise_coefficients(iso)
        gain = a_eff * 2.0
        rn_dn = math.sqrt(b_eff * 2.0)
        hits = total = 0
        for r in range(24):
            rng = np.random.default_rng(0xA117 + int(iso) * 100 + r)
            signal_dn = 1000.0
            electrons = signal_dn / gain
            g1 = rng.poisson(electrons, size=(128, 128)) * gain + rng.normal(0, rn_dn, (128, 128))
            g2 = rng.poisson(electrons, size=(128, 128)) * gain + rng.normal(0, rn_dn, (128, 128))
            luma = 0.5 * (g1 + g2)
            transformed = anscombe(luma, a_eff, b_eff)
            lv = laplacian_pyramid(transformed, 1)[0]
            e = _interior_values(smooth5(lv * lv), max_values=12000)
            v = float(np.mean(anscombe_variance(luma, a_eff, b_eff)))
            f = beta[0, 0, 0] * v
            half = 1.96 * math.sqrt(2.0 * f * f / frozen[0])
            hits += int(np.count_nonzero(np.abs(e - f) <= half))
            total += len(e)
        pg_cover.append(hits / total)
    pg_plant = float(min(pg_cover) - 0.20)
    rows.append(_row("poisson-gaussian-null", "unfitted PG seeds/ISOs", pg_cover, min(pg_cover) >= 0.90, "20-point undercoverage plant", pg_plant, pg_plant < 0.90))

    # Metric controls: 32 independent tiles, with a noise null not used by the
    # phase calibration.  Every detail reading is <=0.25 cyc/output-pixel.
    detail_legacy_1: list[float] = []
    detail_legacy_2: list[float] = []
    detail_blur_1: list[float] = []
    detail_blur_2: list[float] = []
    flat_legacy: list[float] = []
    flat_quiet: list[float] = []
    flat_noisy: list[float] = []
    for i in range(32):
        rng = np.random.default_rng(0xD37A + i)
        latent = gaussian_filter(rng.standard_normal((TILE + 4, TILE + 4)), 0.65)[2:-2, 2:-2]
        n1 = rng.normal(0, 0.08, (TILE, TILE))
        n2 = rng.normal(0, 0.08, (TILE, TILE))
        g1 = latent + n1
        g2 = latent + n2
        detail_legacy_1.append(detail_tile_power(g1, g2))
        detail_legacy_2.append(detail_tile_power(g1, g2))
        detail_blur_1.append(detail_tile_power(gaussian_filter(g1, 1.2), gaussian_filter(g2, 1.2)))
        detail_blur_2.append(detail_tile_power(g1, g2))
        noise = rng.normal(0, 1, (TILE, TILE))
        p = flat_tile_power(noise)
        flat_legacy.append(p)
        flat_quiet.append(flat_tile_power(math.sqrt(0.70) * noise))
        flat_noisy.append(flat_tile_power(math.sqrt(1.20) * noise))
    detail_null = bootstrap_ratio(detail_legacy_1, detail_legacy_2, "detail")
    detail_plant = bootstrap_ratio(detail_blur_1, detail_blur_2, "detail")
    rows.append(
        _row(
            "detail-cross-power-metric",
            "identity with independent channel noise",
            detail_null,
            detail_null["lower95"] >= 0.95,
            "Gaussian blur",
            detail_plant,
            detail_plant["lower95"] < 0.95,
        )
    )
    flat_null = bootstrap_ratio(flat_quiet, flat_legacy, "flat")
    flat_plant = bootstrap_ratio(flat_noisy, flat_legacy, "flat")
    rows.append(
        _row(
            "flat-power-metric",
            "known 30% power reduction",
            flat_null,
            flat_null["upper95"] <= 0.90,
            "known 20% power inflation",
            flat_plant,
            flat_plant["upper95"] > 0.90,
        )
    )

    scripts = {}
    for path in (Path(__file__), MEASURE_PATH, PREREG_PATH, MANIFEST_PATH):
        if not path.exists():
            raise RuntimeError(f"commissioning requires sealed artifact {path}")
        scripts[path.relative_to(HERE).as_posix()] = sha256(path)
    manifest_key = MANIFEST_PATH.relative_to(HERE).as_posix()
    if not FROZEN_MANIFEST_SHA256 or scripts[manifest_key] != FROZEN_MANIFEST_SHA256:
        raise RuntimeError(
            f"manifest hash is not sealed/matched: got {scripts[manifest_key]}, "
            f"expected {FROZEN_MANIFEST_SHA256 or '<unset>'}"
        )
    transforms = {name: sha256(Path(cfg["transform"])) for name, cfg in CAPTURES.items()}
    payload = {
        "schema": 1,
        "status": "PASS" if all(r["pass"] for r in rows) else "FAIL",
        "rows": rows,
        "phase_calibration": calibration,
        "phase_validation": coverage,
        "analytic_nu_validation": analytic_coverage,
        "frozen_nu_eff": list(FROZEN_NU_EFF),
        "hashes": scripts,
        "transforms": transforms,
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "rawpy": rawpy.__version__,
            "libraw": list(rawpy.libraw_version),
        },
    }
    write_json(COMMISSION_PATH, payload)
    for row in rows:
        print(f"{row['id']}: null={row['null']['state']} plant={row['plant']['state']}")
    print(f"commissioning: {payload['status']} -> {COMMISSION_PATH}")
    if payload["status"] != "PASS":
        failed = [r["id"] for r in rows if not r["pass"]]
        raise RuntimeError(f"commissioning failed: {failed}")
    return payload


def build_manifest() -> dict:
    exe = HERE.parents[1] / "target" / "release" / ("strehl.exe" if os.name == "nt" else "strehl")
    if not exe.exists():
        raise RuntimeError(f"missing alignment executable {exe}")
    version = subprocess.run([str(exe), "--version"], check=True, capture_output=True, text=True).stdout.strip()
    captures = {}
    for name, config in CAPTURES.items():
        meta, warps = parse_warpmap(Path(config["transform"]))
        raws = ordered_raws(config)
        entries = []
        for index, path in enumerate(raws):
            entries.append(
                {
                    "index": index,
                    "relative": str(path.relative_to(config["path"])).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
        captures[name] = {
            "root": str(config["path"]),
            "frames": len(raws),
            "raws": entries,
            "score_crop_xywh_plane": [*config["score_origin"], SCORE_SIZE, SCORE_SIZE],
            "work_crop_xywh_plane": [
                config["score_origin"][0] - HALO,
                config["score_origin"][1] - HALO,
                WORK_SIZE,
                WORK_SIZE,
            ],
            "detail_tiles_xy": config["detail_tiles"],
            "flat_tiles_xy": config["flat_tiles"],
            "transform": {
                "path": str(Path(config["transform"]).relative_to(HERE)).replace("\\", "/"),
                "sha256": sha256(Path(config["transform"])),
                "metadata": meta,
                "placed": len(warps),
                "argv": [
                    str(exe),
                    "align",
                    str(config["path"]),
                    "--out",
                    str(config["transform"]),
                    "--threads",
                    str(config["align_threads"]),
                    "--resampler",
                    "catmull-rom",
                ],
            },
        }
    payload = {
        "schema": 1,
        "created_for": "phase-1 W1 preregistration; no candidate outcomes inspected",
        "alignment_binary": {"path": str(exe), "sha256": sha256(exe), "version": version},
        "decoder": {
            "binding": f"rawpy {rawpy.__version__}",
            "libraw": ".".join(str(v) for v in rawpy.libraw_version),
            "visible_geometry": [7028, 4688],
            "reference_plane_geometry": [3514, 2344],
            "sidecar_plane_geometry": [3516, 2344],
            "black": "per-channel LibRaw metadata; equal 512 DN required; subtract after float gather; clamp below black to 0",
            "white": "camera_white_level_per_channel=15360 DN recorded; container white=16383 is not substituted",
            "linearization": "raw_image_visible integer sensor codes; no demosaic, gamma, WB, auto-bright, or Rust decode",
            "photometric_gain": "unity in W1; B3/W4 law is unresolved and explicitly outside this admission-only pilot",
        },
        "analysis": {
            "bands": BANDS,
            "score_size": SCORE_SIZE,
            "halo": HALO,
            "tile": TILE,
            "frequency_output_cycles_per_pixel": list(FREQ_OUTPUT),
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES,
            "k_grid": list(K_GRID),
            "phase_grid": list(PHASE_GRID),
            "frozen_nu_eff": list(FROZEN_NU_EFF),
        },
        "captures": captures,
    }
    write_json(MANIFEST_PATH, payload)
    print(f"{MANIFEST_PATH}: sha256={sha256(MANIFEST_PATH)}")
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--calibrate-nu", action="store_true", help="print deterministic synthetic values before sealing")
    group.add_argument("--write-manifest", action="store_true", help="hash and write preregistered pilot inputs")
    group.add_argument("--commission", action="store_true", help="run all commissioned controls and write artifact")
    args = parser.parse_args(argv)
    try:
        if args.calibrate_nu:
            result = calibrate_phase_model()
            print(json.dumps({"nu_eff": result["nu_eff"]}, indent=2))
        elif args.write_manifest:
            build_manifest()
        else:
            run_commissioning()
        return 0
    except Exception as exc:
        print(f"reference.py: ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
