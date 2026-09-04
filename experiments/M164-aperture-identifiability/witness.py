"""Construct an aperture-ordering counterexample for detail identifiability."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "results.json"
SAMPLES = 256
SELECTED_BIN = 64
SELECTED_FREQUENCY = SELECTED_BIN / SAMPLES
APERTURES = (5.6, 8.0, 11.0)
DIFFRACTION_CUTOFFS = (0.5541, 0.3879, 0.2821)
USM_SIGMA_PX = 0.8
USM_AMOUNT = 0.75
USM_SWEEP = (0.0, 0.5, 1.0, 2.0)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def airy_mtf(frequencies: np.ndarray, cutoff: float) -> np.ndarray:
    normalized = frequencies / cutoff
    result = np.zeros_like(normalized)
    inside = normalized < 1.0
    values = normalized[inside]
    result[inside] = (2.0 / np.pi) * (
        np.arccos(values) - values * np.sqrt(1.0 - values**2)
    )
    return result


def usm_transfer(frequencies: np.ndarray, amount: float) -> np.ndarray:
    gaussian = np.exp(
        -2.0 * np.pi**2 * USM_SIGMA_PX**2 * frequencies**2
    )
    return 1.0 + amount * (1.0 - gaussian)


def render(
    spectrum: np.ndarray,
    optical_transfer: np.ndarray,
    postfilter: np.ndarray,
) -> np.ndarray:
    return np.fft.irfft(
        spectrum * optical_transfer * postfilter,
        n=SAMPLES,
    )


def selected_amplitude(image: np.ndarray) -> float:
    spectrum = np.fft.rfft(image)
    return float(2.0 * abs(spectrum[SELECTED_BIN]) / SAMPLES)


def strict_decrease(values: list[float]) -> bool:
    return all(first > second for first, second in zip(values, values[1:]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    arguments = parser.parse_args(argv)

    samples = np.arange(SAMPLES, dtype=np.float64)
    latent = 0.5 + 0.05 * np.cos(
        2.0 * np.pi * SELECTED_BIN * samples / SAMPLES
    )
    latent_spectrum = np.fft.rfft(latent)
    frequencies = np.fft.rfftfreq(SAMPLES)
    optical_transfers = [
        airy_mtf(frequencies, cutoff) for cutoff in DIFFRACTION_CUTOFFS
    ]
    identity = np.ones_like(frequencies)
    common_usm = usm_transfer(frequencies, USM_AMOUNT)

    unsharpened = [
        render(latent_spectrum, optical, identity)
        for optical in optical_transfers
    ]
    sharpened = [
        render(latent_spectrum, optical, common_usm)
        for optical in optical_transfers
    ]
    unsharpened_scores = [selected_amplitude(image) for image in unsharpened]
    sharpened_scores = [selected_amplitude(image) for image in sharpened]

    selected_airy = [
        float(optical[SELECTED_BIN]) for optical in optical_transfers
    ]
    predicted_relative = np.asarray(selected_airy) / selected_airy[0]
    observed_relative_unsharpened = (
        np.asarray(unsharpened_scores) / unsharpened_scores[0]
    )
    observed_relative_sharpened = (
        np.asarray(sharpened_scores) / sharpened_scores[0]
    )

    sharpened_latent_spectrum = latent_spectrum * common_usm
    sharpened_latent = np.fft.irfft(
        sharpened_latent_spectrum,
        n=SAMPLES,
    )
    world_postfilter = [
        render(latent_spectrum, optical, common_usm)
        for optical in optical_transfers
    ]
    world_latent_detail = [
        render(sharpened_latent_spectrum, optical, identity)
        for optical in optical_transfers
    ]
    world_errors = [
        float(np.max(np.abs(first - second)))
        for first, second in zip(world_postfilter, world_latent_detail)
    ]

    sweep: dict[str, Any] = {}
    for amount in USM_SWEEP:
        transfer = usm_transfer(frequencies, amount)
        scores = [
            selected_amplitude(
                render(latent_spectrum, optical, transfer)
            )
            for optical in optical_transfers
        ]
        sweep[f"{amount:.1f}"] = {
            "scores": scores,
            "aperture_order_passes": strict_decrease(scores),
        }

    optical_support = [
        int(np.count_nonzero(optical > 0.0))
        for optical in optical_transfers
    ]
    sharpened_support = [
        int(np.count_nonzero((optical * common_usm) > 0.0))
        for optical in optical_transfers
    ]
    checks = {
        "C1_diffraction_transfer_strictly_decreases": strict_decrease(
            selected_airy
        ),
        "C2_unsharpened_metric_recovers_aperture_order": strict_decrease(
            unsharpened_scores
        ),
        "C3_sharpened_metric_still_recovers_aperture_order": strict_decrease(
            sharpened_scores
        ),
        "C4_metric_rewards_sharpening_in_every_arm": all(
            sharpened > plain
            for sharpened, plain in zip(
                sharpened_scores, unsharpened_scores
            )
        ),
        "C5_relative_Airy_magnitude_survives_common_sharpening": bool(
            np.allclose(
                observed_relative_sharpened,
                predicted_relative,
                rtol=0.0,
                atol=1.0e-14,
            )
        ),
        "C6_two_world_observations_are_identical": max(world_errors)
        <= 1.0e-14,
        "C7_sharpening_restores_no_optical_support": (
            optical_support == sharpened_support
        ),
        "C8_aperture_order_survives_entire_USM_sweep": all(
            record["aperture_order_passes"] for record in sweep.values()
        ),
        "C9_metric_rises_monotonically_with_USM": all(
            all(
                sweep[f"{first:.1f}"]["scores"][arm]
                < sweep[f"{second:.1f}"]["scores"][arm]
                for first, second in zip(USM_SWEEP, USM_SWEEP[1:])
            )
            for arm in range(len(APERTURES))
        ),
    }

    result = {
        "schema": "m164-aperture-identifiability-v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "verdict": "OBJECTION_CORRECT",
        "captures_opened": 0,
        "construction": {
            "samples": SAMPLES,
            "selected_bin": SELECTED_BIN,
            "selected_frequency_cyc_per_px": SELECTED_FREQUENCY,
            "apertures": list(APERTURES),
            "diffraction_cutoffs_cyc_per_px": list(DIFFRACTION_CUTOFFS),
            "usm_sigma_px": USM_SIGMA_PX,
            "usm_amount": USM_AMOUNT,
            "latent_minimum": float(np.min(latent)),
            "latent_maximum": float(np.max(latent)),
            "sharpened_latent_minimum": float(np.min(sharpened_latent)),
            "sharpened_latent_maximum": float(np.max(sharpened_latent)),
        },
        "selected_frequency": {
            "Airy_MTF": selected_airy,
            "unsharpened_metric_scores": unsharpened_scores,
            "sharpened_metric_scores": sharpened_scores,
            "sharpening_reward_ratio": [
                sharpened / plain
                for sharpened, plain in zip(
                    sharpened_scores, unsharpened_scores
                )
            ],
            "predicted_relative_Airy": predicted_relative.tolist(),
            "observed_relative_unsharpened": (
                observed_relative_unsharpened.tolist()
            ),
            "observed_relative_sharpened": (
                observed_relative_sharpened.tolist()
            ),
            "maximum_relative_calibration_error": float(
                np.max(
                    np.abs(
                        observed_relative_sharpened - predicted_relative
                    )
                )
            ),
        },
        "two_world_witness": {
            "world_A": (
                "latent scene X, known aperture transfers H_i, common "
                "post-render sharpening K"
            ),
            "world_B": (
                "latent scene X'=KX, the same known aperture transfers H_i, "
                "identity postfilter"
            ),
            "identity": "K H_i X = H_i K X for common LSI K and H_i",
            "maximum_absolute_output_difference_by_aperture": world_errors,
            "maximum_absolute_output_difference": max(world_errors),
        },
        "sharpening_sweep": sweep,
        "support": {
            "nonzero_optical_bins": optical_support,
            "nonzero_bins_after_sharpening": sharpened_support,
        },
        "checks": checks,
        "source": {
            "witness_py_sha256": sha256(Path(__file__)),
            "diffraction_cutoff_source": (
                "docs/research/M5-diffraction-measured.md section 9.1"
            ),
        },
        "interpretation": (
            "Aperture order and relative Airy attenuation are preserved by "
            "a common sharpening transfer. They can reject a statistic that "
            "misses the intervention, but cannot identify whether the "
            "observed high-frequency amplitude came from the latent scene or "
            "the common renderer transfer."
        ),
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{result['status']}: {sum(checks.values())}/{len(checks)} checks; "
        f"verdict={result['verdict']}; "
        f"max_world_error={max(world_errors):.3e}; "
        "captures_opened=0"
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
