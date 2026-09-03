"""Independent checker for the A2 re-scope audit record."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
REPO = LANE.parent.parent

EXPECTED_GATES = {
    "direct_mechanism",
    "mechanism_commissioned",
    "cancellation_resistant",
    "reproducible_and_current",
    "tone_confound_excluded",
    "single_depth_defocus_excluded",
    "diffraction_excluded",
}


def finite_number(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def valid_treatment_result(result: object) -> bool:
    if not isinstance(result, dict):
        return False
    text_fields = ("record_id", "subject", "treatment", "source_artifact")
    numeric_fields = (
        "baseline_master_base",
        "treated_master_base",
        "target_base",
        "null_delta",
        "null_abs_limit",
        "detail_retention",
        "detail_floor",
    )
    if not all(
        isinstance(result.get(name), str) and result[name].strip()
        for name in text_fields
    ):
        return False
    if not re.fullmatch(r"[0-9a-fA-F]{40}", str(result.get("code_commit", ""))):
        return False
    if not all(finite_number(result.get(name)) for name in numeric_fields):
        return False
    if result["null_abs_limit"] < 0:
        return False
    return (
        abs(result["treated_master_base"] - result["target_base"])
        < abs(result["baseline_master_base"] - result["target_base"])
        and abs(result["null_delta"]) <= result["null_abs_limit"]
        and result["detail_retention"] >= result["detail_floor"]
        and result.get("zero_magnitude_null") is True
        and result.get("wrong_sign_worsens") is True
    )


def valid_treatment_results(results: object) -> bool:
    return (
        isinstance(results, list)
        and bool(results)
        and all(valid_treatment_result(result) for result in results)
    )


def aperture_scaling_statistic(payload: object) -> float | None:
    if not isinstance(payload, dict):
        return None
    apertures = payload.get("aperture_f_numbers")
    endpoints = payload.get("a2_endpoint_values")
    references = payload.get("diffraction_reference_values")
    if not (
        isinstance(apertures, list)
        and isinstance(endpoints, list)
        and isinstance(references, list)
        and len(apertures) >= 3
        and len(apertures) == len(endpoints) == len(references)
        and all(finite_number(value) and value > 0 for value in apertures)
        and all(
            apertures[index] < apertures[index + 1]
            for index in range(len(apertures) - 1)
        )
        and all(finite_number(value) for value in endpoints)
        and all(finite_number(value) for value in references)
    ):
        return None
    reference_steps = [
        references[index + 1] - references[index]
        for index in range(len(references) - 1)
    ]
    if not (
        all(step > 0 for step in reference_steps)
        or all(step < 0 for step in reference_steps)
    ):
        return None
    endpoint_scale = max(abs(value) for value in endpoints)
    reference_scale = max(abs(value) for value in references)
    if endpoint_scale <= 1e-12 or reference_scale <= 1e-12:
        return None
    endpoint_fractional_range = (
        max(endpoints) - min(endpoints)
    ) / endpoint_scale
    reference_fractional_range = (
        max(references) - min(references)
    ) / reference_scale
    return abs(reference_fractional_range - endpoint_fractional_range)


def valid_aperture_record(
    record: object,
    artifact_payloads: dict[str, bytes] | None = None,
) -> bool:
    if not isinstance(record, dict):
        return False
    if not all(
        isinstance(record.get(name), str) and record[name].strip()
        for name in (
            "record_id",
            "subject",
            "source_artifact",
            "discriminator",
        )
    ):
        return False
    if not re.fullmatch(r"[0-9a-fA-F]{40}", str(record.get("code_commit", ""))):
        return False
    expected_hash = str(record.get("source_sha256", ""))
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
        return False
    source = record["source_artifact"]
    try:
        if artifact_payloads is not None and source in artifact_payloads:
            raw = artifact_payloads[source]
        else:
            path = Path(source)
            if not path.is_absolute():
                path = REPO / path
            raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest().lower() != expected_hash.lower():
            return False
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return False
    if (
        payload.get("capture_set") != "7-aperture-pairs"
        or payload.get("subject") != record["subject"]
    ):
        return False
    derived_statistic = aperture_scaling_statistic(payload)
    statistic = record.get("separation_statistic")
    threshold = record.get("predeclared_threshold")
    return (
        derived_statistic is not None
        and finite_number(statistic)
        and finite_number(threshold)
        and threshold >= 0.5
        and math.isclose(
            statistic,
            derived_statistic,
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        and derived_statistic >= threshold
        and record.get("discriminator") == "fractional-range-separation"
        and record.get("conclusion") == "separable_from_diffraction"
        and record.get("defocus_held_fixed") is True
    )


def valid_aperture_records(
    records: object,
    artifact_payloads: dict[str, bytes] | None = None,
) -> bool:
    return (
        isinstance(records, list)
        and bool(records)
        and all(
            valid_aperture_record(record, artifact_payloads)
            for record in records
        )
    )


def commissioned_record(record: dict) -> bool:
    def complete(pair: object) -> bool:
        return (
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(value, int) for value in pair)
            and pair[1] > 0
            and pair[0] == pair[1]
        )

    return (
        record.get("commission_status") == "COMMISSIONED"
        and complete(record.get("controls"))
        and complete(record.get("plants"))
        and record.get("checker_status") == "PASS"
        and complete(record.get("checker_plants"))
    )


def _nonzero_literal(node: ast.AST | None) -> bool:
    if node is None:
        return False
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError):
        return False
    return isinstance(value, (int, float)) and value != 0


def _is_main_call(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "main"
    )


def potency_failure_propagates(tree: ast.Module) -> bool:
    """Accept only a direct, reachable nonzero exit in the `if fail` branch."""
    main = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        ),
        None,
    )
    if main is None or main.decorator_list:
        return False

    main_invoked_uncaught = False
    return_is_process_exit = False
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        for statement in node.body:
            if (
                isinstance(statement, ast.Expr)
                and _is_main_call(statement.value)
            ):
                main_invoked_uncaught = True
            if (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and statement.value.func.value.id == "sys"
                and statement.value.func.attr == "exit"
                and statement.value.args
                and _is_main_call(statement.value.args[0])
            ):
                main_invoked_uncaught = True
                return_is_process_exit = True
            if (
                isinstance(statement, ast.Raise)
                and isinstance(statement.exc, ast.Call)
                and isinstance(statement.exc.func, ast.Name)
                and statement.exc.func.id == "SystemExit"
                and statement.exc.args
                and _is_main_call(statement.exc.args[0])
            ):
                main_invoked_uncaught = True
                return_is_process_exit = True

    if not main_invoked_uncaught:
        return False

    for branch in main.body:
        if not (
            isinstance(branch, ast.If)
            and isinstance(branch.test, ast.Name)
            and "fail" in branch.test.id.lower()
        ):
            continue
        for statement in branch.body:
            if isinstance(statement, ast.Raise):
                if (
                    isinstance(statement.exc, ast.Call)
                    and isinstance(statement.exc.func, ast.Name)
                    and statement.exc.func.id == "SystemExit"
                ):
                    if (
                        statement.exc.args
                        and _nonzero_literal(statement.exc.args[0])
                    ):
                        return True
                elif main_invoked_uncaught:
                    return True
                break
            if isinstance(statement, ast.Return):
                if (
                    return_is_process_exit
                    and _nonzero_literal(statement.value)
                ):
                    return True
                break
            if (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and statement.value.func.value.id == "sys"
                and statement.value.func.attr == "exit"
            ):
                if (
                    main_invoked_uncaught
                    and statement.value.args
                    and _nonzero_literal(statement.value.args[0])
                ):
                    return True
                break
            if (
                isinstance(statement, ast.Pass)
                or (
                    isinstance(statement, ast.Expr)
                    and (
                        isinstance(statement.value, ast.Constant)
                        or (
                            isinstance(statement.value, ast.Call)
                            and isinstance(statement.value.func, ast.Name)
                            and statement.value.func.id == "print"
                        )
                    )
                )
            ):
                continue
            # Compound control flow could catch, bypass, or precede the exit.
            # Fail closed rather than claiming process propagation.
            break
    return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def derive_gates(
    observations: dict,
    aperture_payloads: dict[str, bytes] | None = None,
) -> dict[str, bool]:
    citations = observations["citations"]
    intervention = observations["causal_intervention"]
    commands = observations["predecessor_commands"]
    generator = observations["generator_checker"]
    tone = observations["tone_witness"]
    defocus = observations["defocus"]
    diffraction = observations["diffraction"]
    standing = observations["standing"]
    current = observations["current_repaired_record"]
    order = observations["commit_order"]

    slopes = [
        value
        for group in tone["positive_affine_slopes_common_to_fixed"].values()
        for value in group.values()
    ]
    sign_flip = tone["fixed_paper_theta"] * tone["common_master_paper_theta"] < 0
    real_curve_present = (
        "real claw curve available: True"
        in commands["curve_classifier_commission"]["stdout"]
    )
    commissioned_path_matches = not (
        generator["build_veilmap_commission_tests_drift_fitter"]
        and generator["build_veilmap_measurement_uses_track_fitter"]
    )
    treatment_is_valid = valid_treatment_results(
        intervention["claw_base_or_coarse_treatment_results"]
    )
    aperture_is_valid = valid_aperture_records(
        diffraction["a2_aperture_endpoint_records"],
        aperture_payloads,
    )
    newer_result_is_adverse = (
        order["triage_is_ancestor_of_repair"]
        and current["verdict"] in {"NOT ROBUST", "KILL"}
        and commissioned_record(current)
    )
    return {
        "direct_mechanism": treatment_is_valid
        and not citations["origin_limits_mechanism"]["found"]
        and not citations["veilmap_missing_merge_cross_reference"]["found"],
        "mechanism_commissioned": real_curve_present
        and commands["curve_classifier_commission"]["exit_code"] == 0
        and commands["veilmap_commission"]["exit_code"] == 0
        and commands["veilmap_potency"]["exit_code"] == 0
        and generator["build_veilmap_potency_propagates_failure"]
        and generator["mechanism_specific_red_plant_found"]
        and commissioned_path_matches,
        "cancellation_resistant": generator["mechanism_specific_red_plant_found"]
        and not generator["build_veilmap_plant_imports_production_gather"],
        "reproducible_and_current": standing[
            "older_mechanism_result_reproducible"
        ]
        and not newer_result_is_adverse,
        "tone_confound_excluded": bool(slopes)
        and all(value > 0 for value in slopes)
        and not sign_flip,
        "single_depth_defocus_excluded": defocus[
            "curve_classifier_has_comparable_single_depth_null"
        ]
        and not defocus["m63_single_depth_false_positive_documented"],
        "diffraction_excluded": aperture_is_valid,
    }


def validate(
    record: dict,
    *,
    check_hashes: bool = True,
    aperture_payloads: dict[str, bytes] | None = None,
) -> list[str]:
    errors: list[str] = []
    gates = record.get("gates", {})
    observations = record.get("observations", {})
    if set(gates) != EXPECTED_GATES:
        errors.append("wrong gate set")
        return errors

    derived = derive_gates(observations, aperture_payloads)
    for name, expected in derived.items():
        if gates[name].get("pass") != expected:
            errors.append(f"{name}: gate disagrees with independent derivation")

    passed = sum(derived.values())
    decision = "SURVIVES_AUDIT" if passed == len(EXPECTED_GATES) else "STOP_DO_NOT_BUILD"
    if passed != record.get("gates_passed"):
        errors.append("stale gate count")
    if record.get("gates_total") != len(EXPECTED_GATES):
        errors.append("stale gate total")
    if record.get("decision") != decision:
        errors.append("decision does not follow fail-closed lookup")

    current = observations["current_repaired_record"]
    measurement_record = json.loads(
        (LANE / "out" / "measurement.json").read_text(encoding="utf-8")
    )
    commission_record = json.loads(
        (LANE / "out" / "commission.json").read_text(encoding="utf-8")
    )
    check_record = json.loads(
        (LANE / "out" / "check.json").read_text(encoding="utf-8")
    )
    primary = measurement_record["bee"]["primary"]
    means = primary["means"]
    theta = (
        (means["master"] - means["background"])
        / (means["foreground"] - means["background"])
    )
    if not math.isclose(
        theta,
        current["independently_derived_theta"],
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        errors.append("independent theta arithmetic is stale")
    expected_current = {
        "commission_status": commission_record["status"],
        "controls": [
            commission_record["controls_passed"],
            commission_record["controls_total"],
        ],
        "plants": [
            commission_record["plants_red"],
            commission_record["plants_total"],
        ],
        "checker_status": check_record["status"],
        "checker_plants": [
            check_record["self_commissioning"]["plants_red"],
            check_record["self_commissioning"]["plants_total"],
        ],
        "recorded_theta": primary["theta"],
        "theta_ci95": primary["theta_ci95"],
        "denominator": primary["denominator"],
        "detail_ci95": primary["detail_margin_ci95"],
        "failed_gates": [
            name
            for name, passed in measurement_record["required_gates"].items()
            if not passed
        ],
        "verdict": measurement_record["verdict"],
    }
    for field, expected in expected_current.items():
        if current.get(field) != expected:
            errors.append(f"current repaired record is stale: {field}")

    tone = observations["tone_witness"]
    slopes = [
        value
        for group in tone["positive_affine_slopes_common_to_fixed"].values()
        for value in group.values()
    ]
    observed_flip = (
        tone["fixed_paper_theta"] * tone["common_master_paper_theta"] < 0
    )
    if not slopes or not all(value > 0 for value in slopes):
        errors.append("tone witness is not strictly increasing")
    if tone.get("theta_sign_flips") != observed_flip:
        errors.append("tone sign-flip flag is stale")
    generator_checker = observations["generator_checker"]
    artifacts = observations["artifacts"]
    standing = observations["standing"]
    if (
        artifacts["focus_curve_reproducible_from_raw"]
        != (artifacts["focus_curve_raw_count"] == 299)
    ):
        errors.append("focus-curve reproducibility flag is stale")
    if (
        standing["older_mechanism_result_reproducible"]
        != artifacts["predecessor_mechanism_master_available"]
    ):
        errors.append("mechanism reproducibility flag is stale")

    intervention = observations["causal_intervention"]
    treatment_results = intervention["claw_base_or_coarse_treatment_results"]
    treatment_valid = valid_treatment_results(treatment_results)
    if treatment_results and not treatment_valid:
        errors.append("causal intervention record is malformed")
    if intervention["observed"] != treatment_valid:
        errors.append("causal intervention flag is stale")

    potency_tree = ast.parse(
        (
            REPO / "experiments" / "BUILD-VEILMAP" / "potency.py"
        ).read_text(encoding="utf-8")
    )
    potency_propagates = potency_failure_propagates(potency_tree)
    if (
        generator_checker["build_veilmap_potency_propagates_failure"]
        != potency_propagates
    ):
        errors.append("potency exit-status audit is stale")

    order = observations["commit_order"]
    actual_ancestor = (
        subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                order["triage_commit"],
                order["repaired_measurement_commit"],
            ],
            cwd=REPO,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    if order["triage_is_ancestor_of_repair"] != actual_ancestor:
        errors.append("recorded commit order disagrees with git")
    expected_adverse = (
        actual_ancestor
        and current["verdict"] in {"NOT ROBUST", "KILL"}
        and commissioned_record(current)
    )
    if standing["newer_result_is_adverse"] != expected_adverse:
        errors.append("newer-result standing flag is stale")

    diffraction = observations["diffraction"]
    aperture_records = diffraction["a2_aperture_endpoint_records"]
    aperture_valid = valid_aperture_records(
        aperture_records,
        aperture_payloads,
    )
    if aperture_records and not aperture_valid:
        errors.append("diffraction aperture endpoint record is malformed")
    if (
        diffraction["a2_endpoint_measured_across_aperture"]
        != aperture_valid
    ):
        errors.append("diffraction endpoint flag is stale")

    if check_hashes:
        for relative, expected in observations["hashes"].items():
            if sha256(REPO / relative) != expected:
                errors.append(f"hash mismatch: {relative}")
    return errors


def main() -> int:
    record_path = LANE / "out" / "rescope-audit.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    errors = validate(record)
    plants = []
    controls = []

    valid_treatment = {
        "record_id": "synthetic-causal-positive",
        "subject": "known-two-layer-target",
        "treatment": "coherence-gated-coarse-merge",
        "source_artifact": "external-fixed-predicate",
        "code_commit": "e4e3939f32213872db9df49832ff4d8456f41a80",
        "baseline_master_base": 0.802,
        "treated_master_base": 0.600,
        "target_base": 0.581,
        "null_delta": 0.001,
        "null_abs_limit": 0.010,
        "detail_retention": 0.99,
        "detail_floor": 0.95,
        "zero_magnitude_null": True,
        "wrong_sign_worsens": True,
    }
    valid_aperture_payload = {
        "subject": "fixed-planar-edge",
        "capture_set": "7-aperture-pairs",
        "aperture_f_numbers": [4.0, 8.0, 16.0],
        "a2_endpoint_values": [0.200, 0.195, 0.190],
        "diffraction_reference_values": [0.100, 0.200, 0.400],
    }
    valid_aperture_bytes = json.dumps(
        valid_aperture_payload,
        sort_keys=True,
    ).encode("utf-8")
    valid_aperture_source = "memory://synthetic-aperture-positive.json"
    valid_aperture_payloads = {
        valid_aperture_source: valid_aperture_bytes,
    }
    valid_aperture = {
        "record_id": "synthetic-aperture-positive",
        "subject": "fixed-planar-edge",
        "source_artifact": valid_aperture_source,
        "source_sha256": hashlib.sha256(valid_aperture_bytes).hexdigest(),
        "code_commit": "e4e3939f32213872db9df49832ff4d8456f41a80",
        "discriminator": "fractional-range-separation",
        "separation_statistic": aperture_scaling_statistic(
            valid_aperture_payload
        ),
        "predeclared_threshold": 0.5,
        "conclusion": "separable_from_diffraction",
        "defocus_held_fixed": True,
    }
    valid_exit_source = ast.parse(
        "def main():\n"
        "    fail = [1]\n"
        "    if fail:\n"
        "        raise SystemExit(1)\n"
        "if __name__ == '__main__':\n"
        "    main()\n"
    )
    controls.extend(
        [
            {
                "name": "structured-causal-result-accepted",
                "pass": valid_treatment_result(valid_treatment),
            },
            {
                "name": "structured-aperture-result-accepted",
                "pass": valid_aperture_record(
                    valid_aperture,
                    valid_aperture_payloads,
                ),
            },
            {
                "name": "nonzero-potency-exit-recognized",
                "pass": potency_failure_propagates(valid_exit_source),
            },
            {
                "name": "commissioned-current-record-recognized",
                "pass": commissioned_record(
                    record["observations"]["current_repaired_record"]
                ),
            },
        ]
    )

    def plant(
        name: str,
        bad: dict,
        expected_error: str,
        *,
        aperture_payloads: dict[str, bytes] | None = None,
    ) -> None:
        reading = validate(
            bad,
            check_hashes=False,
            aperture_payloads=aperture_payloads,
        )
        plants.append(
            {
                "name": name,
                "red": expected_error in reading,
                "expected_error": expected_error,
                "errors": reading,
            }
        )

    bad = copy.deepcopy(record)
    for item in bad["gates"].values():
        item["pass"] = True
    bad["gates_passed"] = len(EXPECTED_GATES)
    bad["decision"] = "SURVIVES_AUDIT"
    plant(
        "false-all-pass",
        bad,
        "direct_mechanism: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    bad["gates"]["reproducible_and_current"]["pass"] = True
    bad["gates_passed"] = 1
    plant(
        "hidden-missing-artifact",
        bad,
        "reproducible_and_current: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    bad["observations"]["tone_witness"]["theta_sign_flips"] = False
    bad["gates"]["tone_confound_excluded"]["pass"] = True
    bad["gates_passed"] = 1
    plant(
        "suppressed-tone-flip",
        bad,
        "tone_confound_excluded: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    order = bad["observations"]["commit_order"]
    order["triage_is_ancestor_of_repair"] = False
    order["repair_is_ancestor_of_triage"] = True
    plant(
        "reversed-commit-order",
        bad,
        "recorded commit order disagrees with git",
    )

    bad = copy.deepcopy(record)
    intervention = bad["observations"]["causal_intervention"]
    intervention["claw_base_or_coarse_treatment_results"] = [valid_treatment]
    intervention["observed"] = True
    citations = bad["observations"]["citations"]
    citations["origin_limits_mechanism"]["found"] = False
    citations["veilmap_missing_merge_cross_reference"]["found"] = False
    plant(
        "direct-mechanism-false-negative",
        bad,
        "direct_mechanism: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    commands = bad["observations"]["predecessor_commands"]
    commands["curve_classifier_commission"]["stdout"] = (
        "real claw curve available: True"
    )
    commands["curve_classifier_commission"]["exit_code"] = 0
    commands["veilmap_commission"]["exit_code"] = 0
    commands["veilmap_potency"]["exit_code"] = 0
    generator = bad["observations"]["generator_checker"]
    generator["build_veilmap_potency_propagates_failure"] = True
    generator["mechanism_specific_red_plant_found"] = True
    generator["build_veilmap_commission_tests_drift_fitter"] = False
    plant(
        "mechanism-commission-false-negative",
        bad,
        "mechanism_commissioned: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    generator = bad["observations"]["generator_checker"]
    generator["mechanism_specific_red_plant_found"] = True
    generator["build_veilmap_plant_imports_production_gather"] = False
    plant(
        "cancellation-false-negative",
        bad,
        "cancellation_resistant: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    defocus = bad["observations"]["defocus"]
    defocus["curve_classifier_has_comparable_single_depth_null"] = True
    defocus["m63_single_depth_false_positive_documented"] = False
    plant(
        "defocus-false-negative",
        bad,
        "single_depth_defocus_excluded: gate disagrees with independent derivation",
    )

    bad = copy.deepcopy(record)
    diffraction = bad["observations"]["diffraction"]
    diffraction["a2_aperture_endpoint_records"] = [valid_aperture]
    diffraction["a2_endpoint_measured_across_aperture"] = True
    plant(
        "diffraction-false-negative",
        bad,
        "diffraction_excluded: gate disagrees with independent derivation",
        aperture_payloads=valid_aperture_payloads,
    )

    bad = copy.deepcopy(record)
    intervention = bad["observations"]["causal_intervention"]
    intervention["claw_base_or_coarse_treatment_results"] = [None]
    intervention["observed"] = True
    plant(
        "direct-null-placeholder",
        bad,
        "causal intervention record is malformed",
    )

    bad = copy.deepcopy(record)
    diffraction = bad["observations"]["diffraction"]
    diffraction["a2_aperture_endpoint_records"] = [None]
    diffraction["a2_endpoint_measured_across_aperture"] = True
    plant(
        "diffraction-null-placeholder",
        bad,
        "diffraction aperture endpoint record is malformed",
    )

    bad = copy.deepcopy(record)
    diffraction = bad["observations"]["diffraction"]
    diffraction["a2_aperture_endpoint_records"] = ["external-aperture-ladder"]
    diffraction["a2_endpoint_measured_across_aperture"] = True
    plant(
        "diffraction-string-placeholder",
        bad,
        "diffraction aperture endpoint record is malformed",
    )

    bad = copy.deepcopy(record)
    bad["observations"]["generator_checker"][
        "build_veilmap_potency_propagates_failure"
    ] = True
    plant(
        "false-potency-propagation",
        bad,
        "potency exit-status audit is stale",
    )

    zero_exit_source = ast.parse(
        "def main():\n"
        "    fail = [1]\n"
        "    if fail:\n"
        "        return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    zero_exit_red = not potency_failure_propagates(zero_exit_source)
    plants.append(
        {
            "name": "potency-return-zero-source",
            "red": zero_exit_red,
            "expected_error": "return 0 does not propagate a potency failure",
            "errors": (
                ["return 0 does not propagate a potency failure"]
                if zero_exit_red
                else []
            ),
        }
    )

    caught_exit_source = ast.parse(
        "def main():\n"
        "    fail = [1]\n"
        "    if fail:\n"
        "        try:\n"
        "            raise SystemExit(7)\n"
        "        except SystemExit:\n"
        "            return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    caught_exit_red = not potency_failure_propagates(caught_exit_source)
    plants.append(
        {
            "name": "potency-caught-nonzero-exit",
            "red": caught_exit_red,
            "expected_error": "caught nonzero exit does not propagate failure",
            "errors": (
                ["caught nonzero exit does not propagate failure"]
                if caught_exit_red
                else []
            ),
        }
    )

    unreachable_exit_source = ast.parse(
        "def main():\n"
        "    fail = [1]\n"
        "    if fail:\n"
        "        return 0\n"
        "        raise SystemExit(7)\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    unreachable_exit_red = not potency_failure_propagates(
        unreachable_exit_source
    )
    plants.append(
        {
            "name": "potency-unreachable-nonzero-exit",
            "red": unreachable_exit_red,
            "expected_error": "unreachable nonzero exit does not propagate failure",
            "errors": (
                ["unreachable nonzero exit does not propagate failure"]
                if unreachable_exit_red
                else []
            ),
        }
    )

    outer_caught_exit_source = ast.parse(
        "def main():\n"
        "    fail = [1]\n"
        "    try:\n"
        "        if fail:\n"
        "            raise SystemExit(7)\n"
        "    except SystemExit:\n"
        "        return 0\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n"
    )
    outer_caught_exit_red = not potency_failure_propagates(
        outer_caught_exit_source
    )
    plants.append(
        {
            "name": "potency-outer-caught-nonzero-exit",
            "red": outer_caught_exit_red,
            "expected_error": "outer-caught exit does not propagate failure",
            "errors": (
                ["outer-caught exit does not propagate failure"]
                if outer_caught_exit_red
                else []
            ),
        }
    )

    zero_aperture_payload = {
        "subject": "fixed-planar-edge",
        "capture_set": "7-aperture-pairs",
        "aperture_f_numbers": [5.6, 8.0, 11.0, 14.0, 18.0],
        "a2_endpoint_values": [0.0] * 5,
        "diffraction_reference_values": [0.0] * 5,
    }
    zero_aperture_bytes = json.dumps(
        zero_aperture_payload,
        sort_keys=True,
    ).encode("utf-8")
    zero_aperture_source = "memory://zero-aperture-placeholder.json"
    zero_aperture_record = copy.deepcopy(valid_aperture)
    zero_aperture_record["source_artifact"] = zero_aperture_source
    zero_aperture_record["source_sha256"] = hashlib.sha256(
        zero_aperture_bytes
    ).hexdigest()
    zero_aperture_record["separation_statistic"] = 0.0
    bad = copy.deepcopy(record)
    diffraction = bad["observations"]["diffraction"]
    diffraction["a2_aperture_endpoint_records"] = [zero_aperture_record]
    diffraction["a2_endpoint_measured_across_aperture"] = True
    plant(
        "diffraction-zero-scaling-placeholder",
        bad,
        "diffraction aperture endpoint record is malformed",
        aperture_payloads={zero_aperture_source: zero_aperture_bytes},
    )

    bad = copy.deepcopy(record)
    current = bad["observations"]["current_repaired_record"]
    current["commission_status"] = "UNCOMMISSIONED"
    current["controls"] = [0, 11]
    current["plants"] = [0, 11]
    current["checker_status"] = "FAIL"
    plant(
        "uncommissioned-adverse-standing",
        bad,
        "newer-result standing flag is stale",
    )

    bad = copy.deepcopy(record)
    current = bad["observations"]["current_repaired_record"]
    current["theta_ci95"] = [999.0, 1000.0]
    current["denominator"] = 999.0
    current["detail_ci95"] = [999.0, 1000.0]
    current["failed_gates"] = []
    plant(
        "stale-current-result-fields",
        bad,
        "current repaired record is stale: theta_ci95",
    )

    all_controls = all(item["pass"] for item in controls)
    all_red = all(item["red"] for item in plants)
    result = {
        "status": "PASS" if not errors and all_controls and all_red else "FAIL",
        "errors": errors,
        "decision": record["decision"],
        "self_commissioning": {
            "controls": controls,
            "controls_passed": sum(item["pass"] for item in controls),
            "controls_total": len(controls),
            "all_controls_passed": all_controls,
            "plants": plants,
            "plants_red": sum(item["red"] for item in plants),
            "plants_total": len(plants),
            "all_plants_red": all_red,
        },
    }
    output = LANE / "out" / "rescope-audit-check.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"checker: {result['status']}")
    print(f"decision: {result['decision']}")
    print(
        "self-controls: "
        f"{result['self_commissioning']['controls_passed']}/"
        f"{result['self_commissioning']['controls_total']} PASS; "
        "self-plants: "
        f"{result['self_commissioning']['plants_red']}/"
        f"{result['self_commissioning']['plants_total']} RED"
    )
    for error in errors:
        print(f"ERROR: {error}")
    print(output)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
