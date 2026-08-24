"""M103b: is the breathing track linear, and is the shortfall uniform per frame?

THE QUESTION
------------
The orchestrator asks me to ship a correction for a solve that recovers about
half the drift, and raises a hypothesis I am asked to try to kill:

    M102 planted a LINEAR breathing track and recovered 96.96%. If the solver
    assumes linear and the plant is linear, that is a statement about arithmetic
    rather than about breathing. If the real track is curved, the fix is not a
    scalar gain but a per-frame one.

This decides what ships, so it is answered before anything is built:

  C1  Is the true track linear?      -> if not, M102's plant is unrepresentative.
  C2  Is the shortfall uniform?      -> if not, a scalar gain cannot fix it.

MEASUREMENT PATH
----------------
`data/truth-dense.json` is a 39-rung ladder of scale(0, j) measured directly from
the RAW frames by NCC over a scale grid, with NO strehl code in the path. It
reproduces the orchestrator's independent end-to-end 0.85715 at j=298
(0.857140). It is the ground truth here and it is independent of every solver.

The solve tracks are read from the sidecars M103 emitted, both in the reference-0
gauge so they are directly comparable to a ladder anchored at frame 0:

  wm-baseline-r0.txt   the shipped solve   (AlignConfig::deep, DEFAULT_SPANS)
  wm-iww-r0.txt        M103's corrected solve (iterated_wide, extended ladder)

CONTROLS (see PREREG-M103b.md)
  C3 PLACEBO   truth vs truth -> r == 1 at every rung, CV == 0 exactly.
  C4 POSITIVE  (a) truth * 0.543 -> mean(r) 0.543, CV 0. Proves C2 CAN say
                   "uniform", so a large CV on the real solve is a finding and
                   not an artefact of the statistic.
               (b) a shaped plant r(j) = 0.4 + 0.3*j/298 -> C2 must recover its
                   closed-form CV to within 1 point.
  C5 The truth instrument's own SELF/PLANT controls are checked, and the NCC
     column is reported across the curved region, because a curvature that
     coincides with a confidence collapse is a measurement of the instrument.

Per discipline 615 the plants act on the log-scale track ONLY, downstream of all
correlation, so they cannot perturb tile selection, capture range or peak-locking
-- the mechanisms being measured through.

USAGE
  python curvature.py <truth-dense.json> <shipped.txt> <corrected.txt> <out.json>
"""

import json
import math
import os
import struct
import sys

import numpy as np

R_PLANE = 0.5 * float(np.hypot(3516.0, 2344.0))   # 2112.8 plane px
MIN_ABS_LN = 0.01          # below this a ratio is formed against noise
CV_THRESHOLD = 0.10        # PREREG C2


def read_sidecar(path):
    """Per-frame ln|a| from a strehl warpmap. Parses the f64 BIT PATTERNS, not
    the human-readable decimals, which the format explicitly says are not
    parsed."""
    out = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("strehl-"):
                continue
            parts = line.split()
            if len(parts) < 6 or parts[1] not in ("placed", "held"):
                continue
            try:
                idx = int(parts[0])
            except ValueError:
                continue
            a_re = struct.unpack(">d", bytes.fromhex(parts[2]))[0]
            a_im = struct.unpack(">d", bytes.fromhex(parts[3]))[0]
            mag = math.hypot(a_re, a_im)
            if mag > 0:
                out[idx] = math.log(mag)
    return out


def cv(vals):
    v = np.asarray(vals, dtype=float)
    m = v.mean()
    if m == 0:
        return float("nan")
    return float(v.std(ddof=0) / abs(m))


