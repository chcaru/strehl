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
import rawpy
import scipy
import torch
import torch.nn.functional as F
from scipy import ndimage, optimize, special


EXPERIMENT = Path(__file__).resolve().parents[1]
REPO = EXPERIMENT.parents[1]
MANIFEST_PATH = EXPERIMENT / "input-manifest.json"

TILE_SIDE = 32
GRID_ROWS = 8
GRID_COLS = 12
MACROS_PER_SESSION = GRID_ROWS * GRID_COLS
TRIALS_PER_MACRO = 8
GUARD_PX = 16

TASK_BAND_LOW = 0.16
TASK_BAND_HIGH = 0.24
SIGNAL_AMPLITUDE = 0.060
NOISE_SD = 0.009
BASE_OPTICAL_SIGMA = 0.85
DEGRADED_OPTICAL_SIGMA = 1.35
IMPROVED_OPTICAL_SIGMA = 0.35
USM_RADIUS = 1.0
USM_AMOUNT = 0.5

FILTER_SEED = 0xC1A551F1
FILTER_COUNT = 32
FILTER_SIDE = 5
RIDGE_LAMBDA = 0.003
OPT_MAXITER = 600
PROBABILITY_FLOOR = 1e-9

TRAIN_PATTERN_SEED = 0x41D3A918
DEV_PATTERN_SEED = 0x09B72CE4
BOOTSTRAP_SEED = 0x50C1A7E1
BOOTSTRAP_DRAWS = 10_000

BASE_J_MIN = 0.08
BASE_J_MAX = 0.85
USM_RATIO_UCB_MAX = 1.01
COMMISSION_RATIO_MARGIN = 0.30
NULL_EQUIVALENCE = 0.01

FROZEN_PATHS = (
    "experiments/M-CAND1/PREREGISTRATION.md",
    "experiments/M-CAND1/README.md",
    "experiments/M-CAND1/input-manifest.json",
    "experiments/M-CAND1/out/preflight.json",
    "experiments/M-CAND1/src/cand1.py",
    "experiments/M-CAND1/src/check.py",
    "experiments/M-CAND1/src/run.py",
)


@dataclass(frozen=True)
class SampleSet:
    images: np.ndarray
    labels: np.ndarray
    sessions: np.ndarray
    macros: np.ndarray


@dataclass(frozen=True)
class ArmResult:
    arm: str
    j_bits: float
    accuracy: float
    macro_j: np.ndarray
    macro_accuracy: np.ndarray
    sessions: np.ndarray
    macros: np.ndarray
    fold_details: list[dict]


def stable_seed(*parts: object) -> int:
    text = "\x1f".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.blake2s(text, digest_size=8).digest(), "little")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
        disk_path = REPO / relative
        disk = disk_path.read_bytes()
        frozen = git_output("show", f"{resolved}:{relative}")
        if disk != frozen:
            raise RuntimeError(f"frozen path differs from {resolved}: {relative}")
        hashes[relative] = hashlib.sha256(disk).hexdigest()
    return {"commit": resolved, **hashes}


