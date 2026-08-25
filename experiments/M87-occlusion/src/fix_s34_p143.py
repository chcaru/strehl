"""M87 -- record the third broken verifier, and the corrected diagnosis.

Two edits, each anchored on a unique single line and each hard-erroring if the
anchor does not land.

A trap this script had to be written around: the repair being described binds
`verify_s29` to three sentence-level anchors, and `control_s29` asserts each
occurs EXACTLY once before mutating it.  So neither the fact row nor the
paragraph may reproduce any of those sentences verbatim -- doing so would
silently break the controls that certify the repair the prose is about.  The
sites are therefore described, never quoted.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

# strings control_s29 asserts are unique; the new prose must not contain them
FORBIDDEN = [
    "It measured **100.00%** and printed PASS.",
    "It measured **100.00%** and printed **PASS**.",
    "| **100.00%** | 0.4137 |",
]

ROW = (
    "| P143 | **A third verifier broke on the same append, in a third "
    "distinct shape, and the common cause is not scope -- it is keying a "
    "check to a VALUE instead of to a SITE.** `verify_s29` counted the bolded "
    "rendering of its full-coverage figure across the whole document and "
    "expected 3 sites; §34's engine ladder quoted two unrelated rates of 100% "
    "and pushed the count to 5. The three defects differ in mechanism -- "
    "`verify_s33` sliced its scope to end-of-file, `verify_s32` re-counted a "
    "denominator from disk, `verify_s29` counted a generic value -- but each "
    "was an expectation that any future sentence could move. | Repaired by "
    "binding all three real sites to their own anchors rather than bumping 3 "
    "to 5, which is strictly stronger than the count it replaces: two of "
    "those sites are the same sentence and differ only in whether the verdict "
    "word is emphasised, and `control_s29`'s new `N11` collapses one onto the "
    "other -- a defect no bare count can see. Three sections appended, three "
    "earlier verifiers broken: that is a rate, not an anecdote. | MEASURED |"
)

ANCHOR = "Three limits, stated rather than buried."

PARA = """**A third verifier broke, and it changes what I think the defect is.**
Running the full suite after §34.9 grew, `verify_s29` -- green at its last
commit -- failed exactly one check: it counts the bolded rendering of its
full-coverage figure across the whole document and expects three sites, and
the engine ladder above quotes two unrelated rates of 100%.

That is three earlier verifiers broken by three successive appends, in three
different shapes: `verify_s33` sliced its scope to end-of-file, `verify_s32`
re-counted its denominator from disk, and now `verify_s29` counted a value
generic enough for a later sentence to reproduce by coincidence. **I had been
calling this a scope problem. It is not.** The property the three share is
that each check was keyed to a *value* rather than to a *site*, and a value is
not an identifier: 100% belongs to no section, so every sentence written after
it is a potential collision.

The repair binds each of the three real sites to an anchor that carries its
neighbouring text, which no future section reproduces by accident. It is also
strictly stronger than the total it replaced, and `control_s29` now
demonstrates that rather than asserting it. Two of the three sites are the
*same sentence*, differing only in whether the verdict word is emphasised, so
the new `N11` arm rewrites one into the other. The document is then left still
holding two sentences that quote the figure, and the old count of three would
have been unmoved -- while both anchors that can tell the sites apart go red,
one because it now matches twice and one because it no longer matches at all.

**The rate is the part worth keeping.** Three sections appended, three prior
verifiers broken, and not one of them would have been caught by re-running the
section being edited. A verifier is not something written once and committed
green; it is a standing claim that every later section is entitled to
falsify."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P143 |" in raw:
        print("P143 already present -- nothing to do")
        return

    bare = ROW.replace("\\|", "")
    assert bare.count("|") == 5, "fact row needs exactly 5 unescaped pipes"
    assert ROW.count("`") % 2 == 0, "fact row backtick count is odd"
    assert PARA.count("`") % 2 == 0, "paragraph backtick count is odd"
    for f in FORBIDDEN:
        if f in ROW or f in PARA:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p143.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P142 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P142 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        n = after.count(f)
        if n != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r now occurs %dx" % (f, n))
    if "| P143 |" not in after:
        sys.exit("POST-WRITE CHECK FAILED: P143 missing")
    print("added P143 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()
