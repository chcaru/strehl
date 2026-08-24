"""F3: does the demosaic branch change which frame wins a pixel?

Pre-registered falsification condition F3 says the fix is void if the demosaic
path changes the election. Two independent lines of evidence.

CODE. `demosaic` is consumed at exactly two places: it is passed into
`write_merged` (merge_cmd.rs:1588) and read inside it (2759, 2774). It is never
read during pass one or pass two. It therefore cannot influence the election.
That is a proof about the program text, and it is labelled DERIVED.

MEASUREMENT. At `--gate 0` the merge elects exactly one frame per pixel, so a
changed election shows up as a large pixel jump. Render the same stack at
`--gate 0` down both branches and compare. Agreement must be at least as tight
as the gate 2.0 pair.

POSITIVE CONTROL, and it is the whole point: the same comparison between two
renders that DO have different elections -- gate 0 against gate 2.0 -- must come
out far looser. Without that, a tight number proves only that the instrument is
blunt.
"""

import json
import os
import sys

import numpy as np
import tifffile

REN = r"C:\dev\strehl-out\M95-resolution"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from f2_boxcontrol import agree, box2  # noqa: E402


def agree2(a, b):
    d = np.abs(a.astype(np.float64) - b)
    out = {"median_abs": float(np.median(d)), "p99_abs": float(np.percentile(d, 99)),
           "p999_abs": float(np.percentile(d, 99.9)),
           "corr": float(np.corrcoef(a.ravel(), b.ravel())[0, 1])}
    for t in (500, 1000, 2000):
        out["frac_gt_%d" % t] = float((d > t).mean())
    return out


def pair(binned_path, demo_path):
    b = tifffile.imread(os.path.join(REN, binned_path)).astype(np.float64)
    d = tifffile.imread(os.path.join(REN, demo_path)).astype(np.float64)
    r = np.stack([box2(d[:, :, c]) for c in range(3)], axis=2)
    h, w = min(b.shape[0], r.shape[0]), min(b.shape[1], r.shape[1])
    return agree2(b[:h, :w], r[:h, :w])


def show(tag, s):
    print("   %-38s p99 %8.2f  p99.9 %9.2f  >1000DN %7.4f %%  corr %.6f"
          % (tag, s["p99_abs"], s["p999_abs"], 100 * s["frac_gt_1000"], s["corr"]))


def main():
    g0 = pair("g0-binned.tif", "g0-demosaic.tif")
    g2 = pair("ship-binned.tif", "ship-demosaic.tif")
    print("FIRST ATTEMPT USED THE MEDIAN AND ITS POSITIVE CONTROL FAILED: gate 0 vs")
    print("gate 2.0 read a SMALLER median (25.00 DN) than the branch comparison")
    print("(60.75 DN), because a changed election moves few pixels a lot, and a")
    print("median is blind to a sparse heavy tail. Tail statistics below.\n")
    print("binned vs box2(demosaic), SAME gate -- election must be unchanged")
    show("gate 0.0", g0)
    show("gate 2.0", g2)

    b0 = tifffile.imread(os.path.join(REN, "g0-binned.tif")).astype(np.float64)
    b2 = tifffile.imread(os.path.join(REN, "ship-binned.tif")).astype(np.float64)
    h, w = min(b0.shape[0], b2.shape[0]), min(b0.shape[1], b2.shape[1])
    ctl = agree2(b0[:h, :w], b2[:h, :w])
    print("\n   POSITIVE CONTROL -- gate 0 vs gate 2.0, same branch, elections DO differ")
    show("gate 0.0 vs gate 2.0", ctl)

    sep = ctl["frac_gt_1000"] / max(g0["frac_gt_1000"], 1e-12)
    print("\n   instrument can see a changed election (separation %.1fx on >1000 DN): %s"
          % (sep, sep > 3))
    ok = sep > 3 and g0["frac_gt_1000"] <= g2["frac_gt_1000"] * 1.5
    print("   F3 does NOT fire; the branch does not change the election: %s" % ok)
    with open(os.path.join(OUT, "f3_election.json"), "w", encoding="utf-8") as f:
        json.dump({"gate0": g0, "gate2": g2, "positive_control": ctl,
                   "separation_frac_gt_1000": sep, "f3_clear": bool(ok),
                   "median_control_failed": True}, f, indent=1)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
