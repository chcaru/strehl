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
EXPECTED_CONTROL_PLANTS = {
    "C1_fixed_external_peak_predicate": {
        "P1_linear_domain_instead_of_log",
    },
    "C2_signed_offsets_and_frame_units": {
        "P2_inverted_vertex_sign",
        "P3_doubled_frame_coordinate",
    },
    "C5_green_pair_null_sensitivity": {
        "P6_shift_G2_by_one_frame",
    },
    "C2b_fixed_external_green_reference": {
        "P9_use_G1_instead_of_two_site_mean",
    },
    "C3_fixed_CFA_layout": {"P4_swap_G2_and_B_sites"},
    "C4_registration_roll_convention": {
        "P5_invert_registration_sign",
    },
    "C6_dose_response_and_ceiling": {
        "P7_clamp_recovered_effect_at_quarter_frame",
    },
    "C7_independent_decoder_contract": {
        "P8_treat_padded_buffer_as_active",
    },
}
EXPECTED_COMMISSION_INPUTS = {
    "fixtures/fixed-curves.json",
    "fixtures/fixed-offset-input.json",
    "fixtures/fixed-offset-predicate.json",
    "fixtures/fixed-predicate.json",
    "src/commission.py",
    "src/lca_lib.py",
}
EXPECTED_CACHE_LABELS = {
    "grid_sw1",
    "grid_sw4",
    "grid_sw10",
    "fabric_f11_sw5",
    "ruler_f11_sw7",
}
EXPECTED_PRIMARY_LABELS = {
    "grid_sw4",
    "fabric_f11_sw5",
    "ruler_f11_sw7",
}
EXPECTED_STEP_LABELS = {"grid_sw1", "grid_sw4", "grid_sw10"}
EXPECTED_RADIAL_GROUPS = {"centre", "q1", "q2", "q3", "q4"}
EXPECTED_PARAMETER_KEYS = {
    (arm, side, baseline, prominence)
    for arm in ("registered", "unregistered")
    for side in (96, 144, 192)
    for baseline in (0.0, 5.0, 10.0)
    for prominence in (1.2, 1.5, 2.0)
}


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


