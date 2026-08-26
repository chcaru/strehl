"""Independent check of the weighting bug BUILD-HULL found in my hullband.py.

BUILD-HULL (section 18, commit c99486d4) says my band-share weighting `w = a.size`
under-weights band k by 4^k, because a decimated coefficient is upsampled to
cover 4^k full-resolution pixels on reconstruction, so each band's full-res
energy is N*rd^2 -- constant N per band, not N/4^k.

If true it inverts my published finding that "88.8% of the total change is in
the 2 px and 4 px bands", which I broadcast to the fleet and used to discard a
correct hypothesis.

I am not re-running their attack. This is my own decisive test, on inputs whose
answer is fixed by construction rather than measured:

  PURE-COARSE : the difference is a single constant offset over the whole frame.
                It has NO fine content whatsoever. Any correct attribution must
                put ~100% of the change in the residual.
  PURE-FINE   : the difference is a 2 px checkerboard, which lives entirely in
                band 0. Any correct attribution must put ~100% in band 0.

A weighting that gets the second right and the first wrong is under-weighting
coarse bands, which is exactly the claim.
"""
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from hullband import bands  # noqa: E402  -- deliberately the shipped code


def shares(diff):
    """Return (as_shipped, corrected) fine-band share of total change."""
    bd, rd_res = bands(diff)
    # as shipped: weight each band by its own coefficient count
    tot_shipped = 0.0
    tot_fixed = 0.0
    per_band = []
    for a in bd:
        r2 = float((a ** 2).mean())
        per_band.append((r2, a.size))
        tot_shipped += r2 * a.size
        tot_fixed += r2 * diff.size          # constant full-res footprint
    r2res = float((rd_res ** 2).mean())
    tot_shipped += r2res * rd_res.size
    tot_fixed += r2res * diff.size

    fine_shipped = sum(r2 * sz for r2, sz in per_band[:2])
    fine_fixed = sum(r2 * diff.size for r2, _ in per_band[:2])
    res_shipped = 100.0 * (r2res * rd_res.size) / tot_shipped
    res_fixed = 100.0 * (r2res * diff.size) / tot_fixed
    return (100.0 * fine_shipped / tot_shipped, 100.0 * fine_fixed / tot_fixed,
            res_shipped, res_fixed)


def main() -> int:
    h, w = 512, 512

    # Orthogonal components with exactly known full-resolution energy:
    #   coarse = constant offset      -> mean square a_c^2, lives in the residual
    #   fine   = 2 px checkerboard    -> mean square a_f^2, lives in band 0
    # They are orthogonal (checkerboard is zero-mean), so the true coarse share
    # of full-resolution energy is a_c^2 / (a_c^2 + a_f^2). That is ground truth
    # by construction, not by measurement.
    #
    # A single-band difference is degenerate: every positive weighting scores it
    # correctly because the other bands are exactly zero. The weighting only
    # matters when energy is SPREAD, so the cases below are mixtures.
    yy, xx = np.mgrid[0:h, 0:w]
    chk = (-1.0) ** (yy + xx)

    print(f"{'true coarse %':>14} {'shipped says':>13} {'corrected says':>15} "
          f"{'shipped error':>14} {'corrected error':>16}")
    print("-" * 78)

    rows = []
    for true_coarse in (0.9975, 0.99, 0.95, 0.80, 0.50, 0.20, 0.05):
        a_c = 100.0
        a_f = a_c * np.sqrt((1.0 - true_coarse) / true_coarse)
        d = a_c + a_f * chk
        fs, ff, rs, rf = shares(d)
        # coarse = everything that is not bands 0-1
        coarse_shipped = 100.0 - fs
        coarse_fixed = 100.0 - ff
        e_ship = abs(coarse_shipped - 100.0 * true_coarse)
        e_fix = abs(coarse_fixed - 100.0 * true_coarse)
        rows.append((true_coarse, coarse_shipped, coarse_fixed, e_ship, e_fix))
        print(f"{100.0 * true_coarse:>13.2f}% {coarse_shipped:>12.2f}% "
              f"{coarse_fixed:>14.2f}% {e_ship:>13.2f} {e_fix:>15.2f}")

    worst_ship = max(r[3] for r in rows)
    worst_fix = max(r[4] for r in rows)
    print()
    print(f"worst absolute error, shipped weighting   : {worst_ship:.2f} points")
    print(f"worst absolute error, corrected weighting : {worst_fix:.2f} points")

    # The specific inversion BUILD-HULL alleges: a difference that is
    # overwhelmingly coarse gets reported as overwhelmingly fine.
    top = rows[0]
    inverted = top[1] < 50.0 and top[0] > 0.9
    print()
    print(f"at {100.0 * top[0]:.2f}% true coarse, shipped reports {top[1]:.2f}% coarse "
          f"-> {'INVERTED' if inverted else 'not inverted'}")
    print()
    if worst_ship > 10.0 * max(worst_fix, 1e-9) and inverted:
        print("CONFIRMED: hullband.py's `w = a.size` under-weights coarse bands "
              "severely. BUILD-HULL is right and my 88.8% finding is inverted.")
        return 0
    if worst_ship <= worst_fix:
        print("NOT CONFIRMED: the shipped weighting is no worse than the corrected one.")
        return 1
    print("PARTIAL: shipped weighting is worse, but not the inversion alleged.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
