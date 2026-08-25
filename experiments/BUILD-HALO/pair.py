"""Native-resolution side-by-side pairs, for judging what the full frame hides.

The full frame says whether the halo is gone at viewing scale, which is the
bar. It cannot say whether the fix bought that by injecting noise or by
inventing structure, because at 1400 px both are below a pixel. This renders
the same crop from two arms at 1:1 with a shared stretch, so the only
difference on screen is the merge.

Shared stretch is the whole point and is not negotiable: auto-levelling each
arm separately would silently rescale one of them and turn any brightness
difference -- which is exactly what a halo IS -- into a no-op.
"""

from __future__ import annotations

import argparse

import numpy as np

from fullframe import develop, read16, write_png


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="TAG=PATH for the left arm")
    ap.add_argument("--b", required=True, help="TAG=PATH for the right arm")
    ap.add_argument("--at", required=True, help="X,Y,W,H in output pixels")
    ap.add_argument("--gain", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=1, help="integer nearest-neighbour zoom")
    a = ap.parse_args()

    ta, pa = a.a.split("=", 1)
    tb, pb = a.b.split("=", 1)
    x, y, w, h = (int(v) for v in a.at.split(","))

    ia = read16(pa)[y : y + h, x : x + w]
    ib = read16(pb)[y : y + h, x : x + w]
    assert ia.shape == ib.shape, (ia.shape, ib.shape)

    da, db = develop(ia, a.gain), develop(ib, a.gain)
    if a.scale > 1:
        da = np.repeat(np.repeat(da, a.scale, 0), a.scale, 1)
        db = np.repeat(np.repeat(db, a.scale, 0), a.scale, 1)

    gap = np.full((da.shape[0], 8, 3), 255, np.uint8)
    write_png(a.out, np.concatenate([da, gap, db], axis=1))
    print(f"wrote {a.out}  [{ta} | {tb}]  crop {x},{y} {w}x{h} x{a.scale}")


if __name__ == "__main__":
    main()
