"""12 -- which fit-quality metric actually predicts slope error?

PRE-REGISTERED. Committed before being run.

--------------------------------------------------------------------------
WHY
--------------------------------------------------------------------------

Script 11 pre-registered a mechanical fit gate, "max PTC bin residual < 25%",
and running it exposed a problem with that gate rather than with the data:

  * `foam` (ISO 1000, resid 42%) FAILS it. `foam` is the sole surviving
    source of M61's published ISO-1000 headline (r = 1.0174), because its
    partner `coffee-bubbles` failed far worse. Under this gate there is NO
    usable ISO-1000 stack at all.

  * `109MSDCF` (ISO 160), the CONTROL, has resid 18.2% -- not far below the
    gate -- yet recovers the independently known ISO-160 gain to 1.1%.

  * `bee-3` has resid 0.5%, the best in the ladder, yet sits 2.7% from 1.0,
    further than the control does.

So the control demonstrates that a large max-bin residual is compatible with
an accurate slope, and the best-residual stack is not the most accurate. The
gate I pre-registered in script 11 may be measuring the wrong thing.

I am NOT going to quietly swap gates. Rule 15: the script-11 gate stays in
the record as pre-registered and its result stays reported. This script asks
an empirical question and fixes the answer criterion in advance.

--------------------------------------------------------------------------
THE QUESTION
--------------------------------------------------------------------------

Of the four fit-quality metrics available per stack --

    resid_pct   max PTC bin residual
    ab_pct      |gB/gA - 1|, disagreement between estimator variants A and B
    ac_pct      |gC/gA - 1|, variants A and C
    half_pct    |g_half1/g_half0 - 1|, first half of the stack vs second

-- which one predicts SLOPE ERROR?

Slope error is not directly observable for most stacks (that is the whole
problem), so I use two proxies, both fixed here before computing anything:

  T1 CONTROL ANCHOR. For 109MSDCF alone, true error is known: |r - 1| against
     the independently calibrated ISO-160 gain. A metric that ranks the
     control as untrustworthy while it is in fact accurate is a bad metric.

  T2 REPLICATE DISAGREEMENT. For every ISO with >= 2 stacks (50, 100, 400,
     500, 1000), the spread of r within that ISO group is an unbiased proxy
     for slope error, because all stacks at one ISO are measuring the same
     physical constant. For each metric I compute the rank correlation
     (Spearman, computed by hand -- no scipy dependency) between a stack's
     metric value and its absolute deviation from its own ISO-group median.

--------------------------------------------------------------------------
PREDICTIONS, fixed before the run
--------------------------------------------------------------------------

  Q-1 resid_pct will correlate WEAKLY or not at all with deviation. A single
      bad PTC bin -- a clipped tile, a bright specular patch, one moment of
      subject motion -- inflates the max residual without moving a slope
      fitted over many bins.

  Q-2 half_pct will correlate BEST. A stack whose first and second halves
      disagree has something changing during the capture (motion, drift,
      lighting), which is exactly what biases a temporal-difference PTC.

  Q-3 If Q-1 and Q-2 hold, the script-11 gate was mis-specified, `foam`
      should be retained, and the correct gate is on half_pct.

  Q-4 If instead resid_pct predicts best, then `foam` genuinely fails, the
      ISO-1000 headline has NO surviving stack, and M61's ISO-1000 number
      must be withdrawn and reported as unmeasurable in this corpus. I state
      that consequence now so it cannot be softened later.

--------------------------------------------------------------------------
ACCEPTANCE
--------------------------------------------------------------------------

  D1 Whichever metric has the highest |Spearman rho| against T2 is declared
     the diagnostic metric. Ties within 0.15 rho are declared "no metric
     predicts" and the honest outcome is to report every arm ungated with
     the full spread as the uncertainty.

  D2 The control must not be rejected by the winning metric at a threshold
     that retains the ladder's best stacks. A gate that throws out a stack
     KNOWN to be accurate is disqualified regardless of its rho.

  D3 The headline is then restated under the winning gate, and under no gate,
     and both are published. If they disagree by more than the quoted
     uncertainty, the arm is reported as gate-dependent, which is a weaker
     claim than M61 currently makes and I will make it.
"""

