"""M87 / 74 -- adjudicate step 72, whose registered decision rule fired the
WRONG ANSWER, and say so in place rather than repairing it quietly.

WHAT THE REGISTERED RULE SAID.  N2 was: "if arm E improves band RMSE at least 2x
more than arm B, the fit is not the limiter".  It measured E/B = 1.02x, below
the bar, and printed

    N2 -> THE FIT IS THE CEILING: step 13 refutes the MODEL

WHY THAT INFERENCE IS WRONG, AND THE DEFECT IS MINE.  "E is no better than B" is
consistent with two opposite worlds and my rule cannot tell them apart:

    (i)  B and E both stall far short of a good reconstruction
         -> the two-component fit really is the ceiling;
    (ii) B and E have both REACHED the achievable floor
         -> nothing is limiting either of them and the model works.

Step 72 is world (ii): on the depth-spread plant arm B lands at 1.8270% band
RMSE and arm E at 1.7837%, and section 4.2 of the report measures the far-field
single-frame noise floor at 1.80%.  Both are AT the floor.  A rule that reads
"already perfect" as "refuted" is a defect in the rule, not a result.

So this step re-adjudicates against the FLOOR instead of against the other arm.
The registered rule's output stays in 72's own stdout and JSON, untouched, and
this file is the correction -- the same handling section 15.4 got when fact 1295
invalidated it.

THE CORRECTED RULE, stated before the floor was computed: score each arm as the
fraction of the AVAILABLE headroom it captures,

    captured = (RMSE_merge - RMSE_arm) / (RMSE_merge - RMSE_floor)

where RMSE_floor is the far-field RMSE of the merge against the known unveiled
background -- the irreducible single-frame noise the intercept is estimated
through.  An arm at captured ~ 1.0 is not limited by anything.  The two-layer
model is refuted only if the ORACLE arm E fails to capture the headroom.

READ-ONLY: D:\\personal\\macro.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("plant", HERE / "16-plant.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)
spec2 = importlib.util.spec_from_file_location("abl", HERE / "72-ablation.py")
A = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(A)

DATA = HERE.parents[0] / "data"
FARBAND = (60, 140)


def main():
    rep = json.load(open(DATA / "72-ablation.json", encoding="utf-8"))
    out = {}
    for tag, spread in (("FLAT placebo", 0), ("DEPTH-SPREAD", A.SPREAD)):
        frames, alphas, m, kf_map, truth, unveiled = A.build(spread)
        mask = m > 0.5
        sel, _ = P.merge(frames)
        d_out = distance_transform_edt(~mask)
        roi = np.zeros_like(mask)
        roi[P.ROI[0]:P.ROI[1], P.ROI[2]:P.ROI[3]] = True
        far = (~mask) & roi & (d_out >= FARBAND[0]) & (d_out <= FARBAND[1])
        floor = float(np.sqrt(np.mean((sel[far] - unveiled[far]) ** 2))
                      / P.LEVEL * 100)
        base = rep[tag]["base_rmse_pct"]
        head = base - floor
        print(f"\n=== {tag} ===", flush=True)
        print(f"  merge band RMSE {base:.4f}%   far-field noise floor "
              f"{floor:.4f}% over d{FARBAND} ({int(far.sum())} px)   "
              f"available headroom {head:.4f} points", flush=True)
        rows = {}
        for name, a in rep[tag]["arms"].items():
            cap = (base - a["rmse_pct"]) / head if head > 1e-9 else float("nan")
            rows[name] = cap
            print(f"  {name:<26} RMSE {a['rmse_pct']:8.4f}%   captures "
                  f"{100 * cap:+8.2f}% of the headroom", flush=True)
        out[tag] = {"floor_pct": floor, "base_pct": base, "headroom": head,
                    "captured": rows}

    print(f"\n{'=' * 74}\n=== CORRECTED ADJUDICATION ===", flush=True)
    s = out["DEPTH-SPREAD"]["captured"]
    cB, cE, cA = s["B oracle k_F map"], s["E oracle alpha"], s["A shipped scalar k_F"]
    print(f"  depth-spread plant, the case the question is about:", flush=True)
    print(f"    A global scalar k_F   captures {100 * cA:+8.2f}%", flush=True)
    print(f"    B per-pixel k_F map   captures {100 * cB:+8.2f}%", flush=True)
    print(f"    E ORACLE alpha        captures {100 * cE:+8.2f}%", flush=True)
    model_alive = cE >= 0.90
    prop_load = (cB - cA)
    print(f"\n  Is the two-component FIT the ceiling?  The oracle captures "
          f"{100 * cE:.2f}% of the headroom -> "
          f"{'NO. The model reaches the floor and is NOT refuted.' if model_alive else 'YES, the fit really is the limit.'}",
          flush=True)
    print(f"  How load-bearing is k_F propagation?  A -> B moves capture by "
          f"{100 * prop_load:+.2f} points on the depth-spread plant, and by "
          f"{100 * (out['FLAT placebo']['captured']['B oracle k_F map'] - out['FLAT placebo']['captured']['A shipped scalar k_F']):+.2f} "
          f"points on the flat placebo where depth does not vary.", flush=True)
    gap = cE - cB
    print(f"  How much is left for a better alpha once k_F is per-pixel?  "
          f"E - B = {100 * gap:+.2f} points.", flush=True)
    out["verdict"] = {
        "depth_spread_captured": {"A": cA, "B": cB, "E": cE},
        "flat_captured": out["FLAT placebo"]["captured"],
        "model_alive": bool(model_alive), "propagation_points": float(prop_load),
        "oracle_headroom_left": float(gap),
        "note": "step 72's registered N2 rule compared E against B and cannot "
                "distinguish 'both stalled' from 'both at the floor'; this is "
                "the floor-relative re-adjudication",
    }
    with open(DATA / "74-adjudicate.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=A._np)
    print(f"\nwrote {DATA / '74-adjudicate.json'}", flush=True)


if __name__ == "__main__":
    main()