def configure_threads() -> None:
    torch.set_num_threads(8)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def environment_record() -> dict:
    thread_names = (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
        "TORCH_NUM_THREADS",
    )
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "torch": torch.__version__,
        "rawpy": rawpy.__version__,
        "threads": {name: os.environ.get(name) for name in thread_names},
        "torch_num_threads": torch.get_num_threads(),
        "torch_num_interop_threads": torch.get_num_interop_threads(),
    }


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _decode_visible_twice(path: Path) -> tuple[np.ndarray, dict]:
    with rawpy.imread(str(path)) as first:
        visible = first.raw_image_visible.copy()
        first_pattern = first.raw_pattern.copy()
        first_black = tuple(int(v) for v in first.black_level_per_channel)
        first_white = int(first.white_level)
        sizes = first.sizes
        size_record = {
            "raw_height": int(sizes.raw_height),
            "raw_width": int(sizes.raw_width),
            "top_margin": int(sizes.top_margin),
            "left_margin": int(sizes.left_margin),
            "height": int(sizes.height),
            "width": int(sizes.width),
        }
    with rawpy.imread(str(path)) as second:
        full = second.raw_image.copy()
        second_pattern = second.raw_pattern.copy()
        second_black = tuple(int(v) for v in second.black_level_per_channel)
        second_white = int(second.white_level)
        second_sizes = second.sizes
    independent = full[
        second_sizes.top_margin : second_sizes.top_margin + second_sizes.height,
        second_sizes.left_margin : second_sizes.left_margin + second_sizes.width,
    ]
    if not np.array_equal(visible, independent):
        raise RuntimeError(f"independent RAW decode mismatch: {path}")
    if not np.array_equal(first_pattern, second_pattern):
        raise RuntimeError(f"RAW pattern changed between decodes: {path}")
    if first_black != second_black or first_white != second_white:
        raise RuntimeError(f"RAW level metadata changed between decodes: {path}")
    return visible, {
        "raw_pattern": first_pattern.tolist(),
        "black_levels": list(first_black),
        "white_level": first_white,
        "sizes": size_record,
        "visible_sha256": hashlib.sha256(visible.tobytes()).hexdigest(),
        "independent_decode_equal": True,
    }


def _phase_order(raw_pattern: np.ndarray) -> list[tuple[int, int, int, str]]:
    named = []
    green_count = 0
    for row in range(2):
        for col in range(2):
            color = int(raw_pattern[row, col])
            if color == 0:
                name = "R"
            elif color == 2:
                name = "B"
            elif color in (1, 3):
                green_count += 1
                name = f"G{green_count}"
            else:
                raise RuntimeError(f"unsupported CFA color index {color}")
            named.append((row, col, color, name))
    order = {"R": 0, "G1": 1, "G2": 2, "B": 3}
    return sorted(named, key=lambda item: order[item[3]])


def _grid_centres(height: int, width: int) -> list[tuple[int, int]]:
    half = TILE_SIDE // 2
    margin = GUARD_PX + half
    ys = np.rint(np.linspace(margin, height - margin - 1, GRID_ROWS)).astype(int)
    xs = np.rint(np.linspace(margin, width - margin - 1, GRID_COLS)).astype(int)
    centres = [(int(y), int(x)) for y in ys for x in xs]
    min_distance = min(
        min(np.diff(np.unique(ys))),
        min(np.diff(np.unique(xs))),
    )
    if min_distance < TILE_SIDE + 2 * GUARD_PX:
        raise RuntimeError(
            f"macro-tile guard violated: distance={min_distance}, "
            f"required={TILE_SIDE + 2 * GUARD_PX}"
        )
    return centres


