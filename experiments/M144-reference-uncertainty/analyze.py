from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import skimage
import xlrd
from skimage.color import deltaE_ciede2000


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

SEED = 20260904
MONTE_CARLO_DRAWS = 100_000

SOURCE_PATHS = [
    ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md",
    ROOT / "docs" / "proposals" / "2026-09-truth-referenced-detail.md",
    ROOT / "docs" / "OWNER-ACTIONS.md",
    ROOT / "docs" / "research" / "M132-blocker-d-routes.md",
    ROOT / "docs" / "research" / "M133-blocker-audit.md",
    ROOT / "docs" / "research" / "M135-detail-instrument.md",
    ROOT / "docs" / "research" / "M-PHASE0-SPLIT2.md",
    ROOT / "docs" / "research" / "M71-flat-fields.md",
    ROOT / "docs" / "research" / "M84b-ruler-metrology.md",
    ROOT / "docs" / "research" / "F-camera-lens-optics.md",
    ROOT / "docs" / "research" / "M8-overshoot.md",
    ROOT
    / "experiments"
    / "M132-blocker-d-routes"
    / "m7-isa-target-colorimetry.xls",
    ROOT / "experiments" / "M71-flat-fields" / "data" / "03-ptc.json",
    ROOT / "experiments" / "M71-flat-fields" / "data" / "05-kappa.json",
    ROOT / "experiments" / "M71-flat-fields" / "data" / "07-structure.json",
    ROOT
    / "experiments"
    / "M84b-ruler-metrology"
    / "out"
    / "depth-truth-params.json",
    ROOT
    / "experiments"
    / "M-PHASE0-SPLIT2"
    / "out"
    / "alignment-gate.json",
    ROOT / "experiments" / "M8-overshoot" / "results.json",
]

WORKBOOK = (
    ROOT
    / "experiments"
    / "M132-blocker-d-routes"
    / "m7-isa-target-colorimetry.xls"
)

# Locally measured/reference-body quantities cited in the report.
GREEN_GAIN_DN_PER_ELECTRON = 0.224001
READ_NOISE_DN_ISO100 = 1.079
SIGNAL_RANGE_DN = (260.4, 10_515.5)
ACTIVE_RANGE_DN = 15_871.0
PRNU_RMS_FRACTION = 0.003096
PRNU_SPREAD_FRACTION = 0.000159
PRNU_STABLE_VARIANCE_FRACTION = 0.9136

REGISTRATION_RMS_PX = (0.064031, 0.070005, 0.105202, 0.107703)
LICENSED_FREQUENCY_CYC_PER_PX = 0.25
SCORECARD_SCALE_FRACTION = 0.001
SITE_WIDTH_PX = 128

M10_MEDIAN_TRUTH_UM = 8.28
M10_P90_TRUTH_UM = 16.43
FOCUS_STEP_UM = 42.20
DEPTH_SCALE_UM = 975.73
DEPTH_SCALE_95_INTERVAL_UM = (975.49, 976.16)

M7_TOTAL_U95_BUDGET_DE00 = 0.25
M7_CERTIFICATE_U95_SCREEN_DE00 = 0.20


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def scorecard_success_quotes() -> dict[str, object]:
    path = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = []
    for index, line in enumerate(lines):
        if line.startswith("### M") and " — " in line:
            axis = line.split(" — ", 1)[0].removeprefix("### ")
            starts.append((axis, index))

    output = {}
    for position, (axis, start) in enumerate(starts):
        end = starts[position + 1][1] if position + 1 < len(starts) else len(lines)
        success = next(
            index
            for index in range(start, end)
            if lines[index].startswith("**Success.**")
        )
        paragraph = []
        index = success
        while index < end and lines[index].strip():
            paragraph.append(lines[index])
            index += 1
        output[axis] = {
            "line_start": success + 1,
            "line_end": index,
            "verbatim": "\n".join(paragraph),
        }
    return output


