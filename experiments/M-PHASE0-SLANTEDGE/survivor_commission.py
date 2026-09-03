"""Independent checker for the M-PHASE0 survivor audit.

This process imports neither plants, adapters nor candidates.  Provenance and
measurement arrive only as child-process JSON.  Expected values are literals.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

BASE = 0.1249270834195184
BLUR = 0.1117381803027320
BLUR_RATIO = 0.8944271909999159
IMPROVEMENT = 0.1561588542743980
IMPROVEMENT_RATIO = 1.25
ANGLES = (0.5, 1.0, 5.0, 12.0)


def close_frac(actual: float, expected: float, limit: float) -> bool:
    return abs(actual / expected - 1.0) <= limit


def angle_gate(output: object) -> bool:
    if not isinstance(output, dict):
        return False
    for angle in ANGLES:
        row = output.get(str(angle))
        if not isinstance(row, dict):
            return False
        if angle == 5.0:
            if row.get("status") != "VALUE":
                return False
            measured = row.get("angle_deg")
            if not isinstance(measured, (int, float)):
                return False
            if abs(float(measured) - angle) > 0.2:
                return False
        elif row.get("status") != "REFUSED":
            return False
    return True


def no_mtf50_relabelling(name: str, field: dict) -> bool:
    reported = str(field.get("reported_name", name)).lower()
    forbidden_keys = {
        str(key).lower()
        for key in field
        if str(key).lower().startswith("mtf50")
    }
    return reported not in {"mtf50", "mtf50_cyc_native_px"} and not forbidden_keys


def adjudicate_field(
    name: str,
    field: dict,
    *,
    source_green: bool,
) -> dict:
    arms = field["arms"]
    base = float(arms["base"])
    identity = float(arms["identity"])
    blur_ratio = float(arms["blur"]) / base
    improvement_ratio = float(arms["improvement"]) / base
    sharpening_ratio = float(arms["sharpen"]) / base
    tone_ratios = {
        key: float(arms[key]) / base
        for key in ("affine", "gamma3", "logistic")
    }
    noise_ratios = [float(value) / base for value in field["noise"]]
    sorted_noise = sorted(noise_ratios)
    noise_median = (
        0.5 * (sorted_noise[11] + sorted_noise[12])
        if len(sorted_noise) == 24 else None
    )
    noise_worst = (
        max(abs(value - 1.0) for value in noise_ratios)
        if noise_ratios else None
    )

    absolute_supported = field.get("absolute_mtf50_status") == "SUPPORTED"
    absolute_ok = (
        absolute_supported
        and close_frac(base, BASE, 0.05)
        and close_frac(float(arms["blur"]), BLUR, 0.05)
        and close_frac(float(arms["improvement"]), IMPROVEMENT, 0.05)
    )
    blur_ratio_ok = close_frac(blur_ratio, BLUR_RATIO, 0.05)
    improvement_ratio_ok = close_frac(
        improvement_ratio, IMPROVEMENT_RATIO, 0.05
    )
    sharpening_ok = sharpening_ratio <= 1.01
    tone_ok = all(
        abs(ratio - 1.0) <= 0.01 for ratio in tone_ratios.values()
    )
    noise_ok = (
        len(noise_ratios) == 24
        and noise_median is not None
        and abs(noise_median - 1.0) <= 0.03
        and noise_worst is not None
        and noise_worst <= 0.05
    )
    identity_ok = abs(identity - base) <= 1e-12

    if not sharpening_ok:
        response_class = "USM_VULNERABLE"
    elif blur_ratio_ok and improvement_ratio_ok:
        response_class = "USM_INVARIANT_AND_QUANTITATIVELY_RESPONSIVE"
    elif (
        abs(float(arms["blur"]) - base) <= 1e-12
        and abs(float(arms["improvement"]) - base) <= 1e-12
    ):
        response_class = "USM_INVARIANT_BUT_BLIND"
    else:
        response_class = "USM_INVARIANT_BUT_UNCALIBRATED"

    gates = {
        "source_provenance": bool(source_green),
        "identity": identity_ok,
        "absolute_mtf50": absolute_ok,
        "quantitative_blur_ratio": blur_ratio_ok,
        "true_improvement_ratio": improvement_ratio_ok,
        "sharpening": sharpening_ok,
        "tone": tone_ok,
        "noise": noise_ok,
        "angle": angle_gate(field.get("angle_output")),
        "licensing": (
            field.get("unlicensed_output_status")
            == "UNLICENSED_GT_0.25"
        ),
        "native_naming": no_mtf50_relabelling(name, field),
    }
    return {
        "gates": gates,
        "all_frozen_bars_green": all(gates.values()),
        "response_class": response_class,
        "values": {
            key: float(value)
            for key, value in arms.items()
        },
        "ratios": {
            "blur": blur_ratio,
            "improvement": improvement_ratio,
            "sharpen": sharpening_ratio,
            **tone_ratios,
            "noise_median": noise_median,
            "noise_min": min(noise_ratios) if noise_ratios else None,
            "noise_max": max(noise_ratios) if noise_ratios else None,
            "noise_worst_abs": noise_worst,
            "angles": {
                key: float(value) / base
                for key, value in field["angles"].items()
            },
        },
        "native_unit": field.get("native_unit"),
        "absolute_mtf50_status": field.get("absolute_mtf50_status"),
        "angle_output": field.get("angle_output"),
        "unlicensed_output_status": field.get(
            "unlicensed_output_status"
        ),
    }


def literal_green_fixture() -> dict:
    return {
        "reported_name": "literal_native_score",
        "native_unit": "cycles_per_native_pixel",
        "absolute_mtf50_status": "SUPPORTED",
        "arms": {
            "base": BASE,
            "identity": BASE,
            "blur": BLUR,
            "improvement": IMPROVEMENT,
            "sharpen": BASE,
            "affine": BASE,
            "gamma3": BASE,
            "logistic": BASE,
            "unlicensed": BASE,
        },
        "noise": [BASE for _ in range(24)],
        "angles": {str(angle): BASE for angle in ANGLES},
        "angle_output": {
            str(angle): (
                {"status": "VALUE", "angle_deg": angle}
                if angle == 5.0 else {"status": "REFUSED"}
            )
            for angle in ANGLES
        },
        "unlicensed_output_status": "UNLICENSED_GT_0.25",
    }


def commission_checker() -> dict:
    fixture = literal_green_fixture()
    baseline = adjudicate_field(
        "literal_native_score", fixture, source_green=True
    )
    mutations = []

    changed = copy.deepcopy(fixture)
    changed["arms"]["identity"] *= 1.02
    mutations.append(("identity", "identity", changed, True))
    changed = copy.deepcopy(fixture)
    changed["arms"]["blur"] = BASE
    mutations.append((
        "blur", "quantitative_blur_ratio", changed, True
    ))
    changed = copy.deepcopy(fixture)
    changed["arms"]["improvement"] = BASE
    mutations.append((
        "improvement", "true_improvement_ratio", changed, True
    ))
    changed = copy.deepcopy(fixture)
    changed["arms"]["sharpen"] = BASE * 1.10
    mutations.append(("sharpening", "sharpening", changed, True))
    changed = copy.deepcopy(fixture)
    changed["arms"]["gamma3"] = BASE * 1.10
    mutations.append(("tone", "tone", changed, True))
    changed = copy.deepcopy(fixture)
    changed["noise"][0] = BASE * 1.10
    mutations.append(("noise", "noise", changed, True))
    changed = copy.deepcopy(fixture)
    changed["angle_output"] = "NONE"
    mutations.append(("angle", "angle", changed, True))
    changed = copy.deepcopy(fixture)
    changed["unlicensed_output_status"] = "NUMERIC"
    mutations.append(("licensing", "licensing", changed, True))
    changed = copy.deepcopy(fixture)
    mutations.append(("source_drift", "source_provenance", changed, False))
    changed = copy.deepcopy(fixture)
    changed["reported_name"] = "mtf50_cyc_native_px"
    mutations.append(("mtf50_relabelling", "native_naming", changed, True))

    tests = {}
    for label, gate, changed, source_green in mutations:
        output = adjudicate_field(
            "literal_native_score",
            changed,
            source_green=source_green,
        )
        tests[label] = not output["gates"][gate]
    caught = sum(tests.values())
    return {
        "baseline_green": baseline["all_frozen_bars_green"],
        "sabotages": tests,
        "caught": caught,
        "total": len(tests),
        "green": (
            baseline["all_frozen_bars_green"]
            and caught == len(tests)
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


def run_child(script: str) -> tuple[dict, int]:
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
    return output, process.returncode


def main() -> int:
    checker = commission_checker()
    if not checker["green"]:
        print(json.dumps({"checker_commission": checker}, indent=2))
        return 2

    provenance, provenance_rc = run_child(
        "verify_survivor_vendor.py"
    )
    if provenance_rc != 0 or not provenance.get("green"):
        print(json.dumps({
            "checker_commission": checker,
            "provenance": provenance,
            "status": "SOURCE_DRIFT",
        }, indent=2, sort_keys=True))
        return 2

    first, first_rc = run_child("survivor_measure.py")
    second, second_rc = run_child("survivor_measure.py")
    deterministic = (
        first_rc == 0 and second_rc == 0 and first == second
    )
    if not deterministic:
        print(json.dumps({
            "checker_commission": checker,
            "provenance": provenance,
            "measurement_return_codes": [first_rc, second_rc],
            "deterministic_repeat": deterministic,
            "status": "NONDETERMINISTIC_MEASUREMENT",
        }, indent=2, sort_keys=True))
        return 2

    candidates = {}
    for candidate_name, candidate in first["candidates"].items():
        fields = {
            field_name: adjudicate_field(
                field_name,
                field,
                source_green=provenance["green"],
            )
            for field_name, field in candidate["fields"].items()
        }
        claim_fields = candidate["claim_fields"]
        candidates[candidate_name] = {
            "candidate": candidate["candidate"],
            "claim_fields": claim_fields,
            "fields": fields,
            "all_claim_fields_green": all(
                fields[name]["all_frozen_bars_green"]
                for name in claim_fields
            ),
            "claim_response_classes": {
                name: fields[name]["response_class"]
                for name in claim_fields
            },
            "frequency_scope": candidate["frequency_scope"],
            "angle_capability": candidate["angle_capability"],
            "licensing_capability": candidate["licensing_capability"],
        }

    result = {
        "schema": 1,
        "checker_commission": checker,
        "provenance": provenance,
        "deterministic_repeat": deterministic,
        "anchors": {
            "base_mtf50": BASE,
            "blur_mtf50": BLUR,
            "blur_ratio": BLUR_RATIO,
            "improvement_mtf50": IMPROVEMENT,
            "improvement_ratio": IMPROVEMENT_RATIO,
        },
        "environment": first["environment"],
        "parameters": first["parameters"],
        "candidates": candidates,
        "overall_verdict": (
            "SURVIVOR_ADMITTED_BY_FULL_FROZEN_BATTERY"
            if any(
                candidate["all_claim_fields_green"]
                for candidate in candidates.values()
            )
            else "NO_SURVIVOR_ADMITTED_BY_FULL_FROZEN_BATTERY"
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

