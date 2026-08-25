"""M87 / s37 -- syncs the stated measurement denominator to disk.

This sentence has now gone stale three times in one night, once per batch of
new measurement scripts, and each time verify_s34 caught it. Rather than hand-
edit a fourth number, this reads the count from disk through the single owner
of the harness/measurement split and rewrites the sentence to match.

Two guards make that safe rather than merely convenient:

  - it refuses to write unless the sentence is found as a COMPLETE LINE
    exactly once, because a sentence-prefix anchor silently grafts the
    unmatched remainder of the line onto the replacement;
  - it refuses to LOWER the figure. The sentence records a span from 97 at
    the start of the night to the count now. A number that only ever rises
    cannot be quietly fitted to whatever makes a checker pass, and if the
    denominator ever falls that is a real event I want to see fail loudly.

Adding this file does not move the figure it writes: `fix_` is a harness
prefix, so the script excludes itself from the count by construction.
"""
import pathlib
import re
import sys

SRC = pathlib.Path(__file__).resolve().parent
DOC = SRC.parents[2] / "docs" / "research" / "M87-occlusion.md"

PAT = re.compile(r"^new scripts moved the measurement denominator from 97 to "
                 r"(\d+)\. \*\*The zeros both$")


def main():
    sys.path.insert(0, str(SRC))
    import fix_audit
    n = len([p for p in sorted(SRC.glob("*.py"))
             if not p.name.startswith(fix_audit.HARNESS)])

    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    lines = raw.split("\r\n")
    hits = [(i, m) for i, l in enumerate(lines) if (m := PAT.match(l))]
    if len(hits) != 1:
        sys.exit("COMPLETE-LINE ANCHOR NOT FOUND EXACTLY ONCE (%d)" % len(hits))
    i, m = hits[0]
    cur = int(m.group(1))
    if cur == n:
        print(f"denominator already current at {n}")
        return 0
    if n < cur:
        sys.exit("REFUSING TO LOWER the denominator %d -> %d; a falling count "
                 "is a real event, not a sync" % (cur, n))
    lines[i] = lines[i].replace(f"97 to {cur}.", f"97 to {n}.", 1)
    out = "\r\n".join(lines)
    assert out.count("\n") == out.count("\r\n"), "CRLF broken"
    assert out.count(f"97 to {n}") == 1, "new figure is not unique"
    DOC.write_bytes(out.encode("utf-8"))
    print(f"denominator sentence: 97 to {cur} -> 97 to {n} (disk confirms {n})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
