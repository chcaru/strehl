"""M129 synthetic commissioning battery.

This script reads no capture. It reuses the validated M5 instrument unchanged and
writes only out/commission.json and out/commission.txt.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import defaultdict

sys.dont_write_bytecode = True

import numpy as np
from scipy import stats
from scipy.optimize import brentq


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
M5_DIR = ROOT.parent / "m5-diffraction"
sys.path.insert(0, str(M5_DIR))

import m5_lib as L  # noqa: E402
import m5_synthetic as M5S  # noqa: E402


# Fixed acquisition and estimator choices. They never vary by cell.
ISO = 100
LATTICE = "GQ"
WINDOW = "hann"
ROI = int(M5S.ROI)
TILE = int(M5S.TILE)
CONTRAST = float(inspect.signature(M5S.make_scene).parameters["contrast"].default)
FINE = 2
SENSOR_N = 1040
FINE_N = SENSOR_N * FINE
CENTRE = SENSOR_N // 2
REACH_FRACTION = 0.90
DEPENDENCE_ALPHA = 0.01

FC_MM_GRID = [25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0, 65.0]
ALPHAS = [1.5, 2.0, 2.5, 3.0, 3.5]
SIGNALS = [484.0, 705.0, 1193.0, 2310.0, 4377.0]
APERTURES = [
    ("f5.6", 5.6, 4377.0),
    ("f8", 8.0, 2310.0),
    ("f11", 11.0, 1193.0),
    ("f14", 14.0, 705.0),
    ("f18", 18.0, 484.0),
]
HYPOTHESES = {
    "H2": 3.0763,
    "H3": 2.4020,
}
LADDER_ALPHA = 2.5

Q1_SEEDS = list(range(129001, 129009))
LADDER_SEEDS = list(range(229001, 229017))
NULL_SEEDS = list(range(329001, 329331))
POTENCY_SEED = 429001
BOOTSTRAP_SEED = 529001
BOOTSTRAP_REPS = 2000

OUT_JSON = ROOT / "out" / "commission.json"
OUT_TXT = ROOT / "out" / "commission.txt"
PROTECTED = [
    M5_DIR / "m5_lib.py",
    M5_DIR / "m5_synthetic.py",
    M5_DIR / "m5_selftest.py",
]


def progress(message: str) -> None:
    print(message, flush=True)


def finite_or_none(value):
    if value is None:
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def clean_json(value):
    if isinstance(value, dict):
        return {str(k): clean_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean_json(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean_json(value.tolist())
    if isinstance(value, (np.floating, float)):
        return finite_or_none(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def repo_root() -> Path:
    run = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(run.stdout.strip())


def protected_git_status(repo: Path) -> str:
    rel = [str(path.relative_to(repo)) for path in PROTECTED]
    run = subprocess.run(
        ["git", "--no-pager", "status", "--short", "--", *rel],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return run.stdout.strip()


def run_m5_selftest() -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = time.perf_counter()
    run = subprocess.run(
        [sys.executable, "-B", str(M5_DIR / "m5_selftest.py")],
        cwd=M5_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    lines = (run.stdout + run.stderr).splitlines()
    return {
        "returncode": run.returncode,
        "passed": run.returncode == 0,
        "elapsed_seconds": time.perf_counter() - started,
        "tail": lines[-8:],
    }


def cyc_mm_to_sensor_cyc_px(value_mm: float) -> float:
    """Numerically invert m5_lib's registered sensor-to-mm conversion."""
    target = float(value_mm)
    return float(
        brentq(
            lambda value: float(L.sensor_cyc_px_to_cyc_mm(value)) - target,
            0.0,
            1.0,
        )
    )


FC_SENSOR_GRID = [cyc_mm_to_sensor_cyc_px(value) for value in FC_MM_GRID]


def conversion_check() -> dict:
    recovered = [float(L.sensor_cyc_px_to_cyc_mm(value)) for value in FC_SENSOR_GRID]
    errors = [got - want for got, want in zip(recovered, FC_MM_GRID)]
    return {
        "input_cyc_mm": FC_MM_GRID,
        "sensor_cyc_px": FC_SENSOR_GRID,
        "roundtrip_cyc_mm": recovered,
        "max_abs_roundtrip_error_cyc_mm": max(abs(value) for value in errors),
    }


def frequency_grid() -> tuple[np.ndarray, np.ndarray]:
    fy = np.fft.fftfreq(FINE_N, d=1.0 / FINE)[:, None]
    fx = np.fft.rfftfreq(FINE_N, d=1.0 / FINE)[None, :]
    radius = np.hypot(fy, fx).astype(np.float32)
    pixel = np.asarray(L.mtf_pixel(radius), dtype=np.float32)
    return radius, pixel


R_FINE, PIXEL_MTF = frequency_grid()
OTF_CACHE: dict[float, np.ndarray] = {}


def optical_mtf(fc_sensor: float) -> np.ndarray:
    key = round(float(fc_sensor), 12)
    if key not in OTF_CACHE:
        diffraction = np.asarray(L.mtf_diffraction(R_FINE, fc_sensor), dtype=np.float32)
        OTF_CACHE[key] = diffraction * PIXEL_MTF
    return OTF_CACHE[key]


def object_fft(alpha: float, seed: int) -> np.ndarray:
    """Power-law object field on a 2x fine grid, normalised before the optics."""
    rng = np.random.default_rng(seed)
    white = rng.standard_normal((FINE_N, FINE_N), dtype=np.float32)
    spectrum = np.fft.rfft2(white)
    del white

    shape = np.zeros_like(R_FINE, dtype=np.float32)
    nonzero = R_FINE > 0.0
    shape[nonzero] = R_FINE[nonzero] ** (-float(alpha) / 2.0)
    spectrum *= shape
    del shape

    field = np.fft.irfft2(spectrum, s=(FINE_N, FINE_N))
    scale = float(field.std())
    del field
    if not math.isfinite(scale) or scale <= 0.0:
        raise RuntimeError("synthetic object field has invalid scale")
    spectrum /= scale
    return spectrum


def sampled_optical_field(spectrum: np.ndarray, fc_sensor: float) -> np.ndarray:
    fine = np.fft.irfft2(
        spectrum * optical_mtf(fc_sensor),
        s=(FINE_N, FINE_N),
    )
    sensor = np.asarray(fine[0::FINE, 0::FINE], dtype=np.float64)
    del fine
    if sensor.shape != (SENSOR_N, SENSOR_N):
        raise RuntimeError(f"unexpected sampled shape {sensor.shape}")
    return sensor


def patch_from_field(
    field: np.ndarray,
    mean_dn: float,
    noise_seed: int,
    *,
    noise_sigma: float | None = None,
) -> tuple[np.ndarray, dict]:
    rng = np.random.default_rng(noise_seed)
    signal = float(mean_dn) * (1.0 + CONTRAST * field)
    model = L.noise_model_var(float(mean_dn), ISO)
    sigma = math.sqrt(float(model["var"])) if noise_sigma is None else float(noise_sigma)
    noisy = signal + rng.normal(0.0, sigma, field.shape)
    raw_float = noisy + L.BLACK_LEVEL
    low_clip = float(np.mean(raw_float < 1.0))
    high_clip = float(np.mean(raw_float > L.WHITE_LEVEL))
    raw = np.rint(np.clip(raw_float, 1.0, L.WHITE_LEVEL)).astype(np.uint16)
    patch = L.crop_lattice(
        raw,
        LATTICE,
        CENTRE,
        CENTRE,
        ROI,
        bounds=(SENSOR_N, SENSOR_N),
    )
    return patch, {
        "mean_dn": float(mean_dn),
        "noise_sigma_dn": sigma,
        "noise_variance_dn2": sigma * sigma,
        "noise_model": model,
        "low_clip_fraction": low_clip,
        "high_clip_fraction": high_clip,
    }


def estimate_patch(patch: np.ndarray, *, model_fit: bool = False) -> dict:
    f, p, counts = L.spectrum(patch, LATTICE, tile=TILE, window=WINDOW)
    knee = L.knee(f, p, counts, TILE, ROI, LATTICE, WINDOW)
    out = {
        "f": f,
        "p": p,
        "counts": counts,
        "knee": knee,
        "f_c": finite_or_none(knee.get("f_c")),
    }
    if model_fit:
        out["model_fit"] = L.knee_model_fit(f, p, counts)
    return out


