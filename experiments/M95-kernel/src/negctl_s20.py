"""Negative control for verify_s20.py.

A verifier that has only ever been shown passing is a claim about nothing. This
plants five defects the verifier is supposed to catch, one at a time, and
requires a RED on each.

Every mutation is anchored on a string that lies WITHIN A SINGLE LINE and is
UNIQUE in the file, and the script hard-errors if either condition fails. Both
guards were paid for: an earlier control in this milestone silently mutated the
wrong occurrence because a bare token matched elsewhere, and another hard-errored
because its anchor spanned a line break in wrapped prose.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "docs" / "research" / "M95-kernel.md"
VERIFY = Path(__file__).resolve().parent / "verify_s20.py"

MUTATIONS = [
    ("NOW cost last digit",
     "| NOW | +0.1813 | 0.0031 |",
     "| NOW | +0.1814 | 0.0031 |"),
    ("FIX cost last digit",
     "| FIX | +0.1855 | 0.0017 |",
     "| FIX | +0.1856 | 0.0017 |"),
    ("SNAP near-integer, the P1 power control",
     "| SNAP | -0.0003 | 0.0005 | 960 | 1.0000 | 100.00% |",
     "| SNAP | -0.0003 | 0.0005 | 960 | 1.0000 | 99.00% |"),
    ("R5 verdict flipped against the JSON",
     "**NOT A LEVER**, and note the direction",
     "**A REAL LEVER**, and note the direction"),
    ("derived 1:1 view arithmetic",
     "at 1:1, a **107.36%** view of the data",
     "at 1:1, a **107.35%** view of the data"),
]


def run_verifier():
    r = subprocess.run([sys.executable, str(VERIFY)], capture_output=True, cwd=ROOT)
    out = r.stdout.decode("utf-8", "replace")
    bad = 0
    for line in out.splitlines():
        if line.strip().startswith("BAD"):
            bad += 1
    return r.returncode, bad


def main():
    original = REPORT.read_bytes()
    backup = Path(tempfile.gettempdir()) / "M95-kernel.md.s20.bak"
    backup.write_bytes(original)
    print(f"backed up {len(original)} bytes to {backup}\n")

    text = original.decode("utf-8")
    for _, old, _ in MUTATIONS:
        if "\n" in old:
            sys.exit(f"ANCHOR SPANS A LINE BREAK: {old!r}")
        n = text.count(old)
        if n != 1:
            sys.exit(f"MUTATION TARGET NOT UNIQUE ({n} occurrences): {old!r}")

    rc, bad = run_verifier()
    print(f"baseline: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        REPORT.write_bytes(original)
        sys.exit("baseline is not GREEN; refusing to run the control")

    caught = 0
    try:
        for label, old, new in MUTATIONS:
            REPORT.write_text(text.replace(old, new, 1), encoding="utf-8")
            rc, bad = run_verifier()
            if rc != 0 and bad > 0:
                print(f"  CAUGHT  {label:<45} rc={rc}  BAD={bad}")
                caught += 1
            else:
                print(f"  MISSED  {label:<45} rc={rc}  BAD={bad}")
            REPORT.write_bytes(original)
    finally:
        REPORT.write_bytes(original)

    same = REPORT.read_bytes() == original
    print(f"\nrestored byte-identical: {same}")
    rc, _ = run_verifier()
    print(f"post-restore: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    print(f"\nnegative control: {caught}/{len(MUTATIONS)} planted defects caught")
    if not same:
        shutil.copyfile(backup, REPORT)
        sys.exit("RESTORE FAILED -- report recovered from the backup")
    return 0 if (caught == len(MUTATIONS) and rc == 0) else 1


if __name__ == "__main__":
    sys.exit(main())
