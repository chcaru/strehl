#!/usr/bin/env python3
"""Wall clock against MACHINE LOAD for the 299-frame reference workload.

Every timing in this experiment was taken on a build box shared with a dozen
other agents.  Rather than pick a number and apologise for the box in a
footnote, ``timeit_stack.py`` recorded the machine's busy fraction beside every
run (sampled with GetSystemTimes across the child's lifetime) and the child's
own CPU-seconds (GetProcessTimes).  This script turns those into the table the
report quotes.

The point it makes is not subtle: identical work, identical output BYTES, and a
2x spread in wall clock that tracks the busy fraction monotonically.  A single
wall-clock number for this workload on this box is not a property of the
software.  What IS a property of the software is the shape -- 4 fold workers,
~500 CPU-seconds of arithmetic, 5.7 GB resident -- and those are stable.

Usage:
    python load_response.py --jsonl C:\\dev\\strehl-out\\BUILD-SPEED\\timings.jsonl
"""

from __future__ import annotations

import argparse
import json


def ols(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    sst = sum((y - my) ** 2 for y in ys)
    sse = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    return a, b, (1.0 - sse / sst if sst else float("nan"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.jsonl, encoding="utf-8") if l.strip()]
    runs = [r for r in rows
            if r.get("rc") == 0 and r.get("frames") == 299
            and r.get("align_how") == "sidecar"]
    runs.sort(key=lambda r: (r.get("gate"), r["wall_s"]))

    print("=" * 100)
    print("299 FRAMES, WARM (alignment from sidecar), pyramid backend -- wall clock vs machine load")
    print("=" * 100)
    print(f"{'gate':>5} {'busy%':>6} {'wall s':>8} {'fold s':>8} {'cpu s':>7} "
          f"{'threads':>8} {'peakWS GB':>10} {'MB/s':>7} {'s/frame':>8}")
    for r in runs:
        raw_mb = r["raw_bytes"] / 1e6
        thr = r["proc_cpu_s"] / r["wall_s"]
        print(f"{r['gate']:>5} {100 * r['machine_busy_frac']:>6.0f} {r['wall_s']:>8.2f} "
              f"{r['fold_s']:>8.1f} {r['proc_cpu_s']:>7.1f} {thr:>8.2f} "
              f"{r['peak_ws_bytes'] / 2**30:>10.2f} {raw_mb / r['wall_s']:>7.1f} "
              f"{r['wall_s'] / 299:>8.4f}")

    busy = [r["machine_busy_frac"] for r in runs]
    wall = [r["wall_s"] for r in runs]
    cpu = [r["proc_cpu_s"] for r in runs]
    a, b, r2 = ols(busy, wall)
    print()
    print(f"  wall = {a:.1f} + {b:.1f} * busy_fraction      R^2 = {r2:.4f}")
    print(f"  observed range: {min(wall):.2f} s at {100 * busy[wall.index(min(wall))]:.0f}% busy "
          f"-> {max(wall):.2f} s at {100 * busy[wall.index(max(wall))]:.0f}% busy "
          f"({max(wall) / min(wall):.2f}x)")
    ac, bc, r2c = ols(busy, cpu)
    print(f"  cpu_s = {ac:.0f} + {bc:.0f} * busy_fraction   R^2 = {r2c:.4f}")
    print(f"  CPU-seconds for IDENTICAL work range {min(cpu):.0f} -> {max(cpu):.0f} "
          f"({max(cpu) / min(cpu):.2f}x): contended threads accrue CPU time while")
    print("  they stall, so CPU-seconds are NOT a load-invariant measure of the work.")

    print()
    print("  Output bytes by gate (determinism control):")
    seen = {}
    for r in runs:
        seen.setdefault(r["gate"], set()).add(r.get("out_sha256", "?")[:16])
    for gate, hashes in sorted(seen.items()):
        n = sum(1 for r in runs if r["gate"] == gate)
        print(f"    gate {gate}: {n} runs -> {len(hashes)} distinct sha256 "
              f"{sorted(hashes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
