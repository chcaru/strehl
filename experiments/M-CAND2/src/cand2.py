from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy
from scipy import linalg, ndimage, special


EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = EXPERIMENT.parents[1]
CAND1_SRC = REPO / "experiments" / "M-CAND1" / "src"
sys.path.insert(0, str(CAND1_SRC))
import cand1  # noqa: E402


CHANNELS = 4
PLANE_SIDE = 8
DIMENSION = CHANNELS * PLANE_SIDE * PLANE_SIDE
TEMPLATE_COUNT = 4
TASK_BAND_LOW = 0.12
TASK_BAND_HIGH = 0.25

SIGNAL_AMPLITUDE = 0.0045
NOISE_SD = cand1.NOISE_SD
BASE_OPTICAL_SIGMA = cand1.BASE_OPTICAL_SIGMA
DEGRADED_OPTICAL_SIGMA = cand1.DEGRADED_OPTICAL_SIGMA
IMPROVED_OPTICAL_SIGMA = cand1.IMPROVED_OPTICAL_SIGMA
CHANNEL_GAINS = np.asarray([1.0, 0.96, 1.04, 0.91], np.float64)[:, None, None]

RENDER_SCALE = 1.9
RENDER_OFFSET = 0.18
USM_RADIUS = 1.0
USM_AMOUNT = 0.5
LOGISTIC_SLOPE = 12.0
SATURATION_LOW = 0.10
SATURATION_HIGH = 0.90
QUANTIZATION_LEVELS = 255

DEV_TEMPLATE_SEED = 0xC20209D1
BOOTSTRAP_SEED = 0xC2B0057A
BOOTSTRAP_DRAWS = 10_000

CONDITION_MAX = 1.0e8
MIN_TRAIN_TO_DIMENSION = 1.40
BASE_D2_MIN = 0.25
BASE_D2_MAX = 64.0
ALGEBRA_RATIO_TOL = 1.0e-8
ALGEBRA_SCORE_TOL = 1.0e-7
CONGRUENCE_REL_TOL = 1.0e-10
NONLINEAR_RATIO_UCB_MAX = 1.01
TONE_EQUIVALENCE = 0.01
OPTICAL_RATIO_MARGIN = 0.30
CLIP_POTENCY_MIN = 0.001

FROZEN_PATHS = (
    "experiments/M-CAND1/input-manifest.json",
    "experiments/M-CAND1/src/cand1.py",
    "experiments/M-CAND2/PREREGISTRATION.md",
    "experiments/M-CAND2/README.md",
    "experiments/M-CAND2/out/preflight.json",
    "experiments/M-CAND2/src/cand2.py",
    "experiments/M-CAND2/src/check.py",
    "experiments/M-CAND2/src/run.py",
)


@dataclass(frozen=True)
class ObservationSet:
    covariance: np.ndarray
    derivative_plus: np.ndarray
    derivative_minus: np.ndarray
    test_plus: np.ndarray
    test_minus: np.ndarray
    blocks: np.ndarray
    macros: np.ndarray


@dataclass(frozen=True)
class FoldModel:
    held_block: int
    covariance: np.ndarray
    derivatives: np.ndarray
    midpoints: np.ndarray
    weights: np.ndarray
    scales: np.ndarray
    condition_number: float
    minimum_eigenvalue: float
    maximum_eigenvalue: float
    train_count: int
    dimension: int
    solve_residual_max: float
    train_d2: np.ndarray


@dataclass(frozen=True)
class HotellingResult:
    arm: str
    status: str
    d2: float | None
    d2_by_template: np.ndarray | None
    accuracy: float | None
    z_plus: np.ndarray | None
    z_minus: np.ndarray | None
    blocks: np.ndarray
    macros: np.ndarray
    models: tuple[FoldModel, ...]
    refusal: str | None


class RankRefusal(RuntimeError):
    pass


def git_output(*args: str) -> bytes:
    return subprocess.check_output(
        ["git", *args],
        cwd=REPO,
        stderr=subprocess.STDOUT,
    )


