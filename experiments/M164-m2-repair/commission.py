"""Commission a truth-normalized comparative noise coordinate for M2."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")

import numpy as np
from scipy.ndimage import gaussian_filter, uniform_filter


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "commission.json"
PREREGISTRATION = HERE / "PREREGISTRATION.md"
AMENDMENT_1 = HERE / "AMENDMENT-1.md"

SEED = 164_200
TRIALS = 256
SITES = 64
FREQUENCIES = np.repeat(np.array([0.15, 0.20, 0.25]), 4)
ANGLES_DEG = np.tile(np.array([0.0, 22.5, 45.0, 67.5]), 3)
REFERENCE_NOISE_SD = 0.10
OUTPUT_NOISE_SD = 0.45
BASE_SIGMA = 0.65


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def complex_normal(
    rng: np.random.Generator, shape: tuple[int, ...], sd: float
) -> np.ndarray:
    return sd * (
        rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    ) / math.sqrt(2.0)


def complex_cov(a: np.ndarray, b: np.ndarray) -> complex:
    ac = a - np.mean(a)
    bc = b - np.mean(b)
    return np.mean(ac * np.conj(bc))


def optical_transfer(sigma: float) -> np.ndarray:
    return np.exp(-2.0 * np.pi**2 * sigma**2 * FREQUENCIES**2)


def output_pair(
    rng: np.random.Generator,
    signal: np.ndarray,
    transfer: np.ndarray,
    noise_sd: float,
) -> tuple[np.ndarray, np.ndarray]:
    shape = signal.shape
    return (
        signal * transfer[np.newaxis, :] + complex_normal(rng, shape, noise_sd),
        signal * transfer[np.newaxis, :] + complex_normal(rng, shape, noise_sd),
    )


def cell_metrics(
    reference: tuple[np.ndarray, np.ndarray],
    output: tuple[np.ndarray, np.ndarray],
) -> dict[str, np.ndarray]:
    r1, r2 = reference
    y1, y2 = output
    reference_power = []
    transfer = []
    noise_power = []
    equivalent_input_noise = []

    for cell in range(r1.shape[1]):
        pr = float(np.real(complex_cov(r1[:, cell], r2[:, cell])))
        cross = np.mean(
            [
                complex_cov(y1[:, cell], r1[:, cell]),
                complex_cov(y1[:, cell], r2[:, cell]),
                complex_cov(y2[:, cell], r1[:, cell]),
                complex_cov(y2[:, cell], r2[:, cell]),
            ]
        )
        pn = 0.5 * float(np.mean(np.abs(y1[:, cell] - y2[:, cell]) ** 2))
        if pr <= 0.0 or pn <= 0.0:
            raise RuntimeError("synthetic cell unexpectedly lacks reference/noise power")
        t = float(abs(cross) / pr)
        if t <= 0.0:
            raise RuntimeError("synthetic cell unexpectedly has zero transfer")
        reference_power.append(pr)
        transfer.append(t)
        noise_power.append(pn)
        equivalent_input_noise.append(math.sqrt(pn) / t)

    return {
        "reference_power": np.asarray(reference_power),
        "transfer": np.asarray(transfer),
        "noise_power": np.asarray(noise_power),
        "equivalent_input_noise": np.asarray(equivalent_input_noise),
    }


def geometric_mean(values: np.ndarray) -> float:
    if np.any(values <= 0.0):
        raise RuntimeError("geometric mean requires positive values")
    return float(np.exp(np.mean(np.log(values))))


def compare(
    arm: dict[str, np.ndarray], baseline: dict[str, np.ndarray]
) -> dict[str, float]:
    return {
        "q_ein": geometric_mean(
            arm["equivalent_input_noise"]
            / baseline["equivalent_input_noise"]
        ),
        "naive_output_noise_ratio": geometric_mean(
            np.sqrt(arm["noise_power"] / baseline["noise_power"])
        ),
        "transfer_ratio": geometric_mean(
            arm["transfer"] / baseline["transfer"]
        ),
    }


def postfilter(
    output: tuple[np.ndarray, np.ndarray], gain: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    return output[0] * gain[np.newaxis, :], output[1] * gain[np.newaxis, :]


def trial(seed: int) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(seed)
    shape = (SITES, len(FREQUENCIES))
    signal = complex_normal(rng, shape, 1.0)
    reference = (
        signal + complex_normal(rng, shape, REFERENCE_NOISE_SD),
        signal + complex_normal(rng, shape, REFERENCE_NOISE_SD),
    )

    base_h = optical_transfer(BASE_SIGMA)
    baseline_output = output_pair(rng, signal, base_h, OUTPUT_NOISE_SD)
    baseline = cell_metrics(reference, baseline_output)

    arms: dict[str, tuple[np.ndarray, np.ndarray]] = {
        "identity": baseline_output,
        "fresh_null": output_pair(rng, signal, base_h, OUTPUT_NOISE_SD),
        "noise_degradation": output_pair(
            rng, signal, base_h, 1.5 * OUTPUT_NOISE_SD
        ),
        "denoising_improvement": output_pair(
            rng, signal, base_h, 0.5 * OUTPUT_NOISE_SD
        ),
        "pre_noise_blur": output_pair(
            rng, signal, optical_transfer(1.05), OUTPUT_NOISE_SD
        ),
        "blur_plus_denoise": output_pair(
            rng, signal, optical_transfer(1.05), 0.15
        ),
        "optical_improvement": output_pair(
            rng, signal, optical_transfer(0.30), OUTPUT_NOISE_SD
        ),
    }

    blur_gain = optical_transfer(0.75)
    usm_gain = 1.0 + 0.75 * (
        1.0 - np.exp(-2.0 * np.pi**2 * 1.0**2 * FREQUENCIES**2)
    )
    arms["post_blur"] = postfilter(baseline_output, blur_gain)
    arms["post_usm"] = postfilter(baseline_output, usm_gain)
    arms["post_gain"] = postfilter(
        baseline_output, np.full_like(FREQUENCIES, 1.0007)
    )

    return {
        name: compare(cell_metrics(reference, output), baseline)
        for name, output in arms.items()
    }


def summary(values: list[float]) -> dict[str, float | int]:
    a = np.asarray(values, dtype=np.float64)
    logs = np.log(a)
    mean_log = float(np.mean(logs))
    standard_error = float(np.std(logs, ddof=1) / math.sqrt(len(logs)))
    return {
        "minimum": float(np.min(a)),
        "q05": float(np.quantile(a, 0.05)),
        "median": float(np.median(a)),
        "geometric_mean": float(np.exp(mean_log)),
        "ci95_low": float(np.exp(mean_log - 1.96 * standard_error)),
        "ci95_high": float(np.exp(mean_log + 1.96 * standard_error)),
        "q95": float(np.quantile(a, 0.95)),
        "maximum": float(np.max(a)),
        "below_one": int(np.sum(a < 1.0)),
        "above_one": int(np.sum(a > 1.0)),
        "max_abs_from_one": float(np.max(np.abs(a - 1.0))),
    }


def box9_fractional(image: np.ndarray) -> float:
    local_mean = uniform_filter(image, 9)
    return float(np.std(image / local_mean - 1.0))


def box9_additive_over_mean(image: np.ndarray) -> float:
    local_mean = uniform_filter(image, 9)
    return float(np.std(image - local_mean) / np.mean(image))


def m159_mechanism_probe() -> dict[str, float | str]:
    rng = np.random.default_rng(SEED + 9_000_000)
    height = width = 384
    yy, xx = np.mgrid[0:height, 0:width]
    latent = (
        0.42
        + 0.035 * (xx / (width - 1) - 0.5)
        - 0.025 * (yy / (height - 1) - 0.5)
        + 0.002 * np.sin(2 * np.pi * xx / 160.0)
        + 0.025 * np.sin(2 * np.pi * xx / 6.0)
    )
    noisy = latent + rng.normal(0.0, 0.004, latent.shape)
    blurred = gaussian_filter(noisy, 1.0)
    noisy_local_mean = uniform_filter(noisy, 9)
    blurred_local_mean = uniform_filter(blurred, 9)

    return {
        "construction": (
            "M159-form six-pixel texture plus independent Gaussian noise, "
            "then Gaussian blur sigma=1.0 px"
        ),
        "fractional_r_box9_blurred_over_unblurred": (
            box9_fractional(blurred) / box9_fractional(noisy)
        ),
        "additive_box9_over_global_mean_blurred_over_unblurred": (
            box9_additive_over_mean(blurred) / box9_additive_over_mean(noisy)
        ),
        "median_local_mean_blurred_over_unblurred": float(
            np.median(blurred_local_mean) / np.median(noisy_local_mean)
        ),
    }


def radial_bandpass(image: np.ndarray) -> np.ndarray:
    fy = np.fft.fftfreq(image.shape[0])[:, np.newaxis]
    fx = np.fft.rfftfreq(image.shape[1])[np.newaxis, :]
    radius = np.sqrt(fx**2 + fy**2)
    mask = (radius >= 0.15) & (radius <= 0.35)
    spectrum = np.fft.rfft2(image)
    return np.fft.irfft2(spectrum * mask, s=image.shape)


def robust_band_residual(first: np.ndarray, second: np.ndarray) -> float:
    residual = radial_bandpass(first - second)
    median = float(np.median(residual))
    return 1.4826 * float(np.median(np.abs(residual - median)))


def band_truth_error(image: np.ndarray, truth: np.ndarray) -> float:
    residual = radial_bandpass(image - truth)
    return float(np.sqrt(np.mean(residual**2)))


def same_resolution_crossfit_probe() -> dict[str, Any]:
    ratios = {
        "blur_crossfit": [],
        "optical_improvement_crossfit": [],
        "denoising_improvement_crossfit": [],
        "blur_truth_error": [],
        "optical_improvement_truth_error": [],
    }
    for index in range(64):
        rng = np.random.default_rng(SEED + 10_000_000 + index)
        white = rng.standard_normal((128, 128))
        truth = 0.42 + 0.035 * (
            gaussian_filter(white, 0.25) / np.std(white)
        )
        captured = gaussian_filter(truth, BASE_SIGMA)
        blurred_signal = gaussian_filter(truth, 1.05)
        improved_signal = gaussian_filter(truth, 0.30)
        noise_sd = 0.004 / math.sqrt(16.0)
        reference = captured + rng.normal(0.0, noise_sd, truth.shape)
        baseline = captured + rng.normal(0.0, noise_sd, truth.shape)
        blurred = blurred_signal + rng.normal(0.0, noise_sd, truth.shape)
        improved = improved_signal + rng.normal(0.0, noise_sd, truth.shape)
        denoised = captured + rng.normal(0.0, 0.5 * noise_sd, truth.shape)

        base_crossfit = robust_band_residual(baseline, reference)
        base_truth = band_truth_error(baseline, truth)
        ratios["blur_crossfit"].append(
            robust_band_residual(blurred, reference) / base_crossfit
        )
        ratios["optical_improvement_crossfit"].append(
            robust_band_residual(improved, reference) / base_crossfit
        )
        ratios["denoising_improvement_crossfit"].append(
            robust_band_residual(denoised, reference) / base_crossfit
        )
        ratios["blur_truth_error"].append(
            band_truth_error(blurred, truth) / base_truth
        )
        ratios["optical_improvement_truth_error"].append(
            band_truth_error(improved, truth) / base_truth
        )

    return {
        "construction": (
            "same-resolution held-out reference carries baseline sigma=0.65 "
            "capture transfer; radial BP is 0.15-0.35 cyc/px"
        ),
        "trials": 64,
        "summaries": {name: summary(values) for name, values in ratios.items()},
        "raw_ratios": ratios,
    }


def main() -> None:
    rows = [trial(SEED + index) for index in range(TRIALS)]
    arm_names = tuple(rows[0])
    fields = ("q_ein", "naive_output_noise_ratio", "transfer_ratio")
    raw = {
        arm: {
            field: [float(row[arm][field]) for row in rows]
            for field in fields
        }
        for arm in arm_names
    }
    summaries = {
        arm: {field: summary(raw[arm][field]) for field in fields}
        for arm in arm_names
    }
    mechanism = m159_mechanism_probe()
    crossfit = same_resolution_crossfit_probe()

    gates = {
        "G0_identity": summaries["identity"]["q_ein"]["max_abs_from_one"]
        <= 1e-12,
        "G1_movable_null": (
            summaries["fresh_null"]["q_ein"]["minimum"] < 1.0
            < summaries["fresh_null"]["q_ein"]["maximum"]
            and 0.98
            <= summaries["fresh_null"]["q_ein"]["geometric_mean"]
            <= 1.02
        ),
        "G2_noise_degradation": (
            summaries["noise_degradation"]["q_ein"]["below_one"] == 0
            and summaries["noise_degradation"]["q_ein"]["q05"] > 1.20
        ),
        "G3_denoising_improvement": (
            summaries["denoising_improvement"]["q_ein"]["above_one"] == 0
            and summaries["denoising_improvement"]["q_ein"]["q95"] < 0.75
        ),
        "G4_pre_noise_blur": (
            summaries["pre_noise_blur"]["q_ein"]["below_one"] == 0
            and summaries["pre_noise_blur"]["q_ein"]["q05"] > 1.20
        ),
        "G5_optical_improvement": (
            summaries["optical_improvement"]["q_ein"]["above_one"] == 0
            and summaries["optical_improvement"]["q_ein"]["q95"] < 0.90
        ),
        "G6_post_blur_invariance": (
            summaries["post_blur"]["q_ein"]["max_abs_from_one"] <= 1e-12
            and summaries["post_blur"]["naive_output_noise_ratio"]["maximum"]
            < 0.90
        ),
        "G7_post_usm_invariance": (
            summaries["post_usm"]["q_ein"]["max_abs_from_one"] <= 1e-12
        ),
        "G8_gain_invariance": (
            summaries["post_gain"]["q_ein"]["max_abs_from_one"] <= 1e-12
        ),
        "G9_m159_mechanism": (
            mechanism["fractional_r_box9_blurred_over_unblurred"] < 0.90
            and mechanism[
                "additive_box9_over_global_mean_blurred_over_unblurred"
            ]
            < 0.90
            and 0.99
            <= mechanism["median_local_mean_blurred_over_unblurred"]
            <= 1.01
        ),
        "G10_blur_plus_denoise_requires_m1": (
            summaries["blur_plus_denoise"]["q_ein"]["q95"] < 0.80
            and summaries["blur_plus_denoise"]["transfer_ratio"]["q95"] < 0.70
        ),
        "G11_same_resolution_crossfit_fails_improvement": (
            crossfit["summaries"]["blur_crossfit"]["q05"] > 1.10
            and crossfit["summaries"]["optical_improvement_crossfit"]["q05"]
            > 1.10
            and crossfit["summaries"]["optical_improvement_truth_error"]["q95"]
            < 0.90
            and crossfit["summaries"]["blur_truth_error"]["q05"] > 1.10
            and crossfit["summaries"]["denoising_improvement_crossfit"]["q95"]
            < 0.90
        ),
    }

    result: dict[str, Any] = {
        "schema": "m164-m2-repair-commission-v1",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "scope": (
            "synthetic commissioning of equivalent-input noise arithmetic; "
            "not a production M2 score or an M1 replacement"
        ),
        "seed": SEED,
        "trials": TRIALS,
        "sites_per_trial": SITES,
        "frequencies_cyc_per_native_px": FREQUENCIES.tolist(),
        "angles_deg": ANGLES_DEG.tolist(),
        "model": {
            "reference_noise_sd": REFERENCE_NOISE_SD,
            "baseline_output_noise_sd": OUTPUT_NOISE_SD,
            "baseline_optical_sigma_px": BASE_SIGMA,
        },
        "statistic": {
            "name": "Q_EIN",
            "cell_reference_power": "Re Cov(R1,R2)",
            "cell_transfer": (
                "|mean(Cov(Y1,R1),Cov(Y1,R2),Cov(Y2,R1),Cov(Y2,R2))| "
                "/ P_R"
            ),
            "cell_noise_power": "0.5 mean |Y1-Y2|^2",
            "cell_equivalent_input_noise": "sqrt(P_N) / T",
            "reduction": (
                "equal-weight geometric mean across 12 preregistered "
                "frequency/orientation cells"
            ),
            "direction": "candidate/comparator; below one is better",
        },
        "summaries": summaries,
        "m159_mechanism_probe": mechanism,
        "same_resolution_crossfit_probe": crossfit,
        "raw_trial_ratios": raw,
        "gates": gates,
        "source_hashes": {
            "preregistration_sha256": sha256(PREREGISTRATION),
            "amendment_1_sha256": sha256(AMENDMENT_1),
            "commission_py_sha256": sha256(Path(__file__)),
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"{result['status']}: {sum(gates.values())}/{len(gates)} gates; "
        f"null={summaries['fresh_null']['q_ein']['geometric_mean']:.6f}; "
        f"noise={summaries['noise_degradation']['q_ein']['geometric_mean']:.6f}; "
        f"denoise={summaries['denoising_improvement']['q_ein']['geometric_mean']:.6f}; "
        f"post-blur={summaries['post_blur']['q_ein']['geometric_mean']:.12f}"
    )


if __name__ == "__main__":
    main()
