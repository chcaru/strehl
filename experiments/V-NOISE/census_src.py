"""ROI CENSUS FOR THE NOISE LANE -- computed on the SOURCE frames, never on an
output.

PREREGISTRATION.md sec.2 fixes this rule and the reason for it: choosing flat
regions by looking at a stacker's output is selecting on the thing being
measured.  So the flat/detail split is derived from the 63 source linear TIFFs
that every arm consumed, and the resulting tile list is byte-identical for
every arm.

Detail energy per tile = MAX over frames of the high-pass variance.  Maximum,
not mean, because a tile should count as detailed if ANY frame could have
resolved detail there -- that is the conservative direction for a lane that
wants genuinely featureless regions.

KNOWN AND ACCEPTED IMPRECISION.  The source frames are unaligned, and focus
breathing spans scale 1.000-1.055 across the sweep, so a tile's scene content
drifts by up to ~150 px at the field edge between the first and last frame.
That smears the detail map.  It smears it in the safe direction: content from a
neighbouring detailed region can wander INTO a tile and mark it detailed, but
detail cannot be hidden from a max-over-frames statistic.  So the FLAT set is
if anything over-conservative, which is what this lane wants.

INVOCATION (rule 47).  Reads C:\\dev\\strehl-out\\V-LINEAR\\lintiff\\*.tif
(63 frames, read-only).  Writes the cached census to
C:\\dev\\strehl-out\\V-NOISE\\census.npz.  Nothing else is written.

    python census_src.py [--force]
"""
import os
import sys
import time

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

SRC = r"C:\dev\strehl-out\V-LINEAR\lintiff"
OUT = r"C:\dev\strehl-out\V-NOISE"
CACHE = os.path.join(OUT, "census.npz")

T = 256                  # tile size, strehl pixel grid
STRIDE = 256             # non-overlapping
MARGIN = 128             # breathing shrinks the usable field
HP = 9                   # high-pass kernel, matches the noise statistic
FLAT_FRAC = 0.25         # PRE-REGISTERED, sec.2 item 3.  Not tuned.


def tile_grid(h, w):
    ys = list(range(MARGIN, h - MARGIN - T + 1, STRIDE))
    xs = list(range(MARGIN, w - MARGIN - T + 1, STRIDE))
    return [(y, x) for y in ys for x in xs]


def frame_energy(path, cells):
    """Per-tile high-pass variance of the green channel of one source frame."""
    a = tifffile.memmap(path, mode="r")
    g = np.asarray(a[:, :, 1], np.float32)
    del a
    hp = g - uniform_filter(g, HP)
    out = np.empty(len(cells), np.float64)
    for i, (y, x) in enumerate(cells):
        out[i] = float(hp[y:y + T, x:x + T].var())
    return out, g.shape


def main():
    force = "--force" in sys.argv
    if os.path.exists(CACHE) and not force:
        z = np.load(CACHE)
        print(f"cached census: {len(z['flat'])} FLAT of {len(z['cells'])} "
              f"tiles from {int(z['nframes'])} source frames")
        return 0

    os.makedirs(OUT, exist_ok=True)
    frames = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".tif"))
    if not frames:
        print(f"no source frames under {SRC}")
        return 2

    a = tifffile.memmap(os.path.join(SRC, frames[0]), mode="r")
    h, w = a.shape[0], a.shape[1]
    del a
    cells = tile_grid(h, w)
    print(f"source {w}x{h}, {len(frames)} frames, {len(cells)} candidate "
          f"tiles ({T}px, margin {MARGIN})")

    emax = np.zeros(len(cells))
    t0 = time.time()
    for i, f in enumerate(frames):
        e, _ = frame_energy(os.path.join(SRC, f), cells)
        emax = np.maximum(emax, e)
        if (i + 1) % 10 == 0 or i + 1 == len(frames):
            print(f"  {i + 1}/{len(frames)} frames  "
                  f"{time.time() - t0:.0f}s", flush=True)

    order = np.argsort(emax)
    nflat = int(round(FLAT_FRAC * len(cells)))
    flat = order[:nflat]
    cells_a = np.array(cells)
    np.savez(CACHE, cells=cells_a, emax=emax, flat=flat,
             nframes=len(frames), T=T, margin=MARGIN, hp=HP)

    q = np.percentile(emax, [0, 25, 50, 75, 100])
    print(f"\nper-tile max-over-frames high-pass variance, percentiles:")
    print(f"  min {q[0]:.4g}  p25 {q[1]:.4g}  med {q[2]:.4g}  "
          f"p75 {q[3]:.4g}  max {q[4]:.4g}")
    print(f"FLAT = bottom {FLAT_FRAC:.0%} = {nflat} tiles, "
          f"energy <= {emax[flat].max():.4g}")
    print(f"  separation: median DETAIL energy / max FLAT energy = "
          f"{q[2] / emax[flat].max():.2f}x")
    print(f"written {CACHE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
