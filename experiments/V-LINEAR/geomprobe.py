"""Geometry probe: how do strehl's linear develop and Lightroom's TIFF of the
SAME RAW frame relate to each other?

7032x4688 (strehl --linear-srgb --demosaic) vs 7008x4672 (Lightroom export).
The difference is 24 px in width and 16 px in height.  That is CONSISTENT with
a pure crop of 12/8 px per side, and it is also consistent with a 1.0034 scale
difference, and the two are not the same thing: a scale difference means every
ROI needs resampling before its spectrum can be compared, and a crop means none
of them do.

V-HEADTOHEAD2 sec.7 says geometry must be re-derived and not trusted -- the
prior lane's fork arm disagreed by 5.3 px rms and that destroyed 41 of 64
regions.  So this measures it instead of assuming it: take ROIs at four widely
separated positions and find the integer shift at each.  A pure crop gives the
SAME shift everywhere.  A scale difference makes the shift drift linearly with
position, and over a 7000 px baseline a 0.34% scale would show up as a ~24 px
spread, which is impossible to miss.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "V-HEADTOHEAD2"))
import h2  # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
LRD = r"D:\edited\macro\test2"


def luma_crop(path, y0, x0, t):
    """One BT.709-luma crop, whatever the file's dtype.  Lightroom's export is
    32-bit float and strehl's is u16; both are gamma-1.0 encoded (measured by
    icc_dump.py), so no transfer function is applied to either."""
    a = tifffile.memmap(path, mode="r")
    blk = np.asarray(a[y0:y0 + t, x0:x0 + t, :3], np.float64)
    return h2.luma709(blk)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 32
    lin = os.path.join(LIN, f"DSC{n:05d}.tif")
    lr = os.path.join(LRD, f"20260507-DSC{n:05d}.tif")
    for p in (lin, lr):
        with tifffile.TiffFile(p) as tf:
            s = tf.series[0]
            print(f"{os.path.basename(p):28s} {s.shape} {s.dtype}")

    t = 512
    # four widely separated positions, quoted in LIGHTROOM coordinates
    pos = [(900, 1200), (900, 5400), (3600, 1200), (3600, 5400), (2300, 3300)]
    print(f"\n{'lr_y':>6} {'lr_x':>6} {'dy':>4} {'dx':>4} {'peak':>7}")
    got = []
    for (y, x) in pos:
        # search a generous window around the centred-crop hypothesis (+8,+12)
        ref = luma_crop(lr, y, x, t)
        mov = luma_crop(lin, y + 8, x + 12, t)
        dy, dx, pk = h2.integer_shift(ref, mov, maxshift=24)
        got.append((dy, dx))
        print(f"{y:6d} {x:6d} {dy:4d} {dx:4d} {pk:7.4f}")

    g = np.array(got)
    spread = g.max(0) - g.min(0)
    print(f"\nshift spread over the frame: dy {spread[0]} px, dx {spread[1]} px")
    print("a 0.34% scale difference would give a spread of about "
          f"{0.0034 * 4200:.0f} px in dy and {0.0034 * 4200:.0f} px in dx")
    if spread.max() <= 2:
        print("VERDICT: pure translation -- LIN[y+8+dy, x+12+dx] == LR[y, x], "
              "no resampling needed")
    else:
        print("VERDICT: NOT a pure translation -- a scale fit is required "
              "before any spectrum may be compared")


if __name__ == "__main__":
    main()
