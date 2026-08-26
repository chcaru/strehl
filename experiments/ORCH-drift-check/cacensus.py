#!/usr/bin/env python3
"""Corpus-wide A/B census of an edge-chroma change, with a built-in placebo.

This exists to answer "does the win generalise", which is a different question
from "is the win real on the subject I tuned it on".

Two design rules it obeys, both learned the hard way in this project:

  * **Pixel selection is made on the ARM MEAN, never on either arm.**  If the
    edge set is chosen on arm A, arm A picks its own ground and the comparison
    is rigged.  The mean is neutral between them.
  * **The flat set is the placebo and is reported next to the signal.**  A
    radial per-channel warp must be a near-no-op where there is no edge.  If
    the flat set moves as much as the edge set, the number is not measuring
    fringe removal and must not be read as if it were.  A placebo that moves is
    a result about the instrument, so it is printed on every row, not
    aggregated away.

Both arms must be the same subject rendered with the same binary and the same
flags, differing in exactly one thing.

Usage:
    python cacensus.py <dirA> <dirB> [--edge-pct 99] [--flat-pct 50]
"""
from __future__ import annotations

import argparse
import glob
import os

import numpy as np
import tifffile


def load(path: str) -> np.ndarray:
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"expected uint16 TIFF, got {a.dtype} for {path}"
    return a.astype(np.float32) / 65535.0


def grad(g: np.ndarray) -> np.ndarray:
    gy = np.zeros_like(g)
    gx = np.zeros_like(g)
    gy[:-1, :] = np.abs(np.diff(g, axis=0))
    gx[:, :-1] = np.abs(np.diff(g, axis=1))
    return gy + gx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dira")
    ap.add_argument("dirb")
    ap.add_argument("--edge-pct", type=float, default=99.0)
    ap.add_argument("--flat-pct", type=float, default=50.0)
    args = ap.parse_args()

    names = sorted(
        os.path.splitext(os.path.basename(p))[0]
        for p in glob.glob(os.path.join(args.dira, "*.tif*"))
    )

    print(f"A = {args.dira}")
    print(f"B = {args.dirb}")
    print(f"edge = top {100 - args.edge_pct:g}% of |grad| on the ARM MEAN; "
          f"flat = bottom {args.flat_pct:g}% (placebo)\n")
    hdr = (f"{'subject':<38s} {'edge R-G':>9s} {'edge R-B':>9s} {'edge B-G':>9s}"
           f" | {'flat R-G':>9s} {'flat R-B':>9s} {'flat B-G':>9s}")
    print(hdr)
    print("-" * len(hdr))

    rows: list[tuple[str, list[float], list[float]]] = []
    missing = 0
    for n in names:
        pb = os.path.join(args.dirb, n + ".tiff")
        if not os.path.exists(pb):
            missing += 1
            continue
        A, B = load(os.path.join(args.dira, n + ".tiff")), load(pb)
        if A.shape != B.shape:
            print(f"{n:<38s}  SHAPE MISMATCH {A.shape} vs {B.shape} -- skipped")
            missing += 1
            continue
        m = 0.5 * (A + B)
        mg = grad(m.mean(axis=2))
        hi = mg >= np.percentile(mg, args.edge_pct)
        lo = mg <= np.percentile(mg, args.flat_pct)

        e, f = [], []
        for i, j in ((0, 1), (0, 2), (2, 1)):
            da, db = A[..., i] - A[..., j], B[..., i] - B[..., j]
            sa, sb = da[hi].std(), db[hi].std()
            e.append(float(sb / sa) if sa else float("nan"))
            sa, sb = da[lo].std(), db[lo].std()
            f.append(float(sb / sa) if sa else float("nan"))
        rows.append((n, e, f))
        print(f"{n:<38s} {e[0]:9.4f} {e[1]:9.4f} {e[2]:9.4f} | "
              f"{f[0]:9.4f} {f[1]:9.4f} {f[2]:9.4f}")

    if not rows:
        print("\nno comparable pairs found")
        return 1

    E = np.array([r[1] for r in rows])
    F = np.array([r[2] for r in rows])
    print("-" * len(hdr))
    print(f"{'MEDIAN':<38s} {np.median(E[:, 0]):9.4f} {np.median(E[:, 1]):9.4f} "
          f"{np.median(E[:, 2]):9.4f} | {np.median(F[:, 0]):9.4f} "
          f"{np.median(F[:, 1]):9.4f} {np.median(F[:, 2]):9.4f}")
    print(f"{'WORST (max ratio)':<38s} {E[:, 0].max():9.4f} {E[:, 1].max():9.4f} "
          f"{E[:, 2].max():9.4f} | {F[:, 0].max():9.4f} {F[:, 1].max():9.4f} "
          f"{F[:, 2].max():9.4f}")

    # Partition every subject into counted outcomes that sum to the total, so a
    # subject that was skipped cannot read as one that improved.
    improved = int((E[:, 0] < 1.0).sum())
    worsened = int((E[:, 0] > 1.0).sum())
    flat_eq = len(rows) - improved - worsened
    print(f"\ncompared {len(rows)}, skipped {missing}, total {len(names)}")
    print(f"edge R-G: improved {improved}, worsened {worsened}, unchanged {flat_eq}"
          f"  (sums to {improved + worsened + flat_eq})")

    worst_placebo = float(np.abs(F - 1.0).max())
    print(f"largest placebo excursion: {worst_placebo:.4f} from 1.0", end="  ")
    print("-- PLACEBO CLEAN" if worst_placebo < 0.02
          else "-- PLACEBO MOVED, treat the edge numbers with suspicion")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
