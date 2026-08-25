"""Commission the pin by proving the dead-ground veto is load-bearing in it.

A pin you have not sabotaged is not a pin; it is a directory you hope is a pin.
This plants one defect that neuters the veto and requires the behaviour test
that exists for it to go RED, then restores from a temp copy and requires GREEN.

The anchor is a unique full-line string and a miss is a hard error. A bare
replace(x, y, 1) that silently lands nowhere reports the same green as a
correct pin, which is the failure this file exists to rule out.
"""

import os
import pathlib
import shutil
import subprocess
import sys

PIN = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-pin-1fbf95c")
SRC = PIN / "crates" / "strehl-core" / "src" / "edgeaware.rs"
TEST = "a_guide_step_without_a_luma_step_is_dead_ground_and_must_not_collapse"
CARGO = pathlib.Path(os.environ["USERPROFILE"]) / ".cargo" / "bin" / "cargo.exe"

ANCHOR = "            let noise_range = 2.0 * sigma * (2.0 * n.ln()).sqrt();\n"
SABOTAGE = "            let noise_range = 0.0f32;\n"


def run() -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(CARGO), "test", "-p", "strehl-core", "--lib", TEST],
        cwd=PIN,
        capture_output=True,
        text=True,
    )


text = SRC.read_text(encoding="utf-8")
if text.count(ANCHOR) != 1:
    raise SystemExit(
        f"MUTATION TARGET NOT FOUND: anchor occurs {text.count(ANCHOR)} times, need 1. "
        "The pin does not contain the source this commission is about."
    )

backup = pathlib.Path(os.environ["TEMP"]) / "edgeaware.rs.commission.bak"
shutil.copy2(SRC, backup)
try:
    SRC.write_text(text.replace(ANCHOR, SABOTAGE), encoding="utf-8")
    red = run()
    if red.returncode == 0:
        raise SystemExit(
            "COMMISSION FAILED: the sabotaged pin still passes. Either the pin is "
            "not building its own sources, or the test cannot see the veto."
        )
    print(f"RED   rc={red.returncode}  (sabotage caught)")
    for line in red.stdout.splitlines():
        if TEST in line or "dead ground" in line or "panicked" in line:
            print("   ", line.strip()[:150])
finally:
    shutil.copy2(backup, SRC)
    # copy2 preserves the BACKUP's mtime, which is the original's -- older than
    # the artifacts the sabotaged build just wrote. Cargo compares mtimes, so it
    # would reuse the sabotaged object and the restore would "fail" with a
    # byte-identical result to the sabotage. Observed exactly that here.
    os.utime(SRC, None)

green = run()
if green.returncode != 0:
    raise SystemExit(f"RESTORE FAILED: rc={green.returncode}\n{green.stdout[-2000:]}")
print(f"GREEN rc={green.returncode}  (restored)")
print("\nCOMMISSIONED: the pin builds its own sources and the veto is load-bearing.")
