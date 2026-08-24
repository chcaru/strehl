"""M77 -- applies PREREGISTRATION.md section 7, verbatim, with one declared
transposition.

THE TRANSPOSITION, STATED BEFORE ANY NUMBER. Section 7 defines

    dN(T) = HP_RATIO(T) / HP_RATIO(4.0)      "noise benefit of opening"

and sets the bar "material noise gain: dN >= 1.10". HP RATIO is a NOISE ratio --
merged high-pass sd over the median per-frame high-pass sd (flat_ratio.rs:348-353)
-- so LOWER is less noise. The formula as written therefore computes a noise
INCREASE, and requiring it to exceed 1.10 asks for the merged image to get 10%
NOISIER as the gate opens. That is the opposite of the quantity the same line
names, and under the literal reading no rung can ever be (a)-SUPPORTED for the
reason the milestone exists to test.

Both are computed and both are reported. The ruling is taken on the orientation
section 7 NAMES:

    dN_benefit(T) = HP_RATIO(4.0) / HP_RATIO(T)

The bar's MAGNITUDE (1.10) is untouched, as is the detail bar (dD <= 0.98) whose
orientation was correct as written.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

G0 = 4.0
NBAR = 1.10
DBAR = 0.98


def decide(rows, k2_met, k3_met):
    r4 = rows[f"{G0:g}"]
    out = {}
    for g in m77.GATES:
        r = rows[f"{g:g}"]
        out[g] = {
            "n_eff": r["n_eff"], "n_eff_over_N": r["n_eff_over_N"],
            "hp": r["hp_ratio"], "ret": r["retention"], "eff": r["eff"],
            "dN_literal": r["hp_ratio"] / r4["hp_ratio"],
            "dN_benefit": r4["hp_ratio"] / r["hp_ratio"],
            "dD": r["retention"] / r4["retention"],
        }
    above = [g for g in m77.GATES if g > G0]
    free = [g for g in above if out[g]["dN_benefit"] >= NBAR and out[g]["dD"] > DBAR]
    knee = max([g for g in m77.GATES if out[g]["dD"] > DBAR], default=None)
    if not k2_met or not k3_met:
        verdict = "INDETERMINATE"
    elif free:
        verdict = "(a)-SUPPORTED"
    else:
        verdict = "(b)-SUPPORTED"
    would = "(a)-SUPPORTED" if free else "(b)-SUPPORTED"
    return out, verdict, would, free, knee


def report(tag, label):
    path = m77.OUT / f"02{tag}-sweep.json"
    if not path.exists():
        print(f"  (no {path.name})")
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    m77.banner(f"M77 section 7 decision rule -- {label}")
    summary = {}
    for stack, d in data.items():
        rows = d["rows"]
        k3 = d["k3_neff_met"] and d["k3_hp_met"]
        out, verdict, would, free, knee = decide(rows, d["k2_met"], k3)
        print(f"\n  --- {stack}   N {d['N']}  ISO {d['iso']:g}   flat "
              f"x{d['flat_roi']['x']},y{d['flat_roi']['y']}  "
              f"contam {d['contam_max']:.4f}")
        print(f"      K1 {'MET' if d['k1_met'] else 'NOT MET'}   "
              f"K2 {'MET' if d['k2_met'] else 'NOT MET'}   "
              f"K3 {'MET' if k3 else 'NOT MET'} "
              f"(gate-0 HP RATIO {rows['0']['hp_ratio']:.4f}x)   "
              f"K4 {'MET' if d['k4_met'] else 'NOT MET'}   "
              f"K5 flat {'MET' if d['k5_flat_met'] else 'NOT MET'} / "
              f"detail {'MET' if d['k5_detail_met'] else 'NOT MET'}")
        print(f"      {'gate':>5} {'n_eff':>9} {'n_eff/N':>8} {'HP':>7} {'RET':>9} "
              f"{'dN_ben':>7} {'dN_lit':>7} {'dD':>7} {'eff':>7}")
        for g in m77.GATES:
            o = out[g]
            mark = "  <-- shipped" if g == G0 else ""
            print(f"      {g:5g} {o['n_eff']:9.3f} {o['n_eff_over_N']:8.4f} "
                  f"{o['hp']:7.4f} {o['ret']:9.4f} {o['dN_benefit']:7.4f} "
                  f"{o['dN_literal']:7.4f} {o['dD']:7.4f} {o['eff']:7.4f}{mark}")
        print(f"      VERDICT {verdict}"
              + (f"   (rule alone would give {would})" if verdict == "INDETERMINATE"
                 else ""))
        print(f"      free rungs above shipped (dN_ben>={NBAR}, dD>{DBAR}): "
              f"{[f'{g:g}' for g in free] or 'none'}")
        if knee is not None:
            k = out[knee]
            print(f"      knee (largest T with dD>{DBAR}): gate {knee:g}   "
                  f"n_eff {k['n_eff']:.3f}   n_eff/N {k['n_eff_over_N']:.4f}   "
                  f"dN_ben {k['dN_benefit']:.4f}   dD {k['dD']:.4f}")
        summary[stack] = {
            "verdict": verdict, "rule_alone": would,
            "free": [f"{g:g}" for g in free],
            "knee": knee, "k1": d["k1_met"], "k2": d["k2_met"], "k3": k3,
            "k4": d["k4_met"], "k5_flat": d["k5_flat_met"],
            "k5_detail": d["k5_detail_met"],
            "gate0_hp": rows["0"]["hp_ratio"], "contam": d["contam_max"],
            "rows": {f"{g:g}": out[g] for g in m77.GATES},
        }
    n_a = sum(1 for v in summary.values() if v["verdict"] == "(a)-SUPPORTED")
    n_b = sum(1 for v in summary.values() if v["verdict"] == "(b)-SUPPORTED")
    n_i = sum(1 for v in summary.values() if v["verdict"] == "INDETERMINATE")
    print(f"\n  SPLIT  (a) {n_a}   (b) {n_b}   INDETERMINATE {n_i}   of {len(summary)}")
    ra = sum(1 for v in summary.values() if v["rule_alone"] == "(a)-SUPPORTED")
    print(f"  rule alone, ignoring controls (NOT THE RULING):  (a) {ra}   "
          f"(b) {len(summary) - ra}")
    return summary


def main():
    res = {}
    s = report("", "arm G0, the REGISTERED arm")
    if s:
        res["G0"] = s
    s = report("b", "arm G0', ALL frames -- DECLARED DEVIATION, post hoc")
    if s:
        res["G0b"] = s
    (m77.OUT / "03-decide.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print("\n  wrote out/03-decide.json")


if __name__ == "__main__":
    main()
