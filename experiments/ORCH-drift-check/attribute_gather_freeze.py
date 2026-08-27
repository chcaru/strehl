"""Attribute the full-resolution-gather byte-freeze break by ISOLATING THE VARIABLE.

Same standard the registry set at `2525e08`, `96571ee` and `6430fb2`, and for
the same reason: a hash moved for *a* reason, not necessarily *that* reason.
This is a shared working tree and five files were left modified in `crates/` by
agents that died before committing. Building a pin of a parent commit could only
show the bytes differ across a boundary; it could not separate the gather flip
from anything else sitting uncommitted in the same tree.

TWO ARMS per row, and a PER-ROW PREDICTION derived from the code before the
measurement is taken:

  * `STREHL_FULLRES_GATHER=0` must reproduce the STANDING registry baseline
    exactly, on **every** row. That shows the flipped default is the *entire*
    delta, and clears the five uncommitted files -- and every commit since
    `6430fb2` -- of touching these bytes.
  * The default arm must move **exactly the rows the mechanism says it can**.
    `fullres_gather_enabled()` is read in exactly one place,
    `align_cmd.rs::warp_frame_in_place`, which is warp application. So:
      - `coffee-bean-20-gate2-sidecar` applies a warp -> **must MOVE**. If it
        does not, the flag is inert and the `=0` arm proves nothing, since a
        build that ignored the flag entirely would also reproduce the baseline.
      - `coffee-bean-20-gate2-unaligned` is rendered with `STREHL_ALIGN=0`, so
        `warp_frame_in_place` never runs and the flag is unreachable -> **must
        NOT MOVE**. If it moves, the change reached past warp application into
        the election or the merge, and the one-line diff is not the whole story.
    The registry predicted this exact signature in the `6430fb2` note, in
    advance and against itself: *"a change that moved only the sidecar row would
    have been in warp application and would not have been this one."* This is
    that change. The unaligned row is therefore a SPECIFICITY CONTROL, not a
    failure -- but it is only a control because the prediction was written from
    the call site before the number came back, and a violation in **either**
    direction fails this script.

A THIRD CHECK this script can make that the acuity one could not: `byte-freeze.rs`
already measured the new sidecar hash independently and printed it as `actual`.
If the default arm here reproduces that value, two instruments that share no code
agree on the new baseline. It is written down as a constant and COMPARED, never
read from the registry -- reading it back would make this script agree with
whatever was already pasted there.

Run:  python experiments/ORCH-drift-check/attribute_gather_freeze.py
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
OUT = Path(r"C:\dev\strehl-out\GATHER-ATTR")

# Mirrors `RENDER_ENV` in byte-freeze.rs, including the entry this change added.
RENDER_ENV = [
    "STREHL_ALIGN", "STREHL_WARPMAP", "STREHL_CACHE_DIR",
    "STREHL_FIX_HALO", "STREHL_FIX_HALO_DELTA",
    "STREHL_EDGE_AWARE", "STREHL_EDGE_TAU", "STREHL_EDGE_CONF",
    "STREHL_ACUITY", "STREHL_FULLRES_GATHER", "STREHL_ONLY_FRAME",
    "STREHL_MERGE", "STREHL_PYRAMID_WORKERS",
    "STREHL_VEIL", "STREHL_VEIL_MARGIN", "STREHL_VEIL_FLOOR",
    "STREHL_FIX_CA", "STREHL_PHOTOMETRIC",
]

# The baselines STANDING IN THE REGISTRY before this change (fields [11] of
# crates/strehl-cli/tests/byte-freezes.tsv at 6430fb2), each with the movement
# the CALL SITE predicts, written down before the render was run.
ROWS = [
    ("coffee-bean-20-gate2-unaligned",
     {"STREHL_ALIGN": "0"},
     "88712017FE31362F35FF2FF5D4B98727CDEFCBAC489D9A7827F21EE0154A8620",
     False,  # no warp is applied, so warp_frame_in_place never reads the flag
     "STREHL_ALIGN=0: warp_frame_in_place never runs, flag unreachable"),
    ("coffee-bean-20-gate2-sidecar",
     {"STREHL_WARPMAP": str(DATA / "coffee-bean-20.warpmap.txt")},
     "63BB88C90908C4CF1EDA32D2C764FECC33F31A4D64A5273BBF677E582394C7F0",
     True,   # applies a warp, so the flag selects the gather for every pixel
     "applies a warp: the flag selects the gather for every output pixel"),
]

# What `byte-freeze.rs` itself reported as `actual` for the sidecar row when the
# flip broke it. Independent of this script; compared, never sourced.
TEST_REPORTED_SIDECAR = (
    "52517FF8AE245F238C29F64A29E601C2D5C064CB4D86E93006512993837EC206"
)


def render(rid: str, extra: dict[str, str], gather: str | None, tag: str) -> str:
    scratch = OUT / f"{rid}-{tag}-cache"
    scratch.mkdir(parents=True, exist_ok=True)
    tif = OUT / f"{rid}-{tag}.tif"
    env = dict(os.environ)
    for k in RENDER_ENV:
        env.pop(k, None)
    env.update(extra)
    env["STREHL_CACHE_DIR"] = str(scratch)
    if gather is not None:
        env["STREHL_FULLRES_GATHER"] = gather
    argv = [str(EXE), "stack", str(STACK),
            # Named explicitly because BOTH defaults have moved since these rows
            # were frozen (byte-freeze.rs passes the same two). Omitting them
            # renders a different pipeline than the rows describe.
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
        sys.exit(f"no binary at {EXE} -- cargo build --release first")
    if not STACK.is_dir():
        sys.exit(f"no capture dir at {STACK}")

    ok = True
    newvals = []
    for rid, extra, old, expect_move, why in ROWS:
        print(f"\n=== {rid} ===", flush=True)
        print(f"  prediction from the call site: "
              f"{'MOVES' if expect_move else 'MUST NOT MOVE'}  ({why})")
        off = render(rid, extra, "0", "gatheroff")
        on = render(rid, extra, None, "gatherdefault")
        rep = off == old
        moved = on != old
        newvals.append((rid, on))
        print(f"  registry baseline      : {old}")
        print(f"  GATHER=0               : {off}   "
              f"{'REPRODUCED' if rep else 'DID NOT REPRODUCE'}")
        print(f"  default (unset == on)  : {on}   "
              f"{'MOVED' if moved else 'DID NOT MOVE'}")
        if not rep:
            print("  -> some of this delta is NOT the gather flip; do not sign this row")
            ok = False
        if moved != expect_move:
            print(f"  -> PREDICTION VIOLATED: predicted "
                  f"{'a move' if expect_move else 'no move'}, "
                  f"observed {'a move' if moved else 'no move'}. "
                  f"{'The flag is inert and the =0 arm proves nothing.' if expect_move else 'The change reached past warp application; the one-line diff is not the whole story.'}")
            ok = False
        elif rep and expect_move:
            print("  -> ATTRIBUTED: the gather flip is the entire delta on this row")
        elif rep:
            print("  -> SPECIFICITY HELD: the flip did not reach a row that applies no warp")

    if not any(m for _, _, _, m, _ in ROWS):
        sys.exit("no row predicts a move: this script cannot fail and proves nothing")

    print("\n--- cross-check against the test's own independent measurement ---")
    got = dict(newvals)["coffee-bean-20-gate2-sidecar"]
    agree = got == TEST_REPORTED_SIDECAR
    print(f"  byte-freeze.rs reported : {TEST_REPORTED_SIDECAR}")
    print(f"  this script measured    : {got}   "
          f"{'AGREE' if agree else 'DISAGREE'}")
    if not agree:
        print("  -> two instruments disagree on the new bytes; something is unpinned")
        ok = False

    print("\n================ NEW BASELINES ================")
    for rid, val in newvals:
        print(f"  {rid:<34} {val}")
    print(f"\n{'ATTRIBUTION PROVEN' if ok else 'ATTRIBUTION FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
