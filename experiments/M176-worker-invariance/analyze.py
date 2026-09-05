from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

from common import (
    EvidenceError,
    canonical_pixel_hash,
    file_record,
    read_json,
    write_json_new,
)


CHANNELS = ("R", "G", "B")
EDGE_BREAKS = (1, 2, 4, 8, 16, 32, 64, 128, 256)


def decode_primary(path: Path) -> np.ndarray:
    import tifffile

    value = np.asarray(tifffile.imread(path))
    if value.dtype != np.uint16 or value.ndim != 3 or value.shape[2] != 3:
        raise EvidenceError(
            "M176-E-DECODE-PRIMARY",
            f"{path} decoded as {value.shape} {value.dtype}, expected HxWx3 uint16",
        )
    return np.ascontiguousarray(value)


def decode_secondary(path: Path) -> np.ndarray:
    import cv2

    value = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if value is None:
        raise EvidenceError("M176-E-DECODE-SECONDARY", f"OpenCV could not read {path}")
    if value.dtype != np.uint16 or value.ndim != 3 or value.shape[2] != 3:
        raise EvidenceError(
            "M176-E-DECODE-SECONDARY",
            f"{path} decoded as {value.shape} {value.dtype}, expected HxWx3 uint16",
        )
    return np.ascontiguousarray(value[:, :, ::-1])


def decoded_record(path: Path) -> tuple[dict[str, Any], np.ndarray]:
    primary = decode_primary(path)
    secondary = decode_secondary(path)
    primary_hash = canonical_pixel_hash(primary)
    secondary_hash = canonical_pixel_hash(secondary)
    equal = bool(np.array_equal(primary, secondary))
    if not equal or primary_hash != secondary_hash:
        raise EvidenceError(
            "M176-E-DECODE-DISAGREE",
            f"independent decoders disagree for {path}",
        )
    import cv2
    import tifffile

    return (
        {
            "file": file_record(path),
            "shape": list(primary.shape),
            "dtype": str(primary.dtype),
            "canonical_pixel_sha256": primary_hash,
            "secondary_canonical_pixel_sha256": secondary_hash,
            "independent_decoders_equal": equal,
            "primary_decoder": {
                "library": "tifffile",
                "version": tifffile.__version__,
            },
            "secondary_decoder": {
                "library": "opencv",
                "version": cv2.__version__,
                "channel_normalization": "BGR-to-RGB",
            },
        },
        primary,
    )