def verify_freeze(commit: str) -> dict[str, str]:
    resolved = git_output("rev-parse", f"{commit}^{{commit}}").decode().strip()
    hashes: dict[str, str] = {}
    for relative in FROZEN_PATHS:
        path = REPO / relative
        frozen_blob = git_output("rev-parse", f"{resolved}:{relative}").decode().strip()
        disk_blob = subprocess.check_output(
            ["git", "hash-object", f"--path={relative}", str(path)],
            cwd=REPO,
            stderr=subprocess.STDOUT,
        ).decode().strip()
        if frozen_blob != disk_blob:
            raise RuntimeError(f"frozen path differs from {resolved}: {relative}")
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"commit": resolved, **hashes}


def configure_threads() -> None:
    cand1.configure_threads()


def environment_record() -> dict:
    record = cand1.environment_record()
    record["scipy"] = scipy.__version__
    record["render_scale"] = RENDER_SCALE
    record["render_offset"] = RENDER_OFFSET
    return record


def stable_seed(*parts: object) -> int:
    return cand1.stable_seed("cand2", *parts)


def sealed_template_seed(commit: str) -> int:
    resolved = git_output("rev-parse", f"{commit}^{{commit}}").decode().strip()
    return stable_seed("sealed-template-after-freeze", resolved)


def crop_backgrounds(backgrounds: np.ndarray) -> np.ndarray:
    if backgrounds.shape[2:] != (4, cand1.TILE_SIDE, cand1.TILE_SIDE):
        raise RuntimeError(f"unexpected CAND1 background shape {backgrounds.shape}")
    start = (cand1.TILE_SIDE - PLANE_SIDE) // 2
    stop = start + PLANE_SIDE
    cropped = backgrounds[:, :, :, start:stop, start:stop].astype(np.float64)
    if cropped.shape[2:] != (CHANNELS, PLANE_SIDE, PLANE_SIDE):
        raise RuntimeError(f"bad cropped shape {cropped.shape}")
    return cropped


def load_backgrounds() -> tuple[np.ndarray, dict]:
    backgrounds, record = cand1.load_backgrounds()
    cropped = crop_backgrounds(backgrounds)
    record = dict(record)
    record["cand2_shape"] = list(cropped.shape)
    record["cand2_dimension"] = DIMENSION
    record["cand2_crop"] = {
        "source_plane_side": cand1.TILE_SIDE,
        "plane_side": PLANE_SIDE,
        "start": (cand1.TILE_SIDE - PLANE_SIDE) // 2,
    }
    return cropped, record


def task_mask() -> np.ndarray:
    fy = np.fft.fftfreq(PLANE_SIDE)[:, None]
    fx = np.fft.fftfreq(PLANE_SIDE)[None, :]
    radius = np.hypot(fx, fy)
    return (radius >= TASK_BAND_LOW) & (radius <= TASK_BAND_HIGH)


def template_bank(seed: int) -> np.ndarray:
    templates = []
    mask = task_mask()
    for index in range(TEMPLATE_COUNT):
        rng = np.random.default_rng(stable_seed("template", seed, index))
        spectrum = np.fft.fft2(rng.standard_normal((PLANE_SIDE, PLANE_SIDE)))
        template = np.fft.ifft2(spectrum * mask).real
        template -= template.mean()
        rms = math.sqrt(float(np.mean(template * template)))
        if rms <= 0:
            raise RuntimeError("degenerate task template")
        templates.append(template / rms)
    return np.stack(templates, axis=0).astype(np.float64)


