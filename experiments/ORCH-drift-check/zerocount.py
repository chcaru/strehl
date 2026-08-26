"""Count exact-zero RGB pixels in shipped masters.

Decisive for one question: was the delivered gallery hull-clamped?

BUILD-HULL measured that the UNCLAMPED pyramid merge emits 122,416 exact-zero
RGB pixels (0.371%) on flower-bud-alone-cpl, in a region the estimator renders
at median ~3920 DN. Exact zero maps to exact zero under any monotone tone
curve, so this count is readable directly off the --srgb master without any
cross-tone-curve comparison.

  ~0 zeros    -> the delivered render IS clamped
  ~122k zeros -> the delivered render is NOT clamped, and the owner has been
                 looking at crushed subjects
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

SHIP = Path(r"C:\dev\strehl-out\SHIP-V1")

# BUILD-HULL's two clipping subjects, plus a control it measured as clean.
SUBJECTS = [
    ("flower-bud-alone-cpl", 122416, 0.371),
    ("dry-erase-marker-head-cpl", None, 1.048),
    ("bee-3-cpl", None, None),
    ("coffee-bean", None, None),
]


def main() -> int:
    print(f"{'subject':<34} {'shape':>18} {'zeroRGB':>10} {'pct':>8} {'lum<500':>9} {'median':>8}")
    print("-" * 94)
    for name, expect_n, expect_pct in SUBJECTS:
        p = SHIP / f"{name}.tiff"
        if not p.exists():
            print(f"{name:<34} MISSING {p}")
            continue
        a = tifffile.imread(str(p))
        assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
        assert a.ndim == 3 and a.shape[2] == 3, f"expected HxWx3, got {a.shape}"
        zero = np.all(a == 0, axis=2)
        n_zero = int(zero.sum())
        total = a.shape[0] * a.shape[1]
        lum = a.astype(np.float32).mean(axis=2)
        n_dark = int((lum < 500).sum())
        note = ""
        if expect_pct is not None:
            note = f"   (unclamped expectation {expect_pct}%)"
        print(
            f"{name:<34} {str(a.shape):>18} {n_zero:>10,} "
            f"{100.0 * n_zero / total:>7.3f}% {100.0 * n_dark / total:>8.3f}% "
            f"{np.median(lum):>8.1f}{note}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