def audit_combined_action(
    name: str,
    action: dict,
    expected_subjects: set[str] | None = None,
) -> list[str]:
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
        if expected_subjects is not None and set(subject) != expected_subjects:
            errors.append(f"{name} subject identities drift")
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
    null_labels = [record.get("label") for record in null_records]
    if len(null_labels) != len(set(null_labels)):
        errors.append(f"{name} duplicate null-record labels")
    if (
        expected_subjects is not None
        and set(null_labels) != expected_subjects
    ):
        errors.append(f"{name} null-record identities drift")
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
    control_names = [control.get("name") for control in controls]
    if len(control_names) != len(set(control_names)):
        errors.append("commission has duplicate control names")
    if set(control_names) != set(EXPECTED_CONTROL_PLANTS):
        errors.append("commission required control identities drift")
    for control in controls:
        name = control.get("name")
        if name not in EXPECTED_CONTROL_PLANTS:
            continue
        plant_names = [
            plant.get("name") for plant in control.get("plants", [])
        ]
        if len(plant_names) != len(set(plant_names)):
            errors.append(f"{name} has duplicate plant names")
        if set(plant_names) != EXPECTED_CONTROL_PLANTS[name]:
            errors.append(f"{name} required plant identities drift")
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
    if not expected_commission["all_passed"]:
        errors.append("commission has a failed control or planted defect")
    input_hashes = commission.get("input_sha256", {})
    if not input_hashes:
        errors.append("commission input hashes missing")
    if set(input_hashes) != EXPECTED_COMMISSION_INPUTS:
        errors.append("commission input identity set drift")
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
    if set(cache_records) != EXPECTED_CACHE_LABELS:
        errors.append("required cache identity set drift")
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
        if path.stem != label:
            errors.append(f"{label} cache path points to {path.stem}")

    primary = measurement.get("primary_actionability", {})
    summaries = measurement.get("primary_stack_summaries", {})
    if set(summaries) != EXPECTED_CACHE_LABELS:
        errors.append("primary stack-summary identity set drift")
    for label, summary_record in summaries.items():
        if summary_record.get("label") != label:
            errors.append(f"{label} stack summary label drift")
    errors.extend(
        audit_combined_action(
            "primary", primary, EXPECTED_PRIMARY_LABELS
        )
    )

    robustness = measurement.get("robustness", {})
    parameter_rows = robustness.get("parameter_ladder", [])
    parameter_keys = [
        (
            row.get("arm"),
            row.get("tile_side_plane_px"),
            float(row.get("baseline_percentile")),
            float(row.get("prominence")),
        )
        for row in parameter_rows
    ]
    if (
        len(parameter_keys) != len(EXPECTED_PARAMETER_KEYS)
        or len(parameter_keys) != len(set(parameter_keys))
        or set(parameter_keys) != EXPECTED_PARAMETER_KEYS
    ):
        errors.append("parameter ladder Cartesian-product identities drift")
    for index, row in enumerate(parameter_rows):
        if set(row.get("valid_tiles", {})) != EXPECTED_PRIMARY_LABELS:
            errors.append(f"parameter[{index}] valid-tile identities drift")
        errors.extend(
            audit_combined_action(
                f"parameter[{index}]",
                row["action"],
                EXPECTED_PRIMARY_LABELS,
            )
        )
    radial_rows = robustness.get("radial_ladder", [])
    radial_groups = [row.get("radius_group") for row in radial_rows]
    if (
        len(radial_groups) != len(EXPECTED_RADIAL_GROUPS)
        or len(radial_groups) != len(set(radial_groups))
        or set(radial_groups) != EXPECTED_RADIAL_GROUPS
    ):
        errors.append("radial ladder identities drift")
    for index, row in enumerate(radial_rows):
        errors.extend(
            audit_combined_action(
                f"radial[{index}]",
                row,
                (
                    EXPECTED_PRIMARY_LABELS
                    if "A_ci95_frames" in row
                    else None
                ),
            )
        )
    step_rows = robustness.get("step_ladder", [])
    step_labels = [row.get("label") for row in step_rows]
    if (
        len(step_labels) != len(EXPECTED_STEP_LABELS)
        or len(step_labels) != len(set(step_labels))
        or set(step_labels) != EXPECTED_STEP_LABELS
    ):
        errors.append("step ladder identities drift")
    for index, row in enumerate(step_rows):
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


def compact_text(text: str) -> str:
    return " ".join(text.split())


def normalise_cell(cell: str) -> str:
    return compact_text(cell.replace("**", ""))


def markdown_row(section: str, key: str) -> list[str] | None:
    matches = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [normalise_cell(cell) for cell in line.strip().strip("|").split("|")]
        if cells and cells[0] == key:
            matches.append(cells)
    return matches[0] if len(matches) == 1 else None


def signed_four(value: float) -> str:
    return f"{float(value):+.4f}".replace("-", "−")


def unsigned_four(value: float) -> str:
    return f"{float(value):.4f}"


