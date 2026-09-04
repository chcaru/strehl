"""Independent-code-path verification of M135's mandatory flat certificate."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from instrument import CaptureSet, evaluate


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FREQUENCIES = np.repeat(np.array([0.10, 0.15, 0.20, 0.25]), 4)


def complex_normal(
    rng: np.random.Generator, shape: tuple[int, ...], sd: float
) -> np.ndarray:
    return sd * (
        rng.standard_normal(shape) + 1j * rng.standard_normal(shape)
    ) / np.sqrt(2.0)


def capture(
    rng: np.random.Generator,
    signal: np.ndarray,
    output_noise_sd: float = 0.20,
) -> tuple[CaptureSet, tuple[np.ndarray, np.ndarray]]:
    shape = signal.shape
    ra = complex_normal(rng, shape, 0.05)
    rb = complex_normal(rng, shape, 0.05)
    ya = complex_normal(rng, shape, output_noise_sd)
    yb = complex_normal(rng, shape, output_noise_sd)
    transfer = np.exp(-2.0 * np.pi**2 * 0.55**2 * FREQUENCIES**2)
    return (
        CaptureSet(
            reference_a=signal + ra,
            reference_b=signal + rb,
            output_a=signal * transfer[np.newaxis, :] + ya,
            output_b=signal * transfer[np.newaxis, :] + yb,
            clip_fraction=0.0,
            effective_bits=16,
            calibration_correlation=0.0,
            target_lineage="nonperiodic-random",
        ),
        (ya, yb),
    )


def main() -> None:
    current = json.loads((HERE / "commission.json").read_text(encoding="utf-8"))
    prior = json.loads(
        (HERE / "commission-run4-pre-flat-null.json").read_text(encoding="utf-8")
    )
    pre_shape_guard = json.loads(
        (HERE / "commission-run5-pre-shape-guard.json").read_text(encoding="utf-8")
    )
    m137 = json.loads(
        (ROOT / "experiments" / "M134-kernel-frontier" / "detail-results.json")
        .read_text(encoding="utf-8")
    )

    checks: dict[str, bool] = {}
    checks["commission_passes_25_gates"] = bool(
        current["status"] == "PASS"
        and len(current["gates"]) == 25
        and all(current["gates"].values())
    )

    preserved_sections = (
        "transfer_ratio_summaries",
        "common_residual_increase",
        "tone_potency_relative_rms",
        "permutation_status_counts",
        "sample_size_battery",
        "checker_mutation_controls",
        "averaging_promotions",
    )
    checks["pre_amendment_sections_exact"] = all(
        current[key] == prior[key] for key in preserved_sections
    )
    checks["pre_amendment_information_exact"] = all(
        current["information_ratio_summaries"][key] == value
        for key, value in prior["information_ratio_summaries"].items()
    )
    checks["pre_amendment_gates_exact"] = all(
        current["gates"][key] == value for key, value in prior["gates"].items()
    )
    checks["shape_guard_campaign_exact"] = current == pre_shape_guard

    flat = current["flat_control_ratio_summaries"]
    checks["all_flat_information_ratios_below_bar"] = all(
        arm["information"]["maximum"] <= 0.10 for arm in flat.values()
    )
    checks["all_flat_reference_ratios_below_bar"] = all(
        arm["reference_repeatable_power"]["maximum"] <= 0.25
        for arm in flat.values()
    )
    checks["all_flat_output_ratios_below_bar"] = all(
        arm["output_repeatable_power"]["maximum"] <= 0.10
        for arm in flat.values()
    )
    checks["common_flat_rejected_128"] = current["common_flat_status_counts"] == {
        "FLAT_NULL_FAILED": 128
    }
    structured = current["refusals"]["structured_flat"]
    checks["structured_flat_rejected"] = bool(
        structured["status"] == "FLAT_NULL_FAILED"
        and "information_bits_per_site" not in structured
        and structured["flat_control"]["flat_to_detail_information_ratio"] == 1.0
        and structured["flat_control"][
            "flat_to_detail_reference_repeatable_power_ratio"
        ]
        == 1.0
        and structured["flat_control"][
            "flat_to_detail_output_repeatable_power_ratio"
        ]
        == 1.0
    )
    checks["missing_flat_rejected_128"] = current["refusals"]["missing_flat"][
        "status_counts"
    ] == {"MISSING_FLAT_CONTROL": 128}

    potency = current["noise_amplification_potency"]
    checks["noise_plant_potency_exact"] = bool(
        np.allclose(
            potency["squared_gain"],
            [1.5376, 2.3716, 3.8416, 6.25],
            rtol=0.0,
            atol=1e-12,
        )
        and abs(potency["upper_two_band_mean_squared_gain"] - 5.0458) <= 1e-12
        and potency["upper_to_lower_mean_squared_gain_ratio"] > 2.58
    )
    checks["noise_plant_not_rewarded"] = bool(
        current["information_ratio_summaries"]["noise_amplified"]["q95"] < 0.90
        and current["noise_amplification_promotions"] == 0
    )

    m137_comparison = m137["flat_null"]["comparison"]
    checks["m137_failure_matches_source"] = bool(
        m137_comparison["detailed_catmull_minus_bilinear_dex"]
        == 0.3403664343410666
        and m137_comparison["flat_catmull_minus_bilinear_dex"]
        == 0.3488548829813006
        and m137_comparison["flat_to_detailed_gap_ratio"]
        == 1.0249391472947889
        and not m137_comparison["pass"]
        and not m137["controls"]["S7_flat_band_null"]
        and m137["existing_all_pass"]
        and not m137["all_pass"]
    )

    rng = np.random.default_rng(9135)
    signal = complex_normal(rng, (128, len(FREQUENCIES)), 1.0)
    detail, output_noise = capture(rng, signal)
    flat_signal = np.zeros_like(signal)
    flat_capture, flat_output_noise = capture(rng, flat_signal)

    baseline = evaluate(detail, flat_capture)
    missing = evaluate(detail)
    structured_flat = evaluate(detail, detail)
    common_pattern = complex_normal(rng, signal.shape, 3.0)
    contaminated_flat = replace(
        flat_capture,
        output_a=flat_capture.output_a + common_pattern,
        output_b=flat_capture.output_b + common_pattern,
    )
    common_flat = evaluate(detail, contaminated_flat)
    invalid_shape = evaluate(
        replace(detail, output_b=detail.output_b[:, :-1]),
        flat_capture,
    )

    gain = 1.0 + 1.5 * (FREQUENCIES / 0.25) ** 2
    amplified_detail = replace(
        detail,
        output_a=detail.output_a + output_noise[0] * (gain[np.newaxis, :] - 1.0),
        output_b=detail.output_b + output_noise[1] * (gain[np.newaxis, :] - 1.0),
    )
    amplified_flat = replace(
        flat_capture,
        output_a=flat_capture.output_a
        + flat_output_noise[0] * (gain[np.newaxis, :] - 1.0),
        output_b=flat_capture.output_b
        + flat_output_noise[1] * (gain[np.newaxis, :] - 1.0),
    )
    amplified = evaluate(amplified_detail, amplified_flat)

    checks["direct_baseline_passes"] = baseline["status"] == "OK"
    checks["direct_missing_flat_fails"] = missing["status"] == "MISSING_FLAT_CONTROL"
    checks["direct_structured_flat_fails"] = (
        structured_flat["status"] == "FLAT_NULL_FAILED"
    )
    checks["direct_common_flat_fails"] = common_flat["status"] == "FLAT_NULL_FAILED"
    checks["direct_invalid_shape_refuses"] = invalid_shape["status"] == "INVALID_SHAPE"
    checks["direct_noise_amplification_not_rewarded"] = bool(
        amplified["status"] == "OK"
        and amplified["flat_control"]["passes"]
        and amplified["information_bits_per_site"]
        < baseline["information_bits_per_site"]
    )

    output = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "direct_probe": {
            "baseline_information_bits_per_site": baseline.get(
                "information_bits_per_site"
            ),
            "noise_amplified_information_bits_per_site": amplified.get(
                "information_bits_per_site"
            ),
            "noise_amplified_to_baseline_ratio": (
                amplified.get("information_bits_per_site")
                / baseline["information_bits_per_site"]
            ),
            "baseline_flat_control": baseline["flat_control"],
            "noise_amplified_flat_control": amplified["flat_control"],
            "structured_flat_status": structured_flat["status"],
            "common_flat_status": common_flat["status"],
            "invalid_shape_status": invalid_shape["status"],
            "missing_flat_status": missing["status"],
        },
    }
    (HERE / "flat-verification.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": output["status"], "checks": checks}, indent=2))
    if output["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
