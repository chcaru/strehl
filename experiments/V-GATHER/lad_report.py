r"""The ladder result: does manufactured detail track the merge's selection law?

WHAT IS BEING DECIDED. Two things had supported the claim that the merge
manufactures detail, neither of them an experiment: `stack.rs:11` names the
mechanism, and 13 of 19 subjects exceed their own focus ceiling. The ladder
makes the selection exponent the independent variable, so the claim becomes
falsifiable in the way ORCH set out: excess should rise with the exponent and
approach zero at exponent 1, and if it is flat across a 16x range, or large at
exponent 1, the selection law is NOT the mechanism.

TWO INDEPENDENT LINES OF EVIDENCE ARE COMPUTED, because each covers the other's
weakness.

  BETWEEN SUBJECTS, the ordering e1 < e2 < e4 < e8 is one of 24 orderings of
  four values. Under a null in which the exponent does nothing and the observed
  order is chance, each subject has probability 1/24 of landing on the increasing
  one. Replication across independent subjects is then a sign test needing no
  distributional assumption and no estimate of the median's sampling error.

  WITHIN SUBJECTS, per site, the same ordering is counted at INDIVIDUAL
  locations. This is the answer to the objection the median cannot answer: a
  monotone sequence of medians could in principle be produced by a few sites
  moving while the rest do nothing.

THE e16 ARM IS REPORTED BUT EXCLUDED FROM THE MONOTONICITY TEST, and the reason
is stated rather than convenient. At exponent 16 selection is effectively argmax,
which the tool's own help predicts will "take adjacent coefficients from
opposite-signed frames, which is ringing"; measured, it is erratic rather than
extreme in one direction -- +1975% on wrapped-text-1 but +5.2% on 112MSDCF,
below that subject's own e8. An arm that is degenerate is not evidence for a
trend in either direction, and including it would let a wild value carry or
destroy the result. The shipping ladder runs 2..8, so 1..8 is the range that
speaks to the shipped product anyway.
"""
import io
import json
import itertools
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lad_measure as lm                                           # noqa: E402

MONO = ["e1", "e2", "e4", "e8"]
ALL = ["e1", "e2", "e4", "e8", "e16", "default"]
# Subjects whose sharpness record placed the master WITHIN its ceiling. They are
# the negative controls: ORCH's second, independent way for the mechanism to be
# wrong is a within-ceiling subject that STAYS within ceiling at exponent 16.
CONTROLS = {"coffee-bubbles", "109MSDCF", "119MSDCF"}


