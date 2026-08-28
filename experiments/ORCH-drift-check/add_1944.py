"""Append fact 1944 to the SYNTHESIS fact table."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1943
NEW_ID = 1944

BODY = (
    "A name-keyed comparison is meaningless when the name is not unique across the search "
    "root: match on the whole set, not one member. Asked whether V-H2H2's 1,375 `.ARW` were "
    "copies of the protected originals, I probed each against the first file of that name "
    "anywhere under `D:\\personal\\macro` and got 0 same-size, 0 missing, 40 size mismatches, "
    "and concluded they were unique data that must not be deleted. `DSC00001.ARW` exists in "
    "every one of the 33 subject folders, so the probe compared frame 1 of one subject against "
    "frame 1 of another and the mismatch was guaranteed a priori. Re-run as a set test -- a "
    "subset is attributed to a subject only if EVERY filename in it is present there at a "
    "byte-identical size -- 22 of 22 subsets resolved with 0 unresolved (bee-3-cpl 16, "
    "113MSDCF 4, coffee-bean 2), i.e. the exact opposite conclusion, and 67.57 GB was safely "
    "reclaimed. The set test cannot make the error because a wrong subject fails on the first "
    "name it lacks. Note the failure was silent and its output was well-formed: 40 rows of "
    "real sizes, no error, no zero counts. Corollary for the whole corpus: same-name/"
    "different-size across two trees means any tool pairing them BY FILENAME silently pairs "
    "the wrong data."
)


def main() -> int:
    src = io.open(PATH, encoding="utf-8").read()

    ids = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", src, re.M)]
    if not ids:
        raise SystemExit("FATAL: no fact rows matched")
    tail = max(ids)
    if tail != EXPECTED_TAIL:
        raise SystemExit("FATAL: tail is %d, expected %d" % (tail, EXPECTED_TAIL))
    if NEW_ID in ids:
        raise SystemExit("FATAL: fact %d already present" % NEW_ID)

    if BODY.count("*") % 2 != 0:
        raise SystemExit("FATAL: odd number of '*' in body -- would break emphasis")
    if "|" in BODY:
        raise SystemExit("FATAL: '|' in body -- would break the table")

    anchor = None
    for m in re.finditer(r"^\| %d \|.*$" % tail, src, re.M):
        anchor = m
    if anchor is None:
        raise SystemExit("FATAL: could not locate row %d" % tail)

    row = "| %d | ORCH | MEASURED | %s |" % (NEW_ID, BODY)
    out = src[: anchor.end()] + "\n" + row + src[anchor.end() :]
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(out)

    back = io.open(PATH, encoding="utf-8").read()
    ids2 = [int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", back, re.M)]
    if max(ids2) != NEW_ID:
        raise SystemExit("FATAL: post-write tail is %d" % max(ids2))
    if len(ids2) != len(ids) + 1:
        raise SystemExit("FATAL: row count went %d -> %d" % (len(ids), len(ids2)))
    print("OK fact %d appended  rows %d -> %d" % (NEW_ID, len(ids), len(ids2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
