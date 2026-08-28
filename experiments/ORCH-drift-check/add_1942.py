"""Bank fact 1942: the bank-before-delete ordering caught a live irreproducibility.

Auto-detects the tail and HARD-ERRORS if it is not the expected value, so a
concurrent lane's insert cannot make this append in the wrong place.
"""
import io
import re
import sys

PATH = "docs/research/SYNTHESIS.md"
EXPECT_TAIL = 1941
NEW_ID = 1942

ROW = (
    "| 1942 | MEASURED | ORCH | "
    "**ORDERING THE PURGE AS BANK-FIRST-DELETE-SECOND CAUGHT A LIVE, "
    "ABOUT-TO-HAPPEN IRREPRODUCIBILITY THAT A DELETE-FIRST ORDER WOULD HAVE "
    "MADE PERMANENT, AND THE LANE THAT FOUND IT WAS NOT THE LANE THAT CAUSED "
    "IT.** When the owner reported low disk I sent all 22 lanes a purge order "
    "whose step 1 was to write every number they still cared about into text "
    "under `experiments/<LANE>/` and step 2 was to delete, with the explicit "
    "warning that a number living only inside a TIFF about to be deleted is a "
    "number being destroyed. V-DILUTE executed step 1 and discovered that its "
    "`arms_(star).json` premium/sharpness ladders -- the evidence behind the "
    "ranked-arm table in its Addendum H -- existed **only** on D: scratch, and "
    "that they were not regenerable, because their input bundles "
    "`112MSDCF.npz` and `119MSDCF.npz` had already been deleted at 22:48 by a "
    "different lane with no copy on either drive. Had V-DILUTE obeyed a "
    "delete-first order, a published ranked table would have joined V-RIM's "
    "5-of-14 rim result in the class of results nobody can ever check. It "
    "banked 39 files / 177 KB instead and committed them. **THE SHAPE IS NOT "
    "CARELESSNESS BUT COUPLING: ONE LANE'S CLEANUP SILENTLY DESTROYED ANOTHER "
    "LANE'S ABILITY TO REGENERATE, AND NEITHER LANE COULD SEE THE DEPENDENCY "
    "FROM ITS OWN SIDE.** In a shared working tree, regenerability is not a "
    "property a lane can assert about its own artifacts -- it is a property of "
    "the whole tree at the moment of deletion, and it decays without notice. "
    "Corroboration from the same round, in the opposite direction: "
    "BUILD-SOFTGATE had already deleted its scratch before the order arrived, "
    "and rather than assert it was fine it grepped **HEAD** (not the working "
    "tree) for twelve key values -- four render hashes, the contaminated hash, "
    "both freeze hashes, two pixel counts, three depth figures, the inertness "
    "denominator and the second-pass timing -- and got True on all twelve. "
    "That is the correct response to the same risk: check, do not assert. "
    "The discipline earned: **a lane may only call an artifact regenerable "
    "after naming the specific inputs the regeneration needs and confirming "
    "those inputs still exist**, and the safe default for anything whose "
    "inputs are outside the lane's own directory is to bank it as text. "
    "Reproduce: read `experiments/V-DILUTE/banked/README` and "
    "`experiments/BUILD-SOFTGATE/results.tsv`. |"
)


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()

    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows found in %s" % PATH)
    tail = max(ids)
    if tail != EXPECT_TAIL:
        raise SystemExit(
            "FATAL: expected tail %d, found %d. A lane inserted rows; re-derive "
            "NEW_ID before running this." % (EXPECT_TAIL, tail)
        )
    if NEW_ID in ids:
        raise SystemExit("FATAL: row %d already present" % NEW_ID)

    body = ROW[ROW.index("**"):]
    if body.count("*") % 2 != 0:
        raise SystemExit("FATAL: odd asterisk count (%d)" % body.count("*"))

    anchor_start = src.rindex("| %d |" % tail)
    anchor_end = src.index("\n", anchor_start)
    anchor = src[anchor_start:anchor_end]

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
