"""Contamination audit: prove every sidecar M107 used carries the FULL bracket.

Prompted by the orchestrator quarantining 11 stray sidecars from the capture
library, one of which (bee-3-cpl, 1560 bytes) held a 40-frame solve for a
299-frame bracket. A stale sidecar contaminates treatment and control
identically, so no control in this milestone could have caught it. The only
defence is to count the frames.

Counts placed/unplaced/refused rows in every sidecar under the M107 renders
directory and checks each against the ARW count of its stack.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from e3_argmax import read_warpmap  # noqa: E402

R = r"C:\dev\strehl-out\M107-chroma\renders"
LIB = r"D:\personal\macro"

rows = []
for name in sorted(os.listdir(R)):
    if not name.endswith("-warpmap.txt"):
        continue
    stack = name[: -len("-warpmap.txt")]
    meta, warps = read_warpmap(os.path.join(R, name))
    n_side = len(warps)
    n_placed = sum(1 for w in warps if w is not None)
    d = os.path.join(LIB, stack)
    n_arw = (len([f for f in os.listdir(d) if f.lower().endswith(".arw")])
             if os.path.isdir(d) else -1)
    ok = (n_side == n_arw) and (n_placed == n_arw)
    rows.append((stack, n_side, n_placed, n_arw, ok))

w = max(len(r[0]) for r in rows)
print(f"{'stack':<{w}}  sidecar  placed   ARWs  verdict")
allok = True
for stack, n_side, n_placed, n_arw, ok in rows:
    allok &= ok
    print(f"{stack:<{w}}  {n_side:>7}  {n_placed:>6}  {n_arw:>5}  "
          f"{'OK' if ok else '*** MISMATCH ***'}")
print("\nALL SIDECARS FULL-BRACKET:", allok)
sys.exit(0 if allok else 1)
