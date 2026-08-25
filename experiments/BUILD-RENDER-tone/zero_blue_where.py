"""Where does the residual zero-blue live: in the dark, or in the picture?

After the chromaticity fix, `flower-inner-edge-cpl` still carries ~11.8% zero-blue
pixels -- the genuine pre-tone condition, not the tone defect. Whether that is a
print defect depends entirely on WHERE those pixels are. Blue pinned at zero in a
near-black shadow is invisible; blue pinned at zero in a lit midtone is a destroyed
channel in the picture. This asks which.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile

AB = Path(r"C:\dev\strehl-out\vtone-ab")


def read16(p: Path) -> np.ndarray:
    a = tifffile.imread(str(p))
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a


def report(subject: str, arm: str) -> None:
    a = read16(AB / f"{subject}-{arm}.tif")
    f = a.astype(np.float32) / 65535.0
    lum = 0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2]
    z = a[..., 2] == 0
    n = z.size
    print(f"\n{subject} [{arm}]  zero-blue {100.0 * z.sum() / n:.4f}%  ({z.sum():,} px)")
    if not z.any():
        return
    zl = lum[z]
    for q in (50, 90, 99, 100):
        print(f"    zero-blue luminance p{q:<3} = {np.percentile(zl, q):.4f}")
    # sRGB display value, which is what the eye actually sees.
    for thr, name in ((0.02, "2% (deep shadow)"), (0.05, "5%"), (0.10, "10%"), (0.20, "20% (clear midtone)")):
        print(f"    zero-blue above {name:<20} : {100.0 * (zl > thr).sum() / n:.4f}% of frame")
    # How far below zero was it? Approximate from the surviving channels: a pixel
    # whose R and G are large but B is 0 is a saturated hue; one where all three
    # are tiny is just dark.
    rg = f[..., :2][z]
    print(f"    of those, median R={np.median(rg[:, 0]):.4f} G={np.median(rg[:, 1]):.4f}")


if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "flower-inner-edge-cpl"
    for arm in ("before", "after"):
        if (AB / f"{subject}-{arm}.tif").exists():
            report(subject, arm)
