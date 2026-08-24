"""Shared M82 configuration and independent shipped-merge reproduction."""

from __future__ import annotations

import hashlib
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CORPUS = Path(r"D:\personal\macro")
PAD = 32

REQUESTS = (0.90, 0.70, 0.50)
PRIMARY_REQUEST = 0.70
CONFIRM_TOLERANCE = 0.005
LADDER_GATES = (
    0.0,
    0.25,
    0.5,
    1.0,
    2.0,
    4.0,
    8.0,
    16.0,
    24.0,
    32.0,
    40.0,
    48.0,
    64.0,
    96.0,
    128.0,
)

STACKS = {
    "wrapped-text-1": {
        "n": 130,
        "iso": 100.0,
        "flat": (32, 1312, 256, 256),
        "detail": (2208, 672, 256, 256),
        "sharp_flat": (32, 1184, 512, 512),
        "sharp_detail": (2080, 544, 512, 512),
    },
    "wrapped-text-2": {
        "n": 120,
        "iso": 400.0,
        "flat": (32, 672, 256, 256),
        "detail": (3104, 160, 256, 256),
        "sharp_flat": (32, 544, 512, 512),
        "sharp_detail": (2970, 32, 512, 512),
    },
    "109MSDCF": {
        "n": 22,
        "iso": 160.0,
        "flat": (1440, 416, 256, 256),
        "detail": (1952, 1056, 256, 256),
        "sharp_flat": (1312, 288, 512, 512),
        "sharp_detail": (1824, 928, 512, 512),
    },
    "coffee-bean": {
        "n": 105,
        "iso": 50.0,
        "flat": (32, 416, 256, 256),
        "detail": (1312, 416, 256, 256),
        "sharp_flat": (32, 288, 512, 512),
        "sharp_detail": (1184, 288, 512, 512),
    },
    "foam": {
        "n": 100,
        "iso": 1000.0,
        "flat": (1312, 288, 256, 256),
        "detail": (160, 1952, 256, 256),
        "sharp_flat": (1184, 160, 512, 512),
        "sharp_detail": (32, 1800, 512, 512),
    },
    "bee-1": {
        "directory": "bee-1-cpl",
        "n": 299,
        "iso": 100.0,
        "flat": (2720, 1568, 256, 256),
        "detail": (1952, 672, 256, 256),
        "sharp_flat": (2592, 1440, 512, 512),
        "sharp_detail": (1824, 544, 512, 512),
    },
    "bee-2": {
        "directory": "bee-2-cpl",
        "n": 299,
        "iso": 400.0,
        "flat": (2720, 1568, 256, 256),
        "detail": (1952, 672, 256, 256),
        "sharp_flat": (2592, 1440, 512, 512),
        "sharp_detail": (1824, 544, 512, 512),
    },
    "bee-3": {
        "directory": "bee-3-cpl",
        "n": 299,
        "iso": 100.0,
        "flat": (2720, 1568, 256, 256),
        "detail": (1952, 672, 256, 256),
        "sharp_flat": (2592, 1440, 512, 512),
        "sharp_detail": (1824, 544, 512, 512),
    },
}

ORIGINAL_STACKS = (
    "wrapped-text-1",
    "wrapped-text-2",
    "109MSDCF",
    "coffee-bean",
    "foam",
    "bee-1",
)
FIVE = ("wrapped-text-1", "109MSDCF", "coffee-bean", "foam", "bee-1")
SIBLINGS = ("wrapped-text-1", "wrapped-text-2")
BEE_SIBLINGS = ("bee-1", "bee-2", "bee-3")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _grab(path: Path, pattern: str, cast=float):
    text = path.read_text(encoding="utf-8")
    match = re.search(pattern, text)
    if match is None:
        raise RuntimeError(f"constant not found in {path}: {pattern}")
    value = match.group(1).replace("_", "")
    return cast(value)


@lru_cache(maxsize=1)
def constants() -> dict[str, float | int]:
    core = REPO / "crates" / "strehl-core" / "src"
    return {
        "focus_noise_sd": _grab(
            core / "merge.rs", r"pub const FOCUS_NOISE_SD: f32 = ([0-9_.]+);"
        ),
        "window_radius": _grab(
            core / "focus.rs", r"pub const WINDOW_RADIUS: usize = (\d+);", int
        ),
        "regulariser_radius": _grab(
            core / "merge.rs",
            r"pub const REGULARISER_RADIUS: usize = (\d+);",
            int,
        ),
        "sigma_eps": _grab(
            core / "focus.rs", r"const SIGMA_EPS: f32 = ([0-9.eE+-]+);"
        ),
        "container_max": _grab(
            core / "clip.rs", r"pub const CONTAINER_MAX_DN: u16 = (\d+);", int
        ),
        "gain_divisor": _grab(
            core / "profile.rs", r"gain_divisor: ([0-9.]+),"
        ),
        "base_iso": _grab(core / "profile.rs", r"base_iso: ([0-9.]+),"),
        "read_noise_low": _grab(
            core / "profile.rs", r"read_noise_e_low: ([0-9.]+),"
        ),
        "read_noise_high": _grab(
            core / "profile.rs", r"read_noise_e_high: ([0-9.]+),"
        ),
        "second_base_iso": _grab(
            core / "profile.rs", r"second_base_iso: ([0-9.]+),"
        ),
        "hp_box_side": _grab(
            core / "flat_ratio.rs",
            r"pub const HP_BOX_SIDE: usize = (\d+);",
            int,
        ),
    }


