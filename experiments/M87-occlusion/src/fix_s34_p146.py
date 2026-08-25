"""M87 -- disclose how cheap a perfect rank reversal is on a four-arm ladder.

Answers ORCH's standing warning by running it against my own headline: the
section 34 ladder reports Spearman rho(gate, V) = -1.0000, and the exact null
says a perfect reversal on four points arrives by chance once in twenty-four.

Same two traps as P144/P145: `control_s29` asserts three sentences occur
exactly once, and `100.00%` is the P143 collision.  Both guarded.
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
    "| P146 | **The ladder's Spearman rho of &#8722;1.0000 is worth p = "
    "0.0417, not what a perfect coefficient looks like.** Exact enumeration "
    "of all 24 rank permutations of four points: a perfect reversal is a "
    "1-in-24 event under the null, and *some* perfect monotone ordering is "
    "1-in-12. A four-arm ladder cannot support a rank claim at all -- a "
    "perfect reversal first clears p < 0.01 at **n = 5** (0.0083). | **This "
    "does not move the section's conclusion, and saying why is the point.** "
    "The refutation never rested on the rank: it rests on the magnitude, "
    "`dV` = **+2.3463 pp** against a predicted **+19.79 pp** with the sign "
    "reversed, collapsing to **0.0572 pp** once the far reference is pinned. "
    "The rho was already carried as a warning that monotonicity alone would "
    "have read as confirmation -- but printing `&#8722;1.0000` to four "
    "decimals lends a four-point statistic an authority it has not earned, "
    "and a reader who took the rank as the evidence would have been misled by "
    "my presentation rather than by my arithmetic. **A coefficient's number "
    "of digits is not its number of observations.** | MEASURED |"
)

ANCHOR = "Three limits, stated rather than buried."

PARA = """**I ran the orchestrator's instrument warning against my own headline
and it found something.** The standing caution is that four instruments
returned confident numbers tonight while measuring the wrong thing, one of them
a two-bin Spearman reading a perfect coefficient on random data. The ladder
above reports Spearman rho(gate, `V`) = &#8722;1.0000 over **four** arms, which
is the same family of statistic on barely more points.

The null is countable rather than estimable, so there is no excuse for not
having it: under the null every one of the `n!` rank orderings is equally
likely, and enumerating all 24 orderings of four points gives **P(rho =
&#8722;1) = 0.0417** and **P(|rho| = 1) = 0.0833**. A perfect reversal on this
ladder is a one-in-twenty-four event. It first becomes rarer than 1 in 100 at
**five** arms (0.0083), and at eight arms it is 0.0000 to four places. **Four
points cannot carry a rank claim**, and mine was printed to four decimal
places, which is exactly the kind of false precision the warning is about.

**The section's conclusion does not move, and I want to be precise about why
rather than merely asserting it.** The refutation was never the rank. It is the
magnitude: `dV` of **+2.3463 pp** against a predicted **+19.79 pp** -- 11.86%
of the predicted swing and of the opposite sign -- collapsing to **0.0572 pp**,
0.289% of predicted, once the far reference is pinned. Those are effect sizes
on 451008 valid pixels, not orderings of four numbers. The rho was already
carried here as a caution that a bar checking monotonicity alone would have
scored this ladder as confirmation of the very mechanism it refutes.

So the correction is to my *presentation*, not my arithmetic, which is the
easier kind to miss on my own work. Reporting `&#8722;1.0000` next to genuinely
well-supported percentages invites a reader to weight them alike. **A
coefficient's number of digits is not its number of observations**, and the
remedy is to publish the null beside the statistic, which this section now
does."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P146 |" in raw:
        print("P146 already present -- nothing to do")
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

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p146.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P145 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P145 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        n = after.count(f)
        if n != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r now occurs %dx" % (f, n))
    if "| P146 |" not in after:
        sys.exit("POST-WRITE CHECK FAILED: P146 missing")
    print("added P146 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()
