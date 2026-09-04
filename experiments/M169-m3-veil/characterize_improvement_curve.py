"""Characterize the frozen M161 combined rim-and-veil response.

This is a synthetic transfer measurement, not a threshold change, a new
commissioning assertion, or an M3 product score. It imports only hash-verified,
untouched M161 source and opens no capture, candidate, or comparator pixels.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
M161 = REPO / "experiments" / "M161-m3-ratification"
OUT = HERE / "out" / "improvement-response-curve.json"
EXPECTED = {
    "m3-checker-definition-v2.json": (
        "578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca"
    ),
    "m3_checker_v2.py": (
        "05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda"
    ),
    "commission_m3_v2.py": (
        "342ea2d9064130117f9173ff2311a47465760519251f2c473f3a8ea8d34952da"
    ),
}
AMPLITUDE_GRID = (
    0.0,
    0.001,
    0.002,
    0.003,
    0.004,
    0.0045,
    0.005,
    0.006,
    0.01,
    0.02,
    0.04,
    0.06,
)
BISECTION_ITERATIONS = 16


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)


def main() -> int:
    source_hashes = {name: sha256_file(M161 / name) for name in EXPECTED}
    if source_hashes != EXPECTED:
        raise RuntimeError(f"M161 source hashes changed: {source_hashes}")

    sys.path.insert(0, str(M161))
    import commission_m3_v2 as commission  # noqa: PLC0415
    import m3_checker_v2 as checker  # noqa: PLC0415

    definition, definition_sha = checker.load_checker_definition()
    if definition_sha != EXPECTED["m3-checker-definition-v2.json"]:
        raise RuntimeError(f"M161 definition hash changed: {definition_sha}")
    median_h_gate = float(definition["bars"]["median_h_e_max"])

    cache: dict[float, tuple[dict[str, Any], list[dict[str, Any]]]] = {}

    def evaluate(
        amplitude: float,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        amplitude = float(amplitude)
        if amplitude not in cache:
            profile_plant = (
                lambda output, offsets, step: output
                + commission.rim_delta(offsets, step, amplitude)
                + commission.two_sided_veil_delta(offsets, step, amplitude)
            )
            patch_plant = lambda patch, step: commission.patch_delta(
                patch, step, rim=amplitude, veil=amplitude
            )
            summary, rows = commission.arm_summary(
                f"characterization_{amplitude:.12f}",
                profile_plant,
                patch_plant,
                definition,
                amplitude,
            )
            cache[amplitude] = (summary, rows)
        return cache[amplitude]

    def compact(amplitude: float) -> dict[str, Any]:
        summary, _ = evaluate(amplitude)
        return {
            "amplitude_fraction_of_step": amplitude,
            "amplitude_percent_of_step": 100.0 * amplitude,
            "median_h_e": summary["median_h_e"],
            "median_v_e": summary["median_v_e"],
            "maximum_max_h_v": summary["maximum_max_h_v"],
            "median_h_gate_passes": summary["median_h_e"] <= median_h_gate,
            "all_registered_gates_pass": summary["verdict"] == "PASS",
        }

    curve = [compact(amplitude) for amplitude in AMPLITUDE_GRID]
    clean_summary, clean_rows = evaluate(0.0)
    registered_summary, registered_rows = evaluate(0.005)
    six_percent_summary, _ = evaluate(0.06)

    low = 0.0
    high = 0.005
    if evaluate(low)[0]["median_h_e"] > median_h_gate:
        raise RuntimeError("clean null does not bracket the median h_e gate")
    if evaluate(high)[0]["median_h_e"] <= median_h_gate:
        raise RuntimeError("registered 0.5% arm does not bracket the gate")
    for _ in range(BISECTION_ITERATIONS):
        midpoint = (low + high) / 2.0
        if evaluate(midpoint)[0]["median_h_e"] <= median_h_gate:
            low = midpoint
        else:
            high = midpoint

    low_summary, _ = evaluate(low)
    high_summary, _ = evaluate(high)
    paired_h_deltas = np.asarray(
        [
            registered["h_e"] - clean["h_e"]
            for clean, registered in zip(
                clean_rows, registered_rows, strict=True
            )
        ],
        dtype=np.float64,
    )
    checks = {
        "source_hashes_match": source_hashes == EXPECTED,
        "clean_null_matches_frozen_run": close(
            clean_summary["median_h_e"], 0.0029430516302103543
        ),
        "registered_improvement_matches_frozen_run": close(
            registered_summary["median_h_e"], 0.010413357351919823
        ),
        "six_percent_arm_matches_frozen_run": close(
            six_percent_summary["median_h_e"], 0.12033896557593107
        ),
        "clean_null_passes_median_h_gate": (
            clean_summary["median_h_e"] <= median_h_gate
        ),
        "registered_improvement_fails_median_h_gate": (
            registered_summary["median_h_e"] > median_h_gate
        ),
        "all_registered_sites_move_up_from_clean": bool(
            np.all(paired_h_deltas > 0.0)
        ),
        "curve_is_monotone_on_fixed_grid": all(
            later["median_h_e"] >= earlier["median_h_e"]
            for earlier, later in zip(curve, curve[1:])
        ),
        "crossing_is_bracketed": (
            low_summary["median_h_e"]
            <= median_h_gate
            < high_summary["median_h_e"]
        ),
    }
    result = {
        "schema": "m169-m3-improvement-response-characterization-v1",
        "purpose": (
            "characterization only; no threshold, plant, assertion, or score "
            "was changed"
        ),
        "source_directory": str(M161),
        "source_hashes": source_hashes,
        "master_seed": commission.MASTER_SEED,
        "site_count": commission.SITE_COUNT,
        "noise_sigma_fraction_of_step": commission.NOISE_SIGMA_FRACTION,
        "median_h_e_gate_unchanged": median_h_gate,
        "amplitude_grid": list(AMPLITUDE_GRID),
        "curve": curve,
        "crossing_bracket": {
            "largest_tested_passing_amplitude_fraction": low,
            "largest_tested_passing_amplitude_percent": 100.0 * low,
            "passing_median_h_e": low_summary["median_h_e"],
            "smallest_tested_failing_amplitude_fraction": high,
            "smallest_tested_failing_amplitude_percent": 100.0 * high,
            "failing_median_h_e": high_summary["median_h_e"],
            "bisection_iterations": BISECTION_ITERATIONS,
        },
        "clean_vs_registered_improvement": {
            "clean_median_h_e": clean_summary["median_h_e"],
            "registered_0_5pct_median_h_e": registered_summary["median_h_e"],
            "median_h_e_increase": (
                registered_summary["median_h_e"]
                - clean_summary["median_h_e"]
            ),
            "sites_with_strict_h_e_increase": int(
                np.count_nonzero(paired_h_deltas > 0.0)
            ),
            "site_count": int(paired_h_deltas.size),
            "median_paired_h_e_increase": float(np.median(paired_h_deltas)),
            "minimum_paired_h_e_increase": float(np.min(paired_h_deltas)),
            "maximum_paired_h_e_increase": float(np.max(paired_h_deltas)),
        },
        "interpretation": (
            "B: the clean-noise null is well below the median h_e gate, while "
            "the registered 0.5% combined rim-and-veil plant produces a "
            "strictly larger h_e at every paired synthetic site and crosses "
            "the gate. This rejects a 0.0104 clean-floor explanation for this "
            "commissioning failure; it does not adjudicate whether M174 should "
            "change the registered assertion."
        ),
        "candidate_outputs_opened": 0,
        "comparator_outputs_opened": 0,
        "capture_pixels_opened": 0,
        "absolute_timing": "QUARANTINED_AND_NOT_REPORTED",
        "checks": checks,
        "verdict": "CHARACTERIZED" if all(checks.values()) else "CHECK_FAILED",
    }
    write_json(OUT, result)

    crossing = result["crossing_bracket"]
    paired = result["clean_vs_registered_improvement"]
    print(
        "CLEAN h50=%.15f gate=%.6f PASS"
        % (paired["clean_median_h_e"], median_h_gate)
    )
    print(
        "REGISTERED_0_5PCT h50=%.15f gate=%.6f FAIL"
        % (paired["registered_0_5pct_median_h_e"], median_h_gate)
    )
    print(
        "PAIRED_INCREASE sites=%d/%d median=%.15f"
        % (
            paired["sites_with_strict_h_e_increase"],
            paired["site_count"],
            paired["median_paired_h_e_increase"],
        )
    )
    print(
        "CROSSING_BRACKET pass=%.12f%% h50=%.15f "
        "fail=%.12f%% h50=%.15f"
        % (
            crossing["largest_tested_passing_amplitude_percent"],
            crossing["passing_median_h_e"],
            crossing["smallest_tested_failing_amplitude_percent"],
            crossing["failing_median_h_e"],
        )
    )
    print(result["verdict"])
    return 0 if result["verdict"] == "CHARACTERIZED" else 7


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
