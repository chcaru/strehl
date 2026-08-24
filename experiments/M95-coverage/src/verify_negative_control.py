"""Certify verify_report.py by planting defects it must catch.

A verifier that has only ever been green is an untested instrument. This plants
three one-character defects in the report and requires the verifier to go RED on
each, then restores and requires GREEN again.

SAFETY. The report is backed up to $env:TEMP and restored from that copy.
Never `git checkout -- <path>`: it reverts to HEAD, and this report is
uncommitted, so a checkout restore would delete it outright.

MUTATION ANCHORING. Each mutation is anchored on a full, unique line and the
script hard-errors if the anchor does not land exactly once. A bare
`replace(x, y, 1)` can silently hit an earlier occurrence and produce a green
run that looks like a passing control.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-coverage.md"
VERIFY = Path(__file__).with_name("verify_report.py")

MUTATIONS = [
    ("**+0.1813 dex** (sem 0.0031)",
     "**+0.1814 dex** (sem 0.0031)",
     "NOW cost last digit"),
    ("0.0042 dex**",
     "0.0043 dex**",
     "recovery last digit"),
    ("| 0.9315 | 7.35% | +0.1836 |",
     "| 0.9315 | 7.35% | +0.1837 |",
     "ladder k=0.9315 cost"),
]


def run():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, str(VERIFY)], capture_output=True,
                       text=True, encoding="utf-8", env=env, cwd=str(VERIFY.parent))
    return p.returncode


def main():
    if not REPORT.exists():
        sys.exit(f"missing {REPORT}")
    backup = Path(tempfile.gettempdir()) / "m95-coverage-report-backup.md"
    shutil.copy2(REPORT, backup)
    print(f"backed up to {backup}\n")
    original = REPORT.read_text(encoding="utf-8")
    failures = []
    try:
        rc = run()
        print(f"baseline (unmutated)                 rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("baseline was not green")

        for old, new, name in MUTATIONS:
            n = original.count(old)
            if n != 1:
                failures.append(f"anchor for {name!r} occurs {n} times, need exactly 1")
                print(f"  MUTATION TARGET NOT FOUND ({n} hits): {name}")
                continue
            REPORT.write_text(original.replace(old, new, 1), encoding="utf-8")
            rc = run()
            print(f"mutated: {name:<28} rc={rc}  "
                  f"{'RED (correct)' if rc != 0 else 'GREEN (WRONG)'}")
            if rc == 0:
                failures.append(f"verifier did not catch {name}")
            REPORT.write_text(original, encoding="utf-8")

        rc = run()
        print(f"restored                             rc={rc}  "
              f"{'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("did not return to green after restore")
    finally:
        shutil.copy2(backup, REPORT)

    if failures:
        print("\nNEGATIVE CONTROL FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nNEGATIVE CONTROL PASSED "
          "(green -> red, red, red -> green)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
