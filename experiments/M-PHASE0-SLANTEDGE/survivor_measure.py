"""Black-box survivor measurements on the frozen slanted-edge plants.

Plants and adapters live here.  Expected values and verdicts do not.  Only
source-pinned vendored candidate functions are imported.
"""

from __future__ import annotations

import json
import math
import platform

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter
from scipy.special import expit, ndtr

from vendor_m1 import m1_tile
from vendor_ordinal import ordinal_shares, q25


BASE_SIGMA = 1.50
BLUR_SIGMA = 0.75
IMPROVED_SIGMA = 1.20
USM_RADIUS = 1.00
USM_AMOUNT = 0.50
NOISE_SD = 0.02
ANGLE_DEG = 5.0
SIDE = 256
NOISE_SEEDS = tuple(range(2026090300, 2026090324))
ANGLES = (0.5, 1.0, 5.0, 12.0)


def vertical_edge(
    sigma: float,
    angle_deg: float = ANGLE_DEG,
    h: int = SIDE,
    w: int = SIDE,
) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    slope = math.tan(math.radians(angle_deg))
    intercept = w / 2.0 - slope * (h - 1) / 2.0
    distance = (xx - (slope * yy + intercept)) / math.hypot(1.0, slope)
    return 0.2 + 0.6 * ndtr(distance / sigma)


def blur(image: np.ndarray) -> np.ndarray:
    return gaussian_filter(
        image, BLUR_SIGMA, mode="nearest", truncate=6.0
    )


def sharpen(image: np.ndarray) -> np.ndarray:
    low = gaussian_filter(
        image, USM_RADIUS, mode="nearest", truncate=6.0
    )
    return image + USM_AMOUNT * (image - low)


def point_maps(image: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "affine": 1.7 * image + 0.13,
        "gamma3": np.power(image, 3.0),
        "logistic": expit(10.0 * (image - 0.5)),
    }


def median(values: list[float]) -> float:
    return float(np.median(np.asarray(values, dtype=np.float64)))


def m1_trial(seed: int) -> dict[str, object]:
    rng = np.random.default_rng(seed)
    noises = [
        rng.normal(0.0, NOISE_SD, (SIDE, SIDE))
        for _ in range(5)
    ]
    noise_a, noise_b, noise_r, extra_a, extra_b = noises

    base_clean = vertical_edge(BASE_SIGMA)
    base_a = base_clean + noise_a
    base_b = base_clean + noise_b
    reference = base_clean + noise_r
    physical_blur = blur(base_clean)
    physical_improvement = vertical_edge(IMPROVED_SIGMA)
    unlicensed = vertical_edge(0.60)

    triplets: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]] = {
        "base": (base_a, base_b, reference),
        "identity": (base_a.copy(), base_b.copy(), reference.copy()),
        "blur": (
            physical_blur + noise_a,
            physical_blur + noise_b,
            reference,
        ),
        "improvement": (
            physical_improvement + noise_a,
            physical_improvement + noise_b,
            reference,
        ),
        "sharpen": (sharpen(base_a), sharpen(base_b), reference),
        "noise": (base_a + extra_a, base_b + extra_b, reference),
        "unlicensed": (
            unlicensed + noise_a,
            unlicensed + noise_b,
            reference,
        ),
    }
    for name in ("affine", "gamma3", "logistic"):
        maps_a = point_maps(base_a)
        maps_b = point_maps(base_b)
        maps_r = point_maps(reference)
        triplets[name] = (maps_a[name], maps_b[name], maps_r[name])

    arms = {
        name: m1_tile(a, b, ref)
        for name, (a, b, ref) in triplets.items()
    }
    angles = {}
    for angle in ANGLES:
        clean = vertical_edge(BASE_SIGMA, angle)
        angles[str(angle)] = m1_tile(
            clean + noise_a,
            clean + noise_b,
            clean + noise_r,
        )
    return {"seed": seed, "arms": arms, "angles": angles}


