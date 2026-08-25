"""M87 / s36 -- lands P152-P154: the provenance answer to M120, the true
delta recomputed without a re-render, and the direction 8-bit laundering
actually pushes each class of M87 statistic.

Three results, two of which are corrections against myself.

P152 clears the headline's provenance MECHANICALLY rather than by my
asserting it: the transitive source chain, the distinct-level counts of the
inputs, and the reader of record.

P153 recomputes the delta M120 believed unrecomputable. It was recomputable;
the sources were never gone. It also retracts a magnitude I gave ORCH.

P154 reports a REGISTERED PREDICTION OF MINE THAT FAILED. I predicted
laundering pulls a small-signal statistic toward zero. On the merge it did
the opposite.

Same guards as P144-P151: control_s29 anchors, the 100.00% collision, CRLF,
complete-line anchoring.
"""
import pathlib
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

FORBIDDEN = [
    "It measured **100.00%** and printed PASS.",
    "It measured **100.00%** and printed **PASS**.",
    "| **100.00%** | 0.4137 |",
]

MINUS = "\u2212"
ANCHOR = "Three limits, stated rather than buried."

ROWS = [
    (
        "| P152 | **The veil headline is structurally incapable of "
        "descending from the 8-bit laundered path, and this is established "
        "by trace and by level count rather than by my reading my own "
        "code.** M120 named `40-ship-delta.py` a laundering victim and "
        "concluded M87 must re-render before any halo number is trusted. "
        "The transitive source chain of `70-veil.py`, which produces the "
        "headline, is exactly `{70-veil.py, m87lib.py}`; the five files in "
        "the milestone that name `ship-delta.npy` are `40-ship-delta.py`, "
        "`41-delta-stats.py`, `45-locate.py`, `fix_audit.py` and this "
        "probe. **The overlap is empty.** | The trace is a necessary "
        "condition, not a sufficient one, so it is paired with a positive "
        "test the arrays cannot fake: an 8-bit-laundered array holds at "
        "most 256 distinct values. `bee3-leg-luma.npy` holds **7093** and "
        "`bee3-leg-sel.npy` holds **8492** on a single slice, at "
        "`float32` over 90 to 8684 DN. The reader of record is "
        "`rawpy.imread` into `raw_image_visible` at `m87lib.py:124`, and "
        "`m87lib.py` contains no `Image.open` at all, so the headline path "
        "never opens a TIFF by any route. `111-provenance.py`, R1 and "
        "R2, both PASS. | MEASURED |"
    ),
    (
        "| P153 | **The delta M120 reported as unrecomputable was "
        "recomputable the whole time, because the source renders were never "
        "gone -- they were in a different directory.** M120 could not "
        "recompute the true ship delta and recorded the sources as absent "
        "from `out/`. They are 198 MB each in "
        "`C:\\dev\\strehl-out\\M87-before-after\\`, which is where "
        "`40-ship-delta.py` wrote them and where its own path constant "
        "still points. Recomputed with `tifffile.imread` and a `uint16` "
        "assert: true `max abs delta` **41887** of 65535, against the "
        "laundered **163**, a factor of **257.0x** -- which is exactly "
        "65535/255, so the discrepancy is the quantisation itself and "
        "nothing else. **No re-render was required.** | **The same "
        "measurement retracts a magnitude I gave ORCH earlier tonight.** I "
        "said the 13.445% changed-pixel fraction was also an undercount, "
        "since any pixel moving under about 128 counts would read as "
        "unchanged. The direction is right and the size is not: the true "
        "fraction is **13.666%**, a ratio of **1.016x**, not the large "
        "undercount my phrasing implied. The reason is that where this "
        "correction moves a pixel at all it moves it far, so almost every "
        "changed pixel already cleared the 8-bit quantum. A correct sign "
        "with an uncalibrated magnitude is still an overstatement. | "
        "MEASURED |"
    ),
    (
        "| P154 | **A registered prediction of mine failed: 8-bit "
        "laundering does not push every small-signal statistic toward zero, "
        "and on the merge it pushed the opposite way.** ORCH broadcast the "
        "hazard as a false-null risk, then corrected itself via M120 to add "
        "a false-alarm risk on band-pass statistics. I registered Q1 "
        "(band-pass inflates) and Q2 (small-signal falls toward zero) "
        "before measuring, on the same array with quantisation as the only "
        "difference between arms, so scale cannot confound it. **Q1 PASS**: "
        "`mean abs grad` on the real render reads **75.4914** laundered "
        "against **73.8319** true, a ratio of **1.0225x**, independently "
        "replicating M120's **1.0161x** on different operands. **Q2 "
        "FAIL.** | The merge veil went "
        "**" + MINUS + "6.6810%** true to **" + MINUS + "7.4718%** "
        "laundered -- **deeper**, by 0.79 pp -- while frame 0 went "
        "**" + MINUS + "28.5999%** to **" + MINUS + "28.3776%**, toward "
        "zero, as predicted. **So the two arms of one statistic moved in "
        "opposite directions**, which rules out a floor and rules out an "
        "inflation. A median of binned medians is a rank statistic: "
        "quantisation snaps each median onto a lattice, displacing it by up "
        "to half a quantum with **arbitrary sign**. Half a quantum here is "
        "33.70/2 DN against a far pedestal of 3143 DN, i.e. 0.536% per "
        "median and about **1.07 pp** when both move; the observed 0.79 pp "
        "sits inside that bound. The headline gap it would have to threaten "
        "is 19.79 pp, so the conclusion survives with margin -- but it "
        "survives on a bound I had to derive after my prediction broke, not "
        "on the prediction. | MEASURED |"
    ),
]