def wilson(k: int, n: int, side: str, z: float = 1.6448536269514722) -> float:
    p = k / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    radius = (
        z
        * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
        / denominator
    )
    if side == "upper":
        return center + radius
    if side == "lower":
        return center - radius
    raise ValueError(side)


def max_failures_for_upper(n: int, limit: float) -> int:
    return max(k for k in range(n + 1) if wilson(k, n, "upper") <= limit)


def max_failures_for_lower_success(
    n: int, point_minimum: float, lower_limit: float
) -> int:
    allowed = []
    for failures in range(n + 1):
        successes = n - failures
        if successes / n >= point_minimum and wilson(successes, n, "lower") >= lower_limit:
            allowed.append(failures)
    return max(allowed)


def lstar_to_y(lstar: float) -> float:
    if lstar > 8.0:
        return ((lstar + 16.0) / 116.0) ** 3
    return lstar / 903.3


def y_to_lstar(y: float) -> float:
    y = max(y, 0.0)
    epsilon = (6.0 / 29.0) ** 3
    if y > epsilon:
        return 116.0 * y ** (1.0 / 3.0) - 16.0
    return 903.3 * y


def load_matte_rows() -> list[dict[str, object]]:
    workbook = xlrd.open_workbook(WORKBOOK)
    sheet = workbook.sheet_by_name("Micro, Nano ,Pico")
    rows = []
    # Excel rows 62-91 are the 30 matte-patch records.
    for row_index in range(61, 91):
        rows.append(
            {
                "patch": int(sheet.cell_value(row_index, 1)),
                "lab": [
                    float(sheet.cell_value(row_index, column))
                    for column in (2, 3, 4)
                ],
                "component_sd": [
                    float(sheet.cell_value(row_index, column))
                    for column in (5, 6, 7)
                ],
            }
        )
    return rows


def nominal_batch_variation(rows: list[dict[str, object]]) -> dict[str, object]:
    rng = np.random.default_rng(SEED)
    results = []
    for row in rows:
        mean = np.asarray(row["lab"], dtype=np.float64)
        component_sd = np.asarray(row["component_sd"], dtype=np.float64)
        samples = mean + rng.normal(size=(MONTE_CARLO_DRAWS, 3)) * component_sd
        differences = deltaE_ciede2000(
            samples, np.broadcast_to(mean, samples.shape)
        )
        results.append(
            {
                "patch": row["patch"],
                "lab": row["lab"],
                "component_sd": row["component_sd"],
                "delta_e00_p50": float(np.quantile(differences, 0.50)),
                "delta_e00_p95": float(np.quantile(differences, 0.95)),
                "delta_e00_p99": float(np.quantile(differences, 0.99)),
            }
        )
    results.sort(key=lambda item: item["delta_e00_p95"], reverse=True)
    p95_values = np.asarray([item["delta_e00_p95"] for item in results])
    return {
        "model": (
            "Independent Gaussian L*, a*, b* target-to-target variation using "
            "the vendor workbook's n=50 component standard deviations. This "
            "is a screening model, not a certificate uncertainty."
        ),
        "seed": SEED,
        "draws_per_patch": MONTE_CARLO_DRAWS,
        "worst_patch": results[0],
        "median_patch_p95_delta_e00": float(np.median(p95_values)),
        "patches_with_p95_over_1_delta_e00": int(np.sum(p95_values > 1.0)),
        "patches_with_p95_over_2_delta_e00": int(np.sum(p95_values > 2.0)),
        "all_patches": results,
    }


