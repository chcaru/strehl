#!/usr/bin/env python3
"""Does the merge at HEAD still behave like the merge at the acceptance pin?

WHY.  Every number in V-SELECT.md and V-DRIFT.md was measured with the pinned
acceptance binary `9b05d0b7` (sha256 44C2F2CD2E5B2894).  The orchestrator has
since ruled that anything measured at or before that pin is stale by 13 commits,
and the merge path is NOT untouched: `git diff 9b05d0b7..HEAD` over
`pyramid.rs` and `merge.rs` is 438 insertions and 11 deletions, and two of the
deletions are in the election arithmetic --

    Gate::tolerance()   threshold * SQRT_2 * FOCUS_NOISE_SD
                     -> threshold * SQRT_2 * self.noise_sd
    fold              gain.beta(k)
                     -> Self::beta_for(&self.gain, frame_beta, k)

Reading the source says both are default-off: `Gate::new` still fills
`FOCUS_NOISE_SD`, and `beta_for` falls through to `gain.beta(k)` when
`frame_beta` is `None`.  READING IS NOT MEASURING.  A default-preserving change
is a claim about behaviour and it is cheap to test directly, so this script
tests it: same frames, same flags, both binaries, compare the bytes.

WHAT A PASS MEANS AND WHAT IT DOES NOT.  Byte-identical output on these
configurations means the merge's arithmetic did not move for them, so the
existing measurements describe HEAD's behaviour too and do not need re-running.
It does NOT mean the binaries are interchangeable in general -- only that on
these stacks, at these depths, with these flags, they agree.  Depth is varied
because an N-dependent change is exactly the kind this lane would care about and
exactly the kind a single shallow render would miss.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from halfstack import ROOT, SHA_PREFIX, build  # noqa: E402

PIN = Path(r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe")
NEW = HERE.parent.parent / "target" / "release" / "strehl.exe"
SCRATCH = ROOT / "binsame"
SRC = {"flower": Path(r"D:\personal\macro\flower-bud-alone-cpl"),
       "bee": Path(r"D:\personal\macro\bee-3-cpl")}
# Shallow and deep, because the question is whether anything became N-dependent.
CASES = [("flower", 12), ("flower", 2), ("bee", 12)]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def run(binary: Path, src: Path, out: Path, tag: str, conf: bool) -> float:
    cache = SCRATCH / f"cache-{tag}"
    cache.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "STREHL_CACHE_DIR": str(cache)}
    cmd = [str(binary), "stack", str(src), "--out", str(out),
           "--linear-srgb", "--demosaic"]
    if conf:
        cmd += ["--confidence-map", str(out.with_name(out.stem + "-conf.tif"))]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    wall = time.time() - t0
    out.with_suffix(".log").write_text(p.stdout + p.stderr, encoding="utf-8")
    shutil.rmtree(cache, ignore_errors=True)
    if p.returncode != 0 or not out.exists():
        raise SystemExit(f"merge failed for {tag}:\n{p.stdout[-2000:]}{p.stderr[-2000:]}")
    return wall


def main() -> int:
    pin_sha, new_sha = sha(PIN), sha(NEW)
    if not pin_sha.startswith(SHA_PREFIX):
        raise SystemExit(f"WRONG PIN BINARY: {pin_sha[:16]} != {SHA_PREFIX}")
    if pin_sha == new_sha:
        raise SystemExit(
            "PIN AND HEAD BINARIES ARE THE SAME FILE -- this test would compare a "
            "build against itself and pass vacuously. Rebuild from HEAD first.")
    print(f"pin  {PIN}\n     sha256 {pin_sha[:16]}")
    print(f"head {NEW}\n     sha256 {new_sha[:16]}\n")

    SCRATCH.mkdir(parents=True, exist_ok=True)
    rows, differ = [], 0
    for subject, stride in CASES:
        frames = sorted(SRC[subject].glob("*.ARW"))[::stride]
        tag = f"{subject}-s{stride}-n{len(frames)}"
        d = SCRATCH / f"src-{tag}"
        build(frames, d)
        a, b = SCRATCH / f"{tag}-pin.tif", SCRATCH / f"{tag}-head.tif"
        wa = run(PIN, d, a, tag + "-pin", conf=True)
        wb = run(NEW, d, b, tag + "-head", conf=True)
        ha, hb = sha(a), sha(b)
        ca = sha(a.with_name(a.stem + "-conf.tif"))
        cb = sha(b.with_name(b.stem + "-conf.tif"))
        same, csame = ha == hb, ca == cb
        differ += (not same) or (not csame)
        rows.append({"subject": subject, "stride": stride, "n": len(frames),
                     "merge_same": same, "conf_same": csame,
                     "pin_sha": ha[:16], "head_sha": hb[:16],
                     "pin_conf": ca[:16], "head_conf": cb[:16],
                     "wall_pin": wa, "wall_head": wb})
        print(f"{tag:22s} merge {'IDENTICAL' if same else 'DIFFERS':9s}  "
              f"conf {'IDENTICAL' if csame else 'DIFFERS':9s}  "
              f"{wa:6.1f}s / {wb:6.1f}s")
        shutil.rmtree(d, ignore_errors=True)

    (ROOT / "binsame.json").write_text(json.dumps(
        {"pin_sha": pin_sha, "head_sha": new_sha, "cases": rows}, indent=1),
        encoding="utf-8")
    if differ:
        print(f"\n{differ} CASE(S) DIFFER -- V-SELECT and V-DRIFT numbers describe "
              "the pin, not HEAD, and the affected ladders must be re-run.")
        return 1
    print("\nMERGE BEHAVIOUR UNCHANGED FROM PIN TO HEAD on every case tested.\n"
          "The two binaries differ in bytes but not in what they compute here, so\n"
          "the existing V-SELECT / V-DRIFT measurements describe HEAD as well.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
