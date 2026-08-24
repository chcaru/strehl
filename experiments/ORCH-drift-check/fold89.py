"""Fold the C1 blank-line defect and the false-RED it produced in my own control."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1448,
     "**THE CITATION CHECKER WAS MANUFACTURING CITATIONS NOBODY WROTE, AND 19 OF THE 20 PASSED "
     "SILENTLY.** `corpus_lint`'s C1 matched `question\\s+(?=\\d)` with `\\s+` crossing blank lines, so a "
     "`## Facts` heading followed by a list item `1. **MEASURED...` was read as a citation to fact 1, "
     "and a heading ending in the word \"question\" followed by a paragraph opening `49 986 adjacent "
     "background pairs` (M87-occlusion.md:3736) was read as `question 49`. Survey across the whole "
     "corpus: **12 832 citations on one line, 172 across one newline, 20 across a blank line -- and "
     "20/20 of the blank-line class were phantoms.** Fixed by forbidding a blank line in the gap while "
     "keeping the one-newline wrap, since 172 real citations live there. Five bars: dangling same-line "
     "citation still caught, dangling **wrapped** citation still caught, heading-plus-list not caught, "
     "M87's phantom gone, **no other violation count changed**.",
     "**The 19 silent passes are the finding, not the 1 failure.** A phantom `Facts 1` resolves -- fact "
     "1 exists -- so the malformed parse was validated against a real item and disappeared. Only the "
     "20th pointed at a number nobody had allocated, and that single accident is the entire reason the "
     "defect became visible after 153 files and 47 rules. **A parser that accepts a malformed input and "
     "then successfully resolves it is strictly worse than one that rejects it**, because the resolution "
     "is what hides the error. Note the shape: the check that polices citation integrity across the "
     "corpus had itself been silently wrong about what a citation is, and no amount of running it "
     "green could have revealed that.",
     "ORCH `c1_gap_survey.py` + `c1_controls.py`, 5/5 bars with 2 reds planted (MEASURED)"),
]

DISCIPLINES = [
    (730,
     "**When a validator quotes its input, parse its output into records, not lines -- a wrapped quote "
     "puts a newline inside the message.** My control for the C1 fix (fact 1448) split the linter's "
     "output on `\\n` and tested `\"99998\" in line`; the violation was present but its number sat on the "
     "record's second line, so the bar reported **FAIL on a fix that was correct**. That is a **false "
     "RED**, and its consequence class is worse than a false green in one specific way: **it argues for "
     "discarding a good change.** I nearly reverted the fix. Delimit records by the "
     "`path:line: [CODE]` prefix and join continuations. This is the same mechanism as the "
     "wrapped-prose search rule, relocated from source text to tool output, which is why the earlier "
     "rule did not protect me: I had filed it under \"reading Markdown\", and the instance arrived "
     "while reading stdout."),
    (731,
     "**Prefer a measured narrowing to a guessed one: survey the population a pattern matches before "
     "you tighten it.** The C1 fix had two plausible forms -- forbid blank lines, or require the "
     "citation to be on one line. The second is simpler and stricter and would have **destroyed 172 "
     "real citations**, all of them invisible in the green run because narrowing a check removes "
     "violations rather than adding them. The 10-minute survey (`c1_gap_survey.py`: 12 832 / 172 / 20) "
     "chose between them on evidence and simultaneously proved the false-positive class was 100% pure. "
     "**A tightening cannot be validated by the gate going green, because going green is what a "
     "too-tight gate does.**"),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1447 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^729\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded fact 1448, disciplines 730-731")


if __name__ == "__main__":
    main()
