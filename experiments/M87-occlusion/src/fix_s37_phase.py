"""M87 / s37 -- lands P155-P157: two of my own framings die, and the survivor
is sharper than either.

ORCH proposed routing my "arbitrary sign" result to M121 as: a RANK statistic
breaks value-locking. I tested it before handing it over and it is false.
Then my replacement framing (co-movement DECAYS with value separation) also
failed. What survived a registered test is periodicity, and it changes the
question ORCH wanted asked.

P155 retracts the rank framing on a measurement, not on reflection.
P156 reports my second failed prediction and the law that replaced it.
P157 states the transfer to M121 as a falsifiable test, and kills the
     rank-vs-mean discriminator ORCH proposed, which would have misrouted it.

Guards as before: control_s29 anchors, the 100.00% collision, CRLF, complete-
line anchoring, 5 unescaped pipes per row, even backticks. Absolute-value
bars are written as "abs rho" -- a literal `|` inside a table row opens a
cell, which is the S1/S6 defect still open in M95's file.
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
        "| P155 | **I retract my own rank framing; it is refuted by a "
        "measurement, not by reconsideration.** I reported to ORCH that a "
        "median of binned medians is a rank statistic whose quantisation "
        "error takes an arbitrary sign, and ORCH proposed routing that to "
        "M121 as a mechanism that would break value-locking. Quantisation "
        "is a monotone map and medians commute with monotone maps: over "
        "2000 random draws of 51 samples from the real cube, "
        "`median(q(X))` equals `q(median(X))` with **0** mismatches. So a "
        "median's error is `e(m)` evaluated at its own value -- **value-"
        "determined, exactly like a mean's**. | The rank framing was mine "
        "and it was wrong, and it was one message away from being folded "
        "into another milestone's open contradiction. Fact 1765 is "
        "untouched by anything about rank. The error is a sawtooth of "
        "period `Delta`: max abs e measures **16.8297 DN** against a "
        "predicted `Delta/2` of **16.8510 DN**, and it changes sign inside "
        "every cell. `113-rankphase.py`, T1 and T2. | MEASURED |"
    ),
    (
        "| P156 | **My replacement framing failed too, and the law that "
        "survived is periodicity rather than decay.** Having lost the rank "
        "story I registered that co-movement of quantisation error would "
        "DECAY with value separation, predicting correlation above 0.80 "
        "under 0.1 `Delta` and under 0.30 beyond 2 `Delta`. **It failed.** "
        "Correlation ran **+0.7957** at 0.02 `Delta`, fell to **&#8722;"
        "0.4982** at 0.50 `Delta`, then returned to **+0.8205**, **+0.7669"
        "**, **+0.8117** and **+0.8194** at 1, 2, 4 and 8 `Delta`. That is "
        "not decay. | Registered on a discriminating grid and re-run: "
        "correlation is **periodic in the quantum**. Half-integer "
        "separations sit in antiphase (**&#8722;0.4972** at 0.5, **&#8722;"
        "0.4973** at 1.5, **&#8722;0.5175** at 2.5) and integer "
        "separations restore phase (**+0.8166** at 1, **+0.8890** at 2, "
        "**+0.8277** at 3). Both registered arms pass. Two of my framings "
        "died to get here, and the second died on a grid I chose before "
        "seeing its result. `114-phaseperiod.py`, T5 and T6. | MEASURED |"
    ),
    (
        "| P157 | **A value-proximity test that ignores phase must read "
        "zero even when every pair in it is perfectly value-determined -- "
        "which is a testable account of a failed prediction elsewhere, not "
        "a resolution of it.** Drawing separations uniformly over 0 to 2 "
        "`Delta` and correlating the errors gives **+0.0038** over 6000 "
        "pairs. Nothing is random in that construction: each pair obeys "
        "value-determinism exactly, and the bin averages the sawtooth "
        "away. **So a null in such a test is a property of the test's bin "
        "width, not of the data.** | **ORCH's proposed discriminator is "
        "the wrong one and would have misrouted this.** It suggested rank "
        "statistics fail while means hold; measured, a mean shows the "
        "SAME periodicity and more strongly -- **&#8722;0.9039** at 1.5 "
        "`Delta` against a median's **&#8722;0.4973**, **+0.9461** at 2 "
        "`Delta` against **+0.8890**. The discriminator is not rank versus "
        "mean but **bin width against the quantum**. Registered test for "
        "any milestone holding a failed value-locking prediction: if its "
        "value-proximity bin spans a non-trivial fraction of `Delta` the "
        "null is forced; re-bin by value **modulo** `Delta` and the "
        "correlation must reappear. I have not seen that milestone's data "
        "and this is offered as a test, not a finding about it. | ARGUED |"
    ),
]

PARA = """### Two framings of mine died on the way to this one

