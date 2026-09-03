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
HALO = 512
WORK_SIZE = SCORE_SIZE + 2 * HALO
TILE = 32
FREQ_OUTPUT = (0.10, 0.25)
BOOTSTRAP_SEED = 0x5A17_2026
BOOTSTRAP_REPLICATES = 8192
K_GRID = tuple(round(i * 0.05, 2) for i in range(161))
AFFINE_CAL_SIZE = 768
AFFINE_CAL_MARGIN = (AFFINE_CAL_SIZE - SCORE_SIZE) // 2
AFFINE_CAL_SEED = 0xB37A_1101
AFFINE_VALIDATION_SEED = 0xE771_9000
NU_ANALYTIC = 13.37469
SCHEMA = 2
EPOCH = "w1-fe111781"
DESIGN_SHA256 = "fe111781488ce950372fd17e45ab1d402dcc0e34"

# Filled after the deterministic synthetic calibration and sealed by the
# preregistration commit.  --commission refuses drift from these values.
FROZEN_NU_EFF = (
    8.0,
    10.0,
    9.5,
    9.0,
    9.0,
    9.0,
    7.5,
)
FROZEN_MANIFEST_SHA256 = "2a5f7f64942ec6044d59a5bfd561d3849522d3688cf0691256adb113ba97cc18"

KERNEL = np.asarray([1, 4, 6, 4, 1], dtype=np.float64) / 16.0


def _pairs(values: Sequence[tuple[int, int]]) -> list[list[int]]:
    return [[int(x), int(y)] for x, y in values]


