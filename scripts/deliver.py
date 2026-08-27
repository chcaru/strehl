"""Deliver the masters at a size a photographer can actually judge.

WHY THIS EXISTS
---------------
`finalpass.ps1` defaults `-PresentWidth 1400`. The masters are 7032x4688 (33 MP).
So the gallery a viewer naturally double-clicks has been 19.9% of the master's
width -- a 1.3 MP thumbnail of a 33 MP focus stack.

Every property this project exists to produce lives ABOVE that resolution.
Reconstruction gain is measured on 1:1 patches. The blur budget closes to 2.6%
at full scale. Halo absence was confirmed on 1:1 grids. A 5x box-down of all of
it lands in the resampling kernel and is simply not visible -- and worse, a 5x
downscale of a sharp image looks SOFTER than a 5x downscale of an oversharpened
one, so the thumbnail actively inverts the judgement it is being used to make.

WHAT THIS WRITES
----------------
  full/<subject>.jpg    the whole master, full resolution, quality 95,
                        sRGB ICC embedded, 300 DPI in the JFIF header.
  crops/<subject>--<n>.jpg
                        1:1 crops, NO resampling of any kind, taken at the
                        most-detailed locations in the frame.

FAITHFULNESS
------------
Masters are written --srgb and already carry the sRGB transfer curve, so this
applies NO tone curve, NO black point, NO saturation, NO percentile stretch.
The only operation is a 16->8 bit reduction with round-to-nearest, (x+128)>>8,
which avoids the systematic half-code downward bias that truncation gives.

Read with tifffile and asserted uint16: PIL.Image.open silently downconverts
16-bit RGB to 8 bits, and this project has been burned by that before precisely
because the result still looks correct.

CROP SELECTION IS MEASURED, NOT CHOSEN
--------------------------------------
Picking crop locations by eye would let the deliverable flatter itself. Instead
each candidate tile is scored by the same quantity the stacker is judged on --
high-frequency energy, as the mean |Laplacian| of the luma -- and the top tiles
are taken subject to a minimum separation so they do not all land on one
antenna. The scoring is on the MASTER, so it selects where detail EXISTS, which
is also where a stacking failure would be most visible. That cuts both ways on
purpose.
"""

import argparse
import glob
import os
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image, ImageCms

CROP = 1000          # px, 1:1
NCROPS = 3
JPEG_Q = 95
DPI = 300


def to8(a16):
    """16-bit -> 8-bit, round to nearest. No curve, no stretch."""
    assert a16.dtype == np.uint16, "expected uint16, got %s" % a16.dtype
    return ((a16.astype(np.uint32) + 128) >> 8).clip(0, 255).astype(np.uint8)


def srgb_icc():
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def detail_score(luma8, y, x, n):
    t = luma8[y:y + n, x:x + n].astype(np.float32)
    lap = (t[1:-1, 2:] + t[1:-1, :-2] + t[2:, 1:-1] + t[:-2, 1:-1]
           - 4.0 * t[1:-1, 1:-1])
    return float(np.abs(lap).mean())


def pick_crops(a8, n, k):
    """Top-k detail tiles with a minimum separation, scored on the master."""
    luma = (0.2126 * a8[..., 0] + 0.7152 * a8[..., 1] + 0.0722 * a8[..., 2])
    h, w = luma.shape
    step = n // 2
    cands = []
    for y in range(0, max(1, h - n), step):
        for x in range(0, max(1, w - n), step):
            cands.append((detail_score(luma, y, x, n), y, x))
    cands.sort(reverse=True)
    out = []
    for s, y, x in cands:
        if all(abs(y - py) >= n or abs(x - px) >= n for _, py, px in out):
            out.append((s, y, x))
        if len(out) == k:
            break
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--only", default=None)
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    dst = pathlib.Path(args.dst)
    (dst / "full").mkdir(parents=True, exist_ok=True)
    (dst / "crops").mkdir(parents=True, exist_ok=True)
    icc = srgb_icc()

    masters = sorted(glob.glob(str(src / "*.tif")) + glob.glob(str(src / "*.tiff")))
    if args.only:
        masters = [m for m in masters if args.only in os.path.basename(m)]
    if not masters:
        raise SystemExit("no masters under %s" % src)

    print("%-36s %10s %8s %s" % ("subject", "size", "fullMB", "crops"))
    print("-" * 78)
    for m in masters:
        stem = os.path.basename(m)
        for suf in (".tiff", ".tif"):
            if stem.endswith(suf):
                stem = stem[:-len(suf)]
        stem = stem.split("--")[0]

        a = tifffile.imread(m)
        assert a.ndim == 3 and a.shape[2] >= 3, "%s is not RGB" % m
        a8 = to8(a[..., :3])

        fp = dst / "full" / (stem + ".jpg")
        Image.fromarray(a8).save(str(fp), quality=JPEG_Q, subsampling=0,
                                 icc_profile=icc, dpi=(DPI, DPI),
                                 optimize=True)

        picks = pick_crops(a8, CROP, NCROPS)
        for i, (s, y, x) in enumerate(picks, 1):
            c = a8[y:y + CROP, x:x + CROP]
            cp = dst / "crops" / ("%s--%d.jpg" % (stem, i))
            Image.fromarray(c).save(str(cp), quality=JPEG_Q, subsampling=0,
                                    icc_profile=icc, dpi=(DPI, DPI))
        print("%-36s %5dx%-4d %8.1f %s"
              % (stem, a.shape[1], a.shape[0],
                 os.path.getsize(fp) / 1e6,
                 " ".join("(%d,%d)" % (y, x) for _, y, x in picks)))
        sys.stdout.flush()

    print("-" * 78)
    print("wrote %d full-resolution masters + %d 1:1 crops to %s"
          % (len(masters), len(masters) * NCROPS, dst))


if __name__ == "__main__":
    main()
