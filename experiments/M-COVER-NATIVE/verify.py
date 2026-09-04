from __future__ import annotations

import sys
from pathlib import Path

import geometry_census
import run


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    pre = run.read_json(run.OUT / "PREFLIGHT.json")
    require(pre["phase"] == "A_Q1_Q2_ONLY", "wrong registered phase")
    require(len(pre["arms"]) == 8, "eight arms were not preregistered")
    require(run.sha256(run.BINARY) == run.BINARY_SHA256, "frozen binary moved")
    require(
        run.cache_snapshot(run.PRIVATE_CACHE) == pre["private_cache"],
        "private cache moved",
    )
    require(
        run.snapshot_files(run.frozen_dependency_paths()) == pre["frozen_dependencies"],
        "frozen dependency moved",
    )

    render_path = run.OUT / "RENDER-MANIFEST.json"
    if not render_path.exists():
        require(
            not any(run.RENDERS.glob("*.tiff")),
            "render exists before the preregistered render manifest",
        )
        print("pre-render verification passed")
        return 0

    renders = run.read_json(render_path)
    require(renders["control"]["returncode"] == 0, "Scale control failed")
    require(renders["control"]["hash_matches"], "Scale control hash mismatch")
    require(renders["crop_interpretable"], "Crop was rendered but is not interpretable")
    require(len(renders["crop_records"]) == 8, "expected eight Crop records")
    for row in renders["crop_records"]:
        require(row["returncode"] == 0, f"{row['name']}: render failed")
        require(row["cache_unchanged"], f"{row['name']}: cache changed")
        require(
            row["same_solve_as_frozen_scale"]["all_match"],
            f"{row['name']}: solve/coverage mismatch",
        )
        require(row["shape_matches_crop_rect"], f"{row['name']}: Crop shape mismatch")

    q1 = run.read_json(run.OUT / "Q1-RESULTS.json")
    require(q1["commissioned_before_real_values"], "ECC was not commissioned first")
    require(q1["audit_exception"] is None, "unchanged audit_geometry.main() failed")
    require(len(q1["rows"]) == 8, "expected eight Q1 rows")
    for row in q1["rows"]:
        require(row["crop_ecc"] is not None, f"{row['arm']}: ECC result missing")
        require(
            row["crop_non_translation"]["status"] == "MEASURED",
            f"{row['arm']}: residual measurement missing",
        )
        require(
            row["crop_ecc"]["scorecard_scale_pass"],
            f"{row['arm']}: native-scale threshold did not clear",
        )
        require(
            row["crop_ecc"]["scorecard_rotation_pass"],
            f"{row['arm']}: rotation threshold did not clear",
        )
    require(
        q1["all_crop_geometry_clauses_pass"]
        == all(row["crop_all_geometry_clauses_pass"] for row in q1["rows"]),
        "Q1 aggregate disagrees with its rows",
    )

    q2 = run.read_json(run.OUT / "Q2-GEOMETRY.json")
    require(
        q2["all_outputs_large_enough_for_common_shape"],
        "a Crop output cannot hold the common shape",
    )
    require(not q2["all_outputs_native_size"], "Crop unexpectedly emitted native size")
    require(
        q2["all_common_overlap_retained_at_least_99_percent"],
        "fixed common overlap fell below 99%",
    )
    require(q2["all_sites_survive_at_least_80_percent"], "site survival fell below 80%")
    require(
        q2["all_differential_attrition_at_most_2pp"],
        "differential attrition exceeded 2pp",
    )

    independent = run.read_json(run.OUT / "INDEPENDENT-VERIFICATION.json")
    require(
        independent["verdict"] == "DEFECTS_FOUND_CONCLUSION_SURVIVES",
        "independent Phase A verdict moved",
    )
    require(
        independent["phase_a_ruling"]["crop_passes_specific_native_scale_rule"],
        "independent review no longer confirms the Crop scale pass",
    )
    require(
        not independent["phase_a_ruling"]["crop_is_native_size"],
        "independent review unexpectedly calls Crop native-size",
    )
    require(
        not independent["admission"]["frozen_residual_reader_admitted"],
        "known-bad residual reader was promoted",
    )
    require(
        independent["phase_a_ruling"]["residual_status"]
        == "UNMEASURED_BY_ADMITTED_INSTRUMENT",
        "residual status moved without a commissioned replacement",
    )
    require(
        len(independent["supersedes_artifact_interpretations"]) == 3,
        "known semantic collisions are no longer explicitly superseded",
    )
    require(
        q1["all_crop_geometry_clauses_pass"] is False,
        "legacy Q1 aggregate moved; review its superseding interpretation",
    )
    require(
        all(
            row["crop_non_translation"]["status"] == "MEASURED"
            for row in q1["rows"]
        ),
        "legacy residual status moved; review its superseding interpretation",
    )
    require(
        all(row["exact_integer_scene_mapping_established"] for row in q2["rows"]),
        "legacy array-mapping field moved; review its superseding interpretation",
    )

    commission = run.read_json(geometry_census.COMMISSION_PATH)
    require(commission["status"] == "COMMISSIONED", "Q3 commission status moved")
    require(commission["all_passed"], "Q3 commission did not pass")
    require(
        commission["temporary_files_removed"],
        "Q3 commissioning temporary files remain",
    )
    require(
        commission["script_sha256"]
        == run.sha256(Path(geometry_census.__file__)),
        "geometry_census.py moved after commissioning",
    )
    require(
        [case["name"] for case in commission["cases"]]
        == ["matching_dimensions_null", "known_smaller_crop"],
        "Q3 commissioning cases moved",
    )
    null, smaller = commission["cases"]
    require(
        null["passed"]
        and null["expected_verdict"] == "GREEN"
        and null["classification"]["verdict"] == "GREEN"
        and null["classification"]["width_pixels_lost"] == 0
        and null["classification"]["height_pixels_lost"] == 0,
        "matching-dimensions null did not stay GREEN",
    )
    require(
        smaller["passed"]
        and smaller["expected_verdict"] == "RED"
        and smaller["classification"]["verdict"] == "RED"
        and smaller["classification"]["width_pixels_lost"] == 2
        and smaller["classification"]["height_pixels_lost"] == 2,
        "known-smaller TIFF did not go RED",
    )

    census = run.read_json(geometry_census.CENSUS_PATH)
    require(census["status"] == "Q3_COMPLETE", "Q3 census status moved")
    require(census["arms"] == list(geometry_census.ARMS), "Q3 arm list moved")
    require(census["row_count"] == 8, "Q3 census does not contain eight rows")
    require(
        [row["arm"] for row in census["rows"]] == list(geometry_census.ARMS),
        "Q3 rows are not the exact eight frozen arms in order",
    )
    require(
        census["native_size_fail_count"] == 8,
        "Q3 native-size result is no longer RED 8/8",
    )
    require(
        census["worst_field_loss_arm"] == "m2-second-first16",
        "Q3 worst field-loss arm moved",
    )
    require(
        census["all_manifest_header_hash_agree"],
        "Q3 TIFF/header/manifest/hash agreement failed",
    )
    require(
        census["all_dimensions_equal_twice_banner_crop_rect"],
        "Q3 TIFF dimensions no longer equal twice the banner Crop rectangles",
    )

    for row in census["rows"]:
        width = row["crop_width"]
        height = row["crop_height"]
        width_lost = row["width_pixels_lost"]
        height_lost = row["height_pixels_lost"]
        retained_area = row["retained_area_pixels"]
        area_lost = row["area_pixels_lost"]
        require(
            width + width_lost == geometry_census.NATIVE_WIDTH,
            f"{row['arm']}: width-loss invariant failed",
        )
        require(
            height + height_lost == geometry_census.NATIVE_HEIGHT,
            f"{row['arm']}: height-loss invariant failed",
        )
        require(
            row["left_pixels_lost"] + row["right_pixels_lost"] == width_lost,
            f"{row['arm']}: horizontal side-loss invariant failed",
        )
        require(
            row["top_pixels_lost"] + row["bottom_pixels_lost"] == height_lost,
            f"{row['arm']}: vertical side-loss invariant failed",
        )
        require(
            retained_area == width * height,
            f"{row['arm']}: retained-area invariant failed",
        )
        require(
            retained_area + area_lost == geometry_census.NATIVE_AREA,
            f"{row['arm']}: area-loss invariant failed",
        )
        require(
            row["percent_width_loss"]
            == geometry_census.percent(width_lost, geometry_census.NATIVE_WIDTH),
            f"{row['arm']}: derived width percentage moved",
        )
        require(
            row["percent_height_loss"]
            == geometry_census.percent(height_lost, geometry_census.NATIVE_HEIGHT),
            f"{row['arm']}: derived height percentage moved",
        )
        require(
            row["percent_area_loss"]
            == geometry_census.percent(area_lost, geometry_census.NATIVE_AREA),
            f"{row['arm']}: derived area-loss percentage moved",
        )
        require(
            row["retained_area_percent"]
            == geometry_census.percent(retained_area, geometry_census.NATIVE_AREA),
            f"{row['arm']}: derived retained-area percentage moved",
        )
        require(
            row["common_overlap_retained_pixels"]
            == row["common_overlap_area_pixels"]
            and row["common_overlap_geometric_retention_percent"]
            == "100.000000000",
            f"{row['arm']}: common-overlap geometric containment moved",
        )
        require(
            row["native_size_verdict"] == "RED",
            f"{row['arm']}: native-size verdict moved",
        )

    require(
        census == geometry_census.build_census(),
        "Q3 census no longer reproduces from TIFF headers and committed manifest",
    )

    provenance = run.read_json(run.OUT / "PROVENANCE-AUDIT.json")
    require(
        provenance["owned_read_only_input_guards_pass"],
        "frozen input or protected version-control guard failed",
    )
    current_protected = run.protected_fingerprint()
    require(
        run.protected_version_control_equal(pre["protected_paths"], current_protected),
        "protected version-control state changed after provenance audit",
    )
    if current_protected != pre["protected_paths"]:
        changed = [
            name
            for name in pre["protected_paths"]
            if current_protected[name] != pre["protected_paths"][name]
        ]
        print(
            "warning: protected filesystem metadata changed concurrently: "
            + ", ".join(changed)
        )
    print(
        "post-render Q1/Q2/Q3 artifact verification passed; "
        "residual remains unmeasured"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verification failed: {error}", file=sys.stderr)
        raise
