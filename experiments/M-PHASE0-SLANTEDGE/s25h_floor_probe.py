"""Actual zero-floor mutant used by the independent S25 checker.

This adapter supplies a ten-zero p95 vector to every floor-aware variant.  It
contains no acceptance threshold or expected status.
"""

from __future__ import annotations

import json

import s25h_fixtures as fixtures
import s25h_variants as variants


FLOOR_VARIANTS = (
    "V1_FLOOR_ELIG_MIN",
    "V2_GES_OLS",
    "V3_RAMP_GES_OLS",
    "V4_RAMP_GES_OLS_ANGLE",
    "V5_RAMP_GES_TS_ANGLE",
)


def main() -> int:
    calibration = variants.noise_calibration(
        fixtures.calibration_pairs()
    )
    eligibility = variants.eligibility_from_sites(
        fixtures.eligibility_sites("edge"),
        calibration,
    )
    mutated = {
        **calibration,
        "p95_higher": [0.0] * 10,
    }
    sites = fixtures.score_sites("base")
    nominal = fixtures.nominal_ramp()
    observed = fixtures.observed_ramp("base")
    results = {
        variant_id: variants.evaluate(
            variant_id,
            sites,
            mutated,
            eligibility,
            nominal,
            observed,
        )
        for variant_id in FLOOR_VARIANTS
    }
    print(json.dumps({
        "schema": 1,
        "mutant": "ZERO_P95_HIGHER",
        "variant_ids": list(FLOOR_VARIANTS),
        "variants": results,
    }, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

