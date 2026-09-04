"""Apply the frozen flat-site rule to already-burned commissioning material.

These captures can never enter the M4 scored population.  This supplemental
census answers only whether existing non-holdout/burned photons can commission
the future flat checker after coffee-bubbles produced no qualifying tile.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from census import census_flat_capture, load_inventory, load_noise, write_json
from census_common import HERE, load_definition, sha256_file, tree_summary


OUT = HERE / "out" / "supplemental-commissioning-census.json"

BURNED_FLAT_SLIDE_STACKS = [
    {
        "capture_id": "burned-slide-flat-et1s",
        "stack_id": (
            "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
            "flat-sw4-cpl\\flat-et1s-sw4-cpl"
        ),
        "path": (
            "D:\\personal\\macro\\requests\\misc-diagnostic\\"
            "high-res-calibration-slide-cpl\\flat-sw4-cpl\\flat-et1s-sw4-cpl"
        ),
        "evidence_class": "BURNED_DEVELOPMENT_NOT_SCORABLE",
        "quota": 100,
    },
    {
        "capture_id": "burned-slide-flat-et2-5s",
        "stack_id": (
            "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
            "flat-sw4-cpl\\flat-et2.5s-sw4-cpl"
        ),
        "path": (
            "D:\\personal\\macro\\requests\\misc-diagnostic\\"
            "high-res-calibration-slide-cpl\\flat-sw4-cpl\\flat-et2.5s-sw4-cpl"
        ),
        "evidence_class": "BURNED_DEVELOPMENT_NOT_SCORABLE",
        "quota": 100,
    },
    {
        "capture_id": "burned-slide-flat-et6s",
        "stack_id": (
            "requests\\misc-diagnostic\\high-res-calibration-slide-cpl\\"
            "flat-sw4-cpl\\flat-et6s-sw4-cpl"
        ),
        "path": (
            "D:\\personal\\macro\\requests\\misc-diagnostic\\"
            "high-res-calibration-slide-cpl\\flat-sw4-cpl\\flat-et6s-sw4-cpl"
        ),
        "evidence_class": "BURNED_DEVELOPMENT_NOT_SCORABLE",
        "quota": 100,
    },
]


def main() -> None:
    definition, definition_sha = load_definition()
    noise = load_noise(definition_sha)
    inventory, holdout = load_inventory(definition)
    inventory_by_id = {row["stack_id"]: row for row in inventory["stacks"]}
    burned_members = {
        member
        for unit in holdout["burned_or_spent_units"]
        for member in unit["members"]
    }
    for capture in BURNED_FLAT_SLIDE_STACKS:
        if capture["stack_id"] not in burned_members:
            raise RuntimeError(
                f"{capture['stack_id']} is not registered as burned/spent"
            )

    roots = [Path(value).resolve() for value in definition["allowed_read_roots"]]
    before = {str(root): tree_summary(root) for root in roots}
    results: list[dict[str, Any]] = []
    for capture in BURNED_FLAT_SLIDE_STACKS:
        result = census_flat_capture(
            capture, definition, noise, inventory_by_id
        )
        result["quota"] = capture["quota"]
        results.append(result)
    after = {str(root): tree_summary(root) for root in roots}
    if before != after:
        raise RuntimeError("a registered read-only source tree changed")

    artifact = {
        "schema": "m152-supplemental-commissioning-census-v1",
        "definition_sha256": definition_sha,
        "noise_calibration_content_sha256": noise["content_sha256"],
        "purpose": "commissioning availability only; never scored",
        "capture_results": results,
        "any_capture_has_100_sites": any(
            int(result["eligible_site_count"]) >= 100 for result in results
        ),
        "read_only_trees_unchanged": True,
    }
    write_json(OUT, artifact)
    digest = sha256_file(OUT)
    OUT.with_suffix(".sha256").write_text(
        f"{digest}  {OUT.name}\n", encoding="ascii"
    )
    for result in results:
        print(
            f"{result['capture_id']}: eligible={result['eligible_site_count']} "
            f"evaluated={len(result['survivor_trajectory'])}/"
            f"{result['inventory_frame_count']}"
        )
    print(
        "existing burned commissioning flat sufficient="
        f"{artifact['any_capture_has_100_sites']}"
    )
    print(f"supplemental sha256={digest}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}")
        raise SystemExit(2)
