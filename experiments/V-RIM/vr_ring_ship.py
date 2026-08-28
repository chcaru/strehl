r"""Second current render through the same mid-scale instrument.

The deliverable disagrees with the published mid-scale table by 25-80x. Two
explanations survive that alone: the vanished 1cacb61 render really did carry a
ring the shipping render does not, or the disagreement is mine. A second,
independently produced current render breaks the tie: if acceptance/SHIP-V4
also reads no ring, then two current renders agree with each other and the odd
one out is the render nobody can produce any more.
"""
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
import vrim_rays                                                   # noqa: E402

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = r"D:\strehl-out\V-RIM\ring-ship"
FIVE = ["bee-3-cpl", "flower-bud-alone-cpl",
        "flower-bud-with-background-fern-cpl", "lavendar-cpl", "coffee-bean"]

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for lab in FIVE:
        p = Path(SHIP) / (lab + "--SHIP-V4.tiff")
        if (Path(OUT) / (lab + "-rays.json")).exists():
            print("skip %s" % lab)
            continue
        vrim_rays.run(p, lab, OUT)