def reference_noise() -> dict[str, object]:
    rows = []
    for signal in SIGNAL_RANGE_DN:
        sigma_one = math.sqrt(
            GREEN_GAIN_DN_PER_ELECTRON * signal + READ_NOISE_DN_ISO100**2
        )
        rows.append(
            {
                "signal_dn": signal,
                "single_frame_sigma_dn": sigma_one,
                "mean_16_sigma_dn": sigma_one / math.sqrt(16.0),
                "mean_32_sigma_dn": sigma_one / math.sqrt(32.0),
                "single_frame_sigma_percent_active_range": (
                    100.0 * sigma_one / ACTIVE_RANGE_DN
                ),
                "mean_16_sigma_percent_active_range": (
                    100.0 * sigma_one / math.sqrt(16.0) / ACTIVE_RANGE_DN
                ),
                "mean_32_sigma_percent_active_range": (
                    100.0 * sigma_one / math.sqrt(32.0) / ACTIVE_RANGE_DN
                ),
            }
        )
    return {
        "model": "sigma^2 = g*S + RN_DN^2; independent frame means scale as 1/sqrt(N)",
        "gain_dn_per_electron": GREEN_GAIN_DN_PER_ELECTRON,
        "read_noise_dn": READ_NOISE_DN_ISO100,
        "rows": rows,
    }


def registration_sensitivity() -> dict[str, object]:
    rows = []
    for residual in REGISTRATION_RMS_PX:
        phase = 2.0 * math.pi * LICENSED_FREQUENCY_CYC_PER_PX * residual
        rows.append(
            {
                "registration_rms_px": residual,
                "phase_rms_rad_at_0_25_cyc_per_px": phase,
                "gaussian_jitter_amplitude_loss_fraction": 1.0
                - math.exp(-0.5 * phase * phase),
            }
        )
    phase_span = (
        math.pi
        * LICENSED_FREQUENCY_CYC_PER_PX
        * SCORECARD_SCALE_FRACTION
        * SITE_WIDTH_PX
    )
    sinc = math.sin(phase_span) / phase_span
    return {
        "model": (
            "Registration phase is 2*pi*f*sigma. Amplitude loss assumes "
            "zero-mean Gaussian residual jitter. Scale attenuation integrates "
            "a linear 0.10% coordinate error over a centered 128-px site."
        ),
        "rows": rows,
        "scale_gate": {
            "scale_fraction": SCORECARD_SCALE_FRACTION,
            "site_width_px": SITE_WIDTH_PX,
            "maximum_edge_displacement_px": (
                SCORECARD_SCALE_FRACTION * SITE_WIDTH_PX / 2.0
            ),
            "phase_span_rad_at_0_25_cyc_per_px": phase_span,
            "sinc_amplitude_loss_fraction": 1.0 - sinc,
        },
    }


def m3_plateau_noise() -> dict[str, object]:
    rows = []
    for samples in (17, 81):
        # Asymptotic standard error of a normal-sample median is
        # sqrt(pi/2)*sigma/sqrt(n). Two independent plateaus contribute.
        relative_u95 = (
            1.96
            * math.sqrt(math.pi / 2.0)
            * math.sqrt(2.0 / samples)
            / 10.0
        )
        rows.append(
            {
                "samples_per_plateau": samples,
                "u95_fraction_of_unit_step_at_10sigma_eligibility_floor": (
                    relative_u95
                ),
            }
        )
    return {
        "model": (
            "Normal-noise approximation for two median plateaus, evaluated at "
            "the scorecard's minimum eligible 10-sigma source step."
        ),
        "rows": rows,
    }


