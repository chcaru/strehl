"""M78b geometry-only audit of the B6 ROI registry.

`rawpy.imread()` opens the file header. This script reads only `RawPy.sizes`;
it never calls `unpack`, `raw_image`, `raw_image_visible`, or `postprocess`.
"""

from __future__ import annotations

import argparse
import glob
import json
import os

import rawpy

import spec_v1 as S


ROOT = r"D:\personal\macro"
PAD = 32
LEGACY_QUAD_WIDTH = 2344
LEGACY_QUAD_HEIGHT = 3514
LEGACY_ROIS = (
    (458, 750, 512, 512),
    (1374, 750, 512, 512),
    (916, 1501, 512, 512),
    (916, 2402, 512, 512),
)


def visible_shape(path: str) -> tuple[int, int]:
    with rawpy.imread(path) as raw:
        return int(raw.sizes.height), int(raw.sizes.width)


def padded_bounds(roi: tuple[int, int, int, int], pad: int = PAD) -> dict:
    x, y, width, height = roi
    return {
        "x0": x - pad,
        "y0": y - pad,
        "x1": x + width + pad,
        "y1": y + height + pad,
    }


def audit_one(
    roi: tuple[int, int, int, int],
    quad_shape: tuple[int, int],
    pad: int = PAD,
) -> dict:
    quad_height, quad_width = quad_shape
    bounds = padded_bounds(roi, pad)
    valid = (
        bounds["x0"] >= 0
        and bounds["y0"] >= 0
        and bounds["x1"] <= quad_width
        and bounds["y1"] <= quad_height
    )
    return {
        "roi": list(roi),
        "padded_quad_bounds": bounds,
        "required_raw_extent": [2 * bounds["y1"], 2 * bounds["x1"]],
        "valid": bool(valid),
    }


def stack_geometry(stack: str) -> dict:
    files = sorted(glob.glob(os.path.join(ROOT, stack, "*.ARW")))
    if not files:
        raise FileNotFoundError(f"{stack}: no ARW files")
    shapes = {visible_shape(path) for path in files}
    if len(shapes) != 1:
        raise ValueError(f"{stack}: non-uniform visible raw shapes {sorted(shapes)}")
    raw_height, raw_width = next(iter(shapes))
    if raw_height % 2 or raw_width % 2:
        raise ValueError(f"{stack}: odd visible raw shape {(raw_height, raw_width)}")
    return {
        "stack": stack,
        "files": len(files),
        "raw_visible_shape": [raw_height, raw_width],
        "quad_shape": [raw_height // 2, raw_width // 2],
    }


def registry(name: str) -> tuple[tuple[int, int, int, int], ...]:
    if name == "legacy":
        return LEGACY_ROIS
    return tuple(S.roi_rule())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", choices=("legacy", "current"), default="current")
    parser.add_argument("--json")
    args = parser.parse_args()

    rois = registry(args.registry)
    stacks = [stack_geometry(stack) for stack in S.HELD_OUT]
    unique_quad_shapes = {tuple(row["quad_shape"]) for row in stacks}
    if len(unique_quad_shapes) != 1:
        raise ValueError(f"held-out stacks have different quad shapes: {sorted(unique_quad_shapes)}")
    quad_shape = next(iter(unique_quad_shapes))

    records = []
    print("M78b B6 ROI GEOMETRY AUDIT")
    print("MEASURED: rawpy header sizes only; pixel decode calls = 0")
    print(f"MEASURED: registry={args.registry}; ROIs={list(rois)}")
    for stack in stacks:
        print(
            f"MEASURED: {stack['stack']}: files={stack['files']}, "
            f"raw_visible={tuple(stack['raw_visible_shape'])}, "
            f"quad={tuple(stack['quad_shape'])}"
        )
        for index, roi in enumerate(rois):
            native = audit_one(roi, quad_shape)
            transposed_roi = (roi[1], roi[0], roi[2], roi[3])
            transposed = audit_one(transposed_roi, quad_shape)
            row = {
                "stack": stack["stack"],
                "roi_index": index,
                "native": native,
                "transposed": transposed,
                "valid_both_ways": bool(native["valid"] and transposed["valid"]),
            }
            records.append(row)
            nb = native["padded_quad_bounds"]
            tb = transposed["padded_quad_bounds"]
            print(
                f"  MEASURED: roi{index}={roi}: "
                f"native quad[x={nb['x0']}..{nb['x1']},y={nb['y0']}..{nb['y1']}] "
                f"raw_extent={tuple(native['required_raw_extent'])} "
                f"{'VALID' if native['valid'] else 'INVALID'}; "
                f"swap={transposed_roi} "
                f"quad[x={tb['x0']}..{tb['x1']},y={tb['y0']}..{tb['y1']}] "
                f"raw_extent={tuple(transposed['required_raw_extent'])} "
                f"{'VALID' if transposed['valid'] else 'INVALID'}; "
                f"both={row['valid_both_ways']}"
            )

    by_roi = {}
    for index in range(len(rois)):
        selected = [row for row in records if row["roi_index"] == index]
        by_roi[index] = {
            "native_valid_stacks": sum(row["native"]["valid"] for row in selected),
            "transposed_valid_stacks": sum(row["transposed"]["valid"] for row in selected),
            "both_valid_stacks": sum(row["valid_both_ways"] for row in selected),
        }
    legacy_constants_swapped = (
        LEGACY_QUAD_WIDTH == quad_shape[0] and LEGACY_QUAD_HEIGHT == quad_shape[1]
    )
    if args.registry == "legacy":
        verdict = (
            "CONFIRMED"
            if legacy_constants_swapped
            and all(row["transposed"]["valid"] for row in records)
            and any(not row["native"]["valid"] for row in records)
            else "REFUTED"
        )
    else:
        verdict = "NOT_APPLICABLE_REPAIRED_REGISTRY"
    print(f"MEASURED: per-ROI summary={by_roi}")
    print(
        "MEASURED: legacy constants "
        f"(width={LEGACY_QUAD_WIDTH}, height={LEGACY_QUAD_HEIGHT}); "
        f"actual quad (height={quad_shape[0]}, width={quad_shape[1]}); "
        f"width/height transposition={legacy_constants_swapped}"
    )
    print(f"DERIVED: row/column-transposition hypothesis={verdict}")

    output = {
        "registry": args.registry,
        "pixel_decode_calls": 0,
        "stacks": stacks,
        "rois": [list(roi) for roi in rois],
        "records": records,
        "per_roi": by_roi,
        "legacy_constants": {
            "quad_width": LEGACY_QUAD_WIDTH,
            "quad_height": LEGACY_QUAD_HEIGHT,
        },
        "actual_quad_shape": list(quad_shape),
        "legacy_constants_swapped": legacy_constants_swapped,
        "transposition_hypothesis": verdict,
    }
    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(output, handle, indent=2)
            handle.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