def template_audit(seed: int) -> dict:
    templates = template_bank(seed)
    mask = task_mask()
    outside = ~mask
    outside_fractions = []
    means = []
    rms_values = []
    for template in templates:
        spectrum = np.fft.fft2(template)
        outside_fractions.append(
            float(
                np.sum(np.abs(spectrum[outside]) ** 2)
                / np.sum(np.abs(spectrum) ** 2)
            )
        )
        means.append(float(np.mean(template)))
        rms_values.append(float(np.sqrt(np.mean(template * template))))
    fy = np.fft.fftfreq(PLANE_SIDE)[:, None]
    fx = np.fft.fftfreq(PLANE_SIDE)[None, :]
    radius = np.hypot(fx, fy)
    return {
        "requested_band": [TASK_BAND_LOW, TASK_BAND_HIGH],
        "active_frequency_min": float(np.min(radius[mask])),
        "active_frequency_max": float(np.max(radius[mask])),
        "active_bins": int(np.sum(mask)),
        "maximum_absolute_mean": max(abs(value) for value in means),
        "maximum_rms_error": max(abs(value - 1.0) for value in rms_values),
        "maximum_outside_band_energy_fraction": max(outside_fractions),
        "template_sha256": hashlib.sha256(templates.tobytes()).hexdigest(),
    }


def optical_sigma(arm: str) -> float:
    if arm == "degraded":
        return DEGRADED_OPTICAL_SIGMA
    if arm == "improved":
        return IMPROVED_OPTICAL_SIGMA
    return BASE_OPTICAL_SIGMA


def _nuisance_background(
    background: np.ndarray,
    template_seed: int,
    block: int,
    macro: int,
    stream: str,
    template: int | None,
) -> np.ndarray:
    rng = np.random.default_rng(
        stable_seed("nuisance", template_seed, block, macro, stream, template)
    )
    turns = int(rng.integers(0, 4))
    transformed = np.rot90(background, turns, axes=(1, 2)).copy()
    return (
        transformed * float(rng.uniform(0.94, 1.06))
        + float(rng.uniform(-0.006, 0.006))
    )


def _noise(
    template_seed: int,
    noise_family: str,
    block: int,
    macro: int,
    stream: str,
    template: int | None,
    sign: int,
) -> np.ndarray:
    rng = np.random.default_rng(
        stable_seed(
            "noise",
            template_seed,
            noise_family,
            block,
            macro,
            stream,
            template,
            sign,
        )
    )
    return rng.normal(
        0.0,
        NOISE_SD,
        size=(CHANNELS, PLANE_SIDE, PLANE_SIDE),
    )


def _observation(
    background: np.ndarray,
    target: np.ndarray | None,
    sign: int,
    template_seed: int,
    noise_family: str,
    block: int,
    macro: int,
    stream: str,
    template: int | None,
) -> np.ndarray:
    nuisance = _nuisance_background(
        background,
        template_seed,
        block,
        macro,
        stream,
        template,
    )
    signal = np.zeros_like(nuisance)
    if target is not None and sign != 0:
        signal = sign * SIGNAL_AMPLITUDE * CHANNEL_GAINS * target[None, :, :]
    noise = _noise(
        template_seed,
        noise_family,
        block,
        macro,
        stream,
        template,
        sign,
    )
    rendered = RENDER_SCALE * (nuisance + signal + noise) + RENDER_OFFSET
    return rendered.reshape(-1)


