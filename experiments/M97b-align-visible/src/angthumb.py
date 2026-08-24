"""Thumbnail both angled-ruler arms so I can actually look at them.

Rule: never describe an image I have not opened. This writes 1/8-scale PNGs
plus a shared-coordinate difference map, so the first thing I see is where the
two arms differ rather than a number claiming they do.

Both arms are FOV-matched by construction (STREHL_ALIGN=zoom keeps the same
fit_to_cover scale and discards only the registration), so a fixed-coordinate
comparison is legitimate HERE and only here -- discipline 606 forbids it
between arms that differ in field of view, which ALIGN=0 does and zoom does
not.
"""

import sys

import numpy as np
import tifffile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

OUT = r"C:\dev\strehl-out\M97"
A = rf"{OUT}\angruler-ALIGNED.tif"
Z = rf"{OUT}\angruler-ZOOMNULL.tif"


def read(path):
    return tifffile.imread(path)


def luma(a):
    return a.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])


def block(a, k):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def png(a, path, lo=None, hi=None):
    lo = np.percentile(a, 0.5) if lo is None else lo
    hi = np.percentile(a, 99.5) if hi is None else hi
    v = np.clip((a - lo) / max(hi - lo, 1e-9), 0, 1)
    Image.fromarray((v * 255).astype(np.uint8)).save(path)


def main():
    ia, iz = read(A), read(Z)
    print(f"ALIGNED  {ia.shape} {ia.dtype} min={ia.min()} max={ia.max()}")
    print(f"ZOOMNULL {iz.shape} {iz.dtype} min={iz.min()} max={iz.max()}")
    assert ia.shape == iz.shape, "arms differ in shape; zoom null is not FOV-matched"

    la, lz = luma(ia), luma(iz)
    ba, bz = block(la, 8), block(lz, 8)
    png(ba, rf"{OUT}\angthumb-ALIGNED.png")
    png(bz, rf"{OUT}\angthumb-ZOOMNULL.png")

    d = np.abs(ba - bz)
    frac = float((np.abs(la - lz) > 0).mean())
    print(f"pixels differing at all: {frac * 100:.3f}%")
    print(f"|diff| thumb: mean={d.mean():.1f} p99={np.percentile(d, 99):.1f} max={d.max():.1f}")
    png(d, rf"{OUT}\angthumb-DIFF.png", lo=0.0, hi=float(np.percentile(d, 99.5)))

    # Where is the ruler? Report the dark-fraction profile along both axes so I
    # can tell the in-frame orientation of the engraved edge before writing an
    # instrument that assumes one.
    dark = ba < np.percentile(ba, 25)
    rows, cols = dark.mean(axis=1), dark.mean(axis=0)
    print(f"thumb {ba.shape}  dark-row peak at y={int(rows.argmax()) * 8} frac={rows.max():.3f}")
    print(f"                  dark-col peak at x={int(cols.argmax()) * 8} frac={cols.max():.3f}")
    print("row dark-fraction deciles:", np.round(rows[:: max(len(rows) // 10, 1)], 3))
    print("col dark-fraction deciles:", np.round(cols[:: max(len(cols) // 10, 1)], 3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
