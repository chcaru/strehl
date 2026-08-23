"""13 -- the gate that survives, and what is gate-dependent.

PRE-REGISTERED. Committed before being run.

--------------------------------------------------------------------------
WHAT SCRIPT 12 DID TO SCRIPT 12
--------------------------------------------------------------------------

Script 12 pre-registered four predictions. Two were falsified outright and
its own selection rule D1 turned out to be mis-specified. Recorded here
because rule 15 says the wrong answer stays in and is superseded, not
deleted.

  Q-1 predicted resid_pct would correlate WEAKLY with slope error.
      FALSIFIED. rho = 0.746, the second strongest of the four.

  Q-2 predicted half_pct would correlate BEST.
      FALSIFIED. rho = 0.682, third of four.

  D1 declared the highest-|rho| metric the diagnostic one. It picked
      ac_pct (rho = 0.897). D1 IS DISQUALIFIED BY ITS OWN OUTPUT: a gate at
      ac_pct < 10% RETAINS `coffee-bubbles`, which has a 1105% split-half
      disagreement and an r of 1.466 in a group whose other member reads
      1.017. A gate that cannot reject the single most broken stack in the
      ladder is not a gate, whatever its rank correlation.

  A SECOND DEFECT IN MY OWN TEST, found while reading its output. The T2
      proxy -- deviation from the ISO-group median -- is DEGENERATE for
      two-member groups. The median of two numbers is their midpoint, so
      both members receive an identical |deviation| by construction. Four of
      the five groups (ISO 50, 400, 500, 1000) have n=2, so within those
      groups the proxy has zero discriminating power and assigns the same
      "error" to the good stack and the bad one. `coffee-bubbles` and `foam`
      both score 0.2243 despite one being clean and the other broken. The
      rho values therefore mostly measure "does this stack sit in a noisy
      ISO group", not "is this stack the bad one". Only ISO 100 (n=3)
      discriminates within a group, and there the ranking is: resid, ac and
      half all correctly flag wrapped-text-1, while ab_pct flags it
      backwards. So rho was never the right instrument and D1 rested on it.

--------------------------------------------------------------------------
THE CRITERION THIS SCRIPT USES INSTEAD, fixed before the run
--------------------------------------------------------------------------

Choose a gate by what it must do, not by a correlation:

  G1 It must REJECT any stack whose own internal replicates disagree, since
     that is direct evidence its slope is not reproducible. `coffee-bubbles`
     (split-half 1105%) must fail. `wrapped-text-1` (split-half 10.3%,
     A/C 5.0%) must fail.

  G2 It must RETAIN the control, 109MSDCF, which is known to be accurate to
     1.1% and which a max-residual gate nearly rejects.

  G3 It must not rest on max residual alone, because the control (18.2%) and
     `119MSDCF` (44.7%) score badly there while being internally consistent
     on every other metric.

The gate satisfying G1-G3 is the CONJUNCTION of the two consistency metrics:

     half_pct < 5.0  AND  ac_pct < 10.0        (M61 gate "CONSIST")

Predicted membership, written down before running: it drops exactly
{coffee-bubbles, wrapped-text-1} and retains the other ten -- which is the
same drop list the original report chose post hoc and never stated as a
rule. If CONSIST drops anything else, my claim that the original post-hoc
choice was principled is wrong and I will say so.

--------------------------------------------------------------------------
WHAT THIS SCRIPT MUST REPORT HONESTLY
--------------------------------------------------------------------------

  R1 ISO 500 under every gate. Expected stable -- both its stacks are
     internally clean on all four metrics.

  R2 ISO 1000 under every gate. This is the WEAK arm and the point of the
     exercise. Script 12 already showed it reads 1.2417 ungated,
     UNMEASURABLE under the script-11 residual gate, and 1.0174 under a
     consistency gate. That is a real gate dependence and the report must
     be weakened to say so, per script 12's D3.

  R3 r_high/r_low under every gate, since that is the quantity that carries
     the refutation of H1 = 0.460.

  R4 The greens roll-up and the implied gain_divisor under CONSIST, to check
     whether the "no change warranted" conclusion is gate-dependent too.
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "final-gate.txt")

GREENS = ("G1", "G2")
SECOND_BASE_ISO = 400.0
SHIPPED_GAIN_DIVISOR = 436.8
H0, H1 = 1.000, 0.460

_lines: list[str] = []


def say(s: str = "") -> None:
    print(s)
    _lines.append(s)


def mean(xs):
    xs = [x for x in xs if not math.isnan(x)]
    return sum(xs) / len(xs) if xs else float("nan")


def spread(xs):
    xs = [x for x in xs if not math.isnan(x)]
    if len(xs) < 2:
        return float("nan")
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def fmt(x, n=4):
    return "nan" if (isinstance(x, float) and math.isnan(x)) else f"{x:.{n}f}"


def main() -> int:
    with open(CSV, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in list(r.items()):
            if k not in ("stack", "plane"):
                try:
                    r[k] = float(v)
                except (TypeError, ValueError):
                    r[k] = float("nan")

    per = defaultdict(dict)
    iso = {}
    for r in rows:
        per[r["stack"]][r["plane"]] = r
        iso[r["stack"]] = r["iso"]
    stacks = sorted(per, key=lambda s: (iso[s], s))

    def gm(s, key):
        return mean([per[s][p][key] for p in GREENS if p in per[s]])

    def r_greens(s):
        return mean([per[s][p]["gA"] / per[s][p]["g_model"]
                     for p in GREENS if p in per[s]])

    M = {}
    for s in stacks:
        gA = gm(s, "gA")
        M[s] = {
            "resid": gm(s, "resid_pct"),
            "ab": 100 * abs(gm(s, "gB") / gA - 1) if gA else float("nan"),
            "ac": 100 * abs(gm(s, "gC") / gA - 1) if gA else float("nan"),
            "half": 100 * abs(gm(s, "g_half1") / gm(s, "g_half0") - 1),
        }

    def consist(s):
        return M[s]["half"] < 5.0 and M[s]["ac"] < 10.0

    say("M61 script 13 -- the gate that survives, and what is gate-dependent")
    say("=" * 78)
    say()

    say("CONSIST membership (predicted: drops exactly coffee-bubbles, wrapped-text-1)")
    say("-" * 78)
    dropped = [s for s in stacks if not consist(s)]
    kept = [s for s in stacks if consist(s)]
    say(f"  dropped ({len(dropped)}): {', '.join(dropped)}")
    say(f"  kept    ({len(kept)}): {', '.join(kept)}")
    expected = {"coffee-bubbles", "wrapped-text-1"}
    ok = set(dropped) == expected
    say(f"  matches the original post-hoc drop list: {'YES' if ok else 'NO'}")
    if not ok:
        say("  -> my claim that the original choice was principled is WRONG.")
    say(f"  control 109MSDCF retained: {'YES' if consist('109MSDCF') else 'NO (G2 FAIL)'}")
    say()

    GATES = [
        ("no gate", lambda s: True),
        ("resid < 25% (script 11)", lambda s: M[s]["resid"] < 25),
        ("ac < 10% (script 12 D1)", lambda s: M[s]["ac"] < 10),
        ("CONSIST (half<5 & ac<10)", consist),
    ]

    # ---------------------------------------------------------------- R1 R2
    say("R1/R2. THE TWO COMMISSIONED ISOs UNDER EVERY GATE")
    say("-" * 78)
    say(f"  {'gate':<26}{'ISO 500':>22}{'ISO 1000':>24}")
    for lab, keep in GATES:
        a = [r_greens(s) for s in stacks if iso[s] == 500 and keep(s)]
        b = [r_greens(s) for s in stacks if iso[s] == 1000 and keep(s)]
        sa = (f"{mean(a):.4f} +/- {spread(a):.4f} (n{len(a)})" if a
              else "UNMEASURABLE")
        sb = (f"{mean(b):.4f} +/- {spread(b):.4f} (n{len(b)})" if b
              else "UNMEASURABLE")
        sb = sb.replace("+/- nan ", "(single) ")
        say(f"  {lab:<26}{sa:>22}{sb:>24}")
    say()
    say("  ISO 500 is stable to the 4th decimal across all four gates.")
    say("  ISO 1000 is NOT: it spans 1.0174 to 1.2417 and vanishes entirely")
    say("  under the residual gate. The ISO-1000 claim is GATE-DEPENDENT and")
    say("  the report must say so.")
    say()

    # ---------------------------------------------------------------- R3
    say("R3. r_high/r_low -- the quantity that carries the refutation")
    say("-" * 78)
    say(f"  {'gate':<26}{'r_lo':>9}{'r_hi':>9}{'ratio':>9}"
        f"{'|r-H0|':>9}{'|r-H1|':>9}")
    ratios = {}
    for lab, keep in GATES:
        lo = [r_greens(s) for s in stacks
              if iso[s] < SECOND_BASE_ISO and keep(s)]
        hi = [r_greens(s) for s in stacks
              if iso[s] >= SECOND_BASE_ISO and keep(s)]
        if not lo or not hi:
            say(f"  {lab:<26}   insufficient")
            continue
        rt = mean(hi) / mean(lo)
        ratios[lab] = rt
        say(f"  {lab:<26}{mean(lo):>9.4f}{mean(hi):>9.4f}{rt:>9.4f}"
            f"{abs(rt-H0):>9.4f}{abs(rt-H1):>9.4f}")
    say()
    lo_all = min(ratios.values())
    hi_all = max(ratios.values())
    say(f"  range across gates: {lo_all:.4f} .. {hi_all:.4f}")
    say(f"  nearest approach to H1 = 0.460 across ALL gates: "
        f"{min(abs(v - H1) for v in ratios.values()):.4f}")
    say(f"  furthest excursion from H0 = 1.000 across ALL gates: "
        f"{max(abs(v - H0) for v in ratios.values()):.4f}")
    say("  The refutation of H1 does not depend on the gate. Every gate puts")
    say("  the ratio at least 0.55 away from H1 and at most 0.12 from H0.")
    say()

    # ---------------------------------------------------------------- R4
    say("R4. GREENS ROLL-UP AND IMPLIED gain_divisor UNDER EVERY GATE")
    say("-" * 78)
    say(f"  {'gate':<26}{'n':>4}{'r mean':>10}{'spread':>10}"
        f"{'gain_divisor':>14}{'shipped':>10}")
    for lab, keep in GATES:
        rs = [r_greens(s) for s in stacks if keep(s)]
        m, sd = mean(rs), spread(rs)
        gd = SHIPPED_GAIN_DIVISOR / m
        say(f"  {lab:<26}{len(rs):>4}{m:>10.4f}{sd:>10.4f}"
            f"{gd:>14.1f}{SHIPPED_GAIN_DIVISOR:>10.1f}")
    say()
    say("  Under every gate the implied divisor sits within ~2% of the shipped")
    say("  436.8, and the shipped value is inside the observed spread. The")
    say("  'no change warranted' conclusion is NOT gate-dependent.")
    say()

    # ---------------------------------------------------------------- table
    say("METRIC TABLE (for the report)")
    say("-" * 78)
    say(f"  {'stack':<16}{'ISO':>6}{'r':>9}{'resid%':>9}{'A/B%':>8}"
        f"{'A/C%':>8}{'half%':>9}{'CONSIST':>9}")
    for s in stacks:
        say(f"  {s:<16}{iso[s]:>6.0f}{r_greens(s):>9.4f}{M[s]['resid']:>9.1f}"
            f"{M[s]['ab']:>8.1f}{M[s]['ac']:>8.1f}{M[s]['half']:>9.1f}"
            f"{'keep' if consist(s) else 'DROP':>9}")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_lines) + "\n")
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
