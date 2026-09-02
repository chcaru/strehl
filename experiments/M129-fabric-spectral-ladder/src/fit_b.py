"""What is B? The registered test asked "H2 or H3" and the data says neither.

ladder.py's first run rejected both hypotheses, with every residual positive: the
real cutoffs sit above what either predicts. reach_guard.py then found why the
comparison was mis-scoped -- the validated out-of-band flag fires 6/6 at f/5.6, f/8
AND f/11, so f/11 was never measuring a diffraction cutoff and had no business in
the chi-squared. Section 2.3 registered f/11 as "a supporting point" whose H3 margin
"is not a margin"; the data has now demoted it further, to a control.

That leaves f/14 and f/18, exactly the two apertures section 2.3 called "the
measurement". Two points and one free parameter. The goodness-of-fit that a third
point would have bought is gone, and this file does not pretend otherwise.

WHAT B MEANS, WHICH IS WHY THIS IS WORTH DOING AT ALL. Section 2.2's three
hypotheses all carry the same magnification -- (B-1)*p is 2.7197, 2.7198, 2.7197 --
and differ only in the pupil magnification p, through B = 1 + m/p. Measuring B
measures p. A larger p means a smaller bellows factor, a higher cutoff and more
recoverable detail at a given marked aperture, which is a fact the stacker needs.

TWO INDEPENDENT ROUTES, REPORTED SEPARATELY AND NEVER AVERAGED.

  A. The physical model fit. knee_model_fit fits N + A f^-alpha MTF(f;f_c)^2 over
     the whole roll-off, so it is not biased downward the way the crossing rule is.
     It buys that by assuming the diffraction MTF shape, which is part of what is
     under test. M5's own docstring calls it "a cross-check, never the headline"
     and it is used here as exactly that.

  B. The forward fit. For each candidate B, synthesise the scene that B implies,
     run the real crossing estimator over it, and compare what it reports against
     what the real estimator reported. Assumes the same MTF shape but pays the
     estimator's bias on both sides, which is the point of Amendment 8.

  If the two disagree the disagreement is the result and both are quoted.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
M5 = os.path.join(os.path.dirname(os.path.dirname(HERE)), "m5-diffraction")
sys.path.insert(0, M5)

import m5_lib as L  # noqa: E402
from bias_ladder import estimate, NYQ_SENSOR  # noqa: E402
from slope_paired import predicted_slope  # noqa: E402
from slope_object import invert  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
INBAND = ["f14", "f18"]
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
HYPS = {"H1": (3.7319, 0.9956), "H2": (3.0763, 1.3099), "H3": (2.4020, 1.9400)}
LOW_BAND = (0.04, 0.09)
NREP = 14


def b_to_p(B, m):
    return m / (B - 1.0) if B > 1.0 else float("inf")


def main():
    d = json.load(open(os.path.join(OUT, "ladder.json"), encoding="utf-8"))
    sn = json.load(open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8"))
    sl = json.load(open(os.path.join(OUT, "slope-w2.json"), encoding="utf-8"))
    cells = d["cells"]

    ms = [(B - 1.0) * p for B, p in HYPS.values()]
    m = float(np.mean(ms))
    print("what B means")
    print("=" * 74)
    print(f"  the three hypotheses carry magnifications "
          f"{', '.join(f'{x:.4f}' for x in ms)}")
    print(f"  spread {max(ms) - min(ms):.2e}, so m = {m:.4f} is common to all three")
    print(f"  and B = 1 + m/p, so measuring B measures the pupil magnification p")
    print()
    print(f"  {'hypothesis':>11} {'B':>8} {'p':>8} {'f_c f/14':>9} {'f_c f/18':>9}")
    for k, (B, p) in HYPS.items():
        print(f"  {k:>11} {B:8.4f} {p:8.4f} "
              f"{L.f_cutoff_sensor(B * EXACT_N['f14'], L.LAMBDA_UM):9.4f} "
              f"{L.f_cutoff_sensor(B * EXACT_N['f18'], L.LAMBDA_UM):9.4f}")

    # ---- route A ---------------------------------------------------------
    print("\nroute A: the physical model fit, per ROI")
    print("=" * 74)
    print(f"  {'ap':>6} {'n':>3} {'fit f_c':>9} {'sd':>8} {'B':>8} {'sd':>8} "
          f"{'p':>8}")
    A = {}
    for t in INBAND:
        v = [c["fit_f_c"] for c in cells
             if c["aperture"] == t and c["fit_f_c"] and c["fit_ok"]]
        if not v:
            continue
        a = np.array(v, float)
        bs = L.PITCH_UM / (L.LAMBDA_UM * EXACT_N[t] * a)
        A[t] = {"n": len(a), "fc": float(a.mean()), "fc_sd": float(a.std(ddof=1)),
                "B": float(bs.mean()), "B_sd": float(bs.std(ddof=1)),
                "B_sem": float(bs.std(ddof=1) / np.sqrt(len(bs)))}
        print(f"  {t:>6} {len(a):3d} {a.mean():9.4f} {a.std(ddof=1):8.4f} "
              f"{bs.mean():8.4f} {bs.std(ddof=1):8.4f} {b_to_p(bs.mean(), m):8.4f}")
    allb = np.array([L.PITCH_UM / (L.LAMBDA_UM * EXACT_N[c["aperture"]] * c["fit_f_c"])
                     for c in cells
                     if c["aperture"] in INBAND and c["fit_f_c"] and c["fit_ok"]])
    A_all = {"B": float(allb.mean()), "sd": float(allb.std(ddof=1)),
             "sem": float(allb.std(ddof=1) / np.sqrt(len(allb))), "n": len(allb)}
    print(f"  pooled over {A_all['n']} cells: B = {A_all['B']:.4f} "
          f"+- {A_all['sem']:.4f} (sd {A_all['sd']:.4f}), "
          f"p = {b_to_p(A_all['B'], m):.4f}")
    print(f"  agreement between the two apertures: "
          f"{abs(A['f14']['B'] - A['f18']['B']):.4f} in B, against a pooled s.e. of "
          f"{A_all['sem']:.4f}")

    # ---- route B ---------------------------------------------------------
    print("\nroute B: the forward fit")
    print("=" * 74)
    meas = {t: d["measured"][t] for t in INBAND}
    assert tuple(sl["band"]) == LOW_BAND, (sl["band"], LOW_BAND)
    fgrid = np.array(sn["records"][0]["f"], float)
    fgrid = fgrid[(fgrid >= LOW_BAND[0]) & (fgrid <= LOW_BAND[1])]
    mslope = {t: float(sl["per_aperture_mean"][t]) for t in INBAND}
    print(f"  measured low-band slope: " +
          ", ".join(f"{t} {mslope[t]:.3f} (sd {sl['per_aperture_sd'][t]:.3f})"
                    for t in INBAND))
    print(f"  {NREP} replicates per (B, aperture); the object slope is re-derived")
    print("  at every B, so the model reproduces the measured low-band shape by")
    print("  construction and all discrimination comes from the roll-off")
    print()
    print(f"  {'B':>7} {'p':>7} " +
          " ".join(f"{'pred ' + t:>11}" for t in INBAND) + f" {'chi2':>9}")
    grid, best = [], None
    for B in np.arange(1.90, 3.21, 0.05):
        chi2, preds, okB = 0.0, {}, True
        for t in INBAND:
            n_eff = B * EXACT_N[t]
            fc = L.f_cutoff_sensor(n_eff, L.LAMBDA_UM)
            if fc >= NYQ_SENSOR:
                okB = False
                break
            a0 = invert(mslope[t], n_eff, fgrid)
            r = estimate(fc, a0, meas[t]["low_snr"], 88000 + int(31 * EXACT_N[t]),
                         nrep=NREP)
            if not r["n"] or not np.isfinite(r["fc_hat"]):
                okB = False
                break
            sd = np.hypot(meas[t]["sem"], r["sd"] / np.sqrt(r["n"]))
            z = (meas[t]["mean"] - r["fc_hat"]) / sd
            chi2 += z * z
            preds[t] = {"fc_true": fc, "fc_hat": r["fc_hat"], "slope": a0,
                        "sd": r["sd"], "z": float(z)}
        if not okB:
            continue
        row = {"B": float(B), "p": b_to_p(B, m), "chi2": float(chi2),
               "preds": preds}
        grid.append(row)
        if best is None or chi2 < best["chi2"]:
            best = row
        print(f"  {B:7.2f} {b_to_p(B, m):7.4f} " +
              " ".join(f"{preds[t]['fc_hat']:11.4f}" for t in INBAND) +
              f" {chi2:9.2f}")

    print()
    if best is None:
        print("  NO FIT: every candidate B put a cutoff beyond the lattice reach.")
        return 1
    lo = min((r["B"] for r in grid if r["chi2"] <= best["chi2"] + 1.0),
             default=best["B"])
    hi = max((r["B"] for r in grid if r["chi2"] <= best["chi2"] + 1.0),
             default=best["B"])
    print(f"  best B = {best['B']:.2f}, chi2 {best['chi2']:.2f} on 1 dof")
    print(f"  delta chi2 <= 1 spans B {lo:.2f} to {hi:.2f}, "
          f"p {b_to_p(hi, m):.2f} to {b_to_p(lo, m):.2f}")
    print(f"  route A gave B = {A_all['B']:.4f}; the two routes differ by "
          f"{abs(best['B'] - A_all['B']):.4f}")

    print("\nwhere the registered hypotheses sit")
    print("=" * 74)
    for k, (B, p) in HYPS.items():
        near = min(grid, key=lambda r: abs(r["B"] - B))
        dchi = near["chi2"] - best["chi2"]
        verdict = ("inside the interval" if near["chi2"] <= best["chi2"] + 1.0
                   else f"excluded, delta chi2 {dchi:.1f} "
                        f"({np.sqrt(dchi):.1f} sigma)")
        print(f"  {k}: B {B:.4f}, p {p:.4f} -> {verdict}")

    payload = {"m": m, "route_A": {"per_aperture": A, "pooled": A_all},
               "route_B": {"grid": grid, "best": best, "lo": lo, "hi": hi},
               "measured": meas, "measured_slope": mslope,
               "inband": INBAND, "nrep": NREP}
    with open(os.path.join(OUT, "fit-b.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/fit-b.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
