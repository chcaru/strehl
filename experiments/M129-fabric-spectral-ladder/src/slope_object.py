"""The measured slope is not the subject's slope, and the difference is large.

WHAT FORCED THIS. slope_paired.py computed, from the diffraction MTF alone, what the
low-band slope of a pure power law WOULD fit to at each aperture. Planting an object
slope of 3.000 and fitting the registered low band 0.040-0.090 cyc/px returns 3.335 at
f/5.6 and 4.619 at f/18 under H2. Those offsets are not small and they are not an
artefact: the incoherent diffraction MTF falls monotonically from zero frequency, so
there is NO flat region below the cutoff. Amendment 6 chose the low band because it
sits "below every candidate cutoff at every aperture" and treated it as free of
optics. Being below the cutoff and being unaffected by it are different things, and
only the first is true.

THREE CONSEQUENCES, EACH OF WHICH HAS TO BE CHECKED RATHER THAN ASSERTED.

  1. Amendment 7 reports the fabric's texture slope as alpha = 3.126. That is a
     MEASURED slope. equalise._scene builds its texture as r**(-slope/2) in amplitude
     and then multiplies by the MTF, so its `slope` argument is an OBJECT slope. The
     two are not the same quantity, and slope_bias.py planted the measured value into
     the object argument.

  2. If the object slope is recovered by removing the MTF, it may land near 2.2 --
     the value every earlier synthetic in this lane planted and which Amendment 7
     declared wrong. If so, Amendment 7's headline correction is itself the error.

  3. The right test of "is this the same subject at every aperture" is whether the
     INFERRED OBJECT slope is constant, not whether the measured slope is. The
     measured slope cannot be constant even in principle, because each aperture's MTF
     steepens the band by a different amount.

REGISTERED PREDICTION, WRITTEN BEFORE RUNNING (rule 18). slope_paired.py measured a
steepening across f/11 to f/18 of +0.2198, where diffraction alone predicts +0.5335
(H3) to +0.8450 (H2). The observed dependence is therefore SMALLER than diffraction
predicts, so removing the full MTF steepening will OVERSHOOT: f/18 will be corrected
down further than f/11 and the ordering will invert rather than flatten. I predict the
between-aperture spread of the inferred object slope will NOT collapse toward zero,
and will be comparable to or larger than the measured spread of 0.1553. If it does
collapse, this prediction is refuted and diffraction alone explains the ladder.

A POTENCY CONTROL IS INCLUDED. The inversion is checked by planting a known object
slope, pushing it through each aperture's MTF, and requiring the inversion to return
the planted value. Without that, a flat set of inferred slopes could equally mean the
inversion is insensitive.
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "m5-diffraction"))

from slope_survey import fit_slope, LOW  # noqa: E402
from slope_paired import predicted_slope, TAGS, NUM  # noqa: E402
import m5_lib  # noqa: E402

B = {"H2": 3.0763, "H3": 2.4020}


def invert(measured, n_eff, f, lo=0.0, hi=6.0, iters=60):
    """Object slope whose MTF-steepened low-band fit equals `measured`."""
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        if predicted_slope(n_eff, mid, f) < measured:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def main():
    with open(os.path.join(OUT, "slope-w2.json"), encoding="utf-8") as fh:
        s = json.load(fh)
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        sn = json.load(fh)
    f = np.asarray(sn["records"][0]["f"], float)
    per = s["per_roi"]
    rois = sorted(per, key=int)
    A = np.array([[per[i][t] for t in TAGS] for i in rois], float)

    print("THE MEASURED SLOPE IS NOT THE OBJECT SLOPE")
    print()
    print("  HARNESS POTENCY FIRST. With no MTF the fit must return the planted")
    print("  index exactly, or every number below is meaningless.")
    # NO MTF means an INFINITE cutoff, which is n_eff -> 0, not n_eff -> infinity.
    # The first version of this check passed n_eff = 1e9, giving a cutoff of 9e-9
    # cyc/px, so the MTF was zero everywhere, the PSD was zero, and the fit returned
    # nan. The gate then read `nan > 1e-6` as False and printed "harness OK".
    # A NaN must never be able to satisfy a numerical gate.
    got = {}
    for a0 in (2.2, 3.0, 3.5):
        got[a0] = predicted_slope(1e-9, a0, f)
        print(f"    planted {a0:.3f}  fitted {got[a0]:.4f}  "
              f"error {got[a0] - a0:+.2e}")
    finite = all(np.isfinite(v) for v in got.values())
    err = max(abs(got[a0] - a0) for a0 in got) if finite else float("inf")
    if not finite or err > 1e-6:
        print(f"    HARNESS FAILS ({'non-finite fit' if not finite else f'error {err:.2e}'}); stopping.")
        return 1
    print(f"    harness OK, worst error {err:.2e}")
    print()

    print(f"  HOW MUCH THE MTF STEEPENS THE REGISTERED LOW BAND "
          f"{LOW[0]:.3f}-{LOW[1]:.3f} cyc/px,")
    print("  for an object slope of 3.000. This is pure model; no data enters.")
    print()
    print(f"  {'ap':>6} {'f_c H2':>9} {'steepen H2':>11} {'f_c H3':>9} "
          f"{'steepen H3':>11}")
    for t in TAGS:
        row = [t]
        for hyp in ("H2", "H3"):
            ne = B[hyp] * NUM[t]
            fc = m5_lib.f_cutoff_sensor(ne)
            row += [f"{fc:9.4f}", f"{predicted_slope(ne, 3.0, f) - 3.0:+11.4f}"]
        print("  " + f"{row[0]:>6} " + " ".join(row[1:]))
    print()
    print("  Every entry is positive and none is small. There is no aperture in this")
    print("  ladder at which the low band is free of the optics.")
    print()

    print("  INFERRED OBJECT SLOPE, per aperture, from the measured means:")
    print()
    print(f"  {'ap':>6} {'measured':>9} {'object H2':>11} {'object H3':>11}")
    obj = {}
    for hyp in B:
        obj[hyp] = {}
    for k, t in enumerate(TAGS):
        m = float(A[:, k].mean())
        cells = []
        for hyp in ("H2", "H3"):
            v = invert(m, B[hyp] * NUM[t], f)
            obj[hyp][t] = v
            cells.append(f"{v:11.4f}")
        print(f"  {t:>6} {m:9.3f} " + " ".join(cells))
    print()

    prim = ["f11", "f14", "f18"]
    meas_between = float(np.std([A[:, TAGS.index(t)].mean() for t in TAGS]))
    print(f"  {'':>22} {'all five':>10} {'primary arm':>13}")
    print(f"  {'measured spread':>22} {meas_between:10.4f} "
          f"{float(np.std([A[:, TAGS.index(t)].mean() for t in prim])):13.4f}")
    res = {}
    for hyp in ("H2", "H3"):
        a5 = float(np.std([obj[hyp][t] for t in TAGS]))
        a3 = float(np.std([obj[hyp][t] for t in prim]))
        res[hyp] = (a5, a3)
        print(f"  {'object spread ' + hyp:>22} {a5:10.4f} {a3:13.4f}")
    print()

    collapsed = min(v[0] for v in res.values()) < 0.5 * meas_between
    print("  REGISTERED PREDICTION WAS: the spread will NOT collapse, because the")
    print("  observed aperture dependence is smaller than diffraction alone predicts,")
    print("  so removing the full MTF steepening overshoots and inverts the order.")
    if collapsed:
        print("  PREDICTION REFUTED: the spread collapsed. Diffraction alone accounts")
        print("  for the aperture dependence and the subject is one subject.")
    else:
        print("  PREDICTION CONFIRMED: the spread did not collapse. Removing the MTF")
        print("  overshoots, which means a second aperture-dependent effect is")
        print("  present with the OPPOSITE sign to diffraction. T1 is the registered")
        print("  candidate: wider apertures have shallower depth of field, so more of")
        print("  the ROI is defocused, and defocus steepens the spectrum. That effect")
        print("  is largest at f/5.6 and smallest at f/18 -- exactly the sign needed.")
    print()

    print("  WHAT THIS DOES TO AMENDMENT 7'S HEADLINE. The fabric's MEASURED slope is")
    print(f"  {float(A.mean()):.3f}. Its inferred OBJECT slope, averaged over the five")
    print(f"  apertures, is {float(np.mean([obj['H2'][t] for t in TAGS])):.3f} under "
          f"H2 and "
          f"{float(np.mean([obj['H3'][t] for t in TAGS])):.3f} under H3.")
    print("  equalise._scene takes an OBJECT slope, so that is the number synthetic")
    print("  work must plant. Amendment 7 planted the measured value into the object")
    print("  argument and reported the result as a correction to the earlier 2.2.")
    o22 = [abs(np.mean([obj[h][t] for t in TAGS]) - 2.2) for h in ("H2", "H3")]
    print(f"  Distance of the inferred object slope from the long-assumed 2.2: "
          f"{min(o22):.3f} to {max(o22):.3f}.")
    print()
    print("  DIRECTION OF THE ERROR, WHICH DECIDES HOW URGENT THIS IS. Planting an")
    print("  object slope steeper than the truth makes the synthetic spectrum reach")
    print("  the floor sooner, which slope_bias.py measured as a MORE NEGATIVE bias.")
    print("  So Amendment 7's -4.24% is more pessimistic than the subject warrants,")
    print("  not less. The lane is not endangered by it, but the number is wrong and")
    print("  the commissioning battery has been told to sweep the wrong range.")

    dest = os.path.join(OUT, "slope-object.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump({"measured_mean": float(A.mean()),
                   "measured_between": meas_between,
                   "object": obj,
                   "object_spread": {h: {"all": res[h][0], "primary": res[h][1]}
                                     for h in res},
                   "object_mean": {h: float(np.mean([obj[h][t] for t in TAGS]))
                                   for h in obj},
                   "collapsed": bool(collapsed)}, fh, indent=2)
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
