"""Negative control for the fact-1843 insert.

A green lint means nothing unless the lint can go red on the defect being
guarded against. This plants the exact defect add_1843.py refuses to write -- a
raw `|` inside a fact cell, which corpus_lint calls S1 and which silently
DISCARDS every cell past the header count in the rendered table -- and requires
the lint to fail.

The file is regressed from a $env:TEMP copy taken here, never from git: a
`git checkout --` reverts to HEAD and would destroy concurrent uncommitted work
by the other lanes sharing this tree.

The mutation is anchored on a unique full-line prefix and hard-errors if it does
not land exactly once. A mutation that silently fails to apply produces a green
that is a statement about nothing.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SYN = ROOT / "docs" / "research" / "SYNTHESIS.md"
ANCHOR = "| 1843 | MEASURED | V-NEVERWORSE |"


def lint() -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "corpus_lint.py"), "--root", str(ROOT)],
        capture_output=True,
    )
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def main() -> int:
    backup = Path(os.environ["TEMP"]) / "SYNTHESIS.negctl1843.md"
    shutil.copy2(SYN, backup)
    print(f"backup: {backup} ({backup.stat().st_size} bytes)")

    rc0, out0 = lint()
    print(f"[baseline]  rc={rc0}  {'GREEN' if rc0 == 0 else 'RED'}")
    if rc0 != 0:
        sys.stderr.write("baseline is already RED; the control cannot be interpreted.\n")
        return 2

    text = SYN.read_text(encoding="utf-8")
    lines = text.split("\n")
    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR)]
    if len(hits) != 1:
        sys.stderr.write(
            f"MUTATION TARGET NOT FOUND: {ANCHOR!r} matched {len(hits)} lines. "
            "Refusing to report a colour.\n"
        )
        return 2

    i = hits[0]
    original = lines[i]
    # Plant S1: a raw pipe inside the cell text, exactly what add_1843.py refuses.
    lines[i] = original.replace(
        "selection premium, not dilution".upper(),
        "SELECTION PREMIUM | NOT DILUTION",
        1,
    )
    if lines[i] == original:
        sys.stderr.write("MUTATION DID NOT CHANGE THE LINE; refusing to report a colour.\n")
        return 2

    SYN.write_text("\n".join(lines), encoding="utf-8", newline="")
    rc1, out1 = lint()
    colour = "RED" if rc1 != 0 else "GREEN"
    print(f"[planted]   rc={rc1}  {colour}")
    for ln in out1.splitlines():
        if "S1" in ln or "1843" in ln or "violation" in ln.lower():
            print(f"            {ln.strip()[:150]}")

    shutil.copy2(backup, SYN)
    rc2, _ = lint()
    print(f"[restored]  rc={rc2}  {'GREEN' if rc2 == 0 else 'RED'}")

    restored_ok = SYN.read_text(encoding="utf-8") == text
    print(f"[restored]  byte-identical to pre-mutation: {restored_ok}")

    ok = rc0 == 0 and rc1 != 0 and rc2 == 0 and restored_ok
    print()
    print("CONTROL PASSES: the lint expresses the defect" if ok else "CONTROL FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
