"""Put the metric's verdict in front of an eye before believing it.

softness_verdict2.py reports the master at 0.108 of the per-site best frame --
a ninth of the detail density -- with all five commissioning arms passing. That
is a far larger deficit than the 35-55% the --srgb measurement suggested, and
large enough that it should be obvious at 1:1. If it is not obvious, the metric
is wrong however many arms it passes, because an instrument that disagrees with
a clear visual fact is reporting on something other than what it claims.

So: pick blocks at chosen percentiles of the master/envelope ratio, and write
the master and the frame that WON that block side by side, cut 1:1 at 400 px --
the size at which V-EYES established the viewer does not resample.

Both crops are display-encoded identically. The renders are --linear-srgb, so
they are dark and low-contrast in a viewer by construction; a common gamma and
a common scale factor are applied to BOTH so the comparison is of structure and
not of brightness. The scale is taken from the master's own percentiles and
reused for the frame, so any exposure difference between a merge and a single
frame shows up as a brightness difference rather than being normalised away
silently. This encoding is for LOOKING ONLY and is never measured on.

Usage:
  python compare_tiles.py <master.tiff> <framesdir> <x> <y> <size> <outdir> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2
from PIL import Image

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict2 import luma_linear, stat, contrast_map, shift_of, warp


def encode(a, lo, hi):
    """Common display encoding: linear -> normalised -> gamma 1/2.2 -> 8 bit."""
    x = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    return (np.power(x, 1 / 2.2) * 255).round().astype(np.uint8)


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    outdir = pathlib.Path(sys.argv[6])
    block = int(sys.argv[7]) if len(sys.argv) > 7 else 64
    outdir.mkdir(parents=True, exist_ok=True)

    m = tifffile.imread(mpath)
    master = luma_linear(m[y : y + size, x : x + size])
    frames = sorted(fdir.glob("frame-*.tiff"))

    tiles, names = [], []
    for f in frames:
        t = luma_linear(tifffile.imread(str(f))[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))
        names.append(f.stem)

    ms, _ = stat(master, block)
    S = np.stack([stat(t, block)[0] for t in tiles])
    envelope = S.max(axis=0)
    winner = S.argmax(axis=0)
    cmap = contrast_map(master, block)
    live = cmap > float(np.percentile(cmap, 65))

    ratio = ms / np.maximum(envelope, 1e-12)
    ys, xs = np.nonzero(live)
    vals = ratio[live]
    order = np.argsort(vals)

    lo = float(np.percentile(master, 2))
    hi = float(np.percentile(master, 99.5))
    print(f"display encode: linear {lo:.0f}..{hi:.0f} -> gamma 2.2, "
          f"identical for both arms")
    print(f"{'pick':<10} {'ratio':>7} {'block':>12} {'master px':>16} {'winner':<16}")
    print("-" * 74)

    half = 200
    for label, q in (("worst", 0.02), ("median", 0.50), ("best", 0.98)):
        k = order[int(q * (len(order) - 1))]
        by, bx = int(ys[k]), int(xs[k])
        r = float(ratio[by, bx])
        w = int(winner[by, bx])
        cy = by * block + block // 2
        cx = bx * block + block // 2
        y0 = int(np.clip(cy - half, 0, size - 2 * half))
        x0 = int(np.clip(cx - half, 0, size - 2 * half))
        mt = encode(master[y0 : y0 + 2 * half, x0 : x0 + 2 * half], lo, hi)
        ft = encode(tiles[w][y0 : y0 + 2 * half, x0 : x0 + 2 * half], lo, hi)
        Image.fromarray(mt).save(outdir / f"{label}-MASTER.png")
        Image.fromarray(ft).save(outdir / f"{label}-FRAME-{names[w]}.png")
        print(f"{label:<10} {r:>7.4f} ({bx:>3},{by:>3}) "
              f"{'(%d,%d)' % (x + x0, y + y0):>16} {names[w]:<16}")


if __name__ == "__main__":
    main()
