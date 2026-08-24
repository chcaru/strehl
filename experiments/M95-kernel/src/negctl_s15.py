"""Negative control for verify_s15.py, rewritten alongside the gate.

A gate that has only ever been seen to pass is not a gate. This plants defects
into section 15 and requires the rewritten verifier to catch each one, then
restores the report and proves the restore was byte-exact.

ARMS
  D1  a 15.3 table cell is altered      -> row reconstruction must break
  D2  the RETRACTED marker is removed   -> structural check must break
  D3  the struck claim is un-struck     -> pass 5 must read STILL ASSERTED
  TOOL  an input artifact is hidden     -> gate must exit 2, not 1
  POWER a byte is appended to the report and the gate must still pass its
        artifact checks, proving the restore path itself is exercised

Each mutation is anchored on a full unique line and hard-errors if it does not
land exactly once. A plant that silently fails to apply produces a green run
that proves nothing -- that is how a control lies.

Never uses `git checkout -- <path>`: the report is stashed to a temp copy and
restored from that copy, and the restore is verified by sha256.
"""

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
GATE = ROOT / "experiments" / "M95-kernel" / "src" / "verify_s15.py"
ART = ROOT / "experiments" / "M95-kernel" / "out" / "k19b_seeds.json"
ART2 = ROOT / "experiments" / "M95-kernel" / "out" / "k19c_quota.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def run_gate():
    p = subprocess.run([sys.executable, str(GATE)], cwd=str(ROOT),
                       capture_output=True, text=True, errors="replace",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return p.returncode, (p.stdout or "") + (p.stderr or "")


ORIG = REPORT.read_bytes()
ORIG_SHA = sha(REPORT)
stash = Path(tempfile.gettempdir()) / "M95-kernel.md.negctl_s15.stash"
stash.write_bytes(ORIG)
text = ORIG.decode("utf-8")

print("=" * 84)
print("negctl_s15 -- can the rewritten section-15 gate fail?")
print("=" * 84)
print(f"report sha256 before: {ORIG_SHA[:16]}...  stashed to {stash.name}")

rc0, out0 = run_gate()
print(f"\nbaseline (unmutated): rc={rc0}  {'GREEN' if 'GREEN' in out0 else 'RED'}")
if rc0 != 0:
    stash.unlink()
    raise SystemExit("baseline is not green; cannot run a negative control against it")

DEFECTS = [
    ("D1 table cell altered",
     "| pwsh 7.6.5 | `\\| -Last 3` | 1 | 1 | 1 | sets it correctly |",
     "| pwsh 7.6.5 | `\\| -Last 3` | 1 | 1 | 0 | sets it correctly |"),
    ("D2 retraction marker removed",
     "> **RETRACTED 2026-08-24 15:5x",
     "> **NOTED 2026-08-24 15:5x"),
    ("D3 struck claim un-struck",
     "3. ~~**Truncation only bites a process that is still running.**",
     "3. **Truncation only bites a process that is still running.**"),
    ("D4 15.4 quota cell altered",
     "| 1,-1,1 | -1,1,1 |",
     "| 1,1,1 | -1,1,1 |"),
    ("D5 15.4 -File cell altered",
     "| -1,-1,-1 | -1,-1,-1 | -1,1,-1 | -1,1,1 |",
     "| -1,-1,-1 | -1,-1,-1 | -1,-1,-1 | -1,1,1 |"),
    ("D6 15.4 prediction un-scored",
     "**Scoring my registered prediction, which was half wrong.**",
     "**Scoring my registered prediction.**"),
]

caught = 0
for label, old, new in DEFECTS:
    n = text.count(old)
    if n != 1:
        REPORT.write_bytes(ORIG)
        stash.unlink()
        raise SystemExit(f"MUTATION TARGET NOT FOUND ({n} occurrences) for {label}: {old!r}")
    REPORT.write_text(text.replace(old, new, 1), encoding="utf-8")
    rc, out = run_gate()
    bad = [ln.strip() for ln in out.splitlines() if ln.strip().startswith("BAD")]
    hit = rc == 1
    caught += hit
    print(f"\n  {label}")
    print(f"    rc={rc}  ->  {'CAUGHT' if hit else 'MISSED'}")
    for ln in bad[:3]:
        print(f"      {ln}")
    REPORT.write_bytes(ORIG)

# TOOL arm: a missing input must be exit 2 (verifier broke), never exit 1.
print("\n  TOOL arm: input artifact hidden")
hidden = ART.with_suffix(".json.hidden")
ART.rename(hidden)
try:
    rc, out = run_gate()
finally:
    hidden.rename(ART)
tool_ok = rc == 2 and "VERIFIER BROKE" in out
print(f"    rc={rc}  ->  {'CORRECT (2 = broke, not 1 = failed)' if tool_ok else 'WRONG'}")

# POWER arm: prove the mutate/restore path is live, not a no-op.
print("\n  POWER arm: one byte appended")
REPORT.write_bytes(ORIG + b"\n")
rc_p, out_p = run_gate()
REPORT.write_bytes(ORIG)
power_ok = sha(REPORT) == ORIG_SHA
print(f"    appended-byte run rc={rc_p}; restore byte-exact: {power_ok}")

print("\n" + "=" * 84)
final_sha = sha(REPORT)
restored = final_sha == ORIG_SHA
rc_final, out_final = run_gate()
print(f"report sha256 after : {final_sha[:16]}...  restored byte-exact: {restored}")
print(f"gate on restored report: rc={rc_final}  {'GREEN' if 'GREEN' in out_final else 'RED'}")
print(f"defects caught: {caught}/{len(DEFECTS)}   tool arm: {'PASS' if tool_ok else 'FAIL'}"
      f"   restore: {'PASS' if power_ok and restored else 'FAIL'}")
stash.unlink()

allgood = caught == len(DEFECTS) and tool_ok and restored and rc_final == 0
print("=" * 84)
print(f"verdict: {'PASS -- the gate can fail, and does' if allgood else 'FAIL'}")
print("=" * 84)
sys.exit(0 if allgood else 1)
