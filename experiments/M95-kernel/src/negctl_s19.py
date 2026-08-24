"""Negative control for verify_s19.py.

Anchors asserted UNIQUE, hard-error on a miss, restore from a scratch copy.
Anchors are chosen to sit WITHIN one line: section 19's prose wraps, and a
mutation string spanning a line break silently finds nothing -- the trap that
fired on negctl_s18's first run.
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
VERIFY = ROOT / "experiments" / "M95-kernel" / "src" / "verify_s19.py"
BACKUP = Path(os.environ["TEMP"]) / "M95-kernel.md.s19.bak"

MUTATIONS = [
    ("fix commit time", "at **10:32:43**", "at **10:32:44**"),
    ("first delta", "| **\u2212306 s** |", "| **\u2212307 s** |"),
    ("third delta", "| **+59 s** |", "| **+58 s** |"),
    ("M97 commit id", "landed at `69f7b4c`", "landed at `69f7b4d`"),
]

shutil.copy2(REPORT, BACKUP)
original = REPORT.read_bytes()
print(f"backed up {len(original)} bytes to {BACKUP}")


def run():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


rc, _ = run()
print(f"\nbaseline: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
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
        rc, out = run()
        bad = sum(1 for l in out.splitlines() if l.strip().startswith("BAD"))
        results.append((label, rc != 0, bad))
        print(f"  {'CAUGHT' if rc != 0 else 'MISSED'}  {label:<18} rc={rc}  BAD={bad}")
        REPORT.write_bytes(original)
        os.utime(REPORT, None)
finally:
    REPORT.write_bytes(original)
    os.utime(REPORT, None)

assert REPORT.read_bytes() == original, "restore failed"
print(f"\nrestored byte-identical: {REPORT.read_bytes() == original}")
rc, _ = run()
print(f"post-restore: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
n_caught = sum(1 for _, c, _ in results if c)
print(f"\nnegative control: {n_caught}/{len(results)} planted defects caught")
sys.exit(0 if (n_caught == len(results) and rc == 0) else 1)
