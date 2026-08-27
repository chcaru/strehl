"""Does registration error grow along the stack, and with what shape?

Given two solves of the same frames, `cross_err` gives their disagreement about
the *relative* geometry of a frame pair, with each solve's own reference
divided out. Plotting that against path length |i - base| separates the three
candidate shapes:

    flat        no accumulation; error is independent of separation
    ~ sqrt(d)   random walk; independent per-step errors compounding
    ~ d         systematic drift; a biased per-step error

The fit is done in log-log space on the positive part, and the exponent is
reported with the residual so a bad fit cannot masquerade as a clean power law.

A truncated span set is a *known-bad* solve: restricted to span 1 it is a pure
sequential chain, which is the align_image_stack failure mode and must
accumulate. Using it as the moving arm is this instrument's positive control --
if the exponent does not come out near a walk or a drift there, the instrument
cannot see accumulation and no null result from it means anything.
"""

import argparse
import math
import statistics
import sys

from wm import WarpMap, cross_err


def curve(wm_a, wm_b, base=0):
    """Disagreement between two solves vs path length from `base`."""
    shared = sorted(set(wm_a.placed()) & set(wm_b.placed()))
    pts = []
    for i in shared:
        if i == base:
            continue
        pts.append((abs(i - base), cross_err(wm_a, wm_b, base, i)))
    return pts


def fit_exponent(pts):
    """Least-squares slope of log(err) on log(distance)."""
    xs = [(math.log(d), math.log(e)) for d, e in pts if d > 0 and e > 1e-12]
    if len(xs) < 8:
        return None, None, None
    mx = statistics.fmean(x for x, _ in xs)
    my = statistics.fmean(y for _, y in xs)
    sxx = sum((x - mx) ** 2 for x, _ in xs)
    sxy = sum((x - mx) * (y - my) for x, y in xs)
    if sxx == 0:
        return None, None, None
    slope = sxy / sxx
    intercept = my - slope * mx
    ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in xs)
    ss_tot = sum((y - my) ** 2 for _, y in xs)
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return slope, intercept, r2


def classify(slope, r2):
    if slope is None:
        return "UNDETERMINED (too few points)"
    if r2 is not None and r2 < 0.5:
        return f"NO CLEAN POWER LAW (r2={r2:.2f})"
    if slope < 0.2:
        return "FLAT -- no accumulation"
    if slope < 0.75:
        return "RANDOM WALK (~sqrt d)"
    if slope < 1.4:
        return "SYSTEMATIC DRIFT (~d)"
    return f"SUPERLINEAR (exponent {slope:.2f})"


def describe(name, pts, slope, intercept, r2):
    byd = sorted(pts)
    n = len(byd)
    q = [byd[int(f * (n - 1))] for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
    print(f"\n{name}")
    print(f"  points {n}, distance {byd[0][0]}..{byd[-1][0]}")
    print("  err at distance:  " + "  ".join(f"d={d}:{e:.2f}px" for d, e in q))
    if slope is not None:
        print(f"  log-log slope {slope:.3f}  r2 {r2:.3f}  ->  {classify(slope, r2)}")
    else:
        print(f"  -> {classify(slope, r2)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reference_wm", help="the better solve (full ladder)")
    ap.add_argument("moving_wm", nargs="+", help="solves to compare against it")
    ap.add_argument("--base", type=int, default=0)
    a = ap.parse_args()

    ref = WarpMap(a.reference_wm)
    print(f"reference solve: {ref.name}, {len(ref.placed())} placed, "
          f"spans {ref.spans}, heldout {ref.heldout_px}, cycle floor {ref.cycle_floor_px}")
    print(f"path length measured from frame {a.base}")

    for path in a.moving_wm:
        mv = WarpMap(path)
        pts = curve(ref, mv, a.base)
        if not pts:
            print(f"\n{mv.path}: no shared placed frames")
            continue
        slope, intercept, r2 = fit_exponent(pts)
        describe(f"{mv.path.split(chr(92))[-1]}  (spans {mv.spans})", pts, slope, intercept, r2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
