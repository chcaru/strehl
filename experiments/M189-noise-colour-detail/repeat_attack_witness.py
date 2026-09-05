"""Finite witness: repeat cross-statistics cannot identify re-noised provenance."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
SIDE = 128
SEED_SCENE = 189201
SEED_NOISE_A = 189202
SEED_NOISE_B = 189203
GAIN_DN_PER_E = 0.221113
READ_NOISE_E = 1.2392
USM_SIGMA = 1.0
USM_AMOUNT = 0.75


def sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value, dtype=np.float64)
    return hashlib.sha256(array.tobytes()).hexdigest().upper()


def cross_summary(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    fa = np.fft.fft2(a, norm="ortho")
    fb = np.fft.fft2(b, norm="ortho")
    fy = np.fft.fftfreq(SIDE)[:, None]
    fx = np.fft.fftfreq(SIDE)[None, :]
    radius = np.sqrt(fx * fx + fy * fy)
    band = (radius >= 0.12) & (radius < 0.30)
    cross = np.real(fa * np.conj(fb))
    auto_a = np.abs(fa) ** 2
    auto_b = np.abs(fb) ** 2
    difference = 0.5 * np.abs(fa - fb) ** 2
    cross_sum = float(np.sum(cross[band]))
    auto_a_sum = float(np.sum(auto_a[band]))
    auto_b_sum = float(np.sum(auto_b[band]))
    coherence = cross_sum / np.sqrt(auto_a_sum * auto_b_sum)
    return {
        "cross_power": cross_sum,
        "difference_noise_power": float(np.mean(difference[band])),
        "coherence": coherence,
    }


def main() -> None:
    scene = np.random.default_rng(SEED_SCENE).standard_normal((SIDE, SIDE))
    scene = gaussian_filter(scene, 1.5, mode="wrap", truncate=6.0)
    scene = 8000.0 + 1200.0 * (
        scene - float(np.mean(scene))
    ) / float(np.std(scene))
    denoised_estimate = gaussian_filter(scene, 0.7, mode="wrap", truncate=6.0)
    low = gaussian_filter(
        denoised_estimate, USM_SIGMA, mode="wrap", truncate=6.0
    )
    rendered_mean = (
        denoised_estimate
        + USM_AMOUNT * (denoised_estimate - low)
    )

    variance = (
        GAIN_DN_PER_E * rendered_mean
        + (GAIN_DN_PER_E * READ_NOISE_E) ** 2
    )
    if float(np.min(variance)) <= 0.0:
        raise ValueError("nonpositive witness variance")
    sigma = np.sqrt(variance)
    noise_a = sigma * np.random.default_rng(
        SEED_NOISE_A
    ).standard_normal((SIDE, SIDE))
    noise_b = sigma * np.random.default_rng(
        SEED_NOISE_B
    ).standard_normal((SIDE, SIDE))

    # World G labels the shared mean as optically delivered. World R labels the
    # same shared mean as a denoised-then-sharpened render. Both then receive
    # the same independent calibrated noise realizations.
    genuine_a = rendered_mean + noise_a
    genuine_b = rendered_mean + noise_b
    rendered_a = rendered_mean + noise_a
    rendered_b = rendered_mean + noise_b

    genuine_summary = cross_summary(genuine_a, genuine_b)
    rendered_summary = cross_summary(rendered_a, rendered_b)
    result = {
        "schema": "m189-repeat-attack-witness-v1",
        "labels": {
            "world_g": "genuine optical mean plus calibrated independent noise",
            "world_r": "denoised-sharpened mean plus calibrated independent re-noise",
        },
        "observation": {
            "a_max_abs_difference": float(
                np.max(np.abs(genuine_a - rendered_a))
            ),
            "b_max_abs_difference": float(
                np.max(np.abs(genuine_b - rendered_b))
            ),
            "a_bytes_equal": genuine_a.tobytes() == rendered_a.tobytes(),
            "b_bytes_equal": genuine_b.tobytes() == rendered_b.tobytes(),
            "a_sha256": sha256(genuine_a),
            "b_sha256": sha256(genuine_b),
        },
        "cross_statistics": {
            "world_g": genuine_summary,
            "world_r": rendered_summary,
            "max_abs_summary_difference": max(
                abs(genuine_summary[key] - rendered_summary[key])
                for key in genuine_summary
            ),
        },
        "captures_opened": 0,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "repeat-attack-witness.json"
    text_path = OUT / "repeat-attack-witness.txt"
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    lines = [
        f"a_bytes_equal={result['observation']['a_bytes_equal']}",
        f"b_bytes_equal={result['observation']['b_bytes_equal']}",
        (
            "max_abs_summary_difference="
            f"{result['cross_statistics']['max_abs_summary_difference']:.12g}"
        ),
        f"cross_power={genuine_summary['cross_power']:.12g}",
        (
            "difference_noise_power="
            f"{genuine_summary['difference_noise_power']:.12g}"
        ),
        f"coherence={genuine_summary['coherence']:.12g}",
        "PASS: identical repeat observations retain opposite provenance labels",
    ]
    text_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print("\n".join(lines))


if __name__ == "__main__":
    main()
