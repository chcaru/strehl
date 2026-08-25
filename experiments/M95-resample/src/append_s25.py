"""Append section 25 to the M95 report, byte-safe, refusing to duplicate.

Written as a Python script rather than a PowerShell here-string on purpose: in
@"..."@ a backtick is an escape introducer that consumes itself AND the following
character, which has already corrupted one report in this corpus (fact 1488).
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-kernel.md")
MARKER = "## 25. Auditing my own report for prefix grafts"

SECTION = """
---

## 25. Auditing my own report for prefix grafts

ORCH, 19:29, discipline 768: *"anchor every edit on a COMPLETE LINE, never on a
sentence prefix. A prefix-anchored replacement silently grafts the unmatched
remainder of the line onto the end of your new text -- no error, no failed match,
no lint violation."*

That is a live hazard for this report specifically, because §24.9 records that I
edited one hash cell in the §24 results table from 8 hex digits to 16. If that
edit had been prefix-anchored, the tail of the original row was grafted on and
would read as ordinary markdown. **None of my existing gates would necessarily
catch it:** `verify_s24.py` asserts that values are *present*, not that no extra
text trails them.

I did not reason about whether my edit was safe. I built a detector and ran it.

### 25.1 Three checks, and why each needed a control

`experiments/M95-resample/src/x20_graftcheck.py`, over both reports I own.

- **A -- table cell-count consistency.** A graft on a table row adds cells. Within
  each contiguous run of table rows, any row disagreeing with the block majority
  is flagged.
- **B -- intra-line repeated substring** of at least 18 characters. A graft
  usually duplicates part of the line it grafted onto. This is a *heuristic*, and
  it is treated as one.
- **C -- hash-cell well-formedness.** Every hash cell in a `C0`--`C4` row must be
  exactly 16 uppercase hex characters. This targets my actual edit directly.

Discipline 594 is my predecessor's and it binds me: a null is a claim about the
world only if the instrument could have said otherwise. So the script plants a
synthetic graft and **requires every check to fire before it will report on the
subject at all.** If a control fails it exits 2 and states that it is blind,
rather than exiting 0 and calling the report clean.

Six controls, all **FIRED** this session:

| control | what it plants | purpose |
| --- | --- | --- |
| A1 | a graft adding two cells | check A responds |
| B1 | a graft duplicating a hash token | check B responds |
| C1 | an 8-hex hash cell | check C responds |
| A2 | a graft in a table that *also* uses escaped pipes | the §25.2 fix corrected rather than silenced |
| A3 | the same table with **no** graft | A2 is not firing on the escaping alone |
| B2 | one character appended to an allowlisted line | the allowlist cannot hide a later graft |

**A3 and B2 are the ones that matter.** A2 alone would pass just as well if check A
had been rewritten to flag everything; A3 requires it to be silent on the clean
version of the same table. B2 guards the allowlist introduced in §25.3.

### 25.2 The first run indicted my own instrument, not the report

First run: **21 candidates**, of which **9 from check A**. All nine traced to one
defect in my detector: it split table rows on every pipe, including the escaped
pipe that markdown requires inside a cell. A row such as the `-First 3` arm in the
§9 exit-code table counted two phantom cells.

The failure was worse than a false positive. Because the inflated rows changed the
block *majority*, check A then flagged the **correct** rows as deviant and left the
inflated ones alone. An instrument that miscounts can accuse the wrong line.

Fix: unescape the escaped pipe before splitting. Check A went **9 hits to 0**, and
control A3 establishes that this corrected the count rather than muting the check.

### 25.3 Check B's 12 hits are all benign, and are allowlisted by content

Check B returned 12 hits across both reports. Every one is legitimate repetition:

- four are §24 result rows that repeat a hash **because pre equals post** -- which
  *is* the finding, so the repetition is the datum and removing it would destroy
  the result;
- two are the `nearest` and `bilinear` rows, which genuinely measured 0.0000 in
  all seven columns;
- the rest are parallel prose, a table header with parallel column names, two
  filenames sharing a directory, and a ratio of two identical-form terms.

These are allowlisted **by SHA-1 of the line's stripped content, not by line
number.** Keying on content means the entry stops matching the instant the line is
edited, so an allowlisted line that later grows a graft re-surfaces. Control B2
proves this by mutating an allowlisted line and requiring it back.

### 25.4 Result

**Clean.** Final run over `M95-kernel.md` (2 962 lines) and
`M95-merge-vs-frame-sharpness.md` (706 lines): check A **0**, check B **0**,
check C **0**, with all six controls firing. **The §24 hash edit landed correctly
and there is no graft in either report.**

One real defect surfaced, and it was cosmetic rather than numeric: the §24 results
table had an **empty header cell** over the column carrying `same` / `DIFFER`. It
is now labelled `A vs B`. That edit was anchored on the complete header line, per
the discipline that prompted the audit. No number moved; `verify_s24.py` re-ran
**29/29 GREEN** afterwards.

All gates re-run this session, each exit code captured on the line immediately
following its process: `verify_s23` **0** (76/76), `verify_s24` **0** (29/29),
`verify_report` **0** (all merge-vs-frame numbers verified), `x20_graftcheck`
**0**.

### 25.5 The same defect class is live in the corpus, in another lane

`corpus_lint` currently reports **4 violations, none of them in an M95-owned
file**: one C3 against an experiment directory under M123, and three against
`M110-sheet.md:1332` -- two S1 and one S6.

Those three are *the same class of defect my check A had*, in the opposite
direction. My instrument miscounted because it did not honour the escaped pipe;
that row is miscounted by the renderer because it does not *use* one, so an
absolute-value bar inside a code span opens a cell and four cells are silently
discarded. I found the bug in my detector at the same hour the corpus linter found
it in a subject. Reported, not touched -- `M110-sheet.md` is M110's lane.

### 25.6 What this section does not claim

It does not claim my reports are free of *all* editing damage. Checks A and C are
structural and decisive within their scope; check B is a heuristic that catches
grafts which duplicate text and would miss one that does not. A graft of entirely
novel prose onto a non-table line remains undetected by this instrument, and I am
recording that limit rather than letting the word "clean" cover it.
"""


def main():
    with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
        body = fh.read()

    if MARKER in body:
        print("ALREADY APPENDED -- refusing to duplicate")
        return 2

    crlf = body.count("\r\n")
    lf_only = body.count("\n") - crlf
    nl = "\r\n" if crlf > lf_only else "\n"

    draft = SECTION.replace("\r\n", "\n").replace("\n", nl)
    if not body.endswith(nl):
        body += nl
    out = body + draft

    with io.open(REPORT, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    ctrl = [c for c in out if ord(c) < 32 and c not in "\r\n\t"]
    print(f"line ending: {'CRLF' if nl == chr(13) + chr(10) else 'LF'}")
    print(f"before {len(body)} bytes, draft {len(draft)}, after {len(out)}")
    print(f"section 25 present: {MARKER in out}")
    print(f"control bytes introduced: {len(ctrl)}")
    print(f"total lines: {out.count(nl) + 1}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
