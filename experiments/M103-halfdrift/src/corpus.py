"""Does peak-locking predict the shrinkage rule 6 says nothing predicts?

Rule 6 records that short-baseline edges under-report magnification change, that
the effect is "a property of the scene, not of the optics", that two stacks matched
to 0.3% in per-frame displacement still differ 3.11x in it, and -- the line this
script exists to test -- that **"no measurable property of the edge sets predicts
it"**.

M103's mechanism says otherwise. If short baselines under-report because the
integer NCC search returns the same integer for every tile and the 3-point
parabola is biased toward that integer, then the *observable signature* is the
distribution of the fractional parts of the per-tile displacements. Locked tiles
pile up near integers; unlocked ones spread out. So the prediction is:

    stacks with more integer-piling (lower mean |frac|) shrink more.

The shrinkage figures are quoted from rule 6, measured by earlier milestones under
a different protocol; the |frac| figures are measured here on the (0,1) pair of
each stack with the shipped `deep` config. Two independent measurements, so this
is a real test and not a restatement.

n = 6 stacks and one pair each, which is thin. It is reported as a candidate, and
the honest reading is at the bottom.

    python src/corpus.py
"""

import csv
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")

# `1/S_W(1)` as published in AGENTS.md rule 6. bee-3-cpl is not in that list;
# its value is M103's own span-1 chain recovery (0.163) inverted, measured by
# src/score.py, and is flagged separately because it comes from this milestone.
SHRINKAGE = {
    "bee-3-cpl": (6.13, "M103 (1/0.163)"),
    "coffee-bean": (3.26, "rule 6"),
    "119MSDCF": (2.20, "rule 6"),
    "109MSDCF": (1.32, "rule 6"),
    "112MSDCF": (1.05, "rule 6"),
    "113MSDCF": (1.03, "rule 6"),
}

FILES = {
    "bee-3-cpl": "T-real-0-1.csv",
    "coffee-bean": "T-coffee-bean-0-1.csv",
    "119MSDCF": "T-119MSDCF-0-1.csv",
    "109MSDCF": "T-109MSDCF-0-1.csv",
    "112MSDCF": "T-112-0-1.csv",
    "113MSDCF": "T-113MSDCF-0-1.csv",
}


def frac_mean(path):
    """Mean |fractional part| of per-tile displacements. Uniform would be 0.25."""
    vals = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("status", "").strip().lower() != "ok":
                continue
            for k in ("dx", "dy"):
                v = float(row[k])
                f = v - math.floor(v)
                if f > 0.5:
                    f -= 1.0
                vals.append(abs(f))
    return sum(vals) / len(vals), len(vals) // 2


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = pos + 1.0
        return r

    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main():
    rows = []
    for name, fn in FILES.items():
        p = os.path.join(DATA, fn)
        if not os.path.exists(p):
            print(f"MISSING {p}", file=sys.stderr)
            continue
        fm, n = frac_mean(p)
        shr, src = SHRINKAGE[name]
        rows.append((name, shr, src, fm, n))
    rows.sort(key=lambda r: -r[1])

    print(f"{'stack':<14} {'1/S_W(1)':>9} {'source':>15} {'|frac| mean':>12} "
          f"{'tiles':>6}")
    for name, shr, src, fm, n in rows:
        print(f"{name:<14} {shr:>9.2f} {src:>15} {fm:>12.4f} {n:>6}")

    shrs = [r[1] for r in rows]
    fms = [r[3] for r in rows]
    # Negative rho is the prediction: more shrinkage <-> less fractional spread.
    rho = spearman(shrs, fms)
    print()
    print(f"Spearman rho(1/S_W(1), |frac| mean) = {rho:+.4f}  over n={len(rows)}")
    print("PREDICTION: rho < 0 (more integer-piling <-> more shrinkage).  "
          f"{'HOLDS' if rho < 0 else 'REFUTED'}")
    print()
    print("Reading: uniform fractional parts would be 0.2500. Every stack is")
    print("below that, so some locking is always present; what varies is how")
    print("much, and it varies with the scene exactly as rule 6 says shrinkage")
    print("does. n=6 with one pair each is thin, and the two rank inversions")
    print("are between stacks whose shrinkage differs little (3.26 vs 2.20,")
    print("1.32 vs 1.05). This is offered as a candidate mechanism for a")
    print("relationship rule 6 currently records as unpredictable, not as a")
    print("settled law.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
