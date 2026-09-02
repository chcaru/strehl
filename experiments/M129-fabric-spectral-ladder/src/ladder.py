"""The M129 measurement: real cutoffs, compared forward against both hypotheses.

This is the reduction the whole lane exists to perform. It reads the radial PSDs
already saved by snr_survey.py -- there is no new decode, because snr_survey kept
the whole spectrum per (ROI, aperture) precisely so this step would not need one --
runs m5_lib's crossing estimator over each, and compares the result against what
each hypothesis predicts the estimator would report.

WHY FORWARD AND NOT INVERSE. Amendment 8 measured what inverting the estimator
costs: the bias reaches 13% of B, nearly half the gap between the hypotheses, and
leaves H3 clearing the decision boundary by 2.3 sigma. The same runs read forward --
predicting the cutoff the estimator would REPORT under each hypothesis, and
comparing that against what it did report -- separate the hypotheses by 60.6 sigma,
because the bias then sits on both sides of the comparison. That change is
registered in Amendment 8 and this is the first use of it.

WHAT THE FORWARD MODEL IS TUNED TO, AND WHAT THAT COSTS. Each prediction plants the
object slope that Amendment 7a inferred for that hypothesis at that aperture, so the
synthetic spectrum reproduces the measured low-band shape by construction. That is
deliberate and it has a consequence worth stating plainly: THE LOW BAND THEREFORE
CARRIES NO DISCRIMINATING INFORMATION. Every bit of separation comes from where the
roll-off meets the floor. This is a strength rather than a concession -- the test
depends on the cutoff and not on the texture -- but it means the low band must never
be quoted as independent support for the verdict.

REGISTERED BEFORE THE FIRST RUN (house rule 18):

  R1  The dynamic-range gate will pass at a far higher rate than M5's 0/113. M5's
      subject was a dark ragged edge; this is a bright woven fabric chosen for
      broadband contrast. A gated rate below 50% would be a surprise and would
      itself need explaining before any cutoff is quoted.
  R2  Measured f_c falls monotonically with f-number, in every ROI. This is not a
      hypothesis, it is diffraction; if it fails the reduction is broken.
  R3  f_c . N is NOT constant across the primary arm. Amendment 8 measured the
      estimator's own cutoff-dependent bias, which tilts the product by a few
      percent even when the physics is exact.

  I do NOT predict which hypothesis wins. That is the measurement, and the
  statistic that decides it -- chi-squared over the primary arm, both arms
  reported, ROI-to-ROI scatter as the denominator -- was fixed in Amendment 8
  before this file existed.
"""

import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402
from bias_ladder import estimate, HYP, PRIMARY, NYQ_SENSOR  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
TAGS = ["f5.6", "f8", "f11", "f14", "f18"]
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}


def cy_mm(f):
    return f * 1000.0 / L.PITCH_UM


def measure(recs, gq_size, tile):
    """Run the crossing estimator over every saved PSD."""
    cells = []
    for r in recs:
        f = np.array(r["f"], float)
        p = np.array(r["psd"], float)
        c = np.array(r["counts"], float)
        k = L.knee(f, p, c, tile, gq_size, "GQ")
        m = L.knee_model_fit(f, p, c)
        cells.append({
            "roi": r["roi"], "aperture": r["aperture"], "N": r["N"],
            "frame": r["frame"], "file": r["file"],
            "f_c": k["f_c"], "dyn": k["dynamic_range"],
            "has_signal": bool(k["has_signal"]), "saturated": bool(k["saturated"]),
            "floor_slope": k["floor_slope"], "f_max": k["f_max"],
            "fit_f_c": m.get("f_c"), "above_reach": bool(m.get("above_reach", False)),
            "fit_ok": bool(m.get("ok", False)),
            "low_snr": r["bands"]["low"]["snr"],
            "knee_snr": r["bands"]["knee"]["snr"],
        })
    return cells


