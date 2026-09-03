"""Run the preregistered tone-neutral comparison on both frozen pairs."""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

from commission import fixture
from ordinal import (
    BAND_NAMES,
    PAIRS,
    bootstrap_effect,
    candidate_centres,
    classify,
    fit_geometry,
    green_memmap,
    leave_one_out_classes,
    measure_roi,
    ordinal_shares,
    quadrant_ratios,
    robustness_downgrade,
)


def blur_sensitivity() -> tuple[list[float], list[bool]]:
    x = fixture()
    base = ordinal_shares(x)
    blurred = ordinal_shares(ndimage.gaussian_filter(x, 2.0))
    move = np.abs(blurred / base - 1.0)
    return move.tolist(), (move >= 0.05).tolist()


def base_class(low: float, high: float) -> str:
    if low > 1.05:
        return "LEADS"
    if high < 1.0 / 1.05:
        return "TRAILS"
    return "UNRESOLVED"


def run_pair(key: str) -> dict:
    pair = PAIRS[key]
    print(f"\n=== {key}: strehl vs {pair.label} ===", flush=True)
    geometry = fit_geometry(pair.strehl, pair.comparator)
    if not geometry["coarse_interior"] or not geometry["fine_interior"]:
        raise RuntimeError(f"{key}: geometry has no interior maximum")
    print(
        f"geometry scale={geometry['scale']:.4f}, score={geometry['score']:.6f}, "
        f"global correction={geometry['global_correction']}, "
        f"tile residual={geometry['residual_rms']:.2f}px",
        flush=True,
    )

    sg = green_memmap(pair.strehl)
    cg = green_memmap(pair.comparator)
    centres = candidate_centres(sg.shape)
    rows = []
    for i, centre in enumerate(centres, 1):
        rows.append(measure_roi(sg, cg, centre, geometry))
        if i % 12 == 0 or i == len(centres):
            print(f"ROI progress {i}/{len(centres)}", flush=True)

    reasons = collections.Counter(r["reason"] or "eligible" for r in rows)
    eligible = [r for r in rows if r["reason"] is None]
    print(f"coverage: {dict(sorted(reasons.items()))}", flush=True)
    if len(eligible) < 24:
        raise RuntimeError(
            f"{key}: only {len(eligible)} eligible ROIs; need 24 for 12 detail/6 flat"
        )

    textures = np.asarray([r["texture"] for r in eligible])
    flat_cut = float(np.quantile(textures, 0.25))
    detail_cut = float(np.quantile(textures, 0.50))
    flat_rows = [r for r in eligible if r["texture"] <= flat_cut]
    detail_rows = [r for r in eligible if r["texture"] >= detail_cut]
    flat = np.asarray([r["log_ratio"] for r in flat_rows], np.float64)
    detail = np.asarray([r["log_ratio"] for r in detail_rows], np.float64)
    if len(detail_rows) < 12 or len(flat_rows) < 6:
        raise RuntimeError(
            f"{key}: strata too small: detail={len(detail_rows)}, flat={len(flat_rows)}"
        )

    effect = bootstrap_effect(detail, flat)
    blur_move, sensitive = blur_sensitivity()
    classes = []
    provisional = []
    for k in range(len(BAND_NAMES)):
        p = base_class(effect["detail_ci_low"][k], effect["detail_ci_high"][k])
        provisional.append(p)
        classes.append(
            classify(
                effect["detail_ci_low"][k],
                effect["detail_ci_high"][k],
                effect["flat_ci_low"][k],
                effect["flat_ci_high"][k],
                sensitive[k],
            )
        )

    loo = leave_one_out_classes(detail, flat)
    loo_reversal = []
    for k, p in enumerate(provisional):
        opposite = "TRAILS" if p == "LEADS" else "LEADS" if p == "TRAILS" else None
        reversed_k = bool(opposite and any(row[k] == opposite for row in loo))
        loo_reversal.append(reversed_k)
        classes[k] = robustness_downgrade(
            classes[k], "UNRESOLVED (LOO REVERSAL)", reversed_k
        )

    quadrants = quadrant_ratios(eligible, detail_cut, sg.shape)
    quadrant_opposition = []
    for k, p in enumerate(provisional):
        ratios = [q["r_detail"][k] for q in quadrants]
        if p == "LEADS":
            n_opposite = sum(x < 1.0 for x in ratios)
        elif p == "TRAILS":
            n_opposite = sum(x > 1.0 for x in ratios)
        else:
            n_opposite = 0
        opposed = n_opposite >= 2
        quadrant_opposition.append(opposed)
        classes[k] = robustness_downgrade(
            classes[k], "UNRESOLVED (QUADRANT)", opposed
        )

    diagnosed = [r for r in rows if "corr_fixed" in r]
    corr_fixed = np.asarray([r["corr_fixed"] for r in diagnosed])
    corr_none = np.asarray([r["corr_none"] for r in diagnosed])
    corr_wrong = np.asarray([r["corr_wrong"] for r in diagnosed])
    aggregate_sign_ok = bool(
        np.nanmedian(corr_fixed) > np.nanmedian(corr_none)
        and np.nanmedian(corr_fixed) > np.nanmedian(corr_wrong)
    )
    if not aggregate_sign_ok:
        classes = [
            robustness_downgrade(c, "UNRESOLVED (REGISTRATION)", True)
            for c in classes
        ]

    for k, name in enumerate(BAND_NAMES):
        print(
            f"{name}: R_detail={effect['r_detail'][k]:.4f} "
            f"[{effect['detail_ci_low'][k]:.4f},{effect['detail_ci_high'][k]:.4f}] "
            f"R_flat={effect['r_flat'][k]:.4f} "
            f"[{effect['flat_ci_low'][k]:.4f},{effect['flat_ci_high'][k]:.4f}] "
            f"=> {classes[k]}",
            flush=True,
        )

    print(
        "registration median correlation "
        f"none={np.nanmedian(corr_none):.4f}, "
        f"wrong={np.nanmedian(corr_wrong):.4f}, "
        f"correct={np.nanmedian(corr_fixed):.4f}, "
        f"sign_ok={aggregate_sign_ok}",
        flush=True,
    )

    result = {
        "pair": key,
        "label": pair.label,
        "geometry": geometry,
        "candidate_count": len(centres),
        "reasons": dict(sorted(reasons.items())),
        "eligible_count": len(eligible),
        "detail_count": len(detail_rows),
        "flat_count": len(flat_rows),
        "flat_cut": flat_cut,
        "detail_cut": detail_cut,
        "detail_centres": [r["centre"] for r in detail_rows],
        "flat_centres": [r["centre"] for r in flat_rows],
        "effect": effect,
        "blur_move": blur_move,
        "sensitive": sensitive,
        "provisional_classes": provisional,
        "classes": classes,
        "loo_reversal": loo_reversal,
        "quadrants": quadrants,
        "quadrant_opposition": quadrant_opposition,
        "registration": {
            "none_median": float(np.nanmedian(corr_none)),
            "wrong_median": float(np.nanmedian(corr_wrong)),
            "correct_median": float(np.nanmedian(corr_fixed)),
            "aggregate_sign_ok": aggregate_sign_ok,
        },
        "rails": {
            "strehl_max": float(max(r["strehl_rail"] for r in diagnosed)),
            "comparator_max": float(max(r["comparator_rail"] for r in diagnosed)),
        },
        "largest_ties": {
            "strehl_median": float(
                np.median([r["strehl_largest_tie"] for r in diagnosed])
            ),
            "strehl_max": float(max(r["strehl_largest_tie"] for r in diagnosed)),
            "comparator_median": float(
                np.median([r["comparator_largest_tie"] for r in diagnosed])
            ),
            "comparator_max": float(
                max(r["comparator_largest_tie"] for r in diagnosed)
            ),
        },
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pairs", nargs="*", choices=tuple(PAIRS), default=None)
    args = parser.parse_args(argv)
    output = {}
    for key in args.pairs or list(PAIRS):
        output[key] = run_pair(key)
    print("\nRESULT_JSON=" + json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
