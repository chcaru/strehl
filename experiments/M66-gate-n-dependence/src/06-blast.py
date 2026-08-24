"""M66 step 6 - the pre-registered criteria, and the blast radius.

Reads out/00-analytic.json (arm A), out/04-burst.json (arm B),
out/05-sweep.json (arm C) and out/07-response-sd.json (K7). Computes nothing
new from image data; it decides the criteria written in PREREGISTRATION.md
section 5 and prices what they touch.
"""

import json
import pathlib
import sys

import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.stats import norm

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from m66 import CORPUS_N, GATES, OUT, banner  # noqa: E402

SQRT2 = float(np.sqrt(2.0))
S_CRIT = 1.05


def f_N(n, t):
    if n == 1:
        return 1.0
    v, _ = quad(
        lambda x: norm.pdf(x) * np.exp((n - 1) * norm.logcdf(x + t)),
        -np.inf, np.inf, limit=400, epsabs=1e-13, epsrel=1e-13,
    )
    return float(v)


def t_for(n, target):
    return float(brentq(lambda t: f_N(n, t) - target, 0.0, 80.0, xtol=1e-10, rtol=1e-12))


A = json.loads((OUT / "00-analytic.json").read_text(encoding="utf-8"))
B = json.loads((OUT / "04-burst.json").read_text(encoding="utf-8"))
C = json.loads((OUT / "05-sweep.json").read_text(encoding="utf-8"))
K7 = json.loads((OUT / "07-response-sd.json").read_text(encoding="utf-8"))
report = {}


def span(vals):
    """max/min ratio and the sign of the endpoint change, over an N-ordered list."""
    v = [x for x in vals if x > 0]
    if len(v) < 2:
        return float("nan"), 0
    lo, hi = min(v), max(v)
    return hi / lo, int(np.sign(v[-1] - v[0]))


# ---------------------------------------------------------------- K6 (power)
banner("K6 - does arm B (real operator, real scene, H0) reproduce arm A (iid null)?")
rho = K7["rows"]["REAL"]["rho"]
print(f"  K7 measured response SD ratios: FLAT {K7['rows']['FLAT']['rho']:.4f}   "
      f"SMOOTH {K7['rows']['SMOOTH']['rho']:.4f}   REAL {K7['rows']['REAL']['rho']:.4f}")
print(f"  arm B's plant is REAL, so its tolerance in units of the response's OWN")
print(f"  temporal SD is T*sqrt(2)/rho, not T*sqrt(2).\n")
print(f"  {'N':>5} {'gate':>5}  {'arm B':>9}  {'arm A raw':>10}  {'arm A /rho':>11}"
      f"  {'B-A raw':>9}  {'B-A /rho':>9}")
k6 = {}
brows = B["seeds"]["0"]["rows"]
for g in (0.5, 1.0, 2.0, 4.0, 8.0):
    for n in (19, 105, 299):
        b = brows[str(n)]["stride"][str(g)]["n_eff_over_N"]
        a_raw = f_N(n, g * SQRT2)
        a_rho = f_N(n, g * SQRT2 / rho)
        k6[f"{n}-{g}"] = {"armB": b, "armA_raw": a_raw, "armA_rho": a_rho}
        print(f"  {n:>5} {g:>5}  {b:>9.6f}  {a_raw:>10.6f}  {a_rho:>11.6f}"
              f"  {b - a_raw:>+9.6f}  {b - a_rho:>+9.6f}")
sB, _ = span([brows[str(n)]["stride"]["4.0"]["n_eff_over_N"] for n in CORPUS_N])
print(f"\n  arm B span at gate 4.0 over corpus N [19..299]: S_null = {sB:.4f}"
      f"   (K6 needs >= {S_CRIT} somewhere on the ladder for the instrument to have power)")
best_power = max(
    span([brows[str(n)]["stride"][str(g)]["n_eff_over_N"] for n in CORPUS_N])[0]
    for g in GATES[1:]
)
print(f"  arm B best span over the whole ladder: {best_power:.4f}")
k6_pass = best_power >= S_CRIT
print(f"  K6 {'PASS' if k6_pass else 'NOT MET'}")
report["K6"] = {"rho": rho, "rows": k6, "armB_span_g4": sB,
                "armB_best_span": best_power, "pass": bool(k6_pass)}

# ---------------------------------------------------- arm A / B spans by gate
banner("The mechanism by gate - span of the admitted fraction over corpus N [19..299]")
print(f"  {'gate':>6}  {'arm A f_N span':>15}  {'arm B span':>12}  "
      f"{'arm A f(19)':>12}  {'arm A f(299)':>13}  {'arm B f(19)':>12}  {'arm B f(299)':>13}")