def gate_report(cells):
    """M5's mandatory disclosure: the raw rate AND the gated rate, never one."""
    n = len(cells)
    raw = sum(1 for c in cells if c["f_c"] is not None)
    gated = sum(1 for c in cells if c["f_c"] is not None and c["has_signal"])
    sat = sum(1 for c in cells if c["saturated"])
    print("\nthe dynamic-range gate, reported raw and gated as M5 requires")
    print("=" * 74)
    print(f"  cells                      {n}")
    print(f"  a crossing was found       {raw} ({100 * raw / n:.1f}%)")
    print(f"  ... and passed the gate    {gated} ({100 * gated / n:.1f}%)")
    print(f"  saturated (f_c >= 0.9 fmax) {sat}")
    print("  M5 quoted 113/330 raw and 0 gated on a dark ragged edge. Quoting only")
    print("  one of those two numbers is how a reduction lies without a false")
    print("  statement in it, which is why both are printed here unconditionally.")
    return {"n": n, "raw": raw, "gated": gated, "saturated": sat}


def per_aperture(cells):
    """Mean and ROI-to-ROI scatter of f_c at each aperture, gated cells only."""
    out = {}
    for t in TAGS:
        v = [c["f_c"] for c in cells
             if c["aperture"] == t and c["f_c"] is not None and c["has_signal"]]
        s = [c["low_snr"] for c in cells if c["aperture"] == t]
        if not v:
            out[t] = {"n": 0}
            continue
        a = np.array(v, float)
        out[t] = {"n": len(a), "mean": float(a.mean()),
                  "sd": float(a.std(ddof=1)) if len(a) > 1 else float("nan"),
                  "sem": (float(a.std(ddof=1) / np.sqrt(len(a)))
                          if len(a) > 1 else float("nan")),
                  "low_snr": float(np.median(s)), "N": EXACT_N[t]}
    return out


def predict(objslope, nrep):
    """What would the estimator report, under each hypothesis, at each aperture?"""
    pred = {}
    for hname, h in HYP.items():
        pred[hname] = {}
        for t in TAGS:
            fc = L.f_cutoff_sensor(h["B"] * EXACT_N[t], L.LAMBDA_UM)
            if fc >= NYQ_SENSOR:
                pred[hname][t] = {"fc_true": fc, "reach": False}
                continue
            sl = objslope[hname][t]
            snr = PRED_SNR[t]
            r = estimate(fc, sl, snr, 71000 + int(97 * EXACT_N[t]), nrep=nrep)
            r.update({"fc_true": fc, "reach": True, "slope": sl, "snr_target": snr})
            pred[hname][t] = r
    return pred


