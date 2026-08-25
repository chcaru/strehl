"""M87 -- correct P142's "corrupted value" claim using a distinguishable sentinel.

ORCH fact 1507 says the stale exit code is RETAINED VERBATIM rather than
coerced.  P142 reported "7.6.5 corrupts to 0" from probes that pre-cleared to
0, so that claim could not distinguish coercion from my own prime echoing back.

Re-measured with sentinel 7 (neither 0 nor the true code 1), which makes the
three hypotheses mutually exclusive.  Result: 7.6.5 RETAINS (reads 7, 10/10),
so fact 1507 is right and my value claim was an artefact -- but 5.1 writes a
genuine -1 that is neither sentinel nor true code, so 1507 is not the whole
story either.

Same guards as P144-P146: control_s29 anchors, and the 100.00% collision.
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

MINUS = "\u2212"

ROW = (
    "| P147 | **P142's corrupted-value claim was an artefact of my own "
    "pre-clear, and correcting it splits the two engines by MECHANISM rather "
    "than by value.** P142 reported 7.6.5 corrupting to 0 -- measured with a "
    "pre-clear of 0, so coercion and stale retention were indistinguishable. "
    "Re-primed with sentinel **7**, which is neither 0 nor the true code 1, "
    "the three hypotheses separate: **7.6.5 reads 7 in 10 of 10** (the prime "
    "survives untouched -- RETAINED), while **5.1 reads &#8722;1 in 9 of 10** "
    "and the true code once. &#8722;1 is neither the sentinel nor the true "
    "code, so 5.1 **actively writes** a value where 7.6.5 merely fails to "
    "update one. | **So fact 1507 is right about 7.6.5 and incomplete about "
    "5.1, and the correction costs P142 nothing that mattered.** The loss "
    "*rates* stand: with a prime of 0 against a true code of 1, a read of 0 is "
    "unambiguous evidence the live code was not read, which is the only "
    "determination the rates ever needed. What dies is the claim about which "
    "value the corruption takes. **A sentinel distinct from the true code also "
    "repairs ORCH's warning that no observed code proves liveness** -- primed "
    "with 7, a read of 1 can only have come from the process. `-Last 3` "
    "and `Select-String` read the true code 10 of 10 on **both** engines, "
    "independently reproducing the fleet's safe-shape table. | MEASURED |"
)

ANCHOR = "Three limits, stated rather than buried."

PARA = """**A refinement from the fleet invalidated one of my own published
numbers, and re-measuring it produced a better result than the one it
replaced.** The correction is that a trapped exit code is *retained verbatim*
from whatever preceded it rather than coerced to a constant. P142 reported
PowerShell 7.6.5 "corrupting to 0" -- and P142's probes pre-cleared to 0. Those
two facts cannot be told apart by any amount of re-reading; the number was
undetermined by my own design and I did not notice until the refinement
arrived.

The fix is a prime that is neither the true code nor a plausible corruption.
With sentinel **7** against an emitter whose true code is **1**, three
hypotheses become mutually exclusive: a read of 7 means the prime survived, a
read of 0 means the engine wrote a zero of its own, and a read of 1 means the
process was reaped. Ten repetitions per shape per engine, with the prime
asserted before every single arm.

| engine | shape | reads | verdict |
|---|---|---|---|
| 7.6.5 | `Select-Object -First 3` | **7**, 10/10 | prime RETAINED |
| 7.6.5 | `-Last 3`, `Select-String` | **1**, 10/10 | live |
| 5.1 | `Select-Object -First 3` | **&#8722;1** 9/10, **1** once | genuine WRITE |
| 5.1 | `-Last 3`, `Select-String` | **1**, 10/10 | live |

**The two engines are not doing the same thing.** 7.6.5 leaves the variable
untouched, so the previous command's value survives; 5.1 actively writes
&#8722;1, a value that is neither my sentinel nor the true code and therefore
cannot be explained by retention at all. The fleet-wide refinement is correct
for 7.6.5 and incomplete for 5.1, and I would not have been able to say that
from a probe primed with 0.

**What this costs P142 is exactly the claim about values, and nothing else.**
The loss *rates* -- 9 of 9 arms clean on 7.6.5, 6 of 9 failing on 5.1, and the
causal sleep ladder -- were determinations of whether the read differed from
the true code, and a prime of 0 against a true code of 1 answers that
unambiguously. The engine-is-the-whole-variable conclusion is untouched.

**Two things this hands back, which is why it was worth the hour.** First, the
standing warning that no observed exit code proves the read was live is
defeated by construction: prime with a value distinct from the true code, and a
read of the true code can only have come from the process. Second, `-Last 3`
and `Select-String` read the true code ten times out of ten on **both**
engines under adversarial priming, which independently reproduces the
safe-shape table rather than inheriting it.

**And the probe caught one defect in itself before it caught anything about
PowerShell.** The first version emitted its lines from a PowerShell script
block instead of a native process, and every shape -- including the unsafe one
-- read the true code, because a script block leaves no process unreaped. Run
as written it would have certified `Select-Object -First` as safe on both
engines. **An instrument for a native-process defect must contain a native
process**, which is obvious once stated and was not obvious while typing it."""


def main():
    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P147 |" in raw:
        print("P147 already present -- nothing to do")
        return

    bare = ROW.replace("\\|", "")
    assert bare.count("|") == 5, "fact row needs exactly 5 unescaped pipes"
    assert ROW.count("`") % 2 == 0, "fact row backtick count is odd"
    assert PARA.count("`") % 2 == 0, "paragraph backtick count is odd"
    assert MINUS not in ROW, "fact rows use the &#8722; entity, not U+2212"
    for f in FORBIDDEN:
        if f in ROW or f in PARA:
            sys.exit("NEW PROSE REPRODUCES A control_s29 ANCHOR: %r" % f)
    if "100.00%" in ROW or "100.00%" in PARA:
        sys.exit("NEW PROSE QUOTES 100.00%% -- the exact P143 collision")

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p147.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    if raw.count(ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P146 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P146 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    for f in FORBIDDEN:
        if after.count(f) != 1:
            sys.exit("POST-WRITE: control_s29 anchor %r moved" % f)
    if "| P147 |" not in after:
        sys.exit("POST-WRITE CHECK FAILED: P147 missing")
    print("added P147 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()
