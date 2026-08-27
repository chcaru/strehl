"""resolve_min.py -- resolve the one cross-check disagreement, do not wave at it.

crosscheck.py reproduced V-REVIEW's published lanczos max (36.9970 vs 36.997),
median (13.4237 vs 13.424), and both zero-kernels exactly, but got min 3.6714
where they published 1.962.

Hypothesis, from reading their code rather than guessing: `vh_run_hull.py:64-71`
aggregates `max_excess` ONLY -- rim ABOVE the local hull, i.e. bright rim.  I
aggregate `max(excess, deficit)`, which also charges dark rim below the hull.
If that is the whole difference, then for the master that sets my min, my
max_excess must equal their 1.962 and my max_deficit must be the 3.6714.

That is a falsifiable prediction with a single number in it.  If it misses, one
of the two implementations is wrong and DELIVER-V5 stops until it is found.
"""
import sys

import numpy as np
import tifffile

import rimlib
from geom import masters

PUBLISHED_MIN = 1.962
TARGET = "flowers-cpl"


def main():
    p = dict(masters()).get(TARGET)
    if p is None:
        print("FAIL: master %s not found" % TARGET)
        return 1
    a8 = rimlib.to8(tifffile.imread(p))
    mx_e = mx_d = 0.0
    for c in range(a8.shape[2]):
        plane = np.ascontiguousarray(a8[..., c])
        from crosscheck import reduce_f
        out = reduce_f(plane, "lanczos")
        exc, dfc = rimlib.hull_window(plane, out, support=18)
        mx_e = max(mx_e, float(exc.max()))
        mx_d = max(mx_d, float(dfc.max()))
    print("%s  lanczos:" % TARGET)
    print("   max_excess  (bright rim, ABOVE the hull) %8.4f DN   <- their column" % mx_e)
    print("   max_deficit (dark rim,   BELOW the hull) %8.4f DN   <- also manufactured" % mx_d)
    print("   max of both                              %8.4f DN   <- my column" % max(mx_e, mx_d))
    print("")
    ok_e = abs(mx_e - PUBLISHED_MIN) <= max(0.01, 0.01 * PUBLISHED_MIN)
    ok_d = abs(max(mx_e, mx_d) - 3.6714) <= 0.01
    print("  [%s] prediction A: my max_excess %.4f == their published min %.3f"
          % ("PASS" if ok_e else "FAIL", mx_e, PUBLISHED_MIN))
    print("  [%s] prediction B: my reported 3.6714 is the DEFICIT, not the excess"
          % ("PASS" if ok_d and mx_d > mx_e else "FAIL"))
    good = ok_e and ok_d and mx_d > mx_e
    print("\nVERDICT: %s" % (
        "the disagreement is DEFINITIONAL, not an implementation error: they "
        "publish bright rim, I publish bright-or-dark. Both implementations are "
        "correct and agree on the quantity they share."
        if good else
        "PREDICTION MISSED -- the two implementations genuinely disagree and no "
        "DELIVER-V5 number may be trusted until it is found."))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
