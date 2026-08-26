"""The deliverable: pictures of the veil fix, all arms at ONE identical gain.

The bar on this project is a picture, not a scalar, and this build has already
had one spectacular numeric result killed by looking at the crop it described
(section 24). So every claim in `veil_accept.py` gets a matching image here.

The one rule that matters: **every arm is developed with the SAME gain**,
computed once from the baseline. The veil estimator only ever raises pixels, so
an arm-specific autostretch would renormalise the lift away and show a fix that
is really a brightness change -- or hide a real one. The gain is printed.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

import fullframe as ff

OUT = Path(r"C:\dev\strehl-out\VEIL")
PIC = OUT / "pics"

ARMS = [
    ("off", "fb-off.tif"),
    ("pm-off", "fb-pm-off.tif"),
    ("pm-c1.5", "fb-pm-c1p5.tif"),
    ("pm-c4.0", "fb-pm-c4p0.tif"),
]

BEE = [
    ("pm-off", "bee2-pm-off.tif"),
    ("pm-c1.5", "bee2-pm-c1p5.tif"),
    ("pm-floor", "bee2-pm-fl.tif"),
]

CF = [
    ("pm-off", "cf-pm-off.tif"),
    ("pm-floor", "cf-pm-fl.tif"),
]


def main() -> int:
    PIC.mkdir(parents=True, exist_ok=True)

    base = ff.read16(str(OUT / ARMS[0][1]))
    # Gain fixed from the BASELINE far field so it is a property of the scene,
    # not of the arm being judged.
    far = float(np.median(base[:, :400, 1]))
    gain = 0.75 * 65535.0 / max(far, 1.0)
    print(f"baseline far-field green {far:.0f} DN -> shared display gain {gain:.4f}")
    del base

    # A crop straddling the silhouette, where rim and surround sit side by side.
    cy, cx, half = 1170, 1760, 480

    for name, fn in ARMS:
        p = OUT / fn
        if not p.exists():
            print(f"  {name:10s} pending")
            continue
        a = ff.read16(str(p))
        tag = name.replace(".", "p")
        ff.write_png(str(PIC / f"fb-{tag}-full.png"),
                     ff.develop(ff.box_downsample(a, 1400), gain))
        crop = a[cy - half:cy + half, cx - half:cx + half]
        ff.write_png(str(PIC / f"fb-{tag}-crop.png"), ff.develop(crop, gain))
        print(f"  {name:10s} full + crop written  (crop mean {crop.mean():.0f} DN)")

    print(f"\npictures in {PIC}")

    # bee-2: the portfolio subject. Same rule -- one gain, fixed from the
    # baseline arm, shared by both.
    for label, arms in (("bee2", BEE), ("cf", CF)):
        b0 = OUT / arms[0][1]
        if not b0.exists():
            continue
        base = ff.read16(str(b0))
        far = float(np.median(base[:, :400, 1]))
        gain = 0.75 * 65535.0 / max(far, 1.0)
        print(f"\n{label} baseline far-field green {far:.0f} DN -> shared gain {gain:.4f}")
        del base
        for name, fn in arms:
            p = OUT / fn
            if not p.exists():
                print(f"  {name:10s} pending")
                continue
            a = ff.read16(str(p))
            tag = name.replace(".", "p")
            ff.write_png(str(PIC / f"{label}-{tag}-full.png"),
                         ff.develop(ff.box_downsample(a, 1400), gain))
            print(f"  {name:10s} full written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
