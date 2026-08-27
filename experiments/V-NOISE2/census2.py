"""Per-subject FLAT-tile census.  The RULE is imported, not re-implemented.

PREREGISTRATION.md sec.3 requires the same ROI rule M127 used: max-over-frames
high-pass variance, bottom quartile, computed on the SOURCE develops and never
on a stacker output.  This file therefore imports `tile_grid`, `frame_energy`
and every constant from V-NOISE/census_src.py rather than copying them.  If the
rule were restated here it could drift from the one that was pre-registered,
and a per-subject drift is exactly how a subject gets a friendlier tile set.

The ONLY thing that changes per subject is which directory is read and where
the cache is written.

INVOCATION (rule 47).  Reads C:\\dev\\strehl-out\\V-NOISE2\\<key>\\lintiff\\*.tif
(the develops built by run_subject.ps1).  Writes
C:\\dev\\strehl-out\\V-NOISE2\\<key>\\census.npz.  Nothing else.

    python census2.py <key> [--force]
"""
import os
import sys
import time

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from census_src import (tile_grid, frame_energy, T, MARGIN, HP,   # noqa: E402
                        FLAT_FRAC)

ROOT = r"C:\dev\strehl-out\V-NOISE2"


def build(key, force=False):
    src = os.path.join(ROOT, key, "lintiff")
    cache = os.path.join(ROOT, key, "census.npz")
    if os.path.exists(cache) and not force:
        z = np.load(cache)
        print(f"{key}: cached census, {len(z['flat'])} FLAT of "
              f"{len(z['cells'])} tiles from {int(z['nframes'])} frames")
        return cache
    frames = sorted(f for f in os.listdir(src) if f.lower().endswith(".tif"))
    if not frames:
        raise SystemExit(f"no develops under {src}")
    a = tifffile.memmap(os.path.join(src, frames[0]), mode="r")
    h, w = a.shape[0], a.shape[1]
    del a
    cells = tile_grid(h, w)
    print(f"{key}: source {w}x{h}, {len(frames)} frames, {len(cells)} "
          f"candidate tiles ({T}px, margin {MARGIN}, hp {HP})")

    emax = np.zeros(len(cells))
    t0 = time.time()
    for i, f in enumerate(frames):
        e, _ = frame_energy(os.path.join(src, f), cells)
        emax = np.maximum(emax, e)
        if (i + 1) % 25 == 0 or i + 1 == len(frames):
            print(f"  {i + 1}/{len(frames)}  {time.time() - t0:.0f}s",
                  flush=True)

    order = np.argsort(emax)
    nflat = int(round(FLAT_FRAC * len(cells)))
    flat = order[:nflat]
    np.savez(cache, cells=np.array(cells), emax=emax, flat=flat,
             nframes=len(frames), T=T, margin=MARGIN, hp=HP)
    q = np.percentile(emax, [0, 25, 50, 75, 100])
    print(f"  percentiles  min {q[0]:.4g}  p25 {q[1]:.4g}  med {q[2]:.4g}  "
          f"p75 {q[3]:.4g}  max {q[4]:.4g}")
    print(f"  FLAT = bottom {FLAT_FRAC:.0%} = {nflat} tiles, "
          f"energy <= {emax[flat].max():.4g}")
    print(f"  separation: median DETAIL / max FLAT = "
          f"{q[2] / emax[flat].max():.2f}x")
    print(f"  written {cache}")
    return cache


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    for key in args:
        build(key, force="--force" in sys.argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