def primary_report_cell(summary: dict, field: str) -> str:
    record = summary["summaries"][field]
    lower, upper = record["ci95"]
    return (
        f"{signed_four(record['median'])} "
        f"[{signed_four(lower)}, {signed_four(upper)}]"
    )


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
    primary_row_keys = {
        "grid_sw4": "grid `sw4`",
        "fabric_f11_sw5": "fabric f/11 `sw5`",
        "ruler_f11_sw7": "ruler f/11 `sw7`",
    }
    for label, row_key in primary_row_keys.items():
        summary = measurement["primary_stack_summaries"][label]
        expected_row = [
            row_key,
            f"{summary['n_tiles_valid']}/{summary['n_tiles_total']}",
            primary_report_cell(summary, "delta_r"),
            primary_report_cell(summary, "delta_b"),
            primary_report_cell(summary, "delta_null"),
        ]
        if markdown_row(section_five, row_key) != expected_row:
            errors.append(f"section 5 {label} table row drift")

    primary_order = ("grid_sw4", "fabric_f11_sw5", "ruler_f11_sw7")
    hwhm = " / ".join(
        f"{measurement['primary_stack_summaries'][label]['median_green_hwhm_frames']:.2f}"
        .rstrip("0")
        .rstrip(".")
        for label in primary_order
    )
    red_forfeit = " / ".join(
        f"{100.0 * measurement['primary_stack_summaries'][label]['median_red_gradient_energy_forfeit']:.2f}%"
        for label in primary_order
    )
    blue_forfeit = " / ".join(
        f"{100.0 * measurement['primary_stack_summaries'][label]['median_blue_gradient_energy_forfeit']:.2f}%"
        for label in primary_order
    )
    compact_five = compact_text(section_five)
    if f"{hwhm} frames" not in compact_five:
        errors.append("section 5 green-HWHM sequence drift")
    if red_forfeit not in compact_five or blue_forfeit not in compact_five:
        errors.append("section 5 focus-energy-forfeit sequence drift")

    section_six = report_section(text, "## 6. Stress tests")
    compact_six = compact_text(section_six)
    parameter_rows = measurement["robustness"]["parameter_ladder"]
    if f"there are {len(parameter_rows)} rungs." not in compact_six:
        errors.append("section 6 total parameter-rung count drift")
    unregistered = [
        row for row in parameter_rows if row["arm"] == "unregistered"
    ]
    unregistered_categories = {
        row["action"]["category"] for row in unregistered
    }
    unregistered_a = [
        row["action"]["A_min_abs_subject_median_frames"]
        for row in unregistered
    ]
    expected_unregistered = (
        f"All **{len(unregistered)} unregistered** rungs say "
        f"{next(iter(unregistered_categories))}, with "
        f"`A={min(unregistered_a):.4f}..{max(unregistered_a):.4f}`."
    )
    if (
        len(unregistered_categories) != 1
        or expected_unregistered not in compact_six
    ):
        errors.append("section 6 unregistered-rung summary drift")

    registered_large = [
        row
        for row in parameter_rows
        if row["arm"] == "registered"
        and row["tile_side_plane_px"] in (144, 192)
    ]
    registered_large_categories = {
        row["action"]["category"] for row in registered_large
    }
    registered_large_a = [
        row["action"]["A_min_abs_subject_median_frames"]
        for row in registered_large
    ]
    expected_large = (
        "Registered 144- and 192-pixel tiles: "
        f"**{len(registered_large)}/{len(registered_large)} "
        f"{next(iter(registered_large_categories))}**, "
        f"`A={min(registered_large_a):.4f}.."
        f"{max(registered_large_a):.4f}`."
    )
    if (
        len(registered_large_categories) != 1
        or expected_large not in compact_six
    ):
        errors.append("section 6 registered-large-rung summary drift")

    q2 = next(
        row
        for row in measurement["robustness"]["radial_ladder"]
        if row.get("radius_group") == "q2"
    )
    q2_interval = q2["A_ci95_frames"]
    expected_q2 = (
        f"`A={q2['A_min_abs_subject_median_frames']:.4f} "
        f"[{q2_interval[0]:.4f},{q2_interval[1]:.4f}]`, "
        f"**{q2['category']}**"
    )
    if expected_q2.replace(" ", "") not in compact_six.replace(" ", ""):
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
    registered_96_categories = {
        row["action"]["category"] for row in registered_96
    }
    registered_96_a = {
        round(row["action"]["A_min_abs_subject_median_frames"], 4)
        for row in registered_96
    }
    expected_96 = (
        "Registered 96-pixel tiles: "
        f"**{len(registered_96)}/{len(registered_96)} "
        f"{next(iter(registered_96_categories))}**. "
        f"The effect itself remains `A={next(iter(registered_96_a)):.4f}`, "
        "but the four-tile ruler G1-G2 uncertainty pushes "
        f"`|median|+halfwidth` to **{null_96:.4f}**, "
        "beyond the registered 0.125 limit."
    )
    if (
        len(registered_96_categories) != 1
        or len(registered_96_a) != 1
        or expected_96 not in compact_six
    ):
        errors.append("section 6 registered-96 summary drift")

    step_row_keys = {
        "grid_sw1": "`sw1`",
        "grid_sw4": "`sw4`",
        "grid_sw10": "`sw10`",
    }
    step_records = {
        row["label"]: row for row in measurement["robustness"]["step_ladder"]
    }
    for label, row_key in step_row_keys.items():
        step = step_records[label]
        summary = measurement["primary_stack_summaries"][label]
        lower, upper = step["abs_delta_r_ci95_frames"]
        hwhm_value = summary["median_green_hwhm_frames"]
        expected_step_row = [
            row_key,
            str(step["n_tiles"]),
            (
                f"{signed_four(step['delta_r_median_frames'])} "
                f"[{unsigned_four(lower)}, {unsigned_four(upper)}]"
            ),
            f"{hwhm_value:.1f}",
            f"{abs(step['delta_r_median_frames']) / hwhm_value:.4f}",
        ]
        if markdown_row(section_six, row_key) != expected_step_row:
            errors.append(f"section 6 {label} step table row drift")

    section_four = report_section(text, "## 4. Commissioning")
    summary = commission["summary"]
    if not summary.get("all_passed"):
        errors.append("section 4 cannot validate a failed commission")
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
        row_key = f"`{label}.npz`"
        expected_cache_row = [row_key, f"`{record['sha256']}`"]
        if markdown_row(section_nine, row_key) != expected_cache_row:
            errors.append(f"section 9 {label} cache row drift")
    if measurement["environment"]["repo_head"] not in section_nine:
        errors.append("section 9 lacks definitive run HEAD")
    if not all(not record["reused"] for record in measurement["cache"].values()):
        errors.append("definitive measurement unexpectedly reused a cache")
    elif "rebuilt all five caches (`reused=false`)" not in section_nine:
        errors.append("section 9 lacks no-cache-reuse statement")
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

    planted_missing_control = copy.deepcopy(commission)
    planted_missing_control["controls"] = [
        control
        for control in planted_missing_control["controls"]
        if control["name"] != "C2b_fixed_external_green_reference"
    ]
    remaining_plants = [
        plant
        for control in planted_missing_control["controls"]
        for plant in control["plants"]
    ]
    planted_missing_control["summary"] = {
        "controls_green": sum(
            control["green"]
            for control in planted_missing_control["controls"]
        ),
        "controls_total": len(planted_missing_control["controls"]),
        "plants_red": sum(plant["red"] for plant in remaining_plants),
        "plants_total": len(remaining_plants),
        "all_passed": all(
            control["green"]
            for control in planted_missing_control["controls"]
        )
        and all(plant["red"] for plant in remaining_plants),
    }
    planted_missing_control_measurement = copy.deepcopy(measurement)
    planted_missing_control_measurement["commission"]["summary"] = (
        planted_missing_control["summary"]
    )
    controls[0]["plants"].append(
        {
            "name": "VP9_delete_required_green_reference_control",
            "red": bool(
                audit(
                    planted_missing_control,
                    planted_missing_control_measurement,
                )
            ),
        }
    )

    planted_missing_cache = copy.deepcopy(measurement)
    planted_missing_cache["cache"].pop("grid_sw1")
    controls[0]["plants"].append(
        {
            "name": "VP10_delete_required_cache_record",
            "red": bool(audit(commission, planted_missing_cache)),
        }
    )

    planted_missing_steps = copy.deepcopy(measurement)
    planted_missing_steps["robustness"]["step_ladder"] = []
    planted_missing_steps["robustness"]["step_categories"] = []
    controls[0]["plants"].append(
        {
            "name": "VP11_delete_required_step_ladder",
            "red": bool(audit(commission, planted_missing_steps)),
        }
    )

    planted_missing_parameters = copy.deepcopy(measurement)
    parameter_rows = planted_missing_parameters["robustness"][
        "parameter_ladder"
    ]
    planted_missing_parameters["robustness"]["parameter_ladder"] = [
        row for row in parameter_rows if row["arm"] == "registered"
    ]
    planted_missing_parameters["robustness"]["parameter_categories"] = (
        sorted(
            {
                row["action"]["category"]
                for row in planted_missing_parameters["robustness"][
                    "parameter_ladder"
                ]
            }
        )
    )
    controls[0]["plants"].append(
        {
            "name": "VP12_delete_parameter_ladder_arm",
            "red": bool(audit(commission, planted_missing_parameters)),
        }
    )

    planted_failed_commission = copy.deepcopy(commission)
    planted_failed_commission["controls"][0]["green"] = False
    planted_failed_commission["summary"] = {
        **planted_failed_commission["summary"],
        "controls_green": (
            planted_failed_commission["summary"]["controls_total"] - 1
        ),
        "all_passed": False,
    }
    planted_failed_measurement = copy.deepcopy(measurement)
    planted_failed_measurement["commission"]["summary"] = (
        planted_failed_commission["summary"]
    )
    controls[0]["plants"].append(
        {
            "name": "VP17_honestly_report_failed_commission",
            "red": bool(
                audit(
                    planted_failed_commission,
                    planted_failed_measurement,
                )
            ),
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
    section_six = report_section(report_text, "## 6. Stress tests")
    planted_section_six = section_six.replace("0.1389", "0.0389", 1)
    planted_report_null = report_text.replace(
        section_six, planted_section_six, 1
    )
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

    section_nine = report_section(report_text, "## 9. Reproduction")
    sw1_hash = measurement["cache"]["grid_sw1"]["sha256"]
    sw4_hash = measurement["cache"]["grid_sw4"]["sha256"]
    planted_section_nine = section_nine.replace(sw1_hash, "X" * 64, 1)
    planted_section_nine = planted_section_nine.replace(
        sw4_hash, sw1_hash, 1
    ).replace("X" * 64, sw4_hash, 1)
    planted_report_swapped_hashes = report_text.replace(
        section_nine, planted_section_nine, 1
    )
    report_control["plants"].append(
        {
            "name": "VP13_swap_printed_cache_hash_labels",
            "red": bool(
                audit_report(
                    planted_report_swapped_hashes,
                    commission,
                    measurement,
                )
            ),
        }
    )

    q2_clause = (
        "`A=0.5170 [0.4237,0.5883]`, **NARROWED**"
    )
    planted_section_six = section_six.replace(
        q2_clause,
        "`A=0.5170 [0.4237,0.5883]`, **SURVIVE**",
        1,
    )
    planted_report_q2 = report_text.replace(
        section_six, planted_section_six, 1
    )
    report_control["plants"].append(
        {
            "name": "VP14_flip_printed_Q2_category",
            "red": bool(
                audit_report(planted_report_q2, commission, measurement)
            ),
        }
    )

    section_five = report_section(report_text, "## 5. Primary measurement")
    planted_section_five = section_five.replace(
        "−1.7866", "−0.7866", 1
    )
    planted_report_delta_b = report_text.replace(
        section_five, planted_section_five, 1
    )
    report_control["plants"].append(
        {
            "name": "VP15_falsify_primary_delta_B",
            "red": bool(
                audit_report(
                    planted_report_delta_b, commission, measurement
                )
            ),
        }
    )

    planted_section_six = section_six.replace(
        "27 unregistered", "26 unregistered", 1
    )
    planted_report_rung_count = report_text.replace(
        section_six, planted_section_six, 1
    )
    report_control["plants"].append(
        {
            "name": "VP16_falsify_parameter_rung_count",
            "red": bool(
                audit_report(
                    planted_report_rung_count, commission, measurement
                )
            ),
        }
    )

    planted_failed_report = report_text.replace(
        "8/8 controls GREEN", "7/8 controls GREEN", 1
    )
    report_control["plants"].append(
        {
            "name": "VP18_print_failed_commission_honestly",
            "red": bool(
                audit_report(
                    planted_failed_report,
                    planted_failed_commission,
                    measurement,
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
