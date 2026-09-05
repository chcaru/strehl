"""Held-out v2 commissioning for the conservative M189 envelope score."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter

import commission as fixture
from metric_v2 import measure


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"

LATENT_SEED = 189101
NOISE_A_SEED = 189103
NOISE_B_SEED = 189104
ATTACK_A_SEED = 189105
ATTACK_B_SEED = 189106

SOURCE_NAMES = (
    "PREREGISTRATION.md",
    "AMENDMENT-1.md",
    "commission.py",
    "metric_v2.py",
    "commission_v2.py",
    "verify_v2.py",
)


def measure_arm(pair: tuple[np.ndarray, np.ndarray]) -> dict[str, float | int]:
    return measure(
        pair[0],
        pair[1],
        gain_dn_per_e=fixture.GAIN_DN_PER_E,
        read_noise_e=fixture.READ_NOISE_E,
    ).to_dict()


def ratio(
    numerator: dict[str, float | int],
    denominator: dict[str, float | int],
    key: str,
) -> float:
    return float(numerator[key]) / float(denominator[key])


def main() -> None:
    high_side = fixture.SIDE * fixture.OVERSAMPLE
    latent = np.random.default_rng(LATENT_SEED).standard_normal(
        (high_side, high_side)
    )
    latent = gaussian_filter(
        latent, 1.0, mode="wrap", truncate=fixture.TRUNCATE
    )
    latent = (
        fixture.MEAN_DN
        + fixture.MODULATION_DN * fixture.normalise(latent)
    )

    scenes = {
        "base": fixture.render(latent, fixture.BASE_SIGMA),
        "optical_improved": fixture.render(latent, fixture.IMPROVED_SIGMA),
        "optical_degraded": fixture.render(latent, fixture.DEGRADED_SIGMA),
    }
    for name, scene in scenes.items():
        if float(np.min(scene)) <= 512.0 or float(np.max(scene)) >= 15500.0:
            raise ValueError(
                f"{name} leaves the preregistered unclipped signal range: "
                f"{np.min(scene)}..{np.max(scene)}"
            )

    noise_a = np.random.default_rng(NOISE_A_SEED).standard_normal(
        (fixture.PAIRS, fixture.SIDE, fixture.SIDE)
    )
    noise_b = np.random.default_rng(NOISE_B_SEED).standard_normal(
        (fixture.PAIRS, fixture.SIDE, fixture.SIDE)
    )
    base = fixture.observe(scenes["base"], noise_a, noise_b)
    improved = fixture.observe(scenes["optical_improved"], noise_a, noise_b)
    degraded = fixture.observe(scenes["optical_degraded"], noise_a, noise_b)

    post_blur = (
        fixture.filter_stack(base[0], fixture.POST_BLUR_SIGMA),
        fixture.filter_stack(base[1], fixture.POST_BLUR_SIGMA),
    )
    post_usm = (
        fixture.unsharp_stack(base[0]),
        fixture.unsharp_stack(base[1]),
    )

    attack_scene = fixture.unsharp_scene(scenes["base"])
    if (
        float(np.min(attack_scene)) <= 512.0
        or float(np.max(attack_scene)) >= 15500.0
    ):
        raise ValueError("adaptive attack scene leaves the unclipped signal range")
    attack_a = np.random.default_rng(ATTACK_A_SEED).standard_normal(
        (fixture.PAIRS, fixture.SIDE, fixture.SIDE)
    )
    attack_b = np.random.default_rng(ATTACK_B_SEED).standard_normal(
        (fixture.PAIRS, fixture.SIDE, fixture.SIDE)
    )
    adaptive_renoise = fixture.observe(attack_scene, attack_a, attack_b)

    flat_scene = np.full(
        (fixture.SIDE, fixture.SIDE),
        fixture.MEAN_DN,
        dtype=np.float64,
    )
    flat = fixture.observe(flat_scene, noise_a, noise_b)

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
    local_ratios = {
        name: ratio(measurement, base_measurement, "local_score")
        for name, measurement in measurements.items()
        if name not in {"base", "flat"}
    }
    raw_ratios = {
        name: ratio(measurement, base_measurement, "raw_coherent_power")
        for name, measurement in measurements.items()
        if name not in {"base", "flat"}
    }

    result = {
        "schema": "m189-noise-colour-detail-v2",
        "status": "MEASURED_SYNTHETIC",
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "captures_opened": 0,
            "thread_contract": 1,
        },
        "source": {
            "git_head_before_run": fixture.git_head(),
            "sha256": {
                name: fixture.sha256_file(HERE / name)
                for name in SOURCE_NAMES
            },
        },
        "fixture": {
            "side": fixture.SIDE,
            "oversample": fixture.OVERSAMPLE,
            "pairs": fixture.PAIRS,
            "latent_seed": LATENT_SEED,
            "noise_seeds": [
                NOISE_A_SEED,
                NOISE_B_SEED,
                ATTACK_A_SEED,
                ATTACK_B_SEED,
            ],
            "gain_dn_per_e": fixture.GAIN_DN_PER_E,
            "read_noise_e": fixture.READ_NOISE_E,
            "base_sigma": fixture.BASE_SIGMA,
            "improved_sigma": fixture.IMPROVED_SIGMA,
            "degraded_sigma": fixture.DEGRADED_SIGMA,
            "post_blur_sigma": fixture.POST_BLUR_SIGMA,
            "usm_sigma": fixture.USM_SIGMA,
            "usm_amount": fixture.USM_AMOUNT,
            "scene_sha256": {
                name: fixture.array_sha256(scene)
                for name, scene in {
                    **scenes,
                    "adaptive_renoise_usm": attack_scene,
                    "flat": flat_scene,
                }.items()
            },
        },
        "measurements": measurements,
        "score_ratios": ratios,
        "local_score_ratios": local_ratios,
        "raw_coherent_ratios": raw_ratios,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "v2-commission.json"
    text_path = OUT / "v2-commission.txt"
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    lines = [
        "M189 PTC-anchored Q_sup held-out synthetic commissioning",
        f"base_score={measurements['base']['score']:.12g}",
        f"optical_improved/base={ratios['optical_improved']:.9f}",
        f"optical_degraded/base={ratios['optical_degraded']:.9f}",
        f"post_blur/base={ratios['post_blur']:.9f}",
        f"post_usm/base={ratios['post_usm']:.9f}",
        f"post_usm_local/base={local_ratios['post_usm']:.9f}",
        (
            "post_usm_raw_coherent/base="
            f"{raw_ratios['post_usm']:.9f}"
        ),
        (
            "post_usm_weighted_noise_gain="
            f"{measurements['post_usm']['weighted_noise_gain']:.9f}"
        ),
        (
            "post_usm_noise_gain_sup="
            f"{measurements['post_usm']['bin_gain_max']:.9f}"
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

