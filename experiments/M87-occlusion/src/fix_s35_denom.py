"""M87 -- keep the two running totals honest after the wrap-up landed.

Adding `110-crosscheck.py` -- a genuine measurement script, not harness --
moved tonight's measurement denominator from 104 to 105, and P150 quotes the
pinned gate-ladder range, which adds a fifth live site for `0.0572 pp`.

Both are the P143 class: a count in prose that is a claim about the tree, and
an inventory of sites that has to be re-counted rather than bumped.  The
denominator sentence is amended because it is now FALSE, not because a check
objects to it -- 97 was the count at the start of the night and 105 is the
count now, so "97 to 105" is the true statement.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

OLD = "new scripts moved the measurement denominator from 97 to 104. **The zeros both"
NEW = "new scripts moved the measurement denominator from 97 to 105. **The zeros both"


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if NEW in raw:
        print("denominator already current -- nothing to do")
        return

    # Discipline 768: anchor on a COMPLETE line.  A prefix anchor would graft
    # the unmatched remainder onto the end of the replacement silently.
    lines = raw.split("\r\n")
    hits = [n for n, l in enumerate(lines) if l == OLD]
    if len(hits) != 1:
        sys.exit("ANCHOR IS NOT A UNIQUE COMPLETE LINE (%d hits)" % len(hits))

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-denom.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    lines[hits[0]] = NEW
    raw = "\r\n".join(lines)
    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    if after.count(NEW) != 1 or OLD in after:
        sys.exit("POST-WRITE CHECK FAILED")
    print("denominator sentence updated to 97 -> 105")


if __name__ == "__main__":
    main()
