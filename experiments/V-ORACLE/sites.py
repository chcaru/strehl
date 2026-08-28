#!/usr/bin/env python3
"""Read stage A and answer the decisive question at named image locations.

For each site (given in MASTER pixel coordinates, as crop1to1.py reports them)
this prints the through-focus curve of the best-covered tile under that site and
says whether ANY frame in the bracket resolved structure there.

It also prints the corpus of tiles ranked by resolvable structure, so a site's
number can be read against the same subject's own best and worst.

Usage:  python sites.py <subject> [--sites "y,x y,x ..."] [--band 2]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

# The six sites crop1to1.py --mode edge selects on flowers-cpl, in MASTER px,
# as top-left corners of 520x520 crops.  Reproduced by running the project's own
# tool; see the report.  My visual read of each is recorded beside it.
FLOWERS_SITES = [
    (3164, 52, "SHARP  (petal cell mesh, pollen grains)"),
    (1212, 292, "BLURRED (smooth, defocus-like)"),
    (1540, 1180, "SHARP  (trichomes fully resolved)"),
    (1972, 420, "BLURRED (smooth)"),
    (1452, 1748, "SHARP  (hairs, black speckles resolved)"),
    (3860, 2396, "BLURRED (near-total smooth)"),
]
CROP = 520


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--band", type=int, default=2)
    args = ap.parse_args()

    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    nr, nc, ts = int(A["nr"]), int(A["nc"]), int(A["tile"])
    ks = A["frames"]
    var_k = A["var_k"]                       # (K, NBAND, nr, nc)
    con = A["contrast"]                      # (NBAND, nr, nc)
    b = args.band

    # Relative contrast: the through-focus modulation as a FRACTION of the
    # out-of-focus floor.  Dimensionless, so it does not rank a bright tile
    # above a dark one merely for being bright -- the exact bias BUILD-TRIAGE
    # section 6.3 had to correct for.
    lo = A["lo"]
    rel = con / np.maximum(lo, 1e-9)

    print(f"=== {args.subject}: {nr}x{nc} tiles of {ts} green px "
          f"({2 * ts} master px), {len(ks)} of {int(A['nframes'])} frames ===")
    print(f"band {b} through-focus contrast over all {nr * nc} tiles:")
    v = con[b].ravel()
    for q in (0, 10, 25, 50, 75, 90, 99, 100):
        print(f"   p{q:<3d} {np.percentile(v, q):12.3f}")
    print(f"band {b} RELATIVE contrast (contrast / out-of-focus floor):")
    rv = rel[b].ravel()
    for q in (0, 10, 25, 50, 75, 90, 99, 100):
        print(f"   p{q:<3d} {np.percentile(rv, q):12.4f}")

    sites = FLOWERS_SITES if args.subject == "flowers-cpl" else []
    if not sites:
        print("\n(no named sites for this subject)")
        return 0

    print(f"\n=== the six 1:1 crop sites, in MASTER px, {CROP}x{CROP} ===")
    print("Tiles are included only if their CENTRE falls inside the crop, so a")
    print("site's number cannot be borrowed from sharp structure sitting")
    print("outside the square the eye actually looked at.  All five DoG bands")
    print("are printed: no band is selected, so no band-choice can be tuned to")
    print("produce a verdict.  Band 0 is near-pure noise on this subject (probe")
    print("measured signal/noise 0.0032 in the richest tile) -- it is printed")
    print("anyway, and the fact that it carries almost no through-focus")
    print("contrast ANYWHERE is itself the evidence for that claim.\n")
    hdr = "   ".join(f"b{j}" for j in range(ora.NBAND))
    for i, (my, mx, note) in enumerate(sites):
        gy0, gx0 = my / 2.0, mx / 2.0
        gy1, gx1 = gy0 + CROP / 2.0, gx0 + CROP / 2.0
        rr = [r for r in range(nr) if gy0 <= (r + 0.5) * ts <= gy1]
        cc = [c for c in range(nc) if gx0 <= (c + 0.5) * ts <= gx1]
        if not rr or not cc:            # crop smaller than a tile pitch
            rr = [min(nr - 1, int((gy0 + gy1) / 2 // ts))]
            cc = [min(nc - 1, int((gx0 + gx1) / 2 // ts))]
        print(f"site {i}  master y={my} x={mx}   {note}")
        print(f"   tiles centred inside the crop: rows {rr} cols {cc} "
              f"({len(rr) * len(cc)} tiles)")
        for bb in range(ora.NBAND):
            sub = con[bb][np.ix_(rr, cc)]
            subrel = rel[bb][np.ix_(rr, cc)]
            allv = con[bb].ravel()
            pct = 100.0 * (allv < sub.max()).mean()
            j = int(np.argmax(sub))
            R, C = rr[j // len(cc)], cc[j % len(cc)]
            curve = var_k[:, bb, R, C]
            kb = int(np.argmax(curve))
            mark = "  <-- BAND USED FOR THE HEADLINE" if bb == b else ""
            print(f"     band {bb}: contrast max={sub.max():10.3f} "
                  f"med={np.median(sub):9.3f}  rel={subrel.max():8.2f}  "
                  f"p{pct:4.1f}  bestframe={int(ks[kb]):3d}"
                  f"{'(END)' if kb in (0, len(ks) - 1) else '     '}{mark}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
