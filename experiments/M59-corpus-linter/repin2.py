"""Second re-pin of docs/research/M59-corpus-linter.md, to sha 7a9b76b.

The corpus is under concurrent edit by other agents, so the row totals moved
twice while this milestone ran. This rewrites the affected passages wholesale
rather than patching numbers one at a time, and asserts each anchor matches
exactly once before writing anything (AGENTS rule 29).

The substantive change is S4: it was rewritten mid-milestone to read the git
index instead of the working tree, which took it from 13 violations to 0.
"""
import io
import sys

PATH = "docs/research/M59-corpus-linter.md"

OLD_S3_DEVIATION = """1. **S3 was split into S3 and S4 after pre-registering.** S3 is now the
   trailing-newline and SYNTHESIS-CR property (the rule 37 defect); S4 is
   "mixed `\\r\\n` and bare `\\n` in one file". They were one bullet in \u00a70.2.
   The reason is in \u00a73: S4 finds 14 files, and a check that is permanently red
   because agents use different editors is a check that gets switched off. A
   separate id can be excluded with `--only` without disabling the rule 37
   property, which is the one that matters."""

NEW_S3_DEVIATION = """1. **S3 was split into S3 and S4 after pre-registering, and S4 was then
   rewritten.** S3 is the trailing-newline property (the rule 37 defect); S4 is
   "the committed blob has mixed line endings". They were one bullet in \u00a70.2.
   The first implementation of both counted `\\r\\n` and `\\n` **on disk** and
   reported 13 violations. That was wrong, and \u00a73.3 gives the measurement that
   proves it: the working tree is not the repository. Both now ask
   `git ls-files --eol` and judge the committed content, and both **skip with a
   printed NOTE** when git is unavailable rather than guessing."""

OLD_S3_BULLET = """**S3 (2):** `docs/research/M47-gain-blast-radius.md:208` and
`docs/research/M49-unapplied-findings.md:190` do not end in a newline. This is
rule 37's named failure mode.

**S4 (14):** files mixing CRLF and bare LF \u2014
`crates/strehl-cli/examples/m60-disagreement.rs`, and in `docs/research/`:
`M16-orientation-fpn-measured.md`, `M25-simulator-measured.md`,
`M31-VERIFICATION.md`, `M36-VERIFICATION.md`, `M39-verify-detail-metric.md`,
`M41-r3-kill-measured.md`, `M48-read-noise-measured.md`,
`M52-gate-cluster-verified.md`, `M54-clip-mask-measured.md`,
`M56-citation-audit.md`, `M58-citation-content-repaired.md`,
`M58c-repair-audit.md`, `M60-robustness-mask-at-merge-time.md`.
**ARGUED:** S4 is the check most likely to be turned off, and I would rather the
project turn off S4 than turn off the linter. It is a separate id for that reason."""

NEW_S3_BULLET = """**S3 (4 violations), all real and all one-character fixes:**

| File:line | Defect |
|---|---|
| `docs/research/M47-gain-blast-radius.md:208` | no trailing newline |
| `docs/research/M49-unapplied-findings.md:190` | no trailing newline |
| `docs/captures-needed.md:813` | ends in 2 newlines |
| `docs/research/OWNER-QUESTIONS.md:1246` | ends in 2 newlines |

The first two are rule 37's named failure mode: `\\Z` inside an item-end
lookahead eats the final newline when the anchor is the last item.

### 3.3.1 S4 = 0, and the reason is the most transferable finding here

**S4 found 13 violations, and all 13 were false.** This is worth more than the
check.

The obvious implementation of "mixed line endings" counts `\\r\\n` and bare `\\n`
in the file on disk. Mine did, and it reported 13 files mixing CRLF and LF,
including four of the corpus's most-cited reports. The list looked exactly like a
real defect: some files converted, some not, a few mixed within themselves.

It was an artifact of my checkout. **MEASURED**, three ways:

| Question | Answer |
|---|---|
| `git config core.autocrlf` in this submodule | `true` |
| `git ls-files --eol`: tracked text files by **index** ending | **1,351 `i/lf`, 0 `i/crlf`, 0 `i/mixed`** |
| `M41-r3-kill-measured.md`: index vs disk | index 0 CRLF / 998 LF; **disk 968 CRLF / 30 LF** |

Every one of the 13 files is pure LF in the object database. `core.autocrlf=true`
rewrote them to CRLF on checkout; the files that came out *mixed* are the ones an
LF-writing tool edited afterwards. **The check was measuring which editor and
which git config I happen to use.** It would be permanently red on every Windows
machine and permanently green on every Linux one, and neither colour would say
anything about the repository.

S4 now calls `git ls-files --eol` and judges the **committed blob**. At the
pinned sha it reports **0**, which is the true answer. If git is not available
the check prints a NOTE and skips, because a check that guesses is worse than a
check that abstains.

**ARGUED, and it generalises past line endings.** A check can be correct in its
logic, fire reliably, produce a plausible-looking list, and still be measuring
the wrong object. Nothing in a red exit code distinguishes that from a real
finding \u2014 discipline 351's point, one level up: it is not enough to confirm the
failure is *your* check firing; you have to confirm your check is looking at the
thing you meant. The only reason I caught it is that git printed
`LF will be replaced by CRLF the next time Git touches it` while I was reading an
unrelated diff."""

