"""Synthetic commissioning v3 for the frozen M161 M3 checker.

This M169-owned copy removes only M161's obsolete host-reservation gate.
M174's adjudication corrects the 0.5%-each arm's expected result and v3 adds
a separately registered sub-boundary green recovery arm. No numerical checker
gate changes. This opens no capture, candidate, or comparator pixels and
records no timing.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import ndimage

from m3_checker_v2 import (
    SiteProfiles,
    load_checker_definition,
    score_site,
    sha256_file,
    summarize,
    validate_geometry,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "out" / "commission-v3.json"
REGISTRATION = HERE / "commissioning-registration-v3.json"
MASTER_SEED = 161_202_609_06
SITE_COUNT = 500
SOURCE_COUNT = 8
NOISE_SIGMA_FRACTION = 0.002
NOISE_STRESS_SIGMA_FRACTION = 0.012
ALLOWED_WARP_RESIDUAL_NATIVE_PX = 0.08


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False
    )
    path.write_text(encoded + "\n", encoding="ascii")


def load_registration(
    definition: dict[str, Any], definition_sha: str
) -> dict[str, Any]:
    registration = json.loads(REGISTRATION.read_text(encoding="utf-8"))
    if registration.get("schema") != "m169-m3-commissioning-registration-v3":
        raise RuntimeError("unexpected M169 commissioning registration")
    authority = registration["authority"]
    if (
        authority["commit"]
        != "a9176fef45ce5bc8306ef690eafc7f51bc2d5ddd"
        or authority["verdict"] != "B_ASSERTION_DEFECT"
    ):
        raise RuntimeError("M174 adjudication authority changed")

    frozen = registration["frozen_instrument"]
    expected_frozen = {
        "checker_definition_sha256": definition_sha,
        "checker_source_sha256": sha256_file(HERE / "m3_checker_v2.py"),
        "master_seed": MASTER_SEED,
        "site_count": SITE_COUNT,
        "noise_sigma_fraction_of_step": NOISE_SIGMA_FRACTION,
    }
    if frozen != expected_frozen:
        raise RuntimeError("registration does not match the frozen instrument")
    if registration["unchanged_gates"] != definition["bars"]:
        raise RuntimeError("registration changed one or more M3 gates")

    boundary = registration["boundary_reduction_arm"]
    if (
        boundary["expected_gate_result"] != "FAIL_MEDIAN_H_E"
        or boundary["expected_result_assertion"]
        != "improved_arm_fails_median_h_e"
        or boundary["rim_component_fraction_of_step"] != 0.005
        or boundary["veil_component_fraction_of_step"] != 0.005
        or boundary["noiseless_overlap_fraction_of_step"]
        != definition["bars"]["median_h_e_max"]
        or boundary["overlap_offsets_native_px"] != list(range(16, 25))
        or boundary["retained_movement_assertions"]
        != [
            "improvement_reduces_h_by_at_least_5pp",
            "improvement_reduces_v_by_at_least_5pp",
        ]
    ):
        raise RuntimeError("boundary-reduction registration changed")

    green = registration["green_recovery_arm"]
    expected_green_component = definition["bars"]["median_h_e_max"] / 4.0
    if (
        green["expected_gate_result"] != "PASS_ALL_GATES"
        or green["rim_component_fraction_of_step"]
        != expected_green_component
        or green["veil_component_fraction_of_step"]
        != expected_green_component
        or green["noiseless_overlap_fraction_of_step"]
        != definition["bars"]["median_h_e_max"] / 2.0
        or green["selection_uses_observed_failure_or_crossing"] is not False
        or registration["score_authorized"] is not False
    ):
        raise RuntimeError("green-recovery registration changed")
    return registration


def logistic_profile(
    offsets: np.ndarray, dark: float, step: float, width: float
) -> np.ndarray:
    return dark + step / (1.0 + np.exp(-offsets / width))


def edge_patch(
    dark: float, step: float, width: float, angle: float, phase: float
) -> np.ndarray:
    yy, xx = np.indices((128, 128), dtype=np.float64)
    x = xx - 63.5
    y = yy - 63.5
    normal = x * math.cos(angle) + y * math.sin(angle)
    texture = 0.006 * step * (
        np.sin(2.0 * math.pi * xx / 5.0 + phase)
        + 0.7 * np.sin(2.0 * math.pi * yy / 6.0 + 0.3 - phase)
    )
    return logistic_profile(normal, dark, step, width) + texture


def rim_delta(
    offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    delta = np.zeros_like(offsets, dtype=np.float64)
    delta[(offsets >= -24.0) & (offsets <= -12.0)] -= amplitude * step
    delta[(offsets >= 12.0) & (offsets <= 24.0)] += amplitude * step
    return delta


def opposite_rim_delta(
    offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    return -rim_delta(offsets, step, amplitude)


def two_sided_veil_delta(
    offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    delta = np.zeros_like(offsets, dtype=np.float64)
    delta[(np.abs(offsets) >= 16.0) & (np.abs(offsets) <= 200.0)] += (
        amplitude * step
    )
    return delta


def one_sided_veil_delta(
    offsets: np.ndarray, step: float, amplitude: float
) -> np.ndarray:
    delta = np.zeros_like(offsets, dtype=np.float64)
    delta[(offsets >= 33.0) & (offsets <= 232.0)] += amplitude * step
    return delta


def patch_delta(
    patch: np.ndarray,
    step: float,
    *,
    rim: float = 0.0,
    veil: float = 0.0,
    opposite: bool = False,
) -> np.ndarray:
    yy, xx = np.indices(patch.shape, dtype=np.float64)
    normal = xx - 63.5
    output = patch.copy()
    if rim:
        sign = -1.0 if opposite else 1.0
        output[(normal >= -24.0) & (normal <= -12.0)] -= sign * rim * step
        output[(normal >= 12.0) & (normal <= 24.0)] += sign * rim * step
    if veil:
        output[(np.abs(normal) >= 16.0) & (np.abs(normal) <= 63.5)] += (
            veil * step
        )
    return output


ProfilePlant = Callable[[np.ndarray, np.ndarray, float], np.ndarray]
PatchPlant = Callable[[np.ndarray, float], np.ndarray]


def synthetic_population(
    profile_plant: ProfilePlant,
    patch_plant: PatchPlant,
    definition: dict[str, Any],
    *,
    noise_sigma_fraction: float = NOISE_SIGMA_FRACTION,
    warp_residual_native_px: float = 0.0,
    sparse_site: int | None = None,
) -> list[dict[str, Any]]:
    rng = np.random.default_rng(MASTER_SEED)
    offsets = np.arange(-400.0, 401.0, 1.0)
    captures = definition["site_population"]["required_capture_ids"]
    results: list[dict[str, Any]] = []
    for index in range(SITE_COUNT):
        step = float(rng.uniform(0.25, 0.75))
        dark = float(rng.uniform(0.05, 0.15))
        width = float(rng.uniform(1.6, 2.4))
        base = logistic_profile(offsets, dark, step, width)
        source_rows = []
        for _ in range(SOURCE_COUNT):
            residual_shift = float(
                rng.uniform(-warp_residual_native_px, warp_residual_native_px)
            )
            shifted = np.interp(
                offsets + residual_shift,
                offsets,
                base,
                left=float(base[0]),
                right=float(base[-1]),
            )
            source_rows.append(
                shifted
                + rng.normal(
                    0.0, noise_sigma_fraction * step, size=offsets.size
                )
            )
        sources = np.stack(source_rows)
        output = base + rng.normal(
            0.0, noise_sigma_fraction * step, size=offsets.size
        )
        if sparse_site is None or index == sparse_site:
            output = profile_plant(output, offsets, step)

        angle = float(rng.uniform(-0.2, 0.2))
        patch = edge_patch(dark, step, width, angle, phase=float(index))
        source_patch = patch + rng.normal(
            0.0, noise_sigma_fraction * step, size=patch.shape
        )
        output_patch = patch + rng.normal(
            0.0, noise_sigma_fraction * step, size=patch.shape
        )
        if sparse_site is None or index == sparse_site:
            output_patch = patch_plant(output_patch, step)

        site = SiteProfiles(
            site_id=f"SYN-{index + 1:04d}",
            capture_id=captures[index % len(captures)],
            offsets_native_px=offsets,
            source_profiles=sources,
            output_profile=output,
            normalization_source_index=1,
            far_reference_source_index=0,
            sharp_source_index=2,
            output_patch=output_patch,
            sharp_source_patch=source_patch,
        )
        results.append(score_site(site, definition))
    return results


def arm_summary(
    name: str,
    profile_plant: ProfilePlant,
    patch_plant: PatchPlant,
    definition: dict[str, Any],
    planted_amplitude: float,
    *,
    noise_sigma_fraction: float = NOISE_SIGMA_FRACTION,
    warp_residual_native_px: float = 0.0,
    sparse_site: int | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = synthetic_population(
        profile_plant,
        patch_plant,
        definition,
        noise_sigma_fraction=noise_sigma_fraction,
        warp_residual_native_px=warp_residual_native_px,
        sparse_site=sparse_site,
    )
    summary = summarize(rows, definition=definition)
    summary["name"] = name
    summary["planted_amplitude_fraction_of_step"] = planted_amplitude
    summary["noise_sigma_fraction_of_step"] = noise_sigma_fraction
    summary["warp_residual_bound_native_px"] = warp_residual_native_px
    summary["detection_rate"] = summary["affected_edge_rate"]
    summary["median_v_e_pooled_diagnostic"] = float(
        np.median([row["v_e_pooled_diagnostic"] for row in rows])
    )
    return summary, rows


def fit_similarity(
    reference_xy: np.ndarray, moving_xy: np.ndarray
) -> tuple[float, float, float, float]:
    reference = np.asarray(reference_xy, dtype=np.float64)
    moving = np.asarray(moving_xy, dtype=np.float64)
    if reference.shape != moving.shape or reference.ndim != 2 or reference.shape[1] != 2:
        raise ValueError("similarity fit needs matching Nx2 arrays")
    x = reference[:, 0]
    y = reference[:, 1]
    design = np.zeros((2 * len(reference), 4), dtype=np.float64)
    target = np.empty(2 * len(reference), dtype=np.float64)
    design[0::2, 0] = x
    design[0::2, 1] = -y
    design[0::2, 2] = 1.0
    design[1::2, 0] = y
    design[1::2, 1] = x
    design[1::2, 3] = 1.0
    target[0::2] = moving[:, 0]
    target[1::2] = moving[:, 1]
    a, b, tx, ty = np.linalg.lstsq(design, target, rcond=None)[0]
    return float(a), float(b), float(tx), float(ty)


def apply_similarity(
    points_xy: np.ndarray, transform: tuple[float, float, float, float]
) -> np.ndarray:
    a, b, tx, ty = transform
    points = np.asarray(points_xy, dtype=np.float64)
    x = points[:, 0]
    y = points[:, 1]
    return np.column_stack([a * x - b * y + tx, b * x + a * y + ty])


def invert_similarity(
    transform: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    a, b, tx, ty = transform
    denominator = a * a + b * b
    if denominator <= 0.0:
        raise ValueError("singular similarity")
    inverse_a = a / denominator
    inverse_b = -b / denominator
    inverse_tx = -(inverse_a * tx - inverse_b * ty)
    inverse_ty = -(inverse_b * tx + inverse_a * ty)
    return inverse_a, inverse_b, inverse_tx, inverse_ty


def geometry_metrics(
    reference_xy: np.ndarray, moving_xy: np.ndarray
) -> dict[str, Any]:
    transform = fit_similarity(reference_xy, moving_xy)
    predicted = apply_similarity(reference_xy, transform)
    residual = moving_xy - predicted
    a, b, _, _ = transform
    return {
        "scale_disagreement_percent": (math.hypot(a, b) - 1.0) * 100.0,
        "rotation_disagreement_degrees": math.degrees(math.atan2(b, a)),
        "nontranslation_residual_rms_output_px": float(
            np.sqrt(np.mean(np.sum(residual * residual, axis=1)))
        ),
        "input_only": True,
        "fitted_transform": [float(value) for value in transform],
    }


def commission_warp(definition: dict[str, Any]) -> dict[str, Any]:
    rng = np.random.default_rng(MASTER_SEED + 1)
    reference = rng.uniform(-1200.0, 1200.0, size=(512, 2))
    measurement_noise = rng.normal(0.0, 0.008, size=reference.shape)
    null_moving = reference + measurement_noise

    planted_scale = 1.0025
    planted_rotation = math.radians(0.05)
    planted = (
        planted_scale * math.cos(planted_rotation),
        planted_scale * math.sin(planted_rotation),
        0.45,
        -0.30,
    )
    degraded_moving = apply_similarity(reference, planted) + measurement_noise

    calibration = np.arange(0, len(reference), 2)
    holdout = np.arange(1, len(reference), 2)
    fitted = fit_similarity(reference[calibration], degraded_moving[calibration])
    corrected_holdout = apply_similarity(
        degraded_moving[holdout], invert_similarity(fitted)
    )

    null_metrics = geometry_metrics(reference[holdout], null_moving[holdout])
    degradation_metrics = geometry_metrics(
        reference[holdout], degraded_moving[holdout]
    )
    improvement_metrics = geometry_metrics(
        reference[holdout], corrected_holdout
    )
    null_verdict = validate_geometry(null_metrics, definition)
    degradation_verdict = validate_geometry(degradation_metrics, definition)
    improvement_verdict = validate_geometry(improvement_metrics, definition)
    assertions = {
        "null_is_nonzero": null_metrics[
            "nontranslation_residual_rms_output_px"
        ]
        > 0.0,
        "null_passes": null_verdict["verdict"] == "PASS",
        "planted_degradation_fails": degradation_verdict["verdict"]
        == "UNMEASURED_WARP_INADEQUATE",
        "planted_improvement_passes": improvement_verdict["verdict"] == "PASS",
        "improvement_reduces_scale_error": abs(
            improvement_metrics["scale_disagreement_percent"]
        )
        < abs(degradation_metrics["scale_disagreement_percent"]),
        "improvement_reduces_rotation_error": abs(
            improvement_metrics["rotation_disagreement_degrees"]
        )
        < abs(degradation_metrics["rotation_disagreement_degrees"]),
    }
    return {
        "landmark_count": int(len(reference)),
        "fit_count": int(len(calibration)),
        "holdout_count": int(len(holdout)),
        "planted_transform": [float(value) for value in planted],
        "null": {"metrics": null_metrics, "gate": null_verdict},
        "degradation": {
            "metrics": degradation_metrics,
            "gate": degradation_verdict,
        },
        "improvement": {
            "metrics": improvement_metrics,
            "gate": improvement_verdict,
        },
        "assertions": assertions,
        "verdict": "PASS" if all(assertions.values()) else "FAIL",
    }


def main() -> None:
    definition, definition_sha = load_checker_definition()
    registration = load_registration(definition, definition_sha)
    boundary_registration = registration["boundary_reduction_arm"]
    green_registration = registration["green_recovery_arm"]
    boundary_amplitude = float(
        boundary_registration["rim_component_fraction_of_step"]
    )
    green_amplitude = float(
        green_registration["rim_component_fraction_of_step"]
    )
    identity = lambda output, offsets, step: output.copy()
    identity_patch = lambda patch, step: patch.copy()
    rim6 = lambda output, offsets, step: output + rim_delta(offsets, step, 0.06)
    rim6_patch = lambda patch, step: patch_delta(patch, step, rim=0.06)
    opposite6 = (
        lambda output, offsets, step: output
        + opposite_rim_delta(offsets, step, 0.06)
    )
    opposite6_patch = lambda patch, step: patch_delta(
        patch, step, rim=0.06, opposite=True
    )
    veil6 = (
        lambda output, offsets, step: output
        + two_sided_veil_delta(offsets, step, 0.06)
    )
    veil6_patch = lambda patch, step: patch_delta(patch, step, veil=0.06)
    one_side6 = (
        lambda output, offsets, step: output
        + one_sided_veil_delta(offsets, step, 0.06)
    )
    combined6 = (
        lambda output, offsets, step: output
        + rim_delta(offsets, step, 0.06)
        + two_sided_veil_delta(offsets, step, 0.06)
    )
    combined6_patch = lambda patch, step: patch_delta(
        patch, step, rim=0.06, veil=0.06
    )
    reduced_boundary = (
        lambda output, offsets, step: output
        + rim_delta(offsets, step, boundary_amplitude)
        + two_sided_veil_delta(offsets, step, boundary_amplitude)
    )
    reduced_boundary_patch = lambda patch, step: patch_delta(
        patch,
        step,
        rim=boundary_amplitude,
        veil=boundary_amplitude,
    )
    green_recovery = (
        lambda output, offsets, step: output
        + rim_delta(offsets, step, green_amplitude)
        + two_sided_veil_delta(offsets, step, green_amplitude)
    )
    green_recovery_patch = lambda patch, step: patch_delta(
        patch,
        step,
        rim=green_amplitude,
        veil=green_amplitude,
    )
    blurred = lambda output, offsets, step: ndimage.gaussian_filter1d(
        output, sigma=5.0, mode="nearest"
    )
    blurred_patch = lambda patch, step: ndimage.gaussian_filter(
        patch, sigma=5.0, mode="nearest"
    )
    shifted_patch = lambda patch, step: ndimage.shift(
        patch, shift=(0.0, 3.0), order=3, mode="nearest", prefilter=True
    )

    arm_specs = [
        (
            "clean_noise_null",
            identity,
            identity_patch,
            0.0,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "noise_sensitivity_degradation",
            identity,
            identity_patch,
            0.0,
            NOISE_STRESS_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_6pct_rim",
            rim6,
            rim6_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_6pct_opposite_sign_rim",
            opposite6,
            opposite6_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_6pct_two_sided_veil",
            veil6,
            veil6_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_6pct_one_sided_far_veil",
            one_side6,
            identity_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_6pct_rim_and_veil",
            combined6,
            combined6_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            boundary_registration["name"],
            reduced_boundary,
            reduced_boundary_patch,
            boundary_amplitude,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            green_registration["name"],
            green_recovery,
            green_recovery_patch,
            green_amplitude,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_blur_degradation",
            blurred,
            blurred_patch,
            0.0,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "planted_rho_phase_degradation",
            identity,
            shifted_patch,
            0.0,
            NOISE_SIGMA_FRACTION,
            0.0,
            None,
        ),
        (
            "allowed_warp_clean_null",
            identity,
            identity_patch,
            0.0,
            NOISE_SIGMA_FRACTION,
            ALLOWED_WARP_RESIDUAL_NATIVE_PX,
            None,
        ),
        (
            "allowed_warp_one_sided_6pct_veil",
            one_side6,
            identity_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            ALLOWED_WARP_RESIDUAL_NATIVE_PX,
            None,
        ),
        (
            "single_site_6pct_one_sided_veil",
            one_side6,
            identity_patch,
            0.06,
            NOISE_SIGMA_FRACTION,
            0.0,
            0,
        ),
    ]

    arms: list[dict[str, Any]] = []
    for (
        name,
        profile_plant,
        patch_plant,
        amplitude,
        noise,
        warp,
        sparse,
    ) in arm_specs:
        summary, _ = arm_summary(
            name,
            profile_plant,
            patch_plant,
            definition,
            amplitude,
            noise_sigma_fraction=noise,
            warp_residual_native_px=warp,
            sparse_site=sparse,
        )
        arms.append(summary)

    by_name = {arm["name"]: arm for arm in arms}
    boundary_arm = by_name[boundary_registration["name"]]
    green_arm = by_name[green_registration["name"]]
    boundary_arm["registered_role"] = "BOUNDARY_REDUCTION_REMAINS_RED"
    boundary_arm["expected_gate_result"] = boundary_registration[
        "expected_gate_result"
    ]
    green_arm["registered_role"] = "SUB_BOUNDARY_GREEN_RECOVERY"
    green_arm["expected_gate_result"] = green_registration[
        "expected_gate_result"
    ]
    sparse = by_name["single_site_6pct_one_sided_veil"]
    sparse_legacy_checks = {
        name: passed
        for name, passed in sparse["checks"].items()
        if name != "headline_maximum"
    }
    warp = commission_warp(definition)
    assertions = {
        "clean_noise_null_is_nonzero": by_name["clean_noise_null"][
            "median_v_e"
        ]
        > 0.0,
        "clean_noise_null_passes": by_name["clean_noise_null"]["verdict"]
        == "PASS",
        "noise_sensitivity_arm_moves": by_name[
            "noise_sensitivity_degradation"
        ]["median_v_e"]
        > by_name["clean_noise_null"]["median_v_e"],
        "noise_sensitivity_arm_fails": by_name[
            "noise_sensitivity_degradation"
        ]["verdict"]
        == "FAIL",
        "both_rim_signs_detected": min(
            by_name["planted_6pct_rim"]["detection_rate"],
            by_name["planted_6pct_opposite_sign_rim"]["detection_rate"],
        )
        >= 0.95,
        "two_sided_veil_detected": by_name[
            "planted_6pct_two_sided_veil"
        ]["detection_rate"]
        >= 0.95,
        "one_sided_far_veil_detected": by_name[
            "planted_6pct_one_sided_far_veil"
        ]["detection_rate"]
        >= 0.95,
        "side_max_exceeds_retired_pool_on_one_sided_veil": by_name[
            "planted_6pct_one_sided_far_veil"
        ]["median_v_e"]
        > by_name["planted_6pct_one_sided_far_veil"][
            "median_v_e_pooled_diagnostic"
        ],
        "improvement_reduces_h_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_h_e"]
            - boundary_arm["median_h_e"]
        )
        >= 0.05,
        "improvement_reduces_v_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_v_e"]
            - boundary_arm["median_v_e"]
        )
        >= 0.05,
        "improved_arm_fails_median_h_e": (
            boundary_arm["verdict"] == "FAIL"
            and sorted(
                name
                for name, passed in boundary_arm["checks"].items()
                if not passed
            )
            == ["median_h_e"]
        ),
        "green_recovery_reduces_h_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_h_e"]
            - green_arm["median_h_e"]
        )
        >= 0.05,
        "green_recovery_reduces_v_by_at_least_5pp": (
            by_name["planted_6pct_rim_and_veil"]["median_v_e"]
            - green_arm["median_v_e"]
        )
        >= 0.05,
        "green_recovery_passes_all_gates": green_arm["verdict"] == "PASS",
        "blur_guard_fails": not by_name["planted_blur_degradation"]["checks"][
            "edge_width"
        ],
        "rho_diagnostic_can_fail": not by_name[
            "planted_rho_phase_degradation"
        ]["checks"]["rho_edge"],
        "allowed_warp_null_passes": by_name["allowed_warp_clean_null"][
            "verdict"
        ]
        == "PASS",
        "allowed_warp_does_not_hide_veil": by_name[
            "allowed_warp_one_sided_6pct_veil"
        ]["detection_rate"]
        >= 0.95,
        "literal_headline_catches_sparse_defect": sparse["verdict"] == "FAIL"
        and not sparse["checks"]["headline_maximum"],
        "sparse_defect_would_pass_old_distribution_tuple": all(
            sparse_legacy_checks.values()
        ),
        "warp_null_degradation_improvement_pass": warp["verdict"] == "PASS",
    }
    failed = [name for name, passed in assertions.items() if not passed]
    result = {
        "schema": "m169-m3-checker-commission-v3",
        "registration_sha256": sha256_file(REGISTRATION),
        "adjudication": registration["authority"],
        "master_seed": MASTER_SEED,
        "checker_definition_sha256": definition_sha,
        "checker_source_sha256": sha256_file(HERE / "m3_checker_v2.py"),
        "commission_source_sha256": sha256_file(HERE / "full_commission.py"),
        "candidate_outputs_opened": 0,
        "comparator_outputs_opened": 0,
        "capture_pixels_opened": 0,
        "host_policy": (
            "orchestrator 2026-09-04: deterministic correctness work proceeds; "
            "no exclusive host lock"
        ),
        "synthetic_site_count_per_arm": SITE_COUNT,
        "source_profiles_per_site": SOURCE_COUNT,
        "arms": arms,
        "warp_commission": warp,
        "assertions": assertions,
        "verdict": "PASS" if not failed else "NOT_ADMITTED_COMMISSIONING_FAILED",
        "failed_assertions": failed,
    }
    write_json(OUT, result)
    digest = sha256_file(OUT)
    OUT.with_suffix(".sha256").write_text(
        f"{digest}  {OUT.name}\n", encoding="ascii"
    )
    for arm in arms:
        print(
            f"{arm['name']}: h50={arm['median_h_e']:.6f} "
            f"v50={arm['median_v_e']:.6f} "
            f"v99={arm['p99_v_e']:.6f} "
            f"max={arm['maximum_max_h_v']:.6f} "
            f"affected={arm['affected_edge_rate']:.3%} "
            f"verdict={arm['verdict']}"
        )
    print(f"warp={warp['verdict']}")
    print(f"commission sha256={digest}")
    if failed:
        print("NOT ADMITTED: failed assertions=" + ",".join(failed))
        raise SystemExit(3)
    print("BATTERY COMMISSIONED")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
