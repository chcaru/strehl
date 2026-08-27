"""Locate a delivered 1:1 crop inside its master, so a visual finding gets coordinates.

The delivery ships crops but not the coordinates they were cut from, and a
defect report without coordinates cannot be handed to an implementer. The crops
are stated to be cut with no resampling, so the match should be exact up to
JPEG quantisation -- which is worth verifying rather than assuming, because if
a crop does NOT match its master at some integer offset then the crop pipeline
is resampling and the README's central claim is wrong.

Matched on a 4x-downsampled luma via normalised cross-correlation, then refined
by exhaustive search in the +/- 8 px neighbourhood at full resolution. The
reported residual is the mean absolute difference in 8-bit DN at the winning
offset: a few DN is JPEG noise, tens of DN means it is not the same pixels.

Usage: python locate_crops.py <cropdir> <masterdir> <suffix> [subject-filter]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2
from PIL import Image


def luma8(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(
        np.float32
    )


def main():
    cropdir = pathlib.Path(sys.argv[1])
    masterdir = pathlib.Path(sys.argv[2])
    suffix = sys.argv[3]
    filt = sys.argv[4] if len(sys.argv) > 4 else ""

    crops = sorted(p for p in cropdir.glob("*.jpg") if filt in p.name)
    by_subject = {}
    for c in crops:
        by_subject.setdefault(c.stem.rsplit("--", 1)[0], []).append(c)

    print(f"{'crop':<44} {'x':>6} {'y':>6} {'residDN':>8} {'peak':>7}")
    print("-" * 76)
    for subject, cs in sorted(by_subject.items()):
        mpath = masterdir / f"{subject}{suffix}"
        if not mpath.exists():
            print(f"{subject:<44} MASTER MISSING")
            continue
        m = tifffile.imread(str(mpath))
        m8 = (m / 257.0).round().clip(0, 255).astype(np.uint8)
        ml = luma8(m8)
        ml4 = cv2.resize(ml, (ml.shape[1] // 4, ml.shape[0] // 4), cv2.INTER_AREA)
        for c in sorted(cs):
            cim = np.asarray(Image.open(c).convert("RGB"))
            cl = luma8(cim)
            cl4 = cv2.resize(cl, (cl.shape[1] // 4, cl.shape[0] // 4), cv2.INTER_AREA)
            res = cv2.matchTemplate(ml4, cl4, cv2.TM_CCOEFF_NORMED)
            _, peak, _, loc = cv2.minMaxLoc(res)
            bx, by = loc[0] * 4, loc[1] * 4
            best = (1e9, bx, by)
            h, w = cl.shape
            for dy in range(-8, 9):
                for dx in range(-8, 9):
                    yy, xx = by + dy, bx + dx
                    if yy < 0 or xx < 0 or yy + h > ml.shape[0] or xx + w > ml.shape[1]:
                        continue
                    d = float(np.abs(ml[yy : yy + h, xx : xx + w] - cl).mean())
                    if d < best[0]:
                        best = (d, xx, yy)
            print(f"{c.stem:<44} {best[1]:>6} {best[2]:>6} {best[0]:>8.2f} {peak:>7.4f}")


if __name__ == "__main__":
    main()