from __future__ import annotations

import csv
import math
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "..", "data", "ptc-ladder.csv")
OUT = os.path.join(HERE, "..", "data", "gate-metric.txt")

GREENS = ("G1", "G2")
SECOND_BASE_ISO = 400.0
TIE_BAND = 0.15

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


def median(xs):
    xs = sorted(x for x in xs if not math.isnan(x))
    if not xs:
        return float("nan")
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def rank(xs):
    """Average ranks, ties shared."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(a, b):
    pairs = [(x, y) for x, y in zip(a, b)
             if not math.isnan(x) and not math.isnan(y)]
    if len(pairs) < 3:
        return float("nan")
    ra = rank([p[0] for p in pairs])
    rb = rank([p[1] for p in pairs])
    ma, mb = mean(ra), mean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da and db else float("nan")


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

    def gm(stack, key):
        return mean([per[stack][p][key] for p in GREENS if p in per[stack]])

    def r_greens(s):
        return mean([per[s][p]["gA"] / per[s][p]["g_model"]
                     for p in GREENS if p in per[s]])

    metrics = {}
    for s in stacks:
        gA = gm(s, "gA")
        metrics[s] = {
            "resid_pct": gm(s, "resid_pct"),
            "ab_pct": 100 * abs(gm(s, "gB") / gA - 1) if gA else float("nan"),
            "ac_pct": 100 * abs(gm(s, "gC") / gA - 1) if gA else float("nan"),
            "half_pct": 100 * abs(gm(s, "g_half1") / gm(s, "g_half0") - 1),
        }

    say("M61 script 12 -- which fit-quality metric predicts slope error?")
    say("=" * 78)
    say()

    say(f"  {'stack':<16}{'ISO':>6}{'r':>9}{'resid%':>9}{'A/B%':>8}"
        f"{'A/C%':>8}{'half%':>8}")
    for s in stacks:
        m = metrics[s]
        say(f"  {s:<16}{iso[s]:>6.0f}{r_greens(s):>9.4f}{m['resid_pct']:>9.1f}"
            f"{m['ab_pct']:>8.1f}{m['ac_pct']:>8.1f}{m['half_pct']:>8.1f}")
    say()

    # ------------------------------------------------------------ T1
    say("T1. CONTROL ANCHOR -- 109MSDCF, the one stack with a known answer")
    say("-" * 78)
    c = metrics["109MSDCF"]
    say(f"  true error |r-1|     = {abs(r_greens('109MSDCF') - 1):.4f}  (1.1%)")
    say(f"  resid_pct            = {c['resid_pct']:.1f}%   <- would look BAD")
    say(f"  A/B, A/C, half       = {c['ab_pct']:.1f}%, {c['ac_pct']:.1f}%, "
        f"{c['half_pct']:.1f}%   <- look GOOD")
    say("  A stack known to be accurate scores badly on resid_pct and well on")
    say("  the consistency metrics. That is one data point, not a result.")
    say()

    # ------------------------------------------------------------ T2
    say("T2. REPLICATE DISAGREEMENT -- deviation from own ISO-group median")
    say("-" * 78)
    groups = defaultdict(list)
    for s in stacks:
        groups[iso[s]].append(s)
    dev = {}
    for i, members in sorted(groups.items()):
        if len(members) < 2:
            say(f"  ISO {i:>5.0f}: n=1 ({members[0]}) -- excluded, no replicate")
            continue
        med = median([r_greens(s) for s in members])
        say(f"  ISO {i:>5.0f}: n={len(members)}  median r = {fmt(med)}")
        for s in members:
            dev[s] = abs(r_greens(s) - med)
            say(f"      {s:<16} r={r_greens(s):.4f}  |dev|={dev[s]:.4f}")
    say()

    say("  Spearman rho between each metric and |deviation from ISO median|:")
    names = list(dev.keys())
    devs = [dev[s] for s in names]
    rhos = {}
    for key in ("resid_pct", "ab_pct", "ac_pct", "half_pct"):
        vals = [metrics[s][key] for s in names]
        rhos[key] = spearman(vals, devs)
        say(f"      {key:<12} rho = {fmt(rhos[key], 3):>7}   (n={len(names)})")
    say()

    # ------------------------------------------------------------ D1
    say("D1. WINNING METRIC")
    say("-" * 78)
    ranked = sorted(rhos.items(),
                    key=lambda kv: (-abs(kv[1]) if not math.isnan(kv[1]) else 1))
    best, best_rho = ranked[0]
    second, second_rho = ranked[1]
    tied = abs(abs(best_rho) - abs(second_rho)) < TIE_BAND
    say(f"  best   {best:<12} rho {fmt(best_rho,3)}")
    say(f"  second {second:<12} rho {fmt(second_rho,3)}")
    if tied:
        say(f"  Within the {TIE_BAND} tie band -> DECLARED: no metric predicts.")
        say("  Per D1 the honest outcome is to report every arm UNGATED with")
        say("  the full observed spread as the uncertainty.")
    else:
        say(f"  DECLARED diagnostic metric: {best}")
    say()

    # ------------------------------------------------------------ D3
    say("D3. THE HEADLINE UNDER EVERY GATE")
    say("-" * 78)

    def arm(label, keep):
        lo = [r_greens(s) for s in stacks
              if iso[s] < SECOND_BASE_ISO and keep(s)]
        hi = [r_greens(s) for s in stacks
              if iso[s] >= SECOND_BASE_ISO and keep(s)]
        i500 = [r_greens(s) for s in stacks if iso[s] == 500 and keep(s)]
        i1000 = [r_greens(s) for s in stacks if iso[s] == 1000 and keep(s)]
        ratio = mean(hi) / mean(lo) if lo and hi else float("nan")
        say(f"  {label:<30}")
        say(f"      ISO 500  {fmt(mean(i500))} +/- {fmt(spread(i500))} (n{len(i500)})"
            f"     ISO 1000  {fmt(mean(i1000))} +/- {fmt(spread(i1000))} (n{len(i1000)})")
        say(f"      r_hi/r_lo {fmt(ratio)}   (H0 1.000, H1 0.460)")

    arm("no gate (all 12 stacks)", lambda s: True)
    arm("script-11 gate resid<25%", lambda s: metrics[s]["resid_pct"] < 25)
    arm("half_pct < 5%", lambda s: metrics[s]["half_pct"] < 5)
    arm("half_pct < 2%", lambda s: metrics[s]["half_pct"] < 2)
    arm("ac_pct < 10%", lambda s: metrics[s]["ac_pct"] < 10)
    say()

    say("  ISO-1000 membership under each gate:")
    for lab, keep in (("no gate", lambda s: True),
                      ("resid<25%", lambda s: metrics[s]["resid_pct"] < 25),
                      ("half<5%", lambda s: metrics[s]["half_pct"] < 5),
                      ("half<2%", lambda s: metrics[s]["half_pct"] < 2),
                      ("ac<10%", lambda s: metrics[s]["ac_pct"] < 10)):
        keptn = [s for s in stacks if iso[s] == 1000 and keep(s)]
        say(f"      {lab:<12} {', '.join(keptn) if keptn else 'NONE -- '
                               'ISO 1000 unmeasurable under this gate'}")
    say()

    say("  Does the control survive each gate? (D2)")
    for lab, keep in (("resid<25%", lambda s: metrics[s]["resid_pct"] < 25),
                      ("half<5%", lambda s: metrics[s]["half_pct"] < 5),
                      ("half<2%", lambda s: metrics[s]["half_pct"] < 2),
                      ("ac<10%", lambda s: metrics[s]["ac_pct"] < 10)):
        say(f"      {lab:<12} 109MSDCF "
            f"{'KEPT' if keep('109MSDCF') else 'REJECTED -- gate disqualified'}")

    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(_lines) + "\n")
    print(f"\n[written] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
