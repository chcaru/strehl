"""Fast integrity/recount checks for committed M152 artifacts."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from census import noise_result_hash
from census_common import HERE, load_definition, sha256_file
from m3_checker import load_checker_definition


OUT = HERE / "out"


def load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="ascii"))


def sidecar_hash(name: str) -> str:
    return (OUT / name).read_text(encoding="ascii").split()[0]


def main() -> None:
    _, definition_sha = load_definition()
    checker, _ = load_checker_definition()
    noise = load("noise-calibration.json")
    manifest = load("census-manifest.json")
    readonly = load("readonly-verification.json")
    commission = load("m3-commission.json")
    side_max_freeze1 = load("m3-side-max-commission.json")
    side_max = load("m3-side-max-commission-v2.json")
    supplemental = load("supplemental-commissioning-census.json")
    m4_freeze = json.loads((HERE / "m4-freeze.json").read_text(encoding="ascii"))

    assert noise["definition_sha256"] == definition_sha
    assert noise_result_hash(noise) == noise["content_sha256"]
    manifest_hash = sha256_file(OUT / "census-manifest.json")
    assert manifest_hash == sidecar_hash("census-manifest.sha256")
    assert manifest_hash == checker["site_population"]["manifest_sha256"]
    assert sha256_file(OUT / "m3-commission.json") == sidecar_hash(
        "m3-commission.sha256"
    )
    side_max_freeze1_hash = sha256_file(OUT / "m3-side-max-commission.json")
    assert side_max_freeze1_hash == sidecar_hash(
        "m3-side-max-commission.sha256"
    )
    assert (
        side_max_freeze1_hash
        == "52fb035d98cd4463a4431fc7abf49b08a99e373f08238a3ecb6291f9eb0974a6"
    )
    side_max_hash = sha256_file(OUT / "m3-side-max-commission-v2.json")
    assert side_max_hash == sidecar_hash("m3-side-max-commission-v2.sha256")
    assert (
        side_max_hash
        == "0df4593573b85cc611005ac112f80c6c9a47949f130ddfd377129db2dff937c4"
    )
    assert sha256_file(OUT / "supplemental-commissioning-census.json") == sidecar_hash(
        "supplemental-commissioning-census.sha256"
    )

    m3_capture_counts = {
        capture["capture_id"]: len(capture["eligible_sites_quality_order"])
        for capture in manifest["m3"]["capture_results"]
    }
    assert sum(m3_capture_counts.values()) == manifest["m3"]["sufficiency"][
        "eligible_edges_overall"
    ]
    selected_m3 = manifest["m3"]["sufficiency"]["selected_sites"]
    assert len(selected_m3) == 500
    assert len({site["site_id"] for site in selected_m3}) == 500
    assert all(site["reach_native_px"] == 400 for site in selected_m3)
    selected_by_capture = Counter(site["capture_id"] for site in selected_m3)
    assert set(selected_by_capture) == set(
        checker["site_population"]["required_capture_ids"]
    )
    assert min(selected_by_capture.values()) >= 50

    flat_results = manifest["m4"]["flat_capture_results"]
    edge_results = manifest["m4"]["edge_capture_results"]
    assert sum(item["eligible_site_count"] for item in flat_results) == manifest[
        "m4"
    ]["sufficiency"]["eligible_flat_sites_overall"]
    assert sum(item["eligible_site_count"] for item in edge_results) == manifest[
        "m4"
    ]["sufficiency"]["eligible_edge_sites_overall"]
    assert manifest["m4"]["sufficiency"]["selected_flat_site_count"] == 138
    assert manifest["m4"]["sufficiency"]["selected_edge_site_count"] == 250
    assert manifest["m4"]["sufficiency"]["verdict"] == "NEEDS_NEW_CAPTURE"

    assert readonly["all_trees_unchanged"]
    assert readonly["before"] == readonly["after"]
    assert not supplemental["any_capture_has_100_sites"]
    assert all(
        item["eligible_site_count"] == 0
        for item in supplemental["capture_results"]
    )
    assert commission["verdict"] == "NOT_ADMITTED_COMMISSIONING_FAILED"
    assert commission["failed_assertions"] == [
        "one_sided_far_veil_detected_at_least_95pct"
    ]
    assert commission["untouched_raw_null"]["false_positive_rate"] == 0.0
    assert (
        side_max_freeze1["verdict"]
        == "NOT_ADMITTED_COMMISSIONING_FAILED"
    )
    assert side_max_freeze1["failed_assertions"] == [
        "improvement_control_passes"
    ]
    assert (
        side_max["fixture_repair"]["superseded_result_sha256"]
        == side_max_freeze1_hash
    )
    assert side_max["commission_source_sha256"] == sha256_file(
        HERE / "commission_m3_side_max.py"
    )
    assert side_max["study_definition_sha256"] == sha256_file(
        HERE / "side-max-commission-definition.json"
    )
    assert side_max["historical_m152_v1_hashes_verified"]
    assert side_max["holdout_pixels_opened"] == 0
    assert side_max["candidate_outputs_opened"] == 0
    assert side_max["comparator_outputs_opened"] == 0
    assert side_max["verdict"] == "SIDE_MAX_REDUCTION_COMMISSIONING_PASS"
    assert side_max["m3_axis_verdict"] == "UNMEASURED_COMPARATOR_QUALIFICATION"
    assert side_max["failed_assertions"] == []
    assert all(side_max["assertions"].values())
    primary = next(
        arm
        for arm in side_max["empirical_clean_noise"]["arms"]
        if arm["role"] == "PRIMARY"
    )
    assert primary["name"] == "iso100_production_covariance_k11"
    assert primary["verdict"] == "PASS"
    assert primary["pooled"]["median_v_e_side_max"] <= 0.01
    assert primary["pooled"]["p99_v_e_side_max"] <= 0.05
    assert primary["pooled"]["affected_edge_count"] == 0
    assert primary["pooled"]["affected_edge_wilson_ucb95"] <= 0.02
    assert primary["pooled"]["new_only_threshold_crossings"] == 0
    assert all(
        arm["verdict"] == "PASS"
        and arm["pooled"]["site_count"] == 500
        and arm["pooled"]["side_asymmetry"]["asymmetric_site_count"] == 500
        for arm in side_max["empirical_clean_noise"]["arms"]
    )
    assert side_max["one_sided_ratio"] == {
        "analytic": 2.0,
        "maximum": 2.0,
        "median": 2.0,
        "minimum": 2.0,
    }
    assert side_max["commissioning_counts"] == {
        "arms_regressed": 0,
        "checks_passed": 15,
        "checks_run": 15,
        "improvement_control_arms_preserved": 1,
        "improvement_control_arms_run": 1,
        "inert_control_arms_run": 6,
        "inert_control_arms_survived": 6,
        "mutated_sites_charged": 3000,
        "mutated_sites_planted": 3000,
        "mutation_arms_killed": 6,
        "mutation_arms_planted": 6,
        "regressed_arm_names": [],
    }
    assert m4_freeze["census_definition_sha256"] == definition_sha
    assert m4_freeze["census_manifest_sha256"] == manifest_hash
    assert m4_freeze["population"]["flat_total"] == 250
    assert m4_freeze["population"]["edge_total"] == 250

    print(f"definition_sha256={definition_sha}")
    print(f"manifest_sha256={manifest_hash}")
    print(f"M3_eligible={sum(m3_capture_counts.values())}")
    print(f"M3_selected={len(selected_m3)}")
    print(
        "M4_eligible_flat="
        f"{manifest['m4']['sufficiency']['eligible_flat_sites_overall']}"
    )
    print(
        "M4_eligible_edge="
        f"{manifest['m4']['sufficiency']['eligible_edge_sites_overall']}"
    )
    print("M3_v1_checker=NOT_ADMITTED_COMMISSIONING_FAILED")
    print("M3_side_max_reduction=SIDE_MAX_REDUCTION_COMMISSIONING_PASS")
    print("M3_axis=UNMEASURED_COMPARATOR_QUALIFICATION")
    print("verification=PASS")


if __name__ == "__main__":
    main()
