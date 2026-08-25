"""Confirmation of cell C on the strongest-coupling subject.

bee-3-cpl cell C gave EXACTLY 0.0% of green and blue pixels changed in linear
camera-native binned output. wrapped-text-1 had the strongest sRGB coupling in
section 14 (98.7% green, 86.7% blue), so it is the hardest case for the claim
that CA is a pure red-plane operation in camera space.

An exact zero is a structural result, not a statistical one -- but it is
exactly the kind of result a single subject can fake if that subject happens
to be degenerate. One more subject is cheap insurance.
"""

from pathlib import Path

import numpy as np
import tifffile

D = Path(r"C:\dev\strehl-out\M110-sheet")


def cell_c(subject: str) -> None:
    a = tifffile.imread(str(D / subject / "lin-default.tif")).astype(np.int64)
    b = tifffile.imread(str(D / subject / "lin-ca.tif")).astype(np.int64)
    if a.shape != b.shape:
        raise SystemExit(f"{subject}: shape mismatch")
    d = b - a
    print(f"{subject}  shape {a.shape}")
    for i, nm in enumerate("RGB"):
        ch = d[:, :, i]
        n = int(np.count_nonzero(ch))
        print(f"  {nm}: {100.0*n/ch.size:7.4f}% of pixels changed   "
              f"max|delta| = {int(np.abs(ch).max()):>6}   n={n:,}")
    green_blue_moved = np.count_nonzero(d[:, :, 1]) + np.count_nonzero(d[:, :, 2])
    red_moved = np.count_nonzero(d[:, :, 0])
    print(f"  red moved on {100.0*red_moved/d[:,:,0].size:.1f}% of pixels "
          f"(CA is live), green+blue moved on {green_blue_moved} pixels total")
    if green_blue_moved == 0 and red_moved > 0:
        print("  => PURE RED-PLANE OPERATION, exactly. Confirms bee-3-cpl.")
    elif red_moved == 0:
        print("  => CA INERT on this subject -- the test is void, investigate.")
    else:
        print("  => NOT pure: green/blue moved. Report the exact count.")


if __name__ == "__main__":
    print(__doc__)
    for s in ("bee-3-cpl", "wrapped-text-1"):
        cell_c(s)
        print()