def make_observations(
    backgrounds: np.ndarray,
    template_seed: int,
    arm: str = "base",
) -> ObservationSet:
    templates = template_bank(template_seed)
    sigma = optical_sigma(arm)
    filtered = np.stack(
        [
            ndimage.gaussian_filter(
                template,
                sigma=sigma,
                mode="wrap",
                truncate=4.0,
            )
            for template in templates
        ],
        axis=0,
    )
    noise_family = arm
    covariance = []
    derivative_plus = [[] for _ in range(TEMPLATE_COUNT)]
    derivative_minus = [[] for _ in range(TEMPLATE_COUNT)]
    test_plus = [[] for _ in range(TEMPLATE_COUNT)]
    test_minus = [[] for _ in range(TEMPLATE_COUNT)]
    blocks = []
    macros = []
    for block in range(backgrounds.shape[0]):
        for macro in range(backgrounds.shape[1]):
            background = backgrounds[block, macro]
            covariance.append(
                _observation(
                    background,
                    None,
                    0,
                    template_seed,
                    noise_family,
                    block,
                    macro,
                    "covariance",
                    None,
                )
            )
            for template in range(TEMPLATE_COUNT):
                target = filtered[template]
                derivative_plus[template].append(
                    _observation(
                        background,
                        target,
                        1,
                        template_seed,
                        noise_family,
                        block,
                        macro,
                        "derivative",
                        template,
                    )
                )
                derivative_minus[template].append(
                    _observation(
                        background,
                        target,
                        -1,
                        template_seed,
                        noise_family,
                        block,
                        macro,
                        "derivative",
                        template,
                    )
                )
                test_plus[template].append(
                    _observation(
                        background,
                        target,
                        1,
                        template_seed,
                        noise_family,
                        block,
                        macro,
                        "test",
                        template,
                    )
                )
                test_minus[template].append(
                    _observation(
                        background,
                        target,
                        -1,
                        template_seed,
                        noise_family,
                        block,
                        macro,
                        "test",
                        template,
                    )
                )
            blocks.append(block)
            macros.append(macro)
    return ObservationSet(
        covariance=np.asarray(covariance, np.float64),
        derivative_plus=np.asarray(derivative_plus, np.float64),
        derivative_minus=np.asarray(derivative_minus, np.float64),
        test_plus=np.asarray(test_plus, np.float64),
        test_minus=np.asarray(test_minus, np.float64),
        blocks=np.asarray(blocks, np.int64),
        macros=np.asarray(macros, np.int64),
    )


def _map_arrays(data: ObservationSet, function) -> ObservationSet:
    return ObservationSet(
        covariance=function(data.covariance),
        derivative_plus=function(data.derivative_plus),
        derivative_minus=function(data.derivative_minus),
        test_plus=function(data.test_plus),
        test_minus=function(data.test_minus),
        blocks=data.blocks.copy(),
        macros=data.macros.copy(),
    )


def usm(values: np.ndarray) -> np.ndarray:
    original_shape = values.shape
    planes = values.reshape(-1, CHANNELS, PLANE_SIDE, PLANE_SIDE)
    lowpass = ndimage.gaussian_filter(
        planes,
        sigma=(0.0, 0.0, USM_RADIUS, USM_RADIUS),
        mode="reflect",
        truncate=4.0,
    )
    sharpened = planes + USM_AMOUNT * (planes - lowpass)
    return sharpened.reshape(original_shape)


def apply_transform(data: ObservationSet, transform: str) -> ObservationSet:
    if transform in ("base", "null"):
        return _map_arrays(data, lambda values: values.copy())
    if transform == "unclipped-usm":
        return _map_arrays(data, usm)
    if transform == "clipped-usm":
        return _map_arrays(data, lambda values: np.clip(usm(values), 0.0, 1.0))
    if transform == "gamma3":
        return _map_arrays(data, lambda values: values**3)
    if transform == "logistic":
        return _map_arrays(
            data,
            lambda values: special.expit(LOGISTIC_SLOPE * (values - 0.5)),
        )
    if transform == "saturation":
        return _map_arrays(
            data,
            lambda values: np.clip(values, SATURATION_LOW, SATURATION_HIGH),
        )
    if transform == "quantization":
        return _map_arrays(
            data,
            lambda values: np.rint(values * QUANTIZATION_LEVELS)
            / QUANTIZATION_LEVELS,
        )
    raise ValueError(f"unknown transform {transform}")


def all_values(data: ObservationSet) -> list[np.ndarray]:
    return [
        data.covariance,
        data.derivative_plus,
        data.derivative_minus,
        data.test_plus,
        data.test_minus,
    ]


