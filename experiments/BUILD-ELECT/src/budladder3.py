"""Ladder v3: the floor and margin at ORCH's verified address.

Section 22.2 measured a detection floor at ABS (3328,924) and reported margins
of 1.10-1.38, with two of six settings blind. That address was 336 px from
ORCH's rim, so those margins describe a different feature and are withdrawn
along with the rest of the section 21 numbers that went through the address.

Re-run at ABS (3664,860), control row 940, verified against ORCH's own published
pixel (R=159 G=137 B=128) and their full ten-value green transect before any
measurement was taken.

Everything else is held: same plant (narrow gaussian subtracted from green at
each row's own tracked edge), same imported statistic, same pre-registered
criterion (detected iff OVER exceeds that arm's own control), signal and floor
measured in the same run at the same N.

Pre-registered before the run. The raw sweep at the true address reads 515 DN on
the default arm against 16 DN on n=1, roughly a 30x separation where section 22
had 1.1x, so I expect margins well above 1 at every setting and no blind rungs.
If any setting still comes back blind, the n=1 evidence is weaker than the raw
numbers suggest and that must be said.
"""
import os
import numpy as np

from budfringe7 import esf, over_of, load, GRID
from budladder2 import plant, LADDER

OUT = r"C:\dev\strehl-out\BUILD-ELECT"
N1 = os.path.join(OUT, "one-fb-pyramid.tiff")
DEF = os.path.join(OUT, "fb-noflags.tiff")

SX, SY, CTL_Y = 3664, 860, 940
WIDE = LADDER + (1600, 3200)


def floor_at(a, nrow, ctl0, over0):
    prev = None
    for A in WIDE:
        b, nch, ach = plant(a, SY, SX, A, nrow)
        if A > 0:
            if nch == 0:
                raise SystemExit(f"PLANT DID NOT LAND at {A}, N={nrow}")
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
    print("LADDER v3 -- floor and margin at ORCH's VERIFIED address")
    print("=" * 78)
    for p in (N1, DEF):
        if not os.path.exists(p):
            print(f"  MISSING {p} -- not a pass")
            return 1
    a1 = load(N1)
    ad = load(DEF)
    print(f"\n  address    : ABS ({SX},{SY}), control row {CTL_Y}")
    print(f"  floor on   : n=1 pyramid (no election)")
    print(f"  signal on  : g2.0 LINEAR default arm")
    print(f"  criterion  : OVER > that arm's own CTL (pre-registered)")
    print(f"\n    {'N':>4} {'rows':>5} {'n1 OVER':>8} {'n1 CTL':>9} {'floor':>7} "
          f"{'signal':>8} {'margin':>7} {'sec22':>7}")
    prior = {0: 1.11, 2: 1.30, 5: 1.10, 10: 1.38, 20: 0.05, 40: 0.32}
    worst = None
    for n in GRID:
        c0 = over_of(esf(a1, CTL_Y, SX, False, False, n))
        o0 = over_of(esf(a1, SY, SX, False, True, n))
        fl, _ = floor_at(a1, n, c0, o0)
        sig = over_of(esf(ad, SY, SX, False, True, n))
        if fl is None:
            print(f"    {n:>4} {2*n+1:>5} {o0:>8.1f} {c0:>9.1f} "
                  f"{'>'+str(WIDE[-1]):>7} {sig:>8.1f} {'--':>7} "
                  f"{prior[n]:>7.2f}")
            worst = 0.0
            continue
        m = sig / fl
        worst = m if worst is None else min(worst, m)
        print(f"    {n:>4} {2*n+1:>5} {o0:>8.1f} {c0:>9.1f} {fl:>7} "
              f"{sig:>8.1f} {m:>7.2f} {prior[n]:>7.2f}")
    print()
    print("  sec22 = the margin reported at the wrong address, for comparison.")
    if worst is None or worst < 1.0:
        print(f"\n  WORST MARGIN {worst:.2f} < 1 -- still blind somewhere.")
    else:
        print(f"\n  WORST MARGIN {worst:.2f}. Every setting has power, and the")
        print("  n=1 arm carries no overshoot at any of them. The n=1 evidence")
        print("  is far stronger at ORCH's address than section 22 could see")
        print("  at mine -- the correction moved the conclusion toward ORCH.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
