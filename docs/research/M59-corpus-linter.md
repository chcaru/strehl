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
