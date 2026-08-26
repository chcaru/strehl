"""What changed between the two builds, on a path with no hull code in either?

The estimator backend contains no `Hull` code in either binary, so any difference
between S-estimator and W-estimator is the intervening commits, not the clamp.
This says which channels moved and whether the movement is geometric (a warp,
e.g. a chromatic-aberration correction, which displaces R and B relative to G) or
photometric (a level change, which does not move edges).

The discriminator: a geometric change concentrates its difference where the image
has gradient, because shifting a flat region by a fraction of a pixel changes
nothing. A photometric change does not care about gradient.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from bhull2 import CHANNELS, load16

D = Path("warp")


def main() -> int:
    s = load16(D / "merge-S-estimator.tiff").astype(np.int32)
    w = load16(D / "merge-W-estimator.tiff").astype(np.int32)
    d = s - w
    print("=== build difference on a path with NO hull code in either build ===")
    print("  S = ORCH-SHIP 705C22D5 (3:52 AM)   W = VERIFY-WIRE 6E4B3696 (10:55 PM)")
    print(f"  both rendered --merge estimator on the same 205-frame aligned basis\n")

    print(f"  {'ch':<4} {'samples':>10} {'identical':>11} {'differing':>11} "
          f"{'pct':>8} {'max|d|':>8} {'mean d':>9}")
    tot_same = 0
    for ci, cn in enumerate(CHANNELS):
        dc = d[:, :, ci]
        same = int((dc == 0).sum())
        tot_same += same
        print(f"  {cn:<4} {dc.size:>10} {same:>11} {int((dc != 0).sum()):>11} "
              f"{100.0 * (dc != 0).mean():>7.3f}% {int(np.abs(dc).max()):>8} "
              f"{dc.mean():>+9.2f}")
    assert tot_same + int((d != 0).sum()) == d.size, "channel partition does not sum"

    # Geometric vs photometric. Gradient is measured on W alone so the test
    # cannot be circular -- it never consults the difference it is explaining.
    g = load16(D / "merge-W-estimator.tiff").astype(np.float32).mean(axis=2)
    gy, gx = np.gradient(g)
    grad = np.hypot(gy, gx)
    edges = grad >= np.percentile(grad, 90)
    flat = grad <= np.percentile(grad, 50)
    print("\n  where does the difference live? (gradient measured on W only)")
    print(f"  {'ch':<4} {'mean|d| edges':>15} {'mean|d| flat':>14} {'ratio':>8}")
    for ci, cn in enumerate(CHANNELS):
        ad = np.abs(d[:, :, ci]).astype(np.float64)
        e, f = ad[edges].mean(), ad[flat].mean()
        print(f"  {cn:<4} {e:>15.2f} {f:>14.2f} {(e / f if f > 0 else float('inf')):>8.1f}x")

    print("\n  reading: a difference concentrated on edges is geometric (a warp);")
    print("  one that is flat-vs-edge indifferent is photometric (a level change).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
