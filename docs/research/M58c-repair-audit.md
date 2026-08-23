# M58c — audit of the repairs (commits `9f6db3a`, `c690546`, `5ffa6bf`, `39b5ca7`)

**Milestone M58c.** Read-only with respect to `crates/**`, `SYNTHESIS.md`, `AGENTS.md`,
`OWNER-QUESTIONS.md`, `captures-needed.md` and `M56-citation-audit.md`. This file is the
only thing this milestone writes.

**Question under audit:** not "were the folds right" — M58b asked that — but **"did the
repairs to M58b's findings actually repair them, and did they introduce new defects".**
The rule that the author never verifies their own work applies to a repair exactly as it
applies to a fold.

Labels per rule 8. **MEASURED** = I ran a command and read its output. **DERIVED** =
exact arithmetic on measured or published quantities. **ARGUED** = reasoning from
structure, no new number.

## 0. Verdict

**The repairs are mostly real, the structural machinery is clean, and both of the two
things the commissioning agent was uneasy about are correct. But two of the twelve
amended rows still assert the claim they were amended to withdraw, one MODERATE finding
was repaired in the fact row and left standing in the question that cites it, and the
wrong-section defect class that AGENTS rule 37 exists to prevent recurred inside the
audit window.**

Two HIGH, six MODERATE, five LOW. Six of my own suspicions were refuted in the audited
party's favour and are recorded in section 6, because a clean result is a result.

**MEASURED, at `9f6db3a` / `c690546` / `5ffa6bf` / `39b5ca7` / HEAD:** zero fact rows
with the wrong unescaped-pipe count, zero rows with an empty provenance cell, zero
duplicate numbers in any namespace, and the file ends in exactly one newline at every
one of the five revisions.

---

## 1. HIGH

### H1 — Fact 627's headline still asserts what its own amendment refutes, and the source says the opposite

*Classification: transcription error + incomplete repair. Row 627 is on the twelve-row
"repaired" list; the repair at `5ffa6bf` fixed the citation and left the false clause.*

**SYNTHESIS `docs/research/SYNTHESIS.md:1188`, Fact cell:**

> An independent Python merge agrees with the shipped binary to **0.09%** on all seven
> stacks, and the three stacks that reproduced are **the ISO-160 ones** — the in-run
> control that makes this a diagnosis rather than an assertion.

**The same row, Consequence cell, amended by `5ffa6bf`:**

> (**Its ISO attribution is WRONG: `113MSDCF` and `112MSDCF` are ISO 500, not ISO 160**
> — per fact 656 ... corrected per fact 758 ...)

**Source, `docs/research/M52-gate-cluster-verified.md:257`:**

> Both wrong stacks are ISO 50; **all three that reproduce are ISO 160 or 500.**

MEASURED. `M52-gate-cluster-verified.md:238` gives `| 113MSDCF | 63 | 500 | 4.757 | 4.761
| -0.09% |` — 113 is ISO 500 and it reproduces. The source never said the reproducing
stacks were the ISO-160 ones; it said "ISO 160 **or** 500". The fold dropped four words,
and the row now carries the false claim in the cell a reader hits first and the
correction in the cell below it.

This is discipline 360 verbatim — *amend the sentence a reader hits first* — inside a row
the repair commit touched. The repair corrected which fact the ISO clause cites (723 →
656, my finding M3) and did not correct the sentence that clause contradicts.

**Reproduce:** `git --no-pager grep -n "all three that reproduce" -- docs/research/M52-gate-cluster-verified.md`

### H2 — `39b5ca7` wrote a question's MOOT verdict into a discipline: the rule-37 defect class recurred

*Classification: structural defect. Introduced by one of the four commits under audit.*

MEASURED. `git --no-pager show 39b5ca7 -- docs/research/SYNTHESIS.md` contains:

```
-170. **A population selected by thresholding a statistic computed on averaged data is not
+170. **MOOT -- answered by fact 771: four correct forms were already committed in `crates/`.** A population selected by thresholding a statistic computed on averaged data is not
```

