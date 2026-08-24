"""Apply M82's frozen readability and portability rules without retuning."""

from __future__ import annotations

import json
import math
import platform
import sys
from pathlib import Path

import numpy as np
import scipy

import m82lib as M

NULL_BOUND_PX = 0.343
SE_FACTOR = 3.09
MIN_Z = 2.0


def price_readable(dsig: dict, pins: int, raw_validation_pass: bool) -> bool:
    px = dsig["px"]
    corrected_se = dsig["corrected_se_px"]
    return bool(
        dsig["ok"]
        and px is not None
        and corrected_se is not None
        and corrected_se > 0.0
        and abs(px) > NULL_BOUND_PX
        and abs(px) / corrected_se >= MIN_Z
        and pins == 0
        and raw_validation_pass
    )


def portability_status(rows: list[dict], bar: float) -> dict:
    if not all(row["readable"] for row in rows):
        return {"status": "NOT_ESTABLISHED", "span": None, "reason": "unreadable price"}
    signs = {math.copysign(1.0, row["price_px"]) for row in rows}
    if len(signs) > 1:
        return {"status": "REFUTED", "span": None, "reason": "readable sign reversal"}
    if all(row["price_px"] < 0.0 for row in rows):
        return {
            "status": "NOT_ESTABLISHED",
            "span": None,
            "reason": "all readable prices are negative",
        }
    prices = [row["price_px"] for row in rows]
    span = max(prices) / min(prices)
    return {
        "status": "PASS" if span <= bar else "REFUTED",
        "span": span,
        "bar": bar,
        "reason": "within bar" if span <= bar else "span exceeds bar",
    }


def curve_status(dsig_by_request: dict, pins: int) -> dict:
    if pins:
        return {"status": "NOT_ESTABLISHED", "reason": "container pin"}
    rows = [dsig_by_request[f"{request:.2f}"] for request in M.REQUESTS]
    if any(
        row["px"] is None
        or row["corrected_se_px"] is None
        or row["corrected_se_px"] <= 0.0
        for row in rows
    ):
        return {"status": "NOT_ESTABLISHED", "reason": "non-finite curve point"}
    reversals = []
    for left, right, pair in zip(rows, rows[1:], ("0.90->0.70", "0.70->0.50")):
        left_low = left["px"] - 2.0 * left["corrected_se_px"]
        right_high = right["px"] + 2.0 * right["corrected_se_px"]
        if right_high < left_low:
            reversals.append(pair)
    return {
        "status": "FAIL" if reversals else "PASS",
        "reason": "significant reversal" if reversals else "no significant reversal",
        "reversals": reversals,
    }


def self_tests() -> None:
    print("M82_DECISION_TEST_COUNT=4")
    good = [
        {"readable": True, "price_px": 0.5},
        {"readable": True, "price_px": 0.7},
    ]
    assert portability_status(good, 1.5)["status"] == "PASS"
    assert portability_status(good, 1.2)["status"] == "REFUTED"
    assert (
        portability_status(
            [{"readable": True, "price_px": -0.5}, good[0]], 2.0
        )["status"]
        == "REFUTED"
    )
    assert (
        portability_status(
            [{"readable": False, "price_px": 0.1}, good[0]], 2.0
        )["status"]
        == "NOT_ESTABLISHED"
    )
    print("M82_DECISION_TESTS=4/4 PASS")


