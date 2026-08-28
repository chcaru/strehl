"""Bank fact 1943: a pin's directory name is an unverified claim about its binary."""
import io
import re
import sys

PATH = "docs/research/SYNTHESIS.md"
EXPECT_TAIL = 1942
NEW_ID = 1943

ROW = (
    "| 1943 | MEASURED | ORCH | "
    "**SEVEN OF THE NINE PINNED BINARIES CANNOT SAY WHAT COMMIT THEY WERE "
    "BUILT FROM, AND THE ONE PIN THAT CAN, CONTRADICTS THE DIRECTORY IT LIVES "
    "IN.** Measured by running every pin under "
    "`C:\\dev\\strehl-out\\acceptance-pins\\<hash>\\target\\release\\strehl.exe "
    "--version`. Results: `bd33ebed` reports `strehl 0.0.0 (6943f04b6654)`; "
    "`d2193a55` reports `(d2193a554f29)` and agrees with its directory; "
    "`2f858c62`, `740e7056`, `9b05d0b7` and `f190a0ea` report the literal "
    "string `(unknown)`; `96b7e119`, `b9b6921e` and `e42ab13` report no hash "
    "at all. So the directory name -- a mutable filesystem path -- is the only "
    "provenance seven of nine pins have, and it is an unverified claim. "
    "**THE ONE CASE WHERE THE CLAIM COULD BE CHECKED, FAILED.** `git "
    "merge-base --is-ancestor` returns rc=0 for `6943f04b` -> `bd33ebed` and "
    "rc=1 for the reverse, so the binary in the `bd33ebed` directory was built "
    "from a strictly EARLIER commit than its label. **This instance is benign, "
    "and it is benign only because it was checked afterwards, not because "
    "anything prevented it:** `git diff --name-only 6943f04b..bd33ebed -- "
    "(star).rs Cargo.toml Cargo.lock crates/` returns empty over 2 commits, "
    "both docs/experiments only, so a rebuild at the label would give the same "
    "binary. Had one Rust commit fallen in that range, every byte-freeze and "
    "every measurement attributed to `bd33ebed` would have been silently "
    "measuring `6943f04b`, and no instrument in the tree would have noticed. "
    "This is fact 1941's shape moved from a work list to an artifact: "
    "**PROVENANCE ENCODED IN A PATH IS PROVENANCE THAT NOTHING VALIDATES.** "
    "The discipline: an artifact must carry its own identity, so the fix is a "
    "build-time commit hash that is always populated and never the literal "
    "`unknown`, plus a startup line naming it; until then, cite a pin by the "
    "SHA256 of its binary, which is immutable and now banked for all nine in "
    "`experiments/ORCH-drift-check/acceptance-pin-binaries.txt`. Reproduce: "
    "loop the nine pins calling `--version`, then `git merge-base "
    "--is-ancestor` each reported hash against its directory name. |"
)


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()
    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows found")
    tail = max(ids)
    if tail != EXPECT_TAIL:
        raise SystemExit("FATAL: expected tail %d, found %d" % (EXPECT_TAIL, tail))
    if NEW_ID in ids:
        raise SystemExit("FATAL: row %d already present" % NEW_ID)

    body = ROW[ROW.index("**"):]
    if body.count("*") % 2 != 0:
        raise SystemExit("FATAL: odd asterisk count (%d)" % body.count("*"))

    anchor_start = src.rindex("| %d |" % tail)
    anchor = src[anchor_start:src.index("\n", anchor_start)]
    out = src.replace(anchor, anchor + "\n" + ROW, 1)
    if out == src:
        raise SystemExit("FATAL: anchor did not land")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)
    check = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", check, re.M)]
    if max(ids2) != NEW_ID or len(ids2) != len(ids) + 1:
        raise SystemExit("FATAL: post-write verification failed")
    print("OK: fact %d written; rows %d -> %d" % (NEW_ID, len(ids), len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
