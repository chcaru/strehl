#!/usr/bin/env python3
"""Fit the frame-count scaling of the DEFAULT (pyramid) stack path.

Input is the measured ladder in ``timings.jsonl`` (written by
``timeit_stack.py``).  This script does no timing of its own; it only does
arithmetic on numbers that were measured, so that the scaling claim in the
report is reproducible from the raw record rather than from a paragraph.

Two models are fitted and compared, because the interesting question is not
"is it linear" -- almost anything is linear enough over one decade -- but
*which* variable the cost actually tracks:

  A)  wall = a + b*N                 (cost tracks frame count)
  B)  wall = a + b*ceil(N/W)         (cost tracks the CHUNK LENGTH, i.e. the
                                      number of sequential rounds a fixed
                                      worker pool has to run)

Model B is the one the architecture predicts: ``band_workers()`` in
``crates/strehl-cli/src/merge_cmd.rs`` caps concurrency by a MEMORY budget and
deliberately ignores core count, so at 33 MP the pool is 4 workers wide no
matter how many cores the box has.  Under B the wall clock is a STAIRCASE in N,
flat inside a chunk and stepping every W frames; over a coarse ladder the two
models are indistinguishable, which is exactly why the distinction has to be
argued from the code and the worker line, not from the residuals alone.

Usage:
    python scaling_fit.py --jsonl C:\\dev\\strehl-out\\BUILD-SPEED\\timings.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict


def ols(xs, ys):
    """Ordinary least squares y = a + b*x.  Returns (a, b, r2, residuals)."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    resid = [y - (a + b * x) for x, y in zip(xs, ys)]
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum(r * r for r in resid)
    r2 = 1.0 - sse / sst if sst > 0 else float("nan")
    return a, b, r2, resid


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--workers", type=int, default=4,
                    help="fold worker count printed by the binary (memory plan line)")
    args = ap.parse_args()

    rows = []
    with open(args.jsonl, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    # The ladder rungs: default-path runs on bee-3-cpl at the COMPILED default
    # gate (2.00) with alignment served from the sidecar, so the solve is
    # excluded here -- it is reported separately below.  Grouped by frame count,
    # minimum per rung over both sweep directions (rule 16).
    by_n = defaultdict(list)
    solves = {}
    for r in rows:
        if r.get("rc") != 0:
            continue
        label = r.get("label", "")
        if not (label.startswith("LADDER") or label.startswith("WARM-299-default")):
            continue
        n = r.get("frames")
        if n is None:
            continue
        if r.get("align_how") == "sidecar":
            by_n[n].append((r["wall_s"], r.get("fold_s"), r.get("peak_ws_bytes")))
        elif r.get("align_how") == "solved" and r.get("align_s"):
            prev = solves.get(n)  # keep the cheapest solve seen at this N
            if prev is None or r["align_s"] < prev:
                solves[n] = r["align_s"]
    # the 299-frame solve lives on the COLD run, which is a separate label
    for r in rows:
        if r.get("rc") == 0 and r.get("align_how") == "solved" and r.get("align_s"):
            n = r.get("frames")
            if n is not None and (n not in solves or r["align_s"] < solves[n]):
                solves[n] = r["align_s"]

    ns = sorted(by_n)
    if len(ns) < 3:
        print("not enough rungs in the record; found:", ns)
        return 2

    walls = [min(v[0] for v in by_n[n]) for n in ns]
    folds = [min(v[1] for v in by_n[n] if v[1] is not None) for n in ns]
    W = args.workers
    chunks = [math.ceil(n / W) for n in ns]

    print("=" * 78)
    print("MEASURED LADDER (per-rung minimum over up-sweep and down-sweep)")
    print("=" * 78)
    print(f"{'N':>5} {'reps':>5} {'best wall s':>12} {'best fold s':>12} "
          f"{'ceil(N/%d)' % W:>10} {'fold/chunk':>11} {'wall/N':>8}")
    for n, w, f, c in zip(ns, walls, folds, chunks):
        print(f"{n:>5} {len(by_n[n]):>5} {w:>12.2f} {f:>12.2f} {c:>10} "
              f"{f / c:>11.3f} {w / n:>8.4f}")

    print()
    print("=" * 78)
    print("MODEL A   wall = a + b*N     (cost tracks frame count)")
    print("=" * 78)
    a, b, r2, resid = ols(ns, walls)
    print(f"  intercept a = {a:+.3f} s")
    print(f"  slope     b = {b:.4f} s per frame")
    print(f"  R^2         = {r2:.6f}")
    print(f"  residuals   = {', '.join('%+.2f' % r for r in resid)} s")
    print(f"  max |resid| = {max(abs(r) for r in resid):.2f} s "
          f"({100 * max(abs(r) / w for r, w in zip(resid, walls)):.1f}% of its rung)")

    print()
    print("=" * 78)
    print(f"MODEL B   wall = a + b*ceil(N/{W})   (cost tracks CHUNK LENGTH)")
    print("=" * 78)
    a2, b2, r22, resid2 = ols(chunks, walls)
    print(f"  intercept a = {a2:+.3f} s")
    print(f"  slope     b = {b2:.4f} s per chunk round")
    print(f"  R^2         = {r22:.6f}")
    print(f"  residuals   = {', '.join('%+.2f' % r for r in resid2)} s")

    print()
    print("=" * 78)
    print("ALIGNMENT SOLVE (cache miss), reported separately -- excluded above")
    print("=" * 78)
    if solves:
        sn = sorted(solves)
        print(f"{'N':>5} {'solve s':>10} {'s/frame':>9} {'vs N=%d scaled' % sn[0]:>15}")
        base_n, base_s = sn[0], solves[sn[0]]
        for n in sn:
            lin = base_s * n / base_n
            print(f"{n:>5} {solves[n]:>10.2f} {solves[n] / n:>9.4f} "
                  f"{solves[n] / lin:>14.2f}x")
        # log-log slope
        xs = [math.log(n) for n in sn]
        ys = [math.log(solves[n]) for n in sn]
        _, p, r2s, _ = ols(xs, ys)
        print(f"  log-log fit: solve ~ N^{p:.3f}   (R^2 {r2s:.4f})")
        print("  exponent > 1 means the solve is SUPERLINEAR in frame count.")
    else:
        print("  no solve rungs found in the record")

    print()
    print("=" * 78)
    print("PEAK WORKING SET (fold-only runs, i.e. alignment served from sidecar)")
    print("=" * 78)
    for n in ns:
        peaks = [v[2] for v in by_n[n] if v[2]]
        if peaks:
            print(f"  N={n:>4}  peak WS {min(peaks) / 2**30:.2f} - "
                  f"{max(peaks) / 2**30:.2f} GB over {len(peaks)} run(s)")
    allpk = [v[2] for n in ns for v in by_n[n] if v[2]]
    if allpk:
        lo, hi = min(allpk) / 2**30, max(allpk) / 2**30
        print(f"  across a {ns[0]}..{ns[-1]} frame range ({ns[-1] / ns[0]:.1f}x more "
              f"frames): {lo:.2f} - {hi:.2f} GB, a spread of {100 * (hi / lo - 1):.1f}%.")
        print("  Flat in N is the signature of O(workers), not O(frames).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
