"""Independent checker for the sharpening follow-up.

This does not import sharpening_core.py or sharpening-measure.py.  It uses the
already independent V-HEADTOHEAD3 checker primitives (numpy.unique ranks,
skimage registration/resampling) and a weighted real FFT.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Sequence

import numpy as np
import tifffile
from skimage.filters import gaussian

import check as baseline_check
import sharpening_frozen as frozen


ROOT0 = Path(r"D:\edited\macro\test2")
ROOT40 = Path(r"D:\edited\macro\test")
PMAX0 = ROOT0 / "2026-05-09-12.12.17 ZS PMax.tif"
PMAX40 = ROOT40 / "2026-05-07-21.31.06 ZS PMax.tif"
STREHL = Path(r"C:\dev\strehl-out\DELIVER-V6\masters\113MSDCF.tiff")
SELECT = (4, 20, 36, 52)
TRAIN = (1, 9, 17, 25, 33, 41, 49, 57)
HOLDOUT = (6, 14, 22, 30, 38, 46, 54, 62)
EDGES = np.arange(0.02, 0.201, 0.01)
SIDE = 512


def source(root: Path, identity: int) -> Path:
    return root / f"20260507-DSC{identity:05d}.tif"


def green(path: Path) -> np.ndarray:
    return tifffile.memmap(path)[:, :, 1]


def q25(a: np.ndarray, scale: float = 1.0) -> float:
    q = baseline_check.ranks(np.asarray(a))
    q -= q.mean()
    variance = float(np.mean(q * q))
    window = np.hanning(q.shape[0])[:, None] * np.hanning(q.shape[1])[None, :]
    power = np.abs(np.fft.rfft2(q * window)) ** 2
    if q.shape[1] % 2 == 0:
        power[:, 1:-1] *= 2.0
    else:
        power[:, 1:] *= 2.0
    radius = np.sqrt(
        np.fft.fftfreq(q.shape[0])[:, None] ** 2
        + np.fft.rfftfreq(q.shape[1])[None, :] ** 2
    )
    numerator = float(
        np.sum(
            power[(radius >= 0.20 * scale) & (radius < 0.25 * scale)],
            dtype=np.float64,
        )
    )
    return numerator / (q.size * float(np.sum(window * window)) * variance)


def registered(
    reference: np.ndarray,
    moving: np.ndarray,
    centre: Sequence[float],
) -> tuple[np.ndarray, np.ndarray, tuple[int, int]]:
    y, x = map(float, centre)
    large = SIDE + 80
    a_large = baseline_check.centred(reference, y, x, large)
    b_large = baseline_check.centred(moving, y, x, large)
    if a_large is None or b_large is None:
        raise ValueError(centre)
    shift = baseline_check.correction(
        baseline_check.ranks(a_large), baseline_check.ranks(b_large)
    )
    a = baseline_check.centred(reference, y, x, SIDE)
    b = baseline_check.centred(moving, y - shift[0], x - shift[1], SIDE)
    if a is None or b is None:
        raise ValueError((centre, shift))
    return a, b, shift


def hull_delta(a: np.ndarray, b: np.ndarray) -> float:
    from scipy.ndimage import maximum_filter, minimum_filter

    qa = baseline_check.ranks(a)
    qb = baseline_check.ranks(b)
    alo = minimum_filter(qa, 3, mode="nearest")
    ahi = maximum_filter(qa, 3, mode="nearest")
    blo = minimum_filter(qb, 3, mode="nearest")
    bhi = maximum_filter(qb, 3, mode="nearest")
    fwd = np.mean((qb < alo - 0.01) | (qb > ahi + 0.01))
    rev = np.mean((qa < blo - 0.01) | (qa > bhi + 0.01))
    return float(fwd - rev)


def summary(logs: Sequence[float], seed: int = 20260905) -> dict:
    values = np.asarray(logs, np.float64)
    rng = np.random.default_rng(seed)
    draws = np.empty(10_000)
    for i in range(len(draws)):
        draws[i] = np.mean(values[rng.integers(0, len(values), len(values))])
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "n": int(len(values)),
        "point": float(np.exp(np.mean(values))),
        "ci_low": float(np.exp(lo)),
        "ci_high": float(np.exp(hi)),
    }


def mean_summary(values: Sequence[float], seed: int = 20260905) -> dict:
    x = np.asarray(values, np.float64)
    rng = np.random.default_rng(seed)
    draws = np.empty(10_000)
    for i in range(len(draws)):
        draws[i] = np.mean(x[rng.integers(0, len(x), len(x))])
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "n": int(len(x)),
        "point": float(np.mean(x)),
        "ci_low": float(lo),
        "ci_high": float(hi),
    }


def independent_sites() -> dict[str, list[list[int]]]:
    images = [green(source(ROOT0, identity)) for identity in SELECT]
    rows = []
    for y in range(512, images[0].shape[0] - 383, 512):
        for x in range(512, images[0].shape[1] - 383, 512):
            scores = []
            rejected = False
            for image in images:
                crop = baseline_check.centred(image, y, x, SIDE)
                if crop is None or baseline_check.rail_fraction(crop) > 0.01:
                    rejected = True
                    break
                smooth = gaussian(
                    baseline_check.ranks(crop),
                    sigma=1.0,
                    mode="reflect",
                    preserve_range=True,
                )
                gy, gx = np.gradient(smooth)
                scores.append(float(np.quantile(np.hypot(gy, gx), 0.95)))
            if not rejected:
                rows.append((y, x, max(scores)))
    result = {}
    for parity in (0, 1):
        part = sorted(
            (
                row
                for row in rows
                if ((row[0] // 512 + row[1] // 512) % 2) == parity
            ),
            key=lambda row: (row[2], row[0], row[1]),
        )
        result[f"flat_{parity}"] = [[y, x] for y, x, _ in part[:12]]
        result[f"detail_{parity}"] = [[y, x] for y, x, _ in part[-12:]]
    return result


def radial(a: np.ndarray, scale: float | None = None) -> tuple[np.ndarray, float]:
    x = np.asarray(a, np.float64)
    own_scale = float(np.quantile(x, 0.75) - np.quantile(x, 0.25))
    norm = own_scale if scale is None else scale
    x = (x - x.mean()) / norm
    window = np.hanning(x.shape[0])[:, None] * np.hanning(x.shape[1])[None, :]
    power = np.abs(np.fft.rfft2(x * window)) ** 2
    if x.shape[1] % 2 == 0:
        power[:, 1:-1] *= 2.0
    else:
        power[:, 1:] *= 2.0
    radius = np.sqrt(
        np.fft.fftfreq(x.shape[0])[:, None] ** 2
        + np.fft.rfftfreq(x.shape[1])[None, :] ** 2
    )
    return (
        np.asarray(
            [
                np.sum(power[(radius >= lo) & (radius < hi)])
                for lo, hi in zip(EDGES[:-1], EDGES[1:])
            ],
            np.float64,
        ),
        own_scale,
    )


def transfer(ids: Sequence[int], sites: Sequence[Sequence[int]]) -> np.ndarray:
    p0 = np.zeros(len(EDGES) - 1)
    p40 = np.zeros_like(p0)
    for identity in ids:
        a = green(source(ROOT0, identity))
        b = green(source(ROOT40, identity))
        for y, x in sites:
            ca = baseline_check.centred(a, y, x, SIDE)
            cb = baseline_check.centred(b, y, x, SIDE)
            if ca is None or cb is None:
                raise ValueError((identity, y, x))
            pa, robust_scale = radial(ca)
            pb, _ = radial(cb, robust_scale)
            p0 += pa
            p40 += pb
    return np.sqrt(np.maximum(p40, 1e-300) / np.maximum(p0, 1e-300))


def model() -> dict:
    train = transfer(TRAIN, frozen.FLAT_0 + frozen.DETAIL_0)
    hold = transfer(HOLDOUT, frozen.FLAT_1 + frozen.DETAIL_1)
    frequencies = 0.5 * (EDGES[:-1] + EDGES[1:])

    def loss(observed: np.ndarray, sigma: float, amount: float) -> float:
        predicted = 1.0 + amount * (
            1.0 - np.exp(-2.0 * np.pi**2 * sigma**2 * frequencies**2)
        )
        return float(np.median(np.abs(np.log(observed) - np.log(predicted))))

    candidates = [
        (loss(train, float(s), float(a)), float(s), float(a))
        for s in np.round(np.arange(0.30, 2.501, 0.05), 2)
        for a in np.round(np.arange(0.00, 3.001, 0.05), 2)
    ]
    train_loss, sigma, amount = min(candidates)
    return {
        "sigma": sigma,
        "amount": amount,
        "train_loss": train_loss,
        "train_identity_loss": loss(train, 1.0, 0.0),
        "holdout_loss": loss(hold, sigma, amount),
        "holdout_identity_loss": loss(hold, 1.0, 0.0),
        "boundary": sigma in (0.30, 2.50) or amount in (0.00, 3.00),
    }


def strehl_pair(
    strehl: np.ndarray,
    comparator: np.ndarray,
    centre: Sequence[int],
    geometry: dict,
) -> tuple[np.ndarray, np.ndarray]:
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    y, x = map(float, centre)
    sy, sx = scale * y + gy, scale * x + gx
    side = int(round(SIDE / scale))
    s = baseline_check.centred(strehl, sy, sx, SIDE)
    c0 = baseline_check.centred(comparator, y, x, side)
    if s is None or c0 is None:
        raise ValueError(centre)
    shift = baseline_check.correction(
        baseline_check.ranks(s), baseline_check.resized_rank(c0, s.shape)
    )
    c = baseline_check.centred(
        comparator, y - shift[0] / scale, x - shift[1] / scale, side
    )
    if c is None:
        raise ValueError((centre, shift))
    return s, c


def main() -> int:
    selected = independent_sites()
    frozen_selected = {
        "flat_0": frozen.FLAT_0,
        "flat_1": frozen.FLAT_1,
        "detail_0": frozen.DETAIL_0,
        "detail_1": frozen.DETAIL_1,
    }
    if selected != frozen_selected:
        raise RuntimeError("independent input-only site set disagrees")
    model_result = model()

    p0 = green(PMAX0)
    p40 = green(PMAX40)
    st = green(STREHL)
    detail_rows = []
    flat_rows = []
    for kind, sites in (
        ("detail", frozen.DETAIL_0 + frozen.DETAIL_1),
        ("flat", frozen.FLAT_0 + frozen.FLAT_1),
    ):
        target = detail_rows if kind == "detail" else flat_rows
        for centre in sites:
            a, b, shift = registered(p0, p40, centre)
            sharpened = np.asarray(a, np.float64) + (
                np.asarray(a, np.float64)
                - gaussian(a, 1.0, mode="reflect", preserve_range=True)
            )
            target.append(
                {
                    "centre": centre,
                    "shift": shift,
                    "p0": q25(a),
                    "p40": q25(b),
                    "nominal": q25(sharpened),
                    "hull": hull_delta(a, b),
                }
            )

    geometry40 = baseline_check.geometry(STREHL, PMAX40)
    strehl_rows = []
    for centre in frozen.DETAIL_0 + frozen.DETAIL_1:
        s, c = strehl_pair(st, p40, centre, geometry40)
        sharpened = np.asarray(s, np.float64) + (
            np.asarray(s, np.float64)
            - gaussian(s, 1.0, mode="reflect", preserve_range=True)
        )
        strehl_rows.append(
            {
                "s": q25(s),
                "p40": q25(c, float(geometry40["scale"])),
                "nominal": q25(sharpened),
            }
        )
    result = {
        "site_freeze": "GREEN",
        "model": model_result,
        "pmax40_over_pmax0": summary(
            [math.log(row["p40"] / row["p0"]) for row in detail_rows]
        ),
        "nominal_pmax0_over_pmax40": summary(
            [math.log(row["nominal"] / row["p40"]) for row in detail_rows]
        ),
        "flat_power": summary(
            [math.log(row["p40"] / row["p0"]) for row in flat_rows]
        ),
        "flat_hull": mean_summary([row["hull"] for row in flat_rows]),
        "strehl_over_pmax40": summary(
            [math.log(row["s"] / row["p40"]) for row in strehl_rows]
        ),
        "nominal_strehl_over_pmax40": summary(
            [math.log(row["nominal"] / row["p40"]) for row in strehl_rows]
        ),
        "geometry40": geometry40,
        "unlicensed": "UNLICENSED_GT_0.25",
    }
    print("SHARPENING_CHECK_JSON=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