def range_audit(data: ObservationSet) -> dict:
    minimum = min(float(np.min(values)) for values in all_values(data))
    maximum = max(float(np.max(values)) for values in all_values(data))
    total = sum(values.size for values in all_values(data))
    outside = sum(
        int(np.count_nonzero((values < 0.0) | (values > 1.0)))
        for values in all_values(data)
    )
    return {
        "minimum": minimum,
        "maximum": maximum,
        "outside_0_1_count": outside,
        "total_values": total,
        "outside_0_1_fraction": outside / total,
        "pass": outside == 0,
    }


def transform_audit(base: ObservationSet, transformed: ObservationSet) -> dict:
    total = 0
    changed = 0
    rail_low = 0
    rail_high = 0
    max_abs = 0.0
    for source, arm in zip(all_values(base), all_values(transformed), strict=True):
        total += source.size
        changed += int(np.count_nonzero(source != arm))
        rail_low += int(np.count_nonzero(arm == 0.0))
        rail_high += int(np.count_nonzero(arm == 1.0))
        max_abs = max(max_abs, float(np.max(np.abs(source - arm))))
    return {
        "changed_fraction": changed / total,
        "low_rail_fraction": rail_low / total,
        "high_rail_fraction": rail_high / total,
        "maximum_absolute_change": max_abs,
        "total_values": total,
    }


def _covariance(values: np.ndarray) -> np.ndarray:
    centered = values - values.mean(axis=0, keepdims=True)
    return centered.T @ centered / (len(values) - 1)


def _fit_fold(
    data: ObservationSet,
    held_block: int,
    macro_limit: int,
) -> tuple[FoldModel, np.ndarray, np.ndarray]:
    train = (data.blocks != held_block) & (data.macros < macro_limit)
    test = (data.blocks == held_block) & (data.macros < macro_limit)
    cov_samples = data.covariance[train]
    train_count = len(cov_samples)
    if train_count <= DIMENSION:
        raise RankRefusal(
            f"n={train_count} is not greater than p={DIMENSION}"
        )
    if train_count / DIMENSION < MIN_TRAIN_TO_DIMENSION:
        raise RankRefusal(
            f"n/p={train_count / DIMENSION:.6f} below "
            f"{MIN_TRAIN_TO_DIMENSION:.6f}"
        )
    covariance = _covariance(cov_samples)
    eigenvalues = np.linalg.eigvalsh(covariance)
    minimum = float(eigenvalues[0])
    maximum = float(eigenvalues[-1])
    if minimum <= 0.0:
        raise RankRefusal(f"non-positive covariance eigenvalue {minimum}")
    condition = maximum / minimum
    if condition > CONDITION_MAX:
        raise RankRefusal(
            f"condition number {condition:.6e} exceeds {CONDITION_MAX:.6e}"
        )
    try:
        factor = linalg.cho_factor(
            covariance,
            lower=True,
            check_finite=True,
        )
    except linalg.LinAlgError as error:
        raise RankRefusal(f"Cholesky failed: {error}") from error

    derivatives = []
    midpoints = []
    weights = []
    scales = []
    train_d2 = []
    residuals = []
    z_plus = []
    z_minus = []
    for template in range(TEMPLATE_COUNT):
        plus = data.derivative_plus[template, train]
        minus = data.derivative_minus[template, train]
        derivative = np.mean(plus - minus, axis=0)
        midpoint = 0.5 * np.mean(plus + minus, axis=0)
        weight = linalg.cho_solve(factor, derivative, check_finite=True)
        solve_residual = float(
            np.linalg.norm(covariance @ weight - derivative)
            / max(np.linalg.norm(derivative), 1e-30)
        )
        d2 = float(derivative @ weight)
        if d2 <= 0.0:
            raise RankRefusal(f"non-positive training d2 {d2}")
        scale = math.sqrt(float(weight @ covariance @ weight))
        test_plus = data.test_plus[template, test]
        test_minus = data.test_minus[template, test]
        center = float(weight @ midpoint)
        z_plus.append((test_plus @ weight - center) / scale)
        z_minus.append((test_minus @ weight - center) / scale)
        derivatives.append(derivative)
        midpoints.append(midpoint)
        weights.append(weight)
        scales.append(scale)
        train_d2.append(d2)
        residuals.append(solve_residual)
    model = FoldModel(
        held_block=held_block,
        covariance=covariance,
        derivatives=np.asarray(derivatives),
        midpoints=np.asarray(midpoints),
        weights=np.asarray(weights),
        scales=np.asarray(scales),
        condition_number=condition,
        minimum_eigenvalue=minimum,
        maximum_eigenvalue=maximum,
        train_count=train_count,
        dimension=DIMENSION,
        solve_residual_max=max(residuals),
        train_d2=np.asarray(train_d2),
    )
    return model, np.asarray(z_plus), np.asarray(z_minus)