def main() -> None:
    self_tests()
    if "--self-test-only" in sys.argv:
        return
    confirm = json.loads((M.HERE / "confirm-results.json").read_text(encoding="utf-8"))
    ladder = json.loads((M.HERE / "ladder-results.json").read_text(encoding="utf-8"))
    validation = json.loads((M.HERE / "validation.json").read_text(encoding="utf-8"))
    mutation_log = (M.HERE / "mutation-control.log").read_text(encoding="utf-8")
    mutation_pass = (
        "PLANTED_READBACK=PASS" in mutation_log
        and "RESTORED=True" in mutation_log
        and "EXIT=0" not in mutation_log
    )
    output = {
        "registered_bars": {
            "null_bound_px": NULL_BOUND_PX,
            "jackknife_factor": SE_FACTOR,
            "minimum_corrected_z": MIN_Z,
            "sibling_span": 1.5,
            "five_stack_span": 2.0,
            "raw_rms_relative_error": 0.01,
        },
        "stacks": {},
        "controls": {
            "confirmations_pass": bool(confirm["all_confirmed"]),
            "whole_plane_validation_pass": bool(validation["pass"]),
            "mutation_control_pass": mutation_pass,
        },
        "provenance": {
            "binary": confirm["binary"],
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "m82lib_sha256": M.sha256(M.HERE / "m82lib.py"),
            "m57lib_sha256": M.sha256(
                M.REPO / "experiments" / "m57-shape-metric" / "src" / "m57lib.py"
            ),
            "validation_sha256": M.sha256(M.HERE / "validation.json"),
            "mutation_log_sha256": M.sha256(M.HERE / "mutation-control.log"),
        },
    }
    raw_validations_all = True
    curve_controls_all = True
    primary_rows = {}
    for stack in M.ORIGINAL_STACKS:
        sharp_path = M.HERE / f"sharpness-{stack}.json"
        sharp = json.loads(sharp_path.read_text(encoding="utf-8"))
        stack_out = {
            "flat_contamination_max": sharp["flat"]["m77_contamination_max"],
            "flat_precondition_pass": sharp["flat"]["m77_flat_pass"],
            "flat_pin_samples": sharp["flat"]["pin_samples"],
            "detail_pin_samples": sharp["detail"]["pin_samples"],
            "sharpness_sha256": M.sha256(sharp_path),
            "targets": {},
        }
        for request in M.REQUESTS:
            key = f"{request:.2f}"
            cli = confirm["stacks"][stack]["targets"][key]
            python_raw = sharp["detail"]["full"][key]["raw_rms"]
            cli_raw = cli["m80"]["raw_rms"]
            raw_relative_error = abs(python_raw / cli_raw - 1.0)
            raw_pass = raw_relative_error <= 0.01
            raw_validations_all &= raw_pass
            dsig = sharp["detail"]["dsig"][key]
            readable = price_readable(
                dsig, sharp["detail"]["pin_samples"], raw_pass
            )
            corrected_z = (
                abs(dsig["px"]) / dsig["corrected_se_px"]
                if dsig["px"] is not None
                and dsig["corrected_se_px"] is not None
                and dsig["corrected_se_px"] > 0.0
                else None
            )
            m80_readable = bool(sharp["flat"]["m77_flat_pass"]) and (
                confirm["stacks"][stack]["selector_m80"]["target"] == "MEASURABLE"
            ) and cli["m80"]["retention"] is not None
            stack_out["targets"][key] = {
                **cli,
                "dsig": dsig,
                "corrected_z": corrected_z,
                "price_readable": readable,
                "python_raw_rms": python_raw,
                "raw_rms_relative_error": raw_relative_error,
                "raw_rms_validation_pass": raw_pass,
                "m80_readable": m80_readable,
                "m80_status": "READABLE" if m80_readable else "UNREADABLE",
                "local_detail_admission": sharp["detail"]["full"][key][
                    "admission"
                ],
                "flat_dsig": sharp["flat"]["dsig"][key],
            }
            if request == M.PRIMARY_REQUEST:
                primary_rows[stack] = {
                    "stack": stack,
                    "readable": readable,
                    "price_px": dsig["px"],
                    "corrected_se_px": dsig["corrected_se_px"],
                }
        curve = curve_status(
            sharp["detail"]["dsig"], sharp["detail"]["pin_samples"]
        )
        stack_out["curve_control"] = curve
        curve_controls_all &= curve["status"] == "PASS"
        output["stacks"][stack] = stack_out
    output["controls"]["raw_rms_validations_pass"] = raw_validations_all
    output["controls"]["curve_controls_pass"] = curve_controls_all
    sibling = portability_status([primary_rows[s] for s in M.SIBLINGS], 1.5)
    five = portability_status([primary_rows[s] for s in M.FIVE], 2.0)
    output["portability"] = {
        "primary_request": M.PRIMARY_REQUEST,
        "siblings": sibling,
        "five_m77_stacks": five,
        "primary_rows": primary_rows,
    }
    controls_pass = all(output["controls"].values())
    refuted = sibling["status"] == "REFUTED" or five["status"] == "REFUTED"
    survives = (
        controls_pass and sibling["status"] == "PASS" and five["status"] == "PASS"
    )
    if survives:
        verdict = "SHIP"
        disposition = "SURVIVES"
    elif refuted:
        verdict = "NO SHIP"
        disposition = "REFUTED"
    else:
        verdict = "NO SHIP"
        disposition = "NOT ESTABLISHED"
    singleton_exposure = {
        stack: {
            f"{request:.2f}": confirm["stacks"][stack]["targets"][
                f"{request:.2f}"
            ]["singleton_percent"]
            for request in M.REQUESTS
        }
        for stack in M.ORIGINAL_STACKS
    }
    output["singletons"] = singleton_exposure
    output["single_frame_floor_claimed"] = False
    output["decision"] = {
        "verdict": verdict,
        "portable_price_list": disposition,
        "production_code_allowed": survives,
    }
    output["input_hashes"] = {
        "ladder_results": M.sha256(M.HERE / "ladder-results.json"),
        "confirm_results": M.sha256(M.HERE / "confirm-results.json"),
        "binary_record": M.sha256(M.HERE / "binary.json"),
        "m77_five_roi_source": M.sha256(
            M.REPO / "experiments" / "M77-gate-sweep" / "out" / "01b-rois.json"
        ),
        "m77_sibling_roi_source": M.sha256(
            M.REPO / "experiments" / "M77-gate-sweep" / "out" / "06-roi-wt2.json"
        ),
    }
    (M.HERE / "results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    for stack, row in primary_rows.items():
        print(
            f"{stack:16} price={row['price_px']} se={row['corrected_se_px']} "
            f"readable={row['readable']}"
        )
    print(f"siblings: {sibling}")
    print(f"five stacks: {five}")
    print(f"VERDICT={verdict} portable_price_list={disposition}")


if __name__ == "__main__":
    main()
