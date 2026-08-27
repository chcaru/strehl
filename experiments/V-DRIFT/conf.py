#!/usr/bin/env python3
"""Does the shipped merge stop committing as the stack gets deeper?

The dilution hypothesis says the pyramid weights each frame's band coefficient
by (snr_i/SNR_REF)^p normalised over frames, so as N grows the number of
near-tied frames grows and the winner's SHARE falls toward a plain average.
Testing that wants the merge's per-pixel decisiveness, and `--index-map` cannot
supply it: it is refused under the pyramid backend, because the pyramid elects
per band coefficient rather than per pixel, so no single frame index owns an
output pixel.

`--confidence-map` is the artifact that does exist on the default backend, and
the CLI help states its polarity outright:

    "how centrally the output sits inside the cloud of aligned observations,
     in milli-units.  Low is good ...  Electing a frame puts the output at an
     extreme of the observations and reads near 0.  Averaging frames that
     disagreed puts it dead centre and reads near 1000, which is what the
     veiled-detail failure looks like from the inside."

So the hypothesis has a direct prediction on this number: mean confidence rises
toward 1000 with N.  A flat curve says the merge commits just as hard on 205
frames as on 17, and the depth collapse is not the winner's share diluting.

WHY THIS IS ALSO THE REQUIRED COMPANION STATISTIC.  Every other number in this
lane is a two-half coherence measure, and the standing instruction is that a
coherence statistic must be paired with one that coherence cannot move.  This
is computed from the cloud of frames behind a single render.  There is no half
split anywhere in it, so nothing about agreement between halves can shift it.

COVERAGE IS HELD CONSTANT.  Each rung takes src[::S] -- the whole depth,
sampled more or less densely -- so the focus range is identical at every N and
only the count of competing frames changes.  Taking the first N frames instead
would change the focus range at the same time and confound the two.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np
import tifffile

from halfstack import BIN, ROOT, build, check_binary

SCRATCH = ROOT / "confscratch"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"D:\personal\macro\flower-bud-alone-cpl")
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--strides", type=int, nargs="*", default=[12, 4, 2, 1])
    a = ap.parse_args()

    print(f"binary sha256 {check_binary()[:16]}... OK")
    src = sorted(Path(a.dir).glob("*.ARW"))
    SCRATCH.mkdir(parents=True, exist_ok=True)
    out = ROOT / "conf"
    out.mkdir(parents=True, exist_ok=True)
    jl = ROOT / f"conf-{a.subject}.jsonl"

    print(f"{'N':>5s} {'k':>7s} {'wall':>7s} {'mean':>8s} {'median':>8s} "
          f"{'p90':>8s} {'frac>500':>9s}")
    with jl.open("a", encoding="utf-8") as fh:
        for S in a.strides:
            frames = src[::S]
            tag = f"{a.subject}-c{len(frames)}"
            work = SCRATCH / tag
            build(frames, work)
            cache = SCRATCH / f"cache-{tag}"
            cache.mkdir(parents=True, exist_ok=True)
            cmap = out / f"{tag}-conf.tif"
            t0 = time.time()
            p = subprocess.run(
                [str(BIN), "stack", str(work), "--out", str(out / f"{tag}.tif"),
                 "--linear-srgb", "--demosaic", "--confidence-map", str(cmap)],
                capture_output=True, text=True,
                env={**os.environ, "STREHL_CACHE_DIR": str(cache)})
            wall = time.time() - t0
            txt = p.stdout + p.stderr
            (out / f"{tag}.log").write_text(txt, encoding="utf-8")
            shutil.rmtree(work, ignore_errors=True)
            shutil.rmtree(cache, ignore_errors=True)
            if p.returncode != 0 or not cmap.exists():
                print(f"{len(frames):5d}  FAILED rc={p.returncode}: "
                      f"{txt.strip().splitlines()[-1][:90] if txt.strip() else ''}")
                continue
            c = tifffile.imread(str(cmap)).astype(np.float64)
            m = re.search(r"field of view scaled to ([0-9.]+)", txt)
            r = {"subject": a.subject, "n": len(frames), "stride": S,
                 "k": float(m.group(1)) if m else None, "wall_s": round(wall, 1),
                 "mean": float(c.mean()), "median": float(np.median(c)),
                 "p90": float(np.percentile(c, 90)),
                 "frac_hi": float((c > 500).mean()), "shape": list(c.shape),
                 "map": str(cmap)}
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(f"{r['n']:5d} {r['k']:7.4f} {r['wall_s']:7.1f} {r['mean']:8.1f} "
                  f"{r['median']:8.1f} {r['p90']:8.1f} {100*r['frac_hi']:8.2f}%")
    shutil.rmtree(SCRATCH, ignore_errors=True)


if __name__ == "__main__":
    main()
