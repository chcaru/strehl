"""One table per subject: gate setting against BOTH axes the product is judged on.

Sharpness is the per-site ceiling ratio (ORCH's orch_sharp1to1.patch_gain,
imported through ceiling.py and proved equal to it in C1). Noise is acuity.py's
flat-tile high-pass rms, which is the already-commissioned instrument for that
axis -- ORCH asked for reuse rather than a third statistic.

WHY BOTH ARE PRINTED SIDE BY SIDE RATHER THAN COMBINED INTO A SCORE

A single figure of merit would have to weight sharpness against noise, and the
whole point of the head-to-head is that the two currencies have very different
exchange rates right now: the product is 1.54-1.76x cleaner than enfuse and
0.977 on sharpness, so a point of sharpness is worth far more than a point of
noise. Baking a weight into the statistic would hide that judgement inside a
number. It is printed as two columns so the trade is visible and arguable.

The tiles are NOT shared between the two axes and that is deliberate: the
ceiling ratio is measured on the three most textured sites, where detail lives,
and the noise statistic on the flattest decile, where noise lives. A statistic
that measured both on the same tiles would be dominated by whichever the tiles
happened to contain.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ceiling import score                                        # noqa: E402
from acuity import luma as aluma, tiles, stats                   # noqa: E402

SWEEP = r"C:\dev\strehl-out\BUILD-GATE\sweep"
CEIL = r"C:\dev\strehl-out\BUILD-GATE\ceil"

# (arm, k, sigma) -- sigma = (k-1)/0.39, the documented false-positive margin.
ARMS = [
    ("WHITE200", "2.0*", None),
    ("G100", "1.0", 0.00),
    ("G140", "1.4", 1.03),
    ("G170", "1.7", 1.79),
    ("G200", "2.0", 2.56),
    ("G300", "3.0", 5.13),
    ("G400", "4.0", 7.69),
]


def main():
    subject = sys.argv[1]
    cz = np.load(os.path.join(CEIL, "%s.npz" % subject), allow_pickle=True)
    ref = os.path.join(SWEEP, "G200", "%s.tiff" % subject)
    # Tiles chosen ONCE from a fixed reference arm, so no arm can move the
    # statistic by moving the selection.
    flat_idx, sharp_idx = tiles(aluma(ref))

    base_arm = "WHITE200"
    rows = []
    for arm, k, sig in ARMS:
        p = os.path.join(SWEEP, arm, "%s.tiff" % subject)
        if not os.path.exists(p):
            rows.append((arm, k, sig, None, None, None))
            continue
        r, n, _, _ = score(p, cz)
        f, s = stats(aluma(p), flat_idx, sharp_idx)
        rows.append((arm, k, sig, r, f, s))

    b = next(x for x in rows if x[0] == base_arm)
    print("\n=== %s : %d/%d frames (COMPLETE), %d sites, ceiling from the whole bracket ==="
          % (subject, int(cz["nframes"]), int(cz["ntotal"]), len(cz["sites"])))
    print("baseline for the deltas is %s = the SHIPPING configuration\n" % base_arm)
    print("%-9s %6s %7s   %9s %9s   %9s %9s   %9s"
          % ("arm", "k", "sigma", "SHARP", "d sharp", "NOISE", "d noise", "sharp/noise"))
    for arm, k, sig, r, f, s in rows:
        if r is None:
            print("%-9s %6s %7s   %9s" % (arm, k, "-", "NOT RENDERED"))
            continue
        dr = 100.0 * (r / b[3] - 1.0)
        df = 100.0 * (f / b[4] - 1.0)
        # A crude exchange rate, printed but not gated on: how many percent of
        # sharpness is bought per percent of noise given up, relative to the
        # shipping arm. Undefined when noise does not move.
        ex = (dr / df) if abs(df) > 0.5 else float("nan")
        print("%-9s %6s %7s   %9.4f %+8.2f%% %9.2f %+8.2f%%   %9s"
              % (arm, k, ("%.2f" % sig) if sig is not None else "-",
                 r, dr, f, df, ("%+.2f" % ex) if np.isfinite(ex) else "-"))
    print("\n* WHITE200 is k=2.0 with the PRE-FIX white-noise floor: measured "
          "pixel-identical to the shipped master.")


if __name__ == "__main__":
    main()
