from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_flats import (
    EXPECTED_HASHES,
    M152,
    PROHIBITED_ROOT,
    sha256_file,
    summarize,
)


HERE = Path(__file__).resolve().parent
OUT = HERE / "out"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def check_source_freeze(probe: dict[str, Any]) -> None:
    require(
        probe["frozen_dependencies"] == EXPECTED_HASHES,
        "frozen M152 dependency hashes differ",
    )
    require(
        probe["noise_calibration_content_sha256"]
        == "47eaf0235c0492ffeabcd0098581f52f22a8d4b8a7241f743c61754476f06566",
        "noise calibration content hash differs",
    )


def check_prohibited_path(inventory: dict[str, Any], probe: dict[str, Any]) -> None:
    banned = str(PROHIBITED_ROOT).lower().replace("/", "\\")
    require(
        inventory["prohibited_root_descended"] is False,
        "inventory says the prohibited root was descended",
    )
    require(
        probe["prohibited_root_opened"] is False,
        "probe says the prohibited root was opened",
    )
    for row in inventory["stacks"]:
        text = str(row["path"]).lower().replace("/", "\\")
        require(
            text != banned and not text.startswith(banned + "\\"),
            f"prohibited stack present in inventory: {row['path']}",
        )
    for row in probe["probes"]:
        text = str(row["path"]).lower().replace("/", "\\")
        require(
            text != banned and not text.startswith(banned + "\\"),
            f"prohibited stack present in probe: {row['path']}",
        )


def check_inventory_integrity(inventory: dict[str, Any]) -> None:
    require(inventory["schema"] == "m181-m4-flat-inventory-v1", "bad inventory schema")
    stack_ids = [row["stack_id"] for row in inventory["stacks"]]
    require(len(stack_ids) == len(set(stack_ids)), "duplicate stack_id in inventory")
    require(
        inventory["stack_directory_count_excluding_prohibited"] == len(stack_ids),
        "inventory stack denominator mismatch",
    )
    require(
        inventory["arw_frame_count_excluding_prohibited"]
        == sum(int(row["frame_count"]) for row in inventory["stacks"]),
        "inventory ARW denominator mismatch",
    )
    details = inventory["detailed_flat_and_slide_stacks"]
    require(len(details) == 14, "detailed inventory must contain exactly 14 stacks")
    for row in details:
        require(
            int(row["exif"]["frame_count"]) > 0,
            f"empty detailed stack: {row['stack_id']}",
        )


def check_rig_audit(inventory: dict[str, Any], rig: dict[str, Any]) -> None:
    require(rig["schema"] == "m181-allowed-rig-audit-v1", "bad rig-audit schema")
    require(rig["complete"] is True, "rig audit is incomplete")
    require(
        rig["prohibited_root_opened"] is False,
        "rig audit says the prohibited root was opened",
    )
    frame_count = int(rig["frame_count_excluding_prohibited"])
    require(
        frame_count == int(inventory["arw_frame_count_excluding_prohibited"]),
        "rig-audit frame denominator differs from inventory",
    )
    expected = {
        "Model": "ILCE-7CM2",
        "LensModel": "FE 100mm F2.8 Macro GM OSS + 2X Teleconverter",
        "FocalLength": 200,
        "ImageStabilization": 1,
    }
    for key, value in expected.items():
        rows = rig["settings"][key]
        require(len(rows) == 1, f"rig audit has multiple {key} populations")
        require(rows[0]["value"] == value, f"rig audit unexpected {key}")
        require(
            int(rows[0]["frame_count"]) == frame_count,
            f"rig audit {key} denominator mismatch",
        )
    require(rig["universal_a7c_ii"] is True, "camera model is not universal")
    require(rig["universal_200mm"] is True, "200 mm is not universal")
    require(
        rig["universal_2x_teleconverter"] is True,
        "2x teleconverter is not universal",
    )
    require(
        int(rig["unexpected_frame_count"]) == len(rig["unexpected_frames"]) == 0,
        "rig audit contains an unexpected or bare-lens frame",
    )


