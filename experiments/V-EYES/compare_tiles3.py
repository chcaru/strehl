"""Put the third instrument's verdict in front of an eye before believing it.

This is the step that killed instrument v2. That one reported the master at
0.108 of the per-site best frame with five arms passing; dumping the actual
pixels showed the "winning" frame was a featureless flat grey and the reference
was inverted. No number from this family gets reported again without this.

Dumps 400 px crops -- the largest size the image viewer shows without
resampling, so what is on screen is the real pixels -- for the master and for
the frame that won that site, at chosen percentiles of the master/best ratio.
Both arms get an identical display encode, stated in the output, because a
linear TIFF looks dark and any per-arm autoscaling would fake a difference.

Usage:
  python compare_tiles3.py <master.tiff> <framesdir> <x> <y> <size> <outdir> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict3 import (  # noqa: E402
    luma_linear, detail, contrast, shift_of, warp, build_envelope,
)

CROP = 400


def encode(a, lo, hi):
    v = np.clip((a - lo) / (hi - lo), 0, 1) ** (1 / 2.2)
    return (v * 255).astype(np.uint8)


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    outdir = pathlib.Path(sys.argv[6])
    block = int(sys.argv[7]) if len(sys.argv) > 7 else 64
    outdir.mkdir(parents=True, exist_ok=True)

    master = luma_linear(tifffile.imread(mpath)[y : y + size, x : x + size])
    files = sorted(fdir.glob("frame-*.tiff"))
    tiles, names = [], []
    for f in files:
        t = luma_linear(tifffile.imread(str(f))[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))
        names.append(f.stem.replace("frame-", ""))

    cm = contrast(master, block)
    cfloor = float(np.percentile(cm, 65))
    env, win, valid = build_envelope(tiles, block, cfloor)
    live = (cm > cfloor) & valid
    md, _ = detail(master, block)
    ratio = md / np.maximum(env, 1e-12)

    lo, hi = float(np.percentile(master, 1)), float(np.percentile(master, 99))
    print(f"display encode: linear {lo:.0f}..{hi:.0f} -> gamma 2.2, "
          f"identical for both arms, block {block}")
    print(f"{'pick':<12}{'ratio':<12}{'block':<13}{'master px':>18}  winner")
    print("-" * 74)

    idx = np.argwhere(live)
    order = idx[np.argsort(ratio[live])]
    picks = {
        "worst": order[0],
        "p25": order[len(order) // 4],
        "median": order[len(order) // 2],
        "best": order[-1],
    }
    for label, (by, bx) in picks.items():
        w = win[by, bx]
        cy = by * block + block // 2
        cx = bx * block + block // 2
        y0 = int(np.clip(cy - CROP // 2, 0, size - CROP))
        x0 = int(np.clip(cx - CROP // 2, 0, size - CROP))
        sl = (slice(y0, y0 + CROP), slice(x0, x0 + CROP))
        cv2.imwrite(str(outdir / f"{label}-MASTER.png"), encode(master[sl], lo, hi))
        cv2.imwrite(str(outdir / f"{label}-FRAME-{names[w]}.png"),
                    encode(tiles[w][sl], lo, hi))
        print(f"{label:<12}{ratio[by, bx]:<12.4f}({bx:>3},{by:>3})   "
              f"({x + cx:>5},{y + cy:>5})  {names[w]}")


if __name__ == "__main__":
    main()
