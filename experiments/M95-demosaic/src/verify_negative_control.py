"""Negative control for verify_report.py: prove it can go red.

Discipline 594 -- a null is a claim about the world only if the instrument could
have said otherwise, and you must SHOW it saying otherwise. "ALL CHECKS PASS" is
worth nothing until a planted one-digit defect turns it red.

Anchors are full unique strings with NO typographic glyphs, and each must land
exactly once or this script hard-errors. A bare replace(old, new, 1) that misses
would silently report the check as passing -- arm 5's F5 was exactly that, an
anchor spelling panel dimensions with ASCII 'x' where the report uses U+00D7.

The report is backed up to %TEMP% first and restored from that copy. NEVER
`git checkout --`, which reverts to HEAD and has destroyed uncommitted work on
this machine.
"""
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-demosaic.md"
VERIFY = pathlib.Path(__file__).parent / "verify_report.py"
BACKUP = pathlib.Path(os.environ["TEMP"]) / "m95-demosaic-report-backup.md"

MUTATIONS = [
    ("**+0.5737 dex louder than MHC**",
     "**+0.5738 dex louder than MHC**",
     "B1 headline last digit"),
    ("| **0.9161** |",
     "| **0.9162** |",
     "NEAREST artifact share"),
    ("synthetic ladder drives the demosaic 0.31x as hard as the real capture",
     "synthetic ladder drives the demosaic 0.32x as hard as the real capture",
     "d3 overdrive"),
]


def run():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, text=True)
    return r.returncode


def main() -> int:
    original = REPORT.read_text(encoding="utf-8")
    shutil.copy2(REPORT, BACKUP)
    print(f"backed up to {BACKUP}\n")

    failures = []
    try:
        rc = run()
        print(f"{'baseline (unmutated)':36s} rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
        if rc != 0:
            failures.append("baseline is not green")

        for old, new, name in MUTATIONS:
            n = original.count(old)
            if n != 1:
                failures.append(f"anchor for {name!r} occurs {n} times, need exactly 1")
                print(f"  MUTATION TARGET NOT FOUND ({n} hits): {name}")
                continue
            REPORT.write_text(original.replace(old, new, 1), encoding="utf-8")
            rc = run()
            ok = rc != 0
            print(f"mutated: {name:27s} rc={rc}  "
                  f"{'RED (correct)' if ok else 'GREEN (WRONG -- check is blind)'}")
            if not ok:
                failures.append(f"{name} did not turn the verifier red")
    finally:
        shutil.copy2(BACKUP, REPORT)

    rc = run()
    print(f"{'restored':36s} rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        failures.append("restore did not return the verifier to green")

    print()
    if failures:
        print("NEGATIVE CONTROL FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("NEGATIVE CONTROL PASSED (green -> red, red, red -> green)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
