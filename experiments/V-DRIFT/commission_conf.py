#!/usr/bin/env python3
"""Commission the confidence map on the shipped merge, both ways.

The confidence map is being asked to answer "did the merge COMMIT to a frame at
this pixel, or did it average frames that disagreed".  Before its depth curve
can be read as evidence about dilution, it has to be shown to respond to
commitment in the documented direction AND in both directions -- a statistic
that only ever moves under damage passes a one-sided test trivially.

The pyramid exposes the knobs that set exactly this, so the plant is the real
mechanism rather than a synthetic stand-in:

  --pyramid-select hard-max   the textbook PMax argmax: one frame wins outright
                              instead of a convex combination.  MAXIMALLY
                              committed, so confidence must FALL.
  --pyramid-exponent <F>      the selection exponent.  Raising it sharpens the
                              weighting toward winner-take-all, so confidence
                              must fall; lowering it flattens the weighting
                              toward a plain average, so confidence must RISE.

The exponent ladder is the both-ways test: the same knob moved in opposite
directions from the shipped default has to move the statistic in opposite
directions.  If confidence only falls, or only rises, the map is not reading
commitment and its depth curve means nothing.

Run at ONE fixed N, so nothing about stack depth is in play and the only thing
changing is how hard the merge is asked to commit.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import tifffile

from halfstack import BIN, ROOT, build, check_binary

SCRATCH = ROOT / "commconf"
SRC = Path(r"D:\personal\macro\flower-bud-alone-cpl")
STRIDE = 4


def run(work: Path, out: Path, tag: str, extra: list[str]) -> dict | None:
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
        tail = (p.stdout + p.stderr).strip().splitlines()
        print(f"    FAILED rc={p.returncode}: {tail[-1][:100] if tail else ''}")
        return None
    c = tifffile.imread(str(cmap)).astype(np.float64)
    return {"mean": float(c.mean()), "median": float(np.median(c)),
            "frac_hi": float((c > 500).mean())}


def main() -> int:
    print(f"binary sha256 {check_binary()[:16]}... OK")
    frames = sorted(SRC.glob("*.ARW"))[::STRIDE]
    work = SCRATCH / "frames"
    out = ROOT / "commconf-out"
    out.mkdir(parents=True, exist_ok=True)
    build(frames, work)
    print(f"commissioning on {len(frames)} frames of flower-bud-alone-cpl, "
          f"fixed N\n")

    arms = [("shipped default", []),
            ("exponent 0.5 (flatter, toward an average)", ["--pyramid-exponent", "0.5"]),
            ("exponent 4.0 (sharper, toward a winner)", ["--pyramid-exponent", "4.0"]),
            ("select hard-max (argmax, one frame wins)", ["--pyramid-select", "hard-max"])]

    res = {}
    print(f"{'arm':>44s} {'mean':>8s} {'median':>8s} {'frac>500':>9s}")
    print("-" * 74)
    for name, extra in arms:
        r = run(work, out, name.split()[0] + name.split()[1][:4], extra)
        if r is None:
            continue
        res[name] = r
        print(f"{name:>44s} {r['mean']:8.1f} {r['median']:8.1f} "
              f"{100*r['frac_hi']:8.2f}%")
    shutil.rmtree(SCRATCH, ignore_errors=True)

    base = res.get("shipped default")
    flat = res.get("exponent 0.5 (flatter, toward an average)")
    sharp = res.get("exponent 4.0 (sharper, toward a winner)")
    hard = res.get("select hard-max (argmax, one frame wins)")
    bad = 0
    print()
    if not base:
        print("FAIL: the default arm did not produce a map")
        return 1

    for r, name, want_lower in ((sharp, "exponent 4.0", True),
                                (flat, "exponent 0.5", False),
                                (hard, "hard-max", True)):
        if r is None:
            print(f"[SKIP] {name} did not run")
            continue
        ok = (r["mean"] < base["mean"]) if want_lower else (r["mean"] > base["mean"])
        bad += not ok
        d = "below" if want_lower else "above"
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: mean {r['mean']:.1f} vs "
              f"default {base['mean']:.1f} (want {d} the default)")

    if sharp and flat:
        ok = flat["mean"] > sharp["mean"]
        bad += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] BOTH WAYS: the same knob moved in "
              f"opposite directions moves the statistic in opposite directions "
              f"({flat['mean']:.1f} > {sharp['mean']:.1f})")

    (ROOT / "commconf.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\n{'CONFIDENCE MAP COMMISSIONED' if bad == 0 else f'{bad} CHECK(S) FAILED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
