from __future__ import annotations

import json
from pathlib import Path

from checker import DEFINITIONS_SHA256


ROOT = Path(__file__).resolve().parent
RESULT = ROOT / "full-population-results.json"


def main() -> int:
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["protocol"] == "M151-M5-full-population-v1"
    assert result["definitions_sha256"] == DEFINITIONS_SHA256
    area = result["active_area_arithmetic"]
    assert area["width"] == 7028
    assert area["height"] == 4688
    assert area["candidate_columns"] == 54
    assert area["candidate_rows"] == 36
    assert area["candidate_tiles"] == 1944
    assert area["right_remainder_px"] == 116
    assert area["bottom_remainder_px"] == 80

    expected = {
        "burned_grid_sw4_exact_55": (0, 0),
        "burned_grid_sw10_exact_27": (0, 0),
        "tilted_sw10_full_92": (69, 53),
        "tilted_sw10_best_27": (328, 275),
    }
    for name, (point_count, eligible_count) in expected.items():
        arm = result["arms"][name]
        assert arm["site_count"] == 1944
        assert arm["point_eligible_count"] == point_count
        assert arm["bootstrap_eligible_count"] == eligible_count
        assert arm["effective_wilson_minimum_met"] == (eligible_count >= 133)
        if eligible_count:
            assert arm["all_success_wilson_lcb95"] > 0.0
        else:
            assert arm["all_success_wilson_lcb95"] is None
    best = result["arms"]["tilted_sw10_best_27"]
    assert best["start_node"] == 9
    assert best["end_node_inclusive"] == 35
    assert best["windows_evaluated"] == 66
    assert best["all_success_wilson_lcb95"] >= 0.98

    prior = result["prior_64_site_design"]
    assert prior["kind"] == "fixed grid subsample"
    assert prior["sites"] == 64
    print(
        "full-population verified: 1944 candidates; "
        "exact-27 tilted eligibility 275"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
