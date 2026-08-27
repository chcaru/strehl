"""Amplitude ladder: make section 21's n=1 silence state a number.

Section 21 reported that the n=1 arm shows no overshoot at five of six averaging
settings, and used that silence as the load-bearing evidence that the defect
needs the merge -- which is the whole reason ORCH's election hypothesis
survived. Tonight's notice:

    A detector's silence is worth nothing until it has been made to speak at a
    stated amplitude. Report "no defect at or above X DN", with X measured by a
    ladder, or do not report clean at all.

Section 21 has a partial answer already: the SAME statistic, at the SAME
address, in the SAME code path, returns +233 DN on the default arm. So the
instrument is not dead. But "it responded to the real defect on another arm" is
not a floor -- it does not say how small a defect the n=1 arm could have hidden.
This measures that floor.

METHOD
  Plant a synthetic version of the real defect into the n=1 arm and sweep its
  depth. The real mechanism, read out of ORCH's own transect, is GREEN falling
  at the boundary while red barely moves: 145 143 142 141 140 137 137 139 144.
  So the plant is a narrow gaussian subtracted from G at the tracked edge, which
  raises R-G by its depth -- the same sign and shape as the thing being looked
  for, not a generic perturbation.

  The statistic is imported unmodified from budfringe7. This ladder therefore
  characterises the number section 21 actually reported, not a new one.

ANCHORING
  A plant that silently fails to apply produces a small OVER and reads as
  "instrument is blind", which is the flattering direction and would inflate the
  quoted floor. So every rung asserts the array really changed and that the
  achieved depth matches the requested depth. A plant that does not land raises.

  A = 0 must reproduce the unplanted value exactly, or the harness is not inert.
  The control rows must not move at all, or the plant is leaking.

PRE-REGISTERED CRITERION, stated before the run
  Detected at depth A iff OVER(A) > CTL, the same comparison section 21 used
  between arms. The reported floor is the smallest A on the grid that satisfies
  it. OVER - OVER0 is printed alongside so a stricter reader can apply their own
  criterion to the same grid rather than taking mine.
"""
import os
import numpy as np
import tifffile

from budfringe7 import esf, over_of, SX, SY, CTL_Y, TRACK, GRID, load

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
ARM = os.path.join(OUT, "one-fb-pyramid.tiff")
NAME = "n=1 pyramid (NO election)"

SIGMA = 1.5
LADDER = (0, 25, 50, 100, 200, 400, 800, 1600)
N_REPORT = 0


def plant(a, y0, x0, depth, nrow):
    """Subtract a gaussian from G at each row's own tracked edge.

    Tracking is replicated from budfringe7.esf so the plant lands where the
    statistic will look. Returns (array, n_changed, achieved_peak_depth).
    """
    b = a.astype(np.int32).copy()
    if depth == 0:
        return b.astype(np.uint16), 0, 0.0
    off = np.arange(-8, 9)
    prof = depth * np.exp(-0.5 * (off / SIGMA) ** 2)
    xp = x0
    hits = 0
    for y in range(y0 - nrow, y0 + nrow + 1):
        band = a[y - 1:y + 2, :, :].astype(np.float64).mean(0)
        w = band[xp - TRACK:xp + TRACK + 1, 1]
        xp = xp - TRACK + int(np.argmax(np.abs(np.diff(w, prepend=w[:1]))))
        for dy in (-1, 0, 1):
            b[y + dy, xp - 8:xp + 9, 1] -= prof.astype(np.int32)
            hits += 1
    lo = int(b[:, :, 1].min())
    d = a.astype(np.int32) - b
    ach = float(d.max())
    if lo < 0:
        print(f"      WARNING depth {depth}: green clipped at 0, "
              f"achieved depth is not the requested depth")
    return np.clip(b, 0, 65535).astype(np.uint16), int((d != 0).sum()), ach


def main():
    print("=" * 78)
    print("AMPLITUDE LADDER -- what could the n=1 arm have hidden?")
    print("=" * 78)
    if not os.path.exists(ARM):
        print("  ARM MISSING -- this is not a pass")
        return 1

    a = load(ARM)
    ctl0 = over_of(esf(a, CTL_Y, SX, False, False, N_REPORT))
    over0 = over_of(esf(a, SY, SX, False, True, N_REPORT))
    print(f"\n  arm            : {NAME}")
    print(f"  address        : ABS ({SX},{SY}), control row {CTL_Y}")
    print(f"  averaging      : N = {N_REPORT} ({2*N_REPORT+1} rows), the most")
    print("                   sensitive rung of the take-7 grid")
    print(f"  unplanted OVER : {over0:>8.1f} DN")
    print(f"  unplanted CTL  : {ctl0:>8.1f} DN")
    print(f"  criterion      : detected iff OVER > CTL  (pre-registered)")

    print(f"\n    {'depth A':>8} {'px hit':>7} {'achieved':>9} "
          f"{'OVER':>8} {'OVER-OVER0':>11} {'CTL':>8} {'seen':>5}")
    floor = None
    for A in LADDER:
        b, nch, ach = plant(a, SY, SX, A, N_REPORT)
        if A > 0:
            if nch == 0:
                raise SystemExit(f"PLANT DID NOT LAND at depth {A} -- "
                                 f"0 samples changed. Refusing to report a "
                                 f"floor from an instrument that was never fed.")
            if ach < 0.6 * A:
                raise SystemExit(f"PLANT UNDER-APPLIED at depth {A}: achieved "
                                 f"{ach:.0f}. Refusing to quote a floor.")
        ov = over_of(esf(b, SY, SX, False, True, N_REPORT))
        ct = over_of(esf(b, CTL_Y, SX, False, False, N_REPORT))
        if A == 0:
            if abs(ov - over0) > 1e-9 or abs(ct - ctl0) > 1e-9:
                raise SystemExit("HARNESS NOT INERT at A=0 -- the plant path "
                                 "changes the answer with nothing planted.")
        else:
            if abs(ct - ctl0) > 1e-9:
                raise SystemExit(f"PLANT LEAKED into the control at depth {A}: "
                                 f"CTL moved {ctl0:.1f} -> {ct:.1f}")
        seen = ov > ct
        if seen and floor is None and A > 0:
            floor = A
        print(f"    {A:>8} {nch:>7} {ach:>9.0f} {ov:>8.1f} "
              f"{ov - over0:>11.1f} {ct:>8.1f} {str(seen):>5}")
        del b

    print()
    if floor is None:
        print(f"  NO RUNG DETECTED up to {LADDER[-1]} DN. The n=1 silence in")
        print("  section 21 is UNQUALIFIED and must be withdrawn as evidence.")
        rc = 1
    else:
        print(f"  FLOOR = {floor} DN. Section 21's n=1 result should read:")
        print(f"    'no overshoot at or above {floor} DN at this address',")
        print(f"  not 'no overshoot'. For scale, the default arm reads +233 DN")
        print(f"  on this same statistic, which is {233.0/floor:.1f}x the floor.")
        rc = 0
    print("\n  A=0 reproduced the unplanted value and the control never moved,")
    print("  so the ladder is measuring the plant and not the harness.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
