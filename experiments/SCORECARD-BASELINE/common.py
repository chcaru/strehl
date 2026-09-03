from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from scipy.ndimage import fourier_shift
from scipy.signal.windows import tukey


LANE = Path(__file__).resolve().parent
ROOT = LANE.parents[1]
OUT = LANE / "out"
WORK = LANE / "work"
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
SOURCE_COMMIT = "4b60b1ba9f56abe92573451815e67f03725d19fa"
SEED = 20260902
Y_WEIGHTS = np.asarray([0.2627, 0.6780, 0.0593], dtype=np.float32)


def jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(jsonable(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path, block: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(block):
            digest.update(chunk)
    return digest.hexdigest()


def robust_sigma(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    median = float(np.median(values))
    return 1.4826 * float(np.median(np.abs(values - median)))


def window_2d(side: int, alpha: float = 0.25) -> np.ndarray:
    one = tukey(side, alpha=alpha, sym=True)
    return one[:, None] * one[None, :]


def frequency_grid(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    fy = np.fft.fftfreq(height)[:, None]
    fx = np.fft.rfftfreq(width)[None, :]
    return np.hypot(fx, fy)


def bandpass(image: np.ndarray, low: float, high: float) -> np.ndarray:
    image = np.asarray(image, dtype=np.float64)
    transformed = np.fft.rfft2(image - float(np.mean(image)))
    frequency = frequency_grid(image.shape)
    mask = (frequency >= low) & (frequency < high)
    return np.fft.irfft2(transformed * mask, s=image.shape)


def band_power(image: np.ndarray, low: float, high: float) -> float:
    response = bandpass(image, low, high)
    return float(np.mean(response * response))


def phase_translation(reference: np.ndarray, moving: np.ndarray) -> tuple[float, float]:
    from skimage.registration import phase_cross_correlation

    reference = np.asarray(reference, dtype=np.float32)
    moving = np.asarray(moving, dtype=np.float32)
    shift, _, _ = phase_cross_correlation(
        reference,
        moving,
        upsample_factor=20,
        normalization="phase",
    )
    return float(shift[0]), float(shift[1])


def translate_fourier(image: np.ndarray, shift_yx: tuple[float, float]) -> np.ndarray:
    transformed = np.fft.fftn(np.asarray(image, dtype=np.float64))
    return np.fft.ifftn(fourier_shift(transformed, shift_yx)).real


def affine_fit(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    valid = np.isfinite(x) & np.isfinite(y) & (x > 0.02) & (x < 0.98)
    x = x[valid]
    y = y[valid]
    if x.size < 100:
        raise ValueError("fewer than 100 affine-fit samples")
    design = np.column_stack([x, np.ones_like(x)])
    slope, intercept = np.linalg.lstsq(design, y, rcond=None)[0]
    residual = y - (slope * x + intercept)
    return {
        "samples": int(x.size),
        "slope": float(slope),
        "intercept": float(intercept),
        "max_abs_residual": float(np.max(np.abs(residual))),
        "rms_residual": float(np.sqrt(np.mean(residual * residual))),
    }


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


def m2_eta(output: np.ndarray, reference: np.ndarray, sigma_one: float) -> dict[str, float]:
    residual = bandpass(
        np.asarray(output, dtype=np.float64) - np.asarray(reference, dtype=np.float64),
        0.15,
        0.35,
    )
    sigma_residual = robust_sigma(residual)
    sigma_ideal = float(sigma_one) * math.sqrt(2.0 / 16.0)
    return {
        "sigma_residual": sigma_residual,
        "sigma_one": float(sigma_one),
        "sigma_ideal": sigma_ideal,
        "eta": sigma_residual / sigma_ideal if sigma_ideal > 0.0 else math.nan,
    }


def one_sided_quantile(values: Iterable[float], probability: float) -> float:
    data = np.asarray(list(values), dtype=np.float64)
    if data.size == 0:
        return math.nan
    return float(np.quantile(data, probability, method="linear"))
