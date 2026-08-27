"""Which way does subsampling the source set move the ratio? Measure it.

I told ORCH that a minimum over a small sample is "biased high, which
manufactures excess", and ORCH adopted that reasoning. The first half is true
and the second half is backwards: a minimum biased HIGH is a LARGER
denominator, so master/min comes out SMALLER. Subsampling SUPPRESSES measured
excess. Every subsampled ratio in RESULT.md is therefore a LOWER bound on its
full-stack value, which is what section 6.1 already said and what my summary
contradicted.

This settles it on real data rather than by argument. coffee-bubbles is the
only subject whose full stack was measured entire, so it is the only place the
subsampling bias can be measured directly instead of bounded: draw random
subsets of the 19 real frames and compare against the known full-19 answer.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_bubbles as B  # noqa: E402
import vn_lib as L  # noqa: E402
import vn_mech as M  # noqa: E402


def main():
    mlum, flums = M.load()
    per = np.array([B.nband(f).std() for f in flums])
    m = float(B.nband(mlum).std())
    full = m / per.min()
    rng = np.random.default_rng(5)
    print("")
    print("SUBSAMPLING BIAS  coffee-bubbles, measured on the real 19 frames")
    print("  full-stack ratio, all 19 sources: %.4fx" % full)
    print("")
    print("  %6s %10s %10s %10s %9s" % ("k", "median", "p10", "p90", "vs full"))
    rows = []
    for k in (3, 6, 12, 17, 19):
        if k >= len(per):
            r = np.array([full])
        else:
            r = np.array([m / per[rng.choice(len(per), k, replace=False)].min()
                          for _ in range(4000)])
        rows.append((k, float(np.median(r))))
        print("  %6d %9.4fx %9.4fx %9.4fx %8.3f"
              % (k, np.median(r), np.percentile(r, 10), np.percentile(r, 90),
                 float(np.median(r)) / full))
    print("")
    lo = [r for kk, r in rows if kk < len(per)]
    print("  Every subsample median is at or below the full-stack ratio:")
    print("  %s" % ("yes" if all(v <= full + 1e-9 for v in lo) else "NO"))
    print("  A 12-of-19 draw understates coffee-bubbles by %.1f%%."
          % (100 * (1 - rows[2][1] / full)))
    print("")
    print("  Direction: subsampling SUPPRESSES the measured excess. The deep-")
    print("  stack subjects' figures are LOWER bounds, so bee-2-cpl's +16%% is")
    print("  if anything understated, not manufactured.")
    L.jdump(dict(full=full, rows=rows), os.path.join(B.OUT, "subsample.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
