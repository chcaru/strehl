"""Run the preregistered DPAR2 curved-track power ladder and file its verdict."""

from __future__ import annotations

import json
import sys

import numpy as np

import dpar2lib as D

COMMISSION = D.LANE / "out" / "commission.json"
OUT = D.LANE / "out" / "measurement.json"


def exact_unplanted(case: D.Case):
    s2 = D.M6.s2_scale_anomaly(case.tiles, case.w, case.ox, case.oy)
    detected = s2["rho_dg_w"] < 0 and s2["p_torus_dg"] <= 0.05
    return {
        "rho_dg_w": float(s2["rho_dg_w"]),
        "p_torus": float(s2["p_torus_dg"]),
        "detected_predicted_direction": bool(detected),
        "n_tiles": int(s2["n_tiles"]),
    }


def stack_result(name: str):
    case = D.load_case(name)
    rows, detection, _rho, _p = D.evaluate_power(case)
    mda = D.bootstrap_mda(detection)
    return {
        "stack": name,
        "role": "primary" if name == D.PRIMARY else "secondary",
        "n_frames": case.n_frames,
        "n_phases": int(detection.shape[1]),
        "scale_centre_plane_px": [case.ox, case.oy],
        "mapped_track": {
            "ln_scale": case.ell.tolist(),
            "median_abs_adjacent_ln": case.track_median_adj,
            "adjacent_abs_increment_cv": float(
                np.std(np.abs(np.diff(case.ell)))
                / np.mean(np.abs(np.diff(case.ell)))
            ),
        },
        "unplanted": exact_unplanted(case),
        "ladder": rows,
        "mda80_px_per_depth_step_r1000": mda,
        "mda80_px_per_depth_step_r2000": {
            "point": None if mda["point"] is None else 2.0 * mda["point"],
            "bootstrap95": [
                None if v is None else 2.0 * v for v in mda["bootstrap95"]
            ],
        },
        "provenance": D.provenance(case),
    }


def main() -> int:
    if not COMMISSION.is_file():
        print("commission.json is absent; run src/commission.py first", file=sys.stderr)
        return 2
    commission = json.loads(COMMISSION.read_text(encoding="utf-8"))
    if not commission.get("pass"):
        print("commission failed; refusing to run the power ladder", file=sys.stderr)
        return 2

    stacks = {name: stack_result(name) for name in D.STACKS}
    primary = stacks[D.PRIMARY]
    unplanted = primary["unplanted"]
    mda = primary["mda80_px_per_depth_step_r1000"]
    upper = mda["bootstrap95"][1]

    if unplanted["detected_predicted_direction"]:
        verdict = "SURVIVE"
        reason = "the unchanged unplanted primary S2 detects the predicted sign"
    elif upper is not None and upper <= 0.300:
        verdict = "KILL"
        reason = (
            "commissioned primary MDA80 upper 95% endpoint clears "
            "0.300 px/depth-step at radius 1000"
        )
    else:
        verdict = "NOT ROBUST / UNDERPOWERED"
        reason = (
            "the primary MDA80 uncertainty does not clear the proposal's "
            "weakest predicted amplitude"
        )

    observed_reached_point = mda["point"] is not None and mda["point"] <= 0.0269
    observed_reached_upper = upper is not None and upper <= 0.0269
    result = {
        "schema": 1,
        "lane": "M-PHASE0-DPAR2",
        "stage": "measurement",
        "commission_pass": True,
        "amplitude_definition": (
            "plane px per depth-index step at radius 1000 for the median "
            "adjacent increment of the mapped M103 ln(scale) track"
        ),
        "amplitudes_px_per_depth_step_r1000": D.AMPLITUDES.tolist(),
        "detection_rule": "rho(dg,w)<0 and M6 two-sided torus p<=0.05",
        "power_rule": "MDA80: first rung >=80% and every higher rung >=80%",
        "verdict": verdict,
        "verdict_reason": reason,
        "predicted_regime": {
            "r1000": 0.300,
            "r2000": 0.600,
            "cleared_by_mda_upper95": bool(upper is not None and upper <= 0.300),
        },
        "audited_m6_p1_regime": {
            "r1000": 0.0269,
            "r2000": 0.0538,
            "reached_by_mda_point": bool(observed_reached_point),
            "reached_by_mda_upper95": bool(observed_reached_upper),
        },
        "stacks": stacks,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    print("DPAR2 curved-track conditional power")
    print("=" * 78)
    for name in D.STACKS:
        r = stacks[name]
        m = r["mda80_px_per_depth_step_r1000"]
        print(
            f"{name:<14} MDA80={m['point']}  95%={m['bootstrap95']}  "
            f"unplanted rho={r['unplanted']['rho_dg_w']:+.3f} "
            f"p={r['unplanted']['p_torus']:.4f}"
        )
    print(f"VERDICT: {verdict} -- {reason}")
    print(f"wrote {OUT.relative_to(D.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