OLD_PLANT_5_6 = """| 5 | S3 | convert SYNTHESIS wholesale to CRLF | exit 0, n=0 | exit 1, n=1 | `SYNTHESIS.md contains 3496 CR; it is LF-only` |
| 6 | S4 | give three lines CRLF endings in an LF file | exit 0, n=0 | exit 1, n=1 | `mixed line endings: 3 CRLF and 3493 bare LF` |"""

NEW_PLANT_5_6 = """| 5 | S3 | commit SYNTHESIS wholesale as CRLF | exit 0, n=0 | exit 1, n=1 | `SYNTHESIS.md is committed with CRLF line endings; it is LF-only` |
| 6 | S4 | commit AGENTS.md with three CRLF lines among LF ones | exit 0, n=0 | exit 1, n=1 | `AGENTS.md:1: committed with MIXED line endings` |"""

OLD_PROBE_INTRO = """*A check that has never been seen to fail has not been tested* (AGENTS rule 36,
SYNTHESIS discipline 351). `experiments/M59-corpus-linter/power_probe.py` builds
a probe root \u2014 `SYNTHESIS.md` **with the three S2 blank lines removed**, plus
`AGENTS.md` and one small Rust file \u2014 establishes that it is clean, then plants
one violation at a time."""

NEW_PROBE_INTRO = """*A check that has never been seen to fail has not been tested* (AGENTS rule 36,
SYNTHESIS discipline 351). `experiments/M59-corpus-linter/power_probe.py` builds
a probe root \u2014 `SYNTHESIS.md` **with the three S2 blank lines removed**, plus
`AGENTS.md` and one small Rust file \u2014 establishes that it is clean, then plants
one violation at a time. The probe root is a throwaway `git init` repository
staged with `core.autocrlf=false`, because S3's and S4's line-ending halves are
judged on the index and cannot be exercised without one (\u00a73.3.1). It is deleted
at the end of the run."""

