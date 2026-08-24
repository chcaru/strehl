"""P6 -- prove the new sign tests can actually fail.

Nine unit tests were green while `optics.rs` shipped a globally inverted
correction sign.  Three of them hardcoded the implementation's own expression,
and the one test that did check direction checked it against `displacement_at`,
which is built from the same convention.  That suite could not have gone red.

So the repair is not complete until the replacement tests are shown to fail on
the defect they exist to catch.  This plants the old convention back into
`compose` and asserts the suite turns red -- and names WHICH tests turn red, so
a mutation that is caught only by an unrelated test does not read as a pass.

Bars, registered here before the run:

  M1  the mutated crate FAILS.  Exit code asserted to be exactly 101 (cargo's
      test-failure code), not merely "nonzero" -- rule 47 as amended.
  M2  `a_planted_magnification_is_actually_undone` is among the failures.  This
      is the test written specifically for this defect; if the mutation is
      caught only by the older tests, the new one is not earning its place.
  M3  `the_pull_maps_wanted_to_sampled_not_the_reverse` is among the failures.
  M4  the restored crate passes again with exactly 282 tests, RC exactly 0.
  M5  the three translation-datum mutants that SURVIVED independent
      verification (sign flip, x10, axis swap) are now each killed, and killed
      specifically by `the_shipped_coefficients_match_the_fit_they_claim` --
      not incidentally by some unrelated test.

Falsifier: if M1 fails -- i.e. the mutated crate is still green -- then the
tests are still sign-symmetric and the repair has NOT been demonstrated.

The file is backed up to a scratch copy and restored from that copy.  It is
never reverted with `git checkout --`.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

SRC = pathlib.Path(
    r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-core\src\optics.rs"
)
REPO = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")

# Unique full-line anchor.  Bare substring replacement is how a mutation
# silently lands somewhere other than where you think it did.
ANCHOR = "        let s = 1.0 + eps;\n"
MUTANT = "        let s = 1.0 / (1.0 + eps);\n"

EXPECT_RED = [
    "a_planted_magnification_is_actually_undone",
    "the_pull_maps_wanted_to_sampled_not_the_reverse",
]

# Mutants that SURVIVED independent verification: flipping the shipped
# translation's signs, scaling it 10x, and swapping its axes each left the suite
# at 281 passed / 0 failed.  Every test that touched translation re-read
# `p.translation` and recomputed its own expectation from it, so the suite was
# self-consistent for any non-zero pair.  `the_shipped_coefficients_match_the_fit_they_claim`
# exists to close that hole, and these arms are what prove it did.
SURVIVOR_ANCHOR = "    translation: (0.6294, -0.4240),\n"
SURVIVORS = [
    ("sign flip", "    translation: (-0.6294, 0.4240),\n"),
    ("x10 magnitude", "    translation: (6.294, -4.240),\n"),
    ("axis swap", "    translation: (-0.4240, 0.6294),\n"),
]
SURVIVOR_KILLER = "the_shipped_coefficients_match_the_fit_they_claim"


CARGO_BIN = pathlib.Path.home() / ".cargo" / "bin" / "cargo.exe"


def cargo(args):
    env = dict(os.environ)
    env["PATH"] = str(CARGO_BIN.parent) + os.pathsep + env["PATH"]
    env["CARGO_TARGET_DIR"] = r"C:\dev\strehl-out\M107-chroma\cargo-target-m107"
    exe = str(CARGO_BIN) if CARGO_BIN.exists() else (shutil.which("cargo") or "cargo")
    p = subprocess.run(
        [exe] + args,
        cwd=str(REPO),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main():
    raw = SRC.read_text(encoding="utf-8")
    n = raw.count(ANCHOR)
    if n != 1:
        raise SystemExit(
            f"MUTATION TARGET NOT FOUND: anchor occurs {n} times, expected 1. "
            "Refusing to run -- an unanchored mutation proves nothing."
        )

    backup = pathlib.Path(tempfile.gettempdir()) / "M107-optics-backup.rs"
    shutil.copy2(SRC, backup)
    print(f"backed up to {backup}")

    results = {}
    try:
        SRC.write_text(raw.replace(ANCHOR, MUTANT), encoding="utf-8")
        # Confirm the mutation is actually on disk before believing the result.
        after = SRC.read_text(encoding="utf-8")
        assert MUTANT in after and ANCHOR not in after, "mutation did not land"

        code, out = cargo(["test", "-p", "strehl-core", "--lib"])
        results["mutant_code"] = code
        red = [t for t in EXPECT_RED if f"{t} ... FAILED" in out]
        results["mutant_red"] = red
        results["mutant_tail"] = [
            ln for ln in out.splitlines() if "test result:" in ln
        ]
    finally:
        shutil.copy2(backup, SRC)
        # copy2 preserves the BACKUP's mtime, which is older than the artifacts
        # cargo built from the mutant -- so cargo considers the restored file
        # up to date and re-runs the mutant binary.  The first run of this
        # harness reported the clean arm as red for exactly that reason.  Stamp
        # the file to now so the restore is visible to the build system.
        os.utime(SRC, None)
        restored = SRC.read_text(encoding="utf-8")
        assert restored == raw, "RESTORE FAILED -- file differs from the backup"
        print("restored, byte-identical to the pre-mutation file, mtime stamped")

    code, out = cargo(["test", "-p", "strehl-core", "--lib"])
    results["clean_code"] = code
    results["clean_tail"] = [ln for ln in out.splitlines() if "test result:" in ln]

    print()
    print("=" * 66)
    print(f"M1  mutated exit code   EXIT={results['mutant_code']}  (want exactly 101)")
    m1 = results["mutant_code"] == 101
    print(f"    M1 {'PASS' if m1 else 'FAIL'}")

    for bar, name in (("M2", EXPECT_RED[0]), ("M3", EXPECT_RED[1])):
        hit = name in results["mutant_red"]
        print(f"{bar}  {name}: {'RED' if hit else 'still green'}  "
              f"{'PASS' if hit else 'FAIL'}")

    print(f"    mutated: {'; '.join(results['mutant_tail'])}")
    print(f"M4  clean exit code     EXIT={results['clean_code']}  (want exactly 0)")
    print(f"    clean:   {'; '.join(results['clean_tail'])}")
    m4 = results["clean_code"] == 0 and any(
        "282 passed" in ln for ln in results["clean_tail"]
    )
    print(f"    M4 {'PASS' if m4 else 'FAIL'}")

    ok = m1 and all(n in results["mutant_red"] for n in EXPECT_RED) and m4

    # M5 -- the three mutants that survived independent verification.
    print()
    print("M5  translation-datum mutants (all three survived verification)")
    if raw.count(SURVIVOR_ANCHOR) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND: translation anchor is not unique")
    m5 = True
    for label, mutant in SURVIVORS:
        try:
            SRC.write_text(raw.replace(SURVIVOR_ANCHOR, mutant), encoding="utf-8")
            assert mutant in SRC.read_text(encoding="utf-8"), "mutation did not land"
            code, out = cargo(["test", "-p", "strehl-core", "--lib"])
        finally:
            shutil.copy2(backup, SRC)
            os.utime(SRC, None)
            assert SRC.read_text(encoding="utf-8") == raw, "RESTORE FAILED"
        killed = f"{SURVIVOR_KILLER} ... FAILED" in out
        hit = code == 101 and killed
        m5 = m5 and hit
        print(f"    {label:<16} EXIT={code:<4} killed by {SURVIVOR_KILLER}: "
              f"{'yes' if killed else 'NO'}  {'PASS' if hit else 'FAIL'}")
    print(f"    M5 {'PASS' if m5 else 'FAIL'}")
    ok = ok and m5

    print("=" * 66)
    print("ALL BARS PASS" if ok else "AT LEAST ONE BAR FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
