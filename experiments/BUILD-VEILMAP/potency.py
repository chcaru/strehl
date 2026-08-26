"""Potency and null, read out of the GRID rather than from a hand-placed box.

ORCH's hard-fail: the claw block must classify MULTI-PEAK.  A named window
measured on its own does not prove that, because the grid is what produces the
headline number and the grid's blocks do not sit where the hand-placed box
sits.  So this looks up the grid cell that contains the claw's centre, at every
block size, in both arms, under both prominence definitions, and prints what
the instrument that produced the corpus number actually says about it.
"""
import argparse
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from classify import classify, peaks, peaks_topo  # noqa: E402

TAGS = ["FLAT", "SINGLE-PEAK", "MULTI-PEAK"]
POINTS = {                      # master px (y, x), from V-VEILCLAW/probe.py
    "claw": (2735, 2175),       # centre of y 2640:2830 x 2080:2270
    "ctl": (3285, 2065),
    "null": (250, 6700),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", default="bee-3-cpl")
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-VEILMAP")
    ap.add_argument("--points", default="claw,ctl,null")
    a = ap.parse_args()
    z = np.load(pathlib.Path(a.out) / "tensors" / f"{a.subject}.npz")
    ks = z["ks"]
    print(f"{a.subject}: grid cells containing named master points\n")
    print(f"{'point':<6}{'block':>6}{'arm':>7}{'det':>8}  {'class':<12}"
          f"{'peaks (frame index : prominence)'}")
    fail = []
    for nm in a.points.split(","):
        py, px = POINTS[nm]
        for B in [int(v) for v in z["blocks"]]:
            b = B // 2
            gy, gx = z[f"gy_b{B}"], z[f"gx_b{B}"]
            i = int(np.clip(np.searchsorted(gy, py / 2, "right") - 1,
                            0, len(gy) - 1))
            j = int(np.clip(np.searchsorted(gx, px / 2, "right") - 1,
                            0, len(gx) - 1))
            for arm in ("resp", "fixed"):
                v = z[f"{arm}_b{B}"][:, i, j].astype(np.float64)
                for dn, det in (("global", peaks), ("topo", peaks_topo)):
                    pk, c = classify(v, det)
                    d = "  ".join(f"f{ks[p[0]]}:{p[2]:.2f}" for p in pk)
                    print(f"{nm:<6}{B:>6}{arm:>7}{dn:>8}  {TAGS[c]:<12}{d}")
                    if nm == "claw" and c != 2:
                        fail.append(f"{nm} b{B} {arm}/{dn} -> {TAGS[c]}")
                    if nm == "null" and c != 0:
                        fail.append(f"{nm} b{B} {arm}/{dn} -> {TAGS[c]}")
        print()
    if fail:
        print("POTENCY/NULL FAILURES:")
        for f in fail:
            print(f"  {f}")
    else:
        print("POTENCY PASS (claw MULTI-PEAK everywhere) and "
              "NULL PASS (paper FLAT everywhere)")


if __name__ == "__main__":
    main()