**The edited line is `SYNTHESIS.md:1835`, which is inside `## 5. Engineering discipline`
(L1414-L2355). It is discipline 170, not question 170.**

Question 170 is at `SYNTHESIS.md:3444`, inside `## 10. Open questions` (L2771-end), and
at HEAD still reads, with no MOOT marker:

> 170. **What is the citable form for a report-local number that folded as a QUESTION
> rather than a fact?** Fact 717: `stack.rs` prints "fact 200a" on every run, the claim
> is true, and no correct form exists to write instead. (M56, fact 717)

Three consequences, all MEASURED:

1. **Discipline 170 is corrupted.** Its subject is thresholding a statistic computed on
   frame-averaged data. It now opens with a moot verdict about citation forms.
2. **Its headline no longer renders.** The original item opened `170. **A population
   selected ... is not\n     selected on the property you think it is.**`. The inserted
   clause consumes that opening `**`, so the discipline's actual headline renders
   unbolded and every emphasis span in the remaining eleven lines is inverted. (The
   item also carries a *pre-existing* unclosed `**` at its final line — that one is not
   from this commit.)
3. **Question 170 is still open**, so fact 771's "Question 170 is **MOOT**"
   (`SYNTHESIS.md:1332`) and the `39b5ca7` commit message's "Question 170 mooted" are
   both false of the file.

This is the defect class self-reported as fact 679 and legislated as AGENTS rule 37 —
inserting into the wrong section because facts, disciplines and questions share one
integer namespace three times over. M58b verified at `9aca35f` that it was repaired and
had stayed repaired. It recurred four commits later.

**Reproduce:**
`(Get-Content docs/research/SYNTHESIS.md)[1834]` and
`Select-String -Path docs/research/SYNTHESIS.md -Pattern '^170\. '`

**Scope note (ARGUED):** a full sweep of every numbered item added or edited by the four
commits found **exactly one** wrong-section landing. The other twenty-eight landed
correctly (disciplines 348-368 in §5, questions 172-181 in §10, the §8 ship-order item in
§8). This is one slip, not a systemic regression.

---

## 2. MODERATE

### M1 — Fact 725's Consequence still says "seven" after its headline was corrected to "8"

*Classification: incomplete repair. Row 725 is on the twelve-row list and was amended
twice.*

**`SYNTHESIS.md:1286`, Fact cell (repaired at `5ffa6bf`):**

> **Refuting the corpus's most-cited recent result touched only **8 of 515** fact rows,
> and **TWO** of them became internally false as a result.**

**Same row, Consequence cell, unchanged:**

> A corpus where one refutation cascades through hundreds of rows is a corpus of
> opinions; one where it touches **seven** is a corpus of measurements.

MEASURED. The row's own enumeration lists eight (613, 618, 622, 623, 639, 645, 650,
652), and its arithmetic now balances at eight (2 false + 4 strengthened-or-unaffected +
2 traps). The Consequence says seven.

Fact 725 is the row from which discipline 360 was derived. **Discipline 360 was
reproduced inside the repair of the row that is its own exhibit.** The commissioning
agent asked specifically whether this shape had recurred; it has, here.

### M2 — Question 165 still carries "four of the six failing cells are flat"

*Classification: half-completed repair of a MODERATE finding.*

Fact 707 was repaired (`SYNTHESIS.md:1268` now reads "**three** of the six failing cells
sit — M55 section 5.4 has exactly three flat ROIs among six, so 'four' was impossible").
**Question 165, which cites fact 707 and carries the identical claim, was not.**

**`SYNTHESIS.md:3407`:**

> 165. **Why is the flat-ROI contiguous penalty K-independent?** Fact 707: ... An
> unidentified mechanism operates on flat regions, and **four of the six failing cells
> are flat.** (M55, fact 707)

MEASURED. `M55-sigpow-verification.md` §5.4's table has six cells (0.368, 0.635, 0.366,
0.037, 0.739, 0.549) of which exactly three are flat ROIs. M58b finding M1 quoted **both**
fact 707 and question 165. The statement "all eight MODERATE findings are repaired" is
therefore refuted on this one.

