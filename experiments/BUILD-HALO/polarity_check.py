"""Did the upper envelope INVERT on a bright subject over a dark backdrop?

`pencil-steep-angle-cpl`: backdrop 0.369, subject 0.686 -- the polarity-reversed
case. The estimator only ever RAISES, so on this scene every pixel it moves in
the backdrop is a pixel pulled TOWARD the bright occluder, which is the veil
being amplified rather than removed.

The test does not need a distance profile. It needs to know whether the pixels
that moved are dark ones. So the difference is stratified by the BASELINE arm's
own luma: if the lift is concentrated in the dark population, the estimator is
running backwards.

Both arms are the same binary, same flags, differing only in STREHL_VEIL.
"""

from pathlib import Path
import sys

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\VEIL")


def green(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p}: {a.dtype}"
    return a[..., 1].astype(np.float64)


def main() -> int:
    off = OUT / "pen-pm-off.tif"
    on = OUT / "pen-pm-fl.tif"
    for p in (off, on):
        if not p.exists():
            print(f"missing {p}")
            return 2

    a, b = green(off), green(on)
    assert a.shape == b.shape, f"{a.shape} vs {b.shape}"
    d = b - a

    lo, hi = np.percentile(a, 5), np.percentile(a, 95)
    print(f"baseline green: p5 {lo:.0f}  median {np.median(a):.0f}  p95 {hi:.0f} DN")
    print(f"pixels raised >10 DN: {100.0 * np.mean(d > 10):.2f}%   "
          f"lowered >10 DN: {100.0 * np.mean(d < -10):.2f}%")
    print(f"mean change {d.mean():+.1f} DN   max {d.max():+.0f}   min {d.min():+.0f}\n")

    print("change stratified by the BASELINE arm's own luma:")
    print(f"{'baseline luma band':>22}   {'px %':>6}  {'mean dDN':>9}  {'p99 dDN':>8}")
    edges = np.percentile(a, [0, 10, 25, 50, 75, 90, 100])
    for i in range(len(edges) - 1):
        m = (a >= edges[i]) & (a < edges[i + 1] if i < len(edges) - 2 else a <= edges[i + 1])
        if m.sum() == 0:
            continue
        print(f"{edges[i]:8.0f}-{edges[i+1]:8.0f} DN   "
              f"{100.0 * m.mean():6.1f}  {d[m].mean():+9.1f}  {np.percentile(d[m], 99):+8.0f}")

    dark = a < np.percentile(a, 40)
    bright = a > np.percentile(a, 80)
    print(f"\ndark population  (backdrop) mean change {d[dark].mean():+8.1f} DN")
    print(f"bright population (subject) mean change {d[bright].mean():+8.1f} DN")
    print("\nVERDICT: " + (
        "INVERTED -- lift is concentrated in the DARK backdrop, i.e. pulled "
        "toward the bright occluder"
        if d[dark].mean() > max(2.0, d[bright].mean()) else
        "no inversion signature"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