PARA = """### The provenance challenge, and the third direction

M120 read `cache/ship-delta.npy` as `(4688,7032) uint16, max 163, mean
1.621`, correctly identified those as 8-bit units wearing a 16-bit dtype, and
concluded that M87 must re-render before any halo number could be trusted.
The first half of that is right and this milestone had already published it
as P40. The second half is not, and the difference matters more than the
agreement does.

The headline cannot descend from that path, and the argument is not that I
remember writing it differently. `70-veil.py` reaches exactly one other
module, `m87lib.py`, and neither names `ship-delta.npy`; the overlap between
the headline's source closure and the set of files that touch the laundered
array is empty. A trace alone would only show that I had not found a link, so
it is paired with a test the data itself has to pass: the inputs carry 7093
and 8492 distinct levels, and no array that has been through an 8-bit reader
can carry more than 256. The reader of record is `rawpy.imread`, which does
not open TIFFs.

The part worth keeping is what happened when I checked M120's own blocked
measurement instead of stopping at my own clearance. The renders it needed
were never deleted; they sit in `M87-before-after`, 198 MB each, at the path
`40-ship-delta.py` still points to. Recomputing takes seconds and gives
**41887** against the laundered **163** -- a factor of **257.0x**, which is
65535/255 to four figures and therefore the quantisation exactly. **A
milestone concluded that another milestone must repeat hours of rendering,
on the strength of a file not being in the first directory it looked in.**
The cheap check is to look for the artefact before prescribing the work that
would recreate it.

Two corrections against myself came out of the same run. I had told ORCH the
13.445% changed-pixel fraction was likewise an undercount; it is **13.666%**,
a ratio of **1.016x**. My sign was right and my magnitude was invented, and
an uncalibrated magnitude presented as an implication is an overstatement
even when the direction holds. And my registered Q2 -- that laundering pulls
a small-signal statistic toward zero -- **failed**: the merge veil deepened
from **&#8722;6.6810%** to **&#8722;7.4718%** while a single frame moved the
predicted way. Two arms of the same statistic moving in opposite directions
is not a floor and not an inflation but a third thing: a rank statistic
snapped onto a quantisation lattice, displaced by up to half a quantum in
**whichever direction the lattice happens to fall**. That bound, 1.07 pp,
contains the observed 0.79 pp, and the 19.79 pp gap the headline rests on is
far outside it. The conclusion holds. It holds on an error bound I only
derived because the prediction broke, which is not the same as having been
right.

None of this touches a published number, because none of the published
numbers were ever read through a TIFF. It is a counterfactual robustness
check on an exposure that did not occur, and it is reported at that strength
and no higher.

"""


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    before = len(raw.split("\r\n"))

    for f in FORBIDDEN:
        if raw.count(f) != 1:
            sys.exit("PRE-WRITE: control_s29 anchor %r is not unique (%d)"
                     % (f, raw.count(f)))

    for r in ROWS:
        if r.count("`") % 2:
            sys.exit("ODD BACKTICK COUNT in row: %r" % r[:80])
        if r.count("|") != 5:
            sys.exit("ROW HAS %d PIPES, need 5: %r" % (r.count("|"), r[:80]))
        for f in FORBIDDEN:
            if f in r:
                sys.exit("NEW ROW REPRODUCES A control_s29 ANCHOR")

    # rows go after the last existing fact row
    last = max(i for i, ln in enumerate(raw.split("\r\n"))
               if ln.startswith("| P1") and ln.count("|") == 5)
    lines = raw.split("\r\n")
    lines[last + 1:last + 1] = [r.replace(MINUS, "&#8722;") for r in ROWS]
    raw = "\r\n".join(lines)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    for f in FORBIDDEN:
        if f in body:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    raw = raw.replace(ANCHOR, body + "\r\n" + ANCHOR, 1)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken"
    # Scope this to MY insertions. The document already carries 376 raw U+2212
    # and passes corpus_lint, so a document-wide assert tests a property it
    # never had and would fail on every run regardless of what I wrote.
    assert MINUS not in body, "raw minus sign in new prose; must be &#8722;"
    for r in ROWS:
        assert MINUS not in r.replace(MINUS, "&#8722;"), "row minus not converted"
    for f in FORBIDDEN:
        if raw.count(f) != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r moved" % f)

    DOC.write_bytes(raw.encode("utf-8"))
    print(f"{DOC.name}: {before} -> {len(raw.split(chr(13) + chr(10)))} lines, "
          f"P152-P154 landed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
