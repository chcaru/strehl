"""Independent checker for the preregistered S25-hardening search.

The checker imports no fixture, variant, adapter or candidate module.  All
measurements and provenance records arrive as child-process JSON.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VARIANT_IDS = (
    "C0_NATIVE_MIN",
    "V1_FLOOR_ELIG_MIN",
    "V2_GES_OLS",
    "V3_RAMP_GES_OLS",
    "V4_RAMP_GES_OLS_ANGLE",
    "V5_RAMP_GES_TS_ANGLE",
)
ARM_IDS = (
    "base",
    "identity",
    "blur",
    "improvement",
    "sharpen",
    "affine",
    "gamma3",
    "logistic",
)
NOISE_SEEDS = tuple(range(2026090300, 2026090324))
ANGLES = (0.5, 1.0, 5.0, 12.0)
BLUR_RATIO = 0.8944271909999159
IMPROVEMENT_RATIO = 1.25


def is_value(record: object) -> bool:
    return (
        isinstance(record, dict)
        and record.get("status") == "VALUE"
        and isinstance(record.get("value"), (int, float))
        and math.isfinite(float(record["value"]))
        and float(record["value"]) > 0.0
    )


def ratio(record: object, base: float) -> float | None:
    return float(record["value"]) / base if is_value(record) else None


def close_frac(actual: float | None, expected: float, limit: float) -> bool:
    return actual is not None and abs(actual / expected - 1.0) <= limit


def naming_ok(record: object) -> bool:
    if not is_value(record):
        return True
    name = str(record.get("metric_name", "")).lower()
    forbidden = ("mtf", "sfr", "cutoff", "cycles")
    return bool(name) and not any(token in name for token in forbidden)


def controls_ok(
    controls: dict,
    *,
    controls_preceded_score: bool,
) -> dict[str, bool]:
    edge = controls.get("edge", {})
    equal = controls.get("equal", {})
    flat = controls.get("flat", {})
    point_only = controls.get("point_only", {})
    return {
        "controls_preceded_score": controls_preceded_score,
        "eligibility_edge": edge.get("pass") is True,
        "eligibility_equal_refused": equal.get("pass") is False,
        "eligibility_flat_refused": flat.get("pass") is False,
        "eligibility_point_and_lcb": (
            point_only.get("point_pass") is True
            and point_only.get("lcb_pass") is False
            and point_only.get("pass") is False
        ),
    }


def adjudicate_variant(
    variant_id: str,
    candidate: dict,
    controls: dict,
    *,
    controls_preceded_score: bool,
    source_green: bool,
) -> dict[str, object]:
    arms = candidate.get("arms", {})
    base_record = arms.get("base")
    base = float(base_record["value"]) if is_value(base_record) else None

    arm_ratios = {
        arm: ratio(arms.get(arm), base)
        if base is not None else None
        for arm in ARM_IDS
        if arm != "base"
    }
    noise_records = candidate.get("noise", [])
    noise_ratios = [
        ratio(row.get("measurement"), base)
        if isinstance(row, dict) and base is not None else None
        for row in noise_records
    ]
    numeric_noise = [
        value for value in noise_ratios
        if value is not None
    ]
    noise_median = (
        float(sorted(numeric_noise)[11] + sorted(numeric_noise)[12]) / 2.0
        if len(numeric_noise) == 24 else None
    )
    noise_worst = (
        max(abs(value - 1.0) for value in numeric_noise)
        if numeric_noise else None
    )

    angle_rows = {
        float(row["plant_deg"]): row.get("measurement")
        for row in candidate.get("angles", [])
        if isinstance(row, dict)
        and isinstance(row.get("plant_deg"), (int, float))
    }
    angle_details = {}
    angle_gate = len(angle_rows) == 4
    for angle in ANGLES:
        record = angle_rows.get(angle)
        if angle == 5.0:
            measured = (
                float(record["angle_deg"])
                if is_value(record)
                and isinstance(record.get("angle_deg"), (int, float))
                else None
            )
            passed = (
                measured is not None
                and abs(measured - 5.0) <= 0.2
            )
        else:
            measured = (
                float(record["angle_deg"])
                if isinstance(record, dict)
                and isinstance(record.get("angle_deg"), (int, float))
                else None
            )
            passed = (
                isinstance(record, dict)
                and record.get("status") == "REFUSED"
            )
        angle_gate &= passed
        angle_details[str(angle)] = {
            "status": (
                record.get("status")
                if isinstance(record, dict) else "MISSING"
            ),
            "measured_deg": measured,
            "pass": passed,
        }

    control_gates = controls_ok(
        controls,
        controls_preceded_score=controls_preceded_score,
    )
    flat_controls = candidate.get("flat_controls", {})
    flat_gate = (
        isinstance(flat_controls.get("base"), dict)
        and flat_controls["base"].get("status") == "REFUSED"
        and isinstance(flat_controls.get("sharpen"), dict)
        and flat_controls["sharpen"].get("status") == "REFUSED"
    )
    spec = candidate.get("spec", {})
    activation = (
        float(base_record.get("floor_activation_fraction", 0.0))
        if isinstance(base_record, dict) else 0.0
    )
    floor_gate = (
        spec.get("floor") is True and activation > 0.0
    )

    naming_gate = (
        all(naming_ok(record) for record in arms.values())
        and all(
            naming_ok(row.get("measurement"))
            for row in noise_records
            if isinstance(row, dict)
        )
        and candidate.get("absolute_mtf50_status")
        == "UNSUPPORTED_COMPARATIVE_ONLY"
        and candidate.get("frequency_scope")
        == "[0.20,0.25) cycles/native-pixel only"
    )

    gates = {
        "eligible_variant": variant_id != "C0_NATIVE_MIN",
        "source_provenance": bool(source_green),
        "base_numeric": base is not None,
        "identity": (
            arm_ratios.get("identity") is not None
            and abs(arm_ratios["identity"] - 1.0) <= 1e-12
        ),
        "quantitative_blur": close_frac(
            arm_ratios.get("blur"), BLUR_RATIO, 0.05
        ),
        "true_improvement": close_frac(
            arm_ratios.get("improvement"),
            IMPROVEMENT_RATIO,
            0.05,
        ),
        "sharpening": (
            arm_ratios.get("sharpen") is not None
            and arm_ratios["sharpen"] <= 1.01
        ),
        "affine_tone": (
            arm_ratios.get("affine") is not None
            and abs(arm_ratios["affine"] - 1.0) <= 0.01
        ),
        "gamma3_tone": (
            arm_ratios.get("gamma3") is not None
            and abs(arm_ratios["gamma3"] - 1.0) <= 0.01
        ),
        "logistic_tone": (
            arm_ratios.get("logistic") is not None
            and abs(arm_ratios["logistic"] - 1.0) <= 0.01
        ),
        "noise": (
            len(numeric_noise) == 24
            and noise_median is not None
            and abs(noise_median - 1.0) <= 0.03
            and noise_worst is not None
            and noise_worst <= 0.05
        ),
        "angle": angle_gate,
        "flat_roi": flat_gate,
        "floor_exercised": floor_gate,
        "native_naming_and_scope": naming_gate,
        **control_gates,
    }
    admitted = all(gates.values())
    return {
        "admitted": admitted,
        "verdict": (
            "COMPARATIVE_ADMISSIBLE_ON_FROZEN_BATTERY"
            if admitted else "NOT_ADMISSIBLE"
        ),
        "gates": gates,
        "base": base,
        "ratios": {
            **arm_ratios,
            "noise": noise_ratios,
            "noise_median": noise_median,
            "noise_min": min(numeric_noise) if numeric_noise else None,
            "noise_max": max(numeric_noise) if numeric_noise else None,
            "noise_worst_abs": noise_worst,
        },
        "angles": angle_details,
        "flat_controls": {
            key: value.get("status")
            if isinstance(value, dict) else "MISSING"
            for key, value in flat_controls.items()
        },
        "floor_activation_fraction": activation,
        "metric_name": (
            base_record.get("metric_name")
            if isinstance(base_record, dict) else None
        ),
    }


def validate_measurement(measurement: dict) -> dict[str, bool]:
    variants = measurement.get("variants", {})
    exact_variants = (
        measurement.get("variant_ids") == list(VARIANT_IDS)
        and set(variants) == set(VARIANT_IDS)
    )
    exact_rows = exact_variants
    if exact_rows:
        for variant_id in VARIANT_IDS:
            candidate = variants[variant_id]
            exact_rows &= set(candidate.get("arms", {})) == set(ARM_IDS)
            noise = candidate.get("noise", [])
            exact_rows &= len(noise) == 24
            exact_rows &= [
                row.get("seed") for row in noise
                if isinstance(row, dict)
            ] == list(NOISE_SEEDS)
            angles = candidate.get("angles", [])
            exact_rows &= len(angles) == 4
            exact_rows &= [
                float(row.get("plant_deg"))
                for row in angles
                if isinstance(row, dict)
            ] == list(ANGLES)
            exact_rows &= set(candidate.get("flat_controls", {})) == {
                "base", "sharpen"
            }
    return {
        "exact_variant_set": exact_variants,
        "complete_rows": bool(exact_rows),
        "controls_preceded_score": (
            measurement.get("controls_preceded_score") is True
        ),
    }


def literal_value(value: float, angle: float = 5.0) -> dict:
    return {
        "status": "VALUE",
        "value": value,
        "metric_name": "comparative_inverse_pixel_scale",
        "angle_deg": angle,
        "floor_activation_fraction": 0.5,
    }


def literal_controls() -> dict:
    return {
        "edge": {"pass": True},
        "equal": {"pass": False},
        "flat": {"pass": False},
        "point_only": {
            "point_pass": True,
            "lcb_pass": False,
            "pass": False,
        },
    }


def literal_candidate(variant_id: str) -> dict:
    arms = {
        "base": literal_value(1.0),
        "identity": literal_value(1.0),
        "blur": literal_value(BLUR_RATIO),
        "improvement": literal_value(IMPROVEMENT_RATIO),
        "sharpen": literal_value(1.0),
        "affine": literal_value(1.0),
        "gamma3": literal_value(1.0),
        "logistic": literal_value(1.0),
    }
    return {
        "variant_id": variant_id,
        "spec": {
            "floor": variant_id != "C0_NATIVE_MIN",
        },
        "flat_controls": {
            "base": {"status": "REFUSED"},
            "sharpen": {"status": "REFUSED"},
        },
        "arms": arms,
        "noise": [
            {
                "seed": seed,
                "measurement": literal_value(1.0),
            }
            for seed in NOISE_SEEDS
        ],
        "angles": [
            {
                "plant_deg": angle,
                "measurement": (
                    literal_value(1.0, angle=angle)
                    if angle == 5.0
                    else {
                        "status": "REFUSED",
                        "reason": "ANGLE_OUT_OF_RANGE",
                        "angle_deg": angle,
                    }
                ),
            }
            for angle in ANGLES
        ],
        "frequency_scope": "[0.20,0.25) cycles/native-pixel only",
        "absolute_mtf50_status": "UNSUPPORTED_COMPARATIVE_ONLY",
    }


def literal_measurement() -> dict:
    return {
        "variant_ids": list(VARIANT_IDS),
        "variants": {
            variant_id: literal_candidate(variant_id)
            for variant_id in VARIANT_IDS
        },
        "controls_preceded_score": True,
        "eligibility_controls": literal_controls(),
    }


def commission_checker() -> dict[str, object]:
    controls = literal_controls()
    candidate = literal_candidate("V4_RAMP_GES_OLS_ANGLE")
    baseline = adjudicate_variant(
        "V4_RAMP_GES_OLS_ANGLE",
        candidate,
        controls,
        controls_preceded_score=True,
        source_green=True,
    )
    structural = validate_measurement(literal_measurement())
    mutations: list[tuple[str, str, dict, dict, bool, bool]] = []

    def add(
        label: str,
        gate: str,
        changed: dict,
        changed_controls: dict | None = None,
        source_green: bool = True,
        controls_preceded: bool = True,
    ) -> None:
        mutations.append((
            label,
            gate,
            changed,
            changed_controls or copy.deepcopy(controls),
            source_green,
            controls_preceded,
        ))

    changed = copy.deepcopy(candidate)
    changed["arms"]["identity"]["value"] = 1.02
    add("identity", "identity", changed)
    changed = copy.deepcopy(candidate)
    changed["arms"]["blur"]["value"] = 1.0
    add("blur", "quantitative_blur", changed)
    changed = copy.deepcopy(candidate)
    changed["arms"]["improvement"]["value"] = 1.0
    add("improvement", "true_improvement", changed)
    changed = copy.deepcopy(candidate)
    changed["arms"]["sharpen"]["value"] = 1.10
    add("sharpening", "sharpening", changed)
    for tone in ("affine", "gamma3", "logistic"):
        changed = copy.deepcopy(candidate)
        changed["arms"][tone]["value"] = 1.10
        add(tone, f"{tone}_tone", changed)
    changed = copy.deepcopy(candidate)
    for row in changed["noise"]:
        row["measurement"]["value"] = 1.10
    add("noise_median", "noise", changed)
    changed = copy.deepcopy(candidate)
    changed["noise"][0]["measurement"]["value"] = 1.10
    add("noise_worst", "noise", changed)
    changed = copy.deepcopy(candidate)
    changed["angles"][2]["measurement"] = {"status": "REFUSED"}
    add("angle_five_missing", "angle", changed)
    changed = copy.deepcopy(candidate)
    for row in changed["angles"]:
        row["measurement"] = literal_value(
            1.0, angle=float(row["plant_deg"])
        )
    add("angle_accept_all", "angle", changed)
    changed = copy.deepcopy(candidate)
    changed["arms"]["base"]["metric_name"] = "MTF50_cutoff"
    add("mtf50_relabelling", "native_naming_and_scope", changed)
    changed = copy.deepcopy(candidate)
    changed["arms"]["base"]["floor_activation_fraction"] = 0.0
    add("floor_ignored", "floor_exercised", changed)
    changed = copy.deepcopy(candidate)
    changed["flat_controls"]["base"] = literal_value(1.0)
    add("flat_admitted", "flat_roi", changed)
    changed_controls = copy.deepcopy(controls)
    changed_controls["edge"]["pass"] = False
    add(
        "edge_ineligible",
        "eligibility_edge",
        copy.deepcopy(candidate),
        changed_controls,
    )
    changed_controls = copy.deepcopy(controls)
    changed_controls["point_only"]["lcb_pass"] = True
    changed_controls["point_only"]["pass"] = True
    add(
        "point_only_admitted",
        "eligibility_point_and_lcb",
        copy.deepcopy(candidate),
        changed_controls,
    )
    add(
        "source_drift",
        "source_provenance",
        copy.deepcopy(candidate),
        source_green=False,
    )
    changed = copy.deepcopy(candidate)
    changed["arms"]["base"]["value"] = 0.0
    add("zero_base", "base_numeric", changed)
    changed = copy.deepcopy(candidate)
    changed["absolute_mtf50_status"] = "SUPPORTED"
    add("absolute_relabelling", "native_naming_and_scope", changed)
    add(
        "controls_after_score",
        "controls_preceded_score",
        copy.deepcopy(candidate),
        controls_preceded=False,
    )

    sabotage_results = {}
    for label, gate, changed, changed_controls, source, preceded in mutations:
        output = adjudicate_variant(
            "V4_RAMP_GES_OLS_ANGLE",
            changed,
            changed_controls,
            controls_preceded_score=preceded,
            source_green=source,
        )
        sabotage_results[label] = not output["gates"][gate]

    structural_results = {}
    changed_measurement = literal_measurement()
    del changed_measurement["variants"]["V5_RAMP_GES_TS_ANGLE"]
    structural_results["missing_variant"] = not validate_measurement(
        changed_measurement
    )["exact_variant_set"]
    changed_measurement = literal_measurement()
    changed_measurement["variant_ids"] = [
        "V4_RAMP_GES_OLS_ANGLE"
    ]
    changed_measurement["variants"] = {
        "V4_RAMP_GES_OLS_ANGLE":
            changed_measurement["variants"]["V4_RAMP_GES_OLS_ANGLE"]
    }
    structural_results["survivor_only"] = not validate_measurement(
        changed_measurement
    )["exact_variant_set"]
    changed_measurement = literal_measurement()
    del changed_measurement["variants"]["V2_GES_OLS"]["arms"]["blur"]
    structural_results["omitted_arm"] = not validate_measurement(
        changed_measurement
    )["complete_rows"]
    changed_measurement = literal_measurement()
    changed_measurement["variants"]["V2_GES_OLS"]["noise"].pop()
    structural_results["omitted_noise"] = not validate_measurement(
        changed_measurement
    )["complete_rows"]

    all_tests = {**sabotage_results, **structural_results}
    caught = sum(all_tests.values())
    return {
        "baseline_green": baseline["admitted"],
        "structural_baseline_green": all(structural.values()),
        "sabotages": all_tests,
        "caught": caught,
        "total": len(all_tests),
        "green": (
            baseline["admitted"]
            and all(structural.values())
            and caught == len(all_tests)
        ),
    }


def child_environment() -> dict[str, str]:
    env = dict(os.environ)
    for key in (
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "BLIS_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        env[key] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_child(script: str) -> tuple[dict, int, str]:
    process = subprocess.run(
        [sys.executable, "-B", str(HERE / script)],
        cwd=ROOT,
        env=child_environment(),
        text=True,
        capture_output=True,
        check=False,
    )
    try:
        output = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{script} emitted invalid JSON; rc={process.returncode}; "
            f"stderr={process.stderr!r}"
        ) from exc
    return output, process.returncode, process.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--checker-only",
        action="store_true",
        help="commission literal checker mutations without measuring variants",
    )
    args = parser.parse_args()

    checker = commission_checker()
    if args.checker_only or not checker["green"]:
        print(json.dumps({
            "schema": 1,
            "checker_commission": checker,
        }, indent=2, sort_keys=True))
        return 0 if checker["green"] else 2

    provenance, provenance_rc, provenance_err = run_child(
        "verify_survivor_vendor.py"
    )
    preflight, preflight_rc, preflight_err = run_child(
        "s25h_real_preflight.py"
    )
    if (
        provenance_rc != 0
        or not provenance.get("green")
        or preflight_rc != 0
        or preflight.get("status") != "FORMAL_REAL_M1_BLOCKED"
    ):
        print(json.dumps({
            "schema": 1,
            "checker_commission": checker,
            "provenance": provenance,
            "provenance_stderr": provenance_err,
            "real_preflight": preflight,
            "preflight_stderr": preflight_err,
            "status": "PREMEASUREMENT_GATE_FAILED",
        }, indent=2, sort_keys=True))
        return 2

    first, first_rc, first_err = run_child("s25h_measure.py")
    second, second_rc, second_err = run_child("s25h_measure.py")
    deterministic = (
        first_rc == 0
        and second_rc == 0
        and first == second
        and not first_err
        and not second_err
    )
    structure = validate_measurement(first)
    if not deterministic or not all(structure.values()):
        print(json.dumps({
            "schema": 1,
            "checker_commission": checker,
            "deterministic_repeat": deterministic,
            "measurement_return_codes": [first_rc, second_rc],
            "measurement_stderr": [first_err, second_err],
            "structure": structure,
            "status": "INVALID_MEASUREMENT",
        }, indent=2, sort_keys=True))
        return 2

    adjudicated = {
        variant_id: adjudicate_variant(
            variant_id,
            first["variants"][variant_id],
            first["eligibility_controls"],
            controls_preceded_score=first["controls_preceded_score"],
            source_green=provenance["green"],
        )
        for variant_id in VARIANT_IDS
    }
    admitted = [
        variant_id
        for variant_id, record in adjudicated.items()
        if record["admitted"]
    ]
    result = {
        "schema": 1,
        "checker_commission": checker,
        "provenance": provenance,
        "real_preflight": preflight,
        "deterministic_repeat": deterministic,
        "structure": structure,
        "environment": first["environment"],
        "parameters": first["parameters"],
        "implementation_sha256": first["implementation_sha256"],
        "calibration": first["calibration"],
        "eligibility_controls": first["eligibility_controls"],
        "variants": adjudicated,
        "admitted_variants": admitted,
        "overall_verdict": (
            "COMPARATIVE_ADMISSIBLE_ON_FROZEN_BATTERY"
            if admitted else "NO_ADMISSIBLE_S25_VARIANT"
        ),
        "formal_m1_status": "FORMAL_REAL_M1_BLOCKED",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

