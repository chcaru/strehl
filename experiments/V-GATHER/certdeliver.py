r"""Measure the DELIVERED file -- the one that is actually printed.

WHY THIS IS NOT THE GAUGE MISTAKE AGAIN, and the distinction is the whole design.

The gauge defect is a defect in RATIOS. Two images developed through two
different content-fitted tone curves cannot have their contrasts divided. It is
not a defect in measuring ONE image: the delivered sRGB master is a display-
referred file, it is the artifact that goes to the printer, and its contrasts are
exactly the contrasts a viewer will see. For the question "is this defect
VISIBLE", the display-referred file is not merely an acceptable gauge, it is the
only correct one -- measuring visibility in linear light would ask whether the
defect is visible in a file nobody looks at.

So this project's two questions are measured in two places, on purpose:

  IS IT VISIBLE?      absolute, on the delivered sRGB file      <- here
  DID THE MERGE DO IT? ratio, on a matched --linear-srgb pair   <- certmeasure.py

Conflating them is what produced a certification that could not fail.
"""
import json
import os
import sys

import numpy as np
import tifffile

ORCH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ORCH-drift-check")
sys.path.insert(0, os.path.abspath(ORCH))
from orch_blotch import blotch_ratio, flattest, lum_of        # noqa: E402
from orch_chroma import banding, chroma_blotch, pick_window   # noqa: E402

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "delivered.json")


def main():
    doc = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    subs = sorted(f[:-len("--SHIP-V4.tiff")] for f in os.listdir(SHIP)
                  if f.endswith("--SHIP-V4.tiff"))
    print("%-30s %9s %9s %8s %9s %8s" % ("subject", "blotch", "chroma", "run px",
                                         "step DN", "clip %"))
    print("-" * 80)
    for s in subs:
        if s in doc:
            r = doc[s]
        else:
            p = os.path.join(SHIP, "%s--SHIP-V4.tiff" % s)
            a = tifffile.imread(p)
            rgb = a[:, :, :3].astype(np.float32)
            lum = lum_of(rgb)
            y, x = flattest(lum)
            br = blotch_ratio(lum[y:y + 900, x:x + 900])
            ch = chroma_blotch(rgb)
            bd = banding(rgb)
            hi = rgb >= 65500
            r = {"blotch": float(br[0]), "band_dn": float(br[1]),
                 "mean_dn": float(br[3]),
                 "chroma": float(ch[0]) if ch else None,
                 "band_run": float(bd[0]) if bd and not isinstance(bd[0], str) else None,
                 "band_step": float(bd[4]) if bd and not isinstance(bd[0], str) else None,
                 "clip": float((hi.sum(axis=2) == 3).mean()),
                 "crush": float((rgb <= 35).mean()),
                 "at_blotch": [int(y), int(x)]}
            doc[s] = r
            json.dump(doc, open(OUT, "w", encoding="utf-8"), indent=1)
            del rgb, a, lum
        print("%-30s %9.5f %9.5f %8s %9s %8.4f"
              % (s, r["blotch"], r["chroma"] if r["chroma"] is not None else float("nan"),
                 ("%.1f" % r["band_run"]) if r["band_run"] is not None else "-",
                 ("%.1f" % r["band_step"]) if r["band_step"] is not None else "-",
                 r["clip"] * 100))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