def _score(z_plus: np.ndarray, z_minus: np.ndarray) -> tuple[float, np.ndarray, float]:
    mean_difference = z_plus.mean(axis=1) - z_minus.mean(axis=1)
    pooled_variance = 0.5 * (
        z_plus.var(axis=1, ddof=1) + z_minus.var(axis=1, ddof=1)
    )
    if np.any(pooled_variance <= 0.0):
        raise RankRefusal("non-positive held-out score variance")
    d2 = mean_difference * mean_difference / pooled_variance
    accuracy = 0.5 * (
        np.mean(z_plus >= 0.0) + np.mean(z_minus < 0.0)
    )
    return float(np.mean(d2)), d2, float(accuracy)


def crossfit(
    data: ObservationSet,
    arm: str,
    macro_limit: int = cand1.MACROS_PER_SESSION,
) -> HotellingResult:
    models = []
    z_plus = np.full(
        (TEMPLATE_COUNT, len(data.blocks)),
        np.nan,
        np.float64,
    )
    z_minus = np.full_like(z_plus, np.nan)
    try:
        for held_block in range(5):
            model, fold_plus, fold_minus = _fit_fold(
                data,
                held_block,
                macro_limit,
            )
            mask = (data.blocks == held_block) & (data.macros < macro_limit)
            z_plus[:, mask] = fold_plus
            z_minus[:, mask] = fold_minus
            models.append(model)
        selected = data.macros < macro_limit
        if not np.all(np.isfinite(z_plus[:, selected])) or not np.all(
            np.isfinite(z_minus[:, selected])
        ):
            raise RankRefusal("cross-fit left non-finite held-out scores")
        d2, by_template, accuracy = _score(
            z_plus[:, selected],
            z_minus[:, selected],
        )
        return HotellingResult(
            arm=arm,
            status="NUMERIC",
            d2=d2,
            d2_by_template=by_template,
            accuracy=accuracy,
            z_plus=z_plus[:, selected],
            z_minus=z_minus[:, selected],
            blocks=data.blocks[selected],
            macros=data.macros[selected],
            models=tuple(models),
            refusal=None,
        )
    except RankRefusal as error:
        selected = data.macros < macro_limit
        return HotellingResult(
            arm=arm,
            status="REFUSED_RANK",
            d2=None,
            d2_by_template=None,
            accuracy=None,
            z_plus=None,
            z_minus=None,
            blocks=data.blocks[selected],
            macros=data.macros[selected],
            models=tuple(models),
            refusal=str(error),
        )


def _score_indices(
    z_plus: np.ndarray,
    z_minus: np.ndarray,
    indices: np.ndarray,
) -> float:
    return _score(z_plus[:, indices], z_minus[:, indices])[0]


