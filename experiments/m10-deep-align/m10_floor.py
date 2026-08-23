"""Summarise the estimator corner-error floor sweep (control P1b).

Reads `<prefix>-floor.csv` and reports, per estimator configuration and anchor
margin, the distribution of corner error in plane px against the planted warp,
stratified by the magnitude of the planted scale change.

The stratification is the point.  A rigid correlation template of side `T`
matched across a scale difference `g` is internally stretched by `g*T` px, so a
wide-baseline pair is mis-modelled by the template itself, on identical content,
with no defocus anywhere.  This sweep is where that shows up or does not.
"""

import sys

import numpy as np

from m10_lib import read_floor

GBINS = [(0.0, 0.005), (0.005, 0.02), (0.02, 0.035), (0.035, 0.06)]


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/coffee-bean-floor.csv"
    rows = read_floor(path)
    cfgs = sorted({r["cfg"] for r in rows})
    margins = sorted({r["margin"] for r in rows})
    print(f"estimator corner-error floor: {len(rows)} planted-warp recoveries, plane px")
    print()
    hdr = f"{'cfg':>8} {'margin':>7} {'n':>4} {'fail':>5} {'median':>8} {'p90':>8} {'max':>8}"
    print(hdr + f" {'med_rms':>8} {'med_used':>9}")
    for c in cfgs:
        for m in margins:
            sub = [r for r in rows if r["margin"] == m and r["cfg"] == c]
            if not sub:
                continue
            ok = [r for r in sub if r["ok"]]
            if not ok:
                print(f"{c:>8} {m:>7} {len(sub):>4} {len(sub):>5}" + "        -" * 5)
                continue
            ce = np.array([r["corner_err"] for r in ok])
            print(
                f"{c:>8} {m:>7} {len(sub):>4} {len(sub) - len(ok):>5} {np.median(ce):>8.3f} "
                f"{np.percentile(ce, 90):>8.3f} {ce.max():>8.3f} "
                f"{np.median([r['rms'] for r in ok]):>8.3f} "
                f"{np.median([r['used'] for r in ok]):>9.1f}"
            )

    print()
    print("median corner error, plane px, by planted |scale change|:")
    cols = [
        (c, m)
        for c in cfgs
        for m in margins
        if any(r["cfg"] == c and r["margin"] == m for r in rows)
    ]
    print("  |g| bin      " + "".join(f"{c[:6]}/{m}".rjust(12) for c, m in cols))
    for lo, hi in GBINS:
        cells = []
        for c, m in cols:
            sub = [
                r
                for r in rows
                if r["cfg"] == c
                and r["margin"] == m
                and r["ok"]
                and lo <= abs(r["g_true"]) < hi
            ]
            cells.append(np.median([r["corner_err"] for r in sub]) if sub else float("nan"))
        print(f"  {lo:.3f}-{hi:.3f} " + "".join(f"{v:>12.3f}" for v in cells))

    print()
    print("equivalent coffee-bean span (total scale change -4.575% over 104 frames):")
    for lo, hi in GBINS:
        span_lo = lo / 0.04575 * 104
        span_hi = hi / 0.04575 * 104
        print(f"  |g| {lo:.3f}-{hi:.3f}  ->  span {span_lo:.0f}-{span_hi:.0f} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
