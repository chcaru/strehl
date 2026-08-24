"""Run M82's M57-equivalent sharpness contrast through the shipped absolute gate."""

from __future__ import annotations

import argparse
import gc
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

import m82lib as M

M57_SRC = M.REPO / "experiments" / "m57-shape-metric" / "src"
sys.path.insert(0, str(M57_SRC))
import m57lib as K  # noqa: E402


def json_number(value):
    value = float(value)
    return value if math.isfinite(value) else None


def load_region(
    stack: str,
    region: tuple[int, int, int, int],
    contamination_roi: tuple[int, int, int, int] | None = None,
) -> dict:
    files = M.stack_files(stack)
    iso = float(M.STACKS[stack]["iso"])
    x, y, width, height = region
    padded = (x - M.PAD, y - M.PAD, width + 2 * M.PAD, height + 2 * M.PAD)
    raw_cube = None
    field_cube = None
    pin_samples = 0
    contamination = []
    black = None
    plane = None
    started = time.time()
    for index, path in enumerate(files):
        raw, luma, field, pins, frame_black, frame_plane = M.frame_arrays(
            path, iso, padded
        )
        if raw_cube is None:
            raw_cube = np.empty((len(files),) + raw.shape, dtype=np.float32)
            field_cube = np.empty((len(files),) + field.shape, dtype=np.float32)
            black = frame_black
            plane = frame_plane
        if frame_black != black or frame_plane != plane:
            raise RuntimeError(f"{stack}: frame levels or geometry changed")
        raw_cube[index] = raw
        field_cube[index] = field
        inner_pins = pins[M.PAD : M.PAD + height, M.PAD : M.PAD + width]
        pin_samples += int(inner_pins.sum())
        if contamination_roi is not None:
            cx, cy, cw, ch = contamination_roi
            local = (cx - padded[0], cy - padded[1], cw, ch)
            contamination.append(M.m77_contamination(luma, local, iso))
        if index == 0 or (index + 1) % max(1, len(files) // 10) == 0:
            print(
                f"{stack} region {region}: {index + 1}/{len(files)} "
                f"({time.time() - started:.1f}s)",
                flush=True,
            )
    if raw_cube is None or field_cube is None:
        raise RuntimeError(f"{stack}: no frames")
    return {
        "raw": raw_cube[:, M.PAD : M.PAD + height, M.PAD : M.PAD + width],
        "field": field_cube[:, M.PAD : M.PAD + height, M.PAD : M.PAD + width],
        "pin_samples": pin_samples,
        "contamination": contamination,
        "black": black,
        "plane": plane,
        "files": files,
    }


def dsig_record(reference: K.RingStats, target: K.RingStats) -> dict:
    row = K.dsig(reference, target)
    return {
        "px": json_number(row["px"]),
        "slope_px2": json_number(row["slope"]),
        "jackknife_se_px": json_number(row["se_px"]),
        "jackknife_se_slope": json_number(row["se_slope"]),
        "corrected_se_px": json_number(3.09 * row["se_px"]),
        "nring": int(row["nring"]),
        "ok": bool(row["ok"]),
        "residual_rms": json_number(row["resid"]),
        "sweep": json_number(row["sweep"]),
        "gof": json_number(row["gof"]),
    }


def process_region(data: dict, gates: dict[str, float], original_roi=None) -> dict:
    raw_cube = data["raw"]
    fields = data["field"]
    n = raw_cube.shape[0]
    even = np.arange(0, n, 2, dtype=np.int64)
    odd = np.arange(1, n, 2, dtype=np.int64)
    outputs = {}
    admission = {}
    for label, indexes in (("even", even), ("odd", odd)):
        best, winner = M.subset_reference(fields, indexes)
        selector, selector_stats = M.merge_subset(
            raw_cube, fields, indexes, best, winner, 0.0
        )
        outputs[(label, "selector")] = selector
        admission[(label, "selector")] = selector_stats
        for request, gate in gates.items():
            merged, stats = M.merge_subset(
                raw_cube, fields, indexes, best, winner, gate
            )
            outputs[(label, request)] = merged
            admission[(label, request)] = stats
    reference = K.RingStats(
        outputs[("even", "selector")], outputs[("odd", "selector")]
    )
    dsig = {
        request: dsig_record(
            reference,
            K.RingStats(outputs[("even", request)], outputs[("odd", request)]),
        )
        for request in gates
    }
    full = {}
    if original_roi is not None:
        best, winner = M.subset_reference(fields, np.arange(n, dtype=np.int64))
        ox, oy, ow, oh = original_roi
        for request, gate in gates.items():
            merged, stats = M.merge_subset(
                raw_cube,
                fields,
                np.arange(n, dtype=np.int64),
                best,
                winner,
                gate,
            )
            tile = merged[oy : oy + oh, ox : ox + ow]
            full[request] = {
                "raw_rms": M.raw_gradient_rms(tile),
                "admission": stats,
            }
    return {
        "dsig": dsig,
        "half_admission": {
            f"{label}:{request}": stats
            for (label, request), stats in admission.items()
        },
        "full": full,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stack", choices=tuple(M.STACKS), required=True)
    parser.add_argument("--confirm-results", default="confirm-results.json")
    parser.add_argument("--output-prefix", default="sharpness")
    args = parser.parse_args()
    stack = args.stack
    confirm = json.loads(
        (M.HERE / args.confirm_results).read_text(encoding="utf-8")
    )
    gates = {
        f"{request:.2f}": confirm["stacks"][stack]["targets"][f"{request:.2f}"][
            "solved_gate"
        ]
        for request in M.REQUESTS
    }
    cfg = M.STACKS[stack]
    output = {
        "stack": stack,
        "n": cfg["n"],
        "iso": cfg["iso"],
        "gates": gates,
        "constants": M.constants(),
        "m57_source": str(M57_SRC / "m57lib.py"),
        "m57_sha256": M.sha256(M57_SRC / "m57lib.py"),
        "files": {
            "first": M.stack_files(stack)[0].name,
            "last": M.stack_files(stack)[-1].name,
        },
    }

    print(f"{stack}: FLAT FIRST", flush=True)
    flat_data = load_region(stack, cfg["sharp_flat"], cfg["flat"])
    flat = process_region(flat_data, gates)
    flat["roi"] = cfg["sharp_flat"]
    flat["pin_samples"] = flat_data["pin_samples"]
    flat["m77_contamination_by_frame"] = flat_data["contamination"]
    flat["m77_contamination_max"] = max(flat_data["contamination"])
    flat["m77_flat_pass"] = flat["m77_contamination_max"] < 1.10
    output["flat"] = flat
    del flat_data
    gc.collect()

    print(f"{stack}: DETAIL", flush=True)
    detail_data = load_region(stack, cfg["sharp_detail"])
    dx = cfg["detail"][0] - cfg["sharp_detail"][0]
    dy = cfg["detail"][1] - cfg["sharp_detail"][1]
    detail = process_region(detail_data, gates, (dx, dy, 256, 256))
    detail["roi"] = cfg["sharp_detail"]
    detail["pin_samples"] = detail_data["pin_samples"]
    output["detail"] = detail
    output["black"] = detail_data["black"]
    output["plane"] = detail_data["plane"]
    del detail_data
    gc.collect()

    path = M.HERE / f"{args.output_prefix}-{stack}.json"
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    for request in gates:
        d = detail["dsig"][request]
        print(
            f"{stack} S={request}: dsig={d['px']} corrected_se={d['corrected_se_px']} "
            f"raw_rms={detail['full'][request]['raw_rms']:.6f}",
            flush=True,
        )
    print(
        f"{stack}: flat contamination max={flat['m77_contamination_max']:.6f} "
        f"pass={flat['m77_flat_pass']} pins(flat/detail)="
        f"{flat['pin_samples']}/{detail['pin_samples']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
