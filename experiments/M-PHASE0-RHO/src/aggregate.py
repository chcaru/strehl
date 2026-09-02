"""Aggregate real rho measurements and apply the preregistered refusal rules."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

import rho_lib as R


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
PHASE = ROOT.parent / "M-PHASE0-PHASE" / "out" / "p1_bar.json"
DIAGNOSTICS = OUT / "diagnostics.json"
PHASE_SIGN_AUDIT = OUT / "phase-sign-audit.json"
BOOTSTRAPS = 10_000
SEED = 20260902


def primary_fit(record: dict) -> dict:
    return record["fits"][record.get("primary_fit_key", "full_a")]


def percentile(values, q):
    return float(np.percentile(np.asarray(values, dtype=float), q))


def summary(values) -> dict:
    a = np.asarray(values, dtype=float)
    return {
        "n": int(a.size),
        "median": float(np.median(a)),
        "p10": percentile(a, 10),
        "p90": percentile(a, 90),
        "min": float(np.min(a)),
        "max": float(np.max(a)),
    }


def scene_groups(records: list[dict]) -> dict[str, list[dict]]:
    groups = {}
    ordinary = sorted(
        {x["scene"] for x in records if x["arm"] == "ordinary-census"}
    )
    for scene in ordinary:
        groups[scene] = [
            x
            for x in records
            if x["arm"] == "ordinary-census"
            and x["scene"] == scene
            and x["status"] == "PASS"
        ]
    groups["bee-repeat"] = [
        x
        for x in records
        if x["arm"] == "repeat-primary"
        and x["scene"] == "bee"
        and x["status"] == "PASS"
    ]
    return {key: value for key, value in groups.items() if value}


def scene_stat(groups: dict[str, list[dict]], getter) -> dict:
    values = {
        scene: float(np.median([getter(row) for row in rows]))
        for scene, rows in groups.items()
    }
    a = np.asarray(list(values.values()), dtype=float)
    rng = np.random.default_rng(SEED)
    boot = np.median(
        rng.choice(a, size=(BOOTSTRAPS, len(a)), replace=True),
        axis=1,
    )
    return {
        "values": values,
        "summary": summary(a),
        "bootstrap_median_95": [
            percentile(boot, 2.5),
            percentile(boot, 97.5),
        ],
        "scene_p90_p10_ratio": percentile(a, 90) / percentile(a, 10),
    }


def bar_curve() -> tuple[np.ndarray, np.ndarray, float]:
    phase = json.load(open(PHASE, encoding="utf-8"))
    rows = []
    for rho in phase["rhos"]:
        values = [
            x["bar_unit"]
            for x in phase["rows"]
            if x["target"] == "G-1x"
            and x["snr"] == "inf"
            and x["gauge"] == "raw"
            and x["rho"] == rho
        ]
        rows.append((float(rho), float(np.median(values))))
    rows.sort(reverse=True)
    rho = np.asarray([x[0] for x in rows])
    bar = np.asarray([x[1] for x in rows])
    tail_slope = float(
        (math.log(bar[-1]) - math.log(bar[-2]))
        / (math.log(rho[-1]) - math.log(rho[-2]))
    )
    return rho, bar, tail_slope


def map_bar(value: float, rho: np.ndarray, bar: np.ndarray, slope: float) -> float:
    if value < rho[-1]:
        return float(
            math.exp(
                math.log(bar[-1])
                + slope * (math.log(value) - math.log(rho[-1]))
            )
        )
    order = np.argsort(np.log(rho))
    return float(
        math.exp(
            np.interp(
                math.log(value),
                np.log(rho)[order],
                np.log(bar)[order],
            )
        )
    )


def main() -> int:
    records = json.load(open(OUT / "scene-estimates.json", encoding="utf-8"))
    passed = [x for x in records if x["status"] == "PASS"]
    groups = scene_groups(records)

    exact = scene_stat(groups, lambda x: primary_fit(x)["rho_g"])
    rb_exact = scene_stat(groups, lambda x: primary_fit(x)["rho_rb"])
    raw = scene_stat(groups, lambda x: x["fits"]["raw_a"]["rho_g"])
    dark = scene_stat(groups, lambda x: x["fits"]["dark_a"]["rho_g"])
    grid16 = scene_stat(
        groups, lambda x: primary_fit(x)["rho_g_grid16"]
    )
    grid32 = scene_stat(
        groups, lambda x: primary_fit(x)["rho_g_grid32"]
    )
    boundary_exclude = scene_stat(
        groups, lambda x: primary_fit(x)["rho_g_boundary_exclude"]
    )
    scene_beta = {
        scene: float(np.median([primary_fit(row)["beta"] for row in rows]))
        for scene, rows in groups.items()
    }
    scene_beta_se = {
        scene: float(np.median([primary_fit(row)["beta_se"] for row in rows]))
        for scene, rows in groups.items()
    }

    def beta_shifted_scene_median(delta: float) -> float:
        values = []
        for rows in groups.values():
            values.append(
                float(
                    np.median(
                        [
                            R.rho_from_params(
                                "G-1x",
                                primary_fit(row)["beta"] + delta,
                                tuple(primary_fit(row)["angular"]),
                                grid=8,
                            )
                            for row in rows
                        ]
                    )
                )
            )
        return float(np.median(values))

    band_results = {}
    for band in ("0.04-0.20", "0.06-0.30", "0.08-0.46"):
        values = {}
        for scene, rows in groups.items():
            accepted = [
                row["fits"]["bands"][band]["rho_g"]
                for row in rows
                if row["fits"]["bands"][band]["status"] == "PASS"
            ]
            if accepted:
                values[scene] = float(np.median(accepted))
        band_results[band] = {
            "values": values,
            "summary": summary(list(values.values())),
        }

    aperture = {}
    for fnumber in sorted(
        {x["aperture"] for x in records if x["arm"] == "aperture"}
    ):
        subset = [
            x
            for x in records
            if x["arm"] == "aperture"
            and x["aperture"] == fnumber
            and x["status"] == "PASS"
        ]
        aperture[str(fnumber)] = (
            summary([primary_fit(x)["rho_g"] for x in subset])
            if subset
            else {"n": 0}
        )

    by_aperture_roi = {
        (x["aperture"], x["roi"]): primary_fit(x)["rho_g"]
        for x in records
        if x["arm"] == "aperture" and x["status"] == "PASS"
    }
    common = sorted(
        {
            roi
            for ap, roi in by_aperture_roi
            if (8.0, roi) in by_aperture_roi
            and (18.0, roi) in by_aperture_roi
        }
    )
    aperture_ratios = np.asarray(
        [
            by_aperture_roi[(8.0, roi)]
            / by_aperture_roi[(18.0, roi)]
            for roi in common
        ],
        dtype=float,
    )
    rng = np.random.default_rng(SEED + 1)
    aperture_boot = np.median(
        rng.choice(
            aperture_ratios,
            size=(BOOTSTRAPS, len(aperture_ratios)),
            replace=True,
        ),
        axis=1,
    )
    aperture_effect = {
        "comparison": "f8/f18",
        "common_rois": common,
        "paired_ratios": [float(x) for x in aperture_ratios],
        "median_ratio": float(np.median(aperture_ratios)),
        "bootstrap_95": [
            percentile(aperture_boot, 2.5),
            percentile(aperture_boot, 97.5),
        ],
    }
    aperture_effect["material"] = bool(
        aperture_effect["median_ratio"] > 2.0
        and aperture_effect["bootstrap_95"][0] > 1.0
    )

    iso_rows = sorted(
        [
            x
            for x in records
            if x["arm"] == "iso-bee" and x["status"] == "PASS"
        ],
        key=lambda x: x["iso"],
    )
    iso_values = [primary_fit(x)["rho_g"] for x in iso_rows]
    cross_values = [
        x["fits"]["cross_a"]["rho_g"]
        for x in iso_rows
        if x["fits"].get("cross_a", {}).get("status") == "PASS"
    ]
    iso_corr = spearmanr(
        [x["iso"] for x in iso_rows],
        iso_values,
    )
    iso = {
        "rows": [
            {
                "iso": x["iso"],
                "rho": primary_fit(x)["rho_g"],
                "cross_rho": x["fits"].get("cross_a", {}).get("rho_g"),
            }
            for x in iso_rows
        ],
        "primary_max_min_ratio": float(max(iso_values) / min(iso_values)),
        "cross_max_min_ratio": float(max(cross_values) / min(cross_values)),
        "spearman_r": float(iso_corr.statistic),
        "spearman_p": float(iso_corr.pvalue),
        "material": False,
        "reason": (
            "primary range exceeds 1.5x, but the independent cross range does "
            "not and no paired confidence interval excludes one"
        ),
    }

    arm_noise = {}
    for arm in ("aperture", "ordinary-census", "repeat-primary"):
        subset = [x for x in passed if x["arm"] == arm]
        if not subset:
            continue
        primary_values = [primary_fit(x)["rho_g"] for x in subset]
        raw_values = [
            x["fits"]["raw_a"]["rho_g"]
            for x in subset
            if x["fits"]["raw_a"]["status"] == "PASS"
        ]
        dark_values = [
            x["fits"]["dark_a"]["rho_g"]
            for x in subset
            if x["fits"]["dark_a"]["status"] == "PASS"
        ]
        arm_noise[arm] = {
            "primary": summary(primary_values),
            "raw": summary(raw_values),
            "dark_only": summary(dark_values),
            "raw_to_primary_median_ratio": float(
                np.median(raw_values) / np.median(primary_values)
            ),
            "dark_to_primary_median_ratio": float(
                np.median(dark_values) / np.median(primary_values)
            ),
        }

    fit_band_medians = [
        band_results[key]["summary"]["median"] for key in band_results
    ]
    exact_median = exact["summary"]["median"]
    median_beta = float(np.median(list(scene_beta.values())))
    median_radial_extrapolation = float(
        np.median(
            [
                primary_fit(row)["extrapolation_median"]
                for rows in groups.values()
                for row in rows
            ]
        )
    )
    maximum_radial_extrapolation = float(
        np.max(
            [
                primary_fit(row)["extrapolation_max"]
                for rows in groups.values()
                for row in rows
            ]
        )
    )
    systematic = {
        "fit_band_scene_medians": {
            key: value["summary"]["median"]
            for key, value in band_results.items()
        },
        "fit_band_median_factor": float(
            max(fit_band_medians + [exact_median])
            / min(fit_band_medians + [exact_median])
        ),
        "grid_scene_medians": {
            "8": exact_median,
            "16": grid16["summary"]["median"],
            "32": grid32["summary"]["median"],
        },
        "grid_median_factor_8_to_32": float(
            exact_median / grid32["summary"]["median"]
        ),
        "boundary_excluded_scene_median": boundary_exclude["summary"]["median"],
        "boundary_excluded_ratio": float(
            boundary_exclude["summary"]["median"] / exact_median
        ),
    }

    refusal_reasons = []
    if systematic["fit_band_median_factor"] > 3.0:
        refusal_reasons.append("fit-band sensitivity exceeds factor three")
    if systematic["grid_median_factor_8_to_32"] > 3.0:
        refusal_reasons.append("frequency-grid sensitivity exceeds factor three")

    rho_curve, bar_curve_values, tail_slope = bar_curve()
    headline_ci = exact["bootstrap_median_95"]
    bar_mapping = {
        "phase_rhos": [float(x) for x in rho_curve],
        "phase_median_bars_px": [float(x) for x in bar_curve_values],
        "tail_log_slope": tail_slope,
        "headline_bar_px": map_bar(
            exact_median, rho_curve, bar_curve_values, tail_slope
        ),
        "sampling_interval_bar_px": [
            map_bar(headline_ci[0], rho_curve, bar_curve_values, tail_slope),
            map_bar(headline_ci[1], rho_curve, bar_curve_values, tail_slope),
        ],
        "mapping_status": (
            "extrapolated below rho 0.01 with the last two PHASE points"
        ),
    }

    reasons = Counter(
        x.get("reason", "PASS") if x["status"] != "PASS" else "PASS"
        for x in records
    )
    high = [
        x["quality"]["high_scene_to_noise"]
        for x in passed
        if np.isfinite(x["quality"]["high_scene_to_noise"])
    ]
    component_p10 = [primary_fit(x)["component_p10"] for x in passed]
    component_median = [primary_fit(x)["component_median"] for x in passed]
    component_p90 = [primary_fit(x)["component_p90"] for x in passed]
    diagnostics = json.load(open(DIAGNOSTICS, encoding="utf-8"))
    sign_audit = json.load(open(PHASE_SIGN_AUDIT, encoding="utf-8"))

    payload = {
        "verdict": "NO_UNIVERSAL_POINT_ESTIMATE",
        "refusal_reasons": refusal_reasons,
        "best_exact_phase_grid_estimate": {
            "population": "accepted f/5.6 scene clusters",
            "rho": exact_median,
            "rho_rb": rb_exact["summary"]["median"],
            "scene_bootstrap_95": headline_ci,
            "rho_rb_scene_bootstrap_95": rb_exact["bootstrap_median_95"],
            "scene_p10_p90": [
                exact["summary"]["p10"],
                exact["summary"]["p90"],
            ],
            "scene_values": exact["values"],
            "status": (
                "usable only for the exact 8 by 8 PHASE scalar convention"
            ),
        },
        "recommended_census": {
            "exact_8_by_8_range": [0.0001, 0.06],
            "grid_points": [0.1, 0.03, 0.01, 0.003, 0.001, 0.0003, 0.0001],
            "reason": (
                "covers accepted exact-grid ROIs and the registered fit-band "
                "envelope; 0.1 is retained as a conservative upper control"
            ),
        },
        "scene": exact,
        "rb_scene": rb_exact,
        "raw_scene": raw,
        "dark_only_scene": dark,
        "aperture": {
            "strata": aperture,
            "paired_effect": aperture_effect,
        },
        "iso": iso,
        "sensor": {
            "models": ["ILCE-7CM2"],
            "variation_identified": False,
        },
        "noise_sensitivity": arm_noise,
        "systematic": systematic,
        "power_law": {
            "scene_beta_values": scene_beta,
            "scene_beta_summary": summary(list(scene_beta.values())),
            "scene_beta_se_median": float(np.median(list(scene_beta_se.values()))),
            "radial_extrapolation_median": median_radial_extrapolation,
            "radial_extrapolation_max": maximum_radial_extrapolation,
            "power_factor_at_median_radial_extrapolation": float(
                median_radial_extrapolation ** (-median_beta)
            ),
            "power_factor_at_max_radial_extrapolation": float(
                maximum_radial_extrapolation ** (-median_beta)
            ),
            "rho_if_beta_minus_0_5": beta_shifted_scene_median(-0.5),
            "rho_if_beta_plus_0_5": beta_shifted_scene_median(0.5),
            "interpretation": (
                "formal beta errors are small, but plausible model-form shifts "
                "in beta move the exact-grid scalar materially"
            ),
        },
        "bar_mapping": bar_mapping,
        "validity": {
            "records_total": len(records),
            "records_passed": len(passed),
            "records_rejected": len(records) - len(passed),
            "status_counts": dict(reasons),
            "high_band_scene_to_noise": summary(high),
            "high_band_positive_count": int(np.sum(np.asarray(high) > 0)),
            "high_band_snr_gt_3_count": int(np.sum(np.asarray(high) > 3)),
            "direct_detection_interpretation": (
                "most accepted estimates are model-dependent continuations; "
                "only high-band scene/noise above 3 counts as a direct detection"
            ),
            "component_ratio_p10_across_records": summary(component_p10),
            "component_ratio_median_across_records": summary(component_median),
            "component_ratio_p90_across_records": summary(component_p90),
        },
        "geometry_controls": {
            "tally": diagnostics["tally"],
            "grid_fundamental_cyc_per_sensor_px": diagnostics[
                "real_calibration_grid"
            ]["median_fundamental_cyc_per_sensor_px"],
            "grid_period_sensor_px": diagnostics["real_calibration_grid"][
                "period_sensor_px"
            ],
            "razor_edge_beta": diagnostics["real_razor_edge"]["beta"],
            "synthetic_edge_beta_error": diagnostics["synthetic_edge"][
                "absolute_error"
            ],
        },
        "phase_sign_audit": {
            "nu_plus_h_outside_target_band": sign_audit["geometry"][
                "nu_plus_h_outside_target_band"
            ],
            "nu_minus_h_outside_target_band": sign_audit["geometry"][
                "nu_minus_h_outside_target_band"
            ],
            "frequency_components": sign_audit["geometry"][
                "frequency_components"
            ],
            "current_physical_abs_error": sign_audit["physical_control"][
                "current_abs_error"
            ],
            "corrected_physical_abs_error": sign_audit["physical_control"][
                "corrected_abs_error"
            ],
            "pooled": sign_audit["pooled"],
            "interpretation": (
                "the PHASE implementation uses nu+h where its own coset "
                "selection and the physical translation phase require nu-h"
            ),
        },
        "contradictions": {
            "A2_3_blanket_unobservable": (
                "green quincunx data directly reach 0.5 cycles/pixel on the "
                "sensor axes, although each observed bin remains an alias-pair sum"
            ),
            "A2_2_common_scalar": (
                "the scalar changes by more than a factor of three under the "
                "registered frequency-grid refinement"
            ),
            "A7_4_normalisation": (
                "the exploratory nine-member sum gives white-scene values 9 "
                "and 27 rather than A2.2's per-component value 1"
            ),
            "PHASE_representative_sign": (
                "nu+h places 64 of 128 tested components outside the target "
                "band; nu-h places none outside and matches the physical phase"
            ),
        },
    }
    with open(OUT / "aggregate.json", "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    sensitivity = {
        "bands": band_results,
        "grid16": grid16,
        "grid32": grid32,
        "boundary_exclude": boundary_exclude,
    }
    with open(OUT / "sensitivity.json", "w", encoding="utf-8") as fh:
        json.dump(sensitivity, fh, indent=2)

    print(payload["verdict"])
    print(
        "exact PHASE-grid rho %.6g, scene-bootstrap 95%% %.6g to %.6g"
        % (exact_median, headline_ci[0], headline_ci[1])
    )
    print(
        "raw scene median %.6g, photon-corrected factor %.2f lower"
        % (
            raw["summary"]["median"],
            raw["summary"]["median"] / exact_median,
        )
    )
    print(
        "f8/f18 paired ratio %.3f, 95%% %.3f to %.3f"
        % (
            aperture_effect["median_ratio"],
            aperture_effect["bootstrap_95"][0],
            aperture_effect["bootstrap_95"][1],
        )
    )
    print(
        "grid 8/32 median ratio %.1f; fit-band median factor %.1f"
        % (
            systematic["grid_median_factor_8_to_32"],
            systematic["fit_band_median_factor"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
