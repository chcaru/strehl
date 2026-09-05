from __future__ import annotations

import hashlib
import inspect
import json
import sys
from pathlib import Path
from types import FrameType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
M152 = PROJECT / "experiments" / "M152-site-census"
OUT = HERE / "out" / "development-flat-resolution.json"
CAPTURE = Path(r"D:\personal\macro\flat-fields\flat-fields").resolve()
PROHIBITED = Path(r"D:\personal\macro\requests\7-aperture-pairs").resolve()
FILES = [CAPTURE / f"DSC{index:05d}.ARW" for index in range(103, 123)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if CAPTURE == PROHIBITED or PROHIBITED in CAPTURE.parents:
        raise RuntimeError("development capture resolves under prohibited holdout")
    if len(FILES) != 20 or any(not path.is_file() for path in FILES):
        raise RuntimeError("the explicit DSC00103--DSC00122 input set is incomplete")

    sys.path.insert(0, str(M152))
    try:
        import census  # type: ignore
        import census_common  # type: ignore
    finally:
        sys.path.pop(0)

    source_hashes_before = {
        name: sha256_file(M152 / name)
        for name in (
            "census.py",
            "census_common.py",
            "census-definition.json",
        )
    }
    definition, definition_hash = census_common.load_definition()
    noise = census.load_noise(definition_hash)
    noise_path = M152 / "out" / "noise-calibration.json"

    coffee = json.loads(
        (M152 / "out" / "probe-m4-commission-coffee-bubbles-flat.json").read_text(
            encoding="ascii"
        )
    )["capture"]
    if (
        Path(coffee["path"]).resolve() == CAPTURE
        or int(coffee["inventory_frame_count"]) != 19
    ):
        raise RuntimeError("M152 coffee reference did not match its frozen artifact")

    capture = {
        "capture_id": "m181-development-flat-dsc00103-dsc00122",
        "stack_id": r"flat-fields\flat-fields",
        "path": str(CAPTURE),
        "evidence_class": "DEVELOPMENT_NOT_HOLDOUT",
    }
    inventory = {
        "path": str(CAPTURE),
        "frame_count": len(FILES),
        "capture_contiguous": True,
        "settings": {"iso": [{"value": 100, "frame_count": len(FILES)}]},
    }

    snapshots: list[dict[str, Any]] = []
    seen_frames: set[int] = set()
    target_code = census.census_flat_capture.__code__
    source_lines, source_start = inspect.getsourcelines(census.census_flat_capture)
    trace_lines = [
        source_start + index
        for index, line in enumerate(source_lines)
        if line.strip() == "failing = ~valid"
    ]
    if len(trace_lines) != 1:
        raise RuntimeError("exact trace anchor did not occur once in M152 predicate")
    trace_line = trace_lines[0]

    def trace(frame: FrameType, event: str, arg: Any) -> Any:
        if (
            frame.f_code is not target_code
            or event != "line"
            or frame.f_lineno != trace_line
        ):
            return trace
        values = frame.f_locals
        required = {
            "frame_index",
            "indices",
            "ratio",
            "low_fraction",
            "high_fraction",
            "medians",
            "sigma",
            "signal_ok",
            "valid",
            "path",
            "alive",
        }
        if not required.issubset(values):
            return trace
        frame_index = int(values["frame_index"])
        if frame_index in seen_frames:
            return trace
        seen_frames.add(frame_index)
        snapshots.append(
            {
                "frame_index": frame_index,
                "file": Path(values["path"]).name,
                "grid_count": len(values["alive"]),
                "indices": np.array(values["indices"], dtype=np.int64, copy=True),
                "ratio": np.array(values["ratio"], dtype=np.float64, copy=True),
                "low_fraction": np.array(
                    values["low_fraction"], dtype=np.float64, copy=True
                ),
                "high_fraction": np.array(
                    values["high_fraction"], dtype=np.float64, copy=True
                ),
                "signal_sigma": np.array(
                    values["medians"] / values["sigma"],
                    dtype=np.float64,
                    copy=True,
                ),
                "signal_ok": np.array(values["signal_ok"], dtype=bool, copy=True),
                "valid": np.array(values["valid"], dtype=bool, copy=True),
            }
        )
        return trace

    original_capture_files = census.capture_files

    def selected_capture_files(
        requested_capture: dict[str, Any],
        _: dict[str, dict[str, Any]],
    ) -> tuple[list[Path], dict[str, Any]]:
        if requested_capture["capture_id"] != capture["capture_id"]:
            raise RuntimeError("unexpected capture substitution")
        return FILES, inventory

    census.capture_files = selected_capture_files
    old_trace = sys.gettrace()
    sys.settrace(trace)
    try:
        result = census.census_flat_capture(capture, definition, noise, {})
    finally:
        sys.settrace(old_trace)
        census.capture_files = original_capture_files

    candidate_count = int(result["initial_candidate_count"])
    if int(result["eligible_site_count"]) != candidate_count:
        raise RuntimeError(
            "trace reduction is intentionally valid only when every candidate survives"
        )
    if len(snapshots) != len(FILES):
        raise RuntimeError("line trace did not observe every evaluated frame")
    if any(len(item["indices"]) != candidate_count for item in snapshots):
        raise RuntimeError("a candidate disappeared during the traced exact predicate")

    grid_count = int(snapshots[0]["grid_count"])
    candidate_indices = snapshots[0]["indices"]
    band_max_full = np.full(grid_count, -np.inf, dtype=np.float64)
    signal_min_full = np.full(grid_count, np.inf, dtype=np.float64)
    low_max_full = np.full(grid_count, -np.inf, dtype=np.float64)
    high_max_full = np.full(grid_count, -np.inf, dtype=np.float64)
    for item in snapshots:
        indices = item["indices"]
        band_max_full[indices] = np.maximum(band_max_full[indices], item["ratio"])
        signal_min_full[indices] = np.minimum(
            signal_min_full[indices], item["signal_sigma"]
        )
        low_max_full[indices] = np.maximum(low_max_full[indices], item["low_fraction"])
        high_max_full[indices] = np.maximum(
            high_max_full[indices], item["high_fraction"]
        )
    band_max = band_max_full[candidate_indices]
    signal_min = signal_min_full[candidate_indices]
    low_max = low_max_full[candidate_indices]
    high_max = high_max_full[candidate_indices]

    stored_band = np.asarray(
        [
            site["maximum_band_over_noise_p99"]
            for site in result["eligible_sites_quality_order"]
        ],
        dtype=np.float64,
    )
    if not np.array_equal(np.sort(stored_band), np.sort(band_max)):
        raise RuntimeError("traced band ratios differ from the predicate output")
    if any(not np.all(item["valid"]) for item in snapshots):
        raise RuntimeError("the direct predicate trace contains an invalid tile")

    flat = definition["m4"]["flat_site_grid"]
    thresholds = {
        "band_ratio_strict_maximum": 1.0,
        "minimum_signal_sigma": float(flat["minimum_signal_sigma"]),
        "maximum_low_rail_fraction": float(flat["maximum_low_rail_fraction"]),
        "maximum_high_rail_fraction": float(flat["maximum_high_rail_fraction"]),
    }
    term_results = {
        "band_20_60_native_px_over_temporal_noise_p99": {
            "threshold": "<1.0",
            "failure_count": int(np.count_nonzero(band_max >= 1.0)),
            "survivor_count": int(np.count_nonzero(band_max < 1.0)),
            "max_over_frame_ratio_min": float(np.min(band_max)),
            "max_over_frame_ratio_median_nearest_rank": census.nearest_rank(
                band_max, 0.5
            ),
            "max_over_frame_ratio_p95_nearest_rank": census.nearest_rank(
                band_max, 0.95
            ),
            "max_over_frame_ratio_max": float(np.max(band_max)),
        },
        "median_signal_over_temporal_sigma": {
            "threshold": ">=10.0",
            "failure_count": int(
                np.count_nonzero(signal_min < thresholds["minimum_signal_sigma"])
            ),
            "survivor_count": int(
                np.count_nonzero(signal_min >= thresholds["minimum_signal_sigma"])
            ),
            "minimum_over_frames_and_tiles_sigma": float(np.min(signal_min)),
        },
        "low_rail_fraction": {
            "threshold": "<=0.01",
            "failure_count": int(
                np.count_nonzero(low_max > thresholds["maximum_low_rail_fraction"])
            ),
            "survivor_count": int(
                np.count_nonzero(low_max <= thresholds["maximum_low_rail_fraction"])
            ),
            "maximum_over_frames_and_tiles": float(np.max(low_max)),
        },
        "high_rail_fraction": {
            "threshold": "<=0.001",
            "failure_count": int(
                np.count_nonzero(high_max > thresholds["maximum_high_rail_fraction"])
            ),
            "survivor_count": int(
                np.count_nonzero(high_max <= thresholds["maximum_high_rail_fraction"])
            ),
            "maximum_over_frames_and_tiles": float(np.max(high_max)),
        },
    }

    source_hashes_after = {
        name: sha256_file(M152 / name) for name in source_hashes_before
    }
    if source_hashes_after != source_hashes_before:
        raise RuntimeError("an M152 predicate source changed during the run")

    artifact = {
        "schema": "m181-development-flat-resolution-v1",
        "method": {
            "authoritative_callable": "M152 census.census_flat_capture",
            "predicate_source_modified": False,
            "input_adapter_only": (
                "capture_files bound to the explicit DSC00103--DSC00122 list"
            ),
            "line_trace_semantics": (
                "read-only observation of exact predicate locals; return values "
                "and control flow unchanged"
            ),
            "m152_source_sha256": source_hashes_before,
            "m152_noise_path": str(noise_path),
            "m152_noise_file_sha256": sha256_file(noise_path),
            "m152_noise_content_sha256": noise["content_sha256"],
            "m152_definition_sha256": definition_hash,
        },
        "capture": {
            "path": str(CAPTURE),
            "frame_count": len(FILES),
            "first_file": FILES[0].name,
            "last_file": FILES[-1].name,
            "decoded_input_count": len(result["decoded_inputs"]),
            "decoded_inputs": [
                {
                    "file": row["file"],
                    "decoded_green_sha256": row["decoded_green_sha256"],
                }
                for row in result["decoded_inputs"]
            ],
        },
        "m152_coffee_reference": {
            "path": coffee["path"],
            "frame_count": int(coffee["inventory_frame_count"]),
            "eligible_tile_count": int(coffee["eligible_site_count"]),
            "same_capture": False,
        },
        "thresholds": thresholds,
        "term_results": term_results,
        "initial_candidate_count": candidate_count,
        "eligible_tile_count": int(result["eligible_site_count"]),
        "development_quota": 100,
        "reaches_development_quota": int(result["eligible_site_count"]) >= 100,
        "all_frames_evaluated": bool(result["all_frames_evaluated"]),
        "first_failure_counts": result["first_failure_counts"],
        "survivor_trajectory": result["survivor_trajectory"],
        "trace_band_distribution_exactly_matches_predicate_output": True,
        "prohibited_root_opened": False,
        "verdict": "DEVELOPMENT_FLAT_ELIGIBLE",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="ascii",
    )
    print(
        f"ELIGIBLE={artifact['eligible_tile_count']}/{candidate_count}; "
        f"quota={artifact['reaches_development_quota']}"
    )
    for name, values in term_results.items():
        print(f"{name}: {json.dumps(values, sort_keys=True)}")
    print(
        "coffee_same_capture="
        f"{artifact['m152_coffee_reference']['same_capture']}; "
        f"coffee_eligible={artifact['m152_coffee_reference']['eligible_tile_count']}"
    )
    print(f"artifact={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
