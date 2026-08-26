"""How large are the out-of-hull excursions, in DN?

The hull clamp binds on 11.5-18.9% of pixels on dry-erase-marker-head-cpl.  That
rate says nothing about whether it matters: 19% of pixels moved by 1 DN is
academic, 19% moved by thousands is the defect ORCH describes.  The design of any
replacement -- in particular whether a noise-calibrated margin is the right shape
-- depends entirely on which of those it is.

`clamped - unclamped` is exactly the correction the hull applied, so its
distribution is the excursion distribution, measured rather than modelled.

One caveat stated plainly: the unclamped render is still written through
`norm`'s `.max(0.0)` and a u16 cast, so excursions that went *below zero* are
truncated at 0 in that file.  The downward magnitudes below are therefore a
LOWER BOUND, and the exact-zero count in the unclamped arm is the count of
pixels whose true excursion is unmeasurable from this file.  Upward excursions
are exact.
"""

import sys

import numpy as np
import tifffile

CH = ("R", "G", "B")


def main():
    pc, pu = sys.argv[1], sys.argv[2]
    C = tifffile.imread(pc).astype(np.int32)
    U = tifffile.imread(pu).astype(np.int32)
    if C.shape != U.shape:
        raise SystemExit("shapes differ")
    n = C.shape[0] * C.shape[1]

    print("=== how many pixels did the hull clamp move, and by how much? ===")
    print(f"{'ch':<3} {'moved':>9} {'median|d|':>10} {'p99|d|':>9} "
          f"{'p99.9|d|':>9} {'max|d|':>9} {'>1000 DN':>10}")
    for c in range(C.shape[2]):
        d = C[:, :, c] - U[:, :, c]
        nz = d[d != 0]
        if nz.size == 0:
            print(f"{CH[c]:<3} {'0':>9}  (clamp never bound in this channel)")
            continue
        a = np.abs(nz)
        big = 100.0 * float((a > 1000).sum()) / n
        print(f"{CH[c]:<3} {100.0 * nz.size / n:>8.3f}% {np.median(a):>10.0f} "
              f"{np.percentile(a, 99):>9.0f} {np.percentile(a, 99.9):>9.0f} "
              f"{a.max():>9.0f} {big:>9.4f}%")

    print("\n=== direction: is the excursion downward into black? ===")
    for c in range(C.shape[2]):
        d = C[:, :, c] - U[:, :, c]
        up = int((d > 0).sum())     # clamp raised the value => reconstruction was too LOW
        dn = int((d < 0).sum())     # clamp lowered it       => reconstruction was too HIGH
        tot = up + dn
        if tot == 0:
            continue
        print(f"{CH[c]:<3} clamp RAISED {100.0 * up / tot:5.1f}% of moved pixels "
              f"(reconstruction below hull), LOWERED {100.0 * dn / tot:5.1f}%")

    print("\n=== unmeasurable tail: pixels the u16 floor truncated ===")
    for c in range(U.shape[2]):
        z = int((U[:, :, c] == 0).sum())
        print(f"{CH[c]:<3} unclamped exact-zero {z:>10,} ({100.0 * z / n:7.4f}%)  "
              f"-> true downward excursion unmeasurable from this file")


if __name__ == "__main__":
    main()