def fit_planted_alpha(
    f: np.ndarray,
    p: np.ndarray,
    counts: np.ndarray,
    fc_sensor: float,
) -> dict:
    top = f >= 0.8 * f[-1]
    floor = float(np.median(p[top]))
    transfer = (
        np.asarray(L.mtf_diffraction(f, fc_sensor), dtype=float)
        * np.asarray(L.mtf_pixel(f), dtype=float)
    ) ** 2
    scene = p - floor
    band = (
        (f >= 0.035)
        & (f <= 0.085)
        & (scene > 0.0)
        & (transfer > 1e-8)
    )
    x = np.log(f[band])
    y = np.log(scene[band] / transfer[band])
    w = counts[band]
    X = np.column_stack([np.ones_like(x), x])
    xtwx = X.T @ (w[:, None] * X)
    beta = np.linalg.solve(xtwx, X.T @ (w * y))
    resid = y - X @ beta
    dof = max(1, len(y) - 2)
    s2 = float(np.sum(w * resid * resid) / dof)
    cov = s2 * np.linalg.inv(xtwx)
    return {
        "alpha": float(-beta[1]),
        "alpha_se": float(math.sqrt(max(cov[1, 1], 0.0))),
        "floor": floor,
        "bins": int(np.sum(band)),
        "fit_band_sensor_cyc_px": [0.035, 0.085],
    }


def run_potency() -> dict:
    planted_alpha = 2.5
    planted_mm = 35.0
    planted_fc = cyc_mm_to_sensor_cyc_px(planted_mm)
    spectrum = object_fft(planted_alpha, POTENCY_SEED)
    field = sampled_optical_field(spectrum, planted_fc)
    del spectrum
    patch, noise = patch_from_field(
        field,
        5000.0,
        POTENCY_SEED + 1,
        noise_sigma=0.5,
    )
    estimate = estimate_patch(patch, model_fit=True)
    alpha = fit_planted_alpha(
        estimate["f"],
        estimate["p"],
        estimate["counts"],
        planted_fc,
    )
    crossing = estimate["f_c"]
    fit = estimate["model_fit"]
    crossing_error = (
        crossing / planted_fc - 1.0 if crossing is not None else float("nan")
    )
    fit_fc = finite_or_none(fit.get("f_c")) if fit.get("ok") else None
    fit_error = fit_fc / planted_fc - 1.0 if fit_fc is not None else float("nan")
    alpha_error = alpha["alpha"] - planted_alpha
    passed = (
        crossing is not None
        and abs(crossing_error) <= 0.05
        and fit_fc is not None
        and abs(fit_error) <= 0.03
        and abs(alpha_error) <= 0.15
    )
    return {
        "passed": bool(passed),
        "seed": POTENCY_SEED,
        "planted_alpha": planted_alpha,
        "recovered_alpha": alpha["alpha"],
        "alpha_error": alpha_error,
        "alpha_fit": alpha,
        "planted_fc_sensor_cyc_px": planted_fc,
        "planted_fc_cyc_mm": planted_mm,
        "crossing_fc_sensor_cyc_px": crossing,
        "crossing_error_fraction": crossing_error,
        "model_fit_fc_sensor_cyc_px": fit_fc,
        "model_fit_error_fraction": fit_error,
        "dynamic_range": finite_or_none(estimate["knee"].get("dynamic_range")),
        "crossing_gate_has_signal": bool(estimate["knee"].get("has_signal")),
        "noise": noise,
        "fixed_pass_limits": {
            "abs_crossing_error_fraction": 0.05,
            "abs_model_fit_error_fraction": 0.03,
            "abs_alpha_error": 0.15,
        },
    }


def run_null() -> dict:
    raw_fires = 0
    gated_fires = 0
    dynamic_ranges = []
    fcs = []
    per_signal = {}
    for signal_index, signal in enumerate(SIGNALS):
        per_signal[str(int(signal))] = {"trials": 0, "raw": 0, "gated": 0}
    for index, seed in enumerate(NULL_SEEDS):
        signal = SIGNALS[index % len(SIGNALS)]
        model = L.noise_model_var(signal, ISO)
        sigma = math.sqrt(float(model["var"]))
        rng = np.random.default_rng(seed)
        patch = np.rint(signal + rng.normal(0.0, sigma, (ROI, ROI))) - signal
        estimate = estimate_patch(patch)
        knee = estimate["knee"]
        raw = estimate["f_c"] is not None
        gated = raw and bool(knee.get("has_signal"))
        raw_fires += int(raw)
        gated_fires += int(gated)
        dynamic_ranges.append(float(knee["dynamic_range"]))
        fcs.append(estimate["f_c"])
        cell = per_signal[str(int(signal))]
        cell["trials"] += 1
        cell["raw"] += int(raw)
        cell["gated"] += int(gated)
    trials = len(NULL_SEEDS)
    return {
        "trials": trials,
        "seeds": NULL_SEEDS,
        "signal_levels_dn": SIGNALS,
        "raw_false_detections": raw_fires,
        "raw_false_detection_rate": raw_fires / trials,
        "gated_false_detections": gated_fires,
        "gated_false_detection_rate": gated_fires / trials,
        "dynamic_range_mean": float(np.mean(dynamic_ranges)),
        "dynamic_range_max": float(np.max(dynamic_ranges)),
        "raw_detected_fc_sensor_cyc_px": fcs,
        "per_signal": per_signal,
        "historical_m5": {
            "raw_false_detections": 113,
            "trials": 330,
            "raw_false_detection_rate": 113 / 330,
            "gated_false_detections": 0,
            "gated_false_detection_rate": 0.0,
        },
    }


def q1_noise_seed(rep_index: int, alpha_index: int, fc_index: int, signal_index: int) -> int:
    return 50_000_000 + rep_index * 100_000 + alpha_index * 10_000 + fc_index * 100 + signal_index


def run_q1() -> list[dict]:
    observations = []
    total = len(ALPHAS) * len(Q1_SEEDS)
    done = 0
    for alpha_index, alpha in enumerate(ALPHAS):
        for rep_index, seed in enumerate(Q1_SEEDS):
            done += 1
            progress(
                f"Q1 object block {done}/{total}: alpha={alpha:.1f}, seed={seed}"
            )
            spectrum = object_fft(alpha, seed)
            for fc_index, (fc_mm, fc_sensor) in enumerate(
                zip(FC_MM_GRID, FC_SENSOR_GRID)
            ):
                field = sampled_optical_field(spectrum, fc_sensor)
                for signal_index, signal in enumerate(SIGNALS):
                    patch, noise = patch_from_field(
                        field,
                        signal,
                        q1_noise_seed(
                            rep_index,
                            alpha_index,
                            fc_index,
                            signal_index,
                        ),
                    )
                    estimate = estimate_patch(patch)
                    recovered = estimate["f_c"]
                    gated = recovered is not None and bool(
                        estimate["knee"].get("has_signal")
                    )
                    bias = (
                        recovered / fc_sensor - 1.0
                        if recovered is not None
                        else None
                    )
                    observations.append(
                        {
                            "seed": seed,
                            "alpha": alpha,
                            "signal_dn": signal,
                            "fc_cyc_mm": fc_mm,
                            "fc_sensor_cyc_px": fc_sensor,
                            "recovered_fc_sensor_cyc_px": recovered,
                            "bias_fraction": bias,
                            "raw_detected": recovered is not None,
                            "gated_detected": gated,
                            "dynamic_range": finite_or_none(
                                estimate["knee"].get("dynamic_range")
                            ),
                            "saturated": bool(estimate["knee"].get("saturated")),
                            "kappa": finite_or_none(estimate["knee"].get("kappa")),
                            "noise_sigma_dn": noise["noise_sigma_dn"],
                            "low_clip_fraction": noise["low_clip_fraction"],
                            "high_clip_fraction": noise["high_clip_fraction"],
                        }
                    )
                del field
            del spectrum
    return observations


def mean_sd_se(values: list[float]) -> dict:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    n = len(array)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "se": None}
    sd = float(np.std(array, ddof=1)) if n > 1 else 0.0
    return {
        "n": n,
        "mean": float(np.mean(array)),
        "sd": sd,
        "se": sd / math.sqrt(n),
    }


