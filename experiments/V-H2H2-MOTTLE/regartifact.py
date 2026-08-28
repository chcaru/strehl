"""How much does an unregistered comparison distort a band statistic?

ORCH asked all three lanes what a COMMON-CAUSE ARTIFACT would look like, given
that two converging lanes share a binary, a corpus and a band-energy statistic.
This lane found a candidate the hard way: there is no flag to pin the merge's
alignment reference, so the merged output's PIXEL GRID is a function of which
frames were in the stack. Two strehl renders of one subject that differ only in
frame set landed up to (-5,+12) px apart.

Every cross-arm comparison in this project is therefore made between images that
may not share a grid -- strehl against enfuse, N=63 against N=32, arm a against
arm b. The question is how much that costs, and the answer is not one number,
because it depends on the SHAPE of the statistic:

  RATIO OF INDEPENDENT BAND ENERGIES. Each arm's own band sd is computed from
  itself. A global shift moves which content a fixed ROI covers, but a 12 px
  shift on a 384 px ROI changes 3% of the content, so the effect should be small.
  If it is, band-energy ratios across arms survive misregistration and the two
  lanes' headline numbers are not artifacts of it.

  ANYTHING BUILT ON A DIFFERENCE. A - B, a half-difference, a residual, a
  correlation. Here a shift puts every EDGE in the image into the difference, and
  edges are exactly where the band energy lives. This should be catastrophic.

Reporting one number for "the registration artifact" would be wrong in one
direction or the other. Both are measured here, on the first staging's renders,
which are still on disk and carry the large offsets that make the effect visible.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import decomplib  # noqa: E402
import nscene  # noqa: E402

OLD = r"C:\dev\strehl-out\V-H2H2\ladder\out"
SITE, PAD = 384, 24
BANDS = [("5-15", 5, 15), ("20-60", 20, 60), ("40-120", 40, 120)]
SITES = [(2520, 984), (3288, 600), (984, 5208)]


def load(name, expo):
    return bandlib.display(tifffile.imread(os.path.join(OLD, name))[..., 1]
                           .astype(np.float64), expo)


def main():
    ref16 = tifffile.imread(os.path.join(OLD, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(ref16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    del ref16
    print("display gain %.4f (one gain, every arm)\n" % expo)

    ga = load("n149a.tiff", expo)
    gb = load("n149b.tiff", expo)

    y, x = SITES[0]
    off, resid, edge = nscene.integer_align(ga[y:y + SITE, x:x + SITE],
                                            gb[y - PAD:y + SITE + PAD,
                                               x - PAD:x + SITE + PAD], PAD)
    if edge:
        sys.exit("alignment search saturated at +-%d" % PAD)
    print("arm b relative to arm a: integer offset %s, residual %.3f codes" % (off, resid))
    if off == (0, 0):
        print("  the arms already share a grid; this measurement has nothing to show.")
        return

    print("\n=== A: ratio of INDEPENDENT band energies (each arm scored on itself) ===")
    print("  %-8s %12s %12s %10s %10s" % ("band", "unreg ratio", "reg ratio",
                                          "change", "verdict"))
    for label, lo, hi in BANDS:
        u, r = [], []
        for (yy, xx) in SITES:
            ca = ga[yy:yy + SITE, xx:xx + SITE]
            cu = gb[yy:yy + SITE, xx:xx + SITE]
            cr = gb[yy + off[0]:yy + off[0] + SITE, xx + off[1]:xx + off[1] + SITE]
            ea = float(np.std(decomplib.bandpass(ca, lo, hi)))
            u.append(float(np.std(decomplib.bandpass(cu, lo, hi))) / ea)
            r.append(float(np.std(decomplib.bandpass(cr, lo, hi))) / ea)
        mu, mr = float(np.median(u)), float(np.median(r))
        d = abs(mu - mr) / mr
        print("  %-8s %12.4f %12.4f %9.2f%% %10s"
              % (label, mu, mr, 100 * d, "robust" if d < 0.03 else "AFFECTED"))

    print("\n=== B: anything built on a DIFFERENCE (this lane's decomposition) ===")
    print("  %-8s %11s %11s %11s %11s" % ("band", "scene unreg", "scene reg",
                                          "noise unreg", "noise reg"))
    for label, lo, hi in BANDS:
        su, sr, nu, nr = [], [], [], []
        for (yy, xx) in SITES:
            ca = ga[yy:yy + SITE, xx:xx + SITE]
            cu = gb[yy:yy + SITE, xx:xx + SITE]
            cr = gb[yy + off[0]:yy + off[0] + SITE, xx + off[1]:xx + off[1] + SITE]
            try:
                s, n = decomplib.decompose(ca, cu, lo, hi)
            except decomplib.Degenerate:
                s, n = float("nan"), float("nan")
            su.append(s)
            nu.append(n)
            s, n = decomplib.decompose(ca, cr, lo, hi)
            sr.append(s)
            nr.append(n)
        msu, msr = float(np.nanmedian(su)), float(np.median(sr))
        mnu, mnr = float(np.nanmedian(nu)), float(np.median(nr))
        print("  %-8s %11.4f %11.4f %11.4f %11.4f   scene x%.3f  noise x%.3f"
              % (label, msu, msr, mnu, mnr, msu / msr if msr else float("nan"),
                 mnu / mnr if mnr else float("nan")))

    print("\nThe two halves of this table are the deliverable. A statistic that scores "
          "each arm on itself\nsurvives a shift of this size; a statistic that "
          "subtracts one arm from the other does not.")


if __name__ == "__main__":
    main()
