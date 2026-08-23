"""M9 ACF summary: correlation length of the focus-field noise, per measure.

Reads the `m9-support acf` CSV and reports, for each measure, the smallest lag
at which the spatial autocorrelation of the high-pass-filtered focus field falls
below 1/e and below 0.1. SYNTHESIS fact 25 (MEASURED, M2) put the correlation
length of the argmax noise excess at 3-7 px and read that as the shipped
measure's support; this checks the focus field's own correlation length against
the measure's support radius.

Usage:
    python m9_acf.py data/acf-109MSDCF.csv [data/sensitivity-109MSDCF.csv]
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict


def cross(lags, vals, level):
    for lag, v in zip(lags, vals):
        if v < level:
            return lag
    return None


def main(paths):
    rows = list(csv.DictReader(open(paths[0], newline="", encoding="utf-8")))
    phi = {}
    if len(paths) > 1:
        for r in csv.DictReader(open(paths[1], newline="", encoding="utf-8")):
            phi[r["measure"]] = float(r["phi"])

    by = defaultdict(list)
    meta = {}
    for r in rows:
        by[r["measure"]].append((int(r["lag"]), float(r["acf"])))
        meta[r["measure"]] = r

    print(f"{'measure':<14} {'role':<9} {'sup_px':>6} {'phi':>8} {'L(1/e)':>7} {'L(0.1)':>7} "
          f"{'acf(1)':>7} {'acf(3)':>7} {'acf(7)':>7}")
    for m, pts in by.items():
        pts.sort()
        lags = [l for l, _ in pts]
        vals = [v for _, v in pts]
        e = cross(lags, vals, 1 / 2.718281828)
        t = cross(lags, vals, 0.1)
        g = dict(pts)
        print(f"{m:<14} {meta[m]['role']:<9} {2 * int(meta[m]['support_radius']) + 1:>6} "
              f"{phi.get(m, float('nan')):>8.5f} {str(e):>7} {str(t):>7} "
              f"{g.get(1, float('nan')):>7.4f} {g.get(3, float('nan')):>7.4f} "
              f"{g.get(7, float('nan')):>7.4f}")

    print()
    print("Reference: SYNTHESIS fact 25 (M2) reports the argmax noise excess as spatially")
    print("correlated over 3-7 px, and reads that as the shipped ring(1,3) support (7 px).")
    ship = "ring-1-3"
    if ship in by:
        pts = sorted(by[ship])
        lags = [l for l, _ in pts]
        vals = [v for _, v in pts]
        print(f"  {ship}: L(1/e) = {cross(lags, vals, 1 / 2.718281828)} px, "
              f"L(0.1) = {cross(lags, vals, 0.1)} px, support_px = 7")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    main(sys.argv[1:])
