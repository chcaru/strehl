"""Discriminate WHY green differs between a CA-on and a CA-off render.

ORCH measured G differing on 30.87M px (mean 51.39 DN, max 9595 DN) between
`m-default.tiff` and `m-caoff.tiff` and listed three possibilities:

  1. the correction touches G directly
  2. changing R/B changes which FRAME the merge elects, and G moves as a
     second-order consequence
  3. the two renders differ in something besides the flag  <- would confound
     the whole comparison, including ORCH's +30% hue-neutral result

The MERGE pair cannot separate these. The SINGLE-FRAME pair can: with one frame
there is no election and no merge, so possibility 2 is removed by construction.

    single-frame pair G identical  -> NOT (1). NOT (3). => possibility 2.
    single-frame pair G differs    -> (1) or (3); the correction is not
                                      green-preserving as documented, or the
                                      pair is not a controlled A/B.

That is a real discriminator and it needs no new render.
"""
import sys
import numpy as np
import tifffile


def cmp(tag, pa, pb):
    a = tifffile.imread(pa)
    b = tifffile.imread(pb)
    if a.shape != b.shape:
        print(f"{tag}: SHAPE MISMATCH {a.shape} vs {b.shape} -- not a controlled pair")
        return None
    out = {}
    for i, ch in enumerate("RGB"):
        x = a[..., i].astype(np.int64)
        y = b[..., i].astype(np.int64)
        d = np.abs(x - y)
        n = int((d != 0).sum())
        out[ch] = (n, float(d.mean()), int(d.max()))
        pct = 100.0 * n / d.size
        print(f"  {tag:14s} {ch}  differs {n:>12,} px ({pct:6.3f}%)  "
              f"mean {d.mean():8.3f} DN  max {d.max():>6d} DN")
    return out


def main():
    base = r"D:\strehl-out\BUILD-CROP\chroma"
    print("Does the CA correction move GREEN? Merge pair vs single-frame pair.\n")
    print("MERGE pair (299/300 frames -- election is live, cannot isolate):")
    m = cmp("merge", rf"{base}\m-default.tiff", rf"{base}\m-caoff.tiff")
    print("\nSINGLE-FRAME pair (no merge, no election -- the control):")
    s = cmp("single", rf"{base}\s1-default.tiff", rf"{base}\s2-caoff.tiff")

    if m is None or s is None:
        print("\nUNSCORED: a pair was not comparable.")
        return 2

    print()
    gm, gs = m["G"][0], s["G"][0]
    if gs == 0 and gm > 0:
        print("VERDICT: possibility 2 -- FRAME ELECTION.")
        print("  Green is bit-identical in the single-frame pair (0 px, 0 DN), so")
        print("  the correction IS green-preserving as documented. Green moves in")
        print("  the merge pair only, therefore changing R/B changed which frame")
        print("  the merge elected. The merge A/B is NOT a controlled experiment.")
    elif gs > 0:
        print("VERDICT: possibility 1 or 3 -- the single-frame pair ALSO moves green.")
        print("  The correction is not green-preserving, or the pair differs in")
        print("  more than the flag. Either way the comparison is confounded.")
    else:
        print("VERDICT: green identical in BOTH pairs; ORCH's G finding does not")
        print("  reproduce on these files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