def tone_and_quantisation(rows: list[dict[str, object]]) -> dict[str, object]:
    neutral_ids = {8, 9, 10, 11, 14, 15, 16, 17, 20, 21, 22, 23}
    neutral_rows = [row for row in rows if row["patch"] in neutral_ids]
    outputs = []
    for row in neutral_rows:
        patch = int(row["patch"])
        lstar = float(row["lab"][0])
        y = lstar_to_y(lstar)
        variants = {
            "slope_only_plus": 1.005 * y,
            "offset_only_plus": y + 0.001,
            "residual_only_plus": y + 0.002,
            "combined_plus": 1.005 * y + 0.001 + 0.002,
            "combined_minus": 0.995 * y - 0.001 - 0.002,
            "half_16bit_lsb_plus": y + 0.5 / 65535.0,
        }
        outputs.append(
            {
                "patch": patch,
                "lstar": lstar,
                "relative_y": y,
                "absolute_delta_lstar": {
                    name: abs(y_to_lstar(value) - lstar)
                    for name, value in variants.items()
                },
            }
        )

    def maximum(name: str) -> dict[str, object]:
        row = max(
            outputs, key=lambda item: item["absolute_delta_lstar"][name]
        )
        return {
            "patch": row["patch"],
            "delta_lstar": row["absolute_delta_lstar"][name],
        }

    return {
        "model": (
            "Neutral-axis CIELAB sensitivity only. The combined tone case "
            "places slope, offset, and maximum affine residual in the same "
            "direction; it is an admitted worst case, not an expected error."
        ),
        "maxima": {
            name: maximum(name)
            for name in (
                "slope_only_plus",
                "offset_only_plus",
                "residual_only_plus",
                "combined_plus",
                "combined_minus",
                "half_16bit_lsb_plus",
            )
        },
        "neutral_patches": outputs,
    }


def m7_patch_random_terms(rows: list[dict[str, object]]) -> dict[str, object]:
    # M132 derives about 484 px across after treating 20% erosion as removal
    # from each side. Divide area by 16 as a deliberately conservative
    # correlation-area assumption.
    eroded_patch_width_px = 484
    effective_independent_pixels = eroded_patch_width_px**2 / 16.0
    darkest = min(
        (row for row in rows if row["patch"] in {8, 9, 10, 11, 14, 15, 16, 17, 20, 21, 22, 23}),
        key=lambda row: row["lab"][0],
    )
    lstar = float(darkest["lab"][0])
    y = lstar_to_y(lstar)
    signal_dn = y * ACTIVE_RANGE_DN
    sigma_dn = math.sqrt(
        GREEN_GAIN_DN_PER_ELECTRON * signal_dn + READ_NOISE_DN_ISO100**2
    )
    median_se_dn = math.sqrt(math.pi / 2.0) * sigma_dn / math.sqrt(
        effective_independent_pixels
    )
    noise_u95_dn = 1.96 * median_se_dn
    noise_u95_lstar = abs(
        y_to_lstar(y + noise_u95_dn / ACTIVE_RANGE_DN) - lstar
    )

    prnu_sigma_dn = PRNU_RMS_FRACTION * signal_dn
    prnu_median_se_dn = math.sqrt(math.pi / 2.0) * prnu_sigma_dn / math.sqrt(
        effective_independent_pixels
    )
    prnu_u95_dn = 1.96 * prnu_median_se_dn
    prnu_u95_lstar = abs(
        y_to_lstar(y + prnu_u95_dn / ACTIVE_RANGE_DN) - lstar
    )
    return {
        "model": (
            "Darkest matte neutral patch, one-frame ISO-100 noise, 484x484 "
            "eroded pixels, and a conservative 16-pixel correlation area. "
            "PRNU calculation treats the measured near-white PRNU spectrum as "
            "spatially averaging; low-frequency flat/illumination residue is "
            "not covered."
        ),
        "patch": darkest["patch"],
        "lstar": lstar,
        "signal_dn": signal_dn,
        "effective_independent_pixels": effective_independent_pixels,
        "noise_u95_dn": noise_u95_dn,
        "noise_u95_delta_lstar": noise_u95_lstar,
        "prnu_u95_dn_if_white": prnu_u95_dn,
        "prnu_u95_delta_lstar_if_white": prnu_u95_lstar,
    }


def m10_reference() -> dict[str, object]:
    lower, upper = DEPTH_SCALE_95_INTERVAL_UM
    return {
        "existing_other-ruler_example_only": True,
        "median_truth_uncertainty_focus_steps": (
            M10_MEDIAN_TRUTH_UM / FOCUS_STEP_UM
        ),
        "p90_truth_uncertainty_focus_steps": M10_P90_TRUTH_UM / FOCUS_STEP_UM,
        "depth_scale_largest_95_relative_half_width": max(
            abs(lower - DEPTH_SCALE_UM), abs(upper - DEPTH_SCALE_UM)
        )
        / DEPTH_SCALE_UM,
    }


