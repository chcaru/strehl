from __future__ import annotations

import json
from pathlib import Path

import checker


LANE = Path(__file__).resolve().parent
RESULTS = LANE / "commission-results.json"
ALLOWED_REAL_PATHS = {
    str(
        Path(
            r"D:\personal\macro\requests\misc-diagnostic"
            r"\high-res-calibration-slide-cpl\tilted-sw10-cpl"
        )
    ),
    str(
        Path(r"D:\personal\macro\requests\30-calibration-grid")
        / "calibration-grid-1-sw4-cpl"
    ),
    str(
        Path(r"D:\personal\macro\requests\30-calibration-grid")
        / "calibration-grid-2-sw10-cpl"
    ),
}


def close(actual: float, expected: float, tolerance: float = 1.0e-12) -> None:
    if abs(actual - expected) > tolerance:
        raise AssertionError(f"{actual} != {expected} within {tolerance}")


def main() -> int:
    result = json.loads(RESULTS.read_text(encoding="ascii"))
    if result["definitions_sha256"] != checker.DEFINITIONS_SHA256:
        raise AssertionError("result uses a different frozen definition hash")
    if result["all_commissioned"]:
        raise AssertionError("real-input commissioning unexpectedly claims success")

    expected_red = {
        "capture_exact_development_arms_at_effective_minimum",
        "real_at_least_50_eligible",
    }
    actual_red = {name for name, passed in result["checks"].items() if not passed}
    if actual_red != expected_red:
        raise AssertionError(
            f"commissioning red set changed: expected {sorted(expected_red)}, "
            f"found {sorted(actual_red)}"
        )

    synthetic = result["synthetic"]
    close(synthetic["healthy"]["coverage"], 1.0)
    close(synthetic["defect"]["coverage"], 0.95)
    close(
        synthetic["response"]["coverage_drop_percentage_points"],
        5.0,
    )
    close(synthetic["healthy"]["run"]["fraction"], 0.0)
    close(synthetic["defect"]["run"]["fraction"], 1.0 / 21.0)
    close(synthetic["crop_plant"]["retained_fov"], 0.98)

    real = result["real"]
    if real["manifest"]["eligible_count"] != 4:
        raise AssertionError("development tilted-sw10 eligibility changed")
    close(real["healthy"]["coverage"], 1.0)
    close(real["defect"]["coverage"], 0.75)
    close(real["response"]["coverage_drop_percentage_points"], 25.0)
    close(real["healthy"]["run"]["fraction"], 0.0)
    close(real["defect"]["run"]["fraction"], 0.25)

    sufficiency = result["capture_sufficiency"]
    if sufficiency["planned_capture_demonstrated_sufficient"]:
        raise AssertionError("capture was promoted without an exact rehearsal")
    if sufficiency["minimum_all_success_sites_for_wilson_98"] != 133:
        raise AssertionError("effective Wilson minimum changed")
    if sufficiency["burned_grid_sw4_exact_55"]["eligible_count"] != 0:
        raise AssertionError("burned-grid sw4 eligibility changed")
    if sufficiency["burned_grid_sw10_exact_27"]["eligible_count"] != 0:
        raise AssertionError("burned-grid sw10 eligibility changed")
    if (
        sufficiency["development_tilted_sw10_best_27"][
            "bootstrap_eligible_count"
        ]
        != 13
    ):
        raise AssertionError("best 27-frame development eligibility changed")

    paths = {
        inventory["path"]
        for inventory in result["development_inventories"].values()
    }
    if paths != ALLOWED_REAL_PATHS:
        raise AssertionError(
            f"unexpected real input paths: {sorted(paths - ALLOWED_REAL_PATHS)}"
        )

    pooled = result["synthetic_pooled_wilson"]["pooled"]
    if pooled["eligible_physical_sites"] != 640 or not pooled["rate_pass"]:
        raise AssertionError("pooled Wilson control failed")

    print(
        "verified expected partial commissioning: "
        "synthetic drop=5.000000pp real drop=25.000000pp "
        "eligible exact sw4/sw10=0/0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
