"""Negative control for verify_s24.py: plant defects, require RED.

A gate that has only ever said GREEN is an untested instrument. This plants
known defects one at a time and requires the gate to catch each, then restores
the report from a byte copy verified by SHA-256.

Design constraints inherited from the section 23 negative control, each of
which came from a measured failure there:

  * every anchor must occur EXACTLY ONCE in the report, and a miss is a hard
    error rather than a silent no-op -- a mutation that does not land reads as
    a green and would certify a hole that is really a typo;
  * restore from a %TEMP% byte copy, NEVER `git checkout --`, which reverts to
    HEAD and has destroyed uncommitted work on this machine before;
  * exit 1 means a planted defect was MISSED (a real hole in the gate),
    exit 2 means this harness could not run. They are different claims.

The tool defects (T*) check the other direction: that the gate reports a tool
failure rather than a green when its own inputs are missing.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
ART = ROOT / "experiments" / "M95-resample" / "out" / "x18_cachectl.json"
GATE = ROOT / "experiments" / "M95-resample" / "src" / "verify_s24.py"
BAK = Path(os.environ["TEMP"]) / "M95-kernel.md.negctl_s24.bak"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def die(msg: str) -> None:
    print(f"TOOL FAILURE: {msg}", file=sys.stderr)
    sys.exit(2)


def run_gate() -> int:
    r = subprocess.run(
        [sys.executable, str(GATE)], capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return r.returncode


# (label, unique anchor to replace, replacement, what it breaks)
SUBJECT: list[tuple[str, str, str, str]] = [
    (
        "D1 flip the power control's verdict to 'same'",
        "| C1 | **PRE** | plain, align between |",
        "| C1 | **PRE** | plain, align between |".replace("C1", "C1"),
        "placeholder -- replaced below",
    ),
]

# D1 needs the whole row, so build the mutations from the real file text.
raw = REPORT.read_text(encoding="utf-8")


def one_line_starting(prefix: str) -> str:
    hits = [ln for ln in raw.splitlines() if ln.startswith(prefix)]
    if len(hits) != 1:
        die(f"expected exactly 1 line starting {prefix!r}, found {len(hits)}")
    return hits[0]


c1row = one_line_starting("| C1 |")
c3row = one_line_starting("| C3 |")

SUBJECT = [
    (
        "D1 power control's DIFFER flipped to same",
        c1row,
        c1row.replace("**DIFFER**", "same"),
        "the claim that the instrument could say otherwise",
    ),
    (
        "D2 one hex digit changed in C3's B hash",
        c3row,
        c3row.replace("2FD1169422E6A6F1` |", "2FD1169422E6A6F2` |", 1),
        "my own clearance: the override arm's byte-identity",
    ),
    (
        "D3 'nine seconds' inflated to 'nine minutes'",
        "committed at 13:41:44, **nine seconds before the fix**",
        "committed at 13:41:44, **nine minutes before the fix**",
        "how close the PRE binary sits to the fix",
    ),
    (
        "D4 frame count 19 -> 18",
        "`coffee-bubbles`, 19 frames, merge reference 9",
        "`coffee-bubbles`, 18 frames, merge reference 9",
        "the fixed inputs of the control",
    ),
    (
        "D5 the stale-artifact disclosure deleted",
        "records\n`8e49842` -- the repository HEAD at the moment the file was written",
        "records the commit the POST binary was built from",
        "the honesty note in 24.5",
    ),
    (
        "D6 capture-dir assertion weakened",
        "held 19 files before the control and 19 after",
        "held the same number of files before the control and after",
        "the read-only guarantee on the capture library",
    ),
    (
        "D7 sidecar-override token swapped for the solved one",
        "`ON (sidecar-override), reference frame 9, 19 placed / 0 refused`, against",
        "`ON (solved), reference frame 9, 19 placed / 0 refused`, against",
        "the evidence that the override path was the one taken",
    ),
]

if BAK.exists():
    BAK.unlink()
shutil.copy2(REPORT, BAK)
if sha(BAK) != sha(REPORT):
    die("backup copy does not match the report")
ORIG = sha(REPORT)
print(f"backup {BAK}  sha256 {ORIG[:16]}...\n")

# The gate must be GREEN before any mutation, or nothing below means anything.
base = run_gate()
if base != 0:
    die(f"gate is not green before mutation (exit {base}); fix that first")
print("baseline: gate GREEN\n")

caught = 0
missed: list[str] = []
for label, old, new, breaks in SUBJECT:
    text = REPORT.read_text(encoding="utf-8")
    n = text.count(old)
    if n != 1:
        REPORT.write_bytes(BAK.read_bytes())
        die(f"MUTATION TARGET NOT FOUND ({n} hits, need 1) for {label!r}")
    REPORT.write_text(text.replace(old, new, 1), encoding="utf-8")
    rc = run_gate()
    REPORT.write_bytes(BAK.read_bytes())
    if sha(REPORT) != ORIG:
        die(f"restore failed after {label!r}")
    if rc == 1:
        caught += 1
        print(f"  CAUGHT  {label}")
    else:
        missed.append(label)
        print(f"  MISSED  {label}  (gate exited {rc}) -- breaks: {breaks}")

# --- tool defects: the gate must say 2, not 0 -------------------------------
tool_ok = 0
tool_total = 2

hidden = ART.with_suffix(".json.hidden")
ART.rename(hidden)
rc = run_gate()
hidden.rename(ART)
print(f"  {'CAUGHT' if rc == 2 else 'MISSED'}  T1 artifact JSON hidden (gate exited {rc}, want 2)")
tool_ok += 1 if rc == 2 else 0

text = REPORT.read_text(encoding="utf-8")
REPORT.write_text(text.replace("## 24. The cache-contamination control", "## 24bis", 1), encoding="utf-8")
rc = run_gate()
REPORT.write_bytes(BAK.read_bytes())
if sha(REPORT) != ORIG:
    die("restore failed after T2")
print(f"  {'CAUGHT' if rc == 2 else 'MISSED'}  T2 section heading removed (gate exited {rc}, want 2)")
tool_ok += 1 if rc == 2 else 0

print(f"\nrestored byte-exact: {sha(REPORT) == ORIG}")
print(f"subject defects: {caught}/{len(SUBJECT)} caught")
print(f"tool defects:    {tool_ok}/{tool_total} caught")
if missed:
    print("\nHOLES IN THE GATE -- these defects would have shipped green:")
    for label in missed:
        print(f"  - {label}")
sys.exit(1 if (missed or tool_ok != tool_total) else 0)
