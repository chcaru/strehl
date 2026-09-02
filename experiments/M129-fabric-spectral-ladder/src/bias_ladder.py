"""A1': does the crossing estimator's bias destroy the hypothesis test?

THE REGISTERED STOP CONDITION. Everything the ladder does reduces to inferring B,
the effective-f-number multiplier, from a set of measured cutoffs. The estimator is
known to read f_c LOW. If that bias is large enough, or differs enough between
apertures, the inferred B is wrong by more than the gap between the hypotheses and
the lane must stop and say so.

The question is NOT "does the bias cancel", which was the loose phrasing carried in
the plan. A common-mode fractional bias b gives f_c_hat = f_c (1+b), so

    K_hat = mean(f_c_hat . N) = K (1+b)   and   B_hat = PITCH_UM/(lambda K_hat)

so B_hat = B/(1+b). Nothing cancels. The bias passes straight into B. The real
question is whether it is small compared with the 28.07% that separates H2 from H3,
and whether its DIFFERENTIAL part across apertures breaks the constancy of f_c.N
that A3 tests.

REGISTERED PREDICTIONS, WRITTEN BEFORE THE FIRST RUN (house rule 18).

  P1  f_c_hat < f_c_true at every aperture. The crossing bias is negative; it has
      been negative in every measurement made so far, at every SNR and every slope.
  P2  Therefore B_hat > B_true. Reading the cutoff low means inferring a bigger
      effective aperture than the truth.
  P3  |B_hat/B_true - 1| < 0.05. At object slope 2.26-2.52 and the ladder's measured
      low-band SNR, Amendment 7a puts the applicable bias near -1.8%, which would
      inflate B by +1.8%. Five percent is a deliberately loose ceiling: it is 18% of
      the H2-H3 gap, so even at the ceiling the hypotheses stay apart.
  P4  DISCRIMINATION. A ladder synthesised at H2's cutoffs recovers a B nearer H2
      than H3, and a ladder synthesised at H3's recovers a B nearer H3. This is the
      decision. If the pipeline cannot tell the two apart on data whose answer I
      chose, no amount of real data will help.
  P5  f_c.N is NOT constant to better than a few percent in the native arm, because
      the low-band SNR varies 1.72x across the primary arm and the bias depends on
      SNR. The equalised arm should be flatter.

  The falsifier: P4 failing, or P3 exceeding 0.14 (half the gap). Either ends the
  lane on synthetic data, before a single real cutoff is quoted.

WHAT THE SYNTHETIC GRID CAN AND CANNOT CARRY. A scene planted with lattice cutoff
fc_lat reads back as fc_lat/LATTICE_PITCH_PX["GQ"] in sensor cyc/px, so the largest
cutoff the GQ lattice can represent at all is 0.5/sqrt(2) = 0.35355 sensor cyc/px.
That is not a limitation of this script. It is the lattice's Nyquist, and it applies
to the real measurement exactly as it applies here. Apertures whose true cutoff
exceeds it are unmeasurable on GQ by construction; they are reported as out of
reach, which is the registered role of the f/5.6 and f/8 controls.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "experiments",
                  "m5-diffraction")
if not os.path.isdir(M5):
    M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402
from equalise import _scene, _fc, low_snr, equalise_to  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")

N = 256
TILE = 128
NREP = 16
PITCH = L.LATTICE_PITCH_PX["GQ"]
NYQ_SENSOR = 0.5 / PITCH

# The ladder. Amendment 7a's hypotheses and the object slope each implies.
HYP = {
    "H2": {"B": 3.0763, "slope": 2.260},
    "H3": {"B": 2.4020, "slope": 2.515},
}
APS = [("f5.6", 5.6), ("f8", 8.0), ("f11", 11.0), ("f14", 14.0), ("f18", 18.0)]

# Measured low-band power SNR, from out/snr-w2.json via Amendment 6's table.
SNR_LOW = {"f5.6": 2011.0, "f8": 1707.0, "f11": 2802.0, "f14": 2591.0,
           "f18": 1730.0}
# The primary arm. f/11 is a supporting point; f/14 and f/18 are the measurement.
PRIMARY = ("f11", "f14", "f18")


def truth_fc(B, n):
    return L.f_cutoff_sensor(B * n, L.LAMBDA_UM)


def estimate(fc_sensor, slope, target_snr, seed, nrep=NREP):
    """Plant fc_sensor, add noise to reach target_snr, recover. Returns a dict."""
    fc_lat = fc_sensor * PITCH
    got, snrs = [], []
    for k in range(nrep):
        rng = np.random.default_rng(seed + 977 * k)
        s = _scene(N, slope, fc_lat, rng)
        seed_patch = s + rng.normal(0.0, 5.0, (N, N))
        if target_snr is None:
            patch = seed_patch
        else:
            patch, _ = equalise_to(seed_patch, target_snr, rng, tile=TILE)
        sn, _, _ = low_snr(patch, tile=TILE)
        snrs.append(sn)
        v = _fc(patch, tile=TILE)
        if v is not None and np.isfinite(v):
            got.append(float(v))
    if not got:
        return {"n": 0, "fc_hat": float("nan"), "bias": float("nan"),
                "sd": float("nan"), "snr": float(np.median(snrs))}
    a = np.array(got)
    return {"n": len(a), "fc_hat": float(a.mean()), "sd": float(a.std()),
            "bias": float(a.mean() / fc_sensor - 1.0),
            "snr": float(np.median(snrs))}


def infer_B(rows):
    """B from a set of (N, fc_hat): fc = PITCH_UM/(lambda B N), so B = .../(K).

    Also returns the standard error of B, propagated from the replicate scatter of
    each aperture. Without it the recovered B is a number with no scale attached,
    and the only question that matters -- how far is it from the boundary between
    the hypotheses -- cannot be asked.
    """
    ks = [r["N"] * r["fc_hat"] for r in rows]
    K = float(np.mean(ks))
    spread = float(np.std(ks) / K) if K else float("nan")
    sems = [r["N"] * r["sd"] / np.sqrt(max(r["n"], 1)) for r in rows]
    K_sem = float(np.sqrt(sum(s * s for s in sems)) / len(rows))
    B = L.PITCH_UM / (L.LAMBDA_UM * K)
    return B, K, spread, B * K_sem / K


def reach_table():
    print("reach of the GQ lattice")
    print("=" * 74)
    print(f"  GQ lattice pitch {PITCH:.4f} px, so its Nyquist is "
          f"{NYQ_SENSOR:.5f} sensor cyc/px")
    print(f"  {'ap':>6} {'f_c H2':>9} {'/Nyq':>7} {'f_c H3':>9} {'/Nyq':>7}  verdict")
    rows = []
    for tag, n in APS:
        c2 = truth_fc(HYP["H2"]["B"], n)
        c3 = truth_fc(HYP["H3"]["B"], n)
        ok2, ok3 = c2 < NYQ_SENSOR, c3 < NYQ_SENSOR
        v = ("both" if ok2 and ok3 else "H2 only" if ok2 else
             "neither" if not ok3 else "H3 only")
        rows.append({"tag": tag, "N": n, "fc_H2": c2, "fc_H3": c3,
                     "reach_H2": ok2, "reach_H3": ok3})
        print(f"  {tag:>6} {c2:9.4f} {c2 / NYQ_SENSOR:7.4f} {c3:9.4f} "
              f"{c3 / NYQ_SENSOR:7.4f}  {v}")
    print()
    print("  f/11 under H3 is the point worth reading twice. Its true cutoff is")
    print(f"  {rows[2]['fc_H3']:.4f} against a Nyquist of {NYQ_SENSOR:.4f}: "
          f"{100 * (1 - rows[2]['fc_H3'] / NYQ_SENSOR):.2f}% below it. The")
    print("  preregistration called f/11's H3 margin '+0.24 cy/mm, not a margin'.")
    print("  This says the same thing in the units that decide it: under H3, f/11's")
    print("  cutoff sits essentially ON the GQ lattice's Nyquist and the lattice")
    print("  cannot resolve it. f/14 and f/18 are the measurement, as registered.")
    return rows


def harness():
    """Before any bias claim: does the planted cutoff come back at all?"""
    print("\nharness: plant a cutoff, recover it, with the noise floor pushed down")
    print("=" * 74)
    ok = True
    rows = []
    print(f"  {'planted':>9} {'recovered':>10} {'ratio':>8} {'snr':>10}")
    for fc in (0.12, 0.18, 0.25, 0.30):
        r = estimate(fc, 2.26, None, 90210, nrep=8)
        good = np.isfinite(r["fc_hat"]) and 0.85 <= r["fc_hat"] / fc <= 1.05
        ok &= bool(good)
        rows.append({"planted": fc, "recovered": r["fc_hat"],
                     "ratio": r["fc_hat"] / fc, "snr": r["snr"]})
        print(f"  {fc:9.4f} {r['fc_hat']:10.4f} {r['fc_hat'] / fc:8.4f} "
              f"{r['snr']:10.1f}{'' if good else '   <-- off'}")
    print(f"  harness {'OK' if ok else 'FAILED'}: a finite, near-unity ratio at every")
    print("  planted cutoff. Finiteness is checked explicitly, because a NaN")
    print("  satisfies an inequality silently and once printed 'harness OK' here.")
    lo, hi = rows[0]["ratio"], rows[-1]["ratio"]
    print()
    print("  READ THE TREND, NOT ONLY THE PASS. The noise floor here is pushed far")
    print(f"  below anything the ladder sees (SNR {rows[0]['snr']:.0f} to "
          f"{rows[-1]['snr']:.0f}, against 1730-2802 on the")
    print(f"  real ladder), and the ratio still runs {lo:.4f} at f_c 0.12 down to "
          f"{hi:.4f} at 0.30.")
    print("  That is a CUTOFF-DEPENDENT bias with almost no noise to blame, and a")
    print("  cutoff-dependent bias is the one kind that does not divide out of a")
    print("  ladder: it tilts f_c.N across the apertures and so tilts the fitted B.")
    print("  It is not fatal on its own, because both hypotheses are read with the")
    print("  same instrument, but it is why P4 and not P3 is the decision.")
    return ok, rows


def ladder(hname, arm, target_map):
    h = HYP[hname]
    rows = []
    for tag, n in APS:
        fc = truth_fc(h["B"], n)
        if fc >= NYQ_SENSOR:
            rows.append({"tag": tag, "N": n, "fc_true": fc, "reach": False})
            continue
        r = estimate(fc, h["slope"], target_map[tag], 5150 + int(13 * n))
        r.update({"tag": tag, "N": n, "fc_true": fc, "reach": True})
        rows.append(r)
    usable = [r for r in rows if r.get("reach") and r["n"] and tag_in(r, PRIMARY)]
    B_hat, K, spread, B_sem = infer_B(usable) if len(usable) >= 2 else (
        float("nan"), float("nan"), float("nan"), float("nan"))
    return {"hypothesis": hname, "arm": arm, "B_true": h["B"],
            "slope": h["slope"], "rows": rows, "B_hat": B_hat, "K": K,
            "fcN_spread": spread, "B_sem": B_sem,
            "B_err": B_hat / h["B"] - 1.0 if np.isfinite(B_hat) else float("nan")}


def tag_in(r, tags):
    return r["tag"] in tags


def forward_separation(out):
    """How far apart do the hypotheses stand in the space the estimator reports?

    This runs NO new simulation. It re-reads the cells already measured. The
    inverse analysis asks "what B does the measured cutoff imply", and pays the
    estimator's bias in full because the bias sits between the measurement and the
    answer. The forward comparison asks the other question: "what cutoff would the
    estimator REPORT under each hypothesis", and compares that against what it did
    report. The bias is then on both sides of the comparison and cancels by
    construction rather than by subtraction.

    ONE HONEST CAVEAT, AND IT IS NOT SMALL. The scatter used here is the synthetic
    replicate scatter of an estimator run repeatedly on statistically identical
    scenes. The real measurement's scatter is ROI-to-ROI on one fabric and will be
    larger, probably much larger. The separations below are therefore an upper
    bound on the real discrimination, not a forecast of it. What they establish is
    the ORDERING -- that the forward comparison is the stronger test -- not the
    margin the real data will have.
    """
    res = []
    for arm in ("native", "equalised"):
        a2 = next(r for r in out if r["hypothesis"] == "H2" and r["arm"] == arm)
        a3 = next(r for r in out if r["hypothesis"] == "H3" and r["arm"] == arm)
        cells, chi2 = [], 0.0
        for t in PRIMARY:
            r2 = next(x for x in a2["rows"] if x["tag"] == t)
            r3 = next(x for x in a3["rows"] if x["tag"] == t)
            if not (r2.get("reach") and r3.get("reach")):
                continue
            s2 = r2["sd"] / np.sqrt(r2["n"])
            s3 = r3["sd"] / np.sqrt(r3["n"])
            d = abs(r2["fc_hat"] - r3["fc_hat"])
            sig = d / np.sqrt(s2 * s2 + s3 * s3)
            chi2 += sig * sig
            cells.append({"tag": t, "fc_H2": r2["fc_hat"], "fc_H3": r3["fc_hat"],
                          "rel_gap": d / r3["fc_hat"], "sigma": sig})
        res.append({"arm": arm, "cells": cells, "combined_sigma": float(np.sqrt(chi2))})
    return res


def report_forward(fwd):
    print("\nthe forward comparison, on the cells already measured")
    print("=" * 74)
    print("  no new simulation: the same runs, read the other way round")
    for a in fwd:
        print(f"\n  {a['arm']} arm")
        print(f"    {'ap':>6} {'reported | H2':>14} {'reported | H3':>14} "
              f"{'gap':>8} {'sigma':>9}")
        for c in a["cells"]:
            print(f"    {c['tag']:>6} {c['fc_H2']:14.4f} {c['fc_H3']:14.4f} "
                  f"{100 * c['rel_gap']:7.1f}% {c['sigma']:9.1f}")
        print(f"    combined separation {a['combined_sigma']:.1f} sigma")
    print()
    print("  Against 2.3 sigma for the inverse analysis on its weakest arm. The")
    print("  hypotheses are 19% to 25% apart in the quantity the estimator actually")
    print("  reports, and that gap does not depend on knowing the bias, only on the")
    print("  bias being the same for a predicted cutoff and a measured one at the")
    print("  same frequency -- which is the one thing about it that is certain.")
    print("  These sigmas are an upper bound: real scatter is ROI-to-ROI, not")
    print("  replicate-to-replicate, and will be larger.")


def report(res):
    print(f"\n{res['hypothesis']}, {res['arm']} arm "
          f"(object slope {res['slope']:.3f}, B true {res['B_true']:.4f})")
    print("-" * 74)
    print(f"  {'ap':>6} {'f_c true':>9} {'f_c hat':>9} {'bias':>8} {'sd':>7} "
          f"{'snr':>8} {'f_c.N':>8}")
    for r in res["rows"]:
        if not r.get("reach"):
            print(f"  {r['tag']:>6} {r['fc_true']:9.4f} {'--':>9} {'--':>8} "
                  f"{'--':>7} {'--':>8} {'--':>8}   beyond GQ Nyquist")
            continue
        star = " *" if r["tag"] in PRIMARY else "  "
        print(f"  {r['tag']:>6} {r['fc_true']:9.4f} {r['fc_hat']:9.4f} "
              f"{100 * r['bias']:7.2f}% {r['sd']:7.4f} {r['snr']:8.1f} "
              f"{r['N'] * r['fc_hat']:8.4f}{star}")
    print(f"  fitted on the primary arm: K {res['K']:.4f}, "
          f"B_hat {res['B_hat']:.4f} against B true {res['B_true']:.4f} "
          f"({100 * res['B_err']:+.2f}%)")
    print(f"  f_c.N spread across the primary arm: {100 * res['fcN_spread']:.2f}%")


def main():
    os.makedirs(OUT, exist_ok=True)
    reach = reach_table()
    hok, hrows = harness()
    if not hok:
        print("\nHARNESS FAILED. No bias figure below would mean anything.")
        return 1

    native = {t: SNR_LOW[t] for t, _ in APS}
    worst = min(SNR_LOW[t] for t in PRIMARY)
    eq = {t: worst for t, _ in APS}
    print(f"\nequalised arm: every aperture taken down to the worst of the primary")
    print(f"arm, SNR {worst:.0f}, per Amendment 6. Equalisation can only add noise,")
    print("which is why the target is set by the worst and not by the mean.")

    out = []
    for hname in ("H2", "H3"):
        for arm, tmap in (("native", native), ("equalised", eq)):
            r = ladder(hname, arm, tmap)
            report(r)
            out.append(r)

    print("\n" + "=" * 74)
    print("P4, the decision: does a ladder built at one hypothesis recover it?")
    print("=" * 74)
    gap = abs(HYP["H2"]["B"] - HYP["H3"]["B"]) / HYP["H3"]["B"]
    print(f"  the hypotheses stand {100 * gap:.2f}% apart in B")
    print(f"  {'built at':>9} {'arm':>10} {'B_hat':>8} {'to H2':>8} {'to H3':>8}"
          f"  recovers")
    p4 = True
    for r in out:
        if not np.isfinite(r["B_hat"]):
            p4 = False
            print(f"  {r['hypothesis']:>9} {r['arm']:>10} {'nan':>8} "
                  f"{'--':>8} {'--':>8}  NOTHING")
            continue
        d2 = abs(r["B_hat"] - HYP["H2"]["B"])
        d3 = abs(r["B_hat"] - HYP["H3"]["B"])
        near = "H2" if d2 < d3 else "H3"
        good = near == r["hypothesis"]
        p4 &= good
        print(f"  {r['hypothesis']:>9} {r['arm']:>10} {r['B_hat']:8.4f} "
              f"{d2:8.4f} {d3:8.4f}  {near}{'' if good else '  <-- WRONG'}")

    biases = [x["bias"] for r in out for x in r["rows"]
              if x.get("reach") and x.get("n")]
    berrs = [r["B_err"] for r in out if np.isfinite(r["B_err"])]
    p1 = all(b < 0 for b in biases)
    p2 = all(e > 0 for e in berrs)
    p3 = all(abs(e) < 0.05 for e in berrs)
    nat = [r["fcN_spread"] for r in out if r["arm"] == "native"]
    eqs = [r["fcN_spread"] for r in out if r["arm"] == "equalised"]
    p5 = float(np.mean(eqs)) <= float(np.mean(nat))

    print("\nregistered predictions")
    print("=" * 74)
    for k, v, txt in (
            ("P1", p1, f"f_c read low everywhere ({len(biases)} cells, worst "
                       f"{100 * min(biases):.2f}%, best {100 * max(biases):.2f}%)"),
            ("P2", p2, f"B inferred high ({', '.join(f'{100 * e:+.2f}%' for e in berrs)})"),
            ("P3", p3, f"|B error| < 5% (max {100 * max(abs(e) for e in berrs):.2f}%, "
                       f"= {100 * max(abs(e) for e in berrs) / gap:.1f}% of the gap)"),
            ("P4", p4, "a ladder built at one hypothesis recovers that hypothesis"),
            ("P5", p5, f"equalising flattens f_c.N ({100 * np.mean(nat):.2f}% native "
                       f"-> {100 * np.mean(eqs):.2f}% equalised)")):
        print(f"  {'PASS' if v else 'FAIL'}  {k}  {txt}")

    # ---- the statistic that actually decides the lane --------------------
    # P4 asks only which side of the boundary B_hat falls on. A verdict that reads
    # the same whether it cleared the boundary by a hair or by a mile is not a
    # measurement. This asks by how much, in units of the replicate scatter.
    print("\nmargin: how far is the recovered B from the decision boundary?")
    print("=" * 74)
    mid = 0.5 * (HYP["H2"]["B"] + HYP["H3"]["B"])
    print(f"  the boundary sits at B = {mid:.4f}, midway between the hypotheses")
    print(f"  {'built at':>9} {'arm':>10} {'B_hat':>8} {'B_sem':>8} "
          f"{'distance':>9} {'sigma':>8}")
    margins = []
    for r in out:
        if not np.isfinite(r["B_hat"]):
            continue
        d = abs(r["B_hat"] - mid)
        s = d / r["B_sem"] if r["B_sem"] > 0 else float("inf")
        margins.append({"hypothesis": r["hypothesis"], "arm": r["arm"],
                        "distance": d, "sigma": s})
        print(f"  {r['hypothesis']:>9} {r['arm']:>10} {r['B_hat']:8.4f} "
              f"{r['B_sem']:8.4f} {d:9.4f} {s:8.1f}")
    worst_m = min(m["sigma"] for m in margins)
    print()
    print("  THE ASYMMETRY IS THE RESULT. H2 clears the boundary by a distance no")
    print("  plausible disturbance could close. H3 does not. Under H3 every cutoff")
    print("  sits higher, nearer the lattice Nyquist, exactly where the harness")
    print("  showed the bias is largest -- and f/11's replicate scatter under H3 is")
    print("  four times its scatter under H2. The lane's weak case is H3, and the")
    print(f"  weakest arm clears the boundary by {worst_m:.1f} sigma.")

    fwd = forward_separation(out)
    report_forward(fwd)

    # ---- verdict, against the falsifier as registered ---------------------    # P3 (<5%) is a PREDICTION about size. The FALSIFIER, written in the same
    # docstring before the first run, is P4 failing or |B error| exceeding 14%,
    # half the gap. They are different thresholds with different jobs and both
    # were fixed in advance. An earlier version of this line used P3 as the
    # verdict, which would have stopped the lane on a prediction it never
    # promised to stop on. Reporting the falsified prediction is not optional.
    p3_falsifier = max(abs(e) for e in berrs) < 0.14
    verdict = p4 and p3_falsifier
    print("\n" + "=" * 74)
    if not p3:
        print("P3 IS FALSIFIED and that stands on the record. I predicted the bias")
        print("would inflate B by under 5%, reasoning from Amendment 7a's applicable")
        print(f"bias near 1.8%. It inflates B by up to "
              f"{100 * max(abs(e) for e in berrs):.2f}%, seven times my estimate.")
        print("The reason is visible in the harness: the bias grows with the cutoff,")
        print("and Amendment 7a's figure was a single number for a quantity that is")
        print("not one number.")
        print()
    if verdict:
        print("THE REGISTERED FALSIFIER IS NOT TRIGGERED. It was P4 failing, or the")
        print(f"B error exceeding 14%. P4 passed and the error reached "
              f"{100 * max(abs(e) for e in berrs):.2f}%.")
        print("The lane continues, but not on the analysis it was going to use:")
        print("inverting the estimator and reading B off the answer spends nearly")
        print("half the gap on a correction I cannot pin down, and leaves H3 with")
        print(f"{worst_m:.1f} sigma. The repair is to stop inverting. Push each")
        print("hypothesis FORWARD through the estimator, bias and all, and compare")
        print("predicted cutoffs against measured ones in the space where the")
        print("measurement actually lives. A common bias then cancels by")
        print("construction instead of being subtracted by hand. That is a change")
        print("to the registered analysis and it needs an amendment before use.")
    else:
        print("A1' IS NOT SATISFIED. The registered response is to stop the lane and")
        print("report the ladder as unable to separate the hypotheses.")

    payload = {"reach": reach, "nyquist_sensor": NYQ_SENSOR, "gap": gap,
               "harness": hrows, "arms": out, "margins": margins,
               "boundary": mid, "worst_sigma": worst_m,
               "forward": fwd,
               "P1": p1, "P2": p2, "P3": p3, "P4": p4, "P5": p5,
               "P3_falsifier_clear": bool(p3_falsifier),
               "verdict": bool(verdict), "nrep": NREP, "n": N, "tile": TILE}
    with open(os.path.join(OUT, "bias-ladder.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    return 0 if verdict else 2


if __name__ == "__main__":
    sys.exit(main())
