from __future__ import annotations

import json
from pathlib import Path


RESULT = Path(__file__).with_name("commission.json")


def main() -> int:
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    try:
        data = json.loads(RESULT.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FAIL could not read commission result: {exc}")
        return 1

    check(data.get("population") == 20_000, "canonical population is not 20,000")
    probe = data.get("probe_nontriviality", {})
    check(
        probe.get("residual_nonzero_count") == 20_000,
        "probe does not have 20,000 nonzero residuals",
    )
    check(
        isinstance(probe.get("residual_sd_steps"), (int, float))
        and probe["residual_sd_steps"] > 0.0,
        "probe residuals are degenerate",
    )
    check(
        isinstance(probe.get("candidate_sigma_p05_steps"), (int, float))
        and isinstance(probe.get("candidate_sigma_p95_steps"), (int, float))
        and 0.0
        < probe["candidate_sigma_p05_steps"]
        < probe["candidate_sigma_p95_steps"],
        "probe candidate uncertainty is degenerate",
    )

    legacy = data.get("legacy_zero_infinity_random", {})
    check(
        legacy.get("all_results_identical") is True,
        "legacy zero/infinity/random decisions moved",
    )
    hashes = legacy.get("canonical_sha256", {})
    check(
        set(hashes) == {"reported", "zero", "infinity", "random"},
        "legacy substitution arm set moved",
    )
    check(len(set(hashes.values())) == 1, "legacy substitution hashes differ")
    legacy_value = legacy.get("canonical_result", {}).get("value", {})
    check(legacy.get("canonical_result", {}).get("pass") is True, "legacy fixture did not pass")
    check(
        len(legacy_value.get("components", {})) == 7
        and all(legacy_value.get("components", {}).values()),
        "legacy fixture did not pass all seven value bars",
    )

    arms = data.get("uncertainty_arms", {})
    check(
        set(arms)
        == {
            "reported",
            "zero",
            "infinity",
            "random",
            "sigma_x1p25",
            "depth_residual_x1p50",
            "sigma_x0p50",
        },
        "uncertainty arm set moved",
    )
    check(arms.get("reported", {}).get("pass") is True, "calibrated input did not pass")
    for name, arm in arms.items():
        uncertainty = arm.get("uncertainty", {})
        check(
            uncertainty.get("population") == 20_000,
            f"{name} population is not the canonical 20,000",
        )
        check(
            uncertainty.get("valid_target_pixels") == 20_000,
            f"{name} valid target population moved",
        )
        expected_calibration = 0 if name == "infinity" else 20_000
        check(
            uncertainty.get("calibration_pixels") == expected_calibration,
            f"{name} calibration population moved",
        )
    for name in ("zero", "infinity", "random"):
        check(
            arms.get(name, {}).get("pass") is False,
            f"{name} substitution did not fail",
        )
        check(
            arms.get(name, {}).get("uncertainty")
            != arms.get("reported", {}).get("uncertainty"),
            f"{name} substitution did not move uncertainty quantities",
        )

    null = data.get("movable_null", {})
    check(null.get("metrics_moved") is True, "null did not move under 1.25x sigma")
    check(arms.get(null.get("before_arm"), {}).get("pass") is True, "null baseline did not pass")
    check(arms.get(null.get("after_arm"), {}).get("pass") is False, "null disturbance did not fail")

    degradation = data.get("planted_degradation", {})
    deg_before = (
        arms.get(degradation.get("before_arm"), {})
        .get("uncertainty", {})
        .get("metrics", {})
        .get("mean_gaussian_crps_steps")
    )
    deg_after = (
        arms.get(degradation.get("after_arm"), {})
        .get("uncertainty", {})
        .get("metrics", {})
        .get("mean_gaussian_crps_steps")
    )
    check(
        isinstance(deg_before, (int, float))
        and isinstance(deg_after, (int, float))
        and deg_after > deg_before,
        "planted degradation did not increase CRPS",
    )
    check(
        arms.get(degradation.get("after_arm"), {}).get("pass") is False,
        "planted degradation did not fail",
    )
    check(
        arms.get(degradation.get("after_arm"), {}).get("value", {}).get("pass")
        is True,
        "planted degradation unexpectedly failed an old value bar",
    )

    improvement = data.get("planted_improvement", {})
    imp_before = (
        arms.get(improvement.get("before_arm"), {})
        .get("uncertainty", {})
        .get("metrics", {})
        .get("mean_gaussian_crps_steps")
    )
    imp_after = (
        arms.get(improvement.get("after_arm"), {})
        .get("uncertainty", {})
        .get("metrics", {})
        .get("mean_gaussian_crps_steps")
    )
    check(
        isinstance(imp_before, (int, float))
        and isinstance(imp_after, (int, float))
        and imp_after < imp_before,
        "planted improvement did not reduce CRPS",
    )
    check(
        arms.get(improvement.get("before_arm"), {}).get("pass") is False,
        "pre-improvement input unexpectedly passed",
    )
    check(
        arms.get(improvement.get("after_arm"), {}).get("pass") is True,
        "planted improvement did not pass",
    )

    relation = data.get("bar_relation", {})
    check(relation.get("classification") == "HARDER", "bar was not classified harder")
    check(relation.get("existing_value_bars_retained") == 7, "value bar count moved")
    check(relation.get("new_uncertainty_vetoes") == 5, "uncertainty veto count moved")

    preflight = data.get("current_product_preflight", {})
    check(preflight.get("advertised_numeric_planes") == 0, "current product count moved")
    check(preflight.get("required_numeric_planes") == 2, "required product count moved")
    check(preflight.get("pass") is False, "absent current product passed preflight")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print("PASS M163 repaired M10 uncertainty instrument")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
