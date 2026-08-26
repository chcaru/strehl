"""Independent check of CROSS-SUBJECT comparability, on the real corpus.

WHY THIS IS WORTH MORE THAN ANOTHER SYNTHETIC ARM
--------------------------------------------------
commission_rank.py perturbs one image and checks the response. That establishes
sensitivity, but a ranking is a claim that DIFFERENT images are on a common
scale, and v2 passed four same-subject arms while being badly incomparable
across subjects. The SPARSITY arm probes that synthetically. This probes it on
the actual corpus, using information the statistic never receives.

THE IDEA
--------
The library contains near-duplicate captures of the same subject: three bees,
two wrapped-text frames, two pencils, two flower-buds. Two captures of the same
subject through the same optics should land at similar quality. So if the
statistic is comparable across subjects, near-duplicates should rank CLOSE
together, and under a statistic that is not comparable they should scatter.
`rank.py` is given only pixels and has no idea which subjects are related, so
this cannot be fitted.

THE PAIRING RULE IS MECHANICAL, AND THAT IS THE POINT
------------------------------------------------------
Groups come from a fixed prefix rule applied to FILENAMES ONLY, fixed below,
with no reference to the images or to the ranks. I had already seen the
contact sheet with ranks attached when writing this, so any grouping I chose by
eye would be unfalsifiable -- I could have unconsciously picked the pairs that
happened to sit together.

The rule therefore keeps `MSDCF` as one group of four even though I can see
that 112/113 (frost dendrites) and 109/119 (crossed straws) are two different
subjects. Splitting them would improve the result, and would be exactly the
kind of after-the-fact adjustment that makes a number meaningless. The
heterogeneous group is left in, and it counts against the statistic.

THE NULL
--------
Permute the ranking uniformly at random and recompute. Reported as the fraction
of permutations at least as tight as the observed value -- an empirical p, with
no distributional assumption.

RESULT -- AND THIS TEST FAILED TO DO ITS JOB. READ BEFORE CITING IT.
---------------------------------------------------------------------
Pre-registered rule, all five groups: v3 `resolved` gap 6.000, v2 8.250, p95
7.750, chance 9.000; v3 p = 0.054, which does not clear the 0.01 bar. Reported
as a miss.

`MSDCF` is the reason its p is weak: ranks [7, 8, 20, 21], two tight pairs
thirteen apart. `MSDCF` is not a subject name, it is Sony's DCIM directory
suffix, so grouping on it groups by CAMERA FOLDER and asserts nothing about
subject identity. Excluding it on that ground is the sensitivity arm.

And the sensitivity arm is what discredits this test as evidence for v3:

                     all groups        MSDCF excluded
    v3 resolved        6.000            3.000  p=0.005
    v2 retracted       8.250            2.833  p=0.003   <- TIGHTEST
    p95 shipped        7.750            3.167  p=0.006
    chance             9.000            9.000

All three pass once the folder-code group is dropped, and the RETRACTED v2 --
the statistic independently shown to rank an award-quality frame 12th -- comes
out tightest of the three. The ordering between statistics REVERSES between the
two arms, so it is not a robust discriminator in either direction.

WHY, in hindsight, and it is a design fault in this test rather than bad luck:
near-duplicate captures of one subject share their darkness, their sparsity and
their texture. Those are precisely the properties every candidate statistic
keys on, so ANY content-based statistic places them together, including a badly
incomparable one. The test is confounded by construction: what makes two frames
duplicates is what makes them score alike.

SO THIS FILE ESTABLISHES ONLY that the ranking is not random, which is a weak
claim that v2 and the shipped proxy satisfy equally. It is NOT evidence for v3
over v2 and must not be cited as such. The discriminating evidence is the
SPARSITY arm in commission_rank.py, which is mechanistic and quantitatively
predicted, plus looking at the pictures.

Kept because a null result on one's own instrument is worth more recorded than
deleted -- and because the next person to reach for "duplicates should rank
together" as a validation should find out here that it does not separate
statistics.
"""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

