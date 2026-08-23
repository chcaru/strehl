"""P4 - end-to-end recovery of a planted camera path from synthetic frames.

Every other measurement in M10 is ground-truth free by necessity. This one is
not: the frames are built from one real coffee-bean frame by a *known* smooth
similarity sequence plus a growing depth-dependent blur, so long-baseline pairs
genuinely decorrelate the way real ones do. The whole path is exercised - ARW
decode, plane extraction, tiled NCC, similarity fit, global solve - and scored
in absolute corner px against the planted transforms.

**Disclosure, per SYNTHESIS section 5 item 11 and the registered design.** The
`warp` flavour resamples bilinearly, which M6 measured to plant a sub-pixel
phase sharpness modulation that a correlation estimator can read as defocus.
That is why this control is used for *recovery* only. It is never evidence about
defocus, and no conclusion about the scale-rate ladder rests on it. The
`integer` flavour, if run, shifts by whole pixels only and has no resampler,
at the cost of a coarser planted path.
"""

import csv
import sys

import numpy as np

from m10_lib import (
    corner_err,
    graph_stats,
    read_edges,
    relative,
    solve_ba,
    solve_fixed,
    solve_hops,
    solve_poly,
)


def read_truth(path):
    g = {}
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            k = int(r["frame"])
            a = (1.0 + float(r["g"])) + 1j * float(r["rot"])
            b = float(r["ax"]) + 1j * float(r["ay"])
            g[k] = (a, b)
    return [g[k] for k in sorted(g)]


def strategies(edges, n):
    return {
        "S0-fixed": solve_fixed(edges, n),
        "S1-hops1": solve_hops(edges, n, 1)[0],
        "S2-hops8": solve_hops(edges, n, 8)[0],
        "S2-hops32": solve_hops(edges, n, 32)[0],
        "S3-ba-invvar": solve_ba(edges, n, scheme="invvar"),
        "S3-ba-unit": solve_ba(edges, n, scheme="unit"),
        "S4-poly6": solve_poly(edges, n, 6, scheme="unit", bdeg=4)[0],
        "S5-centre6": solve_poly(edges, n, 6, scheme="unit",
                                 fixed_centre=True)[0],
        "S6-ba-smooth": solve_ba(edges, n, scheme="unit", smooth=0.05),
    }


def score(sol, truth, n):
    errs, cov = [], 0
    for k in range(1, n):
        if sol[k] is None:
            continue
        cov += 1
        errs.append(corner_err(relative(sol[0], sol[k]),
                               relative(truth[0], truth[k])))
    return cov, np.array(errs)


def main(argv):
    case = argv[1] if len(argv) > 1 else "p4-warp"
    cfg = argv[2] if len(argv) > 2 else "m10"
    truth = read_truth(f"data/{case}-truth.csv")
    n = len(truth)
    rows = read_edges(f"data/{case}-edges.csv", cfg=cfg)
    ok = [e for e in rows if e.ok]

    print("=" * 84)
    print(f"P4  END-TO-END RECOVERY OF A PLANTED PATH - {case}, cfg={cfg}")
    print("  Absolute corner error against planted truth, plane px.")
    print("  DISCLOSED: the 'warp' flavour resamples bilinearly. Recovery only;")
    print("  this control is never evidence about defocus.")
    print("=" * 84)
    st = graph_stats(ok, n)
    tot = corner_err(relative(truth[0], truth[n - 1]), (1.0 + 0j, 0j))
    print(f"\n  {n} frames, {len(rows)} pairs, {len(rows) - len(ok)} no-fit, "
          f"cycle rank {st['cycle_rank']}, components {st['components']}")
    print(f"  planted total drift at the corner: {tot:.1f} plane px "
          f"(scale {100 * (abs(truth[n - 1][0]) - 1):.3f}%)")

    bands = {
        "all measurable": ok,
        "span <= 8": [e for e in ok if e.span <= 8],
        "span 8-32": [e for e in ok if 8 <= e.span <= 32],
        "span >= 16": [e for e in ok if e.span >= 16],
    }
    for bname, band in bands.items():
        bs = graph_stats(band, n)
        tree = " TREE" if bs["is_tree"] else ""
        print(f"\n  train = {bname}: {len(band)} edges, cycle rank "
              f"{bs['cycle_rank']}{tree}")
        print(f"    {'strategy':>14} {'cover':>9} {'median':>9} {'p90':>9} "
              f"{'max':>9}")
        for k, sol in strategies(band, n).items():
            if sol is None:
                continue
            cov, e = score(sol, truth, n)
            if e.size == 0:
                print(f"    {k:>14} {cov:>4}/{n:<4}" + "        -" * 3)
                continue
            print(f"    {k:>14} {cov:>4}/{n:<4} {np.median(e):>9.3f} "
                  f"{np.percentile(e, 90):>9.3f} {e.max():>9.3f}")

    print("\n  Per-span edge accuracy against truth (direct fits, no solver):")
    print(f"    {'span':>6} {'n':>5} {'med err':>9} {'p90':>9} "
          f"{'med used':>9} {'med rms':>9}")
    for lo, hi in [(1, 1), (2, 2), (3, 4), (5, 8), (9, 16), (17, 32),
                   (33, 64), (65, 104)]:
        sub = [e for e in ok if lo <= e.span <= hi]
        if not sub:
            continue
        er = [corner_err(e.t(), relative(truth[e.i], truth[e.j]))
              for e in sub]
        lbl = f"{lo}" if lo == hi else f"{lo}-{hi}"
        print(f"    {lbl:>6} {len(sub):>5} {np.median(er):>9.3f} "
              f"{np.percentile(er, 90):>9.3f} "
              f"{np.median([e.used for e in sub]):>9.0f} "
              f"{np.median([e.rms for e in sub]):>9.3f}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
