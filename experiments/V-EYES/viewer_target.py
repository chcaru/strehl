"""Commission the viewer before trusting anything seen through it.

This whole task exists because a verdict of "horrible, unusable" was returned on
a gallery that had been downscaled 5x before it was looked at. The resampler,
not the stacker, produced the mush. If the tool I use to LOOK at crops also
resamples, I will reproduce that error exactly and report softness that is not
in the file.

So: a target with features of known size in file pixels. If a 1 px checkerboard
survives to my eye, the path from file to eye is 1:1 and a softness verdict on a
1000 x 1000 crop is admissible. If it does not, every softness verdict I have
formed at that size is inadmissible and I must view smaller tiles.

Patches, all at full amplitude black/white so nothing is lost to contrast:
  - checkerboards at 1, 2, 3, 4, 8 px cell
  - horizontal and vertical line gratings at 1, 2, 3 px period
  - a slanted edge, which shows resampling ripple if any is present

Written at several sizes so the size at which the path stops being 1:1 can be
bracketed rather than guessed.

Usage: python viewer_target.py <outdir>
"""

import sys
import pathlib
import numpy as np
from PIL import Image


def checker(n, cell):
    yy, xx = np.mgrid[0:n, 0:n]
    return (((yy // cell) + (xx // cell)) % 2 * 255).astype(np.uint8)


def grating(n, period, vertical):
    yy, xx = np.mgrid[0:n, 0:n]
    v = xx if vertical else yy
    return (((v // period) % 2) * 255).astype(np.uint8)


def slant(n, slope=0.1):
    yy, xx = np.mgrid[0:n, 0:n]
    return np.where(xx > n * 0.5 + yy * slope, 255, 0).astype(np.uint8)


def build(size):
    img = np.full((size, size), 128, np.uint8)
    tile = size // 4
    pad = tile // 10
    specs = [
        ("chk1", lambda n: checker(n, 1)),
        ("chk2", lambda n: checker(n, 2)),
        ("chk3", lambda n: checker(n, 3)),
        ("chk4", lambda n: checker(n, 4)),
        ("chk8", lambda n: checker(n, 8)),
        ("vg1", lambda n: grating(n, 1, True)),
        ("vg2", lambda n: grating(n, 2, True)),
        ("hg1", lambda n: grating(n, 1, False)),
        ("hg2", lambda n: grating(n, 2, False)),
        ("hg3", lambda n: grating(n, 3, False)),
        ("vg3", lambda n: grating(n, 3, True)),
        ("slant", slant),
    ]
    inner = tile - 2 * pad
    for i, (_, fn) in enumerate(specs):
        r, c = divmod(i, 4)
        y0 = r * tile + pad
        x0 = c * tile + pad
        img[y0 : y0 + inner, x0 : x0 + inner] = fn(inner)
    return img


def main():
    out = pathlib.Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    print("layout, row-major, 4 across:")
    print("  chk1 chk2 chk3 chk4 / chk8 vg1 vg2 hg1 / hg2 hg3 vg3 slant")
    for size in (1000, 600, 400, 256):
        p = out / f"VIEWER-TARGET-{size}.png"
        Image.fromarray(build(size)).save(p)
        print(f"wrote {p}  ({size}x{size}, patch inner {size // 4 - 2 * (size // 40)} px)")


if __name__ == "__main__":
    main()
