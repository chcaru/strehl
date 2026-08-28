r"""MATCHED CONTROL FOR THE MID-SCALE RE-RUN: measure in the space the
published run measured in.

render_all.ps1 rendered the vanished 1cacb61 tree with --demosaic and NO
--srgb: camera-linear.  Both surviving renders are the opposite.
acceptance/SHIP-V4's own provenance file says, in capitals,

    colour space  : sRGB, TONE CURVE APPLIED -- DO NOT MEASURE NUMERICALLY

and ORCH-FAITHFUL/faithful matches it to 0.02% on the green channel, so the
deliverable is in that same encoded space.  The sRGB curve is concave, so it
compresses a fractional excursion near the far field by roughly a factor of
0.42.  Comparing an encoded re-run against a linear published run without
undoing that is exactly the unmatched-control error this lane exists to catch.

So: undo the curve, write a camera-linear uint16 TIFF, and run the SAME
instrument on it.  If the ring is still 25-80x below the published figure in
linear light, the encoding was not the explanation.

The inverse curve is applied to the stored values only.  No exposure gain is
touched, and the ring statistic is a RATIO to the far field, so any constant
scale cancels.
"""
import os
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import vrim_rays                                                   # noqa: E402

DELIV = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
LIN = r"D:\strehl-out\V-RIM\lin"
OUT = r"D:\strehl-out\V-RIM\ring-lin"
FIVE = ["bee-3-cpl", "flower-bud-alone-cpl",
        "flower-bud-with-background-fern-cpl", "lavendar-cpl", "coffee-bean"]


def unsrgb(v):
    return np.where(v <= 0.04045, v / 12.92,
                    np.power((v + 0.055) / 1.055, 2.4))


def linearize(lab):
    dst = Path(LIN) / (lab + "-lin.tif")
    if dst.exists():
        return dst
    a = tifffile.imread(str(Path(DELIV) / (lab + ".tiff")))
    v = a.astype(np.float32) / 65535.0
    del a
    lin = unsrgb(v).astype(np.float32)
    del v
    # rescale to fill uint16; a constant scale cancels in every ratio reported
    lin *= 65535.0 / max(float(lin.max()), 1e-9)
    Path(LIN).mkdir(parents=True, exist_ok=True)
    tifffile.imwrite(str(dst), np.clip(lin, 0, 65535).astype(np.uint16))
    del lin
    print("linearised %s -> %s" % (lab, dst))
    return dst


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for lab in FIVE:
        if (Path(OUT) / (lab + "-rays.json")).exists():
            print("skip %s" % lab)
            continue
        p = linearize(lab)
        vrim_rays.run(p, lab, OUT)
