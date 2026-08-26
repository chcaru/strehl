"""Negative control for the RENDER_ENV fix: prove the new entry is load-bearing.

Adding a string to a list and watching the tests pass proves nothing -- they
passed before. The claim is that WITHOUT the entry, an ambient STREHL_FIX_CA
renders a different pipeline than the row records and the freeze fails. That
claim is only tested by removing it and requiring RED.

  arm A  entry ABSENT,  ambient STREHL_FIX_CA=off  -> must FAIL
  arm B  entry PRESENT, ambient STREHL_FIX_CA=off  -> must PASS  (already run)

The mutation is anchored on a unique full-line string and hard-errors if it does
not land, because a mutation that silently misses reads as a green arm and would
have me record the opposite conclusion.

The file is restored from a $env:TEMP copy, never with `git checkout --`.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

REPO = pathlib.Path(r"C:\dev\blog\death-of-software\projects\strehl")
SRC = REPO / "crates" / "strehl-cli" / "tests" / "byte-freeze.rs"
CARGO = pathlib.Path(os.environ["USERPROFILE"]) / ".cargo" / "bin" / "cargo.exe"
TARGET = r"C:\dev\strehl-out\BUILD-RENDER-target"

ANCHOR = '    "STREHL_FIX_CA",\n];'
PATCHED = "];"


def run_freeze():
    env = dict(os.environ)
    env["CARGO_TARGET_DIR"] = TARGET
    env["STREHL_FREEZE_REQUIRE"] = "1"
    env["STREHL_FIX_CA"] = "off"          # the ambient pollution
    b = subprocess.run(
        [str(CARGO), "test", "--release", "-p", "strehl-cli", "--test", "byte-freeze"],
        cwd=REPO, env=env, capture_output=True,
    )
    out = (b.stdout + b.stderr).decode("utf-8", errors="replace")
    line = next((l.strip() for l in out.splitlines() if "test result:" in l), "(no result line)")
    return b.returncode, line


def main():
    backup = pathlib.Path(tempfile.gettempdir()) / "byte-freeze.rs.negctl-backup"
    shutil.copy2(SRC, backup)
    print(f"backed up to {backup}")

    original = SRC.read_text(encoding="utf-8")
    assert original.count(ANCHOR) == 1, (
        f"MUTATION TARGET NOT FOUND ({original.count(ANCHOR)}x) -- refusing to run a "
        "control whose sabotage may not have landed"
    )

    rc = 1
    try:
        SRC.write_text(original.replace(ANCHOR, PATCHED, 1), encoding="utf-8")
        os.utime(SRC, None)
        assert '"STREHL_FIX_CA"' not in SRC.read_text(encoding="utf-8"), "sabotage did not land"
        print("arm A: entry REMOVED, ambient STREHL_FIX_CA=off ... building + running")
        code_a, line_a = run_freeze()
        print(f"       exit={code_a}  {line_a}")
    finally:
        shutil.copy2(backup, SRC)
        os.utime(SRC, None)          # AGENTS.md rule 33: else cargo reuses the stale artifact
        time.sleep(0.5)
        restored = SRC.read_text(encoding="utf-8")
        assert restored == original, "RESTORE FAILED -- file does not match the pre-mutation copy"
        print("restored from the TEMP copy; byte-identical to the original")

    ok = code_a != 0
    print()
    print(f'  [{"PASS" if ok else "FAIL"}] entry absent + ambient pollution => freeze test FAILS')
    print()
    if ok:
        print("COMMISSIONED: the RENDER_ENV entry is load-bearing. Without it an ambient")
        print("STREHL_FIX_CA silently renders a different pipeline than the row records.")
    else:
        print("NOT COMMISSIONED: the test passed without the entry, so the entry is inert")
        print("and my claim about it is wrong.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