def load(name):
    p = os.path.join(HERE, name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def med(doc, sub, arm):
    a = doc.get(sub, {}).get("arms", {}).get(arm, {})
    v = a.get("median")
    return v if lm.finite(v) else None


def main():
    doc = load("ladder.json")
    sites = load("ladder-sites.json")

    print("=" * 96)
    print("LADDER: median ceiling excess, by selection exponent (--pyramid-sharpen 1.0)")
    print("  positive = the master carries MORE mid-band contrast than the best input frame")
    print("=" * 96)
    hdr = "  %-24s %9s %9s %9s %9s %11s %11s  %s" % (
        "subject", "e1", "e2", "e4", "e8", "e16", "shipping", "e1..e8")
    print(hdr)
    n_mono = n_tested = 0
    rows = []
    for sub in doc:
        vals = [med(doc, sub, a) for a in MONO]
        cells = []
        for a in ALL[:5]:
            v = med(doc, sub, a)
            cells.append("%+8.2f%%" % (100 * v) if v is not None else "  REFUSED")
        d = med(doc, sub, "default")
        dcell = "%+9.2f%%" % (100 * d) if d is not None else "   REFUSED"
        if all(v is not None for v in vals):
            n_tested += 1
            up = all(vals[i] < vals[i + 1] for i in range(len(vals) - 1))
            n_mono += up
            tag = "RISING" if up else "not monotone"
        else:
            tag = "incomplete"
        print("  %-24s %s %s %s %s %s %s  %s"
              % (sub + ("*" if sub in CONTROLS else ""), cells[0], cells[1],
                 cells[2], cells[3], cells[4].rjust(10), dcell, tag))
        rows.append((sub, vals, d, med(doc, sub, "e16")))
    print("  * = negative control: the sharpness axis placed this master WITHIN its ceiling")

    print("\n=== BETWEEN SUBJECTS: sign test on the ordering ===")
    p_one = 1.0 / len(list(itertools.permutations(range(4))))
    print("  subjects with all four arms measured        : %d" % n_tested)
    print("  of those, ordering e1 < e2 < e4 < e8        : %d" % n_mono)
    print("  P(a single subject lands on it by chance)   : %.4f  (1 of 24 orderings)" % p_one)
    if n_mono == n_tested and n_tested:
        print("  P(all %d by chance, exponent inert)          : %.3e"
              % (n_tested, p_one ** n_tested))

    print("\n=== VALUE AT EXPONENT 1: is manufactured detail absent there? ===")
    # "Fraction of the excess removed" is only defined where there WAS excess.
    # Where the shipping master already sits below its ceiling the ratio is a
    # quotient of two negatives and prints as a confident number meaning
    # nothing -- the first run of this line emitted "removed -1174.7%".
    for sub, vals, d, _ in rows:
        if vals[0] is None or d is None:
            continue
        if d > 0:
            frac = "removed %5.1f%% of it" % (100 * (1 - vals[0] / d))
        else:
            frac = "no excess to remove: shipping is already below ceiling"
        print("  %-24s e1 %+8.3f%%   shipping %+8.3f%%   %s"
              % (sub, 100 * vals[0], 100 * d, frac))
    pos = [(s, v[0], dd) for s, v, dd, _ in rows
           if v[0] is not None and dd is not None and dd > 0]
    if pos:
        print("  -- of the %d subjects that DO carry excess at the shipping setting:" % len(pos))
        print("     %d fall to zero or below at exponent 1"
              % sum(1 for _, e1, _ in pos if e1 <= 0))
        print("     %d retain some" % sum(1 for _, e1, _ in pos if e1 > 0))

    print("\n=== NEGATIVE CONTROLS: do within-ceiling subjects respond at all? ===")
    print("  ORCH: a subject within ceiling that STAYS within ceiling at exponent 16")
    print("  is a second, independent way for the mechanism to be wrong.")
    for sub, vals, d, e16 in rows:
        if sub not in CONTROLS:
            continue
        a = doc[sub]["arms"]
        mx = a.get("e16", {}).get("max")
        print("  %-24s shipping %+8.3f%%  e1 %+8.3f%%  e16 median %+9.2f%%  e16 max %+9.2f%%"
              % (sub, 100 * d, 100 * vals[0],
                 100 * e16 if e16 is not None else float("nan"),
                 100 * mx if lm.finite(mx) else float("nan")))
        crossed = (d is not None and d < 0 and
                   ((e16 is not None and e16 > 0) or (lm.finite(mx) and mx > 0)))
        print("  %-24s   -> %s" % ("", "CROSSES above its ceiling as the exponent rises"
                                   if crossed else "stays within ceiling at every arm"))

    print("\n=== WITHIN SUBJECTS, PER SITE ===")
    if not sites:
        print("  ladder-sites.json absent -- per-site monotonicity NOT MEASURED")
    tot_up = tot_n = 0
    for sub, e in sites.items():
        arms = e.get("arms", {})
        if not all(a in arms and "excess" in arms[a] for a in MONO):
            print("  %-24s incomplete" % sub)
            continue
        cols = [arms[a]["excess"] for a in MONO]
        n = len(cols[0])
        up = ok = 0
        for i in range(n):
            v = [c[i] for c in cols]
            if not all(lm.finite(x) for x in v):
                continue
            ok += 1
            up += all(v[j] < v[j + 1] for j in range(len(v) - 1))
        tot_up += up
        tot_n += ok
        print("  %-24s %2d of %2d sites rise monotonically e1<e2<e4<e8  (%d offered)"
              % (sub, up, ok, n))
    if tot_n:
        print("  %-24s %2d of %2d overall  (%.1f%%; chance would be %.1f%%)"
              % ("TOTAL", tot_up, tot_n, 100.0 * tot_up / tot_n, 100 * p_one))

    print("\n=== ZERO-SHIFT COARSE AGREEMENT: is the frozen window on the same content? ===")
    for sub, e in sites.items():
        for a in ("e8", "e16"):
            r = e.get("arms", {}).get(a, {}).get("coarse_r_zero_shift")
            if not r:
                continue
            v = [x for x in r if x is not None]
            print("  %-24s %-4s  Pearson r at zero shift: min %.4f  median %.4f  (n=%d)"
                  % (sub, a, min(v), float(np.median(v)), len(v)))

    print("\n=== WHERE THE MASTER MEETS ITS CEILING ===")
    print("  The exponent at which excess crosses zero: below it the merge returns LESS")
    print("  than its best input (real softness), above it MORE (manufactured detail).")
    print("  Interpolated in log2(exponent), which is the axis the arms are spaced on.")
    for sub, vals, d, _ in rows:
        if any(v is None for v in vals):
            print("  %-24s incomplete" % sub)
            continue
        xs = [0.0, 1.0, 2.0, 3.0]
        cross = None
        for i in range(3):
            if vals[i] <= 0 <= vals[i + 1] or vals[i] >= 0 >= vals[i + 1]:
                f0, f1 = vals[i], vals[i + 1]
                if abs(f1 - f0) > 1e-12:
                    cross = 2 ** (xs[i] + (0 - f0) / (f1 - f0) * (xs[i + 1] - xs[i]))
                break
        if cross is not None:
            print("  %-24s crosses zero at exponent %5.2f   (shipping fine-band exponent is 8)"
                  % (sub, cross))
        elif vals[0] > 0:
            print("  %-24s never crosses: already %+.2f%% ABOVE ceiling at exponent 1"
                  % (sub, 100 * vals[0]))
        else:
            print("  %-24s never crosses: still %+.2f%% BELOW ceiling at exponent 8"
                  % (sub, 100 * vals[-1]))

    print("\n=== THE SHIPPING ARM AGAINST A FLAT EXPONENT 8 ===")
    print("  The pin ramps 2 3 4 5 8 8 8 coarse->fine. This statistic lives in the fine")
    print("  bands, where the ramp has saturated at 8, so the two should agree.")
    for sub, vals, d, _ in rows:
        if vals[3] is None or d is None:
            continue
        print("  %-24s shipping %+8.3f%%   flat e8 %+8.3f%%   difference %+7.3f pp"
              % (sub, 100 * d, 100 * vals[3], 100 * (d - vals[3])))

    print("\n=== COUNTED PARTITION ===")
    n_all = len(doc)
    n_inc = sum(1 for _, v, d, _ in rows if any(x is None for x in v) or d is None)
    print("  subjects rendered                    : %d" % n_all)
    print("  monotone rising e1..e8               : %d" % n_mono)
    print("  measured but not monotone            : %d" % (n_tested - n_mono))
    print("  incomplete (an arm refused to render): %d" % n_inc)
    tot = n_mono + (n_tested - n_mono) + n_inc
    print("  TOTAL                                : %d %s"
          % (tot, "OK" if tot == n_all else "*** DOES NOT SUM ***"))
    if tot != n_all:
        raise SystemExit("partition does not sum")


if __name__ == "__main__":
    main()


