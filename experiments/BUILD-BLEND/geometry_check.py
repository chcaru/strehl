"""Is the comparison geometrically honest?

A side-by-side is worthless if the two arms are framed differently -- every
difference then has an alternative explanation, and "the rim went away" could
just be "the rim moved out of frame". This checks the two arms are the same
picture of the same thing before any conclusion is drawn from them.

Reports, on a downsampled luma:
  * the best integer shift by brute-force search, and
  * the residual after that shift, against the residual at zero shift.

If the best shift is (0, 0) the two arms share a pixel grid exactly and the
comparison is sound.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile


def luma(path: Path, step: int = 4) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    return a[::step, ::step, :].astype(np.float32).mean(axis=2)


def main() -> int:
    ctrl, blend = Path(sys.argv[1]), Path(sys.argv[2])
    step = 4
    a, b = luma(ctrl, step), luma(blend, step)
    assert a.shape == b.shape, f"different shapes: {a.shape} vs {b.shape}"

    m = 40  # margin, in downsampled px, so a shifted compare stays in bounds
    ref = a[m:-m, m:-m]
    best, bestval = None, None
    for dy in range(-12, 13):
        for dx in range(-12, 13):
            win = b[m + dy:b.shape[0] - m + dy, m + dx:b.shape[1] - m + dx]
            v = float(np.abs(ref - win).mean())
            if bestval is None or v < bestval:
                best, bestval = (dy, dx), v
    zero = float(np.abs(ref - b[m:-m, m:-m]).mean())

    print(f"control : {ctrl.name}")
    print(f"blend   : {blend.name}")
    print(f"grid    : {a.shape[1]}x{a.shape[0]} (downsampled {step}x)")
    print(f"best shift          : dy={best[0] * step:+d} dx={best[1] * step:+d} px (full res)")
    print(f"  mean|diff| there  : {bestval:.2f} DN")
    print(f"  mean|diff| at 0,0 : {zero:.2f} DN")
    if best == (0, 0):
        print("VERDICT : the arms share a pixel grid exactly. The comparison is sound.")
    else:
        print(
            f"VERDICT : the arms are offset by {best[0] * step},{best[1] * step} px. "
            "Differences in the side-by-side are CONFOUNDED with framing."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
