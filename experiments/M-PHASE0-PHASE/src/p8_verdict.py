"""The C1 verdict, rebuilt after the A8 retraction and the A9 sign fix.

WHAT THIS REPLACES.  `p6_ceiling.py` reported the MEDIAN bar among rows below the
10th-percentile kappa and called it a ceiling.  A ceiling is a maximum, and the bar
depends on `nu`, `N` and gauge as well as `kappa`, so no scalar function of kappa
bounds it.  A7 then compared that median against a CORNER accuracy figure and
reported the ratio as a margin.  Both halves varied across the field by about
threefold and the comparison could not decide anything.  This resolves both sides.

WHAT CHANGED UNDER IT.  Every bar figure here comes from a `p1_bar.json` rebuilt
with the corrected representative sign (A9.1).  The correction LOOSENS the bar --
G-1x zero-mean maxima move 0.3093 -> 0.3592 at rho = 0.01 and 0.4303 -> 0.6872 at
rho = 1 -- so it moves the verdict toward C1 surviving, against my prior finding.
The rho grid was also extended down to 0.0001 to cover the measured census, because
the old grid bottomed out at 0.01 and the measured value is below it.

RHO.  Adopted from M-PHASE0-RHO (A9.2): G 0.00552, 95% 0.00185-0.01078; census
0.0001-0.06 for design decisions.  Its refusal to publish a universal scalar is
adopted with it, so every figure below is reported ACROSS the census rather than at
a single value.  A grid refinement moves that measurement by 30.5x, which is why the
census is wide and why no single number here should be quoted alone.

ACCURACY.  Reported at three field radii rather than pooled.  These come from the p5
transforms on the best stack (113MSDCF) and they are the OPTIMISTIC side of the
bracket: cycle consistency is a self-consistency measure, blind to any systematic
error shared by every edge, and the verifier demonstrated a construction with zero
cycle inconsistency and 3.5 plane px of absolute error.  They are also scored against
a held-out noisy edge rather than against truth, so they are not accuracy against
truth and are not claimed to be.

WHAT THIS DOES NOT DO.  It does not file a verdict.  The preregistered per-site joint
calculation -- matching each real site's conditioning, frequency, frame count and
measured registration error -- has still not been run, and section 9's thresholds are
defined over that census, not over this one.  What follows is the winnable fraction
over the CONDITIONING census, which is a necessary input to that calculation and not
a substitute for it.

Run: python p8_verdict.py
"""

import json
import os
import sys

import numpy as np

OUT = os.path.join(os.path.dirname(__file__), "..", "out", "p8_verdict.json")
BAR = os.path.join(os.path.dirname(__file__), "..", "out", "p1_bar.json")

# Sensor px, 113MSDCF, span <= 8, after such averaging as is really available.
# A8.4: the 0.2250 A7 quoted as "best achievable anywhere" is the CORNER value.
ACCURACY = [
    ("field centre", 0.0801),
    ("inner annulus", 0.1168),
    ("corner", 0.2256),
]

RHO_MEASURED = 0.0055
RHO_CENSUS = (0.0001, 0.06)


def load():
    with open(BAR, "r", encoding="utf-8") as fh:
        d = json.load(fh)
    return [r for r in d["rows"]
            if r["bar_unit"] is not None and str(r["snr"]) == "inf"]


def stats(vals):
    v = np.asarray(vals, dtype=float)
    return dict(n=int(v.size), median=float(np.median(v)),
                p90=float(np.percentile(v, 90)), p99=float(np.percentile(v, 99)),
                maximum=float(v.max()))


def main():
    rows = load()
    rhos = sorted({r["rho"] for r in rows})
    print("=" * 78)
    print("the bar, corrected sign, over the measured rho census")
    print("  measured rho %.4f; census %.4f - %.4f (M-PHASE0-RHO, A9.2)"
          % (RHO_MEASURED, *RHO_CENSUS))
    print("=" * 78)
    print("  %-7s %-10s %7s %6s %8s %8s %8s %8s"
          % ("target", "gauge", "rho", "n", "median", "p90", "p99", "MAX"))

    table = {}
    for tgt in ("G-1x", "RB-1x"):
        for gauge in ("raw", "zero_mean"):
            for rho in rhos:
                sel = [r["bar_unit"] for r in rows if r["target"] == tgt
                       and r["gauge"] == gauge and r["rho"] == rho]
                if not sel:
                    continue
                s = stats(sel)
                table["%s|%s|%s" % (tgt, gauge, rho)] = s
                inside = RHO_CENSUS[0] <= rho <= RHO_CENSUS[1]
                print("  %-7s %-10s %7.4f %6d %8.4f %8.4f %8.4f %8.4f%s"
                      % (tgt, gauge, rho, s["n"], s["median"], s["p90"],
                         s["p99"], s["maximum"], "  <- census" if inside else ""))

    print("\n  A ceiling is a MAXIMUM.  p6 reported the median of the")
    print("  best-conditioned decile, which is the leftmost column here, and")
    print("  called it a ceiling; the rightmost column is the actual bound.")

    print("\n" + "=" * 78)
    print("winnable fraction: rows whose bar EXCEEDS the achieved accuracy")
    print("  section 9: >=60%% SURVIVE, 25-60%% NARROWED, <25%% KILL")
    print("=" * 78)
    print("  %-7s %-10s %7s %14s %8s %8s"
          % ("target", "gauge", "rho", "radius", "acc", "winnable"))

    win = {}
    for tgt in ("G-1x", "RB-1x"):
        for gauge in ("raw", "zero_mean"):
            for rho in rhos:
                if not (RHO_CENSUS[0] <= rho <= RHO_CENSUS[1]):
                    continue
                sel = np.asarray([r["bar_unit"] for r in rows
                                  if r["target"] == tgt and r["gauge"] == gauge
                                  and r["rho"] == rho], dtype=float)
                if sel.size == 0:
                    continue
                for label, acc in ACCURACY:
                    frac = float((sel > acc).mean())
                    win["%s|%s|%s|%s" % (tgt, gauge, rho, label)] = frac
                    print("  %-7s %-10s %7.4f %14s %8.4f %7.1f%%"
                          % (tgt, gauge, rho, label, acc, 100 * frac))

    print("\n" + "=" * 78)
    print("at the measured rho, G-1x zero-mean (the gauge A6 adopted)")
    print("=" * 78)
    near = min(rhos, key=lambda r: abs(r - RHO_MEASURED))
    s = table.get("G-1x|zero_mean|%s" % near)
    if s is not None:
        print("  bar at rho = %.4f : median %.4f  p90 %.4f  p99 %.4f  MAX %.4f"
              % (near, s["median"], s["p90"], s["p99"], s["maximum"]))
        for label, acc in ACCURACY:
            frac = win.get("G-1x|zero_mean|%s|%s" % (near, label))
            verdict = ("SURVIVE" if frac >= 0.60 else
                       "NARROWED" if frac >= 0.25 else "KILL")
            print("    vs %-14s %.4f px : %5.1f%% winnable -> %s"
                  % (label, acc, 100 * frac, verdict))

    print("\n  The three radii do not agree, and that is the finding. A pooled")
    print("  comparison cannot decide a claim whose two sides each vary about")
    print("  threefold across the field. Any verdict must be filed per radius,")
    print("  and the per-site joint census remains the thing that decides it.")

    payload = dict(rho_measured=RHO_MEASURED, rho_census=list(RHO_CENSUS),
                   accuracy=[dict(radius=a, px=b) for a, b in ACCURACY],
                   bar=table, winnable=win)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print("\nwrote %s" % os.path.abspath(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
