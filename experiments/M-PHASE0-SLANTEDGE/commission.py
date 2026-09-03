"""Independent commissioning checker for M-PHASE0-SLANTEDGE.

This process imports neither the plant/measurement module nor any candidate.
Expected values are literal external predicates.  Candidate measurements arrive
only as child-process JSON.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent

BASE = 0.1249270834195184
BLUR = 0.1117381803027320
BLUR_RATIO = 0.8944271909999159
IMPROVEMENT = 0.1561588542743980
IMPROVEMENT_RATIO = 1.25

# Frozen from the published callers, not supplied by measure.py's verdict.
ANGLE_GATES = {
    "M88": (0.4, 12.0),
    "M104c": (2.0, 12.0),
    "BUILD-RESAMP": (2.0, 10.0),
}
ANGLE_EXPECTED = {0.5: False, 1.0: False, 5.0: True, 12.0: False}


def is_value(record: dict) -> bool:
    return record.get("status") == "VALUE" and isinstance(
        record.get("mtf50_cyc_native_px"), (int, float))


def value(record: dict) -> float:
    if not is_value(record):
        raise ValueError(record)
    return float(record["mtf50_cyc_native_px"])


def close_frac(actual: float, expected: float, limit: float) -> bool:
    return abs(actual / expected - 1.0) <= limit


def tone_ok(record: dict, base: float) -> bool:
    if record.get("status") in ("REFUSED", "UNLICENSED_GT_0.25"):
        return True
    return is_value(record) and close_frac(value(record), base, 0.01)


def adjudicate(name: str, instrument: dict,
               angle_gate=None) -> dict:
    arms = instrument["arms"]
    base = value(arms["base"])
    identity = value(arms["identity"])

    identity_ok = abs(identity - base) <= 1e-12
    blur_ok = (
        is_value(arms["blur"])
        and close_frac(base, BASE, 0.05)
        and close_frac(value(arms["blur"]), BLUR, 0.05)
        and close_frac(value(arms["blur"]) / base, BLUR_RATIO, 0.05)
    )
    improvement_ok = (
        is_value(arms["improvement"])
        and close_frac(value(arms["improvement"]), IMPROVEMENT, 0.05)
        and close_frac(value(arms["improvement"]) / base,
                       IMPROVEMENT_RATIO, 0.05)
    )

    sharp = arms["sharpen"]
    explicit_sharp_refusal = (
        sharp.get("status") == "REFUSED"
        and "SHARP" in sharp.get("reason", "").upper()
    ) or bool(instrument.get("sharpening_warning"))
    sharp_ratio = value(sharp) / base if is_value(sharp) else None
    sharpening_ok = explicit_sharp_refusal or (
        sharp_ratio is not None and sharp_ratio <= 1.01
    )

    tone_ok_all = (
        tone_ok(arms["affine"], base)
        and tone_ok(arms["gamma3"], base)
        and tone_ok(arms["logistic"], base)
    )

    noise_values = [value(r) for r in instrument["noise"] if is_value(r)]
    noise_ratios = [v / base for v in noise_values]
    noise_sorted = sorted(noise_ratios)
    noise_median = (
        0.5 * (noise_sorted[11] + noise_sorted[12])
        if len(noise_sorted) == 24 else None
    )
    noise_worst = (
        max(abs(r - 1.0) for r in noise_ratios)
        if noise_ratios else None
    )
    noise_ok = (
        len(noise_ratios) == 24
        and abs(noise_median - 1.0) <= 0.03
        and noise_worst <= 0.05
    )

    lo, hi = ANGLE_GATES[name] if angle_gate is None else angle_gate
    angle_details = []
    angle_ok = True
    for case in instrument["angles"]:
        plant = float(case["plant_deg"])
        rec = case["measurement"]
        measured = (
            abs(float(rec["angle_deg"]))
            if is_value(rec) and "angle_deg" in rec else None
        )
        # Do not let a few ulps decide whether an inclusive published boundary
        # is accepted (the 12-degree plants recover as 12.000000000000004).
        admitted = (
            measured is not None
            and lo - 1e-6 <= measured <= hi + 1e-6
        )
        expected = ANGLE_EXPECTED[plant]
        recovered = (
            (not expected)
            or (measured is not None and abs(measured - plant) <= 0.2)
        )
        case_ok = admitted == expected and recovered
        angle_ok &= case_ok
        angle_details.append({
            "plant_deg": plant,
            "measured_deg": measured,
            "published_gate_admits": admitted,
            "expected_admission": expected,
            "pass": case_ok,
        })

    licence = arms["unlicensed"]
    licensing_ok = licence.get("status") == "UNLICENSED_GT_0.25"

    gates = {
        "identity": identity_ok,
        "quantitative_blur": blur_ok,
        "true_improvement": improvement_ok,
        "sharpening": sharpening_ok,
        "tone": tone_ok_all,
        "noise": noise_ok,
        "angle": angle_ok,
        "licensing": licensing_ok,
        "domain_declared": bool(instrument.get("domain")),
    }
    ratios = {
        "blur": value(arms["blur"]) / base if is_value(arms["blur"]) else None,
        "true_improvement": (
            value(arms["improvement"]) / base
            if is_value(arms["improvement"]) else None
        ),
        "sharpen": sharp_ratio,
        "affine": (
            value(arms["affine"]) / base if is_value(arms["affine"]) else None
        ),
        "gamma3": (
            value(arms["gamma3"]) / base if is_value(arms["gamma3"]) else None
        ),
        "logistic": (
            value(arms["logistic"]) / base
            if is_value(arms["logistic"]) else None
        ),
        "noise_median": noise_median,
        "noise_min": min(noise_ratios) if noise_ratios else None,
        "noise_max": max(noise_ratios) if noise_ratios else None,
        "noise_above_base": sum(r > 1.0 for r in noise_ratios),
        "noise_worst_abs": noise_worst,
    }
    passed = all(gates.values())
    return {
        "verdict": (
            "COMMISSIONED_FOR_RESOLUTION"
            if passed else "REFUSED_AS_SOLE_RESOLUTION_INSTRUMENT"
        ),
        "gates": gates,
        "ratios": ratios,
        "values": {
            key: (value(rec) if is_value(rec) else rec.get("status"))
            for key, rec in arms.items()
        },
        "angles": angle_details,
        "domain": instrument.get("domain"),
        "demosaic_or_render_path": instrument.get(
            "demosaic_or_render_path"),
    }


def literal_green_fixture() -> dict:
    def val(v):
        return {"status": "VALUE", "mtf50_cyc_native_px": v}

    return {
        "arms": {
            "base": val(BASE),
            "identity": val(BASE),
            "blur": val(BLUR),
            "improvement": val(IMPROVEMENT),
            "sharpen": {
                "status": "REFUSED",
                "reason": "SHARPENING_UNSAFE",
            },
            "affine": val(BASE),
            "gamma3": val(BASE),
            "logistic": val(BASE),
            "unlicensed": {"status": "UNLICENSED_GT_0.25"},
        },
        "noise": [val(BASE) for _ in range(24)],
        "angles": [
            {"plant_deg": a, "measurement": {
                "status": "VALUE",
                "mtf50_cyc_native_px": BASE,
                "angle_deg": a,
            }}
            for a in (0.5, 1.0, 5.0, 12.0)
        ],
        "sharpening_warning": "SHARPENING_UNSAFE",
        "domain": "fixed literal linear fixture",
        "demosaic_or_render_path": False,
    }


def commission_checker() -> dict:
    fixture = literal_green_fixture()
    baseline = adjudicate("BUILD-RESAMP", fixture, angle_gate=(2.0, 10.0))
    tests = {}

    mutations = []
    x = copy.deepcopy(fixture)
    x["arms"]["identity"]["mtf50_cyc_native_px"] *= 1.02
    mutations.append(("identity", "identity", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    x["arms"]["blur"]["mtf50_cyc_native_px"] = BASE
    mutations.append(("blur", "quantitative_blur", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    x["arms"]["improvement"]["mtf50_cyc_native_px"] = BASE
    mutations.append(("improvement", "true_improvement", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    x["sharpening_warning"] = None
    x["arms"]["sharpen"] = {
        "status": "VALUE",
        "mtf50_cyc_native_px": BASE * 1.10,
    }
    mutations.append(("sharpening", "sharpening", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    x["arms"]["gamma3"]["mtf50_cyc_native_px"] = BASE * 1.10
    mutations.append(("tone", "tone", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    x["noise"][0]["mtf50_cyc_native_px"] = BASE * 1.10
    mutations.append(("noise", "noise", x, (2.0, 10.0)))
    x = copy.deepcopy(fixture)
    mutations.append(("angle", "angle", x, (0.4, 12.0)))
    x = copy.deepcopy(fixture)
    x["arms"]["unlicensed"] = {
        "status": "VALUE",
        "mtf50_cyc_native_px": 0.31,
    }
    mutations.append(("licensing", "licensing", x, (2.0, 10.0)))

    for label, gate, mutated, angle_gate in mutations:
        out = adjudicate("BUILD-RESAMP", mutated, angle_gate=angle_gate)
        tests[label] = not out["gates"][gate]
    caught = sum(tests.values())
    return {
        "baseline_green": all(baseline["gates"].values()),
        "sabotages": tests,
        "caught": caught,
        "total": len(tests),
        "green": (
            all(baseline["gates"].values()) and caught == len(tests)
        ),
    }


def run_measurement() -> dict:
    env = dict(os.environ)
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS",
                "BLIS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[key] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    proc = subprocess.run(
        [sys.executable, "-B", str(HERE / "measure.py")],
        cwd=HERE.parents[1],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"measurement failed rc={proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


def main() -> int:
    checker = commission_checker()
    if not checker["green"]:
        print(json.dumps({"checker_commission": checker}, indent=2))
        return 2
    measurement = run_measurement()
    instruments = {
        name: adjudicate(name, data)
        for name, data in measurement["instruments"].items()
    }
    result = {
        "schema": 1,
        "checker_commission": checker,
        "anchors": {
            "base_mtf50": BASE,
            "blur_mtf50": BLUR,
            "blur_ratio": BLUR_RATIO,
            "improvement_mtf50": IMPROVEMENT,
            "improvement_ratio": IMPROVEMENT_RATIO,
        },
        "environment": measurement["environment"],
        "parameters": measurement["parameters"],
        "sources": measurement["sources"],
        "instruments": instruments,
        "overall_verdict": (
            "COMMISSIONED_FOR_RESOLUTION"
            if any(v["verdict"] == "COMMISSIONED_FOR_RESOLUTION"
                   for v in instruments.values())
            else "NO_COMMISSIONED_SLANTED_EDGE_RESOLUTION_INSTRUMENT"
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
