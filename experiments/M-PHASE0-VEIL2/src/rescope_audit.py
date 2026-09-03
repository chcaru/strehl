"""Formally score the evidence cited for A2 by the phase-0 triage.

This audit deliberately does not import any V-VEILCLAW, BUILD-VEILMAP, or
M-PHASE0-VEIL2 producer module. It reads their source, records, and process
behaviour as external evidence.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LANE = HERE.parent
REPO = LANE.parent.parent

TRIAGE_COMMIT = "f7017885c90078d601e459d2c0eba6af2c7120ea"
REPAIRED_COMMIT = "e4e3939f32213872db9df49832ff4d8456f41a80"


def read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def citation(path: str, needle: str) -> dict:
    lines = read(path).splitlines()
    matches = [i + 1 for i, line in enumerate(lines) if needle in line]
    return {
        "path": path,
        "needle": needle,
        "lines": matches,
        "found": bool(matches),
    }


def command(args: list[str], timeout: int = 180) -> dict:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONPATH"] = str(REPO)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        args,
        cwd=REPO,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    return {
        "args": args,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
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


def commissioned_record(record: dict) -> bool:
    def complete(pair: list[int]) -> bool:
        return (
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(value, int) for value in pair)
            and pair[1] > 0
            and pair[0] == pair[1]
        )

    return (
        record["commission_status"] == "COMMISSIONED"
        and complete(record["controls"])
        and complete(record["plants"])
        and record["checker_status"] == "PASS"
        and complete(record["checker_plants"])
    )


def main() -> int:
    v_readme = "experiments/V-VEILCLAW/README.md"
    map_readme = "experiments/BUILD-VEILMAP/README.md"
    v_verify = "docs/research/V-veiling.md"
    blend = "docs/research/BUILD-BLEND.md"
    m63 = "docs/research/M63-bimodality.md"
    current_note = "docs/research/M-PHASE0-VEIL2.md"
    proposal = "docs/proposals/2026-08-sota-path.md"

    cited = {
        "origin_limits_mechanism": citation(v_readme, "lead, not a finding"),
        "veilmap_missing_merge_cross_reference": citation(
            map_readme, "Cross-reference to the merge (NOT DONE)"
        ),
        "independent_verifier_refutes_complete_mechanism": citation(
            v_verify, "The mechanism does not."
        ),
        "base_arms_remove_aura_equally": citation(
            blend, "Both base bands removed the aura equally well"
        ),
        "single_depth_defocus_not_excluded": citation(
            m63, "not excluded.** The statistic does not distinguish"
        ),
        "single_depth_sidelobe_measured": citation(
            m63, "Confirmation on a physically correct single-depth plant"
        ),
        "current_verdict": citation(current_note, "**Verdict:** **NOT ROBUST**"),
        "proposal_requires_treatment_response": citation(
            proposal, "master base moves from 0.802 toward 0.581"
        ),
    }

    old_detector = command(
        [sys.executable, "experiments/ORCH-drift-check/commission_verdict.py"]
    )
    map_commission = command(
        [sys.executable, "experiments/BUILD-VEILMAP/commission.py"]
    )
    map_potency = command(
        [sys.executable, "experiments/BUILD-VEILMAP/potency.py"]
    )

    tracked = git("ls-files", "experiments/V-VEILCLAW", "experiments/BUILD-VEILMAP")
    tracked_files = [z for z in tracked.stdout.splitlines() if z]
    artifact_suffixes = {".csv", ".json", ".npz", ".png", ".tif", ".tiff"}
    tracked_artifacts = [
        z for z in tracked_files if Path(z).suffix.lower() in artifact_suffixes
    ]
    external_artifacts = {
        "real_claw_csv": Path(
            r"C:\dev\strehl-out\V-VEILCLAW\probe2\clawtight.csv"
        ).exists(),
        "ship_v1_bee_master": Path(
            r"C:\dev\strehl-out\SHIP-V1\bee-3-cpl.tiff"
        ).exists(),
        "veilmap_tensor": Path(
            r"C:\dev\strehl-out\BUILD-VEILMAP\tensors\bee-3-cpl.npz"
        ).exists(),
    }

    measurement_path = LANE / "out" / "measurement.json"
    commission_path = LANE / "out" / "commission.json"
    check_path = LANE / "out" / "check.json"
    measurement = json.loads(measurement_path.read_text(encoding="utf-8"))
    commissioned = json.loads(commission_path.read_text(encoding="utf-8"))
    checked = json.loads(check_path.read_text(encoding="utf-8"))
    primary = measurement["bee"]["primary"]
    means = primary["means"]
    independent_theta = (
        (means["master"] - means["background"])
        / (means["foreground"] - means["background"])
    )
    common = measurement["adversarial_falsification"][
        "bee_no_per_frame_normalization"
    ]["score"]
    anchors = measurement["bee"]["paper_anchors_dn"]
    master_anchor = float(anchors["master"])
    positive_slopes = {
        group: {
            frame: master_anchor / float(anchor)
            for frame, anchor in values.items()
        }
        for group, values in anchors.items()
        if isinstance(values, dict)
    }
    slopes = [v for values in positive_slopes.values() for v in values.values()]
    tone = {
        "fixed_paper_theta": primary["theta"],
        "fixed_paper_ci95": primary["theta_ci95"],
        "common_master_paper_theta": common["theta"],
        "common_master_paper_ci95": common["theta_ci95"],
        "positive_affine_slopes_common_to_fixed": positive_slopes,
        "all_slopes_strictly_positive": all(v > 0 for v in slopes),
        "theta_sign_flips": primary["theta"] * common["theta"] < 0,
        "explanation": (
            "Each reference changes only by a positive scalar when moving "
            "between the common-master-paper and per-frame-paper conventions."
        ),
    }

    triage_before_repair = (
        git("merge-base", "--is-ancestor", TRIAGE_COMMIT, REPAIRED_COMMIT).returncode
        == 0
    )
    repair_before_triage = (
        git("merge-base", "--is-ancestor", REPAIRED_COMMIT, TRIAGE_COMMIT).returncode
        == 0
    )
    commit_order = {
        "triage_commit": TRIAGE_COMMIT,
        "repaired_measurement_commit": REPAIRED_COMMIT,
        "triage_is_ancestor_of_repair": triage_before_repair,
        "repair_is_ancestor_of_triage": repair_before_triage,
    }

    relevant_aperture_files = [
        v_readme,
        map_readme,
        v_verify,
        blend,
    ]
    aperture_mentions = {
        path: "7-aperture-pairs" in read(path) for path in relevant_aperture_files
    }
    plant_text = read("experiments/BUILD-VEILMAP/plantdrift.py")
    map_commission_text = read("experiments/BUILD-VEILMAP/commission.py")
    map_fit_text = read("experiments/BUILD-VEILMAP/fitdrift.py")
    potency_text = read("experiments/BUILD-VEILMAP/potency.py")
    potency_tree = ast.parse(potency_text)
    potency_main = next(
        node
        for node in potency_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    potency_returns = [
        node for node in ast.walk(potency_main) if isinstance(node, ast.Return)
    ]
    potency_raises = [
        node for node in ast.walk(potency_main) if isinstance(node, ast.Raise)
    ]
    potency_exit_calls = [
        node
        for node in ast.walk(potency_main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "sys"
        and node.func.attr == "exit"
    ]
    potency_propagates = potency_failure_propagates(potency_tree)
    mechanism_text = read(v_readme) + read(map_readme)
    raw_count = len(list(Path(r"D:\personal\macro\bee-3-cpl").glob("*.ARW")))

    current_record = {
        "commission_status": commissioned["status"],
        "controls": [
            commissioned["controls_passed"],
            commissioned["controls_total"],
        ],
        "plants": [commissioned["plants_red"], commissioned["plants_total"]],
        "checker_status": checked["status"],
        "checker_plants": [
            checked["self_commissioning"]["plants_red"],
            checked["self_commissioning"]["plants_total"],
        ],
        "recorded_theta": primary["theta"],
        "independently_derived_theta": independent_theta,
        "theta_ci95": primary["theta_ci95"],
        "denominator": primary["denominator"],
        "detail_ci95": primary["detail_margin_ci95"],
        "failed_gates": [
            name
            for name, passed in measurement["required_gates"].items()
            if not passed
        ],
        "verdict": measurement["verdict"],
    }

    observations = {
        "citations": cited,
        "predecessor_commands": {
            "curve_classifier_commission": old_detector,
            "veilmap_commission": map_commission,
            "veilmap_potency": map_potency,
        },
        "artifacts": {
            "tracked_files": len(tracked_files),
            "tracked_artifacts": tracked_artifacts,
            "external_available": external_artifacts,
            "focus_curve_raw_count": raw_count,
            "focus_curve_reproducible_from_raw": raw_count == 299,
            "predecessor_mechanism_master_available": external_artifacts[
                "ship_v1_bee_master"
            ],
        },
        "causal_intervention": {
            "required_by_proposal": cited[
                "proposal_requires_treatment_response"
            ]["found"],
            "claw_base_or_coarse_treatment_results": [],
            "observed": False,
        },
        "current_repaired_record": current_record,
        "tone_witness": tone,
        "commit_order": commit_order,
        "generator_checker": {
            "build_veilmap_plant_imports_production_gather": (
                "from veilgrid import gather" in plant_text
            ),
            "build_veilmap_commission_tests_drift_fitter": (
                "fit = vc.DriftFitter(ref)" in map_commission_text
            ),
            "build_veilmap_measurement_uses_track_fitter": (
                "tr = vc.TrackFitter" in map_fit_text
            ),
            "build_veilmap_measurement_uses_poly_solve": (
                "solve_poly(" in map_fit_text
            ),
            "build_veilmap_potency_explicit_returns": len(potency_returns),
            "build_veilmap_potency_explicit_raises": len(potency_raises),
            "build_veilmap_potency_sys_exit_calls": len(potency_exit_calls),
            "build_veilmap_potency_propagates_failure": potency_propagates,
            "mechanism_specific_red_plant_found": (
                "wrong-sign" in mechanism_text or "wrong sign" in mechanism_text
            ),
            "classifier_is_not_mechanism_instrument": True,
        },
        "defocus": {
            "primary_contact_sheet_directly_observed_two_contents": True,
            "curve_classifier_has_comparable_single_depth_null": False,
            "m63_single_depth_false_positive_documented": all(
                cited[name]["found"]
                for name in (
                    "single_depth_defocus_not_excluded",
                    "single_depth_sidelobe_measured",
                )
            ),
        },
        "diffraction": {
            "aperture_mentions_in_cited_evidence": aperture_mentions,
            "current_lane_explicitly_did_not_test_aperture": (
                "It did **not** test lens scatter,\n"
                "diffraction tails, or the `19-razor-edge` / "
                "`7-aperture-pairs` captures."
                in read(current_note)
            ),
            "a2_aperture_endpoint_records": [],
            "a2_endpoint_measured_across_aperture": False,
        },
        "standing": {
            "newer_result_is_adverse": (
                triage_before_repair
                and current_record["verdict"] in {"NOT ROBUST", "KILL"}
                and commissioned_record(current_record)
            ),
            "older_focus_curve_still_reproducible": raw_count == 299,
            "older_mechanism_result_reproducible": external_artifacts[
                "ship_v1_bee_master"
            ],
        },
        "hashes": {
            str(path.relative_to(REPO)): sha256(path)
            for path in (measurement_path, commission_path, check_path)
        },
    }

    gates = {
        "direct_mechanism": {
            "pass": (
                observations["causal_intervention"]["observed"]
                and not (
                    cited["origin_limits_mechanism"]["found"]
                    or cited["veilmap_missing_merge_cross_reference"]["found"]
                )
            ),
            "reason": (
                "The origin labels the base explanation a lead; VEILMAP did not "
                "cross-reference it to the merge; the measured base-arm contrast "
                "did not uniquely buy aura removal."
            ),
        },
        "mechanism_commissioned": {
            "pass": (
                old_detector["exit_code"] == 0
                and "real claw curve available: True" in old_detector["stdout"]
                and map_commission["exit_code"] == 0
                and map_potency["exit_code"] == 0
                and observations["generator_checker"][
                    "build_veilmap_potency_propagates_failure"
                ]
                and observations["generator_checker"][
                    "mechanism_specific_red_plant_found"
                ]
            ),
            "reason": (
                "The available 6/6 run commissions only the synthetic curve "
                "classifier; the real curve is absent, VEILMAP's commission "
                "targets DriftFitter while measurement adds TrackFitter and a "
                "polynomial solve, and no wrong-component/sign plant targets "
                "the base mechanism."
            ),
        },
        "cancellation_resistant": {
            "pass": (
                observations["generator_checker"][
                    "mechanism_specific_red_plant_found"
                ]
                and not observations["generator_checker"][
                    "build_veilmap_plant_imports_production_gather"
                ]
            ),
            "reason": (
                "The load-bearing causal inference has no commissioned plant, "
                "while the drift plant imports the production gather it checks."
            ),
        },
        "reproducible_and_current": {
            "pass": (
                observations["standing"]["older_mechanism_result_reproducible"]
                and not observations["standing"]["newer_result_is_adverse"]
            ),
            "reason": (
                "The focus curve can be regenerated from the 299 RAWs, but the "
                "old mechanism master/output cannot; the newer commissioned "
                "result is adverse rather than confirmatory."
            ),
        },
        "tone_confound_excluded": {
            "pass": tone["all_slopes_strictly_positive"]
            and not tone["theta_sign_flips"],
            "reason": (
                "A strictly increasing per-image affine rescaling flips theta "
                "from +0.7410 to -0.0812."
            ),
        },
        "single_depth_defocus_excluded": {
            "pass": (
                observations["defocus"][
                    "curve_classifier_has_comparable_single_depth_null"
                ]
                and not observations["defocus"][
                    "m63_single_depth_false_positive_documented"
                ]
            ),
            "reason": (
                "The claw contents are directly two-layer, but the detector has "
                "no comparable one-depth edge null and M63 measured such false "
                "positives."
            ),
        },
        "diffraction_excluded": {
            "pass": bool(
                observations["diffraction"]["a2_aperture_endpoint_records"]
            ),
            "reason": (
                "None of the cited A2 evidence measures the endpoint on the "
                "7-aperture-pairs ladder."
            ),
        },
    }
    decision = (
        "SURVIVES_AUDIT"
        if all(item["pass"] for item in gates.values())
        else "STOP_DO_NOT_BUILD"
    )
    result = {
        "claim": "A2 depth-boundary base/coarse pedestal",
        "bias": "toward SURVIVES_AUDIT and building",
        "decision": decision,
        "gates_passed": sum(item["pass"] for item in gates.values()),
        "gates_total": len(gates),
        "gates": gates,
        "observations": observations,
        "versions": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    output = LANE / "out" / "rescope-audit.json"
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"DECISION: {decision}")
    print(
        f"gates: {result['gates_passed']}/{result['gates_total']} PASS; "
        f"{result['gates_total'] - result['gates_passed']} FAIL"
    )
    for name, item in gates.items():
        print(f"{name:<30} {'PASS' if item['pass'] else 'FAIL'}")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