def stack_files(stack: str) -> list[Path]:
    directory = str(STACKS[stack].get("directory", stack))
    files = sorted(
        path
        for path in (CORPUS / directory).iterdir()
        if path.suffix.upper() == ".ARW"
    )
    expected = int(STACKS[stack]["n"])
    if len(files) != expected:
        raise RuntimeError(f"{stack}: expected {expected} RAW files, got {len(files)}")
    return files


def gain_dn_per_e(iso: float) -> float:
    c = constants()
    return max(iso, float(c["base_iso"])) / float(c["gain_divisor"])


def read_noise_e(iso: float) -> float:
    c = constants()
    if iso >= float(c["second_base_iso"]):
        return float(c["read_noise_high"])
    return float(c["read_noise_low"])


def green_luma_sigma(signal: np.ndarray | float, iso: float):
    gain = gain_dn_per_e(iso)
    read = read_noise_e(iso) * gain
    variance = gain * np.maximum(signal, 0.0) + read * read
    return np.sqrt(0.5 * variance)


@lru_cache(maxsize=32)
def _box_counts(shape: tuple[int, int], radius: int) -> np.ndarray:
    y = np.arange(shape[0])
    x = np.arange(shape[1])
    ny = np.minimum(y + radius, shape[0] - 1) - np.maximum(y - radius, 0) + 1
    nx = np.minimum(x + radius, shape[1] - 1) - np.maximum(x - radius, 0) + 1
    return (ny[:, None] * nx[None, :]).astype(np.float32)


def clamped_box(values: np.ndarray, radius: int) -> np.ndarray:
    from scipy.ndimage import uniform_filter

    side = 2 * radius + 1
    total = (
        uniform_filter(values, size=side, mode="constant", cval=0.0)
        * np.float32(side * side)
    )
    return total / _box_counts(values.shape, radius)


def focus_field(luma: np.ndarray, iso: float) -> np.ndarray:
    from scipy.ndimage import sobel

    c = constants()
    gx = sobel(luma, axis=1, mode="nearest") * np.float32(0.125)
    gy = sobel(luma, axis=0, mode="nearest") * np.float32(0.125)
    magnitude = np.hypot(gx, gy)
    coarse = clamped_box(magnitude, int(c["window_radius"]))
    sigma = np.maximum(
        green_luma_sigma(luma, iso), np.float32(c["sigma_eps"])
    )
    coarse /= sigma
    return clamped_box(coarse, int(c["regulariser_radius"])).astype(
        np.float32, copy=False
    )


def _green_region(
    path: Path, region: tuple[int, int, int, int] | None
) -> tuple[np.ndarray, np.ndarray, float, tuple[int, int]]:
    import rawpy

    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible
        plane_h = visible.shape[0] // 2
        plane_w = visible.shape[1] // 2
        if region is None:
            x0, y0, width, height = 0, 0, plane_w, plane_h
        else:
            x0, y0, width, height = region
        if x0 < 0 or y0 < 0 or x0 + width > plane_w or y0 + height > plane_h:
            raise RuntimeError(
                f"{path.name}: region {(x0, y0, width, height)} outside "
                f"{plane_w}x{plane_h}"
            )
        g1 = np.array(
            visible[2 * y0 : 2 * (y0 + height) : 2, 2 * x0 + 1 : 2 * (x0 + width) + 1 : 2],
            dtype=np.float32,
            copy=True,
        )
        g2 = np.array(
            visible[2 * y0 + 1 : 2 * (y0 + height) + 1 : 2, 2 * x0 : 2 * (x0 + width) : 2],
            dtype=np.float32,
            copy=True,
        )
        black_levels = tuple(float(v) for v in raw.black_level_per_channel)
    if max(black_levels) != min(black_levels):
        raise RuntimeError(f"{path.name}: unequal RAW black levels {black_levels}")
    return g1, g2, black_levels[0], (plane_h, plane_w)


def frame_arrays(
    path: Path, iso: float, region: tuple[int, int, int, int] | None
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    float,
    tuple[int, int],
]:
    g1, g2, black, plane = _green_region(path, region)
    raw_green = 0.5 * (g1 + g2)
    luma = 0.5 * (np.maximum(g1 - black, 0.0) + np.maximum(g2 - black, 0.0))
    field = focus_field(luma, iso)
    pins = (g1 >= float(constants()["container_max"])) | (
        g2 >= float(constants()["container_max"])
    )
    return raw_green, luma, field, pins, black, plane


def admission_mask(gap: np.ndarray, tolerance: np.float32) -> np.ndarray:
    admitted = gap <= tolerance  # M82_CORE_ADMISSION
    return admitted


