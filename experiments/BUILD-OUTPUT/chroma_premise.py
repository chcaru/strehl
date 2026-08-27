"""chroma_premise.py -- is chroma actually worse than luma?

ORCH's hypothesis rests on a stated premise: "Chroma is worse than luma in all
four chroma cells."  The premise is testable against the very table it was drawn
from, so it is tested here before any mechanism is investigated.

SOURCE.  docs/research/V-REVIEW-noise-verification.md, section "The cells",
lines 544-551, SHIP-V4 column with 95% bootstrap intervals.

CONVENTION, quoted from that document's section 8 so the direction cannot be
guessed: "Ratio of medians, COMPARATOR OVER STREHL".  A ratio ABOVE 1.0 means
strehl is quieter.  A HIGHER ratio is therefore BETTER for strehl, and "chroma
is worse than luma" means the chroma ratio is LOWER than the luma ratio for the
same comparator.

TEST.  Each chroma cell against its OWN comparator's luma cell.  Comparing
across comparators would be meaningless: the denominators differ.

WHAT THIS TEST CAN AND CANNOT SAY.  The two intervals share a denominator (the
same strehl render, the same tiles), so they are positively correlated and
comparing them for overlap is CONSERVATIVE: disjoint intervals prove a
difference, overlapping ones prove nothing either way.  A paired resample on the
tile-level data would be sharper, and that data is not published in the table.
Stated so the negative cell is not over-read.
"""

import sys

# (comparator, channel, point, lo, hi)
CELLS = [
    ("enfuse", "luma", 1.618, 1.511, 1.709),
    ("enfuse", "B-Y", 1.606, 1.525, 1.702),
    ("enfuse", "R-Y", 1.813, 1.717, 1.966),
    ("focus-stack", "luma", 1.475, 1.400, 1.514),
    ("focus-stack", "B-Y", 1.640, 1.550, 1.710),
    ("focus-stack", "R-Y", 1.661, 1.592, 1.755),
]


def adjudicate(cells, label):
    lum = {c: (p, lo, hi) for c, ch, p, lo, hi in cells if ch == "luma"}
    print(f"\n=== {label} ===")
    print(f"{'comparator':<14}{'chan':<6}{'ratio':>8}{'luma':>8}{'delta':>9}"
          f"{'%':>8}  verdict")
    print("-" * 78)
    worse = better = tied = 0
    for comp, ch, p, lo, hi in cells:
        if ch == "luma":
            continue
        lp, llo, lhi = lum[comp]
        d = p - lp
        pct = 100.0 * d / lp
        disjoint = lo > lhi or hi < llo
        if d < 0 and disjoint:
            v, worse = "WORSE than luma (intervals disjoint)", worse + 1
        elif d > 0 and disjoint:
            v, better = "BETTER than luma (intervals disjoint)", better + 1
        else:
            v, tied = "not distinguishable (intervals overlap)", tied + 1
        print(f"{comp:<14}{ch:<6}{p:>8.3f}{lp:>8.3f}{d:>+9.3f}{pct:>+7.1f}%  {v}")
    tot = worse + better + tied
    print(f"\n  chroma cells WORSE than their own luma : {worse}")
    print(f"  chroma cells BETTER than their own luma: {better}")
    print(f"  not distinguishable                    : {tied}")
    print(f"  {'-' * 39}: {tot} == {len([c for c in cells if c[1] != 'luma'])} chroma cells")
    return worse, better, tied


def main():
    worse, better, tied = adjudicate(CELLS, "PUBLISHED SHIP-V4 CELLS")
    premise = (worse == 4)
    print(f"\n  PREMISE 'chroma is worse than luma in all four chroma cells': "
          f"{'HOLDS' if premise else 'REFUTED'}")

    # POTENCY.  A script that can only ever print REFUTED is worth nothing.
    # Plant a table in which chroma really IS worse and require it to say so.
    print("\n" + "=" * 78)
    print("POTENCY CONTROL: plant a corpus where chroma IS worse, require detection")
    planted = []
    for comp, ch, p, lo, hi in CELLS:
        if ch == "luma":
            planted.append((comp, ch, p, lo, hi))
        else:
            # push each chroma cell far below its luma cell, interval and all
            planted.append((comp, ch, p - 0.6, lo - 0.6, hi - 0.6))
    pw, pb, pt = adjudicate(planted, "PLANTED (chroma genuinely worse)")
    potent = (pw == 4)
    print(f"\n  planted premise detected: {'YES' if potent else 'NO'} "
          f"({pw}/4 cells convicted)")

    print("\n" + "=" * 78)
    if not potent:
        print("  INVALID -- the test cannot detect the effect it was built for.")
        return 1
    print("  Test is potent (convicts a planted effect) and returns REFUTED on")
    print("  the real cells: 3 of 4 chroma cells are BETTER than their own luma")
    print("  cell with disjoint intervals; the 4th is 0.7% lower and not")
    print("  distinguishable. The asymmetry the mechanism explains is not there.")
    return 0 if not premise else 1


if __name__ == "__main__":
    raise SystemExit(main())
