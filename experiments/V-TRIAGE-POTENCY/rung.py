#!/usr/bin/env python3
"""Run BUILD-TRIAGE's UNMODIFIED instrument against a scratch tree.

Nothing under experiments/BUILD-TRIAGE/ is edited or copied: compare.py,
tri.py and triage.py are imported as shipped and only the module-level paths
tri.OUT / tri.LIN / compare.FRAMEDIR are redirected, so the code under test is
byte-for-byte the code that produced the 26-subject table.

The master this run actually reads is hashed and fingerprinted HERE, in the
process that reads it, immediately before compare.main() opens it -- a plant
that failed to land cannot then be reported as a green result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

BT = r"C:\dev\blog\death-of-software\projects\strehl\experiments\BUILD-TRIAGE"
sys.path.insert(0, BT)
import tri  # noqa: E402

FP_Y, FP_X, FP_N = 2200, 3400, 512


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("subject")
    ap.add_argument("--root", required=True, help="per-rung OUT tree")
    ap.add_argument("--frames", required=True, help="shared single-frame renders")
    args = ap.parse_args()

    tri.OUT = args.root
    tri.LIN = os.path.join(args.root, "lin")
    import compare  # noqa: E402  (after tri.OUT is redirected)
    import triage   # noqa: E402
    compare.FRAMEDIR = args.frames
    assert compare.tri is tri and triage.tri is tri, "module identity broke"
    assert tri.OUT == args.root and compare.FRAMEDIR == args.frames

    mp = os.path.join(tri.LIN, args.subject + ".tiff")
    print("=" * 100)
    print(f"MASTER THIS RUN READS: {mp}")
    print(f"  sha256      {sha256(mp)}")
    print(f"  mtime       {time.ctime(os.path.getmtime(mp))}")
    a = tri.load16(mp)
    y = tri.luma(a)
    fp = tri.edge_slope(np.ascontiguousarray(y[FP_Y:FP_Y + FP_N, FP_X:FP_X + FP_N]))
    print(f"  fingerprint edge_slope(fixed 512 tile) = {fp:.4f} DN/px")
    del a, y
    print(f"  frames dir  {compare.FRAMEDIR}")
    print("=" * 100)

    sys.argv = ["compare.py", args.subject, "--keep"]
    rc = compare.main()
    if rc != 0:
        raise SystemExit(f"compare.main() returned {rc}")

    ev = triage.load(args.subject)
    r = triage.classify(args.subject, ev)
    cj = os.path.join(tri.OUT, "compare", args.subject + ".json")
    with open(cj, encoding="utf-8") as fh:
        cmp_ = json.load(fh)
    print()
    print("-" * 100)
    print(f"VERDICT  {args.subject}  ->  {r['verdict']}")
    print(f"  why      {' | '.join(r['why'])}")
    print(f"  evidence {json.dumps(r['evidence'])}")
    print("  per-site blur_equiv_px / ratio / merge DN/px / frame_corr DN/px:")
    for k, v in cmp_["sites"].items():
        e = v["edge"]
        print(f"    {k:<12s} blur={e['blur_equiv_px']:.3f} ratio={e['ratio']:.4f} "
              f"merge={e['merge_dnpx']:.1f} frame_corr={e['frame_corr_dnpx']:.1f} "
              f"cost={e['gather_cost']:.4f} noise m/f={e['noise_merge_dn']:.1f}/"
              f"{e['noise_frame_dn']:.1f} caution={v.get('caution')}")
    print("-" * 100)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
