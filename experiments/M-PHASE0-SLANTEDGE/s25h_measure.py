"""Black-box execution of every preregistered S25-hardening variant.

This adapter joins independent fixtures to candidate variants.  It contains
no expected score, pass threshold or verdict logic.
"""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import scipy

import s25h_fixtures as fixtures
import s25h_variants as variants


HERE = Path(__file__).resolve().parent
VARIANT_IDS = tuple(variants.VARIANT_SPECS)
SOURCES = (
    "s25h_fixtures.py",
    "s25h_variants.py",
    "vendor_m1.py",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_arm(
    variant_id: str,
    arm: str,
    calibration: dict[str, object],
    eligibility: dict[str, object],
) -> dict[str, object]:
    sites = fixtures.score_sites(arm)
    return variants.evaluate(
        variant_id,
        sites,
        calibration,
        eligibility,
        fixtures.nominal_ramp(),
        fixtures.observed_ramp(arm),
    )


def evaluate_variant(
    variant_id: str,
    calibration: dict[str, object],
    edge_eligibility: dict[str, object],
    flat_eligibility: dict[str, object],
) -> dict[str, object]:
    flat_controls = {
        "base": variants.evaluate(
            variant_id,
            fixtures.flat_sites(sharpened=False),
            calibration,
            flat_eligibility,
            fixtures.nominal_ramp(),
            fixtures.observed_ramp("base"),
        ),
        "sharpen": variants.evaluate(
            variant_id,
            fixtures.flat_sites(sharpened=True),
            calibration,
            flat_eligibility,
            fixtures.nominal_ramp(),
            fixtures.observed_ramp("base"),
        ),
    }

    arms = {
        arm: evaluate_arm(
            variant_id,
            arm,
            calibration,
            edge_eligibility,
        )
        for arm in (
            "base",
            "identity",
            "blur",
            "improvement",
            "sharpen",
            "affine",
            "gamma3",
            "logistic",
        )
    }
    noise = []
    for noise_index, seed in enumerate(fixtures.NOISE_SEEDS):
        record = variants.evaluate(
            variant_id,
            fixtures.score_sites(
                "noise",
                noise_index=noise_index,
            ),
            calibration,
            edge_eligibility,
            fixtures.nominal_ramp(),
            fixtures.observed_ramp("noise"),
        )
        noise.append({"seed": seed, "measurement": record})

    angles = []
    for angle in fixtures.ANGLES:
        record = variants.evaluate(
            variant_id,
            fixtures.score_sites("angle", angle_deg=angle),
            calibration,
            edge_eligibility,
            fixtures.nominal_ramp(),
            fixtures.observed_ramp("angle"),
        )
        angles.append({"plant_deg": angle, "measurement": record})

    return {
        "variant_id": variant_id,
        "spec": variants.VARIANT_SPECS[variant_id],
        "flat_controls": flat_controls,
        "arms": arms,
        "noise": noise,
        "angles": angles,
        "frequency_scope": "[0.20,0.25) cycles/native-pixel only",
        "absolute_mtf50_status": "UNSUPPORTED_COMPARATIVE_ONLY",
    }


def main() -> int:
    execution_order = []

    execution_order.append("noise_calibration")
    calibration = variants.noise_calibration(
        fixtures.calibration_pairs()
    )

    execution_order.extend([
        "eligibility_edge",
        "eligibility_equal",
        "eligibility_flat",
        "eligibility_point_only",
    ])
    edge_eligibility = variants.eligibility_from_sites(
        fixtures.eligibility_sites("edge"),
        calibration,
    )
    equal_eligibility = variants.eligibility_from_sites(
        fixtures.eligibility_sites("equal"),
        calibration,
    )
    flat_eligibility = variants.eligibility_from_sites(
        fixtures.eligibility_sites("flat"),
        calibration,
    )
    focused, defocused = fixtures.heterogeneous_power_control()
    point_only_eligibility = variants.eligibility_from_power_rows(
        focused,
        defocused,
    )

    results = {}
    for variant_id in VARIANT_IDS:
        execution_order.append(f"{variant_id}:flat_controls")
        execution_order.append(f"{variant_id}:score_battery")
        results[variant_id] = evaluate_variant(
            variant_id,
            calibration,
            edge_eligibility,
            flat_eligibility,
        )

    output = {
        "schema": 1,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "parameters": {
            "side": fixtures.SIDE,
            "site_count": fixtures.SITE_COUNT,
            "calibration_pairs": fixtures.CALIBRATION_PAIRS,
            "base_sigma": fixtures.BASE_SIGMA,
            "blur_sigma": fixtures.BLUR_SIGMA,
            "improved_sigma": fixtures.IMPROVED_SIGMA,
            "usm_radius": fixtures.USM_RADIUS,
            "usm_amount": fixtures.USM_AMOUNT,
            "noise_sd": fixtures.NOISE_SD,
            "noise_seeds": list(fixtures.NOISE_SEEDS),
            "angles": list(fixtures.ANGLES),
        },
        "execution_order": execution_order,
        "controls_preceded_score": (
            execution_order.index("eligibility_point_only")
            < execution_order.index("C0_NATIVE_MIN:score_battery")
        ),
        "calibration": calibration,
        "eligibility_controls": {
            "edge": edge_eligibility,
            "equal": equal_eligibility,
            "flat": flat_eligibility,
            "point_only": point_only_eligibility,
        },
        "implementation_sha256": {
            name: sha256(HERE / name)
            for name in SOURCES
        },
        "variant_ids": list(VARIANT_IDS),
        "variants": results,
    }
    print(json.dumps(
        output,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