FLAT_DETAIL = _pairs(
    [
        (32, 352), (160, 416), (320, 288), (288, 288), (224, 256), (0, 352),
        (480, 128), (64, 448), (288, 416), (448, 256), (64, 320), (320, 256),
        (480, 256), (416, 320), (192, 256), (288, 320), (64, 352), (64, 256),
        (160, 256), (480, 352), (352, 352), (32, 480), (416, 128), (416, 480),
        (320, 192), (256, 288), (416, 288), (416, 160), (0, 384), (288, 192),
        (320, 352), (288, 256),
    ]
)
FLAT_FLAT = _pairs(
    [
        (0, 32), (160, 0), (0, 0), (192, 0), (224, 0), (96, 32), (64, 0),
        (64, 32), (256, 0), (32, 0), (160, 32), (128, 0), (320, 32), (160, 64),
        (0, 64), (352, 96), (416, 32), (448, 32), (96, 0), (128, 32), (128, 64),
        (448, 0), (96, 64), (320, 0), (384, 448), (32, 96), (384, 0), (288, 64),
        (480, 32), (64, 96), (64, 64), (64, 128),
    ]
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
    "flat-on-ruler": {
        "path": Path(r"D:\personal\macro\flat-on-ruler-cpl"),
        "frames": 79,
        "score_origin": [1500, 900],
        "transform": TRANSFORMS / "flat-on-ruler.warpmap.txt",
        "detail_tiles": FLAT_DETAIL,
        "flat_tiles": FLAT_FLAT,
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

CAPTURE_ORDER = ("flat-on-ruler", "coffee-bubbles", "113MSDCF")
EXPECTED_ROOTS = (
    Path(r"D:\personal\macro\flat-on-ruler-cpl"),
    Path(r"D:\personal\macro\coffee-bubbles"),
    Path(r"D:\personal\macro\113MSDCF"),
)
if tuple(CAPTURES) != CAPTURE_ORDER or tuple(c["path"] for c in CAPTURES.values()) != EXPECTED_ROOTS:
    raise RuntimeError("W1 capture ledger drifted from the fe111781 development-only allowlist")


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
    root = Path(config["path"])
    resolved = root.resolve()
    allowed = {p.resolve() for p in EXPECTED_ROOTS}
    if resolved not in allowed or "30-calibration-grid" in str(resolved).casefold():
        raise RuntimeError(f"refusing non-development W1 root {resolved}")
    paths = sorted(root.rglob("*.ARW"), key=lambda p: str(p.relative_to(root)).casefold())
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


def extract_cfa_planes(mosaic: np.ndarray, pattern: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Copy the four RGGB phase planes in canonical R,G1,G2,B order."""
    p = np.asarray(pattern)
    if p.shape != (2, 2) or not np.array_equal(p, np.asarray([[0, 1], [3, 2]])):
        raise RuntimeError(f"W1 requires LibRaw RGGB/RGBG phase [[0,1],[3,2]], got {p.tolist()}")
    a = np.asarray(mosaic)
    return (
        np.array(a[0::2, 0::2], copy=True),
        np.array(a[0::2, 1::2], copy=True),
        np.array(a[1::2, 0::2], copy=True),
        np.array(a[1::2, 1::2], copy=True),
    )


def decode_cfa_planes(path: Path) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], dict]:
    with rawpy.imread(str(path)) as raw:
        visible = np.array(raw.raw_image_visible, dtype=np.float32, copy=True)
        planes = extract_cfa_planes(visible, raw.raw_pattern)
        black = [float(v) for v in raw.black_level_per_channel]
        camera_white = raw.camera_white_level_per_channel
        meta = {
            "visible_shape": list(visible.shape),
            "plane_shape": list(planes[0].shape),
            "black": black,
            "container_white": float(raw.white_level),
            "camera_white": None if camera_white is None else [float(v) for v in camera_white],
            "iso": float(raw.other.iso_speed),
        }
    if len({plane.shape for plane in planes}) != 1 or planes[0].shape != (2344, 3514):
        raise RuntimeError(f"{path}: unexpected LibRaw CFA-plane geometry {[p.shape for p in planes]}")
    if max(black) - min(black) != 0:
        raise RuntimeError(f"{path}: W1 decoder convention requires equal black levels, got {black}")
    return planes, meta


def prepared_crop(
    path: Path,
    transform: Similarity,
    score_origin: Sequence[int],
    sidecar_plane: Sequence[int],
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray], dict]:
    planes, meta = decode_cfa_planes(path)
    work_origin = (int(score_origin[0]) - HALO, int(score_origin[1]) - HALO)
    # Black subtraction follows interpolation.  Catmull undershoot below black
    # is clipped at physical zero before both policy arms see the same bytes.
    phase_to_black = (0, 1, 3, 2)
    aligned = []
    for source, black_index in zip(planes, phase_to_black, strict=True):
        gathered = gather_crop(
            source,
            transform,
            work_origin,
            sidecar_plane=(int(sidecar_plane[0]), int(sidecar_plane[1])),
        )
        aligned.append(np.maximum(gathered - float(meta["black"][black_index]), 0.0, dtype=np.float32))
    return tuple(aligned), meta


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


def affine_white(
    transform: Similarity,
    origin: Sequence[int],
    sidecar_plane: Sequence[int],
    size: int,
    seed: int,
) -> np.ndarray:
    """Pull deterministic unit white noise through one actual affine lattice.

    The source is only the bounding box needed by this output crop.  Its global
    integer origin is retained, so the interpolation phases are identical to a
    full sensor-sized white source without allocating one.
    """
    ox, oy = int(origin[0]), int(origin[1])
    cx, cy = float(sidecar_plane[0]) * 0.5, float(sidecar_plane[1]) * 0.5
    corners_x = np.asarray([ox, ox + size - 1, ox, ox + size - 1], dtype=np.float64)
    corners_y = np.asarray([oy, oy, oy + size - 1, oy + size - 1], dtype=np.float64)
    sx, sy = transform.apply(corners_x, corners_y, cx, cy)
    xmin, xmax = math.floor(float(np.min(sx))) - 1, math.floor(float(np.max(sx))) + 2
    ymin, ymax = math.floor(float(np.min(sy))) - 1, math.floor(float(np.max(sy))) + 2
    rng = np.random.default_rng(seed)
    source = rng.standard_normal((ymax - ymin + 1, xmax - xmin + 1), dtype=np.float64)
    out = np.empty((size, size), dtype=np.float32)
    gx = np.arange(ox, ox + size, dtype=np.float64)
    for row0 in range(0, size, 32):
        gy = np.arange(oy + row0, oy + min(row0 + 32, size), dtype=np.float64)
        yy, xx = np.meshgrid(gy, gx, indexing="ij")
        sx, sy = transform.apply(xx, yy, cx, cy)
        x0 = np.floor(sx).astype(np.intp)
        y0 = np.floor(sy).astype(np.intp)
        wx = catmull_weights(sx - x0)
        wy = catmull_weights(sy - y0)
        acc = np.zeros_like(sx)
        for j in range(4):
            horizontal = np.zeros_like(sx)
            for i in range(4):
                horizontal += source[y0 + j - 1 - ymin, x0 + i - 1 - xmin] * wx[i]
            acc += horizontal * wy[j]
        out[row0 : row0 + len(gy)] = acc.astype(np.float32)
    return out


def _interior_values(array: np.ndarray, max_values: int = 24000) -> np.ndarray:
    margin = max(1, min(8, min(array.shape) // 8))
    core = np.asarray(array, dtype=np.float64)[margin:-margin, margin:-margin]
    flat = core.ravel()
    step = max(1, math.ceil(len(flat) / max_values))
    return flat[::step][:max_values]


def _score_core(level: np.ndarray, band: int) -> np.ndarray:
    start = AFFINE_CAL_MARGIN >> band
    extent = SCORE_SIZE >> band
    return np.asarray(level, dtype=np.float64)[start : start + extent, start : start + extent]


def _affine_features(transform: Similarity, score_origin: Sequence[int], sidecar_plane: Sequence[int]) -> np.ndarray:
    scale = math.hypot(transform.a_re, transform.a_im)
    angle = math.atan2(transform.a_im, transform.a_re)
    x = float(score_origin[0]) + SCORE_SIZE * 0.5
    y = float(score_origin[1]) + SCORE_SIZE * 0.5
    sx, sy = transform.apply(
        np.asarray([x]), np.asarray([y]), float(sidecar_plane[0]) * 0.5, float(sidecar_plane[1]) * 0.5
    )
    px, py = float(sx[0] % 1.0), float(sy[0] % 1.0)
    ds = scale - 1.0
    return np.asarray(
        [
            1.0,
            ds,
            ds * ds,
            ds * ds * ds,
            angle,
            angle * angle,
            ds * angle,
            math.sin(2 * math.pi * px),
            math.cos(2 * math.pi * px),
            math.sin(2 * math.pi * py),
            math.cos(2 * math.pi * py),
        ],
        dtype=np.float64,
    )


def calibrate_affine_model(seed: int = AFFINE_CAL_SEED) -> dict:
    """Estimate beta on every preregistered frame/warp lattice, without RAWs."""
    records: list[dict] = []
    ordinal = 0
    for capture, config in CAPTURES.items():
        meta, transforms = parse_warpmap(Path(config["transform"]))
        sidecar_plane = tuple(int(v) for v in meta["plane"])
        if sidecar_plane[1] != 2344 or sidecar_plane[0] not in (3516, 3520):
            raise RuntimeError(f"{capture}: unsupported sidecar plane {sidecar_plane}")
        origin = (
            int(config["score_origin"][0]) - AFFINE_CAL_MARGIN,
            int(config["score_origin"][1]) - AFFINE_CAL_MARGIN,
        )
        for frame, transform in enumerate(transforms):
            field = affine_white(transform, origin, sidecar_plane, AFFINE_CAL_SIZE, seed + ordinal)
            levels = laplacian_pyramid(field, BANDS)
            raw_beta = [float(np.mean(_score_core(levels[b], b) ** 2)) for b in range(BANDS)]
            records.append(
                {
                    "capture": capture,
                    "frame": frame,
                    "transform": [transform.a_re, transform.a_im, transform.b_re, transform.b_im],
                    "sidecar_plane": list(sidecar_plane),
                    "features": _affine_features(transform, config["score_origin"], sidecar_plane).tolist(),
                    "raw_beta": raw_beta,
                }
            )
            ordinal += 1
    features = np.asarray([r["features"] for r in records], dtype=np.float64)
    raw = np.asarray([r["raw_beta"] for r in records], dtype=np.float64)
    fitted = raw.copy()
    fit_diagnostics = []
    for band in range(BANDS):
        # Bands 0..3 have enough coefficients for a direct frame-specific
        # trace estimate.  Coarser estimates are fitted jointly over actual
        # transforms to remove the otherwise dominant 8x8/16x16 trace noise.
        if band >= 4:
            coefficients, _, _, _ = np.linalg.lstsq(features, np.log(raw[:, band]), rcond=None)
            fitted[:, band] = np.exp(features @ coefficients)
            residual = np.log(raw[:, band]) - features @ coefficients
            fit_diagnostics.append(
                {
                    "band": band,
                    "log_rms": float(np.sqrt(np.mean(residual * residual))),
                    "max_abs_log": float(np.max(np.abs(residual))),
                    "coefficients": coefficients.tolist(),
                }
            )
    if not np.all(np.isfinite(fitted) & (fitted > 0)):
        raise RuntimeError("actual-affine beta calibration produced an invalid value")
    by_capture: dict[str, list[dict]] = {name: [] for name in CAPTURES}
    for record, beta in zip(records, fitted, strict=True):
        out = dict(record)
        out["beta"] = beta.tolist()
        by_capture[record["capture"]].append(out)
    return {
        "kind": "actual-affine stochastic trace over every sealed sidecar transform",
        "seed": seed,
        "field_size": AFFINE_CAL_SIZE,
        "score_core": SCORE_SIZE,
        "coarse_fit_from_band": 4,
        "fit_diagnostics": fit_diagnostics,
        "records": by_capture,
    }


def beta_for_frame(calibration: dict, capture: str, frame: int) -> np.ndarray:
    records = calibration.get("records", {}).get(capture, [])
    if len(records) != CAPTURES[capture]["frames"] or records[frame].get("frame") != frame:
        raise RuntimeError(f"{capture}: commissioned beta records are missing or reordered")
    value = np.asarray(records[frame]["beta"], dtype=np.float64)
    if value.shape != (BANDS,) or not np.all(np.isfinite(value) & (value > 0)):
        raise RuntimeError(f"{capture} frame {frame}: invalid commissioned beta")
    return value


def validate_affine_coverage(calibration: dict, nu: Sequence[float], seed: int = AFFINE_VALIDATION_SEED) -> dict:
    values: list[list[np.ndarray]] = [[] for _ in range(BANDS)]
    frame_hits: dict[str, list[list[float]]] = {name: [] for name in CAPTURES}
    reference_beta = {
        name: beta_for_frame(calibration, name, int(parse_warpmap(Path(cfg["transform"]))[0]["reference"]))
        for name, cfg in CAPTURES.items()
    }
    plant_hits = np.zeros(BANDS, dtype=np.int64)
    plant_total = np.zeros(BANDS, dtype=np.int64)
    ordinal = 0
    for capture, config in CAPTURES.items():
        meta, transforms = parse_warpmap(Path(config["transform"]))
        sidecar_plane = tuple(int(v) for v in meta["plane"])
        origin = (
            int(config["score_origin"][0]) - AFFINE_CAL_MARGIN,
            int(config["score_origin"][1]) - AFFINE_CAL_MARGIN,
        )
        for frame, transform in enumerate(transforms):
            field = affine_white(transform, origin, sidecar_plane, AFFINE_CAL_SIZE, seed + ordinal)
            levels = laplacian_pyramid(field, BANDS)
            beta = beta_for_frame(calibration, capture, frame)
            coverage_row = []
            for band in range(BANDS):
                energy = _score_core(smooth5(levels[band] * levels[band]), band).ravel()
                step = max(1, math.ceil(len(energy) / 12000))
                energy = energy[::step]
                values[band].append(energy / beta[band])
                half = 1.96 * math.sqrt(2.0 * beta[band] * beta[band] / float(nu[band]))
                coverage_row.append(float(np.mean(np.abs(energy - beta[band]) <= half)))
                planted = float(reference_beta[capture][band])
                plant_half = 1.96 * math.sqrt(2.0 * planted * planted / float(nu[band]))
                plant_hits[band] += int(np.count_nonzero(np.abs(energy - planted) <= plant_half))
                plant_total[band] += len(energy)
            frame_hits[capture].append(coverage_row)
            ordinal += 1
    q95 = np.asarray([np.quantile(np.abs(np.concatenate(v) - 1.0), 0.95) for v in values])
    moment = np.asarray([2.0 / np.var(np.concatenate(v), ddof=1) for v in values])
    measured_nu = np.minimum(0.98 * 2.0 * (1.96 / q95) ** 2, moment)
    all_frame_rows = np.asarray([row for rows in frame_hits.values() for row in rows], dtype=np.float64)
    counts = np.asarray([sum(len(x) for x in v) for v in values], dtype=np.int64)
    overall = []
    analytic = []
    for band, samples in enumerate(values):
        joined = np.concatenate(samples)
        half_ratio = 1.96 * math.sqrt(2.0 / float(nu[band]))
        overall.append(float(np.mean(np.abs(joined - 1.0) <= half_ratio)))
        analytic_half = 1.96 * math.sqrt(2.0 / NU_ANALYTIC)
        analytic.append(float(np.mean(np.abs(joined - 1.0) <= analytic_half)))
    return {
        "seed": seed,
        "measured_nu_eff": measured_nu.tolist(),
        "q95_absolute_relative_error": q95.tolist(),
        "moment_nu_eff": moment.tolist(),
        "overall_by_band": overall,
        "analytic_nu_coverage_by_band": analytic,
        "worst_frame_by_band": np.min(all_frame_rows, axis=0).tolist(),
        "median_frame_by_band": np.median(all_frame_rows, axis=0).tolist(),
        "phase_only_reference_beta_plant_coverage": (plant_hits / plant_total).tolist(),
        "sample_counts": counts.tolist(),
        "per_frame": frame_hits,
    }


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
    # Each deinterleaved CFA plane sample is two final-output sensels apart.
    # Giving that physical spacing to NumPy makes every returned coordinate
    # cycles/output-pixel directly; there is no implicit post-hoc /2.
    fy = np.fft.fftfreq(size, d=2.0)
    fx = np.fft.rfftfreq(size, d=2.0)
    yy, xx = np.meshgrid(fy, fx, indexing="ij")
    output_frequency = np.hypot(xx, yy)
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
    # In output-sensel coordinates G1 is offset (+1,0) and G2 (0,+1).
    phase = np.exp(-2j * np.pi * (fx - fy))
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
    calibration = calibrate_affine_model()
    frozen = np.asarray(FROZEN_NU_EFF, dtype=np.float64)
    if np.any(frozen <= 0):
        raise RuntimeError("FROZEN_NU_EFF is not sealed; run --calibrate-nu, preregister, then patch constants")
    coverage = validate_affine_coverage(calibration, frozen)
    measured_nu = np.asarray(coverage["measured_nu_eff"], dtype=np.float64)
    conservatism = frozen / measured_nu

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

    # Independent vector gather checked by an affine analytic predicate and a
    # separately written scalar Keys-kernel implementation on nonlinear data.
    yy, xx = np.mgrid[0:32, 0:32]
    ramp = (3.0 * xx + 5.0 * yy + 11.0).astype(np.float32)
    t = Similarity(0.997, 0.013, 0.25, 0.40)
    got = gather_crop(ramp, t, (8, 8), (8, 8), (32, 32)).astype(np.float64)
    ey, ex = np.mgrid[8:16, 8:16]
    sx, sy = t.apply(ex.astype(np.float64), ey.astype(np.float64), 16.0, 16.0)
    expected = 3.0 * sx + 5.0 * sy + 11.0
    gather_error = float(np.max(np.abs(got - expected)))
    fixture = np.sin(xx * 0.37) + np.cos(yy * 0.29) + 0.01 * xx * yy
    nonlinear = gather_crop(fixture.astype(np.float32), t, (8, 8), (8, 8), (32, 32)).astype(np.float64)
    scalar_expected = np.empty_like(nonlinear)
    fsx, fsy = t.apply(ex.astype(np.float64), ey.astype(np.float64), 16.0, 16.0)
    for py in range(8):
        for px in range(8):
            scalar_expected[py, px] = scalar_catmull(fixture, float(fsx[py, px]), float(fsy[py, px]))
    scalar_error = float(np.max(np.abs(nonlinear - scalar_expected)))
    translated_only = gather_crop(
        fixture.astype(np.float32),
        Similarity(1.0, 0.0, t.b_re, t.b_im),
        (8, 8),
        (8, 8),
        (32, 32),
    )
    affine_omission_error = float(np.max(np.abs(translated_only - scalar_expected)))
    rows.append(
        _row(
            "independent-crop-gather",
            "affine ramp + nonlinear scalar Keys cubic",
            {"analytic_max_error": gather_error, "scalar_vector_error": scalar_error},
            gather_error < 5e-5 and scalar_error < 2e-6,
            "translation-only lattice",
            affine_omission_error,
            affine_omission_error > 1e-3,
        )
    )

    mosaic = np.arange(64, dtype=np.float32).reshape(8, 8)
    er, eg1, eg2, eb = extract_cfa_planes(mosaic, np.asarray([[0, 1], [3, 2]]))
    decode_ok = (
        np.array_equal(er, mosaic[0::2, 0::2])
        and np.array_equal(eg1, mosaic[0::2, 1::2])
        and np.array_equal(eg2, mosaic[1::2, 0::2])
        and np.array_equal(eb, mosaic[1::2, 1::2])
    )
    two_plane_plant = len((eg1, eg2))
    rows.append(
        _row(
            "cfa-four-plane-extraction",
            "canonical R/G1/G2/B phase tags",
            decode_ok,
            decode_ok,
            "green-only reconstruction",
            two_plane_plant,
            two_plane_plant != 4,
        )
    )

    constant = np.full((256, 256), 1234.5, dtype=np.float32)
    constant_error = max(float(np.max(np.abs(x))) for x in laplacian_pyramid(constant, BANDS)[:-1])
    edge_plant = constant.copy()
    edge_plant[:, 128:] += 20
    edge_read = float(np.max(np.abs(laplacian_pyramid(edge_plant, BANDS)[0])))
    rows.append(_row("constant-field-pyramid", "constant has zero bands", constant_error, constant_error < 1e-5, "planted step", edge_read, edge_read > 1.0))

    # The band-6 Laplacian plus smooth5 energy has a 510-pixel input support.
    # A 512 halo must reproduce a larger-context crop; the old 256 halo must not.
    rng = np.random.default_rng(0xA110_512)
    context = rng.standard_normal((2048, 2048), dtype=np.float32)
    full_band = laplacian_pyramid(context, BANDS)[6]
    full_energy = smooth5(full_band * full_band)
    correct_crop = context[256:1792, 256:1792]
    correct_band = laplacian_pyramid(correct_crop, BANDS)[6]
    correct_energy = smooth5(correct_band * correct_band)
    old_crop = context[512:1536, 512:1536]
    old_band = laplacian_pyramid(old_crop, BANDS)[6]
    old_energy = smooth5(old_band * old_band)
    truth = full_energy[12:20, 12:20]
    denominator = np.maximum(np.abs(truth), 1e-30)
    halo512_error = float(np.max(np.abs(correct_energy[8:16, 8:16] - truth) / denominator))
    halo256_error = float(np.max(np.abs(old_energy[4:12, 4:12] - truth) / denominator))
    rows.append(
        _row(
            "pyramid-halo-support",
            "512 halo against larger context",
            halo512_error,
            halo512_error <= 1e-12,
            "old 256 halo",
            halo256_error,
            halo256_error > 0.01,
        )
    )

    # External physical-frequency predicate: a 0.20 cyc/output-pixel sinusoid
    # sampled every two output pixels lands at plane-bin 0.40 and physical bin
    # 0.20. Treating plane samples as d=1 excludes that known in-band signal.
    nfreq = 40
    physical_frequency = 0.20
    wave = np.cos(2.0 * np.pi * physical_frequency * (2.0 * np.arange(nfreq)))
    peak = int(np.argmax(np.abs(np.fft.rfft(wave))[1:]) + 1)
    mask, physical_fx, _ = frequency_mask(nfreq)
    physical_reading = float(physical_fx[0, peak])
    wrong_fx = np.fft.rfftfreq(nfreq, d=1.0)
    wrong_in_band = bool(FREQ_OUTPUT[0] <= wrong_fx[peak] <= FREQ_OUTPUT[1])
    rows.append(
        _row(
            "output-frequency-units",
            "known 0.20 cyc/output-pixel sinusoid",
            {"peak": peak, "frequency": physical_reading, "selected": bool(mask[0, peak])},
            abs(physical_reading - physical_frequency) < 1e-12 and bool(mask[0, peak]),
            "plane-pixel d=1",
            {"reported_frequency": float(wrong_fx[peak]), "selected": wrong_in_band},
            not wrong_in_band,
        )
    )

    rows.append(
        _row(
            "correlated-nu-coverage",
            "held-out actual-affine/null seeds",
            {
                "overall": coverage["overall_by_band"],
                "worst_frame": coverage["worst_frame_by_band"],
                "frozen_over_calibrated": conservatism.tolist(),
            },
            min(coverage["overall_by_band"]) >= 0.94
            and max(coverage["overall_by_band"]) <= 0.997
            and np.all((conservatism >= 0.35) & (conservatism <= 1.0)),
            "phase-only reference-frame beta",
            coverage["phase_only_reference_beta_plant_coverage"],
            min(coverage["phase_only_reference_beta_plant_coverage"]) < 0.94
            or max(coverage["phase_only_reference_beta_plant_coverage"]) > 0.997,
        )
    )
    rows.append(
        _row(
            "correlated-nu-not-analytic",
            "measured actual-affine nu_eff",
            coverage["measured_nu_eff"],
            bool(np.all(measured_nu < NU_ANALYTIC)),
            "NU_SMOOTH=13.37469",
            coverage["analytic_nu_coverage_by_band"],
            min(coverage["analytic_nu_coverage_by_band"]) < 0.93,
        )
    )

    # Poisson-Gaussian null is not part of the Gaussian phase fit.
    identity_beta0 = float(
        np.mean(
            [
                beta_for_frame(
                    calibration,
                    name,
                    int(parse_warpmap(Path(config["transform"]))[0]["reference"]),
                )[0]
                for name, config in CAPTURES.items()
            ]
        )
    )
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
            f = identity_beta0 * v
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
        "schema": SCHEMA,
        "epoch": EPOCH,
        "design_sha": DESIGN_SHA256,
        "status": "PASS" if all(r["pass"] for r in rows) else "FAIL",
        "rows": rows,
        "affine_calibration": calibration,
        "affine_validation": coverage,
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
            "site_provenance": (
                {
                    "kind": "input-only reference-frame scout before any flat-on-ruler candidate score",
                    "reference_raw": "DSC00040.ARW",
                    "selection": "top positive coherent detail; lowest flat power among remaining mean>=1200-DN tiles",
                    "scout_json": {
                        "path": "results/scout-flat-tiles.json",
                        "sha256": sha256(RESULTS / "scout-flat-tiles.json"),
                    },
                    "overlay": {
                        "path": "results/scout-flat-tiles.png",
                        "sha256": sha256(RESULTS / "scout-flat-tiles.png"),
                    },
                    "reference_preview": {
                        "path": "results/scout-flat-reference.png",
                        "sha256": sha256(RESULTS / "scout-flat-reference.png"),
                    },
                }
                if name == "flat-on-ruler"
                else {
                    "kind": "unchanged crop and tile lists carried from e64fca59, frozen before the superseded run outcomes"
                }
            ),
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
        "schema": SCHEMA,
        "epoch": EPOCH,
        "design_sha": DESIGN_SHA256,
        "created_for": "revised phase-1 W1 preregistration; no flat-on-ruler candidate outcome inspected",
        "alignment_binary": {"path": str(exe), "sha256": sha256(exe), "version": version},
        "decoder": {
            "binding": f"rawpy {rawpy.__version__}",
            "libraw": ".".join(str(v) for v in rawpy.libraw_version),
            "visible_geometry": [7028, 4688],
            "reference_plane_geometry": [3514, 2344],
            "sidecar_plane_geometry": "per capture from warpmap: 3520x2344 flat-on-ruler; 3516x2344 others",
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
            "frozen_nu_eff": list(FROZEN_NU_EFF),
            "beta": "one commissioned actual-affine stochastic trace per frame/band; bands 4..6 jointly fitted over actual transform features",
            "frequency_unit": "cycles per full-resolution output sensel; deinterleaved CFA-plane sample spacing d=2",
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
            calibration = calibrate_affine_model()
            result = validate_affine_coverage(calibration, FROZEN_NU_EFF)
            print(json.dumps({"measured_nu_eff": result["measured_nu_eff"]}, indent=2))
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
