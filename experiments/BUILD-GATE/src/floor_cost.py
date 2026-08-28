"""Does the measured floor's runtime cost earn itself?

ORCH measured ~1.9x (65.1 s white vs 34.3 s measured) on a quiet machine. My
renders shared the machine with a verifier and a bootstrap, so my WALL CLOCK is
contaminated. Two defences:

  1. Read the binary's OWN `total` and `folded ... s per frame` lines rather
     than my stopwatch, so at least the number is the one the binary would
     print to a user.
  2. Report the spread across subjects. Contention that varies between arms
     shows up as an inconsistent ratio; a ratio that is stable across five
     subjects rendered at different times is unlikely to be contention.

The honest reading is a RANGE with the contamination stated, not a point
estimate. ORCH's quiet-machine 1.9x is the better number and this is a check
on it, not a replacement.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ab_score as S                                              # noqa: E402


def timing(arm, subject):
    p = os.path.join(S.AB, arm, subject + ".log")
    if not os.path.exists(p):
        return None
    t = open(p, encoding="utf-8", errors="replace").read()
    tot = re.search(r"^total\s*:\s*([\d.]+) s", t, re.M)
    per = re.search(r"folded\s*:.*?\(([\d.]+) s per frame", t)
    return (float(tot.group(1)) if tot else None,
            float(per.group(1)) if per else None)


def main():
    print("Runtime cost of the measured floor. Binary's own `total`, not my")
    print("stopwatch. Machine was NOT quiet: a verifier ran alongside.\n")
    print("  %-22s %5s %9s %9s %8s | %9s"
          % ("subject", "N", "white s", "k=2.0 s", "ratio", "s/frame x"))
    rs, ps = [], []
    for s in S.SUBJECTS:
        w = timing("WHITE200", s)
        m = timing("G200", s)
        if not w or not m or w[0] is None or m[0] is None:
            print("  %-22s %s" % (s, "incomplete"))
            continue
        r = m[0] / w[0]
        pr = m[1] / w[1] if w[1] and m[1] else float("nan")
        rs.append(r)
        ps.append(pr)
        print("  %-22s %5d %9.1f %9.1f %8.2fx | %8.2fx"
              % (s, S.bl.NFRAMES[s], w[0], m[0], r, pr))
    if not rs:
        return 1
    print("\n  total ratio  : %.2fx - %.2fx  (median %.2fx)"
          % (min(rs), max(rs), float(np.median(rs))))
    print("  per-frame    : %.2fx - %.2fx  (median %.2fx)"
          % (np.nanmin(ps), np.nanmax(ps), float(np.nanmedian(ps))))
    print("\n  Spread across %d subjects rendered at different times is the"
          % len(rs))
    print("  contention check: a wide spread would mean I am timing the")
    print("  machine, not the floor probe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
