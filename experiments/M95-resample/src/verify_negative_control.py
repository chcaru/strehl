"""Negative control on verify_report.py itself.

A green verifier is a claim about the instrument, not about the document. This plants a
one-digit defect in the report, requires the verifier to go RED, and restores the report
from a copy in TEMP.

Two disciplines are baked in:

  * The mutation is anchored on a UNIQUE FULL-LINE string and this script HARD-ERRORS if
    the anchor does not land or is not unique. A bare `replace(x, y, 1)` can silently hit
    an earlier occurrence and produce a green "control" that tested nothing.
  * The restore is from a TEMP copy, never `git checkout --`, which reverts to HEAD and
    has destroyed uncommitted work on this machine.
"""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
REPORT = os.path.join(ROOT, "docs", "research", "M95-resample.md")

MUTATIONS = [
    (
        "**Attributable to the interpolation kernel alone: \u22120.2360 dex, 1.722\u00d7 power, 1.312\u00d7",
        "**Attributable to the interpolation kernel alone: \u22120.2361 dex, 1.722\u00d7 power, 1.312\u00d7",
        "headline kernel cost",
    ),
    (
        "| lanczos-3 | 0.000604 | 0.108394 | 0.0000% | **9.902\u00d7** |",
        "| lanczos-3 | 0.000604 | 0.108394 | 0.0000% | **9.903\u00d7** |",
        "lanczos ringing ratio",
    ),
    (
        "| B0 \u2192 C | \u22120.3999 | 2.511\u00d7 | 1.585\u00d7 | **unresampled frame \u2192 shipped merge** |",
        "| B0 \u2192 C | \u22120.3998 | 2.511\u00d7 | 1.585\u00d7 | **unresampled frame \u2192 shipped merge** |",
        "total loss table row",
    ),
]


def run_verifier():
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "verify_report.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return r.returncode, r.stdout


def main():
    backup = os.path.join(tempfile.gettempdir(), "m95-resample-report-backup.md")
    shutil.copy2(REPORT, backup)
    print(f"backed up report to {backup}")

    rc, _ = run_verifier()
    print(f"\nbaseline (unmutated): exit {rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        print("*** the report is already failing; this control cannot run ***")
        return 2

    failures = 0
    try:
        for old, new, name in MUTATIONS:
            src = open(backup, encoding="utf-8").read()
            n = src.count(old)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT UNIQUE for {name!r}: found {n} occurrences.\n"
                    f"  A control anchored on a non-unique string proves nothing.\n  anchor: {old!r}"
                )
            open(REPORT, "w", encoding="utf-8").write(src.replace(old, new))
            rc, out = run_verifier()
            ok = rc != 0
            print(f"  mutate {name:26s} -> exit {rc}  {'RED (correct)' if ok else 'GREEN (CONTROL FAILED)'}")
            if not ok:
                failures += 1
                print("    " + "\n    ".join(out.strip().splitlines()[-6:]))
    finally:
        shutil.copy2(backup, REPORT)
        print(f"\nrestored report from {backup}")

    rc, _ = run_verifier()
    print(f"after restore: exit {rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        print("*** restore did not return the report to a passing state ***")
        return 2

    print("\n" + ("NEGATIVE CONTROL PASSED" if failures == 0 else f"{failures} MUTATIONS WENT UNDETECTED"))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
