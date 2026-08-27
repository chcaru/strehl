#!/usr/bin/env python3
"""The confound control: hold the focus separation between partner frames fixed
at ONE frame while N varies.

WHY THIS EXISTS.  The first ladder built its two halves by interleaving a
subsampled set, which locks the partner separation to the subsampling stride:
at N=35 the two halves' frames sit 6 apart in focus, at N=205 they sit 1 apart.
So a pixel can disagree between the halves for a reason that has nothing to do
with the merge -- at coarse sampling the nearest in-focus frame available to
half A is genuinely a different depth from the one available to half B.  That
inflates the LOW-N end, which is the same direction as a falling curve, so a
fall measured on that ladder cannot distinguish "no rise with N" from "a real
rise masked by the confound".  This ladder removes the ambiguity by
construction instead of correcting for it afterwards.

THE DESIGN.  For half-size M, take

    A = src[0::S]        B = src[1::S]        S = len(src) // M

Both halves span the full depth, both sample it with the same stride, they are
disjoint, and every partner pair is adjacent in focus AT EVERY M.  The only
quantity that changes across the ladder is how many frames compete at each
pixel, which is precisely what the dilution prediction is about.

The residual asymmetry is that a half at large S is internally sparse, which
affects both halves equally and is the same at both ends of the comparison as
the scene, so it cannot manufacture a trend in N by itself.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import halfstack
from halfstack import ROOT, build, check_binary, merge

# Own scratch root: this runs concurrently with halfstack.py, which removes its
# own scratch tree wholesale when it finishes.
SCRATCH = ROOT / "offsetscratch"
halfstack.SCRATCH = SCRATCH


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"D:\personal\macro\flower-bud-alone-cpl")
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--strides", type=int, nargs="*", default=[12, 4, 2])
    a = ap.parse_args()

    print(f"binary sha256 {check_binary()[:16]}... OK")
    src = sorted(Path(a.dir).glob("*.ARW"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (ROOT / "half").mkdir(parents=True, exist_ok=True)
    jl = ROOT / f"half-{a.subject}.jsonl"
    done = {json.loads(l)["tag"] for l in jl.read_text(encoding="utf-8").splitlines()
            if l.strip()} if jl.exists() else set()

    with jl.open("a", encoding="utf-8") as fh:
        for S in a.strides:
            for half, off in (("A", 0), ("B", 1)):
                frames = src[off::S]
                tag = f"{a.subject}-s{S}-{half}"
                if tag in done:
                    print(f"  {tag}: already on disk, skipping")
                    continue
                work = SCRATCH / tag
                print(f"  {tag}: {len(frames)} frames "
                      f"({frames[0].stem}..{frames[-1].stem}) copying...", flush=True)
                build(frames, work)
                r = merge(work, ROOT / "half" / f"{tag}.tif", tag)
                shutil.rmtree(work, ignore_errors=True)
                r.update(set=f"s{S}", half=half, n_half=len(frames),
                         n_set=len(src[::S]) + len(src[1::S]), stride=S,
                         subject=a.subject, sep=1,
                         first=frames[0].name, last=frames[-1].name)
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                print(f"    rc={r['rc']} {r['wall_s']}s k={r['k']}", flush=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
