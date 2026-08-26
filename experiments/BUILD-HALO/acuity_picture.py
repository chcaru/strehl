"""100% crops of the acuity arms, side by side, at ONE shared gain.

`+6.56% gradient RMS` is a number. The owner prints pictures, and this build has
been wrong three times this session about what a favourable number looks like on
the frame -- twice in the direction of "the metric moved and the image is worse".
So the arms get looked at before the result is reported.

The crop is chosen as the SHARPEST tile of the OFF arm, not a hand-picked one:
that is the tile where the shipped behaviour is already at its best, so it is the
hardest place for a sharpening change to show a win, and it is the tile
BUILD-RENDER's isolation image used. Choosing it from one arm keeps the choice
from chasing the effect.

Both arms are developed at the same gain, taken from the OFF arm, so a level
difference cannot read as a contrast difference.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import fullframe as ff

OUT = Path(r"C:\dev\strehl-out\ACUITY")
PIC = OUT / "pics"
CROP = 600
SUBJECTS = ["couch-fibers-cpl", "bee-2-cpl"]


def grad_rms(a: np.ndarray) -> float:
    dx = np.diff(a, axis=1)
    dy = np.diff(a, axis=0)
    n0, n1 = min(dx.shape[0], dy.shape[0]), min(dx.shape[1], dy.shape[1])
    return float(np.sqrt((dx[:n0, :n1] ** 2 + dy[:n0, :n1] ** 2).mean()))


def sharpest_tile(g: np.ndarray, size: int) -> tuple[int, int]:
    h, w = g.shape
    best, by, bx = -1.0, 0, 0
    for y in range(0, h - size, size):
        for x in range(0, w - size, size):
            r = grad_rms(g[y : y + size, x : x + size])
            if r > best:
                best, by, bx = r, y, x
    return by, bx


def main() -> int:
    PIC.mkdir(parents=True, exist_ok=True)
    for s in SUBJECTS:
        pa, pb = OUT / f"{s}.acu-off.tif", OUT / f"{s}.acu-on.tif"
        if not (pa.exists() and pb.exists()):
            print(f"{s}: pending")
            continue
        a, b = ff.read16(str(pa)), ff.read16(str(pb))
        gain = 0.45 * 65535.0 / max(float(np.median(a[..., 1])), 1.0)
        y, x = sharpest_tile(a[..., 1].astype(np.float64), CROP)
        ca, cb = a[y : y + CROP, x : x + CROP], b[y : y + CROP, x : x + CROP]
        print(f"{s}: sharpest tile of OFF arm at ({x},{y}), gain {gain:.4f}")
        print(f"    tile gradient RMS  off {grad_rms(ca[..., 1].astype(np.float64)):8.1f}"
              f"   on {grad_rms(cb[..., 1].astype(np.float64)):8.1f}")
        pair = np.concatenate([ca, np.zeros((CROP, 8, 3), a.dtype), cb], axis=1)
        ff.write_png(str(PIC / f"{s}-100pct-off-vs-on.png"), ff.develop(pair, gain))
        ff.write_png(str(PIC / f"{s}-off-full.png"),
                     ff.develop(ff.box_downsample(a, 1400), gain))
        ff.write_png(str(PIC / f"{s}-on-full.png"),
                     ff.develop(ff.box_downsample(b, 1400), gain))
    print(f"\npictures in {PIC}  (left = acuity OFF / shipped, right = acuity ON / restored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
