"""Commission the pin: plant a known-potent sabotage and REQUIRE red.

An uncommissioned pin and an inert plant both look like one green.  This
neuters the geometric cap in `SelectionScale::from_silhouettes` -- the single
line that makes the window collapse at a silhouette, i.e. the whole shipped
fix -- and requires that the named behavioural test goes RED.  If it stays
green, the pin is not resolving to its own sources and nothing measured from
it means anything.
"""

import pathlib
import shutil
import subprocess
import sys

PIN = pathlib.Path(r"C:\dev\strehl-pin-1ba6dce")
SRC = PIN / "crates" / "strehl-core" / "src" / "edgeaware.rs"
BACKUP = pathlib.Path(r"C:\Users\chris\AppData\Local\Temp") / "edgeaware.commission.rs"
CARGO = pathlib.Path.home() / ".cargo" / "bin" / "cargo.exe"

# Unique full-line anchor. Never a bare replace-count-1 on a short token.
ANCHOR = "                if !capped[i] && hi[i] - lo[i] > tau {"
SABOTAGE = "                if false && hi[i] - lo[i] > tau {"

TEST = "the_window_collapses_at_a_silhouette_and_is_shipped_size_away_from_one"


def run_test():
    p = subprocess.run(
        [str(CARGO), "test", "-p", "strehl-core", "--release", TEST],
        cwd=PIN, capture_output=True, text=True,
        env={**__import__("os").environ, "CARGO_TARGET_DIR": str(PIN / "target")},
    )
    return p.returncode, (p.stdout + p.stderr)


def main():
    original = SRC.read_text(encoding="utf-8")
    n = original.count(ANCHOR)
    if n != 1:
        sys.exit(f"MUTATION TARGET NOT FOUND: anchor occurs {n} times, need exactly 1")
    shutil.copyfile(SRC, BACKUP)
    try:
        rc, out = run_test()
        if rc != 0:
            sys.exit(f"BASELINE ALREADY RED (rc={rc}); pin is not usable\n{out[-2500:]}")
        print(f"baseline GREEN: {TEST} passes on the clean pin")

        SRC.write_text(original.replace(ANCHOR, SABOTAGE), encoding="utf-8")
        rc, out = run_test()
        if rc == 0:
            sys.exit(
                "COMMISSION FAILED: the cap was neutered and the test still "
                "passed. The pin is not compiling its own sources, or the test "
                "does not actually exercise the cap. Nothing measured from this "
                "pin can be trusted.\n" + out[-2500:]
            )
        print(f"sabotage RED (rc={rc}): the pin resolves to its own sources")
        for line in out.splitlines():
            if "FAILED" in line or "failures:" in line or "panicked" in line:
                print("   " + line.strip()[:160])
    finally:
        shutil.copyfile(BACKUP, SRC)
        print("restored from the temp copy (never git checkout --)")

    rc, out = run_test()
    if rc != 0:
        sys.exit(f"RESTORE FAILED, pin left dirty (rc={rc})\n{out[-1500:]}")
    print("restore verified GREEN -- pin COMMISSIONED")


if __name__ == "__main__":
    main()
