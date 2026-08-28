#!/usr/bin/env python3
"""How many frames does the oracle need before it starts missing sharp frames?

The corpus survey cannot decode 299 frames for 26 subjects, so it subsamples the
bracket.  Subsampling is DANGEROUS IN ONE DIRECTION: if a tile's depth of field
spans fewer frames than the stride, the sharp frame is never looked at, the
source arm is under-reported, and every subject drifts toward the verdict
"no frame was ever sharp there" -- which is the verdict prior art already
reached.  An instrument that manufactures agreement with the prior is worthless.

So this measures the loss directly on the one subject where the whole bracket
was decoded, by decimating the saved cube and comparing against the full answer.

Usage:  python stride_control.py <subject> [--band 2]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--band", type=int, default=2)
    args = ap.parse_args()
    A = np.load(os.path.join(ora.OUT, "stageA", args.subject + ".npz"))
    var_k, lev_k = A["var_k"], A["lev_k"]
    g = float(A["g_est"])
    K = var_k.shape[0]
    b = args.band

    full = ora.through_focus_contrast(var_k, lev_k, g)["contrast"][b]
    # tiles that genuinely carry resolvable structure: the top decile, since the
    # question "did subsampling miss a sharp frame" is only meaningful where a
    # sharp frame exists at all.
    det = full >= np.quantile(full, 0.90)
    print(f"{args.subject}: {K} frames decoded, band {b}, "
          f"{det.sum()} detail-bearing tiles (top decile) of {full.size}")
    print("  nframes | stride | median contrast retained | p05 retained | "
          "worst tile | best-frame index moved")
    fk_full = ora.through_focus_contrast(var_k, lev_k, g)["best_k"][b]
    for stride in (1, 2, 3, 4, 6, 8, 12, 16):
        idx = np.arange(0, K, stride)
        tf = ora.through_focus_contrast(var_k[idx], lev_k[idx], g)
        sub = tf["contrast"][b]
        ret = sub[det] / np.maximum(full[det], 1e-9)
        moved = np.abs(idx[tf["best_k"][b]] - fk_full)[det]
        print(f"  {len(idx):7d} | {stride:6d} | {np.median(ret):24.4f} | "
              f"{np.quantile(ret, 0.05):12.4f} | {ret.min():10.4f} | "
              f"median {np.median(moved):4.1f} frames, p95 "
              f"{np.quantile(moved, 0.95):5.1f}")
    print("\n  'retained' = subsampled contrast / full-bracket contrast, so 1.0")
    print("  means the stride lost nothing and <1.0 means it missed sharp frames.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