def aggregate_m1(trials: list[dict[str, object]]) -> dict[str, object]:
    fields = {}
    for field in ("f_licensed", "S_25", "gain_median"):
        arms = {}
        for arm in (
            "base", "identity", "blur", "improvement", "sharpen",
            "affine", "gamma3", "logistic", "unlicensed",
        ):
            arms[arm] = median([
                float(trial["arms"][arm][field])
                for trial in trials
            ])
        fields[field] = {
            "native_unit": {
                "f_licensed": "cycles_per_native_pixel_censored_at_0.25",
                "S_25": "dimensionless_minimum_detail_margin_0.20_to_0.25",
                "gain_median": "dimensionless_target_locked_gain_guard",
            }[field],
            "arms": arms,
            "noise": [
                float(trial["arms"]["noise"][field])
                for trial in trials
            ],
            "angles": {
                str(angle): median([
                    float(trial["angles"][str(angle)][field])
                    for trial in trials
                ])
                for angle in ANGLES
            },
            "angle_output": "NONE",
            "unlicensed_output_status": "NUMERIC_LICENSED_SCOPE_ONLY",
            "absolute_mtf50_status": "UNSUPPORTED",
        }

    bin_summaries = {}
    for arm in ("base", "blur", "improvement", "sharpen"):
        rows = []
        for index in range(10):
            rows.append({
                key: median([
                    float(trial["arms"][arm]["bins"][index][key])
                    for trial in trials
                ])
                for key in ("low", "high", "gain", "D", "FRC")
            })
        bin_summaries[arm] = rows

    return {
        "candidate": "SCORECARD-BASELINE/common.py::m1_tile",
        "claim_fields": ["f_licensed", "S_25"],
        "guard_fields": ["gain_median"],
        "fields": fields,
        "bin_medians": bin_summaries,
        "trials": len(trials),
        "reference_contract": (
            "independent noisy base reference; physical treatments alter A/B only"
        ),
        "frequency_scope": "ten bins [0.15,0.25), f_licensed capped at 0.25",
        "angle_capability": "NONE",
        "licensing_capability": "STRUCTURAL_NO_READ_AT_OR_ABOVE_0.25",
        "absolute_mtf50": "UNSUPPORTED",
    }


def ordinal_arms() -> dict[str, np.ndarray]:
    base = vertical_edge(BASE_SIGMA)
    return {
        "base": base,
        "identity": base.copy(),
        "blur": blur(base),
        "improvement": vertical_edge(IMPROVED_SIGMA),
        "sharpen": sharpen(base),
        **point_maps(base),
        "unlicensed": vertical_edge(0.60),
    }


def ordinal_value(image: np.ndarray, field: str) -> float:
    if field == "Q25":
        return float(q25(image))
    if field == "A20_25":
        return float(ordinal_shares(image)[3])
    raise KeyError(field)


def aggregate_ordinal() -> dict[str, object]:
    images = ordinal_arms()
    fields = {}
    for field in ("Q25", "A20_25"):
        arms = {
            name: ordinal_value(image, field)
            for name, image in images.items()
        }
        noise = []
        for seed in NOISE_SEEDS:
            rng = np.random.default_rng(seed)
            noise.append(ordinal_value(
                images["base"]
                + rng.normal(0.0, NOISE_SD, images["base"].shape),
                field,
            ))
        angles = {
            str(angle): ordinal_value(
                vertical_edge(BASE_SIGMA, angle), field
            )
            for angle in ANGLES
        }
        fields[field] = {
            "native_unit": (
                "dimensionless_licensed_rank_energy"
                if field == "Q25"
                else "dimensionless_six_band_normalised_rank_share"
            ),
            "arms": arms,
            "noise": noise,
            "angles": angles,
            "angle_output": "NONE",
            "unlicensed_output_status": (
                "NUMERIC_LICENSED_SCOPE_ONLY"
                if field == "Q25"
                else "NUMERIC_WITH_UNLICENSED_DENOMINATOR"
            ),
            "absolute_mtf50_status": "UNSUPPORTED",
        }

    tie_diagnostics = {
        name: {
            "unique_values": int(np.unique(image).size),
            "samples": int(image.size),
            "unique_fraction": float(np.unique(image).size / image.size),
        }
        for name, image in images.items()
        if name in ("base", "blur", "improvement", "sharpen")
    }
    return {
        "candidate": "V-HEADTOHEAD3 ordinal licensed Q25",
        "claim_fields": ["Q25"],
        "historical_fields": ["A20_25"],
        "fields": fields,
        "tie_diagnostics": tie_diagnostics,
        "frequency_scope": {
            "Q25": "numerator [0.20,0.25); denominator fixed spatial rank variance",
            "A20_25": "numerator [0.20,0.25); denominator six bands [0.02,0.40)",
        },
        "angle_capability": "NONE",
        "licensing_capability": {
            "Q25": "STRUCTURAL_NO_SPECTRAL_READ_AT_OR_ABOVE_0.25",
            "A20_25": "UNLICENSED_DENOMINATOR",
        },
        "absolute_mtf50": "UNSUPPORTED",
    }


def main() -> int:
    trials = [m1_trial(seed) for seed in NOISE_SEEDS]
    result = {
        "schema": 1,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "parameters": {
            "base_sigma": BASE_SIGMA,
            "blur_sigma": BLUR_SIGMA,
            "improved_sigma": IMPROVED_SIGMA,
            "usm_radius": USM_RADIUS,
            "usm_amount": USM_AMOUNT,
            "noise_sd": NOISE_SD,
            "noise_seeds": list(NOISE_SEEDS),
            "angle_deg": ANGLE_DEG,
            "angles_deg": list(ANGLES),
            "shape": [SIDE, SIDE],
        },
        "candidates": {
            "M1": aggregate_m1(trials),
            "V_ORDINAL": aggregate_ordinal(),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
