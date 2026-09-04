"""Reproduce the M169 commissioning failure from untouched M161 source."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
M161 = REPO / "experiments" / "M161-m3-ratification"
OUT = HERE / "out" / "m161-source-reproduction.json"
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


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    sys.path.insert(0, str(M161))
    import commission_m3_v2 as commission  # noqa: PLC0415
    import m3_checker_v2 as checker  # noqa: PLC0415

    source_hashes = {
        name: checker.sha256_file(M161 / name) for name in EXPECTED
    }
    if source_hashes != EXPECTED:
        raise RuntimeError(f"M161 source hashes changed: {source_hashes}")

    definition, definition_sha = checker.load_checker_definition()
    combined = (
        lambda output, offsets, step: output
        + commission.rim_delta(offsets, step, 0.06)
        + commission.two_sided_veil_delta(offsets, step, 0.06)
    )
    combined_patch = lambda patch, step: commission.patch_delta(
        patch, step, rim=0.06, veil=0.06
    )
    improved = (
        lambda output, offsets, step: output
        + commission.rim_delta(offsets, step, 0.005)
        + commission.two_sided_veil_delta(offsets, step, 0.005)
    )
    improved_patch = lambda patch, step: commission.patch_delta(
        patch, step, rim=0.005, veil=0.005
    )
    degraded, _ = commission.arm_summary(
        "planted_6pct_rim_and_veil",
        combined,
        combined_patch,
        definition,
        0.06,
    )
    repaired, _ = commission.arm_summary(
        "planted_improvement_0_5pct_rim_and_veil",
        improved,
        improved_patch,
        definition,
        0.005,
    )
    checks = {
        "definition_hash_matches": definition_sha
        == EXPECTED["m3-checker-definition-v2.json"],
        "degradation_is_red": degraded["verdict"] == "FAIL",
        "improvement_moves_down": repaired["median_h_e"]
        < degraded["median_h_e"]
        and repaired["median_v_e"] < degraded["median_v_e"],
        "improvement_fails_only_median_h_e": repaired["verdict"] == "FAIL"
        and repaired["checks"]["median_h_e"] is False
        and all(
            passed
            for name, passed in repaired["checks"].items()
            if name != "median_h_e"
        ),
        "improvement_median_h_e_exact": abs(
            repaired["median_h_e"] - 0.010413357351919823
        )
        <= 1e-12,
    }
    result = {
        "schema": "m169-m3-m161-source-reproduction-v1",
        "source_directory": str(M161),
        "source_hashes": source_hashes,
        "candidate_outputs_opened": 0,
        "comparator_outputs_opened": 0,
        "capture_pixels_opened": 0,
        "degradation": degraded,
        "improvement": repaired,
        "checks": checks,
        "verdict": "REPRODUCED" if all(checks.values()) else "NOT_REPRODUCED",
    }
    write_json(OUT, result)
    print(result["verdict"])
    print(
        "degradation h50=%.15f v50=%.15f verdict=%s"
        % (
            degraded["median_h_e"],
            degraded["median_v_e"],
            degraded["verdict"],
        )
    )
    print(
        "improvement h50=%.15f v50=%.15f verdict=%s "
        "failed=median_h_e"
        % (
            repaired["median_h_e"],
            repaired["median_v_e"],
            repaired["verdict"],
        )
    )
    return 0 if result["verdict"] == "REPRODUCED" else 6


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
