"""ORCH: is the deep-stack collapse arithmetic?

The shipping merge (pyramid.rs) forms per-level, per-pixel weights

    w_k = (excess_k / max(floor,1) / SNR_REF) ** p        then normalises by sum_k w_k

with p from the ladder 8,8,8,5,4,3,2 (finest -> coarsest) and SNR_REF cancelling
in the normalised weight.  Nothing in that expression mentions N.

CLAIM UNDER TEST (mine, ARGUED until this file runs):
    the winner's normalised share falls like 1/(1 + (N-1) r^p) where r is the
    typical loser/winner band-energy ratio, so the merge degrades toward the mean
    of blurred frames as the stack deepens -- with no band limit involved, which
    is what V-SOFTCHECK's N-independence argument requires.

This file is pure arithmetic on the published weight law.  It measures nothing
about real pixels and proves nothing about real stacks; it only says whether the
law *can* produce the observed N-dependence.  If the share at N=299 is not
dramatically below the share at N=22, the hypothesis is dead here and cheaply.

Commissioning: two controls that must behave, or the arithmetic is not the
arithmetic in the source.
  C1  p -> infinity must give share -> 1 for any r < 1 (pure winner-take-all)
  C2  p = 0 must give share -> 1/N exactly (pure mean)
Both are checked and the script exits non-zero if either fails.
"""

import sys

# the ladder in pyramid.rs, finest -> coarsest
LADDER = [8, 8, 8, 5, 4, 3, 2]

# frame counts that appear in the measured record
NS = [22, 32, 63, 105, 299]

# typical loser/winner band-energy ratios.  0.3 is a frame one or two focus
# steps off peak; 0.7 is a near-tie (flat region or shallow step); 0.1 is a
# frame far off peak.
RS = [0.1, 0.3, 0.5, 0.7, 0.9]


def share(n, r, p):
    """Winner's normalised share when 1 frame has energy 1 and n-1 have r."""
    return 1.0 / (1.0 + (n - 1) * (r ** p))


def n_eff(n, r, p):
    """Participation ratio (sum w)^2 / sum w^2 -- the same statistic
    V-NEVERWORSE reports out of the Rust merge."""
    w1 = 1.0
    wr = r ** p
    s1 = w1 + (n - 1) * wr
    s2 = w1 * w1 + (n - 1) * wr * wr
    return (s1 * s1) / s2


def commission():
    ok = True
    # C1: huge p is winner-take-all
    s = share(299, 0.9, 4000)
    if not (s > 0.999999):
        print(f"  C1 FAIL: p->inf share = {s!r}, expected ~1")
        ok = False
    else:
        print(f"  C1 pass: p=4000, N=299, r=0.9 -> share {s:.6f} (winner-take-all)")
    # C2: p = 0 is the plain mean
    s = share(299, 0.3, 0)
    if abs(s - 1.0 / 299) > 1e-12:
        print(f"  C2 FAIL: p=0 share = {s!r}, expected {1/299!r}")
        ok = False
    else:
        print(f"  C2 pass: p=0, N=299 -> share {s:.6f} = 1/299 exactly (plain mean)")
    return ok


def main():
    print("COMMISSIONING")
    if not commission():
        print("\nARITHMETIC IS NOT THE ARITHMETIC. Stop.")
        return 1
    print()

    print("WINNER'S NORMALISED SHARE, by exponent and stack depth")
    print("(1 winner at energy 1.0, N-1 losers at energy r)")
    for p in sorted(set(LADDER)):
        lvls = [i for i, q in enumerate(LADDER) if q == p]
        print(f"\n  exponent p={p}   (pyramid levels {lvls}, finest=0)")
        hdr = "    r      " + "".join(f"N={n:<8}" for n in NS)
        print(hdr)
        for r in RS:
            row = f"    {r:<6.1f} "
            for n in NS:
                row += f"{share(n, r, p):<10.4f}"
            print(row)

    print("\n\nEFFECTIVE PARTICIPATION n_eff = (sum w)^2 / sum w^2")
    print("(this is the statistic the falsifier reads out of the Rust merge)")
    for p in [8, 4, 2]:
        print(f"\n  exponent p={p}")
        hdr = "    r      " + "".join(f"N={n:<8}" for n in NS)
        print(hdr)
        for r in RS:
            row = f"    {r:<6.1f} "
            for n in NS:
                row += f"{n_eff(n, r, p):<10.2f}"
            print(row)

    print("\n\nTHE TWO NUMBERS THAT DECIDE IT")
    print("  V-SOFTCHECK measured 63 frames merging SOFTER than 32 at matched range.")
    for r in [0.3, 0.5, 0.7]:
        for p in [8, 4, 2]:
            s32, s63 = share(32, r, p), share(63, r, p)
            print(f"    r={r} p={p}:  share(32)={s32:.4f}  share(63)={s63:.4f}"
                  f"   ratio {s63/s32:.3f}")
    print()
    print("  V-LINEAR measured bee (N=299) retaining 0.180 / 0.060 of comparator detail.")
    for r in [0.3, 0.5, 0.7]:
        for p in [8, 4, 2]:
            s22, s299 = share(22, r, p), share(299, r, p)
            print(f"    r={r} p={p}:  share(22)={s22:.4f}  share(299)={s299:.4f}"
                  f"   ratio {s299/s22:.3f}")

    print("\n\nWHAT AN N-INVARIANT LAW WOULD HAVE TO DO")
    print("  Target: hold n_eff at a fixed value regardless of N.")
    print("  Solve for the p that gives n_eff = 6 at each (N, r):")
    hdr = "    r      " + "".join(f"N={n:<8}" for n in NS)
    print(hdr)
    for r in RS:
        row = f"    {r:<6.1f} "
        for n in NS:
            lo, hi = 0.0, 200.0
            if n_eff(n, r, hi) > 6.0 or n_eff(n, r, lo) < 6.0:
                row += f"{'--':<10}"
                continue
            for _ in range(200):
                mid = 0.5 * (lo + hi)
                if n_eff(n, r, mid) > 6.0:
                    lo = mid
                else:
                    hi = mid
            row += f"{0.5*(lo+hi):<10.2f}"
        print(row)
    print("\n  A single fixed p cannot sit on any row of that table.")
    print("  That is the shape of the defect, if the defect is this.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
