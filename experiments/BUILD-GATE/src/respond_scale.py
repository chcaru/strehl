"""Re-commission the sharpness column on the per-band scale masters.

Commissioning is a claim about whether a statistic can move on a specific set
of pixels, so it does not transfer across pixel sets. Section 14 commissioned
`sharp/tex` on the WHITE200 masters; this sweep measures a different baseline
(G200, the null) and different arms, so the column is uncommissioned here
until this runs.

This matters more than usual for this sweep, because the result being tested
is that sharpness stays FLAT while blotch falls. "Flat" is exactly what a dead
statistic also reports. The planted blur and planted sharpen are what
distinguish a column that could have moved and did not from a column that
cannot move at all.

gauss(), sharpen(), fine_on() and pick_sites() are imported from the originals
rather than re-expressed, so this differs from the section 14 run only in
which masters it reads.
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
import scale_score as S                                           # noqa: E402


def run(subject):
    ref = S.arm_path("NULL", subject)
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
    return base, rows, len(tex)


def main():
    subs = sys.argv[1:] or S.SUBJECTS
    print("Re-commissioning the sharpness column on the SCALE-SWEEP masters.")
    print("Sites and baseline come from the NULL arm (the G200 masters).")
    print("A planted blur must fall >%.0f%%; a planted sharpen must rise "
          ">%.0f%%. Both required.\n" % (TOL * 100, TOL * 100))
    verdicts = {}
    for s in subs:
        if not os.path.exists(S.arm_path("NULL", s)):
            print("%s: baseline missing" % s)
            continue
        base, rows, nt = run(s)
        ok = all(p for _, _, p in rows)
        verdicts[s] = ok
        print("%s  (%d textured sites, base %.6f)  %s"
              % (s, nt, base, "ADMISSIBLE" if ok else "REFUSED"))
        for name, v, p in rows:
            print("    planted %-12s -> %8.4f x   %s"
                  % (name, v, "ok" if p else "FAIL"))
        print()
    if not verdicts:
        print("no subjects scored -- nothing was commissioned")
        return 1
    bad = [s for s, ok in verdicts.items() if not ok]
    print("%d/%d subjects ADMISSIBLE." % (len(verdicts) - len(bad),
                                          len(verdicts)))
    if bad:
        print("REFUSED: %s -- the sharpness column may not be quoted on "
              "these subjects." % ", ".join(bad))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
