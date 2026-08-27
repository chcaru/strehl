#!/usr/bin/env python3
"""Control the confidence map's cloud-width confound by measuring HEADROOM.

The confidence map reports how centrally the output sits inside the cloud of
aligned observations.  That cloud is not a fixed yardstick: as N grows the stack
contributes more badly-defocused frames, the cloud widens, and an output that
elects one frame sits further out on the wider cloud -- reading LOWER -- without
the merge having changed its behaviour at all.  So a flat or gently falling
depth curve cannot by itself be read as "the merge commits just as hard".

The fix is to stop reading the absolute level and read the distance between two
arms measured on the SAME stack at the SAME N:

    headroom(N) = confidence(shipped default) - confidence(hard-max)

`--pyramid-select hard-max` is the textbook argmax -- the most committed merge
the binary can produce.  Both arms see the identical cloud at a given N, so
cloud width cancels in the difference.  Headroom is then "how much less
committed the shipped weighting is than a pure winner-take-all, in the units of
this scene's own cloud".

THE PREDICTION.  Dilution says the shipped weighting's winner-share falls toward
an average as N grows while argmax by construction stays fully committed.  That
requires headroom to GROW with N.  A flat headroom says the shipped weighting is
no less decisive on a deep stack than on a shallow one.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import tifffile

from halfstack import BIN, ROOT, build, check_binary

SCRATCH = ROOT / "headscratch"
ARMS = [("default", []), ("hardmax", ["--pyramid-select", "hard-max"])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=r"D:\personal\macro\flower-bud-alone-cpl")
    ap.add_argument("--subject", default="flower")
    ap.add_argument("--strides", type=int, nargs="*", default=[12, 1])
    a = ap.parse_args()

    # Per-subject scratch.  Two instances of THIS script running concurrently on
    # different subjects share a scratch root otherwise, and whichever finishes
    # first removes the other's frames mid-merge.  That is exactly what happened
    # on the first bee run: "decode failed for ...DSC00023.ARW: The system cannot
    # find the file specified" after the default arm of the same N had succeeded.
    global SCRATCH
    SCRATCH = ROOT / f"headscratch-{a.subject}"

    print(f"binary sha256 {check_binary()[:16]}... OK")
    src = sorted(Path(a.dir).glob("*.ARW"))
    out = ROOT / "head"
    out.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    jl = ROOT / f"head-{a.subject}.jsonl"

    print(f"{'N':>5s} {'arm':>9s} {'mean':>8s} {'frac>500':>9s}   headroom")
    with jl.open("a", encoding="utf-8") as fh:
        for S in a.strides:
            frames = src[::S]
            work = SCRATCH / f"{a.subject}-{len(frames)}"
            build(frames, work)
            vals = {}
            for arm, extra in ARMS:
                tag = f"{a.subject}-h{len(frames)}-{arm}"
                cache = SCRATCH / f"cache-{tag}"
                cache.mkdir(parents=True, exist_ok=True)
                cmap = out / f"{tag}-conf.tif"
                p = subprocess.run(
                    [str(BIN), "stack", str(work), "--out", str(out / f"{tag}.tif"),
                     "--linear-srgb", "--demosaic", "--confidence-map", str(cmap)] + extra,
                    capture_output=True, text=True,
                    env={**os.environ, "STREHL_CACHE_DIR": str(cache)})
                (out / f"{tag}.log").write_text(p.stdout + p.stderr, encoding="utf-8")
                shutil.rmtree(cache, ignore_errors=True)
                if p.returncode != 0 or not cmap.exists():
                    print(f"{len(frames):5d} {arm:>9s}  FAILED rc={p.returncode}")
                    continue
                c = tifffile.imread(str(cmap)).astype(np.float64)
                vals[arm] = {"mean": float(c.mean()),
                             "frac_hi": float((c > 500).mean())}
                print(f"{len(frames):5d} {arm:>9s} {vals[arm]['mean']:8.1f} "
                      f"{100*vals[arm]['frac_hi']:8.2f}%")
            shutil.rmtree(work, ignore_errors=True)
            if len(vals) == 2:
                hr = vals["default"]["mean"] - vals["hardmax"]["mean"]
                r = {"subject": a.subject, "n": len(frames), "stride": S,
                     "default": vals["default"]["mean"],
                     "hardmax": vals["hardmax"]["mean"], "headroom": hr,
                     "frac_default": vals["default"]["frac_hi"],
                     "frac_hardmax": vals["hardmax"]["frac_hi"]}
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                print(f"{'':5s} {'':9s} {'':8s} {'':9s}   HEADROOM {hr:+.1f}")
    shutil.rmtree(SCRATCH, ignore_errors=True)

    rows = [json.loads(l) for l in jl.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [r for r in rows if r["subject"] == a.subject]
    if len(rows) >= 2:
        lo, hi = min(rows, key=lambda r: r["n"]), max(rows, key=lambda r: r["n"])
        print(f"\n{a.subject}: headroom N={lo['n']} -> N={hi['n']}: "
              f"{lo['headroom']:.1f} -> {hi['headroom']:.1f} "
              f"({hi['headroom']/lo['headroom']:.2f}x)")
        print("Dilution requires this to GROW with N.  Cloud width cancels in the\n"
              "difference, so this is the cloud-width-controlled reading.")


if __name__ == "__main__":
    main()
