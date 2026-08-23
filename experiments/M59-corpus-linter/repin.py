"""One-shot: repair PowerShell here-string apostrophe doubling and re-pin the
numbers in docs/research/M59-corpus-linter.md to sha 82f13b0.

Kept in the experiment directory because AGENTS rule 29 asks that an edit that
consumes its own anchor be counted rather than trusted: this asserts a hit count
for every substitution and refuses to write if one is wrong.
"""
import io
import sys

PATH = "docs/research/M59-corpus-linter.md"

PAIRS = [
    ("corpus_lint: 77 markdown file(s), 27 rust file(s); 626 facts, 219 disciplines,\n"
     "             128 questions, 11 risks, 40 rules\n"
     "corpus_lint: FAIL \u2014 23 violation(s): S1=4, S2=3, S3=2, S4=14",
     "corpus_lint: 78 markdown file(s), 27 rust file(s); 635 facts, 221 disciplines,\n"
     "             129 questions, 11 risks, 40 rules\n"
     "corpus_lint: FAIL \u2014 22 violation(s): S1=4, S2=3, S3=2, S4=13"),
    ("| S4 mixed line endings | **14 violations** |",
     "| S4 mixed line endings | **13 violations** |"),
    ("**clean** across 626 + 219 + 128 + 11 + 40 items",
     "**clean** across 635 + 221 + 129 + 11 + 40 items"),
    ("| C1 citation resolution | 0 | **clean** across **4,458** references |",
     "| C1 citation resolution | 0 | **clean** across **4,632** references |"),
    ("a denominator of 4,458.", "a denominator of 4,632."),
    ("### 3.1 S2 \u2014 445 of 626 fact rows do not render as table rows",
     "### 3.1 S2 \u2014 454 of 635 fact rows do not render as table rows"),
    ("| \u00a74 with lines 949, 955, 958 deleted | 635 `tr`, 2525 `td`, "
     "**633 data rows** | 635 `tr`, 2525 `td`, **633 data rows** |",
     "| \u00a74 with lines 949, 955, 958 deleted | 644 `tr`, 2561 `td`, "
     "**642 data rows** | 644 `tr`, 2561 `td`, **642 data rows** |"),
    ("633 \u2212 7 = 626,", "642 \u2212 7 = 635,"),
    ("**445 of 626 fact rows (71.1%) render as paragraph text.**",
     "**454 of 635 fact rows (71.5%) render as paragraph text.**"),
    ("The linter reaches the same 445 by a completely different route \u2014 static\n"
     "strand-counting, no renderer \u2014 as `5 + 2 + 438`. Two methods, one number.",
     "The linter reaches the same 454 by a completely different route \u2014 static\n"
     "strand-counting, no renderer \u2014 as `5 + 2 + 447`. Two methods, one number."),
    ("finding at 148x the scale", "finding at 151x the scale"),
    ("Here 445 rows lose their table-ness entirely.",
     "Here 454 rows lose their table-ness entirely."),
    # 5.1 / 5.2 denominators
    ("| \u00a74 fact rows | 626 | 100% |", "| \u00a74 fact rows | 635 | 100% |"),
    ("| \u2026containing \u22651 enumeration of resolvable corpus numbers | 94 | 15.0% |",
     "| \u2026containing \u22651 enumeration of resolvable corpus numbers | 96 | 15.1% |"),
    ("| \u2026containing an `N of M <corpus-noun>` claim | **1** | **0.2%** |",
     "| \u2026containing an `N of M <corpus-noun>` claim | **2** | **0.3%** |"),
    ("no opinion about the other 625 rows.", "no opinion about the other 634 rows."),
    ("misled, which is why the number 1/626 is printed here",
     "misled, which is why the number 1/635 is printed here"),
    ("**4,458 references resolved,\n0 dangling**, across 77 markdown and 27 Rust files",
     "**4,632 references resolved,\n0 dangling**, across 78 markdown and 27 Rust files"),
    ("| `ref` (plain `fact N`) | 4,458 | must resolve \u2014 **all do** |",
     "| `ref` (plain `fact N`) | 4,632 | must resolve \u2014 **all do** |"),
    ("| `qualified` (`M25 fact 200`, `M25 \u00a77 fact 190`) | 226 |",
     "| `qualified` (`M25 fact 200`, `M25 \u00a77 fact 190`) | 234 |"),
    ("| `sub` (`fact 198c`) | 42 |", "| `sub` (`fact 198c`) | 47 |"),
    ("| `block` (`facts 250+`, `facts 520\u2013539 reserved`) | 21 |",
     "| `block` (`facts 250+`, `facts 520\u2013539 reserved`) | 22 |"),
    ("| by kind | 3,566 fact \u00b7 453 rule \u00b7 377 question \u00b7 316 discipline \u00b7 35 risk | |",
     "| by kind | 3,703 fact \u00b7 466 rule \u00b7 395 question \u00b7 336 discipline \u00b7 35 risk | |"),
    ("| by area | reports 2,735 \u00b7 SYNTHESIS 1,590 \u00b7 Rust 422 | |",
     "| by area | reports 2,875 \u00b7 SYNTHESIS 1,639 \u00b7 Rust 421 | |"),
    ("42 `sub` tokens exist in the corpus at\nthe pinned sha",
     "47 `sub` tokens exist in the corpus at\nthe pinned sha"),
    ("`blank line inside a table: the 621 row(s) below it",
     "`blank line inside a table: the 630 row(s) below it"),
    ("the entire 626-row table", "the entire 635-row table"),
    ("**23 violations at HEAD including\n445 fact rows that do not render**",
     "**22 violations at HEAD including\n454 fact rows that do not render**"),
    ("python scripts/corpus_lint.py                       # 23 violations, exit 1",
     "python scripts/corpus_lint.py                       # 22 violations, exit 1"),
    ("71% of the corpus''s fact rows", "71% of the corpus's fact rows"),
]


def main():
    text = io.open(PATH, encoding="utf-8", newline="").read()

    bad = []
    for old, new in PAIRS:
        n = text.count(old)
        if n != 1:
            bad.append((n, old.splitlines()[0][:70]))
            continue
        text = text.replace(old, new)
    if bad:
        for n, snippet in bad:
            sys.stderr.write("count=%d for %r\n" % (n, snippet))
        sys.stderr.write("refusing to write\n")
        return 1

    # PowerShell single-quoted here-strings do not need doubled apostrophes;
    # I doubled them anyway and they landed literally. Repair, but only where
    # the pair sits between two word characters (a possessive), never in code.
    import re
    before = text.count("''")
    text = re.sub(r"(?<=\w)''(?=\w)", "'", text)
    after = text.count("''")
    sys.stderr.write("apostrophe pairs: %d before, %d after\n" % (before, after))

    text = text.replace("\r\n", "\n").rstrip("\n") + "\n"
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    print("wrote %s (%d bytes)" % (PATH, len(text)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
