"""Exploratory 64-site power and window-residual probe for repeat-pair FRC."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments" / "M-PHASE0-SPLIT2"))

import frc  # noqa: E402


SITES = 64
PRIMARY_SEED = 20260904
FRESH_SEED = 20260906


def exact_fourier_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    n = image.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.rfftfreq(n)[None, :]
    mtf = np.exp(-2.0 * math.pi**2 * sigma**2 * (fx * fx + fy * fy))
    return np.fft.irfft2(np.fft.rfft2(image) * mtf, s=image.shape)


def aggregate(rows: list[frc.Spectrum], indices: np.ndarray | None = None) -> frc.Spectrum:
    selected = rows if indices is None else [rows[int(index)] for index in indices]
    result = frc.Spectrum.zeros(selected[0].count.size)
    for row in selected:
        result.add(row)
    return result


def measured_crossing(spectrum: frc.Spectrum) -> float | None:
    result = frc.classify(spectrum)
    if result["outcome"] != "MEASURED":
        return None
    return float(result["frequency_or_bound"])


def bootstrap_delta(
    base: list[frc.Spectrum],
    arm: list[frc.Spectrum],
    *,
    draws: int,
    seed: int,
) -> dict[str, object]:
    base_aggregate = aggregate(base)
    arm_aggregate = aggregate(arm)
    base_crossing = measured_crossing(base_aggregate)
    arm_crossing = measured_crossing(arm_aggregate)
    if base_crossing is None or arm_crossing is None:
        point_delta = None
    else:
        point_delta = arm_crossing - base_crossing

    indices = np.random.default_rng(seed).integers(0, SITES, size=(draws, SITES))
    deltas = []
    for sample in indices:
        sampled_base = measured_crossing(aggregate(base, sample))
        sampled_arm = measured_crossing(aggregate(arm, sample))
        if sampled_base is not None and sampled_arm is not None:
            deltas.append(sampled_arm - sampled_base)

    base_frc = base_aggregate.frc()
    arm_frc = arm_aggregate.frc()
    valid = np.isfinite(base_frc) & np.isfinite(arm_frc)
    interval = (
        [float(value) for value in np.quantile(deltas, [0.025, 0.975])]
        if deltas
        else None
    )
    return {
        "base_crossing": base_crossing,
        "arm_crossing": arm_crossing,
        "crossing_delta": point_delta,
        "delta_bootstrap_95": interval,
        "measured_bootstrap_fraction": len(deltas) / draws,
        "maximum_ring_frc_movement": float(
            np.max(np.abs(base_frc[valid] - arm_frc[valid]))
        ),
    }


def paired_probe(tile: int) -> dict[str, object]:
    pad = max(32, tile // 2)
    support = tile + 2 * pad
    crop = np.s_[pad : pad + tile, pad : pad + tile]
    rng = np.random.default_rng(PRIMARY_SEED + tile)
    rows = {
        name: []
        for name in (
            "base",
            "post_usm_amount_1_5",
            "post_blur_sigma_2",
            "pre_blur_sigma_0_1",
            "pre_blur_sigma_0_2",
            "pre_blur_sigma_0_3",
            "pre_improve_amount_0_05",
            "pre_improve_amount_0_1",
        )
    }

    for _ in range(SITES):
        signal = 18.0 * exact_fourier_blur(rng.normal(size=(support, support)), 1.8)
        noise_a = 1.2 * rng.normal(size=(support, support))
        noise_b = 1.2 * rng.normal(size=(support, support))
        image_a = signal + noise_a
        image_b = signal + noise_b

        rows["base"].append(frc.spectrum_tile(image_a[crop], image_b[crop]))
        rows["post_usm_amount_1_5"].append(
            frc.spectrum_tile(
                frc.unsharp(image_a, 1.5)[crop],
                frc.unsharp(image_b, 1.5)[crop],
            )
        )
        rows["post_blur_sigma_2"].append(
            frc.spectrum_tile(
                exact_fourier_blur(image_a, 2.0)[crop],
                exact_fourier_blur(image_b, 2.0)[crop],
            )
        )
        for sigma, key in (
            (0.1, "pre_blur_sigma_0_1"),
            (0.2, "pre_blur_sigma_0_2"),
            (0.3, "pre_blur_sigma_0_3"),
        ):
            latent = exact_fourier_blur(signal, sigma)
            rows[key].append(
                frc.spectrum_tile((latent + noise_a)[crop], (latent + noise_b)[crop])
            )

        latent_blur = exact_fourier_blur(signal, 1.0)
        for amount, key in (
            (0.05, "pre_improve_amount_0_05"),
            (0.1, "pre_improve_amount_0_1"),
        ):
            latent = signal + amount * (signal - latent_blur)
            rows[key].append(
                frc.spectrum_tile((latent + noise_a)[crop], (latent + noise_b)[crop])
            )

    return {
        "tile": tile,
        "support": support,
        "ring_spacing": 1.0 / tile,
        "sites": SITES,
        "bootstrap_draws": 3000,
        "seed": PRIMARY_SEED + tile,
        "arms": {
            name: bootstrap_delta(
                rows["base"],
                arm,
                draws=3000,
                seed=PRIMARY_SEED + tile + 7,
            )
            for name, arm in rows.items()
            if name != "base"
        },
    }


def fresh_noise_probe() -> dict[str, object]:
    tile = 256
    pad = 128
    support = 512
    crop = np.s_[pad : pad + tile, pad : pad + tile]
    rng = np.random.default_rng(FRESH_SEED)
    names = (
        "base",
        "pre_blur_sigma_0_1",
        "pre_blur_sigma_0_2",
        "pre_blur_sigma_0_3",
        "pre_blur_sigma_0_5",
        "pre_improve_amount_0_05",
        "pre_improve_amount_0_1",
        "pre_improve_amount_0_2",
    )
    rows = {name: [] for name in names}

    for _ in range(SITES):
        signal = 18.0 * exact_fourier_blur(rng.normal(size=(support, support)), 1.8)
        blurred = exact_fourier_blur(signal, 1.0)
        latents = {
            "base": signal,
            "pre_blur_sigma_0_1": exact_fourier_blur(signal, 0.1),
            "pre_blur_sigma_0_2": exact_fourier_blur(signal, 0.2),
            "pre_blur_sigma_0_3": exact_fourier_blur(signal, 0.3),
            "pre_blur_sigma_0_5": exact_fourier_blur(signal, 0.5),
            "pre_improve_amount_0_05": signal + 0.05 * (signal - blurred),
            "pre_improve_amount_0_1": signal + 0.1 * (signal - blurred),
            "pre_improve_amount_0_2": signal + 0.2 * (signal - blurred),
        }
        for name, latent in latents.items():
            image_a = latent + 1.2 * rng.normal(size=(support, support))
            image_b = latent + 1.2 * rng.normal(size=(support, support))
            rows[name].append(frc.spectrum_tile(image_a[crop], image_b[crop]))

    return {
        "tile": tile,
        "support": support,
        "sites": SITES,
        "bootstrap_draws": 5000,
        "seed": FRESH_SEED,
        "arms": {
            name: bootstrap_delta(
                rows["base"],
                arm,
                draws=5000,
                seed=FRESH_SEED + 123,
            )
            for name, arm in rows.items()
            if name != "base"
        },
    }


def postfilter_replication() -> dict[str, object]:
    tile = 256
    pad = 128
    support = 512
    crop = np.s_[pad : pad + tile, pad : pad + tile]
    rng = np.random.default_rng(FRESH_SEED + 999)
    rows = {
        name: []
        for name in (
            "base",
            "post_blur_sigma_0_5",
            "post_blur_sigma_1",
            "post_blur_sigma_2",
        )
    }

    for _ in range(SITES):
        signal = 18.0 * exact_fourier_blur(rng.normal(size=(support, support)), 1.8)
        image_a = signal + 1.2 * rng.normal(size=(support, support))
        image_b = signal + 1.2 * rng.normal(size=(support, support))
        rows["base"].append(frc.spectrum_tile(image_a[crop], image_b[crop]))
        for sigma, key in (
            (0.5, "post_blur_sigma_0_5"),
            (1.0, "post_blur_sigma_1"),
            (2.0, "post_blur_sigma_2"),
        ):
            rows[key].append(
                frc.spectrum_tile(
                    exact_fourier_blur(image_a, sigma)[crop],
                    exact_fourier_blur(image_b, sigma)[crop],
                )
            )

    return {
        "tile": tile,
        "support": support,
        "sites": SITES,
        "bootstrap_draws": 5000,
        "seed": FRESH_SEED + 999,
        "arms": {
            name: bootstrap_delta(
                rows["base"],
                arm,
                draws=5000,
                seed=FRESH_SEED + 123,
            )
            for name, arm in rows.items()
            if name != "base"
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {
        "schema": 1,
        "status": "EXPLORATORY_NOT_ADMISSION_EVIDENCE",
        "implementation": "experiments/M-PHASE0-SPLIT2/frc.py",
        "paired_common_noise": {
            "tile_64": paired_probe(64),
            "tile_256": paired_probe(256),
        },
        "fresh_arm_noise": fresh_noise_probe(),
        "postfilter_replication": postfilter_replication(),
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
