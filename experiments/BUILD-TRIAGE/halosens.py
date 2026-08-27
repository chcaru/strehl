"""My verdict statistic REWARDS the defect the owner principally complains about.

ORCH's orch_halo.py (commit b0bc4b71) certifies tweezers-cpl at 0.9452 step
units -- a 198% overshoot 12 px off the edge, the worst in the corpus.  I
classified that subject GOOD, why-string "merge matches the best source frame
everywhere measured (worst 0.00 px-equivalent, at/near parity)".  This script
establishes which of those two statements is uninformative, and by how much.

STRUCTURAL FINDING (certain by inspection, no experiment required):

  tri.edge_slope  = p99.5 of |grad| after a 3x3 median -- a MAGNITUDE.
  tri.blur_equiv  = returns 0.0 for any ratio >= 1.0, "nothing to explain".

  An overshoot contributes additional gradient magnitude.  There is no term in
  either function that can go negative for ringing, so THE SIGN OF THE ERROR IS
  BOUNDED BELOW BY ZERO: the statistic may ignore a halo, but no input can make
  it charge for one.  A haloed merge can only ever score at or above a clean
  one, and blur_equiv then floors the result at 0.00 px.

WHY COMMISSIONING NEVER CAUGHT IT (ORCH §92).  E2 planted noise, E3 planted
blur; the instrument is correct on both.  Every defect I ever planted made the
image worse and I checked the number went down.  A defect that makes the number
go UP passes every such test trivially.

    A metric can be BLIND to a defect (reads nothing) or PERVERSE on it (reads
    better).  Commissioning that plants only degradations cannot tell those
    apart, because both present as a pass.

A SYNTHETIC HARNESS FOR THIS WAS BUILT AND WITHDRAWN.  Planting ORCH's profile
into an isolated synthetic step gave +14.9% -- but its direction control failed:
planted blur RAISED edge_slope, 2367.70 -> 2459.29 at sigma 0.5.  On an image
carrying one edge in a large flat field, p99.5 is set by HOW MANY pixels carry
gradient, not by the peak, and blur spreads gradient over more columns.  The
harness was unrepresentative and every number from it is void.  Recorded
because the failure mode is not obvious and someone will rebuild it.

THE METHOD USED INSTEAD.  Plant a halo into a REAL master, in the camera-linear
space the shipped ratios are actually measured in, and let ORCH's tool -- which
this lane may not edit, making it an independent referee -- calibrate how much
halo the plant produced.  Baseline is bee-3-cpl, which that tool reads at
0.0000 and is therefore a genuinely halo-free starting point.

CALIBRATION, measured by orch_halo.py --dir on the planted srgb masters:

    unsharp(amount, r=12)   ORCH halo (step units)
        0.0                     0.0000   <- baseline, confirms halo-free
        0.4                     0.0335
        0.8                     0.0706
        1.6                     0.1206   <- CERTIFIED, just above the 0.1197 floor

CAVEAT, stated because it is the honest reading and not a weakness to hide: an
unsharp mask produces ringing AND genuine edge steepening, and this script does
not separate them.  That is precisely the point.  edge_slope cannot separate
them either, which is exactly why a haloed merge scores as sharper.  The number
below is "what my statistic does when shown a halo", not "what pure ringing
contributes".

Read-only with respect to shipped artifacts.  Writes planted TIFFs to its own
output directory only.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402

SUBJECT = "bee-3-cpl"      # ORCH: halo 0.0000, so a clean baseline to plant into
RADIUS = 12.0              # puts the overshoot peak at ~12px, matching tweezers
CROP = 512                 # matches the tile size compare.py measures on

# Measured by orch_halo.py --dir=<my dir>, an instrument this lane cannot edit.
ORCH_CAL = {0.0: 0.0000, 0.4: 0.0335, 0.8: 0.0706, 1.6: 0.1206}
ORCH_FLOOR = 0.1197
ORCH_TWEEZERS = 0.9452
ORCH_WRAPPED1 = 0.1369


def plant(g: np.ndarray, amount: float) -> np.ndarray:
    """Unsharp halo at `amount`, in whatever space `g` is given in."""
    return g if amount == 0.0 else g + amount * (g - gaussian_filter(g, RADIUS))


def main() -> int:
    path = os.path.join(tri.LIN, SUBJECT + ".tiff")
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    g = a.astype(np.float32).mean(axis=2) if a.ndim == 3 else a.astype(np.float32)
    print(f"{SUBJECT} camera-linear {a.shape}, planting halo at r={RADIUS:.0f}px\n")

    sites = [(y, x)
             for y in range(CROP, g.shape[0] - 2 * CROP, 700)
             for x in range(CROP, g.shape[1] - 2 * CROP, 700)]
    base = {s: tri.edge_slope(g[s[0]:s[0] + CROP, s[1]:s[1] + CROP]) for s in sites}
    sites = [s for s in sites if base[s] > 0]
    assert len(sites) >= 20, f"only {len(sites)} usable crops"
    print(f"{len(sites)} usable {CROP}px crops\n")

    print(f"  {'unsharp':>8} {'ORCH halo':>10} {'edge_slope ratio':>18} "
          f"{'p10':>8} {'p90':>8}")
    hv, rv = [], []
    for amt in sorted(ORCH_CAL):
        h = plant(g, amt)
        r = np.array([tri.edge_slope(h[s[0]:s[0] + CROP, s[1]:s[1] + CROP]) / base[s]
                      for s in sites])
        med = float(np.median(r))
        hv.append(ORCH_CAL[amt])
        rv.append(med)
        print(f"  {amt:>8.1f} {ORCH_CAL[amt]:>10.4f} {med:>18.4f} "
              f"{np.percentile(r, 10):>8.4f} {np.percentile(r, 90):>8.4f}")

    # ANCHOR: amount 0 must return exactly 1.0, or the harness is the signal.
    assert abs(rv[0] - 1.0) < 1e-9, f"null plant returned {rv[0]}, not 1.0"
    assert all(rv[i + 1] > rv[i] for i in range(len(rv) - 1)), "not monotone in halo"
    print("\n  null plant returns exactly 1.0; monotone increasing in halo: OK")

    slope = float(np.polyfit(hv, rv, 1)[0])
    print(f"\n  inflation ~ {slope:.2f}x per step-unit of ORCH halo, over the")
    print(f"  planted range 0.0000..{max(hv):.4f}")

    print("\nWHAT THIS MEANS FOR THE SHIPPED TABLE")
    print(f"  ORCH's certification floor is {ORCH_FLOOR:.4f}: below it that tool")
    print("  reports UNDETERMINED, correctly refusing to interpret.  But a halo of")
    print(f"  {ORCH_CAL[0.4]:.4f} -- less than a third of that floor, invisible to it --")
    print(f"  already inflates my sharpness ratio by {100 * (rv[1] - 1):.0f}%.")
    print("  So the 19 masters reading at/below floor are NOT established halo-free,")
    print("  and each could carry enough halo to move my ratio substantially.")
    print(f"\n  wrapped-text-1 (halo {ORCH_WRAPPED1:.4f}) sits just past my planted")
    print("  range; its GOOD verdict is contaminated at roughly the top row above.")
    print(f"\n  tweezers-cpl (halo {ORCH_TWEEZERS:.4f}) is {ORCH_TWEEZERS / max(hv):.1f}x beyond the")
    print("  strongest plant here.  The response must saturate somewhere, so a linear")
    print("  extrapolation is NOT defensible and none is offered: the inflation there")
    print("  is LARGE BUT UNQUANTIFIED.  What is certain is its sign, which is")
    print("  structural -- it can only be >= 1.0, never a penalty.")
    print("\n  tweezers-cpl's shipped usable edge ratios are 1.2602 / 1.2602 / 1.0250,")
    print("  all >= 1, so blur_equiv floored them to 0.00px and the verdict read GOOD.")
    print("  That verdict is NOT SUPPORTED by the evidence cited for it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
