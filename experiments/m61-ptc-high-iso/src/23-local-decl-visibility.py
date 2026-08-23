"""M61 step 23 -- make this report's local numbering visible to corpus_lint.

THE DEFECT, found by running the linter after appending facts 50-60.

`corpus_lint`'s C1 check resolves a citation like `fact 55` and passes it if
EITHER the number exists in SYNTHESIS's global namespace OR the report
declares it locally:

    if index.resolves(kind, num): continue
    if num in local:              continue   # the report's own numbering

So local numbering is supported. But `local_declarations()` finds
declarations with

    re.compile(r"\\*\\*(?:Discipline|Question|Fact|Risk)\\s+(\\d+)\\.?\\*\\*")

which requires the number to sit immediately before the closing `**`. The
convention actually used across the corpus -- M48c does it, and so does this
report for all 60 facts -- is

    **Fact 50 (DERIVED).**

with the rule-12 label INSIDE the bold. That does not match. So NO local
declaration in this report is detected, `local` is empty, and every local
citation is resolved against SYNTHESIS's global numbering instead.

WHY THAT IS WORSE THAN A LINT MISS. It does not fail; it PASSES, whenever
the local number happens to exist in SYNTHESIS. SYNTHESIS has 925 facts, so
every local citation below 925 passes -- against the wrong fact. This
report's facts 1-49 passed clean for that reason alone. Appending facts
50-60 only surfaced it because SYNTHESIS's 50-60 range holds items of a
different KIND, so resolution failed loudly for once. **The 21 new
violations are not a new defect; they are the first time an old one made a
noise.**

The hazard is not the linter's. It is that a reader or a later agent who
resolves this report's bare `fact 41` against SYNTHESIS gets a different
fact, and nothing anywhere says otherwise.

THE FIX, scoped deliberately narrowly.

I am NOT editing `scripts/corpus_lint.py`. It is shared, several agents are
live in this tree, and widening LOCAL_DECL would change lint results under
every one of them mid-flight -- including surfacing new violations in M48c
and others while their authors are working. That is a corpus-wide change
and it is not mine to make unilaterally; it is filed as a question instead.

What I can do is make THIS report declare itself in the form the existing
linter already understands, without weakening rule 12. One rule, applied to
Fact declarations only -- close the bold straight after the number and
reopen it:

    **Fact 50 (DERIVED).**            -> **Fact 50.** **(DERIVED).**
    **Fact 58 (ARGUED) - prose.**     -> **Fact 58.** **(ARGUED) - prose.**

Renders identically, keeps the rule-12 label on the claim, and matches
LOCAL_DECL. Scoped to Fact because `fact N` is the citation kind C1 is
failing on. Disciplines and Questions in this report use different shapes
(`**Discipline 14 - prose.**`, `**Question 9.**`) and only Question is
already visible; the Discipline case is recorded in the report rather than
churned, because no citation of it currently fails.

GUARD, per discipline 11, because this is a mechanical edit to a 1400-line
document and "be careful" is not a control. The transform is EXACTLY
INVERTIBLE, which gives a stronger guard than counting: apply the inverse
and assert the result is byte-identical to the input. The script ABORTS
unless all of these hold:

  1. inverse(transform(text)) == text, byte for byte
  2. the multiset of Fact declaration numbers is unchanged
  3. the line count and the count of non-empty lines are unchanged
  4. no line without a Fact declaration is touched

A dry run prints the summary and writes nothing unless --apply.
"""
import os
import re
import sys
from collections import Counter

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "..", "docs", "research",
                      "M61-ptc-high-iso-measured.md")

# `**Fact 50 (` -> `**Fact 50.** **(`   (both declaration shapes)
FWD = re.compile(r"\*\*Fact (\d+) \(")
INV = re.compile(r"\*\*Fact (\d+)\.\*\* \*\*\(")
# the form corpus_lint already understands
LOCAL_DECL_OK = re.compile(
    r"\*\*(?:Discipline|Question|Fact|Risk)\s+(\d+)\.?\*\*", re.I)


def transform(text):
    return FWD.sub(lambda m: f"**Fact {m.group(1)}.** **(", text)


def inverse(text):
    return INV.sub(lambda m: f"**Fact {m.group(1)} (", text)


def fact_nums(text, pat):
    return Counter(int(m.group(1)) for m in pat.finditer(text))


def visible(text):
    return Counter(int(m.group(1)) for m in LOCAL_DECL_OK.finditer(text))


def main() -> int:
    apply = "--apply" in sys.argv
    with open(REPORT, encoding="utf-8") as fh:
        before = fh.read()

    b_vis = visible(before)
    b_fact = fact_nums(before, FWD)
    print(f"before: {sum(b_fact.values())} Fact declarations in the labelled "
          f"form, {sum(b_vis.values())} declarations visible to corpus_lint")
    if not b_fact:
        print("nothing to transform")
        return 0

    after = transform(before)
    ok = True

    # ---- guard 1: exact invertibility, the strongest available ---------
    if inverse(after) != before:
        print("GUARD 1 FAILED: transform is not invertible byte-for-byte")
        ok = False

    # ---- guard 2: declaration numbers preserved -----------------------
    a_fact = fact_nums(after, INV)
    if a_fact != b_fact:
        print(f"GUARD 2 FAILED: lost {b_fact - a_fact}, gained {a_fact - b_fact}")
        ok = False

    # ---- guard 3: line structure untouched ----------------------------
    lb, la = before.splitlines(), after.splitlines()
    if len(lb) != len(la):
        print(f"GUARD 3 FAILED: line count {len(lb)} -> {len(la)}")
        ok = False
    elif len([x for x in lb if x.strip()]) != len([y for y in la if y.strip()]):
        print("GUARD 3 FAILED: non-empty line count changed")
        ok = False

    # ---- guard 4: only declaration lines differ -----------------------
    if len(lb) == len(la):
        for i, (x, y) in enumerate(zip(lb, la)):
            if x != y and not FWD.search(x):
                print(f"GUARD 4 FAILED: line {i+1} changed with no Fact decl")
                ok = False
                break

    a_vis = visible(after)
    print(f"after:  {sum(fact_nums(after, INV).values())} Fact declarations, "
          f"{sum(a_vis.values())} declarations visible to corpus_lint")
    print(f"newly visible: +{sum(a_vis.values()) - sum(b_vis.values())}")

    if not ok:
        print("\nABORTED -- guards failed, nothing written")
        return 1
    print("\nall four guards PASS (including exact invertibility)")

    if apply:
        with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(after)
        print(f"[wrote {os.path.normpath(REPORT)}]")
    else:
        print("dry run -- pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
