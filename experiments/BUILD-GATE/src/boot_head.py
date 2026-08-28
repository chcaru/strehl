"""Confidence intervals for the section 14 blotch column.

Section 13's blotch deltas carried bootstrap CIs. Section 14's did not, and a
bare point estimate is not a finding -- the largest moves here (`bee-1-cpl`
G090 -6.94%, `flower-bud-alone-cpl` G260 -12.42%) are bigger than section 13's
knee of -3.57%, which is exactly the size range where section 13 needed an
interval to tell a move from noise.

blotch_boot.run() reads bl.SWEEP and bl.ARMS at call time, so pointing it at
the HEAD tree is a two-attribute patch rather than a second implementation of
the bootstrap. The patch is asserted to have taken effect, because a silently
ignored patch would re-measure the PIN arms and report them as HEAD.

The sufficient-statistic shortcut is re-commissioned against a direct sigma on
these masters before any interval is quoted.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import ab_score as S                                              # noqa: E402

PIN = bl.SWEEP
bl.SWEEP = S.AB
bl.ARMS = list(S.ARMS)
assert bl.SWEEP != PIN and "head" in bl.SWEEP, bl.SWEEP

import blotch_boot as B                                           # noqa: E402


def commission(subject):
    ref = os.path.join(bl.SWEEP, "WHITE200", subject + ".tiff")
    assert os.path.exists(ref), ref
    fl, _, _ = bl.pick_flat_sites(ref)
    di = B.band_image(bl.codes(ref, *fl[0]))
    st = B.blocks(di)
    direct = np.concatenate(
        [di[y:y + B.BLK, x:x + B.BLK].ravel()
         for y in range(B.MARGIN, di.shape[0] - B.MARGIN - B.BLK + 1, B.BLK)
         for x in range(B.MARGIN, di.shape[1] - B.MARGIN - B.BLK + 1, B.BLK)])
    a = float(np.sqrt(st[:, 1].sum() / st[:, 2].sum()
                      - (st[:, 0].sum() / st[:, 2].sum()) ** 2))
    b = float(direct.std())
    rel = abs(a - b) / b
    print("COMMISSION on a HEAD master: pooled %.10f vs direct %.10f, rel "
          "%.2e  %s" % (a, b, rel, "ok" if rel < 1e-9 else "FAIL"))
    if rel >= 1e-9:
        sys.exit(1)


def main():
    print("Reading arms from: %s" % bl.SWEEP)
    commission(S.SUBJECTS[0])
    print("\nPaired spatial bootstrap of the section 14 blotch column, %dpx "
          "blocks, %d resamples." % (B.BLK, B.NBOOT))
    print("Ratio vs WHITE200 (pre-fix ship) with a 95%% CI. A CI containing "
          "1.0 means the arm did not move blotch.\n")
    print("| subject | arm | blotch ratio | 95% CI | moved? |")
    print("|---|---|---:|---|---|")
    nmoved = 0
    for s in S.SUBJECTS:
        out, n = B.run(s)
        for a in bl.ARMS:
            if a == "WHITE200" or a not in out:
                continue
            m, lo, hi = out[a]
            mv = not (lo <= 1.0 <= hi)
            nmoved += 1 if mv else 0
            print("| `%s` | `%s` | %+.2f%% | [%+.2f%%, %+.2f%%] | %s |"
                  % (s, a, 100 * (m - 1), 100 * (lo - 1), 100 * (hi - 1),
                     "**yes**" if mv else "no"))
    print("\n%d of %d measured-floor arms moved blotch beyond the interval."
          % (nmoved, len(S.SUBJECTS) * (len(bl.ARMS) - 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
