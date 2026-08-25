#!/usr/bin/env python3
"""M125 - robustness diagnostics ADDED AFTER the registered score was read.

These are declared post-hoc and every one of them can only WEAKEN the
conclusion, never strengthen it: each asks "does the pass survive X?".  None
can turn a fail into a pass.  They exist because the registered run showed two
warning signs that a pre-registration written before seeing any fold could not
have anticipated:

  1. the per-fold thresholds are BIMODAL (1.839 in twelve folds, 8.454 in two),
     which is the signature of a nearly flat training objective, and
  2. acceptance criterion C4 passed at exactly its bar, 12/14.

Diagnostics run here:
  D1  training-objective profile - how flat is the surface T* was chosen from?
  D2  drop-one-subject jackknife of the CONCLUSION - re-run the whole LOO on
      each 13-stack corpus and ask whether C1 still holds.  This is NOT the
      leave-one-out scoring; it is leave-one-out applied to the verdict.
  D3  how much of the margin is a single stack?
  D4  threshold sensitivity - does a hand-rounded shippable constant score as
      well as the fitted one?
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loo import load, score_all, fit, candidates, loss, SEED

M122 = r"C:\dev\strehl-out\M122"
OUT = r"C:\dev\strehl-out\M125"

rows = load(M122)
stacks = [r["stack"] for r in rows]
drift = np.array([r["Dpp"] for r in rows])
b12n = np.array([r["B12n"] for r in rows])
n = len(rows)
base = score_all(drift, b12n)

print("=" * 74)
print("D1  TRAINING-OBJECTIVE PROFILE (full data) - is T* a real minimum?")
print("=" * 74)
cands = candidates(drift)
prof = [(T, loss(drift, b12n, T).mean()) for T in cands]
best = min(p[1] for p in prof)
print(f"{'T':>10}  {'mean training loss':>18}  {'excess over best':>16}  ON")
for T, s in prof:
    on = int((drift >= T).sum())
    tag = "  <-- T* selected" if T == base["T_full"] else ""
    print(f"{T:>10.4f}  {s:>18.6f}  {s-best:>16.6f}  {on:>2}{tag}")
flat = [T for T, s in prof if s - best < 0.001 and np.isfinite(T)]
print(f"\n  thresholds within 0.001 of the best: {len(flat)} of {len(prof)}"
      f"  -> range [{min(flat):.3f}, {max(flat):.3f}]")
print("  A wide flat range means the corpus does not pin T down; the shipped")
print("  constant is one of many that score alike, and C5's 0.374 pp gap")
print("  describes only the LOCAL spacing, not the confidence in T*.")

print()
print("=" * 74)
print("D2  DROP-ONE-SUBJECT JACKKNIFE OF THE CONCLUSION")
print("=" * 74)
print("Re-run the entire LOO procedure on each 13-stack corpus and ask")
print("whether C1 (S_auto < S_on and < S_off) still holds.\n")
print(f"{'dropped':<26}{'S_auto':>10}{'S_on':>10}{'margin':>10}{'T*':>9}  C1")
survivors = 0
jack = {}
for i in range(n):
    m = np.ones(n, bool); m[i] = False
    r = score_all(drift[m], b12n[m])
    c1 = r["S_auto"] < r["S_on"] - 1e-12 and r["S_auto"] < 1.0 - 1e-12
    survivors += c1
    jack[stacks[i]] = {"S_auto": r["S_auto"], "S_on": r["S_on"],
                       "margin": r["S_on"] - r["S_auto"], "C1": bool(c1)}
    print(f"{stacks[i]:<26}{r['S_auto']:>10.6f}{r['S_on']:>10.6f}"
          f"{r['S_on']-r['S_auto']:>+10.6f}{r['T_full']:>9.3f}  "
          f"{'pass' if c1 else 'FAIL'}")
print(f"\n  C1 survives {survivors}/{n} single-subject deletions")

print()
print("=" * 74)
print("D3  HOW MUCH OF THE MARGIN IS ONE STACK?")
print("=" * 74)
margin = base["S_on"] - base["S_auto"]
print(f"  held-out margin over ALWAYS-ON        {margin:+.6f}")
for s in ("bee-3-cpl", "tweezers-cpl"):
    j = stacks.index(s)
    contrib = (b12n[j] - (b12n[j] if base["held_on"][j] else 1.0)) / n
    print(f"  contribution of {s:<22} {-contrib:+.6f}"
          f"   (B12n {b12n[j]:.4f}, held-out "
          f"{'ON' if base['held_on'][j] else 'OFF'})")
print("\n  The rule's entire advantage over ALWAYS-ON is the harm it avoids on")
print("  the stacks it declines. If that is one stack, the margin rests on")
print("  n = 1 and must be reported that way.")

print()
print("=" * 74)
print("D4  SHIPPABLE ROUNDED CONSTANT")
print("=" * 74)
print(f"  fitted T* = {base['T_full']:.4f} %")
for T in (1.5, 1.75, 1.8, 2.0, 2.5, 3.0, 4.0, 5.0):
    l = loss(drift, b12n, T)
    on = int((drift >= T).sum())
    print(f"  T = {T:4.2f} %  in-sample mean loss {l.mean():.6f}  ON {on:>2}/14")
print("\n  (in-sample, shown only to choose a human-readable constant inside")
print("   the flat region; it is NOT a result and does not re-open selection)")

json.dump({"profile": [[float(T), float(s)] for T, s in prof],
           "flat_range": [float(min(flat)), float(max(flat))],
           "jackknife": jack, "jackknife_survivors": int(survivors),
           "margin": float(margin)},
          open(os.path.join(OUT, "robust.json"), "w"), indent=1)
print(f"\nwrote {os.path.join(OUT, 'robust.json')}")

print()
print("=" * 74)
print("D5  SAMPLE SIZE - registered procedure, run despite the pass")
print("=" * 74)
print("PREREGISTRATION section 6.2 registered this for the NO-SHIP branch. It is")
print("run anyway because D2/D3 changed the live question from 'does the rule")
print("beat ALWAYS-ON' to 'how many subjects until the margin stops resting on")
print("one'. Registered limitation, restated: resampling 14 stacks cannot")
print("manufacture new SUBJECTS, so this bounds the precision limb only and is")
print("an OPTIMISTIC FLOOR on the true requirement.\n")
rng2 = np.random.default_rng(SEED + 1)
boot = {}
TRIALS = 500
# The drop-one column is O(m^2) LOO fits per trial, so it is measured on fewer
# trials and up to m=50. Reported honestly as a smaller sample rather than
# quietly dropped.
ROBUST_TRIALS = 60
ROBUST_MAX_M = 50
print(f"{'m':>6}{'C1 satisfied':>16}{'C1 survives drop-one':>24}")
for m in (14, 20, 30, 50, 80, 120):
    wins = 0
    for _ in range(TRIALS):
        idx = rng2.integers(0, n, size=m)
        rb = score_all(drift[idx], b12n[idx])
        wins += rb["S_auto"] < rb["S_on"] - 1e-12 and rb["S_auto"] < 1.0 - 1e-12
    robust = None
    if m <= ROBUST_MAX_M:
        rob = 0
        for _ in range(ROBUST_TRIALS):
            idx = rng2.integers(0, n, size=m)
            d_, b_ = drift[idx], b12n[idx]
            rb = score_all(d_, b_)
            if not (rb["S_auto"] < rb["S_on"] - 1e-12 and rb["S_auto"] < 1.0 - 1e-12):
                continue
            surv = True
            for j in range(m):
                k = np.ones(m, bool); k[j] = False
                rj = score_all(d_[k], b_[k])
                if not (rj["S_auto"] < rj["S_on"] - 1e-12 and rj["S_auto"] < 1.0 - 1e-12):
                    surv = False
                    break
            rob += surv
        robust = rob / ROBUST_TRIALS
    boot[m] = (wins / TRIALS, robust)
    rtxt = f"{robust*100:.1f}% (n={ROBUST_TRIALS})" if robust is not None else "not measured"
    print(f"{m:>6}{wins/TRIALS*100:>15.1f}%{rtxt:>24}")

need = next((m for m in boot if boot[m][0] >= 0.80), None)
need_r = next((m for m in boot if boot[m][1] is not None and boot[m][1] >= 0.80), None)
print(f"\n  smallest m with >= 80% satisfying C1            : "
      f"{need if need else '> 120'}")
print(f"  smallest m with >= 80% ALSO surviving drop-one  : "
      f"{need_r if need_r else f'> {ROBUST_MAX_M} (not reached in the measured range)'}")
print("  The second column is the number that matters for moving the default.")

json.dump({"profile": [[float(T), float(s)] for T, s in prof],
           "flat_range": [float(min(flat)), float(max(flat))],
           "jackknife": jack, "jackknife_survivors": int(survivors),
           "margin": float(margin),
           "bootstrap": {str(k): [float(v[0]),
                                  (float(v[1]) if v[1] is not None else None)]
                         for k, v in boot.items()},
           "bootstrap_trials": TRIALS, "robust_trials": ROBUST_TRIALS,
           "need_C1": need, "need_robust": need_r},
          open(os.path.join(OUT, "robust.json"), "w"), indent=1)
print(f"\nwrote {os.path.join(OUT, 'robust.json')}")