def compare(meas, pred, tags):
    """Chi-squared of measured against predicted, in the estimator's own space."""
    res = {}
    for hname in HYP:
        chi2, terms = 0.0, []
        for t in tags:
            m, q = meas.get(t, {}), pred[hname].get(t, {})
            if not m.get("n") or not q.get("reach") or not q.get("n"):
                continue
            sd = np.hypot(m["sem"], q["sd"] / np.sqrt(q["n"]))
            if not np.isfinite(sd) or sd <= 0:
                continue
            z = (m["mean"] - q["fc_hat"]) / sd
            chi2 += z * z
            terms.append({"tag": t, "measured": m["mean"], "predicted": q["fc_hat"],
                          "sd": float(sd), "z": float(z)})
        res[hname] = {"chi2": float(chi2), "dof": len(terms), "terms": terms}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--nrep", type=int, default=16)
    args = ap.parse_args()

    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    with open(os.path.join(OUT, "rois-w2.json"), encoding="utf-8") as fh:
        rd = json.load(fh)
    with open(os.path.join(OUT, "slope-object.json"), encoding="utf-8") as fh:
        so = json.load(fh)
    gq = rd["gq_size"]

    print("M129 ladder: the measurement")
    print("=" * 74)
    print(f"  {len(d['records'])} cells, GQ {gq}, Welch tile {args.tile}")
    print(f"  GQ reach {cy_mm(NYQ_SENSOR):.2f} cy/mm ({NYQ_SENSOR:.5f} sensor cyc/px)")

    cells = measure(d["records"], gq, args.tile)
    gates = gate_report(cells)

    meas = per_aperture(cells)
    global PRED_SNR
    PRED_SNR = {t: (meas[t]["low_snr"] if meas[t].get("n")
                    else float(np.median([c["low_snr"] for c in cells
                                          if c["aperture"] == t])))
                for t in TAGS}

    print("\nmeasured cutoffs, gated cells only")
    print("=" * 74)
    print(f"  {'ap':>6} {'n':>3} {'f_c':>8} {'sd':>8} {'sem':>8} {'cy/mm':>8} "
          f"{'f_c.N':>8} {'low SNR':>9}")
    for t in TAGS:
        m = meas[t]
        if not m.get("n"):
            print(f"  {t:>6} {0:>3}  no gated cell")
            continue
        star = " *" if t in PRIMARY else "  "
        print(f"  {t:>6} {m['n']:3d} {m['mean']:8.4f} {m['sd']:8.4f} "
              f"{m['sem']:8.4f} {cy_mm(m['mean']):8.2f} {m['N'] * m['mean']:8.4f} "
              f"{m['low_snr']:9.1f}{star}")

    # R2, checked per ROI and not on the means, because a monotone mean can be
    # assembled from non-monotone rows.
    print("\nR2: does f_c fall with f-number in every ROI?")
    rois = sorted({c["roi"] for c in cells})
    mono, tested = 0, 0
    for i in rois:
        row = [(EXACT_N[t], c["f_c"]) for t in TAGS
               for c in cells if c["roi"] == i and c["aperture"] == t
               and c["f_c"] is not None and c["has_signal"]]
        row.sort()
        if len(row) < 2:
            continue
        tested += 1
        good = all(row[k][1] >= row[k + 1][1] for k in range(len(row) - 1))
        mono += good
        print(f"  ROI {i}: " + " ".join(f"{v:.4f}" for _, v in row) +
              ("  monotone" if good else "  NOT monotone"))
    print(f"  {mono}/{tested} ROIs monotone")

    print("\nforward predictions: what would the estimator report?")
    print("=" * 74)
    print(f"  {args.nrep} synthetic replicates per cell, each planted at that")
    print("  hypothesis' cutoff with the object slope Amendment 7a infers for it")
    pred = predict(so["object"], args.nrep)
    print(f"  {'ap':>6} {'H2 true':>9} {'H2 report':>10} {'H3 true':>9} "
          f"{'H3 report':>10} {'measured':>10}")
    for t in TAGS:
        p2, p3 = pred["H2"][t], pred["H3"][t]
        mm = meas[t].get("mean")
        f2 = f"{p2['fc_hat']:10.4f}" if p2.get("reach") else f"{'--':>10}"
        f3 = f"{p3['fc_hat']:10.4f}" if p3.get("reach") else f"{'--':>10}"
        ms = f"{mm:10.4f}" if mm is not None else f"{'--':>10}"
        print(f"  {t:>6} {p2['fc_true']:9.4f} {f2} {p3['fc_true']:9.4f} {f3} {ms}")

    print("\nthe verdict: chi-squared over the primary arm")
    print("=" * 74)
    cmp_primary = compare(meas, pred, PRIMARY)
    for hname in ("H2", "H3"):
        r = cmp_primary[hname]
        print(f"  {hname}: chi2 {r['chi2']:10.2f} on {r['dof']} terms")
        for t in r["terms"]:
            print(f"      {t['tag']:>5} measured {t['measured']:.4f} "
                  f"predicted {t['predicted']:.4f} sd {t['sd']:.4f} "
                  f"z {t['z']:+8.2f}")
    if all(cmp_primary[h]["dof"] for h in HYP):
        win = min(HYP, key=lambda h: cmp_primary[h]["chi2"])
        lose = "H3" if win == "H2" else "H2"
        dchi = cmp_primary[lose]["chi2"] - cmp_primary[win]["chi2"]
        print(f"\n  {win} is preferred by delta chi2 = {dchi:.2f}")
        print(f"  ({np.sqrt(abs(dchi)):.2f} sigma if read as a one-parameter "
              f"difference)")
    else:
        win, dchi = None, float("nan")
        print("\n  NO VERDICT: at least one hypothesis has no comparable term.")

    payload = {"cells": cells, "gates": gates, "measured": meas,
               "pred_snr": PRED_SNR,
               "predicted": {h: {t: {k: v for k, v in pred[h][t].items()}
                                 for t in TAGS} for h in HYP},
               "chi2_primary": cmp_primary, "winner": win,
               "delta_chi2": float(dchi) if dchi == dchi else None,
               "monotone": {"ok": mono, "tested": tested},
               "tile": args.tile, "nrep": args.nrep, "gq_size": gq}
    with open(os.path.join(OUT, "ladder.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/ladder.json")
    return 0


PRED_SNR = {}

if __name__ == "__main__":
    sys.exit(main())
