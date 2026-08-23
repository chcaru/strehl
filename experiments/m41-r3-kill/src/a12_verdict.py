"""M41 step 12 -- score the pre-registered kill condition PROGRAMMATICALLY, and
find out how much of the verdict rests on the metric a10/a11 just killed.

The condition is transcribed from PREREGISTRATION.md (commit f809772, written
before any arm ran) into `verdict()` below, ONCE, and then applied.  It is never
re-worded in prose and then scored by eye.

RULE 20 -- the input that makes this scorer FAIL to return REFUTED.  An arm with
`n <= 1.10 * n_A` and `f > 1.02 * f_A` returns REOPEN or INDETERMINATE instead.
Such an arm EXISTS IN THIS EXPERIMENT: arm C, the plain mean, reads 0.536x and
0.451x the shipped merge's flat-ROI high-pass noise.  The scorer is therefore
not a tautology, and this script proves it by running arm C through it and
printing the different answer.

RULE 24 -- the thing a verifier should re-choose here is which arm is plugged in
as "D", and what f_D is assumed to be.  Both are swept.

Reads out/a6_results.json (the run of record), out/a10_results.json (which of
its FRC readings are censored) and out/a11_results.json (which metrics have
demonstrated power).  Computes nothing new from pixels.
"""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m41lib as L

OUT = L.OUT
STACKS = ("109MSDCF", "119MSDCF")

KILL_CONDITION = """\
R3 STANDS REFUTED if -- on both 109MSDCF and 119MSDCF --
    f_D <= 1.02 * f_A, i.e. the deconvolving merge buys less than 2% in FRC
    resolution over the shipped noise-gated merge,
OR if it buys resolution only by paying noise:
    f_D > 1.02 * f_A but n_D > 1.10 * n_A.
R3 MUST BE REOPENED if -- on both stacks --
    f_D >= 1.05 * f_A and n_D <= 1.05 * n_A.
The band between (2%, 5%) is INDETERMINATE."""


def verdict(f_ratio, n_ratio):
    """The pre-registered condition, per stack.  f_ratio = f_D/f_A, n_ratio = n_D/n_A."""
    refuted = (f_ratio <= 1.02) or (f_ratio > 1.02 and n_ratio > 1.10)
    reopen = (f_ratio >= 1.05) and (n_ratio <= 1.05)
    if refuted and reopen:
        return "CONFLICT"
    if refuted:
        return "REFUTED"
    if reopen:
        return "REOPEN"
    return "INDETERMINATE"


def combine(per_stack):
    """Both clauses are written 'on both stacks', so the milestone verdict is the
    unanimous one or nothing."""
    s = set(per_stack)
    return per_stack[0] if len(s) == 1 else "SPLIT " + "/".join(per_stack)


