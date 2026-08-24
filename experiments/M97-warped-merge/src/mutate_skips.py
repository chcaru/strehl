"""M97 bar D2b -- RED control for the refused-frame drop.

Removes the three `is_refused` skips from merge_cmd.rs so the build reproduces
the PRE-FIX defect (one refused frame aborts the whole render). The original is
saved to $env:TEMP first and restored from that copy -- never `git checkout --`,
which reverts to HEAD and would destroy concurrent uncommitted work.

Each mutation is anchored on a full-line block and the expected occurrence count
is asserted, so a miss hard-errors instead of silently producing a green run.

    python mutate_skips.py break    # save original, remove skips
    python mutate_skips.py restore  # restore from the TEMP copy, verify
"""

import os
import shutil
import sys

SRC = r"C:\dev\blog\death-of-software\projects\strehl\crates\strehl-cli\src\merge_cmd.rs"
BAK = os.path.join(os.environ["TEMP"], "m97-merge_cmd-FIXED.rs")

# (block text, how many times it must appear)
BLOCKS = [
    ("                if ctx.is_refused(index) {\n                    continue;\n                }\n", 2),
    ("                    if ctx.is_refused(index) {\n                        continue;\n                    }\n", 1),
]

mode = sys.argv[1]

if mode == "break":
    shutil.copy2(SRC, BAK)
    print(f"saved original -> {BAK}")
    text = open(SRC, encoding="utf-8").read()
    for block, want in BLOCKS:
        got = text.count(block)
        if got != want:
            raise SystemExit(
                f"MUTATION TARGET NOT FOUND: expected {want} occurrence(s), found {got}\n"
                f"block was:\n{block}"
            )
        text = text.replace(block, "")
    if text.count("ctx.is_refused(index)") != 0:
        raise SystemExit("MUTATION INCOMPLETE: a skip survived")
    open(SRC, "w", encoding="utf-8", newline="\n").write(text)
    print("removed 3 skips -- build is now PRE-FIX")

elif mode == "restore":
    if not os.path.exists(BAK):
        raise SystemExit(f"NO BACKUP at {BAK}; refusing to guess")
    shutil.copy2(BAK, SRC)
    text = open(SRC, encoding="utf-8").read()
    for block, want in BLOCKS:
        got = text.count(block)
        if got != want:
            raise SystemExit(f"RESTORE FAILED: expected {want}, found {got}")
    print("restored from TEMP copy; all 3 skips present")

else:
    raise SystemExit("usage: mutate_skips.py break|restore")
