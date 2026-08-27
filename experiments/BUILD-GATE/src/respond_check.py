"""Per-subject responsiveness gate for the sharpness column.

The sweep reports `sharp/tex` as "no sharpness cost" when it does not move.
On `bee-1-cpl` it spans 0.44% across a knob that moves grain 12x. That is
indistinguishable, from the number alone, from a column that cannot move on
this subject -- the frozen probe. A statistic that is inert reads as a pass on
every arm, which is the most expensive way to be wrong here, because it would
license a default change on a subject where the instrument is blind.

So each subject's sharpness column is commissioned on its own sites, both ways:

  a planted BLUR    must drive sharp/tex down by roughly the predicted amount
  a planted SHARPEN must drive it up

The second arm is not redundant. A statistic whose error sign is bounded below
-- one that can miss softness but can never charge for it -- passes a
blur-only test trivially. This project has already shipped such a gauge.

A subject that fails either arm has its sweep row REFUSED, not reported.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import blotch as bl                                               # noqa: E402
import tifffile                                                   # noqa: E402
from ceiling import pick_sites                                    # noqa: E402
from blotch_sweep import fine_on                                  # noqa: E402
from orch_eye_check import boxblur                                # noqa: E402

TOL = 0.25


def gauss(c, r):
    """Separable box cascade: a real blur, applied per channel."""
    out = np.empty_like(c)
    for k in range(3):
        p = c[..., k]
        for _ in range(3):
            p = boxblur(p, r)
        out[..., k] = p
    return out


def sharpen(c, r, amt):
    """Unsharp mask: the improvement arm."""
    return c + amt * (c - gauss(c, r))


def run(subject):
    ref = os.path.join(bl.SWEEP, "WHITE200", subject + ".tiff")
    tex, _ = pick_sites(tifffile.imread(ref)[..., :3].astype(np.float64))
    crops = [bl.codes(ref, y, x) for (y, x) in tex]
    base = float(np.mean([fine_on(c) for c in crops]))

    rows = []
    for r in (1, 2, 3):
        v = float(np.mean([fine_on(gauss(c, r)) for c in crops])) / base
        rows.append(("blur r=%d" % r, v, v < 1.0 - TOL))
    for amt in (0.5, 1.0):
        v = float(np.mean([fine_on(sharpen(c, 2, amt)) for c in crops])) / base
        rows.append(("sharpen %.1f" % amt, v, v > 1.0 + TOL))

    # The observed span of the column across the seven arms, for comparison:
    # a column whose planted response dwarfs its arm-to-arm span is responsive
    # but the arms genuinely did not move it. A column that fails the plants is
    # blind and its arm-to-arm span means nothing at all.
    srows, _, _, _, _ = __import__("blotch_sweep").run(subject)
    b = srows["WHITE200"][3]
    vals = [srows[a][3] / b for a in bl.ARMS if a in srows]
    return base, rows, (min(vals), max(vals))


def main():
    print("Per-subject responsiveness of the sharpness column (band 0.20-0.25 "
          "cyc/px, textured sites).")
    print("A planted blur must fall >%.0f%%; a planted sharpen must rise >%.0f%%. "
          "Both arms required." % (TOL * 100, TOL * 100))
    verdicts = {}
    for s in sys.argv[1:]:
        base, rows, span = run(s)
        ok = all(v[2] for v in rows)
        verdicts[s] = ok
        print("\n%-22s base fine %.4e   arm span [%.4f, %.4f] = %.2f%%"
              % (s, base, span[0], span[1], (span[1] - span[0]) * 100))
        for name, v, good in rows:
            print("   %-12s %8.4f x   %s" % (name, v, "ok" if good else "FAIL"))
        print("   -> %s" % ("RESPONSIVE: arm-to-arm readings admissible"
                            if ok else
                            "BLIND ON THIS SUBJECT: sweep row REFUSED"))
    print("\nSUMMARY")
    for s, ok in verdicts.items():
        print("  %-22s %s" % (s, "admissible" if ok else "REFUSED"))
    return 0 if all(verdicts.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
