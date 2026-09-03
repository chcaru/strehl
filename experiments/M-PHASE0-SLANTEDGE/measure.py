"""Black-box measurements for M-PHASE0-SLANTEDGE.

This file owns plants and candidate adapters.  It contains no expected MTF50
values and never imports the independent checker.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter
from scipy.special import expit, ndtr


ROOT = Path(__file__).resolve().parents[2]
BASE_SIGMA = 1.50
BLUR_SIGMA = 0.75
IMPROVED_SIGMA = 1.20
USM_RADIUS = 1.00
USM_AMOUNT = 0.50
NOISE_SD = 0.02
ANGLE_DEG = 5.0
NOISE_SEEDS = tuple(range(2026090300, 2026090324))

SOURCE_PATHS = {
    "M88": ROOT / "experiments/M88-optical-ceiling/src/m88lib.py",
    "M104c": ROOT / "experiments/M104c-mtf/mtf.py",
    "M104c-render-adapter": ROOT / "experiments/M104c-mtf/mtf_real.py",
    "BUILD-RESAMP": ROOT / "experiments/BUILD-RESAMP/slanted_edge.py",
}


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M88 = load_module("mphase0_slantedge_m88", SOURCE_PATHS["M88"])
M104 = load_module("mphase0_slantedge_m104", SOURCE_PATHS["M104c"])
BUILD = load_module("mphase0_slantedge_build", SOURCE_PATHS["BUILD-RESAMP"])


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertical_edge(sigma: float, angle_deg: float = ANGLE_DEG,
                  h: int = 256, w: int = 160) -> np.ndarray:
    """Neutral Gaussian edge for near-vertical M104c/BUILD measurement."""
    yy, xx = np.mgrid[0:h, 0:w]
    slope = math.tan(math.radians(angle_deg))
    intercept = w / 2.0 - slope * (h - 1) / 2.0
    distance = (xx - (slope * yy + intercept)) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def horizontal_edge(sigma: float, angle_deg: float = ANGLE_DEG,
                    h: int = 384, w: int = 1024) -> np.ndarray:
    """Neutral Gaussian edge for M88's near-horizontal RAW geometry."""
    yy, xx = np.mgrid[0:h, 0:w]
    slope = math.tan(math.radians(angle_deg))
    intercept = h / 2.0 - slope * (w - 1) / 2.0
    distance = (yy - (slope * xx + intercept)) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def processed_arms(factory) -> dict[str, np.ndarray]:
    base = factory(BASE_SIGMA, ANGLE_DEG)
    blur = gaussian_filter(base, BLUR_SIGMA, mode="nearest", truncate=6.0)
    low = gaussian_filter(base, USM_RADIUS, mode="nearest", truncate=6.0)
    sharp = base + USM_AMOUNT * (base - low)  # deliberately unclipped float
    return {
        "base": base,
        "identity": base.copy(),
        "blur": blur,
        "improvement": factory(IMPROVED_SIGMA, ANGLE_DEG),
        "sharpen": sharp,
        "affine": 1.7 * base + 0.13,
        "gamma3": np.power(base, 3.0),
        "logistic": expit(10.0 * (base - 0.5)),
        "unlicensed": factory(0.60, ANGLE_DEG),
    }


def value_record(value: float, angle: float | None = None) -> dict:
    if not np.isfinite(value):
        return {"status": "REFUSED", "reason": "non-finite value"}
    out = {"status": "VALUE", "mtf50_cyc_native_px": float(value)}
    if angle is not None:
        out["angle_deg"] = float(angle)
    return out


def refused(exc) -> dict:
    return {"status": "REFUSED", "reason": f"{type(exc).__name__}: {exc}"}


def first_crossing(freq: np.ndarray, mtf: np.ndarray) -> float:
    f = np.asarray(freq, dtype=float)
    m = np.asarray(mtf, dtype=float)
    ok = np.isfinite(f) & np.isfinite(m)
    f, m = f[ok], m[ok]
    for i in range(1, len(m)):
        if m[i] <= 0.5 <= m[i - 1]:
            frac = (m[i - 1] - 0.5) / (m[i - 1] - m[i])
            return float(f[i - 1] + frac * (f[i] - f[i - 1]))
    return float("nan")


def m104_measure(img: np.ndarray) -> dict:
    try:
        r = M104.mtf_from_roi(img)
        return value_record(r["mtf50"], r["angle"])
    except Exception as exc:  # an explicit refusal is part of the result
        return refused(exc)


def measure_m104() -> dict:
    arms = processed_arms(vertical_edge)
    measured = {name: m104_measure(img) for name, img in arms.items()}
    noise = []
    for seed in NOISE_SEEDS:
        rng = np.random.default_rng(seed)
        noise.append(m104_measure(arms["base"] + rng.normal(
            0.0, NOISE_SD, arms["base"].shape)))
    angles = [
        {"plant_deg": a, "measurement": m104_measure(
            vertical_edge(BASE_SIGMA, a))}
        for a in (0.5, 1.0, 5.0, 12.0)
    ]
    return {
        "arms": measured,
        "noise": noise,
        "angles": angles,
        "published_angle_gate_deg": [2.0, 12.0],
        "sharpening_warning": None,
        "licensing_censor": None,
        "domain": "rendered RGB TIFF green channel in mtf_real.py",
        "demosaic_or_render_path": True,
        "sharpen_range": [float(arms["sharpen"].min()),
                          float(arms["sharpen"].max())],
    }


