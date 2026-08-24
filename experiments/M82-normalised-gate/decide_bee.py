"""Apply the frozen M82 bee-amendment rules without retuning."""

from __future__ import annotations

import json
import platform
import sys

import numpy as np
import scipy

import decide as D
import m82lib as M


def selected_max_difference(left, right, keys) -> float:
    return max(abs(float(left[key]) - float(right[key])) for key in keys)


def historical_reproduction(ladder: dict, confirm: dict, sharp: dict) -> dict:
    old_ladder = json.loads(
        (M.HERE / "ladder-results.json").read_text(encoding="utf-8")
    )["stacks"]["bee-1"]
    old_confirm = json.loads(
        (M.HERE / "confirm-results.json").read_text(encoding="utf-8")
    )["stacks"]["bee-1"]
    old_sharp = json.loads(
        (M.HERE / "sharpness-bee-1.json").read_text(encoding="utf-8")
    )
    ladder_keys = (
        "gate",
        "mean_n_eff",
        "predicted_sigma_gain",
        "singleton_percent",
        "boundary_percent",
    )
    ladder_difference = max(
        selected_max_difference(old, new, ladder_keys)
        for old, new in zip(
            old_ladder["rows"], ladder["stacks"]["bee-1"]["rows"], strict=True
        )
    )
    target_keys = (
        "solved_gate",
        "mean_n_eff",
        "predicted_sigma_gain",
        "singleton_percent",
        "boundary_percent",
        "flat_hp_sd_dn",
        "flat_hp_ratio",
    )
    confirm_difference = max(
        selected_max_difference(
            old_confirm["targets"][key],
            confirm["stacks"]["bee-1"]["targets"][key],
            target_keys,
        )
        for key in ("0.90", "0.70", "0.50")
    )
    sharp_equal = old_sharp == sharp
    return {
        "logical_stack": "bee-1",
        "old_directory": "bee-1",
        "current_directory": "bee-1-cpl",
        "ladder_selected_max_absolute_difference": ladder_difference,
        "confirmation_selected_max_absolute_difference": confirm_difference,
        "sharpness_json_exact_match": sharp_equal,
        "pass": ladder_difference == 0.0
        and confirm_difference == 0.0
        and sharp_equal,
    }


def main() -> None:
    D.self_tests()
    if "--self-test-only" in sys.argv:
        return
    physics = json.loads((M.HERE / "bee-physics.json").read_text(encoding="utf-8"))
    ladder = json.loads(
        (M.HERE / "bee-ladder-results.json").read_text(encoding="utf-8")
    )
    confirm = json.loads(
        (M.HERE / "bee-confirm-results.json").read_text(encoding="utf-8")
    )
    mutation_path = M.HERE / "mutation-control-bee.log"
    mutation_log = mutation_path.read_text(encoding="utf-8")
    mutation_pass = (
        "PLANTED_READBACK=PASS" in mutation_log
        and "RESTORED=True" in mutation_log
        and "EXIT=0" not in mutation_log
    )
    output = {
        "registered_bars": {
            "null_bound_px": D.NULL_BOUND_PX,
            "jackknife_factor": D.SE_FACTOR,
            "minimum_corrected_z": D.MIN_Z,
            "bee_span": 1.5,
            "raw_rms_relative_error": 0.01,
        },
        "stacks": {},
        "controls": {
            "confirmations_pass": bool(confirm["all_confirmed"]),
            "mutation_control_pass": mutation_pass,
            "current_path_identity_pass": bool(
                physics["controls"]["identity_pass"]
            ),
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
            "physics_sha256": M.sha256(M.HERE / "bee-physics.json"),
            "mutation_log_sha256": M.sha256(mutation_path),
        },
    }
    raw_validations_all = True
    curve_controls_all = True
    primary_rows = {}
    bee1_sharp = None
    for stack in M.BEE_SIBLINGS:
        sharp_path = M.HERE / f"bee-sharpness-{stack}.json"
        sharp = json.loads(sharp_path.read_text(encoding="utf-8"))
        if stack == "bee-1":
            bee1_sharp = sharp
        stack_out = {
            "directory": M.STACKS[stack]["directory"],
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
            readable = D.price_readable(
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
        curve = D.curve_status(
            sharp["detail"]["dsig"], sharp["detail"]["pin_samples"]
        )
        stack_out["curve_control"] = curve
        curve_controls_all &= curve["status"] == "PASS"
        output["stacks"][stack] = stack_out
    if bee1_sharp is None:
        raise RuntimeError("bee-1 sharpness result missing")
    history = historical_reproduction(ladder, confirm, bee1_sharp)
    output["controls"]["raw_rms_validations_pass"] = raw_validations_all
    output["controls"]["curve_controls_pass"] = curve_controls_all
    output["controls"]["historical_bee1_reproduction_pass"] = history["pass"]
    numerical = D.portability_status(
        [primary_rows[stack] for stack in M.BEE_SIBLINGS], 1.5
    )
    physical_comparability = bool(physics["p34_equivalent"])
    conditional = (
        numerical
        if physical_comparability
        else {
            "status": "PREMISE_NOT_ESTABLISHED",
            "span": None,
            "reason": "bee triple failed frozen physical-comparability rule",
        }
    )
    output["physical_comparability"] = {
        "p34_equivalent": physical_comparability,
        "disposition": physics["disposition"],
        "spans": physics["spans"],
        "peak_windows": physics["peak_windows"],
    }
    output["portability"] = {
        "primary_request": M.PRIMARY_REQUEST,
        "bee_triple_conditional": conditional,
        "bee_triple_numerical_if_comparable": numerical,
        "primary_rows": primary_rows,
    }
    output["historical_bee1_reproduction"] = history
    output["singletons"] = {
        stack: {
            key: {
                "whole_plane_percent": target["singleton_percent"],
                "local_detail_percent": output["stacks"][stack]["targets"][key][
                    "local_detail_admission"
                ]["singleton_percent"],
            }
            for key, target in confirm["stacks"][stack]["targets"].items()
        }
        for stack in M.BEE_SIBLINGS
    }
    output["single_frame_floor_claimed"] = False
    output["decision"] = {
        "original_m82_verdict_unchanged": "NO SHIP / NOT ESTABLISHED",
        "bee_triple": conditional["status"],
        "bee_triple_can_change_original_verdict": False,
        "production_code_allowed": False,
    }
    output["input_hashes"] = {
        "bee_ladder_results": M.sha256(M.HERE / "bee-ladder-results.json"),
        "bee_confirm_results": M.sha256(M.HERE / "bee-confirm-results.json"),
        "binary_record": M.sha256(M.HERE / "binary.json"),
        "bee_preregistration": M.sha256(M.HERE / "PREREGISTRATION-BEE.md"),
    }
    (M.HERE / "bee-results.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    for stack, row in primary_rows.items():
        print(
            f"{stack:8} price={row['price_px']} se={row['corrected_se_px']} "
            f"readable={row['readable']}"
        )
    print(f"physical comparability={physical_comparability}")
    print(f"numerical bee result={numerical}")
    print(f"conditional bee result={conditional}")
    print(f"historical bee-1 reproduction={history}")


if __name__ == "__main__":
    main()
