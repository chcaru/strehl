#!/usr/bin/env python3
"""List and characterise the tiles where the source arm beats the merge.

The headline verdict is about the regions the eye flagged.  This asks the
complementary question the brief also asks -- WHERE, over the whole frame, does
the merge lose -- and then interrogates each losing tile, because "source beats
merge" has three quite different causes that must not be pooled:

  ALIASED     the merge tile is dominated by content above green Nyquist, so
              the point-sampled comparison is not measuring the same passband.
              Detected by the point/box sampling pair disagreeing sharply.
  EDGE        the tile touches the frame border, where the master's crop and
              the frame's active area do not cover the same scene.
  REAL        neither of the above: the frame genuinely holds structure the
              merge did not deliver.

Every losing tile lands in exactly one of these and the counts are asserted to
sum.  Usage:  python losers.py <subject> [--band 2] [--thresh 1.25]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--band", type=int, default=2)
    ap.add_argument("--thresh", type=float, default=1.25)
    args = ap.parse_args()
    b = args.band

    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    B = np.load(os.path.join(ora.OUT, "stageB", args.subject + ".npz"))
    nr, nc = int(A["nr"]), int(A["nc"])
    con, var_k, ks = A["contrast"], A["var_k"], A["frames"]
    modes = [str(m) for m in B["modes"]]
    with np.errstate(divide="ignore", invalid="ignore"):
        rat = {m: con[b] / np.maximum(B[f"{m}_sig"][b], 1e-9) for m in modes}
    det = con[b] >= np.nanquantile(con[b], 0.90)

    # A tile only counts as losing if it loses under BOTH samplings.  'point'
    # flatters the merge and 'box' flatters the frames, so requiring both is
    # requiring the result to survive the choice that has no neutral answer.
    lose = det & np.all([rat[m] > args.thresh for m in modes], axis=0)
    print(f"{args.subject} band {b}: {int(lose.sum())} tiles where the best "
          f"source frame beats the merge by >{args.thresh}x under BOTH "
          f"samplings, out of {int(det.sum())} detail tiles / {nr * nc} total")
    only_one = det & (np.any([rat[m] > args.thresh for m in modes], axis=0)
                      & ~lose)
    print(f"  ({int(only_one.sum())} more lose under one sampling but not the "
          f"other -- counted, not dropped, and excluded from 'REAL' because a "
          f"result that depends on the resampling choice is a measurement of "
          f"the choice)")

    idx = np.argsort(-np.where(lose, rat[modes[0]], -np.inf).ravel())
    cnt = {"ALIASED": 0, "EDGE": 0, "REAL": 0}
    print(f"\n  {'tile':<9}{'master y,x':<18}{'ratio pt':>9}{'ratio box':>10}"
          f"{'srcsig':>10}{'mrgsig':>10}{'bestk':>7}{'rise':>7}  class")
    for j in idx[:int(lose.sum())]:
        r, c = divmod(int(j), nc)
        rp, rb = rat[modes[0]][r, c], rat[modes[-1]][r, c]
        edge = (r == 0 or c == 0 or r == nr - 1 or c == nc - 1)
        alias = abs(np.log(max(rp, 1e-9)) - np.log(max(rb, 1e-9))) > np.log(1.3)
        cls = "EDGE" if edge else ("ALIASED" if alias else "REAL")
        cnt[cls] += 1
        cur = var_k[:, b, r, c].astype(float)
        k = int(np.argmax(cur))
        floor = float(np.quantile(cur, 0.25))
        end = 0 if k <= len(cur) - 1 - k else len(cur) - 1
        rise = (cur[k] - cur[end]) / max(cur[k] - floor, 1e-9)
        print(f"  r{r:02d}c{c:02d}   {r * TS * 2:5d},{c * TS * 2:<11d}"
              f"{rp:9.2f}{rb:10.2f}{con[b, r, c]:10.1f}"
              f"{B[modes[0] + '_sig'][b, r, c]:10.1f}{int(ks[k]):7d}"
              f"{rise:7.2f}  {cls}")
    tot = sum(cnt.values())
    print(f"\n  classification: " + "  ".join(f"{k}={v}" for k, v in cnt.items())
          + f"  TOTAL={tot}")
    assert tot == int(lose.sum()), f"{tot} != {int(lose.sum())}"
    print(f"  partition check OK: {tot} == {int(lose.sum())} losing tiles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