PAIRS = [
    (OLD_S3_DEVIATION, NEW_S3_DEVIATION),
    (OLD_S3_BULLET, NEW_S3_BULLET),
    (OLD_PLANT_5_6, NEW_PLANT_5_6),
    (OLD_PROBE_INTRO, NEW_PROBE_INTRO),
    # --- re-pin to 7a9b76b ---
    ("82f13b03e73f573add3f08754a5439a4beb90bc5",
     "7a9b76bd4523d3bdeead32cc0a2c3fef8f39fae9"),
    ("**635 facts, 221 disciplines, 129 questions, 11 risks, 40 rules.**",
     "**639 facts, 223 disciplines, 131 questions, 11 risks, 40 rules.**"),
    ("corpus_lint: 78 markdown file(s), 27 rust file(s); 635 facts, 221 disciplines,\n"
     "             129 questions, 11 risks, 40 rules\n"
     "corpus_lint: FAIL \u2014 22 violation(s): S1=4, S2=3, S3=2, S4=13",
     "corpus_lint: 78 markdown file(s), 27 rust file(s); 639 facts, 223 disciplines,\n"
     "             131 questions, 11 risks, 40 rules\n"
     "corpus_lint: FAIL \u2014 11 violation(s): S1=4, S2=3, S3=4"),
    ("| S3 trailing newline / SYNTHESIS CR | **2 violations** | real, minor |\n"
     "| S4 mixed line endings | **13 violations** | real but arguably not worth failing on; see \u00a72 |",
     "| S3 file hygiene | **4 violations** | real, minor, one-character fixes |\n"
     "| S4 line endings in the committed blob | **0** | **clean** \u2014 and see \u00a73.3.1, this check first reported 13 and all 13 were false |"),
    ("**clean** across 635 + 221 + 129 + 11 + 40 items",
     "**clean** across 639 + 223 + 131 + 11 + 40 items"),
    ("| C1 citation resolution | 0 | **clean** across **4,632** references |",
     "| C1 citation resolution | 0 | **clean** across **4,672** references |"),
    ("a denominator of 4,632.", "a denominator of 4,672."),
    ("### 3.1 S2 \u2014 454 of 635 fact rows do not render as table rows",
     "### 3.1 S2 \u2014 458 of 639 fact rows do not render as table rows"),
    ("| \u00a74 with lines 949, 955, 958 deleted | 644 `tr`, 2561 `td`, "
     "**642 data rows** | 644 `tr`, 2561 `td`, **642 data rows** |",
     "| \u00a74 with lines 949, 955, 958 deleted | 648 `tr`, 2577 `td`, "
     "**646 data rows** | 648 `tr`, 2577 `td`, **646 data rows** |"),
    ("642 \u2212 7 = 635,", "646 \u2212 7 = 639,"),
    ("**454 of 635 fact rows (71.5%) render as paragraph text.**",
     "**458 of 639 fact rows (71.7%) render as paragraph text.**"),
    ("The linter reaches the same 454 by a completely different route \u2014 static\n"
     "strand-counting, no renderer \u2014 as `5 + 2 + 447`. Two methods, one number.",
     "The linter reaches the same 458 by a completely different route \u2014 static\n"
     "strand-counting, no renderer \u2014 as `5 + 2 + 451`. Two methods, one number."),
    ("finding at 151x the scale", "finding at 153x the scale"),
    ("Here 454 rows lose their table-ness entirely.",
     "Here 458 rows lose their table-ness entirely."),
    ("| \u00a74 fact rows | 635 | 100% |", "| \u00a74 fact rows | 639 | 100% |"),
    ("| \u2026containing \u22651 enumeration of resolvable corpus numbers | 96 | 15.1% |",
     "| \u2026containing \u22651 enumeration of resolvable corpus numbers | 98 | 15.3% |"),
    ("no opinion about the other 634 rows.", "no opinion about the other 638 rows."),
    ("misled, which is why the number 1/635 is printed here",
     "misled, which is why the number 1/639 is printed here"),
    ("**4,632 references resolved,\n0 dangling**, across 78 markdown and 27 Rust files",
     "**4,672 references resolved,\n0 dangling**, across 78 markdown and 27 Rust files"),
    ("| `ref` (plain `fact N`) | 4,632 | must resolve \u2014 **all do** |",
     "| `ref` (plain `fact N`) | 4,672 | must resolve \u2014 **all do** |"),
    ("| `qualified` (`M25 fact 200`, `M25 \u00a77 fact 190`) | 234 |",
     "| `qualified` (`M25 fact 200`, `M25 \u00a77 fact 190`) | 235 |"),
    ("| by kind | 3,703 fact \u00b7 466 rule \u00b7 395 question \u00b7 336 discipline \u00b7 35 risk | |",
     "| by kind | 3,728 fact \u00b7 470 rule \u00b7 400 question \u00b7 343 discipline \u00b7 35 risk | |"),
    ("| by area | reports 2,875 \u00b7 SYNTHESIS 1,639 \u00b7 Rust 421 | |",
     "| by area | reports 2,902 \u00b7 SYNTHESIS 1,653 \u00b7 Rust 421 | |"),
    ("`blank line inside a table: the 630 row(s) below it",
     "`blank line inside a table: the 634 row(s) below it"),
    ("the entire 635-row table", "the entire 639-row table"),
    ("**22 violations at HEAD including\n454 fact rows that do not render**",
     "**11 violations at HEAD including\n458 fact rows that do not render**"),
    ("python scripts/corpus_lint.py                       # 22 violations, exit 1",
     "python scripts/corpus_lint.py                       # 11 violations, exit 1"),
    ("2. **`OWNER-QUESTIONS.md` does not exist inside the submodule** at the pinned\n"
     "   sha; \u00a70.2 listed it. It is in the scan list and will be picked up if it\n"
     "   appears. **MEASURED:** the submodule root contains `AGENTS.md` and\n"
     "   `README.md` only.",
     "2. **`OWNER-QUESTIONS.md` is at `docs/research/OWNER-QUESTIONS.md`,** not at\n"
     "   the submodule root where \u00a70.2 looked for it. It appeared during this\n"
     "   milestone and is scanned, being under `docs/research/`. S3 finds a defect\n"
     "   in it (\u00a73.3)."),
]


def main():
    text = io.open(PATH, encoding="utf-8", newline="").read()
    bad = []
    for old, new in PAIRS:
        n = text.count(old)
        if n != 1:
            bad.append((n, old.splitlines()[0][:72]))
            continue
        text = text.replace(old, new)
    if bad:
        for n, snippet in bad:
            sys.stderr.write("count=%d for %r\n" % (n, snippet))
        sys.stderr.write("refusing to write; %d/%d anchors bad\n" % (len(bad), len(PAIRS)))
        return 1
    text = text.replace("\r\n", "\n").rstrip("\n") + "\n"
    io.open(PATH, "w", encoding="utf-8", newline="").write(text)
    print("wrote %s (%d bytes, %d substitutions)" % (PATH, len(text), len(PAIRS)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
