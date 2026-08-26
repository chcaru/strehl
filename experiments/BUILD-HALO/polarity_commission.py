"""Commission the polarity tests: plant a sabotage and require RED.

A test that has never failed is not evidence. This neuters the polarity gate --
removing only the sign comparison, so the code still compiles and every other
check still runs -- and requires the two tests to go red. Then it restores the
file and requires green again.

The file is restored from a copy in TEMP, never with `git checkout --`, which
reverts to HEAD and would destroy the uncommitted work of any agent sharing
this tree.

The mutation is anchored on a unique full-line string and this script hard-errors
if it does not land exactly once. A `replace(x, y, 1)` that silently matched
nothing would print the same green as a working gate.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "crates" / "strehl-core" / "src" / "merge.rs"
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"

TESTS = [
    "the_veil_declines_rather_than_inverting_on_a_bright_subject",
    "the_backdrop_level_is_the_dead_ground_not_a_global_quantile",
]

ANCHOR = (
    "        if !backdrop.is_finite() || !foreground.is_finite() "
    "|| !(backdrop - foreground > need) {"
)
SABOTAGE = "        if !backdrop.is_finite() || !foreground.is_finite() {"


def run_tests() -> tuple[bool, str]:
    p = subprocess.run(
        [str(CARGO), "test", "-p", "strehl-core", "--release", "--", *TESTS],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = p.stdout + p.stderr
    passed = sum(
        1 for t in TESTS if f"test merge::tests::{t} ... ok" in out
    )
    return p.returncode == 0 and passed == len(TESTS), out


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    n = text.count(ANCHOR)
    if n != 1:
        print(f"MUTATION TARGET NOT FOUND: anchor occurs {n} times, expected 1")
        return 2

    backup = Path(tempfile.gettempdir()) / "merge.rs.polarity-commission"
    shutil.copy2(SRC, backup)
    print(f"backup -> {backup}")

    try:
        SRC.write_text(text.replace(ANCHOR, SABOTAGE, 1), encoding="utf-8")
        print("sabotage planted: polarity comparison removed")
        ok, out = run_tests()
        if ok:
            print("COMMISSION FAILED -- tests stayed GREEN with the gate neutered")
            print("\n".join(l for l in out.splitlines() if "test merge" in l or "test result" in l))
            return 1
        print("RED with sabotage, as required")
        for l in out.splitlines():
            if "test merge" in l or "panicked at" in l or "must decline" in l:
                print("   " + l.strip())
    finally:
        # `copy2` would preserve the BACKUP's mtime, which is older than the
        # artifact cargo just built from the sabotaged source -- so cargo would
        # consider the crate fresh, re-run the SABOTAGED binary, and report
        # "still red after restore" on a file that is in fact correct. That
        # happened on the first run of this script. Copy without metadata and
        # stamp the file now, so the rebuild is unambiguous.
        shutil.copy(backup, SRC)
        SRC.touch()
        print("restored from backup")

    ok, out = run_tests()
    print("GREEN after restore" if ok else "STILL RED AFTER RESTORE -- file not repaired")
    for l in out.splitlines():
        if "test result" in l:
            print("   " + l.strip())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
