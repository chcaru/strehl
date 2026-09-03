from __future__ import annotations

import concurrent.futures
import json
import math
import os
from pathlib import Path

import numpy as np
import rawpy

from common import OUT, write_json
from prepare import CAPTURES


NAMES = (
    "foam",
    "salt",
    "battery",
    "angled-ruler",
    "calibration-grid-sw1",
    "calibration-grid-1-sw4",
    "calibration-grid-2-sw4",
    "calibration-grid-1-sw10",
    "calibration-grid-2-sw10",
    "fabric-f5.6",
    "fabric-f8",
    "fabric-f11",
)


def census_file(path_text: str) -> dict[str, object]:
    path = Path(path_text)
    with rawpy.imread(str(path)) as raw:
        visible = raw.raw_image_visible.copy()
        pattern = np.asarray(raw.raw_pattern, dtype=np.int32)
        black = np.asarray(raw.black_level_per_channel, dtype=np.float64)
        white = float(raw.white_level)
    high = 0
    low = 0
    maximum = -math.inf
    minimum = math.inf
    samples = 0
    for py in range(2):
        for px in range(2):
            channel = int(pattern[py, px])
            plane = visible[py::2, px::2]
            denominator = white - black[channel]
            high_threshold = black[channel] + 0.98 * denominator
            low_threshold = black[channel] + 0.02 * denominator
            high += int(np.count_nonzero(plane >= high_threshold))
            low += int(np.count_nonzero(plane <= low_threshold))
            maximum = max(maximum, (float(np.max(plane)) - black[channel]) / denominator)
            minimum = min(minimum, (float(np.min(plane)) - black[channel]) / denominator)
            samples += int(plane.size)
    return {
        "file": path.name,
        "high_samples": high,
        "low_samples": low,
        "maximum_normalized": maximum,
        "minimum_normalized": minimum,
        "samples": samples,
    }


def commission() -> dict[str, object]:
    black = 512.0
    white = 16383.0
    high_threshold = black + 0.98 * (white - black)
    low_threshold = black + 0.02 * (white - black)
    null = np.asarray([low_threshold + 1.0, high_threshold - 1.0])
    planted = np.asarray([low_threshold - 1.0, high_threshold + 1.0])
    null_green = not np.any(null >= high_threshold) and not np.any(null <= low_threshold)
    high_red = int(np.count_nonzero(planted >= high_threshold)) == 1
    low_red = int(np.count_nonzero(planted <= low_threshold)) == 1
    return {
        "null_stayed_green": bool(null_green),
        "high_rail_plant_went_red": bool(high_red),
        "low_rail_plant_went_red": bool(low_red),
        "commissioned": bool(null_green and high_red and low_red),
        "external_predicate": {
            "high": "sample >= black + 0.98*(white-black)",
            "low": "sample <= black + 0.02*(white-black)",
        },
    }


def main() -> int:
    commissioning = commission()
    if not commissioning["commissioned"]:
        raise RuntimeError("rail preflight did not commission")
    rows = []
    for name in NAMES:
        directory = CAPTURES[name]
        files = sorted(
            path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".arw"
        )
        with concurrent.futures.ProcessPoolExecutor(max_workers=8) as pool:
            readings = list(pool.map(census_file, map(str, files), chunksize=1))
        high = sum(row["high_samples"] for row in readings)
        low = sum(row["low_samples"] for row in readings)
        record = {
            "capture": name,
            "path": str(directory),
            "frames": len(files),
            "high_samples_across_frames": high,
            "low_samples_across_frames": low,
            "maximum_normalized": max(row["maximum_normalized"] for row in readings),
            "minimum_normalized": min(row["minimum_normalized"] for row in readings),
            "high_recoverable_10000_possible": high >= 10_000,
            "low_recoverable_10000_possible": low >= 10_000,
            "qualification_scope": (
                "A false value proves underpower because recoverable unique output pixels "
                "cannot exceed total rail samples. A true value is necessary, not sufficient."
            ),
        }
        rows.append(record)
        print(
            name,
            f"high={high}",
            f"low={low}",
            f"max={record['maximum_normalized']:.6f}",
            f"min={record['minimum_normalized']:.6f}",
        )
    result = {
        "status": "INPUT_ONLY_NECESSARY_CONDITION",
        "commissioning": commissioning,
        "workers": 8,
        "rows": rows,
    }
    write_json(OUT / "RAIL-PREFLIGHT.json", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