by_gate = {}
for g in GATES:
    a = [A["rows"][str(n)][str(g)]["frac"] for n in CORPUS_N]
    b = [brows[str(n)]["stride"][str(g)]["n_eff_over_N"] for n in CORPUS_N]
    sa, _ = span(a)
    sb, _ = span(b)
    by_gate[str(g)] = {"armA_span": sa, "armB_span": sb,
                       "armA_19": a[0], "armA_299": a[-1],
                       "armB_19": b[0], "armB_299": b[-1]}
    print(f"  {g:>6}  {sa:>15.4f}  {sb:>12.4f}  {a[0]:>12.6f}  {a[-1]:>13.6f}"
          f"  {b[0]:>12.6f}  {b[-1]:>13.6f}")
report["by_gate"] = by_gate

# --------------------------------------------------------------- arm C spans
banner("Arm C - span of n_eff/N over N >= 19, per stack, per mode, per gate")
armc = {}
for s, rec in C.items():
    ns = sorted(int(k) for k in rec["rows"] if int(k) >= 19)
    armc[s] = {"N_max": rec["N_max"], "N_used": ns, "modes": {}}
    for mode in ("prefix", "stride", "random"):
        armc[s]["modes"][mode] = {}
        for g in GATES:
            vals = [rec["rows"][str(n)][mode][str(g)]["n_eff_over_N"] for n in ns]
            sp, sgn = span(vals)
            armc[s]["modes"][mode][str(g)] = {
                "span": sp, "sign": sgn, "first": vals[0], "last": vals[-1],
                "N_first": ns[0], "N_last": ns[-1],
                "sd_over_reps_first": rec["rows"][str(ns[0])][mode][str(g)]["sd_over_reps"],
            }
print(f"  {'stack':<15} {'N range':>10}  {'mode':<8}  " +
      "".join(f"{'T=' + str(g):>10}" for g in GATES))
for s in armc:
    for mode in ("prefix", "stride", "random"):
        line = (f"  {s:<15} {armc[s]['N_used'][0]:>3}..{armc[s]['N_used'][-1]:<5}  "
                f"{mode:<8}  ")
        for g in GATES:
            r = armc[s]["modes"][mode][str(g)]
            line += f"{r['span']:>9.4f}{'-' if r['sign'] < 0 else '+'}"
        print(line)
print("\n  (span = max/min of n_eff/N over the N range; sign = direction from "
      "lowest N to highest N)")
report["armC"] = armc

# ------------------------------------------------------ pre-registered verdict
banner("PRE-REGISTERED CRITERIA (PREREGISTRATION.md section 5)")
verdict = {}
print("  E-ABSENT / E-PRESENT / E-CONFOUNDED at the shipped default T = 4.0:\n")
print(f"  {'stack':<15} {'prefix':>18}  {'stride':>18}  {'random':>18}  {'verdict':<14}")
any_present = False
any_conf = False
for s in armc:
    rs = {m: armc[s]["modes"][m]["4.0"] for m in ("prefix", "stride", "random")}
    signs = {m: rs[m]["sign"] for m in rs}
    spans = {m: rs[m]["span"] for m in rs}
    if signs["prefix"] != signs["stride"] and min(spans.values()) > 1.01:
        v = "E-CONFOUNDED"
        any_conf = True
    elif all(x <= S_CRIT for x in spans.values()):
        v = "E-ABSENT"
    else:
        v = "E-PRESENT"
        any_present = True
    verdict[s] = {"spans": spans, "signs": signs, "verdict": v}
    cells = "  ".join(
        f"{spans[m]:>9.4f}{'-' if signs[m] < 0 else '+'} " for m in ("prefix", "stride", "random")
    )
    print(f"  {s:<15} {cells} {v:<14}")
report["verdict_g4"] = verdict
overall = "E-PRESENT" if any_present else ("E-CONFOUNDED" if any_conf else "E-ABSENT")
print(f"\n  Corpus verdict at T = 4.0: {overall}")
print(f"  (E-ABSENT required span <= {S_CRIT} on EVERY stack in ALL THREE modes.)")
report["overall_g4"] = overall

