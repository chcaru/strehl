"""Re-commission the sharpness column on the HEAD masters.

respond_check.py commissioned the column on the PIN masters. Commissioning does
not transfer across binaries: it is a claim about whether this statistic can
move on THESE pixels, and HEAD's merge produces different pixels. Section 14
quotes sharp/tex on HEAD masters, so the gate has to be re-run against them or
section 14's sharpness column is uncommissioned.

Same two-sided test as respond_check.py -- planted blur must fall, planted
sharpen must rise -- with gauss(), sharpen(), fine_on() and pick_sites()
imported from the originals rather than re-expressed, so the two runs differ
only in which masters they read.

Exit is nonzero if any subject is REFUSED. A gate that always exits 0 is not a
gate; respond_check.py had that defect and it is fixed there too.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import tifffile                                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
from blotch_sweep import fine_on                                  # noqa: E402
from respond_check import gauss, sharpen, TOL                     # noqa: E402
import ab_score as S                                              # noqa: E402


def run(subject):
    ref = os.path.join(S.AB, "WHITE200", subject + ".tiff")
    tex, _ = pick_sites(tifffile.imread(ref)[..., :3].astype(np.float64))
    crops = [bl.codes(ref, y, x) for (y, x) in tex]
    base = float(np.mean([fine_on(c) for c in crops]))
    rows = []
    for r in (1, 2):
        v = float(np.mean([fine_on(gauss(c, r)) for c in crops])) / base
        rows.append(("blur r=%d" % r, v, v < 1.0 - TOL))
    for amt in (0.5, 1.0):
        v = float(np.mean([fine_on(sharpen(c, 2, amt)) for c in crops])) / base
        rows.append(("sharpen %.1f" % amt, v, v > 1.0 + TOL))
    rows2 = S.score(subject)
    span = None
    if rows2 and len(rows2) == len(S.ARMS):
        b = rows2["WHITE200"][2]
        v = [rows2[a][2] / b for a in S.ARMS]
        span = (min(v), max(v))
    return base, rows, span, len(tex)


def main():
    print("Re-commissioning the sharpness column on the HEAD masters.")
    print("A planted blur must fall >%.0f%%; a planted sharpen must rise "
          ">%.0f%%. Both required.\n" % (TOL * 100, TOL * 100))
    verdicts = {}
    for s in S.SUBJECTS:
        if not os.path.exists(os.path.join(S.AB, "WHITE200", s + ".tiff")):
            print("%-22s not rendered" % s)
            continue
        base, rows, span, nsite = run(s)
        ok = all(v[2] for v in rows)
        verdicts[s] = ok
        sp = ("arm span [%.4f, %.4f] = %.2f%%"
              % (span[0], span[1], (span[1] - span[0]) * 100)) if span else \
             "arm span n/a"
        print("%-22s %d sites  base %.4e   %s" % (s, nsite, base, sp))
        for name, v, good in rows:
            print("   %-12s %8.4f x   %s" % (name, v, "ok" if good else "FAIL"))
        print("   -> %s\n" % ("RESPONSIVE" if ok else
                              "BLIND ON THIS SUBJECT: section 14 row REFUSED"))
    print("SUMMARY")
    for s, ok in verdicts.items():
        print("  %-22s %s" % (s, "admissible" if ok else "REFUSED"))
    if not verdicts:
        return 1
    return 0 if all(verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