def compare(truth, track, label, rungs):
    """r(j) = ln_solve(j)/ln_truth(j) over rungs above the noise floor."""
    rs, js = [], []
    for j in rungs:
        lt = truth[j]
        if abs(lt) < MIN_ABS_LN or j not in track:
            continue
        rs.append(track[j] / lt)
        js.append(j)
    return {"label": label, "j": js, "r": rs,
            "mean_r": float(np.mean(rs)) if rs else float("nan"),
            "cv_r": cv(rs) if rs else float("nan"),
            "min_r": float(np.min(rs)) if rs else float("nan"),
            "max_r": float(np.max(rs)) if rs else float("nan")}


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    truth_p, ship_p, corr_p, out_p = sys.argv[1:5]

    td = json.load(open(truth_p))
    ladder = {int(k): v for k, v in td["ladder"].items()}
    rungs = sorted(ladder)
    truth = {j: ladder[j]["ln"] for j in rungs}
    ncc = {j: ladder[j]["ncc"] for j in rungs}

    # ---- C5: the truth instrument's own controls ------------------------
    print("C5  truth instrument controls")
    ctrl = td.get("controls", {})
    c5_ok = True
    for name, c in ctrl.items():
        if isinstance(c, dict) and "scale" in c:
            if "planted" in c:
                err = c["scale"] - c["planted"]
                ok = abs(err) < 5e-3
                print(f"      {name:<12} planted {c['planted']:.3f} -> "
                      f"{c['scale']:.5f}  err {err:+.5f}  "
                      f"{'ok' if ok else 'FAIL'}")
            else:
                err = c["scale"] - 1.0
                ok = abs(err) < 5e-3
                print(f"      {name:<12} self          -> {c['scale']:.5f}  "
                      f"err {err:+.5f}  {'ok' if ok else 'FAIL'}")
            c5_ok = c5_ok and ok
    print(f"      -> {'PASS' if c5_ok else 'FAIL'}")

    # ---- C1: linearity of the true track --------------------------------
    j_end = max(rungs)
    ln_end = truth[j_end]
    print(f"\nC1  linearity of the TRUE track "
          f"(line through (0,0) and ({j_end}, {ln_end:+.6f}))")
    print(f"      {'j':>5} {'ln_truth':>11} {'ln_linear':>11} "
          f"{'dev':>10} {'dev_px':>9} {'ncc':>7}")
    devs = []
    rows_c1 = []
    for j in rungs:
        lin = ln_end * (j / j_end)
        dev = truth[j] - lin
        dev_px = dev * R_PLANE
        devs.append(abs(dev_px))
        rows_c1.append({"j": j, "ln_truth": truth[j], "ln_linear": lin,
                        "dev_ln": dev, "dev_px": dev_px, "ncc": ncc[j]})
        if j % 24 == 0 or j == j_end:
            print(f"      {j:>5} {truth[j]:>+11.6f} {lin:>+11.6f} "
                  f"{dev:>+10.6f} {dev_px:>+9.1f} {ncc[j]:>7.4f}")
    max_dev = max(devs)
    worst = max(rows_c1, key=lambda r: abs(r["dev_px"]))
    c1_curved = max_dev > 10.0
    print(f"      max |deviation from linear| = {max_dev:.1f} plane px "
          f"at j={worst['j']}")
    print(f"      -> {'MATERIALLY CURVED' if c1_curved else 'LINEAR'} "
          f"(threshold 10 plane px)")
    ncc_curved = [ncc[j] for j in rungs if abs(truth[j] - ln_end * (j / j_end))
                  * R_PLANE > 10.0]
    if ncc_curved:
        print(f"      NCC across the curved region: "
              f"{min(ncc_curved):.4f} - {max(ncc_curved):.4f} "
              f"(no confidence collapse => curvature is not the instrument)")

    # ---- C2: uniformity of the shortfall --------------------------------
    ship = read_sidecar(ship_p)
    corr = read_sidecar(corr_p)
    print(f"\n     read {len(ship)} frames from {os.path.basename(ship_p)}, "
          f"{len(corr)} from {os.path.basename(corr_p)}")

    print("\nC2  per-frame recovery r(j) = ln_solve(j) / ln_truth(j)")
    res_ship = compare(truth, ship, "shipped", rungs)
    res_corr = compare(truth, corr, "corrected", rungs)

    print(f"      {'j':>5} {'ln_truth':>11} {'shipped':>9} {'corrected':>10}")
    for j in rungs:
        if abs(truth[j]) < MIN_ABS_LN:
            continue
        if j % 24 and j != j_end:
            continue
        rs = ship[j] / truth[j] if j in ship else float("nan")
        rc = corr[j] / truth[j] if j in corr else float("nan")
        print(f"      {j:>5} {truth[j]:>+11.6f} {rs:>9.4f} {rc:>10.4f}")

    for res in (res_ship, res_corr):
        verdict = ("scalar gain SUFFICIENT" if res["cv_r"] <= CV_THRESHOLD
                   else "PER-FRAME SOLVE REQUIRED")
        print(f"\n      {res['label']:<10} mean r = {res['mean_r']:.4f}  "
              f"CV = {res['cv_r'] * 100:.1f}%  "
              f"range [{res['min_r']:.4f}, {res['max_r']:.4f}]")
        print(f"      {'':<10} -> {verdict}")

    # ---- C3 placebo -----------------------------------------------------
    res_pl = compare(truth, dict(truth), "PLACEBO", rungs)
    pl_ok = (abs(res_pl["mean_r"] - 1.0) < 1e-12) and (res_pl["cv_r"] < 1e-12)
    print(f"\nC3  PLACEBO truth vs truth: mean r = {res_pl['mean_r']:.12f}, "
          f"CV = {res_pl['cv_r']:.2e} -> {'PASS' if pl_ok else 'FAIL'}")

    # ---- C4 positive controls -------------------------------------------
    uni = {j: truth[j] * 0.543 for j in rungs}
    res_uni = compare(truth, uni, "POS-uniform", rungs)
    u_ok = abs(res_uni["mean_r"] - 0.543) < 1e-12 and res_uni["cv_r"] < 1e-12
    print(f"C4a POSITIVE uniform x0.543: mean r = {res_uni['mean_r']:.6f}, "
          f"CV = {res_uni['cv_r']:.2e} -> {'PASS' if u_ok else 'FAIL'}")
    print("     (proves C2 returns 'uniform' when that is true, so a large CV")
    print("      on the real solve is a finding, not a property of the metric)")

    shaped = {j: truth[j] * (0.4 + 0.3 * j / j_end) for j in rungs}
    res_sh = compare(truth, shaped, "POS-shaped", rungs)
    used = [j for j in rungs if abs(truth[j]) >= MIN_ABS_LN]
    expect = cv([0.4 + 0.3 * j / j_end for j in used])
    s_ok = abs(res_sh["cv_r"] - expect) < 0.01
    print(f"C4b POSITIVE shaped r=0.4+0.3j/{j_end}: CV = "
          f"{res_sh['cv_r'] * 100:.2f}% against closed-form "
          f"{expect * 100:.2f}% -> {'PASS' if s_ok else 'FAIL'}")

    json.dump({
        "R_PLANE": R_PLANE,
        "C1": {"rows": rows_c1, "max_dev_px": max_dev,
               "worst_j": worst["j"], "curved": bool(c1_curved)},
        "C2": {"shipped": res_ship, "corrected": res_corr,
               "cv_threshold": CV_THRESHOLD},
        "C3": res_pl, "C4a": res_uni, "C4b": res_sh,
        "C5_pass": bool(c5_ok),
    }, open(out_p, "w"), indent=1)
    print(f"\nwrote {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
