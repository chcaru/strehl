r"""M128 / yield_diag — why does a column fail to yield a crossing?

Crossing yield is 74.3% / 70.6% / 61.3% at f/5.6 / f/8 / f/11. That single
number is behind every blocker this lane has hit: it fails most windows in the
census, and it left 22-44% of columns needing interpolation in the locus-PSD
probe, with a gap fraction that differs by aperture, which is enough on its own
to explain that probe's failure.

geom.crossings rejects a column for exactly two reasons, and they call for
completely different responses:

  (a) hi - lo < 300 DN            -- genuinely too little contrast to locate
  (b) len(idx) != 1               -- the profile crosses the mid level more
                                     than once, or not at all

(b) is not a statement that the edge is unfindable. It is a statement that this
particular estimator insists on a globally unique crossing, which noise, the
veiling-glare shoulder and debris all break. A two-pass estimator that first
fits the locus on unambiguous columns and then resolves ambiguous ones against
that prediction would recover them.

This counts the two causes separately, so the fix is chosen on evidence.

    python src\yield_diag.py <frame> [--band-half 60]
"""

import argparse
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M88 = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402
import geom  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--band-half", type=int, default=60)
    ap.add_argument("--dark-first", action="store_true")
    args = ap.parse_args()

    active = L.load_active(args.frame)
    sub, xs, ys = L.green_sites(active, args.which)
    b0, b1, row = geom.find_band(sub)
    b0 = max(row - args.band_half, 0)
    b1 = min(row + args.band_half, sub.shape[0])
    band = sub[b0:b1, :]
    bright_first = not args.dark_first

    n = band.shape[0]
    q = max(6, n // 6)
    first = np.percentile(band[:q, :], 50, axis=0)
    last = np.percentile(band[-q:, :], 50, axis=0)
    hi = first if bright_first else last
    lo = last if bright_first else first
    mid = 0.5 * (hi + lo)

    ncol = band.shape[1]
    counts = {"ok": 0, "low_contrast": 0, "zero_crossings": 0,
              "multi_crossings": 0}
    ncross = np.zeros(ncol, int)
    for x in range(ncol):
        if hi[x] - lo[x] < 300.0:
            counts["low_contrast"] += 1
            ncross[x] = -1
            continue
        prof = band[:, x] if bright_first else band[::-1, x]
        m = mid[x]
        idx = np.nonzero((prof[:-1] >= m) & (prof[1:] < m))[0]
        ncross[x] = len(idx)
        if len(idx) == 1:
            counts["ok"] += 1
        elif len(idx) == 0:
            counts["zero_crossings"] += 1
        else:
            counts["multi_crossings"] += 1

    print(f"{Path(args.frame).name}  plane {args.which}  band rows "
          f"{b0}..{b1}  step row {row}")
    print(f"contrast hi-lo: median {np.median(hi - lo):.0f} DN, "
          f"5th pct {np.percentile(hi - lo, 5):.0f}, "
          f"min {np.min(hi - lo):.0f}")
    print(f"\ncolumns: {ncol}")
    tot = 0
    for k, v in counts.items():
        tot += v
        print(f"  {k:>16s} {v:6d}  {100.0 * v / ncol:6.2f}%")
    print(f"  {'TOTAL':>16s} {tot:6d}  {100.0 * tot / ncol:6.2f}%   "
          f"(must equal the column count: {tot == ncol})")

    mm = ncross > 1
    if mm.any():
        print(f"\ndistribution of crossing counts among the "
              f"{int(mm.sum())} multi-crossing columns:")
        for c in range(2, min(int(ncross.max()), 9) + 1):
            k = int((ncross == c).sum())
            if k:
                print(f"    {c} crossings: {k:5d}")
        big = int((ncross > 9).sum())
        if big:
            print(f"    >9 crossings: {big:5d}")
        print("\n  A column with 2 crossings is one the veiling-glare "
              "shoulder or a noise excursion re-crosses. It is recoverable by "
              "a two-pass estimator: fit the locus on the unambiguous columns "
              "first, then take the crossing nearest that prediction.")
    print(f"\nRECOVERABLE by a two-pass estimator: "
          f"{counts['multi_crossings']} columns "
          f"({100.0 * counts['multi_crossings'] / ncol:.2f}%), taking yield "
          f"from {100.0 * counts['ok'] / ncol:.2f}% to at most "
          f"{100.0 * (counts['ok'] + counts['multi_crossings']) / ncol:.2f}%.")
    print(f"NOT recoverable that way: {counts['low_contrast']} low-contrast "
          f"and {counts['zero_crossings']} zero-crossing columns.")


if __name__ == "__main__":
    main()
