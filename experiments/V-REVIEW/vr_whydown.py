"""Why did planting mid-scale energy LOWER the blotch reading?

blotch is a MINIMUM over windows (flattest() picks the lowest-texture window).
A global plant can move the argmin.  If it does, the ladder measured window
relocation, not added blotch -- and the ladder must be reported as such.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V
from orch_blotch import blotch_ratio, WIN as BWIN

DIR = r"C:\dev\strehl-out\V-REVIEW\commission-masters"
for tag, path in (("clean ", V.master_path("112MSDCF")),
                  ("planted", os.path.join(DIR, "112MSDCF--SHIP-V3.tiff"))):
    rgb = V.read_rgb(path)
    lum = V.lum_of(rgb)
    b = V.gate_blotch(rgb)
    # and the SAME window the adjudication used, held fixed
    fy, fx = 2254, 5926
    r, bd, nd, md = blotch_ratio(lum[fy:fy + BWIN, fx:fx + BWIN])
    print("%s picked window (%4d,%4d) blotch %.5f band %7.1f mean %8.1f | "
          "at FROZEN window (2254,5926) blotch %.5f band %7.1f mean %8.1f"
          % (tag, b["y"], b["x"], b["contrast"], b["band"], b["mean"], r, bd, md))
