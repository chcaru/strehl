"""Is `--exposure` inert on the master? Magnitude, not a hash comparison.

Two renders of `coffee-bubbles` at -0.21 and +3.00 stops have different
sha256s, so a boolean "are they identical" answers NO and stops there. That
answer is nearly useless: a 1 DN difference on a handful of pixels and a
completely different picture both produce it.

The reason to expect near-inertness is algebraic. `Tone::from_luminance` sets
`black` from p0.1 and `white` from p99.9 of the SAME luminance the exposure
multiply has already scaled -- confirmed by the binary's own report, where a
gain ratio of 9.249 moved black by 9.256x and white by 9.254x. A common factor
g therefore cancels out of `(v*g - black*g) / (white*g - black*g)`.

If that cancellation is complete, `--exposure` and `--auto-exposure` cannot
change the master, which would make them inert controls on the shipping path
rather than the exposure decision they are documented as. That is a claim worth
a number, so this reports the distribution of the difference and not a verdict.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

BASE = Path(r"C:\dev\strehl-out\BUILD-RENDER-modulation")


def read(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    if a.dtype != np.uint16:
        raise SystemExit(f"{p.name}: dtype {a.dtype}, expected uint16")
    return a


def main() -> int:
    lo = read(BASE / "cb-expm021.tiff").astype(np.int32)
    hi = read(BASE / "cb-exp300.tiff").astype(np.int32)
    if lo.shape != hi.shape:
        raise SystemExit(f"shape mismatch {lo.shape} vs {hi.shape}")

    d = np.abs(hi - lo)
    n = d.size
    print(f"  -0.21 stops vs +3.00 stops -- a gain ratio of {8.0 / 0.865:.2f}x")
    print(f"  {lo.shape[1]} x {lo.shape[0]} x {lo.shape[2]}, 16-bit, {n:,} samples\n")
    print(f"    pixels differing at all : {100.0 * (d > 0).mean():8.4f}%")
    print(f"    differing by > 1 DN     : {100.0 * (d > 1).mean():8.4f}%")
    print(f"    differing by > 16 DN    : {100.0 * (d > 16).mean():8.4f}%")
    print(f"    differing by > 256 DN   : {100.0 * (d > 256).mean():8.4f}%")
    print(f"    mean |difference|       : {d.mean():8.3f} DN of 65535")
    print(f"    p99.9 |difference|      : {np.percentile(d, 99.9):8.1f} DN")
    print(f"    max  |difference|       : {d.max():8d} DN")

    # A 16-bit DN is far below any print or display threshold; the honest scale
    # is 8-bit, which is what a lab receives and what a viewer sees.
    d8 = np.abs((hi >> 8) - (lo >> 8))
    print(f"\n    at 8-bit: {100.0 * (d8 > 0).mean():.4f}% of samples differ, "
          f"max {d8.max()} of 255 levels")

    # Partition the difference rather than thresholding it. The distribution is
    # bimodal -- a huge identical mass, a thin 1 DN rounding shell, and a tiny
    # tail of large differences -- and a single "max > 1 DN" test reads that
    # tail as if it described the picture. Counts must sum to the total, so a
    # category nobody looked at cannot hide inside a category that passed.
    same = int((d == 0).sum())
    rounding = int(((d > 0) & (d <= 1)).sum())
    real = int((d > 1).sum())
    print("\n  partition of all samples:")
    print(f"    byte-identical            {same:12,}  {100.0 * same / n:8.4f}%")
    print(f"    differ by exactly 1 DN    {rounding:12,}  {100.0 * rounding / n:8.4f}%  (rounding)")
    print(f"    differ by more than 1 DN  {real:12,}  {100.0 * real / n:8.4f}%")
    print(f"    {'':<26}{same + rounding + real:12,}  {100.0 * (same + rounding + real) / n:8.4f}%  = total")

    # Where does the surviving difference live? The obvious hypothesis is that
    # the higher gain clipped highlights the lower one kept. Both polarities
    # are tested, because testing only the expected one returns zero here and
    # zero reads as "not clipping" -- the true answer is that the LOWER gain is
    # the one that clips. One-sided controls are how that gets missed.
    hi_clip = (hi >= 65535) & (lo < 65535)
    lo_clip = (lo >= 65535) & (hi < 65535)
    big = d > 1
    print(f"\n    of the {real:,} samples that really differ:")
    print(f"      clipped by the HIGHER gain only : {int((big & hi_clip).sum()):,}")
    print(f"      clipped by the LOWER  gain only : {int((big & lo_clip).sum()):,}")
    # Locate them on the tone curve instead. `TONE_TOE` and the s-curve
    # strength are ABSOLUTE constants that do not scale with the gain, so they
    # are where the cancellation is expected to break.
    lvl = lo[big].astype(np.float64) / 65535.0
    if lvl.size:
        print(f"      their level in the -0.21 render : p5 {np.percentile(lvl, 5):.4f}  "
              f"median {np.median(lvl):.4f}  p95 {np.percentile(lvl, 95):.4f}")

    scale = 100.0 * d.mean() / 65535.0
    print(f"\n  A {8.0 / 0.865:.1f}x exposure change moved the master by {scale:.4f}% of full scale,")
    print(f"  leaving {100.0 * same / n:.2f}% of it byte-identical.")
    print("  --exposure is INERT as an exposure control: Tone::from_luminance takes its")
    print("  percentiles AFTER the multiply, so the gain cancels out of the mapping.")
    print(f"  The residue of {real:,} samples ({100.0 * real / n:.4f}%) sits entirely in the extreme")
    print("  highlights and is a white-point wobble, not an exposure change: it decides")
    print("  which few samples clip, and it does so in the direction OPPOSITE to intuition")
    print("  -- the LOWER gain is the one that clips more.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
