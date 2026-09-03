from __future__ import annotations

import sys
from pathlib import Path

from common import OUT, SCORECARD, SOURCE_COMMIT, read_json, sha256


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    commission = read_json(OUT / "commission.json")
    inputs = read_json(OUT / "INPUT-MANIFEST.json")
    sites = read_json(OUT / "SITE-MANIFEST.json")
    run = read_json(OUT / "RUN-MANIFEST.json")
    require(commission["all_commissioned"], "commissioning did not pass")
    require(commission["null_stayed_green"], "commissioning null went red")
    require(
        all(row["went_red"] for row in commission["plants"]),
        "at least one planted defect did not go red",
    )
    require(inputs["scorecard_sha256"] == sha256(SCORECARD), "scorecard hash moved")
    require(run["scorecard"]["sha256"] == sha256(SCORECARD), "run scorecard hash moved")
    require(run["source"]["commit"] == SOURCE_COMMIT, "source commit moved")
    binary = Path(run["binary"]["runtime_path"])
    require(binary.exists(), "frozen binary is missing")
    require(sha256(binary) == run["binary"]["sha256"], "frozen binary hash moved")
    require(len(inputs["used_files"]) == 64, "input manifest does not hold 64 bee ARWs")
    require(
        all(record["exists"] for record in inputs["capture_inventory"].values()),
        "a named scorecard capture is missing",
    )
    require(len(sites["m1"]["sites"]) == 486, "M1 site grid changed")
    require(len(sites["m2"]["bright_sites"]) >= 16, "bright M2 arm underpowered")
    require(len(sites["m2"]["second_sites"]) >= 16, "second M2 arm underpowered")
    require(inputs["m7_preflight"]["candidate_count"] == 0, "M7 blocker changed")
    require(inputs["m1_floor_preflight"]["matching_dark_count"] == 0, "bee dark blocker changed")
    require(inputs["m1_floor_preflight"]["matching_flat_count"] == 0, "bee flat blocker changed")

    measurements = OUT / "MEASUREMENTS.json"
    if measurements.exists():
        data = read_json(measurements)
        geometry = read_json(OUT / "GEOMETRY-AUDIT.json")
        rails = read_json(OUT / "RAIL-PREFLIGHT.json")
        renders = read_json(OUT / "RENDER-MANIFEST.json")
        require(len(data["m1"]) == 2, "expected two M1 bee diagnostics")
        require(len(data["m2"]) == 2, "expected two M2 bee diagnostics")
        require(len(renders["records"]) == 8, "expected eight frozen score renders")
        require(
            len({row["sha256"] for row in renders["records"]}) == 8,
            "score render hashes are not all distinct",
        )
        require(geometry["commissioning"]["commissioned"], "geometry audit uncommissioned")
        require(geometry["all_scale_invalid"], "a frozen arm unexpectedly passed scale")
        require(rails["commissioning"]["commissioned"], "rail census uncommissioned")
        for row in data["m1"]:
            require(row["f_licensed"]["point"] <= 0.25, "unlicensed M1 detail escaped")
            require(row["formal_status"] == "UNMEASURED", "native diagnostic became formal")
        for row in data["m2"]:
            require(row["formal_status"] == "UNMEASURED", "native diagnostic became formal")
        print("post-render verification passed")
    else:
        render_dir = OUT / "renders"
        require(
            not render_dir.exists() or not any(render_dir.iterdir()),
            "score render exists before the pre-render verification",
        )
        print("pre-render verification passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