def summarise_q1(observations: list[dict]) -> tuple[list[dict], np.ndarray]:
    grouped = defaultdict(list)
    seed_index = {seed: index for index, seed in enumerate(Q1_SEEDS)}
    fc_index = {value: index for index, value in enumerate(FC_MM_GRID)}
    alpha_index = {value: index for index, value in enumerate(ALPHAS)}
    signal_index = {value: index for index, value in enumerate(SIGNALS)}
    matrix = np.full(
        (len(Q1_SEEDS), len(FC_MM_GRID), len(ALPHAS), len(SIGNALS)),
        np.nan,
    )
    for row in observations:
        key = (row["fc_cyc_mm"], row["alpha"], row["signal_dn"])
        grouped[key].append(row)
        if row["gated_detected"] and row["bias_fraction"] is not None:
            matrix[
                seed_index[row["seed"]],
                fc_index[row["fc_cyc_mm"]],
                alpha_index[row["alpha"]],
                signal_index[row["signal_dn"]],
            ] = row["bias_fraction"]

    cells = []
    for alpha in ALPHAS:
        for signal in SIGNALS:
            for fc_mm in FC_MM_GRID:
                rows = grouped[(fc_mm, alpha, signal)]
                biases = [
                    row["bias_fraction"]
                    for row in rows
                    if row["gated_detected"] and row["bias_fraction"] is not None
                ]
                recovered = [
                    row["recovered_fc_sensor_cyc_px"]
                    for row in rows
                    if row["gated_detected"]
                    and row["recovered_fc_sensor_cyc_px"] is not None
                ]
                bias_stats = mean_sd_se(biases)
                rec_stats = mean_sd_se(recovered)
                cells.append(
                    {
                        "alpha": alpha,
                        "signal_dn": signal,
                        "fc_cyc_mm": fc_mm,
                        "fc_sensor_cyc_px": cyc_mm_to_sensor_cyc_px(fc_mm),
                        "seeds": [row["seed"] for row in rows],
                        "raw_detections": sum(row["raw_detected"] for row in rows),
                        "gated_detections": sum(
                            row["gated_detected"] for row in rows
                        ),
                        "saturated_count": sum(row["saturated"] for row in rows),
                        "bias": bias_stats,
                        "recovered_fc": rec_stats,
                        "biases_fraction": biases,
                        "recovered_fc_sensor_cyc_px": recovered,
                        "dynamic_range_mean": float(
                            np.mean([row["dynamic_range"] for row in rows])
                        ),
                        "noise_sigma_dn": rows[0]["noise_sigma_dn"],
                        "max_high_clip_fraction": max(
                            row["high_clip_fraction"] for row in rows
                        ),
                        "max_low_clip_fraction": max(
                            row["low_clip_fraction"] for row in rows
                        ),
                    }
                )
    return cells, matrix


def friedman_factor(matrix: np.ndarray, factor_axis: int, labels: list) -> dict:
    other = tuple(axis for axis in range(1, matrix.ndim) if axis != factor_axis)
    marginal = np.nanmean(matrix, axis=other)
    complete = np.all(np.isfinite(marginal), axis=1)
    data = marginal[complete]
    if data.shape[0] < 2:
        return {
            "test": "Friedman repeated-measures",
            "labels": labels,
            "n_seed_blocks": int(data.shape[0]),
            "p": None,
            "depends": None,
        }
    result = stats.friedmanchisquare(*[data[:, index] for index in range(data.shape[1])])
    chi2 = float(result.statistic)
    p = float(result.pvalue)
    means = np.mean(data, axis=0)
    return {
        "test": "Friedman repeated-measures",
        "labels": labels,
        "n_seed_blocks": int(data.shape[0]),
        "chi2": chi2,
        "p": p,
        "kendall_w": chi2 / (data.shape[0] * (data.shape[1] - 1)),
        "marginal_bias_fraction": means.tolist(),
        "marginal_span_fraction": float(np.max(means) - np.min(means)),
        "depends": bool(p < DEPENDENCE_ALPHA),
        "decision_alpha": DEPENDENCE_ALPHA,
    }


def q1_dependence(matrix: np.ndarray) -> dict:
    return {
        "fc": friedman_factor(matrix, 1, FC_MM_GRID),
        "alpha": friedman_factor(matrix, 2, ALPHAS),
        "signal": friedman_factor(matrix, 3, SIGNALS),
    }


