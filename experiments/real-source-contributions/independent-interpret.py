"""Frozen-profile interpretation aid. No source ranking, RAW reads or mutation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

NEIGHBOURHOODS = {"near-hair": (108, 112, 116), "far-hair": (148, 152, 156)}
DEFOCUSED = (316, 320, 324)


def reference(path: Path) -> dict:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": digest}


def contrast(profile: np.ndarray) -> np.ndarray:
    return profile[..., 2, :] - 0.5 * (profile[..., 0, :] + profile[..., 4, :])


def shape(profile: np.ndarray) -> dict:
    return {
        "centre_above_both_outer_flanks": ((profile[..., 2, :] > profile[..., 0, :]) &
                                             (profile[..., 2, :] > profile[..., 4, :])).tolist(),
        "ordered_rise_then_fall": ((profile[..., 0, :] <= profile[..., 1, :]) &
                                    (profile[..., 1, :] <= profile[..., 2, :]) &
                                    (profile[..., 2, :] >= profile[..., 3, :]) &
                                    (profile[..., 3, :] >= profile[..., 4, :])).tolist(),
        "signed_contrast_dn": contrast(profile).tolist(),
        "caution": "Shape statements only: no noise-significance, source truth or quality classification."
    }


def run(attribution_path: Path, contribution_path: Path, out: Path) -> None:
    attribution = json.loads(attribution_path.read_text(encoding="utf-8"))
    with np.load(contribution_path, allow_pickle=False) as data:
        gathered = data["gathered"].copy().reshape(488, 5, 5, 4)
        contribution_contrast = data["contribution_contrast"].copy()
        arithmetic = data["arithmetic_residual"].copy().reshape(5, 5, 4)
        clamp = data["clamp_residual"].copy().reshape(5, 5, 4)
    assert np.isfinite(gathered).all()
    assert contribution_contrast.shape == (488, 8, 5, 4)
    plan_path = Path(__file__).with_name("independent-plan.json")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    receipt_path = next(Path(item["path"]) for item in attribution["inputs"] if Path(item["path"]).name == "receipt.json")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    post = np.array([site["post_hull_bits"] for site in receipt["sites"]], dtype=np.uint32).view(np.float32).astype(np.float64).reshape(5, 5, 4)
    profiles = []
    for line, profile in enumerate(plan["profiles"]):
        name = profile["name"]
        selected = NEIGHBOURHOODS.get(name, (112, 152, 320))
        output = {"name": name, "native_centre": profile["centre_native"],
            "axis": profile["axis"], "offsets": plan["offsets_native"],
            "post_hull_five_points_dn": post[line].tolist(), "post_hull_shape": shape(post[line]),
            "arithmetic_residual_contrast_dn": contrast(arithmetic[line]).tolist(),
            "clamp_residual_contrast_dn": contrast(clamp[line]).tolist(),
            "fixed_sources": []}
        for index in (*selected, *DEFOCUSED):
            values = gathered[index, line]
            output["fixed_sources"].append({"source_index": index,
                "gathered_five_points_dn": values.tolist(), "shape": shape(values),
                "post_minus_source_contrast_dn": (contrast(post[line]) - contrast(values)).tolist()})
        # Preserve natural band/bin order. Do not rank the most convenient
        # sources or replace a sign-bearing profile by an absolute score.
        output["signed_contrast_by_band_and_bin"] = [
            {"band": band, "role": "terminal mean base" if band == 7 else "AC",
             "group_inclusive": [lo, hi],
             "signed_contrast_dn": contribution_contrast[lo:hi + 1, band, line].sum(axis=0).tolist()}
            for band in range(8) for lo, hi in plan["source_bins_inclusive"]]
        profiles.append(output)
    result = {"inputs": [reference(attribution_path), reference(contribution_path), reference(receipt_path),
                           reference(plan_path), reference(Path(__file__))],
        "frozen_neighbourhoods": NEIGHBOURHOODS, "frozen_defocused_control": DEFOCUSED,
        "profiles": profiles,
        "interpretation_limits": [
            "The near/far fixed neighbourhoods were prescribed before reading actual trace values; no recentering or source maximization.",
            "Full five-point profiles expose displaced peaks, monotone backgrounds and unequal flanks that scalar contrast hides.",
            "The two middle-offset samples are not independent replications of the central contrast.",
            "An ordered ridge shape can still be noise or another structure; this aid cannot establish sensor-noise significance.",
            "No interval counterfactual or image-quality pass is calculated. A negative group contribution may be necessary to cancel captured blur.",
            "If fixed witnesses do not demonstrate coherent captured structure lost by the consumer, move to the actual complete-chip versus HeliconB gap; do not expand this source search."
        ]}
    with out.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--attribution", type=Path, required=True)
    parser.add_argument("--contributions", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run(args.attribution.resolve(), args.contributions.resolve(), args.out.resolve())
