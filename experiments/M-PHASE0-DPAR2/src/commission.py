"""Commission DPAR2 before the nonzero curved-track power ladder is trusted."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

import dpar2lib as D
import fixed_oracle as O

OUT = D.LANE / "out" / "commission.json"
R_PLANE = 0.5 * math.hypot(3516.0, 2344.0)


def external_curvature_check():
    """Independent parser and fixed predicates; does not call D.mapped_track."""
    raw = json.loads(D.M103_TRACK.read_text(encoding="utf-8"))
    track = {int(k): float(v["ln"]) for k, v in raw["ladder"].items()}
    rungs = sorted(track)

    def readings(values):
        end = rungs[-1]
        chord = {
            j: values[rungs[0]]
            + (values[end] - values[rungs[0]]) * (j - rungs[0]) / (end - rungs[0])
            for j in rungs
        }
        deviations = {j: abs(values[j] - chord[j]) * R_PLANE for j in rungs}
        worst = max(deviations, key=deviations.get)
        rates = [
            abs(values[96] - values[0]) / 96.0,
            abs(values[192] - values[96]) / 96.0,
            abs(values[298] - values[192]) / 106.0,
        ]
        predicates = {
            "deviation_range": 45.5 <= deviations[worst] <= 46.7,
            "worst_j_200": worst == 200,
            "rate_0_96": 0.00028 <= rates[0] <= 0.00032,
            "rate_96_192": 0.00049 <= rates[1] <= 0.00053,
            "rate_192_298": 0.00069 <= rates[2] <= 0.00075,
            "strict_acceleration": rates[0] < rates[1] < rates[2],
        }
        return {
            "max_chord_deviation_plane_px": float(deviations[worst]),
            "worst_j": int(worst),
            "rates_abs_ln_per_frame": [float(v) for v in rates],
            "predicates": predicates,
            "pass": bool(all(predicates.values())),
        }

    real = readings(track)
    end = rungs[-1]
    chord = {
        j: track[0] + (track[end] - track[0]) * j / end
        for j in rungs
    }
    mutation = readings(chord)
    return {
        "source": str(D.M103_TRACK.relative_to(D.ROOT)).replace("\\", "/"),
        "source_sha256": D.sha256(D.M103_TRACK),
        "real": real,
        "straight_chord_mutation": mutation,
        "pass": bool(real["pass"] and not mutation["pass"]),
    }


def estimator_read_check():
    out = {}
    expected = {
        "P1-both": (-0.706, 0.005, True),
        "P2-blur-only": (-0.099, 0.005, False),
    }
    for name, (rho0, tol, should_detect) in expected.items():
        prefix = D.M6_DIR / "data" / "control"
        t = D.M6.load_tiles(str(prefix), name)
        focus = D.M6.load_focus(str(prefix), name)
        fits = D.M6.load_fits(str(prefix), name, grid="m6")
        w, _pk, _prof = D.M6.winner_index(focus)
        ox, oy = D.M6.scale_centre(fits)
        s2 = D.M6.s2_scale_anomaly(t, w, ox, oy)
        detected = s2["rho_dg_w"] < 0 and s2["p_torus_dg"] <= 0.05
        ok = abs(s2["rho_dg_w"] - rho0) <= tol and detected == should_detect
        out[name] = {
            "rho_dg_w": float(s2["rho_dg_w"]),
            "p_torus": float(s2["p_torus_dg"]),
            "detected": bool(detected),
            "expected_rho": rho0,
            "rho_tolerance": tol,
            "expected_detected": should_detect,
            "pass": bool(ok),
        }
    out["pass"] = bool(all(v["pass"] for v in out.values()))
    return out


def scalar_fixture_check():
    actual = D.scalar_fixture(
        O.AMPLITUDE_PX_PER_STEP_R1000,
        np.array(O.PAIR_FACTORS),
        np.array(O.DEPTH_STEPS),
        np.array(O.RADII_PX),
    )
    expected = np.array(O.EXPECTED_RADIAL_PX, dtype=np.float64)
    mutation = D.scalar_fixture(
        O.AMPLITUDE_PX_PER_STEP_R1000,
        -np.ones_like(actual),
        np.array(O.DEPTH_STEPS),
        np.array(O.RADII_PX),
    )
    real_ok = bool(np.allclose(actual, expected, rtol=0.0, atol=1e-15))
    mutation_passes = bool(np.allclose(mutation, expected, rtol=0.0, atol=1e-15))
    return {
        "actual_radial_px": actual.tolist(),
        "fixed_expected_radial_px": expected.tolist(),
        "max_abs_error_px": float(np.max(np.abs(actual - expected))),
        "straight_unit_factor_mutation": mutation.tolist(),
        "mutation_would_pass": mutation_passes,
        "pass": bool(real_ok and not mutation_passes),
    }


def wiring_check(case: D.Case):
    zero, zero_diag = D.apply_plant(
        case.tiles, case.w, case.ox, case.oy, case.ell, 0.0
    )
    maximum, max_diag = D.apply_plant(
        case.tiles, case.w, case.ox, case.oy, case.ell, float(D.AMPLITUDES[-1])
    )
    # Keep both objects live so an accidental no-op cannot satisfy only a
    # diagnostic generated inside apply_plant.
    moved = float(
        np.nanmax(np.hypot(maximum.ex - zero.ex, maximum.ey - zero.ey))
    )
    predicates = {
        "zero_bit_identical": bool(zero_diag["bit_identical_zero"]),
        "orthogonal_to_scale": (
            max_diag["max_similarity_inner_product_ratio"] <= 1e-10
        ),
        "tangential_unchanged": max_diag["max_tangential_change_px"] <= 1e-10,
        "nonzero_fixture_exercised": moved > 1.0,
    }
    return {
        "zero": zero_diag,
        "max_dose": max_diag,
        "max_vector_change_px": moved,
        "predicates": predicates,
        "pass": bool(all(predicates.values())),
    }


def null_and_expressiveness_check(case: D.Case):
    rows, detection, _rho, _p = D.evaluate_power(case, np.array([0.0]))
    false_rate = float(detection[0].mean())
    adj = np.abs(np.diff(case.ell))
    curved_cv = float(np.std(adj) / np.mean(adj))
    chord = D.mapped_track(case.n_frames, chord=True)
    chord_adj = np.abs(np.diff(chord))
    chord_cv = float(np.std(chord_adj) / np.mean(chord_adj))
    max_difference = float(np.max(np.abs(case.ell - chord)))
    predicates = {
        "zero_false_detection_le_0p10": false_rate <= 0.10,
        "curved_increment_cv_nonzero": curved_cv > 1e-6,
        "mapped_track_differs_from_chord": max_difference > 1e-6,
        "chord_increment_cv_lt_1e_minus_12": chord_cv < 1e-12,
    }
    return {
        "zero_dose": rows[0],
        "zero_false_detection_rate": false_rate,
        "curved_adjacent_increment_cv": curved_cv,
        "chord_adjacent_increment_cv": chord_cv,
        "max_abs_ln_difference_from_chord": max_difference,
        "predicates": predicates,
        "pass": bool(all(predicates.values())),
    }


def fast_path_check(case: D.Case):
    rows = D.validate_fast_path(case)
    ok = all(r["abs_rho_error"] <= 1e-12 and r["abs_p_error"] <= 1e-15 for r in rows)
    return {"rows": rows, "pass": bool(ok)}


def main() -> int:
    primary = D.load_case(D.PRIMARY)
    controls = {
        "C1_external_curved_track": external_curvature_check(),
        "C2_estimator_read": estimator_read_check(),
        "C3_external_scalar_fixture": scalar_fixture_check(),
        "C4_similarity_and_channel_wiring": wiring_check(primary),
        "C5_null_and_expressiveness": null_and_expressiveness_check(primary),
        "C6_fast_path_equals_m6": fast_path_check(primary),
    }
    passed = bool(all(v["pass"] for v in controls.values()))
    result = {
        "schema": 1,
        "lane": "M-PHASE0-DPAR2",
        "stage": "commission",
        "pass": passed,
        "controls": controls,
        "provenance": D.provenance(primary),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"DPAR2 commission: {'PASS' if passed else 'FAIL'}")
    for name, value in controls.items():
        print(f"  {name}: {'PASS' if value['pass'] else 'FAIL'}")
    print(f"wrote {OUT.relative_to(D.ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
