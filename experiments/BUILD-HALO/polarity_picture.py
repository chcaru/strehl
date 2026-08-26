"""Pictures for the polarity arm, both developed at ONE shared gain.

The gain is fixed from the BASELINE arm's global median rather than from a
left-edge strip: `veil_picture.py` uses `base[:, :400]` as far field, which is
backdrop on flower-bud but is not guaranteed to be backdrop on this subject.
A gain taken from the wrong region would rescale both arms equally, so it could
not manufacture a difference -- but it could push the whole frame out of the
visible range and hide one.
"""

from pathlib import Path
import sys

import numpy as np

import fullframe as ff

OUT = Path(r"C:\dev\strehl-out\VEIL")
PIC = OUT / "pics"

ARMS = [("pm-off", "pen-pm-off.tif"), ("veil-old", "pen-pm-fl.tif"), ("veil-pol", "pen-pol.tif")]


def main() -> int:
    PIC.mkdir(parents=True, exist_ok=True)
    base = ff.read16(str(OUT / ARMS[0][1]))
    ref = float(np.median(base[..., 1]))
    gain = 0.45 * 65535.0 / max(ref, 1.0)
    print(f"baseline global median green {ref:.0f} DN -> shared display gain {gain:.4f}")
    del base

    for name, fn in ARMS:
        p = OUT / fn
        if not p.exists():
            print(f"  {name:10s} pending")
            continue
        a = ff.read16(str(p))
        ff.write_png(str(PIC / f"pen-{name}-full.png"),
                     ff.develop(ff.box_downsample(a, 1400), gain))
        print(f"  {name:10s} full written  (median {np.median(a[..., 1]):.0f} DN)")
    print(f"\npictures in {PIC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
