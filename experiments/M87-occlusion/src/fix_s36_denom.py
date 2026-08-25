"""M87 / s36 -- moves the stated denominator from 97->105 to 97->107.

Two measurement scripts were added tonight (111-provenance.py and
112-launder.py, renamed out of a harness prefix they never deserved), so the
running denominator moved again. verify_s34 re-derives the figure from disk
and refuses any prose that disagrees, which is how this surfaced.

The anchor is a COMPLETE LINE. A sentence-prefix anchor silently grafts the
unmatched remainder of the line onto the end of the replacement, with no
error and no failed match, and the result reads as plausible prose.

Truthfulness check before writing: 97 was the denominator at the start of the
night and 107 is the count on disk now, so the sentence remains a true
statement of the same span rather than a number bumped to satisfy a checker.
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parent
DOC = SRC.parents[2] / "docs" / "research" / "M87-occlusion.md"
HARNESS_OWNER = SRC / "fix_audit.py"

OLD = "new scripts moved the measurement denominator from 97 to 105. **The zeros both"
NEW = "new scripts moved the measurement denominator from 97 to 107. **The zeros both"


def main():
    sys.path.insert(0, str(SRC))
    import fix_audit
    scripts = sorted(SRC.glob("*.py"))
    meas = [p for p in scripts if not p.name.startswith(fix_audit.HARNESS)]
    if len(meas) != 107:
        sys.exit("disk says %d measurement scripts, not 107 -- refusing to "
                 "write a figure I have not confirmed" % len(meas))

    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    lines = raw.split("\r\n")
    hits = [i for i, l in enumerate(lines) if l == OLD]
    if len(hits) != 1:
        sys.exit("COMPLETE-LINE ANCHOR NOT FOUND EXACTLY ONCE (%d)" % len(hits))
    lines[hits[0]] = NEW
    out = "\r\n".join(lines)
    assert out.count("\n") == out.count("\r\n"), "CRLF broken"
    assert out.count("97 to 107") == 1, "new figure is not unique"
    assert "97 to 105" not in out, "old figure survived"
    DOC.write_bytes(out.encode("utf-8"))
    print("denominator sentence: 97 to 105 -> 97 to 107 (disk confirms 107)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
