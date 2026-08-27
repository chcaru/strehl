"""Paired crush census: ORCH's third column, which zeros.py does not compute.

zeros.py reports two unpaired rails (exact-zero, luma<500). ORCH's defect has a
third and larger column -- 721,189 px "darker than ctrl by >2000 DN", 2.19% --
which is a *paired* statistic and appears in no committed instrument.

Per ORCH's standing instruction ("print the rails and the tails beside the
centre, or a catastrophic minority will keep hiding under a healthy centre"),
every row prints rails and tails alongside the median, so a healthy centre
cannot conceal a crushed minority.

Usage:  python crushcensus.py <ctrl.tiff> <tag>=<arm.tiff> [<tag>=<arm.tiff> ...]

Pass the reference itself as an arm to get the null control. A row that is not
exactly zero everywhere on the null is a broken instrument, not a finding.
"""
import sys
import numpy as np
import tifffile

CRUSH_DN = 2000.0


def luma(a):
    a = a.astype(np.float64)
    if a.ndim == 2:
        return a
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def rails(a, y):
    z = (a <= 0).all(axis=2) if a.ndim == 3 else (a <= 0)
    hi = (a >= 65535).all(axis=2) if a.ndim == 3 else (a >= 65535)
    return 100 * z.mean(), 100 * hi.mean(), 100 * (y < 500).mean()


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ref_path = sys.argv[1]
    ref = tifffile.imread(ref_path)
    ry = luma(ref)
    print(f"reference: {ref_path}")
    print(f"crush threshold: ctrl - arm > {CRUSH_DN:.0f} DN\n")

    hdr = (f"{'tag':14s} {'crush px':>11s} {'crush %':>8s} "
           f"{'ctrlmed':>9s} {'armmed':>9s} | "
           f"{'exact0%':>8s} {'sat%':>7s} {'<500%':>7s} | "
           f"{'p0.01':>9s} {'p1':>8s} {'p50':>8s} {'p99':>8s} {'p99.99':>9s}")
    print(hdr)
    print("-" * len(hdr))

    boxes = []
    for spec in sys.argv[2:]:
        tag, _, path = spec.partition("=")
        if not path:
            tag, path = path or spec, spec
        arm = tifffile.imread(path)
        if arm.shape != ref.shape:
            print(f"{tag:14s}  SHAPE MISMATCH {arm.shape} vs {ref.shape}")
            continue
        ay = luma(arm)
        d = ry - ay                      # positive => arm darker than ctrl
        crush = d > CRUSH_DN
        n = int(crush.sum())
        e0, sat, lo = rails(arm, ay)
        cm = np.median(ry[crush]) if n else float("nan")
        am = np.median(ay[crush]) if n else float("nan")
        qs = np.percentile(d, [0.01, 1, 50, 99, 99.99])
        print(f"{tag:14s} {n:11,} {100*crush.mean():7.3f}% "
              f"{cm:9.1f} {am:9.1f} | "
              f"{e0:7.3f}% {sat:6.3f}% {lo:6.3f}% | "
              f"{qs[0]:9.1f} {qs[1]:8.1f} {qs[2]:8.1f} {qs[3]:8.1f} {qs[4]:9.1f}")
        if n:
            ys, xs = np.nonzero(crush)
            boxes.append((tag, n, ys.min(), ys.max(), xs.min(), xs.max(),
                          ys.mean(), xs.mean()))

    print()
    if boxes:
        print("crushed-region geometry")
        for tag, n, y0, y1, x0, x1, cy, cx in boxes:
            print(f"  {tag:14s} n={n:,}  bbox y {y0}..{y1}  x {x0}..{x1}  "
                  f"centroid y {cy:.0f} x {cx:.0f}")
    else:
        print("crushed-region geometry: no arm had any crushed pixel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
