"""Development-only reciprocal-lattice probe for M147."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import rawpy
from scipy import ndimage


TILE = 512
STRIDE = 256
PAD = 1024
MIN_PERIOD = 24.0
MAX_PERIOD = 160.0


def load_green(path: Path) -> np.ndarray:
    with rawpy.imread(str(path)) as raw:
        mosaic = np.array(raw.raw_image_visible, dtype=np.float32, copy=True)
        pattern = np.array(raw.raw_pattern, copy=True)
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
        color_desc = bytes(raw.color_desc)
    green_indices = [index for index, value in enumerate(color_desc) if value == ord("G")]
    positions = np.argwhere(np.isin(pattern, green_indices))
    planes = []
    for row, column in positions:
        planes.append(mosaic[row::2, column::2] - black[pattern[row, column]])
    return np.mean(planes, axis=0)


def refine(power: np.ndarray, row: int, column: int) -> tuple[float, float]:
    log_power = np.log(np.maximum(power, np.finfo(np.float64).tiny))

    def offset(a: float, b: float, c: float) -> float:
        denominator = a - 2.0 * b + c
        if denominator >= -1e-12:
            return 0.0
        return float(np.clip(0.5 * (a - c) / denominator, -0.5, 0.5))

    dy = offset(log_power[row - 1, column], log_power[row, column], log_power[row + 1, column])
    dx = offset(log_power[row, column - 1], log_power[row, column], log_power[row, column + 1])
    return row + dy, column + dx


def one_tile(tile: np.ndarray) -> dict[str, float] | None:
    robust_range = float(np.percentile(tile, 95) - np.percentile(tile, 5))
    if robust_range <= 50.0:
        return None
    y, x = np.mgrid[-1.0:1.0:complex(TILE), -1.0:1.0:complex(TILE)]
    design = np.column_stack([np.ones(tile.size), x.ravel(), y.ravel()])
    coeff, *_ = np.linalg.lstsq(design, tile.ravel(), rcond=None)
    residual = tile - (coeff[0] + coeff[1] * x + coeff[2] * y)
    window = np.hanning(TILE)
    spectrum = np.fft.fftshift(np.fft.fft2(residual * window[:, None] * window[None, :], s=(PAD, PAD)))
    power = np.abs(spectrum) ** 2
    frequency = np.fft.fftshift(np.fft.fftfreq(PAD))
    fy, fx = np.meshgrid(frequency, frequency, indexing="ij")
    radius = np.hypot(fx, fy)
    annulus = (radius >= 1.0 / MAX_PERIOD) & (radius <= 1.0 / MIN_PERIOD)
    positive = (fy > 0.0) | ((fy == 0.0) & (fx > 0.0))
    local = power == ndimage.maximum_filter(power, size=5, mode="constant")
    candidates = np.argwhere(annulus & positive & local)
    if len(candidates) < 2:
        return None
    background = float(np.median(power[annulus]))
    candidates = sorted(
        candidates,
        key=lambda rc: float(power[tuple(rc)]),
        reverse=True,
    )[:30]
    best = None
    for index, first in enumerate(candidates):
        for second in candidates[index + 1 :]:
            f1 = np.array([frequency[first[1]], frequency[first[0]]])
            f2 = np.array([frequency[second[1]], frequency[second[0]]])
            n1 = float(np.linalg.norm(f1))
            n2 = float(np.linalg.norm(f2))
            angle = math.degrees(math.acos(np.clip(abs(float(f1 @ f2)) / (n1 * n2), 0.0, 1.0)))
            ratio = n1 / n2
            if not (70.0 <= angle <= 90.0 and 0.75 <= ratio <= 1.333333):
                continue
            score = math.sqrt(float(power[tuple(first)]) * float(power[tuple(second)]))
            if best is None or score > best[0]:
                best = (score, first, second, angle)
    if best is None:
        return None
    score, first, second, angle = best
    r1, c1 = refine(power, int(first[0]), int(first[1]))
    r2, c2 = refine(power, int(second[0]), int(second[1]))
    f1 = np.array([(c1 - PAD / 2) / PAD, (r1 - PAD / 2) / PAD])
    f2 = np.array([(c2 - PAD / 2) / PAD, (r2 - PAD / 2) / PAD])
    determinant = abs(float(np.linalg.det(np.stack([f1, f2]))))
    if determinant <= 0.0:
        return None
    return {
        "period": 1.0 / math.sqrt(determinant),
        "angle": angle,
        "snr_db": 10.0 * math.log10(max(score / background, 1e-30)),
        "f1": f1.tolist(),
        "f2": f2.tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw", type=Path)
    args = parser.parse_args()
    image = load_green(args.raw)
    rows = []
    for top in range(0, image.shape[0] - TILE + 1, STRIDE):
        for left in range(0, image.shape[1] - TILE + 1, STRIDE):
            result = one_tile(image[top : top + TILE, left : left + TILE])
            if result is not None:
                result.update(top=top, left=left)
                rows.append(result)
    rows.sort(key=lambda row: row["period"])
    for row in rows:
        print(
            f"top={row['top']:4d} left={row['left']:4d} "
            f"period={row['period']:9.4f} angle={row['angle']:6.2f} "
            f"snr={row['snr_db']:6.2f}"
        )
    periods = np.array([row["period"] for row in rows])
    print(f"count={len(rows)} median={np.median(periods):.6f} range={periods.min():.3f}..{periods.max():.3f}")


if __name__ == "__main__":
    main()
