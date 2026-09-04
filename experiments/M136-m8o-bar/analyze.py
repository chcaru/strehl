from __future__ import annotations

import json
import hashlib
from decimal import Decimal, getcontext
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
M8 = ROOT / "experiments" / "M8-overshoot"
STAGE = M8 / "out" / "stage-attribution"
U16_MAX = 65535.0

STATES = {
    "one-frame-bilinear": STAGE / "bilinear-scale-identity",
    "bilinear-et1s": STAGE / "bilinear-scale-flat-et1s",
    "bilinear-et2.5s": STAGE / "bilinear-scale-flat-et2.5s",
    "bilinear-et6s": STAGE / "bilinear-scale-flat-et6s",
    "catmull-et1s": M8 / "out" / "flat-et1s-state",
    "catmull-et2.5s": M8 / "out" / "flat-et2.5s-state",
    "catmull-et6s": M8 / "out" / "flat-et6s-state",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def quantiles(values: np.ndarray) -> dict[str, float]:
    if not len(values):
        return {}
    return {
        str(q): float(np.quantile(values, q))
        for q in (0.0, 0.5, 0.9, 0.99, 0.999, 1.0)
    }


def aggregate_states(summaries: dict, names: tuple[str, ...]) -> dict:
    aggregate = {
        key: sum(summaries[name][key] for name in names)
        for key in (
            "denominator",
            "violations",
            "nonrail",
            "full_rail_below_hull",
            "projected_hull_violations",
            "projected_plus_internal_quant_violations",
        )
    }
    aggregate["by_channel"] = {
        channel: {
            **{
                key: sum(
                    summaries[name]["by_channel"][channel][key] for name in names
                )
                for key in (
                    "count",
                    "lower",
                    "upper",
                    "rail",
                    "beyond_internal_bound",
                    "nonrail_beyond_internal_bound",
                    "projected_hull_violations",
                    "projected_plus_internal_quant_violations",
                )
            },
            "internal_half_step_lsb_min": min(
                summaries[name]["by_channel"][channel]["internal_half_step_lsb"]
                for name in names
            ),
            "internal_half_step_lsb_max": max(
                summaries[name]["by_channel"][channel]["internal_half_step_lsb"]
                for name in names
            ),
        }
        for channel in ("R", "G", "B")
    }
    return aggregate


def commission_projected_hull() -> dict:
    tolerance = 0.5 / U16_MAX

    def violates(encoded: int, lo: float, hi: float) -> bool:
        value = encoded / U16_MAX
        projected_lo = min(max(lo, 0.0), 1.0)
        projected_hi = min(max(hi, 0.0), 1.0)
        return (
            value < projected_lo - tolerance
            or value > projected_hi + tolerance
        )

    cases = {
        "in_range_copy_green": (round(0.4 * U16_MAX), 0.4, 0.4, False),
        "in_range_convex_green": (round(0.5 * U16_MAX), 0.2, 0.8, False),
        "in_range_high_plant_red": (round(0.9 * U16_MAX), 0.2, 0.8, True),
        "in_range_low_plant_red": (round(0.1 * U16_MAX), 0.2, 0.8, True),
        "unrepresentable_high_at_rail_green": (65535, 1.1, 1.2, False),
        "unrepresentable_high_off_rail_red": (65000, 1.1, 1.2, True),
        "unrepresentable_low_at_rail_green": (0, -0.2, -0.1, False),
        "unrepresentable_low_off_rail_red": (500, -0.2, -0.1, True),
    }
    results = {}
    for name, (encoded, lo, hi, expected) in cases.items():
        observed = violates(encoded, lo, hi)
        results[name] = {
            "encoded": encoded,
            "lo": lo,
            "hi": hi,
            "expected_violation": expected,
            "observed_violation": observed,
            "passed": observed == expected,
        }
    return {
        "expected_green": sum(not case[3] for case in cases.values()),
        "observed_green": sum(
            not result["observed_violation"] for result in results.values()
        ),
        "expected_red": sum(case[3] for case in cases.values()),
        "observed_red": sum(
            result["observed_violation"] for result in results.values()
        ),
        "cases": results,
        "passed": all(case["passed"] for case in results.values()),
    }


def summarize_state(path: Path) -> dict:
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    result = json.loads((path / "m8-o.json").read_text(encoding="utf-8"))
    rows = np.load(path / "m8-o-violations.npy", mmap_mode="r")

    encoded = rows["encoded"].astype(np.float64)
    value = encoded / U16_MAX
    lo = rows["lo"].astype(np.float64)
    hi = rows["hi"].astype(np.float64)
    tolerance = rows["tolerance"].astype(np.float64)
    direction = rows["direction"]
    channel = rows["channel"].astype(np.intp)

    lower_gap = lo - tolerance - value
    upper_gap = value - hi - tolerance
    beyond_tolerance_lsb = np.where(direction < 0, lower_gap, upper_gap) * U16_MAX
    signed_excess_lsb = rows["signed_excess"].astype(np.float64) * U16_MAX

    output_gains = np.asarray(meta["output_gains"], dtype=np.float64)
    value_range = float(meta["range"])
    internal_half_step = 0.5 * output_gains[channel] / value_range
    internal_half_step_lsb = internal_half_step * U16_MAX

    projected_lo = np.clip(lo, 0.0, 1.0)
    projected_hi = np.clip(hi, 0.0, 1.0)
    projected_lower = value < projected_lo - tolerance
    projected_upper = value > projected_hi + tolerance
    projected_violation = projected_lower | projected_upper

    full_tolerance = tolerance + internal_half_step
    quantized_lower = value < projected_lo - full_tolerance
    quantized_upper = value > projected_hi + full_tolerance
    quantized_violation = quantized_lower | quantized_upper
    nonrail = (encoded != 0) & (encoded != U16_MAX)

    by_channel = {}
    for c, name in enumerate(("R", "G", "B")):
        m = channel == c
        by_channel[name] = {
            "count": int(np.count_nonzero(m)),
            "lower": int(np.count_nonzero(m & (direction < 0))),
            "upper": int(np.count_nonzero(m & (direction > 0))),
            "rail": int(np.count_nonzero(m & ((encoded == 0) | (encoded == U16_MAX)))),
            "max_abs_signed_excess_lsb": (
                float(np.max(np.abs(signed_excess_lsb[m]))) if np.any(m) else 0.0
            ),
            "max_beyond_tolerance_lsb": (
                float(np.max(beyond_tolerance_lsb[m])) if np.any(m) else 0.0
            ),
            "internal_half_step_lsb": float(
                0.5 * output_gains[c] / value_range * U16_MAX
            ),
            "beyond_internal_bound": int(
                np.count_nonzero(m & (beyond_tolerance_lsb > internal_half_step_lsb + 1e-3))
            ),
            "nonrail_beyond_internal_bound": int(
                np.count_nonzero(
                    m
                    & nonrail
                    & (beyond_tolerance_lsb > internal_half_step_lsb + 1e-3)
                )
            ),
            "projected_hull_violations": int(np.count_nonzero(m & projected_violation)),
            "projected_plus_internal_quant_violations": int(
                np.count_nonzero(m & quantized_violation)
            ),
        }

    full_rail_below = (
        (encoded == U16_MAX) & (direction < 0) & (lo > 1.0 + tolerance)
    )
    zero_rail_above = (encoded == 0) & (direction > 0) & (hi < -tolerance)
    return {
        "state": str(path),
        "denominator": int(result["denominator"]),
        "violations": int(len(rows)),
        "lower": int(np.count_nonzero(direction < 0)),
        "upper": int(np.count_nonzero(direction > 0)),
        "nonrail": int(np.count_nonzero(nonrail)),
        "full_rail_below_hull": int(np.count_nonzero(full_rail_below)),
        "zero_rail_above_hull": int(np.count_nonzero(zero_rail_above)),
        "projected_hull_violations": int(np.count_nonzero(projected_violation)),
        "projected_plus_internal_quant_violations": int(
            np.count_nonzero(quantized_violation)
        ),
        "beyond_tolerance_lsb_quantiles": quantiles(beyond_tolerance_lsb),
        "abs_signed_excess_lsb_quantiles": quantiles(np.abs(signed_excess_lsb)),
        "hull_width_lsb_quantiles": quantiles((hi - lo) * U16_MAX),
        "by_channel": by_channel,
    }


def main() -> None:
    evidence = {
        "stage_attribution": M8 / "stage-attribution.json",
        "checker": M8 / "checker.py",
        "rail_classifier": M8 / "stage_attribution.py",
        "snapshot_align": M8
        / "out"
        / "source-snapshot"
        / "crates"
        / "strehl-cli"
        / "src"
        / "align_cmd.rs",
        "snapshot_merge": M8
        / "out"
        / "source-snapshot"
        / "crates"
        / "strehl-cli"
        / "src"
        / "merge_cmd.rs",
        "snapshot_pyramid": M8
        / "out"
        / "source-snapshot"
        / "crates"
        / "strehl-core"
        / "src"
        / "pyramid.rs",
        "scorecard": ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md",
    }
    for state_name, state_path in STATES.items():
        evidence[f"{state_name}_meta"] = state_path / "meta.json"
        evidence[f"{state_name}_m8_o"] = state_path / "m8-o.json"
        evidence[f"{state_name}_violations"] = state_path / "m8-o-violations.npy"
    before_hashes = {name: sha256(path) for name, path in evidence.items()}
    summaries = {name: summarize_state(path) for name, path in STATES.items()}
    bilinear_names = ("bilinear-et1s", "bilinear-et2.5s", "bilinear-et6s")
    catmull_names = ("catmull-et1s", "catmull-et2.5s", "catmull-et6s")
    bilinear_aggregate = aggregate_states(summaries, bilinear_names)
    catmull_aggregate = aggregate_states(summaries, catmull_names)
    commissioning = commission_projected_hull()

    assert bilinear_aggregate["violations"] == 980_097
    assert bilinear_aggregate["full_rail_below_hull"] == 977_684
    assert bilinear_aggregate["nonrail"] == 2_413
    assert bilinear_aggregate["projected_hull_violations"] == 2_413
    assert bilinear_aggregate["projected_plus_internal_quant_violations"] == 0
    assert catmull_aggregate["violations"] == 983_648
    assert catmull_aggregate["full_rail_below_hull"] == 938_062
    assert catmull_aggregate["projected_hull_violations"] == 45_586
    assert catmull_aggregate["projected_plus_internal_quant_violations"] == 31_148
    assert summaries["one-frame-bilinear"]["violations"] == 52_570
    assert (
        summaries["one-frame-bilinear"]["projected_plus_internal_quant_violations"]
        == 0
    )
    assert commissioning["passed"]

    after_hashes = {name: sha256(path) for name, path in evidence.items()}
    assert before_hashes == after_hashes
    getcontext().prec = 50
    numerator = Decimal(bilinear_aggregate["nonrail"])
    denominator = Decimal(bilinear_aggregate["denominator"])
    payload = {
        "protocol": "M136 deterministic analysis v1",
        "source": str(M8 / "stage-attribution.json"),
        "source_hashes_before_after": {
            name: {
                "path": str(evidence[name]),
                "before": before_hashes[name],
                "after": after_hashes[name],
                "unchanged": before_hashes[name] == after_hashes[name],
            }
            for name in evidence
        },
        "states": summaries,
        "bilinear_aggregate": bilinear_aggregate,
        "catmull_aggregate": catmull_aggregate,
        "rates": {
            "post_projection_residue_exact": (
                f"{bilinear_aggregate['nonrail']}/{bilinear_aggregate['denominator']}"
            ),
            "post_projection_residue_fraction_decimal": str(numerator / denominator),
            "post_projection_residue_percent_decimal": str(
                Decimal(100) * numerator / denominator
            ),
            "post_projection_residue_fraction": (
                bilinear_aggregate["nonrail"] / bilinear_aggregate["denominator"]
            ),
            "post_projection_residue_percent": (
                100.0
                * bilinear_aggregate["nonrail"]
                / bilinear_aggregate["denominator"]
            ),
        },
        "quantisation_model": {
            "checker_existing_tolerance": "mapped tau_R + 0.5/65535",
            "omitted_internal_half_step": (
                "0.5 * output_gain[channel] / sensor_range"
            ),
            "comparison": (
                "project lo/hi through clamp([0,1]), then add the omitted "
                "internal half-step to the existing tolerance"
            ),
        },
        "proposed_instrument_commissioning": commissioning,
    }
    output = Path(__file__).resolve().parent / "analysis.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
