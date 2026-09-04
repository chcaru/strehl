"""Run the frozen M135 synthetic commissioning battery."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.interpolate import PchipInterpolator

from instrument import (
    ANGLES_DEG,
    FREQUENCIES,
    CaptureSet,
    evaluate,
    postfilter,
    rotate_cells,
)


MASTER_SEED = 135135
TRIALS = 128
SITE_COUNT = 64
SAMPLE_SIZE_LADDER = (64, 128, 256, 512)
REFERENCE_NOISE_SD = 0.10
OUTPUT_NOISE_SD = 0.45


def complex_normal(rng: np.random.Generator, shape: tuple[int, ...], sd: float) -> np.ndarray:
    return sd * (
        rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    ) / np.sqrt(2.0)


def optical_transfer(sigma: float) -> np.ndarray:
    return np.exp(-2.0 * np.pi**2 * sigma**2 * FREQUENCIES**2)


def make_capture(
    rng: np.random.Generator,
    n: int = SITE_COUNT,
    sigma: float = 0.65,
    output_noise_sd: float = OUTPUT_NOISE_SD,
    signal: np.ndarray | None = None,
    reference_noise: tuple[np.ndarray, np.ndarray] | None = None,
    output_noise: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[CaptureSet, dict[str, np.ndarray]]:
    shape = (n, len(FREQUENCIES))
    if signal is None:
        signal = complex_normal(rng, shape, 1.0)
    if reference_noise is None:
        reference_noise = (
            complex_normal(rng, shape, REFERENCE_NOISE_SD),
            complex_normal(rng, shape, REFERENCE_NOISE_SD),
        )
    if output_noise is None:
        output_noise = (
            complex_normal(rng, shape, output_noise_sd),
            complex_normal(rng, shape, output_noise_sd),
        )
    h = optical_transfer(sigma)
    captures = CaptureSet(
        reference_a=signal + reference_noise[0],
        reference_b=signal + reference_noise[1],
        output_a=signal * h[np.newaxis, :] + output_noise[0],
        output_b=signal * h[np.newaxis, :] + output_noise[1],
    )
    components = {
        "signal": signal,
        "reference_noise_a": reference_noise[0],
        "reference_noise_b": reference_noise[1],
        "output_noise_a": output_noise[0],
        "output_noise_b": output_noise[1],
    }
    return captures, components


def rebuild(
    components: dict[str, np.ndarray],
    sigma: float,
    output_noise_sd: float | None = None,
    rng: np.random.Generator | None = None,
) -> CaptureSet:
    signal = components["signal"]
    if output_noise_sd is None:
        na = components["output_noise_a"]
        nb = components["output_noise_b"]
    else:
        if rng is None:
            raise ValueError("rng required for fresh output noise")
        na = complex_normal(rng, signal.shape, output_noise_sd)
        nb = complex_normal(rng, signal.shape, output_noise_sd)
    h = optical_transfer(sigma)
    return CaptureSet(
        reference_a=signal + components["reference_noise_a"],
        reference_b=signal + components["reference_noise_b"],
        output_a=signal * h[np.newaxis, :] + na,
        output_b=signal * h[np.newaxis, :] + nb,
    )


def require_ok(result: dict) -> float:
    if result["status"] != "OK":
        raise RuntimeError(f"expected OK, got {result['status']}")
    return float(result["information_bits_per_site"])


def ratio(arm: dict, base: dict, field: str = "information_bits_per_site") -> float:
    return float(arm[field]) / float(base[field])


def log_mean_ci(values: list[float]) -> dict[str, float]:
    logs = np.log(np.asarray(values))
    mean = float(np.mean(logs))
    se = float(np.std(logs, ddof=1) / np.sqrt(len(logs)))
    return {
        "geometric_mean": float(np.exp(mean)),
        "ci95_low": float(np.exp(mean - 1.96 * se)),
        "ci95_high": float(np.exp(mean + 1.96 * se)),
        "q05": float(np.quantile(values, 0.05)),
        "q95": float(np.quantile(values, 0.95)),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
    }


def component_map(z: np.ndarray, fn: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    return fn(z.real) + 1j * fn(z.imag)


def tone_roundtrip(
    z: np.ndarray, tone: Callable[[np.ndarray], np.ndarray]
) -> tuple[np.ndarray, float]:
    scale = 0.075
    to_unit = lambda x: np.clip(0.5 + scale * x, 0.02, 0.98)
    from_unit = lambda u: (u - 0.5) / scale
    knots = np.linspace(0.0, 1.0, 33)
    encoded_knots = tone(knots)
    inverse = PchipInterpolator(encoded_knots, knots, extrapolate=False)

    def one_component(x: np.ndarray) -> np.ndarray:
        u = to_unit(x)
        encoded = tone(u)
        decoded = inverse(encoded)
        if np.any(~np.isfinite(decoded)):
            raise RuntimeError("tone witness did not span encoded samples")
        return from_unit(decoded)

    restored = component_map(z, one_component)
    raw = component_map(z, lambda x: from_unit(tone(to_unit(x))))
    potency = float(np.sqrt(np.mean(abs(raw - z) ** 2)) / np.sqrt(np.mean(abs(z) ** 2)))
    return restored, potency


def gamma3(u: np.ndarray) -> np.ndarray:
    return u**3


def logistic8(u: np.ndarray) -> np.ndarray:
    lo = 1.0 / (1.0 + np.exp(4.0))
    hi = 1.0 / (1.0 + np.exp(-4.0))
    value = 1.0 / (1.0 + np.exp(-8.0 * (u - 0.5)))
    return (value - lo) / (hi - lo)


def tone_capture(captures: CaptureSet, tone: Callable[[np.ndarray], np.ndarray]) -> tuple[CaptureSet, float]:
    ya, pa = tone_roundtrip(captures.output_a, tone)
    yb, pb = tone_roundtrip(captures.output_b, tone)
    return replace(captures, output_a=ya, output_b=yb), max(pa, pb)


def score_arm(captures: CaptureSet) -> dict:
    return evaluate(captures)


def run_trial(seed: int) -> dict[str, dict]:
    rng = np.random.default_rng(seed)
    base_capture, components = make_capture(rng)
    base = score_arm(base_capture)
    require_ok(base)

    identity = score_arm(replace(base_capture))
    blur = score_arm(rebuild(components, sigma=1.05))
    improvement = score_arm(rebuild(components, sigma=0.30))

    fresh_null_capture = rebuild(
        components, sigma=0.65, output_noise_sd=OUTPUT_NOISE_SD, rng=rng
    )
    fresh_null = score_arm(fresh_null_capture)

    usm_gain = 1.0 + 0.75 * (
        1.0 - np.exp(-2.0 * np.pi**2 * 1.0**2 * FREQUENCIES**2)
    )
    usm = score_arm(postfilter(base_capture, usm_gain))

    blur_gain = np.exp(-2.0 * np.pi**2 * 0.75**2 * FREQUENCIES**2)
    post_blur = score_arm(postfilter(base_capture, blur_gain))

    gamma_capture, gamma_potency = tone_capture(base_capture, gamma3)
    gamma = score_arm(gamma_capture)
    logistic_capture, logistic_potency = tone_capture(base_capture, logistic8)
    logistic = score_arm(logistic_capture)

    extra_noise = replace(
        base_capture,
        output_a=base_capture.output_a
        + complex_normal(rng, base_capture.output_a.shape, 0.70),
        output_b=base_capture.output_b
        + complex_normal(rng, base_capture.output_b.shape, 0.70),
    )
    noisy = score_arm(extra_noise)

    common = complex_normal(rng, base_capture.output_a.shape, 0.80)
    common_capture = replace(
        base_capture,
        output_a=base_capture.output_a + common,
        output_b=base_capture.output_b + common,
    )
    common_result = score_arm(common_capture)

    hallucination = np.zeros_like(base_capture.output_a)
    low = components["signal"][:, 0]
    invented = 1.0 * (
        (abs(low) ** 2 - np.mean(abs(low) ** 2))
        + 1j * (low.real * low.imag - np.mean(low.real * low.imag))
    )
    hallucination[:, 12:16] = invented[:, np.newaxis]
    hallucination_capture = replace(
        base_capture,
        output_a=base_capture.output_a + hallucination,
        output_b=base_capture.output_b + hallucination,
    )
    hallucination_result = score_arm(hallucination_capture)

    averaging_capture = rebuild(
        components, sigma=np.sqrt(0.65**2 + 0.55**2), output_noise_sd=0.18, rng=rng
    )
    averaging = score_arm(averaging_capture)

    angle = score_arm(rotate_cells(base_capture, 1))

    perm = np.random.default_rng(seed + 9_000_000).permutation(SITE_COUNT)
    permuted_reference = replace(
        base_capture,
        reference_a=base_capture.reference_a[perm],
        reference_b=base_capture.reference_b[perm],
    )
    permutation_result = score_arm(permuted_reference)

    return {
        "base": base,
        "identity": identity,
        "fresh_null": fresh_null,
        "blur": blur,
        "improvement": improvement,
        "usm": usm,
        "post_blur": post_blur,
        "gamma": gamma,
        "logistic": logistic,
        "noise": noisy,
        "common": common_result,
        "hallucination": hallucination_result,
        "averaging": averaging,
        "angle": angle,
        "permutation": permutation_result,
        "tone_potency": {
            "gamma": gamma_potency,
            "logistic": logistic_potency,
        },
    }


def refusal_trials() -> dict[str, dict]:
    rng = np.random.default_rng(MASTER_SEED + 77_000_000)
    base_capture, components = make_capture(rng)

    flat_results = []
    periodic_results = []
    for _ in range(TRIALS):
        flat_shape = base_capture.reference_a.shape
        flat_signal = np.zeros(flat_shape, dtype=np.complex128)
        flat_capture, _ = make_capture(rng, signal=flat_signal)
        flat_results.append(score_arm(flat_capture))

        template = complex_normal(rng, (1, len(FREQUENCIES)), 1.0)
        periodic_signal = np.repeat(template, SITE_COUNT, axis=0)
        periodic_capture, _ = make_capture(rng, signal=periodic_signal)
        periodic_capture = replace(periodic_capture, target_lineage="periodic")
        periodic_results.append(score_arm(periodic_capture))

    all_components = np.concatenate(
        [
            base_capture.output_a.real.ravel(),
            base_capture.output_a.imag.ravel(),
            base_capture.output_b.real.ravel(),
            base_capture.output_b.imag.ravel(),
        ]
    )
    rail = float(np.quantile(abs(all_components), 0.985))

    def clip(z: np.ndarray) -> np.ndarray:
        return np.clip(z.real, -rail, rail) + 1j * np.clip(z.imag, -rail, rail)

    clipped_a = clip(base_capture.output_a)
    clipped_b = clip(base_capture.output_b)
    changed = np.count_nonzero(clipped_a != base_capture.output_a) + np.count_nonzero(
        clipped_b != base_capture.output_b
    )
    total = clipped_a.size + clipped_b.size
    clipped_capture = replace(
        base_capture,
        output_a=clipped_a,
        output_b=clipped_b,
        clip_fraction=changed / total,
    )

    quantized_capture = replace(base_capture, effective_bits=8)
    shared_reference_capture = replace(base_capture, calibration_correlation=0.20)

    shared_flat_pattern = complex_normal(rng, base_capture.reference_a.shape, 0.80)
    shared_flat_capture = CaptureSet(
        reference_a=shared_flat_pattern
        + complex_normal(rng, shared_flat_pattern.shape, REFERENCE_NOISE_SD),
        reference_b=shared_flat_pattern
        + complex_normal(rng, shared_flat_pattern.shape, REFERENCE_NOISE_SD),
        output_a=shared_flat_pattern
        + complex_normal(rng, shared_flat_pattern.shape, OUTPUT_NOISE_SD),
        output_b=shared_flat_pattern
        + complex_normal(rng, shared_flat_pattern.shape, OUTPUT_NOISE_SD),
        calibration_correlation=0.20,
    )
    shared_flat_without_lineage = replace(
        shared_flat_capture, calibration_correlation=0.0
    )

    return {
        "flat": {
            "status_counts": {
                status: sum(r["status"] == status for r in flat_results)
                for status in sorted({r["status"] for r in flat_results})
            },
            "first_diagnostic": flat_results[0],
        },
        "periodic": {
            "status_counts": {
                status: sum(r["status"] == status for r in periodic_results)
                for status in sorted({r["status"] for r in periodic_results})
            },
            "first_diagnostic": periodic_results[0],
        },
        "clipping": score_arm(clipped_capture),
        "quantization": score_arm(quantized_capture),
        "shared_reference": score_arm(shared_reference_capture),
        "shared_flat": score_arm(shared_flat_capture),
        "shared_flat_without_lineage": score_arm(shared_flat_without_lineage),
        "clipping_fraction": {"value": clipped_capture.clip_fraction},
        "unused_components_shape": {"signal": list(components["signal"].shape)},
    }


def sample_size_battery() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for n in SAMPLE_SIZE_LADDER:
        rng = np.random.default_rng(MASTER_SEED + n)
        captures, _ = make_capture(rng, n=n)
        base = score_arm(captures)
        usm_gain = 1.0 + 0.75 * (
            1.0 - np.exp(-2.0 * np.pi**2 * FREQUENCIES**2)
        )
        usm = score_arm(postfilter(captures, usm_gain))
        result[str(n)] = {
            "base_status": base["status"],
            "usm_status": usm["status"],
            "ratio": ratio(usm, base),
            "absolute_error": abs(ratio(usm, base) - 1.0),
        }
    return result


def checker_mutation_controls() -> dict[str, bool]:
    def checker(usm_ratio: float, blur_ratio: float, improvement_ratio: float) -> bool:
        return usm_ratio <= 1.01 and blur_ratio < 0.90 and improvement_ratio > 1.10

    nominal = checker(1.0, 0.70, 1.30)
    forced_usm_promotion = checker(1.02, 0.70, 1.30)
    reversed_blur = checker(1.0, 1.05, 1.30)
    suppressed_improvement = checker(1.0, 0.70, 1.00)
    return {
        "nominal_passes": nominal,
        "forced_usm_promotion_fails": not forced_usm_promotion,
        "reversed_blur_fails": not reversed_blur,
        "suppressed_improvement_fails": not suppressed_improvement,
    }


def main() -> None:
    trials = [run_trial(MASTER_SEED + i) for i in range(TRIALS)]
    ratio_fields = {
        "identity": [],
        "fresh_null": [],
        "blur": [],
        "improvement": [],
        "usm": [],
        "post_blur": [],
        "gamma": [],
        "logistic": [],
        "noise": [],
        "common": [],
        "hallucination": [],
        "averaging": [],
        "angle": [],
    }
    transfer_fields = {"post_blur": [], "averaging": []}
    common_residual_increase = []
    statuses = {"permutation": []}
    tone_potency = {"gamma": [], "logistic": []}

    for trial in trials:
        base = trial["base"]
        for name in ratio_fields:
            ratio_fields[name].append(ratio(trial[name], base))
        for name in transfer_fields:
            transfer_fields[name].append(ratio(trial[name], base, "transfer"))
        common_residual_increase.append(
            trial["common"]["unexplained_fraction"] - base["unexplained_fraction"]
        )
        statuses["permutation"].append(trial["permutation"]["status"])
        tone_potency["gamma"].append(trial["tone_potency"]["gamma"])
        tone_potency["logistic"].append(trial["tone_potency"]["logistic"])

    summaries = {name: log_mean_ci(values) for name, values in ratio_fields.items()}
    transfer_summaries = {
        name: log_mean_ci(values) for name, values in transfer_fields.items()
    }
    residual_summary = {
        "q05": float(np.quantile(common_residual_increase, 0.05)),
        "median": float(np.median(common_residual_increase)),
        "q95": float(np.quantile(common_residual_increase, 0.95)),
    }
    tone_summary = {
        name: {
            "minimum": float(np.min(values)),
            "median": float(np.median(values)),
            "maximum": float(np.max(values)),
        }
        for name, values in tone_potency.items()
    }

    refusals = refusal_trials()
    sizes = sample_size_battery()
    mutations = checker_mutation_controls()

    gates = {
        "C0_identity": summaries["identity"]["maximum"] - 1.0 <= 1e-12
        and 1.0 - summaries["identity"]["minimum"] <= 1e-12,
        "C1_fresh_null": summaries["fresh_null"]["ci95_low"] <= 1.0
        <= summaries["fresh_null"]["ci95_high"]
        and summaries["fresh_null"]["ci95_low"] >= 0.95
        and summaries["fresh_null"]["ci95_high"] <= 1.05,
        "C2_blur": summaries["blur"]["q95"] < 0.90,
        "C3_improvement": summaries["improvement"]["q05"] > 1.10,
        "C4_usm": summaries["usm"]["maximum"] <= 1.01
        and max(
            abs(summaries["usm"]["minimum"] - 1.0),
            abs(summaries["usm"]["maximum"] - 1.0),
        )
        <= 1e-10,
        "C5_usm_sizes": all(
            item["ratio"] <= 1.01 and item["absolute_error"] <= 1e-10
            for item in sizes.values()
        ),
        "C6_post_blur": max(
            abs(summaries["post_blur"]["minimum"] - 1.0),
            abs(summaries["post_blur"]["maximum"] - 1.0),
        )
        <= 1e-10
        and transfer_summaries["post_blur"]["q95"] < 0.95,
        "C7_gamma": summaries["gamma"]["minimum"] >= 0.99
        and summaries["gamma"]["maximum"] <= 1.01,
        "C8_logistic": summaries["logistic"]["minimum"] >= 0.99
        and summaries["logistic"]["maximum"] <= 1.01,
        "C9_noise": summaries["noise"]["q95"] < 0.90,
        "C10_common": summaries["common"]["q95"] < 0.90
        and residual_summary["q05"] > 0.05,
        "C11_hallucination": summaries["hallucination"]["q95"] < 0.95,
        "C12_averaging": transfer_summaries["averaging"]["q95"] < 0.98,
        "C13_angle": max(
            abs(summaries["angle"]["minimum"] - 1.0),
            abs(summaries["angle"]["maximum"] - 1.0),
        )
        <= 1e-10,
        "C14_flat": refusals["flat"]["status_counts"] == {"NO_DETAIL": TRIALS},
        "C15_periodic": refusals["periodic"]["status_counts"]
        == {"PREDICTABLE_TARGET": TRIALS},
        "C16_permutation": all(s != "OK" for s in statuses["permutation"]),
        "C17_clipping": refusals["clipping"]["status"] == "NONLINEAR_OUTPUT",
        "C18_quantization": refusals["quantization"]["status"] == "LOW_BIT_DEPTH",
        "C19_shared_reference": refusals["shared_reference"]["status"]
        == "SHARED_REFERENCE"
        and refusals["shared_flat"]["status"] == "SHARED_REFERENCE",
        "C20_checker_mutations": all(mutations.values()),
    }

    averaging_promotions = sum(
        1
        for trial in trials
        if ratio(trial["averaging"], trial["base"]) > 1.02
        and ratio(trial["averaging"], trial["base"], "transfer") >= 0.99
    )
    gates["C12_averaging"] = gates["C12_averaging"] and averaging_promotions == 0

    output = {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "master_seed": MASTER_SEED,
        "trials": TRIALS,
        "sites": SITE_COUNT,
        "frequencies_cyc_per_native_px": FREQUENCIES.tolist(),
        "angles_deg": ANGLES_DEG.tolist(),
        "information_ratio_summaries": summaries,
        "transfer_ratio_summaries": transfer_summaries,
        "common_residual_increase": residual_summary,
        "tone_potency_relative_rms": tone_summary,
        "permutation_status_counts": {
            status: statuses["permutation"].count(status)
            for status in sorted(set(statuses["permutation"]))
        },
        "refusals": refusals,
        "sample_size_battery": sizes,
        "checker_mutation_controls": mutations,
        "averaging_promotions": averaging_promotions,
        "gates": gates,
    }
    output_path = Path(__file__).resolve().parent / "commission.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": output["status"], "gates": gates}, indent=2))


if __name__ == "__main__":
    main()
