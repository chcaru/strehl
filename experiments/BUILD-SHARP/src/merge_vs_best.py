"""Merge against the best-frame composite, per region, on `flowers-cpl`.

ORCH's question: is most of this frame soft because the capture never covered
it, or because the merge is failing? The decisive comparison is the merge
against the best frame available per region, and one number per region is
enough.

WHY THIS INSTRUMENT AND NOT THE PREVIOUS ONE. The first attempt measured a
contrast-normalised gradient on the RAW frames and took the max over the
bracket. It returned argmax frame 0 for 20 of 24 regions, and the curves behind
that were monotonically DECREASING everywhere -- with an exposure trace showing
the frame mean rising 6671 -> 7909 DN, an 18.5% ramp. `mean|grad| / mean` is
invariant to a global gain in its SIGNAL term but not in its NOISE term: photon
noise scales as sqrt(I), so its contribution to the ratio falls as 1/sqrt(I),
which predicts an ~8.8% decline over that ramp on its own against observed
declines of 10-15%. The statistic was measuring the lamp, not the focus.

`argmax-baseline` avoids this entirely. It is strehl's own negative control and
it selects, per pixel, the frame with the highest NOISE-NORMALISED Tenengrad
measure -- normalised against the calibrated noise model, so an exposure ramp
cannot move its choice the way it moved mine. It is binned rather than
demosaiced, so no interpolation contaminates it, and its output is linear.

READ THE COMPARISON IN THE RIGHT DIRECTION. argmax-baseline does not align, so
it is not a candidate output and it is not being proposed as one; it is being
used only as evidence about what the INPUT contains. If a region is soft in the
best-frame composite, no captured frame holds it sharp.

  merge ~= baseline, both soft   -> the capture did not cover it. Not ours.
  merge << baseline              -> a frame held it and we lost it. Ours.

Both inputs are linear and both are reduced the same way: the demosaiced merge
is box-averaged 2x to the baseline's binned raster so that a demosaic MTF
difference cannot masquerade as a merge deficit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

COLS, ROWS = 6, 4


def load_linear(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p)).astype(np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def box2(a: np.ndarray) -> np.ndarray:
    h, w = (a.shape[0] // 2) * 2, (a.shape[1] // 2) * 2
    return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def acutance(t: np.ndarray) -> float:
    """Gain-invariant local acutance: mean|grad| normalised by the region's own
    RMS contrast rather than by its mean, so a brightness difference between
    the two pipelines cannot register as a sharpness difference."""
    gy, gx = np.gradient(t)
    sd = t.std()
    return float(np.hypot(gy, gx).mean() / sd) if sd > 0 else 0.0


def grid(a: np.ndarray) -> np.ndarray:
    h, w = a.shape
    out = np.zeros((ROWS, COLS))
    for r in range(ROWS):
        for c in range(COLS):
            out[r, c] = acutance(
                a[r * h // ROWS:(r + 1) * h // ROWS, c * w // COLS:(c + 1) * w // COLS])
    return out


def main() -> int:
    merge_p, base_p = Path(sys.argv[1]), Path(sys.argv[2])
    merge = box2(load_linear(merge_p))
    base = load_linear(base_p)
    print(f"merge (box-averaged 2x) : {merge.shape}   {merge_p.name}")
    print(f"best-frame baseline     : {base.shape}   {base_p.name}")
    if merge.shape != base.shape:
        n = min(merge.shape[0], base.shape[0]), min(merge.shape[1], base.shape[1])
        print(f"  rasters differ; cropping both to {n} "
              "(coverage rescale makes an exact match impossible)")
        merge = merge[:n[0], :n[1]]
        base = base[:n[0], :n[1]]

    gm, gb = grid(merge), grid(base)
    print("\nACUTANCE per region (columns LEFT to RIGHT)")
    print("  merge:")
    for r in range(ROWS):
        print("   " + "".join(f"{v:9.4f}" for v in gm[r]))
    print("  best-frame baseline:")
    for r in range(ROWS):
        print("   " + "".join(f"{v:9.4f}" for v in gb[r]))
    print("  ratio merge / baseline:")
    for r in range(ROWS):
        print("   " + "".join(f"{v:9.3f}" for v in (gm[r] / np.maximum(gb[r], 1e-12))))

    print("\ncolumn medians, LEFT to RIGHT")
    mm, mb = np.median(gm, axis=0), np.median(gb, axis=0)
    print("  merge          : " + "".join(f"{v:9.4f}" for v in mm))
    print("  baseline       : " + "".join(f"{v:9.4f}" for v in mb))
    print("  ratio          : " + "".join(f"{v:9.3f}" for v in mm / np.maximum(mb, 1e-12)))
    print(f"\n  baseline left/right acutance ratio : {mb[0] / max(mb[-1], 1e-12):.3f}")
    print(f"  merge    left/right acutance ratio : {mm[0] / max(mm[-1], 1e-12):.3f}")
    lo = float((gm / np.maximum(gb, 1e-12)).min())
    print(f"  worst region ratio merge/baseline  : {lo:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