# ------------------------------------------------------- materiality ladder
banner("MATERIALITY LADDER")
mh = {str(n): f_N(n, 8.0 * SQRT2) for n in CORPUS_N}
mh_b = {str(n): brows[str(n)]["stride"]["8.0"]["n_eff_over_N"] for n in CORPUS_N if str(n) in brows}
worst_a = min(mh.values())
worst_b = min(mh_b.values())
print(f"  M-HEADLINE  arm A min f_N(8*sqrt2) over N in [19..299] = {worst_a:.8f}")
print(f"              arm B min admitted fraction at T=8         = {worst_b:.8f}")
print(f"              criterion: >= 0.999.  "
      f"{'MET' if worst_a >= 0.999 and worst_b >= 0.999 else 'NOT MET'}")
sa4 = by_gate["4.0"]["armA_span"]
sb4 = by_gate["4.0"]["armB_span"]
print(f"\n  M-DEFAULT   arm A span at T=4.0 over [19..299] = {sa4:.4f}   "
      f"criterion <= {S_CRIT}: {'MET' if sa4 <= S_CRIT else 'NOT MET'}")
print(f"              arm B span at T=4.0 over [19..299] = {sb4:.4f}   "
      f"criterion <= {S_CRIT}: {'MET' if sb4 <= S_CRIT else 'NOT MET'}")
worst_guard = 0.0
worst_where = None
for s, rec in C.items():
    for n, r in rec["rows"].items():
        for mode in ("prefix", "stride", "random"):
            v = r[mode]["4.0"]["n_eff_over_N"]
            if v > worst_guard:
                worst_guard, worst_where = v, (s, int(n), mode)
print(f"\n  M-GUARD     worst n_eff/N at gate 4.0 over every (stack, N, mode) = "
      f"{worst_guard:.5f}")
print(f"              at {worst_where}, threshold 0.95, margin "
      f"{0.95 / worst_guard:.2f}x.  "
      f"{'MET' if worst_guard < 0.95 else 'NOT MET'}")
worst_guard_real_n = 0.0
worst_real_where = None
for s, rec in C.items():
    v = rec["rows"][str(rec["N_max"])]["stride"]["4.0"]["n_eff_over_N"]
    if v > worst_guard_real_n:
        worst_guard_real_n, worst_real_where = v, (s, rec["N_max"])
print(f"              at each stack's OWN N (the shipped configuration): "
      f"{worst_guard_real_n:.5f} at {worst_real_where}, margin "
      f"{0.95 / worst_guard_real_n:.2f}x")
report["materiality"] = {
    "M_HEADLINE": {"armA": mh, "armB": mh_b, "armA_worst": worst_a,
                   "armB_worst": worst_b,
                   "met": bool(worst_a >= 0.999 and worst_b >= 0.999)},
    "M_DEFAULT": {"armA_span": sa4, "armB_span": sb4,
                  "armA_met": bool(sa4 <= S_CRIT), "armB_met": bool(sb4 <= S_CRIT)},
    "M_GUARD": {"worst": worst_guard, "where": worst_where,
                "worst_at_own_N": worst_guard_real_n, "where_own_N": worst_real_where,
                "met": bool(worst_guard < 0.95)},
}

# ------------------------------------------------ what the corrected T would be
banner("THE CORRECTED TOLERANCE - candidates (ii) and (iii), priced, NOT built")
n0 = 30
for anchor_gate in (2.0, 4.0):
    tgt = f_N(n0, anchor_gate * SQRT2)
    print(f"\n  Anchored at N0 = {n0}, T = {anchor_gate} "
          f"(null admission rate {tgt:.6f}, i.e. alpha = {1 - tgt:.6f}):")
    print(f"  {'N':>5}  {'(ii) T_equiv':>13}  {'(ii)/T':>8}  {'(iii) T_equiv':>14}"
          f"  {'(iii)/T':>9}  {'fixed-T rate':>13}")
    rows = {}
    for n in CORPUS_N:
        t_ii = t_for(n, tgt) / SQRT2
        c_n = A["c_N"][str(n)]
        c_0 = A["c_N"][str(n0)]
        t_iii = (anchor_gate * SQRT2 + c_n - c_0) / SQRT2
        rate = f_N(n, anchor_gate * SQRT2)
        rows[str(n)] = {"T_ii": t_ii, "T_iii": t_iii, "fixed_rate": rate}
        print(f"  {n:>5}  {t_ii:>13.4f}  {t_ii / anchor_gate:>8.4f}  {t_iii:>14.4f}"
              f"  {t_iii / anchor_gate:>9.4f}  {rate:>13.6f}")
    report.setdefault("corrected", {})[str(anchor_gate)] = {"anchor_N": n0, "rows": rows,
                                                            "target_rate": tgt}

OUT.mkdir(parents=True, exist_ok=True)
p = OUT / "06-blast.json"
p.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(f"\nwrote {p}")