def m8_numeric_budget() -> dict[str, object]:
    tau_at_one = 8.0 * float(np.spacing(np.float32(1.0)))
    half_lsb = 0.5 / 65535.0
    total = tau_at_one + half_lsb
    positive_excess = 0.003703290
    absolute_excess = 1.049185276
    return {
        "tau_r_at_unit_scale": tau_at_one,
        "half_16bit_lsb": half_lsb,
        "combined_unit_scale_tolerance": total,
        "largest_positive_m8o_excess": positive_excess,
        "largest_absolute_m8o_excess": absolute_excess,
        "positive_excess_multiple_of_tolerance": positive_excess / total,
        "absolute_excess_multiple_of_tolerance": absolute_excess / total,
    }


def main() -> None:
    # Standard Sharma et al. CIEDE2000 test pair, used only to catch a broken
    # implementation/library path.
    check = float(
        deltaE_ciede2000(
            np.asarray([[50.0, 2.6772, -79.7751]]),
            np.asarray([[50.0, 0.0, -82.7485]]),
        )[0]
    )
    if not math.isclose(check, 2.0425, rel_tol=0.0, abs_tol=5e-5):
        raise RuntimeError(f"CIEDE2000 self-check failed: {check}")

    matte_rows = load_matte_rows()
    remaining = math.sqrt(
        M7_TOTAL_U95_BUDGET_DE00**2
        - M7_CERTIFICATE_U95_SCREEN_DE00**2
    )
    output = {
        "protocol": "M144 reference uncertainty budget v1",
        "seed": SEED,
        "software": {
            "numpy": np.__version__,
            "scikit_image": skimage.__version__,
            "xlrd": xlrd.__version__,
        },
        "ciede2000_self_check": {
            "expected": 2.0425,
            "observed": check,
            "absolute_tolerance": 5e-5,
            "pass": True,
        },
        "source_sha256": {
            str(path.relative_to(ROOT)).replace("\\", "/"): sha256(path)
            for path in SOURCE_PATHS
        },
        "scorecard_success_quotes": scorecard_success_quotes(),
        "m7_nominal_batch_variation": nominal_batch_variation(matte_rows),
        "reference_noise": reference_noise(),
        "registration_sensitivity": registration_sensitivity(),
        "m3_plateau_noise": m3_plateau_noise(),
        "tone_and_quantisation": tone_and_quantisation(matte_rows),
        "m7_patch_random_terms": m7_patch_random_terms(matte_rows),
        "m10_reference": m10_reference(),
        "m8_numeric_budget": m8_numeric_budget(),
        "wilson_count_sensitivity_at_n_500": {
            "m3_m4_max_failures_for_one_sided_ucb95_le_0_02": (
                max_failures_for_upper(500, 0.02)
            ),
            "m9_max_false_certifications_for_one_sided_ucb95_le_0_01": (
                max_failures_for_upper(500, 0.01)
            ),
            "m5_max_failures_for_point_ge_0_99_and_lcb95_ge_0_98": (
                max_failures_for_lower_success(500, 0.99, 0.98)
            ),
        },
        "m7_assumed_procurement_budget": {
            "total_u95_delta_e00": M7_TOTAL_U95_BUDGET_DE00,
            "certificate_screen_u95_delta_e00": (
                M7_CERTIFICATE_U95_SCREEN_DE00
            ),
            "remaining_root_sum_square_u95_delta_e00": remaining,
            "status": (
                "Policy allocation for this report, not scorecard language, "
                "vendor specification, or measured capability."
            ),
        },
    }
    output_path = HERE / "results.json"
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(output_path)


if __name__ == "__main__":
    main()
