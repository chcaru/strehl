#!/usr/bin/env python3
"""Dose-response: merge bee-3-cpl through DELIBERATELY MISREGISTERED sidecars.

This is the experiment that connects geometry to detail.  Everything else in
V-DRIFT measures where the frames were put; this measures what putting them
there costs the picture.

THE MATCHED PAIR.  `walk` and `iid` are planted at the SAME maximum absolute
displacement, so the merge's coverage crop -- and therefore BUILD-TRIAGE's band
scale factor `k` -- is matched between them, and so is the amount by which the
stack is "misregistered" in the sense the word is usually used.  They differ
only in how that displacement is distributed along the index:

    walk   smooth, accumulating.  20 px of absolute excursion, 0.55 px of
           LOCAL relative error between neighbouring frames.
    iid    rough, non-accumulating.  20 px of absolute excursion, 9.46 px of
           LOCAL relative error.

If accumulated drift is what destroys detail, `walk` must cost detail.  If only
local relative error can blur a merge, `walk` is nearly free and `iid` is
expensive.  The arms are the hypothesis.

CACHE ISOLATION.  Each arm gets its OWN STREHL_CACHE_DIR.  The shared cache at
%LOCALAPPDATA%\\strehl\\warpmaps is what `strehl stack` reads by default and
nine other lanes are running on this machine; planting a deliberately broken
sidecar there would corrupt their runs.

MEASUREMENT MODE.  `--linear-srgb --demosaic`, per BUILD-TRIAGE: quality is
never judged on an `--srgb` render because the transfer curve is a strong
non-linearity that moves every ratio, and `--demosaic` is implied by `--srgb`
but NOT by `--linear-srgb`, so omitting it would compare a binned render
against a full-resolution one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from perturb import perturb  # noqa: E402

BIN = Path(r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe")
SHA_PREFIX = "44C2F2CD2E5B2894"
ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
SEED = Path(ROOT, "cache", "bee-3-cpl-9287871c355f81d7.warpmap.txt")

# (arm name, shape, amplitude px)
ARMS = [
    ("d0", "none", 0.0),
    ("walk20", "walk", 20.0),
    ("iid20", "iid", 20.0),
    ("iid2", "iid", 2.0),
    ("walk60", "walk", 60.0),
]


def check_binary() -> str:
    h = hashlib.sha256(BIN.read_bytes()).hexdigest().upper()
    if not h.startswith(SHA_PREFIX):
        raise SystemExit(f"WRONG BINARY: sha256 {h[:16]} != {SHA_PREFIX}")
    return h


def run_arm(name: str, shape: str, amp: float, src_dir: Path, seed: int) -> dict:
    cache = ROOT / "dose-cache" / name
    cache.mkdir(parents=True, exist_ok=True)
    sidecar = cache / SEED.name
    st = perturb(SEED, sidecar, shape, amp, seed)

    out = ROOT / "merge" / f"{name}.tif"
    log = ROOT / "merge" / f"{name}.log"
    env = {**dict(__import__("os").environ), "STREHL_CACHE_DIR": str(cache)}
    cmd = [str(BIN), "stack", str(src_dir), "--out", str(out),
           "--linear-srgb", "--demosaic"]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    wall = time.time() - t0
    log.write_text(p.stdout + p.stderr, encoding="utf-8")
    txt = p.stdout + p.stderr

    m = re.search(r"field of view scaled to ([0-9.]+)", txt)
    k = float(m.group(1)) if m else None
    m = re.search(r"(\d+) placed / (\d+) refused", txt)
    placed = int(m.group(1)) if m else None
    st.update(arm=name, rc=p.returncode, wall_s=round(wall, 1), k=k,
              placed=placed, out=str(out),
              bytes=out.stat().st_size if out.exists() else 0)
    return st


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=r"D:\personal\macro\bee-3-cpl")
    ap.add_argument("--seed", type=int, default=20260824)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--keep-baseline", action="store_true",
                    help="reuse merge/d0.tif instead of re-merging the d0 arm")
    a = ap.parse_args()

    sha = check_binary()
    print(f"binary sha256 {sha[:16]}... OK")
    jsonl = ROOT / "dose-bee3.jsonl"
    with jsonl.open("a", encoding="utf-8") as fh:
        for name, shape, amp in ARMS:
            if a.only and name not in a.only:
                continue
            if name == "d0" and a.keep_baseline and (ROOT / "merge" / "d0.tif").exists():
                print(f"{name:8s} reusing existing baseline merge")
                continue
            st = run_arm(name, shape, amp, Path(a.src), a.seed)
            fh.write(json.dumps(st) + "\n")
            fh.flush()
            loc = st["local_rel_px"]
            print(f"{st['arm']:8s} rc={st['rc']} {st['wall_s']:6.1f}s  k={st['k']} "
                  f"abs_max={st['abs_max_px']:6.2f}  sep1={loc.get(1, 0):6.3f} "
                  f"sep8={loc.get(8, 0):6.3f}  {st['bytes']/1e6:.1f} MB")
            shutil.rmtree(ROOT / "dose-cache" / name, ignore_errors=True)


if __name__ == "__main__":
    main()
