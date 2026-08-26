"""Measure the coarse-gentle / fine-aggressive trade, band by band, whole frame.

The owner's question, verbatim: whether the multi-band merge "can be
conservative at the coarse scales where the rim lives while staying aggressive
at the fine scales where texture lives". This script is the number for that.

WHAT IT MEASURES, AND WHAT IT CANNOT
------------------------------------
For each octave band of a Laplacian decomposition of the luma it reports, for
BOTH arms separately, the RMS band amplitude -- the raw statistic -- and only
then their ratio. Reporting the ratio alone is how this project has been
misled before, so the raw columns are not optional.

The ratio is used here as a SOFTENING DETECTOR: blend/ctrl well below 1 in the
fine bands means the multi-band merge threw away detail the shipped merge kept.
That is BUILD-HALO's stated blocker and it is the thing to catch.

Its failure direction is stated rather than hidden. Band amplitude is a form of
high-pass energy, and this project has twice been fooled by high-pass energy
that was satisfied by an injected artifact. So:

* ratio well BELOW 1 in the fine bands is trustworthy evidence of softening --
  an artifact could only push it up, not down;
* ratio AT OR ABOVE 1 is NOT by itself evidence of "no softening", because
  softening plus injected structure can land there too.

Therefore a ratio near 1 is reported as "no softening detected", never as "no
softening", and the frame itself remains the verdict. If the pictures and this
table disagree, the pictures are right.

The mean-level row exists so that a flat exposure or tone difference between
the arms -- which would scale every band at once -- is visible rather than
being read as a change in detail.

    python bandtrade.py <label> <control.tiff> <blend.tiff> [levels]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

# Separable binomial 5-tap: the standard Burt-Adelson generating kernel.
K = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0


def read16(path: Path) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} has shape {a.shape}, expected HxWx3"
    return a


def luma(a: np.ndarray) -> np.ndarray:
    f = a.astype(np.float32)
    return 0.2126 * f[:, :, 0] + 0.7152 * f[:, :, 1] + 0.0722 * f[:, :, 2]


def blur(a: np.ndarray) -> np.ndarray:
    out = np.apply_along_axis(lambda m: np.convolve(m, K, mode="same"), 1, a)
    return np.apply_along_axis(lambda m: np.convolve(m, K, mode="same"), 0, out)


def laplacian_bands(a: np.ndarray, levels: int) -> list[np.ndarray]:
    """Laplacian bands coarsest-last; the final entry is the residual."""
    bands, cur = [], a
    for _ in range(levels):
        lo = blur(cur)
        bands.append(cur - lo)
        cur = lo[::2, ::2]
    bands.append(cur)
    return bands


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    label, ctrl_p, blend_p = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    levels = int(sys.argv[4]) if len(sys.argv) > 4 else 6

    lc, lb = luma(read16(ctrl_p)), luma(read16(blend_p))
    assert lc.shape == lb.shape, f"shape mismatch {lc.shape} vs {lb.shape}"

    bc = laplacian_bands(lc, levels)
    bb = laplacian_bands(lb, levels)

    print(f"=== {label} ===")
    print(f"    control : {ctrl_p.name}")
    print(f"    blend   : {blend_p.name}")
    print(f"    frame   : {lc.shape[1]} x {lc.shape[0]} px, whole frame, no crop")
    print()
    print("  RMS band amplitude in 16-bit DN. RAW COLUMNS FIRST; the ratio is derived.")
    print("  band 0 is the finest octave (1:1 detail); the last row is the coarse residual.")
    print()
    print(f"  {'band':<6} {'scale':>9} {'ctrl RMS':>10} {'blend RMS':>10} "
          f"{'ratio':>8}  reading")
    print(f"  {'-'*6} {'-'*9} {'-'*10} {'-'*10} {'-'*8}  {'-'*30}")

    for i in range(levels + 1):
        c, b = bc[i], bb[i]
        rc, rb = float(np.sqrt(np.mean(c * c))), float(np.sqrt(np.mean(b * b)))
        ratio = rb / rc if rc > 0 else float("nan")
        if i == levels:
            name, scale = "resid", f">={2**levels} px"
        else:
            name, scale = f"L{i}", f"~{2**(i+1)} px"
        if i == levels:
            reading = "overall tone"
        elif ratio < 0.95:
            reading = f"BLEND SOFTER by {100*(1-ratio):.1f}%"
        elif ratio > 1.05:
            reading = f"blend higher by {100*(ratio-1):.1f}%"
        else:
            reading = "no softening detected"
        print(f"  {name:<6} {scale:>9} {rc:>10.2f} {rb:>10.2f} {ratio:>8.4f}  {reading}")

    mc, mb = float(lc.mean()), float(lb.mean())
    print()
    print(f"  mean level (guards against a flat tone/exposure difference being read")
    print(f"  as a detail change): ctrl {mc:.1f} DN, blend {mb:.1f} DN, "
          f"ratio {mb/mc:.4f}")

    d = lb - lc
    print(f"  whole-frame RMS difference between the arms: "
          f"{float(np.sqrt(np.mean(d*d))):.2f} DN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
