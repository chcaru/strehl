"""Deterministic synthetic commissioning for the M189 positive-control arm."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter

from metric import measure


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

SIDE = 256
OVERSAMPLE = 4
PAIRS = 16
LATENT_SEED = 189001
NOISE_A_SEED = 189003
NOISE_B_SEED = 189004
ATTACK_A_SEED = 189005
ATTACK_B_SEED = 189006
GAIN_DN_PER_E = 0.221113
READ_NOISE_E = 1.2392
BASE_SIGMA = 1.00
IMPROVED_SIGMA = 0.55
DEGRADED_SIGMA = 1.65
POST_BLUR_SIGMA = 1.00
USM_SIGMA = 1.00
USM_AMOUNT = 0.75
MEAN_DN = 8000.0
MODULATION_DN = 1200.0
TRUNCATE = 6.0

SOURCE_NAMES = (
    "PREREGISTRATION.md",
    "metric.py",
    "commission.py",
    "verify.py",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value, dtype=np.float64)
    digest = hashlib.sha256()
    digest.update(str(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest().upper()


def normalise(value: np.ndarray) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    return (array - float(np.mean(array))) / float(np.std(array))


def render(latent: np.ndarray, sigma_output_px: float) -> np.ndarray:
    filtered = gaussian_filter(
        latent,
        sigma_output_px * OVERSAMPLE,
        mode="wrap",
        truncate=TRUNCATE,
    )
    return filtered.reshape(
        SIDE, OVERSAMPLE, SIDE, OVERSAMPLE
    ).mean(axis=(1, 3))


def filter_stack(value: np.ndarray, sigma: float) -> np.ndarray:
    return gaussian_filter(
        value,
        sigma=(0.0, sigma, sigma),
        mode="wrap",
        truncate=TRUNCATE,
    )


def unsharp_stack(value: np.ndarray) -> np.ndarray:
    low = filter_stack(value, USM_SIGMA)
    return value + USM_AMOUNT * (value - low)


def unsharp_scene(value: np.ndarray) -> np.ndarray:
    low = gaussian_filter(
        value,
        USM_SIGMA,
        mode="wrap",
        truncate=TRUNCATE,
    )
    return value + USM_AMOUNT * (value - low)


def observe(
    scene: np.ndarray,
    noise_a: np.ndarray,
    noise_b: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    variance = GAIN_DN_PER_E * scene + (GAIN_DN_PER_E * READ_NOISE_E) ** 2
    if float(np.min(variance)) <= 0.0:
        raise ValueError("fixture produced nonpositive PTC variance")
    sigma = np.sqrt(variance)[None, :, :]
    return scene[None, :, :] + sigma * noise_a, scene[None, :, :] + sigma * noise_b


def measure_arm(pair: tuple[np.ndarray, np.ndarray]) -> dict[str, float | int]:
    return measure(
        pair[0],
        pair[1],
        gain_dn_per_e=GAIN_DN_PER_E,
        read_noise_e=READ_NOISE_E,
    ).to_dict()


def ratio(numerator: dict[str, float | int], denominator: dict[str, float | int], key: str) -> float:
    return float(numerator[key]) / float(denominator[key])


def git_head() -> str:
    root = HERE.parents[1]
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
    ).stdout.decode("ascii").strip()


def main() -> None:
    high_side = SIDE * OVERSAMPLE
    latent = np.random.default_rng(LATENT_SEED).standard_normal(
        (high_side, high_side)
    )
    latent = gaussian_filter(latent, 1.0, mode="wrap", truncate=TRUNCATE)
    latent = MEAN_DN + MODULATION_DN * normalise(latent)

    scenes = {
        "base": render(latent, BASE_SIGMA),
        "optical_improved": render(latent, IMPROVED_SIGMA),
        "optical_degraded": render(latent, DEGRADED_SIGMA),
    }
    for name, scene in scenes.items():
        if float(np.min(scene)) <= 512.0 or float(np.max(scene)) >= 15500.0:
            raise ValueError(
                f"{name} leaves the preregistered unclipped signal range: "
                f"{np.min(scene)}..{np.max(scene)}"
            )

    noise_a = np.random.default_rng(NOISE_A_SEED).standard_normal(
        (PAIRS, SIDE, SIDE)
    )
    noise_b = np.random.default_rng(NOISE_B_SEED).standard_normal(
        (PAIRS, SIDE, SIDE)
    )
    base = observe(scenes["base"], noise_a, noise_b)
    improved = observe(scenes["optical_improved"], noise_a, noise_b)
    degraded = observe(scenes["optical_degraded"], noise_a, noise_b)

    post_blur = (
        filter_stack(base[0], POST_BLUR_SIGMA),
        filter_stack(base[1], POST_BLUR_SIGMA),
    )
    post_usm = (unsharp_stack(base[0]), unsharp_stack(base[1]))

    attack_scene = unsharp_scene(scenes["base"])
    if float(np.min(attack_scene)) <= 512.0 or float(np.max(attack_scene)) >= 15500.0:
        raise ValueError("adaptive attack scene leaves the unclipped signal range")
    attack_a = np.random.default_rng(ATTACK_A_SEED).standard_normal(
        (PAIRS, SIDE, SIDE)
    )
    attack_b = np.random.default_rng(ATTACK_B_SEED).standard_normal(
        (PAIRS, SIDE, SIDE)
    )
    adaptive_renoise = observe(attack_scene, attack_a, attack_b)

    flat_scene = np.full((SIDE, SIDE), MEAN_DN, dtype=np.float64)
    flat = observe(flat_scene, noise_a, noise_b)

    pairs = {
        "base": base,
        "identity": (base[0].copy(), base[1].copy()),
        "optical_improved": improved,
        "optical_degraded": degraded,
        "post_blur": post_blur,
        "post_usm": post_usm,
        "adaptive_renoise_usm": adaptive_renoise,
        "flat": flat,
    }
    measurements = {name: measure_arm(pair) for name, pair in pairs.items()}
    base_measurement = measurements["base"]

    ratios = {
        name: ratio(measurement, base_measurement, "score")
        for name, measurement in measurements.items()
        if name not in {"base", "flat"}
    }
    raw_ratios = {
        name: ratio(measurement, base_measurement, "raw_coherent_power")
        for name, measurement in measurements.items()
        if name not in {"base", "flat"}
    }

    scene_band = {}
    fy = np.fft.fftfreq(SIDE)[:, None]
    fx = np.fft.fftfreq(SIDE)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    licensed = (radius >= 0.12) & (radius < 0.30)
    for name, scene in {
        **scenes,
        "adaptive_renoise_usm": attack_scene,
    }.items():
        spectrum = np.fft.fft2(scene, norm="ortho")
        scene_band[name] = float(np.mean(np.abs(spectrum[licensed]) ** 2))

    result = {
        "schema": "m189-noise-colour-detail-v1",
        "status": "MEASURED_SYNTHETIC",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "captures_opened": 0,
            "thread_contract": 1,
        },
        "source": {
            "git_head_before_run": git_head(),
            "sha256": {
                name: sha256_file(HERE / name) for name in SOURCE_NAMES
            },
        },
        "fixture": {
            "side": SIDE,
            "oversample": OVERSAMPLE,
            "pairs": PAIRS,
            "gain_dn_per_e": GAIN_DN_PER_E,
            "read_noise_e": READ_NOISE_E,
            "base_sigma": BASE_SIGMA,
            "improved_sigma": IMPROVED_SIGMA,
            "degraded_sigma": DEGRADED_SIGMA,
            "post_blur_sigma": POST_BLUR_SIGMA,
            "usm_sigma": USM_SIGMA,
            "usm_amount": USM_AMOUNT,
            "scene_min_max": {
                name: [float(np.min(scene)), float(np.max(scene))]
                for name, scene in {
                    **scenes,
                    "adaptive_renoise_usm": attack_scene,
                }.items()
            },
            "scene_sha256": {
                name: array_sha256(scene)
                for name, scene in {
                    **scenes,
                    "adaptive_renoise_usm": attack_scene,
                    "flat": flat_scene,
                }.items()
            },
            "scene_band_power": scene_band,
        },
        "measurements": measurements,
        "score_ratios": ratios,
        "raw_coherent_ratios": raw_ratios,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "commission.json"
    text_path = OUT / "commission.txt"
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "M189 PTC-anchored Q synthetic commissioning",
        f"base_score={measurements['base']['score']:.12g}",
        f"optical_improved/base={ratios['optical_improved']:.9f}",
        f"optical_degraded/base={ratios['optical_degraded']:.9f}",
        f"post_blur/base={ratios['post_blur']:.9f}",
        f"post_usm/base={ratios['post_usm']:.9f}",
        (
            "post_usm_raw_coherent/base="
            f"{raw_ratios['post_usm']:.9f}"
        ),
        (
            "post_usm_weighted_noise_gain="
            f"{measurements['post_usm']['weighted_noise_gain']:.9f}"
        ),
        (
            "adaptive_renoise_usm/base="
            f"{ratios['adaptive_renoise_usm']:.9f}"
        ),
        (
            "adaptive_renoise_weighted_noise_gain="
            f"{measurements['adaptive_renoise_usm']['weighted_noise_gain']:.9f}"
        ),
        f"flat_score={measurements['flat']['score']:.12g}",
        "captures_opened=0",
    ]
    text_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()

