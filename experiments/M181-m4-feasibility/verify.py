from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from probe_flats import EXPECTED_HASHES, PROHIBITED_ROOT, summarize


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


def check_prohibited_path(
    inventory: dict[str, Any], probe: dict[str, Any]
) -> None:
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
    inventory: dict[str, Any], probe: dict[str, Any]
) -> list[str]:
    checks = [
        ("source-freeze", lambda: check_source_freeze(probe)),
        ("prohibited-path", lambda: check_prohibited_path(inventory, probe)),
        ("inventory-integrity", lambda: check_inventory_integrity(inventory)),
        ("probe-accounting", lambda: check_probe_accounting(probe)),
        ("verdict-reduction", lambda: check_verdict_reduction(probe)),
    ]
    passed = []
    for name, check in checks:
        check()
        passed.append(name)
    return passed


def load_values() -> tuple[dict[str, Any], dict[str, Any]]:
    inventory = json.loads((OUT / "inventory.json").read_text(encoding="ascii"))
    probe = json.loads((OUT / "flat-probe.json").read_text(encoding="ascii"))
    return inventory, probe


def main() -> int:
    inventory, probe = load_values()
    passed = verify_values(inventory, probe)
    print(f"GREEN: {len(passed)} checks: {', '.join(passed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
