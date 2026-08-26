"""Through-focus curves per region, with the instrument diagnosed rather than trusted.

v1 of this census reported the argmax frame index and nothing else, and returned
index 0 for 20 of 24 regions on a 176-frame bracket. The first frame being
sharpest almost everywhere is not a plausible fact about a focus stack, so this
version does not report a verdict until the curve behind it has been looked at.

Three specific repairs to v1:

1. **v1's pileup test was one-sided.** It asked only whether the argmax sat
   near the LAST frame, so a sweep that ran out at the NEAR end -- which is
   exactly what an argmax of 0 suggests -- was classified as "every region has
   an interior optimum". A discriminator that can only detect one of the two
   ways its subject can fail is the same defect this report retracted in s36.4.
   Regions are now classified against BOTH ends.

2. **The whole curve is kept, not just its maximum.** A region that the bracket
   covered has an interior PEAK; a region the sweep never reached has a
   MONOTONIC curve; a region that was never in focus at all is FLAT and its
   argmax is decided by noise. These three are indistinguishable from a maximum
   and are trivially distinguished from a curve.

3. **Two independent focus statistics, and they must agree.** `mean|grad I| /
   mean I` is normalised by intensity, and that normalisation is not
   noise-neutral: photon noise scales as sqrt(I), so its contribution to the
   ratio scales as 1/sqrt(I) and a brightness ramp across the bracket can move
   the argmax on its own. The variance of the Laplacian over mean squared has a
   different noise dependence. If the two disagree about where a region peaks,
   the peak is an artifact of the normalisation and neither is reported.

A per-frame mean-intensity trace is printed for the same reason: if the bracket
has an exposure ramp, it must be visible rather than inferred.

Linear light throughout: gamma=(1,1), no_auto_bright=True.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rawpy

COLS, ROWS = 6, 4


def stats(g: np.ndarray):
    """(contrast-normalised gradient, normalised Laplacian variance) per region."""
    h, w = g.shape
    a = np.zeros((ROWS, COLS))
    b = np.zeros((ROWS, COLS))
    for r in range(ROWS):
        for c in range(COLS):
            t = g[r * h // ROWS:(r + 1) * h // ROWS, c * w // COLS:(c + 1) * w // COLS]
            m = t.mean()
            if m <= 0:
                continue
            gy, gx = np.gradient(t)
            a[r, c] = np.hypot(gy, gx).mean() / m
            lap = (t[:-2, 1:-1] + t[2:, 1:-1] + t[1:-1, :-2] + t[1:-1, 2:]
                   - 4.0 * t[1:-1, 1:-1])
            b[r, c] = lap.var() / (m * m)
    return a, b


def classify(curve: np.ndarray) -> tuple[str, int]:
    n = len(curve)
    k = int(np.argmax(curve))
    lo, hi = curve.min(), curve.max()
    rng = hi - lo
    if rng <= 0:
        return "FLAT", k
    # Peak prominence against BOTH endpoints, not just the maximum's value.
    prom = min(hi - curve[0], hi - curve[-1]) / rng
    edge = max(2, n // 25)
    if prom < 0.15:
        if k <= edge:
            return "MONOTONIC-FALLING (sweep started past it)", k
        if k >= n - 1 - edge:
            return "MONOTONIC-RISING (sweep stopped short)", k
        return "FLAT (never in focus)", k
    return "INTERIOR PEAK (covered)", k


def main() -> int:
    src = Path(sys.argv[1])
    frames = sorted(src.glob("*.ARW"))
    n = len(frames)
    print(f"{n} frames from {src}\n")

    A = np.zeros((n, ROWS, COLS))
    B = np.zeros((n, ROWS, COLS))
    means = np.zeros(n)
    for i, f in enumerate(frames):
        with rawpy.imread(str(f)) as raw:
            rgb = raw.postprocess(half_size=True, gamma=(1, 1), no_auto_bright=True,
                                  output_bps=16, use_camera_wb=True)
        g = rgb[:, :, 1].astype(np.float64)
        means[i] = g.mean()
        A[i], B[i] = stats(g)
        if (i + 1) % 50 == 0 or i + 1 == n:
            print(f"  ...{i + 1}/{n}")

    print(f"\nEXPOSURE TRACE (frame mean, linear DN): first {means[0]:.1f}, "
          f"last {means[-1]:.1f}, min {means.min():.1f}, max {means.max():.1f}, "
          f"max/min {means.max() / max(means.min(), 1e-9):.3f}")

    print("\nPER-REGION CLASSIFICATION  (columns LEFT to RIGHT)")
    agree = 0
    total = 0
    for r in range(ROWS):
        cells = []
        for c in range(COLS):
            ka = classify(A[:, r, c])
            kb = classify(B[:, r, c])
            total += 1
            same = ka[0].split()[0] == kb[0].split()[0]
            agree += same
            cells.append(f"{ka[1]:>4d}{'' if same else '!'}")
        print("   " + "".join(f"{v:>8s}" for v in cells))
    print(f"   (argmax frame index; '!' = the two statistics DISAGREE)")
    print(f"   statistics agree on class in {agree}/{total} regions")

    print("\n   class per region, statistic A:")
    for r in range(ROWS):
        for c in range(COLS):
            k, idx = classify(A[:, r, c])
            print(f"     row {r} col {c}: argmax {idx:4d}  {k}")

    print("\nTHROUGH-FOCUS CURVES, statistic A, subsampled every 16th frame")
    for r in [0, ROWS // 2]:
        for c in [0, COLS - 1]:
            cur = A[:, r, c]
            s = " ".join(f"{v:.4f}" for v in cur[::16])
            print(f"  row {r} col {c} (left-to-right {c + 1}/{COLS}): {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
