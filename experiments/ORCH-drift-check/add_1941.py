"""Bank fact 1941: DELIVER-V6 enumerated its work list from a stale OUTPUT tree.

Auto-detects the fact-table tail and HARD-ERRORS if it is not the expected value,
so a concurrent lane's insert cannot silently make this script append in the wrong
place or renumber over someone else's row.
"""
import io
import re
import sys

PATH = "docs/research/SYNTHESIS.md"
EXPECT_TAIL = 1940
NEW_ID = 1941

ROW = (
    "| 1941 | MEASURED | ORCH | "
    "**THE DELIVERABLE RENDERED 26 OF 33 SUBJECTS BECAUSE IT BUILT ITS WORK LIST BY "
    "LISTING A STALE OUTPUT DIRECTORY INSTEAD OF THE SOURCE TREE, SO THE SEVEN "
    "SUBJECTS THE OWNER ADDED MOST RECENTLY WERE STRUCTURALLY INVISIBLE TO IT AND NO "
    "ERROR WAS EVER RAISED.** Measured by reading the deliverable's own manifest: "
    "`C:\\dev\\strehl-out\\DELIVER-V6\\masters\\MANIFEST.txt` line 10 reads "
    "`subjects : 26 (from C:\\dev\\strehl-out\\ORCH-FAITHFUL\\faithful)`. That path is "
    "an OUTPUT tree written by an earlier lane, not `D:\\personal\\macro`, which is the "
    "read-only source. Diffing the source against the masters named the seven missing "
    "subjects exactly: `chia-seeds-cpl` (130 frames), `dime-flat-narrow-slices-cpl` "
    "(207), `duck-tape-side-layers-cpl` (197), `maldon-sea-salt-cpl` (255), "
    "`medication-pill-cpl` (146), `pottery-art-glazed-cpl` (123), "
    "`unpopped-popcorn-kernels-cpl` (234); 1292 frames in total. The failure is silent "
    "by construction: enumerating a directory that exists and contains 26 valid entries "
    "succeeds, and a count of 26 is indistinguishable from a correct count of 26 unless "
    "you already know the answer is 33. The stall presented as completion. "
    "**THIS IS THE THIRD INDEPENDENT OCCURRENCE OF ONE DEFECT SHAPE: AN INSTRUMENT'S "
    "INPUT PATH IS PART OF ITS CALIBRATION.** Prior two: `SEAL_DIR` pointed at "
    "`acceptance/SHIP-V4` (a superseded output set) and `rimaxis.py` line 52 read a "
    "scratch tree that a later purge had removed. In all three the code was correct, "
    "the path was stale, and the run went green. The discipline this earns: a lane that "
    "enumerates work MUST enumerate from the declared read-only source of truth and MUST "
    "print the enumeration root next to the count, so a reader can audit the count "
    "against its provenance in one line rather than trusting it. `render7.ps1` was "
    "written to do exactly that and prints "
    "`enumerated from: D:\\personal\\macro   <-- NOT from an output tree`. "
    "Reproduce: read the manifest header, then compare "
    "`Get-ChildItem D:\\personal\\macro -Directory` against "
    "the `.tiff` basenames under the masters directory. |"
)


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()

    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows found in %s" % PATH)
    tail = max(ids)
    if tail != EXPECT_TAIL:
        raise SystemExit(
            "FATAL: expected tail %d, found %d. Another lane inserted rows; "
            "re-read the table and re-derive NEW_ID before running this."
            % (EXPECT_TAIL, tail)
        )
    if NEW_ID in ids:
        raise SystemExit("FATAL: row %d already present" % NEW_ID)

    anchor_start = src.rindex("| %d |" % tail)
    anchor_end = src.index("\n", anchor_start)
    anchor = src[anchor_start:anchor_end]

    body = ROW[ROW.index("**"):]
    if body.count("*") % 2 != 0:
        raise SystemExit("FATAL: odd asterisk count in new row (%d)" % body.count("*"))

    cells = ROW.split(" | ")
    if len(cells) < 4:
        raise SystemExit("FATAL: new row does not have the 4 leading cells")

    out = src.replace(anchor, anchor + "\n" + ROW, 1)
    if out == src:
        raise SystemExit("FATAL: anchor did not land; nothing written")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    check = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", check, re.M)]
    if max(ids2) != NEW_ID or len(ids2) != len(ids) + 1:
        raise SystemExit("FATAL: post-write verification failed")
    print("OK: fact %d written; rows %d -> %d" % (NEW_ID, len(ids), len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
