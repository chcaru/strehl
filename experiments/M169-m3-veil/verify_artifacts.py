"""Verify M169 M3 artifacts without opening capture or product pixels."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from m3_checker_v2 import sha256_file


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
EXPECTED_SOURCE_HASHES = {
    "m3-checker-definition-v2.json": (
        "578022e6eeefecce60a00191024e9ffd4dc3c621410b398709b3f92b987b67ca"
    ),
    "m3_checker_v2.py": (
        "05d291c8c24712d46666e9ed398f39cb982fa3b4c918a7e0cfcdee200dec2eda"
    ),
}
EXPECTED_M161_SOURCE_HASHES = {
    **EXPECTED_SOURCE_HASHES,
    "commission_m3_v2.py": (
        "342ea2d9064130117f9173ff2311a47465760519251f2c473f3a8ea8d34952da"
    ),
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12)


def main() -> int:
    for relative, expected in EXPECTED_SOURCE_HASHES.items():
        require(
            sha256_file(HERE / relative) == expected,
            f"source hash mismatch: {relative}",
        )

    feasibility = read_json(OUT / "capture-feasibility.json")
    require(feasibility["verdict"] == "PASS", "capture feasibility is not PASS")
    require(
        feasibility["eligible_edges_overall"] == 1233,
        "eligible edge count changed",
    )
    require(feasibility["selected_site_count"] == 500, "denominator changed")
    require(
        feasibility["selected_site_counts"]
        == {
            "m3-chia": 133,
            "m3-duck-tape": 133,
            "m3-flower-fern": 132,
            "m3-razor-control": 102,
        },
        "subject allocation changed",
    )
    require(
        feasibility["pixel_files_opened"] == 0,
        "feasibility unexpectedly opened pixel files",
    )

    historic_commission = read_json(OUT / "commission-v2.json")
    require(
        historic_commission["verdict"]
        == "NOT_ADMITTED_COMMISSIONING_FAILED",
        "historical v2 commissioning verdict changed",
    )
    require(
        historic_commission["failed_assertions"] == ["improved_arm_passes"],
        "historical v2 commissioning failure set changed",
    )
    require(
        historic_commission["capture_pixels_opened"] == 0
        and historic_commission["candidate_outputs_opened"] == 0
        and historic_commission["comparator_outputs_opened"] == 0,
        "historical commissioning opened protected pixels",
    )
    historic_arms = {
        row["name"]: row for row in historic_commission["arms"]
    }
    improved = historic_arms["planted_improvement_0_5pct_rim_and_veil"]
    require(
        close(improved["median_h_e"], 0.010413357351919823),
        "registered improvement median h_e changed",
    )
    require(
        improved["checks"]["median_h_e"] is False
        and improved["verdict"] == "FAIL",
        "registered improvement no longer exhibits the commissioning failure",
    )
    historic_digest_record = (OUT / "commission-v2.sha256").read_text(
        encoding="ascii"
    ).split()[0]
    require(
        historic_digest_record == sha256_file(OUT / "commission-v2.json"),
        "historical commission artifact digest mismatch",
    )

    registration = read_json(HERE / "commissioning-registration-v3.json")
    definition = read_json(HERE / "m3-checker-definition-v2.json")
    require(
        registration["authority"]["commit"]
        == "a9176fef45ce5bc8306ef690eafc7f51bc2d5ddd"
        and registration["authority"]["verdict"] == "B_ASSERTION_DEFECT",
        "M174 registration authority changed",
    )
    require(
        registration["status"] == "REGISTERED_BEFORE_V3_EXECUTION"
        and registration["score_authorized"] is False,
        "v3 registration status or score prohibition changed",
    )
    require(
        registration["unchanged_gates"] == definition["bars"],
        "v3 registration changed an M3 gate",
    )
    require(
        registration["boundary_reduction_arm"]["expected_gate_result"]
        == "FAIL_MEDIAN_H_E"
        and registration["boundary_reduction_arm"][
            "expected_result_assertion"
        ]
        == "improved_arm_fails_median_h_e"
        and registration["boundary_reduction_arm"][
            "retained_movement_assertions"
        ]
        == [
            "improvement_reduces_h_by_at_least_5pp",
            "improvement_reduces_v_by_at_least_5pp",
        ],
        "M174 boundary-arm registration changed",
    )
    require(
        close(
            registration["green_recovery_arm"][
                "rim_component_fraction_of_step"
            ],
            0.0025,
        )
        and close(
            registration["green_recovery_arm"][
                "veil_component_fraction_of_step"
            ],
            0.0025,
        )
        and registration["green_recovery_arm"][
            "selection_uses_observed_failure_or_crossing"
        ]
        is False,
        "green recovery is not the design-derived 0.25%-each arm",
    )

    commission = read_json(OUT / "commission-v3.json")
    require(
        commission["schema"] == "m169-m3-checker-commission-v3"
        and commission["verdict"] == "PASS"
        and commission["failed_assertions"] == [],
        "v3 battery is not commissioned",
    )
    require(
        len(commission["assertions"]) == 21
        and all(commission["assertions"].values()),
        "not all 21 v3 commissioning assertions pass",
    )
    require(
        commission["registration_sha256"]
        == sha256_file(HERE / "commissioning-registration-v3.json")
        and commission["commission_source_sha256"]
        == sha256_file(HERE / "full_commission.py"),
        "v3 commissioning source or registration digest changed",
    )
    require(
        commission["adjudication"] == registration["authority"],
        "v3 commissioning is not bound to its registered adjudication",
    )
    require(
        commission["capture_pixels_opened"] == 0
        and commission["candidate_outputs_opened"] == 0
        and commission["comparator_outputs_opened"] == 0,
        "v3 commissioning opened protected pixels",
    )
    arms = {row["name"]: row for row in commission["arms"]}
    require(
        "planted_improvement_0_5pct_rim_and_veil" not in arms,
        "ambiguous historical arm name survived in v3",
    )
    boundary = arms["paired_reduction_to_0_5pct_each_boundary_challenge"]
    boundary_failed = sorted(
        name for name, passed in boundary["checks"].items() if not passed
    )
    require(
        boundary["expected_gate_result"] == "FAIL_MEDIAN_H_E"
        and boundary["verdict"] == "FAIL"
        and boundary_failed == ["median_h_e"]
        and close(boundary["median_h_e"], 0.010413357351919823),
        "boundary reduction does not have its registered result",
    )
    green = arms["paired_reduction_to_0_25pct_each_green_control"]
    require(
        green["expected_gate_result"] == "PASS_ALL_GATES"
        and green["verdict"] == "PASS"
        and all(green["checks"].values())
        and close(green["median_h_e"], 0.005648873327640571)
        and close(green["median_v_e"], 0.0032225916705620077),
        "green recovery control does not pass every gate",
    )
    require(
        commission["assertions"][
            "improvement_reduces_h_by_at_least_5pp"
        ]
        and commission["assertions"][
            "improvement_reduces_v_by_at_least_5pp"
        ]
        and commission["assertions"][
            "improved_arm_fails_median_h_e"
        ]
        and commission["assertions"]["green_recovery_passes_all_gates"]
        and "improved_arm_passes" not in commission["assertions"],
        "v3 improvement assertions are not correctly registered",
    )
    digest_record = (OUT / "commission-v3.sha256").read_text(
        encoding="ascii"
    ).split()[0]
    require(
        digest_record == sha256_file(OUT / "commission-v3.json"),
        "v3 commission artifact digest mismatch",
    )

    controls = read_json(OUT / "anchored-controls.json")
    require(controls["verdict"] == "PASS", "anchored controls did not pass")
    require(
        controls["missing_anchor_probe"] == "HARD_ERROR_CONFIRMED",
        "missing-anchor guard was not demonstrated",
    )
    null = controls["arms"]["flat_residual_null"]
    defect = controls["arms"]["planted_defect"]
    repaired = controls["arms"]["planted_improvement"]
    require(
        null["verdict"] == "PASS"
        and null["affected_edge_count"] == 0
        and close(null["maximum_max_h_v"], 0.0),
        "flat-residual null is not exactly clean",
    )
    require(
        defect["verdict"] == "FAIL"
        and defect["affected_edge_count"] == 500
        and close(defect["median_v_e"], 0.05448648648648648),
        "line-anchored veil defect is not RED at the expected magnitude",
    )
    require(
        repaired["verdict"] == "PASS"
        and repaired["affected_edge_count"] == 0
        and close(repaired["median_v_e"], 0.004540540540540539),
        "line-anchored improvement is not clean at the expected magnitude",
    )
    require(
        controls["literal_flat_no_edge_domain_guard"]["status"]
        == "INVALID_OUTPUT_CHARGED"
        and controls["literal_flat_no_edge_domain_guard"]["reason"]
        == "nonpositive_source_step",
        "literal no-edge domain guard changed",
    )

    reproduction = read_json(OUT / "m161-source-reproduction.json")
    require(
        reproduction["verdict"] == "REPRODUCED",
        "untouched M161 source did not reproduce the failure",
    )
    require(
        reproduction["improvement"]["checks"]["median_h_e"] is False
        and close(
            reproduction["improvement"]["median_h_e"],
            0.010413357351919823,
        ),
        "untouched M161 improvement result changed",
    )

    curve = read_json(OUT / "improvement-response-curve.json")
    require(
        curve["verdict"] == "CHARACTERIZED",
        "improvement response curve did not characterize cleanly",
    )
    require(
        curve["source_hashes"] == EXPECTED_M161_SOURCE_HASHES,
        "response curve did not use the frozen M161 source",
    )
    require(
        curve["capture_pixels_opened"] == 0
        and curve["candidate_outputs_opened"] == 0
        and curve["comparator_outputs_opened"] == 0,
        "response characterization opened protected pixels",
    )
    clean_vs_improvement = curve["clean_vs_registered_improvement"]
    require(
        close(
            clean_vs_improvement["clean_median_h_e"],
            0.0029430516302103543,
        )
        and close(
            clean_vs_improvement["registered_0_5pct_median_h_e"],
            0.010413357351919823,
        ),
        "clean or registered-improvement h_e changed",
    )
    require(
        clean_vs_improvement["sites_with_strict_h_e_increase"] == 500
        and clean_vs_improvement["site_count"] == 500,
        "registered improvement did not move all paired sites above clean",
    )
    crossing = curve["crossing_bracket"]
    require(
        close(
            crossing["largest_tested_passing_amplitude_fraction"],
            0.004777984619140625,
        )
        and close(
            crossing["smallest_tested_failing_amplitude_fraction"],
            0.004778060913085937,
        )
        and crossing["passing_median_h_e"] <= 0.01
        < crossing["failing_median_h_e"],
        "median h_e crossing bracket changed",
    )

    measurement = read_json(OUT / "measurement-verdict.json")
    require(
        measurement["verdict"] == "UNMEASURED_COMPARATOR_QUALIFICATION",
        "measurement refusal changed",
    )
    require(measurement["score"] is None, "a score was manufactured")
    require(
        measurement["confidence_interval"] == "NO CI",
        "missing explicit NO CI",
    )
    require(
        measurement["pixel_files_opened_by_m169"] == 0,
        "measurement opened protected pixels",
    )
    require(
        measurement["recommissioning"]["full_m169_v3"] == "PASS"
        and measurement["scorecard_readiness"]["m3_instrument_status"]
        == "COMMISSIONED"
        and measurement["scorecard_readiness"]["axis_score_status"]
        == "UNMEASURED_COMPARATOR_QUALIFICATION",
        "instrument/axis status distinction changed",
    )
    require(
        measurement["axis_contract"]["kind"]
        == "CONJUNCTIVE_ABSOLUTE_AND_COMPARATIVE"
        and measurement["axis_contract"][
            "absolute_candidate_result_is_full_axis_score"
        ]
        is False,
        "M3 absolute/comparator contract changed",
    )

    print("PASS")
    print("capture_feasibility=PASS denominator=500 eligible=1233")
    print(
        "commission=PASS failed_assertions=0 "
        "boundary_expected=FAIL_MEDIAN_H_E "
        "boundary_h50=0.010413357351919823"
    )
    print(
        "green_recovery=PASS amplitude_each=0.0025 "
        "h50=0.005648873327640571 v50=0.0032225916705620077"
    )
    print(
        "anchored_controls=PASS null=0.000000 "
        "defect_v50=0.05448648648648648 "
        "improvement_v50=0.004540540540540539"
    )
    print(
        "response_curve=CHARACTERIZED clean_h50=0.0029430516302103543 "
        "registered_h50=0.010413357351919823 crossing_pct="
        "[0.4777984619140625,0.47780609130859375]"
    )
    print("axis_contract=CONJUNCTIVE_ABSOLUTE_AND_COMPARATIVE")
    print(
        "axis_status=UNMEASURED_COMPARATOR_QUALIFICATION "
        "blockers=(a)(b)(d)"
    )
    print("score=NO SCORE confidence_interval=NO CI")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
