"""Which render did the acquittal baseline actually adjudicate?

The print gate expired four acquittals with messages like

    blotch 0.14667 -> 0.24933 (70.0% > 5%)

which reads as a measurement of drift in the product. Before I let that
stand I have to know it is not a measurement of my own wiring. Two renders
exist on disk - SHIP-V2 (8/26 10:22) and SHIP-V4 (8/27 01:43) - and the
gate's SHIP constant names the older one.

This runs the SAME functions the gate imports against BOTH files and
prints them side by side. If a baseline value matches V2 and the gate's
value matches V4, the expiry is real drift and the gate is correct. If
neither matches, the baseline came from an instrument nobody can identify
and every comparison against it is void.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from orch_blotch import blotch_ratio, flattest, lum_of  # noqa: E402

V2 = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")
V4 = pathlib.Path(r"C:\dev\strehl-out\acceptance\SHIP-V4")
BASE = HERE.parent / "V-REVIEW" / "vr_baseline.json"

SUBJECTS = ["112MSDCF", "113MSDCF", "coffee-bubbles", "couch-fibers-cpl",
            "foam", "109MSDCF", "flat-on-ruler-cpl", "flower-inner-edge-cpl",
            "lead-1-cpl", "leaf-2-cpl"]


def measure(path):
    a = tifffile.imread(str(path))
    y = lum_of(a)
    yy, xx = flattest(y)
    return float(blotch_ratio(y[yy:yy + 900, xx:xx + 900])[0]), [int(yy), int(xx)]


def find(root, name):
    for p in sorted(root.glob("*.tiff")):
        if p.name.startswith(name + "--"):
            return p
    return None


def main():
    base = json.load(open(BASE, encoding="utf-8"))["subjects"]
    print("%-22s %10s | %10s %-16s | %10s %-16s | verdict"
          % ("subject", "baseline", "SHIP-V2", "window", "SHIP-V4", "window"))
    tally = {"V2": 0, "V4": 0, "neither": 0, "absent": 0}
    for name in SUBJECTS:
        rec = base.get(name)
        want = None if rec is None else rec.get("master", {}).get("blotch")
        p2, p4 = find(V2, name), find(V4, name)
        if p2 is None or p4 is None or want is None:
            tally["absent"] += 1
            print("%-22s %10s | %s" % (name, want, "MISSING a file or a baseline row"))
            continue
        v2, w2 = measure(p2)
        v4, w4 = measure(p4)
        # 0.5% is far tighter than the gate's 5% tolerance; this is an
        # identity test, not a drift test.
        m2 = abs(v2 - want) / want < 0.005
        m4 = abs(v4 - want) / want < 0.005
        if m2 and not m4:
            v, tag = "V2", "baseline adjudicated the OLD render"
            tally["V2"] += 1
        elif m4 and not m2:
            v, tag = "V4", "baseline adjudicated the CURRENT render"
            tally["V4"] += 1
        elif m2 and m4:
            v, tag = "both", "renders agree here, tells us nothing"
            tally["V2"] += 1
        else:
            v, tag = "NEITHER", "baseline matches no render on disk"
            tally["neither"] += 1
        print("%-22s %10.5f | %10.5f %-16s | %10.5f %-16s | %s: %s"
              % (name, want, v2, str(w2), v4, str(w4), v, tag))

    print("\npartition: V2 %d + V4 %d + neither %d + absent %d = %d of %d"
          % (tally["V2"], tally["V4"], tally["neither"], tally["absent"],
             sum(tally.values()), len(SUBJECTS)))
    if tally["neither"]:
        print("\nA baseline row matching NO render on disk cannot be compared "
              "against anything. Those acquittals are void, not expired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
