"""Repair fact 1455: it restated fact 1432's measurement. Keep only the new material."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

CLAIM = (
    "**THE MAGENTA DEFECT OF FACT 1432 IS A CLAMP IN THE WRONG PLACE, AND THE REMEDY IS VERIFIED BUT "
    "INERT IN THE SHIPPED COMMAND.** This row deliberately restates fact 1432 rather than re-measuring "
    "it; fact 1432 holds the defect and its numbers, this one holds the mechanism and the fix. Render "
    "order **read from source rather than assumed**: `strehl stack` renders through "
    "`merge_cmd::write_merged` -- **not** `stack.rs`, which serves `argmax-baseline` -- as black, "
    "as-shot green-normalised WB, exposure gain, demosaic, matrix, **clamp(0,1)**, sRGB curve, u16. "
    "**The only clamp is after the matrix.** M109's fix clips conditionally *before* the matrix in "
    "white-balanced camera space at `K0 = 1.0689`; on `argmax-baseline` magenta falls **0.3378 % to "
    "0.0944 %** with the null byte-identical, the negative control shown red, byte-freezes **5/5**, "
    "workspace **394 pass / 0 fail**, and a LibRaw cross-check on **583 873** predicate-selected pinned "
    "quads agreeing to **0.0014**. **It changes nothing in `strehl stack`, because `merge_cmd.rs` "
    "belongs to another agent.**"
)

INTERP = (
    "**Post-matrix clamping is right for gamut and wrong for a pinned sample, and the two had been "
    "conflated in one line of code.** Once a photosite saturates its true value is unknown and bounded "
    "only from below; by the time the clamp runs, the matrix has already mixed a *known-wrong* green "
    "into red and blue, so no later operation can recover neutrality. **The artefact is created one "
    "step before the line that appears to cause it** -- which is why fact 1432 could correctly identify "
    "the defect and still not locate it. The conditional form is what makes the null an identity: an "
    "unconditional clamp at `K` would have clipped genuine red above **~6420 DN** and failed the "
    "byte-identical bar, so **the guard and the fix are the same expression**. Routed to M97 as a "
    "priority insert; the author does not apply it and the applier does not verify it."
)

SRC = "M109-highlights section 6, commit `3e58676`; defect numbers in fact 1432, not restated here"


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    idx = [i for i, l in enumerate(lines) if l.startswith("| 1455 |")]
    assert len(idx) == 1, f"expected exactly 1 row for fact 1455, found {len(idx)}"

    row = f"| 1455 | {CLAIM} | {INTERP} | {SRC} |"
    k = row.count("|") - row.count("\\|")
    assert k == 5, f"fact 1455: {k} unescaped pipes"

    # The numerals D1 flagged as shared with fact 1432 must be gone.
    for bad in ("0.4490", "0.8915", "0.9943", "0.9944", "2.0017", "2.002", "16383"):
        assert bad not in row, f"still restating fact 1432's {bad}"
    assert "fact 1432" in row, "must name the earlier fact -- that is the disclosure"

    lines[idx[0]] = row
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print("repaired fact 1455: duplicate numerals removed, fact 1432 named")


if __name__ == "__main__":
    main()
