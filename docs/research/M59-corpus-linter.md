# M59 — a corpus linter for SYNTHESIS

**Milestone:** M59. **Question:** 178 ("What is the cheapest automated check that
would have caught facts 694, 725, 759 and 763?"). **Fact 766** argues the absence
of that check is the corpus's most reproducible defect.

**Deliverable:** `scripts/corpus_lint.py`, runnable as `python scripts/corpus_lint.py`
from the submodule root, exit non-zero on any violation.

---

## 0. Pre-registration

*This section was written and committed **before** `scripts/corpus_lint.py`
existed, per AGENTS rule 20 and discipline 351. Section 3 onward is the result.*

### 0.1 What I measured first, and disclosed

I did not design blind. Before pre-registering I ran read-only feasibility probes
(`experiments/M59-corpus-linter/*.py`) to find out which candidate checks the
corpus can actually support. Those probes measured base rates only; none of them
is the linter. The probe results that shaped the list below:

| Probe | MEASURED | Effect on the design |
|---|---|---|
| §5 items whose bolded lead contains `?` | 0 of 212 | question-shape is a usable zero-base-rate heuristic for misplacement |
| §10 items whose bolded lead contains `?` | 110 of 124 (89%) | the reverse direction fires 11% of the time — dropped |
| §4 Source cells with no `MEASURED`/`DERIVED`/`ARGUED` label | 98 of 599 | a rule-8 label check would fire constantly — **dropped** |
| continuation-line indents in §5 | `{0:33, 3:19, 4:87, 5:462}` | the "five-space convention" is not uniform — **dropped**, and see §5 |
| continuation-line indents in §10 | `{0:35, 3:33, 4:357, 5:74}` | four-space dominates §10 — **dropped** |
| general count-vs-enumeration (any count, any list) | 4 flags, **4 false positives, 0 true positives** | **rejected**; see §4 |
| restricted `N of M <noun>` vs any enumeration | 8 sites, 7 false positives | rejected as written |
| amendment marker outside the Fact cell | 21 of 599 | too noisy to fail on — **advisory only** |
| `fact 200a` occurrences in `crates/**/*.rs` | 3, all of them prose *explaining* that `200a` is report-local | a "no sub-item labels in code" check would be 3-for-3 false — **dropped** |
| `"N-M are unallocated"` claims in §4's preamble | 4 claims, all true | cheap, deterministic, plantable — **adopted** |

### 0.2 The check list, pre-registered

Every check below is stated with **the input that would make it fail** (rule 20)
and **what it would fail to catch**.

#### Structural

- **S1 — table cell count.** Every markdown table row has exactly the cell count
  of its own table's header row, counting `\|` as an escaped literal and not as a
  delimiter. *Fails on:* a row with an unescaped `|` inside math notation
  (`|H|`, `|grad|`). This is fact 694's mechanism.
  *Will not catch:* a row with the right number of cells and the wrong content;
  a row whose cells are correct but in the wrong order.
- **S2 — table continuity.** No blank line between two table rows. A blank line
  terminates a GFM table; the rows after it have no header and no delimiter row,
  so they render as paragraph text. *Fails on:* one blank line inserted between
  two rows of a long table.
  *Will not catch:* a table split by any *other* block-level interruption
  (a heading, a list) — S2 tests the blank-line mechanism only.
- **S3 — file hygiene.** `SYNTHESIS.md` ends in exactly one `\n` and contains no
  `\r`. Every scanned file ends in a newline and does not mix `\r\n` with bare
  `\n`. *Fails on:* rule 37's `\Z`-in-lookahead bug, which strips the trailing
  newline when the anchor is the last item.
  *Will not catch:* anything about content. It is hygiene, not meaning.

#### Namespace

- **N1 — no duplicate numbers within a namespace.** A namespace is defined **by
  section**, never by number: facts are `| N |` rows in §4, disciplines are
  `N. ` items in §5, questions are `N. ` items in §10, risks are `N. ` items in
  §7. *Fails on:* rule 25's collision (M19 writing into a block M20-V held).
  *Will not catch:* a block written into genuinely free numbers that still
  duplicates an existing fold by *content* (AGENTS rule 28's defect).
- **N2 — placement by section.** No `| N |` fact row outside §4; no column-0
  numbered list item inside §4. *Fails on:* rule 37's "questions 151–154 written
  into §5" defect **when the numbers collide**; when they do not, N1 and N2 are
  both silent and only N3 can see it. **Checking placement by number alone gives
  false positives and is not done here** — disciplines and questions legitimately
  share integers (§4's own numbering note; disciplines 240-242 and facts 240-243
  coexist deliberately).
- **N3 — misplacement heuristic (ADVISORY, and it is a heuristic).** A §5
  discipline whose bolded lead sentence contains `?`. Base rate 0 of 212.
  *Will not catch:* a misplaced item phrased as a statement.
- **N4 — unallocated claims are true.** Every `"N-M are unallocated"` assertion in
  §4's preamble must hold: none of `N..M` may appear as a fact row.
  *Fails on:* folding into a block the document says is empty.
  *Will not catch:* a block that is claimed *reserved* rather than unallocated.

#### Citation

- **C1 — resolution, to a word boundary.** Every `fact N` / `discipline N` /
  `question N` / `risk N` / `rule N` reference in `SYNTHESIS.md`,
  `docs/research/*.md`, `AGENTS.md`, `OWNER-QUESTIONS.md`, `docs/captures-needed.md`
  and `crates/**/*.rs` resolves to an existing item **of that kind**. The number
  is a maximal digit run: `fact 200` must not match `fact 200a`. Fact 763 exists
  because a substring match could not tell those apart.
  When a reference fails, C1 reports whether the number exists in a *different*
  namespace, because that is the actionable case.
  Documented exclusions, each measured in §0.1 or §3: a letter suffix
  (`fact 198c` — report-local sub-item); a milestone qualifier (`M25 §7 fact 190`
  — that report's own numbering); block-reservation notation (`facts 250+`); a
  line asserting a reservation; `proposed as fact N`; and, in a non-SYNTHESIS
  report, a number the report itself declares.
  *Fails on:* fact 627's citation of fact 723 **only if 723 did not exist** — it
  does, so C1 would **not** have caught fact 763's first half. C1 catches a
  dangling number, not a wrong one. Stated plainly here because question 178
  names 763 as a target and **C1 only reaches half of it**.
- **C2 — the second half of 763 (`M25 fact 200` vs `200a`) is a counting bug, not
  a resolution bug.** C1's tokenizer is the fix: it classifies `200a` as
  report-local rather than as `200`. There is no separate check; the property is
  proved by a power probe in §4.

#### Semantic

- **A1 — question-status coherence.** A line claiming to close or answer question
  N, where §10's question N is marked `REOPENED` and the line's row does not
  itself acknowledge the reopening. This is fact 622's exact defect (fact 761's
  first instance). *Fails on:* re-introducing "closes question 119" without the
  amendment. *Will not catch:* an amendment that leaves a headline false without
  involving a question status — the other two instances in fact 761.
- **A2 — count versus enumeration, restricted.** A `N of M <corpus-item-noun>`
  claim in a row that also enumerates corpus numbers, where **no** enumeration in
  that row has length N. *Fails on:* fact 725 as originally written ("7 of 515"
  above a list of eight) — verified as a positive control before pre-registration.
  Restricted to corpus-item nouns (fact / row / question / discipline / site)
  because the unrestricted form scored 0 for 4. **This is the weakest check in
  the set and I say so before running it**; see §4 for what it cannot do.
- **A3 — amendment marker outside the Fact cell (ADVISORY, heuristic).** A row
  carrying `AMENDED`/`REFUTED`/`SCOPED`/`MOOT`/`WITHDRAWN`/`SUPERSEDED`/`NOT
  ADMISSIBLE` in the Consequence or Source cell but not in the Fact cell.
  21 of 599 rows at the time of pre-registration; **printed only under
  `--advisory` and never affecting the exit code**, because a 21-row standing
  list would train readers to ignore the output.

### 0.3 What no check in this set can see

Stated before running, so that it cannot be retrofitted:

- **A citation that resolves, is true, and is the weaker source** (fact 729).
  `gain_divisor = 436.8` citing fact 550 resolves and is correct; fact 585
  adjudicates the same constant by name. Nothing here ranks sources.
- **A sentence in which every number is correct and reproduces, and the sentence
  is still false** (fact 772). `reference.rs` paired SML's gate 0.150 with the
  other configuration's 87.76%. Both numbers real, pairing false. No
  number-checking audit finds this class, and this one does not either.
- **A number that is right in one configuration and quoted into another**
  (fact 768). At `through_focus.rs:514` `k = 5.94` is *correct*; the audit that
  called it wrong would have introduced a 3.27x error. A linter that matched on
  the number would repeat that mistake.
- **Fidelity of a fold to its source** (facts 758, 762, 765). Checking a row
  against the report it was folded from requires reading the report. Fact 765
  records a fold whose source was never committed; no linter can recover it.
- **An amendment that is correct but incomplete** (fact 760): the sweep that
  never revisited its own target.
- **Whether a claim is worth making at all.**

A linter that claimed any of the above would create false confidence in exactly
the document that records what the project believes. It does not.

---

## 1. What was built

`scripts/corpus_lint.py` — 870 lines, standard library only, no dependency on any
markdown renderer. Runs as `python scripts/corpus_lint.py` from the submodule
root; exits 0 when clean and 1 on any violation; exits 2 only if it cannot find
`docs/research/SYNTHESIS.md`. Every violation prints as
`path:line: [ID] message` followed by the offending text, indented.

| Flag | Effect |
|---|---|
| `--root DIR` | lint a different tree (this is what the power probe drives) |
| `--only ID` | run one check; used to prove a plant fires *that* check and not another |
| `--advisory` | additionally print the heuristics; **never** changes the exit code |
| `--list` | print the check ids |

Ten failing checks — `S1 S2 S3 S4 N1 N2 N4 C1 A1 A2` — and two advisories,
`N3 A3`. Scope: `docs/research/*.md`, `AGENTS.md`, `README.md`,
`docs/captures-needed.md`, `docs/research/OWNER-QUESTIONS.md`, and
`crates/**/*.rs` excluding `target/`. 78 markdown files and 27 Rust files at
the pinned sha — this report is one of them, and §5.2 records what happened
when the linter read it.

## 2. Deviations from the pre-registration, declared

Three, all disclosed rather than quietly absorbed.

1. **S3 was split into S3 and S4 after pre-registering, and S4 was then
   rewritten.** S3 is the trailing-newline property (the rule 37 defect); S4 is
   "the committed blob has mixed line endings". They were one bullet in §0.2.
   The first implementation of both counted `\r\n` and `\n` **on disk** and
   reported 13 violations. That was wrong, and §3.3.1 gives the measurement that
   proves it: the working tree is not the repository. Both now ask
   `git ls-files --eol` and judge the committed content, and both **skip with a
   printed NOTE** when git is unavailable rather than guessing.
2. **`OWNER-QUESTIONS.md` is at `docs/research/OWNER-QUESTIONS.md`,** not at
   the submodule root where §0.2 looked for it. It appeared during this
   milestone and is scanned, being under `docs/research/`. S3 finds a defect
   in it (§3.3).
3. **A1's scope was corrected after the power probe caught it doing nothing.**
   See §4.1 — this is the single most useful thing the probe did.

## 3. Result at HEAD

**Pinned:** `7a9b76bd4523d3bdeead32cc0a2c3fef8f39fae9`, working tree clean for
`docs/research/SYNTHESIS.md`. **The corpus is under concurrent edit** — §4 grew
from 573 to 639 rows while this milestone ran, across four orchestrator
commits. Every total below moves; **the defect set does not.** The same four
S1 files, the same three S2 line numbers and the same zero for C1/N1/N2/N4/A1
came back on every run in this session. Index at that sha, MEASURED by the linter:
**639 facts, 223 disciplines, 131 questions, 11 risks, 40 rules.**

```
corpus_lint: 78 markdown file(s), 27 rust file(s); 639 facts, 223 disciplines,
             131 questions, 11 risks, 40 rules
corpus_lint: FAIL — 11 violation(s): S1=4, S2=3, S3=4
```

| Check | At HEAD | Verdict |
|---|---|---|
| S1 table cell count | **4 violations** | real; fact 694's class, in files nobody re-checked |
| S2 table continuity | **3 violations** | real, and the largest single defect in the corpus |
| S3 file hygiene | **4 violations** | real, minor, one-character fixes |
| S4 line endings in the committed blob | **0** | **clean** — and see §3.3.1, this check first reported 13 and all 13 were false |
| N1 duplicate numbers | 0 | **clean** across 639 + 223 + 131 + 11 + 40 items |
| N2 placement by section | 0 | **clean** |
| N4 unallocated claims | 0 | **clean**; all 4 preamble assertions hold |
| C1 citation resolution | 0 | **clean** across **4,672** references |
| A1 question-status coherence | 0 | **clean** |
| A2 count vs enumeration | 0 | clean, but see §5.1 — it examined **one row** |

**Do not read the seven zeros as seven strong results.** C1's zero is strong; it has
a denominator of 4,672. A2's zero is nearly vacuous. §5 gives each its weight.

### 3.1 S2 — 458 of 639 fact rows do not render as table rows

**MEASURED**, at the pinned sha, by two independent renderers that agree to the
cell (`experiments/M59-corpus-linter/render_probe2.py`):

| | markdown-it-py 4.2.0 (`gfm-like`) | python-markdown 3.10.2 (`tables`) |
|---|---|---|
| §4 as committed | 190 `tr`, 745 `td`, **188 data rows** | 190 `tr`, 745 `td`, **188 data rows** |
| §4 with lines 949, 955, 958 deleted | 648 `tr`, 2577 `td`, **646 data rows** | 648 `tr`, 2577 `td`, **646 data rows** |

§4 contains two tables: the fact table and §4.1's 7-row sub-table. 646 − 7 = 639,
which is exactly the number of `| N |` rows in the source, so the control is
demonstrably complete. At HEAD only 188 − 7 = **181** fact rows render.
**458 of 639 fact rows (71.7%) render as paragraph text.**

The linter reaches the same 458 by a completely different route — static
strand-counting, no renderer — as `5 + 2 + 451`. Two methods, one number.

The mechanism is GFM's: a blank line ends a table. The rows below have no header
and no delimiter row, so they are not a table at all. **The fix is to delete
three blank lines** — `docs/research/SYNTHESIS.md` lines **949**, **955** and
**958**. Nothing else changes. This is the orchestrator's file; I have not
touched it.

This is fact 694's finding at 153x the scale. Fact 694 recorded three rows losing
their provenance column. Here 458 rows lose their table-ness entirely.

### 3.2 S1 — four rows silently discarding cells

The exact defect of fact 694, in report files. In every case an unescaped `|` in
mathematical notation opens a cell, and **markdown discards every cell past the
header's column count**.

| File:line | Pipes vs header | Cells discarded | Offending notation |
|---|---|---|---|
| `docs/research/G-edof-deconvolution.md:21` | 9 vs 5 (hdr L17) | 4 | `β(ω)·A³ / (S·\|ω\|)` |
| `docs/research/M20-VERIFICATION.md:28` | 10 vs 4 (hdr L25) | 6 | `Σ\|H\|²`, `√(Σ\|H\|²)/max\|H\|` |
| `docs/research/M46-detail-metric-measured.md:652` | 6 vs 4 (hdr L648) | 2 | `FSC(H·L, L)` row |
| `docs/research/M57-detail-metric-from-first-principles.md:145` | 7 vs 5 (hdr L142) | 2 | `sign(b)√\|b\|` |

Fix in each case: escape the bars as `\|`. `M20-VERIFICATION.md:28` is the worst —
six cells gone, including whatever followed the **REPRODUCED**/**CORRECTED**
verdict.

### 3.3 S3 / S4

**S3 (4 violations), all real and all one-character fixes:**

| File:line | Defect |
|---|---|
| `docs/research/M47-gain-blast-radius.md:208` | no trailing newline |
| `docs/research/M49-unapplied-findings.md:190` | no trailing newline |
| `docs/captures-needed.md:813` | ends in 2 newlines |
| `docs/research/OWNER-QUESTIONS.md:1246` | ends in 2 newlines |

The first two are rule 37's named failure mode: `\Z` inside an item-end
lookahead eats the final newline when the anchor is the last item.

### 3.3.1 S4 = 0, and the reason is the most transferable finding here

**S4 found 13 violations, and all 13 were false.** This is worth more than the
check.

The obvious implementation of "mixed line endings" counts `\r\n` and bare `\n`
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
finding — discipline 351's point, one level up: it is not enough to confirm the
failure is *your* check firing; you have to confirm your check is looking at the
thing you meant. The only reason I caught it is that git printed
`LF will be replaced by CRLF the next time Git touches it` while I was reading an
unrelated diff.

## 4. Power: every check was seen to fail

*A check that has never been seen to fail has not been tested* (AGENTS rule 36,
SYNTHESIS discipline 351). `experiments/M59-corpus-linter/power_probe.py` builds
a probe root — `SYNTHESIS.md` **with the three S2 blank lines removed**, plus
`AGENTS.md` and one small Rust file — establishes that it is clean, then plants
one violation at a time. The probe root is a throwaway `git init` repository
staged with `core.autocrlf=false`, because S3's and S4's line-ending halves are
judged on the index and cannot be exercised without one (§3.3.1). It is deleted
at the end of the run.

**Negative control, MEASURED:** the unmodified probe root scores
`corpus_lint: OK — no violations`, exit 0, across all ten checks. Every plant
below is therefore a change from clean to red and nothing else.

Discipline 351 says a red exit code is not evidence of the red you wanted, so for
every plant the harness asserts **four** things: exit code is 1 (not 2), the
output contains no `Traceback`, at least one violation carries **that check's
id**, and the message matches a needle specific to the planted defect. All
sixteen plants ran with `--only <ID>` so no other check could supply the red.

| # | Check | Plant | Control | Planted | Message that fired |
|---|---|---|---|---|---|
| 1 | S1 | append ` gain \|grad\| over the ROI \|` to a fact row | exit 0, n=0 | exit 1, n=1 | `8 unescaped pipes, header (line 766) has 5: 3 cell(s) … DISCARDED` |
| 2 | S1 | delete the closing pipe from a fact row | exit 0, n=0 | exit 1, n=1 | `4 unescaped pipes; its table's rows are modally 5 … missing a cell` |
| 3 | S2 | one blank line between two fact rows | exit 0, n=0 | exit 1, n=1 | `blank line inside a table: the 634 row(s) below it … Delete the blank line.` |
| 4 | S3 | strip the trailing newline | exit 0, n=0 | exit 1, n=1 | `file does not end in a newline` |
| 5 | S3 | commit SYNTHESIS wholesale as CRLF | exit 0, n=0 | exit 1, n=1 | `SYNTHESIS.md is committed with CRLF line endings; it is LF-only` |
| 6 | S4 | commit AGENTS.md with three CRLF lines among LF ones | exit 0, n=0 | exit 1, n=1 | `AGENTS.md:1: committed with MIXED line endings` |
| 7 | N1 | duplicate a fact row | exit 0, n=0 | exit 1, n=1 | `fact 1 is already declared at line 768 (§4 fact rows)` |
| 8 | N1 | duplicate a discipline number in §5 | exit 0, n=0 | exit 1, n=1 | `discipline 1 is already declared at line 1461 (§5)` |
| 9 | N2 | `9991. **…**` list item inside §4 | exit 0, n=0 | exit 1, n=1 | `numbered list item inside §4; facts are \| N \| table rows` |
| 10 | N2 | 4-column `\| 9992 \| … \|` row in §6 | exit 0, n=0 | exit 1, n=1 | `four-column \| N \| row outside §4` |
| 11 | N4 | fold a fact numbered **57** into the declared-unallocated 55-59 | exit 0, n=0 | exit 1, n=1 | `§4 says 55-59 are unallocated, but 57 exist as fact row(s)` |
| 12 | C1 | a reference to a nonexistent fact numbered 9994 | exit 0, n=0 | exit 1, n=1 | `does not resolve … no item of any kind carries 9994` |
| 13 | C1 | 694 written as a **discipline** number, where 694 is a **fact** | exit 0, n=0 | exit 1, n=1 | `§5 has no such discipline — **694 exists as fact**` |
| 14 | C1 | dangling citation inside a `.rs` file (9995, 9996) | exit 0, n=0 | exit 1, n=2 | `crates/strehl-probe/src/lib.rs:5: … 9995` |
| 15 | A1 | a row reading `(closes question 119)` with no acknowledgement | exit 0, n=0 | exit 1, n=1 | `§10 marks question 119 REOPENED (line 3337) and nothing in this passage says` |
| 16 | A2 | **restore fact 725's original "7 of 515"** | exit 0, n=0 | exit 1, n=1 | `states 7 of 515 fact but the row's corpus enumerations have length(s) [4, 8]` |

**16 of 16 plants proved power. 0 failed.**

Plant 15 is not synthetic: its text reproduces fact 622's pre-repair headline,
which fact 761 names as one of its three instances. Plant 16 is the literal
historical defect that open question 178 asks about.

**Advisories** (`--advisory`, never affects the exit code):
- **N3** control n=0 → planted n=1 (a §5 item phrased as a question), exit code
  unchanged at 0 both times. Power proven, non-failing behaviour proven.
- **A3** emits n=21 on the *unmodified* probe root, so it has been seen to fire
  without a plant.

**A2's negative control, stated because a false-positive check is worse than no
check:** on the repaired corpus, where fact 725 reads "8 of 515", A2 emits **0**.
It is silent on the true form and loud on the false one.

### 4.1 The probe caught a dead check — this is why the requirement exists

On its first run, **A1 did not fire on its own plant**. Control exit 0, planted
exit 0. Had I only run the linter against HEAD, I would have shipped A1 as
"clean" and it would have been clean because it could never fire.

**Cause, MEASURED.** A1 guards against false positives by requiring the amendment
to be absent from the *passage* containing the claim, and the passage was
computed as the contiguous run of non-blank lines. In §4 with the S2 blank lines
repaired, **every fact row is contiguous with every other**, so the "passage" was
the entire 639-row table — which of course contains the word `REOPENED`. Every
row inherited every other row's amendment and A1 was structurally silent.

**Fix.** For a table row the passage is the row itself; for prose it remains the
paragraph. Both forms are needed: the paragraph form is what suppresses two real
false positives where the acknowledgement sits on the next wrapped prose line
(`M58b-fold-fidelity-audit.md:195` and, ironically, this report's own §0).

A red exit code is not evidence of the red you wanted; a green one is not
evidence of the green you wanted either.

### 4.2 Fact 763's substring bug, demonstrated on the tokenizer

Fact 763 records `All cite M25 fact 200` being false because the count came from
a substring match that cannot distinguish `M25 fact 200` from `M25 fact 200a`.
The probe imports the linter and feeds the tokenizer that exact ambiguity:

```
input: All five sites cite M25 fact 200, and :92 cites fact 200a.
   fact  200  'fact 200'   class=qualified
   fact  200  'fact 200a'  class=sub
naive substring `fact 200` matches: 2
tokenizer references to fact 200:   1
```

**MEASURED: the naive matcher reproduces fact 763's over-count and the tokenizer
does not.** The number is a maximal digit run, so a trailing letter changes the
token's class rather than being ignored. 47 `sub` tokens exist in the corpus at
the pinned sha; a substring matcher would miscount every one of them.

## 5. What this linter cannot catch

§0.3 was written before the linter existed and stands unchanged: nothing here
sees fact 729 (a citation that resolves, is true, and is the **weaker** source),
fact 772 (every number correct, sentence still false), fact 768 (a number right
in one configuration and quoted into another), facts 758/762/765 (fidelity of a
fold to its source), or fact 760 (an amendment that is correct but incomplete).
Those were the audit's most valuable findings and they remain hand work.

What follows is the *additional* honesty owed after measurement.

### 5.1 A2 is a regression test for one row, not a general check

The task asked for a count-versus-enumeration check and said that if a reliable
version is not achievable I should say so and say why. **It is not achievable in
the general form, and the restricted form I shipped is far narrower than its name
suggests.** Both halves are MEASURED.

**The general form does not work.** Any-count-versus-any-list over §4 produced
**4 flags and 4 false positives, 0 true positives**: fact 566's "101 facts",
fact 584's "15/30 cells", and *twice* on the now-**correct** fact 725. Relaxing
to `N of M <any noun>` gave 8 sites and 7 false positives ("60 of 60 cells",
"6 of 6 cells", "261 of 421 frames"). Prose enumerates for a dozen reasons that
are not "here is the list of the N things I just counted", and no regex separates
them. A check firing 7 times in 8 gets turned off in a week.

**The restricted form's coverage, MEASURED** (`a2_coverage.py`) at the pinned sha:

| | Rows | Share of 639 |
|---|---|---|
| §4 fact rows | 639 | 100% |
| …containing ≥1 enumeration of resolvable corpus numbers | 98 | 15.3% |
| …containing an `N of M <corpus-noun>` claim | **2** | **0.3%** |
| …**A2 can say anything at all about** (needs both) | **1** | **0.2%** |

That one row is **fact 725 itself**. A2 currently reads exactly the row whose
defect motivated it, confirms "8 of 515" agrees with an eight-item list, and has
no opinion about the other 638 rows.

**ARGUED — call it what it is.** A2 is a *regression test for fact 725 expressed
as a lint rule*. That has real value: the defect cannot silently return, and the
rule generalises for free to any future row written in the same shape. It is not
a general count-versus-enumeration check and this report does not claim it is.
Anyone reading `A2 = 0` as "the corpus's counts have been verified" has been
misled, which is why the number 1/639 is printed here rather than left implicit.

### 5.2 C1 reaches half of fact 763 and none of fact 759

C1 is the strongest check in the set by evidence — **4,672 references resolved,
0 dangling**, across 78 markdown and 27 Rust files:

| Class | Count | C1's treatment |
|---|---|---|
| `ref` (plain `fact N`) | 4,672 | must resolve — **all do** |
| `qualified` (`M25 fact 200`, `M25 §7 fact 190`) | 235 | excluded: that report's own numbering |
| `sub` (`fact 198c`) | 47 | excluded: report-local sub-item label |
| `block` (`facts 250+`, `facts 520–539 reserved`) | 22 | excluded: reservation notation |
| by kind | 3,728 fact · 470 rule · 400 question · 343 discipline · 35 risk | |
| by area | reports 2,902 · SYNTHESIS 1,653 · Rust 421 | |

**But C1 catches a number that does not exist, not a number that is wrong.**
Fact 759 records fact 627 crediting a claim to fact 723 when the claim lives in
fact 656. Fact 723 exists. **C1 is silent on it and would have been silent on it
in 2026 too.** Question 178 names 759 as a target and C1 does not reach it.
Reaching it requires deciding whether a source *supports* a sentence — AGENTS
rule 38's distinction, and the thing fact 766 says nothing in the repository does.
That is still true after this milestone.

C1 reaches the *second* half of 763 (the `200` / `200a` counting bug, §4.2) and
not the first.

**C1's own false-positive surface, found by dogfooding.** References inside
fenced code blocks are excluded — quoted linter output is not a citation — but
inline prose is not. The first draft of this report tripped C1 three times on the
census table above, whose tally originally put each namespace noun *before* its
count (`… · rule` followed by 453, and so on): a *tally by kind* then has the
same token shape as a *citation*, and C1 cannot tell them apart. Putting the
numbers ahead of their nouns fixed it. **ARGUED:** the lesson is that C1's zero
at HEAD partly reflects a corpus that happens not to write tallies in that order,
and a future report that does will get a false positive. It is a cheap one to
diagnose — the message names the namespace the number *does* live in — but it is
real and it is not currently guarded. **This report is the only place in the
corpus where it has ever fired, and it fired on the report about itself.**

### 5.3 A3's recall cannot be measured, and I will not pretend otherwise

A3 is a heuristic and is labelled one in its own output (`[A3] HEURISTIC:`). It
never fails the build. Its 21 hits at HEAD are a review list, not defects.

Fact 761 names three instances — facts **202**, **610** and **622**. A3 fires on
**none of them**, and that is correct: **all three have been repaired** at the
pinned sha. Fact 202's headline now reads "three of six" with the correction
inline; 610's Source cell now says `confirmation REFUTED by fact 697`; 622's
headline now carries "question 119 is REOPENED … this row no longer closes it".
So A3's recall against the only labelled instances the corpus has **cannot be
measured** — the positives were fixed before the detector existed. I can say A3
fires (21 times, §4) and that it fires on a shape fact 761 describes. I cannot
say what fraction of fact 761's class it would find. Stated rather than skipped.

A1 is in better shape only because plant 15 reproduces fact 622's pre-repair
text and A1 fires on it — a real historical positive control.

### 5.4 The rest of the limits, briefly

- **S1** sees cell *count*, never cell *content* or cell *order*. A row with five
  correct cells in the wrong columns passes.
- **S2** tests the blank-line mechanism only. A table interrupted by a heading or
  a list is equally broken and S2 does not look.
- **N1/N2** define namespaces by section, never by number, because disciplines
  and facts legitimately share integers (facts 240-243 and disciplines 240-242
  coexist deliberately). The cost is that a block written into genuinely free
  numbers in the **right** section, duplicating an existing fold by content, is
  invisible — AGENTS rule 28's defect.
- **N4** checks assertions of the form "N-M are unallocated". A block described as
  *reserved* is a different sentence and is not checked.
- **Nothing here reads a report to check a fold against it.** That is the whole
  of facts 758, 762 and 765, and it is the majority of what M58b found by hand.

## 6. Incidental findings (reported, not fixed)

Three, none of them mine to repair.

**6.1 — M58b finding L11's premise does not hold. MEASURED.** L11 says question
142's continuation "is indented 1 space, against **the file's five-space
convention**". Continuation-line indents in `SYNTHESIS.md`, counted:

| Section | 0 sp | 3 sp | 4 sp | 5 sp |
|---|---|---|---|---|
| §5 disciplines | 33 | 19 | 87 | 462 |
| §10 questions | 35 | 33 | **357** | 74 |

Five-space is the plurality in §5 but not a convention (77% of 601), and in **§10
— the section question 142 is in — four-space dominates 357 to 74.** L11's
finding (the continuation consumed the blank line between items 142 and 143) may
still stand on its own; the *reason given* does not. I dropped an indent-uniformity
check for the same reason: it would fire hundreds of times against a rule the
file does not follow.

**6.2 — Fact 774 overstates the Rust test it describes. MEASURED, read-only.**
Fact 774 says `every_citation_the_binary_prints_resolves_to_synthesis_or_the_source`
(`crates/strehl-cli/src/stack.rs:1054`) "asserts that every citation the binary
emits **resolves**". Reading the test: it asserts the Profile arm rendered, that
the rendered string contains the literals `fact 550` and `question 126`, and then
that no printed `fact N` is followed by a letter. **It never opens
`SYNTHESIS.md`.** There is no `include_str!` and no file read anywhere under
`crates/` — verified corpus-wide. If fact 550 were deleted from SYNTHESIS
tomorrow the test would still pass.

What it actually asserts is that printed citations are **well-formed** — no
report-local sub-item labels — which is fact 763's second half and genuinely
valuable. It is not resolution. Fact 774's Consequence cell already says the
right thing ("It checks resolution, not support"); it is the headline that
overclaims, which is precisely fact 761's shape. C1 is the first check in the
repository that reads SYNTHESIS and resolves against it.

**6.3 — S1 finds fact 694's defect still live in four report files.** §3.2. Fact
694 recorded the per-fold pipe check "was only ever run on rows the current fold
added". The four rows in §3.2 are the rows nobody's fold added.

## 7. Answer to open question 178

*"What is the cheapest automated check that would have caught facts 694, 725, 759
and 763?"* — answered as measured, not as hoped.

| Target | Caught? | By what |
|---|---|---|
| **694** — unescaped `\|` drops cells | **Yes** | S1, ~40 lines. Found 4 live instances at HEAD. |
| **725** — count contradicts its own list | **Only in its own shape** | A2, which examines 1 row in 639 (§5.1). Fires on the historical text; does not generalise. |
| **759** — claim credited to the wrong existing fact | **No** | Requires judging support, not resolution (rule 38). §5.2. |
| **763** — `fact 200` matched `fact 200a` | **Half** | C1's tokenizer kills the substring bug (§4.2); the "credited to 723" half is 759's problem. |

**Two of four, plus half of a third.** The cheap half of question 178 is very
cheap: S1, S2, S3, N1, N2, N4 and C1 are all pure structure or pure resolution,
run in about a second, and together they found **11 violations at HEAD including
458 fact rows that do not render**. The expensive half — 725's general form and
759 entirely — is not cheap and I did not make it cheap; I bounded it and said so.

**The most useful single output of this milestone is not a check.** It is §3.1:
71% of the corpus's fact rows have not been rendering as table rows, in the
document that records what the project believes, and the fix is deleting three
blank lines. Fact 766 said every finding in M58b was found by hand and called
that the most reproducible defect in the report. This is the counter-example —
the largest structural defect in `SYNTHESIS.md` was found by a script in under a
second, and it had been sitting there through every hand audit.

---

**Reproduce:**

```
python scripts/corpus_lint.py                       # 11 violations, exit 1
python scripts/corpus_lint.py --advisory            # + 21 heuristic items
python experiments/M59-corpus-linter/power_probe.py # 16/16 plants, exit 0
python experiments/M59-corpus-linter/render_probe2.py
python experiments/M59-corpus-linter/c1_census.py
python experiments/M59-corpus-linter/a2_coverage.py
```

**Not done, deliberately:** no defect found here was fixed. `SYNTHESIS.md`,
`AGENTS.md` and `docs/captures-needed.md` were read and not written.
`crates/**` was read and not written.