def subset_reference(
    fields: np.ndarray, indexes: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    if indexes.size == 0:
        raise RuntimeError("empty frame subset")
    best = np.full(fields.shape[1:], -np.inf, dtype=np.float32)
    winner = np.zeros(fields.shape[1:], dtype=np.uint16)
    for frame_index in indexes:
        better = fields[frame_index] > best
        best[better] = fields[frame_index][better]
        winner[better] = frame_index
    return best, winner


def merge_subset(
    raw_cube: np.ndarray,
    fields: np.ndarray,
    indexes: np.ndarray,
    best: np.ndarray,
    winner: np.ndarray,
    gate: float,
) -> tuple[np.ndarray, dict]:
    tolerance = np.float32(
        gate * math.sqrt(2.0) * float(constants()["focus_noise_sd"])
    )
    count = np.zeros(best.shape, dtype=np.uint16)
    total = np.zeros(best.shape, dtype=np.float64)
    distance = np.zeros(best.shape, dtype=np.float64)
    for frame_index in indexes:
        gap = best - fields[frame_index]
        admitted = admission_mask(gap, tolerance)
        admitted |= winner == frame_index
        count += admitted
        total += raw_cube[frame_index] * admitted
        distance += np.abs(winner.astype(np.int32) - int(frame_index)) * admitted
    if np.any(count == 0):
        raise RuntimeError("admission produced an empty pixel")
    merged = (total / count).astype(np.float32)
    quantiles = np.quantile(count, [0.1, 0.5, 0.9])
    stats = {
        "mean_n_eff": float(count.mean()),
        "singleton_percent": float(100.0 * np.mean(count == 1)),
        "n_eff_p10": float(quantiles[0]),
        "n_eff_p50": float(quantiles[1]),
        "n_eff_p90": float(quantiles[2]),
        "mean_admitted_index_distance": float(np.mean(distance / count)),
    }
    return merged, stats


def raw_gradient_rms(values: np.ndarray) -> float:
    dx = values[:-1, 1:] - values[:-1, :-1]
    dy = values[1:, :-1] - values[:-1, :-1]
    return float(np.sqrt(np.mean(dx.astype(np.float64) ** 2 + dy.astype(np.float64) ** 2)))


def m77_contamination(luma: np.ndarray, roi: tuple[int, int, int, int], iso: float) -> float:
    from scipy.ndimage import uniform_filter

    x, y, width, height = roi
    side = int(constants()["hp_box_side"])
    radius = side // 2
    tile = luma[y : y + height, x : x + width]
    smooth = uniform_filter(tile, size=side, mode="nearest")
    residual = (tile - smooth)[radius:-radius, radius:-radius]
    hp_sd = float(residual.std())
    model_sigma = float(green_luma_sigma(float(tile.mean()), iso))
    hp_gain = math.sqrt(1.0 - 1.0 / float(side * side))
    return hp_sd / (hp_gain * model_sigma)


def solve_gate(rows: list[dict], request: float) -> dict:
    positive = [row for row in rows if row["gate"] > 0.0]
    for low_gate, high_gate in zip(positive, positive[1:]):
        s0 = low_gate["predicted_sigma_gain"]
        s1 = high_gate["predicted_sigma_gain"]
        if s0 >= request >= s1:
            fraction = math.log(request / s0) / math.log(s1 / s0)
            gate = math.exp(
                math.log(low_gate["gate"])
                + fraction * math.log(high_gate["gate"] / low_gate["gate"])
            )
            reconstructed = math.exp(
                math.log(s0)
                + math.log(gate / low_gate["gate"])
                / math.log(high_gate["gate"] / low_gate["gate"])
                * math.log(s1 / s0)
            )
            return {
                "request": request,
                "gate": gate,
                "bracket": [low_gate, high_gate],
                "reconstructed_gain": reconstructed,
                "relative_error": abs(reconstructed / request - 1.0),
            }
    raise RuntimeError(f"request {request:.4f} is not bracketed")


def self_tests() -> None:
    print("M82_SELF_TEST_COUNT=4")
    gaps = np.array([0.0, 1.0, 2.0], dtype=np.float32)
    narrow = admission_mask(gaps, np.float32(0.0))
    wide = admission_mask(gaps, np.float32(2.0))
    assert narrow.tolist() == [True, False, False]
    assert wide.tolist() == [True, True, True]
    plant = [
        {"gate": 1.0, "predicted_sigma_gain": 0.9},
        {"gate": 4.0, "predicted_sigma_gain": 0.6},
        {"gate": 16.0, "predicted_sigma_gain": 0.4},
    ]
    solved = solve_gate(plant, math.sqrt(0.54))
    assert abs(solved["gate"] - 2.0) < 1e-12, solved
    a = np.array([[0.0, 1.0], [2.0, 4.0]], dtype=np.float32)
    assert abs(raw_gradient_rms(a) - math.sqrt(5.0)) < 1e-12
    assert int(constants()["window_radius"]) == 13
    print("M82_SELF_TESTS=4/4 PASS")


if __name__ == "__main__":
    if "--self-test-only" not in sys.argv:
        raise SystemExit("m82lib.py only supports --self-test-only")
    self_tests()
