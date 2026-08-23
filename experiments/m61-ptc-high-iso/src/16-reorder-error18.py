"""M61 step 16 -- move the Error 18 block above Error 19, in document order.

WHY THIS IS A SCRIPT AND NOT AN EDIT
------------------------------------
Errors 12/13, 19 and 20 in this report are all the same defect: a hand edit that
replaced a block beginning with a header and did not re-emit the header, either
deleting it or leaving the following block duplicated. Discipline 11 says the
guard must be structural, so this script implements exactly that guard rather
than asking the author to be careful:

  * the multiset of "**Error N" headers must be IDENTICAL before and after;
  * the multiset of all non-empty lines must be IDENTICAL before and after
    (a pure move changes order, never content);
  * the file length in characters must be unchanged;
  * Error 18 must end up before Error 19.

Any violation aborts and writes nothing. A move that cannot satisfy all four is
not a move, it is an edit, and it should be made by hand and re-read.
"""
import io
import re
import sys
from collections import Counter
from pathlib import Path

DOC = Path(__file__).resolve().parents[3] / "docs" / "research" / \
    "M61-ptc-high-iso-measured.md"

START = "**Error 18 — I labelled a claim ARGUED on a premise I had not checked.**"
END = "the premise.**\n"
ANCHOR = "**Error 19 — I duplicated a block of proposed facts"


def sig(text):
    return (Counter(re.findall(r"\*\*Error (\d+)[ ]?[—(.]", text)),
            Counter(ln for ln in text.splitlines() if ln.strip()),
            len(text))


def main() -> int:
    t = io.open(DOC, encoding="utf-8").read()
    before = sig(t)

    i = t.index(START)
    j = t.index(END, i) + len(END)
    block = t[i:j]
    rest = t[:i] + t[j:]

    # the block was followed by a blank line; carry it with the block so the
    # surrounding spacing is preserved exactly.
    rest = rest.replace("\n\n\n", "\n\n", 1) if "\n\n\n" in rest[i - 4:i + 4] else rest

    k = rest.index(ANCHOR)
    out = rest[:k] + block + "\n" + rest[k:]

    after = sig(out)
    if after[0] != before[0]:
        print(f"ABORT headers changed: {before[0]} -> {after[0]}")
        return 1
    if after[1] != before[1]:
        d = (before[1] - after[1]) + (after[1] - before[1])
        print(f"ABORT line content changed, {sum(d.values())} lines differ")
        for ln in list(d)[:5]:
            print("   ", ln[:78])
        return 1
    if after[2] != before[2]:
        print(f"ABORT length changed: {before[2]} -> {after[2]}")
        return 1
    if out.index("**Error 18 —") > out.index("**Error 19 —"):
        print("ABORT error 18 is still after error 19")
        return 1

    io.open(DOC, "w", encoding="utf-8", newline="").write(out)
    print(f"OK  moved Error 18 ({len(block)} chars) above Error 19; "
          f"headers, line content and length all unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