def check_development_resolution(development: dict[str, Any]) -> None:
    require(
        development["schema"] == "m181-development-flat-resolution-v1",
        "bad development-resolution schema",
    )
    method = development["method"]
    require(
        method["authoritative_callable"] == "M152 census.census_flat_capture",
        "development result did not use the M152 predicate",
    )
    require(
        method["predicate_source_modified"] is False,
        "development result says the M152 predicate was modified",
    )
    for name, digest in method["m152_source_sha256"].items():
        require(
            sha256_file(M152 / name) == digest,
            f"development result is stale against M152 {name}",
        )
    noise_path = Path(method["m152_noise_path"])
    require(
        sha256_file(noise_path) == method["m152_noise_file_sha256"],
        "development result is stale against M152 noise calibration",
    )

    capture = development["capture"]
    expected_files = [f"DSC{index:05d}.ARW" for index in range(103, 123)]
    require(
        capture["path"] == r"D:\personal\macro\flat-fields\flat-fields",
        "unexpected development capture path",
    )
    require(
        int(capture["frame_count"])
        == int(capture["decoded_input_count"])
        == len(capture["decoded_inputs"])
        == 20,
        "development capture does not contain exactly 20 decoded inputs",
    )
    require(
        [row["file"] for row in capture["decoded_inputs"]] == expected_files,
        "development capture file population differs",
    )
    require(
        capture["first_file"] == expected_files[0]
        and capture["last_file"] == expected_files[-1],
        "development capture endpoints differ",
    )

    coffee = development["m152_coffee_reference"]
    require(
        coffee["path"] == r"D:\personal\macro\coffee-bubbles",
        "unexpected M152 coffee reference path",
    )
    require(
        int(coffee["frame_count"]) == 19
        and int(coffee["eligible_tile_count"]) == 0
        and coffee["same_capture"] is False,
        "development burst was conflated with M152 coffee",
    )

    thresholds = development["thresholds"]
    require(
        thresholds
        == {
            "band_ratio_strict_maximum": 1.0,
            "minimum_signal_sigma": 10.0,
            "maximum_low_rail_fraction": 0.01,
            "maximum_high_rail_fraction": 0.001,
        },
        "development predicate thresholds differ",
    )
    candidate_count = int(development["initial_candidate_count"])
    eligible_count = int(development["eligible_tile_count"])
    require(
        candidate_count == eligible_count == 1768, "development joint count differs"
    )
    require(
        int(development["development_quota"]) == 100
        and development["reaches_development_quota"] is True,
        "development burst does not clear the 100-tile quota",
    )
    require(
        development["all_frames_evaluated"] is True
        and development["first_failure_counts"] == {},
        "development predicate did not retain every tile through every frame",
    )
    trajectory = development["survivor_trajectory"]
    require(len(trajectory) == 20, "development trajectory is not 20 frames")
    require(
        [row["file"] for row in trajectory] == expected_files
        and all(int(row["survivors"]) == candidate_count for row in trajectory),
        "development trajectory loses a tile or changes files",
    )

    terms = development["term_results"]
    band = terms["band_20_60_native_px_over_temporal_noise_p99"]
    signal = terms["median_signal_over_temporal_sigma"]
    low = terms["low_rail_fraction"]
    high = terms["high_rail_fraction"]
    for name, term in terms.items():
        require(
            int(term["failure_count"]) == 0
            and int(term["survivor_count"]) == candidate_count,
            f"development {name} term does not retain all tiles",
        )
    require(
        0.0
        <= float(band["max_over_frame_ratio_min"])
        <= float(band["max_over_frame_ratio_median_nearest_rank"])
        <= float(band["max_over_frame_ratio_p95_nearest_rank"])
        <= float(band["max_over_frame_ratio_max"])
        < thresholds["band_ratio_strict_maximum"],
        "development band-power term fails",
    )
    require(
        float(signal["minimum_over_frames_and_tiles_sigma"])
        >= thresholds["minimum_signal_sigma"],
        "development signal term fails",
    )
    require(
        float(low["maximum_over_frames_and_tiles"])
        <= thresholds["maximum_low_rail_fraction"],
        "development low-rail term fails",
    )
    require(
        float(high["maximum_over_frames_and_tiles"])
        <= thresholds["maximum_high_rail_fraction"],
        "development high-rail term fails",
    )
    require(
        development["trace_band_distribution_exactly_matches_predicate_output"] is True,
        "development line trace differs from predicate output",
    )
    require(
        development["prohibited_root_opened"] is False,
        "development run says the prohibited root was opened",
    )
    require(
        development["verdict"] == "DEVELOPMENT_FLAT_ELIGIBLE",
        "unexpected development verdict",
    )


