#!/usr/bin/env python3
"""Does the section 12 headroom survive the pin -> HEAD binary change?

`bindelta.py` shows the binary change moves mean confidence by +0.9 to +10.0
units, and N-DEPENDENTLY: +3.5 at N=18 against +10.0 at N=103 on the same
subject.  Section 7's whole-field depth effect on flower was +6.6 units, so the
binary change alone is larger than the effect that section measured.  That
contaminates any statistic read as an absolute confidence LEVEL across depth.

Headroom might not be contaminated, because it is a DIFFERENCE between two arms
rendered by the SAME binary.  If the binary change shifts both arms equally it
cancels exactly.  That is a hypothesis, not a result, and the difference between
those two is the whole point of this project, so it is measured here: render
both arms with the HEAD binary and compare the headroom to the pin's.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402
from binsame import NEW, SCRATCH, sha  # noqa: E402
from halfstack import ROOT, build  # noqa: E402

SRC = {"flower": Path(r"D:\personal\macro\flower-bud-alone-cpl"),
       "bee": Path(r"D:\personal\macro\bee-3-cpl")}
# Pin-measured headroom, V-SELECT section 7, for the same (subject, stride).
PIN_HEADROOM = {("flower", 12): 50.93, ("bee", 12): 55.51}
ARMS = {"default": [], "hardmax": ["--pyramid-select", "hard-max"]}


def render(subject: str, stride: int, arm: str) -> Path:
    frames = sorted(SRC[subject].glob("*.ARW"))[::stride]
    tag = f"{subject}-s{stride}-n{len(frames)}-{arm}-head"
    out = SCRATCH / f"{tag}.tif"
    cf = out.with_name(out.stem + "-conf.tif")
    if cf.exists():
        return cf
    d = SCRATCH / f"src-{tag}"
    build(frames, d)
    cache = SCRATCH / f"cache-{tag}"
    cache.mkdir(parents=True, exist_ok=True)
    cmd = ([str(NEW), "stack", str(d), "--out", str(out), "--linear-srgb",
            "--demosaic", "--confidence-map", str(cf)] + ARMS[arm])
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True,
                       env={**os.environ, "STREHL_CACHE_DIR": str(cache)})
    out.with_suffix(".log").write_text(p.stdout + p.stderr, encoding="utf-8")
    shutil.rmtree(cache, ignore_errors=True)
    shutil.rmtree(d, ignore_errors=True)
    if p.returncode != 0 or not cf.exists():
        raise SystemExit(f"{tag} failed:\n{p.stdout[-1500:]}{p.stderr[-1500:]}")
    print(f"  rendered {tag} in {time.time() - t0:.0f}s")
    return cf


def mean_conf(p: Path) -> float:
    a = tri.load16(str(p)).astype(np.float64)
    return float((a[..., 0] if a.ndim == 3 else a).mean())


def main() -> int:
    print(f"HEAD binary sha256 {sha(NEW)[:16]}\n")
    rows = []
    for (subject, stride), pin_head in PIN_HEADROOM.items():
        d = mean_conf(render(subject, stride, "default"))
        h = mean_conf(render(subject, stride, "hardmax"))
        got = d - h
        rows.append({"subject": subject, "stride": stride, "default": d,
                     "hardmax": h, "headroom_head": got,
                     "headroom_pin": pin_head, "delta": got - pin_head})
        print(f"{subject:8s} stride {stride:2d}  default {d:7.1f}  hard-max {h:7.1f}"
              f"  headroom {got:6.2f}  (pin {pin_head:6.2f}, "
              f"delta {got - pin_head:+.2f})")

    (ROOT / "headroom-head.json").write_text(json.dumps(rows, indent=1),
                                             encoding="utf-8")
    worst = max(abs(r["delta"]) for r in rows)
    print(f"\nlargest headroom shift from pin to HEAD: {worst:.2f} confidence units")
    print("compare: the binary shifts the mean LEVEL by up to 10.0 units, and the")
    print("section 7 whole-field depth effect it would corrupt is 6.6 / 11.0 units.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
