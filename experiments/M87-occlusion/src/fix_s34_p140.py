"""M87 -- record P140: appending section 34 broke two committed verifiers.

Both defects were in the instrument, not in the numbers, and both were
repaired in the instrument.  This is deliberately a separate fact from P139:
P139 is a discipline I failed to carry forward into new code, while P140 is
about already-passing code being invalidated by text appended beneath it.
"""
import pathlib

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
ANCHOR = "Three limits, stated rather than buried."
GUARD = "the natural adversary of an earlier section"

PARA = """**Appending this section also broke two verifiers that had been committed
green, and in both cases the number was right and the instrument was wrong.**
`verify_s33.py` sliced its scope as `raw[i:]` from the §33 heading to the end
of the file, despite a docstring stating it was scoped to §33 -- so §34's
legitimate citation of `55.321` raised a count from 2 to 3. That docstring
also forbids the repair that suggests itself: bumping the expectation "ends in
someone weakening it to a presence check". The defect was the missing end
delimiter, so §33 now terminates at the §34 heading, and every other count in
it is unchanged at the narrower scope. `verify_s34` had the same unterminated
slice and was correct only by being last; it now looks for a following
section and falls back to EOF.

**The defect then demonstrated itself.** My first attempt to check this fact
pinned the broken scope's reading at 3, and it immediately read 4 -- because
the paragraph you are reading cites the figure again, and the broken scope
swallows §34 too. So the literal 3 is recorded here as history, and what the
verifier actually enforces is an identity: the broken scope reads the correct
count plus however many times §34 quotes the number. A pinned literal in a
growing document is the same class of mistake as the unterminated slice.

`verify_s32` failed differently and by design. It re-counts M87's scripts from
disk rather than trusting `93-audit.json`, because `P124`'s safety argument --
that no measurement script passes the flag that would let a 40-frame sidecar
apply -- is a standing claim about the whole tree, not a snapshot. Tonight's
new scripts moved the measurement denominator from 97 to 104. **The zeros both
re-derived as zero**, so the claim itself survived intact; only its denominator
was stale. §32 already records this same mechanism catching me when I had
written "30 scripts" and there were 116. The running total is deliberately
kept at a **single** live site in §32, maintained by `fix_audit.py`, and is
not restated here: a second copy would be a second thing to go stale, and it
would collide with `verify_s32`'s own assertion that the figure appears
exactly once.

Two notes on how that was repaired, because both could have gone the other
way. Three of tonight's scripts do document harness work but do not match the
`append/verify/control/fix` prefix that `verify_s32` uses to exclude harness,
so they count as measurement scripts. I did **not** widen that filter: "0 of
N" is a stronger claim at larger N, and shrinking N to flatter my own number
is the failure mode this report exists to avoid. The refresh script itself
first landed in the measurement set and **its own assertion fired against it**
-- it quotes the flag in prose and in a regex -- which is precisely the false
positive the prefix filter was built for, so it was renamed to the harness
convention rather than exempted by a new rule.

The generalisation is worth more than either repair: **a later section is the
natural adversary of an earlier section's verifier.** A checker that passed
when it was written is not a checker that passes now, and neither of these
would have been caught by re-running only the section I was working on."""

ROW = (
    "| P140 | **Appending §34 broke two verifiers that had been committed "
    "green; both defects were in the instrument, not the numbers.** "
    "`verify_s33` sliced its scope to end-of-file rather than to the §34 "
    "heading, so §34's legitimate citation of `55.321` pushed a count 2 -> 3; "
    "at the corrected scope every other count in §33 is unchanged. "
    "`verify_s32` re-counts scripts from disk by design, and tonight's new "
    "scripts moved its measurement denominator 97 -> 104 -- but both zeros "
    "re-derived as **0**, so `P124`'s claim survived and only its denominator "
    "was stale. | Neither was repaired by bumping an expectation; "
    "`verify_s33`'s own docstring forbids that as the road to a presence "
    "check. The harness prefix filter was **not** widened to shrink the "
    "denominator, since 0-of-N is stronger at larger N. A later section is "
    "the natural adversary of an earlier section's verifier, and re-running "
    "only the section under edit would have caught neither. | MEASURED |"
)


def main():
    raw = DOC.read_bytes().decode("utf-8")
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"
    assert "| P140 |" not in raw, "P140 already present"
    assert GUARD not in raw, "amendment already applied"
    assert "| P139 |" in raw, "P139 must land first"
    n = raw.count(ANCHOR)
    assert n == 1, f"anchor appears {n} times, expected exactly 1"
    assert ROW.count("|") - ROW.count("&#124;") == 5, "bad pipe count"
    assert ROW.count("`") % 2 == 0, "odd backtick count"
    for line in PARA.split("\n"):
        assert len(line) <= 80, f"line too wide ({len(line)}): {line[:60]}"

    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(ANCHOR, body + "\r\n\r\n" + ANCHOR, 1)

    i = raw.index("| P139 |")
    j = raw.index("\r\n", i) + 2
    raw = raw[:j] + ROW + "\r\n" + raw[j:]

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode("utf-8"))
    print(f"added P140 and the 34.9 paragraph; {raw.count(chr(10))} lines")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
