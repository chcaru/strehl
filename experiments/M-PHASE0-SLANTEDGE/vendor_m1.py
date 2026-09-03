"""Source-pinned M1 functions vendored for the survivor audit.

The provenance checker requires each function AST below to equal the matching
definition in SCORECARD-BASELINE/common.py.  Keep candidate functions verbatim.
"""

from __future__ import annotations

import math
from typing import Any, Iterable

import numpy as np
from scipy.signal.windows import tukey


def window_2d(side: int, alpha: float = 0.25) -> np.ndarray:
    one = tukey(side, alpha=alpha, sym=True)
    return one[:, None] * one[None, :]


def frequency_grid(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    fy = np.fft.fftfreq(height)[:, None]
    fx = np.fft.rfftfreq(width)[None, :]
    return np.hypot(fx, fy)


def m1_tile(
    a: np.ndarray,
    b: np.ndarray,
    reference: np.ndarray,
    *,
    noise_floor: Iterable[float] | None = None,
) -> dict[str, Any]:
    if a.shape != b.shape or a.shape != reference.shape or a.shape[0] != a.shape[1]:
        raise ValueError("M1 needs equal square tiles")
    side = a.shape[0]
    window = window_2d(side)
    spectra = []
    for image in (a, b, reference):
        centered = (np.asarray(image, dtype=np.float64) - float(np.mean(image))) * window
        spectra.append(np.fft.rfft2(centered))
    fa, fb, fr = spectra
    frequency = frequency_grid(a.shape)
    floors = list(noise_floor) if noise_floor is not None else [0.0] * 10
    if len(floors) != 10:
        raise ValueError("M1 noise floor must have ten bins")
    rows = []
    for index in range(10):
        low = 0.15 + 0.01 * index
        high = low + 0.01
        selected = (frequency >= low) & (frequency < high)
        rr = float(np.sum(np.abs(fr[selected]) ** 2))
        numerator = float(
            np.real(np.sum(((fa[selected] + fb[selected]) * 0.5) * np.conj(fr[selected])))
        )
        gain = numerator / rr if rr > 0.0 else math.nan
        noise = max(
            0.5 * float(np.sum(np.abs(fa[selected] - fb[selected]) ** 2)),
            float(floors[index]),
        )
        detail = gain * gain * rr / noise if noise > 0.0 else math.inf
        denominator = math.sqrt(
            float(np.sum(np.abs(fa[selected]) ** 2))
            * float(np.sum(np.abs(fb[selected]) ** 2))
        )
        frc = (
            float(np.real(np.sum(fa[selected] * np.conj(fb[selected])))) / denominator
            if denominator > 0.0
            else math.nan
        )
        rows.append(
            {
                "low": low,
                "high": high,
                "gain": gain,
                "noise": noise,
                "reference_power": rr,
                "D": detail,
                "FRC": frc,
            }
        )
    cutoff = 0.15
    for row in rows:
        if row["D"] >= 1.0 and row["FRC"] >= 1.0 / 7.0:
            cutoff = row["high"]
        else:
            break
    return {
        "bins": rows,
        "f_licensed": min(cutoff, 0.25),
        "S_25": min(row["D"] for row in rows[5:10]),
        "gain_median": float(np.median([row["gain"] for row in rows])),
    }

