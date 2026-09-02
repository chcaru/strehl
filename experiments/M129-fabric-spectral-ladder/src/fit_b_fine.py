"""Refine B, ask whether one B fits both apertures, and test what B did not fix.

fit_b.py located B near 2.10 on a 0.05 grid by two routes that agreed to 0.0112,
and excluded all three registered hypotheses. It left three things open, and this
file closes them. Predictions are registered here before the first run.

P1  GRID RESOLUTION. The fine minimum lies within 0.05 of the coarse minimum
    B = 2.10. Falsifier: it lands more than 0.10 away, which would mean the coarse
    grid never resolved the minimum and fit_b.py's interval is meaningless.

P2  SIGN OF THE RESIDUAL TREND. Fitting each aperture on its own gives
    B(f/14) > B(f/18). Route A already measured 2.1466 against 2.0309, and the sign
    is predicted, not merely observed: any aperture-INDEPENDENT blur -- pixel
    aperture, residual defocus, aberration -- costs a fixed amount of high-frequency
    contrast, so it inflates the apparent B most where diffraction is weakest, which
    is the wider aperture. Falsifier: B(f/14) < B(f/18), which would rule that
    explanation out and point at something aperture-DEPENDENT instead.

P3  SIZE OF THE TREND. The per-aperture gap exceeds 0.05 in B. Below that a single
    B is tenable and the lane can quote one number.

P4  DID B EXPLAIN THE SHAPE? ladder_diag.py measured the real spectrum running
    above the model through the roll-off, peaking at 1.48x (f/14) and 2.17x (f/18),
    with both computed at H3's B = 2.4020. If the whole excess was simply B being
    too high, then rebuilding at the fitted B collapses it. Registered threshold:
    the peak ratio falls below 1.25 at BOTH apertures. Falsifier: it stays above
    1.5 at either, which says a wrong B was not the cause and the MTF shape itself
    is wrong.

    Same normalisation and the SAME frequency bins as ladder_diag.py, reusing its
    own synth(), so the before and after numbers are directly comparable. A
    different binning would make the comparison meaningless.

STATED BEFORE MEASURING, per house rule 18: I expect P1, P2 and P3 to pass -- P2
and P3 because route A already shows the trend and this is a second route to the
same thing, so agreement would be corroboration and not news. P4 I genuinely do not
know, and it is the one that decides whether this lane reports a number or reports
a broken model.
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
from slope_object import invert  # noqa: E402
from ladder_diag import synth, LOW_BAND  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
INBAND = ["f14", "f18"]
EXACT_N = {"f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
BINS = ((0.10, 0.13), (0.13, 0.16), (0.16, 0.19), (0.19, 0.22),
        (0.22, 0.25), (0.25, 0.28), (0.28, 0.32))
PRIOR_PEAK = {"f14": 1.48, "f18": 2.17}
M = 2.7198
NREP = 14


def main():
    d = json.load(open(os.path.join(OUT, "ladder.json"), encoding="utf-8"))
    sn = json.load(open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8"))
    sl = json.load(open(os.path.join(OUT, "slope-w2.json"), encoding="utf-8"))
    coarse = json.load(open(os.path.join(OUT, "fit-b.json"), encoding="utf-8"))
    meas = {t: d["measured"][t] for t in INBAND}
    mslope = {t: float(sl["per_aperture_mean"][t]) for t in INBAND}
    fgrid = np.array(sn["records"][0]["f"], float)
    fgrid = fgrid[(fgrid >= LOW_BAND[0]) & (fgrid <= LOW_BAND[1])]

    print("fine grid, and one B per aperture")
    print("=" * 78)
    print(f"  {'B':>6} {'p':>7} " +
          " ".join(f"{t + ' pred':>10} {t + ' z':>8}" for t in INBAND) +
          f" {'chi2':>8}")
    grid = []
    for B in np.arange(1.95, 2.361, 0.01):
        row = {"B": float(B), "p": M / (B - 1.0), "z": {}, "pred": {}}
        ok = True
        for t in INBAND:
            fc = L.f_cutoff_sensor(B * EXACT_N[t], L.LAMBDA_UM)
            if fc >= NYQ_SENSOR:
                ok = False
                break
            a0 = invert(mslope[t], B * EXACT_N[t], fgrid)
            r = estimate(fc, a0, meas[t]["low_snr"],
                         88000 + int(31 * EXACT_N[t]), nrep=NREP)
            if not r["n"] or not np.isfinite(r["fc_hat"]):
                ok = False
                break
            sd = np.hypot(meas[t]["sem"], r["sd"] / np.sqrt(r["n"]))
            row["z"][t] = float((meas[t]["mean"] - r["fc_hat"]) / sd)
            row["pred"][t] = {"fc_true": fc, "fc_hat": r["fc_hat"], "slope": a0}
        if not ok:
            continue
        row["chi2"] = float(sum(v * v for v in row["z"].values()))
        grid.append(row)
        print(f"  {B:6.2f} {row['p']:7.4f} " +
              " ".join(f"{row['pred'][t]['fc_hat']:10.4f} {row['z'][t]:8.2f}"
                       for t in INBAND) + f" {row['chi2']:8.2f}")

    best = min(grid, key=lambda r: r["chi2"])
    inside = [r["B"] for r in grid if r["chi2"] <= best["chi2"] + 1.0]
    per_ap = {t: min(grid, key=lambda r: abs(r["z"][t])) for t in INBAND}
    per_ap_iv = {t: [r["B"] for r in grid if abs(r["z"][t]) <= 1.0]
                 for t in INBAND}

    print("\nresults")
    print("=" * 78)
    cB = coarse["route_B"]["best"]["B"]
    d1 = abs(best["B"] - cB)
    print(f"  joint best B = {best['B']:.2f}, chi2 {best['chi2']:.2f} on 1 dof, "
          f"p = {best['p']:.4f}")
    print(f"  delta chi2 <= 1 spans B {min(inside):.2f} to {max(inside):.2f}")
    print(f"  P1 grid resolution: fine {best['B']:.2f} vs coarse {cB:.2f}, "
          f"moved {d1:.2f} -> {'PASS' if d1 <= 0.05 else 'FAIL'}")
    print()
    print(f"  {'ap':>6} {'B (own z=0)':>12} {'|z|<=1 span':>18} {'p':>8}")
    for t in INBAND:
        iv = per_ap_iv[t]
        span = f"{min(iv):.2f} to {max(iv):.2f}" if iv else "none"
        print(f"  {t:>6} {per_ap[t]['B']:12.2f} {span:>18} "
              f"{M / (per_ap[t]['B'] - 1):8.4f}")
    gap = per_ap["f14"]["B"] - per_ap["f18"]["B"]
    print(f"  P2 sign  : B(f/14) - B(f/18) = {gap:+.2f} -> "
          f"{'PASS' if gap > 0 else 'FAIL'} (predicted positive)")
    print(f"  P3 size  : |gap| = {abs(gap):.2f} -> "
          f"{'PASS' if abs(gap) > 0.05 else 'FAIL'} (registered > 0.05)")
    print(f"  route A gap was {coarse['route_A']['per_aperture']['f14']['B'] - coarse['route_A']['per_aperture']['f18']['B']:+.4f}")

    # ---- P4 --------------------------------------------------------------
    print("\nP4: does the fitted B explain the shape excess?")
    print("=" * 78)
    print("  same bins and same normalisation as ladder-diag, rebuilt at the")
    print("  per-aperture fitted B instead of H3's 2.4020")
    recs = sn["records"]
    shape, peaks = [], {}
    for t in INBAND:
        B = per_ap[t]["B"]
        fc = L.f_cutoff_sensor(B * EXACT_N[t], L.LAMBDA_UM)
        rl = float(np.median([r["bands"]["low"]["snr"] for r in recs
                              if r["aperture"] == t]))
        a0 = invert(mslope[t], B * EXACT_N[t], fgrid)
        _, _, fs, ps = synth(fc, a0, rl, 71000 + int(97 * EXACT_N[t]))
        rr = [r for r in recs if r["aperture"] == t]
        fr = np.array(rr[0]["f"], float)
        pr = np.median(np.array([r["psd"] for r in rr], float), axis=0)

        def norm(f, p):
            s = (f >= LOW_BAND[0]) & (f <= LOW_BAND[1])
            return p / float(np.mean(p[s]))

        nr, ns = norm(fr, pr), norm(fs, ps)
        print(f"\n  {t}, fitted B {B:.2f}, cutoff {fc:.4f}")
        print(f"    {'f':>8} {'real':>11} {'synth':>11} {'ratio':>8} "
              f"{'was (H3)':>9}")
        prior = {(r["lo"], r["hi"]): r["ratio"] for r in
                 json.load(open(os.path.join(OUT, "ladder-diag.json"),
                                encoding="utf-8"))["shape"] if r["tag"] == t}
        rats = []
        for lo, hi in BINS:
            a, b = (fr >= lo) & (fr < hi), (fs >= lo) & (fs < hi)
            if not a.any() or not b.any():
                continue
            va, vb = float(np.mean(nr[a])), float(np.mean(ns[b]))
            rat = va / vb if vb else float("nan")
            rats.append(rat)
            shape.append({"tag": t, "lo": lo, "hi": hi, "real": va,
                          "synth": vb, "ratio": rat,
                          "prior": prior.get((lo, hi))})
            pw = prior.get((lo, hi))
            print(f"    {0.5 * (lo + hi):8.3f} {va:11.3e} {vb:11.3e} "
                  f"{rat:8.2f} {(f'{pw:9.2f}' if pw else ' ' * 9)}")
        peaks[t] = float(np.nanmax(rats))
        print(f"    peak ratio {peaks[t]:.2f}, was {PRIOR_PEAK[t]:.2f} at H3")

    p4 = all(peaks[t] < 1.25 for t in INBAND)
    p4f = any(peaks[t] > 1.5 for t in INBAND)
    print(f"\n  P4: peaks " + ", ".join(f"{t} {peaks[t]:.2f}" for t in INBAND) +
          f" -> {'PASS' if p4 else 'FAIL'}"
          f"{'  (FALSIFIER TRIPPED: > 1.5)' if p4f else ''}")

    payload = {"grid": grid, "best": best,
               "interval": [min(inside), max(inside)],
               "per_aperture": {t: {"B": per_ap[t]["B"],
                                    "interval": [min(per_ap_iv[t]),
                                                 max(per_ap_iv[t])]
                                    if per_ap_iv[t] else None,
                                    "p": M / (per_ap[t]["B"] - 1)}
                                for t in INBAND},
               "gap": gap, "shape": shape, "peaks": peaks,
               "P1": bool(d1 <= 0.05), "P2": bool(gap > 0),
               "P3": bool(abs(gap) > 0.05), "P4": bool(p4),
               "P4_falsifier": bool(p4f), "nrep": NREP, "m": M}
    with open(os.path.join(OUT, "fit-b-fine.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote out/fit-b-fine.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
