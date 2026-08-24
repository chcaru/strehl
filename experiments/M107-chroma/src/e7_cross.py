"""E7 -- cross-instrument consistency for hypothesis (a).

Instrument A was run on two different data representations, at two different
places in the frame, and the radial model was fitted on only ONE of them:

  E1  RAW CFA planes, sensel lattice, ROIs at large radius (r ~ 2500-3700)
  E4  RENDERED demosaic output, ROIs near the frame centre (r ~ 260-350 px)

The radial model d = eps * ((r - r0) . n) was fitted on the E1/gated set alone.
If lateral CA is real, that fit must PREDICT the E4 numbers it never saw, at a
radius an order of magnitude smaller, on a different representation, through a
different code path.  If it is a fitting artefact, it will not.

This is the strongest available test of (a) short of a lens bench, because the
prediction is extrapolation to a regime the fit had no access to, and the
predicted value is close to zero -- the model is being asked to predict its own
vanishing, which a spurious fit has no reason to get right.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump

COV = {"tweezers-cpl": 0.9726, "bee-3-cpl": 0.9315}
SENSEL_PER_PX = {"linear": 2.0, "binned": 2.0, "demosaic": 1.0}


def rows_of(d):
    if isinstance(d, dict) and "rows" in d:
        return d["rows"]
    if isinstance(d, dict):
        out = []
        for _, arms in d.items():
            if isinstance(arms, dict):
                for _, rs in arms.items():
                    out.extend(rs)
        return out
    return d


if __name__ == "__main__":
    lat = json.load(open(os.path.join(OUT, "json", "e2_lateral.json")))
    lat = lat["data"] if isinstance(lat, dict) and "data" in lat else lat
    fit = lat["radial"]["dR"]
    eps = fit["eps"]
    cx, cy = fit["centre_sensel"]
    print("model fitted on E1 (raw planes, large radius) ONLY:")
    print(f"  eps_R = {eps*1e6:+.1f} ppm, centre ({cx:+.0f},{cy:+.0f}) sensel, "
          f"R2 = {fit['r2']:.4f}\n")

    e4 = rows_of(json.load(open(os.path.join(OUT, "json",
                                             "e4_render_arms.json"))))
    out = []
    print(f"{'stack':>14s} {'arm':>9s} {'r_sensel':>9s} {'predicted':>10s} "
          f"{'measured':>10s} {'meas/pred':>10s}"
          f"   (|dR| along the edge normal, source sensel)")
    for st in sorted({r["stack"] for r in e4}):
        for arm in ("linear", "binned", "demosaic"):
            sel = [r for r in e4 if r["stack"] == st and r["arm"] == arm]
            if not sel:
                continue
            k = SENSEL_PER_PX[arm] * COV[st]
            pred, meas, rr = [], [], []
            for r in sel:
                # ROI position, output px -> source sensel
                rx, ry = r["rx"] * k, r["ry"] * k
                nx, ny = r["normal"]
                p = eps * ((rx - cx) * nx + (ry - cy) * ny)
                pred.append(abs(p)); meas.append(abs(r["dR"]) * k)
                rr.append(np.hypot(rx, ry))
            mp, mm = float(np.median(pred)), float(np.median(meas))
            print(f"{st:>14s} {arm:>9s} {np.median(rr):>9.0f} {mp:>10.4f} "
                  f"{mm:>10.4f} {mm/max(mp,1e-9):>10.2f}")
            out.append({"stack": st, "arm": arm,
                        "median_radius_sensel": float(np.median(rr)),
                        "predicted_sensel": mp, "measured_sensel": mm,
                        "ratio_meas_over_pred": mm / max(mp, 1e-9),
                        "n": len(sel)})

    # and the E1 regime the fit WAS trained on, for scale
    e1 = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))["rows"]
    for st in ("tweezers-cpl", "bee-3-cpl"):
        sel = [r for r in e1 if r["stack"] == st]
        if sel:
            print(f"{st:>14s} {np.median([r['radius'] for r in sel]):>9.0f} "
                  f"{'(in-sample)':>10s} "
                  f"{np.median([abs(r['dR']) for r in sel]):>10.4f}")
    dump("e7_cross_instrument", out)
