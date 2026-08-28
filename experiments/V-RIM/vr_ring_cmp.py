r"""Score every mid-scale arm side by side against the published table."""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "src"))
from ringstat import ring_and_null                                 # noqa: E402
from vr_ring2 import PUBLISHED                                     # noqa: E402

ARMS = [("deliverable sRGB", r"D:\strehl-out\V-RIM\ring"),
        ("SHIP-V4 sRGB", r"D:\strehl-out\V-RIM\ring-ship"),
        ("deliverable LINEARISED", r"D:\strehl-out\V-RIM\ring-lin")]
FIVE = ["bee-3-cpl", "flower-bud-alone-cpl",
        "flower-bud-with-background-fern-cpl", "lavendar-cpl", "coffee-bean"]


def score(d):
    s = d["straight"]
    r, n = ring_and_null(s["grid"], s["med"], s["far"])
    det = r["frac"] >= 3 * max(n["frac"], 0.0005)
    return r, n, det


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("=" * 104)
    print("MID-SCALE RING: published (vanished 1cacb61 LINEAR render) vs every")
    print("surviving render, same instrument, unmodified.")
    print("=" * 104)
    print("%-38s %22s %22s %22s %22s"
          % ("subject", "PUBLISHED lin", "deliverable sRGB", "SHIP-V4 sRGB",
             "deliverable LINEARISED"))
    for lab in FIVE:
        pf, pr, pt, pn = PUBLISHED[lab]
        cells = ["%8.2f%% @%3.0f  RING" % (pr, pt)]
        for name, d in ARMS:
            f = Path(d) / (lab + "-rays.json")
            if not f.exists():
                cells.append("%20s" % "not run")
                continue
            j = json.loads(f.read_text())
            if not j.get("straight"):
                cells.append("%20s" % "no rays")
                continue
            r, n, det = score(j)
            cells.append("%8.2f%% @%3.0f %6s"
                         % (100 * r["frac"], r["t_peak"],
                            "RING" if det else "no ring"))
        print("%-38s %22s %22s %22s %22s" % (lab, *cells))
