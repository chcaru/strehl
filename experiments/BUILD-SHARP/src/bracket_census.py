"""RETRACTED -- DO NOT USE. Superseded by bracket_curve.py and merge_vs_best.py.

Kept runnable rather than deleted, on this project's own principle that an
instrument which is removed can no longer be shown to have failed. Two defects,
both recorded in BUILD-SHARP.md s37.2:

  1. The focus statistic `mean|grad I| / mean I` is invariant to a global gain
     in its SIGNAL term but not in its NOISE term. This bracket carries an 18.5%
     exposure ramp, over which photon noise alone moves the statistic by ~8.8%,
     which is the same size as the effect being measured. It returned argmax
     frame 0 for 20 of 24 regions.
  2. The verdict logic below is ONE-SIDED: it tests only for a pileup at the
     LAST frame, so a sweep that ran out at the NEAR end is reported as "every
     region has an interior optimum" -- a discriminator that can only detect one
     of the two ways its subject can fail.

Original docstring follows.

Is `flowers-cpl` an incomplete bracket, or is the merge failing?

ORCH's reading is that the subject extends deeper than the capture covered, so
no frame holds the right side sharp and no merge can invent it. That is a claim
about the INPUT, so it must be settled on the input, independently of strehl:
this reads the RAW frames directly with rawpy and never consults the merge to
decide the question.

Two statistics per region, and the second is the one that actually decides it.

1. BEST-FRAME SHARPNESS. max over frames of a contrast-normalised gradient,
   `mean|grad I| / mean I`, which is invariant to a global gain so exposure
   drift between frames cannot masquerade as focus. If this falls off toward
   the right, no captured frame holds that region sharp.

2. THE ARGMAX FRAME INDEX, which is the real discriminator. In a bracket that
   COVERS the subject, the best frame index moves smoothly through the interior
   of the stack as the focal plane sweeps. In a bracket that RAN OUT, the
   regions beyond the last focal plane have no interior optimum, so their
   argmax piles up against the final frame -- the sweep was still approaching
   them when it stopped. An index pinned at the last frame is evidence of a
   truncated sweep in a way that a sharpness value alone is not.

Everything is measured in LINEAR light: `gamma=(1,1)`, `no_auto_bright=True`.
A gradient magnitude read through an sRGB curve is not a gradient magnitude,
and this project has already published one comparison that was wrong for that
reason.

CAVEAT, stated rather than buried: this render's banner reports the field of
view scaled to 0.9367 to make every frame cover every pixel, i.e. 6.3% of focus
breathing across the stack. Regions are therefore kept large (about 580 px) so
that a feature cannot leave its own region as magnification changes.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rawpy

COLS, ROWS = 6, 4


def region_sharpness(g: np.ndarray) -> np.ndarray:
    """Contrast-normalised mean gradient magnitude per region."""
    h, w = g.shape
    out = np.zeros((ROWS, COLS))
    for r in range(ROWS):
        for c in range(COLS):
            y0, y1 = r * h // ROWS, (r + 1) * h // ROWS
            x0, x1 = c * w // COLS, (c + 1) * w // COLS
            t = g[y0:y1, x0:x1]
            gy, gx = np.gradient(t)
            m = t.mean()
            out[r, c] = np.hypot(gy, gx).mean() / m if m > 0 else 0.0
    return out


def main() -> int:
    src = Path(sys.argv[1])
    frames = sorted(src.glob("*.ARW"))
    if not frames:
        raise SystemExit(f"no ARW under {src}")
    print(f"{len(frames)} frames from {src}")

    best = None
    arg = None
    for i, f in enumerate(frames):
        with rawpy.imread(str(f)) as raw:
            rgb = raw.postprocess(
                half_size=True, gamma=(1, 1), no_auto_bright=True,
                output_bps=16, use_camera_wb=True,
            )
        s = region_sharpness(rgb[:, :, 1].astype(np.float64))
        if best is None:
            best, arg = s, np.zeros_like(s, dtype=int)
        else:
            hit = s > best
            arg[hit] = i
            best = np.maximum(best, s)
        if (i + 1) % 25 == 0 or i + 1 == len(frames):
            print(f"  ...{i + 1}/{len(frames)}")

    n = len(frames)
    print(f"\nBEST-FRAME SHARPNESS per region (contrast-normalised, linear)")
    print("  columns run LEFT to RIGHT across the frame")
    for r in range(ROWS):
        print("   " + "".join(f"{v:10.5f}" for v in best[r]))

    print(f"\nARGMAX FRAME INDEX per region (of {n} frames, last index {n - 1})")
    for r in range(ROWS):
        print("   " + "".join(f"{v:10d}" for v in arg[r]))

    print("\ncolumn medians, left to right:")
    bm = np.median(best, axis=0)
    am = np.median(arg, axis=0)
    print("  best sharpness : " + "".join(f"{v:10.5f}" for v in bm))
    print("  argmax index   : " + "".join(f"{v:10.1f}" for v in am))
    print(f"  sharpness left/right ratio : {bm[0] / max(bm[-1], 1e-12):.3f}")

    pinned = int((arg >= n - 3).sum())
    print(f"\n  regions whose best frame is within 3 of the LAST frame: "
          f"{pinned} of {ROWS * COLS}")
    if pinned:
        where = [(r, c) for r in range(ROWS) for c in range(COLS) if arg[r, c] >= n - 3]
        print(f"    at (row, col): {where}")
        print("    -> the sweep was still approaching these when it stopped:"
              " INCOMPLETE BRACKET")
    else:
        print("    -> every region has an INTERIOR optimum: the bracket covered"
              " the subject, and softness there is not a coverage failure")
    return 0


if __name__ == "__main__":
    sys.exit(main())
