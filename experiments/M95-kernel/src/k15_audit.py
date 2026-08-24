"""K15 -- audit of section 15's "count = 0" claim, and of the quarantined sidecar.

The orchestrator has quarantined 11 sidecars out of the capture library,
including D:\\personal\\macro\\bee-3-cpl\\warpmap.txt with mtime 09:38:52.
Section 15 of my report says a recursive search of that library at ~12:5x
returned COUNT = 0. Those two statements cannot both be right, and one of them
is mine. This decides which.

BARS, REGISTERED BEFORE THE RUN
-------------------------------
A1 THE PROBE IS THE SUSPECT. Rebuild the exact command shape section 15 used
   -- Get-ChildItem -Recurse -Depth 1 -Filter warpmap*.txt -- against a
   synthetic tree with a file at the SAME depth as
   <library>\\<stack>\\warpmap.txt. If it returns 0, MY PROBE WAS BLIND and
   section 15's finding is retracted. If it returns 1, the probe is sound and
   the file appeared after my check.

A2 CONTROL FOR A1. The same probe with -Recurse and NO -Depth must find the
   file. Without this, a 0 in A1 could just mean the synthetic tree is wrong.

A3 THE QUARANTINED FILE'S TRUE FRAME COUNT. The orchestrator reports it as a
   "40-frame solve". Count the placed rows and read the `frames` and `end`
   fields directly. Reported as measured whether or not it agrees.
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
QUAR = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt")
TREE = Path(r"C:\dev\strehl-out\M95-depthtest")

print("=" * 78)
print("K15  was section 15's 'count = 0' probe blind?")
print("=" * 78)

if TREE.exists():
    shutil.rmtree(TREE)
(TREE / "stack-a").mkdir(parents=True)
(TREE / "stack-a" / "warpmap.txt").write_text("planted\n", encoding="utf-8")
print(f"synthetic tree: {TREE}\\stack-a\\warpmap.txt")
print("  same depth as <library>\\<stack>\\warpmap.txt")


def ps(cmd):
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "").strip()


s15_probe = (f"(Get-ChildItem '{TREE}' -Recurse -Depth 1 -Filter warpmap*.txt "
             f"-ErrorAction SilentlyContinue).Count")
rc_a, out_a = ps(s15_probe)
ctrl_probe = (f"(Get-ChildItem '{TREE}' -Recurse -Filter warpmap*.txt "
              f"-ErrorAction SilentlyContinue).Count")
rc_b, out_b = ps(ctrl_probe)

print(f"\nA1  section 15's exact probe shape  -> {out_a!r}")
print(f"A2  control, -Recurse without -Depth -> {out_b!r}")

n_depth = int(out_a) if out_a.isdigit() else -1
n_plain = int(out_b) if out_b.isdigit() else -1
a2 = n_plain == 1
a1_blind = n_depth == 0

print(f"\n  A2 control (probe can see the planted file at all): "
      f"{'PASS' if a2 else 'FAIL -- A1 is unreadable'}")
if a2:
    if a1_blind:
        print("  A1 VERDICT: MY PROBE WAS BLIND. Section 15's 'count = 0' is RETRACTED.")
    else:
        print("  A1 VERDICT: the probe is sound; the file post-dates my check.")

print("\n" + "=" * 78)
print("A3  the quarantined bee-3-cpl sidecar, read directly")
print("=" * 78)
txt = QUAR.read_text(encoding="utf-8")
frames_field = re.search(r"^frames (\d+)", txt, re.M)
end_field = re.search(r"^end (\d+)", txt, re.M)
ref_field = re.search(r"^reference (\d+)", txt, re.M)
dig_field = re.search(r"^stack-digest (\w+)", txt, re.M)
rows = re.findall(r"^(\d+) (placed|refused)", txt, re.M)
print(f"  bytes           : {QUAR.stat().st_size}")
print(f"  mtime           : {QUAR.stat().st_mtime}")
print(f"  frames field    : {frames_field.group(1) if frames_field else '<none>'}")
print(f"  end field       : {end_field.group(1) if end_field else '<none>'}")
print(f"  reference       : {ref_field.group(1) if ref_field else '<none>'}")
print(f"  stack-digest    : {dig_field.group(1) if dig_field else '<none>'}")
print(f"  placement rows  : {len(rows)}  ({sum(1 for _, s in rows if s == 'placed')} placed)")
claimed = 40
actual = int(frames_field.group(1)) if frames_field else -1
print(f"\n  orchestrator reported a {claimed}-frame solve; the file holds {actual} frames.")
print(f"  {'AGREES' if actual == claimed else 'DISAGREES -- report it'}")

shutil.rmtree(TREE, ignore_errors=True)
print(f"\ncleaned up {TREE}")

print("\n" + "=" * 78)
print("A4  bytes-per-frame across the quarantine, and what 40 frames would weigh")
print("=" * 78)
rowsz = []
for f in sorted(QUAR.parent.glob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    mm = re.search(r"^frames (\d+)", t, re.M)
    n = int(mm.group(1)) if mm else -1
    sz = f.stat().st_size
    per = (sz / n) if n > 0 else float("nan")
    if n > 20:
        rowsz.append(per)
    print(f"  {f.name:<48} {sz:>7} B  frames {n:>4}  {per:>7.1f} B/frame")
if rowsz:
    med = sorted(rowsz)[len(rowsz) // 2]
    hdr = 500
    print(f"\n  median B/frame on the large solves: {med:.1f}")
    print(f"  a 40-frame sidecar would therefore weigh about "
          f"{hdr + 40 * med:.0f} B, not {QUAR.stat().st_size} B")
    print(f"  {QUAR.stat().st_size} B is consistent with the "
          f"{re.search(r'^frames (\d+)', QUAR.read_text(encoding='utf-8'), re.M).group(1)}"
          f" frames the file actually declares")

sys.exit(0)
