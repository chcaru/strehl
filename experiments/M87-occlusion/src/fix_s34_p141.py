"""M87 -- record P141: the exit-code trap, measured rather than inherited.

The orchestrator corrected their own statement of this trap (count framing ->
race framing) and asked only whether any gate of mine reads $LASTEXITCODE
after a pipeline containing -First.  None does.  But every green reading in
this milestone comes through `2>&1 | Out-String`, and the PASS criterion is
code 0 -- the direction a lost exit code manufactures.  The corrected rule
asserts Out-String is safe by construction; since the previous version of the
rule had not survived measurement, this one was measured too.

Two things came out of it that the orchestrator does not have.
"""
import pathlib

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
ANCHOR = "Three limits, stated rather than buried."
GUARD = "reports \u22121, never 0"

PARA = """**A last check on the instrument that certified everything above.** Every
green reading in this milestone is `python <verifier> 2>&1 | Out-String`
followed by `$LASTEXITCODE`, and the pass criterion is **0** -- which is the
direction a lost exit code manufactures, so a genuine failure would read as a
pass. The rule I was given says `Out-String` is safe because it must drain the
stream. That rule had already been corrected once, so it was measured:
`exitcode_probe.ps1` runs six pipeline shapes against a process whose true
code is **1**, at 10, 200 and 5000 lines, each arm preceded by a `cmd /c
exit 0` pre-clear so that a failure to set reads 0 rather than the previous
arm's value, and `exitcode_repeat.ps1` repeats the whole thing 12 times.

**The shapes this report relies on never lost the code: 180 of 180
observations** of capture-first, `Out-String`, `Out-String -Width`,
`Select-Object -Last`, and the exact gate shape used tonight all reported the
true **1**, on runs where the trap demonstrably fired. So §29-§34's 599 checks
rest on a shape that was verified rather than assumed.

Two results worth passing back. First, **the trap reports \u22121, never 0**, on
`PSVersion 5.1.26100.9168` -- in every corrupted observation across all 12
runs. That matters for anyone re-testing it: a gate written `if ($code -ne 0)
{ throw }` *catches* the trap here, while a probe that looks specifically for
0 records a false INCONCLUSIVE. Mine did exactly that on its first run, and
only refused to certify because the positive control was written as a gate
rather than as a note.

Second, **the race framing is confirmed against the count framing by direct
observation**: across 12 identical runs the number of corrupted arms varied
**4 to 6 of 6**, and a `\u2212First` arm at 10 lines read the true code in one run
and \u22121 in the next. Identical inputs disagreeing is what a race looks like;
no count model can produce it.

**My own error here, since it is the same class as `P139` and `P140`.** I
registered the positive control as `expect = 0`, which encoded the *value* the
orchestrator reported instead of the *property* under test -- that the
observed code differs from the true one. On a host that corrupts to \u22121 the
control could not fire, and the run came back `INCONCLUSIVE`. That is the
correct failure mode and it is the only reason the mistake was cheap, but the
expectation was inherited rather than derived, which is the habit this report
keeps finding in me."""

ROW = (
    "| P141 | **The verification shape this milestone runs on preserves exit "
    "codes: 180 of 180 observations reported the true code, on runs where the "
    "truncation trap demonstrably fired.** Six pipeline shapes against a "
    "process whose true code is 1, at 10/200/5000 lines, pre-cleared per arm, "
    "repeated 12 times. `Out-String`, `Out-String -Width`, `Select-Object "
    "-Last` and capture-first never lost it; the `-First` arms were corrupted "
    "in **12 of 12** runs. | Two corrections to the rule as I received it. The "
    "corrupted value is **&#8722;1, never 0** on `PSVersion 5.1.26100.9168`, so a "
    "probe looking specifically for 0 records a false INCONCLUSIVE -- mine did. "
    "And the corrupted-arm count varied **4 to 6 of 6** across 12 identical "
    "runs, which confirms the race framing over the count framing by direct "
    "observation. | MEASURED |"
)


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    assert "| P141 |" not in raw, "P141 already present"
    assert GUARD not in raw, "amendment already applied"
    assert "| P140 |" in raw, "P140 must land first"
    n = raw.count(ANCHOR)
    assert n == 1, f"anchor appears {n} times, expected exactly 1"
    assert ROW.count("|") - ROW.count("&#124;") == 5, "bad pipe count"
    assert ROW.count("`") % 2 == 0, "odd backtick count"
    for line in PARA.split("\n"):
        assert len(line) <= 80, f"line too wide ({len(line)}): {line[:60]}"

    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    i = raw.index("| P140 |")
    j = raw.index("\r\n", i) + 2
    raw = raw[:j] + ROW + "\r\n" + raw[j:]

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode("utf-8"))
    print(f"added P141 and the 34.9 paragraph; {raw.count(chr(10))} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