def bootstrap_comparison(
    base: HotellingResult,
    arm: HotellingResult,
) -> dict:
    if base.status != "NUMERIC" or arm.status != "NUMERIC":
        raise RankRefusal("bootstrap requires two numeric arms")
    assert base.z_plus is not None and base.z_minus is not None
    assert arm.z_plus is not None and arm.z_minus is not None
    assert base.d2 is not None and arm.d2 is not None
    if not np.array_equal(base.blocks, arm.blocks) or not np.array_equal(
        base.macros, arm.macros
    ):
        raise RuntimeError("arm sites are not paired")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    unique_blocks = np.unique(base.blocks)
    ratios = np.empty(BOOTSTRAP_DRAWS, np.float64)
    deltas = np.empty(BOOTSTRAP_DRAWS, np.float64)
    base_values = np.empty(BOOTSTRAP_DRAWS, np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        sampled_blocks = rng.choice(
            unique_blocks,
            size=len(unique_blocks),
            replace=True,
        )
        indices = []
        for block in sampled_blocks:
            available = np.flatnonzero(base.blocks == block)
            indices.append(
                rng.choice(available, size=len(available), replace=True)
            )
        selected = np.concatenate(indices)
        base_value = _score_indices(base.z_plus, base.z_minus, selected)
        arm_value = _score_indices(arm.z_plus, arm.z_minus, selected)
        base_values[draw] = base_value
        ratios[draw] = arm_value / base_value
        deltas[draw] = arm_value - base_value
    if np.any(base_values <= 0.0) or np.any(~np.isfinite(ratios)):
        raise RankRefusal("non-positive or non-finite bootstrap base")
    return {
        "base_d2": base.d2,
        "arm_d2": arm.d2,
        "ratio": arm.d2 / base.d2,
        "decibels": 10.0 * math.log10(arm.d2 / base.d2),
        "delta_d2": arm.d2 - base.d2,
        "ratio_lcb95_one_sided": float(np.quantile(ratios, 0.05)),
        "ratio_ucb95_one_sided": float(np.quantile(ratios, 0.95)),
        "ratio_ci95_two_sided": [
            float(np.quantile(ratios, 0.025)),
            float(np.quantile(ratios, 0.975)),
        ],
        "delta_ci95_two_sided": [
            float(np.quantile(deltas, 0.025)),
            float(np.quantile(deltas, 0.975)),
        ],
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "minimum_bootstrap_base_d2": float(np.min(base_values)),
    }


def usm_operator() -> np.ndarray:
    basis = np.eye(DIMENSION, dtype=np.float64).reshape(
        DIMENSION,
        CHANNELS,
        PLANE_SIDE,
        PLANE_SIDE,
    )
    rows = usm(basis.reshape(DIMENSION, DIMENSION))
    return rows.T


def algebra_audit(
    base: HotellingResult,
    arm: HotellingResult,
) -> dict:
    if base.status != "NUMERIC" or arm.status != "NUMERIC":
        raise RankRefusal("algebra audit requires numeric arms")
    assert base.z_plus is not None and arm.z_plus is not None
    assert base.z_minus is not None and arm.z_minus is not None
    operator = usm_operator()
    eigenvalues = np.linalg.eigvalsh(operator)
    covariance_errors = []
    derivative_errors = []
    midpoint_errors = []
    weight_errors = []
    for base_model, arm_model in zip(base.models, arm.models, strict=True):
        covariance_errors.append(
            float(
                np.linalg.norm(
                    arm_model.covariance
                    - operator @ base_model.covariance @ operator.T
                )
                / np.linalg.norm(arm_model.covariance)
            )
        )
        derivative_errors.append(
            float(
                np.linalg.norm(
                    arm_model.derivatives
                    - base_model.derivatives @ operator.T
                )
                / np.linalg.norm(arm_model.derivatives)
            )
        )
        midpoint_errors.append(
            float(
                np.linalg.norm(
                    arm_model.midpoints - base_model.midpoints @ operator.T
                )
                / np.linalg.norm(arm_model.midpoints)
            )
        )
        expected_weights = np.stack(
            [
                linalg.solve(operator.T, weight, assume_a="pos")
                for weight in base_model.weights
            ],
            axis=0,
        )
        weight_errors.append(
            float(
                np.linalg.norm(arm_model.weights - expected_weights)
                / np.linalg.norm(arm_model.weights)
            )
        )
    return {
        "operator_minimum_eigenvalue": float(eigenvalues[0]),
        "operator_maximum_eigenvalue": float(eigenvalues[-1]),
        "operator_condition_number": float(eigenvalues[-1] / eigenvalues[0]),
        "maximum_covariance_relative_error": max(covariance_errors),
        "maximum_derivative_relative_error": max(derivative_errors),
        "maximum_midpoint_relative_error": max(midpoint_errors),
        "maximum_weight_relative_error": max(weight_errors),
        "maximum_plus_score_absolute_error": float(
            np.max(np.abs(base.z_plus - arm.z_plus))
        ),
        "maximum_minus_score_absolute_error": float(
            np.max(np.abs(base.z_minus - arm.z_minus))
        ),
    }


def model_record(model: FoldModel) -> dict:
    return {
        "held_block": model.held_block,
        "train_count": model.train_count,
        "dimension": model.dimension,
        "train_to_dimension": model.train_count / model.dimension,
        "condition_number": model.condition_number,
        "minimum_eigenvalue": model.minimum_eigenvalue,
        "maximum_eigenvalue": model.maximum_eigenvalue,
        "solve_residual_max": model.solve_residual_max,
        "train_d2": model.train_d2.tolist(),
    }


def result_record(result: HotellingResult) -> dict:
    return {
        "arm": result.arm,
        "status": result.status,
        "d2": result.d2,
        "d2_by_template": (
            result.d2_by_template.tolist()
            if result.d2_by_template is not None
            else None
        ),
        "accuracy": result.accuracy,
        "site_count": int(len(result.blocks)),
        "models": [model_record(model) for model in result.models],
        "refusal": result.refusal,
    }


def source_summary() -> dict:
    return {
        "estimator": {
            "name": "cross-fitted full-covariance Hotelling observer",
            "dimension": DIMENSION,
            "tile": [CHANNELS, PLANE_SIDE, PLANE_SIDE],
            "templates": TEMPLATE_COUNT,
            "covariance": "unregularized sample covariance",
            "inverse": "Cholesky solve",
            "shrinkage": None,
            "pseudoinverse": False,
            "folds": "leave-one-acquisition-block-out",
            "covariance_stream_is_independent_of_derivative_stream": True,
            "condition_max": CONDITION_MAX,
            "minimum_train_to_dimension": MIN_TRAIN_TO_DIMENSION,
        },
        "task": {
            "band": [TASK_BAND_LOW, TASK_BAND_HIGH],
            "signal_amplitude": SIGNAL_AMPLITUDE,
            "noise_sd": NOISE_SD,
            "base_optical_sigma": BASE_OPTICAL_SIGMA,
            "degraded_optical_sigma": DEGRADED_OPTICAL_SIGMA,
            "improved_optical_sigma": IMPROVED_OPTICAL_SIGMA,
            "render_scale": RENDER_SCALE,
            "render_offset": RENDER_OFFSET,
            "usm_radius": USM_RADIUS,
            "usm_amount": USM_AMOUNT,
            "logistic_slope": LOGISTIC_SLOPE,
            "saturation": [SATURATION_LOW, SATURATION_HIGH],
            "quantization_levels": QUANTIZATION_LEVELS,
        },
        "decision": {
            "base_d2_range": [BASE_D2_MIN, BASE_D2_MAX],
            "algebra_ratio_tolerance": ALGEBRA_RATIO_TOL,
            "algebra_score_tolerance": ALGEBRA_SCORE_TOL,
            "congruence_relative_tolerance": CONGRUENCE_REL_TOL,
            "nonlinear_ratio_ucb95_max": NONLINEAR_RATIO_UCB_MAX,
            "tone_equivalence": TONE_EQUIVALENCE,
            "optical_ratio_margin": OPTICAL_RATIO_MARGIN,
            "clip_potency_min": CLIP_POTENCY_MIN,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "interpretation": {
            "primary": "held-out d-prime squared",
            "neq": "REFUSED: spatial stationarity is not established",
            "local_linearity": (
                "exact for the additive symmetric target before nonlinear arms"
            ),
        },
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
