"""Fold the warped frame basis once into cached hulls, whole-image and per-band.

Folding is the expensive half: 205 frames x 47 MB is ~10 GB of reads, and the
per-band pass decomposes every frame into 8 bands. Six merge arms share one
basis, so the fold is done once and cached as .npy and every arm is then a cheap
test against it. This is the same fold-once/test-many discipline used earlier in
pyrhull.py.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import bands_of, load16


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--levels", type=int, default=7)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--bands", action="store_true")
    a = ap.parse_args()

    fdir = Path(a.frames)
    cache = Path(a.cache)
    cache.mkdir(parents=True, exist_ok=True)

    present = sorted(fdir.glob("f*.tiff"))
    print(f"  frames requested : {a.n}")
    print(f"  frames present   : {len(present)}")
    print(f"  frames MISSING   : {a.n - len(present)}")
    missing = [k for k in range(a.n) if not (fdir / f"f{k:04d}.tiff").exists()]
    assert not missing, f"refusing to fold: missing frames {missing[:12]}"

    lo = hi = None
    blo: list = [None] * (a.levels + 1)
    bhi: list = [None] * (a.levels + 1)
    for k in range(a.n):
        f = load16(fdir / f"f{k:04d}.tiff")
        if lo is None:
            lo, hi = f.copy(), f.copy()
        else:
            np.minimum(lo, f, out=lo)
            np.maximum(hi, f, out=hi)
        if a.bands:
            for b, v in enumerate(bands_of(f, a.levels)):
                if blo[b] is None:
                    blo[b], bhi[b] = v.copy(), v.copy()
                else:
                    np.minimum(blo[b], v, out=blo[b])
                    np.maximum(bhi[b], v, out=bhi[b])
        if (k + 1) % 25 == 0:
            print(f"    folded {k + 1}/{a.n}", flush=True)

    np.save(cache / "lo.npy", lo)
    np.save(cache / "hi.npy", hi)
    print(f"  wrote {cache / 'lo.npy'}  {lo.shape} {lo.dtype}")
    if a.bands:
        for b in range(a.levels + 1):
            np.save(cache / f"blo{b}.npy", blo[b].astype(np.float32))
            np.save(cache / f"bhi{b}.npy", bhi[b].astype(np.float32))
        print(f"  wrote {a.levels + 1} band hulls")

    # A fold that silently produced a degenerate hull would make every arm look
    # clean, so state the hull's own scale before anything is tested against it.
    span = hi.astype(np.float32) - lo.astype(np.float32)
    print(f"  hull span DN     : mean {span.mean():.1f}  median {np.median(span):.1f} "
          f"min {span.min():.0f}  max {span.max():.0f}")
    print(f"  degenerate (span==0) samples: {int(np.count_nonzero(span == 0))} "
          f"/ {span.size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
