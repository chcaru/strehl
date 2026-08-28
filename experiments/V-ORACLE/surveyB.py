#!/usr/bin/env python3
"""Run stage B (the merge arm) over every subject that has a stage A result.

Same partitioning rule as survey.py: every subject lands in exactly one counted
outcome and the counts are asserted to sum.

Usage:  python surveyB.py [--jobs 5]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def run_one(subj, force):
    dst = os.path.join(ora.OUT, "stageB", subj + ".npz")
    if os.path.exists(dst) and not force:
        return subj, "OK", "cached"
    if not os.path.exists(os.path.join(ora.OUT, "stageA", subj + ".npz")):
        return subj, "NO-STAGEA", "stage A never produced a result"
    t0 = time.time()
    p = subprocess.run([sys.executable, os.path.join(HERE, "stageB.py"), subj],
                       capture_output=True, text=True)
    if p.returncode != 0 or not os.path.exists(dst):
        tail = (p.stderr or p.stdout).strip().splitlines()
        return subj, "STAGEB-FAIL", " | ".join(tail[-2:])[:250]
    warn = "WARN-RESIDUAL-SHIFT" if "WARNING residual" in p.stdout else ""
    return subj, "OK", f"{time.time() - t0:.0f}s {warn}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=5)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    subs = sorted(f[:-5] for f in os.listdir(ora.MASTERS) if f.endswith(".tiff"))
    print(f"stage B sweep: {len(subs)} subjects, jobs={args.jobs}", flush=True)
    res = {}
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(run_one, s, args.force): s for s in subs}
        done = 0
        for f in cf.as_completed(futs):
            s, st, note = f.result()
            res[s] = (st, note)
            done += 1
            print(f"  [{done}/{len(subs)}] {st:12s} {s}  {note}", flush=True)
    counts = {}
    for s, (st, _) in res.items():
        counts[st] = counts.get(st, 0) + 1
    print("\n-- outcome partition --")
    tot = 0
    for k in sorted(counts):
        print(f"  {k:12s} {counts[k]}")
        tot += counts[k]
    print(f"  {'TOTAL':12s} {tot}")
    assert tot == len(subs), f"partition {tot} != {len(subs)}"
    print(f"partition check OK: {tot} == {len(subs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
