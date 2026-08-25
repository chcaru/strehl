"""M87 -- record the fourth verifier break: a replicated RULE, not a stale value.

P143 concluded the defect class was keying a check to a VALUE rather than a
SITE.  Adding P144 broke two more verifiers in a way that diagnosis does not
cover: both were anchored correctly, and both applied a private copy of a
shared classification rule.

Same trap as P143/P144: `control_s29` asserts three sentences occur exactly
once, and `100.00%` is the collision P143 is about.  Both guarded below.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

FORBIDDEN = [
    "It measured **100.00%** and printed PASS.",
    "It measured **100.00%** and printed **PASS**.",
    "| **100.00%** | 0.4137 |",
]

ROW = (
    "| P145 | **A fourth verifier break, and P143's diagnosis does not cover "
    "it: the checks were anchored correctly and applied a REPLICATED RULE.** "
    "The harness/measurement split that P124's two zeros are scoped by was "
    "written out four times -- in `fix_audit.py`, `verify_s32.py`, "
    "`verify_s34.py` and a new probe -- and adding one prefix to one copy "
    "turned `verify_s32` and `verify_s34` red and moved the published "
    "denominator 104 -> 105 -> 104. Neither verifier was keyed to a value: "
    "both re-counted from disk exactly as designed, and both counted "
    "correctly under a rule that was no longer the one writing the JSON. | "
    "**Consolidating the rule fixes the drift and destroys the evidence, so "
    "it cannot be the whole repair.** One owner now defines the split and the "
    "other three import it -- after which the audit and its verifiers agree "
    "*by construction*, and their agreement stops being a measurement of "
    "anything. `verify_s32` therefore gained the check a shared constant "
    "cannot fake: a script excluded as harness may not decode a raw or open a "
    "frame cube, so the convention is tested against the property it stands "
    "for rather than against itself (58 -> 59 checks). **A duplicated "
    "definition is worse than a duplicated value**, because a value that "
    "drifts makes a check fail loudly, while a rule that drifts makes two "
    "instruments disagree about what they are counting -- and whichever runs "
    "last looks correct. | MEASURED |"
)

ANCHOR = "Three limits, stated rather than buried."

PARA = """**Appending §34.9 broke a fourth verifier, and this one refutes the
diagnosis I gave three paragraphs ago.** P143 concluded that the shared cause
of three earlier breaks was keying a check to a *value* rather than to a
*site*. That was true of those three. It is not true of this one, and the
difference matters more than the count does.

Recording P144 required a new script, and classifying it moved the denominator
that P124's two zeros are quoted against. The classification rule -- which
filename prefixes mark a harness script rather than a measurement -- turned out
to be written in full four separate times: in the script that writes the audit,
in the two verifiers that re-derive it, and in the new probe itself. Changing
one copy moved the disk count to 105 while the JSON said 104, and both
verifiers went red.

**Neither of them was keyed to a value.** Both re-counted the scripts from
disk, which is exactly what I had asked them to do, and each counted correctly
under the rule it was holding. The failure was that they were no longer holding
the same rule as the script that wrote the number, and nothing in either
instrument could see that. A stale value fails loudly the moment the document
moves; a stale *rule* keeps producing a well-formed number, and the last
instrument to run looks authoritative.

The repair gives the split a single owner and has the other three import it.
That removes the drift -- and it also removes the evidence, which is the part
worth being careful about. Once the audit and its verifiers share one
definition they agree by construction, and their agreement is no longer a
measurement. So the consolidation is paired with a check that a shared constant
cannot satisfy: any script excluded as harness must genuinely measure nothing
about an image, and may not decode a raw or open a frame cube. The prefix is a
convention; that is the property the convention exists to stand for, and it is
now tested directly.

**The honest tally is four appends, four broken verifiers, and two distinct
causes.** I would rather record that the class I named was incomplete than
present a tidy one. The rate has not changed, but the claim that one diagnosis
explains it has."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P145 |" in raw:
        print("P145 already present -- nothing to do")
        return

    bare = ROW.replace("\\|", "")
    assert bare.count("|") == 5, "fact row needs exactly 5 unescaped pipes"
    assert ROW.count("`") % 2 == 0, "fact row backtick count is odd"
    assert PARA.count("`") % 2 == 0, "paragraph backtick count is odd"
    for f in FORBIDDEN:
        if f in ROW or f in PARA:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    if "100.00%" in ROW or "100.00%" in PARA:
        sys.exit("NEW PROSE QUOTES 100.00%% -- the exact P143 collision")

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p145.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P144 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P144 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        n = after.count(f)
        if n != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r now occurs %dx" % (f, n))
    if "| P145 |" not in after:
        sys.exit("POST-WRITE CHECK FAILED: P145 missing")
    print("added P145 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()