ORCH asked me to hand M121 a mechanism: that a rank statistic breaks
value-locking, because the error's sign is set by which side of a lattice
boundary the rank falls on. It was my framing and ORCH was quoting it back to
me. Before writing the bridge I tested it, and it is false. Quantisation is
monotone, medians commute with monotone maps, and over 2000 draws
`median(q(X))` equalled `q(median(X))` **every time**. A median's error is
value-determined exactly as a mean's is. Had I written the paragraph ORCH
asked for, I would have supplied a plausible mechanism for another
milestone's open contradiction and it would have been wrong.

My replacement was wrong too. I registered that co-movement decays with value
separation and it does not: it falls, inverts, and comes **back**. What
survived, on a grid registered before it ran, is that co-movement is
**periodic in the quantum**. Two populations separated by a whole number of
quanta sit at the same phase within their cells and their errors coincide;
separated by a half-integer they sit in antiphase and their errors oppose.
Value-locking is not weakened by any of this. It is exact, pairwise, and
**periodic**, and periodicity is the part that makes it disappear from a
badly-scaled test.

That is the whole transfer, and it is narrower than the one I was asked for.
A test that groups pixels by proximity in value, using a bin wider than a
quantum, averages over every phase and must return zero -- I measured
**+0.0038** on 6000 pairs constructed to be perfectly value-determined. So a
null in such a test says the bin was phase-blind; it does not say the data
lack value-locking. The discriminator ORCH proposed -- rank fails, mean holds
-- is not the right one, and I would rather say so than let it route
anything: a mean shows the same periodicity **more** strongly than a median,
&#8722;0.9039 against &#8722;0.4973 in antiphase. The right discriminator is
bin width against the quantum, and the sharp version of the test is to re-bin
by value **modulo** the quantum, where the correlation has to come back.

I am stating this as a test because I have not seen the data it would be run
against, and because I have now been wrong twice in a row about the mechanism
behind my own number. The measurements above are mine and they are solid. The
transfer is a hypothesis with a falsifier attached, and it should be folded at
that strength and no higher.

"""


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    before = len(raw.split("\r\n"))

    for f in FORBIDDEN:
        if raw.count(f) != 1:
            sys.exit("PRE-WRITE: control_s29 anchor %r not unique (%d)"
                     % (f, raw.count(f)))
    for r in ROWS:
        if r.count("`") % 2:
            sys.exit("ODD BACKTICK COUNT: %r" % r[:80])
        if r.count("|") != 5:
            sys.exit("ROW HAS %d PIPES, need 5: %r" % (r.count("|"), r[:80]))
        for f in FORBIDDEN:
            if f in r:
                sys.exit("NEW ROW REPRODUCES A control_s29 ANCHOR")

    lines = raw.split("\r\n")
    last = max(i for i, ln in enumerate(lines)
               if ln.startswith("| P1") and ln.count("|") == 5)
    lines[last + 1:last + 1] = [r.replace(MINUS, "&#8722;") for r in ROWS]
    raw = "\r\n".join(lines)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    assert MINUS not in body, "raw minus in new prose; must be &#8722;"
    for f in FORBIDDEN:
        if f in body:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    raw = raw.replace(ANCHOR, body + "\r\n" + ANCHOR, 1)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken"
    for f in FORBIDDEN:
        if raw.count(f) != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r moved" % f)

    DOC.write_bytes(raw.encode("utf-8"))
    print(f"{DOC.name}: {before} -> {len(raw.split(chr(13) + chr(10)))} lines, "
          f"P155-P157 landed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
