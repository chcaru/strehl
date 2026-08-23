"""M60 / 22 -- is the DENOMINATOR right?

Discipline 338: a separation score whose denominator is a null residual behaves
like a random number.  M60's denominator is not a null residual -- it is
sqrt(sigma_f(k2)^2 + sigma_f(kd)^2) where sigma_f comes from the noise model
INJECTED from crates/strehl-core (AGENTS rule 3).  That is the right shape, but
it is only worth anything if the injected model actually predicts the observed
scatter of f on REAL frames.  Nothing so far has checked that, and the check
must not be run against the constant that generated the prediction (fact 738).

The check.  On a real through-focus curve the second difference

    D_k = f_{k-1} - 2 f_k + f_{k+1}

annihilates any locally linear trend, so for a smooth true curve
Var(D) = 6 sigma^2 and a robust scale of D gives

    sigma_emp = MAD(D) * 1.4826 / sqrt(6)

This is an UPPER bound: real curvature between adjacent frames inflates it and
nothing deflates it.  So sigma_emp / sigma_pred >= 1 is expected, and the size
of the excess is the thing being reported.  sigma_emp is computed from the
observed frames only; sigma_pred is computed by Monte Carlo from the gain and
read-noise constants.  They share no arithmetic.

What this cannot separate: it validates sigma_f as a scale, on these signal
levels, with this operator.  It does not validate the gain itself -- fact 599 /
AGENTS rule 34 -- because a wrong gain would move sigma_pred and would show up
here only as a constant ratio offset, which is exactly what is measured, so a
15% offset is equally consistent with a 15% gain error.
"""

import os
import sys
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cells import CELLS  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
CUR = os.path.join(DATA, "curves")
NUL = os.path.join(DATA, "null")


def robust_sigma_from_second_difference(F):
    d = F[:-2] - 2.0 * F[1:-1] + F[2:]
    mad = np.median(np.abs(d - np.median(d, axis=0)), axis=0)
    return mad * 1.4826 / np.sqrt(6.0)


def main():
    rows = []
    print("=" * 78)
    print("denominator check: predicted sigma_f vs observed frame-to-frame scatter")
    print("  sigma_emp is an UPPER bound (curvature inflates it, nothing deflates it)")
    print("=" * 78)
    for stack, name, cls, y0, y1, x0, x1 in CELLS:
        p = os.path.join(CUR, "%s__%s.npz" % (stack, name))
        if not os.path.exists(p):
            continue
        d = np.load(p, allow_pickle=True)
        F, S, lab = d["F"], d["S"], d["lab"]
        band = lab == 0
        Fb = np.ascontiguousarray(F[:, band].astype(np.float64))
        Sb = np.ascontiguousarray(S[:, band].astype(np.float64))
        emp = robust_sigma_from_second_difference(Fb)
        pred = np.median(Sb, axis=0)
        ok = np.isfinite(emp) & np.isfinite(pred) & (pred > 1e-6)
        r = emp[ok] / pred[ok]
        # the noise-only null has a FLAT true curve, so there sigma_emp is not
        # an upper bound but an estimate -- reported alongside, clearly marked
        rn = None
        pn = os.path.join(NUL, "%s__%s.npz" % (stack, name))
        if os.path.exists(pn):
            dn = np.load(pn, allow_pickle=True)
            Fn = np.ascontiguousarray(dn["F"][:, band].astype(np.float64))
            Sn = np.ascontiguousarray(dn["S"][:, band].astype(np.float64))
            en = robust_sigma_from_second_difference(Fn)
            qn = np.median(Sn, axis=0)
            m = np.isfinite(en) & np.isfinite(qn) & (qn > 1e-6)
            rn = float(np.median(en[m] / qn[m]))
        rows.append(dict(stack=stack, cell=name, cls=cls,
                         pred=float(np.median(pred[ok])),
                         emp=float(np.median(emp[ok])),
                         ratio=float(np.median(r)),
                         ratio_null=rn))
        print("  %-16s %-18s %-8s  pred %7.3f DN  emp(upper) %7.3f DN  "
              "ratio %5.2f | null-cube ratio %s"
              % (stack, name, cls, rows[-1]["pred"], rows[-1]["emp"],
                 rows[-1]["ratio"],
                 "%.2f" % rn if rn is not None else "  -- "))
    print()
    for cls in ("occ", "occ_flat", "ctl"):
        v = [x["ratio"] for x in rows if x["cls"] == cls]
        w = [x["ratio_null"] for x in rows if x["cls"] == cls
             and x["ratio_null"] is not None]
        print("  %-9s n=%2d  real-frame ratio median %5.2f (range %5.2f-%5.2f)"
              "   null-cube ratio median %s"
              % (cls, len(v), np.median(v), min(v), max(v),
                 "%5.2f" % np.median(w) if w else " -- "))
    allr = [x["ratio"] for x in rows]
    alln = [x["ratio_null"] for x in rows if x["ratio_null"] is not None]
    print()
    print("  ALL       n=%2d  real-frame ratio median %5.2f (range %5.2f-%5.2f)"
          % (len(allr), np.median(allr), min(allr), max(allr)))
    print("  ALL       n=%2d  null-cube  ratio median %5.2f (range %5.2f-%5.2f)"
          % (len(alln), np.median(alln), min(alln), max(alln)))
    print()
    print("  Reading: a ratio near 1 on the null cube says the MC estimator and")
    print("  the sd it estimates agree.  A ratio above 1 on real frames is the")
    print("  curvature of the real through-focus curve, not a model error, and")
    print("  it bounds the model error from above.")
    with open(os.path.join(DATA, "22-sigmacheck.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote data/22-sigmacheck.json")


if __name__ == "__main__":
    main()
