from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

from m10_checker import UncertaintyInput, score_legacy, score_repaired


OUT = Path(__file__).with_name("commission.json")
SEED = 20260904
N = 20_000


def value_fixture(residual_steps: np.ndarray) -> dict[str, float]:
    centred = residual_steps - float(np.mean(residual_steps))
    return {
        "valid_fraction": 1.0,
        "rank_correlation": 0.9995,
        "median_abs_error_steps": float(np.median(np.abs(centred))),
        "p95_abs_error_steps": float(np.quantile(np.abs(centred), 0.95)),
        "ruler_slope_error_fraction": 0.01,
        "flat_null_p95_range_steps": 0.20,
        "synthetic_layer_confusion_fraction": 0.005,
    }


def score(
    values: dict[str, float],
    residual: np.ndarray,
    candidate_sigma: np.ndarray,
    truth_sigma: np.ndarray,
) -> dict:
    return score_repaired(
        values,
        UncertaintyInput(
            residual_steps=residual,
            candidate_sigma_steps=candidate_sigma,
            truth_sigma_steps=truth_sigma,
            valid=np.ones(residual.size, dtype=bool),
        ),
    )


def main() -> int:
    rng = np.random.default_rng(SEED)
    candidate_sigma = rng.uniform(0.12, 0.24, size=N)
    truth_sigma = np.zeros(N)
    residual = rng.normal(0.0, candidate_sigma)
    values = value_fixture(residual)

    substitutions = {
        "reported": candidate_sigma,
        "zero": np.zeros(N),
        "infinity": np.full(N, np.inf),
        "random": np.random.default_rng(SEED + 1).uniform(0.01, 0.80, size=N),
    }
    legacy = {
        name: score_legacy(values, sigma)
        for name, sigma in substitutions.items()
    }
    legacy_hashes = {
        name: hashlib.sha256(
            json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for name, result in legacy.items()
    }
    repaired = {
        name: score(values, residual, sigma, truth_sigma)
        for name, sigma in substitutions.items()
    }

    scaled_sigma = candidate_sigma * 1.25
    moved_null = score(values, residual, scaled_sigma, truth_sigma)

    degraded_residual = residual * 1.50
    degraded = score(
        value_fixture(degraded_residual),
        degraded_residual,
        candidate_sigma,
        truth_sigma,
    )

    underconfident_sigma = candidate_sigma * 0.50
    before_improvement = score(values, residual, underconfident_sigma, truth_sigma)
    after_improvement = repaired["reported"]

    root = Path(__file__).resolve().parents[2]
    main_rs = (root / "crates/strehl-cli/src/main.rs").read_text(encoding="utf-8")
    product_fields = {
        "depth_map_option_count": main_rs.count("depth_map: Option<PathBuf>"),
        "sigma_z_map_option_count": main_rs.count("sigma_z_map: Option<PathBuf>"),
    }

    legacy_reference = legacy["reported"]
    legacy_invariant = (
        all(result == legacy_reference for result in legacy.values())
        and len(set(legacy_hashes.values())) == 1
    )
    base_metrics = repaired["reported"]["uncertainty"]["metrics"]
    moved_metrics = moved_null["uncertainty"]["metrics"]
    null_moved = any(
        base_metrics[key] != moved_metrics[key]
        for key in (
            "interval_coverage_95",
            "decile_variance_ratios",
            "median_reported_95_half_width_steps",
            "p95_reported_95_half_width_steps",
            "mean_gaussian_crps_steps",
        )
    )
    arms = {
        name: {
            "pass": result["pass"],
            "uncertainty": result["uncertainty"],
        }
        for name, result in repaired.items()
    }
    arms["sigma_x1p25"] = {
        "pass": moved_null["pass"],
        "uncertainty": moved_null["uncertainty"],
    }
    arms["depth_residual_x1p50"] = {
        "pass": degraded["pass"],
        "value": degraded["value"],
        "uncertainty": degraded["uncertainty"],
    }
    arms["sigma_x0p50"] = {
        "pass": before_improvement["pass"],
        "uncertainty": before_improvement["uncertainty"],
    }

    result = {
        "schema": "strehl.m163-m10-commission.v1",
        "seed": SEED,
        "population": N,
        "probe_nontriviality": {
            "residual_sd_steps": float(np.std(residual)),
            "residual_nonzero_count": int(np.count_nonzero(residual)),
            "candidate_sigma_p05_steps": float(np.quantile(candidate_sigma, 0.05)),
            "candidate_sigma_p95_steps": float(np.quantile(candidate_sigma, 0.95)),
        },
        "legacy_zero_infinity_random": {
            "all_results_identical": legacy_invariant,
            "canonical_sha256": legacy_hashes,
            "canonical_result": legacy_reference,
        },
        "uncertainty_arms": arms,
        "movable_null": {
            "disturbance": "multiply every reported candidate sigma by 1.25",
            "before_arm": "reported",
            "after_arm": "sigma_x1p25",
            "metrics_moved": null_moved,
        },
        "planted_degradation": {
            "disturbance": "multiply every depth residual by 1.50 while holding sigma fixed",
            "before_arm": "reported",
            "after_arm": "depth_residual_x1p50",
        },
        "planted_improvement": {
            "disturbance": (
                "replace a 0.50x under-reported sigma field with the calibrated "
                "reported field while holding depth residuals fixed"
            ),
            "before_arm": "sigma_x0p50",
            "after_arm": "reported",
        },
        "bar_relation": {
            "classification": "HARDER",
            "existing_value_bars_retained": 7,
            "new_uncertainty_vetoes": 5,
        },
        "current_product_preflight": {
            **product_fields,
            "required_numeric_planes": 2,
            "advertised_numeric_planes": sum(product_fields.values()),
            "pass": all(value == 1 for value in product_fields.values()),
            "scope": "Input-contract preflight only; not a scored M10 result.",
        },
    }
    OUT.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(f"population={N}")
    print(f"legacy_invariant={legacy_invariant}")
    for name in ("reported", "zero", "infinity", "random"):
        u = arms[name]["uncertainty"]["metrics"]
        print(
            f"{name}: pass={arms[name]['pass']} "
            f"coverage={u.get('interval_coverage_95')} "
            f"deciles={u.get('deciles_within_variance_ratio_bar')} "
            f"p95_half_width={u.get('p95_reported_95_half_width_steps')} "
            f"crps={u.get('mean_gaussian_crps_steps')}"
        )
    print(
        "movable_null:",
        f"moved={null_moved}",
        f"before_pass={arms['reported']['pass']}",
        f"after_pass={arms['sigma_x1p25']['pass']}",
    )
    print(
        "degradation:",
        f"before_crps={base_metrics['mean_gaussian_crps_steps']}",
        f"after_crps={degraded['uncertainty']['metrics']['mean_gaussian_crps_steps']}",
        f"after_pass={degraded['pass']}",
    )
    print(
        "improvement:",
        f"before_crps={arms['sigma_x0p50']['uncertainty']['metrics']['mean_gaussian_crps_steps']}",
        f"after_crps={base_metrics['mean_gaussian_crps_steps']}",
        f"before_pass={arms['sigma_x0p50']['pass']}",
        f"after_pass={arms['reported']['pass']}",
    )
    print(
        "current_product_preflight:",
        f"{result['current_product_preflight']['advertised_numeric_planes']}/"
        f"{result['current_product_preflight']['required_numeric_planes']}",
        f"pass={result['current_product_preflight']['pass']}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