def pava(values: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    y = np.asarray(values, dtype=float)
    w = np.ones_like(y) if weights is None else np.asarray(weights, dtype=float)
    blocks = []
    for index, (value, weight) in enumerate(zip(y, w)):
        blocks.append([index, index, float(weight), float(value)])
        while len(blocks) >= 2 and blocks[-2][3] > blocks[-1][3]:
            left = blocks[-2]
            right = blocks[-1]
            total = left[2] + right[2]
            mean = (left[3] * left[2] + right[3] * right[2]) / total
            blocks[-2:] = [[left[0], right[1], total, mean]]
    out = np.empty_like(y)
    for start, end, _, value in blocks:
        out[start : end + 1] = value
    return out


def collapse_duplicates(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unique = []
    values = []
    start = 0
    while start < len(x):
        end = start + 1
        while end < len(x) and abs(x[end] - x[start]) < 1e-12:
            end += 1
        unique.append(float(np.mean(x[start:end])))
        values.append(float(np.mean(y[start:end])))
        start = end
    return np.asarray(unique), np.asarray(values)


def interp_extrap(x: np.ndarray, y: np.ndarray, value: float) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2:
        return float("nan")
    if value < x[0]:
        slope = (y[1] - y[0]) / (x[1] - x[0])
        return float(y[0] + slope * (value - x[0]))
    if value > x[-1]:
        slope = (y[-1] - y[-2]) / (x[-1] - x[-2])
        return float(y[-1] + slope * (value - x[-1]))
    return float(np.interp(value, x, y))


def build_calibration(
    observations: list[dict],
    *,
    seed_weights: dict[int, int] | None = None,
    exclude_seed: int | None = None,
) -> dict:
    calibration = {}
    for alpha in ALPHAS:
        for signal in SIGNALS:
            recovered_means = []
            counts = []
            for fc_mm in FC_MM_GRID:
                values = []
                for row in observations:
                    if (
                        row["alpha"] != alpha
                        or row["signal_dn"] != signal
                        or row["fc_cyc_mm"] != fc_mm
                        or not row["gated_detected"]
                        or row["recovered_fc_sensor_cyc_px"] is None
                        or row["seed"] == exclude_seed
                    ):
                        continue
                    weight = (
                        seed_weights.get(row["seed"], 0)
                        if seed_weights is not None
                        else 1
                    )
                    values.extend(
                        [row["recovered_fc_sensor_cyc_px"]] * int(weight)
                    )
                recovered_means.append(
                    float(np.mean(values)) if values else float("nan")
                )
                counts.append(len(values))
            raw = np.asarray(recovered_means)
            valid = np.isfinite(raw)
            true_fc = np.asarray(FC_SENSOR_GRID)[valid]
            raw = raw[valid]
            count_array = np.asarray(counts, dtype=float)[valid]
            if len(raw) < 2:
                calibration[(alpha, signal)] = None
                continue
            violations = int(np.sum(np.diff(raw) < 0.0))
            monotone = pava(raw, np.maximum(count_array, 1.0))
            inverse_x, inverse_y = collapse_duplicates(monotone, true_fc)
            calibration[(alpha, signal)] = {
                "true_fc": true_fc,
                "recovered_fc_raw": raw,
                "recovered_fc_monotone": monotone,
                "inverse_recovered_fc": inverse_x,
                "inverse_true_fc": inverse_y,
                "monotonicity_violations": violations,
            }
    return calibration


def correct_fc(
    recovered_fc: float | None,
    alpha: float,
    signal: float,
    calibration: dict,
) -> tuple[float | None, dict]:
    if recovered_fc is None:
        return None, {"reason": "no recovered cutoff"}
    item = calibration.get((float(alpha), float(signal)))
    if item is None or len(item["inverse_recovered_fc"]) < 2:
        return None, {"reason": "calibration unavailable"}
    x = item["inverse_recovered_fc"]
    y = item["inverse_true_fc"]
    corrected = interp_extrap(x, y, float(recovered_fc))
    return corrected, {
        "extrapolated": bool(recovered_fc < x[0] or recovered_fc > x[-1]),
        "calibration_recovered_range": [float(x[0]), float(x[-1])],
        "monotonicity_violations": item["monotonicity_violations"],
    }


def predicted_bias(
    true_fc: float,
    alpha: float,
    signal: float,
    calibration: dict,
) -> float:
    item = calibration.get((float(alpha), float(signal)))
    if item is None:
        return float("nan")
    recovered = interp_extrap(item["true_fc"], item["recovered_fc_monotone"], true_fc)
    return recovered / true_fc - 1.0


def run_q3(observations: list[dict]) -> tuple[dict, dict]:
    loo = {
        seed: build_calibration(observations, exclude_seed=seed)
        for seed in Q1_SEEDS
    }
    grouped = defaultdict(list)
    all_rows = []
    for row in observations:
        if not row["gated_detected"]:
            continue
        corrected, detail = correct_fc(
            row["recovered_fc_sensor_cyc_px"],
            row["alpha"],
            row["signal_dn"],
            loo[row["seed"]],
        )
        error = (
            corrected / row["fc_sensor_cyc_px"] - 1.0
            if corrected is not None
            else None
        )
        key = (row["fc_cyc_mm"], row["alpha"], row["signal_dn"])
        if error is not None and math.isfinite(error):
            grouped[key].append(error)
        all_rows.append(
            {
                "seed": row["seed"],
                "fc_cyc_mm": row["fc_cyc_mm"],
                "alpha": row["alpha"],
                "signal_dn": row["signal_dn"],
                "corrected_fc_sensor_cyc_px": corrected,
                "corrected_error_fraction": error,
                "detail": detail,
            }
        )

    cells = []
    pooled_numerator = 0.0
    pooled_denom = 0
    for alpha in ALPHAS:
        for signal in SIGNALS:
            for fc_mm in FC_MM_GRID:
                values = grouped[(fc_mm, alpha, signal)]
                summary = mean_sd_se(values)
                if summary["n"] > 1:
                    pooled_numerator += (summary["n"] - 1) * summary["sd"] ** 2
                    pooled_denom += summary["n"] - 1
                cells.append(
                    {
                        "fc_cyc_mm": fc_mm,
                        "alpha": alpha,
                        "signal_dn": signal,
                        "corrected_error": summary,
                        "mean_within_5_percent": bool(
                            summary["n"] >= 6
                            and summary["mean"] is not None
                            and abs(summary["mean"]) <= 0.05
                        ),
                    }
                )
    pooled = math.sqrt(pooled_numerator / pooled_denom) if pooled_denom else float("nan")
    valid_means = [
        abs(cell["corrected_error"]["mean"])
        for cell in cells
        if cell["corrected_error"]["mean"] is not None
    ]
    individual = [
        abs(row["corrected_error_fraction"])
        for row in all_rows
        if row["corrected_error_fraction"] is not None
    ]
    pass_cells = [cell["mean_within_5_percent"] for cell in cells]
    result = {
        "method": (
            "Leave-one-seed-out inverse calibration. For each alpha and signal, "
            "the mean recovered cutoff is monotonised only when needed, then the "
            "recovered-to-planted curve is inverted with linear interpolation."
        ),
        "cells": cells,
        "all_cell_means_within_5_percent": bool(all(pass_cells)),
        "cells_passing": int(sum(pass_cells)),
        "cells_total": len(cells),
        "worst_abs_cell_mean_error_fraction": max(valid_means) if valid_means else None,
        "fraction_individual_estimates_within_5_percent": (
            float(np.mean(np.asarray(individual) <= 0.05)) if individual else None
        ),
        "pooled_within_cell_residual_sd_fraction": pooled,
        "uncertainty_to_carry_into_each_B_fraction_1sigma": pooled,
        "calibration_seed_count_per_fold": len(Q1_SEEDS) - 1,
    }
    ranked = sorted(
        (
            cell
            for cell in cells
            if cell["corrected_error"]["mean"] is not None
        ),
        key=lambda cell: abs(cell["corrected_error"]["mean"]),
        reverse=True,
    )
    if ranked:
        result["worst_cell"] = ranked[0]
    scatter_ranked = sorted(
        (
            cell
            for cell in cells
            if cell["corrected_error"]["sd"] is not None
        ),
        key=lambda cell: cell["corrected_error"]["sd"],
        reverse=True,
    )
    if scatter_ranked:
        result["largest_scatter_cell"] = scatter_ranked[0]
    return result, build_calibration(observations)


def ladder_noise_seed(rep_index: int, hypothesis_index: int, aperture_index: int) -> int:
    return 80_000_000 + rep_index * 100_000 + hypothesis_index * 10_000 + aperture_index


def run_ladders(calibration: dict) -> list[dict]:
    rows = []
    total = len(LADDER_SEEDS)
    for rep_index, seed in enumerate(LADDER_SEEDS):
        progress(f"Q2/Q4 common-scene ladder {rep_index + 1}/{total}: seed={seed}")
        spectrum = object_fft(LADDER_ALPHA, seed)
        for hypothesis_index, (name, bellows) in enumerate(HYPOTHESES.items()):
            for aperture_index, (tag, n_marked, signal) in enumerate(APERTURES):
                true_fc = float(L.f_cutoff_sensor(bellows * n_marked, L.LAMBDA_UM))
                field = sampled_optical_field(spectrum, true_fc)
                patch, noise = patch_from_field(
                    field,
                    signal,
                    ladder_noise_seed(rep_index, hypothesis_index, aperture_index),
                )
                estimate = estimate_patch(patch)
                recovered = estimate["f_c"]
                gated = recovered is not None and bool(
                    estimate["knee"].get("has_signal")
                )
                corrected, correction_detail = correct_fc(
                    recovered,
                    LADDER_ALPHA,
                    signal,
                    calibration,
                )
                true_mm = float(L.sensor_cyc_px_to_cyc_mm(true_fc))
                commissioned = bool(
                    FC_MM_GRID[0] <= true_mm <= FC_MM_GRID[-1]
                    and true_fc
                    <= REACH_FRACTION * L.lattice_nyquist_sensor(LATTICE)
                )
                rows.append(
                    {
                        "seed": seed,
                        "hypothesis": name,
                        "B_true": bellows,
                        "tag": tag,
                        "N": n_marked,
                        "signal_dn": signal,
                        "alpha": LADDER_ALPHA,
                        "true_fc_sensor_cyc_px": true_fc,
                        "true_fc_cyc_mm": true_mm,
                        "reach_fraction": true_fc
                        / L.lattice_nyquist_sensor(LATTICE),
                        "commissioned_domain": commissioned,
                        "recovered_fc_sensor_cyc_px": recovered,
                        "raw_bias_fraction": (
                            recovered / true_fc - 1.0
                            if recovered is not None
                            else None
                        ),
                        "gated_detected": gated,
                        "dynamic_range": finite_or_none(
                            estimate["knee"].get("dynamic_range")
                        ),
                        "saturated": bool(estimate["knee"].get("saturated")),
                        "surface_corrected_fc_sensor_cyc_px": corrected,
                        "surface_correction_detail": correction_detail,
                        "noise_sigma_dn": noise["noise_sigma_dn"],
                    }
                )
                del field
        del spectrum
    return rows


def repeated_measures_test(
    rows: list[dict],
    tags: list[str],
    value_key: str,
) -> dict:
    by_seed = defaultdict(dict)
    for row in rows:
        value = row.get(value_key)
        if row["tag"] in tags and value is not None and math.isfinite(value):
            by_seed[row["seed"]][row["tag"]] = float(value)
    complete_seeds = [
        seed for seed in LADDER_SEEDS if all(tag in by_seed[seed] for tag in tags)
    ]
    data = np.asarray(
        [[by_seed[seed][tag] for tag in tags] for seed in complete_seeds],
        dtype=float,
    )
    if len(data) < 2 or len(tags) < 2:
        return {
            "test": "repeated-measures ANOVA",
            "tags": tags,
            "n_complete_seeds": len(data),
            "p": None,
            "different": None,
        }
    grand = float(np.mean(data))
    subject = np.mean(data, axis=1, keepdims=True)
    aperture = np.mean(data, axis=0, keepdims=True)
    ss_aperture = float(data.shape[0] * np.sum((aperture - grand) ** 2))
    residual = data - subject - aperture + grand
    ss_error = float(np.sum(residual * residual))
    df_aperture = len(tags) - 1
    df_error = (data.shape[0] - 1) * df_aperture
    ms_aperture = ss_aperture / df_aperture
    ms_error = ss_error / df_error if df_error > 0 else float("nan")
    f_stat = ms_aperture / ms_error if ms_error > 0 else float("inf")
    p_value = float(stats.f.sf(f_stat, df_aperture, df_error))
    means = np.mean(data, axis=0)
    slopes = np.asarray(
        [np.polyfit([dict((tag, n) for tag, n, _ in APERTURES)[tag] for tag in tags], row, 1)[0]
         for row in data],
        dtype=float,
    )
    slope_test = stats.ttest_1samp(slopes, 0.0)
    result = {
        "test": "repeated-measures ANOVA with common-scene seed as block",
        "tags": tags,
        "n_complete_seeds": len(data),
        "mean_by_aperture_fraction": {
            tag: float(value) for tag, value in zip(tags, means)
        },
        "bias_span_fraction": float(np.max(means) - np.min(means)),
        "F": f_stat,
        "df": [df_aperture, df_error],
        "p": p_value,
        "different": bool(p_value < DEPENDENCE_ALPHA),
        "decision_alpha": DEPENDENCE_ALPHA,
        "linear_slope_fraction_per_f_number": float(np.mean(slopes)),
        "linear_slope_t": float(slope_test.statistic),
        "linear_slope_p": float(slope_test.pvalue),
    }
    if len(tags) >= 3:
        friedman = stats.friedmanchisquare(
            *[data[:, index] for index in range(data.shape[1])]
        )
        result["friedman_p"] = float(friedman.pvalue)
        result["friedman_chi2"] = float(friedman.statistic)
    else:
        paired = stats.ttest_rel(data[:, 0], data[:, 1])
        result["paired_t_p"] = float(paired.pvalue)
        result["paired_t"] = float(paired.statistic)
    return result


def cv(values: list[float]) -> float:
    array = np.asarray(values, dtype=float)
    mean = float(np.mean(array))
    return float(np.std(array, ddof=0) / mean) if mean != 0.0 else float("nan")


def b_from_rows(
    rows: list[dict],
    tags: list[str],
    *,
    fc_key: str,
    common_bias: float | None = None,
) -> dict:
    by_seed = defaultdict(dict)
    for row in rows:
        if row["tag"] not in tags:
            continue
        value = row.get(fc_key)
        if value is None or not math.isfinite(value):
            continue
        if common_bias is not None:
            value = value / (1.0 + common_bias)
        by_seed[row["seed"]][row["tag"]] = row["N"] * value
    b_values = []
    cv_values = []
    for seed in LADDER_SEEDS:
        if not all(tag in by_seed[seed] for tag in tags):
            continue
        ks = [by_seed[seed][tag] for tag in tags]
        k_mean = float(np.mean(ks))
        b_values.append(float(L.PITCH_UM / (L.LAMBDA_UM * k_mean)))
        cv_values.append(cv(ks))
    summary = mean_sd_se(b_values)
    summary.update(
        {
            "tags": tags,
            "B_by_seed": b_values,
            "mean_per_seed_fcN_cv": float(np.mean(cv_values))
            if cv_values
            else None,
            "fcN_cv_by_seed": cv_values,
        }
    )
    return summary


def summarise_ladder_hypothesis(
    all_rows: list[dict],
    name: str,
    calibration: dict,
) -> dict:
    rows = [row for row in all_rows if row["hypothesis"] == name]
    aperture_rows = {}
    commissioned_tags = []
    for tag, _, _ in APERTURES:
        selected = [row for row in rows if row["tag"] == tag]
        true_fc = selected[0]["true_fc_sensor_cyc_px"]
        raw_biases = [
            row["raw_bias_fraction"]
            for row in selected
            if row["raw_bias_fraction"] is not None
        ]
        raw_fc = [
            row["recovered_fc_sensor_cyc_px"]
            for row in selected
            if row["recovered_fc_sensor_cyc_px"] is not None
        ]
        surface_errors = [
            row["surface_corrected_fc_sensor_cyc_px"] / true_fc - 1.0
            for row in selected
            if row["surface_corrected_fc_sensor_cyc_px"] is not None
        ]
        aperture_rows[tag] = {
            "N": selected[0]["N"],
            "signal_dn": selected[0]["signal_dn"],
            "true_fc_sensor_cyc_px": true_fc,
            "true_fc_cyc_mm": selected[0]["true_fc_cyc_mm"],
            "reach_fraction": selected[0]["reach_fraction"],
            "commissioned_domain": selected[0]["commissioned_domain"],
            "gated_detections": sum(row["gated_detected"] for row in selected),
            "saturated_count": sum(row["saturated"] for row in selected),
            "raw_fc": mean_sd_se(raw_fc),
            "raw_bias": mean_sd_se(raw_biases),
            "surface_corrected_error": mean_sd_se(surface_errors),
        }
        if selected[0]["commissioned_domain"]:
            commissioned_tags.append(tag)

    all_tags = [tag for tag, _, _ in APERTURES]
    mean_k_all = [
        aperture_rows[tag]["N"] * aperture_rows[tag]["raw_fc"]["mean"]
        for tag in all_tags
        if aperture_rows[tag]["raw_fc"]["mean"] is not None
    ]
    mean_k_commissioned = [
        aperture_rows[tag]["N"] * aperture_rows[tag]["raw_fc"]["mean"]
        for tag in commissioned_tags
        if aperture_rows[tag]["raw_fc"]["mean"] is not None
    ]
    common_sources = [
        predicted_bias(
            aperture_rows[tag]["true_fc_sensor_cyc_px"],
            LADDER_ALPHA,
            aperture_rows[tag]["signal_dn"],
            calibration,
        )
        for tag in commissioned_tags
    ]
    common_bias = float(np.mean(common_sources)) if common_sources else float("nan")
    common_all = b_from_rows(
        rows,
        all_tags,
        fc_key="recovered_fc_sensor_cyc_px",
        common_bias=common_bias,
    )
    common_valid = b_from_rows(
        rows,
        commissioned_tags,
        fc_key="recovered_fc_sensor_cyc_px",
        common_bias=common_bias,
    )
    surface_common = b_from_rows(
        rows,
        ["f14", "f18"],
        fc_key="surface_corrected_fc_sensor_cyc_px",
    )
    b_true = HYPOTHESES[name]
    for summary in (common_all, common_valid, surface_common):
        summary["relative_error_fraction"] = (
            summary["mean"] / b_true - 1.0 if summary["mean"] is not None else None
        )
    return {
        "B_true": b_true,
        "alpha": LADDER_ALPHA,
        "apertures": aperture_rows,
        "all_tags": all_tags,
        "commissioned_tags": commissioned_tags,
        "raw_fcN_cv_across_aperture_means_all": cv(mean_k_all),
        "raw_fcN_cv_across_aperture_means_commissioned": cv(
            mean_k_commissioned
        ),
        "bias_same_test_all": repeated_measures_test(
            rows, all_tags, "raw_bias_fraction"
        ),
        "bias_same_test_commissioned": repeated_measures_test(
            rows, commissioned_tags, "raw_bias_fraction"
        ),
        "single_common_bias_correction_fraction": common_bias,
        "single_common_bias_source_by_aperture": {
            tag: value for tag, value in zip(commissioned_tags, common_sources)
        },
        "B_after_common_correction_all_apertures": common_all,
        "B_after_common_correction_commissioned": common_valid,
        "B_after_surface_correction_f14_f18": surface_common,
    }


def bootstrap_calibration(
    observations: list[dict],
    sampled_seed_indices: np.ndarray,
) -> dict:
    weights = defaultdict(int)
    for index in sampled_seed_indices:
        weights[Q1_SEEDS[int(index)]] += 1
    return build_calibration(observations, seed_weights=dict(weights))


def bootstrap_q4(
    observations: list[dict],
    ladder_rows: list[dict],
    point_h2: float,
    point_h3: float,
    residual_sd: float,
) -> dict:
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rows_by_hyp_seed = defaultdict(dict)
    for row in ladder_rows:
        if row["tag"] in ("f14", "f18"):
            rows_by_hyp_seed[(row["hypothesis"], row["seed"])][row["tag"]] = row

    b2 = []
    b3 = []
    delta = []
    for _ in range(BOOTSTRAP_REPS):
        q1_indices = rng.integers(0, len(Q1_SEEDS), len(Q1_SEEDS))
        calibration = bootstrap_calibration(observations, q1_indices)
        ladder_indices = rng.integers(
            0, len(LADDER_SEEDS), len(LADDER_SEEDS)
        )
        means = {}
        for name in ("H2", "H3"):
            values = []
            for index in ladder_indices:
                seed = LADDER_SEEDS[int(index)]
                ks = []
                for tag in ("f14", "f18"):
                    row = rows_by_hyp_seed[(name, seed)][tag]
                    corrected, _ = correct_fc(
                        row["recovered_fc_sensor_cyc_px"],
                        LADDER_ALPHA,
                        row["signal_dn"],
                        calibration,
                    )
                    if corrected is not None:
                        ks.append(row["N"] * corrected)
                if len(ks) == 2:
                    values.append(
                        float(L.PITCH_UM / (L.LAMBDA_UM * np.mean(ks)))
                    )
            means[name] = float(np.mean(values))
        b2.append(means["H2"])
        b3.append(means["H3"])
        delta.append(means["H2"] - means["H3"])

    b2 = np.asarray(b2)
    b3 = np.asarray(b3)
    delta = np.asarray(delta)
    se2 = float(np.std(b2, ddof=1))
    se3 = float(np.std(b3, ddof=1))
    delta_se = float(np.std(delta, ddof=1))
    independent_combined = math.sqrt(se2 * se2 + se3 * se3)
    carry2 = abs(point_h2) * residual_sd
    carry3 = abs(point_h3) * residual_sd
    total2 = math.sqrt(se2 * se2 + carry2 * carry2)
    total3 = math.sqrt(se3 * se3 + carry3 * carry3)
    conservative_combined = math.sqrt(total2 * total2 + total3 * total3)
    point_delta = point_h2 - point_h3
    return {
        "method": (
            "Paired nonparametric bootstrap over the eight Q1 calibration seeds "
            "and sixteen common-scene ladder seeds, using f/14 and f/18. The "
            "reported conservative uncertainty also carries Q3's residual "
            "calibration scatter once per quoted B."
        ),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_reps": BOOTSTRAP_REPS,
        "B_H2": point_h2,
        "B_H3": point_h3,
        "se_H2_from_bootstrap": se2,
        "se_H3_from_bootstrap": se3,
        "point_separation": point_delta,
        "separation_se_paired": delta_se,
        "separation_sigma_paired": abs(point_delta) / delta_se,
        "combined_se_independent": independent_combined,
        "separation_sigma_independent": abs(point_delta) / independent_combined,
        "q3_residual_carry_fraction": residual_sd,
        "total_uncertainty_H2": total2,
        "total_uncertainty_H3": total3,
        "combined_uncertainty_with_q3_carry": conservative_combined,
        "separation_sigma_with_q3_carry": abs(point_delta)
        / conservative_combined,
        "bootstrap_delta_95pct": [
            float(np.percentile(delta, 2.5)),
            float(np.percentile(delta, 97.5)),
        ],
        "separated_by_more_than_combined_uncertainty": bool(
            abs(point_delta) > conservative_combined
        ),
        "separated_at_95_percent": bool(
            abs(point_delta) / conservative_combined >= 1.96
        ),
    }


def forward_q4(ladder_rows: list[dict]) -> dict:
    cells = []
    z2 = 0.0
    for tag in ("f14", "f18"):
        h2 = {
            row["seed"]: row["recovered_fc_sensor_cyc_px"]
            for row in ladder_rows
            if row["hypothesis"] == "H2" and row["tag"] == tag
        }
        h3 = {
            row["seed"]: row["recovered_fc_sensor_cyc_px"]
            for row in ladder_rows
            if row["hypothesis"] == "H3" and row["tag"] == tag
        }
        paired = np.asarray([h3[seed] - h2[seed] for seed in LADDER_SEEDS])
        mean_delta = float(np.mean(paired))
        se = float(np.std(paired, ddof=1) / math.sqrt(len(paired)))
        z = mean_delta / se
        z2 += z * z
        cells.append(
            {
                "tag": tag,
                "mean_reported_fc_H2": float(np.mean(list(h2.values()))),
                "mean_reported_fc_H3": float(np.mean(list(h3.values()))),
                "paired_difference": mean_delta,
                "paired_difference_se": se,
                "separation_sigma": z,
            }
        )
    return {
        "method": "Paired forward comparison in the raw quantity reported by m5_lib.knee.",
        "cells": cells,
        "quadrature_combined_sigma": math.sqrt(z2),
    }


def format_p(value) -> str:
    if value is None:
        return "n/a"
    if value < 0.0001:
        return f"{value:.2e}"
    return f"{value:.4f}"


def pct(value, digits=2) -> str:
    return "n/a" if value is None else f"{100.0 * value:.{digits}f}%"


def render_report(result: dict) -> str:
    lines = []

    def add(text=""):
        lines.append(text)

    cfg = result["configuration"]
    add("M129 SYNTHETIC COMMISSIONING BATTERY")
    add("=" * 78)
    add(f"Runtime: {result['runtime_seconds']:.1f} s")
    add("No capture was read. No path under D:\\ was accessed.")
    add(
        f"Geometry: GQ, ROI {cfg['roi']}, tile {cfg['tile']}, Hann, "
        f"fine-grid factor {cfg['fine_grid_factor']}, fixed contrast "
        f"{cfg['contrast']:.2f}."
    )
    add(
        "M5 thresholds, fixed for every cell: "
        f"z={cfg['thresholds']['z_detect']}, "
        f"run={cfg['thresholds']['run_len']}, "
        f"dynamic-range gate={cfg['thresholds']['dyn_gate']}, "
        f"f_lo={cfg['thresholds']['f_lo_abs']} sensor cyc/px."
    )
    add(
        "Every realistic-noise cell uses variance "
        "m5_lib.noise_model_var(mean_dn, ISO=100)['var']; no replacement noise "
        "model is fitted or invented."
    )
    add(
        f"Q1 seeds ({len(Q1_SEEDS)} per cell): "
        + ", ".join(str(value) for value in Q1_SEEDS)
    )
    add(
        f"Ladder seeds ({len(LADDER_SEEDS)}): "
        + ", ".join(str(value) for value in LADDER_SEEDS)
    )
    add(
        f"Null seeds ({len(NULL_SEEDS)}): {NULL_SEEDS[0]} through "
        f"{NULL_SEEDS[-1]}; potency seed {POTENCY_SEED}; bootstrap seed "
        f"{BOOTSTRAP_SEED}."
    )
    add()
    add("REUSED VERSUS ADDED")
    add("-" * 78)
    add(
        "Reused unmodified from m5_lib.py: diffraction and pixel MTFs, GQ crop, "
        "Welch/radial spectrum, knee(), frequency conversion, cutoff arithmetic, "
        "and noise_model_var(). The crossing estimator was not copied or "
        "reimplemented."
    )
    add(
        "Reused from m5_synthetic.py: its power-law random-field design, "
        f"contrast={CONTRAST:.2f}, ROI={ROI}, tile={TILE}, Hann window, "
        "sensor quantisation and CFA-to-GQ production path."
    )
    add(
        "Added here: a cacheable 2x fine-grid version for the 1,800-estimate "
        "crossed sweep. It explicitly multiplies by m5_lib.mtf_diffraction and "
        "m5_lib.mtf_pixel before sensor sampling. The 2x grid reaches 1.0 sensor "
        "cyc/px, above every planted cutoff. Also added reporting, paired tests, "
        "and cross-validated calibration; no estimator thresholds were added."
    )
    add(
        "The object spectrum is exactly proportional to f^-alpha at every "
        "nonzero discrete frequency; only DC is set to zero."
    )
    add(
        f"Original m5_selftest.py: {'PASS' if result['instrument']['selftest']['passed'] else 'FAIL'} "
        f"(exit {result['instrument']['selftest']['returncode']})."
    )
    add()

    potency = result["potency"]
    add("POTENCY CHECK")
    add("-" * 78)
    add(
        f"Planted alpha {potency['planted_alpha']:.3f}; recovered "
        f"{potency['recovered_alpha']:.3f} "
        f"(error {potency['alpha_error']:+.3f})."
    )
    add(
        f"Planted cutoff {potency['planted_fc_cyc_mm']:.1f} cy/mm; "
        f"knee recovered error {pct(potency['crossing_error_fraction'])}, "
        f"whole-rolloff M5 cross-check error "
        f"{pct(potency['model_fit_error_fraction'])}."
    )
    add(f"Potency verdict: {'PASS' if potency['passed'] else 'FAIL'}.")
    add()

    null = result["null"]
    add("NULL")
    add("-" * 78)
    add(
        f"This run: raw false detections {null['raw_false_detections']}/"
        f"{null['trials']} ({pct(null['raw_false_detection_rate'], 1)}); "
        f"after M5's dynamic-range gate {null['gated_false_detections']}/"
        f"{null['trials']} ({pct(null['gated_false_detection_rate'], 1)})."
    )
    add(
        "Historical M5 number, quoted beside it as required: raw 113/330 "
        "(34.2%); gated 0/330 (0.0%)."
    )
    add()

    q1 = result["q1"]
    add("Q1. WHAT IS THE BIAS, AS A FUNCTION OF WHAT?")
    add("-" * 78)
    for name in ("fc", "alpha", "signal"):
        test = q1["dependence"][name]
        add(
            f"{name:>6}: marginal span {pct(test['marginal_span_fraction'])}, "
            f"Friedman p={format_p(test['p'])}, W={test['kendall_w']:.3f} -> "
            f"{'DEPENDS' if test['depends'] else 'no detected dependence'}."
        )
    depends = [
        name for name in ("fc", "alpha", "signal")
        if q1["dependence"][name]["depends"]
    ]
    add(
        "Plain result: the crossing bias depends on "
        + (", ".join(depends) if depends else "none of the swept variables")
        + "."
    )
    add()
    add(
        "Full bias surface. Bias and SE are percentages; n is gated detections "
        f"out of {len(Q1_SEEDS)}."
    )
    add(
        f"{'alpha':>5} {'mean DN':>7} {'fc mm':>6} {'n':>3} "
        f"{'bias':>9} {'SE':>8} {'sat':>3} {'dyn':>9}"
    )
    for cell in q1["cells"]:
        bias = cell["bias"]
        add(
            f"{cell['alpha']:5.1f} {cell['signal_dn']:7.0f} "
            f"{cell['fc_cyc_mm']:6.0f} {bias['n']:3d} "
            f"{pct(bias['mean']):>9} {pct(bias['se']):>8} "
            f"{cell['saturated_count']:3d} {cell['dynamic_range_mean']:9.1f}"
        )
    add()

    add("Q2. DOES THE BIAS CANCEL IN f_c * N?")
    add("-" * 78)
    for name in ("H2", "H3"):
        block = result["q2"][name]
        add(
            f"{name}: planted B={block['B_true']:.4f}, object alpha "
            f"{block['alpha']:.1f}."
        )
        add(
            "  Per-aperture raw bias: "
            + ", ".join(
                f"{tag} {pct(block['apertures'][tag]['raw_bias']['mean'])}"
                for tag, _, _ in APERTURES
            )
            + "."
        )
        add(
            f"  {'ap':>5} {'true mm':>8} {'recovered mm':>12} "
            f"{'f_c*N':>9} {'reach':>7} {'domain':>8}"
        )
        for tag, _, _ in APERTURES:
            aperture = block["apertures"][tag]
            recovered_mm = float(
                L.sensor_cyc_px_to_cyc_mm(aperture["raw_fc"]["mean"])
            )
            fc_n = aperture["N"] * aperture["raw_fc"]["mean"]
            add(
                f"  {tag:>5} {aperture['true_fc_cyc_mm']:8.2f} "
                f"{recovered_mm:12.2f} {fc_n:9.4f} "
                f"{aperture['reach_fraction']:7.3f} "
                f"{str(aperture['commissioned_domain']):>8}"
            )
        add(
            f"  CV(f_c*N), all five aperture means: "
            f"{pct(block['raw_fcN_cv_across_aperture_means_all'])}; "
            f"commissioned domain {block['commissioned_tags']}: "
            f"{pct(block['raw_fcN_cv_across_aperture_means_commissioned'])}."
        )
        test_all = block["bias_same_test_all"]
        test_valid = block["bias_same_test_commissioned"]
        add(
            f"  Same-bias test, all five: repeated-measures F="
            f"{test_all['F']:.2f}, p={format_p(test_all['p'])}; "
            f"commissioned domain: F={test_valid['F']:.2f}, "
            f"p={format_p(test_valid['p'])}."
        )
        bvalid = block["B_after_common_correction_commissioned"]
        ball = block["B_after_common_correction_all_apertures"]
        add(
            f"  One common Q1 bias correction "
            f"{pct(block['single_common_bias_correction_fraction'])}: "
            f"B(all five)={ball['mean']:.4f} +/- {ball['se']:.4f} SE "
            f"({pct(ball['relative_error_fraction'])}); "
            f"B(commissioned)={bvalid['mean']:.4f} +/- {bvalid['se']:.4f} SE "
            f"({pct(bvalid['relative_error_fraction'])})."
        )
    add()
    if result["q2"]["bias_depends_on_N"]:
        add("BIAS DEPENDS ON N. IT DOES NOT CANCEL IN f_c * N.")
        add(
            "Amendment 1's registered stop condition fires. The inverse ladder "
            "is compromised and must not proceed to a real capture."
        )
    else:
        add("No statistically resolved N-dependence was found at alpha=0.01.")
    add()

    q3 = result["q3"]
    add("Q3. CAN THE CORRECTED ESTIMATOR HIT 5 PERCENT?")
    add("-" * 78)
    add(
        f"Leave-one-seed-out correction: {q3['cells_passing']}/"
        f"{q3['cells_total']} cell means are within 5%; worst absolute cell "
        f"mean residual {pct(q3['worst_abs_cell_mean_error_fraction'])}."
    )
    worst = q3.get("worst_cell")
    if worst:
        add(
            f"Worst cell: fc={worst['fc_cyc_mm']:.0f} cy/mm, "
            f"alpha={worst['alpha']:.1f}, mean={worst['signal_dn']:.0f} DN, "
            f"mean residual={pct(worst['corrected_error']['mean'])}, "
            f"sd={pct(worst['corrected_error']['sd'])}."
        )
    widest = q3.get("largest_scatter_cell")
    if widest:
        add(
            f"Largest correction scatter: fc={widest['fc_cyc_mm']:.0f} cy/mm, "
            f"alpha={widest['alpha']:.1f}, mean={widest['signal_dn']:.0f} DN, "
            f"sd={pct(widest['corrected_error']['sd'])}."
        )
    add(
        f"Individual estimates within 5%: "
        f"{pct(q3['fraction_individual_estimates_within_5_percent'], 1)}."
    )
    add(
        f"Residual within-cell scatter: "
        f"{pct(q3['pooled_within_cell_residual_sd_fraction'])} (1 sigma). "
        "This is carried into every quoted B below without dividing it away."
    )
    add(
        f"A1' corrected-accuracy limb: "
        f"{'PASS' if q3['all_cell_means_within_5_percent'] else 'FAIL'}."
    )
    add()

    q4 = result["q4"]
    add("Q4. CAN THE INSTRUMENT TELL H2 FROM H3 AT ALL?")
    add("-" * 78)
    add(
        f"Surface-corrected B from the common in-range f/14 and f/18 ladder: "
        f"H2 {q4['B_H2']:.4f} +/- {q4['total_uncertainty_H2']:.4f}; "
        f"H3 {q4['B_H3']:.4f} +/- {q4['total_uncertainty_H3']:.4f}."
    )
    add(
        f"Separation {q4['point_separation']:.4f}; combined carried uncertainty "
        f"{q4['combined_uncertainty_with_q3_carry']:.4f}; "
        f"{q4['separation_sigma_with_q3_carry']:.2f} standard errors."
    )
    add(
        f"Paired bootstrap alone gives "
        f"{q4['separation_sigma_paired']:.2f} standard errors; raw forward "
        f"comparison gives {q4['forward']['quadrature_combined_sigma']:.2f} "
        "standard errors."
    )
    add(
        "Literal one-standard-error verdict: "
        + (
            "YES, the separation exceeds the combined 1-sigma uncertainty."
            if q4["separated_by_more_than_combined_uncertainty"]
            else "NO, the separation does not exceed the combined uncertainty."
        )
    )
    add(
        "Conventional 95% verdict: "
        + (
            "YES."
            if q4["separated_at_95_percent"]
            else "NO; the corrected result is only marginal despite the strong raw forward separation."
        )
    )
    add()

    add("FINAL VERDICT")
    add("-" * 78)
    add(result["verdict"]["headline"])
    add(result["verdict"]["detail"])
    add()
    protected = result["instrument"]["protected_files"]
    add(
        "Protected M5 files: "
        + (
            "UNCHANGED by SHA-256 and clean in path-scoped git status."
            if protected["unchanged"] and not protected["git_status_after"]
            else "NOT CLEAN; see commission.json."
        )
    )
    add(f"Path-scoped git status: {protected['git_status_after'] or '(clean)'}")
    return "\n".join(lines) + "\n"


def main() -> int:
    started = time.perf_counter()
    repo = repo_root()
    start_hashes = {str(path): sha256(path) for path in PROTECTED}
    status_before = protected_git_status(repo)

    progress("Running the original M5 self-test...")
    selftest = run_m5_selftest()
    progress(f"M5 self-test {'passed' if selftest['passed'] else 'failed'}.")

    progress("Running potency check...")
    potency = run_potency()
    progress(f"Potency {'passed' if potency['passed'] else 'failed'}.")

    progress("Running 330-case pure-noise null...")
    null = run_null()
    progress(
        f"Null complete: raw {null['raw_false_detections']}/{null['trials']}, "
        f"gated {null['gated_false_detections']}/{null['trials']}."
    )

    progress("Running fully crossed Q1 bias surface...")
    observations = run_q1()
    q1_cells, q1_matrix = summarise_q1(observations)
    dependence = q1_dependence(q1_matrix)

    progress("Cross-validating the Q1 correction...")
    q3, calibration = run_q3(observations)

    progress("Running paired common-scene H2 and H3 ladders...")
    ladder_rows = run_ladders(calibration)
    q2_h2 = summarise_ladder_hypothesis(ladder_rows, "H2", calibration)
    q2_h3 = summarise_ladder_hypothesis(ladder_rows, "H3", calibration)
    n_dependence = bool(
        q2_h2["bias_same_test_commissioned"]["different"]
        or q2_h3["bias_same_test_commissioned"]["different"]
    )

    point_h2 = q2_h2["B_after_surface_correction_f14_f18"]["mean"]
    point_h3 = q2_h3["B_after_surface_correction_f14_f18"]["mean"]
    progress("Bootstrapping H2-H3 separation...")
    q4 = bootstrap_q4(
        observations,
        ladder_rows,
        point_h2,
        point_h3,
        q3["pooled_within_cell_residual_sd_fraction"],
    )
    q4["forward"] = forward_q4(ladder_rows)

    end_hashes = {str(path): sha256(path) for path in PROTECTED}
    status_after = protected_git_status(repo)
    protected = {
        "hashes_before": start_hashes,
        "hashes_after": end_hashes,
        "unchanged": start_hashes == end_hashes,
        "git_status_before": status_before,
        "git_status_after": status_after,
    }

    accuracy_ok = bool(q3["all_cell_means_within_5_percent"])
    null_ok = null["gated_false_detections"] == 0
    instrument_ok = bool(selftest["passed"] and potency["passed"])
    ladder_fit = bool(
        instrument_ok
        and null_ok
        and accuracy_ok
        and not n_dependence
        and q4["separated_by_more_than_combined_uncertainty"]
        and protected["unchanged"]
        and not status_after
    )
    if n_dependence:
        headline = "NO-GO: the ladder is not fit to run under Amendment 1."
        detail = (
            "The raw forward predictions separate strongly, but the Q1 "
            "correction misses 5% in part of the registered surface and its bias "
            "is statistically aperture-dependent. A single multiplicative "
            "correction does not preserve f_c*N, so the registered inverse "
            "falsification test is compromised."
        )
    elif not accuracy_ok:
        headline = "NO-GO: the corrected estimator misses the registered 5% bar."
        detail = (
            "Synthetic H2-H3 separation does not override A1'. The real lane "
            "must stop before reading a capture."
        )
    elif not q4["separated_by_more_than_combined_uncertainty"]:
        headline = "NO-GO: the commissioned instrument cannot separate H2 and H3."
        detail = "This is a complete negative result; no threshold was tuned."
    elif ladder_fit:
        headline = "GO: every registered synthetic commissioning condition passes."
        detail = "The ladder is fit to proceed to real data with the stated uncertainty."
    else:
        headline = "NO-GO: at least one commissioning guard failed."
        detail = "See the potency, null, self-test, and protected-file sections."

    runtime = time.perf_counter() - started
    result = {
        "schema_version": 1,
        "runtime_seconds": runtime,
        "configuration": {
            "synthetic_only": True,
            "iso": ISO,
            "lattice": LATTICE,
            "window": WINDOW,
            "roi": ROI,
            "tile": TILE,
            "contrast": CONTRAST,
            "fine_grid_factor": FINE,
            "sensor_grid_side": SENSOR_N,
            "power_law_dc": 0.0,
            "ladder_alpha": LADDER_ALPHA,
            "reach_fraction_for_commissioned_domain": REACH_FRACTION,
            "thresholds": {
                "z_detect": L.Z_DETECT,
                "run_len": L.RUN_LEN,
                "dyn_gate": L.DYN_GATE,
                "f_lo_abs": L.F_LO_ABS,
                "dyn_band": list(L.DYN_BAND),
            },
            "q1": {
                "fc_cyc_mm": FC_MM_GRID,
                "fc_sensor_cyc_px": FC_SENSOR_GRID,
                "alphas": ALPHAS,
                "signal_dn": SIGNALS,
                "seeds": Q1_SEEDS,
                "replicates_per_cell": len(Q1_SEEDS),
                "cells": len(FC_MM_GRID) * len(ALPHAS) * len(SIGNALS),
                "estimates": len(observations),
            },
            "ladder": {
                "apertures": APERTURES,
                "hypotheses": HYPOTHESES,
                "seeds": LADDER_SEEDS,
            },
            "null_seeds": NULL_SEEDS,
            "potency_seed": POTENCY_SEED,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_reps": BOOTSTRAP_REPS,
            "conversion": conversion_check(),
        },
        "reuse": {
            "m5_lib_unmodified": True,
            "m5_synthetic_defaults_reused": {
                "contrast": CONTRAST,
                "roi": ROI,
                "tile": TILE,
                "window": WINDOW,
            },
            "new_code": (
                "Cacheable fine-grid synthesis with explicit library diffraction "
                "and pixel MTFs, Q1 surface calibration, paired ladder statistics, "
                "bootstrap uncertainty, and JSON/text reporting."
            ),
        },
        "instrument": {
            "selftest": selftest,
            "protected_files": protected,
        },
        "potency": potency,
        "null": null,
        "q1": {
            "cells": q1_cells,
            "dependence": dependence,
            "depends_on": [
                name
                for name in ("fc", "alpha", "signal")
                if dependence[name]["depends"]
            ],
        },
        "q2": {
            "H2": q2_h2,
            "H3": q2_h3,
            "bias_depends_on_N": n_dependence,
            "registered_stop_condition_fired": n_dependence,
            "test_decision_alpha": DEPENDENCE_ALPHA,
        },
        "q3": q3,
        "q4": q4,
        "verdict": {
            "fit_to_run": ladder_fit,
            "headline": headline,
            "detail": detail,
        },
    }

    report = render_report(result)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with OUT_JSON.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(clean_json(result), fh, indent=2, sort_keys=True, allow_nan=False)
        fh.write("\n")
    with OUT_TXT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(report)
    print(report, end="")
    return 0 if ladder_fit else 2


if __name__ == "__main__":
    raise SystemExit(main())
