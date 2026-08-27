#!/usr/bin/env python3
"""Half-stack selection coherence: does the merge choose differently in two
independent halves of the same stack, and does that rise with N?

WHY THIS SHAPE.  The prediction under test is that the shipped weighting
over-selects on a quantity that is partly noise, so its per-pixel frame choice
is not reproducible across two independent halves of the same stack.  The
direct form of that measurement -- read the merge's index map for each half and
count disagreements -- IS NOT AVAILABLE: `--index-map` is refused under the
pyramid backend, and the pyramid is what ships.  So the choice is tested
behaviourally, through what the two halves actually render.

COVERAGE IS HELD CONSTANT AND ONLY N VARIES.  A naive depth ladder (first 32
frames against all 204) changes focus coverage at the same time as N, and then
any difference is coverage, not dilution.  Every set here spans the FULL depth
and differs only in how densely it samples it:

    N=34   every 6th frame, halves = every 12th from 0 and from 6
    N=102  every 2nd frame, halves = every 4th from 0 and from 2
    N=204  every frame,     halves = even and odd

Both halves of a set therefore span the same focus range as each other and as
every other set.  What changes across sets is the number of near-tied frames
competing at each pixel, which is exactly the quantity the dilution hypothesis
is about.

THE CONFOUND, AND WHICH WAY IT PUSHES.  A half of the N=34 set samples focus
every 12 frames, so at some pixels its best frame is genuinely a different
depth from the other half's best frame -- a SCENE reason to disagree that is
strongest at LOW N.  That biases the ladder against the prediction, so a
disagreement that still rises with N is a conservative reading.

SUBJECT CHOICE IS THIS LANE'S CONTRIBUTION.  `flower-bud-alone-cpl` was measured
in V-DRIFT section 4 at 0.715 px of total corner drift, flat across depth.
Running the ladder there tests dilution on a subject where alignment error is
excluded by measurement rather than by assumption.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

BIN = Path(r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe")
SHA_PREFIX = "44C2F2CD2E5B2894"
ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
SCRATCH = ROOT / "halfscratch"

# (set name, stride over the source frames)  -- every set spans the full depth.
SETS = [("n34", 6), ("n102", 2), ("n204", 1)]


def check_binary() -> str:
    h = hashlib.sha256(BIN.read_bytes()).hexdigest().upper()
    if not h.startswith(SHA_PREFIX):
        raise SystemExit(f"WRONG BINARY: sha256 {h[:16]} != {SHA_PREFIX}")
    return h


def build(frames: list[Path], dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in frames:
        shutil.copy2(f, dst / f.name)


def merge(src: Path, out: Path, tag: str) -> dict:
    cache = SCRATCH / f"cache-{tag}"
    cache.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "STREHL_CACHE_DIR": str(cache)}
    log = out.with_suffix(".log")
    t0 = time.time()
    p = subprocess.run([str(BIN), "stack", str(src), "--out", str(out),
                        "--linear-srgb", "--demosaic"],
                       capture_output=True, text=True, env=env)
    wall = time.time() - t0
    txt = p.stdout + p.stderr
    log.write_text(txt, encoding="utf-8")
    shutil.rmtree(cache, ignore_errors=True)
    m = re.search(r"field of view scaled to ([0-9.]+)", txt)
    d = re.search(r"held-out error ([0-9.]+) px", txt)
    return {"tag": tag, "rc": p.returncode, "wall_s": round(wall, 1),
            "k": float(m.group(1)) if m else None,
            "heldout": float(d.group(1)) if d else None,
            "out": str(out)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"D:\personal\macro\flower-bud-alone-cpl")
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--sets", nargs="*", default=[s for s, _ in SETS])
    a = ap.parse_args()

    print(f"binary sha256 {check_binary()[:16]}... OK")
    src = sorted(Path(a.dir).glob("*.ARW"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (ROOT / "half").mkdir(parents=True, exist_ok=True)
    jl = ROOT / f"half-{a.subject}.jsonl"

    with jl.open("a", encoding="utf-8") as fh:
        for name, stride in SETS:
            if name not in a.sets:
                continue
            base = src[::stride]
            for half, off in (("A", 0), ("B", 1)):
                frames = base[off::2]
                tag = f"{a.subject}-{name}-{half}"
                work = SCRATCH / tag
                print(f"  {tag}: {len(frames)} frames "
                      f"({frames[0].stem}..{frames[-1].stem}) copying...", flush=True)
                build(frames, work)
                r = merge(work, ROOT / "half" / f"{tag}.tif", tag)
                shutil.rmtree(work, ignore_errors=True)
                r.update(set=name, half=half, n_half=len(frames),
                         n_set=len(base), stride=stride, subject=a.subject,
                         first=frames[0].name, last=frames[-1].name)
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                print(f"    rc={r['rc']} {r['wall_s']}s k={r['k']} "
                      f"heldout={r['heldout']}", flush=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
