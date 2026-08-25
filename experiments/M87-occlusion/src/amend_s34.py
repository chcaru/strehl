"""M87 -- amend section 34.9 with control_s34's N10 finding, and add fact P139.

IMPORTANT CORRECTION TO MY FIRST DRAFT OF THIS SCRIPT.  I wrote it to record
N10 as a new discovery.  Its own guard refused, because "instance-blind"
already appears in this document: `P105` measured exactly this defect in
section 28, and `P113` recorded it as CLOSED at section 29, where verify_s29
began asserting exact occurrence counts.

So N10 did not find a new defect.  It found that I REGRESSED a discipline this
report had already closed, three sections later, in a verifier I wrote tonight.
That is the more useful finding and it is what gets recorded.
"""
import pathlib

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
ANCHOR = "Three limits, stated rather than buried."
GUARD = "already closed at `P113`"

PARA = """`control_s34.py` runs eleven arms and every operand mutation goes red:
perturbing a single near or far level by 500 DN fails 10 and 15 checks
respectively, relabelling a branch or a control verdict fails 2, and
relabelling §25.7's `gate-0 merge` row fails the source check. `N11` restores
everything and is green-expected, so the harness is not merely always red.

**`N10` caught me regressing a discipline this report had already closed at
`P113`, and that is worth more than the patch.** `verify_s34` passed 90 checks
on its first run. `N10` then altered **one of two** prose instances of a figure
and it stayed **green**, because I had written every prose assertion as
`figure in text`. That is presence-checking, and presence-checking is
instance-blind: a number wrong in one place and right in another passes. This
is not news to this document. `P105` measured the same blind spot in §28, and
`P113` recorded it **closed** at §29, where `verify_s29.py` started asserting
exact occurrence counts. Three sections later I rebuilt the defect from
scratch.

The repair is the one §29 already established -- exact counts, read off the
document by a reporting mode rather than guessed, every site annotated -- and
`N10` now goes red. The transferable part is not the defect but its return: **a
discipline closed in one section does not propagate to the next by itself.**
Only a per-section control catches the regression, which is an argument for
writing the controls even when the verifier looks clean, and especially
then."""

ROW = (
    "| P139 | **A discipline this report had already closed came back three "
    "sections later, and only a per-section control caught it.** `verify_s34` "
    "passed 90 checks on its first run; `control_s34`'s `N10` altered **one of "
    "two** prose instances of a figure and it stayed **GREEN**, because every "
    "prose assertion was written as presence rather than count -- the exact "
    "blind spot `P105` measured in §28 and `P113` recorded as **closed** at "
    "§29. Restoring exact occurrence counts turns `N10` red and raises the "
    "suite to 97 checks. | The finding is the regression, not the defect. A "
    "clean first run is grounds for suspicion rather than comfort: "
    "`verify_s33` failed 14 checks on its first run and was the sounder "
    "instrument for it. Closing a discipline in one section does not carry it "
    "into the next, so each section needs its own controls even -- especially "
    "-- when its verifier looks clean. | MEASURED |"
)


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    assert "| P139 |" not in raw, "P139 already present"
    assert GUARD not in raw, "amendment already applied"
    assert "| P105 |" in raw and "| P113 |" in raw, "cited priors missing"
    n = raw.count(ANCHOR)
    assert n == 1, f"anchor appears {n} times, expected exactly 1"
    assert ROW.count("|") - ROW.count("&#124;") == 5, "bad pipe count"
    assert ROW.count("`") % 2 == 0, "odd backtick count"

    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    i = raw.index("| P138 |")
    j = raw.index("\r\n", i) + 2
    raw = raw[:j] + ROW + "\r\n" + raw[j:]

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode("utf-8"))
    print(f"amended 34.9 and added P139; {raw.count(chr(10))} lines")


if __name__ == "__main__":
    raise SystemExit(main())