### M3 — Fact 709 says "three ... two of them pre-registered", and names only two

*Classification: incomplete repair; the count was corrected and the enumeration was not.*

**`SYNTHESIS.md:1270`:**

> **The verifier refuted three of its own positions, two of them pre-registered.**
> (**Count corrected per fact 758; the row named only the two it went on to describe.**)
> Its objection that matched cost manufactures separation is refuted by its own data ...
> and its pre-registered sign on the gate sweep was refuted by the sweep.

**Source, `M55-sigpow-verification.md:30-35`:**

> Twenty-four predictions, each with a success criterion **and an explicit falsifier of
> my own objection**, registered before the deciding run. PR1-PR9 and PR14-PR24 in the
> session store; PR10-PR13 in script docstrings committed with their output.
>
> **Three of the twenty-four refuted my own stated objection** (PR7, PR11, PR21).

MEASURED. All twenty-four were pre-registered; PR7, PR11 and PR21 are all PR items;
therefore **all three** self-refutations are pre-registered, not two. Two residual
defects in one row:

1. "two of them pre-registered" is still an undercount, and implies one was not.
2. The row's body describes PR7 (§2.3, matched cost) and PR11 (§3.6, the gate-sweep
   sign) and **never mentions PR21** (§4.3, the `lambda^4` docstring). The headline now
   says three; the row still enumerates two.

### M4 — Fact 769's "three sources" drops M43 and substitutes the same milestone's second code path

*Classification: transcription error (scope/enumeration).*

**`SYNTHESIS.md:1330`:**

> **Fact 500's `1.815` is measured three times independently, not a corpus number as the
> routing brief claimed.** M52 measures 1.8145, M54 measures 1.8114 in `strehl-plugin`
> and 1.8109 in `strehl-core` — three sources, **0.21% spread**.

**Source, `docs/research/M58-citation-content-repaired.md:156-160`:**

> **Fact 500's 1.815 is not a corpus number.** ... `M52-gate-cluster-verified.md:99-100`
> already records 0.027605 against M43's 0.027613 (+0.03%, `k` = 1.8145). **Mine is the
> third independent measurement** and the first in Rust.

**and `:427`:** "(M43 0.027613, M52 0.027605, M58 0.0275531 — spread **0.21%**)"

MEASURED. The source's three independent sources are **M43, M52 and M54/M58**. Fact 769's
three are M52, M54-plugin and M54-core — it **drops M43**, the originating measurement,
and makes up the count with the same milestone's second code path. The source itself
calls those two paths one measurement ("Mine is the *third*"), while separately noting
they "share no calibration code".

DERIVED, second point: the source's 0.21% is the spread of the SD triple
(0.027613 / 0.027605 / 0.0275531 → 0.217%). Fact 769 attaches it to the ratio triple
1.8145 / 1.8114 / 1.8109, whose spread is **0.199%**. The quantity is misattached; the
error is small.

The row's claim is *weaker* than the source supports — under its own enumeration only two
milestones measured it — which makes this an understatement, not an overstatement.

### M5 — Fact 765 says the M56 report text "is gone"; it was recovered 26 minutes later and the row was not amended

*Classification: stale row, now internally false. Caused by an out-of-scope commit;
reported because the row is live.*

**`SYNTHESIS.md:1326`, Consequence:**

> Evidence and a disclosure stub are committed here; **the report text is gone.**