def load_backgrounds() -> tuple[np.ndarray, dict]:
    manifest = load_manifest()
    all_tiles = []
    records = []
    expected_pattern = None
    expected_shape = None
    for session_index, entry in enumerate(manifest["sessions"]):
        path = Path(entry["path"])
        if path.stat().st_size != int(entry["bytes"]):
            raise RuntimeError(f"byte count changed: {path}")
        actual_sha = sha256_file(path)
        if actual_sha != entry["sha256"]:
            raise RuntimeError(f"source SHA-256 changed: {path}")
        visible, decode = _decode_visible_twice(path)
        pattern = np.asarray(decode["raw_pattern"], dtype=np.int64)
        if expected_pattern is None:
            expected_pattern = pattern
        elif not np.array_equal(pattern, expected_pattern):
            raise RuntimeError("CFA pattern differs across development inputs")
        phases = []
        names = []
        for row, col, color, name in _phase_order(pattern):
            black = float(decode["black_levels"][color])
            white = float(decode["white_level"])
            plane = (visible[row::2, col::2].astype(np.float32) - black) / (
                white - black
            )
            phases.append(plane)
            names.append(name)
        image = np.stack(phases, axis=0)
        if expected_shape is None:
            expected_shape = image.shape
        elif image.shape != expected_shape:
            raise RuntimeError("active CFA-plane shape differs across inputs")
        centres = _grid_centres(image.shape[1], image.shape[2])
        session_tiles = []
        half = TILE_SIDE // 2
        for y, x in centres:
            tile = image[:, y - half : y + half, x - half : x + half]
            if tile.shape != (4, TILE_SIDE, TILE_SIDE):
                raise RuntimeError(f"bad tile shape {tile.shape} at {(y, x)}")
            session_tiles.append(tile)
        all_tiles.append(np.stack(session_tiles, axis=0))
        records.append(
            {
                "session_index": session_index,
                "session": entry["session"],
                "path": str(path),
                "bytes": int(entry["bytes"]),
                "sha256": actual_sha,
                "decode": decode,
                "cfa_order": names,
                "plane_shape": list(image.shape),
                "centres": [list(value) for value in centres],
                "tile_min": float(np.min(session_tiles)),
                "tile_max": float(np.max(session_tiles)),
                "tile_mean": float(np.mean(session_tiles)),
                "tile_sd": float(np.std(session_tiles)),
            }
        )
    backgrounds = np.stack(all_tiles, axis=0).astype(np.float32)
    return backgrounds, {
        "manifest_sha256": sha256_file(MANIFEST_PATH),
        "shape": list(backgrounds.shape),
        "sessions": records,
    }


def task_mask(side: int = TILE_SIDE) -> np.ndarray:
    fy = np.fft.fftfreq(side)[:, None]
    fx = np.fft.fftfreq(side)[None, :]
    radius = np.hypot(fx, fy)
    return (radius >= TASK_BAND_LOW) & (radius <= TASK_BAND_HIGH)


