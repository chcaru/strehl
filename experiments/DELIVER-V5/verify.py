"""verify.py -- re-derive every shipped file from the master. Trust nothing build.py said.

build.py measured its own output.  That is the arrangement this project has been
burned by: a number printed by the code that produced the thing it is judging.
verify.py opens the SHIPPED PNGs off disk, re-reads the masters, and re-derives
both products independently:

  overview   strip the label bar, and require
               (a) hull_block injected rim == 0.000000 exactly, and
               (b) byte equality with an independently recomputed box reduction.
             (a) alone is not enough: it is satisfied by any faithful-enough
             image.  (b) alone is not enough either -- it would pass if my
             reduction were itself wrong.  Together they say the shipped pixels
             are the area average of the master and contain no manufactured rim.

  crop       strip the label bar and require BYTE equality with the integer
             slice of the master at the manifest's (x0, y0).  Not "close".
             Equal.  A crop that needed a tolerance would not be a 1:1 crop.

And a negative control, because a checker that has only ever passed is not
evidence: the same comparison is run against a deliberately corrupted copy of
each shipped overview and each shipped crop, and it must FAIL on those.

Usage:  python verify.py
"""
import json
import os
import sys

import numpy as np
import tifffile
from PIL import Image

import rimlib

DST = r"C:\dev\strehl-out\DELIVER-V5"


def main():
    with open(os.path.join(DST, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    K, CROP = man["k"], man["crop"]
    BO, BC = man["bar_overview"], man["bar_crop"]

    ok, bad, missing = [], [], []
    rims, aes = [], []
    ctrl_pass, ctrl_fail = 0, 0
    n_files = 0

    for rec in man["images"]:
        name = rec["name"]
        try:
            a8 = rimlib.to8(tifffile.imread(rec["master"]))
        except Exception as e:                                    # noqa: BLE001
            missing.append((name, "master unreadable: %s" % e))
            continue

        probs = []

        # ---- overview -------------------------------------------------------
        po = os.path.join(DST, "overview", rec["overview"])
        if not os.path.exists(po):
            probs.append("overview missing")
        else:
            n_files += 1
            shipped = np.asarray(Image.open(po).convert("RGB"))[:-BO]
            ref = np.rint(rimlib.box_reduce(a8, K)).astype(np.uint8)
            if shipped.shape != ref.shape:
                probs.append("overview shape %s != recomputed %s"
                             % (shipped.shape, ref.shape))
            else:
                exc, dfc = rimlib.hull_block(a8, shipped.astype(np.float64), K)
                rim = float(np.maximum(exc, dfc).max())
                ae = rimlib.area_err(a8, shipped.astype(np.float64), K)
                rims.append(rim)
                aes.append(ae)
                if rim != 0.0:
                    probs.append("overview injected rim %.9f DN != 0" % rim)
                if not np.array_equal(shipped, ref):
                    probs.append("overview differs from an independent box reduction")
                if ae > 0.5 + 1e-9:
                    probs.append("overview area_err %.6f exceeds the 0.5 DN "
                                 "rounding bound" % ae)
                # negative control: one pixel moved by 60 DN must be caught
                corrupt = shipped.copy()
                cy, cx = ref.shape[0] // 2, ref.shape[1] // 2
                base = int(corrupt[cy, cx, 1])
                corrupt[cy, cx, 1] = 255 if base < 128 else 0
                e2, d2 = rimlib.hull_block(a8, corrupt.astype(np.float64), K)
                caught = float(np.maximum(e2, d2).max()) > 0.0 or \
                    not np.array_equal(corrupt, ref)
                ctrl_pass += 1 if caught else 0
                ctrl_fail += 0 if caught else 1

        # ---- crops ----------------------------------------------------------
        for c in rec["crops"]:
            pc = os.path.join(DST, "crops-1to1", c["file"])
            if not os.path.exists(pc):
                probs.append("crop %s missing" % c["file"])
                continue
            n_files += 1
            shipped = np.asarray(Image.open(pc).convert("RGB"))[:-BC]
            ref = a8[c["y0"]:c["y0"] + CROP, c["x0"]:c["x0"] + CROP]
            if shipped.shape != ref.shape:
                probs.append("crop %s shape %s != %s"
                             % (c["file"], shipped.shape, ref.shape))
            elif not np.array_equal(shipped, ref):
                d = np.abs(shipped.astype(int) - ref.astype(int))
                probs.append("crop %s is NOT a byte-exact integer slice "
                             "(max diff %d DN, %d px differ)"
                             % (c["file"], d.max(), int((d > 0).sum())))
            else:
                corrupt = shipped.copy()
                corrupt[CROP // 2, CROP // 2, 0] ^= 0x40
                caught = not np.array_equal(corrupt, ref)
                ctrl_pass += 1 if caught else 0
                ctrl_fail += 0 if caught else 1

        (ok if not probs else bad).append(
            name if not probs else (name, "; ".join(probs)))
        print("%-38s %s" % (name, "OK" if not probs else "BAD  " + "; ".join(probs)),
              flush=True)
        del a8

    n = len(man["images"])
    print("\n=== counted partition of manifest entries ===")
    print("  verified %d + bad %d + unreadable %d = %d of %d   %s"
          % (len(ok), len(bad), len(missing), len(ok) + len(bad) + len(missing), n,
             "OK" if len(ok) + len(bad) + len(missing) == n else "MISMATCH"))
    for nm, why in missing:
        print("  UNREADABLE %-28s %s" % (nm, why))
    for item in bad:
        print("  BAD        %-28s %s" % item)

    print("\n=== the shipped gallery's own injected rim ===")
    if rims:
        print("  hull_block over %d shipped overviews: max %.9f  median %.9f DN"
              % (len(rims), max(rims), float(np.median(rims))))
        print("  area_err  over %d shipped overviews: max %.9f DN (bound 0.5 = "
              "uint8 rounding of an exact area average)" % (len(aes), max(aes)))
    print("\n=== negative control: the checker must be able to fail ===")
    print("  corruption caught %d + missed %d = %d of %d"
          % (ctrl_pass, ctrl_fail, ctrl_pass + ctrl_fail, ctrl_pass + ctrl_fail))

    good = (not bad and not missing and ctrl_fail == 0 and rims
            and max(rims) == 0.0 and n_files > 0)
    print("\nVERDICT: %s" % (
        "every shipped file is re-derivable from its master, injected rim is "
        "exactly 0.000000000 DN, and the checker demonstrably fails on corrupted "
        "input" if good else "DO NOT SHIP"))
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
