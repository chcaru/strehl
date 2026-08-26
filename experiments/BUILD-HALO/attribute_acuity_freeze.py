"""Attribute the acuity byte-freeze break by ISOLATING THE VARIABLE.

Same standard this registry set at `2525e08` and `96571ee`, and for the same
reason: a hash moved for *a* reason, not necessarily *that* reason. Building a
pin of my parent commit could only show the bytes differ across a boundary; it
could not separate my change from anything else other agents landed in the same
range, and this is a shared working tree.

TWO ARMS, both required:

  * `STREHL_ACUITY=0` must reproduce the CURRENT (pre-change) baseline exactly.
    That shows the restored term is the entire delta and clears every other
    commit since the last baseline of touching these bytes.
  * unset must reproduce the NEW baseline exactly. Without this arm, "off
    reproduces the old bytes" would also be satisfied by a build that ignored
    the flag entirely and moved nothing -- the sidecar row's own objection.

The new value is not known in advance, so it is MEASURED here and printed for
pasting into the registry. It is not read back from the registry, which would
make this script agree with whatever was already written there.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
EXE = ROOT / "target" / "release" / "strehl.exe"
STACK = Path(r"D:\personal\macro\coffee-bean")
DATA = ROOT / "crates" / "strehl-cli" / "tests" / "data"
OUT = Path(r"C:\dev\strehl-out\ACUITY-ATTR")

RENDER_ENV = [
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU", "STREHL_EDGE_CONF",
    "STREHL_ACUITY", "STREHL_ONLY_FRAME",
    "STREHL_MERGE", "STREHL_PYRAMID_WORKERS",
    "STREHL_VEIL", "STREHL_VEIL_MARGIN", "STREHL_VEIL_FLOOR",
    "STREHL_FIX_CA", "STREHL_PHOTOMETRIC",
]

# The baselines standing in the registry BEFORE this change.
ROWS = [
    ("coffee-bean-20-gate2-unaligned",
     {"STREHL_ALIGN": "0"},
     "3162EB0B1C8D5F3A1D646CCE50900492DABB9606B6BA58B36156E19171D0781A"),
    ("coffee-bean-20-gate2-sidecar",
     {"STREHL_WARPMAP": str(DATA / "coffee-bean-20.warpmap.txt")},
     "88154E2D59A7288304A6B6967960183F6EB1D538FF5D4649F059206AEECA461E"),
]


def render(rid: str, extra: dict[str, str], acuity: str | None, tag: str) -> str:
    scratch = OUT / f"{rid}-{tag}-cache"
    scratch.mkdir(parents=True, exist_ok=True)
    tif = OUT / f"{rid}-{tag}.tif"
    env = dict(os.environ)
    for k in RENDER_ENV:
        env.pop(k, None)
    env.update(extra)
    env["STREHL_CACHE_DIR"] = str(scratch)
    if acuity is not None:
        env["STREHL_ACUITY"] = acuity
    argv = [str(EXE), "stack", str(STACK),
            # The registry renders every row with these named explicitly
            # (byte-freeze.rs:493-531) because BOTH defaults have since moved:
            # the merge backend now defaults to pyramid and --photometric now
            # defaults on. Omitting them here rendered a different pipeline
            # than the rows describe and the tool refused the flag combination
            # outright -- the same unrecorded-input defect the registry header
            # documents, arriving in the attribution script this time.
            "--merge", "estimator",
            "--photometric", "off",
            "--limit", "20", "--gate", "2.0", "--out", str(tif)]
    p = subprocess.run(argv, env=env, capture_output=True)
    if p.returncode != 0:
        print(p.stderr.decode("utf-8", "replace")[-2500:])
        sys.exit(f"render failed for {rid} ({tag})")
    return hashlib.sha256(tif.read_bytes()).hexdigest().upper()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    if not EXE.exists():
        sys.exit(f"no binary at {EXE} -- cargo build --release -p strehl-cli first")
    if not STACK.is_dir():
        sys.exit(f"no capture dir at {STACK}")

    ok = True
    newvals = []
    for rid, extra, old in ROWS:
        print(f"\n=== {rid} ===", flush=True)
        off = render(rid, extra, "0", "acuoff")
        on = render(rid, extra, None, "acuon")
        rep = off == old
        moved = on != old
        newvals.append((rid, on))
        print(f"  registry baseline : {old}")
        print(f"  STREHL_ACUITY=0   : {off}   {'REPRODUCED' if rep else 'DID NOT REPRODUCE'}")
        print(f"  default (restored): {on}   {'MOVED' if moved else 'DID NOT MOVE'}")
        if not rep:
            print("  -> some of this delta is NOT mine; do not sign for this row")
            ok = False
        if not moved:
            print("  -> the switch is INERT on this row; the 'off' arm proves nothing")
            ok = False
        if rep and moved:
            print("  -> MINE, proven: the restored acuity term is the entire delta")

    print("\n================ NEW BASELINES ================")
    for rid, val in newvals:
        print(f"  {rid:<34} {val}")
    print(f"\n{'ATTRIBUTION PROVEN' if ok else 'ATTRIBUTION FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