def check_probe_accounting(probe: dict[str, Any]) -> None:
    require(probe["schema"] == "m181-m4-flat-probe-v1", "bad probe schema")
    require(probe["complete"] is True, "probe is incomplete")
    unit_ids = [row["unit_id"] for row in probe["probes"]]
    require(len(unit_ids) == len(set(unit_ids)), "duplicate probe unit_id")
    required = {
        "score-medication-pill",
        "score-bee-background",
        "score-foam",
        "development-coffee-bubbles",
        "development-slide-flat-et1s",
        "development-slide-flat-et2p5s",
        "development-slide-flat-et6s",
    }
    require(required.issubset(unit_ids), "required probe unit is missing")
    for row in probe["probes"]:
        if row["status"] != "MEASURED":
            require(
                row["status"].startswith("METADATA_INELIGIBLE_"),
                f"unknown probe status: {row['status']}",
            )
            continue
        selected = int(row["selected_frame_count"])
        processed = int(row["processed_frame_count"])
        initial = int(row["initial_candidate_count"])
        eligible = int(row["eligible_site_count"])
        require(0 < processed <= selected, f"{row['unit_id']}: bad processed count")
        require(
            int(row["decoded_inputs_count"]) == processed,
            f"{row['unit_id']}: decoded-input denominator mismatch",
        )
        require(
            len(str(row["decoded_inputs_content_sha256"])) == 64,
            f"{row['unit_id']}: decoded-input digest is malformed",
        )
        require(
            0 <= eligible <= initial,
            f"{row['unit_id']}: eligible count outside candidate denominator",
        )
        require(
            int(row["eligible_sites_quality_order_count"]) == eligible,
            f"{row['unit_id']}: eligible-site denominator mismatch",
        )
        require(
            len(str(row["eligible_sites_quality_order_content_sha256"])) == 64,
            f"{row['unit_id']}: eligible-site digest is malformed",
        )
        failures = sum(int(value) for value in row["first_failure_counts"].values())
        require(
            failures + eligible == initial,
            f"{row['unit_id']}: failure partition does not close",
        )
        if processed < selected:
            require(eligible == 0, f"{row['unit_id']}: short-circuit left survivors")
            require(
                row["logical_short_circuit_after_zero_survivors"] is True,
                f"{row['unit_id']}: short-circuit not declared",
            )
        else:
            require(
                row["all_frames_evaluated"] is True,
                f"{row['unit_id']}: full evaluation not declared",
            )


def check_verdict_reduction(probe: dict[str, Any]) -> None:
    expected = summarize(probe["probes"])
    require(probe["summary"] == expected, "stored summary differs from exact reduction")
    require(
        expected["capture_verdict"]
        in {
            "RAW_CAPTURE_FLOORS_MET_FINAL_TRANSFER_ELIGIBILITY_UNMEASURED",
            "M4_RETAINED_BLOCKED_CAPTURE",
        },
        "unexpected capture verdict",
    )


def verify_values(
    inventory: dict[str, Any],
    probe: dict[str, Any],
    rig: dict[str, Any],
    development: dict[str, Any],
) -> list[str]:
    checks = [
        ("source-freeze", lambda: check_source_freeze(probe)),
        ("prohibited-path", lambda: check_prohibited_path(inventory, probe)),
        ("inventory-integrity", lambda: check_inventory_integrity(inventory)),
        ("rig-audit", lambda: check_rig_audit(inventory, rig)),
        (
            "development-resolution",
            lambda: check_development_resolution(development),
        ),
        ("probe-accounting", lambda: check_probe_accounting(probe)),
        ("verdict-reduction", lambda: check_verdict_reduction(probe)),
    ]
    passed = []
    for name, check in checks:
        check()
        passed.append(name)
    return passed


def load_values() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    inventory = json.loads((OUT / "inventory.json").read_text(encoding="ascii"))
    probe = json.loads((OUT / "flat-probe.json").read_text(encoding="ascii"))
    rig = json.loads((OUT / "rig-audit.json").read_text(encoding="ascii"))
    development = json.loads(
        (OUT / "development-flat-resolution.json").read_text(encoding="ascii")
    )
    return inventory, probe, rig, development


def main() -> int:
    inventory, probe, rig, development = load_values()
    passed = verify_values(inventory, probe, rig, development)
    print(f"GREEN: {len(passed)} checks: {', '.join(passed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
