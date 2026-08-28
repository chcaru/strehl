#!/usr/bin/env python3
"""Print the raw through-focus curves for named tiles, all bands.

argmax is not evidence.  A curve whose maximum sits at frame 0 can mean the
focus peak was captured exactly at the first frame, or it can mean the curve is
monotonically FALLING from the first frame -- i.e. the true peak is outside the
bracket and the sweep started already past it.  Those are opposite verdicts and
argmax cannot tell them apart.  This prints the curve so it can be read.

The end-slope statistic reported here is the discriminator:

    rise_end = (V[k*] - V[end]) / (V[k*] - floor)

evaluated at whichever end k* is nearer.  Near 1 means the curve fell away from
the peak inside the bracket, so focus WAS captured.  Near 0 means the curve is
still at its peak at the boundary, so the sweep ran out before focus did, and
the true best focus for that tile is a frame that was never taken.

Usage:  python curves.py <subject> --tiles "r,c r,c ..." [--band all]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

SPARK = " .:-=+*#%@"


def spark(v):
    v = np.asarray(v, float)
    lo, hi = v.min(), v.max()
    if hi <= lo:
        return " " * len(v)
    t = (v - lo) / (hi - lo)
    return "".join(SPARK[min(9, int(x * 9.999))] for x in t)


def end_rise(curve):
    """How far the curve falls from its peak by the nearer bracket end."""
    k = int(np.argmax(curve))
    floor = float(np.quantile(curve, 0.25))
    pk = float(curve[k])
    if pk - floor <= 0:
        return float("nan"), k, 0
    end = 0 if k <= len(curve) - 1 - k else len(curve) - 1
    return (pk - float(curve[end])) / (pk - floor), k, end


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    var_k = A["var_k"]
    ks = A["frames"]
    K = len(ks)
    n = 24                       # compact resample for the numeric row
    grid = np.linspace(0, K - 1, n).astype(int)

    for spec in args.tiles.split():
        r, c = (int(x) for x in spec.split(","))
        print(f"\n=== tile r={r} c={c}   {args.label} "
              f"(master y~{r * 128 * 2}-{(r + 1) * 128 * 2}, "
              f"x~{c * 128 * 2}-{(c + 1) * 128 * 2}) ===")
        print(f"    frames {int(ks[0])}..{int(ks[-1])} ({K} sampled)")
        for b in range(ora.NBAND):
            cur = var_k[:, b, r, c].astype(float)
            rise, kpk, kend = end_rise(cur)
            floor = float(np.quantile(cur, 0.25))
            print(f"  b{b} |{spark(cur)}| pk@{int(ks[kpk]):3d} "
                  f"max={cur.max():9.1f} floor={floor:8.1f} "
                  f"amp={cur.max() - floor:9.1f}  rise_end={rise:5.2f} "
                  f"(end k={int(ks[kend])})")
            print("       " + " ".join(f"{cur[g]:7.0f}" for g in grid[:12]))
            print("       " + " ".join(f"{cur[g]:7.0f}" for g in grid[12:]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
