"""Does the lateral-CA correction actually move pixels, and in which channels?

ARM A: STREHL_FIX_CA unset  -> banner said CORRECTING (gear matched, default on)
ARM B: STREHL_FIX_CA=0      -> banner said off

Both arms come from ONE binary, so this is a same-binary A/B and needs no green
restriction. It is a presence/absence test, not a quality statistic, so the sRGB
tone curve on these renders does not invalidate it: a nonzero difference is
nonzero through any monotone curve.

Lateral CA is a radial, wavelength-dependent displacement. If the correction is
real it must move red and blue and leave green very nearly alone -- green is the
reference channel the other two are registered onto. That is a prediction the
mechanism makes BEFORE the measurement, not a description of the result.

Never PIL for 16-bit RGB: it silently downconverts to 8 bits.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import tifffile

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\BUILD-RENDER-caprobe")


def main() -> int:
    a_p, b_p = SCRATCH / "a.tiff", SCRATCH / "b.tiff"
    for p in (a_p, b_p):
        if not p.exists():
            print(f"missing {p}")
            return 2

    a, b = tifffile.imread(str(a_p)), tifffile.imread(str(b_p))
    assert a.dtype == np.uint16 and b.dtype == np.uint16, "not uint16"
    assert a.shape == b.shape, f"shape {a.shape} != {b.shape}"
    print(f"shape {a.shape} {a.dtype}   (A = CA corrected, B = CA off)")

    ai, bi = a.astype(np.int32), b.astype(np.int32)
    names = ("R", "G", "B")
    stats = {}
    for i, nm in enumerate(names):
        d = np.abs(ai[:, :, i] - bi[:, :, i])
        moved = float((d > 0).mean() * 100.0)
        stats[nm] = (int(d.max()), float(d.mean()), moved)
        print(f"  {nm}  max {d.max():6d} DN   mean {d.mean():8.3f} DN   pixels moved {moved:6.2f}%")

    r_max, g_max, b_max = (stats[n][0] for n in names)

    print()
    if r_max == 0 and g_max == 0 and b_max == 0:
        print("INERT: the switch changed the banner but not one pixel. The banner "
              "would then be decoration and the 26/26 evidence worthless.")
        return 1

    print(f"POTENT: the correction moves pixels (max R{r_max} G{g_max} B{b_max} DN).")
    if g_max < r_max and g_max < b_max:
        print("PREDICTION HELD: green moves least, as a lateral-CA correction "
              "registering R and B onto G must.")
    else:
        print("PREDICTION FAILED: green did not move least. The mechanism story "
              "does not fit; do not describe this as lateral CA without checking.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
