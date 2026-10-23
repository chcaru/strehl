"""Original, model-independent research metrics; no Adobe implementation/assets.

Run --commission separately, then call compare_heads on NPZ mappings or arrays.
These measure imitation under declared tensor semantics, not image aesthetics.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path

import numpy as np

HEAD_SHAPES = {
    **{name: (1, 16, 96, 128) for name in ("pgtm", "pgtm_hdr")},
    **{f"rgbt_{index}{suffix}": (1, 3, 32, 32, 32)
       for suffix in ("", "_hdr") for index in range(3)},
    **{name: (1, 1) for name in ("exposure", "exposure_hdr")},
}


def error_statistics(reference: np.ndarray, candidate: np.ndarray) -> dict:
    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape or not a.size:
        raise ValueError(f"matching nonempty shapes required: {a.shape}, {b.shape}")
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError("nonfinite outputs are invalid, not an ignorable sample")
    delta = b - a
    absolute = np.abs(delta)
    return {"mae": float(absolute.mean()), "rmse": float(np.sqrt(np.mean(delta * delta))),
            "p95_absolute": float(np.quantile(absolute, 0.95)),
            "max_absolute": float(absolute.max()), "signed_mean": float(delta.mean()),
            "reference_std": float(a.std()), "candidate_std": float(b.std())}


def compare_heads(teacher: Mapping[str, np.ndarray], student: Mapping[str, np.ndarray]) -> dict:
    required = set(HEAD_SHAPES)
    if set(teacher) != required or set(student) != required:
        raise ValueError("all ten exact named heads required; missing/extra heads cannot silently pass")
    result = {}
    for name, shape in HEAD_SHAPES.items():
        a, b = np.asarray(teacher[name]), np.asarray(student[name])
        if a.shape != shape or b.shape != shape:
            raise ValueError(f"{name}: expected {shape}, got {a.shape}, {b.shape}")
        raw = error_statistics(a, b)
        if name.startswith("pgtm"):
            if np.any(a <= 0) or np.any(b <= 0):
                raise ValueError(f"{name}: spatial gain must be positive; no epsilon clamp hides invalid predictions")
            primary = error_statistics(np.log2(a.astype(np.float64)), np.log2(b.astype(np.float64)))
            result[name] = {"units": "log2_gain_ratio_stops", "primary": primary, "raw": raw}
        elif name.startswith("rgbt"):
            result[name] = {"units": "model_lattice_output_units", "primary": raw,
                            "per_channel": [error_statistics(a[:, c], b[:, c]) for c in range(3)]}
        else:
            result[name] = {"units": "model_scalar_output_units_conversion_unverified", "primary": raw}
    return result


def baseline_improvement(student_report: Mapping, baseline_report: Mapping) -> dict:
    """Call per-image; aggregate by scene group, not tensor element count."""
    result = {}
    for name in HEAD_SHAPES:
        student = float(student_report[name]["primary"]["rmse"])
        baseline = float(baseline_report[name]["primary"]["rmse"])
        result[name] = {"student_rmse": student, "baseline_rmse": baseline,
                        "fraction_reduction": 1 - student / baseline if baseline > 1e-12 else None,
                        "baseline_has_resolvable_error": baseline > 1e-12}
    return result


def render_control_metrics(reference: np.ndarray, candidate: np.ndarray,
                           flat_mask: np.ndarray, *, low: float = 0, high: float = 1) -> dict:
    """Use a fixed native-resolution ROI or a small synthetic image.

    A full-photo caller may tile externally. No camera-noise estimate, color
    primaries, transfer function or perceptual quality is inferred here.
    """
    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    mask = np.asarray(flat_mask, dtype=bool)
    if a.ndim != 3 or a.shape[-1] != 3 or a.shape != b.shape or mask.shape != a.shape[:2]:
        raise ValueError("expected matching HWC RGB images and a spatial flat-region mask")
    if np.count_nonzero(mask) < 16 or not high > low:
        raise ValueError("flat control needs at least 16 samples and declared bounds")
    overall = error_statistics(a, b)
    residual = b[mask] - a[mask]
    centered = residual - residual.mean(axis=0, keepdims=True)
    return {"representation": "caller_declared_RGB_not_a_perceptual_metric", "difference": overall,
            "reference_flat_region_channel_std": a[mask].std(axis=0).tolist(),
            "flat_residual_texture_rms": float(np.sqrt(np.mean(centered * centered))),
            "flat_residual_mean_rgb": residual.mean(axis=0).tolist(),
            "reference_low_fraction": float(np.mean(a <= low)),
            "candidate_low_fraction": float(np.mean(b <= low)),
            "reference_high_fraction": float(np.mean(a >= high)),
            "candidate_high_fraction": float(np.mean(b >= high)),
            "candidate_below_bound_fraction": float(np.mean(b < low)),
            "candidate_above_bound_fraction": float(np.mean(b > high))}


def commission() -> dict:
    # Distinct spatial and color fixtures ensure wrong mappings have power to fail.
    heads = {name: np.full(shape, 0.25 + index * 0.03, np.float32)
             for index, (name, shape) in enumerate(HEAD_SHAPES.items())}
    spatial = np.linspace(0.5, 1.5, 128, dtype=np.float32)[None, None, None, :]
    heads["pgtm"] = np.broadcast_to(spatial, HEAD_SHAPES["pgtm"]).copy()
    assert heads["pgtm"].std() > 0.1
    identical = compare_heads(heads, heads)
    assert all(row["primary"]["rmse"] == 0 for row in identical.values())

    twice = {**heads, "pgtm": heads["pgtm"] * 2}
    ev = compare_heads(heads, twice)["pgtm"]["primary"]
    assert abs(ev["rmse"] - 1) < 1e-10
    assert abs(ev["signed_mean"] - 1) < 1e-10

    flipped = {**heads, "pgtm": heads["pgtm"][..., ::-1]}
    shifted_error = compare_heads(heads, flipped)["pgtm"]["primary"]["rmse"]
    assert shifted_error > 0.5
    assert abs(float(heads["pgtm"].mean()) - float(flipped["pgtm"].mean())) < 1e-6

    rejected = []
    cases = {
        "zero_gain": {**heads, "pgtm": np.zeros_like(heads["pgtm"])},
        "nonfinite": {**heads, "exposure": np.full((1, 1), np.nan)},
        "shape": {**heads, "exposure": np.zeros((1, 2))},
        "missing_head": {k: v for k, v in heads.items() if k != "rgbt_2_hdr"},
    }
    for label, damaged in cases.items():
        try:
            compare_heads(heads, damaged)
        except ValueError:
            rejected.append(label)
        else:
            raise AssertionError(f"negative control unexpectedly accepted: {label}")

    reference = np.full((32, 32, 3), 0.4, np.float32)
    checker = np.indices((32, 32)).sum(axis=0) % 2
    damaged = reference + (checker[..., None] * 2 - 1) * 0.02
    flat = render_control_metrics(reference, damaged, np.ones((32, 32), bool))
    assert flat["flat_residual_texture_rms"] > 0.019
    assert np.max(np.abs(flat["flat_residual_mean_rgb"])) < 1e-7
    return {"commission_only_not_real_photo_acceptance": True, "identical_zero": True,
            "gain_times_two_log2_rmse": ev["rmse"], "histogram_preserving_spatial_reversal_rmse": shifted_error,
            "invalid_cases_rejected": rejected, "flat_added_texture_rms": flat["flat_residual_texture_rms"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commission", action="store_true")
    parser.add_argument("--teacher", type=Path)
    parser.add_argument("--student", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.commission:
        result = commission()
    elif args.teacher and args.student:
        with np.load(args.teacher, allow_pickle=False) as teacher, np.load(args.student, allow_pickle=False) as student:
            result = compare_heads(teacher, student)
    else:
        parser.error("provide --commission or both --teacher and --student NPZ files")
    text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
