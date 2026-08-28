"""Confidence intervals for the per-band scale sweep's blotch column.

The point estimates in `scale_score.py` are not findings on their own. Section
13's knee was -3.57% and section 14's largest interval-backed move was -8.38%,
so any blotch claim in that size range needs an interval to separate a move
from resampling noise.

WHY THE JUNCTION. `blotch_boot.run()` hardcodes the arm name `WHITE200` as
both the flat-site reference and the ratio denominator. Forking it would mean
a second copy of a bootstrap that has already been commissioned against a
direct sigma, so instead the null baseline is exposed inside the scale tree
under that name by a directory junction. The bootstrap then runs verbatim, and
because a junction is not a copy it is guaranteed to read the same bytes that
`scale_score.py` measured -- there is no second set of TIFFs to drift.

The junction target is asserted, not assumed: a junction pointing somewhere
else would silently produce a beautifully-formatted table of the wrong ratios.
"""
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import scale_score as S                                           # noqa: E402

LINK = os.path.join(S.SCALE, "WHITE200")


def ensure_link():
    if not os.path.exists(LINK):
        subprocess.run(["cmd", "/c", "mklink", "/J", LINK, S.BASE],
                       check=True, capture_output=True)
    real = os.path.realpath(LINK).lower()
    assert real == os.path.realpath(S.BASE).lower(), \
        "null-baseline junction resolves to %s, not %s" % (real, S.BASE)
    print("null baseline exposed as WHITE200 -> %s" % os.path.realpath(LINK))


ensure_link()
PIN = bl.SWEEP
bl.SWEEP = S.SCALE
bl.ARMS = ["WHITE200"] + list(S.ARMS)
assert bl.SWEEP != PIN and "scale" in bl.SWEEP, bl.SWEEP

import blotch_boot as B                                           # noqa: E402


def commission(subject):
    """Re-commission the sufficient-statistic shortcut on THESE masters.

    Commissioning does not transfer across pixel sets; a shortcut that is
    exact on one set of images is not thereby exact on another.
    """
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
    print("COMMISSION on a scale-sweep master: pooled %.10f vs direct %.10f, "
          "rel %.2e  %s" % (a, b, rel, "ok" if rel < 1e-9 else "FAIL"))
    if rel >= 1e-9:
        sys.exit(1)


def main():
    subs = sys.argv[1:] or S.SUBJECTS
    print("Reading arms from: %s" % bl.SWEEP)
    commission(subs[0])
    print("\nPaired spatial bootstrap of the blotch column, %dpx blocks, %d "
          "resamples." % (B.BLK, B.NBOOT))
    print("Ratio vs the NULL arm (1,1,1,1,1,1,1 == the G200 masters) with a "
          "95%% CI.")
    print("A CI containing 1.0 means the arm did not move blotch.\n")
    print("| subject | arm | scale | blotch ratio | 95% CI | moved? |")
    print("|---|---|---|---:|---|---|")
    nmoved = ntot = 0
    for s in subs:
        out, n = B.run(s)
        for a in bl.ARMS:
            if a == "WHITE200" or a not in out:
                continue
            m, lo, hi = out[a]
            mv = not (lo <= 1.0 <= hi)
            ntot += 1
            nmoved += 1 if mv else 0
            print("| `%s` | `%s` | `%s` | %+.2f%% | [%+.2f%%, %+.2f%%] | %s |"
                  % (s, a, S.SCALES[a], 100 * (m - 1), 100 * (lo - 1),
                     100 * (hi - 1), "**yes**" if mv else "no"))
    print("\n%d of %d arms moved blotch beyond the interval." % (nmoved, ntot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
