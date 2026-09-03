"""Regression-check the committed M-PHASE0-LCA artifacts.

This is not independent scientific verification; it checks that the concise
verdict is actually implied by detailed JSON rows and that artifact hashes
have not drifted. In-memory plants commission those checks before their green
result is trusted.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from lca_lib import LANE, OUT, REPO, file_sha256, write_json


REPORT = REPO / "docs" / "research" / "M-PHASE0-LCA.md"


def classify_combined(action: dict) -> str:
    if action.get("reason") and "A_ci95_frames" not in action:
        return "INDETERMINATE"
    lower, upper = action["A_ci95_frames"]
    negative = int(action["negative_subjects"])
    count = int(action["subject_count"])
    if not action["null_gate_passed"]:
        return "VOID_NULL_GATE"
    if negative <= 1:
        return "KILL"
    if lower >= 0.50 and negative == count:
        return "SURVIVE"
    if lower >= 0.25 and negative == count:
        return "NARROWED"
    if upper < 0.25:
        return "KILL"
    return "INDETERMINATE"


def audit_combined_action(name: str, action: dict) -> list[str]:
    errors: list[str] = []
    implied_category = classify_combined(action)
    if action.get("category") != implied_category:
        errors.append(
            f"{name} category {action.get('category')!r} "
            f"!= numeric fields {implied_category!r}"
        )
    if implied_category == "INDETERMINATE" and "A_ci95_frames" not in action:
        return errors

    subject = action.get("subject_delta_r_medians_frames", {})
    if not subject:
        errors.append(f"{name} subject medians missing")
    else:
        recomputed_a = min(abs(float(value)) for value in subject.values())
        recorded_a = float(action["A_min_abs_subject_median_frames"])
        if abs(recomputed_a - recorded_a) > 1.0e-12:
            errors.append(
                f"{name} A {recorded_a} != subject minimum {recomputed_a}"
            )
        negative = sum(float(value) < 0.0 for value in subject.values())
        if int(action["negative_subjects"]) != negative:
            errors.append(f"{name} negative-subject count drift")
        if int(action["subject_count"]) != len(subject):
            errors.append(f"{name} subject count drift")

    interval = action.get("A_ci95_frames", [None, None])
    if any(value is None for value in interval) or interval[0] > interval[1]:
        errors.append(f"{name} invalid interval {interval!r}")

    null_records = action.get("null_records", [])
    null_passes = []
    for record in null_records:
        median = float(record["median"])
        lower, upper = (float(value) for value in record["ci95"])
        halfwidth = max(abs(lower - median), abs(upper - median))
        metric = abs(median) + halfwidth
        recorded_metric = float(record["abs_median_plus_halfwidth"])
        if abs(metric - recorded_metric) > 1.0e-12:
            errors.append(f"{name} {record['label']} null metric drift")
        implied_pass = metric < 0.125
        if bool(record["passes_0p125"]) != implied_pass:
            errors.append(f"{name} {record['label']} null pass drift")
        null_passes.append(implied_pass)
    if bool(action["null_gate_passed"]) != (
        bool(null_passes) and all(null_passes)
    ):
        errors.append(f"{name} aggregate null gate drift")
    return errors


def audit_step_action(name: str, action: dict) -> list[str]:
    errors: list[str] = []
    if action.get("reason") and "abs_delta_r_ci95_frames" not in action:
        if action.get("category") != "INDETERMINATE":
            errors.append(f"{name} reason-bearing step is not INDETERMINATE")
        return errors
    lower, upper = (float(value) for value in action["abs_delta_r_ci95_frames"])
    null_median = float(action["delta_null_median_frames"])
    null_lower, null_upper = (
        float(value) for value in action["delta_null_ci95_frames"]
    )
    null_halfwidth = max(
        abs(null_lower - null_median), abs(null_upper - null_median)
    )
    null_gate = abs(null_median) + null_halfwidth < 0.125
    if bool(action["null_gate_passed"]) != null_gate:
        errors.append(f"{name} step null gate drift")
    negative = float(action["delta_r_median_frames"]) < 0.0
    if not null_gate:
        implied = "VOID_NULL_GATE"
    elif not negative:
        implied = "KILL"
    elif lower >= 0.50:
        implied = "SURVIVE"
    elif lower >= 0.25:
        implied = "NARROWED"
    elif upper < 0.25:
        implied = "KILL"
    else:
        implied = "INDETERMINATE"
    if action.get("category") != implied:
        errors.append(
            f"{name} category {action.get('category')!r} "
            f"!= numeric fields {implied!r}"
        )
    return errors


def detailed_ladder_categories(robustness: dict) -> tuple[list[str], ...]:
    parameter = sorted(
        {
            row["action"]["category"]
            for row in robustness.get("parameter_ladder", [])
        }
    )
    radial = sorted(
        {row["category"] for row in robustness.get("radial_ladder", [])}
    )
    step = sorted(
        {row["category"] for row in robustness.get("step_ladder", [])}
    )
    return parameter, radial, step


def detailed_audit_classification(measurement: dict) -> str:
    primary = measurement["primary_actionability"]["category"]
    categories = detailed_ladder_categories(measurement["robustness"])
    changed = any(
        category != primary
        for group in categories
        for category in group
    )
    return "NOT ROBUST" if changed else primary


def audit(commission: dict, measurement: dict) -> list[str]:
    errors: list[str] = []

    controls = commission.get("controls", [])
    green = sum(bool(control.get("green")) for control in controls)
    plants = [
        plant for control in controls for plant in control.get("plants", [])
    ]
    red = sum(bool(plant.get("red")) for plant in plants)
    summary = commission.get("summary", {})
    expected_commission = {
        "controls_green": green,
        "controls_total": len(controls),
        "plants_red": red,
        "plants_total": len(plants),
        "all_passed": green == len(controls) and red == len(plants),
    }
    if summary != expected_commission:
        errors.append(
            f"commission summary {summary!r} != detail {expected_commission!r}"
        )
    input_hashes = commission.get("input_sha256", {})
    if not input_hashes:
        errors.append("commission input hashes missing")
    for relative, expected_hash in input_hashes.items():
        path = LANE / relative
        if not path.is_file():
            errors.append(f"commission input is missing: {relative}")
        elif file_sha256(path) != expected_hash:
            errors.append(f"commission input hash drift: {relative}")

    commission_record = measurement.get("commission", {})
    commission_path = Path(commission_record.get("path", ""))
    if not commission_path.is_file():
        errors.append("measurement commission artifact is missing")
    elif file_sha256(commission_path) != commission_record.get("sha256"):
        errors.append("measurement commission hash drift")
    if commission_record.get("summary") != summary:
        errors.append("measurement commission summary drift")

    if not measurement.get("capture_inventory_after_identical"):
        errors.append("capture inventory was not preserved")
    before = measurement.get("capture_inventory_before", {})
    expected_counts = {
        "grid_sw1": 91,
        "grid_sw4": 55,
        "grid_sw10": 23,
        "fabric_f11_sw5": 109,
        "ruler_f11_sw7": 65,
    }
    got_counts = {
        label: value.get("count") for label, value in before.items()
    }
    if got_counts != expected_counts:
        errors.append(
            f"capture counts {got_counts!r} != registered {expected_counts!r}"
        )

    cache_records = measurement.get("cache", {})
    for label, record in cache_records.items():
        path = Path(record["path"]).resolve()
        try:
            path.relative_to(OUT.resolve())
        except ValueError:
            errors.append(f"{label} cache lies outside out/: {path}")
            continue
        if not path.is_file():
            errors.append(f"{label} cache is missing: {path}")
        elif file_sha256(path) != record["sha256"]:
            errors.append(f"{label} cache hash drift")

    primary = measurement.get("primary_actionability", {})
    errors.extend(audit_combined_action("primary", primary))

    robustness = measurement.get("robustness", {})
    for index, row in enumerate(robustness.get("parameter_ladder", [])):
        errors.extend(
            audit_combined_action(f"parameter[{index}]", row["action"])
        )
    for index, row in enumerate(robustness.get("radial_ladder", [])):
        errors.extend(audit_combined_action(f"radial[{index}]", row))
    for index, row in enumerate(robustness.get("step_ladder", [])):
        errors.extend(audit_step_action(f"step[{index}]", row))

    primary_category = primary.get("category")
    if robustness.get("primary_category") != primary_category:
        errors.append("robustness primary category does not match primary")
    detail_groups = detailed_ladder_categories(robustness)
    for key, derived in zip(
        ("parameter_categories", "radial_categories", "step_categories"),
        detail_groups,
        strict=True,
    ):
        if robustness.get(key) != derived:
            errors.append(f"{key} does not match detailed ladder rows")
    ladder_categories = {
        category for group in detail_groups for category in group
    }
    changed = any(category != primary_category for category in ladder_categories)
    if bool(robustness.get("any_category_changed")) != changed:
        errors.append("robustness change flag does not match ladder categories")
    implied_audit = "NOT ROBUST" if changed else primary_category
    if robustness.get("audit_classification") != implied_audit:
        errors.append(
            f"audit classification {robustness.get('audit_classification')!r} "
            f"!= implied {implied_audit!r}"
        )

    return errors


def report_section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end < 0 else text[start:end]


def audit_report(text: str, commission: dict, measurement: dict) -> list[str]:
    errors: list[str] = []
    primary = measurement["primary_actionability"]
    interval = primary["A_ci95_frames"]
    section_one = report_section(text, "## 1. Verdict")
    expected_a = (
        f"A = {primary['A_min_abs_subject_median_frames']:.4f} frames, "
        f"stratified tile-bootstrap 95% CI "
        f"[{interval[0]:.4f}, {interval[1]:.4f}]"
    )
    expected_verdict = detailed_audit_classification(measurement)
    if f"**{expected_verdict}.**" not in section_one:
        errors.append(f"section 1 does not file {expected_verdict}")
    if expected_a not in section_one:
        errors.append(f"section 1 lacks exact primary string {expected_a!r}")

    section_five = report_section(text, "## 5. Primary measurement")
    section_five_ascii = section_five.replace("−", "-")
    for label in ("grid_sw4", "fabric_f11_sw5", "ruler_f11_sw7"):
        summary = measurement["primary_stack_summaries"][label]
        delta_r = summary["summaries"]["delta_r"]["median"]
        if f"{delta_r:+.4f}".replace("+", "") not in section_five_ascii:
            errors.append(f"section 5 lacks {label} dR {delta_r:+.4f}")
        valid = f"{summary['n_tiles_valid']}/{summary['n_tiles_total']}"
        if valid not in section_five:
            errors.append(f"section 5 lacks {label} valid count {valid}")

    section_six = report_section(text, "## 6. Stress tests")
    q2 = next(
        row
        for row in measurement["robustness"]["radial_ladder"]
        if row.get("radius_group") == "q2"
    )
    q2_interval = q2["A_ci95_frames"]
    expected_q2 = (
        f"`A={q2['A_min_abs_subject_median_frames']:.4f} "
        f"[{q2_interval[0]:.4f},{q2_interval[1]:.4f}]`"
    )
    compact_six = section_six.replace(" ", "")
    if expected_q2.replace(" ", "") not in compact_six:
        errors.append(f"section 6 lacks exact Q2 string {expected_q2!r}")
    registered_96 = [
        row
        for row in measurement["robustness"]["parameter_ladder"]
        if row["arm"] == "registered" and row["tile_side_plane_px"] == 96
    ]
    null_96 = max(
        record["abs_median_plus_halfwidth"]
        for row in registered_96
        for record in row["action"]["null_records"]
    )
    if f"{null_96:.4f}" not in section_six or "0.125" not in section_six:
        errors.append("section 6 lacks exact registered-96 null failure")

    section_four = report_section(text, "## 4. Commissioning")
    summary = commission["summary"]
    expected_controls = (
        f"{summary['controls_green']}/{summary['controls_total']} "
        "controls GREEN"
    )
    expected_plants = (
        f"{summary['plants_red']}/{summary['plants_total']} planted defects RED"
    )
    if expected_controls not in section_four:
        errors.append(f"section 4 lacks {expected_controls!r}")
    if expected_plants not in section_four:
        errors.append(f"section 4 lacks {expected_plants!r}")

    section_seven = report_section(text, "## 7. What changes in the Rust source")
    if "**Nothing changes in Rust as a direct result of this verdict.**" not in section_seven:
        errors.append("section 7 lacks explicit no-Rust-change disposition")
    for module in ("optics.rs", "pyramid.rs", "merge.rs", "merge_cmd.rs"):
        if module not in section_seven:
            errors.append(f"section 7 does not name {module}")

    section_nine = report_section(text, "## 9. Reproduction")
    for label, record in measurement["cache"].items():
        if record["sha256"] not in section_nine:
            errors.append(f"section 9 lacks current {label} cache hash")
    return errors


def main() -> int:
    with (OUT / "commission.json").open("r", encoding="utf-8") as handle:
        commission = json.load(handle)
    with (OUT / "measurement.json").open("r", encoding="utf-8") as handle:
        measurement = json.load(handle)
    report_text = REPORT.read_text(encoding="utf-8")

    untreated_errors = audit(commission, measurement)
    controls = [
        {
            "name": "V1_detailed_artifacts_imply_recorded_verdict",
            "green": not untreated_errors,
            "errors": untreated_errors,
            "plants": [],
        }
    ]

    planted_a = copy.deepcopy(measurement)
    planted_a["primary_actionability"][
        "A_min_abs_subject_median_frames"
    ] += 0.125
    controls[0]["plants"].append(
        {
            "name": "VP1_falsify_headline_A",
            "red": bool(audit(commission, planted_a)),
        }
    )

    planted_verdict = copy.deepcopy(measurement)
    planted_robustness = planted_verdict["robustness"]
    planted_robustness["parameter_categories"] = ["SURVIVE"]
    planted_robustness["radial_categories"] = ["SURVIVE"]
    planted_robustness["step_categories"] = ["SURVIVE"]
    planted_robustness["any_category_changed"] = False
    planted_robustness["audit_classification"] = "SURVIVE"
    controls[0]["plants"].append(
        {
            "name": "VP2_hide_ladder_flip",
            "red": bool(audit(commission, planted_verdict)),
        }
    )

    planted_hash = copy.deepcopy(measurement)
    first_cache = next(iter(planted_hash["cache"].values()))
    first_cache["sha256"] = "0" * 64
    controls[0]["plants"].append(
        {
            "name": "VP3_falsify_cache_hash",
            "red": bool(audit(commission, planted_hash)),
        }
    )

    planted_summary = copy.deepcopy(commission)
    planted_summary["summary"]["plants_red"] -= 1
    controls[0]["plants"].append(
        {
            "name": "VP4_false_green_commission_summary",
            "red": bool(audit(planted_summary, measurement)),
        }
    )

    report_errors = audit_report(report_text, commission, measurement)
    report_control = {
        "name": "V2_report_matches_machine_readable_result",
        "green": not report_errors,
        "errors": report_errors,
        "plants": [],
    }
    planted_report_verdict = report_text.replace(
        "**NOT ROBUST.**", "**SURVIVE.**", 1
    )
    report_control["plants"].append(
        {
            "name": "VP5_flip_section_one_verdict",
            "red": bool(
                audit_report(planted_report_verdict, commission, measurement)
            ),
        }
    )
    planted_report_a = report_text.replace("A = 0.5367", "A = 0.6367", 1)
    report_control["plants"].append(
        {
            "name": "VP6_change_section_one_A",
            "red": bool(
                audit_report(planted_report_a, commission, measurement)
            ),
        }
    )
    planted_report_null = report_text.replace("0.1389", "0.0389", 1)
    report_control["plants"].append(
        {
            "name": "VP7_hide_registered_96px_null_failure",
            "red": bool(
                audit_report(
                    planted_report_null, commission, measurement
                )
            ),
        }
    )
    first_report_hash = next(iter(measurement["cache"].values()))["sha256"]
    planted_report_hash = report_text.replace(
        first_report_hash, "0" * 64, 1
    )
    report_control["plants"].append(
        {
            "name": "VP8_falsify_printed_cache_hash",
            "red": bool(
                audit_report(
                    planted_report_hash, commission, measurement
                )
            ),
        }
    )
    controls.append(report_control)

    green_count = sum(control["green"] for control in controls)
    plants = [plant for control in controls for plant in control["plants"]]
    red_count = sum(plant["red"] for plant in plants)
    passed = green_count == len(controls) and red_count == len(plants)
    result = {
        "schema": 1,
        "scope": (
            "artifact/regression verification only; independent scientific "
            "verification is reported separately"
        ),
        "summary": {
            "controls_green": green_count,
            "controls_total": len(controls),
            "plants_red": red_count,
            "plants_total": len(plants),
            "all_passed": passed,
        },
        "filed_verdict": measurement["robustness"]["audit_classification"],
        "primary_actionability": measurement["primary_actionability"],
        "commission_summary_recomputed": commission["summary"],
        "controls": controls,
    }
    write_json(OUT / "verification.json", result)
    print(
        f"verification: controls {green_count}/{len(controls)} GREEN; "
        f"plants {red_count}/{len(plants)} RED; "
        f"verdict {result['filed_verdict']}"
    )
    print(f"wrote {OUT / 'verification.json'}")
    return 0 if passed else 3


if __name__ == "__main__":
    raise SystemExit(main())
