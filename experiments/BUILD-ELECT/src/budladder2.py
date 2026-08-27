"""Ladder v2: refine the floor, and put the signal beside it at every N.

Ladder v1 reported FLOOR = 400 DN against a 233 DN signal and concluded section
21's n=1 null was worthless. That conclusion was drawn off a coarse grid: the
A=200 rung failed the criterion by 0.5 DN (OVER 61.8 vs CTL 62.3) and the next
rung was 400, so the reported floor was wrong by a factor of two -- in the
direction that UNDERSTATES the instrument. Section 77's rule, met from the other
side: a limit read off the first passing grid point is unaudited whichever way
it errs.

Two changes:

  1. Refine the grid through the crossing.
  2. Measure the SIGNAL and the FLOOR in the same run, at the same N, on the
     same statistic. Section 21 compared a floor measured here against a signal
     quoted from a different table, which is exactly the kind of cross-table
     comparison that hides a mismatch.

The output is a margin, signal/floor, at every averaging setting. That number is
the honest strength of section 21's n=1 evidence:

  margin >> 1  the n=1 null is informative -- a defect the size of the default
               arm's would have been seen and was not.
  margin ~ 1   the null is marginal and must be reported as such.
  margin < 1   the null is uninformative: the instrument could not have seen the
               defect it is being used to rule out, and section 21's use of it
               must be withdrawn.

Pre-registered before the run: I expect margin ~ 1.2 at N=0 from v1's numbers,
i.e. marginal, and section 21 overstated this. Any N where margin < 1 is a
setting at which my own published claim is unsupported.
"""
import os
import numpy as np
import tifffile

from budfringe7 import esf, over_of, SX, SY, CTL_Y, TRACK, GRID, load

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
N1 = os.path.join(OUT, "one-fb-pyramid.tiff")
DEF = os.path.join(OUT, "fb-noflags.tiff")

SIGMA = 1.5
LADDER = (0, 50, 100, 150, 175, 200, 210, 225, 250, 300, 400, 800)


def plant(a, y0, x0, depth, nrow):
    """Subtract a gaussian from G at each row's own tracked edge.

    Only the row band the statistic reads is copied, so the ladder does not
    allocate several full-frame int32 arrays per rung.
    """
    b = a.copy()
    if depth == 0:
        return b, 0, 0.0
    lo = y0 - nrow - 2
    hi = y0 + nrow + 3
    work = a[lo:hi].astype(np.int32)
    off = np.arange(-8, 9)
    prof = np.rint(depth * np.exp(-0.5 * (off / SIGMA) ** 2)).astype(np.int32)
    xp = x0
    for y in range(y0 - nrow, y0 + nrow + 1):
        band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0)
        w = band[xp - TRACK:xp + TRACK + 1, 1]
        xp = xp - TRACK + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
        for dy in (-1, 0, 1):
            work[y + dy - lo, xp - 8:xp + 9, 1] -= prof
    if int(work[:, :, 1].min()) < 0:
        print(f"      WARNING depth {depth}: green hit 0, achieved depth "
              f"is not the requested depth")
    d = a[lo:hi].astype(np.int32) - work
    b[lo:hi] = np.clip(work, 0, 65535).astype(np.uint16)
    return b, int((d != 0).sum()), float(d.max())


def floor_at(a, nrow, ctl0, over0):
    """Smallest ladder depth whose OVER exceeds the arm's own control."""
    prev = None
    for A in LADDER:
        b, nch, ach = plant(a, SY, SX, A, nrow)
        if A > 0:
            if nch == 0:
                raise SystemExit(f"PLANT DID NOT LAND at depth {A}, N={nrow}")
            if ach < 0.6 * A:
                raise SystemExit(f"PLANT UNDER-APPLIED at {A}: got {ach:.0f}")
        ov = over_of(esf(b, SY, SX, False, True, nrow))
        ct = over_of(esf(b, CTL_Y, SX, False, False, nrow))
        if A == 0 and (abs(ov - over0) > 1e-9 or abs(ct - ctl0) > 1e-9):
            raise SystemExit("HARNESS NOT INERT at A=0")
        if A > 0 and abs(ct - ctl0) > 1e-9:
            raise SystemExit(f"PLANT LEAKED into control at {A}, N={nrow}")
        del b
        if A > 0 and ov > ct:
            return A, prev
        prev = A
    return None, prev


def main():
    print("=" * 78)
    print("LADDER v2 -- floor and signal, same run, same N, same statistic")
    print("=" * 78)
    for p in (N1, DEF):
        if not os.path.exists(p):
            print(f"  MISSING {p} -- not a pass")
            return 1

    a1 = load(N1)
    ad = load(DEF)
    print(f"\n  floor measured on : n=1 pyramid (no election)")
    print(f"  signal measured on: g2.0 LINEAR default arm")
    print(f"  address           : ABS ({SX},{SY}), control row {CTL_Y}")
    print(f"  criterion         : OVER > that arm's own CTL (pre-registered)")

    print(f"\n    {'N':>4} {'rows':>5} {'n1 OVER':>8} {'n1 CTL':>7} "
          f"{'floor':>7} {'(last miss)':>11} {'signal':>8} {'margin':>7}")
    worst = None
    for n in GRID:
        c0 = over_of(esf(a1, CTL_Y, SX, False, False, n))
        o0 = over_of(esf(a1, SY, SX, False, True, n))
        fl, miss = floor_at(a1, n, c0, o0)
        sig = over_of(esf(ad, SY, SX, False, True, n))
        if fl is None:
            print(f"    {n:>4} {2*n+1:>5} {o0:>8.1f} {c0:>7.1f} "
                  f"{'>'+str(LADDER[-1]):>7} {miss:>11} {sig:>8.1f} "
                  f"{'--':>7}")
            worst = 0.0
            continue
        m = sig / fl
        worst = m if worst is None else min(worst, m)
        print(f"    {n:>4} {2*n+1:>5} {o0:>8.1f} {c0:>7.1f} {fl:>7} "
              f"{miss:>11} {sig:>8.1f} {m:>7.2f}")

    print()
    print("  margin = default arm's measured overshoot / smallest overshoot the")
    print("  n=1 arm could have carried without this statistic reporting it.")
    print()
    if worst is not None and worst < 1.0:
        print(f"  WORST MARGIN {worst:.2f} < 1. At that setting the n=1 null is")
        print("  UNINFORMATIVE -- the instrument could not have seen a defect")
        print("  the size of the one it is being used to rule out. Section 21's")
        print("  n=1 evidence must be qualified to the settings where the")
        print("  margin exceeds 1, and stated with the margin attached.")
    else:
        print(f"  WORST MARGIN {worst:.2f}. The null holds at every setting, but")
        print("  it is a margin and must be reported as one, not as silence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
