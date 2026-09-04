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
    print("M3_checker=NOT_ADMITTED_COMMISSIONING_FAILED")
    print("verification=PASS")


if __name__ == "__main__":
    main()