MEASURED. `git --no-pager log -- docs/research/M56-citation-audit.md` gives two commits:
`5ffa6bf` (13:35, the stub) and **`606df14` (14:01, "docs: recover M56 citation-content
audit from agent context")**. The file at HEAD opens:

> **Recovered from the auditing agent's context on 2026-08-23, after the fold discovered
> the report had never been committed. This replaces the disclosure stub at this path.**

Fact 765 was not amended by `606df14`. A reader of fact 765 at HEAD is told the M56 report
text is unrecoverable while it sits, in full, at the path the same row points to. This is
fact 723's mechanism (an amendment does not propagate to what cites it) applied to
SYNTHESIS itself — the same mechanism fact 725 records.

### M6 — The M53 fold has no committed findings document, so 25 rows are unauditable for fidelity

*Classification: rule-31 gap. Not the same violation as fact 765 — the evidence is
committed — but the same consequence for an auditor.*

MEASURED. Facts 733-757 (folded at `c690546`) carry provenance of the form `M53 F3
(MEASURED)`, `M53 turn-2 F1/F2 (MEASURED)`, `M53 turn-4 F4 (ARGUED)`. There is **no
`docs/research/M53-*.md` in any commit** and **no `M53` entry in AGENTS.md's report
index**. `git ls-files | Select-String M53` returns only `experiments/m53-flat-ratio/**`,
whose `README.md` (121 lines) documents the flat-ratio replacement and carries no
F-numbering and none of the turn-2/3/4 material.

Three of the twenty-five rows do cite code shas (742 `55b6b0d`, 744 `4a5c270`, 750
`9168b19`, all of which exist) — partial compliance with rule 31's second half.

ARGUED: the F-references resolve to nothing a later reader can open. This is the
condition fact 765 describes ("a fold whose source is not committed is unauditable by
construction"), one severity step down because the experiment directory is committed.

**Systemic context, MEASURED, offered so this is not over-weighted:** only **33 of 599**
fact rows (5.5%) carry a sha in the provenance column at all. Rule 31's "record its sha
in the source column" is corpus-wide unobserved and long predates these commits.

---

## 3. LOW

### L1 — Fact 202's body still enumerates 113 among the zero-clipping stacks

`SYNTHESIS.md:890`. The headline is correctly repaired to "absent from **three of six**
stacks" with an explicit correction note. The body still reads "while `109`, `119`,
`112`, `113` contain **zero**", un-struck, immediately above the amendment that strikes
113 and a later clause reading "`109`, `112` and `119MSDCF` remain exactly zero". Three
statements about 113 in one cell, one of them withdrawn only by the amendment that
follows it. The corpus's amend-in-place convention arguably licenses this; a
strikethrough on the base clause would remove the ambiguity. **Not a factual error.**

### L2 — Fact 694's repair records half of M58b's finding M6

`SYNTHESIS.md:1255`. The repair correctly narrows "two of them" to "**One** of them
(617) ... row 620 carried the same malformation but was not among the three". It does
**not** record the other half of M6: MEASURED at `606c8f7`, commit `7ebfdfa` silently
rewrote **both** 617 and 620 to `M46 (DERIVED + MEASURED)` under a commit whose stated
subject was pipe escaping. The undisclosed provenance edit is still undisclosed.

### L3 — Fact 758's three fidelity ratios are the orchestrator's arithmetic, carried under `M58 (MEASURED)`

`SYNTHESIS.md:1319`: "Fidelity to source confirmed digit-for-digit for **11 of 16 M48b
rows, 9 of 13 M54 rows, 14 of 18 M55 rows** and all four M54-derived questions."

MEASURED. `docs/research/M58b-fold-fidelity-audit.md` contains none of the strings
"11 of", "9 of", "14 of", "16 M48b", "13 M54" or "18 M55", and states no such ratios
anywhere. They are a summarisation of M58b's prose performed by the folder and labelled
`M58 (MEASURED)`. I cannot refute the ratios; I can say they were not measured by the
milestone they are attributed to. Correct label would be DERIVED.

### L4 — Fact 758's "Every HIGH defect is repaired in this commit" is overstated

`SYNTHESIS.md:1319`. M58b's H1 was that fact 725 is false on its own enumeration. The
repair corrected the headline and left the Consequence asserting the old count (M1
above). The HIGH finding is *mostly* repaired; the row is still self-contradicting on the
exact number the finding was about.

### L5 — The M56 disclosure stub, as committed at `5ffa6bf`, overstated what was preserved

Superseded 26 minutes later by `606df14`, so the practical severity is now near zero.
Recorded because `5ffa6bf` is in scope and the question asked was whether the stub was
honest.

MEASURED at `5ffa6bf`: the stub enumerated the committed evidence as including "the
per-file context dumps". `git ls-files experiments/M56-citations` returns **11 files**;
none of the six `ctx_*.txt` per-file context dumps is among them — only `ctx.py`, the
script that generates them. `git status --short` showed **33 further files still
untracked**, including `cites.json`, `facts.json`, `disc_ques.json`, `parse_facts.py`,
`parse_dq.py`, `join.py` and `solve_check.py`.

The stub also said facts 720 and 721 were "**Confirmed exactly.**" M58b's own text
(`M58b-fold-fidelity-audit.md:390-391`) says: for 720, "**CONFIRMED**; but
`M52-gate-cluster-verified.md:670` already reported it, so the `M56 (MEASURED)`
attribution is at best incomplete" — the caveat was dropped — and neither 720's "two of
three assertions false" nor 721's "stale on 8 of 20 rungs" was ever verified by M58b.

**Judgement (ARGUED): the stub named the loss plainly and did not read as an excuse, but
it overstated the salvage.** It is honest about *what* was lost and inaccurate about
*what remains*. The recovery at `606df14` is the better answer and supersedes the
question.

---

## 4. The two things you were uneasy about — both clean

### 4.1 The `87.76%` → `89.02%` propagation: correct sites, no blind substitution

**MEASURED.** Every occurrence of `87.76` and `89.02` in the repository (excluding
`target/` and unrelated CSV columns) was classified by whether the same line pairs it
with `0.168`/`k = 5.94` or with `0.150`/`k = 6.68`.

The two sites `39b5ca7` changed:

| site | text before | pairing on that line | verdict |
|---|---|---|---|
| `E-plugin-architecture.md:1490` (§F4.6 fault 5) | "a `k` = 6.68 operator reverts 87.76% of pixels" | `k` = 6.68 | **change required, change correct** |
| `E-plugin-architecture.md:1531` (§F5.1) | "At `k` = 6.68 the tool reverts 87.76% of pixels" | `k` = 6.68 | **change required, change correct** |

Every surviving `87.76%` falls into one of four classes, and **none of them is a
mis-pairing that was missed, and none of them is a true statement that was overwritten:**

- **Correctly paired with 0.168 / `k` = 5.94** — `M43-plugin-calibration-seam.md:94`
  (`| operator 5.94x noisier than declared | 0.168 | 1.131 | **87.76%** |`),
  `SYNTHESIS.md:1024`, `M56-citation-audit.md:235`,
  `M58-citation-content-repaired.md:78, :193, :317`,
  `experiments/M56-citations/eff_gates_109.txt:45`. **All left alone. Correct.**
- **Explicit correction or diagnosis notes** — `E-plugin-architecture.md:1538-1539`,
  `reference.rs:35`, `:303`, `M52-gate-cluster-verified.md:465-466`,
  `SYNTHESIS.md:1283`, `M58-citation-content-repaired.md:363, :434`.
- **Stated generically with no `k` attached** — `M43:25`, `:98`, `:176`,
  `AGENTS.md:533`, `OWNER-QUESTIONS.md:162`. These describe "one such mistake" without
  naming an operator; they are not mis-pairings. Both were last modified by `a1aed84`
  and `edb1c06` respectively, long before these commits. **Correctly left alone.**
- **Unrelated numeric coincidence** in `experiments/m10-*`, `m12-*`, `m15-*`, `m16-*`,
  `m23-*` CSV data.

**You checked correctly. There is no blind global substitution and no missed site.**

One observation, offered as ARGUED and not as a defect, because it is pre-existing text
in a file you own: `AGENTS.md:533` and `OWNER-QUESTIONS.md:162-168` both state 87.76% for
"one such mistake" and then, in the next clause or paragraph, name 6.68 as the worst case.
Neither pairs them, but a reader moving quickly — and OWNER-QUESTIONS is explicitly
written for a reader moving quickly — can attach the fraction to the worst case, which is
the false pairing fact 772 repaired. Not introduced by these commits.

### 4.2 Rule 39's S-range endpoint `0.980`: correct, and nothing else quotes `0.976` as a range endpoint

**MEASURED.** `AGENTS.md:441-443` now reads "reads 0.770 to **0.980** on one plant with
only the repetition count varying". The source, `M55-sigpow-verification.md`, says
`0.770 to 0.980` at **L3**, **L315** ("`S` ranges 0.770 to 0.980 with nothing changed but
`REPS`") and **L489**, and its §5.6 table at **L309** gives `REPS` = 16 → **0.980**.

A repository-wide search for `0.976` returns four hits in `SYNTHESIS.md` and none in
`AGENTS.md`:

- `:1256` — fact 695 quoting the exact table row `0.770 / 0.976 / 0.937 / 0.972` at
  `REPS` 1 / 8 / 32 / 64. **Correct: 0.976 is the REPS = 8 value.**
- `:1201` — fact 640's restored corroboration "at REPS = 8, `S`(canonical) 0.976 >
  `S`(old) 0.936". **Correct, same reason.**
- `:967`, `:1091` — unrelated pre-existing rows about `R` and `rho`.

Fact 640's own S-range and discipline 338 both read `0.770-0.980` at HEAD. **The endpoint
is right and the old value survives only where it is the correct value.**

---

## 5. Fact 778 and `M52-gate-cluster-verified.md:464-466` — you read it correctly

**MEASURED.** The lines in question, verbatim:

```
464: 4. **`E-plugin-architecture.md` §F4.6 fault 5 mis-cites its own numbers**: it
465:    attributes "87.76% of pixels revert to selection" to a `k` = 6.68 operator,
466:    but 87.76% was measured at effective gate 0.168, i.e. `k` = 5.94.
```

This **diagnoses** the mis-pairing. It names the defective site, quotes the wrong
attribution, and gives the correct pairing in the next clause. It does not carry the
defect. **Fact 778's reading is correct and no repair is needed there.**

Two refinements, neither a defect:

- M52:464-466 names only §F4.6 fault 5. It does **not** name §F5.1. Fact 778 claims both
  sites, which is an *addition* by M54, correctly attributed to this commit rather than
  to the hand-off. MEASURED: §F5.1 (`E-plugin-architecture.md:1531`) did carry the same
  mis-pairing.
- The hand-off's `docs/proposals/` path is indeed wrong; MEASURED, the file is at
  `docs/research/E-plugin-architecture.md` and `git ls-files docs/proposals` is empty.

---

## 6. Six suspicions of mine, refuted in the audited party's favour

Recorded because the value of an audit is destroyed if it only reports the hypotheses
that survived.

1. **I expected the `M54 (MEASURED)` label on facts 767-778 to be a misattribution**,
   because the source report is `docs/research/M58-citation-content-repaired.md`, whose
   first line reads "**Milestone M58.**". **Refuted.** `AGENTS.md:545` documents the
   trap explicitly: "**NAMING TRAP: written by M54, not M58.**" The label is right and
   the index says so.
2. **I expected the M54-batch-2 fold to repeat the M56 rule-31 violation.** **Refuted.**
   The source was committed at `e01da9e` (13:33:54) and folded at `39b5ca7` (13:38:32) —
   the source existed in a commit *before* the fold, which is what rule 31 requires.
3. **I expected provenance cells to have been dropped somewhere**, given fact 694's three
   rows and the twenty-five near-misses in the M53 fold. **Refuted.** MEASURED: every
   fact row at all four commits and at HEAD has a non-empty fourth cell, and **every row
   numbered 726 or above carries an explicit provenance-class token**
   (MEASURED / DERIVED / ARGUED). The 116 rows in the file that lack one are all numbered
   ≤ 568 and use an older convention.
4. **I expected the `87.76%` propagation to have overwritten a correctly-paired site.**
   **Refuted** — section 4.1.
5. **I expected discipline 340's self-citation (M58b finding L9) to still be there.**
   **Refuted.** `SYNTHESIS.md:2291` now reads "(M55, fact 705; the shared-latent
   mechanism is M55's own and is folded nowhere else)".
6. **I expected M58b's omission O1 (M55 §5.6's corroborated direction) to still be
   missing.** **Refuted.** `SYNTHESIS.md:1201` now carries "the fold originally dropped
   that half: in M55's own harness at REPS = 8, `S`(canonical) 0.976 > `S`(old) 0.936.
   The ordering survives; only the MAGNITUDE is unmeasurable."

**Discipline 305 holds for an eighth audit.** The brief named the mechanism (blind
substitution; a wrong range endpoint) and the observable, and withheld the expected sign,
and the answer came back against the auditor's hypothesis in both cases.

---

## 7. Rows verified end to end and found clean

MEASURED, at HEAD, reading headline, "so what" and provenance for each of the twelve
amended rows:

| row | headline | consequence | provenance | verdict |
|---|---|---|---|---|
| 202 | repaired | clean | clean | **repaired** (L1: un-struck base clause) |
| 610 | repaired | repaired | repaired | **repaired** |
| 613 | clean | repaired | clean | **repaired** |
| 622 | repaired | repaired | clean | **repaired** |
| 627 | **still false** | repaired | clean | **H1** |
| 694 | repaired | clean | clean | **repaired** (L2: half of M6) |
| 696 | repaired | clean | clean | **repaired** |
| 707 | repaired | repaired | clean | **repaired**; question 165 not — **M2** |
| 709 | **still undercounts** | clean | clean | **M3** |
| 719 | repaired | clean | clean | **repaired** |
| 725 | repaired | **still says seven** | clean | **M1** |

Facts 758-766 (the fold of M58b) check out against `M58b-fold-fidelity-audit.md` on
every number I can trace: 758's "3 HIGH, 8 MODERATE, 12 LOW defects, 6 omissions and 1
process defect", 759's eight-row enumeration, 760's 231x and the 0.02-to-3.0 range, 761's
three rows, 762's six-cell table `0.368 / 0.635 / 0.366 / 0.037 / 0.739 / 0.549`, 763's
`200a`, 764's two self-refutations, 766's count. Provenance `M58 (MEASURED)` on all nine.

Facts 767-778 check out against `M58-citation-content-repaired.md`:

- **768** — `5.943 = 1.811 x 3.281` matches `:357`; DERIVED, 1.811 x 3.281 = 5.9421,
  consistent with 5.943 to the stated rounding. "3.27x error" matches
  DERIVED 5.943/1.815 = 3.274 and the source's `:173`.
- **770** — "eight sites ... only **two** quote the literal span" gives the 4x over-count
  DERIVED; `calibrate.rs:908`, `:922`, `registry.rs:386` named as the missed sites.
- **771** — MEASURED: `crates/strehl-cli/src/stack.rs:397` emits `question 126`, and
  `:1081` asserts it.
- **772** — matches `:315` (`89.02 vs 87.76`, 1.26 pp) and `experiments/M56-citations/eff_gates_109.txt:43,45`.
- **773** — source `:211` `| tenengrad | 59.73 ms | 4.98 ms | 2.93x |` and `:214` "Agrees
  with M56's 4.99 / 59.84 to 0.2% and with fact 525's 5.02 / 60.3 to ~1%". Fact 773
  transcribes all six numbers exactly. DERIVED: max disagreement 0.95%, so "under 1%" holds.
- **774** — MEASURED: both named tests exist, at `crates/strehl-cli/src/stack.rs:1054`
  and `crates/strehl-plugin/src/reference.rs:700`.
- **777** — source `:401`/`:406` give `strehl-core 126 passed` and `210 passed, 0 failed`;
  DERIVED 40+126+35+8+1 = 210. "Up from 207" matches fact 731's `39+126+33+8+0+1+0 = 207`.

The M48 fold (`9f6db3a`): facts 726-732 trace to `M48-read-noise-measured.md` (committed);
fact 726's four-site account (`:72, :87, :112` → fact 550, `:92` → question 126) matches
M58b's own MEASURED finding M4 exactly, and fact 581's amendment now records it.

**Structural, MEASURED at all five revisions:**

```
sha       fact rows  dup  bad-pipe  empty-prov  disciplines  dup  questions  dup  one-LF
0912210      523      0      0          0           185       0      110      0    True
9f6db3a      523      0      0          0           185       0      110      0    True
c690546      548      0      0          0           194       0      114      0    True
5ffa6bf      557      0      0          0           199       0      116      0    True
39b5ca7      569      0      0          0           203       0      118      0    True
HEAD         573      0      0          0           206       0      120      0    True
```

---

## 8. Process note: one sha in the brief does not exist

MEASURED. The brief names `c11c968` as "the fold of M54 batch 2, which also edits
`docs/research/E-plugin-architecture.md`". `git cat-file -t c11c968` returns
`fatal: Not a valid object name c11c968`. The commit with that description is
**`39b5ca7`**, "Fold M54 batch 2: the routing was wrong three times, once in a way that
would have introduced a 3.27x error". I audited `39b5ca7`.

---

## 9. Summary, ordered by severity

| # | finding | classification | severity |
|---|---|---|---|
| H1 | Fact 627's headline says the reproducing stacks are "the ISO-160 ones"; M52:257 says "ISO 160 **or 500**" and the row's own amendment says 112/113 are ISO 500 | transcription error + incomplete repair | **HIGH** |
| H2 | `39b5ca7` wrote question 170's MOOT verdict into **discipline** 170 (`:1835`); question 170 (`:3444`) is still open and the discipline's headline no longer renders | structural defect | **HIGH** |
| M1 | Fact 725's Consequence still says "seven" after the headline was corrected to "8" | incomplete repair | MODERATE |
| M2 | Question 165 still says "four of the six failing cells are flat"; fact 707 was repaired and the question citing it was not | incomplete repair | MODERATE |
| M3 | Fact 709 says "three ... two of them pre-registered"; M55 §1 pre-registered all twenty-four, and the row still enumerates only two | incomplete repair | MODERATE |
| M4 | Fact 769's "three sources" drops M43 and substitutes M54's own second code path; 0.21% belongs to the SD triple | transcription error | MODERATE |
| M5 | Fact 765 says the M56 report text "is gone"; `606df14` recovered it and the row was not amended | stale row, now false | MODERATE |
| M6 | The M53 fold cites `M53 F1`-`F10` and turn-2/3/4 findings that exist in no commit; 25 rows unauditable | rule-31 gap | MODERATE |
| L1 | Fact 202's body still enumerates 113 among the zero-clipping stacks, un-struck | presentation | LOW |
| L2 | Fact 694 does not record that `7ebfdfa` also rewrote row 620's provenance | omission | LOW |
| L3 | Fact 758's "11 of 16 / 9 of 13 / 14 of 18" appear nowhere in M58b; DERIVED by the folder, labelled MEASURED | provenance | LOW |
| L4 | Fact 758's "Every HIGH defect is repaired in this commit" — H1's repair left 725 self-contradicting | overstatement | LOW |
| L5 | The M56 stub at `5ffa6bf` claimed the per-file context dumps were committed (they are not) and that facts 720/721 were "confirmed exactly" (720's caveat was dropped) — superseded by `606df14` | overstatement | LOW |

**Clean:** the `87.76%` → `89.02%` propagation (§4.1); rule 39's `0.980` (§4.2); fact
778's reading of M52:464-466 (§5); the provenance column at every in-scope commit (§6.3);
all pipe counts, duplicate checks and the trailing newline at all five revisions (§7).

**Not checked:** whether M58b's twelve LOW findings were repaired — `96d37bf` ("Repair
the audit's LOW tier: three of the twelve were not low") is not one of the four commits
in scope. Spot checks found L9 (discipline 340) and omission O1 (fact 640) repaired.
I did not run `cargo test` to re-verify fact 777's 210, because three other agents are
live in `crates/` and the number would not be comparable.