def build_measure(img: np.ndarray, line=None) -> dict:
    try:
        r = BUILD.measure_roi(img, line=line)
        if r is None:
            return {"status": "REFUSED", "reason": "measure_roi returned None"}
        return value_record(r["mtf50"], r["angle"])
    except Exception as exc:
        return refused(exc)


def measure_build() -> dict:
    arms = processed_arms(vertical_edge)
    fitted = BUILD.measure_roi(arms["base"])
    if fitted is None:
        raise RuntimeError("BUILD-RESAMP refused the base edge")
    line = (fitted["slope"], fitted["icept"])
    measured = {name: build_measure(img, line=line)
                for name, img in arms.items()}
    noise = []
    for seed in NOISE_SEEDS:
        rng = np.random.default_rng(seed)
        noise.append(build_measure(arms["base"] + rng.normal(
            0.0, NOISE_SD, arms["base"].shape), line=line))
    angles = [
        {"plant_deg": a, "measurement": build_measure(
            vertical_edge(BASE_SIGMA, a))}
        for a in (0.5, 1.0, 5.0, 12.0)
    ]
    return {
        "arms": measured,
        "noise": noise,
        "angles": angles,
        "published_angle_gate_deg": [2.0, 10.0],
        "sharpening_warning": None,
        "licensing_censor": None,
        "domain": "rendered RGB/TIFF raster green channel",
        "demosaic_or_render_path": True,
        "sharpen_range": [float(arms["sharpen"].min()),
                          float(arms["sharpen"].max())],
    }


def m88_line(img: np.ndarray):
    sub, xs, ys = M88.green_sites(img, "G1")
    line = M88.fit_edge_line(sub, xs, ys, axis="horizontal")
    xx, yy = np.meshgrid(xs, ys)
    return line, xx, yy


def m88_measure(img: np.ndarray, line, xx, yy) -> dict:
    try:
        sub, _, _ = M88.green_sites(img, "G1")
        r = M88.sfr_from_sites(
            sub.ravel(), xx.ravel(), yy.ravel(), line,
            bin_um=0.64, half_width_um=96.0, taper_frac=0.10,
            detrend_iters=2,
        )
        native_freq = r["freq_cymm"] * M88.PITCH_MM
        return value_record(first_crossing(native_freq, r["mtf"]),
                            line["angle_deg"])
    except Exception as exc:
        return refused(exc)


def m88_angle_measure(angle: float) -> dict:
    img = horizontal_edge(BASE_SIGMA, angle)
    try:
        line, xx, yy = m88_line(img)
        return m88_measure(img, line, xx, yy)
    except Exception as exc:
        return refused(exc)


def measure_m88() -> dict:
    arms = processed_arms(horizontal_edge)
    line, xx, yy = m88_line(arms["base"])
    measured = {name: m88_measure(img, line, xx, yy)
                for name, img in arms.items()}
    noise = []
    for seed in NOISE_SEEDS:
        rng = np.random.default_rng(seed)
        noise.append(m88_measure(arms["base"] + rng.normal(
            0.0, NOISE_SD, arms["base"].shape), line, xx, yy))
    angles = [
        {"plant_deg": a, "measurement": m88_angle_measure(a)}
        for a in (0.5, 1.0, 5.0, 12.0)
    ]
    return {
        "arms": measured,
        "noise": noise,
        "angles": angles,
        "published_angle_gate_deg": [0.4, 12.0],
        "sharpening_warning": None,
        "licensing_censor": None,
        "domain": "linear RAW Bayer G1 in canonical load_active path",
        "demosaic_or_render_path": False,
        "sharpen_range": [float(arms["sharpen"].min()),
                          float(arms["sharpen"].max())],
    }


def main() -> int:
    result = {
        "schema": 1,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "threads": 1,
            "captures_opened": 0,
        },
        "parameters": {
            "base_sigma_px": BASE_SIGMA,
            "added_blur_sigma_px": BLUR_SIGMA,
            "improved_sigma_px": IMPROVED_SIGMA,
            "usm_radius_px": USM_RADIUS,
            "usm_amount": USM_AMOUNT,
            "noise_sd": NOISE_SD,
            "noise_seeds": list(NOISE_SEEDS),
            "angle_deg": ANGLE_DEG,
        },
        "sources": {
            name: {
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(path),
            }
            for name, path in SOURCE_PATHS.items()
        },
        "instruments": {
            "M88": measure_m88(),
            "M104c": measure_m104(),
            "BUILD-RESAMP": measure_build(),
        },
    }
    print(json.dumps(result, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