def array_difference(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    if a.shape != b.shape or a.dtype != b.dtype:
        raise EvidenceError(
            "M176-E-COMPARE-SHAPE",
            f"array mismatch: {a.shape}/{a.dtype} versus {b.shape}/{b.dtype}",
        )
    delta = b.astype(np.int32) - a.astype(np.int32)
    changed_samples = delta != 0
    changed_pixels = np.any(changed_samples, axis=2)
    signed, counts = np.unique(delta[changed_samples], return_counts=True)
    histogram = {
        str(int(key)): int(value) for key, value in zip(signed, counts, strict=True)
    }
    per_channel = {
        channel: int(np.count_nonzero(changed_samples[:, :, index]))
        for index, channel in enumerate(CHANNELS)
    }
    ys, xs = np.nonzero(changed_pixels)
    bbox = (
        None
        if len(xs) == 0
        else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    )
    edge_distribution: dict[str, int] = {}
    if len(xs):
        height, width = changed_pixels.shape
        distance = np.minimum.reduce((xs, ys, width - 1 - xs, height - 1 - ys))
        lower = 0
        for upper in EDGE_BREAKS:
            edge_distribution[f"[{lower},{upper})"] = int(
                np.count_nonzero((distance >= lower) & (distance < upper))
            )
            lower = upper
        edge_distribution[f"[{lower},inf)"] = int(np.count_nonzero(distance >= lower))
    else:
        for lower, upper in zip((0, *EDGE_BREAKS[:-1]), EDGE_BREAKS, strict=True):
            edge_distribution[f"[{lower},{upper})"] = 0
        edge_distribution[f"[{EDGE_BREAKS[-1]},inf)"] = 0

    absolute = np.abs(delta)
    max_absolute = int(absolute.max(initial=0))
    max_abs_location: dict[str, Any] | None = None
    if max_absolute:
        y, x, channel_index = np.argwhere(absolute == max_absolute)[0]
        max_abs_location = {
            "x": int(x),
            "y": int(y),
            "channel": CHANNELS[int(channel_index)],
            "a": int(a[y, x, channel_index]),
            "b": int(b[y, x, channel_index]),
            "signed_delta_b_minus_a": int(delta[y, x, channel_index]),
        }

    max_relative = 0.0
    max_relative_location: dict[str, Any] | None = None
    for channel_index, channel in enumerate(CHANNELS):
        numerator = absolute[:, :, channel_index].astype(np.float64)
        denominator = np.maximum(a[:, :, channel_index], b[:, :, channel_index]).astype(
            np.float64
        )
        ratio = np.divide(
            numerator,
            denominator,
            out=np.zeros_like(numerator),
            where=denominator != 0,
        )
        candidate = float(ratio.max(initial=0.0))
        if candidate > max_relative:
            y, x = np.argwhere(ratio == candidate)[0]
            max_relative = candidate
            max_relative_location = {
                "x": int(x),
                "y": int(y),
                "channel": channel,
                "a": int(a[y, x, channel_index]),
                "b": int(b[y, x, channel_index]),
                "absolute_delta": int(absolute[y, x, channel_index]),
                "relative_deviation": candidate,
            }

    examples: list[dict[str, Any]] = []
    for y, x, channel_index in np.argwhere(changed_samples)[:16]:
        examples.append(
            {
                "x": int(x),
                "y": int(y),
                "channel": CHANNELS[int(channel_index)],
                "a": int(a[y, x, channel_index]),
                "b": int(b[y, x, channel_index]),
                "signed_delta_b_minus_a": int(delta[y, x, channel_index]),
            }
        )

    return {
        "shape": list(a.shape),
        "dtype": str(a.dtype),
        "signed_delta_direction": "B_MINUS_A",
        "pixel_identical": bool(not np.any(changed_samples)),
        "differing_channel_samples": int(np.count_nonzero(changed_samples)),
        "differing_pixels_any_channel": int(np.count_nonzero(changed_pixels)),
        "per_channel_differing_samples": per_channel,
        "signed_delta_histogram": histogram,
        "differing_pixel_bbox_xyxy_inclusive": bbox,
        "differing_pixel_edge_distance_bins": edge_distribution,
        "max_absolute_dn16": max_absolute,
        "max_absolute_over_65535": max_absolute / 65535.0,
        "max_absolute_location": max_abs_location,
        "max_relative_per_pixel_channel": max_relative,
        "max_relative_location": max_relative_location,
        "first_differing_channel_samples": examples,
    }


def metadata_relation(
    a_file_hash: str,
    b_file_hash: str,
    a_pixel_hash: str,
    b_pixel_hash: str,
) -> str:
    if a_pixel_hash != b_pixel_hash:
        return "PIXELS_DIFFER"
    if a_file_hash != b_file_hash:
        return "FILE_METADATA_ONLY"
    return "FILE_AND_PIXELS_IDENTICAL"


def classify(
    images: dict[str, dict[str, Any]],
    comparisons: dict[str, dict[str, Any]],
    source: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    repeat = comparisons["affected_w1_vs_repeat"]
    fixed = comparisons["fixed_w1_vs_w2"]
    affected_key = source["affected_comparison"]
    affected = comparisons[affected_key]
    if not repeat["pixel_identical"]:
        return "OTHER_UNRESOLVED", ["affected W1 repeat is not pixel-identical"]
    if affected["pixel_identical"]:
        relation = metadata_relation(
            images["affected-w1"]["file"]["sha256"],
            images[source["affected_other_arm"]]["file"]["sha256"],
            images["affected-w1"]["canonical_pixel_sha256"],
            images[source["affected_other_arm"]]["canonical_pixel_sha256"],
        )
        if relation == "FILE_METADATA_ONLY":
            return "FILE_METADATA_ONLY", [
                "affected files differ but decoded pixels do not"
            ]
        return "NOT_REPRODUCED", [
            "affected decoded pixels are worker-invariant through W3"
        ]
    if not fixed["pixel_identical"]:
        return "OTHER_UNRESOLVED", ["fixed W1/W2 decoded pixels still differ"]
    if not source["runtime_preconditions"]["alignment_off_all_runs"]:
        return "BOUNDARY", ["alignment was active"]
    if not source["runtime_preconditions"]["coverage_boundary_excluded"]:
        return "BOUNDARY", ["coverage boundary was not excluded"]
    if not source["mechanism_preconditions"]["soft_power_default"]:
        return "SELECTION_TIE", ["active selection was not SoftPower"]
    required = [
        "affected_workers_change_chunks",
        "fixed_workers_do_not_change_chunks",
        "f32_accumulators",
        "f32_absorb_addition",
    ]
    missing = [name for name in required if not source["mechanism_preconditions"][name]]
    if missing:
        return "OTHER_UNRESOLVED", [
            f"missing source preconditions: {', '.join(missing)}"
        ]
    reasons.extend(
        [
            "affected fixed-worker repeat is pixel-identical",
            "affected cross-worker decoded pixels differ",
            "affected workers select different frame chunks and absorb grouping",
            "fixed W1/W2 decoded pixels are pixel-identical",
            "SoftPower accumulates and absorbs f32 sums",
            "alignment is off, so coverage/resampling boundaries cannot select the delta",
        ]
    )
    return "REDUCTION_ORDER", reasons


def build_analysis(evidence_dir: Path) -> dict[str, Any]:
    runs = read_json(evidence_dir / "runs.json")
    source = read_json(evidence_dir / "source-evidence.json")
    arrays: dict[str, np.ndarray] = {}
    images: dict[str, dict[str, Any]] = {}
    for record in runs["runs"]:
        run_id = record["run_id"]
        decoded, pixels = decoded_record(Path(record["output"]["path"]))
        images[run_id] = decoded
        arrays[run_id] = pixels

    pairs = {
        "affected_w1_vs_w2": ("affected-w1", "affected-w2"),
        "affected_w1_vs_repeat": ("affected-w1", "affected-w1-repeat"),
        "fixed_w1_vs_w2": ("fixed-w1", "fixed-w2"),
    }
    if "affected-w3" in arrays:
        pairs["affected_w1_vs_w3"] = ("affected-w1", "affected-w3")
    comparisons: dict[str, dict[str, Any]] = {}
    for name, (a_name, b_name) in pairs.items():
        value = array_difference(arrays[a_name], arrays[b_name])
        value["a"] = a_name
        value["b"] = b_name
        value["file_pixel_relation"] = metadata_relation(
            images[a_name]["file"]["sha256"],
            images[b_name]["file"]["sha256"],
            images[a_name]["canonical_pixel_sha256"],
            images[b_name]["canonical_pixel_sha256"],
        )
        comparisons[name] = value

    verdict, reasons = classify(images, comparisons, source)
    return {
        "schema": "strehl-m176-analysis-v1",
        "images": images,
        "comparisons": comparisons,
        "independent_decoder_corroboration": {
            "all_images_equal": all(
                record["independent_decoders_equal"] for record in images.values()
            ),
            "image_count": len(images),
        },
        "mechanism_verdict": verdict,
        "mechanism_reasons": reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = build_analysis(args.evidence_dir)
        write_json_new(args.evidence_dir / "analysis.json", result)
    except EvidenceError as error:
        print(str(error), file=sys.stderr)
        return 1
    source = read_json(args.evidence_dir / "source-evidence.json")
    comparison = result["comparisons"][source["affected_comparison"]]
    print(
        json_summary(
            {
                "verdict": result["mechanism_verdict"],
                "differing_pixels": comparison["differing_pixels_any_channel"],
                "max_absolute_dn16": comparison["max_absolute_dn16"],
                "max_relative": comparison["max_relative_per_pixel_channel"],
            }
        )
    )
    return 0


def json_summary(value: dict[str, Any]) -> str:
    import json

    return json.dumps(value, sort_keys=True)


if __name__ == "__main__":
    raise SystemExit(main())