def target_pair(seed: int) -> tuple[np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    latent = rng.standard_normal((TILE_SIDE, TILE_SIDE))
    coupled = latent * latent - np.mean(latent * latent)
    spectrum = np.fft.fft2(coupled) * task_mask()
    structured = np.fft.ifft2(spectrum).real

    phase_source = np.fft.fft2(rng.standard_normal((TILE_SIDE, TILE_SIDE)))
    unit_phase = phase_source / np.maximum(np.abs(phase_source), 1e-15)
    surrogate_spectrum = np.abs(spectrum) * unit_phase
    surrogate = np.fft.ifft2(surrogate_spectrum).real

    structured -= structured.mean()
    surrogate -= surrogate.mean()
    rms = math.sqrt(float(np.mean(structured * structured)))
    surrogate_rms = math.sqrt(float(np.mean(surrogate * surrogate)))
    if rms <= 0 or surrogate_rms <= 0:
        raise RuntimeError("degenerate task target")
    structured /= rms
    surrogate /= surrogate_rms

    fs = np.fft.fft2(structured)
    fr = np.fft.fft2(surrogate)
    magnitude_error = float(
        np.max(np.abs(np.abs(fs) - np.abs(fr)))
        / max(float(np.max(np.abs(fs))), 1e-15)
    )
    outside = ~task_mask()
    outside_fraction = float(
        (
            np.sum(np.abs(fs[outside]) ** 2)
            + np.sum(np.abs(fr[outside]) ** 2)
        )
        / (
            np.sum(np.abs(fs) ** 2)
            + np.sum(np.abs(fr) ** 2)
        )
    )
    return surrogate.astype(np.float32), structured.astype(np.float32), {
        "relative_magnitude_error": magnitude_error,
        "outside_band_energy_fraction": outside_fraction,
    }


def optical_sigma(arm: str) -> float:
    if arm in ("base", "usm", "null", "no-target"):
        return BASE_OPTICAL_SIGMA
    if arm == "degraded":
        return DEGRADED_OPTICAL_SIGMA
    if arm == "improved":
        return IMPROVED_OPTICAL_SIGMA
    raise ValueError(f"unknown arm {arm}")


def noise_family(arm: str) -> str:
    if arm in ("base", "usm", "null", "no-target"):
        return "base"
    return arm


def make_samples(
    backgrounds: np.ndarray,
    arm: str,
    split_seed: int,
) -> SampleSet:
    images = []
    labels = []
    sessions = []
    macros = []
    channel_gains = np.asarray([1.0, 0.96, 1.04, 0.91], np.float32)[:, None, None]
    for session in range(backgrounds.shape[0]):
        for macro in range(backgrounds.shape[1]):
            assignment_rng = np.random.default_rng(
                stable_seed("assign", split_seed, session, macro)
            )
            macro_labels = np.asarray([0, 0, 0, 0, 1, 1, 1, 1], np.int64)
            assignment_rng.shuffle(macro_labels)
            for trial, label in enumerate(macro_labels):
                nuisance_rng = np.random.default_rng(
                    stable_seed("nuisance", split_seed, session, macro, trial)
                )
                background = backgrounds[session, macro].copy()
                turns = int(nuisance_rng.integers(0, 4))
                background = np.rot90(background, turns, axes=(1, 2)).copy()
                background = (
                    background * float(nuisance_rng.uniform(0.94, 1.06))
                    + float(nuisance_rng.uniform(-0.006, 0.006))
                )

                target0, target1, _ = target_pair(
                    stable_seed("target", split_seed, session, macro, trial)
                )
                target = target1 if label == 1 else target0
                target = np.rot90(target, turns).copy()
                target = np.roll(
                    target,
                    (
                        int(nuisance_rng.integers(0, TILE_SIDE)),
                        int(nuisance_rng.integers(0, TILE_SIDE)),
                    ),
                    axis=(0, 1),
                )
                target = ndimage.gaussian_filter(
                    target,
                    sigma=optical_sigma(arm),
                    mode="wrap",
                    truncate=4.0,
                )
                if arm == "no-target":
                    target.fill(0.0)

                rng_noise = np.random.default_rng(
                    stable_seed(
                        "noise",
                        noise_family(arm),
                        split_seed,
                        session,
                        macro,
                        trial,
                    )
                )
                noise = rng_noise.normal(
                    0.0,
                    NOISE_SD,
                    size=(4, TILE_SIDE, TILE_SIDE),
                ).astype(np.float32)
                output = (
                    background
                    + SIGNAL_AMPLITUDE * channel_gains * target[None, :, :]
                    + noise
                ).astype(np.float32)
                if arm == "usm":
                    lowpass = ndimage.gaussian_filter(
                        output,
                        sigma=(0.0, USM_RADIUS, USM_RADIUS),
                        mode="reflect",
                        truncate=4.0,
                    )
                    output = (
                        output + USM_AMOUNT * (output - lowpass)
                    ).astype(np.float32)
                images.append(output)
                labels.append(int(label))
                sessions.append(session)
                macros.append(macro)
    return SampleSet(
        images=np.stack(images, axis=0),
        labels=np.asarray(labels, np.int64),
        sessions=np.asarray(sessions, np.int64),
        macros=np.asarray(macros, np.int64),
    )


def observer_filters() -> np.ndarray:
    rng = np.random.default_rng(FILTER_SEED)
    kernels = rng.standard_normal(
        (FILTER_COUNT, 4, FILTER_SIDE, FILTER_SIDE)
    ).astype(np.float32)
    kernels -= kernels.mean(axis=(2, 3), keepdims=True)
    norms = np.sqrt(np.sum(kernels * kernels, axis=(1, 2, 3), keepdims=True))
    kernels /= norms
    return kernels


def filter_hash() -> str:
    return hashlib.sha256(observer_filters().tobytes()).hexdigest()


def extract_features(images: np.ndarray, batch_size: int = 256) -> np.ndarray:
    kernels = torch.from_numpy(observer_filters())
    blocks = []
    with torch.no_grad():
        for start in range(0, len(images), batch_size):
            tensor = torch.from_numpy(images[start : start + batch_size])
            padded = F.pad(
                tensor,
                (FILTER_SIDE // 2,) * 4,
                mode="reflect",
            )
            response = F.conv2d(padded, kernels)
            abs_mean = response.abs().mean(dim=(2, 3))
            square_mean = response.square().mean(dim=(2, 3))
            cube_mean = response.pow(3).mean(dim=(2, 3))
            fourth_mean = response.pow(4).mean(dim=(2, 3))
            feature = torch.cat(
                (abs_mean, square_mean, cube_mean, fourth_mean),
                dim=1,
            )
            blocks.append(feature.numpy())
    return np.concatenate(blocks, axis=0).astype(np.float64)


def fit_logistic(features: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, dict]:
    mean = features.mean(axis=0)
    scale = features.std(axis=0, ddof=0)
    scale = np.maximum(scale, 1e-10)
    x = (features - mean) / scale
    y = labels.astype(np.float64)

    def objective(theta: np.ndarray) -> tuple[float, np.ndarray]:
        weights = theta[:-1]
        bias = theta[-1]
        logits = x @ weights + bias
        loss = float(
            np.mean(np.logaddexp(0.0, logits) - y * logits)
            + 0.5 * RIDGE_LAMBDA * np.dot(weights, weights)
        )
        residual = special.expit(logits) - y
        grad_w = x.T @ residual / len(y) + RIDGE_LAMBDA * weights
        grad_b = float(np.mean(residual))
        return loss, np.concatenate((grad_w, [grad_b]))

    initial = np.zeros(x.shape[1] + 1, np.float64)
    result = optimize.minimize(
        objective,
        initial,
        jac=True,
        method="L-BFGS-B",
        options={
            "maxiter": OPT_MAXITER,
            "ftol": 1e-13,
            "gtol": 1e-8,
            "maxls": 50,
        },
    )
    gradient_norm = float(np.linalg.norm(result.jac))
    if not result.success and gradient_norm > 1e-5:
        raise RuntimeError(
            f"logistic fit failed: {result.message}; |grad|={gradient_norm}"
        )
    model = np.concatenate((result.x, mean, scale))
    return model, {
        "success": bool(result.success),
        "message": str(result.message),
        "iterations": int(result.nit),
        "loss_nats": float(result.fun),
        "gradient_norm": gradient_norm,
    }


def predict_logistic(model: np.ndarray, features: np.ndarray) -> np.ndarray:
    dim = features.shape[1]
    theta = model[: dim + 1]
    mean = model[dim + 1 : 2 * dim + 1]
    scale = model[2 * dim + 1 :]
    logits = ((features - mean) / scale) @ theta[:-1] + theta[-1]
    return special.expit(logits)


def crossfit_arm(
    backgrounds: np.ndarray,
    arm: str,
    test_seed: int,
    macro_limit: int = MACROS_PER_SESSION,
) -> ArmResult:
    train_samples = make_samples(backgrounds, arm, TRAIN_PATTERN_SEED)
    test_samples = make_samples(backgrounds, arm, test_seed)
    train_features = extract_features(train_samples.images)
    test_features = extract_features(test_samples.images)
    trial_j = np.full(len(test_samples.labels), np.nan, np.float64)
    trial_correct = np.full(len(test_samples.labels), np.nan, np.float64)
    fold_details = []
    for held_session in range(backgrounds.shape[0]):
        train_mask = (
            (train_samples.sessions != held_session)
            & (train_samples.macros < macro_limit)
        )
        test_mask = (
            (test_samples.sessions == held_session)
            & (test_samples.macros < macro_limit)
        )
        model, fit = fit_logistic(
            train_features[train_mask],
            train_samples.labels[train_mask],
        )
        probability_one = predict_logistic(model, test_features[test_mask])
        labels = test_samples.labels[test_mask]
        probability_true = np.where(labels == 1, probability_one, 1.0 - probability_one)
        probability_true = np.clip(
            probability_true,
            PROBABILITY_FLOOR,
            1.0 - PROBABILITY_FLOOR,
        )
        trial_j[test_mask] = np.log2(2.0 * probability_true)
        trial_correct[test_mask] = (
            (probability_one >= 0.5).astype(np.int64) == labels
        )
        fold_details.append(
            {
                "held_session": held_session,
                "train_samples": int(np.sum(train_mask)),
                "test_samples": int(np.sum(test_mask)),
                "j_bits": float(np.mean(trial_j[test_mask])),
                "accuracy": float(np.mean(trial_correct[test_mask])),
                "fit": fit,
            }
        )
    selected = test_samples.macros < macro_limit
    if not np.all(np.isfinite(trial_j[selected])):
        raise RuntimeError(f"cross-fit left unscored trials for arm {arm}")
    cluster_sessions = []
    cluster_macros = []
    macro_j = []
    macro_accuracy = []
    for session in range(backgrounds.shape[0]):
        for macro in range(macro_limit):
            mask = (
                (test_samples.sessions == session)
                & (test_samples.macros == macro)
            )
            if int(np.sum(mask)) != TRIALS_PER_MACRO:
                raise RuntimeError("macro-tile trial count changed")
            cluster_sessions.append(session)
            cluster_macros.append(macro)
            macro_j.append(float(np.mean(trial_j[mask])))
            macro_accuracy.append(float(np.mean(trial_correct[mask])))
    return ArmResult(
        arm=arm,
        j_bits=float(np.mean(trial_j[selected])),
        accuracy=float(np.mean(trial_correct[selected])),
        macro_j=np.asarray(macro_j),
        macro_accuracy=np.asarray(macro_accuracy),
        sessions=np.asarray(cluster_sessions),
        macros=np.asarray(cluster_macros),
        fold_details=fold_details,
    )


def bootstrap_comparison(base: ArmResult, arm: ArmResult) -> dict:
    if not np.array_equal(base.sessions, arm.sessions) or not np.array_equal(
        base.macros, arm.macros
    ):
        raise RuntimeError("arm macro-tile clusters are not paired")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    unique_sessions = np.unique(base.sessions)
    ratios = np.empty(BOOTSTRAP_DRAWS, np.float64)
    deltas = np.empty(BOOTSTRAP_DRAWS, np.float64)
    base_values = np.empty(BOOTSTRAP_DRAWS, np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        sampled_sessions = rng.choice(
            unique_sessions,
            size=len(unique_sessions),
            replace=True,
        )
        selected_indices = []
        for session in sampled_sessions:
            available = np.flatnonzero(base.sessions == session)
            selected_indices.append(
                rng.choice(available, size=len(available), replace=True)
            )
        index = np.concatenate(selected_indices)
        base_value = float(np.mean(base.macro_j[index]))
        arm_value = float(np.mean(arm.macro_j[index]))
        base_values[draw] = base_value
        ratios[draw] = arm_value / base_value
        deltas[draw] = arm_value - base_value
    if np.any(base_values <= 0.0):
        raise RuntimeError(
            "ratio refused: at least one cluster-bootstrap base J is non-positive"
        )
    if np.any(~np.isfinite(ratios)):
        raise RuntimeError("non-finite bootstrap ratio")
    return {
        "base_j_bits": base.j_bits,
        "arm_j_bits": arm.j_bits,
        "ratio": arm.j_bits / base.j_bits,
        "paired_log_ratio": math.log(arm.j_bits / base.j_bits),
        "delta_bits": arm.j_bits - base.j_bits,
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
        "minimum_bootstrap_base_j": float(np.min(base_values)),
    }


def arm_record(result: ArmResult) -> dict:
    return {
        "arm": result.arm,
        "j_bits": result.j_bits,
        "i_over_hx": result.j_bits,
        "accuracy": result.accuracy,
        "macro_count": int(len(result.macro_j)),
        "macro_j_min": float(np.min(result.macro_j)),
        "macro_j_max": float(np.max(result.macro_j)),
        "folds": result.fold_details,
    }


def task_audit() -> dict:
    rows = []
    for index in range(32):
        _, _, audit = target_pair(stable_seed("audit", index))
        rows.append(audit)
    mask = task_mask()
    fy = np.fft.fftfreq(TILE_SIDE)[:, None]
    fx = np.fft.fftfreq(TILE_SIDE)[None, :]
    radius = np.hypot(fx, fy)
    return {
        "band_requested": [TASK_BAND_LOW, TASK_BAND_HIGH],
        "active_frequency_min": float(np.min(radius[mask])),
        "active_frequency_max": float(np.max(radius[mask])),
        "active_bins": int(np.sum(mask)),
        "worst_relative_magnitude_error": float(
            max(row["relative_magnitude_error"] for row in rows)
        ),
        "worst_outside_band_energy_fraction": float(
            max(row["outside_band_energy_fraction"] for row in rows)
        ),
    }


def transfer_audit() -> dict:
    frequency = 0.21

    def gaussian_mtf(sigma: float) -> float:
        return math.exp(-2.0 * math.pi * math.pi * sigma * sigma * frequency**2)

    base = gaussian_mtf(BASE_OPTICAL_SIGMA)
    degraded = gaussian_mtf(DEGRADED_OPTICAL_SIGMA)
    improved = gaussian_mtf(IMPROVED_OPTICAL_SIGMA)
    usm_gain = 1.0 + USM_AMOUNT * (
        1.0 - gaussian_mtf(USM_RADIUS)
    )
    return {
        "audit_frequency_cyc_per_native_px": frequency,
        "base_mtf": base,
        "degraded_mtf": degraded,
        "improved_mtf": improved,
        "degraded_over_base": degraded / base,
        "improved_over_base": improved / base,
        "post_render_usm_gain": usm_gain,
    }


def test_seed_from_freeze(commit: str) -> int:
    resolved = git_output("rev-parse", f"{commit}^{{commit}}").decode().strip()
    return stable_seed("sealed-test-after-freeze", resolved)


def check_label_balance(sample: SampleSet) -> dict:
    failures = []
    for session in np.unique(sample.sessions):
        for macro in np.unique(sample.macros):
            mask = (sample.sessions == session) & (sample.macros == macro)
            if int(np.sum(sample.labels[mask])) != TRIALS_PER_MACRO // 2:
                failures.append([int(session), int(macro)])
    return {
        "macrotiles_checked": int(
            len(np.unique(sample.sessions)) * len(np.unique(sample.macros))
        ),
        "failures": failures,
        "all_balanced": not failures,
    }


def learning_curve(backgrounds: np.ndarray) -> dict:
    points = []
    full_result = None
    for macro_limit in (24, 48, 72, 96):
        result = crossfit_arm(
            backgrounds,
            "base",
            DEV_PATTERN_SEED,
            macro_limit=macro_limit,
        )
        points.append(
            {
                "macrotiles_per_session": macro_limit,
                "j_bits": result.j_bits,
                "accuracy": result.accuracy,
            }
        )
        full_result = result
    assert full_result is not None
    rng = np.random.default_rng(stable_seed("preflight-power", BOOTSTRAP_SEED))
    unique_sessions = np.unique(full_result.sessions)
    bootstrap_j = np.empty(BOOTSTRAP_DRAWS, np.float64)
    for draw in range(BOOTSTRAP_DRAWS):
        sampled_sessions = rng.choice(
            unique_sessions,
            size=len(unique_sessions),
            replace=True,
        )
        selected_indices = []
        for session in sampled_sessions:
            available = np.flatnonzero(full_result.sessions == session)
            selected_indices.append(
                rng.choice(available, size=len(available), replace=True)
            )
        bootstrap_j[draw] = float(
            np.mean(full_result.macro_j[np.concatenate(selected_indices)])
        )
    bootstrap_se = float(np.std(bootstrap_j, ddof=1))
    independent_relative_se = (
        math.sqrt(2.0) * bootstrap_se / full_result.j_bits
    )
    minimum_detectable_ratio = (
        special.ndtri(0.95) + special.ndtri(0.90)
    ) * independent_relative_se
    plateau_delta = abs(points[-1]["j_bits"] - points[-2]["j_bits"])
    return {
        "points": points,
        "plateau_delta_bits_72_to_96": plateau_delta,
        "plateau_bar_bits": 0.02,
        "plateau_pass": plateau_delta <= 0.02,
        "base_dynamic_range_pass": (
            BASE_J_MIN <= points[-1]["j_bits"] <= BASE_J_MAX
        ),
        "arm_blind_power": {
            "baseline_bootstrap_se_bits": bootstrap_se,
            "conservative_independent_arm_relative_se": independent_relative_se,
            "one_sided_alpha": 0.05,
            "power": 0.90,
            "minimum_detectable_ratio_change": float(minimum_detectable_ratio),
            "frozen_commission_ratio_margin": COMMISSION_RATIO_MARGIN,
            "pass": bool(
                minimum_detectable_ratio <= COMMISSION_RATIO_MARGIN
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


def ensure_no_holdout_paths(metadata: dict) -> None:
    forbidden_fragments = ("319-frame", "holdout", "sw4-a", "sw4-b")
    paths = " ".join(
        record["path"].lower() for record in metadata["sessions"]
    )
    hits = [fragment for fragment in forbidden_fragments if fragment in paths]
    if hits:
        raise RuntimeError(f"possible holdout path touched: {hits}")


def source_summary() -> dict:
    return {
        "observer": {
            "kind": "cross-fitted ridge-logistic variational observer",
            "input": [4, TILE_SIDE, TILE_SIDE],
            "filter_count": FILTER_COUNT,
            "filter_side": FILTER_SIDE,
            "feature_moments": ["mean_abs", "mean_square", "mean_cube", "mean_fourth"],
            "feature_count": FILTER_COUNT * 4,
            "filter_seed": FILTER_SEED,
            "filter_sha256": filter_hash(),
            "ridge_lambda": RIDGE_LAMBDA,
            "optimizer": "scipy L-BFGS-B",
            "optimizer_maxiter": OPT_MAXITER,
            "probability_floor": PROBABILITY_FLOOR,
            "folds": "leave-one-acquisition-session-out (5 folds)",
        },
        "task": {
            "tile_side": TILE_SIDE,
            "grid": [GRID_ROWS, GRID_COLS],
            "macrotiles_per_session": MACROS_PER_SESSION,
            "trials_per_macrotile": TRIALS_PER_MACRO,
            "guard_px": GUARD_PX,
            "band": [TASK_BAND_LOW, TASK_BAND_HIGH],
            "signal_amplitude": SIGNAL_AMPLITUDE,
            "noise_sd": NOISE_SD,
            "base_optical_sigma": BASE_OPTICAL_SIGMA,
            "degraded_optical_sigma": DEGRADED_OPTICAL_SIGMA,
            "improved_optical_sigma": IMPROVED_OPTICAL_SIGMA,
            "usm_radius": USM_RADIUS,
            "usm_amount": USM_AMOUNT,
            "train_pattern_seed": TRAIN_PATTERN_SEED,
            "dev_pattern_seed": DEV_PATTERN_SEED,
        },
        "decision": {
            "base_j_range_bits": [BASE_J_MIN, BASE_J_MAX],
            "usm_ratio_ucb95_max": USM_RATIO_UCB_MAX,
            "commission_ratio_margin": COMMISSION_RATIO_MARGIN,
            "null_equivalence": NULL_EQUIVALENCE,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
    }
