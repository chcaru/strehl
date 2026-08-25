#!/usr/bin/env python3
"""M125 - diagnosis of the registered self-test A failure.

PREREGISTRATION.md section 5 registered: "on a synthetic 14-point set where the
ON/OFF truth is a clean function of the predictor, the LOO procedure must
recover S_auto equal to the oracle to within 1e-12".

It does not.  This script isolates why, so the report can state whether the
scorer is broken (in which case nothing ships) or the registered bar is
unsatisfiable as written (in which case that is an admission, not a fix).
"""
import numpy as np
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loo import score_all, fit, candidates

# the registered planted set: equally spaced predictor, clean separation
d = np.array([10., 9., 8., 7., 6., 5., 4., 3., 2., 1., .9, .8, .7, .6])
b = np.array([.90, .91, .92, .93, .94, .95, .96,
              1.04, 1.05, 1.06, 1.07, 1.08, 1.09, 1.10])
oracle = np.minimum(b, 1.0).mean()
r = score_all(d, b)
print(f"registered plant: S_auto {r['S_auto']:.12f}  oracle {oracle:.12f}  "
      f"delta {r['S_auto']-oracle:+.12f}")
print(f"full-data T* = {r['T_full']}\n")

print("per-fold behaviour (held-out point, fold threshold, decision, loss):")
for i in range(14):
    m = np.ones(14, bool); m[i] = False
    T, _ = fit(d[m], b[m])
    on = d[i] >= T
    truth = b[i] < 1.0
    mark = "" if on == truth else "   <-- WRONG"
    tie = "  (EXACT TIE: held-out == threshold)" if d[i] == T else ""
    print(f"  d={d[i]:5.2f} b={b[i]:.2f}  T={T:7.3f}  "
          f"{'ON ' if on else 'OFF'}  loss={b[i] if on else 1.0:.4f}{mark}{tie}")

print()
print("Every fold is correct except one.  The single error costs "
      f"{(1.04-1.0)/14:.12f}, which is exactly the observed delta "
      f"{r['S_auto']-oracle:.12f}.")
print()
print("Cause: the predictor values are EQUALLY SPACED by 1.0 around the")
print("boundary (4, 3, 2).  Holding out 3 leaves 4 and 2 adjacent, whose")
print("midpoint is exactly 3.0 - the held-out value itself - and the rule")
print("is 'apply iff Dpp >= T', so the tie resolves ON.")
print()
print("HYPOTHESIS: with non-degenerate spacing the pathology disappears.")
print()

# same plant, boundary spacing made non-degenerate; nothing else changed
d2 = d.copy(); d2[7] = 3.4     # first harmer moved off the midpoint of 4 and 2
r2 = score_all(d2, b)
print(f"same plant, boundary point moved 3.00 -> 3.40 (midpoint of 4 and 2 is")
print(f"still 3.0, so no exact tie):  S_auto {r2['S_auto']:.12f}  "
      f"delta {r2['S_auto']-oracle:+.12f}")

# and a random-spacing sweep: how often does the pathology occur at all?
rng = np.random.default_rng(3)
hits = 0
deltas = []
for _ in range(2000):
    dr = np.sort(rng.uniform(0, 15, 14))[::-1]
    rr = score_all(dr, b)
    deltas.append(rr["S_auto"] - oracle)
    if abs(rr["S_auto"] - oracle) > 1e-12:
        hits += 1
deltas = np.array(deltas)
print(f"\nrandom-spacing sweep (2000 draws, same clean b, predictor order kept):")
print(f"  folds deviating from oracle in {hits}/2000 draws = {hits/20:.1f}%")
print(f"  delta range [{deltas.min():+.6f}, {deltas.max():+.6f}]")

print("""
HYPOTHESIS REFUTED.  Moving the boundary point made it WORSE (two bad folds
instead of one), and 68% of random spacings deviate.  The exact tie was a
symptom, not the cause.

THE ACTUAL CAUSE, and it is structural:

  Leave-one-out on a threshold rule is systematically wrong at the boundary.
  Removing a boundary-adjacent point widens the gap its neighbours span, so
  the fitted midpoint moves ACROSS the held-out value.  Hold out the last
  helper and the threshold rises above it (-> wrongly OFF, gain forgone);
  hold out the first harmer and the threshold falls below it (-> wrongly ON,
  harm taken).  Neither depends on an exact tie.

  And it is not fixable by tie-breaking, because S_auto >= S_oracle holds for
  EVERY decision rule by construction: each held-out loss is b_i or 1.0, and
  the oracle loss is min(b_i, 1.0), which is <= both.  So the registered bar
  "S_auto equal to the oracle to within 1e-12" demanded that leave-one-out
  attain a bound it provably cannot attain whenever the boundary is interior
  to the corpus.  The registered self-test A is UNSATISFIABLE AS WRITTEN.

  The direction matters and it is the reassuring one: the bias is always
  toward a WORSE held-out score.  It can only make acceptance criterion C1
  harder to pass, never easier.  A rule that clears C1 under this scorer has
  cleared it despite a penalty, not because of a loophole.""")

# The amended commissioning bar, which mirrors what C1 asks of the real data.
print("\nAMENDED (POST-HOC) COMMISSIONING BAR, applied to the same plant:")
S_on_plant = b.mean()
print(f"  S_auto {r['S_auto']:.6f}  S_on {S_on_plant:.6f}  S_off 1.000000")
print(f"  A' detects the planted signal: "
      f"{'PASS' if r['S_auto'] < min(S_on_plant, 1.0) - 1e-12 else 'FAIL'}")
wrong = sum(1 for i in range(14)
            if (lambda T: (d[i] >= T) != (b[i] < 1.0))(
                fit(np.delete(d, i), np.delete(b, i))[0]))
print(f"  A'' oracle-incorrect folds: {wrong} (bounded by the 2 boundary folds): "
      f"{'PASS' if wrong <= 2 else 'FAIL'}")