def main():
    fh = open(os.path.join(OUT, "a12_verdict.log"), "w", encoding="utf-8")

    def p(m):
        print(m); fh.write(m + "\n"); fh.flush()

    a6 = json.load(open(os.path.join(OUT, "a6_results.json")))
    a10 = json.load(open(os.path.join(OUT, "a10_results.json")))
    a11 = json.load(open(os.path.join(OUT, "a11_results.json")))

    p("M41 step 12 -- scoring the pre-registered kill condition.")
    p("\nTHE CONDITION, verbatim from PREREGISTRATION.md (commit f809772):")
    for line in KILL_CONDITION.splitlines():
        p("    " + line)

    # --- the two metrics, and what a10/a11 say about each -----------------
    p("\nSTATE OF THE TWO METRICS THE CONDITION USES")
    v = a11["verdicts"]
    p(f"  f  (FRC 1/7 crossing) : planted-blur recovery -> {v['frc_cross_1_7']}")
    p(f"     a10: {a10['n_censored']}/{a10['n_total']} of the run-of-record's "
      f"detail-ROI readings are CENSORED at the ring-grid endpoint "
      f"{a10['fallback']['64']:.4f}.")
    p(f"     a10: repair settings (4 ring counts x 4 thresholds) that are "
      f"uncensored AND separate detail from flat, on both stacks: "
      f"{a10['repairs_both'] if a10['repairs_both'] else 'NONE'}.")
    p(f"  n  (flat-ROI high-pass spatial sd ratio) : planted-blur recovery of the "
      f"same statistic -> {v['hp_sd']}")
    p("     and on real data arm E fires it at 144.391x / 295.487x, so it can "
      "reject.")

    res = {"kill_condition": KILL_CONDITION, "per_arm": {}}

    # --- score every arm in D's seat -------------------------------------
    p("\nEVERY ARM PUT IN D's SEAT.  f is quoted as a BOUND where a10 says it is "
      "censored.")
    p(f"  {'arm':4s} " + "  ".join(f"{s + ' f_x/f_A':>18s}  {s + ' n_x/n_A':>13s}  "
                                   f"{'verdict':>13s}" for s in STACKS) +
      "   milestone")
    for arm in ("D", "D'", "E", "C", "B"):
        cells, verds = [], []
        rec = {}
        for st in STACKS:
            fA = a6[st]["frc"]["A"]["cross"]
            fX = a6[st]["frc"][arm]["cross"]
            cA = a10["a6_recheck"][st]["A"]["censored"]
            cX = a10["a6_recheck"][st][arm]["censored"]
            nA = a6[st]["flat"]["A"]["hp_ratio"]
            nX = a6[st]["flat"][arm]["hp_ratio"]
            fr, nr = fX / fA, nX / nA
            vd = verdict(fr, nr)
            mark = (">=" if cX else "") + ("/<=" if cA else "")
            cells.append(f"{(mark + '%.3f' % fr):>18s}  {nr:13.3f}  {vd:>13s}")
            verds.append(vd)
            rec[st] = dict(f_ratio=fr, n_ratio=nr, verdict=vd,
                           f_censored=bool(cX), fA_censored=bool(cA))
        p(f"  {arm:4s} " + "  ".join(cells) + f"   {combine(verds)}")
        rec["milestone"] = combine(verds)
        res["per_arm"][arm] = rec

    p("\n  RULE 20 CHECK.  The scorer is not a tautology: arm C returns "
      f"'{res['per_arm']['C']['milestone']}', not REFUTED,")
    p("  because its noise ratio (0.536x / 0.451x) does not clear the 1.10x "
      "clause.  An input that")
    p("  produces a non-REFUTED answer exists inside this experiment's own "
      "output.")

    # --- how much of D's verdict rests on the dead metric? ----------------
    p("\nDOES THE VERDICT DEPEND ON THE DEAD METRIC?  Sweep f_D/f_A over every "
      "value it could")
    p("have taken -- including the ones the censored reading forbids us from "
      "excluding -- and")
    p("re-score with the MEASURED noise ratios held fixed.")
    grid = [0.50, 0.80, 0.95, 1.00, 1.02, 1.021, 1.05, 1.20, 1.50, 2.00, 5.00]
    outs = {}
    p(f"    {'f_D/f_A':>8s}  " + "  ".join(f"{s:>14s}" for s in STACKS) + "   milestone")
    for fr in grid:
        vs = [verdict(fr, res["per_arm"]["D"][st]["n_ratio"]) for st in STACKS]
        m = combine(vs)
        outs[str(fr)] = m
        p(f"    {fr:8.3f}  " + "  ".join(f"{x:>14s}" for x in vs) + f"   {m}")
    res["f_sweep_D"] = outs
    allref = all(x == "REFUTED" for x in outs.values())
    p(f"  -> REFUTED at every sampled f_D/f_A: {allref}")
    p("  DERIVED: with n_D/n_A = "
      f"{res['per_arm']['D']['109MSDCF']['n_ratio']:.3f} and "
      f"{res['per_arm']['D']['119MSDCF']['n_ratio']:.3f}, both above 1.10, the two "
      "REFUTED clauses")
    p("  ('f <= 1.02' and 'f > 1.02 with n > 1.10') are EXHAUSTIVE over f.  The "
      "verdict for arm D")
    p("  is therefore independent of the FRC reading, and survives that metric "
      "being withdrawn.")

    # the same sweep for arm C, to show the sweep itself can move
    p("\n  The same sweep for arm C, whose noise ratio does NOT clear 1.10x -- "
      "this is what a")
    p("  verdict that DOES depend on the FRC axis looks like:")
    outc = {}
    for fr in grid:
        vs = [verdict(fr, res["per_arm"]["C"][st]["n_ratio"]) for st in STACKS]
        outc[str(fr)] = combine(vs)
        p(f"    {fr:8.3f}  " + "  ".join(f"{x:>14s}" for x in vs) + f"   {combine(vs)}")
    res["f_sweep_C"] = outc

    # --- arithmetic check that the clauses cannot both fire ---------------
    conflicts = sum(1 for fr in np.linspace(0.1, 5.0, 2000)
                    for nr in np.linspace(0.1, 10.0, 400)
                    if verdict(fr, nr) == "CONFLICT")
    p(f"\n  Arithmetic check: CONFLICT cases over an 800k (f, n) grid: {conflicts}. "
      "The REFUTED and")
    p("  REOPEN clauses are disjoint as written, so no data can satisfy both.")
    res["conflicts"] = conflicts

    p("\n" + "=" * 78)
    p(f"M41 VERDICT FOR ARM D (the R3 estimator): "
      f"{res['per_arm']['D']['milestone']}")
    p("  carried by: the NOISE clause, on a statistic with demonstrated power "
      "(a11 recovery")
    p("  +0.967 to +1.000; arm E fires it at 144x/295x on real data).")
    p("  NOT carried by: the FRC clause, which a10 and a11 show has no power "
      "here and is withdrawn.")
    p("  What M41 CANNOT say: whether arm D buys any real resolution.  It has no "
      "metric able to")
    p("  measure that on this data, and it does not manufacture one.")
    p("=" * 78)

    json.dump(res, open(os.path.join(OUT, "a12_results.json"), "w"), indent=2)
    p("wrote out/a12_results.json")
    fh.close()


if __name__ == "__main__":
    main()