# Fixed BEFORE looking at any rank; derived from filenames alone.
GROUP_RULES = [
    ("bee", lambda s: s.startswith("bee-")),
    ("wrapped-text", lambda s: s.startswith("wrapped-text")),
    ("pencil", lambda s: s.startswith("pencil-")),
    ("flower-bud", lambda s: s.startswith("flower-bud")),
    ("MSDCF", lambda s: s.endswith("MSDCF")),
]


def group_of(subject: str) -> str | None:
    for name, pred in GROUP_RULES:
        if pred(subject):
            return name
    return None


def spread(ranks: dict[str, int], groups: dict[str, list[str]]) -> float:
    """Mean absolute pairwise rank difference within groups. Lower = tighter."""
    diffs = [abs(ranks[a] - ranks[b])
             for members in groups.values()
             for a, b in combinations(members, 2)]
    return float(np.mean(diffs)) if diffs else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ranking", type=Path, required=True)
    ap.add_argument("--column", default="resolved",
                    help="score column to order by; use v2_retracted to test the "
                         "retracted statistic on the same corpus")
    ap.add_argument("--trials", type=int, default=200000)
    ap.add_argument("--seed", type=int, default=20260826)
    ap.add_argument("--exclude-group", action="append", default=[],
                    help="drop a group as a SENSITIVITY arm. Both the "
                         "pre-registered result and the excluded one must be "
                         "reported together; this switch is not a way to "
                         "improve a number after seeing it.")
    args = ap.parse_args()

    with args.ranking.open(newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh, delimiter="\t")
                if r.get("rank", "-") != "-"]
    if args.column not in rows[0]:
        raise SystemExit(f"no column {args.column!r}; have {sorted(rows[0])}")

    ordered = sorted(rows, key=lambda r: -float(r[args.column]))
    ranks = {r["subject"]: i + 1 for i, r in enumerate(ordered)}
    n = len(ordered)

    groups: dict[str, list[str]] = {}
    ungrouped = []
    for s in ranks:
        g = group_of(s)
        if g is None:
            ungrouped.append(s)
        else:
            groups.setdefault(g, []).append(s)
    groups = {k: v for k, v in groups.items() if len(v) > 1}
    for g in args.exclude_group:
        if g in groups:
            dropped = groups.pop(g)
            ungrouped.extend(dropped)
            print(f"SENSITIVITY ARM: group {g!r} excluded ({len(dropped)} subjects)")
        else:
            raise SystemExit(f"--exclude-group {g!r}: no such group")

    npairs = sum(len(list(combinations(v, 2))) for v in groups.values())
    grouped_n = sum(len(v) for v in groups.values())
    print(f"subjects {n}   grouped {grouped_n}   ungrouped {len(ungrouped)}   "
          f"pairs {npairs}")
    assert grouped_n + len(ungrouped) == n, "group counts do not partition"

    for g, members in sorted(groups.items()):
        rs = sorted(ranks[m] for m in members)
        print(f"  {g:14s} ranks {rs}")

    obs = spread(ranks, groups)
    # Expected |i-j| for two distinct ranks drawn uniformly from 1..n is (n+1)/3
    print(f"\nobserved mean within-group rank gap : {obs:.3f}")
    print(f"chance expectation (n+1)/3          : {(n + 1) / 3:.3f}")

    rng = np.random.default_rng(args.seed)
    subjects = list(ranks)
    hits = 0
    for _ in range(args.trials):
        perm = rng.permutation(n) + 1
        shuffled = {s: int(perm[i]) for i, s in enumerate(subjects)}
        if spread(shuffled, groups) <= obs:
            hits += 1
    p = (hits + 1) / (args.trials + 1)
    print(f"permutation null ({args.trials} trials): p = {p:.5f}  "
          f"({hits} at least as tight)")
    print("\n" + ("TIGHTER THAN CHANCE: the ranking is not random. NOTE this "
                  "does NOT discriminate between statistics -- the retracted "
                  "v2 passes this too. See the module docstring."
                  if p < 0.01 else
                  "NOT DISTINGUISHABLE FROM CHANCE under this grouping."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
