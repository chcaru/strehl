"""Commission the acuity tests: plant sabotages and require RED.

`57e4554` deleted this term partly because its test suite kept passing without
it -- nothing then in the file could tell the difference. So the restored term
does not get to arrive with three green tests and no evidence that green means
anything.

Two independent sabotages, because the two tests guard different properties:

  A. `min` -> plain assignment. The term may now RAISE a radius, overturning a
     decision the veto or the silhouette cap already made.
     Must break `the_acuity_term_only_ever_tightens`.

  B. `>=` -> `<=` in the floor comparison. The rule now hands the SMALLEST
     window to the WEAKEST peak -- the exact inversion that would show up as
     noise rather than as a crash.
     Must break `a_stronger_peak_buys_a_smaller_window`.

Each mutation is anchored on a unique full-line string and this script
hard-errors if the anchor does not land exactly once: a `replace` that silently
matched nothing prints the same green as a working test.

The file is restored from a copy in TEMP, never with `git checkout --`, which
reverts to HEAD and would destroy the uncommitted work of any agent sharing
this tree.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = ROOT / "crates" / "strehl-core" / "src" / "edgeaware.rs"
CARGO = Path.home() / ".cargo" / "bin" / "cargo.exe"

TESTS = [
    "the_acuity_term_only_ever_tightens",
    "a_peak_that_clears_no_noise_floor_keeps_the_shipped_window",
    "a_stronger_peak_buys_a_smaller_window",
]

MUTATIONS = [
    (
        "the min is dropped: acuity may now RAISE a radius",
        "            *lv = (*lv).min(noise_level);",
        "            *lv = noise_level;",
        "the_acuity_term_only_ever_tightens",
    ),
    (
        "the floor comparison is inverted: weakest peak gets smallest window",
        "                if excess[i] >= *n {",
        "                if excess[i] <= *n {",
        "a_stronger_peak_buys_a_smaller_window",
    ),
    (
        "the term is made inert: it computes a level and discards it",
        "            *lv = (*lv).min(noise_level);",
        "            let _ = noise_level;",
        "the_acuity_term_only_ever_tightens",
    ),
]


def run_tests() -> tuple[bool, str, int]:
    p = subprocess.run(
        [str(CARGO), "test", "-p", "strehl-core", "--release", "--", *TESTS],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = p.stdout + p.stderr
    passed = sum(1 for t in TESTS if f"test edgeaware::tests::{t} ... ok" in out)
    # A filter that matches nothing prints `ok. 0 passed`, which this build has
    # already misread as a pass twice. Require the exact count.
    return p.returncode == 0 and passed == len(TESTS), out, passed


def main() -> int:
    original = SRC.read_text(encoding="utf-8")
    backup = Path(tempfile.gettempdir()) / "edgeaware.rs.acuity-commission"
    shutil.copy2(SRC, backup)
    print(f"backup -> {backup}")

    ok, out, n = run_tests()
    if not ok:
        print(f"BASELINE NOT GREEN ({n}/{len(TESTS)}) -- nothing to commission")
        print("\n".join(l for l in out.splitlines() if "test result" in l))
        return 2
    print(f"baseline GREEN ({n}/{len(TESTS)})\n")

    failures = 0
    for label, anchor, sab, expect in MUTATIONS:
        count = original.count(anchor)
        if count != 1:
            print(f"MUTATION TARGET NOT FOUND [{label}]: anchor occurs {count} times, expected 1")
            failures += 1
            continue
        try:
            SRC.write_text(original.replace(anchor, sab, 1), encoding="utf-8")
            ok, out, _ = run_tests()
            broke = f"test edgeaware::tests::{expect} ... ok" not in out
            if ok or not broke:
                print(f"  FAILED   [{label}] -- {expect} stayed GREEN")
                failures += 1
            else:
                print(f"  RED      [{label}] -> {expect} broke, as required")
        finally:
            # `copy2` restores the BACKUP's mtime, older than the artifact cargo
            # just built from the sabotaged source, so cargo skips the rebuild
            # and re-runs the SABOTAGED binary. That produced a false "still red
            # after restore" once already on this project.
            shutil.copy(backup, SRC)
            SRC.touch()

    ok, out, n = run_tests()
    print(f"\nGREEN after restore ({n}/{len(TESTS)})" if ok else "\nSTILL RED AFTER RESTORE")
    for l in out.splitlines():
        if "test result" in l:
            print("   " + l.strip())
    if failures:
        print(f"\nCOMMISSION FAILED: {failures} of {len(MUTATIONS)} sabotages went undetected")
    else:
        print(f"\nCOMMISSIONED: {len(MUTATIONS)}/{len(MUTATIONS)} sabotages caught")
    return 1 if failures or not ok else 0


if __name__ == "__main__":
    sys.exit(main())
