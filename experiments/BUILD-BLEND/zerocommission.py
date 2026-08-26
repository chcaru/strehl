"""Commission zerocount.py before believing its +0.0000.

A metric that reports "no change" is worthless until it has been shown to move.
zerocount.py returned +0.0000 on every channel of every subject, at every
threshold from 0 to 256.  That is either a genuine pass or an instrument that
cannot see the thing it counts, and the two are indistinguishable from the
output alone.

Three checks:

  1. What is the actual floor of these renders?  If the darkest pixel is
     thousands of DN above zero, a zero-count is vacuous on this data and the
     +0.0000 means "not measured", not "not present".
  2. Positive control: plant a known number of exact zeros and confirm the
     counter reports exactly that number.
  3. Compare the two arms at the low end with a statistic that is NOT
     thresholded at zero, so that a real difference in shadow rendering cannot
     hide behind a floor that never reaches zero.
"""

import glob
import os
import sys

import numpy as np
import tifffile

D = sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\BUILD-BLEND\acceptance"
CH = ("R", "G", "B")


def main():
    pairs = sorted(glob.glob(os.path.join(D, "*-estimator.tiff")))
    if not pairs:
        raise SystemExit(f"no renders under {D}")

    print("=== 1. where is the floor? ===")
    print(f"{'subject':<28} {'arm':<10} {'ch':<3} {'min':>7} {'p0.01%':>8} "
          f"{'p1%':>8} {'<256':>8} {'<1024':>8}")
    for pb in pairs:
        s = os.path.basename(pb).rsplit("-", 1)[0]
        for arm in ("estimator", "pyramid"):
            p = os.path.join(D, f"{s}-{arm}.tiff")
            if not os.path.exists(p):
                continue
            img = tifffile.imread(p)
            n = img.shape[0] * img.shape[1]
            for c in range(img.shape[2]):
                v = img[:, :, c]
                print(f"{s:<28} {arm:<10} {CH[c]:<3} {int(v.min()):>7} "
                      f"{np.percentile(v, 0.01):>8.0f} {np.percentile(v, 1):>8.0f} "
                      f"{100.0 * float((v < 256).sum()) / n:>7.4f}% "
                      f"{100.0 * float((v < 1024).sum()) / n:>7.4f}%")
        print()

    print("=== 2. positive control: can the counter see a planted zero? ===")
    img = tifffile.imread(pairs[0]).copy()
    n = img.shape[0] * img.shape[1]
    rng = np.random.default_rng(20260826)
    want = 12345
    idx = rng.choice(n, size=want, replace=False)
    # Write through 2-D indices.  `img[:, :, 2].ravel()` returns a *copy* for a
    # non-contiguous slice, so assigning into it plants nothing -- which is
    # exactly how this control failed the first time it was run.
    ys, xs = np.unravel_index(idx, (img.shape[0], img.shape[1]))
    img[ys, xs, 2] = 0
    got = int((img[:, :, 2] == 0).sum())
    pct = 100.0 * got / n
    print(f"  planted {want} exact zeros, counter reports {got} ({pct:.4f}% of frame)")
    if got != want:
        raise SystemExit("POSITIVE CONTROL FAILED: counter cannot see planted zeros")
    print("  positive control exact. the counter works; the data has no zeros to find.")

    print("\n=== 3. shadow comparison NOT thresholded at zero ===")
    print("  (if the arms differ in the shadows, it must show here even with no zeros)")
    print(f"{'subject':<28} {'ch':<3} {'BEFORE p0.1%':>13} {'AFTER p0.1%':>13} {'delta DN':>9}")
    for pb in pairs:
        s = os.path.basename(pb).rsplit("-", 1)[0]
        pa = os.path.join(D, f"{s}-pyramid.tiff")
        if not os.path.exists(pa):
            continue
        B = tifffile.imread(pb)
        A = tifffile.imread(pa)
        for c in range(A.shape[2]):
            qb = np.percentile(B[:, :, c], 0.1)
            qa = np.percentile(A[:, :, c], 0.1)
            print(f"{s:<28} {CH[c]:<3} {qb:>13.0f} {qa:>13.0f} {qa - qb:>+9.0f}")
        print()


if __name__ == "__main__":
    main()
