"""Outcome measurement for the frozen V-HEADTOHEAD3 sharpening follow-up.

Only 0.20--0.25 cyc/native-px is measured.  The preregistered source model
failed before this script was run, so sigma=1/amount=1 is reported solely as
the independently commissioned *nominal sensitivity arm*, never as a fitted
or comparable Lightroom model.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Sequence

import numpy as np

import sharpening_core as sc
import sharpening_frozen as frozen
from ordinal import (
    fit_geometry,
    green_memmap,
    midrank_field,
    phase_correction,
    resized_rank,
)


NOMINAL_SIGMA = 1.0
NOMINAL_AMOUNT = 1.0


def render_pair(
    pmax0: np.ndarray,
    pmax40: np.ndarray,
    centre: Sequence[int],
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, float]]:
    """Locally register PMax40 to PMax0 without resampling measured pixels."""
    return sc.registered_pair(pmax0, pmax40, centre, max_shift=32)


def strehl_pair(
    strehl: np.ndarray,
    comparator: np.ndarray,
    comparator_centre: Sequence[int],
    geometry: dict,
) -> tuple[np.ndarray, np.ndarray, tuple[int, int, float]]:
    """Map a source-fixed comparator site to strehl and refine translation."""
    scale = float(geometry["scale"])
    gy, gx = map(float, geometry["global_correction"])
    cy, cx = map(float, comparator_centre)
    sy = scale * cy + gy
    sx = scale * cx + gx
    side_c = int(round(sc.SIDE / scale))
    s = sc.crop_centered(strehl, sy, sx, sc.SIDE)
    c0 = sc.crop_centered(comparator, cy, cx, side_c)
    if s is None or c0 is None:
        raise ValueError(f"mapped crop out of bounds at {comparator_centre}")
    corr = phase_correction(midrank_field(s), resized_rank(c0, s.shape), max_shift=32)
    c = sc.crop_centered(
        comparator,
        cy - corr[0] / scale,
        cx - corr[1] / scale,
        side_c,
    )
    if c is None:
        raise ValueError(f"corrected comparator crop out of bounds: {corr}")
    return s, c, corr


def closure_interval(d_out: Sequence[float], d_pred: Sequence[float]) -> dict:
    a = np.asarray(d_out, np.float64)
    b = np.asarray(d_pred, np.float64)
    if a.shape != b.shape or len(a) < 6:
        raise ValueError("closure needs paired independent sites")
    point_den = float(np.mean(a))
    point = float(np.mean(b) / point_den) if point_den != 0.0 else math.nan
    rng = np.random.default_rng(sc.SEED)
    draws = np.empty(10_000, np.float64)
    for i in range(len(draws)):
        ix = rng.integers(0, len(a), len(a))
        den = float(np.mean(a[ix]))
        draws[i] = float(np.mean(b[ix]) / den) if den != 0.0 else math.nan
    valid = draws[np.isfinite(draws)]
    lo, hi = np.quantile(valid, [0.025, 0.975])
    return {
        "n": int(len(a)),
        "point": point,
        "ci_low": float(lo),
        "ci_high": float(hi),
        "valid_draws": int(len(valid)),
    }


def log_ratio_summary(rows: Sequence[dict], numerator: str, denominator: str) -> dict:
    return sc.bootstrap_log_ratio(
        [math.log(float(r[numerator]) / float(r[denominator])) for r in rows]
    )


def main() -> int:
    if frozen.MODEL_GREEN:
        raise RuntimeError("this script documents the frozen failed-model branch")
    pmax0 = sc.green(sc.PMAX_0)
    pmax40 = sc.green(sc.PMAX_40)
    strehl = green_memmap(sc.STREHL)
    geometry0 = fit_geometry(sc.STREHL, sc.PMAX_0)
    geometry40 = fit_geometry(sc.STREHL, sc.PMAX_40)

    # Priority 1: forward presentation transfer on source-fixed detail sites.
    detail_rows: list[dict] = []
    for y, x in frozen.DETAIL_0 + frozen.DETAIL_1:
        c0, c40, p_corr = render_pair(pmax0, pmax40, (y, x))
        nominal0 = sc.usm(c0, NOMINAL_SIGMA, NOMINAL_AMOUNT)
        s, c40s, s_corr = strehl_pair(strehl, pmax40, (y, x), geometry40)
        nominal_s = sc.usm(s, NOMINAL_SIGMA, NOMINAL_AMOUNT)
        scale40 = float(geometry40["scale"])
        detail_rows.append(
            {
                "centre": [y, x],
                "pmax_pair_correction": list(p_corr),
                "strehl_correction": list(s_corr),
                "q_pmax0": sc.q25(c0),
                "q_pmax40": sc.q25(c40),
                "q_nominal_pmax0": sc.q25(nominal0),
                "q_strehl": sc.q25(s),
                "q_pmax40_for_strehl": sc.q25(c40s, band_scale=scale40),
                "q_nominal_strehl": sc.q25(nominal_s),
                "rail_pmax0": sc.rail_fraction(c0),
                "rail_pmax40": sc.rail_fraction(c40),
                "rail_strehl": sc.rail_fraction(s),
            }
        )

    d_out = [
        math.log(r["q_pmax40"] / r["q_pmax0"])
        for r in detail_rows
    ]
    d_pred = [
        math.log(r["q_nominal_pmax0"] / r["q_pmax0"])
        for r in detail_rows
    ]
    output_advantage = log_ratio_summary(detail_rows, "q_pmax40", "q_pmax0")
    nominal_gain = log_ratio_summary(detail_rows, "q_nominal_pmax0", "q_pmax0")
    nominal_forward = log_ratio_summary(
        detail_rows, "q_nominal_pmax0", "q_pmax40"
    )
    original_strehl = log_ratio_summary(
        detail_rows, "q_strehl", "q_pmax40_for_strehl"
    )
    nominal_strehl = log_ratio_summary(
        detail_rows, "q_nominal_strehl", "q_pmax40_for_strehl"
    )

    print(
        "PRIORITY1_JSON="
        + json.dumps(
            {
                "model_green": frozen.MODEL_GREEN,
                "model_failures": frozen.MODEL_FAILURES,
                "arm": {
                    "status": "NOMINAL_SENSITIVITY_NOT_COMPARABLE_MODEL",
                    "sigma": NOMINAL_SIGMA,
                    "amount": NOMINAL_AMOUNT,
                },
                "pmax40_over_pmax0": output_advantage,
                "nominal_usm_gain_pmax0": nominal_gain,
                "closure": closure_interval(d_out, d_pred),
                "nominal_usm_pmax0_over_pmax40": nominal_forward,
                "strehl_over_pmax40": original_strehl,
                "nominal_usm_strehl_over_pmax40": nominal_strehl,
                "unlicensed": sc.UNLICENSED,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    # Priority 2/3: source-fixed flat placebo and corroborative rank hull.
    flat_rows: list[dict] = []
    for y, x in frozen.FLAT_0 + frozen.FLAT_1:
        c0, c40, corr = render_pair(pmax0, pmax40, (y, x))
        hull, forward, reverse = sc.rank_hull_delta(c0, c40)
        flat_rows.append(
            {
                "centre": [y, x],
                "correction": list(corr),
                "q_pmax0": sc.q25(c0),
                "q_pmax40": sc.q25(c40),
                "hull": hull,
                "hull_forward": forward,
                "hull_reverse": reverse,
                "rail_pmax0": sc.rail_fraction(c0),
                "rail_pmax40": sc.rail_fraction(c40),
            }
        )
    flat_power = log_ratio_summary(flat_rows, "q_pmax40", "q_pmax0")
    hull = sc.bootstrap_mean([r["hull"] for r in flat_rows])

    by_centre = {
        tuple(r["centre"]): math.log(r["q_pmax40"] / r["q_pmax0"])
        for r in detail_rows
    }
    detail_logs = list(by_centre.values())
    spatial = {
        "leave_one_site_same_direction": sc.leave_one_out_same_direction(detail_logs),
        "quadrant_mean_log_ratios": sc.quadrant_signs(by_centre),
        "all_quadrants_positive": all(v > 0.0 for v in sc.quadrant_signs(by_centre)),
    }
    diagnostics = {
        "pmax_pair_shift_range": {
            "dy": [
                int(min(r["pmax_pair_correction"][0] for r in detail_rows)),
                int(max(r["pmax_pair_correction"][0] for r in detail_rows)),
            ],
            "dx": [
                int(min(r["pmax_pair_correction"][1] for r in detail_rows)),
                int(max(r["pmax_pair_correction"][1] for r in detail_rows)),
            ],
        },
        "max_rail_fraction": float(
            max(
                max(r["rail_pmax0"], r["rail_pmax40"])
                for r in detail_rows + flat_rows
            )
        ),
        "geometry0": geometry0,
        "geometry40": geometry40,
    }
    print(
        "FLAT_HULL_JSON="
        + json.dumps(
            {
                "flat_label": "INPUT_FIXED_FLAT_PLACEBO_NOT_M4",
                "flat_power": flat_power,
                "hull_label": "LOCAL_RANK_ENVELOPE_PROXY_NOT_M8",
                "hull": hull,
                "spatial": spatial,
                "diagnostics": diagnostics,
                "unlicensed": sc.UNLICENSED,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )

    # The preregistered fitted-model gate failed; nominal sensitivity cannot
    # promote that branch to REPRODUCES or to either causal verdict.
    flags = {
        "advantage": output_advantage["ci_low"] > 1.05,
        "model": False,
        "reproduces": False,
        "flat_output": flat_power["ci_low"] > 1.25,
        "corroboration": hull["ci_low"] > 0.005,
        "spatial": bool(
            spatial["leave_one_site_same_direction"]
            and spatial["all_quadrants_positive"]
        ),
    }
    print(
        "VERDICT_JSON="
        + json.dumps(
            {
                "preregistered": sc.verdict(flags),
                "flags": flags,
                "reason": "SOURCE_MODEL_FAILED_BEFORE_OUTCOMES",
                "detail_site_count": len(detail_rows),
                "flat_site_count": len(flat_rows),
                "unlicensed": sc.UNLICENSED,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
