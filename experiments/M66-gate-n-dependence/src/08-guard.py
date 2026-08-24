"""M66 step 8 - the guard's N-dependence, absolute n_eff (rule 39), and the
cross-stack comparison confound.

Reads out/05-sweep.json only. Adds no new image computation. Produces the three
tables the report needs that 06-blast.py does not emit:

  1. n_eff/N at gate 4.0 against N, every stack, every mode, with M62's
     Requirement G margin 0.95/(n_eff/N) beside it, and the largest N at which
     the guard would have failed.
  2. Absolute mean n_eff beside every gate (rule 39), stride mode.
  3. What a fixed-gate cross-stack comparison costs: the spread of n_eff/N
     across stacks at each stack's OWN N versus at a common N.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from m66 import GATES, OUT, banner  # noqa: E402

C = json.loads((OUT / "05-sweep.json").read_text(encoding="utf-8"))
report = {}
GUARD = 0.95

# ---------------------------------------------------------------- 1. the guard
banner("M62 Requirement G (n_eff/N < 0.95) as a function of N, at gate 4.0")
print(f"  {'stack':<15} {'mode':<8}  " + "".join(f"{'N=' + str(n):>10}" for n in
                                                 (3, 5, 8, 12, 19, 33, 63, 105, 299)))
guard = {}
for s, rec in C.items():
    guard[s] = {"N_max": rec["N_max"], "modes": {}}
    for mode in ("prefix", "stride", "random"):
        row = {}
        cells = ""
        for n in (3, 5, 8, 12, 19, 33, 63, 105, 299):
            k = str(n)
            if k in rec["rows"]:
                v = rec["rows"][k][mode]["4.0"]["n_eff_over_N"]
                row[k] = v
                cells += f"{v:>10.4f}"
            else:
                cells += f"{'-':>10}"
        guard[s]["modes"][mode] = row
        print(f"  {s:<15} {mode:<8}  {cells}")

banner("Largest N at which Requirement G would FAIL (n_eff/N >= 0.95), gate 4.0")
print(f"  {'stack':<15} {'N_max':>6}  {'prefix':>18}  {'stride':>18}  {'random':>18}")
fails = {}
for s, rec in C.items():
    fails[s] = {}
    line = f"  {s:<15} {rec['N_max']:>6}  "
    for mode in ("prefix", "stride", "random"):
        bad = [int(n) for n, r in rec["rows"].items()
               if r[mode]["4.0"]["n_eff_over_N"] >= GUARD]
        fails[s][mode] = max(bad) if bad else None
        line += f"{(str(max(bad)) if bad else 'never'):>18}  "
    print(line)
report["guard_grid"] = guard
report["guard_fail_max_N"] = fails

n19 = {}
for s, rec in C.items():
    ns = [int(n) for n in rec["rows"] if int(n) >= 19]
    worst = max(rec["rows"][str(n)][m]["4.0"]["n_eff_over_N"]
                for n in ns for m in ("prefix", "stride", "random"))
    own = rec["rows"][str(rec["N_max"])]["stride"]["4.0"]["n_eff_over_N"]
    n19[s] = {"worst_N_ge_19": worst, "at_own_N": own,
              "margin_N_ge_19": GUARD / worst, "margin_own_N": GUARD / own}
banner("Requirement G margin, restricted to N >= 19, and at each stack's own N")
print(f"  {'stack':<15} {'worst n_eff/N (N>=19)':>22} {'margin':>9}"
      f" {'at own N':>10} {'margin':>9}")
for s, r in n19.items():
    print(f"  {s:<15} {r['worst_N_ge_19']:>22.5f} {r['margin_N_ge_19']:>8.2f}x"
          f" {r['at_own_N']:>10.5f} {r['margin_own_N']:>8.2f}x")
gw = max(r["worst_N_ge_19"] for r in n19.values())
print(f"\n  worst over the corpus with N >= 19: {gw:.5f}  "
      f"({'guard holds' if gw < GUARD else 'GUARD FAILS'}, margin {GUARD / gw:.2f}x)")
report["guard_N_ge_19"] = n19

# ------------------------------------------------- 2. absolute n_eff (rule 39)
banner("Rule 39 - absolute mean n_eff beside every gate, stride mode")
print(f"  {'stack':<15} {'N':>5}  " + "".join(f"{'T=' + str(g):>11}" for g in GATES))
neff = {}
for s, rec in C.items():
    neff[s] = {}
    for n in sorted(int(k) for k in rec["rows"]):
        vals = {str(g): rec["rows"][str(n)]["stride"][str(g)]["mean_n_eff"] for g in GATES}
        neff[s][str(n)] = vals
        if n in (19, rec["N_max"]) or n == 105:
            print(f"  {s:<15} {n:>5}  " + "".join(f"{vals[str(g)]:>11.4f}" for g in GATES))
report["n_eff_stride"] = neff

# ------------------------------------------- 3. the cross-stack comparison cost
banner("Cross-stack comparison at a fixed gate: own N versus common N")
for g in (1.0, 2.0, 4.0):
    own, com = {}, {}
    for s, rec in C.items():
        own[s] = rec["rows"][str(rec["N_max"])]["stride"][str(g)]["n_eff_over_N"]
        com[s] = rec["rows"]["19"]["stride"][str(g)]["n_eff_over_N"]
    so = max(own.values()) / min(own.values())
    sc = max(com.values()) / min(com.values())
    print(f"\n  gate {g}:  spread across the 8 stacks at each stack's OWN N = {so:.3f}x")
    print(f"            spread across the same 8 stacks all at N = 19      = {sc:.3f}x")
    print(f"            {'  stack':<17}{'own N':>8}{'n_eff/N own':>14}{'n_eff/N @19':>14}"
          f"{'ratio':>9}")
    for s in own:
        print(f"            {s:<17}{C[s]['N_max']:>8}{own[s]:>14.5f}{com[s]:>14.5f}"
              f"{own[s] / com[s]:>9.3f}")
    report.setdefault("cross_stack", {})[str(g)] = {
        "own": own, "at_19": com, "spread_own": so, "spread_common": sc}

# ------------------------------------- 4. between-subset SD as the SE (rule 39)
banner("Between-subset SD of mean n_eff over random-draw repeats (the SE)")
print(f"  {'stack':<15} {'N':>5}  {'mean n_eff (T=4)':>17}  {'SD over reps':>13}"
      f"  {'reps':>5}  {'SD/mean':>9}")
se = {}
for s, rec in C.items():
    for n in sorted(int(k) for k in rec["rows"]):
        r = rec["rows"][str(n)]["random"]["4.0"]
        if r["reps"] > 1:
            se.setdefault(s, {})[str(n)] = {"mean": r["mean_n_eff"], "sd": r["sd_over_reps"],
                                            "reps": r["reps"]}
            if n in (19, 63, 105):
                print(f"  {s:<15} {n:>5}  {r['mean_n_eff']:>17.4f}  {r['sd_over_reps']:>13.5f}"
                      f"  {r['reps']:>5}  {r['sd_over_reps'] / r['mean_n_eff']:>9.5f}")
report["se_random"] = se
worst_cv = max(v["sd"] / v["mean"] for d in se.values() for v in d.values())
print(f"\n  worst SD/mean over every (stack, N) with reps > 1: {worst_cv:.5f}")
print(f"  Every span reported in 06-blast.py exceeds this by orders of magnitude,")
print(f"  so subset-draw noise cannot produce them.")
report["worst_cv"] = worst_cv

p = OUT / "08-guard.json"
p.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {p}")
