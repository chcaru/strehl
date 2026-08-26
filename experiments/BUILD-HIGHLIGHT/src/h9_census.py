"""How much of the frame the roll-off touched, and how hard -- the regression
census.

`h6_compare` answers "did the colour cast go", on the hot set. This answers the
opposite question, which a print corpus cares about just as much: "what did it
cost everywhere else". Luminance is preserved by construction and that is
asserted in Rust; what can be lost here is *saturation*, so saturation is what
is measured, over the whole frame and as a distribution rather than a mean.

Saturation is taken as `(max_c - min_c) / max_c` on the rendered triple: 0 for a
neutral pixel, 1 for a fully saturated one, and independent of brightness, so a
highlight going white and a shadow going grey are the same number.
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import dump

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def sat(f):
    mx = f.max(axis=2)
    mn = f.min(axis=2)
    return np.where(mx > 0, (mx - mn) / np.maximum(mx, 1.0), 0.0)


def main():
    subject, before, after = sys.argv[1], sys.argv[2], sys.argv[3]
    a = tifffile.imread(before).astype(np.float32)
    b = tifffile.imread(after).astype(np.float32)
    assert a.shape == b.shape, f"{a.shape} vs {b.shape}"
    n = a[..., 0].size

    d = np.abs(b - a).max(axis=2)
    moved = d > 0
    print("=" * 96)
    print(f"{subject}: regression census")
    print("=" * 96)
    print(f"  frame {a.shape[1]} x {a.shape[0]} = {n:,} px")
    print(f"  {'threshold':>14}   {'fraction':>10}   {'pixels':>12}")
    for th in (0, 1, 256, 1024, 4096, 16384):
        m = d > th
        print(f"  |d| > {th:7d} DN   {m.mean() * 100:9.5f}%   {int(m.sum()):12,}")

    ya, yb = a @ LUMA, b @ LUMA
    sa, sb = sat(a), sat(b)
    out = {"moved_frac": float(moved.mean())}
    if moved.any():
        dy = np.abs(yb - ya)[moved]
        ds = (sb - sa)[moved]
        print()
        print("  ON THE PIXELS THAT MOVED")
        print(f"    luminance |dY|   mean {dy.mean():9.1f}  p99 {np.percentile(dy, 99):9.1f}"
              f"  max {dy.max():9.1f} DN")
        print(f"    saturation       before {sa[moved].mean():.4f}  after {sb[moved].mean():.4f}"
              f"  mean d {ds.mean():+.4f}")
        print(f"    saturation lost  p50 {np.percentile(-ds, 50):+.4f}"
              f"  p99 {np.percentile(-ds, 99):+.4f}  max {(-ds).max():+.4f}")
        # A pixel is only allowed to lose saturation for one reason: it is near
        # the container. Report the level of what moved, so a claim that the
        # roll-off stayed in the highlights is checkable rather than asserted.
        print(f"    level max_c      p1  {np.percentile(a.max(axis=2)[moved], 1):8.0f}"
              f"  p50 {np.percentile(a.max(axis=2)[moved], 50):8.0f}"
              f"  min {a.max(axis=2)[moved].min():8.0f} DN")
        out.update(
            dy_mean=float(dy.mean()), dy_max=float(dy.max()),
            sat_before=float(sa[moved].mean()), sat_after=float(sb[moved].mean()),
            sat_lost_p99=float(np.percentile(-ds, 99)),
            level_min=float(a.max(axis=2)[moved].min()),
        )
    print()
    print("  WHOLE FRAME")
    print(f"    mean saturation  before {sa.mean():.5f}  after {sb.mean():.5f}"
          f"   ({(sb.mean() / sa.mean() - 1) * 100:+.3f}%)")
    print(f"    mean luminance   before {ya.mean():.1f}  after {yb.mean():.1f}"
          f"   ({(yb.mean() / ya.mean() - 1) * 100:+.3f}%)")
    out.update(sat_frame_before=float(sa.mean()), sat_frame_after=float(sb.mean()),
               y_frame_before=float(ya.mean()), y_frame_after=float(yb.mean()))
    dump(f"h9-{subject}", out)


if __name__ == "__main__":
    main()
