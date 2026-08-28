# -*- coding: utf-8 -*-
"""Pre-register the order-statistic model's prediction for a subject that has
NOT been measured yet.

`vn_ninv.py` on coffee-bubbles found that the N-dependent softening is not
share dilution -- an arm with zero dilution by construction softened MORE than
shipping, and across four arms the correlation between dilution and softening
runs backwards. What it found instead is a selection premium: on a synthetic
stack carrying no focus signal whatsoever, choosing a winner instead of
averaging multiplies manufactured 0.30-0.35 noise power, and the multiplier
grows with N.

That is the max-of-N order statistic. For N iid draws the mean has band power
~ 1/N while the max has ~ 2 ln N, so the premium should scale as 2 N ln N.
Fitting a curve to the subject that suggested it proves nothing, so this
script writes the prediction for a DIFFERENT subject to disk before that
subject is run. `vn_ninv.py` only ever reads this file.

The calibration is a single scalar taken from the subject already measured:
premium(N) = C * 2 N ln N, with C fixed by that subject's deepest arm. The
refutation interval is deliberately wide (a factor of 1.5 either way) because
the absolute premium depends on the smoothing and the admission floor, which
the iid model does not describe; what the model claims to predict is the
GROWTH, and a factor of 1.5 is far tighter than the 6x growth being predicted.
"""
import io
import json
import os
import sys
import time

import numpy as np

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\ninv"
TOL = 1.5


def model(n):
    return 2.0 * n * np.log(n)


def main():
    if len(sys.argv) < 4:
        print("usage: vn_prereg.py <from-subject> <to-subject> <to-N>")
        return 2
    src, dst, at_n = sys.argv[1], sys.argv[2], int(sys.argv[3])

    p = os.path.join(OUT, "%s.json" % src)
    if not os.path.exists(p):
        print("REFUSED: %s has not been measured, so there is nothing to "
              "calibrate from" % src)
        return 2
    d = json.load(io.open(p, encoding="utf-8"))

    dp = os.path.join(OUT, "%s.json" % dst)
    if os.path.exists(dp):
        print("REFUSED: %s has ALREADY been measured (%s). A prediction "
              "written now would not be out-of-sample and this file will not "
              "pretend otherwise."
              % (dst, time.strftime("%Y-%m-%d %H:%M:%S",
                                    time.localtime(os.path.getmtime(dp)))))
        return 2

    prem = d["mechanism"]["premium"]
    ns = sorted(int(k) for k in prem)
    cal_n = ns[-1]
    c = prem[str(cal_n)] / model(cal_n)
    point = c * model(at_n)
    rec = dict(point=float(point),
               interval=[float(point / TOL), float(point * TOL)],
               at_N=at_n, band="0.30-0.35",
               calibrated_from=dict(subject=src, N=cal_n,
                                    premium=prem[str(cal_n)], C=float(c)),
               model="premium(N) = C * 2 N ln N",
               written_at=time.strftime("%Y-%m-%d %H:%M:%S"))

    fp = os.path.join(OUT, "prereg.json")
    all_ = {}
    if os.path.exists(fp):
        all_ = json.load(io.open(fp, encoding="utf-8"))
    if dst in all_:
        print("REFUSED: a prediction for %s already exists, written %s; "
              "overwriting it would destroy the pre-registration"
              % (dst, all_[dst]["written_at"]))
        return 2
    all_[dst] = rec
    json.dump(all_, io.open(fp, "w", encoding="utf-8"), indent=1)

    print("pre-registered, %s" % rec["written_at"])
    print("  calibrated on %s at N=%d: premium %.2f => C = %.5f"
          % (src, cal_n, prem[str(cal_n)], c))
    print("  PREDICTION for %s at N=%d: selection premium %.1f"
          % (dst, at_n, point))
    print("  the model is REFUTED if the measurement falls outside "
          "%.1f to %.1f" % (rec["interval"][0], rec["interval"][1]))
    print("  growth predicted from N=%d to N=%d: %.2fx"
          % (cal_n, at_n, model(at_n) / model(cal_n)))
    print("wrote %s" % fp)
    return 0


if __name__ == "__main__":
    sys.exit(main())
