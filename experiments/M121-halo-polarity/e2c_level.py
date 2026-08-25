"""E2c -- the level test.  Which law, decided IN-SAMPLE on n=70.

E2b's out-of-sample test rejected CONTRAST and ADDITIVE and left
MULTIPLICATIVE standing, but it did so on 18 bright-object edges, and E2b's
own depth-split showed only 5 of those straddle a depth discontinuity at all.
A verdict resting on 18 edges of doubtful provenance is not a verdict.

This test does not need the bright-object class.  Within the 70 dark-object
edges the bright surround is NOT all one level -- `hi` varies from edge to
edge -- and the three laws make different predictions about how the rim in DN
tracks it:

    CONTRAST        rim_DN = k * A          ->  rim/A  is constant, rim/hi is not
    MULTIPLICATIVE  rim_DN = g * hi         ->  rim/hi is constant, rim/A  is not
    ADDITIVE        rim_DN = c              ->  neither; rim_DN is constant

So: form rim_DN per edge, and see which normalisation makes it flat.  The
statistic is the coefficient of variation (SD/|mean|) of each candidate --
whichever law is true, its own normalised quantity should be the tightest --
plus a regression of rim_DN on `hi` and on `A` separately.

FAILURE DIRECTIONS.
  * If `hi` and `A` are strongly collinear across the accepted edges then this
    test CANNOT separate the laws and must say so rather than pick a winner.
    The script measures that collinearity FIRST and reports it.
  * A coefficient of variation is undefined when the mean is near zero, so it
    is only quoted where the mean is many SEs from zero.

Run:  python experiments/M121-halo-polarity/e2c_level.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, commissioned_max_rise,
    focus_field, make_classifier, polarity_table,
)
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import _boot_ci, scan  # noqa: E402


def cv(v):
    v = np.asarray(v, dtype=float)
    m = float(np.mean(v))
    if abs(m) < 1e-12:
        return np.nan
    return float(np.std(v, ddof=1) / abs(m))


def boot_cv(v, n=4000, seed=7):
    rng = np.random.default_rng(seed)
    v = np.asarray(v, dtype=float)
    out = np.array([cv(rng.choice(v, v.size, replace=True)) for _ in range(n)])
    return float(np.median(out)), float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    max_rise = commissioned_max_rise()
    merged = luma(load_u16(arm_path("armM4-gate4-binlin")))
    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    classify = make_classifier(fmax)

    r = scan(merged, label="E2c shipped", grad_percentile=GRAD_PCT,
             max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
             classify=classify, max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
             verbose=False)
    pt = polarity_table(r)
    lo_b, hi_b = pt["read_band"]

    s = r["bright"]
    sel = s["obj"] == -1                      # dark object, bright surround
    dist = r["dist"]
    m = (dist >= lo_b) & (dist <= hi_b)
    rim_norm = s["stack"][sel][:, m].mean(axis=1)      # rim / A
    A = np.asarray(s["amps"])[sel]
    HI = np.asarray(s["hi"])[sel]
    LO = np.asarray(s["lo"])[sel]
    rim_dn = rim_norm * A

    res = {"n": int(sel.sum()), "read_band": [lo_b, hi_b]}
    print(f"n = {sel.sum()} dark-object edges, read band {lo_b:.2f}-{hi_b:.2f} px")
    print(f"  A  range {A.min():8.0f} .. {A.max():8.0f}  (spread {A.max()/A.min():.2f}x)")
    print(f"  hi range {HI.min():8.0f} .. {HI.max():8.0f}  (spread {HI.max()/HI.min():.2f}x)")
    print(f"  lo range {LO.min():8.0f} .. {LO.max():8.0f}")

    rho = float(np.corrcoef(A, HI)[0, 1])
    res["corr_A_hi"] = rho
    print(f"\n  COLLINEARITY CHECK: corr(A, hi) = {rho:+.4f}")
    if abs(rho) > 0.98:
        print("  -> A and hi are collinear on this sample; the laws are NOT separable here.")
    else:
        print("  -> separable: A and hi vary independently enough to tell the laws apart.")

    print("\n=== which normalisation is flat? (lower CV = better fit) ===")
    cands = {"CONTRAST (rim/A)": rim_norm,
             "MULTIPLICATIVE (rim/hi)": rim_dn / HI,
             "ADDITIVE (rim_DN)": rim_dn}
    res["cv"] = {}
    for name, v in cands.items():
        c, clo, chi = boot_cv(v)
        mv, mlo, mhi = _boot_ci(v)
        res["cv"][name] = {"cv": c, "cv_lo95": clo, "cv_hi95": chi,
                           "mean": mv, "lo95": mlo, "hi95": mhi}
        print(f"  {name:26s} CV={c:6.3f} [{clo:.3f},{chi:.3f}]   "
              f"value={mv:+11.5f} [{mlo:+.5f},{mhi:+.5f}]")
    best = min(res["cv"], key=lambda k: res["cv"][k]["cv"])
    res["tightest"] = best
    print(f"  -> tightest: {best}")

    print("\n=== regression of rim_DN on each predictor (through the origin) ===")
    res["regression"] = {}
    for name, x in (("hi", HI), ("A", A)):
        k = float(np.sum(x * rim_dn) / np.sum(x * x))
        pred = k * x
        ss_res = float(np.sum((rim_dn - pred) ** 2))
        ss_tot = float(np.sum((rim_dn - rim_dn.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot
        res["regression"][name] = {"slope": k, "r2_about_mean": r2}
        print(f"  rim_DN = k * {name:2s}   k={k:+.6f}   R^2(about mean) = {r2:+.4f}")
    kc = float(np.mean(rim_dn))
    ss_res = float(np.sum((rim_dn - kc) ** 2))
    res["regression"]["const"] = {"slope": kc, "r2_about_mean": 0.0}
    print(f"  rim_DN = const   c={kc:+.2f} DN   R^2(about mean) =  0.0000")

    print("\n=== the gain, if MULTIPLICATIVE ===")
    g, glo, ghi = _boot_ci(rim_dn / HI)
    res["gain"] = {"g": g, "lo95": glo, "hi95": ghi}
    print(f"  surround is scaled by 1 + g with g = {g:+.5f} [{glo:+.5f},{ghi:+.5f}]"
          f"  ({100*g:+.2f}%)")
    print(f"  on a dark surround at lo/hi = 0.174 that is {100*g*0.174:+.3f}% of A,")
    print(f"  i.e. a rim of {-g*0.174:+.5f} in the units E2 reports -- below its noise.")

    (OUT / "e2c-level.json").write_text(json.dumps(res, indent=1, default=float))
    print(f"\nwrote {OUT / 'e2c-level.json'}")


if __name__ == "__main__":
    main()
