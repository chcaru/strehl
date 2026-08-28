#!/usr/bin/env python3
"""Corpus survey driver: run stage A over every delivered master, in parallel.

Partitioning rule (the brief is explicit, and AGENTS rule 8 says the same):
a skipped item must never read as a passed one.  This driver therefore emits
one line per subject with exactly one of the outcomes

    OK / NO-RAW / STAGEA-FAIL

and asserts at the end that the three counts sum to the number of subjects
found.  Nothing is silently dropped.

Usage:  python survey.py --maxframes 40 --jobs 4 [--only a,b,c]
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


def subjects():
    return sorted(f[:-5] for f in os.listdir(ora.MASTERS) if f.endswith(".tiff"))


def run_one(subj, maxframes, force):
    dst = os.path.join(ora.OUT, "stageA", subj + ".npz")
    if os.path.exists(dst) and not force:
        return subj, "OK", "cached"
    try:
        ora.frames_of(subj)
    except Exception as e:  # no raw bracket on disk for this master
        return subj, "NO-RAW", str(e)[:120]
    cmd = [sys.executable, os.path.join(HERE, "stageA.py"), subj,
           "--maxframes", str(maxframes)]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True)
    dt = time.time() - t0
    if p.returncode != 0 or not os.path.exists(dst):
        tail = (p.stderr or p.stdout).strip().splitlines()
        return subj, "STAGEA-FAIL", " | ".join(tail[-3:])[:300]
    return subj, "OK", f"{dt:.0f}s"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--maxframes", type=int, default=40)
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--only", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    subs = subjects()
    if args.only:
        want = set(args.only.split(","))
        subs = [s for s in subs if s in want]
    print(f"survey: {len(subs)} subjects, maxframes={args.maxframes}, "
          f"jobs={args.jobs}", flush=True)

    res = {}
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as ex:
        futs = {ex.submit(run_one, s, args.maxframes, args.force): s
                for s in subs}
        done = 0
        for f in cf.as_completed(futs):
            subj, status, note = f.result()
            res[subj] = (status, note)
            done += 1
            print(f"  [{done}/{len(subs)}] {status:12s} {subj}  {note}",
                  flush=True)

    counts = {}
    for s, (st, _) in res.items():
        counts[st] = counts.get(st, 0) + 1
    print("\n-- outcome partition --")
    tot = 0
    for k in sorted(counts):
        print(f"  {k:12s} {counts[k]}")
        tot += counts[k]
    print(f"  {'TOTAL':12s} {tot}")
    assert tot == len(subs), f"partition {tot} != {len(subs)} subjects"
    print(f"partition check OK: {tot} == {len(subs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
