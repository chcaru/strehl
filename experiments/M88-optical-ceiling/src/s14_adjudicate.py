"""M88 s14 — adjudicate fact 1149 (f_c ~ 87) against M84b (f_c ~ 106-135).

The orchestrator asks M88 to decide between two live hypotheses and to state
the result in a form that inverts to the pupil magnification p.

This script does four things.

  1. Checks whether the f/5.6 and f/11 stacks are registered, i.e. whether the
     aperture ratio of section 4.3 compares the SAME edge or two different
     ones. This is a confound audit of M88's own Bar 3.

  2. Calibrates the instrument's rise-vs-cutoff response densely, so that a
     measured rise can be inverted to a cutoff. The response is
     rise(f_c) = sqrt((a/f_c)^2 + b^2): a diffraction term that scales as
     1/f_c, plus an aperture-independent floor from the pixel aperture and the
     ESF binning.

  3. Asks the decisive question: how far apart are the two hypotheses in the
     observable, and is that separation larger or smaller than the measured
     subject-to-subject scatter? If the scatter is larger, the corpus cannot
     adjudicate, and that is a quantitative statement rather than a shrug.

  4. Reports what a hard-edge capture would deliver, in the same units, so the
     capture request is justified by arithmetic rather than by assertion.

Writes out/s14_adjudicate.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import m88lib as L
from s12_closing import rise_1090

LAM_UM = 0.55e-3          # mm
N_MARKED = 5.6
PITCH_MM = 5.12e-3
NYQUIST = 1.0 / (2.0 * PITCH_MM)

# M84b, MEASURED. Supersedes the 2.762 in fact 1149.
M_MAG = 2.7198
M_MAG_SD = 0.0051

# The two live hypotheses, in cy/mm at 550 nm.
H_1149 = (86.30, 87.0)          # fact 1149, p = 1 assumed
H_M84B = (105.54, 135.17)       # M84b/fact 1152, p in [1.31, 1.94]

# Measured 10-90 rises at best focus (from s12), um.
RISE_F56 = [31.75, 31.66, 32.96, 27.83]
RISE_F11 = [42.43, 32.34, 32.65, 31.56]

BIN_UM, TAPER, CORE_UM = 0.64, 0.10, 24.0
CAL_FC = [40.0, 50.0, 60.0, 70.0, 86.3, 100.0, 120.0, 140.0, 170.0, 200.0]


def rise_of_plant(fc, half_um=96.0):
    img = L.synth_edge_frame2(300, 1400, fc, 2.0, 1000.0, 3600.0, sub=8)
    sub, xs, ys = L.green_sites(img, "G1")
    line = L.fit_edge_line(sub, xs, ys, axis="horizontal")
    xx, yy = np.meshgrid(xs, ys)
    res = L.sfr_from_sites2(sub.ravel().astype(float), xx.ravel(), yy.ravel(),
                            line, BIN_UM, half_um, TAPER, core_um=CORE_UM)
    return float(rise_1090(res["centres_um"], res["esf"]))


def calibrate():
    """Fit rise(f_c) = sqrt((a/f_c)^2 + b^2) on noise-free plants."""
    fcs, rises = [], []
    for fc in CAL_FC:
        r = rise_of_plant(fc)
        fcs.append(fc)
        rises.append(r)
        print(f"    fc={fc:6.1f} -> rise {r:6.2f} um")
    fcs = np.asarray(fcs)
    rises = np.asarray(rises)
    # linear least squares in (1/fc^2, 1) against rise^2
    A = np.column_stack([1.0 / fcs ** 2, np.ones_like(fcs)])
    coef, *_ = np.linalg.lstsq(A, rises ** 2, rcond=None)
    a = float(np.sqrt(max(coef[0], 0.0)))
    b = float(np.sqrt(max(coef[1], 0.0)))
    pred = np.sqrt((a / fcs) ** 2 + b ** 2)
    resid = float(np.max(np.abs(pred - rises)))
    print(f"\n    a = {a:.2f} um*cy/mm,  b = {b:.2f} um,  max resid {resid:.3f} um")
    return a, b, resid, fcs.tolist(), rises.tolist()


def registration_audit():
    """Are the two stacks the same edge in the same pose?

    If they are, the aperture ratio is a paired comparison and sigma_other
    cancels. If they are not, the ratio compares different edges and carries a
    confound that must be declared.
    """
    out = []
    for stack, plane, rois in (
        ("119MSDCF", "G1", [("A1", 1280, 0), ("A2", 1280, 200)]),
        ("109MSDCF", "G1", [("C1", 1280, 0), ("C2", 1280, 200)]),
    ):
        scans = json.load(open(Path(__file__).resolve().parents[1] /
                               "out" / f"s06_scan_{stack}_{plane}.json"))
        rows = scans["rows"] if isinstance(scans, dict) else scans
        for name, r0, c0 in rois:
            cand = [r for r in rows if r.get("roi") == name
                    and r.get("mtf40") is not None]
            if not cand:
                continue
            best = max(cand, key=lambda r: r["mtf40"])
            out.append(dict(stack=stack, roi=name, row0=r0, col0=c0,
                            angle_deg=best.get("angle_deg"),
                            contrast=best.get("contrast")))
    for r in out:
        print(f"    {r['stack']:10s} {r['roi']:3s} at (row {r['row0']}, col {r['col0']}): "
              f"angle {r['angle_deg']:7.3f} deg, contrast {r['contrast']:6.0f}")
    a119 = [r for r in out if r["stack"] == "119MSDCF"]
    a109 = [r for r in out if r["stack"] == "109MSDCF"]
    dang = abs(np.mean([r["angle_deg"] for r in a119]) -
               np.mean([r["angle_deg"] for r in a109]))
    rcon = (np.mean([r["contrast"] for r in a119]) /
            np.mean([r["contrast"] for r in a109]))
    registered = bool(dang < 0.3 and 0.8 < rcon < 1.25)
    print(f"\n    same window coordinates, but angle differs by {dang:.2f} deg "
          f"and contrast by {rcon:.2f}x")
    print(f"    REGISTERED: {registered}  -> the aperture ratio compares "
          f"{'the same edge' if registered else 'DIFFERENT edges'}")
    return dict(rows=out, delta_angle_deg=float(dang),
                contrast_ratio=float(rcon), registered=registered)


def discrimination(a, b):
    """Can the observable separate the two hypotheses at all?

    Under rise^2 = d^2 + c^2 with d = a/f_c the diffraction term and c an
    aperture-independent term (pixel aperture, binning, subject softness),
    a given hypothesis for f_c predicts a rise once c is known. The question
    is whether the predicted separation exceeds the measured scatter in c.
    """
    obs = float(np.median(RISE_F56))
    scatter = float(np.std(RISE_F56, ddof=1))
    print(f"    measured f/5.6 rise: median {obs:.2f} um, "
          f"ROI-to-ROI sd {scatter:.2f} um ({100*scatter/obs:.1f}%)")
    print()
    res = []
    for label, (lo, hi) in (("fact 1149", H_1149), ("M84b", H_M84B)):
        for fc in (lo, hi):
            d = a / fc
            c2 = obs ** 2 - d ** 2
            c = float(np.sqrt(c2)) if c2 > 0 else float("nan")
            res.append(dict(hypothesis=label, fc_cymm=fc, d_um=float(d),
                            implied_c_um=c))
            print(f"    {label:10s} fc={fc:7.2f} -> diffraction term d = {d:5.2f} um"
                  f" -> implied subject term c = {c:6.2f} um")
    d_1149 = a / np.mean(H_1149)
    d_m84b = a / np.mean(H_M84B)
    sep = abs(np.sqrt(max(obs ** 2 - d_m84b ** 2, 0)) -
              np.sqrt(max(obs ** 2 - d_1149 ** 2, 0)))
    print()
    print(f"    the two hypotheses differ in predicted rise by only {sep:.2f} um")
    print(f"    the measured ROI-to-ROI scatter in the SAME stack is {scatter:.2f} um")
    print(f"    scatter / separation = {scatter / sep:.2f}x")
    verdict = "CANNOT ADJUDICATE" if scatter > sep else "can adjudicate"
    print(f"    -> {verdict}")
    return dict(rows=res, obs_rise_um=obs, scatter_um=scatter,
                separation_um=float(sep),
                scatter_over_separation=float(scatter / sep),
                can_adjudicate=bool(scatter <= sep))


def invert(fc_lo, fc_hi):
    """f_c -> N_eff -> p, the inversion the orchestrator asked for."""
    out = []
    for fc in (fc_hi, fc_lo):   # high f_c gives low N_eff
        n_eff = 1.0 / (LAM_UM * fc)
        b_fac = n_eff / N_MARKED
        p = M_MAG / (b_fac - 1.0) if b_fac > 1.0 else float("nan")
        out.append(dict(fc_cymm=float(fc), n_eff=float(n_eff),
                        bellows_B=float(b_fac), p=float(p)))
        print(f"    f_c={fc:8.2f} -> N_eff={n_eff:6.2f} -> B={b_fac:5.3f} -> p={p:6.3f}")
    return out


def hard_edge_forecast(a, b):
    """What a negligible-softness edge would deliver, in the same units."""
    print("    on a razor edge (subject term c -> the instrument floor b only):")
    rows = []
    for label, fc in (("fact 1149", 87.0), ("M84b low", 105.54),
                      ("M84b high", 135.17)):
        r = float(np.sqrt((a / fc) ** 2 + b ** 2))
        rows.append(dict(hypothesis=label, fc_cymm=fc, predicted_rise_um=r))
        print(f"      {label:11s} fc={fc:7.2f} -> rise would be {r:6.2f} um")
    spread = max(r["predicted_rise_um"] for r in rows) - \
        min(r["predicted_rise_um"] for r in rows)
    print(f"\n      hypotheses span {spread:.2f} um of rise, "
          f"{100*spread/rows[0]['predicted_rise_um']:.0f}% of the signal")
    print(f"      instrument precision is ~1.5%, so this is resolved "
          f"{spread/rows[0]['predicted_rise_um']/0.015:.0f}x over")
    return dict(rows=rows, spread_um=float(spread))


def main():
    print("=" * 78)
    print("1. REGISTRATION AUDIT: does Bar 3 compare the same edge?")
    print("=" * 78)
    reg = registration_audit()

    print()
    print("=" * 78)
    print("2. INSTRUMENT CALIBRATION: rise as a function of cutoff")
    print("=" * 78)
    a, b, resid, cal_fc, cal_rise = calibrate()

    print()
    print("=" * 78)
    print("3. CAN THE CORPUS ADJUDICATE 87 AGAINST 106-135?")
    print("=" * 78)
    disc = discrimination(a, b)

    print()
    print("=" * 78)
    print("4. WHAT M88 CAN BOUND, AND THE INVERSION TO p")
    print("=" * 78)
    obs = float(np.median(RISE_F56))
    fc_floor = a / obs
    print(f"    hard floor, attributing ALL measured blur to diffraction:")
    print(f"      f_c >= {fc_floor:.1f} cy/mm  (weak: assumes a perfectly hard edge)")
    print(f"    this bound is BELOW both hypotheses "
          f"({H_1149[0]:.0f} and {H_M84B[0]:.0f}), so it excludes neither.")
    print()
    print("    inversion of the two hypotheses to p, with m = 2.7198:")
    inv_1149 = invert(*H_1149)
    inv_m84b = invert(*H_M84B)

    print()
    print("=" * 78)
    print("5. WHAT A HARD-EDGE CAPTURE WOULD DELIVER")
    print("=" * 78)
    fore = hard_edge_forecast(a, b)

    report = dict(
        registration=reg,
        calibration=dict(a_um_cymm=a, b_um=b, max_resid_um=resid,
                         fc=cal_fc, rise_um=cal_rise),
        discrimination=disc,
        fc_hard_floor_cymm=float(fc_floor),
        inversion_fact1149=inv_1149,
        inversion_m84b=inv_m84b,
        hard_edge_forecast=fore,
        constants=dict(lambda_mm=LAM_UM, N_marked=N_MARKED,
                       m=M_MAG, m_sd=M_MAG_SD, nyquist_cymm=NYQUIST),
    )
    out = Path(__file__).resolve().parents[1] / "out" / "s14_adjudicate.json"
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nwrote out/{out.name}")


if __name__ == "__main__":
    main()
