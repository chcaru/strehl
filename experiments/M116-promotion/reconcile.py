"""Reconcile two readings of the same arms that point in opposite directions.

score_arms.py reports the instrument's headline median falling from 1.114 (P0)
to 1.101 (P1) -- photometric looking mildly helpful. gain_check.py reports the
per-window Laplacian RMS RISING in 10 of 12 windows, median +4.4 percent --
photometric looking harmful. The window sets are supposed to be identical, so
at most one of these can be a fair description and I am not reporting either
until I know which.

This compares the instrument's OWN printed per-window tables for the two arms,
row by row, which is the authoritative record of what it actually measured.
Prints nothing but the reconciliation. Reads nothing on D:.
"""

import os
import re
import sys

import numpy as np

OUT = r"C:\dev\strehl-out\M116\invariant"
ROW = re.compile(
    r"^(\d+)\s+(\d+)\s+(-?[0-9.]+|nan)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+"
    r"([0-9.]+)\s+([0-9.]+)\s*$")


def table(tag):
    path = os.path.join(OUT, "score-%s.log" % tag)
    if not os.path.exists(path):
        print("GUARD: missing " + path)
        sys.exit(3)
    with open(path) as fh:
        rows = []
        for line in fh:
            m = ROW.match(line.strip())
            if m:
                rows.append({
                    "x": int(m.group(1)), "y": int(m.group(2)),
                    "hf": float(m.group(4)), "hfmin": float(m.group(5)),
                    "hfmax": float(m.group(6)), "vsmax": float(m.group(8)),
                })
    if len(rows) != 12:
        print("GUARD: parsed %d rows from %s, expected 12" % (len(rows), tag))
        sys.exit(3)
    return rows


def main():
    a = table("P0-default")
    b = table("P1-photometric")

    same_windows = [(r["x"], r["y"]) for r in a] == [(r["x"], r["y"]) for r in b]
    same_denoms = all(abs(r["hfmax"] - s["hfmax"]) < 1e-9 for r, s in zip(a, b))

    print("window sets identical across arms : %s" % same_windows)
    print("denominators identical across arms: %s" % same_denoms)
    print("")
    print("%-6s %-6s %10s %10s %9s %9s %9s"
          % ("x", "y", "hf P0", "hf P1", "hf P1/P0", "vsMAX P0", "vsMAX P1"))
    for r, s in zip(a, b):
        print("%-6d %-6d %10.1f %10.1f %9.4f %9.3f %9.3f"
              % (r["x"], r["y"], r["hf"], s["hf"], s["hf"] / r["hf"],
                 r["vsmax"], s["vsmax"]))

    hf_ratio = np.array([s["hf"] / r["hf"] for r, s in zip(a, b)])
    v0 = np.array([r["vsmax"] for r in a])
    v1 = np.array([s["vsmax"] for s in b])

    print("")
    print("median hf ratio P1/P0        : %.4f  (%d of 12 windows rise)"
          % (np.median(hf_ratio), int((hf_ratio > 1.0).sum())))
    print("median vsMAX P0              : %.4f" % np.median(v0))
    print("median vsMAX P1              : %.4f" % np.median(v1))
    print("median of the PER-WINDOW ratio of vsMAX: %.4f" % np.median(v1 / v0))
    print("")
    print("The headline is a median of per-window ratios, and a median is not "
          "linear: it reports whichever window lands in the middle, not the "
          "average behaviour of the set.")
    order0 = np.argsort(v0)
    order1 = np.argsort(v1)
    mid0 = [(a[i]["x"], a[i]["y"]) for i in order0[5:7]]
    mid1 = [(b[i]["x"], b[i]["y"]) for i in order1[5:7]]
    print("windows straddling the median, P0: %s" % mid0)
    print("windows straddling the median, P1: %s" % mid1)
    print("the median moved to a DIFFERENT window: %s" % (mid0 != mid1))


if __name__ == "__main__":
    main()
