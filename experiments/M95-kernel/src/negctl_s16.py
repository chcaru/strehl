"""Negative control for verify_s16.py.

A green verifier is a claim about the instrument. Each mutation is anchored on
a string asserted UNIQUE in the file and the script hard-errors if it does not
land -- a bare replace(x, y, 1) that silently hits the wrong occurrence, or no
occurrence, produces a green that means nothing. The report is copied to a
scratch path first and restored from that copy, never from git.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Discipline 702: this gate reports through stdout and its exit code is read as
# a claim. Python picks the ANSI codepage for piped stdout, which is every agent
# tool call and every CI log, and cp1252 cannot encode the minus signs and arrows
# this corpus uses. Without this, print() raises mid-run and the process exits 1:
# indistinguishable from a real failure. Measured in k18_gate702.py.
sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
sys.stderr.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
VERIFY = ROOT / "experiments" / "M95-kernel" / "src" / "verify_s16.py"
BACKUP = Path(os.environ["TEMP"]) / "M95-kernel.md.s16.bak"

MUTATIONS = [
    ("DCO lanczos3", "| lanczos3 | 4.852171 |", "| lanczos3 | 4.852172 |"),
    ("bootstrap CI", "**[1.9045, 2.0104]**", "**[1.9046, 2.0104]**"),
    ("void declaration", "**ARM VOID. The bar was not moved",
     "**ARM FINE. The bar was not moved"),
    ("S1 exact zero", "| nearest | **0.000000** |", "| nearest | **0.000001** |"),
]

shutil.copy2(REPORT, BACKUP)
original = REPORT.read_bytes()
print(f"backed up {len(original)} bytes to {BACKUP}")


def run_verify():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


rc, _ = run_verify()
print(f"\nbaseline (unmutated): rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
if rc != 0:
    raise SystemExit("baseline is not green; the control cannot be read")

results = []
try:
    for label, old, new in MUTATIONS:
        text = original.decode("utf-8")
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"MUTATION TARGET NOT UNIQUE for {label!r}: {n} occurrences of {old!r}")
        REPORT.write_text(text.replace(old, new, 1), encoding="utf-8")
        os.utime(REPORT, None)
        time.sleep(0.05)
        rc, out = run_verify()
        bad = sum(1 for line in out.splitlines() if line.strip().startswith("BAD"))
        caught = rc != 0
        results.append((label, caught, bad))
        print(f"  {'CAUGHT' if caught else 'MISSED'}  {label:<20} rc={rc}  BAD lines={bad}")
        REPORT.write_bytes(original)
        os.utime(REPORT, None)
finally:
    REPORT.write_bytes(original)
    os.utime(REPORT, None)

assert REPORT.read_bytes() == original, "restore failed"
print(f"\nrestored byte-identical: {REPORT.read_bytes() == original}")

rc, _ = run_verify()
print(f"post-restore verify: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")

n_caught = sum(1 for _, c, _ in results if c)
print(f"\nnegative control: {n_caught}/{len(results)} planted defects caught")
sys.exit(0 if (n_caught == len(results) and rc == 0) else 1)
