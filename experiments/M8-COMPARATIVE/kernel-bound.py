"""Bound negative-lobe interpolation excess without reading render pixels.

This is a synthetic kernel analysis, not a second M8 checker. Real-render
admission and measurement remain the responsibility of the unchanged
``checker.py`` copied from M8-overshoot.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Iterable


U16_MAX = 65535.0
GRID_INTERVALS = 1024


def keys_weights(t: float, a: float = -0.5) -> tuple[float, ...]:
    """Return the four Keys cubic-convolution weights for phase ``t``."""
    return (
        a * (t**3 - 2.0 * t**2 + t),
        (a + 2.0) * t**3 - (a + 3.0) * t**2 + 1.0,
        -(a + 2.0) * t**3 + (2.0 * a + 3.0) * t**2 - a * t,
        a * (-t**3 + t**2),
    )


def tensor_weights(
    tx: float,
    ty: float,
    a: float = -0.5,
) -> tuple[float, ...]:
    wx = keys_weights(tx, a)
    wy = keys_weights(ty, a)
    return tuple(x * y for y in wy for x in wx)


def negative_mass(weights: Iterable[float]) -> float:
    """Maximum signed hull excess for unit-range arbitrary support values."""
    return -sum(weight for weight in weights if weight < 0.0)


def signed_excess(
    weights: Iterable[float],
    values: Iterable[float],
) -> tuple[float, float, float]:
    weights = tuple(weights)
    values = tuple(values)
    value = sum(weight * sample for weight, sample in zip(weights, values))
    lo = min(values)
    hi = max(values)
    return value, min(0.0, value - lo), max(0.0, value - hi)


def quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def metric(value: float) -> dict[str, float]:
    return {
        "normalised_per_local_support_span": value,
        "uint16_dn_equivalent_per_full_scale_span": value * U16_MAX,
    }


def analyse() -> dict[str, object]:
    half_weights = keys_weights(0.5)
    third_weights = keys_weights(1.0 / 3.0)

    half_step_hi = signed_excess(half_weights, (0.0, 1.0, 1.0, 1.0))
    half_step_lo = signed_excess(half_weights, (1.0, 0.0, 0.0, 0.0))
    optimal_step_hi = signed_excess(
        third_weights,
        (0.0, 1.0, 1.0, 1.0),
    )
    optimal_step_lo = signed_excess(
        third_weights,
        (1.0, 0.0, 0.0, 0.0),
    )

    catmull_1d = keys_weights(0.5)
    positive_1d = tuple(1.0 if weight > 0.0 else 0.0 for weight in catmull_1d)
    negative_1d = tuple(1.0 - sample for sample in positive_1d)
    arbitrary_1d_hi = signed_excess(catmull_1d, positive_1d)
    arbitrary_1d_lo = signed_excess(catmull_1d, negative_1d)

    catmull_2d = tensor_weights(0.5, 0.5)
    positive_2d = tuple(1.0 if weight > 0.0 else 0.0 for weight in catmull_2d)
    negative_2d = tuple(1.0 - sample for sample in positive_2d)
    arbitrary_2d_hi = signed_excess(catmull_2d, positive_2d)
    arbitrary_2d_lo = signed_excess(catmull_2d, negative_2d)

    convex_2d = tensor_weights(0.5, 0.5, a=0.0)
    improved = signed_excess(convex_2d, positive_2d)
    convex_null = signed_excess(
        convex_2d,
        (
            0.0,
            0.2,
            0.8,
            1.0,
            0.3,
            0.1,
            0.9,
            0.7,
            0.4,
            0.6,
            0.5,
            0.2,
            1.0,
            0.0,
            0.25,
            0.75,
        ),
    )

    phases = [index / GRID_INTERVALS for index in range(GRID_INTERVALS + 1)]
    phase_masses_1d = [negative_mass(keys_weights(phase)) for phase in phases]
    phase_masses_2d = [
        nx + ny + 2.0 * nx * ny
        for nx in phase_masses_1d
        for ny in phase_masses_1d
    ]

    checks = {
        "green_convex_null_zero": convex_null[1] == 0.0
        and convex_null[2] == 0.0,
        "red_catmull_upper_plant_found": arbitrary_2d_hi[2] > 0.0,
        "red_catmull_lower_plant_found": arbitrary_2d_lo[1] < 0.0,
        "improvement_removing_negative_lobes_reaches_zero": (
            arbitrary_2d_hi[2] > 0.0
            and improved[1] == 0.0
            and improved[2] == 0.0
        ),
        "weights_sum_to_one": all(
            math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-12)
            for weights in (
                half_weights,
                third_weights,
                catmull_2d,
                convex_2d,
            )
        ),
        "catmull_sign_symmetric": math.isclose(
            arbitrary_2d_hi[2],
            -arbitrary_2d_lo[1],
            rel_tol=0.0,
            abs_tol=1e-12,
        ),
    }

    payload: dict[str, object] = {
        "scope": (
            "Synthetic Keys/Catmull-Rom negative-lobe analysis only; no real "
            "render pixels read and no foreign pipeline inferred."
        ),
        "normalisation": (
            "Every excess is divided by that interpolation support's local "
            "hi-lo span. DN values are full-scale uint16 equivalents."
        ),
        "commission": {
            "checks": checks,
            "passed": all(checks.values()),
            "convex_null_signed_excess": {
                "lower": convex_null[1],
                "upper": convex_null[2],
            },
            "catmull_2d_plant_signed_excess": {
                "lower": arbitrary_2d_lo[1],
                "upper": arbitrary_2d_hi[2],
            },
            "negative_lobe_removed_signed_excess": {
                "lower": improved[1],
                "upper": improved[2],
            },
        },
        "catmull_rom_a_minus_0_5": {
            "one_dimensional_hard_step_half_phase": {
                "lower": metric(-half_step_lo[1]),
                "upper": metric(half_step_hi[2]),
            },
            "one_dimensional_hard_step_phase_one_third": {
                "lower": metric(-optimal_step_lo[1]),
                "upper": metric(optimal_step_hi[2]),
            },
            "one_dimensional_arbitrary_support_global_bound": {
                "lower": metric(-arbitrary_1d_lo[1]),
                "upper": metric(arbitrary_1d_hi[2]),
            },
            "two_dimensional_separable_arbitrary_support_global_bound": {
                "lower": metric(-arbitrary_2d_lo[1]),
                "upper": metric(arbitrary_2d_hi[2]),
            },
            "phase_bound_distribution": {
                "grid_intervals_per_axis": GRID_INTERVALS,
                "one_dimensional": {
                    "median": metric(quantile(phase_masses_1d, 0.5)),
                    "p99": metric(quantile(phase_masses_1d, 0.99)),
                    "max": metric(max(phase_masses_1d)),
                },
                "two_dimensional_separable": {
                    "median": metric(quantile(phase_masses_2d, 0.5)),
                    "p99": metric(quantile(phase_masses_2d, 0.99)),
                    "max": metric(max(phase_masses_2d)),
                },
            },
        },
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = analyse()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if payload["commission"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
