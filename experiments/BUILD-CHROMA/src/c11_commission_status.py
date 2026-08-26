"""Commission the CA status-line tests: plant the ORIGINAL defect, require RED.

A test that passes proves nothing until it has been shown to fail on the bug it
claims to catch. V-CA's defect was specific -- the printed state was derived from
the switch instead of from the resolved profile -- so the sabotage has to be that
exact inversion, not merely "break the string".

Two mutations, one per direction of the original inversion:

  M1  the corrected render printed as off   (row 1: silent + gear matched)
  M2  the uncorrected render printed as CORRECTING, profile "off"  (row 2)

Each mutation is anchored on a UNIQUE FULL-LINE string and the script hard-errors
if the anchor does not land -- a mutation that silently fails to apply produces a
green run that reads exactly like a passing test.

The file is restored from a copy made in %TEMP% before any edit. Never
`git checkout --`, which reverts to HEAD and would discard concurrent work.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = REPO / "crates" / "strehl-core" / "src" / "optics.rs"
CARGO = pathlib.Path.home() / ".cargo" / "bin" / "cargo.exe"

# (name, what it plants, unique anchor, replacement)
MUTATIONS = [
    (
        "M1 corrected render reported as off",
        'the "default on" row prints the pre-fix "off (STREHL_FIX_CA unset)"',
        '                "CORRECTING, profile {:?} (gear matched {body:?} / lens {lens_type3}; default on)",\n',
        '                "off (STREHL_FIX_CA unset){}{body}{lens_type3}",\n',
    ),
    (
        "M2 uncorrected render reported as CORRECTING",
        'the explicit-off row prints the pre-fix \'CORRECTING, profile "off"\'',
        '                write!(f, "off (operator asked for {setting:?})")\n',
        '                write!(f, "CORRECTING, profile {setting:?}")\n',
    ),
]

TESTS = [
    "the_status_line_matches_the_decision_on_every_row",
    "the_reported_profile_is_the_applied_profile",
]


def run_tests():
    """Return (passed, failed, raw) for the two status tests."""
    out = subprocess.run(
        [str(CARGO), "test", "-p", "strehl-core", "--lib", "optics::tests::the_"],
        cwd=REPO, capture_output=True, text=True,
    )
    txt = out.stdout + out.stderr
    got = {}
    for t in TESTS:
        if f"{t} ... ok" in txt:
            got[t] = "PASS"
        elif f"{t} ... FAILED" in txt:
            got[t] = "FAIL"
        else:
            got[t] = "ABSENT"
    return got, txt


def restore(backup, dst):
    """Restore and FORCE the mtime forward.

    `shutil.copy2` preserves the source mtime, which here is the pre-mutation
    timestamp -- older than the artifact cargo built from the mutated source.
    Cargo decides staleness by mtime, so it skips the rebuild and silently runs
    the MUTATED binary against the RESTORED source. Measured: after a clean
    restore the suite still failed with `CORRECTING, profile "off"` -- M2's
    planted output -- from a file that no longer contained it.

    A stale binary is the worst kind of green: it is a real test run, on real
    code, that is not the code in front of you.
    """
    shutil.copy2(backup, dst)
    os.utime(dst, None)


def main():
    backup = pathlib.Path(tempfile.gettempdir()) / "optics.rs.bak"
    shutil.copy2(SRC, backup)
    print(f"backup -> {backup}")

    print("\n" + "=" * 78)
    print("BASELINE (unmutated) -- both must PASS")
    print("=" * 78)
    base, _ = run_tests()
    for k, v in base.items():
        print(f"  {v:6}  {k}")
    if set(base.values()) != {"PASS"}:
        print("\nBASELINE NOT GREEN -- aborting before mutating.")
        return 1

    results = []
    try:
        for name, plants, anchor, repl in MUTATIONS:
            original = SRC.read_text(encoding="utf-8")
            n = original.count(anchor)
            if n != 1:
                raise SystemExit(
                    f"MUTATION TARGET NOT FOUND for {name}: anchor occurs {n} times, "
                    f"expected exactly 1. Refusing to run -- a mutation that does not "
                    f"land reads as a passing test.\nanchor={anchor!r}"
                )
            SRC.write_text(original.replace(anchor, repl, 1), encoding="utf-8")
            print("\n" + "=" * 78)
            print(f"{name}")
            print(f"  plants: {plants}")
            print("=" * 78)
            got, txt = run_tests()
            caught = any(v == "FAIL" for v in got.values())
            for k, v in got.items():
                print(f"  {v:6}  {k}")
            if not caught and "error" in txt.lower():
                print("  (did not compile -- that is not a caught defect)")
            print(f"  --> {'RED, defect caught' if caught else 'GREEN, DEFECT MISSED'}")
            results.append((name, caught))
            SRC.write_text(original, encoding="utf-8")
            os.utime(SRC, None)
    finally:
        restore(backup, SRC)
        print(f"\nrestored from {backup}")

    print("\n" + "=" * 78)
    print("COMMISSIONING RESULT")
    print("=" * 78)
    for name, caught in results:
        print(f"  {'CAUGHT ' if caught else 'MISSED '} {name}")
    ok = all(c for _, c in results)
    print(f"\n{sum(c for _, c in results)}/{len(results)} planted defects caught")
    print("The tests can go red on the bug they claim to catch."
          if ok else "AT LEAST ONE DEFECT WAS MISSED -- the tests are not trustworthy.")

    post, _ = run_tests()
    print(f"\npost-restore: {', '.join(f'{v} {k}' for k, v in post.items())}")
    return 0 if ok and set(post.values()) == {"PASS"} else 1


if __name__ == "__main__":
    sys.exit(main())
